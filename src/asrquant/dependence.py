"""Copula-based dependence diagnostics for portfolio and tail-risk research."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t

from .contracts import ResultMixin


def _pseudo_observations(data: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(data, dtype=float).dropna(how="any")
    if len(frame) < 5 or frame.shape[1] < 2:
        raise ValueError("copula fitting requires at least 5 rows and 2 variables")
    ranks = frame.rank(method="average")
    return ranks / (len(frame) + 1.0)


def _nearest_correlation(matrix: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    values = np.maximum(values, eps)
    out = vectors @ np.diag(values) @ vectors.T
    scale = np.sqrt(np.diag(out))
    out = out / np.outer(scale, scale)
    np.fill_diagonal(out, 1.0)
    return out


@dataclass
class CopulaFit(ResultMixin):
    family: str
    correlation: pd.DataFrame
    df: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="copula_fit", init=False)

    @property
    def summary(self) -> pd.Series:
        corr = self.correlation.to_numpy(dtype=float)
        off = corr[np.triu_indices_from(corr, k=1)]
        return pd.Series(
            {
                "family": self.family,
                "variables": len(self.correlation),
                "mean_pairwise_correlation": float(np.mean(off)) if len(off) else np.nan,
                "df": self.df,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.correlation.copy()

    def tail_dependence(self) -> pd.DataFrame:
        corr = self.correlation.to_numpy(dtype=float)
        if self.family == "gaussian":
            values = np.zeros_like(corr)
            np.fill_diagonal(values, 1.0)
        elif self.family == "student_t":
            if self.df is None:
                raise ValueError("student-t copula requires df")
            nu = float(self.df)
            values = np.empty_like(corr)
            for i in range(len(corr)):
                for j in range(len(corr)):
                    rho = np.clip(corr[i, j], -0.999999, 0.999999)
                    if i == j:
                        values[i, j] = 1.0
                    else:
                        arg = -np.sqrt((nu + 1.0) * (1.0 - rho) / (1.0 + rho))
                        values[i, j] = 2.0 * student_t.cdf(arg, df=nu + 1.0)
        else:
            raise ValueError(f"unsupported family {self.family!r}")
        return pd.DataFrame(values, index=self.correlation.index, columns=self.correlation.columns)

    def simulate(self, n: int, random_state: int | None = 0) -> pd.DataFrame:
        if n <= 0:
            raise ValueError("n must be positive")
        rng = np.random.default_rng(random_state)
        corr = self.correlation.to_numpy(dtype=float)
        z = rng.multivariate_normal(np.zeros(len(corr)), corr, size=n)
        if self.family == "gaussian":
            u = norm.cdf(z)
        elif self.family == "student_t":
            if self.df is None:
                raise ValueError("student-t copula requires df")
            chi = rng.chisquare(self.df, size=n)
            t_draw = z / np.sqrt(chi[:, None] / self.df)
            u = student_t.cdf(t_draw, df=self.df)
        else:
            raise ValueError(f"unsupported family {self.family!r}")
        return pd.DataFrame(u, columns=self.correlation.columns)


class GaussianCopula:
    @staticmethod
    def fit(data: pd.DataFrame) -> CopulaFit:
        u = _pseudo_observations(data)
        z = pd.DataFrame(norm.ppf(u), index=u.index, columns=u.columns)
        corr = _nearest_correlation(z.corr().to_numpy(dtype=float))
        return CopulaFit("gaussian", pd.DataFrame(corr, index=u.columns, columns=u.columns), metadata={"n_observations": len(u)})


class StudentTCopula:
    @staticmethod
    def fit(data: pd.DataFrame, *, df: float = 5.0) -> CopulaFit:
        if df <= 2:
            raise ValueError("df must exceed 2")
        u = _pseudo_observations(data)
        z = pd.DataFrame(student_t.ppf(u, df=df), index=u.index, columns=u.columns)
        corr = _nearest_correlation(z.corr().to_numpy(dtype=float))
        return CopulaFit("student_t", pd.DataFrame(corr, index=u.columns, columns=u.columns), df=float(df), metadata={"n_observations": len(u)})


__all__ = ["CopulaFit", "GaussianCopula", "StudentTCopula"]
