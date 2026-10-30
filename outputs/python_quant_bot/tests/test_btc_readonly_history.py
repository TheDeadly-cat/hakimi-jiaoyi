"""Original BTC history boundaries, using temporary files and extracted helpers."""
from __future__ import annotations

import ast
import csv
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import Mock


SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
FUNCTION_NAMES = {"read_btc_daily_sqlite", "copy_btc_database_for_reading", "unique_existing_paths", "read_local_btc_daily"}
FUNCTIONS = [node for node in ast.parse(SERVER.read_text(encoding="utf-8")).body
             if isinstance(node, ast.FunctionDef) and node.name in FUNCTION_NAMES]


def functions(runtime: Path, *, read_only: bool) -> dict[str, Any]:
    namespace = {
        "Path": Path, "Any": Any, "sqlite3": sqlite3, "csv": csv, "shutil": shutil,
        "RUNTIME_READ_ONLY": read_only, "ensure_runtime": Mock(),
        "BTC_DAILY_DB": runtime / "source.sqlite", "BTC_DAILY_DB_CACHE": runtime / "cache.sqlite",
        "BTC_DAILY_FALLBACK_DB": runtime / "missing.sqlite", "BTC_DAILY_CSV": runtime / "source.csv",
        "BTC_DAILY_FALLBACK_CSV": runtime / "missing.csv",
    }
    exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SERVER), "exec"), namespace)
    return namespace


