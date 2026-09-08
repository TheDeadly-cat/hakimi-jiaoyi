from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (
    EXPECTED_STRATEGY_IDS,
    FROZEN_COST_RUN_IDS,
    FROZEN_EXPERIMENT_PROVENANCE_PROJECTION_VERSION,
    FROZEN_PROVENANCE_FIELD_IDS,
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


class DeterministicStrategyResearchDossierV2ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.controls = build_synthetic_strategy_benchmark_controls_v1(
            source, execute=True
        )
        cls.material = build_deterministic_strategy_research_dossier_material_v2(
            cls.controls
        )

    def test_inventory_and_native_verification_are_exact(self) -> None:
        projection = self.material["receipt"][
            "frozen_experiment_provenance_projection"
        ]
        self.assertEqual(
            projection["schema_version"],
            FROZEN_EXPERIMENT_PROVENANCE_PROJECTION_VERSION,
        )
        self.assertEqual(projection["strategy_ids"], list(EXPECTED_STRATEGY_IDS))
        self.assertEqual(projection["run_ids"], list(FROZEN_COST_RUN_IDS))
        self.assertEqual(projection["field_ids"], list(FROZEN_PROVENANCE_FIELD_IDS))
        self.assertEqual(projection["strategy_count"], 6)
        self.assertEqual(projection["run_count"], 18)
        self.assertEqual(projection["native_manifest_verification_count"], 18)
        self.assertEqual(len(projection["rows"]), 18)
        for row in projection["rows"]:
            self.assertEqual(set(row["provenance"]), set(FROZEN_PROVENANCE_FIELD_IDS))

    def test_incomplete_reproducibility_is_preserved_as_a_gap(self) -> None:
        projection = self.material["receipt"][
            "frozen_experiment_provenance_projection"
        ]
        self.assertFalse(projection["reproducibility_complete"])
        self.assertFalse(projection["provenance_is_profitability_proof"])
        self.assertEqual(projection["blocker_counts"], {"git_worktree_not_clean": 18})
        self.assertEqual(projection["unique_experiment_id_count"], 18)
        self.assertEqual(projection["unique_manifest_sha256_count"], 18)
        self.assertEqual(projection["unique_result_sha256_count"], 18)
        self.assertEqual(projection["unique_source_run_sha256_count"], 18)
        self.assertEqual(projection["unique_dataset_sha256_count"], 1)
        self.assertEqual(projection["unique_config_sha256_count"], 18)
        for row in projection["rows"]:
            provenance = row["provenance"]
            self.assertEqual(provenance["git_commit_sha"], "0" * 40)
            self.assertFalse(provenance["git_worktree_clean"])
            self.assertTrue(provenance["dependency_lock_fully_pinned"])
            self.assertTrue(provenance["evaluation_protocol_verified"])
            self.assertEqual(provenance["classification"], "REPRODUCIBILITY_INCOMPLETE")
            self.assertEqual(provenance["blockers"], ["git_worktree_not_clean"])

    def test_report_exposes_provenance_and_gap_fields(self) -> None:
        report = self.material["files"]["expected_report.md"]
        self.assertIn("## Frozen experiment provenance", report)
        for field_id in FROZEN_PROVENANCE_FIELD_IDS:
            self.assertIn(field_id, report)
        self.assertIn("Native manifest verification: `18/18`", report)
        self.assertIn("Reproducibility complete: `false`", report)
        self.assertIn("does not prove reproducibility", report)

    def test_full_rehash_config_hash_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        receipt = tampered["receipt"]
        projection = receipt["frozen_experiment_provenance_projection"]
        projection["rows"][0]["provenance"]["config_hash"] = "0" * 64
        projection.pop("projection_sha256")
        receipt["frozen_experiment_provenance_projection"] = _seal(
            projection, "projection_sha256"
        )
        receipt.pop("receipt_sha256")
        tampered["receipt"] = _seal(receipt, "receipt_sha256")
        receipt_bytes = _json_bytes(tampered["receipt"])
        report_bytes = _render_report(tampered["receipt"]).encode("utf-8")
        manifest = tampered["manifest"]
        manifest["receipt_sha256"] = tampered["receipt"]["receipt_sha256"]
        manifest["frozen_experiment_provenance_projection_sha256"] = tampered[
            "receipt"
        ]["frozen_experiment_provenance_projection"]["projection_sha256"]
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
