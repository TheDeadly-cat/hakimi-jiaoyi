from __future__ import annotations

import ast
import copy
from hashlib import sha256
from pathlib import Path
import unittest

import exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 as compatibility
import hakimi_research.synthetic_strategy_cscv_pbo_validation as canonical
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
    / "synthetic_strategy_cscv_pbo_validation_v1.py"
)
ARCHIVE_PATH = (
    REPO_ROOT
    / "archive"
    / "historical_research"
    / "adr0576_synthetic_strategy_cscv_pbo_validation_v1.py"
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


class SyntheticStrategyCscvPboValidationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = _context()
        cls.baseline = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=cls.context,
        )
        cls.matrix = build_synthetic_strategy_trial_return_matrix_v2(
            cls.baseline,
            execute=True,
        )
        cls.plan = canonical.plan_synthetic_strategy_cscv_pbo_validation_v2()
        cls.bundle = canonical.build_synthetic_strategy_cscv_pbo_validation_v2(
            cls.matrix,
            execute=True,
        )

    def test_01_plan_binds_v2_matrix_coverage_and_zero_runs(self) -> None:
        self.assertEqual(
            self.plan["schema_version"],
            "synthetic-strategy-cscv-pbo-validation-plan-v2",
        )
        self.assertEqual(
            self.plan["source_matrix_schema_version"],
            "synthetic-strategy-trial-return-matrix-bundle-v2",
        )
        self.assertEqual(self.plan["source_required_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["expected_observed_evidence_count"], 4)
        self.assertEqual(self.plan["expected_gap_evidence_count"], 2)
        self.assertEqual(
            self.plan["expected_gap_strategy_ids"],
            ["dual_ma", "grid"],
        )

    def test_02_bundle_verifies_provenance_and_gap_coverage(self) -> None:
        receipt = canonical.verify_synthetic_strategy_cscv_pbo_validation_v2(
            self.bundle
        )
        self.assertEqual(receipt["state"], "GAP")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["observed_evidence_count"], 4)
        self.assertEqual(receipt["gap_evidence_count"], 2)
        self.assertEqual(receipt["gap_strategy_ids"], ["dual_ma", "grid"])
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertEqual(receipt["source_dependency_bound_run_count"], 179)
        self.assertEqual(receipt["source_git_bound_run_count"], 0)
        self.assertEqual(receipt["matrix_dependency_bound_run_count"], 18)
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertIsNone(receipt["decision_threshold"])

    def test_03_all_splits_retained_and_ties_stay_gap(self) -> None:
        for record in self.bundle["strategy_records"]:
            diagnostic = record["cscv_pbo_diagnostic"]
            self.assertEqual(len(diagnostic["splits"]), 70)
            self.assertEqual(
                diagnostic["observed_split_count"]
                + diagnostic["gap_split_count"],
                70,
            )
            if record["strategy_id"] in {"dual_ma", "grid"}:
                self.assertEqual(record["evidence_state"], "GAP")
                self.assertEqual(diagnostic["gap_split_count"], 70)
                self.assertIsNone(
                    diagnostic["pbo_nonpositive_logit_rate"]
                )
            else:
                self.assertEqual(record["evidence_state"], "OBSERVED")
                self.assertEqual(diagnostic["observed_split_count"], 70)

    def test_04_v1_consumer_rejects_v2_matrix_before_analysis(self) -> None:
        with self.assertRaises(canonical.SyntheticStrategyCscvPboValidationError):
            canonical.build_synthetic_strategy_cscv_pbo_validation_v1(
                self.matrix,
                execute=True,
            )

    def test_05_provenance_coverage_and_authority_tamper_fail_closed(self) -> None:
        mutations = (
            lambda value: value["reproducibility_context"].__setitem__(
                "dependency_lock_hash",
                "f" * 64,
            ),
            lambda value: value.__setitem__(
                "source_dependency_bound_run_count",
                178,
            ),
            lambda value: value.__setitem__("gap_evidence_count", 1),
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
                canonical.SyntheticStrategyCscvPboValidationError
            ):
                canonical.verify_synthetic_strategy_cscv_pbo_validation_v2(
                    tampered
                )

    def test_06_exact_native_wrapper_and_archive_boundaries(self) -> None:
        with self.assertRaises(Exception):
            canonical.verify_synthetic_strategy_cscv_pbo_validation_v2(
                HostileDict(self.bundle)
            )
        self.assertIs(
            compatibility.build_synthetic_strategy_cscv_pbo_validation_v1,
            canonical.build_synthetic_strategy_cscv_pbo_validation_v1,
        )
        self.assertIs(
            compatibility.build_synthetic_strategy_cscv_pbo_validation_v2,
            canonical.build_synthetic_strategy_cscv_pbo_validation_v2,
        )
        tree = ast.parse(WRAPPER_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(
            any(isinstance(node, definitions) for node in ast.walk(tree))
        )
        self.assertEqual(
            sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "20c77e62dd7c1ea7f49010135bd48ce96df1da722d838207cb739e7c35dfdae1",
        )

    def test_07_replay_is_exact_and_executes_zero_backtests(self) -> None:
        receipt = canonical.replay_synthetic_strategy_cscv_pbo_validation_v2(
            self.bundle
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_08_renderer_is_neutral_and_preserves_tie_gap(self) -> None:
        markdown = canonical.render_synthetic_strategy_cscv_pbo_validation_markdown_v2(
            self.bundle
        )
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertIn("Rank ties remain GAP", markdown)
        self.assertIn("without a decision threshold", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)


if __name__ == "__main__":
    unittest.main()
