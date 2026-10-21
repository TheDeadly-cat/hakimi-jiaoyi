import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_history
from exchange_terminal.services.terminal_history import TerminalHistoryReader


class TerminalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "strategy_pipeline.sqlite3"
        self.reader = TerminalHistoryReader(self.root)

    def seed(self, *, corrupt_report=False, corrupt_version=False):
        spec = json.dumps({"strategy_id": "dual_ma", "params": {"fast_window": 7}})
        report = json.dumps({"symbol": "FIXTURE", "current": {"total_return_pct": 1.2}})
        run = json.dumps({"run_id": "run-1", "strategy_id": "dual_ma", "symbol": "FIXTURE", "strategy_version_id": "version-1"})
        with closing(sqlite3.connect(self.path)) as c:
            c.executescript("""CREATE TABLE strategy_runs(run_id TEXT,strategy_id TEXT,symbol TEXT,status TEXT,updated_at INTEGER,payload_json TEXT);
                CREATE TABLE strategy_versions(version_id TEXT,strategy_id TEXT,fingerprint TEXT,spec_json TEXT);
                CREATE TABLE backtest_artifacts(artifact_id TEXT,run_id TEXT,report_hash TEXT,payload_json TEXT);""")
            c.execute("INSERT INTO strategy_runs VALUES(?,?,?,?,?,?)", ("run-1", "dual_ma", "FIXTURE", "RESEARCH", 1, run))
            c.execute("INSERT INTO strategy_versions VALUES(?,?,?,?)", ("version-1", "dual_ma", "bad" if corrupt_version else hashlib.sha256(spec.encode()).hexdigest(), spec))
            c.execute("INSERT INTO backtest_artifacts VALUES(?,?,?,?)", ("artifact-1", "run-1", "bad" if corrupt_report else hashlib.sha256(report.encode()).hexdigest(), report))
            c.commit()

    def inventory(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def test_original_evidence_read_in_place_and_not_promoted(self):
        self.seed()
        before = self.inventory()
        view = self.reader("run-1")
        self.assertEqual(view["version"]["spec"]["params"], {"fast_window": 7})
        self.assertEqual(view["artifact"]["payload"]["current"]["total_return_pct"], 1.2)
        self.assertEqual(view["integrity_status"], "PASS")
        self.assertFalse(view["replay_available"])
        self.assertFalse(view["paper_allowed"])
        self.assertFalse(view["live_allowed"])
        self.assertEqual(len(self.reader()["items"]), 1)
        self.assertEqual(before, self.inventory())

    def test_tampered_report_stays_visible_but_blocked(self):
        self.seed(corrupt_report=True)
        view = self.reader("run-1")
        self.assertEqual(view["integrity_status"], "BLOCK")
        self.assertIn("original_report_hash_mismatch", view["warnings"])

    def test_tampered_version_is_not_used_as_verified_configuration(self):
        self.seed(corrupt_version=True)
        self.assertEqual(self.reader("run-1")["version"]["integrity_status"], "BLOCK")

    def test_wal_prevents_immutable_read_of_stale_database(self):
        self.seed()
        Path(str(self.path) + "-wal").write_bytes(b"uncheckpointed fixture")
        with self.assertRaisesRegex(ValueError, "database_busy"):
            self.reader()

    def test_read_detects_source_change(self):
        self.seed()
        original = self.reader._stable_identity
        calls = []
        def changing():
            calls.append(1)
            value = original()
            return value if len(calls) == 1 else (0, 0, "changed")
        self.reader._stable_identity = changing
        with self.assertRaisesRegex(ValueError, "changed_during_read"):
            self.reader()

    def test_missing_database_and_invalid_identifier(self):
        self.assertEqual(self.reader()["items"], [])
        self.assertFalse(self.path.exists())
        with self.assertRaises(FileNotFoundError):
            self.reader("missing")
        with self.assertRaises(ValueError):
            self.reader("../../outside")


class TerminalReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "reports"
        self.directory.mkdir()
        self.reader = TerminalHistoryReader(self.root)

    def seed(self, name="strategy_research_20260101_001.json", document=None):
        document = document if document is not None else {
            "schema_version": 2, "created_at": "2026-01-01T00:00:00Z",
            "summary": {"status": "RESEARCH", "candidate_count": 3},
            "batch_run_hash": "original-hash-not-resigned", "cells": [{"fixture": True}]}
        path = self.directory / name
        path.write_bytes(json.dumps(document, ensure_ascii=False, indent=2).encode())
        return path

    def inventory(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_original_file_identity_and_detail_retained_without_promotion(self):
        path = self.seed()
        (self.directory / "unrelated.json").write_text("{}")
        before = self.inventory()
        result = self.reader.reports()
        self.assertEqual(result["total_count"], 1)
        item = result["items"][0]
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(item["id"], expected)
        self.assertEqual(item["file_sha256"], expected)
        self.assertEqual(item["historical_schema"], 2)
        self.assertEqual(item["status"], "RESEARCH")
        self.assertEqual(item["original_report_validation"], "NOT_RUN")
        self.assertEqual(item["summary"]["candidate_count"], 3)
        self.assertNotIn("payload", item)
        for key in ("current", "replay_available", "paper_allowed", "live_allowed", "order_allowed"):
            self.assertFalse(item[key])
        self.assertTrue(item["read_only"])
        self.assertTrue(item["is_historical_file"])
        self.assertEqual(item["new_economic_runs"], 0)
        for identity in (expected, path.name):
            detail = self.reader.reports(identity)
            self.assertEqual(detail["payload"], json.loads(before["reports/" + path.name]))
            self.assertEqual(detail["file_sha256"], expected)
        self.assertEqual(before, self.inventory())
        self.assertFalse((self.directory / "current_strategy_research_report.json").exists())

    def test_modified_file_never_resolves_under_prior_hash(self):
        path = self.seed()
        prior_id = self.reader.reports()["items"][0]["id"]
        path.write_bytes(path.read_bytes() + b"\n")
        changed = path.read_bytes()
        with self.assertRaisesRegex(FileNotFoundError, "hash_not_found_or_changed"):
            self.reader.reports(prior_id)
        current = self.reader.reports()["items"][0]
        self.assertNotEqual(current["id"], prior_id)
        self.assertEqual(path.read_bytes(), changed)
        self.assertFalse(current["current"])

    def test_source_change_during_read_is_rejected(self):
        path = self.seed()
        original = self.reader._report_bytes
        calls = []
        def changing(target):
            raw, identity = original(target)
            calls.append(1)
            return (raw, identity) if len(calls) == 1 else (raw + b"\n", identity)
        with patch.object(self.reader, "_report_bytes", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "changed_during_read"):
                self.reader.reports(path.name)

    def test_paths_and_non_whitelisted_names_are_rejected(self):
        self.seed()
        for identity in ("../strategy_research_20260101_001.json", "C:/outside.json", ".env", "other.json",
                         "strategy_research_.json", "strategy_research_ok.json/extra", "page-1", "page-200", 1):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.reader.reports(identity)
        with self.assertRaises(FileNotFoundError):
            self.reader.reports("strategy_research_missing.json")

    def test_malformed_nonfinite_duplicate_and_nonobject_json_are_unavailable(self):
        for index, raw in enumerate((b"not JSON", b'{"x": NaN}', b'{"x": 1, "x": 2}', b"[]")):
            path = self.directory / ("strategy_research_invalid_" + str(index) + ".json")
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.reader.reports(path.name)
        before = self.inventory()
        result = self.reader.reports()
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total_count"], 4)
        self.assertEqual(len(result["warnings"]), 4)
        self.assertEqual(before, self.inventory())

    def test_oversize_and_nonregular_files_are_unavailable(self):
        path = self.seed()
        with patch.object(terminal_history, "_REPORT_MAX_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "too_large"):
                self.reader.reports(path.name)
        directory = self.directory / "strategy_research_directory.json"
        directory.mkdir()
        with self.assertRaisesRegex(ValueError, "not_regular_file"):
            self.reader.reports(directory.name)

    def test_symlink_and_windows_reparse_paths_are_rejected(self):
        path = self.seed()
        real_lstat = Path.lstat
        for mode, attributes in ((stat.S_IFLNK | 0o777, 0), (stat.S_IFREG | 0o644, 0x400)):
            def simulated_lstat(candidate, *args, **kwargs):
                if candidate == path:
                    return SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
                return real_lstat(candidate, *args, **kwargs)
            with self.subTest(attributes=attributes), patch.object(Path, "lstat", simulated_lstat):
                with self.assertRaisesRegex(ValueError, "reparse_path"):
                    self.reader.reports(path.name)

    def test_pagination_reports_total_and_scope_omissions_without_current_selection(self):
        for index in range(201):
            self.seed("strategy_research_%03d.json" % index, {"schema_version": 1, "summary": {"n": index}})
        first = self.reader.reports()
        self.assertEqual(first["total_count"], 201)
        self.assertEqual(first["scope_limit"], 200)
        self.assertEqual(first["omitted_by_scope"], 1)
        self.assertEqual(len(first["items"]), 50)
        self.assertEqual(first["next_page"], "page-50")
        self.assertEqual(first["items"][0]["file_name"], "strategy_research_000.json")
        second = self.reader.reports(first["next_page"])
        self.assertEqual(second["offset"], 50)
        self.assertEqual(second["items"][0]["file_name"], "strategy_research_050.json")
        last = self.reader.reports("page-150")
        self.assertIsNone(last["next_page"])
        self.assertFalse(last["current"])
        self.assertTrue(all(not item["current"] for item in first["items"] + second["items"] + last["items"]))
        self.assertEqual(self.reader.reports("strategy_research_200.json")["payload"]["summary"]["n"], 200)

    def test_list_summary_and_metadata_are_bounded_but_detail_payload_is_preserved(self):
        document = {"schema_version": {"nested": "not scalar"}, "created_at": "x" * 2000,
                    "status": "y" * 2000, "summary": {**{str(n): n for n in range(20)},
                    "nested": {"data": [0] * 1000}, "long": "z" * 5000}}
        path = self.seed(document=document)
        item = self.reader.reports()["items"][0]
        self.assertLessEqual(len(item["summary"]), 12)
        self.assertLessEqual(len(json.dumps(item["summary"]).encode()), 2048)
        self.assertTrue(item["summary_omitted"])
        self.assertTrue(item["summary_available_in_detail"])
        self.assertEqual(item["status"], "NOT_RECORDED")
        self.assertIsNone(item["created_at"])
        self.assertIsNone(item["historical_schema"])
        self.assertEqual(self.reader.reports(path.name)["payload"], document)

    def test_missing_report_directory_is_read_only(self):
        missing = self.root / "absent_runtime"
        reader = TerminalHistoryReader(missing)
        result = reader.reports()
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total_count"], 0)
        self.assertFalse(result["current"])
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
