from __future__ import annotations

import copy
import random
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_direction_contract import (
    CONTRACT_SCHEMA,
    INDEX_RELATION,
    LAG_DIRECTION_CONVENTION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_direction_contract,
    verify_strategy_correlation_cross_lag_direction_contract,
)
from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests.test_strategy_correlation_cross_lag_gate import (
    StrategyCorrelationCrossLagGateTests,
)


class StrategyCorrelationCrossLagDirectionContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = StrategyCorrelationCrossLagGateTests()
        self.fixture.setUp()
        self.strata = {"A": "S1", "B": "S2"}
        self.strata_hash = strict_canonical_hash(self.strata)

    def _evaluate(self, left, right):
        return evaluate_strategy_correlation_cross_lag_gate(
            self.strata,
            self.fixture._rows({"A": left, "B": right}),
            expected_stratum_assignment_hash=self.strata_hash,
        )

    def _assert_locked(self, contract):
        self.assertTrue(contract["authority"]["descriptive_only"])
        for key, value in contract["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_contract_is_strictly_sealed_and_candidate_only(self):
        contract = build_strategy_correlation_cross_lag_direction_contract()
        self.assertEqual(contract["schema_version"], CONTRACT_SCHEMA)
        self.assertEqual(contract["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(contract["index_relation"], INDEX_RELATION)
        self.assertEqual(contract["lag_direction_convention"], LAG_DIRECTION_CONVENTION)
        self.assertEqual(contract["lag_family"], [-2, -1, 1, 2])
        self.assertFalse(contract["zero_lag_included"])
        self.assertTrue(verify_strategy_correlation_cross_lag_direction_contract(contract))
        self._assert_locked(contract)

    def test_nonperiodic_right_follows_left_is_uniquely_positive_lag(self):
        rng = random.Random(20260821)
        left = [rng.uniform(-1.0, 1.0) for _ in range(128)]
        right = [rng.uniform(-1.0, 1.0)] + left[:-1]
        evaluation = self._evaluate(left, right)
        dependent_lags = [item["lag"] for item in evaluation["lag_results"] if item["dependent"]]
        self.assertEqual(dependent_lags, [1])

    def test_nonperiodic_right_leads_left_is_uniquely_negative_lag(self):
        rng = random.Random(20260822)
        right = [rng.uniform(-1.0, 1.0) for _ in range(128)]
        left = [rng.uniform(-1.0, 1.0)] + right[:-1]
        evaluation = self._evaluate(left, right)
        dependent_lags = [item["lag"] for item in evaluation["lag_results"] if item["dependent"]]
        self.assertEqual(dependent_lags, [-1])

    def test_direction_or_source_drift_fails_exact_verification_after_reseal(self):
        contract = build_strategy_correlation_cross_lag_direction_contract()
        for field, value in (
            ("lag_direction_convention", "POSITIVE_LAG_MEANS_LEFT_FOLLOWS_RIGHT"),
            ("index_relation", "LEFT_INDEX_EQUALS_RIGHT_INDEX_PLUS_LAG"),
            ("source_gate_static_fingerprint", "drifted-gate"),
        ):
            with self.subTest(field=field):
                tampered = copy.deepcopy(contract)
                tampered[field] = value
                tampered.pop("contract_hash")
                tampered = seal_strict_canonical_document(tampered, "contract_hash")
                self.assertFalse(verify_strategy_correlation_cross_lag_direction_contract(tampered))

    def test_lag_family_drift_fails_exact_verification(self):
        contract = build_strategy_correlation_cross_lag_direction_contract()
        for family in ([-2, -1, 1], [-2, -1, 1, 2, 3], [2, 1, -1, -2]):
            with self.subTest(family=family):
                tampered = copy.deepcopy(contract)
                tampered["lag_family"] = family
                tampered.pop("contract_hash")
                tampered = seal_strict_canonical_document(tampered, "contract_hash")
                self.assertFalse(verify_strategy_correlation_cross_lag_direction_contract(tampered))

    def test_authority_alias_and_escalation_fail_verification(self):
        contract = build_strategy_correlation_cross_lag_direction_contract()
        for value in (0, "", "false", True):
            with self.subTest(value=value):
                tampered = copy.deepcopy(contract)
                tampered["authority"]["paper_authorized"] = value
                tampered.pop("contract_hash")
                tampered = seal_strict_canonical_document(tampered, "contract_hash")
                self.assertFalse(verify_strategy_correlation_cross_lag_direction_contract(tampered))

    def test_extra_untrusted_field_fails_exact_verification(self):
        contract = build_strategy_correlation_cross_lag_direction_contract()
        contract["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        contract.pop("contract_hash")
        contract = seal_strict_canonical_document(contract, "contract_hash")
        self.assertFalse(verify_strategy_correlation_cross_lag_direction_contract(contract))

    def test_non_mapping_never_verifies(self):
        self.assertFalse(verify_strategy_correlation_cross_lag_direction_contract([]))


if __name__ == "__main__":
    unittest.main()
