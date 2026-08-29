from __future__ import annotations

import copy
import importlib
import json
import re
import unittest

from exchange_terminal.services.strategy_correlation_cluster_stability_formal_persistence_projection import (
    PUBLIC_SUMMARY_SCHEMA_VERSION,
    STATIC_BUILD_FINGERPRINT,
    STATE_NOT_SUPPLIED,
    STATE_READ_CONTRACT_BLOCKED,
    STATE_READ_CONTRACT_COMPLETE_BLOCKED,
    STATE_UNKNOWN,
    project_strategy_correlation_cluster_stability_formal_persistence_summary,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_formal_registry_adapter import (
    InMemoryFormalRegistryReadAdapter,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_protocol_test_module = importlib.import_module(
    "tests.test_strategy_correlation_cluster_stability_formal_persistence_protocol"
)


class StrategyCorrelationClusterStabilityFormalPersistenceProjectionTests(unittest.TestCase):
    def _fixture(self):
        case_type = getattr(
            _protocol_test_module,
            "StrategyCorrelationClusterStabilityFormalPersistenceProtocolTests",
        )
        case = case_type(
            methodName="test_complete_read_contract_is_still_blocked_for_persistence"
        )
        (
            adapter_case,
            _,
            _,
            _,
            _,
            registration,
            read_assessment,
            inputs,
        ) = case._fixture()
        readiness = case._readiness()
        projection_inputs = {**inputs, "read_assessment": read_assessment}
        return case, adapter_case, registration, readiness, projection_inputs

    def test_not_supplied_is_locked(self):
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary()
        self.assertEqual(summary["projection_state"], STATE_NOT_SUPPLIED)
        self.assertEqual(summary["source"]["status"], "NOT_SUPPLIED")
        self.assertEqual(summary["maturity"]["persistence_decision"], "BLOCK")
        self._assert_locked(summary)

    def test_partial_or_malformed_input_is_unknown(self):
        _, _, registration, readiness, inputs = self._fixture()
        partial = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            None,
            **inputs,
        )
        malformed = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            "blocked",
            **inputs,
        )
        self.assertEqual(partial["projection_state"], STATE_UNKNOWN)
        self.assertEqual(malformed["projection_state"], STATE_UNKNOWN)
        self._assert_locked(partial)
        self._assert_locked(malformed)

    def test_complete_read_contract_projects_blocked_persistence(self):
        _, _, registration, readiness, inputs = self._fixture()
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **inputs,
        )
        self.assertEqual(
            summary["projection_state"], STATE_READ_CONTRACT_COMPLETE_BLOCKED
        )
        self.assertEqual(summary["source"]["status"], "PREREGISTRATION_VERIFIED")
        self.assertEqual(summary["source"]["read_contract"], "COMPLETE")
        self.assertEqual(summary["maturity"]["status"], "READ_CONTRACT_ONLY")
        self.assertIs(summary["maturity"]["read_contract_complete"], True)
        self._assert_locked(summary)

    def test_blocked_read_contract_remains_distinct(self):
        case, adapter_case, registration, _, inputs = self._fixture()
        adapter = InMemoryFormalRegistryReadAdapter([])
        read_assessment = adapter_case._assessment(adapter)
        readiness = case._readiness(
            registration=registration,
            read_assessment=read_assessment,
            adapter=adapter,
            expected_adapter_snapshot_hash=adapter.snapshot_hash,
        )
        values = {
            **inputs,
            "adapter": adapter,
            "expected_adapter_snapshot_hash": adapter.snapshot_hash,
            "read_assessment": read_assessment,
        }
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **values,
        )
        self.assertEqual(summary["projection_state"], STATE_READ_CONTRACT_BLOCKED)
        self.assertEqual(summary["source"]["read_contract"], "BLOCKED")
        self.assertEqual(summary["maturity"]["status"], "BLOCKED")
        self.assertIs(summary["maturity"]["read_contract_complete"], False)
        self._assert_locked(summary)

    def test_external_registration_hash_drift_is_unknown(self):
        _, _, registration, readiness, inputs = self._fixture()
        inputs["expected_read_adapter_module_hash"] = "e" * 64
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **inputs,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_resealed_activation_claim_is_unknown(self):
        _, _, registration, readiness, inputs = self._fixture()
        attacked = copy.deepcopy(readiness)
        attacked["decision"] = "ACTIVATE"
        attacked["formal_persistence_verified"] = True
        attacked = seal_strict_canonical_document(attacked, "assessment_hash")
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            attacked,
            **inputs,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_resealed_registration_authority_alias_is_unknown(self):
        _, _, registration, readiness, inputs = self._fixture()
        attacked = copy.deepcopy(registration)
        attacked["formal_registry_bound"] = 0
        attacked = seal_strict_canonical_document(attacked, "registration_hash")
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            attacked,
            readiness,
            **inputs,
        )
        self.assertEqual(summary["projection_state"], STATE_UNKNOWN)
        self._assert_locked(summary)

    def test_unsupported_provider_evidence_stays_publicly_blocked(self):
        case, _, registration, _, inputs = self._fixture()
        fake = {"status": "PASS", "formal_persistence_verified": True}
        readiness = case._readiness(provider_evidence=fake)
        inputs["provider_evidence"] = fake
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **inputs,
        )
        self.assertEqual(
            summary["projection_state"], STATE_READ_CONTRACT_COMPLETE_BLOCKED
        )
        self.assertEqual(summary["gap"]["provider"], "MISSING")
        self.assertEqual(summary["maturity"]["persistence_decision"], "BLOCK")
        self._assert_locked(summary)

    def test_public_summary_redacts_internal_evidence(self):
        _, _, registration, readiness, inputs = self._fixture()
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **inputs,
        )
        serialized = json.dumps(summary, sort_keys=True)
        private_values = (
            registration["registration_hash"],
            registration["preregistered_at"],
            registration["evidence_cutoff_date"],
            inputs["expected_read_adapter_module_hash"],
            inputs["expected_adapter_snapshot_hash"],
            inputs["formal_registry_source"],
            inputs["formal_registry_source_hash"],
            inputs["registry_snapshot_hash"],
        )
        for value in private_values:
            self.assertNotIn(value, serialized)
        self.assertIsNone(re.search(r"[a-f0-9]{64}", serialized, re.IGNORECASE))
        for key in self._keys(summary):
            lowered = key.lower()
            self.assertNotIn("hash", lowered)
            self.assertNotIn("registry_id", lowered)
            self.assertNotIn("source_version", lowered)
            self.assertNotIn("preregistered_at", lowered)
            self.assertNotIn("evidence_cutoff", lowered)
            self.assertNotIn("return", lowered)
            self.assertNotIn("correlation", lowered)
            self.assertNotIn("ranking", lowered)

    def test_public_contract_fingerprint_and_gap_are_fixed(self):
        _, _, registration, readiness, inputs = self._fixture()
        summary = project_strategy_correlation_cluster_stability_formal_persistence_summary(
            registration,
            readiness,
            **inputs,
        )
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA_VERSION)
        self.assertEqual(summary["static_build_fingerprint"], STATIC_BUILD_FINGERPRINT)
        self.assertEqual(summary["maturity"]["activation_prerequisite_count"], 14)
        for field in (
            "provider",
            "durable_write_receipt",
            "durable_reopen_receipt",
            "session_separation",
            "formal_persistence_asset",
            "report_writer",
        ):
            self.assertEqual(summary["gap"][field], "MISSING")
        self.assertEqual(summary["gap"]["current_pointer"], "LOCKED")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self._assert_locked(summary)

    def _assert_locked(self, summary):
        permission = summary["permission"]
        for field in (
            "provider_implemented",
            "formal_persistence_verified",
            "formal_persistence_activation_allowed",
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
