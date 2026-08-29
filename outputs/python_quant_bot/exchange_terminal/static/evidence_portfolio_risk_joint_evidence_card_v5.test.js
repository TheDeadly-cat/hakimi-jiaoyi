"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_joint_evidence_card_v5.js");

function projection(overrides) {
  const value = {
    schema_version: card.PROJECTION_SCHEMA_VERSION,
    static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
    status: "BLOCK",
    decision:
      "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
    source: {
      candidate_v5_schema_version:
        "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v5",
      candidate_v5_static_fingerprint:
        "20260823-portfolio-risk-presentation-http-adapter-v5-unregistered-candidate-1",
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
      remaining_blocker_count: 2,
      remaining_blockers: ["external_review", "route_unregistered"],
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
  };
  Object.assign(value, overrides || {});
  return strictCanonical.sealDocument(value, "projection_hash");
}

test("exports are frozen and version locked", () => {
  assert.equal(Object.isFrozen(card), true);
  assert.equal(card.PROJECTION_SCHEMA_VERSION.endsWith("projection-v5"), true);
  assert.deepEqual(card.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("seal verification is schema aware", () => {
  assert.equal(card.verifyPortfolioRiskProjectionSealV5(projection()), true);
  const wrong = projection({ schema_version: "strategy-correlation-cluster-portfolio-risk-projection-v4" });
  assert.equal(strictCanonical.verifySealedDocument(wrong, "projection_hash"), true);
  assert.equal(card.verifyPortfolioRiskProjectionSealV5(wrong), false);
});

test("valid projection builds a frozen calibrated view model", () => {
  const view = card.buildPortfolioRiskJointEvidenceViewModelV5(projection());
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.tone, "bounded");
  assert.equal(view.status_label, "LOCAL GATE PASS");
  assert.equal(Object.isFrozen(view), true);
  assert.equal(Object.isFrozen(view.stages), true);
});

test("blocked joint decision remains a visible gap", () => {
  const value = projection();
  delete value.projection_hash;
  value.local_decision.status = "BLOCK";
  value.local_decision.joint_risk_gate_passed = false;
  value.joint_risk.assessment = "LOCAL_JOINT_RESEARCH_GATE_BLOCKED";
  const sealed = strictCanonical.sealDocument(value, "projection_hash");
  const view = card.buildPortfolioRiskJointEvidenceViewModelV5(sealed);
  assert.equal(view.contract_state, "KNOWN_BLOCKED");
  assert.equal(view.tone, "gap");
  assert.equal(view.status_label, "LOCAL GATE BLOCK");
});

test("invalid source renders unknown without permission", () => {
  const view = card.buildPortfolioRiskJointEvidenceViewModelV5({});
  assert.equal(view.contract_state, "UNKNOWN");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.match(view.permission_note, /unavailable/i);
});

test("rendered markup is static and escapes source strings", () => {
  const value = projection();
  delete value.projection_hash;
  value.stages[1].detail = '<img src=x onerror="boom">';
  const html = card.renderPortfolioRiskJointEvidenceCardV5(
    strictCanonical.sealDocument(value, "projection_hash")
  );
  assert.match(html, /hakimi-joint-risk-card-v5/);
  assert.match(html, /&lt;img src=x onerror=&quot;boom&quot;&gt;/);
  assert.doesNotMatch(html, /<img/);
  assert.doesNotMatch(html, /onerror\s*=\s*["']/i);
  assert.doesNotMatch(html, /<script/i);
});

test("view and markup contain no readiness or profitability claim", () => {
  const value = projection();
  const rendered = JSON.stringify({
    view: card.buildPortfolioRiskJointEvidenceViewModelV5(value),
    html: card.renderPortfolioRiskJointEvidenceCardV5(value),
  });
  assert.doesNotMatch(rendered, /READY/);
  assert.doesNotMatch(rendered, /profit/i);
  assert.match(rendered, /UNAUTHORIZED/);
});

test("stylesheet is scoped, responsive, and reduced-motion aware", () => {
  const css = fs.readFileSync(
    path.resolve(__dirname, "evidence_portfolio_risk_joint_evidence_card_v5.css"),
    "utf8"
  );
  assert.match(css, /\.hakimi-joint-risk-card-v5/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /prefers-reduced-motion/);
  assert.doesNotMatch(css, /(^|\})\s*(html|body)\s*\{/m);
  assert.doesNotMatch(css, /READY/);
  assert.doesNotMatch(css, /purple/i);
});
