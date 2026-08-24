import numpy as np
import pandas as pd

import asrquant as asr


def test_literature_hypothesis_discovery_is_preserved_in_v120():
    corpus = asr.LiteratureCorpus.from_texts(
        [
            (
                "Rates and Risk",
                "We hypothesize that yield curve inversion predicts a change in future risk premia. "
                "Future research should test whether the relationship survives different monetary regimes.",
            ),
            (
                "Curve Regimes",
                "We examine whether changes in the slope of the yield curve affect subsequent market returns. "
                "Our results suggest that the relationship varies across regimes.",
            ),
        ],
        topic="yield curve rates",
    )
    registry = corpus.discover_hypotheses(topic="yield curve rates")
    assert len(registry) >= 1
    assert registry.corpus_fingerprint == corpus.fingerprint
    assert registry.select(0).evidence


def test_hypothesis_registry_hands_off_to_research_discovery_and_project():
    corpus = asr.LiteratureCorpus.from_texts(
        [
            (
                "Research Gap",
                "Future research remains unclear on whether forward-curve instability predicts derivative hedging error. "
                "We hypothesize that greater forward-curve instability increases subsequent hedge error.",
            )
        ],
        topic="fixed income",
    )
    registry = corpus.discover_hypotheses(topic="fixed income")
    board = asr.discovery.from_literature(registry, topic="fixed_income")
    assert len(board) >= 1
    project = board.start(0)
    assert project.hypothesis.statement
    assert project.hypothesis.metadata["candidate_id"] == board.select(0).candidate_id


def test_weekly_discovery_still_combines_market_and_literature_evidence():
    rng = np.random.default_rng(12)
    idx = pd.date_range("2023-01-02", periods=180, freq="B")
    levels = np.cumsum(rng.normal(0, 0.0002, len(idx)))
    slopes = np.cumsum(rng.normal(0, 0.00015, len(idx)))
    curves = pd.DataFrame(
        {
            "2Y": 0.02 + levels - slopes,
            "5Y": 0.025 + levels,
            "10Y": 0.03 + levels + slopes,
            "30Y": 0.032 + levels + 1.4 * slopes,
        },
        index=idx,
    )
    papers = [
        (
            "Curve Instability",
            "Future research should test whether yield curve factor instability affects hedging performance."
        )
    ]
    board = asr.discovery.weekly(
        data=curves,
        papers=papers,
        domain="fixed_income",
        n=6,
        include_catalog=False,
    )
    assert len(board) >= 1
    assert any(candidate.hypothesis for candidate in board)
    assert board.domain == "fixed_income"
