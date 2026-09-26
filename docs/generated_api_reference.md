# Generated Python API Reference

!!! info "Generated from source"
    This page is regenerated from the current `src/asrquant` tree on every documentation build. It reflects the exported surface of the same commit deployed to GitHub Pages.

**ASRQuant version:** `1.3.0`  
**Exported names discovered:** `296`

## Namespaces

### `alpha`

**Kind:** namespace

Cross-sectional alpha research and signal diagnostics.

### `approx`

**Kind:** namespace

Interpolation, smoothing, response surfaces, extrapolation, and sensitivities.

### `backtesting`

**Kind:** namespace

Auditable vectorized portfolio backtesting.

### `calibration`

**Kind:** namespace

Generic nonlinear calibration contracts with diagnostics and identifiability checks.

### `contracts`

**Kind:** namespace

Shared ASRQuant 1.2 result contracts and domain exceptions.

### `costs`

**Kind:** namespace

Composable transaction-cost models for research and capacity analysis.

### `covariance`

**Kind:** namespace

Covariance estimators and out-of-sample diagnostics for portfolio research.

### `credit`

**Kind:** namespace

Reduced-form credit curves and transparent CDS analytics.

### `data`

**Kind:** namespace

Market-data normalization, validation, and hashing.

### `dependence`

**Kind:** namespace

Copula-based dependence diagnostics for portfolio and tail-risk research.

### `diagnostics`

**Kind:** namespace

Cross-domain diagnostics that explain fragile quantitative results.

### `discovery`

**Kind:** namespace

Research-discovery engine for ASRQuant.

### `factors`

**Kind:** namespace

Factor research, PCA decomposition, exposures, and portfolio factor risk.

### `hypotheses`

**Kind:** namespace

Hypothesis discovery, search and audit for ASRQuant 1.2.0.

### `math`

**Kind:** namespace

Numerical helpers exposed through ASRQuant so user code needs one import.

### `mc`

**Kind:** namespace

Universal Monte Carlo estimation, scenario generation, and parameter surfaces.

### `microstructure`

**Kind:** namespace

Market-microstructure diagnostics for research and execution analysis.

### `ml`

**Kind:** namespace

Leakage-aware feature engineering and walk-forward machine-learning evaluation.

### `model_selection`

**Kind:** namespace

Comparable model diagnostics on a common observation set.

### `options`

**Kind:** namespace

Closed-form, tree, and Monte Carlo derivative analytics.

### `performance`

**Kind:** namespace

Portfolio performance attribution helpers.

### `portfolio`

**Kind:** namespace

Portfolio construction and risk decomposition without mandatory solvers.

### `random`

**Kind:** namespace

Central random-seed helpers for reproducible ASRQuant experiments.

### `rates`

**Kind:** namespace

Interest-rate and fixed-income derivatives research toolkit.

### `regimes`

**Kind:** namespace

Regime diagnostics for time-series research.

### `research`

**Kind:** namespace

Parameter sweeps and strategy comparison for reproducible research.

### `risk`

**Kind:** namespace

Portfolio risk decomposition, tail risk, and scenario analytics.

### `scenarios`

**Kind:** namespace

Cross-domain scenario objects for rates, portfolios and stress analysis.

### `sensitivities`

**Kind:** namespace

Generic finite-difference sensitivity engine for scalar quantitative models.

### `stats`

**Kind:** namespace

Regression, time-series tests, bootstrap inference, and factor analysis.

### `stochastic`

**Kind:** namespace

Stochastic processes, synthetic markets, bootstrap, and Monte Carlo pricing.

### `trading`

**Kind:** namespace

Broker-neutral algorithmic-trading primitives and deterministic paper trading.

### `validation`

**Kind:** namespace

Time-aware validation, leakage guards, and stress utilities.

### `visuals`

**Kind:** namespace

ASRQuant visualization namespace.

### `vol`

**Kind:** namespace

Realized, conditional, and implied-volatility utilities.

## Classes

### `AccountSnapshot`

**Kind:** class

```python
AccountSnapshot(account_id: 'str', equity: 'float', last_equity: 'float', cash: 'float', buying_power: 'float', trading_blocked: 'bool', account_blocked: 'bool', timestamp: 'str' = <factory>) -> None
```

AccountSnapshot(account_id: 'str', equity: 'float', last_equity: 'float', cash: 'float', buying_power: 'float', trading_blocked: 'bool', account_blocked: 'bool', timestamp: 'str' = <factory>)

Defined in `asrquant.live`.

### `AlpacaBroker`

**Kind:** class

```python
AlpacaBroker(*, credentials: 'BrokerCredentials', environment: 'BrokerEnvironment', session: 'Any | None' = None, timeout_seconds: 'float' = 10.0, base_url: 'str | None' = None, _live_authorized: 'bool' = False) -> 'None'
```

Minimal Alpaca Trading API adapter with explicit paper/live separation.

Defined in `asrquant.live`.

### `AlphaVantageProvider`

**Kind:** class

```python
AlphaVantageProvider(api_key: 'str | None' = None, timeout: 'float' = 20.0) -> None
```

Alpha Vantage equities/FX/crypto connector.

Defined in `asrquant.providers`.

### `ApproximationResult`

**Kind:** class

```python
ApproximationResult(model: 'Any', method: 'str', dimension: 'int', domain_min: 'np.ndarray', domain_max: 'np.ndarray', metadata: 'dict[str, Any]', predictor: 'Callable[[np.ndarray], np.ndarray]', uncertainty_predictor: 'Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None' = None) -> None
```

Fitted approximation with a uniform prediction interface.

Defined in `asrquant.approximation`.

### `AuditEvent`

**Kind:** class

```python
AuditEvent(sequence: 'int', event_id: 'str', timestamp: 'str', event_type: 'str', payload: 'dict[str, Any]', previous_hash: 'str', event_hash: 'str') -> None
```

AuditEvent(sequence: 'int', event_id: 'str', timestamp: 'str', event_type: 'str', payload: 'dict[str, Any]', previous_hash: 'str', event_hash: 'str')

Defined in `asrquant.audit_store`.

### `AuditResult`

**Kind:** class

```python
AuditResult(summary: 'pd.DataFrame', diagnostics: 'pd.Series', results: 'dict[str, BacktestResult]') -> None
```

Backtests and cross-contract dispersion diagnostics.

Defined in `asrquant.audit`.

### `BacktestResult`

**Kind:** class

```python
BacktestResult(prices: 'pd.DataFrame', asset_returns: 'pd.DataFrame', target_weights: 'pd.DataFrame', effective_weights: 'pd.DataFrame', gross_returns: 'pd.Series', net_returns: 'pd.Series', equity: 'pd.Series', turnover: 'pd.Series', costs: 'pd.Series', cost_breakdown: 'pd.DataFrame', spec: 'BacktestSpec', metadata: 'dict[str, Any]') -> None
```

All outputs required for analysis, audit, visualization, and export.

Defined in `asrquant.backtest`.

### `BacktestSpec`

**Kind:** class

```python
BacktestSpec(initial_capital: 'float' = 100000.0, annualization: 'int' = 252, execution_delay: 'int' = 1, rebalance: 'str' = 'bar', long_only: 'bool' = False, max_gross_leverage: 'float' = 1.0, max_abs_weight: 'float' = 1.0, risk_free_rate: 'float' = 0.0, missing_data: 'MissingDataPolicy' = <MissingDataPolicy.RAISE: 'raise'>, costs: 'CostModel' = <factory>, name: 'str' = 'ASRQuant backtest', metadata: 'dict[str, Any]' = <factory>) -> None
```

A complete, serializable contract for a weight-based backtest.

Defined in `asrquant.config`.

### `BermudanLSMResult`

**Kind:** class

```python
BermudanLSMResult(price: 'float', exercise_probability: 'np.ndarray', exercise_time_index: 'np.ndarray', path_values: 'np.ndarray') -> None
```

Generic least-squares Monte Carlo early-exercise result.

Defined in `asrquant.interest_rates`.

### `BinanceProvider`

**Kind:** class

```python
BinanceProvider(base_url: 'str' = 'https://data-api.binance.vision', timeout: 'float' = 20.0) -> None
```

Public Binance Spot market-data connector; no credentials are required.

Defined in `asrquant.providers`.

### `BrokerAdapter`

**Kind:** class

```python
BrokerAdapter(*args, **kwargs)
```

Minimal interface for an external paper or live broker adapter.

Defined in `asrquant.trading`.

### `BrokerCredentials`

**Kind:** class

```python
BrokerCredentials(api_key: 'str', api_secret: 'str') -> None
```

BrokerCredentials(api_key: 'str', api_secret: 'str')

Defined in `asrquant.live`.

### `BrokerEnvironment`

**Kind:** class

```python
BrokerEnvironment(*values)
```

str(object='') -> str

Defined in `asrquant.live`.

### `BrokerHealth`

**Kind:** class

```python
BrokerHealth(state: 'HealthState', broker: 'str', environment: 'BrokerEnvironment', latency_ms: 'float', market_open: 'bool | None', account_reachable: 'bool', details: 'dict[str, Any]' = <factory>) -> None
```

BrokerHealth(state: 'HealthState', broker: 'str', environment: 'BrokerEnvironment', latency_ms: 'float', market_open: 'bool | None', account_reachable: 'bool', details: 'dict[str, Any]' = <factory>)

Defined in `asrquant.live`.

### `BrokerOrderReceipt`

**Kind:** class

```python
BrokerOrderReceipt(broker_order_id: 'str', client_order_id: 'str', symbol: 'str', quantity: 'float', side: 'str', order_type: 'str', status: 'str', submitted_at: 'str', filled_quantity: 'float' = 0.0, average_fill_price: 'float | None' = None, request_id: 'str | None' = None, raw: 'dict[str, Any]' = <factory>) -> None
```

BrokerOrderReceipt(broker_order_id: 'str', client_order_id: 'str', symbol: 'str', quantity: 'float', side: 'str', order_type: 'str', status: 'str', submitted_at: 'str', filled_quantity: 'float' = 0.0, average_fill_price: 'float | None' = None, request_id: 'str | None' = None, raw: 'dict[str, Any]' = <factory>)

Defined in `asrquant.live`.

### `CheckLevel`

**Kind:** class

```python
CheckLevel(*values)
```

str(object='') -> str

Defined in `asrquant.production`.

### `CheckState`

**Kind:** class

```python
CheckState(*values)
```

str(object='') -> str

Defined in `asrquant.production`.

### `CostModel`

**Kind:** class

```python
CostModel(commission_bps: 'float' = 0.0, spread_bps: 'float' = 0.0, slippage_bps: 'float' = 0.0, borrow_bps_annual: 'float' = 0.0, impact_coefficient: 'float' = 0.0, impact_exponent: 'float' = 1.5) -> None
```

Transparent transaction- and financing-cost model.

Defined in `asrquant.config`.

### `DataPlan`

**Kind:** class

```python
DataPlan(requirements: 'list[DataRequirement]', notes: 'list[str]' = <factory>, hypothesis_id: 'str | None' = None) -> None
```

Reviewable data specification generated from an economic hypothesis.

Defined in `asrquant.workflow`.

### `DataRequirement`

**Kind:** class

```python
DataRequirement(name: 'str', role: 'str', suggested_source: 'str | None' = None, suggested_symbol: 'str | None' = None, frequency: 'str' = 'daily', field: 'str' = 'Close', availability_lag: 'int' = 0, point_in_time_required: 'bool' = False, required: 'bool' = True, description: 'str' = '') -> None
```

One variable required to operationalize a hypothesis.

Defined in `asrquant.workflow`.

### `DecisionResult`

**Kind:** class

```python
DecisionResult(status: 'str', score: 'float', reasons: 'list[str]', risks: 'list[str]', required_next_step: 'str', evidence: 'pd.Series', governance_note: 'str' = 'This is a research-governance decision, not personalized investment advice or an instruction to trade live capital.') -> None
```

DecisionResult(status: 'str', score: 'float', reasons: 'list[str]', risks: 'list[str]', required_next_step: 'str', evidence: 'pd.Series', governance_note: 'str' = 'This is a research-governance decision, not personalized investment advice or an instruction to trade live capital.')

Defined in `asrquant.workflow`.

### `DeploymentCertificate`

**Kind:** class

