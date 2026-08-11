"""Typed experiment specifications and execution-cost contracts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Literal


class MissingDataPolicy(str, Enum):
    """How missing observations are handled before return calculation."""

    RAISE = "raise"
    DROP = "drop"
    FFILL = "ffill"


class RebalanceFrequency(str, Enum):
    """Common rebalance frequencies."""

    BAR = "bar"
    DAILY = "D"
    WEEKLY = "W-FRI"
    MONTHLY = "ME"
    QUARTERLY = "QE"


@dataclass(frozen=True)
class CostModel:
    """Transparent transaction- and financing-cost model.

    All rates are expressed in basis points except ``impact_coefficient``.
    The market-impact charge is ``impact_coefficient * turnover**impact_exponent``.
    """

    commission_bps: float = 0.0
    spread_bps: float = 0.0
    slippage_bps: float = 0.0
    borrow_bps_annual: float = 0.0
    impact_coefficient: float = 0.0
    impact_exponent: float = 1.5

    def validate(self) -> None:
        values = asdict(self)
        for key, value in values.items():
            if key != "impact_exponent" and value < 0:
                raise ValueError(f"{key} must be non-negative")
        if self.impact_exponent < 1:
            raise ValueError("impact_exponent must be >= 1")

    @property
    def linear_bps(self) -> float:
        return self.commission_bps + self.spread_bps + self.slippage_bps


@dataclass(frozen=True)
class BacktestSpec:
    """A complete, serializable contract for a weight-based backtest.

    ``execution_delay=1`` means a target formed at timestamp *t* is first used
    for the return ending at timestamp *t+1*. ``execution_delay=0`` is allowed
    for diagnostics, but is explicitly flagged as a potential same-bar leak.
    """

    initial_capital: float = 100_000.0
    annualization: int = 252
    execution_delay: int = 1
    rebalance: str = "bar"
    long_only: bool = False
    max_gross_leverage: float = 1.0
    max_abs_weight: float = 1.0
    risk_free_rate: float = 0.0
    missing_data: MissingDataPolicy = MissingDataPolicy.RAISE
    costs: CostModel = field(default_factory=CostModel)
    name: str = "ASRQuant backtest"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.annualization <= 0:
            raise ValueError("annualization must be positive")
        if self.execution_delay < 0:
            raise ValueError("execution_delay must be >= 0")
        if self.max_gross_leverage <= 0:
            raise ValueError("max_gross_leverage must be positive")
        if not 0 < self.max_abs_weight <= self.max_gross_leverage:
            raise ValueError("max_abs_weight must be positive and <= max_gross_leverage")
        self.costs.validate()

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["missing_data"] = self.missing_data.value
        return raw

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str).encode("utf-8")
        return sha256(payload).hexdigest()[:16]

    def with_updates(self, **updates: Any) -> "BacktestSpec":
        payload = self.to_dict()
        payload.update(updates)
        if isinstance(payload.get("costs"), dict):
            payload["costs"] = CostModel(**payload["costs"])
        payload["missing_data"] = MissingDataPolicy(payload["missing_data"])
        return BacktestSpec(**payload)


@dataclass(frozen=True)
class PlotConfig:
    """Shared plotting options."""

    backend: Literal["matplotlib", "plotly"] = "matplotlib"
    figsize: tuple[float, float] = (10.0, 5.5)
    title: str | None = None
    show: bool = False
