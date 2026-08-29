"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const subject = require("./provider_identity_claim_coverage_card_v1.js");

const hash = (character) => character.repeat(64);

function fixture() {
  return {
    authority: { current_admission_allowed: false, current_pointer_written: false, descriptive_only: true, freshness_truth_promotion_allowed: false, live_order_allowed: false, paper_authorized: false, replay_absence_promotion_allowed: false, uniqueness_truth_promotion_allowed: false },
    axes: [
      { axis: "SOURCE", detail: "Signed claims bind the latest checkpoint.", headline: "Detached occurrence and time claims", signal: "VERIFIED_CLAIMS", state: "SIGNED CLAIMS" },
      { axis: "GAP", detail: "External witness authority remains unproven.", headline: "Witness authority and index coverage unproven", signal: "BLOCKED", state: "EXTERNAL TRUST OPEN" },
      { axis: "MATURITY", detail: "Registered tree range 1 to 3.", headline: "3 consecutive checkpoint claims", signal: "PARTIAL", state: "BOUNDED PREFIX" },
      { axis: "PERMISSION", detail: "Descriptive research only.", headline: "No admission or trading authority", signal: "LOCKED", state: "RESEARCH ONLY" }
    ],
    axis_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
    blockers: ["EXTERNAL_OCCURRENCE_INDEX_COMPLETENESS_UNPROVEN", "TRADING_AUTHORITY_NOT_GRANTED"],
    display_state: subject.constants.DISPLAY_STATE,
    facts: { assertion_uniqueness_verified: false, bounded_prefix_verified: true, complete_history_verified: false, complete_scan_claim_verified: true, external_occurrence_provider_trust_attested: false, external_time_authority_trust_attested: false, freshness_verified: false, longitudinal_coverage_evaluation_verified: true, replay_absence_verified: false, result_available: true, signed_claim_evaluation_verified: true, time_window_claim_verified: true },
    lineage: { coverage_evaluation_receipt_hash: hash("b"), coverage_registration_receipt_hash: hash("c"), first_checkpoint_hash: hash("d"), first_source_evaluation_receipt_hash: hash("e"), last_checkpoint_hash: hash("f"), last_source_evaluation_receipt_hash: hash("1"), signed_claim_evaluation_receipt_hash: hash("1"), source_evidence_registration_receipt_hash: hash("2") },
    presentation_hash: hash("3"),
    presentation_status: "UNMOUNTED_CANDIDATE",
    schema_version: subject.constants.ENVELOPE_SCHEMA,
    source_coverage_fingerprint: subject.constants.COVERAGE_FINGERPRINT,
    source_coverage_schema: subject.constants.COVERAGE_SCHEMA,
    source_signed_claim_fingerprint: subject.constants.SIGNED_CLAIM_FINGERPRINT,
    source_signed_claim_schema: subject.constants.SIGNED_CLAIM_SCHEMA,
    static_fingerprint: subject.constants.ENVELOPE_FINGERPRINT,
    summary: { assertion_leaf_index: 0, assertion_receipt_hash: hash("4"), checkpoint_tree_size: 3, coverage_end_tree_size: 3, coverage_evaluation_count: 3, coverage_start_tree_size: 1, maximum_reference_time_gap_ms: 100, occurrence_provider_id: "synthetic-occurrence-provider-v1", reference_time_ms_claim: 1230, replay_registry_id: "synthetic-registry-v1", scan_completed_at_ms_claim: 1220, time_authority_id: "synthetic-time-authority-v1" }
  };
}

class FakeElement {
  constructor(tagName) { this.tagName = tagName; this.className = ""; this.textContent = ""; this.children = []; this.dataset = {}; }
  appendChild(child) { this.children.push(child); return child; }
}

const fakeDocument = { createElement: (tagName) => new FakeElement(tagName) };
const textTree = (node) => [node.textContent].concat(node.children.flatMap(textTree)).join(" ");

test("exports detached model and DOM factories", () => {
  assert.deepEqual(Object.keys(subject).sort(), ["buildProviderIdentityClaimCoverageModelV1", "constants", "contractTestHooks", "createProviderIdentityClaimCoverageCardV1"]);
});

test("builds exact four-axis bounded-prefix model", () => {
  const model = subject.buildProviderIdentityClaimCoverageModelV1(fixture());
  assert.equal(model.statusLabel, "SIGNED CLAIMS / TRUST OPEN");
  assert.deepEqual(model.axes.map((axis) => axis.axis), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(model.coverageRange, "1 to 3");
  assert.equal(model.evaluationCount, 3);
  assert.equal(model.permissionLabel, "DESCRIPTIVE RESEARCH ONLY");
});

test("rejects envelope, truth, and permission drift", () => {
  const extra = fixture(); extra.extra = true;
  assert.throws(() => subject.buildProviderIdentityClaimCoverageModelV1(extra), /fields are not exact/);
  const truth = fixture(); truth.facts.assertion_uniqueness_verified = true;
  assert.throws(() => subject.buildProviderIdentityClaimCoverageModelV1(truth), /truth-bearing facts/);
  const permission = fixture(); permission.authority.paper_authorized = true;
  assert.throws(() => subject.buildProviderIdentityClaimCoverageModelV1(permission), /descriptive and locked/);
});

test("creates scoped semantic card without active-language leakage", () => {
  const card = subject.createProviderIdentityClaimCoverageCardV1(fixture(), fakeDocument);
  assert.equal(card.tagName, "article");
  assert.equal(card.className, "pif-coverage-card");
  const text = textTree(card);
  for (const label of ["Claim Coverage Ledger", "SIGNED CLAIMS", "EXTERNAL TRUST OPEN", "BOUNDED PREFIX", "RESEARCH ONLY"]) assert.match(text, new RegExp(label));
  assert.doesNotMatch(text, /\bREADY\b/i);
  assert.equal(Object.prototype.hasOwnProperty.call(card, "innerHTML"), false);
});

test("keeps untrusted identity text as textContent", () => {
  const value = fixture(); value.summary.replay_registry_id = "<img src=x onerror=alert(1)>";
  const card = subject.createProviderIdentityClaimCoverageCardV1(value, fakeDocument);
  assert.match(textTree(card), /<img src=x onerror=alert\(1\)>/);
  assert.equal(Object.prototype.hasOwnProperty.call(card, "innerHTML"), false);
});

test("requires a document factory", () => {
  assert.throws(() => subject.createProviderIdentityClaimCoverageCardV1(fixture(), {}), /document.createElement is required/);
});

test("browser-global branch exposes the same API", () => {
  const source = fs.readFileSync(path.join(__dirname, "provider_identity_claim_coverage_card_v1.js"), "utf8");
  const context = {};
  vm.createContext(context);
  vm.runInContext(source, context);
  const api = context.HakimiProviderIdentityClaimCoverageCardV1;
  assert.equal(typeof api.buildProviderIdentityClaimCoverageModelV1, "function");
  assert.equal(api.buildProviderIdentityClaimCoverageModelV1(JSON.parse(JSON.stringify(fixture()))).evaluationCount, 3);
});

test("CSS remains scoped, responsive, and motion-safe", () => {
  const css = fs.readFileSync(path.join(__dirname, "provider_identity_claim_coverage_card_v1.css"), "utf8");
  assert.match(css, /\.pif-coverage-card\s*\{/);
  assert.match(css, /@media \(max-width: 620px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.doesNotMatch(css, /(^|\n)\s*(body|html|:root)\s*\{/);
});
