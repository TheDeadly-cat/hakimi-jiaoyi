"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const card = require("./evidence_portfolio_risk_freshness_gate_card_v3.js");

function fixture({ status = "PASS", decision, gapState, gapDetail } = {}) {
  const localDecision = decision
    || "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY";
  const localStatus = status;
  const riskIncreasing = localDecision
    !== "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED";
  const defaultGapState = localStatus === "PASS" ? "NONE_OBSERVED" : "DECLARED";
  const defaultGapDetail = localStatus === "PASS"
    ? (riskIncreasing ? "NO_LOCAL_POLICY_GAP_OBSERVED" : "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION")
    : "SESSION_FRESHNESS";
  return {
    schema_version: card.PROJECTION_SCHEMA_VERSION,
    static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
    status: "PASS",
    decision: "EXACT_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED",
    source: {
      adapter_v3_schema_version: "strategy-correlation-cluster-portfolio-risk-adapter-v3",
      adapter_v3_hash: "a".repeat(64),
      adapter_v3_exactly_verified: true,
      lineage_binding_schema_version: "strategy-correlation-cluster-portfolio-risk-adapter-v2-session-freshness-lineage-binding-v2",
      lineage_binding_hash: "b".repeat(64),
      freshness_evaluation_hash: "c".repeat(64)
    },
    local_decision: {
      status: localStatus,
      decision: localDecision,
      risk_increasing: riskIncreasing,
      session_freshness_required: riskIncreasing,
      blockers: localStatus === "BLOCK" ? ["SESSION_FRESHNESS_BLOCKED"] : [],
      warnings: riskIncreasing ? [] : ["SESSION_FRESHNESS_BLOCK_OBSERVED_RISK_REDUCTION_ONLY"]
    },
    stages: [
      { key: "SOURCE", state: "VERIFIED", detail: "ADAPTER_V3_EXACT_REBUILD" },
      { key: "GAP", state: gapState || defaultGapState, detail: gapDetail || defaultGapDetail },
      { key: "MATURITY", state: localStatus === "PASS" ? "LOCAL_POLICY_SATISFIED" : "LOCAL_POLICY_BLOCKED", detail: localDecision },
      { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY" }
    ],
    facts: {
      projection_only: true,
      source_document_embedded: false,
      positions_embedded: false,
      completed_price_rows_embedded: false,
      return_series_embedded: false,
      correlation_matrices_embedded: false,
      profitability_proven: false,
      runtime_consumer_bound: false
    },
    authority: {
      research_only: true,
      presentation_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false
    },
    projection_hash: "d".repeat(64)
  };
}

test("exports are version locked", () => {
  assert.equal(card.CARD_SCHEMA_VERSION, "portfolio-risk-freshness-gate-card-v3");
  assert.deepEqual(card.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("fresh local pass produces a known neutral model", () => {
  const model = card.buildPortfolioRiskFreshnessGateViewModelV3(fixture());
  assert.equal(model.contract_state, "KNOWN");
  assert.equal(model.stages[2].state, "LOCAL_POLICY_SATISFIED");
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

test("stale risk increase preserves the declared gap", () => {
  const model = card.buildPortfolioRiskFreshnessGateViewModelV3(fixture({
    status: "BLOCK", decision: "BLOCKED_SESSION_FRESHNESS"
  }));
  assert.equal(model.contract_state, "KNOWN");
  assert.equal(model.stages[1].detail, "SESSION_FRESHNESS");
  assert.equal(model.stages[2].state, "LOCAL_POLICY_BLOCKED");
});

test("risk reduction exception is explicit and unauthorized", () => {
  const model = card.buildPortfolioRiskFreshnessGateViewModelV3(fixture({
    decision: "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED"
  }));
  assert.equal(model.stages[1].detail, "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION");
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

for (const [name, mutate] of [
  ["schema drift", (x) => { x.schema_version = "legacy"; }],
  ["extra field", (x) => { x.extra = true; }],
  ["stage reorder", (x) => { x.stages.reverse(); }],
  ["authority promotion", (x) => { x.authority.paper_authorized = true; }],
  ["boolean type alias", (x) => { x.local_decision.risk_increasing = 1; }],
  ["hash shape drift", (x) => { x.projection_hash = "short"; }],
  ["maturity mismatch", (x) => { x.stages[2].state = "LOCAL_POLICY_BLOCKED"; }],
  ["permission promotion", (x) => { x.stages[3].state = "AUTHORIZED"; }]
]) {
  test(`${name} fails closed`, () => {
    const value = fixture();
    mutate(value);
    const model = card.buildPortfolioRiskFreshnessGateViewModelV3(value);
    assert.equal(model.contract_state, "UNKNOWN");
    assert.equal(model.stages[3].state, "UNAUTHORIZED");
  });
}

test("renderer escapes projected text", () => {
  const value = fixture({ status: "BLOCK", decision: "BLOCKED_SESSION_FRESHNESS" });
  value.local_decision.blockers = ["<script>alert(1)</script>"];
  const html = card.renderPortfolioRiskFreshnessGateCardV3(value);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /data-contract-state="KNOWN"/);
});

test("rendered card contains no readiness claim", () => {
  const html = card.renderPortfolioRiskFreshnessGateCardV3(fixture());
  assert.doesNotMatch(html, /\bREADY\b/i);
  assert.match(html, /UNAUTHORIZED/);
});

test("malformed input renders unknown and unauthorized", () => {
  const html = card.renderPortfolioRiskFreshnessGateCardV3(null);
  assert.match(html, /data-contract-state="UNKNOWN"/);
  assert.match(html, /UNAUTHORIZED/);
});
