import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / "tools/review_current_study.py"
spec = importlib.util.spec_from_file_location("current_study_review", path)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def report():
    return {"spec": {"fixed": True}, "dataset": {"data_hash": "a" * 64},
            "report_hash": "b" * 64, "result_hash": "c" * 64,
            "result": {**{field: 0 for field in review.METRICS}, "fills": [{"price": 95}],
                       "orders": [], "equity_curve": [{"equity": 100}], "return_series": []}}


class StudyReviewTests(unittest.TestCase):
    def test_duplicate_or_missing_cells_are_not_a_complete_study(self):
        rows = [{"strategy": strategy, "cell": cell, "cost_factor": factor, "returncode": 0,
                 "spec_hash": f"{index:064x}"} for index, (strategy, cell, factor) in enumerate(sorted(review.EXPECTED_CELLS))]
        study = {"planned_attempt_count": 16, "actual_attempt_count": 16, "attempts": rows}
        self.assertEqual(len(review.validate_study(study)), 16)
        duplicate = copy.deepcopy(study)
        duplicate["attempts"][-1] = duplicate["attempts"][0]
        with self.assertRaisesRegex(ValueError, "unique"):
            review.validate_study(duplicate)
        missing = copy.deepcopy(study)
        missing["attempts"].pop()
        with self.assertRaisesRegex(ValueError, "complete_16"):
            review.validate_study(missing)

    def test_reason_only_change_is_not_claimed_as_economic_change(self):
        old, current = report(), report()
        current["result"]["fills"][0]["reason"] = "known opening protection"
        difference = review.compare(old, current)
        self.assertEqual(difference["changed_record_counts"]["fills"], 1)
        self.assertFalse(difference["economic_path_changed"])

    def test_same_return_does_not_hide_different_trade_paths(self):
        old = report()
        current = copy.deepcopy(old)
        current["result"]["fills"][0]["price"] = 97
        difference = review.compare(old, current)
        self.assertEqual(difference["metric_deltas"]["total_return"], 0)
        self.assertEqual(difference["changed_record_counts"]["fills"], 1)
        self.assertEqual(difference["changed_records"]["fills"][0]["old"]["price"], 95)

    def test_deleted_trailing_events_are_reported(self):
        old, current = report(), report()
        current["result"]["fills"] = []
        change = review.compare(old, current)["changed_records"]["fills"][0]
        self.assertIsNone(change["current"])

    def test_cross_version_data_or_spec_change_is_not_a_like_for_like_comparison(self):
        for field in ("spec", "dataset"):
            old, current = report(), report()
            current[field] = {"data_hash": "d" * 64}
            with self.assertRaisesRegex(ValueError, "identical_spec_and_data"):
                review.compare(old, current)


if __name__ == "__main__":
    unittest.main()
