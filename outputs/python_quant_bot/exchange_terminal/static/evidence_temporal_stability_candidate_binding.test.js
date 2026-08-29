"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentTemporalReport21Lockboard,
  renderTemporalReport21Lockboard,
} = require("./evidence_temporal_stability_report21_lockboard.js");

function reportSummary(decision = "PASS") {
  const blocked = decision === "BLOCK";
  return {
    schema_version: "strategy-correlation-cluster-temporal-stability-migration-public-summary-v1",
    static_fingerprint: "20260821-temporal-report21-protocol-v10-lockboard-1",
    source: {
      status: "OBSERVED", protocol_target: "PROTOCOL_V10", report_target: "REPORT21",
      protocol_registration_status: "PREREGISTERED", report21_consumer_status: "AVAILABLE",
      temporal_policy_status: "SEALED", report21_contract_status: "VERIFIED",
      registration_report_pairing_status: "NOT_FORMALLY_BOUND",
    },
    gap: {
      status: blocked ? "TEMPORAL_EVIDENCE_BLOCKED_AND_UNBOUND" : "FORMAL_BINDING_AND_WRITER_NOT_SUPPLIED",
      temporal_decision: decision, formal_binding_status: "NOT_FORMALLY_BOUND",
      formal_registry_status: "NOT_SUPPLIED", schema21_writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: blocked ? "REPORT21_CONSUMER_BLOCK_UNBOUND" : "REPORT21_CONSUMER_PASS_UNBOUND",
      temporal_policy: "SEALED", report21_consumer: "AVAILABLE", report21_contract: "VERIFIED",
      consumer_decision: decision, formal_binding: "NOT_FORMALLY_BOUND",
      writer: "NOT_IMPLEMENTED", current: "NOT_ACTIVATED", writer_prerequisite_count: 13,
    },
    permission: {
      status: "RESEARCH_ONLY", descriptive_only: true, profitability_claim_allowed: false,
      paper_authorized: false, live_order_allowed: false, formal_registry_activation_allowed: false,
      report_writer_activation_allowed: false, current_admission_allowed: false,
      current_writer_activation_allowed: false,
    },
    redaction: {
      registration_hashes_exposed: false, extension_hashes_exposed: false,
      policy_hashes_exposed: false, source_registration_exposed: false,
      report_extensions_exposed: false, external_bindings_exposed: false,
      strategy_identities_exposed: false, cluster_identities_exposed: false,
      symbol_identities_exposed: false, correlation_values_exposed: false,
      interval_values_exposed: false, return_values_exposed: false,
      completed_price_datasets_exposed: false, profitability_metrics_exposed: false,
    },
  };
}

function candidateSummary(kind = "CANDIDATE_BOUND", decision = "PASS") {
  const states = {
    CANDIDATE_BOUND: ["OBSERVED", "VERIFIED", "CANDIDATE_BOUND", "FORMAL_BINDING_NOT_ESTABLISHED", "CANDIDATE_BOUND_NOT_FORMAL"],
    CANDIDATE_BLOCKED: ["OBSERVED", "VERIFIED", "BLOCK", "CANDIDATE_BINDING_BLOCKED", "CANDIDATE_BLOCKED"],
    UNKNOWN: ["UNKNOWN", "UNKNOWN", "UNKNOWN", "CANDIDATE_BINDING_UNKNOWN", "UNKNOWN"],
  }[kind];
  if (kind === "UNKNOWN") decision = "UNKNOWN";
  return {
    schema_version: "strategy-correlation-cluster-temporal-stability-candidate-binding-public-summary-v1",
    static_fingerprint: "20260821-temporal-report21-candidate-binding-lock-1",
    source: {
      status: states[0], binding_assessment_status: states[1], candidate_binding_status: states[2],
      report21_decision: decision,
    },
    gap: {
      status: states[3], formal_registration_report_binding: "NOT_ESTABLISHED",
      formal_registry_status: "NOT_SUPPLIED", writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: states[4], candidate_binding: states[2], report21_decision: decision,
      formal_binding: "NOT_ESTABLISHED", writer: "NOT_IMPLEMENTED", current: "NOT_ACTIVATED",
    },
    permission: {
      status: "RESEARCH_ONLY", descriptive_only: true, profitability_claim_allowed: false,
      candidate_binding_activation_allowed: false, formal_registration_report_binding_allowed: false,
      formal_registry_activation_allowed: false, paper_authorized: false, live_order_allowed: false,
      current_admission_allowed: false, current_writer_activation_allowed: false,
    },
    redaction: {
      assessment_hash_exposed: false, protocol_registration_hash_exposed: false,
      report21_extension_hash_exposed: false, report_identity_set_hash_exposed: false,
      binding_id_exposed: false, facts_exposed: false, blockers_exposed: false,
      external_assets_exposed: false, external_bindings_exposed: false,
      strategy_identities_exposed: false, correlation_values_exposed: false,
      interval_values_exposed: false, return_values_exposed: false,
      profitability_metrics_exposed: false,
    },
  };
}

