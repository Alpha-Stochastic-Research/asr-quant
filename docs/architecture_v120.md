# ASRQuant 1.2 architecture

ASRQuant 1.2 keeps the mature 1.x numerical modules intact while introducing a cleaner public surface.

## Layers

1. **Data & provenance** — files, URLs, providers, quality checks, fingerprints.
2. **Research discovery** — literature, data-driven hypotheses, candidate boards.
3. **Quantitative analytics** — alpha, factors, statistics, risk, microstructure.
4. **Pricing & modelling** — derivatives, rates, stochastic processes, volatility.
5. **Portfolio & validation** — optimization, backtests, robustness, implementation audits.
6. **Research operations** — projects, weekly cycles, reports, manifests.
7. **Execution boundary** — paper trading, production-readiness, live guardrails.

## Compatibility rule

The 1.2 release does not delete the established root-level 1.x functions. New code should prefer domain namespaces such as `asr.data`, `asr.risk`, `asr.factors`, `asr.hypotheses`, `asr.backtesting` and `asr.rates`.

## Result contract

New structured results implement a common convention:

- `summary`: compact metrics;
- `to_frame()`: tabular analytical payload;
- `to_dict()`: serializable metadata/summary;
- `fingerprint` when provided by the result mixin or underlying engine.

## Errors

Domain wrappers use the hierarchy in `asrquant.contracts`:

- `ASRQuantError`
- `InputValidationError`
- `DataValidationError`
- `BacktestError`
- `OptimizationError`
- `PricingError`
- `CalibrationError`
- `ModelFitError`
- `ProviderError`
- `HypothesisDiscoveryError`

Lower-level 1.x functions keep their historical exceptions for backwards compatibility.
