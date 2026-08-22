# Scientific literature to quantitative decision

ASRQuant 1.0.0 adds a provenance-first research workflow that connects scientific papers, economic hypotheses, data, features, signals, portfolio construction, backtesting, robustness, governed decisions, and paper trading.

The workflow is designed to make assumptions reviewable. It does not claim that an automatically extracted sentence is economically correct, causal, or globally novel.

## 1. Ingest PDF papers

```python
import asrquant as asr

project = asr.research.from_pdfs(
    "papers/",
    topic="interest rates and equity style returns",
    name="Rates and equity styles",
)

print(project.corpus.paper_table())
```

Each paper retains:

- a stable paper identifier;
- path and file fingerprint;
- page-level text;
- title, authors, year and abstract when extractable;
- extraction warnings;
- source excerpts with exact page numbers.

Text-based PDFs are supported directly. Scanned PDFs must be OCRed before ingestion. ASRQuant never silently runs OCR because OCR errors can alter scientific claims.

## 2. Discover source-linked hypotheses

```python
registry = project.discover_hypotheses()
print(registry.to_frame())
```

Corpus-relative labels are:

- `established`: similar claims in at least three supplied papers;
- `replicated`: similar claims in two supplied papers;
- `underexplored`: one direct source in the supplied corpus;
- `contradictory`: similar claims with opposing directional language;
- `corpus-novel`: a gap or limitation with no direct match elsewhere in the supplied corpus.

`corpus-novel` never means that the hypothesis has never been tested anywhere. It means only that no direct match was found in the documents supplied to this run.

The independent `evidence_status` field records whether the cited passage appears to be `tested_in_corpus`, `not_directly_tested_in_corpus`, or `proposed_in_corpus`. It is a triage signal, not a substitute for reading and verifying the cited page.

A custom extractor can connect a local or remote language model while preserving the same citation contract:

```python
def extractor(paper):
    return [
        {
            "statement": "...",
            "page": 12,
            "source_text": "...",
            "confidence": 0.82,
        }
    ]

registry = project.discover_hypotheses(extractor=extractor)
```

## 3. Operationalize one hypothesis

```python
hypothesis = project.select_hypothesis(
    "H001",
    predictor="US10Y",
    target="VALUE minus GROWTH",
    expected_sign="positive",
    horizon=20,
    universe="US equity style ETFs",
    mechanism=(
        "Higher discount rates reduce the present value of long-duration "
        "growth cash flows more strongly."
    ),
    invalidation_criteria=[
        "The predictive coefficient has the opposite sign out of sample.",
        "The result disappears under realistic costs and a one-bar delay.",
    ],
)
```

An `EconomicHypothesis` stores the statement, mechanism, predictor, target, expected sign, horizon, universe, null, evidence, novelty status and falsification criteria.

## 4. Generate and review a data plan

```python
plan = project.plan_data()
print(plan.to_frame())
```

For recognized economic concepts, ASRQuant proposes provider mappings such as FRED and Yahoo Finance. Suggestions are not treated as proof that a proxy correctly measures the construct.

Download is explicit:

```python
data = project.fetch_data(
    start="2005-01-01",
    end="2026-07-31",
    provider_kwargs={
        "fred": {"api_key": "..."},
    },
)
```

For revised macroeconomic series, the user must verify point-in-time vintages and publication timestamps. Standard endpoints may expose revised observations.

Local data can be attached instead:

```python
project.attach_data(
    "research_panel.csv",
    date_column="Date",
    tradable_assets=["VALUE", "GROWTH"],
)
```

## 5. Build leakage-aware features

```python
feature_plan = asr.FeaturePlan([
    asr.FeatureSpec(
        name="yield_change_20",
        source="US10Y",
        transform="diff",
        params={"periods": 20},
        availability_lag=1,
    ),
    asr.FeatureSpec(
        name="yield_change_z252",
        source="US10Y",
        transform="zscore",
        window=252,
        availability_lag=1,
    ),
])

features = project.build_features(feature_plan)
```

Available transformations include raw values, differences, percentage changes, log returns, momentum, rolling means, rolling standard deviations, z-scores, exponential averages, ranks, lags, volatility, drawdowns, ratios, spreads and interactions.

`availability_lag` represents when a datum becomes known. `lag` adds a modelling delay after availability.

A transparent starting plan is available:

```python
feature_plan = project.recommend_features()
features = project.build_features(feature_plan)
```

## 6. Convert features into a signal

