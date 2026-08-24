import numpy as np
from scipy.stats import norm

from asrquant import (
    QuantLab,
    correlated_normal,
    euler_maruyama,
    hedging_loss,
    monte_carlo_parameter_surface,
    normal_samples,
    run_monte_carlo,
    uniform_inverse_transform,
)


def test_universal_monte_carlo_mean_probability_and_tail_statistics():
    def generator(rng, n_scenarios, mean=2.0, std=3.0):
        return mean + std * rng.standard_normal(n_scenarios)

    result = run_monte_carlo(
        generator,
        n_scenarios=100_000,
        estimator="mean",
        random_state=123,
        parameters={"mean": 2.0, "std": 3.0},
    )
    assert abs(result.estimate - 2.0) < 0.03
    assert result.standard_error > 0
    assert result.confidence_interval[0] < 2.0 < result.confidence_interval[1]
    assert abs(result.probability(lambda x: x > 2.0) - 0.5) < 0.01
    assert result.var(0.95) < result.cvar(0.95)
    assert result.summary["n_scenarios"] == 100_000


def test_indicator_probability_estimator():
    def generator(rng, n_scenarios, threshold=0.0):
        return rng.standard_normal(n_scenarios) > threshold

    result = run_monte_carlo(
        generator,
        n_scenarios=50_000,
        estimator="probability",
        random_state=4,
    )
    assert abs(result.estimate - 0.5) < 0.015


def test_inverse_transform_normal_and_correlated_normal():
    sample = uniform_inverse_transform(norm.ppf, 100_000, random_state=9)
    assert abs(sample.mean()) < 0.02
    assert abs(sample.std(ddof=1) - 1.0) < 0.02

    shifted = normal_samples(4.0, 2.0, 100_000, random_state=11)
    assert abs(shifted.mean() - 4.0) < 0.02

    covariance = np.array([[1.0, 0.6], [0.6, 2.0]])
    draws = correlated_normal([0.0, 1.0], covariance, 150_000, random_state=8)
    assert draws.shape == (150_000, 2)
    assert np.allclose(draws.mean(axis=0), [0.0, 1.0], atol=0.02)
    assert np.allclose(np.cov(draws, rowvar=False), covariance, atol=0.03)


def test_generic_euler_maruyama_matches_gbm_expectation():
    mu = 0.07
    sigma = 0.2
    paths = euler_maruyama(
        lambda t, x, mu=mu: mu * x,
        lambda t, x, sigma=sigma: sigma * x,
        100.0,
        maturity=1.0,
        steps=500,
        paths=60_000,
        random_state=3,
    )
    expected_terminal = 100.0 * np.exp(mu)
    assert paths.shape == (501, 60_000)
    assert abs(paths[-1].mean() - expected_terminal) / expected_terminal < 0.01


def test_path_dependent_hedging_loss_and_costs():
    prices = np.array(
        [
            [100.0, 100.0],
            [102.0, 98.0],
            [105.0, 96.0],
        ]
    )
    positions = np.array(
        [
            [0.5, 0.5],
            [0.7, 0.3],
            [0.0, 0.0],
        ]
    )
    payoff = np.array([5.0, 0.0])
    losses_no_cost = hedging_loss(payoff, prices, positions, premium=2.0, cost_rate=0.0)
    losses_with_cost = hedging_loss(payoff, prices, positions, premium=2.0, cost_rate=0.01)
    assert losses_no_cost.shape == (2,)
    assert np.all(losses_with_cost >= losses_no_cost)


def test_monte_carlo_parameter_surface_and_quantlab_wrapper(prices):
    def generator(rng, n_scenarios, mean, std, shift=0.0):
        return mean + shift + std * rng.standard_normal(n_scenarios)

    surface = monte_carlo_parameter_surface(
        generator,
        None,
        {"mean": [0.0, 1.0], "std": [0.5, 1.0], "shift": [0.0, 2.0]},
        x="mean",
        y="std",
        animate_by="shift",
        estimator="mean",
        n_scenarios=30_000,
        random_state=10,
    )
    assert surface.z_values.shape == (2, 2, 2)
    assert surface.frame_count == 2
    assert abs(surface.z_values[0, 0, 1] - 1.0) < 0.03
    assert abs(surface.z_values[1, 0, 1] - 3.0) < 0.03

    lab = QuantLab(prices[["A"]])
    wrapped = lab.monte_carlo_experiment(
        generator,
        n_scenarios=20_000,
        parameters={"mean": 1.0, "std": 0.5, "shift": 0.0},
        random_state=2,
    )
    assert abs(wrapped.estimate - 1.0) < 0.02
