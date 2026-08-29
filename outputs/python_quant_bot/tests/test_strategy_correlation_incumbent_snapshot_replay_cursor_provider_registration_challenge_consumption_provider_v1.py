from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
import inspect
from threading import Lock
import unittest

from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider as port,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class _MemoryChallengeConsumptionFake:
    def __init__(self) -> None:
        self._lock = Lock()
        self._head = _hash("synthetic-challenge-consumption-genesis")
        self._revision = 0
        self._receipts: dict[str, str] = {}

    @property
    def head(self) -> str:
        with self._lock:
            return self._head

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def consume_once(self, command):
        with self._lock:
            observed_head = self._head
            observed_revision = self._revision
            duplicate = self._receipts.get(command.signed_challenge_hash)
            if duplicate is not None:
                return port.build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                    command,
                    outcome=port.ChallengeConsumptionProviderOutcomeV1.ALREADY_CONSUMED,
                    observed_registry_head_hash=observed_head,
                    observed_provider_revision=observed_revision,
                    duplicate_consumption_receipt_hash=duplicate,
                )
            if (
                command.expected_registry_head_hash != observed_head
                or command.expected_provider_revision != observed_revision
            ):
                return port.build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                    command,
                    outcome=(
                        port.ChallengeConsumptionProviderOutcomeV1.COMPARE_AND_SWAP_CONFLICT
                    ),
                    observed_registry_head_hash=observed_head,
                    observed_provider_revision=observed_revision,
                )
            result = port.build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                command,
                outcome=port.ChallengeConsumptionProviderOutcomeV1.CONSUMED,
                observed_registry_head_hash=observed_head,
                observed_provider_revision=observed_revision,
            )
            self._head = result.returned_registry_head_hash
            self._revision = result.returned_provider_revision
            self._receipts[command.signed_challenge_hash] = (
                result.consumption_receipt_hash
            )
            return result


