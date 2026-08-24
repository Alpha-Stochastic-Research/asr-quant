"""End-to-end research workflow from literature to auditable decisions.

This module connects scientific-paper provenance, economic hypotheses, data and
feature design, signal construction, portfolio backtesting, robustness checks,
decision governance, and paper trading. It is intentionally explicit: automatic
steps create reviewable plans rather than hiding assumptions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from .api import QuantLab
from .audit import AuditResult
from .backtest import BacktestResult, run_backtest
from .config import BacktestSpec, CostModel
from .literature import HypothesisCandidate, HypothesisRegistry, LiteratureCorpus, SourceExcerpt
from .metrics import sharpe_ratio
from .statistics import block_bootstrap
from .trading import PaperTradingResult, RiskPolicy, paper_trade
from .validation import detect_lookahead


@dataclass
class DataRequirement:
    """One variable required to operationalize a hypothesis."""

    name: str
    role: str
    suggested_source: str | None = None
    suggested_symbol: str | None = None
    frequency: str = "daily"
    field: str = "Close"
    availability_lag: int = 0
    point_in_time_required: bool = False
    required: bool = True
    description: str = ""


@dataclass
class DataPlan:
    """Reviewable data specification generated from an economic hypothesis."""

    requirements: list[DataRequirement]
    notes: list[str] = field(default_factory=list)
    hypothesis_id: str | None = None

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(item) for item in self.requirements])

    def validate_columns(self, columns: Iterable[str]) -> pd.DataFrame:
        available = {str(column).lower(): str(column) for column in columns}
        rows = []
        for requirement in self.requirements:
            aliases = [requirement.name, requirement.suggested_symbol or ""]
            matched = next((available[item.lower()] for item in aliases if item and item.lower() in available), None)
            rows.append(
                {
                    "name": requirement.name,
                    "role": requirement.role,
                    "required": requirement.required,
                    "matched_column": matched,
                    "available": matched is not None,
                }
            )
        return pd.DataFrame(rows)

    def download(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        provider_kwargs: Mapping[str, dict[str, Any]] | None = None,
        history_kwargs: Mapping[str, dict[str, Any]] | None = None,
        include_optional: bool = True,
    ) -> pd.DataFrame:
        """Download suggested variables through ASRQuant providers.

        Network access is explicit. Point-in-time and vintage correctness remain
        the researcher's responsibility because standard provider endpoints may
        expose revised rather than historically available values.
        """
        from .providers import get_provider

        provider_options = {str(key).lower(): dict(value) for key, value in (provider_kwargs or {}).items()}
        history_options = {str(key): dict(value) for key, value in (history_kwargs or {}).items()}
        series: dict[str, pd.Series] = {}
        for requirement in self.requirements:
            if not requirement.required and not include_optional:
                continue
            if not requirement.suggested_source or not requirement.suggested_symbol:
                if requirement.required:
                    raise ValueError(f"no provider mapping is available for required variable {requirement.name!r}")
                continue
            provider_name = requirement.suggested_source.lower().replace(" ", "_")
            provider = get_provider(provider_name, **provider_options.get(provider_name, {}))
            kwargs = dict(history_options.get(requirement.name, history_options.get(provider_name, {})))
            if provider_name in {"yahoo", "yfinance"}:
                kwargs.setdefault("start", start)
                kwargs.setdefault("end", end)
                kwargs.setdefault("interval", "1d")
            elif provider_name == "fred":
                kwargs.setdefault("observation_start", start)
                kwargs.setdefault("observation_end", end)
            frame = provider.history(requirement.suggested_symbol, **{k: v for k, v in kwargs.items() if v is not None})
            selected = requirement.field if requirement.field in frame.columns else ("Value" if "Value" in frame.columns else frame.columns[0])
            series[requirement.name] = pd.Series(frame[selected], name=requirement.name)
        if not series:
            raise ValueError("the data plan contains no downloadable provider mappings")
        return pd.concat(series, axis=1).sort_index()


@dataclass
class EconomicHypothesis:
    """Operational research hypothesis with explicit falsification fields."""

    hypothesis_id: str
    statement: str
    predictor: str | None = None
    target: str | None = None
    expected_sign: str | None = None
    horizon: int | str | None = None
    universe: str | None = None
    null: str = "No stable out-of-sample predictive or explanatory relationship."
    mechanism: str = ""
    novelty_status: str = "conceptual"
    evidence_status: str = "unknown"
    confidence: float | None = None
    evidence: list[SourceExcerpt] = field(default_factory=list)
    invalidation_criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_candidate(cls, candidate: HypothesisCandidate, **overrides: Any) -> "EconomicHypothesis":
        payload = {
            "hypothesis_id": candidate.hypothesis_id,
            "statement": candidate.statement,
            "expected_sign": candidate.expected_sign,
            "novelty_status": candidate.novelty_status,
            "evidence_status": candidate.evidence_status,
            "confidence": candidate.confidence,
            "evidence": list(candidate.evidence),
            "metadata": dict(candidate.metadata),
        }
        payload.update(overrides)
        return cls(**payload)

    def design_data(self, overrides: Sequence[DataRequirement] | None = None) -> DataPlan:
        if overrides is not None:
            return DataPlan(list(overrides), hypothesis_id=self.hypothesis_id)
        text = self.statement.lower()
        requirements: list[DataRequirement] = []

        def add(name: str, role: str, source: str, symbol: str, **kwargs: Any) -> None:
            if not any(item.name == name for item in requirements):
                requirements.append(DataRequirement(name, role, source, symbol, **kwargs))

        if any(token in text for token in ("10-year", "10 year", "treasury yield", "bond yield", "interest rate", "rates")):
            add("US10Y", "predictor", "FRED", "DGS10", description="US 10-year Treasury constant-maturity yield")
        if "inflation" in text or "cpi" in text:
            add("CPI", "control", "FRED", "CPIAUCSL", frequency="monthly", availability_lag=1, point_in_time_required=True)
        if "unemployment" in text:
            add("UNEMPLOYMENT", "control", "FRED", "UNRATE", frequency="monthly", availability_lag=1, point_in_time_required=True)
        if "volatility" in text or "vix" in text:
            add("VIX", "control", "Yahoo", "^VIX")
        if "credit" in text or "spread" in text:
            add("CREDIT_SPREAD", "control", "FRED", "BAMLH0A0HYM2")
        if "growth" in text and "value" in text:
            add("GROWTH", "tradable", "Yahoo", "IWF", description="Russell 1000 Growth ETF proxy")
            add("VALUE", "tradable", "Yahoo", "IWD", description="Russell 1000 Value ETF proxy")
        if "market" in text or not any(item.role == "tradable" for item in requirements):
            add("MARKET", "tradable", "Yahoo", "SPY", description="US equity market proxy")
        if self.predictor and not any(item.name == self.predictor for item in requirements):
            requirements.insert(0, DataRequirement(self.predictor, "predictor"))
        if self.target and not any(item.name == self.target for item in requirements):
            requirements.append(DataRequirement(self.target, "target"))
        notes = [
            "Confirm publication timestamps and availability lags before backtesting.",
            "Use point-in-time vintages for revised macroeconomic series whenever the decision date matters.",
            "Proxy tickers are suggestions, not proof that the economic construct is measured correctly.",
        ]
        return DataPlan(requirements, notes, self.hypothesis_id)


@dataclass
class FeatureSpec:
    """One leakage-aware transformation in a feature pipeline."""

    name: str
    source: str | tuple[str, str]
    transform: str = "raw"
    window: int | None = None
    lag: int = 0
    availability_lag: int = 0
    params: dict[str, Any] = field(default_factory=dict)

    def apply(self, data: pd.DataFrame) -> pd.Series:
        transform = self.transform.lower().replace("-", "_")
        if isinstance(self.source, tuple):
            left, right = (pd.Series(data[name], dtype=float) for name in self.source)
            if transform == "ratio":
                output = left / right.replace(0.0, np.nan)
            elif transform == "spread":
                output = left - right
            elif transform == "interaction":
                output = left * right
            else:
                raise ValueError(f"transform {transform!r} requires a single source or is unsupported")
        else:
            source = pd.Series(data[self.source], dtype=float)
            if transform == "raw":
                output = source
            elif transform in {"return", "pct_change"}:
                output = source.pct_change(self.params.get("periods", 1), fill_method=None)
            elif transform == "log_return":
                output = np.log(source).diff(self.params.get("periods", 1))
            elif transform == "diff":
                output = source.diff(self.params.get("periods", self.window or 1))
            elif transform == "momentum":
                output = source.pct_change(self.window or self.params.get("periods", 20), fill_method=None)
            elif transform == "rolling_mean":
                output = source.rolling(self._required_window()).mean()
            elif transform == "rolling_std":
                output = source.rolling(self._required_window()).std(ddof=1)
            elif transform in {"zscore", "z_score"}:
                window = self._required_window()
                mean = source.rolling(window).mean()
                std = source.rolling(window).std(ddof=1).replace(0.0, np.nan)
                output = (source - mean) / std
            elif transform == "ema":
                output = source.ewm(span=self._required_window(), adjust=False).mean()
            elif transform == "rank":
                output = source.rolling(self._required_window()).rank(pct=True)
            elif transform == "lag":
                output = source
            elif transform in {"volatility", "realized_volatility"}:
                window = self._required_window()
                returns = source.pct_change(fill_method=None)
                output = returns.rolling(window).std(ddof=1) * np.sqrt(float(self.params.get("annualization", 252)))
            elif transform == "drawdown":
                wealth = source / source.cummax()
                output = wealth - 1.0
            else:
                raise ValueError(f"unknown feature transform {self.transform!r}")
        total_lag = int(self.lag) + int(self.availability_lag)
        if total_lag:
            output = output.shift(total_lag)
        return pd.Series(output, index=data.index, name=self.name)

    def _required_window(self) -> int:
        if self.window is None or self.window <= 0:
            raise ValueError(f"feature {self.name!r} requires a positive window")
        return int(self.window)


@dataclass
class FeaturePlan:
    specs: list[FeatureSpec]
    notes: list[str] = field(default_factory=list)

    def apply(self, data: pd.DataFrame) -> pd.DataFrame:
        frame = pd.DataFrame(data).sort_index()
        features = pd.concat([spec.apply(frame) for spec in self.specs], axis=1)
        return features.replace([np.inf, -np.inf], np.nan)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(spec) for spec in self.specs])


@dataclass
class SignalSpec:
    """Map one feature into target portfolio weights."""

    feature: str
    method: str = "threshold_pair"
    long_asset: str | None = None
    short_asset: str | None = None
    upper: float = 1.0
    lower: float | None = None
    direction: str = "positive"
    gross: float = 1.0
    signal_lag: int = 1
    neutral_when_inactive: bool = True

    def build(self, features: pd.DataFrame, tradable_assets: Sequence[str]) -> pd.DataFrame:
        if self.feature not in features:
            raise KeyError(f"feature {self.feature!r} is not available")
        assets = list(tradable_assets)
        if not assets:
            raise ValueError("at least one tradable asset is required")
        score = pd.Series(features[self.feature], dtype=float)
        if self.direction.lower() in {"negative", "inverse", "short"}:
            score = -score
        method = self.method.lower().replace("-", "_")
        weights = pd.DataFrame(0.0, index=features.index, columns=assets)
        if method in {"threshold_pair", "pair", "long_short_pair"}:
            if self.long_asset not in assets or self.short_asset not in assets:
                raise ValueError("threshold_pair requires long_asset and short_asset among tradable_assets")
            lower = -self.upper if self.lower is None else float(self.lower)
            positive = score > float(self.upper)
            negative = score < lower
            weights.loc[positive, self.long_asset] = self.gross / 2
            weights.loc[positive, self.short_asset] = -self.gross / 2
            weights.loc[negative, self.long_asset] = -self.gross / 2
            weights.loc[negative, self.short_asset] = self.gross / 2
        elif method in {"threshold_long", "long_only"}:
            asset = self.long_asset or assets[0]
            weights.loc[score >= float(self.upper), asset] = self.gross
        elif method in {"continuous_pair", "scaled_pair"}:
            if self.long_asset not in assets or self.short_asset not in assets:
                raise ValueError("continuous_pair requires long_asset and short_asset")
            scale = score.clip(-abs(self.upper), abs(self.upper)) / max(abs(self.upper), 1e-12)
            weights[self.long_asset] = self.gross * scale / 2
            weights[self.short_asset] = -self.gross * scale / 2
        elif method == "sign":
            if len(assets) != 1:
                raise ValueError("sign signal requires exactly one tradable asset")
            weights[assets[0]] = np.sign(score) * self.gross
        else:
            raise ValueError(f"unknown signal method {self.method!r}")
        if self.signal_lag:
            weights = weights.shift(int(self.signal_lag))
        return weights.fillna(0.0)


@dataclass
class PortfolioSpec:
    gross_leverage: float = 1.0
    max_abs_weight: float = 1.0
    long_only: bool = False
    volatility_target: float | None = None
    volatility_window: int = 20
    max_leverage: float = 2.0

    def apply(self, weights: pd.DataFrame, prices: pd.DataFrame, annualization: int = 252) -> pd.DataFrame:
        output = pd.DataFrame(weights, dtype=float).copy()
        if self.long_only:
            output = output.clip(lower=0.0)
        output = output.clip(lower=-self.max_abs_weight, upper=self.max_abs_weight)
        gross = output.abs().sum(axis=1).replace(0.0, np.nan)
        output = output.mul((self.gross_leverage / gross).clip(upper=1.0).fillna(1.0), axis=0)
        if self.volatility_target is not None:
            returns = pd.DataFrame(prices).pct_change(fill_method=None)
            proxy = (output.shift(1).fillna(0.0) * returns).sum(axis=1)
            realized = proxy.rolling(self.volatility_window).std(ddof=1) * np.sqrt(annualization)
            scale = (self.volatility_target / realized.replace(0.0, np.nan)).clip(upper=self.max_leverage).fillna(0.0)
            output = output.mul(scale, axis=0)
        return output.fillna(0.0)


@dataclass
class HypothesisTestResult:
    """Econometric test of the selected feature against a future target."""

    feature: str
    target_name: str
    horizon: int
    regression: Any
    expected_sign: str | None
    sign_consistent: bool | None
    p_value: float | None

    @property
    def summary(self) -> pd.Series:
        coefficient_names = [name for name in self.regression.coefficients.index if str(name).lower() != "const"]
        coefficient = float(self.regression.coefficients[coefficient_names[0]]) if coefficient_names else np.nan
        return pd.Series({
            "feature": self.feature,
            "target": self.target_name,
            "horizon": self.horizon,
            "coefficient": coefficient,
            "p_value": self.p_value,
            "expected_sign": self.expected_sign,
            "sign_consistent": self.sign_consistent,
            "R2": self.regression.diagnostics.get("R2", np.nan),
        })


@dataclass
class RobustnessResult:
    baseline_metrics: pd.Series
    implementation_audit: AuditResult
    subperiod_metrics: pd.DataFrame
    bootstrap: pd.Series
    leakage_diagnostics: pd.Series
    diagnostics: pd.Series
    parameter_sweep: pd.DataFrame | None = None

    @property
    def summary(self) -> pd.Series:
        return pd.concat(
            {
                "robustness": self.diagnostics,
                "bootstrap": self.bootstrap,
                "implementation": self.implementation_audit.diagnostics,
                "leakage": self.leakage_diagnostics,
            }
        )


@dataclass
class DecisionResult:
    status: str
    score: float
    reasons: list[str]
    risks: list[str]
    required_next_step: str
    evidence: pd.Series
    governance_note: str = (
        "This is a research-governance decision, not personalized investment advice or an instruction to trade live capital."
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready decision payload."""
        return {
            "status": self.status,
            "score": float(self.score),
            "reasons": list(self.reasons),
            "risks": list(self.risks),
            "required_next_step": self.required_next_step,
            "evidence": {str(key): value.item() if hasattr(value, "item") else value for key, value in self.evidence.items()},
            "governance_note": self.governance_note,
        }

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "status": self.status,
                "score": self.score,
                "required_next_step": self.required_next_step,
                "reasons": " | ".join(self.reasons),
                "risks": " | ".join(self.risks),
                "governance_note": self.governance_note,
            }
        )


