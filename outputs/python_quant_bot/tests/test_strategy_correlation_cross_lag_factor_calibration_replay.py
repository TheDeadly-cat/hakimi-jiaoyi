import builtins
import math
import random
import time
import unittest
from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_replay import (
    BETA_ABS_TOLERANCE,
    CALIBRATION_SCHEMA,
    CALIBRATION_STATIC_FINGERPRINT,
    REPLAY_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_replay,
    verify_strategy_correlation_cross_lag_factor_calibration_replay,
)


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
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


class StrategyCorrelationCrossLagFactorCalibrationReplayTests(unittest.TestCase):
    def _registration(self, betas=None, **overrides):
        identities = ["A", "B"]
        document = {
            "beta_by_identity": betas or {"A": "1", "B": "2"},
            "calibration_cutoff_date": "2025-01-01",
            "calibration_receipt_hash": "b" * 64,
            "exposure_estimator": "FROZEN_PRE_EVALUATION_OLS_V1",
            "factor_id": "COMMON-FACTOR-1",
            "factor_policy": "CONTEMPORANEOUS_SINGLE_FACTOR_V1",
            "factor_source_hash": "a" * 64,
            "identity_order": identities,
            "identity_order_hash": strict_canonical_hash(identities),
            "intercept_policy": "NO_INTERCEPT_RETURN_RESIDUAL_V1",
            "missing_policy": "FAIL_CLOSED",
            "schema_version": (
                "strategy-correlation-cross-lag-factor-residualization-"
                "registration-candidate-v1"
            ),
            "selection_cutoff_date": "2025-02-01",
            "static_fingerprint": (
                "20260822-cross-lag-factor-residualization-registration-1"
            ),
        }
        document.update(overrides)
        return seal_strict_canonical_document(document, "registration_hash")

    def _observations(self, *, count=40, factor_values=None):
        identities = ["A", "B"]
        start = date(2024, 11, 1)
        values = factor_values or [((index % 7) - 3) / 10 for index in range(count)]
        rows = []
        for index, factor in enumerate(values):
            rows.append(
                {
                    "factor_return": factor,
                    "observation_date": (start + timedelta(days=index)).isoformat(),
                    "observation_id": f"cal-{index:03d}",
                    "returns": {"A": factor, "B": factor * 2},
                    "sequence_number": index,
                }
            )
        document = {
            "factor_id": "COMMON-FACTOR-1",
            "factor_source_hash": "a" * 64,
            "identity_order": identities,
            "rows": rows,
            "schema_version": CALIBRATION_SCHEMA,
            "static_fingerprint": CALIBRATION_STATIC_FINGERPRINT,
        }
        return seal_strict_canonical_document(
            document, "calibration_observations_hash"
        )

    def _evaluate(self, registration=None, observations=None, **overrides):
        registration = registration or self._registration()
        observations = observations or self._observations()
        kwargs = {
            "expected_registration_hash": registration.get("registration_hash"),
            "expected_calibration_observations_hash": observations.get(
                "calibration_observations_hash"
            ),
        }
        kwargs.update(overrides)
        document = evaluate_strategy_correlation_cross_lag_factor_calibration_replay(
            registration, observations, **kwargs
        )
        return document, registration, observations, kwargs

    def _verify(self, document, registration, observations, kwargs):
        return verify_strategy_correlation_cross_lag_factor_calibration_replay(
            document, registration, observations, **kwargs
        )

    def test_exact_ols_match_is_observed(self):
        document, registration, observations, kwargs = self._evaluate()
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["replay_decision"], "MATCH")
        self.assertEqual(document["max_abs_beta_error"], "0")
        self.assertTrue(document["facts"]["beta_replay_matches_registration"])
        self.assertTrue(self._verify(document, registration, observations, kwargs))

    def test_registered_beta_mismatch_is_observed_block(self):
        registration = self._registration({"A": "0.5", "B": "2"})
        document, _, observations, kwargs = self._evaluate(registration=registration)
        self.assertEqual(document["source_state"], "OBSERVED")
        self.assertEqual(document["replay_decision"], "BLOCK")
        self.assertIn("REGISTERED_BETA_REPLAY_MISMATCH", document["blockers"])
        self.assertFalse(document["facts"]["beta_replay_matches_registration"])
        self.assertTrue(self._verify(document, registration, observations, kwargs))

    def test_contract_identity_and_tolerance_are_exact(self):
        document, _, _, _ = self._evaluate()
        self.assertEqual(document["schema_version"], REPLAY_SCHEMA)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["beta_abs_tolerance"], str(BETA_ABS_TOLERANCE))
        self.assertEqual(document["identity_count"], 2)
        self.assertEqual(document["observation_count"], 40)

    def test_registration_and_observation_expected_hashes_are_bound(self):
        for key in (
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            document, _, _, _ = self._evaluate(**{key: "0" * 64})
            self.assertEqual(document["source_state"], "UNKNOWN", key)

    def test_wrong_estimator_and_intercept_policy_fail_closed(self):
        for field, value in (
            ("exposure_estimator", "OTHER"),
            ("intercept_policy", "WITH_INTERCEPT"),
        ):
            registration = self._registration(**{field: value})
            document, _, _, _ = self._evaluate(registration=registration)
            self.assertEqual(document["source_state"], "UNKNOWN", field)

    def test_factor_identity_and_source_mismatch_fail_closed(self):
        for field, value in (
            ("factor_id", "OTHER"),
            ("factor_source_hash", "c" * 64),
        ):
            observations = self._observations()
            changed = deepcopy(observations)
            changed[field] = value
            changed = seal_strict_canonical_document(
                changed, "calibration_observations_hash"
            )
            document, _, _, _ = self._evaluate(observations=changed)
            self.assertEqual(document["source_state"], "UNKNOWN", field)

    def test_identity_order_and_returns_shape_fail_closed(self):
        observations = self._observations()
        for mutate in (
            lambda value: value.update(identity_order=["B", "A"]),
            lambda value: value["rows"][0]["returns"].pop("B"),
            lambda value: value["rows"][0]["returns"].update(C=0.0),
        ):
            changed = deepcopy(observations)
            mutate(changed)
            changed = seal_strict_canonical_document(
                changed, "calibration_observations_hash"
            )
            document, _, _, _ = self._evaluate(observations=changed)
            self.assertEqual(document["source_state"], "UNKNOWN")

    def test_minimum_observation_count_is_enforced(self):
        observations = self._observations(count=19)
        document, _, _, _ = self._evaluate(observations=observations)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_sequence_gap_and_duplicate_id_fail_closed(self):
        observations = self._observations()
        for mutate in (
            lambda rows: rows[5].update(sequence_number=6),
            lambda rows: rows[5].update(observation_id=rows[4]["observation_id"]),
        ):
            changed = deepcopy(observations)
            mutate(changed["rows"])
            changed = seal_strict_canonical_document(
                changed, "calibration_observations_hash"
            )
            document, _, _, _ = self._evaluate(observations=changed)
            self.assertEqual(document["source_state"], "UNKNOWN")

    def test_date_reorder_and_after_cutoff_fail_closed(self):
        observations = self._observations()
        for index, value in ((5, "2024-11-04"), (39, "2025-01-02")):
            changed = deepcopy(observations)
            changed["rows"][index]["observation_date"] = value
            changed = seal_strict_canonical_document(
                changed, "calibration_observations_hash"
            )
            document, _, _, _ = self._evaluate(observations=changed)
            self.assertEqual(document["source_state"], "UNKNOWN")

    def test_cutoff_order_is_enforced(self):
        registration = self._registration(selection_cutoff_date="2024-12-01")
        document, _, _, _ = self._evaluate(registration=registration)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_zero_factor_energy_and_variance_fail_closed(self):
        for factor_values in ([0.0] * 40, [0.2] * 40):
            observations = self._observations(factor_values=factor_values)
            document, _, _, _ = self._evaluate(observations=observations)
            self.assertEqual(document["source_state"], "UNKNOWN")

    def test_nonfinite_values_fail_before_replay(self):
        observations = self._observations()
        changed = deepcopy(observations)
        changed["rows"][0]["factor_return"] = math.nan
        document, _, _, _ = self._evaluate(observations=changed)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_native_container_types_are_required(self):
        registration = _DictSubclass(self._registration())
        document, _, _, _ = self._evaluate(registration=registration)
        self.assertEqual(document["source_state"], "UNKNOWN")
        observations = self._observations()
        observations["rows"] = _ListSubclass(observations["rows"])
        document, _, _, _ = self._evaluate(observations=observations)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_projection_is_aggregate_only(self):
        document, _, _, _ = self._evaluate()
        keys = _all_keys(document)
        self.assertNotIn("beta_by_identity", keys)
        self.assertNotIn("identity_order", keys)
        self.assertNotIn("returns", keys)
        self.assertIn("registered_beta_ledger_hash", keys)
        self.assertIn("replayed_beta_ledger_hash", keys)

    def test_match_never_attests_timing_or_binding(self):
        document, _, _, _ = self._evaluate()
        self.assertFalse(document["facts"]["external_calibration_timing_attested"])
        self.assertFalse(
            document["facts"]["registration_calibration_receipt_g0_bound"]
        )
        self.assertIn("EXTERNAL_CALIBRATION_TIMING_UNATTESTED", document["blockers"])
        self.assertIn(
            "REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND", document["blockers"]
        )

    def test_authority_is_permanently_locked(self):
        document, _, _, _ = self._evaluate()
        self.assertTrue(document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_resealed_receipt_tamper_is_rejected(self):
        document, registration, observations, kwargs = self._evaluate()
        changed = deepcopy(document)
        changed["replay_decision"] = "MATCH"
        changed["facts"]["external_calibration_timing_attested"] = True
        changed = seal_strict_canonical_document(changed, "receipt_hash")
        self.assertFalse(self._verify(changed, registration, observations, kwargs))

    def test_determinism_and_denied_external_state(self):
        registration = self._registration()
        observations = self._observations()
        with patch.object(builtins, "open", side_effect=AssertionError("io")), patch.object(
            time, "time", side_effect=AssertionError("time")
        ), patch.object(random, "random", side_effect=AssertionError("random")):
            first, _, _, _ = self._evaluate(registration, observations)
            second, _, _, _ = self._evaluate(registration, observations)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
