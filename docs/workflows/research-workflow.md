# End-to-End Research Workflow

ASRQuant 1.2.0 is designed to connect research stages without forcing every project into one monolithic object.

## 1. Define the question

Start with a falsifiable statement, a target, an information set and a horizon. Use `asr.hypotheses` when the question is being generated from data, literature, model disagreement or robustness instability.

## 2. Acquire and validate data

```python
panel = asr.data.load("research_panel.csv", date_column="Date")
quality = asr.data.validate(panel)
```

Document data source, timing convention, revisions and transformations before testing the hypothesis.

## 3. Discover or register hypotheses

```python
ideas = asr.hypotheses.discover(
    data=panel,
    targets="target_return",
    horizons=(1, 5),
    lags=(0, 1),
    min_observations=120,
)
```

Candidate ranking is a screening mechanism, not proof of economic significance or scientific novelty.

## 4. Build signal diagnostics

For cross-sectional research, use `asr.alpha` for rank/z-score transforms, forward returns, information coefficients, quantile portfolios, long-short spreads and turnover.

## 5. Separate factor and risk explanations

Use `asr.factors` to estimate exposures and decompose factor/specific risk. Use `asr.risk` for VaR, Expected Shortfall, risk contributions and scenarios.

## 6. Construct the portfolio

```python
construction = asr.portfolio.optimize(
    returns,
    method="hierarchical_risk_parity",
)
```

Portfolio construction is distinct from signal generation. Record the mapping from signal to weights and every constraint.

## 7. Backtest with chronology and costs

```python
backtest = asr.backtesting.run(prices, target_weights)
```

The backtest should encode the information set, rebalance timing, execution delay and costs rather than infer them after the fact.

## 8. Run robustness checks

Change windows, costs, portfolio construction, data vintages and reasonable modelling assumptions. Do not interpret a single parameter setting as a research conclusion.

## 9. Produce a reviewable decision

A research output should preserve enough information for another reviewer to answer:

- What was known at each time?
- Which transformation created each feature?
- Which hypotheses were screened?
- Which model and parameters were used?
- How were weights constructed?
- Which costs and delays were assumed?
- Which robustness checks passed or failed?
