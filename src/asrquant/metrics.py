"""Performance, risk, benchmark, and statistical-quality metrics."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


def _series(returns: pd.Series | Iterable[float]) -> pd.Series:
    out = pd.Series(returns, dtype=float).dropna()
    if out.empty:
        raise ValueError("returns are empty")
    return out


def cumulative_returns(returns: pd.Series | Iterable[float]) -> pd.Series:
    r = _series(returns)
    return (1.0 + r).cumprod() - 1.0


def annualized_return(returns: pd.Series | Iterable[float], annualization: int = 252) -> float:
    r = _series(returns)
    growth = float(np.prod(1.0 + r))
    if growth <= 0:
        return -1.0
    return growth ** (annualization / len(r)) - 1.0


def annualized_volatility(returns: pd.Series | Iterable[float], annualization: int = 252) -> float:
    value = float(_series(returns).std(ddof=1) * np.sqrt(annualization))
    return 0.0 if abs(value) < 1e-15 else value


def sharpe_ratio(
    returns: pd.Series | Iterable[float],
    risk_free_rate: float = 0.0,
    annualization: int = 252,
) -> float:
    r = _series(returns)
    excess = r - risk_free_rate / annualization
    vol = float(excess.std(ddof=1))
    return float(np.sqrt(annualization) * excess.mean() / vol) if vol > 1e-15 else np.nan


def sortino_ratio(
    returns: pd.Series | Iterable[float],
    target: float = 0.0,
    annualization: int = 252,
) -> float:
    r = _series(returns)
    downside = np.minimum(r - target / annualization, 0.0)
    downside_dev = float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(annualization))
    numerator = float((r.mean() - target / annualization) * annualization)
    return numerator / downside_dev if downside_dev > 0 else np.nan


def drawdown_series(returns: pd.Series | Iterable[float]) -> pd.Series:
    r = _series(returns)
    wealth = (1.0 + r).cumprod()
    peak = wealth.cummax()
    return wealth / peak - 1.0


def max_drawdown(returns: pd.Series | Iterable[float]) -> float:
    return float(drawdown_series(returns).min())


def calmar_ratio(returns: pd.Series | Iterable[float], annualization: int = 252) -> float:
    mdd = abs(max_drawdown(returns))
    return annualized_return(returns, annualization) / mdd if mdd > 0 else np.nan


def omega_ratio(returns: pd.Series | Iterable[float], threshold: float = 0.0) -> float:
    r = _series(returns) - threshold
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    return gains / losses if losses > 0 else np.nan


def value_at_risk(returns: pd.Series | Iterable[float], level: float = 0.95) -> float:
    if not 0 < level < 1:
        raise ValueError("level must be between 0 and 1")
    return float(-_series(returns).quantile(1 - level))


def expected_shortfall(returns: pd.Series | Iterable[float], level: float = 0.95) -> float:
    r = _series(returns)
    cutoff = r.quantile(1 - level)
    tail = r[r <= cutoff]
    return float(-tail.mean()) if not tail.empty else np.nan


def ulcer_index(returns: pd.Series | Iterable[float]) -> float:
    dd = drawdown_series(returns)
    return float(np.sqrt(np.mean(np.square(dd))))


def tail_ratio(returns: pd.Series | Iterable[float], quantile: float = 0.95) -> float:
    r = _series(returns)
    upper = float(r.quantile(quantile))
    lower = abs(float(r.quantile(1 - quantile)))
    return upper / lower if lower > 0 else np.nan


def hit_rate(returns: pd.Series | Iterable[float]) -> float:
    r = _series(returns)
    nonzero = r[r != 0]
    return float((nonzero > 0).mean()) if len(nonzero) else np.nan


def profit_factor(returns: pd.Series | Iterable[float]) -> float:
    r = _series(returns)
    gross_profit = float(r[r > 0].sum())
    gross_loss = abs(float(r[r < 0].sum()))
    return gross_profit / gross_loss if gross_loss > 0 else np.nan


def tracking_error(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    annualization: int = 252,
) -> float:
    r, b = pd.concat([_series(returns), _series(benchmark)], axis=1).dropna().T.values
    return float(np.std(r - b, ddof=1) * np.sqrt(annualization))


def information_ratio(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    annualization: int = 252,
) -> float:
    r = _series(returns)
    b = _series(benchmark)
    aligned = pd.concat([r, b], axis=1).dropna()
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = active.std(ddof=1) * np.sqrt(annualization)
    return float(active.mean() * annualization / te) if te > 0 else np.nan


def alpha_beta(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    risk_free_rate: float = 0.0,
    annualization: int = 252,
) -> tuple[float, float]:
    aligned = pd.concat([_series(returns), _series(benchmark)], axis=1).dropna()
    y = aligned.iloc[:, 0] - risk_free_rate / annualization
    x = aligned.iloc[:, 1] - risk_free_rate / annualization
    if x.var(ddof=1) == 0:
        return np.nan, np.nan
    beta = float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))
    alpha = float((y.mean() - beta * x.mean()) * annualization)
    return alpha, beta


def probabilistic_sharpe_ratio(
    returns: pd.Series | Iterable[float],
    benchmark_sharpe: float = 0.0,
    annualization: int = 252,
) -> float:
    """Approximate probability that the population Sharpe exceeds a benchmark."""
    r = _series(returns)
    n = len(r)
    if n < 3:
        return np.nan
    sr = sharpe_ratio(r, annualization=annualization)
    skew = stats.skew(r, bias=False)
    kurt = stats.kurtosis(r, fisher=False, bias=False)
    denom = np.sqrt(max(1e-12, 1 - skew * sr + ((kurt - 1) / 4) * sr**2))
    z = (sr - benchmark_sharpe) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe_ratio(
    returns: pd.Series | Iterable[float],
    trials: int = 1,
    annualization: int = 252,
) -> float:
    """Approximate DSR using the expected maximum Sharpe under multiple trials."""
    if trials < 1:
        raise ValueError("trials must be >= 1")
    r = _series(returns)
    if trials == 1:
        benchmark = 0.0
    else:
        euler_gamma = 0.5772156649
        z1 = stats.norm.ppf(1 - 1 / trials)
        z2 = stats.norm.ppf(1 - 1 / (trials * np.e))
        sr_std = 1 / np.sqrt(max(len(r) - 1, 1))
        benchmark = sr_std * ((1 - euler_gamma) * z1 + euler_gamma * z2)
    return probabilistic_sharpe_ratio(r, benchmark, annualization)


def summary_metrics(
    returns: pd.Series | Iterable[float],
    annualization: int = 252,
    risk_free_rate: float = 0.0,
    benchmark: pd.Series | Iterable[float] | None = None,
    turnover: pd.Series | Iterable[float] | None = None,
) -> pd.Series:
    r = _series(returns)
    metrics: dict[str, float] = {
        "Total Return": float((1 + r).prod() - 1),
        "CAGR": annualized_return(r, annualization),
        "Annual Volatility": annualized_volatility(r, annualization),
        "Sharpe": sharpe_ratio(r, risk_free_rate, annualization),
        "Sortino": sortino_ratio(r, risk_free_rate, annualization),
        "Max Drawdown": max_drawdown(r),
        "Calmar": calmar_ratio(r, annualization),
        "Omega": omega_ratio(r),
        "VaR 95%": value_at_risk(r, 0.95),
        "ES 95%": expected_shortfall(r, 0.95),
        "Ulcer Index": ulcer_index(r),
        "CDaR 95%": conditional_drawdown_at_risk(r, 0.95),
        "Max Drawdown Duration": float(drawdown_duration(r).max()),
        "Kelly Fraction": kelly_fraction(r),
        "Gaussian VaR 95%": parametric_var(r, 0.95, "gaussian"),
        "Cornish-Fisher VaR 95%": parametric_var(r, 0.95, "cornish_fisher"),
        "Tail Ratio": tail_ratio(r),
        "Hit Rate": hit_rate(r),
        "Profit Factor": profit_factor(r),
        "Skew": float(stats.skew(r, bias=False)),
        "Excess Kurtosis": float(stats.kurtosis(r, fisher=True, bias=False)),
        "PSR": probabilistic_sharpe_ratio(r, 0.0, annualization),
    }
    if turnover is not None:
        t = _series(turnover)
        metrics["Average Turnover"] = float(t.mean())
        metrics["Annual Turnover"] = float(t.mean() * annualization)
    if benchmark is not None:
        alpha, beta = alpha_beta(r, benchmark, risk_free_rate, annualization)
        metrics.update(
            {
                "Alpha": alpha,
                "Beta": beta,
                "Tracking Error": tracking_error(r, benchmark, annualization),
                "Information Ratio": information_ratio(r, benchmark, annualization),
            }
        )
    return pd.Series(metrics, name="value")


def parametric_var(
    returns: pd.Series | Iterable[float],
    level: float = 0.95,
    method: str = "gaussian",
) -> float:
    """Gaussian or Cornish-Fisher one-period Value at Risk."""
    r = _series(returns)
    z = stats.norm.ppf(1 - level)
    if method.lower() in {"cornish_fisher", "cornish-fisher", "cf"}:
        skew = stats.skew(r, bias=False)
        kurt = stats.kurtosis(r, fisher=True, bias=False)
        z = z + (z**2 - 1) * skew / 6 + (z**3 - 3*z) * kurt / 24 - (2*z**3 - 5*z) * skew**2 / 36
    elif method.lower() not in {"gaussian", "normal"}:
        raise ValueError("method must be gaussian or cornish_fisher")
    return float(-(r.mean() + z * r.std(ddof=1)))


def conditional_drawdown_at_risk(returns: pd.Series | Iterable[float], level: float = 0.95) -> float:
    """Average of drawdowns beyond the selected drawdown quantile."""
    dd = drawdown_series(returns)
    cutoff = dd.quantile(1 - level)
    tail = dd[dd <= cutoff]
    return float(-tail.mean()) if len(tail) else np.nan


def drawdown_duration(returns: pd.Series | Iterable[float]) -> pd.Series:
    """Number of consecutive periods spent below the previous wealth peak."""
    dd = drawdown_series(returns)
    durations = np.zeros(len(dd), dtype=int)
    for i in range(1, len(dd)):
        durations[i] = durations[i - 1] + 1 if dd.iloc[i] < 0 else 0
    return pd.Series(durations, index=dd.index, name="drawdown_duration")


def kelly_fraction(returns: pd.Series | Iterable[float], max_leverage: float | None = None) -> float:
    """Mean-variance approximation to the growth-optimal fraction."""
    r = _series(returns)
    variance = r.var(ddof=1)
    value = float(r.mean() / variance) if variance > 0 else np.nan
    if max_leverage is not None and np.isfinite(value):
        value = float(np.clip(value, -max_leverage, max_leverage))
    return value


def treynor_ratio(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    risk_free_rate: float = 0.0,
    annualization: int = 252,
) -> float:
    """Annualized excess return per unit of market beta."""
    _, beta = alpha_beta(returns, benchmark, risk_free_rate, annualization)
    excess = annualized_return(returns, annualization) - risk_free_rate
    return float(excess / beta) if beta not in {0, np.nan} and np.isfinite(beta) else np.nan


def m_squared(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    risk_free_rate: float = 0.0,
    annualization: int = 252,
) -> float:
    """Modigliani-Modigliani risk-adjusted performance."""
    benchmark_vol = annualized_volatility(benchmark, annualization)
    return float(risk_free_rate + sharpe_ratio(returns, risk_free_rate, annualization) * benchmark_vol)


def capture_ratio(
    returns: pd.Series | Iterable[float],
    benchmark: pd.Series | Iterable[float],
    annualization: int = 252,
) -> pd.Series:
    """Upside, downside, and upside/downside capture ratios."""
    aligned = pd.concat([_series(returns), _series(benchmark)], axis=1).dropna()
    r, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    up = b > 0; down = b < 0
    up_capture = annualized_return(r[up], annualization) / annualized_return(b[up], annualization) if up.any() else np.nan
    down_capture = annualized_return(r[down], annualization) / annualized_return(b[down], annualization) if down.any() else np.nan
    return pd.Series({"upside_capture": up_capture, "downside_capture": down_capture, "capture_ratio": up_capture / down_capture if down_capture not in {0, np.nan} else np.nan})
