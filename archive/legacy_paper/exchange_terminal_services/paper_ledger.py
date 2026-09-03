from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any, Callable

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable

try:
    from services.paper_order_contract import validate_paper_lifecycle_order
except ModuleNotFoundError:
    try:
        from .paper_order_contract import validate_paper_lifecycle_order
    except ImportError:
        from exchange_terminal.services.paper_order_contract import validate_paper_lifecycle_order


AuditWriter = Callable[[dict[str, Any]], Any]


class PaperLedger:
    """Transactional source of truth for the paper account and order lifecycle."""

    SCHEMA_VERSION = 4
    MAX_RECONCILIATION_RETRIES = 8
    TERMINAL_STATES = {"FILLED", "CANCELLED", "REJECTED", "EXPIRED"}
    IMMUTABLE_ORDER_FIELDS = (
        "order_id",
        "account_id",
        "symbol",
        "side",
        "order_type",
        "mark_price",
        "limit_price",
        "requested_notional",
        "requested_qty",
        "quantity_constrained",
        "source",
        "strategy_id",
        "run_id",
        "market_snapshot_id",
        "risk_request_id",
        "signal_id",
        "signal_created_at",
        "signal_action",
        "signal_reason",
        "position_side_before",
        "reduce_only",
        "idempotency_key",
        "request_signature",
        "created_at",
    )

    def __init__(
        self,
        *,
        db_path: Path | str,
        now_ms: Callable[[], int],
        audit_writer: AuditWriter | None = None,
        account_id: str = "default",
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
        self.audit_writer = audit_writer
        self.account_id = str(account_id or "default")
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if not self.read_only:
            self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_runtime_sqlite(self.db_path, read_only=self.read_only)
        connection.row_factory = sqlite3.Row
        if not self.read_only:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _require_writable(self) -> None:
        require_runtime_writable(read_only=self.read_only, service="paper_ledger")

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (str(table_name),),
        ).fetchone()
        return row is not None

    @classmethod
    def _lifecycle_schema_profile(cls, connection: sqlite3.Connection) -> dict[str, Any]:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(paper_lifecycle_orders)").fetchall()
        }
        schema_version = 0
        if cls._table_exists(connection, "paper_schema"):
            row = connection.execute(
                "SELECT value FROM paper_schema WHERE key = 'schema_version'"
            ).fetchone()
            try:
                schema_version = int(row["value"] if row else 0)
            except (TypeError, ValueError):
                schema_version = 0

        unique_risk_request = False
        if columns:
            for index_row in connection.execute("PRAGMA index_list(paper_lifecycle_orders)").fetchall():
                if not bool(index_row["unique"]):
                    continue
                index_name = str(index_row["name"])
                escaped_index_name = index_name.replace('"', '""')
                index_columns = [
                    str(row["name"])
                    for row in connection.execute(
                        f'PRAGMA index_info("{escaped_index_name}")'
                    ).fetchall()
                ]
                if index_columns == ["risk_request_id"]:
                    unique_risk_request = True
                    break
        return {
            "has_lifecycle_table": bool(columns),
            "columns": columns,
            "has_account_id": "account_id" in columns,
            "has_unique_risk_request": unique_risk_request,
            "schema_version": schema_version,
        }

    def _lifecycle_account_scope(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[dict[str, Any], str, tuple[Any, ...]]:
        profile = self._lifecycle_schema_profile(connection)
        if not profile["has_lifecycle_table"]:
            raise ValueError("paper_lifecycle_schema_missing")
        if profile["has_account_id"]:
            return profile, "account_id = ?", (self.account_id,)
        if not self.read_only:
            raise ValueError("paper_lifecycle_schema_migration_required")
        if self.account_id != "default":
            raise ValueError("paper_legacy_schema_account_isolation_block")
        return profile, "", ()

    def _decode_lifecycle_payload(
        self,
        payload_json: str,
        *,
        legacy_schema: bool,
    ) -> dict[str, Any]:
        raw = json.loads(payload_json)
        if not isinstance(raw, dict):
            raise ValueError("paper_lifecycle_payload_invalid")
        order = dict(raw)
        if legacy_schema:
            stored_account_id = str(order.get("account_id") or "default").strip()
            if stored_account_id != "default":
                raise ValueError("paper_legacy_schema_account_conflict")
            # G41 payloads predate account isolation.  Normalize only the
            # in-memory copy; the read-only database remains byte-identical.
            order["account_id"] = "default"
        validate_paper_lifecycle_order(order)
        if str(order.get("account_id") or "").strip() != self.account_id:
            raise ValueError("paper_lifecycle_account_conflict")
        return order

    def _ensure_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS paper_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_account_state (
                    account_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    UNIQUE(account_id, version)
                );
                CREATE TABLE IF NOT EXISTS paper_balances (
                    account_id TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    cash REAL NOT NULL,
                    short_margin REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    equity REAL NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY(account_id, currency)
                );
                CREATE TABLE IF NOT EXISTS paper_positions (
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    side TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY(account_id, symbol)
                );
                CREATE TABLE IF NOT EXISTS paper_account_orders (
                    account_order_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    lifecycle_order_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_conditions (
                    condition_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_equity (
                    account_id TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    equity REAL NOT NULL,
                    PRIMARY KEY(account_id, observed_at)
                );
                CREATE TABLE IF NOT EXISTS paper_lifecycle_orders (
                    order_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL DEFAULT 'default',
                    idempotency_key TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    state TEXT NOT NULL,
                    risk_request_id TEXT,
                    market_snapshot_id TEXT,
                    strategy_id TEXT,
                    run_id TEXT,
                    account_applied INTEGER NOT NULL DEFAULT 0,
                    account_version INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_order_transitions (
                    order_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    occurred_at INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    PRIMARY KEY(order_id, sequence),
                    FOREIGN KEY(order_id) REFERENCES paper_lifecycle_orders(order_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS paper_fills (
                    fill_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    notional REAL NOT NULL,
                    fee REAL NOT NULL,
                    funding REAL NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES paper_lifecycle_orders(order_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_paper_lifecycle_created
                    ON paper_lifecycle_orders(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_paper_lifecycle_run
                    ON paper_lifecycle_orders(run_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_paper_snapshots_created
                    ON paper_account_snapshots(created_at DESC);
                """
            )
            schema_row = connection.execute(
                "SELECT value FROM paper_schema WHERE key = 'schema_version'"
            ).fetchone()
            try:
                previous_schema_version = int(schema_row["value"] if schema_row else 0)
            except (TypeError, ValueError):
                previous_schema_version = 0
            connection.execute("BEGIN IMMEDIATE")
            if previous_schema_version < 2:
                fill_rows = connection.execute("SELECT fill_id, payload_json FROM paper_fills").fetchall()
                for fill_row in fill_rows:
                    try:
                        report = json.loads(fill_row["payload_json"])
                        funding_charged = float(report.get("funding_charged") or 0.0)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        funding_charged = 0.0
                    if not math.isfinite(funding_charged):
                        funding_charged = 0.0
                    connection.execute(
                        "UPDATE paper_fills SET funding = ? WHERE fill_id = ?",
                        (funding_charged, str(fill_row["fill_id"])),
                    )
            connection.execute(
                "INSERT OR REPLACE INTO paper_schema(key, value) VALUES('funding_column_semantics', 'charged_only')"
            )
            lifecycle_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(paper_lifecycle_orders)").fetchall()
            }
            if "account_applied" not in lifecycle_columns:
                connection.execute("ALTER TABLE paper_lifecycle_orders ADD COLUMN account_applied INTEGER NOT NULL DEFAULT 0")
            if "account_version" not in lifecycle_columns:
                connection.execute("ALTER TABLE paper_lifecycle_orders ADD COLUMN account_version INTEGER NOT NULL DEFAULT 0")
            added_lifecycle_account_id = "account_id" not in lifecycle_columns
            if added_lifecycle_account_id:
                connection.execute("ALTER TABLE paper_lifecycle_orders ADD COLUMN account_id TEXT NOT NULL DEFAULT 'default'")
                legacy_rows = connection.execute(
                    "SELECT order_id, account_id, payload_json FROM paper_lifecycle_orders"
                ).fetchall()
                for legacy_row in legacy_rows:
                    try:
                        raw_payload = json.loads(legacy_row["payload_json"])
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise ValueError("paper_legacy_payload_invalid") from exc
                    if not isinstance(raw_payload, dict):
                        raise ValueError("paper_legacy_payload_invalid")
                    payload = dict(raw_payload)
                    row_account_id = str(legacy_row["account_id"] or "default").strip()
                    payload_account_id = str(payload.get("account_id") or row_account_id).strip()
                    if row_account_id != "default" or payload_account_id != row_account_id:
                        raise ValueError("paper_legacy_schema_account_conflict")
                    payload["account_id"] = row_account_id
                    validate_paper_lifecycle_order(payload)
                    connection.execute(
                        "UPDATE paper_lifecycle_orders SET payload_json = ? WHERE order_id = ?",
                        (self._json(payload), str(legacy_row["order_id"])),
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_paper_lifecycle_account ON paper_lifecycle_orders(account_id, created_at DESC)"
            )
            duplicate_risk_request = connection.execute(
                """
                SELECT risk_request_id
                FROM paper_lifecycle_orders
                WHERE risk_request_id IS NOT NULL AND risk_request_id <> ''
                GROUP BY risk_request_id
                HAVING COUNT(*) > 1
                LIMIT 1
                """
            ).fetchone()
            if duplicate_risk_request:
                raise ValueError("paper_risk_request_history_conflict")
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_lifecycle_risk_request_unique
                ON paper_lifecycle_orders(risk_request_id)
                WHERE risk_request_id IS NOT NULL AND risk_request_id <> ''
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO paper_schema(key, value) VALUES('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )
            connection.commit()

    @staticmethod
    def _json(payload: Any) -> str:
        try:
            return json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            )
        except ValueError as exc:
            if "Out of range float" in str(exc):
                raise ValueError("paper_non_finite_payload") from exc
            raise

    @classmethod
    def _stable_id(cls, prefix: str, payload: dict[str, Any]) -> str:
        digest = hashlib.sha256(cls._json(payload).encode("utf-8")).hexdigest()[:24]
        return f"{prefix}-{digest}"

    @classmethod
    def _order_identity(cls, payload: dict[str, Any]) -> str:
        return cls._json({field: payload.get(field) for field in cls.IMMUTABLE_ORDER_FIELDS})

    @staticmethod
    def _normalized_transitions(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for transition in list(payload.get("transitions") or []):
            if not isinstance(transition, dict):
                raise ValueError("paper_transition_invalid")
            if isinstance(transition.get("time"), bool):
                raise ValueError("paper_transition_invalid")
            try:
                occurred_at = int(transition.get("time") or 0)
            except (TypeError, ValueError, OverflowError):
                raise ValueError("paper_transition_invalid") from None
            rows.append({
                "state": str(transition.get("state") or "UNKNOWN").upper(),
                "time": occurred_at,
                "reason": str(transition.get("reason") or ""),
            })
        return rows

    @classmethod
    def _execution_report(cls, payload: dict[str, Any]) -> dict[str, Any]:
        report = payload.get("execution_report")
        return dict(report) if isinstance(report, dict) else {}

    @staticmethod
    def _filled_quantity(report: dict[str, Any]) -> float:
        if isinstance(report.get("filled_qty"), bool):
            raise ValueError("paper_fill_invalid")
        try:
            quantity = float(report.get("filled_qty") or 0.0)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("paper_fill_invalid") from None
        if not math.isfinite(quantity) or quantity < 0:
            raise ValueError("paper_fill_invalid")
        return quantity

    @classmethod
    def _validate_transition_contract(cls, payload: dict[str, Any], transitions: list[dict[str, Any]]) -> None:
        state = str(payload.get("state") or "UNKNOWN").upper()
        if transitions and transitions[-1]["state"] != state:
            raise ValueError("paper_transition_state_mismatch")
        previous_time = 0
        for transition in transitions:
            if transition["time"] < previous_time:
                raise ValueError("paper_transition_time_regression")
            previous_time = transition["time"]

    @classmethod
    def _validate_lifecycle_update(
        cls,
        existing: dict[str, Any],
        incoming: dict[str, Any],
        *,
        account_applied: bool,
        stored_transitions: list[dict[str, Any]],
        stored_fill: dict[str, Any] | None,
    ) -> None:
        if cls._order_identity(existing) != cls._order_identity(incoming):
            raise ValueError("paper_lifecycle_identity_conflict")

        existing_transitions = cls._normalized_transitions(existing)
        incoming_transitions = cls._normalized_transitions(incoming)
        cls._validate_transition_contract(existing, existing_transitions)
        cls._validate_transition_contract(incoming, incoming_transitions)
        if existing_transitions != stored_transitions:
            raise ValueError("paper_transition_storage_conflict")
        if incoming_transitions[:len(existing_transitions)] != existing_transitions:
            raise ValueError("paper_transition_history_rewrite")

        existing_report = cls._execution_report(existing)
        incoming_report = cls._execution_report(incoming)
        incoming_filled = cls._filled_quantity(incoming_report)
        if stored_fill is not None:
            if cls._json(incoming_report) != cls._json(stored_fill):
                raise ValueError("paper_fill_immutable_conflict")
            if cls._json(existing_report) != cls._json(stored_fill):
                raise ValueError("paper_fill_storage_conflict")
        elif cls._filled_quantity(existing_report) > 0:
            raise ValueError("paper_fill_storage_conflict")
        elif account_applied and incoming_filled > 0:
            raise ValueError("paper_fill_after_settlement")

        existing_state = str(existing.get("state") or "UNKNOWN").upper()
        incoming_state = str(incoming.get("state") or "UNKNOWN").upper()
        if existing_state in cls.TERMINAL_STATES:
            if incoming_state != existing_state:
                raise ValueError("paper_lifecycle_terminal_rewrite")
            if incoming_transitions != existing_transitions:
                raise ValueError("paper_transition_after_terminal")
            if cls._json(incoming_report) != cls._json(existing_report):
                raise ValueError("paper_execution_report_immutable_conflict")

    def load_account(self) -> dict[str, Any]:
        if self.read_only and not self.db_path.is_file():
            return {}
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT state_json FROM paper_account_state WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
        return json.loads(row["state_json"]) if row else {}

    def migrate_legacy(self, payload: dict[str, Any]) -> bool:
        self._require_writable()
        if not payload or self.load_account():
            return False
        self.save_account(payload, reason="legacy_json_migration")
        if self.audit_writer:
            self.audit_writer({"type": "paper_ledger_migrated", "source": "legacy_json", "account_id": self.account_id})
        return True

    def save_account(
        self,
        payload: dict[str, Any],
        reason: str = "state_update",
        *,
        expected_version: int | None = None,
        applied_lifecycle_ids: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        self._require_writable()
        state = dict(payload or {})
        raw_applied_ids = applied_lifecycle_ids if applied_lifecycle_ids is not None else []
        if not isinstance(raw_applied_ids, (list, tuple)):
            raise ValueError("paper_applied_lifecycle_ids_invalid")
        settlement_ids = [str(item or "").strip() for item in raw_applied_ids]
        if any(not item for item in settlement_ids) or len(set(settlement_ids)) != len(settlement_ids):
            raise ValueError("paper_applied_lifecycle_ids_invalid")
        for field in ("cash", "short_margin", "realized_pnl", "position_qty", "entry_price", "leverage"):
            if isinstance(state.get(field), bool):
                raise ValueError(f"paper_boolean_numeric_field:{field}")
        for point in list(state.get("equity_curve") or []):
            if not isinstance(point, dict):
                continue
            if isinstance(point.get("time"), bool) or isinstance(point.get("equity"), bool):
                raise ValueError("paper_boolean_numeric_field:equity_curve")
        timestamp = self.now_ms()
        state_json = self._json(state)
        symbol = str(state.get("symbol") or "UNKNOWN").upper()
        quantity = float(state.get("position_qty") or 0.0)
        entry_price = float(state.get("entry_price") or 0.0)
        side = "LONG" if quantity > 0 else "SHORT" if quantity < 0 else "FLAT"
        equity_curve = list(state.get("equity_curve") or [])
        latest_equity = float((equity_curve[-1] or {}).get("equity") or state.get("cash") or 0.0) if equity_curve else float(state.get("cash") or 0.0)

        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT version FROM paper_account_state WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            current_version = int(row["version"] if row else 0)
            if expected_version is not None and current_version != int(expected_version):
                connection.rollback()
                raise RuntimeError("paper_account_version_conflict")
            state_orders_by_id = {
                str(item.get("order_id") or ""): item
                for item in list(state.get("orders") or [])
                if isinstance(item, dict) and str(item.get("order_id") or "")
            }
            for lifecycle_order_id in settlement_ids:
                account_order = state_orders_by_id.get(lifecycle_order_id)
                if not isinstance(account_order, dict):
                    connection.rollback()
                    raise ValueError("paper_settlement_account_order_missing")
                lifecycle_row = connection.execute(
                    """
                    SELECT account_id, account_applied, payload_json
                    FROM paper_lifecycle_orders
                    WHERE order_id = ?
                    """,
                    (lifecycle_order_id,),
                ).fetchone()
                fill_row = connection.execute(
                    "SELECT payload_json FROM paper_fills WHERE order_id = ? ORDER BY fill_id ASC LIMIT 1",
                    (lifecycle_order_id,),
                ).fetchone()
                if not lifecycle_row or not fill_row:
                    connection.rollback()
                    raise ValueError("paper_settlement_lifecycle_missing")
                if str(lifecycle_row["account_id"] or "") != self.account_id:
                    connection.rollback()
                    raise ValueError("paper_settlement_account_conflict")
                if int(lifecycle_row["account_applied"] or 0) != 0:
                    connection.rollback()
                    raise ValueError("paper_settlement_already_applied")
                lifecycle_payload = json.loads(lifecycle_row["payload_json"])
                fill_payload = json.loads(fill_row["payload_json"])
                validate_paper_lifecycle_order(lifecycle_payload)
                expected_symbol = str(lifecycle_payload.get("symbol") or "").upper()
                if str(account_order.get("symbol") or "").upper() != expected_symbol:
                    connection.rollback()
                    raise ValueError("paper_settlement_symbol_mismatch")
                if str(account_order.get("risk_request_id") or "") != str(lifecycle_payload.get("risk_request_id") or ""):
                    connection.rollback()
                    raise ValueError("paper_settlement_risk_request_mismatch")
                for account_field, fill_field, tolerance in (
                    ("quantity", "filled_qty", 1e-8),
                    ("price", "avg_price", 1e-8),
                    ("notional", "filled_notional", 0.01),
                ):
                    account_value = float(account_order.get(account_field) or 0.0)
                    fill_value = float(fill_payload.get(fill_field) or 0.0)
                    if not math.isfinite(account_value) or abs(account_value - fill_value) > tolerance:
                        connection.rollback()
                        raise ValueError(f"paper_settlement_{account_field}_mismatch")
            version = current_version + 1
            connection.execute(
                """
                INSERT INTO paper_account_state(account_id, version, updated_at, state_json)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    version = excluded.version,
                    updated_at = excluded.updated_at,
                    state_json = excluded.state_json
                """,
                (self.account_id, version, timestamp, state_json),
            )
            connection.execute(
                "INSERT INTO paper_account_snapshots(account_id, version, reason, created_at, state_json) VALUES(?, ?, ?, ?, ?)",
                (self.account_id, version, str(reason or "state_update"), timestamp, state_json),
            )
            connection.execute(
                """
                INSERT INTO paper_balances(account_id, currency, cash, short_margin, realized_pnl, equity, updated_at)
                VALUES(?, 'USDT', ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, currency) DO UPDATE SET
                    cash = excluded.cash,
                    short_margin = excluded.short_margin,
                    realized_pnl = excluded.realized_pnl,
                    equity = excluded.equity,
                    updated_at = excluded.updated_at
                """,
                (
                    self.account_id,
                    float(state.get("cash") or 0.0),
                    float(state.get("short_margin") or 0.0),
                    float(state.get("realized_pnl") or 0.0),
                    latest_equity,
                    timestamp,
                ),
            )
            connection.execute("DELETE FROM paper_positions WHERE account_id = ?", (self.account_id,))
            connection.execute(
                "INSERT INTO paper_positions(account_id, symbol, quantity, entry_price, side, updated_at) VALUES(?, ?, ?, ?, ?, ?)",
                (self.account_id, symbol, quantity, entry_price, side, timestamp),
            )
            for order in list(state.get("orders") or []):
                if not isinstance(order, dict):
                    continue
                account_order_id = str(order.get("account_order_id") or order.get("order_id") or self._stable_id("account-order", order))
                lifecycle_order_id = str(order.get("order_id") or "")
                connection.execute(
                    """
                    INSERT OR REPLACE INTO paper_account_orders(
                        account_order_id, account_id, lifecycle_order_id, symbol, side, status, created_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_order_id,
                        self.account_id,
                        lifecycle_order_id,
                        str(order.get("symbol") or symbol).upper(),
                        str(order.get("side") or "").upper(),
                        str(order.get("match_status") or order.get("status") or "UNKNOWN").upper(),
                        int(order.get("time") or timestamp),
                        self._json(order),
                    ),
                )
            for lifecycle_order_id in settlement_ids:
                updated = connection.execute(
                    """
                    UPDATE paper_lifecycle_orders
                    SET account_applied = 1, account_version = ?
                    WHERE order_id = ? AND account_id = ? AND account_applied = 0
                    """,
                    (version, lifecycle_order_id, self.account_id),
                )
                if updated.rowcount != 1:
                    connection.rollback()
                    raise RuntimeError("paper_settlement_claim_conflict")
            connection.execute("DELETE FROM paper_conditions WHERE account_id = ?", (self.account_id,))
            for condition in list(state.get("conditional_orders") or []):
                if not isinstance(condition, dict):
                    continue
                condition_id = str(condition.get("id") or self._stable_id("condition", condition))
                connection.execute(
                    "INSERT INTO paper_conditions(condition_id, account_id, symbol, side, status, updated_at, payload_json) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (
                        condition_id,
                        self.account_id,
                        str(condition.get("symbol") or symbol).upper(),
                        str(condition.get("side") or "").upper(),
                        str(condition.get("status") or "UNKNOWN").upper(),
                        int(condition.get("updated_at") or condition.get("created_at") or timestamp),
                        self._json(condition),
                    ),
                )
            for point in equity_curve[-5000:]:
                if not isinstance(point, dict):
                    continue
                connection.execute(
                    "INSERT OR REPLACE INTO paper_equity(account_id, observed_at, equity) VALUES(?, ?, ?)",
                    (self.account_id, int(point.get("time") or timestamp), float(point.get("equity") or 0.0)),
                )
            connection.execute(
                """
                DELETE FROM paper_account_snapshots
                WHERE account_id = ? AND id NOT IN (
                    SELECT id FROM paper_account_snapshots WHERE account_id = ? ORDER BY id DESC LIMIT 5000
                )
                """,
                (self.account_id, self.account_id),
            )
            connection.commit()

        return {"ok": True, "account_id": self.account_id, "version": version, "updated_at": timestamp}

    def reconcile_account(self, _retry_count: int = 0) -> dict[str, Any]:
        self._require_writable()
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT lifecycle.payload_json AS order_json, fills.payload_json AS fill_json
                FROM paper_lifecycle_orders AS lifecycle
                JOIN paper_fills AS fills ON fills.order_id = lifecycle.order_id
                WHERE lifecycle.account_id = ? AND lifecycle.account_applied = 0
                ORDER BY lifecycle.created_at ASC, lifecycle.order_id ASC
                """,
                (self.account_id,),
            ).fetchall()
            account_row = connection.execute(
                "SELECT version, state_json FROM paper_account_state WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
        if not rows:
            return {"ok": True, "reconciled": 0, "pending": 0, "blockers": []}

        state = json.loads(account_row["state_json"]) if account_row else {}
        account_version = int(account_row["version"] if account_row else 0)
        if not state:
            return {
                "ok": False,
                "reconciled": 0,
                "pending": len(rows),
                "blockers": ["存在未结算成交，但账户基线不存在"],
            }
        boolean_state_fields = [
            field
            for field in ("cash", "short_margin", "realized_pnl", "position_qty", "entry_price", "leverage")
            if isinstance(state.get(field), bool)
        ]
        if boolean_state_fields:
            return {
                "ok": False,
                "reconciled": 0,
                "pending": len(rows),
                "blockers": [f"账户基线包含布尔数值字段：{','.join(boolean_state_fields)}"],
            }

        orders = [dict(item) for item in state.get("orders", []) if isinstance(item, dict)]
        applied_ids = {str(item.get("order_id") or "") for item in orders}
        blockers: list[str] = []
        reconciled = 0
        reconciled_order_ids: list[str] = []
        for row in rows:
            try:
                order = json.loads(row["order_json"])
                report = json.loads(row["fill_json"])
                validate_paper_lifecycle_order(order)
                if not isinstance(report, dict):
                    raise ValueError("paper_fill_payload_invalid")
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                blockers.append(f"paper_lifecycle_settlement_contract_invalid:{type(exc).__name__}:{exc}")
                break
            order_id = str(order.get("order_id") or "")
            if not order_id or order_id in applied_ids:
                continue
            symbol = str(order.get("symbol") or "").upper()
            current_symbol = str(state.get("symbol") or symbol).upper()
            position_qty = float(state.get("position_qty") or 0.0)
            current_position_side = "LONG" if position_qty > 1e-9 else "SHORT" if position_qty < -1e-9 else "FLAT"
            position_side_before = str(order.get("position_side_before") or "").upper()
            if position_side_before != current_position_side:
                blockers.append(
                    f"{order_id}: 审批持仓方向 {position_side_before or '--'} 与结算时方向 {current_position_side} 不一致"
                )
                break
            if current_symbol != symbol and abs(position_qty) > 1e-9:
                blockers.append(f"{order_id}: 当前账户持有 {current_symbol}，无法自动结算 {symbol}")
                break

            side = str(order.get("side") or "").upper()
            boolean_report_fields = [
                field
                for field in (
                    "filled_qty",
                    "avg_price",
                    "filled_notional",
                    "fee",
                    "funding_estimate",
                    "funding_charged",
                    "slippage_pct",
                )
                if isinstance(report.get(field), bool)
            ]
            if boolean_report_fields:
                blockers.append(f"{order_id}: 成交字段包含布尔数值，无法自动结算")
                break
            try:
                fill_qty = float(report.get("filled_qty") or 0.0)
                fill_price = float(report.get("avg_price") or 0.0)
                notional = float(report.get("filled_notional") or fill_qty * fill_price)
                fee = float(report.get("fee") or 0.0)
                funding_estimate = float(report.get("funding_estimate") or 0.0)
                funding = float(report.get("funding_charged") or 0.0)
            except (TypeError, ValueError, OverflowError):
                blockers.append(f"{order_id}: 成交字段不完整，无法自动结算")
                break
            settlement_values = (position_qty, fill_qty, fill_price, notional, fee, funding_estimate, funding)
            if (
                side not in {"BUY", "SELL"}
                or not all(math.isfinite(value) for value in settlement_values)
                or fill_qty <= 0
                or fill_price <= 0
                or notional <= 0
                or fee < 0
            ):
                blockers.append(f"{order_id}: 成交字段不完整，无法自动结算")
                break

            reduces_position = (
                (side == "BUY" and position_qty < 0)
                or (side == "SELL" and position_qty > 0)
            )
            if order.get("reduce_only") is True and not reduces_position:
                blockers.append(f"{order_id}: 只减仓成交不能增加或反向建立仓位")
                break

            cash = float(state.get("cash") or 0.0)
            entry_price = float(state.get("entry_price") or 0.0)
            realized_pnl = float(state.get("realized_pnl") or 0.0)
            short_margin = float(state.get("short_margin") or 0.0)
            leverage = max(float(state.get("leverage") or 1.0), 1.0)
            account_values = (cash, entry_price, realized_pnl, short_margin, leverage)
            if not all(math.isfinite(value) for value in account_values):
                blockers.append(f"{order_id}: 账户基线包含非有限数值，拒绝自动结算")
                break
            pnl = 0.0

            if side == "BUY" and position_qty < 0:
                if fill_qty > abs(position_qty) + 1e-8:
                    blockers.append(f"{order_id}: 平空成交量超过现有空仓，拒绝自动跨向结算")
                    break
                release_ratio = fill_qty / max(abs(position_qty), 1e-9)
                released_margin = short_margin * release_ratio
                pnl = (entry_price - fill_price) * fill_qty - fee - funding
                cash += released_margin + pnl
                short_margin = max(short_margin - released_margin, 0.0)
                position_qty += fill_qty
            elif side == "BUY":
                old_cost = entry_price * max(position_qty, 0.0)
                cash -= notional + fee
                position_qty += fill_qty
                entry_price = (old_cost + notional + fee) / max(position_qty, 1e-9)
            elif side == "SELL" and position_qty > 0:
                if fill_qty > position_qty + 1e-8:
                    blockers.append(f"{order_id}: 平多成交量超过现有多仓，拒绝自动跨向结算")
                    break
                pnl = (fill_price - entry_price) * fill_qty - fee - funding
                cash += notional - fee - funding
                position_qty -= fill_qty
            else:
                old_abs_qty = abs(min(position_qty, 0.0))
                old_cost = entry_price * old_abs_qty
                margin_required = notional / leverage
                cash -= margin_required + fee
                short_margin += margin_required
                position_qty -= fill_qty
                entry_price = (old_cost + notional) / max(abs(position_qty), 1e-9)

            realized_pnl += pnl
            if abs(position_qty) <= 1e-9:
                position_qty = 0.0
                entry_price = 0.0
                short_margin = 0.0
            state.update({
                "symbol": symbol,
                "cash": cash,
                "position_qty": position_qty,
                "entry_price": entry_price,
                "realized_pnl": realized_pnl,
                "short_margin": short_margin,
            })
            account_order = {
                "order_id": order_id,
                "risk_request_id": str(order.get("risk_request_id") or ""),
                "market_snapshot_id": str(order.get("market_snapshot_id") or ""),
                "idempotency_key": str(order.get("idempotency_key") or ""),
                "time": int(order.get("updated_at") or self.now_ms()),
                "symbol": symbol,
                "side": "COVER" if side == "BUY" and position_qty <= 0 else side,
                "order_type": str(order.get("order_type") or "MARKET"),
                "price": fill_price,
                "quantity": fill_qty,
                "notional": notional,
                "pnl": round(pnl, 8),
                "fee": fee,
                "funding_estimate": funding_estimate,
                "funding_charged": funding,
                "slippage_pct": float(report.get("slippage_pct") or 0.0),
                "match_status": str(report.get("status") or "FILLED"),
                "reason": "进程重启后按持久化成交自动对账",
                "reconciled": True,
            }
            orders.append(account_order)
            applied_ids.add(order_id)
            reconciled_order_ids.append(order_id)
            equity = cash + short_margin + (entry_price - fill_price) * abs(position_qty) if position_qty < 0 else cash + position_qty * fill_price
            state.setdefault("equity_curve", []).append({"time": self.now_ms(), "equity": round(equity, 2)})
            reconciled += 1

        if reconciled:
            state["orders"] = orders
            try:
                self.save_account(
                    state,
                    reason="restart_reconciliation",
                    expected_version=account_version,
                    applied_lifecycle_ids=reconciled_order_ids,
                )
            except RuntimeError as exc:
                if str(exc) != "paper_account_version_conflict":
                    raise
                if _retry_count < self.MAX_RECONCILIATION_RETRIES:
                    return self.reconcile_account(_retry_count + 1)
                pending = self.summary()["pending_settlement_count"]
                return {
                    "ok": False,
                    "reconciled": 0,
                    "pending": pending,
                    "blockers": ["账户版本在恢复结算期间持续变化，拒绝写入陈旧快照"],
                }
            if self.audit_writer:
                self.audit_writer({
                    "type": "paper_ledger_reconciled",
                    "account_id": self.account_id,
                    "reconciled": reconciled,
                    "blockers": blockers,
                })
        pending = self.summary()["pending_settlement_count"]
        if not blockers and pending and _retry_count < self.MAX_RECONCILIATION_RETRIES:
            follow_up = self.reconcile_account(_retry_count + 1)
            return {
                **follow_up,
                "reconciled": reconciled + int(follow_up.get("reconciled") or 0),
            }
        if pending and not blockers:
            blockers.append("paper_ledger_reconciliation_exhausted_with_pending_settlements")
        return {
            "ok": not blockers,
            "reconciled": reconciled,
            "pending": pending,
            "blockers": blockers,
        }

    def record_lifecycle_order(self, order: dict[str, Any]) -> dict[str, Any]:
        self._require_writable()
        payload = dict(order or {})
        incoming_account_id = str(payload.get("account_id") or self.account_id).strip()
        if incoming_account_id != self.account_id:
            raise ValueError("paper_lifecycle_account_conflict")
        payload["account_id"] = self.account_id
        validate_paper_lifecycle_order(payload)
        order_id = str(payload.get("order_id") or "")
        idempotency_key = str(payload.get("idempotency_key") or "") or None
        risk_request_id = str(payload.get("risk_request_id") or "") or None
        report = dict(payload["execution_report"])
        transitions = self._normalized_transitions(payload)
        self._validate_transition_contract(payload, transitions)
        timestamp = int(payload.get("updated_at") or self.now_ms())
        filled_qty = self._filled_quantity(report)

        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                "SELECT account_id, state, account_applied, updated_at, payload_json FROM paper_lifecycle_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            transition_rows = connection.execute(
                "SELECT state, occurred_at, reason FROM paper_order_transitions WHERE order_id = ? ORDER BY sequence ASC",
                (order_id,),
            ).fetchall()
            stored_transitions = [
                {
                    "state": str(row["state"] or "UNKNOWN").upper(),
                    "time": int(row["occurred_at"] or 0),
                    "reason": str(row["reason"] or ""),
                }
                for row in transition_rows
            ]
            fill_row = connection.execute(
                "SELECT payload_json FROM paper_fills WHERE order_id = ? ORDER BY fill_id ASC LIMIT 1",
                (order_id,),
            ).fetchone()
            stored_fill = json.loads(fill_row["payload_json"]) if fill_row else None

            if existing_row:
                if str(existing_row["account_id"] or "") != self.account_id:
                    raise ValueError("paper_lifecycle_account_conflict")
                existing_payload = json.loads(existing_row["payload_json"])
                self._validate_lifecycle_update(
                    existing_payload,
                    payload,
                    account_applied=bool(existing_row["account_applied"]),
                    stored_transitions=stored_transitions,
                    stored_fill=stored_fill,
                )
                if timestamp < int(existing_row["updated_at"] or 0):
                    raise ValueError("paper_lifecycle_time_regression")
                connection.execute(
                    """
                    UPDATE paper_lifecycle_orders
                    SET state = ?, updated_at = ?, payload_json = ?
                    WHERE order_id = ?
                    """,
                    (
                        str(payload.get("state") or "UNKNOWN").upper(),
                        timestamp,
                        self._json(payload),
                        order_id,
                    ),
                )
            else:
                if idempotency_key:
                    conflict = connection.execute(
                        "SELECT order_id FROM paper_lifecycle_orders WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if conflict:
                        raise ValueError("paper_idempotency_key_conflict")
                if risk_request_id:
                    conflict = connection.execute(
                        "SELECT order_id FROM paper_lifecycle_orders WHERE risk_request_id = ?",
                        (risk_request_id,),
                    ).fetchone()
                    if conflict:
                        raise ValueError("paper_risk_request_id_conflict")
                connection.execute(
                    """
                    INSERT INTO paper_lifecycle_orders(
                        order_id, account_id, idempotency_key, symbol, side, state, risk_request_id,
                        market_snapshot_id, strategy_id, run_id, created_at, updated_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        self.account_id,
                        idempotency_key,
                        str(payload.get("symbol") or "").upper(),
                        str(payload.get("side") or "").upper(),
                        str(payload.get("state") or "UNKNOWN").upper(),
                        risk_request_id,
                        str(payload.get("market_snapshot_id") or ""),
                        str(payload.get("strategy_id") or ""),
                        str(payload.get("run_id") or ""),
                        int(payload.get("created_at") or timestamp),
                        timestamp,
                        self._json(payload),
                    ),
                )

            for sequence, transition in enumerate(transitions[len(stored_transitions):], start=len(stored_transitions) + 1):
                connection.execute(
                    "INSERT INTO paper_order_transitions(order_id, sequence, state, occurred_at, reason) VALUES(?, ?, ?, ?, ?)",
                    (
                        order_id,
                        sequence,
                        transition["state"],
                        int(transition["time"] or timestamp),
                        transition["reason"],
                    ),
                )
            if filled_qty > 0 and stored_fill is None:
                fill_id = f"{order_id}:fill:1"
                connection.execute(
                    """
                    INSERT INTO paper_fills(
                        fill_id, order_id, quantity, price, notional, fee, funding, created_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fill_id,
                        order_id,
                        filled_qty,
                        float(report.get("avg_price") or 0.0),
                        float(report.get("filled_notional") or 0.0),
                        float(report.get("fee") or 0.0),
                        float(report.get("funding_charged") or 0.0),
                        timestamp,
                        self._json(report),
                    ),
                )
            connection.commit()
        return payload

    def load_lifecycle_orders(self, limit: int = 2000) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 2000), 10_000))
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            where_clause = f"WHERE {account_clause}" if account_clause else ""
            rows = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders {where_clause} ORDER BY created_at DESC LIMIT ?",
                (*account_params, safe_limit),
            ).fetchall()
        return [
            self._decode_lifecycle_payload(
                row["payload_json"],
                legacy_schema=not profile["has_account_id"],
            )
            for row in reversed(rows)
        ]

    def get_lifecycle_order(self, order_id: str) -> dict[str, Any] | None:
        clean_order_id = str(order_id or "").strip()
        if not clean_order_id:
            return None
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            row = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders WHERE order_id = ?{account_suffix}",
                (clean_order_id, *account_params),
            ).fetchone()
        if not row:
            return None
        return self._decode_lifecycle_payload(
            row["payload_json"],
            legacy_schema=not profile["has_account_id"],
        )

    def is_order_applied(self, order_id: str) -> bool:
        clean_order_id = str(order_id or "").strip()
        if not clean_order_id:
            return False
        with self._lock, closing(self._connect()) as connection:
            _, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            row = connection.execute(
                f"""
                SELECT account_applied
                FROM paper_lifecycle_orders
                WHERE order_id = ?{account_suffix}
                """,
                (clean_order_id, *account_params),
            ).fetchone()
        return bool(row and int(row["account_applied"] or 0) == 1)

    def load_run_orders(self, run_id: str, limit: int = 2000) -> list[dict[str, Any]]:
        clean_run_id = str(run_id or "").strip()
        if not clean_run_id:
            return []
        safe_limit = max(1, min(int(limit or 2000), 10_000))
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            rows = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders WHERE run_id = ?{account_suffix} ORDER BY created_at ASC LIMIT ?",
                (clean_run_id, *account_params, safe_limit),
            ).fetchall()
        return [
            self._decode_lifecycle_payload(
                row["payload_json"],
                legacy_schema=not profile["has_account_id"],
            )
            for row in rows
        ]

    def find_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        clean_key = str(idempotency_key or "").strip()
        if not clean_key:
            return None
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            row = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders WHERE idempotency_key = ?{account_suffix}",
                (clean_key, *account_params),
            ).fetchone()
        if not row:
            return None
        return self._decode_lifecycle_payload(
            row["payload_json"],
            legacy_schema=not profile["has_account_id"],
        )

    def find_by_risk_request_id(self, risk_request_id: str) -> dict[str, Any] | None:
        clean_request_id = str(risk_request_id or "").strip()
        if not clean_request_id:
            return None
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            rows = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders WHERE risk_request_id = ?{account_suffix} LIMIT 2",
                (clean_request_id, *account_params),
            ).fetchall()
        if len(rows) > 1:
            raise ValueError("paper_risk_request_history_conflict")
        if not rows:
            return None
        return self._decode_lifecycle_payload(
            rows[0]["payload_json"],
            legacy_schema=not profile["has_account_id"],
        )

    def run_metrics(self, run_id: str) -> dict[str, Any]:
        clean_run_id = str(run_id or "").strip()
        if not clean_run_id:
            return {
                "run_id": "",
                "order_count": 0,
                "filled_order_count": 0,
                "closed_trade_count": 0,
                "first_order_at": 0,
                "last_order_at": 0,
            }
        with self._lock, closing(self._connect()) as connection:
            profile, account_clause, account_params = self._lifecycle_account_scope(connection)
            account_suffix = f" AND {account_clause}" if account_clause else ""
            rows = connection.execute(
                f"SELECT payload_json FROM paper_lifecycle_orders WHERE run_id = ?{account_suffix} ORDER BY created_at ASC",
                (clean_run_id, *account_params),
            ).fetchall()
        orders = [
            self._decode_lifecycle_payload(
                row["payload_json"],
                legacy_schema=not profile["has_account_id"],
            )
            for row in rows
        ]
        filled = [order for order in orders if float((order.get("execution_report") or {}).get("filled_qty") or 0.0) > 0]
        closed = [order for order in filled if order.get("reduce_only") is True]
        return {
            "run_id": clean_run_id,
            "order_count": len(orders),
            "filled_order_count": len(filled),
            "closed_trade_count": len(closed),
            "first_order_at": int(orders[0].get("created_at") or 0) if orders else 0,
            "last_order_at": int(orders[-1].get("updated_at") or orders[-1].get("created_at") or 0) if orders else 0,
        }

    def summary(self) -> dict[str, Any]:
        if self.read_only and not self.db_path.is_file():
            return {
                "ok": False,
                "status": "DATABASE_MISSING",
                "backend": "sqlite",
                "db_path": str(self.db_path),
                "schema_version": 0,
                "supported_schema_version": self.SCHEMA_VERSION,
                "schema_compatibility": "BLOCK",
                "missing_tables": [
                    "paper_account_state",
                    "paper_account_snapshots",
                    "paper_fills",
                    "paper_lifecycle_orders",
                ],
                "account_id": self.account_id,
                "restart_ready": False,
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        with self._lock, closing(self._connect()) as connection:
            profile = self._lifecycle_schema_profile(connection)
            required_tables = {
                "paper_account_state",
                "paper_account_snapshots",
                "paper_fills",
            }
            missing_tables = sorted(
                table for table in required_tables
                if not self._table_exists(connection, table)
            )
            if not profile["has_lifecycle_table"]:
                missing_tables.append("paper_lifecycle_orders")
            if missing_tables:
                return {
                    "ok": False,
                    "status": "SCHEMA_MISSING",
                    "backend": "sqlite",
                    "db_path": str(self.db_path),
                    "schema_version": profile["schema_version"],
                    "supported_schema_version": self.SCHEMA_VERSION,
                    "schema_compatibility": "BLOCK",
                    "missing_tables": missing_tables,
                    "account_id": self.account_id,
                    "restart_ready": False,
                    "live_order_allowed": False,
                }
            if not profile["has_account_id"] and self.account_id != "default":
                return {
                    "ok": False,
                    "status": "ACCOUNT_ISOLATION_BLOCKED",
                    "backend": "sqlite",
                    "db_path": str(self.db_path),
                    "schema_version": profile["schema_version"],
                    "supported_schema_version": self.SCHEMA_VERSION,
                    "schema_compatibility": "BLOCK",
                    "account_id": self.account_id,
                    "restart_ready": False,
                    "live_order_allowed": False,
                }
            account_clause = "account_id = ?" if profile["has_account_id"] else ""
            account_params: tuple[Any, ...] = (self.account_id,) if account_clause else ()
            where_clause = f"WHERE {account_clause}" if account_clause else ""
            state = connection.execute(
                "SELECT version, updated_at FROM paper_account_state WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            order_count = int(connection.execute(
                f"SELECT COUNT(*) FROM paper_lifecycle_orders {where_clause}",
                account_params,
            ).fetchone()[0])
            fill_account_filter = "WHERE lifecycle.account_id = ?" if account_clause else ""
            fill_count = int(connection.execute(
                f"""
                SELECT COUNT(*) FROM paper_fills AS fills
                JOIN paper_lifecycle_orders AS lifecycle ON lifecycle.order_id = fills.order_id
                {fill_account_filter}
                """,
                account_params,
            ).fetchone()[0])
            snapshot_count = int(connection.execute(
                "SELECT COUNT(*) FROM paper_account_snapshots WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()[0])
            pending_account_filter = "lifecycle.account_id = ? AND " if account_clause else ""
            pending_settlement_count = int(connection.execute(
                f"""
                SELECT COUNT(*) FROM paper_lifecycle_orders AS lifecycle
                JOIN paper_fills AS fills ON fills.order_id = lifecycle.order_id
                WHERE {pending_account_filter}lifecycle.account_applied = 0
                """,
                account_params,
            ).fetchone()[0])
        return {
            "ok": True,
            "status": "READY",
            "backend": "sqlite",
            "db_path": str(self.db_path),
            "schema_version": profile["schema_version"],
            "supported_schema_version": self.SCHEMA_VERSION,
            "schema_compatibility": (
                "CURRENT"
                if (
                    profile["has_account_id"]
                    and profile["schema_version"] == self.SCHEMA_VERSION
                    and profile["has_unique_risk_request"]
                )
                else "PARTIAL_READ_ONLY_COMPAT"
                if profile["has_account_id"]
                else "LEGACY_READ_ONLY_COMPAT"
            ),
            "risk_request_unique": bool(profile["has_unique_risk_request"]),
            "account_id": self.account_id,
            "account_version": int(state["version"] if state else 0),
            "updated_at": int(state["updated_at"] if state else 0),
            "order_count": order_count,
            "fill_count": fill_count,
            "snapshot_count": snapshot_count,
            "pending_settlement_count": pending_settlement_count,
            "restart_ready": pending_settlement_count == 0 and bool(state),
            "live_order_allowed": False,
        }
