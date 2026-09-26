"""Implementation-risk audits across alternative backtest contracts."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

import numpy as np
import pandas as pd

from .backtest import BacktestResult, run_backtest
from .config import BacktestSpec, CostModel


@dataclass
class AuditResult:
    """Backtests and cross-contract dispersion diagnostics."""

    summary: pd.DataFrame
    diagnostics: pd.Series
    results: dict[str, BacktestResult]

    def plot(self):
        from .viz.risk import implementation_audit_plot

        return implementation_audit_plot(self.summary)


def implementation_audit(
    prices: pd.Series | pd.DataFrame,
    target_weights: pd.Series | pd.DataFrame,
    base_spec: BacktestSpec | None = None,
    execution_delays: Iterable[int] = (0, 1),
    linear_costs_bps: Iterable[float] = (0.0, 5.0, 10.0),
    rebalances: Iterable[str] = ("bar",),
) -> AuditResult:
    """Re-run one logical strategy under a grid of defensible conventions."""
    base_spec = base_spec or BacktestSpec()
    rows: list[pd.Series] = []
    results: dict[str, BacktestResult] = {}
    for delay, cost_bps, rebalance in product(execution_delays, linear_costs_bps, rebalances):
        base_costs = base_spec.costs
        costs = CostModel(
            commission_bps=float(cost_bps),
            spread_bps=base_costs.spread_bps,
            slippage_bps=base_costs.slippage_bps,
            borrow_bps_annual=base_costs.borrow_bps_annual,
            impact_coefficient=base_costs.impact_coefficient,
            impact_exponent=base_costs.impact_exponent,
        )
        spec = base_spec.with_updates(execution_delay=int(delay), rebalance=rebalance, costs=costs)
        result = run_backtest(prices, target_weights, spec)
        label = f"delay={delay}|cost={cost_bps:g}bps|rebalance={rebalance}"
        metric_row = result.metrics.rename(label)
        rows.append(metric_row)
        results[label] = result
    summary = pd.DataFrame(rows)
    selected = [c for c in ["Total Return", "CAGR", "Sharpe", "Max Drawdown"] if c in summary]
    ranges = summary[selected].max() - summary[selected].min()
    signs = np.sign(summary["Total Return"].to_numpy()) if "Total Return" in summary else np.array([])
    diagnostics = pd.Series(
        {
            "n_contracts": len(summary),
            "return_interval_low": summary["Total Return"].min(),
            "return_interval_high": summary["Total Return"].max(),
            "return_engine_sensitivity": ranges.get("Total Return", np.nan),
            "sharpe_engine_sensitivity": ranges.get("Sharpe", np.nan),
            "drawdown_engine_sensitivity": ranges.get("Max Drawdown", np.nan),
            "conclusion_stability_index": float(abs(signs.mean())) if len(signs) else np.nan,
        }
    )
    return AuditResult(summary=summary, diagnostics=diagnostics, results=results)
