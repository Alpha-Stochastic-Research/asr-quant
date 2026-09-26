"""One-import martingale diagnostics on a controlled driftless process."""
from pathlib import Path

import asrquant as asr

OUTPUT = Path(__file__).with_name("martingale_diagnostics.png")
process = asr.arithmetic_brownian_motion(
    initial=100, drift=0, volatility=1, maturity=4, steps=1_000, paths=1, random_state=8
).paths.iloc[:, 0]
result = asr.martingale_diagnostics(process, rate=0, annualization=250, lags=10)
print(result.statistics)
print("Conclusion:", result.conclusion)
asr.save(result, OUTPUT, dpi=150)
