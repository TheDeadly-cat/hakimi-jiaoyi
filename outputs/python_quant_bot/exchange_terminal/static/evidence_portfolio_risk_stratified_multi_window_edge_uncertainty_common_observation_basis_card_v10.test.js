"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require(
  "./evidence_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_card_v10.js"
);
const consumer = require(
  "./evidence_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_consumer_fixture_v10.js"
);

const HASHES = {
  presentation: "a".repeat(64),
  presentationV9: "b".repeat(64),
  adapterV9: "c".repeat(64),
  edgeGate: "d".repeat(64),
  basisGate: "e".repeat(64),
  basisEvidence: "f".repeat(64),
  basisPreregistration: "1".repeat(64),
  partition: "2".repeat(64),
  commonSet: "3".repeat(64),
  policy: "4".repeat(64),
  trade: "5".repeat(64),
};
const PRESENTATION_IMPLEMENTATION_HASH =
  "85a317babc16b310b9c62639879a241b0bf206d33a4be460a8d98400fb71c22e";
const STRICT_IMPLEMENTATION_HASH =
  "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
const HTTP_BLOCKERS = [
  "HTTP_CANDIDATE_V10_UNREGISTERED",
  "PRESENTATION_V10_CONSUMER_NOT_REGISTERED",
  "CURRENT_ADMISSION_LOCKED",
  "UI_NOT_MOUNTED",
];
const PRESENTATION_BLOCKERS = [
  "PRESENTATION_V10_CONSUMER_NOT_REGISTERED",
  "HTTP_CANDIDATE_V10_NOT_DEFINED",
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
  const basisBlocked = mode === "basis-block";
  const edgeBlocked = mode === "edge-block";
  const locallyBlocked = basisBlocked || edgeBlocked;
  return strictCanonical.sealDocument({
    authority: authority(),
    common_observation_summary: {
      all_pair_sample_counts_match: !basisBlocked,
      common_sample_count: basisBlocked ? 20 : 800,
      edge_pair_count: 2,
      minimum_common_sample_count: 30,
      pair_count_matching_common_sample_count: basisBlocked ? 1 : 2,
      provenance_declaration_only: true,
      raw_samples_recomputed: false,
    },
    decision: "EXACT_PRESENTATION_V10_PROJECTED_AUTHORITY_UNCHANGED",
    edge_uncertainty_summary: {
      blocked_pair_count: edgeBlocked ? 1 : 0,
      cluster_partition_hash: HASHES.partition,
      confidence_z_micros: 1644854,
      correlation_floor_micros: 700000,
      insufficient_sample_pair_count: edgeBlocked ? 1 : 0,
      maximum_confidence_upper_correlation_micros: edgeBlocked ? 1000000 : 682384,
      observed_breach_pair_count: 0,
      uncertainty_overlap_pair_count: edgeBlocked ? 1 : 0,
      verified_pair_count: 2,
    },
    facts: {
      adapter_v9_exactly_verified: true,
      common_observation_basis_projected: true,
      edge_uncertainty_summary_projected: true,
      matrices_embedded: false,
      multi_window_summary_projected: true,
      positions_embedded: false,
      presentation_v9_exactly_verified: true,
      profitability_proven: false,
      provenance_declaration_only: true,
      raw_samples_recomputed: false,
      runtime_consumer_bound: false,
      source_documents_embedded: false,
      ui_mounted: false,
      verification_contexts_embedded: false,
    },
    gaps: {
      adapter_v9_blocker_count: locallyBlocked ? 1 : 0,
      common_observation_basis_blocker_count: basisBlocked ? 1 : 0,
      http_candidate_blocker_count: HTTP_BLOCKERS.length,
      http_candidate_blockers: HTTP_BLOCKERS.slice(),
      local_blocker_count: locallyBlocked ? 1 : 0,
      presentation_blocker_count: PRESENTATION_BLOCKERS.length,
      presentation_blockers: PRESENTATION_BLOCKERS.slice(),
    },
    local_decision: {
      adapter_v8_decision: edgeBlocked ? "BLOCK_EDGE_UNCERTAINTY" : "PASS_EDGE_UNCERTAINTY",
      adapter_v8_status: edgeBlocked ? "BLOCK" : "PASS",
      adapter_v9_decision: locallyBlocked ? "BLOCK_COMMON_OBSERVATION_ADAPTER_V9" : "PASS_COMMON_OBSERVATION_ADAPTER_V9",
      adapter_v9_status: locallyBlocked ? "BLOCK" : "PASS",
      common_observation_basis_gate_v1_decision: basisBlocked ? "BLOCK_COMMON_OBSERVATION_BASIS" : "PASS_COMMON_OBSERVATION_BASIS_PROVENANCE",
      common_observation_basis_gate_v1_status: basisBlocked ? "BLOCK" : "PASS",
      edge_gate_v1_decision: edgeBlocked ? "BLOCK_EDGE_UNCERTAINTY" : "PASS_EDGE_UNCERTAINTY",
      edge_gate_v1_status: edgeBlocked ? "BLOCK" : "PASS",
      joint_decision: locallyBlocked ? "BLOCK_LOCAL_RESEARCH" : "PASS_COMMON_OBSERVATION_BASIS_LOCAL_RESEARCH_PRESENTATION_V10",
      joint_status: locallyBlocked ? "BLOCK" : "PASS",
      presentation_v9_joint_decision: edgeBlocked ? "BLOCK_EDGE_UNCERTAINTY" : "PASS_EDGE_UNCERTAINTY_LOCAL_RESEARCH",
      presentation_v9_joint_status: edgeBlocked ? "BLOCK" : "PASS",
    },
    multi_window_summary: {
      anchor_window_id: "anchor-2026w34",
      any_registered_window_blocked: false,
      cluster_partition_stable: true,
      minimum_conservative_weighted_effective_strata_count: "2",
      registered_window_count: 3,
      strata_topology_stable: true,
      verified_window_count: 3,
      worst_window_maximum_active_stratum_gross_pct: "40",
    },
    risk_summary: {
      active_dimension_count: 1,
      conservative_weighted_effective_strata_count: "2",
      dimension_results: [{
        active_stratum_count: 2,
        dimension_id: "asset-family",
        diversification_status: "PASS",
        dominant_stratum_id: "family-a",
        dominant_stratum_share_of_active_gross_pct: "50",
        gross_limit_status: "PASS",
        maximum_stratum_gross_pct: "25",
        over_limit_stratum_count: 0,
        status: "PASS",
        weighted_effective_strata_count: "2",
      }],
      maximum_active_stratum_gross_pct: "25",
      total_active_gross_pct: "50",
      v2_weighted_effective_cluster_count: "2",
      weighted_diversification_gate_applied: true,
    },
    schema_version: card.PAYLOAD_SCHEMA_VERSION,
    source: {
      adapter_v9_hash: HASHES.adapterV9,
      basis_evidence_hash: HASHES.basisEvidence,
      basis_preregistration_hash: HASHES.basisPreregistration,
      cluster_partition_hash: HASHES.partition,
      common_observation_basis_gate_v1_hash: HASHES.basisGate,
      common_sample_set_hash: HASHES.commonSet,
      edge_gate_v1_hash: HASHES.edgeGate,
      observation_policy_hash: HASHES.policy,
      presentation_v10_hash: HASHES.presentation,
      presentation_v9_hash: HASHES.presentationV9,
      state: "EXACT_PRESENTATION_V9_AND_ADAPTER_V9",
      trade_identity_hash: HASHES.trade,
    },
    stages: [
      { axis: "SOURCE", detail: "EXACT_PRESENTATION_V9_AND_ADAPTER_V9", state: "KNOWN" },
      { axis: "GAP", detail: locallyBlocked ? "LOCAL_RESEARCH_BLOCK_PRESENT" : "LOCAL_RESEARCH_CLEAR_GOVERNANCE_GAPS_REMAIN", state: locallyBlocked ? "OPEN" : "CLEAR_WITH_GOVERNANCE_GAPS" },
      { axis: "MATURITY", detail: "UNMOUNTED_HTTP_CANDIDATE_V10", state: "CANDIDATE_ONLY" },
      { axis: "PERMISSION", detail: "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY", state: "UNAUTHORIZED" },
    ],
    status: "BLOCK",
  }, "payload_hash");
}

