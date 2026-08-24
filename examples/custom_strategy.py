"""One-import custom strategy example."""
import asrquant as asr


def cross_sectional_trend(prices, window=60):
    score = prices / prices.shift(window) - 1
    centered = score.sub(score.mean(axis=1), axis=0)
    return centered.div(centered.abs().sum(axis=1), axis=0).fillna(0)


prices = asr.regime_switching_prices(periods=1_000, assets=8)
lab = asr.open_lab(prices)
result = lab.backtest(cross_sectional_trend, window=60, costs_bps=8)
print(result.metrics)
