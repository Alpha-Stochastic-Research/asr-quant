"""Targeted compatibility and numerical fixes validated for ASRQuant 1.3.0rc1.

This module keeps the release-candidate fixes isolated while preserving the
public 1.x API.  It is installed once, near the end of package initialization,
after the affected modules have been imported.
"""
from __future__ import annotations

import inspect
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


_INSTALLED = False


def _package_module():
    return sys.modules.get("asrquant")


def _fixed_bump_key_rate(self, maturity: float, bump: float = 1e-4, width: float | None = None):
    """Bump one key rate with a partition-of-unity triangular basis.

    With the default ``width=None`` each side uses its own neighbouring-pillar
    spacing.  This is intentionally asymmetric on irregular market grids.  The
    old implementation used the wider spacing on both sides, which caused
    overlapping bumps and made key-rate DV01s fail to add to the parallel DV01.
    """
    from .interest_rates import DiscountCurve

    maturity = float(maturity)
    if maturity <= 0 or maturity > self.times[-1]:
        raise ValueError("key-rate maturity must lie in the curve domain")

    t = self.times.copy()
    p = self.discounts.copy()
    positive = t > 0
    tp = t[positive]
    z = -np.log(p[positive]) / tp

    if width is not None:
        width = float(width)
        if width <= 0:
            raise ValueError("width must be positive")
        weights = np.maximum(1.0 - np.abs(tp - maturity) / width, 0.0)
    else:
        # Default key-rate buckets are centred on curve pillars.  For a centre
        # between pillars we still construct a valid local triangular bump using
        # the nearest pillar on each side.
        tol = 32.0 * np.finfo(float).eps * max(1.0, abs(maturity))
        equal = np.flatnonzero(np.abs(tp - maturity) <= tol)
        if equal.size:
            idx = int(equal[0])
            left = float(tp[idx - 1]) if idx > 0 else None
            right = float(tp[idx + 1]) if idx + 1 < len(tp) else None
        else:
            insert = int(np.searchsorted(tp, maturity))
            left = float(tp[insert - 1]) if insert > 0 else None
            right = float(tp[insert]) if insert < len(tp) else None

        weights = np.zeros_like(tp, dtype=float)
        at_center = np.abs(tp - maturity) <= tol
        weights[at_center] = 1.0

        if left is not None:
            left_width = maturity - left
            if left_width <= 0:
                raise ValueError("invalid left key-rate spacing")
            mask = (tp >= left) & (tp < maturity)
            weights[mask] = (tp[mask] - left) / left_width

        if right is not None:
            right_width = right - maturity
            if right_width <= 0:
                raise ValueError("invalid right key-rate spacing")
            mask = (tp > maturity) & (tp <= right)
            weights[mask] = (right - tp[mask]) / right_width

        # Endpoint centres have only one shoulder.  Preserve a unit weight at
        # the actual endpoint pillar.
        if equal.size:
            weights[int(equal[0])] = 1.0

    p[positive] = np.exp(-(z + float(bump) * weights) * tp)
    return DiscountCurve(t, p, self.interpolation, self.name + f"_kr{maturity:g}", self.metadata)


def _orient_pca_result(result: dict[str, Any]) -> dict[str, Any]:
    """Apply a deterministic sign convention while preserving reconstruction."""
    fixed = dict(result)
    loadings = pd.DataFrame(result["loadings"]).copy()
    scores = pd.DataFrame(result["scores"]).copy()
    for column in loadings.columns:
        values = loadings[column].to_numpy(dtype=float)
        if not len(values):
            continue
        anchor = int(np.argmax(np.abs(values)))
        if values[anchor] < 0:
            loadings[column] = -loadings[column]
            if column in scores.columns:
                scores[column] = -scores[column]
    fixed["loadings"] = loadings
    fixed["scores"] = scores
    return fixed


def _no_arbitrage_lower_bound(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    option: str,
    dividend: float,
    model: str,
) -> float:
    side = str(option).lower()
    if side not in {"call", "put"}:
        raise ValueError("option must be call or put")
    key = str(model).lower().replace("-", "_")
    disc_r = float(np.exp(-float(rate) * float(maturity)))
    if key in {"black_scholes", "bsm"}:
        disc_q = float(np.exp(-float(dividend) * float(maturity)))
        forward_pv = float(spot) * disc_q
        strike_pv = float(strike) * disc_r
    elif key in {"black76", "black_76", "bachelier", "normal"}:
        forward_pv = float(spot) * disc_r
        strike_pv = float(strike) * disc_r
    else:
        raise ValueError("model must be black_scholes, black76, or bachelier")
    return max(forward_pv - strike_pv, 0.0) if side == "call" else max(strike_pv - forward_pv, 0.0)


