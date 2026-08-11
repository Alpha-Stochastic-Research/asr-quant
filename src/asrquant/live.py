"""Guarded live-trading execution primitives.

This module is designed to make accidental live trading difficult. The live
Alpaca adapter can only be created through :meth:`AlpacaBroker.live`, which
verifies a signed deployment certificate. Every order passes deterministic
pre-trade controls and is written to a tamper-evident audit store.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any, Mapping, Protocol

import requests

from .version import __version__ as package_version
from .audit_store import SQLiteAuditStore
from .production import DeploymentCertificate, stable_hash
from .trading import Order, OrderSide, OrderStatus, RiskPolicy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _utcnow()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class BrokerEnvironment(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ReconciliationState(str, Enum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"


@dataclass(frozen=True)
class BrokerCredentials:
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)

    def validate(self) -> None:
        if not self.api_key.strip() or not self.api_secret.strip():
            raise ValueError("broker API credentials are required")

    @classmethod
    def from_environment(
        cls,
        *,
        key_name: str = "ALPACA_API_KEY_ID",
        secret_name: str = "ALPACA_API_SECRET_KEY",
    ) -> "BrokerCredentials":
        credentials = cls(os.getenv(key_name, ""), os.getenv(secret_name, ""))
        credentials.validate()
        return credentials


@dataclass(frozen=True)
class AccountSnapshot:
    account_id: str
    equity: float
    last_equity: float
    cash: float
    buying_power: float
    trading_blocked: bool
    account_blocked: bool
    timestamp: str = field(default_factory=_iso)

    @property
    def daily_pnl(self) -> float:
        return float(self.equity - self.last_equity)

    @property
    def daily_loss_fraction(self) -> float:
        if self.last_equity <= 0:
            return 1.0
        return max(0.0, -self.daily_pnl / self.last_equity)


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    quantity: float
    market_value: float
    current_price: float
    side: str = "long"


@dataclass(frozen=True)
class BrokerOrderReceipt:
    broker_order_id: str
    client_order_id: str
    symbol: str
    quantity: float
    side: str
    order_type: str
    status: str
    submitted_at: str
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    request_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class MarketDataSnapshot:
    symbol: str
    price: float
    timestamp: str | datetime
    bid: float | None = None
    ask: float | None = None
    source: str = "unknown"

    @property
    def age_seconds(self) -> float:
        return max(0.0, (_utcnow() - _parse_time(self.timestamp)).total_seconds())


@dataclass(frozen=True)
class BrokerHealth:
    state: HealthState
    broker: str
    environment: BrokerEnvironment
    latency_ms: float
    market_open: bool | None
    account_reachable: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    codes: tuple[str, ...]
    reasons: tuple[str, ...]
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationReport:
    state: ReconciliationState
    position_differences: dict[str, float]
    cash_difference: float
    generated_at: str = field(default_factory=_iso)

    @property
    def matched(self) -> bool:
        return self.state == ReconciliationState.MATCHED


@dataclass(frozen=True)
class LiveRiskPolicy(RiskPolicy):
    """Stricter controls applied before any broker submission."""

    max_daily_loss: float = 0.03
    max_open_orders: int = 20
    max_orders_per_minute: int = 30
    max_price_deviation_bps: float = 200.0
    max_market_data_age_seconds: float = 5.0
    max_capital: float | None = None
    max_position_notional: float | None = None
    require_market_open: bool = True
    reject_duplicate_orders: bool = True
    symbol_allowlist: tuple[str, ...] = ()
    symbol_denylist: tuple[str, ...] = ()
    reconciliation_quantity_tolerance: float = 1e-8
    reconciliation_cash_tolerance: float = 0.01
    max_consecutive_broker_failures: int = 3

    def validate(self) -> None:
        super().validate()
        if not 0 < self.max_daily_loss < 1:
            raise ValueError("max_daily_loss must lie in (0, 1)")
        if self.max_open_orders <= 0:
            raise ValueError("max_open_orders must be positive")
        if self.max_orders_per_minute <= 0:
            raise ValueError("max_orders_per_minute must be positive")
        if self.max_price_deviation_bps <= 0:
            raise ValueError("max_price_deviation_bps must be positive")
        if self.max_market_data_age_seconds <= 0:
            raise ValueError("max_market_data_age_seconds must be positive")
        if self.max_capital is not None and self.max_capital <= 0:
            raise ValueError("max_capital must be positive when provided")
        if self.max_position_notional is not None and self.max_position_notional <= 0:
            raise ValueError("max_position_notional must be positive when provided")
        if self.reconciliation_quantity_tolerance < 0 or self.reconciliation_cash_tolerance < 0:
            raise ValueError("reconciliation tolerances cannot be negative")
        if self.max_consecutive_broker_failures <= 0:
            raise ValueError("max_consecutive_broker_failures must be positive")
        overlap = set(self.symbol_allowlist).intersection(self.symbol_denylist)
        if overlap:
            raise ValueError(f"symbols cannot be both allowed and denied: {sorted(overlap)}")


class ExecutionBroker(Protocol):
    name: str
    environment: BrokerEnvironment

    def health(self) -> BrokerHealth: ...
    def account(self) -> AccountSnapshot: ...
    def positions(self) -> dict[str, PositionSnapshot]: ...
    def open_orders(self) -> list[BrokerOrderReceipt]: ...
    def get_order(self, client_order_id: str) -> BrokerOrderReceipt | None: ...
    def submit_order(self, order: Order) -> BrokerOrderReceipt: ...
    def cancel_order(self, broker_order_id: str) -> bool: ...


class AlpacaBroker:
    """Minimal Alpaca Trading API adapter with explicit paper/live separation."""

    name = "alpaca"
    PAPER_URL = "https://paper-api.alpaca.markets"
    LIVE_URL = "https://api.alpaca.markets"

    def __init__(
        self,
        *,
        credentials: BrokerCredentials,
        environment: BrokerEnvironment,
        session: requests.Session | Any | None = None,
        timeout_seconds: float = 10.0,
        base_url: str | None = None,
        _live_authorized: bool = False,
    ) -> None:
        credentials.validate()
        if environment == BrokerEnvironment.LIVE and not _live_authorized:
            raise PermissionError(
                "live Alpaca connections must be created with AlpacaBroker.live() "
                "and a valid deployment certificate"
            )
        self.credentials = credentials
        self.environment = environment
        self.base_url = (base_url or (self.LIVE_URL if environment == BrokerEnvironment.LIVE else self.PAPER_URL)).rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.session = session or requests.Session()

    def __repr__(self) -> str:
        return f"AlpacaBroker(environment={self.environment.value!r}, base_url={self.base_url!r}, credentials=<redacted>)"

    @classmethod
    def paper(
        cls,
        *,
        credentials: BrokerCredentials | None = None,
        session: requests.Session | Any | None = None,
        timeout_seconds: float = 10.0,
        base_url: str | None = None,
    ) -> "AlpacaBroker":
        return cls(
            credentials=credentials or BrokerCredentials.from_environment(),
            environment=BrokerEnvironment.PAPER,
            session=session,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    @classmethod
    def live(
        cls,
        *,
        certificate: DeploymentCertificate,
        certificate_secret: str | bytes,
        account_id: str,
        account_salt: str,
        risk_policy: LiveRiskPolicy,
        requested_capital: float,
        credentials: BrokerCredentials | None = None,
        session: requests.Session | Any | None = None,
        timeout_seconds: float = 10.0,
        base_url: str | None = None,
        environment_fingerprint: str | None = None,
    ) -> "AlpacaBroker":
        risk_policy.validate()
        certificate.verify(
            secret_key=certificate_secret,
            release_version=package_version,
            broker=cls.name,
            account_id=account_id,
            account_salt=account_salt,
            risk_policy=risk_policy,
            requested_capital=requested_capital,
            environment_fingerprint=environment_fingerprint,
        )
        if os.getenv("ASRQUANT_LIVE_TRADING", "").strip() != "ENABLED":
            raise PermissionError(
                "set ASRQUANT_LIVE_TRADING=ENABLED in the controlled deployment environment"
            )
        return cls(
            credentials=credentials or BrokerCredentials.from_environment(),
            environment=BrokerEnvironment.LIVE,
            session=session,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
            _live_authorized=True,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.credentials.api_key,
            "APCA-API-SECRET-KEY": self.credentials.api_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"ASRQuant/{package_version}",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
        retry_safe: bool = True,
        retries: int = 2,
    ) -> tuple[Any, str | None]:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            started = time.perf_counter()
            try:
                response = self.session.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._headers,
                    params=dict(params or {}),
                    json=dict(payload or {}) if payload is not None else None,
                    timeout=self.timeout_seconds,
                )
                request_id = response.headers.get("X-Request-ID") if hasattr(response, "headers") else None
                if response.status_code == 429 or response.status_code >= 500:
                    if retry_safe and attempt < retries:
                        retry_after = response.headers.get("Retry-After") if hasattr(response, "headers") else None
                        delay = float(retry_after) if retry_after else min(2.0**attempt, 4.0)
                        time.sleep(delay)
                        continue
                response.raise_for_status()
                if response.status_code == 204:
                    return None, request_id
                return response.json(), request_id
            except (requests.RequestException, TimeoutError) as exc:
                last_error = exc
                if not retry_safe or attempt >= retries:
                    raise
                elapsed = time.perf_counter() - started
                time.sleep(max(0.05, min(2.0**attempt, 4.0) - elapsed))
        raise RuntimeError("broker request failed") from last_error

    @staticmethod
    def _receipt(payload: Mapping[str, Any], request_id: str | None = None) -> BrokerOrderReceipt:
        return BrokerOrderReceipt(
            broker_order_id=str(payload.get("id", "")),
            client_order_id=str(payload.get("client_order_id", "")),
            symbol=str(payload.get("symbol", "")),
            quantity=float(payload.get("qty") or payload.get("notional") or 0.0),
            side=str(payload.get("side", "")),
            order_type=str(payload.get("type", "")),
            status=str(payload.get("status", "unknown")),
            submitted_at=str(payload.get("submitted_at") or _iso()),
            filled_quantity=float(payload.get("filled_qty") or 0.0),
            average_fill_price=(
                float(payload["filled_avg_price"])
                if payload.get("filled_avg_price") not in (None, "")
                else None
            ),
            request_id=request_id,
            raw=dict(payload),
        )

    def health(self) -> BrokerHealth:
        started = time.perf_counter()
        try:
            account = self.account()
            clock_payload, _ = self._request("GET", "/v2/clock")
            latency = (time.perf_counter() - started) * 1000.0
            return BrokerHealth(
                state=HealthState.HEALTHY,
                broker=self.name,
                environment=self.environment,
                latency_ms=latency,
                market_open=bool(clock_payload.get("is_open")) if isinstance(clock_payload, Mapping) else None,
                account_reachable=not account.account_blocked,
                details={"trading_blocked": account.trading_blocked},
            )
        except Exception as exc:
            return BrokerHealth(
                state=HealthState.UNHEALTHY,
                broker=self.name,
                environment=self.environment,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                market_open=None,
                account_reachable=False,
                details={"error": type(exc).__name__},
            )

    def account(self) -> AccountSnapshot:
        payload, _ = self._request("GET", "/v2/account")
        return AccountSnapshot(
            account_id=str(payload.get("account_number") or payload.get("id") or ""),
            equity=float(payload.get("equity") or 0.0),
            last_equity=float(payload.get("last_equity") or payload.get("equity") or 0.0),
            cash=float(payload.get("cash") or 0.0),
            buying_power=float(payload.get("buying_power") or 0.0),
            trading_blocked=bool(payload.get("trading_blocked", False)),
            account_blocked=bool(payload.get("account_blocked", False)),
        )

    def positions(self) -> dict[str, PositionSnapshot]:
        payload, _ = self._request("GET", "/v2/positions")
        positions: dict[str, PositionSnapshot] = {}
        for row in payload or []:
            symbol = str(row.get("symbol", ""))
            positions[symbol] = PositionSnapshot(
                symbol=symbol,
                quantity=float(row.get("qty") or 0.0),
                market_value=float(row.get("market_value") or 0.0),
                current_price=float(row.get("current_price") or 0.0),
                side=str(row.get("side") or "long"),
            )
        return positions

    def open_orders(self) -> list[BrokerOrderReceipt]:
        payload, request_id = self._request("GET", "/v2/orders", params={"status": "open", "limit": 500})
        return [self._receipt(row, request_id) for row in payload or []]

    def get_order(self, client_order_id: str) -> BrokerOrderReceipt | None:
        try:
            payload, request_id = self._request(
                "GET",
                "/v2/orders:by_client_order_id",
                params={"client_order_id": client_order_id},
                retries=1,
            )
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 404:
                return None
            raise
        return self._receipt(payload, request_id)

    def submit_order(self, order: Order) -> BrokerOrderReceipt:
        payload: dict[str, Any] = {
            "symbol": order.symbol,
            "qty": str(order.quantity),
            "side": order.side.value,
            "type": order.order_type.value,
            "time_in_force": str(order.metadata.get("time_in_force", "day")),
            "client_order_id": order.order_id,
        }
        if order.limit_price is not None:
            payload["limit_price"] = str(order.limit_price)
        if order.stop_price is not None:
            payload["stop_price"] = str(order.stop_price)
        try:
            response, request_id = self._request(
                "POST",
                "/v2/orders",
                payload=payload,
                retry_safe=False,
                retries=0,
            )
        except (requests.RequestException, TimeoutError):
            existing = self.get_order(order.order_id)
            if existing is not None:
                return existing
            response, request_id = self._request(
                "POST",
                "/v2/orders",
                payload=payload,
                retry_safe=False,
                retries=0,
            )
        return self._receipt(response, request_id)

    def cancel_order(self, broker_order_id: str) -> bool:
        try:
            self._request("DELETE", f"/v2/orders/{broker_order_id}", retries=1)
            return True
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 404:
                return False
            raise


class PersistentKillSwitch:
    """File-backed kill switch that survives process restarts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"active": False}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"active": True, "reason": "unreadable kill-switch state"}

    @property
    def active(self) -> bool:
        return bool(self._read().get("active", False))

    @property
    def state(self) -> dict[str, Any]:
        return self._read()

    def activate(self, reason: str, *, operator: str = "system") -> None:
        payload = {
            "active": True,
            "reason": reason,
            "operator": operator,
            "activated_at": _iso(),
        }
        self._atomic_write(payload)

    def clear(self, *, operator: str, authorization: str) -> None:
        if authorization != "CLEAR_KILL_SWITCH":
            raise PermissionError("explicit kill-switch clearance authorization is required")
        payload = {
            "active": False,
            "operator": operator,
            "cleared_at": _iso(),
        }
        self._atomic_write(payload)

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temporary = tempfile.mkstemp(prefix=self.path.name, dir=str(self.path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)


class PreTradeRiskEngine:
    """Stateful deterministic pre-trade controls."""

    def __init__(self, policy: LiveRiskPolicy) -> None:
        policy.validate()
        self.policy = policy
        self._seen_order_ids: set[str] = set()
        self._order_times: deque[float] = deque()
        self._lock = threading.RLock()

    def evaluate(
        self,
        order: Order,
        *,
        market: MarketDataSnapshot,
        account: AccountSnapshot,
        positions: Mapping[str, PositionSnapshot],
        open_orders: list[BrokerOrderReceipt],
        health: BrokerHealth,
    ) -> RiskDecision:
        reasons: list[str] = []
        codes: list[str] = []
        price = float(market.price)
        notional = abs(float(order.quantity) * price) if math.isfinite(price) else math.inf
        with self._lock:
            now_monotonic = time.monotonic()
            while self._order_times and now_monotonic - self._order_times[0] >= 60.0:
                self._order_times.popleft()

            def reject(code: str, reason: str) -> None:
                codes.append(code)
                reasons.append(reason)

            if self.policy.reject_duplicate_orders and order.order_id in self._seen_order_ids:
                reject("duplicate_order", "The client order ID has already been evaluated.")
            if order.quantity <= 0 or not math.isfinite(order.quantity):
                reject("invalid_quantity", "Order quantity must be finite and positive.")
            if not math.isfinite(price) or price <= 0:
                reject("invalid_market_price", "Reference market price must be finite and positive.")
            if market.symbol != order.symbol:
                reject("symbol_mismatch", "Market data symbol does not match the order symbol.")
            if market.age_seconds > self.policy.max_market_data_age_seconds:
                reject("stale_market_data", "Market data is older than the configured freshness limit.")
            if health.state != HealthState.HEALTHY or not health.account_reachable:
                reject("broker_unhealthy", "Broker or account health is not suitable for order entry.")
            if self.policy.require_market_open and health.market_open is not True:
                reject("market_closed", "The broker reports that the market is closed.")
            if account.trading_blocked or account.account_blocked:
                reject("account_blocked", "The broker account is blocked for trading.")
            if account.daily_loss_fraction >= self.policy.max_daily_loss:
                reject("daily_loss_limit", "The configured daily loss limit has been reached.")
            if len(open_orders) >= self.policy.max_open_orders:
                reject("open_order_limit", "The maximum number of open orders has been reached.")
            if len(self._order_times) >= self.policy.max_orders_per_minute:
                reject("order_rate_limit", "The maximum order-entry rate has been reached.")
            if self.policy.symbol_allowlist and order.symbol not in self.policy.symbol_allowlist:
                reject("symbol_not_allowed", "The symbol is not in the production allowlist.")
            if order.symbol in self.policy.symbol_denylist:
                reject("symbol_denied", "The symbol is in the production denylist.")
            if not self.policy.allow_short and order.side == OrderSide.SELL:
                current_qty = positions.get(order.symbol, PositionSnapshot(order.symbol, 0, 0, price)).quantity
                if order.quantity > max(current_qty, 0.0):
                    reject("short_not_allowed", "The order would create a short position.")
            if self.policy.max_order_notional is not None and notional > self.policy.max_order_notional:
                reject("order_notional_limit", "Order notional exceeds the configured maximum.")
            if self.policy.max_capital is not None and account.equity > self.policy.max_capital * 1.01:
                reject("capital_scope", "Broker account equity exceeds the authorized capital scope.")
            if notional > max(account.buying_power, 0.0) and order.side == OrderSide.BUY:
                reject("buying_power", "Order notional exceeds available buying power.")
            reference_for_control = order.limit_price or order.stop_price
            if reference_for_control is not None and price > 0:
                deviation_bps = abs(float(reference_for_control) / price - 1.0) * 10_000.0
                if deviation_bps > self.policy.max_price_deviation_bps:
                    reject("price_collar", "Order price is outside the configured market-price collar.")
            else:
                deviation_bps = 0.0

            current = positions.get(order.symbol)
            current_market_value = float(current.market_value) if current is not None else 0.0
            signed_notional = notional if order.side == OrderSide.BUY else -notional
            projected_position_value = current_market_value + signed_notional
            if self.policy.max_position_notional is not None and abs(projected_position_value) > self.policy.max_position_notional:
                reject("position_notional_limit", "Projected position notional exceeds the configured maximum.")
            if account.equity > 0:
                projected_position_weight = abs(projected_position_value) / account.equity
                if projected_position_weight > self.policy.max_position_weight:
                    reject("position_weight_limit", "Projected position weight exceeds the configured maximum.")
                existing_gross = sum(abs(position.market_value) for position in positions.values())
                projected_gross = max(0.0, existing_gross - abs(current_market_value) + abs(projected_position_value))
                projected_leverage = projected_gross / account.equity
                if projected_leverage > self.policy.max_gross_leverage:
                    reject("gross_leverage_limit", "Projected gross leverage exceeds the configured maximum.")
            else:
                projected_position_weight = math.inf
                projected_leverage = math.inf
                reject("invalid_equity", "Account equity must be positive.")

            approved = not codes
            if approved:
                self._seen_order_ids.add(order.order_id)
                self._order_times.append(now_monotonic)
        return RiskDecision(
            approved=approved,
            codes=tuple(codes),
            reasons=tuple(reasons),
            metrics={
                "market_data_age_seconds": market.age_seconds,
                "order_notional": notional,
                "price_deviation_bps": deviation_bps,
                "daily_loss_fraction": account.daily_loss_fraction,
                "projected_position_weight": projected_position_weight,
                "projected_gross_leverage": projected_leverage,
                "open_orders": float(len(open_orders)),
                "orders_last_minute": float(len(self._order_times)),
            },
        )


class LiveTradingEngine:
    """Production execution coordinator with risk, audit, and kill-switch controls."""

    def __init__(
        self,
        *,
        broker: ExecutionBroker,
        policy: LiveRiskPolicy,
        audit_store: SQLiteAuditStore,
        kill_switch: PersistentKillSwitch,
    ) -> None:
        policy.validate()
        self.broker = broker
        self.policy = policy
        self.audit_store = audit_store
        self.kill_switch = kill_switch
        self.risk_engine = PreTradeRiskEngine(policy)
        self._consecutive_failures = 0
        self._lock = threading.RLock()
        self.audit_store.append(
            "execution_engine_started",
            {
                "broker": broker.name,
                "environment": broker.environment.value,
                "policy_hash": stable_hash(asdict(policy)),
                "package_version": package_version,
            },
        )

    def submit(self, order: Order, market: MarketDataSnapshot) -> BrokerOrderReceipt:
        with self._lock:
            if self.kill_switch.active:
                raise PermissionError(f"kill switch is active: {self.kill_switch.state.get('reason', 'unknown')}")
            existing = self.broker.get_order(order.order_id)
            if existing is not None:
                self.audit_store.append(
                    "order_idempotent_recovery",
                    asdict(existing),
                    idempotency_key=f"recovered:{order.order_id}",
                )
                return existing
            health = self.broker.health()
            account = self.broker.account()
            positions = self.broker.positions()
            open_orders = self.broker.open_orders()
            decision = self.risk_engine.evaluate(
                order,
                market=market,
                account=account,
                positions=positions,
                open_orders=open_orders,
                health=health,
            )
            self.audit_store.append(
                "pre_trade_risk_decision",
                {
                    "order": self._safe_order(order),
                    "decision": asdict(decision),
                    "account": self._safe_account(account),
                    "market": asdict(market),
                    "broker_health": {
                        **asdict(health),
                        "state": health.state.value,
                        "environment": health.environment.value,
                    },
                },
                idempotency_key=f"risk:{order.order_id}",
            )
            if not decision.approved:
                order.status = OrderStatus.REJECTED
                raise PermissionError(
                    "pre-trade risk controls rejected order: " + ", ".join(decision.codes)
                )
            self.audit_store.append(
                "order_intent",
                self._safe_order(order),
                idempotency_key=f"intent:{order.order_id}",
            )
            try:
                receipt = self.broker.submit_order(order)
                self._consecutive_failures = 0
            except Exception as exc:
                self._consecutive_failures += 1
                self.audit_store.append(
                    "broker_submission_failed",
                    {
                        "order_id": order.order_id,
                        "error_type": type(exc).__name__,
                        "consecutive_failures": self._consecutive_failures,
                    },
                )
                if self._consecutive_failures >= self.policy.max_consecutive_broker_failures:
                    self.emergency_stop("broker failure threshold reached", operator="system")
                raise
            self.audit_store.append(
                "broker_order_receipt",
                {
                    **asdict(receipt),
                    "raw": {},
                },
                idempotency_key=f"receipt:{order.order_id}",
            )
            return receipt

    @staticmethod
    def _safe_order(order: Order) -> dict[str, Any]:
        payload = asdict(order)
        payload["side"] = order.side.value
        payload["order_type"] = order.order_type.value
        payload["status"] = order.status.value
        payload["metadata"] = {
            key: value
            for key, value in order.metadata.items()
            if "secret" not in key.lower() and "token" not in key.lower() and "key" not in key.lower()
        }
        return payload

    @staticmethod
    def _safe_account(account: AccountSnapshot) -> dict[str, Any]:
        payload = asdict(account)
        payload["account_id"] = stable_hash(account.account_id)[:16]
        return payload

    def emergency_stop(self, reason: str, *, operator: str) -> None:
        with self._lock:
            self.kill_switch.activate(reason, operator=operator)
            cancellations: list[dict[str, Any]] = []
            try:
                for receipt in self.broker.open_orders():
                    cancelled = self.broker.cancel_order(receipt.broker_order_id)
                    cancellations.append(
                        {
                            "broker_order_id": receipt.broker_order_id,
                            "client_order_id": receipt.client_order_id,
                            "cancelled": cancelled,
                        }
                    )
            finally:
                self.audit_store.append(
                    "emergency_stop",
                    {"reason": reason, "operator": operator, "cancellations": cancellations},
                )

    def reconcile(
        self,
        *,
        expected_positions: Mapping[str, float],
        expected_cash: float,
    ) -> ReconciliationReport:
        actual_positions = self.broker.positions()
        symbols = set(expected_positions).union(actual_positions)
        differences = {
            symbol: float(actual_positions.get(symbol, PositionSnapshot(symbol, 0, 0, 0)).quantity)
            - float(expected_positions.get(symbol, 0.0))
            for symbol in sorted(symbols)
        }
        account = self.broker.account()
        cash_difference = float(account.cash - expected_cash)
        matched = all(
            abs(value) <= self.policy.reconciliation_quantity_tolerance
            for value in differences.values()
        ) and abs(cash_difference) <= self.policy.reconciliation_cash_tolerance
        report = ReconciliationReport(
            state=ReconciliationState.MATCHED if matched else ReconciliationState.MISMATCHED,
            position_differences=differences,
            cash_difference=cash_difference,
        )
        self.audit_store.append(
            "reconciliation",
            {
                **asdict(report),
                "state": report.state.value,
            },
        )
        if not matched:
            self.emergency_stop("broker reconciliation mismatch", operator="system")
        return report

    def health_snapshot(self) -> dict[str, Any]:
        health = self.broker.health()
        chain_valid, broken_sequence = self.audit_store.verify_chain()
        return {
            "timestamp": _iso(),
            "broker": health.broker,
            "environment": health.environment.value,
            "broker_state": health.state.value,
            "latency_ms": health.latency_ms,
            "market_open": health.market_open,
            "account_reachable": health.account_reachable,
            "kill_switch_active": self.kill_switch.active,
            "audit_chain_valid": chain_valid,
            "audit_chain_broken_sequence": broken_sequence,
            "consecutive_broker_failures": self._consecutive_failures,
        }


__all__ = [
    "BrokerEnvironment",
    "HealthState",
    "ReconciliationState",
    "BrokerCredentials",
    "AccountSnapshot",
    "PositionSnapshot",
    "BrokerOrderReceipt",
    "MarketDataSnapshot",
    "BrokerHealth",
    "RiskDecision",
    "ReconciliationReport",
    "LiveRiskPolicy",
    "ExecutionBroker",
    "AlpacaBroker",
    "PersistentKillSwitch",
    "PreTradeRiskEngine",
    "LiveTradingEngine",
]
