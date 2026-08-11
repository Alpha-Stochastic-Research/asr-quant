# Universal Monte Carlo engine

ASRQuant 1.0.0 exposes the model-independent Monte Carlo contract

```text
generate scenarios -> compute one quantity per scenario -> reduce the outcomes
```

The central function is `run_monte_carlo`.

```python
import asrquant as asr


def generator(rng, n_scenarios, mean, volatility):
    return mean + volatility * rng.standard_normal(n_scenarios)

result = asr.run_monte_carlo(
    generator,
    n_scenarios=100_000,
    estimator="mean",
    parameters={"mean": 0.02, "volatility": 0.15},
    random_state=7,
)

print(result.summary)
```

The result reports the estimate, empirical mean, unbiased variance, standard deviation, Monte Carlo standard error, confidence interval for the mean, quantile, VaR and Expected Shortfall.

## Supported reducers

- `mean` or `expectation`;
- `probability`, for Boolean/indicator outcomes;
- `variance` and `std`;
- `quantile`;
- `var` or `value_at_risk` for positive losses;
- `cvar` or `expected_shortfall`;
- `median`, `min`, `max`;
- any user-supplied scalar reducer.

## Probability estimation

```python
probability = asr.run_monte_carlo(
    lambda rng, n: rng.standard_normal(n),
    lambda scenarios: scenarios > 1.96,
    n_scenarios=200_000,
    estimator="probability",
)
```

## Inverse transform and correlated variables

```python
from scipy.stats import expon

exponential = asr.uniform_inverse_transform(expon.ppf, 50_000)
correlated = asr.correlated_normal(
    mean=[0.0, 0.0],
    covariance=[[1.0, 0.7], [0.7, 1.5]],
    n_scenarios=50_000,
)
```

`correlated_normal` uses a Cholesky factor and validates symmetry and positive definiteness.

## Generic Euler-Maruyama

```python
paths = asr.euler_maruyama(
    drift=lambda t, x, mu: mu * x,
    diffusion=lambda t, x, sigma: sigma * x,
    initial=100.0,
    maturity=1.0,
    steps=252,
    paths=20_000,
    parameters={"mu": 0.05, "sigma": 0.20},
)
```

The simulator accepts scalar states, vector states, independent diffusion coefficients, constant diffusion matrices and path-specific diffusion matrices.

## Path-dependent hedging loss

```python
losses = asr.hedging_loss(
    payoff=payoff_per_path,
    prices=price_paths,
    positions=hedge_positions,
    premium=option_premium,
    cost_rate=0.001,
)

var_95 = asr.monte_carlo_value_at_risk(losses, 0.95)
cvar_95 = asr.monte_carlo_expected_shortfall(losses, 0.95)
```

The transaction-cost convention is

```text
sum_t kappa * S_t * abs(delta_t - delta_(t-1)).
```

## Static and animated Monte Carlo surfaces

```python
surface = asr.monte_carlo_parameter_surface(
    generator,
    quantity,
    {
        "transaction_cost": [0.0, 0.001, 0.002],
        "volatility": [0.10, 0.20, 0.30],
        "hedge_every": [1, 5, 20],
    },
    x="transaction_cost",
    y="volatility",
    animate_by="hedge_every",
    estimator="cvar",
    level=0.95,
    n_scenarios=20_000,
)

surface.plot("surface")
surface.animate(kind="surface")
surface.save_animation("cvar_surface.html")
```

This implements a general surface of the form

```text
statistic = f(theta_1, theta_2 | theta_3, theta_4, ...).
```
