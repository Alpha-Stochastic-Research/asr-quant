"""Regression, factor, and residual diagnostic plots."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from ..statistics import RegressionResult
from .base import finalize, new_axis


def regression_scatter(x, y, result: RegressionResult | None = None, title: str = "Regression fit"):
    x_s = pd.Series(x, dtype=float, name="x")
    y_s = pd.Series(y, dtype=float, name="y")
    data = pd.concat([x_s, y_s], axis=1).dropna().sort_values("x")
    fig, ax = new_axis(title=title)
    ax.scatter(data["x"], data["y"], alpha=0.5)
    if result is not None and len(result.coefficients) >= 2:
        intercept = result.coefficients.iloc[0]
        slope = result.coefficients.iloc[1]
        ax.plot(data["x"], intercept + slope * data["x"], linewidth=2)
    else:
        slope, intercept = np.polyfit(data["x"], data["y"], 1)
        ax.plot(data["x"], intercept + slope * data["x"], linewidth=2)
    return finalize(fig)


def residual_diagnostics(result: RegressionResult):
    resid = result.residuals.dropna()
    fitted = result.fitted.reindex(resid.index)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes[0, 0].scatter(fitted, resid, alpha=0.5)
    axes[0, 0].axhline(0, linewidth=0.8)
    axes[0, 0].set_title("Residuals vs fitted")
    axes[0, 1].hist(resid, bins=35, density=True, alpha=0.6)
    x = np.linspace(resid.min(), resid.max(), 300)
    axes[0, 1].plot(x, stats.norm.pdf(x, resid.mean(), resid.std(ddof=1)))
    axes[0, 1].set_title("Residual distribution")
    stats.probplot(resid, plot=axes[1, 0])
    axes[1, 0].set_title("Normal Q-Q")
    axes[1, 1].plot(resid.index, resid)
    axes[1, 1].axhline(0, linewidth=0.8)
    axes[1, 1].set_title("Residual time path")
    for ax in axes.ravel():
        ax.grid(alpha=0.2)
    return finalize(fig)


def coefficient_intervals(result: RegressionResult, title: str = "Coefficient confidence intervals"):
    ci = result.confidence_intervals.copy()
    coef = result.coefficients.reindex(ci.index)
    errors = np.vstack([coef - ci["lower"], ci["upper"] - coef])
    fig, ax = new_axis(title=title)
    ax.errorbar(coef, np.arange(len(coef)), xerr=errors, fmt="o")
    ax.axvline(0, linewidth=0.8)
    ax.set_yticks(np.arange(len(coef)), coef.index)
    return finalize(fig)


def rolling_coefficients(coefficients: pd.DataFrame, title: str = "Rolling coefficients"):
    fig, ax = new_axis(title=title)
    coefficients.plot(ax=ax)
    ax.axhline(0, linewidth=0.8)
    return finalize(fig)


def factor_exposure_heatmap(exposures: pd.DataFrame, title: str = "Factor exposures"):
    data = pd.DataFrame(exposures, dtype=float)
    fig, ax = plt.subplots(figsize=(10, max(4, len(data) * 0.3)))
    image = ax.imshow(data.T, aspect="auto")
    ax.set_yticks(range(len(data.columns)), data.columns)
    tick_idx = np.linspace(0, len(data) - 1, min(8, len(data))).astype(int)
    ax.set_xticks(tick_idx, [str(data.index[i])[:10] for i in tick_idx], rotation=30)
    ax.set_title(title)
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def actual_vs_fitted(result: RegressionResult):
    actual = result.fitted + result.residuals
    frame = pd.concat([actual.rename("Actual"), result.fitted.rename("Fitted")], axis=1)
    fig, ax = new_axis(title="Actual versus fitted")
    frame.plot(ax=ax)
    return finalize(fig)


def residual_acf(result: RegressionResult, lags: int = 40, title: str = "Residual autocorrelation"):
    """Plot residual autocorrelation with approximate confidence bounds."""
    from statsmodels.tsa.stattools import acf

    resid = result.residuals.dropna()
    values = acf(resid, nlags=min(lags, len(resid) - 1), fft=True)
    bound = 1.96 / np.sqrt(len(resid))
    fig, ax = new_axis(title=title)
    ax.stem(range(len(values)), values, basefmt=" ")
    ax.axhline(bound, linestyle="--", linewidth=0.8)
    ax.axhline(-bound, linestyle="--", linewidth=0.8)
    ax.set_xlabel("Lag")
    ax.set_ylabel("ACF")
    return finalize(fig)


def influence_plot(result: RegressionResult, top: int = 10, title: str = "Regression influence"):
    """Plot leverage against standardized residuals with Cook's distance."""
    influence = result.model.get_influence()
    leverage = np.asarray(influence.hat_matrix_diag)
    standardized = np.asarray(influence.resid_studentized_internal)
    cooks = np.asarray(influence.cooks_distance[0])
    sizes = 30 + 600 * cooks / max(float(np.nanmax(cooks)), 1e-12)
    fig, ax = new_axis(title=title)
    ax.scatter(leverage, standardized, s=sizes, alpha=0.45)
    for idx in np.argsort(cooks)[-min(top, len(cooks)):]:
        ax.annotate(str(result.residuals.index[idx]), (leverage[idx], standardized[idx]), fontsize=8)
    ax.axhline(0, linewidth=0.8)
    ax.set_xlabel("Leverage")
    ax.set_ylabel("Studentized residual")
    return finalize(fig)


def prediction_interval(result: RegressionResult, alpha: float = 0.05, title: str = "Fitted values and prediction interval"):
    """Plot fitted values with a model-based observation interval."""
    summary = result.model.get_prediction().summary_frame(alpha=alpha)
    summary.index = result.fitted.index
    actual = result.fitted + result.residuals
    fig, ax = new_axis(title=title)
    ax.plot(actual.index, actual, label="Actual", alpha=0.65)
    ax.plot(result.fitted.index, result.fitted, label="Fitted")
    lower_name = "obs_ci_lower" if "obs_ci_lower" in summary else "mean_ci_lower"
    upper_name = "obs_ci_upper" if "obs_ci_upper" in summary else "mean_ci_upper"
    ax.fill_between(summary.index, summary[lower_name], summary[upper_name], alpha=0.2, label=f"{1-alpha:.0%} interval")
    ax.legend()
    return finalize(fig)


def partial_residual_plot(result: RegressionResult, variable: str | None = None, title: str | None = None):
    """Display a component-plus-residual diagnostic for one regressor."""
    names = list(result.model.model.exog_names)
    candidates = [name for name in names if name.lower() not in {"const", "intercept"}]
    selected = variable or (candidates[0] if candidates else None)
    if selected is None or selected not in names:
        raise ValueError("a valid non-constant variable is required")
    position = names.index(selected)
    x = np.asarray(result.model.model.exog)[:, position]
    beta = float(result.coefficients[selected])
    component_residual = result.residuals.to_numpy() + beta * x
    fig, ax = new_axis(title=title or f"Partial residual: {selected}")
    ax.scatter(x, component_residual, alpha=0.45)
    ordered = np.argsort(x)
    ax.plot(x[ordered], beta * x[ordered])
    ax.set_xlabel(selected)
    ax.set_ylabel("Component + residual")
    return finalize(fig)
