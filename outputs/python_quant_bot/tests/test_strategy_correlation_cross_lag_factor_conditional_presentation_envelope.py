from __future__ import annotations

from copy import deepcopy
import math
import unittest

from exchange_terminal.application.strategy_correlation_cross_lag_factor_conditional_presentation_envelope import (
    ENVELOPE_SCHEMA,
    PRESENTATION_STATUS,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope,
    verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic as evaluate_v1,
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 as evaluate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_conditional_diagnostic,
)
from tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    StrategyCorrelationCrossLagFactorConditionalDiagnosticTests as F0Cases,
)


class _DictSubclass(dict):
    pass


class StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeTests(
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

    def _receipt(self, diagnostic, context, *, expected_diagnostic_hash=None):
        if expected_diagnostic_hash is None and type(diagnostic) is dict:
            expected_diagnostic_hash = diagnostic.get("diagnostic_hash")
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
            expected_diagnostic_hash=expected_diagnostic_hash,
        )

    def _build(
        self,
        receipt,
        diagnostic,
        context,
        *,
        expected_diagnostic_hash=None,
        expected_receipt_hash=None,
    ):
        if expected_diagnostic_hash is None and type(diagnostic) is dict:
            expected_diagnostic_hash = diagnostic.get("diagnostic_hash")
        if expected_receipt_hash is None and type(receipt) is dict:
            expected_receipt_hash = receipt.get("verification_hash")
        return build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope(
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
            expected_diagnostic_hash=expected_diagnostic_hash,
            expected_receipt_hash=expected_receipt_hash,
        )

    def _verify(
        self,
        envelope,
        receipt,
        diagnostic,
        context,
        *,
        expected_diagnostic_hash=None,
        expected_receipt_hash=None,
    ):
        if expected_diagnostic_hash is None and type(diagnostic) is dict:
            expected_diagnostic_hash = diagnostic.get("diagnostic_hash")
        if expected_receipt_hash is None and type(receipt) is dict:
            expected_receipt_hash = receipt.get("verification_hash")
        return verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope(
            envelope,
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
            expected_diagnostic_hash=expected_diagnostic_hash,
            expected_receipt_hash=expected_receipt_hash,
        )

    @staticmethod
    def _reseal(envelope):
        return seal_strict_canonical_document(envelope, "envelope_hash")

    @staticmethod
    def _all_keys(value):
        if type(value) is dict:
            result = set(value)
            for item in value.values():
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeTests._all_keys(
                        item
                    )
                )
            return result
        if type(value) is list:
            result = set()
            for item in value:
                result.update(
                    StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeTests._all_keys(
                        item
                    )
                )
            return result
        return set()

    def _assert_locked(self, envelope) -> None:
        self.assertIs(envelope["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in envelope["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_observed_receipt_is_carried_exactly_in_verified_envelope(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "OBSERVED")
        self.assertEqual(envelope["report"], receipt)
        self.assertEqual(envelope["source_receipt_hash"], receipt["verification_hash"])
        self.assertTrue(self._verify(envelope, receipt, diagnostic, context))
        self._assert_locked(envelope)

    def test_envelope_contract_identity_and_status_are_exact(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(envelope["schema_version"], ENVELOPE_SCHEMA)
        self.assertEqual(envelope["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(envelope["presentation_status"], PRESENTATION_STATUS)

    def test_missing_receipt_is_not_supplied_not_verified(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        envelope = self._build(None, None, context)
        self.assertEqual(envelope["verification_state"], "NOT_SUPPLIED")
        self.assertEqual(envelope["source_state"], "NOT_SUPPLIED")
        self.assertEqual(envelope["blockers"], ["F1_RECEIPT_NOT_SUPPLIED"])
        self.assertIsNone(envelope["report"])
        self.assertTrue(self._verify(envelope, None, None, context))
        self._assert_locked(envelope)

    def test_verified_f1_missing_receipt_remains_missing(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        receipt = self._receipt(None, context)
        envelope = self._build(receipt, None, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "MISSING")
        self.assertEqual(envelope["report"]["report_state"], "UNKNOWN")
        self.assertEqual(envelope["report"], receipt)
        self.assertTrue(self._verify(envelope, receipt, None, context))

    def test_verified_f1_unsupported_v1_receipt_remains_unsupported(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = evaluate_v1(*self._args(context), **self._context_kwargs(context))
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "UNSUPPORTED")
        self.assertEqual(envelope["report"]["report_state"], "UNKNOWN")
        self.assertTrue(self._verify(envelope, receipt, diagnostic, context))

    def test_verified_f1_invalid_receipt_remains_invalid_source(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        diagnostic["diagnostic_hash"] = "0" * 64
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "INVALID")
        self.assertEqual(envelope["report"]["report_state"], "UNKNOWN")
        self.assertTrue(self._verify(envelope, receipt, diagnostic, context))

    def test_wrong_expected_receipt_hash_fails_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(
            receipt,
            diagnostic,
            context,
            expected_receipt_hash="0" * 64,
        )
        self.assertEqual(envelope["verification_state"], "INVALID")
        self.assertIsNone(envelope["report"])

    def test_non_mapping_and_subclass_receipts_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        for value in (True, [], _DictSubclass(receipt)):
            envelope = self._build(value, diagnostic, context)
            with self.subTest(kind=type(value).__name__):
                self.assertEqual(envelope["verification_state"], "INVALID")
                self.assertIsNone(envelope["report"])

    def test_broken_and_resealed_receipt_tamper_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        broken = deepcopy(receipt)
        broken["verification_hash"] = "0" * 64
        changed = deepcopy(receipt)
        changed["report_state"] = "OBSERVED_NO_CONDITIONAL_DEPENDENCE"
        changed = seal_strict_canonical_document(changed, "verification_hash")
        for value in (broken, changed):
            envelope = self._build(value, diagnostic, context)
            with self.subTest(receipt_hash=value["verification_hash"]):
                self.assertEqual(envelope["verification_state"], "INVALID")

    def test_nested_receipt_tamper_fails_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=True)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        receipt["raw_evaluation"]["dependent_test_count"] += 1
        receipt = seal_strict_canonical_document(receipt, "verification_hash")
        self.assertEqual(
            self._build(receipt, diagnostic, context)["verification_state"],
            "INVALID",
        )

    def test_extra_receipt_field_and_authority_alias_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        variants = []
        extra = deepcopy(receipt)
        extra["attacker_text"] = "READY PROFIT LIVE"
        variants.append(extra)
        alias = deepcopy(receipt)
        alias["authority"]["ready"] = True
        variants.append(alias)
        for variant in variants:
            variant = seal_strict_canonical_document(variant, "verification_hash")
            envelope = self._build(variant, diagnostic, context)
            with self.subTest(keys=sorted(variant)):
                self.assertEqual(envelope["verification_state"], "INVALID")
                self.assertNotIn("attacker_text", envelope)
                self.assertNotIn("READY PROFIT LIVE", str(envelope))

    def test_nonfinite_receipt_fails_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        receipt["raw_evaluation"]["dependent_test_count"] = math.nan
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(envelope["verification_state"], "INVALID")

    def test_context_and_diagnostic_mismatch_fail_closed(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        changed_context = deepcopy(context)
        changed_context["expected_registration_hash"] = "0" * 64
        self.assertEqual(
            self._build(receipt, diagnostic, changed_context)["verification_state"],
            "INVALID",
        )
        other_context = self.fixture._common_factor_case(direct_residual=True)
        other_diagnostic = self._v2(other_context)
        self.assertEqual(
            self._build(receipt, other_diagnostic, other_context)["verification_state"],
            "INVALID",
        )

    def test_resealed_envelope_state_report_and_authority_tamper_reject(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        variants = []
        changed = deepcopy(envelope)
        changed["verification_state"] = "INVALID"
        variants.append(changed)
        changed = deepcopy(envelope)
        changed["report"]["report_state"] = "UNKNOWN"
        variants.append(changed)
        changed = deepcopy(envelope)
        changed["authority"]["presentation_mounted"] = True
        variants.append(changed)
        for changed in variants:
            tampered = self._reseal(changed)
            with self.subTest(state=tampered["verification_state"]):
                self.assertFalse(self._verify(tampered, receipt, diagnostic, context))

    def test_broken_envelope_hash_and_non_mapping_never_verify(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        broken = deepcopy(envelope)
        broken["envelope_hash"] = "0" * 64
        self.assertFalse(self._verify(broken, receipt, diagnostic, context))
        self.assertFalse(self._verify(None, receipt, diagnostic, context))
        self.assertFalse(
            self._verify(_DictSubclass(envelope), receipt, diagnostic, context)
        )

    def test_envelope_and_report_are_aggregate_only(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
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
        self.assertFalse(self._all_keys(envelope) & forbidden)

    def test_source_hashes_are_bound_without_source_payloads(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        envelope = self._build(receipt, diagnostic, context)
        self.assertEqual(
            envelope["source_diagnostic_hash"], receipt["source_diagnostic_hash"]
        )
        self.assertEqual(
            envelope["source_v1_diagnostic_hash"],
            receipt["source_v1_diagnostic_hash"],
        )
        self.assertNotIn("diagnostic", envelope)

    def test_envelope_is_deterministic_and_uses_no_external_state(self) -> None:
        context = self.fixture._common_factor_case(direct_residual=False)
        diagnostic = self._v2(context)
        receipt = self._receipt(diagnostic, context)
        first = self._build(receipt, diagnostic, context)
        second = self._build(receipt, diagnostic, context)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
