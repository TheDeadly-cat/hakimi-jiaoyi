from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests.test_strategy_correlation_cluster_portfolio_risk_projection_v2 import (
    StrategyCorrelationClusterPortfolioRiskProjectionV2Tests,
)


class StrategyCorrelationClusterPortfolioRiskProjectionCrossRuntimeV2Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which("node")
        cls.card_path = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "static"
            / "evidence_portfolio_risk_temporal_lattice_card_v2.js"
        )

    def _projection(self, *, stable=True):
        fixture = StrategyCorrelationClusterPortfolioRiskProjectionV2Tests(
            methodName="runTest"
        )
        fixture.setUp()
        case = fixture._case(stable=stable)
        return fixture._projection(case)

    def _node_view(self, projection):
        if self.node is None:
            self.skipTest("node is unavailable")
        script = (
            "const fs=require('node:fs');"
            "const card=require(process.argv[1]);"
            "const payload=JSON.parse(fs.readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify("
            "card.buildPortfolioRiskTemporalLatticeViewModel(payload)));"
        )
        completed = subprocess.run(
            [self.node, "-e", script, str(self.card_path)],
            input=json.dumps(projection, sort_keys=True, separators=(",", ":")),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_python_stable_projection_binds_to_node_view_model(self):
        view = self._node_view(self._projection(stable=True))
        self.assertTrue(view["validContract"])
        self.assertEqual(view["sourceState"], "VERIFIED")
        self.assertEqual(
            view["gapState"],
            "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY",
        )
        self.assertEqual(view["permissionState"], "UNAUTHORIZED")
        self.assertEqual(view["metrics"]["symbolTickets"], 3)
        self.assertEqual(view["metrics"]["effectiveBets"], 2)
        self.assertEqual(view["metrics"]["correlatedDuplicates"], 1)
        self.assertEqual(view["stability"]["status"], "PASS")

    def test_python_unstable_projection_binds_to_temporal_gap(self):
        view = self._node_view(self._projection(stable=False))
        self.assertTrue(view["validContract"])
        self.assertEqual(view["gapState"], "TEMPORAL_STABILITY_GAP_PRESENT")
        self.assertEqual(view["stability"]["status"], "BLOCK")
        self.assertGreater(view["stability"]["unstableWindows"], 0)
        self.assertEqual(view["permissionState"], "UNAUTHORIZED")

    def test_node_fails_closed_on_python_projection_authority_tamper(self):
        projection = self._projection(stable=True)
        tampered = copy.deepcopy(projection)
        tampered["authority"]["current_admission_allowed"] = True
        view = self._node_view(tampered)
        self.assertFalse(view["validContract"])
        self.assertEqual(view["sourceState"], "UNKNOWN")
        self.assertEqual(view["gapState"], "UNKNOWN")
        self.assertEqual(view["permissionState"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
