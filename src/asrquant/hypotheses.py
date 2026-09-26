"""Hypothesis discovery, search and audit for ASRQuant 1.2.0.

This module turns data, literature, model disagreement and robustness evidence
into *research candidates*.  It is intentionally conservative: statistical
screening may suggest a useful hypothesis, but it never establishes scientific
novelty or causality automatically.

The public entry points are::

    asr.hypotheses.from_data(...)
    asr.hypotheses.from_literature(...)
    asr.hypotheses.from_model_disagreement(...)
    asr.hypotheses.from_robustness(...)
    asr.hypotheses.discover(...)
    asr.hypotheses.search(...)
    asr.hypotheses.audit(...)

Every data-driven screen records the number of tests performed, discovery and
holdout samples, raw p-values and Benjamini-Hochberg q-values when applicable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import discovery as _discovery
from .literature import HypothesisRegistry, LiteratureCorpus
from .workflow import ResearchProject
from .contracts import HypothesisDiscoveryError, InputValidationError


DATA_STATUSES = {
    "NOT_TESTED",
    "EXPLORATORY",
    "DATA_SUPPORTED",
    "OUT_OF_SAMPLE_SUPPORTED",
    "INCONCLUSIVE",
    "FALSIFIED",
    "LITERATURE_DERIVED",
}

NOVELTY_STATUSES = {
    "NOVELTY_NOT_ESTABLISHED",
    "CORPUS_RELATED",
    "POTENTIAL_GAP",
    "PRIOR_ART_FOUND",
    "CONTRADICTORY_LITERATURE",
}

_FIXED_INCOME_DOMAINS = {
    "fixed_income",
    "interest_rates",
    "rates",
    "fixed_income_derivatives",
    "interest_rate_derivatives",
}


def _normalise_domain(domain: str) -> str:
    return str(domain).strip().lower().replace("-", "_").replace(" ", "_")


def _identifier(prefix: str, *parts: Any) -> str:
    payload = "|".join(map(str, parts)).encode("utf-8", errors="ignore")
    return f"{prefix}-{sha256(payload).hexdigest()[:10]}"


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
        "is", "are", "be", "by", "as", "from", "at", "this", "that", "does",
        "do", "when", "how", "what", "whether", "than", "into", "under",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) > 2 and token not in stop
    }


def _text_similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    jaccard = len(a & b) / len(a | b) if a and b else 0.0
    sequence = SequenceMatcher(None, str(left).lower(), str(right).lower()).ratio()
    return float(0.72 * jaccard + 0.28 * sequence)


def _bh_adjust(p_values: Sequence[float]) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    if len(p) == 0:
        return p
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must be finite and lie in [0, 1]")
    order = np.argsort(p)
    ranked = p[order]
    adjusted_ranked = np.minimum.accumulate(
        (ranked * len(p) / np.arange(1, len(p) + 1))[::-1]
    )[::-1]
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = np.clip(adjusted_ranked, 0.0, 1.0)
    return adjusted


def _safe_corr(x: pd.Series, y: pd.Series) -> tuple[float, float, int]:
    pair = pd.concat([pd.Series(x, dtype=float), pd.Series(y, dtype=float)], axis=1).dropna()
    if len(pair) < 4 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan, np.nan, len(pair)
    result = stats.pearsonr(pair.iloc[:, 0].to_numpy(), pair.iloc[:, 1].to_numpy())
    return float(result.statistic), float(result.pvalue), int(len(pair))


def _coerce_panel(
    data: pd.DataFrame | pd.Series | Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Coerce one panel or a mapping of named datasets to one numeric frame."""
    source_map: dict[str, str] = {}
    if isinstance(data, pd.Series):
        frame = data.to_frame(data.name or "value")
        source_map[str(frame.columns[0])] = "data"
    elif isinstance(data, pd.DataFrame):
        frame = data.copy()
        source_map = {str(column): "data" for column in frame.columns}
    elif isinstance(data, Mapping):
        if data and all(isinstance(value, (pd.Series, pd.DataFrame)) for value in data.values()):
            pieces: list[pd.DataFrame] = []
            for dataset_name, value in data.items():
                part = pd.DataFrame(value).copy()
                if isinstance(value, pd.Series):
                    part.columns = [value.name or "value"]
                renamed = {column: f"{dataset_name}::{column}" for column in part.columns}
                part = part.rename(columns=renamed)
                for column in part.columns:
                    source_map[str(column)] = str(dataset_name)
                pieces.append(part)
            frame = pd.concat(pieces, axis=1, join="outer")
        else:
            frame = pd.DataFrame(data)
            source_map = {str(column): "data" for column in frame.columns}
    else:
        raise InputValidationError("data must be a Series, DataFrame, column mapping, or mapping of named datasets")

    if frame.empty or frame.shape[1] == 0:
        raise InputValidationError("data is empty")
    if isinstance(frame.index, pd.DatetimeIndex):
        frame = frame.sort_index()
    elif not isinstance(frame.index, pd.RangeIndex):
        try:
            converted = pd.to_datetime(frame.index)
            if not converted.isna().any():
                frame.index = converted
                frame = frame.sort_index()
        except Exception:
            pass
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if frame.shape[1] == 0:
        raise InputValidationError("data contains no numeric columns")
    return frame, source_map


def _infer_transform(series: pd.Series, domain: str) -> str:
    clean = pd.Series(series, dtype=float).dropna()
    if len(clean) < 3:
        return "raw"
    if _normalise_domain(domain) in _FIXED_INCOME_DOMAINS:
        return "diff"
    q95 = float(clean.abs().quantile(0.95))
    median = float(clean.abs().median())
    has_negative = bool((clean < 0).any())
    # Already return/change-like series should not be differenced again.
    if has_negative and q95 <= 0.75:
        return "raw"
    # Small-valued rates/spreads are better treated in changes.
    if median <= 1.5 and q95 <= 5.0:
        return "diff"
    # Positive price/index/macro levels are naturally expressed in proportional changes.
    if (clean > 0).all():
        return "pct_change"
    return "diff"


def _transform_series(series: pd.Series, method: str) -> pd.Series:
    x = pd.Series(series, dtype=float)
    key = str(method).lower().replace("-", "_").replace(" ", "_")
    if key == "raw":
        out = x
    elif key in {"diff", "difference"}:
        out = x.diff()
    elif key in {"pct_change", "return", "returns", "simple_return"}:
        out = x.pct_change(fill_method=None)
    elif key in {"log_return", "log_returns"}:
        out = np.log(x.where(x > 0)).diff()
    else:
        raise ValueError("transform must be raw, diff, pct_change, or log_return")
    return out.replace([np.inf, -np.inf], np.nan)


