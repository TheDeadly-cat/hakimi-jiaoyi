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
    verify_strategy_correlation_downside_tail_evaluation,
)
from exchange_terminal.services.strategy_correlation_downside_tail_report_consumer import (
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA,
    consume_strategy_correlation_downside_tail_evaluation,
    verify_strategy_correlation_downside_tail_consumer_receipt,
)


class StrategyCorrelationDownsideTailReportConsumerTests(unittest.TestCase):
    def setUp(self):
        self.registration = build_strategy_correlation_downside_tail_registration(
            registration_id="downside-tail-consumer-1",
            stratum_by_identity={"A": "S1", "B": "S2"},
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

    def _evaluation(self, *, joint=False, count=60, prefix="obs"):
        return evaluate_strategy_correlation_downside_tail_gate(
            self.registration,
            self._observations(joint=joint, count=count, prefix=prefix),
            expected_registration_hash=self.registration["registration_hash"],
        )

    def _consume(self, evaluation, *, registration_hash=None, evaluation_hash=None):
        return consume_strategy_correlation_downside_tail_evaluation(
            evaluation,
            registration=self.registration,
            expected_registration_hash=(
                self.registration["registration_hash"]
                if registration_hash is None
                else registration_hash
            ),
            expected_evaluation_hash=(
                evaluation["evaluation_hash"]
                if evaluation_hash is None
                else evaluation_hash
            ),
        )

    def test_pass_evaluation_is_hash_bound_but_never_formal(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation)

        self.assertEqual(receipt["schema_version"], VERIFICATION_SCHEMA)
        self.assertEqual(receipt["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(receipt["verification_status"], "PASS")
        self.assertEqual(receipt["gate_decision"], "PASS")
        self.assertEqual(receipt["candidate_binding_status"], "CANDIDATE_HASH_BOUND_NOT_FORMAL")
        self.assertTrue(receipt["semantic_contract_verified"])
        self.assertFalse(receipt["authority"]["formal_report_binding_allowed"])
        self.assertFalse(receipt["authority"]["count_as_independent_allowed"])

    def test_valid_block_remains_observed_and_visible(self):
        evaluation = self._evaluation(joint=True)
        receipt = self._consume(evaluation)

        self.assertEqual(receipt["verification_status"], "PASS")
        self.assertEqual(receipt["source_state"], "OBSERVED")
        self.assertEqual(receipt["gate_decision"], "BLOCK")
        self.assertEqual(receipt["coupled_pair_count"], 1)
        self.assertEqual(receipt["source_blockers"], ["DOWNSIDE_TAIL_COUPLING_DETECTED"])

    def test_valid_unknown_source_is_bound_but_not_presented_as_observed(self):
        evaluation = self._evaluation(count=59)
        receipt = self._consume(evaluation)

        self.assertEqual(receipt["verification_status"], "BLOCK")
        self.assertEqual(receipt["source_state"], "UNKNOWN")
        self.assertEqual(receipt["gate_decision"], "BLOCK")
        self.assertTrue(receipt["semantic_contract_verified"])
        self.assertEqual(receipt["verification_blockers"], ["SOURCE_EVALUATION_UNKNOWN"])

    def test_registration_hash_mismatch_returns_generic_unknown(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation, registration_hash="0" * 64)

        self.assertEqual(receipt["source_state"], "UNKNOWN")
        self.assertFalse(receipt["registration_hash_verified"])
        self.assertFalse(receipt["semantic_contract_verified"])
        self.assertIsNone(receipt["registration_hash"])

    def test_evaluation_hash_mismatch_returns_generic_unknown(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation, evaluation_hash="f" * 64)

        self.assertEqual(receipt["gate_decision"], "UNKNOWN")
        self.assertFalse(receipt["evaluation_hash_verified"])
        self.assertFalse(receipt["semantic_contract_verified"])
        self.assertIsNone(receipt["evaluation_hash"])

    def test_resealed_p_value_tamper_is_rejected(self):
        evaluation = self._evaluation(joint=True)
        tampered = copy.deepcopy(evaluation)
        tampered["pair_results"][0]["raw_p_value"] = "1"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")

        self.assertFalse(
            verify_strategy_correlation_downside_tail_evaluation(
                tampered,
                self.registration,
                expected_registration_hash=self.registration["registration_hash"],
                expected_evaluation_hash=tampered["evaluation_hash"],
            )
        )
        self.assertEqual(self._consume(tampered)["source_state"], "UNKNOWN")

    def test_resealed_pair_scope_tamper_is_rejected(self):
        evaluation = self._evaluation()
        tampered = copy.deepcopy(evaluation)
        tampered["pair_results"][0]["right_stratum"] = "S1"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")

        self.assertEqual(self._consume(tampered)["gate_reason"], "EVALUATION_CONTRACT_UNKNOWN")

    def test_resealed_decision_tamper_is_rejected(self):
        evaluation = self._evaluation()
        tampered = copy.deepcopy(evaluation)
        tampered["gate_decision"] = "BLOCK"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")

        self.assertFalse(self._consume(tampered)["semantic_contract_verified"])

    def test_numeric_evaluation_authority_alias_is_rejected(self):
        evaluation = self._evaluation()
        tampered = copy.deepcopy(evaluation)
        tampered["authority"]["paper_authorized"] = 0
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")

        self.assertEqual(self._consume(tampered)["source_state"], "UNKNOWN")

    def test_exact_consumer_receipt_verifies(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation)

        self.assertTrue(
            verify_strategy_correlation_downside_tail_consumer_receipt(
                receipt,
                evaluation,
                registration=self.registration,
                expected_registration_hash=self.registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_tampered_receipt_schema_does_not_verify(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation)
        receipt["schema_version"] = f"{receipt['schema_version']}-tampered"

        self.assertFalse(
            verify_strategy_correlation_downside_tail_consumer_receipt(
                receipt,
                evaluation,
                registration=self.registration,
                expected_registration_hash=self.registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_resealed_numeric_receipt_authority_alias_does_not_verify(self):
        evaluation = self._evaluation()
        receipt = self._consume(evaluation)
        receipt["authority"]["live_order_allowed"] = 0
        receipt.pop("verification_hash")
        receipt = seal_strict_canonical_document(receipt, "verification_hash")

        self.assertFalse(
            verify_strategy_correlation_downside_tail_consumer_receipt(
                receipt,
                evaluation,
                registration=self.registration,
                expected_registration_hash=self.registration["registration_hash"],
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_receipt_does_not_expose_observation_ids_returns_or_pair_identities(self):
        evaluation = self._evaluation(prefix="PRIVATE-OBSERVATION")
        receipt = self._consume(evaluation)
        encoded = json.dumps(receipt, sort_keys=True)

        self.assertNotIn("PRIVATE-OBSERVATION", encoded)
        self.assertNotIn('"returns"', encoded)
        self.assertNotIn('"left_identity"', encoded)
        self.assertNotIn('"right_identity"', encoded)

    def test_untrusted_input_text_is_never_reflected(self):
        receipt = consume_strategy_correlation_downside_tail_evaluation(
            {"schema_version": "PRIVATE-DO-NOT-REFLECT"},
            registration=self.registration,
            expected_registration_hash=self.registration["registration_hash"],
            expected_evaluation_hash="f" * 64,
        )
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", json.dumps(receipt, sort_keys=True))

    def test_consumption_is_deterministic(self):
        evaluation = self._evaluation(joint=True)
        self.assertEqual(self._consume(evaluation), self._consume(copy.deepcopy(evaluation)))


if __name__ == "__main__":
    unittest.main()
