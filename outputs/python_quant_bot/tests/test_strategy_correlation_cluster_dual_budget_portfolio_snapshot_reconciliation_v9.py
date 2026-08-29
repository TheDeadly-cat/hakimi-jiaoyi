from __future__ import annotations

import copy
import inspect
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9 import (
    DualBudgetPortfolioSnapshotContractError,
    POSITION_RECONCILIATION_RULE,
    PREREGISTRATION_SCHEMA_VERSION,
    RECONCILIATION_SCHEMA_VERSION,
    SNAPSHOT_POSITION_SEMANTICS,
    STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA_VERSION,
    build_dual_budget_portfolio_snapshot_preregistration_v9,
    evaluate_dual_budget_portfolio_snapshot_reconciliation_v9,
    verify_dual_budget_portfolio_snapshot_preregistration_v9,
    verify_dual_budget_portfolio_snapshot_reconciliation_v9,
)
from exchange_terminal.services.strategy_correlation_cluster_dual_budget_proposal_scope_reconciliation_v8 import (
    build_dual_budget_proposal_scope_preregistration_v8,
    evaluate_dual_budget_proposal_scope_reconciliation_v8,
)
from exchange_terminal.services.strategy_correlation_cluster_effective_bet_budget_v11 import (
    evaluate_strategy_correlation_cluster_effective_bet_budget_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_dual_budget_proposal_scope_reconciliation_v8
    as v8_tests,
)


