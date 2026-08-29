from __future__ import annotations

from dataclasses import replace
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as freshness_fixture_module,
)


def _sha(character: str) -> str:
    return character * 64


def _different_hash(*excluded: str | None) -> str:
    for character in "0123456789abcdef":
        candidate = _sha(character)
        if candidate not in excluded:
            return candidate
    raise AssertionError("could not build distinct synthetic hash")


class IncumbentSnapshotReplayCursorCasTransitionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            freshness_fixture_module.IncumbentSnapshotFreshnessReplayGateV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.snapshot = fixture.snapshot()
        cls.temporal = fixture.temporal(cls.snapshot)
        cls.attestation, _, cls.base_cursor, _ = cls.temporal
        cls.proposals = (
            freshness_fixture_module.proposal("cas-proposal", fixture.symbols[0], 200),
        )
        cls.freshness_result = fixture.evaluate(
            cls.proposals,
            cls.snapshot,
            cls.temporal,
        )
        cls.fingerprint = (
            cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
                cls.freshness_result
            )
        )
        if cls.fingerprint is None:
            raise AssertionError("freshness result did not fingerprint")

    @classmethod
    def build_intent(
        cls,
        *,
        nonce_hash: str | None = None,
        freshness_result=None,
        attestation=None,
        cursor=None,
    ):
        source_result = freshness_result or cls.freshness_result
        source_attestation = attestation or cls.attestation
        source_cursor = cursor or cls.base_cursor
        fingerprint = (
            cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
                source_result
            )
        )
        return cas.build_incumbent_snapshot_replay_cursor_cas_transition_intent_v1(
            source_result,
            source_attestation,
            source_cursor,
            request_nonce_hash=nonce_hash or _sha("9"),
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=source_attestation.attestation_hash,
            expected_cursor_hash=source_cursor.cursor_hash,
        )

    @classmethod
    def simulate(
        cls,
        intent,
        *,
        base_cursor=None,
        observed_cursor=None,
        attestation=None,
        freshness_result=None,
        expected_intent_hash=None,
        expected_fingerprint=None,
        expected_observed_cursor_hash=None,
    ):
        source_base = base_cursor or cls.base_cursor
        source_observed = observed_cursor or source_base
        source_attestation = attestation or cls.attestation
        source_result = freshness_result or cls.freshness_result
        fingerprint = expected_fingerprint or (
            cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
                source_result
            )
        )
        return cas.simulate_incumbent_snapshot_replay_cursor_cas_transition_v1(
            source_base,
            source_observed,
            source_attestation,
            source_result,
            intent,
            expected_intent_hash=expected_intent_hash or intent.intent_hash,
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=source_attestation.attestation_hash,
            expected_base_cursor_hash=source_base.cursor_hash,
            expected_observed_cursor_hash=(
                expected_observed_cursor_hash or source_observed.cursor_hash
            ),
            expected_stream_id=source_base.stream_id,
            expected_projection_preregistration_hash=(
                source_base.projection_preregistration_hash
            ),
        )

    def test_candidate_builds_exact_hash_bound_intent(self) -> None:
        intent = self.build_intent()
        self.assertIsNotNone(intent)
        self.assertEqual(intent.expected_cursor_hash, self.base_cursor.cursor_hash)
        self.assertEqual(
            intent.candidate_attestation_hash,
            self.attestation.attestation_hash,
        )
        self.assertNotEqual(intent.proposed_cursor_hash, self.base_cursor.cursor_hash)

    def test_matching_cursor_returns_uncommitted_advanced_cursor(self) -> None:
        intent = self.build_intent()
        result = self.simulate(intent)
        receipt = result.receipt
        self.assertEqual(
            receipt.outcome,
            cas.OUTCOME_ADVANCED_IN_RETURNED_CURSOR,
        )
        self.assertEqual(receipt.gate_status, cas.GATE_STATUS_UNKNOWN)
        self.assertTrue(receipt.returned_cursor_changed)
        self.assertIn(
            self.attestation.attestation_hash,
            result.returned_cursor.consumed_attestation_hashes,
        )
        self.assertEqual(
            result.returned_cursor.high_water_sequence,
            self.attestation.sequence,
        )
        self.assertFalse(receipt.input_cursor_mutation_performed)
        self.assertFalse(receipt.atomic_storage_commit_verified)
        self.assertFalse(receipt.durable_commit_verified)
        self.assertFalse(receipt.linearizable_read_verified)
        self.assertFalse(receipt.permission)

    def test_sequential_duplicate_blocks_before_cas_conflict(self) -> None:
        intent = self.build_intent()
        first = self.simulate(intent)
        replay = self.simulate(intent, observed_cursor=first.returned_cursor)
        self.assertEqual(replay.receipt.outcome, cas.OUTCOME_ALREADY_CONSUMED)
        self.assertEqual(replay.receipt.gate_status, cas.GATE_STATUS_BLOCK)
        self.assertFalse(replay.receipt.returned_cursor_changed)
        self.assertEqual(replay.returned_cursor, first.returned_cursor)

    def test_nonmonotonic_unconsumed_sequence_blocks(self) -> None:
        other_hash = _different_hash(
            self.attestation.attestation_hash,
            self.base_cursor.high_water_attestation_hash,
        )
        observed = replay_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.attestation.sequence,
            high_water_attestation_hash=other_hash,
            consumed_attestation_hashes=tuple(
                sorted(self.base_cursor.consumed_attestation_hashes + (other_hash,))
            ),
        )
        intent = self.build_intent()
        result = self.simulate(intent, observed_cursor=observed)
        self.assertEqual(
            result.receipt.outcome,
            cas.OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER,
        )
        self.assertEqual(result.receipt.gate_status, cas.GATE_STATUS_BLOCK)

    def test_changed_cursor_with_fresh_candidate_is_cas_conflict(self) -> None:
        other_hash = _different_hash(
            self.attestation.attestation_hash,
            self.base_cursor.high_water_attestation_hash,
        )
        observed = replay_gate.build_incumbent_snapshot_replay_cursor_v1(
            stream_id=self.base_cursor.stream_id,
            projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
            high_water_sequence=self.base_cursor.high_water_sequence,
            high_water_attestation_hash=(
                self.base_cursor.high_water_attestation_hash
            ),
            consumed_attestation_hashes=tuple(
                sorted(self.base_cursor.consumed_attestation_hashes + (other_hash,))
            ),
        )
        intent = self.build_intent()
        result = self.simulate(intent, observed_cursor=observed)
        self.assertEqual(
            result.receipt.outcome,
            cas.OUTCOME_COMPARE_AND_SWAP_CONFLICT,
        )
        self.assertEqual(result.receipt.gate_status, cas.GATE_STATUS_UNKNOWN)
        self.assertEqual(result.returned_cursor, observed)
        self.assertFalse(result.receipt.returned_cursor_changed)

    def test_parallel_simulations_are_equal_without_atomic_claim(self) -> None:
        intent = self.build_intent()
        first = self.simulate(intent)
        second = self.simulate(intent)
        self.assertEqual(first, second)
        self.assertFalse(first.receipt.atomic_storage_commit_verified)

    def test_tampered_intent_is_rejected(self) -> None:
        intent = self.build_intent()
        tampered = replace(intent, request_nonce_hash=_sha("8"))
        self.assertIsNone(
            self.simulate(tampered, expected_intent_hash=tampered.intent_hash)
        )

    def test_wrong_expected_hashes_are_rejected(self) -> None:
        intent = self.build_intent()
        wrong = _different_hash(intent.intent_hash, self.fingerprint)
        self.assertIsNone(self.simulate(intent, expected_intent_hash=wrong))
        self.assertIsNone(self.simulate(intent, expected_fingerprint=wrong))
        self.assertIsNone(
            self.simulate(intent, expected_observed_cursor_hash=wrong)
        )

    def test_noncanonical_observed_cursor_is_rejected(self) -> None:
        other_hash = _different_hash(*self.base_cursor.consumed_attestation_hashes)
        forged = replace(
            self.base_cursor,
            consumed_attestation_hashes=(
                self.base_cursor.consumed_attestation_hashes + (other_hash,)
            ),
        )
        intent = self.build_intent()
        self.assertIsNone(self.simulate(intent, observed_cursor=forged))

    def test_upstream_block_cannot_build_transition_intent(self) -> None:
        temporal = self.fixture.temporal(
            self.snapshot,
            sequence=8,
            head=10,
            high_water=7,
            max_lag=1,
        )
        attestation, _, cursor, _ = temporal
        blocked = self.fixture.evaluate(self.proposals, self.snapshot, temporal)
        self.assertNotEqual(
            blocked.status,
            replay_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE,
        )
        self.assertIsNone(
            self.build_intent(
                freshness_result=blocked,
                attestation=attestation,
                cursor=cursor,
            )
        )

    def test_nonce_changes_intent_not_proposed_cursor(self) -> None:
        first = self.build_intent(nonce_hash=_sha("7"))
        second = self.build_intent(nonce_hash=_sha("8"))
        self.assertNotEqual(first.intent_hash, second.intent_hash)
        self.assertEqual(first.proposed_cursor_hash, second.proposed_cursor_hash)

    def test_public_api_exposes_no_storage_commit_operation(self) -> None:
        forbidden_prefixes = ("commit_", "persist_", "write_", "mount_")
        public_names = tuple(name for name in dir(cas) if not name.startswith("_"))
        self.assertFalse(
            any(name.startswith(forbidden_prefixes) for name in public_names)
        )
        intent = self.build_intent()
        receipt = self.simulate(intent).receipt
        self.assertEqual(receipt.gate_status, cas.GATE_STATUS_UNKNOWN)
        self.assertFalse(receipt.atomic_storage_commit_verified)
        self.assertFalse(receipt.durable_commit_verified)
        self.assertFalse(receipt.linearizable_read_verified)


if __name__ == "__main__":
    unittest.main()
