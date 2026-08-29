from __future__ import annotations

import copy
import inspect
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v2 as projection_module,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v2 import (
    PROJECTION_SCHEMA_VERSION,
    PROJECTION_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_projection_v2,
    verify_strategy_correlation_cluster_portfolio_risk_projection_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    StrategyCorrelationClusterPortfolioRiskAdapterV2Tests,
)
from tests.test_strategy_correlation_cluster_temporal_stability import (
    StrategyCorrelationClusterTemporalStabilityTests,
)


_USE_CASE_DOCUMENT = object()


class StrategyCorrelationClusterPortfolioRiskProjectionV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter_fixture = StrategyCorrelationClusterPortfolioRiskAdapterV2Tests(
            methodName="runTest"
        )
        self.adapter_fixture.setUp()
        self.temporal_fixture = StrategyCorrelationClusterTemporalStabilityTests(
            methodName="runTest"
        )
        self.temporal_fixture.setUp()

    def _case(
        self,
        *,
        stable: bool = True,
        risk_increasing: bool = True,
        proposed_notional: int = 500,
    ):
        values = (
            self.temporal_fixture._piecewise_gap(weak_window=None)
            if stable
            else self.temporal_fixture._piecewise_gap()
        )
        return self.adapter_fixture._case(
            values,
            risk_increasing=risk_increasing,
            proposed_notional=proposed_notional,
        )

    def _projection(self, case, document=_USE_CASE_DOCUMENT):
        adapter = (
            self.adapter_fixture._build(case)
            if document is _USE_CASE_DOCUMENT
            else document
        )
        return build_strategy_correlation_cluster_portfolio_risk_projection_v2(
            adapter,
            case["adapter_v1"],
            case["temporal_gate"],
            adapter_v1_verification_context=case["adapter_context"],
            temporal_stability_verification_context=case["temporal_context"],
        )

    def _verify(self, case, projection, adapter_document=_USE_CASE_DOCUMENT):
        adapter = (
            self.adapter_fixture._build(case)
            if adapter_document is _USE_CASE_DOCUMENT
            else adapter_document
        )
        return verify_strategy_correlation_cluster_portfolio_risk_projection_v2(
            projection,
            adapter,
            case["adapter_v1"],
            case["temporal_gate"],
            adapter_v1_verification_context=case["adapter_context"],
            temporal_stability_verification_context=case["temporal_context"],
        )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskProjectionV2Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskProjectionV2Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_not_supplied_is_explicit_and_fail_closed(self):
        case = self._case()
        projection = self._projection(case, None)
        self.assertEqual(projection["status"], "NOT_SUPPLIED")
        self.assertEqual(
            [item["state"] for item in projection["pipeline"]],
            ["NOT_SUPPLIED", "NOT_SUPPLIED", "UNMOUNTED_CANDIDATE", "UNAUTHORIZED"],
        )
        self.assertEqual(projection["summary"]["adapter_decision"], "NOT_SUPPLIED")
        self.assertIsNone(projection["summary"]["window_result_count"])

    def test_stable_risk_increase_projects_joint_observation(self):
        case = self._case(stable=True)
        projection = self._projection(case)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(projection["pipeline"][0]["state"], "VERIFIED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY",
        )
        self.assertEqual(
            projection["summary"]["adapter_decision"],
            "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY",
        )
        self.assertTrue(projection["summary"]["base_adapter_passed"])
        self.assertTrue(projection["summary"]["temporal_stability_passed"])
        self.assertEqual(projection["summary"]["symbol_ticket_count"], 3)
        self.assertEqual(projection["summary"]["effective_independent_bet_count"], 2)
        self.assertEqual(projection["summary"]["correlated_duplicate_ticket_count"], 1)

    def test_unstable_window_projects_temporal_gap_without_authority(self):
        case = self._case(stable=False)
        projection = self._projection(case)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "TEMPORAL_STABILITY_GAP_PRESENT",
        )
        self.assertEqual(
            projection["summary"]["adapter_decision"],
            "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY",
        )
        self.assertFalse(projection["summary"]["temporal_stability_passed"])
        self.assertGreater(projection["summary"]["unstable_window_count"], 0)
        self.assertEqual(projection["pipeline"][3]["state"], "UNAUTHORIZED")

    def test_base_portfolio_block_precedes_temporal_pass(self):
        case = self._case(stable=True, proposed_notional=5_000)
        projection = self._projection(case)
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "PORTFOLIO_RISK_LIMIT_GAP_PRESENT",
        )
        self.assertEqual(
            projection["summary"]["adapter_decision"],
            "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET",
        )
        self.assertFalse(projection["summary"]["base_adapter_passed"])
        self.assertTrue(projection["summary"]["temporal_stability_passed"])

    def test_risk_reduction_is_distinct_and_never_implies_permission(self):
        case = self._case(stable=False, risk_increasing=False)
        projection = self._projection(case)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(projection["pipeline"][1]["state"], "RISK_REDUCTION_PATH")
        self.assertEqual(
            projection["summary"]["adapter_decision"],
            "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED",
        )
        self.assertFalse(projection["summary"]["risk_increasing"])
        self.assertFalse(projection["summary"]["temporal_stability_required"])
        self.assertEqual(projection["pipeline"][3]["state"], "UNAUTHORIZED")

    def test_resealed_adapter_tamper_projects_unknown(self):
        case = self._case()
        adapter = self.adapter_fixture._build(case)
        tampered = copy.deepcopy(adapter)
        tampered["decision"] = "READY"
        tampered = seal_strict_canonical_document(tampered, "adapter_hash")
        projection = self._projection(case, tampered)
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertEqual(projection["pipeline"][0]["state"], "UNKNOWN")
        self.assertEqual(projection["summary"]["adapter_decision"], "UNKNOWN")
        self.assertIsNone(projection["source"]["adapter_hash"])

    def test_non_mapping_adapter_projects_unknown_without_echo(self):
        case = self._case()
        projection = self._projection(case, "claimed-pass")
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertNotIn("claimed-pass", str(projection))

    def test_projection_verifier_rejects_resealed_value_and_type_tampering(self):
        case = self._case()
        adapter = self.adapter_fixture._build(case)
        projection = self._projection(case, adapter)
        self.assertEqual(
            self._verify(case, projection, adapter)["status"],
            "PASS",
        )
        variants = []
        permission_tamper = copy.deepcopy(projection)
        permission_tamper["authority"]["paper_authorized"] = True
        variants.append(permission_tamper)
        type_tamper = copy.deepcopy(projection)
        type_tamper["summary"]["window_result_count"] = 3.0
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(
                    tampered,
                    "projection_hash",
                )
                verification = self._verify(case, resealed, adapter)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["projection_status"], "UNKNOWN")

    def test_projection_redacts_raw_sources_components_and_window_rows(self):
        case = self._case()
        projection = self._projection(case)
        keys = self._all_keys(projection)
        for forbidden in (
            "pair_results",
            "pearson_correlation",
            "return_series",
            "window_results",
            "checks",
            "cluster_exposures",
            "selection_cells",
            "source_uncertainty_audit",
            "full_window_stability_gate",
        ):
            self.assertNotIn(forbidden, keys)
        self.assertFalse(projection["facts"]["source_documents_embedded"])
        self.assertFalse(projection["facts"]["raw_correlations_embedded"])
        self.assertFalse(projection["facts"]["return_series_embedded"])
        self.assertFalse(projection["facts"]["window_rows_embedded"])

    def test_inputs_and_adapter_are_not_mutated(self):
        case = self._case()
        adapter = self.adapter_fixture._build(case)
        expected_case = copy.deepcopy(case)
        expected_adapter = copy.deepcopy(adapter)
        self._projection(case, adapter)
        self.assertEqual(case, expected_case)
        self.assertEqual(adapter, expected_adapter)

    def test_schema_pipeline_fingerprint_and_authority_are_locked(self):
        case = self._case()
        projection = self._projection(case)
        verification = self._verify(case, projection)
        self.assertEqual(projection["schema_version"], PROJECTION_SCHEMA_VERSION)
        self.assertEqual(projection["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            PROJECTION_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["projection_exactly_verified"])
        self.assertFalse(any(
            value
            for key, value in projection["authority"].items()
            if key != "descriptive_only"
        ))
        self.assertTrue(projection["authority"]["descriptive_only"])

    def test_production_module_has_no_runtime_or_public_consumer_imports(self):
        source = inspect.getsource(projection_module)
        for forbidden in (
            "from exchange_terminal.server",
            "import exchange_terminal.server",
            "import sqlite",
            "import requests",
            "from quant_bot",
        ):
            self.assertNotIn(forbidden, source)

    def test_public_exports_are_version_locked(self):
        self.assertEqual(
            projection_module.__all__,
            [
                "PROJECTION_SCHEMA_VERSION",
                "PROJECTION_VERIFICATION_SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "build_strategy_correlation_cluster_portfolio_risk_projection_v2",
                "verify_strategy_correlation_cluster_portfolio_risk_projection_v2",
            ],
        )


if __name__ == "__main__":
    unittest.main()
