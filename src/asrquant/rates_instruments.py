"""Transparent fixed-income instrument objects built on ASRQuant discount curves."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

import numpy as np
import pandas as pd

from .contracts import InputValidationError, ResultMixin
from .interest_rates import (
    DiscountCurve,
    dollar_convexity,
    dv01,
    key_rate_dv01,
    payment_schedule,
)


class RateInstrument(Protocol):
    def price(self, curve: DiscountCurve) -> float: ...
    def cashflows(self, curve: DiscountCurve | None = None) -> pd.DataFrame: ...


@dataclass(frozen=True)
class InstrumentRiskResult(ResultMixin):
    pv: float
    dv01: float
    convexity: float
    key_rate_dv01: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="rates_instrument_risk", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "pv": self.pv,
                "dv01": self.dv01,
                "dollar_convexity": self.convexity,
                "key_rate_buckets": int(len(self.key_rate_dv01)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        if self.key_rate_dv01.empty:
            return self.summary.rename("value").to_frame()
        frame = self.key_rate_dv01.rename("key_rate_dv01").to_frame()
        frame.index.name = "maturity"
        return frame

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "summary": self.summary.to_dict(),
            "key_rate_dv01": self.key_rate_dv01.to_dict(),
            "metadata": dict(self.metadata),
        }


def _validate_position(position: str) -> str:
    key = str(position).lower()
    if key not in {"payer", "receiver", "long", "short"}:
        raise InputValidationError("position must be payer/receiver or long/short")
    return key


def _risk_for(pricer, curve: DiscountCurve, key_maturities: Sequence[float] | None = None) -> InstrumentRiskResult:
    keys = list(key_maturities or curve.times[1:])
    return InstrumentRiskResult(
        pv=float(pricer(curve)),
        dv01=float(dv01(pricer, curve)),
        convexity=float(dollar_convexity(pricer, curve)),
        key_rate_dv01=key_rate_dv01(pricer, curve, keys) if keys else pd.Series(dtype=float),
        metadata={"curve": curve.name},
    )


@dataclass(frozen=True)
class Deposit:
    maturity: float
    rate: float
    notional: float = 1.0
    start: float = 0.0

    def __post_init__(self) -> None:
        if self.maturity <= self.start or self.notional <= 0:
            raise InputValidationError("require maturity > start and positive notional")
        if 1.0 + self.rate * (self.maturity - self.start) <= 0:
            raise InputValidationError("deposit accrual factor must remain positive")

    @property
    def accrual(self) -> float:
        return self.maturity - self.start

    def fair_rate(self, curve: DiscountCurve) -> float:
        p0 = float(curve.df(self.start))
        p1 = float(curve.df(self.maturity))
        return (p0 / p1 - 1.0) / self.accrual

    def price(self, curve: DiscountCurve) -> float:
        return float(
            -self.notional * curve.df(self.start)
            + self.notional * (1.0 + self.rate * self.accrual) * curve.df(self.maturity)
        )

    def cashflows(self, curve: DiscountCurve | None = None) -> pd.DataFrame:
        amounts = [-self.notional, self.notional * (1.0 + self.rate * self.accrual)]
        frame = pd.DataFrame({"time": [self.start, self.maturity], "cashflow": amounts})
        if curve is not None:
            frame["discount_factor"] = [curve.df(self.start), curve.df(self.maturity)]
            frame["pv"] = frame["cashflow"] * frame["discount_factor"]
        return frame

    def risk(self, curve: DiscountCurve, key_maturities: Sequence[float] | None = None) -> InstrumentRiskResult:
        return _risk_for(self.price, curve, key_maturities)


@dataclass(frozen=True)
class FRA:
    start: float
    end: float
    fixed_rate: float
    notional: float = 1.0
    position: str = "payer"

    def __post_init__(self) -> None:
        if self.end <= self.start or self.notional <= 0:
            raise InputValidationError("require end > start and positive notional")
        _validate_position(self.position)

    @property
    def accrual(self) -> float:
        return self.end - self.start

    def forward_rate(self, curve: DiscountCurve) -> float:
        return float(curve.forward_rate(self.start, self.end, "simple"))

    def price(self, curve: DiscountCurve) -> float:
        forward = self.forward_rate(curve)
        sign = 1.0 if self.position.lower() in {"payer", "long"} else -1.0
        # Value at end discounted to today; transparent simple-FRA approximation.
        return float(sign * self.notional * self.accrual * (forward - self.fixed_rate) * curve.df(self.end))

    def cashflows(self, curve: DiscountCurve | None = None) -> pd.DataFrame:
        amount = np.nan if curve is None else self.price(curve) / float(curve.df(self.end))
        frame = pd.DataFrame({"time": [self.end], "cashflow": [amount]})
        if curve is not None:
            frame["discount_factor"] = [curve.df(self.end)]
            frame["pv"] = [self.price(curve)]
        return frame

    def risk(self, curve: DiscountCurve, key_maturities: Sequence[float] | None = None) -> InstrumentRiskResult:
        return _risk_for(self.price, curve, key_maturities)


@dataclass(frozen=True)
class FixedRateBond:
    maturity: float
    coupon_rate: float
    face: float = 100.0
    frequency: int = 2

    def __post_init__(self) -> None:
        if self.maturity <= 0 or self.face <= 0 or self.frequency <= 0:
            raise InputValidationError("maturity, face and frequency must be positive")

    @property
    def payment_times(self) -> np.ndarray:
        return payment_schedule(0.0, self.maturity, self.frequency)

    def cashflows(self, curve: DiscountCurve | None = None) -> pd.DataFrame:
        times = self.payment_times
        amounts = np.full(len(times), self.face * self.coupon_rate / self.frequency, dtype=float)
        amounts[-1] += self.face
        frame = pd.DataFrame({"time": times, "cashflow": amounts})
        if curve is not None:
            frame["discount_factor"] = np.asarray(curve.df(times), dtype=float)
            frame["pv"] = frame["cashflow"] * frame["discount_factor"]
        return frame

    def price(self, curve: DiscountCurve) -> float:
        return float(self.cashflows(curve)["pv"].sum())

    def risk(self, curve: DiscountCurve, key_maturities: Sequence[float] | None = None) -> InstrumentRiskResult:
        return _risk_for(self.price, curve, key_maturities)


@dataclass(frozen=True)
class InterestRateSwap:
    maturity: float
    fixed_rate: float
    notional: float = 1.0
    start: float = 0.0
    fixed_frequency: int = 2
    float_frequency: int = 2
    position: str = "payer"

    def __post_init__(self) -> None:
        if self.maturity <= self.start or self.notional <= 0:
            raise InputValidationError("require maturity > start and positive notional")
        if self.fixed_frequency <= 0 or self.float_frequency <= 0:
            raise InputValidationError("payment frequencies must be positive")
        _validate_position(self.position)

    @property
    def fixed_times(self) -> np.ndarray:
        return payment_schedule(self.start, self.maturity, self.fixed_frequency)

    @property
    def float_times(self) -> np.ndarray:
        return payment_schedule(self.start, self.maturity, self.float_frequency)

    def annuity(self, curve: DiscountCurve) -> float:
        alpha = 1.0 / self.fixed_frequency
        return float(np.sum(alpha * np.asarray(curve.df(self.fixed_times), dtype=float)))

    def par_rate(self, curve: DiscountCurve) -> float:
        annuity = self.annuity(curve)
        if annuity <= 0:
            raise InputValidationError("swap annuity must be positive")
        return float((curve.df(self.start) - curve.df(self.maturity)) / annuity)

    def price(self, curve: DiscountCurve) -> float:
        annuity = self.annuity(curve)
        float_leg = float(curve.df(self.start) - curve.df(self.maturity))
        fixed_leg = self.fixed_rate * annuity
        payer = self.notional * (float_leg - fixed_leg)
        return float(payer if self.position.lower() == "payer" else -payer)

    def cashflows(self, curve: DiscountCurve | None = None) -> pd.DataFrame:
        if curve is None:
            times = self.fixed_times
            return pd.DataFrame(
                {
                    "time": times,
                    "fixed_cashflow": np.full(len(times), self.notional * self.fixed_rate / self.fixed_frequency),
                }
            )
        fixed_times = self.fixed_times
        fixed_alpha = 1.0 / self.fixed_frequency
        fixed_cf = np.full(len(fixed_times), self.notional * self.fixed_rate * fixed_alpha)
        fixed_pv = fixed_cf * np.asarray(curve.df(fixed_times), dtype=float)

        float_ends = self.float_times
        float_starts = np.r_[self.start, float_ends[:-1]]
        float_alpha = float_ends - float_starts
        forwards = np.asarray(curve.forward_rate(float_starts, float_ends, "simple"), dtype=float)
        float_cf = self.notional * float_alpha * forwards
        float_pv = float_cf * np.asarray(curve.df(float_ends), dtype=float)
        rows = []
        for t, cf, pv in zip(fixed_times, fixed_cf, fixed_pv):
            rows.append({"leg": "fixed", "time": t, "cashflow": cf, "pv": pv})
        for t, cf, pv in zip(float_ends, float_cf, float_pv):
            rows.append({"leg": "floating", "time": t, "cashflow": cf, "pv": pv})
        frame = pd.DataFrame(rows).sort_values(["time", "leg"]).reset_index(drop=True)
        return frame

    def risk(self, curve: DiscountCurve, key_maturities: Sequence[float] | None = None) -> InstrumentRiskResult:
        return _risk_for(self.price, curve, key_maturities)


@dataclass(frozen=True)
class OIS(InterestRateSwap):
    fixed_frequency: int = 1
    float_frequency: int = 1


__all__ = [
    "RateInstrument",
    "InstrumentRiskResult",
    "Deposit",
    "FRA",
    "FixedRateBond",
    "InterestRateSwap",
    "OIS",
]
