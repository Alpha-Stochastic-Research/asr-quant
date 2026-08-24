"""Backtest and performance visualizations."""
from __future__ import annotations

import calendar
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..metrics import drawdown_series
from .base import finalize, monthly_return_table, new_axis


class PerformanceVisualizer:
    """Visualization methods that accept a BacktestResult."""

    def equity(self, result, benchmark: pd.Series | None = None, log_scale: bool = False):
        fig, ax = new_axis(title="Equity curve")
        result.equity.plot(ax=ax, label="Strategy")
        if benchmark is not None:
            b = result.spec.initial_capital * (1 + pd.Series(benchmark).reindex(result.equity.index).fillna(0)).cumprod()
            b.plot(ax=ax, label="Benchmark")
        ax.set_yscale("log" if log_scale else "linear")
        ax.legend()
        ax.set_ylabel("Equity")
        return finalize(fig)

    def drawdown(self, result):
        dd = drawdown_series(result.net_returns)
        fig, ax = new_axis(title="Underwater drawdown")
        ax.fill_between(dd.index, dd.to_numpy(), 0, alpha=0.5)
        ax.set_ylabel("Drawdown")
        return finalize(fig)

    def equity_drawdown(self, result):
        dd = drawdown_series(result.net_returns)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
        result.equity.plot(ax=ax1)
        ax1.set_title("Equity and drawdown")
        ax1.set_ylabel("Equity")
        ax2.fill_between(dd.index, dd.to_numpy(), 0, alpha=0.5)
        ax2.set_ylabel("Drawdown")
        for ax in (ax1, ax2):
            ax.grid(alpha=0.25)
        return finalize(fig)

    def rolling_metrics(self, result, window: int = 63):
        r = result.net_returns
        ann = result.spec.annualization
        rolling_return = r.rolling(window).mean() * ann
        rolling_vol = r.rolling(window).std(ddof=1) * np.sqrt(ann)
        rolling_sharpe = rolling_return / rolling_vol.replace(0, np.nan)
        downside = r.clip(upper=0).rolling(window).apply(lambda x: np.sqrt(np.mean(np.square(x))), raw=True) * np.sqrt(ann)
        rolling_sortino = rolling_return / downside.replace(0, np.nan)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        rolling_sharpe.plot(ax=ax1, label="Sharpe")
        rolling_sortino.plot(ax=ax1, label="Sortino")
        rolling_vol.plot(ax=ax2, label="Volatility")
        ax1.axhline(0, linewidth=0.8)
        ax1.legend()
        ax2.legend()
        ax1.set_title(f"Rolling {window}-bar diagnostics")
        for ax in (ax1, ax2):
            ax.grid(alpha=0.25)
        return finalize(fig)

    def monthly_heatmap(self, result):
        table = monthly_return_table(result.net_returns)
        fig, ax = plt.subplots(figsize=(11, max(3.5, 0.45 * len(table) + 1.5)))
        image = ax.imshow(table.fillna(0), aspect="auto")
        ax.set_xticks(range(12), [calendar.month_abbr[i] for i in range(1, 13)])
        ax.set_yticks(range(len(table)), table.index)
        for i in range(len(table)):
            for j in range(table.shape[1]):
                value = table.iloc[i, j]
                if pd.notna(value):
                    ax.text(j, i, f"{value:.1%}", ha="center", va="center", fontsize=8)
        ax.set_title("Monthly strategy returns")
        fig.colorbar(image, ax=ax, label="Return")
        return finalize(fig)

    def annual_returns(self, result):
        annual = (1 + result.net_returns).resample("YE").prod() - 1
        fig, ax = new_axis(title="Annual returns")
        ax.bar(annual.index.year.astype(str), annual.to_numpy())
        ax.axhline(0, linewidth=0.8)
        ax.set_ylabel("Return")
        return finalize(fig)

    def turnover(self, result, rolling: int | None = 21):
        data = result.turnover.rolling(rolling).mean() if rolling else result.turnover
        fig, ax = new_axis(title="Portfolio turnover")
        data.plot(ax=ax)
        ax.set_ylabel("Fraction of NAV traded")
        return finalize(fig)

    def costs(self, result, cumulative: bool = True):
        data = result.cost_breakdown.cumsum() if cumulative else result.cost_breakdown
        fig, ax = new_axis(title="Cumulative cost decomposition" if cumulative else "Cost decomposition")
        data.plot(ax=ax)
        ax.set_ylabel("Return drag")
        return finalize(fig)

    def exposures(self, result):
        gross = result.effective_weights.abs().sum(axis=1).rename("Gross")
        net = result.effective_weights.sum(axis=1).rename("Net")
        fig, ax = new_axis(title="Gross and net exposure")
        pd.concat([gross, net], axis=1).plot(ax=ax)
        ax.axhline(0, linewidth=0.8)
        return finalize(fig)

    def weights(self, result, area: bool = True):
        fig, ax = new_axis(title="Portfolio weights")
        result.effective_weights.plot.area(ax=ax, stacked=False, alpha=0.55) if area else result.effective_weights.plot(ax=ax)
        ax.axhline(0, linewidth=0.8)
        return finalize(fig)

    def return_contributions(self, result, cumulative: bool = True):
        contribution = result.effective_weights * result.asset_returns
        if cumulative:
            contribution = contribution.cumsum()
        fig, ax = new_axis(title="Cumulative asset contributions" if cumulative else "Asset contributions")
        contribution.plot(ax=ax)
        return finalize(fig)

    def benchmark(self, result, benchmark_returns: pd.Series):
        aligned = pd.concat([result.net_returns.rename("Strategy"), benchmark_returns.rename("Benchmark")], axis=1).dropna()
        cumulative = (1 + aligned).cumprod() - 1
        active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        cumulative.plot(ax=ax1)
        active.cumsum().plot(ax=ax2)
        ax1.set_title("Strategy versus benchmark")
        ax2.set_title("Cumulative active return")
        for ax in (ax1, ax2):
            ax.grid(alpha=0.25)
        return finalize(fig)

    def trade_pnl(self, result):
        changes = result.effective_weights.diff().fillna(result.effective_weights)
        event = changes.abs().sum(axis=1) > 0
        pnl = result.net_returns[event]
        fig, ax = new_axis(title="Returns on rebalance bars")
        ax.bar(pnl.index, pnl.to_numpy(), width=2)
        ax.axhline(0, linewidth=0.8)
        return finalize(fig)

    def dashboard(self, result):
        dd = drawdown_series(result.net_returns)
        fig = plt.figure(figsize=(14, 10))
        grid = fig.add_gridspec(3, 2)
        ax1 = fig.add_subplot(grid[0, :])
        ax2 = fig.add_subplot(grid[1, 0])
        ax3 = fig.add_subplot(grid[1, 1])
        ax4 = fig.add_subplot(grid[2, 0])
        ax5 = fig.add_subplot(grid[2, 1])
        result.equity.plot(ax=ax1)
        ax1.set_title("Equity")
        ax2.fill_between(dd.index, dd.to_numpy(), 0, alpha=0.5)
        ax2.set_title("Drawdown")
        result.net_returns.hist(ax=ax3, bins=40)
        ax3.set_title("Returns")
        result.turnover.rolling(21).mean().plot(ax=ax4)
        ax4.set_title("Rolling turnover")
        result.effective_weights.abs().sum(axis=1).plot(ax=ax5, label="Gross")
        result.effective_weights.sum(axis=1).plot(ax=ax5, label="Net")
        ax5.legend()
        ax5.set_title("Exposure")
        for ax in (ax1, ax2, ax3, ax4, ax5):
            ax.grid(alpha=0.2)
        fig.suptitle(result.spec.name)
        return finalize(fig)
