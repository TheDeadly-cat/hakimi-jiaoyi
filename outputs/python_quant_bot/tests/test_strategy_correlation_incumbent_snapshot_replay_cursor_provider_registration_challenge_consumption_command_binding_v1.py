from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_command_binding_v1 as command_binding,
)
from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider as port,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_clock_attestation_binding_v1 as clock_binding_fixture,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ChallengeConsumptionCommandBindingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.upstream = clock_binding_fixture.ReplayCursorProviderRegistrationChallengeClockBindingV1Tests(
            "test_happy_path_reports_only_local_binding_facts"
        )
        self.upstream.setUp()
        self.clock_binding_evidence = self.upstream.evaluate()
        self.inputs = {
            "clock_binding_evidence": self.clock_binding_evidence,
            "clock_attestation": self.upstream.clock_attestation,
            "clock_registration": self.upstream.clock_registration,
            "clock_receipts": self.upstream.clock_receipts,
            "clock_public_keys_by_id": self.upstream.clock_public_keys,
            "challenge_evidence": self.upstream.challenge_evidence,
            "signed_challenge_document": self.upstream.signed_challenge,
            "challenge_document": self.upstream.challenge,
            "provider_preregistration_document": (
                self.upstream.provider_preregistration
            ),
            "challenge_authority_preregistration_document": (
                self.upstream.authority_preregistration
            ),
            "expected_clock_binding_evidence_hash": self.clock_binding_evidence[
                "clock_binding_evidence_hash"
            ],
            "expected_clock_attestation_hash": self.upstream.clock_attestation[
                "attestation_hash"
            ],
            "expected_clock_registration_hash": self.upstream.clock_registration[
                "registration_hash"
            ],
            "expected_clock_receipt_hashes": self.upstream.expected_receipt_hashes,
            "clock_verification_time_ms": 1_010_500,
            "expected_challenge_evidence_hash": self.upstream.challenge_evidence[
                "verification_evidence_hash"
            ],
            "challenge_evaluation_kwargs": (
                self.upstream.challenge_evaluation_kwargs
            ),
            "expected_registry_head_hash": _hash("synthetic-registry-head"),
            "expected_provider_revision": 7,
            "request_id_hash": _hash("synthetic-consumption-request"),
        }
        self.command = command_binding.build_replay_cursor_provider_registration_challenge_consumption_command_binding_v1(
            **self.inputs
        )

    def build_command(self, **overrides):
        return command_binding.build_replay_cursor_provider_registration_challenge_consumption_command_binding_v1(
            **{**self.inputs, **overrides}
        )

    def build_evidence(self, **overrides):
        values = {**self.inputs, **overrides}
        expected_command_hash = values.pop(
            "expected_command_hash", self.command.command_hash
        )
        return command_binding.build_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
            expected_command_hash=expected_command_hash,
            **values,
        )

    def test_exact_adr0388_evidence_builds_exact_adr0389_command(self) -> None:
        self.assertIsInstance(
            self.command,
            port.ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1,
        )
        self.assertEqual(
            self.command.signed_challenge_hash,
            self.upstream.signed_challenge["signed_challenge_hash"],
        )
        self.assertEqual(
            self.command.challenge_clock_binding_evidence_hash,
            self.clock_binding_evidence["clock_binding_evidence_hash"],
        )
        self.assertEqual(
            self.command.registration_nonce_hash,
            self.upstream.registration_nonce_hash,
        )
        self.assertTrue(
            port.verify_replay_cursor_provider_registration_challenge_consume_once_command_v1(
                self.command, expected_command_hash=self.command.command_hash
            )
        )

    def test_binding_evidence_is_blocked_despite_exact_command(self) -> None:
        evidence = self.build_evidence()
        self.assertEqual(evidence["status"], "BLOCKED")
        self.assertTrue(evidence["facts"]["consume_once_command_exact"])
        self.assertFalse(evidence["facts"]["consume_once_called"])
        self.assertFalse(evidence["facts"]["provider_result_observed"])
        self.assertFalse(evidence["facts"]["challenge_consumption_verified"])
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_clock_binding_evidence_mutation_is_rejected(self) -> None:
        mutated = deepcopy(self.clock_binding_evidence)
        mutated["facts"]["current_time_established"] = True
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(clock_binding_evidence=mutated)

    def test_clock_binding_expected_hash_drift_is_rejected(self) -> None:
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(expected_clock_binding_evidence_hash="0" * 64)

    def test_signed_challenge_substitution_is_rejected(self) -> None:
        substituted = deepcopy(self.upstream.signed_challenge)
        substituted["signed_challenge_hash"] = _hash("substituted-challenge")
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(signed_challenge_document=substituted)

    def test_registration_nonce_substitution_is_rejected(self) -> None:
        substituted = deepcopy(self.upstream.challenge)
        substituted["binding"]["registration_nonce_hash"] = _hash(
            "substituted-nonce"
        )
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(challenge_document=substituted)

    def test_registry_head_revision_and_request_are_hash_bound(self) -> None:
        for overrides in (
            {"expected_registry_head_hash": _hash("other-head")},
            {"expected_provider_revision": 8},
            {"request_id_hash": _hash("other-request")},
        ):
            changed = self.build_command(**overrides)
            self.assertNotEqual(changed.command_hash, self.command.command_hash)

    def test_bool_revision_and_role_hash_collision_are_rejected(self) -> None:
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(expected_provider_revision=True)
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_command(request_id_hash=self.upstream.registration_nonce_hash)

    def test_public_evidence_verifier_rebuilds_and_rejects_mutation(self) -> None:
        evidence = self.build_evidence()
        values = dict(self.inputs)
        binding_evidence = values.pop("clock_binding_evidence")
        self.assertTrue(
            command_binding.verify_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
                evidence,
                binding_evidence,
                expected_command_binding_evidence_hash=evidence[
                    "command_binding_evidence_hash"
                ],
                expected_command_hash=self.command.command_hash,
                **values,
            )
        )
        mutated = deepcopy(evidence)
        mutated["facts"]["challenge_consumption_verified"] = True
        self.assertFalse(
            command_binding.verify_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
                mutated,
                binding_evidence,
                expected_command_binding_evidence_hash=evidence[
                    "command_binding_evidence_hash"
                ],
                expected_command_hash=self.command.command_hash,
                **values,
            )
        )

    def test_binding_evidence_redacts_all_raw_material(self) -> None:
        encoded = json.dumps(self.build_evidence(), sort_keys=True)
        for public_key in self.upstream.clock_public_keys.values():
            self.assertNotIn(public_key, encoded)
        for receipt in self.upstream.clock_receipts:
            self.assertNotIn(receipt["signature"]["signature_base64"], encoded)
        self.assertNotIn(
            self.upstream.signed_challenge["signature_base64"], encoded
        )

    def test_build_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        before = deepcopy(self.inputs)
        first = self.build_command()
        second = self.build_command()
        self.assertEqual(first, second)
        self.assertEqual(before, self.inputs)

    def test_expected_command_hash_mismatch_is_rejected(self) -> None:
        with self.assertRaises(command_binding.ChallengeConsumptionCommandBindingError):
            self.build_evidence(expected_command_hash="0" * 64)

    def test_production_module_never_calls_provider_or_runtime_capabilities(self) -> None:
        source = Path(command_binding.__file__).read_text(encoding="utf-8")
        for forbidden in (
            ".consume_once(",
            "Ed25519PrivateKey",
            "private_key",
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "time.time",
            "datetime.now",
            "runtime/",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
