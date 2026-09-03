from __future__ import annotations

import copy
import unittest

from hakimi_research.bootstrap_confidence_evidence import (
    BootstrapConfidenceEvidenceError,
)
from hakimi_research.bootstrap_confidence_evidence_v2 import (
    build_bootstrap_confidence_evidence_v2,
)
from hakimi_research.synthetic_strategy_baseline_lineage_proof import (
    _default_reference_context,
)
from hakimi_research.synthetic_strategy_bootstrap_validation import (
    SyntheticStrategyBootstrapValidationError,
    plan_synthetic_strategy_bootstrap_validation_v1,
    plan_synthetic_strategy_bootstrap_validation_v2,
)
from hakimi_research.synthetic_strategy_bootstrap_validation_v3 import (
    build_synthetic_strategy_bootstrap_validation_v3,
    plan_synthetic_strategy_bootstrap_validation_v3,
    render_synthetic_strategy_bootstrap_validation_markdown_v3,
    verify_synthetic_strategy_bootstrap_validation_v3,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
)
from hakimi_research.synthetic_strategy_statistical_applicability_proof import (
    SyntheticStrategyStatisticalApplicabilityProofError,
    build_synthetic_strategy_statistical_applicability_proof_v2,
    render_synthetic_strategy_statistical_applicability_proof_markdown_v2,
    verify_synthetic_strategy_statistical_applicability_proof_v2,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v1,
    build_synthetic_strategy_trial_return_matrix_v2,
)


