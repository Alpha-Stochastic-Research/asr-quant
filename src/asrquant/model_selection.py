"""Comparable model diagnostics on a common observation set."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .contracts import ResultMixin


@dataclass
class ModelComparisonResult(ResultMixin):
    table: pd.DataFrame
    ranking_metric: str = "rmse"
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="model_comparison", init=False)

    @property
    def best_model(self) -> str:
        ascending = self.ranking_metric not in {"r2", "log_likelihood"}
        return str(self.table[self.ranking_metric].sort_values(ascending=ascending).index[0])

    @property
    def summary(self) -> pd.Series:
        return pd.Series({"models": len(self.table), "ranking_metric": self.ranking_metric, "best_model": self.best_model})

    def to_frame(self) -> pd.DataFrame:
        return self.table.copy()


def compare_predictions(
    actual: pd.Series,
    predictions: Mapping[str, pd.Series],
    *,
    n_parameters: Mapping[str, int] | None = None,
    ranking_metric: str = "rmse",
) -> ModelComparisonResult:
    """Compare prediction vectors on exactly the same aligned observations."""
    if not predictions:
        raise ValueError("predictions must not be empty")
    y = pd.Series(actual, dtype=float).rename("actual")
    pred_frame = pd.DataFrame({name: pd.Series(value, dtype=float) for name, value in predictions.items()})
    data = pd.concat([y, pred_frame], axis=1).dropna()
    if len(data) < 3:
        raise ValueError("at least three aligned observations are required")
    rows = []
    for name in pred_frame.columns:
        resid = data[name] - data["actual"]
        rss = float(np.dot(resid, resid))
        n = len(resid)
        k = int((n_parameters or {}).get(name, 0))
        sigma2 = max(rss / n, np.finfo(float).tiny)
        log_like = float(-0.5 * n * (np.log(2 * np.pi * sigma2) + 1.0))
        tss = float(np.sum((data["actual"] - data["actual"].mean()) ** 2))
        rows.append(
            {
                "model": name,
                "rmse": float(np.sqrt(np.mean(resid**2))),
                "mae": float(np.mean(np.abs(resid))),
                "r2": float(1.0 - rss / tss) if tss > 0 else np.nan,
                "log_likelihood": log_like,
                "aic": float(2 * k - 2 * log_like),
                "bic": float(np.log(n) * k - 2 * log_like),
                "residual_bias": float(resid.mean()),
            }
        )
    table = pd.DataFrame(rows).set_index("model")
    if ranking_metric not in table:
        raise ValueError(f"unknown ranking_metric {ranking_metric!r}")
    return ModelComparisonResult(table, ranking_metric, metadata={"n_observations": len(data)})


__all__ = ["ModelComparisonResult", "compare_predictions"]