```python
DeploymentCertificate(certificate_id: 'str', issued_at: 'str', expires_at: 'str', release_version: 'str', broker: 'str', account_hash: 'str', risk_policy_hash: 'str', evidence_hash: 'str', max_live_capital: 'float', approved_by: 'tuple[str, ...]', environment_fingerprint: 'str', change_ticket: 'str', signature: 'str' = '') -> None
```

Signed authorization required to construct a live-capital session.

Defined in `asrquant.production`.

### `DeploymentEvidence`

**Kind:** class

```python
DeploymentEvidence(release_version: 'str', ci_passed: 'bool' = False, test_count: 'int' = 0, coverage_percent: 'float' = 0.0, static_analysis_passed: 'bool' = False, dependency_scan_passed: 'bool' = False, secrets_scan_passed: 'bool' = False, sbom_present: 'bool' = False, artifacts_signed: 'bool' = False, reproducible_build_verified: 'bool' = False, disaster_recovery_tested: 'bool' = False, rollback_tested: 'bool' = False, monitoring_enabled: 'bool' = False, alerting_enabled: 'bool' = False, durable_audit_log_enabled: 'bool' = False, time_synchronization_verified: 'bool' = False, broker_paper_days: 'int' = 0, broker_paper_orders: 'int' = 0, reconciliation_mismatches: 'int' = 1, unresolved_critical_incidents: 'int' = 1, operator_approved: 'bool' = False, legal_compliance_reviewed: 'bool' = False, data_licenses_reviewed: 'bool' = False, strategy_owner_approved: 'bool' = False, model_validation_approved: 'bool' = False, change_ticket: 'str' = '', notes: 'dict[str, Any]' = <factory>) -> None
```

Evidence required before a deployment certificate can be issued.

Defined in `asrquant.production`.

### `DiscountCurve`

**Kind:** class

```python
DiscountCurve(times: 'np.ndarray', discounts: 'np.ndarray', interpolation: 'str' = 'log_linear', name: 'str' = 'discount', metadata: 'Mapping[str, Any]' = <factory>) -> None
```

Arbitrage-aware discount curve with transparent interpolation.

Defined in `asrquant.interest_rates`.

### `ECBProvider`

**Kind:** class

```python
ECBProvider(base_url: 'str' = 'https://data-api.ecb.europa.eu/service/data', timeout: 'float' = 30.0) -> None
```

European Central Bank Data Portal SDMX REST connector.

Defined in `asrquant.providers`.

### `EconomicHypothesis`

**Kind:** class

```python
EconomicHypothesis(hypothesis_id: 'str', statement: 'str', predictor: 'str | None' = None, target: 'str | None' = None, expected_sign: 'str | None' = None, horizon: 'int | str | None' = None, universe: 'str | None' = None, null: 'str' = 'No stable out-of-sample predictive or explanatory relationship.', mechanism: 'str' = '', novelty_status: 'str' = 'conceptual', evidence_status: 'str' = 'unknown', confidence: 'float | None' = None, evidence: 'list[SourceExcerpt]' = <factory>, invalidation_criteria: 'list[str]' = <factory>, metadata: 'dict[str, Any]' = <factory>) -> None
```

Operational research hypothesis with explicit falsification fields.

Defined in `asrquant.workflow`.

### `ExecutionBroker`

**Kind:** class

```python
ExecutionBroker(*args, **kwargs)
```

Base class for protocol classes.

Defined in `asrquant.live`.

### `FeaturePlan`

**Kind:** class

```python
FeaturePlan(specs: 'list[FeatureSpec]', notes: 'list[str]' = <factory>) -> None
```

FeaturePlan(specs: 'list[FeatureSpec]', notes: 'list[str]' = <factory>)

Defined in `asrquant.workflow`.

### `FeatureSpec`

**Kind:** class

```python
FeatureSpec(name: 'str', source: 'str | tuple[str, str]', transform: 'str' = 'raw', window: 'int | None' = None, lag: 'int' = 0, availability_lag: 'int' = 0, params: 'dict[str, Any]' = <factory>) -> None
```

One leakage-aware transformation in a feature pipeline.

Defined in `asrquant.workflow`.

### `Fill`

**Kind:** class

```python
Fill(order_id: 'str', symbol: 'str', quantity: 'float', price: 'float', commission: 'float', timestamp: 'Any', slippage: 'float' = 0.0) -> None
```

Fill(order_id: 'str', symbol: 'str', quantity: 'float', price: 'float', commission: 'float', timestamp: 'Any', slippage: 'float' = 0.0)

Defined in `asrquant.trading`.

### `ForwardCurve`

**Kind:** class

```python
ForwardCurve(starts: 'np.ndarray', ends: 'np.ndarray', forwards: 'np.ndarray', tenor: 'str' = 'generic') -> None
```

Piecewise-simple forward curve for a single floating-rate tenor.

Defined in `asrquant.interest_rates`.

### `FREDProvider`

**Kind:** class

```python
FREDProvider(api_key: 'str | None' = None, timeout: 'float' = 20.0) -> None
```

Federal Reserve Bank of St. Louis FRED series connector.

Defined in `asrquant.providers`.

### `HealthState`

**Kind:** class

```python
HealthState(*values)
```

str(object='') -> str

Defined in `asrquant.live`.

### `HedgeSolution`

**Kind:** class

```python
HedgeSolution(weights: 'np.ndarray', residual_exposure: 'np.ndarray', residual_norm: 'float') -> None
```

Least-squares key-rate hedge solution.

Defined in `asrquant.interest_rates`.

### `HypothesisCandidate`

**Kind:** class

```python
HypothesisCandidate(hypothesis_id: 'str', statement: 'str', novelty_status: 'str', confidence: 'float', evidence: 'list[SourceExcerpt]' = <factory>, expected_sign: 'str | None' = None, tags: 'list[str]' = <factory>, rationale: 'str' = '', evidence_status: 'str' = 'proposed', metadata: 'dict[str, Any]' = <factory>) -> None
```

A source-linked economic hypothesis or research gap.

Defined in `asrquant.literature`.

### `HypothesisRegistry`

**Kind:** class

```python
HypothesisRegistry(hypotheses: 'list[HypothesisCandidate]', corpus_fingerprint: 'str | None' = None, scope_note: 'str' = "Novelty labels are corpus-relative. 'corpus-novel' never means that a claim has never been tested anywhere in the global literature.") -> None
```

Searchable collection of candidate hypotheses.

Defined in `asrquant.literature`.

### `HypothesisTestResult`

**Kind:** class

```python
HypothesisTestResult(feature: 'str', target_name: 'str', horizon: 'int', regression: 'Any', expected_sign: 'str | None', sign_consistent: 'bool | None', p_value: 'float | None') -> None
```

Econometric test of the selected feature against a future target.

Defined in `asrquant.workflow`.

### `LiteratureCorpus`

**Kind:** class

```python
LiteratureCorpus(papers: 'list[PaperDocument]', topic: 'str | None' = None) -> None
```

A collection of parsed papers with conservative hypothesis discovery.

Defined in `asrquant.literature`.

### `LiveRiskPolicy`

**Kind:** class

```python
LiveRiskPolicy(max_gross_leverage: 'float' = 1.0, max_position_weight: 'float' = 0.25, max_order_notional: 'float | None' = None, max_daily_turnover: 'float' = 2.0, max_drawdown: 'float' = 0.2, allow_short: 'bool' = True, minimum_cash: 'float' = 0.0, max_daily_loss: 'float' = 0.03, max_open_orders: 'int' = 20, max_orders_per_minute: 'int' = 30, max_price_deviation_bps: 'float' = 200.0, max_market_data_age_seconds: 'float' = 5.0, max_capital: 'float | None' = None, max_position_notional: 'float | None' = None, require_market_open: 'bool' = True, reject_duplicate_orders: 'bool' = True, symbol_allowlist: 'tuple[str, ...]' = (), symbol_denylist: 'tuple[str, ...]' = (), reconciliation_quantity_tolerance: 'float' = 1e-08, reconciliation_cash_tolerance: 'float' = 0.01, max_consecutive_broker_failures: 'int' = 3) -> None
```

Stricter controls applied before any broker submission.

Defined in `asrquant.live`.

### `LiveTradingEngine`

**Kind:** class

```python
LiveTradingEngine(*, broker: 'ExecutionBroker', policy: 'LiveRiskPolicy', audit_store: 'SQLiteAuditStore', kill_switch: 'PersistentKillSwitch') -> 'None'
```

Production execution coordinator with risk, audit, and kill-switch controls.

Defined in `asrquant.live`.

### `MarketDataProvider`

**Kind:** class

```python
MarketDataProvider()
```

Minimal interface implemented by all market-data providers.

Defined in `asrquant.providers`.

### `MarketDataSnapshot`

**Kind:** class

```python
MarketDataSnapshot(symbol: 'str', price: 'float', timestamp: 'str | datetime', bid: 'float | None' = None, ask: 'float | None' = None, source: 'str' = 'unknown') -> None
```

MarketDataSnapshot(symbol: 'str', price: 'float', timestamp: 'str | datetime', bid: 'float | None' = None, ask: 'float | None' = None, source: 'str' = 'unknown')

Defined in `asrquant.live`.

### `MartingaleResult`

**Kind:** class

```python
MartingaleResult(increments: 'pd.Series', statistics: 'pd.Series', regression: 'object') -> None
```

Diagnostics that can reject, but never prove, a martingale hypothesis.

Defined in `asrquant.martingales`.

### `MissingDataPolicy`

**Kind:** class

```python
MissingDataPolicy(*values)
```

How missing observations are handled before return calculation.

Defined in `asrquant.config`.

### `ModelFactory`

**Kind:** class

```python
ModelFactory()
```

Attribute-based model factory exposed as ``asrquant.models``.

Defined in `asrquant.models`.

### `MonteCarloPriceResult`

**Kind:** class

```python
MonteCarloPriceResult(price: 'float', standard_error: 'float', confidence_interval: 'tuple[float, float]', discounted_payoffs: 'np.ndarray', simulation: 'SimulationResult', confidence: 'float' = 0.95) -> None
```

Monte Carlo price estimate with uncertainty and raw discounted payoffs.

Defined in `asrquant.simulation`.

### `MonteCarloResult`

**Kind:** class

```python
MonteCarloResult(estimate: 'float', outcomes: 'Array', estimator: 'str', level: 'float' = 0.95, confidence: 'float' = 0.95, scenarios: 'Any | None' = None, parameters: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>) -> None
```

Universal Monte Carlo result with raw scenarios, outcomes, and inference.

Defined in `asrquant.monte_carlo`.

### `MultiCurve`

**Kind:** class

```python
MultiCurve(discount: 'DiscountCurve', projections: 'Mapping[str, ForwardCurve]') -> None
```

OIS discount curve plus tenor-specific projection curves.

Defined in `asrquant.interest_rates`.

### `OptionPrice`

**Kind:** class

```python
OptionPrice(price: 'float', model: 'str', greeks: 'dict[str, float] | None' = None, standard_error: 'float | None' = None, confidence_interval: 'tuple[float, float] | None' = None) -> None
```

Standard option-pricing response.

Defined in `asrquant.derivatives`.

### `Order`

**Kind:** class

```python
Order(symbol: 'str', quantity: 'float', side: 'OrderSide', order_type: 'OrderType' = <OrderType.MARKET: 'market'>, limit_price: 'float | None' = None, stop_price: 'float | None' = None, timestamp: 'Any' = None, order_id: 'str' = <factory>, status: 'OrderStatus' = <OrderStatus.CREATED: 'created'>, metadata: 'dict[str, Any]' = <factory>) -> None
```

Order(symbol: 'str', quantity: 'float', side: 'OrderSide', order_type: 'OrderType' = <OrderType.MARKET: 'market'>, limit_price: 'float | None' = None, stop_price: 'float | None' = None, timestamp: 'Any' = None, order_id: 'str' = <factory>, status: 'OrderStatus' = <OrderStatus.CREATED: 'created'>, metadata: 'dict[str, Any]' = <factory>)

Defined in `asrquant.trading`.

### `OrderSide`

**Kind:** class

```python
OrderSide(*values)
```

str(object='') -> str

Defined in `asrquant.trading`.

### `OrderStatus`

**Kind:** class

```python
OrderStatus(*values)
```

str(object='') -> str

Defined in `asrquant.trading`.

