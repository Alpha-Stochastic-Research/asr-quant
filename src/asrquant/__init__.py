"""ASRQuant: auditable end-to-end quantitative research in Python."""
from .api import QuantLab
from .audit import AuditResult, implementation_audit
from .backtest import BacktestResult, compare_backtests, run_backtest
from .config import BacktestSpec, CostModel, MissingDataPolicy, PlotConfig
from .data import (
    clean_prices,
    data_fingerprint,
    data_quality_report,
    load_prices,
    load_sql,
    log_returns,
    resample_ohlcv,
    simple_returns,
)
from .derivatives import (
    OptionPrice,
    bachelier_greeks,
    bachelier_price,
    black76_price,
    black_scholes_greeks,
    black_scholes_price,
    crr_binomial_price,
    implied_volatility,
    price_option,
)
from .machine_learning import (
    WalkForwardMLResult,
    forward_target,
    lag_features,
    technical_features,
    walk_forward_fit,
    resolve_estimator,
)
from .martingales import MartingaleResult, discount_process, martingale_diagnostics
from .fixed_income import bond_price, bootstrap_zero_curve, convexity, macaulay_duration, modified_duration, yield_to_maturity, zero_coupon_price
from .volatility import VolatilityForecast, ewma_volatility, garch_forecast, garman_klass_volatility, parkinson_volatility, realized_volatility
from .interest_rates import (
    DiscountCurve,
    ForwardCurve,
    MultiCurve,
    RateQuantLab,
    SABRCalibration,
    VasicekCalibration,
    accrued_interest,
    basis_swap_pv,
    compounded_overnight_rate,
    ois_par_rate,
    ois_pv,
    bond_forward_price,
    fx_forward_rate,
    cross_currency_zero_coupon_pv,
    zero_coupon_inflation_rate,
    zero_coupon_inflation_swap_pv,
    curve_scenario,
    HedgeSolution,
    key_rate_hedge,
    BermudanLSMResult,
    bermudan_lsm,
    black_karasinski_paths,
    bond_price_from_curve,
    bootstrap_discount_curve,
    bootstrap_projection_curve_from_swaps,
    calibrate_sabr,
    calibrate_vasicek,
    cap_floor_price,
    caplet_price,
    carry_roll_down,
    clean_price,
    cir_zero_coupon_bond,
    curve_interpolation_risk,
    dirty_price,
    discount_factor,
    dollar_convexity,
    dv01,
    forward_discount_factor,
    forward_rate_from_discounts,
    fra_forward_rate,
    fra_pv,
    hagan_sabr_volatility,
    hjm_one_factor_paths,
    ho_lee_paths,
    hull_white_paths,
    implied_rate_volatility,
    key_rate_dv01,
    level_slope_curvature,
    lmm_terminal_measure_paths,
    no_arbitrage_curve_diagnostics,
    payment_schedule,
    projection_curve_from_discount,
    rate_from_future_price,
    rate_future_price,
    rates_curriculum,
    rates_exercises,
    strip_caplet_volatilities,
    swap_annuity,
    swap_dv01,
    swap_par_rate,
    swap_pv,
    swaption_price,
    vasicek_zero_coupon_bond,
    year_fraction,
    maturity_to_years,
    nelson_siegel_yield,
    svensson_yield,
    YieldCurveCalibration,
    calibrate_nelson_siegel,
    calibrate_svensson,
    yield_curve_pca,
    zero_rate_from_discount,
)
from .discovery import (
    ResearchBoard,
    ResearchCandidate,
    ResearchObservation,
)
from .research_ops import WeeklyResearchCycle, weekly_cycle, research_note_template
from .metrics import summary_metrics
from .statistics import autoregression_fit
from .models import ModelFactory, models, create as create_model
from .easy import PlotHandle, date_range, fit, frame, open_lab, read_table, report, save, series, show, visualize
# Stable domain namespaces. 1.2 keeps the familiar one-import style while
# making each major research area discoverable from one predictable namespace.
from . import math
from . import data
from . import backtest as backtesting
from . import statistics as stats
from . import machine_learning as ml
from . import research
from . import trading
from . import optimization as portfolio
from . import viz as visuals
from . import derivatives as options
from . import simulation as stochastic
from . import monte_carlo as mc
from . import approximation as approx
from . import interest_rates as rates
from . import discovery
from . import hypotheses
from . import alpha
from . import risk
from . import microstructure
from . import factors
from . import volatility as vol
from . import contracts
from .provenance import build_manifest
from .literature import (
    HypothesisCandidate,
    HypothesisRegistry,
    LiteratureCorpus,
    PaperDocument,
    SourceExcerpt,
)
from .workflow import (
    DataPlan,
    DataRequirement,
    DecisionResult,
    EconomicHypothesis,
    FeaturePlan,
    FeatureSpec,
    PortfolioSpec,
    HypothesisTestResult,
    ResearchProject,
    RobustnessResult,
    SignalSpec,
    autoresearch,
    research_project,
)
from .trading import (
    BrokerAdapter,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperBroker,
    PaperTrader,
    PaperTradingResult,
    RiskPolicy,
    paper_trade,
)
from .providers import (
    AlphaVantageProvider,
    BinanceProvider,
    FREDProvider,
    ECBProvider,
    MarketDataProvider,
    PollingFeed,
    YahooProvider,
    download,
    get_provider,
)
from .surfaces import SurfaceResult, evaluate_surface, evaluate_surface_animation, evaluate_parameter_surface, surface_from_dataframe
from .monte_carlo import (
    MonteCarloResult,
    correlated_normal,
    empirical_quantile,
    euler_maruyama,
    event_probability,
    expected_shortfall as monte_carlo_expected_shortfall,
    hedging_loss,
    mean_confidence_interval,
    monte_carlo_parameter_surface,
    normal_samples,
    proportional_transaction_cost,
    run_monte_carlo,
    sample_variance,
    standard_error,
    uniform_inverse_transform,
    value_at_risk as monte_carlo_value_at_risk,
)
from .approximation import (
    ApproximationResult,
    bilinear_interpolation,
    cubic_spline,
    finite_difference_gradient,
    finite_difference_hessian,
    gaussian_process,
    kernel_regression,
    linear_interpolation,
    rbf_interpolation,
    regression_metrics,
    response_regression,
    surface_gradient,
    surface_hessian,
)
from .simulation import (
    MonteCarloPriceResult,
    SimulationResult,
    arithmetic_brownian_motion,
    asian_option_mc,
    cir_process,
    european_option_mc,
    geometric_brownian_motion,
    correlated_gbm,
    regime_switching_prices,
    heston_process,
    merton_jump_diffusion,
    monte_carlo_price,
    ornstein_uhlenbeck,
    simulate,
    simulate_gbm,
    stationary_bootstrap,
    vasicek_process,
)


