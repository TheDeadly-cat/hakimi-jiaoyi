from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_robustness import (
    build_robustness_assessment,
    fixed_parameter_stress_cases,
    verify_robustness_report,
)


def result(label: str, *, positive: bool = True, partial_fills: int = 0) -> dict[str, object]:
    return {
        "label": label,
        "ok": True,
        "total_return_pct": 5.0 if positive else -1.0,
        "max_drawdown_pct": 8.0,
        "partial_fill_count": partial_fills,
        "schedule_status": "PASS",
        "run_hash": f"hash-{label}",
    }


class PortfolioRobustnessTests(unittest.TestCase):
    def test_parameter_stress_grid_is_fixed_and_bounded(self) -> None:
        cases = fixed_parameter_stress_cases({"lookback": 126})

        self.assertEqual(len(cases), 7)
        self.assertEqual(cases[0]["label"], "BASELINE")
        self.assertEqual(len({case["label"] for case in cases}), 7)

    def test_assessment_passes_without_granting_execution_authority(self) -> None:
        parameter_results = [result(f"P{index}") for index in range(7)]
        ablation_results = [result(f"A{index}") for index in range(8)]
        capital_results = [
            result("CAPITAL_100K"),
            result("CAPITAL_1M"),
            result("CAPITAL_10M", partial_fills=2),
        ]

        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=parameter_results,
            ablation_results=ablation_results,
            capital_results=capital_results,
            candidate_verification={"status": "PASS"},
        )
        verification = verify_robustness_report(report, candidate_hash="candidate")

        self.assertEqual(report["status"], "ROBUSTNESS_PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(report["parameter_selection_allowed"])
        self.assertFalse(report["paper_authorized"])

    def test_zero_drawdown_is_preserved_as_a_valid_bounded_result(self) -> None:
        parameter_results = [result(f"P{index}") for index in range(7)]
        for item in parameter_results:
            item["max_drawdown_pct"] = 0.0

        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=parameter_results,
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_PASS")
        self.assertEqual(report["parameter_summary"]["positive_bounded_count"], 7)

    def test_assessment_blocks_a_fragile_parameter_neighborhood(self) -> None:
        parameter_results = [result(f"P{index}", positive=index < 4) for index in range(7)]
        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=parameter_results,
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_BLOCK")
        self.assertFalse(report["checks"]["parameter_neighborhood_positive_at_least_5_of_7"])

    def test_report_tampering_is_detected(self) -> None:
        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=[result(f"P{index}") for index in range(7)],
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )
        report["checks"]["candidate_hash_present"] = False

        verification = verify_robustness_report(report, candidate_hash="candidate")

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("robustness_hash_mismatch", verification["blockers"])

    def test_boolean_metrics_and_string_status_do_not_pass_robustness(self) -> None:
        parameter_results = [result(f"P{index}") for index in range(7)]
        for item in parameter_results:
            item["total_return_pct"] = True
            item["ok"] = "true"
        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=parameter_results,
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_BLOCK")
        self.assertEqual(report["parameter_summary"]["positive_bounded_count"], 0)


if __name__ == "__main__":
    unittest.main()
