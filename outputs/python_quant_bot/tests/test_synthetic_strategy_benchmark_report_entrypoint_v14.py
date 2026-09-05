from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import examples.build_synthetic_strategy_benchmark_report_v14 as v14
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256


def _reseal(value: dict[str, object], field: str) -> None:
    value[field] = canonical_sha256(
        {key: item for key, item in value.items() if key != field}
    )


def _authority() -> dict[str, bool]:
    return {
        "blind_test_complete": False,
        "formal_inference_authorized": False,
        "live_authorized": False,
        "order_entry_authorized": False,
        "paper_authorized": False,
        "profitability_proven": False,
    }


def _fake_sources() -> tuple[dict, dict, dict]:
    material = v14.load_statistical_reference_material_v3()
    receipt = material["receipt"]
    legacy_baseline = {
        "schema_version": "synthetic-strategy-report-bundle-v1",
        "bundle_sha256": "1" * 64,
    }
    legacy_robustness = {
        "schema_version": "synthetic-strategy-robustness-evidence-bundle-v1",
        "bundle_sha256": "2" * 64,
        "source_bundle": legacy_baseline,
    }
    legacy_matrix = {
        "schema_version": "synthetic-strategy-trial-return-matrix-bundle-v1",
        "bundle_sha256": "3" * 64,
        "source_robustness_bundle": legacy_robustness,
    }
    canonical_baseline = {
        "schema_version": "synthetic-strategy-report-bundle-v2",
        "bundle_sha256": receipt["source_bundle_sha256"],
    }
    canonical_robustness = {
        "schema_version": "synthetic-strategy-robustness-evidence-bundle-v2",
        "bundle_sha256": receipt["robustness_bundle_sha256"],
        "source_bundle": canonical_baseline,
    }
    canonical_matrix = {
        "schema_version": "synthetic-strategy-trial-return-matrix-bundle-v2",
        "bundle_sha256": receipt["trial_matrix_bundle_sha256"],
        "source_robustness_bundle": canonical_robustness,
        "source_run_reproducibility_ledger_sha256": receipt[
            "run_reproducibility_ledger_sha256"
        ],
    }
    proof = {
        "schema_version": v14.OUTCOME_BUNDLE_SCHEMA_VERSION,
        "bundle_sha256": "4" * 64,
        "plan": {"plan_sha256": "5" * 64},
        "legacy_matrix_bundle": legacy_matrix,
        "canonical_matrix_bundle": canonical_matrix,
        "legacy_bootstrap_bundle": {"bundle_sha256": "6" * 64},
        "canonical_bootstrap_bundle": {
            "bundle_sha256": receipt["bootstrap_bundle_sha256"]
        },
        "bindings": {
            "robustness_lineage_proof_bundle_sha256": "7" * 64,
            "canonical_run_reproducibility_ledger_sha256": receipt[
                "run_reproducibility_ledger_sha256"
            ],
            "stages": {
                "matrix": {
                    "canonical_bundle_sha256": receipt[
                        "trial_matrix_bundle_sha256"
                    ]
                },
                "dsr": {
                    "canonical_bundle_sha256": receipt[
                        "deflated_sharpe_bundle_sha256"
                    ]
                },
                "pbo": {
                    "canonical_bundle_sha256": receipt[
                        "cscv_pbo_bundle_sha256"
                    ]
                },
                "tie": {
                    "canonical_bundle_sha256": receipt[
                        "cscv_pbo_tie_bounds_bundle_sha256"
                    ]
                },
            },
            "bootstrap": {
                "canonical_bundle_sha256": receipt["bootstrap_bundle_sha256"]
            },
        },
        "matrix_outcome_applicability_proven": True,
        "dsr_numerical_applicability_proven": True,
        "pbo_numerical_applicability_proven": True,
        "tie_bounds_numerical_applicability_proven": True,
        "bootstrap_numerical_applicability_proven": True,
        "full_statistical_numerical_applicability_proven": True,
        "bootstrap_seed_identity_policy_proven": True,
        "bootstrap_source_provenance_binding_preserved": True,
        "canonical_reproducibility_ledger_verified": True,
        "full_statistical_reference_applicability_proven": False,
        "statistical_ledger_alignment_proven": False,
        "full_report_alignment_proven": False,
        "run_accounting_additive": False,
        "formal_inference_claimed": False,
        "status": "BLOCK",
        "authority": _authority(),
        "runtime_mutations": False,
    }
    source = {
        "schema_version": v14.SOURCE_REPORT_SCHEMA_VERSION,
        "report_sha256": "8" * 64,
        "plan": {"plan_sha256": "9" * 64},
        "bindings": {
            "source_baseline_bundle_sha256": legacy_baseline["bundle_sha256"]
        },
        "total_logical_run_count": 222,
        "status": "BLOCK",
        "authority": _authority(),
        "runtime_mutations": False,
    }
    current = source
    for version in range(11, 3, -1):
        child: dict = {}
        current[f"source_report_v{version}"] = child
        current = child
    current["trial_return_matrix"] = copy.deepcopy(legacy_matrix)
    return source, proof, material


