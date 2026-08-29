from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_presentation_envelope import (
    ENVELOPE_SCHEMA,
    PRESENTATION_STATUS,
    REPORT_SCHEMA,
    REPORT_STATIC_FINGERPRINT,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_presentation_envelope,
    verify_strategy_correlation_cross_lag_factor_calibration_presentation_envelope,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_report_consumer as g1_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPresentationEnvelopeTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = g1_fixtures.StrategyCorrelationCrossLagFactorCalibrationReportConsumerTests(
            methodName="test_match_source_is_observed_without_attestation"
        )
        case.setUp()
        self.case = case
        self.registration = case.registration
        self.observations = case.observations
        self.replay = case.replay
        self.report = case._consume()

    def _build(
        self,
        report=...,
        *,
        replay=...,
        registration=None,
        observations=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
        expected_replay_hash=None,
        expected_report_hash=None,
    ):
        report = self.report if report is ... else report
        replay = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        if expected_replay_hash is None:
            expected_replay_hash = "" if replay is None else replay["receipt_hash"]
        if expected_report_hash is None:
            expected_report_hash = (
                "" if report is None else report["verification_hash"]
            )
        return build_strategy_correlation_cross_lag_factor_calibration_presentation_envelope(
            report,
            replay,
            registration,
            observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
            expected_replay_hash=expected_replay_hash,
            expected_report_hash=expected_report_hash,
        )

    def _verify(self, envelope, report=..., **overrides):
        report = self.report if report is ... else report
        replay = overrides.pop("replay", self.replay)
        registration = overrides.pop("registration", self.registration)
        observations = overrides.pop("observations", self.observations)
        expected_registration_hash = overrides.pop(
            "expected_registration_hash", registration["registration_hash"]
        )
        expected_observations_hash = overrides.pop(
            "expected_observations_hash",
            observations["calibration_observations_hash"],
        )
        expected_replay_hash = overrides.pop(
            "expected_replay_hash", "" if replay is None else replay["receipt_hash"]
        )
        if "expected_report_hash" in overrides:
            expected_report_hash = overrides.pop("expected_report_hash")
        else:
            expected_report_hash = (
                "" if report is None else report["verification_hash"]
            )
        self.assertFalse(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_presentation_envelope(
            envelope,
            report,
            replay,
            registration,
            observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
            expected_replay_hash=expected_replay_hash,
            expected_report_hash=expected_report_hash,
        )

    def test_verified_match_report_is_carried_exactly(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "OBSERVED")
        self.assertEqual(envelope["report"], self.report)
        self.assertIsNot(envelope["report"], self.report)
        self.assertTrue(self._verify(envelope))

    def test_verified_block_report_remains_blocked(self) -> None:
        registration, replay = self.case._block_source()
        report = self.case._consume(replay, registration=registration)
        envelope = self._build(report, replay=replay, registration=registration)
        self.assertEqual(
            envelope["report"]["report_state"], "OBSERVED_CALIBRATION_BLOCK"
        )
        self.assertTrue(
            self._verify(
                envelope, report, replay=replay, registration=registration
            )
        )

    def test_verified_g1_unknown_remains_distinct(self) -> None:
        report = self.case._consume(None)
        envelope = self._build(report, replay=None)
        self.assertEqual(envelope["verification_state"], "VERIFIED")
        self.assertEqual(envelope["source_state"], "MISSING")
        self.assertEqual(envelope["report"]["report_state"], "UNKNOWN")
        self.assertTrue(self._verify(envelope, report, replay=None))

    def test_missing_report_is_not_supplied(self) -> None:
        envelope = self._build(None)
        self.assertEqual(envelope["source_state"], "NOT_SUPPLIED")
        self.assertEqual(envelope["verification_state"], "UNKNOWN")
        self.assertIsNone(envelope["report"])
        self.assertTrue(self._verify(envelope, None))

    def test_old_report_contract_is_unsupported(self) -> None:
        report = {"schema_version": "candidate-v0", "static_fingerprint": "v0"}
        envelope = self._build(report, expected_report_hash="a" * 64)
        self.assertEqual(envelope["source_state"], "UNSUPPORTED")
        self.assertTrue(
            self._verify(envelope, report, expected_report_hash="a" * 64)
        )

    def test_wrong_expected_report_hash_is_invalid(self) -> None:
        envelope = self._build(expected_report_hash="0" * 64)
        self.assertEqual(envelope["source_state"], "INVALID")

    def test_coherent_report_reseal_is_invalid(self) -> None:
        report = deepcopy(self.report)
        report["gap_state"] = "CALIBRATION_REPLAY_MISMATCH"
        report = seal_strict_canonical_document(report, "verification_hash")
        envelope = self._build(report)
        self.assertEqual(envelope["source_state"], "INVALID")
        self.assertTrue(self._verify(envelope, report))

    def test_source_context_substitution_is_invalid(self) -> None:
        observations = self.case.fixture._observations(count=39)
        envelope = self._build(observations=observations)
        self.assertEqual(envelope["source_state"], "INVALID")

        registration = self.case.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        envelope = self._build(registration=registration)
        self.assertEqual(envelope["source_state"], "INVALID")

    def test_contract_and_provenance_are_exact(self) -> None:
        envelope = self._build()
        self.assertEqual(
            ENVELOPE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-presentation-envelope-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260823-cross-lag-factor-calibration-presentation-envelope-1",
        )
        self.assertEqual(envelope["presentation_status"], PRESENTATION_STATUS)
        self.assertEqual(envelope["source_schema_version"], REPORT_SCHEMA)
        self.assertEqual(
            envelope["source_static_fingerprint"], REPORT_STATIC_FINGERPRINT
        )
        self.assertEqual(
            envelope["source_report_hash"], self.report["verification_hash"]
        )

    def test_projection_remains_aggregate_only(self) -> None:
        envelope = self._build()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(envelope)
        self.assertTrue(
            {
                "rows",
                "identity_order",
                "beta_by_identity",
                "factor_id",
                "factor_source_hash",
                "returns_by_identity",
                "factor_return",
            }.isdisjoint(keys)
        )
        self.assertNotIn("COMMON-FACTOR-1", json.dumps(envelope, sort_keys=True))

    def test_authority_is_locked_and_detached(self) -> None:
        for envelope in (self._build(), self._build(None)):
            authority = envelope["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["presentation_mounted"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_resealed_envelope_tamper_is_rejected(self) -> None:
        envelope = self._build()
        for field, value in (
            ("presentation_status", "MOUNTED"),
            ("verification_state", "UNKNOWN"),
            ("source_state", "INVALID"),
        ):
            tampered = deepcopy(envelope)
            tampered[field] = value
            tampered = seal_strict_canonical_document(tampered, "envelope_hash")
            self.assertFalse(self._verify(tampered))

    def test_non_native_and_nonfinite_reports_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        envelope = self._build(DictSubclass(self.report))
        self.assertEqual(envelope["source_state"], "INVALID")

        report = deepcopy(self.report)
        report["calibration_summary"]["max_abs_beta_error"] = float("nan")
        envelope = self._build(
            report, expected_report_hash=self.report["verification_hash"]
        )
        self.assertEqual(envelope["source_state"], "INVALID")

    def test_closed_envelopes_are_deterministic(self) -> None:
        self.assertEqual(self._build(None), self._build(None))
        invalid_a = self._build(expected_report_hash="0" * 64)
        invalid_b = self._build(expected_report_hash="0" * 64)
        self.assertEqual(invalid_a, invalid_b)

    def test_denied_external_state_is_unused(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("pathlib.Path.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            envelope = self._build()
        self.assertTrue(self._verify(envelope))


if __name__ == "__main__":
    unittest.main()
