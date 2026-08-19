# ASRQuant 1.2.0 API catalog

The recommended entry point is:

```python
import asrquant as asr
```

## Canonical namespaces

| Namespace | Primary use |
|---|---|
| `asr.data` | local files, URLs, providers, validation |
| `asr.hypotheses` | hypothesis discovery, search, ranking, novelty audit |
| `asr.alpha` | cross-sectional alpha research |
| `asr.factors` | PCA, factor exposures, factor-risk decomposition |
| `asr.risk` | VaR, ES, risk contribution, scenarios |
| `asr.microstructure` | spreads, microprice, OFI, liquidity, Kyle lambda |
| `asr.backtesting` | auditable backtesting |
| `asr.portfolio` | covariance and portfolio optimization |
| `asr.stats` | econometrics, bootstrap and inference |
| `asr.ml` | chronology-safe walk-forward machine learning |
| `asr.options` | derivatives pricing and Greeks |
| `asr.rates` | fixed income and interest-rate derivatives |
| `asr.stochastic` | stochastic-process simulation |
| `asr.mc` | universal Monte Carlo |
| `asr.vol` | volatility estimators and models |
| `asr.visuals` | visualization catalogue |
| `asr.research` | reproducible research workflow |
| `asr.trading` | paper trading and guarded execution primitives |

## Canonical verbs

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

## Data

- `asr.data.load`
- `asr.data.validate`
- `asr.data.from_provider`
- `asr.data.yahoo`
- `asr.data.ecb_yield_curve`
- legacy: `load_prices`, `load_sql`, `clean_prices`, `simple_returns`, `log_returns`
- providers: `ECBProvider`, `YahooProvider`, `FREDProvider`, `BinanceProvider`, `AlphaVantageProvider`

## Hypothesis discovery

- `HypothesisIdea`, `HypothesisCollection`, `HypothesisSearchResult`, `NoveltyAuditResult`
- `asr.hypotheses.from_data`
- `asr.hypotheses.from_literature`
- `asr.hypotheses.from_model_disagreement`
- `asr.hypotheses.from_robustness`
- `asr.hypotheses.discover`
- `asr.hypotheses.search`
- `asr.hypotheses.audit`
- existing literature engine: `LiteratureCorpus.discover_hypotheses`
- existing discovery board: `asr.discovery.weekly`, `ResearchBoard`, `ResearchCandidate`

## Alpha

- `cross_sectional_rank`
- `cross_sectional_zscore`
- `winsorize_cross_section`
- `neutralize_cross_section`
- `forward_returns`
- `information_coefficient`
- `ic_decay`
- `quantile_portfolio_returns`
- `long_short_return`
- `signal_to_weights`
- `weight_turnover`
- `analyze_signal`

## Factors

- `asr.factors.pca`
- `asr.factors.exposures`
- `asr.factors.rolling_beta`
- `asr.factors.risk_decomposition`
- `PCAFactorResult`
- `FactorExposureResult`
- `FactorRiskResult`

## Risk

- `portfolio_returns`
- `portfolio_var`
- `portfolio_expected_shortfall`
- `rolling_var`
- `covariance_risk_contributions`
- `expected_shortfall_contributions`
- `scenario_pnl`
- `portfolio_risk_report`

## Microstructure

- `midquote`
- `quoted_spread`
- `effective_spread`
- `realized_spread`
- `microprice`
- `price_impact`
- `order_flow_imbalance`
- `amihud_illiquidity`
- `roll_spread`
- `kyle_lambda`

## Portfolio

- `asr.portfolio.optimize`
- `estimate_covariance`
- `minimum_variance`
- `maximum_sharpe`
- `equal_risk_contribution`
- `maximum_diversification`
- `hierarchical_risk_parity`
- `efficient_frontier`
- `black_litterman`
- `risk_contributions`

## Statistics

- `asr.stats.regress`
- `ols`
- `rolling_regression`
- `quantile_regression`
- `polynomial_regression`
- `regularized_regression`
- `logistic_regression`
- `factor_regression`
- `stationarity_tests`
- `block_bootstrap`
- `permutation_test`
- `benjamini_hochberg`
- `cointegration_test`
- `granger_causality`
- `arima_fit`, `var_fit`, `autoregression_fit`

## Machine learning

- `asr.ml.fit`
- `walk_forward_fit`
- `lag_features`
- `technical_features`
- `forward_target`
- `resolve_estimator`

## Derivatives

- `asr.options.price`
- `black_scholes_price`, `black_scholes_greeks`
- `black76_price`
- `bachelier_price`, `bachelier_greeks`
- `crr_binomial_price`
- `implied_volatility`
- Monte Carlo option pricers

## Interest rates

- conventions: `year_fraction`, `maturity_to_years`, `payment_schedule`
- curves: `DiscountCurve`, `ForwardCurve`, `MultiCurve`
- curve construction: `bootstrap_discount_curve`, `bootstrap_projection_curve_from_swaps`
- parametric curves: Nelson-Siegel / Svensson functions and calibrators
- instruments: FRAs, futures, swaps, basis swaps, OIS, bond forwards
- rate options: caps, floors, caplets, swaptions
- smile: SABR
- models: Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski, HJM, LMM
- risk: DV01, key-rate DV01, curve scenarios, key-rate hedging
- research: PCA, level/slope/curvature, carry/roll, interpolation risk, no-arbitrage diagnostics
- canonical: `asr.rates.analyze`, `asr.rates.calibrate`

## Backtesting and performance

- `asr.backtesting.run`
- `BacktestSpec`, `CostModel`, `BacktestResult`
- `compare_backtests`, `implementation_audit`
- performance metrics include Sharpe, Sortino, Calmar, Omega, VaR/ES, PSR/DSR, tracking error, information ratio and drawdown metrics

## Research and reproducibility

- `ResearchProject`
- `research_project`, `autoresearch`
- `ResearchBoard`, `WeeklyResearchCycle`
- `build_manifest`
- `SQLiteAuditStore`

## Production and guarded live execution

- `DeploymentEvidence`
- `ProductionReadinessGate`
- `DeploymentCertificate`
- `LiveRiskPolicy`
- `PersistentKillSwitch`
- `PreTradeRiskEngine`
- `LiveTradingEngine`
- `AlpacaBroker.paper(...)`
- certificate-gated live path

Installing ASRQuant does not authorize live capital deployment.
