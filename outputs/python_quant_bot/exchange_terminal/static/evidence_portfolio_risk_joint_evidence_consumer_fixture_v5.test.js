"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_joint_evidence_card_v5.js");
const consumer = require("./evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js");

function projection() {
  return strictCanonical.sealDocument(
    {
      schema_version: card.PROJECTION_SCHEMA_VERSION,
      static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCK",
      decision:
        "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
      source: {
        candidate_v5_schema_version: "candidate-v5",
        candidate_v5_static_fingerprint: "candidate-v5-lock",
        candidate_v5_response_hash: "1".repeat(64),
        candidate_v5_exactly_verified: true,
        candidate_v5_implementation_sha256: "2".repeat(64),
        candidate_state: "KNOWN_BLOCKED",
        source_preregistration_hash: "3".repeat(64),
        portfolio_risk_adapter_v5_hash: "4".repeat(64),
      },
      local_decision: {
        status: "PASS",
        decision: "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE",
        joint_risk_gate_passed: true,
        blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"],
      },
      joint_risk: {
        assessment: "LOCAL_JOINT_RESEARCH_GATE_PASSED",
        multi_window_stability_gate_verified: true,
        anchor_window_budget_and_context_bound: true,
        trade_identity_cross_bound: true,
        anchor_window_id: "medium",
        trade_identity_hash: "5".repeat(64),
      },
      gaps: {
        remaining_blocker_count: 1,
        remaining_blockers: ["route_unregistered"],
        candidate_blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"],
      },
      stages: [
        { key: "SOURCE", state: "VERIFIED", detail: "V5_EXACT_REBUILD" },
        { key: "GAP", state: "PRESENT", detail: "EXTERNAL_GAPS" },
        { key: "MATURITY", state: "LOCAL_EVIDENCE_BOUND", detail: "LOCAL_ONLY" },
        { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_AUTHORITY" },
      ],
      facts: {
        projection_only: true,
        candidate_v5_exactly_verified: true,
        http_candidate_to_projection_bound: true,
        source_document_embedded: false,
        verification_context_embedded: false,
        positions_embedded: false,
        correlation_matrices_embedded: false,
        profitability_proven: false,
        runtime_consumer_bound: false,
        ui_mounted: false,
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
        writer_allowed: false,
      },
    },
    "projection_hash"
  );
}

test("exports are frozen and dependency versions are exact", () => {
  assert.equal(Object.isFrozen(consumer), true);
  assert.equal(consumer.EXPECTED_PROJECTION_SCHEMA_VERSION, card.PROJECTION_SCHEMA_VERSION);
  assert.equal(consumer.EXPECTED_CARD_SCHEMA_VERSION, card.CARD_SCHEMA_VERSION);
  assert.deepEqual(consumer.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("valid projection builds a sealed frozen unmounted descriptor", () => {
  const source = projection();
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(source);
  assert.equal(descriptor.status, "BLOCK");
  assert.equal(descriptor.decision, "KNOWN_BLOCKED_PROJECTION_V5_RENDER_DESCRIPTOR_ONLY");
  assert.equal(descriptor.mount.mode, "UNMOUNTED");
  assert.equal(descriptor.mount.dom_target, null);
  assert.equal(descriptor.mount.selector, null);
  assert.equal(Object.isFrozen(descriptor), true);
  assert.equal(Object.isFrozen(descriptor.presentation.view_model), true);
  assert.equal(
    consumer.verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
      descriptor,
      source
    ),
    true
  );
});

test("wrong schema and tampered seal fail closed", () => {
  const wrong = projection();
  delete wrong.projection_hash;
  wrong.schema_version = "strategy-correlation-cluster-portfolio-risk-projection-v4";
  const resealed = strictCanonical.sealDocument(wrong, "projection_hash");
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(resealed);
  assert.equal(descriptor.decision, "UNKNOWN_PROJECTION_V5_RENDER_DESCRIPTOR_FAIL_CLOSED");
  assert.equal(descriptor.facts.projection_v5_accepted, false);
});

test("descriptor verification rejects resealed authority tamper", () => {
  const source = projection();
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(source);
  const tampered = JSON.parse(JSON.stringify(descriptor));
  delete tampered.descriptor_hash;
  tampered.authority.presentation_mount_allowed = true;
  const resealed = strictCanonical.sealDocument(tampered, "descriptor_hash");
  assert.equal(
    consumer.verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
      resealed,
      source
    ),
    false
  );
});

test("descriptor declares static assets without DOM or browser claims", () => {
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
      projection()
    );
  assert.equal(descriptor.presentation.stylesheet_asset, consumer.STYLESHEET_ASSET);
  assert.match(descriptor.presentation.markup, /hakimi-joint-risk-card-v5/);
  assert.equal(descriptor.mount.mount_api_exposed, false);
  assert.equal(descriptor.mount.browser_executed, false);
  assert.equal(descriptor.facts.dom_accessed, false);
  assert.equal(descriptor.facts.browser_visual_review_performed, false);
  assert.equal(descriptor.facts.ui_mounted, false);
});

test("all authority and profitability claims remain locked", () => {
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
      projection()
    );
  assert.equal(descriptor.authority.descriptive_only, true);
  for (const [key, value] of Object.entries(descriptor.authority)) {
    if (key !== "descriptive_only") assert.equal(value, false);
  }
  assert.equal(descriptor.facts.profitability_proven, false);
  assert.doesNotMatch(JSON.stringify(descriptor), /READY/);
});
