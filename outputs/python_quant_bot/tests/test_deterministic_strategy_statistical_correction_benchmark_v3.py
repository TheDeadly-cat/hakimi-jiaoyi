from __future__ import annotations

import copy
import hashlib
import json
import unittest
from typing import Any

from hakimi_research.deterministic_strategy_statistical_correction_benchmark_v3 import (
    EXPECTED_RECEIPT_SHA256,
    PREDECESSOR_MANIFEST_SHA256,
    PREDECESSOR_RECEIPT_SHA256,
    REFERENCE_ROOT,
    SOURCE_RELATIVE_PATHS,
    DeterministicStrategyStatisticalCorrectionBenchmarkV3Error,
    _json_bytes,
    _render_receipt_markdown,
    canonical_sha256,
    verify_deterministic_strategy_statistical_correction_material_v3,
    verify_deterministic_strategy_statistical_correction_reference_v3,
)


class DeterministicStrategyStatisticalCorrectionBenchmarkV3Tests(unittest.TestCase):
    @staticmethod
    def _rebind_receipt_and_manifest(material: dict[str, Any]) -> None:
        receipt = material["receipt"]
        manifest = material["manifest"]
        files = material["files"]
        receipt_core = dict(receipt)
        receipt_core.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = canonical_sha256(receipt_core)
        files["expected_receipt.json"] = _json_bytes(receipt).decode("utf-8")
        files["expected_receipt.md"] = _render_receipt_markdown(receipt)
        for key in tuple(manifest):
            if key in receipt and key != "manifest_sha256":
                manifest[key] = copy.deepcopy(receipt[key])
        manifest["receipt_schema_version"] = receipt["schema_version"]
        manifest["receipt_sha256"] = receipt["receipt_sha256"]
        manifest["expected_receipt_file_sha256"] = hashlib.sha256(
            files["expected_receipt.json"].encode("utf-8")
        ).hexdigest()
        manifest["expected_markdown_file_sha256"] = hashlib.sha256(
            files["expected_receipt.md"].encode("utf-8")
        ).hexdigest()
        manifest_core = dict(manifest)
        manifest_core.pop("manifest_sha256", None)
        manifest["manifest_sha256"] = canonical_sha256(manifest_core)
        files["fixture_manifest.json"] = _json_bytes(manifest).decode("utf-8")

    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = verify_deterministic_strategy_statistical_correction_reference_v3()
        files = {
            name: (REFERENCE_ROOT / name).read_text(encoding="utf-8")
            for name in (
                "expected_receipt.json",
                "expected_receipt.md",
                "fixture_manifest.json",
            )
        }
        cls.material = {
            "receipt": json.loads(files["expected_receipt.json"]),
            "manifest": json.loads(files["fixture_manifest.json"]),
            "files": files,
        }
        cls.material_receipt = (
            verify_deterministic_strategy_statistical_correction_material_v3(
                cls.material
            )
        )

    def test_01_disk_reference_is_exact(self) -> None:
        self.assertEqual(self.receipt["status"], "PASS")
        self.assertTrue(self.receipt["checks"]["reference_file_set"])
        self.assertTrue(self.receipt["checks"]["lf_only"])
        self.assertTrue(self.receipt["checks"]["expected_bytes_exact"])

    def test_02_material_self_verifies(self) -> None:
        self.assertEqual(self.material_receipt["status"], "PASS")
        self.assertTrue(all(self.material_receipt["checks"].values()))
        self.assertTrue(self.material_receipt["checks"]["receipt_identity_locked"])
        self.assertEqual(
            self.material["receipt"]["receipt_sha256"],
            EXPECTED_RECEIPT_SHA256,
        )

    def test_03_consumer_and_ledger_align_without_report_promotion(self) -> None:
        receipt = self.material["receipt"]
        self.assertIs(receipt["full_statistical_reference_applicability_proven"], True)
        self.assertIs(receipt["statistical_ledger_alignment_proven"], True)
        self.assertIs(receipt["full_report_alignment_proven"], False)
        self.assertIs(receipt["reference_current_updated"], False)
        self.assertIs(receipt["report_current_updated"], False)
        self.assertEqual(receipt["status"], "BLOCK")

    def test_04_run_accounting_is_single_graph_and_additive(self) -> None:
        receipt = self.material["receipt"]
        self.assertEqual(receipt["source_executed_run_count"], 32)
        self.assertEqual(receipt["robustness_executed_run_count"], 147)
        self.assertEqual(receipt["total_executed_run_count"], 179)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertIs(receipt["run_accounting_additive"], True)

    def test_05_bootstrap_v3_identity_scope_is_bound(self) -> None:
        receipt = self.material["receipt"]
        self.assertEqual(receipt["bootstrap_seed_identity_scope"], "STATISTICAL_SAMPLE_ONLY")
        self.assertIs(receipt["bootstrap_source_provenance_bound"], True)
        self.assertIs(receipt["bootstrap_source_provenance_affects_seed"], False)
        self.assertEqual(receipt["bootstrap_replay_status"], "EXACT_MATCH")

    def test_06_predecessor_reference_is_not_modified(self) -> None:
        predecessor = self.material["receipt"]["predecessor_reference"]
        self.assertEqual(predecessor["manifest_sha256"], PREDECESSOR_MANIFEST_SHA256)
        self.assertEqual(predecessor["receipt_sha256"], PREDECESSOR_RECEIPT_SHA256)
        self.assertIs(predecessor["modified"], False)

    def test_07_source_closure_includes_new_and_legacy_dependencies(self) -> None:
        source_files = self.material["manifest"]["source_files"]
        self.assertEqual(len(source_files), len(SOURCE_RELATIVE_PATHS))
        self.assertIn(
            "src/hakimi_research/deterministic_strategy_statistical_correction_benchmark_v3.py",
            source_files,
        )
        self.assertIn(
            "src/hakimi_research/synthetic_strategy_bootstrap_validation_v3.py",
            source_files,
        )
        self.assertIn(
            "src/hakimi_research/bootstrap_confidence_evidence.py",
            source_files,
        )

    def test_08_receipt_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        tampered["receipt"]["full_report_alignment_proven"] = True
        with self.assertRaises(DeterministicStrategyStatisticalCorrectionBenchmarkV3Error):
            verify_deterministic_strategy_statistical_correction_material_v3(tampered)

    def test_09_manifest_source_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        path = next(iter(tampered["manifest"]["source_files"]))
        tampered["manifest"]["source_files"][path] = "0" * 64
        with self.assertRaises(DeterministicStrategyStatisticalCorrectionBenchmarkV3Error):
            verify_deterministic_strategy_statistical_correction_material_v3(tampered)

    def test_10_rehashed_matrix_count_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        tampered["receipt"]["matrix_candidate_count"] += 1
        self._rebind_receipt_and_manifest(tampered)
        receipt_core = dict(tampered["receipt"])
        receipt_sha256 = receipt_core.pop("receipt_sha256")
        self.assertEqual(receipt_sha256, canonical_sha256(receipt_core))
        with self.assertRaises(DeterministicStrategyStatisticalCorrectionBenchmarkV3Error):
            verify_deterministic_strategy_statistical_correction_material_v3(tampered)

    def test_11_rehashed_bootstrap_identity_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.material)
        tampered["receipt"]["bootstrap_bundle_sha256"] = "0" * 64
        self._rebind_receipt_and_manifest(tampered)
        receipt_core = dict(tampered["receipt"])
        receipt_sha256 = receipt_core.pop("receipt_sha256")
        self.assertEqual(receipt_sha256, canonical_sha256(receipt_core))
        with self.assertRaises(DeterministicStrategyStatisticalCorrectionBenchmarkV3Error):
            verify_deterministic_strategy_statistical_correction_material_v3(tampered)

    def test_12_renderer_and_permissions_remain_neutral(self) -> None:
        markdown = self.material["files"]["expected_receipt.md"]
        self.assertNotIn("READY", markdown)
        self.assertNotIn("Profitability proven: TRUE", markdown)
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertIn("Paper authority: FALSE", markdown)
        self.assertIn("Live authority: FALSE", markdown)
        self.assertIn("Full report alignment proven: FALSE", markdown)


if __name__ == "__main__":
    unittest.main()
