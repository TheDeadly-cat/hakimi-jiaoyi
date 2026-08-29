from __future__ import annotations

import base64
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    challenge_consumption_provider_bootstrap_topology_v1 as bootstrap,
)
from exchange_terminal.application import (
    challenge_consumption_provider_threshold_genesis_admission_v1 as admission,
)
from tests import (
    test_challenge_consumption_provider_registration_clock_binding_v1 as clock_fixture,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionProviderThresholdGenesisAdmissionV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.upstream = (
            clock_fixture.ChallengeConsumptionProviderRegistrationClockBindingV1Tests(
                methodName="runTest"
            )
        )
        self.upstream.setUp()
        self.provider = self.upstream.provider_preregistration
        self.clock_evidence = self.upstream.evaluate()
        self.clock_args = (
            self.upstream.clock_attestation,
            self.upstream.clock_registration,
            self.upstream.clock_receipts,
            self.upstream.clock_public_keys,
            self.upstream.handoff_evidence,
            self.upstream.challenge_evidence,
            self.upstream.signed_challenge,
            self.upstream.challenge,
            self.provider,
            self.upstream.authority_preregistration,
            self.upstream.provider_bundle["evidence"],
            self.upstream.provider_bundle["signed"],
            self.upstream.provider_bundle["claim"],
        )
        self.clock_kwargs = {
            "expected_clock_attestation_hash": self.upstream.clock_attestation[
                "attestation_hash"
            ],
            "expected_clock_registration_hash": self.upstream.clock_registration[
                "registration_hash"
            ],
            "expected_clock_receipt_hashes": (
                self.upstream.expected_receipt_hashes
            ),
            "clock_verification_time_ms": 1_010_500,
            "expected_handoff_evidence_hash": self.upstream.handoff_evidence[
                "handoff_evidence_hash"
            ],
            "expected_challenge_evidence_hash": self.upstream.challenge_evidence[
                "verification_evidence_hash"
            ],
            "expected_provider_registration_evidence_hash": (
                self.upstream.provider_bundle["evidence"][
                    "verification_evidence_hash"
                ]
            ),
            "challenge_evaluation_kwargs": (
                self.upstream.challenge_evaluation_kwargs
            ),
            "provider_registration_evaluation_kwargs": (
                self.upstream.provider_bundle["evaluation_kwargs"]
            ),
        }

        self.root_private = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]
        self.root_spki = [_spki(key) for key in self.root_private]
        self.root_ids = [
            "synthetic.root.alpha.v1",
            "synthetic.root.bravo.v1",
            "synthetic.root.charlie.v1",
        ]
        self.root_authorities = [
            {
                "authority_id": authority_id,
                "public_key_spki_sha256": sha256(spki).hexdigest(),
                "trust_domain": f"synthetic.root-domain-{index}",
                "governance_implementation_claim_sha256": _hash(
                    f"root-governance-{index}"
                ),
            }
            for index, (authority_id, spki) in enumerate(
                zip(self.root_ids, self.root_spki)
            )
        ]
        self.topology_kwargs = {
            "root_authorities": self.root_authorities,
            "minimum_root_signatures": 2,
            "provider_preregistration_kwargs": self.upstream.provider_kwargs,
        }
        self.topology = (
            bootstrap.build_challenge_consumption_provider_bootstrap_topology_v1(
                self.provider, **self.topology_kwargs
            )
        )
        self.claim_kwargs = {
            "admission_nonce_hash": _hash("genesis-admission-nonce"),
            "expected_genesis_registry_head_hash": _hash(
                "expected-genesis-head"
            ),
            "expected_clock_binding_evidence_hash": self.clock_evidence[
                "clock_binding_evidence_hash"
            ],
            "topology_build_kwargs": self.topology_kwargs,
            "clock_binding_verification_args": self.clock_args,
            "clock_binding_verification_kwargs": self.clock_kwargs,
        }
        self.bundle = self.build_bundle()

    def signature_material(self, claim, indexes=(0, 1)):
        return {
            self.root_ids[index]: {
                "public_key_spki_base64": _b64(self.root_spki[index]),
                "signature_base64": _b64(
                    self.root_private[index].sign(
                        bytes.fromhex(
                            claim["genesis_admission_claim_hash"]
                        )
                    )
                ),
            }
            for index in indexes
        }

    def build_bundle(self, **claim_overrides):
        claim_kwargs = {**self.claim_kwargs, **claim_overrides}
        claim = (
            admission.build_challenge_consumption_provider_genesis_admission_claim_v1(
                self.provider,
                self.topology,
                self.clock_evidence,
                **claim_kwargs,
            )
        )
        signatures = self.signature_material(claim)
        signed = admission.build_threshold_signed_genesis_admission_v1(
            claim,
            self.provider,
            self.topology,
            self.clock_evidence,
            signatures_by_authority_id=signatures,
            expected_claim_hash=claim["genesis_admission_claim_hash"],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "signatures_by_authority_id": signatures,
            "expected_claim_hash": claim["genesis_admission_claim_hash"],
            "expected_signed_admission_hash": signed[
                "signed_genesis_admission_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = admission.evaluate_threshold_signed_genesis_admission_v1(
            signed,
            claim,
            self.provider,
            self.topology,
            self.clock_evidence,
            **evaluation_kwargs,
        )
        replay_key = admission.build_genesis_admission_replay_key_v1(
            evidence,
            signed,
            claim,
            self.provider,
            self.topology,
            self.clock_evidence,
            expected_verification_evidence_hash=evidence[
                "verification_evidence_hash"
            ],
            evaluation_kwargs=evaluation_kwargs,
        )
        return {
            "claim_kwargs": claim_kwargs,
            "claim": claim,
            "signatures": signatures,
            "signed": signed,
            "evaluation_kwargs": evaluation_kwargs,
            "evidence": evidence,
            "replay_key": replay_key,
        }

    def evaluate_with_signatures(self, signatures):
        signed = admission.build_threshold_signed_genesis_admission_v1(
            self.bundle["claim"],
            self.provider,
            self.topology,
            self.clock_evidence,
            signatures_by_authority_id=signatures,
            expected_claim_hash=self.bundle["claim"][
                "genesis_admission_claim_hash"
            ],
            claim_build_kwargs=self.claim_kwargs,
        )
        return admission.evaluate_threshold_signed_genesis_admission_v1(
            signed,
            self.bundle["claim"],
            self.provider,
            self.topology,
            self.clock_evidence,
            signatures_by_authority_id=signatures,
            expected_claim_hash=self.bundle["claim"][
                "genesis_admission_claim_hash"
            ],
            expected_signed_admission_hash=signed[
                "signed_genesis_admission_hash"
            ],
            claim_build_kwargs=self.claim_kwargs,
        )

    def test_claim_is_exact_blocked_and_binds_upstream_hashes(self) -> None:
        claim = self.bundle["claim"]
        self.assertEqual(claim["status"], "BLOCKED")
        self.assertEqual(
            claim["source"]["bootstrap_topology_hash"],
            self.topology["bootstrap_topology_hash"],
        )
        self.assertEqual(
            claim["source"]["clock_binding_evidence_hash"],
            self.clock_evidence["clock_binding_evidence_hash"],
        )
        self.assertFalse(claim["facts"]["trusted_current_time_established"])
        self.assertTrue(
            admission.verify_challenge_consumption_provider_genesis_admission_claim_v1(
                claim,
                self.provider,
                self.topology,
                self.clock_evidence,
                expected_genesis_admission_claim_hash=claim[
                    "genesis_admission_claim_hash"
                ],
                **self.claim_kwargs,
            )
        )

    def test_valid_strict_majority_signatures_are_local_pass_only(self) -> None:
        evidence = self.bundle["evidence"]
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["facts"]["threshold_root_signatures_verified"])
        self.assertTrue(evidence["facts"]["strict_majority_threshold_met"])
        self.assertEqual(
            evidence["threshold_observation"]["valid_registered_signer_count"],
            2,
        )
        self.assertEqual(evidence["admission_status"], "BLOCKED")
        self.assertFalse(evidence["facts"]["provider_registered"])
        self.assertFalse(evidence["facts"]["genesis_admission_replay_reserved"])
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_one_signature_below_threshold_is_blocked(self) -> None:
        evidence = self.evaluate_with_signatures(
            self.signature_material(self.bundle["claim"], indexes=(0,))
        )
        self.assertFalse(evidence["facts"]["strict_majority_threshold_met"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_wrong_key_self_signature_under_root_id_is_blocked(self) -> None:
        wrong = Ed25519PrivateKey.generate()
        wrong_spki = _spki(wrong)
        signatures = deepcopy(self.bundle["signatures"])
        signatures[self.root_ids[0]] = {
            "public_key_spki_base64": _b64(wrong_spki),
            "signature_base64": _b64(
                wrong.sign(
                    bytes.fromhex(
                        self.bundle["claim"]["genesis_admission_claim_hash"]
                    )
                )
            ),
        }
        evidence = self.evaluate_with_signatures(signatures)
        self.assertEqual(
            evidence["threshold_observation"]["cryptographic_signature_count"],
            2,
        )
        self.assertEqual(
            evidence["threshold_observation"]["registered_key_match_count"],
            1,
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_outsider_signer_is_blocked(self) -> None:
        outsider = Ed25519PrivateKey.generate()
        signatures = deepcopy(self.bundle["signatures"])
        signatures.pop(self.root_ids[0])
        signatures["synthetic.root.outsider.v1"] = {
            "public_key_spki_base64": _b64(_spki(outsider)),
            "signature_base64": _b64(
                outsider.sign(
                    bytes.fromhex(
                        self.bundle["claim"]["genesis_admission_claim_hash"]
                    )
                )
            ),
        }
        self.assertEqual(
            self.evaluate_with_signatures(signatures)["status"], "BLOCK"
        )

    def test_tampered_signature_is_blocked(self) -> None:
        signatures = deepcopy(self.bundle["signatures"])
        material = signatures[self.root_ids[0]]
        raw = bytearray(base64.b64decode(material["signature_base64"]))
        raw[0] ^= 1
        material["signature_base64"] = _b64(bytes(raw))
        self.assertEqual(
            self.evaluate_with_signatures(signatures)["status"], "BLOCK"
        )

    def test_resealed_duplicate_signer_record_is_rejected(self) -> None:
        forged = deepcopy(self.bundle["signed"])
        forged.pop("signed_genesis_admission_hash")
        forged["signatures"].append(deepcopy(forged["signatures"][0]))
        forged["claimed_signer_count"] += 1
        from exchange_terminal.services.strict_canonical_json_hash import (
            seal_strict_canonical_document,
        )
        forged = seal_strict_canonical_document(
            forged, "signed_genesis_admission_hash"
        )
        evidence = admission.evaluate_threshold_signed_genesis_admission_v1(
            forged,
            self.bundle["claim"],
            self.provider,
            self.topology,
            self.clock_evidence,
            **{
                **self.bundle["evaluation_kwargs"],
                "expected_signed_admission_hash": forged[
                    "signed_genesis_admission_hash"
                ],
            },
        )
        self.assertFalse(evidence["facts"]["signed_admission_document_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_forged_claim_governance_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.bundle["claim"])
        forged["facts"]["external_root_governance_verified"] = True
        evidence = admission.evaluate_threshold_signed_genesis_admission_v1(
            self.bundle["signed"],
            forged,
            self.provider,
            self.topology,
            self.clock_evidence,
            **self.bundle["evaluation_kwargs"],
        )
        self.assertFalse(evidence["facts"]["genesis_admission_claim_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_clock_binding_mutation_and_hash_drift_are_rejected(self) -> None:
        forged_clock = deepcopy(self.clock_evidence)
        forged_clock["facts"]["challenge_freshness_verified"] = True
        with self.assertRaisesRegex(
            admission.ChallengeConsumptionProviderThresholdGenesisAdmissionError,
            "clock binding evidence",
        ):
            admission.build_challenge_consumption_provider_genesis_admission_claim_v1(
                self.provider,
                self.topology,
                forged_clock,
                **self.claim_kwargs,
            )
        with self.assertRaises(
            admission.ChallengeConsumptionProviderThresholdGenesisAdmissionError
        ):
            admission.build_challenge_consumption_provider_genesis_admission_claim_v1(
                self.provider,
                self.topology,
                self.clock_evidence,
                **{
                    **self.claim_kwargs,
                    "expected_clock_binding_evidence_hash": "0" * 64,
                },
            )

    def test_topology_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.topology)
        drifted["status"] = "PASS"
        with self.assertRaisesRegex(
            admission.ChallengeConsumptionProviderThresholdGenesisAdmissionError,
            "topology is not exact",
        ):
            admission.build_challenge_consumption_provider_genesis_admission_claim_v1(
                self.provider,
                drifted,
                self.clock_evidence,
                **self.claim_kwargs,
            )

    def test_replay_key_is_exact_independent_and_unreserved(self) -> None:
        replay_key = self.bundle["replay_key"]
        self.assertEqual(replay_key["status"], "BLOCKED")
        self.assertFalse(replay_key["facts"]["replay_key_reserved"])
        self.assertEqual(
            replay_key["source"]["signed_genesis_admission_hash"],
            self.bundle["signed"]["signed_genesis_admission_hash"],
        )
        self.assertTrue(
            admission.verify_genesis_admission_replay_key_v1(
                replay_key,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.bundle["claim"],
                self.provider,
                self.topology,
                self.clock_evidence,
                expected_genesis_admission_replay_key_hash=replay_key[
                    "genesis_admission_replay_key_hash"
                ],
                expected_verification_evidence_hash=self.bundle["evidence"][
                    "verification_evidence_hash"
                ],
                evaluation_kwargs=self.bundle["evaluation_kwargs"],
            )
        )

    def test_replay_key_changes_with_admission_nonce(self) -> None:
        changed = self.build_bundle(
            admission_nonce_hash=_hash("changed-genesis-admission-nonce")
        )
        self.assertNotEqual(
            changed["replay_key"]["genesis_admission_replay_key_hash"],
            self.bundle["replay_key"]["genesis_admission_replay_key_hash"],
        )

    def test_evidence_and_replay_key_redact_raw_material(self) -> None:
        encoded = json.dumps(
            [self.bundle["evidence"], self.bundle["replay_key"]],
            sort_keys=True,
        )
        for spki in self.root_spki:
            self.assertNotIn(_b64(spki), encoded)
        for material in self.bundle["signatures"].values():
            self.assertNotIn(material["signature_base64"], encoded)

    def test_malformed_or_non_ed25519_public_key_is_rejected(self) -> None:
        for value in (
            "not-base64",
            _b64(_spki(ec.generate_private_key(ec.SECP256R1()))),
        ):
            signatures = deepcopy(self.bundle["signatures"])
            signatures[self.root_ids[0]]["public_key_spki_base64"] = value
            with self.assertRaises(
                admission.ChallengeConsumptionProviderThresholdGenesisAdmissionError
            ):
                admission.build_threshold_signed_genesis_admission_v1(
                    self.bundle["claim"],
                    self.provider,
                    self.topology,
                    self.clock_evidence,
                    signatures_by_authority_id=signatures,
                    expected_claim_hash=self.bundle["claim"][
                        "genesis_admission_claim_hash"
                    ],
                    claim_build_kwargs=self.claim_kwargs,
                )

    def test_production_has_no_private_key_io_provider_or_runtime(self) -> None:
        source = Path(admission.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            ".consume_once(",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
            "time.time",
            "datetime.now",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
