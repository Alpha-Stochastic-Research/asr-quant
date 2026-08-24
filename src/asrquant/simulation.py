"""Stochastic processes, synthetic markets, bootstrap, and Monte Carlo pricing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class SimulationResult:
    """Container for simulated paths with summaries and plotting helpers."""

    paths: pd.DataFrame
    model: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def terminal(self) -> pd.Series:
        return self.paths.iloc[-1].rename("terminal")

    @property
    def summary(self) -> pd.Series:
        terminal = self.terminal
        return pd.Series(
            {
                "paths": self.paths.shape[1],
                "steps": self.paths.shape[0] - 1,
                "terminal_mean": terminal.mean(),
                "terminal_std": terminal.std(ddof=1),
                "terminal_median": terminal.median(),
                "terminal_q05": terminal.quantile(0.05),
                "terminal_q95": terminal.quantile(0.95),
            }
        )

    def plot(self, kind: str = "paths", **kwargs):
        from .viz import simulation as viz
        if kind in {"paths", "path"}:
            return viz.paths(self, **kwargs)
        if kind in {"terminal", "distribution"}:
            return viz.terminal_distribution(self, **kwargs)
        if kind in {"fan", "monte_carlo_fan"}:
            from .viz.risk import monte_carlo_fan
            return monte_carlo_fan(self.paths, **kwargs)
        raise ValueError("kind must be paths, terminal, or fan")


@dataclass
class MonteCarloPriceResult:
    """Monte Carlo price estimate with uncertainty and raw discounted payoffs."""

    price: float
    standard_error: float
    confidence_interval: tuple[float, float]
    discounted_payoffs: np.ndarray
    simulation: SimulationResult
    confidence: float = 0.95

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "price": self.price,
                "standard_error": self.standard_error,
                "ci_lower": self.confidence_interval[0],
                "ci_upper": self.confidence_interval[1],
                "confidence": self.confidence,
                "paths": len(self.discounted_payoffs),
            }
        )


def _validate_inputs(initial: float, volatility: float, maturity: float, steps: int, paths: int) -> None:
    if initial <= 0 or maturity <= 0 or steps <= 0 or paths <= 0:
        raise ValueError("initial, maturity, steps, and paths must be positive")
    if volatility < 0:
        raise ValueError("volatility must be non-negative")


def arithmetic_brownian_motion(
    initial: float = 100.0,
    drift: float = 0.0,
    volatility: float = 0.2,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate arithmetic Brownian motion X_t=X_0+mu*t+sigma*W_t."""
    _validate_inputs(initial, volatility, maturity, steps, paths)
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    increments = drift * dt + volatility * np.sqrt(dt) * rng.standard_normal((steps, paths))
    values = np.vstack([np.full(paths, initial), initial + np.cumsum(increments, axis=0)])
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "abm", {"initial": initial, "drift": drift, "volatility": volatility, "maturity": maturity, "steps": steps, "paths": paths, "random_state": random_state})


def geometric_brownian_motion(
    initial: float = 100.0,
    drift: float = 0.05,
    volatility: float = 0.2,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
    antithetic: bool = False,
) -> SimulationResult:
    """Simulate exact-discretization geometric Brownian motion paths."""
    _validate_inputs(initial, volatility, maturity, steps, paths)
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    if antithetic:
        half = (paths + 1) // 2
        z_half = rng.standard_normal((steps, half))
        z = np.concatenate([z_half, -z_half], axis=1)[:, :paths]
    else:
        z = rng.standard_normal((steps, paths))
    log_inc = (drift - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z
    values = initial * np.exp(np.vstack([np.zeros(paths), np.cumsum(log_inc, axis=0)]))
    params = {"initial": initial, "drift": drift, "volatility": volatility, "maturity": maturity, "steps": steps, "paths": paths, "random_state": random_state, "antithetic": antithetic}
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "gbm", params)


