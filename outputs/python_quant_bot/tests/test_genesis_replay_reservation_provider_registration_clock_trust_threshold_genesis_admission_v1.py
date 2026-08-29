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
    genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1 as bootstrap,
)
from exchange_terminal.application import (
    genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1 as admission,
)
from exchange_terminal.services import trusted_clock_authority_v3 as clock
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _raw(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ClockTrustThresholdGenesisAdmissionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock_private = [
            Ed25519PrivateKey.generate(),
            Ed25519PrivateKey.generate(),
        ]
        self.clock_raw = [_raw(key) for key in self.clock_private]
        self.clock_authorities = [
            {
                "authority_id": "clock.threshold.a.v1",
                "key_id": "clock.threshold.a.key.v1",
                "public_key_base64": _b64(self.clock_raw[0]),
            },
            {
                "authority_id": "clock.threshold.b.v1",
                "key_id": "clock.threshold.b.key.v1",
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
            item["authority_id"]: item["public_key_base64"]
            for item in self.clock_authorities
        }

        self.time_source_private = Ed25519PrivateKey.generate()
        self.time_source_spki = _spki(self.time_source_private)
        self.time_source_kwargs = {
            "source_id": "synthetic.threshold.time.source.v1",
            "key_id": "synthetic.threshold.time.key.v1",
            "public_key_spki_sha256": sha256(
                self.time_source_spki
            ).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "implementation_claim_sha256": _hash(
                "synthetic-threshold-time-source"
            ),
            "monotonic_epoch_namespace": (
                "synthetic.threshold.time.epoch.v1"
            ),
        }
        self.time_source = (
            bootstrap.build_verification_time_source_preregistration_v1(
                **self.time_source_kwargs
            )
        )

        self.root_ids = (
            "clock.threshold.root.a.v1",
            "clock.threshold.root.b.v1",
            "clock.threshold.root.c.v1",
        )
        self.root_private = {
            authority_id: Ed25519PrivateKey.generate()
            for authority_id in self.root_ids
        }
        self.root_spki = {
            authority_id: _spki(private_key)
            for authority_id, private_key in self.root_private.items()
        }
        self.roots = [
            {
                "authority_id": authority_id,
                "key_id": f"{authority_id}.key",
                "organization_claim": f"synthetic.org.{index}.v1",
                "public_key_spki_sha256": sha256(
                    self.root_spki[authority_id]
                ).hexdigest(),
            }
            for index, authority_id in enumerate(self.root_ids, start=1)
        ]
        self.topology_kwargs = {
            "clock_registration_document": self.clock_registration,
            "clock_public_keys_by_id": self.clock_public_keys,
            "expected_clock_registration_hash": self.clock_registration[
                "registration_hash"
            ],
            "verification_time_source_preregistration_document": (
                self.time_source
            ),
            "verification_time_source_preregistration_kwargs": (
                self.time_source_kwargs
            ),
            "root_authorities": self.roots,
            "minimum_root_signatures": 2,
            "governance_domain": "synthetic.threshold.governance.v1",
            "genesis_policy_hash": _hash("threshold-genesis-policy"),
        }
        self.topology = bootstrap.build_clock_trust_bootstrap_topology_v1(
            **self.topology_kwargs
        )
        self.plan_kwargs = {
            "expected_topology_hash": self.topology["topology_hash"],
            "topology_build_kwargs": self.topology_kwargs,
            "ceremony_id_hash": _hash("threshold-ceremony"),
            "admission_nonce_hash": _hash("threshold-admission-nonce"),
        }
        self.plan = bootstrap.build_clock_trust_genesis_admission_plan_v1(
            self.topology, **self.plan_kwargs
        )
        self.claim_kwargs = {
            "expected_out_of_band_genesis_commitment_hash": _hash(
                "expected-out-of-band-clock-trust-genesis"
            ),
            "topology_build_kwargs": self.topology_kwargs,
            "plan_build_kwargs": self.plan_kwargs,
        }
        self.claim = admission.build_clock_trust_genesis_admission_claim_v1(
            self.topology, self.plan, **self.claim_kwargs
        )
        self.bundle = self.build_bundle()
        self.commitment = admission.build_clock_trust_genesis_commitment_v1(
            self.bundle["evidence"],
            self.bundle["signed"],
            self.claim,
            self.topology,
            self.plan,
            expected_verification_evidence_hash=self.bundle["evidence"][
                "verification_evidence_hash"
            ],
            evaluation_kwargs=self.bundle["evaluation_kwargs"],
        )

    def signature_material(
        self,
        authority_ids=None,
        *,
        claim=None,
    ):
        selected = self.root_ids[:2] if authority_ids is None else authority_ids
        target = self.claim if claim is None else claim
        return {
            authority_id: {
                "public_key_spki_base64": _b64(
                    self.root_spki[authority_id]
                ),
                "signature_base64": _b64(
                    self.root_private[authority_id].sign(
                        bytes.fromhex(
                            target["genesis_admission_claim_hash"]
                        )
                    )
                ),
            }
            for authority_id in selected
        }

    def build_bundle(
        self,
        *,
        claim=None,
        claim_kwargs=None,
        signatures=None,
    ):
        target_claim = self.claim if claim is None else claim
        target_kwargs = (
            self.claim_kwargs if claim_kwargs is None else claim_kwargs
        )
        material = (
            self.signature_material(claim=target_claim)
            if signatures is None
            else signatures
        )
        signed = (
            admission.build_threshold_signed_clock_trust_genesis_admission_v1(
                target_claim,
                self.topology,
                self.plan,
                signatures_by_authority_id=material,
                expected_claim_hash=target_claim[
                    "genesis_admission_claim_hash"
                ],
                claim_build_kwargs=target_kwargs,
            )
        )
        evaluation_kwargs = {
            "signatures_by_authority_id": material,
            "expected_claim_hash": target_claim[
                "genesis_admission_claim_hash"
            ],
            "expected_signed_admission_hash": signed[
                "signed_genesis_admission_hash"
            ],
            "claim_build_kwargs": target_kwargs,
        }
        evidence = (
            admission.evaluate_threshold_signed_clock_trust_genesis_admission_v1(
                signed,
                target_claim,
                self.topology,
                self.plan,
                **evaluation_kwargs,
            )
        )
        return {
            "signed": signed,
            "signatures": material,
            "evaluation_kwargs": evaluation_kwargs,
            "evidence": evidence,
        }

    def test_claim_is_exact_blocked_and_binds_static_commitments(self) -> None:
        self.assertEqual(self.claim["status"], "BLOCKED")
        self.assertEqual(
            self.claim["source"]["topology_hash"],
            self.topology["topology_hash"],
        )
        self.assertEqual(
            self.claim["source"]["plan_hash"], self.plan["plan_hash"]
        )
        self.assertEqual(
            self.claim["source"]["clock_registration_hash"],
            self.clock_registration["registration_hash"],
        )
        self.assertTrue(self.claim["facts"]["claim_bindings_exact"])
        self.assertFalse(
            self.claim["facts"]["threshold_root_signatures_verified"]
        )
        self.assertTrue(
            admission.verify_clock_trust_genesis_admission_claim_v1(
                self.claim,
                self.topology,
                self.plan,
                expected_genesis_admission_claim_hash=self.claim[
                    "genesis_admission_claim_hash"
                ],
                **self.claim_kwargs,
            )
        )

    def test_valid_threshold_signatures_are_local_pass_only(self) -> None:
        evidence = self.bundle["evidence"]
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(
            evidence["facts"]["threshold_root_signatures_verified"]
        )
        self.assertTrue(evidence["facts"]["configured_threshold_met"])
        for name in (
            "external_root_identity_verified",
            "external_root_governance_verified",
            "root_member_independence_verified",
            "out_of_band_genesis_commitment_verified",
            "genesis_commitment_installed",
            "clock_registration_governance_verified",
            "verification_time_source_trusted",
            "trusted_current_time_established",
        ):
            self.assertFalse(evidence["facts"][name], name)
        self.assertTrue(
            all(value is False for value in evidence["authority"].values())
        )

    def test_one_signature_below_threshold_is_blocked(self) -> None:
        material = self.signature_material(self.root_ids[:1])
        evidence = self.build_bundle(signatures=material)["evidence"]
        self.assertFalse(evidence["facts"]["configured_threshold_met"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_wrong_key_self_signature_under_root_id_is_blocked(self) -> None:
        outsider = Ed25519PrivateKey.generate()
        outsider_spki = _spki(outsider)
        material = self.signature_material(self.root_ids[:1])
        material[self.root_ids[1]] = {
            "public_key_spki_base64": _b64(outsider_spki),
            "signature_base64": _b64(
                outsider.sign(
                    bytes.fromhex(
                        self.claim["genesis_admission_claim_hash"]
                    )
                )
            ),
        }
        evidence = self.build_bundle(signatures=material)["evidence"]
        self.assertEqual(
            evidence["threshold_observation"][
                "cryptographic_signature_count"
            ],
            2,
        )
        self.assertEqual(
            evidence["threshold_observation"][
                "registered_key_match_count"
            ],
            1,
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_outsider_signer_is_blocked(self) -> None:
        outsider = Ed25519PrivateKey.generate()
        material = self.signature_material()
        material["clock.threshold.root.outsider.v1"] = {
            "public_key_spki_base64": _b64(_spki(outsider)),
            "signature_base64": _b64(
                outsider.sign(
                    bytes.fromhex(
                        self.claim["genesis_admission_claim_hash"]
                    )
                )
            ),
        }
        evidence = self.build_bundle(signatures=material)["evidence"]
        self.assertFalse(
            evidence["facts"][
                "all_supplied_signatures_cryptographically_and_structurally_valid"
            ]
        )
        self.assertEqual(evidence["status"], "BLOCK")

    def test_tampered_signature_is_blocked(self) -> None:
        material = self.signature_material()
        material[self.root_ids[1]]["signature_base64"] = _b64(b"x" * 64)
        evidence = self.build_bundle(signatures=material)["evidence"]
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertEqual(
            evidence["threshold_observation"][
                "cryptographic_signature_count"
            ],
            1,
        )

    def test_resealed_duplicate_signer_record_is_rejected(self) -> None:
        forged = deepcopy(self.bundle["signed"])
        forged.pop("signed_genesis_admission_hash")
        forged["signatures"].append(deepcopy(forged["signatures"][0]))
        forged["claimed_signer_count"] = len(forged["signatures"])
        forged = seal_strict_canonical_document(
            forged, "signed_genesis_admission_hash"
        )
        kwargs = deepcopy(self.bundle["evaluation_kwargs"])
        kwargs["expected_signed_admission_hash"] = forged[
            "signed_genesis_admission_hash"
        ]
        evidence = (
            admission.evaluate_threshold_signed_clock_trust_genesis_admission_v1(
                forged,
                self.claim,
                self.topology,
                self.plan,
                **kwargs,
            )
        )
        self.assertFalse(evidence["facts"]["signed_admission_document_exact"])
        self.assertEqual(evidence["status"], "BLOCK")

    def test_forged_claim_governance_promotion_is_rejected(self) -> None:
        forged = deepcopy(self.claim)
        forged.pop("genesis_admission_claim_hash")
        forged["facts"]["external_root_governance_verified"] = True
        forged = seal_strict_canonical_document(
            forged, "genesis_admission_claim_hash"
        )
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            admission.build_threshold_signed_clock_trust_genesis_admission_v1(
                forged,
                self.topology,
                self.plan,
                signatures_by_authority_id=self.signature_material(),
                expected_claim_hash=forged[
                    "genesis_admission_claim_hash"
                ],
                claim_build_kwargs=self.claim_kwargs,
            )

    def test_plan_mutation_and_hash_drift_are_rejected(self) -> None:
        plan = deepcopy(self.plan)
        plan["facts"]["ceremony_executed"] = True
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            admission.build_clock_trust_genesis_admission_claim_v1(
                self.topology, plan, **self.claim_kwargs
            )
        drift = deepcopy(self.claim_kwargs)
        drift["plan_build_kwargs"]["expected_topology_hash"] = "0" * 64
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            admission.build_clock_trust_genesis_admission_claim_v1(
                self.topology, self.plan, **drift
            )

    def test_topology_drift_is_rejected(self) -> None:
        topology = deepcopy(self.topology)
        topology["facts"]["root_signatures_verified"] = True
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            admission.build_clock_trust_genesis_admission_claim_v1(
                topology, self.plan, **self.claim_kwargs
            )

    def test_commitment_is_exact_independent_and_uninstalled(self) -> None:
        self.assertEqual(self.commitment["status"], "BLOCKED")
        self.assertTrue(
            self.commitment["facts"]["threshold_admission_evidence_exact"]
        )
        self.assertFalse(
            self.commitment["facts"][
                "out_of_band_genesis_commitment_verified"
            ]
        )
        self.assertFalse(
            self.commitment["facts"]["genesis_commitment_installed"]
        )
        self.assertFalse(self.commitment["facts"]["runtime_mutations"])
        self.assertTrue(
            admission.verify_clock_trust_genesis_commitment_v1(
                self.commitment,
                self.bundle["evidence"],
                self.bundle["signed"],
                self.claim,
                self.topology,
                self.plan,
                expected_genesis_commitment_hash=self.commitment[
                    "genesis_commitment_hash"
                ],
                expected_verification_evidence_hash=self.bundle["evidence"][
                    "verification_evidence_hash"
                ],
                evaluation_kwargs=self.bundle["evaluation_kwargs"],
            )
        )

    def test_commitment_changes_with_expected_out_of_band_hash(self) -> None:
        kwargs = deepcopy(self.claim_kwargs)
        kwargs["expected_out_of_band_genesis_commitment_hash"] = _hash(
            "different-out-of-band-clock-trust-genesis"
        )
        claim = admission.build_clock_trust_genesis_admission_claim_v1(
            self.topology, self.plan, **kwargs
        )
        bundle = self.build_bundle(claim=claim, claim_kwargs=kwargs)
        commitment = admission.build_clock_trust_genesis_commitment_v1(
            bundle["evidence"],
            bundle["signed"],
            claim,
            self.topology,
            self.plan,
            expected_verification_evidence_hash=bundle["evidence"][
                "verification_evidence_hash"
            ],
            evaluation_kwargs=bundle["evaluation_kwargs"],
        )
        self.assertNotEqual(
            self.claim["genesis_admission_claim_hash"],
            claim["genesis_admission_claim_hash"],
        )
        self.assertNotEqual(
            self.commitment["genesis_commitment_hash"],
            commitment["genesis_commitment_hash"],
        )

    def test_evidence_commitment_redaction_determinism_and_input_immutability(self) -> None:
        before = deepcopy(
            [
                self.topology,
                self.plan,
                self.claim,
                self.bundle["signatures"],
            ]
        )
        encoded = json.dumps(
            [self.bundle["evidence"], self.commitment], sort_keys=True
        )
        for authority_id in self.root_ids[:2]:
            material = self.bundle["signatures"][authority_id]
            self.assertNotIn(material["public_key_spki_base64"], encoded)
            self.assertNotIn(material["signature_base64"], encoded)
        rebuilt = (
            admission.evaluate_threshold_signed_clock_trust_genesis_admission_v1(
                self.bundle["signed"],
                self.claim,
                self.topology,
                self.plan,
                **self.bundle["evaluation_kwargs"],
            )
        )
        self.assertEqual(self.bundle["evidence"], rebuilt)
        self.assertEqual(
            before,
            [
                self.topology,
                self.plan,
                self.claim,
                self.bundle["signatures"],
            ],
        )

    def test_malformed_or_non_der_public_key_is_rejected(self) -> None:
        material = self.signature_material()
        material[self.root_ids[0]]["public_key_spki_base64"] = _b64(
            b"x" * 32
        )
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            self.build_bundle(signatures=material)
        material = self.signature_material()
        material[self.root_ids[0]]["public_key_spki_base64"] = "***"
        with self.assertRaises(
            admission.ClockTrustThresholdGenesisAdmissionError
        ):
            self.build_bundle(signatures=material)

    def test_production_has_no_private_key_io_system_clock_replay_or_runtime(self) -> None:
        source = Path(admission.__file__).read_text(encoding="utf-8")
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
            "reserve_once(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
