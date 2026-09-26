"""Guarded production workflow.

This example never submits a real order by default. It demonstrates the
fail-closed readiness and certificate flow using only ``import asrquant as asr``.
Replace evidence values only with verifiable deployment artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path

import asrquant as asr


STATE = Path("state")
STATE.mkdir(exist_ok=True)

policy = asr.LiveRiskPolicy(
    max_gross_leverage=1.0,
    max_position_weight=0.10,
    max_order_notional=5_000,
    max_daily_turnover=0.25,
    max_drawdown=0.05,
    minimum_cash=1_000,
    allow_short=False,
    max_daily_loss=0.02,
    max_open_orders=10,
    max_orders_per_minute=10,
    max_price_deviation_bps=50,
    max_market_data_age_seconds=2,
    max_capital=25_000,
    max_position_notional=2_500,
    symbol_allowlist=("SPY",),
)

# Defaults fail deliberately. Load actual evidence from a protected deployment
# pipeline instead of hard-coding approvals in application code.
evidence = asr.DeploymentEvidence(release_version=asr.__version__)
report = asr.ProductionReadinessGate().evaluate(evidence)
report.save(STATE / "readiness-report.json")

print("Ready for live capital:", report.ready)
for check in report.failed_required:
    print("BLOCKED:", check.code, "-", check.message)

# Paper endpoint is available without a deployment certificate. Credentials
# must be supplied through environment variables or a secret manager.
if os.getenv("RUN_ALPACA_PAPER") == "1":
    paper_broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials.from_environment(),
    )
    print(paper_broker.health())

# A real deployment may proceed only after report.ready is true, two named
# approvers issue a short-lived certificate, and the controlled runtime sets
# ASRQUANT_LIVE_TRADING=ENABLED. See docs/live_trading.md.
