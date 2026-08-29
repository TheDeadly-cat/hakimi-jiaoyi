import unittest
from copy import deepcopy
from decimal import getcontext, setcontext

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1 import (
    PRESENTATION_STATUS,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as source_tests,
)


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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionPresentationEnvelopeV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        Case = source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionVerifierV1Tests
        self.case = Case(
            methodName="test_twenty_four_seven_sessions_are_verified_but_not_admitted"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.source = self.case._build()

    def _values(self):
        return {
            "session_verification_v1": self.source,
            "calendar_registration_v1": self.case.calendar_registration,
            "calendar_registration_verification_context": self.case.calendar_context,
            "batch_verification_v1": self.case.batch_verification,
            "batch_verification_context": self.case.batch_context,
            "observation_batch": self.case.batch,
        }

    def _expected(self, values):
        source = values.get("session_verification_v1")
        if type(source) is not dict or type(source.get("verification_hash")) is not str:
            source = self.source
        return {
            "expected_session_verification_hash": source["verification_hash"],
            "expected_calendar_registration_hash": values[
                "calendar_registration_v1"
            ]["calendar_registration_hash"],
            "expected_batch_verification_hash": values["batch_verification_v1"][
                "verification_hash"
            ],
        }

    def _build(self, **overrides):
        values = self._values()
        values.update(
            {key: value for key, value in overrides.items() if not key.startswith("expected_")}
        )
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1(
            **values,
            **expected,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(
            {key: value for key, value in overrides.items() if not key.startswith("expected_")}
        )
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1(
            document,
            **values,
            **expected,
        )

    def _block_context(self):
        ids = ["XNYS", "XNYS"]
        calendar = self.case._calendar_registration(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        calendar_context = self.case._calendar_context(
            identity_calendar_ids=ids,
            factor_calendar_id="XNYS",
        )
        source = self.case._build(
            calendar_registration=calendar,
            calendar_context=calendar_context,
        )
        return {
            "session_verification_v1": source,
            "calendar_registration_v1": calendar,
            "calendar_registration_verification_context": calendar_context,
        }

    def test_positive_source_maps_to_local_session_bound_four_axis(self):
        result = self._build()
        self.assertEqual(result["display_state"], "LOCAL_SESSION_BOUND")
        self.assertEqual(
            [
                result["source_axis"]["label"],
                result["gap_axis"]["label"],
                result["maturity_axis"]["label"],
                result["permission_axis"]["label"],
            ],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(self._verify(result))

    def test_valid_negative_source_maps_to_evidence_block(self):
        context = self._block_context()
        result = self._build(**context)
        self.assertEqual(result["display_state"], "EVIDENCE_BLOCK")
        self.assertEqual(result["source_axis"]["state"], "VERIFIED_BLOCK")
        self.assertEqual(result["maturity_axis"]["state"], "EVIDENCE_BLOCK")
        self.assertEqual(result["permission_axis"]["state"], "LOCKED")
        self.assertTrue(self._verify(result, **context))

    def test_missing_and_unsupported_sources_are_distinct_unknowns(self):
        missing = self._build(session_verification_v1=None)
        unsupported = self._build(session_verification_v1={"schema_version": "legacy"})
        self.assertEqual(missing["display_reason"], "MISSING_SESSION_VERIFICATION")
        self.assertEqual(unsupported["source_state"], "UNSUPPORTED")

    def test_expected_source_hash_is_bound(self):
        result = self._build(expected_session_verification_hash="0" * 64)
        self.assertEqual(
            result["display_reason"],
            "EXPECTED_SESSION_VERIFICATION_HASH_MISMATCH",
        )

    def test_expected_upstream_hashes_are_bound(self):
        calendar = self._build(expected_calendar_registration_hash="0" * 64)
        batch = self._build(expected_batch_verification_hash="0" * 64)
        self.assertEqual(
            calendar["display_reason"],
            "SESSION_VERIFICATION_OR_CONTEXT_INVALID",
        )
        self.assertEqual(
            batch["display_reason"],
            "SESSION_VERIFICATION_OR_CONTEXT_INVALID",
        )

    def test_resealed_source_tamper_is_rejected(self):
        source = deepcopy(self.source)
        source.pop("verification_hash")
        source["verification_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "verification_hash")
        result = self._build(
            session_verification_v1=source,
            expected_session_verification_hash=source["verification_hash"],
        )
        self.assertEqual(
            result["display_reason"],
            "SESSION_VERIFICATION_OR_CONTEXT_INVALID",
        )

    def test_maturity_exposes_only_aggregate_session_counts(self):
        result = self._build()
        maturity = result["maturity_axis"]
        self.assertEqual(maturity["row_count"], 80)
        self.assertEqual(maturity["completed_common_session_count"], 80)
        self.assertEqual(maturity["distinct_calendar_count"], 1)
        self.assertEqual(maturity["session_check_count"], 80)
        self.assertFalse(maturity["batch_admitted"])

    def test_timetable_is_ordered_and_admission_remains_locked(self):
        result = self._build()
        self.assertEqual(
            [stop["code"] for stop in result["timetable"]["stops"]],
            ["CAL", "LBL", "CLS", "ADM"],
        )
        self.assertEqual(
            [stop["state"] for stop in result["timetable"]["stops"]],
            ["BOUND", "BOUND", "PROVIDER_TIME_BOUND", "LOCKED"],
        )
        self.assertTrue(
            all(not stop["result_exposed"] for stop in result["timetable"]["stops"])
        )

    def test_gap_axis_cannot_claim_external_identity_time_or_replay(self):
        gap = self._build()["gap_axis"]
        self.assertEqual(gap["state"], "OPEN")
        self.assertTrue(gap["provider_identity_unresolved"])
        self.assertTrue(gap["external_timing_unresolved"])
        self.assertTrue(gap["replay_registry_unresolved"])

    def test_source_hashes_are_cross_bound(self):
        result = self._build()
        self.assertEqual(
            result["source_axis"]["verification_hash"],
            result["source_session_verification_hash"],
        )
        self.assertEqual(
            result["source_axis"]["calendar_registration_hash"],
            result["source_calendar_registration_hash"],
        )
        self.assertEqual(
            result["source_axis"]["batch_verification_hash"],
            result["source_batch_verification_hash"],
        )

    def test_public_envelope_contains_no_private_rows_sessions_or_returns(self):
        forbidden = {
            "factor_return",
            "observation_id",
            "returns",
            "rows",
            "session_closes",
            "session_dates",
            "session_labels",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(self._build())))

    def test_authority_and_permission_are_permanently_locked(self):
        result = self._build()
        self.assertTrue(result["authority"]["descriptive_only"])
        for key, value in result["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key, value in result["permission_axis"].items():
            if key not in {"label", "state"}:
                self.assertFalse(value, key)

    def test_presentation_status_is_unmounted(self):
        result = self._build()
        self.assertEqual(result["presentation_status"], PRESENTATION_STATUS)
        self.assertFalse(result["authority"]["presentation_mount_allowed"])

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["presentation_hash"], second["presentation_hash"])

    def test_verifier_rejects_tamper_extra_keys_and_non_objects(self):
        result = self._build()
        tampered = deepcopy(result)
        tampered["maturity_axis"]["batch_admitted"] = True
        extra = deepcopy(result)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_is_exact(self):
        result = self._build()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["presentation_status"], "UNMOUNTED_CANDIDATE")

    def test_schema_keys_are_exact(self):
        result = self._build()
        self.assertEqual(
            set(result),
            {
                "authority",
                "blocker_count",
                "display_reason",
                "display_state",
                "facts",
                "gap_axis",
                "maturity_axis",
                "permission_axis",
                "presentation_hash",
                "presentation_status",
                "schema_version",
                "source_axis",
                "source_batch_verification_hash",
                "source_calendar_registration_hash",
                "source_observation_batch_hash",
                "source_schedule_hash",
                "source_session_verification_hash",
                "source_state",
                "static_fingerprint",
                "timetable",
            },
        )


if __name__ == "__main__":
    unittest.main()
