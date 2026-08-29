from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_global_independence_registry as fixtures

from exchange_terminal.services.strategy_correlation_global_independence_registry_projection import (
    build_strategy_correlation_global_independence_registry_migration_public_summary,
    verify_strategy_correlation_global_independence_registry_migration_public_summary,
)


class StrategyCorrelationGlobalIndependenceRegistryProjectionTests(unittest.TestCase):
    def _fixture(self):
        fixture = fixtures.StrategyCorrelationGlobalIndependenceRegistryTests(
            methodName="runTest"
        )
        protocol = fixture._protocol()
        asset = fixture._asset(protocol)
        binding = fixture._assessment(protocol, asset)
        arguments = {
            "registry_asset": asset,
            "registry_binding": binding,
            "evidence_cutoff_date": fixture.EVIDENCE_CUTOFF_DATE,
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_registry_source_hash": fixture.REGISTRY_SOURCE_HASH,
            "expected_protocol_registration_hash": protocol["registration_hash"],
            "expected_global_independence_policy_hash": protocol[
                "global_independence_policy_hash"
            ],
        }
        return fixture, protocol, asset, binding, arguments

    def test_no_candidate_is_explicitly_not_supplied(self):
        _, protocol, _, _, _ = self._fixture()

        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol
        )

        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["registry_candidate_status"], "NOT_SUPPLIED")
        self.assertEqual(summary["maturity"]["status"], "PROTOCOL_PREREGISTERED")
        self.assertEqual(summary["maturity"]["writer_prerequisite_count"], 7)

    def test_valid_candidate_is_visible_but_not_formal(self):
        _, protocol, _, _, arguments = self._fixture()

        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            **arguments,
        )

        self.assertEqual(
            summary["gap"]["registry_candidate_status"], "CANDIDATE_BOUND"
        )
        self.assertEqual(summary["maturity"]["status"], "REGISTRY_CANDIDATE_BOUND")
        self.assertEqual(summary["maturity"]["formal_registry"], "PENDING")
        self.assertEqual(summary["gap"]["formal_registry_status"], "NOT_SUPPLIED")
        self.assertFalse(summary["permission"]["formal_registry_activation_allowed"])

    def test_partial_candidate_inputs_project_binding_block(self):
        _, protocol, asset, _, _ = self._fixture()

        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            registry_asset=asset,
        )

        self.assertEqual(summary["gap"]["registry_candidate_status"], "BLOCK")
        self.assertEqual(summary["maturity"]["status"], "CANDIDATE_EVIDENCE_BLOCKED")

    def test_external_hash_mismatch_projects_binding_block(self):
        fixture, protocol, asset, _, arguments = self._fixture()
        blocked_binding = fixture._assessment(
            protocol,
            asset,
            expected_registry_asset_hash="e" * 64,
        )
        arguments["registry_binding"] = blocked_binding
        arguments["expected_registry_asset_hash"] = "e" * 64

        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            **arguments,
        )

        self.assertEqual(summary["gap"]["registry_candidate_status"], "BLOCK")

    def test_invalid_protocol_projects_unknown(self):
        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            {}
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")
        self.assertIsNone(summary["maturity"]["writer_prerequisite_count"])

    def test_tampered_summary_cannot_claim_formal_registry(self):
        _, protocol, _, _, arguments = self._fixture()
        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            **arguments,
        )
        summary["gap"]["formal_registry_status"] = "BOUND"

        verification = verify_strategy_correlation_global_independence_registry_migration_public_summary(
            summary,
            source_protocol_registration=protocol,
            **arguments,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["formal_registry_bound"])

    def test_type_alias_and_authority_escalation_are_rejected(self):
        _, protocol, _, _, arguments = self._fixture()
        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            **arguments,
        )
        alias = deepcopy(summary)
        alias["maturity"]["writer_prerequisite_count"] = 7.0
        escalated = deepcopy(summary)
        escalated["permission"]["paper_authorized"] = True

        alias_verification = verify_strategy_correlation_global_independence_registry_migration_public_summary(
            alias,
            source_protocol_registration=protocol,
            **arguments,
        )
        escalated_verification = verify_strategy_correlation_global_independence_registry_migration_public_summary(
            escalated,
            source_protocol_registration=protocol,
            **arguments,
        )

        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", escalated_verification["blockers"])

    def test_public_summary_contains_no_hash_or_identity_values(self):
        _, protocol, _, _, arguments = self._fixture()
        summary = build_strategy_correlation_global_independence_registry_migration_public_summary(
            protocol,
            **arguments,
        )
        serialized = json.dumps(summary, sort_keys=True)

        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        self.assertNotIn("global-independence-registry-candidate-1", serialized)
        self.assertNotIn("external-governance-registry-snapshot", serialized)


if __name__ == "__main__":
    unittest.main()
