from __future__ import annotations

import copy
import importlib
import json
import re
import unittest

from exchange_terminal.services.strategy_correlation_cluster_stability_registry_projection import (
    PUBLIC_SUMMARY_SCHEMA_VERSION,
    STATIC_BUILD_FINGERPRINT,
    STATE_CANDIDATE_BOUND,
    STATE_CANDIDATE_EVIDENCE_BLOCKED,
    STATE_NOT_SUPPLIED,
    STATE_UNKNOWN,
    project_strategy_correlation_cluster_stability_registry_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_registry_test_module = importlib.import_module(
    "tests.test_strategy_correlation_cluster_stability_registry"
)


class StrategyCorrelationClusterStabilityRegistryProjectionTests(unittest.TestCase):
    def _fixture(self):
        case_type = getattr(
            _registry_test_module,
            "StrategyCorrelationClusterStabilityRegistryTests",
        )
        case = case_type(
            methodName="test_valid_binding_is_candidate_bound_but_not_formal"
        )
        protocol = case._protocol()
        asset = case._asset(protocol)
        binding = case._assessment(protocol=protocol, asset=asset)
        external = {
            "protocol_registration": protocol,
            "evidence_cutoff_date": binding["evidence_cutoff_date"],
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_registry_source_hash": asset["registry_source_hash"],
            "expected_protocol_registration_hash": asset[
                "protocol_registration_hash"
            ],
            "expected_cluster_stability_policy_hash": asset[
                "cluster_stability_policy_hash"
            ],
        }
        return case, protocol, asset, binding, external

    def test_missing_candidate_is_not_supplied_and_locked(self):
        summary = project_strategy_correlation_cluster_stability_registry_summary()
        self.assertEqual(summary["projection_state"], STATE_NOT_SUPPLIED)
        self.assertEqual(summary["source"]["status"], "NOT_SUPPLIED")
        self.assertEqual(summary["maturity"]["status"], "NO_EVIDENCE")
        self.assertFalse(summary["maturity"]["candidate_evidence_bound"])
        self._assert_locked(summary)

    def test_partial_or_malformed_candidate_is_unknown(self):
        _, _, asset, _, external = self._fixture()
        partial = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            None,
            **external,
        )
        malformed = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            "bound",
            **external,
        )
        self.assertEqual(partial["projection_state"], STATE_UNKNOWN)
        self.assertEqual(malformed["projection_state"], STATE_UNKNOWN)
        self._assert_locked(partial)
        self._assert_locked(malformed)

    def test_valid_candidate_binding_projects_candidate_only(self):
        _, _, asset, binding, external = self._fixture()
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(summary["projection_state"], STATE_CANDIDATE_BOUND)
        self.assertEqual(summary["source"]["status"], "VERIFIED_CANDIDATE")
        self.assertEqual(summary["maturity"]["status"], "CANDIDATE_BOUND")
        self.assertIs(summary["maturity"]["candidate_evidence_bound"], True)
        self.assertIs(summary["maturity"]["candidate_only"], True)
        self._assert_locked(summary)

    def test_valid_blocking_assessment_projects_evidence_blocked(self):
        case, protocol, asset, _, external = self._fixture()
        external["expected_registry_source_hash"] = "b" * 64
        blocked = case._assessment(
            protocol=protocol,
            asset=asset,
            expected_registry_source_hash="b" * 64,
        )
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            blocked,
            **external,
        )
        self.assertEqual(
            summary["projection_state"], STATE_CANDIDATE_EVIDENCE_BLOCKED
        )
        self.assertEqual(summary["source"]["status"], "VERIFIED_BLOCK")
        self.assertEqual(summary["maturity"]["status"], "BLOCKED")
        self.assertIs(summary["maturity"]["candidate_evidence_bound"], False)
        self._assert_locked(summary)

    def test_external_binding_mismatch_is_unknown_not_a_valid_block(self):
        _, _, asset, binding, external = self._fixture()
        external["expected_registry_source_hash"] = "b" * 64
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self._assert_locked(summary)

    def test_resealed_status_attack_is_unknown(self):
        case, protocol, asset, _, external = self._fixture()
        external["expected_registry_source_hash"] = "b" * 64
        blocked = case._assessment(
            protocol=protocol,
            asset=asset,
            expected_registry_source_hash="b" * 64,
        )
        attacked = copy.deepcopy(blocked)
        attacked["status"] = "CANDIDATE_BOUND"
        attacked["candidate_bound"] = True
        attacked["blockers"] = []
        attacked = seal_strict_canonical_document(attacked, "assessment_hash")
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            attacked,
            **external,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_resealed_authority_alias_is_unknown(self):
        _, _, asset, binding, external = self._fixture()
        attacked = copy.deepcopy(asset)
        attacked["formal_registry_bound"] = 0
        attacked = seal_strict_canonical_document(attacked, "registry_asset_hash")
        external["expected_registry_asset_hash"] = attacked["registry_asset_hash"]
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            attacked,
            binding,
            **external,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_protocol_drift_is_unknown(self):
        _, protocol, asset, binding, external = self._fixture()
        drifted = copy.deepcopy(protocol)
        drifted["status"] = "BOUND"
        external["protocol_registration"] = drifted
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_public_summary_redacts_private_evidence(self):
        _, _, asset, binding, external = self._fixture()
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        serialized = json.dumps(summary, sort_keys=True)
        private_values = (
            asset["registry_id"],
            asset["registry_source"],
            asset["registry_source_hash"],
            asset["registry_asset_hash"],
            asset["protocol_registration_hash"],
            asset["cluster_stability_policy_hash"],
            asset["effective_date"],
            asset["frozen_at"],
            binding["evidence_cutoff_date"],
        )
        for value in private_values:
            self.assertNotIn(value, serialized)
        self.assertIsNone(re.search(r"[a-f0-9]{64}", serialized, re.IGNORECASE))
        for key in self._keys(summary):
            lowered = key.lower()
            self.assertNotIn("hash", lowered)
            self.assertNotIn("registry_id", lowered)
            self.assertNotIn("registry_source", lowered)
            self.assertNotIn("effective_date", lowered)
            self.assertNotIn("frozen_at", lowered)
            self.assertNotIn("evidence_cutoff_date", lowered)
            self.assertNotIn("return", lowered)
            self.assertNotIn("correlation", lowered)
            self.assertNotIn("ranking", lowered)

    def test_public_contract_and_fingerprint_are_fixed(self):
        _, _, asset, binding, external = self._fixture()
        summary = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA_VERSION)
        self.assertEqual(summary["static_build_fingerprint"], STATIC_BUILD_FINGERPRINT)
        self.assertEqual(summary["source"]["protocol"], "protocol-v9")
        self.assertEqual(summary["source"]["report"], "report-20")
        self.assertEqual(summary["gap"]["formal_registry"], "MISSING")
        self.assertEqual(summary["gap"]["report_writer"], "MISSING")
        self.assertEqual(summary["gap"]["current_pointer"], "LOCKED")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self._assert_locked(summary)

    def _assert_locked(self, summary):
        permission = summary["permission"]
        for field in (
            "formal_registry_bound",
            "formal_registry_activation_allowed",
            "writer_implemented",
            "current_writer_activation_allowed",
            "current_admission_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertIs(permission[field], False)

    def _keys(self, value):
        keys = []
        if isinstance(value, dict):
            for key, nested in value.items():
                keys.append(key)
                keys.extend(self._keys(nested))
        elif isinstance(value, list):
            for nested in value:
                keys.extend(self._keys(nested))
        return keys


if __name__ == "__main__":
    unittest.main()
