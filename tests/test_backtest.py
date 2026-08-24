import numpy as np
import pandas as pd

from asrquant import BacktestSpec, CostModel, QuantLab, run_backtest
from asrquant.strategies import sma_crossover


def test_buy_hold_one_asset_matches_returns(prices):
    one = prices[["A"]]
    weights = pd.DataFrame(1.0, index=one.index, columns=one.columns)
    result = run_backtest(one, weights, BacktestSpec(execution_delay=1, max_gross_leverage=1))
    expected = one.pct_change(fill_method=None).fillna(0).copy()
    expected.iloc[0] = 0
    assert np.allclose(result.net_returns.to_numpy()[1:], expected["A"].to_numpy()[1:])


def test_costs_reduce_equity(prices):
    weights = sma_crossover(prices, fast=5, slow=20)
    free = run_backtest(prices, weights, BacktestSpec(costs=CostModel()))
    costly = run_backtest(prices, weights, BacktestSpec(costs=CostModel(commission_bps=20)))
    assert costly.equity.iloc[-1] <= free.equity.iloc[-1]
    assert costly.costs.sum() > 0


def test_constraints_are_enforced(prices):
    raw = pd.DataFrame(5.0, index=prices.index, columns=prices.columns)
    spec = BacktestSpec(long_only=True, max_gross_leverage=1.2, max_abs_weight=0.8)
    result = run_backtest(prices, raw, spec)
    assert (result.target_weights >= 0).all().all()
    assert (result.target_weights.abs().sum(axis=1) <= 1.2 + 1e-12).all()
    assert (result.target_weights.abs() <= 0.8 + 1e-12).all().all()


def test_quantlab_five_line_api(prices, tmp_path):
    lab = QuantLab(prices)
    result = lab.backtest("sma", fast=10, slow=40, costs_bps=5)
    assert "Sharpe" in result.metrics
    output = tmp_path / "report.html"
    assert result.report(str(output)) == str(output)
    assert output.exists() and output.stat().st_size > 1_000


def test_execution_delay_changes_result(prices):
    weights = sma_crossover(prices, fast=5, slow=20)
    now = run_backtest(prices, weights, BacktestSpec(execution_delay=0))
    later = run_backtest(prices, weights, BacktestSpec(execution_delay=1))
    assert not np.allclose(now.net_returns, later.net_returns)
