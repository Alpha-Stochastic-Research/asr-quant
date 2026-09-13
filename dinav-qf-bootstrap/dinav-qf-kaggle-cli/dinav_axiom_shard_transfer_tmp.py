from __future__ import annotations

import glob
import hashlib
import json
import time
from pathlib import Path

import requests
import torch
from tokenizers import Tokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast

CHECKPOINT_NAME = 'DINAV-QF-125M-1000.pt'
TOKENIZER_NAME = 'dinav_qf_tokenizer.json'
EXPECTED_SOURCE_SHA256 = 'c8b3c7a73da75cba6c5a02db21b7964c05b677c40b8d2118530e2dcaf1642b8f'
EXPECTED_PARAMS = 124_988_160
EXPECTED_STEP = 1000
SUPABASE_URL = 'https://iajqfonieeqfaabmhepc.supabase.co'
SUPABASE_KEY = 'sb_publishable_ezIMrdvZJRlqEgPVkEV8nw_9jRUudFJ'
BUCKET = 'axiom-transfer-7930c7715eae'
PREFIX = 'UPiyZw0SGkEsRNHU38O3xS7R'
PRODUCTION_PREFIX = PREFIX + '/production'
WORK = Path('/kaggle/working/axiom-production')
OUT = WORK / 'DINAV-Axiom-125M'
WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
STATUS = WORK / 'conversion-status.json'

status = {'stage': 'STARTING'}


def report(**updates):
    status.update(updates)
    STATUS.write_text(json.dumps(status, indent=2), encoding='utf-8')
    print('AXIOM_PRODUCTION', json.dumps(status, sort_keys=True), flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def target_key(key: str) -> str | None:
    if key == 'embed.weight':
        return 'model.embed_tokens.weight'
    if key == 'norm.weight':
        return 'model.norm.weight'
    if key == 'lm_head.weight':
        return None
    if not key.startswith('blocks.'):
        return None
    pieces = key.split('.')
    layer = pieces[1]
    tail = '.'.join(pieces[2:])
    suffix = {
        'attn_norm.weight': 'input_layernorm.weight',
        'ffn_norm.weight': 'post_attention_layernorm.weight',
        'attn.q.weight': 'self_attn.q_proj.weight',
        'attn.k.weight': 'self_attn.k_proj.weight',
        'attn.v.weight': 'self_attn.v_proj.weight',
        'attn.o.weight': 'self_attn.o_proj.weight',
        'ffn.gate.weight': 'mlp.gate_proj.weight',
        'ffn.up.weight': 'mlp.up_proj.weight',
        'ffn.down.weight': 'mlp.down_proj.weight',
    }
    mapped = suffix.get(tail)
    return f'model.layers.{layer}.{mapped}' if mapped else None


def auth_headers(content_type: str = 'application/octet-stream'):
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': content_type,
    }


def upload_file(path: Path, remote_name: str):
    url = f'{SUPABASE_URL}/storage/v1/object/{BUCKET}/{PRODUCTION_PREFIX}/{remote_name}'
    headers = auth_headers()
    headers['cache-control'] = 'max-age=3600'
    headers['x-upsert'] = 'false'
    payload = path.read_bytes()
    last = None
    for attempt in range(1, 5):
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=180)
            if response.status_code in (200, 201):
                return
            last = f'HTTP {response.status_code}: {response.text[:1000]}'
        except Exception as exc:
            last = repr(exc)
        time.sleep(min(15, attempt * 3))
    raise RuntimeError(f'upload failed for {remote_name}: {last}')


def delete_raw_transfer():
    raw_names = [f'{PREFIX}/DINAV-Axiom-125M-1000-slim.pt.part-{i:04d}' for i in range(12)]
    raw_names += [f'{PREFIX}/dinav_qf_tokenizer.json', f'{PREFIX}/axiom-shard-manifest.json']
    url = f'{SUPABASE_URL}/storage/v1/object/{BUCKET}'
    response = requests.delete(url, headers=auth_headers('application/json'), json={'prefixes': raw_names}, timeout=180)
    if response.status_code not in (200, 201):
        raise RuntimeError(f'raw cleanup failed: HTTP {response.status_code}: {response.text[:1500]}')
    return raw_names


