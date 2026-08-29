from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import random
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1 as harness,
)
from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as storage_preregistration,
)
from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as evidence,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1 as binding,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_observer_identity_admission_v1 as observer_admission,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_identity_source_adapter_preregistration_v1 as identity_source,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class _Driver:
    def __init__(self) -> None:
        self.calls = 0

    def execute_scenario(self, command):
        self.calls += 1
        return harness.build_witness_ownership_snapshot_storage_harness_scenario_result_v1(
            command,
            outcome=harness.OUTCOME_PASS,
            transcript_hash=_hash(f"transcript-{self.calls}"),
            observed_artifact_hash=_hash(f"artifact-{self.calls}"),
            runtime_mutations_outside_isolated_domain_claimed=False,
            paper_or_live_operation_claimed=False,
            automatic_retry_or_reissue_claimed=False,
        )


class WitnessOwnershipHarnessEvidenceLineageBindingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity_key = Ed25519PrivateKey.generate()
        self.revocation_key = Ed25519PrivateKey.generate()
        identity_spki = _spki(self.identity_key)
        revocation_spki = _spki(self.revocation_key)
        self.identity_kwargs = {
            "target_stream_id": "witness-provider-key-revocations",
            "provider_preregistration_hash": _hash("provider-preregistration"),
            "active_key_state_hash": _hash("active-key-state"),
            "revocation_quorum_evidence_hash": _hash("revocation-quorum"),
            "identity_source_adapter_id": "external-identity-source-adapter-01",
            "identity_source_adapter_static_fingerprint": "synthetic-identity-source-v1",
            "identity_source_adapter_implementation_sha256": _hash("identity-adapter"),
            "identity_registry_id": "identity-registry-01",
            "identity_registry_snapshot_id": "identity-snapshot-0001",
            "identity_registry_snapshot_sha256": _hash("identity-snapshot"),
            "identity_registry_trust_root_sha256": sha256(identity_spki).hexdigest(),
            "provider_subject_id_hash": _hash("provider-subject"),
            "provider_identity_document_sha256": _hash("provider-document"),
            "revocation_authority_source_id": "revocation-source-01",
            "revocation_authority_source_snapshot_id": "revocation-snapshot-0001",
            "revocation_authority_source_snapshot_sha256": _hash("revocation-snapshot"),
            "revocation_authority_source_trust_root_sha256": sha256(revocation_spki).hexdigest(),
            "observation_receipt_protocol_version": "observer-source-receipt-v1",
        }
        self.identity_document = identity_source.build_witness_ownership_provider_identity_source_adapter_preregistration_v1(
            **self.identity_kwargs
        )
        self.storage_kwargs = {
            "identity_source_adapter_preregistration_hash": self.identity_document[
                "adapter_preregistration_hash"
            ],
            "target_stream_id": "witness-provider-key-revocations",
            "storage_adapter_id": "snapshot-storage-adapter-01",
            "storage_adapter_static_fingerprint": "synthetic-storage-adapter-v1",
            "storage_adapter_implementation_sha256": _hash("storage-adapter"),
            "storage_backend_kind": storage_preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM,
            "storage_domain_id_hash": _hash("storage-domain"),
            "content_namespace_id_hash": _hash("content-namespace"),
            "head_namespace_id_hash": _hash("head-namespace"),
            "durability_protocol_version": "durability-protocol-v1",
            "crash_recovery_protocol_version": "crash-recovery-protocol-v1",
            "concurrency_control_protocol_version": "concurrency-protocol-v1",
        }
        self.storage_document = storage_preregistration.build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
            **self.storage_kwargs
        )
        self.plan_kwargs = {
            "driver_id": "synthetic-driver-01",
            "driver_implementation_sha256": _hash("driver-implementation"),
            "isolated_domain_id_hash": _hash("isolated-domain"),
            "plan_nonce_hash": _hash("plan-nonce"),
            "storage_preregistration_kwargs": self.storage_kwargs,
        }
        self.plan = harness.build_witness_ownership_snapshot_isolated_storage_harness_plan_v1(
            self.storage_document,
            **self.plan_kwargs,
        )
        self.harness_bundle = harness.run_witness_ownership_snapshot_isolated_storage_harness_v1(
            _Driver(),
            self.plan,
            self.storage_document,
            harness_run_nonce_hash=_hash("run-nonce"),
            expected_harness_plan_hash=self.plan["harness_plan_hash"],
            plan_build_kwargs=self.plan_kwargs,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.observer_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.observer_registrations = []
        self.observer_public_base64 = []
        for index, key in enumerate(self.observer_keys):
            spki = _spki(key)
            self.observer_public_base64.append(base64.b64encode(spki).decode("ascii"))
            self.observer_registrations.append(
                evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
                    observer_id=f"observer-{index + 1}",
                    trust_domain=f"trust-domain-{index + 1}",
                    public_key_spki_sha256=sha256(spki).hexdigest(),
                )
            )
        self.signed_reports = self._build_reports()
        self.evidence_evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            self.signed_reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.identity_assertions = self._build_identity_assertions()
        self.admission_evaluation = observer_admission.evaluate_witness_ownership_storage_observer_identity_admission_v1(
            self.identity_assertions,
            self.identity_document,
            self.observer_registrations,
            identity_source_preregistration_kwargs=self.identity_kwargs,
        )

    def _sign_report(self, report, observer_index):
        message_hash = evidence.build_witness_ownership_snapshot_storage_observer_signature_message_hash_v1(
            report,
            self.storage_document,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        signature = self.observer_keys[observer_index].sign(bytes.fromhex(message_hash))
        return evidence.build_signed_witness_ownership_snapshot_storage_observer_report_v1(
            report,
            self.storage_document,
            self.observer_registrations[observer_index],
            public_key_spki_base64=self.observer_public_base64[observer_index],
            signature_base64=base64.b64encode(signature).decode("ascii"),
            storage_preregistration_kwargs=self.storage_kwargs,
        )

    def _build_reports(self, overrides=None):
        overrides = overrides or {}
        plan_by_requirement = {
            row["requirement_id"]: row for row in self.plan["scenarios"]
        }
        result_by_requirement = {
            row["requirement_id"]: row
            for row in self.harness_bundle["scenario_result_documents"]
        }
        reports = []
        for requirement_index, requirement in enumerate(
            self.storage_document["required_evidence"]
        ):
            requirement_id = requirement["requirement_id"]
            plan_row = plan_by_requirement[requirement_id]
            values = overrides.get(requirement_id, {})
            scenario_hash = values.get(
                "scenario_hash",
                plan_row["scenario_preregistration_hash"],
            )
            artifact_hash = values.get(
                "artifact_hash",
                (
                    result_by_requirement[requirement_id]["observed_artifact_hash"]
                    if plan_row["execution_mode"] == harness.EXECUTION_MODE_DRIVER
                    else self.harness_bundle["evaluation"]["observer_handoff_hash"]
                ),
            )
            outcome = values.get("outcome", evidence.OUTCOME_PASS)
            for observer_index in (
                requirement_index % 3,
                (requirement_index + 1) % 3,
            ):
                registration = self.observer_registrations[observer_index]
                report = evidence.build_witness_ownership_snapshot_storage_observer_report_v1(
                    self.storage_document,
                    requirement_id=requirement_id,
                    observer_id=registration["observer_id"],
                    observer_trust_domain=registration["trust_domain"],
                    run_context_hash=_hash(
                        f"run-{requirement_index}-{observer_index}-{scenario_hash}-{artifact_hash}"
                    ),
                    scenario_preregistration_hash=scenario_hash,
                    observed_artifact_hash=artifact_hash,
                    declared_outcome=outcome,
                    storage_preregistration_kwargs=self.storage_kwargs,
                )
                reports.append(self._sign_report(report, observer_index))
        return reports

    def _build_identity_assertions(self):
        assertions = []
        identity_spki_b64 = base64.b64encode(_spki(self.identity_key)).decode("ascii")
        revocation_spki_b64 = base64.b64encode(_spki(self.revocation_key)).decode("ascii")
        for index, registration in enumerate(self.observer_registrations):
            claim = observer_admission.build_witness_ownership_storage_observer_identity_claim_v1(
                self.identity_document,
                registration,
                claim_nonce_hash=_hash(f"identity-claim-{index}"),
                expected_identity_source_preregistration_hash=self.identity_document[
                    "adapter_preregistration_hash"
                ],
                identity_source_preregistration_kwargs=self.identity_kwargs,
            )
            identity_message = observer_admission.build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
                claim,
                self.identity_document,
                registration,
                signature_domain=observer_admission.IDENTITY_REGISTRY_SIGNATURE_DOMAIN,
                identity_source_preregistration_kwargs=self.identity_kwargs,
            )
            revocation_message = observer_admission.build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
                claim,
                self.identity_document,
                registration,
                signature_domain=observer_admission.REVOCATION_SOURCE_SIGNATURE_DOMAIN,
                identity_source_preregistration_kwargs=self.identity_kwargs,
            )
            assertions.append(
                observer_admission.build_dual_signed_witness_ownership_storage_observer_identity_assertion_v1(
                    claim,
                    self.identity_document,
                    registration,
                    identity_registry_public_key_spki_base64=identity_spki_b64,
                    identity_registry_signature_base64=base64.b64encode(
                        self.identity_key.sign(bytes.fromhex(identity_message))
                    ).decode("ascii"),
                    revocation_source_public_key_spki_base64=revocation_spki_b64,
                    revocation_source_signature_base64=base64.b64encode(
                        self.revocation_key.sign(bytes.fromhex(revocation_message))
                    ).decode("ascii"),
                    identity_source_preregistration_kwargs=self.identity_kwargs,
                )
            )
        return assertions

    def _evaluate(self, reports=None, evidence_evaluation=None, harness_bundle=None, admission_evaluation=None):
        return binding.evaluate_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
            self.evidence_evaluation if evidence_evaluation is None else evidence_evaluation,
            self.signed_reports if reports is None else reports,
            self.harness_bundle if harness_bundle is None else harness_bundle,
            self.plan,
            self.admission_evaluation if admission_evaluation is None else admission_evaluation,
            self.identity_assertions,
            self.identity_document,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
            harness_plan_build_kwargs=self.plan_kwargs,
            identity_source_preregistration_kwargs=self.identity_kwargs,
        )

    def test_complete_chain_binds_thirteen_driver_and_one_observer_requirement(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["status"], binding.STATUS_LINEAGE_BOUND)
        self.assertEqual(result["bound_driver_requirement_count"], 13)
        self.assertEqual(result["bound_observer_requirement_count"], 1)
        self.assertEqual(result["bound_signed_report_count"], 28)

    def test_success_keeps_external_persistence_and_authority_locked(self) -> None:
        result = self._evaluate()
        self.assertFalse(result["external_observer_identity_verified"])
        self.assertFalse(result["real_adapter_execution_verified"])
        self.assertFalse(result["external_persistence_independently_verified"])
        self.assertFalse(result["permission"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_authorized"])
        self.assertFalse(result["current_chain_activated"])

    def test_exact_verifier_accepts_exact_binding(self) -> None:
        result = self._evaluate()
        self.assertTrue(
            binding.verify_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
                result,
                self.evidence_evaluation,
                self.signed_reports,
                self.harness_bundle,
                self.plan,
                self.admission_evaluation,
                self.identity_assertions,
                self.identity_document,
                self.storage_document,
                self.observer_registrations,
                expected_lineage_binding_hash=result["lineage_binding_hash"],
                storage_preregistration_kwargs=self.storage_kwargs,
                harness_plan_build_kwargs=self.plan_kwargs,
                identity_source_preregistration_kwargs=self.identity_kwargs,
            )
        )

    def test_driver_scenario_mismatch_blocks_even_when_evidence_quorum_passes(self) -> None:
        requirement_id = self.plan["scenarios"][0]["requirement_id"]
        reports = self._build_reports({requirement_id: {"scenario_hash": _hash("wrong-scenario")}})
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertEqual(evaluation["status"], evidence.STATUS_SIGNED_STRUCTURAL_COVERAGE)
        result = self._evaluate(reports, evaluation)
        self.assertEqual(result["blocker_codes"], ["report_to_harness_scenario_lineage_invalid"])

    def test_driver_artifact_mismatch_blocks_even_when_evidence_quorum_passes(self) -> None:
        requirement_id = self.plan["scenarios"][0]["requirement_id"]
        reports = self._build_reports({requirement_id: {"artifact_hash": _hash("wrong-artifact")}})
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        result = self._evaluate(reports, evaluation)
        self.assertEqual(result["blocker_codes"], ["report_to_driver_artifact_lineage_invalid"])

    def test_observer_scenario_mismatch_is_blocked(self) -> None:
        requirement_id = harness.OBSERVER_ONLY_REQUIREMENT_ID
        reports = self._build_reports({requirement_id: {"scenario_hash": _hash("wrong-observer-scenario")}})
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        result = self._evaluate(reports, evaluation)
        self.assertEqual(result["blocker_codes"], ["report_to_harness_scenario_lineage_invalid"])

    def test_observer_handoff_mismatch_is_blocked(self) -> None:
        requirement_id = harness.OBSERVER_ONLY_REQUIREMENT_ID
        reports = self._build_reports({requirement_id: {"artifact_hash": _hash("wrong-handoff")}})
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        result = self._evaluate(reports, evaluation)
        self.assertEqual(result["blocker_codes"], ["report_to_observer_handoff_lineage_invalid"])

    def test_component_block_status_prevents_lineage_success(self) -> None:
        requirement_id = self.plan["scenarios"][0]["requirement_id"]
        reports = self._build_reports({requirement_id: {"outcome": evidence.OUTCOME_BLOCK}})
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        result = self._evaluate(reports, evaluation)
        self.assertEqual(result["blocker_codes"], ["component_success_status_invalid"])

    def test_tampered_evidence_evaluation_is_rejected(self) -> None:
        tampered = deepcopy(self.evidence_evaluation)
        tampered["permission"] = True
        self.assertEqual(self._evaluate(evidence_evaluation=tampered), {})

    def test_tampered_harness_bundle_is_rejected(self) -> None:
        tampered = deepcopy(self.harness_bundle)
        tampered["evaluation"]["permission"] = True
        self.assertEqual(self._evaluate(harness_bundle=tampered), {})

    def test_tampered_observer_admission_is_rejected(self) -> None:
        tampered = deepcopy(self.admission_evaluation)
        tampered["permission"] = True
        self.assertEqual(self._evaluate(admission_evaluation=tampered), {})

    def test_signed_report_order_does_not_change_binding(self) -> None:
        shuffled = list(self.signed_reports)
        random.Random(42).shuffle(shuffled)
        evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            shuffled,
            self.storage_document,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertEqual(self._evaluate()["lineage_binding_hash"], self._evaluate(shuffled, evaluation)["lineage_binding_hash"])

    def test_verifier_rejects_authority_escalation(self) -> None:
        result = self._evaluate()
        tampered = deepcopy(result)
        tampered["permission"] = True
        self.assertFalse(
            binding.verify_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1(
                tampered,
                self.evidence_evaluation,
                self.signed_reports,
                self.harness_bundle,
                self.plan,
                self.admission_evaluation,
                self.identity_assertions,
                self.identity_document,
                self.storage_document,
                self.observer_registrations,
                expected_lineage_binding_hash=result["lineage_binding_hash"],
                storage_preregistration_kwargs=self.storage_kwargs,
                harness_plan_build_kwargs=self.plan_kwargs,
                identity_source_preregistration_kwargs=self.identity_kwargs,
            )
        )


if __name__ == "__main__":
    unittest.main()
