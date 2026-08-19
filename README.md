# ASRQuant

**Auditable quantitative finance research in Python.**

ASRQuant is an open-source Python toolkit developed by **Alpha Stochastic Research (ASR)** for building clear, reproducible and reviewable quantitative-finance workflows.

It brings market data, research design, statistics, machine learning, stochastic simulation, derivatives, fixed income, portfolio analytics, backtesting, visualization and controlled execution into one public interface:

```python
import asrquant as asr
```

The goal is not to hide quantitative assumptions behind a black box. ASRQuant is designed to make the important choices — data, chronology, costs, model parameters, risk limits and experiment specifications — explicit and auditable.

[PyPI](https://pypi.org/project/asrquant/) · [Documentation](docs/) · [Changelog](CHANGELOG.md) · [License](LICENSE)

---

## Installation

ASRQuant requires **Python 3.10+**.

### Install

```bash
pip install asrquant
```

### Upgrade

```bash
pip install --upgrade asrquant
```

### Install all optional research dependencies

```bash
pip install "asrquant[all]"
```

Available optional groups:

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

Or from the terminal:

```bash
asrquant --version
```

---

## 60-second quick start

A standard ASRQuant workflow can begin with a CSV and end with an auditable backtest and report:

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)

asr.save(result, "equity.png", kind="equity")
asr.report(result, "report.html")
```

A `BacktestResult` keeps the information needed to inspect the experiment rather than returning only a chart. This includes strategy returns, equity, turnover, modeled costs, metrics, execution information and reproducibility fingerprints.

---

## What ASRQuant covers

ASRQuant is organized by **research task**, not by backend library.

| Area | Main interface | Typical use |
|---|---|---|
| Research workflows | `asr.research`, `asr.discovery` | Literature, hypotheses, research candidates, reproducible research cycles |
| Data | `asr.open_lab`, `asr.read_table`, `asr.download` | Load, clean, validate and prepare market or macro data |
| Backtesting | `lab.backtest`, `asr.run_backtest` | Strategy testing with chronology, turnover and transaction costs |
| Fixed income & rates | `asr.rates`, `asr.RateQuantLab` | Curves, bonds, FRAs, swaps, OIS, caps/floors, swaptions, SABR, short-rate models and rate risk |
| Derivatives | `asr.options` | Black-Scholes, Bachelier, Black-76, binomial pricing, Greeks and implied volatility |
| Stochastic simulation | `asr.stochastic`, `asr.mc` | GBM, Heston, jump diffusion, CIR, Vasicek, Monte Carlo and SDE experiments |
| Statistics | `asr.stats` | Regression, econometrics, bootstrap and statistical testing |
| Machine learning | `asr.models`, `lab.ml` | Walk-forward ML, feature engineering and model evaluation |
| Portfolio analytics | `asr.portfolio` | Allocation, covariance, optimization and portfolio research |
| Volatility | `asr.vol` | Realized, Parkinson, Garman-Klass, EWMA and GARCH volatility |
| Visualization | `asr.visualize`, `asr.show`, `asr.save`, `asr.visuals` | Research figures, surfaces, dashboards and diagnostics |
| Reporting & provenance | `asr.report`, `asr.build_manifest` | Reproducible reports and experiment provenance |
| Trading controls | `asr.trading` | Paper trading, risk policies, readiness checks and guarded broker execution |

---

## One-import API

The recommended usage pattern is:

```python
import asrquant as asr
```

From that single import, the main namespaces are available directly:

```text
asr.models       machine-learning model factory
asr.math         numerical helpers
asr.stats        statistics and econometrics
asr.portfolio    portfolio analytics and optimization
asr.options      derivative pricing
asr.stochastic   stochastic processes and simulation
asr.mc           Monte Carlo utilities
asr.rates        fixed-income and interest-rate analytics
asr.vol          volatility analytics
asr.research     research workflows
asr.discovery    research discovery
asr.trading      paper and controlled execution tools
asr.visuals      visualization catalog
```

NumPy, pandas, SciPy, Matplotlib, Plotly, statsmodels and scikit-learn are used internally where appropriate. ASRQuant owns the public workflow, validation, result objects, plotting interface and reproducibility contract.

---

## Example: backtesting

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")

result = lab.backtest(
    "momentum",
    lookback=126,
    costs_bps=5,
)

print(result.metrics)
asr.save(result, "dashboard.png", kind="dashboard")
asr.report(result, "backtest-report.html")
```

For more control, use `BacktestSpec` and `CostModel` explicitly.

The backtesting layer is built around explicit chronology, position construction, turnover, execution delay, missing-data rules, leverage constraints and modeled costs.

---

## Example: fixed income and interest rates

The rates stack can be used through the high-level `RateQuantLab` interface:

```python
import asrquant as asr

rates = asr.RateQuantLab.from_zero_rates(
    [0.5, 1.0, 2.0, 5.0, 10.0],
    [0.020, 0.021, 0.023, 0.028, 0.030],
)

print(rates.par_swap(0.0, 5.0))
print(rates.diagnostics())
```