### `OrderType`

**Kind:** class

```python
OrderType(*values)
```

str(object='') -> str

Defined in `asrquant.trading`.

### `PaperBroker`

**Kind:** class

```python
PaperBroker(initial_cash: 'float' = 100000.0, *, commission_bps: 'float' = 0.0, slippage_bps: 'float' = 0.0, participation_rate: 'float' = 1.0) -> 'None'
```

Immediate-fill paper broker with transparent costs and order history.

Defined in `asrquant.trading`.

### `PaperDocument`

**Kind:** class

```python
PaperDocument(paper_id: 'str', title: 'str', path: 'str | None', pages: 'list[str]', authors: 'list[str]' = <factory>, year: 'int | None' = None, abstract: 'str | None' = None, metadata: 'dict[str, Any]' = <factory>, warnings: 'list[str]' = <factory>) -> None
```

Parsed paper text, metadata and page-level provenance.

Defined in `asrquant.literature`.

### `PaperTrader`

**Kind:** class

```python
PaperTrader(*, initial_capital: 'float' = 100000.0, commission_bps: 'float' = 0.0, slippage_bps: 'float' = 0.0, policy: 'RiskPolicy | None' = None, annualization: 'int' = 252) -> 'None'
```

Convert target weights into orders and simulate an auditable paper session.

Defined in `asrquant.trading`.

### `PaperTradingResult`

**Kind:** class

```python
PaperTradingResult(equity: 'pd.Series', cash: 'pd.Series', positions: 'pd.DataFrame', target_weights: 'pd.DataFrame', realized_weights: 'pd.DataFrame', orders: 'pd.DataFrame', fills: 'pd.DataFrame', risk_events: 'pd.DataFrame', policy: 'RiskPolicy', metadata: 'dict[str, Any]') -> None
```

PaperTradingResult(equity: 'pd.Series', cash: 'pd.Series', positions: 'pd.DataFrame', target_weights: 'pd.DataFrame', realized_weights: 'pd.DataFrame', orders: 'pd.DataFrame', fills: 'pd.DataFrame', risk_events: 'pd.DataFrame', policy: 'RiskPolicy', metadata: 'dict[str, Any]')

Defined in `asrquant.trading`.

### `PersistentKillSwitch`

**Kind:** class

```python
PersistentKillSwitch(path: 'str | Path') -> 'None'
```

File-backed kill switch that survives process restarts.

Defined in `asrquant.live`.

### `PlotConfig`

**Kind:** class

```python
PlotConfig(backend: "Literal['matplotlib', 'plotly']" = 'matplotlib', figsize: 'tuple[float, float]' = (10.0, 5.5), title: 'str | None' = None, show: 'bool' = False) -> None
```

Shared plotting options.

Defined in `asrquant.config`.

### `PlotHandle`

**Kind:** class

```python
PlotHandle(object: 'Any') -> None
```

Backend-neutral handle returned by :func:`visualize`.

Defined in `asrquant.easy`.

### `PollingFeed`

**Kind:** class

```python
PollingFeed(provider: 'MarketDataProvider', symbol: 'str', interval_seconds: 'float' = 60.0) -> None
```

Simple near-real-time polling iterator for research dashboards.

Defined in `asrquant.providers`.

### `PortfolioSpec`

**Kind:** class

```python
PortfolioSpec(gross_leverage: 'float' = 1.0, max_abs_weight: 'float' = 1.0, long_only: 'bool' = False, volatility_target: 'float | None' = None, volatility_window: 'int' = 20, max_leverage: 'float' = 2.0) -> None
```

PortfolioSpec(gross_leverage: 'float' = 1.0, max_abs_weight: 'float' = 1.0, long_only: 'bool' = False, volatility_target: 'float | None' = None, volatility_window: 'int' = 20, max_leverage: 'float' = 2.0)

Defined in `asrquant.workflow`.

### `PositionSnapshot`

**Kind:** class

```python
PositionSnapshot(symbol: 'str', quantity: 'float', market_value: 'float', current_price: 'float', side: 'str' = 'long') -> None
```

PositionSnapshot(symbol: 'str', quantity: 'float', market_value: 'float', current_price: 'float', side: 'str' = 'long')

Defined in `asrquant.live`.

### `PreTradeRiskEngine`

**Kind:** class

```python
PreTradeRiskEngine(policy: 'LiveRiskPolicy') -> 'None'
```

Stateful deterministic pre-trade controls.

Defined in `asrquant.live`.

### `ProductionReadinessGate`

**Kind:** class

```python
ProductionReadinessGate(*, minimum_tests: 'int' = 100, minimum_coverage: 'float' = 90.0, minimum_paper_days: 'int' = 30, minimum_paper_orders: 'int' = 500) -> 'None'
```

Evaluate a strict, auditable go-live checklist.

Defined in `asrquant.production`.

### `ProductionReadinessReport`

**Kind:** class

```python
ProductionReadinessReport(checks: 'list[ReadinessCheck]', generated_at: 'str' = <factory>) -> None
```

ProductionReadinessReport(checks: 'list[ReadinessCheck]', generated_at: 'str' = <factory>)

Defined in `asrquant.production`.

### `QuantLab`

**Kind:** class

```python
QuantLab(prices: 'pd.Series | pd.DataFrame', missing_data: 'str' = 'raise')
```

Unified entry point for the end-to-end quantitative research workflow.

Defined in `asrquant.api`.

### `RateQuantLab`

**Kind:** class

```python
RateQuantLab(discount_curve: 'DiscountCurve', projections: 'dict[str, ForwardCurve]' = <factory>, history: 'list[dict[str, Any]]' = <factory>) -> None
```

Simple high-level facade for Fixed Income / Interest Rate Derivatives work.

Defined in `asrquant.interest_rates`.

### `ReadinessCheck`

**Kind:** class

```python
ReadinessCheck(code: 'str', state: 'CheckState', level: 'CheckLevel', message: 'str', evidence: 'Any' = None) -> None
```

ReadinessCheck(code: 'str', state: 'CheckState', level: 'CheckLevel', message: 'str', evidence: 'Any' = None)

Defined in `asrquant.production`.

### `ReconciliationReport`

**Kind:** class

```python
ReconciliationReport(state: 'ReconciliationState', position_differences: 'dict[str, float]', cash_difference: 'float', generated_at: 'str' = <factory>) -> None
```

ReconciliationReport(state: 'ReconciliationState', position_differences: 'dict[str, float]', cash_difference: 'float', generated_at: 'str' = <factory>)

Defined in `asrquant.live`.

### `ReconciliationState`

**Kind:** class

```python
ReconciliationState(*values)
```

str(object='') -> str

Defined in `asrquant.live`.

### `ResearchBoard`

**Kind:** class

```python
ResearchBoard(candidates: 'list[ResearchCandidate]', observations: 'list[ResearchObservation]' = <factory>, domain: 'str' = 'quantitative_finance', scope_note: 'str' = 'Candidates are hypothesis-generation outputs. Novelty is NOT established until a documented literature search and prior-art review are completed.') -> None
```

Ranked weekly research-candidate board.

Defined in `asrquant.discovery`.

### `ResearchCandidate`

**Kind:** class

```python
ResearchCandidate(candidate_id: 'str', title: 'str', research_question: 'str', hypothesis: 'str', domain: 'str', contribution_type: 'str', rationale: 'str', methods: 'tuple[str, ...]' = (), data_requirements: 'tuple[str, ...]' = (), falsification_rule: 'str' = 'Reject the candidate if the effect is not stable under pre-specified robustness checks.', novelty_status: 'str' = 'NOT_ESTABLISHED', evidence_status: 'str' = 'PROPOSED', priority_score: 'float' = 0.5, source_observations: 'tuple[str, ...]' = (), risks: 'tuple[str, ...]' = (), tags: 'tuple[str, ...]' = (), metadata: 'Mapping[str, Any]' = <factory>) -> None
```

Falsifiable candidate idea; novelty is never asserted automatically.

Defined in `asrquant.discovery`.

### `ResearchObservation`

**Kind:** class

```python
ResearchObservation(observation_id: 'str', kind: 'str', description: 'str', score: 'float', variables: 'tuple[str, ...]' = (), evidence: 'Mapping[str, Any]' = <factory>, domain: 'str' = 'quantitative_finance') -> None
```

Transparent quantitative observation from which a question may be formed.

Defined in `asrquant.discovery`.

### `ResearchProject`

**Kind:** class

```python
ResearchProject(name: 'str', topic: 'str | None' = None, corpus: 'LiteratureCorpus | None' = None, registry: 'HypothesisRegistry | None' = None, hypothesis: 'EconomicHypothesis | None' = None, data_plan: 'DataPlan | None' = None, data: 'pd.DataFrame | None' = None, tradable_assets: 'list[str]' = <factory>, feature_plan: 'FeaturePlan | None' = None, features: 'pd.DataFrame | None' = None, signal_spec: 'SignalSpec | None' = None, raw_weights: 'pd.DataFrame | None' = None, portfolio_spec: 'PortfolioSpec | None' = None, weights: 'pd.DataFrame | None' = None, backtest_result: 'BacktestResult | None' = None, hypothesis_test_result: 'HypothesisTestResult | None' = None, robustness_result: 'RobustnessResult | None' = None, decision_result: 'DecisionResult | None' = None, paper_trading_result: 'PaperTradingResult | None' = None, history: 'list[dict[str, Any]]' = <factory>) -> None
```

Stateful, reproducible project from papers to a governed decision.

Defined in `asrquant.workflow`.

### `RiskDecision`

**Kind:** class

```python
RiskDecision(approved: 'bool', codes: 'tuple[str, ...]', reasons: 'tuple[str, ...]', metrics: 'dict[str, float]' = <factory>) -> None
```

RiskDecision(approved: 'bool', codes: 'tuple[str, ...]', reasons: 'tuple[str, ...]', metrics: 'dict[str, float]' = <factory>)

Defined in `asrquant.live`.

### `RiskPolicy`

**Kind:** class

```python
RiskPolicy(max_gross_leverage: 'float' = 1.0, max_position_weight: 'float' = 0.25, max_order_notional: 'float | None' = None, max_daily_turnover: 'float' = 2.0, max_drawdown: 'float' = 0.2, allow_short: 'bool' = True, minimum_cash: 'float' = 0.0) -> None
```

Pre-trade and session-level limits for algorithmic trading.

Defined in `asrquant.trading`.

### `RobustnessResult`

**Kind:** class

```python
RobustnessResult(baseline_metrics: 'pd.Series', implementation_audit: 'AuditResult', subperiod_metrics: 'pd.DataFrame', bootstrap: 'pd.Series', leakage_diagnostics: 'pd.Series', diagnostics: 'pd.Series', parameter_sweep: 'pd.DataFrame | None' = None) -> None
```

RobustnessResult(baseline_metrics: 'pd.Series', implementation_audit: 'AuditResult', subperiod_metrics: 'pd.DataFrame', bootstrap: 'pd.Series', leakage_diagnostics: 'pd.Series', diagnostics: 'pd.Series', parameter_sweep: 'pd.DataFrame | None' = None)

Defined in `asrquant.workflow`.

### `SABRCalibration`

**Kind:** class

```python
SABRCalibration(alpha: 'float', beta: 'float', rho: 'float', nu: 'float', rmse: 'float', fitted_vols: 'np.ndarray', success: 'bool') -> None
```

SABRCalibration(alpha: 'float', beta: 'float', rho: 'float', nu: 'float', rmse: 'float', fitted_vols: 'np.ndarray', success: 'bool')

Defined in `asrquant.interest_rates`.

### `SignalSpec`

**Kind:** class

```python
SignalSpec(feature: 'str', method: 'str' = 'threshold_pair', long_asset: 'str | None' = None, short_asset: 'str | None' = None, upper: 'float' = 1.0, lower: 'float | None' = None, direction: 'str' = 'positive', gross: 'float' = 1.0, signal_lag: 'int' = 1, neutral_when_inactive: 'bool' = True) -> None
```

Map one feature into target portfolio weights.

Defined in `asrquant.workflow`.

### `SimulationResult`

**Kind:** class

```python
SimulationResult(paths: 'pd.DataFrame', model: 'str', parameters: 'dict[str, Any]' = <factory>) -> None
```

Container for simulated paths with summaries and plotting helpers.

