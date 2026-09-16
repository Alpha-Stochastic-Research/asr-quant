"""Behavioral corrections promoted in ASRQuant 1.3.0.

This compatibility layer patches the long-lived 1.x implementations at package
initialization so direct submodule imports and legacy aliases receive the same
correct behavior. The replacements are intentionally small and regression-tested.
"""
from __future__ import annotations

import inspect
import warnings
import numpy as np
import pandas as pd


def install(package_globals: dict) -> None:
    from . import interest_rates as ir, metrics, derivatives, approximation as ap, statistics as st, machine_learning as ml

    def bump_key_rate(self, maturity: float, bump: float = 1e-4, width: float | None = None):
        if maturity <= 0 or maturity > self.times[-1]:
            raise ValueError("key-rate maturity must lie in the curve domain")
        t = self.times.copy(); p = self.discounts.copy(); positive = t > 0
        z = -np.log(p[positive]) / t[positive]; tp = t[positive]
        if width is None:
            idx = int(np.argmin(np.abs(tp - maturity)))
            if not np.isclose(tp[idx], maturity, atol=1e-10, rtol=0):
                raise ValueError("maturity must match a curve pillar when width is omitted")
            left = tp[idx-1] if idx > 0 else maturity
            right = tp[idx+1] if idx+1 < len(tp) else maturity
            lw = max(maturity-left, 1e-12); rw = max(right-maturity, 1e-12)
            weights = np.where(tp <= maturity, np.maximum(1-(maturity-tp)/lw, 0.0), np.maximum(1-(tp-maturity)/rw, 0.0))
        else:
            if width <= 0: raise ValueError("width must be positive")
            weights = np.maximum(1.0 - np.abs(tp-maturity)/width, 0.0)
        p[positive] = np.exp(-(z + bump*weights) * tp)
        return ir.DiscountCurve(t, p, self.interpolation, self.name + f"_kr{maturity:g}", self.metadata)
    ir.DiscountCurve.bump_key_rate = bump_key_rate

    def probabilistic_sharpe_ratio(returns, benchmark_sharpe: float = 0.0, annualization: int = 252) -> float:
        r = metrics._series(returns); n = len(r)
        if n < 3: return np.nan
        sr = metrics.sharpe_ratio(r, annualization=1)
        skew = metrics.stats.skew(r, bias=False); kurt = metrics.stats.kurtosis(r, fisher=False, bias=False)
        denom = np.sqrt(max(1e-12, 1-skew*sr + ((kurt-1)/4)*sr**2))
        z = (sr-benchmark_sharpe)*np.sqrt(n-1)/denom
        return float(metrics.stats.norm.cdf(z))
    metrics.probabilistic_sharpe_ratio = probabilistic_sharpe_ratio
    package_globals["probabilistic_sharpe_ratio"] = probabilistic_sharpe_ratio

    def implied_volatility(market_price, spot, strike, maturity, rate, option="call", dividend=0.0, model="black_scholes"):
        if market_price <= 0: raise ValueError("market_price must be positive")
        key = model.lower().replace("-", "_")
        if key in {"black_scholes", "bsm"}:
            objective = lambda sigma: float(derivatives.black_scholes_price(spot,strike,maturity,rate,sigma,option,dividend)-market_price); low, high = 1e-8, 10.0
        elif key in {"black76", "black_76"}:
            objective = lambda sigma: float(derivatives.black76_price(spot,strike,maturity,rate,sigma,option)-market_price); low, high = 1e-8, 10.0
        elif key in {"bachelier", "normal"}:
            objective = lambda sigma: float(derivatives.bachelier_price(spot,strike,maturity,sigma,option,np.exp(-rate*maturity))-market_price); low, high = 1e-10, max(spot,strike)*100
        else: raise ValueError("model must be black_scholes, black76, or bachelier")
        f_low, f_high = objective(low), objective(high)
        tol = 1e-12 * max(1.0, abs(float(market_price)))
        if abs(f_low) <= tol:
            raise ValueError("market price is at the model's intrinsic boundary; implied volatility is not identifiable")
        if f_low*f_high > 0:
            raise ValueError("market price is outside the model's invertible range")
        return float(derivatives.brentq(objective, low, high, maxiter=300))
    derivatives.implied_volatility = implied_volatility
    package_globals["implied_volatility"] = implied_volatility

    def gaussian_process(x, y, *, length_scale=1.0, noise=1e-6, normalize_y=True, random_state=0):
        if noise <= 0: raise ValueError("noise must be positive")
        xx, yy = ap._xy(x, y); scaler = ap.StandardScaler().fit(xx); scaled = scaler.transform(xx)
        kernel = ap.ConstantKernel(1.0, (1e-6,1e6))*ap.RBF(length_scale=length_scale) + ap.WhiteKernel(noise_level=noise, noise_level_bounds="fixed")
        model = ap.GaussianProcessRegressor(kernel=kernel, normalize_y=normalize_y, random_state=random_state); model.fit(scaled, yy)
        fitted_noise = float(model.kernel_.k2.noise_level)
        return ap.ApproximationResult({"scaler": scaler, "regressor": model}, "gaussian_process", xx.shape[1], xx.min(axis=0), xx.max(axis=0), {"kernel": str(model.kernel_), "noise": fitted_noise, "requested_noise": float(noise), "standardized_inputs": True}, lambda q: model.predict(scaler.transform(q)), lambda q: model.predict(scaler.transform(q), return_std=True))
    ap.gaussian_process = gaussian_process
    package_globals["gaussian_process"] = gaussian_process

    def granger_causality(x, y, maxlag: int = 5):
        from statsmodels.tsa.stattools import grangercausalitytests
        data = pd.concat([pd.Series(y,name="y"), pd.Series(x,name="x")], axis=1).dropna()
        kwargs = {"maxlag": maxlag}
        if "verbose" in inspect.signature(grangercausalitytests).parameters: kwargs["verbose"] = False
        results = grangercausalitytests(data, **kwargs); rows=[]
        for lag, output in results.items():
            test = output[0]["ssr_ftest"]; rows.append({"lag":lag,"F":test[0],"p_value":test[1],"df_denom":test[2],"df_num":test[3]})
        return pd.DataFrame(rows).set_index("lag")
    st.granger_causality = granger_causality

    def autoregression_fit(series, lags=1, trend="c", *, old_names: bool=False):
        from statsmodels.tsa.ar_model import AutoReg
        values = pd.Series(series,dtype=float).dropna()
        if len(values) < 3: raise ValueError("at least three finite observations are required")
        if old_names: warnings.warn("old_names is deprecated and ignored; statsmodels no longer supports it", DeprecationWarning, stacklevel=2)
        return AutoReg(values,lags=lags,trend=trend).fit()
    st.autoregression_fit = autoregression_fit
    package_globals["autoregression_fit"] = autoregression_fit

    def technical_features(prices, windows=(5,20,63), *, rsi_method: str="wilder"):
        p = pd.Series(prices,dtype=float).rename("price"); r = p.pct_change(fill_method=None)
        out={"return_1":r,"log_return_1":np.log(p).diff()}
        for window in windows:
            out[f"momentum_{window}"]=p.pct_change(window,fill_method=None)
            out[f"volatility_{window}"]=r.rolling(window).std(ddof=1)*np.sqrt(252)
            out[f"zscore_{window}"]=(p-p.rolling(window).mean())/p.rolling(window).std(ddof=1)
            out[f"drawdown_{window}"]=p/p.rolling(window).max()-1.0
        delta=p.diff(); gains=delta.clip(lower=0); losses=-delta.clip(upper=0); method=rsi_method.lower().replace("-","_")
        if method in {"wilder","rma"}:
            gain=gains.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); loss=losses.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
        elif method=="sma": gain=gains.rolling(14).mean(); loss=losses.rolling(14).mean()
        else: raise ValueError("rsi_method must be 'wilder' or 'sma'")
        rs=gain/loss.replace(0.0,np.nan); out["rsi_14"]=100-100/(1+rs)
        return pd.DataFrame(out,index=p.index)
    ml.technical_features = technical_features
    package_globals["technical_features"] = technical_features

    def yield_curve_pca(yields, n_components: int=3, *, differences: bool=True):
        frame=pd.DataFrame(yields).apply(pd.to_numeric,errors="coerce").dropna(); x=frame.diff().dropna() if differences else frame.copy()
        if len(x)<3 or x.shape[1]<2: raise ValueError("yield_curve_pca needs at least 3 rows and 2 maturities")
        centered=x.to_numpy()-x.to_numpy().mean(axis=0); _,s,vt=np.linalg.svd(centered,full_matrices=False); k=min(n_components,len(s),x.shape[1]); vt=vt.copy()
        for i in range(k):
            pivot=int(np.argmax(np.abs(vt[i]))); vt[i] *= -1.0 if vt[i,pivot] < 0 else 1.0
        explained=s**2/np.sum(s**2); scores=centered@vt[:k].T; cols=[f"PC{i+1}" for i in range(k)]
        loadings=pd.DataFrame(vt[:k].T,index=frame.columns,columns=cols); score_frame=pd.DataFrame(scores,index=x.index,columns=cols)
        return {"loadings":loadings,"scores":score_frame,"explained_variance_ratio":pd.Series(explained[:k],index=cols)}
    ir.yield_curve_pca = yield_curve_pca
    package_globals["yield_curve_pca"] = yield_curve_pca