from .production import (
    CheckLevel,
    CheckState,
    ReadinessCheck,
    ProductionReadinessReport,
    DeploymentEvidence,
    ProductionReadinessGate,
    DeploymentCertificate,
)
from .audit_store import AuditEvent, SQLiteAuditStore
from .live import (
    BrokerEnvironment,
    HealthState,
    ReconciliationState,
    BrokerCredentials,
    AccountSnapshot,
    PositionSnapshot,
    BrokerOrderReceipt,
    MarketDataSnapshot,
    BrokerHealth,
    RiskDecision,
    ReconciliationReport,
    LiveRiskPolicy,
    ExecutionBroker,
    AlpacaBroker,
    PersistentKillSwitch,
    PreTradeRiskEngine,
    LiveTradingEngine,
)

from .version import __version__

# Canonical 1.2 verbs are attached to the domain namespaces without removing
# the lower-level 1.x functions used by existing notebooks.
from .standard_api import install_namespace_contracts as _install_namespace_contracts
_install_namespace_contracts(
    data_module=data,
    backtesting_module=backtesting,
    portfolio_module=portfolio,
    options_module=options,
    rates_module=rates,
    stats_module=stats,
    ml_module=ml,
)
del _install_namespace_contracts

__all__ = [
    "__version__", "QuantLab", "BacktestSpec", "CostModel", "MissingDataPolicy", "PlotConfig",
    "ModelFactory", "models", "create_model", "PlotHandle", "visualize", "show", "save", "report", "fit",
    "open_lab", "frame", "series", "read_table", "date_range", "math", "stats", "portfolio", "visuals",
    "data", "backtesting", "ml", "options", "stochastic", "mc", "approx", "rates", "vol", "research", "discovery", "hypotheses", "alpha", "risk", "microstructure", "factors", "contracts", "trading",
    "BacktestResult", "AuditResult", "run_backtest", "compare_backtests", "implementation_audit",
    "clean_prices", "simple_returns", "log_returns", "load_prices", "load_sql",
    "resample_ohlcv", "data_quality_report", "data_fingerprint", "summary_metrics", "autoregression_fit", "build_manifest",
    "OptionPrice", "black_scholes_price", "black_scholes_greeks", "bachelier_price",
    "bachelier_greeks", "black76_price", "crr_binomial_price", "implied_volatility", "price_option",
    "SurfaceResult", "evaluate_surface", "evaluate_surface_animation", "evaluate_parameter_surface", "surface_from_dataframe",
    "SimulationResult", "MonteCarloPriceResult", "simulate", "simulate_gbm",
    "arithmetic_brownian_motion", "geometric_brownian_motion", "correlated_gbm", "regime_switching_prices", "ornstein_uhlenbeck",
    "cir_process", "vasicek_process", "heston_process", "merton_jump_diffusion", "stationary_bootstrap",
    "monte_carlo_price", "european_option_mc", "asian_option_mc",
    "MonteCarloResult", "run_monte_carlo", "empirical_quantile", "event_probability",
    "sample_variance", "standard_error", "mean_confidence_interval",
    "monte_carlo_value_at_risk", "monte_carlo_expected_shortfall",
    "uniform_inverse_transform", "normal_samples", "correlated_normal", "euler_maruyama",
    "proportional_transaction_cost", "hedging_loss", "monte_carlo_parameter_surface",
    "ApproximationResult", "linear_interpolation", "bilinear_interpolation", "cubic_spline",
    "kernel_regression", "rbf_interpolation", "gaussian_process", "response_regression",
    "regression_metrics", "finite_difference_gradient", "finite_difference_hessian",
    "surface_gradient", "surface_hessian",
    "MartingaleResult", "discount_process", "martingale_diagnostics",
    "WalkForwardMLResult", "lag_features", "technical_features", "forward_target", "walk_forward_fit", "resolve_estimator",
    "MarketDataProvider", "AlphaVantageProvider", "BinanceProvider", "FREDProvider", "ECBProvider", "YahooProvider",
    "PollingFeed", "download", "get_provider",
    "zero_coupon_price", "bond_price", "yield_to_maturity", "macaulay_duration", "modified_duration", "convexity", "bootstrap_zero_curve",
    "VolatilityForecast", "realized_volatility", "parkinson_volatility", "garman_klass_volatility", "ewma_volatility", "garch_forecast",
    "SourceExcerpt", "PaperDocument", "HypothesisCandidate", "HypothesisRegistry", "LiteratureCorpus",
    "DataRequirement", "DataPlan", "EconomicHypothesis", "FeatureSpec", "FeaturePlan", "SignalSpec",
    "PortfolioSpec", "HypothesisTestResult", "RobustnessResult", "DecisionResult", "ResearchProject", "research_project", "autoresearch",
    "OrderSide", "OrderType", "OrderStatus", "Order", "Fill", "RiskPolicy", "BrokerAdapter",
    "PaperBroker", "PaperTrader", "PaperTradingResult", "paper_trade",
    "CheckLevel", "CheckState", "ReadinessCheck", "ProductionReadinessReport",
    "DeploymentEvidence", "ProductionReadinessGate", "DeploymentCertificate",
    "AuditEvent", "SQLiteAuditStore",
    "BrokerEnvironment", "HealthState", "ReconciliationState", "BrokerCredentials",
    "AccountSnapshot", "PositionSnapshot", "BrokerOrderReceipt", "MarketDataSnapshot",
    "BrokerHealth", "RiskDecision", "ReconciliationReport", "LiveRiskPolicy",
    "ExecutionBroker", "AlpacaBroker", "PersistentKillSwitch", "PreTradeRiskEngine",
    "DiscountCurve", "ForwardCurve", "MultiCurve", "RateQuantLab", "SABRCalibration", "VasicekCalibration",
    "year_fraction", "maturity_to_years", "payment_schedule", "discount_factor", "zero_rate_from_discount", "forward_discount_factor",
    "forward_rate_from_discounts", "bootstrap_discount_curve", "projection_curve_from_discount",
    "bootstrap_projection_curve_from_swaps", "bond_price_from_curve", "accrued_interest", "clean_price", "dirty_price",
    "dv01", "dollar_convexity", "key_rate_dv01", "compounded_overnight_rate", "ois_par_rate", "ois_pv",
    "bond_forward_price", "fx_forward_rate", "cross_currency_zero_coupon_pv", "zero_coupon_inflation_rate",
    "zero_coupon_inflation_swap_pv", "curve_scenario", "HedgeSolution", "key_rate_hedge", "BermudanLSMResult", "bermudan_lsm",
    "fra_forward_rate", "fra_pv", "swap_annuity", "swap_par_rate",
    "swap_pv", "swap_dv01", "basis_swap_pv", "rate_future_price", "rate_from_future_price", "caplet_price",
    "cap_floor_price", "swaption_price", "implied_rate_volatility", "strip_caplet_volatilities",
    "hagan_sabr_volatility", "calibrate_sabr", "vasicek_zero_coupon_bond", "cir_zero_coupon_bond",
    "hull_white_paths", "ho_lee_paths", "black_karasinski_paths", "hjm_one_factor_paths",
    "lmm_terminal_measure_paths", "calibrate_vasicek", "yield_curve_pca", "level_slope_curvature",
    "no_arbitrage_curve_diagnostics", "curve_interpolation_risk", "carry_roll_down",
    "nelson_siegel_yield", "svensson_yield", "YieldCurveCalibration", "calibrate_nelson_siegel", "calibrate_svensson", "rates_curriculum", "rates_exercises",
    "ResearchObservation", "ResearchCandidate", "ResearchBoard", "WeeklyResearchCycle", "weekly_cycle", "research_note_template",
    "LiveTradingEngine",
]
