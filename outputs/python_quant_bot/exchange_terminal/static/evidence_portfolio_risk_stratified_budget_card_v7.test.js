"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_stratified_budget_card_v7.js");
const consumer = require("./evidence_portfolio_risk_stratified_budget_consumer_fixture_v7.js");

const PRESENTATION_HASH = "a".repeat(64);
const PRESENTATION_IMPLEMENTATION_HASH =
  "27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38";
const STRICT_IMPLEMENTATION_HASH =
  "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
const HTTP_BLOCKERS = [
  "HTTP_CANDIDATE_V7_UNREGISTERED",
  "PRESENTATION_CONSUMER_NOT_REGISTERED",
  "CURRENT_ADMISSION_LOCKED",
  "UI_NOT_MOUNTED",
];

function authority() {
  return {
    consumer_activation_allowed: false,
    current_admission_allowed: false,
    descriptive_only: true,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    route_registration_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
  };
}

function payload(mode = "clear") {
  const blocked = mode === "block";
  return strictCanonical.sealDocument({
    authority: authority(),
    decision: "EXACT_PRESENTATION_V7_PROJECTED_AUTHORITY_UNCHANGED",
    facts: {
      budget_v3_exactly_verified: true,
      dimension_summaries_projected: true,
      matrices_embedded: false,
      positions_embedded: false,
      profitability_proven: false,
      runtime_consumer_bound: false,
      source_document_embedded: false,
      ui_mounted: false,
      v6_envelope_exactly_verified: true,
      verification_context_embedded: false,
    },
    gaps: {
      http_candidate_blocker_count: HTTP_BLOCKERS.length,
      http_candidate_blockers: HTTP_BLOCKERS.slice(),
      local_blocker_count: blocked ? 1 : 0,
      stratified_budget_blocker_count: blocked ? 1 : 0,
    },
    local_decision: {
      joint_decision: blocked
        ? "BLOCK_STRATIFIED_EFFECTIVE_BET_BUDGET"
        : "PASS_LOCAL_RESEARCH_COMPONENTS",
      joint_status: blocked ? "BLOCK" : "PASS",
      portfolio_risk_v6_decision: "PASS_LOCAL_RESEARCH_COMPONENTS",
      portfolio_risk_v6_status: "PASS",
      stratified_budget_decision: blocked ? "BLOCK_BUDGET" : "PASS_BUDGET",
      stratified_budget_status: blocked ? "BLOCK" : "PASS",
    },
    risk_summary: {
      active_dimension_count: 1,
      conservative_weighted_effective_strata_count: "2",
      dimension_results: [{
        active_stratum_count: 2,
        dimension_id: "asset-family",
        diversification_status: blocked ? "BLOCK" : "PASS",
        dominant_stratum_id: "technology",
        dominant_stratum_share_of_active_gross_pct: "50",
        gross_limit_status: blocked ? "BLOCK" : "PASS",
        maximum_stratum_gross_pct: "25",
        over_limit_stratum_count: blocked ? 1 : 0,
        status: blocked ? "BLOCK" : "PASS",
        weighted_effective_strata_count: "2",
      }],
      maximum_active_stratum_gross_pct: "25",
      total_active_gross_pct: "50",
      v2_weighted_effective_cluster_count: "2",
      weighted_diversification_gate_applied: true,
    },
    schema_version: card.PAYLOAD_SCHEMA_VERSION,
    source: { presentation_v7_hash: PRESENTATION_HASH, state: "EXACT_V6_AND_BUDGET_V3" },
    stages: [
      { axis: "SOURCE", detail: "EXACT_V6_AND_BUDGET_V3", state: "KNOWN" },
      { axis: "GAP", detail: blocked ? "LOCAL_RESEARCH_BLOCK_PRESENT" : "GOVERNANCE_GAPS_REMAIN", state: blocked ? "OPEN" : "CLEAR_WITH_GOVERNANCE_GAPS" },
      { axis: "MATURITY", detail: "UNMOUNTED_HTTP_CANDIDATE_V7", state: "CANDIDATE_ONLY" },
      { axis: "PERMISSION", detail: "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY", state: "UNAUTHORIZED" },
    ],
    status: "BLOCK",
  }, "payload_hash");
}