def _forward_aggregate(series: pd.Series, horizon: int, transform: str) -> pd.Series:
    if horizon <= 0:
        raise ValueError("horizons must be positive")
    x = pd.Series(series, dtype=float)
    key = str(transform).lower().replace("-", "_")
    if horizon == 1:
        return x.shift(-1)
    if key in {"pct_change", "return", "returns", "simple_return"}:
        future = (1.0 + x).rolling(horizon).apply(np.prod, raw=True) - 1.0
    elif key in {"log_return", "log_returns", "diff", "difference"}:
        future = x.rolling(horizon).sum()
    else:
        # For raw signals, the horizon target is the future level rather than a sum.
        return x.shift(-horizon)
    return future.shift(-(horizon - 1))


def _chronological_split(
    x: pd.Series,
    y: pd.Series,
    holdout_fraction: float,
    min_observations: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    if len(pair) < min_observations:
        return pair.iloc[0:0], pair.iloc[0:0]
    cut = int(np.floor(len(pair) * (1.0 - holdout_fraction)))
    cut = max(4, min(cut, len(pair) - 4))
    return pair.iloc[:cut], pair.iloc[cut:]


def _status(
    *,
    q_value: float,
    holdout_p: float,
    discovery_effect: float,
    holdout_effect: float,
    alpha: float,
) -> str:
    if not np.isfinite(q_value):
        return "EXPLORATORY"
    discovery_sign = np.sign(discovery_effect) if np.isfinite(discovery_effect) else 0.0
    holdout_sign = np.sign(holdout_effect) if np.isfinite(holdout_effect) else 0.0
    same_sign = discovery_sign != 0 and discovery_sign == holdout_sign
    if q_value <= alpha and np.isfinite(holdout_p) and holdout_p <= alpha and same_sign:
        return "OUT_OF_SAMPLE_SUPPORTED"
    if q_value <= alpha and np.isfinite(holdout_p) and holdout_p <= alpha and not same_sign:
        return "FALSIFIED"
    if q_value <= alpha and same_sign:
        return "DATA_SUPPORTED"
    if q_value <= alpha:
        return "INCONCLUSIVE"
    return "EXPLORATORY"


@dataclass
class HypothesisIdea:
    """One falsifiable research hypothesis with separate evidence and novelty states."""

    hypothesis_id: str
    statement: str
    research_question: str
    domain: str = "quantitative_finance"
    source: str = "data"
    data_status: str = "EXPLORATORY"
    novelty_status: str = "NOVELTY_NOT_ESTABLISHED"
    evidence_status: str = "PROPOSED"
    priority_score: float = 0.5
    predictor: str | None = None
    target: str | None = None
    expected_sign: str | None = None
    horizon: int | str | None = None
    mechanism: str = ""
    null_hypothesis: str = "No stable out-of-sample relationship under the pre-specified test."
    falsification_rule: str = "Downgrade or reject the hypothesis if the effect fails chronology-safe holdout and robustness checks."
    methods: tuple[str, ...] = ()
    data_requirements: tuple[str, ...] = ()
    alternative_explanations: tuple[str, ...] = ()
    source_observations: tuple[str, ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)
    references: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.data_status not in DATA_STATUSES:
            raise InputValidationError(f"unknown data_status {self.data_status!r}")
        if self.novelty_status not in NOVELTY_STATUSES:
            raise InputValidationError(f"unknown novelty_status {self.novelty_status!r}")
        self.priority_score = float(np.clip(self.priority_score, 0.0, 1.0))

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "hypothesis_id": self.hypothesis_id,
                "domain": self.domain,
                "source": self.source,
                "data_status": self.data_status,
                "novelty_status": self.novelty_status,
                "evidence_status": self.evidence_status,
                "priority_score": self.priority_score,
                "predictor": self.predictor,
                "target": self.target,
                "expected_sign": self.expected_sign,
                "horizon": self.horizon,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_frame(self) -> pd.DataFrame:
        return self.summary.rename("value").to_frame()

    def start(self, *, name: str | None = None) -> ResearchProject:
        """Hand this hypothesis to ASRQuant's existing end-to-end ResearchProject."""
        return ResearchProject.from_hypothesis(
            self.statement,
            name=name or f"ASRQuant Research — {self.hypothesis_id}",
            topic=self.domain,
            predictor=self.predictor,
            target=self.target,
            expected_sign=self.expected_sign,
            horizon=self.horizon,
            novelty_status=self.novelty_status.lower(),
            evidence_status=self.data_status.lower(),
            mechanism=self.mechanism,
            invalidation_criteria=[self.falsification_rule],
            metadata={
                "hypothesis_source": self.source,
                "hypothesis_priority": self.priority_score,
                "research_question": self.research_question,
                "methods": list(self.methods),
                "data_requirements": list(self.data_requirements),
                "alternative_explanations": list(self.alternative_explanations),
                "source_observations": list(self.source_observations),
                "evidence": self.evidence,
                "references": self.references,
                **self.metadata,
            },
        )


@dataclass
class HypothesisAuditResult:
    """Prior-art/evidence audit that never auto-asserts global novelty."""

    hypothesis_id: str
    novelty_status: str
    data_status: str
    closest_matches: pd.DataFrame
    recommendation: str
    warnings: tuple[str, ...] = ()
    corpus_fingerprint: str | None = None

    @property
    def summary(self) -> pd.Series:
        best_similarity = (
            float(self.closest_matches["similarity"].max())
            if len(self.closest_matches) and "similarity" in self.closest_matches
            else np.nan
        )
        return pd.Series(
            {
                "hypothesis_id": self.hypothesis_id,
                "novelty_status": self.novelty_status,
                "data_status": self.data_status,
                "matches": int(len(self.closest_matches)),
                "best_similarity": best_similarity,
                "recommendation": self.recommendation,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.closest_matches.copy()

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": "hypothesis_audit",
            "summary": self.summary.to_dict(),
            "matches": self.closest_matches.to_dict(orient="records"),
            "warnings": list(self.warnings),
            "corpus_fingerprint": self.corpus_fingerprint,
        }


@dataclass
class HypothesisSearchResult:
    """Search matches across generated hypotheses and/or supplied literature."""

    query: str
    hypotheses: pd.DataFrame = field(default_factory=pd.DataFrame)
    excerpts: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "query": self.query,
                "hypothesis_matches": int(len(self.hypotheses)),
                "source_excerpts": int(len(self.excerpts)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.hypotheses.copy()

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": "hypothesis_search",
            "summary": self.summary.to_dict(),
            "hypotheses": self.hypotheses.to_dict(orient="records"),
            "excerpts": self.excerpts.to_dict(orient="records"),
        }


@dataclass
class HypothesisCollection:
    """Ranked, searchable hypothesis set with screening provenance."""

    hypotheses: list[HypothesisIdea]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.hypotheses)

    def __iter__(self):
        return iter(self.hypotheses)

    def __getitem__(self, item: int) -> HypothesisIdea:
        return self.hypotheses[item]

    @property
    def summary(self) -> pd.Series:
        counts = pd.Series([h.data_status for h in self.hypotheses]).value_counts()
        return pd.Series(
            {
                "hypotheses": len(self.hypotheses),
                "tests_performed": int(self.metadata.get("tests_performed", 0)),
                "multiple_testing": self.metadata.get("multiple_testing", "not_applicable"),
                "out_of_sample_supported": int(counts.get("OUT_OF_SAMPLE_SUPPORTED", 0)),
                "data_supported": int(counts.get("DATA_SUPPORTED", 0)),
                "exploratory": int(counts.get("EXPLORATORY", 0)),
                "falsified": int(counts.get("FALSIFIED", 0)),
            }
        )

    def select(self, identifier: str | int) -> HypothesisIdea:
        if isinstance(identifier, int):
            return self.hypotheses[identifier]
        for item in self.hypotheses:
            if item.hypothesis_id == identifier:
                return item
        raise KeyError(f"unknown hypothesis {identifier!r}")

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for item in self.hypotheses:
            row = {
                "hypothesis_id": item.hypothesis_id,
                "statement": item.statement,
                "research_question": item.research_question,
                "domain": item.domain,
                "source": item.source,
                "data_status": item.data_status,
                "novelty_status": item.novelty_status,
                "evidence_status": item.evidence_status,
                "priority_score": item.priority_score,
                "predictor": item.predictor,
                "target": item.target,
                "expected_sign": item.expected_sign,
                "horizon": item.horizon,
                "q_value": item.evidence.get("q_value", np.nan),
                "holdout_p_value": item.evidence.get("holdout_p_value", np.nan),
                "discovery_effect": item.evidence.get("discovery_effect", np.nan),
                "holdout_effect": item.evidence.get("holdout_effect", np.nan),
            }
            rows.append(row)
        return pd.DataFrame(rows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": "hypothesis_collection",
            "summary": self.summary.to_dict(),
            "metadata": dict(self.metadata),
            "hypotheses": [item.to_dict() for item in self.hypotheses],
        }

    def rank(self, *, by: str = "priority_score", ascending: bool = False) -> "HypothesisCollection":
        key = str(by)
        if key == "priority_score":
            ranked = sorted(self.hypotheses, key=lambda item: item.priority_score, reverse=not ascending)
        elif key in {"q_value", "holdout_p_value"}:
            ranked = sorted(
                self.hypotheses,
                key=lambda item: float(item.evidence.get(key, np.inf)),
                reverse=ascending,
            )
        else:
            raise InputValidationError("by must be priority_score, q_value, or holdout_p_value")
        return HypothesisCollection(ranked, dict(self.metadata))

    def search(self, query: str, *, top_k: int = 10, min_similarity: float = 0.0) -> pd.DataFrame:
        if not str(query).strip():
            raise InputValidationError("query must not be empty")
        rows = []
        for item in self.hypotheses:
            score = _text_similarity(query, f"{item.research_question} {item.statement}")
            if score >= min_similarity:
                rows.append(
                    {
                        "hypothesis_id": item.hypothesis_id,
                        "similarity": score,
                        "statement": item.statement,
                        "data_status": item.data_status,
                        "novelty_status": item.novelty_status,
                        "priority_score": item.priority_score,
                    }
                )
        if not rows:
            return pd.DataFrame(
                columns=["hypothesis_id", "similarity", "statement", "data_status", "novelty_status", "priority_score"]
            )
        return pd.DataFrame(rows).sort_values(["similarity", "priority_score"], ascending=False).head(top_k).reset_index(drop=True)

    def audit(
        self,
        identifier: str | int,
        *,
        corpus: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any] | None = None,
        topic: str | None = None,
        top_k: int = 10,
    ) -> HypothesisAuditResult:
        return audit(self.select(identifier), corpus=corpus, topic=topic, top_k=top_k)

    def start(self, identifier: str | int, *, name: str | None = None) -> ResearchProject:
        return self.select(identifier).start(name=name)


