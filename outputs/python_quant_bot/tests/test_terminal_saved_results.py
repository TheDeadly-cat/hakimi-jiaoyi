"""Use actual new native records to test trusted read-only comparison routing."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from tests import test_terminal_research as fixtures
from exchange_terminal.services.terminal_saved_results import verified_saved_result, resolve_execution_research
from exchange_terminal.services import terminal_saved_results as saved_results


def create_synthetic_native_saved_fixture(testcase):
    """New TEMP sealed SYNTHETIC records; no research runner is invoked.

    This deliberately fabricated completed report tests the real retained-record
    verifier/resolver schema, not research correctness or market authenticity.
    """
    from exchange_terminal.services import terminal_research as native
    fixture = fixtures.TerminalResearchTests("runTest")
    fixture.setUp()
    testcase.addCleanup(fixture.doCleanups)
    testcase.addCleanup(fixture.service.close)
    fixture.market["meta"].update(security_id="QA:SYNTH", currency="USD", asset_class="US_EQUITY",
                                  evidence_kind="SYNTHETIC_TEST", data_kind="SYNTHETIC_TEST")
    fixture.market["digest"] = fixtures.digest({key: value for key, value in fixture.market.items() if key != "digest"})
    selected = fixture.task(name="SYNTHETIC_TEST 记录兼容夹具；没有运行研究")
    task = fixture.service._task_record(selected["id"])
    data = fixture.service._input(task["input_id"])
    operation = native._digest({"task_id": task["id"], "input_id": task["input_id"], "fingerprint": task["fingerprint"]})
    started = native._seal({"schema_version": "hakimi-terminal-run-start-v1", "operation_id": operation,
        "task_id": task["id"], "input_id": task["input_id"], "started_at": "2026-10-30T00:00:00+00:00", "automatic_retry": False})
    report = native._seal({"schema_version": "hakimi-terminal-run-v1", "operation_id": operation,
        "task_id": task["id"], "family_id": task["family_id"], "version": task["version"], "title": task["title"],
        "strategy_id": task["strategy_id"], "engine_id": task["engine_id"], "started_at": started["started_at"],
        "configuration": native._task_configuration(task), "input_summary": fixture.service._input_view(data, rows=False),
        "quality": data["quality"], "evidence_status": "UNVERIFIED", "data_kind": "SYNTHETIC_TEST",
        "evidence_kind": "SYNTHETIC_TEST", "status": "COMPLETED", "error": None,
        "result": {"ok": True, "trades": [], "equity_curve": [], "order_event_count": 0,
                   "fixture_only": True, "not_computed": True}, "automatic_retry": False,
        "permissions": dict(native.PERMISSIONS), "limitations": ["SYNTHETIC_TEST fixture only; no economic run or market evidence."]})
    root = fixture.core.workspace / "terminal-runs" / operation
    fixture.service._write(root / "started.json", started)
    fixture.service._write(root / "report.json", report)
    fixture.runner.assert_not_called()
    return fixture, task, report


class RecordedSourceProjectionTests(unittest.TestCase):
    def inventory(self, fixture):
        return {str(path): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in fixture.core.workspace.rglob("*") if path.is_file()}

    def test_actual_native_opt_in_retains_default_binding_and_uses_only_saved_source(self):
        fixture, task, report = create_synthetic_native_saved_fixture(self)
        reference = {"kind": "terminal_run", "id": report["id"]}
        before = self.inventory(fixture)
        with patch("exchange_terminal.services.terminal_research._engine_source_identity", side_effect=AssertionError("No current source")), \
             patch.object(fixture.service, "fingerprint", side_effect=AssertionError("No rule recomputation")):
            original = resolve_execution_research(fixture.service, reference)
            explicit_default = resolve_execution_research(fixture.service, reference, include_recorded_source=False)
            projected = resolve_execution_research(fixture.service, reference, include_recorded_source=True)
        self.assertEqual(original, explicit_default)
        self.assertEqual(set(original), {"binding", "owner_id", "display", "assumptions"})
        self.assertEqual({key: projected[key] for key in original}, original)
        self.assertNotIn("source_hash", projected["binding"])
        source = projected["recorded_source_identity"]
        self.assertEqual(source["source_files"], task["engine_source_identity"])
        self.assertEqual(source["fingerprint"], task["fingerprint"])
        self.assertEqual(source["content_sha256"], saved_results._recorded_digest(task["engine_source_identity"]))
        self.assertEqual(source["reference"], reference)
        self.assertEqual(source["report_hash"], report["id"])
        self.assertEqual(source["task_id"], task["id"])
        classification = projected["recorded_evidence_classification"]
        self.assertEqual(classification["decision"]["status"], "SYNTHETIC_OFFLINE_ONLY")
        self.assertFalse(classification["decision"]["external_research_eligible"])
        self.assertTrue(classification["decision"]["admission_cannot_override_synthetic"])
        self.assertIn({"path": "report.input_summary.meta.evidence_kind", "value": "SYNTHETIC_TEST"}, classification["facts"])
        self.assertEqual(self.inventory(fixture), before)
        fixture.runner.assert_not_called()

    def test_missing_saved_source_fails_instead_of_reading_current_code(self):
        fixture, task, report = create_synthetic_native_saved_fixture(self)
        reference = {"kind": "terminal_run", "id": report["id"]}
        binding = resolve_execution_research(fixture.service, reference)["binding"]
        # Pure sidecar validation deliberately receives incomplete retained data.
        # The actual positive read path above runs the unmodified record verifier.
        with patch("exchange_terminal.services.terminal_research._engine_source_identity", side_effect=AssertionError("No fallback")):
            for value in (None, {}, {"strategy_signals.py": "not-a-hash"}):
                damaged = {**deepcopy(task), "engine_source_identity": value}
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "saved_native_source_identity_missing"):
                    saved_results._recorded_native_source(damaged, report, reference, binding)
        fixture.runner.assert_not_called()

    def test_classification_unknown_authentication_claim_and_synthetic_are_distinct_without_symbol_guess(self):
        unknown = saved_results._recorded_evidence_decision([])
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertIsNone(unknown["external_research_eligible"])
        # No ticker heuristic, including QADEMO.
        self.assertEqual(saved_results._recorded_evidence_decision([{"path": "report.symbol", "value": "QADEMO"}]), unknown)
        for field, value in (("evidence_kind", "SYNTHETIC_TEST"), ("data_kind", "QA_TEST"), ("synthetic_only", True)):
            classified = saved_results._recorded_evidence_decision([{"path": "snapshot." + field, "value": value}])
            self.assertEqual(classified["status"], "SYNTHETIC_OFFLINE_ONLY")
            self.assertFalse(classified["external_research_eligible"])
        claim = saved_results._recorded_evidence_decision([{"path": "report.quality", "value": {"source_authenticated": True}}])
        self.assertEqual(claim["status"], "RECORDED_AUTHENTICATION_REQUIRES_ADMISSION")
        self.assertIsNone(claim["external_research_eligible"])
        self.assertTrue(claim["external_admission_required"])
        unverified = saved_results._recorded_evidence_decision([{"path": "report.quality", "value": {"source_authenticated": False}}])
        self.assertEqual(unverified["status"], "UNVERIFIED_RESEARCH")


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
