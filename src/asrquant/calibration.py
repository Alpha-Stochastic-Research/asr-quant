"""Generic nonlinear calibration contracts with diagnostics and identifiability checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from .contracts import CalibrationError, ResultMixin


@dataclass
class CalibrationResult(ResultMixin):
    parameters: pd.Series
    residuals: pd.Series
    fitted: pd.Series
    jacobian: pd.DataFrame
    covariance: pd.DataFrame
    rmse: float
    mae: float
    success: bool
    message: str
    condition_number: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="calibration", init=False)

    @property
    def parameter_uncertainty(self) -> pd.Series:
        if self.covariance.empty:
            return pd.Series(index=self.parameters.index, dtype=float)
        return pd.Series(np.sqrt(np.maximum(np.diag(self.covariance), 0.0)), index=self.parameters.index, name="std_error")

    @property
    def identifiability(self) -> str:
        if not np.isfinite(self.condition_number):
            return "UNIDENTIFIED"
        if self.condition_number > 1e12:
            return "VERY_WEAK"
        if self.condition_number > 1e8:
            return "WEAK"
        if self.condition_number > 1e5:
            return "MODERATE"
        return "GOOD"

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "success": self.success,
                "rmse": self.rmse,
                "mae": self.mae,
                "condition_number": self.condition_number,
                "identifiability": self.identifiability,
                "n_parameters": len(self.parameters),
                "n_observations": len(self.residuals),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "parameter": self.parameters,
                "std_error": self.parameter_uncertainty.reindex(self.parameters.index),
            }
        )


class CalibrationProblem:
    """Least-squares calibration with explicit parameter names and bounds.

    ``model`` receives ``(x, params_mapping)`` and must return fitted values with
    the same shape as ``target``.
    """

    def __init__(
        self,
        model: Callable[[Any, Mapping[str, float]], Sequence[float] | np.ndarray],
        x: Any,
        target: Sequence[float] | np.ndarray | pd.Series,
        initial: Mapping[str, float],
        *,
        bounds: Mapping[str, tuple[float, float]] | None = None,
        weights: Sequence[float] | np.ndarray | None = None,
        loss: str = "linear",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not initial:
            raise CalibrationError("initial parameters must not be empty")
        self.model = model
        self.x = x
        self.target = np.asarray(target, dtype=float)
        if self.target.ndim != 1 or len(self.target) == 0 or not np.isfinite(self.target).all():
            raise CalibrationError("target must be a finite one-dimensional vector")
        self.names = list(initial)
        self.initial = np.asarray([initial[n] for n in self.names], dtype=float)
        self.bounds = bounds or {}
        self.weights = np.ones_like(self.target) if weights is None else np.asarray(weights, dtype=float)
        if self.weights.shape != self.target.shape or np.any(self.weights <= 0):
            raise CalibrationError("weights must be positive and match target")
        self.loss = loss
        self.metadata = dict(metadata or {})

    def _mapping(self, values: np.ndarray) -> dict[str, float]:
        return {name: float(value) for name, value in zip(self.names, values)}

    def _residuals(self, values: np.ndarray) -> np.ndarray:
        fitted = np.asarray(self.model(self.x, self._mapping(values)), dtype=float)
        if fitted.shape != self.target.shape:
            raise CalibrationError("model output must have the same shape as target")
        if not np.isfinite(fitted).all():
            raise CalibrationError("model returned non-finite values")
        return np.sqrt(self.weights) * (fitted - self.target)

    def solve(self, *, max_nfev: int | None = None) -> CalibrationResult:
        lower = np.asarray([self.bounds.get(n, (-np.inf, np.inf))[0] for n in self.names], dtype=float)
        upper = np.asarray([self.bounds.get(n, (-np.inf, np.inf))[1] for n in self.names], dtype=float)
        if np.any(lower >= upper):
            raise CalibrationError("every lower bound must be below its upper bound")
        try:
            opt = least_squares(
                self._residuals,
                self.initial,
                bounds=(lower, upper),
                loss=self.loss,
                max_nfev=max_nfev,
            )
        except Exception as exc:
            if isinstance(exc, CalibrationError):
                raise
            raise CalibrationError(str(exc)) from exc
        params = self._mapping(opt.x)
        fitted = np.asarray(self.model(self.x, params), dtype=float)
        raw_resid = fitted - self.target
        jac = np.asarray(opt.jac, dtype=float)
        jtj = jac.T @ jac
        cond = float(np.linalg.cond(jtj)) if jtj.size else np.nan
        dof = max(1, len(self.target) - len(self.names))
        sigma2 = float(np.dot(raw_resid, raw_resid) / dof)
        try:
            cov = sigma2 * np.linalg.pinv(jtj)
        except np.linalg.LinAlgError:
            cov = np.full((len(self.names), len(self.names)), np.nan)
        index = pd.Index(range(len(self.target)), name="observation")
        return CalibrationResult(
            parameters=pd.Series(params, name="value"),
            residuals=pd.Series(raw_resid, index=index, name="residual"),
            fitted=pd.Series(fitted, index=index, name="fitted"),
            jacobian=pd.DataFrame(jac, index=index, columns=self.names),
            covariance=pd.DataFrame(cov, index=self.names, columns=self.names),
            rmse=float(np.sqrt(np.mean(raw_resid**2))),
            mae=float(np.mean(np.abs(raw_resid))),
            success=bool(opt.success),
            message=str(opt.message),
            condition_number=cond,
            metadata={**self.metadata, "loss": self.loss, "nfev": int(opt.nfev)},
        )


__all__ = ["CalibrationProblem", "CalibrationResult"]
