import base64
import hashlib
import json
import os
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
EXPECTED_SHA256 = 'a6a80972ac5eb8ece2a4da5effaf77a11d2076466ef7de9bb1578531b4a864e6'
WORK = Path('/kaggle/working')
ZIP_PATH = WORK / 'dinav_qf_zero_cost_v3_fixed.zip'
ROOT = WORK / 'dinav_qf_zero_cost_v3'
STATUS_PATH = WORK / 'dinav_qf_125m_pilot_status.json'
RAW_CORPUS = ROOT / 'data' / 'smoke_authorized.jsonl'
PILOT_WORK_DIR = ROOT / 'runs' / 'zero-cost-125m-pilot'
CHECKPOINT_DIR = PILOT_WORK_DIR / 'pilot'


def write_status(**kwargs):
    payload = {
        'project': 'DINAV-QF',
        'stage': '125M pilot',
        'research_weights_status': 'NOT_TRAINED',
        'external_llm_calls': 0,
        **kwargs,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('STATUS_JSON', json.dumps(payload, sort_keys=True), flush=True)


def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


print('DINAV-QF 125M PILOT BOOTSTRAP', flush=True)
print('Python', sys.version, flush=True)
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
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        part = response.text.strip()
        print('CHUNK', index, 'LENGTH', len(part), flush=True)
        if len(part) != expected_length:
            raise RuntimeError(f'Chunk {index} length mismatch: {len(part)} != {expected_length}')
        parts.append(part)

    text = ''.join(parts)
    print('B64_LENGTH', len(text), flush=True)
    if len(text) != EXPECTED_B64_LENGTH:
        raise RuntimeError(f'Unexpected base64 length: {len(text)} != {EXPECTED_B64_LENGTH}')

    blob = base64.b64decode(text, validate=True)
    sha = hashlib.sha256(blob).hexdigest()
    print('BUNDLE_SHA256', sha, flush=True)
    if sha != EXPECTED_SHA256:
        raise RuntimeError(f'Bundle SHA mismatch: {sha} != {EXPECTED_SHA256}')

    ZIP_PATH.write_bytes(blob)
    if not zipfile.is_zipfile(ZIP_PATH):
        raise RuntimeError('Decoded bundle is not a valid ZIP')

    if ROOT.exists():
        shutil.rmtree(ROOT)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            raise RuntimeError(f'ZIP integrity failure at {bad_member}')
        zf.extractall(WORK)

    pilot = ROOT / 'zero_cost' / 'pilot.py'
    if not pilot.is_file():
        raise FileNotFoundError(pilot)
    if not RAW_CORPUS.is_file():
        raise FileNotFoundError(RAW_CORPUS)
except Exception as exc:
    write_status(
        status='BOOTSTRAP_FAILED',
        error_type=type(exc).__name__,
        error_message=str(exc),
        completed_at_unix=time.time(),
    )
    raise

print('BUNDLE_READY', ROOT, flush=True)
print('RAW_CORPUS', RAW_CORPUS, 'BYTES', RAW_CORPUS.stat().st_size, flush=True)
write_status(
    status='RUNNING',
    bundle_sha256=sha,
    raw_corpus=str(RAW_CORPUS),
    raw_corpus_bytes=RAW_CORPUS.stat().st_size,
    started_at_unix=time.time(),
)

env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'
start = time.time()
proc = subprocess.Popen(
    [
        sys.executable,
        str(pilot),
        '--raw',
        str(RAW_CORPUS),
        '--work-dir',
        str(PILOT_WORK_DIR),
    ],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    env=env,
)

last_line = ''
assert proc.stdout is not None
for line in proc.stdout:
    last_line = line.rstrip('\n')
    print(last_line, flush=True)

exit_code = proc.wait()
elapsed = time.time() - start

checkpoints = sorted(
    CHECKPOINT_DIR.glob('DINAV-QF-125M-*.pt'),
    key=lambda path: path.stat().st_mtime,
) if CHECKPOINT_DIR.exists() else []
latest_checkpoint = checkpoints[-1] if checkpoints else None
final_checkpoint = CHECKPOINT_DIR / 'DINAV-QF-125M-1000.pt'
validation_path = PILOT_WORK_DIR / 'pilot-validation.json'
eval_path = PILOT_WORK_DIR / 'pilot-eval.json'
corpus_manifest_path = PILOT_WORK_DIR / 'corpus' / 'corpus-manifest.json'

status = 'COMPLETED' if exit_code == 0 else 'FAILED'
write_status(
    status=status,
    exit_code=exit_code,
    elapsed_seconds=elapsed,
    bundle_sha256=sha,
    latest_output_line=last_line,
    latest_checkpoint=str(latest_checkpoint) if latest_checkpoint else None,
    latest_checkpoint_sha256=sha256_file(latest_checkpoint) if latest_checkpoint else None,
    final_checkpoint=str(final_checkpoint) if final_checkpoint.is_file() else None,
    final_checkpoint_sha256=sha256_file(final_checkpoint),
    validation_path=str(validation_path) if validation_path.is_file() else None,
    eval_path=str(eval_path) if eval_path.is_file() else None,
    corpus_manifest_path=str(corpus_manifest_path) if corpus_manifest_path.is_file() else None,
    completed_at_unix=time.time(),
)

if exit_code != 0:
    raise SystemExit(exit_code)
