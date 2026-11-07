"""Fictional offline fixtures, never actual market evidence or source approval.

The ordinary-import branch deliberately models IMPORTED_UNVERIFIED to exercise
the real canonical and native validators. SYNTHETIC_TEST is separately blocked.
No strategy runner, provider, existing workspace, or frozen source is used.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import base64
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from hakimi_research.equity_dataset import build_equity_snapshot, verify_equity_snapshot
from hakimi_research.input_workflow import _retain
from exchange_terminal.services.terminal_daily_bridge import build_native_daily_input, verify_native_daily_input
from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from exchange_terminal.services.terminal_research import _bytes, _seal, _core_input_adapter


def fixture(*, marked_synthetic=False, mutate=None, additional_closed_date=None):
    """New in-memory QA declaration, with actual session shapes but fake prices."""
    first, last = date(2024, 10, 21), date(2024, 12, 3)
    days, prices = [], ["session_date,open,high,low,close,volume"]
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day.weekday() >= 5 or day == date(2024, 11, 28) or day == additional_closed_date:
            days.append({"date": day.isoformat(), "kind": "CLOSED", "reason": "WEEKEND" if day.weekday() >= 5 else "HOLIDAY"})
            continue
        early = day == date(2024, 11, 29)
        def stamp(hour, minute=0):
            return datetime.combine(day, time(hour, minute), ZoneInfo("America/New_York")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        days.append({"date": day.isoformat(), "kind": "OPEN", "open_utc": stamp(9, 30), "close_utc": stamp(13 if early else 16), "early_close": early})
        opening = 100 + offset / 4
        prices.append(f"{day},{opening},{opening + 2},{opening - 1},{opening + .5},{1000 + offset}")
    raw_csv = ("\n".join(prices) + "\n").encode()
    declaration = b"FICTIONAL QA ONLY: fabricated ordinary-import declaration, not actual market evidence or authenticated source."
    def source(name, content):
        return {"name": ("SYNTHETIC_TEST " if marked_synthetic else "QA simulated ordinary import ") + name,
                "reference": "urn:hakimi:qa:daily-bridge:" + name, "retrieved_at": "2024-12-10T00:00:00Z",
                "raw_base64": base64.b64encode(content).decode()}
    manifest = {"schema_version": "us-equity-daily-import-v1",
        "security": {"security_id": "QA:DAILY:COMMON_STOCK", "symbol": "QADEMO", "exchange": "XNYS", "currency": "USD", "instrument_type": "COMMON_STOCK"},
        "identity": {"stable_within_coverage": True, "valid_from": str(first), "valid_through": str(last), "selection_basis": declaration.decode(), "source": source("identity", declaration)},
        "calendar": {"timezone": "America/New_York", "coverage_start": str(first), "coverage_end": str(last), "source": source("calendar", json.dumps(days).encode()), "days": days},
        "corporate_actions": {"coverage_start": str(first), "coverage_end": str(last), "coverage_status": "DECLARED_COMPLETE", "source": source("actions", declaration), "actions": []},
        "price_source": source("provider", raw_csv), "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares", "bar_timestamp_semantics": "SESSION_DATE", "completed_bars_only": True,
        "as_of": "2024-12-09T00:00:00Z", "retrieved_at": "2024-12-10T00:00:00Z", "bar_availability_lag_seconds": 60,
        "evidence_kind": "SYNTHETIC_TEST" if marked_synthetic else "IMPORTED_UNVERIFIED"}
    if mutate:
        mutate(manifest)
    snapshot = build_equity_snapshot(raw_csv, manifest).document
    # Preserve visibly noncanonical original document encoding.
    raw = (json.dumps(snapshot, ensure_ascii=False, indent=3) + "\n").encode("utf-8")
    relative = "data/snapshots/" + snapshot["snapshot_id"] + "/" + sha256(raw).hexdigest() + ".json"
    identity = "canon-" + sha256(relative.encode()).hexdigest()[:32]
    return raw, snapshot, identity


def reseal(record):
    return _seal({key: value for key, value in record.items() if key != "id"})


def hashes(root):
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}


class TerminalDailyBridgeTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("socket.socket.connect", side_effect=AssertionError("No external network in bridge tests")).start()
        self.runner = patch("exchange_terminal.services.backtest_engine.run_causal_long_only_backtest", side_effect=AssertionError("No economic runner in bridge tests")).start()
        self.addCleanup(patch.stopall)

    def test_receipt_retains_all_data_and_original_meta_with_independent_namespace(self):
        raw, snapshot, identity = fixture()
        before = _bytes(snapshot)
        record = build_native_daily_input(raw, verify_equity_snapshot(snapshot), identity)
        self.assertEqual(record["quality"]["status"], "REVIEW", record["quality"]["blockers"])
        self.assertEqual(verify_native_daily_input(record, raw), record)
        self.assertNotEqual(record["id"], snapshot["snapshot_id"])
        self.assertRegex(record["id"], "^[a-f0-9]{64}$")
        self.assertNotIn("core_reference", record)
        self.assertFalse(any(key.startswith("core_") for key in record["meta"]))
        self.assertTrue(record["source_id"].startswith("daily-canonical-price-snapshot:"))
        self.assertEqual(record["meta"]["source_namespace"], "canonical-daily-v1")
        self.assertEqual(record["daily_reference"]["canonical_input_id"], identity)
        self.assertEqual(record["daily_reference"]["file_sha256"], sha256(raw).hexdigest())
        self.assertEqual(record["daily_reference"]["original_byte_count"], len(raw))
        self.assertFalse(record["daily_reference"]["original_rewritten"])
        self.assertFalse(record["quality"]["source_authenticated"])
        self.assertFalse(record["quality"]["frozen_core_import_allowed"])
        self.assertFalse(record["permissions"]["live_order_allowed"])
        self.assertFalse(record["permissions"]["paper_allowed"])
        original = _core_input_adapter(snapshot, "a" * 24, sha256(raw).hexdigest())
        self.assertEqual(record["rows"], original["rows"])
        for key, value in original["meta"].items():
            name = {"core_snapshot_id": "daily_snapshot_id", "core_research_admission": "daily_research_admission"}.get(key, key)
            self.assertEqual(record["meta"][name], value, key)
        self.assertEqual(_bytes(snapshot), before)
        self.runner.assert_not_called()
        self.network.assert_not_called()

    def test_real_current_retain_layout_roundtrip_preserves_exact_original_bytes_and_no_other_writes(self):
        raw, snapshot, expected_id = fixture()
        with tempfile.TemporaryDirectory(prefix="hakimi-daily-bridge-qa-") as directory:
            root = Path(directory)
            retained = _retain(root / "daily", raw)
            reader = TerminalDailyResearch(root)
            item = reader.read("terminal_daily_inputs")["items"][0]
            self.assertEqual(item["id"], expected_id)
            read_raw, read_snapshot = reader.verified_input(item["id"])
            before = hashes(root)
            record = build_native_daily_input(read_raw, read_snapshot, item["id"])
            verify_native_daily_input(record, read_raw)
            self.assertEqual(hashes(root), before)
            original = root / record["daily_reference"]["original_bytes_path"]
            original.parent.mkdir(parents=True)
            original.write_bytes(raw)
            receipt = root / "terminal-inputs" / (record["id"] + ".json")
            receipt.write_bytes(_bytes(record))
            self.assertEqual(original.read_bytes(), raw)
            # A current-source deletion cannot remove retained receipt evidence.
            Path(retained["path"]).unlink()
            self.assertEqual(verify_native_daily_input(json.loads(receipt.read_bytes()), original.read_bytes()), record)
            self.assertFalse((root / "data").exists())
            self.assertFalse((root / "tasks").exists())
            self.assertFalse((root / "runs").exists())

    def test_core_ids_arbitrary_canonical_ids_and_renamed_storage_are_explicitly_rejected(self):
        raw, snapshot, _ = fixture()
        renamed = "canon-" + sha256(b"data/manually-renamed.json").hexdigest()[:32]
        for identity in ("a" * 24, snapshot["snapshot_id"], "canon-" + "f" * 32, renamed, "../input.json", None):
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, "当前股票日线资料的保存流程"):
                build_native_daily_input(raw, snapshot, identity)

    def test_resealed_canonical_id_reference_and_meta_drift_do_not_pass(self):
        raw, snapshot, identity = fixture()
        record = build_native_daily_input(raw, snapshot, identity)
        changes = [
            lambda value: value["daily_reference"].update(canonical_input_id="canon-" + "f" * 32),
            lambda value: value["daily_reference"].update(original_bytes_path="terminal-inputs/core-originals/other.json"),
            lambda value: value["daily_reference"].update(canonical_storage_ref="data/arbitrary.json"),
            lambda value: value["daily_reference"].update(snapshot_hash="f" * 64),
            lambda value: value["daily_reference"].update(file_sha256="f" * 64),
            lambda value: value["daily_reference"].update(source_manifest_hash="f" * 64),
            lambda value: value["daily_reference"].update(csv_sha256="f" * 64),
            lambda value: value["daily_reference"].update(original_rewritten=0),
            lambda value: value["daily_reference"].update(verifier="hakimi_terminal_research.equity_dataset.verify_equity_snapshot"),
            lambda value: value["meta"].update(daily_research_admission={"allowed": True}),
            lambda value: value["rows"][0].update(close=999),
            lambda value: value["quality"].update(source_authenticated=True),
            lambda value: value["permissions"].update(live_allowed=True),
        ]
        for index, change in enumerate(changes):
            altered = deepcopy(record)
            change(altered)
            with self.subTest(index=index), self.assertRaises(ValueError):
                verify_native_daily_input(reseal(altered), raw)

    def test_ambiguous_core_and_daily_references_are_rejected_even_null_or_resealed(self):
        raw, snapshot, identity = fixture()
        record = build_native_daily_input(raw, snapshot, identity)
        for reference in (None, {}, {"core_input_id": "a" * 24}):
            with self.subTest(reference=reference), self.assertRaisesRegex(ValueError, "ambiguous"):
                verify_native_daily_input(reseal({**record, "core_reference": reference}), raw)

    def test_original_byte_encoding_change_and_different_supplied_snapshot_are_rejected(self):
        raw, snapshot, identity = fixture()
        record = build_native_daily_input(raw, snapshot, identity)
        with self.assertRaisesRegex(ValueError, "saved_layout_required"):
            verify_native_daily_input(record, raw + b" ")
        _, other, _ = fixture(mutate=lambda manifest: manifest["identity"].update(selection_basis="Another fictional QA declaration"))
        with self.assertRaisesRegex(ValueError, "raw_snapshot_identity_conflict"):
            build_native_daily_input(raw, other, identity)
        for data in (b'{}', b'{"schema_version":1,"schema_version":2}', raw.decode(), bytearray(raw)):
            with self.subTest(kind=type(data)), self.assertRaises((ValueError, TypeError)):
                build_native_daily_input(data, snapshot, identity)

    def test_synthetic_and_preview_admission_is_visible_but_not_persistable(self):
        cases = [dict(marked_synthetic=True),
            dict(mutate=lambda m: m.update(evidence_kind="SYNTHETIC_TEST")),
            dict(mutate=lambda m: m["price_source"].update(reference="urn:local:preview_seed:prices")),
            dict(mutate=lambda m: m["price_source"].update(name="offline-seed")),
            dict(mutate=lambda m: m["security"].update(security_id="SYNTHETIC:QA")),
            dict(mutate=lambda m: m["calendar"]["source"].update(name="test_fixture calendar"))]
        for index, options in enumerate(cases):
            raw, snapshot, identity = fixture(**options)
            record = build_native_daily_input(raw, snapshot, identity)
            with self.subTest(index=index):
                self.assertEqual(record["quality"]["status"], "BLOCK")
                self.assertTrue(any("synthetic" in reason for reason in record["quality"]["blockers"]))
                with self.assertRaisesRegex(ValueError, "daily_input_blocked"):
                    verify_native_daily_input(record, raw)

    def test_corporate_actions_identity_and_causal_availability_remain_blocked(self):
        def action(manifest):
            manifest["corporate_actions"]["actions"] = [{"action_id": "qa-action", "security_id": manifest["security"]["security_id"],
                "action_type": "SPLIT", "effective_date": "2024-11-01", "source_reference": "urn:qa:action", "details": {"numerator": 2, "denominator": 1}}]
        cases = [(action, "CORPORATE_ACTION_ACCOUNTING"),
            (lambda m: m["corporate_actions"].update(coverage_status="UNKNOWN"), "CORPORATE_ACTION_COVERAGE"),
            (lambda m: m["identity"].update(stable_within_coverage=False), "SECURITY_IDENTITY_NOT_STABLE"),
            (lambda m: m.update(bar_availability_lag_seconds=24 * 3600), "daily_bar_unavailable_before_next_open")]
        for mutate, marker in cases:
            raw, snapshot, identity = fixture(mutate=mutate)
            record = build_native_daily_input(raw, snapshot, identity)
            with self.subTest(marker=marker):
                self.assertEqual(record["quality"]["status"], "BLOCK")
                self.assertTrue(any(marker in reason for reason in record["quality"]["blockers"]))
                with self.assertRaisesRegex(ValueError, marker):
                    verify_native_daily_input(record, raw)
                altered = deepcopy(record)
                altered["quality"].update(status="REVIEW", blockers=[])
                with self.assertRaisesRegex(ValueError, "reference_changed"):
                    verify_native_daily_input(reseal(altered), raw)

    def test_canonical_verifier_rejects_resealed_price_session_manifest_and_action_aware_schema(self):
        raw, snapshot, identity = fixture()
        changes = [lambda doc: doc["candles"][0].__setitem__(1, 200),
            lambda doc: doc["sessions"][0].update(open_utc="2024-10-21T14:30:00Z"),
            lambda doc: doc["raw_input"].update(manifest_sha256="f" * 64),
            lambda doc: doc.update(schema_version="us-equity-action-aware-snapshot-v1")]
        for index, change in enumerate(changes):
            altered = deepcopy(snapshot)
            change(altered)
            with self.subTest(index=index), self.assertRaises(ValueError):
                build_native_daily_input(json.dumps(altered).encode(), altered, identity)
        self.runner.assert_not_called()
        self.network.assert_not_called()

    def test_native_calendar_admission_still_blocks_a_canonical_importer_declaration(self):
        # Canonical identity verification can preserve an importer's incorrect
        # holiday declaration; native admission must still check its calendar.
        raw, snapshot, identity = fixture(additional_closed_date=date(2024, 10, 22))
        self.assertTrue(verify_equity_snapshot(snapshot)["research_admission"]["allowed"])
        record = build_native_daily_input(raw, snapshot, identity)
        self.assertEqual(record["quality"]["status"], "BLOCK")
        self.assertTrue(any(reason.startswith("native_data:market_calendar:") for reason in record["quality"]["blockers"]), record["quality"]["blockers"])
        with self.assertRaisesRegex(ValueError, "native_data:market_calendar:"):
            verify_native_daily_input(record, raw)


if __name__ == "__main__":
    unittest.main()
