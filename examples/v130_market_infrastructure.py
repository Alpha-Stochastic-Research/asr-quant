"""ASRQuant 1.3 market-infrastructure example using deterministic local quotes."""
from __future__ import annotations

import asrquant as asr

builder = asr.rates.CurveBuilder.from_quotes(
    deposits={0.25: 0.0210, 0.50: 0.0220},
    swaps={1.0: 0.0230, 2.0: 0.0240, 5.0: 0.0260},
    valuation_date="2026-09-15",
)
build = builder.build()

swap = asr.rates.InterestRateSwap(
    maturity=5.0,
    fixed_rate=0.0260,
    notional=10_000_000,
)
risk = asr.rates.curve_risk(swap, build.curve, build_result=build)
stressed = asr.rates.curve_scenario(build.curve, parallel_bp=25, slope_bp=10)
explain = asr.rates.pnl_explain(swap, build.curve, stressed)

print("CURVE")
print(build.summary.to_string())
print("\nQUOTE PV01")
print(risk.quote_pv01.to_string())
print("\nP&L EXPLAIN")
print(explain.contributions.to_string())
