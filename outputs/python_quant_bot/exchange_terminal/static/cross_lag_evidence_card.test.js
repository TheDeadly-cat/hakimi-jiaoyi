"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const api = require("./cross_lag_evidence_card.js");

const { buildCrossLagPresentationModel, constants, contractTestHooks, createCrossLagEvidenceCard } = api;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

const AUTHORITY = Object.freeze({
  candidate_binding_activation_allowed: false,
  count_as_independent_allowed: false,
  current_admission_allowed: false,
  current_pointer_written: false,
  current_writer_activation_allowed: false,
  descriptive_only: true,
  formal_preregistration_bound: false,
  formal_registry_activation_allowed: false,
  formal_registry_written: false,
  independence_proven: false,
  live_order_allowed: false,
  paper_authorized: false,
  profitability_claim_allowed: false,
  sequence_order_attested: false,
  strata_timing_attested: false,
});

const STATE_DATA = Object.freeze({
  NOT_SUPPLIED: Object.freeze({
    analytic_policy_hash: "",
    blockers: ["CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED"],
    c2_assessment_hash: "",
    consumer_receipt_hash: "",
    cross_stratum_pair_count: 0,
    dependent_test_count: 0,
    direction_contract_hash: "",
    evaluation_hash: "",
    gap_axis: "SOURCE_NOT_SUPPLIED",
    gate_decision: "UNKNOWN",
    gate_reason: "UNKNOWN",
    lag_test_count: 0,
    maturity_axis: "NOT_EVALUATED",
    max_adjusted_absolute_lower: "0",
    preregistration_adapter_binding_hash: "",
    protocol_registration_hash: "",
    public_summary_hash: "75945f58dfd191780c91fc48ca330328102983a4827694e34b118073204801f8",
    source_axis: "NOT_SUPPLIED",
    stratum_assignment_hash: "",
    verified: false,
  }),
  UNKNOWN: Object.freeze({
    analytic_policy_hash: "",
    blockers: ["CROSS_LAG_PROTOCOL_EVIDENCE_INVALID"],
    c2_assessment_hash: "",
    consumer_receipt_hash: "",
    cross_stratum_pair_count: 0,
    dependent_test_count: 0,
    direction_contract_hash: "",
    evaluation_hash: "",
    gap_axis: "SOURCE_INVALID",
    gate_decision: "UNKNOWN",
    gate_reason: "UNKNOWN",
    lag_test_count: 0,
    maturity_axis: "UNKNOWN",
    max_adjusted_absolute_lower: "0",
    preregistration_adapter_binding_hash: "",
    protocol_registration_hash: "",
    public_summary_hash: "427e36916215299f32b547aa0a434b2590a069dba0b372802f0b20cc783d0827",
    source_axis: "UNKNOWN",
    stratum_assignment_hash: "",
    verified: false,
  }),
  OBSERVED_PASS: Object.freeze({
    analytic_policy_hash: "f8078e3646e7257f6afdb02f5533e96be99b9a66272d183af9b3071c8d5aa80a",
    blockers: ["CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED", "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED"],
    c2_assessment_hash: "a104e44424b4e7dc199a64cb3e5fb903d7fae09d7a4cc937f315a68be05c1886",
    consumer_receipt_hash: "4ade36cd5b51bc81f469dc8536154f27f0b3f1c24e98fc52b05a76e335f3a81c",
    cross_stratum_pair_count: 7,
    dependent_test_count: 0,
    direction_contract_hash: "afbe76f73f151da1c357c940b1ea8b1b480784e80f65ded19c2faa94aa560a87",
    evaluation_hash: "6df7db185f4c2222d461e7dabc4a38ab8aea8c2358ded8405808d09b3a88f95c",
    gap_axis: "SEQUENCE_ORDER_UNATTESTED",
    gate_decision: "PASS",
    gate_reason: "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_DETECTED",
    lag_test_count: 28,
    maturity_axis: "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL",
    max_adjusted_absolute_lower: "0",
    preregistration_adapter_binding_hash: "a02506d2fa53502589f753f031c221ff1737af15d8150300d4ffda5e23037e72",
    protocol_registration_hash: "df7b13dbbaa583e0e06bb26ce1eb6c56ca93cfc439f33d56f0a91d7403147568",
    public_summary_hash: "16a719b916ec1da4402d6af595980fbe42852414750e6e87d9f52e7e1e987dfb",
    source_axis: "VERIFIED_C2",
    stratum_assignment_hash: "d683ee350d06d2564800d320dfe7a069dd61731129559bf6e9f5dec61e1cf39a",
    verified: true,
  }),
  OBSERVED_BLOCK: Object.freeze({
    analytic_policy_hash: "f8078e3646e7257f6afdb02f5533e96be99b9a66272d183af9b3071c8d5aa80a",
    blockers: ["CROSS_LAG_DEPENDENCE_DETECTED", "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED", "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED"],
    c2_assessment_hash: "80b4e54f2515a7131903fe1d34ebc6422475c8936b64dd6f23affc1d10ba845f",
    consumer_receipt_hash: "454143cdf8008dbf6ce758c72d9aa638576c3225b645369712db93309f8223e4",
    cross_stratum_pair_count: 7,
    dependent_test_count: 1,
    direction_contract_hash: "afbe76f73f151da1c357c940b1ea8b1b480784e80f65ded19c2faa94aa560a87",
    evaluation_hash: "3f913e7145c0210a26d885d0fe94d4c606df3c92253ccd5d00ed4c03e2b26f85",
    gap_axis: "CROSS_LAG_DEPENDENCE_OBSERVED",
    gate_decision: "BLOCK",
    gate_reason: "CROSS_LAG_DEPENDENCE_DETECTED",
    lag_test_count: 28,
    maturity_axis: "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL",
    max_adjusted_absolute_lower: "1",
    preregistration_adapter_binding_hash: "a02506d2fa53502589f753f031c221ff1737af15d8150300d4ffda5e23037e72",
    protocol_registration_hash: "df7b13dbbaa583e0e06bb26ce1eb6c56ca93cfc439f33d56f0a91d7403147568",
    public_summary_hash: "a47646d44019e0dd8c883f4ba4dfbbd8837fb2e2912327cc423635721e0b5891",
    source_axis: "VERIFIED_C2",
    stratum_assignment_hash: "d683ee350d06d2564800d320dfe7a069dd61731129559bf6e9f5dec61e1cf39a",
    verified: true,
  }),
});

