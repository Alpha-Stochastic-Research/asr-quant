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

BUNDLE_URL = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/dinav-qf-kaggle-bootstrap/dinav-qf-bootstrap/dinav_qf_zero_cost_v3_fixed.b64'
EXPECTED_B64_LENGTH = 49456
EXPECTED_SHA256 = 'a6a80972ac5eb8ece2a4da5effaf77a11d2076466ef7de9bb1578531b4a864e6'
WORK = Path('/kaggle/working')
ZIP_PATH = WORK / 'dinav_qf_zero_cost_v3_fixed.zip'
ROOT = WORK / 'dinav_qf_zero_cost_v3'
STATUS_PATH = WORK / 'dinav_qf_125m_pilot_status.json'


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

resp = requests.get(BUNDLE_URL, timeout=60)
resp.raise_for_status()
text = resp.text.strip()
print('B64_LENGTH', len(text), flush=True)
if len(text) != EXPECTED_B64_LENGTH:
    raise RuntimeError(f'Unexpected base64 length: {len(text)} != {EXPECTED_B64_LENGTH}')

blob = base64.b64decode(text)
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
    zf.extractall(WORK)

pilot = ROOT / 'zero_cost' / 'pilot.py'
if not pilot.exists():
    raise FileNotFoundError(pilot)

print('BUNDLE_READY', ROOT, flush=True)
write_status(status='RUNNING', bundle_sha256=sha, started_at_unix=time.time())

env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'
start = time.time()
proc = subprocess.Popen(
    [sys.executable, str(pilot)],
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

checkpoints = sorted((ROOT / 'checkpoints').glob('*.pt'), key=lambda p: p.stat().st_mtime) if (ROOT / 'checkpoints').exists() else []
latest_checkpoint = str(checkpoints[-1]) if checkpoints else None
latest_checkpoint_sha256 = None
if checkpoints:
    h = hashlib.sha256()
    with checkpoints[-1].open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    latest_checkpoint_sha256 = h.hexdigest()

status = 'COMPLETED' if exit_code == 0 else 'FAILED'
write_status(
    status=status,
    exit_code=exit_code,
    elapsed_seconds=elapsed,
    bundle_sha256=sha,
    latest_output_line=last_line,
    latest_checkpoint=latest_checkpoint,
    latest_checkpoint_sha256=latest_checkpoint_sha256,
    completed_at_unix=time.time(),
)

if exit_code != 0:
    raise SystemExit(exit_code)
