from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v2 as weighted_v2,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v4 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v3 import (
    PortfolioRiskAdapterV3Tests,
)


class PortfolioRiskAdapterV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.v3_case = PortfolioRiskAdapterV3Tests(
            methodName="test_fresh_risk_increase_passes_local_only"
        )
        self.v3_case.setUp()
        self.base = self._build_case()

    @staticmethod
    def _weighted_context(adapter_v1_context: dict) -> dict:
        return {
            "preregistration": adapter_v1_context["preregistration"],
            "correlation_matrix": adapter_v1_context[
                "cluster_correlation_matrix"
            ],
            "complete_link_audit": adapter_v1_context["complete_link_audit"],
            "equity": adapter_v1_context["equity"],
            "positions": adapter_v1_context["positions"],
            "proposed_symbol": adapter_v1_context["proposed_symbol"],
            "proposed_notional": adapter_v1_context["proposed_notional"],
            "proposed_direction": adapter_v1_context["proposed_direction"],
            "max_cluster_gross_pct": adapter_v1_context[
                "max_cluster_gross_pct"
            ],
            "risk_increasing": adapter_v1_context["risk_increasing"],
        }

    def _build_case(self, **overrides: object) -> dict:
        adapter_v2, adapter_v2_context = self.v3_case._rebuild_adapter(**overrides)
        lineage_context = self.v3_case._lineage_context(
            adapter_v2_document=adapter_v2,
            adapter_v2_context=adapter_v2_context,
        )
        lineage = self.v3_case._build_lineage(lineage_context)
        adapter_v3_document = self.v3_case._evaluate(lineage, lineage_context)
        adapter_v1_context = adapter_v2_context[
            "adapter_v1_verification_context"
        ]
        weighted_context = self._weighted_context(adapter_v1_context)
        weighted_document = weighted_v2.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            weighted_context["preregistration"],
            weighted_context["correlation_matrix"],
            weighted_context["complete_link_audit"],
            equity=weighted_context["equity"],
            positions=weighted_context["positions"],
            proposed_symbol=weighted_context["proposed_symbol"],
            proposed_notional=weighted_context["proposed_notional"],
            proposed_direction=weighted_context["proposed_direction"],
            max_cluster_gross_pct=weighted_context["max_cluster_gross_pct"],
            risk_increasing=weighted_context["risk_increasing"],
        )
        return {
            "adapter_v3_document": adapter_v3_document,
            "weighted_document": weighted_document,
            "adapter_v3_context": {
                "lineage_binding_v2": lineage,
                "lineage_binding_verification_context": lineage_context,
            },
            "weighted_context": weighted_context,
        }

    def _evaluate(self, case: dict | None = None, **overrides: object) -> dict:
        active = self.base if case is None else case
        arguments = {
            "adapter_v3_document": active["adapter_v3_document"],
            "weighted_budget_v2_document": active["weighted_document"],
            "adapter_v3_verification_context": active["adapter_v3_context"],
            "weighted_budget_v2_verification_context": active[
                "weighted_context"
            ],
        }
        arguments.update(overrides)
        with self.v3_case.chain.fixture.source_verifiers():
            return subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4(
                **arguments
            )

    def _verify(self, document: object, case: dict | None = None) -> dict:
        active = self.base if case is None else case
        with self.v3_case.chain.fixture.source_verifiers():
            return subject.verify_strategy_correlation_cluster_portfolio_risk_adapter_v4(
                document,
                active["adapter_v3_document"],
                active["weighted_document"],
                adapter_v3_verification_context=active["adapter_v3_context"],
                weighted_budget_v2_verification_context=active[
                    "weighted_context"
                ],
            )

    def test_base_fresh_case_passes_joint_weighted_candidate(self) -> None:
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_"
            "AND_SESSION_FRESHNESS_LOCAL_ONLY",
        )
        self.assertEqual(document["blockers"], [])

    def test_reproduced_adapter_gap_is_blocked_by_weighted_component(self) -> None:
        case = self._build_case(
            positions=[
                {"symbol": "A", "notional": 2_200, "direction": "LONG"},
                {"symbol": "C", "notional": 200, "direction": "LONG"},
            ],
            proposed_notional=2_200,
            legacy_limits={
                "max_gross_exposure_pct": 100.0,
                "max_correlated_cluster_pct": 45.0,
            },
        )
        self.assertEqual(case["adapter_v3_document"]["status"], "PASS")
        self.assertEqual(case["weighted_document"]["status"], "BLOCK")
        document = self._evaluate(case)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION"
        )
        self.assertEqual(
            document["portfolio"]["weighted_effective_cluster_count"],
            1.090722,
        )

    def test_balanced_above_trigger_case_passes(self) -> None:
        case = self._build_case(
            positions=[
                {"symbol": "A", "notional": 1_250, "direction": "LONG"},
                {"symbol": "C", "notional": 2_500, "direction": "LONG"},
            ],
            proposed_notional=1_250,
            legacy_limits={
                "max_gross_exposure_pct": 100.0,
                "max_correlated_cluster_pct": 45.0,
            },
        )
        document = self._evaluate(case)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["portfolio"]["weighted_effective_cluster_count"], 2.0
        )
        self.assertTrue(
            document["portfolio"]["weighted_diversification_gate_applied"]
        )

    def test_risk_reduction_exemption_is_preserved(self) -> None:
        case = self._build_case(risk_increasing=False)
        document = self._evaluate(case)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED",
        )
        self.assertFalse(document["policy"]["risk_increasing"])

    def test_adapter_v3_block_is_preserved(self) -> None:
        case = self._build_case(proposed_notional=5_000)
        self.assertEqual(case["adapter_v3_document"]["status"], "BLOCK")
        document = self._evaluate(case)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCKED_ADAPTER_V3_COMPONENT")

    def test_weighted_context_position_splice_fails_closed(self) -> None:
        context = copy.deepcopy(self.base["weighted_context"])
        context["positions"] = []
        document = self._evaluate(
            weighted_budget_v2_verification_context=context
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(
            next(
                item
                for item in document["checks"]
                if item["name"] == "weighted_budget_v2_exact_public_verification"
            )["ok"]
        )

    def test_cross_spliced_valid_weighted_document_and_context_fail_lineage(self) -> None:
        other = self._build_case(
            positions=[{"symbol": "C", "notional": 500, "direction": "LONG"}],
            proposed_notional=500,
        )
        document = self._evaluate(
            weighted_budget_v2_document=other["weighted_document"],
            weighted_budget_v2_verification_context=other["weighted_context"],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(
            next(
                item
                for item in document["checks"]
                if item["name"] == "shared_original_input_and_v1_budget_lineage"
            )["ok"]
        )

    def test_context_shapes_are_exact(self) -> None:
        v3_context = copy.deepcopy(self.base["adapter_v3_context"])
        v3_context["compatibility_alias"] = None
        weighted_context = copy.deepcopy(self.base["weighted_context"])
        weighted_context["compatibility_alias"] = None
        for overrides in (
            {"adapter_v3_verification_context": v3_context},
            {"weighted_budget_v2_verification_context": weighted_context},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(self._evaluate(**overrides)["status"], "BLOCK")

    def test_forged_component_receipts_cannot_promote_malformed_documents(self) -> None:
        malformed_v3 = copy.deepcopy(self.base["adapter_v3_document"])
        malformed_v3["policy"]["risk_increasing"] = 1
        malformed_weighted = copy.deepcopy(self.base["weighted_document"])
        malformed_weighted["facts"]["risk_increasing"] = 1
        v3_receipt = {
            "status": "PASS",
            "adapter_v3_exactly_verified": True,
            "adapter_v3_status": "PASS",
            "adapter_v3_hash": malformed_v3["adapter_hash"],
            "blockers": [],
            "current_admission_allowed": False,
            "formal_registry_activation_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "writer_allowed": False,
        }
        weighted_receipt = {
            "status": "PASS",
            "blockers": [],
            "budget_decision": malformed_weighted["decision"],
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with mock.patch.object(subject, "_VERIFY_ADAPTER_V3", return_value=v3_receipt), mock.patch.object(
            subject, "_VERIFY_WEIGHTED_V2", return_value=weighted_receipt
        ):
            document = subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4(
                malformed_v3,
                malformed_weighted,
                adapter_v3_verification_context=self.base["adapter_v3_context"],
                weighted_budget_v2_verification_context=self.base[
                    "weighted_context"
                ],
            )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIsNone(document["policy"]["risk_increasing"])

    def test_exact_verifier_rejects_resealed_decision_metric_and_authority(self) -> None:
        document = self._evaluate()
        self.assertEqual(self._verify(document)["status"], "PASS")
        variants = []
        decision = copy.deepcopy(document)
        decision["decision"] = "R" + "EADY"
        variants.append(decision)
        metric = copy.deepcopy(document)
        metric["portfolio"]["weighted_effective_cluster_count"] = 99.0
        variants.append(metric)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for value in variants:
            with self.subTest(value=value):
                resealed = seal_strict_canonical_document(value, "adapter_hash")
                receipt = self._verify(resealed)
                self.assertEqual(receipt["status"], "BLOCK")
                self.assertEqual(receipt["adapter_v4_status"], "UNKNOWN")

    def test_evaluation_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        snapshot = copy.deepcopy(self.base)
        self.assertEqual(self._evaluate(), self._evaluate())
        self.assertEqual(self.base, snapshot)

    def test_output_is_summary_only(self) -> None:
        document = self._evaluate()
        encoded = json.dumps(document, sort_keys=True)
        for forbidden in (
            '"positions"',
            '"cluster_exposures"',
            '"correlation_matrix"',
            '"adapter_v3_document"',
            '"weighted_budget_v2_document"',
            '"lineage_binding_v2"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(document["facts"]["component_documents_embedded"])

    def test_authority_profitability_and_runtime_remain_locked(self) -> None:
        document = self._evaluate()
        for key, value in document["authority"].items():
            if key in {"research_only", "local_decision_only"}:
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["facts"]["risk_service_invoked"])

    def test_component_implementation_pins_match_current_files(self) -> None:
        paths = {
            "adapter_v3": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v3.py",
            "weighted_v2": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_effective_bet_budget_v2.py",
        }
        self.assertEqual(
            hashlib.sha256(paths["adapter_v3"].read_bytes()).hexdigest(),
            subject.ADAPTER_V3_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(paths["weighted_v2"].read_bytes()).hexdigest(),
            subject.WEIGHTED_V2_IMPLEMENTATION_SHA256,
        )

    def test_api_has_no_runtime_execution_or_precomputed_metric_inputs(self) -> None:
        parameters = set(
            inspect.signature(
                subject.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4
            ).parameters
        )
        self.assertTrue(
            parameters.isdisjoint(
                {
                    "runtime",
                    "database",
                    "cache",
                    "current",
                    "order",
                    "broker",
                    "hhi",
                    "weighted_effective_cluster_count",
                }
            )
        )
        source = inspect.getsource(subject)
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        self.assertNotIn(forbidden, json.dumps(self._evaluate()).upper())


if __name__ == "__main__":
    unittest.main()
