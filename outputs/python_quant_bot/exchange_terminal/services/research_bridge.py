from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Iterator
import uuid

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable


AuditWriter = Callable[[dict[str, Any]], Any]


class ResearchBridge:
    """Read-only boundary between Trading Analysis research and Hakimi execution."""

    SCHEMA_NAME = "ResearchBrief"
    CURRENT_SCHEMA_VERSION = "1.1"
    LEGACY_SCHEMA_VERSION = "1.0"
    SUPPORTED_SCHEMA_VERSIONS = (LEGACY_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)
    MAX_IDEMPOTENCY_KEY_BYTES = 128

    PROHIBITED_KEYS = {
        "action", "side", "order", "orders", "order_type", "quantity", "quantity_pct",
        "leverage", "execute", "execution", "account", "api_key", "secret", "password",
    }

    def __init__(
        self,
        *,
        db_path: Path,
        now_ms: Callable[[], int],
        audit_writer: AuditWriter | None = None,
        read_only: bool = False,
    ) -> None:
        self.db_path = db_path
        self.now_ms = now_ms
        self.audit_writer = audit_writer
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
        try:
            yield connection
            if not self.read_only:
                connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_summaries (
                    summary_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    source_project TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL DEFAULT '1.0',
                    idempotency_key TEXT,
                    payload_hash TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_research_summary_symbol
                    ON research_summaries(symbol, created_at DESC);
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(research_summaries)").fetchall()
            }
            if "schema_version" not in columns:
                connection.execute(
                    "ALTER TABLE research_summaries ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1.0'"
                )
            if "idempotency_key" not in columns:
                connection.execute("ALTER TABLE research_summaries ADD COLUMN idempotency_key TEXT")
            if "payload_hash" not in columns:
                connection.execute("ALTER TABLE research_summaries ADD COLUMN payload_hash TEXT")
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_research_summary_idempotency
                    ON research_summaries(idempotency_key)
                    WHERE idempotency_key IS NOT NULL AND idempotency_key <> ''
                """
            )

    @classmethod
    def _normalise_schema_version(cls, value: Any) -> str:
        text = str(value or cls.LEGACY_SCHEMA_VERSION).strip()
        return text or cls.LEGACY_SCHEMA_VERSION

    @classmethod
    def _normalise_idempotency_key(cls, payload: dict[str, Any]) -> str:
        raw = payload.get("idempotency_key")
        if raw is None:
            raw = payload.get("event_id")
        if raw is None:
            return ""
        return str(raw).strip()

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @classmethod
    def _payload_hash(cls, payload: dict[str, Any], schema_version: str) -> str:
        body = dict(payload)
        for field in ("idempotency_key", "event_id", "summary_id", "created_at"):
            body.pop(field, None)
        body["schema_version"] = schema_version
        return hashlib.sha256(cls._canonical_json(body).encode("utf-8")).hexdigest()

    @classmethod
    def _schema_contract(cls) -> dict[str, Any]:
        return {
            "name": cls.SCHEMA_NAME,
            "version": cls.CURRENT_SCHEMA_VERSION,
            "supported_versions": list(cls.SUPPORTED_SCHEMA_VERSIONS),
            "required": [
                "research_only", "symbol", "timeframe", "thesis", "evidence", "counter_evidence",
            ],
            "optional": ["schema_version", "idempotency_key", "event_id"],
            "allowed_examples": [
                "thesis", "evidence", "counter_evidence", "key_levels", "triggers",
                "invalidation", "data_freshness", "source_refs",
            ],
            "forbidden": sorted(cls.PROHIBITED_KEYS),
            "execution_semantics": "none",
            "live_order_allowed": False,
        }

    def _find_prohibited(self, value: Any, path: str = "") -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            for key, child in value.items():
                clean_key = str(key).lower()
                child_path = f"{path}.{clean_key}" if path else clean_key
                if clean_key in self.PROHIBITED_KEYS:
                    found.append(child_path)
                found.extend(self._find_prohibited(child, child_path))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found.extend(self._find_prohibited(child, f"{path}[{index}]"))
        return found

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"ok": False, "errors": ["Payload must be an object."]}
        errors: list[str] = []
        schema_version = self._normalise_schema_version(payload.get("schema_version"))
        if schema_version not in self.SUPPORTED_SCHEMA_VERSIONS:
            errors.append(f"Unsupported ResearchBrief schema version: {schema_version}.")
        idempotency_key = self._normalise_idempotency_key(payload)
        if len(idempotency_key.encode("utf-8")) > self.MAX_IDEMPOTENCY_KEY_BYTES:
            errors.append("idempotency_key exceeds 128 UTF-8 bytes.")
        if any(char in idempotency_key for char in ("\r", "\n", "\x00")):
            errors.append("idempotency_key contains a control character.")
        if payload.get("research_only") is not True:
            errors.append("research_only must be true.")
        if not str(payload.get("symbol") or "").strip():
            errors.append("symbol is required.")
        if not str(payload.get("timeframe") or "").strip():
            errors.append("timeframe is required.")
        prohibited = self._find_prohibited(payload)
        if prohibited:
            errors.append("Execution fields are forbidden: " + ", ".join(sorted(set(prohibited))))
        size = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
        if size > 120_000:
            errors.append("Research summary exceeds 120 KB.")
        return {
            "ok": not errors,
            "errors": errors,
            "prohibited_fields": prohibited,
            "size_bytes": size,
            "schema_version": schema_version,
            "idempotency_key_present": bool(idempotency_key),
        }

    def import_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="research_bridge")
        validation = self.validate(payload)
        if not validation["ok"]:
            return {
                "ok": False,
                "status": "REJECTED",
                "validation": validation,
                "live_order_allowed": False,
            }
        schema_version = str(validation["schema_version"])
        idempotency_key = self._normalise_idempotency_key(payload)
        payload_hash = self._payload_hash(payload, schema_version)
        timestamp = self.now_ms()
        summary = {
            **payload,
            "summary_id": f"research-{timestamp}-{uuid.uuid4().hex[:8]}",
            "symbol": str(payload["symbol"]).upper(),
            "timeframe": str(payload["timeframe"]),
            "source_project": str(payload.get("source_project") or "trading-analysis"),
            "created_at": timestamp,
            "schema_version": schema_version,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "research_only": True,
            "live_order_allowed": False,
        }
        with self._lock, self._connect() as connection:
            if idempotency_key:
                existing_row = connection.execute(
                    """
                    SELECT payload_json, payload_hash
                    FROM research_summaries
                    WHERE idempotency_key = ?
                    LIMIT 1
                    """,
                    (idempotency_key,),
                ).fetchone()
                if existing_row is not None:
                    existing = json.loads(existing_row["payload_json"])
                    existing_hash = str(existing_row["payload_hash"] or existing.get("payload_hash") or "")
                    if existing_hash != payload_hash:
                        return {
                            "ok": False,
                            "status": "IDEMPOTENCY_CONFLICT",
                            "error": "idempotency_key already contains a different ResearchBrief payload.",
                            "validation": validation,
                            "live_order_allowed": False,
                        }
                    return {
                        "ok": True,
                        "status": "IDEMPOTENT_REPLAY",
                        "summary": existing,
                        "validation": validation,
                        "live_order_allowed": False,
                    }
            connection.execute(
                """
                INSERT INTO research_summaries(
                    summary_id, symbol, timeframe, source_project, created_at, payload_json,
                    schema_version, idempotency_key, payload_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary["summary_id"], summary["symbol"], summary["timeframe"],
                    summary["source_project"], summary["created_at"],
                    json.dumps(summary, ensure_ascii=False, default=str),
                    schema_version, idempotency_key or None, payload_hash,
                ),
            )
        if self.audit_writer:
            self.audit_writer({
                "type": "research_summary_imported",
                "summary_id": summary["summary_id"],
                "symbol": summary["symbol"],
                "source": summary["source_project"],
            })
        return {
            "ok": True,
            "status": "IMPORTED",
            "summary": summary,
            "validation": validation,
            "live_order_allowed": False,
        }

    def list(self, symbol: str = "", limit: int = 30) -> list[dict[str, Any]]:
        sql = "SELECT payload_json FROM research_summaries"
        params: list[Any] = []
        if symbol:
            sql += " WHERE symbol = ?"
            params.append(symbol.upper())
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit or 30), 200)))
        with self._lock, self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    @staticmethod
    def schema() -> dict[str, Any]:
        contract = ResearchBridge._schema_contract()
        return {
            **contract,
            "contract_hash": hashlib.sha256(
                ResearchBridge._canonical_json(contract).encode("utf-8")
            ).hexdigest(),
        }
