"""Covariance estimators and out-of-sample diagnostics for portfolio research."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf, MinCovDet

from .contracts import InputValidationError, ResultMixin


def _returns(value: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(value, dtype=float).dropna(how="any")
    if frame.empty or frame.shape[1] < 1:
        raise InputValidationError("returns must contain at least one numeric asset")
    if len(frame) < 3:
        raise InputValidationError("at least three aligned observations are required")
    return frame


def _frame(matrix: np.ndarray, columns: Sequence[str]) -> pd.DataFrame:
    out = pd.DataFrame(np.asarray(matrix, dtype=float), index=columns, columns=columns)
    return 0.5 * (out + out.T)


def sample(returns: pd.DataFrame, *, annualization: float = 252.0) -> pd.DataFrame:
    frame = _returns(returns)
    return frame.cov() * float(annualization)


def ewma(
    returns: pd.DataFrame,
    *,
    decay: float = 0.94,
    annualization: float = 252.0,
) -> pd.DataFrame:
    frame = _returns(returns)
    if not 0.0 < decay < 1.0:
        raise InputValidationError("decay must lie in (0, 1)")
    x = frame.to_numpy(dtype=float)
    n = len(x)
    weights = (1.0 - decay) * decay ** np.arange(n - 1, -1, -1, dtype=float)
    weights /= weights.sum()
    mean = np.sum(x * weights[:, None], axis=0)
    centered = x - mean
    cov = (centered * weights[:, None]).T @ centered
    # Finite-sample correction for normalized unequal weights.
    denom = max(1e-12, 1.0 - float(np.sum(weights**2)))
    cov /= denom
    return _frame(cov * float(annualization), frame.columns)


def ledoit_wolf(returns: pd.DataFrame, *, annualization: float = 252.0) -> pd.DataFrame:
    frame = _returns(returns)
    model = LedoitWolf().fit(frame.to_numpy(dtype=float))
    return _frame(model.covariance_ * float(annualization), frame.columns)


def factor(
    returns: pd.DataFrame,
    *,
    n_factors: int = 3,
    annualization: float = 252.0,
) -> pd.DataFrame:
    """PCA factor covariance plus diagonal idiosyncratic variance."""
    frame = _returns(returns)
    if not 1 <= n_factors <= frame.shape[1]:
        raise InputValidationError("n_factors must be between 1 and the number of assets")
    cov = frame.cov().to_numpy(dtype=float)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    loadings = eigvecs[:, :n_factors]
    systematic = loadings @ np.diag(np.clip(eigvals[:n_factors], 0.0, None)) @ loadings.T
    residual = np.clip(np.diag(cov - systematic), 0.0, None)
    estimate = systematic + np.diag(residual)
    return _frame(estimate * float(annualization), frame.columns)


def robust(
    returns: pd.DataFrame,
    *,
    annualization: float = 252.0,
    random_state: int | None = 0,
) -> pd.DataFrame:
    frame = _returns(returns)
    if len(frame) <= frame.shape[1] + 1:
        raise InputValidationError("robust covariance requires more observations than assets")
    model = MinCovDet(random_state=random_state).fit(frame.to_numpy(dtype=float))
    return _frame(model.covariance_ * float(annualization), frame.columns)


_ESTIMATORS = {
    "sample": sample,
    "ewma": ewma,
    "ledoit_wolf": ledoit_wolf,
    "factor": factor,
    "robust": robust,
}


@dataclass
class CovarianceComparisonResult(ResultMixin):
    table: pd.DataFrame
    matrices: Mapping[str, pd.DataFrame]
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="covariance_comparison", init=False)

    @property
    def summary(self) -> pd.Series:
        if self.table.empty:
            return pd.Series(dtype=float)
        best = str(self.table["oos_variance_error"].idxmin())
        return pd.Series(
            {
                "estimators": len(self.table),
                "best_oos_variance": best,
                "lowest_oos_variance_error": float(self.table.loc[best, "oos_variance_error"]),
                "lowest_condition_number": float(self.table["condition_number"].min()),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.table.copy()


def compare(
    returns: pd.DataFrame,
    *,
    estimators: Sequence[str] = ("sample", "ewma", "ledoit_wolf", "factor"),
    holdout_fraction: float = 0.30,
    annualization: float = 252.0,
    n_factors: int = 3,
) -> CovarianceComparisonResult:
    """Compare covariance estimators on a chronological holdout."""
    frame = _returns(returns)
    if not 0.10 <= holdout_fraction <= 0.50:
        raise InputValidationError("holdout_fraction must lie in [0.10, 0.50]")
    cut = int(round(len(frame) * (1.0 - holdout_fraction)))
    if cut < 3 or len(frame) - cut < 3:
        raise InputValidationError("not enough observations for train/holdout covariance comparison")
    train, test = frame.iloc[:cut], frame.iloc[cut:]
    realized = sample(test, annualization=annualization)
    w = np.full(frame.shape[1], 1.0 / frame.shape[1])
    realized_var = float(w @ realized.to_numpy() @ w)
    rows: list[dict[str, Any]] = []
    matrices: dict[str, pd.DataFrame] = {}
    for name in estimators:
        key = str(name).lower().replace("-", "_")
        if key not in _ESTIMATORS:
            raise InputValidationError(f"unknown covariance estimator {name!r}")
        if key == "factor":
            matrix = factor(train, n_factors=min(n_factors, train.shape[1]), annualization=annualization)
        else:
            matrix = _ESTIMATORS[key](train, annualization=annualization)
        values = matrix.to_numpy(dtype=float)
        predicted_var = float(w @ values @ w)
        eig = np.linalg.eigvalsh(values)
        rows.append(
            {
                "estimator": key,
                "condition_number": float(np.linalg.cond(values)),
                "minimum_eigenvalue": float(eig.min()),
                "predicted_equal_weight_variance": predicted_var,
                "realized_equal_weight_variance": realized_var,
                "oos_variance_error": abs(predicted_var - realized_var),
            }
        )
        matrices[key] = matrix
    table = pd.DataFrame(rows).set_index("estimator")
    return CovarianceComparisonResult(
        table,
        matrices,
        metadata={"train_observations": len(train), "holdout_observations": len(test), "annualization": annualization},
    )


__all__ = [
    "sample",
    "ewma",
    "ledoit_wolf",
    "factor",
    "robust",
    "compare",
    "CovarianceComparisonResult",
]
