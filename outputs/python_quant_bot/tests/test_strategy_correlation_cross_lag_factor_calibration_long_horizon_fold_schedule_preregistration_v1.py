import unittest
from copy import deepcopy
from decimal import getcontext, setcontext

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 import (
    ASSIGNMENT_RULE,
    DUPLICATE_OR_OUT_OF_ORDER_POLICY,
    ELIGIBILITY_RULE,
    EXCESS_OBSERVATION_POLICY,
    FOLD_COUNT,
    FOLD_ORDER,
    INCOMPLETE_PREFIX_POLICY,
    MISSING_DATA_POLICY,
    ROWS_PER_FOLD,
    SCHEDULE_PROTOCOL_ID,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    TOTAL_SCHEDULED_ROWS,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 as source_tests,
)


_DEFAULT = object()


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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonFoldSchedulePreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationProtocolV1Tests(
                methodName="test_positive_source_declares_protocol_without_observations"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.protocol = self.case._build()
        self.preregistration = self.case.source
        self.context = self.case.context
        self.declared_at_utc = "2026-09-16T00:00:00Z"

    def _build(
        self,
        protocol=_DEFAULT,
        preregistration=_DEFAULT,
        context=_DEFAULT,
        expected_protocol_hash=_DEFAULT,
        expected_preregistration_hash=_DEFAULT,
        declared_at_utc=_DEFAULT,
    ):
        protocol = self.protocol if protocol is _DEFAULT else protocol
        preregistration = (
            self.preregistration
            if preregistration is _DEFAULT
            else preregistration
        )
        context = self.context if context is _DEFAULT else context
        expected_protocol_hash = (
            self.protocol["protocol_hash"]
            if expected_protocol_hash is _DEFAULT
            else expected_protocol_hash
        )
        expected_preregistration_hash = (
            self.preregistration["preregistration_hash"]
            if expected_preregistration_hash is _DEFAULT
            else expected_preregistration_hash
        )
        declared_at_utc = (
            self.declared_at_utc
            if declared_at_utc is _DEFAULT
            else declared_at_utc
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
            protocol,
            preregistration,
            context,
            expected_observation_protocol_hash=expected_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            declared_at_utc=declared_at_utc,
        )

    def _verify(self, document, **overrides):
        values = {
            "protocol": self.protocol,
            "preregistration": self.preregistration,
            "context": self.context,
            "expected_protocol_hash": self.protocol["protocol_hash"],
            "expected_preregistration_hash": self.preregistration[
                "preregistration_hash"
            ],
            "declared_at_utc": self.declared_at_utc,
        }
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
            document,
            values["protocol"],
            values["preregistration"],
            values["context"],
            expected_observation_protocol_hash=values["expected_protocol_hash"],
            expected_preregistration_hash=values["expected_preregistration_hash"],
            declared_at_utc=values["declared_at_utc"],
        )

    def test_positive_source_declares_fixed_schedule_without_observations(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(
            document["schedule_state"],
            "SCHEDULE_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED",
        )
        self.assertTrue(document["facts"]["fold_schedule_pinned"])
        self.assertTrue(document["facts"]["fold_assignment_deterministic"])
        self.assertFalse(document["facts"]["future_observations_collected"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["schedule_protocol_id"], SCHEDULE_PROTOCOL_ID)

    def test_source_identity_factor_and_hash_bindings_are_exact(self):
        document = self._build()
        registration = self.context["residualization_registration"]
        self.assertEqual(document["identity_count"], 2)
        self.assertEqual(
            document["identity_order_hash"], registration["identity_order_hash"]
        )
        self.assertEqual(document["factor_id"], registration["factor_id"])
        self.assertEqual(
            document["factor_source_hash"], registration["factor_source_hash"]
        )
        self.assertEqual(
            document["source_residualization_registration_hash"],
            registration["registration_hash"],
        )

    def test_four_fixed_contiguous_position_ranges_are_exact(self):
        document = self._build()
        self.assertEqual(document["fold_count"], FOLD_COUNT)
        self.assertEqual(document["fold_order"], list(FOLD_ORDER))
        self.assertEqual(
            document["fold_position_ranges"],
            [
                {
                    "end_position_inclusive": 19,
                    "fold_id": "LH-FOLD-01",
                    "start_position_inclusive": 0,
                },
                {
                    "end_position_inclusive": 39,
                    "fold_id": "LH-FOLD-02",
                    "start_position_inclusive": 20,
                },
                {
                    "end_position_inclusive": 59,
                    "fold_id": "LH-FOLD-03",
                    "start_position_inclusive": 40,
                },
                {
                    "end_position_inclusive": 79,
                    "fold_id": "LH-FOLD-04",
                    "start_position_inclusive": 60,
                },
            ],
        )

    def test_support_and_total_prefix_are_exact(self):
        document = self._build()
        self.assertEqual(document["rows_per_fold"], ROWS_PER_FOLD)
        self.assertEqual(document["total_scheduled_rows"], TOTAL_SCHEDULED_ROWS)
        self.assertEqual(document["maximum_evaluated_lag"], 12)
        self.assertEqual(document["minimum_pairs_at_maximum_lag"], 8)

    def test_assignment_and_failure_policies_are_exact(self):
        document = self._build()
        self.assertEqual(document["assignment_rule"], ASSIGNMENT_RULE)
        self.assertEqual(document["eligibility_rule"], ELIGIBILITY_RULE)
        self.assertEqual(document["missing_data_policy"], MISSING_DATA_POLICY)
        self.assertEqual(
            document["duplicate_or_out_of_order_policy"],
            DUPLICATE_OR_OUT_OF_ORDER_POLICY,
        )
        self.assertEqual(
            document["incomplete_prefix_policy"], INCOMPLETE_PREFIX_POLICY
        )
        self.assertEqual(
            document["excess_observation_policy"], EXCESS_OBSERVATION_POLICY
        )

    def test_schedule_binding_hash_covers_design_and_sources(self):
        document = self._build()
        excluded = {
            "authority",
            "blockers",
            "facts",
            "identity_count",
            "schedule_binding_hash",
            "schedule_hash",
            "schedule_protocol_id",
            "schedule_reason",
            "schedule_state",
            "schema_version",
            "source_observation_protocol_schema",
            "source_preregistered_at_utc",
            "source_state",
            "static_fingerprint",
        }
        binding = {
            key: value for key, value in document.items() if key not in excluded
        }
        self.assertEqual(
            document["schedule_binding_hash"], strict_canonical_hash(binding)
        )

    def test_expected_source_hashes_are_bound(self):
        wrong_protocol = self._build(expected_protocol_hash="0" * 64)
        wrong_preregistration = self._build(
            expected_preregistration_hash="0" * 64
        )
        self.assertEqual(
            wrong_protocol["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_HASH_MISMATCH"]
        )
        self.assertEqual(
            wrong_preregistration["blockers"],
            ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"],
        )

    def test_context_fold_count_tamper_is_rejected(self):
        context = deepcopy(self.context)
        context["report_consumer_v7"]["fold_count"] = 5
        document = self._build(context=context)
        self.assertEqual(document["schedule_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"]
        )

    def test_context_identity_hash_tamper_is_rejected(self):
        context = deepcopy(self.context)
        context["residualization_registration"]["identity_order_hash"] = "0" * 64
        document = self._build(context=context)
        self.assertEqual(document["schedule_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"]
        )

    def test_resealed_source_protocol_tamper_is_rejected(self):
        protocol = deepcopy(self.protocol)
        protocol["minimum_rows_per_fold"] = 21
        protocol = seal_strict_canonical_document(
            {key: value for key, value in protocol.items() if key != "protocol_hash"},
            "protocol_hash",
        )
        document = self._build(
            protocol=protocol,
            expected_protocol_hash=protocol["protocol_hash"],
        )
        self.assertEqual(document["schedule_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"]
        )

    def test_declared_time_must_not_precede_preregistration(self):
        document = self._build(declared_at_utc="2026-08-21T23:59:59Z")
        self.assertEqual(
            document["blockers"], ["SCHEDULE_DECLARATION_BEFORE_PREREGISTRATION"]
        )

    def test_declared_time_must_be_strictly_before_evaluation(self):
        document = self._build(declared_at_utc="2026-10-01T00:00:00Z")
        self.assertEqual(
            document["blockers"], ["SCHEDULE_DECLARATION_NOT_BEFORE_EVALUATION"]
        )

    def test_declared_time_grammar_is_strict(self):
        for value in (
            "2026-09-16T00:00:00+00:00",
            "2026-09-16 00:00:00Z",
            "not-a-time",
        ):
            document = self._build(declared_at_utc=value)
            self.assertEqual(
                document["blockers"], ["SCHEDULE_DECLARATION_TIME_INVALID"]
            )

    def test_blocked_source_is_monotone_and_verifiable(self):
        overrides = self.case.case._block_context()
        preregistration = self.case.case._build(**overrides)
        context = self.case._capture_context(preregistration, **overrides)
        protocol = self.case._build(
            source=preregistration,
            context=context,
            expected_hash=preregistration["preregistration_hash"],
        )
        document = self._build(
            protocol=protocol,
            preregistration=preregistration,
            context=context,
            expected_protocol_hash=protocol["protocol_hash"],
            expected_preregistration_hash=preregistration["preregistration_hash"],
        )
        self.assertEqual(document["source_state"], "BLOCKED")
        self.assertEqual(document["schedule_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_DECLARED"]
        )
        self.assertTrue(
            self._verify(
                document,
                protocol=protocol,
                preregistration=preregistration,
                context=context,
                expected_protocol_hash=protocol["protocol_hash"],
                expected_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
            )
        )

    def test_missing_source_is_fail_closed(self):
        document = self._build(protocol=None)
        self.assertEqual(document["schedule_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_OBJECT"]
        )

    def test_document_contains_no_future_rows_returns_or_fold_dates(self):
        document = self._build()
        forbidden = {
            "factor_return",
            "first_observation_date",
            "fold_dates",
            "last_observation_date",
            "observation_batch",
            "observations",
            "result",
            "results",
            "returns",
            "rows",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))
        self.assertFalse(document["facts"]["fold_boundaries_date_observed"])

    def test_authority_is_permanently_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        self.assertFalse(document["facts"]["external_schedule_time_verified"])

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["schedule_hash"], second["schedule_hash"])

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["rows_per_fold"] = 21
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(
            set(document),
            {
                "assignment_rule",
                "authority",
                "blockers",
                "declared_at_utc",
                "duplicate_or_out_of_order_policy",
                "eligibility_rule",
                "evaluation_not_before_date",
                "excess_observation_policy",
                "factor_id",
                "factor_source_hash",
                "facts",
                "fold_count",
                "fold_order",
                "fold_position_ranges",
                "future_evaluation_id",
                "identity_count",
                "identity_order_hash",
                "incomplete_prefix_policy",
                "maximum_evaluated_lag",
                "minimum_pairs_at_maximum_lag",
                "missing_data_policy",
                "rows_per_fold",
                "schedule_binding_hash",
                "schedule_hash",
                "schedule_protocol_id",
                "schedule_reason",
                "schedule_state",
                "schema_version",
                "source_observation_protocol_hash",
                "source_observation_protocol_schema",
                "source_preregistered_at_utc",
                "source_preregistration_hash",
                "source_report_consumer_v7_hash",
                "source_residualization_registration_hash",
                "source_state",
                "static_fingerprint",
                "total_scheduled_rows",
            },
        )


if __name__ == "__main__":
    unittest.main()
