# Algorithmic trading support

ASRQuant 1.0.0 provides a safe bridge from target portfolio weights to order-level paper trading. Live execution is intentionally adapter-based and disabled unless a user supplies an explicit broker implementation.

## Paper trading from a QuantLab

```python
import asrquant as asr

lab = asr.open_lab("prices.csv", date_column="Date")
weights = lab.strategy("sma", fast=20, slow=100)

paper = lab.paper_trade(
    weights,
    initial_capital=100_000,
    commission_bps=1,
    slippage_bps=2,
    policy=asr.RiskPolicy(
        max_gross_leverage=1.0,
        max_position_weight=0.20,
        max_daily_turnover=0.50,
        max_drawdown=0.15,
    ),
)
```

## Paper trading from a research project

```python
paper = project.paper_trade(
    commission_bps=1,
    slippage_bps=2,
)
```

## Order model

```python
order = asr.Order(
    symbol="SPY",
    quantity=10,
    side=asr.OrderSide.BUY,
    order_type=asr.OrderType.LIMIT,
    limit_price=500.0,
)
```

Order statuses are `CREATED`, `ACCEPTED`, `PARTIALLY_FILLED`, `FILLED`, `REJECTED` and `CANCELLED`.

## Broker-neutral adapter

A real or third-party paper broker can implement:

```python
class MyBroker:
    def submit_order(self, order, market_price): ...
    def cancel_order(self, order_id): ...
    def positions(self): ...
    def cash_balance(self): ...
```

The type contract is exposed as `asr.BrokerAdapter`.

## Risk policy

`RiskPolicy` supports:

- maximum gross leverage;
- maximum position weight;
- maximum order notional;
- maximum daily turnover;
- maximum drawdown kill switch;
- short-selling permission;
- minimum cash balance.

## Current execution boundary

ASRQuant does not yet include venue-specific live adapters, exchange authentication, asynchronous order reconciliation, broker callbacks, queue-position models or high-frequency limit-order-book simulation. These capabilities require separate operational security, broker certification and venue-specific testing.
