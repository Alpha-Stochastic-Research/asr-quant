"""Signal capacity diagnostics based on turnover, ADV and square-root impact."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd

from .contracts import ResultMixin


@dataclass
class CapacityResult(ResultMixin):
    curve: pd.DataFrame
    estimated_capacity: float | None
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="alpha_capacity", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "estimated_capacity": self.estimated_capacity,
                "grid_points": len(self.curve),
                "max_aum_tested": float(self.curve.index.max()) if len(self.curve) else np.nan,
                "min_net_alpha": float(self.curve["net_alpha"].min()) if len(self.curve) else np.nan,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.curve.copy()


def capacity(
    target_weights: pd.DataFrame,
    adv_value: pd.Series,
    volatility: pd.Series,
    *,
    expected_gross_alpha: float,
    aum_grid: Sequence[float] | None = None,
    eta: float = 0.5,
    spread_bps: float = 0.0,
    annualization: int = 252,
) -> CapacityResult:
    """Estimate strategy capacity from turnover and square-root market impact.

    ``expected_gross_alpha`` is an annual decimal return.  ``adv_value`` is
    average daily traded value in currency units and ``volatility`` is daily
    decimal volatility.  The result is a research diagnostic, not an execution
    forecast.
    """
    weights = pd.DataFrame(target_weights, dtype=float).dropna(how="all").fillna(0.0)
    adv = pd.Series(adv_value, dtype=float).reindex(weights.columns)
    vol = pd.Series(volatility, dtype=float).reindex(weights.columns)
    if weights.empty or adv.isna().any() or vol.isna().any():
        raise ValueError("weights, adv_value and volatility must align")
    if (adv <= 0).any() or (vol < 0).any() or eta < 0 or spread_bps < 0:
        raise ValueError("ADV must be positive; volatility, eta and spread_bps non-negative")
    trades = weights.diff().abs().fillna(weights.abs())
    grid = np.asarray(aum_grid if aum_grid is not None else np.geomspace(1e5, 1e10, 60), dtype=float)
    if np.any(grid <= 0):
        raise ValueError("aum_grid must be positive")
    rows = []
    for aum in grid:
        trade_value = trades * aum
        participation = trade_value.divide(adv, axis=1)
        impact_fraction = eta * participation.pow(0.5).multiply(vol, axis=1)
        impact_cost = (trade_value * impact_fraction).sum(axis=1) / aum
        spread_cost = trade_value.sum(axis=1) / aum * spread_bps / 20_000.0
        annual_cost = float((impact_cost + spread_cost).mean() * annualization)
        rows.append(
            {
                "aum": float(aum),
                "annual_cost": annual_cost,
                "gross_alpha": float(expected_gross_alpha),
                "net_alpha": float(expected_gross_alpha - annual_cost),
                "mean_participation": float(participation.mean().mean()),
                "max_participation": float(participation.max().max()),
            }
        )
    curve = pd.DataFrame(rows).set_index("aum")
    positive = curve.index[curve["net_alpha"] > 0]
    estimated = float(positive.max()) if len(positive) else None
    return CapacityResult(curve, estimated, metadata={"eta": eta, "spread_bps": spread_bps, "annualization": annualization})


__all__ = ["CapacityResult", "capacity"]
