"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const lockboard = require("./evidence_report22_date_grid_migration_lockboard.js");
const binding = require("./evidence_report22_date_grid_migration_http_binding.js");

function canonicalJson(value) {
  if (value === null) return "null";
  if (typeof value === "string" || typeof value === "number") {
    return JSON.stringify(value);
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
    .join(",")}}`;
}

function seal(document) {
  const unsigned = JSON.parse(JSON.stringify(document));
  delete unsigned.response_hash;
  return {
    ...unsigned,
    response_hash: crypto
      .createHash("sha256")
      .update(canonicalJson(unsigned), "utf8")
      .digest("hex"),
  };
}

function publicSummary(kind = "DRY_PASS") {
  const state = {
    NOT_SUPPLIED: ["NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED", "ASSESSMENT_NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED"],
    UNKNOWN: ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "ASSESSMENT_UNKNOWN", "UNKNOWN", "UNKNOWN"],
    PLAN_LISTED: ["VERIFIED", "LIST", "NOT_EVALUATED", "NOT_EVALUATED", "PLAN_ONLY", "PLAN_LISTED_NOT_EXECUTED", "NOT_EVALUATED"],
    DRY_PASS: ["VERIFIED", "DRY_RUN", "VERIFIED", "PASS", "DRY_RUN_ONLY", "DRY_RUN_VERIFIED_NOT_EXECUTED", "VERIFIED"],
    DRY_BLOCK: ["VERIFIED", "DRY_RUN", "VERIFIED", "BLOCK", "DRY_RUN_ONLY", "DRY_RUN_VERIFIED_NOT_EXECUTED", "VERIFIED"],
  }[kind];
  const sourceState = kind.startsWith("DRY_") ? "DRY_RUN_VERIFIED" : kind;
  return {
    schema_version: lockboard.SUMMARY_SCHEMA,
    contract_fingerprint: lockboard.CONTRACT_FINGERPRINT,
    axis_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
    source: {
      state: sourceState,
      assessment_contract: state[0],
      assessment_mode: state[1],
      report22_contract: state[2],
      report22_decision: state[3],
    },
    gap: {
      state: state[4],
      execution: "NOT_EXECUTED",
      runtime_mutations: "NONE",
      migration_execution: "NOT_ALLOWED",
      fresh_migration: "NOT_ALLOWED",
      formal_registry: "NOT_BOUND",
      writer: "NOT_AVAILABLE",
      current: "NOT_ADMITTED",
    },
    maturity: {
      state: state[5],
      report22_evaluation: state[6],
      formal_registry: "NOT_BOUND",
      current: "NOT_ADMITTED",
    },
    permission: {
      state: "RESEARCH_ONLY",
      descriptive_only: true,
      profitability_claim_allowed: false,
      migration_execution_allowed: false,
      writer_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    },
    redaction: {
      assessment_hash_exposed: false,
      candidate_registration_hash_exposed: false,
      report22_extension_hash_exposed: false,
      expected_hashes_exposed: false,
      identity_bindings_exposed: false,
      raw_dates_exposed: false,
      raw_prices_exposed: false,
      returns_exposed: false,
      correlations_exposed: false,
      plan_details_exposed: false,
      blocker_details_exposed: false,
      profitability_metrics_exposed: false,
      external_assets_embedded: false,
    },
  };
}

function blockers(state, decision) {
  const values = ["TRANSPORT_UNREGISTERED", "MIGRATION_EXECUTION_NOT_ALLOWED"];
  if (state === "NOT_SUPPLIED") values.push("MIGRATION_ASSESSMENT_NOT_SUPPLIED");
  else if (state === "UNKNOWN") values.push("MIGRATION_ASSESSMENT_UNKNOWN");
  else if (state === "PLAN_LISTED") values.push("REPORT22_NOT_EVALUATED");
  else if (decision === "BLOCK") values.push("REPORT22_DECISION_BLOCK");
  return values;
}

function candidateResponse(kind = "DRY_PASS") {
  const payload = publicSummary(kind);
  const state = payload.source.state;
  const supplied = state !== "NOT_SUPPLIED";
  const observed = ["PLAN_LISTED", "DRY_RUN_VERIFIED"].includes(state);
  return seal({
    schema_version: binding.RESPONSE_SCHEMA,
    static_fingerprint: binding.RESPONSE_FINGERPRINT,
    interface_status: binding.INTERFACE_STATUS,
    state,
    payload,
    facts: {
      request_contract_valid: true,
      trusted_context_contract_valid: true,
      migration_assessment_supplied: supplied,
      source_projection_verified: true,
      source_assessment_observed: observed,
      report22_evaluated: state === "DRY_RUN_VERIFIED",
      payload_available: true,
      transport_registered: false,
      runtime_asset_accessed: false,
    },
    lineage: {
      source_projection_schema_version: lockboard.SUMMARY_SCHEMA,
      source_projection_static_fingerprint: lockboard.CONTRACT_FINGERPRINT,
      request_documents_embedded: false,
      migration_assessment_embedded: false,
      verification_context_embedded: false,
      report22_extension_embedded: false,
      source_hashes_embedded: false,
    },
    transport: {
      registered: false,
      externally_callable: false,
      method: null,
      route: null,
      runtime_reads: false,
      runtime_mutations: false,
      cache_reads: false,
      cache_writes: false,
      request_body_logging: false,
    },
    authority: {
      descriptive_only: true,
      route_registration_allowed: false,
      migration_execution_allowed: false,
      fresh_migration_allowed: false,
      writer_allowed: false,
      current_admission_allowed: false,
      current_pointer_written: false,
      paper_authorized: false,
      live_order_allowed: false,
    },
    blockers: blockers(state, payload.source.report22_decision),
  });
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test("verifies all four public states and both dry-run decisions", () => {
  for (const kind of ["NOT_SUPPLIED", "UNKNOWN", "PLAN_LISTED", "DRY_PASS", "DRY_BLOCK"]) {
    const response = candidateResponse(kind);
    const model = binding.presentReport22DateGridMigrationFromHttpCandidate(response);
    assert.equal(binding.verifyReport22DateGridMigrationHttpCandidateResponse(response), true);
    assert.equal(model.variant, "report22-date-grid");
    assert.equal(model.state, response.state);
    assert.equal(model.httpBinding.status, "VERIFIED_HTTP_CANDIDATE");
    assert.equal(model.httpBinding.response_hash_verified, true);
    assert.equal(model.httpBinding.current_admission_allowed, false);
  }
});

test("Python-compatible canonical response hash is required", () => {
  const response = candidateResponse();
  response.response_hash = "0".repeat(64);
  assert.equal(binding.verifyReport22DateGridMigrationHttpCandidateResponse(response), false);
  assert.equal(binding.presentReport22DateGridMigrationFromHttpCandidate(response).httpBinding.status, "UNKNOWN");
});

test("resealed payload authority escalation remains invalid", () => {
  const response = candidateResponse();
  response.payload.permission.paper_authorized = true;
  const resealed = seal(response);
  assert.equal(binding.verifyReport22DateGridMigrationHttpCandidateResponse(resealed), false);
  const model = binding.presentReport22DateGridMigrationFromHttpCandidate(resealed);
  assert.equal(model.variant, "unverified-contract");
  assert.equal(model.rail.at(-1).status, "LOCKED");
});

test("resealed response and payload state mismatch is rejected", () => {
  const response = candidateResponse("DRY_PASS");
  response.state = "PLAN_LISTED";
  response.facts.report22_evaluated = false;
  const resealed = seal(response);
  assert.equal(binding.verifyReport22DateGridMigrationHttpCandidateResponse(resealed), false);
});

test("facts blockers transport and lineage drift fail closed", () => {
  const mutations = [
    (value) => { value.facts.runtime_asset_accessed = true; },
    (value) => { value.blockers = []; },
    (value) => { value.transport.registered = true; },
    (value) => { value.lineage.source_hashes_embedded = true; },
    (value) => { value.authority.descriptive_only = 1; },
  ];
  for (const mutate of mutations) {
    const response = clone(candidateResponse());
    mutate(response);
    assert.equal(
      binding.verifyReport22DateGridMigrationHttpCandidateResponse(seal(response)),
      false,
    );
  }
});

test("extra keys are rejected even after a valid reseal", () => {
  const paths = [[], ["facts"], ["lineage"], ["transport"], ["authority"]];
  for (const pathParts of paths) {
    const response = clone(candidateResponse());
    let target = response;
    for (const part of pathParts) target = target[part];
    target.private_evidence = "x".repeat(64);
    assert.equal(
      binding.verifyReport22DateGridMigrationHttpCandidateResponse(seal(response)),
      false,
    );
  }
});

test("invalid response content is not reflected into renderer", () => {
  const response = candidateResponse();
  response.private_evidence = '<img src=x onerror="boom">';
  const target = { innerHTML: "" };
  const model = binding.renderReport22DateGridMigrationFromHttpCandidate(
    seal(response),
    target,
  );
  assert.equal(model.httpBinding.status, "UNKNOWN");
  assert.doesNotMatch(target.innerHTML, /<img|onerror|boom/);
  assert.match(target.innerHTML, /PUBLIC CONTRACT UNVERIFIED/);
});

test("render without target returns the bound pure model", () => {
  const model = binding.renderReport22DateGridMigrationFromHttpCandidate(
    candidateResponse("PLAN_LISTED"),
  );
  assert.equal(model.state, "PLAN_LISTED");
  assert.equal(model.httpBinding.payload_contract_verified, true);
  assert.equal(model.httpBinding.route_registered, false);
});

test("browser-global classic scripts verify without CommonJS constants", () => {
  const lockboardSource = fs.readFileSync(
    path.join(__dirname, "evidence_report22_date_grid_migration_lockboard.js"),
    "utf8",
  );
  const bindingSource = fs.readFileSync(
    path.join(__dirname, "evidence_report22_date_grid_migration_http_binding.js"),
    "utf8",
  );
  const context = vm.createContext({
    window: {},
    TextEncoder,
    responseJson: JSON.stringify(candidateResponse("DRY_PASS")),
  });
  vm.runInContext(lockboardSource, context, { filename: "lockboard.browser.js" });
  vm.runInContext(bindingSource, context, { filename: "binding.browser.js" });
  const result = vm.runInContext(
    `(() => {
      const response = JSON.parse(responseJson);
      const api = window.HakimiReport22DateGridMigrationHttpBinding;
      const model = api.presentReport22DateGridMigrationFromHttpCandidate(response);
      return {
        verified: api.verifyReport22DateGridMigrationHttpCandidateResponse(response),
        state: model.state,
        decision: model.decision,
        bindingStatus: model.httpBinding.status,
      };
    })()`,
    context,
  );

  assert.equal(result.verified, true);
  assert.equal(result.state, "DRY_RUN_VERIFIED");
  assert.equal(result.decision, "PASS");
  assert.equal(result.bindingStatus, "VERIFIED_HTTP_CANDIDATE");
});

test("binding remains unmounted and has no ambient DOM side effects", () => {
  const moduleSource = fs.readFileSync(
    path.join(__dirname, "evidence_report22_date_grid_migration_http_binding.js"),
    "utf8",
  );
  const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const indexSource = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.doesNotMatch(moduleSource, /DOMContentLoaded|querySelector|appendChild/);
  assert.doesNotMatch(appSource, /HakimiReport22DateGridMigrationHttpBinding|evidence_report22_date_grid_migration_http_binding/);
  assert.doesNotMatch(indexSource, /evidence_report22_date_grid_migration_http_binding/);
});

test("copy and exports provide no ready route or execution signal", () => {
  const model = binding.presentReport22DateGridMigrationFromHttpCandidate(
    candidateResponse("DRY_PASS"),
  );
  assert.doesNotMatch(JSON.stringify(model), /\bREADY\b|guaranteed|profit target/i);
  assert.deepEqual(Object.keys(binding).sort(), [
    "INTERFACE_STATUS",
    "RESPONSE_FINGERPRINT",
    "RESPONSE_SCHEMA",
    "presentReport22DateGridMigrationFromHttpCandidate",
    "renderReport22DateGridMigrationFromHttpCandidate",
    "verifyReport22DateGridMigrationHttpCandidateResponse",
  ]);
  assert.doesNotMatch(Object.keys(binding).join(" "), /register|execute|writer/i);
});
