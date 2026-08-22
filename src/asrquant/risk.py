"""Portfolio risk decomposition, tail risk, and scenario analytics.

Risk measures in this module use a *loss-positive* convention: Value at Risk and
Expected Shortfall are reported as positive loss magnitudes whenever the loss
quantile is positive.  Asset-return inputs remain ordinary signed returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


_EPS = 1e-15


def _returns_frame(returns: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(returns, dtype=float).copy()
    if frame.empty:
        raise ValueError("returns are empty")
    if frame.columns.has_duplicates:
        raise ValueError("returns columns must be unique")
    return frame


def _weights(weights: pd.Series | Iterable[float], columns: pd.Index) -> pd.Series:
    if isinstance(weights, pd.Series):
        w = pd.Series(weights, dtype=float).reindex(columns)
        if w.isna().any():
            missing = list(w.index[w.isna()])
            raise ValueError(f"weights are missing assets: {missing}")
    else:
        values = np.asarray(list(weights), dtype=float)
        if values.ndim != 1 or len(values) != len(columns):
            raise ValueError("weights must have one value per return column")
        w = pd.Series(values, index=columns, dtype=float)
    if not np.isfinite(w.to_numpy()).all():
        raise ValueError("weights must be finite")
    return w


def portfolio_returns(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
) -> pd.Series:
    """Compute fixed-weight portfolio returns after row-wise missing-data checks."""
    frame = _returns_frame(returns)
    w = _weights(weights, frame.columns)
    complete = frame.dropna(how="any")
    if complete.empty:
        raise ValueError("returns contain no complete observations")
    return complete.mul(w, axis=1).sum(axis=1).rename("portfolio_return")


def covariance_risk_contributions(
    weights: pd.Series | Iterable[float],
    covariance: pd.DataFrame | np.ndarray,
    *,
    asset_names: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Euler decomposition of portfolio volatility.

    ``component_volatility`` sums to portfolio volatility (up to floating-point
    precision) for a positive-volatility portfolio.
    """
    if isinstance(covariance, pd.DataFrame):
        cov_frame = pd.DataFrame(covariance, dtype=float)
        if cov_frame.shape[0] != cov_frame.shape[1]:
            raise ValueError("covariance must be square")
        if set(cov_frame.index) != set(cov_frame.columns):
            raise ValueError("covariance index and columns must contain the same assets")
        cov_frame = cov_frame.loc[cov_frame.index, cov_frame.index]
        names = cov_frame.index
        w = _weights(weights, names)
        cov = cov_frame.to_numpy(dtype=float)
    else:
        cov = np.asarray(covariance, dtype=float)
        if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
            raise ValueError("covariance must be a square matrix")
        names = pd.Index(list(asset_names) if asset_names is not None else [f"asset_{i}" for i in range(cov.shape[0])])
        if len(names) != cov.shape[0]:
            raise ValueError("asset_names length must match covariance dimension")
        w = _weights(weights, names)

    if not np.isfinite(cov).all():
        raise ValueError("covariance must be finite")
    if not np.allclose(cov, cov.T, atol=1e-10, rtol=1e-10):
        raise ValueError("covariance must be symmetric")

    variance = float(w.to_numpy() @ cov @ w.to_numpy())
    if variance < -1e-12:
        raise ValueError("covariance produces a negative portfolio variance")
    volatility = float(np.sqrt(max(variance, 0.0)))
    marginal = cov @ w.to_numpy() / volatility if volatility > _EPS else np.zeros(len(w))
    component = w.to_numpy() * marginal
    percent = component / volatility if volatility > _EPS else np.zeros(len(w))
    return pd.DataFrame(
        {
            "weight": w.to_numpy(),
            "marginal_volatility": marginal,
            "component_volatility": component,
            "percent_total": percent,
        },
        index=names,
    )


