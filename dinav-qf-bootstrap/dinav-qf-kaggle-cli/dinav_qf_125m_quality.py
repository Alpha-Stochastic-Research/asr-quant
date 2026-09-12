import hashlib
import json
import math
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

WORK = Path('/kaggle/working')
INPUT = Path('/kaggle/input/dinav-qf-125m-pilot-cli')
ROOT = WORK / 'dinav_qf_zero_cost_v3'
QUALITY = WORK / 'dinav_qf_125m_quality'
STATUS = WORK / 'dinav_qf_125m_quality_status.json'
PILOT_LAUNCHER = WORK / 'dinav_qf_125m_pilot_bootstrap.py'
PILOT_URL = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/dinav-qf-kaggle-bootstrap/dinav-qf-bootstrap/dinav-qf-kaggle-cli/dinav_qf_125m_pilot.py'
EXPECTED_BASE_SHA256 = 'c8b3c7a73da75cba6c5a02db21b7964c05b677c40b8d2118530e2dcaf1642b8f'

HELD_OUT = [
    'A fair coin is tossed twice. Give P(exactly one head) as a decimal.',
    'For standard normal Z, give E[Z^2].',
    'A zero coupon bond pays 100 in one year. Continuously compounded rate is 5%. Give price rounded to 4 decimals.',
    'A 1Y zero rate is 4% continuously compounded. Give the discount factor.',
    'For a forward on a non-dividend asset with S0=100, continuously compounded r=5%, T=1, give fair delivery price.',
    'State the two quantities needed for a historical 99% one-day VaR calculation.',
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_status(**kwargs):
    data = {
        'project': 'DINAV-QF',
        'stage': '125M quality post-training',
        'external_llm_calls': 0,
        **kwargs,
    }
    STATUS.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print('STATUS_JSON', json.dumps(data, sort_keys=True), flush=True)


def newest(root: Path, pattern: str):
    matches = list(root.rglob(pattern)) if root.exists() else []
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime)
    return matches[-1]


