from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any, Callable

from .portfolio_paper_activation import (
    verify_current_paper_authorization,
    verify_paper_activation_receipt,
)
from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable


PORTFOLIO_PAPER_SCHEMA_VERSION = "portfolio-paper-ledger-v2"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def _strict_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _state_contract_blockers(state: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not isinstance(state.get("version"), int) or isinstance(state.get("version"), bool):
        blockers.append("portfolio_state_version_invalid")
    for field in ("cash", "realized_pnl", "fees_paid"):
        if _strict_number(state.get(field)) is None:
            blockers.append(f"portfolio_state_numeric_invalid:{field}")
    if state.get("paper_authorized") is not True:
        blockers.append("portfolio_state_paper_authorization_invalid")
    if state.get("live_order_allowed") is not False:
        blockers.append("portfolio_state_live_order_wall_invalid")
    raw_positions = state.get("positions")
    if not isinstance(raw_positions, dict):
        blockers.append("portfolio_state_positions_invalid")
    else:
        for symbol, item in raw_positions.items():
            if not isinstance(symbol, str) or not isinstance(item, dict):
                blockers.append("portfolio_state_position_invalid")
                break
            values = [_strict_number(item.get(field)) for field in ("quantity", "entry_price", "last_price")]
            if any(value is None or value < 0 for value in values):
                blockers.append(f"portfolio_state_position_numeric_invalid:{symbol}")
                break
    return blockers


def _decode_state(raw: Any) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("portfolio_paper_account_state_not_object")
    return payload


def _normalized_positions(raw_positions: Any) -> dict[str, dict[str, float]]:
    positions: dict[str, dict[str, float]] = {}
    source = raw_positions.values() if isinstance(raw_positions, dict) else raw_positions or []
    for raw in source:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol") or "").upper()
        quantity = max(_number(raw.get("quantity")), 0.0)
        entry_price = max(_number(raw.get("entry_price")), 0.0)
        last_price = max(_number(raw.get("last_price"), entry_price), 0.0)
        if symbol and quantity > 1e-12 and entry_price > 0:
            positions[symbol] = {
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "last_price": last_price or entry_price,
            }
    return positions


def build_target_order_preview(
    *,
    state: dict[str, Any],
    target_weights: dict[str, float],
    prices: dict[str, float],
    decision_hash: str,
    maximum_gross_pct: float = 70.0,
    minimum_trade_notional: float = 100.0,
) -> dict[str, Any]:
    positions = _normalized_positions(state.get("positions") or {})
    cash = max(_number(state.get("cash")), 0.0)
    marks = {str(symbol).upper(): max(_number(price), 0.0) for symbol, price in prices.items()}
    equity = cash + sum(
        item["quantity"] * marks.get(symbol, item["last_price"])
        for symbol, item in positions.items()
    )
    weights = {str(symbol).upper(): max(_number(weight), 0.0) for symbol, weight in target_weights.items()}
    gross_target = sum(weights.values())
    gross_limit = max(0.0, min(_number(maximum_gross_pct, 70.0), 100.0)) / 100.0
    blockers: list[str] = []
    if not decision_hash:
        blockers.append("decision_hash_required")
    if equity <= 0:
        blockers.append("equity_not_positive")
    if gross_target > gross_limit + 1e-12:
        blockers.append(f"gross_target:{gross_target:.6f}>{gross_limit:.6f}")
    missing_prices = sorted(symbol for symbol in set(weights) | set(positions) if marks.get(symbol, 0.0) <= 0)
    if missing_prices:
        blockers.append(f"missing_prices:{','.join(missing_prices)}")
    orders: list[dict[str, Any]] = []
    if not blockers:
        targets = {
            symbol: equity * weights.get(symbol, 0.0) / max(marks[symbol], 1e-12)
            for symbol in set(weights) | set(positions)
        }
        threshold = max(_number(minimum_trade_notional), 0.0)
        for symbol in sorted(targets):
            current = positions.get(symbol, {}).get("quantity", 0.0)
            difference = targets[symbol] - current
            notional = abs(difference) * marks[symbol]
            if difference < -1e-12 and notional >= threshold:
                orders.append({
                    "symbol": symbol,
                    "side": "SELL",
                    "quantity": round(abs(difference), 10),
                    "reference_price": round(marks[symbol], 8),
                    "notional": round(notional, 2),
                    "reduce_only": True,
                    "decision_hash": decision_hash,
                })
        for symbol in sorted(targets):
            current = positions.get(symbol, {}).get("quantity", 0.0)
            difference = targets[symbol] - current
            notional = abs(difference) * marks[symbol]
            if difference > 1e-12 and notional >= threshold:
                orders.append({
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": round(difference, 10),
                    "reference_price": round(marks[symbol], 8),
                    "notional": round(notional, 2),
                    "reduce_only": False,
                    "decision_hash": decision_hash,
                })
    payload = {
        "schema_version": PORTFOLIO_PAPER_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "decision_hash": str(decision_hash or ""),
        "equity": round(equity, 2),
        "gross_target_pct": round(gross_target * 100.0, 6),
        "maximum_gross_pct": round(gross_limit * 100.0, 6),
        "orders": orders,
        "simulation_preview_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["preview_hash"] = _canonical_hash(payload)
    return payload


class PortfolioPaperLedger:
    """Transactional long-only multi-symbol paper ledger with no live-order interface."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        now_ms: Callable[[], int],
        account_id: str = "portfolio-research",
        authorization_provider: Callable[[], dict[str, Any]] | None = None,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
        self.account_id = str(account_id or "portfolio-research")
        self.authorization_provider = authorization_provider
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
        return connection

    def _require_writable(self) -> None:
        require_runtime_writable(read_only=self.read_only, service="portfolio_paper_ledger")

    def _ensure_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS portfolio_paper_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_paper_accounts (
                    account_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_paper_positions (
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    last_price REAL NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY(account_id, symbol)
                );
                CREATE TABLE IF NOT EXISTS portfolio_paper_fills (
                    fill_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    account_id TEXT NOT NULL,
                    account_version INTEGER NOT NULL,
                    decision_hash TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS portfolio_paper_snapshots (
                    account_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    PRIMARY KEY(account_id, version)
                );
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO portfolio_paper_schema(key, value) VALUES('schema_version', ?)",
                (PORTFOLIO_PAPER_SCHEMA_VERSION,),
            )
            connection.commit()

    def _authorization_context(self) -> dict[str, Any]:
        if self.authorization_provider is None:
            return {}
        try:
            payload = self.authorization_provider()
        except Exception as exc:
            return {
                "status": "BLOCK",
                "blockers": [f"paper_authorization_provider_failed:{type(exc).__name__}"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        return dict(payload) if isinstance(payload, dict) else {}

    def _authorization_audit(
        self,
        state: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
        require_activation_readiness_hash: bool = False,
    ) -> dict[str, Any]:
        if state.get("simulation_enabled") is not True:
            return {
                "status": "BLOCK",
                "blockers": ["portfolio_simulation_not_authorized"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        state_blockers = _state_contract_blockers(state)
        if state_blockers:
            return {
                "status": "BLOCK",
                "blockers": state_blockers,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        raw_receipt = state.get("paper_activation_receipt")
        if not isinstance(raw_receipt, dict) or not raw_receipt:
            return {
                "status": "BLOCK",
                "blockers": [
                    "paper_activation_receipt_missing"
                    if raw_receipt is None or raw_receipt == ""
                    else "paper_activation_receipt_invalid_type"
                ],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        receipt = dict(raw_receipt)
        return verify_current_paper_authorization(
            receipt,
            context if context is not None else self._authorization_context(),
            expected_account_id=self.account_id,
            require_activation_readiness_hash=require_activation_readiness_hash,
        )

    def initialize(self, initial_cash: float, *, simulation_enabled: bool = False) -> dict[str, Any]:
        self._require_writable()
        cash = max(_number(initial_cash), 0.0)
        stamp = int(self.now_ms())
        simulation_flag_valid = type(simulation_enabled) is bool
        requested_enable = simulation_enabled is True
        state = {
            "schema_version": PORTFOLIO_PAPER_SCHEMA_VERSION,
            "account_id": self.account_id,
            "version": 1,
            "cash": cash,
            "realized_pnl": 0.0,
            "fees_paid": 0.0,
            "positions": {},
            "simulation_enabled": False,
            "paper_authorized": False,
            "paper_activation_receipt": {},
            "activation_status": "BLOCK",
            "activation_blockers": [
                "direct_simulation_enable_forbidden"
                if requested_enable else "paper_activation_receipt_required"
                if simulation_flag_valid else "simulation_enabled_invalid_type"
            ],
            "live_order_allowed": False,
            "updated_at": stamp,
        }
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT version, state_json FROM portfolio_paper_accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            if existing:
                try:
                    current = _decode_state(existing["state_json"])
                except (TypeError, ValueError, json.JSONDecodeError):
                    connection.rollback()
                    return self._blocked(["portfolio_paper_account_state_corrupt"])
                changed = str(current.get("schema_version") or "") != PORTFOLIO_PAPER_SCHEMA_VERSION
                current["schema_version"] = PORTFOLIO_PAPER_SCHEMA_VERSION
                current["account_id"] = self.account_id
                if current.get("live_order_allowed") is not False:
                    changed = True
                current["live_order_allowed"] = False
                raw_receipt = current.get("paper_activation_receipt")
                receipt = dict(raw_receipt) if isinstance(raw_receipt, dict) else {}
                receipt_audit = verify_paper_activation_receipt(
                    receipt,
                    expected_account_id=self.account_id,
                ) if receipt else {"status": "BLOCK", "blockers": ["paper_activation_receipt_missing"]}
                stored_flag_valid = type(current.get("simulation_enabled")) is bool
                if not stored_flag_valid:
                    current["simulation_enabled"] = False
                    current["paper_authorized"] = False
                    current["activation_status"] = "BLOCK"
                    current["activation_blockers"] = ["simulation_enabled_invalid_type"]
                    changed = True
                elif current.get("simulation_enabled") is True and receipt_audit.get("status") != "PASS":
                    current["simulation_enabled"] = False
                    current["paper_authorized"] = False
                    current["activation_status"] = "BLOCK"
                    current["activation_blockers"] = [
                        "legacy_unbound_simulation_disabled",
                        *list(receipt_audit.get("blockers") or []),
                    ]
                    changed = True
                else:
                    current.setdefault("paper_authorized", False)
                    current.setdefault("paper_activation_receipt", {})
                    current.setdefault("activation_status", "BLOCK")
                    current.setdefault("activation_blockers", ["paper_activation_receipt_required"])
                if not simulation_flag_valid:
                    current["activation_status"] = "BLOCK"
                    current["activation_blockers"] = ["simulation_enabled_invalid_type"]
                    changed = True
                elif requested_enable:
                    current["activation_status"] = "BLOCK"
                    current["activation_blockers"] = ["direct_simulation_enable_forbidden"]
                    changed = True
                if not changed:
                    connection.rollback()
                    return current
                new_version = int(existing["version"]) + 1
                current["version"] = new_version
                current["updated_at"] = stamp
                state_json = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                connection.execute(
                    "UPDATE portfolio_paper_accounts SET version = ?, updated_at = ?, state_json = ? WHERE account_id = ?",
                    (new_version, stamp, state_json, self.account_id),
                )
                connection.execute(
                    "INSERT INTO portfolio_paper_snapshots(account_id, version, reason, created_at, state_json) VALUES(?, ?, ?, ?, ?)",
                    (self.account_id, new_version, "fail_closed_schema_migration", stamp, state_json),
                )
                connection.commit()
                return current
            state_json = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "INSERT INTO portfolio_paper_accounts(account_id, version, updated_at, state_json) VALUES(?, 1, ?, ?)",
                (self.account_id, stamp, state_json),
            )
            connection.execute(
                "INSERT INTO portfolio_paper_snapshots(account_id, version, reason, created_at, state_json) VALUES(?, 1, 'initialize', ?, ?)",
                (self.account_id, stamp, state_json),
            )
            connection.commit()
        return state

    def activate_simulation(
        self,
        receipt: dict[str, Any],
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        self._require_writable()
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            return self._blocked(["invalid_expected_version"])
        context = self._authorization_context()
        if not isinstance(receipt, dict):
            return self._blocked(["paper_activation_receipt_invalid_type"])
        receipt_payload = dict(receipt)
        receipt_audit = verify_current_paper_authorization(
            receipt_payload,
            context,
            expected_account_id=self.account_id,
            require_activation_readiness_hash=True,
        )
        if receipt_audit.get("status") != "PASS":
            return self._blocked([
                "portfolio_paper_activation_not_authorized",
                *list(receipt_audit.get("blockers") or []),
            ])
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT version, state_json FROM portfolio_paper_accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            if not row:
                connection.rollback()
                return self._blocked(["account_not_initialized"])
            try:
                state = _decode_state(row["state_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                connection.rollback()
                return self._blocked(["portfolio_paper_account_state_corrupt"])
            version = int(row["version"])
            current_receipt = state.get("paper_activation_receipt")
            current_receipt_hash = str(current_receipt.get("receipt_hash") or "") if isinstance(current_receipt, dict) else ""
            requested_receipt_hash = str(receipt_payload.get("receipt_hash") or "")
            if state.get("simulation_enabled") is True and current_receipt_hash == requested_receipt_hash:
                connection.rollback()
                return {
                    "ok": True,
                    "status": "IDEMPOTENT_ACTIVATION",
                    "state": state,
                    "paper_authorized": True,
                    "live_order_allowed": False,
                }
            if version != int(expected_version):
                connection.rollback()
                return self._blocked([f"stale_account_version:{expected_version}!={version}"])
            position_count = int(connection.execute(
                "SELECT COUNT(*) FROM portfolio_paper_positions WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()[0])
            fill_count = int(connection.execute(
                "SELECT COUNT(*) FROM portfolio_paper_fills WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()[0])
            if position_count or fill_count:
                connection.rollback()
                return self._blocked(["paper_activation_requires_pristine_ledger"])
            new_version = version + 1
            state.update({
                "schema_version": PORTFOLIO_PAPER_SCHEMA_VERSION,
                "version": new_version,
                "cash": float(receipt_payload.get("initial_cash") or 0.0),
                "realized_pnl": 0.0,
                "fees_paid": 0.0,
                "positions": {},
                "simulation_enabled": True,
                "paper_authorized": True,
                "paper_activation_receipt": receipt_payload,
                "activation_status": "PASS",
                "activation_blockers": [],
                "active_candidate_hash": str(receipt_payload.get("candidate_hash") or ""),
                "live_order_allowed": False,
                "updated_at": stamp,
            })
            state_json = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "UPDATE portfolio_paper_accounts SET version = ?, updated_at = ?, state_json = ? WHERE account_id = ?",
                (new_version, stamp, state_json, self.account_id),
            )
            connection.execute(
                "INSERT INTO portfolio_paper_snapshots(account_id, version, reason, created_at, state_json) VALUES(?, ?, ?, ?, ?)",
                (self.account_id, new_version, f"activate:{requested_receipt_hash}", stamp, state_json),
            )
            connection.commit()
        return {
            "ok": True,
            "status": "ACTIVATED",
            "state": state,
            "paper_authorized": True,
            "live_order_allowed": False,
        }

    def load(self) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT state_json FROM portfolio_paper_accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
        if not row:
            return {}
        try:
            return _decode_state(row["state_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return {
                "schema_version": PORTFOLIO_PAPER_SCHEMA_VERSION,
                "account_id": self.account_id,
                "status": "BLOCK",
                "blockers": ["portfolio_paper_account_state_corrupt"],
                "simulation_enabled": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }

    def apply_fill(
        self,
        fill: dict[str, Any],
        *,
        expected_version: int,
        mode: str = "paper",
    ) -> dict[str, Any]:
        self._require_writable()
        payload = dict(fill or {})
        fill_id = str(payload.get("fill_id") or "")
        idempotency_key = str(payload.get("idempotency_key") or fill_id)
        decision_hash = str(payload.get("decision_hash") or "")
        symbol = str(payload.get("symbol") or "").upper()
        side = str(payload.get("side") or "").upper()
        raw_quantity = _strict_number(payload.get("quantity"))
        raw_price = _strict_number(payload.get("price"))
        raw_fee = _strict_number(payload.get("fee", 0.0))
        quantity = raw_quantity if raw_quantity is not None else 0.0
        price = raw_price if raw_price is not None else 0.0
        fee = raw_fee if raw_fee is not None else 0.0
        canonical_fill = {
            "fill_id": fill_id,
            "idempotency_key": idempotency_key,
            "decision_hash": decision_hash,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "fee": fee,
        }
        payload_hash = _canonical_hash(canonical_fill)
        blockers: list[str] = []
        if str(mode or "").lower() != "paper":
            blockers.append("live_mode_permanently_blocked")
        if not fill_id or not idempotency_key or not decision_hash:
            blockers.append("fill_id_idempotency_and_decision_hash_required")
        if (
            raw_quantity is None
            or raw_price is None
            or raw_fee is None
            or quantity <= 0
            or price <= 0
            or fee < 0
        ):
            blockers.append("invalid_fill_numeric_contract")
        if not symbol or side not in {"BUY", "SELL"}:
            blockers.append("invalid_fill_fields")
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            blockers.append("invalid_expected_version")
        if blockers:
            return self._blocked(blockers)

        context = self._authorization_context()
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT version, state_json FROM portfolio_paper_accounts WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()
            if not row:
                connection.rollback()
                return self._blocked(["account_not_initialized"])
            version = int(row["version"])
            try:
                state = _decode_state(row["state_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                connection.rollback()
                return self._blocked(["portfolio_paper_account_state_corrupt"])
            authorization = self._authorization_audit(state, context=context)
            if authorization.get("status") != "PASS":
                connection.rollback()
                return self._blocked([
                    "portfolio_simulation_not_authorized",
                    *list(authorization.get("blockers") or []),
                ])
            replay = connection.execute(
                "SELECT payload_hash, payload_json FROM portfolio_paper_fills WHERE fill_id = ? OR idempotency_key = ?",
                (fill_id, idempotency_key),
            ).fetchone()
            if replay:
                if str(replay["payload_hash"]) != payload_hash:
                    connection.rollback()
                    return self._blocked(["idempotency_conflict"])
                connection.rollback()
                return {
                    "ok": True,
                    "status": "IDEMPOTENT_REPLAY",
                    "fill": json.loads(replay["payload_json"]),
                    "state": state,
                    "paper_authorized": True,
                    "live_order_allowed": False,
                }
            if version != int(expected_version):
                connection.rollback()
                return self._blocked([f"stale_account_version:{expected_version}!={version}"])
            positions = _normalized_positions(state.get("positions") or {})
            current = dict(positions.get(symbol) or {})
            current_quantity = _number(current.get("quantity"))
            current_entry = _number(current.get("entry_price"))
            cash = _number(state.get("cash"))
            realized_pnl = _number(state.get("realized_pnl"))
            notional = quantity * price
            if side == "BUY":
                required_cash = notional + fee
                if required_cash > cash + 1e-8:
                    connection.rollback()
                    return self._blocked(["insufficient_paper_cash"])
                new_quantity = current_quantity + quantity
                entry_price = (current_entry * current_quantity + notional + fee) / max(new_quantity, 1e-12)
                positions[symbol] = {
                    "symbol": symbol,
                    "quantity": new_quantity,
                    "entry_price": entry_price,
                    "last_price": price,
                }
                cash -= required_cash
                fill_pnl = 0.0
            else:
                if quantity > current_quantity + 1e-8:
                    connection.rollback()
                    return self._blocked(["sell_quantity_exceeds_long_position"])
                fill_pnl = (price - current_entry) * quantity - fee
                realized_pnl += fill_pnl
                cash += notional - fee
                remaining = max(current_quantity - quantity, 0.0)
                if remaining <= 1e-12:
                    positions.pop(symbol, None)
                else:
                    positions[symbol] = {
                        "symbol": symbol,
                        "quantity": remaining,
                        "entry_price": current_entry,
                        "last_price": price,
                    }
            new_version = version + 1
            state.update({
                "version": new_version,
                "cash": cash,
                "realized_pnl": realized_pnl,
                "fees_paid": _number(state.get("fees_paid")) + fee,
                "positions": positions,
                "paper_authorized": True,
                "activation_status": "PASS",
                "activation_blockers": [],
                "updated_at": stamp,
                "live_order_allowed": False,
            })
            stored_fill = {
                **canonical_fill,
                "notional": notional,
                "realized_pnl": fill_pnl,
                "account_version": new_version,
                "created_at": stamp,
            }
            state_json = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "UPDATE portfolio_paper_accounts SET version = ?, updated_at = ?, state_json = ? WHERE account_id = ?",
                (new_version, stamp, state_json, self.account_id),
            )
            connection.execute("DELETE FROM portfolio_paper_positions WHERE account_id = ?", (self.account_id,))
            for item in positions.values():
                connection.execute(
                    """
                    INSERT INTO portfolio_paper_positions(account_id, symbol, quantity, entry_price, last_price, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (self.account_id, item["symbol"], item["quantity"], item["entry_price"], item["last_price"], stamp),
                )
            connection.execute(
                """
                INSERT INTO portfolio_paper_fills(
                    fill_id, idempotency_key, account_id, account_version, decision_hash,
                    payload_hash, created_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill_id,
                    idempotency_key,
                    self.account_id,
                    new_version,
                    decision_hash,
                    payload_hash,
                    stamp,
                    json.dumps(stored_fill, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            connection.execute(
                "INSERT INTO portfolio_paper_snapshots(account_id, version, reason, created_at, state_json) VALUES(?, ?, ?, ?, ?)",
                (self.account_id, new_version, f"fill:{fill_id}", stamp, state_json),
            )
            connection.commit()
        return {
            "ok": True,
            "status": "APPLIED",
            "fill": stored_fill,
            "state": state,
            "paper_authorized": True,
            "live_order_allowed": False,
        }

    def mark_to_market(self, prices: dict[str, float] | None = None) -> dict[str, Any]:
        state = self.load()
        requested_enable = state.get("simulation_enabled") is True
        authorization = self._authorization_audit(state) if requested_enable else {
            "status": "BLOCK",
            "blockers": list(
                state.get("blockers")
                or state.get("activation_blockers")
                or ["portfolio_simulation_not_authorized"]
            ),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        simulation_enabled = requested_enable and authorization.get("status") == "PASS"
        positions = _normalized_positions(state.get("positions") or {})
        marks = {str(symbol).upper(): max(_number(price), 0.0) for symbol, price in dict(prices or {}).items()}
        rows: list[dict[str, Any]] = []
        market_value = 0.0
        unrealized = 0.0
        for symbol, item in sorted(positions.items()):
            mark = marks.get(symbol) or item["last_price"] or item["entry_price"]
            value = item["quantity"] * mark
            pnl = (mark - item["entry_price"]) * item["quantity"]
            market_value += value
            unrealized += pnl
            rows.append({
                **item,
                "last_price": round(mark, 8),
                "market_value": round(value, 2),
                "unrealized_pnl": round(pnl, 2),
            })
        cash = _number(state.get("cash"))
        return {
            "schema_version": PORTFOLIO_PAPER_SCHEMA_VERSION,
            "account_id": self.account_id,
            "version": int(state.get("version") or 0),
            "status": (
                "SIMULATION_READY"
                if simulation_enabled
                else "SIMULATION_SUSPENDED"
                if requested_enable
                else "DISABLED_PENDING_CANDIDATE"
            ),
            "cash": round(cash, 2),
            "equity": round(cash + market_value, 2),
            "market_value": round(market_value, 2),
            "realized_pnl": round(_number(state.get("realized_pnl")), 2),
            "unrealized_pnl": round(unrealized, 2),
            "positions": rows,
            "position_count": len(rows),
            "simulation_enabled": simulation_enabled,
            "activation_status": str(authorization.get("status") or "BLOCK"),
            "activation_blockers": list(authorization.get("blockers") or []),
            "active_candidate_hash": str(state.get("active_candidate_hash") or ""),
            "activation_receipt_hash": str(
                state.get("paper_activation_receipt", {}).get("receipt_hash") or ""
            ) if isinstance(state.get("paper_activation_receipt"), dict) else "",
            "paper_authorized": simulation_enabled,
            "live_order_allowed": False,
        }

    def positions_for_risk(self) -> list[dict[str, Any]]:
        snapshot = self.mark_to_market()
        if snapshot.get("simulation_enabled") is not True:
            return []
        return [
            {
                "symbol": item["symbol"],
                "notional": item["market_value"],
                "direction": "LONG",
            }
            for item in snapshot["positions"]
            if _number(item.get("market_value")) > 0
        ]

    def summary(self) -> dict[str, Any]:
        snapshot = self.mark_to_market()
        with self._lock, closing(self._connect()) as connection:
            fill_count = int(connection.execute(
                "SELECT COUNT(*) FROM portfolio_paper_fills WHERE account_id = ?",
                (self.account_id,),
            ).fetchone()[0])
        return {**snapshot, "fill_count": fill_count, "path": str(self.db_path)}

    @staticmethod
    def _blocked(blockers: list[str]) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
