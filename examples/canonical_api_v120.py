"""ASRQuant 1.2 canonical public API — compact end-to-end example."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

import asrquant as asr

rng = np.random.default_rng(4)
index = pd.date_range("2024-01-02", periods=300, freq="B")
returns = pd.DataFrame(rng.normal(0.0002, 0.01, (300, 3)), index=index, columns=["A", "B", "C"])
prices = 100 * np.exp(returns.cumsum())

quality = asr.data.validate(prices)
portfolio = asr.portfolio.optimize(returns, method="minimum_variance")
weights = pd.DataFrame(np.tile(portfolio.weights, (len(prices), 1)), index=index, columns=prices.columns)
backtest = asr.backtesting.run(prices, weights)

option = asr.options.price(
    "black_scholes",
    spot=100,
    strike=100,
    maturity=1.0,
    rate=0.03,
    volatility=0.20,
)

features = pd.DataFrame({"r1": returns.A, "r5": prices.A.pct_change(5)}, index=index)
target = returns.A.shift(-1)
model = asr.ml.fit(Ridge(), features, target, train_size=120, test_size=30)

print(quality.summary)
print(portfolio.summary)
print(backtest.summary)
print(option.summary)
print(model.summary)
