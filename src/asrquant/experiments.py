"""Experiment manifests and lightweight local research-run registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import platform
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .data_store import DataSnapshot, snapshot
from .version import __version__


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass
class Experiment:
    name: str
    config: Mapping[str, Any] = field(default_factory=dict)
    data: Mapping[str, pd.Series | pd.DataFrame | DataSnapshot] = field(default_factory=dict)
    seed: int | None = None
    code_hash: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("experiment name must not be empty")
        if self.seed is not None and self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)

    @property
    def data_hashes(self) -> dict[str, str]:
        out = {}
        for name, value in self.data.items():
            snap = value if isinstance(value, DataSnapshot) else snapshot(value, source=name)
            out[str(name)] = snap.hash
        return out

    @property
    def config_hash(self) -> str:
        return _json_hash(dict(self.config))

    @property
    def fingerprint(self) -> str:
        return _json_hash(
            {
                "name": self.name,
                "config": dict(self.config),
                "data_hashes": self.data_hashes,
                "seed": self.seed,
                "code_hash": self.code_hash,
                "asrquant_version": __version__,
            }
        )

    @property
    def experiment_id(self) -> str:
        return f"ASR-EXP-{self.created_at:%Y%m%d}-{self.fingerprint[:10].upper()}"

    @property
    def summary(self) -> pd.Series:
        return pd.Series(
            {
                "experiment_id": self.experiment_id,
                "name": self.name,
                "asrquant_version": __version__,
                "config_hash": self.config_hash,
                "datasets": len(self.data_hashes),
                "seed": self.seed,
                "fingerprint": self.fingerprint,
            }
        )

    def manifest(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "asrquant_version": __version__,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "config": dict(self.config),
            "config_hash": self.config_hash,
            "data_hashes": self.data_hashes,
            "seed": self.seed,
            "code_hash": self.code_hash,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "fingerprint": self.fingerprint,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.manifest()

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.manifest(), indent=2, sort_keys=True, default=str), encoding="utf-8")
        return target


class ExperimentRegistry:
    """Append-only JSONL registry for experiment manifests."""

    def __init__(self, path: str | Path = ".asrquant-experiments.jsonl") -> None:
        self.path = Path(path)

    def add(self, experiment: Experiment) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(experiment.manifest(), sort_keys=True, default=str) + "\n")
        return experiment.experiment_id

    def table(self, name: str | None = None) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame()
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        frame = pd.DataFrame(rows)
        if name is not None and "name" in frame:
            frame = frame[frame["name"] == name]
        return frame.reset_index(drop=True)

    def get(self, experiment_id: str) -> dict[str, Any]:
        table = self.table()
        if table.empty or "experiment_id" not in table:
            raise KeyError(experiment_id)
        hit = table[table["experiment_id"] == experiment_id]
        if hit.empty:
            raise KeyError(experiment_id)
        return hit.iloc[-1].to_dict()

    def compare(self, name: str) -> pd.DataFrame:
        table = self.table(name=name)
        keep = [c for c in ["experiment_id", "created_at", "asrquant_version", "config_hash", "data_hashes", "seed", "code_hash", "fingerprint"] if c in table]
        return table[keep].copy() if not table.empty else table


__all__ = ["Experiment", "ExperimentRegistry"]
