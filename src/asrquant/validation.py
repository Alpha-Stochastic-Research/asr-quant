"""Time-aware validation, leakage guards, and stress utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Split:
    train: np.ndarray
    test: np.ndarray


def walk_forward_splits(
    n_samples: int,
    train_size: int,
    test_size: int,
    step: int | None = None,
    expanding: bool = True,
    gap: int = 0,
) -> Iterator[Split]:
    """Yield ordered train/test indices with no future observations in training."""
    if min(n_samples, train_size, test_size) <= 0:
        raise ValueError("sizes must be positive")
    if gap < 0:
        raise ValueError("gap must be non-negative")
    step = step or test_size
    train_end = train_size
    while train_end + gap + test_size <= n_samples:
        train_start = 0 if expanding else train_end - train_size
        test_start = train_end + gap
        yield Split(np.arange(train_start, train_end), np.arange(test_start, test_start + test_size))
        train_end += step


def purged_kfold_splits(
    n_samples: int,
    n_splits: int = 5,
    purge: int = 0,
    embargo: int = 0,
) -> Iterator[Split]:
    """Contiguous K-fold splits with observations around each test block removed."""
    if n_splits < 2 or n_splits > n_samples:
        raise ValueError("n_splits must be between 2 and n_samples")
    indices = np.arange(n_samples)
    for test in np.array_split(indices, n_splits):
        left = max(0, int(test[0]) - purge)
        right = min(n_samples, int(test[-1]) + 1 + purge + embargo)
        mask = np.ones(n_samples, dtype=bool)
        mask[left:right] = False
        yield Split(indices[mask], test)


def detect_lookahead(signal: pd.Series | pd.DataFrame, source: pd.Series | pd.DataFrame) -> pd.Series:
    """Heuristic diagnostics for suspicious alignment and future dependence."""
    sig = pd.DataFrame(signal).astype(float)
    src = pd.DataFrame(source).astype(float)
    aligned = sig.reindex(src.index).fillna(0.0)
    future = src.pct_change(fill_method=None).shift(-1)
    same = src.pct_change(fill_method=None)
    sig_scalar = aligned.mean(axis=1)

    def safe_abs_corr(left: pd.Series, right: pd.Series) -> float:
        pair = pd.concat([left, right], axis=1).dropna()
        if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
            return float("nan")
        return float(abs(pair.iloc[:, 0].corr(pair.iloc[:, 1])))

    return pd.Series(
        {
            "signal_starts_before_data": float(sig.index.min() < src.index.min()),
            "same_bar_abs_corr": safe_abs_corr(sig_scalar, same.mean(axis=1)),
            "next_bar_abs_corr": safe_abs_corr(sig_scalar, future.mean(axis=1)),
            "non_monotonic_index": float(not sig.index.is_monotonic_increasing),
        }
    )


def stress_returns(
    returns: pd.Series,
    shocks: dict[str, float],
    windows: dict[str, tuple[pd.Timestamp | str, pd.Timestamp | str]] | None = None,
) -> pd.DataFrame:
    """Apply additive one-period shocks or summarize named historical windows."""
    r = pd.Series(returns, dtype=float).dropna()
    rows: list[dict[str, float | str]] = []
    for name, shock in shocks.items():
        shocked = r.copy()
        shocked.iloc[-1] += shock
        rows.append({"scenario": name, "total_return": (1 + shocked).prod() - 1, "max_loss": shocked.min()})
    if windows:
        for name, (start, end) in windows.items():
            sample = r.loc[pd.Timestamp(start) : pd.Timestamp(end)]
            if len(sample):
                rows.append({"scenario": name, "total_return": (1 + sample).prod() - 1, "max_loss": sample.min()})
    return pd.DataFrame(rows).set_index("scenario") if rows else pd.DataFrame(columns=["total_return", "max_loss"])

# ---------------------------------------------------------------------------
# ASRQuant 1.3 advanced research validation
# ---------------------------------------------------------------------------

from dataclasses import field
from itertools import combinations, product
from typing import Any, Callable, Mapping, Sequence

from .contracts import ResultMixin


def combinatorial_purged_cv_splits(
    n_samples: int,
    n_groups: int = 6,
    n_test_groups: int = 2,
    *,
    purge: int = 0,
    embargo: int = 0,
) -> Iterator[Split]:
    """Yield combinatorial purged cross-validation splits.

    Observations are divided into contiguous groups.  Every combination of
    ``n_test_groups`` is used as test data and observations within ``purge``
    bars around, and ``embargo`` bars after, each test block are removed from
    training.
    """
    if n_samples <= 1:
        raise ValueError("n_samples must exceed one")
    if not 2 <= n_groups <= n_samples:
        raise ValueError("n_groups must be between 2 and n_samples")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError("n_test_groups must be between 1 and n_groups-1")
    if purge < 0 or embargo < 0:
        raise ValueError("purge and embargo must be non-negative")
    groups = [np.asarray(g, dtype=int) for g in np.array_split(np.arange(n_samples), n_groups)]
    all_idx = np.arange(n_samples)
    for selected in combinations(range(n_groups), n_test_groups):
        test = np.sort(np.concatenate([groups[i] for i in selected]))
        mask = np.ones(n_samples, dtype=bool)
        mask[test] = False
        for i in selected:
            block = groups[i]
            left = max(0, int(block[0]) - purge)
            right = min(n_samples, int(block[-1]) + 1 + purge + embargo)
            mask[left:right] = False
        yield Split(all_idx[mask], test)


def _sharpe(values: np.ndarray, annualization: float = 252.0) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan
    sd = float(np.std(x, ddof=1))
    return float(np.sqrt(annualization) * np.mean(x) / sd) if sd > 1e-15 else np.nan


@dataclass
class PBOResult(ResultMixin):
    probability: float
    logits: pd.Series
    selected_strategies: pd.Series
    train_scores: pd.Series
    test_scores: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="probability_of_backtest_overfitting", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "pbo": self.probability,
                "splits": int(len(self.logits)),
                "median_logit": float(self.logits.median()) if len(self.logits) else np.nan,
                "median_train_score": float(self.train_scores.median()) if len(self.train_scores) else np.nan,
                "median_test_score": float(self.test_scores.median()) if len(self.test_scores) else np.nan,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.concat(
            {
                "logit": self.logits,
                "selected_strategy": self.selected_strategies,
                "train_score": self.train_scores,
                "test_score": self.test_scores,
            }, axis=1
        )


def probability_of_backtest_overfitting(
    strategy_returns: pd.DataFrame,
    *,
    n_groups: int = 8,
    annualization: float = 252.0,
) -> PBOResult:
    """Estimate Probability of Backtest Overfitting via CSCV-style rank logits.

    For every half-sample group combination, the strategy with the highest
    in-sample Sharpe is selected and its out-of-sample rank is transformed to a
    logit. PBO is the fraction of logits below zero.
    """
    frame = pd.DataFrame(strategy_returns, dtype=float).dropna(how="any")
    if frame.shape[1] < 2 or len(frame) < max(12, n_groups):
        raise ValueError("PBO requires at least two strategies and enough aligned observations")
    if n_groups % 2 or n_groups < 4:
        raise ValueError("n_groups must be an even integer >= 4")
    groups = [np.asarray(g, dtype=int) for g in np.array_split(np.arange(len(frame)), n_groups)]
    rows = []
    half = n_groups // 2
    for split_id, train_group_ids in enumerate(combinations(range(n_groups), half)):
        train_ids = set(train_group_ids)
        test_group_ids = [i for i in range(n_groups) if i not in train_ids]
        train_idx = np.sort(np.concatenate([groups[i] for i in train_group_ids]))
        test_idx = np.sort(np.concatenate([groups[i] for i in test_group_ids]))
        train_scores = frame.iloc[train_idx].apply(lambda s: _sharpe(s.to_numpy(), annualization))
        test_scores = frame.iloc[test_idx].apply(lambda s: _sharpe(s.to_numpy(), annualization))
        if train_scores.notna().sum() < 2 or test_scores.notna().sum() < 2:
            continue
        selected = str(train_scores.idxmax())
        valid_test = test_scores.dropna().sort_values()
        rank = int(np.where(valid_test.index.to_numpy() == selected)[0][0]) + 1
        n = len(valid_test)
        omega = (rank - 0.5) / n  # worst near 0, best near 1
        logit = float(np.log(omega / (1.0 - omega)))
        rows.append(
            {
                "split": split_id,
                "selected": selected,
                "train": float(train_scores[selected]),
                "test": float(test_scores[selected]),
                "logit": logit,
            }
        )
    if not rows:
        raise ValueError("no valid CSCV split could be evaluated")
    table = pd.DataFrame(rows).set_index("split")
    return PBOResult(
        probability=float((table["logit"] < 0).mean()),
        logits=table["logit"],
        selected_strategies=table["selected"],
        train_scores=table["train"],
        test_scores=table["test"],
        metadata={"n_groups": n_groups, "annualization": annualization, "strategies": list(frame.columns)},
    )


def _moving_block_indices(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, n, size=int(np.ceil(n / block_size)))
    pieces = [(start + np.arange(block_size)) % n for start in starts]
    return np.concatenate(pieces)[:n]


@dataclass
class BootstrapMultipleTestResult(ResultMixin):
    statistic: float
    p_value: float
    observed_by_strategy: pd.Series
    bootstrap_statistics: pd.Series
    method: str
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="bootstrap_multiple_test", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "method": self.method,
                "statistic": self.statistic,
                "p_value": self.p_value,
                "strategies": int(len(self.observed_by_strategy)),
                "bootstrap_samples": int(len(self.bootstrap_statistics)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.observed_by_strategy.rename("observed_statistic").to_frame()


def reality_check(
    strategy_returns: pd.DataFrame,
    benchmark: pd.Series | float = 0.0,
    *,
    n_boot: int = 1000,
    block_size: int | None = None,
    random_state: int | None = 0,
) -> BootstrapMultipleTestResult:
    """White-style Reality Check for the best strategy against a benchmark."""
    frame = pd.DataFrame(strategy_returns, dtype=float)
    if isinstance(benchmark, pd.Series):
        frame = frame.sub(pd.Series(benchmark, dtype=float), axis=0)
    else:
        frame = frame - float(benchmark)
    frame = frame.dropna(how="any")
    if len(frame) < 10 or frame.shape[1] < 1:
        raise ValueError("insufficient aligned observations")
    n = len(frame)
    block_size = int(block_size or max(2, round(n ** (1 / 3))))
    if not 1 <= block_size <= n:
        raise ValueError("block_size must be between 1 and sample length")
    values = frame.to_numpy(dtype=float)
    means = values.mean(axis=0)
    observed_by = pd.Series(np.sqrt(n) * means, index=frame.columns)
    observed = float(observed_by.max())
    centered = values - means
    rng = np.random.default_rng(random_state)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        idx = _moving_block_indices(n, block_size, rng)
        boot[i] = float(np.max(np.sqrt(n) * centered[idx].mean(axis=0)))
    p = float((1.0 + np.sum(boot >= observed)) / (n_boot + 1.0))
    return BootstrapMultipleTestResult(
        observed,
        p,
        observed_by,
        pd.Series(boot, name="bootstrap_max"),
        "reality_check",
        {"block_size": block_size, "random_state": random_state},
    )


def spa_test(
    strategy_returns: pd.DataFrame,
    benchmark: pd.Series | float = 0.0,
    *,
    n_boot: int = 1000,
    block_size: int | None = None,
    random_state: int | None = 0,
) -> BootstrapMultipleTestResult:
    """Studentized Superior Predictive Ability bootstrap test.

    The implementation uses moving-block resampling and studentizes each
    strategy differential before taking the maximum, reducing domination by
    high-variance alternatives.
    """
    frame = pd.DataFrame(strategy_returns, dtype=float)
    if isinstance(benchmark, pd.Series):
        frame = frame.sub(pd.Series(benchmark, dtype=float), axis=0)
    else:
        frame = frame - float(benchmark)
    frame = frame.dropna(how="any")
    n = len(frame)
    if n < 10 or frame.shape[1] < 1:
        raise ValueError("insufficient aligned observations")
    block_size = int(block_size or max(2, round(n ** (1 / 3))))
    values = frame.to_numpy(dtype=float)
    means = values.mean(axis=0)
    std = values.std(axis=0, ddof=1)
    std = np.where(std > 1e-12, std, np.nan)
    observed_each = np.sqrt(n) * means / std
    observed_by = pd.Series(observed_each, index=frame.columns)
    observed = float(np.nanmax(observed_each))
    centered = values - means
    rng = np.random.default_rng(random_state)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        idx = _moving_block_indices(n, block_size, rng)
        sample = centered[idx]
        stat = np.sqrt(n) * sample.mean(axis=0) / std
        boot[i] = float(np.nanmax(stat))
    p = float((1.0 + np.sum(boot >= observed)) / (n_boot + 1.0))
    return BootstrapMultipleTestResult(
        observed,
        p,
        observed_by,
        pd.Series(boot, name="bootstrap_max_studentized"),
        "spa",
        {"block_size": block_size, "random_state": random_state},
    )


@dataclass
class LeakageReport(ResultMixin):
    issues: tuple[str, ...]
    diagnostics: pd.Series
    suspicious_features: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="leakage_report", init=False)

    @property
    def summary(self) -> pd.Series:
        out = self.diagnostics.copy()
        out.loc["issue_count"] = len(self.issues)
        out.loc["suspicious_feature_count"] = len(self.suspicious_features)
        out.loc["passed"] = len(self.issues) == 0
        return out

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({"feature": list(self.suspicious_features)})


def detect_leakage(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    exact_tolerance: float = 1e-12,
    check_future_shifts: int = 5,
) -> LeakageReport:
    """Detect observable leakage patterns without pretending to prove absence.

    The detector checks chronology, duplicates, suspicious column names, exact
    target copies and exact future-target shifts.  It cannot infer how features
    were computed before they reached the function, so a clean report is not a
    proof that a pipeline is leakage-free.
    """
    x = pd.DataFrame(features).copy()
    y = pd.Series(target, name="target")
    issues: list[str] = []
    suspicious: set[str] = set()
    if not x.index.is_monotonic_increasing or not y.index.is_monotonic_increasing:
        issues.append("non-monotonic time index")
    if x.index.has_duplicates or y.index.has_duplicates:
        issues.append("duplicate timestamps")
    tokens = ("future", "forward", "lead", "target", "label", "next_return")
    for col in x.columns:
        if any(token in str(col).lower() for token in tokens):
            suspicious.add(str(col))
    aligned = pd.concat([x, y], axis=1, join="inner").dropna()
    if len(aligned):
        target_values = aligned["target"].to_numpy(dtype=float)
        for col in x.columns:
            if col not in aligned:
                continue
            values = pd.to_numeric(aligned[col], errors="coerce").to_numpy(dtype=float)
            if np.all(np.isfinite(values)) and np.allclose(values, target_values, atol=exact_tolerance, rtol=0):
                suspicious.add(str(col))
                issues.append(f"feature {col!r} is an exact copy of target")
                continue
            s = pd.Series(values, index=aligned.index)
            for lead in range(1, check_future_shifts + 1):
                future = aligned["target"].shift(-lead)
                pair = pd.concat([s, future], axis=1).dropna()
                if len(pair) and np.allclose(pair.iloc[:, 0], pair.iloc[:, 1], atol=exact_tolerance, rtol=0):
                    suspicious.add(str(col))
                    issues.append(f"feature {col!r} exactly matches target shifted {-lead} bars")
                    break
    if suspicious and not any("exact" in issue for issue in issues):
        issues.append("feature names contain potential leakage markers")
    diagnostics = pd.Series(
        {
            "rows_aligned": int(len(aligned)),
            "features": int(x.shape[1]),
            "monotonic_index": bool(x.index.is_monotonic_increasing and y.index.is_monotonic_increasing),
            "duplicate_timestamps": int(x.index.duplicated().sum() + y.index.duplicated().sum()),
        }
    )
    return LeakageReport(tuple(dict.fromkeys(issues)), diagnostics, tuple(sorted(suspicious)))


@dataclass
class MultiverseResult(ResultMixin):
    results: pd.DataFrame
    metric: str
    threshold: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="multiverse", init=False)

    @property
    def summary(self) -> pd.Series:
        values = pd.to_numeric(self.results[self.metric], errors="coerce").dropna()
        return pd.Series(
            {
                "specifications": int(len(self.results)),
                "metric": self.metric,
                "median": float(values.median()) if len(values) else np.nan,
                "minimum": float(values.min()) if len(values) else np.nan,
                "maximum": float(values.max()) if len(values) else np.nan,
                "robust_fraction": float((values > self.threshold).mean()) if len(values) else np.nan,
                "sign_consistency": float(max((values > 0).mean(), (values < 0).mean())) if len(values) else np.nan,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.results.copy()


class Multiverse:
    """Enumerate explicit research choices and evaluate every specification."""

    def __init__(self, choices: Mapping[str, Sequence[Any]], evaluator: Callable[..., Any]) -> None:
        if not choices:
            raise ValueError("choices must not be empty")
        self.choices = {str(k): list(v) for k, v in choices.items()}
        if any(len(v) == 0 for v in self.choices.values()):
            raise ValueError("every choice must contain at least one value")
        self.evaluator = evaluator

    def run(self, *, metric: str = "metric", threshold: float = 0.0) -> MultiverseResult:
        keys = list(self.choices)
        rows: list[dict[str, Any]] = []
        for values in product(*(self.choices[k] for k in keys)):
            config = dict(zip(keys, values))
            evaluated = self.evaluator(**config)
            if isinstance(evaluated, Mapping):
                row = {**config, **dict(evaluated)}
            else:
                row = {**config, metric: float(evaluated)}
            rows.append(row)
        frame = pd.DataFrame(rows)
        if metric not in frame:
            raise ValueError(f"evaluator results do not contain metric {metric!r}")
        return MultiverseResult(frame, metric, float(threshold), metadata={"choices": self.choices})


@dataclass
class StrategyValidationReport(ResultMixin):
    """Consolidated multiple-testing screen for a strategy search.

    The report is deliberately a screening object. ``SCREEN_PASS`` means the
    configured statistical gates passed; it is not a claim of economic validity
    or future profitability.
    """

    pbo: PBOResult
    reality: BootstrapMultipleTestResult
    spa: BootstrapMultipleTestResult
    alpha: float = 0.05
    pbo_threshold: float = 0.50
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="strategy_validation", init=False)

    @property
    def screen_status(self) -> str:
        passed = (
            float(self.pbo.probability) <= self.pbo_threshold
            and float(self.reality.p_value) <= self.alpha
            and float(self.spa.p_value) <= self.alpha
        )
        return "SCREEN_PASS" if passed else "REVIEW_REQUIRED"

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "status": self.screen_status,
                "pbo": float(self.pbo.probability),
                "reality_check_p_value": float(self.reality.p_value),
                "spa_p_value": float(self.spa.p_value),
                "alpha": float(self.alpha),
                "pbo_threshold": float(self.pbo_threshold),
                "strategies": int(len(self.reality.observed_by_strategy)),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.summary.rename("value").to_frame()


def strategy_report(
    strategy_returns: pd.DataFrame,
    *,
    benchmark: pd.Series | float = 0.0,
    n_groups: int = 8,
    n_boot: int = 1000,
    block_size: int | None = None,
    random_state: int | None = 0,
    alpha: float = 0.05,
    pbo_threshold: float = 0.50,
) -> StrategyValidationReport:
    """Run PBO, Reality Check and SPA under one explicit screening contract."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if not 0.0 <= pbo_threshold <= 1.0:
        raise ValueError("pbo_threshold must lie in [0, 1]")
    pbo = probability_of_backtest_overfitting(strategy_returns, n_groups=n_groups)
    reality = reality_check(
        strategy_returns,
        benchmark,
        n_boot=n_boot,
        block_size=block_size,
        random_state=random_state,
    )
    spa = spa_test(
        strategy_returns,
        benchmark,
        n_boot=n_boot,
        block_size=block_size,
        random_state=random_state,
    )
    return StrategyValidationReport(
        pbo,
        reality,
        spa,
        alpha=float(alpha),
        pbo_threshold=float(pbo_threshold),
        metadata={"n_groups": n_groups, "n_boot": n_boot, "block_size": block_size, "random_state": random_state},
    )


def specification_curve(
    choices: Mapping[str, Sequence[Any]],
    evaluator: Callable[..., Any],
    *,
    metric: str = "metric",
    threshold: float = 0.0,
) -> MultiverseResult:
    """Convenience wrapper around :class:`Multiverse` for specification grids."""
    return Multiverse(choices, evaluator).run(metric=metric, threshold=threshold)
