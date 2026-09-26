"""Composable transaction-cost models for research and capacity analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd

from .contracts import ResultMixin


@dataclass(frozen=True)
class CostContext:
    trade_value: float
    adv_value: float | None = None
    volatility: float | None = None
    spread_bps: float | None = None

    def __post_init__(self) -> None:
        if self.trade_value < 0:
            raise ValueError("trade_value must be non-negative")
        if self.adv_value is not None and self.adv_value <= 0:
            raise ValueError("adv_value must be positive")
        if self.volatility is not None and self.volatility < 0:
            raise ValueError("volatility must be non-negative")
        if self.spread_bps is not None and self.spread_bps < 0:
            raise ValueError("spread_bps must be non-negative")


@dataclass
class CostEstimate(ResultMixin):
    total_cost: float
    total_bps: float
    breakdown: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="transaction_cost", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series({"total_cost": self.total_cost, "total_bps": self.total_bps, "components": len(self.breakdown)})

    def to_frame(self) -> pd.DataFrame:
        return self.breakdown.rename("cost").to_frame()


class FixedBps:
    def __init__(self, bps: float) -> None:
        if bps < 0:
            raise ValueError("bps must be non-negative")
        self.bps = float(bps)

    def estimate(self, context: CostContext) -> float:
        return context.trade_value * self.bps / 10_000.0


class HalfSpread:
    def __init__(self, spread_bps: float | None = None) -> None:
        if spread_bps is not None and spread_bps < 0:
            raise ValueError("spread_bps must be non-negative")
        self.spread_bps = spread_bps

    def estimate(self, context: CostContext) -> float:
        spread = self.spread_bps if self.spread_bps is not None else context.spread_bps
        if spread is None:
            raise ValueError("spread_bps must be supplied in model or context")
        return context.trade_value * float(spread) / 20_000.0


class LinearImpact:
    def __init__(self, coefficient: float) -> None:
        if coefficient < 0:
            raise ValueError("coefficient must be non-negative")
        self.coefficient = float(coefficient)

    def estimate(self, context: CostContext) -> float:
        if context.adv_value is None:
            raise ValueError("adv_value is required for impact models")
        participation = context.trade_value / context.adv_value
        return context.trade_value * self.coefficient * participation


class SquareRootImpact:
    """Square-root market-impact model: cost fraction = eta * sigma * sqrt(Q/ADV)."""

    def __init__(self, eta: float = 0.5) -> None:
        if eta < 0:
            raise ValueError("eta must be non-negative")
        self.eta = float(eta)

    def estimate(self, context: CostContext) -> float:
        if context.adv_value is None or context.volatility is None:
            raise ValueError("adv_value and volatility are required for square-root impact")
        participation = context.trade_value / context.adv_value
        return context.trade_value * self.eta * context.volatility * np.sqrt(max(participation, 0.0))


class CompositeCostModel:
    def __init__(self, *models: Any) -> None:
        if not models:
            raise ValueError("provide at least one cost model")
        self.models = list(models)

    def estimate(self, context: CostContext) -> CostEstimate:
        values: dict[str, float] = {}
        for i, model in enumerate(self.models):
            if not hasattr(model, "estimate"):
                raise TypeError("every cost model must expose estimate(context)")
            name = type(model).__name__
            if name in values:
                name = f"{name}_{i + 1}"
            values[name] = float(model.estimate(context))
        breakdown = pd.Series(values, name="cost")
        total = float(breakdown.sum())
        bps = 10_000.0 * total / context.trade_value if context.trade_value > 0 else 0.0
        return CostEstimate(total, bps, breakdown, metadata={"trade_value": context.trade_value})


__all__ = [
    "CostContext",
    "CostEstimate",
    "FixedBps",
    "HalfSpread",
    "LinearImpact",
    "SquareRootImpact",
    "CompositeCostModel",
]