ckpts = glob.glob('/kaggle/input/**/' + CHECKPOINT_NAME, recursive=True)
tokenizers = glob.glob('/kaggle/input/**/' + TOKENIZER_NAME, recursive=True)
if not ckpts or not tokenizers:
    report(stage='INPUT_NOT_FOUND', checkpoint_matches=ckpts, tokenizer_matches=tokenizers)
    raise SystemExit(2)
checkpoint_path = Path(ckpts[0])
tokenizer_path = Path(tokenizers[0])
report(stage='SOURCE_FOUND', checkpoint_bytes=checkpoint_path.stat().st_size, tokenizer_bytes=tokenizer_path.stat().st_size)

source_sha = sha256_file(checkpoint_path)
if source_sha != EXPECTED_SOURCE_SHA256:
    report(stage='SOURCE_HASH_MISMATCH', source_sha256=source_sha)
    raise SystemExit(3)
report(stage='SOURCE_HASH_OK', source_sha256=source_sha)

checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
state = checkpoint.get('model') if isinstance(checkpoint, dict) else None
raw = dict(checkpoint.get('config') or {}) if isinstance(checkpoint, dict) else {}
step = int(checkpoint.get('step', -1)) if isinstance(checkpoint, dict) else -1
if not isinstance(state, dict) or step != EXPECTED_STEP:
    report(stage='CHECKPOINT_SCHEMA_INVALID', has_model=isinstance(state, dict), step=step)
    raise SystemExit(4)
required = {'vocab_size','dim','n_layers','n_heads','n_kv_heads','ffn_dim','max_seq_len','rope_theta'}
missing_config = sorted(required - set(raw))
if missing_config:
    report(stage='CONFIG_INVALID', missing=missing_config)
    raise SystemExit(5)

core = Tokenizer.from_file(str(tokenizer_path))
special_ids = {token: core.token_to_id(token) for token in ('<pad>','<bos>','<eos>','<unk>')}
if any(value is None for value in special_ids.values()):
    report(stage='TOKENIZER_INVALID', special_ids=special_ids)
    raise SystemExit(6)

config = LlamaConfig(
    vocab_size=int(raw['vocab_size']),
    hidden_size=int(raw['dim']),
    intermediate_size=int(raw['ffn_dim']),
    num_hidden_layers=int(raw['n_layers']),
    num_attention_heads=int(raw['n_heads']),
    num_key_value_heads=int(raw['n_kv_heads']),
    max_position_embeddings=int(raw['max_seq_len']),
    rope_theta=float(raw['rope_theta']),
    hidden_act='silu',
    rms_norm_eps=1e-6,
    attention_bias=False,
    mlp_bias=False,
    tie_word_embeddings=True,
    bos_token_id=int(special_ids['<bos>']),
    eos_token_id=int(special_ids['<eos>']),
    pad_token_id=int(special_ids['<pad>']),
    use_cache=True,
)
model = LlamaForCausalLM(config)
target = model.state_dict()
mapped = {}
seen = set()
for source_name, tensor in state.items():
    if source_name == 'lm_head.weight':
        seen.add(source_name)
        continue
    destination = target_key(source_name)
    if not destination or destination not in target:
        report(stage='MAPPING_FAILED', source_tensor=source_name)
        raise SystemExit(7)
    if tuple(tensor.shape) != tuple(target[destination].shape):
        report(stage='MAPPING_SHAPE_FAILED', source_tensor=source_name, destination=destination, source_shape=list(tensor.shape), target_shape=list(target[destination].shape))
        raise SystemExit(8)
    mapped[destination] = tensor
    seen.add(source_name)

missing_target = (set(target) - {'lm_head.weight'}) - set(mapped)
unmapped_source = set(state) - seen
if missing_target or unmapped_source:
    report(stage='MAPPING_INCOMPLETE', missing_target=sorted(missing_target), unmapped_source=sorted(unmapped_source))
    raise SystemExit(9)

load_result = model.load_state_dict(mapped, strict=False)
remaining_missing = [key for key in load_result.missing_keys if key != 'lm_head.weight']
if load_result.unexpected_keys or remaining_missing:
    report(stage='MODEL_LOAD_MISMATCH', unexpected=load_result.unexpected_keys, missing=remaining_missing)
    raise SystemExit(10)
