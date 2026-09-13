import glob
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests
import torch

CHECKPOINT_NAME = 'DINAV-QF-125M-1000.pt'
TOKENIZER_NAME = 'dinav_qf_tokenizer.json'
EXPECTED_SOURCE_SHA256 = 'c8b3c7a73da75cba6c5a02db21b7964c05b677c40b8d2118530e2dcaf1642b8f'
EXPECTED_STEP = 1000
EXPECTED_PARAMS = 124_988_160
SUPABASE_URL = 'https://iajqfonieeqfaabmhepc.supabase.co'
SUPABASE_KEY = 'sb_publishable_ezIMrdvZJRlqEgPVkEV8nw_9jRUudFJ'
BUCKET = 'axiom-transfer-7930c7715eae'
PREFIX = 'UPiyZw0SGkEsRNHU38O3xS7R'
CHUNK_SIZE = 40 * 1024 * 1024
WORK = Path('/kaggle/working/axiom-shards')
WORK.mkdir(parents=True, exist_ok=True)
STATUS = WORK / 'transfer-status.json'

status = {'stage': 'STARTING'}


def report(**updates):
    status.update(updates)
    STATUS.write_text(json.dumps(status, indent=2), encoding='utf-8')
    print('AXIOM_SHARD_TRANSFER', json.dumps(status, sort_keys=True), flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def upload_file(path: Path, remote_name: str, content_type: str):
    object_path = PREFIX + '/' + remote_name
    url = SUPABASE_URL + '/storage/v1/object/' + BUCKET + '/' + quote(object_path, safe='/')
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': content_type,
        'cache-control': 'max-age=60',
        'x-upsert': 'false',
    }
    payload = path.read_bytes()
    last_error = None
    for attempt in range(1, 5):
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=180)
            if response.status_code in (200, 201):
                return response.text[:500]
            last_error = f'HTTP {response.status_code}: {response.text[:1000]}'
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(min(15, attempt * 3))
    raise RuntimeError(f'upload failed for {remote_name}: {last_error}')


ckpts = glob.glob('/kaggle/input/**/' + CHECKPOINT_NAME, recursive=True)
tokenizers = glob.glob('/kaggle/input/**/' + TOKENIZER_NAME, recursive=True)
if not ckpts or not tokenizers:
    report(stage='INPUT_NOT_FOUND', checkpoint_matches=ckpts, tokenizer_matches=tokenizers)
    raise SystemExit(2)

source = Path(ckpts[0])
tokenizer = Path(tokenizers[0])
report(stage='SOURCE_FOUND', source_bytes=source.stat().st_size, tokenizer_bytes=tokenizer.stat().st_size)

source_sha = sha256_file(source)
if source_sha != EXPECTED_SOURCE_SHA256:
    report(stage='SOURCE_HASH_MISMATCH', source_sha256=source_sha, expected=EXPECTED_SOURCE_SHA256)
    raise SystemExit(3)
report(stage='SOURCE_HASH_OK', source_sha256=source_sha)

checkpoint = torch.load(source, map_location='cpu', weights_only=True)
if not isinstance(checkpoint, dict):
    report(stage='CHECKPOINT_SCHEMA_INVALID', reason='root_not_dict')
    raise SystemExit(4)
model = checkpoint.get('model')
config = checkpoint.get('config')
step = int(checkpoint.get('step', -1))
if not isinstance(model, dict) or not isinstance(config, dict) or step != EXPECTED_STEP:
    report(stage='CHECKPOINT_SCHEMA_INVALID', has_model=isinstance(model, dict), has_config=isinstance(config, dict), step=step)
    raise SystemExit(5)

required = {'vocab_size', 'dim', 'n_layers', 'n_heads', 'n_kv_heads', 'ffn_dim', 'max_seq_len', 'rope_theta'}
missing = sorted(required - set(config))
if missing:
    report(stage='CONFIG_INVALID', missing=missing)
    raise SystemExit(6)

slim = {
    'model': model,
    'config': config,
    'step': step,
    'tokens_seen': int(checkpoint.get('tokens_seen', 0)),
}
slim_path = WORK / 'DINAV-Axiom-125M-1000-slim.pt'
torch.save(slim, slim_path)
slim_sha = sha256_file(slim_path)
report(
    stage='SLIM_READY',
    slim_bytes=slim_path.stat().st_size,
    slim_sha256=slim_sha,
    checkpoint_step=step,
    tokens_seen=slim['tokens_seen'],
)

del checkpoint

parts = []
with slim_path.open('rb') as src:
    index = 0
    while True:
        data = src.read(CHUNK_SIZE)
        if not data:
            break
        name = f'DINAV-Axiom-125M-1000-slim.pt.part-{index:04d}'
        part_path = WORK / name
        part_path.write_bytes(data)
        parts.append({'name': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        index += 1

report(stage='SHARDED', part_count=len(parts), total_part_bytes=sum(p['size'] for p in parts))

for index, part in enumerate(parts):
    report(stage='UPLOADING_PARTS', part_index=index, part_count=len(parts), current=part['name'])
    upload_file(WORK / part['name'], part['name'], 'application/octet-stream')

local_tokenizer = WORK / TOKENIZER_NAME
local_tokenizer.write_bytes(tokenizer.read_bytes())
tokenizer_sha = sha256_file(local_tokenizer)
upload_file(local_tokenizer, TOKENIZER_NAME, 'application/json')

manifest = {
    'format': 'DINAV-Axiom native slim checkpoint shards v1',
    'source_checkpoint': CHECKPOINT_NAME,
    'source_checkpoint_sha256': source_sha,
    'slim_checkpoint': slim_path.name,
    'slim_checkpoint_sha256': slim_sha,
    'slim_checkpoint_bytes': slim_path.stat().st_size,
    'checkpoint_step': step,
    'tokens_seen': slim['tokens_seen'],
    'expected_parameter_count': EXPECTED_PARAMS,
    'config': config,
    'tokenizer': TOKENIZER_NAME,
    'tokenizer_sha256': tokenizer_sha,
    'chunk_size': CHUNK_SIZE,
    'parts': parts,
    'bucket': BUCKET,
    'prefix': PREFIX,
    'conversion_note': 'optimizer and scaler omitted only; model tensors unchanged',
}
manifest_path = WORK / 'axiom-shard-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
upload_file(manifest_path, manifest_path.name, 'application/json')

report(
    stage='UPLOAD_COMPLETE',
    manifest=manifest_path.name,
    part_count=len(parts),
    slim_sha256=slim_sha,
    tokenizer_sha256=tokenizer_sha,
)