def _priority(
    *,
    data_status: str,
    effect: float | None,
    q_value: float | None,
    holdout_effect: float | None,
) -> float:
    score = 0.35
    score += {
        "OUT_OF_SAMPLE_SUPPORTED": 0.36,
        "DATA_SUPPORTED": 0.24,
        "INCONCLUSIVE": 0.08,
        "EXPLORATORY": 0.04,
        "FALSIFIED": -0.22,
        "NOT_TESTED": 0.0,
        "LITERATURE_DERIVED": 0.12,
    }.get(data_status, 0.0)
    if effect is not None and np.isfinite(effect):
        score += min(abs(float(effect)), 1.0) * 0.14
    if q_value is not None and np.isfinite(q_value):
        score += max(0.0, 0.08 * (1.0 - min(float(q_value), 1.0)))
    if effect is not None and holdout_effect is not None and np.isfinite(effect) and np.isfinite(holdout_effect):
        if np.sign(effect) == np.sign(holdout_effect) and np.sign(effect) != 0:
            score += 0.04
    return float(np.clip(score, 0.0, 1.0))


def _correlation_tests(
    transformed: pd.DataFrame,
    transforms: Mapping[str, str],
    *,
    targets: Sequence[str],
    horizons: Sequence[int],
    lags: Sequence[int],
    holdout_fraction: float,
    min_observations: int,
    max_tests: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in targets:
        if target not in transformed:
            raise KeyError(f"target {target!r} not found in data")
        for predictor in transformed.columns:
            if predictor == target:
                continue
            for horizon in horizons:
                y = _forward_aggregate(transformed[target], int(horizon), transforms[target])
                for lag in lags:
                    if len(rows) >= max_tests:
                        return rows
                    x = transformed[predictor].shift(int(lag))
                    discovery, holdout = _chronological_split(x, y, holdout_fraction, min_observations)
                    if discovery.empty:
                        continue
                    effect, p_value, n_discovery = _safe_corr(discovery.x, discovery.y)
                    h_effect, h_p, n_holdout = _safe_corr(holdout.x, holdout.y)
                    if not np.isfinite(effect) or not np.isfinite(p_value):
                        continue
                    rows.append(
                        {
                            "test_type": "lagged_correlation",
                            "predictor": str(predictor),
                            "target": str(target),
                            "horizon": int(horizon),
                            "lag": int(lag),
                            "discovery_effect": effect,
                            "p_value": p_value,
                            "n_discovery": n_discovery,
                            "holdout_effect": h_effect,
                            "holdout_p_value": h_p,
                            "n_holdout": n_holdout,
                        }
                    )
    return rows


def _regime_tests(
    transformed: pd.DataFrame,
    transforms: Mapping[str, str],
    *,
    targets: Sequence[str],
    horizons: Sequence[int],
    holdout_fraction: float,
    min_observations: int,
    max_tests: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in targets:
        for predictor in transformed.columns:
            if predictor == target:
                continue
            for horizon in horizons:
                if len(rows) >= max_tests:
                    return rows
                y = _forward_aggregate(transformed[target], int(horizon), transforms[target])
                pair = pd.concat([transformed[predictor].rename("x"), y.rename("y")], axis=1).dropna()
                if len(pair) < min_observations:
                    continue
                cut = int(np.floor(len(pair) * (1 - holdout_fraction)))
                cut = max(8, min(cut, len(pair) - 8))
                discovery = pair.iloc[:cut]
                holdout = pair.iloc[cut:]

                threshold = float(discovery.x.median())
                low = discovery.loc[discovery.x <= threshold, "y"]
                high = discovery.loc[discovery.x > threshold, "y"]
                if min(len(low), len(high)) < 4:
                    continue
                result = stats.ttest_ind(high, low, equal_var=False, nan_policy="omit")
                pooled = float(np.sqrt((high.var(ddof=1) + low.var(ddof=1)) / 2.0))
                effect = float((high.mean() - low.mean()) / pooled) if pooled > 1e-15 else 0.0

                h_low = holdout.loc[holdout.x <= threshold, "y"]
                h_high = holdout.loc[holdout.x > threshold, "y"]
                if min(len(h_low), len(h_high)) >= 4:
                    h_result = stats.ttest_ind(h_high, h_low, equal_var=False, nan_policy="omit")
                    h_p = float(h_result.pvalue)
                    h_pooled = float(np.sqrt((h_high.var(ddof=1) + h_low.var(ddof=1)) / 2.0))
                    h_effect = float((h_high.mean() - h_low.mean()) / h_pooled) if h_pooled > 1e-15 else 0.0
                else:
                    h_p, h_effect = np.nan, np.nan
                if not np.isfinite(float(result.pvalue)):
                    continue
                rows.append(
                    {
                        "test_type": "median_regime_difference",
                        "predictor": str(predictor),
                        "target": str(target),
                        "horizon": int(horizon),
                        "lag": 0,
                        "discovery_effect": effect,
                        "p_value": float(result.pvalue),
                        "n_discovery": int(len(discovery)),
                        "holdout_effect": h_effect,
                        "holdout_p_value": h_p,
                        "n_holdout": int(len(holdout)),
                        "threshold": threshold,
                    }
                )
    return rows


def _cointegration_tests(
    levels: pd.DataFrame,
    *,
    holdout_fraction: float,
    min_observations: int,
    max_tests: int,
) -> list[dict[str, Any]]:
    try:
        from statsmodels.tsa.stattools import coint
    except ImportError:
        return []
    rows: list[dict[str, Any]] = []
    columns = list(levels.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            if len(rows) >= max_tests:
                return rows
            pair = levels[[left, right]].dropna()
            if len(pair) < min_observations:
                continue
            cut = int(np.floor(len(pair) * (1 - holdout_fraction)))
            cut = max(20, min(cut, len(pair) - 20))
            discovery = pair.iloc[:cut]
            holdout = pair.iloc[cut:]
            try:
                statistic, p_value, _ = coint(discovery[left], discovery[right])
                if len(holdout) >= 20:
                    h_stat, h_p, _ = coint(holdout[left], holdout[right])
                else:
                    h_stat, h_p = np.nan, np.nan
            except (ValueError, np.linalg.LinAlgError):
                continue
            rows.append(
                {
                    "test_type": "cointegration",
                    "predictor": str(left),
                    "target": str(right),
                    "horizon": 0,
                    "lag": 0,
                    "discovery_effect": float(-statistic),
                    "p_value": float(p_value),
                    "n_discovery": int(len(discovery)),
                    "holdout_effect": float(-h_stat) if np.isfinite(h_stat) else np.nan,
                    "holdout_p_value": float(h_p) if np.isfinite(h_p) else np.nan,
                    "n_holdout": int(len(holdout)),
                }
            )
    return rows


def _idea_from_test(
    row: Mapping[str, Any],
    *,
    q_value: float,
    alpha: float,
    domain: str,
    transforms: Mapping[str, str],
    tests_performed: int,
) -> HypothesisIdea:
    predictor = str(row["predictor"])
    target = str(row["target"])
    test_type = str(row["test_type"])
    effect = float(row["discovery_effect"])
    holdout_effect = float(row.get("holdout_effect", np.nan))
    holdout_p = float(row.get("holdout_p_value", np.nan))
    data_status = _status(
        q_value=q_value,
        holdout_p=holdout_p,
        discovery_effect=effect,
        holdout_effect=holdout_effect,
        alpha=alpha,
    )
    sign = "positive" if effect > 0 else "negative" if effect < 0 else None
    horizon = int(row.get("horizon", 0))
    lag = int(row.get("lag", 0))

    if test_type == "lagged_correlation":
        direction = "higher" if effect > 0 else "lower"
        statement = (
            f"Changes in {predictor} available with lag {lag} are associated with {direction} "
            f"{target} outcomes over the next {horizon} period(s)."
        )
        question = (
            f"Does {predictor} contain stable incremental information about {target} over a "
            f"{horizon}-period horizon after chronology-safe lags and out-of-sample validation?"
        )
        methods = ("lagged regression", "HAC inference", "walk-forward validation", "block bootstrap", "placebo lags")
        mechanism = "A temporal association was detected in the discovery sample; economic mechanism remains to be established."
    elif test_type == "median_regime_difference":
        direction = "higher" if effect > 0 else "lower"
        statement = (
            f"Future {target} outcomes differ across high-versus-low states of {predictor}, "
            f"with the high state associated with {direction} outcomes over {horizon} period(s)."
        )
        question = (
            f"Is the relationship between {predictor} and future {target} state-dependent rather than adequately described by one linear effect?"
        )
        methods = ("regime conditioning", "Welch test", "quantile regression", "walk-forward validation", "bootstrap")
        mechanism = "A distributional state difference was detected; regime boundaries and mechanism require independent validation."
    elif test_type == "cointegration":
        statement = f"{predictor} and {target} may share a persistent long-run equilibrium relationship."
        question = f"Is the apparent cointegrating relation between {predictor} and {target} stable out of sample and economically interpretable?"
        methods = ("Engle-Granger", "ADF residual test", "rolling hedge ratio", "structural-break tests", "walk-forward pairs validation")
        mechanism = "The level-series residual appears more stationary than an unrestricted pair under the discovery sample."
        sign = None
    else:  # pragma: no cover - internal construction guards this
        raise ValueError(f"unsupported test_type {test_type}")

    priority = _priority(
        data_status=data_status,
        effect=effect,
        q_value=q_value,
        holdout_effect=holdout_effect,
    )
    evidence = dict(row)
    evidence.update(
        {
            "q_value": float(q_value),
            "multiple_testing": "Benjamini-Hochberg FDR",
            "tests_performed": int(tests_performed),
            "fdr_alpha": float(alpha),
            "predictor_transform": transforms.get(predictor, "raw"),
            "target_transform": transforms.get(target, "raw"),
        }
    )
    return HypothesisIdea(
        hypothesis_id=_identifier("H-DATA", test_type, predictor, target, horizon, lag),
        statement=statement,
        research_question=question,
        domain=domain,
        source="data",
        data_status=data_status,
        novelty_status="NOVELTY_NOT_ESTABLISHED",
        evidence_status="DATA_SCREEN",
        priority_score=priority,
        predictor=predictor,
        target=target,
        expected_sign=sign,
        horizon=horizon if horizon > 0 else None,
        mechanism=mechanism,
        falsification_rule=(
            "Reject or downgrade the candidate if the effect reverses on a pre-specified holdout, "
            "fails FDR control, disappears under chronology-safe resampling, or is explained by a documented confounder."
        ),
        methods=methods,
        data_requirements=(predictor, target),
        alternative_explanations=(
            "common factor exposure",
            "regime selection",
            "data revision or timestamp leakage",
            "multiple testing / data snooping",
            "transaction costs or implementation frictions where applicable",
        ),
        evidence=evidence,
        metadata={"test_type": test_type},
    )


def _idea_from_research_candidate(candidate: Any, *, source: str, data_status: str) -> HypothesisIdea:
    metadata = dict(getattr(candidate, "metadata", {}) or {})
    return HypothesisIdea(
        hypothesis_id=str(getattr(candidate, "candidate_id", _identifier("H", getattr(candidate, "hypothesis", "candidate")))),
        statement=str(getattr(candidate, "hypothesis", "")),
        research_question=str(getattr(candidate, "research_question", "")),
        domain=str(getattr(candidate, "domain", "quantitative_finance")),
        source=source,
        data_status=data_status,
        novelty_status=(
            str(getattr(candidate, "novelty_status", "NOT_ESTABLISHED")).upper().replace("-", "_")
            if str(getattr(candidate, "novelty_status", "NOT_ESTABLISHED")).upper().replace("-", "_") in NOVELTY_STATUSES
            else "NOVELTY_NOT_ESTABLISHED"
        ),
        evidence_status=str(getattr(candidate, "evidence_status", "PROPOSED")),
        priority_score=float(getattr(candidate, "priority_score", 0.5)),
        mechanism=str(getattr(candidate, "rationale", "")),
        falsification_rule=str(getattr(candidate, "falsification_rule", "")),
        methods=tuple(getattr(candidate, "methods", ()) or ()),
        data_requirements=tuple(getattr(candidate, "data_requirements", ()) or ()),
        source_observations=tuple(getattr(candidate, "source_observations", ()) or ()),
        evidence=dict(metadata.get("observation_evidence", {})),
        references=list(metadata.get("evidence", []) or []),
        metadata=metadata,
    )


def _deduplicate(items: Sequence[HypothesisIdea], threshold: float = 0.88) -> list[HypothesisIdea]:
    output: list[HypothesisIdea] = []
    for item in sorted(items, key=lambda x: x.priority_score, reverse=True):
        duplicate = next((existing for existing in output if _text_similarity(item.statement, existing.statement) >= threshold), None)
        if duplicate is None:
            output.append(item)
            continue
        # Preserve the strongest candidate but record that another source converged on it.
        sources = sorted(set(duplicate.metadata.get("supporting_sources", [duplicate.source])) | {item.source})
        duplicate.metadata["supporting_sources"] = sources
        duplicate.metadata.setdefault("merged_hypotheses", []).append(item.hypothesis_id)
        if item.references:
            duplicate.references.extend(item.references)
    return output


def from_data(
    data: pd.DataFrame | pd.Series | Mapping[str, Any],
    *,
    domain: str = "quantitative_finance",
    targets: str | Sequence[str] | None = None,
    horizons: Sequence[int] = (1, 5, 20),
    lags: Sequence[int] = (0, 1, 5),
    transforms: Mapping[str, str] | None = None,
    holdout_fraction: float = 0.30,
    min_observations: int = 80,
    fdr_alpha: float = 0.05,
    min_abs_effect: float = 0.08,
    max_tests: int = 1_500,
    max_candidates: int = 50,
    include_regime_tests: bool = True,
    include_cointegration: bool = True,
    include_structural_scan: bool = True,
) -> HypothesisCollection:
    """Discover falsifiable hypotheses directly from time-indexed quantitative data.

    The function uses a chronological discovery/holdout split and Benjamini-Hochberg
    correction across the statistical screening family.  Returned candidates are
    still *research hypotheses*, not established findings.
    """
    if not 0.05 <= holdout_fraction <= 0.5:
        raise InputValidationError("holdout_fraction must be between 0.05 and 0.5")
    if min_observations < 20:
        raise InputValidationError("min_observations must be at least 20")
    if not 0 < fdr_alpha < 1:
        raise InputValidationError("fdr_alpha must lie in (0, 1)")
    if min_abs_effect < 0:
        raise InputValidationError("min_abs_effect must be non-negative")
    if max_tests < 1 or max_candidates < 1:
        raise InputValidationError("max_tests and max_candidates must be positive")

    frame, source_map = _coerce_panel(data)
    active_domain = _normalise_domain(domain)
    if len(frame) < min_observations:
        raise InputValidationError(f"data-driven discovery requires at least {min_observations} observations")

    transform_map: dict[str, str] = {}
    transformed = pd.DataFrame(index=frame.index)
    supplied = {str(key): str(value) for key, value in (transforms or {}).items()}
    for column in frame.columns:
        method = supplied.get(str(column), _infer_transform(frame[column], active_domain))
        transform_map[str(column)] = method
        transformed[str(column)] = _transform_series(frame[column], method)

    if targets is None:
        target_names = [str(column) for column in frame.columns]
    elif isinstance(targets, str):
        target_names = [targets]
    else:
        target_names = [str(item) for item in targets]
    unknown = sorted(set(target_names) - set(map(str, frame.columns)))
    if unknown:
        raise InputValidationError(f"targets not found in data: {unknown}")

    horizon_values = tuple(sorted({int(value) for value in horizons}))
    lag_values = tuple(sorted({int(value) for value in lags}))
    if not horizon_values or any(value <= 0 for value in horizon_values):
        raise InputValidationError("horizons must contain positive integers")
    if not lag_values or any(value < 0 for value in lag_values):
        raise InputValidationError("lags must contain non-negative integers")

    tests: list[dict[str, Any]] = []
    tests.extend(
        _correlation_tests(
            transformed,
            transform_map,
            targets=target_names,
            horizons=horizon_values,
            lags=lag_values,
            holdout_fraction=holdout_fraction,
            min_observations=min_observations,
            max_tests=max_tests,
        )
    )
    remaining = max(0, max_tests - len(tests))
    if include_regime_tests and remaining:
        tests.extend(
            _regime_tests(
                transformed,
                transform_map,
                targets=target_names,
                horizons=horizon_values,
                holdout_fraction=holdout_fraction,
                min_observations=min_observations,
                max_tests=remaining,
            )
        )
    remaining = max(0, max_tests - len(tests))
    if include_cointegration and remaining and frame.shape[1] >= 2:
        tests.extend(
            _cointegration_tests(
                frame,
                holdout_fraction=holdout_fraction,
                min_observations=min_observations,
                max_tests=remaining,
            )
        )

    ideas: list[HypothesisIdea] = []
    if tests:
        q_values = _bh_adjust([float(row["p_value"]) for row in tests])
        for row, q_value in zip(tests, q_values):
            effect = float(row["discovery_effect"])
            # Keep FDR-supported tests even when the effect is small; otherwise apply a practical floor.
            if abs(effect) < min_abs_effect and q_value > fdr_alpha:
                continue
            ideas.append(
                _idea_from_test(
                    row,
                    q_value=float(q_value),
                    alpha=fdr_alpha,
                    domain=active_domain,
                    transforms=transform_map,
                    tests_performed=len(tests),
                )
            )

    structural_ideas: list[HypothesisIdea] = []
    if include_structural_scan:
        try:
            board = _discovery.weekly(
                data=frame,
                domain=active_domain,
                n=max_candidates,
                include_catalog=False,
            )
            for candidate in board.candidates:
                structural_ideas.append(
                    _idea_from_research_candidate(
                        candidate, source="data_structural_scan", data_status="EXPLORATORY"
                    )
                )
        except (ValueError, TypeError, KeyError, np.linalg.LinAlgError):
            structural_ideas = []

        # Conservative fallback: even when threshold-based discovery finds no
        # event, keep one explicitly exploratory structural question so the
        # structural-scan channel remains visible and auditable. This does not
        # assert statistical support or novelty.
        if not structural_ideas and len(frame) >= min_observations:
            numeric = frame.select_dtypes(include=[np.number]).dropna(how="all")
            if numeric.shape[1] >= 2:
                corr = numeric.corr().abs()
                upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool)).stack()
                if len(upper):
                    left, right = upper.idxmax()
                    pair = numeric[[left, right]].dropna()
                    half = max(1, len(pair) // 2)
                    c1 = float(pair.iloc[:half].corr().iloc[0, 1]) if half >= 3 else np.nan
                    c2 = float(pair.iloc[half:].corr().iloc[0, 1]) if len(pair) - half >= 3 else np.nan
                    structural_ideas.append(HypothesisIdea(
                        hypothesis_id=_identifier("H-STRUCT", left, right, len(pair)),
                        statement=f"The dependence between {left} and {right} may vary across market states or sample regimes.",
                        research_question=f"Is the relationship between {left} and {right} structurally stable through time?",
                        domain=active_domain,
                        source="data_structural_scan",
                        data_status="EXPLORATORY",
                        novelty_status="NOVELTY_NOT_ESTABLISHED",
                        evidence_status="STRUCTURAL_SCREEN",
                        priority_score=float(min(0.60, 0.30 + 0.25 * float(upper.max()))),
                        predictor=str(left),
                        target=str(right),
                        mechanism="A structural-stability question was generated from the strongest observed pairwise dependence; no causal interpretation is implied.",
                        methods=("rolling correlation", "change-point tests", "subperiod stability", "block bootstrap"),
                        data_requirements=(str(left), str(right)),
                        evidence={"absolute_full_sample_correlation": float(upper.max()), "first_half_correlation": c1, "second_half_correlation": c2, "sample_size": int(len(pair))},
                        metadata={"test_type": "structural_stability_fallback", "threshold_triggered": False},
                    ))
            elif numeric.shape[1] == 1:
                column = str(numeric.columns[0])
                series = numeric.iloc[:, 0].dropna()
                structural_ideas.append(HypothesisIdea(
                    hypothesis_id=_identifier("H-STRUCT", column, len(series)),
                    statement=f"The distribution of {column} may be state-dependent rather than stable through time.",
                    research_question=f"Is the distribution of {column} structurally stable across the observed sample?",
                    domain=active_domain,
                    source="data_structural_scan",
                    data_status="EXPLORATORY",
                    novelty_status="NOVELTY_NOT_ESTABLISHED",
                    evidence_status="STRUCTURAL_SCREEN",
                    priority_score=0.30,
                    predictor=column,
                    methods=("rolling moments", "change-point tests", "subperiod stability", "bootstrap"),
                    data_requirements=(column,),
                    evidence={"sample_size": int(len(series))},
                    metadata={"test_type": "structural_stability_fallback", "threshold_triggered": False},
                ))
        ideas.extend(structural_ideas)

    ideas = _deduplicate(ideas)
    # Preserve evidence-channel provenance: if a structural candidate was merged
    # into a stronger statistical screen, retain the highest-priority structural
    # observation as an explicit exploratory candidate rather than making that
    # channel disappear from the result set.
    if structural_ideas and not any(item.source == "data_structural_scan" for item in ideas):
        retained = max(structural_ideas, key=lambda item: item.priority_score)
        retained.metadata["retained_for_source_provenance"] = True
        ideas.append(retained)
    ideas = sorted(ideas, key=lambda item: item.priority_score, reverse=True)[:max_candidates]
    return HypothesisCollection(
        ideas,
        metadata={
            "source": "data",
            "domain": active_domain,
            "rows": int(len(frame)),
            "columns": int(frame.shape[1]),
            "targets": target_names,
            "transforms": transform_map,
            "source_map": source_map,
            "tests_performed": int(len(tests)),
            "multiple_testing": "Benjamini-Hochberg FDR",
            "fdr_alpha": float(fdr_alpha),
            "holdout_fraction": float(holdout_fraction),
            "min_observations": int(min_observations),
            "max_tests": int(max_tests),
        },
    )


def _as_literature_source(
    papers: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any],
    *,
    topic: str | None = None,
) -> LiteratureCorpus | HypothesisRegistry:
    if isinstance(papers, (LiteratureCorpus, HypothesisRegistry)):
        return papers
    if isinstance(papers, (str, Path)):
        path = Path(papers)
        if path.exists() or path.suffix.lower() == ".pdf":
            return LiteratureCorpus.from_pdfs(path, topic=topic)
        return LiteratureCorpus.from_texts([str(papers)], topic=topic)
    sequence = list(papers)
    if sequence and all(isinstance(item, (str, Path)) and Path(item).exists() for item in sequence):
        return LiteratureCorpus.from_pdfs(sequence, topic=topic)
    return LiteratureCorpus.from_texts(sequence, topic=topic)


def from_literature(
    papers: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any],
    *,
    topic: str | None = None,
    max_candidates: int = 50,
) -> HypothesisCollection:
    """Discover source-linked hypotheses and research gaps from scientific literature."""
    try:
        source = _as_literature_source(papers, topic=topic)
        board = _discovery.from_literature(source, topic=topic, max_candidates=max_candidates)
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        raise HypothesisDiscoveryError(f"literature hypothesis discovery failed: {exc}") from exc
    ideas = [
        _idea_from_research_candidate(candidate, source="literature", data_status="LITERATURE_DERIVED")
        for candidate in board.candidates
    ]
    # Translate corpus-relative labels to conservative public novelty states.
    for idea, candidate in zip(ideas, board.candidates):
        original = str(getattr(candidate, "novelty_status", "NOT_ESTABLISHED")).upper().replace("-", "_")
        if original == "CONTRADICTORY":
            idea.novelty_status = "CONTRADICTORY_LITERATURE"
        elif original == "CORPUS_NOVEL":
            idea.novelty_status = "POTENTIAL_GAP"
        elif original in {"ESTABLISHED", "REPLICATED"}:
            idea.novelty_status = "PRIOR_ART_FOUND"
        elif original == "UNDEREXPLORED":
            idea.novelty_status = "CORPUS_RELATED"
        else:
            idea.novelty_status = "NOVELTY_NOT_ESTABLISHED"
        idea.metadata["corpus_relative_label"] = original
    fingerprint = source.corpus_fingerprint if isinstance(source, HypothesisRegistry) else source.fingerprint
    return HypothesisCollection(
        sorted(ideas, key=lambda item: item.priority_score, reverse=True),
        metadata={
            "source": "literature",
            "topic": topic,
            "corpus_fingerprint": fingerprint,
            "tests_performed": 0,
            "multiple_testing": "not_applicable",
        },
    )


