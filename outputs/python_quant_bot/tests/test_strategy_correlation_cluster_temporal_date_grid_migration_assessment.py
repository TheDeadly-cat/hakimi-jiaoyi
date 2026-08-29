from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    MODE_DRY_RUN,
    MODE_LIST,
    PLANNED_STEP_COUNT,
    assess_strategy_correlation_cluster_temporal_date_grid_migration,
    verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment,
)
from tests.test_strategy_correlation_cluster_temporal_date_grid_candidate_registration import (
    StrategyCorrelationClusterTemporalDateGridCandidateRegistrationTests,
)
from tests.test_strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    StrategyCorrelationClusterTemporalDateGridReportConsumerTests,
)


class StrategyCorrelationClusterTemporalDateGridMigrationAssessmentTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration_case = (
            StrategyCorrelationClusterTemporalDateGridCandidateRegistrationTests(
                methodName=(
                    "test_valid_registration_inherits_v9_and_exposes_candidate_capabilities"
                )
            )
        )
        self.registration_case.setUp()
        self.report_case = (
            StrategyCorrelationClusterTemporalDateGridReportConsumerTests(
                methodName="test_valid_report22_passes_contract_and_decision"
            )
        )
        self.report_case.setUp()
        self.addCleanup(self.report_case.doCleanups)

    def _registration(self):
        return self.registration_case._registration()

    def _dry_run_arguments(self, *, misaligned=False):
        report22, arguments, date_grid_binding = self.report_case._fixture(
            misaligned=misaligned
        )
        registration = self._registration()
        return {
            "candidate_registration": registration,
            "mode": MODE_DRY_RUN,
            "expected_candidate_registration_hash": registration[
                "registration_hash"
            ],
            "report22_extension": report22,
            "expected_report22_extension_hash": report22["extension_hash"],
            "expected_base_report_hash": arguments[
                "expected_base_report_hash"
            ],
            "expected_global_independence_extension_hash": arguments[
                "expected_global_independence_extension_hash"
            ],
            "expected_cluster_stability_extension_hash": arguments[
                "expected_cluster_stability_extension_hash"
            ],
            "expected_report21_extension_hash": arguments[
                "expected_report21_extension_hash"
            ],
            "expected_registry_bindings": arguments[
                "expected_registry_bindings"
            ],
            "expected_stability_bindings": arguments[
                "expected_stability_bindings"
            ],
            "expected_temporal_stability_bindings": arguments[
                "expected_temporal_stability_bindings"
            ],
            "expected_temporal_date_grid_bindings": [date_grid_binding],
        }

    @staticmethod
    def _assess(arguments):
        values = deepcopy(arguments)
        registration = values.pop("candidate_registration")
        return assess_strategy_correlation_cluster_temporal_date_grid_migration(
            registration,
            **values,
        )

    @staticmethod
    def _verify(document, arguments):
        return verify_strategy_correlation_cluster_temporal_date_grid_migration_assessment(
            document,
            **deepcopy(arguments),
        )

    def test_list_mode_plans_three_steps_without_report_or_execution(self):
        registration = self._registration()
        arguments = {
            "candidate_registration": registration,
            "mode": MODE_LIST,
            "expected_candidate_registration_hash": registration[
                "registration_hash"
            ],
        }
        assessment = self._assess(arguments)
        verification = self._verify(assessment, arguments)
        self.assertEqual(assessment["status"], "PLAN_LISTED")
        self.assertEqual(assessment["planned"], PLANNED_STEP_COUNT)
        self.assertEqual(assessment["executed"], 0)
        self.assertFalse(assessment["runtime_mutations"])
        self.assertEqual(assessment["report22_decision"], "NOT_EVALUATED")
        self.assertEqual(
            [item["status"] for item in assessment["plan"]],
            ["VERIFIED", "NOT_EVALUATED", "PLANNED"],
        )
        self.assertEqual(verification["status"], "PASS")

    def test_dry_run_verifies_pass_report_without_execution(self):
        arguments = self._dry_run_arguments()
        assessment = self._assess(arguments)
        verification = self._verify(assessment, arguments)
        self.assertEqual(assessment["status"], "DRY_RUN_VERIFIED")
        self.assertEqual(assessment["report22_decision"], "PASS")
        self.assertEqual(assessment["executed"], 0)
        self.assertFalse(assessment["runtime_mutations"])
        self.assertTrue(assessment["migration_prerequisites_observed"])
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["assessment_status"], "DRY_RUN_VERIFIED")

    def test_dry_run_preserves_valid_block_report_decision(self):
        arguments = self._dry_run_arguments(misaligned=True)
        assessment = self._assess(arguments)
        verification = self._verify(assessment, arguments)
        self.assertEqual(assessment["status"], "DRY_RUN_VERIFIED")
        self.assertEqual(assessment["report22_decision"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["report22_decision"], "BLOCK")

    def test_invalid_registration_or_independent_hash_blocks(self):
        arguments = self._dry_run_arguments()
        invalid = deepcopy(arguments)
        invalid["candidate_registration"] = {}
        wrong_hash = deepcopy(arguments)
        wrong_hash["expected_candidate_registration_hash"] = "a" * 64
        invalid_assessment = self._assess(invalid)
        wrong_hash_assessment = self._assess(wrong_hash)
        self.assertEqual(invalid_assessment["status"], "BLOCK")
        self.assertFalse(
            invalid_assessment["facts"][
                "candidate_registration_v10_verified"
            ]
        )
        self.assertEqual(wrong_hash_assessment["status"], "BLOCK")
        self.assertFalse(
            wrong_hash_assessment["facts"][
                "candidate_registration_hash_bound"
            ]
        )

    def test_invalid_report_or_independent_hash_blocks_dry_run(self):
        arguments = self._dry_run_arguments()
        invalid = deepcopy(arguments)
        invalid["report22_extension"] = {}
        wrong_hash = deepcopy(arguments)
        wrong_hash["expected_report22_extension_hash"] = "b" * 64
        invalid_assessment = self._assess(invalid)
        wrong_hash_assessment = self._assess(wrong_hash)
        self.assertEqual(invalid_assessment["status"], "BLOCK")
        self.assertFalse(
            invalid_assessment["facts"][
                "report22_extension_verified_in_dry_run"
            ]
        )
        self.assertEqual(wrong_hash_assessment["status"], "BLOCK")
        self.assertFalse(
            wrong_hash_assessment["facts"][
                "report22_extension_hash_bound_in_dry_run"
            ]
        )

    def test_list_mode_rejects_supplied_report_and_fresh_mode(self):
        arguments = self._dry_run_arguments()
        arguments["mode"] = MODE_LIST
        assessment = self._assess(arguments)
        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(
            assessment["facts"]["report22_not_evaluated_in_list_mode"]
        )
        with self.assertRaisesRegex(ValueError, "mode_invalid"):
            assess_strategy_correlation_cluster_temporal_date_grid_migration(
                arguments["candidate_registration"],
                mode="FRESH",
                expected_candidate_registration_hash=arguments[
                    "expected_candidate_registration_hash"
                ],
            )

    def test_resealed_execution_or_runtime_claim_is_rejected(self):
        arguments = self._dry_run_arguments()
        assessment = self._assess(arguments)
        attacked = deepcopy(assessment)
        attacked["executed"] = 1
        attacked["runtime_mutations"] = True
        attacked["migration_execution_allowed"] = True
        attacked = seal_strict_canonical_document(
            attacked,
            "assessment_hash",
        )
        verification = self._verify(attacked, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["executed"], 0)
        self.assertFalse(verification["runtime_mutations"])
        self.assertFalse(verification["migration_execution_allowed"])

    def test_native_alias_and_authority_escalation_fail_closed(self):
        arguments = self._dry_run_arguments()
        assessment = self._assess(arguments)
        alias = deepcopy(assessment)
        alias["planned"] = 3.0
        alias = seal_strict_canonical_document(alias, "assessment_hash")
        authority = deepcopy(assessment)
        authority["permissions"]["live_order_allowed"] = True
        authority = seal_strict_canonical_document(
            authority,
            "assessment_hash",
        )
        alias_verification = self._verify(alias, arguments)
        authority_verification = self._verify(authority, arguments)
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(authority_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation",
            authority_verification["blockers"],
        )

    def test_assessment_does_not_embed_external_assets_or_mutate_inputs(self):
        arguments = self._dry_run_arguments()
        before = deepcopy(arguments)
        assessment = self._assess(arguments)
        self.assertTrue(strict_json_contract_equal(arguments, before))
        self.assertFalse(assessment["external_assets_embedded"])
        self.assertNotIn("candidate_registration", assessment)
        self.assertNotIn("report22_extension", assessment)
        self.assertNotIn("expected_registry_bindings", assessment)
        self.assertNotIn("expected_temporal_stability_bindings", assessment)

    def test_all_io_activation_flags_and_exports_remain_false(self):
        assessment = self._assess(self._dry_run_arguments())
        for field in (
            "runtime_mutations",
            "filesystem_reads",
            "filesystem_writes",
            "cache_reads",
            "cache_writes",
            "database_reads",
            "database_writes",
            "network_calls",
            "service_starts",
            "scheduler_mutations",
            "migration_execution_allowed",
            "fresh_migration_allowed",
            "candidate_activation_allowed",
            "current_admission_allowed",
        ):
            self.assertIs(assessment[field], False)
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_migration_assessment as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("run_migration", exports)
        self.assertNotIn("fresh_migration", exports)
        self.assertNotIn("write_report22", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
