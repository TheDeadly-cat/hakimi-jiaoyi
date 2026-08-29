from copy import deepcopy
import unittest

from tests import test_strategy_correlation_cluster_stability_protocol as protocol_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_registry import (
    assess_strategy_correlation_cluster_stability_registry_binding,
    build_strategy_correlation_cluster_stability_registry_asset,
    verify_strategy_correlation_cluster_stability_registry_asset,
    verify_strategy_correlation_cluster_stability_registry_binding,
)


class StrategyCorrelationClusterStabilityRegistryTests(unittest.TestCase):
    REGISTRY_SOURCE_HASH = "a" * 64
    EFFECTIVE_DATE = "2026-08-19"
    FROZEN_AT = "2026-08-20T00:00:00Z"
    EVIDENCE_CUTOFF_DATE = "2026-08-21"

    def _protocol(self):
        fixture = protocol_fixtures.StrategyCorrelationClusterStabilityProtocolTests(
            methodName="runTest"
        )
        return fixture._registration()

    def _asset(self, protocol=None, **overrides):
        protocol = self._protocol() if protocol is None else protocol
        arguments = {
            "registry_id": "cluster-stability-registry-candidate-1",
            "registry_source": "external-governance-registry-snapshot",
            "registry_source_version": "2026-08-19",
            "registry_source_hash": self.REGISTRY_SOURCE_HASH,
            "effective_date": self.EFFECTIVE_DATE,
            "frozen_at": self.FROZEN_AT,
        }
        arguments.update(overrides)
        return build_strategy_correlation_cluster_stability_registry_asset(
            protocol,
            **arguments,
        )

    def _assessment(self, protocol=None, asset=None, **overrides):
        protocol = self._protocol() if protocol is None else protocol
        asset = self._asset(protocol) if asset is None else asset
        arguments = {
            "evidence_cutoff_date": self.EVIDENCE_CUTOFF_DATE,
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_registry_source_hash": self.REGISTRY_SOURCE_HASH,
            "expected_protocol_registration_hash": protocol["registration_hash"],
            "expected_cluster_stability_policy_hash": protocol[
                "cluster_stability_policy_hash"
            ],
        }
        arguments.update(overrides)
        return assess_strategy_correlation_cluster_stability_registry_binding(
            asset,
            protocol,
            **arguments,
        )

    def _verify_binding(self, protocol, asset, assessment, **overrides):
        arguments = {
            "evidence_cutoff_date": self.EVIDENCE_CUTOFF_DATE,
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_registry_source_hash": self.REGISTRY_SOURCE_HASH,
            "expected_protocol_registration_hash": protocol["registration_hash"],
            "expected_cluster_stability_policy_hash": protocol[
                "cluster_stability_policy_hash"
            ],
        }
        arguments.update(overrides)
        return verify_strategy_correlation_cluster_stability_registry_binding(
            assessment,
            registry_asset=asset,
            protocol_registration=protocol,
            **arguments,
        )

    def test_valid_asset_is_frozen_candidate_only(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        verification = verify_strategy_correlation_cluster_stability_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(asset["status"], "FROZEN_CANDIDATE")
        self.assertTrue(asset["candidate_only"])
        self.assertFalse(asset["formal_registry_bound"])
        self.assertFalse(asset["writer_implemented"])

    def test_valid_binding_is_candidate_bound_but_not_formal(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(protocol, asset)
        verification = self._verify_binding(protocol, asset, assessment)

        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["candidate_bound"])
        self.assertEqual(assessment["status"], "CANDIDATE_BOUND")
        self.assertFalse(assessment["formal_registry_bound"])
        self.assertFalse(assessment["permissions"]["paper_authorized"])

    def test_protocol_registration_drift_blocks_asset(self):
        protocol = deepcopy(self._protocol())
        protocol["schema20_consumer_available"] = False
        protocol = seal_strict_canonical_document(protocol, "registration_hash")
        asset = self._asset(protocol)

        verification = verify_strategy_correlation_cluster_stability_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("protocol_registration_v7_invalid", verification["blockers"])

    def test_external_asset_hash_mismatch_blocks_candidate(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(
            protocol,
            asset,
            expected_registry_asset_hash="b" * 64,
        )

        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["facts"]["registry_asset_hash_bound"])

    def test_external_source_hash_mismatch_blocks_candidate(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(
            protocol,
            asset,
            expected_registry_source_hash="c" * 64,
        )

        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["facts"]["registry_source_hash_bound"])

    def test_external_policy_hash_mismatch_blocks_candidate(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(
            protocol,
            asset,
            expected_cluster_stability_policy_hash="d" * 64,
        )

        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(
            assessment["facts"]["cluster_stability_policy_hash_bound"]
        )

    def test_post_evidence_effective_or_frozen_date_blocks_candidate(self):
        protocol = self._protocol()
        asset = self._asset(
            protocol,
            effective_date=self.EVIDENCE_CUTOFF_DATE,
            frozen_at="2026-08-21T00:00:00Z",
        )
        assessment = self._assessment(protocol, asset)

        self.assertEqual(assessment["status"], "BLOCK")
        self.assertFalse(assessment["facts"]["effective_before_evidence"])
        self.assertFalse(assessment["facts"]["frozen_before_evidence"])

    def test_native_alias_in_asset_is_rejected_after_reseal(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        asset["candidate_only"] = 1
        asset = seal_strict_canonical_document(asset, "registry_asset_hash")

        verification = verify_strategy_correlation_cluster_stability_registry_asset(
            asset,
            protocol_registration=protocol,
        )

        self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_binding_facts_cannot_override_rebuild(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(protocol, asset)
        assessment["facts"]["formal_registry_unbound_asserted"] = False
        assessment["status"] = "BLOCK"
        assessment["candidate_bound"] = False
        assessment["blockers"] = ["formal_registry_unbound_asserted"]
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")

        verification = self._verify_binding(protocol, asset, assessment)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("registry_binding_contract_invalid", verification["blockers"])

    def test_authority_escalation_and_writer_exports_remain_absent(self):
        protocol = self._protocol()
        asset = self._asset(protocol)
        assessment = self._assessment(protocol, asset)
        assessment["permissions"]["live_order_allowed"] = True
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")

        verification = self._verify_binding(protocol, asset, assessment)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])
        self.assertFalse(verification["formal_registry_bound"])
        self.assertFalse(verification["writer_implemented"])


if __name__ == "__main__":
    unittest.main()
