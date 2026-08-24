"""Monte Carlo delta-hedging surface using only ASRQuant's public facade.

This is not a neural deep-hedging implementation. Replace the callback with a
PyTorch/JAX training-and-evaluation function while keeping the exploration API.
"""
from __future__ import annotations

import asrquant as asr


def bsm_call_price_delta(spot, strike, tau, rate, volatility):
    m = asr.math
    tau = m.maximum(m.asarray(tau, dtype=float), 1e-12)
    spot = m.asarray(spot, dtype=float)
    d1 = (m.log(spot / strike) + (rate + 0.5 * volatility**2) * tau) / (volatility * m.sqrt(tau))
    price = spot * m.normal_cdf(d1) - strike * m.exp(-rate * tau) * m.normal_cdf(d1 - volatility * m.sqrt(tau))
    return price, m.normal_cdf(d1)


def delta_hedging_experiment(
    risk_aversion: float,
    cost_bps: float,
    hedge_every: int,
    volatility: float,
    *,
    spot: float = 100.0,
    strike: float = 100.0,
    maturity: float = 1.0,
    rate: float = 0.02,
    steps: int = 63,
    paths: int = 750,
    seed: int = 7,
):
    m = asr.math
    rng = m.random_generator(seed)
    dt = maturity / steps
    shocks = rng.normal(size=(steps, paths))
    log_increments = (rate - 0.5 * volatility**2) * dt + volatility * m.sqrt(dt) * shocks
    simulated = m.vstack([m.full(paths, spot), spot * m.exp(m.cumsum(log_increments, axis=0))])

    premium, initial_delta = bsm_call_price_delta(spot, strike, maturity, rate, volatility)
    delta = m.full(paths, float(initial_delta))
    cash = m.full(paths, float(premium)) - delta * spot
    cash -= m.abs(delta) * spot * cost_bps / 10_000

    for step in range(1, steps + 1):
        cash *= m.exp(rate * dt)
        if step < steps and step % int(hedge_every) == 0:
            tau = maturity - step * dt
            _, new_delta = bsm_call_price_delta(simulated[step], strike, tau, rate, volatility)
            trade = new_delta - delta
            cash -= trade * simulated[step]
            cash -= m.abs(trade) * simulated[step] * cost_bps / 10_000
            delta = new_delta

    payoff = m.maximum(simulated[-1] - strike, 0.0)
    pnl = cash + delta * simulated[-1] - payoff
    scaled = -risk_aversion * pnl
    entropic_utility = -(m.logsumexp(scaled) - m.log(len(pnl))) / risk_aversion
    cvar_95 = pnl[pnl <= m.quantile(pnl, 0.05)].mean()
    return {
        "entropic_utility": float(entropic_utility),
        "mean_pnl": float(pnl.mean()),
        "cvar_95": float(cvar_95),
    }


prices = asr.frame(
    {"asset": asr.math.linspace(100, 101, 20)},
    index=asr.date_range("2026-01-01", periods=20, freq="B"),
)
lab = asr.QuantLab(prices)

surface = lab.parameter_surface(
    delta_hedging_experiment,
    {
        "risk_aversion": asr.math.linspace(0.05, 0.50, 8),
        "cost_bps": asr.math.linspace(0.0, 20.0, 7),
        "hedge_every": [1, 5, 21],
        "volatility": [0.15, 0.30],
    },
    x="risk_aversion",
    y="cost_bps",
    animate_by=["hedge_every", "volatility"],
    metric="entropic_utility",
    z_name="entropic utility",
    n_jobs=4,
)

print(surface.summary)
print(surface.best("max"))
surface.save_animation("hedging_parameter_animation.html", kind="surface")
