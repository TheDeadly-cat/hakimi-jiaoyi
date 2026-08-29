"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const strictJson = require("./strict_canonical_json_v1.js");
const card = require("./factor_calibration_precommit_evidence_card.js");

const H = (character) => character.repeat(64);

function gateAuthority() {
  return {
    beta_temporal_stability_proven: false,
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    external_precommit_timing_attested: false,
    formal_residualization_registration_v2_issued: false,
    future_evaluation_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    profitability_claim_allowed: false,
  };
}

function envelopeAuthority() {
  return {
    beta_temporal_stability_proven: false,
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    external_precommit_timing_attested: false,
    formal_residualization_registration_v2_issued: false,
    future_evaluation_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mounted: false,
    profitability_claim_allowed: false,
    source_semantics_replayed_in_browser: false,
  };
}

function facts(observed, stable) {
  return {
    beta_stability_threshold_passed: stable,
    beta_temporal_stability_proven: false,
    cross_gate_source_hashes_bound: observed,
    external_time_anchor_verified: false,
    formal_residualization_registration_v2_issued: false,
    future_evaluation_activated: false,
    local_precommit_binding_complete: observed,
    precommit_gate_v1_verified: observed,
    source_gate_block_relaxed: false,
    stability_gate_verified: observed,
  };
}

function makeGate(kind = "GUARDED") {
  const observed = kind === "GUARDED" || kind === "BLOCK";
  const guarded = kind === "GUARDED";
  const gate = {
    schema_version: card.constants.GATE_SCHEMA,
    static_fingerprint: card.constants.GATE_FINGERPRINT,
    source_state: observed ? "OBSERVED" : kind,
    gate_decision: guarded ? "BOUND_LOCAL_ONLY_STABILITY_GUARDED" : observed ? "BLOCK" : "UNKNOWN",
    gate_reason: guarded
      ? "LOCAL_PRECOMMIT_AND_BETA_STABILITY_GUARD_BOUND"
      : observed ? "BETA_STABILITY_GATE_BLOCKED" : `H1_SOURCE_${kind}`,
    source_precommit_gate_v1_hash: observed ? H("1") : null,
    source_stability_gate_hash: observed ? H("2") : null,
    source_declaration_hash: observed ? H("3") : null,
    source_report_hash: observed ? H("4") : null,
    source_replay_hash: observed ? H("5") : null,
    source_registration_hash: observed ? H("6") : null,
    source_calibration_observations_hash: observed ? H("7") : null,
    source_precommit_gate_v1_decision: observed ? "BOUND_LOCAL_ONLY" : null,
    source_stability_gate_decision: observed ? (guarded ? "STABLE_CANDIDATE" : "BLOCK") : null,
    future_evaluation_id: observed ? "EVAL-2025-02-A" : null,
    protocol_id: observed ? "FUTURE_FACTOR_RESIDUALIZATION_EVALUATION_V2" : null,
    precommit_declared_at_utc: observed ? "2025-01-15T00:00:00Z" : null,
    evaluation_not_before_date: observed ? "2025-02-01" : null,
    external_time_anchor_reference_hash: observed ? H("8") : null,
    fold_count: observed ? 4 : null,
    maximum_allowed_normalized_beta_drift: observed ? "0.5" : null,
    maximum_observed_normalized_beta_drift: observed ? (guarded ? "0" : "1") : null,
    unstable_identity_count: observed ? (guarded ? 0 : 1) : null,
    sign_reversal_count: observed ? 0 : null,
    unidentified_fold_count: observed ? 0 : null,
    facts: facts(observed, guarded),
    blockers: observed
      ? [...(guarded ? [] : ["CALIBRATION_BETA_TEMPORAL_INSTABILITY_DETECTED", "BETA_STABILITY_GATE_BLOCKED"]), "PRECOMMIT_GATE_V2_NOT_ACTIVATED"]
      : [`H1_SOURCE_${kind}`],
    authority: gateAuthority(),
  };
  return strictJson.sealDocument(gate, "gate_hash");
}

