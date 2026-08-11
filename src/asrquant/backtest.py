"""Auditable vectorized portfolio backtesting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import BacktestSpec
from .data import align_like, clean_prices, data_fingerprint, simple_returns
from .metrics import summary_metrics


def _rebalance_targets(weights: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "bar":
        return weights
    sampled = weights.resample(rule).last()
    return sampled.reindex(weights.index).ffill().fillna(0.0)


def _enforce_constraints(weights: pd.DataFrame, spec: BacktestSpec) -> pd.DataFrame:
    out = weights.copy()
    if spec.long_only:
        out = out.clip(lower=0.0)
    out = out.clip(lower=-spec.max_abs_weight, upper=spec.max_abs_weight)
    gross = out.abs().sum(axis=1)
    scale = (spec.max_gross_leverage / gross).clip(upper=1.0).fillna(1.0)
    return out.mul(scale, axis=0)


@dataclass
class BacktestResult:
    """All outputs required for analysis, audit, visualization, and export."""

    prices: pd.DataFrame
    asset_returns: pd.DataFrame
    target_weights: pd.DataFrame
    effective_weights: pd.DataFrame
    gross_returns: pd.Series
    net_returns: pd.Series
    equity: pd.Series
    turnover: pd.Series
    costs: pd.Series
    cost_breakdown: pd.DataFrame
    spec: BacktestSpec
    metadata: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        return str(self.metadata["experiment_fingerprint"])


    @property
    def trades(self) -> pd.DataFrame:
        """Return an auditable target-weight change ledger."""
        changes = self.effective_weights.diff().fillna(self.effective_weights)
        records = []
        for timestamp, row in changes.iterrows():
            for asset, change in row.items():
                if abs(change) > 1e-15:
                    records.append({
                        "timestamp": timestamp,
                        "asset": asset,
                        "weight_change": float(change),
                        "direction": "buy" if change > 0 else "sell",
                        "price": float(self.prices.loc[timestamp, asset]),
                        "target_weight": float(self.effective_weights.loc[timestamp, asset]),
                    })
        if not records:
            return pd.DataFrame(columns=["asset", "weight_change", "direction", "price", "target_weight"]).rename_axis("timestamp")
        return pd.DataFrame(records).set_index("timestamp")

    @property
    def metrics(self) -> pd.Series:
        return summary_metrics(
            self.net_returns,
            annualization=self.spec.annualization,
            risk_free_rate=self.spec.risk_free_rate,
            turnover=self.turnover,
        )

    def compare(self, benchmark_returns: pd.Series) -> pd.Series:
        return summary_metrics(
            self.net_returns,
            annualization=self.spec.annualization,
            risk_free_rate=self.spec.risk_free_rate,
            benchmark=benchmark_returns,
            turnover=self.turnover,
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.concat(
            {
                "gross_return": self.gross_returns,
                "net_return": self.net_returns,
                "equity": self.equity,
                "turnover": self.turnover,
                "cost": self.costs,
            },
            axis=1,
        )

    def report(self, output: str | None = None, title: str | None = None) -> str:
        from .report import create_html_report

        return create_html_report(self, output=output, title=title)

    def plot(self, kind: str = "dashboard", **kwargs: Any):
        from .viz.performance import PerformanceVisualizer

        viz = PerformanceVisualizer()
        if kind == "dashboard":
            return viz.dashboard(self, **kwargs)
        if not hasattr(viz, kind):
            raise ValueError(f"unknown plot kind: {kind}")
        return getattr(viz, kind)(self, **kwargs)


def run_backtest(
    prices: pd.Series | pd.DataFrame,
    target_weights: pd.Series | pd.DataFrame,
    spec: BacktestSpec | None = None,
) -> BacktestResult:
    """Run a deterministic weight-based backtest under an explicit contract."""
    spec = spec or BacktestSpec()
    spec.validate()
    price_frame = clean_prices(prices, spec.missing_data)
    weights = align_like(target_weights, price_frame, fill_value=0.0)
    weights = _rebalance_targets(weights, spec.rebalance)
    weights = _enforce_constraints(weights, spec)
    effective = weights.shift(spec.execution_delay).fillna(0.0)

    returns = simple_returns(price_frame)
    gross_returns = (effective * returns).sum(axis=1)

    previous = effective.shift(1).fillna(0.0)
    traded = (effective - previous).abs()
    turnover = traded.sum(axis=1)
    linear_cost = turnover * spec.costs.linear_bps / 10_000.0
    impact_cost = spec.costs.impact_coefficient * np.power(turnover, spec.costs.impact_exponent)
    short_exposure = (-effective.clip(upper=0.0)).sum(axis=1)
    borrow_cost = short_exposure * spec.costs.borrow_bps_annual / 10_000.0 / spec.annualization
    total_cost = linear_cost + impact_cost + borrow_cost

    cash_weight = 1.0 - effective.sum(axis=1)
    cash_return = cash_weight * spec.risk_free_rate / spec.annualization
    net_returns = gross_returns + cash_return - total_cost
    equity = spec.initial_capital * (1.0 + net_returns).cumprod()

    contract_flags = {
        "same_bar_execution_risk": spec.execution_delay == 0,
        "costs_enabled": bool(spec.costs.linear_bps or spec.costs.impact_coefficient or spec.costs.borrow_bps_annual),
        "shorting_enabled": not spec.long_only,
    }
    experiment_payload = f"{data_fingerprint(price_frame)}:{spec.fingerprint()}"
    metadata = {
        "data_fingerprint": data_fingerprint(price_frame),
        "spec_fingerprint": spec.fingerprint(),
        "experiment_fingerprint": experiment_payload,
        "contract_flags": contract_flags,
        "n_observations": len(price_frame),
        "n_assets": price_frame.shape[1],
    }
    cost_breakdown = pd.DataFrame(
        {
            "linear": linear_cost,
            "impact": impact_cost,
            "borrow": borrow_cost,
            "total": total_cost,
        },
        index=price_frame.index,
    )
    return BacktestResult(
        prices=price_frame,
        asset_returns=returns,
        target_weights=weights,
        effective_weights=effective,
        gross_returns=gross_returns.rename("gross_return"),
        net_returns=net_returns.rename("net_return"),
        equity=equity.rename("equity"),
        turnover=turnover.rename("turnover"),
        costs=total_cost.rename("cost"),
        cost_breakdown=cost_breakdown,
        spec=spec,
        metadata=metadata,
    )


def compare_backtests(results: dict[str, BacktestResult]) -> pd.DataFrame:
    """Compare any number of backtests on a common metric table."""
    if not results:
        raise ValueError("at least one result is required")
    return pd.DataFrame({name: result.metrics for name, result in results.items()}).T
