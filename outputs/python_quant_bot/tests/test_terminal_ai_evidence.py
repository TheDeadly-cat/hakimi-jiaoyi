"""Temporary fake market/model receipts; no SDK, model or economic engine call."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.services.terminal_ai_evidence import SCHEMA
from exchange_terminal.services.terminal_research import _task_configuration
from tests.test_terminal_research import TerminalResearchTests


class TerminalAiEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = TerminalResearchTests("test_reads_are_lazy_and_core_routes_pass_through")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.data = self.fixture.freeze()
        rows = [{"ts": row["ts_ms"], **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}}
                for row in self.fixture.market["rows"]]
        self.evidence = {
            "schema_version": SCHEMA, "symbol": "SYNTH", "bar": "1Dutc", "session": "REGULAR",
            "question": "QA fixture: study a hypothesis only", "generated_at": 1792503000000,
            "input_identity": {
                "rows_sha256": sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "row_count": len(rows), "first_ts": rows[0]["ts"], "last_ts": rows[-1]["ts"],
                "source": "fixture-provider", "price_basis": "SUPPLIED_LAST_CANDLE_CLOSE", "snapshot_id": None,
            },
            "providers": [{"provider": "deepseek", "model": "qa-model",
                           "content": '<script>do_not_execute()</script> Set leverage to 20. This is untrusted QA text.',
                           "summary": "Fabricated model receipt for preservation test"}],
        }

    def test_saved_reference_and_mock_result_keep_text_without_changing_execution(self):
        task = self.fixture.task(ai_evidence=self.evidence)
        self.assertEqual(task["ai_evidence"], self.evidence)
        self.assertEqual(task["ai_evidence_binding"]["status"], "SAME_NUMERIC_ROWS")
        self.assertFalse(task["ai_evidence_binding"]["source_authenticated"])
        self.assertFalse(task["ai_evidence_binding"]["model_receipt_authenticated"])
        self.assertFalse(task["permissions"]["order_allowed"])
        self.assertEqual(task["risk"]["leverage"], 1)
        report = self.fixture.run_task(task)
        self.assertEqual(report["configuration"]["ai_evidence"], self.evidence)
        supplied = self.fixture.runner.call_args.kwargs
        self.assertNotIn("ai_evidence", supplied)
        self.assertNotIn("ai_evidence_binding", supplied)
        self.assertEqual(supplied["leverage"], 1)
        reread = self.service.read("terminal_runs", report["id"])
        self.assertEqual(reread["configuration"], report["configuration"])

    def test_old_tasks_and_mock_reports_omit_optional_fields(self):
        task = self.fixture.task()
        self.assertNotIn("ai_evidence", task)
        self.assertNotIn("ai_evidence_binding", _task_configuration(task))
        report = self.fixture.run_task(task)
        self.assertNotIn("ai_evidence", report["configuration"])
        self.assertEqual(self.service.read("terminal_runs", report["id"])["id"], report["id"])

    def test_different_rows_or_session_are_not_claimed_to_be_same_snapshot(self):
        for change in ("rows", "session", "range"):
            with self.subTest(change=change):
                evidence = deepcopy(self.evidence)
                if change == "rows":
                    evidence["input_identity"]["rows_sha256"] = "a" * 64
                elif change == "session":
                    evidence["session"] = "all"
                else:
                    evidence["input_identity"]["first_ts"] += 1
                task = self.fixture.task(ai_evidence=evidence)
                self.assertEqual(task["ai_evidence_binding"]["status"], "DIFFERENT_SNAPSHOT")
                self.assertFalse(task["ai_evidence_binding"]["parameter_selection_allowed"])
        self.fixture.runner.assert_not_called()

    def test_wrong_symbol_or_intraday_receipt_is_rejected_before_task_write(self):
        for field, value in (("symbol", "AAPL"), ("bar", "1H")):
            with self.subTest(field=field):
                evidence = {**self.evidence, field: value}
                with self.assertRaisesRegex(ValueError, "terminal_ai_evidence_"):
                    self.fixture.task(ai_evidence=evidence)
        self.assertFalse((self.fixture.core.workspace / "terminal-tasks").exists())
        self.fixture.runner.assert_not_called()

    def test_receipt_cannot_add_authority_fields_or_unbounded_content(self):
        variants = []
        extra = deepcopy(self.evidence)
        extra["order_allowed"] = True
        variants.append(extra)
        extra = deepcopy(self.evidence)
        extra["providers"][0]["strategy_params"] = {"fast_window": 1}
        variants.append(extra)
        extra = deepcopy(self.evidence)
        extra["providers"][0]["content"] = "x" * 16001
        variants.append(extra)
        extra = deepcopy(self.evidence)
        extra["providers"].append(deepcopy(extra["providers"][0]))
        variants.append(extra)
        for evidence in variants:
            with self.subTest(evidence_keys=list(evidence)), self.assertRaises(ValueError):
                self.fixture.task(ai_evidence=evidence)
        self.assertFalse((self.fixture.core.workspace / "terminal-tasks").exists())

    def test_revision_can_remove_reference_without_rewriting_old_version(self):
        first = self.fixture.task(ai_evidence=self.evidence)
        path = self.fixture.core.workspace / "terminal-tasks" / first["family_id"] / "versions" / (first["id"] + ".json")
        before = path.read_bytes()
        second = self.fixture.task(parent_task_id=first["id"])
        self.assertEqual(second["version"], 2)
        self.assertNotIn("ai_evidence", second)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(first["ai_evidence"], self.evidence)
        self.fixture.runner.assert_not_called()


def load_tests(loader, tests, pattern):
    # Do not rerun the imported fixture's unrelated engine/kernel tests.
    return loader.loadTestsFromTestCase(TerminalAiEvidenceTests)


if __name__ == "__main__":
    unittest.main()
