import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

import requests

CHUNK_URLS = [
    f'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/dinav-qf-kaggle-bootstrap/dinav-qf-bootstrap/chunk_{i:02d}.b64'
    for i in range(7)
]
EXPECTED_CHUNK_LENGTHS = [8000, 8000, 8000, 8000, 8000, 8000, 1456]
EXPECTED_B64_LENGTH = 49456
EXPECTED_BUNDLE_SHA256 = 'a6a80972ac5eb8ece2a4da5effaf77a11d2076466ef7de9bb1578531b4a864e6'
TRAINER_URL = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/dinav-qf-kaggle-bootstrap/dinav-qf-kaggle-cli/train_diskfixed.py'
EXPECTED_TRAINER_SHA256 = '180692a779563537e06d0622b7653f73d65ce3eab50fe2efd25f52c4b3b5593b'
WORK = Path('/kaggle/working')
INPUT = Path('/kaggle/input')
ZIP_PATH = WORK / 'dinav_qf_zero_cost_v3_fixed.zip'
ROOT = WORK / 'dinav_qf_zero_cost_v3'
PILOT_WORK = ROOT / 'runs' / 'zero-cost-125m-pilot'
CHECKPOINT_DIR = PILOT_WORK / 'pilot'
STATUS_PATH = WORK / 'dinav_qf_125m_pilot_status.json'