Or through the lower-level rates API:

```python
curve = asr.rates.DiscountCurve.from_zero_rates(
    [0.5, 1.0, 2.0, 5.0, 10.0],
    [0.020, 0.021, 0.023, 0.028, 0.030],
)

forward = curve.forward_rate(2.0, 3.0, "continuous")
par_rate = asr.rates.swap_par_rate(curve, 0.0, 5.0)
```

The interest-rate stack includes:

- discount and zero curves;
- forward and projection curves;
- single-curve and multi-curve construction;
- bonds, accrued interest, clean/dirty prices, duration, convexity and DV01;
- FRAs, swaps, OIS and basis swaps;
- rate futures;
- caps, floors and swaptions;
- implied rate volatility and caplet-volatility stripping;
- SABR calibration;
- Vasicek, CIR, Hull-White, Ho-Lee and Black-Karasinski models;
- HJM and LMM simulation;
- yield-curve PCA and level/slope/curvature factors;
- curve scenarios, carry/roll-down and interpolation risk;
- key-rate DV01 and hedge construction;
- inflation, FX-forward and cross-currency building blocks.

---

## Example: research discovery

ASRQuant can also start **before** a final hypothesis has been selected.

```python
import asrquant as asr

board = asr.discovery.weekly(
    data=curve_history,
    domain="fixed_income",
    n=10,
)

print(board.to_frame())
project = board.start(0)
```

The discovery layer is designed to produce research candidates from explicit evidence while keeping novelty and publication claims reviewable by humans.

For the full research workflow, see [`docs/research_discovery.md`](docs/research_discovery.md) and [`docs/research_workflow.md`](docs/research_workflow.md).

---

## Core design principles

### 1. Explicit assumptions

Important model, execution and data choices should be visible in code and stored with the result.

### 2. Chronology first

Time-series workflows are designed to preserve temporal ordering and reduce accidental look-ahead bias.

### 3. Reproducible experiments

Results can carry data, specification and experiment fingerprints so that the research path can be reviewed later.

### 4. Auditable outputs

A figure is not the experiment. Important outputs expose the underlying data, parameters, metrics and diagnostics.

### 5. High-level API, inspectable internals

ASRQuant aims to make common workflows concise without preventing advanced users from inspecting lower-level objects.

### 6. Fail-closed live execution

Installing ASRQuant does **not** authorize capital deployment. Live-broker components require explicit risk, deployment and environment controls.

---

## Research, paper trading and live execution are different stages

ASRQuant deliberately separates:

1. **Research** — data, modelling, testing and robustness;
2. **Paper execution** — validation of the execution path without live capital;
3. **Live authorization** — deployment-specific approval, risk limits, broker configuration and operational controls.

The live stack includes production-readiness checks, signed deployment certificates, persistent kill-switch controls, pre-trade risk checks, reconciliation and durable audit logging.

Start with paper execution. Read the operational documentation before connecting a broker:

- [`docs/production_readiness.md`](docs/production_readiness.md)
- [`docs/live_trading.md`](docs/live_trading.md)
- [`docs/operations_runbook.md`](docs/operations_runbook.md)
- [`docs/regulatory_controls.md`](docs/regulatory_controls.md)

---

## Data providers

ASRQuant includes provider interfaces for research workflows, including:

- Yahoo Finance;
- FRED;
- ECB;
- Alpha Vantage;
- Binance.

Provider availability, credentials, rate limits and data licenses remain provider-specific.

See [`docs/data_sources.md`](docs/data_sources.md).

---

## Reproducibility checklist

For serious research, keep these choices explicit:

- source and version of the data;
- cleaning and missing-data policy;
- signal timing;
- execution delay;
- transaction-cost assumptions;
- rebalance frequency;
- leverage and position limits;
- train/test chronology;
- random seeds;
- parameter search space;
- benchmark definition;
- robustness and stress tests.

ASRQuant provides infrastructure for these controls, but the researcher remains responsible for the economic and statistical validity of the experiment.

---

## Development

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/Alpha-Stochastic-Research/asr-quant.git
cd asr-quant
pip install -e ".[dev]"
```

Run the project test suite:

```bash
python scripts/test_all.py
```

Useful project files:

- [`CHANGELOG.md`](CHANGELOG.md) — release history;
- [`docs/`](docs/) — detailed documentation;
- [`tests/`](tests/) — tested behavior and API contracts;
- [`pyproject.toml`](pyproject.toml) — package metadata and dependency groups.

---

## License

ASRQuant is released under the **MIT License**. See [`LICENSE`](LICENSE).

---

## Disclaimer

ASRQuant is research software for quantitative-finance experimentation, education and controlled engineering workflows. It is **not financial advice**, does not guarantee the validity or profitability of a strategy, and does not replace independent model validation, broker controls, legal review, regulatory obligations or accountable human oversight.

---

**Alpha Stochastic Research — Research · Modelling · Analysis · Impact**
