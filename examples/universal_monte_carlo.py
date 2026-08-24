"""Universal Monte Carlo: expectation, probability, tail risk and surfaces."""
import numpy as np
import asrquant as asr


def normal_generator(rng, n_scenarios, mean, volatility, threshold=0.0):
    return mean + volatility * rng.standard_normal(n_scenarios)


expectation = asr.run_monte_carlo(
    normal_generator,
    n_scenarios=100_000,
    estimator="mean",
    parameters={"mean": 0.02, "volatility": 0.15, "threshold": 0.0},
    random_state=7,
)
print(expectation.summary)

probability = asr.run_monte_carlo(
    normal_generator,
    lambda scenarios, threshold, **_: scenarios < threshold,
    n_scenarios=100_000,
    estimator="probability",
    parameters={"mean": 0.02, "volatility": 0.15, "threshold": -0.20},
    random_state=7,
)
print("P(return < -20%) =", probability.estimate)

surface = asr.monte_carlo_parameter_surface(
    normal_generator,
    lambda scenarios, **_: -scenarios,
    {
        "mean": [-0.02, 0.00, 0.02],
        "volatility": [0.10, 0.20, 0.30],
        "threshold": [0.0, 0.05],
    },
    x="mean",
    y="volatility",
    animate_by="threshold",
    estimator="cvar",
    level=0.95,
    n_scenarios=50_000,
    random_state=11,
    z_name="CVaR 95%",
)

surface.save_animation("monte_carlo_cvar_surface.html", kind="surface")
