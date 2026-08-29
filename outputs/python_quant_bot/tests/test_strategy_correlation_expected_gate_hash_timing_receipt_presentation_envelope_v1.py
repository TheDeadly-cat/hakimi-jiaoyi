from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_expected_gate_hash_timing_receipt as receipt_contract,
)
from tests import (
    test_strategy_correlation_expected_gate_hash_timing_receipt as receipt_fixtures,
)


_DEFAULT = object()


class StrategyCorrelationExpectedGateHashTimingReceiptPresentationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.receipt_case = (
            receipt_fixtures.StrategyCorrelationExpectedGateHashTimingReceiptTests(
                methodName="runTest"
            )
        )
        self.receipt, arguments = self.receipt_case._fixture(
            expected_receipt_id="private-receipt-marker"
        )
        self.context = {
            "schema_version": subject.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }

    def _build(self, *, receipt=_DEFAULT, context=_DEFAULT):
        return subject.build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
            self.receipt if receipt is _DEFAULT else receipt,
            verification_context=self.context if context is _DEFAULT else context,
        )

    def test_verified_candidate_renders_neutral_four_axis_envelope(self) -> None:
        document = self._build()

        self.assertEqual(document["presentation_status"], "UNMOUNTED_CANDIDATE")
        self.assertEqual(document["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [axis["axis"] for axis in document["axes"]],
            list(subject.AXIS_ORDER),
        )
        self.assertEqual(document["display_state"], subject.CANDIDATE_DISPLAY_STATE)
        self.assertTrue(document["facts"]["candidate_receipt_contract_verified"])
        self.assertEqual(document["axes"][1]["signal"], "BLOCKED")
        self.assertEqual(document["axes"][2]["signal"], "UNKNOWN")
        self.assertEqual(document["axes"][3]["signal"], "LOCKED")

    def test_candidate_contract_never_promotes_authority_or_maturity(self) -> None:
        document = self._build()

        self.assertEqual(document["summary"]["timing_authority"], "NOT_PROVEN")
        self.assertEqual(
            document["summary"]["preregistration_authority"], "NOT_PROVEN"
        )
        self.assertEqual(
            document["summary"]["natural_forward_maturity"], "NOT_PROVEN"
        )
        self.assertFalse(document["facts"]["timing_authority_verified"])
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertTrue(document["authority"]["descriptive_only"])
        for field, value in document["authority"].items():
            if field != "descriptive_only":
                self.assertIs(value, False)

    def test_receipt_bindings_and_context_are_not_embedded(self) -> None:
        document = self._build()
        serialized = json.dumps(document, sort_keys=True)

        self.assertNotIn("private-receipt-marker", serialized)
        self.assertNotIn("synthetic-uncertainty-audit-v1", serialized)
        self.assertFalse(document["lineage"]["source_receipt_embedded"])
        self.assertFalse(document["lineage"]["gate_bindings_embedded"])
        self.assertFalse(document["lineage"]["verification_context_embedded"])

    def test_invalid_context_is_exact_and_fails_closed(self) -> None:
        cases = [
            None,
            {},
            {**self.context, "unexpected": True},
            {**self.context, "schema_version": "wrong"},
        ]
        for context in cases:
            with self.subTest(context=context):
                document = self._build(context=context)
                self.assertEqual(document["display_state"], "UNKNOWN")
                self.assertTrue(
                    all(axis["state"] == "UNKNOWN" for axis in document["axes"])
                )

    def test_source_hash_drift_fails_closed_to_unknown(self) -> None:
        context = copy.deepcopy(self.context)
        context["expected_source_linkage_hash"] = "0" * 64

        document = self._build(context=context)

        self.assertEqual(document["display_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["SOURCE_RECEIPT_UNVERIFIED"])

    def test_source_verifier_exception_fails_closed(self) -> None:
        with patch.object(
            subject.receipt_contract,
            "verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate",
            side_effect=ValueError("synthetic verifier failure"),
        ):
            document = self._build()

        self.assertEqual(document["display_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["SOURCE_RECEIPT_VERIFIER_ERROR"])

    def test_forged_source_authority_is_rejected_even_with_pass(self) -> None:
        arguments = {
            key: value
            for key, value in self.context.items()
            if key != "schema_version"
        }
        verification = receipt_contract.verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate(
            self.receipt,
            **arguments,
        )
        verification["timing_authority_verified"] = True
        with patch.object(
            subject.receipt_contract,
            "verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate",
            return_value=verification,
        ):
            document = self._build()

        self.assertEqual(document["display_state"], "UNKNOWN")

    def test_exact_rebuild_verifier_is_deterministic(self) -> None:
        first = self._build()
        second = self._build()

        self.assertEqual(first, second)
        self.assertTrue(
            subject.verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
                first,
                self.receipt,
                verification_context=self.context,
            )
        )

    def test_tampered_permission_is_rejected(self) -> None:
        document = self._build()
        tampered = copy.deepcopy(document)
        tampered["authority"]["paper_authorized"] = True

        self.assertFalse(
            subject.verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
                tampered,
                self.receipt,
                verification_context=self.context,
            )
        )

    def test_presentation_contains_no_ready_signal(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True).upper()

        self.assertNotIn("READY", serialized)

    def test_static_fingerprint_and_hash_are_stable(self) -> None:
        document = self._build()

        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(document["presentation_hash"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
