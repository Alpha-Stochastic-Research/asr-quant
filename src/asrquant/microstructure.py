"""Market-microstructure diagnostics for research and execution analysis.

The module focuses on transparent measures that can be computed from quotes,
trades, and signed flow without requiring a proprietary market-data schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


_EPS = 1e-15


def _series(value: pd.Series | Iterable[float], name: str) -> pd.Series:
    out = pd.Series(value, dtype=float).copy()
    if out.empty:
        raise ValueError(f"{name} is empty")
    return out


def _align(*items: tuple[pd.Series | Iterable[float], str]) -> list[pd.Series]:
    series = [_series(value, name).rename(name) for value, name in items]
    frame = pd.concat(series, axis=1).dropna()
    if frame.empty:
        raise ValueError("inputs have no aligned finite observations")
    return [frame.iloc[:, i] for i in range(frame.shape[1])]


def _validate_quotes(bid: pd.Series, ask: pd.Series) -> None:
    if (bid <= 0).any() or (ask <= 0).any():
        raise ValueError("bid and ask must be strictly positive")
    if (ask < bid).any():
        raise ValueError("ask must be greater than or equal to bid")


def midquote(
    bid: pd.Series | Iterable[float],
    ask: pd.Series | Iterable[float],
) -> pd.Series:
    """Arithmetic midpoint of best bid and best ask."""
    bid_s, ask_s = _align((bid, "bid"), (ask, "ask"))
    _validate_quotes(bid_s, ask_s)
    return ((bid_s + ask_s) / 2.0).rename("midquote")


def quoted_spread(
    bid: pd.Series | Iterable[float],
    ask: pd.Series | Iterable[float],
    *,
    relative: bool = False,
) -> pd.Series:
    """Quoted bid-ask spread in price units or relative to the midpoint."""
    bid_s, ask_s = _align((bid, "bid"), (ask, "ask"))
    _validate_quotes(bid_s, ask_s)
    spread = ask_s - bid_s
    if relative:
        spread = spread / ((bid_s + ask_s) / 2.0)
    return spread.rename("quoted_spread")


def microprice(
    bid: pd.Series | Iterable[float],
    ask: pd.Series | Iterable[float],
    bid_size: pd.Series | Iterable[float],
    ask_size: pd.Series | Iterable[float],
) -> pd.Series:
    """Top-of-book microprice using opposite-side depth weighting."""
    bid_s, ask_s, bid_q, ask_q = _align(
        (bid, "bid"),
        (ask, "ask"),
        (bid_size, "bid_size"),
        (ask_size, "ask_size"),
    )
    _validate_quotes(bid_s, ask_s)
    if (bid_q < 0).any() or (ask_q < 0).any():
        raise ValueError("quote sizes must be non-negative")
    depth = bid_q + ask_q
    if (depth <= 0).any():
        raise ValueError("bid_size + ask_size must be positive")
    value = (ask_s * bid_q + bid_s * ask_q) / depth
    return value.rename("microprice")


def effective_spread(
    trade_price: pd.Series | Iterable[float],
    reference_mid: pd.Series | Iterable[float],
    side: pd.Series | Iterable[float] | None = None,
    *,
    relative: bool = False,
) -> pd.Series:
    """Effective spread, conventionally doubled around the midpoint.

    If ``side`` is provided it must be +1 for buyer-initiated and -1 for
    seller-initiated trades.  Without side labels the absolute spread is used.
    """
    if side is None:
        trade, mid = _align((trade_price, "trade_price"), (reference_mid, "mid"))
        spread = 2.0 * (trade - mid).abs()
    else:
        trade, mid, signed = _align(
            (trade_price, "trade_price"),
            (reference_mid, "mid"),
            (side, "side"),
        )
        if not signed.isin([-1.0, 1.0]).all():
            raise ValueError("side must contain only -1 and +1")
        spread = 2.0 * signed * (trade - mid)
    if relative:
        if (mid <= 0).any():
            raise ValueError("relative spread requires a positive reference midpoint")
        spread = spread / mid
    return spread.rename("effective_spread")


def realized_spread(
    trade_price: pd.Series | Iterable[float],
    future_mid: pd.Series | Iterable[float],
    side: pd.Series | Iterable[float],
    *,
    relative_to: pd.Series | Iterable[float] | None = None,
) -> pd.Series:
    """Realized spread using a later midpoint and trade-side sign."""
    trade, future, signed = _align(
        (trade_price, "trade_price"),
        (future_mid, "future_mid"),
        (side, "side"),
    )
    if not signed.isin([-1.0, 1.0]).all():
        raise ValueError("side must contain only -1 and +1")
    spread = 2.0 * signed * (trade - future)
    if relative_to is not None:
        ref = _series(relative_to, "relative_to").reindex(spread.index)
        if ref.isna().any() or (ref <= 0).any():
            raise ValueError("relative_to must be aligned and strictly positive")
        spread = spread / ref
    return spread.rename("realized_spread")


def price_impact(
    reference_mid: pd.Series | Iterable[float],
    future_mid: pd.Series | Iterable[float],
    side: pd.Series | Iterable[float],
    *,
    relative: bool = False,
) -> pd.Series:
    """Signed quote movement after a trade, doubled for spread decomposition."""
    mid, future, signed = _align(
        (reference_mid, "mid"),
        (future_mid, "future_mid"),
        (side, "side"),
    )
    if not signed.isin([-1.0, 1.0]).all():
        raise ValueError("side must contain only -1 and +1")
    impact = 2.0 * signed * (future - mid)
    if relative:
        if (mid <= 0).any():
            raise ValueError("relative impact requires a positive midpoint")
        impact = impact / mid
    return impact.rename("price_impact")


def order_flow_imbalance(
    bid: pd.Series | Iterable[float],
    ask: pd.Series | Iterable[float],
    bid_size: pd.Series | Iterable[float],
    ask_size: pd.Series | Iterable[float],
) -> pd.Series:
    """Top-of-book order-flow imbalance from quote and depth changes.

    This follows the standard event-based best-quote construction: bid-side
    additions/improvements contribute positively, while ask-side
    additions/improvements contribute negatively.
    """
    bid_s, ask_s, bid_q, ask_q = _align(
        (bid, "bid"),
        (ask, "ask"),
        (bid_size, "bid_size"),
        (ask_size, "ask_size"),
    )
    _validate_quotes(bid_s, ask_s)
    if (bid_q < 0).any() or (ask_q < 0).any():
        raise ValueError("quote sizes must be non-negative")

    prev_bid = bid_s.shift(1)
    prev_ask = ask_s.shift(1)
    prev_bid_q = bid_q.shift(1)
    prev_ask_q = ask_q.shift(1)

    bid_event = (
        (bid_s >= prev_bid).astype(float) * bid_q
        - (bid_s <= prev_bid).astype(float) * prev_bid_q
    )
    ask_event = (
        (ask_s <= prev_ask).astype(float) * ask_q
        - (ask_s >= prev_ask).astype(float) * prev_ask_q
    )
    return (bid_event - ask_event).fillna(0.0).rename("order_flow_imbalance")


def amihud_illiquidity(
    returns: pd.Series | Iterable[float],
    dollar_volume: pd.Series | Iterable[float],
    *,
    window: int | None = 20,
    scale: float = 1.0,
) -> pd.Series | float:
    """Amihud absolute-return / dollar-volume illiquidity measure."""
    if window is not None and window < 1:
        raise ValueError("window must be positive or None")
    if scale <= 0:
        raise ValueError("scale must be positive")
    r, volume = _align((returns, "return"), (dollar_volume, "dollar_volume"))
    if (volume <= 0).any():
        raise ValueError("dollar_volume must be strictly positive")
    raw = r.abs() / volume * scale
    if window is None:
        return float(raw.mean())
    return raw.rolling(window, min_periods=window).mean().rename("amihud_illiquidity")


def roll_spread(
    prices: pd.Series | Iterable[float],
    *,
    window: int | None = None,
) -> pd.Series | float:
    """Roll implied spread from first-order price-change autocovariance."""
    price = _series(prices, "prices").dropna()
    if len(price) < 3:
        raise ValueError("at least three prices are required")
    changes = price.diff().dropna()

    def estimate(sample: pd.Series) -> float:
        if len(sample) < 2:
            return np.nan
        cov = float(np.cov(sample.iloc[1:], sample.iloc[:-1], ddof=1)[0, 1])
        return float(2.0 * np.sqrt(max(-cov, 0.0)))

    if window is None:
        return estimate(changes)
    if window < 3:
        raise ValueError("window must be at least 3")
    return changes.rolling(window, min_periods=window).apply(
        lambda values: estimate(pd.Series(values)),
        raw=True,
    ).rename("roll_spread")


@dataclass(frozen=True)
class KyleLambdaResult:
    """Linear price-impact regression result."""

    lambda_: float
    intercept: float
    r_squared: float
    observations: int
    fitted: pd.Series
    residuals: pd.Series


def kyle_lambda(
    price_change: pd.Series | Iterable[float],
    signed_flow: pd.Series | Iterable[float],
    *,
    add_constant: bool = True,
) -> KyleLambdaResult:
    """Estimate linear price impact ``Δp = a + λ q + ε`` by OLS."""
    dp, flow = _align((price_change, "price_change"), (signed_flow, "signed_flow"))
    if len(dp) < 3:
        raise ValueError("at least three aligned observations are required")
    if float(flow.std(ddof=0)) <= _EPS:
        raise ValueError("signed_flow must vary")

    x = flow.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x]) if add_constant else x[:, None]
    beta, *_ = np.linalg.lstsq(design, dp.to_numpy(dtype=float), rcond=None)
    if add_constant:
        intercept, lambda_value = float(beta[0]), float(beta[1])
    else:
        intercept, lambda_value = 0.0, float(beta[0])
    fitted_values = design @ beta
    fitted = pd.Series(fitted_values, index=dp.index, name="fitted")
    residuals = (dp - fitted).rename("residual")
    ss_res = float(np.square(residuals).sum())
    centered = dp - dp.mean()
    ss_tot = float(np.square(centered).sum())
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > _EPS else np.nan
    return KyleLambdaResult(
        lambda_=lambda_value,
        intercept=intercept,
        r_squared=float(r_squared),
        observations=len(dp),
        fitted=fitted,
        residuals=residuals,
    )


__all__ = [
    "KyleLambdaResult",
    "amihud_illiquidity",
    "effective_spread",
    "kyle_lambda",
    "microprice",
    "midquote",
    "order_flow_imbalance",
    "price_impact",
    "quoted_spread",
    "realized_spread",
    "roll_spread",
]
