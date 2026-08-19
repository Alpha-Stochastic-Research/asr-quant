<div align="center">

# ASRQuant

### Auditable quantitative finance research in Python

**From scientific literature and economic hypotheses to auditable quantitative decisions, guarded broker execution, and production-readiness controls in Python.**

<br>

[![PyPI](https://img.shields.io/pypi/v/asrquant?label=PyPI&logo=pypi&logoColor=white)](https://pypi.org/project/asrquant/)
[![Python](https://img.shields.io/pypi/pyversions/asrquant?label=Python&logo=python&logoColor=white)](https://pypi.org/project/asrquant/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Research](https://img.shields.io/badge/Focus-Quantitative%20Finance-0A66C2)](https://www.asr-lab.online)

[**Install**](#installation) ·
[**Quick Start**](#quick-start) ·
[**Capabilities**](#capabilities) ·
[**Fixed Income & Rates**](#fixed-income--interest-rates) ·
[**Research Workflow**](#research-workflow) ·
[**Documentation**](docs/)

</div>

---

## Overview

**ASRQuant** is an open-source quantitative-finance research package developed by **Alpha Stochastic Research (ASR)**.

It provides a compact, explicit and reproducible interface for:

- scientific-paper ingestion and source-linked research;
- hypothesis discovery and research design;
- market-data preparation;
- feature and signal construction;
- econometrics and machine learning;
- stochastic simulation and Monte Carlo;
- derivative pricing;
- fixed-income and interest-rate modelling;
- portfolio analytics;
- backtesting and robustness analysis;
- visualization and reporting;
- paper trading;
- production-readiness controls;
- tamper-evident audit trails;
- explicitly authorized broker execution.

The objective is simple:

> **Workflows that normally require many notebooks, formulas, plotting scripts and validation steps should be expressible in a few readable lines — without hiding the assumptions that materially affect the result.**

### Release status

> **ASRQuant 1.1.0 — stable public API**
>
> The 1.0.0 paper contract remains preserved. Version 1.1.0 adds the Research Discovery / Weekly Research operating layer and a comprehensive interest-rate research stack.
>
> Guarded live-broker primitives remain **fail-closed** and require deployment-specific authorization. Installing the package does not authorize live capital deployment.

ASRQuant is research software. It is **not financial advice** and is not an HFT exchange gateway.

---

## Installation

ASRQuant requires **Python 3.10+**.

### Install from PyPI

```bash
pip install asrquant
```

### Upgrade to the latest release

```bash
pip install --upgrade asrquant
```

### Install all optional research dependencies

```bash
pip install "asrquant[all]"
```

### Optional dependency groups

| Extra | Purpose |
|---|---|
| `data` | Yahoo Finance, Excel, Parquet and Feather support |
| `volatility` | GARCH models |
| `optimization` | CVXPY-backed optimization |
| `ml` | SHAP and hidden-Markov-model extensions |
| `all` | All optional research dependencies |
| `docs` | Documentation toolchain |
| `dev` | Development and testing tools |

### Verify the installation

```python
import asrquant as asr

print(asr.__version__)
```

Or:

```bash
asrquant --version
```

---

## Quick Start

### Five-line workflow

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
asr.save(result, "dashboard.png", kind="dashboard")
asr.report(result, "report.html")
```

A `BacktestResult` keeps the information required to inspect the experiment rather than returning only a chart.

It includes:

- validated prices and asset returns;
- target and effective weights;
- gross and net strategy returns;
- equity curve;
- turnover;
- aggregate and decomposed costs;
- strategy metrics;
- transaction ledger;
- immutable backtest specification;
- data, specification and experiment fingerprints;
- plotting and HTML-report helpers.

---

## One-import API

The recommended public interface is:

```python
import asrquant as asr
```

The main namespaces are available directly from that import:

| Namespace | Purpose |
|---|---|
| `asr.models` | Machine-learning models |
| `asr.math` | Numerical helpers |
| `asr.stats` | Statistics and econometrics |
| `asr.portfolio` | Portfolio analytics and optimization |
| `asr.options` | Derivative pricing and Greeks |
| `asr.stochastic` | Stochastic processes and simulation |
| `asr.mc` | Monte Carlo utilities |
| `asr.rates` | Fixed-income and interest-rate analytics |
| `asr.vol` | Volatility analytics |
| `asr.research` | Research workflows |
| `asr.discovery` | Research discovery |
| `asr.trading` | Paper and controlled execution |
| `asr.visuals` | Visualization catalog |

ASRQuant uses mature scientific libraries internally, including NumPy, pandas, SciPy, Matplotlib, Plotly, statsmodels and scikit-learn.

The user-facing API, validation rules, result objects, visualization interface and reproducibility contract remain owned by ASRQuant.

---

## Capabilities

### Research & Discovery

From literature and evidence to structured research candidates.

```python
board = asr.discovery.weekly(
    data=curve_history,
    domain="fixed_income",
    n=10,
)

print(board.to_frame())
project = board.start(0)
```

Use this layer for:

- literature-driven research;
- hypothesis discovery;
- research-candidate ranking;
- evidence tracking;
- Weekly Research cycles;
- reproducible project structure.

---

### Market Data

```python
lab = asr.open_lab("prices.csv", date_column="Date")
```

ASRQuant supports workflows around:

- tabular market data;
- macroeconomic data;
- OHLCV preparation;
- cleaning and quality checks;
- returns;
- resampling;
- fingerprints and provenance.

Provider interfaces include:

- Yahoo Finance;
- FRED;
- ECB;
- Alpha Vantage;
- Binance.

See [`docs/data_sources.md`](docs/data_sources.md).

---

### Backtesting

```python
result = lab.backtest(
    "momentum",
    lookback=126,
    costs_bps=5,
)
```

The backtesting layer is designed around explicit:

- signal timing;
- execution delay;
- transaction costs;
- turnover;
- rebalance frequency;
- missing-data policy;
- leverage;
- position construction;
- chronology.

---

### Statistics & Econometrics

Use:

```python
asr.stats
```

for research workflows involving:

- regression;
- autoregression;
- bootstrap;
- statistical tests;
- econometric diagnostics;
- time-series analysis.

---

### Machine Learning

```python
model = asr.models.random_forest(
    task="regression",
    trees=500,
    depth=6,
    seed=7,
)

result = lab.ml(
    model,
    train_size=504,
    test_size=63,
    gap=5,
)
```

The ML layer is designed for time-aware experimentation and walk-forward evaluation.

---

### Stochastic Simulation & Monte Carlo

Use:

```python
asr.stochastic
asr.mc
```

Available building blocks include:

- arithmetic Brownian motion;
- geometric Brownian motion;
- correlated GBM;
- Ornstein-Uhlenbeck;
- CIR;
- Vasicek;
- Heston;
- Merton jump diffusion;
- regime-switching prices;
- Euler-Maruyama;
- Monte Carlo confidence intervals;
- VaR and Expected Shortfall;
- parameter surfaces.

---

### Derivatives

Use:

```python
asr.options
```

The derivative-pricing stack includes:

- Black-Scholes;
- Bachelier;
- Black-76;
- CRR binomial pricing;
- Greeks;
- implied volatility;
- Monte Carlo pricing.

---

## Fixed Income & Interest Rates

Fixed income and interest-rate modelling are first-class components of ASRQuant.

### High-level rates interface

```python
import asrquant as asr

rates = asr.RateQuantLab.from_zero_rates(
    [0.5, 1.0, 2.0, 5.0, 10.0],
    [0.020, 0.021, 0.023, 0.028, 0.030],
)

print(rates.par_swap(0.0, 5.0))
print(rates.diagnostics())
```

### Discount curve

```python
curve = asr.rates.DiscountCurve.from_zero_rates(
    [0.5, 1.0, 2.0, 5.0, 10.0],
    [0.020, 0.021, 0.023, 0.028, 0.030],
)
```

### Forward rate

```python
forward = curve.forward_rate(
    2.0,
    3.0,
    "continuous",
)
```

### Par swap rate

```python
par_rate = asr.rates.swap_par_rate(
    curve,
    0.0,
    5.0,
)
```

### Interest-rate research stack

| Area | Coverage |
|---|---|
| Curves | Discount, zero, forward and projection curves |
| Construction | Deposit, FRA and swap bootstrapping |
| Multi-curve | Discounting and projection-curve workflows |
| Bonds | Price, accrued interest, clean/dirty price, duration, convexity |
| Risk | DV01, dollar convexity, key-rate DV01 |
| FRAs | Forward rates and valuation |
| Swaps | Par rate, PV, annuity, DV01 |
| OIS | Overnight compounding, par rates and valuation |
| Basis | Basis-swap valuation |
| Futures | Rate ↔ futures-price conversion |
| Caps/Floors | Caplets, floorlets, caps and floors |
| Swaptions | Payer and receiver swaption pricing |
| Volatility | Implied rate volatility and caplet-vol stripping |
| SABR | Hagan approximation and calibration |
| Short-rate models | Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski |
| HJM / LMM | Forward-rate simulation |
| Curve factors | PCA, level, slope and curvature |
| Curve risk | Interpolation risk, scenarios, carry and roll-down |
| Hedging | Key-rate hedge construction |
| Cross-market | FX forwards, inflation and cross-currency building blocks |
| Parametric curves | Nelson-Siegel and Svensson calibration |

---

## Portfolio Analytics

Use:

```python
asr.portfolio
```

for:

- covariance estimation;
- allocation;
- portfolio construction;
- optimization;
- risk-aware portfolio research.

---

## Volatility

Use:

```python
asr.vol
```

Available estimators and forecasting tools include:

- realized volatility;
- Parkinson volatility;
- Garman-Klass volatility;
- EWMA;
- GARCH.

---

## Visualization

ASRQuant exposes a backend-neutral visualization layer:

```python
asr.visualize(...)
asr.show(...)
asr.save(...)
```

Examples:

```python
asr.save(result, "equity.png", kind="equity")
asr.save(result, "dashboard.png", kind="dashboard")
```

For advanced visualization helpers:

```python
asr.visuals
```

---

## Research Workflow

ASRQuant is designed to connect the stages of quantitative research instead of treating them as unrelated scripts.

```text
Literature / Evidence
        ↓
Hypothesis
        ↓
Data Plan
        ↓
Features
        ↓
Signals
        ↓
Econometric / ML Tests
        ↓
Portfolio Construction
        ↓
Backtest
        ↓
Robustness
        ↓
Decision
        ↓
Paper Execution
```

The full research layer includes:

- `ResearchProject`;
- `EconomicHypothesis`;
- `DataPlan`;
- `FeaturePlan`;
- `SignalSpec`;
- `PortfolioSpec`;
- hypothesis tests;
- robustness results;
- decision results;
- literature provenance;
- research discovery.

See [`docs/research_workflow.md`](docs/research_workflow.md).

---

## Weekly Research

ASRQuant can start before a final research hypothesis exists.

```python
board = asr.discovery.weekly(
    data=curve_history,
    domain="fixed_income",
    n=10,
)

project = board.start(0)

cycle = asr.weekly_cycle(
    board,
    0,
    launch_friday="2026-08-14",
)

cycle.publication_pack("WR-001")
```

The discovery engine converts transparent evidence into ranked research candidates.

Automated candidates do **not** receive an automatic novelty claim.

See:

- [`docs/research_discovery.md`](docs/research_discovery.md)
- [`docs/team_research_operating_model.md`](docs/team_research_operating_model.md)

---

## Reproducibility & Audit

A serious quantitative experiment should make its assumptions inspectable.

ASRQuant provides tools for:

- data fingerprints;
- experiment fingerprints;
- immutable specifications;
- manifests;
- implementation audits;
- validation;
- robustness testing;
- report generation;
- durable execution audit trails.

### Reproducibility checklist

Keep these choices explicit:

- source and version of the data;
- cleaning rules;
- missing-data policy;
- signal timing;
- execution delay;
- transaction-cost assumptions;
- rebalance frequency;
- leverage and position limits;
- train/test chronology;
- random seeds;
- parameter-search space;
- benchmark definition;
- robustness and stress tests.

---

## Paper Trading

Research validation and execution validation are separate concerns.

ASRQuant provides:

```python
asr.trading
```

for controlled paper-trading workflows.

The package separates three claims:

1. **Research-valid**  
   The model and backtest satisfy the chosen scientific checks.

2. **Broker-paper validated**  
   The execution path has been tested in a broker simulator over a defined observation period.

3. **Live-authorized**  
   A deployment certificate matches the exact release, broker account, risk policy, environment and maximum authorized capital.

---

## Production Readiness

Installing ASRQuant does **not** authorize live capital deployment.

The production layer includes:

- deployment evidence;
- readiness gates;
- signed deployment certificates;
- live risk policies;
- pre-trade checks;
- broker-health checks;
- persistent kill switch;
- reconciliation;
- durable audit logs.

Example:

```python
report = asr.ProductionReadinessGate().evaluate(evidence)

print(report.ready)
report.save("readiness-report.json")
```

Read before connecting a live broker:

- [`docs/production_readiness.md`](docs/production_readiness.md)
- [`docs/live_trading.md`](docs/live_trading.md)
- [`docs/operations_runbook.md`](docs/operations_runbook.md)
- [`docs/regulatory_controls.md`](docs/regulatory_controls.md)
- [`THREAT_MODEL.md`](THREAT_MODEL.md)

---

## Command Line Interface

Check the installed version:

```bash
asrquant --version
```

Run a readiness check:

```bash
asrquant readiness deployment-evidence.json --output readiness-report.json
```

Verify an execution audit chain:

```bash
asrquant verify-audit state/execution-audit.db
```

---

## Documentation

Detailed material lives in `docs/` so that this README remains readable.

| Topic | Document |
|---|---|
| Data sources | [`docs/data_sources.md`](docs/data_sources.md) |
| Research workflow | [`docs/research_workflow.md`](docs/research_workflow.md) |
| Research discovery | [`docs/research_discovery.md`](docs/research_discovery.md) |
| Production readiness | [`docs/production_readiness.md`](docs/production_readiness.md) |
| Live trading | [`docs/live_trading.md`](docs/live_trading.md) |
| Operations | [`docs/operations_runbook.md`](docs/operations_runbook.md) |
| Regulatory controls | [`docs/regulatory_controls.md`](docs/regulatory_controls.md) |

---

## Development

Clone the repository:

```bash
git clone https://github.com/Alpha-Stochastic-Research/asr-quant.git
cd asr-quant
```

Install the development environment:

```bash
pip install -e ".[dev]"
```

Run the full test suite:

```bash
python scripts/test_all.py
```

Useful project paths:

```text
src/asrquant/   package source
tests/          automated tests and API contracts
docs/           detailed documentation
paper/          ASRQuant paper
benchmarks/     validation and benchmark scripts
```

---

## Project Links

- **Website:** https://www.asr-lab.online
- **PyPI:** https://pypi.org/project/asrquant/
- **Repository:** https://github.com/Alpha-Stochastic-Research/asr-quant
- **Documentation:** [`docs/`](docs/)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)
- **Paper:** [`paper/ASRQuant_paper.pdf`](paper/ASRQuant_paper.pdf)
- **Issues:** https://github.com/Alpha-Stochastic-Research/asr-quant/issues

---

## Citation

If ASRQuant contributes materially to academic or research work, cite the software and the associated ASRQuant research paper where appropriate.

See the repository paper and release metadata for the current citation information.

---

## License

ASRQuant is released under the **MIT License**.

See [`LICENSE`](LICENSE).

---

## Disclaimer

ASRQuant is research software for quantitative-finance experimentation, education and controlled engineering workflows.

It does **not**:

- provide financial advice;
- guarantee the validity of a research hypothesis;
- guarantee the profitability of a strategy;
- replace independent model validation;
- replace broker safeguards;
- replace legal or regulatory review;
- authorize live capital deployment.

Live execution remains the responsibility of the deploying organization and accountable human operators.

---

<div align="center">

### Alpha Stochastic Research

**Research · Modelling · Analysis · Impact**

[Website](https://www.asr-lab.online) ·
[GitHub](https://github.com/Alpha-Stochastic-Research) ·
[PyPI](https://pypi.org/project/asrquant/)

</div>
