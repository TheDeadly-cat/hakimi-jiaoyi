"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const fixture = require(
  "./evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js"
);
const receipts = require(
  "./evidence_portfolio_risk_weighted_diversification_fixture_execution_receipt_v2.js"
);

const projectRoot = path.resolve(__dirname, "..", "..");
const python = String.raw`
import json
from tests import test_strategy_correlation_cluster_portfolio_risk_projection_v4 as projection_tests
fixture=projection_tests.PortfolioRiskProjectionV4Tests(methodName='test_base_pass_projects_neutral_four_stage_shape')
fixture.setUp()
case=fixture.adapter_case._build_case(
 positions=[{'symbol':'A','notional':2200,'direction':'LONG'},{'symbol':'C','notional':200,'direction':'LONG'}],
 proposed_notional=2200,
 legacy_limits={'max_gross_exposure_pct':100.0,'max_correlated_cluster_pct':45.0},
)
print(json.dumps(fixture._build_projection(case)['projection'],sort_keys=True))
`;
const generated = spawnSync("python", ["-c", python], {
  cwd: projectRoot,
  encoding: "utf8",
  env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" }
});
if (generated.status !== 0) throw new Error(generated.stderr || "projection generation failed");
const baseProjection = JSON.parse(generated.stdout);

function projection() {
  return JSON.parse(JSON.stringify(baseProjection));
}

function execute(value) {
  const descriptor =
    fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      value
    );
  return {
    descriptor,
    receipt:
      receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
        value,
        descriptor
      )
  };
}

test("public versions and six implementation or registration pins are locked", () => {
  assert.equal(
    receipts.SCHEMA_VERSION,
    "portfolio-risk-weighted-diversification-fixture-execution-receipt-v2"
  );
  for (const value of [
    receipts.PROJECTION_IMPLEMENTATION_SHA256,
    receipts.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    receipts.CARD_IMPLEMENTATION_SHA256,
    receipts.FIXTURE_IMPLEMENTATION_SHA256,
    receipts.REGISTRATION_IMPLEMENTATION_SHA256,
    receipts.REGISTRATION_CANDIDATE_HASH
  ]) assert.match(value, /^[0-9a-f]{64}$/);
});

test("sealed concentrated fixture execution produces a local pass receipt", () => {
  const { descriptor, receipt } = execute(projection());
  assert.equal(descriptor.status, "PASS");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.projection_seal_verified, true);
  assert.equal(receipt.verification.descriptor_exactly_rebuilt, true);
  assert.equal(receipt.verification.descriptor_contract_state, "KNOWN");
  assert.equal(receipt.authority.presentation_mount_allowed, false);
});

test("valid-shape projection hash substitution blocks receipt", () => {
  const value = projection();
  assert.notEqual(value.projection_hash, "f".repeat(64));
  value.projection_hash = "f".repeat(64);
  const { receipt } = execute(value);
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("sealed_projection_consumed"));
});

test("descriptor mount tamper blocks exact receipt", () => {
  const value = projection();
  const observed = JSON.parse(JSON.stringify(
    fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      value
    )
  ));
  observed.mount.performed = true;
  const receipt =
    receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      value,
      observed
    );
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("fixture_descriptor_exact_rebuild"));
});

test("projection authority tamper cannot produce pass receipt", () => {
  const value = projection();
  value.authority.paper_authorized = true;
  const { receipt } = execute(value);
  assert.equal(receipt.status, "BLOCK");
  assert.equal(receipt.authority.paper_authorized, false);
});

test("extra descriptor field blocks exact rebuild", () => {
  const value = projection();
  const observed = JSON.parse(JSON.stringify(
    fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      value
    )
  ));
  observed.unexpected = true;
  assert.equal(
    receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      value,
      observed
    ).status,
    "BLOCK"
  );
});

test("public verifier accepts exact receipt and rejects tamper", () => {
  const value = projection();
  const { descriptor, receipt } = execute(value);
  assert.equal(
    receipts.verifyPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      receipt,
      value,
      descriptor
    ).status,
    "PASS"
  );
  receipt.authority.paper_authorized = true;
  assert.equal(
    receipts.verifyPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      receipt,
      value,
      descriptor
    ).status,
    "BLOCK"
  );
});

test("receipt is deterministic and inputs are not mutated", () => {
  const value = projection();
  const descriptor =
    fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
      value
    );
  const before = JSON.stringify(value);
  const first =
    receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      value,
      descriptor
    );
  const second =
    receipts.buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
      value,
      descriptor
    );
  assert.deepEqual(first, second);
  assert.equal(JSON.stringify(value), before);
});

test("receipt embeds no projection descriptor markup or source evidence", () => {
  const { receipt } = execute(projection());
  const serialized = JSON.stringify(receipt);
  for (const forbidden of [
    "local_decision",
    "weighted_diversification",
    "presentation",
    "markup",
    "positions",
    "return_series",
    "correlation_matrix"
  ]) assert.doesNotMatch(serialized, new RegExp(`\\"${forbidden}\\"`));
  assert.equal(receipt.facts.fixture_descriptor_embedded, false);
  assert.equal(receipt.facts.markup_embedded, false);
});

test("registration candidate identity is pinned but not activated", () => {
  const { receipt } = execute(projection());
  assert.equal(
    receipt.source.registration_schema_version,
    receipts.REGISTRATION_SCHEMA_VERSION
  );
  assert.equal(
    receipt.source.registration_candidate_hash,
    receipts.REGISTRATION_CANDIDATE_HASH
  );
  assert.equal(receipt.authority.presentation_consumer_activation_allowed, false);
});

test("local receipt denies process authentication signature browser and CSS evidence", () => {
  const { receipt } = execute(projection());
  assert.equal(receipt.facts.local_process_execution_observed, true);
  assert.equal(receipt.facts.node_process_identity_authenticated, false);
  assert.equal(receipt.facts.receipt_signature_verified, false);
  assert.equal(receipt.facts.browser_visual_review_performed, false);
  assert.equal(receipt.facts.stylesheet_executed, false);
});

test("receipt contains no promotion wording and production has no browser primitive", () => {
  const { receipt } = execute(projection());
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(JSON.stringify(receipt), promotion);
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_risk_weighted_diversification_fixture_execution_receipt_v2.js"
    ),
    "utf8"
  );
  for (const forbidden of ["document.", "window.", "fetch(", "XMLHttpRequest", "WebSocket"])
    assert.doesNotMatch(source, new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});
