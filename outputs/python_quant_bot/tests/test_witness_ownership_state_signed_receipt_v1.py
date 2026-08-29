from __future__ import annotations

import base64
from dataclasses import replace
from hashlib import sha256
import inspect
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as preregistration,
)
from exchange_terminal.application import (
    witness_ownership_state_service,
)
from exchange_terminal.application import (
    witness_ownership_state_signed_receipt_v1 as signed_receipt,
)
from exchange_terminal.interfaces import witness_ownership_state_store
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_witness_ownership_state_store_contract_v1 as adr0412_tests


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipStateSignedReceiptV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = adr0412_tests.WitnessOwnershipStateStoreContractV1Tests(
            methodName=(
                "test_consumer_accepts_structure_but_keeps_source_truth_unknown"
            )
        )
        fixture.setUp()
        self.v11_document = fixture.v11_document
        self.v11_args = fixture.v11_args
        self.v11_kwargs = fixture.v11_kwargs
        self.registry_id = "synthetic-witness-ownership-registry"

        self.private_key = Ed25519PrivateKey.generate()
        self.public_spki = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.public_spki_base64 = base64.b64encode(self.public_spki).decode(
            "ascii"
        )
        self.preregistration_kwargs = {
            "registry_id": self.registry_id,
            "operator_identity_claim": "synthetic-provider-operator",
            "public_key_spki_sha256": sha256(self.public_spki).hexdigest(),
            "trust_domain": "synthetic.research.local",
            "provider_implementation_claim_sha256": _hash(
                "unverified-synthetic-provider-implementation"
            ),
        }
        self.preregistration_document = (
            preregistration.build_witness_ownership_state_provider_preregistration_v1(
                **self.preregistration_kwargs
            )
        )
        source = self.v11_document["source"]
        self.command = witness_ownership_state_store.build_witness_ownership_compare_consume_and_advance_command_v1(
            namespace_preregistration_hash=self.preregistration_document[
                "preregistration_hash"
            ],
            ownership_claim_hash=source["ownership_claim_hash"],
            ownership_evidence_hash=source["ownership_evidence_hash"],
            expected_state_hash=source["previous_ownership_state_hash"],
            proposed_state_hash=source["next_ownership_state_hash"],
            expected_registry_revision=73,
            request_nonce_hash=_hash("synthetic-signed-receipt-request-74"),
        )
        self.result = witness_ownership_state_store.build_witness_ownership_compare_consume_and_advance_result_v1(
            self.command,
            outcome=(
                witness_ownership_state_store.WitnessOwnershipProviderOutcomeV1.ADVANCED
            ),
            registry_id=self.registry_id,
            observed_registry_revision=73,
            observed_state_hash=self.command.expected_state_hash,
        )
        self.consumer_verify_kwargs = {
            "expected_budget_v11_hash": self.v11_document["budget_v11_hash"],
            "budget_v11_verify_args": self.v11_args,
            "budget_v11_verify_kwargs": self.v11_kwargs,
            "expected_command_hash": self.command.command_hash,
            "expected_registry_id": self.registry_id,
        }
        self.consumer_document = witness_ownership_state_service.evaluate_witness_ownership_state_persistence_consumer_v1(
            self.v11_document,
            self.command,
            self.result,
            **self.consumer_verify_kwargs,
        )
        self.message_hash = signed_receipt.build_witness_ownership_provider_receipt_signature_message_hash_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )
        self.signature = self.private_key.sign(bytes.fromhex(self.message_hash))
        self.signature_base64 = base64.b64encode(self.signature).decode("ascii")
        self.signed_document = signed_receipt.build_signed_witness_ownership_state_provider_receipt_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            public_key_spki_base64=self.public_spki_base64,
            signature_base64=self.signature_base64,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )

    def evaluate(self, *, signed_document=None, **overrides):
        kwargs = {
            "public_key_spki_base64": self.public_spki_base64,
            "signature_base64": self.signature_base64,
            "expected_signed_receipt_hash": self.signed_document[
                "signed_receipt_hash"
            ],
            "expected_consumer_evaluation_hash": self.consumer_document[
                "evaluation_hash"
            ],
            "consumer_verify_kwargs": self.consumer_verify_kwargs,
            "preregistration_build_kwargs": self.preregistration_kwargs,
        }
        kwargs.update(overrides)
        return signed_receipt.evaluate_signed_witness_ownership_state_provider_receipt_v1(
            self.signed_document if signed_document is None else signed_document,
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            **kwargs,
        )

    def test_reproduces_unsigned_adr0412_gap(self):
        self.assertEqual(self.consumer_document["status"], "UNKNOWN")
        self.assertFalse(
            self.consumer_document["facts"][
                "provider_receipt_signature_verified"
            ]
        )
        self.assertNotIn("signature_base64", repr(self.consumer_document))

    def test_preregistration_is_exact_deterministic_and_locked(self):
        rebuilt = preregistration.build_witness_ownership_state_provider_preregistration_v1(
            **self.preregistration_kwargs
        )
        self.assertEqual(rebuilt, self.preregistration_document)
        self.assertTrue(
            preregistration.verify_witness_ownership_state_provider_preregistration_v1(
                self.preregistration_document,
                **self.preregistration_kwargs,
            )
        )
        self.assertTrue(
            all(
                value is False
                for value in self.preregistration_document["authority"].values()
            )
        )

    def test_preregistration_key_hash_drift_is_rejected(self):
        changed = dict(self.preregistration_kwargs)
        changed["public_key_spki_sha256"] = _hash("different-key")
        self.assertFalse(
            preregistration.verify_witness_ownership_state_provider_preregistration_v1(
                self.preregistration_document,
                **changed,
            )
        )

    def test_signature_message_is_domain_separated_and_deterministic(self):
        rebuilt = signed_receipt.build_witness_ownership_provider_receipt_signature_message_hash_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )
        self.assertEqual(rebuilt, self.message_hash)
        self.assertNotEqual(
            self.message_hash,
            self.result.receipt_document["receipt_claim_hash"],
        )

    def test_signed_candidate_binds_operation_and_preregistration(self):
        self.assertEqual(
            self.signed_document["signature_message_hash"], self.message_hash
        )
        self.assertEqual(
            self.signed_document["preregistration_hash"],
            self.preregistration_document["preregistration_hash"],
        )
        self.assertEqual(
            self.signed_document["command_hash"], self.command.command_hash
        )

    def test_valid_signature_passes_but_admission_remains_blocked(self):
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["admission_status"], "BLOCKED")
        self.assertTrue(
            evidence["facts"]["provider_receipt_signature_verified"]
        )
        self.assertTrue(evidence["facts"]["provider_key_possession_observed"])
        for name in (
            "provider_organization_identity_verified",
            "provider_key_control_continuity_verified",
            "provider_implementation_verified",
            "external_provider_conformance_verified",
            "durable_commit_verified",
            "linearizable_read_after_write_verified",
            "rollback_resistance_verified",
            "witness_ownership_state_persistence_verified",
        ):
            self.assertFalse(evidence["facts"][name])
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_wrong_key_is_blocked(self):
        other_private = Ed25519PrivateKey.generate()
        other_spki = other_private.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        other_spki_base64 = base64.b64encode(other_spki).decode("ascii")
        other_signature_base64 = base64.b64encode(
            other_private.sign(bytes.fromhex(self.message_hash))
        ).decode("ascii")
        other_signed = signed_receipt.build_signed_witness_ownership_state_provider_receipt_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            public_key_spki_base64=other_spki_base64,
            signature_base64=other_signature_base64,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )
        evidence = self.evaluate(
            signed_document=other_signed,
            public_key_spki_base64=other_spki_base64,
            signature_base64=other_signature_base64,
            expected_signed_receipt_hash=other_signed["signed_receipt_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "PREREGISTERED_PUBLIC_KEY_HASH_MISMATCH", evidence["blockers"]
        )

    def test_invalid_signature_is_blocked(self):
        changed = bytearray(self.signature)
        changed[0] ^= 1
        changed_base64 = base64.b64encode(bytes(changed)).decode("ascii")
        changed_signed = signed_receipt.build_signed_witness_ownership_state_provider_receipt_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            public_key_spki_base64=self.public_spki_base64,
            signature_base64=changed_base64,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )
        evidence = self.evaluate(
            signed_document=changed_signed,
            signature_base64=changed_base64,
            expected_signed_receipt_hash=changed_signed["signed_receipt_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("ED25519_RECEIPT_SIGNATURE_INVALID", evidence["blockers"])

    def test_cross_domain_signature_is_blocked(self):
        wrong_signature = self.private_key.sign(
            bytes.fromhex(self.result.receipt_document["receipt_claim_hash"])
        )
        wrong_base64 = base64.b64encode(wrong_signature).decode("ascii")
        wrong_signed = signed_receipt.build_signed_witness_ownership_state_provider_receipt_v1(
            self.consumer_document,
            self.v11_document,
            self.command,
            self.result,
            self.preregistration_document,
            public_key_spki_base64=self.public_spki_base64,
            signature_base64=wrong_base64,
            expected_consumer_evaluation_hash=self.consumer_document[
                "evaluation_hash"
            ],
            consumer_verify_kwargs=self.consumer_verify_kwargs,
            preregistration_build_kwargs=self.preregistration_kwargs,
        )
        evidence = self.evaluate(
            signed_document=wrong_signed,
            signature_base64=wrong_base64,
            expected_signed_receipt_hash=wrong_signed["signed_receipt_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_noncanonical_public_key_base64_is_rejected(self):
        with self.assertRaises(ValueError):
            signed_receipt.build_signed_witness_ownership_state_provider_receipt_v1(
                self.consumer_document,
                self.v11_document,
                self.command,
                self.result,
                self.preregistration_document,
                public_key_spki_base64=self.public_spki_base64.rstrip("="),
                signature_base64=self.signature_base64,
                expected_consumer_evaluation_hash=self.consumer_document[
                    "evaluation_hash"
                ],
                consumer_verify_kwargs=self.consumer_verify_kwargs,
                preregistration_build_kwargs=self.preregistration_kwargs,
            )

    def test_command_preregistration_drift_is_rejected(self):
        drifted = witness_ownership_state_store.build_witness_ownership_compare_consume_and_advance_command_v1(
            namespace_preregistration_hash=_hash("different-preregistration"),
            ownership_claim_hash=self.command.ownership_claim_hash,
            ownership_evidence_hash=self.command.ownership_evidence_hash,
            expected_state_hash=self.command.expected_state_hash,
            proposed_state_hash=self.command.proposed_state_hash,
            expected_registry_revision=self.command.expected_registry_revision,
            request_nonce_hash=self.command.request_nonce_hash,
        )
        with self.assertRaises(ValueError):
            signed_receipt.build_witness_ownership_provider_receipt_signature_message_hash_v1(
                self.consumer_document,
                self.v11_document,
                drifted,
                self.result,
                self.preregistration_document,
                expected_consumer_evaluation_hash=self.consumer_document[
                    "evaluation_hash"
                ],
                consumer_verify_kwargs=self.consumer_verify_kwargs,
                preregistration_build_kwargs=self.preregistration_kwargs,
            )

    def test_resealed_consumer_promotion_is_rejected(self):
        promoted = dict(self.consumer_document)
        promoted["admission_status"] = "READY"
        promoted.pop("evaluation_hash")
        promoted = seal_strict_canonical_document(promoted, "evaluation_hash")
        with self.assertRaises(ValueError):
            signed_receipt.build_witness_ownership_provider_receipt_signature_message_hash_v1(
                promoted,
                self.v11_document,
                self.command,
                self.result,
                self.preregistration_document,
                expected_consumer_evaluation_hash=promoted["evaluation_hash"],
                consumer_verify_kwargs=self.consumer_verify_kwargs,
                preregistration_build_kwargs=self.preregistration_kwargs,
            )

    def test_tampered_receipt_claim_is_rejected(self):
        receipt = dict(self.result.receipt_document)
        receipt["receipt_claim_hash"] = _hash("tampered-receipt")
        tampered_result = replace(self.result, receipt_document=receipt)
        with self.assertRaises(ValueError):
            signed_receipt.build_witness_ownership_provider_receipt_signature_message_hash_v1(
                self.consumer_document,
                self.v11_document,
                self.command,
                tampered_result,
                self.preregistration_document,
                expected_consumer_evaluation_hash=self.consumer_document[
                    "evaluation_hash"
                ],
                consumer_verify_kwargs=self.consumer_verify_kwargs,
                preregistration_build_kwargs=self.preregistration_kwargs,
            )

    def test_exact_evidence_verifier_rejects_resealed_promotion(self):
        evidence = self.evaluate()
        evaluation_kwargs = {
            "public_key_spki_base64": self.public_spki_base64,
            "signature_base64": self.signature_base64,
            "expected_signed_receipt_hash": self.signed_document[
                "signed_receipt_hash"
            ],
            "expected_consumer_evaluation_hash": self.consumer_document[
                "evaluation_hash"
            ],
            "consumer_verify_kwargs": self.consumer_verify_kwargs,
            "preregistration_build_kwargs": self.preregistration_kwargs,
        }
        self.assertTrue(
            signed_receipt.verify_signed_witness_ownership_state_provider_receipt_evidence_v1(
                evidence,
                self.signed_document,
                self.consumer_document,
                self.v11_document,
                self.command,
                self.result,
                self.preregistration_document,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )
        promoted = dict(evidence)
        promoted["admission_status"] = "READY"
        promoted.pop("verification_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "verification_evidence_hash"
        )
        self.assertFalse(
            signed_receipt.verify_signed_witness_ownership_state_provider_receipt_evidence_v1(
                promoted,
                self.signed_document,
                self.consumer_document,
                self.v11_document,
                self.command,
                self.result,
                self.preregistration_document,
                expected_verification_evidence_hash=promoted[
                    "verification_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )

    def test_evidence_is_deterministic_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        serialized = repr(first)
        self.assertNotIn(self.signature_base64, serialized)
        self.assertNotIn(self.public_spki_base64, serialized)

    def test_production_reuses_shared_parser_and_has_no_private_key_or_io(self):
        source = inspect.getsource(preregistration) + inspect.getsource(
            signed_receipt
        )
        self.assertIn("decode_canonical_base64_v1", source)
        self.assertIn("load_canonical_ed25519_public_key_v1", source)
        for forbidden in (
            "Ed25519PrivateKey",
            "base64.b64decode",
            "serialization.load_der_public_key",
            "requests.",
            "socket.",
            "subprocess.",
            "sqlite3",
            "os.environ",
            "Path(",
            "open(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
