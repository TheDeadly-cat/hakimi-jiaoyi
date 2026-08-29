from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest import mock

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v2 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_complete_link import (
    StrategyCorrelationClusterCompleteLinkTests,
)


class StrategyCorrelationClusterEffectiveBetBudgetV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        fixture = StrategyCorrelationClusterCompleteLinkTests(methodName="runTest")
        fixture.setUp()
        self.preregistration = fixture._preregistration()
        self.matrix = fixture._matrix(ac=0.92)
        self.audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.matrix,
        )
        self.base_inputs = {
            "equity": 10_000,
            "positions": [
                {"symbol": "B", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "D",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": True,
        }

    def _evaluate(self, **overrides: object):
        inputs = copy.deepcopy(self.base_inputs)
        inputs.update(copy.deepcopy(overrides))
        return (
            subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
                self.preregistration,
                self.matrix,
                self.audit,
                **copy.deepcopy(inputs),
            ),
            inputs,
        )

    def _verify(self, document: object, inputs: dict[str, object]):
        return subject.verify_strategy_correlation_cluster_effective_bet_budget_v2(
            document,
            self.preregistration,
            self.matrix,
            self.audit,
            **copy.deepcopy(inputs),
        )

    def test_reproduced_44_plus_2_gap_is_blocked_by_weighted_gate(self) -> None:
        document, _ = self._evaluate(
            positions=[{"symbol": "B", "notional": 4_400, "direction": "LONG"}],
            proposed_symbol="D",
            proposed_notional=200,
        )
        self.assertEqual(document["source"]["v1_status"], "PASS")
        self.assertEqual(document["portfolio"]["unweighted_effective_cluster_count"], 2)
        self.assertEqual(document["portfolio"]["weighted_effective_cluster_count"], 1.090722)
        self.assertEqual(
            document["portfolio"]["dominant_cluster_share_of_active_gross_pct"],
            95.6522,
        )
        self.assertTrue(document["portfolio"]["weighted_diversification_gate_applied"])
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("weighted_effective_cluster_gate", document["blockers"])

    def test_balanced_25_plus_25_passes_above_trigger(self) -> None:
        document, _ = self._evaluate(
            positions=[{"symbol": "B", "notional": 2_500, "direction": "LONG"}],
            proposed_symbol="D",
            proposed_notional=2_500,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "PASS_WEIGHTED_RESEARCH_BUDGET")
        self.assertEqual(document["portfolio"]["weighted_effective_cluster_count"], 2.0)
        self.assertEqual(
            document["portfolio"]["dominant_cluster_share_of_active_gross_pct"],
            50.0,
        )
        self.assertTrue(document["portfolio"]["weighted_diversification_gate_applied"])

    def test_35_plus_15_passes_preregistered_minimum(self) -> None:
        document, _ = self._evaluate(
            positions=[{"symbol": "B", "notional": 3_500, "direction": "LONG"}],
            proposed_symbol="D",
            proposed_notional=1_500,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["portfolio"]["weighted_effective_cluster_count"], 1.724138)

    def test_single_cluster_at_or_below_trigger_is_not_blocked(self) -> None:
        for notional in (4_400, 4_500):
            with self.subTest(notional=notional):
                document, _ = self._evaluate(
                    positions=[],
                    proposed_symbol="B",
                    proposed_notional=notional,
                )
                self.assertEqual(document["status"], "PASS")
                self.assertEqual(
                    document["portfolio"]["weighted_effective_cluster_count"],
                    1.0,
                )
                self.assertFalse(
                    document["portfolio"]["weighted_diversification_gate_applied"]
                )

    def test_v1_cluster_gross_block_is_preserved(self) -> None:
        document, _ = self._evaluate(
            positions=[{"symbol": "B", "notional": 4_600, "direction": "LONG"}],
            proposed_symbol="D",
            proposed_notional=100,
        )
        self.assertEqual(document["source"]["v1_status"], "BLOCK")
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("v1_budget_gate", document["blockers"])

    def test_missing_assignment_and_source_blocks_are_preserved(self) -> None:
        missing, _ = self._evaluate(proposed_symbol="X", proposed_notional=100)
        self.assertEqual(missing["source"]["v1_status"], "BLOCK")
        self.assertEqual(missing["status"], "BLOCK")
        blocked = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            None,
            None,
            None,
            **copy.deepcopy(self.base_inputs),
        )
        self.assertEqual(blocked["status"], "BLOCK")

    def test_risk_reduction_path_remains_source_free_and_not_applicable(self) -> None:
        document = subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            None,
            None,
            None,
            equity=0,
            positions=None,
            proposed_symbol=None,
            proposed_notional=None,
            risk_increasing=False,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "RISK_REDUCTION_PATH")
        self.assertTrue(document["facts"]["weighted_diversification_not_applicable"])
        self.assertFalse(document["portfolio"]["weighted_diversification_gate_applied"])

    def test_strict_input_aliases_inherit_fail_closed_v1_decision(self) -> None:
        for overrides in (
            {"equity": True},
            {"proposed_notional": False},
            {"max_cluster_gross_pct": "45"},
            {"risk_increasing": 1},
        ):
            with self.subTest(overrides=overrides):
                document, _ = self._evaluate(**overrides)
                self.assertEqual(document["status"], "BLOCK")
                self.assertNotEqual(document["source"]["v1_status"], "PASS")

    def test_forged_v1_receipt_cannot_promote_malformed_cluster_metrics(self) -> None:
        malformed = {
            "schema_version": subject.budget_v1.BUDGET_SCHEMA_VERSION,
            "static_fingerprint": subject.budget_v1.STATIC_FINGERPRINT,
            "status": "PASS",
            "decision": "PASS_RESEARCH_BUDGET",
            "budget_hash": "1" * 64,
            "portfolio": {},
            "cluster_exposures": [
                {
                    "cluster_id": "CHAIN",
                    "symbols": ["B"],
                    "symbol_ticket_count": 1,
                    "gross_notional": True,
                    "gross_exposure_pct": 1.0,
                    "limit_pct": 45.0,
                    "status": "PASS",
                }
            ],
            "facts": {"risk_increasing": True},
            "authority": {
                "descriptive_only": True,
                "current_admission_allowed": False,
            },
        }
        forged_receipt = {
            "schema_version": subject.budget_v1.BUDGET_VERIFICATION_SCHEMA_VERSION,
            "status": "PASS",
            "blockers": [],
            "budget_decision": "PASS_RESEARCH_BUDGET",
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with mock.patch.object(subject, "_EVALUATE_V1", return_value=malformed), mock.patch.object(
            subject, "_VERIFY_V1", return_value=forged_receipt
        ):
            document, _ = self._evaluate()
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("weighted_cluster_metrics", document["blockers"])

    def test_output_is_summary_only_and_does_not_embed_cluster_rows(self) -> None:
        document, _ = self._evaluate()
        encoded = json.dumps(document, sort_keys=True)
        self.assertNotIn("cluster_exposures", encoded)
        self.assertNotIn("gross_notional", encoded)
        self.assertNotIn("pearson_correlation", encoded)
        self.assertFalse(document["facts"]["cluster_exposure_rows_embedded"])

    def test_inputs_are_not_mutated(self) -> None:
        preregistration = copy.deepcopy(self.preregistration)
        matrix = copy.deepcopy(self.matrix)
        audit = copy.deepcopy(self.audit)
        inputs = copy.deepcopy(self.base_inputs)
        expected = copy.deepcopy((preregistration, matrix, audit, inputs))
        subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            preregistration,
            matrix,
            audit,
            **inputs,
        )
        self.assertEqual((preregistration, matrix, audit, inputs), expected)

    def test_exact_verifier_rejects_resealed_decision_metric_and_authority_tamper(self) -> None:
        document, inputs = self._evaluate()
        self.assertEqual(self._verify(document, inputs)["status"], "PASS")
        variants = []
        decision = copy.deepcopy(document)
        decision["decision"] = "R" + "EADY"
        variants.append(decision)
        metric = copy.deepcopy(document)
        metric["portfolio"]["weighted_effective_cluster_count"] = 9.0
        variants.append(metric)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for value in variants:
            with self.subTest(value=value):
                resealed = seal_strict_canonical_document(value, "budget_v2_hash")
                verification = self._verify(resealed, inputs)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["budget_decision"], "UNKNOWN")

    def test_v1_implementation_pin_matches_current_file(self) -> None:
        path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget.py"
        )
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.V1_IMPLEMENTATION_SHA256,
        )

    def test_schema_policy_authority_and_exports_are_research_only(self) -> None:
        document, _ = self._evaluate()
        self.assertEqual(document["schema_version"], subject.BUDGET_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(
            document["policy"]["minimum_weighted_effective_cluster_count"],
            1.5,
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )
        self.assertFalse(document["facts"]["runtime_gate_integrated"])
        self.assertFalse(document["facts"]["profitability_proven"])

    def test_api_accepts_no_precomputed_v1_hhi_runtime_or_execution_inputs(self) -> None:
        parameters = set(
            inspect.signature(
                subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v2
            ).parameters
        )
        self.assertTrue(
            parameters.isdisjoint(
                {
                    "v1_result",
                    "hhi",
                    "weighted_effective_cluster_count",
                    "runtime",
                    "database",
                    "cache",
                    "current",
                    "order",
                    "broker",
                }
            )
        )
        source = inspect.getsource(subject)
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        self.assertNotIn(forbidden, json.dumps(self._evaluate()[0]).upper())


if __name__ == "__main__":
    unittest.main()
