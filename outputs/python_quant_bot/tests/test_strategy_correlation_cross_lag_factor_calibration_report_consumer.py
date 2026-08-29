from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_replay import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_replay,
    verify_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    INVALID_REASON,
    MISSING_REASON,
    REPORT_BLOCKER,
    SOURCE_SCHEMA,
    SOURCE_STATIC_FINGERPRINT,
    STATIC_FINGERPRINT,
    UNSUPPORTED_REASON,
    VERIFICATION_SCHEMA,
    consume_strategy_correlation_cross_lag_factor_calibration_replay,
    verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_replay as g0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationReportConsumerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        fixture = g0_fixtures.StrategyCorrelationCrossLagFactorCalibrationReplayTests(
            methodName="test_exact_ols_match_is_observed"
        )
        self.fixture = fixture
        self.registration = fixture._registration()
        self.observations = fixture._observations()
        self.replay = self._build_replay(self.registration, self.observations)
        self.assertTrue(
            verify_strategy_correlation_cross_lag_factor_calibration_replay(
                self.replay,
                self.registration,
                self.observations,
                expected_registration_hash=self.registration["registration_hash"],
                expected_calibration_observations_hash=self.observations[
                    "calibration_observations_hash"
                ],
            )
        )

    @staticmethod
    def _build_replay(registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_replay(
            registration,
            observations,
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _consume(
        self,
        replay=...,
        *,
        registration=None,
        observations=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
        expected_replay_hash=None,
    ):
        source = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        if expected_replay_hash is None:
            expected_replay_hash = "" if source is None else source["receipt_hash"]
        return consume_strategy_correlation_cross_lag_factor_calibration_replay(
            source,
            residualization_registration=registration,
            calibration_observations=observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
            expected_replay_hash=expected_replay_hash,
        )

    def _verify(
        self,
        receipt,
        replay=...,
        *,
        registration=None,
        observations=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
        expected_replay_hash=None,
    ):
        source = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        if expected_replay_hash is None:
            expected_replay_hash = "" if source is None else source["receipt_hash"]
        return verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt(
            receipt,
            source,
            residualization_registration=registration,
            calibration_observations=observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
            expected_replay_hash=expected_replay_hash,
        )

    def _block_source(self):
        registration = self.fixture._registration(betas={"A": "0.5", "B": "0.5"})
        replay = self._build_replay(registration, self.observations)
        self.assertEqual(replay["replay_decision"], "BLOCK")
        return registration, replay

    def test_match_source_is_observed_without_attestation(self) -> None:
        receipt = self._consume()
        self.assertEqual(receipt["source_state"], "OBSERVED")
        self.assertEqual(receipt["report_state"], "OBSERVED_CALIBRATION_MATCH")
        self.assertEqual(receipt["diagnostic_state"], "CALIBRATION_REPLAY_MATCH")
        self.assertEqual(
            receipt["gap_state"],
            "MATHEMATICAL_REPLAY_MATCHED_TIMING_UNATTESTED",
        )
        self.assertTrue(self._verify(receipt))

    def test_block_source_remains_observed_block(self) -> None:
        registration, replay = self._block_source()
        receipt = self._consume(replay, registration=registration)
        self.assertEqual(receipt["source_state"], "OBSERVED")
        self.assertEqual(receipt["report_state"], "OBSERVED_CALIBRATION_BLOCK")
        self.assertEqual(receipt["diagnostic_state"], "CALIBRATION_REPLAY_BLOCK")
        self.assertEqual(receipt["gap_state"], "CALIBRATION_REPLAY_MISMATCH")
        self.assertTrue(self._verify(receipt, replay, registration=registration))

    def test_missing_source_has_fixed_unknown_closure(self) -> None:
        receipt = self._consume(None)
        self.assertEqual(receipt["source_state"], "MISSING")
        self.assertEqual(receipt["report_state"], "UNKNOWN")
        self.assertEqual(receipt["blockers"], [MISSING_REASON])
        self.assertIsNone(receipt["calibration_summary"])
        self.assertTrue(self._verify(receipt, None))

    def test_unsupported_source_has_fixed_unknown_closure(self) -> None:
        source = {
            "schema_version": "strategy-correlation-cross-lag-factor-calibration-replay-candidate-v0",
            "static_fingerprint": "20260823-cross-lag-factor-calibration-replay-0",
        }
        receipt = self._consume(source, expected_replay_hash="a" * 64)
        self.assertEqual(receipt["source_state"], "UNSUPPORTED")
        self.assertEqual(receipt["blockers"], [UNSUPPORTED_REASON])
        self.assertTrue(
            self._verify(receipt, source, expected_replay_hash="a" * 64)
        )

    def test_expected_replay_hash_is_exactly_bound(self) -> None:
        receipt = self._consume(expected_replay_hash="0" * 64)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertEqual(receipt["blockers"], [INVALID_REASON])
        missing_with_hash = self._consume(None, expected_replay_hash="0" * 64)
        self.assertEqual(missing_with_hash["source_state"], "INVALID")

    def test_broken_source_hash_is_invalid(self) -> None:
        source = deepcopy(self.replay)
        source["receipt_hash"] = "0" * 64
        receipt = self._consume(source, expected_replay_hash="0" * 64)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertTrue(
            self._verify(receipt, source, expected_replay_hash="0" * 64)
        )

    def test_resealed_source_metric_tamper_is_invalid(self) -> None:
        source = deepcopy(self.replay)
        source["max_abs_beta_error"] = "0.1"
        source = seal_strict_canonical_document(source, "receipt_hash")
        receipt = self._consume(source)
        self.assertEqual(receipt["source_state"], "INVALID")
        self.assertTrue(self._verify(receipt, source))

    def test_expected_registration_hash_is_bound(self) -> None:
        receipt = self._consume(expected_registration_hash="0" * 64)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_expected_calibration_observations_hash_is_bound(self) -> None:
        receipt = self._consume(expected_observations_hash="0" * 64)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_registration_substitution_is_invalid(self) -> None:
        other = self.fixture._registration(betas={"A": "0.5", "B": "0.5"})
        receipt = self._consume(self.replay, registration=other)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_calibration_observation_substitution_is_invalid(self) -> None:
        other = self.fixture._observations(count=39)
        receipt = self._consume(self.replay, observations=other)
        self.assertEqual(receipt["source_state"], "INVALID")

    def test_observed_projection_is_aggregate_only(self) -> None:
        receipt = self._consume()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(receipt)
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
        self.assertNotIn("COMMON-FACTOR-1", json.dumps(receipt, sort_keys=True))

    def test_match_preserves_all_source_blockers_and_adds_report_blocker(self) -> None:
        receipt = self._consume()
        self.assertEqual(receipt["blockers"], [*self.replay["blockers"], REPORT_BLOCKER])
        self.assertIn("EXTERNAL_CALIBRATION_TIMING_UNATTESTED", receipt["blockers"])
        self.assertIn(
            "REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND", receipt["blockers"]
        )

    def test_match_facts_never_upgrade_timing_or_registration_binding(self) -> None:
        receipt = self._consume()
        self.assertTrue(receipt["facts"]["source_replay_verified"])
        self.assertTrue(receipt["facts"]["beta_replay_matches_registration"])
        self.assertFalse(
            receipt["facts"]["external_calibration_timing_attested"]
        )
        self.assertFalse(
            receipt["facts"]["registration_calibration_receipt_g0_bound"]
        )

    def test_block_is_monotone_and_cannot_be_presented_as_match(self) -> None:
        registration, replay = self._block_source()
        receipt = self._consume(replay, registration=registration)
        self.assertFalse(receipt["facts"]["beta_replay_matches_registration"])
        self.assertIn("REGISTERED_BETA_REPLAY_MISMATCH", receipt["blockers"])
        self.assertNotEqual(receipt["report_state"], "OBSERVED_CALIBRATION_MATCH")

    def test_authority_is_permanently_locked(self) -> None:
        for receipt in (self._consume(), self._consume(None)):
            authority = receipt["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(authority["report_consumer_activated"])
            self.assertFalse(authority["report_mounted"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_sources_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        subclass_receipt = self._consume(DictSubclass(self.replay))
        self.assertEqual(subclass_receipt["source_state"], "INVALID")

        source = deepcopy(self.replay)
        source["max_abs_beta_error"] = float("nan")
        nonfinite_receipt = self._consume(
            source, expected_replay_hash=self.replay["receipt_hash"]
        )
        self.assertEqual(nonfinite_receipt["source_state"], "INVALID")

        source = deepcopy(self.replay)
        source["authority"]["descriptive_only"] = 1
        source = seal_strict_canonical_document(source, "receipt_hash")
        alias_receipt = self._consume(source)
        self.assertEqual(alias_receipt["source_state"], "INVALID")

    def test_resealed_consumer_receipt_tamper_is_rejected(self) -> None:
        receipt = self._consume()
        for field, value in (
            ("report_state", "OBSERVED_CALIBRATION_BLOCK"),
            ("permission_state", "READY"),
        ):
            tampered = deepcopy(receipt)
            tampered[field] = value
            tampered = seal_strict_canonical_document(tampered, "verification_hash")
            self.assertFalse(self._verify(tampered))

        tampered = deepcopy(receipt)
        tampered["blockers"] = list(reversed(tampered["blockers"]))
        tampered = seal_strict_canonical_document(tampered, "verification_hash")
        self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("pathlib.Path.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._consume()
            second = self._consume()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_fingerprint_and_source_bindings_are_exact(self) -> None:
        receipt = self._consume()
        self.assertEqual(
            VERIFICATION_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-report-consumer-verification-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260823-cross-lag-factor-calibration-report-consumer-1",
        )
        self.assertEqual(receipt["source_schema_version"], SOURCE_SCHEMA)
        self.assertEqual(
            receipt["source_static_fingerprint"], SOURCE_STATIC_FINGERPRINT
        )
        self.assertEqual(receipt["source_replay_hash"], self.replay["receipt_hash"])
        self.assertEqual(
            receipt["source_registration_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(
            receipt["source_calibration_observations_hash"],
            self.observations["calibration_observations_hash"],
        )


if __name__ == "__main__":
    unittest.main()
