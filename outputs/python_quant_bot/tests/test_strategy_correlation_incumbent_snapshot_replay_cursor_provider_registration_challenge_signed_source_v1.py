from __future__ import annotations

import base64
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_signed_source_v1 as challenge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1 as registration,
)
from exchange_terminal.application.strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1 import (
    build_replay_cursor_provider_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class ReplayCursorProviderRegistrationChallengeSignedSourceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_private = Ed25519PrivateKey.generate()
        self.provider_spki = _spki(self.provider_private)
        self.provider_kwargs = {
            "registry_id": "synthetic.replay.registry.v1",
            "operator_identity_claim": "synthetic.provider.operator.v1",
            "public_key_spki_sha256": sha256(self.provider_spki).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "provider_implementation_claim_sha256": sha256(
                b"synthetic-provider-implementation"
            ).hexdigest(),
        }
        self.provider_preregistration = build_replay_cursor_provider_preregistration_v1(
            **self.provider_kwargs
        )
        self.authority_private = Ed25519PrivateKey.generate()
        self.authority_spki = _spki(self.authority_private)
        self.authority_kwargs = {
            "challenge_authority_id": "synthetic.challenge.authority.v1",
            "challenge_authority_key_id": "synthetic.challenge.key.v1",
            "challenge_authority_public_key_spki_sha256": sha256(
                self.authority_spki
            ).hexdigest(),
            "challenge_authority_trust_domain": "synthetic.test-only",
            "challenge_authority_implementation_claim_sha256": sha256(
                b"synthetic-challenge-authority-implementation"
            ).hexdigest(),
        }
        self.authority_preregistration = (
            challenge.build_replay_cursor_provider_registration_challenge_authority_preregistration_v1(
                **self.authority_kwargs
            )
        )
        self.challenge_id_hash = sha256(b"synthetic-challenge-id").hexdigest()
        self.registration_nonce_hash = sha256(
            b"synthetic-registration-nonce"
        ).hexdigest()
        self.build_kwargs = {
            "provider_preregistration_kwargs": self.provider_kwargs,
            "authority_preregistration_kwargs": self.authority_kwargs,
            "challenge_id_hash": self.challenge_id_hash,
            "registration_nonce_hash": self.registration_nonce_hash,
            "issued_at_unix_ms": 1_800_000_000_000,
            "expires_at_unix_ms": 1_800_000_120_000,
        }
        self.challenge = challenge.build_replay_cursor_provider_registration_challenge_v1(
            self.provider_preregistration,
            self.authority_preregistration,
            **self.build_kwargs,
        )
        self.signature = self.authority_private.sign(
            bytes.fromhex(self.challenge["challenge_hash"])
        )
        self.signed = challenge.build_signed_replay_cursor_provider_registration_challenge_v1(
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            public_key_spki_base64=_b64(self.authority_spki),
            signature_base64=_b64(self.signature),
            expected_challenge_hash=self.challenge["challenge_hash"],
            **self.build_kwargs,
        )

    def evaluate(self, signed=None, challenge_document=None, **overrides):
        kwargs = {
            "public_key_spki_base64": _b64(self.authority_spki),
            "signature_base64": _b64(self.signature),
            "expected_challenge_hash": self.challenge["challenge_hash"],
            "expected_signed_challenge_hash": self.signed[
                "signed_challenge_hash"
            ],
            **self.build_kwargs,
        }
        kwargs.update(overrides)
        return challenge.evaluate_signed_replay_cursor_provider_registration_challenge_v1(
            self.signed if signed is None else signed,
            self.challenge if challenge_document is None else challenge_document,
            self.provider_preregistration,
            self.authority_preregistration,
            **kwargs,
        )

    def test_authority_preregistration_is_exact_redacted_and_blocked(self) -> None:
        rebuilt = challenge.build_replay_cursor_provider_registration_challenge_authority_preregistration_v1(
            **self.authority_kwargs
        )
        self.assertEqual(rebuilt, self.authority_preregistration)
        self.assertTrue(
            challenge.verify_replay_cursor_provider_registration_challenge_authority_preregistration_v1(
                rebuilt, **self.authority_kwargs
            )
        )
        self.assertEqual(rebuilt["status"], "BLOCKED")
        encoded = json.dumps(rebuilt, sort_keys=True)
        self.assertNotIn(_b64(self.authority_spki), encoded)

    def test_challenge_is_deterministic_and_binds_declared_window_only(self) -> None:
        rebuilt = challenge.build_replay_cursor_provider_registration_challenge_v1(
            self.provider_preregistration,
            self.authority_preregistration,
            **self.build_kwargs,
        )
        self.assertEqual(rebuilt, self.challenge)
        self.assertTrue(
            challenge.verify_replay_cursor_provider_registration_challenge_v1(
                rebuilt,
                self.provider_preregistration,
                self.authority_preregistration,
                expected_challenge_hash=rebuilt["challenge_hash"],
                **self.build_kwargs,
            )
        )
        self.assertTrue(rebuilt["facts"]["claimed_time_window_well_formed"])
        self.assertFalse(rebuilt["facts"]["challenge_freshness_verified"])

    def test_valid_signature_observes_key_possession_without_authority(self) -> None:
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(
            evidence["facts"]["preregistered_challenge_key_signature_verified"]
        )
        self.assertTrue(
            evidence["facts"]["challenge_source_key_possession_observed"]
        )
        self.assertFalse(evidence["facts"]["challenge_freshness_verified"])
        self.assertFalse(evidence["facts"]["challenge_consumption_verified"])
        self.assertFalse(evidence["facts"]["provider_registered"])
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_wrong_key_can_sign_candidate_but_fails_preregistered_binding(self) -> None:
        wrong_private = Ed25519PrivateKey.generate()
        wrong_spki = _spki(wrong_private)
        wrong_signature = wrong_private.sign(bytes.fromhex(self.challenge["challenge_hash"]))
        wrong_signed = challenge.build_signed_replay_cursor_provider_registration_challenge_v1(
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            public_key_spki_base64=_b64(wrong_spki),
            signature_base64=_b64(wrong_signature),
            expected_challenge_hash=self.challenge["challenge_hash"],
            **self.build_kwargs,
        )
        evidence = self.evaluate(
            signed=wrong_signed,
            public_key_spki_base64=_b64(wrong_spki),
            signature_base64=_b64(wrong_signature),
            expected_signed_challenge_hash=wrong_signed["signed_challenge_hash"],
        )
        self.assertTrue(evidence["facts"]["cryptographic_signature_verified"])
        self.assertFalse(
            evidence["facts"]["authority_key_hash_matches_preregistration"]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_tampered_signature_is_rejected(self) -> None:
        tampered_signature = bytes([self.signature[0] ^ 1]) + self.signature[1:]
        tampered = challenge.build_signed_replay_cursor_provider_registration_challenge_v1(
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            public_key_spki_base64=_b64(self.authority_spki),
            signature_base64=_b64(tampered_signature),
            expected_challenge_hash=self.challenge["challenge_hash"],
            **self.build_kwargs,
        )
        evidence = self.evaluate(
            signed=tampered,
            signature_base64=_b64(tampered_signature),
            expected_signed_challenge_hash=tampered["signed_challenge_hash"],
        )
        self.assertFalse(evidence["facts"]["cryptographic_signature_verified"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_resealed_and_resigned_freshness_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.challenge)
        forged.pop("challenge_hash")
        forged["facts"]["challenge_freshness_verified"] = True
        forged = seal_strict_canonical_document(forged, "challenge_hash")
        forged_signature = self.authority_private.sign(bytes.fromhex(forged["challenge_hash"]))
        forged_signed = deepcopy(self.signed)
        forged_signed.pop("signed_challenge_hash")
        forged_signed["challenge_hash"] = forged["challenge_hash"]
        forged_signed["signature_base64"] = _b64(forged_signature)
        forged_signed["signature_sha256"] = sha256(forged_signature).hexdigest()
        forged_signed = seal_strict_canonical_document(
            forged_signed, "signed_challenge_hash"
        )
        evidence = self.evaluate(
            signed=forged_signed,
            challenge_document=forged,
            signature_base64=_b64(forged_signature),
            expected_challenge_hash=forged["challenge_hash"],
            expected_signed_challenge_hash=forged_signed["signed_challenge_hash"],
        )
        self.assertFalse(evidence["facts"]["challenge_document_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_nonce_time_and_provider_binding_drift_fail_closed(self) -> None:
        evidence = self.evaluate(
            registration_nonce_hash=sha256(b"different-nonce").hexdigest()
        )
        self.assertEqual(evidence["status"], "BLOCK")
        evidence = self.evaluate(expires_at_unix_ms=1_800_000_400_001)
        self.assertEqual(evidence["status"], "BLOCK")
        drifted = deepcopy(self.provider_preregistration)
        drifted["status"] = "PASS"
        with self.assertRaises(
            challenge.ReplayCursorProviderRegistrationChallengeContractError
        ):
            challenge.build_replay_cursor_provider_registration_challenge_v1(
                drifted, self.authority_preregistration, **self.build_kwargs
            )

    def test_extra_field_and_schema_alias_are_rejected(self) -> None:
        tampered = deepcopy(self.signed)
        tampered.pop("signed_challenge_hash")
        tampered["unexpected"] = False
        tampered = seal_strict_canonical_document(tampered, "signed_challenge_hash")
        self.assertEqual(
            self.evaluate(
                signed=tampered,
                expected_signed_challenge_hash=tampered["signed_challenge_hash"],
            )["status"],
            "BLOCK",
        )
        alias = deepcopy(self.challenge)
        alias["schema_version"] += "-alias"
        self.assertEqual(self.evaluate(challenge_document=alias)["status"], "BLOCK")

    def test_evidence_verifier_rebuilds_exactly_and_rejects_mutation(self) -> None:
        evidence = self.evaluate()
        self.assertTrue(
            challenge.verify_signed_replay_cursor_provider_registration_challenge_evidence_v1(
                evidence,
                self.signed,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(self.signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                expected_signed_challenge_hash=self.signed[
                    "signed_challenge_hash"
                ],
                **self.build_kwargs,
            )
        )
        mutated = deepcopy(evidence)
        mutated["facts"]["challenge_freshness_verified"] = True
        self.assertFalse(
            challenge.verify_signed_replay_cursor_provider_registration_challenge_evidence_v1(
                mutated,
                self.signed,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                expected_verification_evidence_hash=evidence[
                    "verification_evidence_hash"
                ],
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(self.signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                expected_signed_challenge_hash=self.signed[
                    "signed_challenge_hash"
                ],
                **self.build_kwargs,
            )
        )

    def test_evidence_redacts_public_key_and_signature_material(self) -> None:
        encoded = json.dumps(self.evaluate(), sort_keys=True)
        self.assertNotIn(_b64(self.authority_spki), encoded)
        self.assertNotIn(_b64(self.signature), encoded)
        self.assertTrue(self.evaluate()["facts"]["raw_public_key_redacted"])
        self.assertTrue(self.evaluate()["facts"]["raw_signature_redacted"])

    def test_malformed_base64_short_signature_and_bool_time_are_rejected(self) -> None:
        with self.assertRaises(
            challenge.ReplayCursorProviderRegistrationChallengeContractError
        ):
            challenge.build_signed_replay_cursor_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64="not-base64",
                signature_base64=_b64(self.signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.build_kwargs,
            )
        with self.assertRaises(
            challenge.ReplayCursorProviderRegistrationChallengeContractError
        ):
            challenge.build_signed_replay_cursor_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(b"short"),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.build_kwargs,
            )
        bad_time = {**self.build_kwargs, "issued_at_unix_ms": True}
        with self.assertRaises(
            challenge.ReplayCursorProviderRegistrationChallengeContractError
        ):
            challenge.build_replay_cursor_provider_registration_challenge_v1(
                self.provider_preregistration,
                self.authority_preregistration,
                **bad_time,
            )

    def test_production_module_has_no_private_key_io_clock_or_runtime_access(self) -> None:
        source = Path(challenge.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "time.time",
            "datetime.now",
            "runtime/",
        ):
            self.assertNotIn(forbidden, source)

    def test_dual_signature_handoff_binds_challenge_without_promotion(self) -> None:
        challenge_evidence = self.evaluate()
        provider_claim = registration.build_replay_cursor_provider_registration_claim_v1(
            self.provider_preregistration,
            challenge_hash=self.signed["signed_challenge_hash"],
            registration_nonce_hash=self.registration_nonce_hash,
            **self.provider_kwargs,
        )
        provider_signature = self.provider_private.sign(
            bytes.fromhex(provider_claim["claim_hash"])
        )
        provider_signed = registration.build_signed_replay_cursor_provider_registration_v1(
            provider_claim,
            self.provider_preregistration,
            public_key_spki_base64=_b64(self.provider_spki),
            signature_base64=_b64(provider_signature),
            expected_claim_hash=provider_claim["claim_hash"],
            challenge_hash=self.signed["signed_challenge_hash"],
            registration_nonce_hash=self.registration_nonce_hash,
            **self.provider_kwargs,
        )
        provider_evidence = registration.evaluate_signed_replay_cursor_provider_registration_v1(
            provider_signed,
            provider_claim,
            self.provider_preregistration,
            public_key_spki_base64=_b64(self.provider_spki),
            signature_base64=_b64(provider_signature),
            expected_claim_hash=provider_claim["claim_hash"],
            expected_signed_registration_hash=provider_signed[
                "signed_registration_hash"
            ],
            challenge_hash=self.signed["signed_challenge_hash"],
            registration_nonce_hash=self.registration_nonce_hash,
            **self.provider_kwargs,
        )
        self.assertEqual(challenge_evidence["status"], "PASS")
        self.assertEqual(provider_evidence["status"], "PASS")
        self.assertTrue(
            provider_evidence["facts"]["preregistered_key_signature_verified"]
        )
        self.assertFalse(
            provider_evidence["facts"]["challenge_source_authority_verified"]
        )
        self.assertFalse(challenge_evidence["facts"]["challenge_freshness_verified"])
        self.assertFalse(provider_evidence["facts"]["provider_registered"])
        self.assertTrue(
            all(value is False for value in provider_evidence["authority"].values())
        )


if __name__ == "__main__":
    unittest.main()
