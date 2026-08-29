from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v1 import (
    PROJECTION_SCHEMA_VERSION,
    PROJECTION_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_projection_v1,
    verify_strategy_correlation_cluster_portfolio_risk_projection_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_complete_link import (
    StrategyCorrelationClusterCompleteLinkTests,
)


class StrategyCorrelationClusterPortfolioRiskProjectionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        preregistration = (
            StrategyCorrelationClusterCompleteLinkTests._preregistration()
        )
        cluster_matrix = StrategyCorrelationClusterCompleteLinkTests._matrix(ac=0.92)
        complete_link_audit = build_correlation_cluster_complete_link_audit(
            preregistration,
            cluster_matrix,
        )
        self.base_inputs = {
            "preregistration": preregistration,
            "cluster_correlation_matrix": cluster_matrix,
            "complete_link_audit": complete_link_audit,
            "equity": 10_000,
            "positions": [
                {"symbol": "B", "notional": 1_800, "direction": "LONG"},
                {"symbol": "C", "notional": 1_800, "direction": "LONG"},
            ],
            "proposed_symbol": "D",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "legacy_correlations": {
                "pairs": {"B|D": 0.10, "C|D": 0.10}
            },
        }

    @staticmethod
    def _positional(inputs):
        return [
            inputs.pop("preregistration"),
            inputs.pop("cluster_correlation_matrix"),
            inputs.pop("complete_link_audit"),
        ]

    def _adapter(self, **overrides):
        inputs = copy.deepcopy(self.base_inputs)
        inputs.update(copy.deepcopy(overrides))
        keyword = copy.deepcopy(inputs)
        positional = self._positional(keyword)
        document = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            *positional,
            **keyword,
        )
        return document, inputs

    def _projection(self, adapter_document, inputs):
        keyword = copy.deepcopy(inputs)
        positional = self._positional(keyword)
        return build_strategy_correlation_cluster_portfolio_risk_projection_v1(
            adapter_document,
            *positional,
            **keyword,
        )

    def _verify(self, projection, adapter_document, inputs):
        keyword = copy.deepcopy(inputs)
        positional = self._positional(keyword)
        return verify_strategy_correlation_cluster_portfolio_risk_projection_v1(
            projection,
            adapter_document,
            *positional,
            **keyword,
        )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskProjectionV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskProjectionV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_not_supplied_is_explicit_and_fail_closed(self):
        projection = self._projection(None, self.base_inputs)
        self.assertEqual(projection["status"], "NOT_SUPPLIED")
        self.assertEqual(
            [item["state"] for item in projection["pipeline"]],
            ["NOT_SUPPLIED", "NOT_SUPPLIED", "UNMOUNTED_CANDIDATE", "UNAUTHORIZED"],
        )
        self.assertEqual(projection["summary"]["adapter_decision"], "NOT_SUPPLIED")
        self.assertIsNone(projection["summary"]["symbol_ticket_count"])

    def test_verified_joint_pass_is_observed_not_ready(self):
        adapter, inputs = self._adapter()
        projection = self._projection(adapter, inputs)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(projection["pipeline"][0]["state"], "VERIFIED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "WITHIN_DECLARED_RESEARCH_LIMITS",
        )
        self.assertEqual(projection["summary"]["symbol_ticket_count"], 3)
        self.assertEqual(
            projection["summary"]["effective_independent_bet_count"], 2
        )
        self.assertEqual(projection["summary"]["correlated_duplicate_ticket_count"], 1)

    def test_verified_block_exposes_gap_without_authority(self):
        adapter, inputs = self._adapter(
            positions=[
                {"symbol": "B", "notional": 2_500, "direction": "LONG"},
                {"symbol": "C", "notional": 2_500, "direction": "LONG"},
            ]
        )
        projection = self._projection(adapter, inputs)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "RESEARCH_LIMIT_GAP_PRESENT",
        )
        self.assertEqual(
            projection["summary"]["all_cluster_max_gross_exposure_pct"], 50.0
        )
        self.assertGreater(projection["summary"]["blocker_count"], 0)
        self.assertEqual(projection["pipeline"][3]["state"], "UNAUTHORIZED")

    def test_resealed_adapter_tamper_projects_unknown(self):
        adapter, inputs = self._adapter()
        tampered = copy.deepcopy(adapter)
        tampered["decision"] = "READY"
        tampered = seal_strict_canonical_document(tampered, "adapter_hash")
        projection = self._projection(tampered, inputs)
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertEqual(projection["pipeline"][0]["state"], "UNKNOWN")
        self.assertEqual(projection["summary"]["adapter_decision"], "UNKNOWN")
        self.assertIsNone(projection["source"]["adapter_hash"])

    def test_non_mapping_adapter_projects_unknown_without_echo(self):
        projection = self._projection("claimed-pass", self.base_inputs)
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertNotIn("claimed-pass", str(projection))

    def test_risk_reduction_has_distinct_gap_state_without_cluster_sources(self):
        adapter, inputs = self._adapter(
            preregistration=None,
            cluster_correlation_matrix=None,
            complete_link_audit=None,
            equity=0,
            positions=[],
            proposed_symbol="",
            proposed_notional=0,
            legacy_correlations=None,
            risk_increasing=False,
        )
        projection = self._projection(adapter, inputs)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(projection["pipeline"][1]["state"], "RISK_REDUCTION_PATH")
        self.assertIs(projection["summary"]["risk_increasing"], False)

    def test_projection_verifier_rejects_resealed_value_and_type_tampering(self):
        adapter, inputs = self._adapter()
        projection = self._projection(adapter, inputs)
        self.assertEqual(self._verify(projection, adapter, inputs)["status"], "PASS")
        variants = []
        permission_tamper = copy.deepcopy(projection)
        permission_tamper["authority"]["paper_authorized"] = True
        variants.append(permission_tamper)
        type_tamper = copy.deepcopy(projection)
        type_tamper["summary"]["symbol_ticket_count"] = 3.0
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(
                    tampered,
                    "projection_hash",
                )
                verification = self._verify(resealed, adapter, inputs)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["projection_status"], "UNKNOWN")

    def test_projection_redacts_raw_sources_and_component_documents(self):
        adapter, inputs = self._adapter()
        projection = self._projection(adapter, inputs)
        keys = self._all_keys(projection)
        for forbidden in (
            "pair_results",
            "pearson_correlation",
            "return_series",
            "clusters",
            "checks",
            "cluster_exposures",
        ):
            self.assertNotIn(forbidden, keys)
        self.assertFalse(projection["facts"]["source_documents_embedded"])
        self.assertFalse(projection["facts"]["raw_correlations_embedded"])

    def test_inputs_and_adapter_are_not_mutated(self):
        adapter, inputs = self._adapter()
        expected_adapter = copy.deepcopy(adapter)
        expected_inputs = copy.deepcopy(inputs)
        self._projection(adapter, inputs)
        self.assertEqual(adapter, expected_adapter)
        self.assertEqual(inputs, expected_inputs)

    def test_schema_pipeline_fingerprint_and_authority_are_locked(self):
        adapter, inputs = self._adapter()
        projection = self._projection(adapter, inputs)
        verification = self._verify(projection, adapter, inputs)
        self.assertEqual(projection["schema_version"], PROJECTION_SCHEMA_VERSION)
        self.assertEqual(projection["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            PROJECTION_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            [item["stage"] for item in projection["pipeline"]],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(projection["authority"]["descriptive_only"])
        for key, value in projection["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(projection["facts"]["profitability_proof"])
        self.assertFalse(projection["facts"]["runtime_consumer_mounted"])


if __name__ == "__main__":
    unittest.main()
