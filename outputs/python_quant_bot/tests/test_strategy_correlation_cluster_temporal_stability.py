from __future__ import annotations

import copy
import importlib
import math
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    ABSOLUTE_PEARSON_THRESHOLD,
    FAMILY_SCOPE,
    SIGN_POLICY,
    WINDOW_COUNT,
    WINDOW_OBSERVATIONS,
    build_strategy_correlation_cluster_temporal_stability_policy,
    evaluate_strategy_correlation_cluster_temporal_stability_gate,
    verify_strategy_correlation_cluster_temporal_stability_gate,
    verify_strategy_correlation_cluster_temporal_stability_policy,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_matrix_replay,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_stability_tests = importlib.import_module(
    "tests.test_strategy_correlation_cluster_stability"
)
_return_replay_tests = importlib.import_module(
    "tests.test_strategy_correlation_return_replay"
)
_temporal_module = importlib.import_module(
    "exchange_terminal.services.strategy_correlation_cluster_temporal_stability"
)


class StrategyCorrelationClusterTemporalStabilityTests(unittest.TestCase):
    def setUp(self):
        stability_case_type = getattr(
            _stability_tests,
            "StrategyCorrelationClusterStabilityTests",
        )
        self.stability_case = stability_case_type(
            methodName="test_point_complete_link_pass_can_be_stability_blocked"
        )
        self.stability_case.setUp()
        replay_case_type = getattr(
            _return_replay_tests,
            "StrategyCorrelationReturnReplayTests",
        )
        self.replay_case = replay_case_type(
            methodName="test_price_replay_recomputes_matrix_and_collapses_symbol_majority"
        )
        self.replay_case.setUp()

    def _uniform(self, rho=0.995, *, negative=False, singleton=False):
        return self.stability_case._fixture(
            rho=rho,
            negative=negative,
            singleton=singleton,
        )

    def _piecewise_gap(self, *, weak_window=2, negative=False):
        _, prereg, _, cells, _, _ = self._uniform()
        a = [value * 0.01 for value in self.stability_case.fixture._normal(1)]
        c = [value * 0.01 for value in self.stability_case.fixture._normal(31)]
        noise = [value * 0.01 for value in self.stability_case.fixture._normal(41)]
        b = []
        weak_start = (
            (weak_window - 1) * WINDOW_OBSERVATIONS
            if weak_window is not None
            else None
        )
        weak_end = (
            weak_start + WINDOW_OBSERVATIONS if weak_start is not None else None
        )
        for index, (signal, residual) in enumerate(zip(a, noise)):
            if weak_start is None:
                rho = 0.995
            else:
                rho = 0.75 if weak_start <= index < weak_end else 0.98
            value = rho * signal + math.sqrt(1.0 - rho * rho) * residual
            b.append(-value if negative else value)
        completed = self.replay_case._input(
            {"A": a, "B": b, "C": c},
            preregistration=prereg,
        )
        replay = build_correlation_matrix_replay(completed, prereg)
        source = build_strategy_correlation_uncertainty_audit(replay)
        correlations = {}
        overlaps = {}
        for pair in source["pairs"]:
            key = (pair["left_symbol"], pair["right_symbol"])
            correlations[key] = pair["correlation"]
            overlaps[key] = pair["overlap_observations"]
        matrix = build_correlation_matrix_contract(
            prereg["symbols"],
            correlations,
            overlap_observations=overlaps,
        )
        complete = evaluate_correlation_cluster_gate_v2(
            prereg,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        full_stability = self.stability_case._fixture(rho=0.98)[5]
        # Re-evaluate the full-window gate against the piecewise source through the
        # existing production gate helper used by the fixture.
        from exchange_terminal.services.strategy_correlation_cluster_stability import (
            evaluate_strategy_correlation_cluster_stability_gate,
        )

        full_stability = evaluate_strategy_correlation_cluster_stability_gate(
            source,
            complete,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        return source, prereg, matrix, cells, complete, full_stability

    def _evaluate(self, values):
        source, prereg, matrix, cells, complete, full_stability = values
        return evaluate_strategy_correlation_cluster_temporal_stability_gate(
            source,
            full_stability,
            complete_link_gate=complete,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def _verify(self, values, gate):
        source, prereg, matrix, cells, complete, full_stability = values
        return verify_strategy_correlation_cluster_temporal_stability_gate(
            gate,
            source_uncertainty_audit=source,
            full_window_stability_gate=full_stability,
            complete_link_gate=complete,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def test_policy_freezes_three_equal_preregistered_windows(self):
        policy = build_strategy_correlation_cluster_temporal_stability_policy()
        verification = verify_strategy_correlation_cluster_temporal_stability_policy(
            policy
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(policy["window_count"], 3)
        self.assertEqual(policy["window_observations"], 20)
        self.assertEqual(policy["family_scope"], FAMILY_SCOPE)
        self.assertEqual(policy["sign_policy"], SIGN_POLICY)
        self.assertEqual(policy["absolute_pearson_threshold"], 0.75)
        self.assertIs(policy["writer_available"], False)

    def test_full_window_pass_can_be_temporally_blocked(self):
        values = self._piecewise_gap()
        self.assertEqual(values[4]["status"], "PASS")
        self.assertEqual(values[5]["status"], "PASS")
        gate = self._evaluate(values)
        verification = self._verify(values, gate)
        pair = gate["temporal_stability_audit"]["pair_results"][0]
        middle = pair["window_results"][1]
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "TEMPORAL_WINDOWS")
        self.assertLess(middle["absolute_correlation"], ABSOLUTE_PEARSON_THRESHOLD)
        self.assertEqual(middle["classification"], "UNSTABLE_ABSOLUTE_DEPENDENCE")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision_status"], "BLOCK")

    def test_all_stable_windows_pass(self):
        values = self._piecewise_gap(weak_window=None)
        gate = self._evaluate(values)
        self.assertEqual(gate["status"], "PASS")
        windows = gate["temporal_stability_audit"]["pair_results"][0][
            "window_results"
        ]
        self.assertEqual(len(windows), WINDOW_COUNT)
        self.assertTrue(all(item["status"] == "PASS" for item in windows))
        self.assertEqual(self._verify(values, gate)["status"], "PASS")

    def test_negative_absolute_dependence_is_sign_agnostic(self):
        values = self._piecewise_gap(weak_window=None, negative=True)
        gate = self._evaluate(values)
        windows = gate["temporal_stability_audit"]["pair_results"][0][
            "window_results"
        ]
        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(all(item["correlation"] < 0 for item in windows))
        self.assertTrue(all(item["status"] == "PASS" for item in windows))

    def test_singleton_temporal_family_is_empty_but_upstream_block_is_preserved(self):
        values = self._uniform(singleton=True)
        gate = self._evaluate(values)
        audit = gate["temporal_stability_audit"]
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "FULL_WINDOW_STABILITY")
        self.assertEqual(audit["within_cluster_pair_count"], 0)
        self.assertEqual(audit["pair_window_hypothesis_count"], 0)
        self.assertEqual(audit["pair_results"], [])

    def test_family_correction_counts_pair_by_window_hypotheses(self):
        values = self._piecewise_gap(weak_window=None)
        audit = self._evaluate(values)["temporal_stability_audit"]
        self.assertEqual(audit["within_cluster_pair_count"], 1)
        self.assertEqual(audit["pair_window_hypothesis_count"], 3)
        self.assertAlmostEqual(audit["per_test_alpha"], 0.05 / 3, places=12)
        self.assertGreater(audit["bonferroni_critical_value"], 1.9599)

    def test_any_preregistered_window_can_block(self):
        for weak_window in (1, 2, 3):
            with self.subTest(weak_window=weak_window):
                values = self._piecewise_gap(weak_window=weak_window)
                self.assertEqual(values[4]["status"], "PASS")
                self.assertEqual(values[5]["status"], "PASS")
                gate = self._evaluate(values)
                pair = gate["temporal_stability_audit"]["pair_results"][0]
                self.assertEqual(gate["status"], "BLOCK")
                self.assertEqual(
                    pair["window_results"][weak_window - 1]["status"], "BLOCK"
                )

    def test_full_window_stability_block_is_preserved(self):
        values = self._uniform(rho=0.82)
        self.assertEqual(values[5]["status"], "BLOCK")
        gate = self._evaluate(values)
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "FULL_WINDOW_STABILITY")
        self.assertEqual(gate["temporal_stability_audit"]["pair_results"], [])

    def test_source_audit_tamper_fails_closed(self):
        values = list(self._uniform())
        attacked = copy.deepcopy(values[0])
        attacked["pairs"][0]["correlation"] = 0.999999
        attacked = seal_strict_canonical_document(attacked, "audit_hash")
        values[0] = attacked
        gate = self._evaluate(tuple(values))
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "SOURCE_CONTRACTS")

    def test_complete_link_reseal_cannot_bypass_full_window_binding(self):
        values = list(self._piecewise_gap(weak_window=None))
        attacked = copy.deepcopy(values[4])
        attacked["status"] = "BLOCK"
        attacked = seal_strict_canonical_document(attacked, "gate_hash")
        values[4] = attacked
        gate = self._evaluate(tuple(values))
        audit = gate["temporal_stability_audit"]
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "SOURCE_CONTRACTS")
        self.assertIn("FULL_WINDOW_STABILITY_GATE_NOT_VERIFIED", gate["blockers"])
        self.assertIs(audit["input_binding"]["full_window_stability_gate_verified"], False)

    def test_resealed_gate_status_cannot_override_rebuild(self):
        values = self._piecewise_gap()
        gate = self._evaluate(values)
        attacked = copy.deepcopy(gate)
        attacked["status"] = "PASS"
        attacked["blockers"] = []
        attacked = seal_strict_canonical_document(attacked, "gate_hash")
        verification = self._verify(values, attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["decision_status"], "BLOCK")

    def test_authority_alias_is_rejected_after_reseal(self):
        values = self._uniform()
        attacked = copy.deepcopy(self._evaluate(values))
        attacked["current_admission_allowed"] = 0
        attacked = seal_strict_canonical_document(attacked, "gate_hash")
        verification = self._verify(values, attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIs(verification["current_admission_allowed"], False)
        self.assertIs(verification["permissions"]["paper_authorized"], False)
        self.assertIs(verification["permissions"]["live_order_allowed"], False)

    def test_policy_reseal_cannot_change_window_count(self):
        policy = build_strategy_correlation_cluster_temporal_stability_policy()
        attacked = copy.deepcopy(policy)
        attacked["window_count"] = 2
        attacked = seal_strict_canonical_document(attacked, "policy_hash")
        verification = verify_strategy_correlation_cluster_temporal_stability_policy(
            attacked
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_consumer_only_exports_have_no_writer_or_current_switch(self):
        exports = set(_temporal_module.__all__)
        self.assertNotIn("build_report21", exports)
        self.assertNotIn("write_temporal_stability", exports)
        self.assertNotIn("switch_current_pointer", exports)
        values = self._uniform()
        gate = self._evaluate(values)
        self.assertIs(gate["consumer_only"], True)
        self.assertIs(gate["writer_available"], False)
        self.assertIs(gate["current_writer_activation_allowed"], False)
        self.assertIs(gate["current_admission_allowed"], False)


if __name__ == "__main__":
    unittest.main()
