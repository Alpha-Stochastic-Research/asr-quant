import numpy as np
import pytest

from asrquant import (
    QuantLab,
    bilinear_interpolation,
    cubic_spline,
    finite_difference_gradient,
    finite_difference_hessian,
    gaussian_process,
    kernel_regression,
    linear_interpolation,
    rbf_interpolation,
    regression_metrics,
    response_regression,
)
from asrquant.surfaces import evaluate_surface


def test_linear_and_bilinear_interpolation():
    linear = linear_interpolation([0.0, 1.0, 2.0], [0.0, 2.0, 4.0])
    assert np.allclose(linear.predict([0.5, 1.5]), [1.0, 3.0])
    with pytest.raises(ValueError, match="outside"):
        linear.predict([3.0])

    x = np.array([0.0, 1.0])
    y = np.array([0.0, 2.0])
    xx, yy = np.meshgrid(x, y)
    z = 1.0 + 2.0 * xx + 3.0 * yy
    bilinear = bilinear_interpolation(x, y, z)
    value = bilinear.predict(np.array([[0.25, 0.5]]))
    assert np.allclose(value, [3.0])


def test_spline_kernel_rbf_and_gaussian_process():
    x = np.linspace(0.0, 2.0 * np.pi, 25)
    y = np.sin(x)
    query = np.linspace(0.2, 6.0, 30)

    spline = cubic_spline(x, y)
    assert np.max(np.abs(spline.predict(query) - np.sin(query))) < 0.01

    kernel = kernel_regression(x, y, bandwidth=0.25)
    assert np.mean(np.abs(kernel.predict(query) - np.sin(query))) < 0.08

    points = np.column_stack([np.cos(x), np.sin(x)])
    values = points[:, 0] + 2.0 * points[:, 1]
    rbf = rbf_interpolation(points, values, smoothing=1e-10)
    assert np.max(np.abs(rbf.predict(points) - values)) < 1e-5

    gp = gaussian_process(x, y, noise=1e-8, random_state=1)
    mean, std = gp.predict_with_uncertainty(query)
    assert np.mean(np.abs(mean - np.sin(query))) < 0.03
    assert np.all(std >= 0.0)


def test_response_regression_and_validation_metrics(prices):
    rng = np.random.default_rng(4)
    x = rng.uniform(-1.0, 1.0, size=(500, 2))
    y = 1.0 + 2.0 * x[:, 0] - 3.0 * x[:, 1] + 0.5 * x[:, 0] * x[:, 1]
    model = response_regression(x, y, method="polynomial", degree=2)
    predicted = model.predict(x)
    metrics = regression_metrics(y, predicted)
    assert metrics["RMSE"] < 1e-10
    assert metrics["MAE"] < 1e-10
    assert metrics["R2"] > 0.999999

    lab = QuantLab(prices)
    fitted = lab.approximate(x, y, method="polynomial", degree=2)
    assert regression_metrics(y, fitted.predict(x))["R2"] > 0.999999


def test_gradients_hessians_and_surface_sensitivities():
    function = lambda x, y: x**2 + 3.0 * x * y + 2.0 * y**2
    point = np.array([0.4, -0.7])
    gradient = finite_difference_gradient(function, point)
    hessian = finite_difference_hessian(function, point)
    expected_gradient = np.array([2 * point[0] + 3 * point[1], 3 * point[0] + 4 * point[1]])
    expected_hessian = np.array([[2.0, 3.0], [3.0, 4.0]])
    assert np.allclose(gradient, expected_gradient, atol=1e-5)
    assert np.allclose(hessian, expected_hessian, atol=1e-4)

    x = np.linspace(-1.0, 1.0, 31)
    y = np.linspace(-1.0, 1.0, 35)
    surface = evaluate_surface(function, x, y, x_name="x", y_name="y", z_name="z")
    first = surface.gradient()
    second = surface.hessian()
    center_x = np.argmin(np.abs(x - 0.0))
    center_y = np.argmin(np.abs(y - 0.0))
    assert abs(first["x"].z_values[center_y, center_x]) < 1e-10
    assert abs(first["y"].z_values[center_y, center_x]) < 1e-10
    assert np.isclose(second["xx"].z_values[center_y, center_x], 2.0, atol=0.02)
    assert np.isclose(second["xy"].z_values[center_y, center_x], 3.0, atol=0.02)
    assert np.isclose(second["yy"].z_values[center_y, center_x], 4.0, atol=0.02)
