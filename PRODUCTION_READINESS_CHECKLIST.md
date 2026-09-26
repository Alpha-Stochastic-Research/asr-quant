# ASRQuant production-readiness checklist

## Release engineering

- [ ] Release commit reviewed and protected.
- [ ] CI passes on Linux, macOS and Windows for supported Python versions.
- [ ] At least 100 automated tests pass.
- [ ] Line coverage is at least 90% or every exception is approved and documented.
- [ ] Static analysis and type checks pass.
- [ ] Dependency vulnerability scan passes.
- [ ] Secret scan passes.
- [ ] SBOM generated.
- [ ] Wheel and source distributions built twice and compared.
- [ ] Release artifacts attested or signed.
- [ ] Clean-environment installation verified.

## Model and strategy

- [ ] Economic rationale documented.
- [ ] Data provenance and licensing reviewed.
- [ ] Look-ahead, survivorship and revision risks reviewed.
- [ ] Out-of-sample and walk-forward validation completed.
- [ ] Multiple-testing corrections applied when relevant.
- [ ] Cost, delay, liquidity and capacity stress tests completed.
- [ ] Independent model validation approved.
- [ ] Stop conditions and retirement criteria documented.

## Broker paper environment

- [ ] Correct broker paper account and credentials confirmed.
- [ ] At least 30 calendar days observed.
- [ ] At least 500 orders exercised across expected order states.
- [ ] Partial fills, rejects, cancellations and reconnects tested.
- [ ] Market-open/closed behavior tested.
- [ ] Zero unresolved reconciliation mismatch.
- [ ] Broker paper limitations documented.

## Operations

- [ ] Monitoring dashboards enabled.
- [ ] Alerts delivered to on-call operators.
- [ ] Persistent kill switch tested.
- [ ] Audit database backup and restore tested.
- [ ] Disaster recovery exercised.
- [ ] Rollback exercised.
- [ ] Time synchronization verified.
- [ ] Operations runbook reviewed.
- [ ] Incident-response contacts confirmed.

## Governance and compliance

- [ ] Legal/compliance review completed for jurisdiction, broker, instruments and venue.
- [ ] Broker/API terms reviewed.
- [ ] Market-data licenses reviewed.
- [ ] Strategy owner approved instruments and capital.
- [ ] Risk owner approved policy.
- [ ] Operations owner approved deployment.
- [ ] Change ticket created.
- [ ] Two named certificate approvers recorded.

## Live canary

- [ ] Certificate issued for the exact release, account, policy and environment.
- [ ] Initial capital is below the certificate limit.
- [ ] Symbol allowlist is minimal.
- [ ] Leverage, position, order and daily-loss limits are conservative.
- [ ] Shadow-mode outputs agree with broker-paper outputs.
- [ ] First live session is actively supervised.
- [ ] End-of-day reconciliation and audit verification completed.