def _wilder_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    p = pd.Series(prices, dtype=float)
    delta = p.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = pd.Series(np.nan, index=p.index, dtype=float)
    avg_loss = pd.Series(np.nan, index=p.index, dtype=float)
    if len(p) <= period:
        return avg_gain.rename(f"rsi_{period}")

    seed_gain = float(gains.iloc[1 : period + 1].mean())
    seed_loss = float(losses.iloc[1 : period + 1].mean())
    avg_gain.iloc[period] = seed_gain
    avg_loss.iloc[period] = seed_loss
    for i in range(period + 1, len(p)):
        avg_gain.iloc[i] = ((period - 1) * avg_gain.iloc[i - 1] + gains.iloc[i]) / period
        avg_loss.iloc[i] = ((period - 1) * avg_loss.iloc[i - 1] + losses.iloc[i]) / period

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain > 0.0)), 100.0)
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain == 0.0)), 50.0)
    return rsi.rename(f"rsi_{period}")


def _psr_observation_scale(r: pd.Series, benchmark_observation_sharpe: float) -> float:
    n = len(r)
    if n < 3:
        return np.nan
    volatility = float(r.std(ddof=1))
    if volatility <= 1e-15:
        return np.nan
    sr = float(r.mean() / volatility)
    skew = float(scipy_stats.skew(r, bias=False))
    kurt = float(scipy_stats.kurtosis(r, fisher=False, bias=False))
    variance_term = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2
    denom = np.sqrt(max(1e-12, variance_term))
    z = (sr - float(benchmark_observation_sharpe)) * np.sqrt(n - 1.0) / denom
    return float(scipy_stats.norm.cdf(z))


