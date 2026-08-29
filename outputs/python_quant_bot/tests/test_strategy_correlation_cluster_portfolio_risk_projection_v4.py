from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_projection_v4 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v4 import (
    PortfolioRiskAdapterV4Tests,
)


class PortfolioRiskProjectionV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.adapter_case = PortfolioRiskAdapterV4Tests(
            methodName="test_base_fresh_case_passes_joint_weighted_candidate"
        )
        self.adapter_case.setUp()
        self.base = self._build_projection(self.adapter_case.base)

    @staticmethod
    def _adapter_context(case: dict) -> dict:
        return {
            "adapter_v3_document": case["adapter_v3_document"],
            "weighted_budget_v2_document": case["weighted_document"],
            "adapter_v3_verification_context": case["adapter_v3_context"],
            "weighted_budget_v2_verification_context": case[
                "weighted_context"
            ],
        }

    def _build_projection(self, case: dict) -> dict:
        adapter_document = self.adapter_case._evaluate(case)
        context = self._adapter_context(case)
        with self.adapter_case.v3_case.chain.fixture.source_verifiers():
            projection = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v4(
                adapter_document,
                adapter_v4_verification_context=context,
            )
        return {
            "case": case,
            "adapter_document": adapter_document,
            "context": context,
            "projection": projection,
        }

    def test_base_pass_projects_neutral_four_stage_shape(self) -> None:
        projection = self.base["projection"]
        self.assertEqual(projection["status"], "PASS")
        self.assertEqual(
            [stage["key"] for stage in projection["stages"]],
            list(subject.STAGE_ORDER),
        )
        self.assertEqual(projection["stages"][1]["state"], "NONE_OBSERVED")
        self.assertEqual(
            projection["stages"][2]["state"], "LOCAL_POLICY_SATISFIED"
        )
        self.assertEqual(projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_weighted_gap_is_declared_with_metrics(self) -> None:
        case = self.adapter_case._build_case(
            positions=[
                {"symbol": "A", "notional": 2_200, "direction": "LONG"},
                {"symbol": "C", "notional": 200, "direction": "LONG"},
            ],
            proposed_notional=2_200,
            legacy_limits={
                "max_gross_exposure_pct": 100.0,
                "max_correlated_cluster_pct": 45.0,
            },
        )
        projection = self._build_projection(case)["projection"]
        weighted = projection["weighted_diversification"]
        self.assertEqual(projection["status"], "PASS")
        self.assertEqual(projection["local_decision"]["status"], "BLOCK")
        self.assertEqual(projection["stages"][1]["detail"], "WEIGHTED_CLUSTER_DIVERSIFICATION")
        self.assertEqual(weighted["assessment"], "CONCENTRATED")
        self.assertEqual(weighted["unweighted_effective_cluster_count"], 2)
        self.assertEqual(weighted["weighted_effective_cluster_count"], 1.090722)
        self.assertEqual(
            weighted["dominant_cluster_share_of_active_gross_pct"], 95.6522
        )

    def test_balanced_weighted_case_projects_sufficient(self) -> None:
        case = self.adapter_case._build_case(
            positions=[
                {"symbol": "A", "notional": 1_250, "direction": "LONG"},
                {"symbol": "C", "notional": 2_500, "direction": "LONG"},
            ],
            proposed_notional=1_250,
            legacy_limits={
                "max_gross_exposure_pct": 100.0,
                "max_correlated_cluster_pct": 45.0,
            },
        )
        projection = self._build_projection(case)["projection"]
        self.assertEqual(
            projection["weighted_diversification"]["assessment"], "SUFFICIENT"
        )
        self.assertEqual(
            projection["weighted_diversification"][
                "weighted_effective_cluster_count"
            ],
            2.0,
        )

    def test_risk_reduction_projects_not_applicable_and_unauthorized(self) -> None:
        case = self.adapter_case._build_case(risk_increasing=False)
        projection = self._build_projection(case)["projection"]
        weighted = projection["weighted_diversification"]
        self.assertEqual(weighted["assessment"], "NOT_APPLICABLE")
        self.assertIsNone(weighted["weighted_effective_cluster_count"])
        self.assertEqual(
            projection["stages"][1]["detail"],
            "VERIFIED_RISK_REDUCTION_WEIGHTED_EXEMPTION",
        )
        self.assertEqual(projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_adapter_v3_component_block_projects_upstream_gap(self) -> None:
        case = self.adapter_case._build_case(proposed_notional=5_000)
        projection = self._build_projection(case)["projection"]
        self.assertEqual(projection["local_decision"]["status"], "BLOCK")
        self.assertEqual(projection["stages"][1]["detail"], "ADAPTER_V3_COMPONENT")
        self.assertEqual(
            projection["weighted_diversification"]["assessment"],
            "UPSTREAM_BLOCKED",
        )

    def test_context_splice_projects_unknown_and_unauthorized(self) -> None:
        context = copy.deepcopy(self.base["context"])
        context["weighted_budget_v2_verification_context"]["positions"] = []
        with self.adapter_case.v3_case.chain.fixture.source_verifiers():
            projection = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v4(
                self.base["adapter_document"],
                adapter_v4_verification_context=context,
            )
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(projection["source"]["adapter_v4_exactly_verified"], False)
        self.assertEqual(projection["stages"][0]["state"], "UNKNOWN")
        self.assertEqual(projection["stages"][3]["state"], "UNAUTHORIZED")

    def test_adapter_tamper_projects_unknown(self) -> None:
        tampered = copy.deepcopy(self.base["adapter_document"])
        tampered["authority"]["current_admission_allowed"] = True
        with self.adapter_case.v3_case.chain.fixture.source_verifiers():
            projection = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v4(
                tampered,
                adapter_v4_verification_context=self.base["context"],
            )
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(
            projection["weighted_diversification"]["assessment"], "UNKNOWN"
        )

    def test_exact_verifier_rejects_resealed_stage_metric_and_authority_tamper(self) -> None:
        projection = self.base["projection"]
        with self.adapter_case.v3_case.chain.fixture.source_verifiers():
            receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v4(
                projection,
                self.base["adapter_document"],
                adapter_v4_verification_context=self.base["context"],
            )
        self.assertEqual(receipt["status"], "PASS")
        variants = []
        stage = copy.deepcopy(projection)
        stage["stages"][1]["detail"] = "UNKNOWN"
        variants.append(stage)
        metric = copy.deepcopy(projection)
        metric["weighted_diversification"]["weighted_effective_cluster_count"] = 99.0
        variants.append(metric)
        authority = copy.deepcopy(projection)
        authority["authority"]["current_admission_allowed"] = True
        variants.append(authority)
        for value in variants:
            with self.subTest(value=value):
                resealed = seal_strict_canonical_document(value, "projection_hash")
                with self.adapter_case.v3_case.chain.fixture.source_verifiers():
                    receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_projection_v4(
                        resealed,
                        self.base["adapter_document"],
                        adapter_v4_verification_context=self.base["context"],
                    )
                self.assertEqual(receipt["status"], "BLOCK")
                self.assertEqual(receipt["projection_status"], "UNKNOWN")

    def test_projection_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        snapshot = copy.deepcopy(self.base)
        with self.adapter_case.v3_case.chain.fixture.source_verifiers():
            second = subject.project_strategy_correlation_cluster_portfolio_risk_projection_v4(
                self.base["adapter_document"],
                adapter_v4_verification_context=self.base["context"],
            )
        self.assertEqual(second, self.base["projection"])
        self.assertEqual(self.base, snapshot)

    def test_projection_is_summary_only(self) -> None:
        encoded = json.dumps(self.base["projection"], sort_keys=True)
        for forbidden in (
            '"positions"',
            '"cluster_exposures"',
            '"correlation_matrix"',
            '"adapter_v4_document"',
            '"verification_context"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            self.base["projection"]["facts"]["source_document_embedded"]
        )

    def test_projection_authority_and_profitability_remain_locked(self) -> None:
        projection = self.base["projection"]
        self.assertTrue(projection["authority"]["research_only"])
        self.assertTrue(projection["authority"]["presentation_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in projection["authority"].items()
                if key not in {"research_only", "presentation_only"}
            )
        )
        self.assertFalse(projection["facts"]["profitability_proven"])
        self.assertFalse(projection["facts"]["ui_mounted"])

    def test_adapter_v4_implementation_pin_matches_current_file(self) -> None:
        path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_adapter_v4.py"
        )
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.ADAPTER_V4_IMPLEMENTATION_SHA256,
        )

    def test_api_has_no_runtime_mount_or_execution_inputs(self) -> None:
        parameters = set(
            inspect.signature(
                subject.project_strategy_correlation_cluster_portfolio_risk_projection_v4
            ).parameters
        )
        self.assertTrue(
            parameters.isdisjoint(
                {"runtime", "database", "cache", "current", "mount", "order", "broker"}
            )
        )
        source = inspect.getsource(subject)
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        self.assertNotIn(forbidden, json.dumps(self.base["projection"]).upper())


if __name__ == "__main__":
    unittest.main()
