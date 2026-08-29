"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentGlobalIndependenceProtocolMigration,
  renderGlobalIndependenceProtocolMigration,
} = require("./evidence_global_independence_protocol_migration.js");

function summary(candidateStatus = "CANDIDATE_BOUND") {
  const states = {
    NOT_SUPPLIED: ["REGISTRY_CANDIDATE_NOT_SUPPLIED", "PROTOCOL_PREREGISTERED"],
    BLOCK: ["REGISTRY_CANDIDATE_BINDING_BLOCK", "CANDIDATE_EVIDENCE_BLOCKED"],
    CANDIDATE_BOUND: ["FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED", "REGISTRY_CANDIDATE_BOUND"],
  };
  return {
    schema_version:
      "strategy-correlation-global-independence-protocol-migration-public-summary-v2",
    static_fingerprint:
      "20260821-global-independence-registry-candidate-migration-seal-1",
    source: {
      status: "OBSERVED",
      protocol_target: "PROTOCOL_V8",
      report_target: "REPORT19",
      protocol_registration_status: "PREREGISTERED",
      report19_consumer_status: "AVAILABLE",
      global_independence_policy_status: "SEALED",
      registry_candidate_contract_status: "AVAILABLE",
    },
    gap: {
      status: states[candidateStatus][0],
      registry_candidate_status: candidateStatus,
      formal_registry_status: "NOT_SUPPLIED",
      schema19_writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: states[candidateStatus][1],
      registry_candidate: candidateStatus,
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
      registry_candidate_identity_exposed: false,
      registry_candidate_hash_exposed: false,
      registry_source_exposed: false,
      registry_source_hash_exposed: false,
      selection_cutoff_exposed: false,
      cluster_identities_exposed: false,
      symbol_identities_exposed: false,
    },
  };
}

test("bound candidate adds a seventh node without claiming formal registry", () => {
  const model = presentGlobalIndependenceProtocolMigration(summary());
  assert.equal(model.state, "REGISTRY_CANDIDATE_BOUND");
  assert.equal(model.stateLabel, "CANDIDATE BOUND / NOT FORMAL");
  assert.equal(model.seals.length, 7);
  assert.deepEqual(
    model.seals.map((seal) => seal.status),
    ["SEALED", "AVAILABLE", "REQUIRED", "BOUND", "MISSING", "MISSING", "LOCKED"],
  );
});

test("missing candidate remains preregistered without maturity upgrade", () => {
  const model = presentGlobalIndependenceProtocolMigration(summary("NOT_SUPPLIED"));
  assert.equal(model.state, "REGISTRY_CANDIDATE_NOT_SUPPLIED");
  assert.equal(model.seals[3].status, "MISSING");
  assert.equal(model.seals[4].status, "MISSING");
});

test("blocked candidate evidence is distinct from unknown source", () => {
  const model = presentGlobalIndependenceProtocolMigration(summary("BLOCK"));
  assert.equal(model.state, "CANDIDATE_EVIDENCE_BLOCKED");
  assert.equal(model.seals[3].status, "BLOCKED");
  assert.equal(model.flow[0].value, "Protocol-v8");
});

test("non-number prerequisite count in candidate summary fails closed", () => {
  const payload = summary();
  payload.maturity.writer_prerequisite_count = "7";
  const model = presentGlobalIndependenceProtocolMigration(payload);
  assert.equal(model.state, "UNKNOWN");
});

test("rendered candidate circuit keeps formal and current visibly closed", () => {
  const target = { innerHTML: "" };
  renderGlobalIndependenceProtocolMigration(summary(), target);
  assert.match(target.innerHTML, /data-variant="registry-candidate"/);
  assert.match(target.innerHTML, /Registry candidate/);
  assert.match(target.innerHTML, /Formal registry/);
  assert.match(target.innerHTML, /7\/7/);
  assert.doesNotMatch(target.innerHTML, /\bREADY\b|guaranteed|expected return/i);
});
