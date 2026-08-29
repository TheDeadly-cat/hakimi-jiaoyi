"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentClusterStabilityMigration,
  renderClusterStabilityMigration,
} = require("./evidence_cluster_stability_migration.js");

function validProtocolSummary() {
  return {
    schema_version: "strategy-correlation-cluster-stability-protocol-migration-public-summary-v1",
    static_fingerprint: "20260821-cluster-stability-protocol-v9-migration-rail-1",
    source: {
      status: "OBSERVED",
      protocol_target: "PROTOCOL_V9",
      report_target: "REPORT20",
      protocol_registration_status: "PREREGISTERED",
      report20_consumer_status: "AVAILABLE",
      stability_policy_status: "SEALED",
    },
    gap: {
      status: "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
      formal_registry_status: "NOT_SUPPLIED",
      schema20_writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: "PROTOCOL_PREREGISTERED",
      stability_policy: "SEALED",
      report20_consumer: "AVAILABLE",
      formal_registry: "PENDING",
      writer: "NOT_IMPLEMENTED",
      current: "NOT_ACTIVATED",
      writer_prerequisite_count: 12,
    },
    permission: {
      status: "RESEARCH_ONLY",
      descriptive_only: true,
      profitability_claim_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      formal_registry_activation_allowed: false,
      current_admission_allowed: false,
      current_writer_activation_allowed: false,
    },
    redaction: {
      registration_hashes_exposed: false,
      policy_hashes_exposed: false,
      source_registration_exposed: false,
      registry_identity_exposed: false,
      strategy_identities_exposed: false,
      cluster_identities_exposed: false,
      symbol_identities_exposed: false,
      correlation_values_exposed: false,
      interval_values_exposed: false,
      return_values_exposed: false,
    },
  };
}

test("presents protocol-v9 and report20 without claiming activation", () => {
  const model = presentClusterStabilityMigration(validProtocolSummary());
  assert.equal(model.variant, "protocol-v9");
  assert.equal(model.state, "PROTOCOL_PREREGISTERED");
  assert.deepEqual(model.flow.map((item) => item.key), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.deepEqual(model.rail.map((item) => item.status), ["SEALED", "AVAILABLE", "SEALED", "MISSING", "MISSING", "LOCKED"]);
});

test("renderer keeps registry writer and current visibly open", () => {
  const target = { innerHTML: "" };
  renderClusterStabilityMigration(validProtocolSummary(), target);
  assert.match(target.innerHTML, /data-variant="protocol-v9"/);
  assert.match(target.innerHTML, /Formal registry/);
  assert.match(target.innerHTML, /Report20 writer/);
  assert.match(target.innerHTML, /Preregistration is not activation/);
  assert.doesNotMatch(target.innerHTML, /\bREADY\b|guaranteed|expected return/i);
});

test("string prerequisite alias degrades protocol presentation to unknown", () => {
  const summary = validProtocolSummary();
  summary.maturity.writer_prerequisite_count = "12";
  const model = presentClusterStabilityMigration(summary);
  assert.equal(model.state, "UNKNOWN");
  assert.equal(model.rail.at(-1).status, "LOCKED");
});

test("authority escalation degrades protocol presentation to unknown", () => {
  const summary = validProtocolSummary();
  summary.permission.formal_registry_activation_allowed = true;
  const model = presentClusterStabilityMigration(summary);
  assert.equal(model.stateLabel, "UNVERIFIED SOURCE");
  assert.equal(model.flow[3].value, "Research only");
});

test("fingerprint drift and untrusted text are not reflected", () => {
  const target = { innerHTML: "" };
  const summary = validProtocolSummary();
  summary.static_fingerprint = '<img src=x onerror="boom">';
  renderClusterStabilityMigration(summary, target);
  assert.doesNotMatch(target.innerHTML, /<img|onerror/);
  assert.match(target.innerHTML, /UNVERIFIED SOURCE/);
});

test("protocol visual variant retains responsive and reduced-motion contracts", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_cluster_stability_migration.css"), "utf8");
  assert.match(css, /data-variant="protocol-v9"/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(max-width: 440px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
});
