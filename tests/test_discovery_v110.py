from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import asrquant as asr
from asrquant import discovery
from asrquant.research_ops import weekly_cycle


def synthetic_curve_history(n=300):
    rng = np.random.default_rng(5)
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    level = np.cumsum(rng.normal(0, 0.0002, n))
    # Deliberately higher slope volatility in the second half and sign crossing.
    shocks = np.r_[rng.normal(0, 0.00005, n//2), rng.normal(0, 0.00035, n-n//2)]
    slope = np.cumsum(shocks) - 0.002
    slope[n//2:] += np.linspace(0, 0.006, n-n//2)
    return pd.DataFrame({
        "2Y": .025 + level - slope,
        "5Y": .027 + level - .2*slope,
        "10Y": .029 + level + slope,
        "30Y": .031 + level + 1.3*slope,
    }, index=idx)


def test_market_scan_finds_structural_observations():
    rng = np.random.default_rng(0)
    x = np.r_[rng.normal(0, 1, 100), rng.normal(1.5, 3, 100)]
    y = np.r_[x[:100] + rng.normal(0, .1, 100), -x[100:] + rng.normal(0, .1, 100)]
    obs = discovery.scan_market(pd.DataFrame({"x": x, "y": y}))
    assert len(obs) > 0
    assert any(o.kind in {"mean_shift", "variance_shift", "correlation_break", "rolling_volatility_regime"} for o in obs)


def test_yield_curve_scan_and_weekly_board():
    data = synthetic_curve_history()
    obs = discovery.scan_yield_curve_history(data)
    assert len(obs) > 0
    board = discovery.weekly(data=data, domain="fixed_income", n=8)
    assert len(board) == 8
    assert (board.to_frame()["novelty_status"] == "NOT_ESTABLISHED").any()
    assert len(board.observations) > 0


def test_board_starts_existing_research_project():
    board = discovery.catalog("fixed_income")
    project = board.start(0)
    assert isinstance(project, asr.ResearchProject)
    assert project.hypothesis is not None
    assert project.hypothesis.metadata["candidate_id"] == board.select(0).candidate_id


def test_friday_to_friday_plan():
    board = discovery.catalog("fixed_income")
    plan = board.weekly_plan(0, launch_friday=date(2026, 8, 14))
    assert len(plan) == 8
    assert str(plan.iloc[0]["day"]) == "Friday"
    assert str(plan.iloc[-1]["day"]) == "Friday"
    assert (pd.Timestamp(plan.iloc[-1]["date"]) - pd.Timestamp(plan.iloc[0]["date"])).days == 7


def test_weekly_cycle_publication_pack(tmp_path):
    board = discovery.catalog("fixed_income")
    cycle = weekly_cycle(board, 0, launch_friday="2026-08-14")
    pack = cycle.publication_pack(tmp_path / "weekly")
    expected = [
        "research_brief.md", "RESEARCH_NOTE.md", "REPRODUCIBILITY_CHECKLIST.md",
        "CLAIM_AUDIT.md", "weekly_plan.csv", "cycle_status.csv", "project_manifest.json",
    ]
    for name in expected:
        assert (pack / name).exists()
    text = (pack / "RESEARCH_NOTE.md").read_text()
    assert "Novelty status" in text
    assert "Falsification" in text


def test_model_disagreement_and_robustness_scans():
    rng = np.random.default_rng(3)
    pred = pd.DataFrame({"A": rng.normal(0, 1, 100), "B": rng.normal(0, 2, 100), "C": rng.normal(0, 1.5, 100)})
    obs = discovery.scan_model_disagreement(pred)
    assert any(o.kind == "model_disagreement" for o in obs)
    robust = pd.DataFrame({"spec": [1,2,3,4], "Sharpe": [1.0, .2, -.1, .7]})
    robs = discovery.scan_robustness_grid(robust, "Sharpe")
    assert robs[0].evidence["sign_instability"] is True


def test_research_facade_exposes_discovery_and_cycle():
    board = asr.research.discover(domain="fixed_income", n=5)
    assert len(board) == 5
    cycle = asr.research.weekly_cycle(board, 0, launch_friday="2026-08-14")
    assert cycle.publication_friday.isoformat() == "2026-08-21"
