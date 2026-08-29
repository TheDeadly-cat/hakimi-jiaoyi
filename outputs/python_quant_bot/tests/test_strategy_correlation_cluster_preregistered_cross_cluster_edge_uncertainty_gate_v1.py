from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
    as gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


TRADE_HASH = "a" * 64
PARTITION_HASH = "b" * 64


class PreregisteredCrossClusterEdgeUncertaintyGateV1Tests(unittest.TestCase):
    def setUp(self):
        self.symbol_clusters = [
            {"symbol": "A", "cluster_id": "cluster-1"},
            {"symbol": "B", "cluster_id": "cluster-1"},
            {"symbol": "C", "cluster_id": "cluster-2"},
        ]
        self.preregistration = gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1(
            self.symbol_clusters,
            trade_identity_hash=TRADE_HASH,
            cluster_partition_hash=PARTITION_HASH,
            registration_sequence=100,
            correlation_floor_micros=700_000,
            confidence_z_micros=1_644_854,
            minimum_sample_count=6,
        )
        self.clear_pairs = [
            {
                "left_symbol": "A",
                "right_symbol": "C",
                "observed_correlation_micros": 500_000,
                "sample_count": 800,
            },
            {
                "left_symbol": "B",
                "right_symbol": "C",
                "observed_correlation_micros": 600_000,
                "sample_count": 800,
            },
        ]
        self.clear_evidence = self._evidence(self.clear_pairs)

    def _evidence(self, pairs, *, sequence=101):
        return gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_evidence_v1(
            pairs,
            trade_identity_hash=TRADE_HASH,
            cluster_partition_hash=PARTITION_HASH,
            evidence_sequence=sequence,
        )

    def _evaluate(self, evidence=None, *, expected_hash=None):
        return gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            self.preregistration,
            self.clear_evidence if evidence is None else evidence,
            expected_preregistration_hash=(
                self.preregistration["preregistration_hash"]
                if expected_hash is None
                else expected_hash
            ),
        )

    def test_high_sample_cross_cluster_edges_pass_research_only(self):
        result = self._evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["decision"],
            "PASS_PREREGISTERED_CROSS_CLUSTER_EDGE_UNCERTAINTY",
        )
        self.assertEqual(result["summary"]["verified_pair_count"], 2)
        self.assertEqual(result["summary"]["blocked_pair_count"], 0)
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_low_sample_confidence_overlap_blocks_above_minimum_sample(self):
        pairs = deepcopy(self.clear_pairs)
        pairs[0]["observed_correlation_micros"] = 650_000
        pairs[0]["sample_count"] = 8
        result = self._evaluate(self._evidence(pairs))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["pair_results"][0]["classification"],
            "UNCERTAINTY_INTERVAL_OVERLAPS_CORRELATION_FLOOR",
        )
        self.assertGreaterEqual(
            result["pair_results"][0]["confidence_upper_correlation_micros"],
            700_000,
        )

    def test_observed_edge_at_threshold_blocks_without_confidence_ambiguity(self):
        pairs = deepcopy(self.clear_pairs)
        pairs[0]["observed_correlation_micros"] = 700_000
        result = self._evaluate(self._evidence(pairs))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["pair_results"][0]["classification"],
            "OBSERVED_CROSS_CLUSTER_EDGE_AT_OR_ABOVE_FLOOR",
        )
        self.assertEqual(result["summary"]["observed_breach_pair_count"], 1)

    def test_insufficient_sample_blocks_before_uncertainty_clearance(self):
        pairs = deepcopy(self.clear_pairs)
        pairs[0]["observed_correlation_micros"] = 200_000
        pairs[0]["sample_count"] = 5
        result = self._evaluate(self._evidence(pairs))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["pair_results"][0]["classification"],
            "INSUFFICIENT_SAMPLE_FOR_CROSS_CLUSTER_EDGE",
        )
        self.assertEqual(result["summary"]["insufficient_sample_pair_count"], 1)

    def test_missing_and_same_cluster_extra_pairs_fail_closed(self):
        missing = self._evaluate(self._evidence(self.clear_pairs[:1]))
        extra_pairs = deepcopy(self.clear_pairs) + [
            {
                "left_symbol": "A",
                "right_symbol": "B",
                "observed_correlation_micros": 500_000,
                "sample_count": 800,
            }
        ]
        extra = self._evaluate(self._evidence(extra_pairs))
        for result in (missing, extra):
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["pair_results"], [])
            self.assertIn("CROSS_CLUSTER_PAIR_UNIVERSE_MISMATCH", result["blockers"])

    def test_duplicate_pair_fails_closed_without_partial_results(self):
        evidence = deepcopy(self.clear_evidence)
        evidence["pairs"].append(deepcopy(evidence["pairs"][0]))
        evidence["pairs"].sort(key=lambda row: (row["left_symbol"], row["right_symbol"]))
        evidence.pop("evidence_hash")
        evidence = seal_strict_canonical_document(evidence, "evidence_hash")
        result = self._evaluate(evidence)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["pair_results"], [])

    def test_source_hash_and_sequence_splices_fail_closed(self):
        hash_splice = deepcopy(self.clear_evidence)
        hash_splice["cluster_partition_hash"] = "c" * 64
        hash_splice.pop("evidence_hash")
        hash_splice = seal_strict_canonical_document(hash_splice, "evidence_hash")
        sequence_splice = self._evidence(self.clear_pairs, sequence=100)
        for result in (
            self._evaluate(hash_splice),
            self._evaluate(sequence_splice),
        ):
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["pair_results"], [])

    def test_expected_preregistration_hash_is_an_external_pin(self):
        result = self._evaluate(expected_hash="0" * 64)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("PREREGISTRATION_HASH_SUBSTITUTED", result["blockers"])
        self.assertIsNone(result["source"]["preregistration_hash"])

    def test_invalid_numeric_types_and_ranges_are_unknown(self):
        evidence = deepcopy(self.clear_evidence)
        evidence["pairs"][0]["observed_correlation_micros"] = True
        evidence.pop("evidence_hash")
        evidence = seal_strict_canonical_document(evidence, "evidence_hash")
        result = self._evaluate(evidence)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["pair_results"], [])

    def test_source_builders_are_deterministic_and_canonical(self):
        reverse_preregistration = gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1(
            list(reversed(self.symbol_clusters)),
            trade_identity_hash=TRADE_HASH,
            cluster_partition_hash=PARTITION_HASH,
            registration_sequence=100,
            correlation_floor_micros=700_000,
            confidence_z_micros=1_644_854,
            minimum_sample_count=6,
        )
        reverse_evidence = self._evidence(list(reversed(self.clear_pairs)))
        self.assertEqual(reverse_preregistration, self.preregistration)
        self.assertEqual(reverse_evidence, self.clear_evidence)

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        preregistration_before = deepcopy(self.preregistration)
        evidence_before = deepcopy(self.clear_evidence)
        result = self._evaluate()
        self.assertEqual(self.preregistration, preregistration_before)
        self.assertEqual(self.clear_evidence, evidence_before)
        self.assertNotIn("symbol_clusters", result)
        self.assertNotIn("pairs", result["source"])
        self.assertFalse(result["facts"]["source_documents_embedded"])
        self.assertFalse(result["facts"]["historical_market_data_accessed"])

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        result = self._evaluate()
        receipt = gate.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            result,
            self.preregistration,
            self.clear_evidence,
            expected_preregistration_hash=self.preregistration["preregistration_hash"],
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["edge_uncertainty_gate_v1_exactly_verified"])
        promoted = deepcopy(result)
        promoted["authority"]["paper_authorized"] = True
        promoted.pop("edge_uncertainty_gate_v1_hash")
        promoted = seal_strict_canonical_document(
            promoted,
            "edge_uncertainty_gate_v1_hash",
        )
        rejected = gate.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            promoted,
            self.preregistration,
            self.clear_evidence,
            expected_preregistration_hash=self.preregistration["preregistration_hash"],
        )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["edge_uncertainty_gate_v1_exactly_verified"])


if __name__ == "__main__":
    unittest.main()
