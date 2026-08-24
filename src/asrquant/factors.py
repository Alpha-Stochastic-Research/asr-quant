"""Factor research, PCA decomposition, exposures, and portfolio factor risk.

The module is intentionally transparent: inputs and outputs are pandas objects,
regression chronology remains explicit, and no factor is labelled economically
without the researcher's interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .contracts import InputValidationError, ResultMixin
from .statistics import ols


@dataclass
class PCAFactorResult(ResultMixin):
    """Principal-component factor decomposition of a return or curve panel."""

    loadings: pd.DataFrame
    scores: pd.DataFrame
    explained_variance_ratio: pd.Series
    reconstructed: pd.DataFrame
    residuals: pd.DataFrame
    mean: pd.Series
    scale: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="pca_factors", init=False)

    @property
    def summary(self) -> pd.Series:
        cumulative = self.explained_variance_ratio.cumsum()
        out: dict[str, Any] = {
            "n_observations": int(len(self.scores)),
            "n_assets": int(len(self.loadings)),
            "n_components": int(self.loadings.shape[1]),
            "explained_variance": float(self.explained_variance_ratio.sum()),
        }
        for i, value in enumerate(self.explained_variance_ratio, start=1):
            out[f"pc{i}_explained_variance"] = float(value)
            out[f"pc{i}_cumulative_variance"] = float(cumulative.iloc[i - 1])
        out["residual_rmse"] = float(np.sqrt(np.nanmean(np.square(self.residuals.to_numpy()))))
        return pd.Series(out)

    def to_frame(self) -> pd.DataFrame:
        return self.loadings.copy()


@dataclass
class FactorExposureResult(ResultMixin):
    """Multi-asset time-series factor exposures estimated one asset at a time."""

    betas: pd.DataFrame
    alphas: pd.Series
    r_squared: pd.Series
    residuals: pd.DataFrame
    fitted: pd.DataFrame
    covariance: str
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="factor_exposures", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "n_assets": int(self.betas.shape[0]),
                "n_factors": int(self.betas.shape[1]),
                "mean_r_squared": float(self.r_squared.mean()),
                "median_r_squared": float(self.r_squared.median()),
                "mean_abs_alpha": float(self.alphas.abs().mean()),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        out = self.betas.copy()
        out.insert(0, "alpha", self.alphas)
        out["r_squared"] = self.r_squared
        return out


@dataclass
class FactorRiskResult(ResultMixin):
    """Portfolio variance decomposition into factor and specific components."""

    factor_exposure: pd.Series
    factor_variance_contributions: pd.Series
    specific_variance_contributions: pd.Series
    total_variance: float
    factor_variance: float
    specific_variance: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="factor_risk", init=False)

    @property
    def summary(self) -> pd.Series:
        total = max(float(self.total_variance), 0.0)
        return pd.Series(
            {
                "portfolio_volatility": float(np.sqrt(total)),
                "factor_variance": float(self.factor_variance),
                "specific_variance": float(self.specific_variance),
                "factor_share": float(self.factor_variance / total) if total > 0 else np.nan,
                "specific_share": float(self.specific_variance / total) if total > 0 else np.nan,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        factor = self.factor_variance_contributions.rename("variance_contribution").to_frame()
        factor["component"] = "factor"
        specific = self.specific_variance_contributions.rename("variance_contribution").to_frame()
        specific["component"] = "specific"
        return pd.concat([factor, specific], axis=0)


def _numeric_panel(data: pd.DataFrame | pd.Series, *, name: str) -> pd.DataFrame:
    frame = pd.DataFrame(data).copy()
    if isinstance(data, pd.Series):
        frame.columns = [data.name or name]
    if frame.empty or frame.shape[1] == 0:
        raise InputValidationError(f"{name} is empty")
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(how="any")
    if len(frame) < 3:
        raise InputValidationError(f"{name} requires at least three complete observations")
    return frame


def pca(
    data: pd.DataFrame,
    n_components: int = 3,
    *,
    standardize: bool = False,
    component_prefix: str = "PC",
) -> PCAFactorResult:
    """Extract orthogonal statistical factors using principal components.

    ``standardize=False`` is usually appropriate for returns in common units.
    Set ``standardize=True`` when columns have materially different scales and
    the intended analysis is correlation-based rather than covariance-based.
    """
    frame = _numeric_panel(data, name="data")
    if not 1 <= int(n_components) <= min(frame.shape):
        raise InputValidationError("n_components must be between 1 and min(n_observations, n_assets)")

    mean = frame.mean()
    if standardize:
        scaler = StandardScaler(with_mean=True, with_std=True)
        matrix = scaler.fit_transform(frame)
        scale = pd.Series(scaler.scale_, index=frame.columns, name="scale")
        center = pd.Series(scaler.mean_, index=frame.columns, name="mean")
    else:
        center = mean.rename("mean")
        scale = pd.Series(1.0, index=frame.columns, name="scale")
        matrix = frame.to_numpy(dtype=float) - center.to_numpy(dtype=float)

    model = PCA(n_components=int(n_components), svd_solver="full")
    scores_array = model.fit_transform(matrix)
    component_names = [f"{component_prefix}{i}" for i in range(1, int(n_components) + 1)]
    scores = pd.DataFrame(scores_array, index=frame.index, columns=component_names)
    loadings = pd.DataFrame(model.components_.T, index=frame.columns, columns=component_names)
    explained = pd.Series(model.explained_variance_ratio_, index=component_names, name="explained_variance_ratio")
    reconstructed_scaled = model.inverse_transform(scores_array)
    reconstructed = pd.DataFrame(
        reconstructed_scaled * scale.to_numpy() + center.to_numpy(),
        index=frame.index,
        columns=frame.columns,
    )
    residuals = frame - reconstructed
    return PCAFactorResult(
        loadings=loadings,
        scores=scores,
        explained_variance_ratio=explained,
        reconstructed=reconstructed,
        residuals=residuals,
        mean=center,
        scale=scale,
        metadata={"standardized": bool(standardize)},
    )


def exposures(
    asset_returns: pd.Series | pd.DataFrame,
    factor_returns: pd.Series | pd.DataFrame,
    *,
    covariance: str = "HAC",
    maxlags: int | None = None,
) -> FactorExposureResult:
    """Estimate multi-asset factor betas with robust time-series regressions."""
    assets = _numeric_panel(asset_returns, name="asset_returns")
    factors = _numeric_panel(factor_returns, name="factor_returns")
    aligned = assets.join(factors, how="inner", lsuffix="__asset", rsuffix="__factor").dropna()
    if len(aligned) < max(20, factors.shape[1] + 5):
        raise InputValidationError("insufficient aligned observations for factor regressions")
    asset_names = list(assets.columns)
    factor_names = list(factors.columns)
    # Resolve name collisions deterministically by using source frames rather than joined labels.
    common_index = assets.index.intersection(factors.index)
    a = assets.loc[common_index].dropna()
    f = factors.loc[common_index].dropna()
    common_index = a.index.intersection(f.index)
    a, f = a.loc[common_index], f.loc[common_index]

    beta_rows: dict[str, pd.Series] = {}
    alpha: dict[str, float] = {}
    r2: dict[str, float] = {}
    residuals: dict[str, pd.Series] = {}
    fitted_values: dict[str, pd.Series] = {}
    for asset in asset_names:
        result = ols(a[asset], f[factor_names], add_constant=True, covariance=covariance, maxlags=maxlags)
        params = result.coefficients
        alpha[asset] = float(params.get("const", 0.0))
        beta_rows[asset] = params.drop(labels=["const"], errors="ignore").reindex(factor_names)
        r2[asset] = float(result.diagnostics.get("R2", np.nan))
        residuals[asset] = result.residuals
        fitted_values[asset] = result.fitted

    return FactorExposureResult(
        betas=pd.DataFrame(beta_rows).T.reindex(index=asset_names, columns=factor_names),
        alphas=pd.Series(alpha, name="alpha").reindex(asset_names),
        r_squared=pd.Series(r2, name="r_squared").reindex(asset_names),
        residuals=pd.DataFrame(residuals).reindex(columns=asset_names),
        fitted=pd.DataFrame(fitted_values).reindex(columns=asset_names),
        covariance=covariance,
        metadata={"n_observations": int(len(common_index))},
    )


def rolling_beta(
    asset_returns: pd.Series,
    factor_returns: pd.Series,
    *,
    window: int = 63,
) -> pd.Series:
    """Rolling single-factor beta computed as cov(asset, factor) / var(factor)."""
    if window < 3:
        raise InputValidationError("window must be at least 3")
    pair = pd.concat(
        [pd.Series(asset_returns, dtype=float).rename("asset"), pd.Series(factor_returns, dtype=float).rename("factor")],
        axis=1,
    )
    cov = pair["asset"].rolling(window).cov(pair["factor"])
    var = pair["factor"].rolling(window).var(ddof=1).replace(0.0, np.nan)
    return (cov / var).rename("beta")


def risk_decomposition(
    weights: pd.Series | Sequence[float] | np.ndarray,
    betas: pd.DataFrame | np.ndarray,
    factor_covariance: pd.DataFrame | np.ndarray,
    specific_variance: pd.Series | Sequence[float] | np.ndarray,
    *,
    asset_names: Sequence[str] | None = None,
    factor_names: Sequence[str] | None = None,
) -> FactorRiskResult:
    """Decompose portfolio variance under a linear factor risk model.

    The model is ``Sigma = B F B' + D`` where ``D`` is diagonal specific
    variance. Factor variance contributions use the Euler decomposition of
    ``b_p' F b_p`` with portfolio factor exposure ``b_p = B' w``.
    """
    beta = np.asarray(betas, dtype=float)
    if beta.ndim != 2 or beta.size == 0:
        raise InputValidationError("betas must be a non-empty 2D matrix")
    n_assets, n_factors = beta.shape
    w = np.asarray(weights, dtype=float).reshape(-1)
    specific = np.asarray(specific_variance, dtype=float).reshape(-1)
    f_cov = np.asarray(factor_covariance, dtype=float)
    if len(w) != n_assets or len(specific) != n_assets:
        raise InputValidationError("weights and specific_variance must match the number of assets")
    if f_cov.shape != (n_factors, n_factors):
        raise InputValidationError("factor_covariance dimensions must match betas")
    if np.any(specific < 0):
        raise InputValidationError("specific_variance must be non-negative")
    if not np.allclose(f_cov, f_cov.T, atol=1e-10):
        raise InputValidationError("factor_covariance must be symmetric")

    assets = list(asset_names) if asset_names is not None else (
        list(betas.index) if isinstance(betas, pd.DataFrame) else [f"asset_{i}" for i in range(n_assets)]
    )
    factors = list(factor_names) if factor_names is not None else (
        list(betas.columns) if isinstance(betas, pd.DataFrame) else [f"factor_{i}" for i in range(n_factors)]
    )
    if len(assets) != n_assets or len(factors) != n_factors:
        raise InputValidationError("asset_names/factor_names lengths do not match matrix dimensions")

    portfolio_beta = beta.T @ w
    marginal_factor = f_cov @ portfolio_beta
    factor_contrib = portfolio_beta * marginal_factor
    factor_variance = float(portfolio_beta @ f_cov @ portfolio_beta)
    specific_contrib = np.square(w) * specific
    specific_total = float(specific_contrib.sum())
    total = factor_variance + specific_total
    return FactorRiskResult(
        factor_exposure=pd.Series(portfolio_beta, index=factors, name="exposure"),
        factor_variance_contributions=pd.Series(factor_contrib, index=factors, name="factor_variance_contribution"),
        specific_variance_contributions=pd.Series(specific_contrib, index=assets, name="specific_variance_contribution"),
        total_variance=float(total),
        factor_variance=factor_variance,
        specific_variance=specific_total,
    )


__all__ = [
    "PCAFactorResult",
    "FactorExposureResult",
    "FactorRiskResult",
    "pca",
    "exposures",
    "rolling_beta",
    "risk_decomposition",
]
