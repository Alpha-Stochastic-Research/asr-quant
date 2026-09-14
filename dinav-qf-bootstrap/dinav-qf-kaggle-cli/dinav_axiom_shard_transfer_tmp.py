from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_SOURCE = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/51b6e28826ee7b79eb933cdbae8e0f90a6ad1aa5/dinav-qf-bootstrap/dinav-qf-kaggle-cli/dinav_axiom_shard_transfer_tmp.py'
SUPABASE_URL = 'https://iajqfonieeqfaabmhepc.supabase.co'
SUPABASE_KEY = 'sb_publishable_ezIMrdvZJRlqEgPVkEV8nw_9jRUudFJ'
BUCKET = 'axiom-transfer-7930c7715eae'
PREFIX = 'UPiyZw0SGkEsRNHU38O3xS7R/runtime-web-v1'
CHUNK = 40 * 1024 * 1024
MAX_OBJECT = 47_185_920
WORK = Path('/kaggle/working/axiom-web-runtime')
HF_DIR = WORK / 'hf' / 'DINAV-Axiom-125M'
JS_REPO = WORK / 'transformers.js'
EXPORT_PARENT = WORK / 'exported'
TRANSPORT = WORK / 'transport'
STATUS = WORK / 'axiom-web-runtime-status.json'
for p in (HF_DIR, EXPORT_PARENT, TRANSPORT): p.mkdir(parents=True, exist_ok=True)

state = {'stage': 'STARTING'}
def report(**kw):
    state.update(kw)
    STATUS.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print('AXIOM_WEB_RUNTIME', json.dumps(state, sort_keys=True), flush=True)

def sha(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def upload(path: Path, remote: str, content_type='application/octet-stream'):
    data = path.read_bytes()
    if len(data) > MAX_OBJECT: raise RuntimeError(f'object too large: {remote} {len(data)}')
    url = f'{SUPABASE_URL}/storage/v1/object/{BUCKET}/{PREFIX}/{remote}'
    headers = {'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY, 'Content-Type': content_type, 'x-upsert': 'false'}
    last = ''
    for attempt in range(4):
        try:
            r = requests.post(url, headers=headers, data=data, timeout=180)
            if r.status_code in (200, 201): return
            last = f'HTTP {r.status_code}: {r.text[:500]}'
        except Exception as exc: last = repr(exc)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f'upload failed {remote}: {last}')

# Rebuild the exact validated HF model in memory from the immutable v3 packager,
# but stop before it writes/uploads its own production package.
source = requests.get(BASE_SOURCE, timeout=120)
source.raise_for_status()
code = source.text
marker = "model.save_pretrained(OUT, safe_serialization=True, max_shard_size='40MB')"
if marker not in code: raise RuntimeError('immutable Axiom build marker missing')
prefix_code = code.split(marker, 1)[0]
report(stage='REBUILDING_HF')
exec(compile(prefix_code, 'axiom_immutable_rebuild.py', 'exec'), globals(), globals())
# Variables model/tokenizer/parameter_count/source_sha are now exact outputs of the validated mapping.
HF_DIR.mkdir(parents=True, exist_ok=True)
model.save_pretrained(HF_DIR, safe_serialization=True, max_shard_size='1GB')
tokenizer.save_pretrained(HF_DIR)
report(stage='HF_REBUILT', parameter_count=int(parameter_count), source_sha256=str(source_sha))

# Export with the official Transformers.js v3.8.1 converter.
subprocess.run(['git', 'clone', '--depth', '1', '--branch', 'v3.8.1', 'https://github.com/huggingface/transformers.js.git', str(JS_REPO)], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(JS_REPO / 'scripts' / 'requirements.txt')], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'onnxscript'], check=True)
report(stage='CONVERTER_READY')
cmd = [sys.executable, '-m', 'scripts.convert', '--model_id', str(HF_DIR), '--output_parent_dir', str(EXPORT_PARENT), '--task', 'text-generation', '--quantize', '--modes', 'q4']
subprocess.run(cmd, cwd=str(JS_REPO), check=True)
report(stage='ONNX_EXPORTED')

