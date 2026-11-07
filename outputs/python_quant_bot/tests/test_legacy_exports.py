"""Exercise actual CSV helpers with temporary records; never import the server."""
from __future__ import annotations

import ast
from contextlib import closing
from copy import deepcopy
import csv
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch

from exchange_terminal.services.audit_log import AuditLog
from exchange_terminal.services.legacy_record_exports import load_legacy_order_export_rows
from tests.test_legacy_record_readers import ORDER_SCHEMA


SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
FUNCTION_NAMES = {
    "csv_export_cell", "csv_export_directory", "write_csv", "export_file_metadata",
    "export_orders", "export_ledger", "record_runtime_audit", "append_ledger",
}
FUNCTIONS = [node for node in ast.parse(SERVER.read_text(encoding="utf-8")).body
             if isinstance(node, ast.FunctionDef) and node.name in FUNCTION_NAMES]


def namespace(root: Path, audit: AuditLog) -> dict[str, Any]:
    published_events: list[dict[str, Any]] = []

    def publish(event_type: str, row: dict[str, Any], *, source: str) -> dict[str, Any]:
        published_events.append({"type": event_type, "row": row, "source": source})
        return {"seq": len(published_events)}

    scope = {
        "Any": Any, "Path": Path, "csv": csv, "json": json, "os": os, "secrets": secrets,
        "time": SimpleNamespace(strftime=lambda _: "20261024_100000"),
        "ensure_runtime": lambda: None, "RUNTIME_DIR": root, "EXPORT_DIR": root / "exports",
        "RUNTIME_READ_ONLY": False, "now_ms": lambda: 100,
        "EVENT_BUS": SimpleNamespace(publish=publish), "published_events": published_events,
        "load_legacy_order_export_rows": load_legacy_order_export_rows,
        "AUDIT_LOG": audit,
    }
    exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SERVER), "exec"), scope)
    return scope


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class LegacyExportTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "runtime"
        self.root.mkdir()
        self.order_path = self.root / "paper_ledger.sqlite3"
        self.audit = AuditLog(path=self.root / "audit.jsonl", ensure_runtime=lambda: None,
                              now_ms=lambda: 100)
        self.scope = namespace(self.root, self.audit)
        self.assertEqual({node.name for node in FUNCTIONS}, FUNCTION_NAMES)

    def seed_orders(self, orders: list[dict[str, Any]], account_id: str = "default") -> None:
        missing = not self.order_path.exists()
        with closing(sqlite3.connect(self.order_path)) as connection:
            if missing:
                connection.executescript(ORDER_SCHEMA)
            connection.executemany("INSERT INTO paper_account_orders VALUES (?, ?, ?, ?)", [
                (row["order_id"], account_id, row["time"], json.dumps(row, ensure_ascii=False))
                for row in orders
            ])
            connection.commit()

    def test_same_second_exports_preserve_both_files_and_full_33_column_details(self) -> None:
        order = {"time": 1, "symbol": "AAPL", "order_id": "old-1", "side": "SELL",
                 "pnl": -1.75, "fee": .25, "funding_charged": -.125,
                 "funding_estimate": .5, "risk_request_id": "risk-1", "run_id": "run-1",
                 "reason": "中文,备注\n第二行", "future_field": {"kept": True}}
        self.seed_orders([order])
        source_before = self.order_path.read_bytes()
        first = self.scope["export_orders"]()
        original_bytes = Path(first["path"]).read_bytes()
        second = self.scope["export_orders"]()
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(Path(first["path"]).read_bytes(), original_bytes)
        self.assertTrue(original_bytes.startswith(b"\xef\xbb\xbf"))
        rows = read_csv(Path(first["path"]))
        self.assertEqual(first["rows"], len(rows))
        self.assertEqual(len(rows[0]), 33)
        self.assertEqual(rows[0]["pnl"], "-1.75")
        self.assertEqual(rows[0]["funding_charged"], "-0.125")
        self.assertEqual(rows[0]["fee"], "0.25")
        self.assertEqual(rows[0]["risk_request_id"], "risk-1")
        self.assertEqual(rows[0]["run_id"], "run-1")
        self.assertEqual(rows[0]["reason"], order["reason"])
        payload = json.loads(rows[0]["payload"])
        for key, value in order.items():
            self.assertEqual(payload[key], value)
        self.assertFalse(first["truncated"])
        self.assertEqual(first["scope"], "account_history")
        self.assertEqual(first["filename"], Path(first["path"]).name)
        self.assertEqual(self.order_path.read_bytes(), source_before)

    def test_exclusive_creation_refuses_to_replace_existing_export(self) -> None:
        target = self.root / "existing.csv"
        target.write_bytes(b"previous export bytes")
        with self.assertRaises(FileExistsError):
            self.scope["write_csv"](target, [{"value": 5}], ["value"])
        self.assertEqual(target.read_bytes(), b"previous export bytes")

    def test_random_name_collision_preserves_first_file_and_no_success_event(self) -> None:
        self.scope["secrets"] = SimpleNamespace(token_hex=lambda _: "forced_collision")
        first = self.scope["export_orders"]()
        previous = Path(first["path"]).read_bytes()
        audit_before = self.audit.export_snapshot()
        with self.assertRaises(FileExistsError):
            self.scope["export_orders"]()
        self.assertEqual(Path(first["path"]).read_bytes(), previous)
        self.assertEqual(self.audit.export_snapshot(), audit_before)

    def test_formula_text_escaped_while_numbers_and_original_payload_survive(self) -> None:
        formulas = ["=1+1", "+SUM(A1)", "-SUM(A1)", "@SUM(A1)", "  =1+1", "\t=1+1", "\r=1+1", "\n=1+1"]
        orders = [{"order_id": f"id-{i}", "time": i + 1, "reason": value,
                   "pnl": -12.5, "quantity": 2} for i, value in enumerate(formulas)]
        before = deepcopy(orders)
        self.seed_orders(orders)
        result = self.scope["export_orders"]()
        rows = read_csv(Path(result["path"]))
        self.assertEqual(orders, before)
        for row, original in zip(rows, formulas):
            self.assertEqual(row["reason"], "'" + original)
            self.assertEqual(row["pnl"], "-12.5")
            self.assertEqual(row["quantity"], "2")
            self.assertEqual(json.loads(row["payload"])["reason"], original)

    def test_empty_history_exports_headers_without_creating_paper_database(self) -> None:
        result = self.scope["export_orders"]()
        self.assertEqual(result["rows"], 0)
        self.assertEqual(read_csv(Path(result["path"])), [])
        with Path(result["path"]).open(encoding="utf-8-sig", newline="") as handle:
            columns = next(csv.reader(handle))
        self.assertEqual(len(columns), 33)
        self.assertIn("funding_charged", columns)
        self.assertIn("payload", columns)
        self.assertFalse(self.order_path.exists())

    def test_history_survives_reset_and_excludes_other_accounts(self) -> None:
        orders = [{"order_id": f"old-{i:03}", "time": i + 1, "symbol": "AAPL"} for i in range(101)]
        self.seed_orders(orders)
        self.seed_orders([{"order_id": "other-1", "time": 1, "symbol": "HK.00836"}], account_id="other")
        with closing(sqlite3.connect(self.order_path)) as connection:
            state = json.loads(connection.execute("SELECT state_json FROM paper_account_state WHERE account_id='default'").fetchone()[0])
        self.assertEqual(state["orders"], [])
        result = self.scope["export_orders"]()
        exported = read_csv(Path(result["path"]))
        self.assertEqual(result["rows"], 101)
        self.assertEqual([row["order_id"] for row in exported], [row["order_id"] for row in orders])
        self.assertTrue(all(row["account_id"] == "default" for row in exported))

    def test_readonly_history_read_preserves_database_bytes(self) -> None:
        self.seed_orders([{"order_id": "kept", "time": 1, "reason": "保留"}])
        self.audit.append({"type": "UNKNOWN", "detail": "原事件"})
        paths = [self.order_path, self.audit.db_path]
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        audit_reader = AuditLog(path=self.root / "audit.jsonl", ensure_runtime=lambda: None,
                                now_ms=lambda: 200, read_only=True)
        self.assertEqual(load_legacy_order_export_rows(self.order_path)[0]["order_id"], "kept")
        self.assertEqual(audit_reader.export_snapshot()[0]["type"], "UNKNOWN")
        self.assertEqual(before, {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})

    def test_ledger_export_exceeds_ui_limit_without_changing_old_events(self) -> None:
        old_rows = [{"time": i + 1, "type": "UNKNOWN", "detail": f"原事件 {i}"} for i in range(5003)]
        with closing(sqlite3.connect(self.audit.db_path)) as connection:
            connection.executemany("INSERT INTO audit_events(time,type,payload_json) VALUES (?,?,?)",
                                   [(row["time"], row["type"], json.dumps(row, ensure_ascii=False)) for row in old_rows])
            connection.commit()
        self.assertEqual(len(self.audit.read(9000)), 5000)
        result = self.scope["export_ledger"]()
        exported = read_csv(Path(result["path"]))
        self.assertEqual(result["rows"], 5003)
        self.assertFalse(result["truncated"])
        self.assertEqual([json.loads(row["payload"]) for row in exported], old_rows)
        after = self.audit.export_snapshot()
        self.assertEqual(after[:-1], old_rows)
        self.assertEqual(after[-1]["type"], "export_ledger")
        self.assertEqual(after[-1]["rows"], 5003)

    def test_ledger_export_same_second_keeps_previous_snapshot(self) -> None:
        self.audit.append({"type": "原事件"})
        first = self.scope["export_ledger"]()
        old = Path(first["path"]).read_bytes()
        second = self.scope["export_ledger"]()
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(Path(first["path"]).read_bytes(), old)
        self.assertEqual(second["rows"], first["rows"] + 1)

    def test_corrupt_database_fails_before_export_or_success_audit(self) -> None:
        self.order_path.write_bytes(b"retained damaged database")
        before = self.order_path.read_bytes()
        with self.assertRaises(sqlite3.DatabaseError):
            self.scope["export_orders"]()
        self.assertEqual(self.order_path.read_bytes(), before)
        self.assertFalse((self.root / "exports").exists())
        self.assertEqual(self.audit.export_snapshot(), [])

    def test_bad_event_payload_fails_before_export_or_success_audit(self) -> None:
        with closing(sqlite3.connect(self.audit.db_path)) as connection:
            connection.execute("INSERT INTO audit_events(time,type,payload_json) VALUES (1,'UNKNOWN','not-json')")
            connection.commit()
        before = self.audit.db_path.read_bytes()
        with self.assertRaises(ValueError):
            self.scope["export_ledger"]()
        self.assertEqual(self.audit.db_path.read_bytes(), before)
        self.assertFalse((self.root / "exports").exists())

    def test_readonly_exports_to_external_directory_preserve_entire_runtime(self) -> None:
        self.seed_orders([{"order_id": "old-1", "time": 1, "fee": .25, "reason": "历史订单"}])
        self.audit.append({"type": "UNKNOWN", "detail": "历史事件"})
        reader = AuditLog(path=self.root / "audit.jsonl", ensure_runtime=lambda: None,
                          now_ms=lambda: 200, read_only=True)
        self.scope["RUNTIME_READ_ONLY"] = True
        self.scope["AUDIT_LOG"] = reader
        external = self.root.parent / "user-exports"
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        with patch.dict(os.environ, {"HAKIMI_EXPORT_DIR": str(external)}):
            orders = self.scope["export_orders"]()
            events = self.scope["export_ledger"]()
        self.assertEqual(Path(orders["path"]).parent, external)
        self.assertEqual(Path(events["path"]).parent, external)
        self.assertEqual(read_csv(Path(orders["path"]))[0]["order_id"], "old-1")
        self.assertEqual(read_csv(Path(events["path"]))[0]["type"], "UNKNOWN")
        after = {path.relative_to(self.root).as_posix(): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertEqual(len(self.scope["published_events"]), 2)
        self.assertTrue(all(event["row"]["persistence_status"] == "READ_ONLY_SKIPPED"
                            for event in self.scope["published_events"]))

    def test_readonly_export_rejects_destination_inside_original_runtime(self) -> None:
        self.scope["RUNTIME_READ_ONLY"] = True
        for destination in (self.root, self.root / "exports", self.root.parent / "unused" / ".." / "runtime" / "exports"):
            with self.subTest(destination=destination):
                with patch.dict(os.environ, {"HAKIMI_EXPORT_DIR": str(destination)}):
                    with self.assertRaisesRegex(ValueError, "原数据工作区之外"):
                        self.scope["export_orders"]()
        self.assertFalse((self.root / "exports").exists())
        self.assertEqual(self.audit.export_snapshot(), [])


if __name__ == "__main__":
    unittest.main()
