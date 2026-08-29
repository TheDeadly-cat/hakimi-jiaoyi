from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import unittest

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_publication_consumer_v1 as publication,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class _SyntheticProvider:
    def __init__(self, base_head, *, mode: str = "published") -> None:
        self.current = base_head
        self.mode = mode
        self.publish_calls = 0
        self.read_calls = 0
        self.last_request = None

    @staticmethod
    def _candidate(request):
        manifest = request.candidate_manifest
        return publication.build_witness_ownership_key_revocation_snapshot_publication_head_v1(
            stream_id=request.stream_id,
            revision=manifest.revision,
            snapshot_hash=manifest.snapshot_hash,
            publication_manifest_hash=manifest.publication_manifest_hash,
        )

    @staticmethod
    def _alternate(request, *, revision: int = 1):
        return publication.build_witness_ownership_key_revocation_snapshot_publication_head_v1(
            stream_id=request.stream_id,
            revision=revision,
            snapshot_hash=_hash(f"alternate-snapshot-{revision}"),
            publication_manifest_hash=_hash(f"alternate-manifest-{revision}"),
        )

    def compare_and_swap_publish(self, request):
        self.publish_calls += 1
        self.last_request = request
        if self.mode == "exception":
            raise RuntimeError("synthetic provider failure")
        if self.mode == "malformed_receipt":
            return {"outcome": "PUBLISHED"}

        candidate = self._candidate(request)
        if self.mode == "already_current":
            self.current = candidate
            receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
                request,
                self.current,
                self.current,
                outcome=publication.OUTCOME_ALREADY_CURRENT,
                provider_content_addressed_object_claimed=True,
                provider_atomic_head_compare_and_swap_claimed=False,
                provider_durable_commit_claimed=True,
            )
        elif self.mode in {"conflict", "same_revision_conflict"}:
            self.current = self._alternate(request)
            receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
                request,
                self.current,
                self.current,
                outcome=publication.OUTCOME_HEAD_CONFLICT,
                provider_content_addressed_object_claimed=False,
                provider_atomic_head_compare_and_swap_claimed=False,
                provider_durable_commit_claimed=False,
            )
        elif self.mode == "blocked":
            receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
                request,
                self.current,
                self.current,
                outcome=publication.OUTCOME_BLOCK,
                provider_content_addressed_object_claimed=False,
                provider_atomic_head_compare_and_swap_claimed=False,
                provider_durable_commit_claimed=False,
            )
        else:
            observed = self.current
            self.current = candidate
            receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
                request,
                observed,
                candidate,
                outcome=publication.OUTCOME_PUBLISHED,
                provider_content_addressed_object_claimed=True,
                provider_atomic_head_compare_and_swap_claimed=True,
                provider_durable_commit_claimed=True,
            )

        if self.mode == "tampered_receipt":
            return replace(receipt, request_hash=_hash("wrong-request"))
        if self.mode == "false_atomic_claim":
            return replace(
                receipt,
                provider_atomic_head_compare_and_swap_claimed=False,
            )
        return receipt

    def read_current_head(self, *, stream_id: str):
        self.read_calls += 1
        if self.mode == "read_exception":
            raise RuntimeError("synthetic read failure")
        if self.mode == "malformed_post_read":
            return {"stream_id": stream_id}
        if self.mode == "post_read_mismatch":
            return self._alternate(self.last_request, revision=2)
        return self.current


