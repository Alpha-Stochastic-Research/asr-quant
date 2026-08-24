"""Research-discovery engine for ASRQuant.

The purpose of this module is not to auto-declare novelty.  It turns observable
market/literature/model evidence into falsifiable *research candidates* and then
hands the selected candidate to :class:`asrquant.workflow.ResearchProject`.

Typical use
-----------
>>> board = asr.discovery.weekly(data=curve_history, domain="fixed_income")
>>> board.to_frame()
>>> project = board.start(0)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew

from .interest_rates import level_slope_curvature, yield_curve_pca
from .literature import HypothesisRegistry, LiteratureCorpus
from .workflow import ResearchProject


@dataclass(frozen=True)
class ResearchObservation:
    """Transparent quantitative observation from which a question may be formed."""

    observation_id: str
    kind: str
    description: str
    score: float
    variables: tuple[str, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)
    domain: str = "quantitative_finance"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchCandidate:
    """Falsifiable candidate idea; novelty is never asserted automatically."""

    candidate_id: str
    title: str
    research_question: str
    hypothesis: str
    domain: str
    contribution_type: str
    rationale: str
    methods: tuple[str, ...] = ()
    data_requirements: tuple[str, ...] = ()
    falsification_rule: str = "Reject the candidate if the effect is not stable under pre-specified robustness checks."
    novelty_status: str = "NOT_ESTABLISHED"
    evidence_status: str = "PROPOSED"
    priority_score: float = 0.5
    source_observations: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def brief(self) -> str:
        methods = ", ".join(self.methods) or "To be specified"
        data = ", ".join(self.data_requirements) or "To be specified"
        risks = "; ".join(self.risks) or "No risks documented yet"
        return (
            f"# {self.title}\n\n"
            f"**Candidate:** `{self.candidate_id}`  \n"
            f"**Domain:** {self.domain}  \n"
            f"**Contribution type:** {self.contribution_type}  \n"
            f"**Novelty:** {self.novelty_status} (requires literature review)\n\n"
            f"## Research question\n{self.research_question}\n\n"
            f"## Hypothesis\n{self.hypothesis}\n\n"
            f"## Why this is worth testing\n{self.rationale}\n\n"
            f"## Suggested methods\n{methods}\n\n"
            f"## Data requirements\n{data}\n\n"
            f"## Falsification rule\n{self.falsification_rule}\n\n"
            f"## Main risks\n{risks}\n"
        )


@dataclass
class ResearchBoard:
    """Ranked weekly research-candidate board."""

    candidates: list[ResearchCandidate]
    observations: list[ResearchObservation] = field(default_factory=list)
    domain: str = "quantitative_finance"
    scope_note: str = (
        "Candidates are hypothesis-generation outputs. Novelty is NOT established until a documented "
        "literature search and prior-art review are completed."
    )

    def __len__(self) -> int:
        return len(self.candidates)

    def __iter__(self):
        return iter(self.candidates)

    def select(self, identifier: str | int) -> ResearchCandidate:
        if isinstance(identifier, int):
            return self.candidates[identifier]
        for item in self.candidates:
            if item.candidate_id == identifier:
                return item
        raise KeyError(f"unknown research candidate {identifier!r}")

    def top(self, n: int = 5) -> "ResearchBoard":
        return ResearchBoard(self.candidates[:n], self.observations, self.domain, self.scope_note)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "candidate_id": c.candidate_id,
                    "title": c.title,
                    "research_question": c.research_question,
                    "hypothesis": c.hypothesis,
                    "domain": c.domain,
                    "contribution_type": c.contribution_type,
                    "priority_score": c.priority_score,
                    "novelty_status": c.novelty_status,
                    "methods": ", ".join(c.methods),
                    "data_requirements": ", ".join(c.data_requirements),
                }
                for c in self.candidates
            ]
        )

    def observations_frame(self) -> pd.DataFrame:
        return pd.DataFrame([o.to_dict() for o in self.observations])

    def start(self, identifier: str | int, *, name: str | None = None) -> ResearchProject:
        """Turn one candidate into the existing ASRQuant end-to-end ResearchProject."""
        c = self.select(identifier)
        project = ResearchProject.from_hypothesis(
            c.hypothesis,
            name=name or f"ASR Weekly Research — {c.title}",
            topic=c.domain,
            novelty_status=c.novelty_status.lower().replace("_", "-"),
            evidence_status=c.evidence_status.lower(),
            mechanism=c.rationale,
            invalidation_criteria=[c.falsification_rule],
            metadata={
                "candidate_id": c.candidate_id,
                "research_question": c.research_question,
                "contribution_type": c.contribution_type,
                "suggested_methods": list(c.methods),
                "data_requirements": list(c.data_requirements),
                "source_observations": list(c.source_observations),
                "risks": list(c.risks),
                **dict(c.metadata),
            },
        )
        project._record("research_discovery", candidate_id=c.candidate_id, title=c.title)
        return project

    def weekly_plan(self, identifier: str | int, *, launch_friday: date | str | None = None) -> pd.DataFrame:
        """Create the Friday-to-Friday ASR operating plan for a selected candidate."""
        c = self.select(identifier)
        launch = pd.Timestamp(launch_friday or date.today()).date()
        if launch.weekday() != 4:
            launch = launch + timedelta(days=(4 - launch.weekday()) % 7)
        tasks = [
            (0, "Friday", "Launch", "Lock question, hypothesis, owners, falsification rule and evidence contract."),
            (1, "Saturday", "Prior art", "Map literature, nearest methods, definitions and competing explanations."),
            (2, "Sunday", "Data design", "Freeze dataset, timestamps, availability lags, sample and validation split."),
            (3, "Monday", "Baseline", "Implement simplest baseline and reproduce known reference behaviour."),
            (4, "Tuesday", "Main experiment", "Estimate/model the proposed effect and record full diagnostics."),
            (5, "Wednesday", "Robustness", "Stress assumptions, subperiods, alternatives, costs and falsification tests."),
            (6, "Thursday", "Review", "Independent reproduction, scientific review, limitations and claim audit."),
            (7, "Friday", "Publish", "Release note, notebook, figure, repository evidence and next research question."),
        ]
        return pd.DataFrame(
            {
                "date": [launch + timedelta(days=d) for d, *_ in tasks],
                "day": [day for _, day, _, _ in tasks],
                "stage": [stage for _, _, stage, _ in tasks],
                "deliverable": [deliverable for *_, deliverable in tasks],
                "candidate_id": c.candidate_id,
            }
        )

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "domain": self.domain,
            "scope_note": self.scope_note,
            "observations": [o.to_dict() for o in self.observations],
            "candidates": [c.to_dict() for c in self.candidates],
        }
        output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return output

    def save_brief(self, identifier: str | int, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.select(identifier).brief(), encoding="utf-8")
        return output


def _identifier(prefix: str, *parts: Any) -> str:
    digest = sha256("|".join(map(str, parts)).encode()).hexdigest()[:8]
    return f"{prefix}-{digest}"


def _numeric_frame(data: pd.DataFrame | Mapping[str, Sequence[float]]) -> pd.DataFrame:
    frame = pd.DataFrame(data).copy()
    frame = frame.apply(pd.to_numeric, errors="coerce")
    if isinstance(frame.index, pd.DatetimeIndex):
        frame = frame.sort_index()
    frame = frame.dropna(how="all")
    if frame.shape[1] == 0 or len(frame) < 10:
        raise ValueError("research discovery requires at least 10 observations of numeric data")
    return frame


def scan_market(
    data: pd.DataFrame | Mapping[str, Sequence[float]],
    *,
    domain: str = "quantitative_finance",
    rolling_window: int | None = None,
    max_pairwise: int = 25,
) -> list[ResearchObservation]:
    """Detect interpretable instability, tails and relationship breaks.

    The scan intentionally uses transparent diagnostics rather than a black-box
    anomaly model: variance shifts, mean shifts, tail asymmetry, autocorrelation
    and first-half/second-half correlation breaks.
    """
    frame = _numeric_frame(data)
    observations: list[ResearchObservation] = []
    n = len(frame)
    half = n // 2
    window = rolling_window or max(10, min(63, n // 5))
    for column in frame.columns:
        x = frame[column].dropna()
        if len(x) < 10:
            continue
        first, second = x.iloc[: len(x)//2], x.iloc[len(x)//2 :]
        mean_scale = max(float(x.std(ddof=1)), 1e-12)
        mean_shift = abs(float(second.mean() - first.mean())) / mean_scale
        if mean_shift >= 0.5:
            observations.append(ResearchObservation(
                _identifier("OBS-MEAN", column, mean_shift), "mean_shift",
                f"{column} shows a material sample mean shift between the first and second halves.",
                min(mean_shift / 2.0, 1.0), (str(column),),
                {"standardized_mean_shift": mean_shift, "first_mean": float(first.mean()), "second_mean": float(second.mean())}, domain,
            ))
        s1, s2 = float(first.std(ddof=1)), float(second.std(ddof=1))
        ratio = max(s1, s2) / max(min(s1, s2), 1e-12)
        if ratio >= 1.5:
            observations.append(ResearchObservation(
                _identifier("OBS-VAR", column, ratio), "variance_shift",
                f"{column} volatility differs materially across the two sample halves.",
                min((ratio - 1.0) / 2.0, 1.0), (str(column),),
                {"volatility_ratio": ratio, "first_std": s1, "second_std": s2}, domain,
            ))
        ac1 = float(x.autocorr(1)) if len(x) > 2 else np.nan
        if np.isfinite(ac1) and abs(ac1) >= 0.25:
            observations.append(ResearchObservation(
                _identifier("OBS-AC", column, ac1), "serial_dependence",
                f"{column} has non-trivial lag-1 serial dependence in this sample.",
                min(abs(ac1), 1.0), (str(column),), {"lag1_autocorrelation": ac1}, domain,
            ))
        sk = float(skew(x.to_numpy(), bias=False, nan_policy="omit"))
        ku = float(kurtosis(x.to_numpy(), fisher=True, bias=False, nan_policy="omit"))
        if abs(sk) >= 0.75 or ku >= 2.0:
            score = min(max(abs(sk) / 3.0, ku / 10.0), 1.0)
            observations.append(ResearchObservation(
                _identifier("OBS-TAIL", column, sk, ku), "tail_asymmetry",
                f"{column} exhibits material skewness and/or excess kurtosis.", score, (str(column),),
                {"skewness": sk, "excess_kurtosis": ku}, domain,
            ))
        roll = x.rolling(window).std()
        if roll.notna().sum() >= 4:
            rmin, rmax = float(roll.min()), float(roll.max())
            if rmin > 0 and rmax / rmin >= 2.0:
                observations.append(ResearchObservation(
                    _identifier("OBS-RVOL", column, rmax / rmin), "rolling_volatility_regime",
                    f"{column} rolling volatility spans more than a twofold range.",
                    min((rmax / rmin - 1.0) / 3.0, 1.0), (str(column),),
                    {"window": window, "max_min_vol_ratio": rmax / rmin}, domain,
                ))

    columns = list(frame.columns)[: max(2, int(np.sqrt(max_pairwise * 2)) + 2)]
    pairs = 0
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            if pairs >= max_pairwise:
                break
            a, b = columns[i], columns[j]
            pair = frame[[a, b]].dropna()
            if len(pair) < 12:
                continue
            h = len(pair) // 2
            c1 = float(pair.iloc[:h].corr().iloc[0, 1])
            c2 = float(pair.iloc[h:].corr().iloc[0, 1])
            diff = abs(c2 - c1)
            if diff >= 0.35:
                observations.append(ResearchObservation(
                    _identifier("OBS-CORR", a, b, c1, c2), "correlation_break",
                    f"The correlation between {a} and {b} changes materially across sample halves.",
                    min(diff / 1.2, 1.0), (str(a), str(b)),
                    {"first_half_correlation": c1, "second_half_correlation": c2, "absolute_change": diff}, domain,
                ))
            pairs += 1
        if pairs >= max_pairwise:
            break
    return sorted(observations, key=lambda x: x.score, reverse=True)


def scan_yield_curve_history(yields: pd.DataFrame) -> list[ResearchObservation]:
    """Fixed-income specific diagnostics for a panel of yield-curve maturities."""
    frame = _numeric_frame(yields).dropna()
    if frame.shape[1] < 3:
        raise ValueError("yield-curve discovery needs at least three maturities")
    observations = scan_market(frame.diff().dropna(), domain="fixed_income")
    factors = level_slope_curvature(frame)
    factor_obs = scan_market(factors.diff().dropna(), domain="fixed_income")
    observations.extend(factor_obs)
    pca = yield_curve_pca(frame, n_components=min(3, frame.shape[1]))
    explained = pca["explained_variance_ratio"]
    first_three = float(explained.sum())
    if first_three < 0.90:
        observations.append(ResearchObservation(
            _identifier("OBS-PCA", first_three), "curve_factor_residual",
            "The first three principal components explain less than 90% of yield-curve change variance in this sample.",
            min((0.90 - first_three) / 0.30 + 0.4, 1.0), tuple(map(str, frame.columns)),
            {"first_three_explained_variance": first_three}, "fixed_income",
        ))
    slope = factors["slope"].dropna()
    crossings = int(np.sum(np.sign(slope.to_numpy()[1:]) != np.sign(slope.to_numpy()[:-1])))
    if crossings > 0:
        observations.append(ResearchObservation(
            _identifier("OBS-SLOPE", crossings, len(slope)), "curve_regime_transition",
            "The curve slope changes sign in the observed sample, creating identifiable inversion/normalization transitions.",
            min(0.4 + crossings / max(10, len(slope)), 1.0), ("slope",),
            {"sign_crossings": crossings, "sample_size": len(slope)}, "fixed_income",
        ))
    return sorted(observations, key=lambda x: x.score, reverse=True)


def scan_model_disagreement(
    predictions: pd.DataFrame | Mapping[str, Sequence[float]],
    *,
    target: Sequence[float] | pd.Series | None = None,
    domain: str = "quantitative_finance",
) -> list[ResearchObservation]:
    """Find candidate questions where model outputs materially disagree."""
    frame = _numeric_frame(predictions).dropna()
    if frame.shape[1] < 2:
        raise ValueError("provide predictions from at least two models")
    dispersion = frame.std(axis=1, ddof=0)
    scale = max(float(frame.abs().stack().median()), 1e-12)
    ratio = float(dispersion.mean() / scale)
    obs = [ResearchObservation(
        _identifier("OBS-MODEL", ratio), "model_disagreement",
        "Competing models produce materially dispersed outputs on the same observations.",
        min(ratio, 1.0), tuple(map(str, frame.columns)),
        {"mean_cross_model_dispersion": float(dispersion.mean()), "relative_dispersion": ratio}, domain,
    )]
    if target is not None:
        y = pd.Series(target, index=frame.index).astype(float)
        errors = frame.sub(y, axis=0)
        rmse = np.sqrt((errors**2).mean())
        winner = str(rmse.idxmin())
        obs.append(ResearchObservation(
            _identifier("OBS-RANK", winner, *rmse.round(8).tolist()), "model_ranking",
            f"Model ranking can be tested for stability; {winner} has the lowest full-sample RMSE.",
            min(float((rmse.max() - rmse.min()) / max(rmse.mean(), 1e-12)), 1.0), tuple(map(str, frame.columns)),
            {"rmse": rmse.to_dict(), "best_model": winner}, domain,
        ))
    return obs


def scan_robustness_grid(results: pd.DataFrame, metric: str) -> list[ResearchObservation]:
    """Turn sensitivity across specifications into research observations."""
    frame = pd.DataFrame(results).copy()
    if metric not in frame:
        raise KeyError(f"metric {metric!r} not found")
    values = pd.to_numeric(frame[metric], errors="coerce").dropna()
    if len(values) < 3:
        raise ValueError("robustness scan needs at least three specifications")
    mean = float(values.mean())
    std = float(values.std(ddof=1))
    sign_instability = bool((values > 0).any() and (values < 0).any())
    score = min(std / max(abs(mean), 1e-12), 1.0)
    if sign_instability:
        score = max(score, 0.8)
    return [ResearchObservation(
        _identifier("OBS-ROBUST", metric, mean, std), "specification_sensitivity",
        f"{metric} varies materially across tested specifications" + (" and changes sign." if sign_instability else "."),
        score, (metric,),
        {"mean": mean, "std": std, "min": float(values.min()), "max": float(values.max()), "sign_instability": sign_instability},
        "quantitative_finance",
    )]


def _candidate_from_observation(obs: ResearchObservation) -> ResearchCandidate:
    variables = " and ".join(obs.variables) if obs.variables else "the measured process"
    common_risks = (
        "The observation may be sample-specific.",
        "Multiple testing can create false discoveries.",
        "Novelty must be checked against prior literature before publication claims.",
    )
    if obs.kind in {"variance_shift", "rolling_volatility_regime"}:
        title = f"Regime-Dependent Variability of {variables}"
        question = f"Is the variability of {variables} systematically state-dependent rather than constant through time?"
        hypothesis = f"The conditional variability of {variables} changes across identifiable market regimes."
        contribution = "empirical metric / regime diagnostic"
        methods = ("rolling volatility", "change-point tests", "bootstrap", "subperiod stability")
    elif obs.kind == "correlation_break":
        title = f"Relationship Instability: {variables}"
        question = f"When and why does the relationship between {variables} become unstable?"
        hypothesis = f"The dependence structure between {variables} is regime-dependent and changes before or during market transitions."
        contribution = "dependence stability measure"
        methods = ("rolling correlation", "Fisher-z comparison", "change-point detection", "copula/tail dependence robustness")
    elif obs.kind == "curve_regime_transition":
        title = "Yield-Curve Regime Transition Score"
        question = "Can curve-shape dynamics identify transitions between normal, flat and inverted rate regimes before the sign change is complete?"
        hypothesis = "Joint changes in slope, curvature and forward dispersion increase before major yield-curve regime transitions."
        contribution = "new diagnostic score candidate"
        methods = ("level-slope-curvature", "PCA", "change-point detection", "out-of-sample transition classification")
    elif obs.kind == "curve_factor_residual":
        title = "Beyond Three-Factor Yield-Curve Risk"
        question = "When do standard level/slope/curvature factors leave economically meaningful residual curve risk?"
        hypothesis = "Residual curve components become material during stressed or rapidly transitioning rate regimes."
        contribution = "residual factor risk metric"
        methods = ("PCA", "reconstruction error", "regime conditioning", "key-rate DV01 mapping")
    elif obs.kind == "model_disagreement":
        title = "Model Disagreement as Research Signal"
        question = "Does cross-model pricing or forecast disagreement contain information about model risk or subsequent market adjustment?"
        hypothesis = "Periods of elevated cross-model disagreement coincide with higher realized model error or market instability."
        contribution = "model-risk/disagreement index"
        methods = ("model ensemble", "dispersion index", "forecast evaluation", "bootstrap")
    elif obs.kind == "specification_sensitivity":
        title = "Specification-Induced Research Risk"
        question = "How much of the reported result is caused by researcher specification choices rather than the underlying economic effect?"
        hypothesis = "Economically important conclusions are unstable across a reasonable pre-declared specification set."
        contribution = "robustness/stability score"
        methods = ("multiverse analysis", "bootstrap", "false-discovery control", "specification curve")
    elif obs.kind == "tail_asymmetry":
        title = f"Tail-State Behaviour of {variables}"
        question = f"Does the behaviour of {variables} change materially in the tails relative to ordinary market states?"
        hypothesis = f"Tail observations of {variables} are generated by a different conditional distribution or state."
        contribution = "tail-state diagnostic"
        methods = ("EVT diagnostics", "quantile analysis", "Student-t benchmark", "block bootstrap")
    elif obs.kind == "serial_dependence":
        title = f"Conditional Dependence in {variables}"
        question = f"Is the observed serial dependence in {variables} stable, exploitable, or a sampling artefact?"
        hypothesis = f"Lagged values of {variables} contain stable conditional information after controlling for regime and overlapping horizons."
        contribution = "predictability diagnostic"
        methods = ("ACF/PACF", "HAC inference", "walk-forward validation", "placebo lags")
    else:
        title = f"Structural Change in {variables}"
        question = f"Is the observed structural change in {variables} persistent and economically meaningful?"
        hypothesis = f"The distribution of {variables} differs across statistically identifiable states."
        contribution = "empirical research note"
        methods = ("change-point analysis", "bootstrap", "subperiod analysis")
    data_req = tuple(obs.variables) or ("market data corresponding to the observation",)
    return ResearchCandidate(
        candidate_id=_identifier("RC", obs.observation_id, title),
        title=title,
        research_question=question,
        hypothesis=hypothesis,
        domain=obs.domain,
        contribution_type=contribution,
        rationale=obs.description,
        methods=methods,
        data_requirements=data_req,
        falsification_rule="Reject or downgrade the candidate if the effect disappears out of sample, under chronology-safe resampling, or across reasonable alternative specifications.",
        priority_score=float(min(0.45 + 0.55 * obs.score, 1.0)),
        source_observations=(obs.observation_id,),
        risks=common_risks,
        tags=(obs.kind,) + tuple(obs.variables),
        metadata={"observation_evidence": dict(obs.evidence)},
    )


_FIXED_INCOME_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "title": "Curve Reconstruction Risk",
        "question": "How much pricing and risk uncertainty is induced solely by the yield-curve interpolation/reconstruction method?",
        "hypothesis": "Forward rates and derivative sensitivities are materially more sensitive to curve reconstruction choices than zero rates are.",
        "type": "methodological metric",
        "methods": ("log-linear discount interpolation", "zero-rate interpolation", "splines", "forward dispersion", "DV01 propagation"),
        "data": ("zero/discount curve nodes", "representative swaps/options"),
    },
    {
        "title": "Forward-Curve Instability Index",
        "question": "Can local instability of the forward curve quantify rate-regime transitions better than level and slope alone?",
        "hypothesis": "Forward-curve shape instability increases around policy and curve-regime transitions.",
        "type": "new diagnostic index candidate",
        "methods": ("instantaneous forwards", "rolling dispersion", "PCA", "change points"),
        "data": ("historical zero curves", "policy-event dates"),
    },
    {
        "title": "No-Arbitrage Residual Score",
        "question": "Can deviations from internal curve identities be turned into a reproducible data-quality and model-risk score?",
        "hypothesis": "Large no-arbitrage residuals identify data, interpolation or calibration failures before they materially affect pricing.",
        "type": "diagnostic score",
        "methods": ("discount-forward identities", "par repricing", "bootstrap residuals", "threshold calibration"),
        "data": ("market quotes", "bootstrapped curves"),
    },
    {
        "title": "Interpolation-Induced Forward Volatility",
        "question": "Do common curve interpolation methods create artificial time variation in instantaneous forward rates?",
        "hypothesis": "Some interpolation schemes amplify forward-rate volatility without a corresponding change in observed instrument quotes.",
        "type": "model-risk study",
        "methods": ("multi-interpolator reconstruction", "forward derivatives", "variance decomposition"),
        "data": ("daily curve nodes",),
    },
    {
        "title": "Key-Rate Concentration Risk",
        "question": "Can a portfolio with small parallel DV01 still carry concentrated local curve risk?",
        "hypothesis": "Parallel DV01 materially understates risk for portfolios whose key-rate DV01s offset across maturities.",
        "type": "risk metric",
        "methods": ("parallel DV01", "key-rate DV01", "curve scenarios", "PCA shocks"),
        "data": ("portfolio cashflows", "discount curves"),
    },
    {
        "title": "Carry/Roll Robustness Across Curve Regimes",
        "question": "When does static-curve carry and roll-down remain informative after conditioning on curve regime?",
        "hypothesis": "Carry/roll signals have regime-dependent efficacy and fail systematically during rapid repricing states.",
        "type": "relative-value empirical note",
        "methods": ("carry/roll decomposition", "regime labels", "walk-forward tests", "transaction-cost sensitivity"),
        "data": ("historical curves", "bond/swap prices"),
    },
    {
        "title": "Swaption Model Disagreement Map",
        "question": "Where do shifted-Black, normal and smile-adjusted models disagree most on swaption valuation and Greeks?",
        "hypothesis": "Model disagreement is concentrated in low/negative-rate, long-expiry and far-from-ATM regions.",
        "type": "model-risk surface",
        "methods": ("Black-76", "Bachelier", "SABR", "Greek surfaces", "relative pricing error"),
        "data": ("swaption cube", "discount/projection curves"),
    },
    {
        "title": "SABR Parameter Stability Risk",
        "question": "Are calibrated SABR parameters stable enough across strikes, expiries and dates to support reliable risk attribution?",
        "hypothesis": "SABR parameter instability can be economically material even when the cross-sectional smile fit is good.",
        "type": "calibration-risk study",
        "methods": ("rolling SABR calibration", "parameter bootstrap", "out-of-sample smile error"),
        "data": ("cap/floor or swaption volatility smiles",),
    },
    {
        "title": "Caplet Volatility Stripping Uncertainty",
        "question": "How sensitive are stripped caplet volatilities to cap quote noise and interpolation assumptions?",
        "hypothesis": "Sequential caplet-vol stripping amplifies quote noise at selected maturities.",
        "type": "calibration uncertainty metric",
        "methods": ("caplet stripping", "quote perturbation", "bootstrap", "regularization comparison"),
        "data": ("cap prices/vols", "forward/discount curves"),
    },
    {
        "title": "Multi-Curve Basis Stress Indicator",
        "question": "Can changes in tenor-basis term structures identify funding/liquidity stress that is invisible in the OIS curve alone?",
        "hypothesis": "Cross-tenor basis curvature and dispersion increase disproportionately during funding-stress regimes.",
        "type": "basis-risk indicator",
        "methods": ("multi-curve bootstrap", "basis decomposition", "PCA", "change-point analysis"),
        "data": ("OIS quotes", "tenor swap/basis quotes"),
    },
    {
        "title": "Short-Rate Model Risk Envelope",
        "question": "How different are discounting and option-risk conclusions under Vasicek, CIR, Hull-White and Black-Karasinski calibrations?",
        "hypothesis": "Model risk is small for linear instruments but becomes material for convex/option-like exposures and stressed scenarios.",
        "type": "model-risk envelope",
        "methods": ("short-rate calibration", "Monte Carlo", "scenario pricing", "model dispersion"),
        "data": ("short-rate history", "curve", "option quotes"),
    },
    {
        "title": "Three-Factor Residual Curve Risk",
        "question": "When do level, slope and curvature cease to explain enough of curve moves for hedging purposes?",
        "hypothesis": "Residual curve risk rises in stressed regimes and creates hedge errors for portfolios designed only on three PCA factors.",
        "type": "factor-risk study",
        "methods": ("PCA", "hedge reconstruction", "key-rate DV01", "regime conditioning"),
        "data": ("historical yield curves", "portfolio sensitivities"),
    },
)

_GENERAL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "title": "Specification Stability Score",
        "question": "Can the stability of a quantitative conclusion across reasonable specifications be summarized before publication?",
        "hypothesis": "Many apparently strong results weaken materially under a pre-registered multiverse of defensible specifications.",
        "type": "research-governance metric",
        "methods": ("multiverse analysis", "bootstrap", "FDR control", "specification curves"),
        "data": ("experiment outputs across specifications",),
    },
    {
        "title": "Model Disagreement as Uncertainty Proxy",
        "question": "Does disagreement across plausible models predict future forecast/pricing error?",
        "hypothesis": "Cross-model dispersion contains information about realized model error beyond the average model forecast.",
        "type": "model-risk metric",
        "methods": ("ensemble dispersion", "forecast evaluation", "walk-forward testing"),
        "data": ("multiple model predictions", "realized targets"),
    },
    {
        "title": "Data-Revision Sensitivity Index",
        "question": "How much does a research conclusion change when real-time vintages replace revised macroeconomic data?",
        "hypothesis": "Backtests using revised macro data systematically overstate the stability of selected macro signals.",
        "type": "data-risk metric",
        "methods": ("vintage comparison", "signal reconstruction", "performance delta"),
        "data": ("real-time vintages", "revised series", "asset returns"),
    },
)


def catalog(domain: str = "quantitative_finance") -> ResearchBoard:
    """Return built-in starting questions, all explicitly marked NOT_ESTABLISHED."""
    domain_key = domain.lower().replace("-", "_").replace(" ", "_")
    rows = list(_GENERAL_CATALOG)
    if domain_key in {"fixed_income", "interest_rates", "rates", "fixed_income_derivatives"}:
        rows = list(_FIXED_INCOME_CATALOG) + rows
        active_domain = "fixed_income"
    else:
        active_domain = domain_key
    candidates = []
    for idx, item in enumerate(rows, start=1):
        candidates.append(ResearchCandidate(
            candidate_id=f"RC-CATALOG-{idx:03d}", title=item["title"], research_question=item["question"],
            hypothesis=item["hypothesis"], domain=active_domain, contribution_type=item["type"],
            rationale="Built-in ASRQuant research starting point; it must be connected to current data and literature before selection.",
            methods=tuple(item["methods"]), data_requirements=tuple(item["data"]),
            priority_score=max(0.40, 0.72 - idx * 0.01),
            risks=("Novelty is not established.", "The effect may be sample- or convention-specific.", "Pre-register falsification and robustness tests before estimation."),
            tags=("catalog", active_domain),
        ))
    return ResearchBoard(candidates, domain=active_domain)


def from_literature(
    corpus: LiteratureCorpus | HypothesisRegistry | Sequence[str | tuple[str, str]],
    *,
    topic: str | None = None,
    max_candidates: int = 20,
) -> ResearchBoard:
    """Turn ASRQuant's source-linked literature hypotheses/gaps into candidate cards."""
    if isinstance(corpus, HypothesisRegistry):
        registry = corpus
    else:
        active = corpus if isinstance(corpus, LiteratureCorpus) else LiteratureCorpus.from_texts(corpus, topic=topic)
        registry = active.discover_hypotheses(topic=topic, max_candidates=max_candidates)
    candidates: list[ResearchCandidate] = []
    for item in registry.hypotheses[:max_candidates]:
        candidates.append(ResearchCandidate(
            candidate_id="RC-LIT-" + item.hypothesis_id.replace("H-", ""),
            title=item.statement[:96].rstrip(" ."),
            research_question=f"Does the literature-linked candidate hold under a reproducible ASRQuant test: {item.statement}?",
            hypothesis=item.statement,
            domain=topic or "quantitative_finance",
            contribution_type="literature extension / replication / gap test",
            rationale=item.rationale or "Candidate extracted from supplied literature corpus.",
            methods=("source verification", "replication baseline", "extension test", "robustness analysis"),
            data_requirements=("data matching the cited claim",),
            novelty_status=item.novelty_status.upper().replace("-", "_"),
            evidence_status=item.evidence_status.upper(),
            priority_score=float(item.confidence),
            risks=("Corpus-relative novelty is not global novelty.", "Source extraction must be manually checked against the cited pages."),
            tags=tuple(item.tags),
            metadata={"source_count": item.source_count, "evidence": [asdict(e) for e in item.evidence]},
        ))
    return ResearchBoard(sorted(candidates, key=lambda c: c.priority_score, reverse=True), domain=topic or "quantitative_finance")


