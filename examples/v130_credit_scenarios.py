"""ASRQuant 1.3 credit and rate-scenario example."""
from __future__ import annotations

import asrquant as asr

curve = asr.rates.DiscountCurve.from_zero_rates(
    [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
    [0.020, 0.0205, 0.0210, 0.0215, 0.0220, 0.0225, 0.0230, 0.0235],
)
hazard = asr.credit.bootstrap_hazard_curve(
    curve,
    maturities=[1.0, 3.0, 5.0],
    spreads=[0.0080, 0.0110, 0.0140],
    recovery=0.40,
)
cds = asr.credit.CDS(5.0, 0.0140, notional=1_000_000, recovery=0.40)
print(cds.analytics(curve, hazard).summary.to_string())

swap = asr.rates.InterestRateSwap(5.0, 0.0250, notional=5_000_000)
scenario = asr.scenarios.steepener(25.0)
result = asr.scenarios.run(scenario, instrument=swap, curve=curve)
print("\nSCENARIO")
print(result.summary.to_string())
