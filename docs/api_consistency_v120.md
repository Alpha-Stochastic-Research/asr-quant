# ASRQuant 1.2 — Public API consistency contract

ASRQuant 1.2 keeps the 1.x scientific implementations and adds a small canonical layer above them. Existing notebooks continue to work; new code should prefer the domain namespace plus one clear verb.

## Canonical verbs

| Domain | Canonical API | Result |
|---|---|---|
| Data | `asr.data.load(...)` | `pandas.DataFrame` |
| Data QA | `asr.data.validate(...)` | `DataQualityResult` |
| Backtesting | `asr.backtesting.run(...)` | `BacktestResult` |
| Portfolio | `asr.portfolio.optimize(...)` | `PortfolioOptimizationResult` |
| Derivatives | `asr.options.price(...)` | `OptionPrice` |
| Interest rates | `asr.rates.analyze(...)` / `asr.rates.calibrate(...)` | curve/calibration result |
| Statistics | `asr.stats.regress(...)` | `RegressionResult` or `ModelFitResult` |
| Machine learning | `asr.ml.fit(...)` | `WalkForwardMLResult` |

The older explicit functions (`run_backtest`, `price_option`, `minimum_variance`, `ols`, `walk_forward_fit`, and others) remain available for backwards compatibility and advanced use.

## Result contract

Analytical result objects should expose the following whenever the concept is meaningful:

```python
result.summary      # compact pandas Series
result.to_frame()   # tabular analytical output
result.to_dict()    # serializable audit/report payload
```

New ASRQuant 1.2 result classes additionally expose a stable `fingerprint` derived from their serializable contract.

## Exception hierarchy

Canonical wrappers translate low-level exceptions into domain errors under `asr.contracts`:

```text
ASRQuantError
├── InputValidationError
├── DataValidationError
├── PricingError
├── BacktestError
├── OptimizationError
├── CalibrationError
├── ModelFitError
└── ProviderError
```

The validation/pricing classes retain `ValueError` compatibility and execution/solver classes retain `RuntimeError` compatibility where appropriate.

## Hypothesis discovery is preserved

Version 1.2 does **not** remove the hypothesis engine introduced before this API cleanup.

The following remain public and tested:

```python
corpus = asr.LiteratureCorpus.from_pdfs("papers/")
registry = corpus.discover_hypotheses(topic="fixed income")

board = asr.discovery.from_literature(registry, topic="fixed_income")
project = board.start(0)
```

The weekly discovery flow is also unchanged:

```python
board = asr.discovery.weekly(
    data=curve_history,
    papers=corpus,
    domain="fixed_income",
    n=10,
)
```

Its contract remains:

`evidence -> observation -> research question -> hypothesis -> falsification rule -> ResearchProject -> robustness -> claim audit -> publication pack`

Automatic discovery never establishes global novelty. Literature provenance and falsification remain explicit.

## Why this layer exists

ASRQuant had strong functionality but several historical naming patterns: some modules returned arrays, others Series, others dataclasses; related entry points used different verbs; and low-level `ValueError`/`RuntimeError` exceptions were difficult to handle at application boundaries.

The 1.2 consistency layer solves this without rewriting mathematically validated implementations simply for style. The scientific core stays inspectable, while the public path becomes easier to learn and automate.
