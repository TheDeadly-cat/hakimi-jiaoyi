"""Use actual new native records to test trusted read-only comparison routing."""
from hashlib import sha256
import json
import unittest

from tests import test_terminal_research as fixtures
from exchange_terminal.services.terminal_saved_results import verified_saved_result, resolve_execution_research


class SavedResultRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TerminalResearchTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service

    def inventory(self):
        return {str(path): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in self.fixture.core.workspace.rglob("*") if path.is_file()}

    def test_routed_comparison_reads_saved_bindings_without_run_or_job(self):
        first_task = self.fixture.task()
        first = self.fixture.run_task(first_task)
        second = self.fixture.run_task(self.fixture.task(parent_task_id=first_task["id"],
            risk={"position_pct": 10, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1}))
        before, calls = self.inventory(), self.fixture.runner.call_count
        request = {"references": [{"kind": "terminal_run", "id": item["id"]} for item in (first, second)]}
        view = self.service.read("terminal_saved_comparison", json.dumps(request))
        self.assertEqual(view["status"], "UNKNOWN_CONDITIONS")
        self.assertIn("risk.position_pct", view["mismatches"][0]["fields"])
        self.assertEqual(view["differences_from_first"], [])
        self.assertEqual(view["new_economic_runs"], 0)
        self.assertEqual(self.fixture.runner.call_count, calls)
        self.assertEqual(self.inventory(), before)

    def test_client_report_or_path_cannot_become_verified_result(self):
        for reference in ({"kind": "terminal_run", "id": "../report.json"},
                          {"kind": "terminal_run", "id": "a" * 64, "report": {"status": "COMPLETED"}},
                          {"kind": "other", "id": "a" * 64}):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                verified_saved_result(self.service, reference)
        self.assertFalse(self.fixture.core.workspace.exists())

    def test_changed_saved_report_is_rejected_without_repair(self):
        task = self.fixture.task()
        run = self.fixture.run_task(task)
        path = self.fixture.core.workspace / "terminal-runs" / run["operation_id"] / "report.json"
        document = json.loads(path.read_bytes())
        document["result"]["total_return_pct"] = 999
        path.write_text(json.dumps(document), encoding="utf-8")
        before, calls = self.inventory(), self.fixture.runner.call_count
        with self.assertRaises(ValueError):
            verified_saved_result(self.service, {"kind": "terminal_run", "id": run["id"]})
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.fixture.runner.call_count, calls)

    def test_unknown_saved_result_is_not_completed_or_retried(self):
        task = self.fixture.task()
        self.fixture.runner.side_effect = RuntimeError("new synthetic interrupted case")
        run = self.fixture.run_task(task)
        self.assertEqual(run["status"], "UNKNOWN")
        before, calls = self.inventory(), self.fixture.runner.call_count
        with self.assertRaisesRegex(ValueError, "not_completed"):
            verified_saved_result(self.service, {"kind": "terminal_run", "id": run["id"]})
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.fixture.runner.call_count, calls)

    def test_real_rendered_core_comparison_uses_read_route_and_preserves_vendor(self):
        from exchange_terminal.services import quant_workspace as quant
        raw_path = quant._verified_package_root(quant._VENDOR) / "resources" / "desktop.html"
        raw = raw_path.read_bytes()
        html = quant.render_quant_html(raw, "comparison-test-session", "comparison-test-nonce").decode()
        self.assertIn("case'compare':await showStrictSavedComparison(target);break;", html)
        self.assertIn("await api('terminal_saved_comparison/'", html)
        self.assertNotIn("case'compare':await perform('compare'", html)
        self.assertEqual(raw_path.read_bytes(), raw)
        self.assertIn("terminal_saved_comparison", quant._READ_RESOURCES)

    def test_execution_binding_uses_retained_fields_and_verified_family_chain(self):
        self.fixture.market["meta"].update(security_id="QA:SYNTH", currency="USD", asset_class="US_EQUITY")
        self.fixture.market["digest"] = fixtures.digest({key: value for key, value in self.fixture.market.items() if key != "digest"})
        task = self.fixture.task()
        run = self.fixture.run_task(task)
        self.fixture.task(parent_task_id=task["id"], strategy_params={"fast_window": 7, "slow_window": 45})
        before, calls = self.inventory(), self.fixture.runner.call_count
        resolved = resolve_execution_research(self.service, {"kind": "terminal_run", "id": run["id"]})
        self.assertEqual(resolved["binding"]["strategy_params"], run["configuration"]["strategy_params"])
        self.assertEqual(resolved["binding"]["task_id"], task["id"])
        self.assertEqual(resolved["binding"]["security_id"], "QA:SYNTH")
        self.assertEqual(resolved["display"]["symbol"], "SYNTH")
        self.assertEqual(resolved["owner_id"], "family:" + task["family_id"])
        self.assertNotIn("quantity_policy", resolved["assumptions"])
        self.assertEqual(self.fixture.runner.call_count, calls)
        self.assertEqual(self.inventory(), before)

    def test_execution_missing_security_is_not_inferred_from_symbol(self):
        run = self.fixture.run_task(self.fixture.task())
        resolved = resolve_execution_research(self.service, {"kind": "terminal_run", "id": run["id"]})
        self.assertEqual(resolved["display"]["symbol"], "SYNTH")
        self.assertNotIn("security_id", resolved["binding"])
        self.assertNotIn("currency", resolved["display"])


if __name__ == "__main__":
    unittest.main()
