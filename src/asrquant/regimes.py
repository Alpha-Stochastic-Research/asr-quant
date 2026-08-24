"""Regime diagnostics for time-series research."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .contracts import ResultMixin


@dataclass
class RegimeResult(ResultMixin):
    labels: pd.Series
    probabilities: pd.DataFrame | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="regimes", init=False)

    @property
    def summary(self) -> pd.Series:
        counts = self.labels.value_counts(normalize=True).sort_index()
        values: dict[str, Any] = {"observations": len(self.labels), "regimes": self.labels.nunique()}
        values.update({f"share:{k}": float(v) for k, v in counts.items()})
        return pd.Series(values)

    def to_frame(self) -> pd.DataFrame:
        frame = self.labels.rename("regime").to_frame()
        if self.probabilities is not None:
            frame = frame.join(self.probabilities)
        return frame


def volatility_regimes(
    returns: pd.Series,
    *,
    window: int = 63,
    low_quantile: float = 1 / 3,
    high_quantile: float = 2 / 3,
    annualization: float = 252.0,
) -> RegimeResult:
    """Classify rolling realized volatility into low/medium/high regimes."""
    r = pd.Series(returns, dtype=float).dropna()
    if window < 2 or len(r) < window:
        raise ValueError("window must be >=2 and fit inside sample")
    vol = r.rolling(window).std(ddof=1) * np.sqrt(annualization)
    valid = vol.dropna()
    low = float(valid.quantile(low_quantile))
    high = float(valid.quantile(high_quantile))
    labels = pd.Series(index=valid.index, dtype="object", name="regime")
    labels.loc[valid <= low] = "low"
    labels.loc[(valid > low) & (valid < high)] = "medium"
    labels.loc[valid >= high] = "high"
    return RegimeResult(labels, metadata={"window": window, "low_threshold": low, "high_threshold": high})


def mean_shift_score(series: pd.Series, *, window: int = 63) -> pd.Series:
    """Standardized difference between adjacent rolling means."""
    s = pd.Series(series, dtype=float)
    left = s.rolling(window).mean().shift(window)
    right = s.rolling(window).mean()
    pooled = s.rolling(2 * window).std(ddof=1)
    return ((right - left) / pooled.replace(0.0, np.nan)).rename("mean_shift_score")


def structural_break_candidates(series: pd.Series, *, window: int = 63, threshold: float = 2.5) -> pd.DataFrame:
    score = mean_shift_score(series, window=window)
    mask = score.abs() >= threshold
    return pd.DataFrame({"score": score[mask], "direction": np.where(score[mask] > 0, "up", "down")})


def hmm(data: pd.Series | pd.DataFrame, *, n_regimes: int = 2, random_state: int | None = 0, covariance_type: str = "full") -> RegimeResult:
    """Optional Gaussian HMM regime fit using the ``ml`` extra."""
    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError('install ASRQuant with the ML extra: pip install "asrquant[ml]"') from exc
    frame = pd.DataFrame(data, dtype=float).dropna()
    if len(frame) < max(20, n_regimes * 5):
        raise ValueError("insufficient observations for HMM")
    model = GaussianHMM(n_components=n_regimes, covariance_type=covariance_type, random_state=random_state, n_iter=500)
    model.fit(frame.to_numpy())
    labels = pd.Series(model.predict(frame.to_numpy()), index=frame.index, name="regime")
    prob = pd.DataFrame(model.predict_proba(frame.to_numpy()), index=frame.index, columns=[f"regime_{i}_prob" for i in range(n_regimes)])
    return RegimeResult(labels, prob, metadata={"n_regimes": n_regimes, "converged": bool(model.monitor_.converged)})


__all__ = ["RegimeResult", "volatility_regimes", "mean_shift_score", "structural_break_candidates", "hmm"]
