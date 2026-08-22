# Alpha & Factor Research

## Cross-sectional alpha

The `asr.alpha` namespace includes cross-sectional ranking, z-scores, winsorization, neutralization, forward-return construction, information coefficients, IC decay, quantile portfolios, long-short spreads, signal weights and turnover diagnostics.

```python
raw_signal = prices.pct_change(20, fill_method=None).shift(1)
signal = asr.alpha.cross_sectional_zscore(raw_signal)
forward_5d = asr.alpha.forward_returns(prices, 5)[5]
report = asr.alpha.analyze_signal(signal, forward_5d, quantiles=5, min_assets=15)

print(report.summary)
```

The explicit `.shift(1)` is part of the research specification: it prevents the score from using the current day's return when the score is assumed to be known before that return.

## Factor research

The `asr.factors` namespace supports:

- PCA factor extraction;
- factor exposures;
- rolling beta;
- factor/specific risk decomposition.

Use factor diagnostics to distinguish a signal from a disguised exposure to common systematic drivers.
