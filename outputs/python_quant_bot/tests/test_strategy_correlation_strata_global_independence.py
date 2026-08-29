import copy
import itertools
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strategy_correlation_strata_global_independence import (
    MAX_EXACT_CLUSTER_COUNT,
    evaluate_strategy_correlation_strata_global_independence_gate,
    verify_strategy_correlation_strata_global_independence_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationStrataGlobalIndependenceTests(unittest.TestCase):
    @staticmethod
    def _hash(document, field):
        return strict_canonical_hash(
            {key: value for key, value in document.items() if key != field}
        )

    def _fixture(self, dimensions, *, statuses=None, count=3):
        symbols = [f"S{index:02d}" for index in range(count)]
        cluster_ids = [f"cluster-{index:02d}" for index in range(count)]
        statuses = statuses or {symbol: "PASS" for symbol in symbols}
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": cluster_id, "members": [symbol]}
                for cluster_id, symbol in zip(cluster_ids, symbols)
            ]
        )
        matrix = build_correlation_matrix_contract(
            symbols,
            {
                pair: 0.10
                for pair in itertools.combinations(symbols, 2)
            },
        )
        cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": statuses[symbol],
            }
            for symbol in symbols
        ]
        complete_link_gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            dimensions,
        )
        strata_gate = evaluate_strategy_correlation_strata_gate(
            registration,
            complete_link_gate,
            source_preregistration=preregistration,
        )
        global_gate = (
            evaluate_strategy_correlation_strata_global_independence_gate(
                registration,
                complete_link_gate,
                strata_gate,
                source_preregistration=preregistration,
            )
        )
        return (
            preregistration,
            registration,
            complete_link_gate,
            strata_gate,
            global_gate,
        )

    @staticmethod
    def _separate_dimension(count):
        return [
            {
                "dimension_id": "asset-family",
                "strata": [
                    {
                        "stratum_id": f"family-{index:02d}",
                        "cluster_ids": [f"cluster-{index:02d}"],
                    }
                    for index in range(count)
                ],
            }
        ]

    def test_cross_dimension_cycle_blocks_false_independence(self):
        dimensions = [
            {
                "dimension_id": "d1",
                "strata": [
                    {
                        "stratum_id": "ab",
                        "cluster_ids": ["cluster-00", "cluster-01"],
                    },
                    {
                        "stratum_id": "c",
                        "cluster_ids": ["cluster-02"],
                    },
                ],
            },
            {
                "dimension_id": "d2",
                "strata": [
                    {
                        "stratum_id": "ac",
                        "cluster_ids": ["cluster-00", "cluster-02"],
                    },
                    {
                        "stratum_id": "b",
                        "cluster_ids": ["cluster-01"],
                    },
                ],
            },
            {
                "dimension_id": "d3",
                "strata": [
                    {
                        "stratum_id": "bc",
                        "cluster_ids": ["cluster-01", "cluster-02"],
                    },
                    {
                        "stratum_id": "a",
                        "cluster_ids": ["cluster-00"],
                    },
                ],
            },
        ]
        _, _, _, strata_gate, global_gate = self._fixture(dimensions)
        self.assertEqual(strata_gate["status"], "PASS")
        self.assertEqual(global_gate["status"], "BLOCK")
        audit = global_gate["global_independence_audit"]
        self.assertEqual(audit["registered_independent_capacity"], 1)
        self.assertEqual(audit["passing_independent_capacity"], 1)
        self.assertEqual(audit["required_global_independent_votes"], 2)
        self.assertEqual(audit["conflict_pair_count"], 3)

    def test_three_globally_independent_clusters_pass(self):
        _, _, _, strata_gate, global_gate = self._fixture(
            self._separate_dimension(3)
        )
        self.assertEqual(strata_gate["status"], "PASS")
        self.assertEqual(global_gate["status"], "PASS")
        audit = global_gate["global_independence_audit"]
        self.assertEqual(audit["registered_independent_capacity"], 3)
        self.assertEqual(audit["passing_independent_capacity"], 3)
        self.assertEqual(audit["required_global_independent_votes"], 2)
        self.assertFalse(global_gate["current_admission_allowed"])
        self.assertFalse(global_gate["permissions"]["paper_authorized"])
        self.assertFalse(global_gate["permissions"]["live_order_allowed"])

    def test_two_of_three_independent_passing_clusters_meet_fixed_fraction(self):
        statuses = {"S00": "PASS", "S01": "PASS", "S02": "BLOCK"}
        _, _, _, strata_gate, global_gate = self._fixture(
            self._separate_dimension(3),
            statuses=statuses,
        )
        self.assertEqual(strata_gate["status"], "PASS")
        self.assertEqual(global_gate["status"], "PASS")
        self.assertEqual(
            global_gate["global_independence_audit"][
                "passing_independent_capacity"
            ],
            2,
        )

    def test_base_strata_block_is_monotonic(self):
        statuses = {"S00": "PASS", "S01": "BLOCK", "S02": "BLOCK"}
        _, _, _, strata_gate, global_gate = self._fixture(
            self._separate_dimension(3),
            statuses=statuses,
        )
        self.assertEqual(strata_gate["status"], "BLOCK")
        self.assertEqual(global_gate["status"], "BLOCK")
        self.assertEqual(
            global_gate["first_blocking_tier"],
            "BASE_STRATA_GATE",
        )
        self.assertIn(
            "base_strata_gate_blocked",
            global_gate["blockers"],
        )

    def test_cluster_count_above_exact_limit_fails_closed(self):
        count = MAX_EXACT_CLUSTER_COUNT + 1
        _, _, _, strata_gate, global_gate = self._fixture(
            self._separate_dimension(count),
            count=count,
        )
        self.assertEqual(strata_gate["status"], "PASS")
        self.assertEqual(global_gate["status"], "BLOCK")
        audit = global_gate["global_independence_audit"]
        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn(
            "global_independence_cluster_limit_exceeded",
            audit["blockers"],
        )
        self.assertIsNone(audit["registered_independent_capacity"])

    def test_verifier_exactly_rebuilds_gate_and_audit(self):
        (
            preregistration,
            registration,
            complete_link_gate,
            strata_gate,
            global_gate,
        ) = self._fixture(self._separate_dimension(3))
        self.assertEqual(
            verify_strategy_correlation_strata_global_independence_gate(
                global_gate,
                registration=registration,
                complete_link_gate=complete_link_gate,
                strata_gate=strata_gate,
                source_preregistration=preregistration,
            )["status"],
            "PASS",
        )
        tampered = copy.deepcopy(global_gate)
        tampered["global_independence_audit"][
            "passing_independent_capacity"
        ] = 2
        tampered["global_independence_audit"]["audit_hash"] = self._hash(
            tampered["global_independence_audit"],
            "audit_hash",
        )
        tampered["gate_hash"] = self._hash(tampered, "gate_hash")
        self.assertEqual(
            verify_strategy_correlation_strata_global_independence_gate(
                tampered,
                registration=registration,
                complete_link_gate=complete_link_gate,
                strata_gate=strata_gate,
                source_preregistration=preregistration,
            )["status"],
            "BLOCK",
        )

    def test_resealed_authority_escalation_is_rejected(self):
        (
            preregistration,
            registration,
            complete_link_gate,
            strata_gate,
            global_gate,
        ) = self._fixture(self._separate_dimension(3))
        tampered = copy.deepcopy(global_gate)
        tampered["current_writer_activation_allowed"] = True
        tampered["gate_hash"] = self._hash(tampered, "gate_hash")
        verification = (
            verify_strategy_correlation_strata_global_independence_gate(
                tampered,
                registration=registration,
                complete_link_gate=complete_link_gate,
                strata_gate=strata_gate,
                source_preregistration=preregistration,
            )
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "global_independence_gate_authority_invalid",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
