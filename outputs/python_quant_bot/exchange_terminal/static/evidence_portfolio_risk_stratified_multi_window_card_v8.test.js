"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_stratified_multi_window_card_v8.js");
const consumer = require("./evidence_portfolio_risk_stratified_multi_window_consumer_fixture_v8.js");

const PRESENTATION_HASH = "a".repeat(64);
const PRESENTATION_V7_HASH = "b".repeat(64);
const ADAPTER_V7_HASH = "c".repeat(64);
const STABILITY_GATE_V2_HASH = "d".repeat(64);
const TRADE_IDENTITY_HASH = "e".repeat(64);
const PRESENTATION_IMPLEMENTATION_HASH =
  "f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b";
const STRICT_IMPLEMENTATION_HASH =
  "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
const HTTP_BLOCKERS = [
  "HTTP_CANDIDATE_V8_UNREGISTERED",
  "PRESENTATION_V8_CONSUMER_NOT_REGISTERED",
  "CURRENT_ADMISSION_LOCKED",
  "UI_NOT_MOUNTED",
];
const PRESENTATION_BLOCKERS = [
  "PRESENTATION_V8_CONSUMER_NOT_REGISTERED",
  "HTTP_CANDIDATE_V8_NOT_DEFINED",
  "UI_NOT_MOUNTED",
  "CURRENT_ADMISSION_LOCKED",
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
    decision: "EXACT_PRESENTATION_V8_PROJECTED_AUTHORITY_UNCHANGED",
    facts: {
      adapter_v7_exactly_verified: true,
      matrices_embedded: false,
      multi_window_summary_projected: true,
      positions_embedded: false,
      presentation_v7_exactly_verified: true,
      profitability_proven: false,
      runtime_consumer_bound: false,
      source_documents_embedded: false,
      ui_mounted: false,
      verification_contexts_embedded: false,
    },
    gaps: {
      http_candidate_blocker_count: HTTP_BLOCKERS.length,
      http_candidate_blockers: HTTP_BLOCKERS.slice(),
      local_blocker_count: blocked ? 1 : 0,
      multi_window_blocker_count: blocked ? 1 : 0,
      presentation_blocker_count: PRESENTATION_BLOCKERS.length,
      presentation_blockers: PRESENTATION_BLOCKERS.slice(),
    },
    local_decision: {
      adapter_v7_decision: blocked ? "BLOCK_MULTI_WINDOW" : "PASS_MULTI_WINDOW",
      adapter_v7_status: blocked ? "BLOCK" : "PASS",
      anchor_budget_v3_decision: "PASS_STRATIFIED_RESEARCH_BUDGET",
      anchor_budget_v3_status: "PASS",
      joint_decision: blocked ? "BLOCK_MULTI_WINDOW" : "PASS_LOCAL_RESEARCH_COMPONENTS",
      joint_status: blocked ? "BLOCK" : "PASS",
      presentation_v7_joint_decision: "PASS_LOCAL_RESEARCH_COMPONENTS",
      presentation_v7_joint_status: "PASS",
      stability_gate_v2_decision: blocked ? "BLOCK_REGISTERED_WINDOW" : "PASS_REGISTERED_WINDOWS",
      stability_gate_v2_status: blocked ? "BLOCK" : "PASS",
    },
    multi_window_summary: {
      anchor_window_id: "anchor-2026w34",
      any_registered_window_blocked: blocked,
      cluster_partition_stable: !blocked,
      minimum_conservative_weighted_effective_strata_count: "2",
      registered_window_count: 3,
      strata_topology_stable: !blocked,
      verified_window_count: 3,
      worst_window_maximum_active_stratum_gross_pct: "40",
    },
    risk_summary: {
      active_dimension_count: 1,
      conservative_weighted_effective_strata_count: "2",
      dimension_results: [{
        active_stratum_count: 2,
        dimension_id: "asset-family",
        diversification_status: blocked ? "BLOCK" : "PASS",
        dominant_stratum_id: "family-a",
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
    source: {
      adapter_v7_hash: ADAPTER_V7_HASH,
      presentation_v7_hash: PRESENTATION_V7_HASH,
      presentation_v8_hash: PRESENTATION_HASH,
      stability_gate_v2_hash: STABILITY_GATE_V2_HASH,
      state: "EXACT_PRESENTATION_V7_AND_ADAPTER_V7",
      trade_identity_hash: TRADE_IDENTITY_HASH,
    },
    stages: [
      { axis: "SOURCE", detail: "EXACT_PRESENTATION_V7_AND_ADAPTER_V7", state: "KNOWN" },
      { axis: "GAP", detail: blocked ? "LOCAL_RESEARCH_BLOCK_PRESENT" : "GOVERNANCE_GAPS_REMAIN", state: blocked ? "OPEN" : "CLEAR_WITH_GOVERNANCE_GAPS" },
      { axis: "MATURITY", detail: "UNMOUNTED_HTTP_CANDIDATE_V8", state: "CANDIDATE_ONLY" },
      { axis: "PERMISSION", detail: "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY", state: "UNAUTHORIZED" },
    ],
    status: "BLOCK",
  }, "payload_hash");
}

function response(mode = "clear") {
  if (mode === "unknown") {
    return strictCanonical.sealDocument({
      authority: authority(),
      blockers: HTTP_BLOCKERS.concat(["PRESENTATION_V8_SOURCE_UNKNOWN"]),
      facts: {
        context_contract_valid: true,
        presentation_v8_exactly_verified: false,
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
        presentation_v8_hash: null,
        presentation_v8_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
        presentation_v8_schema_version:
          "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-presentation-v8",
        presentation_v8_static_fingerprint:
          "20260823-stratified-multi-window-presentation-v8-unmounted-lock-1",
        strict_canonical_implementation_sha256: STRICT_IMPLEMENTATION_HASH,
      },
      payload: null,
      schema_version: card.RESPONSE_SCHEMA_VERSION,
      state: "UNKNOWN",
      static_fingerprint: card.RESPONSE_STATIC_FINGERPRINT,
    }, "response_hash");
  }
  const blocked = mode === "block";
  return strictCanonical.sealDocument({
    authority: authority(),
    blockers: HTTP_BLOCKERS.concat(blocked
      ? ["LOCAL_RESEARCH_GATE_BLOCKED", "MULTI_WINDOW_STABILITY_GATE_BLOCKED"]
      : []),
    facts: {
      context_contract_valid: true,
      presentation_v8_exactly_verified: true,
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
      presentation_v8_hash: PRESENTATION_HASH,
      presentation_v8_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
      presentation_v8_schema_version:
        "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-presentation-v8",
      presentation_v8_static_fingerprint:
        "20260823-stratified-multi-window-presentation-v8-unmounted-lock-1",
      strict_canonical_implementation_sha256: STRICT_IMPLEMENTATION_HASH,
    },
    payload: payload(mode),
    schema_version: card.RESPONSE_SCHEMA_VERSION,
    state: "KNOWN_BLOCKED",
    static_fingerprint: card.RESPONSE_STATIC_FINGERPRINT,
  }, "response_hash");
}

function resealResponse(altered) {
  delete altered.response_hash;
  return strictCanonical.sealDocument(altered, "response_hash");
}

test("known local clear remains outer blocked and permission neutral", () => {
  const source = response("clear");
  const view = card.buildPortfolioRiskStratifiedMultiWindowViewModelV8(source);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(source), true);
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.status_label, "LOCAL CLEAR / OUTER BLOCK");
  assert.equal(view.window.coverage, "3/3");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(Object.isFrozen(view), true);
});

