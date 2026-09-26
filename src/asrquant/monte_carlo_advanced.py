"""Variance-reduction and quasi-Monte-Carlo utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm, qmc

from .contracts import ResultMixin


@dataclass
class VarianceReductionResult(ResultMixin):
    adjusted: np.ndarray
    coefficient: float
    raw_variance: float
    adjusted_variance: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="variance_reduction", init=False)

    @property
    def variance_reduction_ratio(self) -> float:
        return self.raw_variance / self.adjusted_variance if self.adjusted_variance > 0 else np.inf

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "coefficient": self.coefficient,
                "raw_variance": self.raw_variance,
                "adjusted_variance": self.adjusted_variance,
                "variance_reduction_ratio": self.variance_reduction_ratio,
                "samples": len(self.adjusted),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({"adjusted": self.adjusted})


def antithetic_normal_samples(n: int, dim: int = 1, *, random_state: int | None = 0) -> np.ndarray:
    """Standard-normal samples paired with their antithetic negatives."""
    if n <= 0 or dim <= 0:
        raise ValueError("n and dim must be positive")
    rng = np.random.default_rng(random_state)
    half = (n + 1) // 2
    z = rng.standard_normal((half, dim))
    out = np.vstack([z, -z])[:n]
    return out[:, 0] if dim == 1 else out


def sobol_normal_samples(
    n: int,
    dim: int = 1,
    *,
    scramble: bool = True,
    random_state: int | None = 0,
) -> np.ndarray:
    """Sobol quasi-random standard-normal samples."""
    if n <= 0 or dim <= 0:
        raise ValueError("n and dim must be positive")
    sampler = qmc.Sobol(d=dim, scramble=scramble, seed=random_state)
    if n & (n - 1) == 0:
        u = sampler.random_base2(int(np.log2(n)))
    else:
        u = sampler.random(n)
    eps = np.finfo(float).eps
    z = norm.ppf(np.clip(u, eps, 1.0 - eps))
    return z[:, 0] if dim == 1 else z


def stratified_uniform(n: int, *, random_state: int | None = 0) -> np.ndarray:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = np.random.default_rng(random_state)
    return (np.arange(n) + rng.random(n)) / n


def control_variate(
    values: np.ndarray,
    control: np.ndarray,
    *,
    known_control_mean: float,
) -> VarianceReductionResult:
    """Optimal single-control-variate adjustment estimated from the sample."""
    y = np.asarray(values, dtype=float).ravel()
    x = np.asarray(control, dtype=float).ravel()
    if y.shape != x.shape or len(y) < 3:
        raise ValueError("values and control must be matching vectors with at least 3 observations")
    var_x = float(np.var(x, ddof=1))
    if var_x <= 1e-20:
        raise ValueError("control variance must be positive")
    beta = float(np.cov(y, x, ddof=1)[0, 1] / var_x)
    adjusted = y - beta * (x - float(known_control_mean))
    return VarianceReductionResult(
        adjusted=adjusted,
        coefficient=beta,
        raw_variance=float(np.var(y, ddof=1)),
        adjusted_variance=float(np.var(adjusted, ddof=1)),
        metadata={"known_control_mean": known_control_mean},
    )


__all__ = ["VarianceReductionResult", "antithetic_normal_samples", "sobol_normal_samples", "stratified_uniform", "control_variate"]
