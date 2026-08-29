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
    challenge_consumption_provider_registration_handoff_v1 as handoff,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1 as preregistration,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_registration_challenge_signed_source_v1 as challenge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_signed_registration_v1 as registration,
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


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionProviderRegistrationHandoffV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_private = Ed25519PrivateKey.generate()
        self.provider_spki = _spki(self.provider_private)
        self.provider_kwargs = {
            "registry_id": "synthetic.challenge.consumption.registry.v1",
            "operator_identity_claim": "synthetic.challenge.operator.v1",
            "public_key_spki_sha256": sha256(self.provider_spki).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "provider_implementation_claim_sha256": _hash(
                "synthetic-consumption-provider"
            ),
        }
        self.provider_preregistration = (
            preregistration.build_challenge_consumption_provider_preregistration_v1(
                **self.provider_kwargs
            )
        )

        self.authority_private = Ed25519PrivateKey.generate()
        self.authority_spki = _spki(self.authority_private)
        self.authority_kwargs = {
            "challenge_authority_id": "synthetic.consumption.challenge.authority.v1",
            "challenge_authority_key_id": "synthetic.consumption.challenge.key.v1",
            "challenge_authority_public_key_spki_sha256": sha256(
                self.authority_spki
            ).hexdigest(),
            "challenge_authority_trust_domain": "synthetic.test-only",
            "challenge_authority_implementation_claim_sha256": _hash(
                "synthetic-consumption-challenge-authority"
            ),
        }
        self.authority_preregistration = (
            challenge.build_challenge_consumption_provider_registration_challenge_authority_preregistration_v1(
                **self.authority_kwargs
            )
        )
        self.registration_nonce_hash = _hash("synthetic-registration-nonce")
        self.challenge_build_kwargs = {
            "provider_preregistration_kwargs": self.provider_kwargs,
            "authority_preregistration_kwargs": self.authority_kwargs,
            "challenge_id_hash": _hash("synthetic-registration-challenge"),
            "registration_nonce_hash": self.registration_nonce_hash,
            "issued_at_unix_ms": 1_800_000_000_000,
            "expires_at_unix_ms": 1_800_000_120_000,
        }
        self.challenge = (
            challenge.build_challenge_consumption_provider_registration_challenge_v1(
                self.provider_preregistration,
                self.authority_preregistration,
                **self.challenge_build_kwargs,
            )
        )
        self.challenge_signature = self.authority_private.sign(
            bytes.fromhex(self.challenge["challenge_hash"])
        )
        self.signed_challenge = (
            challenge.build_signed_challenge_consumption_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(self.challenge_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.challenge_build_kwargs,
            )
        )
        self.challenge_evaluation_kwargs = {
            "public_key_spki_base64": _b64(self.authority_spki),
            "signature_base64": _b64(self.challenge_signature),
            "expected_challenge_hash": self.challenge["challenge_hash"],
            "expected_signed_challenge_hash": self.signed_challenge[
                "signed_challenge_hash"
            ],
            **self.challenge_build_kwargs,
        }
        self.challenge_evidence = (
            challenge.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                self.signed_challenge,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                **self.challenge_evaluation_kwargs,
            )
        )
        self.registration_bundle = self._registration_bundle(
            self.signed_challenge["signed_challenge_hash"],
            self.registration_nonce_hash,
        )

    def _registration_bundle(
        self, challenge_hash: str, registration_nonce_hash: str
    ) -> dict[str, object]:
        claim_kwargs = {
            "challenge_hash": challenge_hash,
            "registration_nonce_hash": registration_nonce_hash,
            "preregistration_kwargs": self.provider_kwargs,
        }
        claim = (
            registration.build_challenge_consumption_provider_registration_claim_v1(
                self.provider_preregistration, **claim_kwargs
            )
        )
        signature = self.provider_private.sign(bytes.fromhex(claim["claim_hash"]))
        signed = (
            registration.build_signed_challenge_consumption_provider_registration_v1(
                claim,
                self.provider_preregistration,
                public_key_spki_base64=_b64(self.provider_spki),
                signature_base64=_b64(signature),
                expected_claim_hash=claim["claim_hash"],
                **claim_kwargs,
            )
        )
        evaluation_kwargs = {
            "public_key_spki_base64": _b64(self.provider_spki),
            "signature_base64": _b64(signature),
            "expected_claim_hash": claim["claim_hash"],
            "expected_signed_registration_hash": signed[
                "signed_registration_hash"
            ],
            **claim_kwargs,
        }
        evidence = (
            registration.evaluate_signed_challenge_consumption_provider_registration_v1(
                signed,
                claim,
                self.provider_preregistration,
                **evaluation_kwargs,
            )
        )
        return {
            "claim": claim,
            "signature": signature,
            "signed": signed,
            "evaluation_kwargs": evaluation_kwargs,
            "evidence": evidence,
        }

    def evaluate_handoff(
        self,
        bundle: dict[str, object] | None = None,
        challenge_evidence=None,
    ):
        selected = self.registration_bundle if bundle is None else bundle
        return handoff.evaluate_challenge_consumption_provider_registration_handoff_v1(
            self.challenge_evidence
            if challenge_evidence is None
            else challenge_evidence,
            self.signed_challenge,
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            selected["evidence"],
            selected["signed"],
            selected["claim"],
            expected_challenge_evidence_hash=self.challenge_evidence[
                "verification_evidence_hash"
            ],
            expected_provider_registration_evidence_hash=selected["evidence"][
                "verification_evidence_hash"
            ],
            challenge_evaluation_kwargs=self.challenge_evaluation_kwargs,
            provider_registration_evaluation_kwargs=selected[
                "evaluation_kwargs"
            ],
        )

    def test_preregistration_and_challenge_are_exact_redacted_and_blocked(self) -> None:
        rebuilt = (
            challenge.build_challenge_consumption_provider_registration_challenge_authority_preregistration_v1(
                **self.authority_kwargs
            )
        )
        self.assertEqual(rebuilt, self.authority_preregistration)
        self.assertTrue(
            challenge.verify_challenge_consumption_provider_registration_challenge_authority_preregistration_v1(
                rebuilt, **self.authority_kwargs
            )
        )
        self.assertEqual(rebuilt["status"], "BLOCKED")
        self.assertNotIn(_b64(self.authority_spki), json.dumps(rebuilt))
        self.assertEqual(
            self.challenge["source"]["provider_preregistration_hash"],
            self.provider_preregistration["preregistration_hash"],
        )
        self.assertFalse(self.challenge["facts"]["challenge_freshness_verified"])

    def test_valid_handoff_is_local_pass_with_all_authority_false(self) -> None:
        evidence = self.evaluate_handoff()
        self.assertEqual(self.challenge_evidence["status"], "PASS")
        self.assertEqual(self.registration_bundle["evidence"]["status"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["facts"]["dual_signature_handoff_exact"])
        self.assertFalse(evidence["facts"]["challenge_freshness_verified"])
        self.assertFalse(evidence["facts"]["registration_replay_consumed"])
        self.assertFalse(evidence["facts"]["provider_registered"])
        self.assertEqual(evidence["registration_status"], "BLOCKED")
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_valid_wrong_challenge_hash_is_rejected_by_handoff(self) -> None:
        alternate = self._registration_bundle(
            _hash("unrelated-signed-challenge"),
            self.registration_nonce_hash,
        )
        self.assertEqual(alternate["evidence"]["status"], "PASS")
        evidence = self.evaluate_handoff(alternate)
        self.assertFalse(
            evidence["facts"]["signed_challenge_hash_bound_to_registration_claim"]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_valid_wrong_nonce_is_rejected_by_handoff(self) -> None:
        alternate = self._registration_bundle(
            self.signed_challenge["signed_challenge_hash"],
            _hash("unrelated-registration-nonce"),
        )
        self.assertEqual(alternate["evidence"]["status"], "PASS")
        evidence = self.evaluate_handoff(alternate)
        self.assertFalse(evidence["facts"]["registration_nonce_bound_end_to_end"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_wrong_authority_key_self_signature_is_rejected(self) -> None:
        wrong = Ed25519PrivateKey.generate()
        wrong_spki = _spki(wrong)
        wrong_signature = wrong.sign(bytes.fromhex(self.challenge["challenge_hash"]))
        wrong_signed = (
            challenge.build_signed_challenge_consumption_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(wrong_spki),
                signature_base64=_b64(wrong_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.challenge_build_kwargs,
            )
        )
        evidence = (
            challenge.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                wrong_signed,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(wrong_spki),
                signature_base64=_b64(wrong_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                expected_signed_challenge_hash=wrong_signed[
                    "signed_challenge_hash"
                ],
                **self.challenge_build_kwargs,
            )
        )
        self.assertTrue(evidence["facts"]["cryptographic_signature_verified"])
        self.assertFalse(
            evidence["facts"]["authority_key_hash_matches_preregistration"]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_tampered_signature_is_rejected(self) -> None:
        tampered_signature = (
            bytes([self.challenge_signature[0] ^ 1])
            + self.challenge_signature[1:]
        )
        tampered = (
            challenge.build_signed_challenge_consumption_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(tampered_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.challenge_build_kwargs,
            )
        )
        evidence = (
            challenge.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                tampered,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(tampered_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                expected_signed_challenge_hash=tampered["signed_challenge_hash"],
                **self.challenge_build_kwargs,
            )
        )
        self.assertFalse(evidence["facts"]["cryptographic_signature_verified"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_resealed_and_resigned_freshness_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.challenge)
        forged.pop("challenge_hash")
        forged["facts"]["challenge_freshness_verified"] = True
        forged = seal_strict_canonical_document(forged, "challenge_hash")
        forged_signature = self.authority_private.sign(
            bytes.fromhex(forged["challenge_hash"])
        )
        forged_signed = deepcopy(self.signed_challenge)
        forged_signed.pop("signed_challenge_hash")
        forged_signed["challenge_hash"] = forged["challenge_hash"]
        forged_signed["signature_base64"] = _b64(forged_signature)
        forged_signed["signature_sha256"] = sha256(forged_signature).hexdigest()
        forged_signed = seal_strict_canonical_document(
            forged_signed, "signed_challenge_hash"
        )
        evidence = (
            challenge.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                forged_signed,
                forged,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.authority_spki),
                signature_base64=_b64(forged_signature),
                expected_challenge_hash=forged["challenge_hash"],
                expected_signed_challenge_hash=forged_signed[
                    "signed_challenge_hash"
                ],
                **self.challenge_build_kwargs,
            )
        )
        self.assertFalse(evidence["facts"]["challenge_document_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_schema_extra_field_and_preregistration_drift_fail_closed(self) -> None:
        alias = deepcopy(self.signed_challenge)
        alias["schema_version"] += "-alias"
        self.assertEqual(
            challenge.evaluate_signed_challenge_consumption_provider_registration_challenge_v1(
                alias,
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                **self.challenge_evaluation_kwargs,
            )["status"],
            "BLOCK",
        )
        extra = deepcopy(self.challenge_evidence)
        extra["unexpected"] = False
        self.assertEqual(
            self.evaluate_handoff(challenge_evidence=extra)["status"], "BLOCK"
        )
        drifted = deepcopy(self.provider_preregistration)
        drifted["status"] = "PASS"
        with self.assertRaises(
            challenge.ChallengeConsumptionProviderRegistrationChallengeSourceError
        ):
            challenge.build_challenge_consumption_provider_registration_challenge_v1(
                drifted,
                self.authority_preregistration,
                **self.challenge_build_kwargs,
            )

    def test_bool_time_and_excessive_lifetime_are_rejected(self) -> None:
        for overrides in (
            {"issued_at_unix_ms": True},
            {"expires_at_unix_ms": 1_800_000_300_001},
        ):
            kwargs = {**self.challenge_build_kwargs, **overrides}
            with self.assertRaises(
                challenge.ChallengeConsumptionProviderRegistrationChallengeSourceError
            ):
                challenge.build_challenge_consumption_provider_registration_challenge_v1(
                    self.provider_preregistration,
                    self.authority_preregistration,
                    **kwargs,
                )

    def test_handoff_verifier_rebuilds_and_rejects_mutation(self) -> None:
        evidence = self.evaluate_handoff()
        bundle = self.registration_bundle
        args = (
            self.challenge_evidence,
            self.signed_challenge,
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
        )
        kwargs = {
            "expected_challenge_evidence_hash": self.challenge_evidence[
                "verification_evidence_hash"
            ],
            "expected_provider_registration_evidence_hash": bundle["evidence"][
                "verification_evidence_hash"
            ],
            "challenge_evaluation_kwargs": self.challenge_evaluation_kwargs,
            "provider_registration_evaluation_kwargs": bundle[
                "evaluation_kwargs"
            ],
        }
        self.assertTrue(
            handoff.verify_challenge_consumption_provider_registration_handoff_v1(
                evidence,
                *args,
                expected_handoff_evidence_hash=evidence[
                    "handoff_evidence_hash"
                ],
                **kwargs,
            )
        )
        mutated = deepcopy(evidence)
        mutated["facts"]["challenge_freshness_verified"] = True
        self.assertFalse(
            handoff.verify_challenge_consumption_provider_registration_handoff_v1(
                mutated,
                *args,
                expected_handoff_evidence_hash=evidence[
                    "handoff_evidence_hash"
                ],
                **kwargs,
            )
        )

    def test_evidence_redacts_raw_material_and_preserves_inputs(self) -> None:
        before_challenge = deepcopy(self.challenge_evaluation_kwargs)
        before_registration = deepcopy(
            self.registration_bundle["evaluation_kwargs"]
        )
        encoded = json.dumps(self.evaluate_handoff(), sort_keys=True)
        for material in (
            _b64(self.authority_spki),
            _b64(self.challenge_signature),
            _b64(self.provider_spki),
            _b64(self.registration_bundle["signature"]),
        ):
            self.assertNotIn(material, encoded)
        self.assertEqual(before_challenge, self.challenge_evaluation_kwargs)
        self.assertEqual(
            before_registration,
            self.registration_bundle["evaluation_kwargs"],
        )

    def test_production_has_no_private_key_io_clock_provider_or_runtime(self) -> None:
        for module in (challenge, handoff):
            source = Path(module.__file__).read_text(encoding="utf-8")
            for forbidden in (
                "Ed25519PrivateKey",
                "private_key",
                ".consume_once(",
                "open(",
                "Path(",
                "socket",
                "subprocess",
                "time.time",
                "datetime.now",
                "runtime/",
            ):
                self.assertNotIn(forbidden, source)
        evidence = self.evaluate_handoff()
        self.assertFalse(evidence["facts"]["current_time_established"])
        self.assertFalse(evidence["facts"]["external_provider_conformance_verified"])


if __name__ == "__main__":
    unittest.main()