test("registered-window block remains visible without authority promotion", () => {
  const view = card.buildPortfolioRiskStratifiedMultiWindowViewModelV8(response("block"));
  assert.equal(view.status_label, "LOCAL BLOCK / OUTER BLOCK");
  assert.equal(view.window.any_blocked, true);
  assert.equal(view.signals[2].state, "BLOCK PRESENT");
  assert.match(view.summary, /preregistered research component/);
});

test("exact unknown candidate hides every partial metric and signal", () => {
  const source = response("unknown");
  const view = card.buildPortfolioRiskStratifiedMultiWindowViewModelV8(source);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(source), true);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.equal(view.window, null);
  assert.deepEqual(view.metrics, []);
  assert.deepEqual(view.signals, []);
  assert.deepEqual(view.dimensions, []);
});

test("substituted response hash fails closed", () => {
  const altered = structuredClone(response("clear"));
  altered.response_hash = "0".repeat(64);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(altered), false);
  assert.equal(card.buildPortfolioRiskStratifiedMultiWindowViewModelV8(altered).contract_state, "UNKNOWN");
});

test("extra multi-window field is rejected after resealing", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.multi_window_summary.hidden_window = true;
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  const resealed = resealResponse(altered);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(resealed), false);
});

test("cross-runtime numeric floats are rejected after resealing", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.multi_window_summary.minimum_conservative_weighted_effective_strata_count = 2;
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  const resealed = resealResponse(altered);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(resealed), false);
});

