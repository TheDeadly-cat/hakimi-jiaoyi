"""Historical v6 tasks remain readable; new calculations require a new version."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_research as research
import test_terminal_research as terminal_fixtures


class IndicatorMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = terminal_fixtures.TerminalResearchTests("test_reads_are_lazy_and_core_routes_pass_through")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_legacy_task_report_remain_byte_identical_readable_and_revisable(self):
        old_id = "terminal.causal-long-only-signals-v6"
        old_sources = research._engine_source_identity()
        old_sources.pop("indicator_math.py")
        seal = research._seal
        def legacy_seal(value, key="id"):
            value = deepcopy(value)
            if value.get("schema_version") == "hakimi-terminal-task-v1":
                value.pop("indicator_contract", None)
            return seal(value, key)
        with patch.object(research, "ENGINE_ID", old_id), patch.object(research, "_seal", legacy_seal), \
                patch.object(research, "_engine_source_identity", return_value=old_sources):
            task = self.fixture.task()
            report = self.fixture.run_task(task)
        before = {path: path.read_bytes() for path in self.fixture.core.workspace.rglob("*.json")}
        service = self.fixture.service
        listed = service.read("terminal_tasks")["items"]
        self.assertEqual(listed[0]["id"], task["id"])
        self.assertTrue(listed[0]["requires_revision"])
        reopened = service.read("terminal_runs", report["id"])
        self.assertEqual(reopened["engine_id"], old_id)
        self.assertEqual(reopened["result"], report["result"])
        self.assertIsNone(reopened["chart"]["indicator_contract"])
        with self.assertRaisesRegex(ValueError, "create_new_version"):
            self.fixture.run_task(task)
        revised = self.fixture.task(parent_task_id=task["id"])
        self.assertEqual(revised["version"], 2)
        self.assertEqual(revised["engine_id"], research.ENGINE_ID)
        self.assertEqual(revised["indicator_contract"]["version"], "hakimi-indicators-v1")
        self.assertFalse(revised["requires_revision"])
        self.assertEqual(self.fixture.run_task(revised)["status"], "COMPLETED")
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw, str(path))


if __name__ == "__main__":
    unittest.main()
