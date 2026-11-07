"""Saved financial projection only: no engine, market request or stored writes."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.terminal_result_presentation import core_result_detail, project_core_result_detail, present_core_run_completion


class CoreResultPresentationTests(unittest.TestCase):
    def fixture(self):
        identity = "a" * 24
        ids = {"run_id": "b" * 64, "task_id": "saved-task", "report_hash": "c" * 64}
        detail = {"id": identity, "identities": ids, "summary": {"total_return": .1235, "net_pnl": 1234.56},
                  "configuration": {"requested": {"initial_cash": 10000}}, "equity_curve": [{"equity": 11234.56, "cash": 7234.56, "position_value": 4000}], "new_economic_runs": 0}
        verified = {"id": identity, "verification_status": "VERIFIED_RECORD", "manifest": {"run_id": ids["run_id"], "task_id": ids["task_id"]},
                    "report": {"report_hash": ids["report_hash"], "dataset": {"security": {"currency": "USD"}},
                               "result": {"execution_model": "saved-model", "metric_semantics_version": "saved-metrics", "round_trip_count": 0}}}
        return detail, verified

    def test_saved_values_units_and_original_objects_are_preserved(self):
        detail, verified = self.fixture()
        originals = deepcopy((detail, verified))
        result = project_core_result_detail(detail, verified)
        self.assertEqual(result["summary"], {**detail["summary"], **verified["report"]["result"], "currency": "USD"})
        self.assertEqual(result["equity_curve"], detail["equity_curve"])
        self.assertEqual(result["configuration"], detail["configuration"])
        self.assertEqual((detail, verified), originals)
        self.assertEqual(result["new_economic_runs"], 0)

    def test_old_missing_facts_stay_absent_without_inferred_currency_or_model(self):
        detail, verified = self.fixture()
        verified["report"].pop("dataset")
        verified["report"]["result"] = {}
        result = project_core_result_detail(detail, verified)
        self.assertEqual(result["summary"], detail["summary"])

    def test_mismatched_report_or_conflicting_fact_is_rejected(self):
        detail, verified = self.fixture()
        for key in detail["identities"]:
            changed = deepcopy(detail);changed["identities"][key] = "other"
            with self.assertRaisesRegex(ValueError, "report_changed"):
                project_core_result_detail(changed, verified)
        detail["summary"]["currency"] = "EUR"
        with self.assertRaisesRegex(ValueError, "saved_fact_conflict"):
            project_core_result_detail(detail, verified)

    def test_read_adapter_uses_original_identifier_without_mutation(self):
        detail, verified = self.fixture()
        core = Mock();core.read.return_value = detail
        service = SimpleNamespace(core=core)
        with patch("exchange_terminal.services.terminal_result_presentation.verified_saved_result", return_value=verified) as read:
            result = core_result_detail(service, detail["id"])
        core.read.assert_called_once_with("runs", detail["id"])
        read.assert_called_once_with(service, {"kind": "core_run", "id": detail["id"]})
        core.mutate.assert_not_called()
        self.assertEqual(result["id"], detail["id"])

    def test_completed_mutation_retains_original_success_when_auxiliary_read_fails(self):
        detail, _ = self.fixture(); detail["new_economic_runs"] = 1
        before = deepcopy(detail)
        service = Mock()
        with patch("exchange_terminal.services.terminal_result_presentation.verified_saved_result", side_effect=OSError("fixture read failure")):
            result = present_core_run_completion(service, detail)
        self.assertEqual({k:v for k,v in result.items() if k != "presentation_warnings"}, before)
        self.assertIn("不要重复运行", result["presentation_warnings"][0])
        self.assertEqual(detail, before)
        service.core.mutate.assert_not_called()

    def test_completed_mutation_keeps_its_actual_run_count_after_projection(self):
        detail, verified = self.fixture();detail["new_economic_runs"] = 1
        with patch("exchange_terminal.services.terminal_result_presentation.verified_saved_result", return_value=verified):
            result = present_core_run_completion(Mock(), detail)
        self.assertEqual(result["new_economic_runs"], 1)
        self.assertEqual(result["summary"]["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
