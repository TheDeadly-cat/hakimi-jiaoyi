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
    verify_strategy_correlation_strata_gate,
    verify_strategy_correlation_strata_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationPreregisteredStrataTests(unittest.TestCase):
    def _base_fixture(self, symbols=("AAA", "BBB"), statuses=None):
        statuses = statuses or {symbol: "PASS" for symbol in symbols}
        clusters = [
            {
                "cluster_id": f"cluster-{symbol.lower()}",
                "members": [symbol],
            }
            for symbol in symbols
        ]
        preregistration = build_correlation_cluster_preregistration(clusters)
        correlations = {
            pair: 0.10 for pair in itertools.combinations(symbols, 2)
        }
        matrix = build_correlation_matrix_contract(
            list(symbols),
            correlations,
            overlap_observations=60,
        )
        cells = [
            {
                "strategy_id": "strategy-1",
                "variant_id": "variant-1",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": statuses[symbol],
            }
            for symbol in symbols
        ]
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="strategy-1",
            variant_id="variant-1",
            lane="RAW_EXCESS",
        )
        return preregistration, gate

    @staticmethod
    def _separate_strata(symbols):
        return [
            {
                "dimension_id": "asset-family",
                "strata": [
                    {
                        "stratum_id": f"family-{symbol.lower()}",
                        "cluster_ids": [f"cluster-{symbol.lower()}"],
                    }
                    for symbol in symbols
                ],
            }
        ]

    def test_same_parent_stratum_blocks_existing_two_vote_pass(self):
        preregistration, base_gate = self._base_fixture()
        self.assertEqual(base_gate["status"], "PASS")
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            [
                {
                    "dimension_id": "sector",
                    "strata": [
                        {
                            "stratum_id": "shared-sector",
                            "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                        }
                    ],
                }
            ],
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            base_gate,
            source_preregistration=preregistration,
        )
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["first_blocking_tier"],
            "PREREGISTERED_STRATA",
        )
        result = gate["dimension_results"][0]
        self.assertEqual(result["passing_stratum_count"], 1)
        self.assertEqual(result["required_stratum_votes"], 2)
        self.assertIn(
            "minimum_independent_strata_not_met",
            result["blockers"],
        )

    def test_two_independent_strata_pass_contract_without_authority(self):
        preregistration, base_gate = self._base_fixture()
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            self._separate_strata(("AAA", "BBB")),
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            base_gate,
            source_preregistration=preregistration,
        )
        self.assertEqual(gate["status"], "PASS")
        self.assertFalse(gate["current_admission_allowed"])
        self.assertFalse(gate["current_writer_activation_allowed"])
        self.assertFalse(gate["permissions"]["paper_authorized"])
        self.assertFalse(gate["permissions"]["live_order_allowed"])
        self.assertTrue(gate["consumer_only"])
        self.assertFalse(gate["writer_implemented"])

    def test_any_preregistered_dimension_can_block_independence(self):
        symbols = ("AAA", "BBB", "CCC")
        preregistration, base_gate = self._base_fixture(symbols)
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            [
                self._separate_strata(symbols)[0],
                {
                    "dimension_id": "macro-factor",
                    "strata": [
                        {
                            "stratum_id": "shared-duration",
                            "cluster_ids": [
                                "cluster-aaa",
                                "cluster-bbb",
                                "cluster-ccc",
                            ],
                        }
                    ],
                },
            ],
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            base_gate,
            source_preregistration=preregistration,
        )
        statuses = {
            result["dimension_id"]: result["status"]
            for result in gate["dimension_results"]
        }
        self.assertEqual(statuses["asset-family"], "PASS")
        self.assertEqual(statuses["macro-factor"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")

    def test_registration_is_order_canonical_and_exactly_rebuildable(self):
        preregistration, _ = self._base_fixture()
        dimensions = [
            {
                "dimension_id": "sector",
                "strata": [
                    {
                        "stratum_id": "sector-b",
                        "cluster_ids": ["cluster-bbb"],
                    },
                    {
                        "stratum_id": "sector-a",
                        "cluster_ids": ["cluster-aaa"],
                    },
                ],
            },
            {
                "dimension_id": "asset-family",
                "strata": [
                    {
                        "stratum_id": "family-a",
                        "cluster_ids": ["cluster-aaa"],
                    },
                    {
                        "stratum_id": "family-b",
                        "cluster_ids": ["cluster-bbb"],
                    },
                ],
            },
        ]
        left = build_strategy_correlation_strata_preregistration(
            preregistration,
            dimensions,
        )
        right = build_strategy_correlation_strata_preregistration(
            preregistration,
            list(reversed(dimensions)),
        )
        self.assertEqual(left, right)
        self.assertEqual(
            verify_strategy_correlation_strata_preregistration(
                left,
                source_preregistration=preregistration,
            )["status"],
            "PASS",
        )

    def test_registration_rejects_missing_duplicate_and_unknown_clusters(self):
        preregistration, _ = self._base_fixture()
        invalid_partitions = [
            [
                {
                    "dimension_id": "sector",
                    "strata": [
                        {
                            "stratum_id": "only-a",
                            "cluster_ids": ["cluster-aaa"],
                        }
                    ],
                }
            ],
            [
                {
                    "dimension_id": "sector",
                    "strata": [
                        {
                            "stratum_id": "first",
                            "cluster_ids": ["cluster-aaa", "cluster-bbb"],
                        },
                        {
                            "stratum_id": "second",
                            "cluster_ids": ["cluster-bbb"],
                        },
                    ],
                }
            ],
            [
                {
                    "dimension_id": "sector",
                    "strata": [
                        {
                            "stratum_id": "unknown",
                            "cluster_ids": [
                                "cluster-aaa",
                                "cluster-bbb",
                                "cluster-ccc",
                            ],
                        }
                    ],
                }
            ],
        ]
        for dimensions in invalid_partitions:
            with self.subTest(dimensions=dimensions):
                with self.assertRaises(ValueError):
                    build_strategy_correlation_strata_preregistration(
                        preregistration,
                        dimensions,
                    )

    def test_resealed_duplicate_partition_is_rejected_before_vote_count(self):
        preregistration, base_gate = self._base_fixture()
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            self._separate_strata(("AAA", "BBB")),
        )
        tampered = copy.deepcopy(registration)
        tampered["dimensions"][0]["strata"] = [
            {
                "stratum_id": "forged-a",
                "cluster_ids": ["cluster-aaa"],
            },
            {
                "stratum_id": "forged-b",
                "cluster_ids": ["cluster-aaa"],
            },
        ]
        tampered["registration_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in tampered.items()
                if key != "registration_hash"
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            "strata_registration_independent_verification_failed",
        ):
            evaluate_strategy_correlation_strata_gate(
                tampered,
                base_gate,
                source_preregistration=preregistration,
            )

    def test_blocked_base_gate_propagates_before_strata(self):
        preregistration, base_gate = self._base_fixture(
            statuses={"AAA": "PASS", "BBB": "BLOCK"}
        )
        self.assertEqual(base_gate["status"], "BLOCK")
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            self._separate_strata(("AAA", "BBB")),
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            base_gate,
            source_preregistration=preregistration,
        )
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "BASE_COMPLETE_LINK")
        self.assertIn("base_complete_link_gate_blocked", gate["blockers"])

    def test_resealed_authority_escalation_in_base_gate_is_rejected(self):
        preregistration, base_gate = self._base_fixture()
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            self._separate_strata(("AAA", "BBB")),
        )
        mutations = [
            (
                "top-level-current",
                lambda document: document.__setitem__(
                    "current_admission_allowed",
                    True,
                ),
            ),
            (
                "nested-writer",
                lambda document: document["complete_link_audit"].__setitem__(
                    "current_writer_activation_allowed",
                    True,
                ),
            ),
            (
                "paper-permission",
                lambda document: document["permissions"].__setitem__(
                    "paper_authorized",
                    True,
                ),
            ),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                tampered = copy.deepcopy(base_gate)
                mutate(tampered)
                tampered["gate_hash"] = strict_canonical_hash(
                    {
                        key: value
                        for key, value in tampered.items()
                        if key != "gate_hash"
                    }
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "complete_link_gate_authority_invalid",
                ):
                    evaluate_strategy_correlation_strata_gate(
                        registration,
                        tampered,
                        source_preregistration=preregistration,
                    )

    def test_registration_and_gate_tampering_fail_verification(self):
        preregistration, base_gate = self._base_fixture()
        registration = build_strategy_correlation_strata_preregistration(
            preregistration,
            self._separate_strata(("AAA", "BBB")),
        )
        tampered_registration = copy.deepcopy(registration)
        tampered_registration["minimum_independent_strata"] = 1
        self.assertEqual(
            verify_strategy_correlation_strata_preregistration(
                tampered_registration,
                source_preregistration=preregistration,
            )["status"],
            "BLOCK",
        )
        gate = evaluate_strategy_correlation_strata_gate(
            registration,
            base_gate,
            source_preregistration=preregistration,
        )
        self.assertEqual(
            verify_strategy_correlation_strata_gate(
                gate,
                registration=registration,
                complete_link_gate=base_gate,
                source_preregistration=preregistration,
            )["status"],
            "PASS",
        )
        tampered_gate = copy.deepcopy(gate)
        tampered_gate["status"] = "BLOCK"
        self.assertEqual(
            verify_strategy_correlation_strata_gate(
                tampered_gate,
                registration=registration,
                complete_link_gate=base_gate,
                source_preregistration=preregistration,
            )["status"],
            "BLOCK",
        )


if __name__ == "__main__":
    unittest.main()
