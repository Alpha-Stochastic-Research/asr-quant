# Migrating from ASRQuant 1.2 to 1.3

## Compatibility policy

The 1.3 release is additive. Existing 1.2 canonical entry points remain supported:

```python
asr.data.load(...)
asr.data.validate(...)
asr.hypotheses.discover(...)
asr.backtesting.run(...)
asr.portfolio.optimize(...)
asr.options.price(...)
asr.rates.analyze(...)
asr.rates.calibrate(...)
asr.stats.regress(...)
asr.ml.fit(...)
```

The literature/data hypothesis-discovery workflow is preserved.

## Recommended new APIs

### Rates

Use `asr.rates.Calendar`, `Schedule`, rate-instrument classes and `CurveBuilder` for workflows that need explicit market conventions and quote diagnostics. The lower-level `bootstrap_discount_curve` remains strict and unchanged.

### Validation

Use `asr.validation` when comparing many strategies/specifications or when chronology/leakage controls matter.

### Data lineage

Wrap research datasets with `asr.data.snapshot` or `DataStore` when the exact dataset used in an experiment must be recoverable.

### Experiment lineage

Use `asr.research.Experiment` and `ExperimentRegistry` for parameter/data/code fingerprints.

## Result serialization

The canonical installer no longer patches result classes at runtime. Existing result methods such as `summary`, `to_frame()` and `to_dict()` are native class methods where supported. User code should not depend on the old internal patching function.

## Public API compatibility

`python scripts/check_public_api.py` checks the declared 1.3 stable surface. Any intentional breaking change should be documented and deferred to a major release rather than silently merged into a 1.x release.
