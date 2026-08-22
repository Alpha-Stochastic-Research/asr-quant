# Backtesting

## Canonical API

```python
result = asr.backtesting.run(prices, target_weights)
print(result.summary)
```

The underlying engine returns `BacktestResult` and supports the existing `BacktestSpec` and `CostModel` objects.

## What belongs in a backtest specification

- information timing;
- target-weight timing;
- execution delay;
- transaction costs;
- missing-data policy;
- rebalancing rule;
- benchmark and performance conventions.

## Performance is not validation

A high in-sample metric is not sufficient. Compare specifications, test costs and delays, use chronological holdouts, and record which decisions were made before observing the evaluation period.