class WitnessOwnershipKeyRevocationSnapshotPublicationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stream_id = "witness-provider-key-revocations"
        self.snapshot_hash = _hash("snapshot-v1")
        self.source_evaluation_hash = _hash("source-evaluation-v1")
        self.request_nonce_hash = _hash("request-nonce-v1")
        self.base_head = publication.build_witness_ownership_key_revocation_snapshot_publication_head_v1(
            stream_id=self.stream_id,
            revision=0,
            snapshot_hash=None,
            publication_manifest_hash=None,
        )
        self.assertIsNotNone(self.base_head)

    def _publish(self, provider, **overrides):
        values = {
            "candidate_revision": 1,
            "candidate_snapshot_hash": self.snapshot_hash,
            "candidate_source_evaluation_hash": self.source_evaluation_hash,
            "request_nonce_hash": self.request_nonce_hash,
            "expected_base_head_hash": self.base_head.head_hash,
            "expected_stream_id": self.stream_id,
        }
        values.update(overrides)
        return publication.publish_witness_ownership_key_revocation_snapshot_v1(
            provider,
            self.base_head,
            **values,
        )

    def _request(self, **overrides):
        values = {
            "candidate_revision": 1,
            "candidate_snapshot_hash": self.snapshot_hash,
            "candidate_source_evaluation_hash": self.source_evaluation_hash,
            "request_nonce_hash": self.request_nonce_hash,
            "expected_base_head_hash": self.base_head.head_hash,
            "expected_stream_id": self.stream_id,
        }
        values.update(overrides)
        return publication.build_witness_ownership_key_revocation_snapshot_publication_request_v1(
            self.base_head,
            **values,
        )

    def test_head_and_manifest_are_content_addressed(self) -> None:
        manifest = publication.build_witness_ownership_key_revocation_snapshot_publication_manifest_v1(
            stream_id=self.stream_id,
            revision=1,
            snapshot_hash=self.snapshot_hash,
            source_evaluation_hash=self.source_evaluation_hash,
        )
        repeated = publication.build_witness_ownership_key_revocation_snapshot_publication_manifest_v1(
            stream_id=self.stream_id,
            revision=1,
            snapshot_hash=self.snapshot_hash,
            source_evaluation_hash=self.source_evaluation_hash,
        )
        self.assertEqual(manifest, repeated)
        self.assertRegex(manifest.publication_manifest_hash, r"^[0-9a-f]{64}$")
        self.assertRegex(self.base_head.head_hash, r"^[0-9a-f]{64}$")

    def test_invalid_head_shapes_are_rejected(self) -> None:
        builder = publication.build_witness_ownership_key_revocation_snapshot_publication_head_v1
        self.assertIsNone(
            builder(
                stream_id=self.stream_id,
                revision=True,
                snapshot_hash=None,
                publication_manifest_hash=None,
            )
        )
        self.assertIsNone(
            builder(
                stream_id=self.stream_id,
                revision=1,
                snapshot_hash=None,
                publication_manifest_hash=None,
            )
        )

    def test_request_requires_strictly_next_revision(self) -> None:
        self.assertIsNone(self._request(candidate_revision=2))

    def test_request_nonce_changes_request_not_manifest(self) -> None:
        first = self._request()
        second = self._request(request_nonce_hash=_hash("request-nonce-v2"))
        self.assertEqual(first.candidate_manifest, second.candidate_manifest)
        self.assertNotEqual(first.request_hash, second.request_hash)

    def test_published_head_is_observed_but_gate_stays_unknown(self) -> None:
        provider = _SyntheticProvider(self.base_head)
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_PUBLISHED_CURRENT_OBSERVED)
        self.assertEqual(result.gate_status, publication.GATE_STATUS_UNKNOWN)
        self.assertEqual(result.blocker_codes, ())
        self.assertEqual((provider.publish_calls, provider.read_calls), (1, 1))
        self.assertTrue(result.post_read_current_head_observed)
        self.assertTrue(result.provider_reported_publication_performed)

    def test_already_current_is_idempotent_without_republication(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="already_current")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_ALREADY_CURRENT_OBSERVED)
        self.assertEqual((provider.publish_calls, provider.read_calls), (1, 1))
        self.assertFalse(result.provider_reported_publication_performed)
        self.assertFalse(result.provider_atomic_head_compare_and_swap_claimed)

    def test_head_conflict_does_not_retry_or_post_read(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="conflict")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_HEAD_CONFLICT)
        self.assertEqual(result.gate_status, publication.GATE_STATUS_UNKNOWN)
        self.assertEqual(
            result.blocker_codes,
            ("publication_head_compare_and_swap_conflict",),
        )
        self.assertEqual((provider.publish_calls, provider.read_calls), (1, 0))

    def test_same_revision_different_snapshot_is_a_conflict(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="same_revision_conflict")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_HEAD_CONFLICT)
        self.assertNotEqual(result.returned_head_hash, result.base_head_hash)

    def test_provider_block_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="blocked")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_provider_blocked",))
        self.assertEqual(provider.read_calls, 0)

    def test_provider_exception_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="exception")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_provider_exception",))

    def test_malformed_receipt_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="malformed_receipt")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_receipt_invalid",))

    def test_tampered_request_binding_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="tampered_receipt")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_receipt_invalid",))

    def test_false_atomic_claim_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="false_atomic_claim")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_receipt_invalid",))

    def test_post_read_mismatch_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="post_read_mismatch")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_post_read_mismatch",))
        self.assertFalse(result.post_read_current_head_observed)

    def test_malformed_post_read_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="malformed_post_read")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_post_read_invalid",))

    def test_post_read_exception_is_fail_closed(self) -> None:
        provider = _SyntheticProvider(self.base_head, mode="read_exception")
        result = self._publish(provider)
        self.assertEqual(result.status, publication.STATUS_BLOCK)
        self.assertEqual(result.blocker_codes, ("publication_post_read_exception",))

    def test_invalid_expected_bindings_do_not_call_provider(self) -> None:
        provider = _SyntheticProvider(self.base_head)
        result = self._publish(provider, expected_base_head_hash=_hash("wrong-base"))
        self.assertIsNone(result)
        self.assertEqual((provider.publish_calls, provider.read_calls), (0, 0))

    def test_receipt_builder_rejects_equivocating_already_current(self) -> None:
        request = self._request()
        alternate = _SyntheticProvider._alternate(request)
        receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
            request,
            alternate,
            alternate,
            outcome=publication.OUTCOME_ALREADY_CURRENT,
            provider_content_addressed_object_claimed=True,
            provider_atomic_head_compare_and_swap_claimed=False,
            provider_durable_commit_claimed=True,
        )
        self.assertIsNone(receipt)

    def test_receipt_builder_rejects_success_from_wrong_base(self) -> None:
        request = self._request()
        alternate = _SyntheticProvider._alternate(request)
        candidate = _SyntheticProvider._candidate(request)
        receipt = publication.build_witness_ownership_key_revocation_snapshot_publication_receipt_v1(
            request,
            alternate,
            candidate,
            outcome=publication.OUTCOME_PUBLISHED,
            provider_content_addressed_object_claimed=True,
            provider_atomic_head_compare_and_swap_claimed=True,
            provider_durable_commit_claimed=True,
        )
        self.assertIsNone(receipt)

    def test_all_operational_outcomes_keep_execution_locked(self) -> None:
        for mode in ("published", "already_current", "conflict", "blocked"):
            with self.subTest(mode=mode):
                result = self._publish(_SyntheticProvider(self.base_head, mode=mode))
                self.assertEqual(result.permission_state, publication.PERMISSION_STATE_RESEARCH_ONLY)
                self.assertFalse(result.permission)
                self.assertFalse(result.paper_authorized)
                self.assertFalse(result.live_authorized)
                self.assertFalse(result.current_chain_activated)
                self.assertFalse(result.external_persistence_independently_verified)
                self.assertFalse(result.provider_identity_verified)
                self.assertFalse(result.external_source_truth_verified)

    def test_non_ascii_stream_identifier_is_rejected(self) -> None:
        head = publication.build_witness_ownership_key_revocation_snapshot_publication_head_v1(
            stream_id="revocations-\u6d41\u8bd5",
            revision=0,
            snapshot_hash=None,
            publication_manifest_hash=None,
        )
        self.assertIsNone(head)


if __name__ == "__main__":
    unittest.main()