Defined in `asrquant.simulation`.

### `SourceExcerpt`

**Kind:** class

```python
SourceExcerpt(paper_id: 'str', page: 'int', text: 'str', section: 'str | None' = None) -> None
```

One source-linked passage from a paper.

Defined in `asrquant.literature`.

### `SQLiteAuditStore`

**Kind:** class

```python
SQLiteAuditStore(path: 'str | Path') -> 'None'
```

Append-only SQLite event log protected by a SHA-256 hash chain.

Defined in `asrquant.audit_store`.

### `SurfaceResult`

**Kind:** class

```python
SurfaceResult(x_values: 'np.ndarray', y_values: 'np.ndarray', z_values: 'np.ndarray', x_name: 'str' = 'x', y_name: 'str' = 'y', z_name: 'str' = 'value', frame_values: 'np.ndarray | None' = None, frame_name: 'str | None' = None, frame_parameters: 'pd.DataFrame | None' = None, metadata: 'dict[str, Any]' = <factory>) -> None
```

Static or animated response surface.

Defined in `asrquant.surfaces`.

### `VasicekCalibration`

**Kind:** class

```python
VasicekCalibration(kappa: 'float', theta: 'float', sigma: 'float', intercept: 'float', phi: 'float', residual_std: 'float', phi_std_error: 'float | None' = None, kappa_std_error: 'float | None' = None) -> None
```

VasicekCalibration(kappa: 'float', theta: 'float', sigma: 'float', intercept: 'float', phi: 'float', residual_std: 'float', phi_std_error: 'float | None' = None, kappa_std_error: 'float | None' = None)

Defined in `asrquant.interest_rates`.

### `VolatilityForecast`

**Kind:** class

```python
VolatilityForecast(model: 'str', conditional_volatility: 'pd.Series', forecast: 'pd.Series', model_result: 'object | None' = None) -> None
```

VolatilityForecast(model: 'str', conditional_volatility: 'pd.Series', forecast: 'pd.Series', model_result: 'object | None' = None)

Defined in `asrquant.volatility`.

### `WalkForwardMLResult`

**Kind:** class

```python
WalkForwardMLResult(estimator_name: 'str', task: 'str', predictions: 'pd.Series', actual: 'pd.Series', probabilities: 'pd.Series | None', fold_metrics: 'pd.DataFrame', aggregate_metrics: 'pd.Series', fitted_models: 'list[Any]') -> None
```

WalkForwardMLResult(estimator_name: 'str', task: 'str', predictions: 'pd.Series', actual: 'pd.Series', probabilities: 'pd.Series | None', fold_metrics: 'pd.DataFrame', aggregate_metrics: 'pd.Series', fitted_models: 'list[Any]')

Defined in `asrquant.machine_learning`.

### `WeeklyResearchCycle`

**Kind:** class

```python
WeeklyResearchCycle(candidate: 'ResearchCandidate', project: 'ResearchProject', launch_friday: 'date', publication_friday: 'date', plan: 'pd.DataFrame') -> None
```

One ASR Friday-to-Friday research cycle.

Defined in `asrquant.research_ops`.

### `YahooProvider`

**Kind:** class

```python
YahooProvider(auto_adjust: 'bool' = True) -> None
```

Optional yfinance connector for convenient research downloads.

Defined in `asrquant.providers`.

### `YieldCurveCalibration`

**Kind:** class

```python
YieldCurveCalibration(model: 'str', parameters: 'Mapping[str, float]', rmse: 'float', fitted_rates: 'np.ndarray', success: 'bool') -> None
```

Result of a parametric yield-curve fit.

Defined in `asrquant.interest_rates`.

## Functions

### `accrued_interest`

**Kind:** function

```python
accrued_interest(face: 'float', coupon_rate: 'float', frequency: 'int', fraction_since_coupon: 'float') -> 'float'
```

Linear accrued interest inside a coupon period.

Defined in `asrquant.interest_rates`.

### `arithmetic_brownian_motion`

**Kind:** function

