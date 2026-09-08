from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (
    CONCENTRATION_METRIC_IDS,
    DISTRIBUTION_METRIC_IDS,
    EXPECTED_STRATEGY_IDS,
    FROZEN_DISTRIBUTION_PROJECTION_VERSION,
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


class DeterministicStrategyResearchDossierV2DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_bundle = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.controls_bundle = build_synthetic_strategy_benchmark_controls_v1(
            cls.source_bundle,
            execute=True,
        )
        cls.material = build_deterministic_strategy_research_dossier_material_v2(
            cls.controls_bundle
        )

    def test_projection_inventory_and_source_binding_are_exact(self) -> None:
        projection = self.material["receipt"][
            "frozen_distribution_metric_projection"
        ]
        self.assertEqual(
            projection["schema_version"], FROZEN_DISTRIBUTION_PROJECTION_VERSION
        )
        self.assertEqual(projection["strategy_ids"], list(EXPECTED_STRATEGY_IDS))
        self.assertEqual(projection["strategy_count"], len(EXPECTED_STRATEGY_IDS))
        self.assertEqual(
            projection["distribution_metric_ids"], list(DISTRIBUTION_METRIC_IDS)
        )
        self.assertEqual(
            projection["concentration_metric_ids"], list(CONCENTRATION_METRIC_IDS)
        )
        self.assertEqual(
            [item["strategy_id"] for item in projection["strategy_metrics"]],
            list(EXPECTED_STRATEGY_IDS),
        )
        for item in projection["strategy_metrics"]:
            self.assertEqual(set(item["metrics"]), set(DISTRIBUTION_METRIC_IDS))
            self.assertEqual(
                set(item["concentration"]), set(CONCENTRATION_METRIC_IDS)
            )
            self.assertEqual(item["evaluation_role"], "FROZEN_COST_1X")
            self.assertEqual(item["distribution_status"], "PARTIAL")

    def test_one_sided_trade_statistics_remain_undefined(self) -> None:
        projection = self.material["receipt"][
            "frozen_distribution_metric_projection"
        ]
        by_id = {item["strategy_id"]: item for item in projection["strategy_metrics"]}
        for strategy_id in ("dual_ma", "grid"):
            self.assertIsNone(by_id[strategy_id]["metrics"]["profit_factor"])
            self.assertIsNone(by_id[strategy_id]["metrics"]["payoff_ratio"])

    def test_report_projects_distribution_tables_without_zero_fill(self) -> None:
        report = self.material["files"]["expected_report.md"]
        self.assertIn("## Frozen distribution metrics and Sharpe", report)
        self.assertIn("| Profit factor |", report)
        self.assertIn("undefined", report)
        self.assertIn("Distribution buckets and concentration", report)

    def test_full_rehash_metric_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        receipt = tampered["receipt"]
        projection = receipt["frozen_distribution_metric_projection"]
        projection["strategy_metrics"][0]["sharpe_ratio"] += 0.25
        projection.pop("projection_sha256")
        receipt["frozen_distribution_metric_projection"] = _seal(
            projection, "projection_sha256"
        )
        receipt.pop("receipt_sha256")
        tampered["receipt"] = _seal(receipt, "receipt_sha256")
        receipt_bytes = _json_bytes(tampered["receipt"])
        report_bytes = _render_report(tampered["receipt"]).encode("utf-8")
        manifest = tampered["manifest"]
        manifest["receipt_sha256"] = tampered["receipt"]["receipt_sha256"]
        manifest["frozen_distribution_metric_projection_sha256"] = tampered[
            "receipt"
        ]["frozen_distribution_metric_projection"]["projection_sha256"]
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
                tampered, self.controls_bundle
            )

    def test_reference_identity_matches_rebuild(self) -> None:
        verify_deterministic_strategy_research_dossier_reference_v2(
            self.controls_bundle
        )


if __name__ == "__main__":
    unittest.main()
