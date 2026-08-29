from __future__ import annotations

import ast
import copy
import inspect
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v1 as adapter_v1_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2 as contract,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
import tests.test_strategy_correlation_cluster_temporal_stability as temporal_test_module


class StrategyCorrelationClusterPortfolioRiskAdapterV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        temporal_type = getattr(
            temporal_test_module, "StrategyCorrelationClusterTemporalStabilityTests"
        )
        self.temporal_case = temporal_type(methodName="test_all_stable_windows_pass")
        self.temporal_case.setUp()
        self.stable = self._case(
            self.temporal_case._piecewise_gap(weak_window=None)
        )
        self.unstable = self._case(self.temporal_case._piecewise_gap())

    def _case(self, values, *, risk_increasing=True, proposed_notional=500):
        source, preregistration, matrix, cells, complete_gate, full_stability = values
        temporal_gate = self.temporal_case._evaluate(values)
        complete_audit = build_correlation_cluster_complete_link_audit(
            preregistration, matrix
        )
        legacy_pairs = {
            f"{pair['left_symbol']}|{pair['right_symbol']}": pair[
                "pearson_correlation"
            ]
            for pair in matrix["pairs"]
        }
        adapter_context = {
            "preregistration": preregistration,
            "cluster_correlation_matrix": matrix,
            "complete_link_audit": complete_audit,
            "equity": 10_000,
            "positions": [
                {"symbol": "A", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "B",
            "proposed_notional": proposed_notional,
            "proposed_direction": "LONG",
            "proposed_cluster": "",
            "risk_increasing": risk_increasing,
            "legacy_correlations": {"pairs": legacy_pairs},
            "regime": None,
            "legacy_limits": None,
            "max_cluster_gross_pct": 45.0,
        }
        adapter_v1 = adapter_v1_contract.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            **adapter_context
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
        document = contract.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            adapter_v1,
            temporal_gate,
            adapter_v1_verification_context=adapter_context,
            temporal_stability_verification_context=temporal_context,
        )
        return {
            "values": values,
            "adapter_v1": adapter_v1,
            "temporal_gate": temporal_gate,
            "adapter_context": adapter_context,
            "temporal_context": temporal_context,
            "document": document,
        }

    def _build(self, case, **overrides):
        values = {
            "adapter_v1_document": case["adapter_v1"],
            "temporal_stability_gate": case["temporal_gate"],
            "adapter_v1_verification_context": case["adapter_context"],
            "temporal_stability_verification_context": case["temporal_context"],
        }
        values.update(overrides)
        return contract.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            **values
        )

    def _verify(self, case, document=None, **overrides):
        values = {
            "document": case["document"] if document is None else document,
            "adapter_v1_document": case["adapter_v1"],
            "temporal_stability_gate": case["temporal_gate"],
            "adapter_v1_verification_context": case["adapter_context"],
            "temporal_stability_verification_context": case["temporal_context"],
        }
        values.update(overrides)
        return contract.verify_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            **values
        )

    def test_v1_gap_same_pass_decision_ignores_temporal_block(self) -> None:
        self.assertEqual(self.stable["adapter_v1"]["status"], "PASS")
        self.assertEqual(self.unstable["adapter_v1"]["status"], "PASS")
        self.assertEqual(
            self.stable["adapter_v1"]["adapter_hash"],
            self.unstable["adapter_v1"]["adapter_hash"],
        )
        self.assertEqual(self.stable["temporal_gate"]["status"], "PASS")
        self.assertEqual(self.unstable["temporal_gate"]["status"], "BLOCK")

    def test_stable_risk_increase_requires_and_passes_both_gates(self) -> None:
        document = self.stable["document"]
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY",
        )
        self.assertTrue(document["facts"]["base_adapter_passed"])
        self.assertTrue(document["facts"]["temporal_stability_passed"])
        self.assertTrue(document["facts"]["temporal_stability_required"])

    def test_unstable_window_blocks_v1_pass_for_risk_increase(self) -> None:
        document = self.unstable["document"]
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["decision"], "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY"
        )
        self.assertIn("TEMPORAL_STABILITY_GATE_BLOCKED", document["blockers"])
        self.assertGreater(document["stability"]["blocked_window_count"], 0)
        self.assertGreater(document["stability"]["unstable_window_count"], 0)

    def test_insufficient_effective_sample_also_blocks_risk_increase(self) -> None:
        case = self._case(self.temporal_case._uniform())
        self.assertEqual(case["temporal_gate"]["status"], "BLOCK")
        self.assertEqual(case["document"]["status"], "BLOCK")
        self.assertGreater(
            case["document"]["stability"]["insufficient_sample_window_count"], 0
        )

    def test_base_adapter_block_is_preserved_before_temporal_pass(self) -> None:
        case = self._case(
            self.temporal_case._piecewise_gap(weak_window=None),
            proposed_notional=5_000,
        )
        self.assertEqual(case["adapter_v1"]["status"], "BLOCK")
        self.assertEqual(case["document"]["status"], "BLOCK")
        self.assertEqual(
            case["document"]["decision"], "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET"
        )

    def test_risk_reduction_path_does_not_turn_temporal_block_into_authority(self) -> None:
        case = self._case(
            self.temporal_case._piecewise_gap(), risk_increasing=False
        )
        self.assertEqual(case["adapter_v1"]["status"], "PASS")
        self.assertEqual(case["temporal_gate"]["status"], "BLOCK")
        self.assertEqual(case["document"]["status"], "PASS")
        self.assertEqual(
            case["document"]["decision"],
            "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED",
        )
        self.assertFalse(case["document"]["facts"]["temporal_stability_required"])
        self.assertFalse(case["document"]["authority"]["current_admission_allowed"])

    def test_negative_stable_dependence_is_sign_agnostic(self) -> None:
        case = self._case(
            self.temporal_case._piecewise_gap(weak_window=None, negative=True)
        )
        self.assertEqual(case["temporal_gate"]["status"], "PASS")
        self.assertEqual(case["document"]["status"], "PASS")

    def test_public_verifier_accepts_exact_rebuild(self) -> None:
        result = self._verify(self.stable)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["adapter_exactly_verified"])

    def test_public_verifier_rejects_projection_tamper(self) -> None:
        changed = copy.deepcopy(self.stable["document"])
        changed["authority"]["paper_authorized"] = True
        result = self._verify(self.stable, document=changed)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["paper_authorized"])

    def test_tampered_adapter_v1_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["adapter_v1"])
        changed["status"] = "BLOCK"
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(self.stable, adapter_v1_document=changed)

    def test_tampered_temporal_gate_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["temporal_gate"])
        changed["status"] = "BLOCK"
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(self.stable, temporal_stability_gate=changed)

    def test_adapter_context_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["adapter_context"])
        changed["proposed_notional"] = 501
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(self.stable, adapter_v1_verification_context=changed)

    def test_temporal_context_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["temporal_context"])
        changed["strategy_id"] = "OTHER"
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable, temporal_stability_verification_context=changed
            )

    def test_shared_preregistration_mismatch_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["temporal_context"])
        changed["preregistration"] = copy.deepcopy(changed["preregistration"])
        changed["preregistration"]["preregistration_hash"] = "0" * 64
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable, temporal_stability_verification_context=changed
            )

    def test_shared_matrix_mismatch_is_rejected(self) -> None:
        changed = copy.deepcopy(self.stable["temporal_context"])
        changed["correlation_matrix"] = copy.deepcopy(changed["correlation_matrix"])
        changed["correlation_matrix"]["matrix_hash"] = "0" * 64
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable, temporal_stability_verification_context=changed
            )

    def test_proposed_symbol_selection_cell_binding_is_required(self) -> None:
        changed = copy.deepcopy(self.stable["temporal_context"])
        changed["selection_cells"] = [
            cell for cell in changed["selection_cells"] if cell["symbol"] != "B"
        ]
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable, temporal_stability_verification_context=changed
            )

    def test_context_schemas_are_exact(self) -> None:
        adapter_context = copy.deepcopy(self.stable["adapter_context"])
        adapter_context["extra"] = None
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable, adapter_v1_verification_context=adapter_context
            )
        temporal_context = copy.deepcopy(self.stable["temporal_context"])
        temporal_context["extra"] = None
        with self.assertRaises(contract.PortfolioRiskAdapterV2ContractError):
            self._build(
                self.stable,
                temporal_stability_verification_context=temporal_context,
            )

    def test_output_redacts_components_returns_and_raw_correlations(self) -> None:
        encoded = json.dumps(self.stable["document"], sort_keys=True)
        for forbidden in (
            "temporal_stability_audit",
            "window_results",
            '"return_series":',
            "pearson_correlation",
            "legacy_correlations",
            "selection_cells",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.stable["document"]["facts"]["component_results_embedded"])

    def test_build_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        adapter = copy.deepcopy(self.stable["adapter_v1"])
        temporal = copy.deepcopy(self.stable["temporal_gate"])
        adapter_context = copy.deepcopy(self.stable["adapter_context"])
        temporal_context = copy.deepcopy(self.stable["temporal_context"])
        snapshots = copy.deepcopy((adapter, temporal, adapter_context, temporal_context))
        first = self._build(
            self.stable,
            adapter_v1_document=adapter,
            temporal_stability_gate=temporal,
            adapter_v1_verification_context=adapter_context,
            temporal_stability_verification_context=temporal_context,
        )
        second = self._build(self.stable)
        self.assertEqual(first, second)
        self.assertEqual(
            snapshots, (adapter, temporal, adapter_context, temporal_context)
        )

    def test_authority_and_profitability_remain_false(self) -> None:
        document = self.stable["document"]
        self.assertTrue(document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertFalse(document["facts"]["runtime_gate_integrated"])
        self.assertFalse(document["facts"]["risk_service_invoked"])

    def test_production_module_has_no_runtime_imports(self) -> None:
        tree = ast.parse(inspect.getsource(contract))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        self.assertFalse(
            any(
                module.endswith((".portfolio_shadow_risk", ".risk_service", ".server"))
                for module in modules
            )
        )

    def test_schema_fingerprint_and_exports_are_version_locked(self) -> None:
        document = self.stable["document"]
        self.assertEqual(document["schema_version"], contract.SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], contract.STATIC_FINGERPRINT)
        self.assertNotIn("READY", json.dumps(document, sort_keys=True))
        self.assertEqual(
            set(contract.__all__),
            {
                "PortfolioRiskAdapterV2ContractError",
                "SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "VERIFICATION_SCHEMA_VERSION",
                "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2",
                "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2",
            },
        )


if __name__ == "__main__":
    unittest.main()
