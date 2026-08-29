"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const strictJson = require("./strict_canonical_json_v1.js");
const card = require("./factor_calibration_evidence_card.js");

const H = (character) => character.repeat(64);

function reportAuthority() {
  return {
    calibration_receipt_attested: false,
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    external_calibration_timing_attested: false,
    factor_registration_formal: false,
    live_order_allowed: false,
    paper_authorized: false,
    profitability_claim_allowed: false,
    report_consumer_activated: false,
    report_mounted: false,
  };
}

function envelopeAuthority() {
  return {
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    external_calibration_timing_attested: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mounted: false,
    profitability_claim_allowed: false,
    report_consumer_activated: false,
    source_semantics_replayed_in_browser: false,
  };
}

function facts(observed, matched) {
  return {
    all_rows_at_or_before_calibration_cutoff: observed,
    beta_replay_matches_registration: matched,
    calibration_input_verified: observed,
    estimator_replayed: observed,
    external_calibration_timing_attested: false,
    registration_calibration_receipt_g0_bound: false,
    registration_v1_verified: observed,
    selection_after_calibration: observed,
    source_replay_verified: observed,
  };
}

function makeReport(kind = "MATCH") {
  const observed = kind === "MATCH" || kind === "BLOCK";
  const state = observed ? "OBSERVED" : kind;
  const match = kind === "MATCH";
  const block = kind === "BLOCK";
  const report = {
    schema_version: card.constants.REPORT_SCHEMA,
    static_fingerprint: card.constants.REPORT_FINGERPRINT,
    source_state: state,
    source_schema_version: observed ? "strategy-correlation-cross-lag-factor-calibration-replay-candidate-v1" : null,
    source_static_fingerprint: observed ? "20260823-cross-lag-factor-calibration-replay-1" : null,
    source_replay_hash: observed ? H("1") : null,
    source_registration_hash: observed ? H("2") : null,
    source_calibration_observations_hash: observed ? H("3") : null,
    source_declared_calibration_receipt_hash: observed ? H("4") : null,
    source_registered_beta_ledger_hash: observed ? H("5") : null,
    source_replayed_beta_ledger_hash: observed ? H("5") : null,
    source_report_contract: observed ? { schema_version: card.constants.REPORT_SCHEMA, activation_state: "UNMOUNTED" } : null,
    report_state: match ? "OBSERVED_CALIBRATION_MATCH" : block ? "OBSERVED_CALIBRATION_BLOCK" : "UNKNOWN",
    diagnostic_state: match ? "CALIBRATION_REPLAY_MATCH" : block ? "CALIBRATION_REPLAY_BLOCK" : "UNKNOWN",
    diagnostic_reason: match ? "REGISTERED_BETAS_REPLAYED_WITHIN_TOLERANCE" : block ? "REGISTERED_BETAS_FAILED_CALIBRATION_REPLAY" : `G0_CALIBRATION_REPLAY_${kind}`,
    gap_state: match ? "MATHEMATICAL_REPLAY_MATCHED_TIMING_UNATTESTED" : block ? "CALIBRATION_REPLAY_MISMATCH" : `G0_CALIBRATION_REPLAY_${kind}`,
    maturity_state: observed ? "CANDIDATE_CALIBRATION_REPLAY_NOT_TIME_ATTESTED" : "UNKNOWN",
    permission_state: "LOCKED",
    calibration_summary: observed ? {
      replay_decision: kind,
      observation_count: 40,
      first_observation_date: "2024-11-01",
      last_observation_date: "2024-12-10",
      calibration_cutoff_date: "2025-01-01",
      selection_cutoff_date: "2025-02-01",
      identity_count: 2,
      estimator: "FROZEN_PRE_EVALUATION_OLS_V1",
      intercept_policy: "NO_INTERCEPT_RETURN_RESIDUAL_V1",
      beta_abs_tolerance: "1E-12",
      max_abs_beta_error: match ? "0" : "1.5",
    } : null,
    facts: facts(observed, match),
    blockers: observed
      ? [...(block ? ["REGISTERED_BETA_REPLAY_MISMATCH"] : []), "EXTERNAL_CALIBRATION_TIMING_UNATTESTED", "REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND", "CALIBRATION_REPLAY_NOT_ACTIVATED", "FACTOR_CALIBRATION_REPORT_NOT_ACTIVATED"]
      : [`G0_CALIBRATION_REPLAY_${kind}`],
    authority: reportAuthority(),
  };
  return strictJson.sealDocument(report, "verification_hash");
}

