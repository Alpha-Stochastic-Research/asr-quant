import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from urllib.parse import quote

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
SMOKE_CORPUS = ROOT / 'data' / 'smoke_authorized.jsonl'
OPEN_CORPUS = WORK / 'dinav_qf_open_pilot_corpus.jsonl'
OPEN_CORPUS_MANIFEST = WORK / 'dinav_qf_open_pilot_manifest.json'
PILOT_WORK_DIR = ROOT / 'runs' / 'zero-cost-125m-pilot'
CHECKPOINT_DIR = PILOT_WORK_DIR / 'pilot'
WIKIPEDIA_API = 'https://en.wikipedia.org/w/api.php'
WIKIPEDIA_LICENSE_URL = 'https://en.wikipedia.org/wiki/Wikipedia:Copyrights'
MAX_WIKI_PAGES = 500
MAX_WIKI_TEXT_BYTES = 18 * 1024 * 1024

WIKI_CATEGORIES = [
    'Category:Mathematical finance',
    'Category:Financial economics',
    'Category:Fixed income',
    'Category:Derivatives (finance)',
    'Category:Interest rates',
    'Category:Stochastic processes',
    'Category:Probability theory',
    'Category:Statistics',
    'Category:Econometrics',
    'Category:Mathematical optimization',
    'Category:Numerical analysis',
    'Category:Time series',
    'Category:Risk management',
    'Category:Financial risk',
    'Category:Financial markets',
    'Category:Macroeconomics',
]

WIKI_SEEDS = [
    'Mathematical finance', 'Quantitative analysis (finance)', 'Financial engineering',
    'Derivative (finance)', 'Option (finance)', 'Black–Scholes model', 'Greeks (finance)',
    'Interest rate derivative', 'Interest rate swap', 'Swaption', 'Cap (finance)', 'Floor (finance)',
    'Yield curve', 'Bootstrapping (finance)', 'Zero-coupon bond', 'Bond duration', 'Bond convexity',
    'Overnight indexed swap', 'Secured Overnight Financing Rate', 'Euro short-term rate',
    'Heath–Jarrow–Morton framework', 'Hull–White model', 'Cox–Ingersoll–Ross model',
    'Short-rate model', 'Vasicek model', 'SABR volatility model', 'Heston model',
    'Local volatility', 'Implied volatility', 'Volatility smile', 'Volatility surface',
    'Risk-neutral measure', 'Martingale pricing', 'Fundamental theorem of asset pricing',
    'Stochastic calculus', 'Itô calculus', 'Itô process', 'Itô lemma', 'Stochastic differential equation',
    'Brownian motion', 'Wiener process', 'Martingale (probability theory)', 'Stopping time',
    'Markov process', 'Fokker–Planck equation', 'Kolmogorov equations', 'Monte Carlo method',
    'Monte Carlo methods in finance', 'Finite difference method', 'Partial differential equation',
    'Optimization', 'Convex optimization', 'Linear programming', 'Quadratic programming',
    'Lagrange multiplier', 'Karush–Kuhn–Tucker conditions', 'Dynamic programming',
    'Stochastic control', 'Portfolio optimization', 'Modern portfolio theory', 'Efficient frontier',
    'Capital asset pricing model', 'Arbitrage pricing theory', 'Value at risk', 'Expected shortfall',
    'Stress testing', 'Credit risk', 'Credit default swap', 'Counterparty risk', 'Wrong-way risk',
    'XVA', 'Market risk', 'Liquidity risk', 'Operational risk', 'Risk management',
    'Market microstructure', 'Bid–ask spread', 'Order book', 'Limit order', 'Algorithmic trading',
    'High-frequency trading', 'Execution (finance)', 'Slippage (finance)',
    'Time series', 'Autoregressive model', 'Moving-average model', 'ARIMA', 'ARCH model',
    'GARCH', 'Vector autoregression', 'Cointegration', 'Unit root', 'Stationary process',
    'Econometrics', 'Regression analysis', 'Ordinary least squares', 'Maximum likelihood estimation',
    'Bayesian inference', 'Kalman filter', 'Hidden Markov model', 'Regime-switching model',
    'Probability theory', 'Conditional probability', 'Conditional expectation', 'Law of large numbers',
    'Central limit theorem', 'Measure (mathematics)', 'Probability measure', 'Radon–Nikodym theorem',
    'Fourier transform', 'Characteristic function (probability theory)', 'Moment-generating function',
    'Macroeconomics', 'Monetary policy', 'Central bank', 'Inflation', 'Interest rate', 'Yield (finance)',
    'Term structure of interest rates', 'Forward rate', 'Futures contract', 'Forward contract',
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


def wikipedia_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'DINAV-QF/0.1 (Alpha Stochastic Research; contact@asr-lab.online)',
        'Accept': 'application/json',
    })
    return session


