"""Realized, conditional, and implied-volatility utilities."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VolatilityForecast:
    model: str
    conditional_volatility: pd.Series
    forecast: pd.Series
    model_result: object | None = None

    def plot(self):
        from .viz.market import rolling_statistics
        return rolling_statistics(self.conditional_volatility / np.sqrt(252), window=1)


def realized_volatility(returns: pd.Series, window: int = 21, annualization: int = 252) -> pd.Series:
    """Rolling close-to-close realized volatility."""
    r = pd.Series(returns, dtype=float)
    return (r.rolling(window).std(ddof=1) * np.sqrt(annualization)).rename("realized_volatility")


def parkinson_volatility(high: pd.Series, low: pd.Series, window: int = 21, annualization: int = 252) -> pd.Series:
    """Rolling Parkinson high-low volatility estimator."""
    h = pd.Series(high, dtype=float); l = pd.Series(low, dtype=float)
    log_range_sq = np.log(h/l) ** 2
    return np.sqrt(log_range_sq.rolling(window).mean() * annualization / (4*np.log(2))).rename("parkinson_volatility")


def garman_klass_volatility(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, window: int = 21, annualization: int = 252) -> pd.Series:
    """Rolling Garman-Klass OHLC volatility estimator."""
    o,h,l,c = map(lambda x: pd.Series(x, dtype=float), (open_, high, low, close))
    variance = 0.5*np.log(h/l)**2 - (2*np.log(2)-1)*np.log(c/o)**2
    return np.sqrt(variance.clip(lower=0).rolling(window).mean()*annualization).rename("garman_klass_volatility")


def ewma_volatility(returns: pd.Series, decay: float = 0.94, annualization: int = 252) -> pd.Series:
    """RiskMetrics-style exponentially weighted volatility."""
    if not 0 < decay < 1:
        raise ValueError("decay must lie in (0, 1)")
    r = pd.Series(returns, dtype=float)
    variance = r.pow(2).ewm(alpha=1-decay, adjust=False).mean()
    return np.sqrt(variance*annualization).rename("ewma_volatility")


def garch_forecast(
    returns: pd.Series,
    p: int = 1,
    q: int = 1,
    horizon: int = 5,
    distribution: str = "t",
    annualization: int = 252,
) -> VolatilityForecast:
    """Fit GARCH(p,q) through the optional ``arch`` dependency."""
    try:
        from arch import arch_model
    except ImportError as exc:
        raise ImportError("install ASRQuant with `pip install asrquant[volatility]`") from exc
    r = pd.Series(returns, dtype=float).dropna() * 100
    model = arch_model(r, mean="Constant", vol="GARCH", p=p, q=q, dist=distribution)
    fitted = model.fit(disp="off")
    conditional = pd.Series(fitted.conditional_volatility / 100 * np.sqrt(annualization), index=r.index, name="conditional_volatility")
    variance = fitted.forecast(horizon=horizon).variance.iloc[-1].to_numpy() / 10_000 * annualization
    forecast = pd.Series(np.sqrt(variance), index=pd.RangeIndex(1, horizon+1, name="horizon"), name="forecast_volatility")
    return VolatilityForecast(f"GARCH({p},{q})", conditional, forecast, fitted)