def portfolio_var(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
    *,
    level: float = 0.95,
    method: str = "historical",
    horizon: int = 1,
) -> float:
    """Portfolio Value at Risk using historical, Gaussian, or Cornish-Fisher loss."""
    if not 0 < level < 1:
        raise ValueError("level must lie in (0, 1)")
    if horizon < 1:
        raise ValueError("horizon must be a positive integer")
    r = portfolio_returns(returns, weights)
    key = method.lower().replace("-", "_")

    if key == "historical":
        if horizon != 1:
            compounded = (1.0 + r).rolling(horizon).apply(np.prod, raw=True) - 1.0
            r = compounded.dropna()
        losses = -r.to_numpy(dtype=float)
        return float(np.quantile(losses, level))

    mean = float(r.mean()) * horizon
    sigma = float(r.std(ddof=1)) * np.sqrt(horizon)
    if sigma <= _EPS:
        return float(-mean)

    if key in {"gaussian", "normal"}:
        z = float(stats.norm.ppf(level))
    elif key in {"cornish_fisher", "cornishfisher", "cf"}:
        losses = -r.to_numpy(dtype=float)
        z0 = float(stats.norm.ppf(level))
        skew = float(stats.skew(losses, bias=False))
        excess_kurtosis = float(stats.kurtosis(losses, fisher=True, bias=False))
        z = (
            z0
            + (z0**2 - 1.0) * skew / 6.0
            + (z0**3 - 3.0 * z0) * excess_kurtosis / 24.0
            - (2.0 * z0**3 - 5.0 * z0) * skew**2 / 36.0
        )
    else:
        raise ValueError("method must be historical, gaussian, or cornish_fisher")

    # Loss L = -R, so E[L] = -mean(R).
    return float(-mean + z * sigma)


def portfolio_expected_shortfall(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
    *,
    level: float = 0.95,
    method: str = "historical",
    horizon: int = 1,
) -> float:
    """Portfolio Expected Shortfall under historical or Gaussian assumptions."""
    if not 0 < level < 1:
        raise ValueError("level must lie in (0, 1)")
    if horizon < 1:
        raise ValueError("horizon must be a positive integer")
    r = portfolio_returns(returns, weights)
    key = method.lower()

    if key == "historical":
        if horizon != 1:
            r = ((1.0 + r).rolling(horizon).apply(np.prod, raw=True) - 1.0).dropna()
        losses = -r
        var = float(losses.quantile(level, interpolation="linear"))
        tail = losses[losses >= var]
        return float(tail.mean()) if len(tail) else np.nan

    if key in {"gaussian", "normal"}:
        mean = float(r.mean()) * horizon
        sigma = float(r.std(ddof=1)) * np.sqrt(horizon)
        if sigma <= _EPS:
            return float(-mean)
        z = float(stats.norm.ppf(level))
        return float(-mean + sigma * stats.norm.pdf(z) / (1.0 - level))

    raise ValueError("method must be historical or gaussian")


def expected_shortfall_contributions(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
    *,
    level: float = 0.95,
) -> pd.Series:
    """Historical asset contributions to portfolio Expected Shortfall.

    The contributions are conditional mean *loss* contributions in observations
    where the total portfolio loss breaches its historical VaR. Their sum equals
    the reported historical ES up to quantile/tie precision.
    """
    if not 0 < level < 1:
        raise ValueError("level must lie in (0, 1)")
    frame = _returns_frame(returns).dropna(how="any")
    if frame.empty:
        raise ValueError("returns contain no complete observations")
    w = _weights(weights, frame.columns)
    loss_contributions = -frame.mul(w, axis=1)
    portfolio_loss = loss_contributions.sum(axis=1)
    var = float(portfolio_loss.quantile(level, interpolation="linear"))
    tail = loss_contributions.loc[portfolio_loss >= var]
    if tail.empty:
        return pd.Series(np.nan, index=frame.columns, name="es_contribution")
    return tail.mean(axis=0).rename("es_contribution")


