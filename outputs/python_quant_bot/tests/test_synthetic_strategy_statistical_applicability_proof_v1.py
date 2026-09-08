from __future__ import annotations

import copy
import unittest

from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256
from hakimi_research.synthetic_strategy_statistical_applicability_proof import (
    SyntheticStrategyStatisticalApplicabilityProofError,
    build_default_synthetic_strategy_statistical_applicability_proof_v1,
    build_synthetic_strategy_statistical_applicability_proof_v1,
    plan_synthetic_strategy_statistical_applicability_proof_v1,
    render_synthetic_strategy_statistical_applicability_proof_markdown_v1,
    verify_synthetic_strategy_statistical_applicability_proof_v1,
)


class SyntheticStrategyStatisticalApplicabilityProofV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = (
            build_default_synthetic_strategy_statistical_applicability_proof_v1(
                execute=True
            )
        )
        cls.receipt = (
            verify_synthetic_strategy_statistical_applicability_proof_v1(
                cls.bundle
            )
        )

    def test_01_plan_registers_358_sources_and_zero_statistical_backtests(self) -> None:
        plan = plan_synthetic_strategy_statistical_applicability_proof_v1()
        self.assertEqual(plan["source_executed_run_count"], 358)
        self.assertEqual(plan["statistical_additional_backtest_run_count"], 0)
        self.assertEqual(plan["matrix_candidate_count"], 18)
        self.assertEqual(plan["bootstrap_interval_value_count"], 54)

    def test_02_four_non_bootstrap_stage_projections_are_exact(self) -> None:
        expected = {
            "matrix": "ac6274c546702d34768ebd4d677825a61c84ca5183f54cd0e6b26c5d39a0ca54",
            "dsr": "b60ff46d13a55d7f5211d5bd66d20b1149218ac5ce3aec00e5dce77dd18bc5a3",
            "pbo": "723983dd0b877fa624475b0abc881712f0c276be90dd8bb540febece9602f759",
            "tie": "5b34f111a9112811fced90fceb26eb6d8daa604414cb6cc4c5d768463129ed7f",
        }
        for stage, digest in expected.items():
            with self.subTest(stage=stage):
                self.assertEqual(
                    self.receipt["bindings"]["stages"][stage][
                        "outcome_projection_sha256"
                    ],
                    digest,
                )

    def test_03_non_bootstrap_numerical_applicability_is_true(self) -> None:
        self.assertTrue(self.receipt["matrix_outcome_applicability_proven"])
        self.assertTrue(self.receipt["dsr_numerical_applicability_proven"])
        self.assertTrue(self.receipt["pbo_numerical_applicability_proven"])
        self.assertTrue(
            self.receipt["tie_bounds_numerical_applicability_proven"]
        )
        self.assertEqual(self.receipt["matrix_candidate_count"], 18)
        self.assertEqual(
            self.receipt["canonical_retained_split_bound_count"], 420
        )

    def test_04_bootstrap_numerical_applicability_remains_false(self) -> None:
        self.assertFalse(
            self.receipt["bootstrap_numerical_applicability_proven"]
        )
        self.assertEqual(self.receipt["bootstrap_interval_value_count"], 54)
        self.assertEqual(
            self.receipt["bootstrap_differing_interval_value_count"], 53
        )
        self.assertEqual(
            self.receipt["bootstrap_equal_interval_value_count"], 1
        )
        self.assertEqual(self.receipt["bootstrap_differing_seed_count"], 6)
        self.assertFalse(
            self.receipt["full_statistical_reference_applicability_proven"]
        )

    def test_05_ledger_and_full_report_alignment_remain_false(self) -> None:
        self.assertTrue(
            self.receipt["canonical_reproducibility_ledger_verified"]
        )
        self.assertFalse(self.receipt["statistical_ledger_alignment_proven"])
        self.assertFalse(self.receipt["full_report_alignment_proven"])
        self.assertFalse(self.receipt["run_accounting_additive"])
        self.assertEqual(self.receipt["status"], "BLOCK")

    def test_06_execute_flag_and_missing_sources_fail_closed(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_statistical_applicability_proof_v1(
                        execute=value  # type: ignore[arg-type]
                    )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_statistical_applicability_proof_v1(
                execute=True
            )

    def test_07_resealed_stage_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["bindings"]["stages"]["dsr"][
            "outcome_projection_sha256"
        ] = "f" * 64
        unsigned = {
            key: value for key, value in tampered.items() if key != "bundle_sha256"
        }
        tampered["bundle_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(SyntheticStrategyStatisticalApplicabilityProofError):
            verify_synthetic_strategy_statistical_applicability_proof_v1(
                tampered
            )

    def test_08_resealed_false_applicability_upgrades_fail_closed(self) -> None:
        for field in (
            "bootstrap_numerical_applicability_proven",
            "full_statistical_reference_applicability_proven",
            "statistical_ledger_alignment_proven",
            "full_report_alignment_proven",
            "run_accounting_additive",
        ):
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.bundle)
                tampered[field] = True
                unsigned = {
                    key: value
                    for key, value in tampered.items()
                    if key != "bundle_sha256"
                }
                tampered["bundle_sha256"] = canonical_sha256(unsigned)
                with self.assertRaises(
                    SyntheticStrategyStatisticalApplicabilityProofError
                ):
                    verify_synthetic_strategy_statistical_applicability_proof_v1(
                        tampered
                    )

    def test_09_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_statistical_applicability_proof_v1(
                DictAlias(self.bundle)
            )
        escalated = copy.deepcopy(self.bundle)
        escalated["authority"]["profitability_proven"] = True
        unsigned = {
            key: value for key, value in escalated.items() if key != "bundle_sha256"
        }
        escalated["bundle_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(SyntheticStrategyStatisticalApplicabilityProofError):
            verify_synthetic_strategy_statistical_applicability_proof_v1(
                escalated
            )

    def test_10_renderer_is_neutral_and_preserves_mixed_result(self) -> None:
        markdown = (
            render_synthetic_strategy_statistical_applicability_proof_markdown_v1(
                self.bundle
            )
        )
        self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
        self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
        self.assertLess(
            markdown.index("## MATURITY"), markdown.index("## PERMISSION")
        )
        self.assertIn("DSR numerical applicability proven: TRUE", markdown)
        self.assertIn("Bootstrap numerical applicability proven: FALSE", markdown)
        self.assertIn(
            "Full statistical reference applicability proven: FALSE", markdown
        )
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
