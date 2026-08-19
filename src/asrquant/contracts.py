"""Shared ASRQuant 1.2 result contracts and domain exceptions.

The module is intentionally dependency-light beyond NumPy/pandas.  Public domain
wrappers use these objects to expose a predictable interface without breaking the
lower-level 1.x functions that existing notebooks may already depend on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


class ASRQuantError(Exception):
    """Base class for ASRQuant domain errors."""


class InputValidationError(ValueError, ASRQuantError):
    """Invalid user input or an inconsistent function contract."""


class DataValidationError(ValueError, ASRQuantError):
    """Market/research data violate a required structural invariant."""


class BacktestError(RuntimeError, ASRQuantError):
    """A backtest could not be completed under the requested specification."""


class OptimizationError(RuntimeError, ASRQuantError):
    """A portfolio optimization problem could not be solved reliably."""


class PricingError(ValueError, ASRQuantError):
    """A derivative-pricing request is invalid or outside the model domain."""


class CalibrationError(RuntimeError, ASRQuantError):
    """A model or curve calibration failed."""


class ModelFitError(RuntimeError, ASRQuantError):
    """A statistical or machine-learning fit could not be completed."""


class ProviderError(RuntimeError, ASRQuantError):
    """A market-data provider request failed."""


class HypothesisDiscoveryError(RuntimeError, ASRQuantError):
    """Hypothesis discovery, search or evidence audit could not be completed."""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Series):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, pd.DataFrame):
        return {
            "index": [str(item) for item in value.index],
            "columns": [str(item) for item in value.columns],
            "data": [[_json_safe(item) for item in row] for row in value.to_numpy().tolist()],
        }
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if value is pd.NaT:
        return None
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


class ResultMixin:
    """Common serialization and fingerprint behavior for structured results."""

    result_type: str = "result"

    @property
    def summary(self) -> pd.Series:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def to_frame(self) -> pd.DataFrame:
        return self.summary.rename("value").to_frame()

    def to_dict(self) -> dict[str, Any]:
        payload = {"result_type": self.result_type, "summary": self.summary.to_dict()}
        metadata = getattr(self, "metadata", None)
        if metadata:
            payload["metadata"] = dict(metadata)
        return _json_safe(payload)

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str).encode("utf-8")
        return sha256(payload).hexdigest()[:16]


@dataclass
class DataQualityResult(ResultMixin):
    """Non-mutating structural diagnostics for a tabular time series."""

    metrics: pd.Series
    issues: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="data_quality", init=False)

    @property
    def summary(self) -> pd.Series:
        return self.metrics.copy()

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def to_frame(self) -> pd.DataFrame:
        return self.metrics.rename("value").to_frame()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "result_type": self.result_type,
                "is_clean": self.is_clean,
                "issues": list(self.issues),
                "metrics": self.metrics.to_dict(),
                "metadata": self.metadata,
            }
        )


@dataclass
class PortfolioOptimizationResult(ResultMixin):
    """Canonical portfolio-optimization response."""

    weights: pd.Series
    method: str
    expected_return: float
    volatility: float
    sharpe: float | None
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="portfolio_optimization", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "method": self.method,
                "success": self.success,
                "expected_return": self.expected_return,
                "volatility": self.volatility,
                "sharpe": self.sharpe,
                "gross_exposure": float(self.weights.abs().sum()),
                "net_exposure": float(self.weights.sum()),
                "n_assets": int(len(self.weights)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.weights.rename("weight").to_frame()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "result_type": self.result_type,
                "summary": self.summary.to_dict(),
                "weights": self.weights.to_dict(),
                "metadata": self.metadata,
            }
        )


@dataclass
class CurveAnalysisResult(ResultMixin):
    """Canonical summary of a constructed interest-rate curve."""

    table: pd.DataFrame
    diagnostics: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="curve_analysis", init=False)

    @property
    def summary(self) -> pd.Series:
        out: dict[str, Any] = {"nodes": int(len(self.table))}
        if "maturity" in self.table:
            out["min_maturity"] = float(self.table["maturity"].min())
            out["max_maturity"] = float(self.table["maturity"].max())
        for name in ("zero_rate_cc", "zero_rate", "rate"):
            if name in self.table:
                out["min_zero_rate"] = float(self.table[name].min())
                out["max_zero_rate"] = float(self.table[name].max())
                break
        out.update({str(key): value for key, value in self.diagnostics.items()})
        return pd.Series(out)

    def to_frame(self) -> pd.DataFrame:
        return self.table.copy()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "result_type": self.result_type,
                "summary": self.summary.to_dict(),
                "diagnostics": self.diagnostics.to_dict(),
                "table": self.table,
                "metadata": self.metadata,
            }
        )


@dataclass
class ModelFitResult(ResultMixin):
    """Canonical response for fitted models that do not use RegressionResult."""

    model: Any
    fitted: pd.Series
    residuals: pd.Series
    metrics: pd.Series
    features: Sequence[str] = ()
    method: str = "model"
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="model_fit", init=False)

    @property
    def summary(self) -> pd.Series:
        out = self.metrics.copy()
        out.loc["method"] = self.method
        out.loc["n_observations"] = int(len(self.fitted))
        out.loc["n_features"] = int(len(self.features))
        return out

    def to_frame(self) -> pd.DataFrame:
        return pd.concat({"fitted": self.fitted, "residual": self.residuals}, axis=1)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "result_type": self.result_type,
                "summary": self.summary.to_dict(),
                "features": list(self.features),
                "metadata": self.metadata,
            }
        )


__all__ = [
    "ASRQuantError",
    "InputValidationError",
    "DataValidationError",
    "BacktestError",
    "OptimizationError",
    "PricingError",
    "CalibrationError",
    "ModelFitError",
    "ProviderError",
    "HypothesisDiscoveryError",
    "ResultMixin",
    "DataQualityResult",
    "PortfolioOptimizationResult",
    "CurveAnalysisResult",
    "ModelFitResult",
]
