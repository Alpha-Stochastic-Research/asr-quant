"""One-import comparison of derivative pricing models."""
import asrquant as asr

requests = {
    "Black-Scholes-Merton": ("black_scholes", dict(spot=100, strike=100, maturity=1, rate=0.03, volatility=0.20, option="call")),
    "Bachelier": ("bachelier", dict(forward=100, strike=100, maturity=1, rate=0.03, normal_volatility=10, option="call")),
    "Black-76": ("black76", dict(forward=100, strike=100, maturity=1, rate=0.03, volatility=0.20, option="call")),
    "CRR": ("crr", dict(spot=100, strike=100, maturity=1, rate=0.03, volatility=0.20, steps=1000, option="call")),
    "Monte Carlo": ("monte_carlo", dict(spot=100, strike=100, maturity=1, rate=0.03, volatility=0.20, paths=100_000, antithetic=True, random_state=7, option="call")),
}

for label, (model, parameters) in requests.items():
    print(f"\n{label}")
    print(asr.price_option(model, **parameters).summary)