def from_model_disagreement(
    predictions: pd.DataFrame | Mapping[str, Sequence[float]],
    *,
    domain: str = "quantitative_finance",
    max_candidates: int = 25,
) -> HypothesisCollection:
    """Generate hypotheses from periods where plausible models disagree materially."""
    board = _discovery.weekly(
        predictions=pd.DataFrame(predictions),
        domain=domain,
        n=max_candidates,
        include_catalog=False,
    )
    ideas = [
        _idea_from_research_candidate(candidate, source="model_disagreement", data_status="EXPLORATORY")
        for candidate in board.candidates
    ]
    return HypothesisCollection(ideas, {"source": "model_disagreement", "tests_performed": 0})


def from_robustness(
    results: pd.DataFrame,
    *,
    metric: str,
    domain: str = "quantitative_finance",
    max_candidates: int = 25,
) -> HypothesisCollection:
    """Generate hypotheses from specification-sensitive research results."""
    board = _discovery.weekly(
        robustness_results=pd.DataFrame(results),
        robustness_metric=metric,
        domain=domain,
        n=max_candidates,
        include_catalog=False,
    )
    ideas = [
        _idea_from_research_candidate(candidate, source="robustness", data_status="EXPLORATORY")
        for candidate in board.candidates
    ]
    return HypothesisCollection(ideas, {"source": "robustness", "metric": metric, "tests_performed": 0})


