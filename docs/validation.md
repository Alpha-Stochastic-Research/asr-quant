# Validation strategy for ASRQuant 1.0.0

## Verified locally

- 74 research, numerical-modelling, backtest, statistics and visualization tests pass.
- 62 production-readiness and guarded-live tests pass.
- Aggregate automated tests: 136.
- Production-boundary line coverage: 93% (`production.py`, `audit_store.py`, `live.py`).
- Live authorization fails closed without a valid certificate and explicit environment arm.
- Audit hash-chain tampering, duplicate order identifiers, stale data, price collars, capital limits, reconciliation mismatches and persistent kill-switch behavior are tested.

## Evidence that must come from CI or the target operator

- supported OS/Python matrix;
- static analysis and type-check results;
- vulnerability, dependency and secret scans;
- full transitive SBOM and artifact attestation;
- reproducible-build comparison;
- real broker-paper longevity and order-state evidence;
- monitoring/alert delivery, backup/restore, disaster recovery and rollback exercises;
- legal/compliance, data-license and independent model-validation approvals.

The local validation report is `VALIDATION_v1.0.0.txt`. A live deployment must additionally produce a passing `ProductionReadinessReport` for its own environment.
