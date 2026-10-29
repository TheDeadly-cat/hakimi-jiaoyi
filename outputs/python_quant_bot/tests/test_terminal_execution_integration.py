"""New synthetic records through the actual terminal resolver and account adapter."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from tests import test_terminal_research as fixtures


class TerminalExecutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TerminalResearchTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.addCleanup(self.service.close)
        self.creation = dict(client_request_id="integration-create-0001", account_id="synthetic-integration", label="合成整合案例",
            evidence_kind="SYNTHETIC_TEST", initial_cash="1000", securities={"QA:SYNTH": {"symbol": "SYNTH", "tick_size": "0.01"}},
            rules=dict(max_order_notional="500", max_total_exposure="800", max_security_exposure="500", cash_floor="100",
                       fee_buffer="1", max_account_loss="200", quote_max_age_ms=60000))

    def prepare_research(self, identity=True):
        if identity:
            self.fixture.market["meta"].update(security_id="QA:SYNTH", currency="USD", asset_class="US_EQUITY")
            self.fixture.market["digest"] = fixtures.digest({key: value for key, value in self.fixture.market.items() if key != "digest"})
        task = self.fixture.task()
        run = self.fixture.run_task(task)
        return task, run, {"kind": "terminal_run", "id": run["id"]}

    def inventory_research(self):
        return {str(path): sha256(path.read_bytes()).hexdigest()
                for folder in ("terminal-inputs", "terminal-tasks", "terminal-runs")
                for path in (self.fixture.core.workspace / folder).rglob("*") if path.is_file()}

    def test_saved_native_run_binds_synthetic_plan_without_another_research_run(self):
        task, run, reference = self.prepare_research()
        before, runs = self.inventory_research(), self.fixture.runner.call_count
        view = self.service.read("terminal_execution_research", json.dumps({"reference": reference}))
        self.assertEqual(view["binding"]["report_hash"], run["id"])
        self.assertEqual(view["binding"]["security_id"], "QA:SYNTH")
        self.assertFalse((self.fixture.core.workspace / "offline-execution").exists())
        created = self.service.mutate("terminal_execution_create_account", deepcopy(self.creation))
        result = self.service.mutate("terminal_execution_create_plan", {
            "client_request_id": "integration-plan-0001", "account_id": self.creation["account_id"],
            "account_context": created["account_context"], "reference": reference, "stage": "SIMULATION"})
        plan = result["account"]["ledger"]["plans"][0]
        self.assertEqual(plan["research_binding"]["task_id"], task["id"])
        self.assertEqual(result["account"]["plan_links"][0]["owner_continuity"], "VERIFIED_TASK_FAMILY")
        self.assertEqual(result["account"]["ledger"]["orders"], [])
        self.assertTrue(result["account"]["permissions"]["local_simulation_allowed"])
        for name in ("paper_order_allowed", "live_order_allowed", "order_allowed", "broker_connection_allowed", "model_calls_allowed"):
            self.assertIs(result["account"]["permissions"][name], False)
        self.assertEqual(self.fixture.runner.call_count, runs)
        self.assertEqual(self.inventory_research(), before)

    def test_missing_security_keeps_saved_research_readable_but_blocks_plan(self):
        _, _, reference = self.prepare_research(identity=False)
        created = self.service.mutate("terminal_execution_create_account", deepcopy(self.creation))
        with self.assertRaises(ValueError):
            self.service.mutate("terminal_execution_create_plan", {
                "client_request_id": "integration-plan-0001", "account_id": self.creation["account_id"],
                "account_context": created["account_context"], "reference": reference, "stage": "SIMULATION"})
        self.assertEqual(self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]["plans"], [])
        self.assertEqual(self.service.read("terminal_runs", reference["id"])["status"], "COMPLETED")

    def test_initial_execution_inventory_is_lazy_and_does_not_dispatch_core(self):
        self.assertEqual(self.service.read("terminal_execution_accounts")["items"], [])
        self.assertFalse(self.fixture.core.workspace.exists())
        self.assertEqual(self.fixture.core.calls, [])
        self.fixture.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
