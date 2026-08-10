"""Universal Monte Carlo estimation, scenario generation, and parameter surfaces.

The central contract is deliberately model agnostic::

    scenarios = generator(rng, n_scenarios, parameters)
    outcomes  = quantity(scenarios, parameters)
    estimate  = reducer(outcomes)

This supports pricing, probabilities, losses, hedging errors, portfolio values,
default indicators, quantiles, VaR, Expected Shortfall, and arbitrary scalar
statistics without forcing users to rewrite the bookkeeping around standard
errors and confidence intervals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from .surfaces import SurfaceResult, evaluate_parameter_surface

Array = np.ndarray
Generator = Callable[..., Any]
Quantity = Callable[..., Any]
Reducer = str | Callable[[Array], float]


def _as_1d(values: Any, *, name: str = "outcomes") -> Array:
    out = np.asarray(values, dtype=float).reshape(-1)
    if out.size == 0:
        raise ValueError(f"{name} must contain at least one finite value")
    if not np.isfinite(out).all():
        raise ValueError(f"{name} contains NaN or infinite values")
    return out


def empirical_quantile(values: Any, level: float = 0.95) -> float:
    """Empirical quantile of a one-dimensional sample."""
    if not 0.0 < level < 1.0:
        raise ValueError("level must lie strictly between 0 and 1")
    return float(np.quantile(_as_1d(values), level))


def value_at_risk(losses: Any, level: float = 0.95) -> float:
    """Monte Carlo VaR for a sample expressed directly as positive losses."""
    return empirical_quantile(losses, level)


def expected_shortfall(losses: Any, level: float = 0.95) -> float:
    """Monte Carlo Expected Shortfall/CVaR for positive losses."""
    sample = _as_1d(losses, name="losses")
    threshold = value_at_risk(sample, level)
    tail = sample[sample >= threshold]
    return float(tail.mean())


def event_probability(values: Any, event: Callable[[Array], Any] | None = None) -> float:
    """Estimate a probability using an indicator or an already Boolean sample."""
    sample = np.asarray(values)
    indicator = np.asarray(event(sample) if event is not None else sample, dtype=bool)
    if indicator.size == 0:
        raise ValueError("indicator sample is empty")
    return float(indicator.mean())


def sample_variance(values: Any) -> float:
    """Unbiased sample variance with denominator N-1."""
    sample = _as_1d(values)
    if sample.size < 2:
        raise ValueError("at least two outcomes are required")
    return float(np.var(sample, ddof=1))


def standard_error(values: Any) -> float:
    """Standard error of the sample mean."""
    sample = _as_1d(values)
    if sample.size < 2:
        raise ValueError("at least two outcomes are required")
    return float(np.std(sample, ddof=1) / np.sqrt(sample.size))


def mean_confidence_interval(values: Any, confidence: float = 0.95) -> tuple[float, float]:
    """Normal-approximation confidence interval for a Monte Carlo mean."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")
    sample = _as_1d(values)
    estimate = float(sample.mean())
    se = standard_error(sample)
    critical = float(stats.norm.ppf(0.5 + confidence / 2.0))
    return estimate - critical * se, estimate + critical * se


def _reduce(values: Array, estimator: Reducer, *, level: float) -> float:
    if callable(estimator):
        return float(estimator(values))
    key = str(estimator).lower().replace("-", "_").replace(" ", "_")
    reducers: dict[str, Callable[[Array], float]] = {
        "mean": lambda x: float(np.mean(x)),
        "expectation": lambda x: float(np.mean(x)),
        "probability": lambda x: event_probability(x),
        "variance": sample_variance,
        "std": lambda x: float(np.std(x, ddof=1)),
        "standard_deviation": lambda x: float(np.std(x, ddof=1)),
        "quantile": lambda x: empirical_quantile(x, level),
        "var": lambda x: value_at_risk(x, level),
        "value_at_risk": lambda x: value_at_risk(x, level),
        "cvar": lambda x: expected_shortfall(x, level),
        "expected_shortfall": lambda x: expected_shortfall(x, level),
        "median": lambda x: float(np.median(x)),
        "min": lambda x: float(np.min(x)),
        "max": lambda x: float(np.max(x)),
    }
    if key not in reducers:
        raise ValueError(f"unknown estimator {estimator!r}; available: {sorted(reducers)}")
    return reducers[key](values)


