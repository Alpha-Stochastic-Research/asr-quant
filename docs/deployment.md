# Deployment guide for ASRQuant 1.0.0

## Status

`1.0.0` is the first stable public-API release. Stable software status does **not** certify any particular live-capital deployment. Live authorization remains deployment-specific and fail-closed.

## Software deployment

```bash
python -m pip install asrquant==1.0.0
asrquant --version
```

Build and validate from a clean checkout:

```bash
python -m build
python -m twine check dist/*
python scripts/test_all.py --group core
python scripts/test_all.py --group quant
python scripts/test_all.py --group surfaces
python scripts/test_all.py --group api
python scripts/test_all.py --group paper
python scripts/test_all.py --group production
```

The paper-contract group is mandatory for a stable release because it executes the public workflows and capability claims used by manuscript v0.1.0.

## Readiness evidence for live capital

Copy `deployment/evidence.template.json` and replace every placeholder with evidence from the target environment. Evaluate it with:

```bash
asrquant readiness deployment/evidence.json --output deployment/readiness-report.json
```

Exit code `0` means the configured readiness checks passed. Exit code `2` means the deployment remains blocked.

## Live authorization

A passing software release is necessary but not sufficient for live capital. Any live deployment should bind authorization to the exact package version, broker/account fingerprint, risk-policy hash, authorized capital, named approvers and expiration time.

See `docs/production_readiness.md`, `docs/live_trading.md`, `docs/operations_runbook.md` and `PRODUCTION_READINESS_CHECKLIST.md`.
