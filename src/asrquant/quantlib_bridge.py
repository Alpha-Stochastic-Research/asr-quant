"""Optional QuantLib interoperability and independent cross-check helpers.

ASRQuant does not depend on QuantLib. When QuantLib-Python is installed, this
module can be used as a second implementation for selected conventions/pricers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class QuantLibUnavailable(ImportError):
    pass


def _ql():
    try:
        import QuantLib as ql
    except ImportError as exc:
        raise QuantLibUnavailable("QuantLib is not installed; install the optional interop extra") from exc
    return ql


@dataclass(frozen=True)
class CrossCheck:
    asr_value: float
    reference_value: float
    absolute_error: float
    relative_error: float
    passed: bool
    tolerance: float


def compare_scalar(asr_value: float, reference_value: float, *, atol: float = 1e-10, rtol: float = 1e-8) -> CrossCheck:
    a, b = float(asr_value), float(reference_value)
    err = abs(a-b); rel = err / max(abs(b), atol); tol = atol + rtol*abs(b)
    return CrossCheck(a, b, err, rel, err <= tol, tol)


def quantlib_black_scholes_price(spot: float, strike: float, maturity: float, rate: float, volatility: float, *, option: str = "call", dividend: float = 0.0) -> float:
    ql = _ql(); today = ql.Date(1, 1, 2020); ql.Settings.instance().evaluationDate = today
    expiry = today + max(1, int(round(maturity*365))); dc = ql.Actual365Fixed(); calendar = ql.NullCalendar()
    payoff_type = ql.Option.Call if option.lower() == "call" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(payoff_type, strike); exercise = ql.EuropeanExercise(expiry)
    rf = ql.YieldTermStructureHandle(ql.FlatForward(today, rate, dc)); div = ql.YieldTermStructureHandle(ql.FlatForward(today, dividend, dc))
    vol = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, volatility, dc))
    process = ql.BlackScholesMertonProcess(ql.QuoteHandle(ql.SimpleQuote(spot)), div, rf, vol)
    instrument = ql.VanillaOption(payoff, exercise); instrument.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    return float(instrument.NPV())


def cross_check(callable_asr: Callable[[], float], callable_reference: Callable[[], float], *, atol: float = 1e-10, rtol: float = 1e-8) -> CrossCheck:
    return compare_scalar(callable_asr(), callable_reference(), atol=atol, rtol=rtol)


__all__ = ["QuantLibUnavailable", "CrossCheck", "compare_scalar", "quantlib_black_scholes_price", "cross_check"]
