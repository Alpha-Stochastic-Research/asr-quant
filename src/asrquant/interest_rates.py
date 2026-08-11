"""Interest-rate and fixed-income derivatives research toolkit.

The module is intentionally dependency-light and transparent.  It provides the
building blocks required by a quant researcher to move from curve construction
to instrument pricing, risk, volatility modelling, short-rate models and
research diagnostics without hiding conventions behind opaque objects.

All rates are decimals (``0.03`` means 3%) and all maturities/accruals are year
fractions unless dates are explicitly supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares
from scipy.stats import norm

from .fixed_income import (
    bond_cashflows,
    bond_price,
    bootstrap_zero_curve,
    convexity,
    macaulay_duration,
    modified_duration,
    yield_to_maturity,
    zero_coupon_price,
)


ArrayLike = float | Sequence[float] | np.ndarray


def _as_float_array(values: ArrayLike) -> np.ndarray:
    return np.asarray(values, dtype=float)


def _scalar_or_array(value: np.ndarray):
    return float(value) if value.ndim == 0 else value


def _validate_positive_times(times: np.ndarray) -> None:
    if times.ndim != 1 or len(times) == 0:
        raise ValueError("times must be a non-empty one-dimensional array")
    if np.any(times < 0) or np.any(np.diff(times) <= 0):
        raise ValueError("times must be strictly increasing and non-negative")


def year_fraction(start: date | datetime | str, end: date | datetime | str, convention: str = "ACT/365F") -> float:
    """Return a year fraction for common money-market/bond day-count bases.

    Supported conventions: ``ACT/360``, ``ACT/365F``, ``30/360``, ``30E/360``.
    """
    s = pd.Timestamp(start).date()
    e = pd.Timestamp(end).date()
    if e < s:
        raise ValueError("end must not precede start")
    conv = convention.upper().replace(" ", "")
    if conv in {"ACT/360", "ACT360"}:
        return (e - s).days / 360.0
    if conv in {"ACT/365F", "ACT365F", "ACT/365", "ACT365"}:
        return (e - s).days / 365.0
    if conv in {"30/360", "30U/360", "BOND"}:
        d1 = min(s.day, 30)
        d2 = min(e.day, 30) if d1 == 30 else e.day
        return ((e.year - s.year) * 360 + (e.month - s.month) * 30 + d2 - d1) / 360.0
    if conv in {"30E/360", "30E360"}:
        d1, d2 = min(s.day, 30), min(e.day, 30)
        return ((e.year - s.year) * 360 + (e.month - s.month) * 30 + d2 - d1) / 360.0
    raise ValueError("unsupported day-count convention")



def maturity_to_years(maturity: str | float | int) -> float:
    """Convert a compact money-market maturity such as ``3M`` or ``10Y`` to years."""
    if isinstance(maturity, (int, float, np.integer, np.floating)):
        value = float(maturity)
        if value <= 0:
            raise ValueError("maturity must be positive")
        return value
    text = str(maturity).strip().upper()
    if not text:
        raise ValueError("maturity must not be empty")
    unit = text[-1]
    try:
        amount = float(text[:-1])
    except ValueError as exc:
        raise ValueError(f"invalid maturity {maturity!r}") from exc
    if amount <= 0:
        raise ValueError("maturity must be positive")
    if unit == "D":
        return amount / 365.0
    if unit == "W":
        return amount * 7.0 / 365.0
    if unit == "M":
        return amount / 12.0
    if unit == "Y":
        return amount
    raise ValueError("maturity unit must be D, W, M, or Y")


def payment_schedule(start: float, end: float, frequency: int = 2) -> np.ndarray:
    """Generate a regular year-fraction payment schedule including ``end``."""
    if end <= start or frequency <= 0:
        raise ValueError("require end > start and positive frequency")
    step = 1.0 / frequency
    n = int(round((end - start) * frequency))
    if n < 1 or not np.isclose(start + n * step, end, atol=1e-10):
        raise ValueError("start/end must lie on the requested regular payment grid")
    return start + step * np.arange(1, n + 1)


def discount_factor(rate: ArrayLike, maturity: ArrayLike, compounding: str | int = "continuous"):
    """Convert zero rates to discount factors under common compounding rules."""
    r, t = np.broadcast_arrays(_as_float_array(rate), _as_float_array(maturity))
    if np.any(t < 0):
        raise ValueError("maturity must be non-negative")
    if isinstance(compounding, str):
        c = compounding.lower()
        if c in {"continuous", "cont", "cc"}:
            out = np.exp(-r * t)
        elif c in {"simple", "money_market"}:
            denom = 1.0 + r * t
            if np.any(denom <= 0):
                raise ValueError("simple-compounding denominator must be positive")
            out = 1.0 / denom
        else:
            raise ValueError("compounding must be continuous, simple, or a positive integer")
    else:
        m = int(compounding)
        if m <= 0:
            raise ValueError("compounding frequency must be positive")
        base = 1.0 + r / m
        if np.any(base <= 0):
            raise ValueError("periodic-compounding base must be positive")
        out = base ** (-m * t)
    return _scalar_or_array(out)


def zero_rate_from_discount(discount: ArrayLike, maturity: ArrayLike, compounding: str | int = "continuous"):
    """Convert discount factors to zero rates."""
    p, t = np.broadcast_arrays(_as_float_array(discount), _as_float_array(maturity))
    if np.any(p <= 0) or np.any(t <= 0):
        raise ValueError("discount factors and maturities must be positive")
    if isinstance(compounding, str):
        c = compounding.lower()
        if c in {"continuous", "cont", "cc"}:
            out = -np.log(p) / t
        elif c in {"simple", "money_market"}:
            out = (1.0 / p - 1.0) / t
        else:
            raise ValueError("compounding must be continuous, simple, or a positive integer")
    else:
        m = int(compounding)
        if m <= 0:
            raise ValueError("compounding frequency must be positive")
        out = m * (p ** (-1.0 / (m * t)) - 1.0)
    return _scalar_or_array(out)


def forward_discount_factor(p_start: ArrayLike, p_end: ArrayLike):
    """Return ``P(0,T2)/P(0,T1)``."""
    p1, p2 = np.broadcast_arrays(_as_float_array(p_start), _as_float_array(p_end))
    if np.any(p1 <= 0) or np.any(p2 <= 0):
        raise ValueError("discount factors must be positive")
    return _scalar_or_array(p2 / p1)


def forward_rate_from_discounts(
    p_start: ArrayLike,
    p_end: ArrayLike,
    start: ArrayLike,
    end: ArrayLike,
    compounding: str = "simple",
):
    """Return a forward rate implied by two discount factors."""
    p1, p2, t1, t2 = np.broadcast_arrays(
        _as_float_array(p_start), _as_float_array(p_end), _as_float_array(start), _as_float_array(end)
    )
    tau = t2 - t1
    if np.any(p1 <= 0) or np.any(p2 <= 0) or np.any(tau <= 0):
        raise ValueError("discounts must be positive and end must exceed start")
    if compounding.lower() in {"simple", "money_market"}:
        out = (p1 / p2 - 1.0) / tau
    elif compounding.lower() in {"continuous", "cont", "cc"}:
        out = np.log(p1 / p2) / tau
    else:
        raise ValueError("forward compounding must be simple or continuous")
    return _scalar_or_array(out)


@dataclass(frozen=True)
class DiscountCurve:
    """Arbitrage-aware discount curve with transparent interpolation.

    ``log_linear`` interpolation is the default because interpolation in log
    discount factors produces piecewise-constant instantaneous forward rates
    and preserves positivity.
    """

    times: np.ndarray
    discounts: np.ndarray
    interpolation: str = "log_linear"
    name: str = "discount"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        t = np.asarray(self.times, dtype=float)
        p = np.asarray(self.discounts, dtype=float)
        if t.ndim != 1 or p.ndim != 1 or len(t) != len(p):
            raise ValueError("times and discounts must be one-dimensional with equal length")
        _validate_positive_times(t)
        if np.any(p <= 0):
            raise ValueError("discount factors must be positive")
        if t[0] > 0:
            t = np.insert(t, 0, 0.0)
            p = np.insert(p, 0, 1.0)
        elif not np.isclose(p[0], 1.0, atol=1e-8):
            raise ValueError("discount factor at time zero must equal one")
        object.__setattr__(self, "times", t)
        object.__setattr__(self, "discounts", p)
        if self.interpolation not in {"log_linear", "linear_zero", "linear_discount"}:
            raise ValueError("unsupported interpolation")

    @classmethod
    def from_zero_rates(
        cls,
        times: ArrayLike,
        zero_rates: ArrayLike,
        *,
        compounding: str | int = "continuous",
        interpolation: str = "log_linear",
        name: str = "discount",
        metadata: Mapping[str, Any] | None = None,
    ) -> "DiscountCurve":
        t = _as_float_array(times)
        r = _as_float_array(zero_rates)
        if len(t) != len(r):
            raise ValueError("times and zero_rates must have equal length")
        p = _as_float_array(discount_factor(r, t, compounding=compounding))
        return cls(t, p, interpolation=interpolation, name=name, metadata=metadata or {})

    def df(self, maturity: ArrayLike):
        x = _as_float_array(maturity)
        if np.any(x < 0) or np.any(x > self.times[-1] + 1e-12):
            raise ValueError("maturity must lie within the curve domain")
        if self.interpolation == "log_linear":
            out = np.exp(np.interp(x, self.times, np.log(self.discounts)))
        elif self.interpolation == "linear_discount":
            out = np.interp(x, self.times, self.discounts)
        else:
            positive = self.times > 0
            zero = -np.log(self.discounts[positive]) / self.times[positive]
            if len(zero) == 0:
                out = np.ones_like(x, dtype=float)
            else:
                r = np.interp(x, self.times[positive], zero, left=zero[0], right=zero[-1])
                out = np.exp(-r * x)
                out = np.where(x == 0, 1.0, out)
        return _scalar_or_array(np.asarray(out))

    def zero_rate(self, maturity: ArrayLike, compounding: str | int = "continuous"):
        x = _as_float_array(maturity)
        if np.any(x <= 0):
            raise ValueError("zero-rate maturity must be positive")
        return zero_rate_from_discount(self.df(x), x, compounding=compounding)

    def forward_rate(self, start: ArrayLike, end: ArrayLike, compounding: str = "simple"):
        s, e = np.broadcast_arrays(_as_float_array(start), _as_float_array(end))
        return forward_rate_from_discounts(self.df(s), self.df(e), s, e, compounding=compounding)

    def instantaneous_forward(self, maturity: ArrayLike, bump: float = 1e-4):
        x = _as_float_array(maturity)
        if np.any(x <= 0) or np.any(x >= self.times[-1]):
            raise ValueError("maturity must be inside (0, curve_end)")
        h = np.minimum(bump, np.minimum(x * 0.5, (self.times[-1] - x) * 0.5))
        out = -(np.log(self.df(x + h)) - np.log(self.df(x - h))) / (2.0 * h)
        return _scalar_or_array(np.asarray(out))

    def annuity(self, payment_times: ArrayLike, accruals: ArrayLike | None = None) -> float:
        t = _as_float_array(payment_times)
        a = np.full(len(t), np.nan) if accruals is None else _as_float_array(accruals)
        if accruals is None:
            a = np.diff(np.r_[0.0, t])
        if len(t) != len(a) or np.any(a <= 0):
            raise ValueError("payment_times and accruals must have compatible positive values")
        return float(np.sum(a * _as_float_array(self.df(t))))

    def par_swap_rate(self, start: float, end: float, frequency: int = 2) -> float:
        times = payment_schedule(start, end, frequency)
        accruals = np.full(len(times), 1.0 / frequency)
        ann = float(np.sum(accruals * _as_float_array(self.df(times))))
        return float((self.df(start) - self.df(end)) / ann)

    def bump_parallel(self, bump: float = 1e-4) -> "DiscountCurve":
        t = self.times.copy()
        p = self.discounts.copy()
        positive = t > 0
        z = -np.log(p[positive]) / t[positive]
        p[positive] = np.exp(-(z + bump) * t[positive])
        return DiscountCurve(t, p, self.interpolation, self.name + f"+{bump:g}", self.metadata)

    def bump_key_rate(self, maturity: float, bump: float = 1e-4, width: float | None = None) -> "DiscountCurve":
        if maturity <= 0 or maturity > self.times[-1]:
            raise ValueError("key-rate maturity must lie in the curve domain")
        t = self.times.copy()
        p = self.discounts.copy()
        positive = t > 0
        z = -np.log(p[positive]) / t[positive]
        tp = t[positive]
        if width is None:
            idx = int(np.argmin(np.abs(tp - maturity)))
            left = tp[max(0, idx - 1)]
            right = tp[min(len(tp) - 1, idx + 1)]
            width = max(maturity - left, right - maturity, 1e-8)
        weights = np.maximum(1.0 - np.abs(tp - maturity) / width, 0.0)
        z_bumped = z + bump * weights
        p[positive] = np.exp(-z_bumped * tp)
        return DiscountCurve(t, p, self.interpolation, self.name + f"_kr{maturity:g}", self.metadata)

    def table(self) -> pd.DataFrame:
        t = self.times[1:] if self.times[0] == 0 else self.times
        return pd.DataFrame(
            {
                "maturity": t,
                "discount_factor": _as_float_array(self.df(t)),
                "zero_rate_cc": _as_float_array(self.zero_rate(t, "continuous")),
            }
        )


@dataclass(frozen=True)
class ForwardCurve:
    """Piecewise-simple forward curve for a single floating-rate tenor."""

    starts: np.ndarray
    ends: np.ndarray
    forwards: np.ndarray
    tenor: str = "generic"

    def __post_init__(self) -> None:
        s, e, f = map(lambda x: np.asarray(x, dtype=float), (self.starts, self.ends, self.forwards))
        if not (s.ndim == e.ndim == f.ndim == 1 and len(s) == len(e) == len(f) and len(s) > 0):
            raise ValueError("starts, ends and forwards must be equal non-empty vectors")
        if np.any(e <= s) or np.any(np.diff(s) < 0):
            raise ValueError("forward periods must be ordered and have end > start")
        object.__setattr__(self, "starts", s)
        object.__setattr__(self, "ends", e)
        object.__setattr__(self, "forwards", f)

    def rate(self, start: float, end: float) -> float:
        mask = np.isclose(self.starts, start) & np.isclose(self.ends, end)
        if not mask.any():
            raise KeyError(f"forward period ({start}, {end}) not found")
        return float(self.forwards[np.flatnonzero(mask)[0]])

    def table(self) -> pd.DataFrame:
        return pd.DataFrame({"start": self.starts, "end": self.ends, "forward_rate": self.forwards, "tenor": self.tenor})


@dataclass(frozen=True)
class MultiCurve:
    """OIS discount curve plus tenor-specific projection curves."""

    discount: DiscountCurve
    projections: Mapping[str, ForwardCurve]

    def forward(self, tenor: str, start: float, end: float) -> float:
        if tenor not in self.projections:
            raise KeyError(f"projection curve {tenor!r} not found")
        return self.projections[tenor].rate(start, end)


def _standardize_quotes(frame: pd.DataFrame | None, required: Sequence[str]) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(columns=required)
    out = pd.DataFrame(frame).copy()
    missing = set(required) - set(out.columns)
    if missing:
        raise ValueError(f"quote table missing columns: {sorted(missing)}")
    for name in required:
        out[name] = pd.to_numeric(out[name], errors="raise")
    return out.sort_values(required[0]).reset_index(drop=True)


def bootstrap_discount_curve(
    *,
    deposits: pd.DataFrame | None = None,
    fras: pd.DataFrame | None = None,
    swaps: pd.DataFrame | None = None,
    swap_frequency: int = 2,
    interpolation: str = "log_linear",
    name: str = "bootstrapped",
) -> DiscountCurve:
    """Bootstrap a single-curve term structure from deposits, FRAs and par swaps.

    Deposit columns: ``maturity, rate``. FRA columns: ``start, end, rate``.
    Swap columns: ``maturity, rate``. Quotes use simple money-market forwards and
    fixed-leg accrual ``1/swap_frequency``.  The function deliberately requires
    the coupon/FRA grid to be fully determined rather than silently interpolating
    missing bootstrap nodes.
    """
    dep = _standardize_quotes(deposits, ["maturity", "rate"])
    fra = _standardize_quotes(fras, ["start", "end", "rate"])
    swp = _standardize_quotes(swaps, ["maturity", "rate"])
    if dep.empty and fra.empty and swp.empty:
        raise ValueError("provide at least one deposit, FRA, or swap quote")
    dfs: dict[float, float] = {0.0: 1.0}
    for row in dep.itertuples(index=False):
        t, r = float(row.maturity), float(row.rate)
        if t <= 0 or 1.0 + r * t <= 0:
            raise ValueError("invalid deposit quote")
        dfs[t] = 1.0 / (1.0 + r * t)
    for row in fra.itertuples(index=False):
        s, e, f = float(row.start), float(row.end), float(row.rate)
        if s not in dfs:
            raise ValueError(f"FRA start {s} is not yet bootstrapped")
        tau = e - s
        if tau <= 0 or 1.0 + f * tau <= 0:
            raise ValueError("invalid FRA quote")
        dfs[e] = dfs[s] / (1.0 + f * tau)
    if not swp.empty:
        if swap_frequency <= 0:
            raise ValueError("swap_frequency must be positive")
        alpha = 1.0 / swap_frequency
        for row in swp.itertuples(index=False):
            maturity, rate = float(row.maturity), float(row.rate)
            times = payment_schedule(0.0, maturity, swap_frequency)
            previous = times[:-1]
            missing = [float(t) for t in previous if float(t) not in dfs]
            if missing:
                raise ValueError(f"swap bootstrap needs discount nodes at {missing}")
            prior_annuity = sum(alpha * dfs[float(t)] for t in previous)
            last = (1.0 - rate * prior_annuity) / (1.0 + rate * alpha)
            if last <= 0:
                raise ValueError("swap quotes imply a non-positive discount factor")
            dfs[float(maturity)] = float(last)
    times = np.array(sorted(dfs), dtype=float)
    discounts = np.array([dfs[t] for t in times], dtype=float)
    return DiscountCurve(times, discounts, interpolation=interpolation, name=name)


def projection_curve_from_discount(discount: DiscountCurve, tenor: float, *, name: str | None = None) -> ForwardCurve:
    """Create a tenor forward curve implied by one discount curve."""
    if tenor <= 0:
        raise ValueError("tenor must be positive")
    ends = np.arange(tenor, discount.times[-1] + 1e-12, tenor)
    starts = ends - tenor
    forwards = _as_float_array(discount.forward_rate(starts, ends, "simple"))
    return ForwardCurve(starts, ends, forwards, tenor=name or f"{tenor:g}Y")


def bootstrap_projection_curve_from_swaps(
    discount: DiscountCurve,
    swaps: pd.DataFrame,
    *,
    tenor: float = 0.5,
    fixed_frequency: int = 2,
    name: str = "projection",
) -> ForwardCurve:
    """Sequentially bootstrap tenor forwards from par swaps under OIS discounting.

    The floating leg is represented by ``sum(alpha_i P_d(0,T_i) F_i)``.
    Quotes must cover consecutive maturities on the chosen tenor grid.
    """
    frame = _standardize_quotes(swaps, ["maturity", "rate"])
    if tenor <= 0:
        raise ValueError("tenor must be positive")
    known: dict[tuple[float, float], float] = {}
    for row in frame.itertuples(index=False):
        maturity, fixed_rate = float(row.maturity), float(row.rate)
        float_ends = np.arange(tenor, maturity + 1e-12, tenor)
        if len(float_ends) == 0 or not np.isclose(float_ends[-1], maturity):
            raise ValueError("swap maturities must lie on the floating tenor grid")
        starts = float_ends - tenor
        fixed_times = payment_schedule(0.0, maturity, fixed_frequency)
        fixed_alpha = 1.0 / fixed_frequency
        fixed_pv_per_notional = fixed_rate * fixed_alpha * np.sum(_as_float_array(discount.df(fixed_times)))
        known_pv = 0.0
        for s, e in zip(starts[:-1], float_ends[:-1]):
            key = (float(s), float(e))
            if key not in known:
                raise ValueError(f"missing earlier projection forward {key}")
            known_pv += tenor * float(discount.df(e)) * known[key]
        e = float(float_ends[-1]); s = float(starts[-1])
        denom = tenor * float(discount.df(e))
        known[(s, e)] = (fixed_pv_per_notional - known_pv) / denom
    keys = sorted(known)
    return ForwardCurve(
        np.array([k[0] for k in keys]),
        np.array([k[1] for k in keys]),
        np.array([known[k] for k in keys]),
        tenor=name,
    )


def bond_price_from_curve(
    curve: DiscountCurve,
    face: float,
    coupon_rate: float,
    maturity: float,
    frequency: int = 2,
) -> float:
    """Dirty price of a deterministic fixed-coupon bond from a discount curve."""
    if face <= 0 or maturity <= 0 or frequency <= 0:
        raise ValueError("face, maturity and frequency must be positive")
    times = payment_schedule(0.0, maturity, frequency)
    cash = np.full(len(times), face * coupon_rate / frequency)
    cash[-1] += face
    return float(np.dot(cash, _as_float_array(curve.df(times))))


def accrued_interest(face: float, coupon_rate: float, frequency: int, fraction_since_coupon: float) -> float:
    """Linear accrued interest inside a coupon period."""
    if face <= 0 or frequency <= 0 or not 0 <= fraction_since_coupon <= 1:
        raise ValueError("invalid accrued-interest inputs")
    return float(face * coupon_rate / frequency * fraction_since_coupon)


def clean_price(dirty_price: float, accrued: float) -> float:
    return float(dirty_price - accrued)


def dirty_price(clean: float, accrued: float) -> float:
    return float(clean + accrued)


def _central_sensitivity(pricer, curve: DiscountCurve, bump: float) -> tuple[float, float, float]:
    base = float(pricer(curve))
    up = float(pricer(curve.bump_parallel(bump)))
    down = float(pricer(curve.bump_parallel(-bump)))
    return base, up, down


def dv01(pricer, curve: DiscountCurve, bump: float = 1e-4) -> float:
    """Dollar value of a one-basis-point *decrease* in rates (central difference)."""
    _, up, down = _central_sensitivity(pricer, curve, bump)
    return float((down - up) / 2.0)


def dollar_convexity(pricer, curve: DiscountCurve, bump: float = 1e-4) -> float:
    """Second derivative of PV with respect to a parallel zero-rate shift."""
    base, up, down = _central_sensitivity(pricer, curve, bump)
    return float((up - 2.0 * base + down) / bump**2)


def key_rate_dv01(pricer, curve: DiscountCurve, key_maturities: Sequence[float], bump: float = 1e-4) -> pd.Series:
    """Bucketed key-rate DV01 using symmetric triangular node bumps."""
    result: dict[float, float] = {}
    for key in key_maturities:
        up = float(pricer(curve.bump_key_rate(float(key), bump)))
        down = float(pricer(curve.bump_key_rate(float(key), -bump)))
        result[float(key)] = (down - up) / 2.0
    return pd.Series(result, name="key_rate_dv01")

def compounded_overnight_rate(rates: ArrayLike, accruals: ArrayLike) -> float:
    """Geometrically compound realized overnight/RFR fixings over accrual periods.

    Market-specific lookback, observation shift, lockout and publication-lag
    conventions must be applied to the fixing schedule before this core identity.
    """
    r, a = _as_float_array(rates), _as_float_array(accruals)
    if r.ndim != 1 or a.shape != r.shape or len(r) == 0:
        raise ValueError("rates and accruals must be matching non-empty one-dimensional arrays")
    if np.any(a <= 0) or np.any(1.0 + r * a <= 0):
        raise ValueError("accruals must be positive and compounding factors must remain positive")
    total_accrual = float(np.sum(a))
    return float((np.prod(1.0 + r * a) - 1.0) / total_accrual)


def ois_par_rate(discount: DiscountCurve, start: float, end: float, *, fixed_frequency: int = 1) -> float:
    """Par fixed rate of a standard OIS under single-curve discounting."""
    return swap_par_rate(discount, start, end, fixed_frequency=fixed_frequency)


def ois_pv(
    discount: DiscountCurve,
    start: float,
    end: float,
    fixed_rate: float,
    *,
    notional: float = 1.0,
    fixed_frequency: int = 1,
    position: str = "payer",
) -> float:
    """PV of a standard fixed-versus-compounded-overnight OIS."""
    return swap_pv(
        discount, start, end, fixed_rate,
        notional=notional, fixed_frequency=fixed_frequency, position=position,
    )


def bond_forward_price(
    discount: DiscountCurve,
    spot_dirty_price: float,
    delivery: float,
    coupon_times: ArrayLike = (),
    coupon_cashflows: ArrayLike = (),
) -> float:
    """No-arbitrage dirty forward price of a coupon bond at delivery."""
    if spot_dirty_price < 0 or delivery <= 0:
        raise ValueError("spot_dirty_price must be non-negative and delivery positive")
    times = _as_float_array(coupon_times)
    cashflows = _as_float_array(coupon_cashflows)
    if times.size == 0 and cashflows.size == 0:
        pv_income = 0.0
    else:
        if times.ndim != 1 or cashflows.shape != times.shape:
            raise ValueError("coupon_times and coupon_cashflows must be matching one-dimensional arrays")
        mask = times <= delivery + 1e-12
        pv_income = float(np.sum(cashflows[mask] * _as_float_array(discount.df(times[mask]))))
    return float((spot_dirty_price - pv_income) / float(discount.df(delivery)))


def fx_forward_rate(
    spot_fx: float,
    domestic_discount: DiscountCurve,
    foreign_discount: DiscountCurve,
    maturity: float,
) -> float:
    """Covered-interest-parity FX forward, quoted domestic currency per foreign."""
    if spot_fx <= 0 or maturity <= 0:
        raise ValueError("spot_fx and maturity must be positive")
    return float(spot_fx * foreign_discount.df(maturity) / domestic_discount.df(maturity))


def cross_currency_zero_coupon_pv(
    spot_fx: float,
    domestic_discount: DiscountCurve,
    foreign_discount: DiscountCurve,
    maturity: float,
    *,
    domestic_notional: float,
    foreign_notional: float,
    receive_foreign: bool = True,
) -> float:
    """PV in domestic currency of exchanging two notionals at maturity."""
    if spot_fx <= 0 or maturity <= 0 or domestic_notional < 0 or foreign_notional < 0:
        raise ValueError("spot/maturity must be positive and notionals non-negative")
    foreign_pv_domestic = spot_fx * foreign_notional * float(foreign_discount.df(maturity))
    domestic_pv = domestic_notional * float(domestic_discount.df(maturity))
    value = foreign_pv_domestic - domestic_pv
    return float(value if receive_foreign else -value)


def zero_coupon_inflation_rate(index_start: float, index_end: float, maturity: float) -> float:
    """Annualized inflation rate implied by a terminal index ratio."""
    if index_start <= 0 or index_end <= 0 or maturity <= 0:
        raise ValueError("index levels and maturity must be positive")
    return float((index_end / index_start) ** (1.0 / maturity) - 1.0)


def zero_coupon_inflation_swap_pv(
    discount: DiscountCurve,
    maturity: float,
    fixed_rate: float,
    index_ratio: float,
    *,
    notional: float = 1.0,
    receive_inflation: bool = True,
) -> float:
    """PV of a zero-coupon inflation swap for a supplied terminal index ratio."""
    if maturity <= 0 or index_ratio <= 0 or notional <= 0 or fixed_rate <= -1:
        raise ValueError("invalid ZC inflation swap inputs")
    payoff = notional * (index_ratio - (1.0 + fixed_rate) ** maturity)
    pv = float(discount.df(maturity)) * payoff
    return float(pv if receive_inflation else -pv)


def curve_scenario(
    curve: DiscountCurve,
    *,
    parallel_bp: float = 0.0,
    slope_bp: float = 0.0,
    curvature_bp: float = 0.0,
) -> DiscountCurve:
    """Apply transparent parallel/slope/curvature shocks to node zero rates."""
    times = curve.times[curve.times > 0]
    if len(times) == 0:
        raise ValueError("curve has no positive-maturity nodes")
    rates = _as_float_array(curve.zero_rate(times))
    if len(times) == 1:
        x = np.zeros(1)
    else:
        center = 0.5 * (float(times[0]) + float(times[-1]))
        half_range = 0.5 * (float(times[-1]) - float(times[0]))
        x = (times - center) / half_range
    hump = 1.0 - 2.0 * x * x
    shock = 1e-4 * (parallel_bp + slope_bp * x + curvature_bp * hump)
    return DiscountCurve.from_zero_rates(
        times, rates + shock, interpolation=curve.interpolation,
        name=f"{curve.name}-scenario",
        metadata={**dict(curve.metadata), "parallel_bp": parallel_bp, "slope_bp": slope_bp, "curvature_bp": curvature_bp},
    )


@dataclass(frozen=True)
class HedgeSolution:
    """Least-squares key-rate hedge solution."""
    weights: np.ndarray
    residual_exposure: np.ndarray
    residual_norm: float


def key_rate_hedge(target_exposure: ArrayLike, hedge_exposures: ArrayLike, *, ridge: float = 0.0) -> HedgeSolution:
    """Solve hedge weights so hedge key-rate exposures offset a target vector."""
    target = _as_float_array(target_exposure)
    matrix = _as_float_array(hedge_exposures)
    if target.ndim != 1 or matrix.ndim != 2 or matrix.shape[0] != len(target):
        raise ValueError("hedge_exposures must have shape (len(target_exposure), n_hedges)")
    if ridge < 0:
        raise ValueError("ridge must be non-negative")
    if ridge > 0:
        lhs = matrix.T @ matrix + ridge * np.eye(matrix.shape[1])
        rhs = -matrix.T @ target
        weights = np.linalg.solve(lhs, rhs)
    else:
        weights, *_ = np.linalg.lstsq(matrix, -target, rcond=None)
    residual = target + matrix @ weights
    return HedgeSolution(np.asarray(weights), np.asarray(residual), float(np.linalg.norm(residual)))


@dataclass(frozen=True)
class BermudanLSMResult:
    """Generic least-squares Monte Carlo early-exercise result."""
    price: float
    exercise_probability: np.ndarray
    exercise_time_index: np.ndarray
    path_values: np.ndarray


def bermudan_lsm(
    immediate_values: np.ndarray,
    state_paths: np.ndarray,
    interval_discounts: ArrayLike,
    *,
    polynomial_degree: int = 2,
    valuation_discount: float = 1.0,
) -> BermudanLSMResult:
    """Generic Longstaff-Schwartz engine for Bermudan-style exercise."""
    exercise = np.asarray(immediate_values, dtype=float)
    state = np.asarray(state_paths, dtype=float)
    if exercise.ndim != 2 or state.shape != exercise.shape or exercise.shape[0] < 2:
        raise ValueError("immediate_values/state_paths must be matching 2D arrays with at least two exercise dates")
    if polynomial_degree < 1 or valuation_discount <= 0:
        raise ValueError("polynomial_degree must be positive and valuation_discount > 0")
    n_times, n_paths = exercise.shape
    d = np.asarray(interval_discounts, dtype=float)
    if d.ndim == 1:
        if len(d) != n_times - 1:
            raise ValueError("interval_discounts must contain one factor per interval")
        d = np.repeat(d[:, None], n_paths, axis=1)
    elif d.shape != (n_times - 1, n_paths):
        raise ValueError("interval_discounts matrix has invalid shape")
    if np.any(d <= 0):
        raise ValueError("discount factors must be positive")

    values = np.maximum(exercise[-1], 0.0)
    exercise_index = np.where(values > 0, n_times - 1, -1).astype(int)
    for i in range(n_times - 2, -1, -1):
        continuation_realized = values * d[i]
        itm = exercise[i] > 0
        estimated = np.full(n_paths, np.inf)
        if np.count_nonzero(itm) >= polynomial_degree + 1:
            x = state[i, itm]
            design = np.column_stack([x ** power for power in range(polynomial_degree + 1)])
            coef, *_ = np.linalg.lstsq(design, continuation_realized[itm], rcond=None)
            full_design = np.column_stack([state[i] ** power for power in range(polynomial_degree + 1)])
            estimated = full_design @ coef
        choose = itm & (exercise[i] >= estimated)
        values = np.where(choose, exercise[i], continuation_realized)
        exercise_index = np.where(choose, i, exercise_index)
    probabilities = np.array([np.mean(exercise_index == i) for i in range(n_times)], dtype=float)
    return BermudanLSMResult(
        price=float(valuation_discount * np.mean(values)),
        exercise_probability=probabilities,
        exercise_time_index=exercise_index,
        path_values=valuation_discount * values,
    )



def fra_forward_rate(curve: DiscountCurve, start: float, end: float) -> float:
    return float(curve.forward_rate(start, end, "simple"))


def fra_pv(
    curve: DiscountCurve,
    start: float,
    end: float,
    strike: float,
    *,
    notional: float = 1.0,
    position: str = "receive_float",
    settlement: str = "end",
    projection: ForwardCurve | None = None,
) -> float:
    """Present value of a FRA.

    ``settlement='end'`` uses the standard end-payment representation
    ``N*tau*(F-K) P(0,T2)``.  ``settlement='start'`` uses the FRA cash
    settlement denominator ``1 + tau F`` and discounts to ``T1``.
    """
    tau = end - start
    if tau <= 0 or notional <= 0:
        raise ValueError("end must exceed start and notional must be positive")
    fwd = projection.rate(start, end) if projection is not None else fra_forward_rate(curve, start, end)
    sign = 1.0 if position.lower() in {"receive_float", "long", "payer_rate"} else -1.0
    if settlement.lower() == "end":
        pv = notional * tau * (fwd - strike) * float(curve.df(end))
    elif settlement.lower() == "start":
        pv = notional * tau * (fwd - strike) / (1.0 + tau * fwd) * float(curve.df(start))
    else:
        raise ValueError("settlement must be 'start' or 'end'")
    return float(sign * pv)


def swap_annuity(curve: DiscountCurve, start: float, end: float, frequency: int = 2) -> float:
    times = payment_schedule(start, end, frequency)
    return float(np.sum((1.0 / frequency) * _as_float_array(curve.df(times))))


def swap_par_rate(
    discount: DiscountCurve,
    start: float,
    end: float,
    *,
    fixed_frequency: int = 2,
    projection: ForwardCurve | None = None,
) -> float:
    """Par IRS rate under single- or multi-curve valuation."""
    fixed_times = payment_schedule(start, end, fixed_frequency)
    ann = float(np.sum((1.0 / fixed_frequency) * _as_float_array(discount.df(fixed_times))))
    if projection is None:
        float_pv = float(discount.df(start) - discount.df(end))
    else:
        float_pv = 0.0
        for s, e, f in zip(projection.starts, projection.ends, projection.forwards):
            if s + 1e-12 >= start and e <= end + 1e-12:
                float_pv += (e - s) * float(discount.df(e)) * f
    return float(float_pv / ann)


def swap_pv(
    discount: DiscountCurve,
    start: float,
    end: float,
    fixed_rate: float,
    *,
    notional: float = 1.0,
    fixed_frequency: int = 2,
    position: str = "payer",
    projection: ForwardCurve | None = None,
) -> float:
    """PV of a vanilla fixed-for-floating interest-rate swap."""
    if notional <= 0:
        raise ValueError("notional must be positive")
    ann = swap_annuity(discount, start, end, fixed_frequency)
    par = swap_par_rate(discount, start, end, fixed_frequency=fixed_frequency, projection=projection)
    receive_float = notional * ann * (par - fixed_rate)
    if position.lower() in {"payer", "pay_fixed", "receive_float"}:
        return float(receive_float)
    if position.lower() in {"receiver", "receive_fixed", "pay_float"}:
        return float(-receive_float)
    raise ValueError("position must be payer or receiver")


def swap_dv01(
    discount: DiscountCurve,
    start: float,
    end: float,
    fixed_rate: float,
    *,
    notional: float = 1.0,
    fixed_frequency: int = 2,
    position: str = "payer",
    bump: float = 1e-4,
) -> float:
    pricer = lambda c: swap_pv(c, start, end, fixed_rate, notional=notional, fixed_frequency=fixed_frequency, position=position)
    return dv01(pricer, discount, bump=bump)


def basis_swap_pv(
    discount: DiscountCurve,
    leg_a: ForwardCurve,
    leg_b: ForwardCurve,
    start: float,
    end: float,
    *,
    spread_a: float = 0.0,
    notional: float = 1.0,
) -> float:
    """PV of receiving projection leg A plus spread and paying leg B."""
    pv = 0.0
    for s, e, f in zip(leg_a.starts, leg_a.ends, leg_a.forwards):
        if s + 1e-12 >= start and e <= end + 1e-12:
            pv += notional * (e - s) * float(discount.df(e)) * (f + spread_a)
    for s, e, f in zip(leg_b.starts, leg_b.ends, leg_b.forwards):
        if s + 1e-12 >= start and e <= end + 1e-12:
            pv -= notional * (e - s) * float(discount.df(e)) * f
    return float(pv)


def rate_future_price(rate: float) -> float:
    """IMM-style quoted rate future price ``100 - 100*rate``."""
    return float(100.0 * (1.0 - rate))


def rate_from_future_price(price: float) -> float:
    return float(1.0 - price / 100.0)


def _black_forward_value(forward: float, strike: float, vol: float, expiry: float, option: str) -> float:
    if forward <= 0 or strike <= 0 or vol <= 0 or expiry <= 0:
        raise ValueError("Black inputs must be positive")
    srt = vol * np.sqrt(expiry)
    d1 = (np.log(forward / strike) + 0.5 * vol * vol * expiry) / srt
    d2 = d1 - srt
    call = forward * norm.cdf(d1) - strike * norm.cdf(d2)
    if option.lower() in {"call", "caplet", "payer"}:
        return float(call)
    if option.lower() in {"put", "floorlet", "receiver"}:
        return float(call - forward + strike)
    raise ValueError("invalid option type")


def _bachelier_forward_value(forward: float, strike: float, vol: float, expiry: float, option: str) -> float:
    if vol <= 0 or expiry <= 0:
        raise ValueError("normal volatility and expiry must be positive")
    std = vol * np.sqrt(expiry)
    d = (forward - strike) / std
    call = (forward - strike) * norm.cdf(d) + std * norm.pdf(d)
    if option.lower() in {"call", "caplet", "payer"}:
        return float(call)
    if option.lower() in {"put", "floorlet", "receiver"}:
        return float(call - forward + strike)
    raise ValueError("invalid option type")


def caplet_price(
    discount: DiscountCurve,
    start: float,
    end: float,
    strike: float,
    volatility: float,
    *,
    notional: float = 1.0,
    option: str = "caplet",
    model: str = "black76",
    projection: ForwardCurve | None = None,
    shift: float = 0.0,
) -> float:
    """Price one caplet/floorlet under Black-76, shifted Black or Bachelier."""
    tau = end - start
    if tau <= 0 or notional <= 0:
        raise ValueError("invalid caplet period/notional")
    fwd = projection.rate(start, end) if projection is not None else fra_forward_rate(discount, start, end)
    factor = notional * tau * float(discount.df(end))
    m = model.lower()
    if m in {"black", "black76", "shifted_black"}:
        return factor * _black_forward_value(fwd + shift, strike + shift, volatility, start, option)
    if m in {"bachelier", "normal"}:
        return factor * _bachelier_forward_value(fwd, strike, volatility, start, option)
    raise ValueError("model must be black76/shifted_black or bachelier")


def cap_floor_price(
    discount: DiscountCurve,
    periods: Sequence[tuple[float, float]],
    strike: float,
    volatilities: float | Sequence[float],
    *,
    notional: float = 1.0,
    option: str = "cap",
    model: str = "black76",
    projection: ForwardCurve | None = None,
    shift: float = 0.0,
) -> float:
    """Price a cap/floor as a portfolio of caplets/floorlets."""
    vols = np.full(len(periods), float(volatilities)) if np.isscalar(volatilities) else _as_float_array(volatilities)
    if len(vols) != len(periods):
        raise ValueError("volatilities must be scalar or one per period")
    unit = "caplet" if option.lower() == "cap" else "floorlet" if option.lower() == "floor" else option
    return float(sum(caplet_price(discount, s, e, strike, float(v), notional=notional, option=unit, model=model, projection=projection, shift=shift) for (s, e), v in zip(periods, vols)))


def swaption_price(
    discount: DiscountCurve,
    expiry: float,
    swap_end: float,
    strike: float,
    volatility: float,
    *,
    notional: float = 1.0,
    fixed_frequency: int = 2,
    option: str = "payer",
    model: str = "black76",
    projection: ForwardCurve | None = None,
    shift: float = 0.0,
) -> float:
    """European physical/cash-annuity-equivalent swaption price."""
    if swap_end <= expiry:
        raise ValueError("swap_end must exceed expiry")
    ann = swap_annuity(discount, expiry, swap_end, fixed_frequency)
    fwd = swap_par_rate(discount, expiry, swap_end, fixed_frequency=fixed_frequency, projection=projection)
    if model.lower() in {"black", "black76", "shifted_black"}:
        unit = _black_forward_value(fwd + shift, strike + shift, volatility, expiry, option)
    elif model.lower() in {"bachelier", "normal"}:
        unit = _bachelier_forward_value(fwd, strike, volatility, expiry, option)
    else:
        raise ValueError("model must be black76/shifted_black or bachelier")
    return float(notional * ann * unit)


def implied_rate_volatility(
    price: float,
    pricer,
    *,
    lower: float = 1e-8,
    upper: float = 5.0,
) -> float:
    """Generic scalar implied-volatility inversion for a rate-option pricer."""
    if price < 0:
        raise ValueError("price must be non-negative")
    objective = lambda sigma: float(pricer(sigma)) - price
    if objective(lower) * objective(upper) > 0:
        raise ValueError("price is outside the implied-volatility bracket")
    return float(brentq(objective, lower, upper))


def strip_caplet_volatilities(
    discount: DiscountCurve,
    periods: Sequence[tuple[float, float]],
    strike: float,
    cap_prices: Sequence[float],
    *,
    notional: float = 1.0,
    model: str = "black76",
    projection: ForwardCurve | None = None,
    shift: float = 0.0,
) -> pd.Series:
    """Bootstrap caplet vols from a sequence of cumulative cap prices."""
    prices = _as_float_array(cap_prices)
    if len(prices) != len(periods):
        raise ValueError("cap_prices must contain one cumulative price per cap maturity")
    vols: list[float] = []
    previous_value = 0.0
    for idx, ((s, e), cumulative) in enumerate(zip(periods, prices)):
        incremental = float(cumulative - previous_value)
        if incremental < -1e-12:
            raise ValueError("cumulative cap prices must be non-decreasing")
        pricer = lambda sigma: caplet_price(discount, s, e, strike, sigma, notional=notional, option="caplet", model=model, projection=projection, shift=shift)
        vols.append(implied_rate_volatility(max(incremental, 0.0), pricer))
        previous_value = float(cumulative)
    return pd.Series(vols, index=[e for _, e in periods], name="caplet_volatility")


def hagan_sabr_volatility(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
    *,
    shift: float = 0.0,
) -> float:
    """Hagan et al. lognormal SABR implied-volatility approximation."""
    f, k = forward + shift, strike + shift
    if f <= 0 or k <= 0 or expiry <= 0 or alpha <= 0 or nu < 0 or not 0 <= beta <= 1 or not -0.999 < rho < 0.999:
        raise ValueError("invalid SABR inputs")
    one_minus_beta = 1.0 - beta
    if np.isclose(f, k, rtol=1e-10, atol=1e-12):
        fk = f ** one_minus_beta
        correction = (
            (one_minus_beta**2 / 24.0) * alpha**2 / fk**2
            + 0.25 * rho * beta * nu * alpha / fk
            + (2.0 - 3.0 * rho**2) * nu**2 / 24.0
        ) * expiry
        return float(alpha / fk * (1.0 + correction))
    log_fk = np.log(f / k)
    fk_beta = (f * k) ** (0.5 * one_minus_beta)
    z = (nu / alpha) * fk_beta * log_fk
    sqrt_term = np.sqrt(1.0 - 2.0 * rho * z + z * z)
    xz = np.log((sqrt_term + z - rho) / (1.0 - rho))
    z_over_x = 1.0 if abs(z) < 1e-12 else z / xz
    denom = fk_beta * (1.0 + one_minus_beta**2 * log_fk**2 / 24.0 + one_minus_beta**4 * log_fk**4 / 1920.0)
    correction = (
        one_minus_beta**2 * alpha**2 / (24.0 * fk_beta**2)
        + rho * beta * nu * alpha / (4.0 * fk_beta)
        + (2.0 - 3.0 * rho**2) * nu**2 / 24.0
    ) * expiry
    return float((alpha / denom) * z_over_x * (1.0 + correction))


@dataclass(frozen=True)
class SABRCalibration:
    alpha: float
    beta: float
    rho: float
    nu: float
    rmse: float
    fitted_vols: np.ndarray
    success: bool


def calibrate_sabr(
    strikes: ArrayLike,
    market_vols: ArrayLike,
    forward: float,
    expiry: float,
    *,
    beta: float = 0.5,
    shift: float = 0.0,
    initial: tuple[float, float, float] = (0.02, 0.0, 0.5),
) -> SABRCalibration:
    """Least-squares SABR calibration with fixed beta."""
    k, v = _as_float_array(strikes), _as_float_array(market_vols)
    if k.ndim != 1 or v.ndim != 1 or len(k) != len(v) or len(k) < 3:
        raise ValueError("need at least three strike/volatility points")

    def residual(params: np.ndarray) -> np.ndarray:
        a, r, n = params
        fitted = np.array([hagan_sabr_volatility(forward, float(kk), expiry, a, beta, r, n, shift=shift) for kk in k])
        return fitted - v

    result = least_squares(residual, np.asarray(initial, dtype=float), bounds=([1e-8, -0.999, 1e-8], [5.0, 0.999, 5.0]))
    a, r, n = map(float, result.x)
    fitted = np.array([hagan_sabr_volatility(forward, float(kk), expiry, a, beta, r, n, shift=shift) for kk in k])
    rmse = float(np.sqrt(np.mean((fitted - v) ** 2)))
    return SABRCalibration(a, float(beta), r, n, rmse, fitted, bool(result.success))


def vasicek_zero_coupon_bond(r_t: float, t: float, maturity: float, kappa: float, theta: float, sigma: float) -> float:
    """Vasicek zero-coupon bond price ``A(t,T) exp(-B(t,T) r_t)``."""
    tau = maturity - t
    if tau < 0 or kappa <= 0 or sigma < 0:
        raise ValueError("require maturity >= t, kappa > 0, sigma >= 0")
    if tau == 0:
        return 1.0
    b = (1.0 - np.exp(-kappa * tau)) / kappa
    a = np.exp((theta - sigma**2 / (2.0 * kappa**2)) * (b - tau) - sigma**2 * b**2 / (4.0 * kappa))
    return float(a * np.exp(-b * r_t))


def cir_zero_coupon_bond(r_t: float, t: float, maturity: float, kappa: float, theta: float, sigma: float) -> float:
    """CIR zero-coupon bond price in affine closed form."""
    tau = maturity - t
    if tau < 0 or kappa <= 0 or theta < 0 or sigma <= 0 or r_t < 0:
        raise ValueError("invalid CIR inputs")
    if tau == 0:
        return 1.0
    gamma = np.sqrt(kappa**2 + 2.0 * sigma**2)
    expg = np.exp(gamma * tau)
    b = 2.0 * (expg - 1.0) / ((gamma + kappa) * (expg - 1.0) + 2.0 * gamma)
    a = (2.0 * gamma * np.exp((kappa + gamma) * tau / 2.0) / ((gamma + kappa) * (expg - 1.0) + 2.0 * gamma)) ** (2.0 * kappa * theta / sigma**2)
    return float(a * np.exp(-b * r_t))


def hull_white_paths(
    r0: float,
    mean_reversion: float,
    theta: float,
    sigma: float,
    maturity: float,
    *,
    steps: int = 252,
    paths: int = 10_000,
    random_state: int | None = 0,
) -> pd.DataFrame:
    """Simulate the one-factor Hull-White/Vasicek SDE with constant theta.

    ``dr = a(theta-r)dt + sigma dW``.  A time-dependent theta can be supplied by
    users through the generic Monte-Carlo/SDE engine; this helper is the compact
    constant-theta laboratory version.
    """
    if mean_reversion <= 0 or sigma < 0 or maturity <= 0 or steps <= 0 or paths <= 0:
        raise ValueError("invalid Hull-White simulation inputs")
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    expa = np.exp(-mean_reversion * dt)
    mean_weight = theta * (1.0 - expa)
    sd = sigma * np.sqrt((1.0 - np.exp(-2.0 * mean_reversion * dt)) / (2.0 * mean_reversion))
    out = np.empty((steps + 1, paths), dtype=float)
    out[0] = r0
    for i in range(steps):
        out[i + 1] = out[i] * expa + mean_weight + sd * rng.standard_normal(paths)
    index = np.linspace(0.0, maturity, steps + 1)
    return pd.DataFrame(out, index=index)


def ho_lee_paths(
    r0: float,
    theta: float,
    sigma: float,
    maturity: float,
    *,
    steps: int = 252,
    paths: int = 10_000,
    random_state: int | None = 0,
) -> pd.DataFrame:
    """Euler simulation of ``dr = theta dt + sigma dW``."""
    if sigma < 0 or maturity <= 0 or steps <= 0 or paths <= 0:
        raise ValueError("invalid Ho-Lee inputs")
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    shocks = theta * dt + sigma * np.sqrt(dt) * rng.standard_normal((steps, paths))
    out = np.vstack([np.full(paths, r0), r0 + np.cumsum(shocks, axis=0)])
    return pd.DataFrame(out, index=np.linspace(0.0, maturity, steps + 1))


def black_karasinski_paths(
    r0: float,
    mean_reversion: float,
    theta_log: float,
    sigma: float,
    maturity: float,
    *,
    steps: int = 252,
    paths: int = 10_000,
    random_state: int | None = 0,
) -> pd.DataFrame:
    """Simulate Black-Karasinski through an OU process for ``log r``."""
    if r0 <= 0:
        raise ValueError("Black-Karasinski requires positive r0")
    log_paths = hull_white_paths(np.log(r0), mean_reversion, theta_log, sigma, maturity, steps=steps, paths=paths, random_state=random_state)
    return np.exp(log_paths)


def hjm_one_factor_paths(
    maturities: ArrayLike,
    initial_forwards: ArrayLike,
    volatilities: ArrayLike,
    horizon: float,
    *,
    steps: int = 100,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> np.ndarray:
    """Discrete one-factor HJM forward-curve simulation under the risk-neutral measure.

    For deterministic maturity-dependent volatility ``sigma(T)``, the drift at
    time ``t`` is approximated as ``sigma(T) * integral_t^T sigma(u) du`` over the
    supplied maturity grid.  Output shape is ``(steps+1, paths, n_maturities)``.
    """
    mats = _as_float_array(maturities)
    f0 = _as_float_array(initial_forwards)
    sig = _as_float_array(volatilities)
    if not (len(mats) == len(f0) == len(sig)) or np.any(np.diff(mats) <= 0) or horizon <= 0:
        raise ValueError("invalid HJM grid")
    rng = np.random.default_rng(random_state)
    dt = horizon / steps
    out = np.empty((steps + 1, paths, len(mats)), dtype=float)
    out[0] = f0
    dT = np.diff(np.r_[0.0, mats])
    for n in range(steps):
        t = n * dt
        active = mats > t
        integral = np.zeros(len(mats))
        for j in range(len(mats)):
            if active[j]:
                mask = (mats <= mats[j]) & active
                integral[j] = np.sum(sig[mask] * dT[mask])
        drift = sig * integral
        z = rng.standard_normal(paths)[:, None]
        out[n + 1] = out[n] + drift[None, :] * dt + sig[None, :] * np.sqrt(dt) * z
    return out


def lmm_terminal_measure_paths(
    initial_forwards: ArrayLike,
    accruals: ArrayLike,
    volatilities: ArrayLike,
    correlation: np.ndarray,
    horizon: float,
    *,
    steps: int = 100,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> np.ndarray:
    """Euler-log simulation of a lognormal LIBOR Market Model under terminal measure.

    Output shape is ``(steps+1, paths, n_forwards)``.  The terminal-measure drift
    uses the standard negative sum over later forwards.  This function is for
    research/education; production calibration should use a dedicated numerical
    implementation with tenor-date fixing and measure bookkeeping.
    """
    f0, delta, sigma = map(_as_float_array, (initial_forwards, accruals, volatilities))
    n = len(f0)
    corr = np.asarray(correlation, dtype=float)
    if not (len(delta) == len(sigma) == n) or corr.shape != (n, n) or np.any(f0 <= 0) or np.any(delta <= 0) or np.any(sigma < 0):
        raise ValueError("invalid LMM inputs")
    if not np.allclose(corr, corr.T, atol=1e-10):
        raise ValueError("correlation matrix must be symmetric")
    eig = np.linalg.eigvalsh(corr)
    if np.min(eig) < -1e-10:
        raise ValueError("correlation matrix must be positive semidefinite")
    chol = np.linalg.cholesky(corr + np.eye(n) * 1e-14)
    rng = np.random.default_rng(random_state)
    dt = horizon / steps
    out = np.empty((steps + 1, paths, n), dtype=float)
    out[0] = f0
    covariance = np.outer(sigma, sigma) * corr
    for step in range(steps):
        current = out[step]
        drift = np.zeros_like(current)
        for i in range(n):
            if i + 1 < n:
                later = np.arange(i + 1, n)
                weights = delta[later] * current[:, later] / (1.0 + delta[later] * current[:, later])
                drift[:, i] = -np.sum(weights * covariance[i, later], axis=1)
        z = rng.standard_normal((paths, n)) @ chol.T
        log_increment = (drift - 0.5 * sigma[None, :] ** 2) * dt + sigma[None, :] * np.sqrt(dt) * z
        out[step + 1] = current * np.exp(log_increment)
    return out


@dataclass(frozen=True)
class VasicekCalibration:
    kappa: float
    theta: float
    sigma: float
    intercept: float
    phi: float
    residual_std: float


def calibrate_vasicek(rates: ArrayLike, dt: float = 1.0 / 252.0) -> VasicekCalibration:
    """Estimate Vasicek parameters from an equally spaced short-rate series via AR(1)."""
    r = _as_float_array(rates)
    if r.ndim != 1 or len(r) < 10 or dt <= 0:
        raise ValueError("need at least 10 observations and positive dt")
    x, y = r[:-1], r[1:]
    design = np.c_[np.ones(len(x)), x]
    intercept, phi = np.linalg.lstsq(design, y, rcond=None)[0]
    phi = float(phi)
    if not 0 < phi < 1:
        raise ValueError("estimated AR(1) coefficient must lie in (0,1) for mean reversion")
    kappa = -np.log(phi) / dt
    theta = float(intercept / (1.0 - phi))
    resid = y - (intercept + phi * x)
    residual_std = float(np.std(resid, ddof=2))
    sigma = residual_std * np.sqrt(2.0 * kappa / (1.0 - phi**2))
    return VasicekCalibration(float(kappa), theta, float(sigma), float(intercept), phi, residual_std)


def yield_curve_pca(yields: pd.DataFrame, n_components: int = 3, *, differences: bool = True) -> dict[str, Any]:
    """PCA of yield-curve changes returning level/slope/curvature-style loadings."""
    frame = pd.DataFrame(yields).apply(pd.to_numeric, errors="coerce").dropna()
    x = frame.diff().dropna() if differences else frame.copy()
    if len(x) < 3 or x.shape[1] < 2:
        raise ValueError("yield_curve_pca needs at least 3 rows and 2 maturities")
    centered = x.to_numpy() - x.to_numpy().mean(axis=0)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    k = min(n_components, len(s), x.shape[1])
    explained = s**2 / np.sum(s**2)
    scores = centered @ vt[:k].T
    loadings = pd.DataFrame(vt[:k].T, index=frame.columns, columns=[f"PC{i+1}" for i in range(k)])
    score_frame = pd.DataFrame(scores, index=x.index, columns=loadings.columns)
    return {
        "loadings": loadings,
        "scores": score_frame,
        "explained_variance_ratio": pd.Series(explained[:k], index=loadings.columns),
    }


def level_slope_curvature(yields: pd.DataFrame) -> pd.DataFrame:
    """Simple interpretable level/slope/curvature factors from ordered maturities."""
    frame = pd.DataFrame(yields).apply(pd.to_numeric, errors="coerce")
    if frame.shape[1] < 3:
        raise ValueError("need at least three maturities")
    short, middle, long = frame.iloc[:, 0], frame.iloc[:, frame.shape[1] // 2], frame.iloc[:, -1]
    return pd.DataFrame({
        "level": frame.mean(axis=1),
        "slope": long - short,
        "curvature": 2.0 * middle - short - long,
    }, index=frame.index)


def no_arbitrage_curve_diagnostics(curve: DiscountCurve, *, tolerance: float = 1e-10) -> pd.Series:
    """Basic curve sanity checks useful before pricing or research."""
    discounts = curve.discounts
    forwards = []
    for s, e in zip(curve.times[:-1], curve.times[1:]):
        if e > s:
            forwards.append(float(curve.forward_rate(s, e, "simple")))
    return pd.Series({
        "positive_discounts": bool(np.all(discounts > 0)),
        "time_zero_is_one": bool(np.isclose(discounts[0], 1.0, atol=tolerance)),
        "discounts_nonincreasing": bool(np.all(np.diff(discounts) <= tolerance)),
        "minimum_discount": float(np.min(discounts)),
        "minimum_simple_forward": float(np.min(forwards)) if forwards else np.nan,
        "maximum_simple_forward": float(np.max(forwards)) if forwards else np.nan,
    })


def curve_interpolation_risk(
    times: ArrayLike,
    zero_rates: ArrayLike,
    evaluation_grid: ArrayLike | None = None,
) -> pd.DataFrame:
    """Compare forward rates induced by three transparent interpolation choices."""
    t, r = _as_float_array(times), _as_float_array(zero_rates)
    if evaluation_grid is None:
        grid = np.linspace(max(float(t[0]), 1e-4), float(t[-1]), max(100, len(t) * 20))
    else:
        grid = _as_float_array(evaluation_grid)
    rows = {"maturity": grid}
    for method in ("log_linear", "linear_zero", "linear_discount"):
        curve = DiscountCurve.from_zero_rates(t, r, interpolation=method)
        eps = np.minimum(1e-4, np.maximum(grid * 1e-4, 1e-7))
        valid = (grid > eps) & (grid < t[-1] - eps)
        fwd = np.full(len(grid), np.nan)
        if valid.any():
            fwd[valid] = _as_float_array(curve.instantaneous_forward(grid[valid], bump=1e-5))
        rows[f"forward_{method}"] = fwd
    frame = pd.DataFrame(rows)
    forward_cols = [c for c in frame if c.startswith("forward_")]
    frame["forward_dispersion"] = frame[forward_cols].std(axis=1, ddof=0)
    return frame


def carry_roll_down(
    curve_today: DiscountCurve,
    maturity: float,
    horizon: float,
    *,
    face: float = 1.0,
) -> pd.Series:
    """Static-curve carry/roll decomposition for a zero-coupon bond."""
    if not 0 < horizon < maturity:
        raise ValueError("require 0 < horizon < maturity")
    p0 = face * float(curve_today.df(maturity))
    p_h_static = face * float(curve_today.df(maturity - horizon))
    financing = p0 / float(curve_today.df(horizon))
    pnl = p_h_static - financing
    return pd.Series({
        "price_today": p0,
        "static_horizon_price": p_h_static,
        "financed_cost": financing,
        "carry_roll_pnl": pnl,
        "carry_roll_return": pnl / p0,
    })



def _ns_loading(maturity: np.ndarray, tau: float) -> tuple[np.ndarray, np.ndarray]:
    """Nelson-Siegel level/slope/curvature factor loadings."""
    if tau <= 0:
        raise ValueError("tau must be positive")
    x = np.asarray(maturity, dtype=float) / tau
    if np.any(maturity < 0):
        raise ValueError("maturities must be non-negative")
    with np.errstate(divide="ignore", invalid="ignore"):
        l1 = np.where(np.abs(x) < 1e-10, 1.0, -np.expm1(-x) / x)
    l2 = l1 - np.exp(-x)
    return l1, l2


def nelson_siegel_yield(
    maturity: ArrayLike,
    beta0: float,
    beta1: float,
    beta2: float,
    tau: float,
):
    """Evaluate a Nelson-Siegel continuously-compounded zero-yield curve."""
    t = _as_float_array(maturity)
    l1, l2 = _ns_loading(t, tau)
    out = beta0 + beta1 * l1 + beta2 * l2
    return _scalar_or_array(np.asarray(out))


def svensson_yield(
    maturity: ArrayLike,
    beta0: float,
    beta1: float,
    beta2: float,
    beta3: float,
    tau1: float,
    tau2: float,
):
    """Evaluate the Nelson-Siegel-Svensson zero-yield curve."""
    t = _as_float_array(maturity)
    l1, l2 = _ns_loading(t, tau1)
    _, l3 = _ns_loading(t, tau2)
    out = beta0 + beta1 * l1 + beta2 * l2 + beta3 * l3
    return _scalar_or_array(np.asarray(out))


@dataclass(frozen=True)
class YieldCurveCalibration:
    """Result of a parametric yield-curve fit."""

    model: str
    parameters: Mapping[str, float]
    rmse: float
    fitted_rates: np.ndarray
    success: bool

    def curve(self, maturities: ArrayLike) -> np.ndarray:
        p = self.parameters
        if self.model == "nelson_siegel":
            return np.asarray(nelson_siegel_yield(maturities, p["beta0"], p["beta1"], p["beta2"], p["tau"]), dtype=float)
        if self.model == "svensson":
            return np.asarray(svensson_yield(maturities, p["beta0"], p["beta1"], p["beta2"], p["beta3"], p["tau1"], p["tau2"]), dtype=float)
        raise ValueError(f"unsupported model {self.model!r}")

    def discount_curve(self, maturities: ArrayLike, *, interpolation: str = "log_linear") -> DiscountCurve:
        t = _as_float_array(maturities)
        return DiscountCurve.from_zero_rates(t, self.curve(t), interpolation=interpolation)


def calibrate_nelson_siegel(
    maturities: ArrayLike,
    zero_rates: ArrayLike,
    *,
    initial: Sequence[float] | None = None,
) -> YieldCurveCalibration:
    """Least-squares Nelson-Siegel calibration with positive decay parameter."""
    t, y = _as_float_array(maturities), _as_float_array(zero_rates)
    if t.ndim != 1 or y.shape != t.shape or len(t) < 4 or np.any(t <= 0):
        raise ValueError("need at least four positive maturities and matching zero rates")
    x0 = np.asarray(initial if initial is not None else [float(y[-1]), float(y[0] - y[-1]), 0.0, 2.0], dtype=float)
    fit = least_squares(
        lambda x: np.asarray(nelson_siegel_yield(t, x[0], x[1], x[2], x[3])) - y,
        x0=x0,
        bounds=([-1.0, -2.0, -2.0, 1e-4], [1.0, 2.0, 2.0, 100.0]),
        max_nfev=20000,
    )
    fitted = np.asarray(nelson_siegel_yield(t, *fit.x), dtype=float)
    return YieldCurveCalibration(
        model="nelson_siegel",
        parameters={"beta0": float(fit.x[0]), "beta1": float(fit.x[1]), "beta2": float(fit.x[2]), "tau": float(fit.x[3])},
        rmse=float(np.sqrt(np.mean((fitted - y) ** 2))),
        fitted_rates=fitted,
        success=bool(fit.success),
    )


def calibrate_svensson(
    maturities: ArrayLike,
    zero_rates: ArrayLike,
    *,
    initial: Sequence[float] | None = None,
) -> YieldCurveCalibration:
    """Least-squares Nelson-Siegel-Svensson calibration."""
    t, y = _as_float_array(maturities), _as_float_array(zero_rates)
    if t.ndim != 1 or y.shape != t.shape or len(t) < 6 or np.any(t <= 0):
        raise ValueError("need at least six positive maturities and matching zero rates")
    x0 = np.asarray(initial if initial is not None else [float(y[-1]), float(y[0] - y[-1]), 0.0, 0.0, 1.5, 5.0], dtype=float)
    fit = least_squares(
        lambda x: np.asarray(svensson_yield(t, x[0], x[1], x[2], x[3], x[4], x[5])) - y,
        x0=x0,
        bounds=([-1.0, -2.0, -2.0, -2.0, 1e-4, 1e-4], [1.0, 2.0, 2.0, 2.0, 100.0, 100.0]),
        max_nfev=30000,
    )
    fitted = np.asarray(svensson_yield(t, *fit.x), dtype=float)
    return YieldCurveCalibration(
        model="svensson",
        parameters={
            "beta0": float(fit.x[0]), "beta1": float(fit.x[1]), "beta2": float(fit.x[2]), "beta3": float(fit.x[3]),
            "tau1": float(fit.x[4]), "tau2": float(fit.x[5]),
        },
        rmse=float(np.sqrt(np.mean((fitted - y) ** 2))),
        fitted_rates=fitted,
        success=bool(fit.success),
    )


RATE_QUANT_CURRICULUM: tuple[dict[str, str], ...] = (
    {"stage": "01 Foundations", "topic": "Compounding & day count", "functions": "year_fraction, discount_factor, zero_rate_from_discount"},
    {"stage": "02 Curves", "topic": "Discount, zero, forward & par curves; Nelson-Siegel/Svensson", "functions": "DiscountCurve, ForwardCurve, bootstrap_discount_curve, calibrate_nelson_siegel, calibrate_svensson"},
    {"stage": "03 Multi-curve", "topic": "OIS discounting & tenor projection", "functions": "MultiCurve, bootstrap_projection_curve_from_swaps"},
    {"stage": "04 Bonds", "topic": "Bond PV, clean/dirty, accrued, duration-style risk", "functions": "bond_price_from_curve, accrued_interest, dv01, key_rate_dv01"},
    {"stage": "05 Linear rates", "topic": "Deposits, FRAs, futures, swaps, basis swaps", "functions": "fra_pv, rate_future_price, swap_pv, basis_swap_pv"},
    {"stage": "05B RFR/OIS", "topic": "Compounded overnight rates and OIS", "functions": "compounded_overnight_rate, ois_par_rate, ois_pv"},
    {"stage": "06 Volatility", "topic": "Black/normal rate-option quoting & implied vol", "functions": "caplet_price, swaption_price, implied_rate_volatility"},
    {"stage": "07 Caps/Floors", "topic": "Cap/floor decomposition & caplet vol stripping", "functions": "cap_floor_price, strip_caplet_volatilities"},
    {"stage": "08 Swaptions", "topic": "Payer/receiver swaptions and annuity measure", "functions": "swaption_price"},
    {"stage": "09 Smile", "topic": "SABR smile & calibration", "functions": "hagan_sabr_volatility, calibrate_sabr"},
    {"stage": "10 Short-rate models", "topic": "Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski", "functions": "vasicek_zero_coupon_bond, cir_zero_coupon_bond, hull_white_paths, ho_lee_paths, black_karasinski_paths"},
    {"stage": "11 HJM/LMM", "topic": "Forward-rate dynamics & market models", "functions": "hjm_one_factor_paths, lmm_terminal_measure_paths"},
    {"stage": "12 Calibration", "topic": "Time-series and volatility calibration", "functions": "calibrate_vasicek, calibrate_sabr, strip_caplet_volatilities"},
    {"stage": "13 Curve risk", "topic": "DV01, key-rate DV01, convexity, interpolation risk", "functions": "dv01, key_rate_dv01, dollar_convexity, curve_interpolation_risk"},
    {"stage": "14 Curve factors", "topic": "Level/slope/curvature & PCA", "functions": "level_slope_curvature, yield_curve_pca"},
    {"stage": "15 Relative value", "topic": "Carry/roll-down & curve-shape research", "functions": "carry_roll_down, curve_interpolation_risk"},
    {"stage": "16 Research", "topic": "No-arbitrage diagnostics and hypothesis generation", "functions": "no_arbitrage_curve_diagnostics, asr.discovery.weekly"},
)


def rates_curriculum() -> pd.DataFrame:
    """Return the built-in Interest Rate Derivatives Quant learning/research map."""
    return pd.DataFrame(RATE_QUANT_CURRICULUM)


RATE_QUANT_EXERCISES: tuple[dict[str, str], ...] = (
    {"id":"IR-01","level":"Foundation","topic":"Discounting","task":"Convert zero rates into discount factors under continuous, simple and periodic compounding; reconcile the results.","api":"discount_factor, zero_rate_from_discount"},
    {"id":"IR-02","level":"Foundation","topic":"Day count","task":"Compute ACT/360, ACT/365F, 30/360 and 30E/360 accruals for the same coupon period and quantify the cashflow impact.","api":"year_fraction"},
    {"id":"IR-03","level":"Foundation","topic":"Forwards","task":"Derive simple and continuously compounded forwards from two discount factors and verify the no-arbitrage identity.","api":"forward_rate_from_discounts"},
    {"id":"IR-04","level":"Foundation","topic":"Curve bootstrap","task":"Bootstrap a deposit/FRA/swap curve and reprice every input quote to numerical tolerance.","api":"bootstrap_discount_curve, DiscountCurve"},
    {"id":"IR-05","level":"Foundation","topic":"Bonds","task":"Price a coupon bond from the curve and reconcile clean price, dirty price and accrued interest.","api":"bond_price_from_curve, accrued_interest, clean_price, dirty_price"},
    {"id":"IR-06","level":"Foundation","topic":"Bond risk","task":"Compare yield duration/convexity with curve DV01 and explain why the risk measures are not identical objects.","api":"modified_duration, convexity, dv01"},
    {"id":"IR-07","level":"Core","topic":"FRA","task":"Price the same FRA with start and end settlement representations and explain the settlement denominator.","api":"fra_pv"},
    {"id":"IR-08","level":"Core","topic":"IRS","task":"Compute a par swap rate, value an off-market payer swap and verify PV is zero at the par fixed rate.","api":"swap_par_rate, swap_pv"},
    {"id":"IR-09","level":"Core","topic":"Swap risk","task":"Calculate swap DV01 and key-rate DV01; identify which curve buckets dominate risk.","api":"swap_dv01, key_rate_dv01"},
    {"id":"IR-10","level":"Core","topic":"Multi-curve","task":"Build OIS discounting and a tenor projection curve; compare single-curve and multi-curve swap par rates.","api":"bootstrap_projection_curve_from_swaps, MultiCurve"},
    {"id":"IR-11","level":"Core","topic":"Basis swaps","task":"Value a basis swap from two projection curves and solve the spread that makes PV zero.","api":"basis_swap_pv"},
    {"id":"IR-12","level":"Core","topic":"Rate futures","task":"Translate futures price into quoted rate and compare the quote with an FRA forward.","api":"rate_future_price, rate_from_future_price"},
    {"id":"IR-13","level":"Derivatives","topic":"Caplets","task":"Price ATM/ITM/OTM caplets under Black-76 and Bachelier; compare sensitivity in low-rate regimes.","api":"caplet_price"},
    {"id":"IR-14","level":"Derivatives","topic":"Caps/floors","task":"Decompose a cap into caplets and verify cap price equals the sum of constituent caplet prices.","api":"cap_floor_price, caplet_price"},
    {"id":"IR-15","level":"Derivatives","topic":"Caplet stripping","task":"Generate cumulative cap prices from known caplet vols, strip the vols back and quantify numerical error.","api":"strip_caplet_volatilities"},
    {"id":"IR-16","level":"Derivatives","topic":"Swaptions","task":"Price payer/receiver swaptions under Black and normal models and verify monotonicity in volatility.","api":"swaption_price"},
    {"id":"IR-17","level":"Derivatives","topic":"Implied volatility","task":"Recover implied volatility from a synthetic option price using a scalar inversion and test bracket failures.","api":"implied_rate_volatility"},
    {"id":"IR-18","level":"Smile","topic":"SABR","task":"Generate a synthetic smile with SABR, recalibrate alpha/rho/nu and compare fitted versus true vols.","api":"hagan_sabr_volatility, calibrate_sabr"},
    {"id":"IR-19","level":"Models","topic":"Vasicek","task":"Price zero-coupon bonds across maturities and study sensitivity to mean reversion, long-run mean and volatility.","api":"vasicek_zero_coupon_bond"},
    {"id":"IR-20","level":"Models","topic":"CIR","task":"Price CIR zero-coupon bonds and study the impact of the Feller-region parameter choices on rate behaviour.","api":"cir_zero_coupon_bond"},
    {"id":"IR-21","level":"Models","topic":"Hull-White","task":"Simulate one-factor Hull-White paths, estimate moments and compare empirical mean reversion with theory.","api":"hull_white_paths"},
    {"id":"IR-22","level":"Models","topic":"Ho-Lee","task":"Simulate Ho-Lee and compare its non-mean-reverting dispersion with Hull-White over long horizons.","api":"ho_lee_paths, hull_white_paths"},
    {"id":"IR-23","level":"Models","topic":"Black-Karasinski","task":"Simulate positive Black-Karasinski rates and compare distributional asymmetry with Gaussian short-rate models.","api":"black_karasinski_paths"},
    {"id":"IR-24","level":"Advanced","topic":"HJM","task":"Simulate an HJM forward surface and verify how the no-arbitrage drift changes with the volatility term structure.","api":"hjm_one_factor_paths"},
    {"id":"IR-25","level":"Advanced","topic":"LMM","task":"Simulate correlated tenor forwards under the terminal measure and inspect the drift contribution of later forwards.","api":"lmm_terminal_measure_paths"},
    {"id":"IR-26","level":"Calibration","topic":"Vasicek calibration","task":"Simulate a Vasicek series, re-estimate parameters by AR(1) mapping and quantify finite-sample bias.","api":"calibrate_vasicek"},
    {"id":"IR-27","level":"Risk","topic":"Curve PCA","task":"Extract level/slope/curvature-like principal components from historical curve changes and report explained variance.","api":"yield_curve_pca, level_slope_curvature"},
    {"id":"IR-28","level":"Risk","topic":"Interpolation risk","task":"Reconstruct the same nodes with multiple interpolation schemes and measure induced forward-rate dispersion.","api":"curve_interpolation_risk"},
    {"id":"IR-29","level":"Relative value","topic":"Carry & roll-down","task":"Compute static-curve zero-bond carry/roll across maturities and test whether the ranking survives historical regime changes.","api":"carry_roll_down"},
    {"id":"IR-30","level":"Research","topic":"No-arbitrage diagnostics","task":"Inject controlled curve inconsistencies and determine which diagnostics detect them first.","api":"no_arbitrage_curve_diagnostics"},
    {"id":"IR-30A","level":"Curves","topic":"Nelson-Siegel","task":"Fit a Nelson-Siegel curve to zero rates, inspect level/slope/curvature parameters and compare pricing errors with interpolation.","api":"calibrate_nelson_siegel"},
    {"id":"IR-30B","level":"Curves","topic":"Svensson","task":"Fit a Svensson curve to a shaped term structure and compare forward-rate smoothness and out-of-sample stability.","api":"calibrate_svensson"},
    {"id":"IR-30C","level":"Linear rates","topic":"RFR/OIS","task":"Compound overnight fixings, compare with the simple average and price an OIS from the discount curve.","api":"compounded_overnight_rate, ois_pv"},
    {"id":"IR-30D","level":"Fixed income","topic":"Bond forwards","task":"Compute a no-arbitrage coupon-bond forward and attribute the difference from spot to carry and interim coupons.","api":"bond_forward_price"},
    {"id":"IR-30E","level":"Cross-currency","topic":"FX forwards","task":"Verify covered interest parity from domestic and foreign discount curves and stress the forward to curve shifts.","api":"fx_forward_rate, curve_scenario"},
    {"id":"IR-30F","level":"Cross-currency","topic":"XCCY foundation","task":"Value a terminal exchange of domestic and foreign notionals and identify what a full cross-currency basis model must add.","api":"cross_currency_zero_coupon_pv"},
    {"id":"IR-30G","level":"Inflation","topic":"ZC inflation swaps","task":"Compute realized annualized inflation from an index ratio and value a supplied terminal-ratio zero-coupon inflation swap.","api":"zero_coupon_inflation_rate, zero_coupon_inflation_swap_pv"},
    {"id":"IR-30H","level":"Exotics","topic":"Bermudan LSM","task":"Build synthetic exercise values and state paths, price early exercise by LSM and inspect exercise probabilities by date.","api":"bermudan_lsm"},
    {"id":"IR-30I","level":"Risk","topic":"Curve scenarios","task":"Apply parallel, steepener and butterfly shocks and compare PV changes with linear DV01/key-rate approximations.","api":"curve_scenario"},
    {"id":"IR-30J","level":"Risk","topic":"Key-rate hedging","task":"Solve a multi-instrument key-rate hedge, quantify residual exposure and study regularization under collinearity.","api":"key_rate_hedge"},
    {"id":"IR-31","level":"Research","topic":"Research discovery","task":"Run the yield-curve discovery engine, select one candidate, define its falsification rule and produce the Friday-to-Friday plan.","api":"asr.discovery.weekly, ResearchBoard.start, weekly_plan"},
    {"id":"IR-32","level":"Research","topic":"Publication","task":"Complete one full research cycle and generate the research note, claim audit, reproducibility checklist and project manifest.","api":"asr.research.weekly_cycle, WeeklyResearchCycle.publication_pack"},
)


def rates_exercises(*, level: str | None = None, topic: str | None = None) -> pd.DataFrame:
    """Return the built-in exercise bank for Interest Rate Derivatives Quant training."""
    frame = pd.DataFrame(RATE_QUANT_EXERCISES)
    if level is not None:
        frame = frame[frame["level"].str.lower() == level.lower()]
    if topic is not None:
        frame = frame[frame["topic"].str.contains(topic, case=False, regex=False)]
    return frame.reset_index(drop=True)


@dataclass
class RateQuantLab:
    """Simple high-level facade for Fixed Income / Interest Rate Derivatives work."""

    discount_curve: DiscountCurve
    projections: dict[str, ForwardCurve] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_zero_rates(
        cls,
        maturities: ArrayLike,
        zero_rates: ArrayLike,
        *,
        compounding: str | int = "continuous",
        interpolation: str = "log_linear",
    ) -> "RateQuantLab":
        return cls(DiscountCurve.from_zero_rates(maturities, zero_rates, compounding=compounding, interpolation=interpolation))

    @classmethod
    def from_ecb(
        cls,
        maturities: Sequence[str] = ("3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"),
        *,
        interpolation: str = "log_linear",
        provider: Any | None = None,
    ) -> "RateQuantLab":
        """Build a lab from the latest common ECB euro-area AAA spot-curve row.

        Network access is explicit because this constructor calls the ECB Data
        Portal.  Pass a compatible provider in tests or controlled environments.
        """
        if provider is None:
            from .providers import ECBProvider
            provider = ECBProvider()
        row = provider.latest_yield_curve(maturities=maturities)
        times = np.asarray([maturity_to_years(m) for m in row.index], dtype=float)
        order = np.argsort(times)
        curve = DiscountCurve.from_zero_rates(
            times[order], row.to_numpy(dtype=float)[order], interpolation=interpolation,
            name="ECB AAA euro-area spot curve",
        )
        metadata = dict(curve.metadata)
        metadata.update({"provider": "ECB", "observation_time": str(row.name)})
        curve = DiscountCurve(curve.times, curve.discounts, curve.interpolation, curve.name, metadata)
        lab = cls(curve)
        lab.history.append({"action": "load_ecb_curve", "observation_time": str(row.name)})
        return lab

    @classmethod
    def bootstrap(
        cls,
        *,
        deposits: pd.DataFrame | None = None,
        fras: pd.DataFrame | None = None,
        swaps: pd.DataFrame | None = None,
        swap_frequency: int = 2,
    ) -> "RateQuantLab":
        return cls(bootstrap_discount_curve(deposits=deposits, fras=fras, swaps=swaps, swap_frequency=swap_frequency))

    @property
    def curve(self) -> DiscountCurve:
        return self.discount_curve

    def add_projection(self, name: str, curve: ForwardCurve) -> "RateQuantLab":
        self.projections[name] = curve
        self.history.append({"action": "add_projection", "name": name})
        return self

    def implied_projection(self, tenor: float, name: str | None = None) -> ForwardCurve:
        key = name or f"{tenor:g}Y"
        curve = projection_curve_from_discount(self.discount_curve, tenor, name=key)
        self.add_projection(key, curve)
        return curve

    def fra(self, start: float, end: float, strike: float, **kwargs: Any) -> float:
        return fra_pv(self.discount_curve, start, end, strike, **kwargs)

    def swap(self, start: float, end: float, fixed_rate: float, **kwargs: Any) -> float:
        if "frequency" in kwargs and "fixed_frequency" not in kwargs:
            kwargs["fixed_frequency"] = kwargs.pop("frequency")
        return swap_pv(self.discount_curve, start, end, fixed_rate, **kwargs)

    def par_swap(self, start: float, end: float, **kwargs: Any) -> float:
        if "frequency" in kwargs and "fixed_frequency" not in kwargs:
            kwargs["fixed_frequency"] = kwargs.pop("frequency")
        return swap_par_rate(self.discount_curve, start, end, **kwargs)

    def caplet(self, start: float, end: float, strike: float, volatility: float, **kwargs: Any) -> float:
        return caplet_price(self.discount_curve, start, end, strike, volatility, **kwargs)

    def swaption(self, expiry: float, swap_end: float, strike: float, volatility: float, **kwargs: Any) -> float:
        return swaption_price(self.discount_curve, expiry, swap_end, strike, volatility, **kwargs)

    def diagnostics(self) -> pd.Series:
        return no_arbitrage_curve_diagnostics(self.discount_curve)

    def curriculum(self) -> pd.DataFrame:
        return rates_curriculum()

    def exercises(self, *, level: str | None = None, topic: str | None = None) -> pd.DataFrame:
        return rates_exercises(level=level, topic=topic)

    def risk(self, pricer, *, key_maturities: Sequence[float] | None = None, bump: float = 1e-4) -> pd.Series:
        result = {
            "pv": float(pricer(self.discount_curve)),
            "dv01": dv01(pricer, self.discount_curve, bump=bump),
            "dollar_convexity": dollar_convexity(pricer, self.discount_curve, bump=bump),
        }
        series = pd.Series(result)
        if key_maturities:
            buckets = key_rate_dv01(pricer, self.discount_curve, key_maturities, bump=bump)
            series = pd.concat([series, buckets.rename(lambda x: f"krdv01_{x:g}Y")])
        return series


__all__ = [
    "zero_coupon_price", "bond_cashflows", "bond_price", "yield_to_maturity", "macaulay_duration", "modified_duration", "convexity", "bootstrap_zero_curve",
    "year_fraction", "maturity_to_years", "payment_schedule", "discount_factor", "zero_rate_from_discount",
    "forward_discount_factor", "forward_rate_from_discounts", "DiscountCurve", "ForwardCurve", "MultiCurve",
    "bootstrap_discount_curve", "projection_curve_from_discount", "bootstrap_projection_curve_from_swaps",
    "bond_price_from_curve", "accrued_interest", "clean_price", "dirty_price", "dv01", "dollar_convexity", "key_rate_dv01",
    "compounded_overnight_rate", "ois_par_rate", "ois_pv", "bond_forward_price", "fx_forward_rate",
    "cross_currency_zero_coupon_pv", "zero_coupon_inflation_rate", "zero_coupon_inflation_swap_pv",
    "curve_scenario", "HedgeSolution", "key_rate_hedge", "BermudanLSMResult", "bermudan_lsm",
    "fra_forward_rate", "fra_pv", "swap_annuity", "swap_par_rate", "swap_pv", "swap_dv01", "basis_swap_pv",
    "rate_future_price", "rate_from_future_price", "caplet_price", "cap_floor_price", "swaption_price",
    "implied_rate_volatility", "strip_caplet_volatilities", "hagan_sabr_volatility", "SABRCalibration", "calibrate_sabr",
    "vasicek_zero_coupon_bond", "cir_zero_coupon_bond", "hull_white_paths", "ho_lee_paths", "black_karasinski_paths",
    "hjm_one_factor_paths", "lmm_terminal_measure_paths", "VasicekCalibration", "calibrate_vasicek",
    "yield_curve_pca", "level_slope_curvature", "no_arbitrage_curve_diagnostics", "curve_interpolation_risk", "carry_roll_down",
    "nelson_siegel_yield", "svensson_yield", "YieldCurveCalibration", "calibrate_nelson_siegel", "calibrate_svensson",
    "RATE_QUANT_CURRICULUM", "rates_curriculum", "RATE_QUANT_EXERCISES", "rates_exercises", "RateQuantLab",
]
