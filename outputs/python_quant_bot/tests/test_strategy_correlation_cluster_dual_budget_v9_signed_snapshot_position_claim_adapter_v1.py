from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_cluster_dual_budget_v9_signed_snapshot_position_claim_adapter_v1
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as v9_contract,
)
from tests import (
    test_strategy_correlation_cluster_dual_budget_portfolio_snapshot_reconciliation_v9
    as v9_support,
)


_EXACT_RECEIPT = {
    "schema_version": (
        "strategy-correlation-cluster-dual-budget-portfolio-snapshot-"
        "reconciliation-v9-verification-v1"
    ),
    "status": "PASS",
    "blockers": [],
    "portfolio_scope_status": "PASS",
    "combined_budget_status": "LOCAL_RESEARCH_SCOPE_RECONCILED",
    "combined_admission_status": "BLOCKED",
    "reconciliation_exactly_verified": True,
    "current_admission_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


class V9SignedSnapshotPositionClaimAdapterV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        case = v9_support.DualBudgetPortfolioSnapshotReconciliationV9Tests(
            "test_fully_aligned_portfolio_scope_passes_without_admission"
        )
        case.setUp()
        real = v9_contract.evaluate_dual_budget_portfolio_snapshot_reconciliation_v9
        with patch.object(
            v9_support,
            "evaluate_dual_budget_portfolio_snapshot_reconciliation_v9",
            wraps=real,
        ) as spy:
            case.test_fully_aligned_portfolio_scope_passes_without_admission()
        call = spy.call_args_list[0]
        parameters = deepcopy(dict(call.kwargs))
        cls.v9_document = real(**deepcopy(parameters))
        cls.v9_context = {
            "preregistration": parameters["preregistration"],
            "proposal_reconciliation_v8_document": parameters[
                "proposal_reconciliation_v8_document"
            ],
            "proposal_reconciliation_v8_context": parameters[
                "proposal_reconciliation_v8_context"
            ],
            "expected_portfolio_snapshot_preregistration_v9_hash": parameters[
                "expected_portfolio_snapshot_preregistration_v9_hash"
            ],
        }
        cls.v9_hash = cls.v9_document[
            "portfolio_snapshot_reconciliation_v9_hash"
        ]
        cls.projection_hash = "f" * 64

    def _build(
        self,
        *,
        document=None,
        context=None,
        expected_v9_hash=None,
        projection_hash=None,
        verifier_receipt=None,
    ):
        document = deepcopy(
            self.v9_document if document is None else document
        )
        context = deepcopy(self.v9_context if context is None else context)
        kwargs = {
            "expected_v9_reconciliation_hash": (
                self.v9_hash if expected_v9_hash is None else expected_v9_hash
            ),
            "expected_projection_preregistration_hash": (
                self.projection_hash
                if projection_hash is None
                else projection_hash
            ),
        }
        if verifier_receipt is None:
            return subject.build_v9_signed_snapshot_position_claim_adapter_v1(
                document,
                context,
                **kwargs,
            )
        with patch.object(
            subject.v9_contract,
            "verify_dual_budget_portfolio_snapshot_reconciliation_v9",
            return_value=verifier_receipt,
        ):
            return subject.build_v9_signed_snapshot_position_claim_adapter_v1(
                document,
                context,
                **kwargs,
            )

    def test_exact_aligned_v9_builds_canonical_gross_position_claim(self):
        result = self._build()
        self.assertIsNotNone(result)
        self.assertEqual(result.position_count, 1)
        self.assertEqual(result.total_gross_bps, 2500)
        self.assertEqual(result.position_claim.positions[0].symbol, "A")
        self.assertEqual(result.position_claim.positions[0].gross_bps, 2500)
        self.assertEqual(
            result.source_v9_reconciliation_hash,
            self.v9_hash,
        )
        self.assertTrue(result.v9_reconciliation_exactly_verified)
        self.assertTrue(result.local_signed_snapshot_claim_bound)

    def test_raw_v9_pass_has_no_canonical_consumer_claim(self):
        self.assertEqual(self.v9_document["status"], "PASS")
        self.assertNotIn("position_claim", self.v9_document)
        self.assertNotIn("gross_bps", json.dumps(self.v9_document))
        self.assertIsNotNone(self._build().position_claim)

    def test_v9_hash_status_and_exact_verifier_are_required(self):
        self.assertIsNone(self._build(expected_v9_hash="0" * 64))
        blocked = deepcopy(self.v9_document)
        blocked["status"] = "BLOCK"
        self.assertIsNone(
            self._build(document=blocked, verifier_receipt=_EXACT_RECEIPT)
        )
        rejected = {**_EXACT_RECEIPT, "reconciliation_exactly_verified": False}
        self.assertIsNone(self._build(verifier_receipt=rejected))

    def test_real_v9_verifier_rejects_signed_position_tamper(self):
        context = deepcopy(self.v9_context)
        claim = context["proposal_reconciliation_v8_context"][
            "legacy_budget_v11_context"
        ]["kwargs"]["snapshot_evaluation_kwargs"]["claim_build_kwargs"]
        claim["positions"][0]["notional"] = 2600
        self.assertIsNone(self._build(context=context))

    def test_snapshot_metadata_must_match_v9_preregistration(self):
        context = deepcopy(self.v9_context)
        prereg = context["preregistration"]
        prereg["expected_snapshot"]["snapshot_sequence"] += 1
        self.assertIsNone(
            self._build(context=context, verifier_receipt=_EXACT_RECEIPT)
        )

    def test_ceiling_conversion_preserves_long_and_short_gross(self):
        context = deepcopy(self.v9_context)
        prereg = context["preregistration"]
        prereg["expected_snapshot"]["equity_minor"] = 3000
        claim = context["proposal_reconciliation_v8_context"][
            "legacy_budget_v11_context"
        ]["kwargs"]["snapshot_evaluation_kwargs"]["claim_build_kwargs"]
        claim["equity"] = 3000
        claim["positions"] = [
            {"symbol": "A", "notional": 1000, "direction": "LONG"},
            {"symbol": "B", "notional": 1000, "direction": "SHORT"},
        ]
        result = self._build(
            context=context,
            verifier_receipt=_EXACT_RECEIPT,
        )
        self.assertEqual(
            [(item.symbol, item.gross_bps) for item in result.position_claim.positions],
            [("A", 3334), ("B", 3334)],
        )
        self.assertEqual(result.total_gross_bps, 6668)
        self.assertFalse(result.direction_netting_applied)

    def test_duplicate_noncanonical_and_boolean_positions_fail_closed(self):
        base = deepcopy(self.v9_context)
        claim = base["proposal_reconciliation_v8_context"][
            "legacy_budget_v11_context"
        ]["kwargs"]["snapshot_evaluation_kwargs"]["claim_build_kwargs"]
        claim["positions"] = [
            {"symbol": "A", "notional": 100, "direction": "LONG"},
            {"symbol": "A", "notional": 200, "direction": "SHORT"},
        ]
        self.assertIsNone(
            self._build(context=base, verifier_receipt=_EXACT_RECEIPT)
        )
        base = deepcopy(self.v9_context)
        claim = base["proposal_reconciliation_v8_context"][
            "legacy_budget_v11_context"
        ]["kwargs"]["snapshot_evaluation_kwargs"]["claim_build_kwargs"]
        claim["positions"][0]["notional"] = True
        self.assertIsNone(
            self._build(context=base, verifier_receipt=_EXACT_RECEIPT)
        )

    def test_projection_hash_is_strict_and_bound_into_claim(self):
        self.assertIsNone(self._build(projection_hash="invalid"))
        result = self._build()
        self.assertEqual(
            result.position_claim.projection_preregistration_hash,
            self.projection_hash,
        )

    def test_output_is_bounded_and_excludes_provider_and_signature_material(self):
        result = self._build()
        rendered = repr(result)
        source_claim = self.v9_context["proposal_reconciliation_v8_context"][
            "legacy_budget_v11_context"
        ]["kwargs"]["snapshot_evaluation_kwargs"]["claim_build_kwargs"]
        provider = source_claim["provider_preregistration_kwargs"]
        self.assertNotIn(provider["provider_id"], rendered)
        self.assertNotIn(provider["key_id"], rendered)
        self.assertLess(len(rendered), 5000)
        self.assertFalse(result.raw_provider_registration_embedded)
        self.assertFalse(result.raw_signatures_embedded)

    def test_external_truth_freshness_profitability_and_authority_stay_closed(self):
        result = self._build()
        self.assertFalse(result.provider_identity_verified)
        self.assertFalse(result.source_truth_verified)
        self.assertFalse(result.freshness_verified)
        self.assertFalse(result.runtime_consumer_bound)
        self.assertFalse(result.current_admission_allowed)
        self.assertFalse(result.paper_authorized)
        self.assertFalse(result.live_order_allowed)
        self.assertFalse(result.profitability_proven)
        self.assertFalse(result.permission)
        self.assertEqual(result.permission_state, "UNAUTHORIZED")

    def test_result_is_deterministic_inputs_immutable_and_exactly_verified(self):
        document = deepcopy(self.v9_document)
        context = deepcopy(self.v9_context)
        before_document = deepcopy(document)
        before_context = deepcopy(context)
        one = self._build(document=document, context=context)
        two = self._build(document=document, context=context)
        self.assertEqual(one, two)
        self.assertEqual(document, before_document)
        self.assertEqual(context, before_context)
        self.assertTrue(
            subject.verify_v9_signed_snapshot_position_claim_adapter_v1(
                one,
                document,
                context,
                expected_v9_reconciliation_hash=self.v9_hash,
                expected_projection_preregistration_hash=self.projection_hash,
            )
        )
        promoted = replace(one, paper_authorized=True)
        self.assertFalse(
            subject.verify_v9_signed_snapshot_position_claim_adapter_v1(
                promoted,
                document,
                context,
                expected_v9_reconciliation_hash=self.v9_hash,
                expected_projection_preregistration_hash=self.projection_hash,
            )
        )


if __name__ == "__main__":
    unittest.main()