function makeSummary(state) {
  const data = STATE_DATA[state];
  return {
    analytic_policy_hash: data.analytic_policy_hash,
    authority: clone(AUTHORITY),
    blockers: Array.from(data.blockers),
    c2_assessment_hash: data.c2_assessment_hash,
    c2_assessment_schema: "strategy-correlation-cross-lag-protocol-binding-candidate-v1",
    c2_assessment_static_fingerprint: "20260821-cross-lag-protocol-binding-1",
    consumer_receipt_hash: data.consumer_receipt_hash,
    cross_stratum_pair_count: data.cross_stratum_pair_count,
    dependent_test_count: data.dependent_test_count,
    direction_contract_hash: data.direction_contract_hash,
    evaluation_hash: data.evaluation_hash,
    facts: {
      aggregate_projection_only: true,
      c2_assessment_verified: data.verified,
      formal_preregistration_bound: false,
      sequence_order_attested: false,
    },
    gap_axis: data.gap_axis,
    gate_decision: data.gate_decision,
    gate_reason: data.gate_reason,
    lag_test_count: data.lag_test_count,
    maturity_axis: data.maturity_axis,
    max_adjusted_absolute_lower: data.max_adjusted_absolute_lower,
    permission_axis: "LOCKED",
    preregistration_adapter_binding_hash: data.preregistration_adapter_binding_hash,
    protocol_registration_hash: data.protocol_registration_hash,
    public_state: state,
    public_summary_hash: data.public_summary_hash,
    schema_version: constants.C3_SCHEMA,
    source_axis: data.source_axis,
    static_fingerprint: constants.C3_FINGERPRINT,
    stratum_assignment_hash: data.stratum_assignment_hash,
    verification_schema_version: constants.C3_VERIFICATION_SCHEMA,
  };
}

