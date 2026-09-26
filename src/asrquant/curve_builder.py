"""Curve construction with explicit quote repricing and calibration diagnostics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from .contracts import CalibrationError, ResultMixin
from .interest_rates import DiscountCurve, bootstrap_discount_curve, no_arbitrage_curve_diagnostics


def _frame(value: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame(columns=columns)
    out = pd.DataFrame(value).copy()
    missing = [c for c in columns if c not in out]
    if missing:
        raise CalibrationError(f"quote table missing columns: {missing}")
    for c in columns:
        out[c] = pd.to_numeric(out[c], errors="raise")
    return out[columns].sort_values(columns[0]).reset_index(drop=True)


def _quote_table(deposits: pd.DataFrame, fras: pd.DataFrame, swaps: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for i, r in deposits.iterrows():
        rows.append({"label": f"DEP:{float(r.maturity):g}", "type": "deposit", "maturity": float(r.maturity), "rate": float(r.rate)})
    for i, r in fras.iterrows():
        rows.append({"label": f"FRA:{float(r.start):g}-{float(r.end):g}", "type": "fra", "start": float(r.start), "end": float(r.end), "rate": float(r.rate)})
    for i, r in swaps.iterrows():
        rows.append({"label": f"SWAP:{float(r.maturity):g}", "type": "swap", "maturity": float(r.maturity), "rate": float(r.rate)})
    return pd.DataFrame(rows).set_index("label") if rows else pd.DataFrame(columns=["type", "rate"])


def _zero_nodes(curve: DiscountCurve) -> pd.Series:
    times = curve.times[curve.times > 0]
    return pd.Series(np.asarray(curve.zero_rate(times), dtype=float), index=times, name="zero_rate")


def _reprice(curve: DiscountCurve, deposits: pd.DataFrame, fras: pd.DataFrame, swaps: pd.DataFrame, swap_frequency: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for r in deposits.itertuples(index=False):
        t, q = float(r.maturity), float(r.rate)
        implied = (1.0 / float(curve.df(t)) - 1.0) / t
        rows.append({"label": f"DEP:{t:g}", "type": "deposit", "market_quote": q, "model_quote": implied, "error": implied - q})
    for r in fras.itertuples(index=False):
        s, e, q = float(r.start), float(r.end), float(r.rate)
        implied = float(curve.forward_rate(s, e, "simple"))
        rows.append({"label": f"FRA:{s:g}-{e:g}", "type": "fra", "market_quote": q, "model_quote": implied, "error": implied - q})
    for r in swaps.itertuples(index=False):
        t, q = float(r.maturity), float(r.rate)
        implied = float(curve.par_swap_rate(0.0, t, swap_frequency))
        rows.append({"label": f"SWAP:{t:g}", "type": "swap", "market_quote": q, "model_quote": implied, "error": implied - q})
    return pd.DataFrame(rows).set_index("label") if rows else pd.DataFrame(columns=["type", "market_quote", "model_quote", "error"])


@dataclass
class CurveBuildResult(ResultMixin):
    curve: DiscountCurve
    quotes: pd.DataFrame
    repricing_errors: pd.DataFrame
    diagnostics: pd.Series
    jacobian: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="curve_build", init=False)

    @property
    def summary(self) -> pd.Series:
        errors = self.repricing_errors["error"].abs() if not self.repricing_errors.empty else pd.Series(dtype=float)
        return pd.Series(
            {
                "nodes": int(len(self.curve.times) - int(self.curve.times[0] == 0)),
                "quotes": int(len(self.quotes)),
                "max_abs_repricing_error": float(errors.max()) if len(errors) else 0.0,
                "mean_abs_repricing_error": float(errors.mean()) if len(errors) else 0.0,
                "positive_discount_factors": bool(np.all(self.curve.discounts > 0)),
                "jacobian_condition_number": float(np.linalg.cond(self.jacobian.to_numpy())) if self.jacobian.size else np.nan,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.curve.table()

    def validate(self, tolerance: float = 1e-10) -> pd.Series:
        max_error = float(self.summary["max_abs_repricing_error"])
        issues: list[str] = []
        if max_error > tolerance:
            issues.append(f"repricing error {max_error:.3e} exceeds tolerance {tolerance:.3e}")
        if not bool(self.summary["positive_discount_factors"]):
            issues.append("curve contains non-positive discount factors")
        return pd.Series({"passed": not issues, "issues": tuple(issues), "tolerance": tolerance})

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "summary": self.summary.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "repricing_errors": self.repricing_errors.to_dict(orient="index"),
            "metadata": dict(self.metadata),
        }


class CurveBuilder:
    """Bootstrap a transparent single curve and retain quote-space diagnostics."""

    def __init__(
        self,
        *,
        deposits: pd.DataFrame | None = None,
        fras: pd.DataFrame | None = None,
        swaps: pd.DataFrame | None = None,
        swap_frequency: int = 2,
        interpolation: str = "log_linear",
        name: str = "market_curve",
        jacobian_bump: float = 1e-6,
        valuation_date: str | pd.Timestamp | None = None,
        grid_policy: str = "interpolate",
    ) -> None:
        self.deposits = _frame(deposits, ["maturity", "rate"])
        self.fras = _frame(fras, ["start", "end", "rate"])
        self.swaps = _frame(swaps, ["maturity", "rate"])
        self.swap_frequency = int(swap_frequency)
        self.interpolation = interpolation
        self.name = name
        self.jacobian_bump = float(jacobian_bump)
        self.valuation_date = pd.Timestamp(valuation_date) if valuation_date is not None else None
        self.grid_policy = str(grid_policy).lower().replace("-", "_")
        if self.grid_policy not in {"interpolate", "strict"}:
            raise CalibrationError("grid_policy must be 'interpolate' or 'strict'")
        if self.swap_frequency <= 0 or self.jacobian_bump <= 0:
            raise CalibrationError("swap_frequency and jacobian_bump must be positive")
        if self.deposits.empty and self.fras.empty and self.swaps.empty:
            raise CalibrationError("provide at least one market quote")

    @classmethod
    def from_quotes(
        cls,
        quotes: pd.DataFrame | None = None,
        *,
        deposits: Mapping[float, float] | pd.DataFrame | None = None,
        fras: Sequence[tuple[float, float, float]] | pd.DataFrame | None = None,
        swaps: Mapping[float, float] | pd.DataFrame | None = None,
        **kwargs: Any,
    ) -> "CurveBuilder":
        """Construct a builder from a quote table or compact quote mappings.

        ``quotes`` uses columns ``type``/``rate`` plus ``maturity`` for deposits
        and swaps or ``start``/``end`` for FRAs.  Alternatively, deposits and
        swaps can be supplied as ``{maturity: rate}`` mappings and FRAs as
        ``(start, end, rate)`` tuples.
        """
        if quotes is not None and any(value is not None for value in (deposits, fras, swaps)):
            raise CalibrationError("use either quotes table or deposits/fras/swaps, not both")
        if quotes is not None:
            frame = pd.DataFrame(quotes).copy()
            if "type" not in frame or "rate" not in frame:
                raise CalibrationError("quotes require type and rate columns")
            kind = frame["type"].astype(str).str.lower()
            deposits = frame.loc[kind == "deposit", ["maturity", "rate"]] if (kind == "deposit").any() else None
            fras = frame.loc[kind == "fra", ["start", "end", "rate"]] if (kind == "fra").any() else None
            swaps = frame.loc[kind == "swap", ["maturity", "rate"]] if (kind == "swap").any() else None
        else:
            if isinstance(deposits, Mapping):
                deposits = pd.DataFrame({"maturity": list(deposits.keys()), "rate": list(deposits.values())})
            if isinstance(swaps, Mapping):
                swaps = pd.DataFrame({"maturity": list(swaps.keys()), "rate": list(swaps.values())})
            if fras is not None and not isinstance(fras, pd.DataFrame):
                fras = pd.DataFrame(list(fras), columns=["start", "end", "rate"])
        return cls(deposits=deposits, fras=fras, swaps=swaps, **kwargs)

    def _expanded_swaps(
        self, deposits: pd.DataFrame, fras: pd.DataFrame, swaps: pd.DataFrame
    ) -> tuple[pd.DataFrame, tuple[float, ...]]:
        if swaps.empty or self.grid_policy == "strict":
            return swaps.copy(), ()
        alpha = 1.0 / self.swap_frequency
        known = set(float(x) for x in deposits.get("maturity", pd.Series(dtype=float)))
        known.update(float(x) for x in fras.get("end", pd.Series(dtype=float)))
        market_maturities = swaps["maturity"].to_numpy(dtype=float)
        market_rates = swaps["rate"].to_numpy(dtype=float)
        max_maturity = float(market_maturities.max())
        grid = np.arange(alpha, max_maturity + alpha * 0.25, alpha)
        existing = set(float(x) for x in market_maturities)
        synthetic: list[dict[str, float]] = []
        for maturity in grid:
            maturity = float(round(maturity, 12))
            if maturity in known or maturity in existing:
                continue
            if maturity >= max_maturity:
                continue
            rate = float(np.interp(maturity, market_maturities, market_rates))
            synthetic.append({"maturity": maturity, "rate": rate})
        if not synthetic:
            return swaps.copy(), ()
        expanded = pd.concat([swaps, pd.DataFrame(synthetic)], ignore_index=True)
        expanded = expanded.sort_values("maturity").reset_index(drop=True)
        return expanded, tuple(row["maturity"] for row in synthetic)

    def _build_raw(self, deposits: pd.DataFrame, fras: pd.DataFrame, swaps: pd.DataFrame) -> DiscountCurve:
        expanded_swaps, _ = self._expanded_swaps(deposits, fras, swaps)
        try:
            return bootstrap_discount_curve(
                deposits=deposits if not deposits.empty else None,
                fras=fras if not fras.empty else None,
                swaps=expanded_swaps if not expanded_swaps.empty else None,
                swap_frequency=self.swap_frequency,
                interpolation=self.interpolation,
                name=self.name,
            )
        except Exception as exc:
            raise CalibrationError(str(exc)) from exc

    def _jacobian(self, base: DiscountCurve) -> pd.DataFrame:
        base_z = _zero_nodes(base)
        quote_specs: list[tuple[str, str, int]] = []
        quote_specs.extend((f"DEP:{float(r.maturity):g}", "deposit", i) for i, r in self.deposits.iterrows())
        quote_specs.extend((f"FRA:{float(r.start):g}-{float(r.end):g}", "fra", i) for i, r in self.fras.iterrows())
        quote_specs.extend((f"SWAP:{float(r.maturity):g}", "swap", i) for i, r in self.swaps.iterrows())
        columns: dict[str, pd.Series] = {}
        for label, kind, idx in quote_specs:
            dep, fra, swp = self.deposits.copy(), self.fras.copy(), self.swaps.copy()
            target = {"deposit": dep, "fra": fra, "swap": swp}[kind]
            target.loc[idx, "rate"] = float(target.loc[idx, "rate"]) + self.jacobian_bump
            bumped = self._build_raw(dep, fra, swp)
            bumped_z = _zero_nodes(bumped).reindex(base_z.index)
            if bumped_z.isna().any():
                raise CalibrationError("quote bump changed curve node structure")
            columns[label] = (bumped_z - base_z) / self.jacobian_bump
        jac = pd.DataFrame(columns, index=base_z.index)
        jac.index.name = "zero_maturity"
        return jac

    def build(self) -> CurveBuildResult:
        curve = self._build_raw(self.deposits, self.fras, self.swaps)
        repricing = _reprice(curve, self.deposits, self.fras, self.swaps, self.swap_frequency)
        diagnostics = pd.Series(no_arbitrage_curve_diagnostics(curve))
        jac = self._jacobian(curve)
        quotes = _quote_table(self.deposits, self.fras, self.swaps)
        _, synthetic_grid = self._expanded_swaps(self.deposits, self.fras, self.swaps)
        result = CurveBuildResult(
            curve=curve,
            quotes=quotes,
            repricing_errors=repricing,
            diagnostics=diagnostics,
            jacobian=jac,
            metadata={
                "swap_frequency": self.swap_frequency,
                "interpolation": self.interpolation,
                "jacobian_bump": self.jacobian_bump,
                "curve_name": self.name,
                "valuation_date": self.valuation_date.isoformat() if self.valuation_date is not None else None,
                "grid_policy": self.grid_policy,
                "synthetic_coupon_nodes": synthetic_grid,
            },
        )
        validation = result.validate()
        if not bool(validation["passed"]):
            raise CalibrationError("; ".join(validation["issues"]))
        return result


__all__ = ["CurveBuilder", "CurveBuildResult"]
