from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from asrquant import QuantLab, evaluate_parameter_surface, surface_from_dataframe


@dataclass
class DummyResult:
    metrics: dict[str, float]


def test_n_dimensional_surface_with_multiple_animation_parameters(tmp_path):
    def experiment(gamma, cost, hedge_every, volatility, model):
        model_penalty = 0.05 if model == "linear" else 0.1
        score = np.cos(gamma) - cost / 100 - hedge_every / 50 - volatility - model_penalty
        return DummyResult(metrics={"utility": score})

    result = evaluate_parameter_surface(
        experiment,
        {
            "gamma": [0.5, 1.0, 2.0],
            "cost": [0, 5],
            "hedge_every": [1, 5],
            "volatility": [0.15, 0.30],
            "model": ["linear", "neural"],
        },
        x="gamma",
        y="cost",
        animate_by=["hedge_every", "volatility", "model"],
        metric="metrics.utility",
        z_name="utility",
        n_jobs=2,
    )
    assert result.frame_count == 8
    assert list(result.frame_parameters.columns) == ["hedge_every", "volatility", "model"]
    assert result.z_values.shape == (8, 2, 3)
    assert "model=linear" in result.frame_labels[0]
    best = result.best("max")
    assert set(["gamma", "cost", "hedge_every", "volatility", "model", "utility"]).issubset(best.index)

    html = result.save_animation(tmp_path / "explorer.html", kind="surface")
    assert Path(html).exists()
    text = Path(html).read_text(encoding="utf-8")
    assert "plotly" in text.lower()
    assert "hedge_every" in text


def test_metric_callable_error_policy_and_guard():
    def experiment(x, y, regime):
        if x == 2 and regime == "stress":
            raise RuntimeError("intentional")
        return {"loss": (x - 1) ** 2 + y + (1 if regime == "stress" else 0)}

    result = evaluate_parameter_surface(
        experiment,
        {"x": [0, 1, 2], "y": [0, 1], "regime": ["base", "stress"]},
        metric=lambda output: -output["loss"],
        error_policy="nan",
    )
    assert result.frame_count == 2
    assert np.isnan(result.z_values).sum() == 2
    assert len(result.metadata["errors"]) == 2

    with pytest.raises(ValueError, match="max_evaluations"):
        evaluate_parameter_surface(
            lambda x, y, a: x + y + a,
            {"x": range(10), "y": range(10), "a": range(10)},
            max_evaluations=100,
        )


def test_dataframe_multiple_frame_columns():
    rows = []
    for model in ["a", "b"]:
        for seed in [1, 2]:
            for x in [1, 2]:
                for y in [10, 20]:
                    rows.append({"x": x, "y": y, "model": model, "seed": seed, "score": x + y + seed})
    result = surface_from_dataframe(
        pd.DataFrame(rows),
        x="x",
        y="y",
        z="score",
        frame_cols=["model", "seed"],
    )
    assert result.frame_count == 4
    assert result.to_long_frame().shape[0] == 16


def test_quantlab_backtest_parameter_surface_multiple_frames(prices):
    lab = QuantLab(prices)
    result = lab.backtest_parameter_surface(
        "sma",
        {
            "fast": [5, 10],
            "slow": [20, 40],
            "costs_bps": [0, 5],
            "execution_delay": [0, 1],
        },
        x="fast",
        y="slow",
        animate_by=["costs_bps", "execution_delay"],
        metric="Sharpe",
    )
    assert result.frame_count == 4
    assert result.z_values.shape == (4, 2, 2)