function makeEnvelope(state) {
  const summary = makeSummary(state);
  return {
    schema_version: constants.ENVELOPE_SCHEMA,
    summary,
    verification: {
      schema_version: constants.C3_VERIFICATION_SCHEMA,
      valid: true,
      supplied_public_summary_hash: summary.public_summary_hash,
      rebuilt_public_summary_hash: summary.public_summary_hash,
    },
  };
}

function resealSummary(summary) {
  const payload = clone(summary);
  delete payload.public_summary_hash;
  summary.public_summary_hash = contractTestHooks.sha256Ascii(contractTestHooks.canonicalJson(payload));
}

class FakeClassList {
  constructor() { this.values = []; }
  add(...values) { values.forEach((value) => { if (!this.values.includes(value)) this.values.push(value); }); }
}

class FakeTextNode {
  constructor(value) { this.nodeType = 3; this.value = String(value); this.parentNode = null; }
  get textContent() { return this.value; }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName).toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.attributes = {};
    this.classList = new FakeClassList();
    this.parentNode = null;
  }
  appendChild(node) { node.parentNode = this; this.children.push(node); return node; }
  setAttribute(name, value) { this.attributes[String(name)] = String(value); }
  addEventListener() { this.ownerDocument.listenerCalls += 1; }
  get textContent() { return this.children.map((child) => child.textContent).join(""); }
}

class FakeDocument {
  constructor() { this.listenerCalls = 0; this.body = new FakeElement("body", this); }
  createElement(tagName) { return new FakeElement(tagName, this); }
  createTextNode(value) { return new FakeTextNode(value); }
}

function descendants(node) {
  const values = [node];
  if (node && Array.isArray(node.children)) node.children.forEach((child) => values.push(...descendants(child)));
  return values;
}

const tests = [];
function test(name, body) { tests.push([name, body]); }

