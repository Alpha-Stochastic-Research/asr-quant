"""Parameter sweeps and strategy comparison for reproducible research."""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping

import pandas as pd

from .api import QuantLab
from .config import BacktestSpec


def parameter_sweep(
    lab: QuantLab,
    strategy: str,
    grid: Mapping[str, list[Any] | tuple[Any, ...]],
    *,
    metric: str = "Sharpe",
    spec: BacktestSpec | None = None,
    costs_bps: float | None = None,
    execution_delay: int | None = None,
) -> pd.DataFrame:
    """Evaluate a Cartesian parameter grid and retain all major metrics."""
    if not grid:
        raise ValueError("grid must not be empty")
    names = list(grid); rows = []
    for values in product(*(grid[name] for name in names)):
        parameters = dict(zip(names, values))
        result = lab.backtest(strategy, spec=spec, costs_bps=costs_bps, execution_delay=execution_delay, **parameters)
        row = dict(parameters); row.update(result.metrics.to_dict()); row["fingerprint"] = result.fingerprint
        rows.append(row)
    frame = pd.DataFrame(rows)
    if metric not in frame.columns:
        raise ValueError(f"metric {metric!r} not available")
    return frame.sort_values(metric, ascending=False).reset_index(drop=True)


def strategy_comparison(lab: QuantLab, strategies: Mapping[str, tuple[str, dict[str, Any]]], **backtest_kwargs) -> pd.DataFrame:
    """Run named strategy specifications and return one metric table."""
    rows = {}
    for label, (name, kwargs) in strategies.items():
        rows[label] = lab.backtest(name, **backtest_kwargs, **kwargs).metrics
    return pd.DataFrame(rows).T

# End-to-end research workflow facade. Kept here so users can write
# ``asr.research.from_pdfs(...)`` while the original sweep helpers remain stable.
from .workflow import (  # noqa: E402
    DataPlan,
    DataRequirement,
    DecisionResult,
    EconomicHypothesis,
    FeaturePlan,
    FeatureSpec,
    PortfolioSpec,
    HypothesisTestResult,
    ResearchProject,
    RobustnessResult,
    SignalSpec,
    autoresearch,
    research_project,
)


def from_pdfs(papers, *, topic=None, name="ASRQuant research project") -> ResearchProject:
    """Create a source-linked research project from one PDF or a folder of PDFs."""
    return ResearchProject.from_pdfs(papers, topic=topic, name=name)


def from_hypothesis(statement: str, *, topic=None, name="ASRQuant research project", **fields) -> ResearchProject:
    """Create a project when the economic hypothesis is already known."""
    return ResearchProject.from_hypothesis(statement, topic=topic, name=name, **fields)


project = research_project


__all__ = [
    "parameter_sweep", "strategy_comparison", "from_pdfs", "from_hypothesis", "project", "autoresearch",
    "DataRequirement", "DataPlan", "EconomicHypothesis", "FeatureSpec", "FeaturePlan", "SignalSpec",
    "PortfolioSpec", "HypothesisTestResult", "RobustnessResult", "DecisionResult", "ResearchProject",
]
