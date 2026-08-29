from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import inspect
from threading import Lock
import unittest

from exchange_terminal.application import (
    challenge_consumption_provider_genesis_replay_reservation_preregistration_v1 as preregistration,
)
from exchange_terminal.interfaces import (
    challenge_consumption_provider_genesis_replay_reservation_provider as port,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class _MemoryReservationFake:
    def __init__(self) -> None:
        self.head = _hash("reservation-genesis-head")
        self.revision = 0
        self.reserved: dict[str, str] = {}
        self.lock = Lock()

    def reserve_once(self, command):
        with self.lock:
            replay_key = command.genesis_admission_replay_key_hash
            if replay_key in self.reserved:
                return port.build_genesis_admission_replay_reserve_once_result_v1(
                    command,
                    outcome=(
                        port.GenesisAdmissionReplayReservationOutcomeV1.ALREADY_RESERVED
                    ),
                    observed_registry_head_hash=self.head,
                    observed_provider_revision=self.revision,
                    duplicate_reservation_receipt_hash=self.reserved[replay_key],
                )
            if (
                command.expected_registry_head_hash != self.head
                or command.expected_provider_revision != self.revision
            ):
                return port.build_genesis_admission_replay_reserve_once_result_v1(
                    command,
                    outcome=(
                        port.GenesisAdmissionReplayReservationOutcomeV1.COMPARE_AND_SWAP_CONFLICT
                    ),
                    observed_registry_head_hash=self.head,
                    observed_provider_revision=self.revision,
                )
            result = port.build_genesis_admission_replay_reserve_once_result_v1(
                command,
                outcome=port.GenesisAdmissionReplayReservationOutcomeV1.RESERVED,
                observed_registry_head_hash=self.head,
                observed_provider_revision=self.revision,
            )
            self.head = result.returned_registry_head_hash
            self.revision = result.returned_provider_revision
            self.reserved[replay_key] = result.reservation_receipt_hash
            return result


class GenesisReplayReservationContractV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _MemoryReservationFake()
        self.command_kwargs = {
            "genesis_admission_replay_key_hash": _hash("replay-key-a"),
            "threshold_admission_evidence_hash": _hash("threshold-evidence-a"),
            "expected_registry_head_hash": self.fake.head,
            "expected_provider_revision": self.fake.revision,
            "request_id_hash": _hash("request-a"),
        }
        self.command = (
            port.build_genesis_admission_replay_reserve_once_command_v1(
                **self.command_kwargs
            )
        )
        self.preregistration_kwargs = {
            "registry_id": "synthetic.genesis.replay.registry.v1",
            "operator_identity_claim": "synthetic.genesis.replay.operator.v1",
            "public_key_spki_sha256": _hash("reservation-provider-key"),
            "trust_domain": "synthetic.test-only",
            "provider_implementation_claim_sha256": _hash(
                "reservation-provider-implementation"
            ),
        }
        self.prereg = (
            preregistration.build_genesis_replay_reservation_provider_preregistration_v1(
                **self.preregistration_kwargs
            )
        )
        self.plan = (
            preregistration.build_genesis_replay_reservation_provider_conformance_plan_v1(
                self.prereg,
                **self.preregistration_kwargs,
            )
        )

    def build_command(self, **overrides):
        return port.build_genesis_admission_replay_reserve_once_command_v1(
            **{**self.command_kwargs, **overrides}
        )

    def test_command_is_immutable_deterministic_and_role_bound(self) -> None:
        self.assertEqual(self.build_command(), self.command)
        with self.assertRaises(FrozenInstanceError):
            self.command.request_id_hash = _hash("mutated")
        for field in (
            "genesis_admission_replay_key_hash",
            "threshold_admission_evidence_hash",
            "expected_registry_head_hash",
            "request_id_hash",
        ):
            changed = self.build_command(**{field: _hash("changed-" + field)})
            self.assertNotEqual(changed.command_hash, self.command.command_hash)

    def test_command_rejects_bool_revision_hash_and_schema_aliases(self) -> None:
        with self.assertRaises(ValueError):
            self.build_command(expected_provider_revision=True)
        with self.assertRaises(ValueError):
            self.build_command(request_id_hash="0")
        with self.assertRaises(ValueError):
            replace(self.command, schema_version=self.command.schema_version + "-alias")

    def test_matching_state_reserves_structurally(self) -> None:
        result = self.fake.reserve_once(self.command)
        self.assertEqual(
            result.outcome,
            port.GenesisAdmissionReplayReservationOutcomeV1.RESERVED,
        )
        self.assertEqual(result.returned_provider_revision, 1)
        self.assertIsNotNone(result.reservation_receipt_hash)
        self.assertTrue(
            port.verify_genesis_admission_replay_reserve_once_result_v1(
                result, self.command, expected_result_hash=result.result_hash
            )
        )

    def test_duplicate_precedes_stale_state_conflict(self) -> None:
        first = self.fake.reserve_once(self.command)
        changed_request = self.build_command(
            expected_registry_head_hash=self.fake.head,
            expected_provider_revision=self.fake.revision,
            request_id_hash=_hash("request-b"),
        )
        second = self.fake.reserve_once(changed_request)
        self.assertEqual(
            second.outcome,
            port.GenesisAdmissionReplayReservationOutcomeV1.ALREADY_RESERVED,
        )
        self.assertEqual(
            second.duplicate_reservation_receipt_hash,
            first.reservation_receipt_hash,
        )

    def test_same_key_concurrency_has_one_reserved_one_duplicate(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(lambda _: self.fake.reserve_once(self.command), range(2))
            )
        self.assertEqual(
            sorted(result.outcome.value for result in results),
            ["ALREADY_RESERVED", "RESERVED"],
        )
        self.assertEqual(self.fake.revision, 1)

    def test_distinct_keys_same_base_have_reserved_and_conflict(self) -> None:
        other = self.build_command(
            genesis_admission_replay_key_hash=_hash("replay-key-b"),
            threshold_admission_evidence_hash=_hash("threshold-evidence-b"),
            request_id_hash=_hash("request-b"),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.fake.reserve_once, [self.command, other]))
        self.assertEqual(
            sorted(result.outcome.value for result in results),
            ["COMPARE_AND_SWAP_CONFLICT", "RESERVED"],
        )
        self.assertEqual(self.fake.revision, 1)

    def test_result_verifier_rejects_hash_and_command_drift(self) -> None:
        result = self.fake.reserve_once(self.command)
        self.assertFalse(
            port.verify_genesis_admission_replay_reserve_once_result_v1(
                result, self.command, expected_result_hash="0" * 64
            )
        )
        other = self.build_command(
            genesis_admission_replay_key_hash=_hash("replay-key-b")
        )
        self.assertFalse(
            port.verify_genesis_admission_replay_reserve_once_result_v1(
                result, other, expected_result_hash=result.result_hash
            )
        )

    def test_result_outcome_alias_and_invalid_conflict_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            port.build_genesis_admission_replay_reserve_once_result_v1(
                self.command,
                outcome="RESERVED",
                observed_registry_head_hash=self.fake.head,
                observed_provider_revision=0,
            )
        with self.assertRaises(ValueError):
            port.build_genesis_admission_replay_reserve_once_result_v1(
                self.command,
                outcome=(
                    port.GenesisAdmissionReplayReservationOutcomeV1.COMPARE_AND_SWAP_CONFLICT
                ),
                observed_registry_head_hash=self.fake.head,
                observed_provider_revision=0,
            )

    def test_memory_fake_is_test_only_and_protocol_conformant(self) -> None:
        self.assertIsInstance(
            self.fake, port.GenesisAdmissionReplayReservationPortV1
        )
        source = inspect.getsource(port)
        self.assertNotIn("_MemoryReservationFake", source)
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

    def test_preregistration_is_exact_redacted_and_blocked(self) -> None:
        self.assertEqual(
            preregistration.build_genesis_replay_reservation_provider_preregistration_v1(
                **self.preregistration_kwargs
            ),
            self.prereg,
        )
        self.assertEqual(self.prereg["status"], "BLOCKED")
        self.assertTrue(
            preregistration.verify_genesis_replay_reservation_provider_preregistration_v1(
                self.prereg, **self.preregistration_kwargs
            )
        )
        self.assertFalse(self.prereg["facts"]["provider_registered"])
        self.assertTrue(
            all(value is False for value in self.prereg["authority"].values())
        )
        self.assertNotIn("public_key_spki_base64", str(self.prereg))

    def test_preregistration_alias_and_identity_drift_fail_closed(self) -> None:
        with self.assertRaises(
            preregistration.GenesisReplayReservationProviderPreregistrationError
        ):
            preregistration.build_genesis_replay_reservation_provider_preregistration_v1(
                **{
                    **self.preregistration_kwargs,
                    "provider_protocol_version": (
                        preregistration.PROVIDER_PROTOCOL_VERSION + "-alias"
                    ),
                }
            )
        drifted = deepcopy(self.prereg)
        drifted["status"] = "PASS"
        with self.assertRaisesRegex(
            preregistration.GenesisReplayReservationProviderPreregistrationError,
            "not exact",
        ):
            preregistration.build_genesis_replay_reservation_provider_conformance_plan_v1(
                drifted, **self.preregistration_kwargs
            )

    def test_plan_freezes_thirteen_unexecuted_cases(self) -> None:
        self.assertEqual(self.plan["summary"]["planned_case_count"], 13)
        self.assertEqual(self.plan["summary"]["executed_case_count"], 0)
        self.assertFalse(self.plan["summary"]["runtime_mutations"])
        self.assertTrue(all(case["executed"] is False for case in self.plan["cases"]))
        self.assertTrue(all(case["observed"] is None for case in self.plan["cases"]))
        self.assertTrue(
            preregistration.verify_genesis_replay_reservation_provider_conformance_plan_v1(
                self.plan,
                self.prereg,
                expected_conformance_plan_hash=self.plan[
                    "conformance_plan_hash"
                ],
                **self.preregistration_kwargs,
            )
        )

    def test_plan_verifier_rejects_resealed_execution_promotion(self) -> None:
        forged = deepcopy(self.plan)
        forged.pop("conformance_plan_hash")
        forged["cases"][0]["executed"] = True
        forged["cases"][0]["observed"] = "RESERVED"
        forged["summary"]["executed_case_count"] = 1
        forged = seal_strict_canonical_document(
            forged, "conformance_plan_hash"
        )
        self.assertFalse(
            preregistration.verify_genesis_replay_reservation_provider_conformance_plan_v1(
                forged,
                self.prereg,
                expected_conformance_plan_hash=forged[
                    "conformance_plan_hash"
                ],
                **self.preregistration_kwargs,
            )
        )

    def test_production_preregistration_has_no_provider_io_or_runtime(self) -> None:
        source = inspect.getsource(preregistration)
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key",
            ".reserve_once(",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "runtime/",
            "threading",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
