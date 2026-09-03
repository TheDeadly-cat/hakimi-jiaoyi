from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


PYTHON_QUANT_BOT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PYTHON_QUANT_BOT_ROOT.parents[1]
for import_root in (PYTHON_QUANT_BOT_ROOT, WORKSPACE_ROOT / "src"):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from examples.build_synthetic_strategy_benchmark_report_v3 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v3,
)
from examples.build_synthetic_strategy_benchmark_report_v4 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v4,
)
from examples.build_synthetic_strategy_benchmark_report_v5 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v5,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_cscv_pbo_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_deflated_sharpe_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_high_volatility_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_high_volatility_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_reproducibility_provenance_gap_audit_v1 import (  # noqa: E402
    SyntheticStrategyReproducibilityProvenanceGapAuditError,
    _canonical_sha256,
    build_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
    plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
    render_synthetic_strategy_reproducibility_provenance_gap_audit_markdown_v1,
    verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (  # noqa: E402
    build_synthetic_strategy_trial_return_matrix_v1,
)


def _reseal_bundle(bundle: dict) -> None:
    payload = {key: value for key, value in bundle.items() if key != "bundle_sha256"}
    bundle["bundle_sha256"] = _canonical_sha256(payload)


class SyntheticStrategyReproducibilityProvenanceGapAuditV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source_v3 = build_synthetic_strategy_benchmark_report_v3(execute=True)
        baseline = source_v3["source_report_v2"]["source_report_v1"][
            "baseline_bundle"
        ]
        matrix = build_synthetic_strategy_trial_return_matrix_v1(
            baseline, execute=True
        )
        dsr = build_synthetic_strategy_deflated_sharpe_validation_v1(
            matrix, execute=True
        )
        pbo = build_synthetic_strategy_cscv_pbo_validation_v1(
            matrix, execute=True
        )
        source_v4 = build_synthetic_strategy_benchmark_report_v4(
            source_v3, matrix, dsr, pbo, execute=True
        )
        high_volatility = build_synthetic_strategy_high_volatility_validation_v1(
            execute=True
        )
        cls.source_v5 = build_synthetic_strategy_benchmark_report_v5(
            source_v4, high_volatility, execute=True
        )
        cls.bundle = (
            build_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                cls.source_v5, execute=True
            )
        )

    def test_01_plan_fingerprints_critical_sources(self) -> None:
        plan = build_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
            execute=False
        )
        self.assertEqual(
            plan,
            plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1(),
        )
        self.assertEqual(plan["critical_source_manifest"]["module_count"], 18)
        self.assertEqual(len(plan["critical_source_manifest"]["files"]), 18)
        self.assertEqual(
            plan["source_commit_collection_policy"],
            "DO_NOT_CALL_GIT_IN_SYNTHETIC_AUDIT",
        )

    def test_02_dependency_document_is_honestly_unpinned(self) -> None:
        audit = self.bundle["dependency_audit"]
        self.assertEqual(audit["requirement_count"], 15)
        self.assertEqual(audit["exact_pin_count"], 1)
        self.assertEqual(audit["unpinned_count"], 14)
        self.assertFalse(audit["dependency_lock_fully_pinned"])
        self.assertEqual(audit["dependency_lock_identity_state"], "GAP")

    def test_03_bundle_verifies_and_retains_zero_identity_counts(self) -> None:
        receipt = verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
            self.bundle, self.source_v5
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["valid_git_commit_identity_count"], 0)
        self.assertEqual(receipt["fully_pinned_dependency_identity_count"], 0)
        self.assertGreaterEqual(receipt["unique_run_manifest_count"], 7)
        self.assertEqual(receipt["permission"], "BLOCK")

    def test_04_every_manifest_retains_required_blockers(self) -> None:
        required = {
            "dependency_lock_hash_missing_or_invalid",
            "dependency_lock_name_missing_or_invalid",
            "dependency_lock_not_fully_pinned",
            "git_commit_sha_missing_or_invalid",
            "git_worktree_not_clean",
        }
        for manifest in self.bundle["run_manifest_audit"]["manifests"]:
            self.assertTrue(required.issubset(set(manifest["blockers"])))
            self.assertEqual(manifest["status"], "BLOCK")
            self.assertFalse(manifest["ranking_input_allowed"])

    def test_05_build_does_not_call_git_or_subprocess(self) -> None:
        with patch.object(
            subprocess,
            "run",
            side_effect=AssertionError("subprocess must not be called"),
        ):
            rebuilt = (
                build_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                    self.source_v5, execute=True
                )
            )
        self.assertEqual(rebuilt, self.bundle)

    def test_06_resealed_source_manifest_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["critical_source_manifest"]["files"][0]["sha256"] = "0" * 64
        _reseal_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyReproducibilityProvenanceGapAuditError,
            "current source binding mismatch",
        ):
            verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                tampered, self.source_v5
            )

    def test_07_resealed_dependency_promotion_fails_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["dependency_audit"]["dependency_lock_fully_pinned"] = True
        tampered["dependency_audit"]["dependency_lock_identity_state"] = "OBSERVED"
        _reseal_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyReproducibilityProvenanceGapAuditError,
            "current dependency audit mismatch",
        ):
            verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                tampered, self.source_v5
            )

    def test_08_resealed_v5_binding_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["source_report_v5_sha256"] = "0" * 64
        _reseal_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyReproducibilityProvenanceGapAuditError,
            "benchmark v5 source binding mismatch",
        ):
            verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                tampered, self.source_v5
            )

    def test_09_authority_escalation_fails_closed(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyReproducibilityProvenanceGapAuditError,
            "gaps or authority drifted",
        ):
            verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                tampered, self.source_v5
            )

    def test_10_exact_native_subclasses_fail_closed(self) -> None:
        class StringAlias(str):
            pass

        tampered = deepcopy(self.bundle)
        tampered["data_source"] = StringAlias(tampered["data_source"])
        with self.assertRaisesRegex(
            SyntheticStrategyReproducibilityProvenanceGapAuditError,
            "exact finite JSON-native values",
        ):
            verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                tampered, self.source_v5
            )

    def test_11_renderer_is_neutral_and_explicitly_incomplete(self) -> None:
        markdown = (
            render_synthetic_strategy_reproducibility_provenance_gap_audit_markdown_v1(
                self.bundle, self.source_v5
            )
        )
        self.assertIn("| SOURCE | LOCAL_SOURCE_FILES_READ_ONLY |", markdown)
        self.assertIn("| GAP |", markdown)
        self.assertIn("| MATURITY |", markdown)
        self.assertIn("| PERMISSION | BLOCK |", markdown)
        self.assertIn("does not call Git", markdown)
        self.assertIn("Valid Git commit identities: 0", markdown)
        self.assertIn("Fully pinned dependency identities: 0", markdown)
        self.assertNotIn("READY", markdown.upper())

    def test_12_source_manifest_fingerprints_without_dynamic_module_execution(self) -> None:
        with patch(
            "importlib.import_module",
            side_effect=AssertionError("source fingerprinting must not import modules"),
        ):
            plan = plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1()
        self.assertEqual(plan["critical_source_manifest"]["module_count"], 18)


if __name__ == "__main__":
    unittest.main()
