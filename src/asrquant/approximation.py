"""Interpolation, smoothing, response surfaces, extrapolation, and sensitivities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence
import warnings

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, RBFInterpolator, RegularGridInterpolator, interp1d
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso

from .surfaces import SurfaceResult


@dataclass
class ApproximationResult:
    """Fitted approximation with a uniform prediction interface."""

    model: Any
    method: str
    dimension: int
    domain_min: np.ndarray
    domain_max: np.ndarray
    metadata: dict[str, Any]
    predictor: Callable[[np.ndarray], np.ndarray]
    uncertainty_predictor: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None

    def predict(self, points: Any, *, allow_extrapolation: bool = False) -> np.ndarray:
        x = np.asarray(points, dtype=float)
        x2 = x.reshape(-1, self.dimension)
        outside = np.any((x2 < self.domain_min) | (x2 > self.domain_max), axis=1)
        if outside.any() and not allow_extrapolation:
            raise ValueError("prediction points lie outside the fitted domain; set allow_extrapolation=True")
        if outside.any():
            warnings.warn("extrapolation outside the observed domain can be unreliable", RuntimeWarning, stacklevel=2)
        return np.asarray(self.predictor(x2), dtype=float).reshape(x.shape[:-1] if self.dimension > 1 else x.shape)

    def predict_with_uncertainty(self, points: Any, *, allow_extrapolation: bool = False) -> tuple[np.ndarray, np.ndarray]:
        if self.uncertainty_predictor is None:
            raise ValueError(f"method {self.method!r} does not provide predictive uncertainty")
        x = np.asarray(points, dtype=float)
        x2 = x.reshape(-1, self.dimension)
        outside = np.any((x2 < self.domain_min) | (x2 > self.domain_max), axis=1)
        if outside.any() and not allow_extrapolation:
            raise ValueError("prediction points lie outside the fitted domain; set allow_extrapolation=True")
        mean, std = self.uncertainty_predictor(x2)
        target_shape = x.shape[:-1] if self.dimension > 1 else x.shape
        return np.asarray(mean).reshape(target_shape), np.asarray(std).reshape(target_shape)


def _xy(x: Any, y: Any) -> tuple[np.ndarray, np.ndarray]:
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float).reshape(-1)
    if xx.ndim == 1:
        xx = xx.reshape(-1, 1)
    if xx.ndim != 2 or xx.shape[0] != yy.size:
        raise ValueError("x must be (n, d) and y must contain n observations")
    if not np.isfinite(xx).all() or not np.isfinite(yy).all():
        raise ValueError("x and y must be finite")
    return xx, yy


def linear_interpolation(x: Any, y: Any, *, extrapolate: bool = False) -> ApproximationResult:
    """Piecewise-linear one-dimensional interpolation."""
    xx, yy = _xy(x, y)
    if xx.shape[1] != 1:
        raise ValueError("linear_interpolation is one-dimensional")
    order = np.argsort(xx[:, 0])
    xs, ys = xx[order, 0], yy[order]
    fill = "extrapolate" if extrapolate else np.nan
    model = interp1d(xs, ys, kind="linear", bounds_error=False, fill_value=fill, assume_sorted=True)
    return ApproximationResult(
        model, "linear_interpolation", 1, np.array([xs.min()]), np.array([xs.max()]),
        {"extrapolate": extrapolate}, lambda q: model(q[:, 0])
    )


def bilinear_interpolation(
    x_values: Sequence[float],
    y_values: Sequence[float],
    z_values: Any,
    *,
    extrapolate: bool = False,
) -> ApproximationResult:
    """Bilinear interpolation on a regular two-dimensional grid."""
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    z = np.asarray(z_values, dtype=float)
    if z.shape != (y.size, x.size):
        raise ValueError("z_values must have shape (len(y_values), len(x_values))")
    model = RegularGridInterpolator(
        (y, x), z, method="linear", bounds_error=not extrapolate, fill_value=None if extrapolate else np.nan
    )
    predictor = lambda q: model(np.column_stack([q[:, 1], q[:, 0]]))
    return ApproximationResult(
        model, "bilinear_interpolation", 2, np.array([x.min(), y.min()]), np.array([x.max(), y.max()]),
        {"extrapolate": extrapolate}, predictor
    )


def cubic_spline(x: Any, y: Any, *, boundary_condition: str = "not-a-knot", extrapolate: bool = False) -> ApproximationResult:
    """One-dimensional cubic spline with continuous first and second derivatives."""
    xx, yy = _xy(x, y)
    if xx.shape[1] != 1:
        raise ValueError("cubic_spline is one-dimensional")
    order = np.argsort(xx[:, 0])
    xs, ys = xx[order, 0], yy[order]
    model = CubicSpline(xs, ys, bc_type=boundary_condition, extrapolate=extrapolate)
    return ApproximationResult(
        model, "cubic_spline", 1, np.array([xs.min()]), np.array([xs.max()]),
        {"boundary_condition": boundary_condition, "extrapolate": extrapolate}, lambda q: model(q[:, 0])
    )


def kernel_regression(x: Any, y: Any, *, bandwidth: float = 1.0) -> ApproximationResult:
    """Gaussian Nadaraya-Watson kernel regression in one or several dimensions."""
    if bandwidth <= 0:
        raise ValueError("bandwidth must be positive")
    xx, yy = _xy(x, y)

    def predict(q: np.ndarray) -> np.ndarray:
        distances2 = np.sum((q[:, None, :] - xx[None, :, :]) ** 2, axis=2)
        weights = np.exp(-0.5 * distances2 / bandwidth**2)
        denominators = weights.sum(axis=1)
        if np.any(denominators <= np.finfo(float).eps):
            raise ValueError("bandwidth is too small for the requested points")
        return weights @ yy / denominators

    return ApproximationResult(
        {"x": xx, "y": yy}, "kernel_regression", xx.shape[1], xx.min(axis=0), xx.max(axis=0),
        {"bandwidth": bandwidth}, predict
    )


def rbf_interpolation(x: Any, y: Any, *, kernel: str = "thin_plate_spline", smoothing: float = 0.0, epsilon: float | None = None) -> ApproximationResult:
    """Radial-basis interpolation for irregular one- or multi-dimensional samples."""
    xx, yy = _xy(x, y)
    model = RBFInterpolator(xx, yy, kernel=kernel, smoothing=smoothing, epsilon=epsilon)
    return ApproximationResult(
        model, "rbf_interpolation", xx.shape[1], xx.min(axis=0), xx.max(axis=0),
        {"kernel": kernel, "smoothing": smoothing, "epsilon": epsilon}, lambda q: model(q)
    )


def gaussian_process(
    x: Any,
    y: Any,
    *,
    length_scale: float | Sequence[float] = 1.0,
    noise: float = 1e-6,
    normalize_y: bool = True,
    random_state: int | None = 0,
) -> ApproximationResult:
    """Gaussian-process surrogate with predictive mean and standard deviation."""
    xx, yy = _xy(x, y)
    scaler = StandardScaler().fit(xx)
    scaled = scaler.transform(xx)
    kernel = ConstantKernel(1.0, (1e-6, 1e6)) * RBF(length_scale=length_scale) + WhiteKernel(noise_level=noise)
    model = GaussianProcessRegressor(kernel=kernel, normalize_y=normalize_y, random_state=random_state)
    model.fit(scaled, yy)
    return ApproximationResult(
        {"scaler": scaler, "regressor": model}, "gaussian_process", xx.shape[1], xx.min(axis=0), xx.max(axis=0),
        {"kernel": str(model.kernel_), "noise": noise, "standardized_inputs": True},
        lambda q: model.predict(scaler.transform(q)),
        lambda q: model.predict(scaler.transform(q), return_std=True),
    )


def response_regression(
    x: Any,
    y: Any,
    *,
    method: str = "polynomial",
    degree: int = 2,
    alpha: float = 1.0,
) -> ApproximationResult:
    """Linear, polynomial, ridge, or lasso response-surface regression."""
    xx, yy = _xy(x, y)
    key = method.lower().replace("-", "_")
    if key == "linear":
        model = LinearRegression().fit(xx, yy)
    elif key in {"polynomial", "poly"}:
        model = make_pipeline(PolynomialFeatures(degree=degree, include_bias=False), LinearRegression()).fit(xx, yy)
    elif key == "ridge":
        model = make_pipeline(StandardScaler(), PolynomialFeatures(degree=degree, include_bias=False), Ridge(alpha=alpha)).fit(xx, yy)
    elif key == "lasso":
        model = make_pipeline(StandardScaler(), PolynomialFeatures(degree=degree, include_bias=False), Lasso(alpha=alpha, max_iter=20_000)).fit(xx, yy)
    else:
        raise ValueError("method must be linear, polynomial, ridge, or lasso")
    return ApproximationResult(
        model, key, xx.shape[1], xx.min(axis=0), xx.max(axis=0),
        {"degree": degree, "alpha": alpha}, lambda q: model.predict(q)
    )


def regression_metrics(actual: Any, predicted: Any) -> pd.Series:
    """RMSE, MAE, and R-squared for model validation."""
    y = np.asarray(actual, dtype=float).reshape(-1)
    p = np.asarray(predicted, dtype=float).reshape(-1)
    if y.size != p.size or y.size == 0:
        raise ValueError("actual and predicted must have the same non-zero length")
    return pd.Series(
        {
            "RMSE": float(mean_squared_error(y, p) ** 0.5),
            "MAE": float(mean_absolute_error(y, p)),
            "R2": float(r2_score(y, p)),
        }
    )


def finite_difference_gradient(function: Callable[..., float], point: Sequence[float], *, step: float = 1e-5) -> np.ndarray:
    """Centered finite-difference gradient of an arbitrary scalar function."""
    x = np.asarray(point, dtype=float)
    if step <= 0:
        raise ValueError("step must be positive")
    gradient = np.empty_like(x)
    for i in range(x.size):
        shift = np.zeros_like(x); shift[i] = step
        gradient[i] = (float(function(*(x + shift))) - float(function(*(x - shift)))) / (2 * step)
    return gradient


def finite_difference_hessian(function: Callable[..., float], point: Sequence[float], *, step: float = 1e-4) -> np.ndarray:
    """Centered finite-difference Hessian of an arbitrary scalar function."""
    x = np.asarray(point, dtype=float)
    if step <= 0:
        raise ValueError("step must be positive")
    n = x.size
    hessian = np.empty((n, n), dtype=float)
    f0 = float(function(*x))
    for i in range(n):
        ei = np.zeros(n); ei[i] = step
        hessian[i, i] = (float(function(*(x + ei))) - 2 * f0 + float(function(*(x - ei)))) / step**2
        for j in range(i + 1, n):
            ej = np.zeros(n); ej[j] = step
            value = (
                float(function(*(x + ei + ej))) - float(function(*(x + ei - ej)))
                - float(function(*(x - ei + ej))) + float(function(*(x - ei - ej)))
            ) / (4 * step**2)
            hessian[i, j] = hessian[j, i] = value
    return hessian


def surface_gradient(surface: SurfaceResult, *, frame: int | None = None) -> dict[str, SurfaceResult]:
    """Numerical first derivatives of a regular response surface."""
    selected = surface.frame(0 if frame is None else frame) if surface.is_animated else surface
    edge_order = 2 if min(len(selected.x_values), len(selected.y_values)) >= 3 else 1
    dz_dy, dz_dx = np.gradient(selected.z_values, selected.y_values, selected.x_values, edge_order=edge_order)
    common = dict(x_values=selected.x_values, y_values=selected.y_values, x_name=selected.x_name, y_name=selected.y_name)
    return {
        selected.x_name: SurfaceResult(z_values=dz_dx, z_name=f"d{selected.z_name}/d{selected.x_name}", **common),
        selected.y_name: SurfaceResult(z_values=dz_dy, z_name=f"d{selected.z_name}/d{selected.y_name}", **common),
    }


def surface_hessian(surface: SurfaceResult, *, frame: int | None = None) -> dict[str, SurfaceResult]:
    """Numerical second derivatives and cross-curvature of a regular surface."""
    selected = surface.frame(0 if frame is None else frame) if surface.is_animated else surface
    first = surface_gradient(selected)
    dzdx = first[selected.x_name].z_values
    dzdy = first[selected.y_name].z_values
    edge_order = 2 if min(len(selected.x_values), len(selected.y_values)) >= 3 else 1
    d2x_dy, d2x_dx = np.gradient(dzdx, selected.y_values, selected.x_values, edge_order=edge_order)
    d2y_dy, d2y_dx = np.gradient(dzdy, selected.y_values, selected.x_values, edge_order=edge_order)
    cross = 0.5 * (d2x_dy + d2y_dx)
    common = dict(x_values=selected.x_values, y_values=selected.y_values, x_name=selected.x_name, y_name=selected.y_name)
    return {
        f"{selected.x_name}{selected.x_name}": SurfaceResult(z_values=d2x_dx, z_name=f"d2{selected.z_name}/d{selected.x_name}2", **common),
        f"{selected.x_name}{selected.y_name}": SurfaceResult(z_values=cross, z_name=f"d2{selected.z_name}/d{selected.x_name}d{selected.y_name}", **common),
        f"{selected.y_name}{selected.y_name}": SurfaceResult(z_values=d2y_dy, z_name=f"d2{selected.z_name}/d{selected.y_name}2", **common),
    }


__all__ = [
    "ApproximationResult",
    "linear_interpolation",
    "bilinear_interpolation",
    "cubic_spline",
    "kernel_regression",
    "rbf_interpolation",
    "gaussian_process",
    "response_regression",
    "regression_metrics",
    "finite_difference_gradient",
    "finite_difference_hessian",
    "surface_gradient",
    "surface_hessian",
]
