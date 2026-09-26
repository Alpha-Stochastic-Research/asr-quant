from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from asrquant import QuantLab, evaluate_parameter_surface, surface_from_dataframe


def _close(fig):
    assert fig is not None
    if hasattr(fig, "savefig"):
        plt.close(fig)


def test_parameter_surface_static_and_animated(tmp_path):
    static = evaluate_parameter_surface(
        lambda gamma, cost: np.cos(gamma) - 0.1 * cost,
        {"gamma": np.linspace(0.5, 2.0, 4), "cost": [0, 5, 10]},
        z_name="utility",
        call_style="keyword",
    )
    assert static.to_frame().shape == (3, 4)
    long = static.to_long_frame()
    assert set(long.columns) == {"gamma", "cost", "utility"}
    _close(static.plot("surface"))

    animated = evaluate_parameter_surface(
        lambda gamma, cost, hedge_freq: np.cos(gamma) - 0.1 * cost - 0.05 * hedge_freq,
        {
            "gamma": np.linspace(0.5, 2.0, 4),
            "cost": [0, 5, 10],
            "hedge_freq": [1, 5],
        },
        z_name="utility",
        call_style="keyword",
    )
    assert animated.frame_count == 2
    files = animated.export_frames(tmp_path / "frames", kind="heatmap")
    assert len(files) == 2
    assert all(Path(p).exists() for p in files)


def test_surface_from_dataframe_and_lab_helpers(prices, tmp_path):
    lab = QuantLab(prices)
    df = pd.DataFrame(
        {
            "gamma": [1, 1, 2, 2, 1, 1, 2, 2],
            "cost": [0, 5, 0, 5, 0, 5, 0, 5],
            "hedge": [1, 1, 1, 1, 2, 2, 2, 2],
            "score": [0.8, 0.6, 0.9, 0.7, 0.75, 0.55, 0.85, 0.65],
        }
    )
    surface = surface_from_dataframe(df, x="gamma", y="cost", z="score")
    assert surface.to_frame().shape == (2, 2)
    anim = lab.surface_from_frame(df, x="gamma", y="cost", z="score", frame_col="hedge")
    assert anim.frame_count == 2
    _close(anim.plot("contour", frame=1))

    generic = lab.parameter_surface(
        lambda gamma, cost, hedge: np.exp(-cost / 10) * np.cos(gamma / 4) - 0.2 * hedge,
        {
            "gamma": np.linspace(0.5, 5.0, 8),
            "cost": np.linspace(0.0, 10.0, 6),
            "hedge": [1, 2, 4],
        },
        z_name="utility",
        call_style="keyword",
    )
    out = generic.save_animation(tmp_path / "generic.html", kind="heatmap")
    assert Path(out).exists()
