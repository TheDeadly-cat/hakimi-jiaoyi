"""Saved account projections remain evidence-only and never revalue holdings."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from exchange_terminal.services.legacy_record_exports import load_legacy_account_snapshot


SCHEMA = """
CREATE TABLE paper_account_state (
    account_id TEXT PRIMARY KEY, version INTEGER NOT NULL,
    updated_at INTEGER NOT NULL, state_json TEXT NOT NULL
);
CREATE TABLE paper_account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL,
    version INTEGER NOT NULL, reason TEXT NOT NULL, created_at INTEGER NOT NULL,
    state_json TEXT NOT NULL, UNIQUE(account_id, version)
);
CREATE TABLE paper_account_orders (
    account_order_id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
    created_at INTEGER NOT NULL, payload_json TEXT NOT NULL
);
"""


class LegacyAccountSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-saved-account-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "paper.sqlite3"

    def fingerprints(self) -> dict[str, str]:
        return {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def seed(self, state: dict | None, orders: list[dict] | None = None, *, account_id="default") -> None:
        absent = not self.path.exists()
        with closing(sqlite3.connect(self.path)) as database:
            if absent:
                database.executescript(SCHEMA)
            if state is not None:
                database.execute("INSERT INTO paper_account_state VALUES (?, 7, 123456789, ?)",
                                 (account_id, json.dumps(state, ensure_ascii=False)))
            database.executemany("INSERT INTO paper_account_orders VALUES (?, ?, ?, ?)", [
                (order["order_id"], account_id, order["time"], json.dumps(order, ensure_ascii=False))
                for order in (orders or [])
            ])
            database.commit()

    def test_saved_state_and_complete_orders_survive_without_new_valuation(self) -> None:
        old_order = {"order_id": "old", "time": 10, "symbol": "AAPL", "fee": .25, "run_id": "old-run"}
        current_order = {"order_id": "current", "time": 20, "symbol": "AAPL", "risk_request_id": "risk-1"}
        state = {"cash": 8123.45, "position_qty": 3, "entry_price": 123.5,
                 "realized_pnl": -4.5, "symbol": "AAPL", "strategy_id": "macd",
                 "orders": [current_order], "signals": [{"status": "UNKNOWN", "note": "原信号"}],
                 "equity_curve": [{"time": 5, "equity": 8500}], "future_field": {"kept": True}}
        self.seed(state, [current_order, old_order])
        with closing(sqlite3.connect(self.path)) as database:
            database.execute("INSERT INTO paper_account_snapshots(account_id, version, reason, created_at, state_json) VALUES ('default', 6, 'old', 1, ?)",
                             (json.dumps({"cash": 10000, "orders": []}),))
            database.commit()
        before = self.fingerprints()
        result = load_legacy_account_snapshot(self.path)
        self.assertTrue(result["available"])
        self.assertTrue(result["state_available"])
        self.assertEqual(result["cash"], 8123.45)
        self.assertEqual(result["position_qty"], 3)
        self.assertEqual(result["entry_price"], 123.5)
        self.assertEqual(result["signals"], state["signals"])
        self.assertEqual(result["equity_curve"], state["equity_curve"])
        self.assertEqual(result["future_field"], state["future_field"])
        self.assertNotIn("equity", result)
        self.assertNotIn("unrealized_pnl", result)
        self.assertNotIn("mark_price", result)
        self.assertEqual(result["account_version"], 7)
        self.assertEqual(result["as_of"], 123456789)
        self.assertEqual(result["valuation"], "saved_state_no_revaluation")
        self.assertEqual(result["saved_state_orders"], [current_order])
        self.assertEqual([order["order_id"] for order in result["orders"]], ["old", "current"])
        self.assertEqual(result["orders"][1]["risk_request_id"], "risk-1")
        self.assertEqual(result["orders"][0]["account_id"], "default")
        self.assertEqual(result["orders"][0]["account_order_id"], "old")
        self.assertEqual(result["source"], "archived_saved_account")
        self.assertEqual(before, self.fingerprints())

    def test_stored_authority_flags_are_false_at_every_projected_depth(self) -> None:
        fields = ("armed", "paper_armed", "paper_authorized", "binding_authorized", "paper_allowed",
                  "live_allowed", "order_allowed", "live_order_allowed", "paper_order_allowed",
                  "automated_paper_order_allowed", "execution_allowed", "execution_eligible",
                  "simulation_enabled", "can_trade", "can_execute", "can_submit", "restart_ready")
        hostile = dict.fromkeys(fields, True)
        hostile["read_only"] = False
        state = {**hostile, "cash": 500, "permissions": dict(hostile),
                 "signals": [{"capability": dict(hostile)}], "orders": []}
        self.seed(state, [{"order_id": "old", "time": 1, "authority": dict(hostile)}])
        before = self.fingerprints()
        result = load_legacy_account_snapshot(self.path)
        for projected in (result, result["permissions"], result["signals"][0]["capability"], result["orders"][0]["authority"]):
            for field in fields:
                self.assertIs(projected[field], False, field)
            self.assertIs(projected["read_only"], True)
        self.assertEqual(result["cash"], 500)
        self.assertEqual(before, self.fingerprints())

    def test_missing_database_has_no_fabricated_account_or_created_directory(self) -> None:
        path = self.root / "absent" / "paper.sqlite3"
        result = load_legacy_account_snapshot(path)
        self.assertFalse(result["available"])
        self.assertFalse(result["state_available"])
        self.assertEqual(result["history_status"], "NO_SAVED_ACCOUNT")
        self.assertNotIn("cash", result)
        self.assertNotIn("initial_cash", result)
        self.assertNotIn("equity", result)
        self.assertFalse(path.parent.exists())

    def test_other_account_state_and_orders_never_leak(self) -> None:
        self.seed({"cash": 9000, "orders": []}, [{"order_id": "other-order", "time": 1}], account_id="other")
        before = self.fingerprints()
        result = load_legacy_account_snapshot(self.path)
        self.assertFalse(result["available"])
        self.assertEqual(result["orders"], [])
        self.assertNotIn("cash", result)
        other = load_legacy_account_snapshot(self.path, account_id="other")
        self.assertEqual(other["cash"], 9000)
        self.assertEqual(other["orders"][0]["account_id"], "other")
        self.assertEqual(before, self.fingerprints())

    def test_saved_state_orders_are_visible_if_history_table_is_empty(self) -> None:
        orders = [{"order_id": "state-only", "time": 1, "fee": .5, "reason": "旧保存记录"}]
        self.seed({"cash": 7000, "orders": orders})
        before = self.fingerprints()
        result = load_legacy_account_snapshot(self.path)
        self.assertEqual(result["orders"], orders)
        self.assertEqual(result["orders_scope"], "saved_state_orders")
        self.assertEqual(result["saved_state_orders"], orders)
        self.assertEqual(before, self.fingerprints())

    def test_orphan_orders_are_labeled_without_reviving_a_versioned_account(self) -> None:
        self.seed(None, [{"order_id": "retained", "time": 1}])
        with closing(sqlite3.connect(self.path)) as database:
            database.execute("INSERT INTO paper_account_snapshots(account_id, version, reason, created_at, state_json) VALUES ('default', 2, 'old', 1, '{\"cash\": 10000}')")
            database.commit()
        result = load_legacy_account_snapshot(self.path)
        self.assertTrue(result["available"])
        self.assertFalse(result["state_available"])
        self.assertEqual(result["history_status"], "ORDERS_WITHOUT_STATE")
        self.assertNotIn("cash", result)
        self.assertIsNone(result["account_version"])

    def test_invalid_saved_state_fails_visibly_without_repair(self) -> None:
        self.seed({"orders": []})
        with closing(sqlite3.connect(self.path)) as database:
            database.execute("UPDATE paper_account_state SET state_json = '[]'")
            database.commit()
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "state_payload_invalid"):
            load_legacy_account_snapshot(self.path)
        self.assertEqual(before, self.fingerprints())

    def test_payload_account_identity_conflict_is_reported(self) -> None:
        self.seed({"account_id": "other", "orders": []})
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "identity_conflict"):
            load_legacy_account_snapshot(self.path)
        self.assertEqual(before, self.fingerprints())


if __name__ == "__main__":
    unittest.main()