```python
arithmetic_brownian_motion(initial: 'float' = 100.0, drift: 'float' = 0.0, volatility: 'float' = 0.2, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate arithmetic Brownian motion X_t=X_0+mu*t+sigma*W_t.

Defined in `asrquant.simulation`.

### `asian_option_mc`

**Kind:** function

```python
asian_option_mc(spot: 'float', strike: 'float', maturity: 'float', rate: 'float', volatility: 'float', option: 'str' = 'call', paths: 'int' = 50000, steps: 'int' = 252, dividend: 'float' = 0.0, random_state: 'int | None' = 0) -> 'MonteCarloPriceResult'
```

Arithmetic-average Asian option price under risk-neutral GBM.

Defined in `asrquant.simulation`.

### `autoregression_fit`

**Kind:** function

```python
autoregression_fit(series: 'pd.Series', lags: 'int | list[int]' = 1, trend: 'str' = 'c', *, old_names: 'bool' = False)
```

Fit an explicit AR(p) model with statsmodels AutoReg.

Defined in `asrquant.statistics`.

### `autoresearch`

**Kind:** function

```python
autoresearch(*, hypothesis: 'str | EconomicHypothesis', data: 'pd.DataFrame | str | Path', tradable_assets: 'Sequence[str]', topic: 'str | None' = None, feature_plan: 'FeaturePlan | Sequence[FeatureSpec] | str' = 'recommended', signal_spec: 'SignalSpec | None' = None, portfolio_spec: 'PortfolioSpec | None' = None, backtest_spec: 'BacktestSpec | None' = None, name: 'str' = 'ASRQuant automatic research project') -> 'ResearchProject'
```

Run the quantitative stages while preserving every generated plan.

Defined in `asrquant.workflow`.

### `bachelier_greeks`

**Kind:** function

```python
bachelier_greeks(forward: 'float | np.ndarray', strike: 'float | np.ndarray', maturity: 'float | np.ndarray', normal_volatility: 'float | np.ndarray', option: 'str' = 'call', discount: 'float | np.ndarray' = 1.0) -> 'dict[str, np.ndarray]'
```

Forward delta, gamma, vega, and theta for the Bachelier model.

Defined in `asrquant.derivatives`.

### `bachelier_price`

**Kind:** function

```python
bachelier_price(forward: 'float | np.ndarray', strike: 'float | np.ndarray', maturity: 'float | np.ndarray', normal_volatility: 'float | np.ndarray', option: 'str' = 'call', discount: 'float | np.ndarray' = 1.0)
```

Bachelier/normal-model European option value.

Defined in `asrquant.derivatives`.

### `basis_swap_pv`

**Kind:** function

```python
basis_swap_pv(discount: 'DiscountCurve', leg_a: 'ForwardCurve', leg_b: 'ForwardCurve', start: 'float', end: 'float', *, spread_a: 'float' = 0.0, notional: 'float' = 1.0) -> 'float'
```

PV of receiving projection leg A plus spread and paying leg B.

Defined in `asrquant.interest_rates`.

### `bermudan_lsm`

**Kind:** function

```python
bermudan_lsm(immediate_values: 'np.ndarray', state_paths: 'np.ndarray', interval_discounts: 'ArrayLike', *, polynomial_degree: 'int' = 2, valuation_discount: 'float' = 1.0) -> 'BermudanLSMResult'
```

Generic Longstaff-Schwartz engine for Bermudan-style exercise.

Defined in `asrquant.interest_rates`.

### `bilinear_interpolation`

**Kind:** function

```python
bilinear_interpolation(x_values: 'Sequence[float]', y_values: 'Sequence[float]', z_values: 'Any', *, extrapolate: 'bool' = False) -> 'ApproximationResult'
```

Bilinear interpolation on a regular two-dimensional grid.

Defined in `asrquant.approximation`.

### `black76_price`

**Kind:** function

```python
black76_price(forward: 'float | np.ndarray', strike: 'float | np.ndarray', maturity: 'float | np.ndarray', rate: 'float', volatility: 'float | np.ndarray', option: 'str' = 'call')
```

Black-76 European option on a forward or futures price.

Defined in `asrquant.derivatives`.

### `black_karasinski_paths`

**Kind:** function

```python
black_karasinski_paths(r0: 'float', mean_reversion: 'float', theta_log: 'float', sigma: 'float', maturity: 'float', *, steps: 'int' = 252, paths: 'int' = 10000, random_state: 'int | None' = 0) -> 'pd.DataFrame'
```

Simulate Black-Karasinski through an OU process for ``log r``.

Defined in `asrquant.interest_rates`.

### `black_scholes_greeks`

**Kind:** function

```python
black_scholes_greeks(spot: 'float | np.ndarray', strike: 'float | np.ndarray', maturity: 'float | np.ndarray', rate: 'float', volatility: 'float | np.ndarray', option: 'str' = 'call', dividend: 'float' = 0.0) -> 'dict[str, np.ndarray]'
```

Return analytic delta, gamma, vega, theta, and rho.

Defined in `asrquant.derivatives`.

### `black_scholes_price`

**Kind:** function

```python
black_scholes_price(spot: 'float | np.ndarray', strike: 'float | np.ndarray', maturity: 'float | np.ndarray', rate: 'float', volatility: 'float | np.ndarray', option: 'str' = 'call', dividend: 'float' = 0.0)
```

Black-Scholes-Merton European option value.

Defined in `asrquant.derivatives`.

### `bond_forward_price`

**Kind:** function

```python
bond_forward_price(discount: 'DiscountCurve', spot_dirty_price: 'float', delivery: 'float', coupon_times: 'ArrayLike' = (), coupon_cashflows: 'ArrayLike' = ()) -> 'float'
```

No-arbitrage dirty forward price of a coupon bond at delivery.

Defined in `asrquant.interest_rates`.

### `bond_price`

**Kind:** function

```python
bond_price(face: 'float', coupon_rate: 'float', maturity: 'float', yield_rate: 'float', frequency: 'int' = 2) -> 'float'
```

Price a fixed-coupon bond from its yield to maturity.

Defined in `asrquant.fixed_income`.

### `bond_price_from_curve`

**Kind:** function

```python
bond_price_from_curve(curve: 'DiscountCurve', face: 'float', coupon_rate: 'float', maturity: 'float', frequency: 'int' = 2) -> 'float'
```

Dirty price of a deterministic fixed-coupon bond from a discount curve.

Defined in `asrquant.interest_rates`.

### `bootstrap_discount_curve`

**Kind:** function

```python
bootstrap_discount_curve(*, deposits: 'pd.DataFrame | None' = None, fras: 'pd.DataFrame | None' = None, swaps: 'pd.DataFrame | None' = None, swap_frequency: 'int' = 2, interpolation: 'str' = 'log_linear', name: 'str' = 'bootstrapped') -> 'DiscountCurve'
```

Bootstrap a single-curve term structure from deposits, FRAs and par swaps.

Defined in `asrquant.interest_rates`.

### `bootstrap_projection_curve_from_swaps`

**Kind:** function

```python
bootstrap_projection_curve_from_swaps(discount: 'DiscountCurve', swaps: 'pd.DataFrame', *, tenor: 'float' = 0.5, fixed_frequency: 'int' = 2, name: 'str' = 'projection') -> 'ForwardCurve'
```

Sequentially bootstrap tenor forwards from par swaps under OIS discounting.

Defined in `asrquant.interest_rates`.

### `bootstrap_zero_curve`

**Kind:** function

```python
bootstrap_zero_curve(instruments: 'pd.DataFrame', frequency: 'int | None' = None) -> 'pd.Series'
```

Bootstrap periodically compounded zero rates from par coupon instruments.

Defined in `asrquant.fixed_income`.

### `build_manifest`

**Kind:** function

```python
build_manifest(result: 'Any', **metadata: 'Any') -> 'Manifest'
```

Build a machine-readable manifest from a BacktestResult.

Defined in `asrquant.provenance`.

### `calibrate_nelson_siegel`

**Kind:** function

```python
calibrate_nelson_siegel(maturities: 'ArrayLike', zero_rates: 'ArrayLike', *, initial: 'Sequence[float] | None' = None) -> 'YieldCurveCalibration'
```

Least-squares Nelson-Siegel calibration with positive decay parameter.

Defined in `asrquant.interest_rates`.

### `calibrate_sabr`

**Kind:** function

```python
calibrate_sabr(strikes: 'ArrayLike', market_vols: 'ArrayLike', forward: 'float', expiry: 'float', *, beta: 'float' = 0.5, shift: 'float' = 0.0, initial: 'tuple[float, float, float]' = (0.02, 0.0, 0.5)) -> 'SABRCalibration'
```

Least-squares SABR calibration with fixed beta.

Defined in `asrquant.interest_rates`.

### `calibrate_svensson`

**Kind:** function

```python
calibrate_svensson(maturities: 'ArrayLike', zero_rates: 'ArrayLike', *, initial: 'Sequence[float] | None' = None) -> 'YieldCurveCalibration'
```

Least-squares Nelson-Siegel-Svensson calibration.

Defined in `asrquant.interest_rates`.

### `calibrate_vasicek`

**Kind:** function

```python
calibrate_vasicek(rates: 'ArrayLike', dt: 'float' = 0.003968253968253968) -> 'VasicekCalibration'
```

Estimate Vasicek parameters from an equally spaced short-rate series via AR(1).

Defined in `asrquant.interest_rates`.

### `cap_floor_price`

**Kind:** function

```python
cap_floor_price(discount: 'DiscountCurve', periods: 'Sequence[tuple[float, float]]', strike: 'float', volatilities: 'float | Sequence[float]', *, notional: 'float' = 1.0, option: 'str' = 'cap', model: 'str' = 'black76', projection: 'ForwardCurve | None' = None, shift: 'float' = 0.0) -> 'float'
```

Price a cap/floor as a portfolio of caplets/floorlets.

Defined in `asrquant.interest_rates`.

### `caplet_price`

**Kind:** function

```python
caplet_price(discount: 'DiscountCurve', start: 'float', end: 'float', strike: 'float', volatility: 'float', *, notional: 'float' = 1.0, option: 'str' = 'caplet', model: 'str' = 'black76', projection: 'ForwardCurve | None' = None, shift: 'float' = 0.0) -> 'float'
```

Price one caplet/floorlet under Black-76, shifted Black or Bachelier.

Defined in `asrquant.interest_rates`.

### `carry_roll_down`

**Kind:** function

```python
carry_roll_down(curve_today: 'DiscountCurve', maturity: 'float', horizon: 'float', *, face: 'float' = 1.0) -> 'pd.Series'
```

Static-curve carry/roll decomposition for a zero-coupon bond.

Defined in `asrquant.interest_rates`.

### `cir_process`

**Kind:** function

```python
cir_process(initial: 'float' = 0.03, speed: 'float' = 1.5, mean: 'float' = 0.04, volatility: 'float' = 0.2, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate a non-negative CIR process with full-truncation Euler.

Defined in `asrquant.simulation`.

### `cir_zero_coupon_bond`

**Kind:** function

```python
cir_zero_coupon_bond(r_t: 'float', t: 'float', maturity: 'float', kappa: 'float', theta: 'float', sigma: 'float') -> 'float'
```

CIR zero-coupon bond price in affine closed form.

Defined in `asrquant.interest_rates`.

### `clean_price`

**Kind:** function

```python
clean_price(dirty_price: 'float', accrued: 'float') -> 'float'
```

Defined in `asrquant.interest_rates`.

### `clean_prices`

**Kind:** function

```python
clean_prices(prices: 'pd.Series | pd.DataFrame', policy: 'MissingDataPolicy | str' = <MissingDataPolicy.RAISE: 'raise'>) -> 'pd.DataFrame'
```

Validate positive prices and apply the selected missing-data policy.

Defined in `asrquant.data`.

### `compare_backtests`

**Kind:** function

```python
compare_backtests(results: 'dict[str, BacktestResult]') -> 'pd.DataFrame'
```

Compare any number of backtests on a common metric table.

Defined in `asrquant.backtest`.

### `compounded_overnight_rate`

**Kind:** function

```python
compounded_overnight_rate(rates: 'ArrayLike', accruals: 'ArrayLike') -> 'float'
```

Geometrically compound realized overnight/RFR fixings over accrual periods.

Defined in `asrquant.interest_rates`.

### `convexity`

**Kind:** function

```python
convexity(face: 'float', coupon_rate: 'float', maturity: 'float', yield_rate: 'float', frequency: 'int' = 2) -> 'float'
```

Standard discrete-compounding bond convexity.

Defined in `asrquant.fixed_income`.

### `correlated_gbm`

**Kind:** function

```python
correlated_gbm(initials: 'np.ndarray | list[float]', drifts: 'np.ndarray | list[float]', volatilities: 'np.ndarray | list[float]', correlation: 'np.ndarray', maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'np.ndarray'
```

Simulate correlated GBM with shape (steps+1, paths, assets).

Defined in `asrquant.simulation`.

### `correlated_normal`

**Kind:** function

```python
correlated_normal(mean: 'Sequence[float] | Array', covariance: 'Array', n_scenarios: 'int' = 10000, *, random_state: 'int | None' = 0) -> 'Array'
```

Generate correlated Gaussian vectors using a Cholesky factor.

Defined in `asrquant.monte_carlo`.

### `create_model`

**Kind:** function

```python
create_model(name: 'str', *, task: 'str | None' = None, **kwargs: 'Any')
```

Create an estimator from a stable ASRQuant name.

Defined in `asrquant.models`.

### `cross_currency_zero_coupon_pv`

**Kind:** function

```python
cross_currency_zero_coupon_pv(spot_fx: 'float', domestic_discount: 'DiscountCurve', foreign_discount: 'DiscountCurve', maturity: 'float', *, domestic_notional: 'float', foreign_notional: 'float', receive_foreign: 'bool' = True) -> 'float'
```

PV in domestic currency of exchanging two notionals at maturity.

Defined in `asrquant.interest_rates`.

### `crr_binomial_price`

**Kind:** function

```python
crr_binomial_price(spot: 'float', strike: 'float', maturity: 'float', rate: 'float', volatility: 'float', option: 'str' = 'call', steps: 'int' = 500, dividend: 'float' = 0.0, american: 'bool' = False) -> 'float'
```

Cox-Ross-Rubinstein binomial price for European or American options.

Defined in `asrquant.derivatives`.

### `cubic_spline`

**Kind:** function

```python
cubic_spline(x: 'Any', y: 'Any', *, boundary_condition: 'str' = 'not-a-knot', extrapolate: 'bool' = False) -> 'ApproximationResult'
```

One-dimensional cubic spline with continuous first and second derivatives.

Defined in `asrquant.approximation`.

### `curve_interpolation_risk`

**Kind:** function

```python
curve_interpolation_risk(times: 'ArrayLike', zero_rates: 'ArrayLike', evaluation_grid: 'ArrayLike | None' = None) -> 'pd.DataFrame'
```

Compare forward rates induced by three transparent interpolation choices.

Defined in `asrquant.interest_rates`.

### `curve_scenario`

**Kind:** function

```python
curve_scenario(curve: 'DiscountCurve', *, parallel_bp: 'float' = 0.0, slope_bp: 'float' = 0.0, curvature_bp: 'float' = 0.0) -> 'DiscountCurve'
```

Apply transparent parallel/slope/curvature shocks to node zero rates.

Defined in `asrquant.interest_rates`.

### `data_fingerprint`

**Kind:** function

```python
data_fingerprint(data: 'pd.Series | pd.DataFrame') -> 'str'
```

Create a stable SHA-256 fingerprint of values, index, and columns.

Defined in `asrquant.data`.

### `data_quality_report`

**Kind:** function

```python
data_quality_report(data: 'pd.Series | pd.DataFrame') -> 'pd.Series'
```

Summarize missingness, duplicates, monotonicity, and sampling gaps.

Defined in `asrquant.data`.

### `date_range`

**Kind:** function

```python
date_range(start: 'Any' = None, end: 'Any' = None, periods: 'int | None' = None, freq: 'str | None' = None)
```

Defined in `asrquant.easy`.

### `dirty_price`

**Kind:** function

```python
dirty_price(clean: 'float', accrued: 'float') -> 'float'
```

Defined in `asrquant.interest_rates`.

### `discount_factor`

**Kind:** function

```python
discount_factor(rate: 'ArrayLike', maturity: 'ArrayLike', compounding: 'str | int' = 'continuous')
```

Convert zero rates to discount factors under common compounding rules.

Defined in `asrquant.interest_rates`.

### `discount_process`

**Kind:** function

```python
discount_process(values: 'pd.Series', rate: 'float' = 0.0, annualization: 'int' = 252) -> 'pd.Series'
```

Discount a value process by a continuously compounded constant rate.

Defined in `asrquant.martingales`.

### `dollar_convexity`

**Kind:** function

```python
dollar_convexity(pricer, curve: 'DiscountCurve', bump: 'float' = 0.0001) -> 'float'
```

Second derivative of PV with respect to a parallel zero-rate shift.

Defined in `asrquant.interest_rates`.

### `download`

**Kind:** function

```python
download(provider: 'str | MarketDataProvider', symbols: 'str | Sequence[str]', *, field: 'str' = 'Close', **kwargs) -> 'pd.DataFrame'
```

Download one or more symbols into one aligned price/value panel.

Defined in `asrquant.providers`.

### `dv01`

**Kind:** function

```python
dv01(pricer, curve: 'DiscountCurve', bump: 'float' = 0.0001) -> 'float'
```

Dollar value of a one-basis-point *decrease* in rates (central difference).

Defined in `asrquant.interest_rates`.

### `empirical_quantile`

**Kind:** function

```python
empirical_quantile(values: 'Any', level: 'float' = 0.95) -> 'float'
```

Empirical quantile of a one-dimensional sample.

Defined in `asrquant.monte_carlo`.

### `euler_maruyama`

**Kind:** function

```python
euler_maruyama(drift: 'Callable[..., Any]', diffusion: 'Callable[..., Any]', initial: 'float | Sequence[float] | Array', *, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 10000, random_state: 'int | None' = 0, parameters: 'Mapping[str, Any] | None' = None) -> 'Array'
```

Generic scalar or vector Euler-Maruyama SDE simulator.

Defined in `asrquant.monte_carlo`.

### `european_option_mc`

**Kind:** function

```python
european_option_mc(spot: 'float', strike: 'float', maturity: 'float', rate: 'float', volatility: 'float', option: 'str' = 'call', paths: 'int' = 100000, steps: 'int' = 1, dividend: 'float' = 0.0, antithetic: 'bool' = True, random_state: 'int | None' = 0) -> 'MonteCarloPriceResult'
```

Risk-neutral Monte Carlo price for a European option under GBM.

Defined in `asrquant.simulation`.

### `evaluate_parameter_surface`

**Kind:** function

```python
evaluate_parameter_surface(function: 'Callable[..., Any]', parameter_grid: 'Mapping[str, ArrayLike]', *, x: 'str | None' = None, y: 'str | None' = None, animate_by: 'str | Sequence[str] | None' = None, z_name: 'str' = 'value', metric: 'MetricSelector' = None, fixed_params: 'Mapping[str, Any] | None' = None, vectorized: 'bool' = False, call_style: 'str' = 'keyword', n_jobs: 'int' = 1, error_policy: 'str' = 'raise', max_evaluations: 'int' = 1000000, progress: 'ProgressCallback | None' = None) -> 'SurfaceResult'
```

Evaluate an arbitrary finite parameter experiment as a surface family.

Defined in `asrquant.surfaces`.

### `evaluate_surface`

**Kind:** function

```python
evaluate_surface(function: 'Callable[..., Any]', x_values: 'ArrayLike', y_values: 'ArrayLike', *, x_name: 'str' = 'x', y_name: 'str' = 'y', z_name: 'str' = 'value', metric: 'MetricSelector' = None, fixed_params: 'Mapping[str, Any] | None' = None, vectorized: 'bool' = False, call_style: 'str' = 'keyword', n_jobs: 'int' = 1, error_policy: 'str' = 'raise') -> 'SurfaceResult'
```

Backward-compatible two-dimensional surface evaluator.

Defined in `asrquant.surfaces`.

### `evaluate_surface_animation`

**Kind:** function

```python
evaluate_surface_animation(function: 'Callable[..., Any]', x_values: 'ArrayLike', y_values: 'ArrayLike', frame_values: 'ArrayLike', *, x_name: 'str' = 'x', y_name: 'str' = 'y', frame_name: 'str' = 'frame', z_name: 'str' = 'value', metric: 'MetricSelector' = None, fixed_params: 'Mapping[str, Any] | None' = None, vectorized: 'bool' = False, call_style: 'str' = 'keyword', n_jobs: 'int' = 1, error_policy: 'str' = 'raise') -> 'SurfaceResult'
```

Backward-compatible one-parameter animation evaluator.

Defined in `asrquant.surfaces`.

### `event_probability`

**Kind:** function

```python
event_probability(values: 'Any', event: 'Callable[[Array], Any] | None' = None) -> 'float'
```

Estimate a probability using an indicator or an already Boolean sample.

Defined in `asrquant.monte_carlo`.

### `ewma_volatility`

**Kind:** function

```python
ewma_volatility(returns: 'pd.Series', decay: 'float' = 0.94, annualization: 'int' = 252) -> 'pd.Series'
```

RiskMetrics-style exponentially weighted volatility.

Defined in `asrquant.volatility`.

### `finite_difference_gradient`

**Kind:** function

```python
finite_difference_gradient(function: 'Callable[..., float]', point: 'Sequence[float]', *, step: 'float' = 1e-05) -> 'np.ndarray'
```

Centered finite-difference gradient of an arbitrary scalar function.

Defined in `asrquant.approximation`.

### `finite_difference_hessian`

**Kind:** function

```python
finite_difference_hessian(function: 'Callable[..., float]', point: 'Sequence[float]', *, step: 'float' = 0.0001) -> 'np.ndarray'
```

Centered finite-difference Hessian of an arbitrary scalar function.

Defined in `asrquant.approximation`.

### `fit`

**Kind:** function

```python
fit(x: 'Any', y: 'Any', *, method: 'str' = 'ols', degree: 'int' = 2, **kwargs: 'Any')
```

Fit a common statistical model from plain Python or pandas inputs.

Defined in `asrquant.easy`.

### `forward_discount_factor`

**Kind:** function

```python
forward_discount_factor(p_start: 'ArrayLike', p_end: 'ArrayLike')
```

Return ``P(0,T2)/P(0,T1)``.

Defined in `asrquant.interest_rates`.

### `forward_rate_from_discounts`

**Kind:** function

```python
forward_rate_from_discounts(p_start: 'ArrayLike', p_end: 'ArrayLike', start: 'ArrayLike', end: 'ArrayLike', compounding: 'str' = 'simple')
```

Return a forward rate implied by two discount factors.

Defined in `asrquant.interest_rates`.

### `forward_target`

**Kind:** function

```python
forward_target(prices: 'pd.Series', horizon: 'int' = 1, classification: 'bool' = False) -> 'pd.Series'
```

Create a forward return or direction target aligned at decision time.

Defined in `asrquant.machine_learning`.

### `fra_forward_rate`

**Kind:** function

```python
fra_forward_rate(curve: 'DiscountCurve', start: 'float', end: 'float') -> 'float'
```

Defined in `asrquant.interest_rates`.

### `fra_pv`

**Kind:** function

```python
fra_pv(curve: 'DiscountCurve', start: 'float', end: 'float', strike: 'float', *, notional: 'float' = 1.0, position: 'str' = 'receive_float', settlement: 'str' = 'end', projection: 'ForwardCurve | None' = None) -> 'float'
```

Present value of a FRA.

Defined in `asrquant.interest_rates`.

### `frame`

**Kind:** function

```python
frame(data: 'Any' = None, *, index: 'Any' = None, columns: 'Any' = None) -> 'pd.DataFrame'
```

Construct a DataFrame through ASRQuant for one-import workflows.

Defined in `asrquant.easy`.

### `fx_forward_rate`

**Kind:** function

```python
fx_forward_rate(spot_fx: 'float', domestic_discount: 'DiscountCurve', foreign_discount: 'DiscountCurve', maturity: 'float') -> 'float'
```

Covered-interest-parity FX forward, quoted domestic currency per foreign.

Defined in `asrquant.interest_rates`.

### `garch_forecast`

**Kind:** function

```python
garch_forecast(returns: 'pd.Series', p: 'int' = 1, q: 'int' = 1, horizon: 'int' = 5, distribution: 'str' = 't', annualization: 'int' = 252) -> 'VolatilityForecast'
```

Fit GARCH(p,q) through the optional ``arch`` dependency.

Defined in `asrquant.volatility`.

### `garman_klass_volatility`

**Kind:** function

```python
garman_klass_volatility(open_: 'pd.Series', high: 'pd.Series', low: 'pd.Series', close: 'pd.Series', window: 'int' = 21, annualization: 'int' = 252) -> 'pd.Series'
```

Rolling Garman-Klass OHLC volatility estimator.

Defined in `asrquant.volatility`.

### `gaussian_process`

**Kind:** function

```python
gaussian_process(x: 'Any', y: 'Any', *, length_scale: 'float | Sequence[float]' = 1.0, noise: 'float' = 1e-06, normalize_y: 'bool' = True, random_state: 'int | None' = 0) -> 'ApproximationResult'
```

Gaussian-process surrogate with predictive mean and standard deviation.

Defined in `asrquant.approximation`.

### `geometric_brownian_motion`

**Kind:** function

```python
geometric_brownian_motion(initial: 'float' = 100.0, drift: 'float' = 0.05, volatility: 'float' = 0.2, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0, antithetic: 'bool' = False) -> 'SimulationResult'
```

Simulate exact-discretization geometric Brownian motion paths.

Defined in `asrquant.simulation`.

### `get_provider`

**Kind:** function

```python
get_provider(name: 'str', **kwargs) -> 'MarketDataProvider'
```

Instantiate a provider by name.

Defined in `asrquant.providers`.

### `hagan_sabr_volatility`

**Kind:** function

```python
hagan_sabr_volatility(forward: 'float', strike: 'float', expiry: 'float', alpha: 'float', beta: 'float', rho: 'float', nu: 'float', *, shift: 'float' = 0.0) -> 'float'
```

Hagan et al. lognormal SABR implied-volatility approximation.

Defined in `asrquant.interest_rates`.

### `hedging_loss`

**Kind:** function

```python
hedging_loss(payoff: 'Any', prices: 'Any', positions: 'Any', *, premium: 'float' = 0.0, cost_rate: 'float' = 0.0, initial_position: 'float | Array' = 0.0) -> 'Array'
```

Pathwise hedging loss including proportional transaction costs.

Defined in `asrquant.monte_carlo`.

### `heston_process`

**Kind:** function

```python
heston_process(initial: 'float' = 100.0, drift: 'float' = 0.05, initial_variance: 'float' = 0.04, mean_reversion: 'float' = 2.0, long_variance: 'float' = 0.04, vol_of_vol: 'float' = 0.5, correlation: 'float' = -0.7, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 2000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate Heston prices using full-truncation Euler for variance.

Defined in `asrquant.simulation`.

### `hjm_one_factor_paths`

**Kind:** function

```python
hjm_one_factor_paths(maturities: 'ArrayLike', initial_forwards: 'ArrayLike', volatilities: 'ArrayLike', horizon: 'float', *, steps: 'int' = 100, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'np.ndarray'
```

Discrete one-factor HJM forward-curve simulation under the risk-neutral measure.

Defined in `asrquant.interest_rates`.

### `ho_lee_paths`

**Kind:** function

```python
ho_lee_paths(r0: 'float', theta: 'float', sigma: 'float', maturity: 'float', *, steps: 'int' = 252, paths: 'int' = 10000, random_state: 'int | None' = 0) -> 'pd.DataFrame'
```

Euler simulation of ``dr = theta dt + sigma dW``.

Defined in `asrquant.interest_rates`.

### `hull_white_paths`

**Kind:** function

```python
hull_white_paths(r0: 'float', mean_reversion: 'float', theta: 'float', sigma: 'float', maturity: 'float', *, steps: 'int' = 252, paths: 'int' = 10000, random_state: 'int | None' = 0) -> 'pd.DataFrame'
```

Simulate the one-factor Hull-White/Vasicek SDE with constant theta.

Defined in `asrquant.interest_rates`.

### `implementation_audit`

**Kind:** function

```python
implementation_audit(prices: 'pd.Series | pd.DataFrame', target_weights: 'pd.Series | pd.DataFrame', base_spec: 'BacktestSpec | None' = None, execution_delays: 'Iterable[int]' = (0, 1), linear_costs_bps: 'Iterable[float]' = (0.0, 5.0, 10.0), rebalances: 'Iterable[str]' = ('bar',)) -> 'AuditResult'
```

Re-run one logical strategy under a grid of defensible conventions.

Defined in `asrquant.audit`.

### `implied_rate_volatility`

**Kind:** function

```python
implied_rate_volatility(price: 'float', pricer, *, lower: 'float' = 1e-08, upper: 'float' = 5.0) -> 'float'
```

Generic scalar implied-volatility inversion for a rate-option pricer.

Defined in `asrquant.interest_rates`.

### `implied_volatility`

**Kind:** function

```python
implied_volatility(market_price: 'float', spot: 'float', strike: 'float', maturity: 'float', rate: 'float', option: 'str' = 'call', dividend: 'float' = 0.0, model: 'str' = 'black_scholes') -> 'float'
```

Invert Black-Scholes-Merton, Black-76, or Bachelier by bracketing.

Defined in `asrquant.derivatives`.

### `kernel_regression`

**Kind:** function

```python
kernel_regression(x: 'Any', y: 'Any', *, bandwidth: 'float' = 1.0) -> 'ApproximationResult'
```

Gaussian Nadaraya-Watson kernel regression in one or several dimensions.

Defined in `asrquant.approximation`.

### `key_rate_dv01`

**Kind:** function

```python
key_rate_dv01(pricer, curve: 'DiscountCurve', key_maturities: 'Sequence[float]', bump: 'float' = 0.0001) -> 'pd.Series'
```

Bucketed key-rate DV01 using partition-preserving triangular pillar bumps.

Defined in `asrquant.interest_rates`.

### `key_rate_hedge`

**Kind:** function

```python
key_rate_hedge(target_exposure: 'ArrayLike', hedge_exposures: 'ArrayLike', *, ridge: 'float' = 0.0) -> 'HedgeSolution'
```

Solve hedge weights so hedge key-rate exposures offset a target vector.

Defined in `asrquant.interest_rates`.

### `lag_features`

**Kind:** function

```python
lag_features(data: 'pd.Series | pd.DataFrame', lags: 'int | list[int]' = (1, 2, 5, 10, 20), *, include_current: 'bool' = False) -> 'pd.DataFrame'
```

Create explicitly lagged features without backward filling.

Defined in `asrquant.machine_learning`.

### `level_slope_curvature`

**Kind:** function

```python
level_slope_curvature(yields: 'pd.DataFrame') -> 'pd.DataFrame'
```

Simple interpretable level/slope/curvature factors from ordered maturities.

Defined in `asrquant.interest_rates`.

### `linear_interpolation`

**Kind:** function

```python
linear_interpolation(x: 'Any', y: 'Any', *, extrapolate: 'bool' = False) -> 'ApproximationResult'
```

Piecewise-linear one-dimensional interpolation.

Defined in `asrquant.approximation`.

### `lmm_terminal_measure_paths`

**Kind:** function

```python
lmm_terminal_measure_paths(initial_forwards: 'ArrayLike', accruals: 'ArrayLike', volatilities: 'ArrayLike', correlation: 'np.ndarray', horizon: 'float', *, steps: 'int' = 100, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'np.ndarray'
```

Euler-log simulation of a lognormal LIBOR Market Model under terminal measure.

Defined in `asrquant.interest_rates`.

### `load_prices`

**Kind:** function

```python
load_prices(path: 'str | Path', date_column: 'str | None' = None, *, columns: 'Sequence[str] | None' = None, sheet_name: 'str | int' = 0) -> 'pd.DataFrame'
```

Load price/value panels from CSV, Parquet, Excel, JSON, or Feather.

Defined in `asrquant.data`.

### `load_sql`

**Kind:** function

```python
load_sql(query: 'str', connection, date_column: 'str', columns: 'Sequence[str] | None' = None) -> 'pd.DataFrame'
```

Load a price/value panel from any pandas-compatible SQL connection.

Defined in `asrquant.data`.

### `log_returns`

**Kind:** function

```python
log_returns(prices: 'pd.Series | pd.DataFrame') -> 'pd.DataFrame'
```

Compute log returns.

Defined in `asrquant.data`.

### `macaulay_duration`

**Kind:** function

```python
macaulay_duration(face: 'float', coupon_rate: 'float', maturity: 'float', yield_rate: 'float', frequency: 'int' = 2) -> 'float'
```

Macaulay duration in years.

Defined in `asrquant.fixed_income`.

### `martingale_diagnostics`

**Kind:** function

```python
martingale_diagnostics(values: 'pd.Series', *, rate: 'float' = 0.0, annualization: 'int' = 252, lags: 'int' = 10) -> 'MartingaleResult'
```

Run mean-increment, predictability, and serial-correlation diagnostics.

Defined in `asrquant.martingales`.

### `maturity_to_years`

**Kind:** function

```python
maturity_to_years(maturity: 'str | float | int') -> 'float'
```

Convert a compact money-market maturity such as ``3M`` or ``10Y`` to years.

Defined in `asrquant.interest_rates`.

### `mean_confidence_interval`

**Kind:** function

```python
mean_confidence_interval(values: 'Any', confidence: 'float' = 0.95) -> 'tuple[float, float]'
```

Normal-approximation confidence interval for a Monte Carlo mean.

Defined in `asrquant.monte_carlo`.

### `merton_jump_diffusion`

**Kind:** function

```python
merton_jump_diffusion(initial: 'float' = 100.0, drift: 'float' = 0.05, volatility: 'float' = 0.2, jump_intensity: 'float' = 0.5, jump_mean: 'float' = -0.1, jump_volatility: 'float' = 0.2, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 2000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate Merton lognormal jump diffusion.

Defined in `asrquant.simulation`.

### `modified_duration`

**Kind:** function

```python
modified_duration(face: 'float', coupon_rate: 'float', maturity: 'float', yield_rate: 'float', frequency: 'int' = 2) -> 'float'
```

Modified duration in years.

Defined in `asrquant.fixed_income`.

### `monte_carlo_expected_shortfall`

**Kind:** function

```python
monte_carlo_expected_shortfall(losses: 'Any', level: 'float' = 0.95) -> 'float'
```

Monte Carlo Expected Shortfall/CVaR for positive losses.

Defined in `asrquant.monte_carlo`.

### `monte_carlo_parameter_surface`

**Kind:** function

```python
monte_carlo_parameter_surface(generator: 'Generator', quantity: 'Quantity | None', parameter_grid: 'Mapping[str, Sequence[Any]]', *, x: 'str', y: 'str', animate_by: 'str | Sequence[str] | None' = None, estimator: 'Reducer' = 'mean', level: 'float' = 0.95, confidence: 'float' = 0.95, n_scenarios: 'int' = 10000, random_state: 'int | None' = 0, fixed_params: 'Mapping[str, Any] | None' = None, z_name: 'str | None' = None, n_jobs: 'int' = 1) -> 'SurfaceResult'
```

Evaluate any Monte Carlo statistic over a 2D or animated parameter grid.

Defined in `asrquant.monte_carlo`.

### `monte_carlo_price`

**Kind:** function

```python
monte_carlo_price(simulation: 'SimulationResult', payoff: 'Callable[[np.ndarray], np.ndarray]', *, rate: 'float' = 0.0, maturity: 'float | None' = None, confidence: 'float' = 0.95) -> 'MonteCarloPriceResult'
```

Price a terminal-payoff claim from a SimulationResult.

Defined in `asrquant.simulation`.

### `monte_carlo_value_at_risk`

**Kind:** function

```python
monte_carlo_value_at_risk(losses: 'Any', level: 'float' = 0.95) -> 'float'
```

Monte Carlo VaR for a sample expressed directly as positive losses.

Defined in `asrquant.monte_carlo`.

### `nelson_siegel_yield`

**Kind:** function

```python
nelson_siegel_yield(maturity: 'ArrayLike', beta0: 'float', beta1: 'float', beta2: 'float', tau: 'float')
```

Evaluate a Nelson-Siegel continuously-compounded zero-yield curve.

Defined in `asrquant.interest_rates`.

### `no_arbitrage_curve_diagnostics`

**Kind:** function

```python
no_arbitrage_curve_diagnostics(curve: 'DiscountCurve', *, tolerance: 'float' = 1e-10) -> 'pd.Series'
```

Basic curve sanity checks useful before pricing or research.

Defined in `asrquant.interest_rates`.

### `normal_samples`

**Kind:** function

```python
normal_samples(mean: 'float' = 0.0, standard_deviation: 'float' = 1.0, size: 'int | tuple[int, ...]' = 10000, *, random_state: 'int | None' = 0) -> 'Array'
```

Generate ``mean + standard_deviation * Z`` with standard-normal Z.

Defined in `asrquant.monte_carlo`.

### `ois_par_rate`

**Kind:** function

```python
ois_par_rate(discount: 'DiscountCurve', start: 'float', end: 'float', *, fixed_frequency: 'int' = 1) -> 'float'
```

Par fixed rate of a standard OIS under single-curve discounting.

Defined in `asrquant.interest_rates`.

### `ois_pv`

**Kind:** function

```python
ois_pv(discount: 'DiscountCurve', start: 'float', end: 'float', fixed_rate: 'float', *, notional: 'float' = 1.0, fixed_frequency: 'int' = 1, position: 'str' = 'payer') -> 'float'
```

PV of a standard fixed-versus-compounded-overnight OIS.

Defined in `asrquant.interest_rates`.

### `open_lab`

**Kind:** function

```python
open_lab(source: 'Any' = None, *, provider: 'str | None' = None, symbols: 'str | Sequence[str] | None' = None, date_column: 'str | None' = None, columns: 'Sequence[str] | None' = None, missing_data: 'str' = 'raise', **kwargs: 'Any')
```

Create a QuantLab from in-memory data, a file, or a market-data provider.

Defined in `asrquant.easy`.

### `ornstein_uhlenbeck`

**Kind:** function

```python
ornstein_uhlenbeck(initial: 'float' = 0.0, speed: 'float' = 2.0, mean: 'float' = 0.0, volatility: 'float' = 0.2, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate an Ornstein-Uhlenbeck mean-reverting process by Euler steps.

Defined in `asrquant.simulation`.

### `paper_trade`

**Kind:** function

```python
paper_trade(prices: 'pd.DataFrame', target_weights: 'pd.DataFrame', *, initial_capital: 'float' = 100000.0, commission_bps: 'float' = 0.0, slippage_bps: 'float' = 0.0, policy: 'RiskPolicy | None' = None, annualization: 'int' = 252) -> 'PaperTradingResult'
```

One-call paper trading simulation from target weights.

Defined in `asrquant.trading`.

### `parkinson_volatility`

**Kind:** function

```python
parkinson_volatility(high: 'pd.Series', low: 'pd.Series', window: 'int' = 21, annualization: 'int' = 252) -> 'pd.Series'
```

Rolling Parkinson high-low volatility estimator.

Defined in `asrquant.volatility`.

### `payment_schedule`

**Kind:** function

```python
payment_schedule(start: 'float', end: 'float', frequency: 'int' = 2) -> 'np.ndarray'
```

Generate a regular year-fraction payment schedule including ``end``.

Defined in `asrquant.interest_rates`.

### `price_option`

**Kind:** function

```python
price_option(model: 'str' = 'black_scholes', **kwargs) -> 'OptionPrice'
```

Unified option-pricing dispatcher returning a standard result object.

Defined in `asrquant.derivatives`.

### `projection_curve_from_discount`

**Kind:** function

```python
projection_curve_from_discount(discount: 'DiscountCurve', tenor: 'float', *, name: 'str | None' = None) -> 'ForwardCurve'
```

Create a tenor forward curve implied by one discount curve.

Defined in `asrquant.interest_rates`.

### `proportional_transaction_cost`

**Kind:** function

```python
proportional_transaction_cost(prices: 'Any', positions: 'Any', cost_rate: 'float', *, initial_position: 'float | Array' = 0.0) -> 'Array'
```

Pathwise proportional trading cost ``sum kappa*S*|delta_t-delta_{t-1}|``.

Defined in `asrquant.monte_carlo`.

### `rate_from_future_price`

**Kind:** function

```python
rate_from_future_price(price: 'float') -> 'float'
```

Defined in `asrquant.interest_rates`.

### `rate_future_price`

**Kind:** function

```python
rate_future_price(rate: 'float') -> 'float'
```

IMM-style quoted rate future price ``100 - 100*rate``.

Defined in `asrquant.interest_rates`.

### `rates_curriculum`

**Kind:** function

```python
rates_curriculum() -> 'pd.DataFrame'
```

Return the built-in Interest Rate Derivatives Quant learning/research map.

Defined in `asrquant.interest_rates`.

### `rates_exercises`

**Kind:** function

```python
rates_exercises(*, level: 'str | None' = None, topic: 'str | None' = None) -> 'pd.DataFrame'
```

Return the built-in exercise bank for Interest Rate Derivatives Quant training.

Defined in `asrquant.interest_rates`.

### `rbf_interpolation`

**Kind:** function

```python
rbf_interpolation(x: 'Any', y: 'Any', *, kernel: 'str' = 'thin_plate_spline', smoothing: 'float' = 0.0, epsilon: 'float | None' = None) -> 'ApproximationResult'
```

Radial-basis interpolation for irregular one- or multi-dimensional samples.

Defined in `asrquant.approximation`.

### `read_table`

**Kind:** function

```python
read_table(path: 'str | Path', **kwargs: 'Any') -> 'pd.DataFrame'
```

Read a general tabular file without importing pandas directly.

Defined in `asrquant.easy`.

### `realized_volatility`

**Kind:** function

```python
realized_volatility(returns: 'pd.Series', window: 'int' = 21, annualization: 'int' = 252) -> 'pd.Series'
```

Rolling close-to-close realized volatility.

Defined in `asrquant.volatility`.

### `regime_switching_prices`

**Kind:** function

```python
regime_switching_prices(periods: 'int' = 1500, assets: 'int' = 4, start: 'float' = 100.0, annualization: 'int' = 252, random_state: 'int | None' = 7) -> 'pd.DataFrame'
```

Generate a reproducible two-regime correlated price panel.

Defined in `asrquant.simulation`.

### `regression_metrics`

**Kind:** function

```python
regression_metrics(actual: 'Any', predicted: 'Any') -> 'pd.Series'
```

RMSE, MAE, and R-squared for model validation.

Defined in `asrquant.approximation`.

### `report`

**Kind:** function

```python
report(value: 'Any', output: 'str | Path', *, title: 'str | None' = None) -> 'Path'
```

Create a report from a compatible ASRQuant result object.

Defined in `asrquant.easy`.

### `resample_ohlcv`

**Kind:** function

```python
resample_ohlcv(data: 'pd.DataFrame', rule: 'str') -> 'pd.DataFrame'
```

Resample canonical OHLCV data with finance-consistent aggregations.

Defined in `asrquant.data`.

### `research_note_template`

**Kind:** function

```python
research_note_template(candidate: 'ResearchCandidate') -> 'str'
```

Defined in `asrquant.research_ops`.

### `research_project`

**Kind:** function

```python
research_project(*, papers: 'str | Path | Sequence[str | Path] | None' = None, hypothesis: 'str | EconomicHypothesis | None' = None, topic: 'str | None' = None, name: 'str' = 'ASRQuant research project') -> 'ResearchProject'
```

Create a project from papers, a hypothesis, or both.

Defined in `asrquant.workflow`.

### `resolve_estimator`

**Kind:** function

```python
resolve_estimator(estimator: 'Any' = 'ridge', *, task: 'str' = 'regression', model_params: 'dict[str, Any] | None' = None)
```

Resolve an ASRQuant model name or pass through a fitted-compatible estimator.

Defined in `asrquant.machine_learning`.

### `response_regression`

**Kind:** function

```python
response_regression(x: 'Any', y: 'Any', *, method: 'str' = 'polynomial', degree: 'int' = 2, alpha: 'float' = 1.0) -> 'ApproximationResult'
```

Linear, polynomial, ridge, or lasso response-surface regression.

Defined in `asrquant.approximation`.

### `run_backtest`

**Kind:** function

```python
run_backtest(prices: 'pd.Series | pd.DataFrame', target_weights: 'pd.Series | pd.DataFrame', spec: 'BacktestSpec | None' = None) -> 'BacktestResult'
```

Run a deterministic weight-based backtest under an explicit contract.

Defined in `asrquant.backtest`.

### `run_monte_carlo`

**Kind:** function

```python
run_monte_carlo(generator: 'Generator', quantity: 'Quantity | None' = None, *, n_scenarios: 'int' = 10000, estimator: 'Reducer' = 'mean', level: 'float' = 0.95, confidence: 'float' = 0.95, random_state: 'int | None' = 0, parameters: 'Mapping[str, Any] | None' = None, keep_scenarios: 'bool' = True) -> 'MonteCarloResult'
```

Run the universal ``generate -> transform -> reduce`` Monte Carlo pipeline.

Defined in `asrquant.monte_carlo`.

### `sample_variance`

**Kind:** function

```python
sample_variance(values: 'Any') -> 'float'
```

Unbiased sample variance with denominator N-1.

Defined in `asrquant.monte_carlo`.

### `save`

**Kind:** function

```python
save(value: 'Any', path: 'str | Path', kind: 'str | None' = None, *, plot_kwargs: 'dict[str, Any] | None' = None, save_kwargs: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Path'
```

Visualize and save in one call using the file suffix as the format.

Defined in `asrquant.easy`.

### `series`

**Kind:** function

```python
series(data: 'Any' = None, *, index: 'Any' = None, name: 'str | None' = None) -> 'pd.Series'
```

Construct a Series through ASRQuant for one-import workflows.

Defined in `asrquant.easy`.

### `show`

**Kind:** function

```python
show(value: 'Any', kind: 'str | None' = None, **kwargs: 'Any') -> 'PlotHandle'
```

Visualize and display in one call.

Defined in `asrquant.easy`.

### `simple_returns`

**Kind:** function

```python
simple_returns(prices: 'pd.Series | pd.DataFrame') -> 'pd.DataFrame'
```

Compute simple returns with no implicit forward fill.

Defined in `asrquant.data`.

### `simulate`

**Kind:** function

```python
simulate(model: 'str' = 'gbm', **kwargs) -> 'SimulationResult'
```

Unified stochastic-process dispatcher.

Defined in `asrquant.simulation`.

### `simulate_gbm`

**Kind:** function

```python
simulate_gbm(spot: 'float', drift: 'float', volatility: 'float', maturity: 'float', steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'pd.DataFrame'
```

Defined in `asrquant.simulation`.

### `standard_error`

**Kind:** function

```python
standard_error(values: 'Any') -> 'float'
```

Standard error of the sample mean.

Defined in `asrquant.monte_carlo`.

### `stationary_bootstrap`

**Kind:** function

```python
stationary_bootstrap(returns: 'pd.Series | pd.DataFrame', samples: 'int' = 1000, expected_block: 'float' = 20.0, random_state: 'int | None' = 0) -> 'np.ndarray'
```

Politis-Romano-style stationary bootstrap samples.

Defined in `asrquant.simulation`.

### `strip_caplet_volatilities`

**Kind:** function

```python
strip_caplet_volatilities(discount: 'DiscountCurve', periods: 'Sequence[tuple[float, float]]', strike: 'float', cap_prices: 'Sequence[float]', *, notional: 'float' = 1.0, model: 'str' = 'black76', projection: 'ForwardCurve | None' = None, shift: 'float' = 0.0) -> 'pd.Series'
```

Bootstrap caplet vols from a sequence of cumulative cap prices.

Defined in `asrquant.interest_rates`.

### `summary_metrics`

**Kind:** function

```python
summary_metrics(returns: 'pd.Series | Iterable[float]', annualization: 'int' = 252, risk_free_rate: 'float' = 0.0, benchmark: 'pd.Series | Iterable[float] | None' = None, turnover: 'pd.Series | Iterable[float] | None' = None, omega_threshold: 'float' = 0.0) -> 'pd.Series'
```

Defined in `asrquant.metrics`.

### `surface_from_dataframe`

**Kind:** function

```python
surface_from_dataframe(frame: 'pd.DataFrame', *, x: 'str', y: 'str', z: 'str', frame_col: 'str | None' = None, frame_cols: 'Sequence[str] | None' = None, x_name: 'str | None' = None, y_name: 'str | None' = None, z_name: 'str | None' = None, frame_name: 'str | None' = None, agg: 'str | Callable[[pd.Series], float]' = 'mean') -> 'SurfaceResult'
```

Build a static or animated surface from long-form experiment results.

Defined in `asrquant.surfaces`.

### `surface_gradient`

**Kind:** function

```python
surface_gradient(surface: 'SurfaceResult', *, frame: 'int | None' = None) -> 'dict[str, SurfaceResult]'
```

Numerical first derivatives of a regular response surface.

Defined in `asrquant.approximation`.

### `surface_hessian`

**Kind:** function

```python
surface_hessian(surface: 'SurfaceResult', *, frame: 'int | None' = None) -> 'dict[str, SurfaceResult]'
```

Numerical second derivatives and cross-curvature of a regular surface.

Defined in `asrquant.approximation`.

### `svensson_yield`

**Kind:** function

```python
svensson_yield(maturity: 'ArrayLike', beta0: 'float', beta1: 'float', beta2: 'float', beta3: 'float', tau1: 'float', tau2: 'float')
```

Evaluate the Nelson-Siegel-Svensson zero-yield curve.

Defined in `asrquant.interest_rates`.

### `swap_annuity`

**Kind:** function

```python
swap_annuity(curve: 'DiscountCurve', start: 'float', end: 'float', frequency: 'int' = 2) -> 'float'
```

Defined in `asrquant.interest_rates`.

### `swap_dv01`

**Kind:** function

```python
swap_dv01(discount: 'DiscountCurve', start: 'float', end: 'float', fixed_rate: 'float', *, notional: 'float' = 1.0, fixed_frequency: 'int' = 2, position: 'str' = 'payer', bump: 'float' = 0.0001) -> 'float'
```

Defined in `asrquant.interest_rates`.

### `swap_par_rate`

**Kind:** function

```python
swap_par_rate(discount: 'DiscountCurve', start: 'float', end: 'float', *, fixed_frequency: 'int' = 2, projection: 'ForwardCurve | None' = None) -> 'float'
```

Par IRS rate under single- or multi-curve valuation.

Defined in `asrquant.interest_rates`.

### `swap_pv`

**Kind:** function

```python
swap_pv(discount: 'DiscountCurve', start: 'float', end: 'float', fixed_rate: 'float', *, notional: 'float' = 1.0, fixed_frequency: 'int' = 2, position: 'str' = 'payer', projection: 'ForwardCurve | None' = None) -> 'float'
```

PV of a vanilla fixed-for-floating interest-rate swap.

Defined in `asrquant.interest_rates`.

### `swaption_price`

**Kind:** function

```python
swaption_price(discount: 'DiscountCurve', expiry: 'float', swap_end: 'float', strike: 'float', volatility: 'float', *, notional: 'float' = 1.0, fixed_frequency: 'int' = 2, option: 'str' = 'payer', model: 'str' = 'black76', projection: 'ForwardCurve | None' = None, shift: 'float' = 0.0) -> 'float'
```

European physical/cash-annuity-equivalent swaption price.

Defined in `asrquant.interest_rates`.

### `technical_features`

**Kind:** function

```python
technical_features(prices: 'pd.Series', windows=(5, 20, 63), *, rsi_method: 'str' = 'wilder') -> 'pd.DataFrame'
```

Generate compact features; RSI uses Wilder smoothing by default.

Defined in `asrquant.machine_learning`.

### `uniform_inverse_transform`

**Kind:** function

```python
uniform_inverse_transform(quantile_function: 'Callable[[Array], Any]', size: 'int | tuple[int, ...]', *, random_state: 'int | None' = 0) -> 'Array'
```

Generate a target distribution through inverse transform sampling.

Defined in `asrquant.monte_carlo`.

### `vasicek_process`

**Kind:** function

```python
vasicek_process(initial: 'float' = 0.03, speed: 'float' = 1.0, mean: 'float' = 0.04, volatility: 'float' = 0.01, maturity: 'float' = 1.0, steps: 'int' = 252, paths: 'int' = 1000, random_state: 'int | None' = 0) -> 'SimulationResult'
```

Simulate the exact Gaussian transition of the Vasicek rate model.

Defined in `asrquant.simulation`.

### `vasicek_zero_coupon_bond`

**Kind:** function

```python
vasicek_zero_coupon_bond(r_t: 'float', t: 'float', maturity: 'float', kappa: 'float', theta: 'float', sigma: 'float') -> 'float'
```

Vasicek zero-coupon bond price ``A(t,T) exp(-B(t,T) r_t)``.

Defined in `asrquant.interest_rates`.

### `visualize`

**Kind:** function

```python
visualize(value: 'Any', kind: 'str | None' = None, **kwargs: 'Any') -> 'PlotHandle'
```

Create or wrap a visualization without importing a plotting library.

Defined in `asrquant.easy`.

### `walk_forward_fit`

**Kind:** function

```python
walk_forward_fit(estimator: 'Any' = 'ridge', features: 'pd.DataFrame | None' = None, target: 'pd.Series | None' = None, *, train_size: 'int', test_size: 'int', step: 'int | None' = None, gap: 'int' = 0, expanding: 'bool' = True, task: 'str' = 'regression', model_params: 'dict[str, Any] | None' = None) -> 'WalkForwardMLResult'
```

Fit fresh estimator clones on chronological train/test splits.

Defined in `asrquant.machine_learning`.

### `weekly_cycle`

**Kind:** function

```python
weekly_cycle(board: 'ResearchBoard', identifier: 'str | int', *, launch_friday: 'date | str | None' = None, name: 'str | None' = None) -> 'WeeklyResearchCycle'
```

Convenience constructor.

Defined in `asrquant.research_ops`.

### `year_fraction`

**Kind:** function

```python
year_fraction(start: 'date | datetime | str', end: 'date | datetime | str', convention: 'str' = 'ACT/365F') -> 'float'
```

Return year fraction under ASRQuant market-convention rules.

Defined in `asrquant.interest_rates`.

### `yield_curve_pca`

**Kind:** function

```python
yield_curve_pca(yields: 'pd.DataFrame', n_components: 'int' = 3, *, differences: 'bool' = True) -> 'dict[str, Any]'
```

PCA of yield-curve changes returning level/slope/curvature-style loadings.

Defined in `asrquant.interest_rates`.

### `yield_to_maturity`

**Kind:** function

```python
yield_to_maturity(price: 'float', face: 'float', coupon_rate: 'float', maturity: 'float', frequency: 'int' = 2) -> 'float'
```

Solve the yield to maturity by robust scalar bracketing.

Defined in `asrquant.fixed_income`.

### `zero_coupon_inflation_rate`

**Kind:** function

```python
zero_coupon_inflation_rate(index_start: 'float', index_end: 'float', maturity: 'float') -> 'float'
```

Annualized inflation rate implied by a terminal index ratio.

Defined in `asrquant.interest_rates`.

### `zero_coupon_inflation_swap_pv`

**Kind:** function

```python
zero_coupon_inflation_swap_pv(discount: 'DiscountCurve', maturity: 'float', fixed_rate: 'float', index_ratio: 'float', *, notional: 'float' = 1.0, receive_inflation: 'bool' = True) -> 'float'
```

PV of a zero-coupon inflation swap for a supplied terminal index ratio.

Defined in `asrquant.interest_rates`.

### `zero_coupon_price`

**Kind:** function

```python
zero_coupon_price(face: 'float', rate: 'float', maturity: 'float', compounding: 'int | None' = None) -> 'float'
```

Price a zero-coupon bond under continuous or periodic compounding.

Defined in `asrquant.fixed_income`.

### `zero_rate_from_discount`

**Kind:** function

```python
zero_rate_from_discount(discount: 'ArrayLike', maturity: 'ArrayLike', compounding: 'str | int' = 'continuous')
```

Convert discount factors to zero rates.

Defined in `asrquant.interest_rates`.

## Objects and constants

### `__version__`

**Kind:** object

str(object='') -> str

### `models`

**Kind:** object

Attribute-based model factory exposed as ``asrquant.models``.

Defined in `asrquant.models`.

### `register`

**Kind:** object

AdapterRegistry(_items: 'dict[str, dict[str, Any]]' = <factory>)

Defined in `asrquant.registry`.
