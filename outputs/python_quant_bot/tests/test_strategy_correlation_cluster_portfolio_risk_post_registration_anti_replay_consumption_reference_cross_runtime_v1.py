from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

import tests.test_strategy_correlation_cluster_portfolio_risk_post_registration_execution_witness_cross_runtime_v2 as witness_support


ROOT = Path(__file__).resolve().parents[1]
MODULE = (
    "./exchange_terminal/static/"
    "evidence_portfolio_risk_post_registration_anti_replay_consumption_reference_v1.js"
)


NODE_SCRIPT = r"""
"use strict";
const fs = require("node:fs");
const canonical = require("./exchange_terminal/static/strict_canonical_json_v1.js");
const referenceV1 = require(inputModulePlaceholder);
const input = JSON.parse(fs.readFileSync(0, "utf8"));

function reseal(document, hashField, mutate) {
  const body = structuredClone(document);
  delete body[hashField];
  mutate(body);
  return canonical.sealDocument(body, hashField);
}

const request = referenceV1.buildAntiReplayConsumptionRequestV1(
  input.verification,
  input.exact
);
const prior = referenceV1.createAntiReplayReferenceStateV1();
const first = referenceV1.applyAntiReplayConsumptionReferenceV1(prior, request);
let result;

if (input.mode === "first") {
  result = {
    request,
    transition: first,
    exact: referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
      prior,
      request,
      first.next_state,
      first.observation
    ),
  };
} else if (input.mode === "duplicate") {
  const duplicate = referenceV1.applyAntiReplayConsumptionReferenceV1(
    first.next_state,
    request
  );
  result = { request, first, transition: duplicate };
} else if (input.mode === "conflict") {
  const other = referenceV1.buildAntiReplayConsumptionRequestV1(
    input.other_verification,
    input.other_exact
  );
  const conflictRequest = reseal(other, "request_hash", (body) => {
    body.source.anti_replay_scope_hash = request.source.anti_replay_scope_hash;
    body.source.consumption_key = request.source.consumption_key;
  });
  const conflict = referenceV1.applyAntiReplayConsumptionReferenceV1(
    first.next_state,
    conflictRequest
  );
  result = { request, first, conflict_request: conflictRequest, transition: conflict };
} else if (input.mode === "alias") {
  const alias = reseal(request, "request_hash", (body) => {
    body.schema_version = `${referenceV1.REQUEST_SCHEMA_VERSION}.0`;
  });
  result = {
    alias_valid: referenceV1.verifyAntiReplayConsumptionRequestV1(alias),
    exact: referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
      prior,
      alias,
      first.next_state,
      first.observation
    ),
  };
} else if (input.mode === "tamper-observation") {
  const observation = structuredClone(first.observation);
  observation.outcome = referenceV1.OUTCOMES.DUPLICATE;
  result = {
    exact: referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
      prior,
      request,
      first.next_state,
      observation
    ),
  };
} else {
  throw new Error(`unsupported mode: ${input.mode}`);
}

process.stdout.write(JSON.stringify(result));
""".replace("inputModulePlaceholder", json.dumps(MODULE))


class AntiReplayConsumptionReferenceCrossRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        support_type = witness_support.PostRegistrationExecutionWitnessCrossRuntimeV2Tests
        support_type.setUpClass()
        support = support_type()
        cls._bundles = {
            state: support._node(state, "valid")
            for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN")
        }

    def _node(self, state: str = "CLEAR", mode: str = "first") -> dict:
        bundle = self._bundles[state]
        other = self._bundles["TAIL_BLOCK" if state != "TAIL_BLOCK" else "CLEAR"]
        payload = {
            "exact": bundle["exact"],
            "mode": mode,
            "other_exact": other["exact"],
            "other_verification": other["verification"],
            "verification": bundle["verification"],
        }
        completed = subprocess.run(
            ["node", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(payload, sort_keys=True),
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_three_semantic_states_produce_distinct_blocked_requests(self) -> None:
        rows = [self._node(state) for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN")]
        self.assertEqual(len({row["request"]["request_hash"] for row in rows}), 3)
        for row in rows:
            self.assertEqual(row["request"]["status"], "BLOCKED")
            self.assertEqual(row["transition"]["observation"]["status"], "BLOCKED")
            self.assertEqual(row["exact"]["status"], "PASS")
            self.assertFalse(row["exact"]["atomic_nonce_consumption_verified"])
            self.assertFalse(row["exact"]["external_linearizability_verified"])

    def test_duplicate_is_rejected_without_reference_state_change(self) -> None:
        row = self._node(mode="duplicate")
        self.assertEqual(
            row["transition"]["observation"]["outcome"],
            "REFERENCE_DUPLICATE_REJECTED",
        )
        self.assertEqual(
            row["transition"]["next_state"]["state_hash"],
            row["first"]["next_state"]["state_hash"],
        )
        self.assertTrue(row["transition"]["observation"]["facts"]["duplicate_rejected"])

    def test_same_scope_different_request_is_rejected_as_conflict(self) -> None:
        row = self._node(mode="conflict")
        self.assertNotEqual(row["request"]["request_hash"], row["conflict_request"]["request_hash"])
        self.assertEqual(
            row["request"]["source"]["consumption_key"],
            row["conflict_request"]["source"]["consumption_key"],
        )
        self.assertEqual(
            row["transition"]["observation"]["outcome"],
            "REFERENCE_CONFLICT_REJECTED",
        )
        self.assertFalse(
            row["transition"]["observation"]["facts"]["external_linearizability_verified"]
        )

    def test_schema_alias_fails_closed(self) -> None:
        row = self._node(mode="alias")
        self.assertFalse(row["alias_valid"])
        self.assertEqual(row["exact"]["status"], "BLOCK")
        self.assertEqual(row["exact"]["reference_transition_status"], "UNKNOWN")

    def test_tampered_observation_fails_closed_without_authority(self) -> None:
        exact = self._node(mode="tamper-observation")["exact"]
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["current_admission_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])
        self.assertFalse(exact["target_consumption_receipt_issued"])


if __name__ == "__main__":
    unittest.main()