function makeEnvelope(report) {
  const envelope = {
    schema_version: card.constants.ENVELOPE_SCHEMA,
    static_fingerprint: card.constants.ENVELOPE_FINGERPRINT,
    presentation_status: card.constants.PRESENTATION_STATUS,
    verification_state: "VERIFIED",
    envelope_reason: "G1_REPORT_VERIFIED",
    source_state: report.source_state,
    source_schema_version: report.schema_version,
    source_static_fingerprint: report.static_fingerprint,
    source_report_hash: report.verification_hash,
    source_replay_hash: report.source_replay_hash,
    source_registration_hash: report.source_registration_hash,
    source_calibration_observations_hash: report.source_calibration_observations_hash,
    report,
    authority: envelopeAuthority(),
  };
  return strictJson.sealDocument(envelope, "envelope_hash");
}

function makeClosedEnvelope(state, reason) {
  return strictJson.sealDocument({
    schema_version: card.constants.ENVELOPE_SCHEMA,
    static_fingerprint: card.constants.ENVELOPE_FINGERPRINT,
    presentation_status: card.constants.PRESENTATION_STATUS,
    verification_state: "UNKNOWN",
    envelope_reason: reason,
    source_state: state,
    source_schema_version: null,
    source_static_fingerprint: null,
    source_report_hash: null,
    source_replay_hash: null,
    source_registration_hash: null,
    source_calibration_observations_hash: null,
    report: null,
    authority: envelopeAuthority(),
  }, "envelope_hash");
}

