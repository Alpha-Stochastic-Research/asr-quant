<div align="center">

# ASRQuant

### Auditable quantitative finance research in Python

**Fixed Income · Derivatives · Backtesting · Risk · Validation · Reproducibility**

```bash
pip install --upgrade asrquant
```

[![PyPI](https://img.shields.io/pypi/v/asrquant?label=PyPI)](https://pypi.org/project/asrquant/)
[![Python](https://img.shields.io/pypi/pyversions/asrquant)](https://pypi.org/project/asrquant/)
[![License](https://img.shields.io/github/license/Alpha-Stochastic-Research/asr-quant)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Alpha-Stochastic-Research/asr-quant?style=flat)](https://github.com/Alpha-Stochastic-Research/asr-quant/stargazers)
[![Downloads](https://static.pepy.tech/badge/asrquant/month)](https://pepy.tech/project/asrquant)

[**Try the real-world notebook**](notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb) ·
[**Open in Colab**](https://colab.research.google.com/github/Alpha-Stochastic-Research/asr-quant/blob/main/notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb) ·
[**Documentation**](https://docs.asr-lab.online/) ·
[**PyPI**](https://pypi.org/project/asrquant/) ·
[**Paper**](paper/ASRQuant_paper.pdf)

</div>

---

ASRQuant is the open-source quantitative-finance toolkit developed by **Alpha Stochastic Research (ASR)** for building **reviewable, reproducible and auditable research workflows**.

It connects market data, hypothesis discovery, fixed income, derivatives, portfolio construction, risk, backtesting, simulation, machine learning, research validation and experiment lineage through one Python package.

The design principle is simple:

> **Make quantitative workflows concise without hiding assumptions that materially change the result.**

## Start with a real case

Instead of learning ASRQuant as a catalogue of functions, start with the public practical notebook:

### ECB EUR curve → 5Y IRS → risk → validation → audit trail

The notebook walks through one coherent rates workflow:

1. retrieve public ECB EUR yield-curve data;
2. validate and freeze the dataset with a fingerprint;
3. analyse curve dynamics with PCA;
4. build explicit curve states and market conventions;
5. price an illustrative 5Y payer IRS;
6. compute DV01, key-rate DV01 and quote-space PV01;
7. explain realized P&L;
8. run parallel / steepener / flattener stresses;
9. test a curve research hypothesis across multiple specifications;
10. run CPCV, PBO, Reality Check and SPA;
11. register the experiment and export an auditable research report.

**[Open the notebook →](notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb)**  
**[Run it in Google Colab →](https://colab.research.google.com/github/Alpha-Stochastic-Research/asr-quant/blob/main/notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb)**

> The public ECB sovereign curve is used as a transparent research proxy. Production EUR IRS work should use appropriate OIS discounting, projection curves, collateral conventions and live market quotes.

---

## What you can build with ASRQuant

| Area | Core capabilities |
|---|---|
| **Fixed Income & IRD** | calendars, schedules, curves, deposits, FRAs, bonds, swaps, OIS, DV01, key-rate DV01, quote PV01, P&L explain |
| **Research Validation** | CPCV, PBO, Reality Check, SPA, leakage diagnostics, multiverse analysis |
| **Risk** | VaR, Expected Shortfall, EVT, drawdowns, scenario P&L, risk contributions |
| **Portfolio Research** | optimization, constraints, risk budgeting, covariance comparison, transaction costs |
| **Backtesting** | auditable backtests, implementation-sensitive research workflows, performance diagnostics |
| **Simulation** | Monte Carlo, stochastic processes, variance-reduction tools, deterministic scenarios |
| **Credit** | hazard curves, survival probabilities, CDS analytics, credit sensitivities |
| **Alpha & Factors** | cross-sectional signals, IC analysis, PCA, factor exposures, risk decomposition |
| **Market Microstructure** | spread, microprice, order-flow imbalance, Kyle lambda, liquidity analytics |
| **Machine Learning** | leakage-aware walk-forward research, model comparison and diagnostics |
| **Reproducible Research** | immutable data snapshots, point-in-time data, experiment registry, research graph, reports |

---

## Why ASRQuant

### 1. Quantitative objects remain explicit

Curves, conventions, instruments, market quotes, risk measures and validation outputs are inspectable research objects rather than hidden side effects.

### 2. Validation is part of the workflow

ASRQuant treats selection risk, leakage and specification fragility as first-class research problems.

```python
pbo = asr.validation.probability_of_backtest_overfitting(strategy_returns)
reality = asr.validation.reality_check(strategy_returns)
spa = asr.validation.spa_test(strategy_returns)
```

These diagnostics are **evidence filters**, not certificates that a strategy is economically valid.

### 3. Fixed-income risk can be expressed in market space

```python
builder = asr.rates.CurveBuilder.from_quotes(
    deposits={0.25: 0.0210, 0.50: 0.0220},
    swaps={1.0: 0.0230, 2.0: 0.0240, 5.0: 0.0260},
)
build = builder.build()

swap = asr.rates.InterestRateSwap(
    maturity=5.0,
    fixed_rate=0.026,
    notional=10_000_000,
)

risk = asr.rates.curve_risk(swap, build.curve, build_result=build)

print(risk.dv01)
print(risk.key_rate_dv01)
print(risk.quote_pv01)
```

### 4. Reproducibility is part of the result

```python
store = asr.data.DataStore("./research-data")
snapshot = store.put("rates_panel", data, source="ECB")

experiment = asr.research.Experiment(
    name="curve_signal",
    config={"lookback": 60},
    data={"market": snapshot},
    seed=42,
)

registry = asr.research.ExperimentRegistry("experiments.jsonl")
registry.add(experiment)
```

The package records not only the final number, but also the path that produced it.

---

## Install

Core package:

```bash
pip install --upgrade asrquant
```

Useful extras:

```bash
pip install "asrquant[data]"          # Yahoo Finance, Excel, Parquet, Feather
pip install "asrquant[providers]"     # ECB / HTTP market-data providers
pip install "asrquant[visualization]" # Matplotlib, Plotly, HTML reporting
pip install "asrquant[ml]"            # scikit-learn, SHAP, HMM extensions
pip install "asrquant[optimization]"  # CVXPY extensions
pip install "asrquant[volatility]"    # ARCH / GARCH
pip install "asrquant[all]"
```

ASRQuant supports Python **3.10–3.13** across the 1.3 release line.

---

## One import

```python
import asrquant as asr

print(asr.__version__)
```

Recommended public namespaces:

```text
asr.data           market data, validation, snapshots and providers
asr.hypotheses     hypothesis discovery and novelty audit
asr.alpha          cross-sectional signal research
asr.factors        PCA, exposures and factor-risk decomposition
asr.risk           VaR, ES, EVT, drawdown and portfolio risk
asr.validation     CPCV, PBO, Reality Check, SPA, leakage, multiverse
asr.scenarios      deterministic cross-domain stress scenarios
asr.credit         hazard curves and CDS analytics
asr.backtesting    auditable backtesting
asr.portfolio      optimization, constraints and risk budgeting
asr.costs          transaction-cost and impact models
asr.stats          econometrics, bootstrap and inference
asr.ml             leakage-aware walk-forward ML
asr.options        derivatives pricing and Greeks
asr.rates          conventions, curves, instruments and rates risk
asr.calibration    calibrated-model diagnostics
asr.sensitivities first-, second- and cross-sensitivities
asr.regimes        volatility and structural-break diagnostics
asr.stochastic     stochastic processes
asr.mc             Monte Carlo and variance reduction
asr.research       experiments, lineage and research reports
asr.trading        paper trading and guarded execution primitives
```

---

## Five-minute examples

### Public ECB curve

```python
import asrquant as asr

curve_history = asr.data.ecb_yield_curve(
    maturities=["3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"],
    start="2024-01-01",
)

quality = asr.data.validate(curve_history)
print(quality.summary)
```

### Portfolio risk

```python
risk = asr.risk.portfolio_risk_report(
    returns,
    weights,
    level=0.99,
)

print(risk.summary)
```

### Research report

```python
report = asr.research.ResearchReport("rates_research")
report.add(experiment, "experiment")
report.add(risk, "risk")
report.export("research_report.html")
```

---

## Research standard

ASRQuant is built for workflows where a result should be able to answer:

- **Which data produced this result?**
- **Which assumptions and conventions were used?**
- **What changed across model specifications?**
- **Was chronology respected?**
- **What validation evidence exists?**
- **What are the known limitations?**
- **Can another researcher reproduce the result?**

ASRQuant does not replace quantitative judgement. It makes the research path easier to inspect, review and challenge.

---

## Documentation

- **Documentation:** https://docs.asr-lab.online/
- **Quickstart:** https://docs.asr-lab.online/quickstart/
- **Repository:** https://github.com/Alpha-Stochastic-Research/asr-quant
- **PyPI:** https://pypi.org/project/asrquant/
- **Issues:** https://github.com/Alpha-Stochastic-Research/asr-quant/issues
- **Paper:** [ASRQuant paper](paper/ASRQuant_paper.pdf)

---

## Contributing

ASRQuant is open source under the MIT License.

Useful contributions include:

- reproducible bug reports;
- numerical validation cases;
- additional market conventions;
- examples and notebooks;
- documentation improvements;
- new tests and benchmark cases.

Before contributing, please read [CONTRIBUTING.md](CONTRIBUTING.md).

If ASRQuant is useful in your research, **star the repository** — it helps other quantitative-finance researchers discover the project.

---

## Citation

If ASRQuant contributes to research or teaching, please cite the project using [CITATION.cff](CITATION.cff) and the associated ASRQuant paper where appropriate.

---

## Disclaimer

ASRQuant is research infrastructure. It is **not investment advice, a broker, or an execution venue**. Guarded execution components require deployment-specific authorization and remain fail-closed by design.

<div align="center">

**Built by [Alpha Stochastic Research](https://www.asr-lab.online)**

</div>
