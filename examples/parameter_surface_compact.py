"""One-import compact deep-hedging-style parameter surface."""
from __future__ import annotations

import asrquant as asr


def main() -> None:
    lab = asr.open_lab("examples/sample_prices.csv", date_column="Date")
    surface = lab.parameter_surface(
        lambda gamma, cost_bps, hedge_freq: asr.math.exp(-cost_bps / 10) * asr.math.cos(gamma) - 0.1 * hedge_freq,
        {
            "gamma": asr.math.linspace(0.5, 5.0, 25),
            "cost_bps": asr.math.linspace(0, 20, 21),
            "hedge_freq": [1, 2, 4, 8],
        },
        z_name="utility",
    )
    asr.PlotHandle(surface.plot("surface", frame=0)).save("examples/parameter_surface_static.png", dpi=150)
    surface.save_animation("examples/parameter_surface_animation.html", kind="heatmap")


if __name__ == "__main__":
    main()