def create_history(path: Path, *, retained_wal: bool = False, wal_mode: bool = False) -> None:
    connection = sqlite3.connect(path)
    try:
        if retained_wal or wal_mode:
            connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE btc_daily_prices (
            symbol TEXT, trading_date TEXT, ts_ms INTEGER, open REAL, high REAL, low REAL,
            close REAL, volume REAL, volume_ccy REAL, volume_quote REAL, confirmed INTEGER, source TEXT)""")
        connection.commit()
        if retained_wal:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("INSERT INTO btc_daily_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("BTC-USDT", "2026-01-02", 1, 1, 2, 1, 1.5, 10, 10, 15, 1, "test-fixture"))
        connection.commit()
        if retained_wal:
            database_bytes = path.read_bytes()
            wal_bytes = Path(str(path) + "-wal").read_bytes()
    finally:
        connection.close()
    if retained_wal:
        path.write_bytes(database_bytes)
        Path(str(path) + "-wal").write_bytes(wal_bytes)


class BtcReadOnlyHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="hakimi-btc-read-boundary-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.assertEqual({node.name for node in FUNCTIONS}, FUNCTION_NAMES)

    def snapshot(self) -> dict[str, str]:
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.iterdir() if path.is_file()}

    def test_read_failure_keeps_existing_cache_and_uses_existing_csv(self) -> None:
        namespace = functions(self.root, read_only=True)
        namespace["BTC_DAILY_DB"].write_bytes(b"unreadable original source")
        namespace["BTC_DAILY_DB_CACHE"].write_bytes(b"historical cache must stay unchanged")
        namespace["BTC_DAILY_CSV"].write_text("date,close\n2026-01-02,1.5\n", encoding="utf-8")
        before = self.snapshot()
        namespace["copy_btc_database_for_reading"] = Mock(side_effect=AssertionError("read must not copy"))
        result = namespace["read_local_btc_daily"](5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "local_csv")
        self.assertEqual(result["rows"], [{"date": "2026-01-02", "close": "1.5"}])
        self.assertIn("sqlite direct", result["warning"])
        namespace["copy_btc_database_for_reading"].assert_not_called()
        namespace["ensure_runtime"].assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_read_failure_without_fallback_reports_failure_without_copy(self) -> None:
        namespace = functions(self.root, read_only=True)
        namespace["BTC_DAILY_DB"].write_bytes(b"unreadable original source")
        namespace["BTC_DAILY_DB_CACHE"].write_bytes(b"historical cache")
        before = self.snapshot()
        result = namespace["read_local_btc_daily"](5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["rows"], [])
        self.assertIn("source.sqlite", result["error"])
        self.assertIn("cache.sqlite", result["error"])
        namespace["ensure_runtime"].assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_direct_cache_copy_is_blocked_before_any_runtime_write(self) -> None:
        namespace = functions(self.root, read_only=True)
        namespace["BTC_DAILY_DB"].write_bytes(b"source")
        namespace["BTC_DAILY_DB_CACHE"].write_bytes(b"saved-cache")
        before = self.snapshot()
        with self.assertRaisesRegex(PermissionError, "cache_copy_disabled"):
            namespace["copy_btc_database_for_reading"]()
        namespace["ensure_runtime"].assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_clean_wal_mode_database_returns_history_without_creating_sidecars(self) -> None:
        namespace = functions(self.root, read_only=True)
        create_history(namespace["BTC_DAILY_DB"], wal_mode=True)
        before = self.snapshot()
        rows = namespace["read_btc_daily_sqlite"](namespace["BTC_DAILY_DB"], 5)
        self.assertEqual(rows[0]["date"], "2026-01-02")
        self.assertEqual(rows[0]["close"], 1.5)
        self.assertEqual(self.snapshot(), before)

    def test_nonempty_wal_is_rejected_without_hiding_committed_rows(self) -> None:
        namespace = functions(self.root, read_only=True)
        create_history(namespace["BTC_DAILY_DB"], retained_wal=True)
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "journal_pending"):
            namespace["read_btc_daily_sqlite"](namespace["BTC_DAILY_DB"], 5)
        self.assertEqual(self.snapshot(), before)
        namespace["RUNTIME_READ_ONLY"] = False
        rows = namespace["read_btc_daily_sqlite"](namespace["BTC_DAILY_DB"], 5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["close"], 1.5)

    def test_pending_rollback_journal_is_preserved(self) -> None:
        namespace = functions(self.root, read_only=True)
        create_history(namespace["BTC_DAILY_DB"])
        Path(str(namespace["BTC_DAILY_DB"]) + "-journal").write_bytes(b"pending journal")
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "journal_pending"):
            namespace["read_btc_daily_sqlite"](namespace["BTC_DAILY_DB"], 5)
        self.assertEqual(self.snapshot(), before)

    def test_existing_clean_fallback_reports_primary_wal_failure(self) -> None:
        namespace = functions(self.root, read_only=True)
        create_history(namespace["BTC_DAILY_DB"], retained_wal=True)
        create_history(namespace["BTC_DAILY_DB_CACHE"])
        before = self.snapshot()
        result = namespace["read_local_btc_daily"](5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], str(namespace["BTC_DAILY_DB_CACHE"]))
        self.assertEqual(result["read_status"], "EXISTING_FALLBACK")
        self.assertIn("journal_pending", result["warning"])
        self.assertEqual(self.snapshot(), before)

    def test_normal_mode_retains_existing_copy_behavior(self) -> None:
        namespace = functions(self.root, read_only=False)
        namespace["BTC_DAILY_DB"].write_bytes(b"normal mode source")
        namespace["BTC_DAILY_DB_CACHE"].write_bytes(b"old")
        result = namespace["copy_btc_database_for_reading"]()
        self.assertEqual(result, namespace["BTC_DAILY_DB_CACHE"])
        self.assertEqual(result.read_bytes(), b"normal mode source")

    def test_locked_database_reports_error_without_copying_over_existing_cache(self) -> None:
        namespace = functions(self.root, read_only=True)
        create_history(namespace["BTC_DAILY_DB"])
        create_history(namespace["BTC_DAILY_DB_CACHE"])
        original_connect = sqlite3.connect

        def connect(database: str, **kwargs: Any):
            if "source.sqlite" in database:
                raise sqlite3.OperationalError("database is locked")
            return original_connect(database, **kwargs)

        namespace["sqlite3"] = SimpleNamespace(connect=connect, Row=sqlite3.Row)
        namespace["copy_btc_database_for_reading"] = Mock(side_effect=AssertionError("read must not copy"))
        before = self.snapshot()
        result = namespace["read_local_btc_daily"](5)
        self.assertEqual(result["read_status"], "EXISTING_FALLBACK")
        self.assertIn("database is locked", result["warning"])
        namespace["copy_btc_database_for_reading"].assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_source_changed_during_immutable_read_is_reported(self) -> None:
        namespace = functions(self.root, read_only=True)
        path = namespace["BTC_DAILY_DB"]
        create_history(path)
        info = path.stat()

        def fetchall():
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
            return [{"date": "2026-01-02", "close": 1.5}]

        connection = SimpleNamespace(
            row_factory=None,
            execute=Mock(return_value=SimpleNamespace(fetchall=fetchall)),
            close=Mock(),
        )
        namespace["sqlite3"] = SimpleNamespace(connect=Mock(return_value=connection), Row=sqlite3.Row)
        with self.assertRaisesRegex(RuntimeError, "changed_during_read"):
            namespace["read_btc_daily_sqlite"](path, 5)
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
