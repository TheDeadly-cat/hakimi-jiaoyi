from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_downside_tail_gate import (
    build_strategy_correlation_downside_tail_registration,
    evaluate_strategy_correlation_downside_tail_gate,
)
from exchange_terminal.services.strategy_correlation_downside_tail_protocol import (
    BINDING_ASSESSMENT_SCHEMA,
    PROTOCOL_SCHEMA,
    STATIC_FINGERPRINT,
    assess_strategy_correlation_downside_tail_protocol_binding,
    build_strategy_correlation_downside_tail_protocol_registration,
    verify_strategy_correlation_downside_tail_protocol_binding_assessment,
    verify_strategy_correlation_downside_tail_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_downside_tail_report_consumer import (
    consume_strategy_correlation_downside_tail_evaluation,
)


class StrategyCorrelationDownsideTailProtocolTests(unittest.TestCase):
    def setUp(self):
        self.source_registration = build_strategy_correlation_downside_tail_registration(
            registration_id="downside-tail-protocol-1",
            stratum_by_identity={"A": "S1", "B": "S2"},
        )
        self.protocol = build_strategy_correlation_downside_tail_protocol_registration(
            self.source_registration
        )

    def _observations(self, *, joint=False, count=60, prefix="obs"):
        rows = []
        for index in range(count):
            left_tail = index < 12
            right_tail = index < 12 if joint else 12 <= index < 24
            rows.append(
                {
                    "observation_id": f"{prefix}-{index:03d}",
                    "returns": {
                        "A": -1.0 if left_tail else (0.0 if index % 2 == 0 else 2.0),
                        "B": -1.0 if right_tail else (2.0 if index % 2 == 0 else 0.0),
                    },
                }
            )
        return rows

    def _source(self, *, joint=False, count=60, prefix="obs"):
        evaluation = evaluate_strategy_correlation_downside_tail_gate(
            self.source_registration,
            self._observations(joint=joint, count=count, prefix=prefix),
            expected_registration_hash=self.source_registration["registration_hash"],
        )
        receipt = consume_strategy_correlation_downside_tail_evaluation(
            evaluation,
            registration=self.source_registration,
            expected_registration_hash=self.source_registration["registration_hash"],
            expected_evaluation_hash=evaluation["evaluation_hash"],
        )
        return evaluation, receipt

    def _assess(
        self,
        evaluation,
        receipt,
        *,
        protocol=None,
        protocol_hash=None,
        registration_hash=None,
        evaluation_hash=None,
    ):
        selected_protocol = self.protocol if protocol is None else protocol
        return assess_strategy_correlation_downside_tail_protocol_binding(
            selected_protocol,
            evaluation,
            receipt,
            source_registration=self.source_registration,
            expected_protocol_hash=(
                selected_protocol.get("protocol_hash")
                if protocol_hash is None
                else protocol_hash
            ),
            expected_registration_hash=(
                self.source_registration["registration_hash"]
                if registration_hash is None
                else registration_hash
            ),
            expected_evaluation_hash=(
                evaluation["evaluation_hash"]
                if evaluation_hash is None
                else evaluation_hash
            ),
        )

    def test_protocol_is_source_bound_and_contains_no_observed_outcome_hash(self):
        rebuilt = build_strategy_correlation_downside_tail_protocol_registration(
            copy.deepcopy(self.source_registration)
        )

        self.assertEqual(self.protocol, rebuilt)
        self.assertEqual(self.protocol["schema_version"], PROTOCOL_SCHEMA)
        self.assertEqual(self.protocol["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            self.protocol["source_registration_hash"],
            self.source_registration["registration_hash"],
        )
        self.assertNotIn("evaluation_hash", self.protocol)
        self.assertFalse(self.protocol["authority"]["registration_timing_attested"])

    def test_protocol_verification_receipt_passes_for_exact_document(self):
        receipt = verify_strategy_correlation_downside_tail_protocol_registration(
            self.protocol,
            source_registration=self.source_registration,
        )

        self.assertEqual(receipt["verification_status"], "PASS")
        self.assertTrue(receipt["protocol_contract_verified"])
        self.assertEqual(receipt["blockers"], [])

    def test_builder_rejects_invalid_source_registration(self):
        invalid = copy.deepcopy(self.source_registration)
        invalid["identity_count"] = 3
        with self.assertRaises(ValueError):
            build_strategy_correlation_downside_tail_protocol_registration(invalid)

    def test_resealed_protocol_target_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.protocol)
        tampered["target_consumer_schema"] = f"{tampered['target_consumer_schema']}-tampered"
        tampered.pop("protocol_hash")
        tampered = seal_strict_canonical_document(tampered, "protocol_hash")

        receipt = verify_strategy_correlation_downside_tail_protocol_registration(
            tampered,
            source_registration=self.source_registration,
        )
        self.assertEqual(receipt["verification_status"], "BLOCK")
        self.assertFalse(receipt["protocol_contract_verified"])

    def test_resealed_numeric_protocol_authority_alias_is_rejected(self):
        tampered = copy.deepcopy(self.protocol)
        tampered["authority"]["paper_authorized"] = 0
        tampered.pop("protocol_hash")
        tampered = seal_strict_canonical_document(tampered, "protocol_hash")

        receipt = verify_strategy_correlation_downside_tail_protocol_registration(
            tampered,
            source_registration=self.source_registration,
        )
        self.assertEqual(receipt["verification_status"], "BLOCK")

    def test_observed_pass_is_candidate_bound_only(self):
        evaluation, receipt = self._source()
        assessment = self._assess(evaluation, receipt)

        self.assertEqual(assessment["schema_version"], BINDING_ASSESSMENT_SCHEMA)
        self.assertEqual(assessment["assessment_status"], "PASS")
        self.assertEqual(assessment["gate_decision"], "PASS")
        self.assertEqual(assessment["binding_status"], "CANDIDATE_BOUND")
        self.assertFalse(assessment["authority"]["formal_report_binding_allowed"])

    def test_observed_block_is_also_candidate_bound_and_preserved(self):
        evaluation, receipt = self._source(joint=True)
        assessment = self._assess(evaluation, receipt)

        self.assertEqual(assessment["assessment_status"], "PASS")
        self.assertEqual(assessment["source_state"], "OBSERVED")
        self.assertEqual(assessment["gate_decision"], "BLOCK")
        self.assertEqual(assessment["binding_status"], "CANDIDATE_BOUND")
        self.assertEqual(assessment["source_blockers"], ["DOWNSIDE_TAIL_COUPLING_DETECTED"])

    def test_valid_unknown_source_is_candidate_blocked(self):
        evaluation, receipt = self._source(count=59)
        assessment = self._assess(evaluation, receipt)

        self.assertEqual(assessment["assessment_status"], "BLOCK")
        self.assertEqual(assessment["source_state"], "UNKNOWN")
        self.assertEqual(assessment["binding_status"], "CANDIDATE_BLOCKED")
        self.assertEqual(assessment["binding_blockers"], ["SOURCE_EVALUATION_UNKNOWN"])

    def test_expected_protocol_hash_mismatch_is_generic_unknown(self):
        evaluation, receipt = self._source()
        assessment = self._assess(evaluation, receipt, protocol_hash="0" * 64)

        self.assertEqual(assessment["binding_status"], "UNKNOWN")
        self.assertTrue(assessment["protocol_contract_verified"])
        self.assertFalse(assessment["protocol_hash_verified"])
        self.assertIsNone(assessment["protocol_hash"])

    def test_tampered_consumer_receipt_is_generic_unknown(self):
        evaluation, receipt = self._source()
        receipt["gate_decision"] = "BLOCK"
        assessment = self._assess(evaluation, receipt)

        self.assertEqual(assessment["binding_status"], "UNKNOWN")
        self.assertFalse(assessment["consumer_receipt_verified"])
        self.assertEqual(assessment["binding_blockers"], ["CONSUMER_RECEIPT_UNKNOWN"])

    def test_expected_evaluation_hash_mismatch_is_generic_unknown(self):
        evaluation, receipt = self._source()
        assessment = self._assess(evaluation, receipt, evaluation_hash="f" * 64)

        self.assertEqual(assessment["source_state"], "UNKNOWN")
        self.assertFalse(assessment["consumer_receipt_verified"])

    def test_exact_binding_assessment_verifies(self):
        evaluation, receipt = self._source(joint=True)
        assessment = self._assess(evaluation, receipt)

        self.assertTrue(
            verify_strategy_correlation_downside_tail_protocol_binding_assessment(
                assessment,
                self.protocol,
                evaluation,
                receipt,
                source_registration=self.source_registration,
                expected_protocol_hash=self.protocol["protocol_hash"],
                expected_registration_hash=self.source_registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_tampered_assessment_schema_does_not_verify(self):
        evaluation, receipt = self._source()
        assessment = self._assess(evaluation, receipt)
        assessment["schema_version"] = f"{assessment['schema_version']}-tampered"

        self.assertFalse(
            verify_strategy_correlation_downside_tail_protocol_binding_assessment(
                assessment,
                self.protocol,
                evaluation,
                receipt,
                source_registration=self.source_registration,
                expected_protocol_hash=self.protocol["protocol_hash"],
                expected_registration_hash=self.source_registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_resealed_numeric_assessment_authority_alias_does_not_verify(self):
        evaluation, receipt = self._source()
        assessment = self._assess(evaluation, receipt)
        assessment["authority"]["live_order_allowed"] = 0
        assessment.pop("assessment_hash")
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")

        self.assertFalse(
            verify_strategy_correlation_downside_tail_protocol_binding_assessment(
                assessment,
                self.protocol,
                evaluation,
                receipt,
                source_registration=self.source_registration,
                expected_protocol_hash=self.protocol["protocol_hash"],
                expected_registration_hash=self.source_registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_assessment_exposes_no_observations_pair_details_or_identities(self):
        evaluation, receipt = self._source(prefix="PRIVATE-OBSERVATION")
        assessment = self._assess(evaluation, receipt)
        encoded = json.dumps(assessment, sort_keys=True)

        self.assertNotIn("PRIVATE-OBSERVATION", encoded)
        self.assertNotIn('"returns"', encoded)
        self.assertNotIn('"left_identity"', encoded)
        self.assertNotIn('"right_identity"', encoded)
        self.assertNotIn('"stratum_by_identity"', encoded)

    def test_untrusted_protocol_text_is_never_reflected(self):
        evaluation, receipt = self._source()
        untrusted = {"protocol_hash": "f" * 64, "secret": "DO-NOT-REFLECT"}
        assessment = self._assess(evaluation, receipt, protocol=untrusted)

        self.assertNotIn("DO-NOT-REFLECT", json.dumps(assessment, sort_keys=True))
        self.assertEqual(assessment["binding_status"], "UNKNOWN")

    def test_binding_assessment_is_deterministic(self):
        evaluation, receipt = self._source(joint=True)
        self.assertEqual(
            self._assess(evaluation, receipt),
            self._assess(copy.deepcopy(evaluation), copy.deepcopy(receipt)),
        )


if __name__ == "__main__":
    unittest.main()