test("forged authority and outer pass cannot be promoted", () => {
  const altered = structuredClone(response("clear"));
  altered.authority.paper_authorized = true;
  altered.payload.status = "PASS";
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  const resealed = resealResponse(altered);
  assert.equal(card.verifyStratifiedMultiWindowCandidateResponseV8(resealed), false);
});

test("renderer escapes adversarial anchor and dimension labels", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.multi_window_summary.anchor_window_id = '<img src=x onerror="anchor">';
  altered.payload.risk_summary.dimension_results[0].dimension_id = '<svg onload="dimension">';
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  const markup = card.renderPortfolioRiskStratifiedMultiWindowCardV8(resealResponse(altered));
  assert.doesNotMatch(markup, /<img\b|<svg\b/i);
  assert.doesNotMatch(markup, /<[^>]+\son(?:error|load)\s*=/i);
  assert.match(markup, /&lt;img/);
  assert.match(markup, /&lt;svg/);
});

test("rendered language remains neutral and explicitly outer blocked", () => {
  const markup = card.renderPortfolioRiskStratifiedMultiWindowCardV8(response("clear"));
  assert.match(markup, /LOCAL CLEAR \/ OUTER BLOCK/);
  assert.match(markup, /NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY/);
  assert.doesNotMatch(markup, /\bREADY\b|profit guaranteed|execution enabled/i);
});

test("source to permission stage order remains fixed", () => {
  const view = card.buildPortfolioRiskStratifiedMultiWindowViewModelV8(response("clear"));
  assert.deepEqual(view.stages.map((stage) => stage.axis), [
    "SOURCE", "GAP", "MATURITY", "PERMISSION",
  ]);
  assert.equal(view.stages[2].state, "CANDIDATE_ONLY");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("consumer fixture remains sealed descriptor-only and unmounted", () => {
  const source = response("clear");
  const descriptor = consumer.buildPortfolioRiskStratifiedMultiWindowConsumerFixtureV8(source);
  assert.equal(
    consumer.verifyPortfolioRiskStratifiedMultiWindowConsumerFixtureV8(descriptor, source),
    true,
  );
  assert.equal(descriptor.status, "BLOCK");
  assert.equal(descriptor.mount.mode, "UNMOUNTED");
  assert.equal(descriptor.mount.mount_api_exposed, false);
  assert.equal(descriptor.mount.browser_executed, false);
  assert.equal(descriptor.facts.local_clear_is_not_permission, true);
  assert.equal(descriptor.authority.paper_authorized, false);
  assert.equal(descriptor.authority.live_order_allowed, false);
});

test("fixture pins the stylesheet and candidate implementation without mounting", () => {
  const descriptor = consumer.buildPortfolioRiskStratifiedMultiWindowConsumerFixtureV8(
    response("clear"),
  );
  assert.equal(
    descriptor.presentation.stylesheet_asset,
    "evidence_portfolio_risk_stratified_multi_window_card_v8.css",
  );
  assert.equal(
    consumer.EXPECTED_HTTP_CANDIDATE_IMPLEMENTATION_SHA256,
    "70e2cabb54d0a9bf51973756fbe40173b142745d3a3f9d0f6f816ca759eb2770",
  );
  assert.equal(descriptor.mount.dom_target, null);
  assert.equal(descriptor.mount.selector, null);
  assert.equal(descriptor.facts.browser_visual_review_performed, false);
});
