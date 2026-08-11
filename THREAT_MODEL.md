# ASRQuant live-execution threat model

## Assets

- broker credentials;
- deployment signing key;
- broker account and capital;
- strategy and model artifacts;
- market data;
- risk policy;
- order and fill state;
- audit log;
- deployment certificate;
- operator identity and approval evidence.

## Trust boundaries

1. research environment;
2. CI and release system;
3. artifact registry or PyPI;
4. deployment host;
5. secret manager;
6. market-data provider;
7. broker API;
8. monitoring and alerting systems;
9. human operators.

## Principal threats and controls

### Accidental paper/live endpoint confusion

Controls: separate constructors, separate endpoints and credentials, live certificate and `ASRQUANT_LIVE_TRADING=ENABLED`.

### Credential disclosure

Controls: environment/secret-manager loading, redacted representations, no credential fields in audit payloads, secret scanning.

### Duplicate orders after network ambiguity

Controls: stable client-order ID, broker lookup before retry, durable intent and receipt events, reconciliation.

### Stale or manipulated market data

Controls: timestamp freshness check, symbol check, price collars, recommended secondary-feed comparison and emergency stop.

### Excessive order or position

Controls: notional, buying power, position, leverage, open-order, order-rate, turnover, daily-loss and drawdown limits.

### Unauthorized code or configuration

Controls: protected branch, reviewed release, artifact attestation, immutable version, signed certificate bound to policy hash and environment.

### Audit-log tampering

Controls: SQLite WAL, full synchronous mode, append-only API, SHA-256 hash chain, verification and backups.

### Process crash or host restart

Controls: persistent kill-switch file, durable event store, restart reconciliation, disaster-recovery and rollback gates.

### Compromised operator

Controls: at least two named certificate approvers, short certificate lifetime, least-privilege broker key, capital cap and independent monitoring.

### Model failure or regime change

Controls: model-validation approval, limited-capital canary, ongoing risk monitoring, drawdown/daily-loss kill switches and periodic recertification.

## Residual risks

- broker outage or incorrect broker state;
- exchange or venue malfunction;
- extreme gaps exceeding stop or collar assumptions;
- market-data vendor errors;
- simultaneous compromise of deployment and signing secrets;
- legal or regulatory obligations not represented in software;
- losses within configured limits;
- strategy decay and adverse selection.
