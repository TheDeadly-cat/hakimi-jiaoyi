from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, getcontext
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    _folds,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3 import (
    BLOCK_DECISION,
    EVALUATED_LAGS,
    NEWLY_EVALUATED_LAGS,
    POSITIVE_DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    _lag_three_coupling,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2
    as residual_order_gate_v2_tests,
)


class StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        decimal_context = getcontext()
        original_precision = decimal_context.prec
        self.addCleanup(setattr, decimal_context, "prec", original_precision)
        decimal_context.prec = 50
        source_name = unittest.defaultTestLoader.getTestCaseNames(
            residual_order_gate_v2_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV2Tests
        )[0]
        self.case = (
            residual_order_gate_v2_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV2Tests(
                source_name
            )
        )
        self.case.setUp()
        self.source_v2 = self.case._evaluate()
        self.source_v1 = self.case.residual_order_gate_v1
        self.beta_gate = self.case.beta_stability_gate
        self.replay = self.case.replay
        self.registration = self.case.registration
        self.observations = self.case.observations

    def _values(self) -> dict[str, object]:
        return {
            "residual_order_gate_v2": self.source_v2,
            "residual_order_gate_v1": self.source_v1,
            "beta_stability_gate": self.beta_gate,
            "replay": self.replay,
            "residualization_registration": self.registration,
            "calibration_observations": self.observations,
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
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
            **values
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
            document,
            **values,
        )

    def _periodic_context(self, period: int) -> dict[str, object]:
        registration = deepcopy(self.registration)
        observations = deepcopy(self.observations)
        observations.pop("calibration_observations_hash", None)
        residual_by_sequence: dict[int, Decimal] = {}
        for fold in _folds(observations["rows"]):
            factors = [Decimal(str(row["factor_return"])) for row in fold]
            if period == 3:
                base = [
                    Decimal(1 if index % 3 in (0, 1) else -1)
                    for index in range(len(fold))
                ]
            else:
                base = [
                    Decimal(1 if index % 2 == 0 else -1)
                    for index in range(len(fold))
                ]
            projection = sum(
                left * right for left, right in zip(base, factors)
            ) / sum(value * value for value in factors)
            residuals = [
                left - projection * right
                for left, right in zip(base, factors)
            ]
            self.assertLessEqual(
                abs(
                    sum(
                        left * right
                        for left, right in zip(residuals, factors)
                    )
                ),
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

        h0_case = self.case.case.case
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
        v1_gate = self.case.case._evaluate(
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
        return {
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

    def test_stable_source_and_lag_three_are_local_candidate(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["gate_decision"], POSITIVE_DECISION)
        self.assertTrue(result["facts"]["source_v2_verified"])
        self.assertTrue(result["facts"]["residual_order_threshold_passed"])
        self.assertTrue(self._verify(result))

    def test_lag_three_periodicity_evades_v2_and_is_blocked(self) -> None:
        context = self._periodic_context(3)
        source = context["residual_order_gate_v2"]
        self.assertEqual(source["gate_decision"], "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE")
        self.assertLessEqual(
            Decimal(
                source[
                    "maximum_observed_absolute_multi_lag_residual_energy_coupling"
                ]
            ),
            Decimal("0.8"),
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], BLOCK_DECISION)
        self.assertGreater(
            Decimal(
                result[
                    "maximum_observed_absolute_lag_three_residual_energy_coupling"
                ]
            ),
            Decimal("0.8"),
        )
        self.assertTrue(self._verify(result, **context))

    def test_source_v2_block_is_monotone(self) -> None:
        context = self._periodic_context(2)
        self.assertNotEqual(
            context["residual_order_gate_v2"]["gate_decision"],
            "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE",
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], BLOCK_DECISION)
        self.assertEqual(result["gate_reason"], "SOURCE_V2_BLOCKED")
        self.assertFalse(result["facts"]["source_gate_block_relaxed"])

    def test_missing_source_is_unknown(self) -> None:
        result = self._evaluate(residual_order_gate_v2=None)
        self.assertEqual(result["gate_decision"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "MISSING_SOURCE_V2")

    def test_unsupported_source_is_distinct(self) -> None:
        result = self._evaluate(residual_order_gate_v2={"schema_version": "legacy"})
        self.assertEqual(result["source_state"], "UNSUPPORTED")
        self.assertEqual(result["gate_reason"], "UNSUPPORTED_SOURCE_V2")

    def test_expected_source_hash_is_bound(self) -> None:
        result = self._evaluate(expected_residual_order_gate_v2_hash="0" * 64)
        self.assertEqual(result["gate_decision"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "EXPECTED_SOURCE_V2_HASH_MISMATCH")

    def test_v1_document_and_expected_hash_are_required(self) -> None:
        missing = self._evaluate(residual_order_gate_v1=None)
        self.assertEqual(missing["gate_decision"], "UNKNOWN")
        self.assertEqual(missing["gate_reason"], "SOURCE_V1_OR_HASH_INVALID")
        mismatched = self._evaluate(expected_residual_order_gate_v1_hash="0" * 64)
        self.assertEqual(mismatched["gate_decision"], "UNKNOWN")
        self.assertEqual(mismatched["gate_reason"], "SOURCE_V1_OR_HASH_INVALID")

    def test_v1_document_is_cross_bound_to_v2_declaration(self) -> None:
        source_v1 = deepcopy(self.source_v1)
        source_v1.pop("gate_hash")
        source_v1["gate_reason"] = "RESEALED_CONTEXT_DRIFT"
        source_v1 = seal_strict_canonical_document(source_v1, "gate_hash")
        result = self._evaluate(
            residual_order_gate_v1=source_v1,
            expected_residual_order_gate_v1_hash=source_v1["gate_hash"],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "SOURCE_V1_V2_HASH_MISMATCH")

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_beta_stability_gate_hash",
            "expected_replay_hash",
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            with self.subTest(key=key):
                result = self._evaluate(**{key: "0" * 64})
                self.assertEqual(result["gate_decision"], "UNKNOWN")
                self.assertEqual(result["gate_reason"], "SOURCE_V2_OR_CONTEXT_INVALID")

    def test_resealed_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.source_v2)
        source.pop("gate_hash")
        source["maximum_observed_absolute_multi_lag_residual_energy_coupling"] = "0.7"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            residual_order_gate_v2=source,
            expected_residual_order_gate_v2_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")
        self.assertEqual(result["gate_reason"], "SOURCE_V2_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        context = self._periodic_context(3)
        result = self._evaluate(
            residual_order_gate_v2=context["residual_order_gate_v2"],
            expected_residual_order_gate_v2_hash=context[
                "expected_residual_order_gate_v2_hash"
            ],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_projection_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._evaluate(), sort_keys=True)
        self.assertNotIn('"rows"', serialized)
        self.assertNotIn('"returns"', serialized)
        self.assertNotIn('"beta_by_identity"', serialized)
        self.assertIn("private_fold_lag_three_residual_order_ledger_hash", serialized)

    def test_candidate_is_not_independence_proof_or_authority(self) -> None:
        result = self._evaluate()
        self.assertFalse(result["facts"]["residual_order_independence_proven"])
        self.assertIn("LAGS_ABOVE_THREE_UNRESOLVED", result["blockers"])
        self.assertFalse(result["authority"]["current_admission_allowed"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])
        self.assertFalse(result["authority"]["profitability_claim_allowed"])

    def test_threshold_boundary_is_inclusive(self) -> None:
        coupling, zero_energy = _lag_three_coupling(
            [Decimal("1"), Decimal("0"), Decimal("0"), Decimal("2")]
        )
        self.assertEqual(coupling, Decimal("0.8"))
        self.assertFalse(zero_energy)
        self.assertLessEqual(coupling, Decimal("0.8"))

    def test_zero_residuals_are_defined_stable(self) -> None:
        coupling, zero_energy = _lag_three_coupling([Decimal("0")] * 10)
        self.assertEqual(coupling, Decimal("0"))
        self.assertTrue(zero_energy)

    def test_determinism(self) -> None:
        self.assertEqual(self._evaluate(), self._evaluate())

    def test_verifier_rejects_resealed_gate_tamper(self) -> None:
        result = self._evaluate()
        tampered = deepcopy(result)
        tampered.pop("gate_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_and_lags_are_exact(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["evaluated_lags"], list(EVALUATED_LAGS))
        self.assertEqual(result["newly_evaluated_lags"], list(NEWLY_EVALUATED_LAGS))


if __name__ == "__main__":
    unittest.main()
