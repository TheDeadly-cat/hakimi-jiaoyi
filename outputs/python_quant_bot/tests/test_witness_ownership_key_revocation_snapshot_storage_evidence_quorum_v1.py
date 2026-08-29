from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as storage_preregistration,
)
from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as evidence,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipSnapshotStorageEvidenceQuorumV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_kwargs = {
            "identity_source_adapter_preregistration_hash": _hash(
                "identity-source-preregistration"
            ),
            "target_stream_id": "witness-provider-key-revocations",
            "storage_adapter_id": "snapshot-storage-adapter-01",
            "storage_adapter_static_fingerprint": (
                "synthetic-snapshot-storage-adapter-v1"
            ),
            "storage_adapter_implementation_sha256": _hash(
                "storage-adapter-implementation"
            ),
            "storage_backend_kind": storage_preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM,
            "storage_domain_id_hash": _hash("storage-domain-id"),
            "content_namespace_id_hash": _hash("content-namespace-id"),
            "head_namespace_id_hash": _hash("head-namespace-id"),
            "durability_protocol_version": "synthetic-durability-protocol-v1",
            "crash_recovery_protocol_version": (
                "synthetic-crash-recovery-protocol-v1"
            ),
            "concurrency_control_protocol_version": (
                "synthetic-concurrency-control-protocol-v1"
            ),
        }
        self.storage_document = storage_preregistration.build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
            **self.storage_kwargs
        )
        self.private_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.public_key_base64 = []
        self.observer_registrations = []
        for index, private_key in enumerate(self.private_keys):
            spki = private_key.public_key().public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            self.public_key_base64.append(base64.b64encode(spki).decode("ascii"))
            registration = evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
                observer_id=f"observer-{index + 1}",
                trust_domain=f"trust-domain-{index + 1}",
                public_key_spki_sha256=sha256(spki).hexdigest(),
            )
            self.observer_registrations.append(registration)

    def _signed_report(
        self,
        requirement_index: int,
        observer_index: int,
        *,
        outcome: str = evidence.OUTCOME_PASS,
        scenario_suffix: str = "",
        artifact_suffix: str = "",
        run_context_override: str | None = None,
    ):
        requirement = self.storage_document["required_evidence"][requirement_index]
        registration = self.observer_registrations[observer_index]
        report = evidence.build_witness_ownership_snapshot_storage_observer_report_v1(
            self.storage_document,
            requirement_id=requirement["requirement_id"],
            observer_id=registration["observer_id"],
            observer_trust_domain=registration["trust_domain"],
            run_context_hash=(
                run_context_override
                or _hash(f"run-{requirement_index}-{observer_index}-{scenario_suffix}-{artifact_suffix}")
            ),
            scenario_preregistration_hash=_hash(
                f"scenario-{requirement_index}-{scenario_suffix}"
            ),
            observed_artifact_hash=_hash(
                f"artifact-{requirement_index}-{artifact_suffix}"
            ),
            declared_outcome=outcome,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        message_hash = evidence.build_witness_ownership_snapshot_storage_observer_signature_message_hash_v1(
            report,
            self.storage_document,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        signature = self.private_keys[observer_index].sign(bytes.fromhex(message_hash))
        return evidence.build_signed_witness_ownership_snapshot_storage_observer_report_v1(
            report,
            self.storage_document,
            registration,
            public_key_spki_base64=self.public_key_base64[observer_index],
            signature_base64=base64.b64encode(signature).decode("ascii"),
            storage_preregistration_kwargs=self.storage_kwargs,
        )

    def _full_bundle(self):
        reports = []
        for requirement_index in range(len(self.storage_document["required_evidence"])):
            first = requirement_index % 3
            second = (requirement_index + 1) % 3
            reports.append(self._signed_report(requirement_index, first))
            reports.append(self._signed_report(requirement_index, second))
        return reports

    def _evaluate(self, reports=None, registrations=None):
        return evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            self._full_bundle() if reports is None else reports,
            self.storage_document,
            self.observer_registrations if registrations is None else registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )

    def test_observer_registration_is_deterministic(self) -> None:
        registration = self.observer_registrations[0]
        rebuilt = evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id=registration["observer_id"],
            trust_domain=registration["trust_domain"],
            public_key_spki_sha256=registration["public_key_spki_sha256"],
        )
        self.assertEqual(registration, rebuilt)

    def test_report_binds_storage_requirement_and_run_context(self) -> None:
        signed = self._signed_report(0, 0)
        report = signed["report_document"]
        self.assertEqual(
            report["storage_adapter_preregistration_hash"],
            self.storage_document["storage_adapter_preregistration_hash"],
        )
        self.assertEqual(
            report["requirement_id"],
            self.storage_document["required_evidence"][0]["requirement_id"],
        )

    def test_signed_report_has_valid_local_signature_binding(self) -> None:
        signed = self._signed_report(0, 0)
        self.assertRegex(signed["signature_message_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(signed["signed_observer_report_hash"], r"^[0-9a-f]{64}$")

    def test_complete_two_of_three_bundle_is_structurally_verified(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["status"], evidence.STATUS_SIGNED_STRUCTURAL_COVERAGE)
        self.assertEqual(result["gate_status"], evidence.GATE_STATUS_UNKNOWN)
        self.assertEqual(result["expected_requirement_count"], 14)
        self.assertEqual(result["observed_signed_report_count"], 28)
        self.assertEqual(result["used_observer_count"], 3)
        self.assertTrue(result["signed_report_signatures_verified"])
        self.assertTrue(result["requirement_coverage_verified"])

    def test_success_still_denies_external_persistence_and_authority(self) -> None:
        result = self._evaluate()
        self.assertFalse(result["external_observer_identity_verified"])
        self.assertFalse(result["adapter_runtime_execution_verified"])
        self.assertFalse(result["external_persistence_independently_verified"])
        self.assertFalse(result["permission"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_authorized"])
        self.assertFalse(result["snapshot_publication_authorized"])
        self.assertFalse(result["current_chain_activated"])

    def test_exact_evaluation_verifier_accepts_exact_rebuild(self) -> None:
        reports = self._full_bundle()
        result = self._evaluate(reports)
        self.assertTrue(
            evidence.verify_witness_ownership_snapshot_storage_evidence_quorum_v1(
                result,
                reports,
                self.storage_document,
                self.observer_registrations,
                expected_quorum_evaluation_hash=result["quorum_evaluation_hash"],
                storage_preregistration_kwargs=self.storage_kwargs,
            )
        )

    def test_missing_report_blocks_cardinality(self) -> None:
        result = self._evaluate(self._full_bundle()[:-1])
        self.assertEqual(result["status"], evidence.STATUS_BLOCK)
        self.assertEqual(
            result["blocker_codes"],
            ["signed_report_collection_cardinality_invalid"],
        )

    def test_duplicate_signed_report_is_replay(self) -> None:
        reports = self._full_bundle()
        reports[-1] = reports[0]
        result = self._evaluate(reports)
        self.assertEqual(
            result["blocker_codes"],
            ["signed_observer_report_replay_detected"],
        )

    def test_tampered_signature_is_rejected(self) -> None:
        reports = self._full_bundle()
        tampered = deepcopy(reports[0])
        signature = bytearray(base64.b64decode(tampered["observer_signature_base64"]))
        signature[0] ^= 1
        tampered["observer_signature_base64"] = base64.b64encode(signature).decode("ascii")
        reports[0] = tampered
        result = self._evaluate(reports)
        self.assertEqual(result["blocker_codes"], ["signed_observer_report_invalid"])

    def test_non_pass_outcome_blocks_requirement(self) -> None:
        reports = self._full_bundle()
        reports[0] = self._signed_report(0, 0, outcome=evidence.OUTCOME_BLOCK)
        result = self._evaluate(reports)
        self.assertEqual(result["blocker_codes"], ["requirement_outcome_not_pass"])

    def test_scenario_disagreement_blocks_consensus(self) -> None:
        reports = self._full_bundle()
        reports[1] = self._signed_report(0, 1, scenario_suffix="different")
        result = self._evaluate(reports)
        self.assertEqual(
            result["blocker_codes"],
            ["requirement_scenario_consensus_invalid"],
        )

    def test_artifact_disagreement_blocks_consensus(self) -> None:
        reports = self._full_bundle()
        reports[1] = self._signed_report(0, 1, artifact_suffix="different")
        result = self._evaluate(reports)
        self.assertEqual(
            result["blocker_codes"],
            ["requirement_artifact_consensus_invalid"],
        )

    def test_run_context_replay_is_rejected(self) -> None:
        reports = self._full_bundle()
        repeated_context = reports[0]["report_document"]["run_context_hash"]
        reports[2] = self._signed_report(
            1,
            1,
            run_context_override=repeated_context,
        )
        result = self._evaluate(reports)
        self.assertEqual(result["blocker_codes"], ["run_context_replay_detected"])

    def test_requirement_observers_must_be_distinct(self) -> None:
        reports = self._full_bundle()
        reports[1] = self._signed_report(0, 0, run_context_override=_hash("alternate-run"))
        result = self._evaluate(reports)
        self.assertEqual(
            result["blocker_codes"],
            ["requirement_observer_independence_invalid"],
        )

    def test_registered_observer_domains_must_be_distinct(self) -> None:
        registrations = deepcopy(self.observer_registrations)
        registrations[2] = evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id=registrations[2]["observer_id"],
            trust_domain=registrations[0]["trust_domain"],
            public_key_spki_sha256=registrations[2]["public_key_spki_sha256"],
        )
        result = self._evaluate(registrations=registrations)
        self.assertEqual(
            result["blocker_codes"],
            ["observer_structural_independence_invalid"],
        )

    def test_all_three_registered_observers_must_be_used(self) -> None:
        reports = []
        for requirement_index in range(14):
            reports.append(self._signed_report(requirement_index, 0))
            reports.append(self._signed_report(requirement_index, 1))
        result = self._evaluate(reports)
        self.assertEqual(
            result["blocker_codes"],
            ["registered_observer_coverage_invalid"],
        )

    def test_unknown_requirement_is_rejected_before_signing(self) -> None:
        report = evidence.build_witness_ownership_snapshot_storage_observer_report_v1(
            self.storage_document,
            requirement_id="UNREGISTERED_REQUIREMENT",
            observer_id="observer-1",
            observer_trust_domain="trust-domain-1",
            run_context_hash=_hash("run"),
            scenario_preregistration_hash=_hash("scenario"),
            observed_artifact_hash=_hash("artifact"),
            declared_outcome=evidence.OUTCOME_PASS,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertEqual(report, {})

    def test_invalid_storage_registration_is_rejected(self) -> None:
        tampered = deepcopy(self.storage_document)
        tampered["authority"]["permission"] = True
        result = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            [],
            tampered,
            self.observer_registrations,
            storage_preregistration_kwargs=self.storage_kwargs,
        )
        self.assertEqual(result, {})

    def test_non_ascii_observer_registration_is_rejected(self) -> None:
        registration = evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id="observer-\u6d4b\u8bd5",
            trust_domain="trust-domain",
            public_key_spki_sha256=_hash("key"),
        )
        self.assertEqual(registration, {})

    def test_evaluation_verifier_rejects_extra_fields(self) -> None:
        reports = self._full_bundle()
        result = self._evaluate(reports)
        tampered = deepcopy(result)
        tampered["profitability"] = True
        self.assertFalse(
            evidence.verify_witness_ownership_snapshot_storage_evidence_quorum_v1(
                tampered,
                reports,
                self.storage_document,
                self.observer_registrations,
                expected_quorum_evaluation_hash=result["quorum_evaluation_hash"],
                storage_preregistration_kwargs=self.storage_kwargs,
            )
        )


if __name__ == "__main__":
    unittest.main()
