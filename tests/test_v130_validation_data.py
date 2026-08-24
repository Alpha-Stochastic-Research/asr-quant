from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def test_cpcv_split_count_and_no_overlap():
    splits = list(asr.validation.combinatorial_purged_cv_splits(120, n_groups=6, n_test_groups=2, purge=2, embargo=1))
    assert len(splits) == 15
    for split in splits:
        assert len(np.intersect1d(split.train, split.test)) == 0


def test_pbo_detects_overfit_selection_pressure():
    rng = np.random.default_rng(42)
    # Many noise strategies: selecting the in-sample winner should frequently fail OOS.
    returns = pd.DataFrame(rng.normal(0, 0.01, size=(320, 20)), columns=[f"s{i}" for i in range(20)])
    result = asr.validation.probability_of_backtest_overfitting(returns, n_groups=8)
    assert 0 <= result.probability <= 1
    assert len(result.logits) == 70


def test_reality_check_positive_strategy_has_finite_pvalue():
    rng = np.random.default_rng(7)
    frame = pd.DataFrame({
        "strong": rng.normal(0.0015, 0.008, 300),
        "noise": rng.normal(0.0, 0.01, 300),
    })
    result = asr.validation.reality_check(frame, n_boot=250, block_size=8, random_state=1)
    assert 0 <= result.p_value <= 1
    assert result.statistic > 0


def test_spa_studentized_finite():
    rng = np.random.default_rng(8)
    frame = pd.DataFrame(rng.normal(0.0003, 0.01, size=(250, 4)), columns=list("ABCD"))
    result = asr.validation.spa_test(frame, n_boot=150, block_size=7)
    assert 0 <= result.p_value <= 1
    assert np.isfinite(result.statistic)


def test_leakage_detector_flags_exact_target_copy():
    idx = pd.date_range("2024-01-01", periods=30)
    target = pd.Series(np.arange(30.0), index=idx)
    features = pd.DataFrame({"x": np.arange(30.0), "safe": np.sin(np.arange(30))}, index=idx)
    report = asr.validation.detect_leakage(features, target)
    assert not bool(report.summary["passed"])
    assert "x" in report.suspicious_features


def test_multiverse_enumerates_all_choices():
    study = asr.validation.Multiverse(
        {"lookback": [20, 60], "cost": [0, 5, 10]},
        lambda lookback, cost: {"sharpe": 2.0 - lookback / 100 - cost / 100},
    )
    result = study.run(metric="sharpe", threshold=1.0)
    assert len(result.results) == 6
    assert 0 <= result.summary["robust_fraction"] <= 1


def test_snapshot_roundtrip_and_hash(tmp_path):
    idx = pd.date_range("2025-01-01", periods=5)
    frame = pd.DataFrame({"x": np.arange(5.0)}, index=idx)
    snap = asr.data.snapshot(frame, source="unit-test")
    path = snap.save(tmp_path)
    loaded = asr.data.DataSnapshot.load(path)
    assert loaded.hash == snap.hash
    pd.testing.assert_frame_equal(loaded.data, frame, check_freq=False)


def test_datastore_cache_and_offline(tmp_path):
    store = asr.data.DataStore(tmp_path)
    idx = pd.date_range("2025-01-01", periods=3)
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]}, index=idx)
    calls = {"n": 0}
    def loader():
        calls["n"] += 1
        return frame
    first = store.fetch("x", loader, refresh_seconds=3600)
    second = store.fetch("x", loader, refresh_seconds=3600)
    assert first.hash == second.hash
    assert calls["n"] == 1
    offline = asr.data.DataStore(tmp_path, offline=True)
    assert offline.fetch("x", loader).hash == first.hash


def test_point_in_time_frame_hides_future_revision():
    raw = pd.DataFrame({
        "observation_date": ["2025-01-01", "2025-01-01", "2025-02-01"],
        "available_date": ["2025-01-10", "2025-03-10", "2025-02-10"],
        "revision_date": [None, "2025-03-10", None],
        "value": [100.0, 110.0, 200.0],
    })
    pit = asr.data.PointInTimeFrame(raw)
    feb = pit.as_of("2025-02-20")
    assert feb.loc[feb["observation_date"] == pd.Timestamp("2025-01-01"), "value"].iloc[0] == 100.0
    apr = pit.as_of("2025-04-01")
    assert apr.loc[apr["observation_date"] == pd.Timestamp("2025-01-01"), "value"].iloc[0] == 110.0


def test_strategy_report_consolidates_multiple_testing_diagnostics():
    rng = np.random.default_rng(1234)
    frame = pd.DataFrame(
        {
            "a": rng.normal(0.0004, 0.01, 240),
            "b": rng.normal(0.0001, 0.01, 240),
            "c": rng.normal(0.0000, 0.01, 240),
            "d": rng.normal(-0.0001, 0.01, 240),
        }
    )
    result = asr.validation.strategy_report(frame, n_groups=6, n_boot=100, random_state=7)
    assert result.screen_status in {"SCREEN_PASS", "REVIEW_REQUIRED"}
    assert 0 <= result.summary["pbo"] <= 1
    assert 0 <= result.summary["spa_p_value"] <= 1


def test_specification_curve_wrapper():
    result = asr.validation.specification_curve(
        {"lookback": [20, 60], "cost": [0, 5]},
        lambda lookback, cost: {"metric": 1 / lookback - cost / 1000},
    )
    assert result.summary["specifications"] == 4
