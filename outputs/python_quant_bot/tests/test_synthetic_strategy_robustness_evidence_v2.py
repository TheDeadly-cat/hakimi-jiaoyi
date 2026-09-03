from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import platform
import unittest

import exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 as compatibility
import hakimi_research.synthetic_strategy_robustness_evidence as canonical
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _context() -> dict[str, object]:
    lock = (REPO_ROOT / "requirements.research.lock").read_bytes()
    return {
        "schema_version": "synthetic-strategy-reference-context-v1",
        "git_commit_sha": "0" * 40,
        "git_worktree_clean": False,
        "dependency_lock_hash": sha256(lock).hexdigest(),
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "runtime_version": platform.python_version(),
    }


def _reseal(record: dict[str, object], field: str) -> None:
    record[field] = canonical_sha256(
        {key: value for key, value in record.items() if key != field}
    )


class SyntheticStrategyRobustnessEvidenceV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = _context()
        cls.source = build_synthetic_strategy_report_bundle_v2(
            execute=True,
            reproducibility_context=cls.context,
        )
        cls.bundle = canonical.build_synthetic_strategy_robustness_evidence_v2(
            cls.source,
            execute=True,
        )

    def test_01_plan_is_dry_and_preregisters_v2_source_and_147_runs(self) -> None:
        plan = canonical.plan_synthetic_strategy_robustness_evidence_v2()
        self.assertEqual(
            plan["schema_version"],
            "synthetic-strategy-robustness-plan-v2",
        )
        self.assertEqual(
            plan["source_schema_version"],
            "synthetic-strategy-report-bundle-v2",
        )
        self.assertTrue(plan["source_reproducibility_context_required"])
        self.assertEqual(plan["planned_run_count"], 147)
        self.assertEqual(plan["executed_run_count"], 0)
        self.assertFalse(plan["runtime_mutations"])

    def test_02_v2_source_and_all_147_bound_runs_verify(self) -> None:
        receipt = canonical.verify_synthetic_strategy_robustness_evidence_v2(
            self.bundle
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["verified_run_count"], 147)
        self.assertEqual(receipt["dependency_bound_run_count"], 147)
        self.assertEqual(receipt["git_bound_run_count"], 0)
        self.assertEqual(
            self.bundle["reproducibility_context"],
            self.source["reproducibility_context"],
        )
        self.assertNotIn("DEPENDENCY_LOCK_NOT_BOUND", self.bundle["gaps"])

    def test_03_reproducibility_ledger_is_complete_and_role_bounded(self) -> None:
        ledger = self.bundle["run_reproducibility_ledger"]
        self.assertEqual(ledger["run_count"], 147)
        self.assertEqual(len(ledger["records"]), 147)
        self.assertEqual(
            ledger["evaluation_role_counts"],
            {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39},
        )
        self.assertEqual(
            {record["experiment_manifest"]["dependency_lock_hash"]
             for record in ledger["records"]},
            {self.context["dependency_lock_hash"]},
        )
        self.assertTrue(
            all(
                "git_worktree_not_clean"
                in record["experiment_manifest"]["blockers"]
                for record in ledger["records"]
            )
        )

    def test_04_v1_consumer_still_rejects_v2_source_without_running_147(self) -> None:
        with self.assertRaises(canonical.SyntheticStrategyRobustnessError):
            canonical.build_synthetic_strategy_robustness_evidence_v1(
                self.source,
                execute=True,
            )

    def test_05_compatibility_module_reexports_canonical_identities(self) -> None:
        self.assertIs(
            compatibility.build_synthetic_strategy_robustness_evidence_v1,
            canonical.build_synthetic_strategy_robustness_evidence_v1,
        )
        self.assertIs(
            compatibility.build_synthetic_strategy_robustness_evidence_v2,
            canonical.build_synthetic_strategy_robustness_evidence_v2,
        )
        self.assertIs(
            compatibility.verify_synthetic_strategy_robustness_evidence_v2,
            canonical.verify_synthetic_strategy_robustness_evidence_v2,
        )

    def test_06_manifest_tamper_blocks_after_all_seals_are_recomputed(self) -> None:
        tampered = deepcopy(self.bundle)
        record = tampered["run_reproducibility_ledger"]["records"][0]
        record["experiment_manifest"]["dependency_lock_hash"] = "f" * 64
        _reseal(record, "record_sha256")
        _reseal(
            tampered["run_reproducibility_ledger"],
            "ledger_sha256",
        )
        _reseal(tampered, "bundle_sha256")
        receipt = canonical.verify_synthetic_strategy_robustness_evidence_v2(
            tampered
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn(
            "robustness run reproducibility manifest mismatch",
            receipt["blockers"][0],
        )

    def test_07_authority_escalation_and_neutral_renderer_fail_closed(self) -> None:
        escalated = deepcopy(self.bundle)
        escalated["authority"]["live_authorized"] = True
        _reseal(escalated, "bundle_sha256")
        self.assertEqual(
            canonical.verify_synthetic_strategy_robustness_evidence_v2(
                escalated
            )["status"],
            "BLOCK",
        )
        markdown = canonical.render_synthetic_strategy_robustness_markdown_v2(
            self.bundle
        )
        for heading in ("## SOURCE", "## GAP", "## MATURITY", "## PERMISSION"):
            self.assertIn(heading, markdown)
        self.assertNotIn("READY", markdown)


if __name__ == "__main__":
    unittest.main()
