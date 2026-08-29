from __future__ import annotations

import unittest
from copy import deepcopy

from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1 import (
    CANDIDATE_STATE,
    PREREQUISITE_POLICY_ID,
    REQUIRED_BLOCKERS,
    REQUIRED_EVIDENCE_KINDS,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as calendar_session_source_tests,
)


_UNSET = object()


def _all_keys(value):
    if type(value) is dict:
        found = set(value)
        for item in value.values():
            found.update(_all_keys(item))
        return found
    if type(value) is list:
        found = set()
        for item in value:
            found.update(_all_keys(item))
        return found
    return set()


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarBoundObservationAdmissionGateV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.source_case = calendar_session_source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionVerifierV1Tests(
            methodName="test_twenty_four_seven_sessions_are_verified_but_not_admitted"
        )
        self.source_case.setUp()
        self.addCleanup(self.source_case.doCleanups)
        self.source = self.source_case._build()
        self.context = {
            "batch_verification_context": self.source_case.batch_context,
            "batch_verification_v1": self.source_case.batch_verification,
            "calendar_registration_v1": self.source_case.calendar_registration,
            "calendar_registration_verification_context": self.source_case.calendar_context,
            "expected_batch_verification_hash": self.source_case.batch_verification[
                "verification_hash"
            ],
            "expected_calendar_registration_hash": self.source_case.calendar_registration[
                "calendar_registration_hash"
            ],
            "observation_batch": self.source_case.batch,
        }

    def _build(self, *, source=None, context=_UNSET, expected_hash=None):
        source = self.source if source is None else source
        return evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1(
            source,
            self.context if context is _UNSET else context,
            expected_calendar_session_verification_hash=(
                source.get("verification_hash")
                if expected_hash is None and type(source) is dict
                else expected_hash
            ),
        )

    def _verify(self, document):
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1(
            document,
            self.source,
            self.context,
            expected_calendar_session_verification_hash=self.source[
                "verification_hash"
            ],
        )

    def test_verified_session_maps_to_closed_admission_candidate(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(document["admission_decision_state"], CANDIDATE_STATE)
        self.assertEqual(document["blockers"], list(REQUIRED_BLOCKERS))
        self.assertEqual(
            document["required_evidence_kinds"], list(REQUIRED_EVIDENCE_KINDS)
        )
        self.assertEqual(document["evidence_requirement_count"], 5)
        self.assertTrue(document["facts"]["admission_policy_bound"])
        self.assertFalse(document["facts"]["observation_admitted"])
        self.assertTrue(self._verify(document))

    def test_policy_hash_binds_source_lineage_and_ordered_requirements(self):
        document = self._build()
        binding = {
            "calendar_session_evaluation_hash": self.source[
                "calendar_session_evaluation_hash"
            ],
            "future_evaluation_id": self.source["future_evaluation_id"],
            "identity_calendar_assignment_hash": self.source[
                "identity_calendar_assignment_hash"
            ],
            "observation_batch_hash": self.source["observation_batch_hash"],
            "prerequisite_policy_id": PREREQUISITE_POLICY_ID,
            "required_evidence_kinds": list(REQUIRED_EVIDENCE_KINDS),
            "source_batch_verification_hash": self.source[
                "source_batch_verification_hash"
            ],
            "source_calendar_registration_hash": self.source[
                "source_calendar_registration_hash"
            ],
            "source_calendar_session_verification_hash": self.source[
                "verification_hash"
            ],
            "source_schedule_hash": self.source["source_schedule_hash"],
        }
        self.assertEqual(document["admission_policy_hash"], strict_canonical_hash(binding))

    def test_expected_source_hash_is_fail_closed(self):
        invalid = self._build(expected_hash="invalid")
        mismatch = self._build(expected_hash="0" * 64)
        self.assertEqual(
            invalid["blockers"], ["EXPECTED_SESSION_VERIFICATION_HASH_INVALID"]
        )
        self.assertEqual(
            mismatch["blockers"], ["SOURCE_SESSION_VERIFICATION_HASH_MISMATCH"]
        )

    def test_context_requires_exact_fields(self):
        missing = deepcopy(self.context)
        missing.pop("observation_batch")
        extra = deepcopy(self.context)
        extra["ready"] = True
        for context in (missing, extra, None):
            document = self._build(context=context)
            self.assertEqual(
                document["blockers"], ["SESSION_VERIFICATION_CONTEXT_INVALID"]
            )

    def test_tampered_source_is_reverified_not_merely_resealed(self):
        tampered = deepcopy(self.source)
        tampered["completed_common_session_count"] = 79
        document = self._build(source=tampered, expected_hash=self.source["verification_hash"])
        self.assertEqual(
            document["blockers"], ["SOURCE_SESSION_VERIFICATION_NOT_VERIFIED"]
        )

    def test_private_batch_tamper_is_rejected_through_the_source_chain(self):
        context = deepcopy(self.context)
        context["observation_batch"]["rows"][0]["observation_date"] = "2099-01-01"
        document = self._build(context=context)
        self.assertEqual(
            document["blockers"], ["SOURCE_SESSION_VERIFICATION_NOT_VERIFIED"]
        )

    def test_cross_binding_hash_drift_is_rejected(self):
        context = deepcopy(self.context)
        context["expected_batch_verification_hash"] = "0" * 64
        document = self._build(context=context)
        self.assertEqual(
            document["blockers"], ["SOURCE_SESSION_VERIFICATION_NOT_VERIFIED"]
        )

    def test_source_admission_gap_order_is_contractual(self):
        tampered = deepcopy(self.source)
        tampered["blockers"] = list(reversed(tampered["blockers"]))
        document = self._build(source=tampered, expected_hash=self.source["verification_hash"])
        self.assertEqual(
            document["blockers"], ["SOURCE_SESSION_VERIFICATION_NOT_VERIFIED"]
        )

    def test_output_contains_no_private_rows_receipts_or_signatures(self):
        forbidden = {
            "attestation_receipt",
            "private_observation_ledger_hash",
            "public_key",
            "returns",
            "rows",
            "session_closes",
            "signature",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(self._build())))

    def test_all_external_and_trading_authority_stays_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key in (
            "admission_receipt_verified",
            "calendar_registration_time_attestation_verified",
            "evaluation_activation_receipt_verified",
            "external_provider_identity_attestation_verified",
            "observation_admitted",
            "replay_registry_receipt_verified",
            "result_available",
        ):
            self.assertFalse(document["facts"][key], key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["admission_gate_hash"], second["admission_gate_hash"])

    def test_verifier_rejects_tamper_extra_fields_and_non_objects(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["evidence_requirement_count"] = 4
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_and_source_lineage_are_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            document["source_calendar_session_verification_hash"],
            self.source["verification_hash"],
        )
        self.assertEqual(
            document["source_calendar_session_verification_schema"],
            self.source["schema_version"],
        )

    def test_schema_keys_are_exact(self):
        self.assertEqual(
            set(self._build()),
            {
                "admission_decision_state",
                "admission_gate_hash",
                "admission_policy_hash",
                "authority",
                "blockers",
                "calendar_session_evaluation_hash",
                "evidence_requirement_count",
                "factor_id",
                "factor_source_hash",
                "facts",
                "future_evaluation_id",
                "identity_calendar_assignment_hash",
                "identity_count",
                "identity_order_hash",
                "observation_batch_hash",
                "prerequisite_policy_id",
                "provider_id",
                "provider_timestamp_utc",
                "required_evidence_kinds",
                "row_count",
                "schema_version",
                "session_check_count",
                "source_batch_verification_hash",
                "source_calendar_registration_hash",
                "source_calendar_session_verification_hash",
                "source_calendar_session_verification_schema",
                "source_schedule_hash",
                "source_state",
                "static_fingerprint",
                "verification_reason",
            },
        )


if __name__ == "__main__":
    unittest.main()
