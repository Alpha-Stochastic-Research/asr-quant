"""Portfolio performance attribution helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .contracts import ResultMixin


@dataclass
class FactorAttributionResult(ResultMixin):
    exposures: pd.Series
    contribution: pd.Series
    alpha: float
    residual_volatility: float
    r2: float
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="factor_attribution", init=False)

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "alpha": self.alpha,
                "residual_volatility": self.residual_volatility,
                "r2": self.r2,
                "factors": len(self.exposures),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.concat({"exposure": self.exposures, "mean_contribution": self.contribution}, axis=1)


def factor_attribution(
    portfolio_returns: pd.Series,
    factor_returns: pd.DataFrame,
    *,
    annualization: float = 252.0,
) -> FactorAttributionResult:
    """OLS factor attribution on a common aligned sample."""
    y = pd.Series(portfolio_returns, dtype=float).rename("portfolio")
    x = pd.DataFrame(factor_returns, dtype=float)
    data = pd.concat([y, x], axis=1).dropna()
    if len(data) < x.shape[1] + 3:
        raise ValueError("insufficient observations for factor attribution")
    design = sm.add_constant(data.iloc[:, 1:], has_constant="add")
    fit = sm.OLS(data.iloc[:, 0], design).fit()
    exposures = pd.Series(fit.params.drop("const"), name="exposure")
    mean_contrib = exposures * data.iloc[:, 1:].mean() * annualization
    alpha = float(fit.params["const"] * annualization)
    residual_vol = float(np.std(fit.resid, ddof=1) * np.sqrt(annualization))
    return FactorAttributionResult(
        exposures,
        mean_contrib.rename("mean_contribution"),
        alpha,
        residual_vol,
        float(fit.rsquared),
        metadata={"annualization": annualization, "n_observations": len(data)},
    )


def brinson(
    portfolio_weights: pd.Series,
    benchmark_weights: pd.Series,
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> pd.DataFrame:
    """Single-period Brinson attribution by sector/group.

    Inputs are indexed by the same groups. Returns are decimal group returns.
    """
    pw = pd.Series(portfolio_weights, dtype=float)
    bw = pd.Series(benchmark_weights, dtype=float).reindex(pw.index)
    pr = pd.Series(portfolio_returns, dtype=float).reindex(pw.index)
    br = pd.Series(benchmark_returns, dtype=float).reindex(pw.index)
    frame = pd.concat({"portfolio_weight": pw, "benchmark_weight": bw, "portfolio_return": pr, "benchmark_return": br}, axis=1).dropna()
    if frame.empty:
        raise ValueError("inputs do not align")
    benchmark_total = float((frame["benchmark_weight"] * frame["benchmark_return"]).sum())
    allocation = (frame["portfolio_weight"] - frame["benchmark_weight"]) * (frame["benchmark_return"] - benchmark_total)
    selection = frame["benchmark_weight"] * (frame["portfolio_return"] - frame["benchmark_return"])
    interaction = (frame["portfolio_weight"] - frame["benchmark_weight"]) * (frame["portfolio_return"] - frame["benchmark_return"])
    return pd.DataFrame({"allocation": allocation, "selection": selection, "interaction": interaction, "total": allocation + selection + interaction})


__all__ = ["FactorAttributionResult", "factor_attribution", "brinson"]
