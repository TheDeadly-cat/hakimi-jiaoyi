from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2 import (
    build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v3 import (
    LINEAGE_CONTEXT_KEYS,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3,
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v3,
)
from tests.synthetic_portfolio_risk_freshness_chain import (
    SyntheticCorrelatedPortfolioRiskFreshnessChain,
)


class PortfolioRiskAdapterV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = SyntheticCorrelatedPortfolioRiskFreshnessChain()

    def _lineage_context(
        self,
        *,
        adapter_v2_document=None,
        adapter_v2_context=None,
        freshness=None,
        freshness_context=None,
    ):
        return {
            "adapter_v2_document": (
                self.chain.adapter_v2_document
                if adapter_v2_document is None
                else adapter_v2_document
            ),
            "freshness_evaluation": (
                self.chain.freshness_evaluation
                if freshness is None
                else freshness
            ),
            "legacy_matrix_binding": self.chain.legacy_binding,
            "adapter_v2_verification_context": (
                self.chain.adapter_v2_context
                if adapter_v2_context is None
                else adapter_v2_context
            ),
            "freshness_verification_context": (
                self.chain.freshness_context
                if freshness_context is None
                else freshness_context
            ),
            "legacy_matrix_binding_verification_context": (
                self.chain.legacy_context
            ),
        }

    def _build_lineage(self, context):
        with self.chain.fixture.source_verifiers():
            return build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
                context["adapter_v2_document"],
                context["freshness_evaluation"],
                context["legacy_matrix_binding"],
                adapter_v2_verification_context=(
                    context["adapter_v2_verification_context"]
                ),
                freshness_verification_context=(
                    context["freshness_verification_context"]
                ),
                legacy_matrix_binding_verification_context=(
                    context["legacy_matrix_binding_verification_context"]
                ),
            )

    def _evaluate(self, lineage, context):
        with self.chain.fixture.source_verifiers():
            return evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3(
                lineage,
                lineage_binding_verification_context=context,
            )

    def _rebuild_adapter(self, **overrides):
        adapter_v1_context = copy.deepcopy(self.chain.adapter_v1_context)
        adapter_v1_context.update(overrides)
        with self.chain.fixture.source_verifiers():
            adapter_v1 = (
                evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
                    **adapter_v1_context
                )
            )
            adapter_v2_context = {
                "adapter_v1_document": adapter_v1,
                "temporal_stability_gate": self.chain.temporal_stability_gate,
                "adapter_v1_verification_context": adapter_v1_context,
                "temporal_stability_verification_context": (
                    self.chain.temporal_context
                ),
            }
            adapter_v2 = (
                evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
                    adapter_v1,
                    self.chain.temporal_stability_gate,
                    adapter_v1_verification_context=adapter_v1_context,
                    temporal_stability_verification_context=(
                        self.chain.temporal_context
                    ),
                )
            )
        return adapter_v2, adapter_v2_context

    def test_fresh_risk_increase_passes_local_only(self):
        context = self._lineage_context()
        document = self._evaluate(self._build_lineage(context), context)
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_"
            "SESSION_FRESHNESS_LOCAL_ONLY",
        )
        self.assertEqual(document["blockers"], [])
        self.assertTrue(document["source"]["lineage_binding_exactly_verified"])

    def test_stale_risk_increase_is_blocked(self):
        freshness, freshness_context = self.chain.build_freshness(
            "2026-12-29T00:00:00Z"
        )
        context = self._lineage_context(
            freshness=freshness,
            freshness_context=freshness_context,
        )
        lineage = self._build_lineage(context)
        self.assertEqual(lineage["status"], "PASS")
        document = self._evaluate(lineage, context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["decision"], "BLOCKED_SESSION_FRESHNESS")
        self.assertEqual(document["blockers"], ["SESSION_FRESHNESS_BLOCKED"])

    def test_base_budget_block_is_preserved(self):
        adapter_v2, adapter_v2_context = self._rebuild_adapter(
            proposed_notional=5000
        )
        context = self._lineage_context(
            adapter_v2_document=adapter_v2,
            adapter_v2_context=adapter_v2_context,
        )
        document = self._evaluate(self._build_lineage(context), context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET"
        )
        self.assertEqual(document["blockers"], ["BASE_ADAPTER_V2_BLOCKED"])

    def test_stale_risk_reduction_passes_with_warning(self):
        adapter_v2, adapter_v2_context = self._rebuild_adapter(
            risk_increasing=False
        )
        freshness, freshness_context = self.chain.build_freshness(
            "2026-12-29T00:00:00Z"
        )
        context = self._lineage_context(
            adapter_v2_document=adapter_v2,
            adapter_v2_context=adapter_v2_context,
            freshness=freshness,
            freshness_context=freshness_context,
        )
        document = self._evaluate(self._build_lineage(context), context)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED",
        )
        self.assertEqual(
            document["warnings"],
            ["SESSION_FRESHNESS_BLOCK_OBSERVED_RISK_REDUCTION_ONLY"],
        )

    def test_tampered_lineage_fails_closed(self):
        context = self._lineage_context()
        lineage = self._build_lineage(context)
        lineage["lineage_binding_hash"] = "0" * 64
        document = self._evaluate(lineage, context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCKED_ADAPTER_FRESHNESS_LINEAGE"
        )
        self.assertEqual(document["component_states"]["adapter_v2_status"], "UNKNOWN")

    def test_cross_spliced_freshness_context_fails_closed(self):
        fresh_context = self._lineage_context()
        fresh_lineage = self._build_lineage(fresh_context)
        stale, stale_context = self.chain.build_freshness(
            "2026-12-29T00:00:00Z"
        )
        spliced = self._lineage_context(
            freshness=stale,
            freshness_context=stale_context,
        )
        document = self._evaluate(fresh_lineage, spliced)
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(document["source"]["lineage_binding_exactly_verified"])

    def test_context_requires_exact_six_key_shape(self):
        context = self._lineage_context()
        self.assertEqual(set(context), LINEAGE_CONTEXT_KEYS)
        lineage = self._build_lineage(context)
        context["unexpected"] = True
        document = self._evaluate(lineage, context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["blockers"], ["ADAPTER_FRESHNESS_LINEAGE_V2_INVALID"]
        )

    def test_malformed_inputs_are_total_and_fail_closed(self):
        document = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3(
            None,
            lineage_binding_verification_context=None,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["policy"]["risk_increasing"], None)

    def test_exact_verifier_accepts_only_exact_rebuild(self):
        context = self._lineage_context()
        lineage = self._build_lineage(context)
        document = self._evaluate(lineage, context)
        with self.chain.fixture.source_verifiers():
            receipt = verify_strategy_correlation_cluster_portfolio_risk_adapter_v3(
                document,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(receipt["status"], "PASS")
        tampered = copy.deepcopy(document)
        tampered["decision"] = "UNKNOWN"
        with self.chain.fixture.source_verifiers():
            receipt = verify_strategy_correlation_cluster_portfolio_risk_adapter_v3(
                tampered,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["adapter_v3_status"], "UNKNOWN")

    def test_evaluation_does_not_mutate_inputs(self):
        context = self._lineage_context()
        lineage = self._build_lineage(context)
        lineage_before = copy.deepcopy(lineage)
        context_before = copy.deepcopy(context)
        self._evaluate(lineage, context)
        self.assertEqual(lineage, lineage_before)
        self.assertEqual(context, context_before)

    def test_output_is_summary_only(self):
        context = self._lineage_context()
        document = self._evaluate(self._build_lineage(context), context)
        serialized = json.dumps(document, sort_keys=True)
        for forbidden in (
            '"positions"',
            '"completed_price_rows"',
            '"return_series"',
            '"correlation_matrix"',
            '"adapter_v1_document"',
            '"freshness_evaluation"',
            '"legacy_matrix_binding"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(len(document["adapter_hash"]), 64)

    def test_authority_is_permanently_locked(self):
        context = self._lineage_context()
        document = self._evaluate(self._build_lineage(context), context)
        authority = document["authority"]
        for key, value in authority.items():
            if key in ("research_only", "local_decision_only"):
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])


if __name__ == "__main__":
    unittest.main()
