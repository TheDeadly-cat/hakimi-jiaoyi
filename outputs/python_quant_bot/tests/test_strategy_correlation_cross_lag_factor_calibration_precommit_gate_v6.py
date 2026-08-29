from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6 import (
    POSITIVE_DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3 import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5 as v5_tests
from tests import test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3 as v3_tests


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        V5Case = v5_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV5Tests
        self.v5_case = V5Case(unittest.defaultTestLoader.getTestCaseNames(V5Case)[0])
        self.v5_case.setUp()
        self.precommit_gate_v5 = self.v5_case._evaluate()
        self.precommit_gate_v4 = self.v5_case.precommit_gate_v4
        self.residual_order_gate_v2 = self.v5_case.residual_order_gate_v2
        self.precommit_gate_v3 = self.v5_case.precommit_gate_v3
        self.residual_order_gate_v1 = self.v5_case.residual_order_gate_v1
        self.precommit_gate_v2 = self.v5_case.precommit_gate_v2
        self.residual_energy_gate = self.v5_case.residual_energy_gate
        self.precommit_gate_v1 = self.v5_case.precommit_gate_v1
        self.beta_stability_gate = self.v5_case.beta_stability_gate
        self.declaration = self.v5_case.declaration
        self.report = self.v5_case.report
        self.replay = self.v5_case.replay
        self.registration = self.v5_case.registration
        self.observations = self.v5_case.observations
        self.residual_order_gate_v3 = self._v3_gate(
            self.residual_order_gate_v2,
            self.residual_order_gate_v1,
            self.beta_stability_gate,
            self.replay,
            self.registration,
            self.observations,
        )

    @staticmethod
    def _v3_gate(v2, v1, beta, replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
            v2,
            v1,
            beta,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v2_hash=v2["gate_hash"],
            expected_residual_order_gate_v1_hash=v1["gate_hash"],
            expected_beta_stability_gate_hash=beta["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _expected(self, values: dict[str, object]) -> dict[str, object]:
        baseline = self._values()
        hash_fields = {
            "precommit_gate_v5": "gate_hash",
            "residual_order_gate_v3": "gate_hash",
            "precommit_gate_v4": "gate_hash",
            "residual_order_gate_v2": "gate_hash",
            "precommit_gate_v3": "gate_hash",
            "residual_order_gate_v1": "gate_hash",
            "precommit_gate_v2": "gate_hash",
            "residual_energy_gate": "gate_hash",
            "precommit_gate_v1": "gate_hash",
            "beta_stability_gate": "gate_hash",
            "precommit_declaration": "declaration_hash",
            "report": "verification_hash",
            "replay": "receipt_hash",
            "residualization_registration": "registration_hash",
            "calibration_observations": "calibration_observations_hash",
        }
        documents = {}
        for key, hash_field in hash_fields.items():
            candidate = values.get(key)
            if isinstance(candidate, dict) and isinstance(
                candidate.get(hash_field), str
            ):
                documents[key] = candidate
            else:
                documents[key] = baseline[key]
        return {
            "expected_precommit_gate_v5_hash": documents["precommit_gate_v5"]["gate_hash"],
            "expected_residual_order_gate_v3_hash": documents["residual_order_gate_v3"]["gate_hash"],
            "expected_precommit_gate_v4_hash": documents["precommit_gate_v4"]["gate_hash"],
            "expected_residual_order_gate_v2_hash": documents["residual_order_gate_v2"]["gate_hash"],
            "expected_precommit_gate_v3_hash": documents["precommit_gate_v3"]["gate_hash"],
            "expected_residual_order_gate_v1_hash": documents["residual_order_gate_v1"]["gate_hash"],
            "expected_precommit_gate_v2_hash": documents["precommit_gate_v2"]["gate_hash"],
            "expected_residual_energy_gate_hash": documents["residual_energy_gate"]["gate_hash"],
            "expected_precommit_gate_v1_hash": documents["precommit_gate_v1"]["gate_hash"],
            "expected_beta_stability_gate_hash": documents["beta_stability_gate"]["gate_hash"],
            "expected_declaration_hash": documents["precommit_declaration"]["declaration_hash"],
            "expected_report_hash": documents["report"]["verification_hash"],
            "expected_replay_hash": documents["replay"]["receipt_hash"],
            "expected_registration_hash": documents["residualization_registration"]["registration_hash"],
            "expected_calibration_observations_hash": documents["calibration_observations"]["calibration_observations_hash"],
        }

    def _values(self) -> dict[str, object]:
        return {
            "precommit_gate_v5": self.precommit_gate_v5,
            "residual_order_gate_v3": self.residual_order_gate_v3,
            "precommit_gate_v4": self.precommit_gate_v4,
            "residual_order_gate_v2": self.residual_order_gate_v2,
            "precommit_gate_v3": self.precommit_gate_v3,
            "residual_order_gate_v1": self.residual_order_gate_v1,
            "precommit_gate_v2": self.precommit_gate_v2,
            "residual_energy_gate": self.residual_energy_gate,
            "precommit_gate_v1": self.precommit_gate_v1,
            "beta_stability_gate": self.beta_stability_gate,
            "precommit_declaration": self.declaration,
            "report": self.report,
            "replay": self.replay,
            "residualization_registration": self.registration,
            "calibration_observations": self.observations,
        }

    def _evaluate(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        values = {key: value for key, value in values.items() if not key.startswith("expected_")}
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
            **values,
            **expected,
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        values = {key: value for key, value in values.items() if not key.startswith("expected_")}
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
            document,
            **values,
            **expected,
        )

    def _lag_three_block_context(self) -> dict[str, object]:
        V3Case = v3_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV3Tests
        fixture = V3Case(unittest.defaultTestLoader.getTestCaseNames(V3Case)[0])
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = fixture._periodic_context(3)
        v2 = source["residual_order_gate_v2"]
        v1 = source["residual_order_gate_v1"]
        beta = source["beta_stability_gate"]
        replay = source["replay"]
        registration = source["residualization_registration"]
        observations = source["calibration_observations"]
        residual_energy = v5_tests.evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            beta,
            replay,
            registration,
            observations,
            expected_beta_stability_gate_hash=beta["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )
        report = v5_tests.consume_strategy_correlation_cross_lag_factor_calibration_replay(
            replay,
            residualization_registration=registration,
            calibration_observations=observations,
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
            expected_replay_hash=replay["receipt_hash"],
        )
        declaration = self.v5_case.case.case.h1_case.case._declaration(report)
        precommit_v1 = v5_tests.evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_declaration_hash=declaration["declaration_hash"],
            expected_report_hash=report["verification_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )
        precommit_v2 = self.v5_case.case.case.h1_case._evaluate(
            precommit_gate_v1=precommit_v1,
            stability_gate=beta,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_v3 = self.v5_case.case.case._evaluate(
            precommit_gate_v2=precommit_v2,
            residual_energy_gate=residual_energy,
            precommit_gate_v1=precommit_v1,
            beta_stability_gate=beta,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_v4 = self.v5_case.case._evaluate(
            precommit_gate_v3=precommit_v3,
            residual_order_gate=v1,
            precommit_gate_v2=precommit_v2,
            residual_energy_gate=residual_energy,
            precommit_gate_v1=precommit_v1,
            beta_stability_gate=beta,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_v5 = self.v5_case._evaluate(
            precommit_gate_v4=precommit_v4,
            residual_order_gate_v2=v2,
            precommit_gate_v3=precommit_v3,
            residual_order_gate_v1=v1,
            precommit_gate_v2=precommit_v2,
            residual_energy_gate=residual_energy,
            precommit_gate_v1=precommit_v1,
            beta_stability_gate=beta,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        v3 = self._v3_gate(v2, v1, beta, replay, registration, observations)
        values = {
            "precommit_gate_v5": precommit_v5,
            "residual_order_gate_v3": v3,
            "precommit_gate_v4": precommit_v4,
            "residual_order_gate_v2": v2,
            "precommit_gate_v3": precommit_v3,
            "residual_order_gate_v1": v1,
            "precommit_gate_v2": precommit_v2,
            "residual_energy_gate": residual_energy,
            "precommit_gate_v1": precommit_v1,
            "beta_stability_gate": beta,
            "precommit_declaration": declaration,
            "report": report,
            "replay": replay,
            "residualization_registration": registration,
            "calibration_observations": observations,
        }
        return {**values, **self._expected(values)}

    def _v5_block_context(self) -> dict[str, object]:
        source = self.v5_case._multi_lag_block_context()
        v5 = self.v5_case._evaluate(**source)
        v3 = self._v3_gate(
            source["residual_order_gate_v2"],
            source["residual_order_gate_v1"],
            source["beta_stability_gate"],
            source["replay"],
            source["registration"],
            source["observations"],
        )
        values = {
            "precommit_gate_v5": v5,
            "residual_order_gate_v3": v3,
            "precommit_gate_v4": source["precommit_gate_v4"],
            "residual_order_gate_v2": source["residual_order_gate_v2"],
            "precommit_gate_v3": source["precommit_gate_v3"],
            "residual_order_gate_v1": source["residual_order_gate_v1"],
            "precommit_gate_v2": source["precommit_gate_v2"],
            "residual_energy_gate": source["residual_energy_gate"],
            "precommit_gate_v1": source["precommit_gate_v1"],
            "beta_stability_gate": source["beta_stability_gate"],
            "precommit_declaration": source["declaration"],
            "report": source["report"],
            "replay": source["replay"],
            "residualization_registration": source["registration"],
            "calibration_observations": source["observations"],
        }
        return {**values, **self._expected(values)}

    def test_dual_positive_sources_are_bound_local_only(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["gate_decision"], POSITIVE_DECISION)
        self.assertTrue(result["facts"]["precommit_gate_v5_verified"])
        self.assertTrue(result["facts"]["residual_order_gate_v3_verified"])
        self.assertTrue(self._verify(result))

    def test_v3_block_overrides_positive_v5(self) -> None:
        context = self._lag_three_block_context()
        self.assertEqual(
            context["precommit_gate_v5"]["gate_decision"],
            "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED",
        )
        self.assertEqual(
            context["residual_order_gate_v3"]["gate_decision"],
            "RESIDUAL_THREE_LAG_ORDER_BLOCK",
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(
            result["gate_reason"],
            "RESIDUAL_THREE_LAG_ORDER_STABILITY_GATE_BLOCKED",
        )
        self.assertTrue(self._verify(result, **context))

    def test_v5_block_is_monotone(self) -> None:
        context = self._v5_block_context()
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(result["gate_reason"], "PRECOMMIT_GATE_V5_BLOCKED")
        self.assertFalse(result["facts"]["source_gate_block_relaxed"])

    def test_missing_sources_are_unknown(self) -> None:
        cases = (
            (
                "precommit_gate_v5",
                "expected_precommit_gate_v5_hash",
                self.precommit_gate_v5["gate_hash"],
            ),
            (
                "residual_order_gate_v3",
                "expected_residual_order_gate_v3_hash",
                self.residual_order_gate_v3["gate_hash"],
            ),
        )
        for source_key, expected_key, expected_hash in cases:
            with self.subTest(key=source_key):
                self.assertEqual(
                    self._evaluate(
                        **{source_key: None, expected_key: expected_hash}
                    )["gate_decision"],
                    "UNKNOWN",
                )

    def test_unsupported_sources_are_distinct(self) -> None:
        self.assertEqual(
            self._evaluate(
                precommit_gate_v5={"schema_version": "legacy"},
                expected_precommit_gate_v5_hash=self.precommit_gate_v5["gate_hash"],
            )["source_state"],
            "UNSUPPORTED",
        )
        self.assertEqual(
            self._evaluate(
                residual_order_gate_v3={"schema_version": "legacy"},
                expected_residual_order_gate_v3_hash=self.residual_order_gate_v3[
                    "gate_hash"
                ],
            )["source_state"],
            "UNSUPPORTED",
        )

    def test_expected_top_hashes_are_bound(self) -> None:
        for key in ("expected_precommit_gate_v5_hash", "expected_residual_order_gate_v3_hash"):
            with self.subTest(key=key):
                self.assertEqual(
                    self._evaluate(**{key: "0" * 64})["gate_decision"],
                    "UNKNOWN",
                )

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v4_hash",
            "expected_residual_order_gate_v2_hash",
            "expected_precommit_gate_v3_hash",
            "expected_residual_order_gate_v1_hash",
            "expected_precommit_gate_v2_hash",
            "expected_residual_energy_gate_hash",
            "expected_precommit_gate_v1_hash",
            "expected_beta_stability_gate_hash",
            "expected_declaration_hash",
            "expected_report_hash",
            "expected_replay_hash",
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            with self.subTest(key=key):
                self.assertEqual(self._evaluate(**{key: "0" * 64})["gate_decision"], "UNKNOWN")

    def test_resealed_v5_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v5)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            precommit_gate_v5=source,
            expected_precommit_gate_v5_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_reason"], "SOURCE_GATE_OR_CONTEXT_INVALID")

    def test_resealed_v3_tamper_is_invalid(self) -> None:
        source = deepcopy(self.residual_order_gate_v3)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            residual_order_gate_v3=source,
            expected_residual_order_gate_v3_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_reason"], "SOURCE_GATE_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        context = self._lag_three_block_context()
        result = self._evaluate(
            precommit_gate_v5=context["precommit_gate_v5"],
            residual_order_gate_v3=context["residual_order_gate_v3"],
            expected_precommit_gate_v5_hash=context["expected_precommit_gate_v5_hash"],
            expected_residual_order_gate_v3_hash=context["expected_residual_order_gate_v3_hash"],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_projection_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._evaluate(), sort_keys=True)
        for private_key in ('"rows"', '"returns"', '"beta_by_identity"', '"phase_comb"'):
            self.assertNotIn(private_key, serialized)

    def test_no_independence_or_authority_promotion(self) -> None:
        result = self._evaluate()
        self.assertFalse(result["facts"]["residual_order_independence_proven"])
        for key in (
            "candidate_activation_allowed",
            "current_admission_allowed",
            "current_pointer_written",
            "live_order_allowed",
            "paper_authorized",
            "profitability_claim_allowed",
        ):
            self.assertFalse(result["authority"][key])

    def test_blockers_are_deduplicated(self) -> None:
        blockers = self._evaluate()["blockers"]
        self.assertEqual(len(blockers), len(set(blockers)))

    def test_determinism(self) -> None:
        self.assertEqual(self._evaluate(), self._evaluate())

    def test_verifier_rejects_resealed_v6_tamper(self) -> None:
        result = self._evaluate()
        tampered = deepcopy(result)
        tampered.pop("gate_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_and_fingerprint_are_exact(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
