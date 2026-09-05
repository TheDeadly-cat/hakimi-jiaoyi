from __future__ import annotations

import ast
import copy
from hashlib import sha256
from pathlib import Path
import unittest

import exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 as compatibility
import hakimi_research.synthetic_strategy_trial_return_matrix as canonical
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
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
    / "synthetic_strategy_trial_return_matrix_v1.py"
)
ARCHIVE_PATH = (
    REPO_ROOT
    / "archive"
    / "historical_research"
    / "adr0574_synthetic_strategy_trial_return_matrix_v1.py"
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


def _reseal(record: dict, field: str) -> None:
    record[field] = canonical_trial_return_matrix_sha256(
        {key: value for key, value in record.items() if key != field}
    )


class SyntheticStrategyTrialReturnMatrixV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = _context()
        cls.baseline = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=cls.context,
        )
        cls.plan = canonical.plan_synthetic_strategy_trial_return_matrix_v2()
        cls.bundle = canonical.build_synthetic_strategy_trial_return_matrix_v2(
            cls.baseline,
            execute=True,
        )

    def test_01_plan_preregisters_v2_sources_and_zero_extra_backtests(self) -> None:
        self.assertEqual(
            self.plan["schema_version"],
            "synthetic-strategy-trial-return-matrix-plan-v2",
        )
        self.assertEqual(
            self.plan["source_baseline_schema_version"],
            "synthetic-strategy-report-bundle-v2",
        )
        self.assertEqual(
            self.plan["source_robustness_schema_version"],
            "synthetic-strategy-robustness-evidence-v2",
        )
        self.assertEqual(self.plan["planned_run_count"], 147)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_bundle_verifies_all_sources_and_six_matrices(self) -> None:
        receipt = canonical.verify_synthetic_strategy_trial_return_matrix_v2(
            self.bundle
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["trial_count"], 18)
        self.assertEqual(receipt["observation_count_per_trial"], 169)
        self.assertEqual(receipt["executed_run_count"], 147)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertEqual(receipt["source_dependency_bound_run_count"], 179)
        self.assertEqual(receipt["source_git_bound_run_count"], 0)
        self.assertEqual(receipt["matrix_dependency_bound_run_count"], 18)

    def test_03_all_candidate_manifests_bind_context_plan_and_role(self) -> None:
        manifests = [
            row["source_run"]["result"]["experiment_manifest"]
            for record in self.bundle["strategy_records"]
            for row in record["trial_return_matrix"]["candidate_rows"]
        ]
        self.assertEqual(len(manifests), 18)
        for manifest in manifests:
            self.assertEqual(
                manifest["dependency_lock_hash"],
                self.context["dependency_lock_hash"],
            )
            self.assertEqual(manifest["evaluation_role"], "FROZEN_TEST")
            self.assertEqual(
                manifest["evaluation_protocol_hash"],
                self.bundle["source_robustness_bundle"]["plan"][
                    "plan_sha256"
                ],
            )
            self.assertTrue(manifest["evaluation_protocol_verified"])
            self.assertIn("git_worktree_not_clean", manifest["blockers"])

    def test_04_v1_consumer_rejects_v2_baseline_before_147_runs(self) -> None:
        with self.assertRaises(
            canonical.SyntheticStrategyTrialReturnMatrixError
        ):
            canonical.build_synthetic_strategy_trial_return_matrix_v1(
                self.baseline,
                execute=True,
            )

    def test_05_context_and_authority_tamper_fail_after_outer_reseal(self) -> None:
        context_tamper = copy.deepcopy(self.bundle)
        context_tamper["reproducibility_context"][
            "dependency_lock_hash"
        ] = "f" * 64
        _reseal(context_tamper, "bundle_sha256")
        with self.assertRaises(
            canonical.SyntheticStrategyTrialReturnMatrixError
        ):
            canonical.verify_synthetic_strategy_trial_return_matrix_v2(
                context_tamper
            )

        authority_tamper = copy.deepcopy(self.bundle)
        authority_tamper["authority"]["live_authorized"] = True
        _reseal(authority_tamper, "bundle_sha256")
        with self.assertRaises(
            canonical.SyntheticStrategyTrialReturnMatrixError
        ):
            canonical.verify_synthetic_strategy_trial_return_matrix_v2(
                authority_tamper
            )

    def test_06_exact_native_bundle_and_compatibility_identity(self) -> None:
        with self.assertRaises(Exception):
            canonical.verify_synthetic_strategy_trial_return_matrix_v2(
                HostileDict(self.bundle)
            )
        self.assertIs(
            compatibility.build_synthetic_strategy_trial_return_matrix_v1,
            canonical.build_synthetic_strategy_trial_return_matrix_v1,
        )
        self.assertIs(
            compatibility.build_synthetic_strategy_trial_return_matrix_v2,
            canonical.build_synthetic_strategy_trial_return_matrix_v2,
        )

    def test_07_wrapper_is_definition_free_and_archive_is_exact(self) -> None:
        tree = ast.parse(WRAPPER_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(
            any(isinstance(node, definitions) for node in ast.walk(tree))
        )
        self.assertEqual(
            sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "e01d3c4da7e6320aadaece72e1ba52caec18d294746957694654d253ae52ae3a",
        )

    def test_08_renderer_is_neutral_and_preserves_statistical_gaps(self) -> None:
        markdown = (
            canonical.render_synthetic_strategy_trial_return_matrix_markdown_v2(
                self.bundle
            )
        )
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertIn("not a DSR or PBO result", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)


if __name__ == "__main__":
    unittest.main()
