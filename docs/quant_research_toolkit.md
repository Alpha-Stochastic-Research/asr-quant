# Quant Research Toolkit

ASRQuant 1.2 adds three focused research namespaces to the one-import API:

```python
import asrquant as asr

asr.alpha
asr.risk
asr.microstructure
```

The design goal is to cover common quant-research tasks without turning the top-level API into a collection of unrelated helper functions.

## Alpha research

`asr.alpha` is for cross-sectional signal research.

```python
signal = asr.alpha.cross_sectional_zscore(raw_signal)
forward = asr.alpha.forward_returns(prices, 5)[5]
report = asr.alpha.analyze_signal(signal, forward, quantiles=5)

print(report.summary)
print(report.quantile_returns)
```

Available building blocks include:

- cross-sectional winsorization;
- ranks and z-scores;
- exposure neutralization;
- forward-return construction;
- Pearson and Spearman information coefficients;
- IC decay across horizons;
- quantile portfolios;
- top-minus-bottom long-short returns;
- signal-to-weight normalization;
- portfolio turnover.

The functions operate within a timestamp unless documented otherwise. Forward returns are explicitly future-labelled and do not shift the signal automatically.

## Portfolio risk

`asr.risk` is for fixed-weight portfolio risk snapshots and scenario analysis.

```python
weights = pd.Series({"A": 0.40, "B": 0.35, "C": 0.25})
report = asr.risk.portfolio_risk_report(asset_returns, weights, level=0.95)

print(report.summary)
print(report.volatility_contributions)
print(report.expected_shortfall_contributions)
```

The module includes:

- portfolio returns;
- Euler volatility decomposition;
- historical VaR;
- Gaussian VaR;
- Cornish-Fisher VaR;
- historical Expected Shortfall;
- Gaussian Expected Shortfall;
- historical ES contributions;
- scenario P&L decomposition;
- rolling VaR.

VaR and ES use a **loss-positive convention**. Asset returns remain ordinary signed returns.

## Market microstructure

`asr.microstructure` provides transparent quote/trade diagnostics.

```python
mid = asr.microstructure.midquote(bid, ask)
micro = asr.microstructure.microprice(bid, ask, bid_size, ask_size)
spread = asr.microstructure.effective_spread(trade_price, mid, side)
ofi = asr.microstructure.order_flow_imbalance(bid, ask, bid_size, ask_size)
```

Available measures include:

- midpoint and quoted spread;
- top-of-book microprice;
- effective spread;
- realized spread;
- post-trade price impact;
- top-of-book order-flow imbalance;
- Amihud illiquidity;
- Roll implied spread;
- Kyle lambda.

These functions intentionally accept pandas objects rather than enforcing a proprietary tick-data schema.

## End-to-end example

```python
import asrquant as asr

# 1. Build a lagged cross-sectional score.
raw = prices.pct_change(20, fill_method=None).shift(1)
signal = asr.alpha.cross_sectional_zscore(raw)

# 2. Evaluate the signal on future returns.
fwd = asr.alpha.forward_returns(prices, 5)[5]
alpha_report = asr.alpha.analyze_signal(signal, fwd, quantiles=5)

# 3. Convert the latest score into a normalized portfolio.
weights = alpha_report.weights.dropna().iloc[-1]

# 4. Inspect volatility and tail risk.
risk_report = asr.risk.portfolio_risk_report(
    prices.pct_change(fill_method=None).tail(252),
    weights,
)

# 5. Inspect execution-quality inputs separately.
mid = asr.microstructure.midquote(bid, ask)
micro = asr.microstructure.microprice(bid, ask, bid_size, ask_size)
```

Research validity, execution validity, and live authorization remain separate ASRQuant concepts. These research diagnostics do not authorize capital deployment.