@dataclass
class MonteCarloResult:
    """Universal Monte Carlo result with raw scenarios, outcomes, and inference."""

    estimate: float
    outcomes: Array
    estimator: str
    level: float = 0.95
    confidence: float = 0.95
    scenarios: Any | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_scenarios(self) -> int:
        return int(self.outcomes.size)

    @property
    def mean(self) -> float:
        return float(self.outcomes.mean())

    @property
    def variance(self) -> float:
        return sample_variance(self.outcomes)

    @property
    def standard_deviation(self) -> float:
        return float(np.std(self.outcomes, ddof=1))

    @property
    def standard_error(self) -> float:
        return standard_error(self.outcomes)

    @property
    def confidence_interval(self) -> tuple[float, float]:
        return mean_confidence_interval(self.outcomes, self.confidence)

    def quantile(self, level: float | None = None) -> float:
        return empirical_quantile(self.outcomes, self.level if level is None else level)

    def probability(self, event: Callable[[Array], Any] | None = None) -> float:
        return event_probability(self.outcomes, event)

    def var(self, level: float | None = None) -> float:
        return value_at_risk(self.outcomes, self.level if level is None else level)

    def cvar(self, level: float | None = None) -> float:
        return expected_shortfall(self.outcomes, self.level if level is None else level)

    @property
    def summary(self) -> pd.Series:
        ci = self.confidence_interval
        return pd.Series(
            {
                "estimator": self.estimator,
                "estimate": self.estimate,
                "n_scenarios": self.n_scenarios,
                "mean": self.mean,
                "variance": self.variance,
                "standard_deviation": self.standard_deviation,
                "standard_error": self.standard_error,
                "confidence": self.confidence,
                "ci_lower_mean": ci[0],
                "ci_upper_mean": ci[1],
                "level": self.level,
                "quantile": self.quantile(),
                "VaR": self.var(),
                "CVaR": self.cvar(),
            }
        )

    def plot(self, kind: str = "distribution", **kwargs: Any):
        """Plot outcomes or cumulative convergence without exposing matplotlib boilerplate."""
        import matplotlib.pyplot as plt

        key = kind.lower().replace("-", "_")
        if key in {"distribution", "hist", "histogram"}:
            fig, ax = plt.subplots()
            ax.hist(self.outcomes, bins=kwargs.pop("bins", 50), density=kwargs.pop("density", True), **kwargs)
            ax.axvline(self.estimate, linestyle="--", label=f"estimate={self.estimate:.6g}")
            ax.set_title("Monte Carlo outcome distribution")
            ax.legend()
            return fig
        if key in {"convergence", "running_mean"}:
            fig, ax = plt.subplots()
            running = np.cumsum(self.outcomes) / np.arange(1, self.n_scenarios + 1)
            ax.plot(np.arange(1, self.n_scenarios + 1), running, **kwargs)
            ax.axhline(self.mean, linestyle="--", label=f"final mean={self.mean:.6g}")
            ax.set_xscale("log")
            ax.set_xlabel("Scenarios")
            ax.set_ylabel("Running mean")
            ax.set_title("Monte Carlo convergence")
            ax.legend()
            return fig
        raise ValueError("kind must be distribution or convergence")


def _invoke(function: Callable[..., Any], *args: Any, parameters: Mapping[str, Any]) -> Any:
    """Call user functions with a tolerant signature without masking internal errors."""
    candidates = [
        (args, dict(parameters)),
        ((*args, parameters), {}),
        (args, {}),
    ]
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        signature = None
    if signature is not None:
        for positional, keywords in candidates:
            try:
                signature.bind(*positional, **keywords)
            except TypeError:
                continue
            return function(*positional, **keywords)
        raise TypeError("function signature is incompatible with the ASRQuant Monte Carlo contract")
    first_error: TypeError | None = None
    for positional, keywords in candidates:
        try:
            return function(*positional, **keywords)
        except TypeError as exc:
            if first_error is None:
                first_error = exc
    raise first_error or TypeError("unable to invoke function")


