"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const subject = require("./provider_identity_artifact_transparency_card_v1.js");
const strictJson = require("./strict_canonical_json_v1.js");

const hash = (character) => character.repeat(64);

function fixture() {
  return strictJson.sealDocument({
    authority: { artifact_promotion_allowed: false, current_admission_allowed: false, current_pointer_written: false, descriptive_only: true, live_order_allowed: false, paper_authorized: false, parameter_selection_allowed: false, public_availability_promotion_allowed: false },
    axes: [
      { axis: "SOURCE", detail: "172 supplied bytes match catalog hashes and sizes.", headline: "4 supplied artifacts match the catalog", signal: "VERIFIED_LOCAL", state: "LOCAL CONTENT BOUND" },
      { axis: "GAP", detail: "Public reachability and independent operation remain unproven.", headline: "External log and network retrieval remain unproven", signal: "BLOCKED", state: "PUBLIC AVAILABILITY OPEN" },
      { axis: "MATURITY", detail: "Checkpoint tree size 4 and matching result roots.", headline: "4 inclusions and two observer transcripts", signal: "PARTIAL", state: "SIGNED CLAIM SET" },
      { axis: "PERMISSION", detail: "Descriptive only.", headline: "No promotion or trading authority", signal: "LOCKED", state: "RESEARCH ONLY" }
    ],
    axis_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
    blockers: ["EXTERNAL_LOG_GOVERNANCE_UNPROVEN", "PUBLIC_ARTIFACT_AVAILABILITY_UNPROVEN", "TRADING_AUTHORITY_NOT_GRANTED"],
    display_state: subject.constants.DISPLAY_STATE,
    facts: { append_only_consistency_verified: true, catalog_scope_verified: true, dual_observer_claims_verified: true, dual_observer_result_agreement_verified: true, external_log_trust_verified: false, external_persistence_verified: false, external_time_truth_verified: false, inclusion_set_verified: true, local_artifact_content_verified: true, observer_independence_verified: false, profitability_verified: false, public_availability_verified: false, result_available: true, signed_checkpoint_verified: true, source_evaluation_verified: true },
    lineage: { artifact_catalog_root_hash: hash("a"), observer_a_receipt_hash: hash("b"), observer_b_receipt_hash: hash("c"), observer_result_transcript_root_hash: hash("d"), registration_receipt_hash: hash("e"), source_evaluation_receipt_hash: hash("f"), transparency_checkpoint_hash: hash("1"), transparency_checkpoint_root_hash: hash("2") },
    presentation_status: "UNMOUNTED_CANDIDATE",
    schema_version: subject.constants.ENVELOPE_SCHEMA,
    source_evaluation_fingerprint: subject.constants.SOURCE_FINGERPRINT,
    source_evaluation_schema: subject.constants.SOURCE_SCHEMA,
    static_fingerprint: subject.constants.ENVELOPE_FINGERPRINT,
    summary: { artifact_count: 4, checkpoint_tree_size: 4, observer_count: 2, signed_retrieval_claim_count: 8, total_payload_bytes: 172, verified_inclusion_count: 4 }
  }, "presentation_hash");
}

const reseal = (value) => strictJson.sealDocument(value, "presentation_hash");
const buildModel = (value, expectedHash = value.presentation_hash) => (
  subject.buildProviderIdentityArtifactTransparencyModelV1(value, expectedHash)
);
const createCard = (value, documentRef, expectedHash = value.presentation_hash) => (
  subject.createProviderIdentityArtifactTransparencyCardV1(value, documentRef, expectedHash)
);

class FakeElement {
  constructor(tagName) { this.tagName = tagName; this.className = ""; this.textContent = ""; this.children = []; this.dataset = {}; }
  appendChild(child) { this.children.push(child); return child; }
}

const fakeDocument = { createElement: (tagName) => new FakeElement(tagName) };
const textTree = (node) => [node.textContent].concat(node.children.flatMap(textTree)).join(" ");

function fixtureInContext(context) {
  context.fixtureJson = JSON.stringify(fixture());
  return vm.runInContext("JSON.parse(fixtureJson)", context);
}

test("exports detached model and DOM factories", () => {
  assert.deepEqual(Object.keys(subject).sort(), ["buildProviderIdentityArtifactTransparencyModelV1", "constants", "contractTestHooks", "createProviderIdentityArtifactTransparencyCardV1"]);
});

