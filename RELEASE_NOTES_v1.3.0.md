# ASRQuant 1.3.0 — Research Infrastructure

ASRQuant 1.3.0 strengthens the infrastructure around quantitative research rather than replacing the 1.2 API.

## Highlights

- Market conventions: calendars, business-day rules, day counts, schedules and stubs.
- High-level rate instruments and a curve builder with quote repricing/Jacobian diagnostics.
- Quote-space curve risk and rate P&L explanation.
- Credit foundations: hazard/survival curves and CDS analytics/bootstrap.
- Advanced validation: CPCV, PBO, Reality Check, SPA, consolidated strategy screens, leakage diagnostics and multiverse/specification analysis.
- Data snapshots, local store and point-in-time availability/revision contracts.
- Experiment fingerprints/registry, research artifact lineage/stale propagation and cross-domain research reports.
- Generic calibration/sensitivities, scenario/cost models, robust portfolio tools, covariance estimator comparison, EVT tail risk, copulas, attribution, regimes and Monte Carlo variance reduction.
- Adapter protocols/registry for internal components.
- Public API signature snapshot and compatibility gate.
- New CLI commands: `info`, `doctor`, `validate`.

## Compatibility

The 1.0 paper contract, 1.1 rates/discovery stack and 1.2 canonical API remain in place. The runtime result monkey-patching previously retained for compatibility has been removed because supported result methods are now native.

## Scope

This release is quantitative research infrastructure. It does not claim to replace venue-specific market calendars, a complete credit/XVA stack, institutional market-data entitlement systems or exchange execution infrastructure.

## Public release gate

The source tree can be validated locally, but the public PyPI release should only be made after the exact release commit passes hosted multi-OS/Python CI and the TestPyPI workflow.