test("exports a frozen unmounted contract", () => {
  assert.equal(Object.isFrozen(api), true);
  assert.equal(Object.isFrozen(constants), true);
  assert.equal(constants.PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE");
});

test("pure SHA-256 matches standard vectors", () => {
  assert.equal(contractTestHooks.sha256Ascii(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  assert.equal(contractTestHooks.sha256Ascii("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
});

test("canonical JSON sorts keys and rejects non-canonical strings", () => {
  assert.equal(contractTestHooks.canonicalJson({ b: 1, a: 2 }), "{\"a\":2,\"b\":1}");
  assert.throws(() => contractTestHooks.canonicalJson({ value: "\u4e2d" }), /non-ASCII/);
});

test("all four real C3 fixtures match Python public-summary hashes", () => {
  Object.keys(STATE_DATA).forEach((state) => {
    const summary = makeSummary(state);
    const expected = summary.public_summary_hash;
    resealSummary(summary);
    assert.equal(summary.public_summary_hash, expected, state);
  });
});

test("absent envelope remains distinct not supplied", () => {
  assert.equal(buildCrossLagPresentationModel(undefined).public_state, "NOT_SUPPLIED");
});

test("malformed envelope fails closed to unknown", () => {
  assert.equal(buildCrossLagPresentationModel({ schema_version: "wrong" }).public_state, "UNKNOWN");
});

test("verified not-supplied and invalid C3 summaries preserve their states", () => {
  assert.equal(buildCrossLagPresentationModel(makeEnvelope("NOT_SUPPLIED")).public_state, "NOT_SUPPLIED");
  assert.equal(buildCrossLagPresentationModel(makeEnvelope("UNKNOWN")).public_state, "UNKNOWN");
});

test("valid pass preserves fixed four-axis order and locked authority", () => {
  const model = buildCrossLagPresentationModel(makeEnvelope("OBSERVED_PASS"));
  assert.equal(model.public_state, "OBSERVED_PASS");
  assert.deepEqual(model.axes.map((axis) => axis.axis), ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.deepEqual(model.axes.map((axis) => axis.state), ["VERIFIED_C2", "SEQUENCE_ORDER_UNATTESTED", "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL", "LOCKED"]);
  assert.equal(model.authority.paper_authorized, false);
  assert.equal(model.authority.live_order_allowed, false);
});

test("valid block remains visible with a real nonzero count", () => {
  const model = buildCrossLagPresentationModel(makeEnvelope("OBSERVED_BLOCK"));
  assert.equal(model.public_state, "OBSERVED_BLOCK");
  assert.equal(model.metrics.dependent_test_count, 1);
  assert.equal(model.blockers[0], "CROSS_LAG_DEPENDENCE_DETECTED");
});

test("verification must be a native true boolean", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.verification.valid = "true";
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("verification hash mismatch fails closed", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.verification.rebuilt_public_summary_hash = "0".repeat(64);
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("content tamper retaining the official receipt fails closed", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.summary.max_adjusted_absolute_lower = "0.1";
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("resealed real nonzero count tamper still mismatches the official receipt", () => {
  const envelope = makeEnvelope("OBSERVED_BLOCK");
  assert.ok(envelope.summary.dependent_test_count > 0);
  envelope.summary.dependent_test_count += 1;
  resealSummary(envelope.summary);
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("fully resealed semantic axis tamper still fails closed", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.summary.gap_axis = "CROSS_LAG_DEPENDENCE_OBSERVED";
  resealSummary(envelope.summary);
  envelope.verification.supplied_public_summary_hash = envelope.summary.public_summary_hash;
  envelope.verification.rebuilt_public_summary_hash = envelope.summary.public_summary_hash;
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("fully resealed true authority still fails closed", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.summary.authority.paper_authorized = true;
  resealSummary(envelope.summary);
  envelope.verification.supplied_public_summary_hash = envelope.summary.public_summary_hash;
  envelope.verification.rebuilt_public_summary_hash = envelope.summary.public_summary_hash;
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
});

test("extra raw field is never reflected", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  envelope.summary.raw_returns = "HOSTILE_RAW_RETURN_SERIES";
  const model = buildCrossLagPresentationModel(envelope);
  assert.equal(model.public_state, "UNKNOWN");
  assert.equal(JSON.stringify(model).includes("HOSTILE_RAW_RETURN_SERIES"), false);
});

test("accessor field is rejected without invoking the getter", () => {
  const envelope = makeEnvelope("OBSERVED_PASS");
  let calls = 0;
  Object.defineProperty(envelope.summary, "raw_returns", {
    enumerable: true,
    get() { calls += 1; return "HOSTILE"; },
  });
  assert.equal(buildCrossLagPresentationModel(envelope).public_state, "UNKNOWN");
  assert.equal(calls, 0);
});

test("models are deeply frozen", () => {
  const model = buildCrossLagPresentationModel(makeEnvelope("OBSERVED_PASS"));
  assert.equal(Object.isFrozen(model), true);
  assert.equal(Object.isFrozen(model.axes), true);
  assert.equal(Object.isFrozen(model.axes[0]), true);
  assert.equal(Object.isFrozen(model.authority), true);
});

test("renderer returns a detached semantic section", () => {
  const documentRef = new FakeDocument();
  const card = createCrossLagEvidenceCard(documentRef, buildCrossLagPresentationModel(makeEnvelope("OBSERVED_PASS")));
  assert.equal(card.tagName, "SECTION");
  assert.equal(card.parentNode, null);
  assert.equal(documentRef.body.children.length, 0);
  const tags = descendants(card).map((node) => node.tagName).filter(Boolean);
  assert.ok(tags.includes("DL"));
  assert.ok(tags.includes("DT"));
  assert.ok(tags.includes("DD"));
  assert.equal(card.attributes["aria-label"], "Cross-lag dependence research evidence");
});

test("block renderer keeps dependence copy first and explicit", () => {
  const documentRef = new FakeDocument();
  const card = createCrossLagEvidenceCard(documentRef, buildCrossLagPresentationModel(makeEnvelope("OBSERVED_BLOCK")));
  assert.match(card.textContent, /Dependence block/);
  assert.match(card.textContent, /Dependence was detected across preregistered lag tests/);
  assert.match(card.textContent, /must not be counted independently/);
});

test("malformed model renders fixed unknown without hostile HTML", () => {
  const documentRef = new FakeDocument();
  const hostile = { ...buildCrossLagPresentationModel(makeEnvelope("OBSERVED_PASS")), observation: "<script>attack()</script>" };
  const card = createCrossLagEvidenceCard(documentRef, hostile);
  assert.match(card.textContent, /could not be verified/);
  assert.equal(card.textContent.includes("attack()"), false);
  assert.equal(descendants(card).some((node) => node.tagName === "SCRIPT"), false);
});

test("rendered states contain no promotional or execution controls", () => {
  ["NOT_SUPPLIED", "UNKNOWN", "OBSERVED_PASS", "OBSERVED_BLOCK"].forEach((state) => {
    const documentRef = new FakeDocument();
    const card = createCrossLagEvidenceCard(documentRef, buildCrossLagPresentationModel(makeEnvelope(state)));
    assert.doesNotMatch(card.textContent, /\bREADY\b|\bAUTHORIZED\b|\bEXECUTABLE\b|expected return|target return|recommendation|allocation|profit claim/i);
    const tags = descendants(card).map((node) => node.tagName);
    ["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA"].forEach((tag) => assert.equal(tags.includes(tag), false));
  });
});

test("build and render call no network timer or listener API", () => {
  const names = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "setTimeout", "setInterval", "requestAnimationFrame"];
  const originals = new Map();
  let calls = 0;
  names.forEach((name) => {
    originals.set(name, globalThis[name]);
    globalThis[name] = () => { calls += 1; throw new Error(`${name} forbidden`); };
  });
  try {
    const documentRef = new FakeDocument();
    createCrossLagEvidenceCard(documentRef, buildCrossLagPresentationModel(makeEnvelope("OBSERVED_PASS")));
    assert.equal(calls, 0);
    assert.equal(documentRef.listenerCalls, 0);
  } finally {
    names.forEach((name) => {
      if (originals.get(name) === undefined) delete globalThis[name];
      else globalThis[name] = originals.get(name);
    });
  }
});

test("renderer rejects an invalid document dependency", () => {
  assert.throws(() => createCrossLagEvidenceCard({}, buildCrossLagPresentationModel(undefined)), /documentRef/);
});

test("component source contains no mutation or I/O primitives", () => {
  const source = fs.readFileSync(path.join(__dirname, "cross_lag_evidence_card.js"), "utf8");
  [
    ".innerHTML", ".outerHTML", "insertAdjacentHTML", "fetch(", "XMLHttpRequest",
    "WebSocket", "EventSource", "setTimeout(", "setInterval(", "requestAnimationFrame(",
    "addEventListener(", "querySelector(", "localStorage", "sessionStorage", "indexedDB",
  ].forEach((token) => assert.equal(source.includes(token), false, token));
});

test("CSS is scoped responsive and reduced-motion safe", () => {
  const css = fs.readFileSync(path.join(__dirname, "cross_lag_evidence_card.css"), "utf8");
  assert.match(css, /\.cross-lag-evidence-card/);
  assert.match(css, /@media \(max-width: 720px\)/);
  assert.match(css, /@media \(max-width: 420px\)/);
  assert.match(css, /grid-template-columns: 1fr/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /animation: none !important/);
  assert.match(css, /transform: none !important/);
  assert.doesNotMatch(css, /@import|url\(|(^|\n)\s*:root\s*\{|(^|\n)\s*(?:html|body)\s*\{/i);
});

let passed = 0;
for (const [name, body] of tests) {
  try {
    body();
    passed += 1;
  } catch (error) {
    console.error(`FAIL ${name}`);
    console.error(error && error.stack ? error.stack : error);
    process.exitCode = 1;
    break;
  }
}
if (!process.exitCode) console.log(`C4 cross-lag evidence card: ${passed}/${tests.length} PASS`);
