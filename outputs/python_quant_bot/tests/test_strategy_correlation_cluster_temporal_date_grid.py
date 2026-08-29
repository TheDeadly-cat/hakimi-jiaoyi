from __future__ import annotations

import copy
from datetime import date
import hashlib
import random
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    evaluate_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    DATE_GRID_RULE,
    REQUIRED_PRICE_ROWS,
    build_strategy_correlation_cluster_temporal_date_grid_policy,
    evaluate_strategy_correlation_cluster_temporal_date_grid_gate,
    verify_strategy_correlation_cluster_temporal_date_grid_gate,
    verify_strategy_correlation_cluster_temporal_date_grid_policy,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    evaluate_strategy_correlation_cluster_temporal_stability_gate,
)
from exchange_terminal.services.strategy_correlation_return_replay import (
    build_correlation_completed_price_input,
    build_correlation_matrix_replay,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_temporal_stability import (
    StrategyCorrelationClusterTemporalStabilityTests,
)


class StrategyCorrelationClusterTemporalDateGridTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal_case = StrategyCorrelationClusterTemporalStabilityTests(
            methodName="test_all_stable_windows_pass"
        )
        self.temporal_case.setUp()

    def _evaluate(self, values, source_temporal_gate):
        source, prereg, matrix, cells, complete, full_stability = values
        return evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
            source,
            source_temporal_gate,
            full_window_stability_gate=full_stability,
            complete_link_gate=complete,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def _verify(self, values, source_temporal_gate, gate):
        source, prereg, matrix, cells, complete, full_stability = values
        return verify_strategy_correlation_cluster_temporal_date_grid_gate(
            gate,
            source_uncertainty_audit=source,
            source_temporal_stability_gate=source_temporal_gate,
            full_window_stability_gate=full_stability,
            complete_link_gate=complete,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def _misaligned_but_upstream_passes(self):
        _, prereg, _, cells, _, _ = self.temporal_case._uniform()
        pattern = [
            random.Random(1000 + index).uniform(-0.012, 0.012)
            for index in range(20)
        ]
        series = {
            "A": pattern * 3,
            "B": pattern * 3,
            "C": [
                random.Random(3000 + index).uniform(-0.012, 0.012)
                for index in range(60)
            ],
        }
        starts = {
            "A": date(2026, 1, 1),
            "B": date(2025, 12, 12),
            "C": date(2026, 1, 1),
        }
        payloads = {}
        manifests = []
        for symbol, returns in series.items():
            rows = self.temporal_case.replay_case._price_rows(
                returns,
                start=starts[symbol],
            )
            payloads[symbol] = {"source": "frozen-fixture", "rows": rows}
            manifests.append(
                {
                    "role": "SELECTION",
                    "symbol": symbol,
                    "timeframe": "1D",
                    "source": "frozen-fixture",
                    "data_hash": hashlib.sha256(
                        symbol.encode("ascii")
                    ).hexdigest(),
                    "row_count": len(rows),
                }
            )
        completed = build_correlation_completed_price_input(
            payloads,
            manifests,
            prereg,
            cutoff_date="2026-03-02",
            selection_alignment_input_hash="a" * 64,
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
        values = (source, prereg, matrix, cells, complete, full_stability)
        source_temporal_gate = (
            evaluate_strategy_correlation_cluster_temporal_stability_gate(
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
        )
        return values, source_temporal_gate

    def test_policy_is_fixed_consumer_only_and_non_authoritative(self):
        policy = build_strategy_correlation_cluster_temporal_date_grid_policy()
        verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_policy(policy)
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(policy["date_grid_rule"], DATE_GRID_RULE)
        self.assertEqual(policy["required_price_rows"], REQUIRED_PRICE_ROWS)
        self.assertIs(policy["date_intersection_substitution_allowed"], False)
        self.assertIs(policy["writer_available"], False)

    def test_exact_common_date_grid_preserves_source_pass(self):
        values = self.temporal_case._piecewise_gap(weak_window=None)
        source_temporal_gate = self.temporal_case._evaluate(values)
        gate = self._evaluate(values, source_temporal_gate)
        verification = self._verify(values, source_temporal_gate, gate)
        audit = gate["date_grid_audit"]
        self.assertEqual(source_temporal_gate["status"], "PASS")
        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(audit["exact_common_price_date_grid_proven"])
        self.assertEqual(audit["common_price_date_count"], 61)
        self.assertEqual(audit["common_return_observation_count"], 60)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision_status"], "PASS")

    def test_only_forty_common_dates_blocks_previous_temporal_pass(self):
        values, source_temporal_gate = self._misaligned_but_upstream_passes()
        source = values[0]
        internal_pair = next(
            pair
            for pair in source["pairs"]
            if {pair["left_symbol"], pair["right_symbol"]} == {"A", "B"}
        )
        self.assertEqual(source["status"], "PASS")
        self.assertEqual(values[5]["status"], "PASS")
        self.assertEqual(source_temporal_gate["status"], "PASS")
        self.assertEqual(internal_pair["overlap_observations"], 40)
        gate = self._evaluate(values, source_temporal_gate)
        verification = self._verify(values, source_temporal_gate, gate)
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "DATE_GRID_BINDING")
        self.assertIn(
            "exact_common_price_date_grid_not_proven",
            gate["blockers"],
        )
        self.assertFalse(
            gate["date_grid_audit"]["exact_common_price_date_grid_proven"]
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision_status"], "BLOCK")

    def test_coherently_resealed_date_grid_claim_is_rejected(self):
        values = self.temporal_case._piecewise_gap(weak_window=None)
        source_temporal_gate = self.temporal_case._evaluate(values)
        attacked = copy.deepcopy(self._evaluate(values, source_temporal_gate))
        attacked["date_grid_audit"]["common_price_date_count"] = 60
        attacked["date_grid_audit"] = seal_strict_canonical_document(
            {
                key: value
                for key, value in attacked["date_grid_audit"].items()
                if key != "audit_hash"
            },
            "audit_hash",
        )
        attacked["date_grid_audit_hash"] = attacked["date_grid_audit"][
            "audit_hash"
        ]
        attacked = seal_strict_canonical_document(
            {key: value for key, value in attacked.items() if key != "gate_hash"},
            "gate_hash",
        )
        verification = self._verify(values, source_temporal_gate, attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["decision_status"], "BLOCK")

    def test_native_type_and_authority_aliases_fail_closed(self):
        policy = build_strategy_correlation_cluster_temporal_date_grid_policy()
        attacked_policy = copy.deepcopy(policy)
        attacked_policy["required_price_rows"] = 61.0
        attacked_policy = seal_strict_canonical_document(
            {
                key: value
                for key, value in attacked_policy.items()
                if key != "policy_hash"
            },
            "policy_hash",
        )
        self.assertEqual(
            verify_strategy_correlation_cluster_temporal_date_grid_policy(
                attacked_policy
            )["status"],
            "BLOCK",
        )
        values = self.temporal_case._piecewise_gap(weak_window=None)
        source_temporal_gate = self.temporal_case._evaluate(values)
        attacked_gate = copy.deepcopy(self._evaluate(values, source_temporal_gate))
        attacked_gate["liveOrderAllowed"] = True
        attacked_gate = seal_strict_canonical_document(
            {key: value for key, value in attacked_gate.items() if key != "gate_hash"},
            "gate_hash",
        )
        verification = self._verify(values, source_temporal_gate, attacked_gate)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIs(verification["permissions"]["paper_authorized"], False)
        self.assertIs(verification["permissions"]["live_order_allowed"], False)

    def test_exports_have_no_writer_or_current_switch(self):
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("build_report21", exports)
        self.assertNotIn("write_temporal_date_grid", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
