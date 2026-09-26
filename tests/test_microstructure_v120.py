import numpy as np
import pandas as pd
import pytest

from asrquant import microstructure as micro


def test_midquote_and_spread():
    bid = pd.Series([99.0, 100.0])
    ask = pd.Series([101.0, 102.0])
    assert micro.midquote(bid, ask).tolist() == [100.0, 101.0]
    assert micro.quoted_spread(bid, ask).tolist() == [2.0, 2.0]
    assert micro.quoted_spread(bid, ask, relative=True).iloc[0] == pytest.approx(0.02)


def test_microprice_moves_toward_ask_when_bid_depth_dominates():
    bid = pd.Series([99.0])
    ask = pd.Series([101.0])
    value = micro.microprice(bid, ask, pd.Series([9.0]), pd.Series([1.0])).iloc[0]
    assert 100.0 < value < 101.0
    assert value == pytest.approx(100.8)


def test_spread_decomposition_identity():
    trade = pd.Series([101.0, 99.0])
    mid = pd.Series([100.0, 100.0])
    future = pd.Series([100.4, 99.6])
    side = pd.Series([1.0, -1.0])
    effective = micro.effective_spread(trade, mid, side)
    realized = micro.realized_spread(trade, future, side)
    impact = micro.price_impact(mid, future, side)
    assert np.allclose(effective, realized + impact)


def test_order_flow_imbalance_signs_quote_improvement():
    bid = pd.Series([100.0, 100.1, 100.1])
    ask = pd.Series([100.2, 100.2, 100.3])
    bid_size = pd.Series([10.0, 12.0, 15.0])
    ask_size = pd.Series([10.0, 9.0, 8.0])
    ofi = micro.order_flow_imbalance(bid, ask, bid_size, ask_size)
    assert ofi.iloc[0] == 0.0
    assert ofi.iloc[1] > 0


def test_amihud_is_positive():
    returns = pd.Series([0.01, -0.005, 0.002, -0.001])
    volume = pd.Series([1e6, 2e6, 1.5e6, 1.2e6])
    value = micro.amihud_illiquidity(returns, volume, window=None)
    assert value > 0


def test_roll_spread_detects_bid_ask_bounce():
    prices = pd.Series([100.1, 99.9, 100.1, 99.9, 100.1, 99.9, 100.1, 99.9])
    spread = micro.roll_spread(prices)
    assert spread > 0


def test_kyle_lambda_recovers_linear_price_impact():
    rng = np.random.default_rng(4)
    flow = pd.Series(rng.normal(size=500))
    true_lambda = 2.5e-4
    price_change = 0.001 + true_lambda * flow + rng.normal(scale=1e-5, size=len(flow))
    result = micro.kyle_lambda(pd.Series(price_change), flow)
    assert result.lambda_ == pytest.approx(true_lambda, rel=0.03)
    assert result.r_squared > 0.95

def test_effective_spread_without_side_and_relative_variants():
    trade = pd.Series([100.1, 99.9])
    mid = pd.Series([100.0, 100.0])
    spread = micro.effective_spread(trade, mid)
    rel = micro.effective_spread(trade, mid, relative=True)
    assert np.allclose(spread, [0.2, 0.2])
    assert np.allclose(rel, [0.002, 0.002])


def test_relative_realized_spread_and_price_impact():
    trade = pd.Series([100.1])
    mid = pd.Series([100.0])
    future = pd.Series([100.04])
    side = pd.Series([1.0])
    realized = micro.realized_spread(trade, future, side, relative_to=mid)
    impact = micro.price_impact(mid, future, side, relative=True)
    effective = micro.effective_spread(trade, mid, side, relative=True)
    assert effective.iloc[0] == pytest.approx(realized.iloc[0] + impact.iloc[0])


def test_rolling_amihud_and_roll_spread():
    r = pd.Series([0.01, -0.01, 0.005, -0.005, 0.002, -0.002])
    volume = pd.Series([1e6] * len(r))
    amihud = micro.amihud_illiquidity(r, volume, window=3)
    assert amihud.notna().sum() == 4
    prices = pd.Series([100.1, 99.9, 100.1, 99.9, 100.1, 99.9, 100.1, 99.9, 100.1])
    roll = micro.roll_spread(prices, window=4)
    assert roll.notna().sum() > 0


def test_kyle_lambda_without_intercept():
    flow = pd.Series(np.linspace(-2, 2, 100))
    result = micro.kyle_lambda(0.002 * flow, flow, add_constant=False)
    assert result.lambda_ == pytest.approx(0.002)
    assert result.intercept == 0.0
    assert result.r_squared == pytest.approx(1.0)


def test_microstructure_validation():
    with pytest.raises(ValueError):
        micro.midquote([101.0], [100.0])
    with pytest.raises(ValueError):
        micro.microprice([99.0], [101.0], [-1.0], [2.0])
    with pytest.raises(ValueError):
        micro.effective_spread([100.1], [100.0], side=[0.0])
    with pytest.raises(ValueError):
        micro.amihud_illiquidity([0.01], [0.0], window=None)
    with pytest.raises(ValueError):
        micro.roll_spread([100.0, 100.1])
    with pytest.raises(ValueError):
        micro.kyle_lambda([0.1, 0.2, 0.3], [1.0, 1.0, 1.0])
