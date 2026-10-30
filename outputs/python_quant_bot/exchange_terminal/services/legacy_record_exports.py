"""Read retained account history without restoring the archived execution runtime."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .legacy_record_snapshot import read_legacy_record_snapshot


_EXECUTION_AUTHORITY_FIELDS = frozenset({
    "armed", "paper_armed", "paper_authorized", "binding_authorized",
    "paper_allowed", "live_allowed", "order_allowed", "live_order_allowed",
    "paper_order_allowed", "automated_paper_order_allowed", "execution_allowed",
    "execution_eligible", "execution_enabled", "simulation_enabled",
    "paper_enabled", "live_enabled", "trading_enabled", "can_trade",
    "can_execute", "can_submit", "paper_clock_supported", "restart_ready",
})


def _archived_account_projection(value: Any) -> Any:
    """Copy saved values while removing authority even inside nested receipts."""
    if isinstance(value, dict):
        return {
            key: False if key in _EXECUTION_AUTHORITY_FIELDS else
            True if key == "read_only" else _archived_account_projection(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_archived_account_projection(item) for item in value]
    return value


def load_legacy_account_snapshot(
    db_path: Path | str, *, account_id: str = "default"
) -> dict[str, Any]:
    """Project saved state and retained orders without loading an execution class.

    paper_account_state is the latest committed account. The versioned snapshot
    table is an audit trail, not a substitute for a missing current state. No
    price lookup, valuation, strategy evaluation or account initialization occurs.
    """
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("legacy_account_snapshot_account_id_required")
    path = Path(db_path).expanduser().resolve()
    envelope: dict[str, Any] = {
        "available": False, "state_available": False,
        "status": "ARCHIVED", "source": "archived_saved_account",
        "read_only": True, "research_only": True,
        "account_id": account_id, "account_version": None, "as_of": None,
        "valuation": "saved_state_no_revaluation",
        "orders_scope": "account_history", "orders": [], "saved_state_orders": [],
        **dict.fromkeys(_EXECUTION_AUTHORITY_FIELDS, False),
    }
    if not path.exists():
        return {**envelope, "history_status": "NO_SAVED_ACCOUNT"}
    records = read_legacy_record_snapshot(
        path,
        "SELECT 'state' AS record_kind, account_id, version AS record_version, "
        "updated_at AS recorded_at, state_json AS payload_json, NULL AS record_id "
        "FROM paper_account_state WHERE account_id = ? "
        "UNION ALL "
        "SELECT 'order', account_id, NULL, created_at, payload_json, account_order_id "
        "FROM paper_account_orders WHERE account_id = ? "
        "ORDER BY record_kind DESC, recorded_at ASC, record_id ASC",
        (account_id, account_id),
    )
    state: dict[str, Any] | None = None
    history_orders: list[dict[str, Any]] = []
    version = as_of = None
    for record in records:
        payload = json.loads(record["payload_json"])
        if not isinstance(payload, dict):
            raise ValueError(f"legacy_account_{record['record_kind']}_payload_invalid")
        if payload.get("account_id", account_id) != account_id:
            raise ValueError("legacy_account_payload_identity_conflict")
        if record["record_kind"] == "state":
            state = payload
            version, as_of = record["record_version"], record["recorded_at"]
        else:
            payload.setdefault("account_id", account_id)
            payload.setdefault("account_order_id", str(record["record_id"]))
            history_orders.append(payload)
    saved_orders = (state or {}).get("orders", [])
    if not isinstance(saved_orders, list) or any(not isinstance(order, dict) for order in saved_orders):
        raise ValueError("legacy_account_saved_orders_invalid")
    result = _archived_account_projection({
        **(state or {}), **envelope,
        "available": state is not None or bool(history_orders),
        "state_available": state is not None,
        "account_version": version, "as_of": as_of,
        "orders": history_orders or saved_orders, "saved_state_orders": saved_orders,
        "orders_scope": "account_history" if history_orders or not saved_orders else "saved_state_orders",
        "history_status": "SAVED_STATE" if state is not None else
                          "ORDERS_WITHOUT_STATE" if history_orders else "NO_SAVED_ACCOUNT",
    })
    return result


def load_legacy_order_export_rows(
    db_path: Path | str, *, account_id: str = "default"
) -> list[dict[str, Any]]:
    """Return one account's complete committed history, including before resets.

    A fresh installation need not have an archived paper database. An existing
    but unreadable/incompatible database must fail visibly, rather than appear
    to contain no orders. No schema initialization, migration or executor is used.
    """
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        return []
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("legacy_order_export_account_id_required")
    records = read_legacy_record_snapshot(
        path,
        "SELECT account_order_id, payload_json FROM paper_account_orders "
        "WHERE account_id = ? ORDER BY created_at ASC, account_order_id ASC",
        (account_id,),
    )
    rows: list[dict[str, Any]] = []
    for record in records:
        row = json.loads(record["payload_json"])
        if not isinstance(row, dict):
            raise ValueError("paper_account_order_payload_invalid")
        row.setdefault("account_id", account_id)
        row.setdefault("account_order_id", str(record["account_order_id"]))
        rows.append(row)
    return rows
