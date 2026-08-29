from __future__ import annotations

import copy
import importlib
import unittest

from exchange_terminal.services.strategy_correlation_cluster_stability_formal_persistence_protocol import (
    ACTIVATION_PREREQUISITES,
    REQUIRED_PROVIDER_EVIDENCE_FIELDS,
    STATUS_PREREGISTERED,
    STATUS_READ_CONTRACT_BLOCKED,
    STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED,
    STATUS_UNKNOWN,
    assess_strategy_correlation_cluster_stability_formal_persistence_readiness,
    build_strategy_correlation_cluster_stability_formal_persistence_registration,
    verify_strategy_correlation_cluster_stability_formal_persistence_readiness,
    verify_strategy_correlation_cluster_stability_formal_persistence_registration,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_formal_registry_adapter import (
    InMemoryFormalRegistryReadAdapter,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_registry_projection import (
    project_strategy_correlation_cluster_stability_registry_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_adapter_test_module = importlib.import_module(
    "tests.test_strategy_correlation_cluster_stability_formal_registry_adapter"
)
_protocol_module = importlib.import_module(
    "exchange_terminal.services.strategy_correlation_cluster_stability_formal_persistence_protocol"
)


class StrategyCorrelationClusterStabilityFormalPersistenceProtocolTests(unittest.TestCase):
    READ_ADAPTER_MODULE_HASH = (
        "28104ef1b7d1cc1048cabc564bfea81f9538e7adc8f98901b6e4904f2390e1b4"
    )
    PREREGISTERED_AT = "2026-08-20T08:00:00Z"
    EVIDENCE_CUTOFF_DATE = "2026-08-21"

    def _fixture(self):
        case_type = getattr(
            _adapter_test_module,
            "StrategyCorrelationClusterStabilityFormalRegistryAdapterTests",
        )
        case = case_type(
            methodName="test_valid_unique_record_is_candidate_verified_but_not_formal"
        )
        protocol, asset, binding, external, record_inputs = case._fixture()
        record = case._record()
        adapter = InMemoryFormalRegistryReadAdapter([record])
        read_assessment = case._assessment(adapter)
        registration = (
            build_strategy_correlation_cluster_stability_formal_persistence_registration(
                read_adapter_module_hash=self.READ_ADAPTER_MODULE_HASH,
                preregistered_at=self.PREREGISTERED_AT,
                evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
            )
        )
        candidate_bindings = dict(external)
        candidate_bindings.pop("protocol_registration", None)
        readiness_inputs = {
            "expected_read_adapter_module_hash": self.READ_ADAPTER_MODULE_HASH,
            "preregistered_at": self.PREREGISTERED_AT,
            "evidence_cutoff_date": self.EVIDENCE_CUTOFF_DATE,
            "adapter": adapter,
            "expected_adapter_snapshot_hash": adapter.snapshot_hash,
            "protocol_registration": protocol,
            "registry_asset": asset,
            "binding_assessment": binding,
            **candidate_bindings,
            **record_inputs,
        }
        return (
            case,
            protocol,
            asset,
            binding,
            external,
            registration,
            read_assessment,
            readiness_inputs,
        )

    def _readiness(self, *, registration=None, read_assessment=None, **overrides):
        _, _, _, _, _, base_registration, base_read, inputs = self._fixture()
        values = {**inputs, **overrides}
        return assess_strategy_correlation_cluster_stability_formal_persistence_readiness(
            base_registration if registration is None else registration,
            base_read if read_assessment is None else read_assessment,
            **values,
        )

    def _verify_readiness(
        self,
        readiness,
        *,
        registration=None,
        read_assessment=None,
        **overrides,
    ):
        _, _, _, _, _, base_registration, base_read, inputs = self._fixture()
        values = {**inputs, **overrides}
        return verify_strategy_correlation_cluster_stability_formal_persistence_readiness(
            readiness,
            base_registration if registration is None else registration,
            base_read if read_assessment is None else read_assessment,
            **values,
        )

    def test_registration_is_preregistered_and_never_activated(self):
        _, _, _, _, _, registration, _, _ = self._fixture()
        verification = verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            registration,
            expected_read_adapter_module_hash=self.READ_ADAPTER_MODULE_HASH,
            preregistered_at=self.PREREGISTERED_AT,
            evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
        )
        self.assertEqual(registration["status"], STATUS_PREREGISTERED)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            registration["policy"]["activation_prerequisites"],
            list(ACTIVATION_PREREQUISITES),
        )
        self.assertEqual(
            registration["policy"]["activation_prerequisite_count"], 14
        )
        self._assert_locked(registration)
        self._assert_locked(registration["policy"])
        self._assert_locked(verification)

    def test_registration_binds_adapter_module_and_provider_fields(self):
        _, _, _, _, _, registration, _, _ = self._fixture()
        source = registration["policy"]["source_read_contract"]
        provider = registration["policy"]["provider_isolation_contract"]
        self.assertEqual(source["read_adapter_module_hash"], self.READ_ADAPTER_MODULE_HASH)
        self.assertEqual(provider["environment"], "ISOLATED_TEMPORARY_ONLY")
        self.assertEqual(
            provider["required_evidence_fields"],
            list(REQUIRED_PROVIDER_EVIDENCE_FIELDS),
        )
        self.assertIs(provider["receipt_producer_implemented"], False)

    def test_adapter_module_hash_drift_blocks_registration(self):
        _, _, _, _, _, registration, _, _ = self._fixture()
        verification = verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            registration,
            expected_read_adapter_module_hash="e" * 64,
            preregistered_at=self.PREREGISTERED_AT,
            evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self._assert_locked(verification)

    def test_preregistration_at_cutoff_is_blocked(self):
        registration = build_strategy_correlation_cluster_stability_formal_persistence_registration(
            read_adapter_module_hash=self.READ_ADAPTER_MODULE_HASH,
            preregistered_at="2026-08-21T00:00:00Z",
            evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
        )
        verification = verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            registration,
            expected_read_adapter_module_hash=self.READ_ADAPTER_MODULE_HASH,
            preregistered_at="2026-08-21T00:00:00Z",
            evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_registration_authority_attack_is_blocked(self):
        _, _, _, _, _, registration, _, _ = self._fixture()
        attacked = copy.deepcopy(registration)
        attacked["formal_persistence_activation_allowed"] = True
        attacked = seal_strict_canonical_document(attacked, "registration_hash")
        verification = verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            attacked,
            expected_read_adapter_module_hash=self.READ_ADAPTER_MODULE_HASH,
            preregistered_at=self.PREREGISTERED_AT,
            evidence_cutoff_date=self.EVIDENCE_CUTOFF_DATE,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self._assert_locked(verification)

    def test_complete_read_contract_is_still_blocked_for_persistence(self):
        readiness = self._readiness()
        verification = self._verify_readiness(readiness)
        self.assertEqual(
            readiness["status"], STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED
        )
        self.assertEqual(readiness["decision"], "BLOCK")
        self.assertIs(readiness["facts"]["isolated_read_contract_verified"], True)
        self.assertIs(readiness["facts"]["unique_candidate_record_verified"], True)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self._assert_locked(readiness)
        self._assert_locked(verification)

    def test_missing_read_record_blocks_read_contract(self):
        case, _, _, _, _, registration, _, inputs = self._fixture()
        adapter = InMemoryFormalRegistryReadAdapter([])
        missing = case._assessment(adapter)
        readiness = self._readiness(
            registration=registration,
            read_assessment=missing,
            adapter=adapter,
            expected_adapter_snapshot_hash=adapter.snapshot_hash,
        )
        self.assertEqual(readiness["status"], STATUS_READ_CONTRACT_BLOCKED)
        self.assertIs(readiness["facts"]["isolated_read_contract_verified"], False)
        self._assert_locked(readiness)

    def test_duplicate_read_record_blocks_read_contract(self):
        case, _, _, _, _, registration, _, _ = self._fixture()
        record = case._record()
        adapter = InMemoryFormalRegistryReadAdapter([record, record])
        duplicate = case._assessment(adapter)
        readiness = self._readiness(
            registration=registration,
            read_assessment=duplicate,
            adapter=adapter,
            expected_adapter_snapshot_hash=adapter.snapshot_hash,
        )
        self.assertEqual(readiness["status"], STATUS_READ_CONTRACT_BLOCKED)
        self._assert_locked(readiness)

    def test_drift_assessment_cannot_satisfy_read_contract(self):
        case, _, _, _, _, registration, _, _ = self._fixture()
        adapter = InMemoryFormalRegistryReadAdapter([case._record()])
        drift = case._assessment(
            adapter,
            expected_adapter_snapshot_hash="e" * 64,
        )
        readiness = self._readiness(
            registration=registration,
            read_assessment=drift,
            adapter=adapter,
            expected_adapter_snapshot_hash="e" * 64,
        )
        self.assertEqual(readiness["status"], STATUS_READ_CONTRACT_BLOCKED)
        self._assert_locked(readiness)

    def test_fake_provider_evidence_is_rejected_not_promoted(self):
        readiness = self._readiness(
            provider_evidence={"status": "PASS", "formal_persistence_verified": True}
        )
        self.assertEqual(
            readiness["status"], STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED
        )
        self.assertEqual(readiness["decision"], "BLOCK")
        self.assertIn("UNSUPPORTED_PROVIDER_EVIDENCE", readiness["blockers"])
        self.assertIs(readiness["facts"]["provider_evidence_supplied"], True)
        self._assert_locked(readiness)

    def test_fake_durable_reopen_evidence_is_rejected(self):
        readiness = self._readiness(
            durable_reopen_evidence="truthy-reopen-receipt"
        )
        self.assertIn(
            "UNSUPPORTED_DURABLE_REOPEN_EVIDENCE", readiness["blockers"]
        )
        self.assertEqual(readiness["decision"], "BLOCK")
        self._assert_locked(readiness)

    def test_resealed_readiness_cannot_claim_activation(self):
        readiness = self._readiness()
        attacked = copy.deepcopy(readiness)
        attacked["decision"] = "ACTIVATE"
        attacked["formal_persistence_verified"] = True
        attacked = seal_strict_canonical_document(attacked, "assessment_hash")
        verification = self._verify_readiness(attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["decision"], "BLOCK")
        self._assert_locked(verification)

    def test_invalid_registration_makes_readiness_unknown(self):
        _, _, _, _, _, registration, read_assessment, _ = self._fixture()
        attacked = copy.deepcopy(registration)
        attacked["status"] = "ACTIVATED"
        attacked = seal_strict_canonical_document(attacked, "registration_hash")
        readiness = self._readiness(
            registration=attacked,
            read_assessment=read_assessment,
        )
        self.assertEqual(readiness["status"], STATUS_UNKNOWN)
        self.assertEqual(readiness["decision"], "BLOCK")
        self._assert_locked(readiness)

    def test_public_projection_and_exports_do_not_gain_provider_authority(self):
        _, _, asset, binding, external, _, _, _ = self._fixture()
        public = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(public["projection_state"], "CANDIDATE_BOUND")
        self.assertEqual(public["gap"]["formal_registry"], "MISSING")
        self.assertIs(public["permission"]["formal_registry_bound"], False)
        exports = set(_protocol_module.__all__)
        self.assertNotIn("build_formal_registry_provider_receipt", exports)
        self.assertNotIn("persist_formal_registry", exports)
        self.assertNotIn("activate_report20_writer", exports)
        self.assertNotIn("switch_current_pointer", exports)

    def _assert_locked(self, value):
        for field in (
            "provider_implemented",
            "formal_persistence_verified",
            "formal_persistence_activation_allowed",
            "formal_registry_bound",
            "formal_registry_activation_allowed",
            "writer_implemented",
            "current_writer_activation_allowed",
            "current_admission_allowed",
        ):
            self.assertIs(value[field], False)
        self.assertIs(value["permissions"]["paper_authorized"], False)
        self.assertIs(value["permissions"]["live_order_allowed"], False)


if __name__ == "__main__":
    unittest.main()
