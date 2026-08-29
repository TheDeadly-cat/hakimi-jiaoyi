from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_candidate_registration import (
    AVAILABILITY_SCOPE,
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_date_grid_candidate_registration,
    verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration,
)
from tests.test_strategy_correlation_cluster_temporal_date_grid_protocol import (
    StrategyCorrelationClusterTemporalDateGridProtocolTests,
)


class StrategyCorrelationClusterTemporalDateGridCandidateRegistrationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source_case = StrategyCorrelationClusterTemporalDateGridProtocolTests(
            methodName="test_valid_registration_inherits_v8_and_targets_report22"
        )
        self.source_case.setUp()

    def _source(self):
        return self.source_case._registration()

    def _registration(self):
        return (
            build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                self._source()
            )
        )

    def test_valid_registration_inherits_v9_and_exposes_candidate_capabilities(self):
        registration = self._registration()
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(registration["schema_version"], REGISTRATION_SCHEMA_VERSION)
        self.assertEqual(
            registration["source_registration"]["schema_version"],
            SOURCE_REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(registration["target_report_schema_version"], 22)
        self.assertEqual(
            registration["target_protocol_schema_version"],
            "strategy-matrix-protocol-v11",
        )
        self.assertTrue(registration["report22_consumer_candidate_available"])
        self.assertTrue(registration["report22_builder_candidate_available"])
        self.assertEqual(registration["status"], "CANDIDATE_IMPLEMENTED")

    def test_capability_policy_binds_consumer_builder_and_scope(self):
        registration = self._registration()
        policy = registration["candidate_capability_policy"]
        self.assertEqual(policy["schema_version"], POLICY_SCHEMA_VERSION)
        self.assertTrue(policy["report22_consumer_callable_bound"])
        self.assertTrue(policy["report22_builder_callable_bound"])
        self.assertEqual(policy["availability_scope"], AVAILABILITY_SCOPE)
        self.assertEqual(
            policy["report22_consumer_callable_name"],
            "verify_strategy_correlation_cluster_temporal_date_grid_report_extension",
        )
        self.assertEqual(
            policy["report22_builder_callable_name"],
            "build_strategy_correlation_cluster_temporal_date_grid_report_extension",
        )
        self.assertEqual(
            registration["candidate_capability_policy_hash"],
            policy["policy_hash"],
        )

    def test_source_v9_snapshot_remains_unmodified_and_unavailable(self):
        source = self._source()
        before = deepcopy(source)
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                source
            )
        )
        self.assertTrue(strict_json_contract_equal(source, before))
        self.assertFalse(source["report22_consumer_available"])
        self.assertFalse(source["report22_writer_available"])
        self.assertTrue(registration["report22_consumer_candidate_available"])
        self.assertFalse(registration["writer_available"])

    def test_validation_migration_writer_and_current_authority_remain_false(self):
        registration = self._registration()
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
        self.assertFalse(registration["targeted_contract_validation_embedded"])
        self.assertFalse(registration["candidate_validation_authority"])
        self.assertFalse(registration["migration_assessment_available"])
        self.assertFalse(registration["migration_execution_allowed"])
        self.assertFalse(registration["fresh_migration_allowed"])
        self.assertFalse(verification["report22_candidate_activation_allowed"])
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_invalid_source_v9_blocks_registration(self):
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                {}
            )
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v9_invalid", verification["blockers"])
        self.assertFalse(verification["report22_consumer_candidate_available"])

    def test_resealed_source_v9_drift_is_rejected(self):
        source = deepcopy(self._source())
        source["date_grid_policy_preregistered"] = False
        source = seal_strict_canonical_document(source, "registration_hash")
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                source
            )
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v9_invalid", verification["blockers"])

    def test_resealed_capability_policy_drift_is_rejected(self):
        registration = deepcopy(self._registration())
        policy = registration["candidate_capability_policy"]
        policy["migration_assessment_available"] = True
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["candidate_capability_policy"] = policy
        registration["candidate_capability_policy_hash"] = policy["policy_hash"]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "date_grid_candidate_registration_contract_invalid",
            verification["blockers"],
        )

    def test_native_alias_and_authority_escalation_fail_closed(self):
        registration = self._registration()
        alias = deepcopy(registration)
        alias["target_report_schema_version"] = 22.0
        alias = seal_strict_canonical_document(alias, "registration_hash")
        authority = deepcopy(registration)
        authority["permissions"]["live_order_allowed"] = True
        authority = seal_strict_canonical_document(
            authority,
            "registration_hash",
        )
        alias_verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                alias
            )
        )
        authority_verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
                authority
            )
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(authority_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation",
            authority_verification["blockers"],
        )
        self.assertFalse(
            authority_verification["permissions"]["live_order_allowed"]
        )

    def test_targets_are_exact_and_exports_have_no_activation_path(self):
        registration = self._registration()
        self.assertEqual(
            registration["target_report_schema_version"],
            TARGET_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_protocol_schema_version"],
            TARGET_PROTOCOL_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_extension_schema_version"],
            TARGET_EXTENSION_SCHEMA_VERSION,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_candidate_registration as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("activate_report22", exports)
        self.assertNotIn("migrate_report22", exports)
        self.assertNotIn("write_report22", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
