import unittest
from copy import deepcopy
from decimal import getcontext, setcontext
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1 as service_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1 import (
    CALENDAR_LIBRARY_DISTRIBUTION,
    CALENDAR_LIBRARY_VERSION,
    CALENDAR_PROTOCOL_ID,
    COMMON_DATE_RULE,
    MISSING_CALENDAR_POLICY,
    SCHEMA_VERSION,
    SESSION_COMPLETION_POLICY,
    SESSION_LABEL_POLICY,
    STATIC_FINGERPRINT,
    UNSUPPORTED_CALENDAR_POLICY,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 as source_tests,
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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonFoldSchedulePreregistrationV1Tests(
                methodName="test_positive_source_declares_fixed_schedule_without_observations"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.schedule = self.case._build()
        self.schedule_context = {
            "declared_at_utc": self.case.declared_at_utc,
            "expected_observation_protocol_hash": self.case.protocol["protocol_hash"],
            "expected_preregistration_hash": self.case.preregistration[
                "preregistration_hash"
            ],
            "long_horizon_preregistration_v1": self.case.preregistration,
            "observation_protocol_v1": self.case.protocol,
            "source_verification_context": self.case.context,
        }
        self.identity_calendar_ids = ["XNYS", "XNYS"]
        self.factor_calendar_id = "XNYS"
        self.declared_at_utc = "2026-09-17T00:00:00Z"

    def _build(
        self,
        schedule=_DEFAULT,
        context=_DEFAULT,
        expected_schedule_hash=_DEFAULT,
        identity_calendar_ids=_DEFAULT,
        factor_calendar_id=_DEFAULT,
        declared_at_utc=_DEFAULT,
    ):
        schedule = self.schedule if schedule is _DEFAULT else schedule
        context = self.schedule_context if context is _DEFAULT else context
        expected_schedule_hash = (
            self.schedule["schedule_hash"]
            if expected_schedule_hash is _DEFAULT
            else expected_schedule_hash
        )
        identity_calendar_ids = (
            self.identity_calendar_ids
            if identity_calendar_ids is _DEFAULT
            else identity_calendar_ids
        )
        factor_calendar_id = (
            self.factor_calendar_id
            if factor_calendar_id is _DEFAULT
            else factor_calendar_id
        )
        declared_at_utc = (
            self.declared_at_utc
            if declared_at_utc is _DEFAULT
            else declared_at_utc
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
            schedule,
            context,
            expected_schedule_hash=expected_schedule_hash,
            identity_calendar_ids=identity_calendar_ids,
            factor_calendar_id=factor_calendar_id,
            declared_at_utc=declared_at_utc,
        )

    def _verify(self, document, **overrides):
        values = {
            "schedule": self.schedule,
            "context": self.schedule_context,
            "expected_schedule_hash": self.schedule["schedule_hash"],
            "identity_calendar_ids": self.identity_calendar_ids,
            "factor_calendar_id": self.factor_calendar_id,
            "declared_at_utc": self.declared_at_utc,
        }
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
            document,
            values["schedule"],
            values["context"],
            expected_schedule_hash=values["expected_schedule_hash"],
            identity_calendar_ids=values["identity_calendar_ids"],
            factor_calendar_id=values["factor_calendar_id"],
            declared_at_utc=values["declared_at_utc"],
        )

    def test_exchange_calendar_assignments_are_declared_not_time_attested(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(
            document["calendar_registration_state"],
            "CALENDAR_ASSIGNMENT_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED",
        )
        self.assertTrue(document["facts"]["calendar_assignments_pinned"])
        self.assertFalse(document["facts"]["calendar_sessions_evaluated"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_and_library_are_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["calendar_protocol_id"], CALENDAR_PROTOCOL_ID)
        self.assertEqual(
            document["calendar_library_distribution"],
            CALENDAR_LIBRARY_DISTRIBUTION,
        )
        self.assertEqual(document["calendar_library_version"], CALENDAR_LIBRARY_VERSION)

    def test_identity_assignments_are_position_bound_without_identity_labels(self):
        document = self._build()
        self.assertEqual(
            document["identity_calendar_assignments"],
            [
                {"calendar_id": "XNYS", "identity_index": 0},
                {"calendar_id": "XNYS", "identity_index": 1},
            ],
        )
        self.assertEqual(document["identity_count"], 2)
        self.assertNotIn("identity", _all_keys(document))

    def test_mixed_exchange_and_twenty_four_seven_assignments_are_supported(self):
        document = self._build(
            identity_calendar_ids=["XNYS", "24/7"],
            factor_calendar_id="24/7",
        )
        self.assertNotEqual(document["calendar_registration_state"], "UNKNOWN")
        self.assertEqual(document["distinct_calendar_ids"], ["24/7", "XNYS"])

    def test_assignment_hash_covers_positions_rules_library_and_schedule(self):
        document = self._build()
        binding = {
            "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
            "calendar_library_version": CALENDAR_LIBRARY_VERSION,
            "common_date_rule": COMMON_DATE_RULE,
            "factor_calendar_id": "XNYS",
            "identity_calendar_assignments": document[
                "identity_calendar_assignments"
            ],
            "identity_order_hash": document["identity_order_hash"],
            "session_completion_policy": SESSION_COMPLETION_POLICY,
            "session_label_policy": SESSION_LABEL_POLICY,
            "source_schedule_hash": self.schedule["schedule_hash"],
        }
        self.assertEqual(
            document["identity_calendar_assignment_hash"],
            strict_canonical_hash(binding),
        )

    def test_common_date_and_failure_policies_are_exact(self):
        document = self._build()
        self.assertEqual(document["common_date_rule"], COMMON_DATE_RULE)
        self.assertEqual(
            document["session_completion_policy"], SESSION_COMPLETION_POLICY
        )
        self.assertEqual(document["session_label_policy"], SESSION_LABEL_POLICY)
        self.assertEqual(document["missing_calendar_policy"], MISSING_CALENDAR_POLICY)
        self.assertEqual(
            document["unsupported_calendar_policy"], UNSUPPORTED_CALENDAR_POLICY
        )

    def test_identity_calendar_count_and_types_are_exact(self):
        for value in (None, "XNYS", ["XNYS"], ["XNYS", 1], ["XNYS", ""]):
            document = self._build(identity_calendar_ids=value)
            self.assertEqual(
                document["blockers"], ["IDENTITY_CALENDAR_ASSIGNMENTS_INVALID"]
            )

    def test_unknown_identity_calendar_is_blocked(self):
        document = self._build(identity_calendar_ids=["XNYS", "UNKNOWN-CALENDAR"])
        self.assertEqual(document["blockers"], ["IDENTITY_CALENDAR_UNSUPPORTED"])

    def test_factor_calendar_is_required_and_supported(self):
        missing = self._build(factor_calendar_id="")
        unknown = self._build(factor_calendar_id="UNKNOWN-CALENDAR")
        self.assertEqual(missing["blockers"], ["FACTOR_CALENDAR_ASSIGNMENT_INVALID"])
        self.assertEqual(unknown["blockers"], ["FACTOR_CALENDAR_UNSUPPORTED"])

    def test_alias_calendar_ids_are_noncanonical_and_blocked(self):
        self.assertIn(
            "NYSE",
            service_module.exchange_calendars.get_calendar_names(
                include_aliases=True
            ),
        )
        self.assertNotIn(
            "NYSE",
            service_module.exchange_calendars.get_calendar_names(
                include_aliases=False
            ),
        )
        self.assertEqual(
            service_module.exchange_calendars.get_calendar("NYSE").name,
            "XNYS",
        )
        identity_alias = self._build(identity_calendar_ids=["XNYS", "NYSE"])
        factor_alias = self._build(factor_calendar_id="NYSE")
        self.assertEqual(
            identity_alias["blockers"],
            ["IDENTITY_CALENDAR_NONCANONICAL"],
        )
        self.assertEqual(
            factor_alias["blockers"],
            ["FACTOR_CALENDAR_NONCANONICAL"],
        )

    def test_library_absence_is_fail_closed(self):
        with patch.object(service_module, "exchange_calendars", None):
            document = self._build()
        self.assertEqual(document["blockers"], ["CALENDAR_LIBRARY_UNAVAILABLE"])

    def test_library_version_mismatch_is_fail_closed(self):
        with patch.object(service_module, "distribution_version", return_value="4.13.1"):
            document = self._build()
        self.assertEqual(document["blockers"], ["CALENDAR_LIBRARY_VERSION_MISMATCH"])

    def test_loaded_module_version_mismatch_is_fail_closed(self):
        with patch.object(
            service_module.exchange_calendars,
            "__version__",
            "4.13.1",
        ):
            document = self._build()
        self.assertEqual(
            document["blockers"],
            ["CALENDAR_LIBRARY_MODULE_VERSION_MISMATCH"],
        )

    def test_calendar_registry_exception_is_fail_closed(self):
        with patch.object(
            service_module.exchange_calendars,
            "get_calendar_names",
            side_effect=RuntimeError("registry unavailable"),
        ):
            document = self._build()
        self.assertEqual(document["blockers"], ["CALENDAR_LIBRARY_UNAVAILABLE"])
        self.assertEqual(document["calendar_registration_state"], "UNKNOWN")
        self.assertFalse(document["authority"]["calendar_enforcement_activated"])

    def test_expected_schedule_hash_is_bound(self):
        document = self._build(expected_schedule_hash="0" * 64)
        self.assertEqual(document["blockers"], ["SOURCE_SCHEDULE_HASH_MISMATCH"])

    def test_schedule_context_requires_exact_fields(self):
        missing = deepcopy(self.schedule_context)
        missing.pop("declared_at_utc")
        extra = deepcopy(self.schedule_context)
        extra["authority"] = "forged"
        for context in (missing, extra):
            document = self._build(context=context)
            self.assertEqual(
                document["blockers"], ["SCHEDULE_VERIFICATION_CONTEXT_INVALID"]
            )

    def test_resealed_schedule_tamper_is_rejected(self):
        schedule = deepcopy(self.schedule)
        schedule["identity_count"] = 3
        schedule = seal_strict_canonical_document(
            {key: value for key, value in schedule.items() if key != "schedule_hash"},
            "schedule_hash",
        )
        document = self._build(
            schedule=schedule,
            expected_schedule_hash=schedule["schedule_hash"],
        )
        self.assertEqual(document["blockers"], ["SOURCE_SCHEDULE_NOT_VERIFIED"])

    def test_declared_time_must_not_precede_schedule(self):
        document = self._build(declared_at_utc="2026-09-15T23:59:59Z")
        self.assertEqual(document["blockers"], ["CALENDAR_DECLARATION_BEFORE_SCHEDULE"])

    def test_declared_time_must_be_strictly_before_evaluation(self):
        document = self._build(declared_at_utc="2026-10-01T00:00:00Z")
        self.assertEqual(
            document["blockers"], ["CALENDAR_DECLARATION_NOT_BEFORE_EVALUATION"]
        )

    def test_declared_time_grammar_is_strict(self):
        for value in (
            "2026-09-17T00:00:00+00:00",
            "2026-09-17 00:00:00Z",
            "not-a-time",
        ):
            document = self._build(declared_at_utc=value)
            self.assertEqual(
                document["blockers"], ["CALENDAR_DECLARATION_TIME_INVALID"]
            )

    def test_document_contains_no_observations_sessions_or_results(self):
        document = self._build()
        forbidden = {
            "observation_batch",
            "observations",
            "result",
            "results",
            "returns",
            "rows",
            "session_dates",
            "session_opens",
            "session_closes",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))

    def test_authority_is_permanently_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        self.assertFalse(
            document["facts"]["external_calendar_registration_time_verified"]
        )

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(
            first["calendar_registration_hash"],
            second["calendar_registration_hash"],
        )

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["factor_calendar_id"] = "24/7"
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
                "authority",
                "blockers",
                "calendar_library_distribution",
                "calendar_library_version",
                "calendar_protocol_id",
                "calendar_registration_hash",
                "calendar_registration_state",
                "common_date_rule",
                "declared_at_utc",
                "distinct_calendar_ids",
                "evaluation_not_before_date",
                "factor_calendar_id",
                "factor_id",
                "factor_source_hash",
                "facts",
                "future_evaluation_id",
                "identity_calendar_assignment_hash",
                "identity_calendar_assignments",
                "identity_count",
                "identity_order_hash",
                "missing_calendar_policy",
                "registration_reason",
                "schema_version",
                "session_completion_policy",
                "session_label_policy",
                "source_schedule_hash",
                "source_schedule_schema",
                "source_state",
                "static_fingerprint",
                "unsupported_calendar_policy",
            },
        )


if __name__ == "__main__":
    unittest.main()
