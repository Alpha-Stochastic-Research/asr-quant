"""Interpolation, Gaussian-process uncertainty, gradients and Hessians."""
import numpy as np
import asrquant as asr

rng = np.random.default_rng(7)
points = rng.uniform([0.0, 0.10], [0.04, 0.40], size=(60, 2))
values = 5.0 + 80.0 * points[:, 0] + 12.0 * points[:, 1] + 100.0 * points[:, 0] * points[:, 1]

gp = asr.gaussian_process(points, values, noise=1e-8)
query = np.array([[0.015, 0.20], [0.030, 0.30]])
mean, uncertainty = gp.predict_with_uncertainty(query)
print("GP mean:", mean)
print("GP uncertainty:", uncertainty)

surface = asr.evaluate_surface(
    lambda transaction_cost, volatility: (
        5.0
        + 80.0 * transaction_cost
        + 12.0 * volatility
        + 100.0 * transaction_cost * volatility
    ),
    np.linspace(0.0, 0.04, 41),
    np.linspace(0.10, 0.40, 41),
    x_name="transaction_cost",
    y_name="volatility",
    z_name="CVaR",
)

surface.plot("surface")
surface.gradient()["transaction_cost"].plot("heatmap")
surface.hessian()["transaction_costvolatility"].plot("contour")
