from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    challenge_consumption_provider_genesis_replay_reservation_preregistration_v1 as preregistration,
)
from exchange_terminal.application import (
    challenge_consumption_provider_genesis_replay_reservation_signed_registration_v1 as registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class GenesisReplayReservationProviderSignedRegistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.private = Ed25519PrivateKey.generate()
        self.spki = _spki(self.private)
        self.preregistration_kwargs = {
            "registry_id": "synthetic.genesis.replay.registry.v1",
            "operator_identity_claim": "synthetic.genesis.replay.operator.v1",
            "public_key_spki_sha256": sha256(self.spki).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "provider_implementation_claim_sha256": sha256(
                b"synthetic-genesis-replay-reservation-provider"
            ).hexdigest(),
        }
        self.prereg = preregistration.build_genesis_replay_reservation_provider_preregistration_v1(
            **self.preregistration_kwargs
        )
        self.challenge_hash = sha256(b"synthetic-genesis-replay-provider-registration-challenge").hexdigest()
        self.nonce_hash = sha256(b"synthetic-genesis-replay-provider-registration-nonce").hexdigest()
        self.claim_kwargs = {
            "challenge_hash": self.challenge_hash,
            "registration_nonce_hash": self.nonce_hash,
            "preregistration_kwargs": self.preregistration_kwargs,
        }
        self.claim = registration.build_genesis_replay_reservation_provider_registration_claim_v1(
            self.prereg, **self.claim_kwargs
        )
        self.signature = self.private.sign(bytes.fromhex(self.claim["claim_hash"]))
        self.signed = registration.build_signed_genesis_replay_reservation_provider_registration_v1(
            self.claim,
            self.prereg,
            public_key_spki_base64=_b64(self.spki),
            signature_base64=_b64(self.signature),
            expected_claim_hash=self.claim["claim_hash"],
            **self.claim_kwargs,
        )

    def evaluate(self, signed=None, claim=None, **overrides):
        kwargs = {
            "public_key_spki_base64": _b64(self.spki),
            "signature_base64": _b64(self.signature),
            "expected_claim_hash": self.claim["claim_hash"],
            "expected_signed_registration_hash": self.signed[
                "signed_registration_hash"
            ],
            **self.claim_kwargs,
        }
        kwargs.update(overrides)
        return registration.evaluate_signed_genesis_replay_reservation_provider_registration_v1(
            self.signed if signed is None else signed,
            self.claim if claim is None else claim,
            self.prereg,
            **kwargs,
        )

    def test_claim_is_exact_deterministic_and_operationally_blocked(self) -> None:
        rebuilt = registration.build_genesis_replay_reservation_provider_registration_claim_v1(
            self.prereg, **self.claim_kwargs
        )
        self.assertEqual(rebuilt, self.claim)
        self.assertEqual(rebuilt["status"], "BLOCKED")
        self.assertTrue(
            registration.verify_genesis_replay_reservation_provider_registration_claim_v1(
                rebuilt,
                self.prereg,
                expected_claim_hash=rebuilt["claim_hash"],
                **self.claim_kwargs,
            )
        )

    def test_valid_signature_observes_key_possession_not_registration(self) -> None:
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["facts"]["preregistered_key_signature_verified"])
        self.assertTrue(evidence["facts"]["provider_key_possession_observed"])
        self.assertFalse(evidence["facts"]["provider_registered"])
        self.assertEqual(evidence["registration_status"], "BLOCKED")
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_wrong_key_self_signature_fails_preregistered_binding(self) -> None:
        wrong = Ed25519PrivateKey.generate()
        wrong_spki = _spki(wrong)
        wrong_signature = wrong.sign(bytes.fromhex(self.claim["claim_hash"]))
        wrong_signed = registration.build_signed_genesis_replay_reservation_provider_registration_v1(
            self.claim,
            self.prereg,
            public_key_spki_base64=_b64(wrong_spki),
            signature_base64=_b64(wrong_signature),
            expected_claim_hash=self.claim["claim_hash"],
            **self.claim_kwargs,
        )
        evidence = self.evaluate(
            signed=wrong_signed,
            public_key_spki_base64=_b64(wrong_spki),
            signature_base64=_b64(wrong_signature),
            expected_signed_registration_hash=wrong_signed[
                "signed_registration_hash"
            ],
        )
        self.assertTrue(evidence["facts"]["cryptographic_signature_verified"])
        self.assertFalse(evidence["facts"]["key_hash_matches_preregistration"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_tampered_signature_is_rejected(self) -> None:
        tampered_signature = bytes([self.signature[0] ^ 1]) + self.signature[1:]
        tampered = registration.build_signed_genesis_replay_reservation_provider_registration_v1(
            self.claim,
            self.prereg,
            public_key_spki_base64=_b64(self.spki),
            signature_base64=_b64(tampered_signature),
            expected_claim_hash=self.claim["claim_hash"],
            **self.claim_kwargs,
        )
        evidence = self.evaluate(
            signed=tampered,
            signature_base64=_b64(tampered_signature),
            expected_signed_registration_hash=tampered["signed_registration_hash"],
        )
        self.assertFalse(evidence["facts"]["cryptographic_signature_verified"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_resealed_and_resigned_registration_promotion_is_rejected(self) -> None:
        forged_claim = deepcopy(self.claim)
        forged_claim.pop("claim_hash")
        forged_claim["facts"]["provider_registered"] = True
        forged_claim = seal_strict_canonical_document(forged_claim, "claim_hash")
        forged_signature = self.private.sign(bytes.fromhex(forged_claim["claim_hash"]))
        forged_signed = deepcopy(self.signed)
        forged_signed.pop("signed_registration_hash")
        forged_signed["claim_hash"] = forged_claim["claim_hash"]
        forged_signed["signature_base64"] = _b64(forged_signature)
        forged_signed["signature_sha256"] = sha256(forged_signature).hexdigest()
        forged_signed = seal_strict_canonical_document(
            forged_signed, "signed_registration_hash"
        )
        evidence = self.evaluate(
            signed=forged_signed,
            claim=forged_claim,
            signature_base64=_b64(forged_signature),
            expected_claim_hash=forged_claim["claim_hash"],
            expected_signed_registration_hash=forged_signed[
                "signed_registration_hash"
            ],
        )
        self.assertFalse(evidence["facts"]["claim_document_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_signed_document_extra_field_and_schema_alias_are_rejected(self) -> None:
        for mutation in ("extra", "schema"):
            tampered = deepcopy(self.signed)
            tampered.pop("signed_registration_hash")
            if mutation == "extra":
                tampered["unexpected"] = False
            else:
                tampered["schema_version"] += "-alias"
            tampered = seal_strict_canonical_document(
                tampered, "signed_registration_hash"
            )
            self.assertEqual(
                self.evaluate(
                    signed=tampered,
                    expected_signed_registration_hash=tampered[
                        "signed_registration_hash"
                    ],
                )["status"],
                "BLOCK",
            )

    def test_challenge_and_nonce_drift_fail_closed(self) -> None:
        self.assertEqual(
            self.evaluate(challenge_hash=sha256(b"other-challenge").hexdigest())[
                "status"
            ],
            "BLOCK",
        )
        self.assertEqual(
            self.evaluate(
                registration_nonce_hash=sha256(b"other-nonce").hexdigest()
            )["status"],
            "BLOCK",
        )

    def test_preregistration_drift_cannot_build_claim(self) -> None:
        drifted = deepcopy(self.prereg)
        drifted["status"] = "PASS"
        with self.assertRaises(
            registration.GenesisReplayReservationProviderSignedRegistrationError
        ):
            registration.build_genesis_replay_reservation_provider_registration_claim_v1(
                drifted, **self.claim_kwargs
            )

    def test_evidence_verifier_rebuilds_and_rejects_mutation(self) -> None:
        evidence = self.evaluate()
        evaluation_kwargs = {
            "public_key_spki_base64": _b64(self.spki),
            "signature_base64": _b64(self.signature),
            "expected_claim_hash": self.claim["claim_hash"],
            "expected_signed_registration_hash": self.signed[
                "signed_registration_hash"
            ],
            **self.claim_kwargs,
        }
        self.assertTrue(
            registration.verify_signed_genesis_replay_reservation_provider_registration_evidence_v1(
                evidence,
                self.signed,
                self.claim,
                self.prereg,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )
        mutated = deepcopy(evidence)
        mutated["facts"]["provider_registered"] = True
        self.assertFalse(
            registration.verify_signed_genesis_replay_reservation_provider_registration_evidence_v1(
                mutated,
                self.signed,
                self.claim,
                self.prereg,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                **evaluation_kwargs,
            )
        )

    def test_evidence_redacts_raw_key_and_signature(self) -> None:
        encoded = json.dumps(self.evaluate(), sort_keys=True)
        self.assertNotIn(_b64(self.spki), encoded)
        self.assertNotIn(_b64(self.signature), encoded)
        self.assertTrue(self.evaluate()["facts"]["raw_public_key_redacted"])
        self.assertTrue(self.evaluate()["facts"]["raw_signature_redacted"])

    def test_malformed_base64_short_signature_and_non_ed25519_key_are_rejected(self) -> None:
        for key_b64, signature_b64 in (
            ("not-base64", _b64(self.signature)),
            (_b64(self.spki), _b64(b"short")),
            (_b64(_spki(ec.generate_private_key(ec.SECP256R1()))), _b64(self.signature)),
        ):
            with self.assertRaises(
                registration.GenesisReplayReservationProviderSignedRegistrationError
            ):
                registration.build_signed_genesis_replay_reservation_provider_registration_v1(
                    self.claim,
                    self.prereg,
                    public_key_spki_base64=key_b64,
                    signature_base64=signature_b64,
                    expected_claim_hash=self.claim["claim_hash"],
                    **self.claim_kwargs,
                )

    def test_builders_are_deterministic_and_do_not_mutate_inputs(self) -> None:
        before = deepcopy(self.preregistration_kwargs)
        rebuilt = registration.build_genesis_replay_reservation_provider_registration_claim_v1(
            self.prereg, **self.claim_kwargs
        )
        self.assertEqual(rebuilt, self.claim)
        self.assertEqual(before, self.preregistration_kwargs)

    def test_production_module_has_no_private_key_provider_io_or_runtime(self) -> None:
        source = Path(registration.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            ".reserve_once(",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