class DualBudgetPortfolioSnapshotReconciliationV9Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v8_case = v8_tests.DualBudgetProposalScopeReconciliationV8Tests(
            methodName="runTest"
        )
        self.v8_case.setUp()
        self.default_v8_document = self.v8_case.evaluate()
        self.default_v8_context = self._v8_context(
            self.v8_case.preregistration,
            self.v8_case.v7_document,
            self.v8_case.v7_context,
            self.v8_case.v11_document,
            self.v8_case.v11_context,
        )
        self.preregistration = self.build_preregistration(
            self.default_v8_context
        )
        self.expected_preregistration_hash = self.preregistration[
            "portfolio_snapshot_preregistration_v9_hash"
        ]

    @staticmethod
    def _v8_context(
        preregistration,
        v7_document,
        v7_context,
        v11_document,
        v11_context,
    ):
        return {
            "preregistration": preregistration,
            "dynamic_budget_v7_document": v7_document,
            "dynamic_budget_v7_context": v7_context,
            "legacy_budget_v11_document": v11_document,
            "legacy_budget_v11_context": v11_context,
            "expected_proposal_scope_preregistration_v8_hash": preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        }

    @staticmethod
    def _legacy_bound(v8_context):
        legacy_context = v8_context["legacy_budget_v11_context"]
        return inspect.signature(
            evaluate_strategy_correlation_cluster_effective_bet_budget_v11
        ).bind(
            *legacy_context["args"],
            **legacy_context["kwargs"],
        ).arguments

    def build_preregistration(self, v8_context, **overrides):
        bound = self._legacy_bound(v8_context)
        snapshot = bound["snapshot_claim_document"]["snapshot"]
        v7_document = v8_context["dynamic_budget_v7_document"]
        v7_context = v8_context["dynamic_budget_v7_context"]
        values = {
            "expected_proposal_scope_preregistration_v8_hash": (
                v8_context["expected_proposal_scope_preregistration_v8_hash"]
            ),
            "expected_legacy_snapshot_claim_hash": bound[
                "snapshot_claim_document"
            ]["snapshot_claim_hash"],
            "expected_dynamic_positions_before_hash": v7_document["source"][
                "positions_before_hash"
            ],
            "expected_equity_minor": v7_context["equity_minor"],
            "expected_snapshot_sequence": snapshot["snapshot_sequence"],
            "expected_observed_at_unix_ms": snapshot["observed_at_unix_ms"],
            "legacy_portfolio_unit_to_minor": 1,
            "snapshot_position_semantics": SNAPSHOT_POSITION_SEMANTICS,
            "position_reconciliation_rule": POSITION_RECONCILIATION_RULE,
        }
        values.update(copy.deepcopy(overrides))
        return build_dual_budget_portfolio_snapshot_preregistration_v9(**values)

    def evaluate(self, **overrides):
        values = {
            "preregistration": self.preregistration,
            "proposal_reconciliation_v8_document": self.default_v8_document,
            "proposal_reconciliation_v8_context": self.default_v8_context,
            "expected_portfolio_snapshot_preregistration_v9_hash": (
                self.expected_preregistration_hash
            ),
        }
        values.update(overrides)
        return evaluate_dual_budget_portfolio_snapshot_reconciliation_v9(
            **values
        )

    def build_aligned_source(
        self,
        *,
        scale=1,
        positions=None,
        equity_minor=None,
    ):
        proposal = {
            "symbol": "B",
            "notional_minor": 2_500 * scale,
            "direction": "LONG",
        }
        clean_positions = (
            [
                {
                    "symbol": "A",
                    "notional_minor": 2_500 * scale,
                    "direction": "LONG",
                }
            ]
            if positions is None
            else positions
        )
        clean_equity = 10_000 * scale if equity_minor is None else equity_minor
        v7_preregistration = self.v8_case.v7_case.build_preregistration(
            max_cluster_gross_bps=5_000
        )
        v7_document = self.v8_case.v7_case.evaluate(
            budget_preregistration=v7_preregistration,
            expected_budget_preregistration_v7_hash=v7_preregistration[
                "budget_preregistration_v7_hash"
            ],
            positions_before=clean_positions,
            proposal=proposal,
            equity_minor=clean_equity,
        )
        v7_context = {
            "budget_preregistration": v7_preregistration,
            "common_cutoff_gate_v6_document": self.v8_case.v7_case.cutoff_document,
            "common_cutoff_gate_v6_context": self.v8_case.v7_case.cutoff_context,
            "positions_before": clean_positions,
            "proposal": proposal,
            "equity_minor": clean_equity,
            "expected_budget_preregistration_v7_hash": v7_preregistration[
                "budget_preregistration_v7_hash"
            ],
        }

        v11_document = self.v8_case.v11_case.evaluate_v11(
            max_cluster_gross_pct=50.0
        )
        v11_args, v11_kwargs = self.v8_case.v11_case.call_parts()
        v11_kwargs = copy.deepcopy(v11_kwargs)
        v11_kwargs["max_cluster_gross_pct"] = 50.0
        v11_context = {
            "args": list(v11_args),
            "kwargs": v11_kwargs,
            "expected_budget_v11_hash": v11_document["budget_v11_hash"],
        }

        v8_preregistration = build_dual_budget_proposal_scope_preregistration_v8(
            expected_dynamic_budget_preregistration_v7_hash=v7_preregistration[
                "budget_preregistration_v7_hash"
            ],
            expected_proposal_symbol="B",
            expected_proposal_direction="LONG",
            expected_proposal_notional_minor=2_500 * scale,
            expected_max_cluster_gross_bps=5_000,
            legacy_notional_unit_to_minor=scale,
            require_legacy_risk_increasing=True,
        )
        v8_document = evaluate_dual_budget_proposal_scope_reconciliation_v8(
            v8_preregistration,
            v7_document,
            v7_context,
            v11_document,
            v11_context,
            expected_proposal_scope_preregistration_v8_hash=v8_preregistration[
                "proposal_scope_preregistration_v8_hash"
            ],
        )
        return v8_document, self._v8_context(
            v8_preregistration,
            v7_document,
            v7_context,
            v11_document,
            v11_context,
        )

    def test_gap_proof_v8_pass_can_have_position_notional_mismatch(self):
        self.assertEqual(self.default_v8_document["status"], "PASS")
        document = self.evaluate()
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "POSITIONS")
        self.assertIn("pre_proposal_positions_exact", document["blockers"])
        self.assertFalse(document["facts"]["portfolio_snapshot_reconciled"])

    def test_fully_aligned_portfolio_scope_passes_without_admission(self):
        v8_document, v8_context = self.build_aligned_source()
        preregistration = self.build_preregistration(v8_context)
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(v8_document["status"], "PASS")
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["combined_budget_scope_status"], "PASS")
        self.assertEqual(
            document["combined_budget_status"],
            "LOCAL_RESEARCH_SCOPE_RECONCILED",
        )
        self.assertEqual(document["combined_admission_status"], "BLOCKED")
        self.assertTrue(document["facts"]["positions_reconciled"])
        self.assertTrue(document["facts"]["equity_reconciled"])
        self.assertTrue(document["facts"]["portfolio_snapshot_reconciled"])

    def test_integer_scale_reconciles_positions_equity_and_proposal(self):
        v8_document, v8_context = self.build_aligned_source(scale=100)
        preregistration = self.build_preregistration(
            v8_context,
            legacy_portfolio_unit_to_minor=100,
        )
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["snapshot_scope"]["normalized_legacy_equity_minor"],
            1_000_000,
        )
        self.assertEqual(
            document["snapshot_scope"][
                "normalized_legacy_gross_notional_minor"
            ],
            250_000,
        )

    def test_equity_mismatch_blocks_after_proposal_scope_pass(self):
        v8_document, v8_context = self.build_aligned_source(
            equity_minor=11_000
        )
        preregistration = self.build_preregistration(v8_context)
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(v8_document["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "EQUITY")

    def test_position_symbol_mismatch_blocks(self):
        positions = [
            {"symbol": "C", "notional_minor": 2_500, "direction": "LONG"}
        ]
        v8_document, v8_context = self.build_aligned_source(
            positions=positions
        )
        preregistration = self.build_preregistration(v8_context)
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(v8_document["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "POSITIONS")

    def test_snapshot_sequence_preregistration_mismatch_blocks(self):
        v8_document, v8_context = self.build_aligned_source()
        preregistration = self.build_preregistration(
            v8_context,
            expected_snapshot_sequence=9,
        )
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "SNAPSHOT_SEQUENCE")

    def test_snapshot_context_tamper_is_unknown(self):
        context = copy.deepcopy(self.default_v8_context)
        bound = self._legacy_bound(context)
        snapshot_evidence = bound["snapshot_evidence_document"]
        snapshot_evidence["snapshot_summary"]["equity"] += 1
        document = self.evaluate(
            proposal_reconciliation_v8_context=context
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(document["first_blocking_tier"], "SOURCE")

    def test_exact_blocked_v8_predecessor_blocks_portfolio_scope(self):
        default_v7_document, default_v7_context = self.v8_case.build_v7(
            self.v8_case.v7_case.proposal
        )
        blocked_v8 = self.v8_case.evaluate(
            dynamic_budget_v7_document=default_v7_document,
            dynamic_budget_v7_context=default_v7_context,
        )
        blocked_context = self._v8_context(
            self.v8_case.preregistration,
            default_v7_document,
            default_v7_context,
            self.v8_case.v11_document,
            self.v8_case.v11_context,
        )
        preregistration = self.build_preregistration(blocked_context)
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=blocked_v8,
            proposal_reconciliation_v8_context=blocked_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(blocked_v8["status"], "BLOCK")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["first_blocking_tier"], "PROPOSAL_SCOPE")

    def test_preregistration_rejects_boolean_scale_and_invalid_lineage(self):
        invalid = [
            {"legacy_portfolio_unit_to_minor": True},
            {"expected_equity_minor": False},
            {"expected_snapshot_sequence": -1},
            {"expected_observed_at_unix_ms": 0},
            {"snapshot_position_semantics": "POST_PROPOSAL"},
            {"position_reconciliation_rule": "NETTED"},
            {"expected_legacy_snapshot_claim_hash": "f" * 63},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(
                DualBudgetPortfolioSnapshotContractError
            ):
                self.build_preregistration(
                    self.default_v8_context,
                    **overrides,
                )

    def test_preregistration_verifier_rejects_resealed_authority(self):
        verification = verify_dual_budget_portfolio_snapshot_preregistration_v9(
            self.preregistration,
            expected_portfolio_snapshot_preregistration_v9_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        promoted = copy.deepcopy(self.preregistration)
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "portfolio_snapshot_preregistration_v9_hash",
        )
        verification = verify_dual_budget_portfolio_snapshot_preregistration_v9(
            promoted,
            expected_portfolio_snapshot_preregistration_v9_hash=promoted[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_exact_verifier_rejects_resealed_scope_and_authority_tamper(self):
        document = self.evaluate()
        verification = verify_dual_budget_portfolio_snapshot_reconciliation_v9(
            document,
            self.preregistration,
            self.default_v8_document,
            self.default_v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=(
                self.expected_preregistration_hash
            ),
        )
        self.assertEqual(verification["status"], "PASS")
        variants = []
        scope = copy.deepcopy(document)
        scope["snapshot_scope"]["normalized_legacy_equity_minor"] += 1
        variants.append(scope)
        authority = copy.deepcopy(document)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for variant in variants:
            with self.subTest(variant=variant):
                resealed = seal_strict_canonical_document(
                    variant,
                    "portfolio_snapshot_reconciliation_v9_hash",
                )
                verification = verify_dual_budget_portfolio_snapshot_reconciliation_v9(
                    resealed,
                    self.preregistration,
                    self.default_v8_document,
                    self.default_v8_context,
                    expected_portfolio_snapshot_preregistration_v9_hash=(
                        self.expected_preregistration_hash
                    ),
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["portfolio_scope_status"], "UNKNOWN")
                self.assertEqual(
                    verification["combined_admission_status"],
                    "BLOCKED",
                )

    def test_output_is_bounded_deterministic_and_inputs_unmutated(self):
        before = copy.deepcopy(
            (
                self.preregistration,
                self.default_v8_document,
                self.default_v8_context,
            )
        )
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertEqual(
            before,
            (
                self.preregistration,
                self.default_v8_document,
                self.default_v8_context,
            ),
        )
        encoded = json.dumps(first, ensure_ascii=True, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"positions_before":',
            '"args":',
            '"kwargs":',
            '"signature_base64":',
            '"public_key_spki_base64":',
            '"market_data_payloads":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(first["facts"]["raw_positions_embedded"])
        self.assertFalse(first["facts"]["raw_predecessor_context_embedded"])

    def test_schema_claims_and_external_authority_remain_locked(self):
        v8_document, v8_context = self.build_aligned_source()
        preregistration = self.build_preregistration(v8_context)
        document = self.evaluate(
            preregistration=preregistration,
            proposal_reconciliation_v8_document=v8_document,
            proposal_reconciliation_v8_context=v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        verification = verify_dual_budget_portfolio_snapshot_reconciliation_v9(
            document,
            preregistration,
            v8_document,
            v8_context,
            expected_portfolio_snapshot_preregistration_v9_hash=preregistration[
                "portfolio_snapshot_preregistration_v9_hash"
            ],
        )
        self.assertEqual(
            preregistration["schema_version"],
            PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(document["schema_version"], RECONCILIATION_SCHEMA_VERSION)
        self.assertEqual(verification["schema_version"], VERIFICATION_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertFalse(
            document["facts"]["external_snapshot_provider_identity_verified"]
        )
        self.assertFalse(document["facts"]["snapshot_source_truth_verified"])
        self.assertFalse(document["facts"]["snapshot_freshness_verified"])
        self.assertFalse(document["facts"]["combined_admission_allowed"])
        self.assertFalse(document["facts"]["profitability_proven"])
        for key, value in document["authority"].items():
            if key in {"descriptive_only", "consumer_only"}:
                self.assertTrue(value)
            else:
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
