"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  presentTemporalReport21Lockboard,
  renderTemporalReport21Lockboard,
} = require("./evidence_temporal_stability_report21_lockboard.js");

function validSummary(kind = "PASS") {
  const states = {
    PASS: {
      contract: "VERIFIED",
      pairing: "NOT_FORMALLY_BOUND",
      gap: "FORMAL_BINDING_AND_WRITER_NOT_SUPPLIED",
      decision: "PASS",
      maturity: "REPORT21_CONSUMER_PASS_UNBOUND",
    },
    BLOCK: {
      contract: "VERIFIED",
      pairing: "NOT_FORMALLY_BOUND",
      gap: "TEMPORAL_EVIDENCE_BLOCKED_AND_UNBOUND",
      decision: "BLOCK",
      maturity: "REPORT21_CONSUMER_BLOCK_UNBOUND",
    },
    NOT_SUPPLIED: {
      contract: "NOT_SUPPLIED",
      pairing: "NOT_SUPPLIED",
      gap: "REPORT21_CONTRACT_NOT_SUPPLIED",
      decision: "NOT_SUPPLIED",
      maturity: "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED",
    },
    UNKNOWN: {
      contract: "UNKNOWN",
      pairing: "UNKNOWN",
      gap: "REPORT21_CONTRACT_UNKNOWN",
      decision: "UNKNOWN",
      maturity: "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN",
    },
  }[kind];
  return {
    schema_version: "strategy-correlation-cluster-temporal-stability-migration-public-summary-v1",
    static_fingerprint: "20260821-temporal-report21-protocol-v10-lockboard-1",
    source: {
      status: "OBSERVED",
      protocol_target: "PROTOCOL_V10",
      report_target: "REPORT21",
      protocol_registration_status: "PREREGISTERED",
      report21_consumer_status: "AVAILABLE",
      temporal_policy_status: "SEALED",
      report21_contract_status: states.contract,
      registration_report_pairing_status: states.pairing,
    },
    gap: {
      status: states.gap,
      temporal_decision: states.decision,
      formal_binding_status: states.pairing,
      formal_registry_status: "NOT_SUPPLIED",
      schema21_writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: states.maturity,
      temporal_policy: "SEALED",
      report21_consumer: "AVAILABLE",
      report21_contract: states.contract,
      consumer_decision: states.decision,
      formal_binding: states.pairing,
      writer: "NOT_IMPLEMENTED",
      current: "NOT_ACTIVATED",
      writer_prerequisite_count: 13,
    },
    permission: {
      status: "RESEARCH_ONLY",
      descriptive_only: true,
      profitability_claim_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      formal_registry_activation_allowed: false,
      report_writer_activation_allowed: false,
      current_admission_allowed: false,
      current_writer_activation_allowed: false,
    },
    redaction: {
      registration_hashes_exposed: false,
      extension_hashes_exposed: false,
      policy_hashes_exposed: false,
      source_registration_exposed: false,
      report_extensions_exposed: false,
      external_bindings_exposed: false,
      strategy_identities_exposed: false,
      cluster_identities_exposed: false,
      symbol_identities_exposed: false,
      correlation_values_exposed: false,
      interval_values_exposed: false,
      return_values_exposed: false,
      completed_price_datasets_exposed: false,
      profitability_metrics_exposed: false,
    },
  };
}

