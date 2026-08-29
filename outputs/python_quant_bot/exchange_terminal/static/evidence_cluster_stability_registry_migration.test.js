"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const api = require("./evidence_cluster_stability_registry_migration.js");

let passed = 0;

function test(name, body) {
  body();
  passed += 1;
  process.stdout.write(`ok ${passed} - ${name}\n`);
}

function summary(state = "CANDIDATE_BOUND") {
  const shapes = {
    CANDIDATE_BOUND: ["VERIFIED_CANDIDATE", "CANDIDATE_BOUND", true],
    CANDIDATE_EVIDENCE_BLOCKED: ["VERIFIED_BLOCK", "BLOCKED", false],
    NOT_SUPPLIED: ["NOT_SUPPLIED", "NO_EVIDENCE", false],
    UNKNOWN: ["UNKNOWN", "UNKNOWN", false],
  };
  const [sourceStatus, maturityStatus, candidateBound] = shapes[state];
  return {
    schema_version: api.SCHEMA_VERSION,
    static_build_fingerprint: api.STATIC_BUILD_FINGERPRINT,
    projection_state: state,
    source: {
      status: sourceStatus,
      protocol: "protocol-v9",
      report: "report-20",
      contract: "cluster-stability-registry-candidate-v1",
    },
    gap: {
      status: "OPEN",
      formal_registry: "MISSING",
      report_writer: "MISSING",
      current_pointer: "LOCKED",
      next_required_boundary: "FORMAL_REGISTRY_FINGERPRINT",
    },
    maturity: {
      status: maturityStatus,
      candidate_evidence_bound: candidateBound,
      candidate_only: true,
    },
    permission: {
      status: "RESEARCH_ONLY",
      formal_registry_bound: false,
      formal_registry_activation_allowed: false,
      writer_implemented: false,
      current_writer_activation_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    },
  };
}

test("bound candidate remains visibly non-formal", () => {
  const view = api.buildClusterStabilityRegistryMigrationView(summary());
  assert.equal(view.state, "CANDIDATE_BOUND");
  assert.equal(view.stamp, "CANDIDATE ONLY");
  assert.equal(view.stages.length, 7);
  assert.deepEqual(
    view.stages.map((stage) => stage.label),
    ["SOURCE", "CANDIDATE", "BINDING", "FORMAL", "WRITER", "CURRENT", "PERMISSION"],
  );
  assert.equal(view.stages[3].value, "MISSING");
  assert.equal(view.stages[4].value, "MISSING");
  assert.equal(view.stages[5].value, "LOCKED");
  assert.equal(view.stages[6].value, "RESEARCH ONLY");
});

test("verified blocking evidence is distinct from unknown", () => {
  const view = api.buildClusterStabilityRegistryMigrationView(
    summary("CANDIDATE_EVIDENCE_BLOCKED"),
  );
  assert.equal(view.state, "CANDIDATE_EVIDENCE_BLOCKED");
  assert.equal(view.tone, "blocked");
  assert.equal(view.stages[0].value, "VERIFIED BLOCK");
  assert.equal(view.stages[2].value, "BLOCK");
});

test("not supplied candidate keeps every downstream boundary closed", () => {
  const view = api.buildClusterStabilityRegistryMigrationView(summary("NOT_SUPPLIED"));
  assert.equal(view.state, "NOT_SUPPLIED");
  assert.equal(view.stages[0].value, "NOT SUPPLIED");
  assert.equal(view.stages[3].value, "MISSING");
  assert.equal(view.stages[5].value, "LOCKED");
});

test("invalid schema fails closed to unknown", () => {
  const attacked = summary();
  attacked.schema_version = "future-schema";
  const view = api.buildClusterStabilityRegistryMigrationView(attacked);
  assert.equal(view.state, "UNKNOWN");
  assert.equal(view.stamp, "UNKNOWN INPUT");
  assert.equal(view.stages[5].value, "LOCKED");
});

test("truthy authority aliases fail closed", () => {
  for (const alias of [true, 1, "false", null]) {
    const attacked = summary();
    attacked.permission.formal_registry_bound = alias;
    const view = api.buildClusterStabilityRegistryMigrationView(attacked);
    assert.equal(view.state, "UNKNOWN");
    assert.equal(view.stages[6].value, "RESEARCH ONLY");
  }
});

test("state and evidence-shape mismatch fails closed", () => {
  const attacked = summary();
  attacked.maturity.candidate_evidence_bound = false;
  attacked.source.status = "VERIFIED_BLOCK";
  const view = api.buildClusterStabilityRegistryMigrationView(attacked);
  assert.equal(view.state, "UNKNOWN");
});

test("view model never copies private input fields", () => {
  const attacked = summary();
  attacked.registry_id = "PRIVATE-REGISTRY-IDENTITY";
  attacked.registry_source_hash = "a".repeat(64);
  attacked.returns = [99];
  const serialized = JSON.stringify(
    api.buildClusterStabilityRegistryMigrationView(attacked),
  );
  assert.doesNotMatch(serialized, /PRIVATE-REGISTRY-IDENTITY/);
  assert.doesNotMatch(serialized, /a{64}/);
  assert.doesNotMatch(serialized, /"returns"/);
});

test("copy remains neutral and permission-first", () => {
  for (const state of [
    "CANDIDATE_BOUND",
    "CANDIDATE_EVIDENCE_BLOCKED",
    "NOT_SUPPLIED",
    "UNKNOWN",
  ]) {
    const serialized = JSON.stringify(
      api.buildClusterStabilityRegistryMigrationView(summary(state)),
    );
    assert.doesNotMatch(serialized, /\bready\b|profit|buy signal|sell signal|trading enabled/i);
    assert.match(serialized, /RESEARCH ONLY/);
    assert.match(serialized, /Formal registry fingerprint/);
  }
});

test("renderer uses text nodes rather than HTML injection", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_cluster_stability_registry_migration.js"),
    "utf8",
  );
  assert.doesNotMatch(source, /innerHTML|insertAdjacentHTML|document\.write/);
  assert.match(source, /textContent/);
  assert.match(source, /replaceChildren/);
});

test("visual contract is responsive and motion-safe", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_cluster_stability_registry_migration.css"),
    "utf8",
  );
  assert.match(css, /--csr-survey:\s*#2e7188/);
  assert.match(css, /grid-template-columns:\s*repeat\(7/);
  assert.match(css, /DIN Condensed/);
  assert.match(css, /@media \(max-width: 520px\)/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.doesNotMatch(css, /\bInter\b|\bRoboto\b/);
});

process.stdout.write(`cluster stability registry migration: ${passed}/${passed} PASS\n`);
