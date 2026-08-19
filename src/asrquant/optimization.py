"""Portfolio construction and risk decomposition without mandatory solvers."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def portfolio_return(weights: np.ndarray, expected_returns: np.ndarray) -> float:
    return float(np.asarray(weights) @ np.asarray(expected_returns))


def portfolio_volatility(weights: np.ndarray, covariance: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float)
    return float(np.sqrt(max(0.0, w @ np.asarray(covariance) @ w)))


def marginal_risk_contribution(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    vol = portfolio_volatility(w, cov)
    return cov @ w / vol if vol > 0 else np.zeros_like(w)


def risk_contributions(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    return w * marginal_risk_contribution(w, covariance)


def minimum_variance(covariance: pd.DataFrame | np.ndarray, long_only: bool = True) -> np.ndarray:
    cov = np.asarray(covariance, dtype=float)
    n = cov.shape[0]
    bounds = [(0.0, 1.0)] * n if long_only else [(-1.0, 1.0)] * n
    result = minimize(
        lambda w: w @ cov @ w,
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
    )
    if not result.success:
        raise RuntimeError(f"optimization failed: {result.message}")
    return result.x


def maximum_sharpe(
    expected_returns: pd.Series | np.ndarray,
    covariance: pd.DataFrame | np.ndarray,
    risk_free_rate: float = 0.0,
    long_only: bool = True,
) -> np.ndarray:
    mu = np.asarray(expected_returns, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    n = len(mu)
    bounds = [(0.0, 1.0)] * n if long_only else [(-1.0, 1.0)] * n

    def objective(w: np.ndarray) -> float:
        vol = portfolio_volatility(w, cov)
        return -(portfolio_return(w, mu) - risk_free_rate) / vol if vol > 0 else 1e6

    result = minimize(
        objective,
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
    )
    if not result.success:
        raise RuntimeError(f"optimization failed: {result.message}")
    return result.x


def equal_risk_contribution(covariance: pd.DataFrame | np.ndarray) -> np.ndarray:
    cov = np.asarray(covariance, dtype=float)
    n = cov.shape[0]

    def objective(w: np.ndarray) -> float:
        rc = risk_contributions(w, cov)
        total = rc.sum()
        if total <= 0:
            return 1e6
        normalized = rc / total
        return float(np.square(normalized - 1 / n).sum())

    result = minimize(
        objective,
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=[(1e-10, 1.0)] * n,
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
        options={"ftol": 1e-14, "maxiter": 10_000},
    )
    if not result.success:
        raise RuntimeError(f"optimization failed: {result.message}")
    return result.x


def random_frontier(
    expected_returns: pd.Series | np.ndarray,
    covariance: pd.DataFrame | np.ndarray,
    n_portfolios: int = 5_000,
    risk_free_rate: float = 0.0,
    random_state: int | None = 0,
) -> pd.DataFrame:
    """Monte Carlo long-only portfolio cloud."""
    mu = np.asarray(expected_returns, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    rng = np.random.default_rng(random_state)
    weights = rng.dirichlet(np.ones(len(mu)), size=n_portfolios)
    rets = weights @ mu
    vols = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov, weights))
    sharpes = np.divide(rets - risk_free_rate, vols, out=np.full_like(rets, np.nan), where=vols > 0)
    frame = pd.DataFrame({"return": rets, "volatility": vols, "sharpe": sharpes})
    for i in range(weights.shape[1]):
        frame[f"w{i}"] = weights[:, i]
    return frame


def estimate_covariance(
    returns: pd.DataFrame,
    method: str = "sample",
    *,
    annualization: int = 252,
    span: int = 60,
) -> pd.DataFrame:
    """Estimate annualized covariance using sample, EWMA, Ledoit-Wolf, or OAS."""
    frame = pd.DataFrame(returns, dtype=float).dropna()
    key = method.lower().replace("-", "_")
    if key == "sample":
        cov = frame.cov().to_numpy() * annualization
    elif key == "ewma":
        cov = frame.ewm(span=span, adjust=False).cov().groupby(level=1).tail(1).droplevel(0).reindex(index=frame.columns, columns=frame.columns).to_numpy() * annualization
    elif key in {"ledoit_wolf", "ledoitwolf"}:
        from sklearn.covariance import LedoitWolf
        cov = LedoitWolf().fit(frame).covariance_ * annualization
    elif key == "oas":
        from sklearn.covariance import OAS
        cov = OAS().fit(frame).covariance_ * annualization
    else:
        raise ValueError("method must be sample, ewma, ledoit_wolf, or oas")
    return pd.DataFrame(cov, index=frame.columns, columns=frame.columns)


def maximum_diversification(covariance: pd.DataFrame | np.ndarray, long_only: bool = True) -> np.ndarray:
    """Maximize the diversification ratio w' sigma / sqrt(w' Sigma w)."""
    cov = np.asarray(covariance, dtype=float)
    asset_vol = np.sqrt(np.diag(cov)); n = len(asset_vol)
    bounds = [(0.0, 1.0)] * n if long_only else [(-1.0, 1.0)] * n
    def objective(w):
        vol = portfolio_volatility(w, cov)
        return -(w @ asset_vol) / vol if vol > 0 else 1e6
    result = minimize(objective, np.repeat(1/n, n), method="SLSQP", bounds=bounds, constraints={"type": "eq", "fun": lambda w: w.sum()-1})
    if not result.success:
        raise RuntimeError(f"optimization failed: {result.message}")
    return result.x


def efficient_frontier(
    expected_returns: pd.Series | np.ndarray,
    covariance: pd.DataFrame | np.ndarray,
    points: int = 50,
    long_only: bool = True,
) -> pd.DataFrame:
    """Compute minimum-volatility portfolios across a return grid."""
    mu = np.asarray(expected_returns, dtype=float); cov = np.asarray(covariance, dtype=float); n = len(mu)
    bounds = [(0.0, 1.0)] * n if long_only else [(-1.0, 1.0)] * n
    targets = np.linspace(mu.min(), mu.max(), points)
    rows = []
    for target in targets:
        result = minimize(lambda w: w@cov@w, np.repeat(1/n,n), method="SLSQP", bounds=bounds, constraints=[{"type":"eq","fun":lambda w:w.sum()-1},{"type":"eq","fun":lambda w,t=target:w@mu-t}])
        if result.success:
            row={"return": result.x@mu, "volatility": np.sqrt(result.x@cov@result.x)}
            row.update({f"w{i}": value for i,value in enumerate(result.x)}); rows.append(row)
    return pd.DataFrame(rows)


def black_litterman(
    covariance: pd.DataFrame | np.ndarray,
    market_weights: np.ndarray,
    risk_aversion: float,
    views: np.ndarray | None = None,
    pick_matrix: np.ndarray | None = None,
    view_covariance: np.ndarray | None = None,
    tau: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Return Black-Litterman posterior mean and covariance."""
    cov = np.asarray(covariance, dtype=float); w = np.asarray(market_weights, dtype=float)
    pi = risk_aversion * cov @ w
    if views is None or pick_matrix is None:
        return pi, cov + tau*cov
    q = np.asarray(views, dtype=float); p = np.asarray(pick_matrix, dtype=float)
    omega = np.asarray(view_covariance, dtype=float) if view_covariance is not None else np.diag(np.diag(p @ (tau*cov) @ p.T))
    tau_inv = np.linalg.inv(tau*cov); omega_inv = np.linalg.inv(omega)
    posterior_cov = np.linalg.inv(tau_inv + p.T@omega_inv@p)
    posterior_mean = posterior_cov @ (tau_inv@pi + p.T@omega_inv@q)
    return posterior_mean, cov + posterior_cov


def hierarchical_risk_parity(returns: pd.DataFrame) -> pd.Series:
    """Hierarchical risk parity using correlation clustering and recursive bisection."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    frame = pd.DataFrame(returns, dtype=float).dropna()
    cov = frame.cov(); corr = frame.corr().clip(-1,1)
    distance = np.sqrt((1-corr)/2)
    order = leaves_list(linkage(squareform(distance.to_numpy(), checks=False), method="single"))
    ordered = list(frame.columns[order])
    weights = pd.Series(1.0, index=ordered)
    clusters = [ordered]
    def cluster_var(items):
        sub = cov.loc[items, items]
        ivp = 1/np.diag(sub); ivp = ivp/ivp.sum()
        return float(ivp @ sub.to_numpy() @ ivp)
    while clusters:
        next_clusters=[]
        for cluster in clusters:
            if len(cluster)<=1: continue
            split=len(cluster)//2; left=cluster[:split]; right=cluster[split:]
            v_left=cluster_var(left); v_right=cluster_var(right); alpha=1-v_left/(v_left+v_right)
            weights[left]*=alpha; weights[right]*=1-alpha
            next_clusters.extend([left,right])
        clusters=next_clusters
    return weights.reindex(frame.columns)
