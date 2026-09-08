"""Version lineage and CSV admission behavior; no network or provider calls."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from hakimi_research.dataset_registry import (
    build_csv_snapshot, build_snapshot, import_capture, import_csv,
    load_snapshot, save_snapshot, verify_lineage, verify_snapshot,
)
from hakimi_research.documents import canonical_bytes
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, replay_report
from test_experiment_runner import capture_fixture, edit_rows, snapshot_fixture


def csv_fixture():
    raw = b"time,open,high,low,close,volume\n2024-01-01T00:00:00Z,100,102,99,101,10\n2024-01-01T01:00:00Z,101,103,100,102,12\n2024-01-01T02:00:00Z,102,104,101,103,15\n"
    metadata = {"market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT",
                "timeframe": "1h", "source": "synthetic CSV fixture for software admission tests",
                "retrieved_at": "2024-01-02T00:00:00Z", "as_of": "2024-01-01T03:00:00Z",
                "volume_unit": "base_currency", "quote_unit": "USDT", "timezone": "UTC",
                "start": "2024-01-01T00:00:00Z", "end_exclusive": "2024-01-01T03:00:00Z",
                "completed_bars_only": True}
    return raw, metadata


class DatasetVersionTests(unittest.TestCase):
    def test_preserved_v1_fixture_and_explicit_v2_successor(self):
        # This fixture was produced by the preserved 0.1.0 wheel, independently
        # of the new v2 implementation. Its old identity is never regenerated.
        path = Path(__file__).parent / "fixtures/dataset_snapshot_v1.json"
        before = path.read_bytes()
        original = load_snapshot(path)
        self.assertEqual(original.snapshot_id, "563be4e0bb536df2f88cfce8cc33bb207e616aa7d85d8fd306196cdcffcc34a1")
        self.assertEqual(original.document["dataset_id"], "okx-btc-usdt-spot-1h")
        successor = build_snapshot(original.document["pages"], start=original.document["start"],
                                   end=original.document["end_exclusive"], as_of=original.document["as_of"],
                                   evidence_kind=original.document["evidence_kind"], predecessor=original)
        self.assertEqual(successor.document["schema_version"], "research-dataset-snapshot-v2")
        self.assertNotEqual(successor.document["dataset_id"], original.document["dataset_id"])
        self.assertEqual(successor.document["data_hash"], original.document["data_hash"])
        self.assertEqual(verify_lineage(successor, original)["status"], "VERIFIED")
        self.assertEqual(path.read_bytes(), before)

    def test_raw_revision_changes_dataset_version_with_validated_parent(self):
        capture = capture_fixture(4)
        first = snapshot_fixture(capture)
        page = capture["pages"][0]
        page["raw_base64"] = base64.b64encode(base64.b64decode(page["raw_base64"]) + b"\n").decode()
        second = build_snapshot(capture["pages"], start=capture["start"], end=capture["end_exclusive"],
                                as_of=capture["as_of"], evidence_kind=capture["evidence_kind"], predecessor=first)
        self.assertEqual(first.document["data_hash"], second.document["data_hash"])
        self.assertNotEqual(first.document["dataset_id"], second.document["dataset_id"])
        self.assertEqual(first.document["dataset_series_id"], second.document["dataset_series_id"])
        self.assertEqual(second.document["lineage"]["previous_snapshot_id"], first.snapshot_id)
        self.assertEqual(second.document["lineage_status"], "RECORDED_REFERENCE")
        self.assertNotIn("parent_snapshot", second.document["lineage"])
        self.assertEqual(verify_lineage(second, first)["status"], "VERIFIED")
        with tempfile.TemporaryDirectory() as folder:
            old_path = Path(save_snapshot(first, folder))
            old_bytes = old_path.read_bytes()
            new_path = Path(save_snapshot(second, folder))
            self.assertNotEqual(old_path, new_path)
            self.assertEqual(old_path.read_bytes(), old_bytes)
            self.assertEqual(load_snapshot(new_path).document, second.document)

    def test_predecessor_must_verify_and_match_series_and_reference(self):
        old = snapshot_fixture(capture_fixture(4))
        tampered = copy.deepcopy(old.document)
        tampered["candles"][0][1] += 1
        capture = capture_fixture(4)
        with self.assertRaises(ValueError):
            build_snapshot(capture["pages"], start=capture["start"], end=capture["end_exclusive"],
                           as_of=capture["as_of"], predecessor=tampered)
        raw, metadata = csv_fixture()
        with self.assertRaisesRegex(ValueError, "series_mismatch"):
            build_csv_snapshot(raw, metadata, predecessor=old)
        unrelated = snapshot_fixture(capture_fixture(5))
        child = build_snapshot(capture["pages"], start=capture["start"], end=capture["end_exclusive"],
                               as_of=capture["as_of"], evidence_kind=capture["evidence_kind"], predecessor=old)
        with self.assertRaisesRegex(ValueError, "link_mismatch"):
            verify_lineage(child, unrelated)

    def test_missing_duplicate_and_order_diagnostics_locate_source(self):
        capture = capture_fixture(4)
        edit_rows(capture, lambda rows: rows.pop(1))
        with self.assertRaisesRegex(ValueError, "missing=1:timestamps=2024-01-01T02:00:00Z"):
            snapshot_fixture(capture)
        capture = capture_fixture(4)
        edit_rows(capture, lambda rows: rows.append(rows[1]))
        with self.assertRaisesRegex(ValueError, "duplicate_raw_timestamp:timestamp=2024-01-01T02:00:00Z:page=0:row=4:first_page=0:first_row=1"):
            snapshot_fixture(capture)
        capture = capture_fixture(4)
        edit_rows(capture, lambda rows: rows.reverse())
        with self.assertRaisesRegex(ValueError, "order_invalid.*page=0:row=1"):
            snapshot_fixture(capture)


class CSVAdmissionTests(unittest.TestCase):
    def test_csv_snapshot_runs_and_replays_with_declared_import_limitations(self):
        raw, metadata = csv_fixture()
        snapshot = build_csv_snapshot(raw, metadata)
        spec = {"schema_version": "research-experiment-spec-v1", "name": "csv-software-regression",
                "snapshot_id": snapshot.snapshot_id, "strategy": {"name": "cash", "params": {}},
                "score_start": "2024-01-01T01:00:00Z", "score_end": metadata["end_exclusive"],
                "initial_cash": 10000, "fee_rate": 0.001, "slippage_pct": 0,
                "risk": {"max_leverage": 1}, "end_policy": "MARK_TO_MARKET", "purpose": "SYNTHETIC_REGRESSION"}
        report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec))
        self.assertEqual(report.document["result"]["fill_count"], 0)
        self.assertEqual(report.document["dataset"]["source_authentication"], "IMPORTER_DECLARATION_NOT_VERIFIED")
        self.assertEqual(report.document["evidence"]["data_scope"]["evidence_kind"], "IMPORTED_UNVERIFIED")
        self.assertEqual(report.document["dataset"]["quality"]["completion_basis"], "IMPORTER_DECLARATION_ONLY")
        self.assertTrue(replay_report(snapshot, report)["replay_verified"])

    def test_csv_raw_and_normalized_identity_with_explicit_unverified_scope(self):
        raw, metadata = csv_fixture()
        snapshot = build_csv_snapshot(raw, metadata)
        document = snapshot.document
        self.assertEqual(document["source_format"], "CSV")
        self.assertEqual(document["evidence_kind"], "IMPORTED_UNVERIFIED")
        self.assertEqual(document["source_authentication"], "IMPORTER_DECLARATION_NOT_VERIFIED")
        self.assertEqual(document["source_receipts"][0]["raw_csv_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(document["source_receipts"][0]["normalized_sha256"], document["data_hash"])
        self.assertEqual(document["pages"], [])
        self.assertEqual(document["quality"]["completion_basis"], "IMPORTER_DECLARATION_ONLY")
        self.assertNotIn("endpoint", document["source_receipts"][0])
        self.assertEqual(verify_snapshot(document), document)
        changed = snapshot.frame()
        changed.iloc[0, 0] = 9999
        self.assertEqual(snapshot.frame().iloc[0, 0], 100)

    def test_every_metadata_field_and_supported_units_are_required(self):
        raw, metadata = csv_fixture()
        for field in metadata:
            altered = dict(metadata)
            altered.pop(field)
            with self.subTest(missing=field), self.assertRaisesRegex(ValueError, "metadata_required"):
                build_csv_snapshot(raw, altered)
        for field, value in (("volume_unit", "contracts"), ("market", "crypto_derivatives"),
                             ("symbol", "BTC-USDT-SWAP"), ("timeframe", "4h"),
                             ("timezone", "local"), ("completed_bars_only", False), ("source", "")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_csv_snapshot(raw, {**metadata, field: value})

    def test_csv_missing_duplicate_wrong_order_and_geometry_are_locatable(self):
        raw, metadata = csv_fixture()
        lines = raw.decode().splitlines()
        cases = [
            ("\n".join([lines[0], lines[1], lines[3]]) + "\n", "missing=1:timestamps=2024-01-01T01:00:00Z"),
            ("\n".join(lines + [lines[2]]) + "\n", "duplicate_timestamp:timestamp=2024-01-01T01:00:00Z:row=5:first_row=3"),
            ("\n".join([lines[0], lines[2], lines[1], lines[3]]) + "\n", "order_invalid.*row=3"),
            (raw.decode().replace(",100,102,99,101,10", ",100,90,99,101,10"), "geometry_invalid.*row=2"),
            (raw.decode().replace(",100,102,99,101,10", ",NaN,102,99,101,10"), "numeric_invalid:row=2"),
            (raw.decode().replace("00:00:00Z", "00:30:00Z", 1), "timestamp_invalid:row=2"),
        ]
        for content, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                build_csv_snapshot(content.encode(), metadata)

    def test_cutoff_and_retrieval_declarations_are_not_silently_relabelled(self):
        raw, metadata = csv_fixture()
        with self.assertRaisesRegex(ValueError, "range_or_cutoff"):
            build_csv_snapshot(raw, {**metadata, "as_of": "2024-01-01T02:00:00Z"})
        with self.assertRaisesRegex(ValueError, "cutoff_after_retrieval"):
            build_csv_snapshot(raw, {**metadata, "retrieved_at": "2024-01-01T02:00:00Z"})
        changed = build_csv_snapshot(raw, {**metadata, "source": "another declared source"})
        self.assertNotEqual(changed.document["dataset_id"], build_csv_snapshot(raw, metadata).document["dataset_id"])

    def test_path_and_capture_imports_match_and_revision_is_immutable(self):
        raw, metadata = csv_fixture()
        with tempfile.TemporaryDirectory(prefix="CSV 中文 path ") as folder:
            folder = Path(folder)
            csv_path, metadata_path, capture_path = folder / "行情 CSV.csv", folder / "metadata.json", folder / "capture.json"
            csv_path.write_bytes(raw)
            metadata_path.write_bytes(canonical_bytes(metadata))
            capture_path.write_bytes(canonical_bytes({"schema_version": "csv-ohlcv-capture-v1", "raw_base64": base64.b64encode(raw).decode(), "metadata": metadata}))
            first = import_csv(csv_path, metadata_path)
            self.assertEqual(first.document, import_capture(capture_path).document)
            revision = build_csv_snapshot(raw.replace(b",101,10\n", b",101.0,10.0\n", 1), metadata, predecessor=first)
            self.assertEqual(first.document["data_hash"], revision.document["data_hash"])
            self.assertNotEqual(first.document["dataset_id"], revision.document["dataset_id"])
            self.assertEqual(verify_lineage(revision, first)["status"], "VERIFIED")
            path = save_snapshot(first, folder / "artifacts")
            original = Path(path).read_bytes()
            save_snapshot(revision, folder / "artifacts")
            self.assertEqual(Path(path).read_bytes(), original)

    def test_cli_csv_import_and_predecessor_use_same_offline_contract(self):
        raw, metadata = csv_fixture()
        with tempfile.TemporaryDirectory(prefix="CSV CLI 中文 path ") as folder:
            folder = Path(folder)
            csv_path, metadata_path = folder / "行情 CSV.csv", folder / "metadata.json"
            csv_path.write_bytes(raw)
            metadata_path.write_bytes(canonical_bytes(metadata))
            env = dict(os.environ)
            env["PYTHONUTF8"], env["PYTHONIOENCODING"] = "1", "utf-8"
            command = [sys.executable, "-m", "hakimi_research", "snapshot-import", "--csv", str(csv_path),
                       "--metadata", str(metadata_path), "--output-dir", str(folder / "数据 output")]
            first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            result = json.loads(first.stdout)
            original_path = Path(result["snapshot"])
            original_bytes = original_path.read_bytes()
            csv_path.write_bytes(raw.replace(b",101,10\n", b",101.0,10.0\n", 1))
            revision = subprocess.run(command + ["--predecessor", str(original_path)], capture_output=True,
                                      text=True, encoding="utf-8", env=env)
            self.assertEqual(revision.returncode, 0, revision.stderr + revision.stdout)
            revised = load_snapshot(json.loads(revision.stdout)["snapshot"])
            self.assertEqual(verify_lineage(revised, load_snapshot(original_path))["status"], "VERIFIED")
            self.assertEqual(original_path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
