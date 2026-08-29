from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    DATE_GRID_RULE,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_protocol import (
    POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION,
    SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_date_grid_protocol_registration,
    verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration,
)
from tests.test_strategy_correlation_cluster_temporal_stability_protocol import (
    StrategyCorrelationClusterTemporalStabilityProtocolTests,
)


class StrategyCorrelationClusterTemporalDateGridProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_case = StrategyCorrelationClusterTemporalStabilityProtocolTests(
            methodName="test_valid_registration_inherits_v7_and_targets_report21"
        )

    def _source(self):
        return self.source_case._registration()

    def _registration(self):
        return (
            build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                self._source()
            )
        )

    def test_valid_registration_inherits_v8_and_targets_report22(self):
        registration = self._registration()
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
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
        self.assertEqual(
            registration["target_extension_schema_version"],
            TARGET_EXTENSION_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_report_schema_version"],
            TARGET_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            registration["target_protocol_schema_version"],
            TARGET_PROTOCOL_SCHEMA_VERSION,
        )

    def test_gate_policy_hash_and_date_grid_rule_are_preregistered(self):
        registration = self._registration()
        gate_policy = registration["temporal_date_grid_gate_policy"]
        self.assertEqual(gate_policy["date_grid_rule"], DATE_GRID_RULE)
        self.assertEqual(gate_policy["required_price_rows"], 61)
        self.assertEqual(gate_policy["required_return_observations"], 60)
        self.assertEqual(
            registration["temporal_date_grid_gate_policy_hash"],
            gate_policy["policy_hash"],
        )
        self.assertTrue(registration["date_grid_policy_preregistered"])

    def test_report_policy_freezes_binding_and_pass_implication(self):
        policy = self._registration()[
            "cluster_temporal_date_grid_report_policy"
        ]
        self.assertEqual(policy["schema_version"], POLICY_SCHEMA_VERSION)
        self.assertEqual(
            policy["external_date_grid_binding_fields"],
            [
                "strategy_id",
                "variant_id",
                "lane",
                "expected_temporal_date_grid_gate_hash",
            ],
        )
        self.assertTrue(policy["date_grid_gate_exact_rebuild_required"])
        self.assertTrue(
            policy["report21_pass_implies_all_date_grid_gates_pass"]
        )
        self.assertTrue(policy["one_date_grid_gate_per_report_identity_required"])
        self.assertIn(
            "completed_price_datasets",
            policy["report22_payload_excluded_fields"],
        )
        self.assertIn("price_dates", policy["report22_payload_excluded_fields"])

    def test_consumer_and_writer_remain_unavailable(self):
        registration = self._registration()
        policy = registration["cluster_temporal_date_grid_report_policy"]
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                registration
            )
        )
        self.assertTrue(registration["date_grid_candidate_binding_available"])
        self.assertFalse(registration["report22_consumer_available"])
        self.assertFalse(registration["report22_writer_available"])
        self.assertFalse(policy["report22_consumer_available"])
        self.assertFalse(verification["report22_consumer_available"])
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_invalid_source_v8_blocks_registration(self):
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                {}
            )
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v8_invalid", verification["blockers"])
        self.assertFalse(verification["date_grid_policy_preregistered"])

    def test_resealed_source_v8_drift_is_rejected(self):
        source = deepcopy(self._source())
        source["schema21_consumer_available"] = False
        source = seal_strict_canonical_document(source, "registration_hash")
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                source
            )
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("source_registration_v8_invalid", verification["blockers"])

    def test_resealed_gate_policy_drift_is_rejected(self):
        registration = deepcopy(self._registration())
        gate_policy = registration["temporal_date_grid_gate_policy"]
        gate_policy["required_price_rows"] = 60
        gate_policy = seal_strict_canonical_document(
            gate_policy,
            "policy_hash",
        )
        registration["temporal_date_grid_gate_policy"] = gate_policy
        registration["temporal_date_grid_gate_policy_hash"] = gate_policy[
            "policy_hash"
        ]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "temporal_date_grid_gate_policy_invalid",
            verification["blockers"],
        )

    def test_resealed_report_policy_drift_is_rejected(self):
        registration = deepcopy(self._registration())
        policy = registration["cluster_temporal_date_grid_report_policy"]
        policy["report21_pass_implies_all_date_grid_gates_pass"] = False
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["cluster_temporal_date_grid_report_policy"] = policy
        registration["cluster_temporal_date_grid_report_policy_hash"] = policy[
            "policy_hash"
        ]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                registration
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "temporal_date_grid_protocol_contract_invalid",
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
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                alias
            )
        )
        authority_verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
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

    def test_builder_does_not_mutate_source_and_exports_no_activation(self):
        source = self._source()
        before = deepcopy(source)
        registration = (
            build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                source
            )
        )
        self.assertTrue(strict_json_contract_equal(source, before))
        self.assertEqual(
            registration["source_registration_hash"],
            source["registration_hash"],
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_protocol as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("build_report22", exports)
        self.assertNotIn("write_report22", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
