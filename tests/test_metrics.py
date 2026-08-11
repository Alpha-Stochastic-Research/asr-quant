import numpy as np
import pandas as pd

from asrquant.metrics import (
    annualized_return,
    annualized_volatility,
    deflated_sharpe_ratio,
    drawdown_series,
    expected_shortfall,
    max_drawdown,
    sharpe_ratio,
    summary_metrics,
    value_at_risk,
)


def test_known_constant_returns():
    r = pd.Series([0.01] * 12)
    assert annualized_return(r, 12) == pytest_approx((1.01**12) - 1)
    assert annualized_volatility(r, 12) == 0
    assert np.isnan(sharpe_ratio(r, annualization=12))


def pytest_approx(value, tol=1e-12):
    class Approx:
        def __eq__(self, other):
            return abs(other - value) <= tol
    return Approx()


def test_drawdown_and_tail_metrics():
    r = pd.Series([0.1, -0.2, 0.05, -0.1])
    dd = drawdown_series(r)
    assert max_drawdown(r) == dd.min()
    assert expected_shortfall(r, 0.75) >= value_at_risk(r, 0.75)


def test_summary_metrics_contains_core(returns):
    metrics = summary_metrics(returns["A"], turnover=pd.Series(0.1, index=returns.index))
    for name in ["CAGR", "Sharpe", "Max Drawdown", "ES 95%", "Annual Turnover"]:
        assert name in metrics.index


def test_dsr_bounds(returns):
    value = deflated_sharpe_ratio(returns["A"], trials=100)
    assert 0 <= value <= 1
