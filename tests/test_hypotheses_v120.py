import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def predictive_panel(n=520, seed=17):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2020-01-01", periods=n, freq="B")
    x = rng.normal(size=n)
    noise = rng.normal(scale=0.45, size=n)
    y = np.empty(n)
    y[0] = noise[0]
    y[1:] = 0.85 * x[:-1] + noise[1:]
    z = rng.normal(size=n)
    return pd.DataFrame({"x": x, "y": y, "noise": z}, index=index)


def literature_corpus():
    return asr.LiteratureCorpus.from_texts(
        [
            (
                "Forward curve regimes",
                "We hypothesize that forward curve instability predicts subsequent changes in fixed income rate regimes. "
                "Future research should test whether the effect survives alternative curve constructions and monetary policy subsamples.",
            ),
            (
                "Yield curve transitions",
                "We examine whether changes in yield curve slope are associated with later fixed income market transitions. "
                "Our results suggest that the relationship varies across policy regimes.",
            ),
        ],
        topic="fixed income",
    )


def test_from_data_recovers_chronology_safe_predictive_relation():
    data = predictive_panel()
    result = asr.hypotheses.from_data(
        data,
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        fdr_alpha=0.05,
        min_abs_effect=0.05,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    frame = result.to_frame()
    relation = frame[(frame.predictor == "x") & (frame.target == "y")]
    assert len(relation) == 1
    row = relation.iloc[0]
    assert row.discovery_effect > 0.7
    assert row.holdout_effect > 0.7
    assert row.q_value < 0.05
    assert row.data_status == "OUT_OF_SAMPLE_SUPPORTED"
    assert row.novelty_status == "NOVELTY_NOT_ESTABLISHED"
    assert result.metadata["tests_performed"] >= 2
    assert result.metadata["multiple_testing"] == "Benjamini-Hochberg FDR"


def test_data_discovery_keeps_evidence_and_novelty_separate():
    result = asr.hypotheses.from_data(
        predictive_panel(),
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    idea = next(item for item in result if item.predictor == "x" and item.target == "y")
    assert idea.data_status in {"DATA_SUPPORTED", "OUT_OF_SAMPLE_SUPPORTED"}
    assert idea.novelty_status == "NOVELTY_NOT_ESTABLISHED"
    assert idea.evidence["tests_performed"] == result.metadata["tests_performed"]
    assert "q_value" in idea.evidence
    assert "holdout_p_value" in idea.evidence


def test_named_dataset_mapping_is_supported():
    panel = predictive_panel()
    result = asr.hypotheses.from_data(
        {"macro": panel[["x"]], "market": panel[["y", "noise"]]},
        targets="market::y",
        horizons=(1,),
        lags=(0,),
        transforms={"macro::x": "raw", "market::y": "raw", "market::noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    assert any(item.predictor == "macro::x" and item.target == "market::y" for item in result)
    assert result.metadata["source_map"]["macro::x"] == "macro"


def test_hypothesis_search_ranks_close_generated_idea():
    result = asr.hypotheses.from_data(
        predictive_panel(),
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    matches = result.search("does x contain information about future y", top_k=3)
    assert len(matches) >= 1
    assert matches.iloc[0].hypothesis_id
    assert matches.iloc[0].similarity > 0


def test_literature_discovery_and_search_preserve_source_provenance():
    corpus = literature_corpus()
    result = asr.hypotheses.from_literature(corpus, topic="fixed income")
    assert len(result) >= 1
    assert all(item.source == "literature" for item in result)
    assert all(item.data_status == "LITERATURE_DERIVED" for item in result)
    search = asr.hypotheses.search(
        "forward curve instability fixed income regimes",
        hypotheses=result,
        papers=corpus,
        topic="fixed income",
    )
    assert search.summary["hypothesis_matches"] >= 1
    assert search.summary["source_excerpts"] >= 1
    assert {"paper_id", "page", "text"}.issubset(search.excerpts.columns)


def test_novelty_audit_is_conservative_and_finds_prior_art():
    corpus = literature_corpus()
    idea = asr.hypotheses.HypothesisIdea(
        hypothesis_id="H-MANUAL",
        statement="Forward curve instability predicts subsequent changes in fixed income rate regimes.",
        research_question="Does forward curve instability precede rate regime changes?",
        domain="fixed_income",
        source="manual",
        data_status="NOT_TESTED",
    )
    audit = asr.hypotheses.audit(idea, corpus=corpus, topic="fixed income")
    assert audit.novelty_status in {"PRIOR_ART_FOUND", "CORPUS_RELATED", "POTENTIAL_GAP"}
    assert len(audit.closest_matches) >= 1
    assert audit.summary["best_similarity"] > 0.45
    assert "corpus-relative" in " ".join(audit.warnings).lower()


def test_audit_without_corpus_never_claims_novelty():
    audit = asr.hypotheses.audit("A completely new sounding quantitative hypothesis")
    assert audit.novelty_status == "NOVELTY_NOT_ESTABLISHED"
    assert audit.closest_matches.empty


def test_combined_discovery_audits_data_candidates_against_literature():
    combined = asr.hypotheses.discover(
        data=predictive_panel(),
        papers=literature_corpus(),
        domain="fixed_income",
        max_candidates=20,
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    assert len(combined) >= 1
    assert "data" in combined.metadata["component_sources"]
    assert "literature" in combined.metadata["component_sources"]
    assert combined.metadata["novelty_rule"].startswith("Never established automatically")


def test_data_hypothesis_starts_existing_research_project():
    result = asr.hypotheses.from_data(
        predictive_panel(),
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    idea = next(item for item in result if item.predictor == "x" and item.target == "y")
    project = idea.start()
    assert isinstance(project, asr.ResearchProject)
    assert project.hypothesis.predictor == "x"
    assert project.hypothesis.target == "y"
    assert project.hypothesis.metadata["hypothesis_source"] == "data"


def test_from_data_validation_is_fail_fast():
    with pytest.raises(ValueError):
        asr.hypotheses.from_data(pd.DataFrame({"x": [1, 2, 3]}), min_observations=20)
    with pytest.raises(ValueError):
        asr.hypotheses.from_data(predictive_panel(100), holdout_fraction=0.9)
    with pytest.raises(asr.contracts.InputValidationError):
        asr.hypotheses.from_data(predictive_panel(), targets="missing")


def test_model_disagreement_and_robustness_sources_are_first_class():
    idx = pd.date_range("2024-01-02", periods=120, freq="B")
    predictions = pd.DataFrame(
        {
            "model_a": np.linspace(0.0, 1.0, len(idx)),
            "model_b": np.linspace(0.2, 1.4, len(idx)),
        },
        index=idx,
    )
    model_ideas = asr.hypotheses.from_model_disagreement(predictions)
    assert len(model_ideas) >= 1
    assert all(item.source == "model_disagreement" for item in model_ideas)

    robustness = pd.DataFrame({"sharpe": [1.2, 0.9, 0.1, -0.3, 0.8]})
    robust_ideas = asr.hypotheses.from_robustness(robustness, metric="sharpe")
    assert len(robust_ideas) >= 1
    assert all(item.source == "robustness" for item in robust_ideas)


def test_structural_scan_can_contribute_exploratory_candidates():
    panel = predictive_panel(260)
    result = asr.hypotheses.from_data(
        panel,
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=80,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=True,
    )
    assert any(item.source == "data_structural_scan" for item in result)


def test_cointegration_screen_generates_auditable_candidate():
    rng = np.random.default_rng(73)
    n = 420
    idx = pd.date_range("2018-01-02", periods=n, freq="B")
    common = np.cumsum(rng.normal(scale=0.6, size=n)) + 100.0
    left = common + rng.normal(scale=0.08, size=n)
    right = 1.7 * common + rng.normal(scale=0.08, size=n)
    result = asr.hypotheses.from_data(
        pd.DataFrame({"left": left, "right": right}, index=idx),
        targets="right",
        horizons=(1,),
        lags=(0,),
        transforms={"left": "pct_change", "right": "pct_change"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=True,
        include_structural_scan=False,
        min_abs_effect=0.0,
    )
    coint = [item for item in result if item.metadata.get("test_type") == "cointegration"]
    assert coint
    assert coint[0].evidence["tests_performed"] == result.metadata["tests_performed"]
    assert coint[0].novelty_status == "NOVELTY_NOT_ESTABLISHED"


def test_collection_rank_and_serialization_contract():
    result = asr.hypotheses.from_data(
        predictive_panel(),
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=120,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    ranked = result.rank(by="q_value")
    frame = ranked.to_frame()
    assert len(frame) == len(ranked)
    payload = ranked.to_dict()
    assert payload["result_type"] == "hypothesis_collection"
    assert payload["summary"]["tests_performed"] == result.metadata["tests_performed"]
    assert set(frame.data_status).issubset(asr.hypotheses.DATA_STATUSES)


def test_combined_discover_supports_all_evidence_channels():
    panel = predictive_panel(260)
    idx = panel.index
    predictions = pd.DataFrame(
        {"m1": panel["y"].rolling(3).mean(), "m2": panel["y"].rolling(8).mean()},
        index=idx,
    ).bfill()
    robustness = pd.DataFrame({"metric": [0.8, 0.5, -0.1, 0.7]})
    result = asr.hypotheses.discover(
        data=panel,
        papers=literature_corpus(),
        predictions=predictions,
        robustness_results=robustness,
        robustness_metric="metric",
        domain="quantitative_finance",
        max_candidates=30,
        targets="y",
        horizons=(1,),
        lags=(0,),
        transforms={"x": "raw", "y": "raw", "noise": "raw"},
        min_observations=80,
        include_regime_tests=False,
        include_cointegration=False,
        include_structural_scan=False,
    )
    sources = set(result.metadata["component_sources"])
    assert {"data", "literature", "model_disagreement", "robustness"}.issubset(sources)
    assert result.metadata["tests_performed"] > 0
