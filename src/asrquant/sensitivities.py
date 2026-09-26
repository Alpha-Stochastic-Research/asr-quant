"""Generic finite-difference sensitivity engine for scalar quantitative models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from .contracts import ResultMixin


@dataclass
class SensitivityResult(ResultMixin):
    base_value: float
    first_order: pd.Series
    second_order: pd.Series
    cross_greeks: pd.DataFrame
    error_estimate: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="sensitivities", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "base_value": self.base_value,
                "parameters": int(len(self.first_order)),
                "max_abs_first_order": float(self.first_order.abs().max()) if len(self.first_order) else 0.0,
                "max_error_estimate": float(self.error_estimate.abs().max()) if len(self.error_estimate) else 0.0,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.concat(
            {
                "first_order": self.first_order,
                "second_order": self.second_order,
                "error_estimate": self.error_estimate,
            }, axis=1
        )


def compute(
    pricing_function: Callable[..., float],
    parameters: Mapping[str, float],
    *,
    steps: Mapping[str, float] | None = None,
    relative_step: float = 1e-5,
    second_order: bool = True,
    cross: bool = False,
) -> SensitivityResult:
    """Central finite-difference first/second/cross sensitivities.

    The function is intentionally model-agnostic. ``pricing_function`` is called
    with keyword parameters and must return a scalar.
    """
    params = {str(k): float(v) for k, v in parameters.items()}
    if not params:
        raise ValueError("parameters must not be empty")
    if relative_step <= 0:
        raise ValueError("relative_step must be positive")
    step_map = {
        name: float((steps or {}).get(name, relative_step * max(1.0, abs(value))))
        for name, value in params.items()
    }
    if any(h <= 0 for h in step_map.values()):
        raise ValueError("all finite-difference steps must be positive")

    def value(p: Mapping[str, float]) -> float:
        out = float(pricing_function(**dict(p)))
        if not np.isfinite(out):
            raise ValueError("pricing_function returned a non-finite value")
        return out

    base = value(params)
    first: dict[str, float] = {}
    second: dict[str, float] = {}
    errors: dict[str, float] = {}
    for name, h in step_map.items():
        up, down = dict(params), dict(params)
        up[name] += h
        down[name] -= h
        f_up, f_down = value(up), value(down)
        d1 = (f_up - f_down) / (2.0 * h)
        first[name] = d1
        second[name] = (f_up - 2.0 * base + f_down) / (h * h) if second_order else np.nan
        # Richardson-style diagnostic using half step.
        hh = h / 2.0
        up2, down2 = dict(params), dict(params)
        up2[name] += hh
        down2[name] -= hh
        d_half = (value(up2) - value(down2)) / (2.0 * hh)
        errors[name] = abs(d_half - d1)

    cross_df = pd.DataFrame(index=params, columns=params, dtype=float)
    if cross:
        for a in params:
            cross_df.loc[a, a] = second[a]
        names = list(params)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                ha, hb = step_map[a], step_map[b]
                pp, pm, mp, mm = [dict(params) for _ in range(4)]
                pp[a] += ha; pp[b] += hb
                pm[a] += ha; pm[b] -= hb
                mp[a] -= ha; mp[b] += hb
                mm[a] -= ha; mm[b] -= hb
                value_cross = (value(pp) - value(pm) - value(mp) + value(mm)) / (4.0 * ha * hb)
                cross_df.loc[a, b] = cross_df.loc[b, a] = value_cross
    return SensitivityResult(
        base_value=base,
        first_order=pd.Series(first, name="first_order"),
        second_order=pd.Series(second, name="second_order"),
        cross_greeks=cross_df,
        error_estimate=pd.Series(errors, name="error_estimate"),
        metadata={"relative_step": relative_step, "steps": step_map, "cross": cross},
    )


__all__ = ["SensitivityResult", "compute"]
