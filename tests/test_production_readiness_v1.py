from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

import pytest
import requests

import asrquant as asr


SECRET = "x" * 64


def ready_evidence(**changes: Any) -> asr.DeploymentEvidence:
    payload = dict(
        release_version="1.0.0",
        ci_passed=True,
        test_count=120,
        coverage_percent=92.0,
        static_analysis_passed=True,
        dependency_scan_passed=True,
        secrets_scan_passed=True,
        sbom_present=True,
        artifacts_signed=True,
        reproducible_build_verified=True,
        disaster_recovery_tested=True,
        rollback_tested=True,
        monitoring_enabled=True,
        alerting_enabled=True,
        durable_audit_log_enabled=True,
        time_synchronization_verified=True,
        broker_paper_days=45,
        broker_paper_orders=1000,
        reconciliation_mismatches=0,
        unresolved_critical_incidents=0,
        operator_approved=True,
        legal_compliance_reviewed=True,
        data_licenses_reviewed=True,
        strategy_owner_approved=True,
        model_validation_approved=True,
        change_ticket="CHG-2026-001",
    )
    payload.update(changes)
    return asr.DeploymentEvidence(**payload)


def certificate(policy: asr.LiveRiskPolicy | None = None) -> asr.DeploymentCertificate:
    policy = policy or asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",))
    evidence = ready_evidence()
    report = asr.ProductionReadinessGate().evaluate(evidence)
    return asr.DeploymentCertificate.issue(
        report=report,
        evidence=evidence,
        secret_key=SECRET,
        release_version=asr.__version__,
        broker="alpaca",
        account_id="ACCOUNT-1",
        account_salt="deployment-salt",
        risk_policy=policy,
        max_live_capital=100_000,
        approved_by=("risk-owner", "operations-owner"),
        validity_hours=24,
    )


def test_default_evidence_fails_closed():
    evidence = asr.DeploymentEvidence(release_version=asr.__version__)
    report = asr.ProductionReadinessGate().evaluate(evidence)
    assert not report.ready
    assert len(report.failed_required) > 20


def test_complete_evidence_passes():
    report = asr.ProductionReadinessGate().evaluate(ready_evidence())
    assert report.ready
    assert not report.failed_required


@pytest.mark.parametrize(
    "field,value",
    [
        ("ci_passed", False),
        ("coverage_percent", 89.9),
        ("dependency_scan_passed", False),
        ("disaster_recovery_tested", False),
        ("broker_paper_days", 29),
        ("broker_paper_orders", 499),
        ("reconciliation_mismatches", 1),
        ("legal_compliance_reviewed", False),
        ("model_validation_approved", False),
        ("change_ticket", ""),
    ],
)
def test_each_critical_gate_fails(field: str, value: Any):
    report = asr.ProductionReadinessGate().evaluate(ready_evidence(**{field: value}))
    assert not report.ready


def test_certificate_requires_ready_report():
    evidence = ready_evidence(ci_passed=False)
    report = asr.ProductionReadinessGate().evaluate(evidence)
    with pytest.raises(PermissionError):
        asr.DeploymentCertificate.issue(
            report=report,
            evidence=evidence,
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="salt",
            risk_policy=asr.LiveRiskPolicy(),
            max_live_capital=1000,
            approved_by=("a", "b"),
        )


def test_certificate_requires_two_approvers():
    evidence = ready_evidence()
    report = asr.ProductionReadinessGate().evaluate(evidence)
    with pytest.raises(ValueError):
        asr.DeploymentCertificate.issue(
            report=report,
            evidence=evidence,
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="salt",
            risk_policy=asr.LiveRiskPolicy(),
            max_live_capital=1000,
            approved_by=("single",),
        )


def test_certificate_round_trip(tmp_path: Path):
    cert = certificate()
    path = cert.save(tmp_path / "certificate.json")
    loaded = asr.DeploymentCertificate.load(path)
    assert loaded.signature == cert.signature
    assert loaded.approved_by == cert.approved_by


