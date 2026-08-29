from __future__ import annotations

import copy
import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_provider_evidence_presentation_envelope_v1 as subject,
)


class StrategyCorrelationProviderEvidencePresentationEnvelopeV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.protocol_summary = {
            "schema_version": "synthetic-protocol-summary-v1",
            "private_marker": "protocol-document-secret",
        }
        self.provider_replay_gate = {
            "schema_version": "synthetic-provider-replay-v1",
            "private_marker": "provider-document-secret",
        }
        self.protocol_context = {"trust_root": "protocol-context-secret"}
        self.replay_context = {"registry_key": "replay-context-secret"}

    @contextmanager
    def _upstream_verifiers(
        self,
        *,
        protocol_status: str = "PASS",
        replay_status: str = "PASS",
    ):
        with patch.object(
            subject.projection_contract,
            "verify_protocol_summary",
            return_value={"status": protocol_status, "blockers": []},
        ), patch.object(
            subject.projection_contract,
            "verify_provider_replay_gate",
            return_value={"status": replay_status, "blockers": []},
        ):
            yield

    def _build(
        self,
        *,
        protocol_status: str = "PASS",
        replay_status: str = "PASS",
        protocol_context=None,
        replay_context=None,
    ):
        if protocol_context is None:
            protocol_context = self.protocol_context
        if replay_context is None:
            replay_context = self.replay_context
        with self._upstream_verifiers(
            protocol_status=protocol_status,
            replay_status=replay_status,
        ):
            return subject.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=protocol_context,
                provider_replay_verification_context=replay_context,
            )

    def test_verified_sources_render_neutral_four_axis_envelope(self) -> None:
        document = self._build()

        self.assertEqual(document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(document["presentation_status"], "UNMOUNTED_CANDIDATE")
        self.assertEqual(document["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [axis["axis"] for axis in document["axes"]],
            list(subject.AXIS_ORDER),
        )
        self.assertEqual(document["display_state"], subject.POSITIVE_DISPLAY_STATE)
        self.assertTrue(document["facts"]["source_projection_verified"])
        self.assertFalse(document["facts"]["semantic_gate_outcome_projected"])
        self.assertIsNone(document["summary"]["provider_gate_outcome"])
        self.assertIsNone(document["summary"]["natural_forward_maturity"])

    def test_positive_envelope_remains_unmounted_and_non_authoritative(self) -> None:
        document = self._build()

        self.assertEqual(document["axes"][2]["state"], "UNKNOWN")
        self.assertEqual(document["axes"][3]["signal"], "LOCKED")
        self.assertFalse(document["summary"]["current_reference_present"])
        self.assertTrue(document["authority"]["descriptive_only"])
        for field in (
            "provider_gate_outcome_promotion_allowed",
            "maturity_promotion_allowed",
            "profitability_claim_allowed",
            "current_admission_allowed",
            "current_pointer_written",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertFalse(document["authority"][field])

    def test_documents_and_verification_contexts_are_not_embedded(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)

        for secret in (
            "protocol-document-secret",
            "provider-document-secret",
            "protocol-context-secret",
            "replay-context-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertFalse(self._build()["lineage"]["source_documents_embedded"])
        self.assertFalse(self._build()["lineage"]["verification_context_embedded"])

    def test_each_upstream_block_fails_closed_to_unknown(self) -> None:
        for protocol_status, replay_status in (("BLOCK", "PASS"), ("PASS", "BLOCK")):
            with self.subTest(
                protocol_status=protocol_status,
                replay_status=replay_status,
            ):
                document = self._build(
                    protocol_status=protocol_status,
                    replay_status=replay_status,
                )
                self.assertEqual(document["display_state"], "UNKNOWN")
                self.assertTrue(
                    all(axis["state"] == "UNKNOWN" for axis in document["axes"])
                )
                self.assertFalse(document["facts"]["result_available"])

    def test_verifier_exception_fails_closed_to_unknown(self) -> None:
        with patch.object(
            subject.projection_contract,
            "verify_protocol_summary",
            side_effect=ValueError("synthetic verifier failure"),
        ), patch.object(
            subject.projection_contract,
            "verify_provider_replay_gate",
            return_value={"status": "PASS", "blockers": []},
        ):
            document = subject.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(document["display_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["SOURCE_PROJECTION_UNVERIFIED"])

    def test_projection_verification_block_fails_closed(self) -> None:
        with self._upstream_verifiers(), patch.object(
            subject.projection_contract,
            "verify_strategy_correlation_provider_evidence_public_projection_v1",
            return_value={"status": "BLOCK", "blockers": ["synthetic"]},
        ):
            document = subject.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(document["display_state"], "UNKNOWN")

    def test_semantic_authority_tamper_is_rejected_even_with_pass_result(self) -> None:
        with self._upstream_verifiers():
            projection = subject.projection_contract.build_strategy_correlation_provider_evidence_public_projection_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )
        projection["permission"]["paper_authorized"] = True
        fake_verification = {
            "status": "PASS",
            "upstream_source_contracts_verified": True,
            "provider_gate_outcome_proven": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with patch.object(
            subject.projection_contract,
            "build_strategy_correlation_provider_evidence_public_projection_v1",
            return_value=projection,
        ), patch.object(
            subject.projection_contract,
            "verify_strategy_correlation_provider_evidence_public_projection_v1",
            return_value=fake_verification,
        ):
            document = subject.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
                self.protocol_summary,
                self.provider_replay_gate,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(document["display_state"], "UNKNOWN")

    def test_exact_rebuild_verifier_accepts_deterministic_envelope(self) -> None:
        first = self._build()
        second = self._build()

        self.assertEqual(first, second)
        with self._upstream_verifiers():
            self.assertTrue(
                subject.verify_strategy_correlation_provider_evidence_presentation_envelope_v1(
                    first,
                    self.protocol_summary,
                    self.provider_replay_gate,
                    protocol_verification_context=self.protocol_context,
                    provider_replay_verification_context=self.replay_context,
                )
            )

    def test_tampered_envelope_is_rejected(self) -> None:
        document = self._build()
        tampered = copy.deepcopy(document)
        tampered["authority"]["paper_authorized"] = True

        with self._upstream_verifiers():
            self.assertFalse(
                subject.verify_strategy_correlation_provider_evidence_presentation_envelope_v1(
                    tampered,
                    self.protocol_summary,
                    self.provider_replay_gate,
                    protocol_verification_context=self.protocol_context,
                    provider_replay_verification_context=self.replay_context,
                )
            )

    def test_non_dict_context_fails_closed(self) -> None:
        document = self._build(protocol_context=[])

        self.assertEqual(document["display_state"], "UNKNOWN")
        self.assertFalse(document["facts"]["source_projection_verified"])

    def test_sealed_hash_shape_and_static_fingerprint_are_stable(self) -> None:
        document = self._build()

        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(document["presentation_hash"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
