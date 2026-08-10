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
