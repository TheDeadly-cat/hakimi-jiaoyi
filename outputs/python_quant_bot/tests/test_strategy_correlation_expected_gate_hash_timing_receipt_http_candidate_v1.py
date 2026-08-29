from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_expected_gate_hash_timing_receipt_candidate_v1 as subject,
)
from tests import (
    test_strategy_correlation_expected_gate_hash_timing_receipt as receipt_fixtures,
)


_DEFAULT = object()


class StrategyCorrelationExpectedGateHashTimingReceiptHttpCandidateTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        receipt_case = (
            receipt_fixtures.StrategyCorrelationExpectedGateHashTimingReceiptTests(
                methodName="runTest"
            )
        )
        receipt, arguments = receipt_case._fixture(
            expected_receipt_id="private-http-receipt-marker"
        )
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "candidate_receipt": receipt,
        }
        self.context = {
            "schema_version": (
                subject.envelope_contract.VERIFICATION_CONTEXT_SCHEMA_VERSION
            ),
            **arguments,
        }

    def _build(self, *, request=_DEFAULT, context=_DEFAULT):
        return subject.build_strategy_correlation_expected_gate_hash_timing_receipt_http_candidate_response_v1(
            self.request if request is _DEFAULT else request,
            verification_context=self.context if context is _DEFAULT else context,
        )

    def test_verified_envelope_is_unregistered_observation(self) -> None:
        response = self._build()

        self.assertEqual(response["state"], "OBSERVED")
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertTrue(response["facts"]["source_envelope_verified"])
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
            {**self.request, "candidate_receipt": []},
        ]
        for request in cases:
            with self.subTest(request=request):
                response = self._build(request=request)
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])

    def test_invalid_context_fails_before_application_call(self) -> None:
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
        ) as builder:
            response = self._build(context=None)

        builder.assert_not_called()
        self.assertEqual(response["state"], "UNKNOWN")
        self.assertEqual(response["blockers"], ["VERIFICATION_CONTEXT_INVALID"])

    def test_verified_unknown_envelope_is_not_promoted(self) -> None:
        context = copy.deepcopy(self.context)
        context["expected_gate_commitment_hash"] = "0" * 64

        response = self._build(context=context)

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsInstance(response["payload"], dict)
        self.assertEqual(response["payload"]["display_state"], "UNKNOWN")
        self.assertTrue(response["facts"]["source_envelope_verified"])
        self.assertFalse(response["facts"]["result_available"])

    def test_application_builder_exception_fails_closed(self) -> None:
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
            side_effect=ValueError("synthetic failure"),
        ):
            response = self._build()

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_application_verification_false_fails_closed(self) -> None:
        with patch.object(
            subject.envelope_contract,
            "verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
            return_value=False,
        ):
            response = self._build()

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_forged_application_authority_promotion_is_rejected(self) -> None:
        envelope = subject.envelope_contract.build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
            self.request["candidate_receipt"],
            verification_context=self.context,
        )
        envelope["authority"]["paper_authorized"] = True
        with patch.object(
            subject.envelope_contract,
            "build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
            return_value=envelope,
        ), patch.object(
            subject.envelope_contract,
            "verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
            return_value=True,
        ):
            response = self._build()

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])

    def test_request_and_context_values_are_not_echoed(self) -> None:
        response = self._build()
        serialized = json.dumps(response, sort_keys=True)

        self.assertNotIn("private-http-receipt-marker", serialized)
        self.assertNotIn("synthetic-uncertainty-audit-v1", serialized)
        self.assertFalse(response["lineage"]["request_documents_embedded"])
        self.assertFalse(response["lineage"]["verification_context_embedded"])

    def test_exact_rebuild_response_is_deterministic(self) -> None:
        first = self._build()
        second = self._build()

        self.assertEqual(first, second)
        self.assertTrue(
            subject.verify_strategy_correlation_expected_gate_hash_timing_receipt_http_candidate_response_v1(
                first,
                self.request,
                verification_context=self.context,
            )
        )

    def test_transport_tamper_is_rejected(self) -> None:
        response = self._build()
        tampered = copy.deepcopy(response)
        tampered["transport"]["registered"] = True

        self.assertFalse(
            subject.verify_strategy_correlation_expected_gate_hash_timing_receipt_http_candidate_response_v1(
                tampered,
                self.request,
                verification_context=self.context,
            )
        )

    def test_authority_is_research_only_and_no_ready_signal_exists(self) -> None:
        response = self._build()

        self.assertTrue(response["authority"]["descriptive_only"])
        for field, value in response["authority"].items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(response, sort_keys=True).upper())

    def test_static_fingerprint_and_response_hash_are_stable(self) -> None:
        response = self._build()

        self.assertEqual(response["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(response["response_hash"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
