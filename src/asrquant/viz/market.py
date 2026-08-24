"""Price, return, distribution, dependence, and time-series visualizations."""
from __future__ import annotations

import calendar
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

from ..data import as_frame, simple_returns, validate_ohlcv
from .base import finalize, monthly_return_table, new_axis, to_series


def _boxplot_with_labels(ax, values, labels, **kwargs):
    """Call Matplotlib boxplot across the 3.8-to-3.11 keyword transition."""
    try:
        return ax.boxplot(values, tick_labels=labels, **kwargs)
    except TypeError as exc:
        if "tick_labels" not in str(exc):
            raise
        return ax.boxplot(values, labels=labels, **kwargs)


def price_chart(prices, normalize: bool = False, log_scale: bool = False, title: str | None = None):
    frame = as_frame(prices)
    if normalize:
        frame = frame.div(frame.iloc[0]).mul(100)
    fig, ax = new_axis(title=title or ("Normalized prices" if normalize else "Prices"))
    frame.plot(ax=ax)
    ax.set_yscale("log" if log_scale else "linear")
    ax.set_ylabel("Index = 100" if normalize else "Price")
    return finalize(fig)


def returns_chart(prices=None, returns=None, cumulative: bool = False, title: str | None = None):
    if returns is None:
        if prices is None:
            raise ValueError("provide prices or returns")
        frame = simple_returns(prices)
    else:
        frame = as_frame(returns, "return")
    data = (1 + frame).cumprod() - 1 if cumulative else frame
    fig, ax = new_axis(title=title or ("Cumulative returns" if cumulative else "Returns"))
    data.plot(ax=ax)
    ax.set_ylabel("Return")
    return finalize(fig)


def candlestick(data: pd.DataFrame, volume: bool = True, width: float = 0.6, title: str = "OHLC"):
    """Dependency-light OHLC candlestick plot."""
    ohlcv = validate_ohlcv(data)
    if volume and "Volume" in ohlcv:
        fig, (ax, axv) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [4, 1]})
    else:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        axv = None
    x = np.arange(len(ohlcv))
    for i, row in enumerate(ohlcv.itertuples()):
        open_, high, low, close = row.Open, row.High, row.Low, row.Close
        ax.vlines(i, low, high, linewidth=1)
        bottom = min(open_, close)
        height = max(abs(close - open_), np.finfo(float).eps)
        rect = plt.Rectangle((i - width / 2, bottom), width, height, fill=close >= open_, alpha=0.7)
        ax.add_patch(rect)
    ax.set_xlim(-1, len(ohlcv))
    ax.set_title(title)
    ax.set_ylabel("Price")
    ax.grid(alpha=0.2)
    ticks = np.linspace(0, len(ohlcv) - 1, min(8, len(ohlcv))).astype(int)
    ax.set_xticks(ticks, [ohlcv.index[i].strftime("%Y-%m-%d") for i in ticks], rotation=30)
    if axv is not None:
        axv.bar(x, ohlcv["Volume"].to_numpy())
        axv.set_ylabel("Volume")
        axv.grid(alpha=0.2)
    return finalize(fig)


def distribution(returns, bins: int = 50, kde: bool = True, normal_overlay: bool = True, title: str = "Return distribution"):
    r = to_series(returns, "return")
    fig, ax = new_axis(title=title)
    ax.hist(r, bins=bins, density=True, alpha=0.55)
    x = np.linspace(r.min(), r.max(), 400)
    if kde and r.nunique() > 1:
        ax.plot(x, stats.gaussian_kde(r)(x), label="KDE")
    if normal_overlay and r.std(ddof=1) > 0:
        ax.plot(x, stats.norm.pdf(x, r.mean(), r.std(ddof=1)), linestyle="--", label="Normal")
    ax.axvline(r.mean(), linestyle=":", label="Mean")
    ax.legend()
    return finalize(fig)


def ecdf(returns, title: str = "Empirical cumulative distribution"):
    r = np.sort(to_series(returns).to_numpy())
    y = np.arange(1, len(r) + 1) / len(r)
    fig, ax = new_axis(title=title)
    ax.step(r, y, where="post")
    ax.set_xlabel("Return")
    ax.set_ylabel("Probability")
    return finalize(fig)


