"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const api = require("./evidence_formal_persistence_migration.js");

let passed = 0;
function test(name, body) {
  body();
  passed += 1;
  process.stdout.write(`ok ${passed} - ${name}\n`);
}

function summary(state = "READ_CONTRACT_COMPLETE_BLOCKED") {
  const shapes = {
    READ_CONTRACT_COMPLETE_BLOCKED: ["PREREGISTRATION_VERIFIED", "COMPLETE", "READ_CONTRACT_ONLY", true],
    READ_CONTRACT_BLOCKED: ["PREREGISTRATION_VERIFIED", "BLOCKED", "BLOCKED", false],
    NOT_SUPPLIED: ["NOT_SUPPLIED", "NOT_SUPPLIED", "NO_EVIDENCE", false],
    UNKNOWN: ["UNKNOWN", "UNKNOWN", "UNKNOWN", false],
  };
  const [sourceStatus, readStatus, maturityStatus, complete] = shapes[state];
  return {
    schema_version: api.SCHEMA_VERSION,
    static_build_fingerprint: api.STATIC_BUILD_FINGERPRINT,
    projection_state: state,
    source: { status: sourceStatus, protocol: "formal-persistence-v1", read_contract: readStatus },
    gap: {
      status: "OPEN",
      provider: "MISSING",
      durable_write_receipt: "MISSING",
      durable_reopen_receipt: "MISSING",
      session_separation: "MISSING",
      formal_persistence_asset: "MISSING",
      report_writer: "MISSING",
      current_pointer: "LOCKED",
      next_required_boundary: "AUTHORIZED_ISOLATED_PROVIDER_EVIDENCE",
    },
    maturity: {
      status: maturityStatus,
      read_contract_complete: complete,
      activation_prerequisite_count: 14,
      persistence_decision: "BLOCK",
    },
    permission: {
      status: "RESEARCH_ONLY",
      provider_implemented: false,
      formal_persistence_verified: false,
      formal_persistence_activation_allowed: false,
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

test("complete read remains a blocked persistence state", () => {
  const view = api.buildFormalPersistenceMigrationView(summary());
  assert.equal(view.state, "READ_CONTRACT_COMPLETE_BLOCKED");
  assert.equal(view.seal, "PERSISTENCE BLOCKED");
  assert.equal(view.stages.length, 9);
  assert.equal(view.stages[1].value, "COMPLETE");
  assert.equal(view.stages[2].value, "MISSING");
  assert.equal(view.stages[4].value, "MISSING");
  assert.equal(view.stages[7].value, "LOCKED");
  assert.equal(view.stages[8].value, "RESEARCH ONLY");
});

test("blocked read is distinct from unknown", () => {
  const view = api.buildFormalPersistenceMigrationView(summary("READ_CONTRACT_BLOCKED"));
  assert.equal(view.state, "READ_CONTRACT_BLOCKED");
  assert.equal(view.tone, "blocked");
  assert.equal(view.stages[0].value, "VERIFIED");
  assert.equal(view.stages[1].value, "BLOCKED");
});

test("not supplied keeps all downstream latches closed", () => {
  const view = api.buildFormalPersistenceMigrationView(summary("NOT_SUPPLIED"));
  assert.equal(view.state, "NOT_SUPPLIED");
  assert.equal(view.stages[0].value, "NOT SUPPLIED");
  assert.equal(view.stages[2].value, "MISSING");
  assert.equal(view.stages[7].value, "LOCKED");
});

test("schema drift fails closed to unknown", () => {
  const attacked = summary();
  attacked.schema_version = "future-schema";
  const view = api.buildFormalPersistenceMigrationView(attacked);
  assert.equal(view.state, "UNKNOWN");
  assert.equal(view.seal, "UNKNOWN INPUT");
});

test("truthy authority aliases fail closed", () => {
  for (const alias of [true, 1, "false", null]) {
    const attacked = summary();
    attacked.permission.formal_persistence_verified = alias;
    const view = api.buildFormalPersistenceMigrationView(attacked);
    assert.equal(view.state, "UNKNOWN");
    assert.equal(view.stages[8].value, "RESEARCH ONLY");
  }
});

test("state shape mismatch fails closed", () => {
  const attacked = summary();
  attacked.maturity.read_contract_complete = false;
  attacked.source.read_contract = "BLOCKED";
  assert.equal(api.buildFormalPersistenceMigrationView(attacked).state, "UNKNOWN");
});

test("private input fields are never reflected", () => {
  const attacked = summary();
  attacked.provider_artifact_hash = "a".repeat(64);
  attacked.registry_id = "PRIVATE-PERSISTENCE-ID";
  attacked.returns = [88];
  const serialized = JSON.stringify(api.buildFormalPersistenceMigrationView(attacked));
  assert.doesNotMatch(serialized, /a{64}|PRIVATE-PERSISTENCE-ID|"returns"/);
});

test("copy is neutral and permission-first", () => {
  for (const state of ["READ_CONTRACT_COMPLETE_BLOCKED", "READ_CONTRACT_BLOCKED", "NOT_SUPPLIED", "UNKNOWN"]) {
    const serialized = JSON.stringify(api.buildFormalPersistenceMigrationView(summary(state)));
    assert.doesNotMatch(serialized, /\bready\b|profit|buy signal|sell signal|trading enabled/i);
    assert.match(serialized, /RESEARCH ONLY/);
    assert.match(serialized, /Persistence activation remains blocked/);
  }
});

test("renderer uses text nodes only", () => {
  const source = fs.readFileSync(path.join(__dirname, "evidence_formal_persistence_migration.js"), "utf8");
  assert.doesNotMatch(source, /innerHTML|insertAdjacentHTML|document\.write/);
  assert.match(source, /textContent/);
  assert.match(source, /replaceChildren/);
});

test("lockboard is responsive and motion-safe", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_formal_persistence_migration.css"), "utf8");
  assert.match(css, /--fpm-petrol:\s*#174c58/);
  assert.match(css, /grid-template-columns:\s*repeat\(9/);
  assert.match(css, /data-key="REOPEN"/);
  assert.match(css, /Agency FB/);
  assert.match(css, /@media \(max-width: 620px\)/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.doesNotMatch(css, /\bInter\b|\bRoboto\b/);
});

process.stdout.write(`formal persistence migration: ${passed}/${passed} PASS\n`);
