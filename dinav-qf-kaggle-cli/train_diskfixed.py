from __future__ import annotations

import argparse
import json
import math
import random
import time
from contextlib import nullcontext
from pathlib import Path

import torch
from torch.utils.data import Dataset

from model import DinavQF, ModelConfig
from run_manifest import build as build_manifest, write as write_manifest


class TokenDataset(Dataset):
    def __init__(self, path: str, seq_len: int):
        token_path = Path(path)
        byte_size = token_path.stat().st_size
        if byte_size % 4 != 0:
            raise RuntimeError(f'int32 token file has invalid byte size: {byte_size}')
        count = byte_size // 4
        self.tokens = torch.from_file(str(token_path), dtype=torch.int32, size=count).long()
        self.seq_len = seq_len

    def __len__(self) -> int:
        return max(0, (self.tokens.numel() - 1) // self.seq_len)

    def __getitem__(self, idx: int):
        start = idx * self.seq_len
        chunk = self.tokens[start:start + self.seq_len + 1]
        return chunk[:-1], chunk[1:]


class DeterministicBatchStream:
    def __init__(self, dataset: TokenDataset, batch_size: int, seed: int):
        self.dataset = dataset
        self.batch_size = batch_size
        self.seed = seed
        self.batches_per_epoch = len(dataset) // batch_size
        if self.batches_per_epoch < 1:
            raise RuntimeError('token dataset is smaller than one micro-batch; lower --micro-batch-size or add admissible corpus data')
        self._epoch = -1
        self._perm: torch.Tensor | None = None

    def _permutation(self, epoch: int) -> torch.Tensor:
        if epoch != self._epoch or self._perm is None:
            generator = torch.Generator().manual_seed(self.seed + epoch)
            self._perm = torch.randperm(len(self.dataset), generator=generator)
            self._epoch = epoch
        return self._perm

    def batch(self, micro_batch_cursor: int) -> tuple[torch.Tensor, torch.Tensor]:
        epoch = micro_batch_cursor // self.batches_per_epoch
        batch_in_epoch = micro_batch_cursor % self.batches_per_epoch
        perm = self._permutation(epoch)
        start = batch_in_epoch * self.batch_size
        indices = perm[start:start + self.batch_size].tolist()
        pairs = [self.dataset[int(i)] for i in indices]
        return torch.stack([x for x, _ in pairs]), torch.stack([y for _, y in pairs])


def lr_for_step(step: int, total: int, peak: float, warmup: int, floor_ratio: float = 0.1) -> float:
    if step < warmup:
        return peak * (step + 1) / max(1, warmup)
    progress = min(1.0, (step - warmup) / max(1, total - warmup))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return peak * (floor_ratio + (1.0 - floor_ratio) * cosine)


def choose_device() -> str:
    if torch.cuda.is_available():
        return 'cuda'
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def prune_checkpoints(directory: Path, model_name: str, keep: int) -> None:
    prefix = f'{model_name}-'
    ranked = []
    for path in directory.glob(f'{model_name}-*.pt'):
        stem = path.stem
        if not stem.startswith(prefix):
            continue
        try:
            step = int(stem[len(prefix):])
        except ValueError:
            continue
        ranked.append((step, path))
    ranked.sort(reverse=True)
    for _, path in ranked[keep:]:
        path.unlink(missing_ok=True)


def save_checkpoint_atomic(state: dict, path: Path, model_name: str, keep: int) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.unlink(missing_ok=True)
    torch.save(state, temp)
    temp.replace(path)
    prune_checkpoints(path.parent, model_name, keep)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--tokens', required=True)
    p.add_argument('--steps', type=int, default=1000)
    p.add_argument('--stop-after-step', type=int, help='pause intentionally at this optimizer step while preserving the original schedule target')
    p.add_argument('--micro-batch-size', type=int, default=2)
    p.add_argument('--grad-accum', type=int, default=8)
    p.add_argument('--lr', type=float, default=3e-4)
    p.add_argument('--warmup-steps', type=int, default=100)
    p.add_argument('--seed', type=int, default=1337)
    p.add_argument('--checkpoint-every', type=int, default=500)
    p.add_argument('--keep-last-checkpoints', type=int, default=1, help='retain only the newest N checkpoints for this model after each successful atomic save')
    p.add_argument('--gradient-checkpointing', action='store_true')
    p.add_argument('--resume', help='checkpoint path to resume model/optimizer/scaler and deterministic batch cursor from')
    p.add_argument('--average-gpu-watts', type=float)
    p.add_argument('--pue', type=float, default=1.0)
    p.add_argument('--carbon-intensity-g-per-kwh', type=float)
    p.add_argument('--out', default='checkpoints')
    args = p.parse_args()
    if args.keep_last_checkpoints < 1:
        raise RuntimeError('--keep-last-checkpoints must be >= 1')

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    raw = json.loads(Path(args.config).read_text())
    cfg = ModelConfig(**{k: v for k, v in raw.items() if k not in {'name', 'runtime_note'}})
    device = choose_device()
    use_bf16 = device == 'cuda' and torch.cuda.is_bf16_supported()
    use_fp16 = device == 'cuda' and not use_bf16
    precision = 'bf16' if use_bf16 else 'fp16' if use_fp16 else 'fp32'
    if use_bf16:
        autocast = lambda: torch.autocast(device_type='cuda', dtype=torch.bfloat16)
    elif use_fp16:
        autocast = lambda: torch.autocast(device_type='cuda', dtype=torch.float16)
    else:
        autocast = nullcontext
    scaler = torch.amp.GradScaler('cuda', enabled=use_fp16)

    model = DinavQF(cfg).to(device)
    model.set_gradient_checkpointing(args.gradient_checkpointing)
    dataset = TokenDataset(args.tokens, cfg.max_seq_len)
    if len(dataset) == 0:
        raise RuntimeError('token dataset is smaller than one sequence')
    stream = DeterministicBatchStream(dataset, args.micro_batch_size, args.seed)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)

    resume_step = 0
    tokens_seen = 0
    micro_batches_seen = 0
    resume_path = None
    if args.resume:
        resume_path = Path(args.resume).expanduser().resolve()
        if not resume_path.is_file():
            raise RuntimeError(f'resume checkpoint not found: {resume_path}')
        checkpoint_state = torch.load(resume_path, map_location=device, weights_only=False)
        if int(checkpoint_state.get('schedule_total_steps', args.steps)) != args.steps:
            raise RuntimeError('resume checkpoint schedule target differs from --steps; refusing LR-schedule discontinuity')
        if int(checkpoint_state.get('micro_batch_size', args.micro_batch_size)) != args.micro_batch_size or int(checkpoint_state.get('grad_accum', args.grad_accum)) != args.grad_accum:
            raise RuntimeError('resume checkpoint batch settings differ from current micro-batch/grad-accum settings')
        model.load_state_dict(checkpoint_state['model'])
        opt.load_state_dict(checkpoint_state['optimizer'])
        resume_step = int(checkpoint_state.get('step', 0))
        tokens_seen = int(checkpoint_state.get('tokens_seen', 0))
        micro_batches_seen = int(checkpoint_state.get('micro_batches_seen', resume_step * args.grad_accum))
        if use_fp16 and checkpoint_state.get('scaler'):
            scaler.load_state_dict(checkpoint_state['scaler'])
        if resume_step >= args.steps:
            raise RuntimeError(f'resume checkpoint already reached step {resume_step}, target is {args.steps}')
        print(json.dumps({'resume_from': str(resume_path), 'resume_step': resume_step, 'tokens_seen': tokens_seen, 'micro_batches_seen': micro_batches_seen}), flush=True)

    end_step = args.steps if args.stop_after_step is None else min(args.steps, args.stop_after_step)
    if end_step <= resume_step:
        raise RuntimeError('stop-after-step must be greater than the resumed step')

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run_manifest = build_manifest(args.config, args.tokens, args.seed)
    run_manifest.update({
        'status': 'RUNNING',
        'steps_target': args.steps,
        'planned_stop_step': end_step,
        'steps_resumed_from': resume_step,
        'resume_from': str(resume_path) if resume_path else None,
        'resume_determinism': 'exact deterministic batch cursor restored from seed/epoch/micro-batch index',
        'micro_batch_size': args.micro_batch_size,
        'grad_accum': args.grad_accum,
        'peak_lr': args.lr,
        'device': device,
        'precision': precision,
        'bf16': use_bf16,
        'fp16': use_fp16,
        'gradient_checkpointing': args.gradient_checkpointing,
        'checkpoint_retention': args.keep_last_checkpoints,
        'checkpoint_write_mode': 'atomic-temp-then-replace',
        'gpu_count': torch.cuda.device_count() if device == 'cuda' else 0,
        'apple_mps': device == 'mps',
        'average_gpu_watts': args.average_gpu_watts,
        'pue': args.pue,
        'carbon_intensity_g_per_kwh': args.carbon_intensity_g_per_kwh,
    })
    write_manifest(str(out / 'run-manifest.json'), run_manifest)

    model.train()
    started = time.time()
    session_tokens = 0
    last_loss = None
    opt.zero_grad(set_to_none=True)
    for step in range(resume_step + 1, end_step + 1):
        total_loss = 0.0
        for _ in range(args.grad_accum):
            x, y = stream.batch(micro_batches_seen)
            micro_batches_seen += 1
            x, y = x.to(device), y.to(device)
            with autocast():
                _, loss = model(x, y)
                if not torch.isfinite(loss):
                    raise RuntimeError(f'non-finite loss at step {step}')
                scaled_loss = loss / args.grad_accum
            if use_fp16:
                scaler.scale(scaled_loss).backward()
            else:
                scaled_loss.backward()
            total_loss += float(loss.detach())
            tokens_seen += x.numel()
            session_tokens += x.numel()

        if use_fp16:
            scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        lr = lr_for_step(step - 1, args.steps, args.lr, args.warmup_steps)
        for group in opt.param_groups:
            group['lr'] = lr
        if use_fp16:
            scaler.step(opt)
            scaler.update()
        else:
            opt.step()
        opt.zero_grad(set_to_none=True)
        last_loss = total_loss / args.grad_accum

        if step == resume_step + 1 or step % 10 == 0:
            elapsed = max(time.time() - started, 1e-9)
            print(json.dumps({'step': step, 'loss': round(last_loss, 6), 'lr': lr, 'tokens_seen': tokens_seen, 'session_tokens_per_second': round(session_tokens / elapsed, 2), 'device': device, 'precision': precision}), flush=True)
        if step % args.checkpoint_every == 0 or step == end_step:
            model_name = raw.get('name', 'dinav-qf')
            checkpoint_path = out / f"{model_name}-{step}.pt"
            save_checkpoint_atomic({
                'model': model.state_dict(),
                'optimizer': opt.state_dict(),
                'scaler': scaler.state_dict() if use_fp16 else None,
                'config': raw,
                'step': step,
                'tokens_seen': tokens_seen,
                'micro_batches_seen': micro_batches_seen,
                'micro_batch_size': args.micro_batch_size,
                'grad_accum': args.grad_accum,
                'schedule_total_steps': args.steps,
            }, checkpoint_path, model_name, args.keep_last_checkpoints)
            print(json.dumps({'checkpoint_saved': str(checkpoint_path), 'checkpoint_retention': args.keep_last_checkpoints}), flush=True)

    wall_seconds = time.time() - started
    energy_kwh = None
    estimated_co2_kg = None
    if device == 'cuda' and args.average_gpu_watts is not None:
        gpu_count = max(1, torch.cuda.device_count())
        energy_kwh = gpu_count * args.average_gpu_watts * (wall_seconds / 3600.0) * args.pue / 1000.0
        if args.carbon_intensity_g_per_kwh is not None:
            estimated_co2_kg = energy_kwh * args.carbon_intensity_g_per_kwh / 1000.0

    completed = end_step == args.steps
    run_manifest.update({
        'status': 'COMPLETED' if completed else 'PAUSED',
        'steps_completed': end_step,
        'tokens_seen': tokens_seen,
        'micro_batches_seen': micro_batches_seen,
        'session_tokens': session_tokens,
        'wall_seconds': wall_seconds,
        'final_loss': last_loss,
        'energy_kwh': energy_kwh,
        'estimated_co2_kg': estimated_co2_kg,
    })
    write_manifest(str(out / 'run-manifest.json'), run_manifest)


if __name__ == '__main__':
    main()
