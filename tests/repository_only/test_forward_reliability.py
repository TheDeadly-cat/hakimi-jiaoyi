"""Offline contracts for the scheduler sidecar, using local files and stubs only."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools/forward_reliability.py"
SPEC = importlib.util.spec_from_file_location("forward_reliability_tested", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
PLAN_PATH = Path(__file__).resolve().parents[2] / "docs/studies/forward-reliability-plan-20260906.json"


class ForwardReliabilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.receipts = self.root / "forward/reliability"
        self.plan = module.load_plan(PLAN_PATH)
        self.cutoff = module.timestamp(self.plan["start_cutoff"])
        self.clock = self.cutoff + timedelta(minutes=2)
        for context in (patch.object(module, "now", side_effect=lambda: self.clock),
                        patch.object(module, "verify_runtime", return_value={"test_stub": True})):
            context.start()
            self.addCleanup(context.stop)

    def record(self, item, cutoff=None, delay=120, backfill=False):
        cutoff = cutoff or self.cutoff
        available = cutoff + timedelta(seconds=delay)
        inputs = {"input_available_at": module.stamp(cutoff + timedelta(seconds=min(delay, 100))),
                  "snapshot_id": "a" * 64}
        signal = {"action": "HOLD"}
        record = {"schema_version": "forward-observation-v1", "plan_hash": item["plan_hash"],
                  "cutoff": module.stamp(cutoff), "signal_available_at": module.stamp(available),
                  "recorded_at_utc": module.stamp(available), "input": inputs,
                  "input_hash": module.digest(inputs), "signal": signal, "output_hash": module.digest(signal),
                  "backfill": backfill, "timing_status": "BACKFILL" if backfill else "ON_TIME" if delay <= 300 else "LATE",
                  "lateness_seconds": float(delay), "state_policy": "FLAT_REFERENCE_OBSERVATION",
                  "source_sha256": self.plan["source_sha256"], "environment_sha256": self.plan["environment_sha256"],
                  "position_state_observed": False,
                  "execution_permission": {"research_only": True, "paper_allowed": False,
                                           "live_allowed": False, "order_allowed": False}}
        return module.seal(record, "record_hash")

    def projection(self, item, cutoff=None, delay=120, backfill=False):
        record = self.record(item, cutoff, delay, backfill)
        path = self.root / (record["record_hash"] + ".json")
        module.write_new(path, record)
        return module._record_projection(path, record, item, self.plan)

    def child(self, *, fail=False):
        if fail:
            return SimpleNamespace(returncode=3, stdout="", stderr="local stub failure")
        hour = module._hour(self.root, self.cutoff)
        records = []
        for item in self.plan["plans"]:
            record = self.record(item)
            path = hour / "observations" / (item["strategy"] + ".json")
            if not path.exists():
                module.write_new(path, record)
            records.append({"plan_hash": item["plan_hash"], "record": str(path), "record_hash": record["record_hash"]})
        cycle = {"status": "RECORDED_AND_REPLAYED", "cutoff": module.stamp(self.cutoff),
                 "observations": 2, "replays_verified": 2, "order_allowed": False,
                 "automatic_backfill": False, "records": records, "prior_absences": []}
        if not (hour / "forward_cycle_fixed.json").exists():
            module.write_new(hour / "forward_cycle_fixed.json", cycle)
        return SimpleNamespace(returncode=0, stdout=json.dumps(cycle), stderr="")

    def run_wrapper(self):
        return module.run(self.root, self.plan, self.receipts, trigger_kind="SCHEDULED",
                          trigger_at=module.stamp(self.cutoff + timedelta(minutes=1)))

    def test_actual_execution_receipt_and_idempotent_duplicate_preserve_original_bytes(self):
        with patch.object(module, "_execute", side_effect=lambda root: self.child()) as child:
            first = self.run_wrapper()
            originals = module._originals(self.root, self.cutoff)
            self.clock += timedelta(seconds=30)
            second = self.run_wrapper()
        self.assertEqual(child.call_count, 2)  # duplicate replays using the unchanged child
        self.assertEqual(first["classification"], "FIRST_ATTEMPT")
        self.assertEqual(second["classification"], "DUPLICATE_VERIFY")
        self.assertEqual(first["records"], second["records"])
        self.assertEqual(originals, module._originals(self.root, self.cutoff))
        self.assertTrue(second["original_bytes_preserved"])
        self.assertEqual(second["exit_code"], 0)
        self.assertEqual(second["notification"]["decision"], "DONT_NOTIFY")
        saved = module.attempts(self.receipts)
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]["start"]["trigger_kind"], "SCHEDULED")
        self.assertEqual(saved[0]["start"]["trigger_at"], module.stamp(self.cutoff + timedelta(minutes=1)))
        self.assertEqual(saved[0]["end"]["actual_ended_at"], module.stamp(self.cutoff + timedelta(minutes=2)))

    def test_parallel_trigger_does_not_launch_second_child(self):
        entered, release = threading.Event(), threading.Event()
        result = []
        def local_stub(root):
            entered.set()
            self.assertTrue(release.wait(5))
            return self.child()
        with patch.object(module, "_execute", side_effect=local_stub) as child:
            thread = threading.Thread(target=lambda: result.append(self.run_wrapper()))
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                duplicate = self.run_wrapper()
                self.assertEqual(duplicate["status"], "DUPLICATE_IN_FLIGHT")
                self.assertIsNone(duplicate["exit_code"])
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(child.call_count, 1)
        self.assertEqual(result[0]["status"], "RECORDED_AND_REPLAYED")

    def test_os_lock_released_after_holder_process_terminates(self):
        lock = self.receipts / "locks/test.lock"
        script = ("import importlib.util, pathlib, sys; "
                  "s=importlib.util.spec_from_file_location('m',sys.argv[1]); "
                  "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                  "c=m.cutoff_lock(pathlib.Path(sys.argv[2])); "
                  "ok=c.__enter__(); print('LOCKED' if ok else 'FAILED',flush=True); sys.stdin.read()")
        child = subprocess.Popen([sys.executable, "-B", "-c", script, str(MODULE_PATH), str(lock)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "LOCKED")
            with module.cutoff_lock(lock) as acquired:
                self.assertFalse(acquired)
        finally:
            child.terminate()
            child.communicate(timeout=10)
        with module.cutoff_lock(lock) as acquired:
            self.assertTrue(acquired)
        self.assertTrue(lock.is_file())

    def test_retry_records_prior_failure_and_recovery_without_rewriting_receipts(self):
        with patch.object(module, "_execute", side_effect=lambda root: self.child(fail=True)):
            failed = self.run_wrapper()
        first_bytes = {path: path.read_bytes() for path in self.receipts.glob("attempts/*/*.json")}
        self.clock += timedelta(seconds=10)
        with patch.object(module, "_execute", side_effect=lambda root: self.child()):
            retried = self.run_wrapper()
        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual(failed["exit_code"], 3)
        self.assertEqual(retried["classification"], "RETRY")
        self.assertTrue(retried["recovery"])
        self.assertIn("recovered_after_failed_or_unfinished_attempt", retried["notification"]["reasons"])
        for path, value in first_bytes.items():
            self.assertEqual(path.read_bytes(), value)

    def test_timeout_records_unknown_exit_code_and_failed_status(self):
        with patch.object(module, "_execute", side_effect=subprocess.TimeoutExpired(["local_stub"], 240)):
            result = self.run_wrapper()
        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["error"]["type"], "TimeoutExpired")
        self.assertIsNotNone(result["child_ended_at"])

    def test_source_change_fails_before_child_and_receipt_is_retained(self):
        with patch.object(module, "verify_runtime", side_effect=ValueError("changed environment")), \
                patch.object(module, "_execute") as child:
            result = self.run_wrapper()
        child.assert_not_called()
        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["exit_code"])
        self.assertEqual(len(module.attempts(self.receipts)), 1)

    def test_changed_old_bytes_are_fail_closed(self):
        with patch.object(module, "_execute", side_effect=lambda root: self.child()):
            self.run_wrapper()
        def changes_existing(root):
            child = self.child()
            path = next(module._hour(root, self.cutoff).glob("observations/*.json"))
            path.write_text("tampered", encoding="utf-8")
            return child
        with patch.object(module, "_execute", side_effect=changes_existing):
            result = self.run_wrapper()
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["original_bytes_preserved"])
        self.assertIn("original_cycle_bytes_changed", result["error"]["message"])

    def test_wrong_child_cutoff_and_order_permission_are_failed(self):
        for key, wrong_value in (("cutoff", module.stamp(self.cutoff + module.HOUR)), ("order_allowed", True)):
            def inconsistent(root):
                child = self.child()
                payload = json.loads(child.stdout)
                payload[key] = wrong_value
                child.stdout = json.dumps(payload)
                return child
            with patch.object(module, "_execute", side_effect=inconsistent):
                result = self.run_wrapper()
            self.assertEqual(result["status"], "FAILED")
            self.assertIn("frozen_driver_contract_mismatch", result["error"]["message"])

    def test_current_cutoff_never_backfills_missing_earlier_hour(self):
        self.cutoff += 2 * module.HOUR
        self.clock = self.cutoff + timedelta(minutes=2)
        with patch.object(module, "_execute", side_effect=lambda root: self.child()):
            result = self.run_wrapper()
        self.assertEqual(result["input_cutoff"], module.stamp(self.cutoff))
        self.assertFalse(result["automatic_backfill"])
        self.assertEqual([path.name for path in (self.root / "forward/cycles").iterdir()],
                         [self.cutoff.strftime("%Y%m%dT%H0000Z")])

    def test_late_duplicate_does_not_rename_original_on_time_signal(self):
        with patch.object(module, "_execute", side_effect=lambda root: self.child()):
            first = self.run_wrapper()
            self.clock = self.cutoff + timedelta(minutes=20)
            duplicate = self.run_wrapper()
        self.assertEqual(first["records"], duplicate["records"])
        self.assertTrue(all(record["timing_status"] == "ON_TIME" for record in duplicate["records"]))

    def test_window_fixed_and_changed_plan_cannot_reuse_receipt_root(self):
        with patch.object(module, "_execute", side_effect=lambda root: self.child()):
            self.run_wrapper()
        altered = deepcopy(self.plan)
        altered["start_cutoff"] = "2026-09-06T15:00:00Z"
        with self.assertRaisesRegex(ValueError, "immutable_reliability_plan_changed"):
            module.run(self.root, altered, self.receipts, trigger_kind="MANUAL")
        self.assertEqual(len(module.attempts(self.receipts)), 1)

    def test_no_fabricated_trigger_or_late_hour_launch(self):
        with self.assertRaisesRegex(ValueError, "actual_scheduler_timestamp"):
            module.run(self.root, self.plan, self.receipts, trigger_kind="SCHEDULED")
        with self.assertRaisesRegex(ValueError, "trigger_cannot_postdate"):
            module.run(self.root, self.plan, self.receipts, trigger_kind="SCHEDULED",
                       trigger_at=module.stamp(self.clock + timedelta(seconds=1)))
        self.clock = self.cutoff + timedelta(minutes=55)
        with patch.object(module, "_execute") as child:
            result = self.run_wrapper()
        child.assert_not_called()
        self.assertEqual(result["status"], "FAILED")

    def test_elapsed_denominator_excludes_future_and_pending_hours(self):
        records = [self.projection(item) for item in self.plan["plans"]]
        report = module.build_coverage(self.plan, records, [], [], [], self.cutoff + timedelta(minutes=2))
        self.assertEqual(report["elapsed_strategy_hours"], 0)
        self.assertIsNone(report["on_time_fraction"])
        self.assertEqual(report["future_strategy_hours"], 142)
        self.assertEqual(report["soak_acceptance"], "INCOMPLETE_72_HOURS")
        later = module.build_coverage(self.plan, records, [], [], [], self.cutoff + 3 * module.HOUR + timedelta(minutes=6))
        self.assertEqual(later["elapsed_strategy_hours"], 8)
        self.assertEqual(later["counts"], {"ON_TIME": 2, "LATE": 0, "MISSING": 6, "FAILED": 0})
        self.assertEqual(later["observed_fraction"], 0.25)

    def test_missing_stays_missing_after_backfill_and_after_later_nonbackfill(self):
        as_of = self.cutoff + timedelta(minutes=6)
        first = module.build_coverage(self.plan, [], [], [], [], as_of)
        backfill = [self.projection(item, delay=900, backfill=True) for item in self.plan["plans"]]
        later = module.build_coverage(self.plan, backfill, [], [], [first], self.cutoff + timedelta(minutes=20))
        self.assertEqual(later["counts"]["MISSING"], 2)
        self.assertEqual(len(later["backfill_observations_separate"]), 2)
        self.assertEqual(later["new_missing"], [])
        changed_intent = [self.projection(item, delay=900) for item in self.plan["plans"]]
        report = module.build_coverage(self.plan, changed_intent, [], [], [first], self.cutoff + timedelta(minutes=20))
        self.assertEqual(report["counts"]["MISSING"], 2)
        self.assertTrue(report["rows"][0]["original_missing_preserved"])

    def test_failed_record_or_failed_attempt_is_failed_not_missing(self):
        problem = {"cutoff": module.stamp(self.cutoff), **self.plan["plans"][0], "reason": "bad input hash"}
        result = module.build_coverage(self.plan, [], [problem], [], [], self.cutoff + timedelta(minutes=6))
        self.assertEqual(result["counts"]["FAILED"], 1)
        self.assertEqual(result["counts"]["MISSING"], 1)
        self.assertIsNone(result["first_nonmanual_execution_receipt"])

    def test_timing_policy_uses_actual_signal_and_unknown_fields_stay_null(self):
        record = self.record(self.plan["plans"][0], delay=242.249879)
        fields = module.time_fields(record)
        self.assertEqual(fields["reference_execution_eligible_at"], module.stamp(self.cutoff + module.HOUR))
        self.assertGreater(module.timestamp(fields["reference_execution_eligible_at"]),
                           module.timestamp(fields["signal_available_at"]))
        self.assertFalse(fields["reference_execution_performed"])
        self.assertIsNone(fields["reference_execution_price"])
        record.pop("signal_available_at")
        record["input"].pop("input_available_at")
        fields = module.time_fields(record)
        self.assertIsNone(fields["data_received_at"])
        self.assertIsNone(fields["signal_available_at"])
        self.assertIsNone(fields["reference_execution_eligible_at"])

    def test_300_second_deadline_is_inclusive_and_late_does_not_enable_current_open(self):
        for delay, expected in ((300, "ON_TIME"), (300.000001, "LATE"), (3600, "LATE")):
            record = self.projection(self.plan["plans"][0], delay=delay)
            self.assertEqual(record["timing_status"], expected)
            self.assertGreater(module.timestamp(record["reference_execution_eligible_at"]),
                               module.timestamp(record["signal_available_at"]))

    def test_new_missing_notifies_once_and_duplicate_is_measured(self):
        absent_cutoff = self.cutoff
        self.cutoff += module.HOUR
        self.clock = self.cutoff + timedelta(minutes=2)
        def with_absence(root):
            child = self.child()
            cycle = json.loads(child.stdout)
            cycle["prior_absences"] = [{"cutoff": module.stamp(absent_cutoff),
                                         "missing_plan_hashes": [item["plan_hash"] for item in self.plan["plans"]]}]
            child.stdout = json.dumps(cycle)
            return child
        with patch.object(module, "_execute", side_effect=with_absence):
            first = self.run_wrapper()
            second = self.run_wrapper()
        self.assertEqual(len(first["new_missing"]), 2)
        self.assertEqual(second["new_missing"], [])
        self.assertEqual(first["notification"]["decision"], "NOTIFY")
        self.assertEqual(second["notification"]["decision"], "DONT_NOTIFY")

    def test_child_process_receives_clean_environment_and_only_fixed_driver(self):
        tools = self.root / "tools"
        tools.mkdir()
        (tools / "run_forward_cycle.py").write_text(
            "import json, os, sys\nprint(json.dumps({'argv':sys.argv[1:], 'pythonpath':os.getenv('PYTHONPATH'),"
            "'pythonhome':os.getenv('PYTHONHOME'), 'utf8':os.getenv('PYTHONUTF8')}))\n", encoding="utf-8")
        # This executes a harmless stdlib local stub; no network or observer runs.
        with patch.dict(os.environ, {"PYTHONPATH": "untrusted", "PYTHONHOME": "untrusted"}):
            result = module._execute(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIsNone(value["pythonpath"])
        self.assertIsNone(value["pythonhome"])
        self.assertEqual(value["utf8"], "1")
        self.assertEqual(value["argv"], ["--deployment", str(self.root / "forward/deployment-plans.json"),
                                         "--runtime-root", str(self.root)])


if __name__ == "__main__":
    unittest.main()
