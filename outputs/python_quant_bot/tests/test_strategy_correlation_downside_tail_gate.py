from __future__ import annotations

import copy
import json
import math
import unittest
from decimal import Decimal
from statistics import fmean

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_downside_tail_gate import (
    EVALUATION_SCHEMA,
    REGISTRATION_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_downside_tail_registration,
    evaluate_strategy_correlation_downside_tail_gate,
    verify_strategy_correlation_downside_tail_registration,
)


class StrategyCorrelationDownsideTailGateTests(unittest.TestCase):
    def _registration(self, strata=None):
        return build_strategy_correlation_downside_tail_registration(
            registration_id="downside-tail-candidate-1",
            stratum_by_identity=strata or {"A": "S1", "B": "S2"},
        )

    def _observations(self, tail_by_identity, *, count=60, prefix="obs"):
        identities = sorted(tail_by_identity)
        rows = []
        for index in range(count):
            values = {}
            for offset, identity in enumerate(identities):
                if index in tail_by_identity[identity]:
                    value = -1.0
                else:
                    value = 0.0 if (index + offset) % 2 == 0 else 2.0
                values[identity] = value
            rows.append(
                {
                    "observation_id": f"{prefix}-{index:03d}",
                    "returns": values,
                }
            )
        return rows

    def _evaluate(self, registration, observations, expected_hash=None):
        return evaluate_strategy_correlation_downside_tail_gate(
            registration,
            observations,
            expected_registration_hash=(
                registration["registration_hash"]
                if expected_hash is None
                else expected_hash
            ),
        )

    def test_registration_is_canonical_and_candidate_only(self):
        first = self._registration({"B": "S2", "A": "S1"})
        second = self._registration({"A": "S1", "B": "S2"})

        self.assertEqual(first, second)
        self.assertTrue(verify_strategy_correlation_downside_tail_registration(first))
        self.assertEqual(first["schema_version"], REGISTRATION_SCHEMA)
        self.assertEqual(first["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertTrue(first["authority"]["descriptive_only"])
        self.assertFalse(first["authority"]["formal_preregistration_bound"])
        self.assertFalse(first["authority"]["count_as_independent_allowed"])

    def test_registration_rejects_a_single_stratum(self):
        with self.assertRaises(ValueError):
            self._registration({"A": "S1", "B": "S1"})

    def test_expected_registration_hash_mismatch_fails_closed(self):
        registration = self._registration()
        result = self._evaluate(
            registration,
            self._observations({"A": set(range(12)), "B": set(range(12, 24))}),
            "0" * 64,
        )

        self.assertEqual(result["source_state"], "UNKNOWN")
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(result["gate_reason"], "EXPECTED_REGISTRATION_HASH_MISMATCH")

    def test_resealed_posthoc_protocol_change_is_rejected(self):
        registration = self._registration()
        tampered = copy.deepcopy(registration)
        tampered["protocol"]["minimum_overlap_ratio"]["numerator"] = 0
        tampered.pop("registration_hash")
        tampered = seal_strict_canonical_document(tampered, "registration_hash")

        result = self._evaluate(
            tampered,
            self._observations({"A": set(range(12)), "B": set(range(12, 24))}),
        )
        self.assertFalse(verify_strategy_correlation_downside_tail_registration(tampered))
        self.assertEqual(result["gate_reason"], "REGISTRATION_CONTRACT_INVALID")

    def test_numeric_authority_alias_is_rejected_even_when_resealed(self):
        registration = self._registration()
        tampered = copy.deepcopy(registration)
        tampered["authority"]["paper_authorized"] = 0
        tampered.pop("registration_hash")
        tampered = seal_strict_canonical_document(tampered, "registration_hash")

        result = self._evaluate(
            tampered,
            self._observations({"A": set(range(12)), "B": set(range(12, 24))}),
        )
        self.assertEqual(result["source_state"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "REGISTRATION_CONTRACT_INVALID")

    def test_every_observation_requires_the_exact_identity_set(self):
        registration = self._registration()
        observations = self._observations(
            {"A": set(range(12)), "B": set(range(12, 24))}
        )
        observations[0]["returns"].pop("B")

        result = self._evaluate(registration, observations)
        self.assertEqual(result["gate_reason"], "OBSERVATION_IDENTITY_SET_MISMATCH")

    def test_bool_and_nonfinite_returns_fail_closed(self):
        for invalid in (True, float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid=invalid):
                registration = self._registration()
                observations = self._observations(
                    {"A": set(range(12)), "B": set(range(12, 24))}
                )
                observations[0]["returns"]["A"] = invalid
                result = self._evaluate(registration, observations)
                self.assertEqual(result["gate_reason"], "RETURN_VALUE_INVALID")

    def test_duplicate_observation_ids_fail_closed(self):
        registration = self._registration()
        observations = self._observations(
            {"A": set(range(12)), "B": set(range(12, 24))}
        )
        observations[1]["observation_id"] = observations[0]["observation_id"]

        result = self._evaluate(registration, observations)
        self.assertEqual(result["gate_reason"], "OBSERVATION_ID_INVALID_OR_DUPLICATE")

    def test_insufficient_observations_fail_closed(self):
        registration = self._registration()
        result = self._evaluate(
            registration,
            self._observations(
                {"A": set(range(12)), "B": set(range(12, 24))},
                count=59,
            ),
        )

        self.assertEqual(result["source_state"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "OBSERVATION_COUNT_OUTSIDE_PROTOCOL")

    def test_tail_boundary_tie_fails_closed(self):
        registration = self._registration()
        result = self._evaluate(
            registration,
            self._observations({"A": set(range(13)), "B": set(range(12, 24))}),
        )

        self.assertEqual(result["source_state"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "TAIL_BOUNDARY_TIE_AMBIGUOUS")

    def test_low_pearson_but_shared_crash_tail_is_blocked(self):
        registration = self._registration()
        observations = []
        left = []
        right = []
        for index in range(60):
            if index < 12:
                left_value = right_value = -1.0
            else:
                left_value = 0.0 if index % 2 == 0 else 2.0
                right_value = 2.0 if index % 2 == 0 else 0.0
            left.append(left_value)
            right.append(right_value)
            observations.append(
                {
                    "observation_id": f"obs-{index:03d}",
                    "returns": {"A": left_value, "B": right_value},
                }
            )

        left_mean = fmean(left)
        right_mean = fmean(right)
        covariance = fmean(
            (a - left_mean) * (b - right_mean) for a, b in zip(left, right)
        )
        left_variance = fmean((value - left_mean) ** 2 for value in left)
        right_variance = fmean((value - right_mean) ** 2 for value in right)
        pearson = covariance / math.sqrt(left_variance * right_variance)
        result = self._evaluate(registration, observations)

        self.assertLess(abs(pearson), 0.2)
        self.assertEqual(result["schema_version"], EVALUATION_SCHEMA)
        self.assertEqual(result["source_state"], "OBSERVED")
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(result["coupled_pair_count"], 1)
        self.assertTrue(result["pair_results"][0]["tail_coupled"])

    def test_disjoint_tails_clear_only_this_candidate_gate(self):
        registration = self._registration()
        result = self._evaluate(
            registration,
            self._observations({"A": set(range(12)), "B": set(range(12, 24))}),
        )

        self.assertEqual(result["source_state"], "OBSERVED")
        self.assertEqual(result["gate_decision"], "PASS")
        self.assertEqual(result["coupled_pair_count"], 0)
        self.assertFalse(result["authority"]["independence_proven"])
        self.assertFalse(result["authority"]["count_as_independent_allowed"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_bonferroni_family_includes_every_cross_stratum_pair(self):
        registration = self._registration({"A": "S1", "B": "S2", "C": "S3"})
        result = self._evaluate(
            registration,
            self._observations(
                {
                    "A": set(range(12)),
                    "B": set(range(12)),
                    "C": set(range(12, 24)),
                }
            ),
        )

        self.assertEqual(result["cross_stratum_pair_count"], 3)
        self.assertEqual(result["tested_pair_count"], 3)
        coupled = next(item for item in result["pair_results"] if item["tail_coupled"])
        self.assertGreaterEqual(
            Decimal(coupled["family_adjusted_p_value"]),
            Decimal(coupled["raw_p_value"]),
        )
        self.assertEqual(result["gate_decision"], "BLOCK")

    def test_same_stratum_pairs_are_not_recounted_as_independent(self):
        registration = self._registration({"A": "S1", "B": "S1", "C": "S2"})
        result = self._evaluate(
            registration,
            self._observations(
                {
                    "A": set(range(12)),
                    "B": set(range(12)),
                    "C": set(range(12, 24)),
                }
            ),
        )

        tested = {
            frozenset((item["left_identity"], item["right_identity"]))
            for item in result["pair_results"]
        }
        self.assertNotIn(frozenset(("A", "B")), tested)
        self.assertEqual(result["cross_stratum_pair_count"], 2)
        self.assertEqual(result["gate_decision"], "PASS")

    def test_output_never_contains_observation_ids_or_raw_returns(self):
        registration = self._registration()
        observations = self._observations(
            {"A": set(range(12)), "B": set(range(12, 24))},
            prefix="PRIVATE-OBS",
        )
        observations[0]["returns"]["A"] = -123.456
        result = self._evaluate(registration, observations)
        encoded = json.dumps(result, sort_keys=True)

        self.assertNotIn("PRIVATE-OBS", encoded)
        self.assertNotIn("-123.456", encoded)
        self.assertNotIn('"returns"', encoded)

    def test_observation_and_mapping_order_do_not_change_the_evaluation(self):
        registration = self._registration({"B": "S2", "A": "S1"})
        observations = self._observations(
            {"B": set(range(12, 24)), "A": set(range(12))}
        )
        reversed_rows = list(reversed(observations))

        self.assertEqual(
            self._evaluate(registration, observations),
            self._evaluate(registration, reversed_rows),
        )


if __name__ == "__main__":
    unittest.main()
