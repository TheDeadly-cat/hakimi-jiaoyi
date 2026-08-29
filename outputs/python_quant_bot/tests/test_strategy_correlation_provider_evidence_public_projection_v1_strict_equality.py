from __future__ import annotations

import copy
import inspect
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_provider_evidence_public_projection_v1 as subject,
)


def _boolean_paths(value, prefix=()):
    if type(value) is bool:
        yield prefix, value
    elif type(value) is dict:
        for key, child in value.items():
            yield from _boolean_paths(child, prefix + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _boolean_paths(child, prefix + (index,))


def _replace_path(document, path, value) -> None:
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


class StrategyCorrelationProviderEvidencePublicProjectionV1StrictEqualityTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.protocol_summary = {
            "schema_version": "synthetic-protocol-summary-v1",
            "private_marker": "protocol-secret",
        }
        self.provider_replay_gate = {
            "schema_version": "synthetic-provider-replay-v1",
            "private_marker": "replay-secret",
        }
        self.protocol_context = {"trust": "protocol-trust-secret"}
        self.replay_context = {"trust": "replay-trust-secret"}

    @contextmanager
    def _verifiers(
        self,
        *,
        protocol_status: str = "PASS",
        replay_status: str = "PASS",
    ):
        with patch.object(
            subject,
            "verify_protocol_summary",
            return_value={"status": protocol_status, "blockers": []},
        ), patch.object(
            subject,
            "verify_provider_replay_gate",
            return_value={"status": replay_status, "blockers": []},
        ):
            yield

    def _build_and_verify(self, *, protocol_status="PASS", replay_status="PASS"):
        with self._verifiers(
            protocol_status=protocol_status,
            replay_status=replay_status,
        ):
            document = subject.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )
            verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                document,
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )
        return document, verification

    def test_untampered_observed_and_unknown_projections_still_verify(self) -> None:
        for protocol_status in ("PASS", "BLOCK"):
            with self.subTest(protocol_status=protocol_status):
                document, verification = self._build_and_verify(
                    protocol_status=protocol_status
                )
                self.assertEqual(verification["status"], "PASS")
                self.assertEqual(
                    document["source"]["status"],
                    "OBSERVED" if protocol_status == "PASS" else "UNKNOWN",
                )

    def test_every_boolean_integer_alias_blocks_in_both_projection_states(self) -> None:
        attacked = 0
        for protocol_status in ("PASS", "BLOCK"):
            document, _ = self._build_and_verify(protocol_status=protocol_status)
            paths = list(_boolean_paths(document))
            self.assertEqual(len(paths), 27)
            for path, original in paths:
                with self.subTest(protocol_status=protocol_status, path=path):
                    attacked += 1
                    tampered = copy.deepcopy(document)
                    _replace_path(tampered, path, int(original))
                    with self._verifiers(protocol_status=protocol_status):
                        verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                            tampered,
                            self.protocol_summary,
                            self.provider_replay_gate,
                            protocol_verification_context=self.protocol_context,
                            provider_replay_verification_context=self.replay_context,
                        )
                    self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(attacked, 54)

    def test_non_dict_document_remains_blocked(self) -> None:
        with self._verifiers():
            verification = subject.verify_strategy_correlation_provider_evidence_public_projection_v1(
                [],
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(
            verification["blockers"],
            ["provider_evidence_public_projection_contract_invalid"],
        )

    def test_verifier_source_has_no_ordinary_python_equality_bypass(self) -> None:
        source = inspect.getsource(
            subject.verify_strategy_correlation_provider_evidence_public_projection_v1
        )

        self.assertIn("strict_json_contract_equal", source)
        self.assertNotIn("document == expected", source)
        self.assertNotIn("document != expected", source)


if __name__ == "__main__":
    unittest.main()
