from __future__ import annotations

from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from asrquant import BacktestSpec, QuantLab
from asrquant.simulation import regime_switching_prices
from asrquant.viz import derivatives, general

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# Main reproducible experiment
prices = regime_switching_prices(periods=1500, assets=4, random_state=7)
lab = QuantLab(prices)
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5, execution_delay=1)
result.metrics.to_csv(ROOT / "benchmarks" / "baseline_metrics.csv", header=["value"])
result.to_frame().to_csv(ROOT / "benchmarks" / "baseline_timeseries.csv")
fig = result.plot("dashboard")
fig.savefig(OUT / "dashboard.png", dpi=180, bbox_inches="tight")
plt.close(fig)
result.report(str(ROOT / "examples" / "asrquant_demo_report.html"), title="ASRQuant reproducible demonstration")

# Implementation audit
weights = lab.strategy("sma", fast=20, slow=100)
audit = lab.audit(
    weights,
    execution_delays=(0, 1, 2),
    linear_costs_bps=(0.0, 5.0, 10.0, 25.0),
    rebalances=("bar", "ME"),
)
audit.summary.to_csv(ROOT / "benchmarks" / "implementation_audit.csv")
audit.diagnostics.to_csv(ROOT / "benchmarks" / "implementation_audit_diagnostics.csv", header=["value"])
fig = audit.plot()
fig.savefig(OUT / "implementation_audit.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# Parameter landscape
rows = []
for fast in (5, 10, 20, 40):
    for slow in (60, 100, 150, 200):
        if fast >= slow:
            continue
        r = lab.backtest("sma", fast=fast, slow=slow, costs_bps=5, execution_delay=1)
        rows.append({"fast": fast, "slow": slow, "Sharpe": r.metrics["Sharpe"], "CAGR": r.metrics["CAGR"], "Max Drawdown": r.metrics["Max Drawdown"]})
landscape = pd.DataFrame(rows)
landscape.to_csv(ROOT / "benchmarks" / "parameter_landscape.csv", index=False)
table = landscape.pivot(index="slow", columns="fast", values="Sharpe")
fig = general.surface3d(table.columns.to_numpy(), table.index.to_numpy(), table.to_numpy(), title="SMA Sharpe parameter surface", x_label="Fast window", y_label="Slow window", z_label="Sharpe")
fig.savefig(OUT / "parameter_surface.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# Derivatives surface
strikes = np.linspace(70, 130, 31)
maturities = np.linspace(0.05, 2.0, 25)
kk, tt = np.meshgrid(strikes, maturities)
iv = 0.18 + 0.00007 * (kk - 100) ** 2 + 0.025 * np.exp(-tt)
fig = derivatives.volatility_surface(strikes, maturities, iv)
fig.savefig(OUT / "volatility_surface.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# Runtime scaling benchmark. Median of five runs.
bench_rows = []
for periods, assets in [(1_000, 1), (1_000, 10), (5_000, 10), (5_000, 50), (20_000, 50)]:
    p = regime_switching_prices(periods=periods, assets=assets, random_state=periods + assets)
    q = QuantLab(p)
    timings = []
    for _ in range(5):
        start = perf_counter()
        q.backtest("sma", fast=20, slow=100, costs_bps=5)
        timings.append(perf_counter() - start)
    bench_rows.append({"periods": periods, "assets": assets, "cells": periods * assets, "median_seconds": float(np.median(timings)), "min_seconds": float(np.min(timings))})
bench = pd.DataFrame(bench_rows)
bench.to_csv(ROOT / "benchmarks" / "runtime_scaling.csv", index=False)

print("BASELINE")
print(result.metrics.to_string())
print("\nAUDIT")
print(audit.diagnostics.to_string())
print("\nRUNTIME")
print(bench.to_string(index=False))
