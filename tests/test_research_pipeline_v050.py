from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def synthetic_research_data(n=600):
    rng = np.random.default_rng(11)
    index = pd.date_range("2020-01-01", periods=n, freq="B")
    yield_changes = rng.normal(0, 0.04, n)
    us10y = 2.0 + np.cumsum(yield_changes)
    regime = pd.Series(yield_changes, index=index).rolling(20).sum().fillna(0.0)
    value_returns = 0.0003 + 0.0015 * (regime > 0.15).astype(float).to_numpy() + rng.normal(0, 0.006, n)
    growth_returns = 0.0003 - 0.0012 * (regime > 0.15).astype(float).to_numpy() + rng.normal(0, 0.006, n)
    value = 100 * np.cumprod(1 + value_returns)
    growth = 100 * np.cumprod(1 + growth_returns)
    return pd.DataFrame({"US10Y": us10y, "VALUE": value, "GROWTH": growth}, index=index)


def test_literature_hypothesis_discovery_and_scope():
    corpus = asr.LiteratureCorpus.from_texts(
        [
            (
                "Rates and styles",
                "We hypothesize that rapid increases in long-term interest rates lead to value outperforming growth equities. "
                "Future research should examine whether the relationship changes across inflation regimes.",
            ),
            (
                "Replication",
                "We test whether higher Treasury yields predict relative value returns and find a positive relationship.",
            ),
        ],
        topic="interest rates value growth",
    )
    registry = corpus.discover_hypotheses()
    assert len(registry) >= 2
    assert "corpus-relative" in registry.scope_note.lower()
    assert registry.to_frame()["source_count"].max() >= 1


def test_end_to_end_research_project(tmp_path: Path):
    data = synthetic_research_data()
    project = asr.research.from_hypothesis(
        "Rapid increases in US 10-year yields predict value outperformance relative to growth.",
        predictor="US10Y",
        target="VALUE minus GROWTH",
        expected_sign="positive",
        mechanism="Higher discount rates reduce the present value of long-duration growth cash flows more strongly.",
    )
    project.attach_data(data, tradable_assets=["VALUE", "GROWTH"])
    feature_plan = asr.FeaturePlan(
        [asr.FeatureSpec("yield_change_20", "US10Y", "diff", params={"periods": 20}, availability_lag=1)]
    )
    project.build_features(feature_plan)
    project.build_signal(
        asr.SignalSpec(
            feature="yield_change_20",
            method="threshold_pair",
            long_asset="VALUE",
            short_asset="GROWTH",
            upper=0.15,
            lower=-0.15,
            signal_lag=1,
        )
    )
    project.construct_portfolio(asr.PortfolioSpec(gross_leverage=1.0, max_abs_weight=0.5))
    result = project.backtest(costs_bps=2.0, execution_delay=1)
    assert np.isfinite(result.metrics["Sharpe"])
    robust = project.robustness(n_boot=50, execution_delays=(1, 2), costs_bps=(0, 5), rebalances=("bar",))
    assert len(robust.implementation_audit.summary) == 4
    decision = project.decide()
    assert decision.status in {
        "REJECT", "RESEARCH-ONLY", "LIMITED-CAPITAL CANDIDATE", "PAPER-TRADING CANDIDATE",
        "REVISE HYPOTHESIS", "COLLECT MORE DATA",
    }
    manifest = project.save_manifest(tmp_path / "manifest.json")
    report = project.report(tmp_path / "report.html")
    assert manifest.exists() and report.exists()
    assert project.fingerprint


def test_paper_trading_and_risk_controls():
    data = synthetic_research_data(80)[["VALUE", "GROWTH"]]
    weights = pd.DataFrame(0.0, index=data.index, columns=data.columns)
    weights.loc[:, "VALUE"] = 0.5
    weights.loc[:, "GROWTH"] = -0.5
    policy = asr.RiskPolicy(max_gross_leverage=1.0, max_position_weight=0.5, max_daily_turnover=2.0)
    result = asr.paper_trade(data, weights, commission_bps=1, slippage_bps=1, policy=policy)
    assert len(result.equity) == len(data)
    assert len(result.orders) > 0
    assert np.isfinite(result.metrics["Total Return"])


def test_autoresearch_one_import():
    data = synthetic_research_data()
    project = asr.autoresearch(
        hypothesis="Rising yields predict value outperformance relative to growth.",
        data=data,
        tradable_assets=["VALUE", "GROWTH"],
        feature_plan=asr.FeaturePlan([
            asr.FeatureSpec("yield_change", "US10Y", "diff", params={"periods": 20}, availability_lag=1)
        ]),
        signal_spec=asr.SignalSpec(
            "yield_change", long_asset="VALUE", short_asset="GROWTH", upper=0.15, lower=-0.15
        ),
        portfolio_spec=asr.PortfolioSpec(max_abs_weight=0.5),
        backtest_spec=asr.BacktestSpec(execution_delay=1),
    )
    assert project.backtest_result is not None
    assert project.robustness_result is not None
    assert project.decision_result is not None


def test_candidate_evidence_status_flows_to_operational_hypothesis():
    corpus = asr.LiteratureCorpus.from_texts([
        ("Paper", "We test whether rising yields predict value returns and find a positive relationship.")
    ])
    candidate = corpus.discover_hypotheses().select(0)
    hypothesis = asr.EconomicHypothesis.from_candidate(candidate)
    assert hypothesis.evidence_status == "tested_in_corpus"


def test_decision_manifest_is_json_ready(tmp_path: Path):
    data = synthetic_research_data()
    project = asr.autoresearch(
        hypothesis="Rising yields predict value outperformance relative to growth.",
        data=data,
        tradable_assets=["VALUE", "GROWTH"],
        feature_plan=asr.FeaturePlan([
            asr.FeatureSpec("yield_change", "US10Y", "diff", params={"periods": 20}, availability_lag=1)
        ]),
        signal_spec=asr.SignalSpec(
            "yield_change", long_asset="VALUE", short_asset="GROWTH", upper=0.15, lower=-0.15
        ),
        portfolio_spec=asr.PortfolioSpec(max_abs_weight=0.5),
        backtest_spec=asr.BacktestSpec(execution_delay=1),
    )
    payload = project.manifest()
    assert isinstance(payload["decision"]["evidence"], dict)
    output = project.save_manifest(tmp_path / "manifest.json")
    assert '"evidence": {' in output.read_text()


def test_risk_policy_rejects_invalid_cash_and_order_cap():
    with pytest.raises(ValueError):
        asr.RiskPolicy(minimum_cash=-1).validate()
    with pytest.raises(ValueError):
        asr.RiskPolicy(max_order_notional=0).validate()
