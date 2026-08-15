from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Iterator

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable


class AuditLog:
    def __init__(
        self,
        *,
        path: Path,
        ensure_runtime: Callable[[], None],
        now_ms: Callable[[], int],
        publish_event: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        db_path: Path | None = None,
        read_only: bool = False,
    ) -> None:
        self.path = path
        self.db_path = db_path or path.with_suffix(".sqlite3")
        self.ensure_runtime = ensure_runtime
        self.now_ms = now_ms
        self.publish_event = publish_event
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
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
            if not self.read_only:
                connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock:
            self.ensure_runtime()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_seq INTEGER,
                        time INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        source TEXT,
                        run_id TEXT,
                        strategy_id TEXT,
                        symbol TEXT,
                        signal_id TEXT,
                        order_id TEXT,
                        request_id TEXT,
                        snapshot_id TEXT,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_audit_events_type_id ON audit_events(type, id DESC);
                    CREATE INDEX IF NOT EXISTS idx_audit_events_run_id ON audit_events(run_id, id DESC);
                    CREATE INDEX IF NOT EXISTS idx_audit_events_symbol ON audit_events(symbol, id DESC);
                    CREATE TABLE IF NOT EXISTS audit_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    """
                )
                columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(audit_events)").fetchall()}
                for column in ("signal_id", "order_id", "request_id", "snapshot_id"):
                    if column not in columns:
                        connection.execute(f"ALTER TABLE audit_events ADD COLUMN {column} TEXT")
                    connection.execute(f"CREATE INDEX IF NOT EXISTS idx_audit_events_{column} ON audit_events({column}, id DESC)")
                migrated = connection.execute("SELECT value FROM audit_meta WHERE key='legacy_jsonl_migrated'").fetchone()
                if not migrated:
                    self._migrate_jsonl(connection)
                    connection.execute(
                        "INSERT OR REPLACE INTO audit_meta(key, value) VALUES('legacy_jsonl_migrated', ?)",
                        (str(self.now_ms()),),
                    )

    def _insert(self, connection: sqlite3.Connection, row: dict[str, Any]) -> None:
        def indexed_text(value: Any) -> Any:
            if value is None or isinstance(value, (str, int, float, bytes)):
                return value
            return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)

        connection.execute(
            """
            INSERT INTO audit_events(
                event_seq, time, type, source, run_id, strategy_id, symbol,
                signal_id, order_id, request_id, snapshot_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("event_seq"),
                int(row.get("time") or self.now_ms()),
                str(row.get("type") or "audit_event"),
                indexed_text(row.get("source")),
                indexed_text(row.get("run_id")),
                indexed_text(row.get("strategy_id")),
                indexed_text(row.get("symbol")),
                indexed_text(row.get("signal_id")),
                indexed_text(row.get("order_id")),
                indexed_text(row.get("request_id") or row.get("risk_request_id")),
                indexed_text(row.get("snapshot_id") or row.get("market_snapshot_id")),
                json.dumps(row, ensure_ascii=False, default=str),
            ),
        )

    def _migrate_jsonl(self, connection: sqlite3.Connection) -> None:
        if not self.path.exists() or self.path.suffix.lower() not in {".jsonl", ".log", ".txt"}:
            return
        for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                self._insert(connection, row)

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="audit_log")
        with self._lock:
            self.ensure_runtime()
            event_type = str(event.get("type") or "audit_event")
            row = {"time": self.now_ms(), **event}
            if self.publish_event:
                bus_event = self.publish_event(event_type, row)
                row["event_seq"] = bus_event.get("seq")
            with self._connect() as connection:
                self._insert(connection, row)
        return row

    def read(self, limit: int = 120, event_type: str = "") -> list[dict[str, Any]]:
        with self._lock:
            limit = max(1, min(int(limit or 120), 5000))
            sql = "SELECT payload_json FROM audit_events"
            params: list[Any] = []
            if event_type:
                sql += " WHERE type = ?"
                params.append(event_type)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            with self._connect() as connection:
                records = connection.execute(sql, params).fetchall()
        return [json.loads(record["payload_json"]) for record in reversed(records)]

    def query(
        self,
        *,
        limit: int = 120,
        event_type: str = "",
        run_id: str = "",
        symbol: str = "",
        signal_id: str = "",
        order_id: str = "",
        request_id: str = "",
        snapshot_id: str = "",
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if event_type:
            clauses.append("type = ?")
            params.append(event_type)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(signal_id)
        if order_id:
            clauses.append("order_id = ?")
            params.append(order_id)
        if request_id:
            clauses.append("request_id = ?")
            params.append(request_id)
        if snapshot_id:
            clauses.append("snapshot_id = ?")
            params.append(snapshot_id)
        sql = "SELECT payload_json FROM audit_events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(int(limit or 120), 5000)))
        with self._lock, self._connect() as connection:
            records = connection.execute(sql, params).fetchall()
        return [json.loads(record["payload_json"]) for record in reversed(records)]

    def summary(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
            rows = connection.execute(
                "SELECT type, COUNT(*) AS count FROM audit_events GROUP BY type ORDER BY count DESC LIMIT 12"
            ).fetchall()
        return {
            "ok": True,
            "backend": "sqlite",
            "db_path": str(self.db_path),
            "event_count": total,
            "counts": {str(row["type"]): int(row["count"]) for row in rows},
        }
