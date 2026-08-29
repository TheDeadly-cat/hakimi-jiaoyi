from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_projection_v6 as projection_test_support


class PortfolioRiskPresentationConsumerCrossRuntimeV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.case = projection_test_support.PortfolioRiskProjectionV6Tests(
            "test_exact_local_clear_projects_blocked_frontend_authority"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def _projection(
        self,
        *,
        coupled: bool = False,
        observations: list[dict[str, object]] | None = None,
    ) -> dict:
        if not coupled and observations is None:
            return copy.deepcopy(self.case.projection)
        candidate, context = self.case._bundle(
            coupled=coupled,
            observations=observations,
        )
        return self.case._project(candidate, context)

    def _node(self, projection: dict) -> dict:
        script = r"""
const fs = require('node:fs');
const card = require('./exchange_terminal/static/evidence_portfolio_risk_downside_tail_card_v6.js');
const consumer = require('./exchange_terminal/static/evidence_portfolio_risk_downside_tail_consumer_fixture_v6.js');
const projection = JSON.parse(fs.readFileSync(0, 'utf8'));
const view = card.buildPortfolioRiskDownsideTailViewModelV6(projection);
const markup = card.renderPortfolioRiskDownsideTailCardV6(projection);
const descriptor = consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(projection);
process.stdout.write(JSON.stringify({
  seal_verified: card.verifyPortfolioRiskProjectionSealV6(projection),
  view,
  markup,
  descriptor,
  descriptor_verified: consumer.verifyPortfolioRiskDownsideTailPresentationConsumerFixtureV6(descriptor, projection),
  expected_projection_implementation_sha256: consumer.EXPECTED_PROJECTION_IMPLEMENTATION_SHA256
}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(projection, separators=(",", ":"), sort_keys=True),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_python_clear_projection_builds_bounded_unauthorized_node_view(
        self,
    ) -> None:
        result = self._node(self._projection())
        self.assertTrue(result["seal_verified"])
        self.assertEqual(result["view"]["contract_state"], "KNOWN_BLOCKED")
        self.assertEqual(result["view"]["tone"], "bounded")
        self.assertEqual(result["view"]["status_label"], "LOCAL CHECKS CLEAR")
        self.assertEqual(result["view"]["stages"][3]["state"], "UNAUTHORIZED")
        self.assertTrue(result["descriptor_verified"])

    def test_python_tail_block_projects_critical_node_semantics(self) -> None:
        result = self._node(self._projection(coupled=True))
        self.assertEqual(result["view"]["tone"], "critical")
        self.assertEqual(result["view"]["status_label"], "TAIL COUPLING BLOCK")
        self.assertEqual(result["view"]["tail_risk"]["decision"], "BLOCK")
        self.assertTrue(
            result["descriptor"]["facts"]["downside_tail_block_visible"]
        )
        self.assertFalse(
            result["descriptor"]["authority"]["presentation_mount_allowed"]
        )

    def test_exact_unknown_python_source_stays_known_fail_closed_in_node(
        self,
    ) -> None:
        result = self._node(self._projection(observations=[]))
        self.assertTrue(result["seal_verified"])
        self.assertEqual(result["view"]["contract_state"], "KNOWN_BLOCKED")
        self.assertEqual(result["view"]["source_state"], "UNKNOWN")
        self.assertTrue(
            result["descriptor"]["facts"]["exact_unknown_source_presented"]
        )
        self.assertEqual(result["view"]["stages"][3]["state"], "UNAUTHORIZED")

    def test_resealed_python_authority_promotion_fails_closed_in_node(
        self,
    ) -> None:
        projection = self._projection()
        projection["authority"]["paper_authorized"] = True
        projection = seal_strict_canonical_document(
            projection, "projection_hash"
        )
        result = self._node(projection)
        self.assertEqual(result["view"]["contract_state"], "UNKNOWN")
        self.assertFalse(result["descriptor"]["facts"]["projection_v6_accepted"])
        self.assertEqual(result["descriptor"]["mount"]["mode"], "UNMOUNTED")

    def test_resealed_projection_v5_schema_is_rejected_by_v6_consumer(
        self,
    ) -> None:
        projection = self._projection()
        projection["schema_version"] = (
            "strategy-correlation-cluster-portfolio-risk-projection-v5"
        )
        projection = seal_strict_canonical_document(
            projection, "projection_hash"
        )
        result = self._node(projection)
        self.assertFalse(result["seal_verified"])
        self.assertEqual(result["view"]["contract_state"], "UNKNOWN")

    def test_resealed_untrusted_text_is_not_reflected_into_markup(self) -> None:
        projection = self._projection()
        projection["local_decision"]["downside_tail_gate_reason"] = (
            '<img src=x onerror="DO-NOT-RUN">'
        )
        projection = seal_strict_canonical_document(
            projection, "projection_hash"
        )
        result = self._node(projection)
        self.assertEqual(result["view"]["contract_state"], "UNKNOWN")
        self.assertNotIn("DO-NOT-RUN", result["markup"])
        self.assertNotIn("<img", result["markup"])

    def test_descriptor_declares_scoped_css_without_runtime_or_visual_claim(
        self,
    ) -> None:
        result = self._node(self._projection())
        descriptor = result["descriptor"]
        self.assertEqual(
            descriptor["presentation"]["stylesheet_asset"],
            "evidence_portfolio_risk_downside_tail_card_v6.css",
        )
        self.assertFalse(descriptor["facts"]["runtime_assets_accessed"])
        self.assertFalse(descriptor["facts"]["dom_accessed"])
        self.assertFalse(
            descriptor["facts"]["browser_visual_review_performed"]
        )
        self.assertFalse(descriptor["facts"]["profitability_proven"])

    def test_node_projection_pin_matches_python_source_and_no_promotion_wording(
        self,
    ) -> None:
        projection_path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_projection_v6.py"
        )
        result = self._node(self._projection())
        self.assertEqual(
            result["expected_projection_implementation_sha256"],
            hashlib.sha256(projection_path.read_bytes()).hexdigest(),
        )
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("READY", encoded)


if __name__ == "__main__":
    unittest.main()