def test_certificate_detects_tampering():
    cert = certificate()
    cert.max_live_capital += 1
    with pytest.raises(PermissionError, match="signature"):
        cert.verify(
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="deployment-salt",
            risk_policy=asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",)),
            requested_capital=1000,
        )


def test_certificate_detects_account_mismatch():
    cert = certificate()
    with pytest.raises(PermissionError, match="account"):
        cert.verify(
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="OTHER",
            account_salt="deployment-salt",
            risk_policy=asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",)),
            requested_capital=1000,
        )


def test_certificate_detects_policy_mismatch():
    cert = certificate()
    with pytest.raises(PermissionError, match="policy"):
        cert.verify(
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="deployment-salt",
            risk_policy=asr.LiveRiskPolicy(max_capital=50_000, symbol_allowlist=("SPY",)),
            requested_capital=1000,
        )


def test_certificate_detects_expiry():
    cert = certificate()
    future = datetime.now(timezone.utc) + timedelta(days=2)
    with pytest.raises(PermissionError, match="expired"):
        cert.verify(
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="deployment-salt",
            risk_policy=asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",)),
            requested_capital=1000,
            now=future,
        )


def test_certificate_rejects_excess_capital():
    cert = certificate()
    with pytest.raises(PermissionError, match="capital"):
        cert.verify(
            secret_key=SECRET,
            release_version=asr.__version__,
            broker="alpaca",
            account_id="ACCOUNT-1",
            account_salt="deployment-salt",
            risk_policy=asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",)),
            requested_capital=100_001,
        )


def test_audit_store_is_idempotent_and_chain_valid(tmp_path: Path):
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    first = store.append("test", {"value": 1}, idempotency_key="same")
    second = store.append("test", {"value": 2}, idempotency_key="same")
    assert first.event_id == second.event_id
    assert len(store.events()) == 1
    assert store.verify_chain() == (True, None)
    store.close()


def test_audit_store_backup(tmp_path: Path):
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    store.append("test", {"value": 1})
    backup = store.backup(tmp_path / "backup.db")
    store.close()
    reopened = asr.SQLiteAuditStore(backup)
    assert len(reopened.events()) == 1
    assert reopened.verify_chain()[0]
    reopened.close()


def test_audit_chain_detects_tampering(tmp_path: Path):
    import sqlite3

    path = tmp_path / "audit.db"
    store = asr.SQLiteAuditStore(path)
    store.append("one", {"x": 1})
    store.append("two", {"x": 2})
    store.close()
    connection = sqlite3.connect(path)
    connection.execute("UPDATE audit_events SET payload_json = ? WHERE sequence = 1", ('{"x":999}',))
    connection.commit()
    connection.close()
    reopened = asr.SQLiteAuditStore(path)
    assert reopened.verify_chain() == (False, 1)
    reopened.close()


def healthy_context(symbol: str = "SPY"):
    market = asr.MarketDataSnapshot(symbol, 100.0, datetime.now(timezone.utc), source="test")
    account = asr.AccountSnapshot("A", 100_000, 100_000, 50_000, 100_000, False, False)
    health = asr.BrokerHealth(
        asr.HealthState.HEALTHY,
        "fake",
        asr.BrokerEnvironment.PAPER,
        1.0,
        True,
        True,
    )
    return market, account, health


def test_pretrade_approves_valid_order():
    policy = asr.LiveRiskPolicy(max_order_notional=20_000, symbol_allowlist=("SPY",))
    engine = asr.PreTradeRiskEngine(policy)
    market, account, health = healthy_context()
    decision = engine.evaluate(
        asr.Order("SPY", 10, asr.OrderSide.BUY),
        market=market,
        account=account,
        positions={},
        open_orders=[],
        health=health,
    )
    assert decision.approved


