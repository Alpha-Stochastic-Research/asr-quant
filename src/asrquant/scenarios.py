"""Cross-domain scenario objects for rates, portfolios and stress analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .contracts import ResultMixin
from .interest_rates import DiscountCurve, curve_scenario


@dataclass(frozen=True)
class Scenario:
    name: str
    asset_shocks: Mapping[str, float] = field(default_factory=dict)
    parallel_rate_bp: float = 0.0
    slope_rate_bp: float = 0.0
    curvature_rate_bp: float = 0.0
    volatility_shock: float = 0.0
    liquidity_multiplier: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.liquidity_multiplier <= 0:
            raise ValueError("liquidity_multiplier must be positive")

    def apply_curve(self, curve: DiscountCurve) -> DiscountCurve:
        return curve_scenario(
            curve,
            parallel_bp=self.parallel_rate_bp,
            slope_bp=self.slope_rate_bp,
            curvature_bp=self.curvature_rate_bp,
        )


@dataclass
class ScenarioResult(ResultMixin):
    scenario: Scenario
    pnl: float
    contributions: pd.Series
    base_value: float | None = None
    shocked_value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="scenario", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "scenario": self.scenario.name,
                "pnl": self.pnl,
                "base_value": self.base_value,
                "shocked_value": self.shocked_value,
                "n_contributions": int(len(self.contributions)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.contributions.rename("pnl_contribution").to_frame()


def run(
    scenario: Scenario,
    *,
    weights: pd.Series | Mapping[str, float] | None = None,
    portfolio_value: float = 1.0,
    instrument: Any | None = None,
    curve: DiscountCurve | None = None,
) -> ScenarioResult:
    """Run an asset-shock or rate-curve scenario.

    Asset shocks are decimal returns, e.g. ``-0.10`` for a 10% drop.  For a rate
    instrument, pass an object exposing ``price(curve)`` together with ``curve``.
    """
    if instrument is not None:
        if curve is None or not hasattr(instrument, "price"):
            raise ValueError("rate-instrument scenario requires curve and instrument.price(curve)")
        base = float(instrument.price(curve))
        shocked_curve = scenario.apply_curve(curve)
        shocked = float(instrument.price(shocked_curve))
        return ScenarioResult(
            scenario=scenario,
            pnl=shocked - base,
            contributions=pd.Series({"rates": shocked - base}),
            base_value=base,
            shocked_value=shocked,
            metadata={"curve": curve.name},
        )

    if weights is None:
        raise ValueError("provide weights for an asset scenario or instrument+curve for a rate scenario")
    w = pd.Series(weights, dtype=float)
    shocks = pd.Series(scenario.asset_shocks, dtype=float).reindex(w.index).fillna(0.0)
    contrib = portfolio_value * w * shocks
    pnl = float(contrib.sum())
    return ScenarioResult(
        scenario=scenario,
        pnl=pnl,
        contributions=contrib,
        base_value=float(portfolio_value),
        shocked_value=float(portfolio_value + pnl),
    )


def parallel_rate_shift(bp: float, name: str | None = None) -> Scenario:
    return Scenario(name or f"rates_parallel_{bp:+g}bp", parallel_rate_bp=float(bp))


def steepener(bp: float = 25.0) -> Scenario:
    return Scenario(f"steepener_{bp:g}bp", slope_rate_bp=float(bp))


def flattener(bp: float = 25.0) -> Scenario:
    return Scenario(f"flattener_{bp:g}bp", slope_rate_bp=-float(bp))


def butterfly(bp: float = 25.0) -> Scenario:
    return Scenario(f"butterfly_{bp:g}bp", curvature_rate_bp=float(bp))


def equity_crash(shocks: Mapping[str, float] | None = None, magnitude: float = -0.20) -> Scenario:
    return Scenario("equity_crash", asset_shocks=shocks or {"equity": magnitude})


def volatility_shock(change: float = 0.10) -> Scenario:
    return Scenario("volatility_shock", volatility_shock=float(change))


def liquidity_stress(multiplier: float = 2.0) -> Scenario:
    return Scenario("liquidity_stress", liquidity_multiplier=float(multiplier))


__all__ = [
    "Scenario",
    "ScenarioResult",
    "run",
    "parallel_rate_shift",
    "steepener",
    "flattener",
    "butterfly",
    "equity_crash",
    "volatility_shock",
    "liquidity_stress",
]
