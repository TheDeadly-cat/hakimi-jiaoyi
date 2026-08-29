from copy import deepcopy
import unittest

from tests import test_strategy_correlation_global_independence_protocol as source_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_protocol import (
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_stability_protocol_registration,
    verify_strategy_correlation_cluster_stability_protocol_registration,
)


class StrategyCorrelationClusterStabilityProtocolTests(unittest.TestCase):
    def _source(self):
        fixture = source_fixtures.StrategyCorrelationGlobalIndependenceProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    def _registration(self):
        return build_strategy_correlation_cluster_stability_protocol_registration(
            self._source()
        )

    def test_valid_registration_inherits_v6_and_targets_report20(self):
        registration = self._registration()
        verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            registration
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(registration["schema_version"], REGISTRATION_SCHEMA_VERSION)
        self.assertEqual(
            registration["source_registration"]["schema_version"],
            SOURCE_REGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(registration["target_report_schema_version"], 20)
        self.assertEqual(registration["target_protocol_schema_version"], "strategy-matrix-protocol-v9")
        self.assertEqual(registration["target_extension_schema_version"], TARGET_EXTENSION_SCHEMA_VERSION)

    def test_policy_freezes_stability_gate_and_external_bindings(self):
        policy = self._registration()["cluster_stability_policy"]

        self.assertEqual(policy["schema_version"], POLICY_SCHEMA_VERSION)
        self.assertEqual(policy["family_scope"], "WITHIN_CLUSTER_PAIRS_ONLY")
        self.assertEqual(policy["correction_method"], "BONFERRONI_TWO_SIDED_FWER_V1")
        self.assertEqual(policy["familywise_confidence_level"], 0.95)
        self.assertTrue(policy["stability_gate_exact_rebuild_required"])
        self.assertTrue(policy["external_report19_extension_hash_required"])
        self.assertEqual(
            policy["external_stability_binding_fields"],
            [
                "strategy_id",
                "variant_id",
                "lane",
                "source_uncertainty_audit",
                "correlation_matrix",
                "selection_cells",
                "expected_stability_gate_hash",
            ],
        )

    def test_policy_forbids_payload_copy_and_freezes_writer_prerequisites(self):
        policy = self._registration()["cluster_stability_policy"]

        self.assertEqual(
            policy["report20_payload_excluded_fields"],
            [
                "source_uncertainty_audit",
                "correlation_matrix",
                "selection_cells",
                "return_series",
            ],
        )
        self.assertIn(
            "REPORT20_SOLE_WRITER_IMPLEMENTED",
            policy["writer_activation_prerequisites"],
        )
        self.assertIn(
            "FORMAL_REGISTRY_ACTIVATED",
            policy["writer_activation_prerequisites"],
        )
        self.assertFalse(policy["writer_available"])
        self.assertFalse(policy["current_admission_allowed"])
        self.assertFalse(policy["permissions"]["paper_authorized"])

    def test_invalid_source_v6_blocks_registration(self):
        registration = build_strategy_correlation_cluster_stability_protocol_registration(
            {}
        )

        verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            registration
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v6_invalid", verification["blockers"])

    def test_resealed_source_v6_drift_is_rejected(self):
        source = deepcopy(self._source())
        source["schema19_consumer_available"] = False
        source = seal_strict_canonical_document(source, "registration_hash")
        registration = build_strategy_correlation_cluster_stability_protocol_registration(
            source
        )

        verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            registration
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v6_invalid", verification["blockers"])

    def test_resealed_policy_drift_is_rejected(self):
        registration = deepcopy(self._registration())
        policy = registration["cluster_stability_policy"]
        policy["correction_method"] = "NONE"
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["cluster_stability_policy"] = policy
        registration["cluster_stability_policy_hash"] = policy["policy_hash"]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )

        verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            registration
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("cluster_stability_protocol_contract_invalid", verification["blockers"])

    def test_native_type_alias_and_authority_escalation_are_rejected(self):
        registration = self._registration()
        alias = deepcopy(registration)
        alias["target_report_schema_version"] = 20.0
        alias = seal_strict_canonical_document(alias, "registration_hash")
        escalated = deepcopy(registration)
        escalated["permissions"]["live_order_allowed"] = True
        escalated = seal_strict_canonical_document(escalated, "registration_hash")

        alias_verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            alias
        )
        escalated_verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            escalated
        )

        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", escalated_verification["blockers"])

    def test_builder_does_not_mutate_source_and_hash_binds_nested_policy(self):
        source = self._source()
        before = deepcopy(source)
        registration = build_strategy_correlation_cluster_stability_protocol_registration(
            source
        )

        self.assertTrue(strict_json_contract_equal(source, before))
        self.assertEqual(
            registration["source_registration_hash"],
            source["registration_hash"],
        )
        self.assertEqual(
            registration["cluster_stability_policy_hash"],
            registration["cluster_stability_policy"]["policy_hash"],
        )
        self.assertEqual(registration["status"], "PREREGISTERED")
        self.assertFalse(registration["writer_available"])
        self.assertEqual(registration["target_report_schema_version"], TARGET_REPORT_SCHEMA_VERSION)
        self.assertEqual(registration["target_protocol_schema_version"], TARGET_PROTOCOL_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
