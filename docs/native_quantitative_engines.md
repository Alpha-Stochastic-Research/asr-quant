# Native quantitative engines

ASRQuant keeps its finance-specific numerical logic inside the package. Pricing, curve construction, rate risk, calibration and related derivative analytics are **not delegated to an external quantitative-finance pricing engine**.

General-purpose scientific libraries such as NumPy, SciPy, pandas and statsmodels remain part of the numerical stack where appropriate. They provide numerical primitives, array operations, data structures and econometric routines; they do not replace ASRQuant's finance-model implementations.

## Validation philosophy

Native implementations are validated through contracts that remain meaningful independently of any vendor or third-party finance library:

- **Analytical identities** — e.g. European-option put-call parity.
- **Inverse / round-trip checks** — e.g. price -> implied volatility -> repriced option.
- **Curve invariants** — discount-factor positivity/ordering where the convention implies it, quote repricing and key-rate partition checks.
- **Limiting and boundary cases** — explicit treatment of non-identifiable implied-volatility boundaries and degenerate inputs.
- **Deterministic conventions** — explicit day-count, calendar, smoothing and PCA-orientation semantics.
- **Regression fixtures** — confirmed defects receive tests that prevent silent reintroduction.
- **Reproducibility controls** — deterministic seeds, experiment fingerprints and artifact lineage where stochastic workflows are involved.

## Native validation benchmark

The repository includes `benchmarks/native_engine_contracts.py`. It exercises selected model identities using only ASRQuant and the scientific core. It is a validation aid, not a claim that the covered contracts exhaust every model risk.

```bash
PYTHONPATH=src python benchmarks/native_engine_contracts.py
```

A successful run reports the selected contracts as PASS. The package test suite remains the release gate and provides broader coverage.

## Scope boundary

Native implementation does not imply that ASRQuant reproduces every instrument, convention or market feature found in large institutional libraries. The design goal is different: finance-specific behavior should be inspectable, testable and extensible directly in ASRQuant, with assumptions and conventions made explicit rather than hidden behind an external pricing engine.
