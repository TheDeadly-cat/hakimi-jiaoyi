"""Offline behavioral acceptance; also executed against the installed wheel."""
import base64
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from hakimi_research.dataset_registry import (build_snapshot, import_capture, load_snapshot,
                                            save_snapshot, utc_text, verify_snapshot)
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, ResearchReport, replay_report, verify_report, required_context


def capture_fixture(count=180):
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    rows = []
    last = 100.0
    for index in range(count):
        close = 100 + 10 * math.sin(index / 6)
        rows.append([str(int((start + pd.Timedelta(hours=index)).timestamp() * 1000)),
                     str(last), str(max(last, close) + 1), str(min(last, close) - 1),
                     str(close), "100", str(close * 100), str(close * 100), "1"])
        last = close
    end = utc_text(start + pd.Timedelta(hours=count))
    return {"schema_version": "okx-public-capture-v1", "start": utc_text(start),
            "end_exclusive": end, "as_of": end, "evidence_kind": "SYNTHETIC_TEST",
            "pages": [{"raw_base64": base64.b64encode(canonical_bytes({"code": "0", "msg": "", "data": rows[::-1]})).decode(),
                       "endpoint": "/api/v5/market/history-candles", "origin": "https://www.okx.com",
                       "params": {"instId": "BTC-USDT", "bar": "1H", "limit": 300},
                       "retrieved_at": "2024-02-01T00:00:00Z"}]}


def snapshot_fixture(capture=None):
    capture = capture_fixture() if capture is None else capture
    return build_snapshot(capture["pages"], start=capture["start"], end=capture["end_exclusive"],
                          as_of=capture["as_of"], evidence_kind=capture["evidence_kind"])


def spec_fixture(snapshot):
    return {"schema_version": "research-experiment-spec-v1", "name": "offline-behavior",
            "snapshot_id": snapshot.snapshot_id, "strategy": {"name": "dual_ma", "params": {"fast_window": 5, "slow_window": 60}},
            "score_start": "2024-01-04T00:00:00Z", "score_end": "2024-01-08T12:00:00Z",
            "initial_cash": 10000, "fee_rate": 0.001, "slippage_pct": 0.0005,
            "risk": {"max_leverage": 1}, "end_policy": "MARK_TO_MARKET", "purpose": "SYNTHETIC_REGRESSION"}


def edit_rows(capture, transform):
    page = capture["pages"][0]
    payload = json.loads(base64.b64decode(page["raw_base64"]))
    transform(payload["data"])
    page["raw_base64"] = base64.b64encode(canonical_bytes(payload)).decode()


class DatasetAdmissionTests(unittest.TestCase):
    def test_request_cursor_and_raw_duplicate_binding(self):
        for key, cursor in [("after", 1), ("before", 9999999999999)]:
            capture = capture_fixture()
            capture["pages"][0]["params"][key] = cursor
            with self.assertRaisesRegex(ValueError, "cursor"):
                snapshot_fixture(capture)
        capture = capture_fixture()
        def duplicate_uncompleted(rows):
            row = list(rows[0])
            row[8] = "0"
            rows.append(row)
        edit_rows(capture, duplicate_uncompleted)
        with self.assertRaisesRegex(ValueError, "duplicate_raw"):
            snapshot_fixture(capture)

    def test_roundtrip_reparses_raw_bytes_and_detaches_frame(self):
        snapshot = snapshot_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(save_snapshot(snapshot, directory))
            before = path.read_bytes()
            frame = load_snapshot(path).frame()
            frame.iloc[0, 0] = 99999
            self.assertEqual(load_snapshot(path).document, snapshot.document)
            self.assertEqual(path.read_bytes(), before)

    def test_missing_duplicate_wrong_period_and_wrong_product_rejected(self):
        for transform in [lambda rows: rows.pop(0), lambda rows: rows.pop(-1), lambda rows: rows.pop(80),
                          lambda rows: rows.append(rows[5]),
                          lambda rows: rows[0].__setitem__(0, str(int(rows[0][0]) + 1000))]:
            capture = capture_fixture()
            edit_rows(capture, transform)
            with self.assertRaises(ValueError):
                snapshot_fixture(capture)
        for key, value in [("instId", "BTC-USDT-SWAP"), ("bar", "4H")]:
            capture = capture_fixture()
            capture["pages"][0]["params"][key] = value
            with self.assertRaises(ValueError):
                snapshot_fixture(capture)

    def test_uncompleted_in_requested_range_blocks_but_outside_is_recorded(self):
        capture = capture_fixture()
        edit_rows(capture, lambda rows: rows[0].__setitem__(8, "0"))
        with self.assertRaises(ValueError):
            snapshot_fixture(capture)
        capture["end_exclusive"] = "2024-01-08T11:00:00Z"
        snapshot = snapshot_fixture(capture)
        self.assertEqual(snapshot.document["quality"]["rejected_uncompleted_rows"], 1)

    def test_units_and_receipts_are_recomputed_and_tampering_fails(self):
        for field, value in [("volume_unit", "contracts"), ("data_hash", "f" * 64),
                             ("live_allowed", True), ("as_of", "2023-12-01T00:00:00Z")]:
            doc = copy.deepcopy(snapshot_fixture().document)
            doc[field] = value
            doc["snapshot_id"] = digest({k: v for k, v in doc.items() if k != "snapshot_id"})
            with self.assertRaises(ValueError):
                verify_snapshot(doc)

    def test_cutoff_retrieval_time_and_numeric_semantics(self):
        capture = capture_fixture()
        capture["pages"][0]["retrieved_at"] = "2024-01-01T01:00:00Z"
        with self.assertRaises(ValueError):
            snapshot_fixture(capture)
        for value in ["NaN", "-1", "infinity"]:
            capture = capture_fixture()
            edit_rows(capture, lambda rows: rows[0].__setitem__(6, value))
            with self.assertRaises(ValueError):
                snapshot_fixture(capture)

    def test_raw_byte_revision_creates_new_version_without_overwrite(self):
        capture = capture_fixture()
        first = snapshot_fixture(capture)
        page = capture["pages"][0]
        page["raw_base64"] = base64.b64encode(base64.b64decode(page["raw_base64"]) + b"\n").decode()
        second = snapshot_fixture(capture)
        self.assertEqual(first.document["data_hash"], second.document["data_hash"])
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)
        with tempfile.TemporaryDirectory() as directory:
            path1 = Path(save_snapshot(first, directory))
            raw1 = path1.read_bytes()
            path2 = Path(save_snapshot(second, directory))
            self.assertNotEqual(path1, path2)
            self.assertEqual(path1.read_bytes(), raw1)


