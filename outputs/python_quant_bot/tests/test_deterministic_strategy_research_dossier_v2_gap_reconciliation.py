from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (
    EVIDENCE_GAP_RECONCILIATION_VERSION,
    REQUIRED_RETAINED_GAP_IDS,
    RESOLVED_STALE_GAP_IDS,
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


class DeterministicStrategyResearchDossierV2GapReconciliationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.controls = build_synthetic_strategy_benchmark_controls_v1(
            source, execute=True
        )
        cls.material = build_deterministic_strategy_research_dossier_material_v2(
            cls.controls
        )

    def test_component_identity_and_evidence_summary_are_bound(self) -> None:
        projection = self.material["receipt"]["evidence_gap_reconciliation"]
        self.assertEqual(
            projection["schema_version"], EVIDENCE_GAP_RECONCILIATION_VERSION
        )
        self.assertTrue(projection["component_receipt_identity_verified"])
        self.assertFalse(projection["component_reference_rebuild_performed"])
        self.assertEqual(
            projection["robustness_summary"]["executed_run_count"], 147
        )
        self.assertEqual(
            projection["statistical_v3_summary"][
                "bootstrap_observed_evidence_count"
            ],
            6,
        )
        self.assertEqual(
            projection["statistical_v3_summary"]["bootstrap_gap_evidence_count"],
            0,
        )
        self.assertEqual(
            projection["statistical_v3_summary"][
                "deflated_sharpe_diagnostic_count"
            ],
            6,
        )

    def test_only_six_stale_gaps_are_removed(self) -> None:
        receipt = self.material["receipt"]
        projection = receipt["evidence_gap_reconciliation"]
        self.assertEqual(
            projection["resolved_stale_gap_ids"], list(RESOLVED_STALE_GAP_IDS)
        )
        self.assertEqual(projection["resolved_stale_gap_count"], 6)
        self.assertEqual(projection["inherited_gap_count"], 37)
        self.assertEqual(projection["retained_gap_count"], 31)
        self.assertEqual(receipt["gaps"], projection["retained_gap_ids"])
        self.assertFalse(set(RESOLVED_STALE_GAP_IDS) & set(receipt["gaps"]))
        self.assertTrue(set(REQUIRED_RETAINED_GAP_IDS) <= set(receipt["gaps"]))
        self.assertFalse(projection["reconciliation_is_profitability_proof"])
        self.assertFalse(projection["reconciliation_is_formal_inference"])

    def test_report_separates_resolved_from_retained_gaps(self) -> None:
        report = self.material["files"]["expected_report.md"]
        gap_section = report.split("## GAP\n", 1)[1].split("\n## MATURITY", 1)[0]
        for gap in RESOLVED_STALE_GAP_IDS:
            self.assertNotIn(gap, gap_section)
            self.assertIn(gap, report)
        for gap in REQUIRED_RETAINED_GAP_IDS:
            self.assertIn(gap, gap_section)
        self.assertIn("## Evidence gap reconciliation", report)
        self.assertIn("Resolved stale GAP count: `6`", report)
        self.assertIn("Retained GAP count: `31`", report)

    def test_full_rehash_retained_gap_deletion_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        receipt = tampered["receipt"]
        projection = receipt["evidence_gap_reconciliation"]
        projection["retained_gap_ids"].remove("REAL_DATASET_GAP")
        projection["retained_gap_count"] -= 1
        projection.pop("projection_sha256")
        receipt["evidence_gap_reconciliation"] = _seal(
            projection, "projection_sha256"
        )
        receipt["gaps"] = list(projection["retained_gap_ids"])
        receipt.pop("receipt_sha256")
        tampered["receipt"] = _seal(receipt, "receipt_sha256")
        receipt_bytes = _json_bytes(tampered["receipt"])
        report_bytes = _render_report(tampered["receipt"]).encode("utf-8")
        manifest = tampered["manifest"]
        manifest["receipt_sha256"] = tampered["receipt"]["receipt_sha256"]
        manifest["evidence_gap_reconciliation_sha256"] = tampered["receipt"][
            "evidence_gap_reconciliation"
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
