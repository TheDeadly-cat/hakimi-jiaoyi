from __future__ import annotations

import copy
import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_provider_evidence_candidate_v1 as subject,
)


_DEFAULT_REQUEST = object()


class StrategyCorrelationProviderEvidenceHttpCandidateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "protocol_summary": {
                "schema_version": "synthetic-protocol-summary-v1",
                "private_marker": "protocol-request-secret",
            },
            "provider_replay_gate": {
                "schema_version": "synthetic-provider-replay-v1",
                "private_marker": "provider-request-secret",
            },
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
        projection_contract = subject.envelope_contract.projection_contract
        with patch.object(
            projection_contract,
            "verify_protocol_summary",
            return_value={"status": protocol_status, "blockers": []},
        ), patch.object(
            projection_contract,
            "verify_provider_replay_gate",
            return_value={"status": replay_status, "blockers": []},
        ):
            yield

    def _build(
        self,
        *,
        request=_DEFAULT_REQUEST,
        protocol_status: str = "PASS",
        replay_status: str = "PASS",
    ):
        if request is _DEFAULT_REQUEST:
            request = self.request
        with self._upstream_verifiers(
            protocol_status=protocol_status,
            replay_status=replay_status,
        ):
            return subject.build_strategy_correlation_provider_evidence_http_candidate_response_v1(
                request,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

    def test_verified_envelope_is_wrapped_as_unregistered_observation(self) -> None:
        response = self._build()

        self.assertEqual(response["state"], "OBSERVED")
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertTrue(response["facts"]["source_envelope_verified"])
        self.assertTrue(response["facts"]["result_available"])
        self.assertEqual(
            response["payload"]["axis_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )

    def test_transport_is_permanently_unregistered_and_side_effect_free(self) -> None:
        response = self._build()

        self.assertEqual(
            response["transport"],
            {
                "registered": False,
                "externally_callable": False,
                "method": None,
                "route": None,
                "runtime_reads": False,
                "runtime_mutations": False,
                "cache_reads": False,
                "cache_writes": False,
            },
        )
        self.assertFalse(response["facts"]["transport_registered"])

    def test_request_contract_is_exact_and_fail_closed(self) -> None:
        cases = [
            None,
            {},
            {**self.request, "unexpected": True},
            {**self.request, "schema_version": "wrong"},
            {**self.request, "protocol_summary": []},
            {**self.request, "provider_replay_gate": []},
        ]
        for request in cases:
            with self.subTest(request=request):
                response = self._build(request=request)
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])
                self.assertFalse(response["facts"]["request_contract_valid"])

    def test_invalid_context_fails_before_application_call(self) -> None:
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_provider_evidence_presentation_envelope_v1",
        ) as builder:
            response = subject.build_strategy_correlation_provider_evidence_http_candidate_response_v1(
                self.request,
                protocol_verification_context=None,
                provider_replay_verification_context=self.replay_context,
            )

        builder.assert_not_called()
        self.assertEqual(response["state"], "UNKNOWN")
        self.assertEqual(response["blockers"], ["VERIFICATION_CONTEXT_INVALID"])

    def test_verified_unknown_envelope_is_carried_without_result_promotion(self) -> None:
        response = self._build(protocol_status="BLOCK")

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsInstance(response["payload"], dict)
        self.assertEqual(response["payload"]["display_state"], "UNKNOWN")
        self.assertTrue(response["facts"]["source_envelope_verified"])
        self.assertFalse(response["facts"]["source_envelope_observed"])
        self.assertFalse(response["facts"]["result_available"])

    def test_application_builder_exception_fails_closed_without_payload(self) -> None:
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_provider_evidence_presentation_envelope_v1",
            side_effect=ValueError("synthetic failure"),
        ):
            response = subject.build_strategy_correlation_provider_evidence_http_candidate_response_v1(
                self.request,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_application_verification_false_fails_closed(self) -> None:
        with self._upstream_verifiers(), patch.object(
            subject.envelope_contract,
            "verify_strategy_correlation_provider_evidence_presentation_envelope_v1",
            return_value=False,
        ):
            response = subject.build_strategy_correlation_provider_evidence_http_candidate_response_v1(
                self.request,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_forged_application_authority_promotion_is_rejected(self) -> None:
        with self._upstream_verifiers():
            envelope = subject.envelope_contract.build_strategy_correlation_provider_evidence_presentation_envelope_v1(
                self.request["protocol_summary"],
                self.request["provider_replay_gate"],
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )
        envelope["authority"]["paper_authorized"] = True
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_provider_evidence_presentation_envelope_v1",
            return_value=envelope,
        ), patch.object(
            subject.envelope_contract,
            "verify_strategy_correlation_provider_evidence_presentation_envelope_v1",
            return_value=True,
        ):
            response = subject.build_strategy_correlation_provider_evidence_http_candidate_response_v1(
                self.request,
                protocol_verification_context=self.protocol_context,
                provider_replay_verification_context=self.replay_context,
            )

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_request_and_context_values_are_not_echoed(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)

        for secret in (
            "protocol-request-secret",
            "provider-request-secret",
            "protocol-context-secret",
            "replay-context-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertFalse(self._build()["lineage"]["request_documents_embedded"])
        self.assertFalse(self._build()["lineage"]["verification_context_embedded"])

    def test_exact_rebuild_response_is_deterministic_and_verifiable(self) -> None:
        first = self._build()
        second = self._build()

        self.assertEqual(first, second)
        with self._upstream_verifiers():
            self.assertTrue(
                subject.verify_strategy_correlation_provider_evidence_http_candidate_response_v1(
                    first,
                    self.request,
                    protocol_verification_context=self.protocol_context,
                    provider_replay_verification_context=self.replay_context,
                )
            )

    def test_transport_tamper_is_rejected(self) -> None:
        response = self._build()
        tampered = copy.deepcopy(response)
        tampered["transport"]["registered"] = True

        with self._upstream_verifiers():
            self.assertFalse(
                subject.verify_strategy_correlation_provider_evidence_http_candidate_response_v1(
                    tampered,
                    self.request,
                    protocol_verification_context=self.protocol_context,
                    provider_replay_verification_context=self.replay_context,
                )
            )

    def test_authority_is_permanently_research_only(self) -> None:
        response = self._build()

        self.assertTrue(response["authority"]["descriptive_only"])
        for field in (
            "current_admission_allowed",
            "current_pointer_written",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertFalse(response["authority"][field])

    def test_static_fingerprint_and_response_hash_shape_are_stable(self) -> None:
        response = self._build()

        self.assertEqual(response["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(response["response_hash"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
