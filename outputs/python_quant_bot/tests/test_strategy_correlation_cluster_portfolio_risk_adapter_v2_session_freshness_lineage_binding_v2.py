from __future__ import annotations

import ast
import copy
import inspect
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2
    as contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_adapter_v2 as adapter_v2_tests,
)
from tests import (
    test_strategy_correlation_cluster_temporal_stability as temporal_tests,
)
from tests.synthetic_portfolio_risk_freshness_chain import (
    SyntheticCorrelatedPortfolioRiskFreshnessChain,
)


class StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.chain = SyntheticCorrelatedPortfolioRiskFreshnessChain()
        self.addCleanup(self.chain.close)
        self.document = self.build()

    def build(self, **overrides):
        values = {
            "adapter_v2_document": self.chain.adapter_v2_document,
            "freshness_evaluation": self.chain.freshness_evaluation,
            "legacy_matrix_binding": self.chain.legacy_binding,
            "adapter_v2_verification_context": self.chain.adapter_v2_context,
            "freshness_verification_context": self.chain.freshness_context,
            "legacy_matrix_binding_verification_context": self.chain.legacy_context,
        }
        values.update(overrides)
        with self.chain.source_verifiers():
            return contract.build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
                **values
            )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "adapter_v2_document": self.chain.adapter_v2_document,
            "freshness_evaluation": self.chain.freshness_evaluation,
            "legacy_matrix_binding": self.chain.legacy_binding,
            "adapter_v2_verification_context": self.chain.adapter_v2_context,
            "freshness_verification_context": self.chain.freshness_context,
            "legacy_matrix_binding_verification_context": self.chain.legacy_context,
        }
        values.update(overrides)
        with self.chain.source_verifiers():
            return contract.verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
                **values
            )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV2Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV2Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_v1_gap_is_exactly_the_two_replaced_matrix_checks(self):
        predecessor = self.chain.build_lineage_v1()
        self.assertEqual(predecessor["status"], "BLOCK")
        self.assertEqual(
            set(predecessor["blockers"]),
            {
                "adapter_native_pairwise_matrix_identity",
                "public_source_hash_projection",
            },
        )

    def test_correlated_three_symbol_same_lineage_passes_v2(self):
        self.assertEqual(self.chain.complete_link_gate["status"], "PASS")
        self.assertEqual(self.chain.full_stability_gate["status"], "PASS")
        self.assertEqual(self.chain.temporal_stability_gate["status"], "PASS")
        self.assertEqual(self.chain.adapter_v2_document["status"], "PASS")
        self.assertEqual(self.chain.freshness_evaluation["status"], "PASS")
        self.assertEqual(self.document["status"], "PASS")
        self.assertTrue(self.document["facts"]["shared_native_lineage_verified"])
        self.assertTrue(self.document["facts"]["adapter_v2_pass_observed"])
        self.assertTrue(self.document["facts"]["session_freshness_pass_observed"])
        self.assertFalse(self.document["facts"]["joint_admission_decision_made"])

    def test_replay_and_adapter_matrix_hashes_are_distinct_and_bound(self):
        source = self.document["source"]
        self.assertNotEqual(
            source["native_pairwise_matrix_hash"],
            source["adapter_projected_matrix_hash"],
        )
        self.assertEqual(
            source["native_pairwise_matrix_hash"],
            self.chain.matrix_replay["correlation_matrix"]["matrix_hash"],
        )
        self.assertEqual(
            source["native_uncertainty_audit_hash"],
            self.chain.uncertainty_audit["audit_hash"],
        )
        self.assertEqual(
            source["adapter_projected_matrix_hash"],
            self.chain.adapter_matrix["matrix_hash"],
        )

    def test_stale_freshness_preserves_lineage_and_component_block(self):
        stale, context = self.chain.build_freshness("2026-12-22T00:00:00Z")
        document = self.build(
            freshness_evaluation=stale,
            freshness_verification_context=context,
        )
        self.assertEqual(stale["status"], "BLOCK")
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["component_states"]["session_freshness_status"],
            "BLOCK",
        )
        self.assertFalse(document["facts"]["session_freshness_pass_observed"])
        self.assertFalse(document["facts"]["joint_admission_decision_made"])

    def test_unrelated_stable_adapter_is_rejected_as_cross_splice(self):
        adapter_case_type = getattr(
            adapter_v2_tests,
            "StrategyCorrelationClusterPortfolioRiskAdapterV2Tests",
        )
        temporal_case_type = getattr(
            temporal_tests,
            "StrategyCorrelationClusterTemporalStabilityTests",
        )
        adapter_case = adapter_case_type(methodName="runTest")
        adapter_case.setUp()
        temporal_case = temporal_case_type(methodName="runTest")
        temporal_case.setUp()
        case = adapter_case._case(
            temporal_case._piecewise_gap(weak_window=None)
        )
        adapter = adapter_case._build(case)
        context = {
            "adapter_v1_document": case["adapter_v1"],
            "temporal_stability_gate": case["temporal_gate"],
            "adapter_v1_verification_context": case["adapter_context"],
            "temporal_stability_verification_context": case["temporal_context"],
        }
        document = self.build(
            adapter_v2_document=adapter,
            adapter_v2_verification_context=context,
        )
        self.assertEqual(adapter["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "binding_v1_predecessor_diagnostics_compatible",
            document["blockers"],
        )

    def test_temporal_uncertainty_context_tamper_is_rejected(self):
        changed = copy.deepcopy(self.chain.adapter_v2_context)
        changed["temporal_stability_verification_context"][
            "source_uncertainty_audit"
        ]["audit_hash"] = "0" * 64
        document = self.build(adapter_v2_verification_context=changed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "binding_v1_predecessor_diagnostics_compatible",
            document["blockers"],
        )

    def test_native_replay_value_tamper_is_rejected(self):
        changed = copy.deepcopy(self.chain.freshness_context)
        changed["registration_inputs"]["native_cutoff_context"]["matrix_replay"][
            "correlation_matrix"
        ]["pairs"][0]["pearson_correlation"] = 0.0
        document = self.build(freshness_verification_context=changed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "binding_v1_predecessor_diagnostics_compatible",
            document["blockers"],
        )

    def test_public_verifier_accepts_exact_rebuild_and_rejects_tamper(self):
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["lineage_binding_exactly_verified"])
        self.assertEqual(result["lineage_binding_status"], "PASS")
        changed = copy.deepcopy(self.document)
        changed["facts"]["joint_admission_decision_made"] = True
        changed = seal_strict_canonical_document(changed, "lineage_binding_hash")
        result = self.verify(document=changed)
        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["joint_admission_decision_allowed"])

    def test_output_redacts_predecessor_raw_documents_matrices_and_returns(self):
        keys = self._all_keys(self.document)
        for forbidden in (
            "price_rows",
            "datasets",
            "correlation_matrix",
            "return_series",
            "pair_results",
            "sources",
            "signature_base64",
            "selection_cells",
            "completed_price_input",
        ):
            self.assertNotIn(forbidden, keys)
        facts = self.document["facts"]
        self.assertFalse(facts["source_documents_embedded"])
        self.assertFalse(facts["predecessor_diagnostics_embedded"])
        self.assertFalse(facts["correlation_matrices_embedded"])

    def test_authority_external_trust_and_profit_remain_false(self):
        facts = self.document["facts"]
        self.assertFalse(facts["external_provider_trust_verified"])
        self.assertFalse(facts["external_time_authority_verified"])
        self.assertFalse(facts["profitability_proven"])
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_build_is_deterministic_and_does_not_mutate_inputs(self):
        values = (
            copy.deepcopy(self.chain.adapter_v2_document),
            copy.deepcopy(self.chain.freshness_evaluation),
            copy.deepcopy(self.chain.legacy_binding),
            copy.deepcopy(self.chain.adapter_v2_context),
            copy.deepcopy(self.chain.freshness_context),
            copy.deepcopy(self.chain.legacy_context),
        )
        snapshots = copy.deepcopy(values)
        first = self.build(
            adapter_v2_document=values[0],
            freshness_evaluation=values[1],
            legacy_matrix_binding=values[2],
            adapter_v2_verification_context=values[3],
            freshness_verification_context=values[4],
            legacy_matrix_binding_verification_context=values[5],
        )
        self.assertEqual(first, self.build())
        self.assertEqual(values, snapshots)

    def test_api_imports_schema_fingerprint_and_exports_are_locked(self):
        parameters = inspect.signature(
            contract.build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2
        ).parameters
        self.assertEqual(
            set(parameters),
            {
                "adapter_v2_document",
                "freshness_evaluation",
                "legacy_matrix_binding",
                "adapter_v2_verification_context",
                "freshness_verification_context",
                "legacy_matrix_binding_verification_context",
            },
        )
        source = inspect.getsource(contract)
        tree = ast.parse(source)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        self.assertFalse(
            any(
                module.endswith((".server", ".risk_service", ".portfolio_shadow_risk"))
                for module in modules
            )
        )
        self.assertEqual(
            self.document["schema_version"],
            contract.BINDING_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.document["static_fingerprint"],
            contract.STATIC_FINGERPRINT,
        )
        self.assertEqual(
            contract.__all__,
            [
                "BINDING_SCHEMA_VERSION",
                "BINDING_VERIFICATION_SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
                "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
            ],
        )


if __name__ == "__main__":
    unittest.main()