def api_json(session, params, method='GET'):
    for attempt in range(4):
        try:
            if method == 'POST':
                response = session.post(WIKIPEDIA_API, data=params, timeout=60)
            else:
                response = session.get(WIKIPEDIA_API, params=params, timeout=60)
            response.raise_for_status()
            payload = response.json()
            if 'error' in payload:
                raise RuntimeError(f"Wikipedia API error: {payload['error']}")
            return payload
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError('unreachable')


def discover_wikipedia_titles(session):
    titles = set(WIKI_SEEDS)
    for category in WIKI_CATEGORIES:
        continuation = None
        category_count = 0
        while len(titles) < MAX_WIKI_PAGES and category_count < 100:
            params = {
                'action': 'query',
                'list': 'categorymembers',
                'cmtitle': category,
                'cmnamespace': '0',
                'cmtype': 'page',
                'cmlimit': '100',
                'format': 'json',
                'formatversion': '2',
            }
            if continuation:
                params['cmcontinue'] = continuation
            payload = api_json(session, params)
            members = payload.get('query', {}).get('categorymembers', [])
            if not members:
                break
            for member in members:
                title = str(member.get('title', '')).strip()
                if title:
                    titles.add(title)
                    category_count += 1
                    if len(titles) >= MAX_WIKI_PAGES or category_count >= 100:
                        break
            continuation = payload.get('continue', {}).get('cmcontinue')
            if not continuation:
                break
        print('WIKI_CATEGORY', category, 'DISCOVERED_TOTAL', len(titles), flush=True)
        if len(titles) >= MAX_WIKI_PAGES:
            break
    return sorted(titles)[:MAX_WIKI_PAGES]


