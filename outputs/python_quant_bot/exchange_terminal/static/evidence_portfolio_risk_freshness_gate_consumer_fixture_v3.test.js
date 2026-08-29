"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const fixture = require("./evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js");

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
    status: "PASS",
    decision: "EXACT_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED",
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

test("public API is narrow and version locked", () => {
  assert.equal(fixture.SCHEMA_VERSION, "portfolio-risk-freshness-presentation-consumer-fixture-v3");
  assert.deepEqual(Object.keys(fixture).sort(), [
    "EXPECTED_CARD_SCHEMA_VERSION", "EXPECTED_CARD_STATIC_FINGERPRINT",
    "EXPECTED_PROJECTION_SCHEMA_VERSION", "SCHEMA_VERSION", "STAGE_ORDER",
    "STATIC_FINGERPRINT", "buildPortfolioRiskFreshnessPresentationConsumerFixtureV3"
  ]);
  assert.equal(fixture.mount, undefined);
});

test("fresh projection produces a known unmounted descriptor", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection());
  assert.equal(result.status, "PASS");
  assert.equal(result.presentation.contract_state, "KNOWN");
  assert.equal(result.presentation.view_model.stages[2].state, "LOCAL_POLICY_SATISFIED");
  assert.deepEqual(result.mount, {
    requested: false, performed: false, target_kind: "NONE", selector: null,
    dom_accessed: false, browser_review_performed: false
  });
});

test("stale risk increase remains known but locally blocked", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(
    projection({ localStatus: "BLOCK", decision: "BLOCKED_SESSION_FRESHNESS" })
  );
  assert.equal(result.status, "PASS");
  assert.equal(result.presentation.view_model.stages[1].detail, "SESSION_FRESHNESS");
  assert.equal(result.presentation.view_model.stages[2].state, "LOCAL_POLICY_BLOCKED");
  assert.equal(result.presentation.view_model.stages[3].state, "UNAUTHORIZED");
});

test("risk reduction exception remains visible and unauthorized", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(
    projection({ decision: "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED" })
  );
  assert.equal(result.presentation.view_model.stages[1].detail, "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION");
  assert.equal(result.presentation.view_model.stages[3].state, "UNAUTHORIZED");
});

test("authority tamper becomes unknown without mount", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(
    projection({ authorityTamper: true })
  );
  assert.equal(result.status, "BLOCK");
  assert.equal(result.presentation.contract_state, "UNKNOWN");
  assert.equal(result.presentation.view_model.stages[3].state, "UNAUTHORIZED");
  assert.equal(result.mount.performed, false);
});

test("malformed input becomes a safe descriptor", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(null);
  assert.equal(result.status, "BLOCK");
  assert.match(result.presentation.markup, /UNKNOWN/);
  assert.match(result.presentation.markup, /UNAUTHORIZED/);
});

test("projection input is not mutated", () => {
  const input = projection();
  const before = JSON.stringify(input);
  fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(input);
  assert.equal(JSON.stringify(input), before);
});

test("descriptor is deeply immutable", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection());
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.presentation), true);
  assert.equal(Object.isFrozen(result.presentation.view_model.stages), true);
  assert.throws(() => { result.mount.performed = true; }, TypeError);
});

test("descriptor embeds presentation summary but not source evidence", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection());
  const text = JSON.stringify(result);
  for (const forbidden of ["positions", "completed_price_rows", "return_series", "correlation_matrix"])
    assert.doesNotMatch(text, new RegExp(`\\"${forbidden}\\"`));
  assert.equal(result.facts.projection_document_embedded, false);
  assert.equal(result.facts.source_evidence_embedded, false);
});

test("render descriptor contains no readiness or permission promotion", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection());
  assert.doesNotMatch(result.presentation.markup, /\bREADY\b/i);
  assert.match(result.presentation.markup, /UNAUTHORIZED/);
  assert.equal(result.authority.presentation_consumer_activation_allowed, false);
});

test("production fixture has no DOM network or mount primitives", () => {
  const source = fs.readFileSync(path.join(__dirname,
    "evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js"), "utf8");
  for (const forbidden of ["document.", "window.", "querySelector", "innerHTML", "appendChild", "replaceChildren", "fetch(", "XMLHttpRequest", "WebSocket"])
    assert.doesNotMatch(source, new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});

test("stage order remains source gap maturity permission", () => {
  const result = fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection());
  assert.deepEqual(result.presentation.stage_order, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});
