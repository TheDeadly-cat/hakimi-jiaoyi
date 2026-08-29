import math
import unittest

from tests import test_strategy_correlation_uncertainty_audit as uncertainty_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    build_strategy_correlation_cluster_stability_policy,
    evaluate_strategy_correlation_cluster_stability_gate,
    verify_strategy_correlation_cluster_stability_gate,
    verify_strategy_correlation_cluster_stability_policy,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)


class StrategyCorrelationClusterStabilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests(
            methodName="runTest"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def _fixture(self, rho=0.98, *, negative=False, singleton=False, cross_high=False):
        a = self.fixture._normal(11)
        noise = self.fixture._normal(12)
        c = a if cross_high else self.fixture._normal(13)
        sign = -1.0 if negative else 1.0
        b = [
            sign * rho * value + math.sqrt(1.0 - rho * rho) * residual
            for value, residual in zip(a, noise)
        ]
        clusters = (
            [
                {"cluster_id": "cluster-a", "members": ["A"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
            if singleton
            else [
                {"cluster_id": "cluster-ab", "members": ["A", "B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
        )
        preregistration = build_correlation_cluster_preregistration(clusters)
        replay = self.fixture._replay({"A": a, "B": b, "C": c}, clusters)
        replay["preregistration"] = preregistration
        uncertainty_audit = build_strategy_correlation_uncertainty_audit(replay)
        correlations = {}
        overlaps = {}
        for pair in uncertainty_audit["pairs"]:
            key = (pair["left_symbol"], pair["right_symbol"])
            correlations[key] = pair["correlation"]
            overlaps[key] = pair["overlap_observations"]
        matrix = build_correlation_matrix_contract(
            ["A", "B", "C"],
            correlations,
            overlap_observations=overlaps,
        )
        cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "lane": "RAW_EXCESS",
                "symbol": symbol,
                "gate_status": "PASS",
            }
            for symbol in ("A", "B", "C")
        ]
        complete_link_gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        stability_gate = evaluate_strategy_correlation_cluster_stability_gate(
            uncertainty_audit,
            complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        return uncertainty_audit, preregistration, matrix, cells, complete_link_gate, stability_gate

    def _verify(self, values, document=None):
        uncertainty, preregistration, matrix, cells, complete_link, stability = values
        return verify_strategy_correlation_cluster_stability_gate(
            document or stability,
            source_uncertainty_audit=uncertainty,
            complete_link_gate=complete_link,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def test_policy_is_fixed_descriptive_and_non_authoritative(self):
        policy = build_strategy_correlation_cluster_stability_policy()
        verification = verify_strategy_correlation_cluster_stability_policy(policy)

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(policy["family_scope"], "WITHIN_CLUSTER_PAIRS_ONLY")
        self.assertEqual(policy["correction_method"], "BONFERRONI_TWO_SIDED_FWER_V1")
        self.assertTrue(policy["descriptive_only"])
        self.assertFalse(policy["parameter_selection_allowed"])
        self.assertFalse(policy["permissions"]["paper_authorized"])

    def test_point_complete_link_pass_can_be_stability_blocked(self):
        values = self._fixture(rho=0.80)
        uncertainty, _, _, _, complete_link, stability = values
        pair = stability["stability_audit"]["pair_results"][0]

        self.assertEqual(uncertainty["status"], "PASS")
        self.assertEqual(complete_link["status"], "PASS")
        self.assertEqual(pair["classification"], "UNSTABLE_THRESHOLD")
        self.assertLess(pair["adjusted_absolute_interval_lower"], 0.75)
        self.assertEqual(stability["status"], "BLOCK")
        self.assertEqual(self._verify(values)["status"], "PASS")
        self.assertEqual(self._verify(values)["decision"], "BLOCK")

    def test_stable_positive_internal_pair_passes(self):
        values = self._fixture(rho=0.98)
        pair = values[-1]["stability_audit"]["pair_results"][0]

        self.assertEqual(pair["classification"], "STABLE_HIGH")
        self.assertGreaterEqual(pair["adjusted_absolute_interval_lower"], 0.75)
        self.assertEqual(values[-1]["status"], "PASS")
        self.assertEqual(self._verify(values)["decision"], "PASS")

    def test_stable_negative_internal_pair_passes_by_absolute_rule(self):
        values = self._fixture(rho=0.98, negative=True)
        pair = values[-1]["stability_audit"]["pair_results"][0]

        self.assertLess(pair["correlation"], 0.0)
        self.assertEqual(pair["classification"], "STABLE_HIGH")
        self.assertEqual(values[-1]["status"], "PASS")

    def test_singleton_clusters_have_no_internal_family_and_pass(self):
        values = self._fixture(rho=0.0, singleton=True)
        audit = values[-1]["stability_audit"]

        self.assertEqual(audit["within_cluster_pair_count"], 0)
        self.assertIsNone(audit["bonferroni_critical_value"])
        self.assertTrue(
            all(item["interpretation"] == "NO_INTERNAL_PAIR" for item in audit["cluster_results"])
        )
        self.assertEqual(values[-1]["status"], "PASS")

    def test_source_uncertainty_block_is_preserved(self):
        values = self._fixture(rho=0.98, cross_high=True)
        uncertainty, _, _, _, _, stability = values

        self.assertEqual(uncertainty["status"], "BLOCK")
        self.assertEqual(stability["status"], "BLOCK")
        self.assertIn("source_uncertainty_audit_blocked", stability["blockers"])

    def test_matrix_binding_drift_blocks_without_reinterpreting_pairs(self):
        values = self._fixture(rho=0.98)
        uncertainty, preregistration, matrix, cells, complete_link, _ = values
        correlations = {
            (pair["left_symbol"], pair["right_symbol"]): pair["pearson_correlation"]
            for pair in matrix["pairs"]
        }
        correlations[("A", "C")] = 0.2
        drifted_matrix = build_correlation_matrix_contract(
            matrix["symbols"],
            correlations,
            overlap_observations=60,
        )

        gate = evaluate_strategy_correlation_cluster_stability_gate(
            uncertainty,
            complete_link,
            preregistration=preregistration,
            correlation_matrix=drifted_matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

        self.assertEqual(gate["status"], "BLOCK")
        self.assertFalse(
            gate["stability_audit"]["input_binding"]["pair_matrix_exactly_bound"]
        )

    def test_coherently_resealed_pair_classification_is_rejected(self):
        values = self._fixture(rho=0.98)
        tampered = values[-1].copy()
        tampered["stability_audit"] = tampered["stability_audit"].copy()
        tampered["stability_audit"]["pair_results"] = [
            item.copy() for item in tampered["stability_audit"]["pair_results"]
        ]
        tampered["stability_audit"]["pair_results"][0]["classification"] = (
            "UNSTABLE_THRESHOLD"
        )
        tampered["stability_audit"] = seal_strict_canonical_document(
            tampered["stability_audit"], "audit_hash"
        )
        tampered["stability_audit_hash"] = tampered["stability_audit"]["audit_hash"]
        tampered = seal_strict_canonical_document(tampered, "gate_hash")

        verification = self._verify(values, tampered)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("cluster_stability_gate_contract_invalid", verification["blockers"])

    def test_native_type_alias_is_rejected(self):
        values = self._fixture(rho=0.98)
        tampered = values[-1].copy()
        tampered["consumer_only"] = 1
        tampered = seal_strict_canonical_document(tampered, "gate_hash")

        verification = self._verify(values, tampered)

        self.assertEqual(verification["status"], "BLOCK")

    def test_authority_escalation_is_rejected(self):
        values = self._fixture(rho=0.98)
        tampered = values[-1].copy()
        tampered["permissions"] = dict(tampered["permissions"])
        tampered["permissions"]["live_order_allowed"] = True
        tampered = seal_strict_canonical_document(tampered, "gate_hash")

        verification = self._verify(values, tampered)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
