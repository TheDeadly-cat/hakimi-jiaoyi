from __future__ import annotations

import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_replay_snapshot_gate_v1 import (
    build_nonce_replay_key_v1,
    build_nonce_replay_snapshot_v1,
    evaluate_nonce_replay_snapshot_gate_v1,
)


def _sha(character: str) -> str:
    return character * 64


class NonceReplaySnapshotGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.observed = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("a"),
            reviewer_key_sha256=_sha("b"),
            review_nonce_hash=_sha("c"),
        )
        self.snapshot = build_nonce_replay_snapshot_v1(entries=[self.observed])

    def test_replay_key_uses_shared_strict_canonical_hash(self) -> None:
        unsealed = dict(self.observed)
        actual_hash = unsealed.pop("replay_key_hash")
        self.assertEqual(actual_hash, strict_canonical_hash(unsealed))

    def test_replay_key_rejects_noncanonical_hashes(self) -> None:
        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            build_nonce_replay_key_v1(
                signed_attestation_hash=_sha("A"),
                reviewer_key_sha256=_sha("b"),
                review_nonce_hash=_sha("c"),
            )

    def test_snapshot_sorts_entries_deterministically(self) -> None:
        second = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("d"),
            reviewer_key_sha256=_sha("e"),
            review_nonce_hash=_sha("f"),
        )
        forward = build_nonce_replay_snapshot_v1(entries=[self.observed, second])
        reverse = build_nonce_replay_snapshot_v1(entries=[second, self.observed])
        self.assertEqual(forward, reverse)

    def test_snapshot_rejects_duplicate_replay_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate replay keys"):
            build_nonce_replay_snapshot_v1(entries=[self.observed, self.observed])

    def test_exact_signed_attestation_replay_blocks(self) -> None:
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=self.observed,
            replay_snapshot=self.snapshot,
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["gate_status"], "BLOCK")
        self.assertEqual(
            receipt["reason_code"], "SIGNED_ATTESTATION_REPLAY_OBSERVED"
        )
        self.assertTrue(receipt["exact_signed_attestation_seen"])

    def test_reviewer_nonce_reuse_with_new_attestation_blocks(self) -> None:
        candidate = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("d"),
            reviewer_key_sha256=_sha("b"),
            review_nonce_hash=_sha("c"),
        )
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=candidate,
            replay_snapshot=self.snapshot,
        )
        self.assertEqual(receipt["gate_status"], "BLOCK")
        self.assertEqual(receipt["reason_code"], "REVIEWER_NONCE_REUSE_OBSERVED")
        self.assertFalse(receipt["exact_signed_attestation_seen"])
        self.assertTrue(receipt["reviewer_nonce_seen"])

    def test_snapshot_absence_remains_unknown(self) -> None:
        candidate = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("d"),
            reviewer_key_sha256=_sha("e"),
            review_nonce_hash=_sha("f"),
        )
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=candidate,
            replay_snapshot=self.snapshot,
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["gate_status"], "UNKNOWN")
        self.assertFalse(receipt["absence_authorizes_progression"])

    def test_empty_snapshot_does_not_authorize_novelty(self) -> None:
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=self.observed,
            replay_snapshot=build_nonce_replay_snapshot_v1(entries=[]),
        )
        self.assertEqual(receipt["gate_status"], "UNKNOWN")
        self.assertEqual(
            receipt["reason_code"],
            "SNAPSHOT_ABSENCE_NOT_AUTHENTICATED_OR_DURABLE",
        )

    def test_tampered_snapshot_is_unknown(self) -> None:
        tampered = dict(self.snapshot)
        tampered["entry_count"] = 0
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=self.observed,
            replay_snapshot=tampered,
        )
        self.assertEqual(receipt["status"], "UNKNOWN")
        self.assertEqual(receipt["gate_status"], "UNKNOWN")
        self.assertEqual(receipt["reason_code"], "INVALID_REPLAY_SNAPSHOT")

    def test_tampered_candidate_is_unknown(self) -> None:
        tampered = dict(self.observed)
        tampered["review_nonce_hash"] = _sha("d")
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=tampered,
            replay_snapshot=self.snapshot,
        )
        self.assertEqual(receipt["status"], "UNKNOWN")
        self.assertEqual(receipt["reason_code"], "INVALID_CANDIDATE_REPLAY_KEY")

    def test_gate_status_never_passes(self) -> None:
        fresh = build_nonce_replay_key_v1(
            signed_attestation_hash=_sha("d"),
            reviewer_key_sha256=_sha("e"),
            review_nonce_hash=_sha("f"),
        )
        receipts = [
            evaluate_nonce_replay_snapshot_gate_v1(
                candidate_replay_key=self.observed,
                replay_snapshot=self.snapshot,
            ),
            evaluate_nonce_replay_snapshot_gate_v1(
                candidate_replay_key=fresh,
                replay_snapshot=self.snapshot,
            ),
            evaluate_nonce_replay_snapshot_gate_v1(
                candidate_replay_key=fresh,
                replay_snapshot=build_nonce_replay_snapshot_v1(entries=[]),
            ),
        ]
        self.assertNotIn("PASS", {receipt["gate_status"] for receipt in receipts})

    def test_receipt_is_redacted_and_keeps_authority_locked(self) -> None:
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=self.observed,
            replay_snapshot=self.snapshot,
        )
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("public_key", serialized)
        self.assertNotIn("signature", serialized)
        self.assertFalse(receipt["source_authentication_verified"])
        self.assertFalse(receipt["durable_registry_receipt_verified"])
        self.assertFalse(receipt["linearizable_read_verified"])
        self.assertFalse(receipt["http_registered"])
        self.assertFalse(receipt["ui_mounted"])
        self.assertFalse(receipt["current_activated"])
        self.assertFalse(receipt["paper_authorized"])
        self.assertFalse(receipt["live_authorized"])
        self.assertFalse(receipt["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