def scenario_pnl(
    weights: pd.Series | Iterable[float],
    scenarios: pd.DataFrame,
    *,
    capital: float = 1.0,
) -> pd.DataFrame:
    """Apply instantaneous asset-return scenarios to a portfolio.

    ``scenarios`` is a Scenario x Asset matrix of signed shocks/returns.  Output
    asset columns are P&L contributions and ``portfolio_pnl`` is their sum.
    """
    if capital <= 0 or not np.isfinite(capital):
        raise ValueError("capital must be a positive finite number")
    frame = pd.DataFrame(scenarios, dtype=float).copy()
    if frame.empty:
        raise ValueError("scenarios are empty")
    if frame.columns.has_duplicates:
        raise ValueError("scenario asset columns must be unique")
    w = _weights(weights, frame.columns)
    contributions = frame.mul(w * capital, axis=1)
    contributions["portfolio_pnl"] = contributions.sum(axis=1)
    return contributions


def rolling_var(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
    *,
    window: int = 252,
    level: float = 0.95,
    method: str = "historical",
) -> pd.Series:
    """Rolling one-period portfolio VaR with a fixed weight vector."""
    if window < 2:
        raise ValueError("window must be at least 2")
    frame = _returns_frame(returns)
    w = _weights(weights, frame.columns)
    complete = frame.dropna(how="any")
    values = pd.Series(np.nan, index=complete.index, name="rolling_var", dtype=float)
    for end in range(window - 1, len(complete)):
        sample = complete.iloc[end - window + 1 : end + 1]
        values.iloc[end] = portfolio_var(sample, w, level=level, method=method)
    return values


@dataclass(frozen=True)
class PortfolioRiskReport:
    """Compact portfolio-risk snapshot with inspectable decompositions."""

    summary: pd.Series
    volatility_contributions: pd.DataFrame
    expected_shortfall_contributions: pd.Series
    portfolio_returns: pd.Series


def portfolio_risk_report(
    returns: pd.DataFrame,
    weights: pd.Series | Iterable[float],
    *,
    level: float = 0.95,
    annualization: int = 252,
) -> PortfolioRiskReport:
    """Build a standard volatility + tail-risk report from asset returns."""
    if annualization <= 0:
        raise ValueError("annualization must be positive")
    frame = _returns_frame(returns).dropna(how="any")
    if len(frame) < 2:
        raise ValueError("at least two complete return observations are required")
    w = _weights(weights, frame.columns)
    p = portfolio_returns(frame, w)
    annual_cov = frame.cov() * annualization
    contributions = covariance_risk_contributions(w, annual_cov)
    es_contrib = expected_shortfall_contributions(frame, w, level=level)
    annual_vol = float(p.std(ddof=1) * np.sqrt(annualization))
    summary = pd.Series(
        {
            "annualized_return_arithmetic": float(p.mean() * annualization),
            "annualized_volatility": annual_vol,
            f"historical_var_{level:.2%}": portfolio_var(frame, w, level=level, method="historical"),
            f"gaussian_var_{level:.2%}": portfolio_var(frame, w, level=level, method="gaussian"),
            f"cornish_fisher_var_{level:.2%}": portfolio_var(frame, w, level=level, method="cornish_fisher"),
            f"historical_es_{level:.2%}": portfolio_expected_shortfall(frame, w, level=level, method="historical"),
            f"gaussian_es_{level:.2%}": portfolio_expected_shortfall(frame, w, level=level, method="gaussian"),
            "gross_exposure": float(w.abs().sum()),
            "net_exposure": float(w.sum()),
        },
        name="value",
    )
    return PortfolioRiskReport(
        summary=summary,
        volatility_contributions=contributions,
        expected_shortfall_contributions=es_contrib,
        portfolio_returns=p,
    )


__all__ = [
    "PortfolioRiskReport",
    "covariance_risk_contributions",
    "expected_shortfall_contributions",
    "portfolio_expected_shortfall",
    "portfolio_returns",
    "portfolio_risk_report",
    "portfolio_var",
    "rolling_var",
    "scenario_pnl",
]
