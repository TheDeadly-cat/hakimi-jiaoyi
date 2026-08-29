"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const fixture = require("./evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js");
const receipts = require("./evidence_portfolio_risk_freshness_gate_fixture_execution_receipt_v1.js");

function projection({ localStatus = "PASS", decision, authorityTamper = false } = {}) {
  const localDecision = decision
    || "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY";
  const reduction = localDecision
    === "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED";
  const riskIncreasing = !reduction;
  const gapDetail = reduction
    ? "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION"
    : localStatus === "PASS" ? "NO_LOCAL_POLICY_GAP_OBSERVED" : "SESSION_FRESHNESS";
  return {
    schema_version: "strategy-correlation-cluster-portfolio-risk-projection-v3",
    static_fingerprint: "20260822-portfolio-risk-freshness-public-projection-lock-1",
    status: "PASS", decision: "EXACT_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED",
    source: {
      adapter_v3_schema_version: "strategy-correlation-cluster-portfolio-risk-adapter-v3",
      adapter_v3_hash: "a".repeat(64), adapter_v3_exactly_verified: true,
      lineage_binding_schema_version: "strategy-correlation-cluster-portfolio-risk-adapter-v2-session-freshness-lineage-binding-v2",
      lineage_binding_hash: "b".repeat(64), freshness_evaluation_hash: "c".repeat(64)
    },
    local_decision: {
      status: localStatus, decision: localDecision, risk_increasing: riskIncreasing,
      session_freshness_required: riskIncreasing,
      blockers: localStatus === "BLOCK" ? ["SESSION_FRESHNESS_BLOCKED"] : [],
      warnings: reduction ? ["SESSION_FRESHNESS_BLOCK_OBSERVED_RISK_REDUCTION_ONLY"] : []
    },
    stages: [
      { key: "SOURCE", state: "VERIFIED", detail: "ADAPTER_V3_EXACT_REBUILD" },
      { key: "GAP", state: localStatus === "BLOCK" ? "DECLARED" : "NONE_OBSERVED", detail: gapDetail },
      { key: "MATURITY", state: localStatus === "PASS" ? "LOCAL_POLICY_SATISFIED" : "LOCAL_POLICY_BLOCKED", detail: localDecision },
      { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY" }
    ],
    facts: {
      projection_only: true, source_document_embedded: false, positions_embedded: false,
      completed_price_rows_embedded: false, return_series_embedded: false,
      correlation_matrices_embedded: false, profitability_proven: false,
      runtime_consumer_bound: false
    },
    authority: {
      research_only: true, presentation_only: true,
      current_admission_allowed: false, current_pointer_written: false,
      formal_registry_activation_allowed: false, live_order_allowed: false,
      migration_allowed: false, paper_authorized: authorityTamper,
      runtime_gate_activation_allowed: false, shadow_consumer_activation_allowed: false,
      writer_allowed: false
    },
    projection_hash: "d".repeat(64)
  };
}

function execute(value) {
  const descriptor = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(value);
  return {
    descriptor,
    receipt: receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(value, descriptor)
  };
}

test("public versions and implementation pins are locked", () => {
  assert.equal(receipts.SCHEMA_VERSION, "portfolio-risk-freshness-fixture-execution-receipt-v1");
  for (const value of [receipts.PROJECTION_IMPLEMENTATION_SHA256,
    receipts.CARD_IMPLEMENTATION_SHA256, receipts.FIXTURE_IMPLEMENTATION_SHA256])
    assert.match(value, /^[0-9a-f]{64}$/);
});

test("fresh fixture execution produces a local pass receipt", () => {
  const { receipt } = execute(projection());
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.descriptor_exactly_rebuilt, true);
  assert.equal(receipt.verification.descriptor_contract_state, "KNOWN");
  assert.equal(receipt.authority.presentation_mount_allowed, false);
});

test("stale risk increase descriptor still verifies exactly", () => {
  const { receipt } = execute(projection({
    localStatus: "BLOCK", decision: "BLOCKED_SESSION_FRESHNESS"
  }));
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.descriptor_status, "PASS");
});

test("risk reduction descriptor still verifies exactly", () => {
  const { receipt } = execute(projection({
    decision: "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED"
  }));
  assert.equal(receipt.status, "PASS");
  assert.deepEqual(receipt.verification.stage_order,
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("descriptor tamper blocks exact receipt", () => {
  const value = projection();
  const observed = JSON.parse(JSON.stringify(
    fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(value)));
  observed.mount.performed = true;
  const receipt = receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(value, observed);
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("fixture_descriptor_exact_rebuild"));
});

test("projection authority tamper cannot produce pass receipt", () => {
  const { receipt } = execute(projection({ authorityTamper: true }));
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("known_projection_consumed"));
});

test("extra descriptor field blocks exact rebuild", () => {
  const value = projection();
  const observed = JSON.parse(JSON.stringify(
    fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(value)));
  observed.unexpected = true;
  assert.equal(
    receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(value, observed).status,
    "BLOCK"
  );
});

test("public verifier accepts exact receipt and rejects tamper", () => {
  const value = projection();
  const { descriptor, receipt } = execute(value);
  assert.equal(
    receipts.verifyPortfolioRiskFreshnessFixtureExecutionReceiptV1(
      receipt, value, descriptor).status,
    "PASS"
  );
  receipt.authority.paper_authorized = true;
  assert.equal(
    receipts.verifyPortfolioRiskFreshnessFixtureExecutionReceiptV1(
      receipt, value, descriptor).status,
    "BLOCK"
  );
});

test("receipt is deterministic and inputs are not mutated", () => {
  const value = projection();
  const descriptor = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(value);
  const before = JSON.stringify(value);
  const first = receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(value, descriptor);
  const second = receipts.buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(value, descriptor);
  assert.deepEqual(first, second);
  assert.equal(JSON.stringify(value), before);
});

test("receipt embeds no projection descriptor or markup", () => {
  const { receipt } = execute(projection());
  const text = JSON.stringify(receipt);
  for (const forbidden of ["local_decision", "presentation", "markup", "positions", "return_series"])
    assert.doesNotMatch(text, new RegExp(`\\"${forbidden}\\"`));
  assert.equal(receipt.facts.fixture_descriptor_embedded, false);
  assert.equal(receipt.facts.markup_embedded, false);
});

test("local receipt explicitly denies process authentication and browser evidence", () => {
  const { receipt } = execute(projection());
  assert.equal(receipt.facts.node_process_identity_authenticated, false);
  assert.equal(receipt.facts.receipt_signature_verified, false);
  assert.equal(receipt.facts.browser_visual_review_performed, false);
  assert.equal(receipt.authority.presentation_consumer_activation_allowed, false);
});

test("receipt contains no readiness claim", () => {
  const { receipt } = execute(projection());
  assert.doesNotMatch(JSON.stringify(receipt), /\bREADY\b/i);
});
