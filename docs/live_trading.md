# Guarded broker execution

## Supported adapter

ASRQuant 1.0.0 includes an Alpaca Trading API adapter for paper and live environments. The implementation uses distinct official endpoints:

- paper: `https://paper-api.alpaca.markets`;
- live: `https://api.alpaca.markets`.

The adapter is intentionally conservative. It does not implement high-frequency trading, smart-order routing across venues or a complete OMS/EMS.

## Credentials

Set credentials only in the execution environment or secret manager:

```bash
export ALPACA_API_KEY_ID='...'
export ALPACA_API_SECRET_KEY='...'
```

Never place credentials in:

- source files;
- notebooks;
- configuration committed to Git;
- command history;
- HTML reports;
- exception messages;
- audit payloads.

`BrokerCredentials` redacts secrets from its representation.

## Paper connection

```python
import asrquant as asr

broker = asr.AlpacaBroker.paper(
    credentials=asr.BrokerCredentials.from_environment(),
)

print(broker.health())
print(broker.account())
```

Broker paper environments are simulations. Execution behavior, order types, depth, partial fills and queue position may differ from live markets.

## Live connection

The live classmethod requires:

- a valid deployment certificate;
- the certificate signing key;
- the exact account and salt used for the certificate;
- the exact risk policy used for the certificate;
- a requested capital amount within the certificate limit;
- `ASRQUANT_LIVE_TRADING=ENABLED`;
- live broker credentials.

```python
broker = asr.AlpacaBroker.live(
    certificate=certificate,
    certificate_secret=signing_key,
    account_id=account_id,
    account_salt=account_salt,
    risk_policy=policy,
    requested_capital=25_000,
    credentials=asr.BrokerCredentials.from_environment(),
)
```

Calling the normal constructor with `environment="live"` raises `PermissionError`.

## Pre-trade controls

`LiveTradingEngine.submit()` evaluates:

- persistent kill switch;
- duplicate client order ID;
- quantity and market price;
- market-data symbol and age;
- broker/account health;
- market-open state;
- account blocks;
- daily loss;
- open-order count;
- order-entry rate;
- allowlist and denylist;
- short-selling policy;
- order notional;
- capital scope;
- buying power;
- limit/stop price collar;
- projected position notional;
- projected position weight;
- projected gross leverage.

Rejected orders never reach the broker adapter.

## Idempotency

ASRQuant sends `Order.order_id` as the broker `client_order_id`. If an order submission times out, the adapter queries the broker by client order ID before retrying. This reduces duplicate orders after ambiguous network failures.

A production deployment should still monitor and reconcile because no network protocol can eliminate every ambiguity without broker-side cooperation.

## Example submission

```python
store = asr.SQLiteAuditStore("state/execution-audit.db")
kill_switch = asr.PersistentKillSwitch("state/KILL_SWITCH.json")
engine = asr.LiveTradingEngine(
    broker=broker,
    policy=policy,
    audit_store=store,
    kill_switch=kill_switch,
)

order = asr.Order(
    symbol="SPY",
    quantity=10,
    side=asr.OrderSide.BUY,
    order_type=asr.OrderType.LIMIT,
    limit_price=500.00,
    metadata={"time_in_force": "day"},
)

receipt = engine.submit(
    order,
    asr.MarketDataSnapshot(
        symbol="SPY",
        price=499.90,
        bid=499.89,
        ask=499.91,
        timestamp=market_timestamp,
        source="primary-feed",
    ),
)
```

## Reconciliation

```python
report = engine.reconcile(
    expected_positions={"SPY": 10.0},
    expected_cash=20_000.0,
)
```

Any mismatch beyond the configured tolerances activates the kill switch and attempts to cancel open orders.

## Emergency stop

```python
engine.emergency_stop(
    "market data diverged from secondary feed",
    operator="risk-owner",
)
```

The kill-switch file survives a process restart. A corrupted or unreadable file is interpreted as active.
