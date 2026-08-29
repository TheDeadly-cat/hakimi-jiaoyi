from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_multi_window_cutoff_bound_effective_ticket_budget_consumer_v7 import (
    CLUSTER_MERGE_RULE,
    COMPONENT_DERIVATION_SCHEMA_VERSION,
    CONSUMER_SCHEMA_VERSION,
    CONSUMER_VERIFICATION_SCHEMA_VERSION,
    CutoffBoundEffectiveTicketBudgetContractError,
    PREREGISTRATION_SCHEMA_VERSION,
    REQUIRED_WINDOW_IDS,
    STATIC_FINGERPRINT,
    build_cutoff_bound_effective_ticket_budget_preregistration_v7,
    derive_conservative_multi_window_components_v1,
    evaluate_cutoff_bound_effective_ticket_budget_consumer_v7,
    verify_cutoff_bound_effective_ticket_budget_consumer_v7,
    verify_cutoff_bound_effective_ticket_budget_preregistration_v7,
)
from exchange_terminal.services.strategy_correlation_cluster_multi_window_market_data_common_cutoff_gate_v6 import (
    evaluate_market_data_common_cutoff_gate_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_multi_window_market_data_common_cutoff_gate_v6
    as v6_tests,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class CutoffBoundEffectiveTicketBudgetConsumerV7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v6_case = v6_tests.MultiWindowMarketDataCommonCutoffGateV6Tests(
            methodName="runTest"
        )
        self.v6_case.setUp()
        self.cutoff_document = self.v6_case.evaluate()
        self.cutoff_context = {
            "common_cutoff_preregistration": self.v6_case.preregistration,
            "adapter_v5_document": self.v6_case.adapter_v5_document,
            "adapter_v5_context": self.v6_case.adapter_v5_context,
            "expected_common_cutoff_preregistration_v6_hash": (
                self.v6_case.expected_preregistration_hash
            ),
        }
        self.preregistration = self.build_preregistration()
        self.expected_preregistration_hash = self.preregistration[
            "budget_preregistration_v7_hash"
        ]
        self.positions = [
            {"symbol": "A", "notional_minor": 2_000, "direction": "LONG"}
        ]
        self.proposal = {
            "symbol": "B",
            "notional_minor": 2_000,
            "direction": "LONG",
        }

    def build_preregistration(self, **overrides):
        values = {
            "expected_symbols": ["A", "B", "C"],
            "strategy_id": "trend",
            "variant_id": "envelope-v5",
            "lane": "RAW_EXCESS",
            "expected_common_cutoff_preregistration_v6_hash": (
                self.v6_case.expected_preregistration_hash
            ),
            "max_effective_ticket_count": 2,
            "max_cluster_gross_bps": 4_500,
            "required_window_ids": list(REQUIRED_WINDOW_IDS),
            "cluster_merge_rule": CLUSTER_MERGE_RULE,
        }
        values.update(copy.deepcopy(overrides))
        return build_cutoff_bound_effective_ticket_budget_preregistration_v7(
            **values
        )

    def evaluate(self, **overrides):
        values = {
            "budget_preregistration": self.preregistration,
            "common_cutoff_gate_v6_document": self.cutoff_document,
            "common_cutoff_gate_v6_context": self.cutoff_context,
            "positions_before": self.positions,
            "proposal": self.proposal,
            "equity_minor": 10_000,
            "expected_budget_preregistration_v7_hash": (
                self.expected_preregistration_hash
            ),
        }
        values.update(overrides)
        return evaluate_cutoff_bound_effective_ticket_budget_consumer_v7(
            **values
        )

    def test_correlated_proposal_reuses_ticket_but_accumulates_gross(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["budget_status"], "PASS")
        self.assertEqual(document["admission_status"], "BLOCKED")
        self.assertEqual(
            document["source"]["adapter_v5_hash"],
            self.v6_case.adapter_v5_document["adapter_v5_hash"],
        )
        self.assertEqual(
            document["budget_summary"]["effective_ticket_count_before"],
            1,
        )
        self.assertEqual(
            document["budget_summary"]["effective_ticket_count_after"],
            1,
        )
        self.assertEqual(
            document["budget_summary"]["marginal_effective_ticket_count"],
            0,
        )
        proposal_component = next(
            item for item in document["component_summaries"]
            if item["includes_proposal"]
        )
        self.assertEqual(proposal_component["members"], ["A", "B"])
        self.assertEqual(proposal_component["gross_notional_minor_after"], 4_000)
        self.assertEqual(proposal_component["gross_bps_after"], 4_000)

    def test_correlated_cluster_gross_limit_blocks_without_new_ticket(self):
        positions = [
            {"symbol": "A", "notional_minor": 3_000, "direction": "LONG"}
        ]
        document = self.evaluate(positions_before=positions)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["budget_status"], "BLOCK")
        self.assertEqual(
            document["budget_summary"]["marginal_effective_ticket_count"],
            0,
        )
        self.assertIn("cluster_gross_limit", document["blockers"])
        self.assertEqual(document["first_blocking_tier"], "CLUSTER_GROSS_LIMIT")

    def test_isolated_component_consumes_second_effective_ticket(self):
        positions = [
            {"symbol": "C", "notional_minor": 1_000, "direction": "LONG"}
        ]
        document = self.evaluate(positions_before=positions)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["budget_summary"]["effective_ticket_count_after"],
            2,
        )
        self.assertEqual(
            document["budget_summary"]["marginal_effective_ticket_count"],
            1,
        )

    def test_effective_ticket_limit_blocks_second_component(self):
        preregistration = self.build_preregistration(
            max_effective_ticket_count=1,
            max_cluster_gross_bps=10_000,
        )
        positions = [
            {"symbol": "C", "notional_minor": 1_000, "direction": "LONG"}
        ]
        document = self.evaluate(
            budget_preregistration=preregistration,
            expected_budget_preregistration_v7_hash=preregistration[
                "budget_preregistration_v7_hash"
            ],
            positions_before=positions,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("effective_ticket_limit", document["blockers"])
        self.assertEqual(
            document["first_blocking_tier"],
            "EFFECTIVE_TICKET_LIMIT",
        )

    def test_unknown_cutoff_chain_prevents_budget_evaluation(self):
        shifted_v5, shifted_adapter_context = (
            self.v6_case._coherently_shifted_v5_chain(
                10 * 365 * 24 * 60 * 60 * 1000
            )
        )
        shifted_cutoff = evaluate_market_data_common_cutoff_gate_v6(
            self.v6_case.preregistration,
            shifted_v5,
            shifted_adapter_context,
            expected_common_cutoff_preregistration_v6_hash=(
                self.v6_case.expected_preregistration_hash
            ),
        )
        shifted_context = copy.deepcopy(self.cutoff_context)
        shifted_context["adapter_v5_document"] = shifted_v5
        shifted_context["adapter_v5_context"] = shifted_adapter_context
        document = self.evaluate(
            common_cutoff_gate_v6_document=shifted_cutoff,
            common_cutoff_gate_v6_context=shifted_context,
        )
        self.assertEqual(shifted_cutoff["status"], "UNKNOWN")
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(document["budget_status"], "NOT_EVALUATED")
        self.assertIn("common_cutoff_gate_v6_exact_pass", document["blockers"])

    def test_any_window_cocluster_union_is_conservative_and_transitive(self):
        def gate(groups, label):
            clusters = []
            for index, members in enumerate(groups, start=1):
                clusters.append(
                    {
                        "cluster_id": f"cluster-{index}",
                        "effective_vote_count": 1,
                        "member_outcomes": [
                            {"status": "PASS", "symbol": symbol}
                            for symbol in members
                        ],
                        "status": "PASS",
                    }
                )
            return {
                "status": "PASS",
                "decision": (
                    "PASS_DYNAMIC_WINDOW_INDEPENDENT_TICKET_RESEARCH_GATE"
                ),
                "gate_v2_hash": _hash(label),
                "cluster_results": clusters,
                "raw_passing_symbol_ticket_count": 3,
                "effective_independent_ticket_count": len(clusters),
                "discounted_correlated_ticket_count": 3 - len(clusters),
            }

        window_inputs = {
            "short": {"gate": gate([["A", "B"], ["C"]], "short")},
            "anchor": {"gate": gate([["A"], ["B", "C"]], "anchor")},
            "long": {"gate": gate([["A"], ["B"], ["C"]], "long")},
        }
        document = derive_conservative_multi_window_components_v1(
            window_inputs,
            ["A", "B", "C"],
            list(REQUIRED_WINDOW_IDS),
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["effective_independent_ticket_count"], 1)
        self.assertEqual(document["components"][0]["members"], ["A", "B", "C"])

    def test_preregistration_rejects_boolean_limits_and_scope_drift(self):
        invalid = [
            {"max_effective_ticket_count": True},
            {"max_cluster_gross_bps": False},
            {"max_effective_ticket_count": 0},
            {"max_cluster_gross_bps": 10_001},
            {"required_window_ids": ["short", "anchor"]},
            {"cluster_merge_rule": "INTERSECTION"},
            {"expected_symbols": ["B", "A", "C"]},
            {"expected_common_cutoff_preregistration_v6_hash": "f" * 63},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(
                CutoffBoundEffectiveTicketBudgetContractError
            ):
                self.build_preregistration(**overrides)

    def test_boolean_money_and_malformed_portfolio_are_unknown(self):
        variants = [
            {"equity_minor": True},
            {"positions_before": [{"symbol": "A", "notional_minor": True, "direction": "LONG"}]},
            {"proposal": {"symbol": "B", "notional_minor": False, "direction": "LONG"}},
            {"positions_before": [self.positions[0], copy.deepcopy(self.positions[0])]},
            {"proposal": {"symbol": "Z", "notional_minor": 1, "direction": "LONG"}},
        ]
        for overrides in variants:
            with self.subTest(overrides=overrides):
                document = self.evaluate(**overrides)
                self.assertEqual(document["status"], "UNKNOWN")
                self.assertEqual(document["budget_status"], "NOT_EVALUATED")
                self.assertIn("portfolio_proposal_inputs_exact", document["blockers"])

    def test_window_gate_tamper_fails_through_exact_cutoff_source(self):
        context = copy.deepcopy(self.cutoff_context)
        context["adapter_v5_context"]["window_inputs"]["short"]["gate"][
            "effective_independent_ticket_count"
        ] = 3
        document = self.evaluate(common_cutoff_gate_v6_context=context)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("common_cutoff_gate_v6_exact_pass", document["blockers"])

    def test_preregistration_verifier_rejects_resealed_policy_promotion(self):
        verification = (
            verify_cutoff_bound_effective_ticket_budget_preregistration_v7(
                self.preregistration,
                expected_budget_preregistration_v7_hash=(
                    self.expected_preregistration_hash
                ),
            )
        )
        self.assertEqual(verification["status"], "PASS")
        promoted = copy.deepcopy(self.preregistration)
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "budget_preregistration_v7_hash",
        )
        verification = (
            verify_cutoff_bound_effective_ticket_budget_preregistration_v7(
                promoted,
                expected_budget_preregistration_v7_hash=promoted[
                    "budget_preregistration_v7_hash"
                ],
            )
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_consumer_verifier_rejects_resealed_budget_and_authority_tamper(self):
        document = self.evaluate()
        verification = verify_cutoff_bound_effective_ticket_budget_consumer_v7(
            document,
            self.preregistration,
            self.cutoff_document,
            self.cutoff_context,
            self.positions,
            self.proposal,
            equity_minor=10_000,
            expected_budget_preregistration_v7_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        variants = []
        budget = copy.deepcopy(document)
        budget["budget_summary"]["effective_ticket_count_after"] = 2
        variants.append(budget)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for variant in variants:
            with self.subTest(variant=variant):
                resealed = seal_strict_canonical_document(
                    variant,
                    "budget_consumer_v7_hash",
                )
                verification = (
                    verify_cutoff_bound_effective_ticket_budget_consumer_v7(
                        resealed,
                        self.preregistration,
                        self.cutoff_document,
                        self.cutoff_context,
                        self.positions,
                        self.proposal,
                        equity_minor=10_000,
                        expected_budget_preregistration_v7_hash=(
                            self.expected_preregistration_hash
                        ),
                    )
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["consumer_status"], "UNKNOWN")
                self.assertEqual(verification["admission_status"], "BLOCKED")

    def test_output_is_bounded_deterministic_and_inputs_are_unmutated(self):
        before = copy.deepcopy(
            (
                self.preregistration,
                self.cutoff_document,
                self.cutoff_context,
                self.positions,
                self.proposal,
            )
        )
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertEqual(
            before,
            (
                self.preregistration,
                self.cutoff_document,
                self.cutoff_context,
                self.positions,
                self.proposal,
            ),
        )
        encoded = json.dumps(first, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            '"positions_before":',
            '"proposal":',
            '"window_inputs":',
            '"rows":',
            '"market_data_payloads":',
            '"correlation_matrix":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(first["facts"]["portfolio_positions_embedded"])
        self.assertFalse(first["facts"]["raw_market_rows_embedded"])

    def test_schema_claims_and_authority_are_locked(self):
        document = self.evaluate()
        verification = verify_cutoff_bound_effective_ticket_budget_consumer_v7(
            document,
            self.preregistration,
            self.cutoff_document,
            self.cutoff_context,
            self.positions,
            self.proposal,
            equity_minor=10_000,
            expected_budget_preregistration_v7_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(
            self.preregistration["schema_version"],
            PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            document["source"]["component_derivation_v1_hash"] is not None,
            True,
        )
        self.assertEqual(document["schema_version"], CONSUMER_SCHEMA_VERSION)
        self.assertEqual(
            verification["schema_version"],
            CONSUMER_VERIFICATION_SCHEMA_VERSION,
        )
        derivation = derive_conservative_multi_window_components_v1(
            self.v6_case.adapter_v5_context["window_inputs"],
            ["A", "B", "C"],
            list(REQUIRED_WINDOW_IDS),
        )
        self.assertEqual(
            derivation["schema_version"],
            COMPONENT_DERIVATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertFalse(document["facts"]["latest_effective_bet_budget_v11_bound"])
        self.assertFalse(document["facts"]["execution_verified"])
        self.assertFalse(document["facts"]["profitability_proven"])
        for key, value in document["authority"].items():
            if key in {"descriptive_only", "consumer_only"}:
                self.assertTrue(value)
            else:
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