def weekly(
    *,
    data: pd.DataFrame | Mapping[str, Sequence[float]] | None = None,
    papers: LiteratureCorpus | HypothesisRegistry | Sequence[str | tuple[str, str]] | None = None,
    predictions: pd.DataFrame | Mapping[str, Sequence[float]] | None = None,
    robustness_results: pd.DataFrame | None = None,
    robustness_metric: str | None = None,
    domain: str = "quantitative_finance",
    n: int = 10,
    include_catalog: bool = True,
) -> ResearchBoard:
    """Generate a ranked Friday-to-Friday research-candidate board.

    At least one of ``data``, ``papers``, ``predictions`` or ``include_catalog``
    must provide evidence/starting material.  Candidates generated from the
    built-in catalog remain lower-priority until connected to actual evidence.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    domain_key = domain.lower().replace("-", "_").replace(" ", "_")
    observations: list[ResearchObservation] = []
    candidates: list[ResearchCandidate] = []
    if data is not None:
        if domain_key in {"fixed_income", "interest_rates", "rates", "fixed_income_derivatives"}:
            observations.extend(scan_yield_curve_history(pd.DataFrame(data)))
            domain_key = "fixed_income"
        else:
            observations.extend(scan_market(data, domain=domain_key))
        candidates.extend(_candidate_from_observation(o) for o in observations)
    if predictions is not None:
        model_obs = scan_model_disagreement(predictions, domain=domain_key)
        observations.extend(model_obs)
        candidates.extend(_candidate_from_observation(o) for o in model_obs)
    if robustness_results is not None:
        if robustness_metric is None:
            raise ValueError("robustness_metric is required with robustness_results")
        robust_obs = scan_robustness_grid(robustness_results, robustness_metric)
        observations.extend(robust_obs)
        candidates.extend(_candidate_from_observation(o) for o in robust_obs)
    if papers is not None:
        lit = from_literature(papers, topic=domain_key, max_candidates=max(n, 20))
        candidates.extend(lit.candidates)
    if include_catalog:
        candidates.extend(catalog(domain_key).candidates)
    if not candidates:
        raise ValueError("no research candidates could be generated")

    # Deduplicate near-identical titles while retaining evidence-driven entries.
    seen: set[str] = set()
    unique: list[ResearchCandidate] = []
    for c in sorted(candidates, key=lambda item: (bool(item.source_observations), item.priority_score), reverse=True):
        key = " ".join(c.title.lower().split())
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return ResearchBoard(unique[:n], observations, domain_key)


__all__ = [
    "ResearchObservation", "ResearchCandidate", "ResearchBoard", "scan_market", "scan_yield_curve_history",
    "scan_model_disagreement", "scan_robustness_grid", "catalog", "from_literature", "weekly",
]
