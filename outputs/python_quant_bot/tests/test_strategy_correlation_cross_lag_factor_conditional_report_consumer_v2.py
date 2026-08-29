import builtins
import math
import random
import time
import unittest
from copy import deepcopy
from unittest.mock import patch

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_conditional_diagnostic,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 import (
    PERMISSION_STATE,
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA,
    consume_strategy_correlation_cross_lag_factor_conditional_report_v2,
    verify_strategy_correlation_cross_lag_factor_conditional_report_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_gate import (
    evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate,
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


class StrategyCorrelationCrossLagFactorConditionalReportConsumerV2Tests(
    unittest.TestCase
):
    def setUp(self):
        from tests.test_strategy_correlation_cross_lag_two_view_multiplicity_gate import (
            StrategyCorrelationCrossLagTwoViewMultiplicityGateTests,
        )

        self.fixture = StrategyCorrelationCrossLagTwoViewMultiplicityGateTests(
            methodName="runTest"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def _context(self, suppression=False):
        if suppression:
            return self.fixture._suppression_context()
        return self.fixture._pass_context()

    def _sources(self, context):
        family = self.fixture._family(context)
        f0 = self.fixture._f0(context)
        residual = self.fixture._residual(context)
        v1 = consume_strategy_correlation_cross_lag_factor_conditional_diagnostic(
            f0,
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
            expected_diagnostic_hash=f0["diagnostic_hash"],
        )
        gate = evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate(
            family,
            f0,
            context["preregistered_strata"],
            context["aligned_observations"],
            residual,
            context["residualization_registration"],
            context["factor_observations"],
            expected_stratum_assignment_hash=context[
                "expected_stratum_assignment_hash"
            ],
            expected_residualization_registration_hash=context[
                "expected_registration_hash"
            ],
            expected_factor_observations_hash=context[
                "expected_factor_observations_hash"
            ],
            expected_family_registration_hash=family["registration_hash"],
            expected_f0_diagnostic_hash=f0["diagnostic_hash"],
            expected_residual_input_hash=f0["residual_input_hash"],
        )
        return {
            "family": family,
            "f0": f0,
            "gate": gate,
            "residual": residual,
            "v1": v1,
        }

    def _kwargs(self, context, sources):
        return {
            "expected_stratum_assignment_hash": context[
                "expected_stratum_assignment_hash"
            ],
            "expected_residualization_registration_hash": context[
                "expected_registration_hash"
            ],
            "expected_factor_observations_hash": context[
                "expected_factor_observations_hash"
            ],
            "expected_family_registration_hash": sources["family"][
                "registration_hash"
            ],
            "expected_f0_diagnostic_hash": sources["f0"]["diagnostic_hash"],
            "expected_residual_input_hash": sources["f0"]["residual_input_hash"],
            "expected_v1_receipt_hash": sources["v1"]["verification_hash"],
            "expected_two_view_gate_hash": sources["gate"]["evaluation_hash"],
        }

    def _consume(self, context, sources=None, *, overrides=None):
        sources = self._sources(context) if sources is None else sources
        kwargs = self._kwargs(context, sources)
        if overrides:
            kwargs.update(overrides)
        document = consume_strategy_correlation_cross_lag_factor_conditional_report_v2(
            sources["v1"],
            sources["gate"],
            sources["family"],
            sources["f0"],
            context["preregistered_strata"],
            context["aligned_observations"],
            sources["residual"],
            context["residualization_registration"],
            context["factor_observations"],
            **kwargs,
        )
        return document, sources, kwargs

    def _verify(self, document, context, sources, kwargs, expected_hash=None):
        return verify_strategy_correlation_cross_lag_factor_conditional_report_v2(
            document,
            sources["v1"],
            sources["gate"],
            sources["family"],
            sources["f0"],
            context["preregistered_strata"],
            context["aligned_observations"],
            sources["residual"],
            context["residualization_registration"],
            context["factor_observations"],
            expected_verification_hash=(
                document["verification_hash"]
                if expected_hash is None
                else expected_hash
            ),
            **kwargs,
        )

    def test_pass_sources_produce_observed_unactivated_v2(self):
        context = self._context()
        document, sources, kwargs = self._consume(context)
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["gap_state"], "NO_GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED")
        self.assertEqual(
            document["report_state"],
            "GLOBAL_TWO_VIEW_FAMILY_OBSERVED_NOT_ACTIVATED",
        )
        self.assertEqual(document["global_recalibrated_decision"], "PASS")
        self.assertTrue(self._verify(document, context, sources, kwargs))

    def test_suppression_preserves_source_and_global_block(self):
        context = self._context(suppression=True)
        document, sources, kwargs = self._consume(context)
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["gap_state"], "GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED")
        self.assertEqual(document["global_recalibrated_decision"], "BLOCK")
        self.assertTrue(document["facts"]["source_block_preserved"])
        self.assertTrue(self._verify(document, context, sources, kwargs))

    def test_contract_identity_is_exact(self):
        document, _, _ = self._consume(self._context())
        self.assertEqual(document["schema_version"], VERIFICATION_SCHEMA)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["permission_state"], PERMISSION_STATE)
        self.assertEqual(document["views"], ["RAW", "RESIDUAL"])
        self.assertEqual(document["lags"], [-2, -1, 1, 2])
        self.assertEqual(document["per_view_test_count"], 4)
        self.assertEqual(document["global_test_count"], 8)

    def test_every_expected_hash_is_bound(self):
        context = self._context()
        _, sources, kwargs = self._consume(context)
        for key in kwargs:
            changed = dict(kwargs)
            changed[key] = "0" * 64
            document, _, _ = self._consume(context, sources, overrides=changed)
            self.assertEqual(document["source_state"], "UNKNOWN", key)

    def test_v1_tamper_and_coherent_reseal_fail_closed(self):
        context = self._context()
        _, sources, _ = self._consume(context)
        changed = deepcopy(sources["v1"])
        changed["gap_state"] = "NO_GAP"
        changed = seal_strict_canonical_document(changed, "verification_hash")
        sources["v1"] = changed
        document, _, _ = self._consume(context, sources)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["F1_RECEIPT_NOT_VERIFIED"])

    def test_f3_tamper_and_coherent_reseal_fail_closed(self):
        context = self._context()
        _, sources, _ = self._consume(context)
        changed = deepcopy(sources["gate"])
        changed["global_test_count"] += 1
        changed = seal_strict_canonical_document(changed, "evaluation_hash")
        sources["gate"] = changed
        document, _, _ = self._consume(context, sources)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["F3_GATE_NOT_VERIFIED"])

    def test_residual_row_mutations_fail_closed(self):
        context = self._context()
        for mutate in (
            lambda rows: rows[:-1],
            lambda rows: rows + [deepcopy(rows[-1])],
            lambda rows: list(reversed(rows)),
            lambda rows: rows + [{**deepcopy(rows[-1]), "sequence_number": 1001}],
        ):
            _, sources, _ = self._consume(context)
            sources["residual"] = mutate(sources["residual"])
            document, _, _ = self._consume(context, sources)
            self.assertEqual(document["source_state"], "UNKNOWN")

    def test_f0_family_and_context_substitution_fail_closed(self):
        pass_context = self._context()
        suppression_context = self._context(suppression=True)
        _, pass_sources, _ = self._consume(pass_context)
        suppression_sources = self._sources(suppression_context)
        for key in ("f0", "gate", "v1"):
            changed = dict(pass_sources)
            changed[key] = suppression_sources[key]
            document, _, _ = self._consume(pass_context, changed)
            self.assertEqual(document["source_state"], "UNKNOWN", key)
        changed = dict(pass_sources)
        changed["family"] = deepcopy(pass_sources["family"])
        changed["family"]["global_test_count"] += 1
        changed["family"] = seal_strict_canonical_document(
            changed["family"], "registration_hash"
        )
        document, _, _ = self._consume(pass_context, changed)
        self.assertEqual(document["source_state"], "UNKNOWN", "family")

    def test_cross_link_mismatch_closes_after_independent_verifiers(self):
        import exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 as module

        context = self._context()
        _, sources, _ = self._consume(context)
        changed = deepcopy(sources["v1"])
        changed["source_raw_evaluation_hash"] = "a" * 64
        changed = seal_strict_canonical_document(changed, "verification_hash")
        sources["v1"] = changed
        with patch.object(
            module,
            "verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt",
            return_value=True,
        ), patch.object(
            module,
            "verify_strategy_correlation_cross_lag_two_view_multiplicity_gate",
            return_value=True,
        ):
            document, _, _ = self._consume(context, sources)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["SOURCE_CROSS_LINK_MISMATCH"])

    def test_v2_resealed_tamper_is_rejected(self):
        context = self._context()
        document, sources, kwargs = self._consume(context)
        for path in ("global_test_count", "blockers", "facts", "authority"):
            changed = deepcopy(document)
            if path == "global_test_count":
                changed[path] += 1
            elif path == "blockers":
                changed[path] = []
            elif path == "facts":
                changed[path]["source_cross_links_verified"] = False
            else:
                changed[path]["paper_authorized"] = True
            changed = seal_strict_canonical_document(changed, "verification_hash")
            self.assertFalse(
                self._verify(changed, context, sources, kwargs, changed["verification_hash"]),
                path,
            )

    def test_projection_is_aggregate_only(self):
        document, _, _ = self._consume(self._context())
        keys = _all_keys(document)
        self.assertTrue(
            {
                "left_identity",
                "right_identity",
                "source_correlation",
                "global_adjusted_absolute_lower",
                "private_recalculated_test_ledger_hash",
            }.isdisjoint(keys)
        )
        self.assertEqual([item["view"] for item in document["view_summaries"]], ["RAW", "RESIDUAL"])

    def test_superseded_v1_blockers_are_not_duplicated(self):
        document, _, _ = self._consume(self._context())
        self.assertNotIn("GLOBAL_TWO_VIEW_MULTIPLICITY_NOT_REGISTERED", document["blockers"])
        self.assertNotIn("FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED", document["blockers"])
        self.assertIn("FACTOR_CONDITIONAL_REPORT_V2_NOT_ACTIVATED", document["blockers"])
        self.assertIn("TWO_VIEW_MULTIPLICITY_GATE_NOT_ACTIVATED", document["blockers"])

    def test_authority_is_permanently_locked(self):
        for suppression in (False, True):
            document, _, _ = self._consume(self._context(suppression=suppression))
            self.assertTrue(document["authority"]["descriptive_only"])
            self.assertTrue(
                all(
                    value is False
                    for key, value in document["authority"].items()
                    if key != "descriptive_only"
                )
            )

    def test_unknown_is_deterministic_and_verifiable(self):
        context = self._context()
        _, sources, _ = self._consume(context)
        overrides = {"expected_v1_receipt_hash": "0" * 64}
        first, _, kwargs = self._consume(context, sources, overrides=overrides)
        second, _, _ = self._consume(context, sources, overrides=overrides)
        self.assertEqual(first, second)
        self.assertEqual(first["source_state"], "UNKNOWN")
        self.assertTrue(self._verify(first, context, sources, kwargs))

    def test_non_native_and_nonfinite_sources_never_escape(self):
        context = self._context()
        _, sources, _ = self._consume(context)
        changed = dict(sources)
        changed["v1"] = _DictSubclass(sources["v1"])
        document, _, _ = self._consume(context, changed)
        self.assertEqual(document["source_state"], "UNKNOWN")
        changed = dict(sources)
        changed["f0"] = deepcopy(sources["f0"])
        changed["f0"]["nonfinite_probe"] = math.nan
        document, _, _ = self._consume(context, changed)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_verifier_rejects_non_mapping_and_wrong_hash(self):
        context = self._context()
        document, sources, kwargs = self._consume(context)
        self.assertFalse(self._verify([], context, sources, kwargs, "0" * 64))
        self.assertFalse(self._verify(document, context, sources, kwargs, "0" * 64))

    def test_source_unknown_never_becomes_observed(self):
        context = self._context()
        _, sources, _ = self._consume(context)
        sources["residual"][0]["returns"]["A"] += 1e-6
        document, _, _ = self._consume(context, sources)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["report_state"], "UNKNOWN")
        self.assertEqual(document["global_recalibrated_decision"], "UNKNOWN")

    def test_determinism_and_denied_external_state(self):
        context = self._context()
        sources = self._sources(context)
        with patch.object(builtins, "open", side_effect=AssertionError("io")), patch.object(
            time, "time", side_effect=AssertionError("time")
        ), patch.object(random, "random", side_effect=AssertionError("random")):
            first, _, _ = self._consume(context, sources)
            second, _, _ = self._consume(context, sources)
        self.assertEqual(first, second)
        self.assertEqual(first["source_state"], "OBSERVED")


if __name__ == "__main__":
    unittest.main()
