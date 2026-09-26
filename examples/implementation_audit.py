"""One-import implementation audit."""
import asrquant as asr

prices = asr.regime_switching_prices(periods=500, assets=3, random_state=7)
lab = asr.open_lab(prices)
audit = lab.audit(
    "sma",
    fast=10,
    slow=40,
    execution_delays=(0, 1),
    linear_costs_bps=(0, 5, 10),
)
print(audit.summary[["Total Return", "Sharpe", "Max Drawdown"]])
print(audit.diagnostics)
asr.save(audit, "implementation_audit.png", dpi=150)
