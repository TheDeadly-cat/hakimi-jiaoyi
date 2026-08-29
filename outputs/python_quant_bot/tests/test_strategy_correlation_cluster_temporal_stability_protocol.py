from copy import deepcopy
import unittest

from tests import test_strategy_correlation_cluster_stability_protocol as source_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_protocol import (
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_stability_protocol_registration,
    verify_strategy_correlation_cluster_temporal_stability_protocol_registration,
)


class StrategyCorrelationClusterTemporalStabilityProtocolTests(unittest.TestCase):
    def _source(self):
        fixture = source_fixtures.StrategyCorrelationClusterStabilityProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    def _registration(self):
        return build_strategy_correlation_cluster_temporal_stability_protocol_registration(
            self._source()
        )

    def test_valid_registration_inherits_v7_and_targets_report21(self):
        registration = self._registration()
        verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            registration
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(registration["schema_version"], REGISTRATION_SCHEMA_VERSION)
        self.assertEqual(
            registration["source_registration"]["schema_version"],
            SOURCE_REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(registration["target_report_schema_version"], 21)
        self.assertEqual(
            registration["target_protocol_schema_version"],
            "strategy-matrix-protocol-v10",
        )
        self.assertEqual(
            registration["target_extension_schema_version"],
            TARGET_EXTENSION_SCHEMA_VERSION,
        )

    def test_policy_freezes_windows_family_and_external_bindings(self):
        policy = self._registration()["cluster_temporal_stability_policy"]
        self.assertEqual(policy["schema_version"], POLICY_SCHEMA_VERSION)
        self.assertEqual(policy["lookback_observations"], 60)
        self.assertEqual(policy["window_count"], 3)
        self.assertEqual(policy["window_observations"], 20)
        self.assertEqual(policy["minimum_effective_observations"], 12.0)
        self.assertEqual(policy["absolute_pearson_threshold"], 0.75)
        self.assertEqual(
            policy["family_scope"],
            "WITHIN_CLUSTER_PAIR_X_PREREGISTERED_WINDOW",
        )
        self.assertEqual(
            policy["external_temporal_stability_binding_fields"],
            [
                "strategy_id",
                "variant_id",
                "lane",
                "source_uncertainty_audit",
                "correlation_matrix",
                "selection_cells",
                "expected_temporal_stability_gate_hash",
            ],
        )
        self.assertTrue(policy["temporal_stability_gate_exact_rebuild_required"])
        self.assertTrue(
            policy[
                "complete_link_and_full_window_gate_derived_from_report20_required"
            ]
        )

    def test_policy_forbids_payload_copy_and_freezes_writer_prerequisites(self):
        policy = self._registration()["cluster_temporal_stability_policy"]
        self.assertEqual(
            policy["report21_payload_excluded_fields"],
            [
                "source_uncertainty_audit",
                "correlation_matrix",
                "selection_cells",
                "return_series",
                "completed_price_datasets",
            ],
        )
        self.assertIn(
            "REPORT21_SOLE_WRITER_IMPLEMENTED",
            policy["writer_activation_prerequisites"],
        )
        self.assertIn(
            "FORMAL_REGISTRY_ACTIVATED",
            policy["writer_activation_prerequisites"],
        )
        self.assertIs(policy["writer_available"], False)
        self.assertIs(policy["current_admission_allowed"], False)
        self.assertIs(policy["permissions"]["paper_authorized"], False)

    def test_invalid_source_v7_blocks_registration(self):
        registration = build_strategy_correlation_cluster_temporal_stability_protocol_registration(
            {}
        )
        verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            registration
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v7_invalid", verification["blockers"])

    def test_resealed_source_v7_drift_is_rejected(self):
        source = deepcopy(self._source())
        source["schema20_consumer_available"] = False
        source = seal_strict_canonical_document(source, "registration_hash")
        registration = build_strategy_correlation_cluster_temporal_stability_protocol_registration(
            source
        )
        verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            registration
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v7_invalid", verification["blockers"])

    def test_resealed_policy_drift_is_rejected(self):
        registration = deepcopy(self._registration())
        policy = registration["cluster_temporal_stability_policy"]
        policy["window_count"] = 2
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["cluster_temporal_stability_policy"] = policy
        registration["cluster_temporal_stability_policy_hash"] = policy["policy_hash"]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )
        verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            registration
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "cluster_temporal_stability_protocol_contract_invalid",
            verification["blockers"],
        )

    def test_native_type_alias_and_authority_escalation_are_rejected(self):
        registration = self._registration()
        alias = deepcopy(registration)
        alias["target_report_schema_version"] = 21.0
        alias = seal_strict_canonical_document(alias, "registration_hash")
        escalated = deepcopy(registration)
        escalated["permissions"]["live_order_allowed"] = True
        escalated = seal_strict_canonical_document(escalated, "registration_hash")
        alias_verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            alias
        )
        escalated_verification = verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
            escalated
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation", escalated_verification["blockers"]
        )

    def test_builder_does_not_mutate_source_and_hash_binds_nested_policy(self):
        source = self._source()
        before = deepcopy(source)
        registration = build_strategy_correlation_cluster_temporal_stability_protocol_registration(
            source
        )
        self.assertTrue(strict_json_contract_equal(source, before))
        self.assertEqual(
            registration["source_registration_hash"],
            source["registration_hash"],
        )
        self.assertEqual(
            registration["cluster_temporal_stability_policy_hash"],
            registration["cluster_temporal_stability_policy"]["policy_hash"],
        )
        self.assertEqual(registration["status"], "PREREGISTERED")
        self.assertIs(registration["writer_available"], False)
        self.assertEqual(
            registration["target_report_schema_version"],
            TARGET_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_protocol_schema_version"],
            TARGET_PROTOCOL_SCHEMA_VERSION,
        )


if __name__ == "__main__":
    unittest.main()