```python
signal = project.build_signal(
    asr.SignalSpec(
        feature="yield_change_z252",
        method="threshold_pair",
        long_asset="VALUE",
        short_asset="GROWTH",
        upper=1.0,
        lower=-1.0,
        signal_lag=1,
    )
)
```

Supported signal mappings include threshold pairs, continuous pairs, threshold long-only signals and sign signals.

The automatic starting proposal is reviewable:

```python
proposal = project.recommend_signal()
print(proposal)
```

## 7. Test the economic hypothesis

```python
test = project.test_hypothesis(
    feature="yield_change_z252",
    horizon=20,
    covariance="HAC",
)

print(test.summary)
```

For a two-asset pair, ASRQuant constructs the future long-minus-short return and regresses it on the time-t feature. The output reports coefficient, robust p-value, R-squared and whether the estimated sign agrees with the hypothesis.

This is a predictive econometric test, not proof of structural causality.

## 8. Construct the portfolio

```python
weights = project.construct_portfolio(
    asr.PortfolioSpec(
        gross_leverage=1.0,
        max_abs_weight=0.5,
        volatility_target=0.10,
        volatility_window=20,
        max_leverage=1.5,
    )
)
```

Portfolio construction applies long-only constraints when requested, position limits, gross leverage limits and optional ex-ante volatility targeting.

## 9. Run an auditable backtest

```python
result = project.backtest(
    costs_bps=5,
    execution_delay=1,
    rebalance="W-FRI",
)

print(result.metrics)
```

The ordinary ASRQuant backtest contract remains available, including spread, slippage, borrow costs, nonlinear impact, leverage, rebalance frequency and initial capital.

## 10. Run robustness checks

```python
robustness = project.robustness(
    execution_delays=(1, 2, 3),
    costs_bps=(0, 5, 10, 20),
    rebalances=("bar", "W-FRI", "ME"),
    n_subperiods=4,
    n_boot=2000,
)

print(robustness.summary)
```

The result contains:

- implementation audit across costs, delays and rebalancing conventions;
- chronological subperiod metrics;
- moving-block bootstrap confidence interval for Sharpe;
- look-ahead alignment diagnostics;
- positive-subperiod and positive-contract ratios;
- optional parameter-sweep results.

## 11. Obtain a governed decision

```python
decision = project.decide()
print(decision.summary)
```

Possible statuses are:

- `REJECT`;
- `RESEARCH-ONLY`;
- `COLLECT MORE DATA`;
- `REVISE HYPOTHESIS`;
- `PAPER-TRADING CANDIDATE`;
- `LIMITED-CAPITAL CANDIDATE`.

A backtest alone never produces an automatic unrestricted live-deployment authorization. The decision includes reasons, risks, score, evidence and the required next step.

## 12. Paper trade the strategy

```python
paper = project.paper_trade(
    initial_capital=100_000,
    commission_bps=1,
    slippage_bps=2,
    policy=asr.RiskPolicy(
        max_gross_leverage=1.0,
        max_position_weight=0.50,
        max_daily_turnover=1.0,
        max_drawdown=0.15,
        minimum_cash=0.0,
    ),
)

print(paper.summary)
print(paper.orders)
print(paper.fills)
print(paper.risk_events)
```

The paper broker supports market, limit, stop and stop-limit order primitives, order states, commissions, slippage, partial-fill modelling, position accounting, turnover controls, cash limits and a drawdown kill switch.

It does not connect to a live broker by default.

## 13. Preserve the entire research record

```python
project.save_manifest("research_manifest.json")
project.report("research_dossier.html")
```

The manifest records paper, hypothesis, data-plan, feature, signal, portfolio, backtest, robustness, decision and workflow history fingerprints.

## One-call quantitative stages

When the hypothesis and data are already available:

```python
import asrquant as asr

project = asr.autoresearch(
    hypothesis="Rising yields predict value outperformance relative to growth.",
    data="research_panel.csv",
    tradable_assets=["VALUE", "GROWTH"],
    feature_plan=asr.FeaturePlan([
        asr.FeatureSpec(
            "yield_change",
            "US10Y",
            "diff",
            params={"periods": 20},
            availability_lag=1,
        )
    ]),
    signal_spec=asr.SignalSpec(
        "yield_change",
        long_asset="VALUE",
        short_asset="GROWTH",
        upper=0.15,
        lower=-0.15,
    ),
)

print(project.decision_result.summary)
```

The short API does not remove the intermediate objects. Every generated plan remains available for inspection and modification.

## Evidence-status triage

Candidates record whether cited passages appear tested, explicitly untested, or proposed. Page-level verification remains mandatory.