@pytest.mark.parametrize(
    "order,market_transform,policy,expected_code",
    [
        (
            asr.Order("QQQ", 1, asr.OrderSide.BUY),
            lambda m: asr.MarketDataSnapshot("QQQ", m.price, m.timestamp),
            asr.LiveRiskPolicy(symbol_allowlist=("SPY",)),
            "symbol_not_allowed",
        ),
        (
            asr.Order("SPY", 1000, asr.OrderSide.BUY),
            lambda m: m,
            asr.LiveRiskPolicy(max_order_notional=1000),
            "order_notional_limit",
        ),
        (
            asr.Order("SPY", 1, asr.OrderSide.BUY, limit_price=150),
            lambda m: m,
            asr.LiveRiskPolicy(max_price_deviation_bps=100),
            "price_collar",
        ),
        (
            asr.Order("SPY", 1, asr.OrderSide.BUY),
            lambda m: asr.MarketDataSnapshot(
                "SPY", 100, datetime.now(timezone.utc) - timedelta(minutes=1)
            ),
            asr.LiveRiskPolicy(max_market_data_age_seconds=1),
            "stale_market_data",
        ),
    ],
)
def test_pretrade_rejects_common_risks(order, market_transform, policy, expected_code):
    engine = asr.PreTradeRiskEngine(policy)
    market, account, health = healthy_context()
    decision = engine.evaluate(
        order,
        market=market_transform(market),
        account=account,
        positions={},
        open_orders=[],
        health=health,
    )
    assert not decision.approved
    assert expected_code in decision.codes


def test_pretrade_rejects_duplicate_order_id():
    engine = asr.PreTradeRiskEngine(asr.LiveRiskPolicy())
    market, account, health = healthy_context()
    order = asr.Order("SPY", 1, asr.OrderSide.BUY, order_id="DUPLICATE")
    assert engine.evaluate(order, market=market, account=account, positions={}, open_orders=[], health=health).approved
    second = engine.evaluate(order, market=market, account=account, positions={}, open_orders=[], health=health)
    assert "duplicate_order" in second.codes


def test_pretrade_rejects_daily_loss():
    engine = asr.PreTradeRiskEngine(asr.LiveRiskPolicy(max_daily_loss=0.02))
    market, _, health = healthy_context()
    account = asr.AccountSnapshot("A", 95_000, 100_000, 50_000, 100_000, False, False)
    decision = engine.evaluate(
        asr.Order("SPY", 1, asr.OrderSide.BUY),
        market=market,
        account=account,
        positions={},
        open_orders=[],
        health=health,
    )
    assert "daily_loss_limit" in decision.codes


def test_pretrade_rejects_market_closed():
    engine = asr.PreTradeRiskEngine(asr.LiveRiskPolicy(require_market_open=True))
    market, account, _ = healthy_context()
    health = asr.BrokerHealth(
        asr.HealthState.HEALTHY,
        "fake",
        asr.BrokerEnvironment.PAPER,
        1.0,
        False,
        True,
    )
    decision = engine.evaluate(
        asr.Order("SPY", 1, asr.OrderSide.BUY),
        market=market,
        account=account,
        positions={},
        open_orders=[],
        health=health,
    )
    assert "market_closed" in decision.codes


def test_kill_switch_persists(tmp_path: Path):
    switch = asr.PersistentKillSwitch(tmp_path / "kill.json")
    assert not switch.active
    switch.activate("test", operator="unit")
    assert asr.PersistentKillSwitch(tmp_path / "kill.json").active
    with pytest.raises(PermissionError):
        switch.clear(operator="unit", authorization="wrong")
    switch.clear(operator="unit", authorization="CLEAR_KILL_SWITCH")
    assert not switch.active


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200, request_id: str = "REQ-1"):
        self._payload = payload
        self.status_code = status_code
        self.headers = {"X-Request-ID": request_id}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class FakeSession:
    def __init__(self):
        self.calls = []
        self.orders: dict[str, dict[str, Any]] = {}

    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        self.calls.append((method, url, headers, params, json, timeout))
        if url.endswith("/v2/account"):
            return FakeResponse(
                {
                    "account_number": "ACCOUNT-1",
                    "equity": "100000",
                    "last_equity": "100000",
                    "cash": "100000",
                    "buying_power": "100000",
                    "trading_blocked": False,
                    "account_blocked": False,
                }
            )
        if url.endswith("/v2/clock"):
            return FakeResponse({"is_open": True})
        if url.endswith("/v2/positions"):
            return FakeResponse([])
        if "/v2/orders:by_client_order_id" in url:
            client_id = (params or {}).get("client_order_id")
            if client_id not in self.orders:
                return FakeResponse({"message": "not found"}, 404)
            return FakeResponse(self.orders[client_id])
        if url.endswith("/v2/orders") and method == "GET":
            return FakeResponse([])
        if url.endswith("/v2/orders") and method == "POST":
            payload = {
                "id": "BROKER-1",
                "client_order_id": json["client_order_id"],
                "symbol": json["symbol"],
                "qty": json["qty"],
                "side": json["side"],
                "type": json["type"],
                "status": "accepted",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "filled_qty": "0",
            }
            self.orders[payload["client_order_id"]] = payload
            return FakeResponse(payload)
        if "/v2/orders/" in url and method == "DELETE":
            return FakeResponse(None, 204)
        raise AssertionError((method, url))