test("matching pass candidate changes only binding maturity, never formal state", () => {
  const model = presentTemporalReport21Lockboard(reportSummary("PASS"), candidateSummary("CANDIDATE_BOUND", "PASS"));
  assert.match(model.state, /CANDIDATE_BOUND_NOT_FORMAL$/);
  assert.equal(model.rail.find((item) => item.code === "BND").status, "CANDIDATE");
  assert.equal(model.rail.find((item) => item.code === "WRT").status, "MISSING");
  assert.equal(model.rail.find((item) => item.code === "CUR").status, "LOCKED");
});

test("matching block report remains blocked while candidate binding is visible", () => {
  const model = presentTemporalReport21Lockboard(reportSummary("BLOCK"), candidateSummary("CANDIDATE_BOUND", "BLOCK"));
  assert.match(model.state, /^REPORT21_CONSUMER_BLOCK_UNBOUND_/);
  assert.equal(model.rail[3].status, "BLOCK");
  assert.equal(model.rail[4].status, "CANDIDATE");
});

test("candidate blocked remains distinct from unknown and formal", () => {
  const model = presentTemporalReport21Lockboard(reportSummary("PASS"), candidateSummary("CANDIDATE_BLOCKED", "PASS"));
  assert.match(model.state, /CANDIDATE_BLOCKED$/);
  assert.equal(model.rail[4].status, "BLOCKED");
  assert.doesNotMatch(model.stateLabel, /FORMAL|ACTIVATED/);
});

test("candidate decision mismatch fails closed at binding without hiding report evidence", () => {
  const model = presentTemporalReport21Lockboard(reportSummary("PASS"), candidateSummary("CANDIDATE_BOUND", "BLOCK"));
  assert.match(model.state, /BINDING_UNKNOWN$/);
  assert.equal(model.rail[3].status, "PASS");
  assert.equal(model.rail[4].status, "UNKNOWN");
  assert.equal(model.rail.at(-1).status, "LOCKED");
});

test("candidate permission alias fails closed at binding", () => {
  const candidate = candidateSummary("CANDIDATE_BOUND", "PASS");
  candidate.permission.candidate_binding_activation_allowed = 0;
  const model = presentTemporalReport21Lockboard(reportSummary("PASS"), candidate);
  assert.match(model.state, /BINDING_UNKNOWN$/);
  assert.equal(model.rail[4].status, "UNKNOWN");
});

test("renderer never presents candidate as formal, ready, or executable", () => {
  const target = { innerHTML: "" };
  renderTemporalReport21Lockboard(reportSummary("PASS"), target, candidateSummary("CANDIDATE_BOUND", "PASS"));
  assert.match(target.innerHTML, /CANDIDATE/);
  assert.match(target.innerHTML, /not formal registration or activation/i);
  assert.doesNotMatch(target.innerHTML, /\bREADY\b|FORMALLY BOUND|ACTIVATED|paper authorized|live order allowed/i);
});
