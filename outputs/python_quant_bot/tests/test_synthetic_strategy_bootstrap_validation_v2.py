from __future__ import annotations

import ast
import copy
from hashlib import sha256
from pathlib import Path
import unittest

import exchange_terminal.application.synthetic_strategy_bootstrap_validation_v1 as compatibility
import hakimi_research.synthetic_strategy_bootstrap_validation as canonical
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER_PATH = (
    REPO_ROOT
    / "outputs"
    / "python_quant_bot"
    / "exchange_terminal"
    / "application"
    / "synthetic_strategy_bootstrap_validation_v1.py"
)
ARCHIVE_PATH = (
    REPO_ROOT
    / "archive"
    / "historical_research"
    / "adr0579_synthetic_strategy_bootstrap_validation_v1.py"
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


class SyntheticStrategyBootstrapValidationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = _context()
        cls.baseline = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=cls.context,
        )
        cls.plan = canonical.plan_synthetic_strategy_bootstrap_validation_v2()
        cls.bundle = canonical.build_synthetic_strategy_bootstrap_validation_v2(
            cls.baseline,
            execute=True,
        )

    def test_01_v1_false_acceptance_is_closed(self) -> None:
        with self.assertRaises(
            canonical.SyntheticStrategyBootstrapValidationError
        ):
            canonical.build_synthetic_strategy_bootstrap_validation_v1(
                self.baseline,
                execute=True,
            )

    def test_02_plan_binds_v2_source_and_fixed_bootstrap_policy(self) -> None:
        self.assertEqual(
            self.plan["schema_version"],
            "synthetic-strategy-bootstrap-validation-plan-v2",
        )
        self.assertEqual(
            self.plan["source_baseline_schema_version"],
            "synthetic-strategy-report-bundle-v2",
        )
        self.assertEqual(self.plan["source_required_run_count"], 32)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(
            self.plan["expected_source_dependency_bound_run_count"],
            32,
        )
        self.assertEqual(
            self.plan["expected_paired_observation_count_per_strategy"],
            169,
        )
        self.assertEqual(self.plan["expected_replicate_count"], 1000)
        self.assertFalse(self.plan["formal_inference_claimed"])
        self.assertIsNone(self.plan["decision_threshold"])

    def test_03_bundle_verifies_six_observed_source_bound_records(self) -> None:
        receipt = canonical.verify_synthetic_strategy_bootstrap_validation_v2(
            self.bundle,
            self.baseline,
        )
        self.assertEqual(receipt["state"], "OBSERVED")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["observed_evidence_count"], 6)
        self.assertEqual(receipt["gap_evidence_count"], 0)
        self.assertEqual(receipt["source_dependency_bound_run_count"], 32)
        self.assertEqual(receipt["source_git_bound_run_count"], 0)
        self.assertEqual(
            receipt["paired_observation_count_per_strategy"],
            169,
        )
        self.assertEqual(receipt["replicate_count"], 1000)
        self.assertEqual(receipt["interval_count_per_strategy"], 3)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertIsNone(receipt["decision_threshold"])

    def test_04_source_manifests_and_distribution_hashes_are_bound(self) -> None:
        for record in self.bundle["strategy_records"]:
            evidence = record["bootstrap_evidence"]
            self.assertRegex(evidence["evidence_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                record["bootstrap_receipt"]["paired_observation_count"],
                169,
            )
            self.assertEqual(
                record["bootstrap_receipt"]["replicate_count"],
                1000,
            )
            for interval in evidence["intervals"]:
                self.assertRegex(
                    interval["distribution_sha256"],
                    r"^[0-9a-f]{64}$",
                )

    def test_05_context_coverage_and_authority_tamper_fail_closed(self) -> None:
        mutations = (
            lambda value: value["reproducibility_context"].__setitem__(
                "dependency_lock_hash",
                "f" * 64,
            ),
            lambda value: value.__setitem__(
                "source_dependency_bound_run_count",
                31,
            ),
            lambda value: value.__setitem__(
                "paired_observation_count_per_strategy",
                168,
            ),
            lambda value: value["authority"].__setitem__(
                "live_authorized",
                True,
            ),
        )
        for mutate in mutations:
            tampered = copy.deepcopy(self.bundle)
            mutate(tampered)
            tampered["bundle_sha256"] = canonical._canonical_sha256(
                {
                    key: value
                    for key, value in tampered.items()
                    if key != "bundle_sha256"
                }
            )
            with self.assertRaises(
                canonical.SyntheticStrategyBootstrapValidationError
            ):
                canonical.verify_synthetic_strategy_bootstrap_validation_v2(
                    tampered,
                    self.baseline,
                )

    def test_06_exact_native_wrapper_and_archive_boundaries(self) -> None:
        with self.assertRaises(Exception):
            canonical.verify_synthetic_strategy_bootstrap_validation_v2(
                HostileDict(self.bundle),
                self.baseline,
            )
        self.assertIs(
            compatibility.build_synthetic_strategy_bootstrap_validation_v1,
            canonical.build_synthetic_strategy_bootstrap_validation_v1,
        )
        self.assertIs(
            compatibility.build_synthetic_strategy_bootstrap_validation_v2,
            canonical.build_synthetic_strategy_bootstrap_validation_v2,
        )
        tree = ast.parse(WRAPPER_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(
            any(isinstance(node, definitions) for node in ast.walk(tree))
        )
        self.assertEqual(
            sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "a71aa4c71e36697db0e459a21f654b4f19b9cb2f1347a62d6c51502333ebf19d",
        )

    def test_07_replay_is_exact_and_executes_zero_backtests(self) -> None:
        receipt = canonical.replay_synthetic_strategy_bootstrap_validation_v2(
            self.bundle,
            self.baseline,
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_08_renderer_is_neutral_and_disclaims_formal_inference(self) -> None:
        markdown = canonical.render_synthetic_strategy_bootstrap_validation_markdown_v2(
            self.bundle,
            self.baseline,
        )
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertIn("Formal inference authority: false", markdown)
        self.assertNotIn("READY", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)


if __name__ == "__main__":
    unittest.main()
