from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import inspect
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_state_provider_key_continuity_v1 as continuity,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_witness_ownership_state_signed_receipt_v1 as adr0413_tests


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipProviderKeyContinuityV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = adr0413_tests.WitnessOwnershipStateSignedReceiptV1Tests(
            methodName="test_valid_signature_passes_but_admission_remains_blocked"
        )
        fixture.setUp()
        self.provider_preregistration_document = fixture.preregistration_document
        self.provider_preregistration_kwargs = fixture.preregistration_kwargs
        self.adr0413_evidence = fixture.evaluate()
        self.old_private_key = fixture.private_key
        self.old_spki = fixture.public_spki
        self.old_spki_base64 = fixture.public_spki_base64
        self.old_key_hash = sha256(self.old_spki).hexdigest()
        self.new_private_key = Ed25519PrivateKey.generate()
        self.new_spki = self.new_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.new_spki_base64 = base64.b64encode(self.new_spki).decode("ascii")
        self.new_key_hash = sha256(self.new_spki).hexdigest()
        self.previous_state_kwargs = {
            "key_epoch": 0,
            "active_public_key_spki_sha256": self.old_key_hash,
            "predecessor_key_state_hash": continuity.ZERO_HASH,
            "last_rotation_event_hash": continuity.ZERO_HASH,
            "provider_preregistration_kwargs": self.provider_preregistration_kwargs,
        }
        self.previous_state = continuity.build_witness_ownership_provider_key_continuity_state_v1(
            self.provider_preregistration_document,
            **self.previous_state_kwargs,
        )
        self.claim_kwargs = {
            "expected_previous_key_state_hash": self.previous_state[
                "key_state_hash"
            ],
            "previous_key_state_build_kwargs": self.previous_state_kwargs,
            "next_public_key_spki_sha256": self.new_key_hash,
            "rotation_nonce_hash": _hash("synthetic-rotation-nonce-1"),
            "revocation_snapshot_hash": _hash(
                "synthetic-revocation-snapshot-unverified"
            ),
            "rotation_reason_code": "SCHEDULED_ROTATION",
            "provider_preregistration_kwargs": self.provider_preregistration_kwargs,
        }
        self.claim = continuity.build_witness_ownership_provider_key_rotation_claim_v1(
            self.previous_state,
            self.provider_preregistration_document,
            **self.claim_kwargs,
        )
        self.message_hash = continuity.build_witness_ownership_provider_key_rotation_signature_message_hash_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
        )
        self.old_signature = self.old_private_key.sign(
            bytes.fromhex(self.message_hash)
        )
        self.new_signature = self.new_private_key.sign(
            bytes.fromhex(self.message_hash)
        )
        self.old_signature_base64 = base64.b64encode(self.old_signature).decode(
            "ascii"
        )
        self.new_signature_base64 = base64.b64encode(self.new_signature).decode(
            "ascii"
        )
        self.signed_document = continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            old_public_key_spki_base64=self.old_spki_base64,
            new_public_key_spki_base64=self.new_spki_base64,
            old_signature_base64=self.old_signature_base64,
            new_signature_base64=self.new_signature_base64,
            expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
            rotation_claim_build_kwargs=self.claim_kwargs,
        )

    def evaluate(self, *, signed_document=None, **overrides):
        kwargs = {
            "old_public_key_spki_base64": self.old_spki_base64,
            "new_public_key_spki_base64": self.new_spki_base64,
            "old_signature_base64": self.old_signature_base64,
            "new_signature_base64": self.new_signature_base64,
            "expected_rotation_claim_hash": self.claim["rotation_claim_hash"],
            "expected_dual_signed_rotation_hash": self.signed_document[
                "dual_signed_rotation_hash"
            ],
            "rotation_claim_build_kwargs": self.claim_kwargs,
        }
        kwargs.update(overrides)
        return continuity.evaluate_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.signed_document if signed_document is None else signed_document,
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            **kwargs,
        )

    def test_reproduces_single_signature_key_continuity_gap(self):
        self.assertEqual(self.adr0413_evidence["status"], "PASS")
        self.assertFalse(
            self.adr0413_evidence["facts"][
                "provider_key_control_continuity_verified"
            ]
        )

    def test_genesis_state_is_exact_and_preregistration_bound(self):
        self.assertTrue(
            continuity.verify_witness_ownership_provider_key_continuity_state_v1(
                self.previous_state,
                self.provider_preregistration_document,
                **self.previous_state_kwargs,
            )
        )
        self.assertEqual(self.previous_state["state"]["key_epoch"], 0)
        self.assertEqual(
            self.previous_state["state"]["active_public_key_spki_sha256"],
            self.old_key_hash,
        )

    def test_genesis_state_rejects_non_preregistered_active_key(self):
        with self.assertRaises(ValueError):
            continuity.build_witness_ownership_provider_key_continuity_state_v1(
                self.provider_preregistration_document,
                key_epoch=0,
                active_public_key_spki_sha256=self.new_key_hash,
                predecessor_key_state_hash=continuity.ZERO_HASH,
                last_rotation_event_hash=continuity.ZERO_HASH,
                provider_preregistration_kwargs=(
                    self.provider_preregistration_kwargs
                ),
            )

    def test_boolean_key_epoch_is_rejected(self):
        with self.assertRaises(ValueError):
            continuity.build_witness_ownership_provider_key_continuity_state_v1(
                self.provider_preregistration_document,
                key_epoch=True,
                active_public_key_spki_sha256=self.old_key_hash,
                predecessor_key_state_hash=continuity.ZERO_HASH,
                last_rotation_event_hash=continuity.ZERO_HASH,
                provider_preregistration_kwargs=(
                    self.provider_preregistration_kwargs
                ),
            )

    def test_rotation_claim_increments_epoch_and_binds_next_state(self):
        transition = self.claim["transition"]
        self.assertEqual(transition["previous_key_epoch"], 0)
        self.assertEqual(transition["next_key_epoch"], 1)
        self.assertEqual(
            transition["next_key_state_hash"],
            self.claim["next_key_state_candidate"]["key_state_hash"],
        )
        self.assertEqual(
            self.claim["next_key_state_candidate"]["state"][
                "predecessor_key_state_hash"
            ],
            self.previous_state["key_state_hash"],
        )

    def test_rotation_to_same_key_is_rejected(self):
        kwargs = dict(self.claim_kwargs)
        kwargs["next_public_key_spki_sha256"] = self.old_key_hash
        with self.assertRaises(ValueError):
            continuity.build_witness_ownership_provider_key_rotation_claim_v1(
                self.previous_state,
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_rotation_claim_is_deterministic_and_exact(self):
        rebuilt = continuity.build_witness_ownership_provider_key_rotation_claim_v1(
            self.previous_state,
            self.provider_preregistration_document,
            **self.claim_kwargs,
        )
        self.assertEqual(rebuilt, self.claim)
        self.assertTrue(
            continuity.verify_witness_ownership_provider_key_rotation_claim_v1(
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
                **self.claim_kwargs,
            )
        )

    def test_valid_dual_signature_passes_locally_but_admission_blocks(self):
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["admission_status"], "BLOCKED")
        self.assertTrue(
            evidence["facts"]["local_dual_key_rotation_signature_verified"]
        )
        for name in (
            "provider_key_control_continuity_verified",
            "provider_organization_identity_verified",
            "revocation_snapshot_source_verified",
            "trusted_rotation_clock_verified",
            "key_state_persistence_verified",
            "provider_implementation_update_verified",
            "external_provider_conformance_verified",
        ):
            self.assertFalse(evidence["facts"][name])
        self.assertTrue(
            all(
                value is False
                for key, value in evidence["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_wrong_old_key_is_rejected_by_builder(self):
        wrong_key = Ed25519PrivateKey.generate()
        wrong_spki = wrong_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaises(ValueError):
            continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                old_public_key_spki_base64=base64.b64encode(wrong_spki).decode(
                    "ascii"
                ),
                new_public_key_spki_base64=self.new_spki_base64,
                old_signature_base64=self.old_signature_base64,
                new_signature_base64=self.new_signature_base64,
                expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
                rotation_claim_build_kwargs=self.claim_kwargs,
            )

    def test_wrong_new_key_is_rejected_by_builder(self):
        wrong_key = Ed25519PrivateKey.generate()
        wrong_spki = wrong_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaises(ValueError):
            continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                old_public_key_spki_base64=self.old_spki_base64,
                new_public_key_spki_base64=base64.b64encode(wrong_spki).decode(
                    "ascii"
                ),
                old_signature_base64=self.old_signature_base64,
                new_signature_base64=self.new_signature_base64,
                expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
                rotation_claim_build_kwargs=self.claim_kwargs,
            )

    def test_invalid_old_signature_is_blocked(self):
        changed = bytearray(self.old_signature)
        changed[0] ^= 1
        changed_base64 = base64.b64encode(bytes(changed)).decode("ascii")
        changed_signed = continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            old_public_key_spki_base64=self.old_spki_base64,
            new_public_key_spki_base64=self.new_spki_base64,
            old_signature_base64=changed_base64,
            new_signature_base64=self.new_signature_base64,
            expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
            rotation_claim_build_kwargs=self.claim_kwargs,
        )
        evidence = self.evaluate(
            signed_document=changed_signed,
            old_signature_base64=changed_base64,
            expected_dual_signed_rotation_hash=changed_signed[
                "dual_signed_rotation_hash"
            ],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("OLD_KEY_SIGNATURE_INVALID", evidence["blockers"])

    def test_invalid_new_signature_is_blocked(self):
        changed = bytearray(self.new_signature)
        changed[0] ^= 1
        changed_base64 = base64.b64encode(bytes(changed)).decode("ascii")
        changed_signed = continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            old_public_key_spki_base64=self.old_spki_base64,
            new_public_key_spki_base64=self.new_spki_base64,
            old_signature_base64=self.old_signature_base64,
            new_signature_base64=changed_base64,
            expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
            rotation_claim_build_kwargs=self.claim_kwargs,
        )
        evidence = self.evaluate(
            signed_document=changed_signed,
            new_signature_base64=changed_base64,
            expected_dual_signed_rotation_hash=changed_signed[
                "dual_signed_rotation_hash"
            ],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("NEW_KEY_SIGNATURE_INVALID", evidence["blockers"])

    def test_cross_domain_signatures_are_blocked(self):
        wrong_message = bytes.fromhex(self.claim["rotation_claim_hash"])
        old_wrong = base64.b64encode(
            self.old_private_key.sign(wrong_message)
        ).decode("ascii")
        new_wrong = base64.b64encode(
            self.new_private_key.sign(wrong_message)
        ).decode("ascii")
        changed_signed = continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            old_public_key_spki_base64=self.old_spki_base64,
            new_public_key_spki_base64=self.new_spki_base64,
            old_signature_base64=old_wrong,
            new_signature_base64=new_wrong,
            expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
            rotation_claim_build_kwargs=self.claim_kwargs,
        )
        evidence = self.evaluate(
            signed_document=changed_signed,
            old_signature_base64=old_wrong,
            new_signature_base64=new_wrong,
            expected_dual_signed_rotation_hash=changed_signed[
                "dual_signed_rotation_hash"
            ],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_revocation_snapshot_drift_rejects_claim_verification(self):
        kwargs = dict(self.claim_kwargs)
        kwargs["revocation_snapshot_hash"] = _hash("different-snapshot")
        self.assertFalse(
            continuity.verify_witness_ownership_provider_key_rotation_claim_v1(
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
                **kwargs,
            )
        )

    def test_old_claim_cannot_replay_against_next_state(self):
        next_state = self.claim["next_key_state_candidate"]
        next_state_kwargs = {
            "key_epoch": 1,
            "active_public_key_spki_sha256": self.new_key_hash,
            "predecessor_key_state_hash": self.previous_state[
                "key_state_hash"
            ],
            "last_rotation_event_hash": self.claim["transition"][
                "rotation_event_hash"
            ],
            "provider_preregistration_kwargs": self.provider_preregistration_kwargs,
        }
        replay_kwargs = dict(self.claim_kwargs)
        replay_kwargs["expected_previous_key_state_hash"] = next_state[
            "key_state_hash"
        ]
        replay_kwargs["previous_key_state_build_kwargs"] = next_state_kwargs
        self.assertFalse(
            continuity.verify_witness_ownership_provider_key_rotation_claim_v1(
                self.claim,
                next_state,
                self.provider_preregistration_document,
                expected_rotation_claim_hash=self.claim["rotation_claim_hash"],
                **replay_kwargs,
            )
        )

    def test_exact_evidence_verifier_rejects_resealed_promotion(self):
        evidence = self.evaluate()
        evaluation_kwargs = {
            "old_public_key_spki_base64": self.old_spki_base64,
            "new_public_key_spki_base64": self.new_spki_base64,
            "old_signature_base64": self.old_signature_base64,
            "new_signature_base64": self.new_signature_base64,
            "expected_rotation_claim_hash": self.claim["rotation_claim_hash"],
            "expected_dual_signed_rotation_hash": self.signed_document[
                "dual_signed_rotation_hash"
            ],
            "rotation_claim_build_kwargs": self.claim_kwargs,
        }
        self.assertTrue(
            continuity.verify_dual_signed_witness_ownership_provider_key_rotation_evidence_v1(
                evidence,
                self.signed_document,
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_rotation_evidence_hash=evidence[
                    "rotation_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )
        promoted = deepcopy(evidence)
        promoted["admission_status"] = "READY"
        promoted.pop("rotation_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "rotation_evidence_hash"
        )
        self.assertFalse(
            continuity.verify_dual_signed_witness_ownership_provider_key_rotation_evidence_v1(
                promoted,
                self.signed_document,
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_rotation_evidence_hash=promoted[
                    "rotation_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )

    def test_evidence_is_deterministic_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        serialized = repr(first)
        self.assertNotIn(self.old_signature_base64, serialized)
        self.assertNotIn(self.new_signature_base64, serialized)
        self.assertNotIn(self.old_spki_base64, serialized)
        self.assertNotIn(self.new_spki_base64, serialized)

    def test_production_has_no_private_key_custom_parser_or_io(self):
        source = inspect.getsource(continuity)
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
