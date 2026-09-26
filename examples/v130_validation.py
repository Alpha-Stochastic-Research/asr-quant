"""ASRQuant 1.3 research-validation example with deterministic synthetic strategies."""
from __future__ import annotations

import numpy as np
import pandas as pd
import asrquant as asr

rng = np.random.default_rng(42)
n = 600
common = rng.normal(0.0, 0.008, n)
strategies = pd.DataFrame(
    {
        "candidate_a": common + rng.normal(0.00015, 0.004, n),
        "candidate_b": common + rng.normal(0.00005, 0.004, n),
        "candidate_c": common + rng.normal(-0.00005, 0.004, n),
        "candidate_d": common + rng.normal(0.00000, 0.004, n),
    }
)

pbo = asr.validation.probability_of_backtest_overfitting(strategies, n_groups=6)
reality = asr.validation.reality_check(strategies, n_boot=200, random_state=42)
spa = asr.validation.spa_test(strategies, n_boot=200, random_state=42)

study = asr.validation.Multiverse(
    choices={"lookback": [20, 60, 120], "cost_bps": [0, 5, 10]},
    evaluator=lambda lookback, cost_bps: {"metric": 1.0 / np.sqrt(lookback) - cost_bps / 1000.0},
).run()

print("PBO")
print(pbo.summary.to_string())
print("\nREALITY CHECK")
print(reality.summary.to_string())
print("\nSPA")
print(spa.summary.to_string())
print("\nMULTIVERSE")
print(study.summary.to_string())
