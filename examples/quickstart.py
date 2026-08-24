"""One-import quickstart: simulation, backtest, chart, and report."""
import asrquant as asr

prices = asr.regime_switching_prices(periods=1_000, assets=4)
lab = asr.open_lab(prices)
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
print(result.metrics)
asr.save(result, "quickstart_dashboard.png", kind="dashboard", dpi=150)
asr.report(result, "quickstart_report.html")
