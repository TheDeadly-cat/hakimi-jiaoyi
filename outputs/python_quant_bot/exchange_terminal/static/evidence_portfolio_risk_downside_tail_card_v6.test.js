"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_downside_tail_card_v6.js");
const consumer = require("./evidence_portfolio_risk_downside_tail_consumer_fixture_v6.js");

const HASHES = Object.freeze({
  candidate: "a".repeat(64),
  envelope: "b".repeat(64),
  adapter: "c".repeat(64),
});
const HTTP_BLOCKERS = Object.freeze([
  "HTTP_CANDIDATE_V6_UNREGISTERED",
  "PRESENTATION_CONSUMER_NOT_REGISTERED",
  "CURRENT_ADMISSION_LOCKED",
]);

function authority() {
  return {
    research_only: true,
    presentation_only: true,
    frontend_projection_only: true,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    formal_registry_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function buildProjection(mode = "clear") {
  const sourceKnown = mode !== "unknown";
  const tailBlocked = mode === "tail-block";
  const localStatus = sourceKnown ? (tailBlocked ? "BLOCK" : "PASS") : "UNKNOWN";
  const localDecision = sourceKnown
    ? tailBlocked
      ? "BLOCK_DOWNSIDE_TAIL_COUPLING"
      : "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE"
    : "UNKNOWN";
  const localBlockers = tailBlocked
    ? ["downside_tail_coupling_detected"]
    : sourceKnown
      ? []
      : ["downside_tail_source_observed"];
  const candidateBlockers = HTTP_BLOCKERS.concat(
    sourceKnown
      ? tailBlocked
        ? ["LOCAL_RESEARCH_GATE_BLOCKED"]
        : []
      : ["JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN"]
  );
  const projection = {
    schema_version: card.PROJECTION_SCHEMA_VERSION,
    static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
    status: "BLOCK",
    decision: "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED",
    axis_order: card.STAGE_ORDER.slice(),
    source: {
      state: sourceKnown ? "OBSERVED" : "UNKNOWN",
      candidate_v6_schema_version:
        "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v6",
      candidate_v6_static_fingerprint:
        "20260823-adapter-v6-envelope-first-http-unregistered-candidate-1",
      candidate_v6_response_hash: HASHES.candidate,
      candidate_v6_implementation_sha256:
        "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096",
      candidate_state: "KNOWN_BLOCKED",
      presentation_envelope_v1_hash: HASHES.envelope,
      adapter_v6_hash: HASHES.adapter,
      strict_canonical_implementation_sha256:
        "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412",
    },
    local_decision: {
      status: localStatus,
      decision: localDecision,
      adapter_v5_status: sourceKnown ? "PASS" : "UNKNOWN",
      downside_tail_source_state: sourceKnown ? "OBSERVED" : "UNKNOWN",
      downside_tail_gate_decision: sourceKnown
        ? tailBlocked
          ? "BLOCK"
          : "PASS"
        : "UNKNOWN",
      downside_tail_gate_reason: sourceKnown
        ? tailBlocked
          ? "DOWNSIDE_TAIL_COUPLING_DETECTED"
          : "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
        : "UNKNOWN",
      risk_increasing: sourceKnown ? true : null,
    },
    gaps: {
      local_blocker_count: localBlockers.length,
      local_blockers: localBlockers,
      http_candidate_blocker_count: HTTP_BLOCKERS.length,
      http_candidate_blockers: HTTP_BLOCKERS.slice(),
      candidate_blockers: candidateBlockers,
    },
    stages: [
      {
        axis: "SOURCE",
        state: sourceKnown ? "OBSERVED" : "UNKNOWN",
        detail: sourceKnown
          ? "EXACT_ADAPTER_V6_AND_DOWNSIDE_TAIL_SOURCE_BOUND"
          : "EXACT_ADAPTER_V6_WITH_UNKNOWN_JOINT_SOURCE",
      },
      {
        axis: "GAP",
        state: sourceKnown ? (tailBlocked ? "BLOCKED" : "PRESENT") : "UNKNOWN",
        detail: sourceKnown
          ? tailBlocked
            ? "LOCAL_RESEARCH_GATE_BLOCKED"
            : "HTTP_REGISTRATION_CONSUMER_AND_CURRENT_GAPS"
          : "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN",
      },
      {
        axis: "MATURITY",
        state: "CANDIDATE_ONLY",
        detail: "UNMOUNTED_HTTP_CANDIDATE_V6",
      },
      {
        axis: "PERMISSION",
        state: "UNAUTHORIZED",
        detail: "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
      },
    ],
    facts: {
      candidate_v6_exactly_verified: true,
      presentation_envelope_v1_bound: true,
      adapter_v6_exactly_verified: true,
      joint_local_research_source_known: sourceKnown,
      trade_symbol_set_tail_identity_set_cross_bound: sourceKnown,
      downside_tail_block_override_visible: true,
      risk_reduction_joint_exemption_implemented: false,
      projection_only: true,
      source_document_embedded: false,
      verification_context_embedded: false,
      positions_embedded: false,
      aligned_observations_embedded: false,
      pair_results_embedded: false,
      runtime_consumer_bound: false,
      ui_mounted: false,
      profitability_proven: false,
    },
    authority: authority(),
  };
  return strictCanonical.sealDocument(projection, "projection_hash");
}

test("exact clear projection builds a bounded unauthorized view", () => {
  const projection = buildProjection("clear");
  const view = card.buildPortfolioRiskDownsideTailViewModelV6(projection);
  assert.equal(card.verifyPortfolioRiskProjectionSealV6(projection), true);
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.tone, "bounded");
  assert.equal(view.status_label, "LOCAL CHECKS CLEAR");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(Object.isFrozen(view), true);
});

test("downside-tail block receives critical semantics", () => {
  const view = card.buildPortfolioRiskDownsideTailViewModelV6(
    buildProjection("tail-block")
  );
  assert.equal(view.tone, "critical");
  assert.equal(view.status_label, "TAIL COUPLING BLOCK");
  assert.equal(view.tail_risk.decision, "BLOCK");
  assert.match(view.summary, /one constrained risk unit/);
});

test("exact unknown source stays known blocked and fail closed", () => {
  const view = card.buildPortfolioRiskDownsideTailViewModelV6(
    buildProjection("unknown")
  );
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.source_state, "UNKNOWN");
  assert.equal(view.tone, "unknown");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("resealed authority promotion is rejected", () => {
  const projection = buildProjection("clear");
  projection.authority.paper_authorized = true;
  const promoted = strictCanonical.sealDocument(projection, "projection_hash");
  const view = card.buildPortfolioRiskDownsideTailViewModelV6(promoted);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("older projection schema is rejected even when resealed", () => {
  const projection = buildProjection("clear");
  projection.schema_version =
    "strategy-correlation-cluster-portfolio-risk-projection-v5";
  const downgraded = strictCanonical.sealDocument(
    projection,
    "projection_hash"
  );
  assert.equal(card.verifyPortfolioRiskProjectionSealV6(downgraded), false);
  assert.equal(
    card.buildPortfolioRiskDownsideTailViewModelV6(downgraded).contract_state,
    "UNKNOWN"
  );
});

test("unexpected fields are rejected", () => {
  const projection = buildProjection("clear");
  projection.local_status = "PASS";
  const altered = strictCanonical.sealDocument(projection, "projection_hash");
  assert.equal(
    card.buildPortfolioRiskDownsideTailViewModelV6(altered).contract_state,
    "UNKNOWN"
  );
});

test("untrusted markup is neither accepted nor reflected", () => {
  const projection = buildProjection("clear");
  projection.local_decision.downside_tail_gate_reason =
    '<img src=x onerror="boom">';
  const altered = strictCanonical.sealDocument(projection, "projection_hash");
  const markup = card.renderPortfolioRiskDownsideTailCardV6(altered);
  assert.doesNotMatch(markup, /onerror|<img/);
  assert.match(markup, /SOURCE UNKNOWN/);
});

test("unregistered decision stage and blocker vocabulary fail closed", () => {
  const variants = [];

  const decision = buildProjection("clear");
  decision.local_decision.decision = "PASS_UNREGISTERED_TEXT";
  variants.push(strictCanonical.sealDocument(decision, "projection_hash"));

  const stage = buildProjection("clear");
  stage.stages[1].detail = "UNREGISTERED_STAGE_DETAIL";
  variants.push(strictCanonical.sealDocument(stage, "projection_hash"));

  const blocker = buildProjection("unknown");
  blocker.gaps.local_blockers = ["unregistered_blocker_text"];
  blocker.gaps.local_blocker_count = 1;
  variants.push(strictCanonical.sealDocument(blocker, "projection_hash"));

  variants.forEach((projection) => {
    const view = card.buildPortfolioRiskDownsideTailViewModelV6(projection);
    assert.equal(view.contract_state, "UNKNOWN");
    assert.equal(view.stages[3].state, "UNAUTHORIZED");
  });
});

test("source and fact contradictions fail closed after reseal", () => {
  const variants = [];

  const observedUnknown = buildProjection("clear");
  observedUnknown.facts.joint_local_research_source_known = false;
  variants.push(
    strictCanonical.sealDocument(observedUnknown, "projection_hash")
  );

  const observedIdentityMissing = buildProjection("clear");
  observedIdentityMissing.facts.trade_symbol_set_tail_identity_set_cross_bound =
    false;
  variants.push(
    strictCanonical.sealDocument(observedIdentityMissing, "projection_hash")
  );

  const unknownIdentityPromoted = buildProjection("unknown");
  unknownIdentityPromoted.facts.trade_symbol_set_tail_identity_set_cross_bound =
    true;
  variants.push(
    strictCanonical.sealDocument(unknownIdentityPromoted, "projection_hash")
  );

  variants.forEach((projection) => {
    assert.equal(
      card.buildPortfolioRiskDownsideTailViewModelV6(projection)
        .contract_state,
      "UNKNOWN"
    );
  });
});

test("descriptor is sealed, unmounted, and exactly verifiable", () => {
  const projection = buildProjection("tail-block");
  const descriptor =
    consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
      projection
    );
  assert.equal(descriptor.status, "BLOCK");
  assert.equal(descriptor.mount.mode, "UNMOUNTED");
  assert.equal(descriptor.mount.browser_executed, false);
  assert.equal(descriptor.facts.downside_tail_block_visible, true);
  assert.equal(
    consumer.verifyPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
      descriptor,
      projection
    ),
    true
  );
});

test("descriptor tamper cannot verify after reseal", () => {
  const projection = buildProjection("clear");
  const descriptor = JSON.parse(
    JSON.stringify(
      consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
        projection
      )
    )
  );
  descriptor.mount.mode = "MOUNTED";
  const altered = strictCanonical.sealDocument(descriptor, "descriptor_hash");
  assert.equal(
    consumer.verifyPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
      altered,
      projection
    ),
    false
  );
});

test("consumer declares scoped stylesheet without mounting it", () => {
  const descriptor =
    consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
      buildProjection("clear")
    );
  assert.equal(
    descriptor.presentation.stylesheet_asset,
    "evidence_portfolio_risk_downside_tail_card_v6.css"
  );
  assert.equal(descriptor.facts.stylesheet_declared, true);
  assert.equal(descriptor.facts.runtime_assets_accessed, false);
  assert.equal(descriptor.facts.browser_visual_review_performed, false);
});
