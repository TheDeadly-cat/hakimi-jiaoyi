from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, getcontext
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1 import (
    BAND_QUADRATIC_ENERGY_CEILING,
    BLOCK_DECISION,
    EVALUATED_LAGS,
    OMNIBUS_BAND_LAGS,
    POSITIVE_DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    _band_quadratic_energy,
    _evaluate_band,
    _lag_coupling,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    _folds,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3
    as residual_order_gate_v3_tests,
)


class StrategyCorrelationCrossLagFactorCalibrationResidualOrderOmnibusGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        decimal_context = getcontext()
        original_precision = decimal_context.prec
        self.addCleanup(setattr, decimal_context, "prec", original_precision)
        decimal_context.prec = 50

        source_name = unittest.defaultTestLoader.getTestCaseNames(
            residual_order_gate_v3_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV3Tests
        )[0]
        self.case = residual_order_gate_v3_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV3Tests(
            source_name
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

        self.source_v3 = self.case._evaluate()
        self.source_v2 = self.case.source_v2
        self.source_v1 = self.case.source_v1
        self.beta_gate = self.case.beta_gate
        self.replay = self.case.replay
        self.registration = self.case.registration
        self.observations = self.case.observations

    def _values(self) -> dict[str, object]:
        return {
            "residual_order_gate_v3": self.source_v3,
            "residual_order_gate_v2": self.source_v2,
            "residual_order_gate_v1": self.source_v1,
            "beta_stability_gate": self.beta_gate,
            "replay": self.replay,
            "residualization_registration": self.registration,
            "calibration_observations": self.observations,
            "expected_residual_order_gate_v3_hash": self.source_v3["gate_hash"],
            "expected_residual_order_gate_v2_hash": self.source_v2["gate_hash"],
            "expected_residual_order_gate_v1_hash": self.source_v1["gate_hash"],
            "expected_beta_stability_gate_hash": self.beta_gate["gate_hash"],
            "expected_replay_hash": self.replay["receipt_hash"],
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_calibration_observations_hash": self.observations[
                "calibration_observations_hash"
            ],
        }

    def _evaluate(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
            **values
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
            document,
            **values,
        )

    def _sequence_context(self, sequence: list[int]) -> dict[str, object]:
        registration = deepcopy(self.registration)
        observations = deepcopy(self.observations)
        observations.pop("calibration_observations_hash", None)
        residual_by_sequence: dict[int, Decimal] = {}

        for fold in _folds(observations["rows"]):
            self.assertEqual(len(fold), len(sequence))
            factors = [Decimal(str(row["factor_return"])) for row in fold]
            base = [Decimal(value) for value in sequence]
            projection = sum(
                left * right for left, right in zip(base, factors)
            ) / sum(value * value for value in factors)
            residuals = [
                left - projection * right
                for left, right in zip(base, factors)
            ]
            self.assertLessEqual(
                abs(sum(left * right for left, right in zip(residuals, factors))),
                Decimal("1e-40"),
            )
            for row, residual in zip(fold, residuals):
                residual_by_sequence[row["sequence_number"]] = residual

        for row in observations["rows"]:
            factor = Decimal(str(row["factor_return"]))
            residual = residual_by_sequence[row["sequence_number"]]
            for identity in registration["identity_order"]:
                beta = Decimal(str(registration["beta_by_identity"][identity]))
                row["returns"][identity] = float(beta * factor + residual)
        observations = seal_strict_canonical_document(
            observations,
            "calibration_observations_hash",
        )

        h0_case = self.case.case.case.case
        replay = h0_case._replay(registration, observations)
        replay_hash = replay["receipt_hash"]
        registration_hash = registration["registration_hash"]
        observations_hash = observations["calibration_observations_hash"]
        beta_gate = h0_case._evaluate(
            replay=replay,
            registration=registration,
            observations=observations,
            expected_replay_hash=replay_hash,
            expected_registration_hash=registration_hash,
            expected_observations_hash=observations_hash,
        )
        beta_hash = beta_gate["gate_hash"]
        v1_gate = self.case.case.case._evaluate(
            beta_stability_gate=beta_gate,
            replay=replay,
            registration=registration,
            observations=observations,
            expected_beta_gate_hash=beta_hash,
            expected_replay_hash=replay_hash,
            expected_registration_hash=registration_hash,
            expected_observations_hash=observations_hash,
        )
        v2_gate = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            v1_gate,
            beta_gate,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v1_hash=v1_gate["gate_hash"],
            expected_beta_stability_gate_hash=beta_hash,
            expected_replay_hash=replay_hash,
            expected_registration_hash=registration_hash,
            expected_calibration_observations_hash=observations_hash,
        )
        v3_context = {
            "residual_order_gate_v2": v2_gate,
            "residual_order_gate_v1": v1_gate,
            "beta_stability_gate": beta_gate,
            "replay": replay,
            "residualization_registration": registration,
            "calibration_observations": observations,
            "expected_residual_order_gate_v2_hash": v2_gate["gate_hash"],
            "expected_residual_order_gate_v1_hash": v1_gate["gate_hash"],
            "expected_beta_stability_gate_hash": beta_hash,
            "expected_replay_hash": replay_hash,
            "expected_registration_hash": registration_hash,
            "expected_calibration_observations_hash": observations_hash,
        }
        v3_gate = self.case._evaluate(**v3_context)
        return {
            "residual_order_gate_v3": v3_gate,
            **v3_context,
            "expected_residual_order_gate_v3_hash": v3_gate["gate_hash"],
        }

    def _band_couplings(
        self,
        context: dict[str, object],
    ) -> list[dict[int, Decimal]]:
        registration = context["residualization_registration"]
        observations = context["calibration_observations"]
        result: list[dict[int, Decimal]] = []
        for fold in _folds(observations["rows"]):
            for identity in registration["identity_order"]:
                beta = Decimal(str(registration["beta_by_identity"][identity]))
                residuals = [
                    Decimal(str(row["returns"][identity]))
                    - beta * Decimal(str(row["factor_return"]))
                    for row in fold
                ]
                result.append(
                    {
                        lag: _lag_coupling(residuals, lag)[0]
                        for lag in OMNIBUS_BAND_LAGS
                    }
                )
        return result

    def test_stable_source_and_zero_band_are_local_candidate(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["gate_decision"], POSITIVE_DECISION)
        self.assertEqual(result["maximum_observed_lag_band_quadratic_energy"], "0")
        self.assertTrue(result["facts"]["source_v3_verified"])
        self.assertTrue(
            result["facts"]["omnibus_quadratic_energy_threshold_passed"]
        )
        self.assertTrue(self._verify(result))

    def test_distributed_band_order_evades_every_single_lag_ceiling(self) -> None:
        context = self._sequence_context(
            [1, 1, -1, 1, 1, 1, -1, -1, 1, 1]
        )
        source = context["residual_order_gate_v3"]
        self.assertEqual(
            source["gate_decision"],
            "RESIDUAL_THREE_LAG_ORDER_STABLE_CANDIDATE",
        )
        self.assertLessEqual(
            Decimal(
                source[
                    "maximum_observed_absolute_three_lag_residual_energy_coupling"
                ]
            ),
            Decimal("0.8"),
        )
        couplings = self._band_couplings(context)
        self.assertTrue(
            all(
                value <= Decimal("0.8")
                for values in couplings
                for value in values.values()
            )
        )
        self.assertTrue(
            all(
                _band_quadratic_energy(values)
                > BAND_QUADRATIC_ENERGY_CEILING
                for values in couplings
            )
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], BLOCK_DECISION)
        self.assertGreater(
            Decimal(result["maximum_observed_lag_band_quadratic_energy"]),
            BAND_QUADRATIC_ENERGY_CEILING,
        )
        self.assertTrue(self._verify(result, **context))

    def test_single_band_lag_breach_is_blocked_by_derived_ceiling(self) -> None:
        sequence = [1, 1, 1, -1, 1] * 2
        context = self._sequence_context(sequence)
        couplings = self._band_couplings(context)
        self.assertTrue(
            any(
                values[5] > Decimal("0.8")
                for values in couplings
            )
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], BLOCK_DECISION)

    def test_source_v3_block_is_monotone(self) -> None:
        source_context = self.case._periodic_context(3)
        source_v3 = self.case._evaluate(**source_context)
        self.assertNotEqual(
            source_v3["gate_decision"],
            "RESIDUAL_THREE_LAG_ORDER_STABLE_CANDIDATE",
        )
        context = {
            **source_context,
            "residual_order_gate_v3": source_v3,
            "expected_residual_order_gate_v3_hash": source_v3["gate_hash"],
        }
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], BLOCK_DECISION)
        self.assertEqual(result["gate_reason"], "SOURCE_V3_BLOCKED")
        self.assertFalse(result["facts"]["source_gate_block_relaxed"])

    def test_missing_and_unsupported_source_are_distinct(self) -> None:
        missing = self._evaluate(residual_order_gate_v3=None)
        self.assertEqual(missing["gate_reason"], "MISSING_SOURCE_V3")
        unsupported = self._evaluate(
            residual_order_gate_v3={"schema_version": "legacy"}
        )
        self.assertEqual(unsupported["source_state"], "UNSUPPORTED")
        self.assertEqual(unsupported["gate_reason"], "UNSUPPORTED_SOURCE_V3")

    def test_expected_source_hash_is_bound(self) -> None:
        result = self._evaluate(expected_residual_order_gate_v3_hash="0" * 64)
        self.assertEqual(result["gate_decision"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "EXPECTED_SOURCE_V3_HASH_MISMATCH")

    def test_v2_and_v1_documents_and_hashes_are_required(self) -> None:
        missing_v2 = self._evaluate(residual_order_gate_v2=None)
        self.assertEqual(missing_v2["gate_reason"], "SOURCE_V2_OR_HASH_INVALID")
        missing_v1 = self._evaluate(residual_order_gate_v1=None)
        self.assertEqual(missing_v1["gate_reason"], "SOURCE_V1_OR_HASH_INVALID")
        mismatched_v1 = self._evaluate(
            expected_residual_order_gate_v1_hash="0" * 64
        )
        self.assertEqual(mismatched_v1["gate_reason"], "SOURCE_V1_OR_HASH_INVALID")

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_residual_order_gate_v2_hash",
            "expected_beta_stability_gate_hash",
            "expected_replay_hash",
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            with self.subTest(key=key):
                result = self._evaluate(**{key: "0" * 64})
                self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_resealed_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.source_v3)
        source.pop("gate_hash")
        source["maximum_observed_absolute_three_lag_residual_energy_coupling"] = "0.7"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            residual_order_gate_v3=source,
            expected_residual_order_gate_v3_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_reason"], "SOURCE_V3_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        alternate = self._sequence_context(
            [1, 1, -1, 1, 1, 1, -1, -1, 1, 1]
        )
        result = self._evaluate(
            residual_order_gate_v3=alternate["residual_order_gate_v3"],
            expected_residual_order_gate_v3_hash=alternate[
                "expected_residual_order_gate_v3_hash"
            ],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_projection_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._evaluate(), sort_keys=True)
        self.assertNotIn('"rows"', serialized)
        self.assertNotIn('"returns"', serialized)
        self.assertNotIn('"beta_by_identity"', serialized)
        self.assertNotIn("absolute_residual_energy_coupling_by_lag", serialized)
        self.assertIn(
            "private_fold_lag_band_residual_order_ledger_hash",
            serialized,
        )

    def test_candidate_is_finite_horizon_not_independence_or_authority(self) -> None:
        result = self._evaluate()
        self.assertTrue(result["facts"]["finite_horizon_only"])
        self.assertFalse(result["facts"]["residual_order_independence_proven"])
        self.assertIn("LAGS_ABOVE_SIX_UNRESOLVED", result["blockers"])
        self.assertIn("EXTERNAL_TIMING_UNRESOLVED", result["blockers"])
        self.assertFalse(result["authority"]["current_admission_allowed"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])
        self.assertFalse(result["authority"]["profitability_claim_allowed"])

    def test_quadratic_energy_boundary_is_derived_and_inclusive(self) -> None:
        energy = _band_quadratic_energy(
            {4: Decimal("0.8"), 5: Decimal("0"), 6: Decimal("0")}
        )
        self.assertEqual(energy, Decimal("0.64"))
        self.assertEqual(energy, BAND_QUADRATIC_ENERGY_CEILING)
        self.assertLessEqual(energy, BAND_QUADRATIC_ENERGY_CEILING)

    def test_quadratic_energy_detects_distributed_moderate_coupling(self) -> None:
        energy = _band_quadratic_energy(
            {4: Decimal("0.5"), 5: Decimal("0.5"), 6: Decimal("0.5")}
        )
        self.assertEqual(energy, Decimal("0.75"))
        self.assertGreater(energy, BAND_QUADRATIC_ENERGY_CEILING)

    def test_zero_residuals_are_defined_stable(self) -> None:
        coupling, zero_energy = _lag_coupling([Decimal("0")] * 10, 6)
        self.assertEqual(coupling, Decimal("0"))
        self.assertTrue(zero_energy)
        metrics = _evaluate_band(self.registration, self.observations)
        self.assertEqual(
            metrics["maximum_observed_lag_band_quadratic_energy"],
            "0",
        )

    def test_incomplete_band_and_short_fold_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _band_quadratic_energy({4: Decimal("0"), 5: Decimal("0")})
        with self.assertRaises(ValueError):
            _lag_coupling([Decimal("1")] * 6, 6)

    def test_decimal_context_is_not_mutated(self) -> None:
        getcontext().prec = 17
        _lag_coupling([Decimal("1")] * 10, 6)
        _band_quadratic_energy(
            {4: Decimal("0.5"), 5: Decimal("0.5"), 6: Decimal("0.5")}
        )
        self.assertEqual(getcontext().prec, 17)

    def test_private_ledger_changes_with_residual_path(self) -> None:
        baseline = self._evaluate()
        alternate_context = self._sequence_context(
            [1, 1, -1, 1, 1, 1, -1, -1, 1, 1]
        )
        alternate = self._evaluate(**alternate_context)
        self.assertNotEqual(
            baseline["private_fold_lag_band_residual_order_ledger_hash"],
            alternate["private_fold_lag_band_residual_order_ledger_hash"],
        )

    def test_determinism(self) -> None:
        self.assertEqual(self._evaluate(), self._evaluate())

    def test_verifier_rejects_resealed_gate_tamper(self) -> None:
        result = self._evaluate()
        tampered = deepcopy(result)
        tampered.pop("gate_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_lags_and_pair_counts_are_exact(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["evaluated_lags"], list(EVALUATED_LAGS))
        self.assertEqual(result["omnibus_band_lags"], list(OMNIBUS_BAND_LAGS))
        self.assertEqual(result["maximum_evaluated_lag"], 6)
        self.assertEqual(
            result["maximum_allowed_lag_band_quadratic_energy"],
            "0.64",
        )
        self.assertEqual(result["minimum_observed_lag_pairs"], 4)
        self.assertEqual(result["maximum_observed_lag_pairs"], 6)


if __name__ == "__main__":
    unittest.main()
