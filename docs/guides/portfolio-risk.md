# Portfolio & Risk

## Portfolio construction

```python
result = asr.portfolio.optimize(
    returns,
    method="minimum_variance",
)
print(result.weights)
print(result.summary)
```

Supported canonical optimization methods include minimum variance, maximum Sharpe, equal risk contribution, maximum diversification and hierarchical risk parity.

## Risk report

```python
risk = asr.risk.portfolio_risk_report(
    returns.tail(252),
    result.weights,
    level=0.95,
)
print(risk.summary)
```

The risk namespace also exposes historical/Gaussian/Cornish-Fisher VaR, Expected Shortfall, rolling VaR, covariance risk contributions, ES contributions and scenario P&L.

## Research rule

Do not report only aggregate volatility or Sharpe. Inspect concentration, exposures and risk contribution so that portfolio behaviour is attributable rather than opaque.
