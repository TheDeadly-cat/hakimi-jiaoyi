from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest

from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_freshness_replay_binding_v1
    as freshness_binding,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_v9_position_derived_snapshot_replay_cursor_cas_binding_v1
    as subject,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1
    as cas_contract,
)
from tests import (
    test_strategy_correlation_cluster_v9_position_derived_snapshot_freshness_replay_binding_v1
    as source_support,
)


class V9PositionDerivedSnapshotReplayCursorCasBindingV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        source_support.V9PositionDerivedSnapshotFreshnessReplayBindingV1Tests.setUpClass()
        cls.fixture = (
            source_support.V9PositionDerivedSnapshotFreshnessReplayBindingV1Tests
        )
        cls.source_context = cls.fixture._kwargs()
        cls.source_result = freshness_binding.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **cls.source_context
        )
        cls.attestation = cls.source_context["attestation"]
        cls.base_cursor = cls.source_context["cursor"]
        cls.request_nonce_hash = "9" * 64

    @classmethod
    def _evaluate(
        cls,
        *,
        source_result=None,
        source_context=None,
        attestation=None,
        base_cursor=None,
        observed_cursor=None,
        expected_observed_cursor_hash=None,
    ):
        source_result = cls.source_result if source_result is None else source_result
        source_context = (
            cls.source_context if source_context is None else source_context
        )
        attestation = cls.attestation if attestation is None else attestation
        base_cursor = cls.base_cursor if base_cursor is None else base_cursor
        observed_cursor = (
            base_cursor if observed_cursor is None else observed_cursor
        )
        return subject.evaluate_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
            source_result,
            deepcopy(source_context),
            attestation,
            base_cursor,
            observed_cursor,
            expected_freshness_binding_hash=source_result.binding_hash,
            request_nonce_hash=cls.request_nonce_hash,
            expected_observed_cursor_hash=(
                observed_cursor.cursor_hash
                if expected_observed_cursor_hash is None
                else expected_observed_cursor_hash
            ),
        )

    def test_prebinding_cas_accepts_unverified_freshness_dataclass(self):
        forged = freshness_gate.IncumbentSnapshotFreshnessReplayResultV1(
            contract_version=freshness_gate.CONTRACT_VERSION,
            status=freshness_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE,
            permission_state="UNAUTHORIZED",
            permission=False,
            research_only=True,
            blocker_codes=(),
            post_merge_result_hash="0" * 64,
            post_merge_status="FORGED_WITHOUT_SOURCE_RECOMPUTATION",
            attestation_hash=self.attestation.attestation_hash,
            reference_hash="1" * 64,
            cursor_hash=self.base_cursor.cursor_hash,
            policy_fingerprint_sha256="2" * 64,
            snapshot_sequence=self.attestation.sequence,
            head_sequence=self.attestation.sequence,
            sequence_lag=0,
            cursor_high_water_sequence=self.base_cursor.high_water_sequence,
            cursor_mutation_performed=False,
        )
        fingerprint = cas_contract.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
            forged
        )
        intent = cas_contract.build_incumbent_snapshot_replay_cursor_cas_transition_intent_v1(
            forged,
            self.attestation,
            self.base_cursor,
            request_nonce_hash="8" * 64,
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=self.attestation.attestation_hash,
            expected_cursor_hash=self.base_cursor.cursor_hash,
        )
        self.assertIsNotNone(intent)
        self.assertNotIn("freshness_result", subject.__all__)

    def test_exact_source_builds_uncommitted_returned_cursor_candidate(self):
        result = self._evaluate()
        self.assertEqual(
            result.status,
            subject.STATUS_UNCOMMITTED_RETURNED_CURSOR_CANDIDATE,
        )
        self.assertEqual(
            result.outcome,
            cas_contract.OUTCOME_ADVANCED_IN_RETURNED_CURSOR,
        )
        self.assertTrue(result.returned_cursor_changed)
        self.assertEqual(
            result.returned_high_water_sequence,
            self.attestation.sequence,
        )
        self.assertIn(
            self.attestation.attestation_hash,
            result.returned_cursor.consumed_attestation_hashes,
        )
        self.assertTrue(result.freshness_result_reconstructed_from_source_binding)

    def test_changed_observed_cursor_returns_cas_conflict_unknown(self):
        extra_hash = "0" * 64
        if extra_hash in self.base_cursor.consumed_attestation_hashes:
            extra_hash = "1" * 64
        observed = freshness_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.base_cursor.high_water_sequence,
            high_water_attestation_hash=(
                self.base_cursor.high_water_attestation_hash
            ),
            consumed_attestation_hashes=tuple(
                sorted(
                    self.base_cursor.consumed_attestation_hashes
                    + (extra_hash,)
                )
            ),
        )
        result = self._evaluate(observed_cursor=observed)
        self.assertEqual(result.status, subject.STATUS_UNKNOWN)
        self.assertEqual(
            result.outcome,
            cas_contract.OUTCOME_COMPARE_AND_SWAP_CONFLICT,
        )
        self.assertFalse(result.returned_cursor_changed)

    def test_returned_candidate_replay_is_blocked_not_committed(self):
        first = self._evaluate()
        replay = self._evaluate(observed_cursor=first.returned_cursor)
        self.assertEqual(replay.status, subject.STATUS_BLOCKED)
        self.assertEqual(
            replay.outcome,
            cas_contract.OUTCOME_ALREADY_CONSUMED,
        )
        self.assertFalse(replay.returned_cursor_changed)

    def test_nonmonotonic_observed_high_water_is_blocked(self):
        other_hash = "0" * 64
        if other_hash == self.attestation.attestation_hash:
            other_hash = "1" * 64
        observed = freshness_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.attestation.sequence,
            high_water_attestation_hash=other_hash,
            consumed_attestation_hashes=tuple(
                sorted(
                    self.base_cursor.consumed_attestation_hashes
                    + (other_hash,)
                )
            ),
        )
        result = self._evaluate(observed_cursor=observed)
        self.assertEqual(result.status, subject.STATUS_BLOCKED)
        self.assertEqual(
            result.outcome,
            cas_contract.OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER,
        )

    def test_blocked_source_binding_cannot_build_cas_intent(self):
        temporal = self.fixture.fixture.temporal(
            self.fixture.snapshot,
            sequence=self.fixture.adapter.snapshot_sequence,
            head=self.fixture.adapter.snapshot_sequence + 2,
            high_water=self.fixture.adapter.snapshot_sequence - 1,
            max_lag=1,
        )
        context = self.fixture._kwargs(temporal)
        blocked = freshness_binding.evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
            **context
        )
        self.assertEqual(blocked.status, freshness_binding.STATUS_BLOCKED_BOUND_SNAPSHOT)
        self.assertIsNone(
            self._evaluate(source_result=blocked, source_context=context)
        )

    def test_source_binding_context_and_observed_hash_are_exact(self):
        promoted = replace(self.source_result, paper_authorized=True)
        self.assertIsNone(self._evaluate(source_result=promoted))
        self.assertIsNone(
            self._evaluate(expected_observed_cursor_hash="0" * 64)
        )
        context = deepcopy(self.source_context)
        context["cursor"] = self._evaluate().returned_cursor
        self.assertIsNone(self._evaluate(source_context=context))

    def test_invalid_temporal_objects_fail_closed_without_attribute_error(self):
        for index, values in enumerate(
            (
                (object(), self.base_cursor, self.base_cursor),
                (self.attestation, object(), self.base_cursor),
                (self.attestation, self.base_cursor, object()),
            )
        ):
            with self.subTest(index=index):
                attestation, base_cursor, observed_cursor = values
                self.assertIsNone(
                    subject.evaluate_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
                        self.source_result,
                        deepcopy(self.source_context),
                        attestation,
                        base_cursor,
                        observed_cursor,
                        expected_freshness_binding_hash=(
                            self.source_result.binding_hash
                        ),
                        request_nonce_hash=self.request_nonce_hash,
                        expected_observed_cursor_hash=self.base_cursor.cursor_hash,
                    )
                )

    def test_returned_cursor_is_never_described_as_persisted_or_committed(self):
        result = self._evaluate()
        self.assertFalse(result.observed_cursor_provider_registered)
        self.assertFalse(result.observed_cursor_source_truth_verified)
        self.assertFalse(result.consume_once_verified)
        self.assertFalse(result.atomic_storage_commit_verified)
        self.assertFalse(result.durable_commit_verified)
        self.assertFalse(result.linearizable_read_verified)
        self.assertFalse(result.replay_registry_persistence_verified)
        self.assertFalse(result.cursor_write_performed)
        self.assertFalse(result.runtime_consumer_bound)
        self.assertFalse(result.current_admission_allowed)
        self.assertFalse(result.paper_authorized)
        self.assertFalse(result.live_order_allowed)
        self.assertFalse(result.profitability_proven)
        self.assertFalse(result.permission)

    def test_exact_verifier_rejects_authority_promotion(self):
        result = self._evaluate()
        self.assertTrue(
            subject.verify_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
                result,
                self.source_result,
                deepcopy(self.source_context),
                self.attestation,
                self.base_cursor,
                self.base_cursor,
                expected_freshness_binding_hash=self.source_result.binding_hash,
                request_nonce_hash=self.request_nonce_hash,
                expected_observed_cursor_hash=self.base_cursor.cursor_hash,
            )
        )
        self.assertFalse(
            subject.verify_v9_position_derived_snapshot_replay_cursor_cas_binding_v1(
                replace(result, atomic_storage_commit_verified=True),
                self.source_result,
                deepcopy(self.source_context),
                self.attestation,
                self.base_cursor,
                self.base_cursor,
                expected_freshness_binding_hash=self.source_result.binding_hash,
                request_nonce_hash=self.request_nonce_hash,
                expected_observed_cursor_hash=self.base_cursor.cursor_hash,
            )
        )

    def test_result_is_deterministic_redacted_and_bounded(self):
        one = self._evaluate()
        two = self._evaluate()
        self.assertEqual(one, two)
        rendered = repr(one)
        self.assertLess(len(rendered), 7000)
        self.assertNotIn("v9_verification_context", rendered)
        self.assertNotIn("clock_receipts", rendered)

    def test_production_binding_has_no_storage_provider_runtime_or_io_api(self):
        source = Path(subject.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "requests.",
            "urllib.",
            "socket.",
            "sqlite3",
            "subprocess",
            "commit_cursor",
            "save_cursor",
            "advance_cursor",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
