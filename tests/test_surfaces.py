from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from asrquant import QuantLab, evaluate_surface, evaluate_surface_animation


def _close(fig):
    assert fig is not None
    if hasattr(fig, "savefig"):
        plt.close(fig)


def test_generic_surface_and_animation(tmp_path):
    surface = evaluate_surface(
        lambda x, y: np.sin(x) * np.cos(y),
        x_values=np.linspace(0, 1, 5),
        y_values=np.linspace(0, 2, 4),
        x_name="gamma",
        y_name="cost",
        z_name="objective",
        call_style="positional",
    )
    assert surface.to_frame().shape == (4, 5)
    assert surface.summary["frames"] == 1
    _close(surface.plot("surface"))
    _close(surface.plot("heatmap"))
    _close(surface.plot("contour"))

    animated = evaluate_surface_animation(
        lambda x, y, t: np.sin(x + t) * np.cos(y),
        x_values=np.linspace(0, 1, 5),
        y_values=np.linspace(0, 2, 4),
        frame_values=[0.0, 0.5, 1.0],
        x_name="gamma",
        y_name="cost",
        frame_name="hedge_freq",
        z_name="objective",
        call_style="positional",
    )
    assert animated.frame_count == 3
    _close(animated.plot("surface", frame=1))
    html_path = animated.save_animation(tmp_path / "surface_animation.html", kind="heatmap")
    assert Path(html_path).exists()
    assert "<script" in Path(html_path).read_text(encoding="utf-8")


def test_lab_backtest_surface_and_animation(prices, tmp_path):
    lab = QuantLab(prices)
    surface = lab.backtest_surface(
        "sma",
        x_param="fast",
        x_values=[5, 10],
        y_param="slow",
        y_values=[20, 40],
        metric="Sharpe",
    )
    assert surface.to_frame().shape == (2, 2)
    _close(surface.plot("heatmap"))

    animated = lab.animate_backtest_surface(
        "sma",
        x_param="fast",
        x_values=[5, 10],
        y_param="slow",
        y_values=[20, 40],
        frame_param="execution_delay",
        frame_values=[0, 1],
        metric="Sharpe",
    )
    assert animated.frame_count == 2
    output = animated.save_animation(tmp_path / "backtest_animation.html", kind="contour")
    assert Path(output).exists()
