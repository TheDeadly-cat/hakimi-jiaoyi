import builtins
import math
import random
import time
import unittest
from copy import deepcopy
from unittest.mock import patch

from exchange_terminal.application.strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2 import (
    ENVELOPE_SCHEMA,
    PRESENTATION_STATUS,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2,
    verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class _DictSubclass(dict):
    pass


def _all_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_all_keys(child))
        return keys
    if isinstance(value, list):
        keys = set()
        for child in value:
            keys.update(_all_keys(child))
        return keys
    return set()


class StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeV2Tests(
    unittest.TestCase
):
    def setUp(self):
        from tests.test_strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 import (
            StrategyCorrelationCrossLagFactorConditionalReportConsumerV2Tests,
        )

        self.fixture = StrategyCorrelationCrossLagFactorConditionalReportConsumerV2Tests(
            methodName="runTest"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def _context(self, suppression=False):
        return self.fixture._context(suppression=suppression)

    def _report(self, context, *, overrides=None):
        return self.fixture._consume(context, overrides=overrides)

    def _build(self, report, sources, kwargs, context, *, expected_report_hash=None):
        return build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2(
            report,
            sources["v1"],
            sources["gate"],
            sources["family"],
            sources["f0"],
            context["preregistered_strata"],
            context["aligned_observations"],
            sources["residual"],
            context["residualization_registration"],
            context["factor_observations"],
            expected_report_hash=(
                report.get("verification_hash")
                if expected_report_hash is None and type(report) is dict
                else expected_report_hash
            ),
            **kwargs,
        )

    def _verify(self, envelope, report, sources, kwargs, context):
        return verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2(
            envelope,
            report,
            sources["v1"],
            sources["gate"],
            sources["family"],
            sources["f0"],
            context["preregistered_strata"],
            context["aligned_observations"],
            sources["residual"],
            context["residualization_registration"],
            context["factor_observations"],
            expected_report_hash=(
                report.get("verification_hash") if type(report) is dict else None
            ),
            **kwargs,
        )

    def test_verified_pass_report_is_carried_exactly(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "OBSERVED")
        self.assertEqual(envelope["report"], report)
        self.assertTrue(self._verify(envelope, report, sources, kwargs, context))

    def test_verified_block_report_remains_blocked(self):
        context = self._context(suppression=True)
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["report"]["global_recalibrated_decision"], "BLOCK")
        self.assertEqual(envelope["report"]["gap_state"], "GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED")

    def test_verified_unknown_remains_unknown(self):
        context = self._context()
        report, sources, kwargs = self._report(
            context, overrides={"expected_v1_receipt_hash": "0" * 64}
        )
        envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "UNKNOWN")
        self.assertEqual(envelope["report"]["report_state"], "UNKNOWN")
        self.assertTrue(self._verify(envelope, report, sources, kwargs, context))

    def test_missing_report_is_not_supplied(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(None, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "NOT_SUPPLIED")
        self.assertEqual(envelope["report"], None)
        self.assertTrue(self._verify(envelope, None, sources, kwargs, context))

    def test_old_source_contract_is_unsupported(self):
        context = self._context()
        _, sources, kwargs = self._report(context)
        report = sources["v1"]
        envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "UNSUPPORTED")
        self.assertEqual(envelope["report"], None)

    def test_wrong_expected_report_hash_is_invalid(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(
            report, sources, kwargs, context, expected_report_hash="0" * 64
        )
        self.assertEqual(envelope["verification_state"], "INVALID")
        self.assertEqual(envelope["report"], None)

    def test_coherent_report_reseal_is_invalid(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        changed = deepcopy(report)
        changed["global_test_count"] += 1
        changed = seal_strict_canonical_document(changed, "verification_hash")
        envelope = self._build(changed, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "INVALID")

    def test_source_context_substitution_is_invalid(self):
        context = self._context()
        other = self._context(suppression=True)
        report, sources, kwargs = self._report(context)
        _, other_sources, _ = self._report(other)
        for key in ("v1", "gate", "f0"):
            changed = dict(sources)
            changed[key] = other_sources[key]
            envelope = self._build(report, changed, kwargs, context)
            self.assertEqual(envelope["verification_state"], "INVALID", key)
        changed = dict(sources)
        changed["family"] = deepcopy(sources["family"])
        changed["family"]["global_test_count"] += 1
        changed["family"] = seal_strict_canonical_document(
            changed["family"], "registration_hash"
        )
        envelope = self._build(report, changed, kwargs, context)
        self.assertEqual(envelope["verification_state"], "INVALID", "family")

    def test_residual_row_mutations_are_invalid(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        for rows in (
            sources["residual"][:-1],
            sources["residual"] + [deepcopy(sources["residual"][-1])],
            list(reversed(sources["residual"])),
        ):
            changed = dict(sources)
            changed["residual"] = rows
            envelope = self._build(report, changed, kwargs, context)
            self.assertEqual(envelope["verification_state"], "INVALID")

    def test_contract_and_provenance_are_exact(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["schema_version"], ENVELOPE_SCHEMA)
        self.assertEqual(envelope["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(envelope["presentation_status"], PRESENTATION_STATUS)
        self.assertEqual(envelope["source_report_hash"], report["verification_hash"])
        self.assertEqual(
            envelope["source_two_view_gate_evaluation_hash"],
            report["source_two_view_gate_evaluation_hash"],
        )

    def test_projection_remains_aggregate_only(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        forbidden = {
            "left_identity",
            "right_identity",
            "source_correlation",
            "private_recalculated_test_ledger_hash",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(envelope)))

    def test_authority_is_locked_and_detached(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        self.assertTrue(envelope["authority"]["descriptive_only"])
        self.assertTrue(envelope["authority"]["global_two_view_multiplicity_registered"])
        self.assertTrue(
            all(
                value is False
                for key, value in envelope["authority"].items()
                if key not in {"descriptive_only", "global_two_view_multiplicity_registered"}
            )
        )

    def test_resealed_envelope_tamper_is_rejected(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(report, sources, kwargs, context)
        for key in ("source_state", "report", "authority"):
            changed = deepcopy(envelope)
            if key == "source_state":
                changed[key] = "READY"
            elif key == "report":
                changed[key]["global_test_count"] = 1
            else:
                changed[key]["paper_authorized"] = True
            changed = seal_strict_canonical_document(changed, "envelope_hash")
            self.assertFalse(self._verify(changed, report, sources, kwargs, context))

    def test_non_native_and_nonfinite_reports_are_invalid(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        envelope = self._build(_DictSubclass(report), sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "INVALID")
        changed = deepcopy(report)
        changed["nonfinite_probe"] = math.nan
        envelope = self._build(changed, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "INVALID")

    def test_closed_envelopes_are_deterministic(self):
        context = self._context()
        _, sources, kwargs = self._report(context)
        first = self._build(None, sources, kwargs, context)
        second = self._build(None, sources, kwargs, context)
        self.assertEqual(first, second)

    def test_denied_external_state_is_unused(self):
        context = self._context()
        report, sources, kwargs = self._report(context)
        with patch.object(builtins, "open", side_effect=AssertionError("io")), patch.object(
            time, "time", side_effect=AssertionError("time")
        ), patch.object(random, "random", side_effect=AssertionError("random")):
            envelope = self._build(report, sources, kwargs, context)
        self.assertEqual(envelope["verification_state"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
