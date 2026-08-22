# Quickstart

## 1. Local CSV to audited backtest

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
print(result.metrics)
result.plot("dashboard")
result.report("report.html")
```

## 2. Remote data

```python
lab = QuantLab.from_provider("yahoo", ["SPY", "QQQ"], start="2018-01-01")
```

```python
lab = QuantLab.from_provider("binance", ["BTCUSDT", "ETHUSDT"], interval="1h", limit=1000)
```

Alpha Vantage and FRED require API keys. Yahoo requires the `data` extra.

## 3. Monte Carlo

```python
sim = lab.monte_carlo("gbm", drift=0.05, volatility=0.20, paths=10_000, random_state=7)
print(sim.summary)
sim.plot("fan")
```

```python
mc = lab.option(
    "monte_carlo", strike=100, maturity=1, rate=0.03,
    volatility=0.20, paths=100_000, antithetic=True, random_state=7,
)
print(mc.summary)
```

## 4. Closed-form and tree pricing

```python
bsm = lab.option("black_scholes", strike=100, maturity=1, rate=0.03, volatility=0.20)
bach = lab.option("bachelier", strike=100, maturity=1, rate=0.03, normal_volatility=10)
tree = lab.option("crr", strike=100, maturity=1, rate=0.03, volatility=0.20, steps=1000)
```

## 5. Martingale diagnostics

```python
diagnostic = lab.martingale_test(rate=0.03, lags=10)
print(diagnostic.statistics)
diagnostic.plot()
```

## 6. Regression

```python
fit = lab.regress("SPY", ["QQQ", "TLT"], covariance="HAC", maxlags=5)
print(fit.coefficients)
fit.plot("residuals")
```

## 7. Walk-forward ML

```python
import asrquant as asr

X = lab.ml_features("SPY").shift(1)
y = asr.forward_target(lab.prices["SPY"], horizon=5)
wf = lab.ml_walk_forward("ridge", X, y, train_size=504, test_size=63, gap=5, model_params={"alpha": 1.0})
print(wf.aggregate_metrics)
```

## Input contract

- index: unique, sortable timestamps;
- values: finite positive prices for `QuantLab`;
- columns: unique asset identifiers;
- missing observations: rejected by default, or explicitly dropped/forward-filled;
- target weights: same index and a subset of the same asset columns;
- execution: one-bar delay by default.

## Built-in strategies

`buy_hold`, `sma`, `momentum`, `mean_reversion`, `vol_target`, `breakout`, `bollinger`, `rsi`, and `pairs`.

Built-in strategies are examples and reusable primitives, not investment recommendations.

## 8. N-dimensional parameter surface

```python
surface = lab.parameter_surface(
    experiment,
    {
        "gamma": [0.5, 1, 2, 4],
        "cost_bps": [0, 5, 10],
        "hedge_every": [1, 5, 20],
        "volatility": [0.15, 0.30],
    },
    x="gamma",
    y="cost_bps",
    animate_by=["hedge_every", "volatility"],
    metric="metrics.utility",
)
surface.save_animation("parameter_landscape.html")
```

The HTML output includes a frame slider. Use `.gif` or `.mp4` for video-style
exports, and `surface.best("max")` to retrieve the best finite point.