function makeEnvelope(gate) {
  return strictJson.sealDocument({
    schema_version: card.constants.ENVELOPE_SCHEMA,
    static_fingerprint: card.constants.ENVELOPE_FINGERPRINT,
    presentation_status: card.constants.PRESENTATION_STATUS,
    verification_state: "VERIFIED",
    envelope_reason: "H1_PRECOMMIT_GATE_VERIFIED",
    source_state: gate.source_state,
    source_schema_version: gate.schema_version,
    source_static_fingerprint: gate.static_fingerprint,
    source_gate_hash: gate.gate_hash,
    source_precommit_gate_v1_hash: gate.source_precommit_gate_v1_hash,
    source_stability_gate_hash: gate.source_stability_gate_hash,
    source_replay_hash: gate.source_replay_hash,
    source_registration_hash: gate.source_registration_hash,
    source_calibration_observations_hash: gate.source_calibration_observations_hash,
    gate,
    authority: envelopeAuthority(),
  }, "envelope_hash");
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
    source_gate_hash: null,
    source_precommit_gate_v1_hash: null,
    source_stability_gate_hash: null,
    source_replay_hash: null,
    source_registration_hash: null,
    source_calibration_observations_hash: null,
    gate: null,
    authority: envelopeAuthority(),
  }, "envelope_hash");
}

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.className = "";
    this.textContent = "";
    this.children = [];
    this.attributes = {};
  }
  appendChild(child) { this.children.push(child); return child; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
}

class FakeDocument {
  constructor() { this.created = 0; }
  createElement(tagName) { this.created += 1; return new FakeElement(tagName); }
}

function allText(node) {
  return [node.textContent, ...node.children.flatMap((child) => allText(child))].join(" ");
}

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

test("guarded candidate builds a verified frozen model", () => {
  const model = card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(makeGate()));
  assert.strictEqual(model.evidence_state, "BOUND_LOCAL_ONLY_STABILITY_GUARDED");
  assert.strictEqual(model.stability.fold_count, 4);
  assert.strictEqual(model.authority.beta_temporal_stability_proven, false);
  assert.strictEqual(Object.isFrozen(model), true);
  assert.strictEqual(Object.isFrozen(model.stability), true);
});

test("verified H0 block remains blocked", () => {
  const model = card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(makeGate("BLOCK")));
  assert.strictEqual(model.evidence_state, "BLOCK");
  assert.strictEqual(model.gap.state, "BETA_STABILITY_GATE_BLOCKED");
  assert(model.blockers.includes("BETA_STABILITY_GATE_BLOCKED"));
});

test("verified H1 missing source remains unknown", () => {
  const model = card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(makeGate("MISSING")));
  assert.strictEqual(model.verification_state, "VERIFIED");
  assert.strictEqual(model.evidence_state, "UNKNOWN");
  assert.strictEqual(model.source.state, "MISSING");
  assert.strictEqual(model.stability, null);
});

test("closed envelope states remain distinct unknown", () => {
  for (const [state, reason] of [
    ["NOT_SUPPLIED", "H1_PRECOMMIT_GATE_NOT_SUPPLIED"],
    ["UNSUPPORTED", "H1_PRECOMMIT_GATE_UNSUPPORTED"],
    ["INVALID", "H1_PRECOMMIT_GATE_INVALID"],
  ]) {
    const model = card.buildFactorCalibrationPrecommitPresentationModel(makeClosedEnvelope(state, reason));
    assert.strictEqual(model.evidence_state, "UNKNOWN");
    assert.deepStrictEqual(model.blockers, [reason]);
  }
});

test("envelope hash tamper fails closed", () => {
  const envelope = makeEnvelope(makeGate());
  envelope.envelope_reason = "H1_PRECOMMIT_GATE_INVALID";
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(envelope).verification_state, "UNKNOWN");
});

test("coherently resealed drift relaxation fails closed", () => {
  const gate = makeGate();
  gate.maximum_observed_normalized_beta_drift = "2";
  const resealedGate = strictJson.sealDocument(gate, "gate_hash");
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(resealedGate)).verification_state, "UNKNOWN");
});

