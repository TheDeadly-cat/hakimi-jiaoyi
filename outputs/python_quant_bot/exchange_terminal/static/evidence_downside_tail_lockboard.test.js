"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const api = require("./evidence_downside_tail_lockboard.js");

function summary(kind = "PASS") {
  const observed = kind === "PASS" || kind === "BLOCK";
  const notSupplied = kind === "NOT_SUPPLIED";
  const candidateBlocked = kind === "CANDIDATE_BLOCKED";
  const sourceState = observed ? "OBSERVED" : notSupplied ? "NOT_SUPPLIED" : "UNKNOWN";
  const decision = observed ? kind : candidateBlocked ? "BLOCK" : notSupplied ? "NOT_SUPPLIED" : "UNKNOWN";
  return {
    schema_version: api.SUMMARY_SCHEMA,
    static_fingerprint: api.STATIC_FINGERPRINT,
    source: {
      state: sourceState,
      evidence_contract: "PREREGISTERED_DOWNSIDE_TAIL_CANDIDATE_V1",
      observation_count: observed ? 60 : null,
      tail_event_count: observed ? 12 : null,
      cross_stratum_pair_count: observed ? 3 : null,
      coupled_pair_count: kind === "BLOCK" ? 1 : observed ? 0 : null,
    },
    gap: {
      gate_decision: decision,
      gate_reason: kind === "PASS" ? "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP" : kind === "BLOCK" ? "DOWNSIDE_TAIL_COUPLING_DETECTED" : candidateBlocked ? "SOURCE_EVALUATION_UNKNOWN" : notSupplied ? "NOT_SUPPLIED" : "SOURCE_CONTRACT_UNKNOWN",
      binding_status: observed ? "CANDIDATE_BOUND" : candidateBlocked ? "CANDIDATE_BLOCKED" : notSupplied ? "NOT_SUPPLIED" : "UNKNOWN",
      protocol_status: observed || candidateBlocked ? "VERIFIED_CANDIDATE" : notSupplied ? "NOT_SUPPLIED" : "UNKNOWN",
    },
    maturity: {
      state: observed ? "CANDIDATE_BOUND_NOT_FORMAL" : candidateBlocked ? "CANDIDATE_BLOCKED_NOT_FORMAL" : notSupplied ? "NOT_SUPPLIED" : "UNKNOWN",
      formal_registration_status: "NOT_ESTABLISHED",
      current_status: "LOCKED",
    },
    permission: {
      descriptive_only: true, independence_proven: false, count_as_independent_allowed: false,
      candidate_binding_activation_allowed: false, formal_report_binding_allowed: false,
      formal_registry_activation_allowed: false, profitability_claim_allowed: false,
      current_admission_allowed: false, current_writer_activation_allowed: false,
      paper_authorized: false, live_order_allowed: false,
    },
    redaction: {
      protocol_hash_exposed: false, registration_hash_exposed: false, evaluation_hash_exposed: false,
      consumer_verification_hash_exposed: false, assessment_hash_exposed: false,
      identity_set_hash_exposed: false, stratum_assignment_hash_exposed: false,
      observation_ids_exposed: false, returns_exposed: false, pair_identities_exposed: false,
      strata_exposed: false, overlap_values_exposed: false, p_values_exposed: false,
      profitability_metrics_exposed: false,
    },
  };
}

test("observed pass remains candidate-only with every permission locked", () => {
  const model = api.presentDownsideTailLockboard(summary("PASS"));
  assert.equal(model.kind, "OBSERVED_PASS");
  assert.equal(model.nodes[2].value, "CANDIDATE / NOT FORMAL");
  assert.equal(model.nodes[3].value, "ALL PATHS LOCKED");
  assert.deepEqual(model.metrics.map((item) => item[1]), ["60", "12", "3", "0"]);
});

test("observed block remains visible rather than degrading to unknown", () => {
  const model = api.presentDownsideTailLockboard(summary("BLOCK"));
  assert.equal(model.kind, "OBSERVED_BLOCK");
  assert.equal(model.nodes[1].value, "BLOCK");
  assert.equal(model.metrics[3][1], "1");
});

