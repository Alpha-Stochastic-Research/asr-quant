"""Finite-sample diagnostics for martingale and discounted-martingale hypotheses."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox


@dataclass
class MartingaleResult:
    """Diagnostics that can reject, but never prove, a martingale hypothesis."""

    increments: pd.Series
    statistics: pd.Series
    regression: object

    @property
    def conclusion(self) -> str:
        p_values = self.statistics.filter(like="p-value").dropna()
        return "not rejected" if len(p_values) and bool((p_values >= 0.05).all()) else "diagnostic rejection"

    def plot(self):
        from .viz.simulation import martingale_diagnostics_plot
        return martingale_diagnostics_plot(self)


def discount_process(values: pd.Series, rate: float = 0.0, annualization: int = 252) -> pd.Series:
    """Discount a value process by a continuously compounded constant rate."""
    s = pd.Series(values, dtype=float).dropna()
    t = np.arange(len(s), dtype=float) / annualization
    return pd.Series(s.to_numpy() * np.exp(-rate * t), index=s.index, name="discounted_value")


def martingale_diagnostics(
    values: pd.Series,
    *,
    rate: float = 0.0,
    annualization: int = 252,
    lags: int = 10,
) -> MartingaleResult:
    """Run mean-increment, predictability, and serial-correlation diagnostics.

    Under the tested null, discounted increments have zero unconditional mean,
    cannot be linearly predicted by the lagged process level, and are not
    serially correlated at the selected horizon. Passing these tests does not
    establish the full conditional-expectation definition of a martingale.
    """
    discounted = discount_process(values, rate=rate, annualization=annualization)
    increments = discounted.diff().dropna().rename("increment")
    if len(increments) < max(20, lags + 3):
        raise ValueError("at least 20 usable increments are required")
    t_stat, mean_p = stats.ttest_1samp(increments, 0.0)
    lagged_level = discounted.shift(1).reindex(increments.index)
    x = sm.add_constant(lagged_level.rename("lagged_level"), has_constant="add")
    regression = sm.OLS(increments, x).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, lags)})
    lb_lag = min(lags, max(1, len(increments) // 5))
    lb = acorr_ljungbox(increments, lags=[lb_lag], return_df=True).iloc[0]
    stats_out = pd.Series(
        {
            "mean increment": increments.mean(),
            "mean increment t-statistic": float(t_stat),
            "mean increment p-value": float(mean_p),
            "lagged-level coefficient": float(regression.params["lagged_level"]),
            "lagged-level p-value": float(regression.pvalues["lagged_level"]),
            "Ljung-Box statistic": float(lb["lb_stat"]),
            "Ljung-Box p-value": float(lb["lb_pvalue"]),
            "increment volatility": float(increments.std(ddof=1)),
        }
    )
    return MartingaleResult(increments=increments, statistics=stats_out, regression=regression)
