from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_cluster_temporal_stability_protocol as protocol_fixtures
from tests import test_strategy_correlation_cluster_temporal_stability_report_consumer as report_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_migration_projection import (
    build_strategy_correlation_cluster_temporal_stability_migration_public_summary,
    verify_strategy_correlation_cluster_temporal_stability_migration_public_summary,
)


class StrategyCorrelationClusterTemporalStabilityMigrationProjectionTests(
    unittest.TestCase
):
    def setUp(self):
        self.report_case = report_fixtures.StrategyCorrelationClusterTemporalStabilityReportConsumerTests(
            methodName="test_valid_report21_passes_contract_and_decision"
        )
        self.report_case.setUp()
        self.protocol_case = protocol_fixtures.StrategyCorrelationClusterTemporalStabilityProtocolTests(
            methodName="test_valid_registration_inherits_v7_and_targets_report21"
        )

    def tearDown(self):
        self.report_case.tearDown()

    def _inputs(self, *, low_effective_sample=False):
        values = self.report_case._fixture(
            low_effective_sample=low_effective_sample
        )
        extension, report20, report19, registry, stability, temporal = values
        return {
            "registration": self.protocol_case._registration(),
            "report21_extension": extension,
            "expected_base_report_hash": report20["base_report_hash"],
            "expected_global_independence_extension_hash": report19[
                "extension_hash"
            ],
            "expected_cluster_stability_extension_hash": report20[
                "extension_hash"
            ],
            "expected_registry_bindings": [registry],
            "expected_stability_bindings": [stability],
            "expected_temporal_stability_bindings": [temporal],
        }

    def test_valid_registration_without_report_is_not_supplied_not_unknown(self):
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            self.protocol_case._registration()
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["protocol_target"], "PROTOCOL_V10")
        self.assertEqual(summary["source"]["report_target"], "REPORT21")
        self.assertEqual(summary["source"]["report21_contract_status"], "NOT_SUPPLIED")
        self.assertEqual(summary["gap"]["status"], "REPORT21_CONTRACT_NOT_SUPPLIED")
        self.assertEqual(
            summary["maturity"]["status"],
            "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED",
        )

    def test_valid_report21_pass_is_observed_but_not_formally_bound(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **inputs
        )
        self.assertEqual(summary["source"]["report21_contract_status"], "VERIFIED")
        self.assertEqual(summary["gap"]["temporal_decision"], "PASS")
        self.assertEqual(summary["gap"]["formal_binding_status"], "NOT_FORMALLY_BOUND")
        self.assertEqual(
            summary["maturity"]["status"], "REPORT21_CONSUMER_PASS_UNBOUND"
        )
        self.assertFalse(summary["permission"]["report_writer_activation_allowed"])

    def test_valid_report21_block_remains_observed_block(self):
        inputs = self._inputs(low_effective_sample=True)
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **inputs
        )
        self.assertEqual(summary["source"]["report21_contract_status"], "VERIFIED")
        self.assertEqual(summary["gap"]["temporal_decision"], "BLOCK")
        self.assertEqual(
            summary["gap"]["status"], "TEMPORAL_EVIDENCE_BLOCKED_AND_UNBOUND"
        )
        self.assertEqual(
            summary["maturity"]["status"], "REPORT21_CONSUMER_BLOCK_UNBOUND"
        )

    def test_invalid_registration_projects_unknown(self):
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            {}
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")
        self.assertIsNone(summary["maturity"]["writer_prerequisite_count"])
        self.assertEqual(summary["maturity"]["current"], "NOT_ACTIVATED")

    def test_invalid_supplied_report_projects_unknown_not_missing(self):
        inputs = self._inputs()
        inputs["report21_extension"] = {}
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **inputs
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["report21_contract_status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "REPORT21_CONTRACT_UNKNOWN")
        self.assertEqual(
            summary["maturity"]["status"],
            "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN",
        )

    def test_resealed_registration_policy_drift_projects_unknown(self):
        registration = deepcopy(self.protocol_case._registration())
        policy = registration["cluster_temporal_stability_policy"]
        policy["window_count"] = 2
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["cluster_temporal_stability_policy"] = policy
        registration["cluster_temporal_stability_policy_hash"] = policy["policy_hash"]
        registration = seal_strict_canonical_document(
            registration, "registration_hash"
        )
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            registration
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")

    def test_tampered_summary_cannot_claim_writer_or_current(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **inputs
        )
        summary["maturity"]["writer"] = "AVAILABLE"
        summary["gap"]["current_activation_status"] = "ACTIVATED"
        verification = verify_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            summary,
            **inputs,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_type_alias_and_authority_escalation_are_rejected(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **inputs
        )
        alias = deepcopy(summary)
        alias["maturity"]["writer_prerequisite_count"] = 13.0
        escalated = deepcopy(summary)
        escalated["permission"]["live_order_allowed"] = True
        alias_verification = verify_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            alias,
            **inputs,
        )
        escalated_verification = verify_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            escalated,
            **inputs,
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation", escalated_verification["blockers"]
        )

    def test_public_summary_redacts_hashes_identities_and_values(self):
        summary = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
            **self._inputs()
        )
        serialized = json.dumps(summary, sort_keys=True)
        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        for forbidden in (
            '"registration_hash":',
            '"extension_hash":',
            '"policy_hash":',
            '"strategy_id":',
            '"cluster_id":',
            '"symbol":',
            "correlation_matrix",
            "selection_cells",
            '"completed_price_datasets":',
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
