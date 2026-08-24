"""Market-microstructure and execution visualizations."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import finalize, new_axis


def bid_ask_spread(bid, ask, relative: bool = True, rolling: int | None = 20):
    bid = pd.Series(bid, dtype=float)
    ask = pd.Series(ask, dtype=float)
    spread = ask - bid
    if relative:
        spread = spread / ((ask + bid) / 2)
    if rolling:
        spread = spread.rolling(rolling).mean()
    fig, ax = new_axis(title="Relative bid-ask spread" if relative else "Bid-ask spread")
    spread.plot(ax=ax)
    return finalize(fig)


def volume_profile(price, volume, bins: int = 30):
    price = pd.Series(price, dtype=float)
    volume = pd.Series(volume, dtype=float).reindex(price.index)
    categories = pd.cut(price, bins=bins)
    profile = volume.groupby(categories, observed=True).sum()
    centers = np.array([interval.mid for interval in profile.index])
    fig, ax = new_axis(title="Volume profile")
    ax.barh(centers, profile.to_numpy(), height=np.diff(np.linspace(price.min(), price.max(), bins + 1)).mean())
    ax.set_xlabel("Volume")
    ax.set_ylabel("Price")
    return finalize(fig)


def order_book_depth(bid_prices, bid_sizes, ask_prices, ask_sizes):
    bp = np.asarray(bid_prices, dtype=float)
    bs = np.asarray(bid_sizes, dtype=float)
    ap = np.asarray(ask_prices, dtype=float)
    ass = np.asarray(ask_sizes, dtype=float)
    order_b = np.argsort(bp)[::-1]
    order_a = np.argsort(ap)
    fig, ax = new_axis(title="Order-book depth")
    ax.step(bp[order_b], np.cumsum(bs[order_b]), where="post", label="Bid depth")
    ax.step(ap[order_a], np.cumsum(ass[order_a]), where="post", label="Ask depth")
    ax.set_xlabel("Price")
    ax.set_ylabel("Cumulative size")
    ax.legend()
    return finalize(fig)


def slippage_curve(order_size, slippage, title: str = "Slippage versus order size"):
    fig, ax = new_axis(title=title)
    ax.scatter(order_size, slippage, alpha=0.5)
    if len(order_size) >= 2:
        x = np.asarray(order_size, dtype=float)
        y = np.asarray(slippage, dtype=float)
        coef = np.polyfit(x, y, 1)
        grid = np.linspace(x.min(), x.max(), 200)
        ax.plot(grid, np.polyval(coef, grid))
    ax.set_xlabel("Order size")
    ax.set_ylabel("Slippage")
    return finalize(fig)


def trade_timeline(prices: pd.Series, trades: pd.DataFrame):
    required = {"timestamp", "side", "price"}
    if not required.issubset(trades.columns):
        raise ValueError(f"trades must contain {required}")
    fig, ax = new_axis(title="Trade timeline")
    pd.Series(prices).plot(ax=ax)
    for side, marker in [("buy", "^"), ("sell", "v")]:
        subset = trades[trades["side"].str.lower() == side]
        ax.scatter(pd.to_datetime(subset["timestamp"]), subset["price"], marker=marker, s=60, label=side.title())
    ax.legend()
    return finalize(fig)


def spread_distribution(bid, ask, relative: bool = True, bins: int = 40, title: str = "Spread distribution"):
    bid_s = pd.Series(bid, dtype=float)
    ask_s = pd.Series(ask, dtype=float)
    spread = ask_s - bid_s
    if relative:
        spread = spread / ((ask_s + bid_s) / 2)
    fig, ax = new_axis(title=title)
    ax.hist(spread.dropna(), bins=bins, density=True, alpha=0.65)
    ax.set_xlabel("Relative spread" if relative else "Spread")
    return finalize(fig)


def order_flow_imbalance(bid_volume, ask_volume, rolling: int | None = 20, title: str = "Order-flow imbalance"):
    bid_s = pd.Series(bid_volume, dtype=float)
    ask_s = pd.Series(ask_volume, dtype=float)
    imbalance = (bid_s - ask_s) / (bid_s + ask_s).replace(0, np.nan)
    if rolling:
        imbalance = imbalance.rolling(rolling).mean()
    fig, ax = new_axis(title=title)
    imbalance.plot(ax=ax)
    ax.axhline(0, linewidth=0.8)
    ax.set_ylabel("Imbalance")
    return finalize(fig)


def intraday_seasonality(values, statistic: str = "mean", title: str = "Intraday seasonality"):
    s = pd.Series(values, dtype=float).dropna()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("values must use a DatetimeIndex")
    grouped = s.groupby(s.index.strftime("%H:%M"))
    if statistic == "mean":
        profile = grouped.mean()
    elif statistic == "median":
        profile = grouped.median()
    elif statistic == "std":
        profile = grouped.std(ddof=1)
    else:
        raise ValueError("statistic must be mean, median, or std")
    fig, ax = new_axis(title=title)
    profile.plot(ax=ax)
    ax.set_xlabel("Time of day")
    ax.set_ylabel(statistic.title())
    ax.tick_params(axis="x", rotation=45)
    return finalize(fig)


def price_impact_scatter(signed_volume, price_change, title: str = "Price impact"):
    volume = pd.Series(signed_volume, dtype=float, name="signed_volume")
    change = pd.Series(price_change, dtype=float, name="price_change")
    data = pd.concat([volume, change], axis=1).dropna()
    fig, ax = new_axis(title=title)
    ax.scatter(data["signed_volume"], data["price_change"], alpha=0.45)
    if len(data) >= 2:
        slope, intercept = np.polyfit(data["signed_volume"], data["price_change"], 1)
        x = np.linspace(data["signed_volume"].min(), data["signed_volume"].max(), 100)
        ax.plot(x, intercept + slope * x)
    ax.set_xlabel("Signed volume")
    ax.set_ylabel("Price change")
    return finalize(fig)
