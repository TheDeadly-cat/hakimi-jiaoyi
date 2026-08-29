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
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v3 import (
    SCHEMA_VERSION,
    STAGE_ORDER,
    STATIC_FINGERPRINT,
    project_strategy_correlation_cluster_portfolio_risk_projection_v3,
    verify_strategy_correlation_cluster_portfolio_risk_projection_v3,
)
from tests.synthetic_portfolio_risk_freshness_chain import (
    SyntheticCorrelatedPortfolioRiskFreshnessChain,
)


def build_projection_v3_fixture(*, reference_utc=None, adapter_overrides=None):
    chain = SyntheticCorrelatedPortfolioRiskFreshnessChain()
    adapter_v2 = chain.adapter_v2_document
    adapter_v2_context = chain.adapter_v2_context
    if adapter_overrides:
        adapter_v1_context = copy.deepcopy(chain.adapter_v1_context)
        adapter_v1_context.update(adapter_overrides)
        with chain.fixture.source_verifiers():
            adapter_v1 = (
                evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
                    **adapter_v1_context
                )
            )
            adapter_v2_context = {
                "adapter_v1_document": adapter_v1,
                "temporal_stability_gate": chain.temporal_stability_gate,
                "adapter_v1_verification_context": adapter_v1_context,
                "temporal_stability_verification_context": chain.temporal_context,
            }
            adapter_v2 = (
                evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
                    adapter_v1,
                    chain.temporal_stability_gate,
                    adapter_v1_verification_context=adapter_v1_context,
                    temporal_stability_verification_context=chain.temporal_context,
                )
            )

    if reference_utc is None:
        freshness = chain.freshness_evaluation
        freshness_context = chain.freshness_context
    else:
        freshness, freshness_context = chain.build_freshness(reference_utc)
    lineage_context = {
        "adapter_v2_document": adapter_v2,
        "freshness_evaluation": freshness,
        "legacy_matrix_binding": chain.legacy_binding,
        "adapter_v2_verification_context": adapter_v2_context,
        "freshness_verification_context": freshness_context,
        "legacy_matrix_binding_verification_context": chain.legacy_context,
    }
    with chain.fixture.source_verifiers():
        lineage = build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
            adapter_v2,
            freshness,
            chain.legacy_binding,
            adapter_v2_verification_context=adapter_v2_context,
            freshness_verification_context=freshness_context,
            legacy_matrix_binding_verification_context=chain.legacy_context,
        )
        adapter = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3(
            lineage,
            lineage_binding_verification_context=lineage_context,
        )
        projection = project_strategy_correlation_cluster_portfolio_risk_projection_v3(
            adapter,
            lineage,
            lineage_binding_verification_context=lineage_context,
        )
    return chain, adapter, lineage, lineage_context, projection


class PortfolioRiskProjectionV3Tests(unittest.TestCase):
    def test_fresh_local_pass_projects_neutral_four_stage_shape(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        self.assertEqual(projection["schema_version"], SCHEMA_VERSION)
        self.assertEqual(projection["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(projection["status"], "PASS")
        self.assertEqual(
            [stage["key"] for stage in projection["stages"]], list(STAGE_ORDER)
        )
        self.assertEqual(projection["stages"][1]["state"], "NONE_OBSERVED")
        self.assertEqual(
            projection["stages"][2]["state"], "LOCAL_POLICY_SATISFIED"
        )
        self.assertEqual(projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_stale_risk_increase_is_valid_projection_of_declared_gap(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z"
        )
        self.assertEqual(projection["status"], "PASS")
        self.assertEqual(projection["local_decision"]["status"], "BLOCK")
        self.assertEqual(projection["stages"][1]["state"], "DECLARED")
        self.assertEqual(projection["stages"][1]["detail"], "SESSION_FRESHNESS")
        self.assertEqual(
            projection["stages"][2]["state"], "LOCAL_POLICY_BLOCKED"
        )

    def test_stale_risk_reduction_projects_explicit_exemption(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z",
            adapter_overrides={"risk_increasing": False},
        )
        self.assertEqual(projection["local_decision"]["status"], "PASS")
        self.assertFalse(projection["local_decision"]["session_freshness_required"])
        self.assertEqual(
            projection["stages"][1]["detail"],
            "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION",
        )

    def test_base_budget_block_is_not_confused_with_projection_failure(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            adapter_overrides={"proposed_notional": 5000}
        )
        self.assertEqual(projection["status"], "PASS")
        self.assertEqual(projection["local_decision"]["status"], "BLOCK")
        self.assertEqual(
            projection["stages"][1]["detail"], "BASE_PORTFOLIO_RISK_BUDGET"
        )

    def test_tampered_adapter_fails_to_unknown_without_permission(self):
        chain, adapter, lineage, context, _ = build_projection_v3_fixture()
        adapter["adapter_hash"] = "0" * 64
        with chain.fixture.source_verifiers():
            projection = project_strategy_correlation_cluster_portfolio_risk_projection_v3(
                adapter,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(projection["decision"], "UNKNOWN_SOURCE")
        self.assertEqual(
            [stage["state"] for stage in projection["stages"]],
            ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNAUTHORIZED"],
        )

    def test_exact_verifier_rejects_projection_tamper(self):
        chain, adapter, lineage, context, projection = build_projection_v3_fixture()
        with chain.fixture.source_verifiers():
            receipt = verify_strategy_correlation_cluster_portfolio_risk_projection_v3(
                projection,
                adapter,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(receipt["status"], "PASS")
        projection["stages"][3]["state"] = "AUTHORIZED"
        with chain.fixture.source_verifiers():
            receipt = verify_strategy_correlation_cluster_portfolio_risk_projection_v3(
                projection,
                adapter,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(receipt["status"], "BLOCK")

    def test_projection_is_deterministic_and_does_not_mutate_inputs(self):
        chain, adapter, lineage, context, first = build_projection_v3_fixture()
        adapter_before = copy.deepcopy(adapter)
        lineage_before = copy.deepcopy(lineage)
        context_before = copy.deepcopy(context)
        with chain.fixture.source_verifiers():
            second = project_strategy_correlation_cluster_portfolio_risk_projection_v3(
                adapter,
                lineage,
                lineage_binding_verification_context=context,
            )
        self.assertEqual(first, second)
        self.assertEqual(adapter, adapter_before)
        self.assertEqual(lineage, lineage_before)
        self.assertEqual(context, context_before)

    def test_projection_is_summary_only(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        serialized = json.dumps(projection, sort_keys=True)
        for forbidden in (
            '"positions"',
            '"completed_price_rows"',
            '"return_series"',
            '"correlation_matrix"',
            '"adapter_v3_document"',
            '"lineage_binding_v2"',
            '"verification_context"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(len(projection["projection_hash"]), 64)

    def test_authority_and_profitability_are_always_false(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        for key, value in projection["authority"].items():
            if key in ("research_only", "presentation_only"):
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)
        self.assertFalse(projection["facts"]["profitability_proven"])
        self.assertFalse(projection["facts"]["runtime_consumer_bound"])


if __name__ == "__main__":
    unittest.main()
