"""Constraint-aware and cost-aware portfolio construction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .contracts import OptimizationError, PortfolioOptimizationResult
from .optimization import estimate_covariance


@dataclass(frozen=True)
class Constraints:
    long_only: bool = True
    max_weight: float | None = 1.0
    max_gross: float = 1.0
    target_net: float = 1.0
    turnover_limit: float | None = None
    min_weights: Mapping[str, float] = field(default_factory=dict)
    max_weights: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_weight is not None and self.max_weight <= 0:
            raise ValueError("max_weight must be positive")
        if self.max_gross <= 0:
            raise ValueError("max_gross must be positive")
        if self.turnover_limit is not None and self.turnover_limit < 0:
            raise ValueError("turnover_limit must be non-negative")


def _bounds(names: pd.Index, c: Constraints) -> list[tuple[float, float]]:
    out = []
    for name in names:
        low = 0.0 if c.long_only else -float(c.max_weight or c.max_gross)
        high = float(c.max_weight or c.max_gross)
        if name in c.min_weights:
            low = max(low, float(c.min_weights[name]))
        if name in c.max_weights:
            high = min(high, float(c.max_weights[name]))
        if low > high:
            raise OptimizationError(f"inconsistent bounds for asset {name!r}")
        out.append((low, high))
    return out


def _constraints(c: Constraints, current: np.ndarray | None):
    cons: list[dict[str, Any]] = [
        {"type": "eq", "fun": lambda w: float(np.sum(w) - c.target_net)},
        {"type": "ineq", "fun": lambda w: float(c.max_gross - np.sum(np.abs(w)))},
    ]
    if c.turnover_limit is not None:
        if current is None:
            raise OptimizationError("turnover_limit requires current_weights")
        cons.append({"type": "ineq", "fun": lambda w: float(c.turnover_limit - np.sum(np.abs(w - current)))})
    return cons


def cost_aware_optimize(
    returns: pd.DataFrame,
    *,
    current_weights: pd.Series | Mapping[str, float] | None = None,
    objective: str = "max_sharpe",
    constraints: Constraints | None = None,
    covariance_method: str = "ledoit_wolf",
    annualization: float = 252.0,
    risk_free_rate: float = 0.0,
    turnover_penalty: float = 0.0,
    l2_penalty: float = 0.0,
) -> PortfolioOptimizationResult:
    """Optimize a portfolio while internalizing turnover and concentration penalties."""
    frame = pd.DataFrame(returns, dtype=float).dropna(how="any")
    if frame.empty or frame.shape[1] < 1:
        raise OptimizationError("returns must contain aligned observations")
    c = constraints or Constraints()
    names = frame.columns
    mu = frame.mean().to_numpy(dtype=float) * annualization
    cov = estimate_covariance(frame, method=covariance_method, annualization=annualization)
    cov_arr = np.asarray(cov, dtype=float)
    if current_weights is None:
        current = None
    else:
        current = pd.Series(current_weights, dtype=float).reindex(names).fillna(0.0).to_numpy(dtype=float)
    key = objective.lower().replace("-", "_")
    if turnover_penalty < 0 or l2_penalty < 0:
        raise OptimizationError("penalties must be non-negative")

    def penalty(w: np.ndarray) -> float:
        turn = np.sum(np.abs(w - current)) if current is not None else 0.0
        return turnover_penalty * turn + l2_penalty * float(np.dot(w, w))

    def vol(w: np.ndarray) -> float:
        return float(np.sqrt(max(0.0, w @ cov_arr @ w)))

    if key in {"minimum_variance", "min_variance"}:
        fun = lambda w: float(w @ cov_arr @ w) + penalty(w)
        canonical = "cost_aware_minimum_variance"
    elif key in {"maximum_sharpe", "max_sharpe"}:
        def fun(w: np.ndarray) -> float:
            sigma = vol(w)
            if sigma <= 1e-12:
                return 1e6 + penalty(w)
            return -float((w @ mu - risk_free_rate) / sigma) + penalty(w)
        canonical = "cost_aware_maximum_sharpe"
    else:
        raise OptimizationError("objective must be max_sharpe or min_variance")

    x0 = np.full(len(names), c.target_net / len(names), dtype=float)
    if current is not None and np.isclose(current.sum(), c.target_net, atol=1e-8):
        x0 = current.copy()
    result = minimize(
        fun,
        x0,
        method="SLSQP",
        bounds=_bounds(names, c),
        constraints=_constraints(c, current),
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    if not result.success:
        raise OptimizationError(f"portfolio optimization failed: {result.message}")
    w = np.asarray(result.x, dtype=float)
    expected = float(w @ mu)
    sigma = vol(w)
    sharpe = (expected - risk_free_rate) / sigma if sigma > 1e-12 else None
    turnover = float(np.sum(np.abs(w - current))) if current is not None else np.nan
    return PortfolioOptimizationResult(
        weights=pd.Series(w, index=names, name="weight"),
        method=canonical,
        expected_return=expected,
        volatility=sigma,
        sharpe=float(sharpe) if sharpe is not None else None,
        metadata={
            "covariance_method": covariance_method,
            "turnover": turnover,
            "turnover_penalty": turnover_penalty,
            "l2_penalty": l2_penalty,
            "max_gross": c.max_gross,
            "target_net": c.target_net,
            "turnover_limit": c.turnover_limit,
        },
    )


def robust_mean_variance(
    expected_returns: pd.Series,
    covariance: pd.DataFrame,
    *,
    risk_aversion: float = 1.0,
    uncertainty_radius: float = 0.0,
    constraints: Constraints | None = None,
) -> pd.Series:
    """Ellipsoidal robust mean-variance allocation.

    The uncertainty penalty ``radius * sqrt(w' Sigma w)`` reduces reliance on
    fragile expected-return estimates.
    """
    mu = pd.Series(expected_returns, dtype=float)
    cov = pd.DataFrame(covariance, dtype=float).reindex(index=mu.index, columns=mu.index)
    if cov.isna().any().any():
        raise OptimizationError("covariance does not align with expected_returns")
    if risk_aversion <= 0 or uncertainty_radius < 0:
        raise OptimizationError("risk_aversion must be positive and uncertainty_radius non-negative")
    c = constraints or Constraints()
    arr = cov.to_numpy(dtype=float)

    def fun(w: np.ndarray) -> float:
        variance = float(w @ arr @ w)
        robust_penalty = uncertainty_radius * np.sqrt(max(variance, 0.0))
        utility = float(w @ mu.to_numpy()) - 0.5 * risk_aversion * variance - robust_penalty
        return -utility

    x0 = np.full(len(mu), c.target_net / len(mu))
    result = minimize(fun, x0, method="SLSQP", bounds=_bounds(mu.index, c), constraints=_constraints(c, None), options={"maxiter": 2000, "ftol": 1e-12})
    if not result.success:
        raise OptimizationError(str(result.message))
    return pd.Series(result.x, index=mu.index, name="weight")


def risk_budgeting(covariance: pd.DataFrame, budgets: pd.Series | Sequence[float] | None = None) -> pd.Series:
    """Long-only risk-budgeting portfolio for arbitrary positive budgets."""
    cov = pd.DataFrame(covariance, dtype=float)
    if cov.shape[0] != cov.shape[1] or not cov.index.equals(cov.columns):
        raise OptimizationError("covariance must be a square DataFrame with matching labels")
    n = len(cov)
    if budgets is None:
        b = np.full(n, 1.0 / n)
    else:
        b = np.asarray(pd.Series(budgets, index=cov.index if not isinstance(budgets, pd.Series) else None), dtype=float)
        if len(b) != n or np.any(b <= 0):
            raise OptimizationError("budgets must be positive and match covariance dimension")
        b = b / b.sum()
    arr = cov.to_numpy(dtype=float)

    def objective(w: np.ndarray) -> float:
        sigma2 = float(w @ arr @ w)
        if sigma2 <= 1e-20:
            return 1e6
        marginal = arr @ w
        rc = w * marginal / sigma2
        return float(np.sum((rc - b) ** 2))

    res = minimize(objective, np.full(n, 1 / n), method="SLSQP", bounds=[(1e-10, 1.0)] * n, constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}], options={"maxiter": 5000, "ftol": 1e-14})
    if not res.success:
        raise OptimizationError(str(res.message))
    return pd.Series(res.x, index=cov.index, name="weight")


__all__ = ["Constraints", "cost_aware_optimize", "robust_mean_variance", "risk_budgeting"]
