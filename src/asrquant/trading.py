"""Broker-neutral algorithmic-trading primitives and deterministic paper trading.

No live orders are sent by this module. A live broker must implement ``BrokerAdapter``
and be explicitly supplied by the user. The built-in ``PaperBroker`` is the safe
reference implementation used for research-to-execution validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol
import uuid

import numpy as np
import pandas as pd

from .metrics import summary_metrics


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Order:
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    timestamp: Any = None
    order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    status: OrderStatus = OrderStatus.CREATED
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def signed_quantity(self) -> float:
        return float(self.quantity if self.side == OrderSide.BUY else -self.quantity)


@dataclass
class Fill:
    order_id: str
    symbol: str
    quantity: float
    price: float
    commission: float
    timestamp: Any
    slippage: float = 0.0


@dataclass(frozen=True)
class RiskPolicy:
    """Pre-trade and session-level limits for algorithmic trading."""

    max_gross_leverage: float = 1.0
    max_position_weight: float = 0.25
    max_order_notional: float | None = None
    max_daily_turnover: float = 2.0
    max_drawdown: float = 0.20
    allow_short: bool = True
    minimum_cash: float = 0.0

    def validate(self) -> None:
        if self.max_gross_leverage <= 0:
            raise ValueError("max_gross_leverage must be positive")
        if not 0 < self.max_position_weight <= self.max_gross_leverage:
            raise ValueError("max_position_weight must be positive and <= max_gross_leverage")
        if self.max_daily_turnover <= 0:
            raise ValueError("max_daily_turnover must be positive")
        if not 0 < self.max_drawdown < 1:
            raise ValueError("max_drawdown must lie in (0, 1)")
        if self.max_order_notional is not None and self.max_order_notional <= 0:
            raise ValueError("max_order_notional must be positive when provided")
        if self.minimum_cash < 0:
            raise ValueError("minimum_cash cannot be negative")


class BrokerAdapter(Protocol):
    """Minimal interface for an external paper or live broker adapter."""

    def submit_order(self, order: Order, market_price: float) -> Fill | None: ...
    def cancel_order(self, order_id: str) -> bool: ...
    def positions(self) -> dict[str, float]: ...
    def cash_balance(self) -> float: ...


class PaperBroker:
    """Immediate-fill paper broker with transparent costs and order history."""

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        *,
        commission_bps: float = 0.0,
        slippage_bps: float = 0.0,
        participation_rate: float = 1.0,
    ) -> None:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if not 0 < participation_rate <= 1:
            raise ValueError("participation_rate must lie in (0, 1]")
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.commission_bps = float(commission_bps)
        self.slippage_bps = float(slippage_bps)
        self.participation_rate = float(participation_rate)
        self._positions: dict[str, float] = {}
        self.orders: dict[str, Order] = {}
        self.fills: list[Fill] = []

    def submit_order(self, order: Order, market_price: float) -> Fill | None:
        if order.quantity <= 0 or not np.isfinite(market_price) or market_price <= 0:
            order.status = OrderStatus.REJECTED
            self.orders[order.order_id] = order
            return None
        executable = True
        if order.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT} and order.limit_price is not None:
            executable = market_price <= order.limit_price if order.side == OrderSide.BUY else market_price >= order.limit_price
        if order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT} and order.stop_price is not None:
            executable = executable and (market_price >= order.stop_price if order.side == OrderSide.BUY else market_price <= order.stop_price)
        if not executable:
            order.status = OrderStatus.ACCEPTED
            self.orders[order.order_id] = order
            return None

        fill_quantity = float(order.quantity * self.participation_rate)
        direction = 1.0 if order.side == OrderSide.BUY else -1.0
        slippage = market_price * self.slippage_bps / 10_000.0 * direction
        fill_price = float(market_price + slippage)
        notional = fill_quantity * fill_price
        commission = abs(notional) * self.commission_bps / 10_000.0
        cash_change = -direction * notional - commission
        self.cash += cash_change
        self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) + direction * fill_quantity
        order.status = OrderStatus.FILLED if self.participation_rate == 1 else OrderStatus.PARTIALLY_FILLED
        self.orders[order.order_id] = order
        fill = Fill(order.order_id, order.symbol, direction * fill_quantity, fill_price, commission, order.timestamp, slippage)
        self.fills.append(fill)
        return fill

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order is None or order.status in {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED}:
            return False
        order.status = OrderStatus.CANCELLED
        return True

    def positions(self) -> dict[str, float]:
        return dict(self._positions)

    def cash_balance(self) -> float:
        return float(self.cash)


@dataclass
class PaperTradingResult:
    equity: pd.Series
    cash: pd.Series
    positions: pd.DataFrame
    target_weights: pd.DataFrame
    realized_weights: pd.DataFrame
    orders: pd.DataFrame
    fills: pd.DataFrame
    risk_events: pd.DataFrame
    policy: RiskPolicy
    metadata: dict[str, Any]

    @property
    def returns(self) -> pd.Series:
        return self.equity.pct_change(fill_method=None).fillna(0.0).rename("paper_return")

    @property
    def metrics(self) -> pd.Series:
        return summary_metrics(self.returns, annualization=int(self.metadata.get("annualization", 252)))

    @property
    def summary(self) -> pd.Series:
        values = self.metrics.to_dict()
        values.update(
            {
                "orders": len(self.orders),
                "fills": len(self.fills),
                "risk_events": len(self.risk_events),
                "final_equity": float(self.equity.iloc[-1]),
            }
        )
        return pd.Series(values)

    def to_frame(self) -> pd.DataFrame:
        return pd.concat({"equity": self.equity, "cash": self.cash, "returns": self.returns}, axis=1)


class PaperTrader:
    """Convert target weights into orders and simulate an auditable paper session."""

    def __init__(
        self,
        *,
        initial_capital: float = 100_000.0,
        commission_bps: float = 0.0,
        slippage_bps: float = 0.0,
        policy: RiskPolicy | None = None,
        annualization: int = 252,
    ) -> None:
        self.initial_capital = float(initial_capital)
        self.commission_bps = float(commission_bps)
        self.slippage_bps = float(slippage_bps)
        self.policy = policy or RiskPolicy()
        self.policy.validate()
        self.annualization = int(annualization)

    def run(self, prices: pd.DataFrame, target_weights: pd.DataFrame) -> PaperTradingResult:
        price_frame = pd.DataFrame(prices, dtype=float).sort_index()
        weights = pd.DataFrame(target_weights, dtype=float).reindex(index=price_frame.index, columns=price_frame.columns).ffill().fillna(0.0)
        broker = PaperBroker(
            self.initial_capital,
            commission_bps=self.commission_bps,
            slippage_bps=self.slippage_bps,
        )
        positions_history: list[pd.Series] = []
        realized_weight_history: list[pd.Series] = []
        equity_history: list[float] = []
        cash_history: list[float] = []
        order_records: list[dict[str, Any]] = []
        risk_records: list[dict[str, Any]] = []
        peak_equity = self.initial_capital

        for timestamp, current_prices in price_frame.iterrows():
            current_positions = pd.Series(broker.positions(), index=price_frame.columns, dtype=float).fillna(0.0)
            equity_before = float(broker.cash + (current_positions * current_prices).sum())
            peak_equity = max(peak_equity, equity_before)
            drawdown = 1 - equity_before / peak_equity if peak_equity > 0 else 1.0
            if drawdown >= self.policy.max_drawdown:
                desired_weights = pd.Series(0.0, index=price_frame.columns)
                risk_records.append({"timestamp": timestamp, "event": "kill_switch", "value": drawdown})
            else:
                desired_weights = weights.loc[timestamp].clip(
                    lower=-self.policy.max_position_weight if self.policy.allow_short else 0.0,
                    upper=self.policy.max_position_weight,
                )
                gross = float(desired_weights.abs().sum())
                if gross > self.policy.max_gross_leverage:
                    desired_weights *= self.policy.max_gross_leverage / gross
                    risk_records.append({"timestamp": timestamp, "event": "gross_leverage_scaled", "value": gross})

            desired_notional = desired_weights * equity_before
            current_notional = current_positions * current_prices
            delta_notional = desired_notional - current_notional
            turnover = float(delta_notional.abs().sum() / max(equity_before, 1e-12))
            if turnover > self.policy.max_daily_turnover:
                scale = self.policy.max_daily_turnover / turnover
                delta_notional *= scale
                risk_records.append({"timestamp": timestamp, "event": "turnover_scaled", "value": turnover})

            ordered_deltas = sorted(delta_notional.items(), key=lambda item: float(item[1]))
            for symbol, notional in ordered_deltas:
                if abs(notional) < 1e-10:
                    continue
                if self.policy.max_order_notional is not None and abs(notional) > self.policy.max_order_notional:
                    notional = np.sign(notional) * self.policy.max_order_notional
                    risk_records.append({"timestamp": timestamp, "event": "order_notional_capped", "symbol": symbol, "value": abs(delta_notional[symbol])})
                if notional > 0:
                    available_cash = max(0.0, broker.cash - self.policy.minimum_cash)
                    estimated_rate = (self.commission_bps + self.slippage_bps) / 10_000.0
                    affordable = available_cash / max(1.0 + estimated_rate, 1e-12)
                    if notional > affordable:
                        risk_records.append({"timestamp": timestamp, "event": "cash_capped", "symbol": symbol, "value": float(notional)})
                        notional = affordable
                if abs(notional) < 1e-10:
                    continue
                quantity = abs(float(notional / current_prices[symbol]))
                order = Order(
                    symbol=str(symbol),
                    quantity=quantity,
                    side=OrderSide.BUY if notional > 0 else OrderSide.SELL,
                    timestamp=timestamp,
                )
                fill = broker.submit_order(order, float(current_prices[symbol]))
                record = asdict(order)
                record["timestamp"] = timestamp
                record["fill_price"] = fill.price if fill else np.nan
                record["commission"] = fill.commission if fill else np.nan
                order_records.append(record)

            current_positions = pd.Series(broker.positions(), index=price_frame.columns, dtype=float).fillna(0.0)
            equity = float(broker.cash + (current_positions * current_prices).sum())
            realized_weights = current_positions * current_prices / max(equity, 1e-12)
            positions_history.append(current_positions.rename(timestamp))
            realized_weight_history.append(realized_weights.rename(timestamp))
            equity_history.append(equity)
            cash_history.append(broker.cash)

        fills = pd.DataFrame([asdict(fill) for fill in broker.fills])
        if not fills.empty:
            fills = fills.set_index("timestamp")
        orders = pd.DataFrame(order_records)
        if not orders.empty:
            orders = orders.set_index("timestamp")
        risk_events = pd.DataFrame(risk_records)
        if not risk_events.empty:
            risk_events = risk_events.set_index("timestamp")
        return PaperTradingResult(
            equity=pd.Series(equity_history, index=price_frame.index, name="paper_equity"),
            cash=pd.Series(cash_history, index=price_frame.index, name="cash"),
            positions=pd.DataFrame(positions_history).reindex(columns=price_frame.columns),
            target_weights=weights,
            realized_weights=pd.DataFrame(realized_weight_history).reindex(columns=price_frame.columns),
            orders=orders,
            fills=fills,
            risk_events=risk_events,
            policy=self.policy,
            metadata={
                "initial_capital": self.initial_capital,
                "commission_bps": self.commission_bps,
                "slippage_bps": self.slippage_bps,
                "annualization": self.annualization,
            },
        )


def paper_trade(
    prices: pd.DataFrame,
    target_weights: pd.DataFrame,
    *,
    initial_capital: float = 100_000.0,
    commission_bps: float = 0.0,
    slippage_bps: float = 0.0,
    policy: RiskPolicy | None = None,
    annualization: int = 252,
) -> PaperTradingResult:
    """One-call paper trading simulation from target weights."""
    return PaperTrader(
        initial_capital=initial_capital,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        policy=policy,
        annualization=annualization,
    ).run(prices, target_weights)


__all__ = [
    "OrderSide", "OrderType", "OrderStatus", "Order", "Fill", "RiskPolicy",
    "BrokerAdapter", "PaperBroker", "PaperTrader", "PaperTradingResult", "paper_trade",
]
