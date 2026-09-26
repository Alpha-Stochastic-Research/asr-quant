"""Interest-rate P&L explain from curve factor moves."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .contracts import ResultMixin
from .interest_rates import DiscountCurve, carry_roll_down


@dataclass
class RatePnLExplain(ResultMixin):
    contributions: pd.Series
    curve_move_bp: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="rates_pnl_explain", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.concat([self.contributions, self.curve_move_bp.add_prefix("curve_move_bp:")])

    def to_frame(self) -> pd.DataFrame:
        return self.contributions.rename("pnl").to_frame()


def _curve_from_zero(base: DiscountCurve, times: np.ndarray, zero: np.ndarray, name: str) -> DiscountCurve:
    return DiscountCurve.from_zero_rates(times, zero, interpolation=base.interpolation, name=name, metadata=base.metadata)


def pnl_explain(instrument: Any, curve_t0: DiscountCurve, curve_t1: DiscountCurve) -> RatePnLExplain:
    """Explain rate-instrument P&L into parallel, slope, curvature and residual moves.

    The zero-rate change is projected onto level/slope/curvature basis functions.
    Contributions are sequential repricings; residual captures the part of the
    curve move not represented by the three-factor projection.
    """
    if not hasattr(instrument, "price"):
        raise TypeError("instrument must expose price(curve)")
    times = curve_t0.times[curve_t0.times > 0]
    if len(times) < 2 or np.any(times > curve_t1.times[-1] + 1e-12):
        raise ValueError("curves require a common positive-maturity domain")
    z0 = np.asarray(curve_t0.zero_rate(times), dtype=float)
    z1 = np.asarray(curve_t1.zero_rate(times), dtype=float)
    dz = z1 - z0
    if len(times) == 2:
        x = np.linspace(-1.0, 1.0, len(times))
    else:
        center = 0.5 * (times[0] + times[-1])
        half = max(1e-12, 0.5 * (times[-1] - times[0]))
        x = (times - center) / half
    hump = 1.0 - 2.0 * x**2
    design = np.column_stack([np.ones(len(times)), x, hump])
    coeff, *_ = np.linalg.lstsq(design, dz, rcond=None)
    p0 = float(instrument.price(curve_t0))
    c_level = _curve_from_zero(curve_t0, times, z0 + coeff[0], "pnl-level")
    c_slope = _curve_from_zero(curve_t0, times, z0 + coeff[0] + coeff[1] * x, "pnl-slope")
    c_curve = _curve_from_zero(curve_t0, times, z0 + design @ coeff, "pnl-lsc")
    p_level = float(instrument.price(c_level))
    p_slope = float(instrument.price(c_slope))
    p_curve = float(instrument.price(c_curve))
    p1 = float(instrument.price(curve_t1))
    contributions = pd.Series(
        {
            "parallel": p_level - p0,
            "slope": p_slope - p_level,
            "curvature": p_curve - p_slope,
            "residual": p1 - p_curve,
            "total": p1 - p0,
        },
        name="pnl",
    )
    moves = pd.Series({"parallel": coeff[0] * 1e4, "slope": coeff[1] * 1e4, "curvature": coeff[2] * 1e4})
    return RatePnLExplain(contributions, moves, metadata={"base_pv": p0, "final_pv": p1, "curve_nodes": len(times)})


def zero_coupon_carry_roll(curve: DiscountCurve, maturity: float, horizon: float, *, face: float = 1.0) -> pd.Series:
    """Expose the existing static-curve zero-coupon carry/roll decomposition."""
    return carry_roll_down(curve, maturity, horizon, face=face)


__all__ = ["RatePnLExplain", "pnl_explain", "zero_coupon_carry_roll"]
