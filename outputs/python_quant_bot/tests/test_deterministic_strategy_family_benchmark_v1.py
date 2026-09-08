from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from hakimi_research.deterministic_strategy_family_benchmark import (
    REFERENCE_ROOT,
    build_deterministic_strategy_family_reference_material,
    verify_deterministic_strategy_family_reference,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    verify_synthetic_strategy_report_bundle_v2,
)


class DeterministicStrategyFamilyBenchmarkV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = json.loads(
            (REFERENCE_ROOT / "expected_bundle.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (REFERENCE_ROOT / "fixture_manifest.json").read_text(encoding="utf-8")
        )
        cls.receipt = verify_deterministic_strategy_family_reference()

    def test_reference_verifies_and_binds_all_nested_dependencies(self) -> None:
        self.assertEqual(self.receipt["status"], "PASS")
        self.assertEqual(self.receipt["executed_run_count"], 32)
        self.assertEqual(self.receipt["dependency_bound_run_count"], 32)
        self.assertEqual(self.receipt["git_clean_run_count"], 0)
        self.assertTrue(all(self.receipt["checks"].values()))

    def test_family_scope_and_ensemble_gap_are_exact(self) -> None:
        self.assertEqual(
            self.receipt["family_report_counts"],
            {"RANGE": 3, "TREND": 3, "ENSEMBLE": 0},
        )
        self.assertEqual(self.receipt["ensemble_status"], "GAP")
        self.assertIn("ENSEMBLE_STRATEGY_NOT_IMPLEMENTED", self.manifest["gaps"])
        self.assertNotIn("DEPENDENCY_LOCK_NOT_BOUND", self.manifest["gaps"])

    def test_nested_manifests_keep_git_gap_and_authority_false(self) -> None:
        runs = [
            *self.bundle["benchmarks"].values(),
            *[
                run
                for report in self.bundle["strategy_reports"]
                for run in report["runs"].values()
            ],
        ]
        self.assertEqual(len(runs), 32)
        for run in runs:
            manifest = run["result"]["experiment_manifest"]
            self.assertTrue(manifest["dependency_lock_fully_pinned"])
            self.assertFalse(manifest["git_worktree_clean"])
            self.assertIn("git_worktree_not_clean", manifest["blockers"])
            self.assertFalse(manifest["paper_authorized"])
            self.assertFalse(manifest["live_order_allowed"])
            self.assertFalse(manifest["order_entry_allowed"])

    def test_bundle_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        receipt = verify_synthetic_strategy_report_bundle_v2(tampered)
        self.assertEqual(receipt["status"], "BLOCK")

    def test_reference_material_is_byte_exact(self) -> None:
        material = build_deterministic_strategy_family_reference_material()
        for name, text in material["files"].items():
            self.assertEqual((REFERENCE_ROOT / name).read_bytes(), text.encode("utf-8"))
        markdown = (REFERENCE_ROOT / "expected_bundle.md").read_text(encoding="utf-8")
        self.assertIn("Nested dependency lock bound: `true`", markdown)
        self.assertIn("ENSEMBLE report: `GAP`", markdown)
        self.assertNotIn("READY", markdown)


if __name__ == "__main__":
    unittest.main()
