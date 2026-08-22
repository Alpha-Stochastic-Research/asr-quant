# Statistics & Machine Learning

## Regression

```python
fit = asr.stats.regress(
    y,
    X,
    method="ols",
)
print(fit.summary)
```

The canonical wrapper supports OLS, quantile, logistic, polynomial, factor and regularized regression variants.

## Walk-forward machine learning

```python
wf = asr.ml.fit(
    "ridge",
    features,
    target,
    train_size=120,
    test_size=30,
    gap=1,
)
print(wf.summary)
```

The walk-forward API keeps training and testing chronological. A gap can be used when the target horizon or feature construction requires an embargo between training and evaluation windows.

## Statistical research utilities

The broader statistics namespace includes rolling regression, stationarity diagnostics, block bootstrap, permutation tests, Benjamini-Hochberg multiple-testing control, cointegration, Granger causality and time-series model helpers.
