"""ASRQuant visualization namespace.

Visualization backends are loaded on first use so ``import asrquant`` does not
initialize Matplotlib/Plotly or the visualization-only scikit-learn helpers.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any


_MODULES = {
    "market",
    "risk",
    "regression",
    "portfolio",
    "derivatives",
    "ml",
    "microstructure",
    "general",
    "simulation",
}


def __getattr__(name: str) -> Any:
    if name in _MODULES:
        value = import_module(f"{__name__}.{name}")
        globals()[name] = value
        return value
    if name == "PerformanceVisualizer":
        value = import_module(f"{__name__}.performance").PerformanceVisualizer
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "market",
    "risk",
    "regression",
    "portfolio",
    "derivatives",
    "ml",
    "microstructure",
    "general",
    "simulation",
    "PerformanceVisualizer",
]
