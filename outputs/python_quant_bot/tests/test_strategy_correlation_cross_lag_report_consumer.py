from __future__ import annotations

import copy
import json
import math
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_report_consumer import (
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA,
    consume_strategy_correlation_cross_lag_evaluation,
    verify_strategy_correlation_cross_lag_consumer_receipt,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cross_lag_gate import (
    StrategyCorrelationCrossLagGateTests,
)


class StrategyCorrelationCrossLagReportConsumerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = StrategyCorrelationCrossLagGateTests()
        self.fixture.setUp()
        self.strata = copy.deepcopy(self.fixture.strata)
        self.strata_hash = self.fixture.strata_hash

    def _source(self, series):
        rows = self.fixture._rows(series)
        evaluation = evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            rows,
            expected_stratum_assignment_hash=self.strata_hash,
        )
        return rows, evaluation

    def _consume(
        self,
        evaluation,
        rows,
        *,
        expected_evaluation_hash=None,
        strata=None,
        strata_hash=None,
    ):
        if expected_evaluation_hash is None:
            expected_evaluation_hash = evaluation.get("evaluation_hash", "") if isinstance(evaluation, dict) else ""
        return consume_strategy_correlation_cross_lag_evaluation(
            evaluation,
            preregistered_strata=self.strata if strata is None else strata,
            aligned_observations=rows,
            expected_stratum_assignment_hash=self.strata_hash if strata_hash is None else strata_hash,
            expected_evaluation_hash=expected_evaluation_hash,
        )

    def _reseal(self, evaluation):
        evaluation.pop("evaluation_hash", None)
        return seal_strict_canonical_document(evaluation, "evaluation_hash")

    def _assert_locked(self, receipt):
        self.assertTrue(receipt["authority"]["descriptive_only"])
        for key, value in receipt["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)
        self.assertEqual(receipt["permission_state"], "LOCKED")

    def test_valid_independent_evaluation_is_observed_pass_but_candidate_only(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        receipt = self._consume(evaluation, rows)
        self.assertEqual(receipt["schema_version"], VERIFICATION_SCHEMA)
        self.assertEqual(receipt["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(receipt["report_state"], "OBSERVED_PASS")
        self.assertEqual(receipt["maturity_state"], "CANDIDATE_EVALUATED_NOT_FORMAL")
        self.assertEqual(receipt["dependent_test_count"], 0)
        self.assertNotIn("lag_results", receipt)
        self._assert_locked(receipt)
        self.assertTrue(
            verify_strategy_correlation_cross_lag_consumer_receipt(
                receipt,
                evaluation,
                preregistered_strata=self.strata,
                aligned_observations=rows,
                expected_stratum_assignment_hash=self.strata_hash,
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_valid_dependence_remains_visible_as_observed_block(self):
        rows, evaluation = self._source(self.fixture._shifted_series())
        receipt = self._consume(evaluation, rows)
        self.assertEqual(receipt["report_state"], "OBSERVED_BLOCK")
        self.assertEqual(receipt["gate_decision"], "BLOCK")
        self.assertGreater(receipt["dependent_test_count"], 0)
        self.assertEqual(receipt["blockers"], ["CROSS_LAG_DEPENDENCE_DETECTED"])
        self._assert_locked(receipt)

    def test_missing_evaluation_is_distinct_from_invalid_supplied(self):
        missing = self._consume(None, [], expected_evaluation_hash="0" * 64)
        invalid = self._consume([], [], expected_evaluation_hash="0" * 64)
        self.assertEqual(missing["report_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["report_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_hash_or_strata_hash_mismatch_fails_closed(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        self.assertEqual(
            self._consume(evaluation, rows, expected_evaluation_hash="f" * 64)["report_state"],
            "UNKNOWN",
        )
        self.assertEqual(
            self._consume(evaluation, rows, strata_hash="e" * 64)["report_state"],
            "UNKNOWN",
        )

    def test_schema_and_fingerprint_drift_fail_closed_after_reseal(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        for field, value in (
            ("schema_version", "strategy-correlation-cross-lag-gate-candidate-v999"),
            ("static_fingerprint", "drifted-fingerprint"),
        ):
            with self.subTest(field=field):
                tampered = copy.deepcopy(evaluation)
                tampered[field] = value
                tampered = self._reseal(tampered)
                self.assertEqual(self._consume(tampered, rows)["report_state"], "UNKNOWN")

    def test_broken_hash_and_coherently_resealed_metric_tamper_fail_closed(self):
        rows, evaluation = self._source(self.fixture._shifted_series())
        broken = copy.deepcopy(evaluation)
        target = next(item for item in broken["lag_results"] if item["dependent"])
        self.assertNotEqual(target["adjusted_absolute_lower"], "0")
        target["adjusted_absolute_lower"] = "0"
        self.assertEqual(
            self._consume(broken, rows, expected_evaluation_hash=evaluation["evaluation_hash"])["report_state"],
            "UNKNOWN",
        )

        resealed = self._reseal(copy.deepcopy(broken))
        self.assertEqual(self._consume(resealed, rows)["report_state"], "UNKNOWN")

    def test_missing_reordered_or_extra_lag_fails_closed(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        variants = []
        missing = copy.deepcopy(evaluation)
        missing["lag_family"] = missing["lag_family"][:-1]
        variants.append(missing)
        reordered = copy.deepcopy(evaluation)
        reordered["lag_family"] = list(reversed(reordered["lag_family"]))
        variants.append(reordered)
        extra = copy.deepcopy(evaluation)
        extra["lag_family"].append(3)
        variants.append(extra)
        for index, tampered in enumerate(variants):
            with self.subTest(index=index):
                tampered = self._reseal(tampered)
                self.assertEqual(self._consume(tampered, rows)["report_state"], "UNKNOWN")

    def test_missing_duplicate_or_extra_pair_lag_result_fails_closed(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        variants = []
        missing = copy.deepcopy(evaluation)
        missing["lag_results"].pop()
        missing["lag_test_count"] -= 1
        variants.append(missing)
        duplicate = copy.deepcopy(evaluation)
        duplicate["lag_results"].append(copy.deepcopy(duplicate["lag_results"][0]))
        duplicate["lag_test_count"] += 1
        variants.append(duplicate)
        extra = copy.deepcopy(evaluation)
        extra_result = copy.deepcopy(extra["lag_results"][0])
        extra_result["lag"] = 3
        extra["lag_results"].append(extra_result)
        extra["lag_test_count"] += 1
        variants.append(extra)
        for index, tampered in enumerate(variants):
            with self.subTest(index=index):
                tampered = self._reseal(tampered)
                self.assertEqual(self._consume(tampered, rows)["report_state"], "UNKNOWN")

    def test_pair_count_and_decision_evidence_mismatch_fail_closed(self):
        rows, evaluation = self._source(self.fixture._shifted_series())
        pair_drift = copy.deepcopy(evaluation)
        pair_drift["cross_stratum_pair_count"] += 1
        pair_drift = self._reseal(pair_drift)
        self.assertEqual(self._consume(pair_drift, rows)["report_state"], "UNKNOWN")

        decision_drift = copy.deepcopy(evaluation)
        decision_drift["gate_decision"] = "PASS"
        decision_drift["gate_reason"] = "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_DETECTED"
        decision_drift["blockers"] = []
        decision_drift = self._reseal(decision_drift)
        self.assertEqual(self._consume(decision_drift, rows)["report_state"], "UNKNOWN")

    def test_nonfinite_and_pseudo_numeric_metrics_fail_closed(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        nonfinite = copy.deepcopy(evaluation)
        nonfinite["lag_results"][0]["correlation"] = math.nan
        self.assertEqual(
            self._consume(nonfinite, rows, expected_evaluation_hash=evaluation["evaluation_hash"])["report_state"],
            "UNKNOWN",
        )
        for value in ("NaN", "Infinity", True):
            with self.subTest(value=value):
                pseudo = copy.deepcopy(evaluation)
                pseudo["lag_results"][0]["correlation"] = value
                pseudo = self._reseal(pseudo)
                self.assertEqual(self._consume(pseudo, rows)["report_state"], "UNKNOWN")

    def test_authority_aliases_fail_closed(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        for value in (0, "", "false"):
            with self.subTest(value=value):
                tampered = copy.deepcopy(evaluation)
                tampered["authority"]["paper_authorized"] = value
                tampered = self._reseal(tampered)
                self.assertEqual(self._consume(tampered, rows)["report_state"], "UNKNOWN")

    def test_extra_untrusted_fields_are_not_reflected(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        tampered = copy.deepcopy(evaluation)
        tampered["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        tampered = self._reseal(tampered)
        receipt = self._consume(tampered, rows)
        self.assertEqual(receipt["report_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", json.dumps(receipt))

    def test_source_replay_mismatch_fails_closed(self):
        rows, evaluation = self._source(self.fixture._shifted_series())
        other_rows = self.fixture._rows(self.fixture._independent_series())
        self.assertEqual(self._consume(evaluation, other_rows)["report_state"], "UNKNOWN")

    def test_resealed_receipt_tamper_does_not_verify(self):
        rows, evaluation = self._source(self.fixture._shifted_series())
        receipt = self._consume(evaluation, rows)
        tampered = copy.deepcopy(receipt)
        tampered["dependent_test_count"] = 0
        tampered.pop("verification_hash")
        tampered = seal_strict_canonical_document(tampered, "verification_hash")
        self.assertFalse(
            verify_strategy_correlation_cross_lag_consumer_receipt(
                tampered,
                evaluation,
                preregistered_strata=self.strata,
                aligned_observations=rows,
                expected_stratum_assignment_hash=self.strata_hash,
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )

    def test_non_mapping_receipt_never_verifies(self):
        rows, evaluation = self._source(self.fixture._independent_series())
        self.assertFalse(
            verify_strategy_correlation_cross_lag_consumer_receipt(
                [],
                evaluation,
                preregistered_strata=self.strata,
                aligned_observations=rows,
                expected_stratum_assignment_hash=self.strata_hash,
                expected_evaluation_hash=evaluation["evaluation_hash"],
            )
        )


if __name__ == "__main__":
    unittest.main()