def sha256_file(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_status(**kwargs):
    payload = {
        'project': 'DINAV-QF',
        'stage': '125M pilot resume',
        'research_weights_status': 'NOT_TRAINED',
        'pilot_checkpoint_status': 'IN_PROGRESS',
        'external_llm_calls': 0,
        **kwargs,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('STATUS_JSON', json.dumps(payload, sort_keys=True), flush=True)


def run(*args: str):
    print('+', ' '.join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def disk_free_gb():
    return shutil.disk_usage(WORK).free / (1024 ** 3)


def find_named(name: str, prefer_fragment: str = 'zero-cost-125m-pilot') -> Path:
    matches = [p for p in INPUT.rglob(name) if p.is_file()]
    if not matches:
        raise FileNotFoundError(f'Previous kernel output missing required file: {name}')
    preferred = [p for p in matches if prefer_fragment in str(p)]
    chosen = preferred[0] if preferred else matches[0]
    print('INPUT_ARTIFACT', name, chosen, 'BYTES', chosen.stat().st_size, flush=True)
    return chosen


def find_latest_resume_checkpoint() -> tuple[Path, int]:
    pattern = re.compile(r'^DINAV-QF-125M-(\d+)\.pt$')
    candidates = []
    for p in INPUT.rglob('DINAV-QF-125M-*.pt'):
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if not m:
            continue
        step = int(m.group(1))
        if step < 1000:
            candidates.append((step, p))
    if not candidates:
        raise FileNotFoundError('No resumable DINAV-QF-125M checkpoint found in Kaggle input sources')
    candidates.sort(key=lambda x: x[0], reverse=True)
    step, path = candidates[0]
    print('RESUME_CHECKPOINT_INPUT', path, 'STEP', step, 'BYTES', path.stat().st_size, 'SHA256', sha256_file(path), flush=True)
    return path, step


def copy_artifact(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print('COPIED', src, '->', dst, 'BYTES', dst.stat().st_size, flush=True)


print('DINAV-QF 125M PILOT RESUME V5', flush=True)
print('Python', sys.version, flush=True)
print('DISK_FREE_GB_START', round(disk_free_gb(), 3), flush=True)
try:
    import torch
    print('Torch', torch.__version__, flush=True)
    print('CUDA_AVAILABLE', torch.cuda.is_available(), flush=True)
    print('CUDA_DEVICE_COUNT', torch.cuda.device_count(), flush=True)
    for i in range(torch.cuda.device_count()):
        print('GPU', i, torch.cuda.get_device_name(i), flush=True)
except Exception as exc:
    print('TORCH_INFO_ERROR', repr(exc), flush=True)

try:
    parts = []
    for index, (url, expected_length) in enumerate(zip(CHUNK_URLS, EXPECTED_CHUNK_LENGTHS)):
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        part = r.text.strip()
        if len(part) != expected_length:
            raise RuntimeError(f'Chunk {index} length mismatch: {len(part)} != {expected_length}')
        parts.append(part)
    encoded = ''.join(parts)
    if len(encoded) != EXPECTED_B64_LENGTH:
        raise RuntimeError(f'Unexpected bundle base64 length: {len(encoded)} != {EXPECTED_B64_LENGTH}')
    blob = base64.b64decode(encoded, validate=True)
    bundle_sha = hashlib.sha256(blob).hexdigest()
    if bundle_sha != EXPECTED_BUNDLE_SHA256:
        raise RuntimeError(f'Bundle SHA mismatch: {bundle_sha} != {EXPECTED_BUNDLE_SHA256}')
    ZIP_PATH.write_bytes(blob)
    if not zipfile.is_zipfile(ZIP_PATH):
        raise RuntimeError('Decoded bundle is not a valid ZIP')
    if ROOT.exists():
        shutil.rmtree(ROOT)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f'ZIP integrity failure at {bad}')
        zf.extractall(WORK)
    ZIP_PATH.unlink(missing_ok=True)

    trainer_response = requests.get(TRAINER_URL, timeout=60)
    trainer_response.raise_for_status()
    trainer_bytes = trainer_response.content
    trainer_sha = hashlib.sha256(trainer_bytes).hexdigest()
    if trainer_sha != EXPECTED_TRAINER_SHA256:
        raise RuntimeError(f'Disk-safe trainer SHA mismatch: {trainer_sha} != {EXPECTED_TRAINER_SHA256}')
    trainer_path = ROOT / 'training' / 'train.py'
    trainer_path.write_bytes(trainer_bytes)
    print('DISK_SAFE_TRAINER_READY', trainer_path, trainer_sha, flush=True)

    resume_input, resume_step = find_latest_resume_checkpoint()
    if resume_step < 700:
        raise RuntimeError(f'Latest available checkpoint is only step {resume_step}; expected at least 700 from v4')

    config_src = find_named('pilot-runtime-config.json')
    train_src = find_named('train.bin')
    validation_src = find_named('validation.bin')
    tokenizer_src = find_named('dinav_qf_tokenizer.json')
    train_meta_src = find_named('train.meta.json')
    validation_meta_src = find_named('validation.meta.json')
    contamination_src = find_named('contamination.json')
    corpus_manifest_src = find_named('corpus-manifest.json')

    config = PILOT_WORK / 'pilot-runtime-config.json'
    train_tokens = PILOT_WORK / 'train.bin'
    validation_tokens = PILOT_WORK / 'validation.bin'
    tokenizer = PILOT_WORK / 'dinav_qf_tokenizer.json'
    train_meta = PILOT_WORK / 'train.meta.json'
    validation_meta = PILOT_WORK / 'validation.meta.json'
    contamination = PILOT_WORK / 'contamination.json'
    corpus_manifest = PILOT_WORK / 'corpus' / 'corpus-manifest.json'
    resume_checkpoint = CHECKPOINT_DIR / resume_input.name

    for src, dst in [
        (config_src, config),
        (train_src, train_tokens),
        (validation_src, validation_tokens),
        (tokenizer_src, tokenizer),
        (train_meta_src, train_meta),
        (validation_meta_src, validation_meta),
        (contamination_src, contamination),
        (corpus_manifest_src, corpus_manifest),
        (resume_input, resume_checkpoint),
    ]:
        copy_artifact(src, dst)

    if sha256_file(resume_checkpoint) != sha256_file(resume_input):
        raise RuntimeError('Copied resume checkpoint hash mismatch')
    if disk_free_gb() < 4.0:
        raise RuntimeError(f'Insufficient free disk before resume: {disk_free_gb():.2f} GB')
except Exception as exc:
    write_status(status='BOOTSTRAP_FAILED', error_type=type(exc).__name__, error_message=str(exc), completed_at_unix=time.time())
    raise

write_status(
    status='RUNNING',
    pilot_checkpoint_status='RESUMING',
    bundle_sha256=bundle_sha,
    trainer_sha256=trainer_sha,
    resume_step=resume_step,
    resume_checkpoint=str(resume_checkpoint),
    resume_checkpoint_sha256=sha256_file(resume_checkpoint),
    disk_free_gb=round(disk_free_gb(), 3),
    started_at_unix=time.time(),
)

start = time.time()
try:
    run(sys.executable, 'training/preflight.py')
    run(
        sys.executable,
        'training/train.py',
        '--config', str(config),
        '--tokens', str(train_tokens),
        '--out', str(CHECKPOINT_DIR),
        '--steps', '1000',
        '--micro-batch-size', '1',
        '--grad-accum', '16',
        '--lr', '3e-4',
        '--warmup-steps', '100',
        '--checkpoint-every', '50',
        '--keep-last-checkpoints', '1',
        '--gradient-checkpointing',
        '--resume', str(resume_checkpoint),
    )

    final_checkpoint = CHECKPOINT_DIR / 'DINAV-QF-125M-1000.pt'
    if not final_checkpoint.is_file():
        raise FileNotFoundError(final_checkpoint)
    if disk_free_gb() < 2.0:
        raise RuntimeError(f'Insufficient free disk after training: {disk_free_gb():.2f} GB')

    eval_path = PILOT_WORK / 'pilot-eval.json'
    validation_path = PILOT_WORK / 'pilot-validation.json'
    run(sys.executable, 'eval/model_eval.py', '--checkpoint', str(final_checkpoint), '--config', str(config), '--tokenizer', str(tokenizer), '--out', str(eval_path))
    run(sys.executable, 'training/validate_checkpoint.py', '--checkpoint', str(final_checkpoint), '--config', str(config), '--tokens', str(validation_tokens), '--out', str(validation_path), '--max-batches', '32', '--eval-seq-len', '256')

    run_manifest = CHECKPOINT_DIR / 'run-manifest.json'
    manifest = json.loads(run_manifest.read_text(encoding='utf-8'))
    eval_result = json.loads(eval_path.read_text(encoding='utf-8'))
    validation_result = json.loads(validation_path.read_text(encoding='utf-8'))
    elapsed = time.time() - start
    write_status(
        status='COMPLETED',
        pilot_checkpoint_status='TRAINED_AND_VALIDATED',
        research_weights_status='NOT_TRAINED',
        resume_step=resume_step,
        final_step=manifest.get('steps_completed'),
        tokens_seen=manifest.get('tokens_seen'),
        final_train_loss=manifest.get('final_loss'),
        wall_seconds=manifest.get('wall_seconds'),
        session_elapsed_seconds=elapsed,
        final_checkpoint=str(final_checkpoint),
        final_checkpoint_sha256=sha256_file(final_checkpoint),
        eval_path=str(eval_path),
        eval_overall=eval_result.get('overall'),
        validation_path=str(validation_path),
        validation_loss=validation_result.get('validation_loss'),
        validation_perplexity=validation_result.get('perplexity'),
        tokenizer_sha256=sha256_file(tokenizer),
        corpus_manifest=str(corpus_manifest),
        contamination=str(contamination),
        disk_free_gb=round(disk_free_gb(), 3),
        completed_at_unix=time.time(),
    )
except Exception as exc:
    elapsed = time.time() - start
    checkpoints = []
    pattern = re.compile(r'^DINAV-QF-125M-(\d+)\.pt$')
    for p in CHECKPOINT_DIR.glob('DINAV-QF-125M-*.pt') if CHECKPOINT_DIR.exists() else []:
        m = pattern.match(p.name)
        if m:
            checkpoints.append((int(m.group(1)), p))
    checkpoints.sort(reverse=True)
    latest = checkpoints[0][1] if checkpoints else None
    write_status(
        status='FAILED',
        pilot_checkpoint_status='RESUME_FAILED',
        error_type=type(exc).__name__,
        error_message=str(exc),
        latest_checkpoint=str(latest) if latest else None,
        latest_checkpoint_sha256=sha256_file(latest) if latest else None,
        disk_free_gb=round(disk_free_gb(), 3),
        elapsed_seconds=elapsed,
        completed_at_unix=time.time(),
    )
    raise
