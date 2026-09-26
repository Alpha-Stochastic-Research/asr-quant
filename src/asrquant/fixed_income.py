"""Core fixed-income pricing, yield, duration, convexity, and curve bootstrapping."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def zero_coupon_price(face: float, rate: float, maturity: float, compounding: int | None = None) -> float:
    """Price a zero-coupon bond under continuous or periodic compounding."""
    if face <= 0 or maturity < 0:
        raise ValueError("face must be positive and maturity non-negative")
    if compounding is None:
        return float(face*np.exp(-rate*maturity))
    if compounding <= 0:
        raise ValueError("compounding must be positive")
    return float(face/(1+rate/compounding)**(compounding*maturity))


def bond_cashflows(face: float, coupon_rate: float, maturity: float, frequency: int = 2) -> pd.Series:
    """Return deterministic fixed-coupon cash flows indexed by year fraction."""
    if face <= 0 or maturity <= 0 or frequency <= 0:
        raise ValueError("face, maturity, and frequency must be positive")
    periods = int(round(maturity*frequency))
    times = np.arange(1, periods+1)/frequency
    cash = np.full(periods, face*coupon_rate/frequency)
    cash[-1] += face
    return pd.Series(cash, index=times, name="cashflow")


def bond_price(face: float, coupon_rate: float, maturity: float, yield_rate: float, frequency: int = 2) -> float:
    """Price a fixed-coupon bond from its yield to maturity."""
    cf = bond_cashflows(face, coupon_rate, maturity, frequency)
    periods = np.arange(1, len(cf)+1)
    return float(np.sum(cf.to_numpy()/(1+yield_rate/frequency)**periods))


def yield_to_maturity(price: float, face: float, coupon_rate: float, maturity: float, frequency: int = 2) -> float:
    """Solve the yield to maturity by robust scalar bracketing."""
    if price <= 0:
        raise ValueError("price must be positive")
    objective = lambda y: bond_price(face, coupon_rate, maturity, y, frequency)-price
    return float(brentq(objective, -0.99*frequency, 100.0))


def macaulay_duration(face: float, coupon_rate: float, maturity: float, yield_rate: float, frequency: int = 2) -> float:
    """Macaulay duration in years."""
    cf = bond_cashflows(face, coupon_rate, maturity, frequency)
    periods = np.arange(1, len(cf)+1); pv = cf.to_numpy()/(1+yield_rate/frequency)**periods
    return float(np.sum(cf.index.to_numpy()*pv)/np.sum(pv))


def modified_duration(face: float, coupon_rate: float, maturity: float, yield_rate: float, frequency: int = 2) -> float:
    """Modified duration in years."""
    return macaulay_duration(face, coupon_rate, maturity, yield_rate, frequency)/(1+yield_rate/frequency)


def convexity(face: float, coupon_rate: float, maturity: float, yield_rate: float, frequency: int = 2) -> float:
    """Standard discrete-compounding bond convexity."""
    cf = bond_cashflows(face, coupon_rate, maturity, frequency)
    n = np.arange(1, len(cf)+1); denom=(1+yield_rate/frequency)
    price = np.sum(cf.to_numpy()/denom**n)
    value = np.sum(cf.to_numpy()*n*(n+1)/denom**(n+2))/(price*frequency**2)
    return float(value)


def bootstrap_zero_curve(instruments: pd.DataFrame, frequency: int | None = None) -> pd.Series:
    """Bootstrap periodically compounded zero rates from par coupon instruments.

    Parameters
    ----------
    instruments
        Table containing ``maturity`` (years) and ``par_rate`` (decimal). An
        optional ``frequency`` column may be supplied when all instruments use
        the same coupon frequency.
    frequency
        Coupon payments per year. When omitted, a constant ``frequency`` column
        is inferred if present; otherwise annual coupons are assumed.

    Notes
    -----
    A simple par bootstrap requires an instrument at every coupon date needed by
    later instruments. The function therefore rejects incomplete coupon grids
    instead of silently omitting unavailable discount factors.
    """
    frame = pd.DataFrame(instruments).copy()
    if not {"maturity", "par_rate"}.issubset(frame.columns):
        raise ValueError("instruments require maturity and par_rate columns")
    frame["maturity"] = pd.to_numeric(frame["maturity"], errors="raise")
    frame["par_rate"] = pd.to_numeric(frame["par_rate"], errors="raise")
    frame = frame.sort_values("maturity").reset_index(drop=True)

    inferred_frequency: int | None = None
    if "frequency" in frame.columns:
        raw = pd.to_numeric(frame["frequency"], errors="raise")
        unique = sorted(set(float(value) for value in raw))
        if len(unique) != 1:
            raise ValueError("bootstrap_zero_curve requires one common coupon frequency")
        value = unique[0]
        if not float(value).is_integer():
            raise ValueError("frequency must be a positive integer")
        inferred_frequency = int(value)

    active_frequency = int(
        frequency if frequency is not None else (inferred_frequency or 1)
    )
    if active_frequency <= 0:
        raise ValueError("frequency must be a positive integer")
    if inferred_frequency is not None and frequency is not None and inferred_frequency != active_frequency:
        raise ValueError("frequency argument conflicts with instruments['frequency']")

    discounts: dict[int, float] = {}
    rates: dict[float, float] = {}
    for row in frame.itertuples(index=False):
        maturity = float(row.maturity)
        par_rate = float(row.par_rate)
        if maturity <= 0:
            raise ValueError("maturities must be positive")
        periods_float = maturity * active_frequency
        periods = int(round(periods_float))
        if periods < 1 or not np.isclose(periods_float, periods, atol=1e-10, rtol=0.0):
            raise ValueError(
                "each maturity must be an integer multiple of 1/frequency"
            )
        if periods in discounts:
            raise ValueError("duplicate maturity on the coupon grid")

        missing = [index for index in range(1, periods) if index not in discounts]
        if missing:
            missing_times = [index / active_frequency for index in missing]
            raise ValueError(
                "incomplete par curve: missing instruments at coupon dates "
                f"{missing_times}"
            )

        coupon = par_rate / active_frequency
        prior = sum(coupon * discounts[index] for index in range(1, periods))
        discount = (1.0 - prior) / (1.0 + coupon)
        if not 0.0 < discount <= 1.0 + 1e-12:
            raise ValueError(
                "inconsistent par curve produces an invalid discount factor"
            )
        discounts[periods] = float(discount)
        rates[maturity] = float(
            active_frequency * (discount ** (-1.0 / periods) - 1.0)
        )

    return pd.Series(rates, name="zero_rate", dtype=float)

