from __future__ import annotations

import copy
import hashlib
import unittest

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (
    BENCHMARK_CONTROL_IDS,
    EXPECTED_CONTROL_RUN_IDS,
    EXPECTED_STRATEGY_IDS,
    build_deterministic_strategy_research_dossier_material_v2,
    verify_deterministic_strategy_research_dossier_material_v2,
    verify_deterministic_strategy_research_dossier_reference_v2,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    build_synthetic_strategy_benchmark_controls_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
    canonical_sha256,
)
from hakimi_research.deterministic_strategy_research_dossier_v1 import (
    REFERENCE_ROOT as DOSSIER_V1_REFERENCE_ROOT,
)


def _reseal(value: dict[str, object], field: str) -> None:
    value[field] = canonical_sha256(
        {key: item for key, item in value.items() if key != field}
    )


class DeterministicStrategyResearchDossierV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.controls = build_synthetic_strategy_benchmark_controls_v1(
            cls.source, execute=True
        )
        cls.material = build_deterministic_strategy_research_dossier_material_v2(
            cls.controls
        )
        cls.receipt = cls.material["receipt"]
        cls.projection = cls.receipt["benchmark_control_projection"]
        cls.verification = (
            verify_deterministic_strategy_research_dossier_material_v2(
                cls.material, cls.controls
            )
        )

    def test_01_dossier_v1_reference_bytes_remain_exact(self) -> None:
        expected = {
            "expected_receipt.json": "cf343fd7d5b66641bd7e7567280ec67043c2ee6efa9db656febce6c14d63af24",
            "expected_report.md": "07f0b8f345aa35a76bfd5682aa3f3c0e62e81341d93b5e8da10a0c3ce1ec5f2a",
            "fixture_manifest.json": "ed89c15e7459b8d824721113f3269fd7db1e9961fade829a3bc67d12c93b8f87",
        }
        self.assertEqual(
            {
                name: hashlib.sha256(
                    (DOSSIER_V1_REFERENCE_ROOT / name).read_bytes()
                ).hexdigest()
                for name in expected
            },
            expected,
        )

    def test_02_control_identity_and_run_accounting_are_bound(self) -> None:
        self.assertEqual(
            self.projection["source_control_bundle_sha256"],
            "89ce8c8589ae5e59010f92f6e33f3a8270867162e51d8eb6ab18cca43fc8f1ec",
        )
        self.assertEqual(self.projection["source_reused_run_count"], 32)
        self.assertEqual(self.projection["additional_backtest_run_count"], 18)
        self.assertEqual(
            tuple(item["control_id"] for item in self.projection["control_run_identities"]),
            EXPECTED_CONTROL_RUN_IDS,
        )

    def test_03_all_six_control_comparisons_are_projected(self) -> None:
        self.assertEqual(
            tuple(self.receipt["benchmark_control_ids"]), BENCHMARK_CONTROL_IDS
        )
        comparisons = self.projection["strategy_control_comparisons"]
        self.assertEqual(
            tuple(item["strategy_id"] for item in comparisons),
            EXPECTED_STRATEGY_IDS,
        )
        for item in comparisons:
            self.assertEqual(
                tuple(item["control_total_returns"]), BENCHMARK_CONTROL_IDS
            )
            self.assertEqual(
                tuple(item["strategy_minus_control_return_deltas"]),
                BENCHMARK_CONTROL_IDS,
            )

    def test_04_no_skill_distribution_is_complete_and_descriptive(self) -> None:
        distribution = self.projection["no_skill_distribution"]
        self.assertEqual(distribution["path_count"], 16)
        self.assertEqual(
            distribution["summary"]["median_type7"],
            "-0.015769999999999999",
        )
        self.assertEqual(len(distribution["summary"]["summary_sha256"]), 64)

    def test_05_volatility_matched_projection_is_not_executable(self) -> None:
        self.assertFalse(self.projection["equal_volatility_projection_executable"])
        projections = self.projection["volatility_matched_projections"]
        self.assertEqual(
            tuple(item["strategy_id"] for item in projections),
            EXPECTED_STRATEGY_IDS,
        )
        self.assertTrue(all(item["executable_claim"] is False for item in projections))

    def test_06_report_is_neutral_ordered_and_numerically_comparative(self) -> None:
        report = self.material["files"]["expected_report.md"]
        self.assertLess(report.index("## SOURCE"), report.index("## GAP"))
        self.assertLess(report.index("## GAP"), report.index("## MATURITY"))
        self.assertLess(report.index("## MATURITY"), report.index("## PERMISSION"))
        self.assertIn("Strategy minus control", report)
        self.assertIn("No-skill median", report)
        self.assertIn("volatility-matched result is an ex-post synthetic projection", report)
        self.assertNotIn("READY", report)
        self.assertIn("Profitability proven: `false`", report)

    def test_07_candidate_never_activates_current_or_authority(self) -> None:
        self.assertTrue(self.receipt["candidate_only"])
        self.assertFalse(self.receipt["current_activation"])
        self.assertFalse(self.receipt["full_report_alignment_proven"])
        self.assertFalse(
            self.receipt[
                "benchmark_control_to_recorded_v14_identity_alignment_proven"
            ]
        )
        self.assertFalse(any(self.receipt["authority"].values()))
        self.assertEqual(self.receipt["status"], "BLOCK")

    def test_08_resealed_control_value_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.controls)
        comparison = tampered["strategy_control_comparisons"][0]
        comparison["control_total_returns"]["cash"] = "1"
        _reseal(comparison, "comparison_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(Exception):
            build_deterministic_strategy_research_dossier_material_v2(tampered)

    def test_09_reordered_control_run_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.controls)
        tampered["control_runs"][0], tampered["control_runs"][1] = (
            tampered["control_runs"][1],
            tampered["control_runs"][0],
        )
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(Exception):
            build_deterministic_strategy_research_dossier_material_v2(tampered)

    def test_10_resealed_material_authority_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.material)
        tampered["receipt"]["authority"]["paper_authorized"] = True
        _reseal(tampered["receipt"], "receipt_sha256")
        with self.assertRaises(Exception):
            verify_deterministic_strategy_research_dossier_material_v2(
                tampered, self.controls
            )

    def test_11_exact_native_alias_is_rejected(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            build_deterministic_strategy_research_dossier_material_v2(
                DictAlias(self.controls)
            )

    def test_12_reference_bytes_verify_against_rebuilt_controls(self) -> None:
        verification = verify_deterministic_strategy_research_dossier_reference_v2(
            self.controls
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(all(verification["checks"].values()))
        self.assertTrue(verification["candidate_only"])
        self.assertFalse(verification["current_activation"])
        self.assertEqual(self.verification["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
