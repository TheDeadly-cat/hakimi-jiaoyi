from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from threading import Barrier, Lock, Thread
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas,
)
from exchange_terminal.interfaces.anti_replay_registry import (
    AntiReplayRegistryPortV1,
)
from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider as provider,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1
    as cas_fixture_module,
)


def _different_hash(*excluded: str | None) -> str:
    for character in "0123456789abcdef":
        candidate = character * 64
        if candidate not in excluded:
            return candidate
    raise AssertionError("could not build distinct synthetic hash")


class _InMemoryReplayCursorProvider:
    registry_id = "synthetic.in-memory.replay-cursor-provider"

    def __init__(self, initial_cursor) -> None:
        self._lock = Lock()
        self._revision = 0
        self._cursors = {
            (
                initial_cursor.stream_id,
                initial_cursor.projection_preregistration_hash,
            ): initial_cursor
        }

    def current(self, command):
        return self._cursors[
            (command.stream_id, command.projection_preregistration_hash)
        ]

    def compare_and_advance(self, command):
        with self._lock:
            current = self.current(command)
            if (
                command.candidate_attestation_hash
                in current.consumed_attestation_hashes
                or command.candidate_sequence <= current.high_water_sequence
            ):
                outcome = provider.ReplayCursorProviderOutcomeV1.DUPLICATE_REJECTED
                returned = current
            elif current.cursor_hash != command.base_cursor.cursor_hash:
                outcome = provider.ReplayCursorProviderOutcomeV1.CONFLICT_REJECTED
                returned = current
            else:
                outcome = provider.ReplayCursorProviderOutcomeV1.ADVANCED
                returned = command.proposed_cursor
                self._cursors[
                    (command.stream_id, command.projection_preregistration_hash)
                ] = returned
                self._revision += 1
            return provider.ReplayCursorCompareAndAdvanceResultV1(
                outcome=outcome,
                command_hash=command.command_hash,
                intent_hash=command.intent_hash,
                registry_id=self.registry_id,
                registry_revision=self._revision,
                observed_cursor_hash=current.cursor_hash,
                returned_cursor_hash=returned.cursor_hash,
                receipt_document=None,
            )


