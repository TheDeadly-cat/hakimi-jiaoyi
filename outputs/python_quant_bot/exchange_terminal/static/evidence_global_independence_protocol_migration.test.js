"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentGlobalIndependenceProtocolMigration,
  renderGlobalIndependenceProtocolMigration,
} = require("./evidence_global_independence_protocol_migration.js");

function validSummary() {
  return {
    schema_version:
      "strategy-correlation-global-independence-protocol-migration-public-summary-v1",
    static_fingerprint:
      "20260821-global-independence-protocol-v8-migration-seal-1",
    source: {
      status: "OBSERVED",
      protocol_target: "PROTOCOL_V8",
      report_target: "REPORT19",
      protocol_registration_status: "PREREGISTERED",
      report19_consumer_status: "AVAILABLE",
      global_independence_policy_status: "SEALED",
    },
    gap: {
      status: "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
      formal_registry_status: "NOT_SUPPLIED",
      schema19_writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: "PROTOCOL_PREREGISTERED",
      exact_graph_policy: "SEALED",
      formal_registry: "PENDING",
      writer: "NOT_IMPLEMENTED",
      current: "NOT_ACTIVATED",
      writer_prerequisite_count: 7,
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
      artifact_hashes_exposed: false,
      policy_hashes_exposed: false,
      source_registration_exposed: false,
      registry_identity_exposed: false,
      classification_source_exposed: false,
      selection_cutoff_exposed: false,
      cluster_identities_exposed: false,
      symbol_identities_exposed: false,
    },
  };
}

test("presents source-gap-maturity-permission without activation language", () => {
  const model = presentGlobalIndependenceProtocolMigration(validSummary());
  assert.equal(model.state, "PREREGISTERED_ONLY");
  assert.deepEqual(
    model.flow.map((item) => item.key),
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
  );
  assert.deepEqual(
    model.seals.map((seal) => seal.status),
    ["SEALED", "AVAILABLE", "REQUIRED", "MISSING", "MISSING", "LOCKED"],
  );
  assert.equal(model.prerequisiteCount, 7);
});

test("numeric permission alias degrades the whole presentation to unknown", () => {
  const summary = validSummary();
  summary.permission.paper_authorized = 0;
  const model = presentGlobalIndependenceProtocolMigration(summary);
  assert.equal(model.state, "UNKNOWN");
  assert.equal(model.flow[3].value, "Research only");
});

test("partial or mismatched fingerprint never presents observed state", () => {
  const summary = validSummary();
  summary.static_fingerprint = "drifted";
  const model = presentGlobalIndependenceProtocolMigration(summary);
  assert.equal(model.stateLabel, "UNVERIFIED SOURCE");
  assert.equal(model.seals[5].status, "LOCKED");
});

test("renderer emits the seal circuit without forbidden claims", () => {
  const target = { innerHTML: "" };
  const model = renderGlobalIndependenceProtocolMigration(validSummary(), target);
  assert.equal(model.state, "PREREGISTERED_ONLY");
  assert.match(target.innerHTML, /ACTIVATION SEAL CIRCUIT/);
  assert.match(target.innerHTML, /Formal registry/);
  assert.match(target.innerHTML, /No paper or live execution authority/);
  assert.doesNotMatch(target.innerHTML, /\bREADY\b|guaranteed|expected return/i);
});

test("untrusted summary text is not reflected into rendered markup", () => {
  const target = { innerHTML: "" };
  const summary = validSummary();
  summary.source.protocol_target = '<img src=x onerror="boom">';
  renderGlobalIndependenceProtocolMigration(summary, target);
  assert.doesNotMatch(target.innerHTML, /<img|onerror/);
  assert.match(target.innerHTML, /UNVERIFIED SOURCE/);
});

test("render without a target returns the neutral presentation model", () => {
  const model = renderGlobalIndependenceProtocolMigration(validSummary());
  assert.equal(model.state, "PREREGISTERED_ONLY");
  assert.equal(model.seals.length, 6);
});
