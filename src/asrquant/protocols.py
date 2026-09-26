"""Minimal extension protocols for institution-specific ASRQuant adapters."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataProviderProtocol(Protocol):
    def history(self, *args: Any, **kwargs: Any) -> pd.Series | pd.DataFrame: ...


@runtime_checkable
class PricingEngineProtocol(Protocol):
    def price(self, instrument: Any, market: Any, **kwargs: Any) -> float: ...


@runtime_checkable
class RiskModelProtocol(Protocol):
    def risk(self, positions: Any, market: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class ExecutionModelProtocol(Protocol):
    def execute(self, orders: Any, market: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class CostModelProtocol(Protocol):
    def estimate(self, *args: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class OptimizerProtocol(Protocol):
    def optimize(self, *args: Any, **kwargs: Any) -> Any: ...


__all__ = [
    "DataProviderProtocol",
    "PricingEngineProtocol",
    "RiskModelProtocol",
    "ExecutionModelProtocol",
    "CostModelProtocol",
    "OptimizerProtocol",
]
