import numpy as np
import pandas as pd

from asrquant.statistics import benjamini_hochberg, block_bootstrap, ols, rolling_regression, stationarity_tests


def test_ols_recovers_slope():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(size=400), name="factor")
    y = 0.2 + 1.5 * x + rng.normal(scale=0.2, size=400)
    result = ols(y, x, covariance="HAC")
    assert abs(result.coefficients["factor"] - 1.5) < 0.05
    assert "Ljung-Box p" in result.diagnostics


def test_rolling_regression_shape():
    x = pd.Series(np.arange(100, dtype=float), name="x")
    y = 2 * x + 1
    result = rolling_regression(y, x, window=20)
    assert result.shape[0] == 100
    assert "x" in result.columns


def test_stationarity_and_bootstrap(returns):
    tests = stationarity_tests(returns["A"])
    assert "ADF p-value" in tests
    ci = block_bootstrap(returns["A"], n_boot=100, random_state=1)
    assert ci["lower"] <= ci["upper"]


def test_bh_monotonic_adjustment():
    result = benjamini_hochberg([0.001, 0.01, 0.2, 0.9])
    assert ((result["adjusted_p"] >= 0) & (result["adjusted_p"] <= 1)).all()
    assert result.iloc[0]["reject"]
