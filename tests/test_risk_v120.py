import numpy as np
import pandas as pd
import pytest

from asrquant import risk


def returns_panel(rows=2000, seed=11):
    rng = np.random.default_rng(seed)
    cov = np.array([
        [0.0001, 0.00003, 0.00001],
        [0.00003, 0.0002, 0.00002],
        [0.00001, 0.00002, 0.00015],
    ])
    values = rng.multivariate_normal([0.0002, 0.0001, 0.00015], cov, size=rows)
    return pd.DataFrame(values, columns=["A", "B", "C"])


def test_portfolio_returns_fixed_weights():
    frame = pd.DataFrame({"A": [0.01, 0.02], "B": [0.03, -0.01]})
    out = risk.portfolio_returns(frame, pd.Series({"A": 0.6, "B": 0.4}))
    assert out.iloc[0] == pytest.approx(0.018)
    assert out.iloc[1] == pytest.approx(0.008)


def test_covariance_risk_contributions_sum_to_volatility():
    cov = pd.DataFrame([[0.04, 0.01], [0.01, 0.09]], index=["A", "B"], columns=["A", "B"])
    contrib = risk.covariance_risk_contributions(pd.Series({"A": 0.4, "B": 0.6}), cov)
    weights = np.array([0.4, 0.6])
    expected_vol = np.sqrt(weights @ cov.to_numpy() @ weights)
    assert contrib["component_volatility"].sum() == pytest.approx(expected_vol)
    assert contrib["percent_total"].sum() == pytest.approx(1.0)


def test_var_and_es_are_loss_positive_and_es_exceeds_var():
    frame = returns_panel()
    weights = [0.4, 0.35, 0.25]
    var = risk.portfolio_var(frame, weights, level=0.975, method="historical")
    es = risk.portfolio_expected_shortfall(frame, weights, level=0.975, method="historical")
    assert var > 0
    assert es >= var


def test_gaussian_var_is_close_to_historical_for_normal_sample():
    frame = returns_panel(rows=10000)
    weights = [0.4, 0.35, 0.25]
    historical = risk.portfolio_var(frame, weights, level=0.95, method="historical")
    gaussian = risk.portfolio_var(frame, weights, level=0.95, method="gaussian")
    assert gaussian == pytest.approx(historical, rel=0.08)


def test_es_contributions_add_to_tail_loss_mean():
    frame = returns_panel(rows=3000)
    weights = pd.Series({"A": 0.4, "B": 0.35, "C": 0.25})
    contributions = risk.expected_shortfall_contributions(frame, weights, level=0.95)
    es = risk.portfolio_expected_shortfall(frame, weights, level=0.95, method="historical")
    assert contributions.sum() == pytest.approx(es, rel=1e-12, abs=1e-12)


def test_scenario_pnl_has_exact_additive_decomposition():
    scenarios = pd.DataFrame(
        {"A": [-0.10, 0.03], "B": [-0.05, -0.02], "C": [0.01, 0.04]},
        index=["risk_off", "rebound"],
    )
    out = risk.scenario_pnl([0.5, 0.3, 0.2], scenarios, capital=1_000_000)
    assert np.allclose(out[["A", "B", "C"]].sum(axis=1), out["portfolio_pnl"])
    assert out.loc["risk_off", "portfolio_pnl"] < 0


def test_portfolio_risk_report_end_to_end():
    frame = returns_panel(rows=1500)
    report = risk.portfolio_risk_report(frame, [0.4, 0.35, 0.25], level=0.95)
    assert report.summary["annualized_volatility"] > 0
    assert report.volatility_contributions["percent_total"].sum() == pytest.approx(1.0)
    assert report.expected_shortfall_contributions.sum() > 0

def test_gaussian_es_and_cornish_fisher_var_are_finite():
    frame = returns_panel(rows=2500)
    weights = [0.4, 0.35, 0.25]
    es = risk.portfolio_expected_shortfall(frame, weights, level=0.99, method="gaussian")
    cf = risk.portfolio_var(frame, weights, level=0.99, method="cornish_fisher")
    assert np.isfinite(es) and es > 0
    assert np.isfinite(cf) and cf > 0


def test_covariance_ndarray_and_named_assets():
    cov = np.array([[0.04, 0.0], [0.0, 0.09]])
    out = risk.covariance_risk_contributions([0.5, 0.5], cov, asset_names=["X", "Y"])
    assert out.index.tolist() == ["X", "Y"]
    assert out["percent_total"].sum() == pytest.approx(1.0)


def test_horizon_and_rolling_var():
    frame = returns_panel(rows=300)
    weights = [0.4, 0.35, 0.25]
    var5 = risk.portfolio_var(frame, weights, level=0.95, method="historical", horizon=5)
    rolling = risk.rolling_var(frame, weights, window=100, level=0.95)
    assert np.isfinite(var5)
    assert rolling.notna().sum() == len(frame) - 99


def test_risk_input_validation():
    frame = returns_panel(rows=20)
    with pytest.raises(ValueError):
        risk.portfolio_var(frame, [0.3, 0.3], level=0.95)
    with pytest.raises(ValueError):
        risk.portfolio_var(frame, [0.3, 0.3, 0.4], level=1.0)
    with pytest.raises(ValueError):
        risk.portfolio_var(frame, [0.3, 0.3, 0.4], method="unsupported")
    with pytest.raises(ValueError):
        risk.portfolio_expected_shortfall(frame, [0.3, 0.3, 0.4], method="cf")
    with pytest.raises(ValueError):
        risk.scenario_pnl([0.5, 0.5], pd.DataFrame({"A": [-0.1], "B": [0.1]}), capital=0)
    with pytest.raises(ValueError):
        risk.rolling_var(frame, [0.3, 0.3, 0.4], window=1)
    nonsymmetric = np.array([[1.0, 0.2], [0.1, 1.0]])
    with pytest.raises(ValueError):
        risk.covariance_risk_contributions([0.5, 0.5], nonsymmetric)
