"""Dependency graph for research artifacts and stale-result propagation."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

import pandas as pd

from .contracts import ResearchError


def _fingerprint(value: Any) -> str:
    if hasattr(value, "fingerprint"):
        return str(value.fingerprint)
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()[:16]


@dataclass(frozen=True)
class ResearchArtifact:
    name: str
    fingerprint: str
    depends_on: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ResearchGraph:
    """Acyclic artifact graph with lineage and stale-result propagation.

    Dependencies must already exist when a node is added. This makes cycles
    impossible by construction and keeps the graph deterministic.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, ResearchArtifact] = {}

    def add(
        self,
        name: str,
        value: Any = None,
        *,
        depends_on: Iterable[str] = (),
        fingerprint: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ResearchArtifact:
        key = str(name).strip()
        if not key:
            raise ResearchError("artifact name must not be empty")
        if key in self._nodes:
            raise ResearchError(f"artifact {key!r} already exists")
        deps = tuple(str(x) for x in depends_on)
        missing = [dep for dep in deps if dep not in self._nodes]
        if missing:
            raise ResearchError(f"dependencies must be added first: {missing}")
        fp = str(fingerprint) if fingerprint is not None else _fingerprint(value)
        artifact = ResearchArtifact(key, fp, deps, dict(metadata or {}))
        self._nodes[key] = artifact
        return artifact

    def get(self, name: str) -> ResearchArtifact:
        try:
            return self._nodes[name]
        except KeyError as exc:
            raise ResearchError(f"unknown research artifact {name!r}") from exc

    def dependencies(self, name: str, *, transitive: bool = False) -> tuple[str, ...]:
        node = self.get(name)
        if not transitive:
            return node.depends_on
        seen: set[str] = set()
        stack = list(node.depends_on)
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._nodes[current].depends_on)
        return tuple(item for item in self._nodes if item in seen)

    def downstream(self, name: str) -> tuple[str, ...]:
        self.get(name)
        affected: set[str] = set()
        frontier = {name}
        while frontier:
            next_frontier: set[str] = set()
            for node_name, node in self._nodes.items():
                if node_name in affected or node_name == name:
                    continue
                if any(dep in frontier for dep in node.depends_on):
                    affected.add(node_name)
                    next_frontier.add(node_name)
            frontier = next_frontier
        return tuple(item for item in self._nodes if item in affected)

    def stale_artifacts(self, changed: str | Iterable[str]) -> tuple[str, ...]:
        changed_names = (changed,) if isinstance(changed, str) else tuple(changed)
        affected: set[str] = set()
        for name in changed_names:
            affected.update(self.downstream(name))
        return tuple(item for item in self._nodes if item in affected)

    def lineage(self, name: str) -> pd.DataFrame:
        wanted = set(self.dependencies(name, transitive=True)) | {name}
        rows = [
            {
                "artifact": node.name,
                "fingerprint": node.fingerprint,
                "depends_on": node.depends_on,
            }
            for node in self._nodes.values()
            if node.name in wanted
        ]
        return pd.DataFrame(rows).set_index("artifact")

    def to_frame(self) -> pd.DataFrame:
        rows = [
            {
                "artifact": node.name,
                "fingerprint": node.fingerprint,
                "depends_on": node.depends_on,
                "n_dependencies": len(node.depends_on),
            }
            for node in self._nodes.values()
        ]
        return pd.DataFrame(rows).set_index("artifact") if rows else pd.DataFrame(columns=["fingerprint", "depends_on", "n_dependencies"])

    def manifest(self) -> dict[str, Any]:
        return {
            "artifacts": [
                {
                    "name": node.name,
                    "fingerprint": node.fingerprint,
                    "depends_on": list(node.depends_on),
                    "metadata": dict(node.metadata),
                }
                for node in self._nodes.values()
            ]
        }


__all__ = ["ResearchArtifact", "ResearchGraph"]
