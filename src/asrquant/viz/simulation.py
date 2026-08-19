"""Stochastic-process and martingale diagnostic visualizations."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from .base import finalize, new_axis


def paths(simulation, max_paths: int = 50, title: str | None = None):
    frame = simulation.paths if hasattr(simulation, "paths") else pd.DataFrame(simulation)
    fig, ax = new_axis(title=title or "Monte Carlo paths")
    frame.iloc[:, :max_paths].plot(ax=ax, legend=False, alpha=0.35)
    ax.set_xlabel("Time")
    ax.set_ylabel("State")
    return finalize(fig)


def terminal_distribution(simulation, bins: int = 50, title: str = "Terminal distribution"):
    terminal = simulation.terminal if hasattr(simulation, "terminal") else pd.Series(pd.DataFrame(simulation).iloc[-1])
    fig, ax = new_axis(title=title)
    ax.hist(pd.Series(terminal).dropna(), bins=bins, density=True, alpha=0.65)
    ax.axvline(np.mean(terminal), linestyle="--", label="Mean")
    ax.axvline(np.median(terminal), linestyle=":", label="Median")
    ax.legend()
    return finalize(fig)


def martingale_diagnostics_plot(result):
    increments = result.increments
    fitted = pd.Series(result.regression.fittedvalues, index=increments.index)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    axes[0, 0].plot(increments.index, increments)
    axes[0, 0].axhline(0, linewidth=0.8)
    axes[0, 0].set_title("Discounted increments")
    axes[0, 1].hist(increments, bins=35, density=True, alpha=0.65)
    x = np.linspace(increments.min(), increments.max(), 250)
    axes[0, 1].plot(x, stats.norm.pdf(x, increments.mean(), increments.std(ddof=1)))
    axes[0, 1].set_title("Increment distribution")
    axes[1, 0].scatter(result.regression.model.exog[:, -1], increments, alpha=0.45)
    axes[1, 0].set_xlabel("Lagged level")
    axes[1, 0].set_ylabel("Next increment")
    axes[1, 0].set_title("Conditional-mean diagnostic")
    axes[1, 1].plot(fitted.index, fitted, label="Fitted predictable component")
    axes[1, 1].axhline(0, linewidth=0.8)
    axes[1, 1].legend()
    axes[1, 1].set_title("Estimated predictable component")
    for ax in axes.ravel():
        ax.grid(alpha=0.2)
    fig.suptitle("Martingale diagnostics (non-rejection is not proof)")
    return finalize(fig)


def quantile_bands(simulation, quantiles=(0.05, 0.25, 0.5, 0.75, 0.95), title: str = "Simulation quantile bands"):
    frame = simulation.paths if hasattr(simulation, "paths") else pd.DataFrame(simulation)
    values = frame.quantile(list(quantiles), axis=1).T
    fig, ax = new_axis(title=title)
    if len(quantiles) >= 5:
        ax.fill_between(values.index, values.iloc[:, 0], values.iloc[:, -1], alpha=0.15, label="Outer band")
        ax.fill_between(values.index, values.iloc[:, 1], values.iloc[:, -2], alpha=0.25, label="Inner band")
        ax.plot(values.index, values.iloc[:, len(quantiles) // 2], label="Median")
    else:
        values.plot(ax=ax)
    ax.set_xlabel("Time")
    ax.set_ylabel("State")
    ax.legend()
    return finalize(fig)


def increment_diagnostics(simulation, path: int = 0, title: str = "Simulation increment diagnostics"):
    frame = simulation.paths if hasattr(simulation, "paths") else pd.DataFrame(simulation)
    if not 0 <= path < frame.shape[1]:
        raise ValueError("path index is out of range")
    increments = frame.iloc[:, path].diff().dropna()
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    axes[0, 0].plot(increments.index, increments)
    axes[0, 0].set_title("Increments")
    axes[0, 1].hist(increments, bins=35, density=True, alpha=0.65)
    axes[0, 1].set_title("Increment distribution")
    stats.probplot(increments, plot=axes[1, 0])
    axes[1, 0].set_title("Increment Q-Q")
    axes[1, 1].scatter(increments.shift(1), increments, alpha=0.4)
    axes[1, 1].set_xlabel("Lagged increment")
    axes[1, 1].set_ylabel("Increment")
    axes[1, 1].set_title("Lag dependence")
    fig.suptitle(title)
    for ax in axes.ravel():
        ax.grid(alpha=0.2)
    return finalize(fig)


def first_passage_distribution(simulation, barrier: float, direction: str = "above", title: str = "First-passage distribution"):
    frame = simulation.paths if hasattr(simulation, "paths") else pd.DataFrame(simulation)
    if direction == "above":
        crossed = frame >= barrier
    elif direction == "below":
        crossed = frame <= barrier
    else:
        raise ValueError("direction must be above or below")
    times = []
    for column in crossed:
        mask = crossed[column]
        if mask.any():
            times.append(frame.index[np.argmax(mask.to_numpy())])
    fig, ax = new_axis(title=title)
    if times:
        ax.hist(np.asarray(times, dtype=float), bins=min(40, max(5, int(np.sqrt(len(times))))), alpha=0.65)
    ax.set_xlabel("First-passage time")
    ax.set_ylabel("Path count")
    return finalize(fig)


def convergence_diagnostics(estimates, reference: float | None = None, title: str = "Estimator convergence"):
    values = pd.Series(estimates, dtype=float).dropna()
    cumulative = values.expanding().mean()
    se = values.expanding().std(ddof=1) / np.sqrt(np.arange(1, len(values) + 1))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax1.plot(cumulative.index, cumulative, label="Cumulative mean")
    ax1.fill_between(cumulative.index, cumulative - 1.96 * se, cumulative + 1.96 * se, alpha=0.2)
    if reference is not None:
        ax1.axhline(reference, linestyle="--", label="Reference")
        ax2.plot(cumulative.index, cumulative - reference)
        ax2.axhline(0, linewidth=0.8)
        ax2.set_ylabel("Estimation error")
    else:
        ax2.plot(se.index, se)
        ax2.set_ylabel("Standard error")
    ax1.set_title(title)
    ax1.legend()
    ax2.set_xlabel("Samples")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.2)
    return finalize(fig)
