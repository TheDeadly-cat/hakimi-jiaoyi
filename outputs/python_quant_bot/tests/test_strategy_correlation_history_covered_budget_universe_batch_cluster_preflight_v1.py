import copy
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1
    as batch_preflight,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_effective_budget_covered_universe_projection_v1
    as projection_tests,
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


class StrategyCorrelationHistoryCoveredBudgetUniverseBatchClusterPreflightV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        upstream = (
            projection_tests.StrategyCorrelationPersistedCheckpointHistoryEffectiveBudgetCoveredUniverseProjectionV1Tests
        )
        upstream.setUpClass()
        cls.projection = upstream.projection
        cls.projection_hash = upstream.projection_hash
        cls.context = {
            "structural_coverage_gate": upstream.structural_gate,
            "expected_structural_coverage_gate_hash": upstream.structural_gate_hash,
            "structural_gate_verification_context": upstream.context,
        }
        cls.projected = cls._evaluate(["A", "B"])
        cls.excluded = cls._evaluate(["A", "C"])
        cls.unknown = cls._evaluate(["A", "D"])

    @classmethod
    def _evaluate(cls, symbols, *, projection=None, projection_hash=None):
        return batch_preflight.evaluate_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
            cls.projection if projection is None else projection,
            symbols,
            expected_projection_preregistration_hash=cls.projection_hash
            if projection_hash is None
            else projection_hash,
            projection_verification_context=cls.context,
        )

    def test_current_projected_batch_counts_unique_source_clusters(self):
        self.assertEqual(
            self.projected["status"], batch_preflight.PROJECTED_IMMATURE_STATUS
        )
        self.assertEqual(
            self.projected["ticket_summary"]["unique_projected_symbol_count"], 2
        )
        self.assertEqual(
            self.projected["ticket_summary"]["effective_projected_ticket_count"],
            2,
        )
        self.assertFalse(self.projected["facts"]["batch_admission_allowed"])

    def test_excluded_member_blocks_the_batch(self):
        self.assertEqual(self.excluded["status"], batch_preflight.EXCLUDED_STATUS)
        self.assertEqual(self.excluded["ticket_summary"]["excluded_symbol_count"], 1)
        self.assertIn(
            "BATCH_CONTAINS_HISTORY_COVERAGE_EXCLUDED_SYMBOL",
            self.excluded["blockers"],
        )

    def test_unknown_member_has_precedence_over_other_batch_members(self):
        self.assertEqual(self.unknown["status"], batch_preflight.UNKNOWN_STATUS)
        self.assertEqual(self.unknown["ticket_summary"]["unknown_symbol_count"], 1)
        mixed = self._evaluate(["A", "C", "D"])
        self.assertEqual(mixed["status"], batch_preflight.UNKNOWN_STATUS)

    def test_duplicate_proposals_count_as_one_effective_ticket(self):
        duplicate = self._evaluate(["A", "A"])
        self.assertEqual(duplicate["ticket_summary"]["proposal_occurrence_count"], 2)
        self.assertEqual(duplicate["ticket_summary"]["unique_proposal_symbol_count"], 1)
        self.assertEqual(
            duplicate["ticket_summary"]["effective_projected_ticket_count"], 1
        )

    def test_correlated_symbols_collapse_to_one_ticket(self):
        derivation = batch_preflight.derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
            ["A", "B"],
            ["A", "B", "C"],
            [
                {"cluster_id": "cluster-ab", "members": ["A", "B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ],
            ["A", "B"],
            ["C"],
        )
        self.assertIsNotNone(derivation)
        self.assertEqual(derivation["counts"]["unique_projected_symbol_count"], 2)
        self.assertEqual(derivation["counts"]["effective_projected_ticket_count"], 1)
        self.assertEqual(derivation["counts"]["cluster_collapse_reduction_count"], 1)

    def test_partial_or_overlapping_source_partition_is_rejected(self):
        partial = batch_preflight.derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
            ["A"],
            ["A", "B"],
            [{"cluster_id": "cluster-ab", "members": ["A", "B"]}],
            ["A"],
            ["B"],
        )
        overlapping = batch_preflight.derive_strategy_correlation_batch_cluster_effective_ticket_summary_v1(
            ["A"],
            ["A", "B"],
            [
                {"cluster_id": "one", "members": ["A", "B"]},
                {"cluster_id": "two", "members": ["B"]},
            ],
            ["A", "B"],
            [],
        )
        self.assertIsNone(partial)
        self.assertIsNone(overlapping)

    def test_output_is_hash_only_and_neutral(self):
        sentinel = "PRIVATE-SYMBOL-DO-NOT-ECHO"
        result = self._evaluate([sentinel])
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn(sentinel, rendered)
        self.assertNotIn("cluster-a", json.dumps(self.projected, sort_keys=True))
        self.assertNotIn("READY", rendered)
        self.assertEqual(result["decision_path"]["permission"], "NOT_AUTHORIZED")

    def test_resealed_projection_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.projection)
        tampered["derivation"]["projected_symbols"] = ["A", "B", "C"]
        tampered = _reseal(tampered, "projection_preregistration_hash")
        self.assertIsNone(
            self._evaluate(
                ["A"],
                projection=tampered,
                projection_hash=tampered["projection_preregistration_hash"],
            )
        )

    def test_resealed_permission_promotion_fails_exact_verification(self):
        self.assertTrue(
            batch_preflight.verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
                self.projected,
                self.projection,
                ["A", "B"],
                expected_preflight_hash=self.projected["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(self.projected)
        tampered["decision_path"]["permission"] = "AUTHORIZED"
        tampered["authority"]["batch_admission_allowed"] = True
        tampered = _reseal(tampered, "preflight_hash")
        self.assertFalse(
            batch_preflight.verify_strategy_correlation_history_covered_budget_universe_batch_cluster_preflight_v1(
                tampered,
                self.projection,
                ["A", "B"],
                expected_preflight_hash=tampered["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        self.assertTrue(self.projected["authority"]["research_evidence_only"])
        for field, value in self.projected["authority"].items():
            if field != "research_evidence_only":
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
