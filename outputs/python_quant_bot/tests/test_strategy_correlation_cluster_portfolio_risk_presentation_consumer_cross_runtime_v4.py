from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v4 import (
    project_strategy_correlation_cluster_portfolio_risk_projection_v4,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_projection_v4
    as projection_v4_tests,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "exchange_terminal"
    / "static"
    / "evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js"
)


def _consume(projection):
    script = f"""
const fixture = require({json.dumps(str(FIXTURE_PATH))});
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {{
  const result = fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(JSON.parse(input));
  process.stdout.write(JSON.stringify(result));
}});
"""
    completed = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(projection, sort_keys=True),
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(completed.stdout)


class PortfolioRiskPresentationConsumerCrossRuntimeV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projection_case = projection_v4_tests.PortfolioRiskProjectionV4Tests(
            methodName="test_base_pass_projects_neutral_four_stage_shape"
        )
        cls.projection_case.setUp()

    def _build(self, **overrides):
        case = self.projection_case.adapter_case._build_case(**overrides)
        return self.projection_case._build_projection(case)

    def test_concentrated_projection_builds_known_unmounted_descriptor(self):
        bundle = self._build(
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
        descriptor = _consume(bundle["projection"])
        model = descriptor["presentation"]["view_model"]
        self.assertEqual(descriptor["status"], "PASS")
        self.assertEqual(descriptor["presentation"]["contract_state"], "KNOWN")
        self.assertEqual(model["stages"][1]["detail"], "WEIGHTED_CLUSTER_DIVERSIFICATION")
        self.assertEqual(model["stages"][2]["state"], "LOCAL_POLICY_BLOCKED")
        self.assertEqual(model["stages"][3]["state"], "UNAUTHORIZED")
        self.assertIn("1.09", descriptor["presentation"]["markup"])
        self.assertFalse(descriptor["mount"]["requested"])
        self.assertFalse(descriptor["mount"]["performed"])

    def test_balanced_projection_remains_known_and_neutral(self):
        bundle = self._build()
        descriptor = _consume(bundle["projection"])
        stages = descriptor["presentation"]["view_model"]["stages"]
        self.assertEqual(descriptor["status"], "PASS")
        self.assertEqual(stages[1]["state"], "NONE_OBSERVED")
        self.assertEqual(stages[2]["state"], "LOCAL_POLICY_SATISFIED")
        self.assertEqual(stages[3]["state"], "UNAUTHORIZED")

    def test_risk_reduction_exception_remains_explicit(self):
        bundle = self._build(risk_increasing=False)
        descriptor = _consume(bundle["projection"])
        stages = descriptor["presentation"]["view_model"]["stages"]
        self.assertEqual(descriptor["status"], "PASS")
        self.assertEqual(
            stages[1]["detail"],
            "VERIFIED_RISK_REDUCTION_WEIGHTED_EXEMPTION",
        )
        self.assertEqual(stages[3]["state"], "UNAUTHORIZED")

    def test_upstream_adapter_block_remains_known(self):
        bundle = self._build(proposed_notional=5_000)
        descriptor = _consume(bundle["projection"])
        stages = descriptor["presentation"]["view_model"]["stages"]
        self.assertEqual(descriptor["status"], "PASS")
        self.assertEqual(stages[1]["detail"], "ADAPTER_V3_COMPONENT")
        self.assertEqual(stages[2]["state"], "LOCAL_POLICY_BLOCKED")
        self.assertEqual(stages[3]["state"], "UNAUTHORIZED")

    def test_projection_authority_tamper_fails_closed(self):
        bundle = self._build()
        tampered = copy.deepcopy(bundle["projection"])
        tampered["authority"]["paper_authorized"] = True
        descriptor = _consume(tampered)
        self.assertEqual(descriptor["status"], "BLOCK")
        self.assertEqual(descriptor["presentation"]["contract_state"], "UNKNOWN")
        self.assertEqual(
            descriptor["presentation"]["view_model"]["stages"][3]["state"],
            "UNAUTHORIZED",
        )
        self.assertFalse(descriptor["mount"]["performed"])

    def test_valid_shape_projection_hash_substitution_fails_closed(self):
        bundle = self._build()
        tampered = copy.deepcopy(bundle["projection"])
        self.assertNotEqual(tampered["projection_hash"], "f" * 64)
        tampered["projection_hash"] = "f" * 64
        descriptor = _consume(tampered)
        self.assertEqual(descriptor["status"], "BLOCK")
        self.assertEqual(descriptor["presentation"]["contract_state"], "UNKNOWN")
        self.assertIsNone(descriptor["source"]["projection_hash"])
        self.assertFalse(descriptor["mount"]["performed"])

    def test_projection_context_splice_fails_closed(self):
        bundle = self._build()
        context = copy.deepcopy(bundle["context"])
        context["weighted_budget_v2_verification_context"]["positions"] = []
        with self.projection_case.adapter_case.v3_case.chain.fixture.source_verifiers():
            projection = (
                project_strategy_correlation_cluster_portfolio_risk_projection_v4(
                    bundle["adapter_document"],
                    adapter_v4_verification_context=context,
                )
            )
        descriptor = _consume(projection)
        self.assertEqual(projection["status"], "BLOCK")
        self.assertEqual(descriptor["status"], "BLOCK")
        self.assertEqual(descriptor["source"]["projection_schema_version"], "UNKNOWN")
        self.assertEqual(
            descriptor["presentation"]["view_model"]["stages"][3]["state"],
            "UNAUTHORIZED",
        )

    def test_descriptor_does_not_echo_projection_or_source_evidence(self):
        bundle = self._build()
        descriptor = _consume(bundle["projection"])
        serialized = json.dumps(descriptor, sort_keys=True)
        for forbidden in (
            '"local_decision"',
            '"weighted_diversification"',
            '"positions"',
            '"return_series"',
            '"correlation_matrix"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(descriptor["facts"]["projection_document_embedded"])
        self.assertFalse(descriptor["facts"]["source_evidence_embedded"])
        self.assertEqual(
            descriptor["source"]["projection_hash"],
            bundle["projection"]["projection_hash"],
        )

    def test_cross_runtime_descriptor_is_deterministic(self):
        bundle = self._build()
        first = _consume(bundle["projection"])
        second = _consume(bundle["projection"])
        self.assertEqual(first, second)
        self.assertFalse(
            first["source"]["implementation_hashes_runtime_verified"]
        )
        self.assertFalse(
            first["authority"]["presentation_consumer_activation_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
