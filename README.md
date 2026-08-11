# ASRQuant

**From scientific literature and economic hypotheses to auditable quantitative decisions, guarded broker execution, and production-readiness controls in Python.**

ASRQuant is an open-source research package developed by **Alpha Stochastic Research**. It provides a compact, explicit and reproducible interface for scientific-paper ingestion, source-linked hypothesis discovery, market-data planning, feature and signal construction, quantitative visualization, stochastic simulation, derivative pricing, econometrics, machine learning, portfolio analytics, parameter exploration, backtesting, robustness, governed decisions and paper trading, production readiness, tamper-evident audit trails and explicitly authorized broker execution.

The central objective is simple: workflows that normally require many notebooks, formulas and plotting scripts should be expressible in a few readable lines without hiding the assumptions that materially affect the result.

> **Release status: 1.1.0 (stable public API).** The 1.0.0 paper-contract remains preserved; 1.1.0 adds the Research Discovery / Weekly Research operating layer and the comprehensive interest-rate research stack. The paper workflows are enforced by a dedicated paper-contract test group. Guarded live-broker primitives remain fail-closed and require deployment-specific authorization; installing the stable software does not authorize capital deployment. ASRQuant is research software, not financial advice or an HFT exchange gateway.

## Contents

- [Installation](#installation)
- [One-import user contract](#one-import-user-contract)
- [Five-line workflow](#five-line-workflow)
- [Core concepts](#core-concepts)
- [Scientific literature to decision](#scientific-literature-to-decision)
- [Research discovery and Weekly Research](#research-discovery-and-weekly-research)
- [Algorithmic trading and paper execution](#algorithmic-trading-and-paper-execution)
- [Production readiness and live capital](#production-readiness-and-live-capital)
- [Durable audit, reconciliation and emergency controls](#durable-audit-reconciliation-and-emergency-controls)
- [Data ingestion and preparation](#data-ingestion-and-preparation)
- [The `QuantLab` interface](#the-quantlab-interface)
- [Strategies](#strategies)
- [Backtesting](#backtesting)
- [Performance and risk metrics](#performance-and-risk-metrics)
- [Implementation audits](#implementation-audits)
- [Parameter sweeps, surfaces and animations](#parameter-sweeps-surfaces-and-animations)
- [Stochastic simulation and Monte Carlo](#stochastic-simulation-and-monte-carlo)
- [Derivative pricing](#derivative-pricing)
- [Martingale diagnostics](#martingale-diagnostics)
- [Regression and econometrics](#regression-and-econometrics)
- [Machine learning](#machine-learning)
- [Portfolio optimization](#portfolio-optimization)
- [Volatility models](#volatility-models)
- [Fixed income](#fixed-income)
- [Validation and stress testing](#validation-and-stress-testing)
- [Visualization system](#visualization-system)
- [Reports and provenance](#reports-and-provenance)
- [Command-line interface](#command-line-interface)
- [Complete end-to-end examples](#complete-end-to-end-examples)
- [API map](#api-map)
- [Reproducibility rules](#reproducibility-rules)
- [Current limitations](#current-limitations)
- [Development and testing](#development-and-testing)
- [Citation and license](#citation-and-license)

---

## Installation

ASRQuant requires **Python 3.10 or later**.

### Install the provided wheel

```bash
pip install asrquant-1.1.0-py3-none-any.whl
```

### Install from the source directory

```bash
pip install .
```

### Editable development installation

```bash
pip install -e ".[dev]"
python scripts/test_all.py
```

### Optional dependency groups

The base installation automatically installs the validated numerical and visualization engines required by ASRQuant. They remain internal implementation details: normal user workflows do not require importing NumPy, pandas, SciPy, Matplotlib, Plotly, statsmodels or scikit-learn directly.

```bash
# Yahoo Finance, Excel, Parquet and Feather support
pip install ".[data]"

# GARCH models
pip install ".[volatility]"

# CVXPY-backed optimization methods when required
pip install ".[optimization]"

# SHAP and hidden Markov model extensions
pip install ".[ml]"

# All optional research dependencies
pip install ".[all]"

# Documentation toolchain
pip install ".[docs]"
```

When the project is officially registered on PyPI, the intended commands are:

```bash
pip install asrquant
pip install "asrquant[all]"
```

Until registration is completed, install the supplied wheel or source archive.

### Verify the installation

```python
import asrquant

print(asrquant.__version__)
# 1.1.0
```

```bash
asrquant --version
```

---

## Five-line workflow

```python
import asrquant as asr

lab = asr.open_lab(prices)
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
asr.save(result, "dashboard.png", kind="dashboard")
asr.report(result, "report.html")
```

The returned `BacktestResult` contains:

- validated prices and asset returns;
- target and effective weights;
- gross and net strategy returns;
- equity curve;
- turnover;
- aggregate and decomposed costs;
- strategy metrics;
- a transaction ledger;
- the immutable backtest specification;
- data, specification and experiment fingerprints;
- plotting and HTML-report helpers.

---

## One-import user contract

The recommended public interface is a single import:

```python
import asrquant as asr
```

After that import, the standard workflow is available through ASRQuant itself:

```python
lab = asr.open_lab("prices.csv", date_column="Date")
model = asr.models.random_forest(task="regression", trees=500, depth=6, seed=7)
ml = lab.ml(model, train_size=504, test_size=63, gap=5)
backtest = lab.backtest("momentum", lookback=126, costs_bps=5)
asr.save(backtest, "equity.png", kind="equity")
```

The following namespaces deliberately hide the backend libraries:

- `asr.models`: linear models, trees, forests, boosting, SVM, KNN, clustering, PCA and anomaly detection;
- `asr.math`: arrays, grids, elementary functions, normal distribution functions and random generators;
- `asr.visualize`, `asr.show`, `asr.save`: backend-neutral visualization;
- `asr.stats`: regression, econometrics, bootstrap and statistical tests;
- `asr.portfolio`: allocation, covariance and optimization;
- `asr.options`: derivative pricing and Greeks;
- `asr.stochastic`: stochastic processes and Monte Carlo;
- `asr.rates`: fixed-income analytics;
- `asr.vol`: volatility estimators and forecasts;
- `asr.visuals`: the complete visualization catalog.

Matplotlib, Plotly, scikit-learn and statsmodels are used internally because they are mature scientific engines. ASRQuant owns the user-facing API, parameter validation, output objects, visualization calls and reproducibility contract. Advanced users may access a raw backend object through `PlotHandle.raw`, but ordinary workflows never need to do so.

---

## Production readiness and live capital

ASRQuant deliberately separates three different claims:

1. **research-valid**: the strategy and backtest pass scientific review;
2. **broker-paper validated**: the deployed execution path has survived a defined observation period in the broker simulator;
3. **live-authorized**: a signed deployment certificate matches the exact release, broker account, risk policy, environment and maximum capital.

A wheel cannot certify the second and third claims by itself. The deployment gate therefore fails closed by default.

### 1. Create an evidence file

```python
import asrquant as asr

evidence = asr.DeploymentEvidence(
    release_version=asr.__version__,
    ci_passed=True,
    test_count=120,
    coverage_percent=92.0,
    static_analysis_passed=True,
    dependency_scan_passed=True,
    secrets_scan_passed=True,
    sbom_present=True,
    artifacts_signed=True,
    reproducible_build_verified=True,
    disaster_recovery_tested=True,
    rollback_tested=True,
    monitoring_enabled=True,
    alerting_enabled=True,
    durable_audit_log_enabled=True,
    time_synchronization_verified=True,
    broker_paper_days=45,
    broker_paper_orders=1000,
    reconciliation_mismatches=0,
    unresolved_critical_incidents=0,
    operator_approved=True,
    legal_compliance_reviewed=True,
    data_licenses_reviewed=True,
    strategy_owner_approved=True,
    model_validation_approved=True,
    change_ticket="CHG-2026-001",
)

report = asr.ProductionReadinessGate().evaluate(evidence)
print(report.ready)
report.save("readiness-report.json")
```

The same check is available from the CLI:

```bash
asrquant readiness deployment-evidence.json --output readiness-report.json
```

The command exits with status `2` when any required gate fails.

### 2. Define the exact live risk policy

```python
policy = asr.LiveRiskPolicy(
    max_gross_leverage=1.0,
    max_position_weight=0.10,
    max_order_notional=5_000,
    max_daily_turnover=0.25,
    max_drawdown=0.10,
    max_daily_loss=0.02,
    max_open_orders=5,
    max_orders_per_minute=10,
    max_price_deviation_bps=100,
    max_market_data_age_seconds=2,
    max_capital=50_000,
    max_position_notional=10_000,
    allow_short=False,
    require_market_open=True,
    symbol_allowlist=("SPY", "QQQ"),
)
```

### 3. Issue a signed, expiring deployment certificate

The signing key must come from a secret manager or protected deployment environment. Never place it in source code, notebooks, reports or CI logs.

```python
certificate = asr.DeploymentCertificate.issue(
    report=report,
    evidence=evidence,
    secret_key=certificate_signing_key,
    release_version=asr.__version__,
    broker="alpaca",
    account_id=broker_account_id,
    account_salt=account_specific_salt,
    risk_policy=policy,
    max_live_capital=50_000,
    approved_by=("risk-owner", "operations-owner"),
    validity_hours=24,
)

certificate.save("deployment-certificate.json")
```

The certificate becomes invalid if any of the following changes:

- package version;
- broker;
- broker account;
- risk policy;
- maximum authorized capital;
- environment fingerprint when enforced;
- validity period;
- signed payload.

### 4. Test the real broker adapter in paper mode

```python
credentials = asr.BrokerCredentials.from_environment()
broker = asr.AlpacaBroker.paper(credentials=credentials)
print(broker.health())
```

Paper and live Alpaca environments use different base URLs and should use different credentials. Paper execution remains a simulator and may differ from real fills.

### 5. Arm live mode explicitly

Live creation requires both a valid deployment certificate and an environment-level arm:

```bash
export ASRQUANT_LIVE_TRADING=ENABLED
```

```python
broker = asr.AlpacaBroker.live(
    certificate=certificate,
    certificate_secret=certificate_signing_key,
    account_id=broker_account_id,
    account_salt=account_specific_salt,
    risk_policy=policy,
    requested_capital=25_000,
    credentials=asr.BrokerCredentials.from_environment(),
)
```

Direct construction of a live adapter is rejected. The certificate is not a substitute for broker permissions, venue rules, regulatory review or an accountable human go-live decision.

## Durable audit, reconciliation and emergency controls

```python
store = asr.SQLiteAuditStore("state/execution-audit.db")
kill_switch = asr.PersistentKillSwitch("state/KILL_SWITCH.json")

engine = asr.LiveTradingEngine(
    broker=broker,
    policy=policy,
    audit_store=store,
    kill_switch=kill_switch,
)

receipt = engine.submit(
    asr.Order("SPY", 10, asr.OrderSide.BUY),
    asr.MarketDataSnapshot(
        symbol="SPY",
        price=last_price,
        timestamp=market_timestamp,
        bid=bid,
        ask=ask,
        source="primary-feed",
    ),
)
```

Before submission, the engine checks at least:

- live kill-switch state;
- duplicate client-order IDs;
- broker and account health;
- market-open state;
- market-data freshness;
- symbol allowlist and denylist;
- order size and notional;
- price collars;
- buying power;
- daily loss;
- open-order count;
- order-entry rate;
- projected position weight;
- projected gross leverage;
- short-selling policy.

Every risk decision, order intent, broker receipt, failure, reconciliation and emergency stop is appended to a SQLite write-ahead log with a SHA-256 hash chain.

```python
valid, broken_sequence = store.verify_chain()
backup = store.backup("backups/execution-audit.db")
```

```bash
asrquant verify-audit state/execution-audit.db
```

Reconciliation is explicit:

```python
report = engine.reconcile(
    expected_positions={"SPY": 10.0},
    expected_cash=24_000.0,
)
```

A mismatch outside tolerance activates the persistent kill switch and attempts to cancel open orders. Manual emergency stop is also available:

```python
engine.emergency_stop("unexpected market-data divergence", operator="risk-owner")
```

Clearing the kill switch requires an explicit operator action and authorization string:

```python
kill_switch.clear(
    operator="operations-owner",
    authorization="CLEAR_KILL_SWITCH",
)
```

See `docs/production_readiness.md`, `docs/live_trading.md`, `docs/operations_runbook.md`, `docs/regulatory_controls.md` and `THREAT_MODEL.md` before enabling a broker connection.

---

## Core concepts

### 1. Explicit data

ASRQuant accepts ASR-created frames and compatible time-indexed tabular objects. It does not silently infer an arbitrary date order or broadcast one asset across a multi-asset panel.

### 2. Explicit execution contract

A backtest is defined by a `BacktestSpec`, including execution delay, rebalance frequency, leverage limits, missing-data policy, annualization, cash rate and all modeled costs.

### 3. Explicit chronology

Signals, features and validation folds are designed to preserve temporal ordering. Same-bar execution is possible for diagnostics, but it is not the default.

### 4. Scalar experiment interface

Any Python experiment that returns, or can be reduced to, a scalar value can be evaluated over a finite parameter grid and represented as a surface, heatmap, contour or animation.

### 5. Auditable outputs

Important results expose summary tables, underlying data, parameters and deterministic fingerprints rather than only displaying a chart.

---

## Research discovery and Weekly Research

ASRQuant can now start before a formal hypothesis exists. The discovery engine converts transparent market, curve, literature, model-disagreement and robustness evidence into ranked **research candidates**. Automated candidates never receive an automatic novelty claim.

```python
import asrquant as asr

board = asr.discovery.weekly(data=curve_history, domain="fixed_income", n=10)
print(board.to_frame())

project = board.start(0)
cycle = asr.weekly_cycle(board, 0, launch_friday="2026-08-14")
cycle.publication_pack("WR-001")
```

The resulting cycle follows ASR's Friday-to-Friday contract: launch, prior-art review, data design, baseline, main experiment, robustness, independent review, then publication on the next Friday. See `docs/research_discovery.md` and `docs/team_research_operating_model.md`.

---

## Scientific literature to decision

ASRQuant 1.0.0 connects paper provenance, economic hypotheses, data, features, signals, econometric testing, portfolio construction, backtesting, robustness, decisions and paper trading in one stateful `ResearchProject`. The automatic stages remain reviewable and do not hide their assumptions.

### 1. Ingest PDF papers

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

### 2. Discover source-linked hypotheses

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

Each candidate also receives an independent evidence status:

- `tested_in_corpus`: the source passage explicitly reports a test, estimate, result or finding;
- `not_directly_tested_in_corpus`: the candidate comes from an explicit gap or future-research passage;
- `proposed_in_corpus`: the passage formulates or predicts a relationship without a directly detected empirical test.

These labels are evidence-triage aids. Researchers must verify the quoted page passages before treating a candidate as tested or untested.

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

### 3. Operationalize one hypothesis

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

### 4. Generate and review a data plan

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

### 5. Build leakage-aware features

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

### 6. Convert features into a signal

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

### 7. Test the economic hypothesis

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

### 8. Construct the portfolio

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

### 9. Run an auditable backtest

```python
result = project.backtest(
    costs_bps=5,
    execution_delay=1,
    rebalance="W-FRI",
)

print(result.metrics)
```

The ordinary ASRQuant backtest contract remains available, including spread, slippage, borrow costs, nonlinear impact, leverage, rebalance frequency and initial capital.

### 10. Run robustness checks

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

### 11. Obtain a governed decision

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

### 12. Paper trade the strategy

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

### 13. Preserve the entire research record

```python
project.save_manifest("research_manifest.json")
project.report("research_dossier.html")
```

The manifest records paper, hypothesis, data-plan, feature, signal, portfolio, backtest, robustness, decision and workflow history fingerprints.

### One-call quantitative stages

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


See [`docs/research_workflow.md`](docs/research_workflow.md) for the standalone guide.

---

## Algorithmic trading and paper execution

The built-in execution layer is safe by default: it simulates order creation, acceptance, fills, commissions, slippage, positions, cash and risk events without connecting to a live broker.

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")
weights = lab.strategy("sma", fast=20, slow=100)

paper = lab.paper_trade(
    weights,
    initial_capital=100_000,
    commission_bps=1,
    slippage_bps=2,
    policy=asr.RiskPolicy(
        max_gross_leverage=1.0,
        max_position_weight=0.20,
        max_daily_turnover=0.50,
        max_drawdown=0.15,
        minimum_cash=0.0,
    ),
)

print(paper.summary)
print(paper.orders)
print(paper.fills)
print(paper.risk_events)
```

The public primitives are `Order`, `Fill`, `OrderSide`, `OrderType`, `OrderStatus`, `RiskPolicy`, `PaperBroker`, `PaperTrader`, `PaperTradingResult`, `paper_trade` and the `BrokerAdapter` protocol.

Order types are market, limit, stop and stop-limit. The paper broker supports immediate or partial fills, commissions and slippage. The trader enforces maximum leverage, position size, order notional, daily turnover, short-selling permission, minimum cash and a maximum-drawdown kill switch.

A live or external paper broker can implement the following explicit adapter contract:

```python
class MyBroker:
    def submit_order(self, order, market_price): ...
    def cancel_order(self, order_id): ...
    def positions(self): ...
    def cash_balance(self): ...
```

ASRQuant does not include credentials, exchange authentication or unrestricted live-order submission. See [`docs/algorithmic_trading.md`](docs/algorithmic_trading.md).

---

## Data ingestion and preparation

### Required price-panel format

The standard input is created with `asr.series(...)`, `asr.frame(...)`, a file loader, a provider, or any compatible time-indexed table with:

- a unique `DatetimeIndex` or an index convertible to dates;
- one column per asset or numerical series;
- strictly positive values for price data;
- no infinite values;
- at least two observations.

```python
import asrquant as asr

prices = asr.frame(
    {
        "SPY": [100.0, 101.2, 100.8, 102.5],
        "QQQ": [100.0, 102.1, 101.6, 103.9],
    },
    index=asr.date_range("2026-01-01", periods=4, freq="D"),
)

lab = asr.open_lab(prices)
```

### Missing-data policies

```python
lab = QuantLab(prices, missing_data="raise")  # reject missing observations
lab = QuantLab(prices, missing_data="drop")   # remove rows containing missing values
lab = QuantLab(prices, missing_data="ffill")  # forward-fill, then drop unresolved rows
```

Forward filling is an explicit user choice because it may be inappropriate for some instruments or research questions.

### CSV

```python
from asrquant import QuantLab

lab = QuantLab.from_csv(
    "prices.csv",
    date_column="Date",
    columns=["SPY", "QQQ", "TLT"],
    missing_data="drop",
)
```

Expected CSV structure:

```text
Date,SPY,QQQ,TLT
2024-01-02,472.65,402.12,98.41
2024-01-03,470.26,399.77,99.02
```

If `date_column` is omitted, the first column is used.

### Other local file formats

`QuantLab.from_file(...)` supports:

- CSV and text files;
- Parquet;
- Excel;
- JSON;
- Feather.

```python
lab = QuantLab.from_file("prices.parquet", date_column="timestamp")
lab = QuantLab.from_file("prices.xlsx", date_column="Date", sheet_name="Close")
lab = QuantLab.from_file("prices.json", date_column="date")
lab = QuantLab.from_file("prices.feather", date_column="timestamp")
```

Excel, Parquet and Feather may require the `data` optional dependencies.

### Lower-level file loader

```python
from asrquant import load_prices

prices = load_prices(
    "prices.csv",
    date_column="Date",
    columns=["SPY", "QQQ"],
)
```

### SQL

```python
import sqlite3
from asrquant import load_sql, QuantLab

connection = sqlite3.connect("market_data.db")
prices = load_sql(
    "SELECT timestamp, SPY, QQQ FROM daily_prices ORDER BY timestamp",
    connection,
    date_column="timestamp",
    columns=["SPY", "QQQ"],
)

lab = QuantLab(prices)
```

### Returns

```python
from asrquant import simple_returns, log_returns

simple = simple_returns(prices)
logs = log_returns(prices)
```

No implicit forward fill is used during return calculation.

### Data-quality report

```python
print(lab.quality)
```

or:

```python
from asrquant import data_quality_report

quality = data_quality_report(prices)
```

The report includes row count, column count, date range, missingness, duplicate timestamps, index monotonicity, median spacing, maximum gap and constant columns.

### Data fingerprint

```python
from asrquant import data_fingerprint

fingerprint = data_fingerprint(prices)
print(fingerprint)
```

The SHA-256 fingerprint incorporates values, timestamps and columns.

### OHLCV validation and resampling

Canonical OHLCV columns are `Open`, `High`, `Low`, `Close` and optionally `Volume`.

```python
from asrquant.data import validate_ohlcv, resample_ohlcv

clean_ohlcv = validate_ohlcv(ohlcv)
weekly = resample_ohlcv(clean_ohlcv, "W-FRI")
```

Resampling uses finance-consistent rules:

- Open: first;
- High: maximum;
- Low: minimum;
- Close: last;
- Volume: sum.

### Remote providers

Available providers:

| Provider | Name | Credentials | Typical use |
|---|---|---:|---|
| Yahoo Finance | `yahoo` or `yfinance` | No | Equities, ETFs, indices and other supported instruments |
| Binance Spot | `binance` | No | Public cryptocurrency OHLCV |
| Alpha Vantage | `alpha_vantage` | API key | Equities and supported Alpha Vantage series |
| FRED | `fred` | API key | Macroeconomic and interest-rate series |

#### Yahoo Finance

```python
lab = QuantLab.from_provider(
    "yahoo",
    ["SPY", "QQQ", "TLT"],
    start="2020-01-01",
    end="2026-01-01",
    interval="1d",
    field="Close",
)
```

Requires:

```bash
pip install ".[data]"
```

#### Binance

```python
lab = QuantLab.from_provider(
    "binance",
    "BTCUSDT",
    interval="1h",
    limit=1000,
    field="Close",
)
```

#### Alpha Vantage

```bash
export ALPHAVANTAGE_API_KEY="your-key"
```

```python
lab = QuantLab.from_provider(
    "alpha_vantage",
    "IBM",
    interval="daily",
    adjusted=True,
    outputsize="full",
    field="Adjusted Close",
)
```

The key can also be passed explicitly:

```python
lab = QuantLab.from_provider(
    "alpha_vantage",
    "IBM",
    provider_kwargs={"api_key": "your-key"},
    interval="daily",
)
```

#### FRED

```bash
export FRED_API_KEY="your-key"
```

```python
lab = QuantLab.from_provider(
    "fred",
    ["DGS10", "DGS2"],
    observation_start="2015-01-01",
    observation_end="2026-01-01",
    field="Value",
)
```

#### Provider-neutral download function

```python
from asrquant import download

prices = download(
    "yahoo",
    ["SPY", "QQQ"],
    start="2020-01-01",
    field="Close",
)
```

### Near-real-time polling

`PollingFeed` repeatedly calls a provider's quote method. It is appropriate for research dashboards and data collection, not order execution.

```python
from asrquant import BinanceProvider, PollingFeed

provider = BinanceProvider()
feed = PollingFeed(provider, "BTCUSDT", interval_seconds=60)

for quote in feed.stream(max_updates=5, interval="1m", limit=1):
    print(quote.name, quote["Close"], quote.attrs["received_at"])
```

A user application is responsible for persistence, retry policies, rate-limit management and interruption handling.

---

## The `QuantLab` interface

`QuantLab` is the unified high-level entry point.

```python
from asrquant import QuantLab

lab = QuantLab(prices)
```

Important attributes:

```python
lab.prices          # validated price DataFrame
lab.returns         # simple returns
lab.assets          # asset names
lab.quality         # data-quality report
lab.source_metadata # origin and loading metadata
lab.last_weights    # most recently generated weights
lab.last_result     # most recent BacktestResult
```

Main methods:

```text
QuantLab.from_file(...)
QuantLab.from_csv(...)
QuantLab.from_provider(...)
QuantLab.strategy(...)
QuantLab.backtest(...)
QuantLab.audit(...)
QuantLab.sweep(...)
QuantLab.surface(...)
QuantLab.animate_surface(...)
QuantLab.parameter_surface(...)
QuantLab.explore(...)
QuantLab.surface_from_frame(...)
QuantLab.backtest_parameter_surface(...)
QuantLab.monte_carlo(...)
QuantLab.option(...)
QuantLab.martingale_test(...)
QuantLab.regress(...)
QuantLab.ml_features(...)
QuantLab.ml_walk_forward(...)
QuantLab.plot(...)
```

### Quick data plots

```python
lab.plot("prices")
lab.plot("prices", normalize=True)
lab.plot("prices", log_scale=True)
lab.plot("returns")
lab.plot("cumulative_returns")
```

After a backtest, `lab.plot(...)` forwards unknown plot kinds to the latest `BacktestResult`.

---

## Strategies

### Built-in strategy names

| Strategy | Accepted names | Main parameters |
|---|---|---|
| Equal-weight buy and hold | `buy_hold`, `buy-and-hold` | `gross=1.0` |
| Moving-average crossover | `sma`, `sma_crossover` | `fast=20`, `slow=100`, `long_short=False`, `gross=1.0` |
| Cross-sectional momentum | `momentum` | `lookback=126`, `top_fraction=0.2`, `long_short=True`, `gross=1.0` |
| Rolling z-score mean reversion | `mean_reversion` | `lookback=20`, `z_entry=1.0`, `long_short=True`, `gross=1.0` |
| Volatility targeting | `vol_target`, `volatility_target` | `target_vol=0.1`, `lookback=20`, `annualization=252`, `max_leverage=2.0` |
| Donchian breakout | `breakout` | `lookback=55`, `exit_lookback=20`, `gross=1.0` |
| Bollinger mean reversion | `bollinger`, `bollinger_mean_reversion` | `window=20`, `entry_z=2.0`, `exit_z=0.5`, `gross=1.0` |
| RSI strategy | `rsi` | `window=14`, `oversold=30`, `overbought=70`, `gross=1.0` |
| Two-asset pairs strategy | `pairs`, `pairs_zscore` | `asset_a`, `asset_b`, `lookback=60`, `entry_z=2.0`, `gross=1.0` |

### Generate weights without backtesting

```python
weights = lab.strategy("sma", fast=20, slow=100)
```

```python
weights = lab.strategy(
    "momentum",
    lookback=126,
    top_fraction=0.25,
    long_short=True,
    gross=1.0,
)
```

### Custom strategy

A custom strategy receives the validated price panel and must return target weights with matching timestamps and asset columns.

```python
def custom_trend(prices, window: int = 50):
    trend = prices / prices.rolling(window).mean() - 1.0
    raw = trend.rank(axis=1, pct=True) - 0.5
    gross = raw.abs().sum(axis=1).replace(0.0, float("nan"))
    return raw.div(gross, axis=0).fillna(0.0)


result = lab.backtest(custom_trend, window=50, costs_bps=5)
```

### Direct weight input

```python
weights = asr.frame(
    {"SPY": 0.6, "QQQ": 0.4},
    index=lab.prices.index,
)

result = lab.backtest(weights)
```

A single-column weight series is not silently broadcast across multiple assets.

---

## Backtesting

### Minimal backtest

```python
result = lab.backtest(
    "sma",
    fast=20,
    slow=100,
    costs_bps=5,
    execution_delay=1,
)
```

`costs_bps` is a convenience argument that sets commission basis points while preserving the other components of the active `CostModel`. For a complete cost model, use `BacktestSpec`.

### Complete backtest contract

```python
from asrquant import BacktestSpec, CostModel, MissingDataPolicy

spec = BacktestSpec(
    name="Cross-sectional momentum research",
    initial_capital=250_000,
    annualization=252,
    execution_delay=1,
    rebalance="ME",
    long_only=False,
    max_gross_leverage=1.5,
    max_abs_weight=0.25,
    risk_free_rate=0.02,
    missing_data=MissingDataPolicy.DROP,
    costs=CostModel(
        commission_bps=2.0,
        spread_bps=3.0,
        slippage_bps=2.0,
        borrow_bps_annual=75.0,
        impact_coefficient=0.0001,
        impact_exponent=1.5,
    ),
    metadata={"research_cycle": "C01", "author": "ASR"},
)

result = lab.backtest(
    "momentum",
    lookback=126,
    top_fraction=0.2,
    spec=spec,
)
```

### Execution delay

`execution_delay=1` means a target weight formed at timestamp `t` is first applied to the return ending at `t+1`.

```python
spec = BacktestSpec(execution_delay=1)
```

`execution_delay=0` is allowed for diagnostics but can create same-bar leakage depending on how the signal was constructed.

### Rebalance frequency

Common values:

```text
bar      every observation
D        daily
W-FRI    weekly on Friday
ME       month end
QE       quarter end
```

Any valid pandas resampling rule compatible with the engine may be supplied.

### Cost model

Linear trading cost per period is based on turnover and:

```text
commission_bps + spread_bps + slippage_bps
```

Nonlinear impact is:

```text
impact_coefficient * turnover ** impact_exponent
```

Short borrow cost is applied to short exposure using `borrow_bps_annual` and the specified annualization factor.

### Backtest result fields

```python
result.prices
result.asset_returns
result.target_weights
result.effective_weights
result.gross_returns
result.net_returns
result.equity
result.turnover
result.costs
result.cost_breakdown
result.spec
result.metadata
```

### Metrics

```python
print(result.metrics)
```

### Transaction ledger

```python
trades = result.trades
print(trades.head())
```

The ledger contains timestamp, asset, weight change, direction, execution-reference price and resulting target weight.

### Export time series

```python
frame = result.to_frame()
frame.to_csv("backtest_timeseries.csv")
```

### Compare with a benchmark

```python
benchmark = lab.returns["SPY"]
comparison = result.compare(benchmark)
print(comparison)
```

### Compare several backtests

```python
from asrquant import compare_backtests

results = {
    "SMA": lab.backtest("sma", fast=20, slow=100),
    "Momentum": lab.backtest("momentum", lookback=126),
    "Vol target": lab.backtest("vol_target", target_vol=0.10),
}

comparison = compare_backtests(results)
print(comparison)
```

### Plot backtest results

```python
result.plot()                         # dashboard
result.plot("equity")
result.plot("drawdown")
result.plot("equity_drawdown")
result.plot("rolling_metrics", window=63)
result.plot("monthly_heatmap")
result.plot("annual_returns")
result.plot("turnover")
result.plot("costs")
result.plot("weights")
result.plot("exposures")
result.plot("return_contributions")
result.plot("trade_pnl")
result.plot("benchmark", benchmark_returns=benchmark)
```

### HTML report

```python
path = result.report(
    "reports/sma_report.html",
    title="SMA strategy research report",
)
print(path)
```

---

## Performance and risk metrics

```python
from asrquant import summary_metrics

metrics = summary_metrics(
    result.net_returns,
    annualization=252,
    risk_free_rate=0.02,
    benchmark=benchmark,
    turnover=result.turnover,
)
```

Lower-level functions are available in `asrquant.metrics`:

```python
from asrquant.metrics import (
    cumulative_returns,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    omega_ratio,
    max_drawdown,
    drawdown_series,
    drawdown_duration,
    value_at_risk,
    parametric_var,
    expected_shortfall,
    conditional_drawdown_at_risk,
    hit_rate,
    profit_factor,
    alpha_beta,
    information_ratio,
    capture_ratio,
    m_squared,
    kelly_fraction,
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
)
```

Examples:

```python
from asrquant.metrics import value_at_risk, expected_shortfall

var_95 = value_at_risk(result.net_returns, level=0.95)
es_95 = expected_shortfall(result.net_returns, level=0.95)
```

```python
from asrquant.metrics import parametric_var

gaussian_var = parametric_var(result.net_returns, method="gaussian")
cornish_fisher_var = parametric_var(result.net_returns, method="cornish_fisher")
```

Probabilistic and deflated Sharpe outputs are diagnostics, not guarantees that a strategy will remain profitable.

---

## Implementation audits

The same logical strategy can produce materially different results under different defensible execution conventions. `QuantLab.audit(...)` reruns fixed weights under alternative delays, costs and rebalance rules.

```python
audit = lab.audit(
    "sma",
    fast=20,
    slow=100,
    execution_delays=(0, 1, 2),
    linear_costs_bps=(0, 5, 10, 25),
    rebalances=("bar", "W-FRI", "ME"),
)

print(audit.summary)
print(audit.diagnostics)
audit.plot()
```

The result contains:

```python
audit.summary      # metrics for every implementation contract
audit.diagnostics  # cross-contract dispersion statistics
audit.results      # dictionary of individual BacktestResult objects
```

Lower-level usage:

```python
from asrquant import implementation_audit

audit = implementation_audit(
    prices,
    weights,
    base_spec=spec,
    execution_delays=(0, 1, 2),
    linear_costs_bps=(0, 5, 10),
    rebalances=("bar", "ME"),
)
```

---

## Parameter sweeps, surfaces and animations

### Simple parameter sweep

```python
results = lab.sweep(
    "sma",
    {
        "fast": [5, 10, 20, 30],
        "slow": [50, 100, 150, 200],
    },
    metric="Sharpe",
    costs_bps=5,
)

print(results.head())
```

### Generic two-dimensional surface

```python
import asrquant as asr

surface = lab.surface(
    lambda risk_aversion, cost: -(risk_aversion - 2.0) ** 2 - 0.04 * cost,
    x_values=asr.math.linspace(0.1, 5.0, 40),
    y_values=asr.math.linspace(0.0, 25.0, 40),
    x_name="risk_aversion",
    y_name="cost",
    z_name="utility",
)

surface.plot("surface")
surface.plot("heatmap")
surface.plot("contour")
```

### Multidimensional parameter exploration

Any finite experiment can be explored if each parameter combination returns a scalar or an object from which a scalar can be extracted.

```python
parameter_grid = {
    "risk_aversion": asr.math.linspace(0.1, 5.0, 30),
    "transaction_cost": asr.math.linspace(0.0, 25.0, 30),
    "hedge_frequency": [1, 5, 20],
    "volatility": [0.15, 0.20, 0.30, 0.40],
    "model": ["linear", "neural"],
}

surface = lab.parameter_surface(
    train_and_evaluate,
    parameter_grid,
    x="risk_aversion",
    y="transaction_cost",
    animate_by=["hedge_frequency", "volatility", "model"],
    metric="metrics.entropic_utility",
    z_name="entropic utility",
    n_jobs=4,
    max_evaluations=100_000,
)
```

`lab.explore(...)` is an alias:

```python
surface = lab.explore(
    experiment,
    parameter_grid,
    x="parameter_a",
    y="parameter_b",
    animate_by=["regime", "model"],
    metric=lambda output: output.test_metrics["cvar"],
)
```

### Metric extraction

The experiment may return:

- a Python number;
- a dictionary;
- a pandas Series;
- a dataclass;
- a `BacktestResult`;
- a machine-learning result;
- a pricing result;
- any custom object.

Select the plotted scalar with:

```python
metric="Sharpe"
metric="metrics.Sharpe"
metric="out_of_sample.cvar"
metric=lambda result: result.losses[-1]
```

### Backtest parameter surface

```python
surface = lab.backtest_parameter_surface(
    "sma",
    {
        "fast": [5, 10, 20, 30],
        "slow": [40, 80, 120, 160],
        "costs_bps": [0, 5, 10, 20],
        "execution_delay": [0, 1, 2],
    },
    x="fast",
    y="slow",
    animate_by=["costs_bps", "execution_delay"],
    metric="Sharpe",
    error_policy="nan",
)
```

`costs_bps` and `execution_delay` are applied to the backtest contract. Other grid parameters are passed to the strategy.

### Surface from an existing DataFrame or CSV

```python
import asrquant as asr

results = asr.read_table("experiment_results.csv")

surface = lab.surface_from_frame(
    results,
    x="gamma",
    y="cost_bps",
    z="utility",
    frame_cols=["hedge_every", "volatility", "model"],
    agg="mean",
)
```

### Vectorized formulas

Set `vectorized=True` when the function accepts arrays for the two surface axes.

```python
surface = lab.surface(
    vectorized_formula,
    strikes,
    maturities,
    x_name="strike",
    y_name="maturity",
    fixed_params={"spot": 100, "rate": 0.03, "volatility": 0.20},
    vectorized=True,
)
```

### Positional functions

The default `call_style="keyword"` calls the experiment with named parameters. Use positional style only when necessary:

```python
surface = lab.surface(
    positional_function,
    x_values,
    y_values,
    call_style="positional",
)
```

### Error policy

```python
surface = lab.parameter_surface(
    experiment,
    parameter_grid,
    x="x",
    y="y",
    error_policy="nan",
)
```

`error_policy="nan"` preserves the grid and stores failed evaluations as missing values. `error_policy="raise"` stops at the first error.

### Evaluation limit

```python
surface = lab.parameter_surface(
    experiment,
    parameter_grid,
    x="x",
    y="y",
    animate_by=["a", "b"],
    max_evaluations=50_000,
)
```

The safeguard prevents accidental Cartesian explosions.

### Progress callback

```python
def progress(done: int, total: int) -> None:
    print(f"{done}/{total}")

surface = lab.parameter_surface(
    experiment,
    parameter_grid,
    x="x",
    y="y",
    progress=progress,
)
```

### Surface result API

```python
surface.summary
surface.frame_count
surface.frame_labels
surface.is_animated
surface.parameters_at(0)
surface.best("max")
surface.best("min")
surface.to_frame(frame=0)
surface.to_long_frame()
```

### Static plotting

```python
surface.plot("surface", frame=0)
surface.plot("heatmap", frame=0)
surface.plot("contour", frame=0)
surface.plot("surface", frame=0, interactive=True)
```

### Animation in memory

```python
animation = surface.animate(
    kind="surface",
    interval=250,
    repeat=True,
    stable_scale=True,
    elevation=30,
    azimuth=-60,
    rotate_camera=2,
)
```

Available animation kinds:

```text
surface
heatmap
contour
```

### Animation export

```python
surface.save_animation("surface.html")
surface.save_animation("surface.gif", kind="heatmap", fps=8)
surface.save_animation("surface.mp4", kind="surface", fps=12)
```

- HTML uses an interactive Plotly animation with play/pause controls and a slider.
- GIF requires a compatible Matplotlib/Pillow writer.
- MP4 requires FFmpeg.

### Export each frame

```python
paths = surface.export_frames(
    "frames",
    kind="contour",
    prefix="deep_hedging",
)
```

### Scientific interpretation

A geometric surface can display only two explicit axes. Higher-dimensional parameters are represented as:

- fixed values;
- successive slices;
- animation frames;
- categorical frame labels.

The plotting engine does not remove the need to justify parameter ranges, metrics, random seeds or out-of-sample protocols.

See [`docs/parameter_surfaces.md`](docs/parameter_surfaces.md) for the dedicated surface guide.

---

## Stochastic simulation and Monte Carlo

### Unified simulation interface

```python
simulation = lab.monte_carlo(
    "gbm",
    drift=0.05,
    volatility=0.20,
    maturity=1.0,
    steps=252,
    paths=10_000,
    random_state=7,
)
```

For a single-asset `QuantLab`, the latest observed price is used as `initial` unless explicitly supplied.

### Available stochastic models

| Model | Dispatcher names | Main parameters |
|---|---|---|
| Arithmetic Brownian motion | `abm`, `brownian` | `initial`, `drift`, `volatility`, `maturity`, `steps`, `paths` |
| Geometric Brownian motion | `gbm` | `initial`, `drift`, `volatility`, `antithetic` |
| Ornstein-Uhlenbeck | `ou`, `ornstein_uhlenbeck` | `initial`, `speed`, `mean`, `volatility` |
| Cox-Ingersoll-Ross | `cir` | `initial`, `speed`, `mean`, `volatility` |
| Vasicek | `vasicek` | `initial`, `speed`, `mean`, `volatility` |
| Heston | `heston` | `initial_variance`, `mean_reversion`, `long_variance`, `vol_of_vol`, `correlation` |
| Merton jump diffusion | `merton`, `jump_diffusion` | `jump_intensity`, `jump_mean`, `jump_volatility` |

### Direct model functions

```python
from asrquant import (
    arithmetic_brownian_motion,
    geometric_brownian_motion,
    ornstein_uhlenbeck,
    cir_process,
    vasicek_process,
    heston_process,
    merton_jump_diffusion,
)
```

### GBM

```python
from asrquant import geometric_brownian_motion

simulation = geometric_brownian_motion(
    initial=100,
    drift=0.05,
    volatility=0.20,
    maturity=1,
    steps=252,
    paths=20_000,
    antithetic=True,
    random_state=7,
)
```

### Heston

```python
simulation = lab.monte_carlo(
    "heston",
    initial=100,
    drift=0.03,
    initial_variance=0.04,
    mean_reversion=2.0,
    long_variance=0.04,
    vol_of_vol=0.5,
    correlation=-0.7,
    maturity=1,
    steps=252,
    paths=20_000,
    random_state=7,
)
```

For Heston simulations, variance paths are available as:

```python
simulation.variance_paths
```

### Correlated multi-asset GBM

```python
import asrquant as asr

simulation = asr.correlated_gbm(
    initial=asr.math.array([100.0, 80.0, 120.0]),
    drift=asr.math.array([0.05, 0.04, 0.06]),
    volatility=asr.math.array([0.20, 0.15, 0.25]),
    correlation=asr.math.array(
        [
            [1.0, 0.40, 0.30],
            [0.40, 1.0, 0.20],
            [0.30, 0.20, 1.0],
        ]
    ),
    maturity=1.0,
    steps=252,
    paths=5_000,
    random_state=7,
)
```

### Simulation outputs

```python
simulation.paths
simulation.terminal
simulation.summary
simulation.parameters
simulation.model
```

### Simulation plots

```python
simulation.plot("paths", max_paths=50)
simulation.plot("terminal")
simulation.plot("fan")
```

Additional functions:

```python
from asrquant.viz.simulation import (
    quantile_bands,
    first_passage_distribution,
    increment_diagnostics,
    terminal_distribution,
    paths,
)
```

### Generic Monte Carlo pricing

```python
import asrquant as asr

simulation = asr.geometric_brownian_motion(
    initial=100,
    drift=0.03,
    volatility=0.20,
    maturity=1,
    steps=252,
    paths=100_000,
    antithetic=True,
    random_state=7,
)

result = asr.monte_carlo_price(
    simulation,
    payoff=lambda terminal: asr.math.maximum(terminal - 100, 0.0),
    rate=0.03,
    maturity=1.0,
    confidence=0.95,
)

print(result.summary)
```

The output includes price, standard error, confidence interval, discounted pathwise payoffs and the underlying simulation.

### European option Monte Carlo

```python
from asrquant import european_option_mc

mc = european_option_mc(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
    paths=100_000,
    antithetic=True,
    random_state=7,
)
```

### Asian option Monte Carlo

```python
from asrquant import asian_option_mc

asian = asian_option_mc(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
    paths=50_000,
    steps=252,
    random_state=7,
)
```

### Synthetic regime-switching market

```python
from asrquant.simulation import regime_switching_prices

synthetic_prices = regime_switching_prices(
    periods=1500,
    assets=4,
    start=100,
    random_state=7,
)
```

### Stationary bootstrap

```python
from asrquant.simulation import stationary_bootstrap

samples = stationary_bootstrap(
    lab.returns,
    samples=1000,
    expected_block=20,
    random_state=7,
)
```

---

## Derivative pricing

### High-level option interface

```python
option = lab.option(
    "black_scholes",
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
)

print(option.summary)
```

For a one-asset `QuantLab`, the latest observed value is used as spot or forward unless supplied explicitly.

### Supported pricing models

| Model | Common names | Notes |
|---|---|---|
| Black-Scholes-Merton | `black_scholes`, `bsm` | European call or put, optional dividend yield |
| Bachelier normal model | `bachelier`, `normal` | European option on a forward with normal volatility |
| Black-76 | `black76`, `black_76` | European option on a forward or futures price |
| Cox-Ross-Rubinstein | `crr`, `binomial` | European or American call/put |
| Monte Carlo | `monte_carlo`, `mc` | European option under risk-neutral GBM |

### Black-Scholes-Merton

```python
from asrquant import black_scholes_price, black_scholes_greeks

price = black_scholes_price(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
    dividend=0.01,
)

greeks = black_scholes_greeks(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
    dividend=0.01,
)
```

Greeks include delta, gamma, vega, theta and rho.

### Bachelier

```python
from asrquant import bachelier_price, bachelier_greeks

price = bachelier_price(
    forward=100,
    strike=105,
    maturity=1,
    normal_volatility=12,
    option="call",
    discount=0.97,
)
```

### Black-76

```python
from asrquant import black76_price

price = black76_price(
    forward=100,
    strike=105,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
)
```

### CRR binomial tree

```python
from asrquant import crr_binomial_price

american_put = crr_binomial_price(
    spot=100,
    strike=105,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="put",
    steps=1000,
    dividend=0.0,
    american=True,
)
```

### Implied volatility

```python
from asrquant import implied_volatility

iv = implied_volatility(
    market_price=9.50,
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    option="call",
    model="black_scholes",
)
```

Supported inversion models are Black-Scholes-Merton, Black-76 and Bachelier.

### Finite-difference Greeks

```python
from asrquant.derivatives import finite_difference_greeks

fd = finite_difference_greeks(
    black_scholes_price,
    spot=100,
    volatility=0.20,
    rate=0.03,
    strike=100,
    maturity=1,
    option="call",
)
```

### Payoff

```python
import asrquant as asr

terminal = asr.math.linspace(50, 150, 500)
pnl = asr.options.option_payoff(
    terminal,
    strike=100,
    option="call",
    premium=9.41,
    position=1.0,
)
```

### Derivative visualizations

```python
from asrquant.viz.derivatives import (
    payoff_diagram,
    option_price_curve,
    greek_curves,
    greek_heatmap,
    greek_surface,
    volatility_surface,
    implied_volatility_smile,
    term_structure_slices,
    scenario_pnl_surface,
    model_comparison,
    monte_carlo_convergence,
    yield_curve,
)
```

Example volatility surface:

```python
fig = volatility_surface(
    strikes,
    maturities,
    implied_vol_matrix,
    interactive=True,
)
```

---

## Martingale diagnostics

```python
diagnostic = lab.martingale_test(
    asset="SPY",
    rate=0.03,
    annualization=252,
    lags=10,
)

print(diagnostic.statistics)
print(diagnostic.conclusion)
diagnostic.plot()
```

Lower-level usage:

```python
from asrquant import discount_process, martingale_diagnostics

discounted = discount_process(price_series, rate=0.03, annualization=252)
diagnostic = martingale_diagnostics(discounted, lags=10)
```

The diagnostics examine finite-sample implications such as:

- mean increments;
- predictability of increments;
- serial correlation;
- HAC-robust regression inference.

Failure to reject these diagnostics is **not** a mathematical proof that a process is a martingale.

---

## Regression and econometrics

### High-level regression interface

```python
fit = lab.regress(
    y="Strategy",
    x=["Market", "Value", "Momentum"],
    method="ols",
    use_returns=True,
    covariance="HAC",
    maxlags=5,
)

print(fit.summary)
fit.plot("residuals")
fit.plot("coefficients")
fit.plot("fitted")
```

Available high-level methods:

```text
ols
quantile
polynomial
logistic
ridge
lasso
elastic_net
```

### OLS and robust covariance

```python
from asrquant.statistics import ols

fit = ols(
    y,
    x,
    add_constant=True,
    covariance="HAC",
    maxlags=5,
)
```

Accepted covariance values:

```text
HAC
HC0
HC1
HC2
HC3
nonrobust
classical
```

### Regression result

```python
fit.model                 # advanced internal fitted-model object
fit.coefficients
fit.confidence_intervals
fit.fitted
fit.residuals
fit.diagnostics
fit.summary
```

The OLS diagnostics include R-squared, adjusted R-squared, Durbin-Watson, Jarque-Bera p-value, Ljung-Box p-value, Breusch-Pagan p-value and White-test p-value when applicable.

### Rolling regression

```python
from asrquant.statistics import rolling_regression

rolling_beta = rolling_regression(
    y=asset_returns,
    x=factor_returns,
    window=63,
)
```

### Factor regression

```python
from asrquant.statistics import factor_regression

factor_fit = factor_regression(
    asset_returns=strategy_returns,
    factors=factors,
    risk_free=risk_free_series,
    covariance="HAC",
    maxlags=5,
)
```

### Quantile regression

```python
from asrquant.statistics import quantile_regression

left_tail = quantile_regression(y, x, quantile=0.05)
median = quantile_regression(y, x, quantile=0.50)
```

### Polynomial regression

```python
from asrquant.statistics import polynomial_regression

fit = polynomial_regression(y, x, degree=3, covariance="HAC")
```

### Regularized regression

```python
from asrquant.statistics import regularized_regression

ridge = regularized_regression(y, x, method="ridge", alpha=1.0)
lasso = regularized_regression(y, x, method="lasso", alpha=0.01)
elastic = regularized_regression(
    y,
    x,
    method="elastic_net",
    alpha=0.01,
    l1_ratio=0.5,
)
```

### Logistic regression

```python
from asrquant.statistics import logistic_regression

classification_fit = logistic_regression(
    direction_target,
    features,
    covariance="HC1",
)
```

### Stationarity tests

```python
from asrquant.statistics import stationarity_tests

stationarity = stationarity_tests(price_or_spread_series)
print(stationarity)
```

ADF and KPSS are reported together to reduce one-test overinterpretation.

### Cointegration

```python
from asrquant.statistics import cointegration_test

result = cointegration_test(series_a, series_b, trend="c")
```

### Granger predictability

```python
from asrquant.statistics import granger_causality

p_values = granger_causality(x, y, maxlag=5)
```

This is a predictive test and does not establish structural causality.

### ARIMA and VAR

```python
from asrquant.statistics import arima_fit, var_fit

arima = arima_fit(series, order=(1, 0, 1), trend="c")
var = var_fit(multivariate_returns, lags=2, trend="c")
```

### Moving-block bootstrap

```python
import asrquant as asr

bootstrap = asr.stats.block_bootstrap(
    result.net_returns,
    statistic=asr.math.mean,
    n_boot=5000,
    block_size=20,
    confidence=0.95,
    random_state=7,
)
```

### Permutation test

```python
from asrquant.statistics import permutation_test

permutation = permutation_test(
    strategy_a_returns,
    strategy_b_returns,
    n_permutations=5000,
    random_state=7,
)
```

### Multiple testing

```python
from asrquant.statistics import benjamini_hochberg

adjusted = benjamini_hochberg(p_values, alpha=0.05)
```

### Regression visualizations

```python
from asrquant.viz.regression import (
    regression_scatter,
    residual_diagnostics,
    coefficient_intervals,
    actual_vs_fitted,
    rolling_coefficients,
    residual_acf,
    prediction_interval,
    influence_plot,
    partial_residual_plot,
    factor_exposure_heatmap,
)
```

---

## Machine learning

ASRQuant's built-in ML workflow emphasizes chronological evaluation. It does not randomly shuffle time-series observations.

### Feature generation

```python
features = lab.ml_features(
    asset="SPY",
    windows=(5, 20, 63),
)
```

Generated features include one-period returns, log returns, momentum, volatility, rolling z-scores, rolling drawdowns and RSI.

### Explicit lag features

```python
from asrquant import lag_features

lagged = lag_features(
    lab.returns[["SPY", "QQQ"]],
    lags=[1, 2, 5, 10, 20],
    include_current=False,
)
```

### Forward target

```python
from asrquant import forward_target

target_return = forward_target(lab.prices["SPY"], horizon=5)
target_direction = forward_target(
    lab.prices["SPY"],
    horizon=5,
    classification=True,
)
```

The target is aligned at decision time and future observations are shifted backward only into the target column.

### Walk-forward regression

```python
import asrquant as asr

features = lab.ml_features("SPY").dropna()
target = forward_target(lab.prices["SPY"], horizon=5)

model = asr.models.random_forest(
    task="regression",
    trees=300,
    depth=5,
    seed=7,
)

ml_result = lab.ml_walk_forward(
    model,
    features,
    target,
    train_size=500,
    test_size=63,
    step=63,
    gap=5,
    expanding=True,
    task="regression",
)

print(ml_result.aggregate_metrics)
print(ml_result.fold_metrics)
ml_result.plot("predictions")
ml_result.plot("residuals")
```

### Walk-forward classification

```python
classifier = asr.models.logistic_regression(iterations=2000)

classification = lab.ml_walk_forward(
    classifier,
    features,
    target_direction,
    train_size=500,
    test_size=63,
    gap=5,
    task="classification",
)

print(classification.aggregate_metrics)
classification.plot("predictions")
classification.plot("roc")
```

### Walk-forward result fields

```python
ml_result.estimator_name
ml_result.task
ml_result.predictions
ml_result.actual
ml_result.probabilities
ml_result.fold_metrics
ml_result.aggregate_metrics
ml_result.fitted_models
```

### ML visualizations

```python
from asrquant.viz.ml import (
    prediction_path,
    residuals,
    confusion,
    roc,
    precision_recall,
    calibration,
    lift_curve,
    feature_importance,
    permutation_importance_plot,
    learning_curve_plot,
    regime_probabilities,
)
```

SHAP and hidden Markov functionality requires the optional `ml` dependency group where used by the user's workflow.

---

## Portfolio optimization

```python
from asrquant.optimization import estimate_covariance

returns = lab.returns.dropna()
expected_returns = returns.mean() * 252
covariance = estimate_covariance(returns, method="ledoit_wolf")
```

### Covariance estimators

```python
sample_cov = estimate_covariance(returns, method="sample")
ewma_cov = estimate_covariance(returns, method="ewma", span=60)
lw_cov = estimate_covariance(returns, method="ledoit_wolf")
oas_cov = estimate_covariance(returns, method="oas")
```

### Minimum variance

```python
from asrquant.optimization import minimum_variance

weights = minimum_variance(covariance, long_only=True)
```

### Maximum Sharpe

```python
from asrquant.optimization import maximum_sharpe

weights = maximum_sharpe(
    expected_returns,
    covariance,
    risk_free_rate=0.02,
    long_only=True,
)
```

### Equal risk contribution

```python
from asrquant.optimization import equal_risk_contribution

weights = equal_risk_contribution(covariance)
```

### Maximum diversification

```python
from asrquant.optimization import maximum_diversification

weights = maximum_diversification(covariance, long_only=True)
```

### Hierarchical risk parity

```python
from asrquant.optimization import hierarchical_risk_parity

weights = hierarchical_risk_parity(returns)
```

### Efficient frontier

```python
from asrquant.optimization import efficient_frontier

frontier = efficient_frontier(
    expected_returns,
    covariance,
    points=50,
    long_only=True,
)
```

### Random portfolio cloud

```python
from asrquant.optimization import random_frontier

cloud = random_frontier(
    expected_returns,
    covariance,
    n_portfolios=10_000,
    risk_free_rate=0.02,
    random_state=7,
)
```

### Black-Litterman

```python
import asrquant as asr

posterior_mean, posterior_covariance = asr.portfolio.black_litterman(
    covariance=covariance,
    market_weights=asr.math.array([0.4, 0.3, 0.2, 0.1]),
    risk_aversion=2.5,
    views=asr.math.array([0.03]),
    pick_matrix=asr.math.array([[1.0, -1.0, 0.0, 0.0]]),
    tau=0.05,
)
```

### Risk contributions

```python
from asrquant.optimization import (
    marginal_risk_contribution,
    risk_contributions,
    portfolio_return,
    portfolio_volatility,
)

mrc = marginal_risk_contribution(weights, covariance.to_numpy())
trc = risk_contributions(weights, covariance.to_numpy())
portfolio_mu = portfolio_return(weights, expected_returns.to_numpy())
portfolio_sigma = portfolio_volatility(weights, covariance.to_numpy())
```

### Portfolio plots

```python
from asrquant.viz.portfolio import (
    allocation_pie,
    covariance_heatmap,
    efficient_frontier,
    frontier_surface,
    risk_contribution_plot,
    rolling_risk_contributions,
    weights_heatmap,
    correlation_network,
    correlation_dendrogram,
    concentration_curve,
)
```

---

## Volatility models

### Realized volatility

```python
from asrquant import realized_volatility

rv = realized_volatility(
    lab.returns["SPY"],
    window=21,
    annualization=252,
)
```

### Parkinson estimator

```python
from asrquant import parkinson_volatility

parkinson = parkinson_volatility(
    ohlcv["High"],
    ohlcv["Low"],
    window=21,
)
```

### Garman-Klass estimator

```python
from asrquant import garman_klass_volatility

gk = garman_klass_volatility(
    ohlcv["Open"],
    ohlcv["High"],
    ohlcv["Low"],
    ohlcv["Close"],
    window=21,
)
```

### EWMA volatility

```python
from asrquant import ewma_volatility

ewma = ewma_volatility(lab.returns["SPY"], decay=0.94)
```

### GARCH

```bash
pip install ".[volatility]"
```

```python
from asrquant import garch_forecast

garch = garch_forecast(
    lab.returns["SPY"].dropna(),
    p=1,
    q=1,
    horizon=5,
    distribution="t",
    annualization=252,
)

print(garch.forecast)
garch.plot()
```

---

## Fixed income

ASRQuant 1.1.0 exposes the complete research-oriented rates stack through `asr.rates` and the high-level `RateQuantLab`: conventions and compounding; discount/zero/forward/par curves; deposit/FRA/swap bootstrapping; OIS/multi-curve projection; Nelson-Siegel/Svensson; bonds; FRAs/futures/IRS/basis; DV01/key-rate risk/convexity; caps/floors; swaptions; Black and normal rate vol; SABR; Vasicek/CIR/Hull-White/Ho-Lee/Black-Karasinski; HJM/LMM; RFR/OIS compounding; bond forwards; FX-forward/CIP and cross-currency foundations; zero-coupon inflation; Bermudan LSM; curve scenarios/key-rate hedging; PCA; carry/roll; no-arbitrage and interpolation-risk diagnostics.

```python
import asrquant as asr

lab = asr.RateQuantLab.from_zero_rates(
    [0.25, 0.5, 1, 2, 3, 5, 7, 10],
    [0.020, 0.021, 0.022, 0.023, 0.024, 0.026, 0.027, 0.028],
)

par_5y = lab.par_swap(0, 5, frequency=2)
pv = lab.swap(0, 5, fixed_rate=0.025, notional=10_000_000)
print(lab.diagnostics())
```

For official ECB curve research, `ECBProvider.yield_curve_history()` downloads and aligns selected maturities and `RateQuantLab.from_ecb()` constructs the latest common curve. The full scope, conventions and limitations are documented in `docs/interest_rate_derivatives.md`.

### Legacy bond helpers

### Zero-coupon bond

```python
from asrquant import zero_coupon_price

price = zero_coupon_price(
    face=100,
    rate=0.04,
    maturity=5,
    compounding=2,
)
```

Set `compounding=None` for continuous compounding.

### Fixed-coupon bond price

```python
from asrquant import bond_price

price = bond_price(
    face=100,
    coupon_rate=0.05,
    maturity=10,
    yield_rate=0.04,
    frequency=2,
)
```

### Yield to maturity

```python
from asrquant import yield_to_maturity

ytm = yield_to_maturity(
    price=108.11,
    face=100,
    coupon_rate=0.05,
    maturity=10,
    frequency=2,
)
```

### Duration and convexity

```python
from asrquant import macaulay_duration, modified_duration, convexity

mac = macaulay_duration(100, 0.05, 10, 0.04, frequency=2)
mod = modified_duration(100, 0.05, 10, 0.04, frequency=2)
conv = convexity(100, 0.05, 10, 0.04, frequency=2)
```

### Cash flows and zero-curve bootstrap

```python
from asrquant.fixed_income import bond_cashflows, bootstrap_zero_curve

cashflows = bond_cashflows(
    face=100,
    coupon_rate=0.05,
    maturity=5,
    frequency=2,
)

zero_curve = bootstrap_zero_curve(instruments, frequency=1)
```

---

## Validation and stress testing

### Walk-forward splits

```python
from asrquant.validation import walk_forward_splits

for split in walk_forward_splits(
    n_samples=1000,
    train_size=500,
    test_size=100,
    step=100,
    expanding=True,
    gap=5,
):
    train_indices = split.train
    test_indices = split.test
```

### Purged K-fold

```python
from asrquant.validation import purged_kfold_splits

for split in purged_kfold_splits(
    n_samples=1000,
    n_splits=5,
    purge=5,
    embargo=10,
):
    ...
```

### Look-ahead diagnostics

```python
from asrquant.validation import detect_lookahead

diagnostics = detect_lookahead(signal, source_data)
print(diagnostics)
```

This is a heuristic diagnostic, not a formal proof of the absence of leakage.

### Stress testing

```python
from asrquant.validation import stress_returns

stress = stress_returns(
    result.net_returns,
    shocks={
        "mild selloff": -0.03,
        "severe selloff": -0.10,
    },
    windows={
        "historical period": ("2020-02-20", "2020-04-01"),
    },
)

print(stress)
```

---

## Visualization system

ASRQuant v1.0.0 exposes **108 public plotting entry points** across high-level result methods and lower-level visualization modules.

### Backtest visualizations

Use `BacktestResult.plot(...)`:

```text
dashboard
equity
drawdown
equity_drawdown
rolling_metrics
monthly_heatmap
annual_returns
turnover
costs
weights
exposures
return_contributions
trade_pnl
benchmark
```

### Market-data visualizations

```python
from asrquant.viz.market import (
    price_chart,
    returns_chart,
    distribution,
    ecdf,
    qq_plot,
    box_violin,
    autocorrelation,
    lag_scatter,
    rolling_statistics,
    rolling_correlation,
    rolling_beta,
    correlation_heatmap,
    scatter_matrix,
    monthly_heatmap,
    calendar_heatmap,
    seasonality_boxplot,
    period_return_ranking,
    volatility_cone,
    candlestick,
)
```

### Risk visualizations

```python
from asrquant.viz.risk import (
    var_es_plot,
    rolling_var_es,
    var_exceedances,
    tail_plot,
    rolling_drawdown,
    drawdown_duration_plot,
    drawdown_table_plot,
    rolling_skew_kurtosis,
    expected_shortfall_contributions,
    risk_return_scatter,
    monte_carlo_fan,
    stress_plot,
    sensitivity_heatmap,
    implementation_audit_plot,
)
```

### Generic 2D, 3D and animated visualizations

```python
from asrquant.viz.general import (
    response_heatmap,
    parameter_heatmap,
    contour,
    surface3d,
    animate_surface,
)
```

### Simulation visualizations

```python
from asrquant.viz.simulation import (
    paths,
    terminal_distribution,
    quantile_bands,
    first_passage_distribution,
    increment_diagnostics,
    convergence_diagnostics,
    martingale_diagnostics_plot,
)
```

### Regression visualizations

See [Regression and econometrics](#regression-and-econometrics).

### Portfolio visualizations

See [Portfolio optimization](#portfolio-optimization).

### Derivative visualizations

See [Derivative pricing](#derivative-pricing).

### Machine-learning visualizations

See [Machine learning](#machine-learning).

### Market-microstructure visualizations

```python
from asrquant.viz.microstructure import (
    bid_ask_spread,
    spread_distribution,
    order_book_depth,
    order_flow_imbalance,
    price_impact_scatter,
    slippage_curve,
    volume_profile,
    trade_timeline,
    intraday_seasonality,
)
```

### Static versus interactive rendering

Use `asr.visualize(...)`, `asr.show(...)` and `asr.save(...)` for backend-neutral rendering. Standard figures use the validated static engine internally; interactive surfaces and animations use the validated HTML engine internally. Normal users do not import either backend.

```python
surface.plot("surface", interactive=True)
```

The exhaustive visualization reference is available in [`docs/visualization_catalog.md`](docs/visualization_catalog.md).

---

## Reports and provenance

### Portable HTML report

```python
result.report("report.html")
```

Lower-level function:

```python
from asrquant.report import create_html_report

html_or_path = create_html_report(
    result,
    output="report.html",
    title="Research report",
)
```

### Experiment fingerprint

```python
print(result.fingerprint)
print(result.spec.fingerprint())
```

### Machine-readable manifest

```python
from asrquant import build_manifest

manifest = build_manifest(
    result,
    project="Deep hedging parameter study",
    author="Alpha Stochastic Research",
    dataset="synthetic_heston_v1",
)

manifest.to_json("experiment_manifest.json")
```

The manifest records environment versions and data, specification and experiment fingerprints.

### Store parameters and random seeds

Use the `metadata` field of `BacktestSpec` and save model configuration beside every exported result.

```python
spec = BacktestSpec(
    metadata={
        "seed": 7,
        "data_vintage": "2026-07-31",
        "commit": "abc1234",
    }
)
```

---

## Command-line interface

### Help and version

```bash
asrquant --help
asrquant --version
```

### Synthetic demonstration

```bash
asrquant demo --output asrquant_demo.html
```

### Backtest a local file

```bash
asrquant backtest prices.csv \
  --date-column Date \
  --strategy sma \
  --fast 20 \
  --slow 100 \
  --costs-bps 5 \
  --execution-delay 1 \
  --output sma_report.html
```

Supported CLI strategy names:

```text
buy_hold
sma
momentum
mean_reversion
vol_target
breakout
bollinger
rsi
pairs
```

### Simulate a stochastic process

```bash
asrquant simulate \
  --model heston \
  --initial 100 \
  --drift 0.03 \
  --initial-variance 0.04 \
  --long-variance 0.04 \
  --mean-reversion 2.0 \
  --vol-of-vol 0.5 \
  --correlation -0.7 \
  --maturity 1 \
  --steps 252 \
  --paths 10000 \
  --seed 7 \
  --output heston_paths.csv
```

Supported models:

```text
abm
gbm
ou
cir
vasicek
heston
merton
```

### Price an option

```bash
asrquant price \
  --model black_scholes \
  --spot 100 \
  --strike 100 \
  --maturity 1 \
  --rate 0.03 \
  --volatility 0.20 \
  --option call
```

American CRR example:

```bash
asrquant price \
  --model crr \
  --spot 100 \
  --strike 105 \
  --maturity 1 \
  --rate 0.03 \
  --volatility 0.20 \
  --option put \
  --steps 1000 \
  --american
```

### Download data

```bash
asrquant download SPY QQQ TLT \
  --provider yahoo \
  --start 2020-01-01 \
  --end 2026-01-01 \
  --field Close \
  --output prices.csv
```

```bash
asrquant download BTCUSDT \
  --provider binance \
  --interval 1h \
  --limit 1000 \
  --field Close \
  --output btc.csv
```

---

## Complete end-to-end examples

### 1. CSV to audited report

```python
from asrquant import QuantLab, BacktestSpec, CostModel, build_manifest

lab = QuantLab.from_csv(
    "prices.csv",
    date_column="Date",
    columns=["SPY", "QQQ", "TLT"],
    missing_data="drop",
)

print(lab.quality)

spec = BacktestSpec(
    execution_delay=1,
    rebalance="ME",
    max_gross_leverage=1.0,
    max_abs_weight=0.50,
    costs=CostModel(
        commission_bps=2,
        spread_bps=2,
        slippage_bps=1,
    ),
)

result = lab.backtest(
    "momentum",
    lookback=126,
    top_fraction=0.34,
    long_short=True,
    spec=spec,
)

print(result.metrics)
result.plot("dashboard")
result.report("momentum_report.html")

manifest = build_manifest(result, research_id="W01-C01")
manifest.to_json("momentum_manifest.json")

audit = lab.audit(
    "momentum",
    lookback=126,
    top_fraction=0.34,
    execution_delays=(0, 1, 2),
    linear_costs_bps=(0, 5, 10, 20),
    rebalances=("bar", "W-FRI", "ME"),
)

audit.summary.to_csv("implementation_audit.csv")
audit.plot()
```

### 2. Black-Scholes validation with Monte Carlo

```python
from asrquant import black_scholes_price, european_option_mc

analytic = black_scholes_price(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
)

mc = european_option_mc(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    option="call",
    paths=200_000,
    antithetic=True,
    random_state=7,
)

print("Analytic:", analytic)
print(mc.summary)
print("Absolute error:", abs(float(analytic) - mc.price))
```

### 3. Deep-hedging-style parameter animation

```python
import asrquant as asr


def evaluate_hedging(
    risk_aversion,
    transaction_cost,
    hedge_frequency,
    volatility,
):
    # Replace this compact example with a PyTorch/JAX training callback.
    hedging_error = (
        0.08 / asr.math.sqrt(hedge_frequency)
        + 0.6 * volatility
        + 0.002 * transaction_cost * hedge_frequency
    )
    utility = -hedging_error - risk_aversion * hedging_error**2
    return {
        "metrics": {
            "utility": utility,
            "hedging_error": hedging_error,
        }
    }


surface = asr.open_lab(prices).explore(
    evaluate_hedging,
    {
        "risk_aversion": asr.math.linspace(0.1, 5.0, 35),
        "transaction_cost": asr.math.linspace(0.0, 25.0, 35),
        "hedge_frequency": [1, 5, 20, 63],
        "volatility": [0.15, 0.20, 0.30, 0.40],
    },
    x="risk_aversion",
    y="transaction_cost",
    animate_by=["hedge_frequency", "volatility"],
    metric="metrics.utility",
    z_name="utility",
    n_jobs=4,
)

print(surface.summary)
print(surface.best("max"))
surface.save_animation("hedging_landscape.html")
surface.save_animation("hedging_landscape.gif", kind="heatmap", fps=8)
```

### 4. Walk-forward ML to tradable weights

```python
import asrquant as asr

lab = asr.open_lab("spy.csv", date_column="Date", columns=["SPY"])
features = lab.ml_features("SPY").dropna()
target = asr.forward_target(lab.prices["SPY"], horizon=5, classification=True)

model = asr.models.random_forest(
    task="classification",
    trees=300,
    depth=5,
    seed=7,
)

ml = lab.ml_walk_forward(
    model,
    features,
    target,
    train_size=500,
    test_size=63,
    step=63,
    gap=5,
    task="classification",
)

signal = (ml.probabilities > 0.55).astype(float)
weights = signal.reindex(lab.prices.index).fillna(0.0).to_frame("SPY")
result = lab.backtest(weights, costs_bps=5, execution_delay=1)

print(ml.aggregate_metrics)
print(result.metrics)
result.report("ml_strategy_report.html")
```

---

## API map

### Top-level exports

```python
from asrquant import (
    QuantLab,
    BacktestSpec,
    CostModel,
    MissingDataPolicy,
    PlotConfig,
    BacktestResult,
    AuditResult,
    SurfaceResult,
    SimulationResult,
    MonteCarloPriceResult,
    MartingaleResult,
    WalkForwardMLResult,
    OptionPrice,
)
```

### Data

```text
clean_prices
simple_returns
log_returns
load_prices
load_sql
resample_ohlcv
data_quality_report
data_fingerprint
```

### Backtesting and research

```text
run_backtest
compare_backtests
implementation_audit
parameter_sweep
strategy_comparison
```

### Surfaces

```text
evaluate_surface
evaluate_surface_animation
evaluate_parameter_surface
surface_from_dataframe
```

### Simulation

```text
simulate
simulate_gbm
arithmetic_brownian_motion
geometric_brownian_motion
ornstein_uhlenbeck
cir_process
vasicek_process
heston_process
merton_jump_diffusion
monte_carlo_price
european_option_mc
asian_option_mc
```

### Derivatives

```text
black_scholes_price
black_scholes_greeks
bachelier_price
bachelier_greeks
black76_price
crr_binomial_price
implied_volatility
price_option
```

### Providers

```text
MarketDataProvider
AlphaVantageProvider
BinanceProvider
FREDProvider
YahooProvider
PollingFeed
download
get_provider
```

### Fixed income

ASRQuant 1.1.0 exposes the complete research-oriented rates stack through `asr.rates` and the high-level `RateQuantLab`: conventions and compounding; discount/zero/forward/par curves; deposit/FRA/swap bootstrapping; OIS/multi-curve projection; Nelson-Siegel/Svensson; bonds; FRAs/futures/IRS/basis; DV01/key-rate risk/convexity; caps/floors; swaptions; Black and normal rate vol; SABR; Vasicek/CIR/Hull-White/Ho-Lee/Black-Karasinski; HJM/LMM; RFR/OIS compounding; bond forwards; FX-forward/CIP and cross-currency foundations; zero-coupon inflation; Bermudan LSM; curve scenarios/key-rate hedging; PCA; carry/roll; no-arbitrage and interpolation-risk diagnostics.

```python
import asrquant as asr

lab = asr.RateQuantLab.from_zero_rates(
    [0.25, 0.5, 1, 2, 3, 5, 7, 10],
    [0.020, 0.021, 0.022, 0.023, 0.024, 0.026, 0.027, 0.028],
)

par_5y = lab.par_swap(0, 5, frequency=2)
pv = lab.swap(0, 5, fixed_rate=0.025, notional=10_000_000)
print(lab.diagnostics())
```

For official ECB curve research, `ECBProvider.yield_curve_history()` downloads and aligns selected maturities and `RateQuantLab.from_ecb()` constructs the latest common curve. The full scope, conventions and limitations are documented in `docs/interest_rate_derivatives.md`.

### Legacy bond helpers

```text
zero_coupon_price
bond_price
yield_to_maturity
macaulay_duration
modified_duration
convexity
```

### Volatility

```text
realized_volatility
parkinson_volatility
garman_klass_volatility
ewma_volatility
garch_forecast
```

### Module namespaces

```text
asrquant.data
asrquant.providers
asrquant.strategies
asrquant.backtest
asrquant.audit
asrquant.metrics
asrquant.statistics
asrquant.validation
asrquant.optimization
asrquant.derivatives
asrquant.simulation
asrquant.martingales
asrquant.machine_learning
asrquant.fixed_income
asrquant.volatility
asrquant.surfaces
asrquant.research
asrquant.provenance
asrquant.report
asrquant.viz
```

Additional references:

- [`docs/api_catalog.md`](docs/api_catalog.md)
- [`docs/data_sources.md`](docs/data_sources.md)
- [`docs/model_catalog.md`](docs/model_catalog.md)
- [`docs/parameter_surfaces.md`](docs/parameter_surfaces.md)
- [`docs/visualization_catalog.md`](docs/visualization_catalog.md)

---

## Reproducibility rules

For serious research, always:

1. pin the ASRQuant version and dependency environment;
2. preserve raw data or a stable data-vintage identifier;
3. save the data fingerprint;
4. save the complete `BacktestSpec`;
5. use explicit random seeds;
6. distinguish in-sample selection from out-of-sample evaluation;
7. use execution delays consistent with information availability;
8. model realistic commissions, spread, slippage, impact and borrow costs;
9. report parameter-search breadth and multiple-testing controls;
10. preserve code, manifests, reports and benchmark outputs together.

Example:

```python
print(lab.source_metadata)
print(result.spec.to_dict())
print(result.spec.fingerprint())
print(result.fingerprint)
```

---

## Current limitations

ASRQuant v1.1.0 retains the stable public API and adds Research Discovery and the expanded rates stack. It deliberately does not claim to be a complete production trading platform. Current limitations include:

- a general-purpose asynchronous event-driven execution engine;
- exchange queue-position and full limit-order-book simulation;
- venue-specific fee schedules and maker/taker logic;
- a full limit-order-book simulator;
- automatic corporate-action reconstruction for arbitrary raw datasets;
- borrow recalls or security-specific short availability;
- a universal neural deep-hedging training implementation;
- distributed training or cluster scheduling;
- guarantees that external providers will maintain their APIs;
- guarantees that a backtest is free from economic misspecification, data snooping or overfitting.

The generic experiment engine can wrap PyTorch, JAX, TensorFlow or custom research functions, but the user remains responsible for the correctness and computational cost of those functions.

---

## Development and testing

### Run the release-validation suite

```bash
python scripts/test_all.py
```

The runner executes each test module in a fresh interpreter. This prevents plotting, BLAS, optional statistical backends and third-party pytest plugins from leaking global state across test families. A conventional `pytest` invocation remains useful during local development for targeted modules.

### Coverage

```bash
python -m coverage run --branch --source=src/asrquant -m pytest tests/test_production_readiness_v1.py
python -m coverage report --show-missing
```

### Linting

```bash
ruff check src tests examples
```

### Type checking

```bash
mypy src/asrquant
```

### Build distributions

```bash
python -m build
python -m twine check dist/*
```

### Validation status for v1.1.0

The supplied release was validated with:

- 154 automated tests across isolated test modules, including 18 paper-contract tests;
- wheel installation in an isolated environment;
- source-distribution installation;
- CSV, provider, backtest, simulation, pricing, martingale, regression, ML and surface examples;
- HTML, GIF and MP4 surface-animation exports;
- paper compilation and artifact-integrity checks.

See [`VALIDATION_v1.1.0.md`](VALIDATION_v1.1.0.md); the original 1.0.0 validation is retained for provenance.

Runtime measurements are environment-specific and are not performance guarantees.

### Contributing

Read:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md)

---

## Paper

The accompanying paper is:

> **ASRQuant: From Scientific Literature to Auditable Quantitative Decisions and Algorithmic Trading**  
> Manuscript v0.1.0 — software release ASRQuant 1.0.0.

Files:

- `paper/ASRQuant_paper.pdf`
- `paper/main.tex`

The paper formalizes the package architecture, backtest contract, stochastic and statistical components, implementation sensitivity, multidimensional parameter surfaces and reproducible validation protocol.

---

## Citation and license

ASRQuant is released under the **MIT License**. See [`LICENSE`](LICENSE).

Citation metadata is available in [`CITATION.cff`](CITATION.cff).

```text
Alpha Stochastic Research. ASRQuant: From Scientific Literature to Auditable
Quantitative Decisions and Algorithmic Trading. Version 1.0.0.
```

Project links:

- Website: <https://www.asr-lab.online>
- Repository: <https://github.com/Alpha-Stochastic-Research/asrquant>
- Contact: research@asr-lab.online
