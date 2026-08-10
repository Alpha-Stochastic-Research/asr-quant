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
