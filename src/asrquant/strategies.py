"""Small, composable strategy constructors that produce target weights."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import as_frame


def _normalize_cross_section(signal: pd.DataFrame, gross: float = 1.0) -> pd.DataFrame:
    denom = signal.abs().sum(axis=1).replace(0.0, np.nan)
    return signal.div(denom, axis=0).fillna(0.0) * gross


def buy_and_hold(prices: pd.Series | pd.DataFrame, gross: float = 1.0) -> pd.DataFrame:
    """Equal-weight buy-and-hold targets."""
    frame = as_frame(prices, "asset")
    return pd.DataFrame(gross / frame.shape[1], index=frame.index, columns=frame.columns)


def sma_crossover(
    prices: pd.Series | pd.DataFrame,
    fast: int = 20,
    slow: int = 100,
    long_short: bool = False,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Moving-average crossover target weights."""
    if fast <= 0 or slow <= fast:
        raise ValueError("require 0 < fast < slow")
    frame = as_frame(prices, "asset")
    fast_ma = frame.rolling(fast, min_periods=fast).mean()
    slow_ma = frame.rolling(slow, min_periods=slow).mean()
    if long_short:
        signal = np.sign(fast_ma - slow_ma)
    else:
        signal = (fast_ma > slow_ma).astype(float)
    return _normalize_cross_section(signal.fillna(0.0), gross=gross)


