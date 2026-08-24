# ASRQuant 1.3.0 API Catalog

The supported user-facing style remains:

```python
import asrquant as asr
```

## Research and data

| Namespace | Main entry points |
|---|---|
| `asr.data` | `load`, `validate`, `snapshot`, `DataStore`, `PointInTimeFrame`, provider helpers |
| `asr.hypotheses` | `discover`, `from_data`, `from_literature`, `search`, `audit` |
| `asr.research` | `ResearchProject`, `Experiment`, `ExperimentRegistry`, `ResearchGraph`, `ResearchReport` |
| `asr.validation` | walk-forward/purged CV, CPCV, PBO, Reality Check, SPA, leakage, multiverse, `strategy_report` |

## Markets and instruments

| Namespace | Main entry points |
|---|---|
| `asr.rates` | calendars, schedules, curves, `CurveBuilder`, rate instruments, IR derivatives, curve risk, P&L explain |
| `asr.credit` | `HazardCurve`, `CDS`, `bootstrap_hazard_curve` |
| `asr.options` | Black-Scholes, Bachelier, Black-76, trees, MC, Greeks |
| `asr.microstructure` | spreads, microprice, OFI, price impact, Amihud, Roll, Kyle lambda |
| `asr.scenarios` | rate, asset, volatility and liquidity scenario contracts |

## Portfolio, risk and performance

| Namespace | Main entry points |
|---|---|
| `asr.portfolio` | canonical optimizer, HRP, Black-Litterman, constraints, cost-aware/robust optimization, risk budgeting |
| `asr.covariance` | sample, EWMA, Ledoit-Wolf, factor, robust and holdout estimator comparison |
| `asr.risk` | VaR/ES, contributions, scenarios, EVT, filtered historical simulation, drawdown tail measures |
| `asr.factors` | PCA, exposures, rolling beta, factor-risk decomposition |
| `asr.performance` | factor attribution, Brinson attribution |
| `asr.alpha` | IC, IC decay, quantile portfolios, turnover, signal analysis, capacity |

## Modelling and numerical research

| Namespace | Main entry points |
|---|---|
| `asr.calibration` | `CalibrationProblem` and diagnostics |
| `asr.sensitivities` | generic finite-difference sensitivities |
| `asr.dependence` | Gaussian and Student-t copula research |
| `asr.regimes` | volatility regimes, structural-break diagnostics, optional HMM |
| `asr.model_selection` | prediction-model comparison |
| `asr.mc` | Monte Carlo plus variance reduction |
| `asr.stochastic` | stochastic process simulation |
| `asr.stats` | regression, econometrics, bootstrap and inference |
| `asr.ml` | chronology-aware walk-forward ML |

## Implementation and extension

| Namespace | Main entry points |
|---|---|
| `asr.backtesting` | auditable weight-based backtesting |
| `asr.costs` | fixed/spread/linear/square-root impact cost models |
| `asr.diagnostics` | conservative diagnostics for structured results |
| `asr.register` | internal adapter registration |
| `asr.trading` | paper trading and guarded execution primitives |

## Stable canonical verbs

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

See `PUBLIC_API_v1.3.json` for the declared compatibility snapshot.
