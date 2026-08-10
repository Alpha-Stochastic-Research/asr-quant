"""Regression, time-series tests, bootstrap inference, and factor analysis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan, het_white
from statsmodels.tsa.stattools import adfuller, kpss


@dataclass
class RegressionResult:
    """Aligned regression outputs with compact plotting helpers."""

    model: object
    coefficients: pd.Series
    confidence_intervals: pd.DataFrame
    fitted: pd.Series
    residuals: pd.Series
    diagnostics: pd.Series

    @property
    def summary(self) -> pd.Series:
        values = {f"coefficient:{name}": value for name, value in self.coefficients.items()}
        values.update({f"diagnostic:{name}": value for name, value in self.diagnostics.items()})
        return pd.Series(values)

    def plot(self, kind: str = "residuals"):
        from .viz import regression as viz

        if kind in {"residuals", "diagnostics"}:
            return viz.residual_diagnostics(self)
        if kind in {"coefficients", "intervals"}:
            return viz.coefficient_intervals(self)
        if kind in {"fitted", "actual_vs_fitted"}:
            return viz.actual_vs_fitted(self)
        raise ValueError("kind must be residuals, coefficients, or fitted")


def ols(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    add_constant: bool = True,
    covariance: str = "HAC",
    maxlags: int | None = None,
) -> RegressionResult:
    """OLS with classical, HC, or Newey-West/HAC covariance."""
    y = pd.Series(y, dtype=float).rename("y")
    x = pd.DataFrame(x, dtype=float)
    data = pd.concat([y, x], axis=1).dropna()
    y_clean = data.iloc[:, 0]
    x_clean = data.iloc[:, 1:]
    if add_constant:
        x_clean = sm.add_constant(x_clean, has_constant="add")
    model = sm.OLS(y_clean, x_clean)
    cov_upper = covariance.upper()
    if cov_upper == "HAC":
        lag = maxlags if maxlags is not None else max(1, int(len(data) ** 0.25))
        fitted = model.fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    elif cov_upper in {"HC0", "HC1", "HC2", "HC3"}:
        fitted = model.fit(cov_type=cov_upper)
    elif cov_upper in {"NONROBUST", "CLASSICAL"}:
        fitted = model.fit()
    else:
        raise ValueError("covariance must be HAC, HC0-HC3, or nonrobust")
    residuals = pd.Series(fitted.resid, index=data.index, name="residual")
    diagnostics = pd.Series(
        {
            "R2": fitted.rsquared,
            "Adjusted R2": fitted.rsquared_adj,
            "Durbin-Watson": sm.stats.stattools.durbin_watson(residuals),
            "Jarque-Bera p": sm.stats.stattools.jarque_bera(residuals)[1],
            "Ljung-Box p": float(acorr_ljungbox(residuals, lags=[min(10, max(1, len(residuals)//5))], return_df=True)["lb_pvalue"].iloc[0]),
            "Breusch-Pagan p": het_breuschpagan(residuals, fitted.model.exog)[1],
            "White p": het_white(residuals, fitted.model.exog)[1] if fitted.model.exog.shape[1] > 1 else np.nan,
        }
    )
    return RegressionResult(
        model=fitted,
        coefficients=pd.Series(fitted.params),
        confidence_intervals=fitted.conf_int().set_axis(["lower", "upper"], axis=1),
        fitted=pd.Series(fitted.fittedvalues, index=data.index, name="fitted"),
        residuals=residuals,
        diagnostics=diagnostics,
    )


def rolling_regression(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    window: int = 63,
    add_constant: bool = True,
) -> pd.DataFrame:
    """Rolling least-squares coefficients."""
    y = pd.Series(y, dtype=float).rename("y")
    x = pd.DataFrame(x, dtype=float)
    data = pd.concat([y, x], axis=1).dropna()
    x_clean = data.iloc[:, 1:]
    if add_constant:
        x_clean = sm.add_constant(x_clean, has_constant="add")
    model = RollingOLS(data.iloc[:, 0], x_clean, window=window)
    return model.fit().params


def stationarity_tests(series: pd.Series) -> pd.Series:
    """ADF and KPSS tests reported together to reduce one-test overinterpretation."""
    s = pd.Series(series, dtype=float).dropna()
    adf = adfuller(s, autolag="AIC")
    try:
        kpss_result = kpss(s, regression="c", nlags="auto")
        kpss_stat, kpss_p = kpss_result[0], kpss_result[1]
    except ValueError:
        kpss_stat, kpss_p = np.nan, np.nan
    return pd.Series(
        {
            "ADF statistic": adf[0],
            "ADF p-value": adf[1],
            "KPSS statistic": kpss_stat,
            "KPSS p-value": kpss_p,
        }
    )


def block_bootstrap(
    series: pd.Series,
    statistic: Callable[[pd.Series], float] = np.mean,
    n_boot: int = 1_000,
    block_size: int | None = None,
    confidence: float = 0.95,
    random_state: int | None = 0,
) -> pd.Series:
    """Moving-block bootstrap confidence interval for dependent data."""
    s = pd.Series(series, dtype=float).dropna().reset_index(drop=True)
    n = len(s)
    if n < 2:
        raise ValueError("at least two observations are required")
    block_size = block_size or max(2, int(round(n ** (1 / 3))))
    if not 1 <= block_size <= n:
        raise ValueError("block_size must be between 1 and sample length")
    rng = np.random.default_rng(random_state)
    starts = np.arange(0, n - block_size + 1)
    estimates = np.empty(n_boot)
    for i in range(n_boot):
        chunks: list[np.ndarray] = []
        while sum(len(c) for c in chunks) < n:
            start = int(rng.choice(starts))
            chunks.append(s.iloc[start : start + block_size].to_numpy())
        sample = pd.Series(np.concatenate(chunks)[:n])
        estimates[i] = statistic(sample)
    alpha = 1 - confidence
    return pd.Series(
        {
            "estimate": float(statistic(s)),
            "lower": float(np.quantile(estimates, alpha / 2)),
            "upper": float(np.quantile(estimates, 1 - alpha / 2)),
            "bootstrap_std": float(np.std(estimates, ddof=1)),
        }
    )


def permutation_test(
    x: pd.Series,
    y: pd.Series,
    statistic: Callable[[np.ndarray, np.ndarray], float] | None = None,
    n_permutations: int = 5_000,
    random_state: int | None = 0,
) -> pd.Series:
    """Two-sided permutation test for a difference in means by default."""
    x = pd.Series(x, dtype=float).dropna().to_numpy()
    y = pd.Series(y, dtype=float).dropna().to_numpy()
    statistic = statistic or (lambda a, b: float(np.mean(a) - np.mean(b)))
    observed = statistic(x, y)
    pooled = np.concatenate([x, y])
    rng = np.random.default_rng(random_state)
    count = 0
    for _ in range(n_permutations):
        shuffled = rng.permutation(pooled)
        value = statistic(shuffled[: len(x)], shuffled[len(x) :])
        count += abs(value) >= abs(observed)
    return pd.Series({"statistic": observed, "p_value": (count + 1) / (n_permutations + 1)})


def benjamini_hochberg(p_values: Iterable[float], alpha: float = 0.05) -> pd.DataFrame:
    """Benjamini-Hochberg false-discovery-rate correction."""
    p = np.asarray(list(p_values), dtype=float)
    if np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must lie in [0, 1]")
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adjusted_ranked = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    adjusted = np.empty(n)
    adjusted[order] = np.clip(adjusted_ranked, 0, 1)
    return pd.DataFrame({"p_value": p, "adjusted_p": adjusted, "reject": adjusted <= alpha})


def quantile_regression(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    quantile: float = 0.5,
    add_constant: bool = True,
) -> RegressionResult:
    """Linear quantile regression for conditional-tail relationships."""
    if not 0 < quantile < 1:
        raise ValueError("quantile must lie in (0, 1)")
    y_s = pd.Series(y, dtype=float).rename("y"); x_f = pd.DataFrame(x, dtype=float)
    data = pd.concat([y_s, x_f], axis=1).dropna(); y_c = data.iloc[:, 0]; x_c = data.iloc[:, 1:]
    if add_constant:
        x_c = sm.add_constant(x_c, has_constant="add")
    fitted = sm.QuantReg(y_c, x_c).fit(q=quantile)
    residuals = pd.Series(y_c - fitted.fittedvalues, index=data.index, name="residual")
    return RegressionResult(
        model=fitted,
        coefficients=pd.Series(fitted.params),
        confidence_intervals=fitted.conf_int().set_axis(["lower", "upper"], axis=1),
        fitted=pd.Series(fitted.fittedvalues, index=data.index, name="fitted"),
        residuals=residuals,
        diagnostics=pd.Series({"Pseudo R2": getattr(fitted, "prsquared", np.nan), "quantile": quantile}),
    )


def polynomial_regression(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    degree: int = 2,
    covariance: str = "HAC",
    maxlags: int | None = None,
) -> RegressionResult:
    """Polynomial least-squares regression with named transformed features."""
    if degree < 1:
        raise ValueError("degree must be at least 1")
    from sklearn.preprocessing import PolynomialFeatures
    x_f = pd.DataFrame(x, dtype=float)
    transformer = PolynomialFeatures(degree=degree, include_bias=False)
    values = transformer.fit_transform(x_f)
    transformed = pd.DataFrame(values, index=x_f.index, columns=transformer.get_feature_names_out(x_f.columns.astype(str)))
    result = ols(y, transformed, add_constant=True, covariance=covariance, maxlags=maxlags)
    result.model.asrquant_transformer = transformer
    return result


def regularized_regression(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    method: str = "ridge",
    alpha: float = 1.0,
    l1_ratio: float = 0.5,
    standardize: bool = True,
):
    """Fit Ridge, Lasso, or Elastic Net in a scikit-learn pipeline."""
    from sklearn.linear_model import ElasticNet, Lasso, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    x_f = pd.DataFrame(x, dtype=float); y_s = pd.Series(y, dtype=float).rename("y")
    data = pd.concat([y_s, x_f], axis=1).dropna(); y_c = data.iloc[:, 0]; x_c = data.iloc[:, 1:]
    key = method.lower().replace("-", "_")
    if key == "ridge":
        estimator = Ridge(alpha=alpha)
    elif key == "lasso":
        estimator = Lasso(alpha=alpha, max_iter=20_000)
    elif key in {"elastic_net", "elasticnet"}:
        estimator = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=20_000)
    else:
        raise ValueError("method must be ridge, lasso, or elastic_net")
    model = make_pipeline(StandardScaler(), estimator) if standardize else estimator
    model.fit(x_c, y_c)
    fitted = pd.Series(model.predict(x_c), index=data.index, name="fitted")
    residuals = (y_c - fitted).rename("residual")
    return {"model": model, "fitted": fitted, "residuals": residuals, "r2": float(model.score(x_c, y_c)), "features": list(x_c.columns)}


def logistic_regression(
    y: pd.Series,
    x: pd.Series | pd.DataFrame,
    add_constant: bool = True,
    covariance: str = "HC1",
) -> RegressionResult:
    """Binary logistic regression with robust covariance support."""
    y_s = pd.Series(y, dtype=float).rename("y"); x_f = pd.DataFrame(x, dtype=float)
    data = pd.concat([y_s, x_f], axis=1).dropna(); y_c = data.iloc[:, 0]; x_c = data.iloc[:, 1:]
    if not set(y_c.unique()).issubset({0.0, 1.0}):
        raise ValueError("logistic target must contain only 0 and 1")
    if add_constant:
        x_c = sm.add_constant(x_c, has_constant="add")
    fitted = sm.Logit(y_c, x_c).fit(disp=False, cov_type=covariance)
    probabilities = pd.Series(fitted.predict(x_c), index=data.index, name="fitted")
    residuals = (y_c - probabilities).rename("residual")
    return RegressionResult(
        model=fitted,
        coefficients=pd.Series(fitted.params),
        confidence_intervals=fitted.conf_int().set_axis(["lower", "upper"], axis=1),
        fitted=probabilities,
        residuals=residuals,
        diagnostics=pd.Series({"Pseudo R2": fitted.prsquared, "AIC": fitted.aic, "BIC": fitted.bic}),
    )


def factor_regression(
    asset_returns: pd.Series,
    factors: pd.DataFrame,
    risk_free: float | pd.Series = 0.0,
    covariance: str = "HAC",
    maxlags: int | None = None,
) -> RegressionResult:
    """Run a CAPM or multi-factor time-series regression on excess returns."""
    asset = pd.Series(asset_returns, dtype=float)
    rf = pd.Series(risk_free, index=asset.index, dtype=float) if np.isscalar(risk_free) else pd.Series(risk_free, dtype=float)
    excess = (asset - rf).rename("excess_return")
    return ols(excess, pd.DataFrame(factors, dtype=float), covariance=covariance, maxlags=maxlags)


def cointegration_test(y: pd.Series, x: pd.Series, trend: str = "c") -> pd.Series:
    """Engle-Granger two-step cointegration test."""
    from statsmodels.tsa.stattools import coint
    data = pd.concat([pd.Series(y, dtype=float), pd.Series(x, dtype=float)], axis=1).dropna()
    statistic, p_value, critical = coint(data.iloc[:, 0], data.iloc[:, 1], trend=trend)
    return pd.Series({"statistic": statistic, "p_value": p_value, "critical_1%": critical[0], "critical_5%": critical[1], "critical_10%": critical[2]})


def granger_causality(x: pd.Series, y: pd.Series, maxlag: int = 5) -> pd.DataFrame:
    """Report Granger-predictive F-test p-values; this is not structural causality."""
    from statsmodels.tsa.stattools import grangercausalitytests
    data = pd.concat([pd.Series(y, name="y"), pd.Series(x, name="x")], axis=1).dropna()
    results = grangercausalitytests(data, maxlag=maxlag, verbose=False)
    rows = []
    for lag, output in results.items():
        test = output[0]["ssr_ftest"]
        rows.append({"lag": lag, "F": test[0], "p_value": test[1], "df_denom": test[2], "df_num": test[3]})
    return pd.DataFrame(rows).set_index("lag")


def arima_fit(series: pd.Series, order: tuple[int, int, int] = (1, 0, 0), trend: str | None = None):
    """Fit an ARIMA model and return the statsmodels result object."""
    from statsmodels.tsa.arima.model import ARIMA
    s = pd.Series(series, dtype=float).dropna()
    return ARIMA(s, order=order, trend=trend).fit()


def var_fit(data: pd.DataFrame, lags: int = 1, trend: str = "c"):
    """Fit a vector autoregression to a multivariate stationary panel."""
    from statsmodels.tsa.api import VAR
    frame = pd.DataFrame(data, dtype=float).dropna()
    if frame.shape[1] < 2:
        raise ValueError("VAR requires at least two series")
    return VAR(frame).fit(lags, trend=trend)


def autoregression_fit(
    series: pd.Series,
    lags: int | list[int] = 1,
    trend: str = "c",
    *,
    old_names: bool = False,
):
    """Fit an explicit AR(p) model with statsmodels AutoReg.

    Parameters
    ----------
    series:
        Univariate time series.
    lags:
        Maximum lag order or an explicit list of included lags.
    trend:
        Deterministic terms: ``"n"``, ``"c"``, ``"t"`` or ``"ct"``.
    """
    from statsmodels.tsa.ar_model import AutoReg

    values = pd.Series(series, dtype=float).dropna()
    if len(values) < 3:
        raise ValueError("at least three finite observations are required")
    return AutoReg(values, lags=lags, trend=trend, old_names=old_names).fit()
