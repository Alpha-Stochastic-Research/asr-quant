# ASRQuant 1.3.0rc1 — Local Pytest Validation

Validation target: the exact user-supplied ASRQuant 1.3.0 development tree converted to package version `1.3.0rc1`, with the unpublished `paper/` directory removed.

## Result

**PASS — 319 tests passed across the repository's isolated pytest groups.**

| Group | Passed |
| --- | ---: |
| core | 27 |
| quant | 28 |
| surfaces | 15 |
| api | 4 |
| rates | 36 |
| discovery | 7 |
| v120 | 76 |
| v130 | 46 |
| legacy package contract | 18 |
| production | 62 |
| **Total** | **319** |

## Additional checks

- `pyproject.toml` version: `1.3.0rc1`
- `asrquant.__version__`: `1.3.0rc1`
- release tag gate `v1.3.0rc1`: PASS
- `compileall` for source/tests/examples/scripts: PASS
- wheel built: `asrquant-1.3.0rc1-py3-none-any.whl`
- source distribution built: `asrquant-1.3.0rc1.tar.gz`
- wheel metadata version: `1.3.0rc1`
- sdist root: `asrquant-1.3.0rc1`
- `paper/` entries in sdist: 0
- wheel import/version check from an isolated target directory: PASS
- all 85 packaged Python source files are byte-identical between the verified source tree and wheel: PASS

## Recommended independent command

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/test_all.py --group all
```
