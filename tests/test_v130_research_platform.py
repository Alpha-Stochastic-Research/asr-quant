from __future__ import annotations

import json
import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def test_experiment_manifest_is_reproducible_for_same_inputs(tmp_path):
    idx = pd.date_range("2025-01-01", periods=4)
    data = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0]}, index=idx)
    exp = asr.research.Experiment("test", config={"window": 20}, data={"market": data}, seed=42, code_hash="abc")
    manifest = exp.manifest()
    assert manifest["config_hash"]
    assert manifest["data_hashes"]["market"]
    path = exp.save(tmp_path / "manifest.json")
    loaded = json.loads(path.read_text())
    assert loaded["fingerprint"] == exp.fingerprint


def test_experiment_registry_compare(tmp_path):
    reg = asr.research.ExperimentRegistry(tmp_path / "runs.jsonl")
    reg.add(asr.research.Experiment("x", config={"a": 1}))
    reg.add(asr.research.Experiment("x", config={"a": 2}))
    assert len(reg.compare("x")) == 2


def test_research_report_exports(tmp_path):
    result = asr.calibration.CalibrationProblem(lambda x, p: p["a"] * x, np.arange(5.0), np.arange(5.0) * 2, {"a": 1}).solve()
    report = asr.research.ResearchReport("Test").add(result, "calibration")
    for suffix in ["html", "json"]:
        path = report.export(tmp_path / f"report.{suffix}")
        assert path.exists() and path.stat().st_size > 20
    assert bool(report.audit().loc["calibration", "has_summary"])


def test_adapter_registry_roundtrip():
    asr.register.clear()
    adapter = object()
    assert asr.register.pricer("internal", adapter) is adapter
    assert asr.register.get("pricer", "internal") is adapter
    assert "internal" in asr.register.available("pricer")
    asr.register.clear()


def test_diagnostics_flags_portfolio_concentration():
    result = asr.contracts.PortfolioOptimizationResult(
        weights=pd.Series({"A": 0.9, "B": 0.1}),
        method="test",
        expected_return=0.1,
        volatility=0.2,
        sharpe=0.5,
    )
    report = asr.diagnostics.explain(result)
    assert report.status == "WARNING"
    assert "PORTFOLIO_CONCENTRATION" in set(report.findings["code"])


def test_model_comparison_ranks_better_predictions():
    y = pd.Series(np.linspace(0, 1, 100))
    result = asr.model_selection.compare_predictions(
        y,
        {
            "good": y + 0.01,
            "bad": y + np.sin(np.arange(100)) * 0.5,
        },
    )
    assert result.best_model == "good"


def test_factor_attribution_recovers_exposure():
    rng = np.random.default_rng(10)
    f = pd.DataFrame({"MKT": rng.normal(0, 0.01, 500), "RATE": rng.normal(0, 0.005, 500)})
    y = 0.0001 + 1.2 * f["MKT"] - 0.5 * f["RATE"] + rng.normal(0, 0.001, 500)
    result = asr.performance.factor_attribution(y, f)
    assert result.exposures["MKT"] == pytest.approx(1.2, abs=0.05)
    assert result.exposures["RATE"] == pytest.approx(-0.5, abs=0.05)


def test_regime_volatility_labels():
    rng = np.random.default_rng(11)
    r = pd.Series(np.r_[rng.normal(0, 0.005, 150), rng.normal(0, 0.03, 150)])
    result = asr.regimes.volatility_regimes(r, window=30)
    assert set(result.labels.unique()).issubset({"low", "medium", "high"})
    assert len(result.labels) > 0


def test_alpha_capacity_curve_decreases_net_alpha_with_aum():
    idx = pd.date_range("2025-01-01", periods=40)
    w = pd.DataFrame({"A": np.where(np.arange(40) % 2 == 0, 1.0, 0.0), "B": np.where(np.arange(40) % 2 == 0, 0.0, 1.0)}, index=idx)
    result = asr.alpha.capacity(
        w,
        pd.Series({"A": 50_000_000, "B": 50_000_000}),
        pd.Series({"A": 0.02, "B": 0.02}),
        expected_gross_alpha=0.20,
        aum_grid=[1e5, 1e6, 1e7, 1e8],
    )
    assert result.curve["net_alpha"].iloc[-1] < result.curve["net_alpha"].iloc[0]


def test_random_seed_reproducible():
    asr.random.seed(123)
    a = asr.random.generator().normal(size=5)
    asr.random.seed(123)
    b = asr.random.generator().normal(size=5)
    np.testing.assert_allclose(a, b)


def test_experiment_exposes_native_result_contract():
    exp = asr.research.Experiment("native-contract", config={"x": 1}, seed=7)
    assert exp.summary["name"] == "native-contract"
    assert exp.to_dict()["fingerprint"] == exp.fingerprint


def test_cli_info_and_validate(tmp_path, capsys):
    from asrquant.cli import main

    assert main(["info"]) == 0
    info = capsys.readouterr().out
    assert '"version": "1.3.0rc1"' in info

    path = tmp_path / "data.csv"
    pd.DataFrame(
        {"Date": pd.date_range("2026-01-01", periods=5), "x": np.arange(5.0)}
    ).to_csv(path, index=False)
    assert main(["validate", str(path), "--date-column", "Date"]) == 0
    output = capsys.readouterr().out
    assert "Issues: none" in output


def test_research_graph_lineage_and_stale_propagation():
    graph = asr.research.ResearchGraph()
    graph.add("data", {"hash": "abc"})
    graph.add("signal", {"window": 20}, depends_on=["data"])
    graph.add("backtest", {"sharpe": 1.1}, depends_on=["signal"])
    graph.add("report", {"status": "draft"}, depends_on=["backtest"])
    assert graph.dependencies("report", transitive=True) == ("data", "signal", "backtest")
    assert graph.stale_artifacts("data") == ("signal", "backtest", "report")
    assert list(graph.lineage("report").index) == ["data", "signal", "backtest", "report"]


def test_covariance_estimators_and_comparison():
    rng = np.random.default_rng(100)
    returns = pd.DataFrame(rng.normal(size=(300, 4)) * [0.01, 0.012, 0.008, 0.015], columns=list("ABCD"))
    for estimator in [asr.covariance.sample, asr.covariance.ewma, asr.covariance.ledoit_wolf, asr.covariance.factor]:
        cov = estimator(returns)
        assert cov.shape == (4, 4)
        assert np.linalg.eigvalsh(cov.to_numpy()).min() >= -1e-10
    comparison = asr.covariance.compare(returns, estimators=["sample", "ledoit_wolf", "factor"])
    assert len(comparison.to_frame()) == 3
    assert comparison.summary["best_oos_variance"] in {"sample", "ledoit_wolf", "factor"}
    assert asr.risk.covariance is asr.covariance
