from __future__ import annotations

import ast
import copy
import inspect
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1
    as contract,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1,
    evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    evaluate_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    StrategyCorrelationClusterPortfolioRiskAdapterV2Tests,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 import (
    StrategyCorrelationClusterPortfolioRiskLegacyMatrixDerivationBindingV1Tests,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    StrategyCorrelationClusterPortfolioRiskSessionFreshnessV1Tests,
)
from tests.test_strategy_correlation_cluster_temporal_stability import (
    StrategyCorrelationClusterTemporalStabilityTests,
)


class StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.legacy_fixture = (
            StrategyCorrelationClusterPortfolioRiskLegacyMatrixDerivationBindingV1Tests(
                methodName="runTest"
            )
        )
        self.legacy_fixture.setUp()
        self.addCleanup(self.legacy_fixture.doCleanups)
        self.clock_fixture = (
            StrategyCorrelationClusterPortfolioRiskSessionFreshnessV1Tests(
                methodName="runTest"
            )
        )
        self.clock_fixture.setUp()
        self.addCleanup(self.clock_fixture.doCleanups)

        self.adapter_v2_document, self.adapter_v2_context = (
            self._build_native_adapter_v2()
        )
        self.legacy_binding = self.legacy_fixture._build()
        self.legacy_context = copy.deepcopy(self.legacy_fixture.base_inputs)

        cutoff = self.legacy_fixture.completed_price_input["cutoff_date"]
        self.native_context = {
            "completed_price_input": self.legacy_fixture.completed_price_input,
            "matrix_replay": self.legacy_fixture.matrix_replay,
            "derivation_receipt": self.legacy_fixture.derivation_receipt,
            "composition_document": self.legacy_fixture.composition_document,
            "composition_context": self.legacy_fixture.composition_context,
            "expected_observation_cutoff_utc": f"{cutoff}T00:00:00Z",
        }
        with self.legacy_fixture.fixture.source_verifiers():
            self.native_manifest = (
                build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                    **self.native_context
                )
            )
        self.registration_inputs = {
            "native_cutoff_manifest": self.native_manifest,
            "native_cutoff_context": self.native_context,
            "expected_native_cutoff_manifest_hash": self.native_manifest[
                "manifest_hash"
            ],
            "max_completed_session_lag": 1,
            "declared_at_utc": "2026-09-18T00:00:00Z",
        }
        with self.legacy_fixture.fixture.source_verifiers():
            self.registration = build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                **self.registration_inputs
            )
        self.freshness_evaluation, self.freshness_context = (
            self._build_freshness("2026-12-21T00:00:00Z")
        )
        self.document = self.build()

    def _build_native_adapter_v2(self, *, legacy_correlations=None):
        preregistration = self.legacy_fixture.matrix_replay["preregistration"]
        matrix = self.legacy_fixture.matrix_replay["correlation_matrix"]
        cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "lane": "RAW_EXCESS",
                "symbol": symbol,
                "gate_status": "PASS",
            }
            for symbol in preregistration["symbols"]
        ]
        globals_ = StrategyCorrelationClusterTemporalStabilityTests._piecewise_gap.__globals__
        source = globals_["build_strategy_correlation_uncertainty_audit"](
            self.legacy_fixture.matrix_replay
        )
        complete_gate = globals_["evaluate_correlation_cluster_gate_v2"](
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        full_stability = evaluate_strategy_correlation_cluster_stability_gate(
            source,
            complete_gate,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        temporal_gate = globals_[
            "evaluate_strategy_correlation_cluster_temporal_stability_gate"
        ](
            source,
            full_stability,
            complete_link_gate=complete_gate,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        complete_audit = build_correlation_cluster_complete_link_audit(
            preregistration,
            matrix,
        )
        if legacy_correlations is None:
            legacy_correlations = {
                "pairs": {
                    key: item["correlation"]
                    for key, item in self.legacy_fixture.legacy_matrix[
                        "pairs"
                    ].items()
                }
            }
        adapter_v1_context = {
            "preregistration": preregistration,
            "cluster_correlation_matrix": matrix,
            "complete_link_audit": complete_audit,
            "equity": 10_000,
            "positions": [
                {"symbol": "A", "notional": 1_800, "direction": "LONG"}
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "proposed_cluster": "",
            "risk_increasing": True,
            "legacy_correlations": legacy_correlations,
            "regime": None,
            "legacy_limits": None,
            "max_cluster_gross_pct": 45.0,
        }
        adapter_v1 = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            **adapter_v1_context
        )
        temporal_context = {
            "source_uncertainty_audit": source,
            "full_window_stability_gate": full_stability,
            "complete_link_gate": complete_gate,
            "preregistration": preregistration,
            "correlation_matrix": matrix,
            "selection_cells": cells,
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
        }
        adapter_v2 = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            adapter_v1,
            temporal_gate,
            adapter_v1_verification_context=adapter_v1_context,
            temporal_stability_verification_context=temporal_context,
        )
        context = {
            "adapter_v1_document": adapter_v1,
            "temporal_stability_gate": temporal_gate,
            "adapter_v1_verification_context": adapter_v1_context,
            "temporal_stability_verification_context": temporal_context,
        }
        return adapter_v2, context

    def _build_freshness(self, reference_utc):
        clock = self.clock_fixture._clock(reference_utc)
        with self.legacy_fixture.fixture.source_verifiers():
            evaluation = evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
                self.registration,
                registration_inputs=self.registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=clock["attestation_hash"],
            )
        context = {
            "registration": self.registration,
            "registration_inputs": self.registration_inputs,
            "trusted_clock_attestation": clock,
            "expected_trusted_clock_attestation_hash": clock["attestation_hash"],
        }
        return evaluation, context

    def build(self, **overrides):
        values = {
            "adapter_v2_document": self.adapter_v2_document,
            "freshness_evaluation": self.freshness_evaluation,
            "legacy_matrix_binding": self.legacy_binding,
            "adapter_v2_verification_context": self.adapter_v2_context,
            "freshness_verification_context": self.freshness_context,
            "legacy_matrix_binding_verification_context": self.legacy_context,
        }
        values.update(overrides)
        with self.legacy_fixture.fixture.source_verifiers():
            return contract.build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
                **values
            )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "adapter_v2_document": self.adapter_v2_document,
            "freshness_evaluation": self.freshness_evaluation,
            "legacy_matrix_binding": self.legacy_binding,
            "adapter_v2_verification_context": self.adapter_v2_context,
            "freshness_verification_context": self.freshness_context,
            "legacy_matrix_binding_verification_context": self.legacy_context,
        }
        values.update(overrides)
        with self.legacy_fixture.fixture.source_verifiers():
            return contract.verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
                **values
            )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskAdapterV2SessionFreshnessLineageBindingV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_exact_shared_native_lineage_passes_even_when_adapter_blocks(self):
        self.assertEqual(self.adapter_v2_document["status"], "BLOCK")
        self.assertEqual(self.freshness_evaluation["status"], "PASS")
        self.assertEqual(self.legacy_binding["status"], "PASS")
        self.assertEqual(self.document["status"], "PASS")
        self.assertTrue(self.document["facts"]["shared_native_lineage_verified"])
        self.assertFalse(self.document["facts"]["adapter_v2_pass_observed"])
        self.assertFalse(self.document["facts"]["joint_admission_decision_made"])

    def test_receipt_projects_exact_component_states_without_promotion(self):
        states = self.document["component_states"]
        self.assertEqual(states["adapter_v2_status"], "BLOCK")
        self.assertEqual(states["session_freshness_status"], "PASS")
        self.assertEqual(states["legacy_matrix_binding_status"], "PASS")
        self.assertIn("COMPONENT_DECISIONS_NOT_PROMOTED", self.document["decision"])

    def test_stale_freshness_is_same_lineage_but_remains_component_block(self):
        stale, context = self._build_freshness("2026-12-22T00:00:00Z")
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

    def test_source_hashes_bind_adapter_native_freshness_and_legacy(self):
        source = self.document["source"]
        self.assertEqual(
            source["preregistration_hash"],
            self.legacy_fixture.matrix_replay["preregistration"][
                "preregistration_hash"
            ],
        )
        self.assertEqual(
            source["correlation_matrix_hash"],
            self.legacy_fixture.matrix_replay["correlation_matrix"]["matrix_hash"],
        )
        self.assertEqual(
            source["legacy_matrix_hash"],
            self.legacy_fixture.legacy_matrix["matrix_hash"],
        )
        self.assertEqual(
            source["native_cutoff_manifest_hash"],
            self.native_manifest["manifest_hash"],
        )
        self.assertEqual(
            source["freshness_registration_hash"],
            self.registration["registration_hash"],
        )

    def test_cross_spliced_three_symbol_adapter_is_blocked(self):
        adapter_fixture = StrategyCorrelationClusterPortfolioRiskAdapterV2Tests(
            methodName="runTest"
        )
        adapter_fixture.setUp()
        temporal_fixture = StrategyCorrelationClusterTemporalStabilityTests(
            methodName="runTest"
        )
        temporal_fixture.setUp()
        case = adapter_fixture._case(
            temporal_fixture._piecewise_gap(weak_window=None)
        )
        foreign_adapter = adapter_fixture._build(case)
        foreign_context = {
            "adapter_v1_document": case["adapter_v1"],
            "temporal_stability_gate": case["temporal_gate"],
            "adapter_v1_verification_context": case["adapter_context"],
            "temporal_stability_verification_context": case["temporal_context"],
        }
        document = self.build(
            adapter_v2_document=foreign_adapter,
            adapter_v2_verification_context=foreign_context,
        )
        self.assertEqual(foreign_adapter["status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "adapter_native_preregistration_identity",
            document["blockers"],
        )
        self.assertIn(
            "adapter_native_pairwise_matrix_identity",
            document["blockers"],
        )
        self.assertTrue(all(value is None for value in document["source"].values()))

    def test_exact_adapter_with_different_legacy_projection_is_blocked(self):
        changed_correlations = copy.deepcopy(
            self.adapter_v2_context["adapter_v1_verification_context"][
                "legacy_correlations"
            ]
        )
        key = sorted(changed_correlations["pairs"])[0]
        changed_correlations["pairs"][key] = 0.0
        adapter, context = self._build_native_adapter_v2(
            legacy_correlations=changed_correlations
        )
        document = self.build(
            adapter_v2_document=adapter,
            adapter_v2_verification_context=context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "adapter_legacy_matrix_projection_identity",
            document["blockers"],
        )

    def test_adapter_context_schema_drift_is_rejected(self):
        changed = copy.deepcopy(self.adapter_v2_context)
        changed["extra"] = None
        document = self.build(adapter_v2_verification_context=changed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("adapter_v2_exact_verification", document["blockers"])

    def test_freshness_context_hash_drift_is_rejected(self):
        changed = copy.deepcopy(self.freshness_context)
        changed["expected_trusted_clock_attestation_hash"] = "0" * 64
        document = self.build(freshness_verification_context=changed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "session_freshness_exact_verification",
            document["blockers"],
        )

    def test_legacy_binding_context_drift_is_rejected(self):
        changed = copy.deepcopy(self.legacy_context)
        changed["expected_attestation_hash"] = "0" * 64
        document = self.build(
            legacy_matrix_binding_verification_context=changed
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "legacy_matrix_binding_exact_verification",
            document["blockers"],
        )

    def test_resealed_component_document_tamper_is_rejected(self):
        changed = copy.deepcopy(self.freshness_evaluation)
        changed["decision"] = "SESSION_LAG_WITHIN_POLICY"
        changed = seal_strict_canonical_document(changed, "evaluation_hash")
        document = self.build(freshness_evaluation=changed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "session_freshness_exact_verification",
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

    def test_output_redacts_raw_documents_rows_matrices_and_returns(self):
        keys = self._all_keys(self.document)
        for forbidden in (
            "price_rows",
            "datasets",
            "correlation_matrix",
            "return_series",
            "sources",
            "signature_base64",
            "selection_cells",
            "temporal_stability_audit",
            "completed_price_input",
        ):
            self.assertNotIn(forbidden, keys)
        facts = self.document["facts"]
        self.assertFalse(facts["source_documents_embedded"])
        self.assertFalse(facts["completed_price_rows_embedded"])
        self.assertFalse(facts["correlation_matrices_embedded"])
        self.assertFalse(facts["return_series_embedded"])

    def test_external_trust_profit_and_authority_remain_false(self):
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
        adapter = copy.deepcopy(self.adapter_v2_document)
        freshness = copy.deepcopy(self.freshness_evaluation)
        legacy = copy.deepcopy(self.legacy_binding)
        contexts = copy.deepcopy(
            (
                self.adapter_v2_context,
                self.freshness_context,
                self.legacy_context,
            )
        )
        snapshots = copy.deepcopy((adapter, freshness, legacy, contexts))
        first = self.build(
            adapter_v2_document=adapter,
            freshness_evaluation=freshness,
            legacy_matrix_binding=legacy,
            adapter_v2_verification_context=contexts[0],
            freshness_verification_context=contexts[1],
            legacy_matrix_binding_verification_context=contexts[2],
        )
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(snapshots, (adapter, freshness, legacy, contexts))

    def test_context_apis_are_exact_and_accept_no_runtime_handle(self):
        parameters = inspect.signature(
            contract.build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1
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

    def test_production_module_has_no_runtime_server_or_execution_imports(self):
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

    def test_schema_fingerprint_and_exports_are_locked(self):
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
                "build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
                "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
            ],
        )


if __name__ == "__main__":
    unittest.main()