def qq_plot(returns, distribution_name: str = "norm", title: str = "Q-Q plot"):
    r = to_series(returns)
    dist = getattr(stats, distribution_name)
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    stats.probplot(r, dist=dist, plot=ax)
    ax.set_title(title)
    ax.grid(alpha=0.25)
    return finalize(fig)


def box_violin(returns, title: str = "Return dispersion"):
    frame = as_frame(returns, "return")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    _boxplot_with_labels(ax1, [frame[c].dropna() for c in frame], frame.columns)
    ax2.violinplot([frame[c].dropna() for c in frame], showmeans=True, showextrema=True)
    ax2.set_xticks(range(1, len(frame.columns) + 1), frame.columns)
    ax1.set_title("Box plot")
    ax2.set_title("Violin plot")
    fig.suptitle(title)
    for ax in (ax1, ax2):
        ax.grid(alpha=0.2)
    return finalize(fig)


def rolling_statistics(returns, window: int = 63, annualization: int = 252, title: str = "Rolling statistics"):
    r = as_frame(returns, "return")
    mean = r.rolling(window).mean() * annualization
    vol = r.rolling(window).std(ddof=1) * np.sqrt(annualization)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    mean.plot(ax=ax1)
    vol.plot(ax=ax2)
    ax1.set_title(title)
    ax1.set_ylabel("Annualized mean")
    ax2.set_ylabel("Annualized volatility")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.25)
    return finalize(fig)


def autocorrelation(returns, lags: int = 40, pacf: bool = False, title: str | None = None):
    r = to_series(returns)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    effective_lags = min(lags, max(1, len(r) // 2 - 1))
    if pacf:
        plot_pacf(r, lags=effective_lags, ax=ax, method="ywm")
    else:
        plot_acf(r, lags=effective_lags, ax=ax)
    ax.set_title(title or ("Partial autocorrelation" if pacf else "Autocorrelation"))
    return finalize(fig)


def correlation_heatmap(returns, method: str = "pearson", title: str = "Correlation matrix"):
    corr = as_frame(returns, "return").corr(method=method)
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    image = ax.imshow(corr, vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="Correlation")
    return finalize(fig)


def rolling_correlation(returns, asset_a: str | None = None, asset_b: str | None = None, window: int = 63):
    frame = as_frame(returns, "return")
    if frame.shape[1] < 2:
        raise ValueError("at least two assets are required")
    a = asset_a or frame.columns[0]
    b = asset_b or frame.columns[1]
    corr = frame[a].rolling(window).corr(frame[b])
    fig, ax = new_axis(title=f"Rolling correlation: {a} vs {b}")
    corr.plot(ax=ax)
    ax.axhline(0, linewidth=0.8)
    ax.set_ylim(-1, 1)
    return finalize(fig)


def monthly_heatmap(returns, title: str = "Monthly returns"):
    table = monthly_return_table(to_series(returns))
    fig, ax = plt.subplots(figsize=(11, max(3.5, 0.45 * len(table) + 1.5)))
    image = ax.imshow(table.fillna(0), aspect="auto")
    ax.set_xticks(range(12), [calendar.month_abbr[i] for i in range(1, 13)])
    ax.set_yticks(range(len(table)), table.index)
    for i in range(len(table)):
        for j in range(12):
            value = table.iloc[i, j] if j < table.shape[1] else np.nan
            if pd.notna(value):
                ax.text(j, i, f"{value:.1%}", ha="center", va="center", fontsize=8)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="Return")
    return finalize(fig)


def calendar_heatmap(returns, title: str = "Daily return calendar"):
    r = to_series(returns)
    frame = r.to_frame("return")
    frame["year"] = frame.index.year
    frame["week"] = frame.index.isocalendar().week.astype(int)
    frame["weekday"] = frame.index.weekday
    pivot = frame.pivot_table(index="weekday", columns=["year", "week"], values="return", aggfunc="sum")
    fig, ax = plt.subplots(figsize=(14, 4))
    image = ax.imshow(pivot.fillna(0), aspect="auto")
    ax.set_yticks(range(5), ["Mon", "Tue", "Wed", "Thu", "Fri"])
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="Return")
    return finalize(fig)


