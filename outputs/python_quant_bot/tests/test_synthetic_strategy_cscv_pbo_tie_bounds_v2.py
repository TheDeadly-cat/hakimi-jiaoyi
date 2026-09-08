from __future__ import annotations

import ast
import copy
from hashlib import sha256
from pathlib import Path
import unittest

import exchange_terminal.application.synthetic_strategy_cscv_pbo_tie_bounds_v1 as compatibility
import hakimi_research.synthetic_strategy_cscv_pbo_tie_bounds as canonical
from hakimi_research.synthetic_strategy_cscv_pbo_validation import (
    build_synthetic_strategy_cscv_pbo_validation_v2,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v2,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER_PATH = (
    REPO_ROOT
    / "outputs"
    / "python_quant_bot"
    / "exchange_terminal"
    / "application"
    / "synthetic_strategy_cscv_pbo_tie_bounds_v1.py"
)
ARCHIVE_PATH = (
    REPO_ROOT
    / "archive"
    / "historical_research"
    / "adr0577_synthetic_strategy_cscv_pbo_tie_bounds_v1.py"
)


class HostileDict(dict):
    pass


def _context() -> dict[str, object]:
    lock = (REPO_ROOT / "requirements.research.lock").read_bytes()
    return {
        "schema_version": "synthetic-strategy-reference-context-v1",
        "git_commit_sha": "0" * 40,
        "git_worktree_clean": False,
        "dependency_lock_hash": sha256(lock).hexdigest(),
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "runtime_version": "python-3.14",
    }


def _reseal(record: dict) -> None:
    record["bundle_sha256"] = canonical_trial_return_matrix_sha256(
        {
            key: value
            for key, value in record.items()
            if key != "bundle_sha256"
        }
    )


class SyntheticStrategyCscvPboTieBoundsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = _context()
        baseline = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=cls.context,
        )
        matrix = build_synthetic_strategy_trial_return_matrix_v2(
            baseline,
            execute=True,
        )
        cls.pbo = build_synthetic_strategy_cscv_pbo_validation_v2(
            matrix,
            execute=True,
        )
        cls.plan = canonical.plan_synthetic_strategy_cscv_pbo_tie_bounds_v2()
        cls.bundle = canonical.build_synthetic_strategy_cscv_pbo_tie_bounds_v2(
            cls.pbo,
            execute=True,
        )

    def test_01_plan_binds_v2_source_identified_sets_and_zero_runs(self) -> None:
        self.assertEqual(
            self.plan["schema_version"],
            "synthetic-strategy-cscv-pbo-tie-bounds-plan-v2",
        )
        self.assertEqual(
            self.plan["source_cscv_schema_version"],
            "synthetic-strategy-cscv-pbo-validation-bundle-v2",
        )
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(
            self.plan["expected_point_identified_strategy_ids"],
            ["bollinger", "macd", "momentum", "rsi"],
        )
        self.assertEqual(
            self.plan["expected_partial_interval_strategy_ids"],
            ["grid"],
        )
        self.assertEqual(
            self.plan["expected_full_unit_interval_strategy_ids"],
            ["dual_ma"],
        )
        self.assertEqual(
            self.plan["expected_retained_split_bound_count"],
            420,
        )

    def test_02_bundle_verifies_coverage_provenance_and_zero_runs(self) -> None:
        receipt = canonical.verify_synthetic_strategy_cscv_pbo_tie_bounds_v2(
            self.bundle
        )
        self.assertEqual(receipt["state"], "OBSERVED_WITH_GAPS")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["point_identified_evidence_count"], 4)
        self.assertEqual(receipt["partial_interval_evidence_count"], 1)
        self.assertEqual(receipt["full_unit_interval_evidence_count"], 1)
        self.assertEqual(receipt["retained_split_bound_count"], 420)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertEqual(receipt["source_dependency_bound_run_count"], 179)
        self.assertEqual(receipt["source_git_bound_run_count"], 0)
        self.assertEqual(receipt["matrix_dependency_bound_run_count"], 18)
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertIsNone(receipt["decision_threshold"])

    def test_03_point_partial_and_full_membership_is_exact(self) -> None:
        qualities = {
            record["strategy_id"]: record["bound_quality"]
            for record in self.bundle["strategy_records"]
        }
        self.assertEqual(qualities["grid"], "PARTIAL_IDENTIFIED_SET")
        self.assertEqual(qualities["dual_ma"], "FULL_UNIT_INTERVAL")
        self.assertEqual(
            {
                strategy_id
                for strategy_id, quality in qualities.items()
                if quality == "POINT_IDENTIFIED"
            },
            {"bollinger", "macd", "momentum", "rsi"},
        )
        self.assertTrue(
            all(
                record["tie_bounds_diagnostic"]["retained_split_count"] == 70
                for record in self.bundle["strategy_records"]
            )
        )

    def test_04_v1_consumer_rejects_v2_pbo_before_analysis(self) -> None:
        with self.assertRaises(
            canonical.SyntheticStrategyCscvPboTieBoundsError
        ):
            canonical.build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
                self.pbo,
                execute=True,
            )

    def test_05_provenance_coverage_and_policy_tamper_fail_closed(self) -> None:
        mutations = (
            lambda value: value["reproducibility_context"].__setitem__(
                "dependency_lock_hash",
                "f" * 64,
            ),
            lambda value: value.__setitem__(
                "source_dependency_bound_run_count",
                178,
            ),
            lambda value: value.__setitem__(
                "retained_split_bound_count",
                419,
            ),
            lambda value: value["plan"]["policy"].__setitem__(
                "interval_midpoint_reported_as_pbo",
                True,
            ),
            lambda value: value["authority"].__setitem__(
                "live_authorized",
                True,
            ),
        )
        for mutate in mutations:
            tampered = copy.deepcopy(self.bundle)
            mutate(tampered)
            _reseal(tampered)
            with self.assertRaises(
                canonical.SyntheticStrategyCscvPboTieBoundsError
            ):
                canonical.verify_synthetic_strategy_cscv_pbo_tie_bounds_v2(
                    tampered
                )

    def test_06_exact_native_wrapper_and_archive_boundaries(self) -> None:
        with self.assertRaises(Exception):
            canonical.verify_synthetic_strategy_cscv_pbo_tie_bounds_v2(
                HostileDict(self.bundle)
            )
        self.assertIs(
            compatibility.build_synthetic_strategy_cscv_pbo_tie_bounds_v1,
            canonical.build_synthetic_strategy_cscv_pbo_tie_bounds_v1,
        )
        self.assertIs(
            compatibility.build_synthetic_strategy_cscv_pbo_tie_bounds_v2,
            canonical.build_synthetic_strategy_cscv_pbo_tie_bounds_v2,
        )
        tree = ast.parse(WRAPPER_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(
            any(isinstance(node, definitions) for node in ast.walk(tree))
        )
        self.assertEqual(
            sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "414b45415e635893791b2b5404d3d5933e5353899687d7541db511edfaeb500f",
        )

    def test_07_replay_is_exact_and_executes_zero_backtests(self) -> None:
        receipt = canonical.replay_synthetic_strategy_cscv_pbo_tie_bounds_v2(
            self.bundle
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_08_renderer_is_neutral_and_preserves_uninformative_bound(self) -> None:
        markdown = canonical.render_synthetic_strategy_cscv_pbo_tie_bounds_markdown_v2(
            self.bundle
        )
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertIn("No arbitrary tie-break", markdown)
        self.assertIn("Full-unit bounds remain explicitly uninformative", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)


if __name__ == "__main__":
    unittest.main()
