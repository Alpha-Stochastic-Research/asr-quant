"""Derivative payoff, Greek, volatility-surface, and term-structure plots."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..derivatives import black_scholes_greeks, black_scholes_price, option_payoff
from .base import finalize, new_axis


def payoff_diagram(spot_grid, strike: float, option: str = "call", premium: float = 0.0, position: float = 1.0):
    grid = np.asarray(spot_grid, dtype=float)
    payoff = option_payoff(grid, strike, option, premium, position)
    fig, ax = new_axis(title=f"{option.title()} option payoff")
    ax.plot(grid, payoff)
    ax.axhline(0, linewidth=0.8)
    ax.axvline(strike, linestyle="--", label="Strike")
    ax.set_xlabel("Terminal underlying price")
    ax.set_ylabel("Profit / loss")
    ax.legend()
    return finalize(fig)


def option_price_curve(spot_grid, strike: float, maturity: float, rate: float, volatility: float, option: str = "call"):
    grid = np.asarray(spot_grid, dtype=float)
    values = black_scholes_price(grid, strike, maturity, rate, volatility, option)
    fig, ax = new_axis(title=f"Black-Scholes {option} value")
    ax.plot(grid, values)
    ax.set_xlabel("Spot")
    ax.set_ylabel("Option value")
    return finalize(fig)


def greek_curves(spot_grid, strike: float, maturity: float, rate: float, volatility: float, option: str = "call"):
    grid = np.asarray(spot_grid, dtype=float)
    greeks = black_scholes_greeks(grid, strike, maturity, rate, volatility, option)
    fig, axes = plt.subplots(3, 2, figsize=(12, 11))
    for ax, (name, values) in zip(axes.ravel(), greeks.items()):
        ax.plot(grid, values)
        ax.set_title(name.title())
        ax.grid(alpha=0.2)
    axes[-1, -1].axis("off")
    fig.suptitle(f"{option.title()} Greeks")
    return finalize(fig)


def volatility_surface(strikes, maturities, implied_vols, title: str = "Implied volatility surface", interactive: bool = False):
    x = np.asarray(strikes, dtype=float)
    y = np.asarray(maturities, dtype=float)
    z = np.asarray(implied_vols, dtype=float)
    if z.shape != (len(y), len(x)):
        raise ValueError("implied_vols shape must be (len(maturities), len(strikes))")
    xx, yy = np.meshgrid(x, y)
    if interactive:
        import plotly.graph_objects as go
        return go.Figure(data=[go.Surface(x=xx, y=yy, z=z)], layout=go.Layout(title=title, scene={"xaxis_title": "Strike", "yaxis_title": "Maturity", "zaxis_title": "Implied vol"}))
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(xx, yy, z, cmap=None, alpha=0.85)
    ax.set_xlabel("Strike")
    ax.set_ylabel("Maturity")
    ax.set_zlabel("Implied volatility")
    ax.set_title(title)
    return finalize(fig)


def greek_surface(strikes, maturities, spot: float, rate: float, volatility: float, greek: str = "gamma", option: str = "call", interactive: bool = False):
    strikes = np.asarray(strikes, dtype=float)
    maturities = np.asarray(maturities, dtype=float)
    kk, tt = np.meshgrid(strikes, maturities)
    values = black_scholes_greeks(spot, kk, tt, rate, volatility, option)[greek]
    return volatility_surface(strikes, maturities, values, title=f"{greek.title()} surface", interactive=interactive)


def yield_curve(maturities, yields, title: str = "Yield curve"):
    fig, ax = new_axis(title=title)
    ax.plot(maturities, yields, marker="o")
    ax.set_xlabel("Maturity")
    ax.set_ylabel("Yield")
    return finalize(fig)


def model_comparison(spot_grid, strike: float, maturity: float, rate: float, lognormal_volatility: float, normal_volatility: float, option: str = "call"):
    """Compare Black-Scholes-Merton and Bachelier prices on one grid."""
    from ..derivatives import bachelier_price
    grid = np.asarray(spot_grid, dtype=float)
    bsm = black_scholes_price(grid, strike, maturity, rate, lognormal_volatility, option)
    normal = bachelier_price(grid*np.exp(rate*maturity), strike, maturity, normal_volatility, option, np.exp(-rate*maturity))
    fig, ax = new_axis(title=f"{option.title()} model comparison")
    ax.plot(grid, bsm, label="Black-Scholes-Merton")
    ax.plot(grid, normal, label="Bachelier")
    ax.set_xlabel("Spot")
    ax.set_ylabel("Option value")
    ax.legend()
    return finalize(fig)


def monte_carlo_convergence(estimates, reference: float | None = None, title: str = "Monte Carlo convergence"):
    """Plot cumulative Monte Carlo estimates against an optional reference."""
    values = pd.Series(estimates, dtype=float).dropna()
    cumulative = values.expanding().mean()
    se = values.expanding().std(ddof=1) / np.sqrt(np.arange(1, len(values)+1))
    fig, ax = new_axis(title=title)
    ax.plot(cumulative.index, cumulative, label="Cumulative estimate")
    ax.fill_between(cumulative.index, cumulative-1.96*se, cumulative+1.96*se, alpha=0.2, label="Approx. 95% interval")
    if reference is not None:
        ax.axhline(reference, linestyle="--", label="Reference")
    ax.set_xlabel("Number of paths")
    ax.set_ylabel("Price estimate")
    ax.legend()
    return finalize(fig)


def implied_volatility_smile(strikes, implied_vols, forward: float | None = None, title: str = "Implied volatility smile"):
    strikes = np.asarray(strikes, dtype=float)
    vols = np.asarray(implied_vols, dtype=float)
    fig, ax = new_axis(title=title)
    ax.plot(strikes, vols, marker="o")
    if forward is not None:
        ax.axvline(forward, linestyle="--", label="Forward")
        ax.legend()
    ax.set_xlabel("Strike")
    ax.set_ylabel("Implied volatility")
    return finalize(fig)


def term_structure_slices(strikes, maturities, implied_vols, title: str = "Implied volatility term slices"):
    strikes = np.asarray(strikes, dtype=float)
    maturities = np.asarray(maturities, dtype=float)
    surface = np.asarray(implied_vols, dtype=float)
    if surface.shape != (len(maturities), len(strikes)):
        raise ValueError("implied_vols shape must be (len(maturities), len(strikes))")
    fig, ax = new_axis(title=title)
    for maturity, row in zip(maturities, surface):
        ax.plot(strikes, row, marker="o", label=f"T={maturity:g}")
    ax.set_xlabel("Strike")
    ax.set_ylabel("Implied volatility")
    ax.legend()
    return finalize(fig)


def greek_heatmap(strikes, maturities, spot: float, rate: float, volatility: float, greek: str = "gamma", option: str = "call"):
    strikes = np.asarray(strikes, dtype=float)
    maturities = np.asarray(maturities, dtype=float)
    kk, tt = np.meshgrid(strikes, maturities)
    values = black_scholes_greeks(spot, kk, tt, rate, volatility, option)[greek]
    fig, ax = plt.subplots(figsize=(9, 6))
    image = ax.imshow(values, aspect="auto", origin="lower")
    ax.set_xticks(range(len(strikes)), [f"{x:g}" for x in strikes], rotation=35)
    ax.set_yticks(range(len(maturities)), [f"{x:g}" for x in maturities])
    ax.set_xlabel("Strike")
    ax.set_ylabel("Maturity")
    ax.set_title(f"{greek.title()} heatmap")
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def scenario_pnl_surface(
    spot_grid,
    volatility_grid,
    strike: float,
    maturity: float,
    rate: float,
    base_spot: float,
    base_volatility: float,
    option: str = "call",
):
    """Show option mark-to-model P&L across spot and volatility scenarios."""
    spots = np.asarray(spot_grid, dtype=float)
    vols = np.asarray(volatility_grid, dtype=float)
    ss, vv = np.meshgrid(spots, vols)
    base = float(black_scholes_price(base_spot, strike, maturity, rate, base_volatility, option))
    pnl = black_scholes_price(ss, strike, maturity, rate, vv, option) - base
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(ss, vv, pnl, alpha=0.85)
    ax.set_xlabel("Spot")
    ax.set_ylabel("Volatility")
    ax.set_zlabel("P&L")
    ax.set_title("Option scenario P&L surface")
    return finalize(fig)
