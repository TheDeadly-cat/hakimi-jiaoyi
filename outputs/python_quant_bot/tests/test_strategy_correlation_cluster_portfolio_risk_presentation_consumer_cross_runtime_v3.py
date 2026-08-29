from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from tests.test_strategy_correlation_cluster_portfolio_risk_projection_v3 import (
    build_projection_v3_fixture,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "exchange_terminal"
    / "static"
    / "evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js"
)


def _consume(projection):
    script = f"""
const fixture = require({json.dumps(str(FIXTURE_PATH))});
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {{
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(JSON.parse(input));
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


class PortfolioRiskPresentationConsumerCrossRuntimeV3Tests(unittest.TestCase):
    def test_fresh_projection_builds_unmounted_known_descriptor(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        descriptor = _consume(projection)
        self.assertEqual(descriptor["status"], "PASS")
        self.assertEqual(descriptor["presentation"]["contract_state"], "KNOWN")
        self.assertFalse(descriptor["mount"]["requested"])
        self.assertFalse(descriptor["mount"]["performed"])

    def test_stale_risk_increase_remains_known_gap(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z"
        )
        descriptor = _consume(projection)
        stages = descriptor["presentation"]["view_model"]["stages"]
        self.assertEqual(stages[1]["detail"], "SESSION_FRESHNESS")
        self.assertEqual(stages[2]["state"], "LOCAL_POLICY_BLOCKED")
        self.assertEqual(stages[3]["state"], "UNAUTHORIZED")

    def test_stale_reduction_exemption_remains_visible(self):
        _, _, _, _, projection = build_projection_v3_fixture(
            reference_utc="2026-12-29T00:00:00Z",
            adapter_overrides={"risk_increasing": False},
        )
        descriptor = _consume(projection)
        stages = descriptor["presentation"]["view_model"]["stages"]
        self.assertEqual(
            stages[1]["detail"],
            "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION",
        )
        self.assertEqual(stages[3]["state"], "UNAUTHORIZED")

    def test_projection_authority_tamper_fails_closed(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        tampered = copy.deepcopy(projection)
        tampered["authority"]["paper_authorized"] = True
        descriptor = _consume(tampered)
        self.assertEqual(descriptor["status"], "BLOCK")
        self.assertEqual(descriptor["presentation"]["contract_state"], "UNKNOWN")
        self.assertFalse(descriptor["mount"]["performed"])

    def test_descriptor_does_not_echo_python_projection(self):
        _, _, _, _, projection = build_projection_v3_fixture()
        descriptor = _consume(projection)
        self.assertNotIn("local_decision", descriptor)
        self.assertFalse(descriptor["facts"]["projection_document_embedded"])
        self.assertEqual(
            descriptor["source"]["projection_hash"], projection["projection_hash"]
        )


if __name__ == "__main__":
    unittest.main()
