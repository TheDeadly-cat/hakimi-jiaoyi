from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1
    as preregistration,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1
    as registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class ReplayCursorProviderSignedRegistrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key_der = _spki(cls.private_key)
        cls.public_key_base64 = _b64(cls.public_key_der)
        cls.preregistration_kwargs = {
            "registry_id": "synthetic.signed-replay-cursor.registry.v1",
            "operator_identity_claim": "synthetic-signed-provider-operator",
            "public_key_spki_sha256": sha256(cls.public_key_der).hexdigest(),
            "trust_domain": "synthetic.signed-replay-cursor.provider.test",
            "provider_implementation_claim_sha256": sha256(
                b"synthetic-signed-provider-implementation"
            ).hexdigest(),
        }
        cls.preregistration = preregistration.build_replay_cursor_provider_preregistration_v1(
            **cls.preregistration_kwargs
        )
        cls.challenge_hash = sha256(b"synthetic-registration-challenge").hexdigest()
        cls.registration_nonce_hash = sha256(
            b"synthetic-registration-nonce"
        ).hexdigest()
        cls.claim = registration.build_replay_cursor_provider_registration_claim_v1(
            cls.preregistration,
            challenge_hash=cls.challenge_hash,
            registration_nonce_hash=cls.registration_nonce_hash,
            **cls.preregistration_kwargs,
        )
        cls.signature_base64 = _b64(
            cls.private_key.sign(bytes.fromhex(cls.claim["claim_hash"]))
        )
        cls.signed = registration.build_signed_replay_cursor_provider_registration_v1(
            cls.claim,
            cls.preregistration,
            public_key_spki_base64=cls.public_key_base64,
            signature_base64=cls.signature_base64,
            expected_claim_hash=cls.claim["claim_hash"],
            challenge_hash=cls.challenge_hash,
            registration_nonce_hash=cls.registration_nonce_hash,
            **cls.preregistration_kwargs,
        )
        cls.evidence = registration.evaluate_signed_replay_cursor_provider_registration_v1(
            cls.signed,
            cls.claim,
            cls.preregistration,
            public_key_spki_base64=cls.public_key_base64,
            signature_base64=cls.signature_base64,
            expected_claim_hash=cls.claim["claim_hash"],
            expected_signed_registration_hash=cls.signed[
                "signed_registration_hash"
            ],
            challenge_hash=cls.challenge_hash,
            registration_nonce_hash=cls.registration_nonce_hash,
            **cls.preregistration_kwargs,
        )

    def evaluate(self, signed, *, claim=None, key_base64=None, signature=None):
        source_claim = self.claim if claim is None else claim
        return registration.evaluate_signed_replay_cursor_provider_registration_v1(
            signed,
            source_claim,
            self.preregistration,
            public_key_spki_base64=(
                self.public_key_base64 if key_base64 is None else key_base64
            ),
            signature_base64=(
                self.signature_base64 if signature is None else signature
            ),
            expected_claim_hash=source_claim["claim_hash"],
            expected_signed_registration_hash=signed["signed_registration_hash"],
            challenge_hash=self.challenge_hash,
            registration_nonce_hash=self.registration_nonce_hash,
            **self.preregistration_kwargs,
        )

    def test_claim_is_exact_deterministic_and_operationally_blocked(self) -> None:
        rebuilt = registration.build_replay_cursor_provider_registration_claim_v1(
            self.preregistration,
            challenge_hash=self.challenge_hash,
            registration_nonce_hash=self.registration_nonce_hash,
            **self.preregistration_kwargs,
        )
        self.assertEqual(self.claim, rebuilt)
        self.assertEqual(self.claim["status"], "BLOCKED")
        self.assertFalse(self.claim["facts"]["provider_registered"])
        self.assertTrue(
            registration.verify_replay_cursor_provider_registration_claim_v1(
                self.claim,
                self.preregistration,
                expected_claim_hash=self.claim["claim_hash"],
                challenge_hash=self.challenge_hash,
                registration_nonce_hash=self.registration_nonce_hash,
                **self.preregistration_kwargs,
            )
        )

    def test_valid_signature_is_observed_without_provider_registration(self) -> None:
        facts = self.evidence["facts"]
        self.assertEqual(self.evidence["status"], "PASS")
        self.assertEqual(
            self.evidence["registration_status"],
            "SIGNED_REGISTRATION_CANDIDATE_BLOCKED",
        )
        self.assertTrue(facts["cryptographic_signature_verified"])
        self.assertTrue(facts["preregistered_key_signature_verified"])
        self.assertTrue(facts["provider_key_possession_observed"])
        self.assertFalse(facts["provider_identity_verified"])
        self.assertFalse(facts["provider_registered"])
        self.assertFalse(facts["challenge_freshness_verified"])
        self.assertFalse(facts["registration_replay_consumed"])
        self.assertTrue(all(value is False for value in self.evidence["authority"].values()))

    def test_exact_evidence_verifier_rejects_mutation(self) -> None:
        kwargs = {
            "public_key_spki_base64": self.public_key_base64,
            "signature_base64": self.signature_base64,
            "expected_claim_hash": self.claim["claim_hash"],
            "expected_signed_registration_hash": self.signed[
                "signed_registration_hash"
            ],
            "challenge_hash": self.challenge_hash,
            "registration_nonce_hash": self.registration_nonce_hash,
            **self.preregistration_kwargs,
        }
        self.assertTrue(
            registration.verify_signed_replay_cursor_provider_registration_evidence_v1(
                self.evidence,
                self.signed,
                self.claim,
                self.preregistration,
                expected_verification_evidence_hash=self.evidence[
                    "verification_evidence_hash"
                ],
                **kwargs,
            )
        )
        attacked = deepcopy(self.evidence)
        attacked["facts"]["provider_registered"] = True
        self.assertFalse(
            registration.verify_signed_replay_cursor_provider_registration_evidence_v1(
                attacked,
                self.signed,
                self.claim,
                self.preregistration,
                expected_verification_evidence_hash=self.evidence[
                    "verification_evidence_hash"
                ],
                **kwargs,
            )
        )

    def test_wrong_key_can_verify_its_signature_but_not_preregistered_binding(self) -> None:
        wrong_private = Ed25519PrivateKey.generate()
        wrong_der = _spki(wrong_private)
        wrong_key = _b64(wrong_der)
        wrong_signature = _b64(
            wrong_private.sign(bytes.fromhex(self.claim["claim_hash"]))
        )
        signed = registration.build_signed_replay_cursor_provider_registration_v1(
            self.claim,
            self.preregistration,
            public_key_spki_base64=wrong_key,
            signature_base64=wrong_signature,
            expected_claim_hash=self.claim["claim_hash"],
            challenge_hash=self.challenge_hash,
            registration_nonce_hash=self.registration_nonce_hash,
            **self.preregistration_kwargs,
        )
        evidence = self.evaluate(
            signed,
            key_base64=wrong_key,
            signature=wrong_signature,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertTrue(evidence["facts"]["cryptographic_signature_verified"])
        self.assertFalse(evidence["facts"]["key_hash_matches_preregistration"])
        self.assertFalse(evidence["facts"]["preregistered_key_signature_verified"])

    def test_tampered_signature_is_rejected(self) -> None:
        signature = bytearray(base64.b64decode(self.signature_base64))
        signature[0] ^= 1
        tampered_signature = _b64(bytes(signature))
        signed = registration.build_signed_replay_cursor_provider_registration_v1(
            self.claim,
            self.preregistration,
            public_key_spki_base64=self.public_key_base64,
            signature_base64=tampered_signature,
            expected_claim_hash=self.claim["claim_hash"],
            challenge_hash=self.challenge_hash,
            registration_nonce_hash=self.registration_nonce_hash,
            **self.preregistration_kwargs,
        )
        evidence = self.evaluate(signed, signature=tampered_signature)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertFalse(evidence["facts"]["cryptographic_signature_verified"])

    def test_resealed_and_resigned_semantic_promotion_is_rejected(self) -> None:
        body = deepcopy(self.claim)
        body.pop("claim_hash")
        body["facts"]["provider_identity_verified"] = True
        forged_claim = seal_strict_canonical_document(body, "claim_hash")
        forged_signature = _b64(
            self.private_key.sign(bytes.fromhex(forged_claim["claim_hash"]))
        )
        forged_signed = seal_strict_canonical_document(
            {
                "authority": deepcopy(self.signed["authority"]),
                "claim_hash": forged_claim["claim_hash"],
                "preregistration_hash": self.preregistration[
                    "preregistration_hash"
                ],
                "public_key_spki_base64": self.public_key_base64,
                "public_key_spki_sha256": sha256(self.public_key_der).hexdigest(),
                "schema_version": registration.SIGNED_REGISTRATION_SCHEMA_VERSION,
                "signature_algorithm": "ED25519",
                "signature_base64": forged_signature,
                "signature_domain": registration.SIGNATURE_DOMAIN,
                "signature_message_format": "RAW_SHA256_DIGEST_BYTES_V1",
                "static_fingerprint": registration.STATIC_FINGERPRINT,
                "status": "SIGNED_CANDIDATE",
            },
            "signed_registration_hash",
        )
        evidence = self.evaluate(
            forged_signed,
            claim=forged_claim,
            signature=forged_signature,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertFalse(evidence["facts"]["claim_document_exact"])
        self.assertFalse(evidence["facts"]["provider_identity_verified"])

    def test_signed_document_tamper_and_schema_alias_are_rejected(self) -> None:
        for field, value in (
            ("status", "REGISTERED"),
            ("schema_version", f"{registration.SIGNED_REGISTRATION_SCHEMA_VERSION}.0"),
        ):
            attacked = deepcopy(self.signed)
            attacked[field] = value
            evidence = self.evaluate(attacked)
            self.assertEqual(evidence["status"], "BLOCK")
            self.assertFalse(evidence["facts"]["signed_registration_document_exact"])

    def test_evidence_redacts_raw_public_key_and_signature(self) -> None:
        serialized = repr(self.evidence)
        self.assertNotIn(self.public_key_base64, serialized)
        self.assertNotIn(self.signature_base64, serialized)
        self.assertTrue(self.evidence["facts"]["raw_public_key_redacted"])
        self.assertTrue(self.evidence["facts"]["raw_signature_redacted"])

    def test_challenge_nonce_binding_and_replay_nonclaim_are_deterministic(self) -> None:
        changed = registration.build_replay_cursor_provider_registration_claim_v1(
            self.preregistration,
            challenge_hash="0" * 64,
            registration_nonce_hash=self.registration_nonce_hash,
            **self.preregistration_kwargs,
        )
        self.assertNotEqual(changed["claim_hash"], self.claim["claim_hash"])
        replay = self.evaluate(self.signed)
        self.assertEqual(replay, self.evidence)
        self.assertFalse(replay["facts"]["registration_replay_consumed"])
        self.assertFalse(replay["facts"]["challenge_source_authority_verified"])

    def test_preregistration_or_implementation_drift_cannot_build_claim(self) -> None:
        drifted = dict(self.preregistration_kwargs)
        drifted["provider_implementation_claim_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            registration.build_replay_cursor_provider_registration_claim_v1(
                self.preregistration,
                challenge_hash=self.challenge_hash,
                registration_nonce_hash=self.registration_nonce_hash,
                **drifted,
            )

    def test_invalid_base64_non_ed25519_and_short_signature_are_rejected(self) -> None:
        invalid = (
            ("not-base64", self.signature_base64),
            (self.public_key_base64, _b64(b"short")),
        )
        for key, signature in invalid:
            with self.subTest(key=key[:8], signature=signature[:8]):
                with self.assertRaises(ValueError):
                    registration.build_signed_replay_cursor_provider_registration_v1(
                        self.claim,
                        self.preregistration,
                        public_key_spki_base64=key,
                        signature_base64=signature,
                        expected_claim_hash=self.claim["claim_hash"],
                        challenge_hash=self.challenge_hash,
                        registration_nonce_hash=self.registration_nonce_hash,
                        **self.preregistration_kwargs,
                    )

    def test_production_contract_has_no_private_key_io_or_runtime_operations(self) -> None:
        source = Path(registration.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            "open(",
            "subprocess",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