def test_alpaca_paper_uses_paper_endpoint_and_redacts_credentials():
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"),
        session=session,
    )
    broker.account()
    assert session.calls[0][1].startswith(asr.AlpacaBroker.PAPER_URL)
    assert "SECRET" not in repr(broker)


def test_direct_live_broker_construction_is_blocked():
    with pytest.raises(PermissionError):
        asr.AlpacaBroker(
            credentials=asr.BrokerCredentials("KEY", "SECRET"),
            environment=asr.BrokerEnvironment.LIVE,
        )


def test_alpaca_live_requires_environment_arm(monkeypatch):
    policy = asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",))
    cert = certificate(policy)
    monkeypatch.delenv("ASRQUANT_LIVE_TRADING", raising=False)
    with pytest.raises(PermissionError, match="ASRQUANT_LIVE_TRADING"):
        asr.AlpacaBroker.live(
            certificate=cert,
            certificate_secret=SECRET,
            account_id="ACCOUNT-1",
            account_salt="deployment-salt",
            risk_policy=policy,
            requested_capital=50_000,
            credentials=asr.BrokerCredentials("KEY", "SECRET"),
            session=FakeSession(),
        )


def test_alpaca_live_authorized(monkeypatch):
    policy = asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",))
    cert = certificate(policy)
    monkeypatch.setenv("ASRQUANT_LIVE_TRADING", "ENABLED")
    broker = asr.AlpacaBroker.live(
        certificate=cert,
        certificate_secret=SECRET,
        account_id="ACCOUNT-1",
        account_salt="deployment-salt",
        risk_policy=policy,
        requested_capital=50_000,
        credentials=asr.BrokerCredentials("KEY", "SECRET"),
        session=FakeSession(),
    )
    assert broker.environment == asr.BrokerEnvironment.LIVE


def test_alpaca_order_is_idempotent_by_client_id():
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    order = asr.Order("SPY", 1, asr.OrderSide.BUY, order_id="CLIENT-1")
    first = broker.submit_order(order)
    recovered = broker.get_order("CLIENT-1")
    assert first.broker_order_id == recovered.broker_order_id


def test_live_engine_submits_and_audits(tmp_path: Path):
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    engine = asr.LiveTradingEngine(
        broker=broker,
        policy=asr.LiveRiskPolicy(max_order_notional=10_000, symbol_allowlist=("SPY",)),
        audit_store=store,
        kill_switch=asr.PersistentKillSwitch(tmp_path / "kill.json"),
    )
    receipt = engine.submit(
        asr.Order("SPY", 1, asr.OrderSide.BUY, order_id="ORDER-1"),
        asr.MarketDataSnapshot("SPY", 100, datetime.now(timezone.utc)),
    )
    assert receipt.status == "accepted"
    assert store.latest("broker_order_receipt") is not None
    assert store.verify_chain()[0]
    store.close()


