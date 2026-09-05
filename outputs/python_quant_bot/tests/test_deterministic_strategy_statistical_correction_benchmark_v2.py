from __future__ import annotations

import argparse
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import hakimi_research.deterministic_strategy_statistical_correction_benchmark as v1
import hakimi_research.deterministic_strategy_statistical_correction_benchmark_v2 as v2
from hakimi_research.cli import command_strategy_statistical_correction_benchmark


class DeterministicStrategyStatisticalCorrectionBenchmarkV2Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.material = (
            v2.build_deterministic_strategy_statistical_correction_reference_material_v2()
        )
        with patch.object(
            v2,
            "build_deterministic_strategy_statistical_correction_reference_material_v2",
            return_value=cls.material,
        ):
            cls.verification = (
                v2.verify_deterministic_strategy_statistical_correction_reference_v2()
            )
        cls.receipt = cls.material["receipt"]
        cls.manifest = cls.material["manifest"]

    def test_reference_binds_bootstrap_without_additional_backtests(self) -> None:
        self.assertEqual(self.verification["status"], "PASS")
        self.assertEqual(self.verification["total_executed_run_count"], 179)
        self.assertEqual(
            self.verification["total_dependency_bound_run_count"], 179
        )
        self.assertEqual(self.verification["git_bound_run_count"], 0)
        self.assertEqual(self.verification["additional_backtest_run_count"], 0)
        self.assertTrue(all(self.verification["checks"].values()))

    def test_bootstrap_scope_and_replay_are_exact(self) -> None:
        self.assertEqual(self.receipt["bootstrap_observed_evidence_count"], 6)
        self.assertEqual(
            self.receipt["bootstrap_paired_observation_count_per_strategy"],
            169,
        )
        self.assertEqual(self.receipt["bootstrap_replicate_count"], 1000)
        self.assertEqual(
            self.receipt["bootstrap_interval_count_per_strategy"], 3
        )
        self.assertEqual(
            self.receipt["bootstrap_source_dependency_bound_run_count"], 32
        )
        self.assertEqual(self.receipt["bootstrap_replay_status"], "EXACT_MATCH")
        self.assertEqual(
            self.receipt["bootstrap_source_bundle_sha256"],
            self.receipt["source_bundle_sha256"],
        )

    def test_compact_receipt_excludes_raw_statistical_values(self) -> None:
        receipt_bytes = self.material["files"]["expected_receipt.json"].encode(
            "utf-8"
        )
        self.assertLess(len(receipt_bytes), 32768)
        for token in v2._FORBIDDEN_RECEIPT_TOKENS:
            self.assertNotIn(token, receipt_bytes)

    def test_manifest_binds_bootstrap_source_closure(self) -> None:
        self.assertEqual(
            set(self.manifest["source_files"]), set(v2.SOURCE_RELATIVE_PATHS)
        )
        for path in (
            "src/hakimi_research/synthetic_strategy_bootstrap_validation.py",
            "src/hakimi_research/bootstrap_confidence_evidence.py",
        ):
            self.assertIn(path, self.manifest["source_files"])

    def test_v1_receipt_identity_and_default_dispatch_are_unchanged(self) -> None:
        v1_receipt = json.loads(
            (v1.REFERENCE_ROOT / "expected_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        v1_manifest = json.loads(
            (v1.REFERENCE_ROOT / "fixture_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            v1_receipt["receipt_sha256"],
            "c8333dd879913b6caa5417dd9ffdba363c27cbd986c16aa01ffab2368c0c073e",
        )
        self.assertEqual(
            v1_manifest["manifest_sha256"],
            "a412b053e09cc28ea25272e047d744f9229bdfcb3a97df964fd4da5f0d47b922",
        )
        args = argparse.Namespace(statistical_reference_version="v1")
        with patch.object(
            v1,
            "verify_deterministic_strategy_statistical_correction_reference",
            return_value={"status": "PASS", "selected_version": "v1"},
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                command_strategy_statistical_correction_benchmark(args)
        self.assertEqual(json.loads(output.getvalue())["selected_version"], "v1")

    def test_explicit_v2_dispatch_is_consumer_first(self) -> None:
        args = argparse.Namespace(statistical_reference_version="v2")
        with patch.object(
            v2,
            "verify_deterministic_strategy_statistical_correction_reference_v2",
            return_value={"status": "PASS", "selected_version": "v2"},
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                command_strategy_statistical_correction_benchmark(args)
        self.assertEqual(json.loads(output.getvalue())["selected_version"], "v2")

    def test_reference_tamper_fails_closed_without_reexecution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, text in self.material["files"].items():
                (root / name).write_text(text, encoding="utf-8", newline="\n")
            tampered = copy.deepcopy(self.receipt)
            tampered["bootstrap_replicate_count"] = 999
            (root / "expected_receipt.json").write_text(
                json.dumps(tampered, ensure_ascii=True, sort_keys=True, indent=2)
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(
                v2.DeterministicStrategyStatisticalCorrectionBenchmarkV2Error
            ):
                v2._verify_reference_material(root, self.material)

    def test_renderer_and_permissions_remain_neutral(self) -> None:
        markdown = self.material["files"]["expected_receipt.md"]
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(self.receipt["formal_inference_claimed"])
        self.assertIsNone(self.receipt["decision_threshold"])
        self.assertTrue(
            all(value is False for value in self.receipt["authority"].values())
        )
        self.assertTrue(
            all(value is False for value in self.receipt["claims"].values())
        )


if __name__ == "__main__":
    unittest.main()