def run_monte_carlo(
    generator: Generator,
    quantity: Quantity | None = None,
    *,
    n_scenarios: int = 10_000,
    estimator: Reducer = "mean",
    level: float = 0.95,
    confidence: float = 0.95,
    random_state: int | None = 0,
    parameters: Mapping[str, Any] | None = None,
    keep_scenarios: bool = True,
) -> MonteCarloResult:
    """Run the universal ``generate -> transform -> reduce`` Monte Carlo pipeline.

    The preferred generator signature is ``generator(rng, n_scenarios, **parameters)``.
    The preferred quantity signature is ``quantity(scenarios, **parameters)``. Simpler
    signatures are accepted for concise notebook use.
    """
    if n_scenarios <= 1:
        raise ValueError("n_scenarios must be greater than one")
    if not 0.0 < level < 1.0:
        raise ValueError("level must lie strictly between 0 and 1")
    params = dict(parameters or {})
    rng = np.random.default_rng(random_state)
    scenarios = _invoke(generator, rng, int(n_scenarios), parameters=params)
    transformed = scenarios if quantity is None else _invoke(quantity, scenarios, parameters=params)
    outcomes = _as_1d(transformed)
    if outcomes.size != n_scenarios:
        raise ValueError(
            f"quantity must return one scalar per scenario: expected {n_scenarios}, got {outcomes.size}"
        )
    estimator_name = getattr(estimator, "__name__", str(estimator))
    estimate = _reduce(outcomes, estimator, level=level)
    return MonteCarloResult(
        estimate=estimate,
        outcomes=outcomes,
        estimator=estimator_name,
        level=level,
        confidence=confidence,
        scenarios=scenarios if keep_scenarios else None,
        parameters=params,
        metadata={"random_state": random_state},
    )


def uniform_inverse_transform(
    quantile_function: Callable[[Array], Any],
    size: int | tuple[int, ...],
    *,
    random_state: int | None = 0,
) -> Array:
    """Generate a target distribution through inverse transform sampling."""
    rng = np.random.default_rng(random_state)
    uniforms = rng.uniform(0.0, 1.0, size=size)
    return np.asarray(quantile_function(uniforms), dtype=float)


def normal_samples(
    mean: float = 0.0,
    standard_deviation: float = 1.0,
    size: int | tuple[int, ...] = 10_000,
    *,
    random_state: int | None = 0,
) -> Array:
    """Generate ``mean + standard_deviation * Z`` with standard-normal Z."""
    if standard_deviation < 0:
        raise ValueError("standard_deviation must be non-negative")
    rng = np.random.default_rng(random_state)
    return mean + standard_deviation * rng.standard_normal(size)


