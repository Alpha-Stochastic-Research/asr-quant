"""One-import parameter surfaces and animations."""
from __future__ import annotations

import asrquant as asr


def main() -> None:
    lab = asr.open_lab("examples/sample_prices.csv", date_column="Date")

    surface = lab.backtest_surface(
        "sma",
        x_param="fast",
        x_values=[5, 10, 20, 30],
        y_param="slow",
        y_values=[40, 80, 120, 160],
        metric="Sharpe",
    )
    asr.PlotHandle(surface.plot("surface")).save("examples/backtest_surface.png", dpi=150)

    animation = lab.animate_backtest_surface(
        "sma",
        x_param="fast",
        x_values=[5, 10, 20, 30],
        y_param="slow",
        y_values=[40, 80, 120, 160],
        frame_param="costs_bps",
        frame_values=[0, 5, 10, 20],
        metric="Sharpe",
    )
    animation.save_animation("examples/backtest_surface_animation.html", kind="heatmap")

    generic = lab.animate_surface(
        lambda gamma, transaction_cost_bps, hedge_frequency: (
            asr.math.exp(-transaction_cost_bps / 10)
            * asr.math.cos(gamma / 4)
            - 0.2 * hedge_frequency
        ),
        x_values=asr.math.linspace(0.5, 5.0, 20),
        y_values=asr.math.linspace(0.0, 10.0, 20),
        frame_values=[1, 2, 4, 8],
        x_name="gamma",
        y_name="transaction_cost_bps",
        frame_name="hedge_frequency",
        z_name="utility",
    )
    generic.save_animation("examples/generic_surface_animation.html", kind="surface")


if __name__ == "__main__":
    main()
