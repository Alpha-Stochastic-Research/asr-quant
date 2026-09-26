"""Reduced-form credit curves and transparent CDS analytics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .contracts import CalibrationError, PricingError, ResultMixin
from .interest_rates import DiscountCurve, payment_schedule


@dataclass(frozen=True)
class HazardCurve:
    """Piecewise-constant hazard-rate curve.

    ``times`` are increasing segment end dates in years and ``hazards`` are the
    annualized intensities applying from the previous node to each segment end.
    The last hazard is extrapolated flat beyond the final node.
    """

    times: np.ndarray
    hazards: np.ndarray
    recovery: float = 0.40
    name: str = "hazard"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        t = np.asarray(self.times, dtype=float)
        h = np.asarray(self.hazards, dtype=float)
        if t.ndim != 1 or h.ndim != 1 or len(t) != len(h) or len(t) == 0:
            raise ValueError("times and hazards must be matching non-empty vectors")
        if np.any(t <= 0) or np.any(np.diff(t) <= 0):
            raise ValueError("times must be strictly increasing and positive")
        if np.any(h < 0):
            raise ValueError("hazard rates must be non-negative")
        if not 0 <= self.recovery < 1:
            raise ValueError("recovery must lie in [0, 1)")
        object.__setattr__(self, "times", t)
        object.__setattr__(self, "hazards", h)

    @classmethod
    def constant(cls, hazard: float, maturity: float = 30.0, *, recovery: float = 0.40, name: str = "constant") -> "HazardCurve":
        return cls(np.array([float(maturity)]), np.array([float(hazard)]), recovery=recovery, name=name)

    def integrated_hazard(self, maturity: float | np.ndarray):
        x = np.asarray(maturity, dtype=float)
        if np.any(x < 0):
            raise ValueError("maturity must be non-negative")
        flat = x.ravel()
        out = np.zeros_like(flat)
        for j, val in enumerate(flat):
            total = 0.0
            left = 0.0
            for end, hazard in zip(self.times, self.hazards):
                if val <= left:
                    break
                segment_end = min(val, float(end))
                total += float(hazard) * max(0.0, segment_end - left)
                if val <= end:
                    break
                left = float(end)
            if val > self.times[-1]:
                total += float(self.hazards[-1]) * (val - float(self.times[-1]))
            out[j] = total
        out = out.reshape(x.shape)
        return float(out) if out.ndim == 0 else out

    def survival(self, maturity: float | np.ndarray):
        value = np.exp(-np.asarray(self.integrated_hazard(maturity), dtype=float))
        return float(value) if value.ndim == 0 else value

    def default_probability(self, start: float, end: float) -> float:
        if end < start or start < 0:
            raise ValueError("require 0 <= start <= end")
        return float(self.survival(start) - self.survival(end))

    def hazard(self, maturity: float) -> float:
        if maturity < 0:
            raise ValueError("maturity must be non-negative")
        idx = int(np.searchsorted(self.times, maturity, side="left"))
        idx = min(idx, len(self.hazards) - 1)
        return float(self.hazards[idx])

    def bump(self, spread_bump: float, *, recovery: float | None = None) -> "HazardCurve":
        rec = self.recovery if recovery is None else recovery
        if not 0 <= rec < 1:
            raise ValueError("recovery must lie in [0, 1)")
        hazard_bump = spread_bump / max(1e-12, 1.0 - rec)
        return HazardCurve(self.times, np.maximum(self.hazards + hazard_bump, 0.0), self.recovery, self.name, self.metadata)

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "maturity": self.times,
                "hazard_rate": self.hazards,
                "survival_probability": np.asarray(self.survival(self.times), dtype=float),
                "cumulative_default_probability": 1.0 - np.asarray(self.survival(self.times), dtype=float),
            }
        )


@dataclass
class CDSAnalytics(ResultMixin):
    pv: float
    premium_leg: float
    protection_leg: float
    risky_annuity: float
    par_spread: float
    cs01: float
    jump_to_default: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="cds_analytics", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "pv": self.pv,
                "premium_leg": self.premium_leg,
                "protection_leg": self.protection_leg,
                "risky_annuity": self.risky_annuity,
                "par_spread": self.par_spread,
                "cs01": self.cs01,
                "jump_to_default": self.jump_to_default,
            }
        )


@dataclass(frozen=True)
class CDS:
    maturity: float
    spread: float
    notional: float = 1.0
    payment_frequency: int = 4
    recovery: float = 0.40
    position: str = "protection_buyer"

    def __post_init__(self) -> None:
        if self.maturity <= 0 or self.notional <= 0 or self.payment_frequency <= 0:
            raise PricingError("maturity, notional and payment_frequency must be positive")
        if self.spread < 0 or not 0 <= self.recovery < 1:
            raise PricingError("spread must be non-negative and recovery in [0,1)")
        if self.position not in {"protection_buyer", "protection_seller"}:
            raise PricingError("position must be protection_buyer or protection_seller")

    @property
    def payment_times(self) -> np.ndarray:
        return payment_schedule(0.0, self.maturity, self.payment_frequency)

    def legs(self, discount: DiscountCurve, hazard: HazardCurve) -> dict[str, float]:
        times = self.payment_times
        starts = np.r_[0.0, times[:-1]]
        alpha = times - starts
        surv_end = np.asarray(hazard.survival(times), dtype=float)
        surv_start = np.asarray(hazard.survival(starts), dtype=float)
        defaults = surv_start - surv_end
        dfs = np.asarray(discount.df(times), dtype=float)
        risky_annuity = float(np.sum(alpha * dfs * surv_end + 0.5 * alpha * dfs * defaults))
        protection_unit = float((1.0 - self.recovery) * np.sum(dfs * defaults))
        premium = self.notional * self.spread * risky_annuity
        protection = self.notional * protection_unit
        return {
            "risky_annuity": risky_annuity,
            "premium_leg": premium,
            "protection_leg": protection,
        }

    def par_spread(self, discount: DiscountCurve, hazard: HazardCurve) -> float:
        legs = self.legs(discount, hazard)
        annuity = legs["risky_annuity"]
        return float((legs["protection_leg"] / self.notional) / annuity) if annuity > 0 else np.nan

    def price(self, discount: DiscountCurve, hazard: HazardCurve) -> float:
        legs = self.legs(discount, hazard)
        buyer = legs["protection_leg"] - legs["premium_leg"]
        return float(buyer if self.position == "protection_buyer" else -buyer)

    def analytics(self, discount: DiscountCurve, hazard: HazardCurve, bump: float = 1e-4) -> CDSAnalytics:
        legs = self.legs(discount, hazard)
        base = self.price(discount, hazard)
        up = self.price(discount, hazard.bump(bump, recovery=self.recovery))
        down = self.price(discount, hazard.bump(-bump, recovery=self.recovery))
        cs01 = (up - down) / 2.0
        jtd_buyer = self.notional * (1.0 - self.recovery) - base
        jtd = jtd_buyer if self.position == "protection_buyer" else -jtd_buyer
        return CDSAnalytics(
            pv=base,
            premium_leg=legs["premium_leg"],
            protection_leg=legs["protection_leg"],
            risky_annuity=legs["risky_annuity"],
            par_spread=self.par_spread(discount, hazard),
            cs01=float(cs01),
            jump_to_default=float(jtd),
            metadata={"maturity": self.maturity, "recovery": self.recovery, "bump": bump},
        )


def bootstrap_hazard_curve(
    discount: DiscountCurve,
    maturities: Sequence[float],
    spreads: Sequence[float],
    *,
    recovery: float = 0.40,
    payment_frequency: int = 4,
    max_hazard: float = 5.0,
) -> HazardCurve:
    """Sequentially bootstrap piecewise-constant hazards from par CDS spreads."""
    t = np.asarray(maturities, dtype=float)
    s = np.asarray(spreads, dtype=float)
    if t.ndim != 1 or s.shape != t.shape or len(t) == 0:
        raise CalibrationError("maturities and spreads must be matching non-empty vectors")
    order = np.argsort(t)
    t, s = t[order], s[order]
    if np.any(t <= 0) or np.any(np.diff(t) <= 0) or np.any(s < 0):
        raise CalibrationError("maturities must increase and spreads must be non-negative")
    hazards: list[float] = []
    for maturity, spread in zip(t, s):
        def objective(h: float) -> float:
            curve = HazardCurve(t[: len(hazards) + 1], np.asarray(hazards + [h]), recovery=recovery)
            cds = CDS(float(maturity), float(spread), payment_frequency=payment_frequency, recovery=recovery)
            return cds.price(discount, curve)
        try:
            f0, f1 = objective(1e-12), objective(max_hazard)
            if f0 == 0:
                solved = 0.0
            elif f0 * f1 > 0:
                raise CalibrationError(f"could not bracket hazard for maturity {maturity:g}")
            else:
                solved = float(brentq(objective, 1e-12, max_hazard, xtol=1e-12, rtol=1e-10))
        except Exception as exc:
            if isinstance(exc, CalibrationError):
                raise
            raise CalibrationError(f"CDS hazard bootstrap failed at {maturity:g}Y: {exc}") from exc
        hazards.append(solved)
    return HazardCurve(t, np.asarray(hazards), recovery=recovery, name="cds_bootstrap")


__all__ = ["HazardCurve", "CDS", "CDSAnalytics", "bootstrap_hazard_curve"]
