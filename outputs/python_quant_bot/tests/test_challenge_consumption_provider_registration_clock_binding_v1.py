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
    challenge_consumption_provider_registration_clock_binding_v1 as binding,
)
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
from exchange_terminal.services import trusted_clock_authority_v3 as clock
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


def _raw(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionProviderRegistrationClockBindingV1Tests(
    unittest.TestCase
):
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

        self.challenge_private = Ed25519PrivateKey.generate()
        self.challenge_spki = _spki(self.challenge_private)
        self.authority_kwargs = {
            "challenge_authority_id": "synthetic.consumption.challenge.authority.v1",
            "challenge_authority_key_id": "synthetic.consumption.challenge.key.v1",
            "challenge_authority_public_key_spki_sha256": sha256(
                self.challenge_spki
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
        self.registration_nonce_hash = _hash("registration-nonce")
        self.challenge_build_kwargs = {
            "provider_preregistration_kwargs": self.provider_kwargs,
            "authority_preregistration_kwargs": self.authority_kwargs,
            "challenge_id_hash": _hash("registration-challenge"),
            "registration_nonce_hash": self.registration_nonce_hash,
            "issued_at_unix_ms": 1_009_000,
            "expires_at_unix_ms": 1_012_000,
        }
        self.challenge = (
            challenge.build_challenge_consumption_provider_registration_challenge_v1(
                self.provider_preregistration,
                self.authority_preregistration,
                **self.challenge_build_kwargs,
            )
        )
        self.challenge_signature = self.challenge_private.sign(
            bytes.fromhex(self.challenge["challenge_hash"])
        )
        self.signed_challenge = (
            challenge.build_signed_challenge_consumption_provider_registration_challenge_v1(
                self.challenge,
                self.provider_preregistration,
                self.authority_preregistration,
                public_key_spki_base64=_b64(self.challenge_spki),
                signature_base64=_b64(self.challenge_signature),
                expected_challenge_hash=self.challenge["challenge_hash"],
                **self.challenge_build_kwargs,
            )
        )
        self.challenge_evaluation_kwargs = {
            "public_key_spki_base64": _b64(self.challenge_spki),
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
        self.provider_bundle = self.build_provider_bundle(
            self.signed_challenge["signed_challenge_hash"],
            self.registration_nonce_hash,
        )
        self.handoff_evidence = self.build_handoff(self.provider_bundle)

        self.clock_private = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]
        self.clock_raw = [_raw(key) for key in self.clock_private]
        self.clock_authorities = [
            {
                "authority_id": "clock.a.v1",
                "key_id": "clock.a.key.v1",
                "public_key_base64": _b64(self.clock_raw[0]),
            },
            {
                "authority_id": "clock.b.v1",
                "key_id": "clock.b.key.v1",
                "public_key_base64": _b64(self.clock_raw[1]),
            },
        ]
        self.clock_registration = (
            clock.build_trusted_clock_authority_registration_v3(
                self.clock_authorities,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=100,
                max_local_skew_ms=1_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )
        )
        self.clock_public_keys = {
            authority["authority_id"]: authority["public_key_base64"]
            for authority in self.clock_authorities
        }
        (
            self.clock_receipts,
            self.expected_receipt_hashes,
            self.clock_attestation,
        ) = self.build_clock_chain()

    def build_provider_bundle(
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

    def build_handoff(self, bundle: dict[str, object]):
        return handoff.evaluate_challenge_consumption_provider_registration_handoff_v1(
            self.challenge_evidence,
            self.signed_challenge,
            self.challenge,
            self.provider_preregistration,
            self.authority_preregistration,
            bundle["evidence"],
            bundle["signed"],
            bundle["claim"],
            expected_challenge_evidence_hash=self.challenge_evidence[
                "verification_evidence_hash"
            ],
            expected_provider_registration_evidence_hash=bundle["evidence"][
                "verification_evidence_hash"
            ],
            challenge_evaluation_kwargs=self.challenge_evaluation_kwargs,
            provider_registration_evaluation_kwargs=bundle[
                "evaluation_kwargs"
            ],
        )

    def build_clock_chain(
        self,
        *,
        context_hash: str | None = None,
        nonce_hash: str | None = None,
        observed: tuple[int, int] = (1_010_000, 1_010_020),
        verification_time_ms: int = 1_010_500,
    ):
        context = context_hash or self.signed_challenge["signed_challenge_hash"]
        nonce = nonce_hash or self.registration_nonce_hash
        receipts = []
        expected = {}
        for private_key, authority, observed_at in zip(
            self.clock_private, self.clock_authorities, observed
        ):
            unsigned = clock.build_unsigned_trusted_clock_authority_receipt_v3(
                self.clock_registration,
                authority_id=authority["authority_id"],
                key_id=authority["key_id"],
                request_nonce_hash=nonce,
                request_context_hash=context,
                observed_at_ms=observed_at,
                issued_at_ms=observed_at + 10,
            )
            signature = private_key.sign(
                bytes.fromhex(unsigned["receipt_content_hash"])
            )
            receipt = clock.assemble_trusted_clock_authority_receipt_v3(
                self.clock_registration, unsigned, _b64(signature)
            )
            receipts.append(receipt)
            expected[authority["authority_id"]] = receipt["receipt_hash"]
        attestation = clock.evaluate_trusted_clock_authority_v3(
            self.clock_registration,
            receipts,
            self.clock_public_keys,
            expected_registration_hash=self.clock_registration[
                "registration_hash"
            ],
            expected_receipt_hashes=expected,
            request_nonce_hash=nonce,
            request_context_hash=context,
            verification_time_ms=verification_time_ms,
        )
        return receipts, expected, attestation

    def evaluate(self, **overrides):
        bundle = overrides.pop("provider_bundle", self.provider_bundle)
        kwargs = {
            "clock_attestation": self.clock_attestation,
            "clock_registration": self.clock_registration,
            "clock_receipts": self.clock_receipts,
            "clock_public_keys_by_id": self.clock_public_keys,
            "handoff_evidence": self.handoff_evidence,
            "challenge_evidence": self.challenge_evidence,
            "signed_challenge_document": self.signed_challenge,
            "challenge_document": self.challenge,
            "provider_preregistration_document": self.provider_preregistration,
            "challenge_authority_preregistration_document": (
                self.authority_preregistration
            ),
            "provider_registration_evidence_document": bundle["evidence"],
            "signed_provider_registration_document": bundle["signed"],
            "provider_registration_claim_document": bundle["claim"],
            "expected_clock_attestation_hash": self.clock_attestation[
                "attestation_hash"
            ],
            "expected_clock_registration_hash": self.clock_registration[
                "registration_hash"
            ],
            "expected_clock_receipt_hashes": self.expected_receipt_hashes,
            "clock_verification_time_ms": 1_010_500,
            "expected_handoff_evidence_hash": self.handoff_evidence[
                "handoff_evidence_hash"
            ],
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
        kwargs.update(overrides)
        return binding.evaluate_challenge_consumption_provider_registration_clock_binding_v1(
            **kwargs
        )

    def test_happy_path_reports_only_local_binding_facts(self) -> None:
        evidence = self.evaluate()
        self.assertEqual(evidence["status"], "PASS")
        for name in (
            "handoff_evidence_exact",
            "dual_signature_handoff_verified",
            "challenge_source_key_signature_verified",
            "provider_key_signature_verified",
            "clock_attestation_exact",
            "clock_detached_signatures_verified",
            "clock_multi_authority_quorum_verified",
            "clock_context_bound_to_signed_challenge",
            "clock_nonce_bound_to_registration_nonce",
            "reference_time_inside_declared_challenge_window",
        ):
            self.assertTrue(evidence["facts"][name], name)
        for name in (
            "external_time_authority_trust_verified",
            "verification_time_source_trusted",
            "current_time_established",
            "challenge_freshness_verified",
            "registration_replay_consumed",
            "provider_registered",
        ):
            self.assertFalse(evidence["facts"][name], name)
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_clock_context_must_equal_signed_challenge_hash(self) -> None:
        receipts, expected, attestation = self.build_clock_chain(
            context_hash=_hash("wrong-context")
        )
        evidence = self.evaluate(
            clock_attestation=attestation,
            clock_receipts=receipts,
            expected_clock_receipt_hashes=expected,
            expected_clock_attestation_hash=attestation["attestation_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertFalse(evidence["facts"]["clock_attestation_exact"])

    def test_clock_nonce_must_equal_registration_nonce(self) -> None:
        receipts, expected, attestation = self.build_clock_chain(
            nonce_hash=_hash("wrong-nonce")
        )
        evidence = self.evaluate(
            clock_attestation=attestation,
            clock_receipts=receipts,
            expected_clock_receipt_hashes=expected,
            expected_clock_attestation_hash=attestation["attestation_hash"],
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertFalse(evidence["facts"]["clock_attestation_exact"])

    def test_reference_time_outside_declared_window_is_blocked(self) -> None:
        receipts, expected, attestation = self.build_clock_chain(
            observed=(1_013_000, 1_013_020),
            verification_time_ms=1_013_500,
        )
        evidence = self.evaluate(
            clock_attestation=attestation,
            clock_receipts=receipts,
            expected_clock_receipt_hashes=expected,
            expected_clock_attestation_hash=attestation["attestation_hash"],
            clock_verification_time_ms=1_013_500,
        )
        self.assertTrue(evidence["facts"]["clock_attestation_exact"])
        self.assertFalse(
            evidence["facts"]["reference_time_inside_declared_challenge_window"]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_independently_valid_wrong_provider_challenge_pair_is_blocked(self) -> None:
        alternate = self.build_provider_bundle(
            _hash("unrelated-signed-challenge"),
            self.registration_nonce_hash,
        )
        alternate_handoff = self.build_handoff(alternate)
        self.assertEqual(alternate["evidence"]["status"], "PASS")
        self.assertEqual(alternate_handoff["status"], "BLOCK")
        evidence = self.evaluate(
            provider_bundle=alternate,
            handoff_evidence=alternate_handoff,
            expected_handoff_evidence_hash=alternate_handoff[
                "handoff_evidence_hash"
            ],
        )
        self.assertTrue(evidence["facts"]["handoff_evidence_exact"])
        self.assertFalse(evidence["facts"]["dual_signature_handoff_verified"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_receipt_signature_tamper_is_blocked(self) -> None:
        receipts = deepcopy(self.clock_receipts)
        receipts[0]["signature"]["signature_base64"] = _b64(b"0" * 64)
        evidence = self.evaluate(clock_receipts=receipts)
        self.assertFalse(evidence["facts"]["clock_attestation_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_resealed_current_time_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.clock_attestation)
        forged.pop("attestation_hash")
        forged["facts"]["current_time_established"] = True
        forged = seal_strict_canonical_document(forged, "attestation_hash")
        evidence = self.evaluate(
            clock_attestation=forged,
            expected_clock_attestation_hash=forged["attestation_hash"],
        )
        self.assertFalse(evidence["facts"]["clock_attestation_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_handoff_freshness_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.handoff_evidence)
        forged["facts"]["challenge_freshness_verified"] = True
        evidence = self.evaluate(handoff_evidence=forged)
        self.assertFalse(evidence["facts"]["handoff_evidence_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_expected_hash_drift_is_blocked(self) -> None:
        self.assertEqual(
            self.evaluate(expected_clock_attestation_hash="0" * 64)["status"],
            "BLOCK",
        )
        self.assertEqual(
            self.evaluate(expected_handoff_evidence_hash="1" * 64)["status"],
            "BLOCK",
        )

    def test_public_verifier_rebuilds_and_rejects_mutation(self) -> None:
        evidence = self.evaluate()
        bundle = self.provider_bundle
        args = (
            self.clock_attestation,
            self.clock_registration,
            self.clock_receipts,
            self.clock_public_keys,
            self.handoff_evidence,
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
            "expected_clock_attestation_hash": self.clock_attestation[
                "attestation_hash"
            ],
            "expected_clock_registration_hash": self.clock_registration[
                "registration_hash"
            ],
            "expected_clock_receipt_hashes": self.expected_receipt_hashes,
            "clock_verification_time_ms": 1_010_500,
            "expected_handoff_evidence_hash": self.handoff_evidence[
                "handoff_evidence_hash"
            ],
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
            binding.verify_challenge_consumption_provider_registration_clock_binding_v1(
                evidence,
                *args,
                expected_clock_binding_evidence_hash=evidence[
                    "clock_binding_evidence_hash"
                ],
                **kwargs,
            )
        )
        mutated = deepcopy(evidence)
        mutated["facts"]["challenge_freshness_verified"] = True
        self.assertFalse(
            binding.verify_challenge_consumption_provider_registration_clock_binding_v1(
                mutated,
                *args,
                expected_clock_binding_evidence_hash=evidence[
                    "clock_binding_evidence_hash"
                ],
                **kwargs,
            )
        )

    def test_evidence_redacts_clock_challenge_and_provider_material(self) -> None:
        encoded = json.dumps(self.evaluate(), sort_keys=True)
        for raw_key in self.clock_public_keys.values():
            self.assertNotIn(raw_key, encoded)
        for receipt in self.clock_receipts:
            self.assertNotIn(receipt["signature"]["signature_base64"], encoded)
        for material in (
            _b64(self.challenge_spki),
            _b64(self.challenge_signature),
            _b64(self.provider_spki),
            _b64(self.provider_bundle["signature"]),
        ):
            self.assertNotIn(material, encoded)

    def test_output_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        before = deepcopy(
            [
                self.clock_attestation,
                self.clock_registration,
                self.clock_receipts,
                self.clock_public_keys,
                self.handoff_evidence,
                self.challenge_evidence,
            ]
        )
        self.assertEqual(self.evaluate(), self.evaluate())
        self.assertEqual(
            before,
            [
                self.clock_attestation,
                self.clock_registration,
                self.clock_receipts,
                self.clock_public_keys,
                self.handoff_evidence,
                self.challenge_evidence,
            ],
        )

    def test_bool_verification_time_alias_is_blocked(self) -> None:
        evidence = self.evaluate(clock_verification_time_ms=True)
        self.assertFalse(evidence["facts"]["clock_attestation_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_production_has_no_private_key_io_clock_or_runtime_access(self) -> None:
        source = Path(binding.__file__).read_text(encoding="utf-8")
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
            ".consume_once(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
