from __future__ import annotations

import copy
import math
import unittest

from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (
    SyntheticStrategyCscvPboValidationError,
    build_synthetic_strategy_cscv_pbo_validation_v1,
    plan_synthetic_strategy_cscv_pbo_validation_v1,
    render_synthetic_strategy_cscv_pbo_validation_markdown_v1,
    replay_synthetic_strategy_cscv_pbo_validation_v1,
    verify_synthetic_strategy_cscv_pbo_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (
    build_synthetic_strategy_trial_return_matrix_v1,
)
from hakimi_research.cscv_pbo_diagnostic import (
    CscvPboDiagnosticError,
    build_cscv_pbo_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


class _TextAlias(str):
    pass


class SyntheticStrategyCscvPboValidationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.matrix_bundle = build_synthetic_strategy_trial_return_matrix_v1(
            cls.baseline, execute=True
        )
        cls.plan = plan_synthetic_strategy_cscv_pbo_validation_v1()
        cls.bundle = build_synthetic_strategy_cscv_pbo_validation_v1(
            cls.matrix_bundle, execute=True
        )
        cls.markdown = render_synthetic_strategy_cscv_pbo_validation_markdown_v1(
            cls.bundle
        )

    @staticmethod
    def _compound(values: list[float], indices: list[int]) -> float:
        return math.expm1(math.fsum(math.log1p(values[index]) for index in indices))

    def test_01_plan_locks_eight_partitions_seventy_splits_and_zero_runs(self) -> None:
        policy = self.plan["policy"]
        self.assertEqual(self.plan["source_required_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertEqual(policy["partition_count"], 8)
        self.assertEqual(policy["expected_combination_count"], 70)
        self.assertEqual(policy["performance_tie_policy"], "GAP_NO_ARBITRARY_RANK_NO_SPLIT_DROP")

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyCscvPboValidationError):
                    build_synthetic_strategy_cscv_pbo_validation_v1(
                        self.matrix_bundle, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_retains_four_observed_and_two_explicit_gaps(self) -> None:
        receipt = verify_synthetic_strategy_cscv_pbo_validation_v1(self.bundle)
        self.assertEqual(receipt["state"], "GAP")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["observed_evidence_count"], 4)
        self.assertEqual(receipt["gap_evidence_count"], 2)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertIsNone(receipt["decision_threshold"])

    def test_04_all_combinations_and_partition_complements_are_retained(self) -> None:
        all_partition_ids = {f"partition-{index:02d}" for index in range(1, 9)}
        for record in self.bundle["strategy_records"]:
            diagnostic = record["cscv_pbo_diagnostic"]
            combinations = set()
            for split in diagnostic["splits"]:
                is_ids = set(split["is_partition_ids"])
                oos_ids = set(split["oos_partition_ids"])
                combinations.add(tuple(split["is_partition_ids"]))
                self.assertEqual(len(is_ids), 4)
                self.assertEqual(len(oos_ids), 4)
                self.assertFalse(is_ids & oos_ids)
                self.assertEqual(is_ids | oos_ids, all_partition_ids)
                self.assertEqual(split["is_observation_count"], 84)
                self.assertEqual(split["oos_observation_count"], 84)
            self.assertEqual(len(diagnostic["splits"]), 70)
            self.assertEqual(len(combinations), 70)

    def test_05_cscv_is_combinatorially_symmetric(self) -> None:
        diagnostic = self.bundle["strategy_records"][0]["cscv_pbo_diagnostic"]
        is_counts = {f"partition-{index:02d}": 0 for index in range(1, 9)}
        oos_counts = dict(is_counts)
        is_sets = {tuple(split["is_partition_ids"]) for split in diagnostic["splits"]}
        for split in diagnostic["splits"]:
            for partition_id in split["is_partition_ids"]:
                is_counts[partition_id] += 1
            for partition_id in split["oos_partition_ids"]:
                oos_counts[partition_id] += 1
            self.assertIn(tuple(split["oos_partition_ids"]), is_sets)
        self.assertEqual(set(is_counts.values()), {35})
        self.assertEqual(set(oos_counts.values()), {35})

    def test_06_observed_splits_match_independent_performance_and_logit_formula(self) -> None:
        source_by_strategy = {
            record["strategy_id"]: record for record in self.matrix_bundle["strategy_records"]
        }
        for record in self.bundle["strategy_records"]:
            if record["evidence_state"] != "OBSERVED":
                continue
            diagnostic = record["cscv_pbo_diagnostic"]
            matrix = source_by_strategy[record["strategy_id"]]["trial_return_matrix"]
            trial_ids = matrix["preregistered_trial_ids"]
            returns = {
                row["trial_id"]: [float(value) for value in row["period_returns"][:168]]
                for row in matrix["candidate_rows"]
            }
            for split in diagnostic["splits"]:
                is_partition_indices = [int(value[-2:]) - 1 for value in split["is_partition_ids"]]
                oos_partition_indices = [int(value[-2:]) - 1 for value in split["oos_partition_ids"]]
                is_indices = [i for p in is_partition_indices for i in range(p * 21, (p + 1) * 21)]
                oos_indices = [i for p in oos_partition_indices for i in range(p * 21, (p + 1) * 21)]
                is_scores = [self._compound(returns[trial_id], is_indices) for trial_id in trial_ids]
                oos_scores = [self._compound(returns[trial_id], oos_indices) for trial_id in trial_ids]
                selected_index = max(range(3), key=lambda index: is_scores[index])
                ordered_oos = sorted(range(3), key=lambda index: oos_scores[index])
                rank = ordered_oos.index(selected_index) + 1
                omega = rank / 4.0
                expected_logit = math.log(omega / (1.0 - omega))
                self.assertEqual(split["selected_trial_id"], trial_ids[selected_index])
                self.assertEqual(split["selected_oos_rank"], rank)
                self.assertAlmostEqual(float(split["logit"]), expected_logit, places=14)
            expected_nonpositive = sum(split["logit"] <= "0" if False else float(split["logit"]) <= 0.0 for split in diagnostic["splits"])
            self.assertEqual(diagnostic["nonpositive_logit_count"], expected_nonpositive)
            self.assertAlmostEqual(
                float(diagnostic["pbo_nonpositive_logit_rate"]),
                expected_nonpositive / 70.0,
                places=14,
            )

    def test_07_rank_ties_remain_gap_without_dropped_splits_or_fake_votes(self) -> None:
        states = {record["strategy_id"]: record["evidence_state"] for record in self.bundle["strategy_records"]}
        self.assertEqual(
            {strategy for strategy, state in states.items() if state == "GAP"},
            {"dual_ma", "grid"},
        )
        for record in self.bundle["strategy_records"]:
            diagnostic = record["cscv_pbo_diagnostic"]
            if record["evidence_state"] == "GAP":
                self.assertEqual(diagnostic["gap_split_count"], 70)
                self.assertEqual(diagnostic["observed_split_count"], 0)
                self.assertIsNone(diagnostic["pbo_nonpositive_logit_rate"])
                self.assertTrue(
                    all(split["gap_code"] == "NON_UNIQUE_CSCV_PERFORMANCE_RANK" for split in diagnostic["splits"])
                )
            else:
                self.assertEqual(diagnostic["gap_split_count"], 0)
                self.assertEqual(diagnostic["observed_split_count"], 70)

    def test_08_trailing_exclusion_is_explicit_and_source_bound(self) -> None:
        for record in self.bundle["strategy_records"]:
            diagnostic = record["cscv_pbo_diagnostic"]
            self.assertEqual(diagnostic["source_observation_count"], 169)
            self.assertEqual(diagnostic["usable_observation_count"], 168)
            self.assertEqual(diagnostic["excluded_observation_count"], 1)
            excluded = diagnostic["excluded_observations"]
            self.assertEqual(len(excluded), 1)
            self.assertEqual(excluded[0]["source_observation_index"], 168)
            self.assertRegex(
                diagnostic["source_binding"]["excluded_observations_sha256"],
                r"^[0-9a-f]{64}$",
            )

    def test_09_missing_or_overlapping_split_tamper_fails_closed(self) -> None:
        for mutation in ("missing", "overlap"):
            tampered = copy.deepcopy(self.bundle)
            splits = tampered["strategy_records"][0]["cscv_pbo_diagnostic"]["splits"]
            if mutation == "missing":
                splits.pop()
            else:
                splits[0]["oos_partition_ids"][0] = splits[0]["is_partition_ids"][0]
            with self.subTest(mutation=mutation):
                with self.assertRaises(SyntheticStrategyCscvPboValidationError):
                    verify_synthetic_strategy_cscv_pbo_validation_v1(tampered)

    def test_10_exact_native_subclass_is_rejected(self) -> None:
        matrix = copy.deepcopy(
            self.matrix_bundle["strategy_records"][0]["trial_return_matrix"]
        )
        matrix["selected_trial_id"] = _TextAlias(matrix["selected_trial_id"])
        with self.assertRaises(CscvPboDiagnosticError):
            build_cscv_pbo_diagnostic(matrix)

    def test_11_authority_escalation_fails_even_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        tampered["bundle_sha256"] = canonical_trial_return_matrix_sha256(
            {
                key: value
                for key, value in tampered.items()
                if key != "bundle_sha256"
            }
        )
        with self.assertRaises(SyntheticStrategyCscvPboValidationError):
            verify_synthetic_strategy_cscv_pbo_validation_v1(tampered)

    def test_12_replay_and_renderer_are_zero_run_and_neutral(self) -> None:
        receipt = replay_synthetic_strategy_cscv_pbo_validation_v1(self.bundle)
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("Rank ties remain GAP", self.markdown)
        self.assertIn("without a decision threshold", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
