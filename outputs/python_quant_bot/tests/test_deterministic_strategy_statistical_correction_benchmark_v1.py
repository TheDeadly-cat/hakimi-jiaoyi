from __future__ import annotations

import json
import unittest

from hakimi_research.deterministic_strategy_statistical_correction_benchmark import (
    REFERENCE_FILE_NAMES,
    REFERENCE_ROOT,
    SOURCE_RELATIVE_PATHS,
    verify_deterministic_strategy_statistical_correction_reference,
)


class DeterministicStrategyStatisticalCorrectionBenchmarkV1Tests(
    unittest.TestCase
):
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
            verify_deterministic_strategy_statistical_correction_reference()
        )

    def test_reference_verifies_179_bound_runs_and_zero_statistical_backtests(
        self,
    ) -> None:
        self.assertEqual(self.verification["status"], "PASS")
        self.assertEqual(self.verification["total_executed_run_count"], 179)
        self.assertEqual(
            self.verification["total_dependency_bound_run_count"],
            179,
        )
        self.assertEqual(self.verification["git_bound_run_count"], 0)
        self.assertEqual(
            self.verification["matrix_dependency_bound_run_count"],
            18,
        )
        self.assertTrue(all(self.verification["checks"].values()))

    def test_reference_is_compact_and_excludes_statistical_values(self) -> None:
        self.assertEqual(
            sorted(
                path.name for path in REFERENCE_ROOT.iterdir() if path.is_file()
            ),
            sorted(REFERENCE_FILE_NAMES),
        )
        self.assertLess(
            (REFERENCE_ROOT / "expected_receipt.json").stat().st_size,
            32768,
        )
        text = (REFERENCE_ROOT / "expected_receipt.json").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "deflated_sharpe_probability",
            "pbo_nonpositive_logit_rate",
            "pbo_nonpositive_logit_lower_bound",
            "pbo_nonpositive_logit_upper_bound",
            "strategy_records",
        ):
            self.assertNotIn(forbidden, text)

    def test_dsr_pbo_and_tie_coverage_is_exact(self) -> None:
        self.assertEqual(
            self.receipt["deflated_sharpe_diagnostic_count"],
            6,
        )
        self.assertEqual(
            self.receipt["cscv_pbo_observed_evidence_count"],
            4,
        )
        self.assertEqual(self.receipt["cscv_pbo_gap_evidence_count"], 2)
        self.assertEqual(
            self.receipt["cscv_pbo_gap_strategy_ids"],
            ["dual_ma", "grid"],
        )
        self.assertEqual(
            self.receipt["tie_bounds_point_identified_strategy_ids"],
            ["bollinger", "macd", "momentum", "rsi"],
        )
        self.assertEqual(
            self.receipt["tie_bounds_partial_interval_strategy_ids"],
            ["grid"],
        )
        self.assertEqual(
            self.receipt["tie_bounds_full_unit_interval_strategy_ids"],
            ["dual_ma"],
        )
        self.assertEqual(self.receipt["tie_bounds_retained_split_count"], 420)
        self.assertFalse(self.receipt["formal_inference_claimed"])
        self.assertIsNone(self.receipt["decision_threshold"])

    def test_manifest_binds_declared_statistical_source_closure(self) -> None:
        self.assertEqual(
            set(self.manifest["source_files"]),
            set(SOURCE_RELATIVE_PATHS),
        )
        for path in (
            "src/hakimi_research/synthetic_strategy_deflated_sharpe_validation.py",
            "src/hakimi_research/synthetic_strategy_cscv_pbo_validation.py",
            "src/hakimi_research/synthetic_strategy_cscv_pbo_tie_bounds.py",
        ):
            self.assertIn(path, self.manifest["source_files"])

    def test_renderer_and_permissions_remain_neutral(self) -> None:
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, self.markdown)
        self.assertIn("No formal inference or decision threshold", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertTrue(
            all(value is False for value in self.receipt["authority"].values())
        )
        self.assertTrue(
            all(value is False for value in self.receipt["claims"].values())
        )


if __name__ == "__main__":
    unittest.main()