def build_open_corpus():
    session = wikipedia_session()
    titles = discover_wikipedia_titles(session)
    retrieved = now_iso()
    records = 0
    text_bytes = 0
    source_rows = []
    with OPEN_CORPUS.open('w', encoding='utf-8') as dst:
        for start in range(0, len(titles), 20):
            if records >= MAX_WIKI_PAGES or text_bytes >= MAX_WIKI_TEXT_BYTES:
                break
            batch = titles[start:start + 20]
            payload = api_json(session, {
                'action': 'query',
                'prop': 'revisions',
                'titles': '|'.join(batch),
                'rvprop': 'ids|timestamp|content',
                'rvslots': 'main',
                'redirects': '1',
                'format': 'json',
                'formatversion': '2',
            }, method='POST')
            for page in payload.get('query', {}).get('pages', []):
                if page.get('missing'):
                    continue
                revisions = page.get('revisions') or []
                if not revisions:
                    continue
                revision = revisions[0]
                slot = (revision.get('slots') or {}).get('main') or {}
                content = slot.get('content')
                if not isinstance(content, str) or len(content.strip()) < 1000:
                    continue
                title = str(page.get('title', '')).strip()
                revid = revision.get('revid')
                timestamp = revision.get('timestamp')
                if not title or not revid or not timestamp:
                    continue
                text = f'Title: {title}\n\n{content.strip()}'
                encoded_bytes = len(text.encode('utf-8'))
                if text_bytes + encoded_bytes > MAX_WIKI_TEXT_BYTES and records >= 250:
                    break
                source_uri = f'https://en.wikipedia.org/w/index.php?title={quote(title.replace(" ", "_"))}&oldid={revid}'
                row = {
                    'text': text,
                    'source_uri': source_uri,
                    'source_type': 'wikipedia_revision',
                    'publication_time': timestamp,
                    'retrieved_time': retrieved,
                    'license_id': 'cc_by_sa',
                    'rights_owner': 'Wikimedia contributors',
                    'permission_evidence': f'Wikipedia text is reusable under CC BY-SA; exact revision {revid} and source URI retained. License reference: {WIKIPEDIA_LICENSE_URL}',
                }
                dst.write(json.dumps(row, ensure_ascii=False) + '\n')
                source_rows.append({
                    'title': title,
                    'revision_id': revid,
                    'revision_timestamp': timestamp,
                    'source_uri': source_uri,
                    'sha256_text': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'bytes': encoded_bytes,
                    'license_id': 'cc_by_sa',
                })
                records += 1
                text_bytes += encoded_bytes
                if records >= MAX_WIKI_PAGES or text_bytes >= MAX_WIKI_TEXT_BYTES:
                    break
            print('WIKI_FETCH_PROGRESS', records, 'PAGES', text_bytes, 'TEXT_BYTES', flush=True)
    manifest = {
        'schema_version': '1.0',
        'created_at': now_iso(),
        'source': 'English Wikipedia revision API',
        'license_id': 'cc_by_sa',
        'license_reference': WIKIPEDIA_LICENSE_URL,
        'selection': {
            'categories': WIKI_CATEGORIES,
            'seed_titles': WIKI_SEEDS,
            'max_pages': MAX_WIKI_PAGES,
            'max_text_bytes': MAX_WIKI_TEXT_BYTES,
        },
        'records': records,
        'text_bytes': text_bytes,
        'corpus_sha256': sha256_file(OPEN_CORPUS),
        'sources': source_rows,
        'external_llm_calls': 0,
    }
    OPEN_CORPUS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    if records < 250:
        raise RuntimeError(f'Open pilot corpus too small: only {records} Wikipedia revisions accepted')
    if text_bytes < 4 * 1024 * 1024:
        raise RuntimeError(f'Open pilot corpus text too small: only {text_bytes} bytes')
    print('OPEN_CORPUS_READY', records, 'PAGES', text_bytes, 'TEXT_BYTES', sha256_file(OPEN_CORPUS), flush=True)
    return manifest


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
    if not SMOKE_CORPUS.is_file():
        raise FileNotFoundError(SMOKE_CORPUS)
    open_manifest = build_open_corpus()
except Exception as exc:
    write_status(
        status='BOOTSTRAP_FAILED',
        error_type=type(exc).__name__,
        error_message=str(exc),
        completed_at_unix=time.time(),
    )
    raise

print('BUNDLE_READY', ROOT, flush=True)
print('SMOKE_CORPUS', SMOKE_CORPUS, 'BYTES', SMOKE_CORPUS.stat().st_size, flush=True)
print('OPEN_CORPUS', OPEN_CORPUS, 'BYTES', OPEN_CORPUS.stat().st_size, flush=True)
write_status(
    status='RUNNING',
    bundle_sha256=sha,
    smoke_corpus=str(SMOKE_CORPUS),
    smoke_corpus_bytes=SMOKE_CORPUS.stat().st_size,
    open_corpus=str(OPEN_CORPUS),
    open_corpus_sha256=sha256_file(OPEN_CORPUS),
    open_corpus_records=open_manifest['records'],
    open_corpus_text_bytes=open_manifest['text_bytes'],
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
        str(SMOKE_CORPUS),
        str(OPEN_CORPUS),
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
tokenizer_path = PILOT_WORK_DIR / 'dinav_qf_tokenizer.json'

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
    tokenizer_path=str(tokenizer_path) if tokenizer_path.is_file() else None,
    tokenizer_sha256=sha256_file(tokenizer_path),
    validation_path=str(validation_path) if validation_path.is_file() else None,
    eval_path=str(eval_path) if eval_path.is_file() else None,
    corpus_manifest_path=str(corpus_manifest_path) if corpus_manifest_path.is_file() else None,
    open_corpus_manifest=str(OPEN_CORPUS_MANIFEST) if OPEN_CORPUS_MANIFEST.is_file() else None,
    completed_at_unix=time.time(),
)

if exit_code != 0:
    raise SystemExit(exit_code)
