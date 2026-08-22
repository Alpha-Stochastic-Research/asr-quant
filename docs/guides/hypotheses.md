# Hypothesis Discovery

ASRQuant 1.2.0 adds a dedicated `asr.hypotheses` layer for generating and reviewing research candidates.

## Sources

Candidates can be derived from:

- structured data;
- literature;
- model disagreement;
- robustness instability;
- combinations of those sources.

## Data-driven example

```python
ideas = asr.hypotheses.discover(
    data=research_panel,
    targets="value_minus_growth",
    horizons=(1,),
    lags=(0,),
    transforms={
        "rate_change": "raw",
        "value_minus_growth": "raw",
    },
    min_observations=120,
)

ideas.to_frame().head()
```

## Literature + data

```python
papers = [
    (
        "Rates and styles",
        "Future research should test whether changes in interest rates are associated "
        "with subsequent differences between value and growth returns.",
    )
]

ideas = asr.hypotheses.discover(
    data=research_panel,
    papers=papers,
    domain="quantitative_finance",
    targets="value_minus_growth",
    horizons=(1,),
    lags=(0,),
    min_observations=120,
)
```

## Important boundary

Statistical support and novelty status are separate. A hypothesis can be statistically interesting without being new, and a novel idea can fail empirical validation.
