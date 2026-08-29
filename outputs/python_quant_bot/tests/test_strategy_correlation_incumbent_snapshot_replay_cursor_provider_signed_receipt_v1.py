from __future__ import annotations

import base64
from dataclasses import fields
from hashlib import sha256
import inspect
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as signed_receipt,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as provider_port,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as provider_tests,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1
    as registration_tests,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _clone(value, **changes):
    cloned = object.__new__(type(value))
    for item in fields(value):
        object.__setattr__(
            cloned,
            item.name,
            changes.get(item.name, getattr(value, item.name)),
        )
    return cloned


class ReplayCursorProviderSignedReceiptV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        fixture_class = (
            registration_tests.ReplayCursorProviderSignedRegistrationV1Tests
        )
        fixture_class.setUpClass()
        cls.private_key = fixture_class.private_key
        cls.preregistration_document = fixture_class.preregistration
        cls.registration_claim_document = fixture_class.claim
        cls.signed_registration_document = fixture_class.signed
        cls.registration_evidence_document = fixture_class.evidence
        cls.preregistration_kwargs = dict(fixture_class.preregistration_kwargs)
        cls.registration_verification_kwargs = {
            **cls.preregistration_kwargs,
            "public_key_spki_base64": fixture_class.public_key_base64,
            "signature_base64": fixture_class.signature_base64,
            "expected_claim_hash": cls.registration_claim_document[
                "claim_hash"
            ],
            "expected_signed_registration_hash": (
                cls.signed_registration_document[
                    "signed_registration_hash"
                ]
            ),
            "challenge_hash": fixture_class.challenge_hash,
            "registration_nonce_hash": fixture_class.registration_nonce_hash,
        }
        cls.registration_evidence_hash = cls.registration_evidence_document[
            "verification_evidence_hash"
        ]
        provider_fixture = (
            provider_tests.IncumbentSnapshotReplayCursorProviderV1Tests
        )
        provider_fixture.setUpClass()
        cls.provider_command = provider_fixture.command
        cls._fixture_setup_complete_v1 = True

    def setUp(self) -> None:
        self.registry_id = self.preregistration_document["identity"][
            "registry_id"
        ]
        self.command = self.provider_command
        self.base_cursor_hash = self.command.base_cursor.cursor_hash
        self.proposed_cursor_hash = self.command.proposed_cursor.cursor_hash
        self.command_hash = self.command.command_hash
        self.intent_hash = self.command.intent_hash
        self.result = provider_port.ReplayCursorCompareAndAdvanceResultV1(
            outcome=provider_port.ReplayCursorProviderOutcomeV1.ADVANCED,
            command_hash=self.command_hash,
            intent_hash=self.intent_hash,
            registry_id=self.registry_id,
            registry_revision=7,
            observed_cursor_hash=self.base_cursor_hash,
            returned_cursor_hash=self.proposed_cursor_hash,
            receipt_document={
                "opaque_provider_receipt": "synthetic-only-do-not-project",
                "provider_receipt_hash": _hash("adr0478-provider-receipt"),
            },
        )
        self.claim = self._build_claim()
        self.signature = self.private_key.sign(
            bytes.fromhex(self.claim["receipt_claim_hash"])
        )
        self.signature_base64 = base64.b64encode(self.signature).decode(
            "ascii"
        )
        self.public_key_spki_base64 = (
            self.registration_verification_kwargs["public_key_spki_base64"]
        )
        self.signed_document = self._build_signed()

    def _build_claim(self, *, command=None, result=None):
        return signed_receipt.build_replay_cursor_provider_receipt_claim_v1(
            self.command if command is None else command,
            self.result if result is None else result,
            self.registration_evidence_document,
            self.signed_registration_document,
            self.registration_claim_document,
            self.preregistration_document,
            expected_registration_evidence_hash=(
                self.registration_evidence_hash
            ),
            registration_verification_kwargs=(
                self.registration_verification_kwargs
            ),
        )

    def _build_signed(
        self,
        *,
        claim=None,
        public_key_spki_base64=None,
        signature_base64=None,
    ):
        claim = self.claim if claim is None else claim
        return signed_receipt.build_signed_replay_cursor_provider_receipt_v1(
            claim,
            self.command,
            self.result,
            self.registration_evidence_document,
            self.signed_registration_document,
            self.registration_claim_document,
            self.preregistration_document,
            public_key_spki_base64=(
                self.public_key_spki_base64
                if public_key_spki_base64 is None
                else public_key_spki_base64
            ),
            signature_base64=(
                self.signature_base64
                if signature_base64 is None
                else signature_base64
            ),
            expected_receipt_claim_hash=claim["receipt_claim_hash"],
            expected_registration_evidence_hash=(
                self.registration_evidence_hash
            ),
            registration_verification_kwargs=(
                self.registration_verification_kwargs
            ),
        )

    def _evaluate(self, *, signed_document=None, claim=None, **overrides):
        claim = self.claim if claim is None else claim
        kwargs = {
            "public_key_spki_base64": self.public_key_spki_base64,
            "signature_base64": self.signature_base64,
            "expected_signed_receipt_hash": self.signed_document[
                "signed_receipt_hash"
            ],
            "expected_receipt_claim_hash": claim["receipt_claim_hash"],
            "expected_registration_evidence_hash": (
                self.registration_evidence_hash
            ),
            "registration_verification_kwargs": (
                self.registration_verification_kwargs
            ),
        }
        kwargs.update(overrides)
        return signed_receipt.evaluate_signed_replay_cursor_provider_receipt_v1(
            self.signed_document
            if signed_document is None
            else signed_document,
            claim,
            self.command,
            self.result,
            self.registration_evidence_document,
            self.signed_registration_document,
            self.registration_claim_document,
            self.preregistration_document,
            **kwargs,
        )

    def test_unsigned_structural_advanced_result_gap_is_reproduced(self):
        self.assertEqual(self.result.outcome.value, "ADVANCED")
        self.assertNotIn("signature_base64", repr(self.result))
        self.assertNotIn("public_key_spki", repr(self.result))

    def test_claim_binds_exact_command_result_and_registration(self):
        self.assertEqual(self.claim["command_hash"], self.command_hash)
        self.assertEqual(self.claim["intent_hash"], self.intent_hash)
        self.assertEqual(self.claim["registry_id"], self.registry_id)
        self.assertEqual(
            self.claim["registration_evidence_hash"],
            self.registration_evidence_hash,
        )

    def test_valid_preregistered_key_receipt_is_local_only(self):
        evidence = self._evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["admission_status"], "BLOCKED")
        self.assertTrue(
            evidence["facts"]["provider_key_possession_observed_local_only"]
        )
        for name in (
            "provider_identity_verified",
            "provider_implementation_verified",
            "provider_registered",
            "actual_provider_invocation_verified",
            "external_atomic_compare_and_advance_verified",
            "durable_commit_verified",
            "linearizable_read_after_write_verified",
            "rollback_resistance_verified",
            "consume_once_semantics_verified",
            "replay_cursor_persistence_verified",
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
            other_private.sign(bytes.fromhex(self.claim["receipt_claim_hash"]))
        ).decode("ascii")
        other_signed = self._build_signed(
            public_key_spki_base64=other_spki_base64,
            signature_base64=other_signature_base64,
        )
        evidence = self._evaluate(
            signed_document=other_signed,
            public_key_spki_base64=other_spki_base64,
            signature_base64=other_signature_base64,
            expected_signed_receipt_hash=other_signed["signed_receipt_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "PREREGISTERED_PUBLIC_KEY_HASH_MISMATCH", evidence["blockers"]
        )

    def test_modified_signature_is_blocked(self):
        changed = bytearray(self.signature)
        changed[0] ^= 1
        changed_base64 = base64.b64encode(bytes(changed)).decode("ascii")
        changed_signed = self._build_signed(signature_base64=changed_base64)
        evidence = self._evaluate(
            signed_document=changed_signed,
            signature_base64=changed_base64,
            expected_signed_receipt_hash=changed_signed[
                "signed_receipt_hash"
            ],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "ED25519_PROVIDER_RECEIPT_SIGNATURE_INVALID",
            evidence["blockers"],
        )

    def test_command_or_registry_drift_is_rejected(self):
        drifted_command = _clone(
            self.command, command_hash=_hash("adr0478-drifted-command")
        )
        with self.assertRaises(ValueError):
            self._build_claim(command=drifted_command)
        drifted_result = _clone(self.result, registry_id="wrong-registry")
        with self.assertRaises(ValueError):
            self._build_claim(result=drifted_result)

    def test_raw_provider_receipt_is_hashed_and_not_projected(self):
        serialized = repr(self.claim)
        self.assertNotIn("synthetic-only-do-not-project", serialized)
        result_snapshot = self.claim["provider_result_snapshot"]
        receipt_values = [
            value
            for key, value in result_snapshot.items()
            if "receipt" in key
        ]
        self.assertEqual(len(receipt_values), 1)
        self.assertRegex(receipt_values[0]["content_sha256"], r"^[0-9a-f]{64}$")

    def test_resealed_and_resigned_permission_promotion_is_blocked(self):
        promoted = dict(self.claim)
        promoted["status"] = "READY"
        promoted.pop("receipt_claim_hash")
        promoted = seal_strict_canonical_document(
            promoted, "receipt_claim_hash"
        )
        promoted_signature = base64.b64encode(
            self.private_key.sign(
                bytes.fromhex(promoted["receipt_claim_hash"])
            )
        ).decode("ascii")
        forged = dict(self.signed_document)
        forged["receipt_claim_hash"] = promoted["receipt_claim_hash"]
        forged["signature_message_hash"] = promoted["receipt_claim_hash"]
        forged["signature_base64"] = promoted_signature
        forged.pop("signed_receipt_hash")
        forged = seal_strict_canonical_document(forged, "signed_receipt_hash")
        evidence = self._evaluate(
            signed_document=forged,
            claim=promoted,
            signature_base64=promoted_signature,
            expected_signed_receipt_hash=forged["signed_receipt_hash"],
            expected_receipt_claim_hash=promoted["receipt_claim_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_exact_evidence_verifier_rejects_resealed_promotion(self):
        evidence = self._evaluate()
        kwargs = {
            "public_key_spki_base64": self.public_key_spki_base64,
            "signature_base64": self.signature_base64,
            "expected_signed_receipt_hash": self.signed_document[
                "signed_receipt_hash"
            ],
            "expected_receipt_claim_hash": self.claim[
                "receipt_claim_hash"
            ],
            "expected_registration_evidence_hash": (
                self.registration_evidence_hash
            ),
            "registration_verification_kwargs": (
                self.registration_verification_kwargs
            ),
        }
        self.assertTrue(
            signed_receipt.verify_signed_replay_cursor_provider_receipt_evidence_v1(
                evidence,
                self.signed_document,
                self.claim,
                self.command,
                self.result,
                self.registration_evidence_document,
                self.signed_registration_document,
                self.registration_claim_document,
                self.preregistration_document,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                **kwargs,
            )
        )
        promoted = dict(evidence)
        promoted["admission_status"] = "READY"
        promoted.pop("verification_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "verification_evidence_hash"
        )
        self.assertFalse(
            signed_receipt.verify_signed_replay_cursor_provider_receipt_evidence_v1(
                promoted,
                self.signed_document,
                self.claim,
                self.command,
                self.result,
                self.registration_evidence_document,
                self.signed_registration_document,
                self.registration_claim_document,
                self.preregistration_document,
                expected_verification_evidence_hash=promoted[
                    "verification_evidence_hash"
                ],
                **kwargs,
            )
        )

    def test_evidence_is_deterministic_and_redacted(self):
        first = self._evaluate()
        second = self._evaluate()
        self.assertEqual(first, second)
        serialized = repr(first)
        self.assertNotIn(self.signature_base64, serialized)
        self.assertNotIn(self.public_key_spki_base64, serialized)
        self.assertNotIn("synthetic-only-do-not-project", serialized)

    def test_noncanonical_key_and_short_signature_are_rejected(self):
        with self.assertRaises(ValueError):
            self._build_signed(
                public_key_spki_base64=self.public_key_spki_base64.rstrip("=")
            )
        short_signature = base64.b64encode(b"x" * 63).decode("ascii")
        with self.assertRaises(ValueError):
            self._build_signed(signature_base64=short_signature)

    def test_production_has_no_private_key_io_network_or_runtime_access(self):
        source = inspect.getsource(signed_receipt)
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