def scatter_matrix(returns, title: str = "Return scatter matrix"):
    frame = as_frame(returns, "return").dropna()
    axes = pd.plotting.scatter_matrix(frame, figsize=(10, 10), diagonal="kde", alpha=0.4)
    fig = axes[0, 0].figure
    fig.suptitle(title)
    return finalize(fig)


def seasonality_boxplot(returns, by: str = "month", title: str | None = None):
    """Compare return distributions by calendar month or weekday."""
    s = to_series(returns, "return")
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("returns must use a DatetimeIndex")
    key = by.lower()
    if key == "month":
        groups = [s[s.index.month == i].to_numpy() for i in range(1, 13)]
        labels = [calendar.month_abbr[i] for i in range(1, 13)]
    elif key in {"weekday", "dayofweek"}:
        groups = [s[s.index.dayofweek == i].to_numpy() for i in range(5)]
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    else:
        raise ValueError("by must be month or weekday")
    fig, ax = new_axis(title=title or f"Return seasonality by {key}")
    _boxplot_with_labels(ax, groups, labels, showfliers=False)
    ax.axhline(0, linewidth=0.8)
    ax.set_ylabel("Return")
    return finalize(fig)


def lag_scatter(returns, lag: int = 1, title: str | None = None):
    """Plot returns against their selected lag."""
    if lag <= 0:
        raise ValueError("lag must be positive")
    s = to_series(returns, "return")
    data = pd.concat([s.shift(lag).rename("lagged"), s.rename("current")], axis=1).dropna()
    fig, ax = new_axis(title=title or f"Return lag scatter (lag={lag})")
    ax.scatter(data["lagged"], data["current"], alpha=0.45)
    if len(data) >= 2:
        slope, intercept = np.polyfit(data["lagged"], data["current"], 1)
        x = np.linspace(data["lagged"].min(), data["lagged"].max(), 100)
        ax.plot(x, intercept + slope * x)
    ax.set_xlabel(f"Return t-{lag}")
    ax.set_ylabel("Return t")
    return finalize(fig)


def volatility_cone(
    returns,
    windows=(5, 21, 63, 126, 252),
    quantiles=(0.10, 0.50, 0.90),
    annualization: int = 252,
    title: str = "Historical volatility cone",
):
    """Show the distribution of rolling annualized volatility by horizon."""
    s = to_series(returns, "return")
    records = []
    for window in windows:
        values = s.rolling(int(window)).std(ddof=1) * np.sqrt(annualization)
        records.append([values.quantile(q) for q in quantiles])
    frame = pd.DataFrame(records, index=list(windows), columns=list(quantiles))
    fig, ax = new_axis(title=title)
    for q in quantiles:
        ax.plot(frame.index, frame[q], marker="o", label=f"q={q:.0%}")
    ax.set_xlabel("Rolling window")
    ax.set_ylabel("Annualized volatility")
    ax.legend()
    return finalize(fig)


def rolling_beta(asset_returns, benchmark_returns, window: int = 63, title: str = "Rolling beta"):
    """Plot rolling covariance-to-variance beta."""
    asset = to_series(asset_returns, "asset")
    benchmark = to_series(benchmark_returns, "benchmark")
    data = pd.concat([asset, benchmark], axis=1).dropna()
    beta = data["asset"].rolling(window).cov(data["benchmark"]) / data["benchmark"].rolling(window).var()
    fig, ax = new_axis(title=title)
    beta.plot(ax=ax)
    ax.axhline(1, linestyle="--", linewidth=0.8)
    ax.set_ylabel("Beta")
    return finalize(fig)


def period_return_ranking(returns: pd.DataFrame, rule: str = "YE", title: str = "Asset return ranking"):
    """Rank assets by compounded return in each resampling period."""
    frame = pd.DataFrame(returns, dtype=float).dropna(how="all")
    compounded = (1 + frame).resample(rule).prod() - 1
    ranks = compounded.rank(axis=1, ascending=False)
    fig, ax = plt.subplots(figsize=(max(8, 0.8 * len(ranks)), max(4, 0.45 * frame.shape[1] + 2)))
    image = ax.imshow(ranks.T, aspect="auto")
    ax.set_yticks(range(len(frame.columns)), frame.columns)
    ax.set_xticks(range(len(ranks)), [str(x)[:10] for x in ranks.index], rotation=35, ha="right")
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="Rank (1 = best)")
    return finalize(fig)
