from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.synthetic_strategy_bootstrap_validation_v1 import (
    SyntheticStrategyBootstrapValidationError,
    build_synthetic_strategy_bootstrap_validation_v1,
    plan_synthetic_strategy_bootstrap_validation_v1,
    render_synthetic_strategy_bootstrap_validation_markdown_v1,
    verify_synthetic_strategy_bootstrap_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)


class SyntheticStrategyBootstrapValidationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.plan = plan_synthetic_strategy_bootstrap_validation_v1()
        cls.bundle = build_synthetic_strategy_bootstrap_validation_v1(
            cls.baseline, execute=True
        )
        cls.markdown = render_synthetic_strategy_bootstrap_validation_markdown_v1(
            cls.bundle, cls.baseline
        )

    def test_01_plan_adds_six_analyses_and_zero_backtest_runs(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 32)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyBootstrapValidationError):
                    build_synthetic_strategy_bootstrap_validation_v1(
                        self.baseline, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_and_all_six_evidence_objects_verify(self) -> None:
        receipt = verify_synthetic_strategy_bootstrap_validation_v1(
            self.bundle, self.baseline
        )
        self.assertEqual(receipt["state"], "OBSERVED")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["observed_evidence_count"], 6)
        self.assertEqual(receipt["gap_evidence_count"], 0)

    def test_04_policy_is_fixed_deterministic_and_non_inferential(self) -> None:
        policy = self.plan["policy"]
        self.assertEqual(policy["block_length"], 5)
        self.assertEqual(policy["replicate_count"], 1000)
        self.assertEqual(policy["confidence_level"], "0.95")
        self.assertEqual(policy["quantile_method"], "LINEAR_TYPE_7")
        self.assertEqual(
            policy["seed_derivation"], "SHA256_SOURCE_BOUND_BLOCK_START_V1"
        )
        self.assertFalse(policy["formal_inference_claimed"])
        self.assertFalse(policy["performance_selection_used"])
        self.assertFalse(policy["post_observation_policy_tuning"])

    def test_05_all_records_have_169_pairs_and_three_decimal_intervals(self) -> None:
        for record in self.bundle["strategy_records"]:
            with self.subTest(strategy_id=record["strategy_id"]):
                receipt = record["bootstrap_receipt"]
                self.assertEqual(receipt["state"], "OBSERVED")
                self.assertEqual(receipt["paired_observation_count"], 169)
                self.assertEqual(receipt["replicate_count"], 1000)
                self.assertEqual(receipt["interval_count"], 3)
                for interval in record["bootstrap_evidence"]["intervals"]:
                    self.assertIsInstance(interval["lower_bound"], str)
                    self.assertIsInstance(interval["median"], str)
                    self.assertIsInstance(interval["upper_bound"], str)

    def test_06_source_and_distribution_hashes_are_bound(self) -> None:
        for record in self.bundle["strategy_records"]:
            with self.subTest(strategy_id=record["strategy_id"]):
                evidence = record["bootstrap_evidence"]
                self.assertRegex(evidence["evidence_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(
                    evidence["seed_material_sha256"], r"^[0-9a-f]{64}$"
                )
                for interval in evidence["intervals"]:
                    self.assertRegex(
                        interval["distribution_sha256"], r"^[0-9a-f]{64}$"
                    )

    def test_07_replay_is_exact_without_additional_backtests(self) -> None:
        replay = build_synthetic_strategy_bootstrap_validation_v1(
            self.baseline, execute=True
        )
        self.assertEqual(replay, self.bundle)
        self.assertEqual(replay["planned_run_count"], 0)
        self.assertEqual(replay["executed_run_count"], 0)

    def test_08_nested_interval_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["strategy_records"][0]["bootstrap_evidence"]["intervals"][0][
            "lower_bound"
        ] = "999"
        with self.assertRaises(SyntheticStrategyBootstrapValidationError):
            verify_synthetic_strategy_bootstrap_validation_v1(
                tampered, self.baseline
            )

    def test_09_authority_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        with self.assertRaises(SyntheticStrategyBootstrapValidationError):
            verify_synthetic_strategy_bootstrap_validation_v1(
                tampered, self.baseline
            )

    def test_10_renderer_is_neutral_and_disclaims_formal_inference(self) -> None:
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("Formal inference authority: false", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
