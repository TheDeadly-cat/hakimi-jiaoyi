import unittest
from copy import deepcopy
from datetime import timedelta, timezone
from decimal import getcontext, setcontext
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as service_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1 import (
    CALENDAR_LIBRARY_DISTRIBUTION,
    CALENDAR_LIBRARY_VERSION,
    COMMON_DATE_RULE,
    SESSION_COMPLETION_POLICY,
    SESSION_LABEL_POLICY,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 import (
    CALENDAR_SESSION_PROTOCOL_ID,
    POSITIVE_STATE,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 as fold_schedule_source_tests,
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1 as source_tests,
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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionVerifierV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationBatchVerifierV1Tests(
                methodName="test_valid_batch_content_is_verified_but_not_admitted"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.schedule = self.case.schedule
        self.schedule_context = self.case.schedule_context
        self.batch = self.case.batch
        self.batch_verification = self.case._build()
        self.identity_calendar_ids = ["24/7", "24/7"]
        self.factor_calendar_id = "24/7"
        self.declared_at_utc = "2026-09-17T00:00:00Z"
        self.calendar_registration = self._calendar_registration()
        self.calendar_context = self._calendar_context()
        self.batch_context = self._batch_context()

    def _calendar_registration(
        self,
        identity_calendar_ids=_DEFAULT,
        factor_calendar_id=_DEFAULT,
        schedule=_DEFAULT,
        schedule_context=_DEFAULT,
    ):
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
        schedule = self.schedule if schedule is _DEFAULT else schedule
        schedule_context = (
            self.schedule_context
            if schedule_context is _DEFAULT
            else schedule_context
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
            schedule,
            schedule_context,
            expected_schedule_hash=schedule["schedule_hash"],
            identity_calendar_ids=identity_calendar_ids,
            factor_calendar_id=factor_calendar_id,
            declared_at_utc=self.declared_at_utc,
        )

    def _calendar_context(
        self,
        identity_calendar_ids=_DEFAULT,
        factor_calendar_id=_DEFAULT,
        schedule=_DEFAULT,
        schedule_context=_DEFAULT,
    ):
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
        schedule = self.schedule if schedule is _DEFAULT else schedule
        schedule_context = (
            self.schedule_context
            if schedule_context is _DEFAULT
            else schedule_context
        )
        return {
            "declared_at_utc": self.declared_at_utc,
            "expected_schedule_hash": schedule["schedule_hash"],
            "factor_calendar_id": factor_calendar_id,
            "fold_schedule_v1": schedule,
            "identity_calendar_ids": identity_calendar_ids,
            "schedule_verification_context": schedule_context,
        }

    def _batch_context(
        self,
        batch=_DEFAULT,
        signature_verification=_DEFAULT,
        signature_context=_DEFAULT,
        schedule=_DEFAULT,
        schedule_context=_DEFAULT,
    ):
        batch = self.batch if batch is _DEFAULT else batch
        signature_verification = (
            self.case.signature_verification
            if signature_verification is _DEFAULT
            else signature_verification
        )
        signature_context = (
            self.case.signature_context
            if signature_context is _DEFAULT
            else signature_context
        )
        schedule = self.schedule if schedule is _DEFAULT else schedule
        schedule_context = (
            self.schedule_context
            if schedule_context is _DEFAULT
            else schedule_context
        )
        return {
            "expected_batch_hash": batch["observation_batch_hash"],
            "expected_schedule_hash": schedule["schedule_hash"],
            "expected_signature_verification_hash": signature_verification[
                "verification_hash"
            ],
            "fold_schedule_v1": schedule,
            "schedule_verification_context": schedule_context,
            "signature_verification_context": signature_context,
            "signature_verification_v1": signature_verification,
        }

    def _build(
        self,
        calendar_registration=_DEFAULT,
        calendar_context=_DEFAULT,
        batch_verification=_DEFAULT,
        batch_context=_DEFAULT,
        batch=_DEFAULT,
        expected_calendar_hash=_DEFAULT,
        expected_batch_verification_hash=_DEFAULT,
    ):
        calendar_registration = (
            self.calendar_registration
            if calendar_registration is _DEFAULT
            else calendar_registration
        )
        calendar_context = (
            self.calendar_context
            if calendar_context is _DEFAULT
            else calendar_context
        )
        batch_verification = (
            self.batch_verification
            if batch_verification is _DEFAULT
            else batch_verification
        )
        batch_context = (
            self.batch_context if batch_context is _DEFAULT else batch_context
        )
        batch = self.batch if batch is _DEFAULT else batch
        expected_calendar_hash = (
            calendar_registration["calendar_registration_hash"]
            if expected_calendar_hash is _DEFAULT
            else expected_calendar_hash
        )
        expected_batch_verification_hash = (
            batch_verification["verification_hash"]
            if expected_batch_verification_hash is _DEFAULT
            else expected_batch_verification_hash
        )
        return evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
            calendar_registration,
            calendar_context,
            batch_verification,
            batch_context,
            batch,
            expected_calendar_registration_hash=expected_calendar_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )

    def _verify(self, document, **overrides):
        values = {
            "calendar_registration": self.calendar_registration,
            "calendar_context": self.calendar_context,
            "batch_verification": self.batch_verification,
            "batch_context": self.batch_context,
            "batch": self.batch,
            "expected_calendar_hash": self.calendar_registration[
                "calendar_registration_hash"
            ],
            "expected_batch_verification_hash": self.batch_verification[
                "verification_hash"
            ],
        }
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
            document,
            values["calendar_registration"],
            values["calendar_context"],
            values["batch_verification"],
            values["batch_context"],
            values["batch"],
            expected_calendar_registration_hash=values[
                "expected_calendar_hash"
            ],
            expected_batch_verification_hash=values[
                "expected_batch_verification_hash"
            ],
        )

    def _stock_evidence(self, provider_delta_seconds=1):
        runtime = service_module.calendar_registration_module.exchange_calendars
        calendar = runtime.get_calendar("XNYS")
        sessions = list(
            calendar.sessions_in_range("2026-10-01", "2027-04-30")
        )[:80]
        self.assertEqual(len(sessions), 80)
        rows = deepcopy(self.batch["rows"])
        for row, session in zip(rows, sessions):
            row["observation_date"] = session.date().isoformat()
        batch = self.case._batch(rows=rows)
        last_close = calendar.session_close(sessions[-1]).to_pydatetime().astimezone(
            timezone.utc
        )
        provider_timestamp = (
            last_close + timedelta(seconds=provider_delta_seconds)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt = self.case.case._receipt(
            provider_timestamp_utc=provider_timestamp,
            observation_batch_hash=batch["observation_batch_hash"],
            batch_first_observation_date=batch["first_observation_date"],
            batch_last_observation_date=batch["last_observation_date"],
        )
        signature_verification = self.case.case._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        signature_context = deepcopy(self.case.signature_context)
        signature_context["attestation_receipt"] = receipt
        signature_context["expected_attestation_hash"] = receipt[
            "attestation_hash"
        ]
        batch_verification = self.case._build(
            batch=batch,
            signature_verification=signature_verification,
            signature_context=signature_context,
            expected_signature_hash=signature_verification["verification_hash"],
            expected_batch_hash=batch["observation_batch_hash"],
        )
        identity_calendar_ids = ["XNYS", "XNYS"]
        factor_calendar_id = "XNYS"
        calendar_registration = self._calendar_registration(
            identity_calendar_ids=identity_calendar_ids,
            factor_calendar_id=factor_calendar_id,
        )
        calendar_context = self._calendar_context(
            identity_calendar_ids=identity_calendar_ids,
            factor_calendar_id=factor_calendar_id,
        )
        batch_context = self._batch_context(
            batch=batch,
            signature_verification=signature_verification,
            signature_context=signature_context,
        )
        return {
            "batch": batch,
            "batch_context": batch_context,
            "batch_verification": batch_verification,
            "calendar_context": calendar_context,
            "calendar_registration": calendar_registration,
            "last_close": last_close,
            "provider_timestamp": provider_timestamp,
        }

    def _build_from_stock_evidence(self, evidence):
        return self._build(
            calendar_registration=evidence["calendar_registration"],
            calendar_context=evidence["calendar_context"],
            batch_verification=evidence["batch_verification"],
            batch_context=evidence["batch_context"],
            batch=evidence["batch"],
        )

    def test_twenty_four_seven_sessions_are_verified_but_not_admitted(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(document["calendar_session_verification_state"], POSITIVE_STATE)
        self.assertEqual(document["completed_common_session_count"], 80)
        self.assertEqual(document["distinct_calendar_count"], 1)
        self.assertEqual(document["session_check_count"], 80)
        self.assertTrue(document["facts"]["calendar_sessions_evaluated"])
        self.assertFalse(document["facts"]["observation_admission_allowed"])
        self.assertTrue(self._verify(document))

    def test_eighty_exchange_sessions_are_verified(self):
        evidence = self._stock_evidence()
        document = self._build_from_stock_evidence(evidence)
        self.assertEqual(document["calendar_session_verification_state"], POSITIVE_STATE)
        self.assertEqual(document["completed_common_session_count"], 80)
        self.assertEqual(document["session_check_count"], 80)

    def test_exact_exchange_session_close_is_completed(self):
        evidence = self._stock_evidence(provider_delta_seconds=0)
        document = self._build_from_stock_evidence(evidence)
        self.assertEqual(document["calendar_session_verification_state"], POSITIVE_STATE)
        self.assertEqual(
            document["provider_timestamp_utc"],
            evidence["last_close"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def test_exchange_calendar_rejects_consecutive_weekend_and_holiday_dates(self):
        ids = ["XNYS", "XNYS"]
        calendar = self._calendar_registration(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        context = self._calendar_context(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        document = self._build(
            calendar_registration=calendar,
            calendar_context=context,
        )
        self.assertEqual(
            document["blockers"],
            ["OBSERVATION_DATE_NOT_COMMON_REGISTERED_SESSION"],
        )

    def test_mixed_calendar_requires_the_common_session_intersection(self):
        ids = ["XNYS", "24/7"]
        calendar = self._calendar_registration(
            identity_calendar_ids=ids,
            factor_calendar_id="24/7",
        )
        context = self._calendar_context(
            identity_calendar_ids=ids,
            factor_calendar_id="24/7",
        )
        document = self._build(
            calendar_registration=calendar,
            calendar_context=context,
        )
        self.assertEqual(
            document["blockers"],
            ["OBSERVATION_DATE_NOT_COMMON_REGISTERED_SESSION"],
        )

    def test_factor_calendar_participates_in_the_intersection(self):
        ids = ["24/7", "24/7"]
        calendar = self._calendar_registration(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        context = self._calendar_context(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        document = self._build(
            calendar_registration=calendar,
            calendar_context=context,
        )
        self.assertEqual(
            document["blockers"],
            ["OBSERVATION_DATE_NOT_COMMON_REGISTERED_SESSION"],
        )

    def test_alias_equivalent_calendars_cannot_double_count_sessions(self):
        ids = ["XNYS", "NYSE"]
        calendar = self._calendar_registration(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        context = self._calendar_context(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        self.assertEqual(
            calendar["blockers"],
            ["IDENTITY_CALENDAR_NONCANONICAL"],
        )
        document = self._build(
            calendar_registration=calendar,
            calendar_context=context,
        )
        self.assertEqual(
            document["blockers"],
            ["SOURCE_CALENDAR_REGISTRATION_STATE_NOT_POSITIVE"],
        )
        self.assertIsNone(document["distinct_calendar_count"])
        self.assertIsNone(document["session_check_count"])

    def test_session_close_after_provider_timestamp_is_blocked(self):
        evidence = self._stock_evidence(provider_delta_seconds=-1)
        self.assertEqual(
            evidence["batch_verification"]["verification_state"],
            "BATCH_CONTENT_VERIFIED_SIGNATURE_LIMITED",
        )
        document = self._build_from_stock_evidence(evidence)
        self.assertEqual(
            document["blockers"],
            ["CALENDAR_SESSION_NOT_COMPLETED_AT_PROVIDER_TIMESTAMP"],
        )

    def test_calendar_runtime_lookup_exception_is_fail_closed(self):
        with patch.object(
            service_module.calendar_registration_module.exchange_calendars,
            "get_calendar",
            side_effect=RuntimeError("calendar unavailable"),
        ):
            document = self._build()
        self.assertEqual(document["blockers"], ["CALENDAR_RUNTIME_UNAVAILABLE"])

    def test_loaded_calendar_module_version_drift_is_fail_closed(self):
        with patch.object(
            service_module.calendar_registration_module.exchange_calendars,
            "__version__",
            "4.13.1",
        ):
            document = self._build()
        self.assertEqual(
            document["blockers"],
            ["SOURCE_CALENDAR_REGISTRATION_NOT_VERIFIED"],
        )

    def test_expected_source_hashes_are_bound(self):
        invalid_calendar = self._build(expected_calendar_hash="invalid")
        invalid_batch = self._build(expected_batch_verification_hash="invalid")
        wrong_calendar = self._build(expected_calendar_hash="0" * 64)
        wrong_batch = self._build(expected_batch_verification_hash="0" * 64)
        self.assertEqual(
            invalid_calendar["blockers"],
            ["EXPECTED_CALENDAR_REGISTRATION_HASH_INVALID"],
        )
        self.assertEqual(
            invalid_batch["blockers"],
            ["EXPECTED_BATCH_VERIFICATION_HASH_INVALID"],
        )
        self.assertEqual(
            wrong_calendar["blockers"],
            ["SOURCE_CALENDAR_REGISTRATION_HASH_MISMATCH"],
        )
        self.assertEqual(
            wrong_batch["blockers"],
            ["SOURCE_BATCH_VERIFICATION_HASH_MISMATCH"],
        )

    def test_verification_contexts_require_exact_fields(self):
        calendar_missing = deepcopy(self.calendar_context)
        calendar_missing.pop("declared_at_utc")
        calendar_extra = deepcopy(self.calendar_context)
        calendar_extra["ready"] = True
        batch_missing = deepcopy(self.batch_context)
        batch_missing.pop("expected_batch_hash")
        batch_extra = deepcopy(self.batch_context)
        batch_extra["ready"] = True
        for context in (calendar_missing, calendar_extra):
            document = self._build(calendar_context=context)
            self.assertEqual(
                document["blockers"],
                ["CALENDAR_REGISTRATION_VERIFICATION_CONTEXT_INVALID"],
            )
        for context in (batch_missing, batch_extra):
            document = self._build(batch_context=context)
            self.assertEqual(
                document["blockers"],
                ["BATCH_VERIFICATION_CONTEXT_INVALID"],
            )

    def test_tampered_calendar_registration_is_rejected(self):
        tampered = deepcopy(self.calendar_registration)
        tampered["factor_calendar_id"] = "XNYS"
        document = self._build(calendar_registration=tampered)
        self.assertEqual(
            document["blockers"],
            ["SOURCE_CALENDAR_REGISTRATION_NOT_VERIFIED"],
        )

    def test_tampered_batch_verification_is_rejected(self):
        tampered = deepcopy(self.batch_verification)
        tampered["provider_timestamp_utc"] = "2099-01-01T00:00:00Z"
        document = self._build(batch_verification=tampered)
        self.assertEqual(
            document["blockers"],
            ["SOURCE_BATCH_VERIFICATION_NOT_VERIFIED"],
        )

    def test_private_batch_tamper_is_rejected_by_source_verifier(self):
        tampered = deepcopy(self.batch)
        tampered["rows"][0]["observation_date"] = "2099-01-01"
        document = self._build(batch=tampered)
        self.assertEqual(
            document["blockers"],
            ["SOURCE_BATCH_VERIFICATION_NOT_VERIFIED"],
        )

    def test_independently_valid_but_unrelated_sources_do_not_cross_bind(self):
        other = (
            fold_schedule_source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonFoldSchedulePreregistrationV1Tests(
                methodName="test_positive_source_declares_fixed_schedule_without_observations"
            )
        )
        other.setUp()
        self.addCleanup(other.doCleanups)
        other_declared_at_utc = "2026-09-16T00:00:01Z"
        other_schedule = other._build(declared_at_utc=other_declared_at_utc)
        other_schedule_context = {
            "declared_at_utc": other_declared_at_utc,
            "expected_observation_protocol_hash": other.protocol["protocol_hash"],
            "expected_preregistration_hash": other.preregistration[
                "preregistration_hash"
            ],
            "long_horizon_preregistration_v1": other.preregistration,
            "observation_protocol_v1": other.protocol,
            "source_verification_context": other.context,
        }
        other_calendar = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
            other_schedule,
            other_schedule_context,
            expected_schedule_hash=other_schedule["schedule_hash"],
            identity_calendar_ids=self.identity_calendar_ids,
            factor_calendar_id=self.factor_calendar_id,
            declared_at_utc=self.declared_at_utc,
        )
        other_context = self._calendar_context(
            schedule=other_schedule,
            schedule_context=other_schedule_context,
        )
        document = self._build(
            calendar_registration=other_calendar,
            calendar_context=other_context,
        )
        self.assertEqual(document["blockers"], ["SOURCE_CROSS_BINDING_INVALID"])

    def test_evaluation_hash_binds_sources_rules_counts_and_provider_time(self):
        document = self._build()
        binding = {
            "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
            "calendar_library_version": CALENDAR_LIBRARY_VERSION,
            "calendar_session_protocol_id": CALENDAR_SESSION_PROTOCOL_ID,
            "common_date_rule": COMMON_DATE_RULE,
            "completed_common_session_count": 80,
            "distinct_calendar_count": 1,
            "first_observation_date": self.batch_verification[
                "first_observation_date"
            ],
            "identity_calendar_assignment_hash": self.calendar_registration[
                "identity_calendar_assignment_hash"
            ],
            "last_observation_date": self.batch_verification[
                "last_observation_date"
            ],
            "observation_batch_hash": self.batch_verification[
                "observation_batch_hash"
            ],
            "provider_timestamp_utc": self.batch_verification[
                "provider_timestamp_utc"
            ],
            "row_count": 80,
            "session_check_count": 80,
            "session_completion_policy": SESSION_COMPLETION_POLICY,
            "session_label_policy": SESSION_LABEL_POLICY,
            "source_batch_verification_hash": self.batch_verification[
                "verification_hash"
            ],
            "source_calendar_registration_hash": self.calendar_registration[
                "calendar_registration_hash"
            ],
            "source_schedule_hash": self.calendar_registration[
                "source_schedule_hash"
            ],
        }
        self.assertEqual(
            document["calendar_session_evaluation_hash"],
            strict_canonical_hash(binding),
        )

    def test_public_document_contains_no_private_rows_or_session_details(self):
        document = self._build()
        forbidden = {
            "factor_return",
            "observation_id",
            "returns",
            "rows",
            "session_closes",
            "session_dates",
            "session_labels",
            "sessions",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))

    def test_source_hashes_and_aggregate_counts_are_exposed(self):
        document = self._build()
        self.assertEqual(
            document["source_calendar_registration_hash"],
            self.calendar_registration["calendar_registration_hash"],
        )
        self.assertEqual(
            document["source_batch_verification_hash"],
            self.batch_verification["verification_hash"],
        )
        self.assertEqual(
            document["identity_calendar_assignment_hash"],
            self.calendar_registration["identity_calendar_assignment_hash"],
        )
        self.assertEqual(document["row_count"], 80)

    def test_remaining_provenance_time_replay_and_admission_gaps_stay_locked(self):
        document = self._build()
        self.assertEqual(
            document["blockers"],
            [
                "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
                "CALENDAR_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
                "REPLAY_REGISTRY_NOT_CHECKED",
                "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
                "OBSERVATION_ADMISSION_NOT_ACTIVATED",
            ],
        )
        self.assertFalse(document["facts"]["external_provider_identity_verified"])
        self.assertFalse(
            document["facts"]["external_calendar_registration_time_verified"]
        )
        self.assertFalse(document["facts"]["replay_registry_checked"])
        self.assertFalse(document["facts"]["result_available"])

    def test_authority_is_permanently_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["verification_hash"], second["verification_hash"])

    def test_verifier_rejects_tamper_extra_keys_and_non_objects(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["completed_common_session_count"] = 79
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            document["calendar_session_protocol_id"],
            CALENDAR_SESSION_PROTOCOL_ID,
        )
        self.assertEqual(document["common_date_rule"], COMMON_DATE_RULE)
        self.assertEqual(
            document["session_completion_policy"], SESSION_COMPLETION_POLICY
        )
        self.assertEqual(document["session_label_policy"], SESSION_LABEL_POLICY)

    def test_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(
            set(document),
            {
                "authority",
                "blockers",
                "calendar_library_distribution",
                "calendar_library_version",
                "calendar_session_evaluation_hash",
                "calendar_session_protocol_id",
                "calendar_session_verification_state",
                "common_date_rule",
                "completed_common_session_count",
                "distinct_calendar_count",
                "evaluation_not_before_date",
                "factor_id",
                "factor_source_hash",
                "facts",
                "first_observation_date",
                "future_evaluation_id",
                "identity_calendar_assignment_hash",
                "identity_count",
                "identity_order_hash",
                "last_observation_date",
                "observation_batch_hash",
                "provider_id",
                "provider_timestamp_utc",
                "row_count",
                "schema_version",
                "session_check_count",
                "session_completion_policy",
                "session_label_policy",
                "source_batch_verification_hash",
                "source_batch_verification_schema",
                "source_calendar_registration_hash",
                "source_calendar_registration_schema",
                "source_schedule_hash",
                "source_state",
                "static_fingerprint",
                "verification_hash",
                "verification_reason",
            },
        )


if __name__ == "__main__":
    unittest.main()
