from copy import deepcopy
import unittest

from tests import test_strategy_correlation_global_independence_protocol as protocol_fixtures

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_global_independence_registry import (
    assess_strategy_correlation_global_independence_registry_binding,
    build_strategy_correlation_global_independence_registry_asset,
    verify_strategy_correlation_global_independence_registry_asset,
    verify_strategy_correlation_global_independence_registry_binding,
)


class StrategyCorrelationGlobalIndependenceRegistryTests(unittest.TestCase):
    REGISTRY_SOURCE_HASH = "d" * 64
    EVIDENCE_CUTOFF_DATE = "2026-08-21"

    @staticmethod
    def _seal(document, field):
        document.pop(field, None)
        document[field] = strict_canonical_hash(document)
        return document

    def _protocol(self):
        fixture = protocol_fixtures.StrategyCorrelationGlobalIndependenceProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    def _asset(self, protocol=None):
        if protocol is None:
            protocol = self._protocol()
        return build_strategy_correlation_global_independence_registry_asset(
            protocol,
            registry_id="global-independence-registry-candidate-1",
            registry_source="external-governance-registry-snapshot",
            registry_source_version="2026-08-20",
            registry_source_hash=self.REGISTRY_SOURCE_HASH,
            effective_date="2026-08-19",
            frozen_at="2026-08-20T00:00:00Z",
        )

    def _assessment(self, protocol=None, asset=None, **overrides):
        if protocol is None:
            protocol = self._protocol()
        if asset is None:
            asset = self._asset(protocol)
        arguments = {
            "evidence_cutoff_date": self.EVIDENCE_CUTOFF_DATE,
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_registry_source_hash": self.REGISTRY_SOURCE_HASH,
            "expected_protocol_registration_hash": protocol["registration_hash"],
            "expected_global_independence_policy_hash": protocol[
                "global_independence_policy_hash"
            ],
        }
        arguments.update(overrides)
        return assess_strategy_correlation_global_independence_registry_binding(
            asset,
            protocol,
            **arguments,
        )

    def test_valid_candidate_is_bound_but_never_formal(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(protocol, asset)

        asset_verification = (
            verify_strategy_correlation_global_independence_registry_asset(
                asset,
                protocol_registration=protocol,
            )
        )
        binding_verification = (
            verify_strategy_correlation_global_independence_registry_binding(
                assessment,
                registry_asset=asset,
                protocol_registration=protocol,
                evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
                expected_registry_asset_hash=asset["registry_asset_hash"],
                expected_registry_source_hash=self.REGISTRY_SOURCE_HASH,
                expected_protocol_registration_hash=protocol["registration_hash"],
                expected_global_independence_policy_hash=protocol[
                    "global_independence_policy_hash"
                ],
            )
        )

        self.assertEqual(asset_verification["status"], "PASS")
        self.assertEqual(assessment["status"], "CANDIDATE_BOUND")
        self.assertTrue(assessment["candidate_bound"])
        self.assertEqual(binding_verification["status"], "PASS")
        self.assertTrue(binding_verification["candidate_bound"])
        self.assertFalse(assessment["formal_registry_bound"])
        self.assertFalse(binding_verification["formal_registry_bound"])
        self.assertFalse(assessment["permissions"]["paper_authorized"])
        self.assertFalse(assessment["permissions"]["live_order_allowed"])

    def test_invalid_protocol_cannot_build_candidate(self):
        with self.assertRaisesRegex(ValueError, "protocol_v8_registration_invalid"):
            self._asset(protocol={})

    def test_resealed_protocol_hash_drift_in_asset_is_rejected(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        asset["protocol_registration_hash"] = "e" * 64
        self._seal(asset, "registry_asset_hash")

        verification = verify_strategy_correlation_global_independence_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("registry_asset_contract_invalid", verification["blockers"])

    def test_resealed_report_schema_float_alias_is_rejected(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        asset["target_report_schema_version"] = 19.0
        self._seal(asset, "registry_asset_hash")

        verification = verify_strategy_correlation_global_independence_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "BLOCK")

    def test_nested_authority_escalation_is_rejected(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        asset["permissions"]["paper_authorized"] = True
        self._seal(asset, "registry_asset_hash")

        verification = verify_strategy_correlation_global_independence_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])

    def test_external_asset_and_source_hashes_cannot_self_authenticate(self):
        protocol = self._protocol()
        asset = self._asset(protocol)

        asset_mismatch = self._assessment(
            protocol,
            asset,
            expected_registry_asset_hash="e" * 64,
        )
        source_mismatch = self._assessment(
            protocol,
            asset,
            expected_registry_source_hash="e" * 64,
        )

        self.assertEqual(asset_mismatch["status"], "BLOCK")
        self.assertIn("registry_asset_hash_bound", asset_mismatch["blockers"])
        self.assertEqual(source_mismatch["status"], "BLOCK")
        self.assertIn("registry_source_hash_bound", source_mismatch["blockers"])

    def test_external_protocol_and_policy_hashes_cannot_self_authenticate(self):
        protocol = self._protocol()
        asset = self._asset(protocol)

        protocol_mismatch = self._assessment(
            protocol,
            asset,
            expected_protocol_registration_hash="e" * 64,
        )
        policy_mismatch = self._assessment(
            protocol,
            asset,
            expected_global_independence_policy_hash="e" * 64,
        )

        self.assertEqual(protocol_mismatch["status"], "BLOCK")
        self.assertIn(
            "protocol_registration_hash_bound", protocol_mismatch["blockers"]
        )
        self.assertEqual(policy_mismatch["status"], "BLOCK")
        self.assertIn(
            "global_independence_policy_hash_bound", policy_mismatch["blockers"]
        )

    def test_effective_and_frozen_dates_must_precede_evidence(self):
        protocol = self._protocol()
        asset = self._asset(protocol)

        assessment = self._assessment(
            protocol,
            asset,
            evidence_cutoff_date="2026-08-20",
        )

        self.assertEqual(assessment["status"], "BLOCK")
        self.assertIn("frozen_before_evidence", assessment["blockers"])

    def test_resealed_candidate_cannot_claim_formal_binding(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(protocol, asset)
        assessment["formal_registry_bound"] = True
        self._seal(assessment, "assessment_hash")

        verification = (
            verify_strategy_correlation_global_independence_registry_binding(
                assessment,
                registry_asset=asset,
                protocol_registration=protocol,
                evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
                expected_registry_asset_hash=asset["registry_asset_hash"],
                expected_registry_source_hash=self.REGISTRY_SOURCE_HASH,
                expected_protocol_registration_hash=protocol["registration_hash"],
                expected_global_independence_policy_hash=protocol[
                    "global_independence_policy_hash"
                ],
            )
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["formal_registry_bound"])
        self.assertIn("registry_binding_contract_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