function response(mode = "clear") {
  if (mode === "unknown") {
    return strictCanonical.sealDocument({
      authority: authority(),
      blockers: HTTP_BLOCKERS.concat(["PRESENTATION_V7_SOURCE_UNKNOWN"]),
      facts: {
        context_contract_valid: true,
        presentation_v7_exactly_verified: false,
        profitability_proven: false,
        request_contract_valid: true,
        result_available: false,
        route_registered: false,
        runtime_mutations_performed: false,
        source_contract_known: false,
        transport_registered: false,
        ui_mounted: false,
      },
      interface_status: "UNREGISTERED_CANDIDATE",
      lineage: {
        presentation_v7_hash: null,
        presentation_v7_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
        presentation_v7_schema_version: "strategy-correlation-cluster-portfolio-risk-stratified-presentation-v7",
        presentation_v7_static_fingerprint: "20260823-stratified-portfolio-risk-presentation-v7-lock-1",
        strict_canonical_implementation_sha256: STRICT_IMPLEMENTATION_HASH,
      },
      payload: null,
      schema_version: card.RESPONSE_SCHEMA_VERSION,
      state: "UNKNOWN",
      static_fingerprint: card.RESPONSE_STATIC_FINGERPRINT,
    }, "response_hash");
  }
  return strictCanonical.sealDocument({
    authority: authority(),
    blockers: HTTP_BLOCKERS.concat(mode === "block" ? ["LOCAL_RESEARCH_GATE_BLOCKED"] : []),
    facts: {
      context_contract_valid: true,
      presentation_v7_exactly_verified: true,
      profitability_proven: false,
      request_contract_valid: true,
      result_available: true,
      route_registered: false,
      runtime_mutations_performed: false,
      source_contract_known: true,
      transport_registered: false,
      ui_mounted: false,
    },
    interface_status: "UNREGISTERED_CANDIDATE",
    lineage: {
      presentation_v7_hash: PRESENTATION_HASH,
      presentation_v7_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
      presentation_v7_schema_version: "strategy-correlation-cluster-portfolio-risk-stratified-presentation-v7",
      presentation_v7_static_fingerprint: "20260823-stratified-portfolio-risk-presentation-v7-lock-1",
      strict_canonical_implementation_sha256: STRICT_IMPLEMENTATION_HASH,
    },
    payload: payload(mode),
    schema_version: card.RESPONSE_SCHEMA_VERSION,
    state: "KNOWN_BLOCKED",
    static_fingerprint: card.RESPONSE_STATIC_FINGERPRINT,
  }, "response_hash");
}

test("known local clear stays bounded and unauthorized", () => {
  const source = response("clear");
  const view = card.buildPortfolioRiskStratifiedBudgetViewModelV7(source);
  assert.equal(card.verifyStratifiedBudgetCandidateResponseV7(source), true);
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.status_label, "LOCAL CLEAR");
  assert.equal(view.metrics[1].value, "2");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(Object.isFrozen(view), true);
});

test("budget block remains visible above a clear v6 component", () => {
  const view = card.buildPortfolioRiskStratifiedBudgetViewModelV7(response("block"));
  assert.equal(view.status_label, "LOCAL BLOCK");
  assert.equal(view.dimensions[0].status, "BLOCK");
  assert.match(view.summary, /preregistered stratum/);
});

test("exact unknown candidate hides every partial metric", () => {
  const source = response("unknown");
  const view = card.buildPortfolioRiskStratifiedBudgetViewModelV7(source);
  assert.equal(card.verifyStratifiedBudgetCandidateResponseV7(source), true);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.deepEqual(view.metrics, []);
  assert.deepEqual(view.dimensions, []);
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("substituted response hash fails closed", () => {
  const altered = structuredClone(response("clear"));
  altered.response_hash = "0".repeat(64);
  assert.equal(card.verifyStratifiedBudgetCandidateResponseV7(altered), false);
  assert.equal(card.buildPortfolioRiskStratifiedBudgetViewModelV7(altered).contract_state, "UNKNOWN");
});

test("extra payload field is rejected even after resealing", () => {
  const altered = structuredClone(response("clear"));
  const payloadDocument = { ...altered.payload, hidden_permission: true };
  delete payloadDocument.payload_hash;
  altered.payload = strictCanonical.sealDocument(payloadDocument, "payload_hash");
  delete altered.response_hash;
  const resealed = strictCanonical.sealDocument(altered, "response_hash");
  assert.equal(card.verifyStratifiedBudgetCandidateResponseV7(resealed), false);
});

test("forged authority and outer pass cannot be promoted", () => {
  const altered = structuredClone(response("clear"));
  altered.authority.paper_authorized = true;
  altered.payload.status = "PASS";
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  delete altered.response_hash;
  const resealed = strictCanonical.sealDocument(altered, "response_hash");
  assert.equal(card.verifyStratifiedBudgetCandidateResponseV7(resealed), false);
});

test("renderer escapes adversarial dimension labels", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.risk_summary.dimension_results[0].dimension_id = '<img src=x onerror="boom">';
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  delete altered.response_hash;
  const resealed = strictCanonical.sealDocument(altered, "response_hash");
  const markup = card.renderPortfolioRiskStratifiedBudgetCardV7(resealed);
  assert.doesNotMatch(markup, /<img\b|onerror\s*=\s*["']/i);
  assert.match(markup, /&lt;img/);
});

test("consumer fixture remains sealed and unmounted", () => {
  const source = response("clear");
  const descriptor = consumer.buildPortfolioRiskStratifiedBudgetConsumerFixtureV7(source);
  assert.equal(consumer.verifyPortfolioRiskStratifiedBudgetConsumerFixtureV7(descriptor, source), true);
  assert.equal(descriptor.status, "BLOCK");
  assert.equal(descriptor.mount.mode, "UNMOUNTED");
  assert.equal(descriptor.mount.browser_executed, false);
  assert.equal(descriptor.facts.local_clear_is_not_permission, true);
  assert.equal(descriptor.authority.paper_authorized, false);
  assert.equal(descriptor.authority.live_order_allowed, false);
});
