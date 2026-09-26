"""Shared plotting helpers."""
from __future__ import annotations

from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


def new_axis(figsize: tuple[float, float] = (10, 5.5), title: str | None = None):
    fig, ax = plt.subplots(figsize=figsize)
    if title:
        ax.set_title(title)
    ax.grid(alpha=0.25)
    return fig, ax


def finalize(fig, show: bool = False):
    fig.tight_layout()
    if show:
        plt.show()
    return fig


def to_series(data: pd.Series | Iterable[float], name: str = "value") -> pd.Series:
    out = pd.Series(data, dtype=float, name=name).dropna()
    if out.empty:
        raise ValueError("data are empty")
    return out


def monthly_return_table(returns: pd.Series) -> pd.DataFrame:
    monthly = (1 + pd.Series(returns).dropna()).resample("ME").prod() - 1
    table = monthly.to_frame("return")
    table["year"] = table.index.year
    table["month"] = table.index.month
    return table.pivot(index="year", columns="month", values="return")


def drawdown_periods(returns: pd.Series) -> pd.DataFrame:
    wealth = (1 + pd.Series(returns).dropna()).cumprod()
    dd = wealth / wealth.cummax() - 1
    underwater = dd < 0
    groups = (underwater != underwater.shift()).cumsum()
    rows = []
    for _, sample in dd[underwater].groupby(groups):
        if sample.empty:
            continue
        rows.append(
            {
                "start": sample.index[0],
                "trough": sample.idxmin(),
                "end": sample.index[-1],
                "depth": sample.min(),
                "duration": len(sample),
            }
        )
    return pd.DataFrame(rows)