test("candidate blocked is distinct from unknown", () => {
  const blocked = api.presentDownsideTailLockboard(summary("CANDIDATE_BLOCKED"));
  const unknown = api.presentDownsideTailLockboard(summary("UNKNOWN"));
  assert.equal(blocked.kind, "CANDIDATE_BLOCKED");
  assert.equal(unknown.kind, "UNKNOWN");
  assert.notEqual(blocked.title, unknown.title);
});

test("not supplied is distinct from invalid supplied", () => {
  assert.equal(api.presentDownsideTailLockboard(summary("NOT_SUPPLIED")).kind, "NOT_SUPPLIED");
  assert.equal(api.presentDownsideTailLockboard({}).kind, "UNKNOWN");
});

test("numeric authority aliases fail closed", () => {
  const value = summary("PASS");
  value.permission.paper_authorized = 0;
  assert.equal(api.presentDownsideTailLockboard(value).kind, "UNKNOWN");
});

test("fingerprint and count drift fail closed", () => {
  const fingerprint = summary("PASS");
  fingerprint.static_fingerprint += "-drift";
  assert.equal(api.presentDownsideTailLockboard(fingerprint).kind, "UNKNOWN");
  const counts = summary("PASS");
  counts.source.coupled_pair_count = 1;
  assert.equal(api.presentDownsideTailLockboard(counts).kind, "UNKNOWN");
});

test("extra untrusted fields are not reflected", () => {
  const value = summary("PASS");
  value.source.untrusted = "PRIVATE-DO-NOT-REFLECT";
  const encoded = JSON.stringify(api.presentDownsideTailLockboard(value));
  assert.equal(encoded.includes("PRIVATE-DO-NOT-REFLECT"), false);
  assert.equal(JSON.parse(encoded).kind, "UNKNOWN");
});

class FakeElement {
  constructor(ownerDocument, tag) {
    this.ownerDocument = ownerDocument;
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.className = "";
    const properties = new Map();
    this.style = {
      setProperty(name, value) { properties.set(name, String(value)); },
      getPropertyValue(name) { return properties.get(name) || ""; },
    };
  }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
}

test("renderer uses text nodes and remains target-scoped", () => {
  const documentRef = { createElement(tag) { return new FakeElement(documentRef, tag); } };
  const target = new FakeElement(documentRef, "target");
  const model = api.renderDownsideTailLockboard(summary("BLOCK"), target);
  assert.equal(model.kind, "OBSERVED_BLOCK");
  assert.equal(target.children.length, 1);
  assert.equal(target.children[0].children[1].children[0].style.getPropertyValue("--dt-index"), "0");
  const source = fs.readFileSync(path.join(__dirname, "evidence_downside_tail_lockboard.js"), "utf8");
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("document.querySelector"), false);
});

test("render without a target returns the pure model", () => {
  assert.equal(api.renderDownsideTailLockboard(summary("PASS")).kind, "OBSERVED_PASS");
});

test("module load has no ambient document dependency", () => {
  const source = fs.readFileSync(path.join(__dirname, "evidence_downside_tail_lockboard.js"), "utf8");
  assert.equal(/\bdocument\./.test(source), false);
  assert.equal(/DOMContentLoaded|appendChild\(.*document/.test(source), false);
});

test("stylesheet is responsive, motion-safe, and uses the project paper palette", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_downside_tail_lockboard.css"), "utf8");
  assert.match(css, /--dt-paper:\s*#f2ead7/i);
  assert.match(css, /--dt-block:\s*#a33d2d/i);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(max-width: 430px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
});

test("copy never presents profit, execution, or activation authority", () => {
  for (const kind of ["PASS", "BLOCK", "CANDIDATE_BLOCKED", "UNKNOWN", "NOT_SUPPLIED"]) {
    const text = JSON.stringify(api.presentDownsideTailLockboard(summary(kind))).toLowerCase();
    assert.equal(/guaranteed|profitable|execute trade|activation allowed|\bready\b/.test(text), false);
    assert.match(text, /locked/);
  }
});
