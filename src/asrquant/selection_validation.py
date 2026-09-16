"""Strategy-selection and chronology validation for ASRQuant 1.3.0."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from .validation import Split


@dataclass(frozen=True)
class SelectionTestResult:
    statistic: float
    p_value: float
    details: Mapping[str, Any]

    @property
    def summary(self) -> pd.Series:
        scalar_details = {k: v for k, v in self.details.items() if np.isscalar(v)}
        return pd.Series({"statistic": self.statistic, "p_value": self.p_value, **scalar_details})


def purged_kfold_splits(
    n_samples: int,
    n_splits: int = 5,
    *,
    purge: int = 0,
    embargo: int = 0,
):
    """Yield contiguous purged K-fold splits using the stable ASRQuant Split contract."""
    if n_samples <= 1 or not 2 <= n_splits <= n_samples:
        raise ValueError("require n_samples > 1 and 2 <= n_splits <= n_samples")
    if purge < 0 or embargo < 0:
        raise ValueError("purge and embargo must be non-negative")
    folds = [np.asarray(x, dtype=int) for x in np.array_split(np.arange(n_samples), n_splits)]
    for test in folds:
        lo, hi = int(test[0]), int(test[-1])
        excluded = np.zeros(n_samples, dtype=bool)
        excluded[test] = True
        excluded[max(0, lo - purge) : lo] = True
        excluded[hi + 1 : min(n_samples, hi + 1 + embargo)] = True
        yield Split(np.flatnonzero(~excluded), test)


def combinatorial_purged_cv(
    n_samples: int,
    n_splits: int = 6,
    n_test_splits: int = 2,
    *,
    purge: int = 0,
    embargo: int = 0,
):
    """Yield combinatorial purged train/test splits through the stable Split object."""
    if not 1 <= n_test_splits < n_splits:
        raise ValueError("n_test_splits must be in [1, n_splits)")
    if purge < 0 or embargo < 0:
        raise ValueError("purge and embargo must be non-negative")
    folds = [np.asarray(x, dtype=int) for x in np.array_split(np.arange(n_samples), n_splits)]
    for combo in combinations(range(n_splits), n_test_splits):
        test = np.sort(np.concatenate([folds[i] for i in combo]))
        excluded = np.zeros(n_samples, dtype=bool)
        excluded[test] = True
        for i in combo:
            lo, hi = int(folds[i][0]), int(folds[i][-1])
            excluded[max(0, lo - purge) : lo] = True
            excluded[hi + 1 : min(n_samples, hi + 1 + embargo)] = True
        yield Split(np.flatnonzero(~excluded), test)


def probability_of_backtest_overfitting(
    returns: pd.DataFrame | np.ndarray,
    *,
    n_slices: int = 8,
) -> SelectionTestResult:
    x = np.asarray(returns, dtype=float)
    if x.ndim != 2 or x.shape[1] < 2 or n_slices < 4 or n_slices % 2:
        raise ValueError("returns must be T x N with N>=2 and n_slices even >=4")
    if x.shape[0] < n_slices:
        raise ValueError("not enough observations for n_slices")
    blocks = np.array_split(np.arange(x.shape[0]), n_slices)
    lambdas = []
    half = n_slices // 2
    for ins in combinations(range(n_slices), half):
        ins_set = set(ins)
        oos = [i for i in range(n_slices) if i not in ins_set]
        is_idx = np.concatenate([blocks[i] for i in sorted(ins_set)])
        oos_idx = np.concatenate([blocks[i] for i in oos])
        chosen = int(np.nanargmax(np.nanmean(x[is_idx], axis=0)))
        oos_perf = np.nanmean(x[oos_idx], axis=0)
        order = np.argsort(np.argsort(oos_perf))
        omega = (order[chosen] + 1) / (x.shape[1] + 1)
        lambdas.append(float(np.log(omega / (1.0 - omega))))
    arr = np.asarray(lambdas)
    pbo = float(np.mean(arr <= 0.0))
    return SelectionTestResult(
        pbo,
        pbo,
        {
            "pbo": pbo,
            "n_paths": len(arr),
            "median_logit_rank": float(np.median(arr)),
            "logit_ranks": arr,
        },
    )


def _moving_block_sample(
    x: np.ndarray,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    n = len(x)
    blocks = int(np.ceil(n / block_size))
    starts = rng.integers(0, n, size=blocks)
    idx = np.concatenate([(np.arange(s, s + block_size) % n) for s in starts])[:n]
    return x[idx]


def reality_check(
    returns: pd.DataFrame | np.ndarray,
    *,
    reps: int = 1000,
    block_size: int = 10,
    random_state: int | None = 0,
) -> SelectionTestResult:
    x = np.asarray(returns, dtype=float)
    x = x[:, None] if x.ndim == 1 else x
    if x.ndim != 2 or len(x) < 5 or reps < 100 or block_size < 1:
        raise ValueError("invalid Reality Check inputs")
    means = np.nanmean(x, axis=0)
    observed = float(np.sqrt(len(x)) * max(0.0, np.nanmax(means)))
    centered = x - means
    rng = np.random.default_rng(random_state)
    boot = np.empty(reps)
    for i in range(reps):
        sample = _moving_block_sample(centered, block_size, rng)
        boot[i] = np.sqrt(len(x)) * max(0.0, float(np.nanmax(np.nanmean(sample, axis=0))))
    p_value = float((1 + np.sum(boot >= observed)) / (reps + 1))
    return SelectionTestResult(
        observed,
        p_value,
        {"reps": reps, "block_size": block_size, "n_strategies": x.shape[1]},
    )


def spa_test(
    returns: pd.DataFrame | np.ndarray,
    *,
    reps: int = 1000,
    block_size: int = 10,
    random_state: int | None = 0,
) -> SelectionTestResult:
    x = np.asarray(returns, dtype=float)
    x = x[:, None] if x.ndim == 1 else x
    if x.ndim != 2 or len(x) < 5:
        raise ValueError("returns must be a non-empty T x N matrix")
    n = len(x)
    means = np.nanmean(x, axis=0)
    std = np.nanstd(x, axis=0, ddof=1)
    se = np.where(std > 0, std / np.sqrt(n), np.inf)
    tstats = means / se
    observed = float(max(0.0, np.nanmax(tstats)))
    centered = x - np.maximum(means, 0.0)
    rng = np.random.default_rng(random_state)
    boot = np.empty(reps)
    for i in range(reps):
        sample = _moving_block_sample(centered, block_size, rng)
        bm = np.nanmean(sample, axis=0)
        boot[i] = max(0.0, float(np.nanmax(bm / se)))
    p_value = float((1 + np.sum(boot >= observed)) / (reps + 1))
    return SelectionTestResult(
        observed,
        p_value,
        {"reps": reps, "block_size": block_size, "n_strategies": x.shape[1]},
    )


def leakage_diagnostics(
    features: pd.DataFrame,
    target: pd.Series | None = None,
) -> pd.Series:
    x = pd.DataFrame(features)
    issues = []
    if not x.index.is_monotonic_increasing:
        issues.append("feature_index_not_monotonic")
    if x.index.has_duplicates:
        issues.append("duplicate_feature_index")
    suspicious = [
        str(c)
        for c in x.columns
        if any(token in str(c).lower() for token in ("future", "lead", "t+", "target"))
    ]
    if suspicious:
        issues.append("suspicious_future_named_columns")
    if target is not None:
        y = pd.Series(target)
        if y.index.has_duplicates:
            issues.append("duplicate_target_index")
        if not x.index.equals(y.reindex(x.index).index):
            issues.append("target_index_alignment_issue")
    return pd.Series(
        {
            "ok": not issues,
            "n_issues": len(issues),
            "issues": tuple(issues),
            "suspicious_columns": tuple(suspicious),
        }
    )


def multiverse(
    evaluator: Callable[..., float],
    specifications: Mapping[str, Sequence[Any]],
) -> pd.DataFrame:
    keys = list(specifications)
    rows = []
    for values in product(*(specifications[k] for k in keys)):
        spec = dict(zip(keys, values))
        rows.append({**spec, "result": float(evaluator(**spec))})
    frame = pd.DataFrame(rows)
    if len(frame):
        frame["rank_pct"] = frame["result"].rank(pct=True)
    return frame


__all__ = [
    "SelectionTestResult",
    "purged_kfold_splits",
    "combinatorial_purged_cv",
    "probability_of_backtest_overfitting",
    "reality_check",
    "spa_test",
    "leakage_diagnostics",
    "multiverse",
]
