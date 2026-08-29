from __future__ import annotations

import json
import unittest
from copy import deepcopy

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6 import (
    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7 import (
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    _cross_bindings_match,
    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7
    as v7_tests,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6
    as consumer_v6_tests,
)


class StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV7Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        V7Case = v7_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV7Tests
        self.case = V7Case(unittest.defaultTestLoader.getTestCaseNames(V7Case)[0])
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

        source_values = self.case._values()
        self.precommit_gate_v7 = self.case._evaluate()
        self.report_consumer_v5 = self._build_report_consumer_v5(source_values)
        self.report_consumer_v6 = self._build_report_consumer_v6(
            source_values,
            self.report_consumer_v5,
        )

    @staticmethod
    def _consumer_v6_documents(values: dict[str, object]) -> dict[str, object]:
        return {
            "precommit_gate_v5": values["precommit_gate_v5"],
            "residual_order_gate_v3": values["residual_order_gate_v3"],
            "precommit_gate_v4": values["precommit_gate_v4"],
            "residual_order_gate_v2": values["residual_order_gate_v2"],
            "precommit_gate_v3": values["precommit_gate_v3"],
            "residual_order_gate_v1": values["residual_order_gate_v1"],
            "precommit_gate_v2": values["precommit_gate_v2"],
            "residual_energy_gate": values["residual_energy_gate"],
            "precommit_gate_v1": values["precommit_gate_v1"],
            "beta_stability_gate": values["beta_stability_gate"],
            "precommit_declaration": values["precommit_declaration"],
            "source_report": values["report"],
            "replay": values["replay"],
            "residualization_registration": values[
                "residualization_registration"
            ],
            "calibration_observations": values["calibration_observations"],
        }

    @classmethod
    def _build_report_consumer_v5(
        cls,
        values: dict[str, object],
    ) -> dict[str, object]:
        documents = cls._consumer_v6_documents(values)
        ConsumerV6Case = consumer_v6_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV6Tests
        return ConsumerV6Case._v5_consumer(documents)

    @classmethod
    def _build_report_consumer_v6(
        cls,
        values: dict[str, object],
        report_consumer_v5: dict[str, object],
    ) -> dict[str, object]:
        consumer_values = {
            "precommit_gate_v6": values["precommit_gate_v6"],
            "report_consumer_v5": report_consumer_v5,
            **cls._consumer_v6_documents(values),
        }
        ConsumerV6Case = consumer_v6_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV6Tests
        return consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
            **consumer_values,
            **ConsumerV6Case._expected(consumer_values),
        )

    def _values(self) -> dict[str, object]:
        return {
            "precommit_gate_v7": self.precommit_gate_v7,
            "report_consumer_v6": self.report_consumer_v6,
            "report_consumer_v5": self.report_consumer_v5,
            **self.case._values(),
        }

    def _expected(self, values: dict[str, object]) -> dict[str, object]:
        baseline = self._values()
        specs = {
            "precommit_gate_v7": ("expected_precommit_gate_v7_hash", "gate_hash"),
            "report_consumer_v6": (
                "expected_report_consumer_v6_hash",
                "verification_hash",
            ),
            "precommit_gate_v6": ("expected_precommit_gate_v6_hash", "gate_hash"),
            "omnibus_gate_v1": ("expected_omnibus_gate_v1_hash", "gate_hash"),
            "report_consumer_v5": (
                "expected_report_consumer_v5_hash",
                "verification_hash",
            ),
            "precommit_gate_v5": ("expected_precommit_gate_v5_hash", "gate_hash"),
            "residual_order_gate_v3": (
                "expected_residual_order_gate_v3_hash",
                "gate_hash",
            ),
            "precommit_gate_v4": ("expected_precommit_gate_v4_hash", "gate_hash"),
            "residual_order_gate_v2": (
                "expected_residual_order_gate_v2_hash",
                "gate_hash",
            ),
            "precommit_gate_v3": ("expected_precommit_gate_v3_hash", "gate_hash"),
            "residual_order_gate_v1": (
                "expected_residual_order_gate_v1_hash",
                "gate_hash",
            ),
            "precommit_gate_v2": ("expected_precommit_gate_v2_hash", "gate_hash"),
            "residual_energy_gate": (
                "expected_residual_energy_gate_hash",
                "gate_hash",
            ),
            "precommit_gate_v1": ("expected_precommit_gate_v1_hash", "gate_hash"),
            "beta_stability_gate": (
                "expected_beta_stability_gate_hash",
                "gate_hash",
            ),
            "precommit_declaration": (
                "expected_declaration_hash",
                "declaration_hash",
            ),
            "report": ("expected_report_hash", "verification_hash"),
            "replay": ("expected_replay_hash", "receipt_hash"),
            "residualization_registration": (
                "expected_registration_hash",
                "registration_hash",
            ),
            "calibration_observations": (
                "expected_calibration_observations_hash",
                "calibration_observations_hash",
            ),
        }
        expected: dict[str, object] = {}
        for key, (expected_key, hash_key) in specs.items():
            candidate = values.get(key)
            if not isinstance(candidate, dict) or not isinstance(
                candidate.get(hash_key), str
            ):
                candidate = baseline[key]
            expected[expected_key] = candidate[hash_key]
        return expected

    def _consume(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
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
        return consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
            **values,
            **expected,
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
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
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7(
            document,
            **values,
            **expected,
        )

    def _materialize_context(
        self,
        source: dict[str, object],
    ) -> dict[str, object]:
        values = {
            key: value
            for key, value in source.items()
            if not key.startswith("expected_")
        }
        precommit_gate_v7 = self.case._evaluate(**source)
        report_consumer_v5 = self._build_report_consumer_v5(values)
        report_consumer_v6 = self._build_report_consumer_v6(
            values,
            report_consumer_v5,
        )
        materialized = {
            **values,
            "precommit_gate_v7": precommit_gate_v7,
            "report_consumer_v6": report_consumer_v6,
            "report_consumer_v5": report_consumer_v5,
        }
        return {**materialized, **self._expected(materialized)}

    def _omnibus_block_context(self) -> dict[str, object]:
        return self._materialize_context(
            self.case._shared_context([1, 1, -1, 1, 1, 1, -1, -1, 1, 1])
        )

    def _v6_block_context(self) -> dict[str, object]:
        return self._materialize_context(self.case._v6_block_context())

    def test_dual_positive_sources_are_verified_local_binding(self) -> None:
        result = self._consume()
        self.assertEqual(result["verification_state"], "VERIFIED_LOCAL_BINDING")
        self.assertTrue(result["facts"]["precommit_gate_v7_verified"])
        self.assertTrue(result["facts"]["report_consumer_v6_verified"])
        self.assertTrue(self._verify(result))

    def test_omnibus_block_overrides_positive_v6_consumer(self) -> None:
        context = self._omnibus_block_context()
        result = self._consume(**context)
        self.assertEqual(
            context["report_consumer_v6"]["verification_state"],
            "VERIFIED_LOCAL_BINDING",
        )
        self.assertEqual(result["verification_state"], "VERIFIED_BLOCK")
        self.assertEqual(
            result["source_report_consumer_v6_state"],
            "VERIFIED_LOCAL_BINDING",
        )
        self.assertTrue(self._verify(result, **context))

    def test_v6_block_is_monotone(self) -> None:
        context = self._v6_block_context()
        result = self._consume(**context)
        self.assertEqual(
            context["report_consumer_v6"]["verification_state"],
            "VERIFIED_BLOCK",
        )
        self.assertEqual(result["verification_state"], "VERIFIED_BLOCK")
        self.assertFalse(result["facts"]["source_gate_block_relaxed"])

    def test_missing_sources_are_unknown(self) -> None:
        for key in ("precommit_gate_v7", "report_consumer_v6"):
            with self.subTest(key=key):
                self.assertEqual(
                    self._consume(**{key: None})["verification_state"],
                    "UNKNOWN",
                )

    def test_unsupported_sources_are_distinct(self) -> None:
        unsupported_gate = self._consume(
            precommit_gate_v7={"schema_version": "legacy"}
        )
        self.assertEqual(unsupported_gate["source_state"], "UNSUPPORTED")
        unsupported_consumer = self._consume(
            report_consumer_v6={"schema_version": "legacy"}
        )
        self.assertEqual(unsupported_consumer["source_state"], "UNSUPPORTED")

    def test_expected_top_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v7_hash",
            "expected_report_consumer_v6_hash",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self._consume(**{key: "0" * 64})["verification_state"],
                    "UNKNOWN",
                )

    def test_expected_context_hashes_are_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v6_hash",
            "expected_omnibus_gate_v1_hash",
            "expected_report_consumer_v5_hash",
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
                    self._consume(**{key: "0" * 64})["verification_state"],
                    "UNKNOWN",
                )

    def test_resealed_v7_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v7)
        source.pop("gate_hash")
        source["gate_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "gate_hash")
        result = self._consume(
            precommit_gate_v7=source,
            expected_precommit_gate_v7_hash=source["gate_hash"],
        )
        self.assertEqual(result["verification_reason"], "SOURCE_OR_CONTEXT_INVALID")

    def test_resealed_v6_consumer_tamper_is_invalid(self) -> None:
        source = deepcopy(self.report_consumer_v6)
        source.pop("verification_hash")
        source["verification_reason"] = "RESEALED_DRIFT"
        source = seal_strict_canonical_document(source, "verification_hash")
        result = self._consume(
            report_consumer_v6=source,
            expected_report_consumer_v6_hash=source["verification_hash"],
        )
        self.assertEqual(result["verification_reason"], "SOURCE_OR_CONTEXT_INVALID")

    def test_complete_context_is_bound(self) -> None:
        alternate = self._omnibus_block_context()
        result = self._consume(
            precommit_gate_v7=alternate["precommit_gate_v7"],
            report_consumer_v6=alternate["report_consumer_v6"],
            expected_precommit_gate_v7_hash=alternate[
                "expected_precommit_gate_v7_hash"
            ],
            expected_report_consumer_v6_hash=alternate[
                "expected_report_consumer_v6_hash"
            ],
        )
        self.assertEqual(result["verification_state"], "UNKNOWN")

    def test_cross_consumer_hash_mismatch_is_detected(self) -> None:
        consumer = deepcopy(self.report_consumer_v6)
        consumer["source_precommit_gate_v5_hash"] = "0" * 64
        expected = self._expected(self._values())
        self.assertFalse(
            _cross_bindings_match(
                self.precommit_gate_v7,
                consumer,
                self.case.precommit_gate_v6,
                self.case.omnibus_gate_v1,
                self.report_consumer_v5,
                expected_precommit_gate_v6_hash=expected[
                    "expected_precommit_gate_v6_hash"
                ],
                expected_omnibus_gate_v1_hash=expected[
                    "expected_omnibus_gate_v1_hash"
                ],
                expected_report_consumer_v5_hash=expected[
                    "expected_report_consumer_v5_hash"
                ],
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

    def test_public_six_lag_aggregate_is_exact(self) -> None:
        result = self._consume()
        for key in (
            "evaluated_lags",
            "omnibus_band_lags",
            "maximum_evaluated_lag",
            "maximum_allowed_lag_band_quadratic_energy",
            "maximum_observed_lag_band_quadratic_energy",
            "fold_count",
            "unstable_identity_count",
        ):
            self.assertEqual(result[key], self.precommit_gate_v7[key])

    def test_public_report_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._consume(), sort_keys=True)
        for private_key in (
            '"rows"',
            '"returns"',
            '"beta_by_identity"',
            '"phase_comb"',
            "absolute_residual_energy_coupling_by_lag",
            "private_fold_lag_band_residual_order_ledger_hash",
        ):
            self.assertNotIn(private_key, serialized)

    def test_authority_and_independence_are_locked(self) -> None:
        result = self._consume()
        self.assertFalse(result["facts"]["residual_order_independence_proven"])
        for key, value in result["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_blockers_are_deduplicated(self) -> None:
        blockers = self._consume()["blockers"]
        self.assertEqual(len(blockers), len(set(blockers)))

    def test_determinism(self) -> None:
        self.assertEqual(self._consume(), self._consume())

    def test_verifier_rejects_resealed_consumer_tamper(self) -> None:
        result = self._consume()
        tampered = deepcopy(result)
        tampered.pop("verification_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "verification_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_and_coverage_are_exact(self) -> None:
        result = self._consume()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["evaluated_lags"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(result["omnibus_band_lags"], [4, 5, 6])
        self.assertEqual(result["maximum_evaluated_lag"], 6)


if __name__ == "__main__":
    unittest.main()
