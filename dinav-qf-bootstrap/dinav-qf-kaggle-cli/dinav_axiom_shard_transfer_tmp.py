from __future__ import annotations

import json
import traceback
import requests

SOURCE = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/51b6e28826ee7b79eb933cdbae8e0f90a6ad1aa5/dinav-qf-bootstrap/dinav-qf-kaggle-cli/dinav_axiom_shard_transfer_tmp.py'

print('AXIOM_PRODUCTION ' + json.dumps({'stage': 'V4_BOOTSTRAP_START'}), flush=True)
try:
    response = requests.get(SOURCE, timeout=120)
    response.raise_for_status()
    code = response.text
    print('AXIOM_PRODUCTION ' + json.dumps({'stage': 'V4_SOURCE_LOADED', 'bytes': len(code)}), flush=True)
    exec(compile(code, 'dinav_axiom_packager_v3.py', 'exec'), globals(), globals())
except BaseException as exc:
    print('AXIOM_PRODUCTION ' + json.dumps({'stage': 'V4_FATAL', 'error': repr(exc)}), flush=True)
    traceback.print_exc()
    raise
