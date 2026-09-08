from __future__ import annotations

import copy
import math
import unittest

from exchange_terminal.application.synthetic_strategy_cscv_pbo_tie_bounds_v1 import (
    SyntheticStrategyCscvPboTieBoundsError,
    build_synthetic_strategy_cscv_pbo_tie_bounds_v1,
    plan_synthetic_strategy_cscv_pbo_tie_bounds_v1,
    render_synthetic_strategy_cscv_pbo_tie_bounds_markdown_v1,
    replay_synthetic_strategy_cscv_pbo_tie_bounds_v1,
    verify_synthetic_strategy_cscv_pbo_tie_bounds_v1,
)
from hakimi_research.cscv_pbo_tie_bounds import (
    CscvPboTieBoundsError,
    build_cscv_pbo_tie_bounds,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


class _TextAlias(str):
    pass


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = canonical_trial_return_matrix_sha256(unsigned)


class SyntheticStrategyCscvPboTieBoundsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_cscv_pbo_validation_v1 import (
            SyntheticStrategyCscvPboValidationV1Tests,
        )

        SyntheticStrategyCscvPboValidationV1Tests.setUpClass()
        cls.source = SyntheticStrategyCscvPboValidationV1Tests.bundle
        cls.plan = plan_synthetic_strategy_cscv_pbo_tie_bounds_v1()
        cls.bundle = build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
            cls.source, execute=True
        )
        cls.receipt = verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(
            cls.bundle
        )
        cls.markdown = render_synthetic_strategy_cscv_pbo_tie_bounds_markdown_v1(
            cls.bundle
        )

    def test_01_plan_is_preregistered_zero_run_consumer(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        policy = self.plan["policy"]
        self.assertFalse(policy["arbitrary_tie_breaking"])
        self.assertFalse(policy["interval_midpoint_reported_as_pbo"])
        self.assertFalse(policy["split_drop_allowed"])

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyCscvPboTieBoundsError):
                    build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
                        self.source, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_distinguishes_point_partial_and_full_bounds(self) -> None:
        self.assertEqual(self.receipt["state"], "OBSERVED_WITH_GAPS")
        self.assertEqual(self.receipt["point_identified_evidence_count"], 4)
        self.assertEqual(self.receipt["partial_interval_evidence_count"], 1)
        self.assertEqual(self.receipt["full_unit_interval_evidence_count"], 1)
        self.assertEqual(self.receipt["executed_analysis_count"], 6)
        self.assertEqual(self.receipt["executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertFalse(self.receipt["formal_inference_claimed"])

    def test_04_all_420_split_bounds_match_independent_formula(self) -> None:
        source_by_id = {
            record["strategy_id"]: record for record in self.source["strategy_records"]
        }
        for record in self.bundle["strategy_records"]:
            source_splits = source_by_id[record["strategy_id"]][
                "cscv_pbo_diagnostic"
            ]["splits"]
            bounds_splits = record["tie_bounds_diagnostic"]["split_bounds"]
            self.assertEqual(len(bounds_splits), 70)
            for source_split, bounds in zip(source_splits, bounds_splits):
                is_scores = [
                    float(item["compounded_total_return"])
                    for item in source_split["is_performance"]
                ]
                oos_scores = [
                    float(item["compounded_total_return"])
                    for item in source_split["oos_performance"]
                ]
                maximum = max(is_scores)
                selected = [
                    index for index, score in enumerate(is_scores)
                    if score == maximum
                ]
                lower = min(
                    1 + sum(score < oos_scores[index] for score in oos_scores)
                    for index in selected
                )
                upper = max(
                    sum(score <= oos_scores[index] for score in oos_scores)
                    for index in selected
                )
                self.assertEqual(bounds["oos_rank_lower"], lower)
                self.assertEqual(bounds["oos_rank_upper"], upper)
                self.assertEqual(
                    bounds["nonpositive_lower_indicator"], upper <= 2
                )
                self.assertEqual(
                    bounds["nonpositive_upper_indicator"], lower <= 2
                )

    def test_05_previously_observed_pbo_collapses_to_exact_points(self) -> None:
        source_by_id = {
            record["strategy_id"]: record for record in self.source["strategy_records"]
        }
        for record in self.bundle["strategy_records"]:
            if record["bound_quality"] != "POINT_IDENTIFIED":
                continue
            diagnostic = record["tie_bounds_diagnostic"]
            source_diagnostic = source_by_id[record["strategy_id"]][
                "cscv_pbo_diagnostic"
            ]
            lower = float(diagnostic["pbo_nonpositive_logit_lower_bound"])
            upper = float(diagnostic["pbo_nonpositive_logit_upper_bound"])
            self.assertEqual(lower, upper)
            self.assertAlmostEqual(
                lower,
                float(source_diagnostic["pbo_nonpositive_logit_rate"]),
                places=14,
            )

    def test_06_dual_ma_remains_honestly_uninformative(self) -> None:
        record = next(
            item for item in self.bundle["strategy_records"]
            if item["strategy_id"] == "dual_ma"
        )
        diagnostic = record["tie_bounds_diagnostic"]
        self.assertEqual(record["bound_quality"], "FULL_UNIT_INTERVAL")
        self.assertEqual(
            float(diagnostic["pbo_nonpositive_logit_lower_bound"]), 0.0
        )
        self.assertEqual(
            float(diagnostic["pbo_nonpositive_logit_upper_bound"]), 1.0
        )
        self.assertEqual(diagnostic["ambiguous_cross_zero_count"], 70)

    def test_07_grid_retains_informative_conservative_lower_bound(self) -> None:
        record = next(
            item for item in self.bundle["strategy_records"]
            if item["strategy_id"] == "grid"
        )
        diagnostic = record["tie_bounds_diagnostic"]
        self.assertEqual(record["bound_quality"], "PARTIAL_IDENTIFIED_SET")
        self.assertEqual(diagnostic["definite_nonpositive_count"], 48)
        self.assertEqual(diagnostic["ambiguous_cross_zero_count"], 22)
        self.assertAlmostEqual(
            float(diagnostic["pbo_nonpositive_logit_lower_bound"]),
            48 / 70,
            places=14,
        )
        self.assertEqual(
            float(diagnostic["pbo_nonpositive_logit_upper_bound"]), 1.0
        )

    def test_08_source_identity_and_all_splits_are_bound(self) -> None:
        self.assertEqual(
            self.bundle["source_cscv_bundle_sha256"],
            self.source["bundle_sha256"],
        )
        for record in self.bundle["strategy_records"]:
            diagnostic = record["tie_bounds_diagnostic"]
            self.assertEqual(diagnostic["retained_split_count"], 70)
            self.assertRegex(diagnostic["source_diagnostic_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(
                all(
                    split["source_split_sha256"]
                    for split in diagnostic["split_bounds"]
                )
            )

    def test_09_resealed_bound_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        record = tampered["strategy_records"][0]
        diagnostic = record["tie_bounds_diagnostic"]
        split = diagnostic["split_bounds"][0]
        split["oos_rank_lower"] = 1
        _reseal(split, "split_bounds_sha256")
        _reseal(diagnostic, "diagnostic_sha256")
        _reseal(record, "record_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyCscvPboTieBoundsError):
            verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(tampered)

    def test_10_exact_native_subclass_is_rejected(self) -> None:
        source = copy.deepcopy(
            self.source["strategy_records"][0]["cscv_pbo_diagnostic"]
        )
        source["strategy_id"] = _TextAlias(source["strategy_id"])
        with self.assertRaises(CscvPboTieBoundsError):
            build_cscv_pbo_tie_bounds(source)

    def test_11_authority_escalation_fails_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyCscvPboTieBoundsError):
            verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(tampered)

    def test_12_replay_and_renderer_are_zero_run_and_neutral(self) -> None:
        receipt = replay_synthetic_strategy_cscv_pbo_tie_bounds_v1(self.bundle)
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("No arbitrary tie-break", self.markdown)
        self.assertIn("Full-unit bounds remain explicitly uninformative", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
