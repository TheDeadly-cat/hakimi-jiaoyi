"""Fictional injected stock replies; no live source, economic runner or broker."""
from datetime import date, timedelta
from hashlib import sha256
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from hakimi_research import daily_updates as daily, stock_intake as intake


def fixtures():
    path = Path(__file__).parents[3] / "tests" / "test_daily_updates.py"
    spec = importlib.util.spec_from_file_location("canonical_daily_test_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_hashes(root):
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()} if root.exists() else {}


class TerminalDailyResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-daily-adapter-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = (Path(self.temp.name) / "current-workspace").resolve()
        self.now = daily._clock("2026-10-23T21:00:00Z")
        self.data = fixtures()
        _, _, _, first, latest = intake._coverage(self.now, 20, "XNYS")
        self.query_start = (date.fromisoformat(first) - timedelta(days=120)).isoformat()
        self.response = self.reply(latest)
        self.requests = []
        self.sequence = 0
        self.adapter = TerminalDailyResearch(self.workspace, fetcher=self.fetch, clock=lambda: self.now)
        self.addCleanup(patch.stopall)
        patch("hakimi_research.daily_updates._fetch", side_effect=AssertionError("No real source request")).start()
        patch("hakimi_research.workbench_service.run_task", side_effect=AssertionError("No automatic economic execution")).start()

    def reply(self, last):
        value = self.data.source_reply(self.query_start, last)
        value["chart"]["result"][0]["meta"].update(dataGranularity="1d", longName="Fictional TEST Corporation")
        return value

    def fetch(self, url):
        self.requests.append(url)
        if isinstance(self.response, Exception):
            raise self.response
        return self.data.encoded(self.response)

    def action(self, action, **values):
        self.sequence += 1
        return self.adapter.mutate("terminal_daily_" + action,
                                   {"operation_id": f"isolated-{self.sequence:04d}", **values})

    def initial(self, *, create=True):
        checked = self.action("check_stock", symbol="TEST", history_sessions=20)
        self.assertEqual(checked["status"], "REVIEW_REQUIRED")
        saved = self.action("save_stock", intake_id=checked["id"], expected_check_hash=checked["check_hash"],
                            confirmed_security=checked["security"])
        self.assertEqual(saved["action_status"], "STOCK_INPUT_SAVED")
        if not create:
            return checked, saved, None
        task = self.action("create_task", input_id=saved["id"], **saved["suggested_task"])
        return checked, saved, task

    def test_reads_are_lazy_and_invalid_or_execution_actions_create_no_workspace(self):
        for kind in ("inputs", "intakes", "updates", "tasks"):
            self.assertEqual(self.adapter.read("terminal_daily_" + kind)["items"], [])
        catalog = self.adapter.read("terminal_daily_catalog")
        self.assertEqual(catalog["record_namespace"], "canonical-daily-v1")
        self.assertFalse(self.workspace.exists())
        for action in ("run_task", "advance_account", "execute", "stop_watch"):
            with self.assertRaisesRegex(ValueError, "no_execution"):
                self.action(action)
        with self.assertRaises(ValueError):
            self.action("check_stock", symbol="../TEST", history_sessions=20)
        with self.assertRaises(ValueError):
            self.action("check_update", input_id="a" * 24)
        self.assertFalse(self.workspace.exists())
        self.assertEqual(self.requests, [])

    def test_first_check_requires_exact_confirmation_and_save_does_not_create_task_or_run(self):
        checked = self.action("check_stock", symbol="TEST", history_sessions=20)
        self.assertEqual(checked["security"]["currency"], "USD")
        self.assertEqual(checked["session_count"], 20)
        self.assertFalse(checked["source_truth_verified"])
        self.assertEqual(checked["permissions"]["network_requests"], 1)  # one injected source call, no live request
        self.assertEqual(self.adapter.read("terminal_daily_inputs")["items"], [])
        with self.assertRaisesRegex(ValueError, "exact_security_confirmation"):
            self.action("save_stock", intake_id=checked["id"], expected_check_hash=checked["check_hash"],
                        confirmed_security={**checked["security"], "currency": "EUR"})
        saved = self.action("save_stock", intake_id=checked["id"], expected_check_hash=checked["check_hash"],
                            confirmed_security=checked["security"])
        self.assertEqual(saved["price_basis"], "RAW_UNADJUSTED")
        self.assertEqual(saved["evidence_kind"], "IMPORTED_UNVERIFIED")
        self.assertEqual(saved["record_schema"], "us-equity-daily-snapshot-v1")
        self.assertEqual(saved["new_economic_runs"], 0)
        self.assertTrue(saved["id"].startswith("canon-"))
        raw, snapshot = self.adapter.verified_input(saved["id"])
        self.assertEqual(sha256(raw).hexdigest(), saved["file_sha256"])
        self.assertEqual(snapshot["snapshot_id"], saved["input_id"])
        self.assertEqual(snapshot["security"], checked["security"])
        self.assertEqual(self.adapter.read("terminal_daily_tasks")["items"], [])
        self.assertEqual(list((self.adapter.root / "runs").iterdir()), [])
        before = file_hashes(self.workspace)
        self.adapter.read("terminal_daily_intakes", checked["id"])
        self.adapter.read("terminal_daily_inputs", saved["id"])
        self.assertEqual(file_hashes(self.workspace), before)
        self.assertEqual(len(self.requests), 1)

    def test_unchanged_creates_no_input_task_version_or_run_and_adoption_is_a_noop(self):
        _, saved, task = self.initial()
        protected = {name: file_hashes(self.adapter.root / name) for name in ("data", "tasks", "runs")}
        checked = self.action("check_update", input_id=saved["id"])
        self.assertEqual(checked["status"], "UNCHANGED")
        self.assertEqual(checked["display_status"], "UNCHANGED")
        self.assertIsNone(checked["candidate_snapshot_id"])
        self.assertEqual({name: file_hashes(self.adapter.root / name) for name in protected}, protected)
        before = file_hashes(self.workspace)
        result = self.action("freeze_update", update_id=checked["id"], expected_check_hash=checked["check_hash"])
        self.assertEqual(result["adoption_status"], "UNCHANGED_NO_NEW_VERSION")
        adopted = self.action("adopt_update", update_id=checked["id"], expected_check_hash=checked["check_hash"],
                              task_id=task["id"], expected_task_id=task["task_id"], score_end="2026-10-23")
        self.assertEqual(adopted["new_task_versions"], 0)
        self.assertEqual(file_hashes(self.workspace), before)

    def test_new_daily_requires_separate_freeze_and_adopt_preserving_old_version_and_no_run(self):
        _, saved, task = self.initial()
        old_inputs = file_hashes(self.adapter.root / "data")
        old_tasks = file_hashes(self.adapter.root / "tasks")
        self.response = self.reply("2026-10-26")
        self.now = daily._clock("2026-10-26T21:00:00Z")
        update = self.action("check_update", input_id=saved["id"])
        self.assertEqual((update["status"], update["display_status"]), ("READY", "NEW_DAILY"))
        self.assertEqual(update["new_dates"], ["2026-10-26"])
        with self.assertRaisesRegex(ValueError, "explicitly_frozen"):
            self.action("adopt_update", update_id=update["id"], expected_check_hash=update["check_hash"],
                        task_id=task["id"], expected_task_id=task["task_id"], score_end="2026-10-26")
        self.assertEqual(file_hashes(self.adapter.root / "tasks"), old_tasks)
        frozen = self.action("freeze_update", update_id=update["id"], expected_check_hash=update["check_hash"])
        self.assertEqual(frozen["action_status"], "DAILY_UPDATE_FROZEN")
        self.assertEqual(file_hashes(self.adapter.root / "tasks"), old_tasks)
        adopted = self.action("adopt_update", update_id=update["id"], expected_check_hash=update["check_hash"],
                              task_id=task["id"], expected_task_id=task["task_id"], score_end="2026-10-26")
        self.assertEqual(adopted["input_update_status"], "NEW_IMMUTABLE_VERSION")
        self.assertEqual(len(adopted["revisions"]), 2)
        self.assertNotEqual(adopted["task_id"], task["task_id"])
        for name, checksum in old_tasks.items():
            self.assertEqual(file_hashes(self.adapter.root / "tasks")[name], checksum)
        for name, checksum in old_inputs.items():
            self.assertEqual(file_hashes(self.adapter.root / "data")[name], checksum)
        self.assertEqual(list((self.adapter.root / "runs").iterdir()), [])
        self.assertEqual(adopted["new_economic_runs"], 0)

    def test_revision_requires_acknowledgement_and_failed_source_retains_real_status(self):
        _, saved, _ = self.initial(create=False)
        old_inputs = file_hashes(self.adapter.root / "data")
        self.response["chart"]["result"][0]["indicators"]["quote"][0]["high"][-3] += 1
        revised = self.action("check_update", input_id=saved["id"])
        self.assertEqual((revised["status"], revised["display_status"]), ("REVISION_REVIEW_REQUIRED", "REVISION"))
        with self.assertRaisesRegex(ValueError, "require_acknowledgement"):
            self.action("freeze_update", update_id=revised["id"], expected_check_hash=revised["check_hash"])
        self.assertEqual(file_hashes(self.adapter.root / "data"), old_inputs)
        self.action("freeze_update", update_id=revised["id"], expected_check_hash=revised["check_hash"], acknowledge_revisions=True)
        protected = file_hashes(self.adapter.root / "data")
        self.response = OSError("fictional unavailable source")
        failed = self.action("check_update", input_id=saved["id"])
        self.assertEqual((failed["status"], failed["display_status"]), ("BLOCKED", "FAILED"))
        self.assertFalse(failed["can_freeze"])
        self.assertEqual(file_hashes(self.adapter.root / "data"), protected)

    def test_same_physical_workspace_does_not_change_frozen_core_inventory_or_status(self):
        from exchange_terminal.services.quant_workspace import _load_kernel
        kernel = _load_kernel()
        frozen_cli = importlib.import_module("hakimi_terminal_research.trade_cli")
        frozen_cli.initialize_demo(self.workspace)
        frozen = kernel.service(self.workspace)
        before = {kind: frozen.read(kind) for kind in ("status", "tasks", "inputs", "runs")}
        root_data = {name: file_hashes(self.workspace / name) for name in ("data", "tasks", "runs")}
        _, saved, task = self.initial()
        self.response = self.reply("2026-10-26")
        self.now = daily._clock("2026-10-26T21:00:00Z")
        update = self.action("check_update", input_id=saved["id"])
        self.action("freeze_update", update_id=update["id"], expected_check_hash=update["check_hash"])
        self.action("adopt_update", update_id=update["id"], expected_check_hash=update["check_hash"],
                    task_id=task["id"], expected_task_id=task["task_id"], score_end="2026-10-26")
        after = {kind: frozen.read(kind) for kind in before}
        self.assertEqual(after, before)
        self.assertEqual({name: file_hashes(self.workspace / name) for name in root_data}, root_data)
        self.assertEqual(self.adapter.root, self.workspace / "daily")


if __name__ == "__main__":
    unittest.main()