test("builds exact local-evidence external-gap model", () => {
  const model = buildModel(fixture());
  assert.equal(model.statusLabel, "LOCAL EVIDENCE / EXTERNAL GAP");
  assert.equal(model.artifactCount, 4);
  assert.equal(model.inclusionCount, 4);
  assert.equal(model.observerCount, 2);
  assert.equal(model.retrievalClaimCount, 8);
  assert.deepEqual(model.axes.map((axis) => axis.axis), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("rejects envelope, count, truth, and permission drift", () => {
  const extra = fixture(); extra.extra = true;
  assert.throws(() => buildModel(reseal(extra)), /fields are not exact/);
  const count = fixture(); count.summary.signed_retrieval_claim_count = 7;
  assert.throws(() => buildModel(reseal(count)), /retrieval claim count drift/);
  const truth = fixture(); truth.facts.public_availability_verified = true;
  assert.throws(() => buildModel(reseal(truth)), /external facts/);
  const permission = fixture(); permission.authority.paper_authorized = true;
  assert.throws(() => buildModel(reseal(permission)), /descriptive and locked/);
});

test("requires an independently supplied expected hash", () => {
  const value = fixture();
  assert.throws(() => subject.buildProviderIdentityArtifactTransparencyModelV1(value), /expected presentation hash is required/);
  assert.throws(() => buildModel(value, "0".repeat(64)), /expected presentation hash mismatch/);
});

test("rejects coherently resealed drift against the original pin", () => {
  const original = fixture();
  const expectedHash = original.presentation_hash;
  original.axes[0].headline = "Coherently resealed replacement";
  assert.throws(() => buildModel(reseal(original), expectedHash), /expected presentation hash mismatch/);
});

test("rejects unsealed presentation tampering before projection", () => {
  const value = fixture(); value.summary.total_payload_bytes += 1;
  assert.throws(() => buildModel(value), /presentation hash mismatch/);
});

test("rejects observer identity collapse", () => {
  const value = fixture(); value.lineage.observer_b_receipt_hash = value.lineage.observer_a_receipt_hash;
  assert.throws(() => buildModel(reseal(value)), /observer receipts/);
});

test("creates semantic observatory card without active-language leakage", () => {
  const card = createCard(fixture(), fakeDocument);
  assert.equal(card.tagName, "article");
  assert.equal(card.className, "pia-transparency-card");
  const text = textTree(card);
  for (const label of ["Availability Evidence Plate", "LOCAL CONTENT BOUND", "PUBLIC AVAILABILITY OPEN", "SIGNED CLAIM SET", "RESEARCH ONLY"]) assert.match(text, new RegExp(label));
  assert.doesNotMatch(text, /\bREADY\b|profit/i);
  assert.equal(Object.prototype.hasOwnProperty.call(card, "innerHTML"), false);
});

test("keeps untrusted axis text as textContent", () => {
  const value = fixture(); value.axes[0].headline = "<img src=x onerror=alert(1)>";
  const card = createCard(reseal(value), fakeDocument);
  assert.match(textTree(card), /<img src=x onerror=alert\(1\)>/);
  assert.equal(Object.prototype.hasOwnProperty.call(card, "innerHTML"), false);
});

test("does not expose payloads urls keys or signatures", () => {
  const text = JSON.stringify(buildModel(fixture())).toLowerCase();
  for (const forbidden of ["content_base64url", "https://", "public_key", "signature"]) assert.doesNotMatch(text, new RegExp(forbidden));
});

test("requires a document factory", () => {
  assert.throws(() => createCard(fixture(), {}), /document.createElement is required/);
});

test("browser-global branch exposes the same API", () => {
  const context = {};
  vm.createContext(context);
  for (const filename of ["strict_canonical_json_v1.js", "provider_identity_artifact_transparency_card_v1.js"]) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, filename), "utf8"), context);
  }
  const api = context.HakimiProviderIdentityArtifactTransparencyCardV1;
  assert.equal(typeof api.buildProviderIdentityArtifactTransparencyModelV1, "function");
  const browserFixture = fixtureInContext(context);
  assert.equal(api.buildProviderIdentityArtifactTransparencyModelV1(browserFixture, browserFixture.presentation_hash).artifactCount, 4);
});

test("browser-global card fails closed without canonical verifier", () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "provider_identity_artifact_transparency_card_v1.js"), "utf8"), context);
  const browserFixture = fixtureInContext(context);
  assert.throws(
    () => context.HakimiProviderIdentityArtifactTransparencyCardV1.buildProviderIdentityArtifactTransparencyModelV1(browserFixture, browserFixture.presentation_hash),
    /strict canonical verifier is required/
  );
});

test("CSS remains scoped, responsive, and motion-safe", () => {
  const css = fs.readFileSync(path.join(__dirname, "provider_identity_artifact_transparency_card_v1.css"), "utf8");
  assert.match(css, /\.pia-transparency-card\s*\{/);
  assert.match(css, /@media \(max-width: 560px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.doesNotMatch(css, /(^|\n)\s*(body|html|:root)\s*\{/);
});
