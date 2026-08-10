"""Closed-form, tree, and Monte Carlo derivative analytics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm


@dataclass
class OptionPrice:
    """Standard option-pricing response."""

    price: float
    model: str
    greeks: dict[str, float] | None = None
    standard_error: float | None = None
    confidence_interval: tuple[float, float] | None = None

    @property
    def summary(self) -> pd.Series:
        values = {"price": self.price, "model": self.model}
        if self.standard_error is not None:
            values["standard_error"] = self.standard_error
        if self.confidence_interval is not None:
            values["ci_lower"], values["ci_upper"] = self.confidence_interval
        if self.greeks:
            values.update(self.greeks)
        return pd.Series(values)


def _validate_option_inputs(spot, strike, maturity, volatility=None) -> None:
    if np.any(np.asarray(spot, dtype=float) <= 0) or np.any(np.asarray(strike, dtype=float) <= 0):
        raise ValueError("spot and strike must be positive")
    if np.any(np.asarray(maturity, dtype=float) <= 0):
        raise ValueError("maturity must be positive")
    if volatility is not None and np.any(np.asarray(volatility, dtype=float) <= 0):
        raise ValueError("volatility must be positive")


def black_scholes_price(
    spot: float | np.ndarray,
    strike: float | np.ndarray,
    maturity: float | np.ndarray,
    rate: float,
    volatility: float | np.ndarray,
    option: str = "call",
    dividend: float = 0.0,
):
    """Black-Scholes-Merton European option value."""
    _validate_option_inputs(spot, strike, maturity, volatility)
    s = np.asarray(spot, dtype=float); k = np.asarray(strike, dtype=float)
    t = np.asarray(maturity, dtype=float); sigma = np.asarray(volatility, dtype=float)
    d1 = (np.log(s / k) + (rate - dividend + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    call = s * np.exp(-dividend * t) * norm.cdf(d1) - k * np.exp(-rate * t) * norm.cdf(d2)
    if option.lower() == "call":
        return call
    if option.lower() == "put":
        return call - s * np.exp(-dividend * t) + k * np.exp(-rate * t)
    raise ValueError("option must be 'call' or 'put'")


def black_scholes_greeks(
    spot: float | np.ndarray,
    strike: float | np.ndarray,
    maturity: float | np.ndarray,
    rate: float,
    volatility: float | np.ndarray,
    option: str = "call",
    dividend: float = 0.0,
) -> dict[str, np.ndarray]:
    """Return analytic delta, gamma, vega, theta, and rho."""
    _validate_option_inputs(spot, strike, maturity, volatility)
    s = np.asarray(spot, dtype=float); k = np.asarray(strike, dtype=float)
    t = np.asarray(maturity, dtype=float); sigma = np.asarray(volatility, dtype=float)
    d1 = (np.log(s / k) + (rate - dividend + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t)); d2 = d1 - sigma * np.sqrt(t)
    disc_q = np.exp(-dividend * t); disc_r = np.exp(-rate * t)
    gamma = disc_q * norm.pdf(d1) / (s * sigma * np.sqrt(t)); vega = s * disc_q * norm.pdf(d1) * np.sqrt(t)
    if option.lower() == "call":
        delta = disc_q * norm.cdf(d1)
        theta = -(s * disc_q * norm.pdf(d1) * sigma) / (2 * np.sqrt(t)) - rate * k * disc_r * norm.cdf(d2) + dividend * s * disc_q * norm.cdf(d1)
        rho = k * t * disc_r * norm.cdf(d2)
    elif option.lower() == "put":
        delta = disc_q * (norm.cdf(d1) - 1)
        theta = -(s * disc_q * norm.pdf(d1) * sigma) / (2 * np.sqrt(t)) + rate * k * disc_r * norm.cdf(-d2) - dividend * s * disc_q * norm.cdf(-d1)
        rho = -k * t * disc_r * norm.cdf(-d2)
    else:
        raise ValueError("option must be 'call' or 'put'")
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


def bachelier_price(
    forward: float | np.ndarray,
    strike: float | np.ndarray,
    maturity: float | np.ndarray,
    normal_volatility: float | np.ndarray,
    option: str = "call",
    discount: float | np.ndarray = 1.0,
):
    """Bachelier/normal-model European option value."""
    f = np.asarray(forward, dtype=float); k = np.asarray(strike, dtype=float)
    t = np.asarray(maturity, dtype=float); sigma_n = np.asarray(normal_volatility, dtype=float)
    if np.any(t <= 0) or np.any(sigma_n <= 0) or np.any(np.asarray(discount) <= 0):
        raise ValueError("maturity, normal volatility, and discount must be positive")
    scale = sigma_n * np.sqrt(t); d = (f - k) / scale
    call = np.asarray(discount) * ((f - k) * norm.cdf(d) + scale * norm.pdf(d))
    if option.lower() == "call":
        return call
    if option.lower() == "put":
        return call - np.asarray(discount) * (f - k)
    raise ValueError("option must be call or put")


def bachelier_greeks(
    forward: float | np.ndarray,
    strike: float | np.ndarray,
    maturity: float | np.ndarray,
    normal_volatility: float | np.ndarray,
    option: str = "call",
    discount: float | np.ndarray = 1.0,
) -> dict[str, np.ndarray]:
    """Forward delta, gamma, vega, and theta for the Bachelier model."""
    f = np.asarray(forward, dtype=float); k = np.asarray(strike, dtype=float)
    t = np.asarray(maturity, dtype=float); sigma = np.asarray(normal_volatility, dtype=float)
    disc = np.asarray(discount, dtype=float); scale = sigma * np.sqrt(t); d = (f-k)/scale
    call_delta = disc * norm.cdf(d)
    delta = call_delta if option.lower() == "call" else call_delta - disc
    gamma = disc * norm.pdf(d) / scale
    vega = disc * np.sqrt(t) * norm.pdf(d)
    theta = -disc * sigma * norm.pdf(d) / (2 * np.sqrt(t))
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def black76_price(
    forward: float | np.ndarray,
    strike: float | np.ndarray,
    maturity: float | np.ndarray,
    rate: float,
    volatility: float | np.ndarray,
    option: str = "call",
):
    """Black-76 European option on a forward or futures price."""
    _validate_option_inputs(forward, strike, maturity, volatility)
    f = np.asarray(forward, dtype=float); k = np.asarray(strike, dtype=float)
    t = np.asarray(maturity, dtype=float); sigma = np.asarray(volatility, dtype=float)
    d1 = (np.log(f/k) + 0.5*sigma**2*t)/(sigma*np.sqrt(t)); d2 = d1 - sigma*np.sqrt(t)
    disc = np.exp(-rate*t)
    call = disc * (f*norm.cdf(d1)-k*norm.cdf(d2))
    if option.lower() == "call":
        return call
    if option.lower() == "put":
        return call - disc*(f-k)
    raise ValueError("option must be call or put")


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    option: str = "call",
    dividend: float = 0.0,
    model: str = "black_scholes",
) -> float:
    """Invert Black-Scholes-Merton, Black-76, or Bachelier by bracketing."""
    if market_price <= 0:
        raise ValueError("market_price must be positive")
    key = model.lower().replace("-", "_")
    if key in {"black_scholes", "bsm"}:
        objective = lambda sigma: float(black_scholes_price(spot, strike, maturity, rate, sigma, option, dividend) - market_price)
        low, high = 1e-8, 10.0
    elif key in {"black76", "black_76"}:
        objective = lambda sigma: float(black76_price(spot, strike, maturity, rate, sigma, option) - market_price)
        low, high = 1e-8, 10.0
    elif key in {"bachelier", "normal"}:
        objective = lambda sigma: float(bachelier_price(spot, strike, maturity, sigma, option, np.exp(-rate*maturity)) - market_price)
        low, high = 1e-10, max(spot, strike) * 100
    else:
        raise ValueError("model must be black_scholes, black76, or bachelier")
    try:
        return float(brentq(objective, low, high, maxiter=300))
    except ValueError as exc:
        raise ValueError("market price is outside the model's invertible range") from exc


def option_payoff(
    terminal_price: np.ndarray | pd.Series,
    strike: float,
    option: str = "call",
    premium: float = 0.0,
    position: float = 1.0,
) -> np.ndarray:
    """European option payoff net of premium."""
    s = np.asarray(terminal_price, dtype=float)
    if option.lower() == "call":
        intrinsic = np.maximum(s-strike, 0.0)
    elif option.lower() == "put":
        intrinsic = np.maximum(strike-s, 0.0)
    else:
        raise ValueError("option must be call or put")
    return position * (intrinsic-premium)


def put_call_parity_error(call: float, put: float, spot: float, strike: float, maturity: float, rate: float, dividend: float = 0.0) -> float:
    """Return C-P-[S exp(-qT)-K exp(-rT)]."""
    return float(call-put-(spot*np.exp(-dividend*maturity)-strike*np.exp(-rate*maturity)))


def crr_binomial_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    option: str = "call",
    steps: int = 500,
    dividend: float = 0.0,
    american: bool = False,
) -> float:
    """Cox-Ross-Rubinstein binomial price for European or American options."""
    _validate_option_inputs(spot, strike, maturity, volatility)
    if steps <= 0:
        raise ValueError("steps must be positive")
    dt = maturity/steps; u = np.exp(volatility*np.sqrt(dt)); d = 1/u
    p = (np.exp((rate-dividend)*dt)-d)/(u-d)
    if not 0 <= p <= 1:
        raise ValueError("risk-neutral probability is outside [0,1]")
    if option.lower() not in {"call", "put"}:
        raise ValueError("option must be call or put")
    j = np.arange(steps+1); terminal = spot * u**j * d**(steps-j)
    values = np.maximum(terminal-strike, 0.0) if option.lower()=="call" else np.maximum(strike-terminal, 0.0)
    disc = np.exp(-rate*dt)
    for n in range(steps-1, -1, -1):
        values = disc * (p*values[1:n+2] + (1-p)*values[:n+1])
        if american:
            j = np.arange(n+1); nodes = spot*u**j*d**(n-j)
            exercise = np.maximum(nodes-strike, 0.0) if option.lower()=="call" else np.maximum(strike-nodes, 0.0)
            values = np.maximum(values, exercise)
    return float(values[0])


def finite_difference_greeks(
    pricer: Callable[..., float],
    *,
    spot: float,
    volatility: float,
    rate: float,
    spot_step: float | None = None,
    vol_step: float = 1e-4,
    rate_step: float = 1e-4,
    **kwargs,
) -> dict[str, float]:
    """Generic central finite-difference delta, gamma, vega, and rho."""
    h = spot_step or max(1e-4, spot*1e-4)
    base_kwargs = dict(kwargs)
    up = pricer(spot=spot+h, volatility=volatility, rate=rate, **base_kwargs)
    mid = pricer(spot=spot, volatility=volatility, rate=rate, **base_kwargs)
    down = pricer(spot=spot-h, volatility=volatility, rate=rate, **base_kwargs)
    delta = (up-down)/(2*h); gamma = (up-2*mid+down)/(h*h)
    vega = (pricer(spot=spot, volatility=volatility+vol_step, rate=rate, **base_kwargs)-pricer(spot=spot, volatility=volatility-vol_step, rate=rate, **base_kwargs))/(2*vol_step)
    rho = (pricer(spot=spot, volatility=volatility, rate=rate+rate_step, **base_kwargs)-pricer(spot=spot, volatility=volatility, rate=rate-rate_step, **base_kwargs))/(2*rate_step)
    return {"delta": float(delta), "gamma": float(gamma), "vega": float(vega), "rho": float(rho)}


def price_option(model: str = "black_scholes", **kwargs) -> OptionPrice:
    """Unified option-pricing dispatcher returning a standard result object."""
    key = model.lower().replace("-", "_")
    if key in {"black_scholes", "bsm"}:
        price = float(black_scholes_price(**kwargs)); greeks = {k: float(np.asarray(v)) for k,v in black_scholes_greeks(**kwargs).items()}
        return OptionPrice(price, "black_scholes", greeks)
    if key in {"bachelier", "normal"}:
        normal_kwargs = dict(kwargs)
        rate = normal_kwargs.pop("rate", None)
        if rate is not None and "discount" not in normal_kwargs:
            normal_kwargs["discount"] = float(np.exp(-float(rate) * float(normal_kwargs["maturity"])))
        price = float(bachelier_price(**normal_kwargs))
        greeks = {
            name: float(np.asarray(value))
            for name, value in bachelier_greeks(**normal_kwargs).items()
        }
        return OptionPrice(price, "bachelier", greeks)
    if key in {"black76", "black_76"}:
        return OptionPrice(float(black76_price(**kwargs)), "black76")
    if key in {"binomial", "crr"}:
        return OptionPrice(float(crr_binomial_price(**kwargs)), "crr_binomial")
    if key in {"monte_carlo", "mc"}:
        from .simulation import european_option_mc
        result = european_option_mc(**kwargs)
        return OptionPrice(result.price, "monte_carlo_gbm", standard_error=result.standard_error, confidence_interval=result.confidence_interval)
    if key in {"asian_monte_carlo", "asian_mc"}:
        from .simulation import asian_option_mc
        result = asian_option_mc(**kwargs)
        return OptionPrice(result.price, "asian_monte_carlo_gbm", standard_error=result.standard_error, confidence_interval=result.confidence_interval)
    raise ValueError("unknown model")


# Backward-compatible helper retained.
def simulate_gbm(spot: float, drift: float, volatility: float, maturity: float, steps: int = 252, paths: int = 1_000, random_state: int | None = 0) -> pd.DataFrame:
    from .simulation import geometric_brownian_motion
    return geometric_brownian_motion(spot, drift, volatility, maturity, steps, paths, random_state).paths
