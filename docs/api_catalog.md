# API catalog

The stable high-level entry point is `asrquant.QuantLab`. Lower-level namespaces are available for research workflows:

- `asrquant.backtest`
- `asrquant.metrics`
- `asrquant.statistics`
- `asrquant.validation`
- `asrquant.optimization`
- `asrquant.derivatives`
- `asrquant.simulation`
- `asrquant.provenance`
- `asrquant.viz`

Version 0.1.0 is alpha. Pin the package version and save the experiment manifest for reproducible work.


# Production and guarded-live API (1.0.0)

- `DeploymentEvidence`: structured deployment proof, failing by default.
- `ProductionReadinessGate`: evaluates software, operations, paper-broker and governance checks.
- `ProductionReadinessReport`: serializable result; `ready` is true only when every required check passes.
- `DeploymentCertificate`: signed, expiring authorization bound to release, broker, account, policy and capital.
- `SQLiteAuditStore`: durable hash-chained event log with idempotency and backup.
- `LiveRiskPolicy`: pre-trade, account, market-data, rate, capital and reconciliation limits.
- `AlpacaBroker.paper(...)`: official paper endpoint.
- `AlpacaBroker.live(...)`: certificate-gated live endpoint.
- `PersistentKillSwitch`: restart-safe emergency stop.
- `PreTradeRiskEngine`: deterministic rejection before broker submission.
- `LiveTradingEngine`: audited submission, reconciliation, health and emergency-stop orchestration.

# Universal Monte Carlo and approximation API (1.0.0)

## Monte Carlo

- `MonteCarloResult`
- `run_monte_carlo`
- `empirical_quantile`
- `event_probability`
- `sample_variance`
- `standard_error`
- `mean_confidence_interval`
- `monte_carlo_value_at_risk`
- `monte_carlo_expected_shortfall`
- `uniform_inverse_transform`
- `normal_samples`
- `correlated_normal`
- `euler_maruyama`
- `proportional_transaction_cost`
- `hedging_loss`
- `monte_carlo_parameter_surface`

High-level methods:

- `QuantLab.monte_carlo_experiment`
- `QuantLab.monte_carlo_surface`

## Approximation and sensitivities

- `ApproximationResult`
- `linear_interpolation`
- `bilinear_interpolation`
- `cubic_spline`
- `kernel_regression`
- `rbf_interpolation`
- `gaussian_process`
- `response_regression`
- `regression_metrics`
- `finite_difference_gradient`
- `finite_difference_hessian`
- `surface_gradient`
- `surface_hessian`
- `SurfaceResult.gradient`
- `SurfaceResult.hessian`

High-level method:

- `QuantLab.approximate`

## Time-series convenience

- `autoregression_fit`
- `QuantLab.autoregression`
- `QuantLab.garch`


# Research Discovery and Interest Rates API (1.1.0)

## Research discovery

- `asr.discovery.weekly`
- `ResearchObservation`, `ResearchCandidate`, `ResearchBoard`
- `ResearchBoard.start`, `ResearchBoard.weekly_plan`
- `WeeklyResearchCycle`, `weekly_cycle`, `research_note_template`

## Interest rates

- conventions: `year_fraction`, `maturity_to_years`, `payment_schedule`
- curves: `DiscountCurve`, `ForwardCurve`, `MultiCurve`, `bootstrap_discount_curve`, `bootstrap_projection_curve_from_swaps`
- parametric curves: `nelson_siegel_yield`, `svensson_yield`, `calibrate_nelson_siegel`, `calibrate_svensson`
- linear rates: `fra_pv`, `rate_future_price`, `swap_pv`, `basis_swap_pv`, `compounded_overnight_rate`, `ois_pv`
- fixed-income/cross-asset building blocks: `bond_forward_price`, `fx_forward_rate`, `cross_currency_zero_coupon_pv`, `zero_coupon_inflation_swap_pv`
- scenarios/exotics: `curve_scenario`, `key_rate_hedge`, `bermudan_lsm`
- rate options: `caplet_price`, `cap_floor_price`, `swaption_price`, `implied_rate_volatility`, `strip_caplet_volatilities`
- smile: `hagan_sabr_volatility`, `calibrate_sabr`
- rates models: Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski, HJM and LMM functions
- risk/research: `dv01`, `key_rate_dv01`, `yield_curve_pca`, `curve_interpolation_risk`, `carry_roll_down`
- data: `ECBProvider`, `ECBProvider.yield_curve_history`, `RateQuantLab.from_ecb`
- learning: `rates_curriculum`, `rates_exercises`
