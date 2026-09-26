"""Cross-domain diagnostics that explain fragile quantitative results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .contracts import ResultMixin


_LEVEL_ORDER = {"INFO": 0, "WARNING": 1, "FAIL": 2}


@dataclass
class DiagnosticReport(ResultMixin):
    findings: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="diagnostics", init=False)

    @property
    def status(self) -> str:
        if self.findings.empty:
            return "PASS"
        levels = self.findings["level"].map(_LEVEL_ORDER).fillna(0)
        maximum = int(levels.max())
        return {0: "PASS", 1: "WARNING", 2: "FAIL"}[maximum]

    @property
    def summary(self) -> pd.Series:
        counts = self.findings["level"].value_counts() if not self.findings.empty else pd.Series(dtype=int)
        return pd.Series(
            {
                "status": self.status,
                "findings": int(len(self.findings)),
                "failures": int(counts.get("FAIL", 0)),
                "warnings": int(counts.get("WARNING", 0)),
                "info": int(counts.get("INFO", 0)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.findings.copy()


def explain(result: Any) -> DiagnosticReport:
    """Return conservative diagnostics for common ASRQuant result objects."""
    findings: list[dict[str, str]] = []

    def add(level: str, code: str, message: str) -> None:
        findings.append({"level": level, "code": code, "message": message})

    name = type(result).__name__

    # Curve construction.
    if hasattr(result, "repricing_errors") and hasattr(result, "jacobian"):
        errors = pd.DataFrame(result.repricing_errors)
        max_error = float(errors["error"].abs().max()) if "error" in errors and len(errors) else 0.0
        if max_error > 1e-8:
            add("FAIL", "CURVE_REPRICING", f"maximum quote repricing error is {max_error:.3e}")
        else:
            add("INFO", "CURVE_REPRICING", f"quotes reprice within {max_error:.3e}")
        jac = pd.DataFrame(result.jacobian)
        if jac.size:
            cond = float(np.linalg.cond(jac.to_numpy(dtype=float)))
            if not np.isfinite(cond) or cond > 1e10:
                add("WARNING", "CURVE_CONDITION", f"quote-to-zero Jacobian is ill-conditioned ({cond:.3e})")

    # Portfolio optimization.
    if hasattr(result, "weights") and hasattr(result, "volatility"):
        w = pd.Series(result.weights, dtype=float)
        gross = float(w.abs().sum())
        max_weight = float(w.abs().max()) if len(w) else 0.0
        hhi = float(np.sum(np.square(w / gross))) if gross > 0 else np.nan
        if max_weight > 0.40:
            add("WARNING", "PORTFOLIO_CONCENTRATION", f"largest absolute weight is {max_weight:.1%}")
        if np.isfinite(hhi) and hhi > 0.25:
            add("WARNING", "PORTFOLIO_HHI", f"weight concentration HHI is {hhi:.3f}")
        if float(result.volatility) <= 1e-12:
            add("FAIL", "PORTFOLIO_ZERO_RISK", "portfolio volatility is numerically zero")

    # Backtests.
    if hasattr(result, "net_returns") and hasattr(result, "gross_returns") and hasattr(result, "turnover"):
        net = pd.Series(result.net_returns, dtype=float).dropna()
        gross = pd.Series(result.gross_returns, dtype=float).reindex(net.index).fillna(0.0)
        costs = gross - net
        avg_turnover = float(pd.Series(result.turnover, dtype=float).mean())
        if avg_turnover > 1.0:
            add("WARNING", "HIGH_TURNOVER", f"average one-period turnover is {avg_turnover:.2f}")
        if len(net):
            total_abs = float(net.abs().sum())
            top = int(max(1, np.ceil(0.1 * len(net))))
            concentration = float(net.abs().nlargest(top).sum() / total_abs) if total_abs > 0 else 0.0
            if concentration > 0.60:
                add("WARNING", "PNL_CONCENTRATION", f"top 10% of periods contribute {concentration:.1%} of absolute P&L")
        cost_drag = float(costs.sum())
        if cost_drag > 0:
            add("INFO", "COST_DRAG", f"aggregate gross-to-net return drag is {cost_drag:.4f}")

    # Generic calibration.
    if hasattr(result, "condition_number") and hasattr(result, "identifiability"):
        cond = float(result.condition_number)
        ident = str(result.identifiability)
        if ident in {"VERY_WEAK", "UNIDENTIFIED"}:
            add("FAIL", "IDENTIFIABILITY", f"calibration identifiability is {ident} (condition {cond:.3e})")
        elif ident == "WEAK":
            add("WARNING", "IDENTIFIABILITY", f"calibration identifiability is {ident} (condition {cond:.3e})")

    # Leakage and validation objects.
    if hasattr(result, "issues") and "Leakage" in name:
        for issue in tuple(result.issues):
            add("FAIL", "LEAKAGE", str(issue))
    if hasattr(result, "probability") and "PBO" in name:
        pbo = float(result.probability)
        if pbo >= 0.50:
            add("FAIL", "PBO", f"estimated probability of backtest overfitting is {pbo:.1%}")
        elif pbo >= 0.25:
            add("WARNING", "PBO", f"estimated probability of backtest overfitting is {pbo:.1%}")
        else:
            add("INFO", "PBO", f"estimated probability of backtest overfitting is {pbo:.1%}")

    if not findings:
        add("INFO", "NO_SPECIALIZED_RULE", f"no specialized diagnostic rule for {name}; inspect the native result summary")
    frame = pd.DataFrame(findings)
    return DiagnosticReport(frame, metadata={"result_type": name})


__all__ = ["DiagnosticReport", "explain"]
