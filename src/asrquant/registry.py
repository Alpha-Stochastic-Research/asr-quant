"""Runtime registry for institution-specific adapters without core-package forks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterRegistry:
    _items: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "data_provider": {},
        "pricer": {},
        "risk_model": {},
        "execution": {},
        "cost_model": {},
        "optimizer": {},
    })

    def _register(self, kind: str, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        key = str(name).strip().lower()
        if not key:
            raise ValueError("adapter name must not be empty")
        bucket = self._items[kind]
        if key in bucket and not overwrite:
            raise KeyError(f"{kind} adapter {key!r} is already registered")
        bucket[key] = adapter
        return adapter

    def data_provider(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("data_provider", name, adapter, overwrite=overwrite)

    def pricer(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("pricer", name, adapter, overwrite=overwrite)

    def risk_model(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("risk_model", name, adapter, overwrite=overwrite)

    def execution(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("execution", name, adapter, overwrite=overwrite)

    def cost_model(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("cost_model", name, adapter, overwrite=overwrite)

    def optimizer(self, name: str, adapter: Any, *, overwrite: bool = False) -> Any:
        return self._register("optimizer", name, adapter, overwrite=overwrite)

    def get(self, kind: str, name: str) -> Any:
        if kind not in self._items:
            raise KeyError(f"unknown adapter kind {kind!r}")
        return self._items[kind][str(name).strip().lower()]

    def available(self, kind: str | None = None) -> dict[str, tuple[str, ...]] | tuple[str, ...]:
        if kind is not None:
            if kind not in self._items:
                raise KeyError(kind)
            return tuple(sorted(self._items[kind]))
        return {k: tuple(sorted(v)) for k, v in self._items.items()}

    def clear(self, kind: str | None = None) -> None:
        if kind is None:
            for bucket in self._items.values():
                bucket.clear()
            return
        self._items[kind].clear()


register = AdapterRegistry()

__all__ = ["AdapterRegistry", "register"]
