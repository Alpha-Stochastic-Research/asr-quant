import pandas as pd
import pytest

from asrquant import BacktestSpec, CostModel
from asrquant.data import clean_prices, data_fingerprint, validate_ohlcv


def test_spec_fingerprint_is_stable():
    a = BacktestSpec(costs=CostModel(commission_bps=5))
    b = BacktestSpec(costs=CostModel(commission_bps=5))
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != b.with_updates(execution_delay=0).fingerprint()


def test_clean_prices_missing_policy(prices):
    damaged = prices.copy()
    damaged.iloc[3, 0] = float("nan")
    with pytest.raises(ValueError):
        clean_prices(damaged, "raise")
    assert not clean_prices(damaged, "ffill").isna().any().any()
    assert len(clean_prices(damaged, "drop")) == len(prices) - 1


def test_data_fingerprint_changes(prices):
    first = data_fingerprint(prices)
    changed = prices.copy()
    changed.iloc[0, 0] += 1
    assert first != data_fingerprint(changed)


def test_ohlc_validation():
    idx = pd.date_range("2024-01-01", periods=2)
    data = pd.DataFrame({"Open": [10, 11], "High": [12, 13], "Low": [9, 10], "Close": [11, 12], "Volume": [100, 120]}, index=idx)
    assert validate_ohlcv(data).shape == (2, 5)
