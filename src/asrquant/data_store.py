"""Research data snapshots, local cache, and point-in-time availability contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from .contracts import DataValidationError, ResultMixin


def _frame_hash(frame: pd.DataFrame) -> str:
    h = pd.util.hash_pandas_object(frame, index=True).to_numpy(dtype=np.uint64).tobytes()
    h += json.dumps([str(c) for c in frame.columns], sort_keys=True).encode("utf-8")
    h += json.dumps([str(t) for t in frame.dtypes], sort_keys=True).encode("utf-8")
    return sha256(h).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DataSnapshot(ResultMixin):
    data: pd.DataFrame
    source: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    result_type: str = field(default="data_snapshot", init=False)

    def __post_init__(self) -> None:
        self.data = pd.DataFrame(self.data).copy()
        if self.data.empty:
            raise DataValidationError("cannot snapshot empty data")
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)

    @property
    def hash(self) -> str:
        return _frame_hash(self.data)

    @property
    def schema(self) -> dict[str, str]:
        return {str(c): str(t) for c, t in self.data.dtypes.items()}

    @property
    def summary(self) -> pd.Series:
        index = self.data.index
        return pd.Series(
            {
                "hash": self.hash,
                "rows": int(len(self.data)),
                "columns": int(self.data.shape[1]),
                "source": self.source,
                "created_at": self.created_at.isoformat(),
                "start": str(index.min()) if len(index) else None,
                "end": str(index.max()) if len(index) else None,
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return self.data.copy()

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "summary": self.summary.to_dict(),
            "schema": self.schema,
            "metadata": dict(self.metadata),
        }

    def save(self, directory: str | Path) -> Path:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        stem = self.hash
        data_path = root / f"{stem}.csv.gz"
        meta_path = root / f"{stem}.json"
        self.data.to_csv(data_path, compression="gzip", index=True, index_label="__index__")
        meta = {
            "hash": self.hash,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "schema": self.schema,
            "metadata": self.metadata,
            "index_name": self.data.index.name,
        }
        meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        return meta_path

    @classmethod
    def load(cls, metadata_path: str | Path) -> "DataSnapshot":
        meta_path = Path(metadata_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        data_path = meta_path.with_suffix(".csv.gz")
        frame = pd.read_csv(data_path, index_col="__index__")
        # Recover datetime indexes when lossless parsing is possible.
        try:
            parsed = pd.to_datetime(frame.index)
            if not parsed.isna().any():
                frame.index = parsed
        except Exception:
            pass
        frame.index.name = meta.get("index_name")
        snap = cls(
            frame,
            source=meta.get("source"),
            created_at=datetime.fromisoformat(meta["created_at"]),
            metadata=dict(meta.get("metadata") or {}),
        )
        if snap.hash != meta["hash"]:
            raise DataValidationError("snapshot hash mismatch; cached data may be corrupted")
        return snap


def snapshot(data: pd.Series | pd.DataFrame, *, source: str | None = None, metadata: Mapping[str, Any] | None = None) -> DataSnapshot:
    frame = data.to_frame() if isinstance(data, pd.Series) else pd.DataFrame(data)
    return DataSnapshot(frame, source=source, metadata=dict(metadata or {}))


class DataStore:
    """Local research cache with explicit freshness and offline semantics."""

    def __init__(self, root: str | Path = ".asrquant-data", *, offline: bool = False) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir(exist_ok=True)
        self.index_path = self.root / "index.json"
        self.offline = bool(offline)

    def _index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write_index(self, value: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")

    def put(
        self,
        key: str,
        data: pd.Series | pd.DataFrame,
        *,
        source: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> DataSnapshot:
        snap = snapshot(data, source=source, metadata=metadata)
        meta_path = snap.save(self.snapshots)
        idx = self._index()
        idx[str(key)] = {"metadata_path": str(meta_path.relative_to(self.root)), "created_at": snap.created_at.isoformat(), "hash": snap.hash}
        self._write_index(idx)
        return snap

    def get(self, key: str, *, max_age_seconds: float | None = None) -> DataSnapshot:
        idx = self._index()
        if key not in idx:
            raise KeyError(key)
        entry = idx[key]
        snap = DataSnapshot.load(self.root / entry["metadata_path"])
        if max_age_seconds is not None:
            age = (_utc_now() - snap.created_at.astimezone(timezone.utc)).total_seconds()
            if age > max_age_seconds:
                raise DataValidationError(f"cached dataset {key!r} is stale ({age:.0f}s > {max_age_seconds:.0f}s)")
        return snap

    def fetch(
        self,
        key: str,
        loader: Callable[..., pd.Series | pd.DataFrame],
        *args: Any,
        refresh_seconds: float | None = None,
        force: bool = False,
        source: str | None = None,
        **kwargs: Any,
    ) -> DataSnapshot:
        if not force:
            try:
                return self.get(key, max_age_seconds=refresh_seconds)
            except (KeyError, DataValidationError):
                pass
        if self.offline:
            try:
                return self.get(key)
            except KeyError as exc:
                raise DataValidationError(f"offline mode: no cached dataset for {key!r}") from exc
        loaded = loader(*args, **kwargs)
        return self.put(key, loaded, source=source or getattr(loader, "__name__", None))

    def list(self) -> pd.DataFrame:
        idx = self._index()
        rows = [{"key": key, **entry} for key, entry in idx.items()]
        return pd.DataFrame(rows).set_index("key") if rows else pd.DataFrame(columns=["metadata_path", "created_at", "hash"])


@dataclass(frozen=True)
class PointInTimeFrame:
    """Tabular data carrying observation, availability and revision timestamps."""

    data: pd.DataFrame
    observation_column: str = "observation_date"
    available_column: str = "available_date"
    revision_column: str | None = "revision_date"

    def __post_init__(self) -> None:
        frame = pd.DataFrame(self.data).copy()
        required = {self.observation_column, self.available_column}
        missing = required.difference(frame.columns)
        if missing:
            raise DataValidationError(f"point-in-time data missing columns: {sorted(missing)}")
        for col in [self.observation_column, self.available_column] + ([self.revision_column] if self.revision_column and self.revision_column in frame else []):
            if col:
                frame[col] = pd.to_datetime(frame[col], errors="raise")
        if (frame[self.available_column] < frame[self.observation_column]).any():
            raise DataValidationError("available_date cannot precede observation_date")
        if self.revision_column and self.revision_column in frame:
            bad = frame[self.revision_column].notna() & (frame[self.revision_column] < frame[self.available_column])
            if bad.any():
                raise DataValidationError("revision_date cannot precede available_date")
        object.__setattr__(self, "data", frame.sort_values([self.observation_column, self.available_column]))

    def as_of(self, timestamp: str | pd.Timestamp) -> pd.DataFrame:
        ts = pd.Timestamp(timestamp)
        frame = self.data[self.data[self.available_column] <= ts].copy()
        if self.revision_column and self.revision_column in frame:
            revision = frame[self.revision_column].fillna(frame[self.available_column])
            frame = frame.loc[revision <= ts].copy()
            frame["__effective_revision__"] = revision.loc[frame.index]
            frame = frame.sort_values([self.observation_column, "__effective_revision__"])
            frame = frame.groupby(self.observation_column, as_index=False).tail(1).drop(columns="__effective_revision__")
        else:
            frame = frame.sort_values([self.observation_column, self.available_column])
            frame = frame.groupby(self.observation_column, as_index=False).tail(1)
        return frame.sort_values(self.observation_column).reset_index(drop=True)

    def available_on(self, decision_time: str | pd.Timestamp) -> pd.DataFrame:
        return self.as_of(decision_time)

    def audit(self) -> pd.Series:
        return pd.Series(
            {
                "rows": len(self.data),
                "observations": self.data[self.observation_column].nunique(),
                "revisions": len(self.data) - self.data[self.observation_column].nunique(),
                "min_availability_lag_days": float((self.data[self.available_column] - self.data[self.observation_column]).dt.total_seconds().min() / 86400.0),
                "max_availability_lag_days": float((self.data[self.available_column] - self.data[self.observation_column]).dt.total_seconds().max() / 86400.0),
            }
        )


__all__ = ["DataSnapshot", "DataStore", "PointInTimeFrame", "snapshot"]