def install_release_fixes() -> None:
    """Install the validated 1.3.0rc1 fixes exactly once."""
    global _INSTALLED
    if _INSTALLED:
        return

    from . import approximation as approx
    from . import derivatives as options
    from . import interest_rates as rates
    from . import machine_learning as ml
    from . import metrics
    from . import statistics as statistics_module

    package = _package_module()

    # FIND-003: irregular key-rate grids must use each side's own spacing.
    rates.DiscountCurve.bump_key_rate = _fixed_bump_key_rate

    # FIND-015: SVD signs are arbitrary; orient each component deterministically.
    original_yield_curve_pca = rates.yield_curve_pca

    def yield_curve_pca(*args: Any, **kwargs: Any):
        return _orient_pca_result(original_yield_curve_pca(*args, **kwargs))

    rates.yield_curve_pca = yield_curve_pca

    # FIND-014: a quote at the zero-volatility intrinsic bound is not an
    # identifiable implied-volatility problem.  Refuse instead of returning the
    # numerical solver's lower bracket as if it were calibrated.
    original_implied_volatility = options.implied_volatility

    def implied_volatility(
        market_price: float,
        spot: float,
        strike: float,
        maturity: float,
        rate: float,
        option: str = "call",
        dividend: float = 0.0,
        model: str = "black_scholes",
    ) -> float:
        lower = _no_arbitrage_lower_bound(spot, strike, maturity, rate, option, dividend, model)
        scale = max(1.0, abs(float(market_price)), abs(float(spot)), abs(float(strike)), abs(lower))
        tolerance = 64.0 * np.finfo(float).eps * scale
        if float(market_price) <= lower + tolerance:
            raise ValueError(
                "market price is at the model's zero-volatility boundary; "
                "implied volatility is not identifiable at machine precision"
            )
        return original_implied_volatility(
            market_price,
            spot,
            strike,
            maturity,
            rate,
            option=option,
            dividend=dividend,
            model=model,
        )

    options.implied_volatility = implied_volatility

    # FIND-012: statsmodels 0.15 removed old_names and verbose.
    def autoregression_fit(
        series: pd.Series,
        lags: int | list[int] = 1,
        trend: str = "c",
        *,
        old_names: bool = False,
    ):
        from statsmodels.tsa.ar_model import AutoReg

        values = pd.Series(series, dtype=float).dropna()
        if len(values) < 3:
            raise ValueError("at least three finite observations are required")
        kwargs: dict[str, Any] = {"lags": lags, "trend": trend}
        parameters = inspect.signature(AutoReg).parameters
        if "old_names" in parameters:
            kwargs["old_names"] = old_names
        elif old_names:
            raise ValueError("old_names=True is unsupported by statsmodels >= 0.15")
        return AutoReg(values, **kwargs).fit()

    def granger_causality(x: pd.Series, y: pd.Series, maxlag: int = 5) -> pd.DataFrame:
        from statsmodels.tsa.stattools import grangercausalitytests

        data = pd.concat([pd.Series(y, name="y"), pd.Series(x, name="x")], axis=1).dropna()
        results = grangercausalitytests(data, maxlag=maxlag)
        rows = []
        for lag, output in results.items():
            test = output[0]["ssr_ftest"]
            rows.append({"lag": lag, "F": test[0], "p_value": test[1], "df_denom": test[2], "df_num": test[3]})
        return pd.DataFrame(rows).set_index("lag")

    statistics_module.autoregression_fit = autoregression_fit
    statistics_module.granger_causality = granger_causality

    # FIND-011: PSR/DSR formulae operate on per-observation Sharpe ratios.
    def probabilistic_sharpe_ratio(
        returns,
        benchmark_sharpe: float = 0.0,
        annualization: int = 252,
    ) -> float:
        if annualization <= 0:
            raise ValueError("annualization must be positive")
        r = metrics._series(returns)
        benchmark_observation = float(benchmark_sharpe) / np.sqrt(float(annualization))
        return _psr_observation_scale(r, benchmark_observation)

    def deflated_sharpe_ratio(
        returns,
        trials: int = 1,
        annualization: int = 252,
    ) -> float:
        if trials < 1:
            raise ValueError("trials must be >= 1")
        if annualization <= 0:
            raise ValueError("annualization must be positive")
        r = metrics._series(returns)
        if trials == 1:
            benchmark_observation = 0.0
        else:
            euler_gamma = 0.5772156649
            z1 = scipy_stats.norm.ppf(1.0 - 1.0 / trials)
            z2 = scipy_stats.norm.ppf(1.0 - 1.0 / (trials * np.e))
            sr_std = 1.0 / np.sqrt(max(len(r) - 1, 1))
            benchmark_observation = sr_std * ((1.0 - euler_gamma) * z1 + euler_gamma * z2)
        return _psr_observation_scale(r, benchmark_observation)

    metrics.probabilistic_sharpe_ratio = probabilistic_sharpe_ratio
    metrics.deflated_sharpe_ratio = deflated_sharpe_ratio

    # FIND-005: zero-threshold Omega equals Profit Factor by identity.  Expose
    # the Omega threshold at summary level so users can request non-redundant
    # information without breaking the existing zero default.
    original_summary_metrics = metrics.summary_metrics

    def summary_metrics(
        returns,
        annualization: int = 252,
        risk_free_rate: float = 0.0,
        benchmark=None,
        turnover=None,
        *,
        omega_threshold: float = 0.0,
    ) -> pd.Series:
        result = original_summary_metrics(
            returns,
            annualization=annualization,
            risk_free_rate=risk_free_rate,
            benchmark=benchmark,
            turnover=turnover,
        ).copy()
        result.loc["Omega"] = metrics.omega_ratio(returns, threshold=omega_threshold)
        return result

    metrics.summary_metrics = summary_metrics

    # FIND-013: unqualified RSI(14) uses Wilder's smoothing convention.
    original_technical_features = ml.technical_features

    def technical_features(prices: pd.Series, windows=(5, 20, 63)) -> pd.DataFrame:
        result = original_technical_features(prices, windows=windows).copy()
        result["rsi_14"] = _wilder_rsi(pd.Series(prices, dtype=float), period=14)
        return result

    ml.technical_features = technical_features

    # FIND-006: ``noise`` is a fixed observation-noise contract, not merely an
    # optimizer starting value.  Fit the remaining kernel parameters while
    # keeping WhiteKernel at the requested value, and report the fitted value.
    def gaussian_process(
        x: Any,
        y: Any,
        *,
        length_scale: float | list[float] | tuple[float, ...] = 1.0,
        noise: float = 1e-6,
        normalize_y: bool = True,
        random_state: int | None = 0,
    ):
        if noise <= 0:
            raise ValueError("noise must be positive")
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
        from sklearn.preprocessing import StandardScaler

        xx, yy = approx._xy(x, y)
        scaler = StandardScaler().fit(xx)
        scaled = scaler.transform(xx)
        kernel = (
            ConstantKernel(1.0, (1e-6, 1e6))
            * RBF(length_scale=length_scale)
            + WhiteKernel(noise_level=noise, noise_level_bounds="fixed")
        )
        model = GaussianProcessRegressor(
            kernel=kernel,
            normalize_y=normalize_y,
            random_state=random_state,
        )
        model.fit(scaled, yy)
        fitted_noise = float(model.kernel_.k2.noise_level)
        return approx.ApproximationResult(
            {"scaler": scaler, "regressor": model},
            "gaussian_process",
            xx.shape[1],
            xx.min(axis=0),
            xx.max(axis=0),
            {"kernel": str(model.kernel_), "noise": fitted_noise, "standardized_inputs": True},
            lambda q: model.predict(scaler.transform(q)),
            lambda q: model.predict(scaler.transform(q), return_std=True),
        )

    approx.gaussian_process = gaussian_process

    # Keep the one-import package aliases synchronized with the patched module
    # attributes.  Direct submodule imports already see the module assignments.
    if package is not None:
        package.implied_volatility = implied_volatility
        package.yield_curve_pca = yield_curve_pca
        package.autoregression_fit = autoregression_fit
        package.technical_features = technical_features
        package.gaussian_process = gaussian_process
        package.summary_metrics = summary_metrics

    _INSTALLED = True
