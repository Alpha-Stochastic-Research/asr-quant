from __future__ import annotations

import hashlib
import html
import json
import math
import os
import random
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests
import torch
from tokenizers import Tokenizer

WORK = Path('/kaggle/working')
OUT = WORK / 'dinav_qf_quality_v1'
OUT.mkdir(parents=True, exist_ok=True)
STATUS = OUT / 'quality_status.json'
STACK_API = 'https://api.stackexchange.com/2.3'
CC_BY_SA_4 = 'https://creativecommons.org/licenses/by-sa/4.0/'
LICENSE_CUTOFF = 1525219200
SEED = 20260912
SFT_STEPS = 600
GRAD_ACCUM = 8
PEAK_LR = 5e-5
WARMUP = 30
MAX_SEQ = 768
MIN_FREE_GB = 5.0

QUERY_SPECS = [
    ('quant', None, 2),
    ('quant', 'fixed-income', 2),
    ('quant', 'interest-rates', 2),
    ('quant', 'derivatives', 2),
    ('quant', 'risk-management', 2),
    ('quant', 'options', 1),
    ('stats', None, 1),
    ('stats', 'probability', 2),
    ('stats', 'mathematical-statistics', 1),
    ('math', 'probability', 2),
]

EVALS = [
    ('prob-001', 'A fair coin is tossed twice. Give P(exactly one head) as a decimal.', 0.5, 1e-4, None),
    ('stats-001', 'For standard normal Z, give E[Z^2].', 1.0, 1e-4, None),
    ('fi-001', 'A zero coupon bond pays 100 in one year. Continuously compounded rate is 5%. Give price rounded to 4 decimals.', 100 * math.exp(-0.05), 1e-4, None),
    ('fi-002', 'A 1Y zero rate is 4% continuously compounded. Give the discount factor.', math.exp(-0.04), 1e-4, None),
    ('deriv-001', 'For a forward on a non-dividend asset with S0=100, continuously compounded r=5%, T=1, give fair delivery price.', 100 * math.exp(0.05), 1e-3, None),
    ('risk-001', 'State the two quantities needed for a historical 99% one-day VaR calculation.', None, None, ('loss', 'quantile')),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def disk_state() -> dict:
    usage = shutil.disk_usage(WORK)
    return {
        'total_gb': round(usage.total / 2**30, 2),
        'used_gb': round(usage.used / 2**30, 2),
        'free_gb': round(usage.free / 2**30, 2),
    }


def write_status(**extra) -> None:
    payload = {
        'project': 'DINAV-QF',
        'stage': '125M quality post-training',
        'external_llm_calls': 0,
        'base_weights': 'DINAV-QF-125M-1000',
        'semantic_training_text_sources': ['Stack Exchange CC BY-SA 4.0 posts only'],
        'generated_training_text_from_external_llm': False,
        'updated_at': now_iso(),
        'disk': disk_state(),
        **extra,
    }
    STATUS.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('QUALITY_STATUS', json.dumps(payload, sort_keys=True), flush=True)


def find_one(name: str) -> Path:
    candidates = [p for p in Path('/kaggle/input').rglob(name) if p.is_file()]
    if not candidates:
        raise FileNotFoundError(f'Unable to find {name} under /kaggle/input')
    candidates.sort(key=lambda p: (len(str(p)), str(p)))
    chosen = candidates[0]
    print('INPUT_FOUND', name, chosen, flush=True)
    return chosen


class TextExtractor(HTMLParser):
    BLOCK = {'p', 'br', 'div', 'li', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'tr'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {'script', 'style'}:
            self.skip += 1
        if not self.skip and tag in self.BLOCK:
            self.parts.append('\n')
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {'script', 'style'} and self.skip:
            self.skip -= 1
        if not self.skip and tag in self.BLOCK:
            self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(raw: str) -> str:
    parser = TextExtractor()
    parser.feed(raw or '')
    text = html.unescape(''.join(parser.parts))
    text = text.replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def api_get(session: requests.Session, path: str, params: dict) -> dict:
    for attempt in range(5):
        response = session.get(f'{STACK_API}{path}', params=params, timeout=60)
        if response.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        payload = response.json()
        backoff = payload.get('backoff')
        if backoff:
            time.sleep(float(backoff) + 1)
        return payload
    raise RuntimeError(f'Stack Exchange API repeatedly failed: {path}')


def build_stackexchange_corpus() -> tuple[Path, Path, list[dict], list[dict]]:
    session = requests.Session()
    session.headers.update({'User-Agent': 'DINAV-QF/0.2 (Alpha Stochastic Research; contact@asr-lab.online)'})
    questions: dict[tuple[str, int], dict] = {}
    quota_remaining = None

    for site, tag, pages in QUERY_SPECS:
        for page in range(1, pages + 1):
            params = {
                'site': site,
                'page': page,
                'pagesize': 100,
                'order': 'desc',
                'sort': 'votes',
                'fromdate': LICENSE_CUTOFF,
                'filter': 'withbody',
            }
            if tag:
                params['tagged'] = tag
            payload = api_get(session, '/questions', params)
            quota_remaining = payload.get('quota_remaining', quota_remaining)
            for q in payload.get('items', []):
                aid = q.get('accepted_answer_id')
                qid = q.get('question_id')
                if not aid or not qid:
                    continue
                if int(q.get('creation_date', 0)) < LICENSE_CUTOFF:
                    continue
                questions[(site, int(qid))] = q
            print('STACK_Q_PROGRESS', site, tag, page, 'QUESTIONS', len(questions), 'QUOTA', quota_remaining, flush=True)
            if not payload.get('has_more'):
                break

    by_site: dict[str, list[int]] = {}
    answer_to_question: dict[tuple[str, int], dict] = {}
    for (site, _), q in questions.items():
        aid = int(q['accepted_answer_id'])
        by_site.setdefault(site, []).append(aid)
        answer_to_question[(site, aid)] = q

    pairs: list[dict] = []
    for site, answer_ids in by_site.items():
        unique_ids = sorted(set(answer_ids))
        for start in range(0, len(unique_ids), 100):
            batch = unique_ids[start:start + 100]
            payload = api_get(session, '/answers/' + ';'.join(map(str, batch)), {
                'site': site,
                'pagesize': 100,
                'filter': 'withbody',
            })
            quota_remaining = payload.get('quota_remaining', quota_remaining)
            for answer in payload.get('items', []):
                aid = int(answer.get('answer_id', 0))
                q = answer_to_question.get((site, aid))
                if not q:
                    continue
                if int(answer.get('creation_date', 0)) < LICENSE_CUTOFF:
                    continue
                title = html_to_text(q.get('title', ''))
                qbody = html_to_text(q.get('body', ''))
                abody = html_to_text(answer.get('body', ''))
                if len(qbody) < 40 or len(abody) < 40:
                    continue
                prompt = (title + '\n\n' + qbody).strip()
                completion = abody.strip()
                if len(prompt) > 16000:
                    prompt = prompt[:16000]
                if len(completion) > 24000:
                    completion = completion[:24000]
                qid = int(q['question_id'])
                question_url = q.get('link') or f'https://{site}.stackexchange.com/questions/{qid}'
                owner = answer.get('owner') or {}
                record = {
                    'site': site,
                    'question_id': qid,
                    'accepted_answer_id': aid,
                    'prompt': prompt,
                    'completion': completion,
                    'source_uri': question_url,
                    'answer_uri': f'{question_url}#answer-{aid}',
                    'question_creation_unix': int(q.get('creation_date', 0)),
                    'answer_creation_unix': int(answer.get('creation_date', 0)),
                    'answer_author': owner.get('display_name'),
                    'answer_author_url': owner.get('link'),
                    'license_id': 'cc_by_sa_4_0',
                    'license_uri': CC_BY_SA_4,
                    'retrieved_time': now_iso(),
                    'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'completion_sha256': hashlib.sha256(completion.encode()).hexdigest(),
                }
                pairs.append(record)
            print('STACK_A_PROGRESS', site, start, 'PAIRS', len(pairs), 'QUOTA', quota_remaining, flush=True)

    if len(pairs) < 250:
        raise RuntimeError(f'Insufficient accepted CC BY-SA Q/A pairs: {len(pairs)}')

    eval_canon = {re.sub(r'\s+', ' ', prompt.lower()).strip() for _, prompt, *_ in EVALS}
    filtered = []
    contamination = []
    for pair in pairs:
        canon = re.sub(r'\s+', ' ', pair['prompt'].lower()).strip()
        hit = any(e in canon or canon in e for e in eval_canon)
        if hit:
            contamination.append({'site': pair['site'], 'question_id': pair['question_id']})
        else:
            filtered.append(pair)
    pairs = filtered

    train, val = [], []
    for pair in pairs:
        key = f"{pair['site']}:{pair['question_id']}:{pair['accepted_answer_id']}"
        bucket = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 10
        (val if bucket == 0 else train).append(pair)
    if len(train) < 200 or len(val) < 20:
        raise RuntimeError(f'Post-split Q/A corpus too small: train={len(train)}, val={len(val)}')

    train_path = OUT / 'stackexchange_sft_train.jsonl'
    val_path = OUT / 'stackexchange_sft_validation.jsonl'
    with train_path.open('w', encoding='utf-8') as f:
        for x in train:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    with val_path.open('w', encoding='utf-8') as f:
        for x in val:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    manifest = {
        'created_at': now_iso(),
        'license_policy': 'Only posts created on/after 2018-05-02 UTC; Stack Exchange Help Center identifies these contributions as CC BY-SA 4.0.',
        'license_uri': CC_BY_SA_4,
        'external_llm_calls': 0,
        'semantic_text_generation': 'none',
        'format_only_separator': 'two newline characters between source question and accepted answer',
        'query_specs': QUERY_SPECS,
        'pairs_total': len(pairs),
        'train_pairs': len(train),
        'validation_pairs': len(val),
        'exact_eval_prompt_contamination_hits': contamination,
        'quota_remaining_last_seen': quota_remaining,
        'train_sha256': sha256_file(train_path),
        'validation_sha256': sha256_file(val_path),
    }
    (OUT / 'stackexchange_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('STACK_CORPUS_READY', json.dumps(manifest, sort_keys=True), flush=True)
    return train_path, val_path, train, val


@dataclass
class Example:
    input_ids: list[int]
    labels: list[int]


def make_example(tok: Tokenizer, prompt: str, completion: str, bos: int, eos: int) -> Example | None:
    pids = tok.encode(prompt + '\n\n').ids
    aids = tok.encode(completion).ids
    if not pids or not aids:
        return None
    max_content = MAX_SEQ - 2
    if len(pids) + len(aids) > max_content:
        prompt_budget = min(len(pids), max(128, max_content // 2))
        answer_budget = max_content - prompt_budget
        pids = pids[:prompt_budget]
        aids = aids[:answer_budget]
    seq = [bos] + pids + aids + [eos]
    inputs = seq[:-1]
    labels = seq[1:]
    first_answer_target = len([bos] + pids) - 1
    labels[:first_answer_target] = [-100] * first_answer_target
    return Example(inputs, labels)


def lr_for_step(step: int) -> float:
    if step < WARMUP:
        return PEAK_LR * (step + 1) / WARMUP
    progress = min(1.0, (step - WARMUP) / max(1, SFT_STEPS - WARMUP))
    return PEAK_LR * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * progress)))


def choose_device() -> str:
    return 'cuda' if torch.cuda.is_available() else 'cpu'


def number_hits(answer: str, target: float, tol: float) -> bool:
    vals = re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', answer.replace(',', ''))
    for raw in vals:
        try:
            if abs(float(raw) - target) <= tol:
                return True
        except Exception:
            pass
    return False


def markup_artifact(answer: str) -> bool:
    low = answer.lower()
    return any(x in low for x in ('[[category:', '==references==', '{{reflist', '{{finance-stub', '[[', ']]'))


def generate(model, tok: Tokenizer, cfg, prompt: str, device: str, max_new: int = 64) -> str:
    bos = tok.token_to_id('<bos>')
    eos = tok.token_to_id('<eos>')
    ids = [bos] + tok.encode(prompt + '\n\n').ids
    generated = []
    with torch.inference_mode():
        for _ in range(max_new):
            x = torch.tensor([ids[-cfg.max_seq_len:]], dtype=torch.long, device=device)
            with torch.autocast(device_type='cuda', dtype=torch.bfloat16, enabled=(device == 'cuda' and torch.cuda.is_bf16_supported())):
                logits = model(x)
            nxt = int(torch.argmax(logits[0, -1]).item())
            if nxt == eos:
                break
            ids.append(nxt)
            generated.append(nxt)
    return tok.decode(generated, skip_special_tokens=True)


def main() -> None:
    print('DINAV-QF 125M QUALITY STAGE', flush=True)
    print('DISK_START', json.dumps(disk_state()), flush=True)
    checkpoint = find_one('DINAV-QF-125M-1000.pt')
    tokenizer_path = find_one('dinav_qf_tokenizer.json')
    config_candidates = [p for p in Path('/kaggle/input').rglob('pilot-runtime-config.json') if p.is_file()]
    if not config_candidates:
        config_candidates = [p for p in Path('/kaggle/input').rglob('dinav_qf_125m.json') if p.is_file()]
    if not config_candidates:
        raise FileNotFoundError('No 125M runtime config found in v6 kernel source')
    config_path = sorted(config_candidates, key=lambda p: (len(str(p)), str(p)))[0]
    print('INPUT_FOUND config', config_path, flush=True)

    source_root_candidates = [p.parent.parent for p in Path('/kaggle/input').rglob('training/model.py')]
    if not source_root_candidates:
        raise FileNotFoundError('Unable to find DINAV-QF source root in v6 kernel output')
    source_root = sorted(source_root_candidates, key=lambda p: (len(str(p)), str(p)))[0]
    sys.path.insert(0, str(source_root / 'training'))
    from model import DinavQF, ModelConfig

    raw_cfg = json.loads(config_path.read_text(encoding='utf-8'))
    raw_cfg['max_seq_len'] = min(int(raw_cfg.get('max_seq_len', 1024)), MAX_SEQ)
    cfg = ModelConfig(**{k: v for k, v in raw_cfg.items() if k not in {'name', 'runtime_note'}})
    tok = Tokenizer.from_file(str(tokenizer_path))
    if tok.get_vocab_size() != cfg.vocab_size:
        raise RuntimeError(f'Tokenizer/config mismatch: {tok.get_vocab_size()} != {cfg.vocab_size}')

    write_status(status='BUILDING_CC_BY_SA_SFT_CORPUS', base_checkpoint_sha256=sha256_file(checkpoint))
    _, _, train_rows, val_rows = build_stackexchange_corpus()

    bos = tok.token_to_id('<bos>')
    eos = tok.token_to_id('<eos>')
    if bos is None or eos is None:
        raise RuntimeError('Tokenizer lacks bos/eos tokens')
    train_examples = [ex for row in train_rows if (ex := make_example(tok, row['prompt'], row['completion'], bos, eos))]
    val_examples = [ex for row in val_rows if (ex := make_example(tok, row['prompt'], row['completion'], bos, eos))]
    if len(train_examples) < 200 or len(val_examples) < 20:
        raise RuntimeError(f'Insufficient tokenized SFT examples: {len(train_examples)}/{len(val_examples)}')
    print('SFT_EXAMPLES', len(train_examples), len(val_examples), flush=True)

    device = choose_device()
    ck = torch.load(checkpoint, map_location=device, weights_only=False)
    model = DinavQF(cfg).to(device)
    model.load_state_dict(ck['model'])
    model.set_gradient_checkpointing(True)
    model.train()
    use_bf16 = device == 'cuda' and torch.cuda.is_bf16_supported()
    use_fp16 = device == 'cuda' and not use_bf16
    scaler = torch.amp.GradScaler('cuda', enabled=use_fp16)
    optimizer = torch.optim.AdamW(model.parameters(), lr=PEAK_LR, betas=(0.9, 0.95), weight_decay=0.01)
    rng = random.Random(SEED)
    order = list(range(len(train_examples)))
    rng.shuffle(order)
    cursor = 0
    started = time.time()
    answer_tokens_seen = 0
    last_loss = None
    optimizer.zero_grad(set_to_none=True)
    write_status(status='SFT_RUNNING', train_pairs=len(train_examples), validation_pairs=len(val_examples), step=0)

    for step in range(1, SFT_STEPS + 1):
        total = 0.0
        for _ in range(GRAD_ACCUM):
            if cursor >= len(order):
                rng.shuffle(order)
                cursor = 0
            ex = train_examples[order[cursor]]
            cursor += 1
            x = torch.tensor([ex.input_ids], dtype=torch.long, device=device)
            y = torch.tensor([ex.labels], dtype=torch.long, device=device)
            if use_bf16:
                ctx = torch.autocast(device_type='cuda', dtype=torch.bfloat16)
            elif use_fp16:
                ctx = torch.autocast(device_type='cuda', dtype=torch.float16)
            else:
                from contextlib import nullcontext
                ctx = nullcontext()
            with ctx:
                _, loss = model(x, y)
                if not torch.isfinite(loss):
                    raise RuntimeError(f'Non-finite SFT loss at step {step}')
                scaled = loss / GRAD_ACCUM
            if use_fp16:
                scaler.scale(scaled).backward()
            else:
                scaled.backward()
            total += float(loss.detach())
            answer_tokens_seen += sum(1 for v in ex.labels if v != -100)
        if use_fp16:
            scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        lr = lr_for_step(step - 1)
        for group in optimizer.param_groups:
            group['lr'] = lr
        if use_fp16:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        last_loss = total / GRAD_ACCUM
        if step == 1 or step % 10 == 0:
            elapsed = max(time.time() - started, 1e-9)
            print('SFT_STEP', json.dumps({
                'step': step,
                'loss': round(last_loss, 6),
                'lr': lr,
                'answer_tokens_seen': answer_tokens_seen,
                'answer_tokens_per_second': round(answer_tokens_seen / elapsed, 2),
                'disk': disk_state(),
            }, sort_keys=True), flush=True)
        if disk_state()['free_gb'] < MIN_FREE_GB:
            raise RuntimeError(f'Disk guard: free disk below {MIN_FREE_GB} GB')

    model.eval()
    losses = []
    with torch.inference_mode():
        for ex in val_examples[:64]:
            x = torch.tensor([ex.input_ids], dtype=torch.long, device=device)
            y = torch.tensor([ex.labels], dtype=torch.long, device=device)
            if use_bf16:
                with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
                    _, loss = model(x, y)
            else:
                _, loss = model(x, y)
            losses.append(float(loss))
    validation_loss = sum(losses) / len(losses)

    final_ckpt = OUT / 'DINAV-QF-125M-QUALITY-SFT-600.pt'
    torch.save({
        'model': model.state_dict(),
        'config': raw_cfg,
        'step': 1000,
        'quality_sft_steps': SFT_STEPS,
        'base_checkpoint_sha256': sha256_file(checkpoint),
        'stackexchange_manifest_sha256': sha256_file(OUT / 'stackexchange_manifest.json'),
        'external_llm_calls': 0,
    }, final_ckpt)

    eval_cases = []
    passed_count = 0
    clean_count = 0
    for case_id, prompt, target, tol, terms in EVALS:
        answer = generate(model, tok, cfg, prompt, device)
        if terms:
            passed = all(t.lower() in answer.lower() for t in terms)
        else:
            passed = number_hits(answer, float(target), float(tol))
        clean = not markup_artifact(answer)
        passed_count += int(passed)
        clean_count += int(clean)
        eval_cases.append({'id': case_id, 'prompt': prompt, 'answer': answer, 'passed': passed, 'clean': clean})
        print('QUALITY_EVAL_CASE', json.dumps(eval_cases[-1], ensure_ascii=False), flush=True)

    overall = passed_count / len(EVALS)
    clean_rate = clean_count / len(EVALS)
    gate = {
        'passed': overall >= 0.5 and clean_rate >= 0.9 and math.isfinite(validation_loss),
        'model_eval_overall': overall,
        'minimum_model_eval': 0.5,
        'clean_output_rate': clean_rate,
        'minimum_clean_output_rate': 0.9,
        'sft_validation_loss': validation_loss,
        'train_pairs': len(train_examples),
        'validation_pairs': len(val_examples),
        'external_llm_calls': 0,
        'scale_1_3b_unlocked': overall >= 0.5 and clean_rate >= 0.9 and math.isfinite(validation_loss),
    }
    result = {
        'base_checkpoint': str(checkpoint),
        'base_checkpoint_sha256': sha256_file(checkpoint),
        'final_checkpoint': str(final_ckpt),
        'final_checkpoint_sha256': sha256_file(final_ckpt),
        'sft_steps': SFT_STEPS,
        'final_sft_loss': last_loss,
        'sft_validation_loss': validation_loss,
        'answer_tokens_seen': answer_tokens_seen,
        'wall_seconds': time.time() - started,
        'device': device,
        'precision': 'bf16' if use_bf16 else 'fp16' if use_fp16 else 'fp32',
        'eval': {'overall': overall, 'clean_rate': clean_rate, 'cases': eval_cases},
        'quality_gate': gate,
        'disk_final': disk_state(),
    }
    (OUT / 'quality_eval.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    write_status(status='COMPLETED', quality_gate=gate, final_checkpoint_sha256=result['final_checkpoint_sha256'], final_sft_loss=last_loss, sft_validation_loss=validation_loss)
    print('QUALITY_RESULT', json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
