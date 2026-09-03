from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
    canonical_sha256,
)
from exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 import (
    SyntheticStrategyRobustnessError,
    build_synthetic_strategy_robustness_evidence_v1,
    plan_synthetic_strategy_robustness_evidence_v1,
    render_synthetic_strategy_robustness_markdown_v1,
    replay_synthetic_strategy_robustness_evidence_v1,
    verify_synthetic_strategy_robustness_evidence_v1,
)


class SyntheticStrategyRobustnessEvidenceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.bundle = build_synthetic_strategy_robustness_evidence_v1(
            cls.source, execute=True
        )

    def test_01_plan_is_dry_and_preregisters_147_runs(self) -> None:
        plan = plan_synthetic_strategy_robustness_evidence_v1()
        self.assertEqual(plan["planned_run_count"], 147)
        self.assertEqual(len(plan["planned_runs"]), 147)
        self.assertEqual(plan["executed_run_count"], 0)
        self.assertFalse(plan["runtime_mutations"])
        self.assertFalse(plan["selection_policy"]["frozen_used_for_selection"])

    def test_02_execution_requires_exact_true_and_verified_source(self) -> None:
        for value in (False, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyRobustnessError):
                    build_synthetic_strategy_robustness_evidence_v1(
                        self.source, execute=value  # type: ignore[arg-type]
                    )
        bad_source = deepcopy(self.source)
        bad_source["authority"]["paper_authorized"] = True
        with self.assertRaises(SyntheticStrategyRobustnessError):
            build_synthetic_strategy_robustness_evidence_v1(
                bad_source, execute=True
            )

    def test_03_bundle_and_all_six_standard_evidence_objects_verify(self) -> None:
        receipt = verify_synthetic_strategy_robustness_evidence_v1(self.bundle)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["verified_run_count"], 147)
        self.assertEqual(receipt["verified_strategy_count"], 6)
        self.assertEqual(len(self.bundle["strategy_evidence"]), 6)
        self.assertTrue(all(value is False for value in self.bundle["authority"].values()))

    def test_04_walk_forward_executes_three_ordered_windows(self) -> None:
        for item in self.bundle["strategy_evidence"]:
            summary = item["validation_receipt"]["walk_forward"]
            self.assertEqual(summary["observed_count"], 3)
            self.assertEqual(summary["failed_count"], 0)
            windows = item["validation_evidence"]["walk_forward"]["windows"]
            self.assertEqual([window["window_id"] for window in windows], ["wf-01", "wf-02", "wf-03"])
            self.assertTrue(all(window["frozen_test"]["end_index"] <= 399 for window in windows))

    def test_05_center_and_neighbors_are_bound_without_frozen_selection(self) -> None:
        for item in self.bundle["strategy_evidence"]:
            self.assertTrue(item["center_binding"]["exact_match"])
            stability = item["validation_evidence"]["parameter_stability"]
            self.assertEqual(len(stability["neighbors"]), 2)
            self.assertTrue(stability["selected_parameter_id"].endswith(":center"))
            self.assertEqual(
                item["validation_evidence"]["multiple_testing"]["selected_parameter_id"],
                stability["selected_parameter_id"],
            )

    def test_06_complete_trial_and_execution_ledgers_are_retained(self) -> None:
        for item in self.bundle["strategy_evidence"]:
            self.assertEqual(len(item["run_ledger"]), 24)
            self.assertEqual(len({run["run_id"] for run in item["run_ledger"]}), 24)
            multiple = item["validation_evidence"]["multiple_testing"]
            self.assertEqual(len(multiple["preregistered_trial_ids"]), 3)
            self.assertEqual(len(multiple["trial_outcomes"]), 3)
            self.assertEqual(
                {trial["trial_id"] for trial in multiple["trial_outcomes"]},
                set(multiple["preregistered_trial_ids"]),
            )

    def test_07_multiplicity_diagnostics_are_bounded_and_keep_gaps(self) -> None:
        for item in self.bundle["strategy_evidence"]:
            diagnostics = item["multiplicity_diagnostics"]
            self.assertEqual(diagnostics["trial_count"], 3)
            self.assertEqual(len(diagnostics["trials"]), 3)
            self.assertIn("PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED", diagnostics["gaps"])
            for trial in diagnostics["trials"]:
                self.assertGreaterEqual(float(trial["bonferroni_adjusted_p"]), 0.0)
                self.assertLessEqual(float(trial["bonferroni_adjusted_p"]), 1.0)
                self.assertGreaterEqual(float(trial["benjamini_hochberg_adjusted_p"]), 0.0)
                self.assertLessEqual(float(trial["benjamini_hochberg_adjusted_p"]), 1.0)

    def test_08_renderer_is_neutral_and_preserves_remaining_gaps(self) -> None:
        markdown = render_synthetic_strategy_robustness_markdown_v1(self.bundle)
        self.assertIn("## SOURCE", markdown)
        self.assertIn("## GAP", markdown)
        self.assertIn("## MATURITY", markdown)
        self.assertIn("## PERMISSION", markdown)
        self.assertIn("MARKET_REGIME_ANALYSIS_NOT_EXECUTED", markdown)
        self.assertIn("SYNTHETIC_OBSERVATION_ONLY", markdown)
        self.assertNotIn("READY", markdown)

    def test_09_tamper_and_authority_escalation_fail_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["strategy_evidence"][0]["run_ledger"][0]["total_return"] = "999"
        self.assertEqual(
            verify_synthetic_strategy_robustness_evidence_v1(tampered)["status"],
            "BLOCK",
        )

        escalated = deepcopy(self.bundle)
        escalated["authority"]["live_authorized"] = True
        escalated["bundle_sha256"] = canonical_sha256(
            {key: value for key, value in escalated.items() if key != "bundle_sha256"}
        )
        self.assertEqual(
            verify_synthetic_strategy_robustness_evidence_v1(escalated)["status"],
            "BLOCK",
        )

    def test_10_full_147_run_replay_is_exact(self) -> None:
        receipt = replay_synthetic_strategy_robustness_evidence_v1(self.bundle)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_run_count"], 147)
        self.assertFalse(receipt["runtime_mutations"])


if __name__ == "__main__":
    unittest.main()
