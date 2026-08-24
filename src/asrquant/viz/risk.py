"""Tail-risk, stress, sensitivity, and implementation-audit plots."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..metrics import drawdown_series, expected_shortfall, value_at_risk
from .base import drawdown_periods, finalize, new_axis, to_series


def var_es_plot(returns, level: float = 0.95, bins: int = 60):
    r = to_series(returns)
    var = value_at_risk(r, level)
    es = expected_shortfall(r, level)
    fig, ax = new_axis(title=f"VaR and Expected Shortfall ({level:.0%})")
    ax.hist(r, bins=bins, alpha=0.6, density=True)
    ax.axvline(-var, linestyle="--", label=f"VaR = {var:.2%}")
    ax.axvline(-es, linestyle=":", label=f"ES = {es:.2%}")
    ax.legend()
    return finalize(fig)


def rolling_var_es(returns, window: int = 252, level: float = 0.95):
    r = to_series(returns)
    var = -r.rolling(window).quantile(1 - level)
    es = r.rolling(window).apply(lambda x: -np.mean(x[x <= np.quantile(x, 1 - level)]), raw=True)
    fig, ax = new_axis(title=f"Rolling {level:.0%} tail risk")
    var.plot(ax=ax, label="VaR")
    es.plot(ax=ax, label="ES")
    ax.legend()
    return finalize(fig)


def tail_plot(returns, threshold: float = 0.95):
    r = np.sort(to_series(returns).to_numpy())
    tail_n = max(2, int(len(r) * (1 - threshold)))
    losses = -r[:tail_n][::-1]
    ranks = np.arange(1, len(losses) + 1)
    fig, ax = new_axis(title="Empirical loss tail")
    ax.loglog(ranks, losses, marker="o", linestyle="none")
    ax.set_xlabel("Tail rank")
    ax.set_ylabel("Loss")
    return finalize(fig)


def drawdown_table_plot(returns, top: int = 10):
    periods = drawdown_periods(to_series(returns)).nsmallest(top, "depth")
    fig, ax = new_axis(title=f"Top {top} drawdowns")
    labels = [pd.Timestamp(x).strftime("%Y-%m-%d") for x in periods["trough"]]
    ax.barh(labels, periods["depth"])
    ax.set_xlabel("Drawdown")
    return finalize(fig)


def stress_plot(stress_results: pd.DataFrame, column: str = "total_return"):
    if column not in stress_results:
        raise ValueError(f"column {column!r} not found")
    fig, ax = new_axis(title=f"Stress scenarios: {column}")
    ax.bar(stress_results.index.astype(str), stress_results[column].to_numpy())
    ax.axhline(0, linewidth=0.8)
    ax.tick_params(axis="x", rotation=30)
    return finalize(fig)


def sensitivity_heatmap(results: pd.DataFrame, x: str, y: str, value: str):
    table = results.pivot_table(index=y, columns=x, values=value, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(table, aspect="auto")
    ax.set_xticks(range(len(table.columns)), table.columns)
    ax.set_yticks(range(len(table.index)), table.index)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"Sensitivity of {value}")
    for i in range(len(table)):
        for j in range(len(table.columns)):
            ax.text(j, i, f"{table.iloc[i, j]:.3g}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def monte_carlo_fan(paths: pd.DataFrame | np.ndarray, quantiles=(0.05, 0.25, 0.5, 0.75, 0.95), title: str = "Monte Carlo fan"):
    frame = pd.DataFrame(paths)
    q = frame.quantile(quantiles, axis=1).T
    fig, ax = new_axis(title=title)
    ax.fill_between(q.index, q[quantiles[0]], q[quantiles[-1]], alpha=0.2, label=f"{quantiles[0]:.0%}-{quantiles[-1]:.0%}")
    ax.fill_between(q.index, q[quantiles[1]], q[quantiles[-2]], alpha=0.35, label=f"{quantiles[1]:.0%}-{quantiles[-2]:.0%}")
    ax.plot(q.index, q[quantiles[2]], label="Median")
    ax.legend()
    return finalize(fig)


def implementation_audit_plot(summary: pd.DataFrame):
    required = ["Total Return", "Sharpe", "Max Drawdown"]
    columns = [c for c in required if c in summary]
    fig, axes = plt.subplots(len(columns), 1, figsize=(11, 3.2 * len(columns)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, column in zip(axes, columns):
        ax.bar(summary.index, summary[column])
        ax.set_ylabel(column)
        ax.grid(alpha=0.2)
    axes[-1].tick_params(axis="x", rotation=35)
    fig.suptitle("Implementation-contract sensitivity")
    return finalize(fig)


def rolling_drawdown(returns):
    dd = drawdown_series(to_series(returns))
    fig, ax = new_axis(title="Drawdown path")
    dd.plot(ax=ax)
    ax.fill_between(dd.index, dd.to_numpy(), 0, alpha=0.3)
    return finalize(fig)


def rolling_skew_kurtosis(returns, window: int = 126, title: str = "Rolling skewness and kurtosis"):
    s = pd.Series(returns, dtype=float).dropna()
    fig, ax = new_axis(title=title)
    s.rolling(window).skew().plot(ax=ax, label="Skewness")
    s.rolling(window).kurt().plot(ax=ax, label="Excess kurtosis")
    ax.axhline(0, linewidth=0.8)
    ax.legend()
    return finalize(fig)


def var_exceedances(returns, window: int = 252, level: float = 0.95, title: str = "VaR exceedances"):
    """Display rolling historical VaR and observations that breach it."""
    s = pd.Series(returns, dtype=float).dropna()
    var = -s.rolling(window).quantile(1 - level)
    losses = -s
    exceed = losses > var
    fig, ax = new_axis(title=title)
    ax.plot(losses.index, losses, alpha=0.55, label="Loss")
    ax.plot(var.index, var, label=f"Historical VaR {level:.0%}")
    ax.scatter(losses.index[exceed], losses[exceed], marker="x", label="Exceedance")
    ax.set_ylabel("Loss")
    ax.legend()
    return finalize(fig)


def drawdown_duration_plot(returns, title: str = "Drawdown duration"):
    """Plot the number of consecutive observations below the previous peak."""
    s = pd.Series(returns, dtype=float).dropna()
    wealth = (1 + s).cumprod()
    underwater = wealth < wealth.cummax()
    duration = pd.Series(0, index=s.index, dtype=float)
    count = 0
    for i, flag in enumerate(underwater):
        count = count + 1 if flag else 0
        duration.iloc[i] = count
    fig, ax = new_axis(title=title)
    duration.plot(ax=ax)
    ax.set_ylabel("Bars underwater")
    return finalize(fig)


def risk_return_scatter(returns: pd.DataFrame, annualization: int = 252, title: str = "Risk-return map"):
    """Compare annualized mean return and volatility across assets."""
    frame = pd.DataFrame(returns, dtype=float).dropna(how="all")
    mean = frame.mean() * annualization
    vol = frame.std(ddof=1) * np.sqrt(annualization)
    fig, ax = new_axis(title=title)
    ax.scatter(vol, mean)
    for name in frame.columns:
        ax.annotate(str(name), (vol[name], mean[name]))
    ax.set_xlabel("Annualized volatility")
    ax.set_ylabel("Annualized mean return")
    return finalize(fig)


def expected_shortfall_contributions(weights, returns: pd.DataFrame, level: float = 0.95, title: str = "Expected Shortfall contributions"):
    """Decompose average weighted asset losses in the portfolio tail."""
    frame = pd.DataFrame(returns, dtype=float).dropna()
    w = pd.Series(weights, index=frame.columns, dtype=float)
    portfolio = frame.mul(w, axis=1).sum(axis=1)
    threshold = portfolio.quantile(1 - level)
    tail = frame.loc[portfolio <= threshold].mul(w, axis=1)
    contribution = -tail.mean().sort_values()
    fig, ax = new_axis(title=title)
    ax.bar(contribution.index.astype(str), contribution.to_numpy())
    ax.set_ylabel("Mean tail loss contribution")
    ax.tick_params(axis="x", rotation=35)
    return finalize(fig)
