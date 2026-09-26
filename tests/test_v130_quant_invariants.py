from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def test_black_scholes_put_call_parity_random_grid():
    rng = np.random.default_rng(1)
    for _ in range(100):
        s = rng.uniform(50, 150)
        k = rng.uniform(50, 150)
        t = rng.uniform(0.05, 5)
        r = rng.uniform(-0.01, 0.08)
        q = rng.uniform(0, 0.04)
        vol = rng.uniform(0.05, 0.8)
        call = float(asr.black_scholes_price(s, k, t, r, vol, "call", q))
        put = float(asr.black_scholes_price(s, k, t, r, vol, "put", q))
        rhs = s * np.exp(-q * t) - k * np.exp(-r * t)
        assert call - put == pytest.approx(rhs, rel=1e-10, abs=1e-10)


def test_discount_zero_roundtrip_random_grid():
    rng = np.random.default_rng(2)
    rates = rng.uniform(-0.02, 0.10, 100)
    times = rng.uniform(0.05, 30, 100)
    discounts = asr.rates.discount_factor(rates, times)
    recovered = asr.rates.zero_rate_from_discount(discounts, times)
    np.testing.assert_allclose(recovered, rates, rtol=1e-12, atol=1e-12)


def test_generic_calibration_recovers_linear_parameters():
    x = np.linspace(0, 2, 50)
    y = 1.5 + 2.25 * x
    problem = asr.calibration.CalibrationProblem(
        lambda xx, p: p["a"] + p["b"] * xx,
        x,
        y,
        {"a": 0.0, "b": 1.0},
    )
    result = problem.solve()
    assert result.success
    assert result.parameters["a"] == pytest.approx(1.5, abs=1e-8)
    assert result.parameters["b"] == pytest.approx(2.25, abs=1e-8)
    assert result.rmse < 1e-9


def test_generic_sensitivities_quadratic():
    result = asr.sensitivities.compute(lambda x, y: x * x + 3 * x * y + y * y, {"x": 2.0, "y": -1.0}, cross=True)
    assert result.first_order["x"] == pytest.approx(2 * 2 + 3 * -1, rel=1e-6)
    assert result.first_order["y"] == pytest.approx(3 * 2 + 2 * -1, rel=1e-6)
    assert result.second_order["x"] == pytest.approx(2.0, rel=1e-4)
    assert result.cross_greeks.loc["x", "y"] == pytest.approx(3.0, rel=1e-4)


def test_cost_model_nonnegative_and_composite():
    context = asr.costs.CostContext(trade_value=1_000_000, adv_value=20_000_000, volatility=0.02, spread_bps=4)
    model = asr.costs.CompositeCostModel(asr.costs.FixedBps(1), asr.costs.HalfSpread(), asr.costs.SquareRootImpact(0.2))
    estimate = model.estimate(context)
    assert estimate.total_cost > 0
    assert estimate.total_bps > 0
    assert estimate.breakdown.sum() == pytest.approx(estimate.total_cost)


def test_cost_aware_portfolio_respects_bounds_and_turnover():
    rng = np.random.default_rng(3)
    returns = pd.DataFrame(rng.normal(0.0004, 0.01, size=(300, 4)), columns=list("ABCD"))
    current = pd.Series(0.25, index=returns.columns)
    constraints = asr.portfolio.Constraints(max_weight=0.40, turnover_limit=0.20)
    result = asr.portfolio.cost_aware_optimize(
        returns,
        current_weights=current,
        constraints=constraints,
        turnover_penalty=0.01,
    )
    assert result.weights.sum() == pytest.approx(1.0, abs=1e-7)
    assert result.weights.max() <= 0.400001
    assert np.abs(result.weights - current).sum() <= 0.200001


def test_risk_budgeting_sums_to_one():
    cov = pd.DataFrame([[0.04, 0.01], [0.01, 0.09]], index=["A", "B"], columns=["A", "B"])
    w = asr.portfolio.risk_budgeting(cov, [0.4, 0.6])
    assert w.sum() == pytest.approx(1.0)
    assert (w > 0).all()


def test_evt_quantiles_increase():
    rng = np.random.default_rng(4)
    losses = pd.Series(rng.standard_t(df=4, size=2000) * 0.01)
    fit = asr.risk.evt(losses, threshold_quantile=0.90)
    assert fit.var(0.99) > fit.var(0.95)
    assert fit.expected_shortfall(0.99) >= fit.var(0.99)


def test_copula_simulation_and_tail_dependence():
    rng = np.random.default_rng(5)
    data = pd.DataFrame(rng.multivariate_normal([0, 0], [[1, 0.6], [0.6, 1]], size=500), columns=["A", "B"])
    gauss = asr.dependence.GaussianCopula.fit(data)
    student = asr.dependence.StudentTCopula.fit(data, df=5)
    assert gauss.tail_dependence().loc["A", "B"] == pytest.approx(0.0)
    assert student.tail_dependence().loc["A", "B"] > 0
    sim = student.simulate(1000)
    assert ((sim > 0) & (sim < 1)).all().all()


def test_qmc_and_control_variate():
    z = asr.mc.sobol_normal_samples(1024, dim=2, random_state=1)
    assert z.shape == (1024, 2)
    assert abs(z.mean()) < 0.02
    rng = np.random.default_rng(6)
    x = rng.normal(size=2000)
    y = x + rng.normal(scale=0.5, size=2000)
    cv = asr.mc.control_variate(y, x, known_control_mean=0.0)
    assert cv.adjusted_variance < cv.raw_variance
