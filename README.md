<div align="center">

# ASRQuant

### Auditable quantitative finance research in Python

**Research · Modelling · Analysis · Reproducibility**

`pip install asrquant`

</div>

---

ASRQuant is the open-source quantitative-finance toolkit developed by **Alpha Stochastic Research (ASR)**. It connects data, hypothesis discovery, statistical research, fixed income, derivatives, portfolio construction, risk, factor models, market microstructure, backtesting, machine learning, simulation, visualization and reproducibility in one Python package.

The design principle is simple: **make quantitative workflows concise without hiding assumptions that materially change the result.**

> **Current release: 1.2.0.** The 1.0.0 paper contract and the 1.1.0 Research Discovery / Interest Rates capabilities are preserved. Version 1.2.0 adds a structured public API, data-driven hypothesis discovery, cross-sectional alpha research, portfolio risk analytics, factor research, market microstructure tools and stronger end-to-end validation. Guarded live-broker components remain fail-closed and require deployment-specific authorization.

## Documentation & official notebook

- **Official documentation:** <https://docs.asr-lab.online/asrquant/>
- **Documentation source:** [`docs/index.md`](docs/index.md)
- **MkDocs configuration:** [`mkdocs.yml`](mkdocs.yml)
- **ASRQuant 1.2.0 quickstart notebook:** [`notebooks/ASRQuant_v1.2.0_Quickstart.ipynb`](notebooks/ASRQuant_v1.2.0_Quickstart.ipynb)
- **Documentation deployment:** GitHub Pages workflow in [`.github/workflows/docs.yml`](.github/workflows/docs.yml)

Run the documentation locally:

```bash
python -m pip install -e ".[docs]"
mkdocs serve
```

## Install

```bash
pip install asrquant
```

Upgrade:

```bash
pip install --upgrade asrquant
```

Optional research dependencies:

```bash
pip install "asrquant[data]"          # Yahoo Finance, Excel, Parquet, Feather
pip install "asrquant[ml]"            # SHAP, HMM extensions
pip install "asrquant[optimization]"  # CVXPY extensions
pip install "asrquant[volatility]"    # ARCH / GARCH
pip install "asrquant[all]"
```

ASRQuant supports Python **3.10–3.13**.

## One import

```python
import asrquant as asr

print(asr.__version__)
# 1.2.0
```

The recommended public namespaces are intentionally predictable:

```text
asr.data           data ingestion, validation and providers
asr.hypotheses     data/literature hypothesis discovery and novelty audit
asr.alpha          cross-sectional signal research
asr.factors        PCA, exposures and factor-risk decomposition
asr.risk           VaR, ES, scenario and portfolio risk
asr.microstructure spread, microprice, OFI, Kyle lambda and liquidity analytics
asr.backtesting    auditable backtesting
asr.portfolio      optimization and covariance estimation
asr.stats          econometrics, bootstrap and inference
asr.ml             leakage-aware walk-forward ML
asr.options        derivative pricing and Greeks
asr.rates          fixed income and interest-rate derivatives
asr.stochastic     stochastic processes
asr.mc             universal Monte Carlo
asr.vol            volatility modelling
asr.visuals        visualization catalogue
asr.research       reproducible research workflow
asr.trading        paper trading and guarded execution primitives
```

Legacy 1.x entry points remain available for existing notebooks.

---

# Canonical 1.2 API

The high-level verbs are designed to be memorable:

```python
asr.data.load(...)
asr.data.validate(...)
asr.hypotheses.discover(...)
asr.backtesting.run(...)
asr.portfolio.optimize(...)
asr.options.price(...)
asr.rates.analyze(...)
asr.rates.calibrate(...)
asr.stats.regress(...)
asr.ml.fit(...)
```

Structured result objects expose consistent analysis helpers where applicable:

```python
result.summary
result.to_frame()
result.to_dict()
```

---

# Data

ASRQuant 1.2 uses one data layer for local files, public URLs and provider-backed market data.

## CSV / local file

```python
prices = asr.data.load(
    "prices.csv",
    date_column="Date",
)
```

Supported local formats include CSV, Parquet, Excel, JSON and Feather.

## Public CSV URL

```python
macro = asr.data.load(
    "https://example.org/data.csv",
    date_column="DATE",
)
```

Remote reads use an explicit bounded HTTP request and preserve the same tabular contract.

## Yahoo Finance

Install the data extra first:

