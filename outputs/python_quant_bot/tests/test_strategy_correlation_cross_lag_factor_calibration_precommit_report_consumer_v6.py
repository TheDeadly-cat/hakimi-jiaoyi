from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5 import (
    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6 import (
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6 as v6_tests


class StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV6Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        V6Case = v6_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV6Tests
        self.case = V6Case(unittest.defaultTestLoader.getTestCaseNames(V6Case)[0])
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.precommit_gate_v6 = self.case._evaluate()
        self.report_consumer_v5 = self._v5_consumer(self._base_documents())

    def _base_documents(self) -> dict[str, object]:
        return {
            "precommit_gate_v5": self.case.precommit_gate_v5,
            "residual_order_gate_v3": self.case.residual_order_gate_v3,
            "precommit_gate_v4": self.case.precommit_gate_v4,
            "residual_order_gate_v2": self.case.residual_order_gate_v2,
            "precommit_gate_v3": self.case.precommit_gate_v3,
            "residual_order_gate_v1": self.case.residual_order_gate_v1,
            "precommit_gate_v2": self.case.precommit_gate_v2,
            "residual_energy_gate": self.case.residual_energy_gate,
            "precommit_gate_v1": self.case.precommit_gate_v1,
            "beta_stability_gate": self.case.beta_stability_gate,
            "precommit_declaration": self.case.declaration,
            "source_report": self.case.report,
            "replay": self.case.replay,
            "residualization_registration": self.case.registration,
            "calibration_observations": self.case.observations,
        }

    @staticmethod
    def _v5_consumer(values: dict[str, object]) -> dict[str, object]:
        return consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
            values["precommit_gate_v5"],
            values["precommit_gate_v4"],
            values["residual_order_gate_v2"],
            values["precommit_gate_v3"],
            values["residual_order_gate_v1"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["precommit_declaration"],
            values["source_report"],
            values["replay"],
            values["residualization_registration"],
            values["calibration_observations"],
            expected_precommit_gate_v5_hash=values["precommit_gate_v5"]["gate_hash"],
            expected_precommit_gate_v4_hash=values["precommit_gate_v4"]["gate_hash"],
            expected_residual_order_gate_v2_hash=values["residual_order_gate_v2"]["gate_hash"],
            expected_precommit_gate_v3_hash=values["precommit_gate_v3"]["gate_hash"],
            expected_residual_order_gate_v1_hash=values["residual_order_gate_v1"]["gate_hash"],
            expected_precommit_gate_v2_hash=values["precommit_gate_v2"]["gate_hash"],
            expected_residual_energy_gate_hash=values["residual_energy_gate"]["gate_hash"],
            expected_precommit_gate_v1_hash=values["precommit_gate_v1"]["gate_hash"],
            expected_beta_stability_gate_hash=values["beta_stability_gate"]["gate_hash"],
            expected_declaration_hash=values["precommit_declaration"]["declaration_hash"],
            expected_source_report_hash=values["source_report"]["verification_hash"],
            expected_replay_hash=values["replay"]["receipt_hash"],
            expected_registration_hash=values["residualization_registration"]["registration_hash"],
            expected_calibration_observations_hash=values["calibration_observations"]["calibration_observations_hash"],
        )

    @staticmethod
    def _expected(values: dict[str, object]) -> dict[str, object]:
        return {
            "expected_precommit_gate_v6_hash": values["precommit_gate_v6"]["gate_hash"],
            "expected_report_consumer_v5_hash": values["report_consumer_v5"]["verification_hash"],
            "expected_precommit_gate_v5_hash": values["precommit_gate_v5"]["gate_hash"],
            "expected_residual_order_gate_v3_hash": values["residual_order_gate_v3"]["gate_hash"],
            "expected_precommit_gate_v4_hash": values["precommit_gate_v4"]["gate_hash"],
            "expected_residual_order_gate_v2_hash": values["residual_order_gate_v2"]["gate_hash"],
            "expected_precommit_gate_v3_hash": values["precommit_gate_v3"]["gate_hash"],
            "expected_residual_order_gate_v1_hash": values["residual_order_gate_v1"]["gate_hash"],
            "expected_precommit_gate_v2_hash": values["precommit_gate_v2"]["gate_hash"],
            "expected_residual_energy_gate_hash": values["residual_energy_gate"]["gate_hash"],
            "expected_precommit_gate_v1_hash": values["precommit_gate_v1"]["gate_hash"],
            "expected_beta_stability_gate_hash": values["beta_stability_gate"]["gate_hash"],
            "expected_declaration_hash": values["precommit_declaration"]["declaration_hash"],
            "expected_source_report_hash": values["source_report"]["verification_hash"],
            "expected_replay_hash": values["replay"]["receipt_hash"],
            "expected_registration_hash": values["residualization_registration"]["registration_hash"],
            "expected_calibration_observations_hash": values["calibration_observations"]["calibration_observations_hash"],
        }

    def _values(self) -> dict[str, object]:
        return {
            "precommit_gate_v6": self.precommit_gate_v6,
            "report_consumer_v5": self.report_consumer_v5,
            **self._base_documents(),
        }

    def _consume(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        values = {key: value for key, value in values.items() if not key.startswith("expected_")}
        return consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
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
        args = [
            values.pop("precommit_gate_v6"),
            values.pop("report_consumer_v5"),
            values.pop("precommit_gate_v5"),
            values.pop("residual_order_gate_v3"),
            values.pop("precommit_gate_v4"),
            values.pop("residual_order_gate_v2"),
            values.pop("precommit_gate_v3"),
            values.pop("residual_order_gate_v1"),
            values.pop("precommit_gate_v2"),
            values.pop("residual_energy_gate"),
            values.pop("precommit_gate_v1"),
            values.pop("beta_stability_gate"),
            values.pop("precommit_declaration"),
            values.pop("source_report"),
            values.pop("replay"),
            values.pop("residualization_registration"),
            values.pop("calibration_observations"),
        ]
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6(
            document,
            *args,
            **expected,
        )

    def _context(self, kind: str) -> dict[str, object]:
        source = (
            self.case._lag_three_block_context()
            if kind == "v3"
            else self.case._v5_block_context()
        )
        documents = {
            key: value
            for key, value in source.items()
            if not key.startswith("expected_")
        }
        documents["source_report"] = documents.pop("report")
        gate_v6 = self.case._evaluate(**source)
        consumer_v5 = self._v5_consumer(documents)
        values = {
            "precommit_gate_v6": gate_v6,
            "report_consumer_v5": consumer_v5,
            **documents,
        }
        return {**values, **self._expected(values)}

    def test_positive_source_is_verified_local_binding(self) -> None:
        result = self._consume()
        self.assertEqual(result["verification_state"], "VERIFIED_LOCAL_BINDING")
        self.assertTrue(result["facts"]["precommit_gate_v6_verified"])
        self.assertTrue(result["facts"]["report_consumer_v5_verified"])
        self.assertTrue(self._verify(result))

    def test_v3_block_is_verified_block(self) -> None:
        context = self._context("v3")
        result = self._consume(**context)
        self.assertEqual(result["verification_state"], "VERIFIED_BLOCK")
        self.assertEqual(result["source_v5_consumer_state"], "VERIFIED_LOCAL_BINDING")
        self.assertTrue(self._verify(result, **context))

    def test_v5_block_is_verified_block(self) -> None:
        context = self._context("v5")
        result = self._consume(**context)
        self.assertEqual(result["verification_state"], "VERIFIED_BLOCK")

    def test_missing_sources_are_unknown(self) -> None:
        for key in ("precommit_gate_v6", "report_consumer_v5"):
            with self.subTest(key=key):
                values = self._values()
                expected = self._expected(values)
                values[key] = None
                self.assertEqual(
                    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
                        **values,
                        **expected,
                    )["verification_state"],
                    "UNKNOWN",
                )

    def test_unsupported_sources_are_distinct(self) -> None:
        values = self._values()
        expected = self._expected(values)
        values["precommit_gate_v6"] = {"schema_version": "legacy"}
        self.assertEqual(
            consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
                **values,
                **expected,
            )["source_state"],
            "UNSUPPORTED",
        )

    def test_expected_top_hashes_are_bound(self) -> None:
        for key in ("expected_precommit_gate_v6_hash", "expected_report_consumer_v5_hash"):
            with self.subTest(key=key):
                self.assertEqual(self._consume(**{key: "0" * 64})["verification_state"], "UNKNOWN")

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v5_hash",
            "expected_residual_order_gate_v3_hash",
            "expected_residual_order_gate_v2_hash",
            "expected_residual_order_gate_v1_hash",
            "expected_replay_hash",
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            with self.subTest(key=key):
                self.assertEqual(self._consume(**{key: "0" * 64})["verification_state"], "UNKNOWN")

    def test_resealed_v6_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v6)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._consume(
            precommit_gate_v6=source,
            expected_precommit_gate_v6_hash=source["gate_hash"],
        )
        self.assertEqual(result["verification_reason"], "SOURCE_OR_CONTEXT_INVALID")

    def test_resealed_v5_consumer_tamper_is_invalid(self) -> None:
        source = deepcopy(self.report_consumer_v5)
        source.pop("verification_hash")
        source["verification_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "verification_hash")
        result = self._consume(
            report_consumer_v5=source,
            expected_report_consumer_v5_hash=source["verification_hash"],
        )
        self.assertEqual(result["verification_reason"], "SOURCE_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        context = self._context("v3")
        result = self._consume(
            precommit_gate_v6=context["precommit_gate_v6"],
            report_consumer_v5=context["report_consumer_v5"],
            expected_precommit_gate_v6_hash=context["expected_precommit_gate_v6_hash"],
            expected_report_consumer_v5_hash=context["expected_report_consumer_v5_hash"],
        )
        self.assertEqual(result["verification_state"], "UNKNOWN")

    def test_public_three_lag_aggregate_is_exact(self) -> None:
        result = self._consume()
        source = self.case.residual_order_gate_v3
        self.assertEqual(result["evaluated_lags"], [1, 2, 3])
        self.assertEqual(result["maximum_evaluated_lag"], 3)
        self.assertEqual(
            result["maximum_observed_absolute_three_lag_residual_energy_coupling"],
            source["maximum_observed_absolute_three_lag_residual_energy_coupling"],
        )

    def test_public_report_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._consume(), sort_keys=True)
        for private_key in ('"rows"', '"returns"', '"beta_by_identity"', '"phase_comb"'):
            self.assertNotIn(private_key, serialized)

    def test_authority_and_independence_are_locked(self) -> None:
        result = self._consume()
        self.assertFalse(result["facts"]["residual_order_independence_proven"])
        for key, value in result["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_determinism(self) -> None:
        self.assertEqual(self._consume(), self._consume())

    def test_verifier_rejects_resealed_consumer_tamper(self) -> None:
        result = self._consume()
        tampered = deepcopy(result)
        tampered.pop("verification_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "verification_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_and_fingerprint_are_exact(self) -> None:
        result = self._consume()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
