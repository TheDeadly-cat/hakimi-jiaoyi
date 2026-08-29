"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentClusterStabilityMigration,
  renderClusterStabilityMigration,
} = require("./evidence_cluster_stability_migration.js");

function validSummary(decision = "PASS") {
  const blocked = decision === "BLOCK";
  return {
    schema_version: "strategy-correlation-cluster-stability-public-summary-v1",
    static_fingerprint: "20260821-within-cluster-stability-calibration-rail-1",
    source: {
      status: "OBSERVED",
      uncertainty_evidence_status: "VERIFIED",
      complete_link_gate_status: "VERIFIED",
      stability_policy_status: "SEALED",
      stability_gate_contract_status: "VERIFIED",
    },
    gap: {
      status: blocked ? "STABILITY_EVIDENCE_BLOCKED" : "REPORT_INTEGRATION_NOT_IMPLEMENTED",
      stability_decision: decision,
      report_integration_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: blocked ? "CONSUMER_GATE_BLOCK" : "CONSUMER_GATE_PASS",
      family_scope: "WITHIN_CLUSTER_PAIRS_ONLY",
      correction_method: "BONFERRONI_TWO_SIDED_FWER_V1",
      interval_rule: "SEALED",
      report_integration: "NOT_IMPLEMENTED",
      writer: "NOT_IMPLEMENTED",
      current: "NOT_ACTIVATED",
    },
    permission: {
      status: "RESEARCH_ONLY",
      descriptive_only: true,
      profitability_claim_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      current_admission_allowed: false,
      current_writer_activation_allowed: false,
    },
    redaction: {
      artifact_hashes_exposed: false,
      strategy_identity_exposed: false,
      variant_identity_exposed: false,
      lane_identity_exposed: false,
      cluster_identities_exposed: false,
      symbol_identities_exposed: false,
      correlation_values_exposed: false,
      interval_values_exposed: false,
      return_values_exposed: false,
      rankings_exposed: false,
      profitability_metrics_exposed: false,
    },
  };
}

test("presents a held interval as consumer-only rather than activated", () => {
  const model = presentClusterStabilityMigration(validSummary());
  assert.equal(model.state, "CONSUMER_GATE_PASS");
  assert.deepEqual(model.flow.map((item) => item.key), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.deepEqual(model.rail.map((item) => item.status), ["VERIFIED", "VERIFIED", "HELD", "PASS", "MISSING", "LOCKED"]);
  assert.equal(model.flow[3].value, "Research only");
});

test("valid block evidence stays visible and never becomes unknown or ready", () => {
  const model = presentClusterStabilityMigration(validSummary("BLOCK"));
  assert.equal(model.state, "EVIDENCE_BLOCKED");
  assert.equal(model.rail[2].status, "BLOCKED");
  assert.equal(model.rail[3].status, "BLOCK");
  assert.equal(model.rail[5].status, "LOCKED");
});

test("numeric authority aliases degrade the whole presentation to unknown", () => {
  const summary = validSummary();
  summary.permission.paper_authorized = 0;
  const model = presentClusterStabilityMigration(summary);
  assert.equal(model.state, "UNKNOWN");
  assert.equal(model.flow[3].value, "Research only");
});

test("fingerprint or contract drift cannot retain observed presentation", () => {
  const summary = validSummary();
  summary.static_fingerprint = "drifted";
  const model = presentClusterStabilityMigration(summary);
  assert.equal(model.stateLabel, "UNVERIFIED SOURCE");
  assert.equal(model.rail[5].status, "LOCKED");
});

test("renderer emits the calibration rail without sensitive or promotional claims", () => {
  const target = { innerHTML: "" };
  renderClusterStabilityMigration(validSummary(), target);
  assert.match(target.innerHTML, /STABILITY CALIBRATION RAIL/);
  assert.match(target.innerHTML, /Report integration/);
  assert.match(target.innerHTML, /No paper or live execution authority/);
  assert.doesNotMatch(target.innerHTML, /cluster-ab|RAW_EXCESS|0\.75|0\.713|\bREADY\b|guaranteed|expected return/i);
});

test("untrusted summary text is never reflected into rendered markup", () => {
  const target = { innerHTML: "" };
  const summary = validSummary();
  summary.source.status = '<img src=x onerror="boom">';
  renderClusterStabilityMigration(summary, target);
  assert.doesNotMatch(target.innerHTML, /<img|onerror/);
  assert.match(target.innerHTML, /UNVERIFIED SOURCE/);
});

test("render without a target returns the neutral presentation model", () => {
  const model = renderClusterStabilityMigration(validSummary("BLOCK"));
  assert.equal(model.state, "EVIDENCE_BLOCKED");
  assert.equal(model.rail.length, 6);
});

test("stylesheet preserves responsive and reduced-motion contracts", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_cluster_stability_migration.css"), "utf8");
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(max-width: 440px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /--csmp-sealed:/);
  assert.doesNotMatch(css, /#[a-f0-9]{3,6}[^\n]*(purple|violet)/i);
});
