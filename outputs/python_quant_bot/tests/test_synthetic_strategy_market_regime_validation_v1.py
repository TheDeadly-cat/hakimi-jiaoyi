from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.synthetic_strategy_market_regime_validation_v1 import (
    SyntheticStrategyMarketRegimeValidationError,
    build_synthetic_strategy_market_regime_validation_v1,
    plan_synthetic_strategy_market_regime_validation_v1,
    render_synthetic_strategy_market_regime_validation_markdown_v1,
    verify_synthetic_strategy_market_regime_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 import (
    build_synthetic_strategy_robustness_evidence_v1,
)


class SyntheticStrategyMarketRegimeValidationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.robustness = build_synthetic_strategy_robustness_evidence_v1(
            cls.baseline, execute=True
        )
        cls.plan = plan_synthetic_strategy_market_regime_validation_v1()
        cls.bundle = build_synthetic_strategy_market_regime_validation_v1(
            cls.baseline, cls.robustness, execute=True
        )
        cls.markdown = (
            render_synthetic_strategy_market_regime_validation_markdown_v1(
                cls.bundle, cls.baseline, cls.robustness
            )
        )

    def test_01_plan_adds_six_analyses_and_zero_backtest_runs(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 179)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyMarketRegimeValidationError):
                    build_synthetic_strategy_market_regime_validation_v1(
                        self.baseline,
                        self.robustness,
                        execute=value,  # type: ignore[arg-type]
                    )

    def test_03_bundle_and_all_standard_validation_objects_verify(self) -> None:
        receipt = verify_synthetic_strategy_market_regime_validation_v1(
            self.bundle, self.baseline, self.robustness
        )
        self.assertEqual(receipt["state"], "GAP")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["planned_run_count"], 0)
        self.assertEqual(receipt["executed_run_count"], 0)

    def test_04_each_strategy_observes_three_regimes_and_keeps_high_vol_gap(self) -> None:
        for record in self.bundle["strategy_records"]:
            with self.subTest(strategy_id=record["strategy_id"]):
                receipt = record["market_regime_receipt"]
                self.assertEqual(receipt["observed_count"], 3)
                self.assertEqual(receipt["gap_count"], 1)
                self.assertEqual(
                    record["validation_receipt"]["market_regimes"],
                    {"state": "GAP", "observed_count": 3, "gap_count": 1},
                )
                observations = record["market_regime_evidence"]["observations"]
                consumer_slices = record["market_regime_evidence"]["consumer_view"][
                    "slices"
                ]
                for consumer_slice in consumer_slices:
                    if consumer_slice["status"] == "OBSERVED":
                        self.assertIsInstance(
                            consumer_slice["strategy_total_return"], str
                        )
                        self.assertIsInstance(
                            consumer_slice["benchmark_total_return"], str
                        )
                high_vol = next(
                    item
                    for item in observations
                    if item["regime_id"] == "HIGH_VOLATILITY"
                )
                self.assertEqual(high_vol["status"], "GAP")
                self.assertEqual(high_vol["observation_count"], 0)

    def test_05_policy_is_fixed_causal_and_not_performance_tuned(self) -> None:
        policy = self.plan["policy"]
        self.assertEqual(policy["lookback_bars"], 20)
        self.assertEqual(policy["label_lag_bars"], 1)
        self.assertEqual(policy["high_volatility_annualized_threshold"], 0.20)
        self.assertFalse(policy["performance_selection_used"])
        self.assertFalse(policy["threshold_tuning_after_observation"])

    def test_06_source_hashes_and_observation_hashes_are_bound(self) -> None:
        for record in self.bundle["strategy_records"]:
            with self.subTest(strategy_id=record["strategy_id"]):
                evidence = record["market_regime_evidence"]
                self.assertRegex(evidence["evidence_sha256"], r"^[0-9a-f]{64}$")
                for observation in evidence["observations"]:
                    if observation["status"] == "OBSERVED":
                        self.assertRegex(
                            observation["observation_sha256"], r"^[0-9a-f]{64}$"
                        )

    def test_07_non_regime_evidence_and_frozen_selection_are_unchanged(self) -> None:
        source_by_id = {
            record["strategy_id"]: record
            for record in self.robustness["strategy_evidence"]
        }
        preserved = (
            "formal_search_lineage",
            "distribution_evidence",
            "walk_forward",
            "parameter_stability",
            "multiple_testing",
            "authority",
        )
        for record in self.bundle["strategy_records"]:
            source = source_by_id[record["strategy_id"]]["validation_evidence"]
            current = record["validation_evidence"]
            with self.subTest(strategy_id=record["strategy_id"]):
                for key in preserved:
                    self.assertEqual(current[key], source[key])

    def test_08_nested_observation_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        observed = next(
            item
            for item in tampered["strategy_records"][0]["market_regime_evidence"][
                "observations"
            ]
            if item["status"] == "OBSERVED"
        )
        observed["strategy_total_return"] += 0.01
        with self.assertRaises(SyntheticStrategyMarketRegimeValidationError):
            verify_synthetic_strategy_market_regime_validation_v1(
                tampered, self.baseline, self.robustness
            )

    def test_09_authority_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        with self.assertRaises(SyntheticStrategyMarketRegimeValidationError):
            verify_synthetic_strategy_market_regime_validation_v1(
                tampered, self.baseline, self.robustness
            )

    def test_10_replay_and_renderer_are_deterministic_and_neutral(self) -> None:
        replay = build_synthetic_strategy_market_regime_validation_v1(
            self.baseline, self.robustness, execute=True
        )
        self.assertEqual(replay, self.bundle)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertNotIn("READY", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
