"""Canonical ASRQuant 1.2 namespace API.

The public rule is deliberately small and memorable:

- ``asr.data.load`` / ``asr.data.validate``
- ``asr.backtesting.run``
- ``asr.portfolio.optimize``
- ``asr.options.price``
- ``asr.rates.analyze``
- ``asr.stats.regress``
- ``asr.ml.fit``

Existing 1.x functions remain available.  These wrappers standardize names,
result contracts and domain exceptions without silently changing the scientific
behavior of the underlying implementations.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from . import backtest as _backtesting
from . import data as _data
from . import derivatives as _options
from . import interest_rates as _rates
from . import machine_learning as _ml
from . import optimization as _portfolio
from . import statistics as _stats
from .contracts import (
    BacktestError,
    CurveAnalysisResult,
    DataQualityResult,
    DataValidationError,
    InputValidationError,
    ModelFitError,
    ModelFitResult,
    OptimizationError,
    PortfolioOptimizationResult,
    PricingError,
)


def _normalise_key(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def load_data(path, date_column: str | None = None, **kwargs: Any) -> pd.DataFrame:
    """Load a market/value panel through the canonical data API.

    Parameters
    ----------
    path:
        CSV, Parquet, Excel, JSON or Feather file.
    date_column:
        Column to parse as the time index.  The first column is used when omitted.
    **kwargs:
        Forwarded to :func:`asrquant.data.load_prices`.

    Returns
    -------
    pandas.DataFrame
        Sorted numeric time-indexed data.

    Raises
    ------
    DataValidationError
        If the file cannot satisfy the ASRQuant data contract.
    """
    try:
        return _data.load(path, date_column=date_column, **kwargs)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise DataValidationError(str(exc)) from exc


def validate_data(data: pd.Series | pd.DataFrame) -> DataQualityResult:
    """Inspect time-series structure without mutating or silently cleaning data."""
    return _data.validate(data)


def run_backtest(
    prices: pd.Series | pd.DataFrame,
    target_weights: pd.Series | pd.DataFrame,
    spec: Any | None = None,
):
    """Run the canonical auditable backtest and return ``BacktestResult``."""
    try:
        return _backtesting.run_backtest(prices, target_weights, spec=spec)
    except (ValueError, TypeError, KeyError) as exc:
        raise BacktestError(str(exc)) from exc


def optimize_portfolio(
    returns: pd.DataFrame | None = None,
    *,
    expected_returns: pd.Series | np.ndarray | None = None,
    covariance: pd.DataFrame | np.ndarray | None = None,
    method: str = "minimum_variance",
    annualization: int = 252,
    covariance_method: str = "sample",
    risk_free_rate: float = 0.0,
    long_only: bool = True,
) -> PortfolioOptimizationResult:
    """Solve a common portfolio-construction problem through one result contract.

    Supported methods are ``minimum_variance``, ``maximum_sharpe``,
    ``equal_risk_contribution``, ``maximum_diversification`` and
    ``hierarchical_risk_parity``.
    """
    key = _normalise_key(method)
    frame: pd.DataFrame | None = None
    if returns is not None:
        frame = pd.DataFrame(returns, dtype=float).dropna(how="any")
        if frame.empty or frame.shape[1] == 0:
            raise InputValidationError("returns must contain at least one complete observation")
        if expected_returns is None:
            expected_returns = frame.mean() * annualization
        if covariance is None:
            covariance = _portfolio.estimate_covariance(
                frame,
                method=covariance_method,
                annualization=annualization,
            )

    if covariance is None:
        raise InputValidationError("covariance or returns is required")
    cov = pd.DataFrame(covariance, dtype=float)
    n_assets = cov.shape[0]
    if cov.shape[0] != cov.shape[1] or n_assets == 0:
        raise InputValidationError("covariance must be a non-empty square matrix")

    if isinstance(covariance, pd.DataFrame):
        names = list(covariance.index)
    elif frame is not None:
        names = list(frame.columns)
    else:
        names = [f"asset_{i}" for i in range(n_assets)]

    if expected_returns is None:
        mu = np.zeros(n_assets, dtype=float)
    else:
        mu = np.asarray(expected_returns, dtype=float)
        if len(mu) != n_assets:
            raise InputValidationError("expected_returns length must match covariance dimensions")

    try:
        if key in {"minimum_variance", "min_variance", "min_var"}:
            raw = _portfolio.minimum_variance(cov, long_only=long_only)
            canonical = "minimum_variance"
        elif key in {"maximum_sharpe", "max_sharpe", "tangency"}:
            if expected_returns is None:
                raise InputValidationError("maximum_sharpe requires expected_returns or returns")
            raw = _portfolio.maximum_sharpe(mu, cov, risk_free_rate=risk_free_rate, long_only=long_only)
            canonical = "maximum_sharpe"
        elif key in {"equal_risk_contribution", "erc", "risk_parity"}:
            raw = _portfolio.equal_risk_contribution(cov)
            canonical = "equal_risk_contribution"
        elif key in {"maximum_diversification", "max_diversification"}:
            raw = _portfolio.maximum_diversification(cov, long_only=long_only)
            canonical = "maximum_diversification"
        elif key in {"hierarchical_risk_parity", "hrp"}:
            if frame is None:
                raise InputValidationError("hierarchical_risk_parity requires returns")
            series = _portfolio.hierarchical_risk_parity(frame)
            raw = series.reindex(names).to_numpy(dtype=float)
            canonical = "hierarchical_risk_parity"
        else:
            raise InputValidationError(
                "method must be minimum_variance, maximum_sharpe, equal_risk_contribution, "
                "maximum_diversification, or hierarchical_risk_parity"
            )
    except InputValidationError:
        raise
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
        raise OptimizationError(str(exc)) from exc

    weights = pd.Series(np.asarray(raw, dtype=float), index=names, name="weight")
    expected = float(weights.to_numpy() @ mu)
    vol = float(np.sqrt(max(0.0, weights.to_numpy() @ cov.to_numpy() @ weights.to_numpy())))
    sharpe = (expected - risk_free_rate) / vol if vol > 1e-15 else None
    return PortfolioOptimizationResult(
        weights=weights,
        method=canonical,
        expected_return=expected,
        volatility=vol,
        sharpe=float(sharpe) if sharpe is not None else None,
        metadata={
            "annualization": annualization,
            "covariance_method": covariance_method,
            "long_only": long_only,
        },
    )


def price_option(model: str = "black_scholes", **kwargs: Any):
    """Price a derivative through the canonical ``asr.options.price`` verb."""
    try:
        return _options.price_option(model=model, **kwargs)
    except (ValueError, TypeError, KeyError) as exc:
        raise PricingError(str(exc)) from exc


def regress(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    *,
    method: str = "ols",
    **kwargs: Any,
):
    """Fit a regression through one canonical statistics entry point."""
    key = _normalise_key(method)
    try:
        if key in {"ols", "linear"}:
            return _stats.ols(y, x, **kwargs)
        if key in {"quantile", "quantile_regression"}:
            return _stats.quantile_regression(y, x, **kwargs)
        if key in {"logistic", "logit", "logistic_regression"}:
            return _stats.logistic_regression(y, x, **kwargs)
        if key in {"polynomial", "polynomial_regression"}:
            return _stats.polynomial_regression(y, x, **kwargs)
        if key in {"factor", "factor_regression"}:
            return _stats.factor_regression(y, pd.DataFrame(x), **kwargs)
        if key in {"ridge", "lasso", "elastic_net", "elasticnet"}:
            fitted = _stats.regularized_regression(y, x, method=key, **kwargs)
            residuals = pd.Series(fitted["residuals"], dtype=float)
            fitted_values = pd.Series(fitted["fitted"], dtype=float)
            rmse = float(np.sqrt(np.mean(np.square(residuals))))
            return ModelFitResult(
                model=fitted["model"],
                fitted=fitted_values,
                residuals=residuals,
                metrics=pd.Series({"r2": float(fitted["r2"]), "rmse": rmse}),
                features=list(fitted["features"]),
                method=key,
            )
    except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as exc:
        raise ModelFitError(str(exc)) from exc
    raise InputValidationError(
        "method must be ols, quantile, logistic, polynomial, factor, ridge, lasso, or elastic_net"
    )


def fit_ml(
    estimator: Any = "ridge",
    features: pd.DataFrame | None = None,
    target: pd.Series | None = None,
    *,
    train_size: int,
    test_size: int,
    step: int | None = None,
    gap: int = 0,
    expanding: bool = True,
    task: str = "regression",
    model_params: dict[str, Any] | None = None,
):
    """Run chronology-safe walk-forward ML through ``asr.ml.fit``."""
    if features is None or target is None:
        raise InputValidationError("features and target are required")
    aligned = pd.concat([pd.DataFrame(features), pd.Series(target, name="target")], axis=1).dropna()
    minimum = train_size + gap + test_size
    if len(aligned) < minimum:
        raise InputValidationError(
            f"at least {minimum} aligned observations are required for one walk-forward fold"
        )
    try:
        return _ml.walk_forward_fit(
            estimator,
            features,
            target,
            train_size=train_size,
            test_size=test_size,
            step=step,
            gap=gap,
            expanding=expanding,
            task=task,
            model_params=model_params,
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise ModelFitError(str(exc)) from exc


def analyze_curve(curve: Any) -> CurveAnalysisResult:
    """Summarize a discount curve with table and no-arbitrage diagnostics."""
    if not hasattr(curve, "table"):
        raise InputValidationError("curve must expose a table() method")
    try:
        table = pd.DataFrame(curve.table()).copy()
        diagnostics = pd.Series(_rates.no_arbitrage_curve_diagnostics(curve))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise DataValidationError(str(exc)) from exc
    metadata = {"curve_type": type(curve).__name__}
    name = getattr(curve, "name", None)
    if name is not None:
        metadata["name"] = str(name)
    return CurveAnalysisResult(table=table, diagnostics=diagnostics, metadata=metadata)



def calibrate_rates(model: str, *args: Any, **kwargs: Any):
    """Calibrate a supported interest-rate model through one domain verb.

    Supported model names are ``nelson_siegel``, ``svensson``, ``sabr`` and
    ``vasicek``. Existing specialized calibration functions remain public.
    """
    from .contracts import CalibrationError

    key = _normalise_key(model)
    functions = {
        "nelson_siegel": _rates.calibrate_nelson_siegel,
        "ns": _rates.calibrate_nelson_siegel,
        "svensson": _rates.calibrate_svensson,
        "nelson_siegel_svensson": _rates.calibrate_svensson,
        "nss": _rates.calibrate_svensson,
        "sabr": _rates.calibrate_sabr,
        "vasicek": _rates.calibrate_vasicek,
    }
    if key not in functions:
        raise InputValidationError("model must be nelson_siegel, svensson, sabr, or vasicek")
    try:
        return functions[key](*args, **kwargs)
    except (ValueError, TypeError, KeyError, RuntimeError, np.linalg.LinAlgError) as exc:
        raise CalibrationError(str(exc)) from exc

def _install_result_methods() -> None:
    """Add non-breaking serialization helpers to legacy result classes."""

    if not hasattr(_backtesting.BacktestResult, "summary"):
        _backtesting.BacktestResult.summary = property(lambda self: self.metrics)  # type: ignore[attr-defined]
    if not hasattr(_backtesting.BacktestResult, "to_dict"):
        def backtest_to_dict(self):
            return {
                "result_type": "backtest",
                "summary": self.metrics.to_dict(),
                "fingerprint": self.fingerprint,
                "metadata": dict(self.metadata),
                "spec": self.spec.to_dict(),
            }
        _backtesting.BacktestResult.to_dict = backtest_to_dict  # type: ignore[attr-defined]

    if not hasattr(_options.OptionPrice, "to_frame"):
        _options.OptionPrice.to_frame = lambda self: self.summary.rename("value").to_frame()  # type: ignore[attr-defined]
    if not hasattr(_options.OptionPrice, "to_dict"):
        _options.OptionPrice.to_dict = lambda self: {  # type: ignore[attr-defined]
            "result_type": "option_price",
            "summary": self.summary.to_dict(),
        }

    if not hasattr(_stats.RegressionResult, "to_frame"):
        def regression_to_frame(self):
            return pd.concat(
                {
                    "fitted": self.fitted,
                    "residual": self.residuals,
                },
                axis=1,
            )
        _stats.RegressionResult.to_frame = regression_to_frame  # type: ignore[attr-defined]
    if not hasattr(_stats.RegressionResult, "to_dict"):
        _stats.RegressionResult.to_dict = lambda self: {  # type: ignore[attr-defined]
            "result_type": "regression",
            "summary": self.summary.to_dict(),
            "coefficients": self.coefficients.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
        }

    if not hasattr(_ml.WalkForwardMLResult, "summary"):
        _ml.WalkForwardMLResult.summary = property(  # type: ignore[attr-defined]
            lambda self: self.aggregate_metrics.copy()
        )
    if not hasattr(_ml.WalkForwardMLResult, "to_frame"):
        def ml_to_frame(self):
            pieces = {"actual": self.actual, "prediction": self.predictions}
            if self.probabilities is not None:
                pieces["probability"] = self.probabilities
            return pd.concat(pieces, axis=1)
        _ml.WalkForwardMLResult.to_frame = ml_to_frame  # type: ignore[attr-defined]
    if not hasattr(_ml.WalkForwardMLResult, "to_dict"):
        _ml.WalkForwardMLResult.to_dict = lambda self: {  # type: ignore[attr-defined]
            "result_type": "walk_forward_ml",
            "estimator_name": self.estimator_name,
            "task": self.task,
            "summary": self.aggregate_metrics.to_dict(),
            "fold_metrics": self.fold_metrics.to_dict(orient="index"),
        }


def install_namespace_contracts(
    *,
    data_module: Any,
    backtesting_module: Any,
    portfolio_module: Any,
    options_module: Any,
    rates_module: Any,
    stats_module: Any,
    ml_module: Any,
) -> None:
    """Attach canonical verbs to the existing ASRQuant domain namespaces."""
    _install_result_methods()
    if not hasattr(data_module, "load"):
        data_module.load = load_data
    if not hasattr(data_module, "validate"):
        data_module.validate = validate_data
    backtesting_module.run = run_backtest
    portfolio_module.optimize = optimize_portfolio
    options_module.price = price_option
    rates_module.analyze = analyze_curve
    rates_module.calibrate = calibrate_rates
    stats_module.regress = regress
    ml_module.fit = fit_ml


__all__ = [
    "load_data",
    "validate_data",
    "run_backtest",
    "optimize_portfolio",
    "price_option",
    "regress",
    "fit_ml",
    "analyze_curve",
    "calibrate_rates",
    "install_namespace_contracts",
]
