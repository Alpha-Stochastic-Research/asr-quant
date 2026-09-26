"""Credit term-structure foundations for ASRQuant 1.3.0."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Any
import numpy as np
import pandas as pd
from scipy.optimize import brentq


@dataclass(frozen=True)
class HazardCurve:
    """Piecewise-constant hazard curve on increasing year-fraction pillars."""
    times: np.ndarray
    hazards: np.ndarray
    recovery: float = 0.40
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        t = np.asarray(self.times, dtype=float); h = np.asarray(self.hazards, dtype=float)
        if t.ndim != 1 or h.ndim != 1 or len(t) == 0 or len(t) != len(h):
            raise ValueError("times and hazards must be non-empty one-dimensional arrays of equal length")
        if np.any(t <= 0) or np.any(np.diff(t) <= 0) or np.any(h < 0):
            raise ValueError("times must be positive/increasing and hazards non-negative")
        if not 0 <= self.recovery < 1:
            raise ValueError("recovery must lie in [0,1)")
        object.__setattr__(self, "times", t); object.__setattr__(self, "hazards", h)

    def cumulative_hazard(self, maturity: float | np.ndarray) -> float | np.ndarray:
        x = np.asarray(maturity, dtype=float)
        if np.any(x < 0): raise ValueError("maturity must be non-negative")
        flat = x.reshape(-1); out = np.zeros_like(flat); starts = np.r_[0.0, self.times[:-1]]
        for left, right, hazard in zip(starts, self.times, self.hazards):
            out += hazard * np.maximum(np.minimum(flat, right) - left, 0.0)
        beyond = flat > self.times[-1]; out[beyond] += self.hazards[-1] * (flat[beyond] - self.times[-1])
        out = out.reshape(x.shape); return float(out) if out.ndim == 0 else out

    def survival(self, maturity: float | np.ndarray) -> float | np.ndarray:
        out = np.exp(-np.asarray(self.cumulative_hazard(maturity))); return float(out) if out.ndim == 0 else out

    def default_probability(self, start: float, end: float) -> float:
        if not 0 <= start < end: raise ValueError("require 0 <= start < end")
        return float(self.survival(start) - self.survival(end))

    def table(self) -> pd.DataFrame:
        return pd.DataFrame({"maturity": self.times, "hazard": self.hazards, "survival": self.survival(self.times)})


def _df(discount_curve, maturity):
    if hasattr(discount_curve, "df"): return np.asarray(discount_curve.df(maturity), dtype=float)
    if callable(discount_curve): return np.asarray(discount_curve(maturity), dtype=float)
    return np.exp(-float(discount_curve) * np.asarray(maturity, dtype=float))


def cds_legs(curve: HazardCurve, discount_curve, maturity: float, spread: float, *, frequency: int = 4, notional: float = 1.0) -> dict[str, float]:
    if maturity <= 0 or spread < 0 or frequency <= 0 or notional <= 0: raise ValueError("invalid CDS inputs")
    n = int(round(maturity * frequency))
    if n < 1 or not np.isclose(n / frequency, maturity, atol=1e-10): raise ValueError("maturity must lie on the regular payment grid")
    times = np.arange(1, n + 1, dtype=float) / frequency; prev = np.r_[0.0, times[:-1]]
    q = np.asarray(curve.survival(times), dtype=float); q_prev = np.asarray(curve.survival(prev), dtype=float); default_prob = q_prev - q
    disc = _df(discount_curve, times); mid_disc = _df(discount_curve, 0.5 * (prev + times)); accrual = 1.0 / frequency
    risky_annuity = float(np.sum(accrual * disc * q) + np.sum(0.5 * accrual * mid_disc * default_prob))
    protection_unit = float((1.0 - curve.recovery) * np.sum(mid_disc * default_prob))
    premium = notional * spread * risky_annuity; protection = notional * protection_unit
    return {"premium_leg": premium, "protection_leg": protection, "risky_annuity": risky_annuity, "protection_unit": protection_unit, "pv": protection-premium}


def cds_par_spread(curve: HazardCurve, discount_curve, maturity: float, *, frequency: int = 4) -> float:
    legs = cds_legs(curve, discount_curve, maturity, 0.0, frequency=frequency); annuity = legs["risky_annuity"]
    return float(legs["protection_unit"] / annuity) if annuity > 0 else np.nan


def cds_cs01(curve: HazardCurve, discount_curve, maturity: float, spread: float, *, bump: float = 1e-4, frequency: int = 4) -> float:
    base = cds_legs(curve, discount_curve, maturity, spread, frequency=frequency)["pv"]
    bumped = cds_legs(curve, discount_curve, maturity, spread + bump, frequency=frequency)["pv"]
    return float(bumped - base)


def jump_to_default(curve: HazardCurve, notional: float = 1.0) -> float:
    if notional <= 0: raise ValueError("notional must be positive")
    return float((1.0 - curve.recovery) * notional)


def bootstrap_hazard_curve(maturities: Sequence[float], spreads: Sequence[float], discount_curve, *, recovery: float = 0.40, frequency: int = 4, hazard_upper: float = 10.0) -> HazardCurve:
    mats = np.asarray(maturities, dtype=float); spr = np.asarray(spreads, dtype=float)
    if mats.ndim != 1 or len(mats) != len(spr) or len(mats) == 0: raise ValueError("maturities and spreads must have equal non-zero length")
    if np.any(np.diff(mats) <= 0) or np.any(spr < 0): raise ValueError("maturities must increase and spreads must be non-negative")
    hazards: list[float] = []
    for i, maturity in enumerate(mats):
        target = float(spr[i])
        def objective(last_hazard: float) -> float:
            trial = HazardCurve(mats[: i+1], np.asarray(hazards + [last_hazard]), recovery)
            return cds_par_spread(trial, discount_curve, float(maturity), frequency=frequency) - target
        lo, hi = 0.0, hazard_upper; f_lo, f_hi = objective(lo), objective(hi)
        if abs(f_lo) < 1e-14: root = 0.0
        elif f_lo * f_hi > 0: raise ValueError(f"cannot bracket hazard for maturity {maturity:g}")
        else: root = float(brentq(objective, lo, hi, xtol=1e-13, rtol=1e-12, maxiter=200))
        hazards.append(root)
    curve = HazardCurve(mats, np.asarray(hazards), recovery, {"source": "cds_bootstrap", "spreads": spr.tolist()})
    repricing = np.array([cds_par_spread(curve, discount_curve, float(m), frequency=frequency) for m in mats])
    object.__setattr__(curve, "metadata", {**(curve.metadata or {}), "max_repricing_error": float(np.max(np.abs(repricing-spr)))})
    return curve


__all__ = ["HazardCurve", "cds_legs", "cds_par_spread", "cds_cs01", "jump_to_default", "bootstrap_hazard_curve"]