```bash
pip install "asrquant[data]"
```

Then:

```python
prices = asr.data.yahoo(
    ["SPY", "TLT", "GLD"],
    start="2020-01-01",
)
```

or through the generic loader:

```python
prices = asr.data.load(
    "yahoo",
    symbols=["SPY", "TLT"],
    start="2020-01-01",
)
```

## ECB yield-curve data

```python
curve_history = asr.data.ecb_yield_curve(
    maturities=["3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"],
    start="2020-01-01",
)
```

The ECB connector uses the ECB Data Portal SDMX REST service and returns decimal annual rates. The generic `ECBProvider` remains available for arbitrary ECB series keys.

## Other providers

```python
fred = asr.data.from_provider("fred", "DGS10", field="Value")
btc = asr.data.from_provider("binance", "BTCUSDT", field="Close", interval="1d")
```

Provider adapters currently include ECB, Yahoo Finance, FRED, Binance and Alpha Vantage.

## Validate before research

```python
quality = asr.data.validate(prices)
print(quality.summary)
print(quality.issues)
```

Validation reports duplicates, missing values, infinities, non-numeric values, constant columns, index ordering and sampling gaps without silently changing the input.

---

# Hypothesis discovery

ASRQuant does not treat a statistically interesting pattern as scientific novelty. Version 1.2 separates **data evidence** from **novelty evidence**.

## From data

```python
ideas = asr.hypotheses.from_data(
    data,
    domain="fixed_income",
    targets="target",
    horizons=(1, 5, 20),
)

ideas.to_frame()
```

The discovery layer can screen chronology-safe candidate relationships, lagged effects, regime changes, structural breaks, cointegration and other research observations. Multiple-testing controls and holdout evidence are tracked explicitly.

## From literature

```python
corpus = asr.LiteratureCorpus.from_pdfs("papers/")
ideas = asr.hypotheses.from_literature(
    corpus,
    topic="interest-rate derivatives",
)
```

Source excerpts retain paper/page provenance.

## Combine data + papers + model disagreement + robustness

```python
ideas = asr.hypotheses.discover(
    data=data,
    papers=corpus,
    predictions=model_predictions,
    robustness_results=robustness_grid,
    robustness_metric="sharpe",
    domain="fixed_income",
)
```

## Search and novelty audit

```python
matches = asr.hypotheses.search(
    "Forward-curve instability precedes rate-regime changes",
    hypotheses=ideas,
    papers=corpus,
)

audit = asr.hypotheses.audit(ideas[0], corpus=corpus)
print(audit.novelty_status)
```

A corpus-relative gap is **not** a claim of global novelty. The public statuses are intentionally conservative.

## Start a research project

```python
project = ideas[0].start()
```

That hands the selected hypothesis to the existing reproducible `ResearchProject` workflow.

---

# Cross-sectional alpha research

```python
signal = prices.pct_change(20, fill_method=None).shift(1)
signal = asr.alpha.cross_sectional_zscore(signal)

future = asr.alpha.forward_returns(prices, periods=(1, 5, 20))
report = asr.alpha.analyze_signal(
    signal,
    future[5],
    quantiles=5,
)

print(report.summary)
```

The alpha layer includes:

- cross-sectional winsorization, ranking and z-scores;
- signal neutralization against exposures;
- forward returns;
- Pearson/Spearman Information Coefficient;
- IC decay;
- quantile portfolios and long-short spreads;
- signal-to-weight conversion;
- turnover diagnostics.

---

# Factor research

## PCA factors

```python
pca = asr.factors.pca(returns, n_components=3)
print(pca.explained_variance_ratio)
print(pca.loadings)
```

## Time-series factor exposures

```python
exposure = asr.factors.exposures(
    asset_returns,
    factor_returns,
    covariance="HAC",
)

print(exposure.to_frame())
```

## Factor-risk decomposition

```python
risk = asr.factors.risk_decomposition(
    weights,
    betas,
    factor_covariance,
    specific_variance,
)

print(risk.summary)
```

---

# Portfolio risk

```python
risk = asr.risk.portfolio_risk_report(
    returns,
    weights,
    level=0.99,
)

print(risk.summary)
```

Available analytics include:

- historical, Gaussian and Cornish-Fisher VaR;
- Expected Shortfall;
- rolling VaR;
- covariance / Euler risk contribution;
- Expected Shortfall contribution;
- scenario P&L;
- volatility and exposure diagnostics.

