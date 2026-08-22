# 10-minute Quickstart

This example uses deterministic synthetic data so that the workflow can be reproduced without an external data provider.

## 1. Create a market panel

```python
import numpy as np
import pandas as pd
import asrquant as asr

rng = np.random.default_rng(42)
index = pd.date_range("2024-01-02", periods=320, freq="B")
returns = pd.DataFrame(
    rng.normal(0.0002, 0.01, size=(len(index), 4)),
    index=index,
    columns=["A", "B", "C", "D"],
)
prices = 100.0 * (1.0 + returns).cumprod()
```

## 2. Validate the data

```python
quality = asr.data.validate(prices)
print(quality.summary)
```

Validation inspects the time-series contract without silently cleaning or mutating the input.

## 3. Construct a portfolio

```python
portfolio = asr.portfolio.optimize(
    returns,
    method="minimum_variance",
)
print(portfolio.summary)
print(portfolio.weights)
```

## 4. Backtest the weights

```python
weights = pd.DataFrame(
    np.tile(portfolio.weights.to_numpy(), (len(prices), 1)),
    index=prices.index,
    columns=prices.columns,
)

result = asr.backtesting.run(prices, weights)
print(result.summary)
```

## 5. Price an option

```python
option = asr.options.price(
    "black_scholes",
    spot=100,
    strike=100,
    maturity=1.0,
    rate=0.03,
    volatility=0.20,
)
print(option.summary)
```

## 6. Build and inspect a yield curve

```python
maturities = np.array([0.5, 1, 2, 5, 10.0])
zero_rates = np.array([0.020, 0.021, 0.022, 0.025, 0.028])

rates_lab = asr.RateQuantLab.from_zero_rates(maturities, zero_rates)
curve_report = asr.rates.analyze(rates_lab.curve)
print(curve_report.summary)
```

## Next

Use the [official notebook](../notebook.md) for a single executable walkthrough that also covers alpha, risk, microstructure, hypothesis discovery, statistics and walk-forward ML.