model.tie_weights()
model.eval()
parameter_count = sum(parameter.numel() for parameter in model.parameters())
if parameter_count != EXPECTED_PARAMS:
    report(stage='PARAMETER_COUNT_MISMATCH', parameter_count=parameter_count)
    raise SystemExit(11)
report(stage='MAPPING_VERIFIED', parameter_count=parameter_count)

tokenizer = PreTrainedTokenizerFast(
    tokenizer_file=str(tokenizer_path),
    bos_token='<bos>',
    eos_token='<eos>',
    unk_token='<unk>',
    pad_token='<pad>',
)
if len(tokenizer) != int(raw['vocab_size']):
    report(stage='TOKENIZER_VOCAB_MISMATCH', tokenizer_size=len(tokenizer), expected=int(raw['vocab_size']))
    raise SystemExit(12)

model.save_pretrained(OUT, safe_serialization=True, max_shard_size='40MB')
tokenizer.save_pretrained(OUT)
report(stage='SAFETENSORS_SAVED', file_count=len(list(OUT.iterdir())))

reloaded = AutoModelForCausalLM.from_pretrained(
    OUT,
    local_files_only=True,
    trust_remote_code=False,
    torch_dtype=torch.float32,
)
reloaded_tokenizer = AutoTokenizer.from_pretrained(OUT, local_files_only=True, trust_remote_code=False)
reloaded_count = sum(parameter.numel() for parameter in reloaded.parameters())
if reloaded_count != EXPECTED_PARAMS or len(reloaded_tokenizer) != int(raw['vocab_size']):
    report(stage='PRODUCTION_RELOAD_FAILED', parameter_count=reloaded_count, tokenizer_size=len(reloaded_tokenizer))
    raise SystemExit(13)

encoded = reloaded_tokenizer('DV01', return_tensors='pt')
with torch.no_grad():
    generated = reloaded.generate(**encoded, max_new_tokens=2, do_sample=False)
smoke_text = reloaded_tokenizer.decode(generated[0], skip_special_tokens=True)
report(stage='PRODUCTION_RELOAD_VERIFIED', parameter_count=reloaded_count, smoke_text=smoke_text[:200])

files = []
for path in sorted(OUT.iterdir()):
    if not path.is_file():
        continue
    size = path.stat().st_size
    if size > 47_185_920:
        report(stage='OUTPUT_FILE_TOO_LARGE', file=path.name, size=size)
        raise SystemExit(14)
    files.append({'name': path.name, 'size': size, 'sha256': sha256_file(path)})

manifest = {
    'model_name': 'DINAV-Axiom-125M',
    'format': 'huggingface-llama-compatible-safetensors',
    'source_checkpoint': checkpoint_path.name,
    'source_checkpoint_sha256': source_sha,
    'source_tokenizer': tokenizer_path.name,
    'source_tokenizer_sha256': sha256_file(tokenizer_path),
    'checkpoint_step': step,
    'tokens_seen': int(checkpoint.get('tokens_seen', 0)),
    'parameter_count': EXPECTED_PARAMS,
    'vocab_size': int(raw['vocab_size']),
    'training_max_seq_len': int(raw['max_seq_len']),
    'native_architecture': {key: raw[key] for key in ('dim','n_layers','n_heads','n_kv_heads','ffn_dim','rope_theta')},
    'conversion': 'exact tensor mapping; no retraining, distillation, interpolation or external LLM call',
    'production_loader_verified': True,
    'generation_smoke_verified': True,
    'production_files': files,
}
manifest_path = OUT / 'dinav_axiom_manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
files.append({'name': manifest_path.name, 'size': manifest_path.stat().st_size, 'sha256': sha256_file(manifest_path)})
report(stage='PRODUCTION_PACKAGE_VERIFIED', production_files=len(files))

removed = delete_raw_transfer()
report(stage='RAW_TRANSFER_CLEANED', removed_count=len(removed))

for index, item in enumerate(files):
    report(stage='UPLOADING_PRODUCTION', file_index=index, file_count=len(files), current=item['name'])
    upload_file(OUT / item['name'], item['name'])

report(
    stage='UPLOAD_COMPLETE',
    parameter_count=EXPECTED_PARAMS,
    production_files=len(files),
    source_checkpoint_sha256=source_sha,
    manifest_sha256=sha256_file(manifest_path),
)
