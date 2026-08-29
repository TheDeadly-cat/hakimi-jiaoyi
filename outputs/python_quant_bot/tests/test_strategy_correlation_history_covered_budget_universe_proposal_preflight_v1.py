import copy
import hashlib
import json
import unittest

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_proposal_preflight_v1
    as preflight,
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


class StrategyCorrelationHistoryCoveredBudgetUniverseProposalPreflightV1Tests(
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
        cls.projected = cls._evaluate("A")
        cls.excluded = cls._evaluate("C")
        cls.unknown = cls._evaluate("D")

    @classmethod
    def _evaluate(cls, symbol, *, projection=None, projection_hash=None):
        return preflight.evaluate_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
            cls.projection if projection is None else projection,
            symbol,
            expected_projection_preregistration_hash=cls.projection_hash
            if projection_hash is None
            else projection_hash,
            projection_verification_context=cls.context,
        )

    def test_excluded_symbol_is_blocked_by_history_coverage_policy(self):
        self.assertEqual(self.excluded["status"], preflight.EXCLUDED_STATUS)
        self.assertTrue(self.excluded["facts"]["excluded_universe_member"])
        self.assertFalse(self.excluded["facts"]["projected_universe_member"])
        self.assertIn(
            "PROPOSED_SYMBOL_EXCLUDED_BY_HISTORY_COVERAGE_POLICY",
            self.excluded["blockers"],
        )

    def test_projected_symbol_stays_blocked_until_fresh_evidence(self):
        self.assertEqual(
            self.projected["status"], preflight.PROJECTED_IMMATURE_STATUS
        )
        self.assertTrue(self.projected["facts"]["projected_universe_member"])
        self.assertFalse(
            self.projected["facts"]["fresh_projected_budget_evidence_completed"]
        )
        self.assertIn(
            "FRESH_PROJECTED_EFFECTIVE_BUDGET_BINDING_NOT_PROVIDED",
            self.projected["blockers"],
        )

    def test_unknown_symbol_is_unknown_and_not_admitted(self):
        self.assertEqual(self.unknown["status"], preflight.UNKNOWN_STATUS)
        self.assertFalse(self.unknown["facts"]["known_in_budget_source"])
        self.assertFalse(self.unknown["facts"]["known_in_history_source"])
        self.assertFalse(self.unknown["facts"]["proposal_admission_allowed"])

    def test_decision_path_is_neutral_source_gap_maturity_permission(self):
        self.assertEqual(
            list(self.projected["decision_path"]),
            ["source", "gap", "maturity", "permission"],
        )
        self.assertEqual(
            self.projected["decision_path"]["source"],
            "ADR0365_PROJECTION_EXACTLY_VERIFIED",
        )
        self.assertEqual(
            self.projected["decision_path"]["permission"], "NOT_AUTHORIZED"
        )
        self.assertNotIn("READY", json.dumps(self.projected, sort_keys=True))

    def test_public_output_redacts_raw_symbol_and_cluster_id(self):
        sentinel = "PRIVATE-SYMBOL-DO-NOT-ECHO"
        evidence = self._evaluate(sentinel)
        rendered = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(sentinel, rendered)
        self.assertNotIn("cluster-c", json.dumps(self.excluded, sort_keys=True))
        self.assertEqual(
            evidence["proposal"]["symbol_sha256"],
            hashlib.sha256(sentinel.encode("utf-8")).hexdigest(),
        )

    def test_noncanonical_symbol_is_rejected(self):
        self.assertIsNone(self._evaluate(""))
        self.assertIsNone(self._evaluate("symbol with spaces"))
        self.assertIsNone(self._evaluate("x" * 65))

    def test_resealed_projection_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.projection)
        tampered["derivation"]["excluded_symbols"] = []
        tampered = _reseal(tampered, "projection_preregistration_hash")
        self.assertIsNone(
            self._evaluate(
                "C",
                projection=tampered,
                projection_hash=tampered["projection_preregistration_hash"],
            )
        )

    def test_resealed_permission_promotion_is_rejected(self):
        tampered = copy.deepcopy(self.projected)
        tampered["decision_path"]["permission"] = "AUTHORIZED"
        tampered["authority"]["proposal_admission_allowed"] = True
        tampered = _reseal(tampered, "preflight_hash")
        self.assertFalse(
            preflight.verify_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
                tampered,
                self.projection,
                "A",
                expected_preflight_hash=tampered["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )

    def test_preflight_is_deterministic_exactly_verifiable_and_locked(self):
        rebuilt = self._evaluate("A")
        self.assertEqual(rebuilt, self.projected)
        self.assertTrue(
            preflight.verify_strategy_correlation_history_covered_budget_universe_proposal_preflight_v1(
                self.projected,
                self.projection,
                "A",
                expected_preflight_hash=self.projected["preflight_hash"],
                expected_projection_preregistration_hash=self.projection_hash,
                projection_verification_context=self.context,
            )
        )
        self.assertFalse(self.projected["registered"])
        self.assertTrue(self.projected["authority"]["research_evidence_only"])
        for field, value in self.projected["authority"].items():
            if field != "research_evidence_only":
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
