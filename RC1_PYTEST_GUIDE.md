# ASRQuant 1.3.0rc1 — Pytest Release Candidate

This archive is a pre-release validation candidate for ASRQuant 1.3.0. It is not the final published 1.3.0 release.

## Package identity

- Distribution: `asrquant`
- Candidate version: `1.3.0rc1`
- Final target: `1.3.0`
- Python: `>=3.10`
- Manuscript directory: intentionally excluded from this candidate

## Recommended validation

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/test_all.py --group all
```

A direct pytest run is also supported for quick validation:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src MPLBACKEND=Agg pytest -q
```

Verify the candidate identity:

```bash
python -c "import asrquant; print(asrquant.__version__)"
asrquant --version
python scripts/check_release.py v1.3.0rc1
```

## Distribution validation

After building, validate the exact wheel rather than only the source tree:

```bash
python -m pip install --force-reinstall dist/asrquant-1.3.0rc1-py3-none-any.whl
python -c "import asrquant; assert asrquant.__version__ == '1.3.0rc1'"
pytest -q
```

Use this candidate to discover defects, numerical edge cases, API regressions, reproducibility issues and performance problems before producing the next candidate or the final 1.3.0 release.
