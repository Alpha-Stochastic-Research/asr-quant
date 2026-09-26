"""Reproducible experiment, snapshot and lineage utilities for ASRQuant 1.3.0."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Iterable
import json
import os
import platform

import pandas as pd


def _json_default(value: Any):
    if isinstance(value, (pd.Timestamp, datetime)): return value.isoformat()
    if isinstance(value, Path): return str(value)
    if hasattr(value, "item"):
        try: return value.item()
        except Exception: pass
    return str(value)


def fingerprint(value: Any) -> str:
    if isinstance(value, pd.DataFrame): payload = value.to_json(orient="split", date_format="iso", double_precision=15)
    elif isinstance(value, pd.Series): payload = value.to_json(date_format="iso", double_precision=15)
    else: payload = json.dumps(value, sort_keys=True, default=_json_default, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DataSnapshot:
    name: str
    fingerprint: str
    path: str
    source: str | None
    created_at: str
    rows: int
    columns: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


class DataStore:
    """Local deterministic DataFrame store using non-executable JSON-table serialization."""
    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, frame: pd.DataFrame, *, source: str | None = None, metadata: Mapping[str, Any] | None = None) -> DataSnapshot:
        data = pd.DataFrame(frame).copy(); fp = fingerprint(data); path = self.root / f"{key}-{fp[:16]}.json"
        data.to_json(path, orient="table", date_format="iso", double_precision=15)
        snapshot = DataSnapshot(key, fp, str(path), source, datetime.now(timezone.utc).isoformat(), len(data), tuple(map(str, data.columns)), dict(metadata or {}))
        path.with_suffix(".meta.json").write_text(json.dumps(asdict(snapshot), sort_keys=True, default=_json_default, indent=2), encoding="utf-8")
        return snapshot

    def get(self, snapshot: DataSnapshot | str) -> pd.DataFrame:
        path = Path(snapshot.path if isinstance(snapshot, DataSnapshot) else snapshot); return pd.read_json(path, orient="table")

    def verify(self, snapshot: DataSnapshot) -> bool:
        return fingerprint(self.get(snapshot)) == snapshot.fingerprint


@dataclass(frozen=True)
class Experiment:
    name: str
    config: Mapping[str, Any]
    data_fingerprints: Mapping[str, str] = field(default_factory=dict)
    seed: int | None = None
    code_hash: str | None = None
    package_version: str | None = None
    notes: str | None = None

    @property
    def id(self) -> str:
        payload = {"name": self.name, "config": self.config, "data_fingerprints": self.data_fingerprints, "seed": self.seed, "code_hash": self.code_hash, "package_version": self.package_version}
        return fingerprint(payload)[:20]

    @classmethod
    def from_data(cls, name: str, config: Mapping[str, Any], data: Mapping[str, Any], *, seed: int | None = None, code_hash: str | None = None, package_version: str | None = None, notes: str | None = None):
        return cls(name, dict(config), {k: fingerprint(v) for k,v in data.items()}, seed, code_hash, package_version, notes)

    def record(self) -> dict[str, Any]:
        return {**asdict(self), "id": self.id, "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "platform": platform.platform()}


class ExperimentRegistry:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, experiment: Experiment) -> str:
        with self.path.open("a", encoding="utf-8") as fh: fh.write(json.dumps(experiment.record(), sort_keys=True, default=_json_default) + "\n")
        return experiment.id

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass
class ResearchGraph:
    dependencies: dict[str, set[str]] = field(default_factory=dict)

    def add(self, artifact: str, depends_on: Iterable[str] = ()) -> None:
        self.dependencies.setdefault(artifact, set()).update(depends_on)
        for dep in depends_on: self.dependencies.setdefault(dep, set())

    def downstream(self, changed: str) -> set[str]:
        out: set[str] = set(); frontier = [changed]
        while frontier:
            node = frontier.pop()
            for artifact, deps in self.dependencies.items():
                if node in deps and artifact not in out: out.add(artifact); frontier.append(artifact)
        return out


@dataclass
class ResearchReport:
    title: str
    sections: list[tuple[str, Any]] = field(default_factory=list)

    def add(self, heading: str, value: Any) -> "ResearchReport": self.sections.append((heading, value)); return self

    def to_markdown(self) -> str:
        blocks = [f"# {self.title}"]
        for heading, value in self.sections: blocks += [f"\n## {heading}", self._render(value)]
        return "\n".join(blocks)

    def to_html(self) -> str:
        import html
        body = [f"<h1>{html.escape(self.title)}</h1>"]
        for heading, value in self.sections: body.append(f"<h2>{html.escape(heading)}</h2><pre>{html.escape(self._render(value))}</pre>")
        return "<!doctype html><meta charset='utf-8'><title>" + html.escape(self.title) + "</title>" + "".join(body)

    def to_json(self) -> str:
        return json.dumps({"title": self.title, "sections": [{"heading":h,"value":self._render(v)} for h,v in self.sections]}, indent=2)

    @staticmethod
    def _render(value: Any) -> str:
        if isinstance(value, pd.DataFrame): return value.to_string()
        if isinstance(value, pd.Series): return value.to_string()
        if hasattr(value, "to_dict"):
            try: return json.dumps(value.to_dict(), indent=2, default=_json_default)
            except Exception: pass
        return str(value)


__all__ = ["fingerprint", "DataSnapshot", "DataStore", "Experiment", "ExperimentRegistry", "ResearchGraph", "ResearchReport"]
