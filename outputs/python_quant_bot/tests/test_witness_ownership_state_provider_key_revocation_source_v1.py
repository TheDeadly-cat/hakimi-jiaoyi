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
from exchange_terminal.application import (
    witness_ownership_state_provider_key_revocation_source_v1 as revocation,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_witness_ownership_state_provider_key_continuity_v1 as adr0416_tests


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipProviderKeyRevocationSourceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = adr0416_tests.WitnessOwnershipProviderKeyContinuityV1Tests(
            methodName="test_valid_dual_signature_passes_locally_but_admission_blocks"
        )
        fixture.setUp()
        self.provider_preregistration_document = (
            fixture.provider_preregistration_document
        )
        self.provider_preregistration_kwargs = fixture.provider_preregistration_kwargs
        self.previous_state = fixture.previous_state
        self.previous_state_kwargs = fixture.previous_state_kwargs
        self.old_private_key = fixture.old_private_key
        self.old_spki_base64 = fixture.old_spki_base64
        self.old_key_hash = fixture.old_key_hash
        self.new_private_key = fixture.new_private_key
        self.new_spki_base64 = fixture.new_spki_base64
        self.new_key_hash = fixture.new_key_hash

        self.authority_private_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.authority_spki = [
            key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            for key in self.authority_private_keys
        ]
        self.authority_registrations = [
            {
                "authority_id": f"synthetic-revocation-authority-{index + 1}",
                "public_key_spki_sha256": sha256(spki).hexdigest(),
                "organization_claim_hash": _hash(
                    f"synthetic-revocation-organization-{index + 1}"
                ),
                "trust_domain": f"synthetic.revocation{index + 1}.local",
            }
            for index, spki in enumerate(self.authority_spki)
        ]
        self.authority_set_kwargs = {
            "authority_registrations": self.authority_registrations,
            "policy_id": "synthetic-key-revocation-policy",
            "policy_version": 1,
            "policy_hash": _hash("synthetic-key-revocation-policy-v1"),
            "provider_preregistration_kwargs": self.provider_preregistration_kwargs,
        }
        self.authority_set = revocation.build_witness_ownership_provider_key_revocation_authority_set_v1(
            self.provider_preregistration_document,
            **self.authority_set_kwargs,
        )
        rotation_nonce_hash = _hash("synthetic-rotation-nonce-1")
        self.snapshot_kwargs = {
            "previous_key_epoch": 0,
            "next_key_epoch": 1,
            "previous_public_key_spki_sha256": self.old_key_hash,
            "next_public_key_spki_sha256": self.new_key_hash,
            "rotation_nonce_hash": rotation_nonce_hash,
            "previous_revocation_snapshot_hash": revocation.ZERO_HASH,
            "revocation_sequence": 1,
            "revocation_reason_code": "SCHEDULED_ROTATION",
            "authority_set_build_kwargs": self.authority_set_kwargs,
        }
        self.snapshot = revocation.build_witness_ownership_provider_key_revocation_snapshot_v1(
            self.authority_set,
            self.provider_preregistration_document,
            **self.snapshot_kwargs,
        )
        self.claim_kwargs = {
            "expected_previous_key_state_hash": self.previous_state[
                "key_state_hash"
            ],
            "previous_key_state_build_kwargs": self.previous_state_kwargs,
            "next_public_key_spki_sha256": self.new_key_hash,
            "rotation_nonce_hash": rotation_nonce_hash,
            "revocation_snapshot_hash": self.snapshot[
                "revocation_snapshot_hash"
            ],
            "rotation_reason_code": "SCHEDULED_ROTATION",
            "provider_preregistration_kwargs": self.provider_preregistration_kwargs,
        }
        self.claim = continuity.build_witness_ownership_provider_key_rotation_claim_v1(
            self.previous_state,
            self.provider_preregistration_document,
            **self.claim_kwargs,
        )
        rotation_message_hash = continuity.build_witness_ownership_provider_key_rotation_signature_message_hash_v1(
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
        )
        self.old_signature_base64 = base64.b64encode(
            self.old_private_key.sign(bytes.fromhex(rotation_message_hash))
        ).decode("ascii")
        self.new_signature_base64 = base64.b64encode(
            self.new_private_key.sign(bytes.fromhex(rotation_message_hash))
        ).decode("ascii")
        self.signed_rotation = continuity.build_dual_signed_witness_ownership_provider_key_rotation_v1(
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
        self.rotation_evidence_verify_kwargs = {
            "old_public_key_spki_base64": self.old_spki_base64,
            "new_public_key_spki_base64": self.new_spki_base64,
            "old_signature_base64": self.old_signature_base64,
            "new_signature_base64": self.new_signature_base64,
            "expected_rotation_claim_hash": self.claim["rotation_claim_hash"],
            "expected_dual_signed_rotation_hash": self.signed_rotation[
                "dual_signed_rotation_hash"
            ],
            "rotation_claim_build_kwargs": self.claim_kwargs,
        }
        self.rotation_evidence = continuity.evaluate_dual_signed_witness_ownership_provider_key_rotation_v1(
            self.signed_rotation,
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            **self.rotation_evidence_verify_kwargs,
        )
        self.signed_statements = [self.build_signed_statement(i) for i in range(3)]

    def build_signed_statement(self, index: int, *, signature_bytes=None):
        message_hash = revocation.build_witness_ownership_provider_key_revocation_signature_message_hash_v1(
            self.snapshot,
            self.authority_set,
        )
        signature = (
            self.authority_private_keys[index].sign(bytes.fromhex(message_hash))
            if signature_bytes is None
            else signature_bytes
        )
        return revocation.build_signed_witness_ownership_provider_key_revocation_authority_statement_v1(
            self.snapshot,
            self.authority_set,
            self.provider_preregistration_document,
            authority_id=self.authority_registrations[index]["authority_id"],
            public_key_spki_base64=base64.b64encode(
                self.authority_spki[index]
            ).decode("ascii"),
            signature_base64=base64.b64encode(signature).decode("ascii"),
            expected_revocation_snapshot_hash=self.snapshot[
                "revocation_snapshot_hash"
            ],
            snapshot_build_kwargs=self.snapshot_kwargs,
        )

    def evaluate(self, rows=None, **overrides):
        kwargs = {
            "authority_set_build_kwargs": self.authority_set_kwargs,
            "snapshot_build_kwargs": self.snapshot_kwargs,
            "expected_rotation_evidence_hash": self.rotation_evidence[
                "rotation_evidence_hash"
            ],
            "rotation_evidence_verify_kwargs": (
                self.rotation_evidence_verify_kwargs
            ),
        }
        kwargs.update(overrides)
        return revocation.evaluate_witness_ownership_provider_key_revocation_authority_quorum_v1(
            self.signed_statements[:2] if rows is None else rows,
            self.snapshot,
            self.authority_set,
            self.rotation_evidence,
            self.signed_rotation,
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            **kwargs,
        )

    def test_reproduces_unverified_revocation_hash_gap(self):
        self.assertEqual(self.rotation_evidence["status"], "PASS")
        self.assertFalse(
            self.rotation_evidence["facts"][
                "revocation_snapshot_source_verified"
            ]
        )

    def test_authority_set_is_exact_structurally_separated_and_locked(self):
        self.assertTrue(
            revocation.verify_witness_ownership_provider_key_revocation_authority_set_v1(
                self.authority_set,
                self.provider_preregistration_document,
                **self.authority_set_kwargs,
            )
        )
        self.assertEqual(len(self.authority_set["authorities"]), 3)
        self.assertEqual(
            self.authority_set["policy"]["required_signature_quorum"], 2
        )

    def test_duplicate_authority_id_is_rejected(self):
        kwargs = deepcopy(self.authority_set_kwargs)
        kwargs["authority_registrations"][1]["authority_id"] = kwargs[
            "authority_registrations"
        ][0]["authority_id"]
        with self.assertRaises(ValueError):
            revocation.build_witness_ownership_provider_key_revocation_authority_set_v1(
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_provider_key_cannot_be_revocation_authority_key(self):
        kwargs = deepcopy(self.authority_set_kwargs)
        kwargs["authority_registrations"][0]["public_key_spki_sha256"] = (
            self.old_key_hash
        )
        with self.assertRaises(ValueError):
            revocation.build_witness_ownership_provider_key_revocation_authority_set_v1(
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_snapshot_is_exact_monotonic_and_claim_bound(self):
        self.assertTrue(
            revocation.verify_witness_ownership_provider_key_revocation_snapshot_v1(
                self.snapshot,
                self.authority_set,
                self.provider_preregistration_document,
                **self.snapshot_kwargs,
            )
        )
        self.assertEqual(self.snapshot["snapshot"]["revocation_sequence"], 1)
        self.assertEqual(
            self.snapshot["revocation_snapshot_hash"],
            self.claim["transition"]["revocation_snapshot_hash"],
        )

    def test_boolean_revocation_sequence_is_rejected(self):
        kwargs = dict(self.snapshot_kwargs)
        kwargs["revocation_sequence"] = True
        with self.assertRaises(ValueError):
            revocation.build_witness_ownership_provider_key_revocation_snapshot_v1(
                self.authority_set,
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_snapshot_epoch_gap_is_rejected(self):
        kwargs = dict(self.snapshot_kwargs)
        kwargs["next_key_epoch"] = 2
        with self.assertRaises(ValueError):
            revocation.build_witness_ownership_provider_key_revocation_snapshot_v1(
                self.authority_set,
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_epoch_zero_snapshot_must_revoke_preregistered_key(self):
        kwargs = dict(self.snapshot_kwargs)
        kwargs["previous_public_key_spki_sha256"] = _hash("different-old-key")
        with self.assertRaises(ValueError):
            revocation.build_witness_ownership_provider_key_revocation_snapshot_v1(
                self.authority_set,
                self.provider_preregistration_document,
                **kwargs,
            )

    def test_signed_authority_statement_binds_snapshot_and_key(self):
        statement = self.signed_statements[0]
        self.assertEqual(
            statement["revocation_snapshot_hash"],
            self.snapshot["revocation_snapshot_hash"],
        )
        self.assertEqual(
            statement["public_key_spki_sha256"],
            self.authority_registrations[0]["public_key_spki_sha256"],
        )

    def test_two_of_three_local_quorum_passes_but_source_truth_blocks(self):
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["admission_status"], "BLOCKED")
        self.assertTrue(
            evidence["facts"][
                "local_revocation_authority_signature_quorum_verified"
            ]
        )
        for name in (
            "revocation_authority_organization_identities_verified",
            "revocation_authority_independence_source_truth_verified",
            "revocation_snapshot_source_verified",
            "revocation_snapshot_publication_verified",
            "revocation_snapshot_persistence_verified",
            "trusted_revocation_clock_verified",
            "provider_key_control_continuity_verified",
        ):
            self.assertFalse(evidence["facts"][name])

    def test_one_statement_does_not_form_quorum(self):
        evidence = self.evaluate(rows=[self.signed_statements[0]])
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "REVOCATION_STATEMENT_COUNT_NOT_TWO_OR_THREE",
            evidence["blockers"],
        )

    def test_duplicate_authority_statements_do_not_form_quorum(self):
        evidence = self.evaluate(
            rows=[self.signed_statements[0], self.signed_statements[0]]
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("DUPLICATE_REVOCATION_AUTHORITY_ID", evidence["blockers"])

    def test_wrong_authority_key_is_rejected_by_builder(self):
        wrong_key = Ed25519PrivateKey.generate()
        wrong_spki = wrong_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaises(ValueError):
            revocation.build_signed_witness_ownership_provider_key_revocation_authority_statement_v1(
                self.snapshot,
                self.authority_set,
                self.provider_preregistration_document,
                authority_id=self.authority_registrations[0]["authority_id"],
                public_key_spki_base64=base64.b64encode(wrong_spki).decode(
                    "ascii"
                ),
                signature_base64=self.signed_statements[0]["signature_base64"],
                expected_revocation_snapshot_hash=self.snapshot[
                    "revocation_snapshot_hash"
                ],
                snapshot_build_kwargs=self.snapshot_kwargs,
            )

    def test_invalid_authority_signature_is_blocked(self):
        signature = bytearray(
            base64.b64decode(self.signed_statements[0]["signature_base64"])
        )
        signature[0] ^= 1
        changed = deepcopy(self.signed_statements[0])
        changed["signature_base64"] = base64.b64encode(bytes(signature)).decode(
            "ascii"
        )
        changed.pop("signed_statement_hash")
        changed = seal_strict_canonical_document(changed, "signed_statement_hash")
        evidence = self.evaluate(rows=[changed, self.signed_statements[1]])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_snapshot_rotation_binding_drift_is_blocked(self):
        changed = deepcopy(self.snapshot)
        changed["snapshot"]["rotation_nonce_hash"] = _hash("changed-nonce")
        changed.pop("revocation_snapshot_hash")
        changed = seal_strict_canonical_document(
            changed, "revocation_snapshot_hash"
        )
        evidence = revocation.evaluate_witness_ownership_provider_key_revocation_authority_quorum_v1(
            self.signed_statements[:2],
            changed,
            self.authority_set,
            self.rotation_evidence,
            self.signed_rotation,
            self.claim,
            self.previous_state,
            self.provider_preregistration_document,
            authority_set_build_kwargs=self.authority_set_kwargs,
            snapshot_build_kwargs=self.snapshot_kwargs,
            expected_rotation_evidence_hash=self.rotation_evidence[
                "rotation_evidence_hash"
            ],
            rotation_evidence_verify_kwargs=(
                self.rotation_evidence_verify_kwargs
            ),
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_exact_quorum_verifier_rejects_resealed_promotion(self):
        evidence = self.evaluate()
        evaluation_kwargs = {
            "authority_set_build_kwargs": self.authority_set_kwargs,
            "snapshot_build_kwargs": self.snapshot_kwargs,
            "expected_rotation_evidence_hash": self.rotation_evidence[
                "rotation_evidence_hash"
            ],
            "rotation_evidence_verify_kwargs": (
                self.rotation_evidence_verify_kwargs
            ),
        }
        self.assertTrue(
            revocation.verify_witness_ownership_provider_key_revocation_authority_quorum_v1(
                evidence,
                self.signed_statements[:2],
                self.snapshot,
                self.authority_set,
                self.rotation_evidence,
                self.signed_rotation,
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_quorum_evidence_hash=evidence["quorum_evidence_hash"],
                **evaluation_kwargs,
            )
        )
        promoted = deepcopy(evidence)
        promoted["admission_status"] = "READY"
        promoted.pop("quorum_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "quorum_evidence_hash"
        )
        self.assertFalse(
            revocation.verify_witness_ownership_provider_key_revocation_authority_quorum_v1(
                promoted,
                self.signed_statements[:2],
                self.snapshot,
                self.authority_set,
                self.rotation_evidence,
                self.signed_rotation,
                self.claim,
                self.previous_state,
                self.provider_preregistration_document,
                expected_quorum_evidence_hash=promoted[
                    "quorum_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )

    def test_output_is_deterministic_order_independent_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate(
            rows=[self.signed_statements[1], self.signed_statements[0]]
        )
        self.assertEqual(first, second)
        serialized = repr(first)
        for statement in self.signed_statements[:2]:
            self.assertNotIn(statement["signature_base64"], serialized)
            self.assertNotIn(statement["public_key_spki_base64"], serialized)

    def test_production_has_no_private_key_custom_parser_provider_call_or_io(self):
        source = inspect.getsource(revocation)
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
            ".compare_consume_and_advance(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