def test_live_engine_blocks_when_kill_switch_active(tmp_path: Path):
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    switch = asr.PersistentKillSwitch(tmp_path / "kill.json")
    switch.activate("manual", operator="risk")
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    engine = asr.LiveTradingEngine(
        broker=broker,
        policy=asr.LiveRiskPolicy(symbol_allowlist=("SPY",)),
        audit_store=store,
        kill_switch=switch,
    )
    with pytest.raises(PermissionError, match="kill switch"):
        engine.submit(
            asr.Order("SPY", 1, asr.OrderSide.BUY),
            asr.MarketDataSnapshot("SPY", 100, datetime.now(timezone.utc)),
        )
    store.close()


def test_reconciliation_mismatch_activates_kill_switch(tmp_path: Path):
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    switch = asr.PersistentKillSwitch(tmp_path / "kill.json")
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    engine = asr.LiveTradingEngine(
        broker=broker,
        policy=asr.LiveRiskPolicy(),
        audit_store=store,
        kill_switch=switch,
    )
    report = engine.reconcile(expected_positions={"SPY": 1}, expected_cash=100_000)
    assert not report.matched
    assert switch.active
    store.close()


def test_health_snapshot_contains_control_states(tmp_path: Path):
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=FakeSession()
    )
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    engine = asr.LiveTradingEngine(
        broker=broker,
        policy=asr.LiveRiskPolicy(),
        audit_store=store,
        kill_switch=asr.PersistentKillSwitch(tmp_path / "kill.json"),
    )
    snapshot = engine.health_snapshot()
    assert snapshot["broker_state"] == "healthy"
    assert snapshot["audit_chain_valid"] is True
    store.close()

@pytest.mark.parametrize(
    "policy",
    [
        asr.LiveRiskPolicy(max_daily_loss=0),
        asr.LiveRiskPolicy(max_open_orders=0),
        asr.LiveRiskPolicy(max_orders_per_minute=0),
        asr.LiveRiskPolicy(max_price_deviation_bps=0),
        asr.LiveRiskPolicy(max_market_data_age_seconds=0),
        asr.LiveRiskPolicy(max_capital=0),
        asr.LiveRiskPolicy(max_position_notional=0),
        asr.LiveRiskPolicy(reconciliation_quantity_tolerance=-1),
        asr.LiveRiskPolicy(max_consecutive_broker_failures=0),
        asr.LiveRiskPolicy(symbol_allowlist=("SPY",), symbol_denylist=("SPY",)),
    ],
)
def test_live_risk_policy_rejects_invalid_controls(policy):
    with pytest.raises(ValueError):
        policy.validate()


def test_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY_ID", "KEY")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "SECRET")
    credentials = asr.BrokerCredentials.from_environment()
    assert credentials.api_key == "KEY"
    monkeypatch.delenv("ALPACA_API_SECRET_KEY")
    with pytest.raises(ValueError):
        asr.BrokerCredentials.from_environment()


def test_account_daily_loss_with_invalid_last_equity():
    account = asr.AccountSnapshot("A", 0, 0, 0, 0, False, False)
    assert account.daily_loss_fraction == 1.0


def test_readiness_report_save_and_warning_properties(tmp_path: Path):
    report = asr.ProductionReadinessReport(
        [
            asr.ReadinessCheck(
                "warning",
                asr.CheckState.WARN,
                asr.CheckLevel.ADVISORY,
                "warning",
            )
        ]
    )
    assert report.ready
    assert len(report.warnings) == 1
    path = report.save(tmp_path / "report.json")
    assert json.loads(path.read_text())["ready"] is True


def test_certificate_rejects_short_secret():
    evidence = ready_evidence()
    report = asr.ProductionReadinessGate().evaluate(evidence)
    with pytest.raises(ValueError, match="32 bytes"):
        asr.DeploymentCertificate.issue(
            report=report,
            evidence=evidence,
            secret_key="short",
            release_version=asr.__version__,
            broker="alpaca",
            account_id="A",
            account_salt="salt",
            risk_policy=asr.LiveRiskPolicy(),
            max_live_capital=1000,
            approved_by=("a", "b"),
        )


