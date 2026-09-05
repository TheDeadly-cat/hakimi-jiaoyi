from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (
    EXPECTED_STRATEGY_IDS,
    FROZEN_COST_ROLES,
    FROZEN_COST_RUN_IDS,
    FROZEN_COST_STRESS_PROJECTION_VERSION,
    FROZEN_FEE_RATES,
    FROZEN_SLIPPAGE_RATES,
    _json_bytes,
    _render_report,
    _seal,
    _sha256_bytes,
    build_deterministic_strategy_research_dossier_material_v2,
    verify_deterministic_strategy_research_dossier_material_v2,
    verify_deterministic_strategy_research_dossier_reference_v2,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    build_synthetic_strategy_benchmark_controls_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)


class DeterministicStrategyResearchDossierV2CostStressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.controls = build_synthetic_strategy_benchmark_controls_v1(
            source, execute=True
        )
        cls.material = build_deterministic_strategy_research_dossier_material_v2(
            cls.controls
        )

    def test_inventory_roles_and_cost_models_are_exact(self) -> None:
        projection = self.material["receipt"]["frozen_cost_stress_projection"]
        self.assertEqual(
            projection["schema_version"], FROZEN_COST_STRESS_PROJECTION_VERSION
        )
        self.assertEqual(projection["strategy_ids"], list(EXPECTED_STRATEGY_IDS))
        self.assertEqual(projection["run_ids"], list(FROZEN_COST_RUN_IDS))
        self.assertEqual(projection["cost_roles"], list(FROZEN_COST_ROLES))
        self.assertEqual(projection["expected_fee_rates"], list(FROZEN_FEE_RATES))
        self.assertEqual(
            projection["expected_slippage_rates"], list(FROZEN_SLIPPAGE_RATES)
        )
        self.assertEqual(projection["strategy_count"], 6)
        self.assertEqual(projection["run_count"], 18)
        self.assertFalse(projection["observations_are_profitability_proof"])
        for index, row in enumerate(projection["run_rows"]):
            cost_index = index % 3
            self.assertEqual(row["run_id"], FROZEN_COST_RUN_IDS[cost_index])
            self.assertEqual(row["cost_role"], FROZEN_COST_ROLES[cost_index])
            self.assertEqual(row["manifest_evaluation_role"], "FROZEN_TEST")
            self.assertEqual(row["fee_model"]["rate"], FROZEN_FEE_RATES[cost_index])
            self.assertEqual(
                row["slippage_model"]["rate"],
                FROZEN_SLIPPAGE_RATES[cost_index],
            )

    def test_deltas_and_monotonic_observations_are_recomputed(self) -> None:
        projection = self.material["receipt"]["frozen_cost_stress_projection"]
        for offset in range(0, len(projection["run_rows"]), 3):
            rows = projection["run_rows"][offset : offset + 3]
            baseline = rows[0]
            for row in rows:
                self.assertAlmostEqual(
                    row["total_return_delta_from_1x"],
                    row["total_return"] - baseline["total_return"],
                    places=12,
                )
                self.assertAlmostEqual(
                    row["sharpe_ratio_delta_from_1x"],
                    row["sharpe_ratio"] - baseline["sharpe_ratio"],
                    places=12,
                )
                self.assertAlmostEqual(
                    row["max_drawdown_delta_from_1x"],
                    row["max_drawdown"] - baseline["max_drawdown"],
                    places=12,
                )
                self.assertAlmostEqual(
                    row["total_fees_delta_from_1x"],
                    row["total_fees"] - baseline["total_fees"],
                    places=12,
                )
        for observation in projection["strategy_observations"]:
            self.assertTrue(observation["fees_non_decreasing_observation"])
            self.assertTrue(observation["returns_non_increasing_observation"])
            self.assertTrue(observation["drawdowns_non_decreasing_observation"])

    def test_report_contains_all_cost_roles_and_neutral_boundary(self) -> None:
        report = self.material["files"]["expected_report.md"]
        self.assertIn("## Frozen cost-stress observations", report)
        for role in FROZEN_COST_ROLES:
            self.assertEqual(report.count(role), len(EXPECTED_STRATEGY_IDS))
        self.assertIn("do not prove profitability", report)

    def test_full_rehash_fee_rate_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        receipt = tampered["receipt"]
        projection = receipt["frozen_cost_stress_projection"]
        projection["run_rows"][0]["fee_model"]["rate"] = "0"
        projection.pop("projection_sha256")
        receipt["frozen_cost_stress_projection"] = _seal(
            projection, "projection_sha256"
        )
        receipt.pop("receipt_sha256")
        tampered["receipt"] = _seal(receipt, "receipt_sha256")
        receipt_bytes = _json_bytes(tampered["receipt"])
        report_bytes = _render_report(tampered["receipt"]).encode("utf-8")
        manifest = tampered["manifest"]
        manifest["receipt_sha256"] = tampered["receipt"]["receipt_sha256"]
        manifest["frozen_cost_stress_projection_sha256"] = tampered["receipt"][
            "frozen_cost_stress_projection"
        ]["projection_sha256"]
        manifest["expected_receipt_file_sha256"] = _sha256_bytes(receipt_bytes)
        manifest["expected_report_file_sha256"] = _sha256_bytes(report_bytes)
        manifest.pop("manifest_sha256")
        tampered["manifest"] = _seal(manifest, "manifest_sha256")
        tampered["files"] = {
            "expected_receipt.json": receipt_bytes.decode("utf-8"),
            "expected_report.md": report_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(tampered["manifest"]).decode(
                "utf-8"
            ),
        }
        with self.assertRaises(Exception):
            verify_deterministic_strategy_research_dossier_material_v2(
                tampered, self.controls
            )

    def test_reference_identity_matches_rebuild(self) -> None:
        verify_deterministic_strategy_research_dossier_reference_v2(self.controls)


if __name__ == "__main__":
    unittest.main()
