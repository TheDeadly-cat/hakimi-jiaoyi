from __future__ import annotations

import json
import unittest

from hakimi_research.deterministic_strategy_robustness_benchmark import (
    REFERENCE_FILE_NAMES,
    REFERENCE_ROOT,
    SOURCE_RELATIVE_PATHS,
    verify_deterministic_strategy_robustness_reference,
)


class DeterministicStrategyRobustnessBenchmarkV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(
            (REFERENCE_ROOT / "expected_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        cls.manifest = json.loads(
            (REFERENCE_ROOT / "fixture_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.markdown = (REFERENCE_ROOT / "expected_receipt.md").read_text(
            encoding="utf-8"
        )
        cls.verification = (
            verify_deterministic_strategy_robustness_reference()
        )

    def test_reference_verifies_all_179_dependency_bound_runs(self) -> None:
        self.assertEqual(self.verification["status"], "PASS")
        self.assertEqual(self.verification["source_executed_run_count"], 32)
        self.assertEqual(
            self.verification["robustness_executed_run_count"],
            147,
        )
        self.assertEqual(
            self.verification["total_dependency_bound_run_count"],
            179,
        )
        self.assertEqual(self.verification["git_bound_run_count"], 0)
        self.assertTrue(all(self.verification["checks"].values()))

    def test_reference_is_compact_and_has_exact_file_set(self) -> None:
        self.assertEqual(
            sorted(path.name for path in REFERENCE_ROOT.iterdir() if path.is_file()),
            sorted(REFERENCE_FILE_NAMES),
        )
        self.assertLess(
            (REFERENCE_ROOT / "expected_receipt.json").stat().st_size,
            32768,
        )
        self.assertFalse(
            {
                "source_bundle",
                "strategy_evidence",
                "run_reproducibility_ledger",
            }.intersection(self.receipt)
        )

    def test_plan_roles_scope_and_gaps_are_exact(self) -> None:
        self.assertEqual(
            self.receipt["evaluation_role_counts"],
            {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39},
        )
        self.assertEqual(
            self.receipt["registered_strategy_ids"],
            ["bollinger", "dual_ma", "grid", "macd", "momentum", "rsi"],
        )
        self.assertNotIn("DEPENDENCY_LOCK_NOT_BOUND", self.receipt["gaps"])
        self.assertIn(
            "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
            self.receipt["gaps"],
        )

    def test_manifest_binds_the_declared_computation_closure(self) -> None:
        self.assertEqual(
            set(self.manifest["source_files"]),
            set(SOURCE_RELATIVE_PATHS),
        )
        self.assertIn(
            "src/hakimi_research/synthetic_strategy_robustness_evidence.py",
            self.manifest["source_files"],
        )
        self.assertIn(
            "src/hakimi_research/deterministic_strategy_robustness_benchmark.py",
            self.manifest["source_files"],
        )

    def test_renderer_and_permissions_remain_neutral(self) -> None:
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertTrue(
            all(value is False for value in self.receipt["authority"].values())
        )
        self.assertTrue(
            all(value is False for value in self.receipt["claims"].values())
        )


if __name__ == "__main__":
    unittest.main()
