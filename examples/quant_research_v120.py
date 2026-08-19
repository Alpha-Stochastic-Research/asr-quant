"""ASRQuant 1.2 cross-sectional research -> risk -> microstructure example."""
from __future__ import annotations

import numpy as np
import pandas as pd
import asrquant as asr

rng = np.random.default_rng(7)
index = pd.date_range("2025-01-01", periods=320, freq="B")
assets = [f"Asset{i:02d}" for i in range(20)]
returns = pd.DataFrame(
    rng.normal(0.0002, 0.01, size=(len(index), len(assets))),
    index=index,
    columns=assets,
)
prices = 100.0 * (1.0 + returns).cumprod()

raw_signal = prices.pct_change(20, fill_method=None).shift(1)
signal = asr.alpha.cross_sectional_zscore(raw_signal)
forward_5d = asr.alpha.forward_returns(prices, 5)[5]
alpha_report = asr.alpha.analyze_signal(signal, forward_5d, quantiles=5, min_assets=15)

weights = alpha_report.weights.iloc[-1]
risk_report = asr.risk.portfolio_risk_report(returns.tail(252), weights)

mid = pd.Series(100 + np.cumsum(rng.normal(0, 0.01, 100)))
bid, ask = mid - 0.01, mid + 0.01
bid_size = pd.Series(rng.integers(10, 100, size=len(mid)), dtype=float)
ask_size = pd.Series(rng.integers(10, 100, size=len(mid)), dtype=float)

print("Alpha summary")
print(alpha_report.summary)
print("\nRisk summary")
print(risk_report.summary)
print("\nMicroprice head")
print(asr.microstructure.microprice(bid, ask, bid_size, ask_size).head())