class ExperimentAcceptanceTests(unittest.TestCase):
    def test_declared_context_matches_all_strategy_requirements(self):
        snapshot = snapshot_fixture()
        for strategy_name in ("dual_ma", "macd", "momentum", "rsi", "bollinger", "grid"):
            with self.subTest(strategy=strategy_name):
                spec = spec_fixture(snapshot)
                spec["strategy"] = {"name": strategy_name, "params": {}}
                warmup = required_context(strategy_name, {})
                spec["score_start"] = utc_text(pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(hours=warmup))
                report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec)).document
                first_signal = report["result"]["signals"][0]
                self.assertNotIn("not enough", first_signal["reason"].lower())
                spec["score_start"] = utc_text(pd.Timestamp("2024-01-01T00:00:00Z") + pd.Timedelta(hours=warmup-1))
                with self.assertRaisesRegex(ValueError, "insufficient_warmup"):
                    ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec))

    def test_missing_report_fields_and_contradictory_claims_rejected(self):
        snapshot = snapshot_fixture()
        original = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec_fixture(snapshot))).document
        for mutate in [lambda d: d.pop("limitations"),
                       lambda d: d["scoring_protocol"].__setitem__("confirmation_evaluation", True),
                       lambda d: d["evidence"].__setitem__("statistical_status", {"status": "SUFFICIENT"})]:
            doc = copy.deepcopy(original)
            mutate(doc)
            doc["report_hash"] = digest({key: value for key, value in doc.items() if key != "report_hash"})
            with self.assertRaises(ValueError):
                verify_report(doc)

    def test_unknown_source_does_not_become_verified_replay(self):
        snapshot = snapshot_fixture()
        original = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec_fixture(snapshot))).document
        source = {"status": "UNKNOWN", "content_sha256": ""}
        original["provenance"]["source_identity"] = source
        original["evidence"]["source_identity"] = source
        original["run_id"] = digest({"computation_id": original["computation_id"], "provenance": original["provenance"]})
        original["report_hash"] = digest({key: value for key, value in original.items() if key != "report_hash"})
        receipt = replay_report(snapshot, ResearchReport(original))
        self.assertFalse(receipt["source_matches"])
        self.assertFalse(receipt["replay_verified"])

    def test_formal_cash_and_buy_hold_share_core_and_explicit_policy(self):
        snapshot = snapshot_fixture()
        for name, params, policy in [("cash", {}, "STANDARD_STRATEGY_RISK"),
                                    ("buy_and_hold", {"target_position_pct": 1}, "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET")]:
            spec = spec_fixture(snapshot)
            spec["strategy"] = {"name": name, "params": params}
            spec["execution_policy"] = policy
            spec["risk"] = {"max_position_pct": 1, "min_cash_pct": 0, "max_leverage": 1}
            report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec)).document
            verify_report(report)
            result = report["result"]
            self.assertEqual(result["fill_count"], 0 if name == "cash" else 1)
            self.assertEqual(result["round_trip_count"], 0)
            self.assertEqual(result["sell_fees"], 0)
            self.assertFalse(report["strategy_spec"]["adding_to_position"])
            if name == "cash":
                self.assertEqual(result["total_return"], 0)
            else:
                self.assertGreater(result["buy_fees"], 0)
                self.assertGreater(result["open_position_qty"], 0)
                spec.pop("execution_policy")
                with self.assertRaisesRegex(ValueError, "policy"):
                    ExperimentSpec.from_document(spec)

    def test_fixed_snapshot_offline_replay_and_active_strategy(self):
        snapshot = snapshot_fixture()
        spec = ExperimentSpec.from_document(spec_fixture(snapshot))
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            report = ExperimentRunner().run(snapshot, spec)
            receipt = replay_report(snapshot, report)
        self.assertTrue(receipt["result_matches"])
        self.assertTrue(receipt["source_matches"])
        self.assertTrue(receipt["replay_verified"])
        self.assertGreater(report.document["result"]["fill_count"], 0)
        self.assertGreater(report.document["result"]["total_fees"], 0)
        self.assertEqual(report.document["scoring_protocol"]["required_context_rows"], 62)
        self.assertFalse(report.document["scoring_protocol"]["warmup_trading"])
        self.assertFalse(report.document["execution_permission"]["live_allowed"])

    def test_long_window_requires_context_not_fixed_thirty_rows(self):
        snapshot = snapshot_fixture()
        spec = spec_fixture(snapshot)
        spec["score_start"] = "2024-01-02T06:00:00Z"
        with self.assertRaisesRegex(ValueError, "insufficient_warmup"):
            ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec))

    def test_rejects_snapshot_alias_leverage_silent_parameters_and_confirmation(self):
        snapshot = snapshot_fixture()
        for mutate in [lambda s: s.__setitem__("snapshot_id", "f" * 64),
                       lambda s: s["risk"].__setitem__("max_leverage", 2),
                       lambda s: s["strategy"]["params"].__setitem__("slow_widnow", 20),
                       lambda s: s.__setitem__("purpose", "FORMAL_CONFIRMATION")]:
            spec = spec_fixture(snapshot)
            mutate(spec)
            with self.assertRaises(ValueError):
                ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec))

    def test_future_mutation_does_not_change_earlier_decisions(self):
        capture = capture_fixture()
        first = snapshot_fixture(capture)
        report1 = ExperimentRunner().run(first, ExperimentSpec.from_document(spec_fixture(first))).document
        def change(rows):
            for row in rows[:30]:
                row[1:5] = ["130", "135", "125", "131"]
        edit_rows(capture, change)
        second = snapshot_fixture(capture)
        report2 = ExperimentRunner().run(second, ExperimentSpec.from_document(spec_fixture(second))).document
        # Signals are ordered; first 70 are entirely before the changed final 30 bars.
        self.assertEqual(report1["result"]["signals"][:70], report2["result"]["signals"][:70])
        self.assertEqual(report1["result"]["equity_curve"][:70], report2["result"]["equity_curve"][:70])

    def test_report_integrity_and_read_consumer_has_no_side_effects(self):
        snapshot = snapshot_fixture()
        report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec_fixture(snapshot)))
        with tempfile.TemporaryDirectory() as directory:
            path = report.save(directory)
            before = path.read_bytes()
            output_dir = Path(directory) / "must-not-exist"
            process = subprocess.run([sys.executable, "-B", "-m", "hakimi_research", "report-show", "--report", str(path),
                                      "--output-dir", str(output_dir)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(output_dir.exists())
        tampered = copy.deepcopy(report.document)
        tampered["result"]["final_equity"] += 1
        with self.assertRaises(ValueError):
            verify_report(tampered)

    def test_full_cli_capture_to_report_to_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = capture_fixture()
            capture_path = root / "capture.json"
            capture_path.write_bytes(canonical_bytes(capture))
            def cli(*arguments):
                completed = subprocess.run([sys.executable, "-B", "-m", "hakimi_research", *arguments,
                                             "--output-dir", str(root / "output")], capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                return json.loads(completed.stdout)
            imported = cli("snapshot-import", "--capture", str(capture_path))
            snapshot = load_snapshot(imported["snapshot"])
            spec_path = root / "spec.json"
            spec_path.write_bytes(canonical_bytes(spec_fixture(snapshot)))
            report = cli("research", "--snapshot", imported["snapshot"], "--spec", str(spec_path))
            original_bytes = Path(report["full_report"]).read_bytes()
            replay = cli("replay", "--snapshot", imported["snapshot"], "--report", report["full_report"])
            self.assertTrue(replay["replay_verified"])
            self.assertEqual(Path(report["full_report"]).read_bytes(), original_bytes)
            self.assertTrue(Path(replay["receipt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
