from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_dual_budget_proposal_scope_reconciliation_v8 import (
    DualBudgetProposalScopeContractError,
    PREREGISTRATION_SCHEMA_VERSION,
    RECONCILIATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA_VERSION,
    build_dual_budget_proposal_scope_preregistration_v8,
    evaluate_dual_budget_proposal_scope_reconciliation_v8,
    verify_dual_budget_proposal_scope_preregistration_v8,
    verify_dual_budget_proposal_scope_reconciliation_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v11 as v11_tests
from tests import (
    test_strategy_correlation_cluster_multi_window_cutoff_bound_effective_ticket_budget_consumer_v7
    as v7_tests,
)


class DualBudgetProposalScopeReconciliationV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v11_case = v11_tests.StrategyCorrelationClusterEffectiveBetBudgetV11Tests(
            methodName="runTest"
        )
        self.v11_case.setUp()
        v11_args, v11_kwargs = self.v11_case.call_parts()
        self.v11_document = self.v11_case.evaluate_v11()
        self.v11_context = {
            "args": list(v11_args),
            "kwargs": v11_kwargs,
            "expected_budget_v11_hash": self.v11_document["budget_v11_hash"],
        }

        self.v7_case = v7_tests.CutoffBoundEffectiveTicketBudgetConsumerV7Tests(
            methodName="runTest"
        )
        self.v7_case.setUp()
        self.aligned_proposal = {
            "symbol": "B",
            "notional_minor": 2_500,
            "direction": "LONG",
        }
        self.v7_document, self.v7_context = self.build_v7(
            self.aligned_proposal
        )
        self.preregistration = self.build_preregistration()
        self.expected_preregistration_hash = self.preregistration[
            "proposal_scope_preregistration_v8_hash"
        ]

    def build_v7(
        self,
        proposal,
        *,
        positions=None,
        equity_minor=10_000,
    ):
        clean_positions = (
            self.v7_case.positions if positions is None else positions
        )
        document = self.v7_case.evaluate(
            proposal=proposal,
            positions_before=clean_positions,
            equity_minor=equity_minor,
        )
        context = {
            "budget_preregistration": self.v7_case.preregistration,
            "common_cutoff_gate_v6_document": self.v7_case.cutoff_document,
            "common_cutoff_gate_v6_context": self.v7_case.cutoff_context,
            "positions_before": clean_positions,
            "proposal": proposal,
            "equity_minor": equity_minor,
            "expected_budget_preregistration_v7_hash": (
                self.v7_case.expected_preregistration_hash
            ),
        }
        return document, context

    def build_preregistration(self, **overrides):
        values = {
            "expected_dynamic_budget_preregistration_v7_hash": (
                self.v7_case.expected_preregistration_hash
            ),
            "expected_proposal_symbol": "B",
            "expected_proposal_direction": "LONG",
            "expected_proposal_notional_minor": 2_500,
            "expected_max_cluster_gross_bps": 4_500,
            "legacy_notional_unit_to_minor": 1,
            "require_legacy_risk_increasing": True,
        }
        values.update(copy.deepcopy(overrides))
        return build_dual_budget_proposal_scope_preregistration_v8(**values)

    def evaluate(self, **overrides):
        values = {
            "preregistration": self.preregistration,
            "dynamic_budget_v7_document": self.v7_document,
            "dynamic_budget_v7_context": self.v7_context,
            "legacy_budget_v11_document": self.v11_document,
            "legacy_budget_v11_context": self.v11_context,
            "expected_proposal_scope_preregistration_v8_hash": (
                self.expected_preregistration_hash
            ),
        }
        values.update(overrides)
        return evaluate_dual_budget_proposal_scope_reconciliation_v8(**values)

    def test_aligned_dual_pass_reconciles_proposal_only(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["reconciliation_status"], "PASS")
        self.assertEqual(document["combined_budget_status"], "NOT_ESTABLISHED")
        self.assertEqual(document["combined_admission_status"], "BLOCKED")
        self.assertTrue(document["facts"]["proposal_scope_reconciled"])
        self.assertFalse(document["facts"]["portfolio_snapshot_reconciled"])
        self.assertFalse(document["facts"]["combined_budget_established"])
        self.assertEqual(
            document["proposal_scope"]["converted_legacy_notional_minor"],
            2_500,
        )

    def test_gap_proof_two_local_passes_with_notional_mismatch_block(self):
        default_v7_document, default_v7_context = self.build_v7(
            self.v7_case.proposal
        )
        self.assertEqual(default_v7_document["status"], "PASS")
        self.assertEqual(self.v11_document["status"], "PASS")
        document = self.evaluate(
            dynamic_budget_v7_document=default_v7_document,
            dynamic_budget_v7_context=default_v7_context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "PROPOSAL_NOTIONAL")
        self.assertIn(
            "proposal_notional_unit_conversion_exact",
            document["blockers"],
        )

    def test_symbol_mismatch_blocks_even_when_both_local_budgets_pass(self):
        proposal = {
            "symbol": "C",
            "notional_minor": 2_500,
            "direction": "LONG",
        }
        dynamic_document, dynamic_context = self.build_v7(proposal)
        preregistration = self.build_preregistration(
            expected_proposal_symbol="C"
        )
        self.assertEqual(dynamic_document["status"], "PASS")
        document = self.evaluate(
            preregistration=preregistration,
            dynamic_budget_v7_document=dynamic_document,
            dynamic_budget_v7_context=dynamic_context,
            expected_proposal_scope_preregistration_v8_hash=preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "PROPOSAL_SYMBOL")

    def test_direction_mismatch_blocks(self):
        proposal = {
            "symbol": "B",
            "notional_minor": 2_500,
            "direction": "SHORT",
        }
        dynamic_document, dynamic_context = self.build_v7(proposal)
        preregistration = self.build_preregistration(
            expected_proposal_direction="SHORT"
        )
        document = self.evaluate(
            preregistration=preregistration,
            dynamic_budget_v7_document=dynamic_document,
            dynamic_budget_v7_context=dynamic_context,
            expected_proposal_scope_preregistration_v8_hash=preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "PROPOSAL_DIRECTION")

    def test_explicit_integer_unit_conversion_can_reconcile(self):
        proposal = {
            "symbol": "B",
            "notional_minor": 250_000,
            "direction": "LONG",
        }
        dynamic_document, dynamic_context = self.build_v7(
            proposal,
            positions=[],
            equity_minor=1_000_000,
        )
        preregistration = self.build_preregistration(
            expected_proposal_notional_minor=250_000,
            legacy_notional_unit_to_minor=100,
        )
        document = self.evaluate(
            preregistration=preregistration,
            dynamic_budget_v7_document=dynamic_document,
            dynamic_budget_v7_context=dynamic_context,
            expected_proposal_scope_preregistration_v8_hash=preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        self.assertEqual(dynamic_document["status"], "PASS")
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["proposal_scope"]["converted_legacy_notional_minor"],
            250_000,
        )

    def test_cluster_gross_policy_mismatch_blocks(self):
        preregistration = self.build_preregistration(
            expected_max_cluster_gross_bps=4_000
        )
        document = self.evaluate(
            preregistration=preregistration,
            expected_proposal_scope_preregistration_v8_hash=preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["first_blocking_tier"],
            "CLUSTER_GROSS_POLICY",
        )

    def test_exact_unknown_dynamic_predecessor_blocks_reconciliation(self):
        shifted_v5, shifted_adapter_context = (
            self.v7_case.v6_case._coherently_shifted_v5_chain(
                10 * 365 * 24 * 60 * 60 * 1000
            )
        )
        shifted_cutoff = self.v7_case.v6_case.evaluate(
            adapter_v5_document=shifted_v5,
            adapter_v5_context=shifted_adapter_context,
        )
        shifted_cutoff_context = copy.deepcopy(self.v7_case.cutoff_context)
        shifted_cutoff_context["adapter_v5_document"] = shifted_v5
        shifted_cutoff_context["adapter_v5_context"] = shifted_adapter_context
        dynamic_document = self.v7_case.evaluate(
            proposal=self.aligned_proposal,
            common_cutoff_gate_v6_document=shifted_cutoff,
            common_cutoff_gate_v6_context=shifted_cutoff_context,
        )
        dynamic_context = copy.deepcopy(self.v7_context)
        dynamic_context["common_cutoff_gate_v6_document"] = shifted_cutoff
        dynamic_context["common_cutoff_gate_v6_context"] = shifted_cutoff_context
        self.assertEqual(dynamic_document["status"], "UNKNOWN")
        document = self.evaluate(
            dynamic_budget_v7_document=dynamic_document,
            dynamic_budget_v7_context=dynamic_context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["first_blocking_tier"],
            "PREDECESSOR_DECISION",
        )

    def test_legacy_output_or_context_tamper_is_unknown(self):
        legacy = copy.deepcopy(self.v11_document)
        legacy["authority"]["current_admission_allowed"] = True
        document = self.evaluate(legacy_budget_v11_document=legacy)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(document["first_blocking_tier"], "SOURCE")

        context = copy.deepcopy(self.v11_context)
        context["kwargs"]["proposed_notional"] = 2_501
        document = self.evaluate(legacy_budget_v11_context=context)
        self.assertEqual(document["status"], "UNKNOWN")

    def test_preregistration_rejects_boolean_scale_and_invalid_scope(self):
        invalid = [
            {"legacy_notional_unit_to_minor": True},
            {"expected_proposal_notional_minor": False},
            {"expected_max_cluster_gross_bps": 10_001},
            {"expected_proposal_symbol": "b"},
            {"expected_proposal_direction": "BUY"},
            {"require_legacy_risk_increasing": 1},
            {"expected_dynamic_budget_preregistration_v7_hash": "f" * 63},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(
                DualBudgetProposalScopeContractError
            ):
                self.build_preregistration(**overrides)

    def test_preregistration_verifier_rejects_resealed_authority(self):
        verification = verify_dual_budget_proposal_scope_preregistration_v8(
            self.preregistration,
            expected_proposal_scope_preregistration_v8_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        promoted = copy.deepcopy(self.preregistration)
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "proposal_scope_preregistration_v8_hash",
        )
        verification = verify_dual_budget_proposal_scope_preregistration_v8(
            promoted,
            expected_proposal_scope_preregistration_v8_hash=promoted[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_exact_verifier_rejects_resealed_scope_and_authority_tamper(self):
        document = self.evaluate()
        verification = verify_dual_budget_proposal_scope_reconciliation_v8(
            document,
            self.preregistration,
            self.v7_document,
            self.v7_context,
            self.v11_document,
            self.v11_context,
            expected_proposal_scope_preregistration_v8_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        variants = []
        scope = copy.deepcopy(document)
        scope["proposal_scope"]["converted_legacy_notional_minor"] += 1
        variants.append(scope)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for variant in variants:
            with self.subTest(variant=variant):
                resealed = seal_strict_canonical_document(
                    variant,
                    "proposal_scope_reconciliation_v8_hash",
                )
                verification = verify_dual_budget_proposal_scope_reconciliation_v8(
                    resealed,
                    self.preregistration,
                    self.v7_document,
                    self.v7_context,
                    self.v11_document,
                    self.v11_context,
                    expected_proposal_scope_preregistration_v8_hash=(
                        self.expected_preregistration_hash
                    ),
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(
                    verification["reconciliation_status"],
                    "UNKNOWN",
                )
                self.assertEqual(
                    verification["combined_admission_status"],
                    "BLOCKED",
                )

    def test_output_is_bounded_deterministic_and_inputs_unmutated(self):
        before = copy.deepcopy(
            (
                self.preregistration,
                self.v7_document,
                self.v7_context,
                self.v11_document,
                self.v11_context,
            )
        )
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertEqual(
            before,
            (
                self.preregistration,
                self.v7_document,
                self.v7_context,
                self.v11_document,
                self.v11_context,
            ),
        )
        encoded = json.dumps(first, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            '"args":',
            '"kwargs":',
            '"positions_before":',
            '"signature_base64":',
            '"public_key_spki_base64":',
            '"market_data_payloads":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(first["facts"]["raw_predecessor_context_embedded"])

    def test_schema_claims_and_authority_remain_locked(self):
        document = self.evaluate()
        verification = verify_dual_budget_proposal_scope_reconciliation_v8(
            document,
            self.preregistration,
            self.v7_document,
            self.v7_context,
            self.v11_document,
            self.v11_context,
            expected_proposal_scope_preregistration_v8_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(
            self.preregistration["schema_version"],
            PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["schema_version"], RECONCILIATION_SCHEMA_VERSION)
        self.assertEqual(verification["schema_version"], VERIFICATION_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertFalse(document["facts"]["portfolio_snapshot_reconciled"])
        self.assertFalse(document["facts"]["positions_reconciled"])
        self.assertFalse(document["facts"]["equity_reconciled"])
        self.assertFalse(document["facts"]["combined_admission_allowed"])
        self.assertFalse(document["facts"]["profitability_proven"])
        for key, value in document["authority"].items():
            if key in {"descriptive_only", "consumer_only"}:
                self.assertTrue(value)
            else:
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