class SyntheticStrategyBenchmarkReportEntrypointV14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source, cls.proof, cls.material = _fake_sources()
        with patch.object(
            v14,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"receipt_sha256": "a" * 64, "status": "BLOCK"},
        ), patch.object(
            v14,
            "verify_synthetic_strategy_statistical_applicability_proof_v2",
            return_value={"bundle_sha256": cls.proof["bundle_sha256"]},
        ):
            cls.report = v14.build_synthetic_strategy_benchmark_report_v14(
                cls.source, cls.proof, cls.material, execute=True
            )
            cls.receipt = v14.verify_synthetic_strategy_benchmark_report_v14(
                cls.report, cls.proof
            )

    def _verify(self, report: dict, proof: dict | None = None) -> dict:
        candidate = self.proof if proof is None else proof
        with patch.object(
            v14,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"receipt_sha256": "a" * 64, "status": "BLOCK"},
        ), patch.object(
            v14,
            "verify_synthetic_strategy_statistical_applicability_proof_v2",
            return_value={"bundle_sha256": candidate.get("bundle_sha256")},
        ):
            return v14.verify_synthetic_strategy_benchmark_report_v14(
                report, candidate
            )

    def test_01_plan_is_nonexecuting_and_alignment_is_unproven(self) -> None:
        plan = v14.plan_synthetic_strategy_benchmark_report_v14()
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertFalse(plan["full_report_alignment_proven"])
        self.assertFalse(plan["run_accounting_additive"])

    def test_02_report_activates_v3_alignment_without_authority(self) -> None:
        self.assertTrue(self.receipt["full_report_alignment_proven"])
        self.assertTrue(self.receipt["statistical_reference_v3_applied"])
        self.assertTrue(self.receipt["bootstrap_v3_replaces_legacy_v1"])
        self.assertTrue(
            self.receipt["legacy_v12_statistical_evidence_superseded"]
        )
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(any(self.receipt["authority"].values()))
        self.assertFalse(self.receipt["formal_inference_claimed"])

    def test_03_all_canonical_statistical_digests_are_bound(self) -> None:
        binding = self.report["alignment_binding"]
        source_receipt = self.material["receipt"]
        for field in (
            "source_bundle_sha256",
            "robustness_bundle_sha256",
            "trial_matrix_bundle_sha256",
            "deflated_sharpe_bundle_sha256",
            "cscv_pbo_bundle_sha256",
            "cscv_pbo_tie_bounds_bundle_sha256",
            "bootstrap_bundle_sha256",
            "run_reproducibility_ledger_sha256",
        ):
            self.assertEqual(binding[field], source_receipt[field])

    def test_04_v12_legacy_matrix_substitution_fails_closed(self) -> None:
        source = copy.deepcopy(self.source)
        current = source
        for version in range(11, 3, -1):
            current = current[f"source_report_v{version}"]
        current["trial_return_matrix"]["bundle_sha256"] = "0" * 64
        with patch.object(
            v14,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"receipt_sha256": "a" * 64, "status": "BLOCK"},
        ), patch.object(
            v14,
            "verify_synthetic_strategy_statistical_applicability_proof_v2",
            return_value={"bundle_sha256": self.proof["bundle_sha256"]},
        ):
            with self.assertRaises(v14.SyntheticStrategyBenchmarkReportV14Error):
                v14.build_synthetic_strategy_benchmark_report_v14(
                    source, self.proof, self.material, execute=True
                )

    def test_05_canonical_source_or_stage_digest_mismatch_fails_closed(self) -> None:
        mutations = (
            ("source",),
            ("stage", "dsr"),
            ("stage", "pbo"),
            ("stage", "tie"),
            ("bootstrap",),
            ("ledger",),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                proof = copy.deepcopy(self.proof)
                if mutation[0] == "source":
                    proof["canonical_matrix_bundle"]["source_robustness_bundle"][
                        "source_bundle"
                    ]["bundle_sha256"] = "0" * 64
                elif mutation[0] == "stage":
                    proof["bindings"]["stages"][mutation[1]][
                        "canonical_bundle_sha256"
                    ] = "0" * 64
                elif mutation[0] == "bootstrap":
                    proof["bindings"]["bootstrap"][
                        "canonical_bundle_sha256"
                    ] = "0" * 64
                else:
                    proof["bindings"][
                        "canonical_run_reproducibility_ledger_sha256"
                    ] = "0" * 64
                with self.assertRaises(
                    v14.SyntheticStrategyBenchmarkReportV14Error
                ):
                    self._verify(self.report, proof)

    def test_06_outer_reseal_cannot_change_alignment_or_authority(self) -> None:
        for path in ("alignment", "authority"):
            with self.subTest(path=path):
                tampered = copy.deepcopy(self.report)
                if path == "alignment":
                    tampered["full_report_alignment_proven"] = False
                else:
                    tampered["authority"]["paper_authorized"] = True
                _reseal(tampered, "report_sha256")
                with self.assertRaises(
                    v14.SyntheticStrategyBenchmarkReportV14Error
                ):
                    self._verify(tampered)

    def test_07_external_proof_identity_is_mandatory(self) -> None:
        proof = copy.deepcopy(self.proof)
        proof["bundle_sha256"] = "0" * 64
        with self.assertRaises(v14.SyntheticStrategyBenchmarkReportV14Error):
            self._verify(self.report, proof)
        with self.assertRaises(TypeError):
            v14.verify_synthetic_strategy_benchmark_report_v14(
                self.report, None  # type: ignore[arg-type]
            )

    def test_08_exact_native_types_and_execute_flag_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            self._verify(DictAlias(self.report))
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    v14.build_synthetic_strategy_benchmark_report_v14(
                        execute=value  # type: ignore[arg-type]
                    )

    def test_09_resolved_gaps_are_removed_and_synthetic_gaps_remain(self) -> None:
        gaps = set(self.report["gaps"])
        self.assertFalse(v14._RESOLVED_GAPS & gaps)
        self.assertTrue(v14._ALIGNMENT_GAPS.issubset(gaps))
        self.assertIn("REAL_DATASET_GAP", gaps)
        self.assertIn("FORMAL_FROZEN_BLIND_TEST_GAP", gaps)

    def test_10_renderer_is_neutral_and_ordered(self) -> None:
        with patch.object(
            v14,
            "verify_synthetic_strategy_benchmark_report_v12",
            return_value={"receipt_sha256": "a" * 64, "status": "BLOCK"},
        ), patch.object(
            v14,
            "verify_synthetic_strategy_statistical_applicability_proof_v2",
            return_value={"bundle_sha256": self.proof["bundle_sha256"]},
        ):
            markdown = v14.render_synthetic_strategy_benchmark_report_markdown_v14(
                self.report, self.proof
            )
        self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
        self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
        self.assertLess(
            markdown.index("## MATURITY"), markdown.index("## PERMISSION")
        )
        self.assertIn("Full report alignment proven: TRUE", markdown)
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertNotIn("READY", markdown)


if __name__ == "__main__":
    unittest.main()
