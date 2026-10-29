"""Read-only history access using temporary synthetic records and real verifiers."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_workspace_history import TerminalWorkspaceHistory
from exchange_terminal.services.terminal_research import TerminalResearchService
from tests import test_terminal_research as native_fixture_tests


def tree_identity(root):
    return {str(path.relative_to(root)): ("directory" if path.is_dir() else sha256(path.read_bytes()).hexdigest())
            for path in root.rglob("*")}


class WorkspaceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-history-read-only-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local = self.root / "local"
        self.original = self.root / "old-original"

    def reader(self, *roots, **options):
        return TerminalWorkspaceHistory(local_app_data=self.local, known_original_root=self.original,
                                        extra_roots=roots, **options)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_missing_discovery_is_lazy_and_never_creates_any_path(self):
        before = tree_identity(self.root)
        with patch.object(Path, "mkdir", side_effect=AssertionError("history must not initialize paths")):
            self.assertEqual(self.reader().list_workspaces()["items"], [])
        self.assertEqual(tree_identity(self.root), before)

    def test_discovers_known_trial_roots_with_identity_and_excludes_current_workspace(self):
        trial = self.local / "HakimiTradeTrial" / "workspaces"
        for name in ("old", "active"):
            self.write(trial / name / "trial-workspace-identity.json",
                       {"schema_version": "research-trial-workspace-v1", "bundle_id": name})
        before = tree_identity(self.root)
        inventory = self.reader(current_workspace=trial / "active").list_workspaces()
        self.assertEqual(len(inventory["items"]), 1)
        item = inventory["items"][0]
        self.assertEqual(item["physical_root"], str((trial / "old").resolve()))
        self.assertEqual(item["schemas"], ["research-trial-workspace-v1"])
        self.assertTrue(item["read_only"])
        self.assertEqual(item["new_economic_runs"], 0)
        self.assertEqual(tree_identity(self.root), before)

    def test_unknown_run_is_retained_without_verifier_retry_or_new_files(self):
        self.write(self.original / "runs" / "run-interrupted" / "started.json",
                   {"run_id": "historical-unknown", "started_at": "2026-01-01T00:00:00Z"})
        reader = self.reader()
        workspace = reader.list_workspaces()["items"][0]["id"]
        before = tree_identity(self.root)
        with patch.object(reader, "_core", side_effect=AssertionError("Unknown must not invoke calculation or verification repair")):
            items = reader.list_records(workspace, "runs")["items"]
            view = reader.read_detail(workspace, "runs", items[0]["id"])
        self.assertEqual(view["status"], "UNKNOWN")
        self.assertEqual(view["verification_status"], "METADATA_ONLY")
        self.assertFalse(view["automatic_retry"])
        self.assertNotIn("chart", view)
        self.assertEqual(tree_identity(self.root), before)

    def test_actual_native_read_contract_preserves_tasks_results_and_no_service_constructor(self):
        fixture = native_fixture_tests.TerminalResearchTests("runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        task = fixture.task()
        report = fixture.run_task(task)
        reader = self.reader(fixture.core.workspace)
        workspace = reader.list_workspaces()["items"][0]["id"]
        before = tree_identity(fixture.core.workspace)
        with patch.object(TerminalResearchService, "__init__", side_effect=AssertionError("no old service initialization")), \
             patch.object(TerminalResearchService, "_write", side_effect=AssertionError("no old record writes")):
            tasks = reader.list_records(workspace, "tasks")["items"]
            runs = reader.list_records(workspace, "runs")["items"]
            detail = reader.read_detail(workspace, "runs", runs[0]["id"])
        self.assertEqual(tasks[0]["task_id"], task["id"])
        self.assertEqual(tasks[0]["verification_status"], "VERIFIED_RECORD")
        self.assertEqual(detail["report"]["id"], report["id"])
        self.assertEqual(detail["engine_id"], task["engine_id"])
        self.assertEqual(detail["configuration"], report["configuration"])
        self.assertEqual(detail["verification_status"], "VERIFIED_RECORD")
        self.assertTrue(detail["chart_available"])
        self.assertEqual(tree_identity(fixture.core.workspace), before)

    def test_changed_native_record_remains_unverified_metadata_and_cannot_supply_chart(self):
        fixture = native_fixture_tests.TerminalResearchTests("runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        task = fixture.task()
        fixture.run_task(task)
        path = next((fixture.core.workspace / "terminal-runs").glob("*/report.json"))
        document = json.loads(path.read_bytes())
        document["title"] = "altered synthetic report"
        path.write_text(json.dumps(document), encoding="utf-8")
        reader = self.reader(fixture.core.workspace)
        workspace = reader.list_workspaces()["items"][0]["id"]
        before = tree_identity(fixture.core.workspace)
        item = reader.list_records(workspace, "runs")["items"][0]
        view = reader.read_detail(workspace, "runs", item["id"])
        self.assertEqual(view["verification_status"], "METADATA_ONLY")
        self.assertEqual(view["stored_metadata"]["title"], "altered synthetic report")
        self.assertNotIn("chart", view)
        self.assertEqual(tree_identity(fixture.core.workspace), before)

    def test_canonical_demo_tasks_use_pure_current_verifier_without_workbench(self):
        from hakimi_research.trade_cli import initialize_demo
        from hakimi_research.workbench_service import Workbench
        initialize_demo(self.original)
        reader = self.reader()
        workspace = reader.list_workspaces()["items"][0]["id"]
        before = tree_identity(self.root)
        with patch.object(Workbench, "__init__", side_effect=AssertionError("no workbench initialization")):
            items = reader.list_records(workspace, "tasks")["items"]
            detail = reader.read_detail(workspace, "tasks", items[0]["id"])
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["verification_status"] == "VERIFIED_RECORD" for item in items))
        self.assertEqual(detail["verified_by"], "hakimi_research")
        self.assertIn("configuration", detail["task"])
        self.assertEqual(tree_identity(self.root), before)

    def test_external_legacy_input_is_rejected_before_calling_core_verifier(self):
        self.write(self.root / "outside.json", {"source": "must not read"})
        self.write(self.original / "tasks" / "old.json", {
            "schema_version": "hakimi-offline-task-v1", "snapshot": str(self.root / "outside.json"),
            "title": "external reference"})
        reader = self.reader()
        workspace = reader.list_workspaces()["items"][0]["id"]
        before = tree_identity(self.root)
        view = reader.list_records(workspace, "tasks")["items"][0]
        self.assertEqual(view["verification_status"], "METADATA_ONLY")
        self.assertIn("outside_workspace", view["verification_error"])
        self.assertEqual(tree_identity(self.root), before)

    def test_unsupported_schema_discloses_metadata_only_and_ids_do_not_accept_paths(self):
        self.write(self.original / "runs" / "run-future" / "report.json",
                   {"schema_version": "future-v999", "title": "future record", "status": "COMPLETED"})
        reader = self.reader()
        workspace = reader.list_workspaces()["items"][0]["id"]
        item = reader.list_records(workspace, "runs")["items"][0]
        self.assertEqual(item["verification_status"], "METADATA_ONLY")
        self.assertEqual(item["schema_version"], "future-v999")
        self.assertFalse(item["chart_available"])
        for identity in ("../tasks", str(self.original), "0" * 32):
            with self.assertRaises(ValueError):
                reader.read_detail(workspace, "runs", identity)
        with self.assertRaises(ValueError):
            reader.list_records(workspace, "../../data")

    def test_reparse_workspace_and_reparse_record_are_never_followed(self):
        real = self.root / "real"
        self.write(real / "tasks" / "task.json", {"title": "real"})
        link = self.root / "linked"
        try:
            link.symlink_to(real, target_is_directory=True)
        except OSError as exc:
            self.skipTest("Creating a local symlink unavailable: " + str(exc))
        inventory = self.reader(link).list_workspaces()
        self.assertEqual(inventory["items"], [])
        self.assertTrue(any("reparse" in item for item in inventory["warnings"]))
        self.original.mkdir()
        (self.original / "tasks").mkdir()
        (self.original / "tasks" / "linked.json").symlink_to(real / "tasks" / "task.json")
        reader = self.reader()
        workspace = reader.list_workspaces()["items"][0]["id"]
        records = reader.list_records(workspace, "tasks")
        self.assertEqual(records["items"], [])
        self.assertTrue(any("reparse" in item for item in records["warnings"]))


if __name__ == "__main__":
    unittest.main()
