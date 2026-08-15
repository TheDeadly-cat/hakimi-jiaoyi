from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Iterator

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable


MAX_IDEMPOTENCY_KEY_LENGTH = 160


class MutationJournal:
    """Persistent idempotency registry for local state-changing HTTP requests."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        now_ms: Callable[[], int],
        stale_after_ms: int = 60_000,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
        self.stale_after_ms = max(int(stale_after_ms), 5_000)
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if not self.read_only:
            self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = connect_runtime_sqlite(self.db_path, read_only=self.read_only)
        connection.row_factory = sqlite3.Row
        if not self.read_only:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
            if not self.read_only:
                connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS mutation_requests (
                    idempotency_key TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    http_status INTEGER NOT NULL DEFAULT 0,
                    response_json TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mutation_requests_updated
                    ON mutation_requests(updated_at DESC);
                """
            )

    @staticmethod
    def _fingerprint(path: str, payload: dict[str, Any]) -> str:
        clean_payload = {key: value for key, value in payload.items() if key != "idempotencyKey"}
        canonical = json.dumps(
            {"path": path, "payload": clean_payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def begin(self, path: str, idempotency_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="mutation_journal")
        if not isinstance(idempotency_key, str):
            return {"status": "INVALID", "error": "idempotency key must be a string"}
        clean_key = idempotency_key.strip()
        if len(clean_key) < 8:
            return {"status": "INVALID", "error": "idempotency key must contain at least 8 characters"}
        if len(clean_key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            return {
                "status": "INVALID",
                "error": f"idempotency key must contain at most {MAX_IDEMPOTENCY_KEY_LENGTH} characters",
            }
        fingerprint = self._fingerprint(path, payload)
        timestamp = self.now_ms()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM mutation_requests WHERE idempotency_key = ?",
                (clean_key,),
            ).fetchone()
            if row:
                if str(row["path"]) != path or str(row["fingerprint"]) != fingerprint:
                    return {"status": "CONFLICT", "error": "idempotency key was already used for a different request"}
                if str(row["status"]) == "COMPLETE":
                    return {
                        "status": "REPLAY",
                        "http_status": int(row["http_status"]),
                        "response": json.loads(row["response_json"]),
                    }
                age_ms = max(timestamp - int(row["updated_at"]), 0)
                if age_ms <= self.stale_after_ms:
                    return {"status": "IN_PROGRESS", "error": "request with this idempotency key is still in progress"}
                connection.execute("DELETE FROM mutation_requests WHERE idempotency_key = ?", (clean_key,))
            connection.execute(
                """
                INSERT INTO mutation_requests(
                    idempotency_key, path, fingerprint, status, http_status,
                    response_json, created_at, updated_at
                ) VALUES(?, ?, ?, 'IN_PROGRESS', 0, '{}', ?, ?)
                """,
                (clean_key, path, fingerprint, timestamp, timestamp),
            )
        return {"status": "NEW", "idempotency_key": clean_key, "fingerprint": fingerprint}

    def complete(self, idempotency_key: str, http_status: int, response: dict[str, Any]) -> None:
        require_runtime_writable(read_only=self.read_only, service="mutation_journal")
        clean_key = str(idempotency_key or "").strip()
        if not clean_key:
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE mutation_requests
                SET status = 'COMPLETE', http_status = ?, response_json = ?, updated_at = ?
                WHERE idempotency_key = ?
                """,
                (
                    int(http_status),
                    json.dumps(response, ensure_ascii=False, separators=(",", ":"), default=str),
                    self.now_ms(),
                    clean_key,
                ),
            )
            connection.execute(
                """
                DELETE FROM mutation_requests
                WHERE idempotency_key NOT IN (
                    SELECT idempotency_key FROM mutation_requests ORDER BY updated_at DESC LIMIT 5000
                )
                """
            )

    def abandon(self, idempotency_key: str) -> None:
        require_runtime_writable(read_only=self.read_only, service="mutation_journal")
        clean_key = str(idempotency_key or "").strip()
        if not clean_key:
            return
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM mutation_requests WHERE idempotency_key = ?", (clean_key,))

    def summary(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM mutation_requests GROUP BY status"
            ).fetchall()
        return {
            "ok": True,
            "backend": "sqlite",
            "db_path": str(self.db_path),
            "counts": {str(row["status"]): int(row["count"]) for row in rows},
        }
