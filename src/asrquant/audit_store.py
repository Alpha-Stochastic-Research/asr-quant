"""Durable tamper-evident event storage for production trading workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any
import uuid

from .production import canonical_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_lastrowid(cursor: sqlite3.Cursor) -> int:
    """Return the SQLite row ID or fail explicitly."""
    lastrowid = cursor.lastrowid
    if lastrowid is None:
        raise RuntimeError(
            "SQLite completed the INSERT without returning a row ID."
        )
    return lastrowid


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_id: str
    timestamp: str
    event_type: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class SQLiteAuditStore:
    """Append-only SQLite event log protected by a SHA-256 hash chain.

    SQLite is suitable for a single-node deployment or local execution gateway.
    A distributed deployment should replace this implementation with a durable
    transactional store while preserving the same append/read/verify contract.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_type_time "
                "ON audit_events(event_type, timestamp)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    idempotency_key TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES audit_events(event_id)
                )
                """
            )

    @staticmethod
    def _hash_event(
        *,
        event_id: str,
        timestamp: str,
        event_type: str,
        payload_json: str,
        previous_hash: str,
    ) -> str:
        material = canonical_json(
            {
                "event_id": event_id,
                "timestamp": timestamp,
                "event_type": event_type,
                "payload_json": payload_json,
                "previous_hash": previous_hash,
            }
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def append(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        timestamp: str | None = None,
    ) -> AuditEvent:
        if not event_type.strip():
            raise ValueError("event_type is required")

        identifier = event_id or uuid.uuid4().hex
        created_at = timestamp or _now()
        payload_json = canonical_json(payload or {})

        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    existing = self._connection.execute(
                        """
                        SELECT e.*
                        FROM idempotency_keys AS i
                        JOIN audit_events AS e ON e.event_id = i.event_id
                        WHERE i.idempotency_key = ?
                        """,
                        (idempotency_key,),
                    ).fetchone()
                    if existing is not None:
                        self._connection.execute("COMMIT")
                        return self._from_row(existing)

                last = self._connection.execute(
                    "SELECT event_hash "
                    "FROM audit_events "
                    "ORDER BY sequence DESC "
                    "LIMIT 1"
                ).fetchone()
                previous_hash = str(last["event_hash"]) if last else "0" * 64

                event_hash = self._hash_event(
                    event_id=identifier,
                    timestamp=created_at,
                    event_type=event_type,
                    payload_json=payload_json,
                    previous_hash=previous_hash,
                )

                cursor = self._connection.execute(
                    """
                    INSERT INTO audit_events(
                        event_id,
                        timestamp,
                        event_type,
                        payload_json,
                        previous_hash,
                        event_hash
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        created_at,
                        event_type,
                        payload_json,
                        previous_hash,
                        event_hash,
                    ),
                )

                if idempotency_key:
                    self._connection.execute(
                        """
                        INSERT INTO idempotency_keys(
                            idempotency_key,
                            event_id,
                            created_at
                        ) VALUES (?, ?, ?)
                        """,
                        (idempotency_key, identifier, created_at),
                    )

                sequence = _require_lastrowid(cursor)
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

        return AuditEvent(
            sequence=sequence,
            event_id=identifier,
            timestamp=created_at,
            event_type=event_type,
            payload=json.loads(payload_json),
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> AuditEvent:
        return AuditEvent(
            sequence=int(row["sequence"]),
            event_id=str(row["event_id"]),
            timestamp=str(row["timestamp"]),
            event_type=str(row["event_type"]),
            payload=json.loads(str(row["payload_json"])),
            previous_hash=str(row["previous_hash"]),
            event_hash=str(row["event_hash"]),
        )

    def events(
        self,
        *,
        event_type: str | None = None,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        after = int(after_sequence)
        normalized_limit = None if limit is None else int(limit)

        if normalized_limit is not None and normalized_limit <= 0:
            return []

        with self._lock:
            if event_type is None and normalized_limit is None:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE sequence > ?
                    ORDER BY sequence
                    """,
                    (after,),
                ).fetchall()

            elif event_type is None:
                assert normalized_limit is not None
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE sequence > ?
                    ORDER BY sequence
                    LIMIT ?
                    """,
                    (after, normalized_limit),
                ).fetchall()

            elif normalized_limit is None:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE sequence > ?
                      AND event_type = ?
                    ORDER BY sequence
                    """,
                    (after, event_type),
                ).fetchall()

            else:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE sequence > ?
                      AND event_type = ?
                    ORDER BY sequence
                    LIMIT ?
                    """,
                    (after, event_type, normalized_limit),
                ).fetchall()

        return [self._from_row(row) for row in rows]

    def verify_chain(self) -> tuple[bool, int | None]:
        previous_hash = "0" * 64
        for event in self.events():
            payload_json = canonical_json(event.payload)
            expected = self._hash_event(
                event_id=event.event_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                payload_json=payload_json,
                previous_hash=previous_hash,
            )
            if event.previous_hash != previous_hash or event.event_hash != expected:
                return False, event.sequence
            previous_hash = event.event_hash
        return True, None

    def latest(self, event_type: str | None = None) -> AuditEvent | None:
        with self._lock:
            if event_type is None:
                row = self._connection.execute(
                    "SELECT * FROM audit_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
            else:
                row = self._connection.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE event_type = ?
                    ORDER BY sequence DESC
                    LIMIT 1
                    """,
                    (event_type,),
                ).fetchone()

        return self._from_row(row) if row is not None else None

    def checkpoint(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA wal_checkpoint(FULL)")

    def backup(self, destination: str | Path) -> Path:
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            target = sqlite3.connect(str(output))
            try:
                self._connection.backup(target)
            finally:
                target.close()

        return output

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> SQLiteAuditStore:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


__all__ = ["AuditEvent", "SQLiteAuditStore"]
