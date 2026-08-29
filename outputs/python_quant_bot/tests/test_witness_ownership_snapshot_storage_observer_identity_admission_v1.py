from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as storage_evidence,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_observer_identity_admission_v1 as admission,
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


class WitnessOwnershipStorageObserverIdentityAdmissionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity_registry_key = Ed25519PrivateKey.generate()
        self.revocation_source_key = Ed25519PrivateKey.generate()
        self.identity_registry_spki = _spki(self.identity_registry_key)
        self.revocation_source_spki = _spki(self.revocation_source_key)
        self.identity_source_kwargs = {
            "target_stream_id": "witness-provider-key-revocations",
            "provider_preregistration_hash": _hash("provider-preregistration"),
            "active_key_state_hash": _hash("active-key-state"),
            "revocation_quorum_evidence_hash": _hash("revocation-quorum"),
            "identity_source_adapter_id": "external-identity-source-adapter-01",
            "identity_source_adapter_static_fingerprint": (
                "synthetic-external-identity-source-adapter-v1"
            ),
            "identity_source_adapter_implementation_sha256": _hash(
                "identity-source-adapter-implementation"
            ),
            "identity_registry_id": "identity-registry-01",
            "identity_registry_snapshot_id": "identity-snapshot-0001",
            "identity_registry_snapshot_sha256": _hash(
                "identity-registry-snapshot"
            ),
            "identity_registry_trust_root_sha256": sha256(
                self.identity_registry_spki
            ).hexdigest(),
            "provider_subject_id_hash": _hash("provider-subject-id"),
            "provider_identity_document_sha256": _hash(
                "provider-identity-document"
            ),
            "revocation_authority_source_id": "revocation-authority-source-01",
            "revocation_authority_source_snapshot_id": "revocation-source-0001",
            "revocation_authority_source_snapshot_sha256": _hash(
                "revocation-source-snapshot"
            ),
            "revocation_authority_source_trust_root_sha256": sha256(
                self.revocation_source_spki
            ).hexdigest(),
            "observation_receipt_protocol_version": (
                "witness-provider-identity-source-observation-receipt-v1"
            ),
        }
        self.identity_source_document = identity_source.build_witness_ownership_provider_identity_source_adapter_preregistration_v1(
            **self.identity_source_kwargs
        )
        self.observer_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.observer_registrations = []
        for index, observer_key in enumerate(self.observer_keys):
            observer_spki = _spki(observer_key)
            self.observer_registrations.append(
                storage_evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
                    observer_id=f"observer-{index + 1}",
                    trust_domain=f"trust-domain-{index + 1}",
                    public_key_spki_sha256=sha256(observer_spki).hexdigest(),
                )
            )

    def _signed_assertion(
        self,
        observer_index: int,
        *,
        nonce_label: str | None = None,
        identity_key: Ed25519PrivateKey | None = None,
        revocation_key: Ed25519PrivateKey | None = None,
    ):
        registration = self.observer_registrations[observer_index]
        claim = admission.build_witness_ownership_storage_observer_identity_claim_v1(
            self.identity_source_document,
            registration,
            claim_nonce_hash=_hash(nonce_label or f"claim-nonce-{observer_index}"),
            expected_identity_source_preregistration_hash=(
                self.identity_source_document["adapter_preregistration_hash"]
            ),
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )
        identity_message = admission.build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
            claim,
            self.identity_source_document,
            registration,
            signature_domain=admission.IDENTITY_REGISTRY_SIGNATURE_DOMAIN,
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )
        revocation_message = admission.build_witness_ownership_storage_observer_identity_signature_message_hash_v1(
            claim,
            self.identity_source_document,
            registration,
            signature_domain=admission.REVOCATION_SOURCE_SIGNATURE_DOMAIN,
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )
        identity_key = identity_key or self.identity_registry_key
        revocation_key = revocation_key or self.revocation_source_key
        identity_spki = _spki(identity_key)
        revocation_spki = _spki(revocation_key)
        return admission.build_dual_signed_witness_ownership_storage_observer_identity_assertion_v1(
            claim,
            self.identity_source_document,
            registration,
            identity_registry_public_key_spki_base64=base64.b64encode(
                identity_spki
            ).decode("ascii"),
            identity_registry_signature_base64=base64.b64encode(
                identity_key.sign(bytes.fromhex(identity_message))
            ).decode("ascii"),
            revocation_source_public_key_spki_base64=base64.b64encode(
                revocation_spki
            ).decode("ascii"),
            revocation_source_signature_base64=base64.b64encode(
                revocation_key.sign(bytes.fromhex(revocation_message))
            ).decode("ascii"),
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )

    def _assertions(self):
        return [self._signed_assertion(index) for index in range(3)]

    def _evaluate(self, assertions=None, registrations=None):
        return admission.evaluate_witness_ownership_storage_observer_identity_admission_v1(
            self._assertions() if assertions is None else assertions,
            self.identity_source_document,
            self.observer_registrations if registrations is None else registrations,
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )

    def test_claim_binds_observer_and_both_source_snapshots(self) -> None:
        assertion = self._signed_assertion(0)
        claim = assertion["claim_document"]
        self.assertEqual(
            claim["observer_registration_hash"],
            self.observer_registrations[0]["observer_registration_hash"],
        )
        self.assertEqual(
            claim["identity_registry_snapshot_sha256"],
            self.identity_source_kwargs["identity_registry_snapshot_sha256"],
        )
        self.assertEqual(
            claim["revocation_source_snapshot_sha256"],
            self.identity_source_kwargs[
                "revocation_authority_source_snapshot_sha256"
            ],
        )

    def test_signature_domains_are_separate(self) -> None:
        assertion = self._signed_assertion(0)
        self.assertNotEqual(
            assertion["identity_registry_signature_message_hash"],
            assertion["revocation_source_signature_message_hash"],
        )

    def test_complete_dual_signed_set_is_structurally_admissible(self) -> None:
        result = self._evaluate()
        self.assertEqual(
            result["status"],
            admission.STATUS_DUAL_SIGNED_ADMISSION_CANDIDATE,
        )
        self.assertEqual(result["gate_status"], admission.GATE_STATUS_UNKNOWN)
        self.assertEqual(result["covered_observer_count"], 3)
        self.assertTrue(result["identity_registry_signatures_verified"])
        self.assertTrue(result["revocation_source_signatures_verified"])
        self.assertTrue(result["isolated_evidence_observer_admission_candidate"])

    def test_success_keeps_external_truth_and_authority_locked(self) -> None:
        result = self._evaluate()
        self.assertFalse(result["external_observer_identity_verified"])
        self.assertFalse(result["external_source_truth_verified"])
        self.assertFalse(result["external_persistence_independently_verified"])
        self.assertFalse(result["permission"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_authorized"])
        self.assertFalse(result["current_chain_activated"])

    def test_exact_evaluation_verifier_accepts_exact_rebuild(self) -> None:
        assertions = self._assertions()
        result = self._evaluate(assertions)
        self.assertTrue(
            admission.verify_witness_ownership_storage_observer_identity_admission_v1(
                result,
                assertions,
                self.identity_source_document,
                self.observer_registrations,
                expected_observer_admission_evaluation_hash=result[
                    "observer_admission_evaluation_hash"
                ],
                identity_source_preregistration_kwargs=self.identity_source_kwargs,
            )
        )

    def test_missing_assertion_blocks_cardinality(self) -> None:
        result = self._evaluate(self._assertions()[:-1])
        self.assertEqual(
            result["blocker_codes"],
            ["observer_assertion_cardinality_invalid"],
        )

    def test_duplicate_assertion_is_replay(self) -> None:
        assertions = self._assertions()
        assertions[2] = assertions[0]
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_replay_detected"],
        )

    def test_claim_nonce_replay_is_rejected(self) -> None:
        assertions = self._assertions()
        assertions[1] = self._signed_assertion(1, nonce_label="claim-nonce-0")
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["observer_identity_claim_nonce_replay_detected"],
        )

    def test_observer_coverage_must_be_exact(self) -> None:
        assertions = self._assertions()
        assertions[2] = self._signed_assertion(0, nonce_label="alternate-observer-0")
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["observer_identity_assertion_coverage_invalid"],
        )

    def test_tampered_identity_signature_is_rejected(self) -> None:
        assertions = self._assertions()
        tampered = deepcopy(assertions[0])
        raw = bytearray(base64.b64decode(tampered["identity_registry_signature_base64"]))
        raw[0] ^= 1
        tampered["identity_registry_signature_base64"] = base64.b64encode(raw).decode("ascii")
        assertions[0] = tampered
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_invalid"],
        )

    def test_tampered_revocation_signature_is_rejected(self) -> None:
        assertions = self._assertions()
        tampered = deepcopy(assertions[0])
        raw = bytearray(base64.b64decode(tampered["revocation_source_signature_base64"]))
        raw[0] ^= 1
        tampered["revocation_source_signature_base64"] = base64.b64encode(raw).decode("ascii")
        assertions[0] = tampered
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_invalid"],
        )

    def test_wrong_identity_trust_root_key_cannot_build_assertion(self) -> None:
        assertion = self._signed_assertion(0, identity_key=Ed25519PrivateKey.generate())
        self.assertEqual(assertion, {})

    def test_wrong_revocation_trust_root_key_cannot_build_assertion(self) -> None:
        assertion = self._signed_assertion(0, revocation_key=Ed25519PrivateKey.generate())
        self.assertEqual(assertion, {})

    def test_swapped_source_signatures_are_rejected(self) -> None:
        assertion = self._signed_assertion(0)
        swapped = deepcopy(assertion)
        swapped["identity_registry_signature_base64"], swapped[
            "revocation_source_signature_base64"
        ] = (
            swapped["revocation_source_signature_base64"],
            swapped["identity_registry_signature_base64"],
        )
        result = self._evaluate([swapped, self._signed_assertion(1), self._signed_assertion(2)])
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_invalid"],
        )

    def test_duplicate_observer_trust_domains_are_rejected(self) -> None:
        registrations = deepcopy(self.observer_registrations)
        registrations[2] = storage_evidence.build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id=registrations[2]["observer_id"],
            trust_domain=registrations[0]["trust_domain"],
            public_key_spki_sha256=registrations[2]["public_key_spki_sha256"],
        )
        result = self._evaluate(registrations=registrations)
        self.assertEqual(
            result["blocker_codes"],
            ["observer_structural_independence_invalid"],
        )

    def test_identity_status_tamper_breaks_exact_assertion(self) -> None:
        assertions = self._assertions()
        tampered = deepcopy(assertions[0])
        tampered["claim_document"]["identity_status"] = "SUSPENDED"
        assertions[0] = tampered
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_invalid"],
        )

    def test_revocation_status_tamper_breaks_exact_assertion(self) -> None:
        assertions = self._assertions()
        tampered = deepcopy(assertions[0])
        tampered["claim_document"]["revocation_status"] = "REVOKED"
        assertions[0] = tampered
        result = self._evaluate(assertions)
        self.assertEqual(
            result["blocker_codes"],
            ["dual_signed_observer_identity_assertion_invalid"],
        )

    def test_invalid_identity_source_registration_is_rejected(self) -> None:
        tampered = deepcopy(self.identity_source_document)
        tampered["authority"]["permission"] = True
        result = admission.evaluate_witness_ownership_storage_observer_identity_admission_v1(
            [],
            tampered,
            self.observer_registrations,
            identity_source_preregistration_kwargs=self.identity_source_kwargs,
        )
        self.assertEqual(result, {})

    def test_evaluation_verifier_rejects_authority_escalation(self) -> None:
        assertions = self._assertions()
        result = self._evaluate(assertions)
        tampered = deepcopy(result)
        tampered["permission"] = True
        self.assertFalse(
            admission.verify_witness_ownership_storage_observer_identity_admission_v1(
                tampered,
                assertions,
                self.identity_source_document,
                self.observer_registrations,
                expected_observer_admission_evaluation_hash=result[
                    "observer_admission_evaluation_hash"
                ],
                identity_source_preregistration_kwargs=self.identity_source_kwargs,
            )
        )

    def test_claim_contains_no_raw_provider_subject_or_credentials(self) -> None:
        claim = self._signed_assertion(0)["claim_document"]
        serialized = str(claim)
        self.assertNotIn("provider@example", serialized)
        self.assertNotIn("credential", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("storage_path", serialized)


if __name__ == "__main__":
    unittest.main()