def correlated_normal(
    mean: Sequence[float] | Array,
    covariance: Array,
    n_scenarios: int = 10_000,
    *,
    random_state: int | None = 0,
) -> Array:
    """Generate correlated Gaussian vectors using a Cholesky factor."""
    mu = np.asarray(mean, dtype=float).reshape(-1)
    sigma = np.asarray(covariance, dtype=float)
    if sigma.shape != (mu.size, mu.size):
        raise ValueError("covariance shape must match mean dimension")
    if not np.allclose(sigma, sigma.T, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    try:
        factor = np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError as exc:
        raise ValueError("covariance must be positive definite") from exc
    rng = np.random.default_rng(random_state)
    independent = rng.standard_normal((int(n_scenarios), mu.size))
    return mu + independent @ factor.T


def euler_maruyama(
    drift: Callable[..., Any],
    diffusion: Callable[..., Any],
    initial: float | Sequence[float] | Array,
    *,
    maturity: float = 1.0,
    steps: int = 252,
    paths: int = 10_000,
    random_state: int | None = 0,
    parameters: Mapping[str, Any] | None = None,
) -> Array:
    """Generic scalar or vector Euler-Maruyama SDE simulator.

    ``drift(t, x, **parameters)`` must return the state shape. ``diffusion`` may
    return the state shape for independent shocks, or a matrix ``(d, m)`` for a
    vector state driven by ``m`` Brownian factors.
    """
    if maturity <= 0 or steps <= 0 or paths <= 0:
        raise ValueError("maturity, steps, and paths must be positive")
    params = dict(parameters or {})
    x0 = np.asarray(initial, dtype=float)
    scalar = x0.ndim == 0
    state_dim = 1 if scalar else int(x0.size)
    state0 = x0.reshape(state_dim)
    out = np.empty((steps + 1, paths, state_dim), dtype=float)
    out[0] = state0
    rng = np.random.default_rng(random_state)
    dt = maturity / steps
    sqrt_dt = np.sqrt(dt)

    for step in range(steps):
        t = step * dt
        current = out[step]
        mu = np.asarray(_invoke(drift, t, current, parameters=params), dtype=float)
        if mu.ndim == 0:
            mu = np.full_like(current, float(mu))
        else:
            mu = np.broadcast_to(mu, current.shape)
        sigma = np.asarray(_invoke(diffusion, t, current, parameters=params), dtype=float)
        if sigma.ndim <= 2 and sigma.shape == current.shape:
            shocks = rng.standard_normal(current.shape)
            noise = sigma * shocks
        elif sigma.ndim == 0:
            noise = float(sigma) * rng.standard_normal(current.shape)
        elif sigma.ndim == 2 and sigma.shape[0] == state_dim:
            shocks = rng.standard_normal((paths, sigma.shape[1]))
            noise = shocks @ sigma.T
        elif sigma.ndim == 3 and sigma.shape[:2] == (paths, state_dim):
            shocks = rng.standard_normal((paths, sigma.shape[2]))
            noise = np.einsum("pdm,pm->pd", sigma, shocks)
        else:
            raise ValueError("diffusion returned an unsupported shape")
        out[step + 1] = current + mu * dt + noise * sqrt_dt

    return out[:, :, 0] if scalar else out


def proportional_transaction_cost(
    prices: Any,
    positions: Any,
    cost_rate: float,
    *,
    initial_position: float | Array = 0.0,
) -> Array:
    """Pathwise proportional trading cost ``sum kappa*S*|delta_t-delta_{t-1}|``."""
    s = np.asarray(prices, dtype=float)
    d = np.asarray(positions, dtype=float)
    if s.shape != d.shape or s.ndim < 2:
        raise ValueError("prices and positions must share a pathwise shape (time, paths[, assets])")
    previous = np.concatenate([np.broadcast_to(initial_position, d[:1].shape), d[:-1]], axis=0)
    costs = cost_rate * s * np.abs(d - previous)
    if costs.ndim == 2:
        return np.sum(costs, axis=0)
    axes = (0, *range(2, costs.ndim))  # preserve the path axis at position 1
    return np.sum(costs, axis=axes)


def hedging_loss(
    payoff: Any,
    prices: Any,
    positions: Any,
    *,
    premium: float = 0.0,
    cost_rate: float = 0.0,
    initial_position: float | Array = 0.0,
) -> Array:
    """Pathwise hedging loss including proportional transaction costs."""
    s = np.asarray(prices, dtype=float)
    d = np.asarray(positions, dtype=float)
    if s.shape != d.shape or s.ndim != 2:
        raise ValueError("prices and positions must have shape (time, paths)")
    gains = np.sum(d[:-1] * np.diff(s, axis=0), axis=0)
    costs = proportional_transaction_cost(s[:-1], d[:-1], cost_rate, initial_position=initial_position)
    return np.asarray(payoff, dtype=float).reshape(-1) - premium - gains + costs


def monte_carlo_parameter_surface(
    generator: Generator,
    quantity: Quantity | None,
    parameter_grid: Mapping[str, Sequence[Any]],
    *,
    x: str,
    y: str,
    animate_by: str | Sequence[str] | None = None,
    estimator: Reducer = "mean",
    level: float = 0.95,
    confidence: float = 0.95,
    n_scenarios: int = 10_000,
    random_state: int | None = 0,
    fixed_params: Mapping[str, Any] | None = None,
    z_name: str | None = None,
    n_jobs: int = 1,
) -> SurfaceResult:
    """Evaluate any Monte Carlo statistic over a 2D or animated parameter grid."""

    def experiment(**varying: Any) -> float:
        params = dict(fixed_params or {})
        params.update(varying)
        result = run_monte_carlo(
            generator,
            quantity,
            n_scenarios=n_scenarios,
            estimator=estimator,
            level=level,
            confidence=confidence,
            random_state=random_state,
            parameters=params,
            keep_scenarios=False,
        )
        return result.estimate

    estimator_name = getattr(estimator, "__name__", str(estimator))
    return evaluate_parameter_surface(
        experiment,
        parameter_grid,
        x=x,
        y=y,
        animate_by=animate_by,
        z_name=z_name or estimator_name,
        n_jobs=n_jobs,
    )


__all__ = [
    "MonteCarloResult",
    "run_monte_carlo",
    "empirical_quantile",
    "event_probability",
    "sample_variance",
    "standard_error",
    "mean_confidence_interval",
    "value_at_risk",
    "expected_shortfall",
    "uniform_inverse_transform",
    "normal_samples",
    "correlated_normal",
    "euler_maruyama",
    "proportional_transaction_cost",
    "hedging_loss",
    "monte_carlo_parameter_surface",
]