# Locate the generated model root and keep only q4 runtime ONNX variants plus metadata.
candidates = [p.parent for p in EXPORT_PARENT.rglob('tokenizer.json') if (p.parent / 'config.json').exists()]
if not candidates: raise RuntimeError('Transformers.js export root not found')
MODEL_DIR = max(candidates, key=lambda p: len(list(p.rglob('*'))))
onnx_dir = MODEL_DIR / 'onnx'
if not onnx_dir.exists(): raise RuntimeError('ONNX directory missing')
q4_files = sorted([p for p in onnx_dir.iterdir() if p.is_file() and ('q4' in p.name or p.name.endswith('.onnx_data'))])
if not any(p.name.endswith('.onnx') and 'q4' in p.name for p in q4_files):
    raise RuntimeError('q4 ONNX model missing')
for p in list(onnx_dir.iterdir()):
    if p.is_file() and p not in q4_files: p.unlink()
report(stage='Q4_SELECTED', model_dir=str(MODEL_DIR), q4_files=[{'name': p.name, 'bytes': p.stat().st_size} for p in q4_files])

# Validate through the actual JavaScript runtime (WASM path) before publishing.
node_root = WORK / 'node-check'
node_root.mkdir(parents=True, exist_ok=True)
subprocess.run(['npm', 'init', '-y'], cwd=str(node_root), stdout=subprocess.DEVNULL, check=True)
subprocess.run(['npm', 'install', '--silent', '@huggingface/transformers@3.8.1'], cwd=str(node_root), check=True)
js = f'''import {{ env, pipeline }} from '@huggingface/transformers';
env.allowRemoteModels=false;
env.allowLocalModels=true;
env.localModelPath={json.dumps(str(MODEL_DIR.parent) + '/')};
env.useFSCache=false;
const gen=await pipeline('text-generation',{json.dumps(MODEL_DIR.name)},{{dtype:'q4',device:'wasm',local_files_only:true}});
const out=await gen('DV01',{{max_new_tokens:2,do_sample:false}});
console.log(JSON.stringify(out));
'''
(node_root / 'check.mjs').write_text(js, encoding='utf-8')
node = subprocess.run(['node', 'check.mjs'], cwd=str(node_root), capture_output=True, text=True, timeout=300)
if node.returncode != 0: raise RuntimeError('Transformers.js validation failed: ' + node.stderr[-3000:])
report(stage='TRANSFORMERS_JS_VERIFIED', js_output=node.stdout[-1000:])

# Build an authenticated, chunk-aware transport manifest. The DINAV client will
# reconstruct any logical object larger than the Supabase free per-file limit.
keep_names = {'config.json', 'generation_config.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json'}
logical = []
for path in sorted(MODEL_DIR.rglob('*')):
    if not path.is_file(): continue
    rel = path.relative_to(MODEL_DIR).as_posix()
    if not (rel.startswith('onnx/') or path.name in keep_names): continue
    size = path.stat().st_size
    entry = {'path': rel, 'size': size, 'sha256': sha(path), 'objects': []}
    if size <= CHUNK:
        remote = 'files/' + rel
        entry['mode'] = 'direct'
        entry['objects'].append({'name': remote, 'size': size, 'sha256': sha(path)})
    else:
        entry['mode'] = 'chunked'
        with path.open('rb') as src:
            idx = 0
            while True:
                data = src.read(CHUNK)
                if not data: break
                local = TRANSPORT / f'{path.name}.part-{idx:04d}'
                local.write_bytes(data)
                remote = f'chunks/{rel.replace("/", "__")}.part-{idx:04d}'
                entry['objects'].append({'name': remote, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'local': str(local)})
                idx += 1
    logical.append(entry)
manifest = {'runtime': 'DINAV-Axiom-125M Transformers.js v3.8.1 q4', 'source_checkpoint_sha256': str(source_sha), 'parameter_count': int(parameter_count), 'transformers_js_verified': True, 'dtype': 'q4', 'logical_files': [{**e, 'objects': [{k:v for k,v in o.items() if k!='local'} for o in e['objects']]} for e in logical]}
manifest_path = WORK / 'runtime-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
report(stage='TRANSPORT_READY', logical_files=len(logical), total_bytes=sum(e['size'] for e in logical), manifest_sha256=sha(manifest_path))

for entry in logical:
    source_path = MODEL_DIR / entry['path']
    if entry['mode'] == 'direct':
        upload(source_path, entry['objects'][0]['name'], 'application/json' if source_path.suffix == '.json' else 'application/octet-stream')
    else:
        for obj in entry['objects']:
            upload(Path(obj['local']), obj['name'])
upload(manifest_path, 'runtime-manifest.json', 'application/json')
report(stage='UPLOAD_COMPLETE', logical_files=len(logical), total_bytes=sum(e['size'] for e in logical), manifest_sha256=sha(manifest_path))
