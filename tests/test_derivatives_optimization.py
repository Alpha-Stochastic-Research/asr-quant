import numpy as np

from asrquant.derivatives import black_scholes_greeks, black_scholes_price, implied_volatility, simulate_gbm
from asrquant.optimization import equal_risk_contribution, maximum_sharpe, minimum_variance, risk_contributions


def test_put_call_parity():
    s, k, t, r, v = 100, 105, 1.2, 0.03, 0.25
    call = black_scholes_price(s, k, t, r, v, "call")
    put = black_scholes_price(s, k, t, r, v, "put")
    assert abs((call - put) - (s - k * np.exp(-r * t))) < 1e-10


def test_implied_vol_recovers_input():
    price = black_scholes_price(100, 100, 1, 0.02, 0.3)
    assert abs(implied_volatility(float(price), 100, 100, 1, 0.02) - 0.3) < 1e-8


def test_greeks_and_simulation():
    greeks = black_scholes_greeks(100, 100, 1, 0.02, 0.2)
    assert greeks["gamma"] > 0
    paths = simulate_gbm(100, 0.05, 0.2, 1, steps=12, paths=50)
    assert paths.shape == (13, 50)
    assert np.allclose(paths.iloc[0], 100)


def test_optimizers_sum_to_one():
    mu = np.array([0.05, 0.08, 0.11])
    cov = np.array([[0.04, 0.01, 0.005], [0.01, 0.06, 0.015], [0.005, 0.015, 0.09]])
    for weights in [minimum_variance(cov), maximum_sharpe(mu, cov), equal_risk_contribution(cov)]:
        assert abs(weights.sum() - 1) < 1e-6
        assert np.all(weights >= -1e-8)
    rc = risk_contributions(equal_risk_contribution(cov), cov)
    assert np.std(rc) < 1e-5
