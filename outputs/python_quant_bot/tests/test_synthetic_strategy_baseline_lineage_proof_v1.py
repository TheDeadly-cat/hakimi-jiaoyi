from __future__ import annotations

import copy
import json
import unittest

from hakimi_research.synthetic_strategy_baseline_lineage_proof import (
    SyntheticStrategyBaselineLineageProofError,
    build_default_synthetic_strategy_baseline_lineage_proof_v1,
    build_synthetic_strategy_baseline_lineage_proof_v1,
    plan_synthetic_strategy_baseline_lineage_proof_v1,
    render_synthetic_strategy_baseline_lineage_proof_markdown_v1,
    verify_synthetic_strategy_baseline_lineage_proof_v1,
)
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256


class SyntheticStrategyBaselineLineageProofV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_default_synthetic_strategy_baseline_lineage_proof_v1(
            execute=True
        )
        cls.receipt = verify_synthetic_strategy_baseline_lineage_proof_v1(
            cls.bundle
        )

    def test_01_plan_registers_two_32_run_sources_and_zero_comparison(self) -> None:
        plan = plan_synthetic_strategy_baseline_lineage_proof_v1()
        self.assertEqual(plan["legacy_source_run_count"], 32)
        self.assertEqual(plan["canonical_source_run_count"], 32)
        self.assertEqual(plan["source_executed_run_count"], 64)
        self.assertEqual(plan["aligned_outcome_pair_count"], 32)
        self.assertEqual(plan["comparison_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertFalse(plan["baseline_outcome_alignment_proven"])

    def test_02_source_and_projection_identities_are_exact(self) -> None:
        self.assertEqual(
            self.receipt["legacy_v1_bundle_sha256"],
            "a74cdbf982b2919912cf6dc12de0c445b486a63b61b60ed71e8ce60942a347b7",
        )
        self.assertEqual(
            self.receipt["canonical_v2_bundle_sha256"],
            "941901724a989b49649abbbf90c519595f62cf3b8c157c4850349c070076e36f",
        )
        self.assertEqual(
            self.receipt["canonical_v1_projection_bundle_sha256"],
            "828d5e492fc1579229a9725d43e7bfa6f70748a7f6b1b1519e73deb15472fb75",
        )
        self.assertEqual(
            self.receipt["outcome_projection_sha256"],
            "d773c121d8ea8651640154178e2ac595c3b40a61cdee7a43f76afcbc3d6d3320",
        )

    def test_03_baseline_outcomes_align_but_bundle_identity_does_not(self) -> None:
        self.assertTrue(self.receipt["baseline_outcome_alignment_proven"])
        self.assertFalse(self.receipt["baseline_bundle_identity_equal"])
        self.assertEqual(self.receipt["aligned_outcome_pair_count"], 32)
        self.assertEqual(self.receipt["source_executed_run_count"], 64)
        self.assertEqual(self.receipt["comparison_executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)

    def test_03b_sorted_json_round_trip_does_not_change_run_alignment(self) -> None:
        canonical_round_trip = json.loads(
            json.dumps(
                self.bundle["canonical_v2_bundle"],
                allow_nan=False,
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        proof = build_synthetic_strategy_baseline_lineage_proof_v1(
            self.bundle["legacy_v1_bundle"],
            canonical_round_trip,
            execute=True,
        )
        receipt = verify_synthetic_strategy_baseline_lineage_proof_v1(proof)
        self.assertTrue(receipt["baseline_outcome_alignment_proven"])
        self.assertEqual(receipt["aligned_outcome_pair_count"], 32)

    def test_04_downstream_alignment_and_additive_accounting_remain_false(self) -> None:
        self.assertFalse(self.receipt["robustness_alignment_proven"])
        self.assertFalse(self.receipt["statistical_ledger_alignment_proven"])
        self.assertFalse(self.receipt["full_report_alignment_proven"])
        self.assertFalse(self.receipt["run_accounting_additive"])
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertEqual(self.receipt["state"], "OBSERVED_WITH_GAPS")

    def test_05_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_baseline_lineage_proof_v1(
                        execute=value  # type: ignore[arg-type]
                    )

    def test_06_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_baseline_lineage_proof_v1(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_baseline_lineage_proof_v1(
                self.bundle["legacy_v1_bundle"], execute=True
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_baseline_lineage_proof_v1(
                canonical_v2_bundle=self.bundle["canonical_v2_bundle"],
                execute=True,
            )

    def test_07_resealed_alignment_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["robustness_alignment_proven"] = True
        unsigned = {
            key: value for key, value in tampered.items() if key != "bundle_sha256"
        }
        tampered["bundle_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(SyntheticStrategyBaselineLineageProofError):
            verify_synthetic_strategy_baseline_lineage_proof_v1(tampered)

    def test_08_resealed_projection_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["bindings"]["outcome_projection_sha256"] = "f" * 64
        unsigned = {
            key: value for key, value in tampered.items() if key != "bundle_sha256"
        }
        tampered["bundle_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(SyntheticStrategyBaselineLineageProofError):
            verify_synthetic_strategy_baseline_lineage_proof_v1(tampered)

    def test_09_exact_native_source_and_bundle_types_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_baseline_lineage_proof_v1(
                DictAlias(self.bundle)
            )
        with self.assertRaises(TypeError):
            build_synthetic_strategy_baseline_lineage_proof_v1(
                DictAlias(self.bundle["legacy_v1_bundle"]),
                self.bundle["canonical_v2_bundle"],
                execute=True,
            )

    def test_10_renderer_is_neutral_and_explicitly_partial(self) -> None:
        markdown = render_synthetic_strategy_baseline_lineage_proof_markdown_v1(
            self.bundle
        )
        self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
        self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
        self.assertLess(
            markdown.index("## MATURITY"), markdown.index("## PERMISSION")
        )
        self.assertIn("Baseline outcome alignment proven: TRUE", markdown)
        self.assertIn("Full report alignment proven: FALSE", markdown)
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
