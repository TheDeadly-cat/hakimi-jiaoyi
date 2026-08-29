from __future__ import annotations

from copy import deepcopy
import math
import random
import socket
import sqlite3
import time
import unittest
from unittest.mock import patch
import uuid

import exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic as diagnostic
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests.test_strategy_correlation_cross_lag_gate import (
    StrategyCorrelationCrossLagGateTests,
)


class StrategyCorrelationCrossLagFactorConditionalDiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = StrategyCorrelationCrossLagGateTests(
            methodName="test_evaluation_is_deterministic"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def _registration(self, identities, betas=None, **overrides):
        if betas is None:
            betas = {identity: "1" for identity in identities}
        payload = {
            "schema_version": diagnostic.REGISTRATION_SCHEMA,
            "static_fingerprint": diagnostic.REGISTRATION_STATIC_FINGERPRINT,
            "factor_id": "COMMON-FACTOR-1",
            "factor_source_hash": "a" * 64,
            "calibration_receipt_hash": "b" * 64,
            "identity_order_hash": strict_canonical_hash(identities),
            "identity_order": list(identities),
            "beta_by_identity": dict(betas),
            "calibration_cutoff_date": "2025-01-01",
            "selection_cutoff_date": "2025-02-01",
            "exposure_estimator": "FROZEN_PRE_EVALUATION_OLS_V1",
            "intercept_policy": "NO_INTERCEPT_RETURN_RESIDUAL_V1",
            "factor_policy": "CONTEMPORANEOUS_SINGLE_FACTOR_V1",
            "missing_policy": "FAIL_CLOSED",
        }
        payload.update(overrides)
        return seal_strict_canonical_document(payload, "registration_hash")

    def _factor_document(self, raw_rows, factor_values, registration, **overrides):
        rows = [
            {
                "sequence_number": row["sequence_number"],
                "observation_id": row["observation_id"],
                "factor_return": factor_values[index],
            }
            for index, row in enumerate(raw_rows)
        ]
        payload = {
            "schema_version": diagnostic.FACTOR_OBSERVATION_SCHEMA,
            "factor_id": registration["factor_id"],
            "factor_source_hash": registration["factor_source_hash"],
            "rows": rows,
        }
        payload.update(overrides)
        return seal_strict_canonical_document(payload, "factor_observations_hash")

    def _context(self, series, factor_values, betas=None, prefix="obs"):
        identities = list(series)
        raw_rows = self.fixture._rows(series, prefix=prefix)
        registration = self._registration(identities, betas=betas)
        factor_document = self._factor_document(
            raw_rows,
            factor_values,
            registration,
        )
        return {
            "preregistered_strata": dict(self.fixture.strata),
            "aligned_observations": raw_rows,
            "residualization_registration": registration,
            "factor_observations": factor_document,
            "expected_stratum_assignment_hash": self.fixture.strata_hash,
            "expected_registration_hash": registration["registration_hash"],
            "expected_factor_observations_hash": factor_document[
                "factor_observations_hash"
            ],
        }

    def _evaluate(self, context):
        return diagnostic.evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic(
            **context
        )

    def _verify(self, document, context):
        return diagnostic.verify_strategy_correlation_cross_lag_factor_conditional_diagnostic(
            document,
            **context,
        )

    def _common_factor_case(self, *, direct_residual=False):
        count = 1000
        rng = random.Random(20260822 if direct_residual else 20260821)
        factor = 0.0
        factors = []
        left = []
        right = []
        previous_left = 0.0
        for _ in range(count):
            factor = 0.90 * factor + rng.gauss(0.0, 1.0)
            if direct_residual:
                current_left = rng.gauss(0.0, 0.65)
                current_right = 0.96 * previous_left + rng.gauss(0.0, 0.06)
                previous_left = current_left
            else:
                current_left = rng.gauss(0.0, 0.04)
                current_right = rng.gauss(0.0, 0.04)
            factors.append(factor)
            left.append(current_left)
            right.append(current_right)
        series = {
            "A": [factors[index] + left[index] for index in range(count)],
            "B": [factors[index] + right[index] for index in range(count)],
        }
        return self._context(series, factors)

    def test_versioned_contract_is_exact(self) -> None:
        self.assertEqual(
            diagnostic.DIAGNOSTIC_SCHEMA,
            "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1",
        )
        self.assertEqual(
            diagnostic.STATIC_FINGERPRINT,
            "20260822-cross-lag-factor-conditional-diagnostic-1",
        )

    def test_common_factor_only_preserves_raw_block(self) -> None:
        context = self._common_factor_case()
        document = self._evaluate(context)
        self.assertEqual(document["raw_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(document["residual_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(
            document["diagnostic_state"], "COMMON_FACTOR_MEDIATED_CANDIDATE"
        )
        self.assertEqual(document["blockers"][0], "RAW_C0_BLOCK_PRESERVED")
        self.assertIs(document["facts"]["raw_block_relaxed"], False)

    def test_direct_residual_lag_remains_blocked(self) -> None:
        context = self._common_factor_case(direct_residual=True)
        document = self._evaluate(context)
        self.assertEqual(document["raw_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(document["residual_evaluation"]["gate_decision"], "BLOCK")
        self.assertGreater(document["residual_evaluation"]["dependent_test_count"], 0)
        self.assertEqual(
            document["diagnostic_state"],
            "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
        )

    def test_independent_raw_and_residual_series_remain_candidate_only(self) -> None:
        series = self.fixture._independent_series(192)
        factors = [math.sin(index / 9.0) for index in range(192)]
        context = self._context(series, factors, betas={"A": "0", "B": "0"})
        document = self._evaluate(context)
        self.assertEqual(document["raw_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(document["residual_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(
            document["diagnostic_state"], "NO_CONDITIONAL_DEPENDENCE_DETECTED"
        )
        self.assertIs(document["authority"]["residual_independence_proven"], False)

    def test_suppression_or_model_instability_is_a_blocker(self) -> None:
        count = 1000
        rng = random.Random(20260823)
        left = [rng.gauss(0.0, 1.0) for _ in range(count)]
        right = [rng.gauss(0.0, 0.04) for _ in range(count)]
        factors = [0.0] + left[:-1]
        context = self._context(
            {"A": left, "B": right},
            factors,
            betas={"A": "0", "B": "1"},
        )
        document = self._evaluate(context)
        self.assertEqual(document["raw_evaluation"]["gate_decision"], "PASS")
        self.assertEqual(document["residual_evaluation"]["gate_decision"], "BLOCK")
        self.assertEqual(
            document["diagnostic_state"],
            "SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY",
        )
        self.assertIn("SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY", document["blockers"])

    def test_valid_documents_exactly_verify(self) -> None:
        for context in (
            self._common_factor_case(),
            self._common_factor_case(direct_residual=True),
        ):
            with self.subTest(direct=context is not None):
                document = self._evaluate(context)
                self.assertTrue(self._verify(document, context))

    def test_registration_hash_and_expected_hash_are_bound(self) -> None:
        context = self._common_factor_case()
        for mutation in ("document", "expected"):
            with self.subTest(mutation=mutation):
                changed = deepcopy(context)
                if mutation == "document":
                    changed["residualization_registration"]["factor_id"] = "OTHER"
                else:
                    changed["expected_registration_hash"] = "0" * 64
                self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_noncanonical_beta_forms_fail_closed(self) -> None:
        context = self._common_factor_case()
        invalid_values = (True, 1, "1.0", "1e0", "NaN", "11", "-0", " 1")
        for value in invalid_values:
            with self.subTest(value=repr(value)):
                changed = deepcopy(context)
                registration = dict(changed["residualization_registration"])
                registration.pop("registration_hash")
                registration["beta_by_identity"] = {"A": value, "B": "1"}
                registration = seal_strict_canonical_document(
                    registration,
                    "registration_hash",
                )
                changed["residualization_registration"] = registration
                changed["expected_registration_hash"] = registration[
                    "registration_hash"
                ]
                self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_identity_and_calibration_timing_mismatch_fail_closed(self) -> None:
        context = self._common_factor_case()
        mutations = (
            ("identity_order", ["B", "A"]),
            ("calibration_cutoff_date", "2025-02-01"),
            ("selection_cutoff_date", "2025-01-01"),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                changed = deepcopy(context)
                registration = dict(changed["residualization_registration"])
                registration.pop("registration_hash")
                registration[key] = value
                registration = seal_strict_canonical_document(
                    registration,
                    "registration_hash",
                )
                changed["residualization_registration"] = registration
                changed["expected_registration_hash"] = registration[
                    "registration_hash"
                ]
                self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_factor_alignment_hash_and_variance_fail_closed(self) -> None:
        context = self._common_factor_case()
        variants = []
        missing = deepcopy(context["factor_observations"])
        missing["rows"] = missing["rows"][:-1]
        variants.append(missing)
        reordered = deepcopy(context["factor_observations"])
        reordered["rows"][0], reordered["rows"][1] = (
            reordered["rows"][1], reordered["rows"][0]
        )
        variants.append(reordered)
        zero_variance = deepcopy(context["factor_observations"])
        for row in zero_variance["rows"]:
            row["factor_return"] = 0.0
        variants.append(zero_variance)
        nonfinite = deepcopy(context["factor_observations"])
        nonfinite["rows"][4]["factor_return"] = float("nan")
        nonfinite_payload = dict(nonfinite)
        nonfinite_payload.pop("factor_observations_hash")
        with self.assertRaisesRegex(ValueError, "strict_canonical_json_invalid"):
            seal_strict_canonical_document(
                nonfinite_payload,
                "factor_observations_hash",
            )
        changed = deepcopy(context)
        changed["factor_observations"] = nonfinite
        self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")
        for index, variant in enumerate(variants):
            with self.subTest(index=index):
                changed = deepcopy(context)
                unsealed = dict(variant)
                unsealed.pop("factor_observations_hash")
                resealed = seal_strict_canonical_document(
                    unsealed,
                    "factor_observations_hash",
                )
                changed["factor_observations"] = resealed
                changed["expected_factor_observations_hash"] = resealed[
                    "factor_observations_hash"
                ]
                self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_factor_observation_id_mismatch_fails_closed(self) -> None:
        context = self._common_factor_case()
        changed = deepcopy(context)
        unsealed = dict(changed["factor_observations"])
        unsealed.pop("factor_observations_hash")
        unsealed["rows"][7]["observation_id"] = "other-007"
        resealed = seal_strict_canonical_document(
            unsealed,
            "factor_observations_hash",
        )
        changed["factor_observations"] = resealed
        changed["expected_factor_observations_hash"] = resealed[
            "factor_observations_hash"
        ]
        self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_c0_builder_and_verifier_fail_closed(self) -> None:
        context = self._common_factor_case()
        with patch.object(
            diagnostic,
            "evaluate_strategy_correlation_cross_lag_gate",
            side_effect=RuntimeError("synthetic C0 failure"),
        ):
            self.assertEqual(self._evaluate(context)["diagnostic_state"], "UNKNOWN")
        for alias in (False, 1, "true", {}, []):
            with self.subTest(alias=repr(alias)), patch.object(
                diagnostic,
                "verify_strategy_correlation_cross_lag_evaluation",
                return_value=alias,
            ):
                self.assertEqual(self._evaluate(context)["diagnostic_state"], "UNKNOWN")

    def test_output_is_aggregate_only_and_authority_locked(self) -> None:
        document = self._evaluate(self._common_factor_case(direct_residual=True))
        serialized = repr(document).lower()
        for forbidden in (
            "beta_by_identity",
            "factor_return",
            "returns",
            "observation_id",
            "sequence_number",
            "aligned_observations",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertIs(document["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_context_mismatch_and_extra_source_field_reject(self) -> None:
        context = self._common_factor_case()
        document = self._evaluate(context)
        changed = deepcopy(context)
        changed["expected_factor_observations_hash"] = "0" * 64
        self.assertFalse(self._verify(document, changed))
        changed = deepcopy(context)
        changed["factor_observations"]["raw_path"] = "C:/secret"
        self.assertEqual(self._evaluate(changed)["diagnostic_state"], "UNKNOWN")

    def test_real_nonzero_raw_and_residual_tamper_reject(self) -> None:
        context = self._common_factor_case(direct_residual=True)
        document = self._evaluate(context)
        self.assertGreater(document["raw_evaluation"]["dependent_test_count"], 0)
        self.assertGreater(
            document["residual_evaluation"]["dependent_test_count"], 0
        )
        for view in ("raw_evaluation", "residual_evaluation"):
            with self.subTest(view=view):
                unsealed = deepcopy(document)
                unsealed.pop("diagnostic_hash")
                unsealed[view]["dependent_test_count"] += 1
                tampered = seal_strict_canonical_document(
                    unsealed,
                    "diagnostic_hash",
                )
                self.assertFalse(self._verify(tampered, context))

    def test_denied_io_and_nondeterminism_are_unused(self) -> None:
        context = self._common_factor_case()
        denied = AssertionError("denied side effect")
        with patch("builtins.open", side_effect=denied), patch.object(
            socket, "socket", side_effect=denied
        ), patch.object(sqlite3, "connect", side_effect=denied), patch.object(
            time, "time", side_effect=denied
        ), patch.object(random, "random", side_effect=denied), patch.object(
            uuid, "uuid4", side_effect=denied
        ):
            document = self._evaluate(context)
            self.assertEqual(
                document["diagnostic_state"], "COMMON_FACTOR_MEDIATED_CANDIDATE"
            )
            self.assertTrue(self._verify(document, context))

    def test_verifier_exception_never_escapes(self) -> None:
        context = self._common_factor_case()
        document = self._evaluate(context)
        with patch.object(
            diagnostic,
            "evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic",
            side_effect=RuntimeError("synthetic diagnostic failure"),
        ):
            self.assertFalse(self._verify(document, context))


if __name__ == "__main__":
    unittest.main()