def momentum(
    prices: pd.Series | pd.DataFrame,
    lookback: int = 126,
    top_fraction: float = 0.2,
    long_short: bool = True,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Cross-sectional momentum weights."""
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if not 0 < top_fraction <= 0.5:
        raise ValueError("top_fraction must be in (0, 0.5]")
    frame = as_frame(prices, "asset")
    score = frame.pct_change(lookback, fill_method=None)
    rank_pct = score.rank(axis=1, pct=True)
    longs = (rank_pct >= 1 - top_fraction).astype(float)
    if long_short:
        shorts = (rank_pct <= top_fraction).astype(float)
        raw = longs - shorts
    else:
        raw = longs
    return _normalize_cross_section(raw.fillna(0.0), gross=gross)


def mean_reversion(
    prices: pd.Series | pd.DataFrame,
    lookback: int = 20,
    z_entry: float = 1.0,
    long_short: bool = True,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Rolling z-score mean-reversion weights."""
    frame = as_frame(prices, "asset")
    mean = frame.rolling(lookback, min_periods=lookback).mean()
    std = frame.rolling(lookback, min_periods=lookback).std(ddof=1).replace(0.0, np.nan)
    z = (frame - mean) / std
    if long_short:
        raw = pd.DataFrame(np.where(z > z_entry, -1.0, np.where(z < -z_entry, 1.0, 0.0)), index=frame.index, columns=frame.columns)
    else:
        raw = (z < -z_entry).astype(float)
    return _normalize_cross_section(raw.fillna(0.0), gross=gross)


def volatility_target(
    prices: pd.Series | pd.DataFrame,
    target_vol: float = 0.10,
    lookback: int = 20,
    annualization: int = 252,
    max_leverage: float = 2.0,
) -> pd.DataFrame:
    """Inverse-volatility weights scaled to an ex-ante volatility target."""
    frame = as_frame(prices, "asset")
    returns = frame.pct_change(fill_method=None)
    vol = returns.rolling(lookback, min_periods=lookback).std(ddof=1) * np.sqrt(annualization)
    inverse = 1.0 / vol.replace(0.0, np.nan)
    base = inverse.div(inverse.sum(axis=1), axis=0).fillna(0.0)
    portfolio_vol_proxy = (base * vol).sum(axis=1).replace(0.0, np.nan)
    scale = (target_vol / portfolio_vol_proxy).clip(upper=max_leverage).fillna(0.0)
    return base.mul(scale, axis=0)


def breakout(
    prices: pd.Series | pd.DataFrame,
    lookback: int = 55,
    exit_lookback: int = 20,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Donchian-style long/short breakout targets."""
    if lookback <= exit_lookback or exit_lookback <= 0:
        raise ValueError("require lookback > exit_lookback > 0")
    frame = as_frame(prices, "asset")
    upper = frame.shift(1).rolling(lookback).max(); lower = frame.shift(1).rolling(lookback).min()
    exit_high = frame.shift(1).rolling(exit_lookback).max(); exit_low = frame.shift(1).rolling(exit_lookback).min()
    state = pd.DataFrame(0.0, index=frame.index, columns=frame.columns)
    for t in range(1, len(frame)):
        previous = state.iloc[t-1].copy(); current = frame.iloc[t]
        long_entry = current > upper.iloc[t]; short_entry = current < lower.iloc[t]
        long_exit = (previous > 0) & (current < exit_low.iloc[t]); short_exit = (previous < 0) & (current > exit_high.iloc[t])
        previous[long_exit | short_exit] = 0.0; previous[long_entry] = 1.0; previous[short_entry] = -1.0
        state.iloc[t] = previous
    return _normalize_cross_section(state, gross=gross)


def bollinger_mean_reversion(
    prices: pd.Series | pd.DataFrame,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Stateful Bollinger-band mean-reversion strategy."""
    if window <= 1 or entry_z <= exit_z or exit_z < 0:
        raise ValueError("require window>1 and entry_z>exit_z>=0")
    frame = as_frame(prices, "asset")
    mean = frame.rolling(window).mean(); std = frame.rolling(window).std(ddof=1).replace(0,np.nan); z=(frame-mean)/std
    state = pd.DataFrame(0.0, index=frame.index, columns=frame.columns)
    for t in range(1,len(frame)):
        previous=state.iloc[t-1].copy(); current=z.iloc[t]
        previous[(previous>0)&(current>=-exit_z)] = 0; previous[(previous<0)&(current<=exit_z)] = 0
        previous[current<=-entry_z]=1; previous[current>=entry_z]=-1; state.iloc[t]=previous
    return _normalize_cross_section(state, gross=gross)


def rsi_strategy(
    prices: pd.Series | pd.DataFrame,
    window: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Cross-sectional RSI threshold strategy."""
    if not 0 < oversold < overbought < 100:
        raise ValueError("require 0 < oversold < overbought < 100")
    frame=as_frame(prices,"asset"); delta=frame.diff(); gain=delta.clip(lower=0).rolling(window).mean(); loss=-delta.clip(upper=0).rolling(window).mean()
    rsi=100-100/(1+gain/loss.replace(0,np.nan)); raw=pd.DataFrame(np.where(rsi<oversold,1,np.where(rsi>overbought,-1,0)),index=frame.index,columns=frame.columns)
    return _normalize_cross_section(raw,gross=gross)


def pairs_zscore(
    prices: pd.Series | pd.DataFrame,
    asset_a: str | None = None,
    asset_b: str | None = None,
    lookback: int = 60,
    entry_z: float = 2.0,
    gross: float = 1.0,
) -> pd.DataFrame:
    """Two-asset log-spread z-score strategy with rolling hedge ratio."""
    frame=as_frame(prices,"asset")
    if frame.shape[1] < 2:
        raise ValueError("pairs strategy requires at least two assets")
    a=asset_a or frame.columns[0]; b=asset_b or frame.columns[1]
    log_a=np.log(frame[a]); log_b=np.log(frame[b]); cov=log_a.rolling(lookback).cov(log_b); var=log_b.rolling(lookback).var().replace(0,np.nan); beta=cov/var
    spread=log_a-beta*log_b; z=(spread-spread.rolling(lookback).mean())/spread.rolling(lookback).std(ddof=1)
    weights=pd.DataFrame(0.0,index=frame.index,columns=frame.columns)
    weights.loc[z>entry_z,a]=-1; weights.loc[z>entry_z,b]=beta[z>entry_z]
    weights.loc[z<-entry_z,a]=1; weights.loc[z<-entry_z,b]=-beta[z<-entry_z]
    return _normalize_cross_section(weights.fillna(0),gross=gross)