function response(mode = "clear") {
  if (mode === "unknown") {
    return strictCanonical.sealDocument({
      authority: authority(),
      blockers: HTTP_BLOCKERS.concat(["PRESENTATION_V10_SOURCE_UNKNOWN"]),
      facts: {
        context_contract_valid: true,
        presentation_v10_exactly_verified: false,
        profitability_proven: false,
        provenance_declaration_only: true,
        raw_samples_recomputed: false,
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
        presentation_v10_hash: null,
        presentation_v10_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
        presentation_v10_schema_version:
          "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-uncertainty-common-observation-basis-presentation-v10",
        presentation_v10_static_fingerprint:
          "20260823-stratified-multi-window-edge-uncertainty-common-observation-basis-presentation-v10-unmounted-lock-1",
        strict_canonical_implementation_sha256: STRICT_IMPLEMENTATION_HASH,
      },
      payload: null,
      schema_version: card.RESPONSE_SCHEMA_VERSION,
      state: "UNKNOWN",
      static_fingerprint: card.RESPONSE_STATIC_FINGERPRINT,
    }, "response_hash");
  }
  const blockers = HTTP_BLOCKERS.slice();
  if (mode === "basis-block") blockers.push("COMMON_OBSERVATION_BASIS_GATE_BLOCKED", "LOCAL_RESEARCH_GATE_BLOCKED");
  if (mode === "edge-block") blockers.push("CROSS_CLUSTER_EDGE_UNCERTAINTY_GATE_BLOCKED", "LOCAL_RESEARCH_GATE_BLOCKED");
  return strictCanonical.sealDocument({
    authority: authority(),
    blockers,
    facts: {
      context_contract_valid: true,
      presentation_v10_exactly_verified: true,
      profitability_proven: false,
      provenance_declaration_only: true,
      raw_samples_recomputed: false,
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
      presentation_v10_hash: HASHES.presentation,
      presentation_v10_implementation_sha256: PRESENTATION_IMPLEMENTATION_HASH,
      presentation_v10_schema_version:
        "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-uncertainty-common-observation-basis-presentation-v10",
      presentation_v10_static_fingerprint:
        "20260823-stratified-multi-window-edge-uncertainty-common-observation-basis-presentation-v10-unmounted-lock-1",
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

function resealPayloadAndResponse(altered) {
  delete altered.payload.payload_hash;
  altered.payload = strictCanonical.sealDocument(altered.payload, "payload_hash");
  return resealResponse(altered);
}

test("known basis clear remains outer blocked and declaration explicit", () => {
  const source = response("clear");
  const view = card.buildViewModelV10(source);
  assert.equal(card.verifyCandidateResponseV10(source), true);
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.status_label, "LOCAL CLEAR / OUTER BLOCK");
  assert.equal(view.common.sample_count, 800);
  assert.equal(view.common.provenance_declaration_only, true);
  assert.equal(view.common.raw_samples_recomputed, false);
  assert.equal(Object.isFrozen(view), true);
});

test("common-observation basis block remains visible without authority promotion", () => {
  const view = card.buildViewModelV10(response("basis-block"));
  assert.equal(view.status_label, "LOCAL BLOCK / OUTER BLOCK");
  assert.equal(view.common.blocked, true);
  assert.equal(view.signals[0].state, "BASIS BLOCK");
  assert.match(view.summary, /not counted as independent evidence/);
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("edge uncertainty block survives the added observation layer", () => {
  const view = card.buildViewModelV10(response("edge-block"));
  assert.equal(view.status_label, "LOCAL BLOCK / OUTER BLOCK");
  assert.equal(view.edge.blocked, true);
  assert.equal(view.signals[3].state, "BLOCK PRESENT");
});

test("unknown candidate hides every partial aggregate", () => {
  const source = response("unknown");
  const view = card.buildViewModelV10(source);
  assert.equal(card.verifyCandidateResponseV10(source), true);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.equal(view.common, null);
  assert.equal(view.edge, null);
  assert.equal(view.window, null);
  assert.deepEqual(view.metrics, []);
  assert.deepEqual(view.signals, []);
  assert.deepEqual(view.dimensions, []);
});

test("substituted response hash fails closed", () => {
  const altered = structuredClone(response("clear"));
  altered.response_hash = "0".repeat(64);
  assert.equal(card.verifyCandidateResponseV10(altered), false);
  assert.equal(card.buildViewModelV10(altered).contract_state, "UNKNOWN");
});

test("extra common-observation field is rejected after resealing", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.common_observation_summary.hidden_samples = true;
  assert.equal(card.verifyCandidateResponseV10(resealPayloadAndResponse(altered)), false);
});

test("impossible pair-count agreement is rejected", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.common_observation_summary.pair_count_matching_common_sample_count = 1;
  assert.equal(card.verifyCandidateResponseV10(resealPayloadAndResponse(altered)), false);
});

test("raw-sample recomputation and provenance promotion are rejected", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.common_observation_summary.raw_samples_recomputed = true;
  altered.payload.facts.raw_samples_recomputed = true;
  assert.equal(card.verifyCandidateResponseV10(resealPayloadAndResponse(altered)), false);
});

test("forged authority and payload pass cannot be promoted", () => {
  const altered = structuredClone(response("clear"));
  altered.authority.paper_authorized = true;
  altered.payload.status = "PASS";
  assert.equal(card.verifyCandidateResponseV10(resealPayloadAndResponse(altered)), false);
});

test("renderer escapes adversarial dimension labels", () => {
  const altered = structuredClone(response("clear"));
  altered.payload.risk_summary.dimension_results[0].dimension_id = '<svg onload="dimension">';
  altered.payload.risk_summary.dimension_results[0].dominant_stratum_id = '<img src=x onerror="dominant">';
  const markup = card.renderCardV10(resealPayloadAndResponse(altered));
  assert.doesNotMatch(markup, /<svg\b|<img\b/i);
  assert.doesNotMatch(markup, /<[^>]+\son(?:load|error)\s*=/i);
  assert.match(markup, /&lt;svg/);
  assert.match(markup, /&lt;img/);
});

test("language and stage order stay neutral and fail closed", () => {
  const source = response("clear");
  const view = card.buildViewModelV10(source);
  const markup = card.renderCardV10(source);
  assert.deepEqual(view.stages.map((stage) => stage.axis), [
    "SOURCE", "GAP", "MATURITY", "PERMISSION",
  ]);
  assert.match(markup, /DECLARATION ONLY/);
  assert.match(markup, /RAW SAMPLES NOT RECOMPUTED/);
  assert.match(markup, /LOCAL CLEAR \/ OUTER BLOCK/);
  assert.match(markup, /NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY/);
  assert.doesNotMatch(markup, /\bREADY\b|profit guaranteed|execution enabled/i);
});

test("consumer fixture is sealed, pinned, descriptor-only, and unmounted", () => {
  const source = response("clear");
  const descriptor = consumer.buildConsumerFixtureV10(source);
  assert.equal(consumer.verifyConsumerFixtureV10(descriptor, source), true);
  assert.equal(descriptor.status, "BLOCK");
  assert.equal(descriptor.mount.mode, "UNMOUNTED");
  assert.equal(descriptor.mount.mount_api_exposed, false);
  assert.equal(descriptor.mount.browser_executed, false);
  assert.equal(descriptor.facts.common_observation_summary_visible, true);
  assert.equal(descriptor.facts.provenance_declaration_only, true);
  assert.equal(descriptor.facts.raw_samples_recomputed, false);
  assert.equal(descriptor.authority.paper_authorized, false);
  assert.equal(descriptor.authority.live_order_allowed, false);
  assert.equal(
    descriptor.presentation.stylesheet_asset,
    "evidence_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_card_v10.css"
  );
  assert.equal(
    consumer.EXPECTED_HTTP_CANDIDATE_IMPLEMENTATION_SHA256,
    "771e1737ef51f1e3a1fcb008908c926ab98e75b9847be0fa04232163025ea0f5"
  );
  assert.equal(descriptor.mount.dom_target, null);
  assert.equal(descriptor.mount.selector, null);
  assert.equal(descriptor.facts.browser_visual_review_performed, false);
});
