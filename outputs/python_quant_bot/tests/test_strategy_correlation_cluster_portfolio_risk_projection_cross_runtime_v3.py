from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from tests.test_strategy_correlation_cluster_portfolio_risk_projection_v3 import (
    build_projection_v3_fixture,
)


CARD_PATH = (
    Path(__file__).resolve().parents[1]
    / "exchange_terminal"
    / "static"
    / "evidence_portfolio_risk_freshness_gate_card_v3.js"
)


def _node_view_model(projection):
    script = f"""
const card = require({json.dumps(str(CARD_PATH))});
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {{
  process.stdout.write(JSON.stringify(card.buildPortfolioRiskFreshnessGateViewModelV3(JSON.parse(input))));
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


class PortfolioRiskProjectionCrossRuntimeV3Tests(unittest.TestCase):
    def test_fresh_python_projection_is_known_to_node_consumer(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        model = _node_view_model(projection)
        self.assertEqual(model["contract_state"], "KNOWN")
        self.assertEqual(model["stages"][2]["state"], "LOCAL_POLICY_SATISFIED")
        self.assertEqual(model["stages"][3]["state"], "UNAUTHORIZED")

    def test_stale_python_projection_preserves_declared_gap(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z"
        )
        model = _node_view_model(projection)
        self.assertEqual(model["contract_state"], "KNOWN")
        self.assertEqual(model["stages"][1]["detail"], "SESSION_FRESHNESS")
        self.assertEqual(model["stages"][2]["state"], "LOCAL_POLICY_BLOCKED")

    def test_reduction_exemption_crosses_runtime_without_permission(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z",
            adapter_overrides={"risk_increasing": False},
        )
        model = _node_view_model(projection)
        self.assertEqual(
            model["stages"][1]["detail"],
            "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION",
        )
        self.assertEqual(model["stages"][3]["state"], "UNAUTHORIZED")

    def test_authority_tamper_fails_closed_in_node(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        tampered = copy.deepcopy(projection)
        tampered["authority"]["paper_authorized"] = True
        model = _node_view_model(tampered)
        self.assertEqual(model["contract_state"], "UNKNOWN")
        self.assertEqual(model["stages"][3]["state"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
