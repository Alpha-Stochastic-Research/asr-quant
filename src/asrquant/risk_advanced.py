"""Advanced tail-risk estimators for ASRQuant."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import genpareto

from .contracts import ResultMixin


@dataclass
class EVTResult(ResultMixin):
    threshold: float
    shape: float
    scale: float
    exceedance_probability: float
    sample_size: int
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="evt", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "threshold": self.threshold,
                "shape": self.shape,
                "scale": self.scale,
                "exceedance_probability": self.exceedance_probability,
                "sample_size": self.sample_size,
            }
        )

    def var(self, level: float = 0.99) -> float:
        if not 0 < level < 1:
            raise ValueError("level must lie in (0,1)")
        tail_prob = 1.0 - level
        p_u = self.exceedance_probability
        if tail_prob >= p_u:
            raise ValueError("requested level lies below the fitted EVT threshold")
        xi, beta = self.shape, self.scale
        if abs(xi) < 1e-10:
            excess = beta * np.log(p_u / tail_prob)
        else:
            excess = beta / xi * ((p_u / tail_prob) ** xi - 1.0)
        return float(self.threshold + excess)

    def expected_shortfall(self, level: float = 0.99) -> float:
        q = self.var(level)
        xi, beta = self.shape, self.scale
        if xi >= 1:
            return np.inf
        return float((q + beta - xi * self.threshold) / (1.0 - xi))


def evt(losses: pd.Series, *, threshold_quantile: float = 0.95) -> EVTResult:
    """Peaks-over-threshold Generalized Pareto fit for positive losses."""
    x = pd.Series(losses, dtype=float).dropna().to_numpy()
    if len(x) < 50:
        raise ValueError("EVT fit requires at least 50 observations")
    if not 0.5 < threshold_quantile < 1.0:
        raise ValueError("threshold_quantile must lie in (0.5,1)")
    threshold = float(np.quantile(x, threshold_quantile))
    exceed = x[x > threshold] - threshold
    if len(exceed) < 10:
        raise ValueError("too few threshold exceedances for EVT fit")
    shape, loc, scale = genpareto.fit(exceed, floc=0.0)
    if scale <= 0:
        raise ValueError("invalid EVT scale estimate")
    return EVTResult(
        threshold=threshold,
        shape=float(shape),
        scale=float(scale),
        exceedance_probability=float(len(exceed) / len(x)),
        sample_size=len(x),
        metadata={"threshold_quantile": threshold_quantile, "exceedances": len(exceed)},
    )


def filtered_historical_simulation(
    returns: pd.Series,
    *,
    level: float = 0.99,
    decay: float = 0.94,
    horizon: int = 1,
) -> pd.Series:
    """EWMA-filtered historical VaR/ES using current conditional volatility."""
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 20 or not 0 < decay < 1 or not 0 < level < 1 or horizon <= 0:
        raise ValueError("invalid FHS inputs")
    var = np.empty(len(r))
    var[0] = float(r.var(ddof=1))
    for i in range(1, len(r)):
        var[i] = decay * var[i - 1] + (1.0 - decay) * r.iloc[i - 1] ** 2
    vol = np.sqrt(np.maximum(var, 1e-20))
    standardized = r.to_numpy() / vol
    current_vol = vol[-1] * np.sqrt(horizon)
    scenarios = standardized * current_vol
    losses = -scenarios
    q = float(np.quantile(losses, level))
    es = float(losses[losses >= q].mean())
    return pd.Series({"var": q, "expected_shortfall": es, "current_volatility": current_vol, "level": level})


def drawdown_at_risk(returns: pd.Series, level: float = 0.95) -> float:
    r = pd.Series(returns, dtype=float).dropna()
    equity = (1.0 + r).cumprod()
    drawdown_loss = 1.0 - equity / equity.cummax()
    return float(drawdown_loss.quantile(level))


def conditional_drawdown_at_risk(returns: pd.Series, level: float = 0.95) -> float:
    r = pd.Series(returns, dtype=float).dropna()
    equity = (1.0 + r).cumprod()
    losses = 1.0 - equity / equity.cummax()
    threshold = float(losses.quantile(level))
    tail = losses[losses >= threshold]
    return float(tail.mean()) if len(tail) else threshold


def liquidity_adjusted_var(var: float, *, liquidation_cost: float, portfolio_value: float = 1.0) -> float:
    if var < 0 or liquidation_cost < 0 or portfolio_value <= 0:
        raise ValueError("var/liquidation_cost must be non-negative and portfolio_value positive")
    return float(var + liquidation_cost / portfolio_value)


__all__ = [
    "EVTResult",
    "evt",
    "filtered_historical_simulation",
    "drawdown_at_risk",
    "conditional_drawdown_at_risk",
    "liquidity_adjusted_var",
]
