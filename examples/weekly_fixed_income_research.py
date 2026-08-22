"""Minimal Friday-to-Friday fixed-income research-discovery example."""
from pathlib import Path

import numpy as np
import pandas as pd
import asrquant as asr

rng = np.random.default_rng(7)
dates = pd.bdate_range("2024-01-01", periods=400)
maturities = np.array([0.25, 0.5, 1, 2, 5, 10, 30.0])
base = 0.025 + 0.002 * np.log1p(maturities)
changes = rng.normal(0, 0.0004, (len(dates), len(maturities)))
changes[260:, 3:5] *= 2.5
curves = pd.DataFrame(base + np.cumsum(changes, axis=0), index=dates, columns=maturities)

board = asr.discovery.weekly(data=curves, domain="fixed_income", n=8)
print(board.to_frame()[["candidate_id", "title", "priority_score", "novelty_status"]])

cycle = asr.weekly_cycle(board, 0, launch_friday="2026-08-14")
print(cycle.plan[["date", "stage", "deliverable"]])

output = cycle.publication_pack(Path("weekly_research") / cycle.candidate.candidate_id)
print(f"Publication pack: {output}")
