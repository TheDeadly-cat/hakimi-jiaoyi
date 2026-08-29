from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import unittest

import tests.test_anti_replay_registry_ed25519_key_possession_cross_runtime_v1 as possession_support


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = r"""
"use strict";
const fs = require("node:fs");
const projectionV1 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_projection_v1.js");
const cardV1 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_card_v1.js");
const fixtureV1 = require("./exchange_terminal/static/evidence_anti_replay_registry_gap_consumer_fixture_v1.js");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const projection = projectionV1.buildAntiReplayRegistryGapProjectionV1(
  input.verification,
  input.exact
);
const fixture = fixtureV1.buildAntiReplayRegistryGapPresentationConsumerFixtureV1(
  projection
);
let candidate = fixture;
if (input.mode === "tamper-fixture") {
  candidate = structuredClone(fixture);
  candidate.facts.mounted = true;
}
const fixtureExact =
  fixtureV1.verifyAntiReplayRegistryGapPresentationConsumerFixtureV1(
    projection,
    candidate
  );
process.stdout.write(JSON.stringify({
  projection,
  view_model: cardV1.buildAntiReplayRegistryGapViewModelV1(projection),
  html: cardV1.renderAntiReplayRegistryGapCardV1(projection),
  fixture,
  fixture_exact: fixtureExact,
}));
"""


class AntiReplayRegistryGapPresentationCrossRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        support_type = (
            possession_support.AntiReplayRegistryEd25519KeyPossessionCrossRuntimeV1Tests
        )
        support_type.setUpClass()
        cls.support = support_type()
        cls.possession = cls.support._verify()

    def _node(self, mode: str = "valid") -> dict:
        completed = subprocess.run(
            ["node", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(
                {
                    "exact": self.possession["exact"],
                    "mode": mode,
                    "verification": self.possession["verification"],
                },
                sort_keys=True,
            ),
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_real_cross_runtime_possession_builds_blocked_projection(self) -> None:
        row = self._node()
        self.assertEqual(row["projection"]["status"], "BLOCKED")
        self.assertEqual(
            row["projection"]["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(row["projection"]["stages"]["source"]["state"], "HASH_BOUND")
        self.assertEqual(row["projection"]["stages"]["maturity"]["state"], "LOCAL_ONLY")

    def test_projection_exposes_seven_non_pass_external_gaps(self) -> None:
        gaps = self._node()["projection"]["stages"]["gap"]["items"]
        self.assertEqual(len(gaps), 7)
        self.assertEqual(len({gap["id"] for gap in gaps}), 7)
        self.assertTrue(all(gap["state"] != "PASS" for gap in gaps))

    def test_fixture_remains_unmounted_and_has_no_authority(self) -> None:
        row = self._node()
        fixture = row["fixture"]
        exact = row["fixture_exact"]
        self.assertEqual(fixture["status"], "UNMOUNTED")
        self.assertFalse(fixture["facts"]["mounted"])
        self.assertFalse(fixture["facts"]["route_bound"])
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["fixture_status"], "UNMOUNTED")
        self.assertFalse(exact["presentation_mount_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_html_is_neutral_and_contains_no_cryptographic_material(self) -> None:
        html = self._node()["html"]
        self.assertNotRegex(html.upper(), r"\bREADY\b")
        self.assertNotRegex(html.lower(), r"profit|return|alpha|win rate")
        self.assertIn("EVIDENCE GAP", html)
        self.assertIn("LOCAL-ONLY", html)
        for material in (
            base64.b64encode(self.support.raw_nonce).decode("ascii"),
            self.support.raw_nonce.hex(),
            base64.b64encode(self.support.signature).decode("ascii"),
            self.support.signature.hex(),
            base64.b64encode(self.support.public_key_der).decode("ascii"),
        ):
            self.assertNotIn(material, html)

    def test_fixture_tamper_becomes_block_unknown(self) -> None:
        exact = self._node("tamper-fixture")["fixture_exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["fixture_status"], "UNKNOWN")
        self.assertFalse(exact["mounted"])
        self.assertFalse(exact["presentation_mount_allowed"])


if __name__ == "__main__":
    unittest.main()