def _literature_registry(
    corpus: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any],
    *,
    topic: str | None,
    max_candidates: int = 250,
) -> tuple[HypothesisRegistry, str | None]:
    try:
        source = _as_literature_source(corpus, topic=topic)
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        raise HypothesisDiscoveryError(f"could not prepare literature corpus: {exc}") from exc
    if isinstance(source, HypothesisRegistry):
        return source, source.corpus_fingerprint
    try:
        registry = source.discover_hypotheses(topic=topic, max_candidates=max_candidates)
    except (ValueError, TypeError, RuntimeError) as exc:
        raise HypothesisDiscoveryError(f"hypothesis prior-art extraction failed: {exc}") from exc
    if len(registry) == 0 and topic is not None:
        # A domain label is an aid, not a reason to erase potentially relevant prior art.
        registry = source.discover_hypotheses(topic=None, max_candidates=max_candidates)
    return registry, source.fingerprint


def audit(
    hypothesis: HypothesisIdea | str,
    *,
    corpus: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any] | None = None,
    topic: str | None = None,
    top_k: int = 10,
) -> HypothesisAuditResult:
    """Audit prior art around a hypothesis without asserting global novelty."""
    if isinstance(hypothesis, HypothesisIdea):
        idea = hypothesis
    else:
        statement = str(hypothesis).strip()
        if not statement:
            raise InputValidationError("hypothesis must not be empty")
        idea = HypothesisIdea(
            _identifier("H-AUDIT", statement),
            statement,
            f"Is the following hypothesis supported and distinct from documented prior work: {statement}?",
            domain=_normalise_domain(topic or "quantitative_finance"),
            source="manual",
            data_status="NOT_TESTED",
        )

    if corpus is None:
        return HypothesisAuditResult(
            idea.hypothesis_id,
            "NOVELTY_NOT_ESTABLISHED",
            idea.data_status,
            pd.DataFrame(columns=["hypothesis_id", "similarity", "statement", "corpus_label", "evidence_status", "source_count", "pages"]),
            "Supply a documented literature corpus and perform a manual prior-art review before making any novelty claim.",
            warnings=("No literature corpus was supplied; novelty cannot be assessed.",),
        )

    registry, fingerprint = _literature_registry(corpus, topic=topic or idea.domain)
    rows = []
    for item in registry.hypotheses:
        similarity = _text_similarity(idea.statement, item.statement)
        rows.append(
            {
                "hypothesis_id": item.hypothesis_id,
                "similarity": similarity,
                "statement": item.statement,
                "corpus_label": item.novelty_status,
                "evidence_status": item.evidence_status,
                "source_count": item.source_count,
                "pages": ", ".join(f"{excerpt.paper_id}:p{excerpt.page}" for excerpt in item.evidence),
            }
        )
    matches = (
        pd.DataFrame(rows).sort_values("similarity", ascending=False).head(top_k).reset_index(drop=True)
        if rows
        else pd.DataFrame(columns=["hypothesis_id", "similarity", "statement", "corpus_label", "evidence_status", "source_count", "pages"])
    )

    if matches.empty:
        novelty = "NOVELTY_NOT_ESTABLISHED"
        recommendation = "No hypothesis-like passage was extracted from this corpus. Expand the prior-art search; absence of a match is not evidence of novelty."
    else:
        best = matches.iloc[0]
        similarity = float(best.similarity)
        label = str(best.corpus_label).lower().replace("-", "_")
        if label == "contradictory" and similarity >= 0.45:
            novelty = "CONTRADICTORY_LITERATURE"
            recommendation = "Review the contradictory source passages and design a test that discriminates between competing explanations."
        elif similarity >= 0.72:
            novelty = "PRIOR_ART_FOUND"
            recommendation = "Close prior art was found. Frame the project as replication, extension, boundary test or methodological comparison unless broader review supports another claim."
        elif label == "corpus_novel" and similarity >= 0.45:
            novelty = "POTENTIAL_GAP"
            recommendation = "The supplied corpus contains a related explicit gap. Validate it against broader literature before describing it as novel."
        elif similarity >= 0.50:
            novelty = "CORPUS_RELATED"
            recommendation = "Related prior work exists. Compare definitions, data, horizon, method and market scope before formulating the contribution."
        else:
            novelty = "NOVELTY_NOT_ESTABLISHED"
            recommendation = "No close match was detected in this corpus. Expand the search across databases, synonyms and adjacent literatures before any novelty claim."

    warnings = (
        "Novelty is corpus-relative; this audit does not search the complete global literature.",
        "Automatically extracted source passages must be checked on the cited pages before publication.",
    )
    return HypothesisAuditResult(
        idea.hypothesis_id,
        novelty,
        idea.data_status,
        matches,
        recommendation,
        warnings=warnings,
        corpus_fingerprint=fingerprint,
    )


