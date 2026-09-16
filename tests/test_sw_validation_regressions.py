"""Regression tests for externally reported SW-002/SW-004/SW-006/SW-007/SW-009 findings."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import asrquant as asr
from asrquant import metrics


def test_find_003_key_rate_bumps_form_partition_on_irregular_grid():
    pillars = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0])
    base = asr.DiscountCurve.from_zero_rates(pillars, np.full_like(pillars, 0.03))
    bump = 1e-4
    weights = []
    base_rates = np.asarray(base.zero_rate(pillars), dtype=float)
    for key in pillars:
        bumped = base.bump_key_rate(float(key), bump)
        shifted = np.asarray(bumped.zero_rate(pillars), dtype=float)
        weights.append((shifted - base_rates) / bump)
    weight_sum = np.sum(np.vstack(weights), axis=0)
    assert np.allclose(weight_sum, 1.0, atol=1e-10, rtol=0.0)


def test_find_003_seven_year_bucket_does_not_bump_five_year_node():
    pillars = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0])
    base = asr.DiscountCurve.from_zero_rates(pillars, np.full_like(pillars, 0.03))
    bumped = base.bump_key_rate(7.0, 1e-4)
    shift_at_five = float(bumped.zero_rate(5.0) - base.zero_rate(5.0))
    assert abs(shift_at_five) < 1e-12


def test_find_011_psr_uses_observation_scale():
    returns = pd.Series([0.010, -0.006, 0.008, -0.003, 0.004, 0.001, -0.002, 0.006] * 20)
    r = returns.dropna()
    sr = float(r.mean() / r.std(ddof=1))
    skew = float(stats.skew(r, bias=False))
    kurt = float(stats.kurtosis(r, fisher=False, bias=False))
    denominator = np.sqrt(1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2)
    expected = float(stats.norm.cdf(sr * np.sqrt(len(r) - 1.0) / denominator))
    actual = metrics.probabilistic_sharpe_ratio(r, benchmark_sharpe=0.0, annualization=252)
    assert actual == pytest.approx(expected, abs=1e-12)


def test_find_011_psr_annualized_benchmark_is_scaled_consistently():
    returns = pd.Series([0.004, -0.003, 0.002, -0.001, 0.003, -0.002] * 30)
    annualization = 252
    benchmark_annual = 0.5
    r = returns.dropna()
    sr = float(r.mean() / r.std(ddof=1))
    benchmark_obs = benchmark_annual / np.sqrt(annualization)
    skew = float(stats.skew(r, bias=False))
    kurt = float(stats.kurtosis(r, fisher=False, bias=False))
    denominator = np.sqrt(1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2)
    expected = float(stats.norm.cdf((sr - benchmark_obs) * np.sqrt(len(r) - 1.0) / denominator))
    actual = metrics.probabilistic_sharpe_ratio(r, benchmark_annual, annualization)
    assert actual == pytest.approx(expected, abs=1e-12)


def test_find_012_statsmodels_015_removed_keywords_are_not_forwarded():
    rng = np.random.default_rng(42)
    x = pd.Series(rng.normal(size=120)).cumsum()
    y = 0.25 * x.shift(1).fillna(0.0) + pd.Series(rng.normal(size=120))
    fitted = asr.autoregression_fit(x, lags=2)
    assert np.isfinite(np.asarray(fitted.params, dtype=float)).all()
    granger = asr.stats.granger_causality(x, y, maxlag=2)
    assert list(granger.index) == [1, 2]
    assert np.isfinite(granger["p_value"]).all()


def test_find_013_rsi14_uses_wilder_smoothing():
    prices = pd.Series(
        [54.8, 56.8, 57.85, 59.85, 60.57, 61.1, 62.17, 60.6, 62.35, 62.15,
         62.35, 61.45, 62.8, 61.37, 62.5, 62.57, 60.8, 59.37, 60.35, 62.35,
         62.17, 62.55, 64.55, 64.37, 65.3, 64.42, 62.9, 61.6, 62.05, 60.05]
    )
    delta = prices.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.iloc[1:15].mean()
    avg_loss = losses.iloc[1:15].mean()
    expected = np.nan
    for i in range(15, len(prices)):
        avg_gain = (13.0 * avg_gain + gains.iloc[i]) / 14.0
        avg_loss = (13.0 * avg_loss + losses.iloc[i]) / 14.0
        expected = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    actual = float(asr.technical_features(prices)["rsi_14"].iloc[-1])
    assert actual == pytest.approx(expected, abs=1e-12)


def test_find_014_implied_volatility_refuses_intrinsic_boundary():
    spot, strike, maturity, rate = 100.0, 50.0, 1.0, 0.05
    intrinsic_bound = spot - strike * np.exp(-rate * maturity)
    with pytest.raises(ValueError, match="not identifiable"):
        asr.implied_volatility(
            intrinsic_bound,
            spot,
            strike,
            maturity,
            rate,
            option="call",
            model="black_scholes",
        )


def test_find_014_implied_volatility_still_inverts_identifiable_quotes():
    market = float(asr.black_scholes_price(100.0, 100.0, 1.0, 0.03, 0.2, "call"))
    implied = asr.implied_volatility(market, 100.0, 100.0, 1.0, 0.03, "call")
    assert implied == pytest.approx(0.2, abs=1e-10)


def test_find_015_pca_loadings_have_deterministic_sign_convention():
    rng = np.random.default_rng(42)
    panel = pd.DataFrame(
        rng.normal(size=(300, 5)).cumsum(axis=0),
        columns=["1Y", "2Y", "5Y", "10Y", "30Y"],
    )
    result = asr.yield_curve_pca(panel, n_components=3)
    loadings = result["loadings"]
    for column in loadings.columns:
        values = loadings[column].to_numpy(dtype=float)
        anchor = int(np.argmax(np.abs(values)))
        assert values[anchor] >= 0.0


def test_find_006_gaussian_process_honours_noise_contract():
    x = np.linspace(0.0, 1.0, 10)
    y = np.sin(2.0 * np.pi * x)
    fitted = asr.gaussian_process(x, y, noise=1e-6)
    model = fitted.model["regressor"]
    assert float(model.kernel_.k2.noise_level) == pytest.approx(1e-6, rel=0.0, abs=1e-15)
    assert float(fitted.metadata["noise"]) == pytest.approx(1e-6, rel=0.0, abs=1e-15)


def test_find_005_summary_exposes_nonzero_omega_threshold():
    returns = pd.Series([0.03, -0.01, 0.02, -0.015, 0.01, -0.005] * 10)
    summary = asr.summary_metrics(returns, omega_threshold=0.002)
    assert summary["Omega"] != pytest.approx(summary["Profit Factor"])
