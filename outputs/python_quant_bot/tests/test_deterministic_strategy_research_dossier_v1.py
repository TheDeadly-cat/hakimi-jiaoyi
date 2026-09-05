from __future__ import annotations

import copy
import hashlib
import unittest

from hakimi_research.deterministic_strategy_research_dossier_v1 import (
    V14_RECEIPT_SHA256,
    _AUTHORITY,
    build_deterministic_strategy_research_dossier_material_v1,
    verify_deterministic_strategy_research_dossier_material_v1,
)
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256


def _reseal(value: dict[str, object], field: str) -> None:
    value[field] = canonical_sha256(
        {key: item for key, item in value.items() if key != field}
    )


class DeterministicStrategyResearchDossierV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.material = build_deterministic_strategy_research_dossier_material_v1()
        cls.receipt = cls.material["receipt"]
        cls.manifest = cls.material["manifest"]
        cls.verification = (
            verify_deterministic_strategy_research_dossier_material_v1(
                cls.material
            )
        )

    def test_01_six_strategies_and_three_frozen_cost_levels_are_bound(self) -> None:
        self.assertEqual(self.receipt["registered_strategy_count"], 6)
        self.assertEqual(
            self.receipt["registered_strategy_ids"],
            ["bollinger", "dual_ma", "grid", "macd", "momentum", "rsi"],
        )
        self.assertEqual(self.receipt["observed_family_ids"], ["RANGE", "TREND"])
        self.assertEqual(self.receipt["gap_family_ids"], ["ENSEMBLE"])
        self.assertEqual(self.receipt["frozen_cost_stress_multipliers"], [1, 2, 3])
        self.assertEqual(self.receipt["frozen_strategy_observation_count"], 18)

    def test_02_v14_full_rebuild_receipt_is_exact_and_non_authorizing(self) -> None:
        receipt = self.receipt["v14_full_rebuild_receipt"]
        self.assertEqual(receipt["receipt_sha256"], V14_RECEIPT_SHA256)
        self.assertTrue(receipt["full_report_alignment_proven"])
        self.assertTrue(receipt["bootstrap_v3_replaces_legacy_v1"])
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(any(receipt["authority"].values()))

    def test_03_compact_trust_boundary_is_explicit(self) -> None:
        self.assertTrue(
            self.receipt["v14_full_rebuild_semantic_revalidation_required"]
        )
        self.assertFalse(self.receipt["v14_report_json_embedded"])
        self.assertIn(
            "FULL_V14_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION",
            self.receipt["gaps"],
        )
        self.assertFalse(self.receipt["ranking_performed"])
        self.assertFalse(self.receipt["formal_frozen_blind_test_complete"])

    def test_04_report_is_ordered_neutral_and_contains_numeric_tables(self) -> None:
        report = self.material["files"]["expected_report.md"]
        self.assertLess(report.index("## SOURCE"), report.index("## GAP"))
        self.assertLess(report.index("## GAP"), report.index("## MATURITY"))
        self.assertLess(report.index("## MATURITY"), report.index("## PERMISSION"))
        self.assertIn("Frozen 1x | Frozen 2x | Frozen 3x", report)
        self.assertIn("| RANGE | bollinger |", report)
        self.assertIn("| TREND | dual_ma |", report)
        self.assertIn("ENSEMBLE family: GAP", report)
        self.assertIn("Profitability proven: `false`", report)
        self.assertNotIn("READY", report)

    def test_05_component_and_source_files_are_byte_bound(self) -> None:
        self.assertEqual(self.manifest["component_file_count"], 9)
        self.assertEqual(self.manifest["source_file_count"], 6)
        self.assertEqual(
            self.manifest["component_files"],
            self.receipt["component_file_sha256"],
        )
        for value in self.manifest["component_files"].values():
            self.assertEqual(len(value), 64)

    def test_06_resealed_v14_identity_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.material)
        receipt = tampered["receipt"]
        receipt["v14_full_rebuild_receipt"]["report_sha256"] = "0" * 64
        _reseal(receipt["v14_full_rebuild_receipt"], "receipt_sha256")
        _reseal(receipt, "receipt_sha256")
        tampered["files"]["expected_receipt.json"] = "tampered\n"
        with self.assertRaises(Exception):
            verify_deterministic_strategy_research_dossier_material_v1(tampered)

    def test_07_resealed_component_hash_or_authority_tamper_fails_closed(self) -> None:
        for field in ("component", "authority"):
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.material)
                receipt = tampered["receipt"]
                if field == "component":
                    first = next(iter(receipt["component_file_sha256"]))
                    receipt["component_file_sha256"][first] = "f" * 64
                else:
                    receipt["authority"]["paper_authorized"] = True
                _reseal(receipt, "receipt_sha256")
                with self.assertRaises(Exception):
                    verify_deterministic_strategy_research_dossier_material_v1(
                        tampered
                    )

    def test_08_exact_native_alias_is_rejected(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_deterministic_strategy_research_dossier_material_v1(
                DictAlias(self.material)
            )

    def test_09_manifest_hashes_match_generated_files(self) -> None:
        files = self.material["files"]
        self.assertEqual(
            self.manifest["expected_receipt_file_sha256"],
            hashlib.sha256(files["expected_receipt.json"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            self.manifest["expected_report_file_sha256"],
            hashlib.sha256(files["expected_report.md"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(self.verification["status"], "PASS")
        self.assertEqual(self.verification["authority"], _AUTHORITY)


if __name__ == "__main__":
    unittest.main()
