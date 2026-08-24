"""One-import stochastic simulation and Monte Carlo option pricing."""
from pathlib import Path

import asrquant as asr

OUTPUT = Path(__file__).with_name("monte_carlo_paths.png")
simulation = asr.simulate(
    "heston",
    initial=100,
    drift=0.03,
    initial_variance=0.04,
    mean_reversion=2.0,
    long_variance=0.04,
    vol_of_vol=0.5,
    correlation=-0.7,
    maturity=1,
    steps=252,
    paths=2_000,
    random_state=7,
)
print(simulation.summary)
asr.save(simulation, OUTPUT, kind="fan", dpi=150)

price = asr.european_option_mc(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.20,
    paths=100_000,
    antithetic=True,
    random_state=7,
)
print(price.summary)
