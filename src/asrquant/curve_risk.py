"""Curve, key-rate and market-quote sensitivities for rate instruments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

from .contracts import ResultMixin
from .curve_builder import CurveBuildResult
from .interest_rates import DiscountCurve, dollar_convexity, dv01, key_rate_dv01


def _pricer(instrument_or_pricer: Any) -> Callable[[DiscountCurve], float]:
    if callable(instrument_or_pricer) and not hasattr(instrument_or_pricer, "price"):
        return instrument_or_pricer
    if hasattr(instrument_or_pricer, "price"):
        return lambda curve: float(instrument_or_pricer.price(curve))
    raise TypeError("instrument_or_pricer must be callable or expose price(curve)")


def _bump_zero_node(curve: DiscountCurve, maturity: float, bump: float) -> DiscountCurve:
    positive = curve.times > 0
    times = curve.times[positive]
    zero = -np.log(curve.discounts[positive]) / times
    idx = int(np.argmin(np.abs(times - maturity)))
    if not np.isclose(times[idx], maturity, atol=1e-12):
        raise ValueError(f"maturity {maturity} is not a curve node")
    zero = zero.copy()
    zero[idx] += bump
    return DiscountCurve.from_zero_rates(
        times,
        zero,
        interpolation=curve.interpolation,
        name=curve.name,
        metadata=curve.metadata,
    )


@dataclass
class CurveRiskResult(ResultMixin):
    pv: float
    dv01: float
    dollar_convexity: float
    key_rate_dv01: pd.Series
    node_delta: pd.Series
    quote_delta: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    quote_pv01: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="curve_risk", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "pv": self.pv,
                "dv01": self.dv01,
                "dollar_convexity": self.dollar_convexity,
                "key_rate_buckets": int(len(self.key_rate_dv01)),
                "quote_sensitivities": int(len(self.quote_delta)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        frames = []
        if len(self.key_rate_dv01):
            f = self.key_rate_dv01.rename("value").to_frame()
            f["measure"] = "key_rate_dv01"
            frames.append(f.reset_index(names="bucket"))
        if len(self.quote_pv01):
            f = self.quote_pv01.rename("value").to_frame()
            f["measure"] = "quote_pv01"
            frames.append(f.reset_index(names="bucket"))
        return pd.concat(frames, ignore_index=True) if frames else self.summary.rename("value").to_frame()

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "summary": self.summary.to_dict(),
            "key_rate_dv01": self.key_rate_dv01.to_dict(),
            "node_delta": self.node_delta.to_dict(),
            "quote_delta": self.quote_delta.to_dict(),
            "quote_pv01": self.quote_pv01.to_dict(),
            "metadata": dict(self.metadata),
        }


def curve_risk(
    instrument_or_pricer: Any,
    curve: DiscountCurve,
    *,
    key_maturities: Sequence[float] | None = None,
    build_result: CurveBuildResult | None = None,
    bump: float = 1e-4,
) -> CurveRiskResult:
    """Compute parallel, key-rate, node and quote-space curve sensitivities.

    ``quote_delta`` is ``dPV/dq`` in PV units per one absolute quote-rate unit.
    ``quote_pv01`` scales that derivative by one basis point.
    """
    if bump <= 0:
        raise ValueError("bump must be positive")
    pricer = _pricer(instrument_or_pricer)
    pv = float(pricer(curve))
    keys = list(key_maturities or curve.times[curve.times > 0])
    kr = key_rate_dv01(pricer, curve, keys, bump=bump) if keys else pd.Series(dtype=float)

    node_delta: dict[float, float] = {}
    for maturity in curve.times[curve.times > 0]:
        up = pricer(_bump_zero_node(curve, float(maturity), bump))
        down = pricer(_bump_zero_node(curve, float(maturity), -bump))
        node_delta[float(maturity)] = (up - down) / (2.0 * bump)
    node = pd.Series(node_delta, name="dPV_dZero")

    quote_delta = pd.Series(dtype=float)
    quote_pv01 = pd.Series(dtype=float)
    if build_result is not None:
        jac = build_result.jacobian.reindex(index=node.index)
        if jac.isna().any().any():
            raise ValueError("curve node grid does not match build_result jacobian")
        q = node.to_numpy(dtype=float) @ jac.to_numpy(dtype=float)
        quote_delta = pd.Series(q, index=jac.columns, name="dPV_dQuote")
        quote_pv01 = (quote_delta * 1e-4).rename("quote_pv01")

    return CurveRiskResult(
        pv=pv,
        dv01=float(dv01(pricer, curve, bump=bump)),
        dollar_convexity=float(dollar_convexity(pricer, curve, bump=bump)),
        key_rate_dv01=kr,
        node_delta=node,
        quote_delta=quote_delta,
        quote_pv01=quote_pv01,
        metadata={"curve": curve.name, "bump": bump},
    )


__all__ = ["CurveRiskResult", "curve_risk"]
