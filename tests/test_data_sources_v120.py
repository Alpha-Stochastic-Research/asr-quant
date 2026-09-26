from io import StringIO
import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def test_data_load_local_csv(tmp_path):
    path = tmp_path / "prices.csv"
    pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "A": [100, 101]}).to_csv(path, index=False)
    out = asr.data.load(path, date_column="Date")
    assert out.index.is_monotonic_increasing
    assert out["A"].iloc[-1] == 101


def test_data_load_http_csv(monkeypatch):
    class Response:
        text = "Date,A\n2024-01-01,100\n2024-01-02,101\n"
        content = text.encode()
        headers = {"content-type": "text/csv"}
        def raise_for_status(self):
            return None
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: Response())
    out = asr.data.load("https://example.test/prices.csv", date_column="Date")
    assert out.shape == (2, 1)
    assert out.iloc[-1, 0] == 101


def test_data_load_yahoo_provider_contract(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=3, tz="UTC")
    frame = pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=idx)

    class FakeYahoo:
        def history(self, symbol, **kwargs):
            assert symbol in {"SPY", "TLT"}
            return frame

    monkeypatch.setattr("asrquant.providers.get_provider", lambda name, **kwargs: FakeYahoo())
    out = asr.data.from_provider("yahoo", ["SPY", "TLT"], start="2024-01-01")
    assert out.columns.tolist() == ["SPY", "TLT"]
    assert out.iloc[-1].tolist() == [102.0, 102.0]


def test_data_ecb_yield_curve_contract(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=2, tz="UTC")
    fake = pd.DataFrame({"3M": [0.02, 0.021], "1Y": [0.025, 0.026]}, index=idx)
    fake.attrs["provider"] = "ECB"

    def fake_curve(self, **kwargs):
        assert kwargs["maturities"] == ["3M", "1Y"]
        return fake.copy()

    monkeypatch.setattr("asrquant.providers.ECBProvider.yield_curve_history", fake_curve)
    out = asr.data.ecb_yield_curve(["3M", "1Y"], start="2024-01-01")
    assert out.attrs["provider"] == "ECB"
    assert out.columns.tolist() == ["3M", "1Y"]


def test_data_validate_reports_instead_of_mutating():
    idx = pd.to_datetime(["2024-01-02", "2024-01-01", "2024-01-01"])
    frame = pd.DataFrame({"A": [1.0, np.nan, np.inf]}, index=idx)
    original = frame.copy(deep=True)
    result = asr.data.validate(frame)
    assert result.metrics["duplicate_timestamps"] == 1
    assert result.metrics["infinite_values"] == 1
    assert not result.is_clean
    pd.testing.assert_frame_equal(frame, original)
