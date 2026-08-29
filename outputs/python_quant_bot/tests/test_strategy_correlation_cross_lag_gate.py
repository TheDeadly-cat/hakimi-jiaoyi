from __future__ import annotations

import copy
import json
import math
import random
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA,
    LAGS,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_gate,
    verify_strategy_correlation_cross_lag_evaluation,
)


class StrategyCorrelationCrossLagGateTests(unittest.TestCase):
    def setUp(self):
        self.strata = {"A": "S1", "B": "S2"}
        self.strata_hash = strict_canonical_hash(self.strata)

    def _rows(self, series, *, prefix="obs"):
        count = len(next(iter(series.values())))
        return [
            {
                "sequence_number": index,
                "observation_id": f"{prefix}-{index:03d}",
                "returns": {identity: values[index] for identity, values in series.items()},
            }
            for index in range(count)
        ]

    def _independent_series(self, count=96):
        left_rng = random.Random(173)
        right_rng = random.Random(941)
        return {
            "A": [left_rng.uniform(-1.0, 1.0) for _ in range(count)],
            "B": [right_rng.uniform(-1.0, 1.0) for _ in range(count)],
        }

    def _shifted_series(self, count=96):
        left = [1.0, 1.0, -1.0, -1.0] * (count // 4)
        right = [left[-1], *left[:-1]]
        return {"A": left, "B": right}

    def _evaluate(self, series, *, strata=None, expected_hash=None, prefix="obs"):
        selected_strata = self.strata if strata is None else strata
        selected_hash = (
            strict_canonical_hash(dict(sorted(selected_strata.items())))
            if expected_hash is None
            else expected_hash
        )
        return evaluate_strategy_correlation_cross_lag_gate(
            selected_strata,
            self._rows(series, prefix=prefix),
            expected_stratum_assignment_hash=selected_hash,
        )

    def test_candidate_strata_hash_is_bound_but_timing_is_unattested(self):
        result = self._evaluate(self._independent_series())

        self.assertEqual(result["schema_version"], EVALUATION_SCHEMA)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["stratum_assignment_hash"], self.strata_hash)
        self.assertFalse(result["authority"]["strata_timing_attested"])
        self.assertFalse(result["authority"]["count_as_independent_allowed"])

    def test_expected_strata_hash_mismatch_fails_closed(self):
        result = self._evaluate(self._independent_series(), expected_hash="0" * 64)
        self.assertEqual(result["source_state"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "EXPECTED_STRATUM_ASSIGNMENT_HASH_MISMATCH")

    def test_single_stratum_mapping_fails_closed(self):
        strata = {"A": "S1", "B": "S1"}
        result = self._evaluate(self._independent_series(), strata=strata)
        self.assertEqual(result["gate_reason"], "STRATA_CONTRACT_INVALID")

    def test_sequence_numbers_must_be_contiguous_and_ordered(self):
        rows = self._rows(self._independent_series())
        rows[1]["sequence_number"] = 2
        result = evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            rows,
            expected_stratum_assignment_hash=self.strata_hash,
        )
        self.assertEqual(result["gate_reason"], "OBSERVATION_SEQUENCE_INVALID")

    def test_reordered_rows_fail_closed_instead_of_silently_realigning(self):
        rows = list(reversed(self._rows(self._independent_series())))
        result = evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            rows,
            expected_stratum_assignment_hash=self.strata_hash,
        )
        self.assertEqual(result["gate_reason"], "OBSERVATION_SEQUENCE_INVALID")

    def test_duplicate_observation_ids_fail_closed(self):
        rows = self._rows(self._independent_series())
        rows[1]["observation_id"] = rows[0]["observation_id"]
        result = evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            rows,
            expected_stratum_assignment_hash=self.strata_hash,
        )
        self.assertEqual(result["gate_reason"], "OBSERVATION_ID_INVALID_OR_DUPLICATE")

    def test_exact_identity_set_is_required(self):
        rows = self._rows(self._independent_series())
        rows[0]["returns"].pop("B")
        result = evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            rows,
            expected_stratum_assignment_hash=self.strata_hash,
        )
        self.assertEqual(result["gate_reason"], "OBSERVATION_IDENTITY_SET_MISMATCH")

    def test_bool_and_nonfinite_returns_fail_closed(self):
        for invalid in (True, float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid=invalid):
                rows = self._rows(self._independent_series())
                rows[0]["returns"]["A"] = invalid
                result = evaluate_strategy_correlation_cross_lag_gate(
                    self.strata,
                    rows,
                    expected_stratum_assignment_hash=self.strata_hash,
                )
                self.assertEqual(result["gate_reason"], "RETURN_VALUE_INVALID")

    def test_insufficient_observations_fail_closed(self):
        result = self._evaluate(self._independent_series(count=63))
        self.assertEqual(result["gate_reason"], "OBSERVATION_COUNT_OUTSIDE_PROTOCOL")

    def test_constant_shifted_series_fail_closed(self):
        series = self._independent_series()
        series["B"] = [1.0] * 96
        result = self._evaluate(series)
        self.assertEqual(result["gate_reason"], "SHIFTED_SERIES_NOT_EVALUABLE")

    def test_low_zero_lag_but_shifted_duplicate_is_blocked(self):
        series = self._shifted_series()
        left = series["A"]
        right = series["B"]
        left_mean = sum(left) / len(left)
        right_mean = sum(right) / len(right)
        covariance = sum(
            (a - left_mean) * (b - right_mean) for a, b in zip(left, right)
        )
        left_ss = sum((value - left_mean) ** 2 for value in left)
        right_ss = sum((value - right_mean) ** 2 for value in right)
        zero_lag = covariance / math.sqrt(left_ss * right_ss)
        result = self._evaluate(series)

        self.assertLess(abs(zero_lag), 0.02)
        self.assertEqual(result["source_state"], "OBSERVED")
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertGreater(result["dependent_test_count"], 0)
        self.assertTrue(
            any(item["lag"] == 1 and item["dependent"] for item in result["lag_results"])
        )

    def test_independent_random_sequences_clear_only_this_candidate_gate(self):
        result = self._evaluate(self._independent_series())
        self.assertEqual(result["gate_decision"], "PASS")
        self.assertEqual(result["dependent_test_count"], 0)
        self.assertFalse(result["authority"]["independence_proven"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_family_contains_every_cross_stratum_pair_times_every_lag(self):
        strata = {"A": "S1", "B": "S2", "C": "S3"}
        left_rng = random.Random(11)
        middle_rng = random.Random(22)
        right_rng = random.Random(33)
        series = {
            "A": [left_rng.uniform(-1, 1) for _ in range(96)],
            "B": [middle_rng.uniform(-1, 1) for _ in range(96)],
            "C": [right_rng.uniform(-1, 1) for _ in range(96)],
        }
        result = self._evaluate(series, strata=strata)
        self.assertEqual(result["cross_stratum_pair_count"], 3)
        self.assertEqual(result["lag_family"], list(LAGS))
        self.assertEqual(result["lag_test_count"], 12)
        self.assertEqual(len(result["lag_results"]), 12)

    def test_resealed_metric_tamper_does_not_verify(self):
        series = self._shifted_series()
        rows = self._rows(series)
        result = self._evaluate(series)
        tampered = copy.deepcopy(result)
        target = next(item for item in tampered["lag_results"] if item["dependent"])
        self.assertNotEqual(target["adjusted_absolute_lower"], "0")
        target["adjusted_absolute_lower"] = "0"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")

        self.assertFalse(
            verify_strategy_correlation_cross_lag_evaluation(
                tampered,
                self.strata,
                rows,
                expected_stratum_assignment_hash=self.strata_hash,
            )
        )

    def test_resealed_numeric_authority_alias_does_not_verify(self):
        series = self._independent_series()
        rows = self._rows(series)
        result = self._evaluate(series)
        result["authority"]["paper_authorized"] = 0
        result.pop("evaluation_hash")
        result = seal_strict_canonical_document(result, "evaluation_hash")

        self.assertFalse(
            verify_strategy_correlation_cross_lag_evaluation(
                result,
                self.strata,
                rows,
                expected_stratum_assignment_hash=self.strata_hash,
            )
        )

    def test_output_never_contains_observation_ids_or_raw_returns(self):
        result = self._evaluate(self._shifted_series(), prefix="PRIVATE-OBSERVATION")
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("PRIVATE-OBSERVATION", encoded)
        self.assertNotIn('"returns"', encoded)

    def test_evaluation_is_deterministic(self):
        series = self._shifted_series()
        self.assertEqual(self._evaluate(series), self._evaluate(copy.deepcopy(series)))


if __name__ == "__main__":
    unittest.main()
