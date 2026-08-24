# Approximation, interpolation and surface sensitivities

ASRQuant 1.0.0 distinguishes interpolation, regression, smoothing, extrapolation, simulation, optimization and validation.

## Available methods

| Operation | ASRQuant function |
|---|---|
| Linear interpolation | `linear_interpolation` |
| Bilinear regular-grid interpolation | `bilinear_interpolation` |
| Cubic spline | `cubic_spline` |
| Gaussian kernel regression | `kernel_regression` |
| Radial-basis interpolation | `rbf_interpolation` |
| Gaussian-process surrogate | `gaussian_process` |
| Linear response regression | `response_regression(..., method="linear")` |
| Polynomial response regression | `response_regression(..., method="polynomial")` |
| Ridge response regression | `response_regression(..., method="ridge")` |
| Lasso response regression | `response_regression(..., method="lasso")` |
| RMSE, MAE and R-squared | `regression_metrics` |
| Finite-difference gradient | `finite_difference_gradient` |
| Finite-difference Hessian | `finite_difference_hessian` |
| Grid-surface gradient | `SurfaceResult.gradient()` |
| Grid-surface Hessian | `SurfaceResult.hessian()` |

## Interpolation

```python
import asrquant as asr

curve = asr.linear_interpolation(
    x=[0.00, 0.01, 0.02, 0.04],
    y=[4.8, 5.5, 7.2, 10.6],
)
print(curve.predict([0.015]))
```

For a regular two-dimensional grid:

```python
surface_model = asr.bilinear_interpolation(
    x_values=cost_grid,
    y_values=volatility_grid,
    z_values=cvar_matrix,
)
value = surface_model.predict([[0.0015, 0.25]])
```

## Smoothing and irregular data

```python
spline = asr.cubic_spline(maturities, zero_rates)
kernel = asr.kernel_regression(points, values, bandwidth=0.4)
rbf = asr.rbf_interpolation(points, values, smoothing=1e-6)
```

## Gaussian-process surrogate and uncertainty

```python
gp = asr.gaussian_process(points, expensive_model_values, noise=1e-6)
mean, standard_deviation = gp.predict_with_uncertainty(new_points)
```

The Gaussian process provides both a predictive mean and predictive standard deviation. It is useful for sparse expensive experiments, calibration and Bayesian-optimization workflows.

## Extrapolation control

Predictions outside the observed domain fail by default:

```python
model.predict(outside_points)
```

Explicit extrapolation requires:

```python
model.predict(outside_points, allow_extrapolation=True)
```

ASRQuant emits a warning because extrapolation is structurally less reliable than interpolation.

## Gradient and Hessian

For a callable:

```python
gradient = asr.finite_difference_gradient(function, [x0, y0])
hessian = asr.finite_difference_hessian(function, [x0, y0])
```

For an evaluated `SurfaceResult`:

```python
surface = lab.parameter_surface(...)
first_order = surface.gradient()
second_order = surface.hessian()

first_order["transaction_cost"].plot("heatmap")
second_order["transaction_costvolatility"].plot("surface")
```

These objects preserve axis names and can use the same 3D, heatmap and contour renderers as the original surface.
