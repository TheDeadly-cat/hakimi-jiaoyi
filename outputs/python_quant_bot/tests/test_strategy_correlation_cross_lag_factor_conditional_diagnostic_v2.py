from __future__ import annotations

from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 as v2_module
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic as evaluate_v1,
    seal_strict_canonical_document,
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic as verify_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    DIAGNOSTIC_SCHEMA,
    REPORT_CONSUMER_SCHEMA,
    STABLE_REPORT_BLOCKER,
    STATIC_FINGERPRINT,
    V1_DYNAMIC_BLOCKER,
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2,
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2,
)
from tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    StrategyCorrelationCrossLagFactorConditionalDiagnosticTests as F0Cases,
)


class _DictSubclass(dict):
    pass


class StrategyCorrelationCrossLagFactorConditionalDiagnosticV2Tests(unittest.TestCase):
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
    def _kwargs(context):
        return {
            key: context[key]
            for key in (
                "expected_stratum_assignment_hash",
                "expected_registration_hash",
                "expected_factor_observations_hash",
            )
        }

    def _evaluate(self, context):
        return evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
            *self._args(context),
            **self._kwargs(context),
        )

    def _verify(self, document, context, *, expected_hash=None):
        return verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
            document,
            *self._args(context),
            **self._kwargs(context),
            expected_diagnostic_hash=(
                document.get("diagnostic_hash")
                if expected_hash is None and type(document) is dict
                else expected_hash
            ),
        )

    @staticmethod
    def _reseal(document):
        return seal_strict_canonical_document(document, "diagnostic_hash")

    @staticmethod
    def _all_keys(value):
        if type(value) is dict:
            result = set(value)
            for item in value.values():
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalDiagnosticV2Tests._all_keys(item)
                )
            return result
        if type(value) is list:
            result = set()
            for item in value:
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalDiagnosticV2Tests._all_keys(item)
                )
            return result
        return set()

    def test_observed_contract_is_versioned_exact_and_unmounted(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertTrue(self._verify(document, context))
        self.assertEqual(document["schema_version"], DIAGNOSTIC_SCHEMA)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            document["report_contract"],
            {
                "activation_state": "UNMOUNTED",
                "schema_version": REPORT_CONSUMER_SCHEMA,
            },
        )
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["diagnostic_state"], "COMMON_FACTOR_MEDIATED_CANDIDATE")

    def test_v1_is_unchanged_and_exactly_bound_as_source(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        before = evaluate_v1(*self._args(context), **self._kwargs(context))
        before_copy = deepcopy(before)
        document = self._evaluate(context)
        after = evaluate_v1(*self._args(context), **self._kwargs(context))
        self.assertEqual(before, before_copy)
        self.assertEqual(after, before)
        self.assertTrue(verify_v1(before, *self._args(context), **self._kwargs(context)))
        self.assertEqual(document["source_v1_diagnostic_hash"], before["diagnostic_hash"])
        self.assertIn(V1_DYNAMIC_BLOCKER, before["blockers"])
        self.assertNotIn(STABLE_REPORT_BLOCKER, before["blockers"])

    def test_dynamic_blocker_is_replaced_once_without_reordering_other_blockers(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        source = evaluate_v1(*self._args(context), **self._kwargs(context))
        document = self._evaluate(context)
        expected = [
            STABLE_REPORT_BLOCKER if item == V1_DYNAMIC_BLOCKER else item
            for item in source["blockers"]
        ]
        self.assertEqual(document["blockers"], expected)
        self.assertEqual(document["blockers"].count(STABLE_REPORT_BLOCKER), 1)
        self.assertNotIn(V1_DYNAMIC_BLOCKER, document["blockers"])

    def test_direct_residual_dependence_is_preserved(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        document = self._evaluate(context)
        self.assertEqual(document["raw_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(document["residual_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(
            document["diagnostic_state"],
            "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
        )
        self.assertFalse(document["facts"]["raw_block_relaxed"])
        self.assertTrue(self._verify(document, context))

    def test_invalid_v1_context_has_fixed_exact_unknown_closure(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        context["expected_registration_hash"] = "0" * 64
        first = self._evaluate(context)
        second = self._evaluate(context)
        self.assertEqual(first, second)
        self.assertEqual(first["source_state"], "UNKNOWN")
        self.assertEqual(first["diagnostic_state"], "UNKNOWN")
        self.assertEqual(
            first["blockers"],
            ["F0_V1_SOURCE_INVALID", STABLE_REPORT_BLOCKER],
        )
        self.assertIsNone(first["source_v1_diagnostic_hash"])
        self.assertTrue(self._verify(first, context))

    def test_unknown_from_invalid_context_does_not_verify_against_valid_context(self) -> None:
        valid = self.fixture._common_factor_case(direct_residual=False)
        invalid = deepcopy(valid)
        invalid["expected_factor_observations_hash"] = "0" * 64
        document = self._evaluate(invalid)
        self.assertFalse(self._verify(document, valid))

    def test_wrong_expected_v2_hash_rejects(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertFalse(self._verify(document, context, expected_hash="0" * 64))
        self.assertFalse(self._verify(document, context, expected_hash=True))

    def test_v1_document_is_not_a_v2_document(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = evaluate_v1(*self._args(context), **self._kwargs(context))
        self.assertFalse(
            self._verify(source, context, expected_hash=source["diagnostic_hash"])
        )

    def test_duplicate_or_missing_dynamic_source_marker_fails_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        source = evaluate_v1(*self._args(context), **self._kwargs(context))
        for blockers in (
            source["blockers"] + [V1_DYNAMIC_BLOCKER],
            [item for item in source["blockers"] if item != V1_DYNAMIC_BLOCKER],
        ):
            tampered = deepcopy(source)
            tampered["blockers"] = blockers
            tampered = self._reseal(tampered)
            with self.subTest(blockers=blockers), patch.object(
                v2_module, "_evaluate_v1", return_value=tampered
            ), patch.object(v2_module, "_verify_v1", return_value=True):
                document = self._evaluate(context)
                self.assertEqual(document["source_state"], "UNKNOWN")

    def test_resealed_top_level_tamper_rejects(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        tampered = deepcopy(document)
        tampered["diagnostic_state"] = "NO_CONDITIONAL_DEPENDENCE_DETECTED"
        tampered = self._reseal(tampered)
        self.assertFalse(self._verify(tampered, context))

    def test_resealed_raw_and_residual_tamper_reject(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        document = self._evaluate(context)
        for branch in ("raw_evaluation", "residual_evaluation"):
            tampered = deepcopy(document)
            tampered[branch]["dependent_test_count"] += 1
            tampered = self._reseal(tampered)
            with self.subTest(branch=branch):
                self.assertFalse(self._verify(tampered, context))

    def test_resealed_report_contract_and_authority_alias_reject(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        mutations = []
        changed_contract = deepcopy(document)
        changed_contract["report_contract"]["activation_state"] = "ACTIVE"
        mutations.append(changed_contract)
        authority_alias = deepcopy(document)
        authority_alias["authority"]["ready"] = True
        mutations.append(authority_alias)
        for mutation in mutations:
            tampered = self._reseal(mutation)
            with self.subTest(keys=sorted(tampered)):
                self.assertFalse(self._verify(tampered, context))

    def test_every_source_context_binding_is_required(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        mutations = []
        for key in (
            "expected_stratum_assignment_hash",
            "expected_registration_hash",
            "expected_factor_observations_hash",
        ):
            changed = deepcopy(context)
            changed[key] = "0" * 64
            mutations.append((key, changed))
        changed_rows = deepcopy(context)
        changed_rows["aligned_observations"][0]["returns"]["A"] += 0.125
        mutations.append(("aligned_observations", changed_rows))
        for key, changed in mutations:
            with self.subTest(key=key):
                self.assertFalse(self._verify(document, changed))

    def test_output_is_aggregate_only(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        forbidden = {
            "aligned_observations",
            "beta",
            "betas",
            "factor_values",
            "observation_id",
            "pair_lag_results",
            "raw_rows",
            "residual_rows",
            "returns",
        }
        self.assertFalse(self._all_keys(document) & forbidden)

    def test_all_authority_remains_locked(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertIs(document["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )
        self.assertFalse(document["facts"]["calibration_receipt_attested"])
        self.assertFalse(
            document["facts"]["global_two_view_multiplicity_registered"]
        )

    def test_non_mapping_subclass_and_nonfinite_document_never_verify(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        document = self._evaluate(context)
        self.assertFalse(self._verify(None, context, expected_hash=document["diagnostic_hash"]))
        self.assertFalse(
            self._verify(
                _DictSubclass(document),
                context,
                expected_hash=document["diagnostic_hash"],
            )
        )
        nonfinite = deepcopy(document)
        nonfinite["raw_evaluation"]["dependent_test_count"] = math.nan
        self.assertFalse(
            self._verify(
                nonfinite,
                context,
                expected_hash=document["diagnostic_hash"],
            )
        )

    def test_evaluation_is_deterministic_and_uses_no_external_state(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        first = self._evaluate(context)
        second = self._evaluate(context)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
