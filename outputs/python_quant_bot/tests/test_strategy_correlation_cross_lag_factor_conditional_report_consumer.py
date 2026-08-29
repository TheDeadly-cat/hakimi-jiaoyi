from __future__ import annotations

from copy import deepcopy
import math
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic as evaluate_v1,
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 as evaluate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer import (
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA,
    consume_strategy_correlation_cross_lag_factor_conditional_diagnostic,
    verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt,
)
from tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    StrategyCorrelationCrossLagFactorConditionalDiagnosticTests as F0Cases,
)


class _DictSubclass(dict):
    pass


class StrategyCorrelationCrossLagFactorConditionalReportConsumerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = F0Cases("runTest")
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    @staticmethod
    def _args(context):
        return (
            context["preregistered_strata"],
            context["aligned_observations"],
            context["residualization_registration"],
            context["factor_observations"],
        )

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

    def _v2(self, context):
        return evaluate_v2(*self._args(context), **self._context_kwargs(context))

    def _consume(self, diagnostic, context, *, expected_hash=None):
        if expected_hash is None and type(diagnostic) is dict:
            expected_hash = diagnostic.get("diagnostic_hash")
        return consume_strategy_correlation_cross_lag_factor_conditional_diagnostic(
            diagnostic,
            preregistered_strata=context["preregistered_strata"],
            aligned_observations=context["aligned_observations"],
            residualization_registration=context["residualization_registration"],
            factor_observations=context["factor_observations"],
            expected_stratum_assignment_hash=context[
                "expected_stratum_assignment_hash"
            ],
            expected_registration_hash=context["expected_registration_hash"],
            expected_factor_observations_hash=context[
                "expected_factor_observations_hash"
            ],
            expected_diagnostic_hash=expected_hash,
        )

    def _verify(self, receipt, diagnostic, context, *, expected_hash=None):
        if expected_hash is None and type(diagnostic) is dict:
            expected_hash = diagnostic.get("diagnostic_hash")
        return verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt(
            receipt,
            diagnostic,
            preregistered_strata=context["preregistered_strata"],
            aligned_observations=context["aligned_observations"],
            residualization_registration=context["residualization_registration"],
            factor_observations=context["factor_observations"],
            expected_stratum_assignment_hash=context[
                "expected_stratum_assignment_hash"
            ],
            expected_registration_hash=context["expected_registration_hash"],
            expected_factor_observations_hash=context[
                "expected_factor_observations_hash"
            ],
            expected_diagnostic_hash=expected_hash,
        )

    @staticmethod
    def _reseal_receipt(receipt):
        return seal_strict_canonical_document(receipt, "verification_hash")

    @staticmethod
    def _reseal_source(source):
        return seal_strict_canonical_document(source, "diagnostic_hash")

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
            prefix="pass",
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
            prefix="suppress",
        )

    @staticmethod
    def _all_keys(value):
        if type(value) is dict:
            result = set(value)
            for item in value.values():
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalReportConsumerTests._all_keys(
                        item
                    )
                )
            return result
        if type(value) is list:
            result = set()
            for item in value:
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalReportConsumerTests._all_keys(
                        item
                    )
                )
            return result
        return set()

    def _assert_locked(self, receipt) -> None:
        self.assertEqual(receipt["permission_state"], "LOCKED")
        self.assertIs(receipt["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in receipt["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_common_factor_only_is_observed_without_relaxing_raw_block(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        receipt = self._consume(source, context)
        self.assertEqual(
            receipt["report_state"], "OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE"
        )
        self.assertEqual(receipt["raw_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(receipt["residual_evaluation"]["gate_decision"], "PASS")
        self.assertFalse(receipt["facts"]["raw_block_relaxed"])
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, source, context))

    def test_direct_residual_lag_is_observed_as_residual_dependence(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        source = self._v2(context)
        receipt = self._consume(source, context)
        self.assertEqual(
            receipt["report_state"], "OBSERVED_RESIDUAL_CROSS_LAG_DEPENDENCE"
        )
        self.assertEqual(receipt["raw_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(receipt["residual_evaluation"]["gate_decision"], "BLOCK")
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, source, context))

    def test_pass_pass_is_observed_without_independence_authority(self) -> None:
        context = self._pass_context()
        source = self._v2(context)
        receipt = self._consume(source, context)
        self.assertEqual(
            receipt["report_state"], "OBSERVED_NO_CONDITIONAL_DEPENDENCE"
        )
        self.assertEqual(receipt["raw_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(receipt["residual_evaluation"]["gate_decision"], "PASS")
        self.assertFalse(receipt["authority"]["raw_independence_proven"])
        self.assertFalse(receipt["authority"]["residual_independence_proven"])
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, source, context))

    def test_suppression_is_observed_as_factor_model_instability(self) -> None:
        context = self._suppression_context()
        source = self._v2(context)
        receipt = self._consume(source, context)
        self.assertEqual(
            receipt["report_state"],
            "OBSERVED_SUPPRESSION_OR_MODEL_INSTABILITY",
        )
        self.assertEqual(receipt["raw_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(receipt["residual_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(receipt["gap_state"], "FACTOR_MODEL_INSTABILITY_OBSERVED")
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, source, context))

    def test_missing_source_has_fixed_unknown_closure(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        receipt = self._consume(None, context)
        self.assertEqual(receipt["source_state"], "MISSING")
        self.assertEqual(receipt["report_state"], "UNKNOWN")
        self.assertEqual(receipt["blockers"], ["F0_V2_DIAGNOSTIC_MISSING"])
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, None, context))

    def test_valid_v1_is_unsupported_and_never_auto_migrated(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = evaluate_v1(*self._args(context), **self._context_kwargs(context))
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "UNSUPPORTED")
        self.assertEqual(receipt["report_state"], "UNKNOWN")
        self.assertEqual(receipt["blockers"], ["F0_V1_PRECONSUMER_CONTRACT"])
        self.assertEqual(receipt["source_v1_diagnostic_hash"], source["diagnostic_hash"])
        self.assertTrue(receipt["facts"]["source_diagnostic_verified"])
        self._assert_locked(receipt)
        self.assertTrue(self._verify(receipt, source, context))

    def test_wrong_expected_diagnostic_hash_is_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        receipt = self._consume(source, context, expected_hash="0" * 64)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertEqual(receipt["blockers"], ["F0_V2_DIAGNOSTIC_INVALID"])
        self.assertIsNone(receipt["source_diagnostic_hash"])

    def test_broken_source_hash_is_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        source["diagnostic_hash"] = "0" * 64
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertEqual(receipt["report_state"], "UNKNOWN")

    def test_resealed_top_level_source_tamper_is_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        source["diagnostic_state"] = "NO_CONDITIONAL_DEPENDENCE_DETECTED"
        source = self._reseal_source(source)
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_resealed_nested_raw_tamper_is_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        source = self._v2(context)
        source["raw_evaluation"]["dependent_test_count"] += 1
        source = self._reseal_source(source)
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_resealed_nested_residual_tamper_is_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        source = self._v2(context)
        source["residual_evaluation"]["dependent_test_count"] += 1
        source = self._reseal_source(source)
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_every_source_context_binding_is_required(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        mutations = []
        for key in (
            "expected_stratum_assignment_hash",
            "expected_registration_hash",
            "expected_factor_observations_hash",
        ):
            changed = deepcopy(context)
            changed[key] = "0" * 64
            mutations.append((key, changed))
        changed = deepcopy(context)
        changed["aligned_observations"][0]["returns"]["A"] += 0.125
        mutations.append(("aligned_observations", changed))
        for key, changed_context in mutations:
            receipt = self._consume(source, changed_context)
            with self.subTest(key=key):
                self.assertEqual(receipt["source_state"], "INVALID")

    def test_duplicate_removed_or_reordered_source_blockers_are_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        blocker_variants = (
            source["blockers"] + [source["blockers"][-1]],
            source["blockers"][:-1],
            list(reversed(source["blockers"])),
        )
        for blockers in blocker_variants:
            tampered = deepcopy(source)
            tampered["blockers"] = blockers
            tampered = self._reseal_source(tampered)
            receipt = self._consume(tampered, context)
            with self.subTest(blockers=blockers):
                self.assertEqual(receipt["source_state"], "INVALID")

    def test_extra_untrusted_source_field_is_invalid_and_not_reflected(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        source["attacker_text"] = "READY PROFIT LIVE"
        source = self._reseal_source(source)
        receipt = self._consume(source, context)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertNotIn("attacker_text", receipt)
        self.assertNotIn("READY PROFIT LIVE", str(receipt))

    def test_subclass_pseudo_boolean_and_nonfinite_source_are_invalid(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        variants = [_DictSubclass(source)]
        pseudo = deepcopy(source)
        pseudo["facts"]["raw_block_relaxed"] = 0
        variants.append(pseudo)
        nonfinite = deepcopy(source)
        nonfinite["raw_evaluation"]["dependent_test_count"] = math.nan
        variants.append(nonfinite)
        for variant in variants:
            receipt = self._consume(variant, context)
            with self.subTest(kind=type(variant).__name__):
                self.assertEqual(receipt["source_state"], "INVALID")

    def test_authority_alias_in_source_or_receipt_is_rejected(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        source_alias = deepcopy(source)
        source_alias["authority"]["ready"] = True
        source_alias = self._reseal_source(source_alias)
        self.assertEqual(self._consume(source_alias, context)["source_state"], "INVALID")
        receipt = self._consume(source, context)
        receipt["authority"]["ready"] = True
        receipt = self._reseal_receipt(receipt)
        self.assertFalse(self._verify(receipt, source, context))

    def test_observed_output_is_aggregate_only(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        receipt = self._consume(source, context)
        forbidden = {
            "aligned_observations",
            "beta",
            "betas",
            "factor_id",
            "factor_values",
            "observation_id",
            "pair_lag_results",
            "raw_rows",
            "residual_rows",
            "returns",
        }
        self.assertFalse(self._all_keys(receipt) & forbidden)

    def test_resealed_receipt_state_count_hash_and_authority_tamper_reject(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        source = self._v2(context)
        receipt = self._consume(source, context)
        variants = []
        changed = deepcopy(receipt)
        changed["report_state"] = "OBSERVED_NO_CONDITIONAL_DEPENDENCE"
        variants.append(changed)
        changed = deepcopy(receipt)
        changed["raw_evaluation"]["dependent_test_count"] += 1
        variants.append(changed)
        changed = deepcopy(receipt)
        changed["source_diagnostic_hash"] = "0" * 64
        variants.append(changed)
        changed = deepcopy(receipt)
        changed["authority"]["current_admission_allowed"] = True
        variants.append(changed)
        for changed in variants:
            tampered = self._reseal_receipt(changed)
            with self.subTest(state=tampered["report_state"]):
                self.assertFalse(self._verify(tampered, source, context))

    def test_evaluation_is_deterministic_and_uses_no_external_state(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        first = self._consume(source, context)
        second = self._consume(source, context)
        self.assertEqual(first, second)

    def test_schema_fingerprint_and_source_binding_are_exact(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = self._v2(context)
        receipt = self._consume(source, context)
        self.assertEqual(receipt["schema_version"], VERIFICATION_SCHEMA)
        self.assertEqual(receipt["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(receipt["source_diagnostic_hash"], source["diagnostic_hash"])
        self.assertEqual(
            receipt["source_v1_diagnostic_hash"],
            source["source_v1_diagnostic_hash"],
        )
        self.assertTrue(receipt["facts"]["source_diagnostic_verified"])
        self.assertTrue(self._verify(receipt, source, context))


if __name__ == "__main__":
    unittest.main()
