from __future__ import annotations

import copy
import inspect
import json
import unittest

from exchange_terminal.services.portfolio_risk import evaluate_portfolio_risk
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_effective_bet_budget import (
    BUDGET_SCHEMA_VERSION,
    evaluate_strategy_correlation_cluster_effective_bet_budget,
    verify_strategy_correlation_cluster_effective_bet_budget,
)
from tests import test_strategy_correlation_cluster_complete_link as source_fixtures


class StrategyCorrelationClusterEffectiveBetBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_class = source_fixtures.StrategyCorrelationClusterCompleteLinkTests
        self.fixture = fixture_class(methodName="runTest")
        self.fixture.setUp()
        self.preregistration = self.fixture._preregistration()
        self.matrix = self.fixture._matrix(ac=0.92)
        self.audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.matrix,
        )

    def _evaluate(self, **overrides):
        arguments = {
            "equity": 10_000,
            "positions": [
                {"symbol": "B", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "D",
            "proposed_notional": 500,
        }
        arguments.update(overrides)
        return evaluate_strategy_correlation_cluster_effective_bet_budget(
            self.preregistration,
            self.matrix,
            self.audit,
            **arguments,
        ), arguments

    def test_existing_gate_passes_unrelated_proposal_while_v2_blocks_overlimit_cluster(self) -> None:
        legacy = evaluate_portfolio_risk(
            equity=10_000,
            positions=[
                {"symbol": "B", "notional": 2_500, "direction": "LONG"},
                {"symbol": "C", "notional": 2_500, "direction": "LONG"},
            ],
            proposed_symbol="D",
            proposed_notional=500,
            correlations={"B|C": 0.92, "B|D": 0.10, "C|D": 0.10},
        )
        budget, _ = self._evaluate(
            positions=[
                {"symbol": "B", "notional": 2_500, "direction": "LONG"},
                {"symbol": "C", "notional": 2_500, "direction": "LONG"},
            ]
        )

        self.assertEqual(legacy["status"], "PASS")
        self.assertEqual(legacy["exposure_after"]["correlated_cluster_pct"], 5.0)
        self.assertEqual(budget["status"], "BLOCK")
        chain = next(
            item for item in budget["cluster_exposures"] if item["cluster_id"] == "CHAIN"
        )
        self.assertEqual(chain["gross_exposure_pct"], 50.0)
        self.assertEqual(chain["status"], "BLOCK")

    def test_every_active_cluster_is_evaluated_when_within_budget(self) -> None:
        budget, _ = self._evaluate()

        self.assertEqual(budget["status"], "PASS")
        self.assertEqual(
            [item["cluster_id"] for item in budget["cluster_exposures"]],
            ["CHAIN", "D"],
        )
        self.assertTrue(budget["facts"]["all_active_clusters_evaluated"])
        self.assertFalse(budget["facts"]["proposal_centered_only"])

    def test_correlated_symbols_count_as_one_effective_bet(self) -> None:
        budget, _ = self._evaluate(
            positions=[
                {"symbol": "B", "notional": 1_000, "direction": "LONG"},
                {"symbol": "C", "notional": 1_000, "direction": "LONG"},
            ],
            proposed_symbol="A",
            proposed_notional=1_000,
        )

        self.assertEqual(budget["status"], "PASS")
        self.assertEqual(budget["portfolio"]["symbol_ticket_count"], 3)
        self.assertEqual(budget["portfolio"]["effective_independent_bet_count"], 1)
        self.assertEqual(budget["portfolio"]["correlated_duplicate_ticket_count"], 2)
        self.assertTrue(budget["facts"]["correlated_symbols_counted_as_one"])

    def test_missing_cluster_assignment_fails_closed(self) -> None:
        budget, _ = self._evaluate(proposed_symbol="X", proposed_notional=100)

        self.assertEqual(budget["status"], "BLOCK")
        self.assertIsNone(budget["portfolio"]["effective_independent_bet_count"])
        self.assertIn("cluster_assignment_missing:X", budget["blockers"])
        self.assertFalse(budget["facts"]["all_active_clusters_evaluated"])

    def test_blocked_complete_link_decision_blocks_budget(self) -> None:
        blocked_matrix = self.fixture._matrix(ac=0.10)
        blocked_audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            blocked_matrix,
        )
        budget = evaluate_strategy_correlation_cluster_effective_bet_budget(
            self.preregistration,
            blocked_matrix,
            blocked_audit,
            equity=10_000,
            positions=[],
            proposed_symbol="D",
            proposed_notional=500,
        )

        self.assertEqual(blocked_audit["status"], "BLOCK")
        self.assertEqual(budget["status"], "BLOCK")
        self.assertIn("complete_link_decision_block", budget["blockers"])

    def test_tampered_source_contract_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.audit)
        tampered["status"] = "PASS" if self.audit["status"] == "BLOCK" else "BLOCK"
        budget = evaluate_strategy_correlation_cluster_effective_bet_budget(
            self.preregistration,
            self.matrix,
            tampered,
            equity=10_000,
            positions=[],
            proposed_symbol="D",
            proposed_notional=500,
        )

        self.assertEqual(budget["status"], "BLOCK")
        self.assertIn("complete_link_contract_unverified", budget["blockers"])

    def test_long_short_members_still_use_conservative_gross_budget(self) -> None:
        budget, _ = self._evaluate(
            positions=[
                {"symbol": "B", "notional": 2_300, "direction": "LONG"},
                {"symbol": "C", "notional": 2_300, "direction": "SHORT"},
            ],
            proposed_symbol="D",
            proposed_notional=500,
        )

        self.assertEqual(budget["status"], "BLOCK")
        chain = next(
            item for item in budget["cluster_exposures"] if item["cluster_id"] == "CHAIN"
        )
        self.assertEqual(chain["gross_exposure_pct"], 46.0)
        self.assertFalse(budget["facts"]["direction_netting_used"])

    def test_same_symbol_positions_are_one_ticket_but_all_gross_is_counted(self) -> None:
        budget, _ = self._evaluate(
            positions=[
                {"symbol": "B", "notional": 1_000, "direction": "LONG"},
                {"symbol": "B", "notional": 800, "direction": "SHORT"},
            ],
            proposed_symbol="D",
            proposed_notional=500,
        )

        self.assertEqual(budget["portfolio"]["symbol_ticket_count"], 2)
        chain = next(
            item for item in budget["cluster_exposures"] if item["cluster_id"] == "CHAIN"
        )
        self.assertEqual(chain["gross_notional"], 1_800.0)

    def test_native_aliases_and_invalid_limits_fail_closed(self) -> None:
        cases = [
            {"equity": True},
            {"proposed_notional": False},
            {"proposed_direction": 1},
            {"max_cluster_gross_pct": "45"},
            {"max_cluster_gross_pct": 101},
            {"positions": [{"symbol": "B", "notional": True, "direction": "LONG"}]},
            {"risk_increasing": 1},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                budget, _ = self._evaluate(**overrides)
                self.assertEqual(budget["status"], "BLOCK")

    def test_risk_reduction_path_never_requires_cluster_sources(self) -> None:
        budget = evaluate_strategy_correlation_cluster_effective_bet_budget(
            None,
            None,
            None,
            equity=0,
            positions=None,
            proposed_symbol=None,
            proposed_notional=None,
            risk_increasing=False,
        )

        self.assertEqual(budget["status"], "PASS")
        self.assertEqual(budget["decision"], "RISK_REDUCTION_PATH")
        self.assertEqual(budget["source"]["complete_link_decision"], "NOT_EVALUATED")
        self.assertFalse(budget["authority"]["paper_authorized"])

    def test_inputs_are_not_mutated_and_private_source_payloads_are_not_embedded(self) -> None:
        preregistration = copy.deepcopy(self.preregistration)
        matrix = copy.deepcopy(self.matrix)
        audit = copy.deepcopy(self.audit)
        positions = [{"symbol": "B", "notional": 1_000, "direction": "LONG"}]
        before = copy.deepcopy((preregistration, matrix, audit, positions))
        budget = evaluate_strategy_correlation_cluster_effective_bet_budget(
            preregistration,
            matrix,
            audit,
            equity=10_000,
            positions=positions,
            proposed_symbol="D",
            proposed_notional=500,
        )

        self.assertEqual((preregistration, matrix, audit, positions), before)
        serialized = json.dumps(budget, sort_keys=True)
        self.assertNotIn("pair_results", serialized)
        self.assertNotIn("pearson_correlation", serialized)
        self.assertNotIn("matrix_hash", serialized)
        self.assertFalse(budget["facts"]["source_documents_embedded"])
        self.assertFalse(budget["facts"]["raw_correlations_embedded"])

    def test_exact_rebuild_rejects_decision_and_native_type_reseal(self) -> None:
        budget, arguments = self._evaluate()
        verification = verify_strategy_correlation_cluster_effective_bet_budget(
            budget,
            self.preregistration,
            self.matrix,
            self.audit,
            **arguments,
        )
        self.assertEqual(verification["status"], "PASS")

        for mutation in (
            lambda value: value.update({"decision": "READY"}),
            lambda value: value["authority"].update({"paper_authorized": True}),
            lambda value: value["facts"].update({"direction_netting_used": 0}),
        ):
            tampered = copy.deepcopy(budget)
            mutation(tampered)
            self.assertEqual(
                verify_strategy_correlation_cluster_effective_bet_budget(
                    tampered,
                    self.preregistration,
                    self.matrix,
                    self.audit,
                    **arguments,
                )["status"],
                "BLOCK",
            )

    def test_schema_authority_hash_and_exports_remain_research_only(self) -> None:
        budget, _ = self._evaluate()

        self.assertEqual(budget["schema_version"], BUDGET_SCHEMA_VERSION)
        self.assertRegex(budget["budget_hash"], r"^[0-9a-f]{64}$")
        self.assertTrue(budget["authority"]["descriptive_only"])
        for field, value in budget["authority"].items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(budget, sort_keys=True).upper())
        for function in (
            evaluate_strategy_correlation_cluster_effective_bet_budget,
            verify_strategy_correlation_cluster_effective_bet_budget,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {"runtime", "database", "cache", "current", "order", "broker"}
                )
            )


if __name__ == "__main__":
    unittest.main()