---

# Market microstructure

```python
micro = asr.microstructure.microprice(
    bid,
    ask,
    bid_size,
    ask_size,
)

ofi = asr.microstructure.order_flow_imbalance(
    bid,
    ask,
    bid_size,
    ask_size,
)
```

The microstructure namespace includes quoted, effective and realized spreads, microprice, price impact, order-flow imbalance, Amihud illiquidity, Roll spread and Kyle lambda.

---

# Portfolio construction

```python
result = asr.portfolio.optimize(
    returns,
    method="maximum_sharpe",
    covariance_method="ledoit_wolf",
)

print(result.weights)
print(result.summary)
```

Supported allocation methods include:

- minimum variance;
- maximum Sharpe;
- equal risk contribution / risk parity;
- maximum diversification;
- hierarchical risk parity;
- efficient frontier;
- Black-Litterman utilities.

Covariance estimators include sample, EWMA, Ledoit-Wolf and OAS.

---

# Backtesting

```python
spec = asr.BacktestSpec(
    execution_delay=1,
    costs=asr.CostModel(
        commission_bps=1,
        spread_bps=2,
        slippage_bps=1,
    ),
)

result = asr.backtesting.run(
    prices,
    target_weights,
    spec=spec,
)

print(result.summary)
result.report("report.html")
```

The engine tracks target/effective weights, transaction costs, borrow cost, turnover, equity, trades and experiment fingerprints.

---

# Statistics and econometrics

```python
fit = asr.stats.regress(
    y,
    x,
    method="ols",
    covariance="HAC",
)
```

The statistics layer includes OLS, quantile regression, factor regression, polynomial regression, logistic regression, Ridge/Lasso/Elastic Net, stationarity tests, block bootstrap, permutation tests, Benjamini-Hochberg FDR, cointegration, Granger causality, ARIMA, VAR and autoregression utilities.

---

# Machine learning

```python
result = asr.ml.fit(
    "ridge",
    features,
    target,
    train_size=504,
    test_size=63,
    gap=5,
    task="regression",
)

print(result.summary)
```

Walk-forward splits are chronological and estimators are re-fitted per fold. ASRQuant does not randomly shuffle time-series observations in this workflow.

---

# Fixed income & interest-rate derivatives

ASRQuant contains a dedicated interest-rate research stack for:

- day-count conventions and schedules;
- discount factors, zero rates and forward rates;
- discount and projection curves;
- multi-curve construction;
- Nelson-Siegel and Svensson calibration;
- bonds, FRAs, futures, swaps and basis swaps;
- OIS / overnight compounding;
- DV01, key-rate DV01 and convexity;
- caps, floors, caplets and swaptions;
- Black-76, Bachelier and SABR volatility;
- Vasicek, CIR, Hull-White, Ho-Lee and Black-Karasinski;
- HJM and LMM simulation;
- PCA / level-slope-curvature analysis;
- carry and roll-down;
- curve interpolation risk and no-arbitrage diagnostics;
- key-rate hedging and rate scenarios;
- Bermudan LSM building blocks.

Example:

```python
curve = asr.rates.DiscountCurve.from_zero_rates(
    maturities=[0.5, 1, 2, 5, 10],
    zero_rates=[0.025, 0.027, 0.029, 0.032, 0.034],
)

analysis = asr.rates.analyze(curve)
print(analysis.summary)
```

---

# Derivatives

```python
price = asr.options.price(
    "black_scholes",
    spot=100,
    strike=100,
    maturity=1.0,
    rate=0.03,
    volatility=0.20,
)

print(price.summary)
```

Pricing tools include Black-Scholes-Merton, Black-76, Bachelier, CRR trees, Monte Carlo and implied-volatility inversion.

---

# Simulation and Monte Carlo

```python
paths = asr.stochastic.simulate(
    "heston",
    steps=252,
    paths=10_000,
    random_state=7,
)
```

Supported process families include ABM, GBM, OU, CIR, Vasicek, Heston, Merton jump diffusion and regime-switching processes.

The universal Monte Carlo layer supports custom generators, estimators, empirical quantiles, confidence intervals, expected shortfall, path-dependent losses, parameter surfaces and animations.

---

# Research workflow

ASRQuant can connect the full chain:

