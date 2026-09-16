# ASRQuant 1.3.0 — Final release notes

ASRQuant 1.3.0 strengthens the project as an auditable quantitative-finance research and market-infrastructure library while preserving the public 1.x workflow.

## Correctness fixes promoted from independent validation

- **Key-rate DV01 / hedge partition (FIND-003):** uneven market-pillar grids now use asymmetric hat functions instead of applying the widest neighbouring gap to both sides.
- **Gaussian-process noise contract (FIND-006):** the requested white-noise level is held fixed and reported consistently.
- **Probabilistic / Deflated Sharpe (FIND-011):** PSR now uses the per-observation Sharpe scale required by the published formula instead of annualising the sample Sharpe before the probability calculation.
- **statsmodels 0.15 compatibility (FIND-012):** removed third-party keywords are no longer forwarded; the legacy `old_names` argument remains accepted as a deprecated no-op.
- **RSI convention (FIND-013):** Wilder smoothing is the 1.3 default; SMA remains available explicitly through `rsi_method="sma"`.
- **Implied-volatility boundary (FIND-014):** an intrinsic-boundary quote is rejected as non-identifiable instead of returning the numerical lower solver bound as a calibrated volatility.
- **Yield-curve PCA sign (FIND-015):** components receive a deterministic sign orientation so rolling windows do not flip merely because SVD eigenvectors are sign-indeterminate.

## New institutional market layer

### Conventions and schedules

`asr.conventions` and the `asr.rates` namespace now expose explicit business-day conventions, day-count rules, calendars, end-of-month handling, fixing/payment lags and regular schedules.

### Credit

`asr.credit` adds:

- piecewise-constant hazard curves;
- survival and default probabilities;
- CDS premium/protection legs and par spread;
- CS01-style spread sensitivity;
- jump-to-default diagnostics;
- sequential CDS hazard bootstrapping with repricing diagnostics.

### Scenario engine

`asr.scenarios` introduces named rate level/slope/curvature shocks, volatility/liquidity descriptors, curve shocking and instrument-agnostic portfolio repricing.

### Research reproducibility

The new research utilities add deterministic data fingerprints, non-executable JSON-table snapshots, local snapshot verification, experiment identities, append-only experiment registries, dependency graphs and multi-format research reports.

### Selection-risk validation

The validation namespace gains purged K-fold and combinatorial purged CV splits, CSCV-style Probability of Backtest Overfitting, moving-block White-style Reality Check, SPA-style studentised tests, leakage diagnostics and multiverse evaluation.

### QuantLib interoperability

`asr.quantlib_bridge` is an **optional validation/interoperability layer**. ASRQuant does not depend on QuantLib; when the optional `interop` extra is installed, selected ASRQuant outputs can be cross-checked against a second implementation.

## Positioning relative to QuantLib

ASRQuant 1.3.0 is not presented as a complete replacement for QuantLib's decades of instrument/pricing-engine coverage. The 1.3 direction is different and complementary: combine transparent quantitative methods with research provenance, hypothesis workflow, selection-risk controls, point-in-time discipline, backtesting, machine learning, portfolio research and guarded execution in a single auditable Python interface.

The objective is to exceed specialised pricing libraries on **research traceability and end-to-end quantitative workflow**, while progressively expanding market-instrument depth with independent numerical validation.

## Release gates

The final release is intended to pass:

- Python 3.10–3.13 on Linux, macOS and Windows;
- the 1.x regression groups plus dedicated 1.3 regression tests;
- wheel/sdist build and strict Twine metadata validation;
- clean wheel installation and version consistency;
- Ruff correctness checks, production-boundary type checks, dependency/security audit, secret scan and SBOM generation.

No public-release claim should be made until the exact release commit passes those hosted gates.