test("envelope cross-hash substitution fails closed", () => {
  const envelope = makeEnvelope(makeGate());
  envelope.source_replay_hash = H("9");
  const resealed = strictJson.sealDocument(envelope, "envelope_hash");
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(resealed).verification_state, "UNKNOWN");
});

test("private key injection fails closed", () => {
  const gate = makeGate();
  gate.rows = [];
  const resealedGate = strictJson.sealDocument(gate, "gate_hash");
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(resealedGate)).verification_state, "UNKNOWN");
});

test("authority unlock and alias fail closed", () => {
  for (const mutate of [
    (gate) => { gate.authority.paper_authorized = true; },
    (gate) => { gate.authority.ready = false; },
  ]) {
    const gate = makeGate();
    mutate(gate);
    const resealedGate = strictJson.sealDocument(gate, "gate_hash");
    assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(resealedGate)).verification_state, "UNKNOWN");
  }
});

test("duplicate blockers and nonfinite aggregate fail closed", () => {
  const duplicate = makeGate();
  duplicate.blockers.push(duplicate.blockers[0]);
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(strictJson.sealDocument(duplicate, "gate_hash"))).verification_state, "UNKNOWN");
  const nonfinite = makeGate();
  nonfinite.maximum_observed_normalized_beta_drift = "NaN";
  assert.strictEqual(card.buildFactorCalibrationPrecommitPresentationModel(makeEnvelope(strictJson.sealDocument(nonfinite, "gate_hash"))).verification_state, "UNKNOWN");
});

test("detached renderer exposes four private-ledger folds safely", () => {
  const documentRef = new FakeDocument();
  const root = card.createFactorCalibrationPrecommitEvidenceCard(makeEnvelope(makeGate()), { documentRef });
  const text = allText(root);
  assert.strictEqual(root.tagName, "section");
  assert.strictEqual(root.attributes["aria-label"], "Factor calibration precommit and stability evidence");
  assert(documentRef.created > 35);
  assert(text.includes("Does the local precommit survive a beta-regime check?"));
  assert.strictEqual((text.match(/PRIVATE LEDGER/g) || []).length, 4);
  assert.strictEqual(Object.prototype.hasOwnProperty.call(root, "innerHTML"), false);
});

test("unknown renderer stays neutral and permission locked", () => {
  const root = card.createFactorCalibrationPrecommitEvidenceCard(
    makeClosedEnvelope("INVALID", "H1_PRECOMMIT_GATE_INVALID"),
    { documentRef: new FakeDocument() },
  );
  const text = allText(root);
  assert(text.includes("UNKNOWN"));
  assert(text.includes("LOCKED"));
  assert(!/ready to trade|buy now|sell now|guaranteed profit/i.test(text));
});

test("CSS is scoped, responsive, instrument-specific, and reduced-motion aware", () => {
  const css = fs.readFileSync(path.join(__dirname, "factor_calibration_precommit_evidence_card.css"), "utf8");
  assert(css.includes(".factor-precommit-card__fold-rail"));
  assert(css.includes("grid-template-columns: repeat(4"));
  assert(css.includes("@media (max-width: 760px)"));
  assert(css.includes("@media (max-width: 440px)"));
  assert(css.includes("prefers-reduced-motion: reduce"));
  assert(!/(^|\n)\s*body\s*\{/m.test(css));
});

test("constants remain exact and unmounted", () => {
  assert.strictEqual(card.constants.PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE");
  assert.strictEqual(card.constants.MODEL_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-model-v1");
  assert.strictEqual(card.constants.PRESENTATION_FINGERPRINT, "20260827-cross-lag-factor-calibration-h2-unmounted-presentation-1");
});

test("production module exposes no mount or network API", () => {
  assert.deepStrictEqual(Object.keys(card).sort(), [
    "buildFactorCalibrationPrecommitPresentationModel", "constants",
    "contractTestHooks", "createFactorCalibrationPrecommitEvidenceCard",
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
console.log(`factor calibration precommit evidence card: ${passed}/${tests.length} PASS`);
