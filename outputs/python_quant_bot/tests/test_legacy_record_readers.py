"""Retained record reads use only isolated SQLite fixtures, with no executor."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import legacy_record_snapshot
from exchange_terminal.services.audit_log import AuditLog
from exchange_terminal.services.legacy_record_exports import load_legacy_order_export_rows


ORDER_SCHEMA = """
CREATE TABLE paper_account_orders (
    account_order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE paper_account_state (account_id TEXT PRIMARY KEY, state_json TEXT NOT NULL);
INSERT INTO paper_account_state VALUES ('default', '{"orders": []}');
"""
AUDIT_SCHEMA = """
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
"""


class LegacyRecordReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def snapshot(self) -> dict[str, str]:
        return {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*") if path.is_file()
        }

    def audit_reader(self, path: Path) -> tuple[AuditLog, Mock]:
        ensure_runtime = Mock(side_effect=AssertionError("reader must not initialize runtime"))
        return AuditLog(
            path=path.with_suffix(".jsonl"), db_path=path,
            ensure_runtime=ensure_runtime, now_ms=lambda: 999,
            publish_event=Mock(side_effect=AssertionError("reader must not publish events")),
            read_only=True,
        ), ensure_runtime

    def test_orders_include_reset_history_and_details_without_mixing_accounts(self) -> None:
        path = self.root / "paper.sqlite3"
        orders = [
            {"order_id": f"old-{i:03}", "time": i, "fee": .25,
             "funding_charged": -.125, "risk_request_id": f"risk-{i}",
             "run_id": "old-run", "reason": "中文,备注\n保留", "future_field": {"kept": True}}
            for i in range(103)
        ]
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(ORDER_SCHEMA)
            connection.executemany("INSERT INTO paper_account_orders VALUES (?, 'default', ?, ?)", [
                (row["order_id"], row["time"], json.dumps(row, ensure_ascii=False))
                for row in reversed(orders)
            ])
            connection.execute("INSERT INTO paper_account_orders VALUES ('other', 'other', 0, '{}')")
            connection.commit()
        before = self.snapshot()
        rows = load_legacy_order_export_rows(path)
        self.assertEqual(len(rows), 103)
        for expected, actual in zip(orders, rows):
            self.assertEqual(actual, {**expected, "account_id": "default", "account_order_id": expected["order_id"]})
        self.assertEqual(load_legacy_order_export_rows(path, account_id="other"), [
            {"account_id": "other", "account_order_id": "other"}
        ])
        self.assertEqual(before, self.snapshot())

    def test_missing_database_does_not_create_runtime_or_empty_database(self) -> None:
        path = self.root / "missing" / "paper.sqlite3"
        self.assertEqual(load_legacy_order_export_rows(path), [])
        self.assertEqual(self.snapshot(), {})
        self.assertFalse(path.parent.exists())

    def test_existing_incompatible_database_fails_without_schema_migration(self) -> None:
        path = self.root / "legacy.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE retained_record(value TEXT)")
            connection.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(sqlite3.OperationalError, "paper_account_orders"):
            load_legacy_order_export_rows(path)
        self.assertEqual(before, self.snapshot())

    def test_invalid_order_payload_is_reported_instead_of_silently_skipped(self) -> None:
        for payload in ("[1, 2]", "not-json"):
            path = self.root / ("array.sqlite3" if payload.startswith("[") else "invalid.sqlite3")
            with closing(sqlite3.connect(path)) as connection:
                connection.executescript(ORDER_SCHEMA)
                connection.execute("INSERT INTO paper_account_orders VALUES ('bad', 'default', 1, ?)", (payload,))
                connection.commit()
            before = self.snapshot()
            with self.assertRaises(ValueError):
                load_legacy_order_export_rows(path)
            self.assertEqual(before, self.snapshot())

    def test_orders_read_committed_wal_without_uncommitted_rows(self) -> None:
        path = self.root / "wal-orders.sqlite3"
        with closing(sqlite3.connect(path)) as writer:
            writer.executescript(ORDER_SCHEMA)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO paper_account_orders VALUES ('kept', 'default', 1, '{\"fee\": 1.25}')")
            writer.commit()
            writer.execute("INSERT INTO paper_account_orders VALUES ('pending', 'default', 2, '{}')")
            # Windows locks bytes in an active writer's SHM; validate the full
            # file set plus database/WAL bytes here. Closed sidecars are tested
            # byte-for-byte separately below.
            file_set_before = {p.name for p in self.root.iterdir()}
            data_before = {p.name: p.read_bytes() for p in (path, Path(str(path) + "-wal"))}
            self.assertEqual(load_legacy_order_export_rows(path), [
                {"fee": 1.25, "account_id": "default", "account_order_id": "kept"}
            ])
            self.assertEqual(file_set_before, {p.name for p in self.root.iterdir()})
            self.assertEqual(data_before, {p.name: p.read_bytes() for p in (path, Path(str(path) + "-wal"))})
            writer.rollback()

    def test_audit_snapshot_exceeds_ui_limit_and_preserves_all_events(self) -> None:
        path = self.root / "audit.sqlite3"
        events = [{"time": i, "type": "UNKNOWN", "detail": f"原事件 {i}"} for i in range(5003)]
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(AUDIT_SCHEMA)
            connection.executemany("INSERT INTO audit_events(time,type,payload_json) VALUES (?, ?, ?)", [
                (event["time"], event["type"], json.dumps(event, ensure_ascii=False)) for event in events
            ])
            connection.commit()
        reader, ensure_runtime = self.audit_reader(path)
        before = self.snapshot()
        self.assertEqual(len(reader.read(9000)), 5000)
        exported = reader.export_snapshot()
        self.assertEqual(exported, events)
        ensure_runtime.assert_not_called()
        self.assertEqual(before, self.snapshot())
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("INSERT INTO audit_events(time,type,payload_json) VALUES (9999, 'export_ledger', ?)",
                               (json.dumps({"time": 9999, "type": "export_ledger"}),))
            connection.commit()
        self.assertEqual(exported, events)
        self.assertEqual(reader.export_snapshot()[:-1], events)

    def test_audit_snapshot_includes_committed_wal_and_excludes_inflight_event(self) -> None:
        path = self.root / "wal-audit.sqlite3"
        with closing(sqlite3.connect(path)) as writer:
            writer.executescript(AUDIT_SCHEMA)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO audit_events(time,type,payload_json) VALUES (1, 'kept', '{\"type\": \"kept\"}')")
            writer.commit()
            writer.execute("INSERT INTO audit_events(time,type,payload_json) VALUES (2, 'pending', '{\"type\": \"pending\"}')")
            reader, ensure_runtime = self.audit_reader(path)
            file_set_before = {p.name for p in self.root.iterdir()}
            data_before = {p.name: p.read_bytes() for p in (path, Path(str(path) + "-wal"))}
            self.assertEqual(reader.export_snapshot(), [{"type": "kept"}])
            self.assertEqual(file_set_before, {p.name for p in self.root.iterdir()})
            self.assertEqual(data_before, {p.name: p.read_bytes() for p in (path, Path(str(path) + "-wal"))})
            ensure_runtime.assert_not_called()
            writer.rollback()

    def test_audit_reader_reports_missing_or_invalid_history(self) -> None:
        missing, _ = self.audit_reader(self.root / "missing.sqlite3")
        with self.assertRaises(FileNotFoundError):
            missing.export_snapshot()
        self.assertEqual(self.snapshot(), {})
        path = self.root / "invalid-audit.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(AUDIT_SCHEMA)
            connection.execute("INSERT INTO audit_events(time,type,payload_json) VALUES (1, 'bad', '[]')")
            connection.commit()
        reader, _ = self.audit_reader(path)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "audit_event_payload_invalid"):
            reader.export_snapshot()
        self.assertEqual(before, self.snapshot())

    def test_wal_change_during_snapshot_fails_instead_of_exporting_mixed_history(self) -> None:
        path = self.root / "changing-wal.sqlite3"
        with closing(sqlite3.connect(path)) as writer:
            writer.executescript(ORDER_SCHEMA)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO paper_account_orders VALUES ('old', 'default', 1, '{}')")
            writer.commit()
            original_identity = legacy_record_snapshot._source_identity
            changed = False

            def change_after_capture(database_path: Path):
                nonlocal changed
                identity = original_identity(database_path)
                if database_path == path and not changed:
                    changed = True
                    writer.execute("INSERT INTO paper_account_orders VALUES ('new', 'default', 2, '{}')")
                    writer.commit()
                return identity

            with patch.object(legacy_record_snapshot, "_source_identity", side_effect=change_after_capture):
                with self.assertRaisesRegex(
                    legacy_record_snapshot.LegacyRecordSnapshotChangedError, "snapshot_changed_retry"
                ):
                    load_legacy_order_export_rows(path)
            self.assertTrue(changed)
            self.assertEqual(len(load_legacy_order_export_rows(path)), 2)

    def test_retained_wal_and_opaque_source_shm_remain_byte_identical(self) -> None:
        path = self.root / "retained-wal.sqlite3"
        wal = Path(str(path) + "-wal")
        shm = Path(str(path) + "-shm")
        with closing(sqlite3.connect(path)) as writer:
            writer.executescript(ORDER_SCHEMA)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO paper_account_orders VALUES ('retained', 'default', 1, '{}')")
            writer.commit()
            retained_database, retained_wal = path.read_bytes(), wal.read_bytes()
        # Re-create an uncheckpointed archive entirely within the fixture. Its
        # original SHM is opaque evidence, never something the reader rewrites.
        path.write_bytes(retained_database)
        wal.write_bytes(retained_wal)
        shm.write_bytes(b"retained source shared-memory evidence")
        before = self.snapshot()
        self.assertEqual(load_legacy_order_export_rows(path), [
            {"account_id": "default", "account_order_id": "retained"}
        ])
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
