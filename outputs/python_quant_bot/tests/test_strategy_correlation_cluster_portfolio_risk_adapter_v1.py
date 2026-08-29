from __future__ import annotations

import copy
import inspect
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    ADAPTER_SCHEMA_VERSION,
    ADAPTER_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1,
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_complete_link import (
    StrategyCorrelationClusterCompleteLinkTests,
)


class StrategyCorrelationClusterPortfolioRiskAdapterV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.preregistration = (
            StrategyCorrelationClusterCompleteLinkTests._preregistration()
        )
        self.cluster_matrix = StrategyCorrelationClusterCompleteLinkTests._matrix(
            ac=0.92
        )
        self.complete_link_audit = build_correlation_cluster_complete_link_audit(
            self.preregistration,
            self.cluster_matrix,
        )
        self.base_inputs = {
            "preregistration": self.preregistration,
            "cluster_correlation_matrix": self.cluster_matrix,
            "complete_link_audit": self.complete_link_audit,
            "equity": 10_000,
            "positions": [
                {"symbol": "B", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "D",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "legacy_correlations": {
                "pairs": {"B|D": 0.10, "C|D": 0.10}
            },
        }

    def _evaluate(self, **overrides):
        resolved_inputs = copy.deepcopy(self.base_inputs)
        resolved_inputs.update(copy.deepcopy(overrides))
        inputs = copy.deepcopy(resolved_inputs)
        positional = [
            inputs.pop("preregistration"),
            inputs.pop("cluster_correlation_matrix"),
            inputs.pop("complete_link_audit"),
        ]
        return (
            evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
                *positional,
                **inputs,
            ),
            resolved_inputs,
        )

    @staticmethod
    def _verify(document, inputs):
        rebuilt = copy.deepcopy(inputs)
        positional = [
            rebuilt.pop("preregistration"),
            rebuilt.pop("cluster_correlation_matrix"),
            rebuilt.pop("complete_link_audit"),
        ]
        return verify_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            document,
            *positional,
            **rebuilt,
        )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_joint_pass_reports_effective_independent_bets(self):
        document, _ = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "WITHIN_RESEARCH_RISK_BUDGET")
        self.assertEqual(document["portfolio"]["symbol_ticket_count"], 3)
        self.assertEqual(
            document["portfolio"]["effective_independent_bet_count"], 2
        )
        self.assertEqual(
            document["portfolio"]["correlated_duplicate_ticket_count"], 1
        )
        self.assertEqual(document["portfolio"]["all_cluster_max_gross_exposure_pct"], 36.0)
        self.assertEqual(document["blockers"], [])

    def test_legacy_block_cannot_be_overridden_by_effective_bet_pass(self):
        document, _ = self._evaluate(proposed_notional=3_500)
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(document["facts"]["legacy_gate_passed"])
        self.assertTrue(document["facts"]["effective_bet_gate_passed"])
        self.assertIn("legacy_portfolio_risk_gate", document["blockers"])

    def test_existing_cluster_block_cannot_be_overridden_by_legacy_pass(self):
        positions = [
            {"symbol": "B", "notional": 2_500, "direction": "LONG"},
            {"symbol": "C", "notional": 2_500, "direction": "LONG"},
        ]
        document, _ = self._evaluate(positions=positions)
        self.assertEqual(document["status"], "BLOCK")
        self.assertTrue(document["facts"]["legacy_gate_passed"])
        self.assertFalse(document["facts"]["effective_bet_gate_passed"])
        self.assertEqual(
            document["portfolio"]["legacy_proposal_centered_cluster_pct"], 5.0
        )
        self.assertEqual(
            document["portfolio"]["all_cluster_max_gross_exposure_pct"], 50.0
        )
        self.assertIn("all_cluster_effective_bet_gate", document["blockers"])

    def test_missing_complete_link_source_blocks_even_when_legacy_passes(self):
        document, _ = self._evaluate(
            preregistration=None,
            cluster_correlation_matrix=None,
            complete_link_audit=None,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertTrue(document["facts"]["legacy_gate_passed"])
        self.assertFalse(document["facts"]["effective_bet_gate_passed"])
        self.assertTrue(document["source"]["effective_bet_exactly_verified"])

    def test_limit_drift_blocks_even_when_both_component_gates_pass(self):
        document, _ = self._evaluate(
            legacy_limits={"max_correlated_cluster_pct": 40.0},
            max_cluster_gross_pct=45.0,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertTrue(document["facts"]["legacy_gate_passed"])
        self.assertTrue(document["facts"]["effective_bet_gate_passed"])
        self.assertFalse(document["facts"]["cluster_limit_aligned"])
        self.assertIn("correlated_cluster_limit_alignment", document["blockers"])

    def test_aligned_custom_limit_passes(self):
        document, _ = self._evaluate(
            legacy_limits={"max_correlated_cluster_pct": 40.0},
            max_cluster_gross_pct=40.0,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(document["facts"]["cluster_limit_aligned"])

    def test_strict_aliases_and_invalid_legacy_limits_block(self):
        for overrides in (
            {"risk_increasing": 1},
            {"max_cluster_gross_pct": True},
            {"legacy_limits": {"max_correlated_cluster_pct": True}},
            {"legacy_limits": {"unknown_limit": 1}},
        ):
            with self.subTest(overrides=overrides):
                document, _ = self._evaluate(**overrides)
                self.assertEqual(document["status"], "BLOCK")
                self.assertIn("adapter_input_contract", document["blockers"])

    def test_risk_reduction_passes_without_cluster_sources(self):
        document, _ = self._evaluate(
            preregistration=None,
            cluster_correlation_matrix=None,
            complete_link_audit=None,
            equity=0,
            positions=[],
            proposed_symbol="",
            proposed_notional=0,
            legacy_correlations=None,
            risk_increasing=False,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["facts"]["risk_increasing"], False)
        self.assertTrue(document["facts"]["legacy_gate_passed"])
        self.assertTrue(document["facts"]["effective_bet_gate_passed"])

    def test_inputs_are_not_mutated(self):
        inputs = copy.deepcopy(self.base_inputs)
        expected = copy.deepcopy(inputs)
        positional = [
            inputs["preregistration"],
            inputs["cluster_correlation_matrix"],
            inputs["complete_link_audit"],
        ]
        keyword = {
            key: value
            for key, value in inputs.items()
            if key
            not in {
                "preregistration",
                "cluster_correlation_matrix",
                "complete_link_audit",
            }
        }
        evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            *positional,
            **keyword,
        )
        self.assertEqual(inputs, expected)

    def test_output_does_not_embed_component_or_raw_correlation_documents(self):
        document, _ = self._evaluate()
        keys = self._all_keys(document)
        self.assertNotIn("pair_results", keys)
        self.assertNotIn("pearson_correlation", keys)
        self.assertNotIn("return_series", keys)
        self.assertNotIn("clusters", keys)
        self.assertFalse(document["facts"]["component_results_embedded"])
        self.assertFalse(document["facts"]["source_documents_embedded"])

    def test_exact_verifier_rejects_resealed_status_authority_and_type_changes(self):
        document, inputs = self._evaluate()
        self.assertEqual(self._verify(document, inputs)["status"], "PASS")

        variants = []
        status_tamper = copy.deepcopy(document)
        status_tamper["decision"] = "READY"
        variants.append(status_tamper)
        authority_tamper = copy.deepcopy(document)
        authority_tamper["authority"]["current_admission_allowed"] = True
        variants.append(authority_tamper)
        type_tamper = copy.deepcopy(document)
        type_tamper["portfolio"]["symbol_ticket_count"] = 3.0
        variants.append(type_tamper)

        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(tampered, "adapter_hash")
                verification = self._verify(resealed, inputs)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["adapter_decision"], "UNKNOWN")

    def test_api_does_not_accept_precomputed_component_results(self):
        parameters = inspect.signature(
            evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1
        ).parameters
        self.assertNotIn("legacy_result", parameters)
        self.assertNotIn("budget_result", parameters)
        self.assertFalse(
            self._evaluate()[0]["facts"]["precomputed_component_results_accepted"]
        )

    def test_override_inputs_round_trip_through_exact_verifier(self):
        document, inputs = self._evaluate(proposed_notional=3_500)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(self._verify(document, inputs)["status"], "PASS")

    def test_schema_fingerprint_authority_and_exports_are_research_only(self):
        document, inputs = self._evaluate()
        verification = self._verify(document, inputs)
        self.assertEqual(
            document["schema_version"],
            "strategy-correlation-cluster-portfolio-risk-adapter-v1",
        )
        self.assertEqual(document["schema_version"], ADAPTER_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"], ADAPTER_VERIFICATION_SCHEMA_VERSION
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(document["facts"]["runtime_assets_accessed"])
        self.assertFalse(document["facts"]["runtime_gate_integrated"])
        self.assertTrue(
            document["source"]["dual_correlation_source_formats_required"]
        )


if __name__ == "__main__":
    unittest.main()
