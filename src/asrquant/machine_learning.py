"""Leakage-aware feature engineering and walk-forward machine-learning evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

from .validation import walk_forward_splits


@dataclass
class WalkForwardMLResult:
    estimator_name: str
    task: str
    predictions: pd.Series
    actual: pd.Series
    probabilities: pd.Series | None
    fold_metrics: pd.DataFrame
    aggregate_metrics: pd.Series
    fitted_models: list[Any]

    def plot(self, kind: str = "predictions"):
        from .viz import ml
        if kind == "predictions":
            return ml.prediction_path(self.actual, self.predictions)
        if kind == "residuals":
            return ml.residuals(self.actual, self.predictions)
        if kind == "roc":
            if self.probabilities is None:
                raise ValueError("probabilities are unavailable for this model")
            return ml.roc(self.actual, self.probabilities)
        raise ValueError("kind must be predictions, residuals, or roc")


def resolve_estimator(estimator: Any = "ridge", *, task: str = "regression", model_params: dict[str, Any] | None = None):
    """Resolve an ASRQuant model name or pass through a fitted-compatible estimator."""
    if isinstance(estimator, str):
        from .models import create
        return create(estimator, task=task, **(model_params or {}))
    if model_params:
        raise ValueError("model_params can only be used when estimator is a model name")
    return estimator


def lag_features(
    data: pd.Series | pd.DataFrame,
    lags: int | list[int] = (1, 2, 5, 10, 20),
    *,
    include_current: bool = False,
) -> pd.DataFrame:
    """Create explicitly lagged features without backward filling."""
    frame = pd.DataFrame(data, dtype=float)
    lag_list = list(range(1, lags + 1)) if isinstance(lags, int) else list(lags)
    pieces = []
    if include_current:
        pieces.append(frame.add_suffix("_t"))
    for lag in lag_list:
        if lag <= 0:
            raise ValueError("lags must be positive")
        pieces.append(frame.shift(lag).add_suffix(f"_lag{lag}"))
    return pd.concat(pieces, axis=1)


def technical_features(prices: pd.Series, windows=(5, 20, 63)) -> pd.DataFrame:
    """Generate compact, model-agnostic features from one price series."""
    p = pd.Series(prices, dtype=float).rename("price")
    r = p.pct_change(fill_method=None)
    out = {"return_1": r, "log_return_1": np.log(p).diff()}
    for window in windows:
        out[f"momentum_{window}"] = p.pct_change(window, fill_method=None)
        out[f"volatility_{window}"] = r.rolling(window).std(ddof=1) * np.sqrt(252)
        out[f"zscore_{window}"] = (p - p.rolling(window).mean()) / p.rolling(window).std(ddof=1)
        out[f"drawdown_{window}"] = p / p.rolling(window).max() - 1.0
    delta = p.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0.0, np.nan)
    out["rsi_14"] = 100 - 100 / (1 + rs)
    return pd.DataFrame(out, index=p.index)


def forward_target(prices: pd.Series, horizon: int = 1, classification: bool = False) -> pd.Series:
    """Create a forward return or direction target aligned at decision time."""
    p = pd.Series(prices, dtype=float)
    target = p.shift(-horizon) / p - 1.0
    return (target > 0).astype(float).where(target.notna()).rename("target") if classification else target.rename("target")


def walk_forward_fit(
    estimator: Any = "ridge",
    features: pd.DataFrame | None = None,
    target: pd.Series | None = None,
    *,
    train_size: int,
    test_size: int,
    step: int | None = None,
    gap: int = 0,
    expanding: bool = True,
    task: str = "regression",
    model_params: dict[str, Any] | None = None,
) -> WalkForwardMLResult:
    """Fit fresh estimator clones on chronological train/test splits.

    ``estimator`` may be an ASRQuant model name such as ``"ridge"`` or
    ``"random_forest"``. This keeps scikit-learn internal to ASRQuant.
    """
    if features is None or target is None:
        raise ValueError("features and target are required")
    estimator = resolve_estimator(estimator, task=task, model_params=model_params)
    data = pd.concat([pd.DataFrame(features), pd.Series(target, name="target")], axis=1).dropna()
    x, y = data.iloc[:, :-1], data.iloc[:, -1]
    predictions = pd.Series(index=data.index, dtype=float, name="prediction")
    probabilities = pd.Series(index=data.index, dtype=float, name="probability") if task == "classification" else None
    models: list[Any] = []
    rows = []
    splits = walk_forward_splits(len(data), train_size, test_size, step=step, gap=gap, expanding=expanding)
    if not splits:
        raise ValueError("no walk-forward split can be formed with the requested sizes")
    for fold, split in enumerate(splits):
        model = clone(estimator)
        x_train, y_train = x.iloc[split.train], y.iloc[split.train]
        x_test, y_test = x.iloc[split.test], y.iloc[split.test]
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float)
        predictions.iloc[split.test] = pred
        row = {"fold": fold, "train_n": len(x_train), "test_n": len(x_test)}
        if task == "classification":
            row["accuracy"] = accuracy_score(y_test, pred)
            if hasattr(model, "predict_proba"):
                prob = np.asarray(model.predict_proba(x_test))[:, 1]
                probabilities.iloc[split.test] = prob
                if y_test.nunique() > 1:
                    row["roc_auc"] = roc_auc_score(y_test, prob)
                    row["log_loss"] = log_loss(y_test, prob, labels=[0, 1])
        elif task == "regression":
            row["rmse"] = mean_squared_error(y_test, pred) ** 0.5
            row["mae"] = mean_absolute_error(y_test, pred)
            row["r2"] = r2_score(y_test, pred)
        else:
            raise ValueError("task must be regression or classification")
        rows.append(row)
        models.append(model)
    mask = predictions.notna()
    actual = y.loc[mask]
    pred_clean = predictions.loc[mask]
    if task == "classification":
        aggregate = {"accuracy": accuracy_score(actual, pred_clean)}
        prob_clean = probabilities.loc[mask] if probabilities is not None and probabilities.loc[mask].notna().all() else None
        if prob_clean is not None and actual.nunique() > 1:
            aggregate.update({"roc_auc": roc_auc_score(actual, prob_clean), "log_loss": log_loss(actual, prob_clean, labels=[0, 1])})
    else:
        prob_clean = None
        aggregate = {
            "rmse": mean_squared_error(actual, pred_clean) ** 0.5,
            "mae": mean_absolute_error(actual, pred_clean),
            "r2": r2_score(actual, pred_clean),
        }
    return WalkForwardMLResult(
        estimator_name=type(estimator).__name__,
        task=task,
        predictions=pred_clean,
        actual=actual,
        probabilities=prob_clean,
        fold_metrics=pd.DataFrame(rows).set_index("fold"),
        aggregate_metrics=pd.Series(aggregate),
        fitted_models=models,
    )
