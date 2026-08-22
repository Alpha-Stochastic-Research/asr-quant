"""Cross-sectional alpha research and signal diagnostics.

The functions in this module are deliberately model-agnostic.  They help turn
an arbitrary cross-sectional score into an auditable research object: cleaned
signals, forward returns, information coefficients, quantile portfolios,
long-short returns, and turnover.

All transforms are performed *within a timestamp* unless documented otherwise,
which avoids leaking future cross-sections into the current observation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


_EPS = 1e-15


def _frame(value: pd.DataFrame, name: str) -> pd.DataFrame:
    frame = pd.DataFrame(value, dtype=float).copy()
    if frame.empty:
        raise ValueError(f"{name} is empty")
    if frame.columns.has_duplicates:
        raise ValueError(f"{name} columns must be unique")
    if frame.index.has_duplicates:
        raise ValueError(f"{name} index must be unique")
    return frame


def _aligned_pair(
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = _frame(signal, "signal")
    r = _frame(forward_return, "forward_return")
    common_index = s.index.intersection(r.index)
    common_columns = s.columns.intersection(r.columns)
    if len(common_index) == 0 or len(common_columns) == 0:
        raise ValueError("signal and forward_return do not share observations")
    return s.loc[common_index, common_columns], r.loc[common_index, common_columns]


def winsorize_cross_section(
    signal: pd.DataFrame,
    lower: float = 0.01,
    upper: float = 0.99,
) -> pd.DataFrame:
    """Winsorize each timestamp independently using cross-sectional quantiles."""
    if not 0 <= lower < upper <= 1:
        raise ValueError("require 0 <= lower < upper <= 1")
    frame = _frame(signal, "signal")
    low = frame.quantile(lower, axis=1)
    high = frame.quantile(upper, axis=1)
    return frame.clip(lower=low, upper=high, axis=0)


def cross_sectional_zscore(
    signal: pd.DataFrame,
    *,
    ddof: int = 0,
    clip: float | None = None,
) -> pd.DataFrame:
    """Standardize each timestamp across assets.

    Rows with zero cross-sectional dispersion are mapped to zero for the finite
    observations in that row.  Missing values remain missing.
    """
    if ddof < 0:
        raise ValueError("ddof must be non-negative")
    if clip is not None and clip <= 0:
        raise ValueError("clip must be positive")
    frame = _frame(signal, "signal")
    mean = frame.mean(axis=1, skipna=True)
    std = frame.std(axis=1, ddof=ddof, skipna=True)
    out = frame.sub(mean, axis=0).div(std.replace(0.0, np.nan), axis=0)

    zero_dispersion = std.abs() <= _EPS
    if zero_dispersion.any():
        mask = frame.loc[zero_dispersion].notna()
        replacement = frame.loc[zero_dispersion].where(~mask, 0.0)
        out.loc[zero_dispersion] = replacement

    if clip is not None:
        out = out.clip(-clip, clip)
    return out


def cross_sectional_rank(
    signal: pd.DataFrame,
    *,
    pct: bool = True,
    center: bool = False,
) -> pd.DataFrame:
    """Rank assets independently at each timestamp."""
    frame = _frame(signal, "signal")
    ranked = frame.rank(axis=1, method="average", pct=pct, na_option="keep")
    if center:
        ranked = ranked.sub(ranked.mean(axis=1), axis=0)
    return ranked


def neutralize_cross_section(
    signal: pd.DataFrame,
    exposures: Mapping[str, pd.DataFrame],
    *,
    add_constant: bool = True,
    min_assets: int | None = None,
) -> pd.DataFrame:
    """Remove linear cross-sectional exposure to one or more characteristics.

    Parameters
    ----------
    signal:
        Date x asset score matrix.
    exposures:
        Mapping from exposure name to a Date x asset matrix, for example
        ``{"beta": beta, "size": log_market_cap}``.
    add_constant:
        Include a cross-sectional intercept.
    min_assets:
        Minimum complete observations required at a timestamp.  By default the
        number of regressors plus two is used.

    Returns
    -------
    pandas.DataFrame
        Cross-sectional OLS residuals with the same shape as ``signal``.
    """
    frame = _frame(signal, "signal")
    if not exposures:
        raise ValueError("at least one exposure is required")

    aligned: dict[str, pd.DataFrame] = {}
    for name, exposure in exposures.items():
        e = _frame(exposure, f"exposure:{name}")
        aligned[name] = e.reindex(index=frame.index, columns=frame.columns)

    n_regressors = len(aligned) + int(add_constant)
    required = min_assets if min_assets is not None else n_regressors + 2
    if required <= n_regressors:
        raise ValueError("min_assets must exceed the number of regressors")

    out = pd.DataFrame(np.nan, index=frame.index, columns=frame.columns, dtype=float)
    for timestamp in frame.index:
        y = frame.loc[timestamp]
        x = pd.DataFrame(
            {name: exposure.loc[timestamp] for name, exposure in aligned.items()},
            index=frame.columns,
        )
        data = pd.concat([y.rename("signal"), x], axis=1).dropna()
        if len(data) < required:
            continue
        design = data.drop(columns="signal").to_numpy(dtype=float)
        if add_constant:
            design = np.column_stack([np.ones(len(data)), design])
        coefficients, *_ = np.linalg.lstsq(
            design,
            data["signal"].to_numpy(dtype=float),
            rcond=None,
        )
        residual = data["signal"].to_numpy(dtype=float) - design @ coefficients
        out.loc[timestamp, data.index] = residual
    return out


def forward_returns(
    prices: pd.DataFrame,
    periods: int | Iterable[int] = (1, 5, 21),
    *,
    log: bool = False,
) -> dict[int, pd.DataFrame]:
    """Compute future returns from time *t* to *t+h* without shifting signals.

    The return labelled at time ``t`` uses ``price[t+h] / price[t]``.  The final
    ``h`` observations are therefore missing by construction.
    """
    frame = _frame(prices, "prices")
    if (frame <= 0).any().any() and log:
        raise ValueError("log forward returns require strictly positive prices")
    horizons = [periods] if isinstance(periods, int) else list(periods)
    if not horizons or any(int(h) != h or h <= 0 for h in horizons):
        raise ValueError("periods must contain positive integers")

    result: dict[int, pd.DataFrame] = {}
    for horizon_raw in horizons:
        horizon = int(horizon_raw)
        if log:
            result[horizon] = np.log(frame.shift(-horizon) / frame)
        else:
            result[horizon] = frame.shift(-horizon) / frame - 1.0
    return result


def information_coefficient(
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
    *,
    method: str = "spearman",
    min_assets: int = 5,
) -> pd.Series:
    """Cross-sectional correlation between a signal and a future return."""
    if min_assets < 2:
        raise ValueError("min_assets must be at least 2")
    key = method.lower()
    if key not in {"spearman", "pearson"}:
        raise ValueError("method must be spearman or pearson")
    s, r = _aligned_pair(signal, forward_return)

    values: dict[object, float] = {}
    for timestamp in s.index:
        data = pd.concat([s.loc[timestamp], r.loc[timestamp]], axis=1).dropna()
        if len(data) < min_assets:
            values[timestamp] = np.nan
            continue
        if data.iloc[:, 0].nunique() < 2 or data.iloc[:, 1].nunique() < 2:
            values[timestamp] = np.nan
            continue
        values[timestamp] = float(data.iloc[:, 0].corr(data.iloc[:, 1], method=key))
    return pd.Series(values, name=f"{key}_ic", dtype=float)


def ic_decay(
    signal: pd.DataFrame,
    prices: pd.DataFrame,
    horizons: Iterable[int] = (1, 5, 10, 21),
    *,
    method: str = "spearman",
    min_assets: int = 5,
) -> pd.DataFrame:
    """Summarize information-coefficient decay across future horizons."""
    forward = forward_returns(prices, horizons)
    rows: list[dict[str, float | int]] = []
    for horizon, returns in forward.items():
        ic = information_coefficient(signal, returns, method=method, min_assets=min_assets).dropna()
        n = len(ic)
        mean = float(ic.mean()) if n else np.nan
        std = float(ic.std(ddof=1)) if n > 1 else np.nan
        rows.append(
            {
                "horizon": horizon,
                "mean_ic": mean,
                "std_ic": std,
                "ic_ir": mean / std if n > 1 and std > _EPS else np.nan,
                "t_stat": mean / (std / np.sqrt(n)) if n > 1 and std > _EPS else np.nan,
                "positive_rate": float((ic > 0).mean()) if n else np.nan,
                "observations": n,
            }
        )
    return pd.DataFrame(rows).set_index("horizon")


def quantile_portfolio_returns(
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
    *,
    quantiles: int = 5,
    min_assets: int | None = None,
) -> pd.DataFrame:
    """Equal-weight future returns for cross-sectional signal quantiles."""
    if quantiles < 2:
        raise ValueError("quantiles must be at least 2")
    required = min_assets if min_assets is not None else quantiles
    if required < quantiles:
        raise ValueError("min_assets cannot be smaller than quantiles")
    s, r = _aligned_pair(signal, forward_return)
    columns = [f"Q{i}" for i in range(1, quantiles + 1)]
    out = pd.DataFrame(np.nan, index=s.index, columns=columns, dtype=float)

    for timestamp in s.index:
        data = pd.concat(
            [s.loc[timestamp].rename("signal"), r.loc[timestamp].rename("return")],
            axis=1,
        ).dropna()
        if len(data) < required or data["signal"].nunique() < 2:
            continue

        # Ranks make the assignment deterministic even when raw signal values tie.
        ranks = data["signal"].rank(method="first", pct=True)
        labels = np.minimum((ranks * quantiles).apply(np.ceil).astype(int), quantiles)
        labels = labels.clip(lower=1)
        grouped = data["return"].groupby(labels).mean()
        for q, value in grouped.items():
            out.loc[timestamp, f"Q{int(q)}"] = float(value)
    return out


def long_short_return(quantile_returns: pd.DataFrame) -> pd.Series:
    """Return top-minus-bottom quantile performance."""
    frame = _frame(quantile_returns, "quantile_returns")
    if frame.shape[1] < 2:
        raise ValueError("at least two quantile columns are required")

    def _number(column: object) -> int:
        text = str(column)
        if not text.startswith("Q") or not text[1:].isdigit():
            raise ValueError("quantile columns must be named Q1, Q2, ...")
        return int(text[1:])

    ordered = sorted(frame.columns, key=_number)
    return (frame[ordered[-1]] - frame[ordered[0]]).rename("long_short")


def signal_to_weights(
    signal: pd.DataFrame,
    *,
    gross: float = 1.0,
    dollar_neutral: bool = True,
    max_abs_weight: float | None = None,
) -> pd.DataFrame:
    """Convert continuous scores into normalized portfolio weights.

    Dollar-neutral weights are demeaned cross-sectionally before gross scaling.
    Long-only-style usage can set ``dollar_neutral=False``; negative signals are
    then allowed and are simply gross-normalized.
    """
    if gross <= 0:
        raise ValueError("gross must be positive")
    if max_abs_weight is not None and not 0 < max_abs_weight <= gross:
        raise ValueError("max_abs_weight must lie in (0, gross]")
    frame = _frame(signal, "signal")
    raw = frame.sub(frame.mean(axis=1), axis=0) if dollar_neutral else frame.copy()
    denom = raw.abs().sum(axis=1).replace(0.0, np.nan)
    weights = raw.div(denom, axis=0).fillna(0.0) * gross

    if max_abs_weight is not None:
        # Iterative clipping/rescaling preserves the gross target as far as the
        # cap permits.  It intentionally does not manufacture exposure when all
        # scores are zero.
        for _ in range(20):
            clipped = weights.clip(-max_abs_weight, max_abs_weight)
            row_gross = clipped.abs().sum(axis=1)
            scalable = row_gross > _EPS
            scaled = clipped.copy()
            scaled.loc[scalable] = clipped.loc[scalable].div(row_gross[scalable], axis=0) * gross
            next_weights = scaled.clip(-max_abs_weight, max_abs_weight)
            if np.nanmax(np.abs((next_weights - weights).to_numpy())) < 1e-12:
                weights = next_weights
                break
            weights = next_weights
    return weights


def weight_turnover(weights: pd.DataFrame) -> pd.Series:
    """One-way portfolio turnover: 0.5 * sum(|w_t - w_{t-1}|)."""
    frame = _frame(weights, "weights").fillna(0.0)
    return (0.5 * frame.diff().abs().sum(axis=1)).fillna(0.0).rename("turnover")


@dataclass(frozen=True)
class AlphaResearchReport:
    """Compact, inspectable output of a cross-sectional signal study."""

    information_coefficient: pd.Series
    quantile_returns: pd.DataFrame
    long_short_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    summary: pd.Series


def analyze_signal(
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
    *,
    quantiles: int = 5,
    ic_method: str = "spearman",
    min_assets: int = 5,
    gross: float = 1.0,
) -> AlphaResearchReport:
    """Run a standard cross-sectional alpha diagnostic in one call."""
    s, r = _aligned_pair(signal, forward_return)
    ic = information_coefficient(s, r, method=ic_method, min_assets=min_assets)
    qret = quantile_portfolio_returns(
        s,
        r,
        quantiles=quantiles,
        min_assets=max(min_assets, quantiles),
    )
    spread = long_short_return(qret)
    weights = signal_to_weights(s, gross=gross, dollar_neutral=True)
    turnover = weight_turnover(weights)

    spread_clean = spread.dropna()
    ic_clean = ic.dropna()
    spread_std = float(spread_clean.std(ddof=1)) if len(spread_clean) > 1 else np.nan
    ic_std = float(ic_clean.std(ddof=1)) if len(ic_clean) > 1 else np.nan
    summary = pd.Series(
        {
            "mean_ic": float(ic_clean.mean()) if len(ic_clean) else np.nan,
            "ic_ir": float(ic_clean.mean() / ic_std) if len(ic_clean) > 1 and ic_std > _EPS else np.nan,
            "ic_positive_rate": float((ic_clean > 0).mean()) if len(ic_clean) else np.nan,
            "mean_long_short_return": float(spread_clean.mean()) if len(spread_clean) else np.nan,
            "long_short_t_stat": (
                float(spread_clean.mean() / (spread_std / np.sqrt(len(spread_clean))))
                if len(spread_clean) > 1 and spread_std > _EPS
                else np.nan
            ),
            "mean_turnover": float(turnover.mean()),
            "observations": float(len(ic_clean)),
        },
        name="value",
    )
    return AlphaResearchReport(
        information_coefficient=ic,
        quantile_returns=qret,
        long_short_returns=spread,
        weights=weights,
        turnover=turnover,
        summary=summary,
    )


__all__ = [
    "AlphaResearchReport",
    "analyze_signal",
    "cross_sectional_rank",
    "cross_sectional_zscore",
    "forward_returns",
    "ic_decay",
    "information_coefficient",
    "long_short_return",
    "neutralize_cross_section",
    "quantile_portfolio_returns",
    "signal_to_weights",
    "weight_turnover",
    "winsorize_cross_section",
]
