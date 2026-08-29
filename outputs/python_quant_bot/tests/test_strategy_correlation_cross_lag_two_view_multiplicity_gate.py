from __future__ import annotations

from copy import deepcopy
import math
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    _factor_values,
    _registration_values,
    _residual_rows,
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic as evaluate_v1,
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 as evaluate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_gate import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    _adjusted_absolute_lower,
    _decimal_text,
    _gate_decision,
    evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate,
    verify_strategy_correlation_cross_lag_two_view_multiplicity_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_registration import (
    build_strategy_correlation_cross_lag_two_view_multiplicity_registration,
)
from tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    StrategyCorrelationCrossLagFactorConditionalDiagnosticTests as F0Cases,
)


class _ListSubclass(list):
    pass


class _DictSubclass(dict):
    pass


class StrategyCorrelationCrossLagTwoViewMultiplicityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = F0Cases("runTest")
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    @staticmethod
    def _context_kwargs(context):
        return {
            key: context[key]
            for key in (
                "expected_stratum_assignment_hash",
                "expected_registration_hash",
                "expected_factor_observations_hash",
            )
        }

    def _f0(self, context):
        return evaluate_v2(
            context["preregistered_strata"],
            context["aligned_observations"],
            context["residualization_registration"],
            context["factor_observations"],
            **self._context_kwargs(context),
        )

    def _family(self, context):
        return build_strategy_correlation_cross_lag_two_view_multiplicity_registration(
            context["preregistered_strata"],
            expected_stratum_assignment_hash=context[
                "expected_stratum_assignment_hash"
            ],
        )

    def _residual(self, context):
        identities, betas = _registration_values(
            context["residualization_registration"],
            expected_registration_hash=context["expected_registration_hash"],
        )
        factor_rows, factor_values = _factor_values(
            context["factor_observations"],
            context["residualization_registration"],
            expected_factor_observations_hash=context[
                "expected_factor_observations_hash"
            ],
        )
        return _residual_rows(
            context["aligned_observations"],
            factor_rows,
            factor_values,
            identities,
            betas,
        )

    def _evaluate(self, context, *, family=None, f0=None, residual=None, overrides=None):
        family = self._family(context) if family is None else family
        f0 = self._f0(context) if f0 is None else f0
        residual = self._residual(context) if residual is None else residual
        expected = {
            "expected_stratum_assignment_hash": context[
                "expected_stratum_assignment_hash"
            ],
            "expected_residualization_registration_hash": context[
                "expected_registration_hash"
            ],
            "expected_factor_observations_hash": context[
                "expected_factor_observations_hash"
            ],
            "expected_family_registration_hash": family.get("registration_hash")
            if type(family) is dict
            else None,
            "expected_f0_diagnostic_hash": f0.get("diagnostic_hash")
            if type(f0) is dict
            else None,
            "expected_residual_input_hash": f0.get("residual_input_hash")
            if type(f0) is dict
            else None,
        }
        expected.update(overrides or {})
        return evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate(
            family,
            f0,
            context["preregistered_strata"],
            context["aligned_observations"],
            residual,
            context["residualization_registration"],
            context["factor_observations"],
            **expected,
        )

    def _verify(
        self,
        document,
        context,
        *,
        family=None,
        f0=None,
        residual=None,
        expected_hash=None,
        overrides=None,
    ):
        family = self._family(context) if family is None else family
        f0 = self._f0(context) if f0 is None else f0
        residual = self._residual(context) if residual is None else residual
        expected = {
            "expected_stratum_assignment_hash": context[
                "expected_stratum_assignment_hash"
            ],
            "expected_residualization_registration_hash": context[
                "expected_registration_hash"
            ],
            "expected_factor_observations_hash": context[
                "expected_factor_observations_hash"
            ],
            "expected_family_registration_hash": family.get("registration_hash")
            if type(family) is dict
            else None,
            "expected_f0_diagnostic_hash": f0.get("diagnostic_hash")
            if type(f0) is dict
            else None,
            "expected_residual_input_hash": f0.get("residual_input_hash")
            if type(f0) is dict
            else None,
            "expected_evaluation_hash": document.get("evaluation_hash")
            if expected_hash is None and type(document) is dict
            else expected_hash,
        }
        expected.update(overrides or {})
        return verify_strategy_correlation_cross_lag_two_view_multiplicity_gate(
            document,
            family,
            f0,
            context["preregistered_strata"],
            context["aligned_observations"],
            residual,
            context["residualization_registration"],
            context["factor_observations"],
            **expected,
        )

    @staticmethod
    def _reseal(document):
        return seal_strict_canonical_document(document, "evaluation_hash")

    def _pass_context(self):
        series = self.fixture.fixture._independent_series(count=1000)
        state = 0x13579BDF
        factor = []
        for _ in range(1000):
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            factor.append((state / 4294967296.0) - 0.5)
        return self.fixture._context(
            series,
            factor,
            betas={"A": "0", "B": "0"},
            prefix="global-pass",
        )

    def _suppression_context(self):
        series = self.fixture.fixture._independent_series(count=1000)
        x = series["A"]
        y = series["B"]
        factor = [
            y[index] - (0.96 * x[index - 1] if index else 0.0)
            for index in range(1000)
        ]
        return self.fixture._context(
            series,
            factor,
            betas={"A": "0", "B": "1"},
            prefix="global-suppress",
        )

    @staticmethod
    def _all_keys(value):
        if type(value) is dict:
            result = set(value)
            for item in value.values():
                result.update(
                    StrategyCorrelationCrossLagTwoViewMultiplicityGateTests._all_keys(
                        item
                    )
                )
            return result
        if type(value) is list:
            result = set()
            for item in value:
                result.update(
                    StrategyCorrelationCrossLagTwoViewMultiplicityGateTests._all_keys(
                        item
                    )
                )
            return result
        return set()

    def test_critical_point_changes_under_registered_two_view_family(self) -> None:
        per_view = _adjusted_absolute_lower(0.9185, 20.0, 4)
        global_family = _adjusted_absolute_lower(0.9185, 20.0, 8)
        self.assertEqual(_decimal_text(per_view), "0.750266889215")
        self.assertEqual(_decimal_text(global_family), "0.724078648693")
        self.assertGreaterEqual(per_view, 0.75)
        self.assertLess(global_family, 0.75)

    def test_common_factor_case_replays_exact_dual_c0_and_preserves_raw_block(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["gate_decision"], "BLOCK")
        self.assertTrue(document["facts"]["source_block_preserved"])
        self.assertEqual(document["view_summaries"][0]["source_gate_decision"], "BLOCK")
        self.assertEqual(document["view_summaries"][1]["source_gate_decision"], "PASS")
        self.assertTrue(self._verify(document, context))

    def test_direct_residual_case_preserves_both_source_blocks(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        document = self._evaluate(context)
        self.assertEqual(document["gate_decision"], "BLOCK")
        self.assertEqual(
            [item["source_gate_decision"] for item in document["view_summaries"]],
            ["BLOCK", "BLOCK"],
        )
        self.assertIn("RAW_C0_BLOCK_PRESERVED", document["blockers"])
        self.assertIn("RESIDUAL_C0_BLOCK_PRESERVED", document["blockers"])
        self.assertTrue(self._verify(document, context))

    def test_pass_pass_case_is_candidate_global_pass_without_independence(self) -> None:
        context = self._pass_context()
        document = self._evaluate(context)
        self.assertEqual(document["global_recalibrated_decision"], "PASS")
        self.assertEqual(document["gate_decision"], "PASS")
        self.assertEqual(document["global_dependent_test_count"], 0)
        self.assertFalse(document["authority"]["global_independence_proven"])
        self.assertFalse(document["authority"]["raw_independence_proven"])
        self.assertFalse(document["authority"]["residual_independence_proven"])
        self.assertTrue(self._verify(document, context))

    def test_suppression_case_preserves_residual_source_block(self) -> None:
        context = self._suppression_context()
        document = self._evaluate(context)
        self.assertEqual(document["gate_decision"], "BLOCK")
        self.assertEqual(
            [item["source_gate_decision"] for item in document["view_summaries"]],
            ["PASS", "BLOCK"],
        )
        self.assertIn("RESIDUAL_C0_BLOCK_PRESERVED", document["blockers"])
        self.assertTrue(self._verify(document, context))

    def test_formula_reproduces_every_source_c0_per_view_lower(self):
        from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
            _adjusted_absolute_lower as c0_adjusted_absolute_lower,
            _decimal_text as c0_decimal_text,
            _effective_sample_size as c0_effective_sample_size,
            _pearson as c0_pearson,
            _shifted_pair as c0_shifted_pair,
            evaluate_strategy_correlation_cross_lag_gate as evaluate_c0,
        )

        for context in (self._pass_context(), self._suppression_context()):
            family = self._family(context)
            residual = self._residual(context)
            for observations in (context["aligned_observations"], residual):
                evaluation = evaluate_c0(
                    context["preregistered_strata"],
                    observations,
                    expected_stratum_assignment_hash=context[
                        "expected_stratum_assignment_hash"
                    ],
                )
                self.assertEqual(evaluation["source_state"], "OBSERVED")
                for result in evaluation["lag_results"]:
                    left = [
                        row["returns"][result["left_identity"]]
                        for row in observations
                    ]
                    right = [
                        row["returns"][result["right_identity"]]
                        for row in observations
                    ]
                    shifted_left, shifted_right = c0_shifted_pair(
                        left, right, result["lag"]
                    )
                    correlation = c0_pearson(shifted_left, shifted_right)
                    effective_sample_size = c0_effective_sample_size(
                        shifted_left, shifted_right
                    )
                    self.assertIsNotNone(correlation)
                    self.assertIsNotNone(effective_sample_size)
                    self.assertEqual(
                        c0_decimal_text(correlation), result["correlation"]
                    )
                    self.assertEqual(
                        c0_decimal_text(effective_sample_size),
                        result["effective_sample_size"],
                    )
                    per_view_lower = c0_adjusted_absolute_lower(
                        correlation,
                        effective_sample_size,
                        family["per_view_test_count"],
                    )
                    global_lower = c0_adjusted_absolute_lower(
                        correlation,
                        effective_sample_size,
                        family["global_test_count"],
                    )
                    self.assertEqual(
                        c0_decimal_text(per_view_lower),
                        result["adjusted_absolute_lower"],
                    )
                    self.assertLessEqual(global_lower, per_view_lower)

    def test_residual_hash_mismatch_has_fixed_unknown_closure(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(
            context,
            overrides={"expected_residual_input_hash": "0" * 64},
        )
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertTrue(
            self._verify(
                document,
                context,
                overrides={"expected_residual_input_hash": "0" * 64},
            )
        )

    def test_removed_duplicate_reordered_and_extra_residual_rows_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        residual = self._residual(context)
        variants = (
            residual[:-1],
            residual + [deepcopy(residual[-1])],
            list(reversed(residual)),
            residual + [{"observation_id": "extra", "sequence": 1000, "returns": {"A": 0.0, "B": 0.0}}],
        )
        for rows in variants:
            document = self._evaluate(context, residual=rows)
            with self.subTest(length=len(rows)):
                self.assertEqual(document["source_state"], "UNKNOWN")

    def test_context_and_expected_hash_mismatch_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        for key in (
            "expected_stratum_assignment_hash",
            "expected_residualization_registration_hash",
            "expected_factor_observations_hash",
            "expected_family_registration_hash",
            "expected_f0_diagnostic_hash",
        ):
            document = self._evaluate(context, overrides={key: "0" * 64})
            with self.subTest(key=key):
                self.assertEqual(document["source_state"], "UNKNOWN")

    def test_f0_v1_and_resealed_f0_v2_tamper_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        v1 = evaluate_v1(
            context["preregistered_strata"],
            context["aligned_observations"],
            context["residualization_registration"],
            context["factor_observations"],
            **self._context_kwargs(context),
        )
        self.assertEqual(self._evaluate(context, f0=v1)["source_state"], "UNKNOWN")
        v2 = self._f0(context)
        v2["raw_evaluation"]["dependent_test_count"] += 1
        v2 = seal_strict_canonical_document(v2, "diagnostic_hash")
        self.assertEqual(self._evaluate(context, f0=v2)["source_state"], "UNKNOWN")

    def test_resealed_family_policy_count_and_order_tamper_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        family = self._family(context)
        variants = []
        for key, value in (
            ("global_test_count", family["global_test_count"] + 1),
            ("family_alpha", "0.10"),
            ("correction_method", "NONE"),
            ("views", list(reversed(family["views"]))),
            ("lags", [-1, 1]),
        ):
            changed = deepcopy(family)
            changed[key] = value
            variants.append(seal_strict_canonical_document(changed, "registration_hash"))
        for changed in variants:
            with self.subTest(hash=changed["registration_hash"]):
                self.assertEqual(
                    self._evaluate(context, family=changed)["source_state"],
                    "UNKNOWN",
                )

    def test_monotonic_decision_never_relaxes_source_block(self) -> None:
        self.assertEqual(
            _gate_decision("BLOCK", "PASS", 0),
            (
                "BLOCK",
                "SOURCE_C0_BLOCK_PRESERVED_AFTER_GLOBAL_RECALIBRATION",
                True,
            ),
        )
        self.assertEqual(_gate_decision("PASS", "BLOCK", 0)[0], "BLOCK")
        self.assertEqual(_gate_decision("PASS", "PASS", 0)[0], "PASS")

    def test_gate_contract_identity_family_and_provenance_are_exact(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        family = self._family(context)
        f0 = self._f0(context)
        document = self._evaluate(context, family=family, f0=f0)
        self.assertEqual(document["schema_version"], GATE_SCHEMA)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["family_registration_hash"], family["registration_hash"])
        self.assertEqual(document["f0_diagnostic_hash"], f0["diagnostic_hash"])
        self.assertEqual(document["global_test_count"], 8)
        self.assertEqual(document["per_view_test_count"], 4)

    def test_resealed_gate_metric_blocker_hash_and_authority_tamper_reject(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        variants = []
        changed = deepcopy(document)
        changed["global_dependent_test_count"] += 1
        variants.append(changed)
        changed = deepcopy(document)
        changed["blockers"] = list(reversed(changed["blockers"]))
        variants.append(changed)
        changed = deepcopy(document)
        changed["private_recalculated_test_ledger_hash"] = "0" * 64
        variants.append(changed)
        changed = deepcopy(document)
        changed["authority"]["current_admission_allowed"] = True
        variants.append(changed)
        for changed in variants:
            tampered = self._reseal(changed)
            self.assertFalse(self._verify(tampered, context))

    def test_output_is_aggregate_only_and_authority_locked(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        forbidden = {
            "aligned_observations",
            "beta",
            "betas",
            "factor_id",
            "factor_values",
            "lag_results",
            "left_identity",
            "observation_id",
            "pair_lag_results",
            "raw_rows",
            "residual_rows",
            "returns",
            "right_identity",
        }
        self.assertFalse(self._all_keys(document) & forbidden)
        self.assertIs(document["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_non_mapping_subclass_and_nonfinite_documents_never_verify(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertFalse(self._verify(None, context, expected_hash=document["evaluation_hash"]))
        self.assertFalse(
            self._verify(
                _DictSubclass(document),
                context,
                expected_hash=document["evaluation_hash"],
            )
        )
        nonfinite = deepcopy(document)
        nonfinite["global_dependent_test_count"] = math.nan
        self.assertFalse(
            self._verify(
                nonfinite,
                context,
                expected_hash=document["evaluation_hash"],
            )
        )
        residual = _ListSubclass(self._residual(context))
        self.assertEqual(
            self._evaluate(context, residual=residual)["source_state"],
            "UNKNOWN",
        )

    def test_unknown_gate_is_deterministic_and_exactly_replayable(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        first = self._evaluate(
            context,
            overrides={"expected_family_registration_hash": "0" * 64},
        )
        second = self._evaluate(
            context,
            overrides={"expected_family_registration_hash": "0" * 64},
        )
        self.assertEqual(first, second)
        self.assertTrue(
            self._verify(
                first,
                context,
                overrides={"expected_family_registration_hash": "0" * 64},
            )
        )

    def test_gate_is_deterministic_and_uses_no_external_state(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        first = self._evaluate(context)
        second = self._evaluate(context)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
