# Changelog

## 1.2.0 — 2026-08-19

- Reorganized the public API around stable domain namespaces and canonical verbs.
- Added local/URL/provider data facade, including Yahoo Finance and ECB yield-curve convenience access.
- Added data-driven and literature-driven hypothesis discovery, search and conservative novelty audit.
- Added cross-sectional alpha research tools.
- Added portfolio risk analytics and scenario decomposition.
- Added factor research: PCA, factor exposures, rolling beta and factor-risk decomposition.
- Added market microstructure analytics including spread, microprice, OFI, Amihud, Roll and Kyle lambda.
- Added shared structured result and domain exception contracts.
- Preserved the 1.0 paper contract and 1.1 Research Discovery / Interest Rates APIs.
- Corrected repository URLs to `Alpha-Stochastic-Research/asr-quant`.

## 1.1.0 - 2026-08-11

### Added

- Research Discovery engine that turns market, yield-curve, literature, model-disagreement and robustness evidence into ranked falsifiable research candidates without auto-asserting novelty.
- Friday-to-Friday `WeeklyResearchCycle` with research brief, research-note template, claim audit, reproducibility checklist, project manifest and publication-pack generation.
- Comprehensive `asr.rates` interest-rate research stack: conventions, curves, multi-curve bootstrapping, FRAs, futures, swaps, OIS/RFR, basis swaps, bonds/bond forwards, curve risk, caps/floors, swaptions, implied rate volatility, caplet stripping, SABR, short-rate models, HJM/LMM, FX-forward/cross-currency and ZC-inflation foundations, curve hedging and Bermudan LSM.
- Nelson-Siegel and Nelson-Siegel-Svensson curve evaluation/calibration.
- ECB Data Portal provider plus aligned euro-area AAA yield-curve downloads and `RateQuantLab.from_ecb()`.
- Yield-curve PCA, level/slope/curvature factors, no-arbitrage diagnostics, interpolation-risk and carry/roll analytics.
- Built-in Interest Rate Derivatives Quant curriculum and exercise bank.
- Team operating-model, Research Discovery and Interest Rate Derivatives documentation plus executable examples.

### Changed

- `asr.rates` now points to the expanded interest-rate module while preserving the legacy fixed-income public helpers.
- Production-readiness release matching now follows the exact installed ASRQuant release instead of hard-coding the 1.0.0 family.

## 1.0.0 - 2026-08-10

- First stable public-API release corresponding to manuscript v0.1.0.
- Added an 18-test executable paper-contract suite; total automated test count is 154.
- Reconciled every manuscript appendix workflow with the one-import API.
- Hardened fixed-income curve bootstrapping with explicit coupon-frequency and complete-grid validation.
- Regenerated empirical benchmarks and paper figures from the stable codebase.
- Stabilized release, coverage, security and PyPI workflows for the 1.0.0 distribution.
- Kept live-capital authorization separate and fail-closed from software release status.

## 1.0.0rc3 - 2026-08-01

### Fixed

- Restored compatibility across Matplotlib 3.8–3.11+ with a boxplot keyword fallback for `tick_labels` and legacy `labels`.
- Explicitly load the `pytest-cov` plugin when global pytest plugin autoload is disabled.
- Audit only shipped runtime dependencies instead of mixing development tooling into the blocking dependency gate, and generate the SBOM from an isolated installed-runtime environment.
- Removed unused imports and aligned the Ruff profile with correctness-oriented rules.
- Included the rc2 Monte Carlo and approximation tests in isolated CI domain groups.

### Changed

- Added bounded major-version ranges for runtime dependencies to reduce accidental breaking upgrades.
- Added `requirements/runtime.txt` as the canonical runtime dependency-audit input.

## 1.0.0rc2 - 2026-08-01

### Added

- Universal Monte Carlo engine implementing generate -> transform -> reduce for arbitrary scenario generators and pathwise quantities.
- Generic expectation, probability, variance, standard deviation, standard error, confidence interval, quantile, VaR and Expected Shortfall estimators.
- Inverse-transform sampling, normal sampling, Cholesky-correlated Gaussian scenarios and generic scalar/vector Euler-Maruyama simulation.
- Path-dependent hedging loss and proportional transaction-cost utilities.
- Static and animated Monte Carlo parameter surfaces.
- Linear and bilinear interpolation, cubic splines, Gaussian kernel regression, RBF interpolation and Gaussian-process surrogates.
- Controlled extrapolation, response-surface linear/polynomial/ridge/lasso regression, RMSE/MAE/R-squared validation, gradients and Hessians.
- Explicit AR(p) interface and high-level `QuantLab` wrappers for universal Monte Carlo, Monte Carlo surfaces, approximation, AR and GARCH.

### Changed

- `SurfaceResult` now exposes first- and second-order sensitivity surfaces through `gradient()` and `hessian()`.
- Release candidate advanced from rc1 to rc2 after filling the generic simulation and approximation gaps identified in the scientific audit.

## 1.0.0rc1 - 2026-08-01

### Added

- Production-readiness evidence gate and signed, expiring deployment certificates.
- Guarded Alpaca paper/live broker adapter.
- Pre-trade live risk engine, persistent kill switch, reconciliation and durable audit store.
- Operations, security, threat-model and regulatory-control documentation.
- 62 production-hardening tests, bringing the total collected suite to 126 tests.

### Changed

- Version moved from research alpha 0.5.0 to production-hardening release candidate 1.0.0rc1.
- Security policy and CI/release expectations expanded for live-capable deployments.

## 0.5.0 - 2026-08-01

- Added PDF paper ingestion with page-level provenance and corpus fingerprints.
- Added source-linked hypothesis discovery and corpus-relative novelty labels.
- Added the complete `ResearchProject` workflow from hypothesis through data, features, signals, econometric testing, backtesting, robustness, decisions, manifests, and reports.
- Added provider-assisted data-plan downloads and leakage-aware feature specifications.
- Added order-level paper trading, broker-neutral interfaces, order states, partial fills, cash and position accounting, and risk controls.
- Added CLI `papers` and `research` commands.
- Added literature-to-decision and algorithmic-trading guides and examples.
- Expanded the automated suite to 64 tests.

## 0.1.0 - 2026-07-31

Initial research release.

- Added specification-first multi-asset backtesting.
- Added transparent linear, nonlinear, and borrow costs.
- Added implementation-contract audit.
- Added performance, risk, regression, validation, portfolio, derivatives, and simulation modules.
- Added 69 user-facing visualizations.
- Added self-contained HTML reports and reproducibility manifests.
- Added 26 automated tests, examples, benchmarks, and a 24-page paper.
