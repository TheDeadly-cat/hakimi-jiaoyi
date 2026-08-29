from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_cluster_stability_protocol as fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_protocol_projection import (
    build_strategy_correlation_cluster_stability_protocol_migration_public_summary,
    verify_strategy_correlation_cluster_stability_protocol_migration_public_summary,
)


class StrategyCorrelationClusterStabilityProtocolProjectionTests(unittest.TestCase):
    def _registration(self):
        fixture = fixtures.StrategyCorrelationClusterStabilityProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    def test_valid_registration_projects_preregistered_protocol(self):
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            self._registration()
        )

        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["protocol_target"], "PROTOCOL_V9")
        self.assertEqual(summary["source"]["report_target"], "REPORT20")
        self.assertEqual(summary["maturity"]["status"], "PROTOCOL_PREREGISTERED")
        self.assertEqual(summary["maturity"]["writer_prerequisite_count"], 12)

    def test_valid_projection_keeps_registry_writer_and_current_open(self):
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            self._registration()
        )

        self.assertEqual(summary["gap"]["formal_registry_status"], "NOT_SUPPLIED")
        self.assertEqual(summary["gap"]["schema20_writer_status"], "NOT_IMPLEMENTED")
        self.assertEqual(summary["maturity"]["current"], "NOT_ACTIVATED")
        self.assertFalse(summary["permission"]["formal_registry_activation_allowed"])
        self.assertFalse(summary["permission"]["paper_authorized"])

    def test_invalid_registration_projects_unknown(self):
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            {}
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")
        self.assertIsNone(summary["maturity"]["writer_prerequisite_count"])
        self.assertEqual(summary["maturity"]["current"], "NOT_ACTIVATED")

    def test_resealed_nested_policy_drift_projects_unknown(self):
        registration = deepcopy(self._registration())
        policy = registration["cluster_stability_policy"]
        policy["writer_available"] = True
        policy = seal_strict_canonical_document(policy, "policy_hash")
        registration["cluster_stability_policy"] = policy
        registration["cluster_stability_policy_hash"] = policy["policy_hash"]
        registration = seal_strict_canonical_document(
            registration,
            "registration_hash",
        )

        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            registration
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")

    def test_tampered_summary_cannot_claim_writer_or_current(self):
        registration = self._registration()
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            registration
        )
        summary["maturity"]["writer"] = "AVAILABLE"
        summary["gap"]["current_activation_status"] = "ACTIVATED"

        verification = verify_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            summary,
            registration=registration,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_type_alias_and_authority_escalation_are_rejected(self):
        registration = self._registration()
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            registration
        )
        alias = deepcopy(summary)
        alias["maturity"]["writer_prerequisite_count"] = 12.0
        escalated = deepcopy(summary)
        escalated["permission"]["live_order_allowed"] = True

        alias_verification = verify_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            alias,
            registration=registration,
        )
        escalated_verification = verify_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            escalated,
            registration=registration,
        )

        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", escalated_verification["blockers"])

    def test_public_summary_redacts_registration_hashes_and_evidence(self):
        summary = build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            self._registration()
        )
        serialized = json.dumps(summary, sort_keys=True)

        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        for forbidden in (
            '"registration_hash":',
            '"policy_hash":',
            '"source_registration":',
            "cluster_preregistration_hash",
            "correlation_matrix",
            "selection_cells",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