def search(
    query: str,
    *,
    hypotheses: HypothesisCollection | Sequence[HypothesisIdea] | None = None,
    papers: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any] | None = None,
    topic: str | None = None,
    top_k: int = 10,
) -> HypothesisSearchResult:
    """Search generated hypotheses and source-linked literature with one query."""
    if not str(query).strip():
        raise InputValidationError("query must not be empty")
    if hypotheses is None:
        hypothesis_matches = pd.DataFrame()
    else:
        collection = hypotheses if isinstance(hypotheses, HypothesisCollection) else HypothesisCollection(list(hypotheses))
        hypothesis_matches = collection.search(query, top_k=top_k)

    excerpts = pd.DataFrame()
    if papers is not None:
        source = _as_literature_source(papers, topic=topic)
        if isinstance(source, HypothesisRegistry):
            rows = []
            for item in source.hypotheses:
                rows.append(
                    {
                        "paper_id": None,
                        "page": None,
                        "similarity": _text_similarity(query, item.statement),
                        "text": item.statement,
                        "hypothesis_id": item.hypothesis_id,
                    }
                )
            excerpts = pd.DataFrame(rows).sort_values("similarity", ascending=False).head(top_k) if rows else pd.DataFrame()
        else:
            hits = source.search(query, top_k=top_k)
            excerpts = pd.DataFrame(
                [
                    {
                        "paper_id": hit.paper_id,
                        "page": hit.page,
                        "similarity": _text_similarity(query, hit.text),
                        "text": hit.text,
                        "section": hit.section,
                    }
                    for hit in hits
                ]
            )
            if len(excerpts):
                excerpts = excerpts.sort_values("similarity", ascending=False).reset_index(drop=True)
    return HypothesisSearchResult(str(query), hypothesis_matches, excerpts)


