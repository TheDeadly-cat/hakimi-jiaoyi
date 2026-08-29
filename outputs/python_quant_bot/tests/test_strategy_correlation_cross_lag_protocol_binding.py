from __future__ import annotations

import copy
import random
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_protocol import (
    BINDING_ASSESSMENT_SCHEMA,
    BINDING_ASSESSMENT_STATIC_FINGERPRINT,
    assess_strategy_correlation_cross_lag_protocol_binding,
    verify_strategy_correlation_cross_lag_protocol_binding_assessment,
)
from exchange_terminal.services.strategy_correlation_cross_lag_report_consumer import (
    consume_strategy_correlation_cross_lag_evaluation,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cross_lag_gate import (
    StrategyCorrelationCrossLagGateTests,
)
from tests.test_strategy_correlation_cross_lag_protocol import (
    StrategyCorrelationCrossLagProtocolRegistrationTests,
)


class StrategyCorrelationCrossLagProtocolBindingTests(unittest.TestCase):
    def setUp(self):
        self.registration_fixture = StrategyCorrelationCrossLagProtocolRegistrationTests()
        self.registration_fixture.setUp()
        self.protocol_registration = self.registration_fixture._build()
        self.p1b_fixture = self.registration_fixture.fixture
        self.gate_fixture = StrategyCorrelationCrossLagGateTests()
        self.gate_fixture.setUp()
        self.rows, self.evaluation, self.receipt = self._observed(block=False, seed=20260823)

    def _observed(self, *, block, seed):
        rng = random.Random(seed)
        identities = sorted(self.p1b_fixture.assignment)
        series = {
            identity: [rng.uniform(-1.0, 1.0) for _ in range(128)]
            for identity in identities
        }
        if block:
            leader, follower = identities[:2]
            series[follower] = [rng.uniform(-1.0, 1.0)] + series[leader][:-1]
        rows = self.gate_fixture._rows(series)
        evaluation = evaluate_strategy_correlation_cross_lag_gate(
            self.p1b_fixture.adapter["stratum_assignment"],
            rows,
            expected_stratum_assignment_hash=self.p1b_fixture.assignment_hash,
        )
        receipt = consume_strategy_correlation_cross_lag_evaluation(
            evaluation,
            preregistered_strata=self.p1b_fixture.adapter["stratum_assignment"],
            aligned_observations=rows,
            expected_stratum_assignment_hash=self.p1b_fixture.assignment_hash,
            expected_evaluation_hash=evaluation["evaluation_hash"],
        )
        return rows, evaluation, receipt

    def _values(self):
        values = self.registration_fixture._values()
        return {
            "protocol_registration": self.protocol_registration,
            "evaluation": self.evaluation,
            "consumer_receipt": self.receipt,
            **values,
            "aligned_observations": self.rows,
            "expected_protocol_registration_hash": self.protocol_registration["protocol_registration_hash"],
            "expected_evaluation_hash": self.evaluation["evaluation_hash"],
            "expected_consumer_receipt_hash": self.receipt["verification_hash"],
        }

    def _build(self, **overrides):
        values = self._values()
        values.update(overrides)
        return assess_strategy_correlation_cross_lag_protocol_binding(
            values.pop("protocol_registration"),
            values.pop("preregistration_adapter_binding"),
            values.pop("evaluation"),
            values.pop("consumer_receipt"),
            **values,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_protocol_binding_assessment(
            document,
            values.pop("protocol_registration"),
            values.pop("preregistration_adapter_binding"),
            values.pop("evaluation"),
            values.pop("consumer_receipt"),
            **values,
        )

    def _assert_locked(self, document):
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_valid_pass_remains_candidate_with_sequence_and_projection_gaps(self):
        assessment = self._build()
        self.assertEqual(assessment["schema_version"], BINDING_ASSESSMENT_SCHEMA)
        self.assertEqual(assessment["static_fingerprint"], BINDING_ASSESSMENT_STATIC_FINGERPRINT)
        self.assertEqual(assessment["assessment_state"], "OBSERVED_PASS_CANDIDATE_PROTOCOL")
        self.assertEqual(assessment["maturity_state"], "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL")
        self.assertEqual(
            assessment["blockers"],
            [
                "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
                "CROSS_LAG_C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED",
            ],
        )
        self.assertTrue(all(assessment["facts"].values()))
        self._assert_locked(assessment)

    def test_valid_dependence_remains_visible_as_block(self):
        rows, evaluation, receipt = self._observed(block=True, seed=20260824)
        assessment = self._build(
            aligned_observations=rows,
            evaluation=evaluation,
            consumer_receipt=receipt,
            expected_evaluation_hash=evaluation["evaluation_hash"],
            expected_consumer_receipt_hash=receipt["verification_hash"],
        )
        self.assertEqual(assessment["assessment_state"], "OBSERVED_BLOCK_CANDIDATE_PROTOCOL")
        self.assertEqual(assessment["gate_decision"], "BLOCK")
        self.assertGreater(assessment["dependent_test_count"], 0)
        self.assertEqual(assessment["blockers"][0], "CROSS_LAG_DEPENDENCE_DETECTED")
        self._assert_locked(assessment)

    def test_valid_pass_and_block_exactly_verify(self):
        self.assertTrue(self._verify(self._build()))
        rows, evaluation, receipt = self._observed(block=True, seed=20260825)
        overrides = {
            "aligned_observations": rows,
            "evaluation": evaluation,
            "consumer_receipt": receipt,
            "expected_evaluation_hash": evaluation["evaluation_hash"],
            "expected_consumer_receipt_hash": receipt["verification_hash"],
        }
        assessment = self._build(**overrides)
        self.assertTrue(self._verify(assessment, **overrides))

    def test_missing_is_distinct_from_invalid_supplied(self):
        missing = self._build(
            protocol_registration=None,
            preregistration_adapter_binding=None,
            evaluation=None,
            consumer_receipt=None,
        )
        invalid = self._build(
            protocol_registration=[],
            preregistration_adapter_binding=[],
            evaluation=[],
            consumer_receipt=[],
        )
        self.assertEqual(missing["assessment_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["assessment_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_hash_mismatches_fail_closed(self):
        fields = [
            "expected_protocol_registration_hash",
            "expected_preregistration_adapter_binding_hash",
            "expected_evaluation_hash",
            "expected_consumer_receipt_hash",
            "expected_strata_protocol_registration_hash",
            "expected_registry_assignment_adapter_hash",
            "expected_direction_contract_hash",
            "expected_registry_asset_hash",
            "expected_classification_source_hash",
            "expected_stratum_assignment_hash",
        ]
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(self._build(**{field: "f" * 64})["assessment_state"], "UNKNOWN")

    def test_other_valid_evaluation_with_original_expectation_fails_closed(self):
        rows, evaluation, _ = self._observed(block=False, seed=20260901)
        assessment = self._build(aligned_observations=rows, evaluation=evaluation)
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_other_valid_receipt_with_original_expectation_fails_closed(self):
        _, _, receipt = self._observed(block=True, seed=20260902)
        assessment = self._build(consumer_receipt=receipt)
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_coherently_resealed_nondefault_metric_tamper_fails_closed(self):
        rows, evaluation, _ = self._observed(block=True, seed=20260903)
        tampered = copy.deepcopy(evaluation)
        target = next(item for item in tampered["lag_results"] if item["dependent"])
        self.assertNotEqual(target["adjusted_absolute_lower"], "0")
        target["adjusted_absolute_lower"] = "0"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")
        assessment = self._build(
            aligned_observations=rows,
            evaluation=tampered,
            expected_evaluation_hash=tampered["evaluation_hash"],
        )
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_resealed_receipt_decision_and_count_tamper_fail_closed(self):
        for field, value in (("gate_decision", "BLOCK"), ("dependent_test_count", 999)):
            with self.subTest(field=field):
                receipt = copy.deepcopy(self.receipt)
                receipt[field] = value
                receipt.pop("verification_hash")
                receipt = seal_strict_canonical_document(receipt, "verification_hash")
                assessment = self._build(
                    consumer_receipt=receipt,
                    expected_consumer_receipt_hash=receipt["verification_hash"],
                )
                self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_resealed_registration_and_p1b_tamper_fail_closed(self):
        registration = copy.deepcopy(self.protocol_registration)
        registration["analytic_policy_hash"] = "d" * 64
        registration.pop("protocol_registration_hash")
        registration = seal_strict_canonical_document(registration, "protocol_registration_hash")
        self.assertEqual(
            self._build(
                protocol_registration=registration,
                expected_protocol_registration_hash=registration["protocol_registration_hash"],
            )["assessment_state"],
            "UNKNOWN",
        )
        binding = copy.deepcopy(self.registration_fixture.binding)
        binding["cluster_preregistration_hash"] = "d" * 64
        binding.pop("binding_hash")
        binding = seal_strict_canonical_document(binding, "binding_hash")
        self.assertEqual(
            self._build(
                preregistration_adapter_binding=binding,
                expected_preregistration_adapter_binding_hash=binding["binding_hash"],
            )["assessment_state"],
            "UNKNOWN",
        )

    def test_assignment_replay_mismatch_fails_closed(self):
        adapter = copy.deepcopy(self.p1b_fixture.adapter)
        adapter["stratum_assignment_hash"] = "d" * 64
        adapter.pop("adapter_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_hash")
        assessment = self._build(
            registry_assignment_adapter=adapter,
            expected_registry_assignment_adapter_hash=adapter["adapter_hash"],
        )
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_authority_aliases_fail_closed(self):
        for value in (0, "", "false", True):
            with self.subTest(value=value):
                receipt = copy.deepcopy(self.receipt)
                receipt["authority"]["paper_authorized"] = value
                receipt.pop("verification_hash")
                receipt = seal_strict_canonical_document(receipt, "verification_hash")
                assessment = self._build(
                    consumer_receipt=receipt,
                    expected_consumer_receipt_hash=receipt["verification_hash"],
                )
                self.assertEqual(assessment["assessment_state"], "UNKNOWN")

    def test_extra_untrusted_source_field_is_not_reflected(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        receipt.pop("verification_hash")
        receipt = seal_strict_canonical_document(receipt, "verification_hash")
        assessment = self._build(
            consumer_receipt=receipt,
            expected_consumer_receipt_hash=receipt["verification_hash"],
        )
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", str(assessment))

    def test_verifier_exception_fails_closed(self):
        with patch(
            "exchange_terminal.services.strategy_correlation_cross_lag_protocol.verify_strategy_correlation_cross_lag_evaluation",
            side_effect=RuntimeError("adversarial verifier fault"),
        ):
            assessment = self._build()
        self.assertEqual(assessment["assessment_state"], "UNKNOWN")
        self._assert_locked(assessment)

    def test_resealed_assessment_tamper_does_not_verify(self):
        assessment = self._build()
        tampered = copy.deepcopy(assessment)
        tampered["authority"]["sequence_order_attested"] = True
        tampered.pop("binding_assessment_hash")
        tampered = seal_strict_canonical_document(tampered, "binding_assessment_hash")
        self.assertFalse(self._verify(tampered))

    def test_non_mapping_assessment_never_verifies(self):
        self.assertFalse(self._verify([]))

    def test_output_is_aggregate_and_contains_no_raw_evidence(self):
        assessment = self._build()
        forbidden = {
            "stratum_assignment",
            "identity_set",
            "lag_results",
            "aligned_observations",
            "returns",
            "return_series",
            "local_path",
            "url",
            "callback",
        }
        self.assertFalse(forbidden.intersection(assessment))


if __name__ == "__main__":
    unittest.main()