function validCandidateSummary(kind = "BOUND_PASS") {
  const states = {
    BOUND_PASS: {
      source: "OBSERVED",
      assessment: "VERIFIED",
      binding: "CANDIDATE_BOUND",
      decision: "PASS",
      gap: "FORMAL_BINDING_NOT_ESTABLISHED",
      maturity: "CANDIDATE_BOUND_NOT_FORMAL",
    },
    BOUND_BLOCK: {
      source: "OBSERVED",
      assessment: "VERIFIED",
      binding: "CANDIDATE_BOUND",
      decision: "BLOCK",
      gap: "FORMAL_BINDING_NOT_ESTABLISHED",
      maturity: "CANDIDATE_BOUND_NOT_FORMAL",
    },
    CANDIDATE_BLOCKED: {
      source: "OBSERVED",
      assessment: "VERIFIED",
      binding: "BLOCK",
      decision: "PASS",
      gap: "CANDIDATE_BINDING_BLOCKED",
      maturity: "CANDIDATE_BLOCKED",
    },
    NOT_SUPPLIED: {
      source: "NOT_SUPPLIED",
      assessment: "NOT_SUPPLIED",
      binding: "NOT_SUPPLIED",
      decision: "NOT_SUPPLIED",
      gap: "CANDIDATE_BINDING_NOT_SUPPLIED",
      maturity: "NOT_SUPPLIED",
    },
    UNKNOWN: {
      source: "UNKNOWN",
      assessment: "UNKNOWN",
      binding: "UNKNOWN",
      decision: "UNKNOWN",
      gap: "CANDIDATE_BINDING_UNKNOWN",
      maturity: "UNKNOWN",
    },
  }[kind];
  return {
    schema_version:
      "strategy-correlation-cluster-temporal-stability-candidate-binding-public-summary-v1",
    static_fingerprint:
      "20260821-temporal-report21-candidate-binding-lock-1",
    source: {
      status: states.source,
      binding_assessment_status: states.assessment,
      candidate_binding_status: states.binding,
      report21_decision: states.decision,
    },
    gap: {
      status: states.gap,
      formal_registration_report_binding: "NOT_ESTABLISHED",
      formal_registry_status: "NOT_SUPPLIED",
      writer_status: "NOT_IMPLEMENTED",
      current_activation_status: "NOT_ACTIVATED",
    },
    maturity: {
      status: states.maturity,
      candidate_binding: states.binding,
      report21_decision: states.decision,
      formal_binding: "NOT_ESTABLISHED",
      writer: "NOT_IMPLEMENTED",
      current: "NOT_ACTIVATED",
    },
    permission: {
      status: "RESEARCH_ONLY",
      descriptive_only: true,
      profitability_claim_allowed: false,
      candidate_binding_activation_allowed: false,
      formal_registration_report_binding_allowed: false,
      formal_registry_activation_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      current_admission_allowed: false,
      current_writer_activation_allowed: false,
    },
    redaction: {
      assessment_hash_exposed: false,
      protocol_registration_hash_exposed: false,
      report21_extension_hash_exposed: false,
      report_identity_set_hash_exposed: false,
      binding_id_exposed: false,
      facts_exposed: false,
      blockers_exposed: false,
      external_assets_exposed: false,
      external_bindings_exposed: false,
      strategy_identities_exposed: false,
      correlation_values_exposed: false,
      interval_values_exposed: false,
      return_values_exposed: false,
      profitability_metrics_exposed: false,
    },
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test("presents report21 pass as verified but explicitly unbound", () => {
  const model = presentTemporalReport21Lockboard(validSummary("PASS"));
  assert.equal(model.state, "REPORT21_CONSUMER_PASS_UNBOUND");
  assert.deepEqual(model.flow.map((item) => item.key), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.deepEqual(model.rail.map((item) => item.status), ["SEALED", "AVAILABLE", "SEALED", "PASS", "UNBOUND", "MISSING", "LOCKED"]);
  assert.equal(model.flow[3].value, "Research only");
});

test("valid block remains visible without becoming unknown or ready", () => {
  const model = presentTemporalReport21Lockboard(validSummary("BLOCK"));
  assert.equal(model.state, "REPORT21_CONSUMER_BLOCK_UNBOUND");
  assert.equal(model.rail[3].status, "BLOCK");
  assert.equal(model.rail[4].status, "UNBOUND");
  assert.equal(model.rail.at(-1).status, "LOCKED");
});

test("not supplied and invalid supplied report remain distinct", () => {
  const missing = presentTemporalReport21Lockboard(validSummary("NOT_SUPPLIED"));
  const invalid = presentTemporalReport21Lockboard(validSummary("UNKNOWN"));
  assert.equal(missing.state, "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED");
  assert.equal(missing.rail[3].status, "MISSING");
  assert.equal(invalid.state, "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN");
  assert.equal(invalid.rail[3].status, "UNKNOWN");
});

test("numeric authority aliases degrade the whole presentation to unknown", () => {
  const summary = validSummary("PASS");
  summary.permission.paper_authorized = 0;
  const model = presentTemporalReport21Lockboard(summary);
  assert.equal(model.state, "UNKNOWN");
  assert.equal(model.flow[3].value, "Research only");
});

test("fingerprint and prerequisite drift cannot retain observed state", () => {
  const fingerprint = validSummary("PASS");
  fingerprint.static_fingerprint = "drifted";
  const count = validSummary("PASS");
  count.maturity.writer_prerequisite_count = "13";
  assert.equal(presentTemporalReport21Lockboard(fingerprint).state, "UNKNOWN");
  assert.equal(presentTemporalReport21Lockboard(count).state, "UNKNOWN");
});

test("candidate-bound pass and block remain non-formal and current-locked", () => {
  const passing = presentTemporalReport21Lockboard(
    validSummary("PASS"),
    validCandidateSummary("BOUND_PASS"),
  );
  const blocked = presentTemporalReport21Lockboard(
    validSummary("BLOCK"),
    validCandidateSummary("BOUND_BLOCK"),
  );
  assert.equal(
    passing.state,
    "REPORT21_CONSUMER_PASS_UNBOUND_CANDIDATE_BOUND_NOT_FORMAL",
  );
  assert.equal(
    blocked.state,
    "REPORT21_CONSUMER_BLOCK_UNBOUND_CANDIDATE_BOUND_NOT_FORMAL",
  );
  assert.equal(passing.rail[4].status, "CANDIDATE");
  assert.equal(blocked.rail[3].status, "BLOCK");
  assert.equal(blocked.rail.at(-1).status, "LOCKED");
});

test("candidate blocked unknown and not-supplied remain distinct", () => {
  const blocked = presentTemporalReport21Lockboard(
    validSummary("PASS"),
    validCandidateSummary("CANDIDATE_BLOCKED"),
  );
  const unknown = presentTemporalReport21Lockboard(
    validSummary("PASS"),
    validCandidateSummary("UNKNOWN"),
  );
  const missing = presentTemporalReport21Lockboard(
    validSummary("PASS"),
    validCandidateSummary("NOT_SUPPLIED"),
  );
  assert.equal(blocked.rail[4].status, "BLOCKED");
  assert.match(unknown.state, /BINDING_UNKNOWN$/);
  assert.equal(unknown.rail[4].status, "UNKNOWN");
  assert.equal(missing.state, "REPORT21_CONSUMER_PASS_UNBOUND");
});

test("candidate decision and native type drift degrade binding to unknown", () => {
  const mismatch = validCandidateSummary("BOUND_BLOCK");
  const permissionAlias = validCandidateSummary("BOUND_PASS");
  permissionAlias.permission.paper_authorized = 0;
  const redactionAlias = validCandidateSummary("BOUND_PASS");
  redactionAlias.redaction.facts_exposed = 0;
  for (const candidate of [mismatch, permissionAlias, redactionAlias]) {
    const model = presentTemporalReport21Lockboard(
      validSummary("PASS"),
      candidate,
    );
    assert.match(model.state, /BINDING_UNKNOWN$/);
    assert.equal(model.rail[4].status, "UNKNOWN");
    assert.equal(model.rail.at(-1).status, "LOCKED");
  }
});

test("extra private keys invalidate migration and candidate public shapes", () => {
  const sections = [[], ["source"], ["gap"], ["maturity"], ["permission"], ["redaction"]];
  for (const pathParts of sections) {
    const summary = clone(validSummary("PASS"));
    let target = summary;
    for (const part of pathParts) target = target[part];
    target.private_evidence = "a".repeat(64);
    assert.equal(presentTemporalReport21Lockboard(summary).state, "UNKNOWN");

    const candidate = clone(validCandidateSummary("BOUND_PASS"));
    target = candidate;
    for (const part of pathParts) target = target[part];
    target.private_evidence = "b".repeat(64);
    const model = presentTemporalReport21Lockboard(
      validSummary("PASS"),
      candidate,
    );
    assert.match(model.state, /BINDING_UNKNOWN$/);
    assert.equal(model.rail[4].status, "UNKNOWN");
  }
});

test("candidate renderer never reflects private evidence or implies ready", () => {
  const target = { innerHTML: "" };
  const candidate = validCandidateSummary("BOUND_PASS");
  candidate.facts = '<img src=x onerror="boom">';
  renderTemporalReport21Lockboard(validSummary("PASS"), target, candidate);
  assert.doesNotMatch(target.innerHTML, /<img|onerror|\bREADY\b/i);
  assert.match(target.innerHTML, /Candidate assessment unverified or mismatched/);
  assert.match(target.innerHTML, /No paper or live execution authority/);
});

test("renderer exposes three sealed boundaries and a locked migration rail", () => {
  const target = { innerHTML: "" };
  renderTemporalReport21Lockboard(validSummary("PASS"), target);
  assert.match(target.innerHTML, /PREREGISTERED WINDOW REGISTER/);
  assert.match(target.innerHTML, /W1/);
  assert.match(target.innerHTML, /W2/);
  assert.match(target.innerHTML, /W3/);
  assert.match(target.innerHTML, /Formal binding/);
  assert.match(target.innerHTML, /No paper or live execution authority/);
  assert.doesNotMatch(target.innerHTML, /cluster-ab|RAW_EXCESS|0\.75|0\.713|\bREADY\b|guaranteed|expected return/i);
});

test("untrusted summary text is never reflected into rendered markup", () => {
  const target = { innerHTML: "" };
  const summary = validSummary("PASS");
  summary.source.status = '<img src=x onerror="boom">';
  renderTemporalReport21Lockboard(summary, target);
  assert.doesNotMatch(target.innerHTML, /<img|onerror/);
  assert.match(target.innerHTML, /UNVERIFIED SOURCE/);
});

test("render without a target returns the neutral presentation model", () => {
  const model = renderTemporalReport21Lockboard(validSummary("BLOCK"));
  assert.equal(model.state, "REPORT21_CONSUMER_BLOCK_UNBOUND");
  assert.equal(model.windows.length, 3);
  assert.equal(model.rail.length, 7);
});

test("component remains unmounted and has no ambient document side effects", () => {
  const moduleSource = fs.readFileSync(path.join(__dirname, "evidence_temporal_stability_report21_lockboard.js"), "utf8");
  const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  assert.doesNotMatch(moduleSource, /DOMContentLoaded|querySelector|appendChild/);
  assert.doesNotMatch(appSource, /HakimiTemporalReport21Lockboard|evidence_temporal_stability_report21_lockboard/);
});

test("stylesheet preserves responsive reduced-motion and project palette contracts", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_temporal_stability_report21_lockboard.css"), "utf8");
  assert.match(css, /@media \(max-width: 920px\)/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(max-width: 440px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /--tsr21-sealed: #2e665d/);
  assert.match(css, /--tsr21-gap: #8e4f32/);
  assert.doesNotMatch(css, /purple|violet|#(?:6f|7c|8b)\w{4}/i);
});