class ChallengeConsumptionProviderPortV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _MemoryChallengeConsumptionFake()
        self.base = {
            "signed_challenge_hash": _hash("signed-challenge-a"),
            "challenge_clock_binding_evidence_hash": _hash("clock-binding-a"),
            "registration_nonce_hash": _hash("registration-nonce-a"),
            "expected_registry_head_hash": self.fake.head,
            "expected_provider_revision": self.fake.revision,
            "request_id_hash": _hash("request-a"),
        }
        self.command = port.build_replay_cursor_provider_registration_challenge_consume_once_command_v1(
            **self.base
        )

    def build_command(self, **overrides):
        values = {**self.base, **overrides}
        return port.build_replay_cursor_provider_registration_challenge_consume_once_command_v1(
            **values
        )

    def test_command_is_exact_hash_bound_and_immutable(self) -> None:
        self.assertTrue(
            port.verify_replay_cursor_provider_registration_challenge_consume_once_command_v1(
                self.command, expected_command_hash=self.command.command_hash
            )
        )
        with self.assertRaises(FrozenInstanceError):
            self.command.request_id_hash = _hash("mutated")
        with self.assertRaises(ValueError):
            replace(self.command, command_hash="0" * 64)

    def test_each_binding_role_changes_command_hash(self) -> None:
        for field in (
            "signed_challenge_hash",
            "challenge_clock_binding_evidence_hash",
            "registration_nonce_hash",
            "request_id_hash",
        ):
            changed = self.build_command(**{field: _hash("changed-" + field)})
            self.assertNotEqual(changed.command_hash, self.command.command_hash)

    def test_memory_fake_conforms_only_as_test_provider(self) -> None:
        self.assertIsInstance(
            self.fake,
            port.ReplayCursorProviderRegistrationChallengeConsumptionPortV1,
        )
        source = inspect.getsource(port)
        self.assertNotIn("_MemoryChallengeConsumptionFake", source)

    def test_matching_state_consumes_once_structurally(self) -> None:
        result = self.fake.consume_once(self.command)
        self.assertEqual(
            result.outcome, port.ChallengeConsumptionProviderOutcomeV1.CONSUMED
        )
        self.assertEqual(result.returned_provider_revision, 1)
        self.assertEqual(result.returned_registry_head_hash, self.fake.head)
        self.assertIsNotNone(result.consumption_receipt_hash)
        self.assertTrue(
            port.verify_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                result, self.command, expected_result_hash=result.result_hash
            )
        )

    def test_sequential_duplicate_precedes_stale_head_conflict(self) -> None:
        first = self.fake.consume_once(self.command)
        second = self.fake.consume_once(self.command)
        self.assertEqual(
            second.outcome,
            port.ChallengeConsumptionProviderOutcomeV1.ALREADY_CONSUMED,
        )
        self.assertEqual(
            second.duplicate_consumption_receipt_hash,
            first.consumption_receipt_hash,
        )

    def test_changed_request_for_same_challenge_is_still_duplicate(self) -> None:
        first = self.fake.consume_once(self.command)
        retry = self.build_command(
            expected_registry_head_hash=self.fake.head,
            expected_provider_revision=self.fake.revision,
            request_id_hash=_hash("request-b"),
        )
        result = self.fake.consume_once(retry)
        self.assertEqual(
            result.outcome,
            port.ChallengeConsumptionProviderOutcomeV1.ALREADY_CONSUMED,
        )
        self.assertEqual(
            result.duplicate_consumption_receipt_hash,
            first.consumption_receipt_hash,
        )

    def test_stale_state_for_fresh_challenge_is_conflict(self) -> None:
        self.fake.consume_once(self.command)
        fresh = self.build_command(
            signed_challenge_hash=_hash("signed-challenge-b"),
            challenge_clock_binding_evidence_hash=_hash("clock-binding-b"),
            registration_nonce_hash=_hash("registration-nonce-b"),
            request_id_hash=_hash("request-b"),
        )
        result = self.fake.consume_once(fresh)
        self.assertEqual(
            result.outcome,
            port.ChallengeConsumptionProviderOutcomeV1.COMPARE_AND_SWAP_CONFLICT,
        )
        self.assertEqual(result.returned_registry_head_hash, self.fake.head)

    def test_two_threads_same_challenge_consume_once(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.fake.consume_once(self.command), range(2)))
        outcomes = sorted(result.outcome.value for result in results)
        self.assertEqual(outcomes, ["ALREADY_CONSUMED", "CONSUMED"])
        self.assertEqual(self.fake.revision, 1)

    def test_two_fresh_challenges_same_base_yield_consumed_and_conflict(self) -> None:
        other = self.build_command(
            signed_challenge_hash=_hash("signed-challenge-b"),
            challenge_clock_binding_evidence_hash=_hash("clock-binding-b"),
            registration_nonce_hash=_hash("registration-nonce-b"),
            request_id_hash=_hash("request-b"),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.fake.consume_once, [self.command, other]))
        outcomes = sorted(result.outcome.value for result in results)
        self.assertEqual(outcomes, ["COMPARE_AND_SWAP_CONFLICT", "CONSUMED"])
        self.assertEqual(self.fake.revision, 1)

    def test_result_verifier_rejects_hash_and_command_drift(self) -> None:
        result = self.fake.consume_once(self.command)
        self.assertFalse(
            port.verify_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                result, self.command, expected_result_hash="0" * 64
            )
        )
        other = self.build_command(
            signed_challenge_hash=_hash("signed-challenge-b"),
            challenge_clock_binding_evidence_hash=_hash("clock-binding-b"),
            registration_nonce_hash=_hash("registration-nonce-b"),
            request_id_hash=_hash("request-b"),
        )
        self.assertFalse(
            port.verify_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                result, other, expected_result_hash=result.result_hash
            )
        )

    def test_bool_schema_and_outcome_aliases_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.build_command(expected_provider_revision=True)
        with self.assertRaises(ValueError):
            replace(self.command, schema_version=self.command.schema_version + "-alias")
        with self.assertRaises(ValueError):
            port.build_replay_cursor_provider_registration_challenge_consume_once_result_v1(
                self.command,
                outcome="CONSUMED",
                observed_registry_head_hash=self.fake.head,
                observed_provider_revision=self.fake.revision,
            )

    def test_result_contains_no_external_authority_claims(self) -> None:
        result = self.fake.consume_once(self.command)
        fields = asdict(result)
        for forbidden in (
            "atomic_storage_commit_verified",
            "durable_commit_verified",
            "linearizable_storage_verified",
            "provider_identity_verified",
            "paper_authorized",
            "live_allowed",
            "permission",
        ):
            self.assertNotIn(forbidden, fields)

    def test_production_module_has_no_provider_state_or_runtime_implementation(self) -> None:
        source = inspect.getsource(port)
        for forbidden in (
            "from threading import",
            "import threading",
            "sqlite3",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse(
            any(
                name.startswith("Memory") or name.startswith("Persistent")
                for name in port.__dict__
            )
        )


if __name__ == "__main__":
    unittest.main()