class IncumbentSnapshotReplayCursorProviderV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        fixture = (
            cas_fixture_module.IncumbentSnapshotReplayCursorCasTransitionV1Tests
        )
        fixture.setUpClass()
        cls.fixture = fixture
        cls.base_cursor = fixture.base_cursor
        cls.attestation = fixture.attestation
        cls.freshness_result = fixture.freshness_result
        cls.intent = fixture.build_intent()
        cls.fingerprint = fixture.fingerprint
        cls.command = provider.build_replay_cursor_compare_and_advance_command_v1(
            cls.base_cursor,
            cls.attestation,
            cls.freshness_result,
            cls.intent,
            expected_intent_hash=cls.intent.intent_hash,
            expected_freshness_result_fingerprint_sha256=cls.fingerprint,
            expected_attestation_hash=cls.attestation.attestation_hash,
            expected_base_cursor_hash=cls.base_cursor.cursor_hash,
            expected_stream_id=cls.base_cursor.stream_id,
            expected_projection_preregistration_hash=(
                cls.base_cursor.projection_preregistration_hash
            ),
        )
        if cls.command is None:
            raise AssertionError("provider command did not build")
        cls._fixture_setup_complete_v1 = True

    def test_command_is_exact_hash_bound_and_immutable(self) -> None:
        self.assertEqual(self.command.base_cursor, self.base_cursor)
        self.assertEqual(
            self.command.proposed_cursor.high_water_sequence,
            self.attestation.sequence,
        )
        self.assertIn(
            self.attestation.attestation_hash,
            self.command.proposed_cursor.consumed_attestation_hashes,
        )
        with self.assertRaises(FrozenInstanceError):
            self.command.command_hash = "0" * 64  # type: ignore[misc]

    def test_memory_fake_matches_specialized_port_not_generic_port(self) -> None:
        fake = _InMemoryReplayCursorProvider(self.base_cursor)
        self.assertIsInstance(fake, provider.ReplayCursorProviderPortV1)
        self.assertNotIsInstance(fake, AntiReplayRegistryPortV1)

    def test_matching_cursor_advances_exactly_once(self) -> None:
        fake = _InMemoryReplayCursorProvider(self.base_cursor)
        result = fake.compare_and_advance(self.command)
        self.assertEqual(
            result.outcome,
            provider.ReplayCursorProviderOutcomeV1.ADVANCED,
        )
        self.assertEqual(result.registry_revision, 1)
        self.assertEqual(fake.current(self.command), self.command.proposed_cursor)
        self.assertIsNone(result.receipt_document)

    def test_sequential_duplicate_is_rejected_before_conflict(self) -> None:
        fake = _InMemoryReplayCursorProvider(self.base_cursor)
        first = fake.compare_and_advance(self.command)
        second = fake.compare_and_advance(self.command)
        self.assertEqual(
            first.outcome,
            provider.ReplayCursorProviderOutcomeV1.ADVANCED,
        )
        self.assertEqual(
            second.outcome,
            provider.ReplayCursorProviderOutcomeV1.DUPLICATE_REJECTED,
        )
        self.assertEqual(second.registry_revision, 1)
        self.assertEqual(second.returned_cursor_hash, second.observed_cursor_hash)

    def test_changed_but_still_fresh_cursor_is_conflict(self) -> None:
        other_hash = _different_hash(
            self.attestation.attestation_hash,
            self.base_cursor.high_water_attestation_hash,
        )
        changed = replay_gate.build_incumbent_snapshot_replay_cursor_v1(
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
        fake = _InMemoryReplayCursorProvider(changed)
        result = fake.compare_and_advance(self.command)
        self.assertEqual(
            result.outcome,
            provider.ReplayCursorProviderOutcomeV1.CONFLICT_REJECTED,
        )
        self.assertEqual(result.registry_revision, 0)
        self.assertEqual(result.returned_cursor_hash, changed.cursor_hash)

    def test_two_threads_against_same_memory_state_advance_once(self) -> None:
        fake = _InMemoryReplayCursorProvider(self.base_cursor)
        start = Barrier(3)
        output_lock = Lock()
        outcomes = []

        def invoke() -> None:
            start.wait(timeout=2)
            result = fake.compare_and_advance(self.command)
            with output_lock:
                outcomes.append(result.outcome)

        threads = [Thread(target=invoke), Thread(target=invoke)]
        for thread in threads:
            thread.start()
        start.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertEqual(
            outcomes.count(provider.ReplayCursorProviderOutcomeV1.ADVANCED),
            1,
        )
        self.assertEqual(
            outcomes.count(
                provider.ReplayCursorProviderOutcomeV1.DUPLICATE_REJECTED
            ),
            1,
        )

    def test_blocked_upstream_cannot_build_provider_command(self) -> None:
        blocked = replace(
            self.freshness_result,
            status=replay_gate.STATUS_BLOCKED_FRESHNESS_OR_REPLAY,
            blocker_codes=("SNAPSHOT_SEQUENCE_NOT_ABOVE_HIGH_WATER",),
        )
        fingerprint = cas.fingerprint_incumbent_snapshot_freshness_replay_result_v1(
            blocked
        )
        command = provider.build_replay_cursor_compare_and_advance_command_v1(
            self.base_cursor,
            self.attestation,
            blocked,
            self.intent,
            expected_intent_hash=self.intent.intent_hash,
            expected_freshness_result_fingerprint_sha256=fingerprint,
            expected_attestation_hash=self.attestation.attestation_hash,
            expected_base_cursor_hash=self.base_cursor.cursor_hash,
            expected_stream_id=self.base_cursor.stream_id,
            expected_projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
        )
        self.assertIsNone(command)

    def test_wrong_expected_hash_cannot_build_provider_command(self) -> None:
        command = provider.build_replay_cursor_compare_and_advance_command_v1(
            self.base_cursor,
            self.attestation,
            self.freshness_result,
            self.intent,
            expected_intent_hash="0" * 64,
            expected_freshness_result_fingerprint_sha256=self.fingerprint,
            expected_attestation_hash=self.attestation.attestation_hash,
            expected_base_cursor_hash=self.base_cursor.cursor_hash,
            expected_stream_id=self.base_cursor.stream_id,
            expected_projection_preregistration_hash=(
                self.base_cursor.projection_preregistration_hash
            ),
        )
        self.assertIsNone(command)

    def test_resealed_command_field_without_hash_update_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "command hash"):
            replace(self.command, request_nonce_hash="0" * 64)
        with self.assertRaisesRegex(ValueError, "cursor sequence transition"):
            replace(self.command, candidate_attestation_hash="0" * 64)

    def test_result_rejects_alias_revision_and_outcome_hash_drift(self) -> None:
        base = {
            "outcome": provider.ReplayCursorProviderOutcomeV1.ADVANCED,
            "command_hash": self.command.command_hash,
            "intent_hash": self.command.intent_hash,
            "registry_id": "synthetic.result",
            "registry_revision": 1,
            "observed_cursor_hash": self.command.base_cursor.cursor_hash,
            "returned_cursor_hash": self.command.proposed_cursor.cursor_hash,
        }
        for patch in (
            {"schema_version": f"{provider.COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION}.0"},
            {"registry_revision": -1},
            {"outcome": "ADVANCED"},
            {"returned_cursor_hash": self.command.base_cursor.cursor_hash},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    provider.ReplayCursorCompareAndAdvanceResultV1(
                        **(base | patch)
                    )

    def test_structural_result_makes_no_external_authority_claim(self) -> None:
        fake = _InMemoryReplayCursorProvider(self.base_cursor)
        result = fake.compare_and_advance(self.command)
        for name in (
            "external_linearizability_verified",
            "durable_commit_verified",
            "registry_identity_verified",
            "paper_authorized",
            "live_authorized",
        ):
            self.assertFalse(hasattr(result, name))

    def test_production_interface_has_no_provider_or_runtime_implementation(self) -> None:
        source = Path(provider.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "threading",
            "sqlite3",
            "open(",
            "requests.",
            "urllib.",
            "socket.",
            "localStorage",
            "register_route(",
            "write_current_pointer(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("class InMemory", source)


if __name__ == "__main__":
    unittest.main()
