from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_matrix_geometry_gate_v1 as geometry_gate_module
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_matrix_contract,
    verify_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_gate_v1 import (
    GATE_CONTRACT_HASH,
    MAXIMUM_DIMENSION,
    build_strategy_correlation_matrix_geometry_preregistration_v1,
    evaluate_strategy_correlation_matrix_geometry_gate_v1,
    verify_strategy_correlation_matrix_geometry_gate_v1,
    verify_strategy_correlation_matrix_geometry_preregistration_v1,
)


class CorrelationMatrixGeometryGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = ["AAA", "BBB", "CCC"]
        self.preregistration = build_strategy_correlation_matrix_geometry_preregistration_v1(
            self.symbols
        )
        self.expected_preregistration_hash = self.preregistration[
            "preregistration_hash"
        ]

    def _matrix(self, ab, ac, bc):
        return build_correlation_matrix_contract(
            self.symbols,
            {
                ("AAA", "BBB"): ab,
                ("AAA", "CCC"): ac,
                ("BBB", "CCC"): bc,
            },
            overlap_observations=60,
        )

    def _evaluate(self, matrix):
        return evaluate_strategy_correlation_matrix_geometry_gate_v1(
            self.preregistration,
            matrix,
            expected_preregistration_hash=self.expected_preregistration_hash,
        )

    def test_contract_and_preregistration_hashes_are_pinned(self):
        self.assertEqual(
            GATE_CONTRACT_HASH,
            "ecefe7b0fe09edc3bb5d5b925b4acb731930b3e91af91edc8790c45cfa24b863",
        )
        self.assertEqual(
            self.expected_preregistration_hash,
            "cf84bbb32813af7a2230a9e7cdd764b4536c6010ab839ca23d4978e85df71ace",
        )

    def test_preregistration_exactly_verifies(self):
        self.assertTrue(
            verify_strategy_correlation_matrix_geometry_preregistration_v1(
                self.preregistration,
                expected_symbols=self.symbols,
                expected_preregistration_hash=self.expected_preregistration_hash,
            )
        )

    def test_thresholds_are_not_caller_overridable(self):
        self.assertFalse(
            self.preregistration["facts"]["thresholds_caller_overridable"]
        )

    def test_activation_order_precedes_cluster_consumers(self):
        order = self.preregistration["activation_order"]
        geometry = order.index("EVALUATE_MATRIX_GEOMETRY")
        self.assertLess(geometry, order.index("RUN_COMPLETE_LINK_AUDIT"))
        self.assertLess(geometry, order.index("RUN_EFFECTIVE_BET_BUDGET"))

    def test_existing_matrix_contract_passes_impossible_geometry(self):
        matrix = self._matrix(0.9, 0.9, -0.9)
        verification = verify_correlation_matrix_contract(
            matrix,
            expected_symbols=self.symbols,
        )
        self.assertEqual(verification["status"], "PASS")

    def test_impossible_pairwise_matrix_is_blocked(self):
        result = self._evaluate(self._matrix(0.9, 0.9, -0.9))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["reason_code"],
            "CORRELATION_MATRIX_NOT_POSITIVE_SEMIDEFINITE",
        )
        self.assertAlmostEqual(
            result["geometry"]["minimum_eigenvalue"],
            -0.8,
            places=12,
        )

    def test_identity_matrix_passes(self):
        result = self._evaluate(self._matrix(0.0, 0.0, 0.0))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["geometry"]["eigenvalues"], [1.0, 1.0, 1.0])

    def test_positive_equicorrelation_matrix_passes(self):
        result = self._evaluate(self._matrix(0.9, 0.9, 0.9))
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(
            result["geometry"]["minimum_eigenvalue"],
            0.1,
            places=12,
        )

    def test_rank_one_matrix_passes_with_zero_eigenvalues(self):
        result = self._evaluate(self._matrix(1.0, 1.0, 1.0))
        self.assertEqual(result["status"], "PASS")
        self.assertGreaterEqual(result["geometry"]["minimum_eigenvalue"], -1e-10)

    def test_gate_result_exactly_verifies(self):
        matrix = self._matrix(0.2, 0.3, 0.4)
        result = self._evaluate(matrix)
        self.assertTrue(
            verify_strategy_correlation_matrix_geometry_gate_v1(
                result,
                self.preregistration,
                matrix,
                expected_preregistration_hash=self.expected_preregistration_hash,
            )
        )

    def test_gate_is_deterministic(self):
        matrix = self._matrix(0.2, 0.3, 0.4)
        self.assertEqual(self._evaluate(matrix), self._evaluate(matrix))

    def test_missing_pair_becomes_unknown(self):
        matrix = self._matrix(0.2, 0.3, 0.4)
        matrix["pairs"].pop()
        result = self._evaluate(matrix)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_nonfinite_pair_becomes_unknown(self):
        matrix = self._matrix(0.2, 0.3, 0.4)
        matrix["pairs"][0]["pearson_correlation"] = float("nan")
        result = self._evaluate(matrix)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_wrong_expected_preregistration_hash_fails_closed(self):
        self.assertIsNone(
            evaluate_strategy_correlation_matrix_geometry_gate_v1(
                self.preregistration,
                self._matrix(0.0, 0.0, 0.0),
                expected_preregistration_hash="0" * 64,
            )
        )

    def test_tampered_preregistration_fails_closed(self):
        preregistration = deepcopy(self.preregistration)
        preregistration["parameters"]["psd_tolerance"] = 10.0
        self.assertIsNone(
            evaluate_strategy_correlation_matrix_geometry_gate_v1(
                preregistration,
                self._matrix(0.9, 0.9, -0.9),
                expected_preregistration_hash=self.expected_preregistration_hash,
            )
        )

    def test_gate_tamper_fails_verification(self):
        matrix = self._matrix(0.9, 0.9, -0.9)
        result = self._evaluate(matrix)
        result["status"] = "PASS"
        self.assertFalse(
            verify_strategy_correlation_matrix_geometry_gate_v1(
                result,
                self.preregistration,
                matrix,
                expected_preregistration_hash=self.expected_preregistration_hash,
            )
        )

    def test_symbol_order_drift_is_not_accepted_as_same_contract(self):
        matrix = self._matrix(0.2, 0.3, 0.4)
        matrix["symbols"] = ["BBB", "AAA", "CCC"]
        unsigned = dict(matrix)
        unsigned.pop("matrix_hash")
        matrix["matrix_hash"] = hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        with patch.object(
            geometry_gate_module,
            "verify_correlation_matrix_contract",
            return_value={"status": "PASS", "blockers": []},
        ):
            result = self._evaluate(matrix)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "SYMBOL_ORDER_MISMATCH")

    def test_preregistration_rejects_too_many_symbols(self):
        symbols = [f"S{index:02d}" for index in range(MAXIMUM_DIMENSION + 1)]
        self.assertIsNone(
            build_strategy_correlation_matrix_geometry_preregistration_v1(symbols)
        )

    def test_preregistration_rejects_duplicate_symbols(self):
        self.assertIsNone(
            build_strategy_correlation_matrix_geometry_preregistration_v1(
                ["AAA", "AAA"]
            )
        )

    def test_pass_does_not_grant_activation_authority(self):
        result = self._evaluate(self._matrix(0.0, 0.0, 0.0))
        self.assertEqual(result["status"], "PASS")
        for key in (
            "consumer_activation_authorized",
            "http_registration_authorized",
            "runtime_activation_authorized",
            "paper_authorized",
            "live_authorized",
            "profitability_claimed",
        ):
            self.assertFalse(result["authority"][key])

    def test_output_has_no_ready_or_profitability_promotion(self):
        rendered = json.dumps(
            self._evaluate(self._matrix(0.0, 0.0, 0.0)),
            sort_keys=True,
        )
        self.assertNotIn("READY", rendered)
        self.assertNotIn('"profitability_claimed": true', rendered)

    def test_blocked_geometry_keeps_activation_blockers(self):
        result = self._evaluate(self._matrix(0.9, 0.9, -0.9))
        self.assertIn("UNMOUNTED_CANDIDATE", result["activation_blockers"])
        self.assertIn("PAPER_LIVE_UNAUTHORIZED", result["activation_blockers"])


if __name__ == "__main__":
    unittest.main()