def run(*args, cwd=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def canonical(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().lower()


def record(text: str, index: int):
    return {
        'text': text,
        'source_uri': f'asr://dinav-qf/deterministic-curriculum/{index}',
        'source_type': 'deterministic_quantitative_curriculum',
        'publication_time': '2026-09-12T00:00:00+00:00',
        'retrieved_time': '2026-09-12T00:00:00+00:00',
        'license_id': 'owned',
        'rights_owner': 'Alpha Stochastic Research',
        'permission_evidence': 'Deterministically generated from mathematical identities and numerical computation; no external LLM text generation used.',
    }


def build_curriculum(path: Path):
    rng = random.Random(20260912)
    rows = []
    index = 0

    for _ in range(5000):
        n = rng.randint(3, 12)
        k = rng.randint(0, n)
        p = rng.choice([.2, .25, .3, .4, .5, .6, .7, .75, .8])
        answer = math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
        text = (
            f'Question: A Bernoulli trial has success probability p={p:.2f} and is repeated n={n} times independently. '
            f'What is P(X={k}) for X~Binomial(n,p)? Give a decimal.\nAnswer: {answer:.10f}'
        )
        rows.append(record(text, index))
        index += 1

    for _ in range(5000):
        mu = rng.choice([-2, -1.5, -1, -.5, 0, .5, 1, 1.5, 2])
        variance = rng.choice([.25, .5, 1, 1.5, 2, 3, 4])
        kind = rng.randrange(4)
        if kind == 0:
            question, answer = 'mean', mu
        elif kind == 1:
            question, answer = 'variance', variance
        elif kind == 2:
            question, answer = 'second moment E[X^2]', variance + mu * mu
        else:
            question, answer = 'standard deviation', math.sqrt(variance)
        text = (
            f'Question: Let X be normally distributed with mean {mu:.4f} and variance {variance:.4f}. '
            f'Give the {question} as a decimal.\nAnswer: {answer:.10f}'
        )
        rows.append(record(text, index))
        index += 1

    for _ in range(8000):
        rate = rng.randint(5, 120) / 1000
        maturity = rng.choice([.25, .5, .75, 1.25, 1.5, 2, 3, 5, 7, 10])
        if rng.random() < .5:
            answer = math.exp(-rate * maturity)
            text = (
                f'Question: With continuously compounded zero rate r={rate:.4f} and maturity T={maturity:.2f} years, '
                f'what is the discount factor exp(-rT)?\nAnswer: {answer:.10f}'
            )
        else:
            face = rng.choice([50, 80, 90, 100, 120, 150, 200, 1000])
            answer = face * math.exp(-rate * maturity)
            text = (
                f'Question: A zero-coupon bond pays {face} at T={maturity:.2f} years. '
                f'The continuously compounded zero rate is r={rate:.4f}. What is its present value?\nAnswer: {answer:.10f}'
            )
        rows.append(record(text, index))
        index += 1

    for _ in range(7000):
        spot = rng.choice([40, 50, 75, 80, 90, 110, 120, 150, 200, 250])
        rate = rng.randint(5, 120) / 1000
        dividend = rng.choice([0, .005, .01, .015, .02, .025, .03])
        maturity = rng.choice([.25, .5, .75, 1.25, 1.5, 2, 3])
        answer = spot * math.exp((rate - dividend) * maturity)
        text = (
            f'Question: For an asset with spot S0={spot:.2f}, continuously compounded risk-free rate r={rate:.4f}, '
            f'dividend yield q={dividend:.4f}, and maturity T={maturity:.2f}, compute the fair forward delivery price '
            f'S0*exp((r-q)T).\nAnswer: {answer:.10f}'
        )
        rows.append(record(text, index))
        index += 1

    concepts = [
        (
            'Question: In historical Value-at-Risk, which empirical object is taken at the confidence level?',
            'Answer: the empirical loss quantile at the selected confidence level.',
        ),
        (
            'Question: What data and threshold define a one-day historical VaR estimate?',
            'Answer: a sample of one-day portfolio losses and the empirical quantile corresponding to the chosen confidence level.',
        ),
        (
            'Question: Historical VaR is computed from which distribution and which statistic?',
            'Answer: the empirical distribution of historical losses and its confidence-level quantile.',
        ),
    ]
    for _ in range(3000):
        question, answer = rng.choice(concepts)
        rows.append(record(question + '\n' + answer, index))
        index += 1

    rng.shuffle(rows)
    held = [canonical(item) for item in HELD_OUT]
    for row in rows:
        candidate = canonical(row['text'])
        if any(item in candidate for item in held):
            raise RuntimeError('held-out prompt contamination')

    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print('CURRICULUM_RECORDS', len(rows), 'SHA256', sha(path), flush=True)
    return len(rows)


def ensure_base_pilot():
    input_checkpoint = newest(INPUT, 'DINAV-QF-125M-1000.pt')
    if input_checkpoint is not None:
        digest = sha(input_checkpoint)
        print('BASE_CHECKPOINT_FROM_INPUT', input_checkpoint, digest, flush=True)
        return input_checkpoint, 'kaggle-input'

    local_checkpoint = newest(ROOT, 'DINAV-QF-125M-1000.pt')
    if local_checkpoint is not None:
        digest = sha(local_checkpoint)
        print('BASE_CHECKPOINT_LOCAL', local_checkpoint, digest, flush=True)
        return local_checkpoint, 'local-existing'

    print('BASE_CHECKPOINT_NOT_PUBLISHED_REBUILDING_PILOT_IN_SAME_KERNEL', flush=True)
    response = requests.get(PILOT_URL, timeout=60)
    response.raise_for_status()
    PILOT_LAUNCHER.write_text(response.text, encoding='utf-8')
    write_status(status='REBUILDING_BASE_PILOT', reason='published Kaggle input does not include the .pt checkpoint')
    run(sys.executable, PILOT_LAUNCHER, cwd=WORK)

    rebuilt = newest(ROOT, 'DINAV-QF-125M-1000.pt')
    if rebuilt is None:
        raise FileNotFoundError('DINAV-QF-125M-1000.pt after autonomous base-pilot rebuild')
    digest = sha(rebuilt)
    print('BASE_CHECKPOINT_REBUILT', rebuilt, digest, flush=True)
    if digest != EXPECTED_BASE_SHA256:
        print('BASE_CHECKPOINT_SHA_NOTE expected previous v6 SHA but deterministic rebuild produced', digest, flush=True)
    return rebuilt, 'autonomous-rebuild'


print('DINAV-QF QUALITY POST-TRAINING AUTONOMOUS V2', flush=True)
import torch
print('TORCH', torch.__version__, 'CUDA', torch.cuda.is_available(), 'GPUS', torch.cuda.device_count(), flush=True)
for gpu_index in range(torch.cuda.device_count()):
    print('GPU', gpu_index, torch.cuda.get_device_name(gpu_index), flush=True)

base_checkpoint, base_origin = ensure_base_pilot()

if not ROOT.exists():
    source_model = newest(INPUT, 'training/model.py')
    if source_model is None:
        raise FileNotFoundError('training/model.py in pilot input')
    source_root = source_model.parents[1]
    shutil.copytree(source_root, ROOT)

QUALITY.mkdir(parents=True, exist_ok=True)
tokenizer = newest(ROOT, 'dinav_qf_tokenizer.json') or newest(INPUT, 'dinav_qf_tokenizer.json')
runtime_config = newest(ROOT, 'pilot-runtime-config.json') or newest(INPUT, 'pilot-runtime-config.json')
if tokenizer is None:
    raise FileNotFoundError('dinav_qf_tokenizer.json')
if runtime_config is None:
    raise FileNotFoundError('pilot-runtime-config.json')

base_digest = sha(base_checkpoint)
print('BASE_CHECKPOINT', base_checkpoint, 'SHA256', base_digest, 'ORIGIN', base_origin, flush=True)
print('TOKENIZER', tokenizer, 'SHA256', sha(tokenizer), flush=True)

train_path = ROOT / 'training' / 'train.py'
train_text = train_path.read_text(encoding='utf-8')
resume_anchor = "p.add_argument('--resume', help='checkpoint path to resume model/optimizer/scaler and deterministic batch cursor from')"
if "--init-model" not in train_text:
    if resume_anchor not in train_text:
        raise RuntimeError('Unable to patch train.py: resume parser anchor missing')
    train_text = train_text.replace(
        resume_anchor,
        resume_anchor + "\n    p.add_argument('--init-model', help='checkpoint whose model weights initialize a fresh optimizer/schedule')",
    )
model_anchor = "model = DinavQF(cfg).to(device)\n    model.set_gradient_checkpointing(args.gradient_checkpointing)"
if 'initialized_model_from' not in train_text:
    if model_anchor not in train_text:
        raise RuntimeError('Unable to patch train.py: model initialization anchor missing')
    train_text = train_text.replace(
        model_anchor,
        "model = DinavQF(cfg).to(device)\n    if args.init_model:\n        init_state = torch.load(Path(args.init_model).expanduser().resolve(), map_location=device, weights_only=False)\n        model.load_state_dict(init_state['model'])\n        print(json.dumps({'initialized_model_from': str(Path(args.init_model).expanduser().resolve()), 'initialized_step': init_state.get('step')}), flush=True)\n    model.set_gradient_checkpointing(args.gradient_checkpointing)",
    )
train_path.write_text(train_text, encoding='utf-8')

curriculum = QUALITY / 'deterministic_curriculum.jsonl'
record_count = build_curriculum(curriculum)
corpus = QUALITY / 'corpus'
run(sys.executable, 'corpus/bootstrap_125m.py', '--raw', curriculum, '--out-dir', corpus, cwd=ROOT)
run(sys.executable, 'eval/contamination.py', '--corpus', corpus / 'accepted.jsonl', '--out', QUALITY / 'contamination.json', cwd=ROOT)
run(sys.executable, 'training/prepare_tokens.py', '--tokenizer', tokenizer, '--input', corpus / 'train.jsonl', '--output', QUALITY / 'train.bin', '--meta', QUALITY / 'train.meta.json', cwd=ROOT)

output_dir = QUALITY / 'checkpoints'
write_status(
    status='QUALITY_TRAINING',
    base_checkpoint=str(base_checkpoint),
    base_checkpoint_sha256=base_digest,
    base_checkpoint_origin=base_origin,
    curriculum_records=record_count,
)
run(
    sys.executable,
    'training/train.py',
    '--config', runtime_config,
    '--tokens', QUALITY / 'train.bin',
    '--out', output_dir,
    '--steps', '500',
    '--micro-batch-size', '1',
    '--grad-accum', '8',
    '--lr', '5e-5',
    '--warmup-steps', '50',
    '--checkpoint-every', '250',
    '--gradient-checkpointing',
    '--init-model', base_checkpoint,
    cwd=ROOT,
)

final_checkpoint = output_dir / 'DINAV-QF-125M-500.pt'
if not final_checkpoint.exists():
    raise FileNotFoundError(final_checkpoint)

run(
    sys.executable,
    'eval/model_eval.py',
    '--checkpoint', final_checkpoint,
    '--config', runtime_config,
    '--tokenizer', tokenizer,
    '--out', QUALITY / 'quality-eval.json',
    '--max-new-tokens', '32',
    cwd=ROOT,
)

metadata = json.loads((QUALITY / 'train.meta.json').read_text(encoding='utf-8'))
evaluation = json.loads((QUALITY / 'quality-eval.json').read_text(encoding='utf-8'))
write_status(
    status='COMPLETED',
    base_checkpoint_sha256=base_digest,
    base_checkpoint_origin=base_origin,
    final_checkpoint=str(final_checkpoint),
    final_checkpoint_sha256=sha(final_checkpoint),
    curriculum_records=record_count,
    train_tokens=metadata.get('tokens'),
    eval_overall=evaluation.get('overall'),
    eval_cases=evaluation.get('cases'),
    completed_at=time.time(),
)
print('QUALITY_FINAL', json.dumps(evaluation, indent=2), flush=True)
