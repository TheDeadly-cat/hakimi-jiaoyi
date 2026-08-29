import copy
import hashlib
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_structural_coverage_crosswalk_gate_v1
    as crosswalk_gate,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as cluster_gate,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1
    as upstream_tests,
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


class StrategyCorrelationPersistedCheckpointHistoryEffectiveBudgetStructuralCoverageCrosswalkGateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        upstream = (
            upstream_tests.StrategyCorrelationPersistedCheckpointHistoryCoverageEffectiveBudgetProvenanceBindingV1Tests
        )
        upstream.setUpClass()
        cls.provenance = upstream.preregistration
        cls.provenance_hash = cls.provenance["preregistration_hash"]
        cls.provenance_context = upstream.preregistration_context

        cls.history_context = {
            "expected_symbols": ["A", "B"],
            "expected_clusters": [
                {"cluster_id": "cluster-a", "members": ["A"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
            ],
            "expected_windows": ["window-01", "window-02"],
        }
        cls.history = cluster_gate.build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            cls.history_context["expected_symbols"],
            cls.history_context["expected_clusters"],
            cls.history_context["expected_windows"],
        )
        if cls.history is None:
            raise AssertionError("history cluster preregistration did not build")
        cls.history_hash = cls.history["preregistration_hash"]
        if cls.history_hash != "ae629b53618d92eded42696237544350b326e377da9174b8c9f8806d7d23cc62":
            raise AssertionError("history fixture preregistration fingerprint drifted")

        budget_context_root = cls.provenance_context[
            "budget_binding_preregistration_verification_context"
        ]
        cls.budget = budget_context_root["uncertainty_preregistration"]
        cls.budget_hash = cls.budget["preregistration_hash"]
        cls.budget_context = {
            "expected_symbols": list(cls.budget["expected_symbols"]),
            "expected_clusters": copy.deepcopy(cls.budget["expected_clusters"]),
            "expected_windows": list(cls.budget["expected_windows"]),
        }

        cls.window_crosswalk = [
            {
                "history_window_id": "window-01",
                "budget_window_id": "short",
                "relationship": crosswalk_gate.CROSSWALK_RELATIONSHIP,
            },
            {
                "history_window_id": "window-02",
                "budget_window_id": "long",
                "relationship": crosswalk_gate.CROSSWALK_RELATIONSHIP,
            },
        ]
        cls.preregistration = crosswalk_gate.build_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
            cls.provenance,
            cls.history,
            cls.budget,
            cls.window_crosswalk,
            expected_provenance_preregistration_hash=cls.provenance_hash,
            provenance_preregistration_verification_context=cls.provenance_context,
            expected_history_cluster_preregistration_hash=cls.history_hash,
            history_cluster_preregistration_verification_context=cls.history_context,
            expected_budget_cluster_preregistration_hash=cls.budget_hash,
            budget_cluster_preregistration_verification_context=cls.budget_context,
        )
        if cls.preregistration is None:
            raise AssertionError("structural coverage crosswalk preregistration did not build")
        cls.preregistration_hash = cls.preregistration["preregistration_hash"]
        cls.gate = cls._evaluate()
        cls.gate_hash = cls.gate["gate_hash"]

    @classmethod
    def _evaluate(
        cls,
        *,
        preregistration=None,
        provenance=None,
        history=None,
        budget=None,
        window_crosswalk=None,
        expected_crosswalk_hash=None,
        expected_provenance_hash=None,
        expected_history_hash=None,
        expected_budget_hash=None,
    ):
        return crosswalk_gate.evaluate_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
            cls.preregistration if preregistration is None else preregistration,
            cls.provenance if provenance is None else provenance,
            cls.history if history is None else history,
            cls.budget if budget is None else budget,
            cls.window_crosswalk if window_crosswalk is None else window_crosswalk,
            expected_crosswalk_preregistration_hash=cls.preregistration_hash
            if expected_crosswalk_hash is None
            else expected_crosswalk_hash,
            expected_provenance_preregistration_hash=cls.provenance_hash
            if expected_provenance_hash is None
            else expected_provenance_hash,
            provenance_preregistration_verification_context=cls.provenance_context,
            expected_history_cluster_preregistration_hash=cls.history_hash
            if expected_history_hash is None
            else expected_history_hash,
            history_cluster_preregistration_verification_context=cls.history_context,
            expected_budget_cluster_preregistration_hash=cls.budget_hash
            if expected_budget_hash is None
            else expected_budget_hash,
            budget_cluster_preregistration_verification_context=cls.budget_context,
        )

    def test_budget_symbol_without_persisted_history_is_blocked(self):
        self.assertEqual(self.gate["status"], crosswalk_gate.BLOCKED_UNIVERSE_STATUS)
        self.assertEqual(self.gate["coverage"]["budget_uncovered_symbols"], ["C"])
        self.assertFalse(self.gate["facts"]["all_budget_symbols_history_covered"])
        self.assertIn(
            "BUDGET_SYMBOLS_MISSING_PERSISTED_HISTORY_COVERAGE",
            self.gate["blockers"],
        )

    def test_policy_matches_without_equating_study_identity(self):
        self.assertTrue(self.gate["facts"]["policy_profile_match"])
        self.assertFalse(
            self.gate["facts"]["semantic_study_identity_equivalence_verified"]
        )
        self.assertFalse(self.gate["facts"]["window_order_identity_equal"])
        self.assertFalse(self.gate["facts"]["full_cluster_partition_identity_equal"])

    def test_shared_cluster_projection_matches_but_full_partition_does_not(self):
        self.assertEqual(self.gate["coverage"]["shared_symbols"], ["A", "B"])
        self.assertEqual(
            self.gate["coverage"]["history_shared_cluster_projection"],
            [["A"], ["B"]],
        )
        self.assertEqual(
            self.gate["coverage"]["budget_shared_cluster_projection"],
            [["A"], ["B"]],
        )
        self.assertTrue(self.gate["facts"]["shared_symbol_cluster_projection_equal"])
        self.assertFalse(self.gate["facts"]["full_cluster_partition_identity_equal"])

    def test_window_crosswalk_is_order_only_and_cannot_promote_semantics(self):
        self.assertEqual(
            self.preregistration["window_crosswalk"], self.window_crosswalk
        )
        self.assertFalse(self.gate["facts"]["window_label_issuer_binding_verified"])
        self.assertIn("WINDOW_LABEL_ISSUER_BINDING_UNPROVEN", self.gate["blockers"])
        self.assertFalse(
            self.gate["authority"]["semantic_identity_equivalence_claim_allowed"]
        )

    def test_resealed_history_preregistration_tamper_is_unknown(self):
        tampered = copy.deepcopy(self.history)
        tampered["expected_symbols"] = ["A", "C"]
        tampered = _reseal(tampered, "preregistration_hash")
        evaluated = self._evaluate(
            history=tampered,
            expected_history_hash=tampered["preregistration_hash"],
        )
        self.assertEqual(evaluated["status"], crosswalk_gate.UNKNOWN_STATUS)

    def test_resealed_budget_preregistration_tamper_is_unknown(self):
        tampered = copy.deepcopy(self.budget)
        tampered["expected_windows"] = ["short", "medium"]
        tampered = _reseal(tampered, "preregistration_hash")
        evaluated = self._evaluate(
            budget=tampered,
            expected_budget_hash=tampered["preregistration_hash"],
        )
        self.assertEqual(evaluated["status"], crosswalk_gate.UNKNOWN_STATUS)

    def test_duplicate_or_semantic_promotion_crosswalk_is_rejected(self):
        duplicate = copy.deepcopy(self.window_crosswalk)
        duplicate[1]["history_window_id"] = "window-01"
        self.assertIsNone(
            crosswalk_gate.build_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
                self.provenance,
                self.history,
                self.budget,
                duplicate,
                expected_provenance_preregistration_hash=self.provenance_hash,
                provenance_preregistration_verification_context=self.provenance_context,
                expected_history_cluster_preregistration_hash=self.history_hash,
                history_cluster_preregistration_verification_context=self.history_context,
                expected_budget_cluster_preregistration_hash=self.budget_hash,
                budget_cluster_preregistration_verification_context=self.budget_context,
            )
        )
        promotion = copy.deepcopy(self.window_crosswalk)
        promotion[0]["relationship"] = "SEMANTICALLY_EQUIVALENT"
        self.assertIsNone(
            crosswalk_gate.build_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
                self.provenance,
                self.history,
                self.budget,
                promotion,
                expected_provenance_preregistration_hash=self.provenance_hash,
                provenance_preregistration_verification_context=self.provenance_context,
                expected_history_cluster_preregistration_hash=self.history_hash,
                history_cluster_preregistration_verification_context=self.history_context,
                expected_budget_cluster_preregistration_hash=self.budget_hash,
                budget_cluster_preregistration_verification_context=self.budget_context,
            )
        )

    def test_resealed_authority_promotion_is_rejected(self):
        tampered = copy.deepcopy(self.gate)
        tampered["authority"]["effective_budget_activation_allowed"] = True
        tampered = _reseal(tampered, "gate_hash")
        self.assertFalse(
            crosswalk_gate.verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
                tampered,
                self.preregistration,
                self.provenance,
                self.history,
                self.budget,
                self.window_crosswalk,
                expected_gate_hash=tampered["gate_hash"],
                expected_crosswalk_preregistration_hash=self.preregistration_hash,
                expected_provenance_preregistration_hash=self.provenance_hash,
                provenance_preregistration_verification_context=self.provenance_context,
                expected_history_cluster_preregistration_hash=self.history_hash,
                history_cluster_preregistration_verification_context=self.history_context,
                expected_budget_cluster_preregistration_hash=self.budget_hash,
                budget_cluster_preregistration_verification_context=self.budget_context,
            )
        )

    def test_documents_reverify_exactly_and_all_authority_is_locked(self):
        self.assertTrue(
            crosswalk_gate.verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_preregistration_v1(
                self.preregistration,
                self.provenance,
                self.history,
                self.budget,
                self.window_crosswalk,
                expected_crosswalk_preregistration_hash=self.preregistration_hash,
                expected_provenance_preregistration_hash=self.provenance_hash,
                provenance_preregistration_verification_context=self.provenance_context,
                expected_history_cluster_preregistration_hash=self.history_hash,
                history_cluster_preregistration_verification_context=self.history_context,
                expected_budget_cluster_preregistration_hash=self.budget_hash,
                budget_cluster_preregistration_verification_context=self.budget_context,
            )
        )
        self.assertTrue(
            crosswalk_gate.verify_strategy_correlation_persisted_history_effective_budget_structural_coverage_crosswalk_gate_v1(
                self.gate,
                self.preregistration,
                self.provenance,
                self.history,
                self.budget,
                self.window_crosswalk,
                expected_gate_hash=self.gate_hash,
                expected_crosswalk_preregistration_hash=self.preregistration_hash,
                expected_provenance_preregistration_hash=self.provenance_hash,
                provenance_preregistration_verification_context=self.provenance_context,
                expected_history_cluster_preregistration_hash=self.history_hash,
                history_cluster_preregistration_verification_context=self.history_context,
                expected_budget_cluster_preregistration_hash=self.budget_hash,
                budget_cluster_preregistration_verification_context=self.budget_context,
            )
        )
        self.assertTrue(self.gate["authority"]["research_evidence_only"])
        for field, value in self.gate["authority"].items():
            if field != "research_evidence_only":
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