def discover(
    *,
    data: pd.DataFrame | pd.Series | Mapping[str, Any] | None = None,
    papers: LiteratureCorpus | HypothesisRegistry | str | Path | Sequence[Any] | None = None,
    predictions: pd.DataFrame | Mapping[str, Sequence[float]] | None = None,
    robustness_results: pd.DataFrame | None = None,
    robustness_metric: str | None = None,
    domain: str = "quantitative_finance",
    max_candidates: int = 50,
    audit_data_candidates: bool = True,
    **data_kwargs: Any,
) -> HypothesisCollection:
    """Combine data-driven and literature-driven hypothesis discovery.

    Data evidence and novelty evidence remain separate.  When both data and a
    literature corpus are supplied, data-generated candidates are audited against
    the supplied corpus; no global novelty claim is made automatically.
    """
    collections: list[HypothesisCollection] = []
    active_domain = _normalise_domain(domain)
    if data is not None:
        collections.append(from_data(data, domain=active_domain, max_candidates=max_candidates, **data_kwargs))
    if papers is not None:
        collections.append(from_literature(papers, topic=active_domain, max_candidates=max_candidates))
    if predictions is not None:
        collections.append(from_model_disagreement(predictions, domain=active_domain, max_candidates=max_candidates))
    if robustness_results is not None:
        if robustness_metric is None:
            raise InputValidationError("robustness_metric is required with robustness_results")
        collections.append(
            from_robustness(
                robustness_results,
                metric=robustness_metric,
                domain=active_domain,
                max_candidates=max_candidates,
            )
        )
    if not collections:
        raise InputValidationError("provide at least one of data, papers, predictions, or robustness_results")

    items = [item for collection in collections for item in collection.hypotheses]
    if papers is not None and data is not None and audit_data_candidates:
        audited: list[HypothesisIdea] = []
        for item in items:
            if item.source.startswith("data"):
                result = audit(item, corpus=papers, topic=active_domain, top_k=5)
                references = result.closest_matches.to_dict(orient="records")
                audited.append(
                    replace(
                        item,
                        novelty_status=result.novelty_status,
                        references=item.references + references,
                        metadata={
                            **item.metadata,
                            "novelty_audit_recommendation": result.recommendation,
                            "corpus_fingerprint": result.corpus_fingerprint,
                        },
                    )
                )
            else:
                audited.append(item)
        items = audited

    items = _deduplicate(items)
    items = sorted(items, key=lambda item: item.priority_score, reverse=True)[:max_candidates]
    metadata = {
        "source": "combined" if len(collections) > 1 else collections[0].metadata.get("source", "unknown"),
        "domain": active_domain,
        "component_sources": [collection.metadata.get("source") for collection in collections],
        "tests_performed": int(sum(int(collection.metadata.get("tests_performed", 0)) for collection in collections)),
        "multiple_testing": "Benjamini-Hochberg FDR" if any(collection.metadata.get("tests_performed", 0) for collection in collections) else "not_applicable",
        "novelty_rule": "Never established automatically; corpus-relative prior-art audit only.",
    }
    return HypothesisCollection(items, metadata)


__all__ = [
    "DATA_STATUSES",
    "NOVELTY_STATUSES",
    "HypothesisIdea",
    "HypothesisCollection",
    "HypothesisAuditResult",
    "HypothesisSearchResult",
    "from_data",
    "from_literature",
    "from_model_disagreement",
    "from_robustness",
    "discover",
    "search",
    "audit",
]
