"""Machine-learning diagnostics designed for financial time series."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from sklearn.metrics import confusion_matrix, roc_curve, auc

from .base import finalize, new_axis


def feature_importance(importances, names=None, top: int = 20, title: str = "Feature importance"):
    values = np.asarray(importances, dtype=float)
    names = np.asarray(names if names is not None else [f"x{i}" for i in range(len(values))])
    order = np.argsort(np.abs(values))[-top:]
    fig, ax = new_axis(title=title)
    ax.barh(names[order], values[order])
    return finalize(fig)


def prediction_path(y_true, y_pred, title: str = "Walk-forward predictions"):
    frame = pd.concat([pd.Series(y_true, name="Actual"), pd.Series(y_pred, name="Predicted")], axis=1).dropna()
    fig, ax = new_axis(title=title)
    frame.plot(ax=ax)
    return finalize(fig)


def residuals(y_true, y_pred, title: str = "Prediction residuals"):
    y = pd.Series(y_true, dtype=float)
    p = pd.Series(y_pred, dtype=float)
    e = y - p
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    ax1.scatter(p, e, alpha=0.5)
    ax1.axhline(0, linewidth=0.8)
    ax1.set_xlabel("Predicted")
    ax1.set_ylabel("Residual")
    ax2.hist(e.dropna(), bins=35)
    ax1.set_title("Residuals vs predictions")
    ax2.set_title("Residual distribution")
    fig.suptitle(title)
    for ax in (ax1, ax2):
        ax.grid(alpha=0.2)
    return finalize(fig)


def roc(y_true, probability, title: str = "ROC curve"):
    fpr, tpr, _ = roc_curve(y_true, probability)
    score = auc(fpr, tpr)
    fig, ax = new_axis(title=title)
    ax.plot(fpr, tpr, label=f"AUC = {score:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.set_xlabel("False-positive rate")
    ax.set_ylabel("True-positive rate")
    ax.legend()
    return finalize(fig)


def confusion(y_true, y_pred, labels=None, normalize: bool = False, title: str = "Confusion matrix"):
    matrix = confusion_matrix(y_true, y_pred, labels=labels, normalize="true" if normalize else None)
    fig, ax = plt.subplots(figsize=(6, 5.5))
    image = ax.imshow(matrix)
    ticks = labels if labels is not None else np.arange(matrix.shape[0])
    ax.set_xticks(range(len(ticks)), ticks)
    ax.set_yticks(range(len(ticks)), ticks)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.2f}" if normalize else str(matrix[i, j]), ha="center", va="center")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def calibration(y_true, probability, bins: int = 10, title: str = "Probability calibration"):
    fraction, mean_prob = calibration_curve(y_true, probability, n_bins=bins)
    fig, ax = new_axis(title=title)
    ax.plot(mean_prob, fraction, marker="o")
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    return finalize(fig)


def regime_probabilities(probabilities: pd.DataFrame, prices: pd.Series | None = None):
    probs = pd.DataFrame(probabilities, dtype=float)
    if prices is None:
        fig, ax = new_axis(title="Regime probabilities")
        probs.plot.area(ax=ax, stacked=True, alpha=0.7)
        return finalize(fig)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    pd.Series(prices).plot(ax=ax1)
    probs.plot.area(ax=ax2, stacked=True, alpha=0.7)
    ax1.set_title("Price and inferred regimes")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.2)
    return finalize(fig)


def precision_recall(y_true, probability, title: str = "Precision-recall curve"):
    from sklearn.metrics import average_precision_score, precision_recall_curve

    y = np.asarray(y_true)
    p = np.asarray(probability, dtype=float)
    precision_values, recall_values, _ = precision_recall_curve(y, p)
    ap = average_precision_score(y, p)
    fig, ax = new_axis(title=title)
    ax.plot(recall_values, precision_values, label=f"AP={ap:.3f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend()
    return finalize(fig)


def learning_curve_plot(train_sizes, train_scores, validation_scores, title: str = "Learning curve"):
    sizes = np.asarray(train_sizes)
    train = np.asarray(train_scores, dtype=float)
    validation = np.asarray(validation_scores, dtype=float)
    train_mean = train.mean(axis=1) if train.ndim == 2 else train
    validation_mean = validation.mean(axis=1) if validation.ndim == 2 else validation
    fig, ax = new_axis(title=title)
    ax.plot(sizes, train_mean, marker="o", label="Training")
    ax.plot(sizes, validation_mean, marker="o", label="Validation")
    ax.set_xlabel("Training observations")
    ax.set_ylabel("Score")
    ax.legend()
    return finalize(fig)


def lift_curve(y_true, probability, bins: int = 10, title: str = "Lift curve"):
    y = pd.Series(y_true, dtype=float).reset_index(drop=True)
    p = pd.Series(probability, dtype=float).reset_index(drop=True)
    data = pd.DataFrame({"y": y, "p": p}).dropna().sort_values("p", ascending=False)
    data["bucket"] = pd.qcut(np.arange(len(data)), q=min(bins, len(data)), labels=False, duplicates="drop")
    base = data["y"].mean()
    lift = data.groupby("bucket")["y"].mean() / base if base != 0 else data.groupby("bucket")["y"].mean() * np.nan
    fig, ax = new_axis(title=title)
    ax.bar(np.arange(1, len(lift) + 1), lift.to_numpy())
    ax.axhline(1, linestyle="--", linewidth=0.8)
    ax.set_xlabel("Score bucket (best first)")
    ax.set_ylabel("Lift")
    return finalize(fig)


def permutation_importance_plot(importances, names=None, top: int = 20, title: str = "Permutation importance"):
    values = np.asarray(importances, dtype=float)
    if values.ndim == 2:
        mean = values.mean(axis=1)
        error = values.std(axis=1, ddof=1)
    else:
        mean = values
        error = None
    labels = np.asarray(names if names is not None else [f"x{i}" for i in range(len(mean))])
    order = np.argsort(mean)[-top:]
    fig, ax = new_axis(title=title)
    ax.barh(labels[order], mean[order], xerr=None if error is None else error[order])
    ax.set_xlabel("Score decrease")
    return finalize(fig)
