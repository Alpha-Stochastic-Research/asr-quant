"""Portfolio allocation, frontier, dependence, and risk-contribution plots."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..optimization import random_frontier, risk_contributions
from .base import finalize, new_axis


def efficient_frontier(expected_returns, covariance, n_portfolios: int = 5_000, risk_free_rate: float = 0.0):
    cloud = random_frontier(expected_returns, covariance, n_portfolios, risk_free_rate)
    fig, ax = new_axis(title="Monte Carlo efficient-frontier cloud")
    scatter = ax.scatter(cloud["volatility"], cloud["return"], c=cloud["sharpe"], s=8, alpha=0.55)
    best = cloud.loc[cloud["sharpe"].idxmax()]
    ax.scatter(best["volatility"], best["return"], marker="*", s=180, label="Maximum Sharpe")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Expected return")
    ax.legend()
    fig.colorbar(scatter, ax=ax, label="Sharpe")
    return finalize(fig)


def allocation_pie(weights, labels=None, title: str = "Portfolio allocation"):
    w = np.asarray(weights, dtype=float)
    labels = labels or [f"Asset {i+1}" for i in range(len(w))]
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(np.abs(w), labels=labels, autopct="%1.1f%%")
    ax.set_title(title)
    return finalize(fig)


def risk_contribution_plot(weights, covariance, labels=None):
    rc = risk_contributions(np.asarray(weights), np.asarray(covariance))
    labels = labels or [f"Asset {i+1}" for i in range(len(rc))]
    fig, ax = new_axis(title="Risk contributions")
    ax.bar(labels, rc)
    ax.tick_params(axis="x", rotation=30)
    return finalize(fig)


def correlation_network(returns: pd.DataFrame, threshold: float = 0.5):
    """Simple circular network with edges above an absolute-correlation threshold."""
    corr = pd.DataFrame(returns).corr()
    n = len(corr)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = np.c_[np.cos(angles), np.sin(angles)]
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(pos[:, 0], pos[:, 1], s=280)
    for i, name in enumerate(corr.columns):
        ax.text(pos[i, 0], pos[i, 1], str(name), ha="center", va="center")
    for i in range(n):
        for j in range(i + 1, n):
            value = corr.iloc[i, j]
            if abs(value) >= threshold:
                ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]], alpha=min(1, abs(value)), linewidth=1 + 3 * abs(value))
    ax.set_title(f"Correlation network |rho| >= {threshold}")
    ax.axis("off")
    return finalize(fig)


def weights_heatmap(weights: pd.DataFrame, title: str = "Weights through time"):
    data = pd.DataFrame(weights, dtype=float)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.4 * len(data.columns) + 2)))
    image = ax.imshow(data.T, aspect="auto")
    ax.set_yticks(range(len(data.columns)), data.columns)
    tick_idx = np.linspace(0, len(data) - 1, min(8, len(data))).astype(int)
    ax.set_xticks(tick_idx, [str(data.index[i])[:10] for i in tick_idx], rotation=30)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="Weight")
    return finalize(fig)


def covariance_heatmap(covariance, title: str = "Covariance matrix"):
    cov = pd.DataFrame(covariance, dtype=float)
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(cov, aspect="auto")
    ax.set_xticks(range(len(cov.columns)), cov.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(cov.index)), cov.index)
    ax.set_title(title)
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def correlation_dendrogram(returns: pd.DataFrame, method: str = "single", title: str = "Correlation dendrogram"):
    """Cluster assets by correlation distance."""
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import squareform

    frame = pd.DataFrame(returns, dtype=float).dropna()
    distance = np.sqrt(np.clip((1 - frame.corr()) / 2, 0, 1))
    condensed = squareform(distance.to_numpy(), checks=False)
    links = linkage(condensed, method=method)
    fig, ax = new_axis(figsize=(10, 6), title=title)
    dendrogram(links, labels=list(frame.columns), ax=ax)
    ax.set_ylabel("Distance")
    return finalize(fig)


def concentration_curve(weights, title: str = "Portfolio concentration curve"):
    """Plot cumulative absolute weight against the number of holdings."""
    w = pd.Series(weights, dtype=float).abs().sort_values(ascending=False)
    cumulative = w.cumsum() / max(float(w.sum()), 1e-12)
    fig, ax = new_axis(title=title)
    ax.plot(np.arange(1, len(w) + 1), cumulative, marker="o")
    ax.plot([1, len(w)], [1 / len(w), 1], linestyle="--", label="Equal weight")
    ax.set_xlabel("Number of largest positions")
    ax.set_ylabel("Cumulative absolute weight")
    ax.legend()
    return finalize(fig)


def rolling_risk_contributions(weights: pd.DataFrame, covariance, title: str = "Risk contributions through time"):
    """Plot total risk contributions for time-varying weights and one covariance matrix."""
    w = pd.DataFrame(weights, dtype=float)
    cov = pd.DataFrame(covariance, index=w.columns, columns=w.columns, dtype=float)
    rows = []
    for _, row in w.iterrows():
        vector = row.to_numpy()
        variance = float(vector @ cov.to_numpy() @ vector)
        if variance <= 0:
            rows.append(np.full(len(vector), np.nan))
        else:
            rows.append(vector * (cov.to_numpy() @ vector) / variance)
    contributions = pd.DataFrame(rows, index=w.index, columns=w.columns)
    fig, ax = new_axis(title=title)
    contributions.plot(ax=ax)
    ax.axhline(0, linewidth=0.8)
    ax.set_ylabel("Fraction of variance")
    return finalize(fig)


def frontier_surface(expected_returns, covariance, n_portfolios: int = 3_000, risk_free_rate: float = 0.0, random_state: int = 0):
    """Plot volatility, return, and Sharpe ratio as a 3D portfolio cloud."""
    mu = pd.Series(expected_returns, dtype=float)
    cov = pd.DataFrame(covariance, index=mu.index, columns=mu.index, dtype=float)
    rng = np.random.default_rng(random_state)
    weights = rng.dirichlet(np.ones(len(mu)), size=n_portfolios)
    returns = weights @ mu.to_numpy()
    volatility = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov.to_numpy(), weights))
    sharpe = (returns - risk_free_rate) / np.where(volatility > 0, volatility, np.nan)
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    points = ax.scatter(volatility, returns, sharpe, c=sharpe, s=8, alpha=0.55)
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Expected return")
    ax.set_zlabel("Sharpe")
    ax.set_title("Portfolio frontier surface")
    fig.colorbar(points, ax=ax, label="Sharpe")
    return finalize(fig)
