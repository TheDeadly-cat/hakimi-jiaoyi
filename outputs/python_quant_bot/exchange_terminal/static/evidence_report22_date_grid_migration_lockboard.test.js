"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  SUMMARY_SCHEMA,
  CONTRACT_FINGERPRINT,
  presentReport22DateGridMigrationLockboard,
  renderReport22DateGridMigrationLockboard,
} = require("./evidence_report22_date_grid_migration_lockboard.js");

function validSummary(kind = "DRY_PASS") {
  const state = {
    NOT_SUPPLIED: {
      state: "NOT_SUPPLIED",
      assessmentContract: "NOT_SUPPLIED",
      mode: "NOT_SUPPLIED",
      reportContract: "NOT_SUPPLIED",
      decision: "NOT_SUPPLIED",
      gap: "ASSESSMENT_NOT_SUPPLIED",
      maturity: "NOT_SUPPLIED",
      evaluation: "NOT_SUPPLIED",
    },
    UNKNOWN: {
      state: "UNKNOWN",
      assessmentContract: "UNKNOWN",
      mode: "UNKNOWN",
      reportContract: "UNKNOWN",
      decision: "UNKNOWN",
      gap: "ASSESSMENT_UNKNOWN",
      maturity: "UNKNOWN",
      evaluation: "UNKNOWN",
    },
    PLAN_LISTED: {
      state: "PLAN_LISTED",
      assessmentContract: "VERIFIED",
      mode: "LIST",
      reportContract: "NOT_EVALUATED",
      decision: "NOT_EVALUATED",
      gap: "PLAN_ONLY",
      maturity: "PLAN_LISTED_NOT_EXECUTED",
      evaluation: "NOT_EVALUATED",
    },
    DRY_PASS: {
      state: "DRY_RUN_VERIFIED",
      assessmentContract: "VERIFIED",
      mode: "DRY_RUN",
      reportContract: "VERIFIED",
      decision: "PASS",
      gap: "DRY_RUN_ONLY",
      maturity: "DRY_RUN_VERIFIED_NOT_EXECUTED",
      evaluation: "VERIFIED",
    },
    DRY_BLOCK: {
      state: "DRY_RUN_VERIFIED",
      assessmentContract: "VERIFIED",
      mode: "DRY_RUN",
      reportContract: "VERIFIED",
      decision: "BLOCK",
      gap: "DRY_RUN_ONLY",
      maturity: "DRY_RUN_VERIFIED_NOT_EXECUTED",
      evaluation: "VERIFIED",
    },
  }[kind];

  return {
    schema_version: SUMMARY_SCHEMA,
    contract_fingerprint: CONTRACT_FINGERPRINT,
    axis_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
    source: {
      state: state.state,
      assessment_contract: state.assessmentContract,
      assessment_mode: state.mode,
      report22_contract: state.reportContract,
      report22_decision: state.decision,
    },
    gap: {
      state: state.gap,
      execution: "NOT_EXECUTED",
      runtime_mutations: "NONE",
      migration_execution: "NOT_ALLOWED",
      fresh_migration: "NOT_ALLOWED",
      formal_registry: "NOT_BOUND",
      writer: "NOT_AVAILABLE",
      current: "NOT_ADMITTED",
    },
    maturity: {
      state: state.maturity,
      report22_evaluation: state.evaluation,
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

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test("presents all four public states without permission drift", () => {
  const cases = [
    ["NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED"],
    ["UNKNOWN", "UNKNOWN", "UNKNOWN"],
    ["PLAN_LISTED", "PLAN_LISTED", "NOT_EVALUATED"],
    ["DRY_PASS", "DRY_RUN_VERIFIED", "PASS"],
  ];
  for (const [fixture, expectedState, expectedDecision] of cases) {
    const model = presentReport22DateGridMigrationLockboard(validSummary(fixture));
    assert.equal(model.variant, "report22-date-grid");
    assert.equal(model.state, expectedState);
    assert.equal(model.decision, expectedDecision);
    assert.deepEqual(model.flow.map((item) => item.key), [
      "SOURCE",
      "GAP",
      "MATURITY",
      "PERMISSION",
    ]);
    assert.equal(model.flow.at(-1).value, "Research only");
    assert.equal(model.rail.at(-1).status, "LOCKED");
  }
});

test("dry-run pass and block remain decisions rather than activation", () => {
  const passing = presentReport22DateGridMigrationLockboard(validSummary("DRY_PASS"));
  const blocked = presentReport22DateGridMigrationLockboard(validSummary("DRY_BLOCK"));
  assert.equal(passing.decision, "PASS");
  assert.equal(blocked.decision, "BLOCK");
  assert.equal(passing.rail[3].status, "ZERO");
  assert.equal(blocked.rail[3].status, "ZERO");
  assert.equal(passing.rail[4].status, "LOCKED");
  assert.equal(blocked.rail[4].status, "LOCKED");
  assert.doesNotMatch(`${passing.stateLabel} ${blocked.stateLabel}`, /\bREADY\b/i);
});

test("axis order fingerprint and schema drift fail closed", () => {
  const axis = validSummary();
  axis.axis_order = ["GAP", "SOURCE", "MATURITY", "PERMISSION"];
  const fingerprint = validSummary();
  fingerprint.contract_fingerprint = "drifted";
  const schema = validSummary();
  schema.schema_version = `${SUMMARY_SCHEMA}-drift`;
  for (const candidate of [axis, fingerprint, schema]) {
    const model = presentReport22DateGridMigrationLockboard(candidate);
    assert.equal(model.variant, "unverified-contract");
    assert.equal(model.state, "UNKNOWN");
  }
});

test("native aliases and permission escalation fail closed", () => {
  const permissionAlias = validSummary();
  permissionAlias.permission.descriptive_only = 1;
  const redactionAlias = validSummary();
  redactionAlias.redaction.raw_dates_exposed = 0;
  const escalation = validSummary();
  escalation.permission.current_admission_allowed = true;
  for (const candidate of [permissionAlias, redactionAlias, escalation]) {
    const model = presentReport22DateGridMigrationLockboard(candidate);
    assert.equal(model.variant, "unverified-contract");
    assert.equal(model.rail.at(-1).status, "LOCKED");
  }
});

test("extra keys at every public boundary invalidate the shape", () => {
  const paths = [[], ["source"], ["gap"], ["maturity"], ["permission"], ["redaction"]];
  for (const pathParts of paths) {
    const summary = clone(validSummary());
    let target = summary;
    for (const part of pathParts) target = target[part];
    target.private_evidence = "a".repeat(64);
    assert.equal(
      presentReport22DateGridMigrationLockboard(summary).variant,
      "unverified-contract",
    );
  }
});

test("cross-state resealing cannot retain a verified presentation", () => {
  const listedPass = validSummary("PLAN_LISTED");
  listedPass.source.report22_decision = "PASS";
  const dryListed = validSummary("DRY_PASS");
  dryListed.maturity.state = "PLAN_LISTED_NOT_EXECUTED";
  const executed = validSummary("DRY_PASS");
  executed.gap.execution = "EXECUTED";
  for (const candidate of [listedPass, dryListed, executed]) {
    assert.equal(
      presentReport22DateGridMigrationLockboard(candidate).variant,
      "unverified-contract",
    );
  }
});

test("renderer exposes the neutral ledger and lock rail", () => {
  const target = { innerHTML: "" };
  const model = renderReport22DateGridMigrationLockboard(
    validSummary("DRY_BLOCK"),
    target,
  );
  assert.equal(model.decision, "BLOCK");
  assert.match(target.innerHTML, /SOURCE/);
  assert.match(target.innerHTML, /GAP/);
  assert.match(target.innerHTML, /MATURITY/);
  assert.match(target.innerHTML, /PERMISSION/);
  assert.match(target.innerHTML, /REDACTED VERIFICATION LEDGER/);
  assert.match(target.innerHTML, /Stops before execution and current/);
  assert.match(target.innerHTML, /No migration, paper or live execution authority/);
  assert.doesNotMatch(target.innerHTML, /\bREADY\b|guaranteed|expected return|profit target/i);
});

test("untrusted values are neither reflected nor promoted", () => {
  const target = { innerHTML: "" };
  const summary = validSummary();
  summary.private_evidence = '<img src=x onerror="boom">';
  renderReport22DateGridMigrationLockboard(summary, target);
  assert.doesNotMatch(target.innerHTML, /<img|onerror|boom/);
  assert.match(target.innerHTML, /PUBLIC CONTRACT UNVERIFIED/);
  assert.match(target.innerHTML, /Execution remains locked/);
});

test("render without target returns a neutral model", () => {
  const model = renderReport22DateGridMigrationLockboard(validSummary("PLAN_LISTED"));
  assert.equal(model.state, "PLAN_LISTED");
  assert.equal(model.ledger.length, 4);
  assert.equal(model.rail.length, 5);
});

test("component remains unmounted with no ambient DOM side effects", () => {
  const moduleSource = fs.readFileSync(
    path.join(__dirname, "evidence_report22_date_grid_migration_lockboard.js"),
    "utf8",
  );
  const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const indexSource = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.doesNotMatch(moduleSource, /DOMContentLoaded|querySelector|appendChild/);
  assert.doesNotMatch(
    appSource,
    /HakimiReport22DateGridMigrationLockboard|evidence_report22_date_grid_migration_lockboard/,
  );
  assert.doesNotMatch(
    indexSource,
    /evidence_report22_date_grid_migration_lockboard/,
  );
});

test("stylesheet is responsive accessible and palette constrained", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_report22_date_grid_migration_lockboard.css"),
    "utf8",
  );
  assert.match(css, /--tdg22-source: #285f5a/);
  assert.match(css, /--tdg22-gap: #9a5437/);
  assert.match(css, /@media \(max-width: 920px\)/);
  assert.match(css, /@media \(max-width: 680px\)/);
  assert.match(css, /@media \(max-width: 440px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /@media \(forced-colors: active\)/);
  assert.doesNotMatch(css, /purple|violet|#(?:6f|7c|8b)\w{4}/i);
});

test("module exports only constants presenter and renderer", () => {
  const exported = Object.keys(
    require("./evidence_report22_date_grid_migration_lockboard.js"),
  ).sort();
  assert.deepEqual(exported, [
    "CONTRACT_FINGERPRINT",
    "SUMMARY_SCHEMA",
    "presentReport22DateGridMigrationLockboard",
    "renderReport22DateGridMigrationLockboard",
  ]);
  assert.doesNotMatch(exported.join(" "), /route|writer|current|activate|execute/i);
});