class SyntheticStrategyBootstrapValidationV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy_source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.canonical_source = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=_default_reference_context(),
        )
        cls.legacy_bootstrap = build_synthetic_strategy_bootstrap_validation_v3(
            cls.legacy_source,
            execute=True,
        )
        cls.canonical_bootstrap = build_synthetic_strategy_bootstrap_validation_v3(
            cls.canonical_source,
            execute=True,
        )
        cls.legacy_matrix = build_synthetic_strategy_trial_return_matrix_v1(
            cls.legacy_source,
            execute=True,
        )
        cls.canonical_matrix = build_synthetic_strategy_trial_return_matrix_v2(
            cls.canonical_source,
            execute=True,
        )
        cls.proof = build_synthetic_strategy_statistical_applicability_proof_v2(
            cls.legacy_matrix,
            cls.canonical_matrix,
            cls.legacy_bootstrap,
            cls.canonical_bootstrap,
            execute=True,
        )

    @staticmethod
    def _bootstrap_projection(bundle: dict) -> list[dict]:
        return [
            {
                "strategy_id": record["strategy_id"],
                "sample": record["statistical_sample_sha256"],
                "seed": record["bootstrap_evidence"]["seed_material_sha256"],
                "summary": record["bootstrap_evidence"]["sample_summary"],
                "intervals": record["bootstrap_evidence"]["intervals"],
            }
            for record in bundle["strategy_records"]
        ]

    def test_01_v3_plan_is_opt_in_and_zero_run(self) -> None:
        plan = plan_synthetic_strategy_bootstrap_validation_v3()
        self.assertEqual(plan["planned_run_count"], 0)
        self.assertEqual(plan["policy"]["seed_derivation"], "SHA256_STATISTICAL_SAMPLE_IDENTITY_V2")
        self.assertIs(plan["source_provenance_affects_seed"], False)
        self.assertIs(plan["authority"]["profitability_proven"], False)

    def test_02_v1_v2_plan_identities_remain_unchanged(self) -> None:
        self.assertEqual(
            plan_synthetic_strategy_bootstrap_validation_v1()["plan_sha256"],
            "d12d21c87ed8299d4ae2bdfd2e18a06764442727b825fcf89c815277884922cc",
        )
        self.assertEqual(
            plan_synthetic_strategy_bootstrap_validation_v2()["plan_sha256"],
            "2c2eae0059c3833528cfe1640bd020f1407289d33d6f8680b82f24dd66d5f52d",
        )

    def test_03_both_source_contracts_verify(self) -> None:
        legacy = verify_synthetic_strategy_bootstrap_validation_v3(
            self.legacy_bootstrap,
            self.legacy_source,
        )
        canonical = verify_synthetic_strategy_bootstrap_validation_v3(
            self.canonical_bootstrap,
            self.canonical_source,
        )
        self.assertEqual(legacy["state"], "OBSERVED")
        self.assertEqual(canonical["state"], "OBSERVED")
        self.assertNotEqual(legacy["source_schema_version"], canonical["source_schema_version"])

    def test_04_equal_outcomes_have_equal_samples_seeds_and_intervals(self) -> None:
        self.assertEqual(
            self._bootstrap_projection(self.legacy_bootstrap),
            self._bootstrap_projection(self.canonical_bootstrap),
        )

    def test_05_source_provenance_identities_remain_distinct(self) -> None:
        self.assertNotEqual(
            self.legacy_bootstrap["bundle_sha256"],
            self.canonical_bootstrap["bundle_sha256"],
        )
        self.assertNotEqual(
            self.legacy_bootstrap["source_provenance_binding"],
            self.canonical_bootstrap["source_provenance_binding"],
        )

    def test_06_provenance_only_change_does_not_change_seed_or_intervals(self) -> None:
        report = self.canonical_source["strategy_reports"][0]
        run = report["runs"]["frozen_1x"]
        benchmark = self.canonical_source["benchmarks"]["buy_and_hold"]
        first = build_bootstrap_confidence_evidence_v2(
            run["result"]["equity_curve"],
            benchmark["result"]["equity_curve"],
            strategy_id=report["strategy_id"],
            dataset_sha256="a" * 64,
            strategy_result_sha256="b" * 64,
            benchmark_result_sha256="c" * 64,
            observation_class="SYNTHETIC_OBSERVATION_ONLY",
        )
        second = build_bootstrap_confidence_evidence_v2(
            run["result"]["equity_curve"],
            benchmark["result"]["equity_curve"],
            strategy_id=report["strategy_id"],
            dataset_sha256="d" * 64,
            strategy_result_sha256="e" * 64,
            benchmark_result_sha256="f" * 64,
            observation_class="SYNTHETIC_OBSERVATION_ONLY",
        )
        self.assertEqual(first["statistical_sample_sha256"], second["statistical_sample_sha256"])
        self.assertEqual(first["seed_material_sha256"], second["seed_material_sha256"])
        self.assertEqual(first["intervals"], second["intervals"])
        self.assertNotEqual(first["source_binding"], second["source_binding"])
        self.assertNotEqual(first["evidence_sha256"], second["evidence_sha256"])

    def test_07_outcome_change_changes_sample_and_seed(self) -> None:
        report = self.canonical_source["strategy_reports"][0]
        run = report["runs"]["frozen_1x"]
        benchmark = self.canonical_source["benchmarks"]["buy_and_hold"]
        curve = run["result"]["equity_curve"]
        changed_curve = copy.deepcopy(curve)
        changed_curve[-1]["equity"] *= 1.01
        kwargs = {
            "strategy_id": report["strategy_id"],
            "dataset_sha256": "a" * 64,
            "strategy_result_sha256": "b" * 64,
            "benchmark_result_sha256": "c" * 64,
            "observation_class": "SYNTHETIC_OBSERVATION_ONLY",
        }
        first = build_bootstrap_confidence_evidence_v2(
            curve,
            benchmark["result"]["equity_curve"],
            **kwargs,
        )
        second = build_bootstrap_confidence_evidence_v2(
            changed_curve,
            benchmark["result"]["equity_curve"],
            **kwargs,
        )
        self.assertNotEqual(first["statistical_sample_sha256"], second["statistical_sample_sha256"])
        self.assertNotEqual(first["seed_material_sha256"], second["seed_material_sha256"])
        self.assertNotEqual(first["intervals"], second["intervals"])

    def test_08_tampered_evidence_is_rejected_even_with_outer_rehash(self) -> None:
        tampered = copy.deepcopy(self.canonical_bootstrap)
        tampered["strategy_records"][0]["bootstrap_evidence"]["intervals"][0][
            "median"
        ] = "0"
        record = tampered["strategy_records"][0]
        record_without_hash = dict(record)
        record_without_hash.pop("record_sha256")
        record["record_sha256"] = canonical_sha256(record_without_hash)
        bundle_without_hash = dict(tampered)
        bundle_without_hash.pop("bundle_sha256")
        tampered["bundle_sha256"] = canonical_sha256(bundle_without_hash)
        with self.assertRaises(SyntheticStrategyBootstrapValidationError):
            verify_synthetic_strategy_bootstrap_validation_v3(
                tampered,
                self.canonical_source,
            )

    def test_09_exact_native_identifier_boundary(self) -> None:
        class StrategyId(str):
            pass

        report = self.canonical_source["strategy_reports"][0]
        run = report["runs"]["frozen_1x"]
        benchmark = self.canonical_source["benchmarks"]["buy_and_hold"]
        with self.assertRaises(BootstrapConfidenceEvidenceError):
            build_bootstrap_confidence_evidence_v2(
                run["result"]["equity_curve"],
                benchmark["result"]["equity_curve"],
                strategy_id=StrategyId(report["strategy_id"]),
                dataset_sha256="a" * 64,
                strategy_result_sha256="b" * 64,
                benchmark_result_sha256="c" * 64,
                observation_class="SYNTHETIC_OBSERVATION_ONLY",
            )

    def test_10_v2_proof_closes_numerical_not_consumer_alignment(self) -> None:
        receipt = verify_synthetic_strategy_statistical_applicability_proof_v2(
            self.proof
        )
        self.assertIs(receipt["bootstrap_numerical_applicability_proven"], True)
        self.assertIs(receipt["full_statistical_numerical_applicability_proven"], True)
        self.assertIs(receipt["full_statistical_reference_applicability_proven"], False)
        self.assertIs(receipt["statistical_ledger_alignment_proven"], False)
        self.assertIs(receipt["full_report_alignment_proven"], False)
        self.assertEqual(receipt["bootstrap_differing_interval_value_count"], 0)
        self.assertEqual(receipt["bootstrap_differing_seed_count"], 0)

    def test_11_proof_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.proof)
        tampered["bootstrap_numerical_applicability_proven"] = False
        with self.assertRaises(SyntheticStrategyStatisticalApplicabilityProofError):
            verify_synthetic_strategy_statistical_applicability_proof_v2(tampered)

    def test_12_renderers_remain_neutral(self) -> None:
        bootstrap_markdown = render_synthetic_strategy_bootstrap_validation_markdown_v3(
            self.canonical_bootstrap,
            self.canonical_source,
        )
        proof_markdown = render_synthetic_strategy_statistical_applicability_proof_markdown_v2(
            self.proof
        )
        for markdown in (bootstrap_markdown, proof_markdown):
            self.assertNotIn("READY", markdown)
            self.assertNotIn("Profitability proof: true", markdown)
            self.assertNotIn("Profitability proven: TRUE", markdown)
        self.assertIn("Profitability proof: false", bootstrap_markdown)
        self.assertIn(
            "Paper, live, and order-entry authorization: false",
            bootstrap_markdown,
        )
        self.assertIn("Profitability proven: FALSE", proof_markdown)
        self.assertIn("Paper authority: FALSE", proof_markdown)
        self.assertIn("Live authority: FALSE", proof_markdown)


if __name__ == "__main__":
    unittest.main()
