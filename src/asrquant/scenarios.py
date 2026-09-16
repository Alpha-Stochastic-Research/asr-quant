"""Named scenario and stress-testing primitives for ASRQuant 1.3.0."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    name: str
    rate_parallel_bp: float = 0.0
    rate_slope_bp: float = 0.0
    rate_curvature_bp: float = 0.0
    volatility_relative: float = 0.0
    liquidity_bps: float = 0.0
    asset_returns: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def zero_rate_shock(self, maturities) -> np.ndarray:
        t = np.asarray(maturities, dtype=float)
        if np.any(t < 0): raise ValueError("maturities must be non-negative")
        if t.size == 0: return t
        x = t / max(float(np.max(t)), 1e-12)
        level = self.rate_parallel_bp * 1e-4
        slope = self.rate_slope_bp * 1e-4 * (2.0*x - 1.0)
        curvature = self.rate_curvature_bp * 1e-4 * (1.0 - 4.0*(x-0.5)**2)
        return level + slope + curvature


@dataclass
class ScenarioResult:
    values: pd.DataFrame
    base_values: pd.Series

    @property
    def pnl(self) -> pd.DataFrame:
        return self.values.subtract(self.base_values, axis=1)

    @property
    def summary(self) -> pd.Series:
        pnl = self.pnl
        return pd.Series({"worst_total_pnl": float(pnl.sum(axis=1).min()), "best_total_pnl": float(pnl.sum(axis=1).max()), "n_scenarios": len(pnl), "n_positions": pnl.shape[1]})


def shock_discount_curve(curve, scenario: Scenario):
    t = np.asarray(curve.times, dtype=float); positive = t > 0; p = np.asarray(curve.discounts, dtype=float).copy()
    z = -np.log(p[positive]) / t[positive]; z = z + scenario.zero_rate_shock(t[positive]); p[positive] = np.exp(-z * t[positive])
    return type(curve)(t, p, curve.interpolation, f"{curve.name}:{scenario.name}", {**dict(getattr(curve, "metadata", {}) or {}), "scenario": scenario.name})


def stress_portfolio(positions: Mapping[str, Any], pricers: Mapping[str, Callable[[Any, Scenario | None], float]], scenarios: list[Scenario]) -> ScenarioResult:
    if set(positions) != set(pricers): raise ValueError("positions and pricers must have identical keys")
    base = pd.Series({name: float(pricers[name](position, None)) for name, position in positions.items()}, name="base")
    rows = [pd.Series({name: float(pricers[name](position, scenario)) for name, position in positions.items()}, name=scenario.name) for scenario in scenarios]
    return ScenarioResult(pd.DataFrame(rows), base)


__all__ = ["Scenario", "ScenarioResult", "shock_discount_curve", "stress_portfolio"]