```text
Evidence / Data
      ↓
Observation
      ↓
Research Question
      ↓
Hypothesis
      ↓
Data Plan
      ↓
Features / Model / Signal
      ↓
Backtest / Experiment
      ↓
Robustness & Falsification
      ↓
Decision
      ↓
Research Note / Publication Pack
```

The existing `ResearchProject`, `ResearchBoard` and `WeeklyResearchCycle` APIs remain available.

---

# Guarded trading and production readiness

ASRQuant includes paper-broker objects, risk policies, audit storage, reconciliation and guarded live-broker primitives. These are deliberately separated from research validity.

Installing the package **does not authorize live capital deployment**. Live components require explicit deployment evidence, a matching certificate and risk-policy gates.

---

# End-to-end example

```python
import asrquant as asr

# 1. Data
prices = asr.data.yahoo(["SPY", "TLT", "GLD"], start="2018-01-01")
quality = asr.data.validate(prices)

# 2. Returns
returns = prices.pct_change(fill_method=None).dropna()

# 3. Factors
pca = asr.factors.pca(returns, n_components=2)

# 4. Portfolio
portfolio = asr.portfolio.optimize(
    returns,
    method="maximum_sharpe",
    covariance_method="ledoit_wolf",
)

# 5. Risk
risk = asr.risk.portfolio_risk_report(
    returns,
    portfolio.weights,
    level=0.99,
)

print(portfolio.summary)
print(risk.summary)
```

For research projects, replace step 2 with `asr.hypotheses.discover(...)` and hand the selected candidate to `candidate.start()`.

---

# Reproducibility rules

ASRQuant is opinionated about research hygiene:

- preserve source/provenance metadata;
- make missing-data policy explicit;
- separate signal time from execution time;
- model costs explicitly;
- use chronological validation for time series;
- correct for multiple testing when exploring many hypotheses;
- separate in-sample evidence from holdout evidence;
- separate data support from scientific novelty;
- save configuration and experiment fingerprints;
- never infer live-deployment authorization from package installation.

---

# Development

```bash
git clone https://github.com/Alpha-Stochastic-Research/asr-quant.git
cd asr-quant

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,all]"
```

Run the full domain suite:

```bash
python scripts/test_all.py --group all
```

Run the 1.2 integration suite:

```bash
pytest -q \
  tests/test_api_consistency_v120.py \
  tests/test_data_sources_v120.py \
  tests/test_hypotheses_v120.py \
  tests/test_alpha_v120.py \
  tests/test_factors_v120.py \
  tests/test_risk_v120.py \
  tests/test_microstructure_v120.py \
  tests/test_end_to_end_v120.py
```

Build distributions:

```bash
python -m build
python -m twine check --strict dist/*
```

---

# Repository structure

```text
src/asrquant/
├── api.py                  QuantLab high-level API
├── data.py                 data loading / validation
├── providers.py            ECB, Yahoo, FRED, Binance, Alpha Vantage
├── hypotheses.py           hypothesis discovery / search / audit
├── discovery.py            research-candidate discovery board
├── workflow.py             research project workflow
├── alpha.py                cross-sectional alpha research
├── factors.py              PCA / factor exposures / factor risk
├── risk.py                 portfolio risk and scenarios
├── microstructure.py       execution / liquidity analytics
├── backtest.py             auditable backtesting
├── optimization.py         portfolio construction
├── statistics.py           econometrics / inference
├── machine_learning.py     walk-forward ML
├── derivatives.py          option pricing
├── interest_rates.py       fixed income / interest-rate derivatives
├── simulation.py           stochastic processes
├── monte_carlo.py          generic Monte Carlo engine
├── volatility.py           volatility models
├── trading.py              paper trading
├── production.py           readiness gates
├── live.py                 guarded broker execution
├── audit_store.py          durable audit log
└── viz/                    visualization catalogue
```

The package keeps domain modules explicit rather than hiding quantitative logic behind a monolithic object hierarchy.

---

# Project links

- Website: https://www.asr-lab.online
- Repository: https://github.com/Alpha-Stochastic-Research/asr-quant
- Issues: https://github.com/Alpha-Stochastic-Research/asr-quant/issues

# Citation

See `CITATION.cff` and the accompanying ASRQuant paper in `paper/`.

# License

MIT License. See `LICENSE`.

# Disclaimer

ASRQuant is research software. It is not investment advice, a brokerage service, or a guarantee that a model, strategy, backtest or hypothesis is economically valid. Users remain responsible for data licenses, model validation, operational controls and applicable regulation.
