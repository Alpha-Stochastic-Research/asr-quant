# ASRQuant 1.3.0rc1 — Pytest Release Candidate

ASRQuant `1.3.0rc1` is a pre-release package candidate for independent validation of the upcoming 1.3.0 release. It is not the final published 1.3.0 artifact.

## Purpose

The candidate is intended to be installed, exercised and challenged with `pytest` before final release. Validation should focus on API regressions, mathematical and quantitative correctness, numerical stability, input validation, reproducibility, integration workflows and performance-sensitive paths.

## Candidate boundaries

- Package version: `1.3.0rc1`
- Final target: `1.3.0`
- Full source and tests included
- Unpublished manuscript directory excluded
- No final 1.3.0 wheel or source distribution included

## Primary test command

```bash
python -m pip install -e ".[dev]"
python scripts/test_all.py --group all
```

The grouped runner invokes pytest in isolated domain processes. A direct quick run is also available:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src MPLBACKEND=Agg pytest -q
```
