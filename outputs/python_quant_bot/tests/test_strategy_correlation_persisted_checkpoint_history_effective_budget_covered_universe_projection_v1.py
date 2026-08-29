import copy
import hashlib
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_covered_universe_projection_v1
    as covered_projection,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_effective_budget_structural_coverage_crosswalk_gate_v1
    as structural_tests,
)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(document, hash_field):
    mutated = copy.deepcopy(document)
    mutated.pop(hash_field, None)
    mutated[hash_field] = _digest(mutated)
    return mutated


class StrategyCorrelationPersistedCheckpointHistoryEffectiveBudgetCoveredUniverseProjectionV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        upstream = (
            structural_tests.StrategyCorrelationPersistedCheckpointHistoryEffectiveBudgetStructuralCoverageCrosswalkGateV1Tests
        )
        upstream.setUpClass()
        cls.structural_gate = upstream.gate
        cls.structural_gate_hash = upstream.gate_hash
        cls.context = {
            "crosswalk_preregistration": upstream.preregistration,
            "provenance_preregistration": upstream.provenance,
            "history_cluster_preregistration": upstream.history,
            "budget_cluster_preregistration": upstream.budget,
            "window_crosswalk": upstream.window_crosswalk,
            "expected_crosswalk_preregistration_hash": upstream.preregistration_hash,
            "expected_provenance_preregistration_hash": upstream.provenance_hash,
            "provenance_preregistration_verification_context": upstream.provenance_context,
            "expected_history_cluster_preregistration_hash": upstream.history_hash,
            "history_cluster_preregistration_verification_context": upstream.history_context,
            "expected_budget_cluster_preregistration_hash": upstream.budget_hash,
            "budget_cluster_preregistration_verification_context": upstream.budget_context,
        }
        cls.projection = covered_projection.build_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
            cls.structural_gate,
            expected_structural_coverage_gate_hash=cls.structural_gate_hash,
            structural_gate_verification_context=cls.context,
        )
        if cls.projection is None:
            raise AssertionError("covered-universe projection did not build")
        cls.projection_hash = cls.projection["projection_preregistration_hash"]

    def test_current_projection_retains_ab_and_excludes_c(self):
        derivation = self.projection["derivation"]
        self.assertEqual(derivation["projected_symbols"], ["A", "B"])
        self.assertEqual(derivation["excluded_symbols"], ["C"])
        self.assertEqual(
            [cluster["cluster_id"] for cluster in derivation["projected_clusters"]],
            ["cluster-a", "cluster-b"],
        )
        self.assertEqual(derivation["excluded_cluster_ids"], ["cluster-c"])

    def test_projected_preregistration_is_fresh_and_exact(self):
        projected = self.projection["projected_cluster_preregistration"]
        original = self.context["budget_cluster_preregistration"]
        self.assertNotEqual(
            projected["preregistration_hash"], original["preregistration_hash"]
        )
        self.assertEqual(projected["expected_symbols"], ["A", "B"])
        self.assertEqual(projected["expected_windows"], ["short", "long"])
        self.assertTrue(
            cluster_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
                projected,
                expected_symbols=["A", "B"],
                expected_clusters=[
                    {"cluster_id": "cluster-a", "members": ["A"]},
                    {"cluster_id": "cluster-b", "members": ["B"]},
                ],
                expected_windows=["short", "long"],
                expected_preregistration_hash=projected["preregistration_hash"],
            )
        )

    def test_fresh_evidence_is_required_and_original_reuse_is_forbidden(self):
        contract = self.projection["fresh_evidence_contract"]
        self.assertEqual(
            contract["required_artifacts_in_order"],
            [
                "PROJECTED_MULTI_WINDOW_AUDITS_V1",
                "PROJECTED_MULTI_WINDOW_CLUSTER_GATE_V1",
                "PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_PREREGISTRATION_V1",
                "PROJECTED_UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_EVALUATION_V1",
            ],
        )
        self.assertFalse(contract["original_full_universe_evidence_reuse_allowed"])
        self.assertFalse(contract["projected_evaluation_completed"])
        self.assertFalse(contract["readonly_projection_adapter_eligible"])

    def test_partially_covered_cluster_is_excluded_atomically(self):
        derivation = covered_projection.derive_strategy_correlation_cluster_atomic_history_covered_budget_universe_projection_v1(
            ["A", "B", "C"],
            [
                {"cluster_id": "mixed-ac", "members": ["A", "C"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
            ],
            ["A", "B"],
        )
        self.assertIsNotNone(derivation)
        self.assertEqual(derivation["projected_symbols"], ["B"])
        self.assertEqual(derivation["excluded_symbols"], ["A", "C"])
        self.assertEqual(derivation["partially_covered_cluster_ids"], ["mixed-ac"])
        self.assertEqual(
            derivation["projected_clusters"],
            [{"cluster_id": "cluster-b", "members": ["B"]}],
        )

    def test_overlapping_or_incomplete_partition_is_rejected(self):
        overlapping = covered_projection.derive_strategy_correlation_cluster_atomic_history_covered_budget_universe_projection_v1(
            ["A", "B"],
            [
                {"cluster_id": "one", "members": ["A", "B"]},
                {"cluster_id": "two", "members": ["B"]},
            ],
            ["A"],
        )
        incomplete = covered_projection.derive_strategy_correlation_cluster_atomic_history_covered_budget_universe_projection_v1(
            ["A", "B"],
            [{"cluster_id": "one", "members": ["A"]}],
            ["A"],
        )
        self.assertIsNone(overlapping)
        self.assertIsNone(incomplete)

    def test_resealed_structural_gate_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.structural_gate)
        tampered["coverage"]["budget_uncovered_symbols"] = []
        tampered = _reseal(tampered, "gate_hash")
        self.assertIsNone(
            covered_projection.build_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
                tampered,
                expected_structural_coverage_gate_hash=tampered["gate_hash"],
                structural_gate_verification_context=self.context,
            )
        )

    def test_resealed_projected_preregistration_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.projection)
        projected = tampered["projected_cluster_preregistration"]
        projected["expected_symbols"] = ["A", "B", "C"]
        tampered["projected_cluster_preregistration"] = _reseal(
            projected, "preregistration_hash"
        )
        tampered = _reseal(tampered, "projection_preregistration_hash")
        self.assertFalse(
            covered_projection.verify_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
                tampered,
                self.structural_gate,
                expected_projection_preregistration_hash=tampered[
                    "projection_preregistration_hash"
                ],
                expected_structural_coverage_gate_hash=self.structural_gate_hash,
                structural_gate_verification_context=self.context,
            )
        )

    def test_resealed_authority_promotion_is_rejected(self):
        tampered = copy.deepcopy(self.projection)
        tampered["authority"]["readonly_projection_adapter_activation_allowed"] = True
        tampered = _reseal(tampered, "projection_preregistration_hash")
        self.assertFalse(
            covered_projection.verify_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
                tampered,
                self.structural_gate,
                expected_projection_preregistration_hash=tampered[
                    "projection_preregistration_hash"
                ],
                expected_structural_coverage_gate_hash=self.structural_gate_hash,
                structural_gate_verification_context=self.context,
            )
        )

    def test_projection_reverifies_and_all_authority_stays_locked(self):
        self.assertTrue(
            covered_projection.verify_strategy_correlation_persisted_history_effective_budget_covered_universe_projection_v1(
                self.projection,
                self.structural_gate,
                expected_projection_preregistration_hash=self.projection_hash,
                expected_structural_coverage_gate_hash=self.structural_gate_hash,
                structural_gate_verification_context=self.context,
            )
        )
        self.assertEqual(
            self.projection["status"], covered_projection.PREREGISTERED_STATUS
        )
        self.assertFalse(
            self.projection["facts"]["fresh_projected_budget_evidence_completed"]
        )
        self.assertTrue(self.projection["authority"]["research_evidence_only"])
        for field, value in self.projection["authority"].items():
            if field != "research_evidence_only":
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