class FakeElement {
  constructor(tagName, counters) {
    this.tagName = tagName;
    this.className = "";
    this.textContent = "";
    this.children = [];
    this.attributes = {};
    this.counters = counters;
  }
  appendChild(child) { this.children.push(child); return child; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
}

class FakeDocument {
  constructor() { this.counters = { created: 0 }; }
  createElement(tagName) {
    this.counters.created += 1;
    return new FakeElement(tagName, this.counters);
  }
}

function allText(node) {
  return [node.textContent, ...node.children.flatMap((child) => allText(child))].join(" ");
}

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

test("strict canonical utility seals and hashes deterministically", () => {
  assert.strictEqual(strictJson.sha256Hex("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assert.strictEqual(strictJson.strictCanonicalStringify({ b: [true, null], a: 1 }), '{"a":1,"b":[true,null]}');
  const sealed = strictJson.sealDocument({ b: 2, a: 1 }, "hash");
  assert.strictEqual(strictJson.verifySealedDocument(sealed, "hash"), true);
});

test("MATCH builds a verified frozen model", () => {
  const model = card.buildFactorCalibrationPresentationModel(makeEnvelope(makeReport("MATCH")));
  assert.strictEqual(model.evidence_state, "OBSERVED_CALIBRATION_MATCH");
  assert.strictEqual(model.calibration.replay_decision, "MATCH");
  assert.strictEqual(Object.isFrozen(model), true);
  assert.strictEqual(Object.isFrozen(model.calibration), true);
});

test("BLOCK remains blocked", () => {
  const model = card.buildFactorCalibrationPresentationModel(makeEnvelope(makeReport("BLOCK")));
  assert.strictEqual(model.evidence_state, "OBSERVED_CALIBRATION_BLOCK");
  assert(model.blockers.includes("REGISTERED_BETA_REPLAY_MISMATCH"));
});

test("verified G1 UNKNOWN remains unknown", () => {
  const model = card.buildFactorCalibrationPresentationModel(makeEnvelope(makeReport("MISSING")));
  assert.strictEqual(model.evidence_state, "UNKNOWN");
  assert.strictEqual(model.source.state, "MISSING");
  assert.strictEqual(model.calibration, null);
});

test("closed envelopes remain distinct unknown states", () => {
  for (const [state, reason] of [["NOT_SUPPLIED", "G1_REPORT_NOT_SUPPLIED"], ["UNSUPPORTED", "G1_REPORT_UNSUPPORTED"], ["INVALID", "G1_REPORT_INVALID"]]) {
    const model = card.buildFactorCalibrationPresentationModel(makeClosedEnvelope(state, reason));
    assert.strictEqual(model.evidence_state, "UNKNOWN");
    assert.deepStrictEqual(model.blockers, [reason]);
  }
});

test("envelope hash tamper fails closed", () => {
  const envelope = makeEnvelope(makeReport("MATCH"));
  envelope.envelope_reason = "G1_REPORT_INVALID";
  assert.strictEqual(card.buildFactorCalibrationPresentationModel(envelope).verification_state, "UNKNOWN");
});

test("coherently resealed report state tamper fails closed", () => {
  const report = makeReport("MATCH");
  report.report_state = "OBSERVED_CALIBRATION_BLOCK";
  const resealed = strictJson.sealDocument(report, "verification_hash");
  assert.strictEqual(card.buildFactorCalibrationPresentationModel(makeEnvelope(resealed)).verification_state, "UNKNOWN");
});

test("private key injection fails closed", () => {
  const report = makeReport("MATCH");
  report.rows = [];
  const resealed = strictJson.sealDocument(report, "verification_hash");
  assert.strictEqual(card.buildFactorCalibrationPresentationModel(makeEnvelope(resealed)).verification_state, "UNKNOWN");
});

test("authority unlock and alias fail closed", () => {
  for (const mutate of [
    (report) => { report.authority.paper_authorized = true; },
    (report) => { report.authority.ready = false; },
  ]) {
    const report = makeReport("MATCH");
    mutate(report);
    const resealed = strictJson.sealDocument(report, "verification_hash");
    assert.strictEqual(card.buildFactorCalibrationPresentationModel(makeEnvelope(resealed)).verification_state, "UNKNOWN");
  }
});

test("detached renderer uses safe text primitives", () => {
  const documentRef = new FakeDocument();
  const root = card.createFactorCalibrationEvidenceCard(makeEnvelope(makeReport("MATCH")), { documentRef });
  assert.strictEqual(root.tagName, "section");
  assert.strictEqual(root.attributes["aria-label"], "Factor calibration replay evidence");
  assert(documentRef.counters.created > 20);
  assert(allText(root).includes("Does the declared beta ledger replay?"));
  assert.strictEqual(Object.prototype.hasOwnProperty.call(root, "innerHTML"), false);
});

test("unknown renderer stays neutral", () => {
  const root = card.createFactorCalibrationEvidenceCard(makeClosedEnvelope("INVALID", "G1_REPORT_INVALID"), { documentRef: new FakeDocument() });
  const text = allText(root);
  assert(text.includes("UNKNOWN"));
  assert(!/ready to trade|buy now|sell now|guaranteed/i.test(text));
});

test("CSS is scoped, responsive, and reduced-motion aware", () => {
  const css = fs.readFileSync(path.join(__dirname, "factor_calibration_evidence_card.css"), "utf8");
  assert(css.includes(".factor-calibration-evidence-card"));
  assert(css.includes("@media (max-width: 720px)"));
  assert(css.includes("@media (max-width: 420px)"));
  assert(css.includes("prefers-reduced-motion: reduce"));
  assert(!/(^|\n)\s*body\s*\{/m.test(css));
});

test("constants remain exact and unmounted", () => {
  assert.strictEqual(card.constants.PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE");
  assert.strictEqual(card.constants.MODEL_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-presentation-model-v1");
  assert.strictEqual(card.constants.PRESENTATION_FINGERPRINT, "20260823-cross-lag-factor-calibration-g2-unmounted-presentation-1");
});

test("production module exposes no mount or network API", () => {
  assert.deepStrictEqual(Object.keys(card).sort(), [
    "buildFactorCalibrationPresentationModel", "constants", "contractTestHooks",
    "createFactorCalibrationEvidenceCard",
  ]);
  assert.strictEqual(typeof global.document, "undefined");
});

let passed = 0;
for (const [name, fn] of tests) {
  try {
    fn();
    passed += 1;
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}
console.log(`factor calibration evidence card: ${passed}/${tests.length} PASS`);
