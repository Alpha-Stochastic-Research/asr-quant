# One-import ASRQuant API

ASRQuant v1.2.0 preserves the one-import public contract introduced in 1.0.0:

```python
import asrquant as asr
```

Users do not need to import plotting, machine-learning, econometric, numerical or table libraries directly for normal workflows. ASRQuant installs and calls validated engines internally while owning the public names, argument normalization, result objects and reproducibility metadata.

## Data

```python
lab = asr.open_lab("prices.csv", date_column="Date")
remote = asr.open_lab(provider="yahoo", symbols=["SPY", "QQQ"], start="2020-01-01")
frame = asr.frame({"SPY": [100, 101]}, index=asr.date_range("2026-01-01", periods=2))
```

## Visualizations

```python
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
asr.show(result, kind="dashboard")
asr.save(result, "equity.png", kind="equity", dpi=180)
```

`asr.visualize(...)` returns a `PlotHandle` with `show()`, `save()` and `close()`. `PlotHandle.raw` exists only for exceptional advanced backend access.

## Machine learning

```python
model = asr.models.random_forest(
    task="regression", trees=500, depth=6, seed=7
)
result = lab.ml(
    model, train_size=504, test_size=63, gap=5
)
```

A model name can replace the model object:

```python
result = lab.ml(
    "ridge",
    train_size=504,
    test_size=63,
    model_params={"alpha": 1.0},
)
```

Available factories include linear regression, ridge, lasso, elastic net, logistic regression, decision trees, random forests, extra trees, gradient boosting, histogram gradient boosting, KNN, SVM, Gaussian naive Bayes, PCA, k-means and isolation forests.

## Numerical functions

```python
x = asr.math.linspace(0.1, 5.0, 50)
y = asr.math.normal_cdf(x)
rng = asr.math.random_generator(7)
```

The namespace includes arrays, grids, exponentials, logarithms, trigonometric functions, reductions, quantiles, normal distribution functions and stable `logsumexp`.

## Scientific namespaces

- `asr.stats`: econometrics and statistical inference;
- `asr.portfolio`: portfolio construction and optimization;
- `asr.options`: derivatives and Greeks;
- `asr.stochastic`: stochastic processes and Monte Carlo;
- `asr.rates`: fixed income;
- `asr.vol`: volatility;
- `asr.visuals`: lower-level visualization catalog.

## Design boundary

ASRQuant does not claim to reproduce from scratch every algorithm implemented by mature scientific libraries. That would increase numerical risk and maintenance burden. Instead, it provides a stable, finance-oriented facade and keeps the engines replaceable behind the public ASRQuant contract.


## Literature-to-decision workflow

```python
import asrquant as asr

project = asr.research.from_pdfs("papers/", topic="rates and equity styles")
registry = project.discover_hypotheses()
project.select_hypothesis("H001", predictor="US10Y", expected_sign="positive")
```

The same namespace provides data planning, feature construction, econometric testing, backtesting, robustness, decision governance and paper trading. `asr.trading` exposes broker-neutral order primitives and the safe built-in paper broker.