def correlated_gbm(
    initials: np.ndarray | list[float],
    drifts: np.ndarray | list[float],
    volatilities: np.ndarray | list[float],
    correlation: np.ndarray,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> np.ndarray:
    """Simulate correlated GBM with shape (steps+1, paths, assets)."""
    s0 = np.asarray(initials, dtype=float)
    mu = np.asarray(drifts, dtype=float)
    sigma = np.asarray(volatilities, dtype=float)
    corr = np.asarray(correlation, dtype=float)
    n = len(s0)
    if mu.shape != (n,) or sigma.shape != (n,) or corr.shape != (n, n):
        raise ValueError("incompatible parameter dimensions")
    if np.any(np.linalg.eigvalsh(corr) < -1e-10):
        raise ValueError("correlation matrix must be positive semidefinite")
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    chol = np.linalg.cholesky(corr + np.eye(n) * 1e-12)
    z = rng.standard_normal((steps, paths, n)) @ chol.T
    inc = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.concatenate([np.zeros((1, paths, n)), np.cumsum(inc, axis=0)], axis=0)
    return s0 * np.exp(log_paths)


def ornstein_uhlenbeck(
    initial: float = 0.0,
    speed: float = 2.0,
    mean: float = 0.0,
    volatility: float = 0.2,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate an Ornstein-Uhlenbeck mean-reverting process by Euler steps."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    _validate_inputs(max(abs(initial), 1e-12), volatility, maturity, steps, paths)
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    values = np.empty((steps + 1, paths)); values[0] = initial
    for t in range(steps):
        values[t + 1] = values[t] + speed * (mean - values[t]) * dt + volatility * np.sqrt(dt) * rng.standard_normal(paths)
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "ou", {"initial": initial, "speed": speed, "mean": mean, "volatility": volatility, "maturity": maturity})


def cir_process(
    initial: float = 0.03,
    speed: float = 1.5,
    mean: float = 0.04,
    volatility: float = 0.2,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate a non-negative CIR process with full-truncation Euler."""
    if min(initial, speed, mean) < 0:
        raise ValueError("initial, speed, and mean must be non-negative")
    _validate_inputs(max(initial, 1e-12), volatility, maturity, steps, paths)
    rng = np.random.default_rng(random_state); dt = maturity / steps
    values = np.empty((steps + 1, paths)); values[0] = initial
    for t in range(steps):
        prev = np.maximum(values[t], 0.0)
        values[t + 1] = np.maximum(prev + speed * (mean - prev) * dt + volatility * np.sqrt(prev * dt) * rng.standard_normal(paths), 0.0)
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "cir", {"initial": initial, "speed": speed, "mean": mean, "volatility": volatility})


def vasicek_process(
    initial: float = 0.03,
    speed: float = 1.0,
    mean: float = 0.04,
    volatility: float = 0.01,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 1_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate the exact Gaussian transition of the Vasicek rate model."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    _validate_inputs(max(abs(initial), 1e-12), volatility, maturity, steps, paths)
    rng = np.random.default_rng(random_state); dt = maturity / steps
    decay = np.exp(-speed * dt)
    sd = volatility * np.sqrt((1 - np.exp(-2 * speed * dt)) / (2 * speed))
    values = np.empty((steps + 1, paths)); values[0] = initial
    for t in range(steps):
        values[t + 1] = mean + (values[t] - mean) * decay + sd * rng.standard_normal(paths)
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "vasicek", {"initial": initial, "speed": speed, "mean": mean, "volatility": volatility})


def heston_process(
    initial: float = 100.0,
    drift: float = 0.05,
    initial_variance: float = 0.04,
    mean_reversion: float = 2.0,
    long_variance: float = 0.04,
    vol_of_vol: float = 0.5,
    correlation: float = -0.7,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 2_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate Heston prices using full-truncation Euler for variance."""
    if not -1 <= correlation <= 1:
        raise ValueError("correlation must be in [-1, 1]")
    if min(initial, initial_variance, mean_reversion, long_variance, vol_of_vol, maturity, steps, paths) <= 0:
        raise ValueError("positive Heston parameters are required")
    rng = np.random.default_rng(random_state); dt = maturity / steps
    prices = np.empty((steps + 1, paths)); variances = np.empty_like(prices)
    prices[0] = initial; variances[0] = initial_variance
    for t in range(steps):
        z1 = rng.standard_normal(paths); z2 = correlation * z1 + np.sqrt(1 - correlation**2) * rng.standard_normal(paths)
        v = np.maximum(variances[t], 0.0)
        variances[t + 1] = np.maximum(v + mean_reversion * (long_variance - v) * dt + vol_of_vol * np.sqrt(v * dt) * z2, 0.0)
        prices[t + 1] = prices[t] * np.exp((drift - 0.5 * v) * dt + np.sqrt(v * dt) * z1)
    params = {"initial": initial, "drift": drift, "initial_variance": initial_variance, "mean_reversion": mean_reversion, "long_variance": long_variance, "vol_of_vol": vol_of_vol, "correlation": correlation}
    result = SimulationResult(pd.DataFrame(prices, index=np.linspace(0, maturity, steps + 1)), "heston", params)
    result.variance_paths = pd.DataFrame(variances, index=result.paths.index)
    return result


def merton_jump_diffusion(
    initial: float = 100.0,
    drift: float = 0.05,
    volatility: float = 0.2,
    jump_intensity: float = 0.5,
    jump_mean: float = -0.1,
    jump_volatility: float = 0.2,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 2_000,
    random_state: int | None = 0,
) -> SimulationResult:
    """Simulate Merton lognormal jump diffusion."""
    _validate_inputs(initial, volatility, maturity, steps, paths)
    if min(jump_intensity, jump_volatility) < 0:
        raise ValueError("jump intensity and volatility must be non-negative")
    rng = np.random.default_rng(random_state); dt = maturity / steps
    kappa = np.exp(jump_mean + 0.5 * jump_volatility**2) - 1
    z = rng.standard_normal((steps, paths))
    counts = rng.poisson(jump_intensity * dt, (steps, paths))
    jump_sizes = counts * jump_mean + np.sqrt(counts) * jump_volatility * rng.standard_normal((steps, paths))
    inc = (drift - jump_intensity * kappa - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z + jump_sizes
    values = initial * np.exp(np.vstack([np.zeros(paths), np.cumsum(inc, axis=0)]))
    return SimulationResult(pd.DataFrame(values, index=np.linspace(0, maturity, steps + 1)), "merton", {"initial": initial, "drift": drift, "volatility": volatility, "jump_intensity": jump_intensity, "jump_mean": jump_mean, "jump_volatility": jump_volatility})


def simulate(model: str = "gbm", **kwargs) -> SimulationResult:
    """Unified stochastic-process dispatcher."""
    models = {
        "abm": arithmetic_brownian_motion,
        "brownian": arithmetic_brownian_motion,
        "gbm": geometric_brownian_motion,
        "ou": ornstein_uhlenbeck,
        "ornstein_uhlenbeck": ornstein_uhlenbeck,
        "cir": cir_process,
        "vasicek": vasicek_process,
        "heston": heston_process,
        "merton": merton_jump_diffusion,
        "jump_diffusion": merton_jump_diffusion,
    }
    key = model.lower().replace("-", "_")
    if key not in models:
        raise ValueError(f"unknown model {model!r}; available: {sorted(models)}")
    return models[key](**kwargs)


def monte_carlo_price(
    simulation: SimulationResult,
    payoff: Callable[[np.ndarray], np.ndarray],
    *,
    rate: float = 0.0,
    maturity: float | None = None,
    confidence: float = 0.95,
) -> MonteCarloPriceResult:
    """Price a terminal-payoff claim from a SimulationResult."""
    terminal = simulation.terminal.to_numpy()
    raw = np.asarray(payoff(terminal), dtype=float)
    if raw.shape != terminal.shape:
        raise ValueError("payoff must return one value per path")
    maturity = float(maturity if maturity is not None else simulation.paths.index[-1])
    discounted = np.exp(-rate * maturity) * raw
    price = float(np.mean(discounted))
    se = float(np.std(discounted, ddof=1) / np.sqrt(len(discounted)))
    z = float(stats.norm.ppf(0.5 + confidence / 2))
    return MonteCarloPriceResult(price, se, (price - z * se, price + z * se), discounted, simulation, confidence)


def european_option_mc(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    option: str = "call",
    paths: int = 100_000,
    steps: int = 1,
    dividend: float = 0.0,
    antithetic: bool = True,
    random_state: int | None = 0,
) -> MonteCarloPriceResult:
    """Risk-neutral Monte Carlo price for a European option under GBM."""
    sim = geometric_brownian_motion(spot, rate - dividend, volatility, maturity, steps, paths, random_state, antithetic)
    if option.lower() == "call":
        payoff = lambda terminal: np.maximum(terminal - strike, 0.0)
    elif option.lower() == "put":
        payoff = lambda terminal: np.maximum(strike - terminal, 0.0)
    else:
        raise ValueError("option must be call or put")
    return monte_carlo_price(sim, payoff, rate=rate, maturity=maturity)


def asian_option_mc(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    option: str = "call",
    paths: int = 50_000,
    steps: int = 252,
    dividend: float = 0.0,
    random_state: int | None = 0,
) -> MonteCarloPriceResult:
    """Arithmetic-average Asian option price under risk-neutral GBM."""
    sim = geometric_brownian_motion(spot, rate - dividend, volatility, maturity, steps, paths, random_state, True)
    average = sim.paths.iloc[1:].mean(axis=0).to_numpy()
    if option.lower() == "call":
        raw = np.maximum(average - strike, 0.0)
    elif option.lower() == "put":
        raw = np.maximum(strike - average, 0.0)
    else:
        raise ValueError("option must be call or put")
    discounted = np.exp(-rate * maturity) * raw
    price = float(discounted.mean()); se = float(discounted.std(ddof=1) / np.sqrt(paths)); z = stats.norm.ppf(0.975)
    return MonteCarloPriceResult(price, se, (price - z * se, price + z * se), discounted, sim)


def regime_switching_prices(
    periods: int = 1_500,
    assets: int = 4,
    start: float = 100.0,
    annualization: int = 252,
    random_state: int | None = 7,
) -> pd.DataFrame:
    """Generate a reproducible two-regime correlated price panel."""
    rng = np.random.default_rng(random_state)
    transition = np.array([[0.97, 0.03], [0.08, 0.92]])
    regimes = np.zeros(periods, dtype=int)
    for t in range(1, periods):
        regimes[t] = rng.choice([0, 1], p=transition[regimes[t - 1]])
    means = np.array([0.08, -0.12]) / annualization
    vols = np.array([0.12, 0.32]) / np.sqrt(annualization)
    corr = 0.35 * np.ones((assets, assets)) + 0.65 * np.eye(assets)
    chol = np.linalg.cholesky(corr)
    z = rng.standard_normal((periods, assets)) @ chol.T
    returns = means[regimes, None] + vols[regimes, None] * z
    prices = start * np.exp(np.cumsum(returns, axis=0))
    index = pd.bdate_range("2020-01-01", periods=periods)
    return pd.DataFrame(prices, index=index, columns=[f"Asset_{i+1}" for i in range(assets)])


def stationary_bootstrap(
    returns: pd.Series | pd.DataFrame,
    samples: int = 1_000,
    expected_block: float = 20.0,
    random_state: int | None = 0,
) -> np.ndarray:
    """Politis-Romano-style stationary bootstrap samples."""
    frame = pd.DataFrame(returns).dropna().to_numpy()
    n, k = frame.shape
    if n == 0 or samples <= 0 or expected_block <= 0:
        raise ValueError("non-empty returns and positive samples/expected_block are required")
    rng = np.random.default_rng(random_state)
    out = np.empty((samples, n, k)); p = 1 / expected_block
    for s in range(samples):
        idx = int(rng.integers(n))
        for t in range(n):
            idx = int(rng.integers(n)) if t == 0 or rng.random() < p else (idx + 1) % n
            out[s, t] = frame[idx]
    return out


# Backwards-compatible name retained from v0.1.
def simulate_gbm(spot: float, drift: float, volatility: float, maturity: float, steps: int = 252, paths: int = 1_000, random_state: int | None = 0) -> pd.DataFrame:
    return geometric_brownian_motion(spot, drift, volatility, maturity, steps, paths, random_state).paths
