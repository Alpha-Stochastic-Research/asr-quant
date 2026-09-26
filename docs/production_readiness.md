# Production readiness and ASRQuant 1.0

## Purpose

ASRQuant distinguishes a package release from a production trading deployment. A release may contain live-capable code while a particular deployment remains unauthorized. The production gate therefore requires evidence from software engineering, model validation, broker testing, operations, compliance, data licensing and accountable human approval.

The gate follows a fail-closed design:

- every evidence field defaults to a failing value;
- a certificate cannot be issued while any required check fails;
- a certificate is tied to one package version, broker, account fingerprint, risk policy and maximum capital;
- certificates expire;
- live broker construction also requires an environment-level arm;
- changing the signed payload invalidates the HMAC signature.

## Required evidence

`DeploymentEvidence` contains the following required groups.

### Software quality

- immutable release version;
- successful CI;
- minimum test count;
- minimum coverage;
- static analysis and type checks;
- dependency vulnerability scan;
- secret scan;
- software bill of materials;
- signed or attested artifacts;
- reproducible-build verification.

### Operational resilience

- disaster-recovery exercise;
- rollback exercise;
- monitoring;
- alerting;
- durable audit log;
- time synchronization;
- no unresolved critical incident.

### Broker-paper validation

- minimum number of observed paper-trading days;
- minimum number of paper orders;
- zero unresolved reconciliation mismatch.

### Governance

- operator approval;
- legal/compliance review;
- data-license review;
- strategy-owner approval;
- independent model-validation approval;
- change-control ticket.

## Default thresholds

`ProductionReadinessGate()` requires by default:

- at least 100 automated tests;
- at least 90% line coverage;
- at least 30 broker-paper days;
- at least 500 broker-paper orders.

These values are minimum software defaults, not universal regulatory thresholds. A firm may configure stricter values.

## Example

```python
import asrquant as asr

evidence = asr.DeploymentEvidence(
    release_version=asr.__version__,
    ci_passed=True,
    test_count=120,
    coverage_percent=92.0,
    static_analysis_passed=True,
    dependency_scan_passed=True,
    secrets_scan_passed=True,
    sbom_present=True,
    artifacts_signed=True,
    reproducible_build_verified=True,
    disaster_recovery_tested=True,
    rollback_tested=True,
    monitoring_enabled=True,
    alerting_enabled=True,
    durable_audit_log_enabled=True,
    time_synchronization_verified=True,
    broker_paper_days=45,
    broker_paper_orders=1000,
    reconciliation_mismatches=0,
    unresolved_critical_incidents=0,
    operator_approved=True,
    legal_compliance_reviewed=True,
    data_licenses_reviewed=True,
    strategy_owner_approved=True,
    model_validation_approved=True,
    change_ticket="CHG-2026-001",
)

report = asr.ProductionReadinessGate().evaluate(evidence)
report.save("readiness-report.json")
assert report.ready
```

## Certificate issuance

```python
certificate = asr.DeploymentCertificate.issue(
    report=report,
    evidence=evidence,
    secret_key=signing_key,
    release_version=asr.__version__,
    broker="alpaca",
    account_id=account_id,
    account_salt=account_salt,
    risk_policy=policy,
    max_live_capital=50_000,
    approved_by=("risk-owner", "operations-owner"),
    validity_hours=24,
)
```

The signing key should be provided by a secret manager or protected deployment service. It must never be committed to the repository or stored beside the certificate.

## What the certificate does not prove

A valid certificate does not prove profitability, causality, regulatory registration, suitability for another account, or future market behavior. It only proves that the configured deployment gate was satisfied and that the authorization payload has not been modified.

## Promotion path

Recommended promotion sequence:

1. research backtest;
2. independent model validation;
3. deterministic internal paper broker;
4. real broker paper environment;
5. shadow mode with live market data but no orders;
6. limited-capital canary deployment;
7. controlled capital increase after a new review;
8. periodic recertification.

Every promotion should use a new change ticket and certificate.
