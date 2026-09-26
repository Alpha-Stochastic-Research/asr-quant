# ASRQuant 1.3.0 — Final Stable Release

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

## Final audit corrections

The final 1.3.0 build closes the confirmed release-candidate findings:

- **FIND-003:** key-rate zero bumps now use each side's own pillar spacing, restoring the partition-of-unity behaviour on uneven market grids.
- **FIND-006:** Gaussian-process observation noise is a fixed user contract rather than an optimizer-adjusted hyperparameter reported under the requested value.
- **FIND-011:** PSR/DSR now use the per-observation Sharpe scale required by the published statistic.
- **FIND-012:** the statsmodels interface no longer passes removed `old_names` / `verbose` keywords.
- **FIND-013:** RSI-14 defaults to Wilder smoothing and exposes the legacy SMA convention explicitly.
- **FIND-014:** implied-volatility inversion refuses the discounted-intrinsic boundary when volatility is not identifiable instead of returning the solver's lower bracket.
- **FIND-015:** yield-curve PCA components use deterministic sign orientation.
- Vasicek calibration now reports delta-method uncertainty for the AR(1) coefficient and mean-reversion speed.
- `summary_metrics` exposes `omega_threshold`, so Omega is no longer forced to duplicate Profit Factor at a zero threshold.

Packaging was also tightened: Matplotlib/Plotly/Jinja2, scikit-learn, requests and pypdf moved behind optional extras, while the corresponding code paths use lazy imports. The final package therefore keeps a smaller core install and a lighter `import asrquant`.

## Native quantitative engines

ASRQuant 1.3.0 does not depend on an external quantitative-finance pricing engine. Pricing, curve construction, rate risk, calibration and related financial analytics are implemented within ASRQuant. Validation is based on analytical identities, round-trip recovery, limiting cases, invariants, regression tests and explicit convention checks. General-purpose scientific libraries remain dependencies where appropriate, but they do not replace ASRQuant's financial-engine implementations.
The repository also includes `benchmarks/native_engine_contracts.py` for selected analytical and round-trip contracts using only ASRQuant and its scientific core.

## Compatibility

The 1.0 paper contract, 1.1 rates/discovery stack and 1.2 canonical API remain in place. The runtime result monkey-patching previously retained for compatibility has been removed because supported result methods are now native.

## Scope

This release is quantitative research infrastructure. It does not claim to replace venue-specific market calendars, a complete credit/XVA stack, institutional market-data entitlement systems or exchange execution infrastructure.

## Release provenance

The final 1.3.0 source and distribution metadata recognize Alpha Kabinet TOURE and Srijan Mishra as software contributors, with Alpha Stochastic Research as institutional maintainer. Srijan Mishra’s recorded v1.3.0 contribution covers clean-runtime package verification, public API surface mapping, reproducibility/numerical QA, and validation-template defect discovery.

The final artifact version is `1.3.0` (not an RC). Public PyPI publication should still be performed only from the exact tagged commit after hosted multi-OS/Python CI and the publication workflow are green.
