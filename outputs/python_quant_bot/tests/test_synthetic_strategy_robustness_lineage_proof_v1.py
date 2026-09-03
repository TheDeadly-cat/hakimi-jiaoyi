from __future__ import annotations

import copy
import unittest

from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256
from hakimi_research.synthetic_strategy_robustness_lineage_proof import (
    SyntheticStrategyRobustnessLineageProofError,
    build_default_synthetic_strategy_robustness_lineage_proof_v1,
    build_synthetic_strategy_robustness_lineage_proof_v1,
    plan_synthetic_strategy_robustness_lineage_proof_v1,
    render_synthetic_strategy_robustness_lineage_proof_markdown_v1,
    verify_synthetic_strategy_robustness_lineage_proof_v1,
)


class SyntheticStrategyRobustnessLineageProofV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_default_synthetic_strategy_robustness_lineage_proof_v1(
            execute=True
        )
        cls.receipt = verify_synthetic_strategy_robustness_lineage_proof_v1(
            cls.bundle
        )

    def test_01_plan_registers_358_sources_and_zero_comparison(self) -> None:
        plan = plan_synthetic_strategy_robustness_lineage_proof_v1()
        self.assertEqual(plan["legacy_baseline_run_count"], 32)
        self.assertEqual(plan["legacy_robustness_run_count"], 147)
        self.assertEqual(plan["canonical_baseline_run_count"], 32)
        self.assertEqual(plan["canonical_robustness_run_count"], 147)
        self.assertEqual(plan["source_executed_run_count"], 358)
        self.assertEqual(plan["aligned_outcome_pair_count"], 147)
        self.assertEqual(plan["comparison_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)

    def test_02_source_projection_and_ledger_identities_are_exact(self) -> None:
        self.assertEqual(
            self.receipt["legacy_v1_robustness_bundle_sha256"],
            "a45545477289b8ad8f85fb6a5e6bb025665ba8be2468e46ddf32274437ecd7d2",
        )
        self.assertEqual(
            self.receipt["canonical_v2_robustness_bundle_sha256"],
            "cf794c8741b24f663700920526e5f0e0bf76706a28cf752cd95fa0bd70eddc84",
        )
        self.assertEqual(
            self.receipt["robustness_outcome_projection_sha256"],
            "2f393c3bd59c4d0ef6ee7c27a94e19ae4c8774e55475bff8c59bb2f494a3aacc",
        )
        self.assertEqual(
            self.receipt["canonical_run_reproducibility_ledger_sha256"],
            "6434b4abfa717c96cdb76def63851097689b32c1a33985f86de8a26034f71a4e",
        )

    def test_03_all_147_outcomes_align_but_bundle_identity_does_not(self) -> None:
        self.assertTrue(self.receipt["baseline_outcome_alignment_proven"])
        self.assertTrue(self.receipt["robustness_outcome_alignment_proven"])
        self.assertFalse(self.receipt["robustness_bundle_identity_equal"])
        self.assertEqual(self.receipt["aligned_outcome_pair_count"], 147)

    def test_04_canonical_ledger_is_verified_but_not_legacy_aligned(self) -> None:
        self.assertTrue(
            self.receipt["canonical_reproducibility_ledger_verified"]
        )
        self.assertFalse(self.receipt["statistical_ledger_alignment_proven"])
        self.assertFalse(self.receipt["full_report_alignment_proven"])
        self.assertFalse(self.receipt["run_accounting_additive"])
        self.assertEqual(self.receipt["status"], "BLOCK")

    def test_05_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_robustness_lineage_proof_v1(
                        execute=value  # type: ignore[arg-type]
                    )

    def test_06_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_robustness_lineage_proof_v1(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_robustness_lineage_proof_v1(
                self.bundle["legacy_v1_robustness_bundle"], execute=True
            )

    def test_07_resealed_projection_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["bindings"]["robustness_outcome_projection_sha256"] = "f" * 64
        unsigned = {
            key: value for key, value in tampered.items() if key != "bundle_sha256"
        }
        tampered["bundle_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(SyntheticStrategyRobustnessLineageProofError):
            verify_synthetic_strategy_robustness_lineage_proof_v1(tampered)

    def test_08_resealed_downstream_alignment_claims_fail_closed(self) -> None:
        for field in (
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
                    SyntheticStrategyRobustnessLineageProofError
                ):
                    verify_synthetic_strategy_robustness_lineage_proof_v1(
                        tampered
                    )

    def test_09_exact_native_source_and_bundle_types_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_robustness_lineage_proof_v1(
                DictAlias(self.bundle)
            )
        with self.assertRaises(TypeError):
            build_synthetic_strategy_robustness_lineage_proof_v1(
                DictAlias(self.bundle["legacy_v1_robustness_bundle"]),
                self.bundle["canonical_v2_robustness_bundle"],
                execute=True,
            )

    def test_10_renderer_is_neutral_and_explicitly_partial(self) -> None:
        markdown = render_synthetic_strategy_robustness_lineage_proof_markdown_v1(
            self.bundle
        )
        self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
        self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
        self.assertLess(
            markdown.index("## MATURITY"), markdown.index("## PERMISSION")
        )
        self.assertIn("Robustness outcome alignment proven: TRUE", markdown)
        self.assertIn("Statistical ledger alignment proven: FALSE", markdown)
        self.assertIn("Full report alignment proven: FALSE", markdown)
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