def test_certificate_rejects_version_broker_environment_and_not_yet_valid():
    policy = asr.LiveRiskPolicy(max_capital=100_000, symbol_allowlist=("SPY",))
    cert = certificate(policy)
    common = dict(
        secret_key=SECRET,
        account_id="ACCOUNT-1",
        account_salt="deployment-salt",
        risk_policy=policy,
        requested_capital=1000,
    )
    with pytest.raises(PermissionError, match="version"):
        cert.verify(release_version="9.9.9", broker="alpaca", **common)
    with pytest.raises(PermissionError, match="broker"):
        cert.verify(release_version=asr.__version__, broker="other", **common)
    with pytest.raises(PermissionError, match="environment"):
        cert.verify(
            release_version=asr.__version__,
            broker="alpaca",
            environment_fingerprint="other",
            **common,
        )
    before_issue = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(PermissionError, match="not yet"):
        cert.verify(
            release_version=asr.__version__,
            broker="alpaca",
            now=before_issue,
            **common,
        )


def test_audit_store_query_checkpoint_context_and_latest(tmp_path: Path):
    path = tmp_path / "audit.db"
    with asr.SQLiteAuditStore(path) as store:
        store.append("a", {"n": 1})
        store.append("b", {"n": 2})
        store.append("a", {"n": 3})
        assert [e.payload["n"] for e in store.events(event_type="a", limit=1)] == [1]
        assert [e.payload["n"] for e in store.events(after_sequence=1)] == [2, 3]
        assert store.events(limit=0) == []
        assert store.latest("b").payload["n"] == 2
        store.checkpoint()


def test_alpaca_get_missing_order_and_cancel(tmp_path: Path):
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    assert broker.get_order("MISSING") is None
    assert broker.cancel_order("BROKER-1") is True


class FailingSession(FakeSession):
    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        if url.endswith("/v2/account"):
            raise requests.ConnectionError("offline")
        return super().request(method, url, headers, params, json, timeout)


def test_alpaca_health_failure_is_fail_closed():
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=FailingSession()
    )
    health = broker.health()
    assert health.state == asr.HealthState.UNHEALTHY
    assert health.account_reachable is False


def test_pretrade_rejects_account_and_open_order_controls():
    policy = asr.LiveRiskPolicy(max_open_orders=1)
    engine = asr.PreTradeRiskEngine(policy)
    market, _, health = healthy_context()
    blocked = asr.AccountSnapshot("A", 100_000, 100_000, 0, 0, True, False)
    open_receipt = asr.BrokerOrderReceipt(
        "B", "C", "SPY", 1, "buy", "market", "accepted", datetime.now(timezone.utc).isoformat()
    )
    decision = engine.evaluate(
        asr.Order("SPY", 1, asr.OrderSide.BUY),
        market=market,
        account=blocked,
        positions={},
        open_orders=[open_receipt],
        health=health,
    )
    assert "account_blocked" in decision.codes
    assert "open_order_limit" in decision.codes
    assert "buying_power" in decision.codes


def test_pretrade_rejects_short_position_and_position_notional():
    policy = asr.LiveRiskPolicy(
        allow_short=False,
        max_position_notional=50,
        max_position_weight=1.0,
    )
    engine = asr.PreTradeRiskEngine(policy)
    market, account, health = healthy_context()
    decision = engine.evaluate(
        asr.Order("SPY", 1, asr.OrderSide.SELL),
        market=market,
        account=account,
        positions={},
        open_orders=[],
        health=health,
    )
    assert "short_not_allowed" in decision.codes
    assert "position_notional_limit" in decision.codes


def test_reconciliation_match_does_not_activate_kill_switch(tmp_path: Path):
    session = FakeSession()
    broker = asr.AlpacaBroker.paper(
        credentials=asr.BrokerCredentials("KEY", "SECRET"), session=session
    )
    switch = asr.PersistentKillSwitch(tmp_path / "kill.json")
    store = asr.SQLiteAuditStore(tmp_path / "audit.db")
    engine = asr.LiveTradingEngine(
        broker=broker,
        policy=asr.LiveRiskPolicy(),
        audit_store=store,
        kill_switch=switch,
    )
    report = engine.reconcile(expected_positions={}, expected_cash=100_000)
    assert report.matched
    assert not switch.active
    store.close()
