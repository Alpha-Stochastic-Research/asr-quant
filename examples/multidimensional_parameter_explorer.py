"""Explore five experiment parameters with one ASRQuant import."""
from __future__ import annotations

from dataclasses import dataclass

import asrquant as asr


@dataclass
class ExperimentResult:
    metrics: dict[str, float]


def research_experiment(
    risk_aversion: float,
    cost_bps: float,
    hedge_every: int,
    volatility: float,
    model: str,
) -> ExperimentResult:
    """Replace this body with a backtest, pricing routine, or model trainer."""
    model_penalty = {"linear": 0.03, "neural": 0.01}[model]
    utility = (
        asr.math.cos(risk_aversion / 2)
        - cost_bps / 50
        - hedge_every / 100
        - volatility
        - model_penalty
    )
    return ExperimentResult(metrics={"utility": float(utility)})


prices = asr.frame(
    {"asset": asr.math.linspace(100, 110, 40)},
    index=asr.date_range("2026-01-01", periods=40, freq="B"),
)
lab = asr.QuantLab(prices)

surface = lab.explore(
    research_experiment,
    {
        "risk_aversion": asr.math.linspace(0.5, 5.0, 20),
        "cost_bps": asr.math.linspace(0.0, 20.0, 16),
        "hedge_every": [1, 5, 20],
        "volatility": [0.15, 0.30],
        "model": ["linear", "neural"],
    },
    x="risk_aversion",
    y="cost_bps",
    animate_by=["hedge_every", "volatility", "model"],
    metric="metrics.utility",
    z_name="utility",
    n_jobs=4,
)

print(surface.summary)
print("Best point:\n", surface.best("max"))
surface.save_animation("multidimensional_parameter_explorer.html", kind="surface")