@dataclass
class ResearchProject:
    """Stateful, reproducible project from papers to a governed decision."""

    name: str
    topic: str | None = None
    corpus: LiteratureCorpus | None = None
    registry: HypothesisRegistry | None = None
    hypothesis: EconomicHypothesis | None = None
    data_plan: DataPlan | None = None
    data: pd.DataFrame | None = None
    tradable_assets: list[str] = field(default_factory=list)
    feature_plan: FeaturePlan | None = None
    features: pd.DataFrame | None = None
    signal_spec: SignalSpec | None = None
    raw_weights: pd.DataFrame | None = None
    portfolio_spec: PortfolioSpec | None = None
    weights: pd.DataFrame | None = None
    backtest_result: BacktestResult | None = None
    hypothesis_test_result: HypothesisTestResult | None = None
    robustness_result: RobustnessResult | None = None
    decision_result: DecisionResult | None = None
    paper_trading_result: PaperTradingResult | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_pdfs(
        cls,
        papers: str | Path | Sequence[str | Path],
        *,
        topic: str | None = None,
        name: str = "ASRQuant research project",
    ) -> "ResearchProject":
        corpus = LiteratureCorpus.from_pdfs(papers, topic=topic)
        project = cls(name=name, topic=topic, corpus=corpus)
        project._record("ingest_papers", papers=len(corpus.papers), corpus_fingerprint=corpus.fingerprint)
        return project

    @classmethod
    def from_hypothesis(
        cls,
        statement: str,
        *,
        name: str = "ASRQuant research project",
        topic: str | None = None,
        **hypothesis_fields: Any,
    ) -> "ResearchProject":
        identifier = "H-" + sha256(statement.encode()).hexdigest()[:8]
        hypothesis = EconomicHypothesis(identifier, statement, **hypothesis_fields)
        project = cls(name=name, topic=topic, hypothesis=hypothesis)
        project.data_plan = hypothesis.design_data()
        project._record("define_hypothesis", hypothesis_id=identifier)
        return project

    @property
    def fingerprint(self) -> str:
        payload = {
            "name": self.name,
            "topic": self.topic,
            "corpus": self.corpus.fingerprint if self.corpus else None,
            "hypothesis": asdict(self.hypothesis) if self.hypothesis else None,
            "feature_plan": [asdict(item) for item in self.feature_plan.specs] if self.feature_plan else None,
            "signal": asdict(self.signal_spec) if self.signal_spec else None,
            "portfolio": asdict(self.portfolio_spec) if self.portfolio_spec else None,
            "backtest": self.backtest_result.fingerprint if self.backtest_result else None,
        }
        return sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def discover_hypotheses(self, **kwargs: Any) -> HypothesisRegistry:
        if self.corpus is None:
            raise RuntimeError("no literature corpus is attached")
        self.registry = self.corpus.discover_hypotheses(topic=self.topic, **kwargs)
        self._record("discover_hypotheses", count=len(self.registry))
        return self.registry

    def select_hypothesis(self, identifier: str | int, **operational_fields: Any) -> EconomicHypothesis:
        if self.registry is None:
            raise RuntimeError("run discover_hypotheses() first")
        candidate = self.registry.select(identifier)
        self.hypothesis = EconomicHypothesis.from_candidate(candidate, **operational_fields)
        self.data_plan = self.hypothesis.design_data()
        self._record("select_hypothesis", hypothesis_id=self.hypothesis.hypothesis_id)
        return self.hypothesis

    def set_hypothesis(self, hypothesis: EconomicHypothesis) -> "ResearchProject":
        self.hypothesis = hypothesis
        self.data_plan = hypothesis.design_data()
        self._record("set_hypothesis", hypothesis_id=hypothesis.hypothesis_id)
        return self

    def plan_data(self, requirements: Sequence[DataRequirement] | None = None) -> DataPlan:
        if self.hypothesis is None:
            raise RuntimeError("define or select a hypothesis first")
        self.data_plan = self.hypothesis.design_data(requirements)
        self._record("plan_data", requirements=len(self.data_plan.requirements))
        return self.data_plan

    def attach_data(
        self,
        data: pd.DataFrame | str | Path,
        *,
        tradable_assets: Sequence[str] | None = None,
        date_column: str | None = None,
        **read_kwargs: Any,
    ) -> "ResearchProject":
        if isinstance(data, (str, Path)):
            source = Path(data)
            suffix = source.suffix.lower()
            if suffix == ".csv":
                frame = pd.read_csv(source, **read_kwargs)
            elif suffix in {".parquet", ".pq"}:
                frame = pd.read_parquet(source, **read_kwargs)
            elif suffix in {".xlsx", ".xls"}:
                frame = pd.read_excel(source, **read_kwargs)
            else:
                raise ValueError(f"unsupported project data format: {suffix}")
            if date_column is not None:
                frame[date_column] = pd.to_datetime(frame[date_column])
                frame = frame.set_index(date_column)
        else:
            frame = pd.DataFrame(data).copy()
        frame = frame.sort_index()
        frame = frame.apply(pd.to_numeric, errors="coerce")
        self.data = frame
        if tradable_assets is None:
            planned = [] if self.data_plan is None else [
                item.name for item in self.data_plan.requirements if item.role == "tradable" and item.name in frame.columns
            ]
            self.tradable_assets = planned or list(frame.columns[: min(2, len(frame.columns))])
        else:
            missing = sorted(set(tradable_assets) - set(frame.columns))
            if missing:
                raise KeyError(f"tradable assets not found in data: {missing}")
            self.tradable_assets = list(tradable_assets)
        self._record("attach_data", rows=len(frame), columns=list(frame.columns), tradable_assets=self.tradable_assets)
        return self

    def fetch_data(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        provider_kwargs: Mapping[str, dict[str, Any]] | None = None,
        history_kwargs: Mapping[str, dict[str, Any]] | None = None,
        tradable_assets: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        """Download the current data plan and attach the resulting panel."""
        if self.data_plan is None:
            self.plan_data()
        frame = self.data_plan.download(
            start=start,
            end=end,
            provider_kwargs=provider_kwargs,
            history_kwargs=history_kwargs,
        )
        planned_tradables = [item.name for item in self.data_plan.requirements if item.role == "tradable"]
        self.attach_data(frame, tradable_assets=tradable_assets or planned_tradables)
        self._record("fetch_data", start=start, end=end)
        return frame

    def recommend_features(self) -> FeaturePlan:
        if self.data is None:
            raise RuntimeError("attach data before requesting feature recommendations")
        text = (self.hypothesis.statement if self.hypothesis else self.topic or "").lower()
        columns = list(self.data.columns)
        predictor = self.hypothesis.predictor if self.hypothesis else None
        if predictor not in columns:
            keywords = ("yield", "rate", "dgs10", "us10y") if any(word in text for word in ("yield", "rate")) else ()
            predictor = next((column for column in columns if any(word in str(column).lower() for word in keywords)), None)
        predictor = predictor or next((column for column in columns if column not in self.tradable_assets), columns[0])
        specs = [
            FeatureSpec(f"{predictor}_diff_5", predictor, "diff", params={"periods": 5}, availability_lag=1),
            FeatureSpec(f"{predictor}_diff_20", predictor, "diff", params={"periods": 20}, availability_lag=1),
            FeatureSpec(f"{predictor}_z_252", predictor, "zscore", window=min(252, max(20, len(self.data) // 3)), availability_lag=1),
        ]
        if len(self.tradable_assets) >= 2:
            specs.append(FeatureSpec("relative_performance_20", (self.tradable_assets[0], self.tradable_assets[1]), "ratio", lag=1))
        self.feature_plan = FeaturePlan(
            specs,
            notes=[
                "Recommended features are starting points and must be justified economically.",
                "Availability lag is applied before signals are formed.",
            ],
        )
        self._record("recommend_features", count=len(specs), predictor=predictor)
        return self.feature_plan

    def build_features(self, plan: FeaturePlan | Sequence[FeatureSpec] | str = "recommended") -> pd.DataFrame:
        if self.data is None:
            raise RuntimeError("attach data before building features")
        if isinstance(plan, str):
            if plan != "recommended":
                raise ValueError("string feature plan must be 'recommended'")
            active = self.recommend_features()
        elif isinstance(plan, FeaturePlan):
            active = plan
        else:
            active = FeaturePlan(list(plan))
        self.feature_plan = active
        self.features = active.apply(self.data)
        self._record("build_features", columns=list(self.features.columns))
        return self.features

    def recommend_signal(self, *, feature: str | None = None) -> SignalSpec:
        """Create a transparent initial signal specification from the hypothesis."""
        if self.features is None:
            raise RuntimeError("build features before requesting a signal recommendation")
        selected_feature = feature or next((name for name in self.features if "z_" in name or "zscore" in name), self.features.columns[0])
        text = (self.hypothesis.statement if self.hypothesis else "").lower()
        if len(self.tradable_assets) >= 2:
            value = next((asset for asset in self.tradable_assets if "value" in asset.lower() or asset.upper() == "IWD"), self.tradable_assets[0])
            growth = next((asset for asset in self.tradable_assets if "growth" in asset.lower() or asset.upper() == "IWF"), self.tradable_assets[1])
            if "growth" in text and "value" in text:
                long_asset, short_asset = value, growth
            else:
                long_asset, short_asset = self.tradable_assets[0], self.tradable_assets[1]
            threshold = 1.0 if ("z_" in selected_feature or "zscore" in selected_feature) else 0.0
            return SignalSpec(
                feature=selected_feature,
                method="threshold_pair",
                long_asset=long_asset,
                short_asset=short_asset,
                upper=threshold,
                lower=-threshold,
                direction=self.hypothesis.expected_sign if self.hypothesis and self.hypothesis.expected_sign in {"positive", "negative"} else "positive",
                signal_lag=1,
            )
        return SignalSpec(selected_feature, method="threshold_long", long_asset=self.tradable_assets[0], upper=0.0, signal_lag=1)

    def build_signal(self, spec: SignalSpec | None = None, **kwargs: Any) -> pd.DataFrame:
        if self.features is None:
            raise RuntimeError("build features before the signal")
        if spec is None:
            if not self.tradable_assets:
                raise RuntimeError("attach tradable assets first")
            if kwargs:
                feature = kwargs.pop("feature", self.features.columns[0])
                if len(self.tradable_assets) >= 2:
                    spec = SignalSpec(
                        feature=feature,
                        long_asset=kwargs.pop("long_asset", self.tradable_assets[0]),
                        short_asset=kwargs.pop("short_asset", self.tradable_assets[1]),
                        **kwargs,
                    )
                else:
                    spec = SignalSpec(feature=feature, method="threshold_long", long_asset=self.tradable_assets[0], **kwargs)
            else:
                spec = self.recommend_signal()
        self.signal_spec = spec
        self.raw_weights = spec.build(self.features, self.tradable_assets)
        self._record("build_signal", signal=asdict(spec))
        return self.raw_weights

    def test_hypothesis(
        self,
        *,
        feature: str | None = None,
        horizon: int | None = None,
        covariance: str = "HAC",
        maxlags: int | None = None,
    ) -> HypothesisTestResult:
        """Regress a future tradable return target on a time-t feature."""
        if self.features is None or self.data is None:
            raise RuntimeError("attach data and build features before testing the hypothesis")
        selected_feature = feature or (self.signal_spec.feature if self.signal_spec else self.features.columns[0])
        if selected_feature not in self.features:
            raise KeyError(f"unknown feature {selected_feature!r}")
        active_horizon = horizon or (self.hypothesis.horizon if self.hypothesis and isinstance(self.hypothesis.horizon, int) else 1)
        active_horizon = int(active_horizon)
        prices = self.data[self.tradable_assets]
        future = prices.pct_change(active_horizon, fill_method=None).shift(-active_horizon)
        if len(self.tradable_assets) >= 2:
            long_asset = self.signal_spec.long_asset if self.signal_spec and self.signal_spec.long_asset else self.tradable_assets[0]
            short_asset = self.signal_spec.short_asset if self.signal_spec and self.signal_spec.short_asset else self.tradable_assets[1]
            target = (future[long_asset] - future[short_asset]).rename(f"future_{long_asset}_minus_{short_asset}")
        else:
            target = future[self.tradable_assets[0]].rename(f"future_{self.tradable_assets[0]}")
        from .statistics import ols
        regression = ols(target, self.features[[selected_feature]], covariance=covariance, maxlags=maxlags)
        coefficient = float(regression.coefficients.get(selected_feature, np.nan))
        expected = self.hypothesis.expected_sign if self.hypothesis else None
        sign_consistent = None if expected not in {"positive", "negative"} else bool(coefficient > 0 if expected == "positive" else coefficient < 0)
        p_value = None
        model_pvalues = getattr(regression.model, "pvalues", None)
        if model_pvalues is not None and selected_feature in model_pvalues:
            p_value = float(model_pvalues[selected_feature])
        self.hypothesis_test_result = HypothesisTestResult(
            selected_feature, target.name, active_horizon, regression, expected, sign_consistent, p_value
        )
        self._record("test_hypothesis", summary=self.hypothesis_test_result.summary.to_dict())
        return self.hypothesis_test_result

    def construct_portfolio(self, spec: PortfolioSpec | None = None, **kwargs: Any) -> pd.DataFrame:
        if self.raw_weights is None or self.data is None:
            raise RuntimeError("build a signal and attach data before portfolio construction")
        self.portfolio_spec = spec or PortfolioSpec(**kwargs)
        prices = self.data[self.tradable_assets]
        self.weights = self.portfolio_spec.apply(self.raw_weights, prices)
        self._record("construct_portfolio", portfolio=asdict(self.portfolio_spec))
        return self.weights

    def backtest(
        self,
        *,
        spec: BacktestSpec | None = None,
        costs_bps: float | None = None,
        execution_delay: int | None = None,
        **spec_updates: Any,
    ) -> BacktestResult:
        if self.data is None:
            raise RuntimeError("attach data before backtesting")
        if self.weights is None:
            if self.raw_weights is None:
                raise RuntimeError("build a signal before backtesting")
            self.construct_portfolio()
        active = spec or BacktestSpec(name=self.name)
        updates = dict(spec_updates)
        if costs_bps is not None:
            current = active.costs
            updates["costs"] = CostModel(
                commission_bps=float(costs_bps),
                spread_bps=current.spread_bps,
                slippage_bps=current.slippage_bps,
                borrow_bps_annual=current.borrow_bps_annual,
                impact_coefficient=current.impact_coefficient,
                impact_exponent=current.impact_exponent,
            )
        if execution_delay is not None:
            updates["execution_delay"] = int(execution_delay)
        if updates:
            active = active.with_updates(**updates)
        self.backtest_result = run_backtest(self.data[self.tradable_assets], self.weights, active)
        self.backtest_result.metadata["research_project_fingerprint"] = self.fingerprint
        self._record("backtest", fingerprint=self.backtest_result.fingerprint, metrics=self.backtest_result.metrics.to_dict())
        return self.backtest_result

    def robustness(
        self,
        *,
        execution_delays: Sequence[int] = (1, 2),
        costs_bps: Sequence[float] = (0.0, 5.0, 10.0, 20.0),
        rebalances: Sequence[str] = ("bar", "W-FRI"),
        n_subperiods: int = 3,
        n_boot: int = 500,
        parameter_sweep: pd.DataFrame | None = None,
    ) -> RobustnessResult:
        if self.backtest_result is None or self.data is None or self.weights is None:
            raise RuntimeError("run a backtest before robustness analysis")
        lab = QuantLab(self.data[self.tradable_assets], missing_data="drop")
        audit = lab.audit(
            self.weights,
            spec=self.backtest_result.spec,
            execution_delays=execution_delays,
            linear_costs_bps=costs_bps,
            rebalances=rebalances,
        )
        index_chunks = [chunk for chunk in np.array_split(np.arange(len(self.data)), n_subperiods) if len(chunk) >= 5]
        rows: list[pd.Series] = []
        for number, positions in enumerate(index_chunks, start=1):
            selected_index = self.data.index[positions]
            result = run_backtest(
                self.data.loc[selected_index, self.tradable_assets],
                self.weights.loc[selected_index, self.tradable_assets],
                self.backtest_result.spec,
            )
            rows.append(result.metrics.rename(f"period_{number}"))
        subperiods = pd.DataFrame(rows)
        bootstrap = block_bootstrap(
            self.backtest_result.net_returns,
            statistic=lambda sample: sharpe_ratio(sample, annualization=self.backtest_result.spec.annualization),
            n_boot=n_boot,
            random_state=7,
        )
        leakage = detect_lookahead(self.raw_weights if self.raw_weights is not None else self.weights, self.data[self.tradable_assets])
        positive_subperiod_ratio = float((subperiods["Total Return"] > 0).mean()) if "Total Return" in subperiods else np.nan
        positive_contract_ratio = float((audit.summary["Total Return"] > 0).mean()) if "Total Return" in audit.summary else np.nan
        diagnostics = pd.Series(
            {
                "positive_subperiod_ratio": positive_subperiod_ratio,
                "positive_contract_ratio": positive_contract_ratio,
                "parameter_stability_available": float(parameter_sweep is not None),
                "bootstrap_sharpe_lower": bootstrap.get("lower", np.nan),
                "implementation_stability": audit.diagnostics.get("conclusion_stability_index", np.nan),
            }
        )
        self.robustness_result = RobustnessResult(
            self.backtest_result.metrics,
            audit,
            subperiods,
            bootstrap,
            leakage,
            diagnostics,
            parameter_sweep,
        )
        self._record("robustness", diagnostics=diagnostics.to_dict())
        return self.robustness_result

    def decide(self) -> DecisionResult:
        if self.backtest_result is None:
            raise RuntimeError("run a backtest before requesting a decision")
        metrics = self.backtest_result.metrics
        robustness = self.robustness_result or self.robustness(n_boot=200)
        sharpe = float(metrics.get("Sharpe", np.nan))
        psr = float(metrics.get("PSR", np.nan))
        total_return = float(metrics.get("Total Return", np.nan))
        max_drawdown = abs(float(metrics.get("Max Drawdown", np.nan)))
        subperiod_ratio = float(robustness.diagnostics.get("positive_subperiod_ratio", 0.0))
        contract_ratio = float(robustness.diagnostics.get("positive_contract_ratio", 0.0))
        bootstrap_lower = float(robustness.bootstrap.get("lower", np.nan))
        same_bar = bool(self.backtest_result.spec.execution_delay == 0)
        sample_size = len(self.backtest_result.net_returns)

        components = {
            "positive_return": float(total_return > 0),
            "sharpe_quality": float(np.clip((sharpe + 0.5) / 2.0, 0, 1)) if np.isfinite(sharpe) else 0.0,
            "probabilistic_sharpe": float(np.clip(psr, 0, 1)) if np.isfinite(psr) else 0.0,
            "subperiod_stability": subperiod_ratio,
            "implementation_resilience": contract_ratio,
            "drawdown_control": float(np.clip(1 - max_drawdown / 0.40, 0, 1)) if np.isfinite(max_drawdown) else 0.0,
            "chronology": 0.0 if same_bar else 1.0,
            "hypothesis_sign": (
                1.0 if self.hypothesis_test_result and self.hypothesis_test_result.sign_consistent is True
                else 0.5 if self.hypothesis_test_result is None or self.hypothesis_test_result.sign_consistent is None
                else 0.0
            ),
        }
        score = float(np.mean(list(components.values())) * 100)
        reasons: list[str] = []
        risks: list[str] = []
        if total_return > 0:
            reasons.append("The baseline net return is positive.")
        else:
            risks.append("The baseline net return is non-positive.")
        if psr >= 0.95:
            reasons.append("The probabilistic Sharpe ratio is at least 95%.")
        elif psr < 0.80:
            risks.append("The probabilistic Sharpe ratio is below 80%.")
        if subperiod_ratio >= 2 / 3:
            reasons.append("Most chronological subperiods are profitable.")
        else:
            risks.append("Performance is not stable across chronological subperiods.")
        if contract_ratio >= 0.75:
            reasons.append("Most tested implementation contracts remain profitable.")
        else:
            risks.append("Results are sensitive to costs, delays, or rebalancing conventions.")
        if same_bar:
            risks.append("Same-bar execution is enabled and may contain look-ahead bias.")
        if sample_size < 252:
            risks.append("The sample contains fewer than 252 observations.")
        if np.isfinite(bootstrap_lower) and bootstrap_lower <= 0:
            risks.append("The lower bootstrap bound for Sharpe is not positive.")
        if self.hypothesis and not self.hypothesis.mechanism:
            risks.append("The economic mechanism has not been documented.")

        if total_return <= 0 or sharpe < 0:
            status, next_step = "REJECT", "Revise or replace the hypothesis before further trading work."
        elif same_bar or sample_size < 126:
            status, next_step = "RESEARCH-ONLY", "Correct chronology or collect a longer sample."
        elif score >= 82 and psr >= 0.95 and contract_ratio >= 0.75 and subperiod_ratio >= 2 / 3:
            status, next_step = "LIMITED-CAPITAL CANDIDATE", "Complete monitored paper trading before any limited-capital deployment."
        elif score >= 65 and psr >= 0.80 and contract_ratio >= 0.50:
            status, next_step = "PAPER-TRADING CANDIDATE", "Run a monitored paper-trading period and compare live-like slippage with the backtest."
        elif score >= 50:
            status, next_step = "REVISE HYPOTHESIS", "Address the weakest robustness dimension and rerun the full protocol."
        else:
            status, next_step = "COLLECT MORE DATA", "Expand the data and validation design before making a deployment decision."
        evidence = pd.Series({**components, "score": score, "Sharpe": sharpe, "PSR": psr, "Total Return": total_return})
        self.decision_result = DecisionResult(status, score, reasons, risks, next_step, evidence)
        self._record("decision", status=status, score=score)
        return self.decision_result

    def paper_trade(
        self,
        *,
        initial_capital: float | None = None,
        commission_bps: float = 0.0,
        slippage_bps: float = 0.0,
        policy: RiskPolicy | None = None,
    ) -> PaperTradingResult:
        if self.data is None or self.weights is None:
            raise RuntimeError("construct portfolio weights before paper trading")
        capital = initial_capital or (
            self.backtest_result.spec.initial_capital if self.backtest_result is not None else 100_000.0
        )
        self.paper_trading_result = paper_trade(
            self.data[self.tradable_assets],
            self.weights,
            initial_capital=capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            policy=policy,
            annualization=self.backtest_result.spec.annualization if self.backtest_result else 252,
        )
        self._record("paper_trade", final_equity=float(self.paper_trading_result.equity.iloc[-1]))
        return self.paper_trading_result

    def run_pipeline(
        self,
        *,
        data: pd.DataFrame | str | Path | None = None,
        tradable_assets: Sequence[str] | None = None,
        feature_plan: FeaturePlan | Sequence[FeatureSpec] | str = "recommended",
        signal_spec: SignalSpec | None = None,
        portfolio_spec: PortfolioSpec | None = None,
        backtest_spec: BacktestSpec | None = None,
        robustness: bool = True,
        decide: bool = True,
    ) -> "ResearchProject":
        if data is not None:
            self.attach_data(data, tradable_assets=tradable_assets)
        if self.data is None:
            raise RuntimeError("run_pipeline requires attached data")
        self.build_features(feature_plan)
        self.build_signal(signal_spec)
        self.test_hypothesis()
        self.construct_portfolio(portfolio_spec)
        self.backtest(spec=backtest_spec)
        if robustness:
            self.robustness()
        if decide:
            self.decide()
        return self

    def manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "topic": self.topic,
            "fingerprint": self.fingerprint,
            "corpus_fingerprint": self.corpus.fingerprint if self.corpus else None,
            "hypothesis": asdict(self.hypothesis) if self.hypothesis else None,
            "data_plan": [asdict(item) for item in self.data_plan.requirements] if self.data_plan else None,
            "tradable_assets": self.tradable_assets,
            "feature_plan": [asdict(item) for item in self.feature_plan.specs] if self.feature_plan else None,
            "signal": asdict(self.signal_spec) if self.signal_spec else None,
            "portfolio": asdict(self.portfolio_spec) if self.portfolio_spec else None,
            "backtest_fingerprint": self.backtest_result.fingerprint if self.backtest_result else None,
            "hypothesis_test": self.hypothesis_test_result.summary.to_dict() if self.hypothesis_test_result else None,
            "decision": self.decision_result.to_dict() if self.decision_result else None,
            "history": self.history,
        }

    def save_manifest(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.manifest(), indent=2, default=str), encoding="utf-8")
        return output

    def report(self, path: str | Path) -> Path:
        """Create a portable HTML research dossier with provenance and decisions."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        hypothesis = self.hypothesis
        decision = self.decision_result
        papers = self.corpus.paper_table().to_html(index=False) if self.corpus else "<p>No paper corpus attached.</p>"
        hypotheses = self.registry.to_frame().to_html(index=False) if self.registry else "<p>No hypothesis registry generated.</p>"
        data_plan = self.data_plan.to_frame().to_html(index=False) if self.data_plan else "<p>No data plan.</p>"
        feature_plan = self.feature_plan.to_frame().to_html(index=False) if self.feature_plan else "<p>No feature plan.</p>"
        hypothesis_test = self.hypothesis_test_result.summary.to_frame("value").to_html() if self.hypothesis_test_result else "<p>No econometric hypothesis test.</p>"
        metrics = self.backtest_result.metrics.to_frame("value").to_html() if self.backtest_result else "<p>No backtest.</p>"
        robustness = self.robustness_result.summary.to_frame("value").to_html() if self.robustness_result else "<p>No robustness analysis.</p>"
        decision_html = decision.summary.to_frame("value").to_html() if decision else "<p>No decision.</p>"
        statement = hypothesis.statement if hypothesis else "No hypothesis selected."
        html = f"""<!doctype html><html><head><meta charset='utf-8'><title>{self.name}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1200px;margin:36px auto;padding:0 24px;color:#17202a}}table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}th,td{{border-bottom:1px solid #ddd;padding:7px;text-align:left;vertical-align:top}}code{{background:#f3f4f6;padding:2px 5px}}.note{{background:#f6f8fa;padding:14px;border-radius:8px}}</style></head><body>
<h1>{self.name}</h1><div class='note'><b>Project fingerprint:</b> <code>{self.fingerprint}</code><br><b>Hypothesis:</b> {statement}</div>
<h2>Paper corpus</h2>{papers}<h2>Hypothesis registry</h2>{hypotheses}<h2>Data plan</h2>{data_plan}
<h2>Feature plan</h2>{feature_plan}<h2>Hypothesis test</h2>{hypothesis_test}<h2>Backtest metrics</h2>{metrics}<h2>Robustness</h2>{robustness}<h2>Decision</h2>{decision_html}
<p><b>Scope:</b> novelty labels are corpus-relative. Decisions are research-governance outputs, not personalized investment advice.</p></body></html>"""
        output.write_text(html, encoding="utf-8")
        self._record("report", path=str(output))
        return output

    def _record(self, action: str, **details: Any) -> None:
        self.history.append({"step": len(self.history) + 1, "action": action, "details": details})


def research_project(
    *,
    papers: str | Path | Sequence[str | Path] | None = None,
    hypothesis: str | EconomicHypothesis | None = None,
    topic: str | None = None,
    name: str = "ASRQuant research project",
) -> ResearchProject:
    """Create a project from papers, a hypothesis, or both."""
    if papers is not None:
        project = ResearchProject.from_pdfs(papers, topic=topic, name=name)
        if isinstance(hypothesis, EconomicHypothesis):
            project.set_hypothesis(hypothesis)
        elif isinstance(hypothesis, str):
            project.set_hypothesis(EconomicHypothesis("H-user", hypothesis))
        return project
    if isinstance(hypothesis, EconomicHypothesis):
        project = ResearchProject(name=name, topic=topic)
        return project.set_hypothesis(hypothesis)
    if isinstance(hypothesis, str):
        return ResearchProject.from_hypothesis(hypothesis, name=name, topic=topic)
    return ResearchProject(name=name, topic=topic)


def autoresearch(
    *,
    hypothesis: str | EconomicHypothesis,
    data: pd.DataFrame | str | Path,
    tradable_assets: Sequence[str],
    topic: str | None = None,
    feature_plan: FeaturePlan | Sequence[FeatureSpec] | str = "recommended",
    signal_spec: SignalSpec | None = None,
    portfolio_spec: PortfolioSpec | None = None,
    backtest_spec: BacktestSpec | None = None,
    name: str = "ASRQuant automatic research project",
) -> ResearchProject:
    """Run the quantitative stages while preserving every generated plan.

    Literature novelty cannot be inferred unless a corpus is supplied separately.
    """
    project = research_project(hypothesis=hypothesis, topic=topic, name=name)
    project.attach_data(data, tradable_assets=tradable_assets)
    return project.run_pipeline(
        feature_plan=feature_plan,
        signal_spec=signal_spec,
        portfolio_spec=portfolio_spec,
        backtest_spec=backtest_spec,
    )


__all__ = [
    "DataRequirement", "DataPlan", "EconomicHypothesis", "FeatureSpec", "FeaturePlan",
    "SignalSpec", "PortfolioSpec", "RobustnessResult", "DecisionResult", "ResearchProject",
    "research_project", "autoresearch",
]
