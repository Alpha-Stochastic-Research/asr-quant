import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

import asrquant as asr


def sample_prices(n=320):
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    returns = rng.normal(0.00025, 0.01, size=(n, 3))
    prices = 100 * pd.DataFrame(np.exp(np.cumsum(returns, axis=0)), index=idx, columns=["A", "B", "C"])
    return prices


def test_canonical_namespaces_are_installed():
    assert callable(asr.data.load)
    assert callable(asr.data.validate)
    assert callable(asr.backtesting.run)
    assert callable(asr.portfolio.optimize)
    assert callable(asr.options.price)
    assert callable(asr.rates.analyze)
    assert callable(asr.rates.calibrate)
    assert callable(asr.stats.regress)
    assert callable(asr.ml.fit)


def test_data_validate_reports_duplicates_without_mutating_input():
    prices = sample_prices(20)
    duplicate = pd.concat([prices.iloc[:5], prices.iloc[[4]], prices.iloc[5:]])
    original = duplicate.copy()
    result = asr.data.validate(duplicate)
    assert result.metrics["duplicate_timestamps"] == 1
    assert not result.is_clean
    pd.testing.assert_frame_equal(duplicate, original)
    assert "duplicate timestamps" in " ".join(result.issues)


def test_backtest_result_has_common_contract():
    prices = sample_prices(80)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    weights["A"] = 1.0
    result = asr.backtesting.run(prices, weights)
    assert result.summary["Total Return"] == pytest.approx(result.metrics["Total Return"])
    assert {"net_return", "equity", "turnover"}.issubset(result.to_frame().columns)
    payload = result.to_dict()
    assert payload["result_type"] == "backtest"
    assert payload["fingerprint"] == result.fingerprint


def test_portfolio_optimize_returns_named_result():
    returns = sample_prices(180).pct_change().dropna()
    result = asr.portfolio.optimize(returns, method="minimum_variance")
    assert result.method == "minimum_variance"
    assert result.weights.sum() == pytest.approx(1.0, abs=1e-7)
    assert list(result.weights.index) == list(returns.columns)
    assert result.volatility >= 0
    assert result.to_frame().columns.tolist() == ["weight"]
    assert result.fingerprint


def test_portfolio_hrp_and_max_sharpe():
    returns = sample_prices(220).pct_change().dropna()
    hrp = asr.portfolio.optimize(returns, method="hrp")
    assert hrp.weights.sum() == pytest.approx(1.0, abs=1e-7)
    tangency = asr.portfolio.optimize(returns, method="max_sharpe")
    assert tangency.weights.sum() == pytest.approx(1.0, abs=1e-6)


def test_option_price_uses_common_result_helpers_and_domain_error():
    result = asr.options.price(
        "black_scholes",
        spot=100.0,
        strike=100.0,
        maturity=1.0,
        rate=0.03,
        volatility=0.20,
        option="call",
    )
    assert result.price > 0
    assert result.to_dict()["result_type"] == "option_price"
    assert "price" in result.to_frame().index
    with pytest.raises(asr.contracts.PricingError):
        asr.options.price(
            "black_scholes",
            spot=-1.0,
            strike=100.0,
            maturity=1.0,
            rate=0.03,
            volatility=0.20,
        )


def test_statistics_regress_standardizes_classical_and_regularized_results():
    rng = np.random.default_rng(11)
    idx = pd.date_range("2024-01-01", periods=180, freq="B")
    x = pd.DataFrame({"x1": rng.normal(size=len(idx)), "x2": rng.normal(size=len(idx))}, index=idx)
    y = pd.Series(0.5 + 0.8 * x.x1 - 0.3 * x.x2 + rng.normal(scale=0.2, size=len(idx)), index=idx)

    ols = asr.stats.regress(y, x, method="ols", covariance="HC1")
    assert "coefficient:x1" in ols.summary.index
    assert {"fitted", "residual"}.issubset(ols.to_frame().columns)
    assert ols.to_dict()["result_type"] == "regression"

    ridge = asr.stats.regress(y, x, method="ridge", alpha=1.0)
    assert ridge.summary["r2"] > 0.5
    assert ridge.to_dict()["result_type"] == "model_fit"


def test_ml_fit_common_contract_and_prevalidation():
    prices = sample_prices(260)["A"]
    features = pd.DataFrame({
        "r1": prices.pct_change(),
        "r5": prices.pct_change(5),
        "vol": prices.pct_change().rolling(10).std(),
    })
    target = prices.pct_change().shift(-1)
    result = asr.ml.fit(
        Ridge(alpha=1.0),
        features,
        target,
        train_size=100,
        test_size=30,
        step=30,
    )
    assert "rmse" in result.summary.index
    assert {"actual", "prediction"}.issubset(result.to_frame().columns)
    assert result.to_dict()["result_type"] == "walk_forward_ml"

    with pytest.raises(asr.contracts.InputValidationError):
        asr.ml.fit(Ridge(), features.iloc[:20], target.iloc[:20], train_size=20, test_size=10)


def test_rate_curve_analyze_common_contract():
    curve = asr.rates.DiscountCurve.from_zero_rates(
        [0.5, 1.0, 2.0, 5.0, 10.0],
        [0.02, 0.021, 0.023, 0.028, 0.03],
    )
    result = asr.rates.analyze(curve)
    assert result.summary["nodes"] == 5
    assert "positive_discounts" in result.diagnostics.index
    assert result.to_dict()["result_type"] == "curve_analysis"


def test_rate_calibration_dispatcher():
    maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0])
    synthetic = np.asarray(asr.rates.nelson_siegel_yield(maturities, 0.032, -0.018, 0.012, 2.5))
    result = asr.rates.calibrate("nelson_siegel", maturities, synthetic)
    assert result.success
    assert result.rmse < 1e-6
