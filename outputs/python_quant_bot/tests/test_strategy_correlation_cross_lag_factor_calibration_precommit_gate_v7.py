from __future__ import annotations

from copy import deepcopy
from decimal import getcontext
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7 import (
    EVALUATED_LAGS,
    OMNIBUS_BAND_LAGS,
    POSITIVE_DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    _cross_bindings_match,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1 import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6
    as v6_tests,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1
    as omnibus_tests,
)


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV7Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        decimal_context = getcontext()
        original_precision = decimal_context.prec
        self.addCleanup(setattr, decimal_context, "prec", original_precision)
        decimal_context.prec = 50

        V6Case = v6_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV6Tests
        self.v6_case = V6Case(unittest.defaultTestLoader.getTestCaseNames(V6Case)[0])
        self.v6_case.setUp()
        self.addCleanup(self.v6_case.doCleanups)
        self.addCleanup(self.v6_case.v5_case.doCleanups)

        OmnibusCase = omnibus_tests.StrategyCorrelationCrossLagFactorCalibrationResidualOrderOmnibusGateV1Tests
        self.omnibus_case = OmnibusCase(
            unittest.defaultTestLoader.getTestCaseNames(OmnibusCase)[0]
        )
        self.omnibus_case.setUp()
        self.addCleanup(self.omnibus_case.doCleanups)

        self.precommit_gate_v6 = self.v6_case._evaluate()
        self.precommit_gate_v5 = self.v6_case.precommit_gate_v5
        self.residual_order_gate_v3 = self.v6_case.residual_order_gate_v3
        self.precommit_gate_v4 = self.v6_case.precommit_gate_v4
        self.residual_order_gate_v2 = self.v6_case.residual_order_gate_v2
        self.precommit_gate_v3 = self.v6_case.precommit_gate_v3
        self.residual_order_gate_v1 = self.v6_case.residual_order_gate_v1
        self.precommit_gate_v2 = self.v6_case.precommit_gate_v2
        self.residual_energy_gate = self.v6_case.residual_energy_gate
        self.precommit_gate_v1 = self.v6_case.precommit_gate_v1
        self.beta_stability_gate = self.v6_case.beta_stability_gate
        self.declaration = self.v6_case.declaration
        self.report = self.v6_case.report
        self.replay = self.v6_case.replay
        self.registration = self.v6_case.registration
        self.observations = self.v6_case.observations
        self.omnibus_gate_v1 = self._omnibus_gate(
            self.residual_order_gate_v3,
            self.residual_order_gate_v2,
            self.residual_order_gate_v1,
            self.beta_stability_gate,
            self.replay,
            self.registration,
            self.observations,
        )

    @staticmethod
    def _omnibus_gate(v3, v2, v1, beta, replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
            v3,
            v2,
            v1,
            beta,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v3_hash=v3["gate_hash"],
            expected_residual_order_gate_v2_hash=v2["gate_hash"],
            expected_residual_order_gate_v1_hash=v1["gate_hash"],
            expected_beta_stability_gate_hash=beta["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _values(self) -> dict[str, object]:
        return {
            "precommit_gate_v6": self.precommit_gate_v6,
            "omnibus_gate_v1": self.omnibus_gate_v1,
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

    def _expected(self, values: dict[str, object]) -> dict[str, object]:
        baseline = self._values()
        hash_fields = {
            "precommit_gate_v6": "gate_hash",
            "omnibus_gate_v1": "gate_hash",
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
        documents: dict[str, dict[str, object]] = {}
        for key, hash_field in hash_fields.items():
            candidate = values.get(key)
            if isinstance(candidate, dict) and isinstance(
                candidate.get(hash_field), str
            ):
                documents[key] = candidate
            else:
                documents[key] = baseline[key]
        return {
            f"expected_{key}_hash": document[hash_fields[key]]
            for key, document in documents.items()
        } | {
            "expected_declaration_hash": documents["precommit_declaration"][
                "declaration_hash"
            ],
            "expected_report_hash": documents["report"]["verification_hash"],
            "expected_replay_hash": documents["replay"]["receipt_hash"],
            "expected_registration_hash": documents[
                "residualization_registration"
            ]["registration_hash"],
            "expected_calibration_observations_hash": documents[
                "calibration_observations"
            ]["calibration_observations_hash"],
        }

    def _normalized_expected(self, values: dict[str, object]) -> dict[str, object]:
        expected = self._expected(values)
        aliases = {
            "expected_precommit_declaration_hash": "expected_declaration_hash",
            "expected_residualization_registration_hash": "expected_registration_hash",
        }
        for source, target in aliases.items():
            expected.pop(source, None)
        expected.pop("expected_report_hash", None)
        expected["expected_report_hash"] = self._expected(values)[
            "expected_report_hash"
        ]
        expected.pop("expected_replay_hash", None)
        expected["expected_replay_hash"] = self._expected(values)[
            "expected_replay_hash"
        ]
        expected.pop("expected_calibration_observations_hash", None)
        expected["expected_calibration_observations_hash"] = self._expected(values)[
            "expected_calibration_observations_hash"
        ]
        return expected

    def _evaluate(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._normalized_expected(values)
        expected.update(
            {
                key: value
                for key, value in overrides.items()
                if key.startswith("expected_")
            }
        )
        values = {
            key: value
            for key, value in values.items()
            if not key.startswith("expected_")
        }
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
            **values,
            **expected,
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        expected = self._normalized_expected(values)
        expected.update(
            {
                key: value
                for key, value in overrides.items()
                if key.startswith("expected_")
            }
        )
        values = {
            key: value
            for key, value in values.items()
            if not key.startswith("expected_")
        }
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
            document,
            **values,
            **expected,
        )

    def _shared_context(self, sequence: list[int]) -> dict[str, object]:
        source = self.omnibus_case._sequence_context(sequence)
        v3 = source["residual_order_gate_v3"]
        v2 = source["residual_order_gate_v2"]
        v1 = source["residual_order_gate_v1"]
        beta = source["beta_stability_gate"]
        replay = source["replay"]
        registration = source["residualization_registration"]
        observations = source["calibration_observations"]

        v5_module = v6_tests.v5_tests
        residual_energy = v5_module.evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
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
        report = v5_module.consume_strategy_correlation_cross_lag_factor_calibration_replay(
            replay,
            residualization_registration=registration,
            calibration_observations=observations,
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
            expected_replay_hash=replay["receipt_hash"],
        )
        declaration = self.v6_case.v5_case.case.case.h1_case.case._declaration(
            report
        )
        precommit_v1 = v5_module.evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
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
        precommit_v2 = self.v6_case.v5_case.case.case.h1_case._evaluate(
            precommit_gate_v1=precommit_v1,
            stability_gate=beta,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_v3 = self.v6_case.v5_case.case.case._evaluate(
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
        precommit_v4 = self.v6_case.v5_case.case._evaluate(
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
        precommit_v5 = self.v6_case.v5_case._evaluate(
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
        v6_values = {
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
        precommit_v6 = self.v6_case._evaluate(**v6_values)
        omnibus = self.omnibus_case._evaluate(**source)
        values = {
            "precommit_gate_v6": precommit_v6,
            "omnibus_gate_v1": omnibus,
            **v6_values,
        }
        return {**values, **self._normalized_expected(values)}

    def _v6_block_context(self) -> dict[str, object]:
        source = self.v6_case._lag_three_block_context()
        precommit_v6 = self.v6_case._evaluate(**source)
        omnibus = self._omnibus_gate(
            source["residual_order_gate_v3"],
            source["residual_order_gate_v2"],
            source["residual_order_gate_v1"],
            source["beta_stability_gate"],
            source["replay"],
            source["residualization_registration"],
            source["calibration_observations"],
        )
        values = {
            "precommit_gate_v6": precommit_v6,
            "omnibus_gate_v1": omnibus,
            **{
                key: value
                for key, value in source.items()
                if not key.startswith("expected_")
            },
        }
        return {**values, **self._normalized_expected(values)}

    def test_dual_positive_sources_are_bound_local_only(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["gate_decision"], POSITIVE_DECISION)
        self.assertTrue(result["facts"]["precommit_gate_v6_verified"])
        self.assertTrue(result["facts"]["omnibus_gate_v1_verified"])
        self.assertTrue(result["facts"]["finite_horizon_omnibus_guard_bound"])
        self.assertTrue(self._verify(result))

    def test_omnibus_block_overrides_positive_v6(self) -> None:
        context = self._shared_context(
            [1, 1, -1, 1, 1, 1, -1, -1, 1, 1]
        )
        self.assertEqual(
            context["precommit_gate_v6"]["gate_decision"],
            "BOUND_LOCAL_ONLY_THREE_LAG_STABILITY_GUARDED",
        )
        self.assertEqual(
            context["omnibus_gate_v1"]["gate_decision"],
            "RESIDUAL_FINITE_HORIZON_OMNIBUS_BLOCK",
        )
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(
            result["gate_reason"],
            "RESIDUAL_FINITE_HORIZON_OMNIBUS_GATE_BLOCKED",
        )
        self.assertTrue(self._verify(result, **context))

    def test_v6_block_is_monotone(self) -> None:
        context = self._v6_block_context()
        result = self._evaluate(**context)
        self.assertEqual(result["gate_decision"], "BLOCK")
        self.assertEqual(result["gate_reason"], "PRECOMMIT_GATE_V6_BLOCKED")
        self.assertFalse(result["facts"]["source_gate_block_relaxed"])

    def test_missing_sources_are_unknown(self) -> None:
        for key in ("precommit_gate_v6", "omnibus_gate_v1"):
            with self.subTest(key=key):
                result = self._evaluate(**{key: None})
                self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_unsupported_sources_are_distinct(self) -> None:
        unsupported_v6 = self._evaluate(
            precommit_gate_v6={"schema_version": "legacy"},
            expected_precommit_gate_v6_hash=self.precommit_gate_v6["gate_hash"],
        )
        self.assertEqual(unsupported_v6["source_state"], "UNSUPPORTED")
        unsupported_omnibus = self._evaluate(
            omnibus_gate_v1={"schema_version": "legacy"},
            expected_omnibus_gate_v1_hash=self.omnibus_gate_v1["gate_hash"],
        )
        self.assertEqual(unsupported_omnibus["source_state"], "UNSUPPORTED")

    def test_expected_top_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v6_hash",
            "expected_omnibus_gate_v1_hash",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self._evaluate(**{key: "0" * 64})["gate_decision"],
                    "UNKNOWN",
                )

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v5_hash",
            "expected_residual_order_gate_v3_hash",
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
                self.assertEqual(
                    self._evaluate(**{key: "0" * 64})["gate_decision"],
                    "UNKNOWN",
                )

    def test_resealed_v6_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v6)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            precommit_gate_v6=source,
            expected_precommit_gate_v6_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_reason"], "SOURCE_GATE_OR_CONTEXT_INVALID")

    def test_resealed_omnibus_tamper_is_invalid(self) -> None:
        source = deepcopy(self.omnibus_gate_v1)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._evaluate(
            omnibus_gate_v1=source,
            expected_omnibus_gate_v1_hash=source["gate_hash"],
        )
        self.assertEqual(result["gate_reason"], "SOURCE_GATE_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        alternate = self._shared_context(
            [1, 1, -1, 1, 1, 1, -1, -1, 1, 1]
        )
        result = self._evaluate(
            precommit_gate_v6=alternate["precommit_gate_v6"],
            omnibus_gate_v1=alternate["omnibus_gate_v1"],
            expected_precommit_gate_v6_hash=alternate[
                "expected_precommit_gate_v6_hash"
            ],
            expected_omnibus_gate_v1_hash=alternate[
                "expected_omnibus_gate_v1_hash"
            ],
        )
        self.assertEqual(result["gate_decision"], "UNKNOWN")

    def test_cross_gate_hash_mismatch_is_detected(self) -> None:
        omnibus = deepcopy(self.omnibus_gate_v1)
        omnibus["source_residual_order_gate_v3_hash"] = "0" * 64
        expected = self._normalized_expected(self._values())
        self.assertFalse(
            _cross_bindings_match(
                self.precommit_gate_v6,
                omnibus,
                expected_precommit_gate_v5_hash=expected[
                    "expected_precommit_gate_v5_hash"
                ],
                expected_residual_order_gate_v3_hash=expected[
                    "expected_residual_order_gate_v3_hash"
                ],
                expected_precommit_gate_v4_hash=expected[
                    "expected_precommit_gate_v4_hash"
                ],
                expected_residual_order_gate_v2_hash=expected[
                    "expected_residual_order_gate_v2_hash"
                ],
                expected_residual_order_gate_v1_hash=expected[
                    "expected_residual_order_gate_v1_hash"
                ],
                expected_beta_stability_gate_hash=expected[
                    "expected_beta_stability_gate_hash"
                ],
                expected_replay_hash=expected["expected_replay_hash"],
                expected_registration_hash=expected[
                    "expected_registration_hash"
                ],
                expected_calibration_observations_hash=expected[
                    "expected_calibration_observations_hash"
                ],
            )
        )

    def test_projection_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._evaluate(), sort_keys=True)
        for private_key in (
            '"rows"',
            '"returns"',
            '"beta_by_identity"',
            "absolute_residual_energy_coupling_by_lag",
            "private_fold_lag_band_residual_order_ledger_hash",
        ):
            self.assertNotIn(private_key, serialized)

    def test_omnibus_aggregate_is_preserved_exactly(self) -> None:
        result = self._evaluate()
        for key in (
            "evaluated_lags",
            "omnibus_band_lags",
            "maximum_evaluated_lag",
            "maximum_allowed_lag_band_quadratic_energy",
            "maximum_observed_lag_band_quadratic_energy",
            "fold_count",
            "unstable_identity_count",
        ):
            self.assertEqual(result[key], self.omnibus_gate_v1[key])

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

    def test_verifier_rejects_resealed_v7_tamper(self) -> None:
        result = self._evaluate()
        tampered = deepcopy(result)
        tampered.pop("gate_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_and_coverage_are_exact(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["evaluated_lags"], list(EVALUATED_LAGS))
        self.assertEqual(result["omnibus_band_lags"], list(OMNIBUS_BAND_LAGS))
        self.assertEqual(result["maximum_evaluated_lag"], 6)


if __name__ == "__main__":
    unittest.main()
