from __future__ import annotations

from dataclasses import FrozenInstanceError
from hashlib import sha256
import unittest

from exchange_terminal.interfaces.anti_replay_registry import (
    AntiReplayCompareAndConsumeCommandV1,
    AntiReplayCompareAndConsumeResultV1,
    AntiReplayRegistryOutcomeV1,
    AntiReplayRegistryPortV1,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_post_registration_anti_replay_consumption_reference_cross_runtime_v1 as reference_support


class _SyntheticStructuralPort:
    registry_id = "synthetic.structural.port"

    def compare_and_consume(
        self, command: AntiReplayCompareAndConsumeCommandV1
    ) -> AntiReplayCompareAndConsumeResultV1:
        return AntiReplayCompareAndConsumeResultV1(
            outcome=AntiReplayRegistryOutcomeV1.CONSUMED,
            request_hash=command.request_hash,
            consumption_key=command.consumption_key,
            registry_id=self.registry_id,
            registry_revision=1,
            receipt_document=None,
        )


class AntiReplayRegistryInterfaceCrossRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        support_type = (
            reference_support.AntiReplayConsumptionReferenceCrossRuntimeV1Tests
        )
        support_type.setUpClass()
        cls.support = support_type()

    def _request(self, state: str = "CLEAR") -> dict:
        return self.support._node(state, "first")["request"]

    def test_three_node_requests_become_distinct_immutable_commands(self) -> None:
        commands = [
            AntiReplayCompareAndConsumeCommandV1.from_request_document(
                self._request(state)
            )
            for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN")
        ]
        self.assertEqual(len({command.request_hash for command in commands}), 3)
        with self.assertRaises(FrozenInstanceError):
            commands[0].request_hash = sha256(b"mutated").hexdigest()  # type: ignore[misc]

    def test_structural_protocol_match_is_not_external_conformance(self) -> None:
        port = _SyntheticStructuralPort()
        self.assertIsInstance(port, AntiReplayRegistryPortV1)
        command = AntiReplayCompareAndConsumeCommandV1.from_request_document(
            self._request()
        )
        result = port.compare_and_consume(command)
        self.assertEqual(result.outcome, AntiReplayRegistryOutcomeV1.CONSUMED)
        self.assertIsNone(result.receipt_document)
        self.assertFalse(hasattr(result, "external_linearizability_verified"))
        self.assertFalse(hasattr(result, "registry_identity_verified"))

    def test_request_schema_alias_and_hash_tamper_are_rejected(self) -> None:
        alias = self._request()
        alias["schema_version"] = f"{alias['schema_version']}.0"
        with self.assertRaises(ValueError):
            AntiReplayCompareAndConsumeCommandV1.from_request_document(alias)
        tampered = self._request()
        tampered["source"]["witness_verification_hash"] = sha256(
            b"tampered"
        ).hexdigest()
        with self.assertRaises(ValueError):
            AntiReplayCompareAndConsumeCommandV1.from_request_document(tampered)

    def test_consumption_key_rebinding_is_rejected_even_when_resealed_upstream(self) -> None:
        request = self._request()
        request["source"]["consumption_key"] = sha256(b"wrong-key").hexdigest()
        body = dict(request)
        body.pop("request_hash")
        from exchange_terminal.services.strict_canonical_json_hash import (
            seal_strict_canonical_document,
        )

        resealed = seal_strict_canonical_document(body, "request_hash")
        with self.assertRaises(ValueError):
            AntiReplayCompareAndConsumeCommandV1.from_request_document(resealed)

    def test_result_rejects_alias_invalid_revision_and_non_enum_outcome(self) -> None:
        request = self._request()
        command = AntiReplayCompareAndConsumeCommandV1.from_request_document(request)
        base = {
            "outcome": AntiReplayRegistryOutcomeV1.CONSUMED,
            "request_hash": command.request_hash,
            "consumption_key": command.consumption_key,
            "registry_id": "synthetic.structural.port",
            "registry_revision": 1,
        }
        for patch in (
            {"schema_version": "anti-replay-compare-and-consume-result-v1.0"},
            {"registry_revision": -1},
            {"outcome": "CONSUMED"},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    AntiReplayCompareAndConsumeResultV1(**(base | patch))


if __name__ == "__main__":
    unittest.main()
