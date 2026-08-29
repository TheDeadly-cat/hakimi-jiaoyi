from __future__ import annotations

import base64
import json
import unittest
from copy import deepcopy
from hashlib import sha256

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_atomic_reserve_protocol_v1 import (
    build_nonce_atomic_reserve_request_v1,
    build_nonce_registry_authority_registration_v1,
    build_nonce_registry_synthetic_state_v1,
    build_signed_nonce_reserve_receipt_v1,
    evaluate_signed_nonce_reserve_receipt_v1,
    simulate_nonce_atomic_reserve_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_replay_snapshot_gate_v1 import (
    build_nonce_replay_key_v1,
)


def _sha(character: str) -> str:
    return character * 64


class NonceAtomicReserveProtocolV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay_key = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("a"),
            reviewer_key_sha256=_sha("b"),
            review_nonce_hash=_sha("c"),
        )
        self.genesis = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=[],
            sequence=0,
            previous_registry_head_hash=None,
        )
        self.request = build_nonce_atomic_reserve_request_v1(
            candidate_replay_key=self.replay_key,
            expected_registry_head_hash=self.genesis["registry_head_hash"],
            request_nonce_hash=_sha("d"),
        )
        self.private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_base64 = base64.b64encode(public_key).decode("ascii")
        self.registration = build_nonce_registry_authority_registration_v1(
            registry_authority_id_hash=_sha("e"),
            public_key_base64=self.public_key_base64,
        )

    def _sign(self, receipt: dict[str, object]) -> str:
        signature = self.private_key.sign(
            bytes.fromhex(str(receipt["reserve_transition_receipt_hash"]))
        )
        return base64.b64encode(signature).decode("ascii")

    def test_genesis_state_is_deterministic(self) -> None:
        rebuilt = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=[],
            sequence=0,
            previous_registry_head_hash=None,
        )
        self.assertEqual(self.genesis, rebuilt)
        self.assertFalse(rebuilt["durability_verified"])

    def test_state_sequence_must_match_unique_entry_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "sequence must equal"):
            build_nonce_registry_synthetic_state_v1(
                reserved_replay_key_hashes=[self.replay_key["replay_key_hash"]],
                sequence=0,
                previous_registry_head_hash=None,
            )

    def test_request_rejects_tampered_replay_key(self) -> None:
        tampered = dict(self.replay_key)
        tampered["review_nonce_hash"] = _sha("f")
        with self.assertRaisesRegex(ValueError, "exact replay-key-v1"):
            build_nonce_atomic_reserve_request_v1(
                candidate_replay_key=tampered,
                expected_registry_head_hash=self.genesis["registry_head_hash"],
                request_nonce_hash=_sha("d"),
            )

    def test_matching_head_returns_synthetic_reserved_state(self) -> None:
        result = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        state = result["next_registry_state"]
        receipt = result["transition_receipt"]
        self.assertEqual(state["sequence"], 1)
        self.assertIn(self.replay_key["replay_key_hash"], state["reserved_replay_key_hashes"])
        self.assertEqual(receipt["outcome"], "RESERVED_IN_RETURNED_STATE")
        self.assertEqual(receipt["gate_status"], "UNKNOWN")
        self.assertFalse(receipt["durable_commit_verified"])

    def test_sequential_duplicate_blocks(self) -> None:
        first = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        second = simulate_nonce_atomic_reserve_v1(
            registry_state=first["next_registry_state"],
            reserve_request=self.request,
        )
        receipt = second["transition_receipt"]
        self.assertEqual(receipt["outcome"], "ALREADY_RESERVED")
        self.assertEqual(receipt["gate_status"], "BLOCK")
        self.assertFalse(receipt["state_changed"])

    def test_stale_expected_head_returns_conflict(self) -> None:
        other_key = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("f"),
            reviewer_key_sha256=_sha("1"),
            review_nonce_hash=_sha("2"),
        )
        other_request = build_nonce_atomic_reserve_request_v1(
            candidate_replay_key=other_key,
            expected_registry_head_hash=self.genesis["registry_head_hash"],
            request_nonce_hash=_sha("3"),
        )
        first = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        conflict = simulate_nonce_atomic_reserve_v1(
            registry_state=first["next_registry_state"],
            reserve_request=other_request,
        )
        self.assertEqual(
            conflict["transition_receipt"]["outcome"],
            "COMPARE_AND_SWAP_CONFLICT",
        )
        self.assertEqual(conflict["transition_receipt"]["gate_status"], "UNKNOWN")

    def test_parallel_synthetic_calls_do_not_claim_atomic_storage(self) -> None:
        first = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        second = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        self.assertEqual(first, second)
        self.assertFalse(
            first["transition_receipt"]["atomic_storage_commit_verified"]
        )

    def test_tampered_state_is_rejected(self) -> None:
        tampered = dict(self.genesis)
        tampered["sequence"] = 1
        with self.assertRaisesRegex(ValueError, "exact synthetic-state-v1"):
            simulate_nonce_atomic_reserve_v1(
                registry_state=tampered,
                reserve_request=self.request,
            )

    def test_authority_registration_commits_raw_public_key(self) -> None:
        public_key_bytes = base64.b64decode(self.public_key_base64)
        self.assertEqual(
            self.registration["public_key_sha256"], sha256(public_key_bytes).hexdigest()
        )
        self.assertFalse(self.registration["real_world_identity_verified"])
        self.assertFalse(self.registration["key_governance_verified"])

    def test_valid_signature_verifies_without_durability_promotion(self) -> None:
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )["transition_receipt"]
        signed = build_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition,
            authority_registration=self.registration,
            signature_base64=self._sign(transition),
        )
        evidence = evaluate_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition,
            authority_registration=self.registration,
            signed_receipt=signed,
        )
        self.assertTrue(evidence["signature_verified"])
        self.assertEqual(evidence["gate_status"], "UNKNOWN")
        self.assertFalse(evidence["durable_commit_verified"])

    def test_signed_duplicate_receipt_blocks(self) -> None:
        first = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )
        duplicate = simulate_nonce_atomic_reserve_v1(
            registry_state=first["next_registry_state"],
            reserve_request=self.request,
        )["transition_receipt"]
        signed = build_signed_nonce_reserve_receipt_v1(
            transition_receipt=duplicate,
            authority_registration=self.registration,
            signature_base64=self._sign(duplicate),
        )
        evidence = evaluate_signed_nonce_reserve_receipt_v1(
            transition_receipt=duplicate,
            authority_registration=self.registration,
            signed_receipt=signed,
        )
        self.assertEqual(evidence["gate_status"], "BLOCK")

    def test_wrong_registered_key_is_rejected(self) -> None:
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )["transition_receipt"]
        other_private_key = Ed25519PrivateKey.generate()
        other_public_key = other_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        other_registration = build_nonce_registry_authority_registration_v1(
            registry_authority_id_hash=_sha("f"),
            public_key_base64=base64.b64encode(other_public_key).decode("ascii"),
        )
        with self.assertRaisesRegex(ValueError, "does not verify"):
            build_signed_nonce_reserve_receipt_v1(
                transition_receipt=transition,
                authority_registration=other_registration,
                signature_base64=self._sign(transition),
            )

    def test_tampered_signature_is_rejected(self) -> None:
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )["transition_receipt"]
        signature = bytearray(base64.b64decode(self._sign(transition)))
        signature[0] ^= 1
        with self.assertRaisesRegex(ValueError, "does not verify"):
            build_signed_nonce_reserve_receipt_v1(
                transition_receipt=transition,
                authority_registration=self.registration,
                signature_base64=base64.b64encode(signature).decode("ascii"),
            )

    def test_promoted_transition_is_unknown_even_when_resealed(self) -> None:
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )["transition_receipt"]
        signed = build_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition,
            authority_registration=self.registration,
            signature_base64=self._sign(transition),
        )
        promoted = deepcopy(transition)
        promoted["durable_commit_verified"] = True
        evidence = evaluate_signed_nonce_reserve_receipt_v1(
            transition_receipt=promoted,
            authority_registration=self.registration,
            signed_receipt=signed,
        )
        self.assertEqual(evidence["status"], "UNKNOWN")
        self.assertEqual(evidence["gate_status"], "UNKNOWN")

    def test_evidence_redacts_material_and_keeps_all_locks(self) -> None:
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=self.genesis,
            reserve_request=self.request,
        )["transition_receipt"]
        signature_base64 = self._sign(transition)
        signed = build_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition,
            authority_registration=self.registration,
            signature_base64=signature_base64,
        )
        evidence = evaluate_signed_nonce_reserve_receipt_v1(
            transition_receipt=transition,
            authority_registration=self.registration,
            signed_receipt=signed,
        )
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(self.public_key_base64, serialized)
        self.assertNotIn(signature_base64, serialized)
        for field in (
            "registry_authority_identity_verified",
            "registry_key_governance_verified",
            "registry_source_authenticated",
            "atomic_storage_commit_verified",
            "durable_commit_verified",
            "linearizable_storage_verified",
            "absence_authorizes_progression",
            "http_registered",
            "ui_mounted",
            "current_activated",
            "paper_authorized",
            "live_authorized",
            "profitability_proven",
        ):
            self.assertFalse(evidence[field], field)


if __name__ == "__main__":
    unittest.main()
