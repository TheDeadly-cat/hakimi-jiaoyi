"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const card = require("./factor_conditional_evidence_card.js");

const {
  buildFactorConditionalPresentationModel,
  constants,
  contractTestHooks,
  createFactorConditionalEvidenceCard,
} = card;

function canonical(value) {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" && Number.isSafeInteger(value) && !Object.is(value, -0)) return String(value);
  if (Array.isArray(value) && Object.getPrototypeOf(value) === Array.prototype) {
    return `[${value.map(canonical).join(",")}]`;
  }
  if (value && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  throw new TypeError("invalid_test_fixture");
}

function digest(value) {
  return crypto.createHash("sha256").update(value, "ascii").digest("hex");
}

function seal(payload, field) {
  return { ...payload, [field]: digest(canonical(payload)) };
}

function hash(char) {
  return String(char).repeat(64);
}

const receiptAuthority = Object.freeze({
  candidate_activation_allowed: false,
  common_factor_causality_proven: false,
  current_admission_allowed: false,
  current_pointer_written: false,
  descriptive_only: true,
  factor_calibration_attested: false,
  formal_factor_registration_bound: false,
  global_two_view_multiplicity_registered: false,
  live_order_allowed: false,
  paper_authorized: false,
  profitability_claim_allowed: false,
  raw_independence_proven: false,
  report_consumer_activated: false,
  report_mounted: false,
  residual_independence_proven: false,
});

const envelopeAuthority = Object.freeze({
  candidate_activation_allowed: false,
  common_factor_causality_proven: false,
  current_admission_allowed: false,
  current_pointer_written: false,
  descriptive_only: true,
  factor_calibration_attested: false,
  global_two_view_multiplicity_registered: false,
  live_order_allowed: false,
  paper_authorized: false,
  presentation_mounted: false,
  profitability_claim_allowed: false,
  raw_independence_proven: false,
  residual_independence_proven: false,
  source_semantics_replayed_in_browser: false,
});

const stateContracts = Object.freeze({
  OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE: {
    diagnostic: "COMMON_FACTOR_MEDIATED_CANDIDATE",
    gap: "COMMON_FACTOR_MEDIATION_CANDIDATE",
    raw: "BLOCK", residual: "PASS", rawCount: 2, residualCount: 0,
  },
  OBSERVED_RESIDUAL_CROSS_LAG_DEPENDENCE: {
    diagnostic: "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
    gap: "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
    raw: "BLOCK", residual: "BLOCK", rawCount: 1, residualCount: 1,
  },
  OBSERVED_NO_CONDITIONAL_DEPENDENCE: {
    diagnostic: "NO_CONDITIONAL_DEPENDENCE_DETECTED",
    gap: "NO_CONDITIONAL_DEPENDENCE_OBSERVED",
    raw: "PASS", residual: "PASS", rawCount: 0, residualCount: 0,
  },
  OBSERVED_SUPPRESSION_OR_MODEL_INSTABILITY: {
    diagnostic: "SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY",
    gap: "FACTOR_MODEL_INSTABILITY_OBSERVED",
    raw: "PASS", residual: "BLOCK", rawCount: 0, residualCount: 1,
  },
});

function evaluation(decision, dependent, marker) {
  return {
    cross_stratum_pair_count: 1,
    dependent_test_count: dependent,
    evaluation_hash: hash(marker),
    gate_decision: decision,
    gate_reason: decision === "PASS" ? "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_DETECTED" : "CROSS_LAG_DEPENDENCE_DETECTED",
    lag_test_count: 4,
    max_adjusted_absolute_lower: dependent ? "0.8125" : "0",
    observation_count: 1000,
    schema_version: "strategy-correlation-cross-lag-gate-candidate-v1",
    static_fingerprint: "20260821-cross-lag-dependence-gate-1",
  };
}

function observedReceipt(reportState) {
  const contract = stateContracts[reportState];
  const raw = evaluation(contract.raw, contract.rawCount, "1");
  const residual = evaluation(contract.residual, contract.residualCount, "2");
  return seal({
    authority: { ...receiptAuthority },
    blockers: ["FACTOR_CALIBRATION_RECEIPT_UNATTESTED", "GLOBAL_TWO_VIEW_MULTIPLICITY_NOT_REGISTERED", "FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED"],
    diagnostic_reason: contract.diagnostic,
    diagnostic_state: contract.diagnostic,
    facts: {
      calibration_receipt_attested: false,
      global_two_view_multiplicity_registered: false,
      raw_block_relaxed: false,
      raw_c0_verified: true,
      residual_c0_verified: true,
      source_diagnostic_verified: true,
    },
    gap_state: contract.gap,
    maturity_state: "CANDIDATE_RESIDUALIZED_NOT_FORMAL",
    permission_state: "LOCKED",
    raw_evaluation: raw,
    report_state: reportState,
    residual_evaluation: residual,
    schema_version: constants.RECEIPT_SCHEMA,
    source_diagnostic_hash: hash("3"),
    source_factor_observations_hash: hash("4"),
    source_identity_order_hash: hash("5"),
    source_raw_evaluation_hash: raw.evaluation_hash,
    source_registration_hash: hash("6"),
    source_report_contract: { activation_state: "UNMOUNTED", schema_version: constants.RECEIPT_SCHEMA },
    source_residual_evaluation_hash: residual.evaluation_hash,
    source_residual_input_hash: hash("7"),
    source_schema_version: "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v2",
    source_state: "OBSERVED",
    source_static_fingerprint: "20260822-cross-lag-factor-conditional-diagnostic-2",
    source_v1_diagnostic_hash: hash("8"),
    static_fingerprint: constants.RECEIPT_FINGERPRINT,
  }, "verification_hash");
}

function unknownReceipt(sourceState) {
  const blocker = {
    MISSING: "F0_V2_DIAGNOSTIC_MISSING",
    UNSUPPORTED: "F0_V1_PRECONSUMER_CONTRACT",
    INVALID: "F0_V2_DIAGNOSTIC_INVALID",
  }[sourceState];
  const unsupported = sourceState === "UNSUPPORTED";
  return seal({
    authority: { ...receiptAuthority },
    blockers: [blocker],
    diagnostic_reason: blocker,
    diagnostic_state: "UNKNOWN",
    facts: {
      calibration_receipt_attested: false,
      global_two_view_multiplicity_registered: false,
      raw_block_relaxed: false,
      raw_c0_verified: false,
      residual_c0_verified: false,
      source_diagnostic_verified: unsupported,
    },
    gap_state: blocker,
    maturity_state: "UNKNOWN",
    permission_state: "LOCKED",
    raw_evaluation: null,
    report_state: "UNKNOWN",
    residual_evaluation: null,
    schema_version: constants.RECEIPT_SCHEMA,
    source_diagnostic_hash: unsupported ? hash("9") : null,
    source_factor_observations_hash: null,
    source_identity_order_hash: null,
    source_raw_evaluation_hash: null,
    source_registration_hash: null,
    source_report_contract: null,
    source_residual_evaluation_hash: null,
    source_residual_input_hash: null,
    source_schema_version: unsupported ? "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1" : null,
    source_state: sourceState,
    source_static_fingerprint: unsupported ? "20260822-cross-lag-factor-conditional-diagnostic-1" : null,
    source_v1_diagnostic_hash: unsupported ? hash("9") : null,
    static_fingerprint: constants.RECEIPT_FINGERPRINT,
  }, "verification_hash");
}

function verifiedEnvelope(report) {
  return seal({
    authority: { ...envelopeAuthority },
    blockers: [],
    envelope_reason: "F1_RECEIPT_VERIFIED",
    presentation_status: constants.PRESENTATION_STATUS,
    report,
    schema_version: constants.ENVELOPE_SCHEMA,
    source_diagnostic_hash: report.source_diagnostic_hash,
    source_receipt_hash: report.verification_hash,
    source_schema_version: constants.RECEIPT_SCHEMA,
    source_state: report.source_state,
    source_static_fingerprint: constants.RECEIPT_FINGERPRINT,
    source_v1_diagnostic_hash: report.source_v1_diagnostic_hash,
    static_fingerprint: constants.ENVELOPE_FINGERPRINT,
    verification_state: "VERIFIED",
  }, "envelope_hash");
}

function closedEnvelope(kind) {
  const notSupplied = kind === "NOT_SUPPLIED";
  const reason = notSupplied ? "F1_RECEIPT_NOT_SUPPLIED" : "F1_RECEIPT_INVALID";
  return seal({
    authority: { ...envelopeAuthority },
    blockers: [reason],
    envelope_reason: reason,
    presentation_status: constants.PRESENTATION_STATUS,
    report: null,
    schema_version: constants.ENVELOPE_SCHEMA,
    source_diagnostic_hash: null,
    source_receipt_hash: null,
    source_schema_version: null,
    source_state: notSupplied ? "NOT_SUPPLIED" : "INVALID",
    source_static_fingerprint: null,
    source_v1_diagnostic_hash: null,
    static_fingerprint: constants.ENVELOPE_FINGERPRINT,
    verification_state: kind,
  }, "envelope_hash");
}

function assertLocked(model) {
  assert.equal(model.authority.descriptive_only, true);
  for (const [key, value] of Object.entries(model.authority)) {
    if (key !== "descriptive_only") assert.equal(value, false, key);
  }
  assert.equal(model.axes[3].axis, "PERMISSION");
  assert.equal(model.axes[3].state, "LOCKED");
}

function collectKeys(value, result = new Set()) {
  if (Array.isArray(value)) value.forEach((item) => collectKeys(item, result));
  else if (value && typeof value === "object") {
    Object.entries(value).forEach(([key, item]) => { result.add(key); collectKeys(item, result); });
  }
  return result;
}

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.className = "";
    this.attributes = {};
    this.children = [];
    this.parentNode = null;
    this._textContent = "";
  }
  set textContent(value) { this._textContent = String(value); }
  get textContent() { return this._textContent; }
  set innerHTML(_value) { throw new Error("inner_html_forbidden"); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
}

class FakeTextNode extends FakeElement {
  constructor(text) { super("#text"); this.textContent = text; }
}

function fakeDocument() {
  return {
    createElement(tagName) { return new FakeElement(tagName); },
    createTextNode(text) { return new FakeTextNode(text); },
    querySelector() { throw new Error("global_lookup_forbidden"); },
    getElementById() { throw new Error("global_lookup_forbidden"); },
  };
}

function textTree(node) {
  return [node.textContent, ...node.children.map(textTree)].join(" ");
}

function run() {
  assert.deepEqual(Object.keys(card).sort(), [
    "buildFactorConditionalPresentationModel", "constants",
    "contractTestHooks", "createFactorConditionalEvidenceCard",
  ]);
  assert.equal(constants.PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE");
  assert.equal(contractTestHooks.sha256Ascii("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assert.equal(contractTestHooks.canonicalJson({ b: 2, a: [true, "x"] }), '{"a":[true,"x"],"b":2}');

  const nullModel = buildFactorConditionalPresentationModel(null);
  const sealedNotSupplied = buildFactorConditionalPresentationModel(closedEnvelope("NOT_SUPPLIED"));
  assert.deepEqual(nullModel, sealedNotSupplied);
  assert.equal(nullModel.public_state, "NOT_SUPPLIED");
  assertLocked(nullModel);

  const invalidModel = buildFactorConditionalPresentationModel({});
  assert.deepEqual(invalidModel, buildFactorConditionalPresentationModel(closedEnvelope("INVALID")));
  assert.equal(invalidModel.public_state, "UNKNOWN");
  assertLocked(invalidModel);

  for (const [reportState, contract] of Object.entries(stateContracts)) {
    const receipt = observedReceipt(reportState);
    const envelope = verifiedEnvelope(receipt);
    const model = buildFactorConditionalPresentationModel(envelope);
    assert.equal(model.public_state, reportState);
    assert.equal(model.axes[0].state, "OBSERVED");
    assert.equal(model.axes[1].state, contract.gap);
    assert.equal(model.comparison.raw.decision, contract.raw);
    assert.equal(model.comparison.residual.decision, contract.residual);
    assert.equal(model.provenance.receipt_hash, receipt.verification_hash);
    assertLocked(model);
  }

  for (const sourceState of ["MISSING", "UNSUPPORTED", "INVALID"]) {
    const receipt = unknownReceipt(sourceState);
    const model = buildFactorConditionalPresentationModel(verifiedEnvelope(receipt));
    assert.equal(model.axes[0].state, sourceState);
    assert.equal(model.public_state, "UNKNOWN");
    assert.equal(model.comparison, null);
    assert.equal(model.provenance.receipt_hash, receipt.verification_hash);
    assertLocked(model);
  }

  const valid = verifiedEnvelope(observedReceipt("OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE"));
  const brokenEnvelope = structuredClone(valid);
  brokenEnvelope.envelope_hash = hash("0");
  assert.deepEqual(buildFactorConditionalPresentationModel(brokenEnvelope), invalidModel);

  const nestedTamper = structuredClone(valid);
  nestedTamper.report.report_state = "OBSERVED_NO_CONDITIONAL_DEPENDENCE";
  nestedTamper.envelope_hash = digest(canonical(Object.fromEntries(Object.entries(nestedTamper).filter(([key]) => key !== "envelope_hash"))));
  assert.deepEqual(buildFactorConditionalPresentationModel(nestedTamper), invalidModel);

  const schemaDrift = structuredClone(valid);
  schemaDrift.schema_version = `${constants.ENVELOPE_SCHEMA}-drift`;
  schemaDrift.envelope_hash = digest(canonical(Object.fromEntries(Object.entries(schemaDrift).filter(([key]) => key !== "envelope_hash"))));
  assert.deepEqual(buildFactorConditionalPresentationModel(schemaDrift), invalidModel);

  const authorityAlias = structuredClone(valid);
  authorityAlias.authority.ready = true;
  authorityAlias.envelope_hash = digest(canonical(Object.fromEntries(Object.entries(authorityAlias).filter(([key]) => key !== "envelope_hash"))));
  assert.deepEqual(buildFactorConditionalPresentationModel(authorityAlias), invalidModel);

  const duplicateBlocker = structuredClone(valid);
  duplicateBlocker.report.blockers.push("FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED");
  duplicateBlocker.report = seal(Object.fromEntries(Object.entries(duplicateBlocker.report).filter(([key]) => key !== "verification_hash")), "verification_hash");
  duplicateBlocker.source_receipt_hash = duplicateBlocker.report.verification_hash;
  duplicateBlocker.envelope_hash = digest(canonical(Object.fromEntries(Object.entries(duplicateBlocker).filter(([key]) => key !== "envelope_hash"))));
  assert.deepEqual(buildFactorConditionalPresentationModel(duplicateBlocker), invalidModel);

  const hostile = structuredClone(valid);
  hostile.attacker_text = "READY PROFIT LIVE";
  hostile.envelope_hash = digest(canonical(Object.fromEntries(Object.entries(hostile).filter(([key]) => key !== "envelope_hash"))));
  assert.deepEqual(buildFactorConditionalPresentationModel(hostile), invalidModel);
  assert.equal(JSON.stringify(buildFactorConditionalPresentationModel(hostile)).includes("READY PROFIT LIVE"), false);

  const nonFinite = structuredClone(valid);
  nonFinite.report.raw_evaluation.dependent_test_count = Number.NaN;
  assert.deepEqual(buildFactorConditionalPresentationModel(nonFinite), invalidModel);
  const prototypeEnvelope = Object.assign(Object.create({ inherited: true }), valid);
  assert.deepEqual(buildFactorConditionalPresentationModel(prototypeEnvelope), invalidModel);

  const model = buildFactorConditionalPresentationModel(valid);
  const forbiddenKeys = new Set([
    "aligned_observations", "observation_id", "returns", "beta", "betas",
    "factor_id", "factor_values", "residual_rows", "pair_lag_results",
  ]);
  assert.equal([...collectKeys(model)].some((key) => forbiddenKeys.has(key)), false);
  assert.deepEqual(buildFactorConditionalPresentationModel(valid), model);
  assert.equal(JSON.stringify(valid), JSON.stringify(verifiedEnvelope(observedReceipt("OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE"))));

  const doc = fakeDocument();
  const root = createFactorConditionalEvidenceCard(doc, valid);
  assert.equal(root.tagName, "article");
  assert.equal(root.parentNode, null);
  assert.equal(root.className, "factor-conditional-evidence-card");
  assert.equal(root.attributes["data-presentation-status"], "UNMOUNTED_CANDIDATE");
  const rendered = textTree(root);
  assert.equal(rendered.includes("Cross-lag mechanism ledger"), true);
  assert.equal(rendered.includes("Research display only"), true);
  assert.equal(rendered.includes("No independence, causality, profitability, paper, or live authority."), true);
  for (const phrase of ["safe to trade", "buy now", "sell now", "profit guaranteed"]) {
    assert.equal(rendered.toLowerCase().includes(phrase), false, phrase);
  }
  assert.throws(() => createFactorConditionalEvidenceCard({}, valid), /explicit_dom_document_required/);

  const cssPath = path.join(__dirname, "factor_conditional_evidence_card.css");
  const css = fs.readFileSync(cssPath, "utf8");
  assert.equal(css.includes(".factor-conditional-evidence-card"), true);
  assert.equal(css.includes("@media (max-width: 760px)"), true);
  assert.equal(css.includes("@media (prefers-reduced-motion: reduce)"), true);
  assert.equal(css.includes(":root"), false);
  assert.equal(/(^|[\s,{])body([\s,{]|$)/m.test(css), false);
  assert.equal(/(^|[\s,{])html([\s,{]|$)/m.test(css), false);
  assert.equal(css.includes("@import"), false);
  assert.equal(css.includes("!important"), false);

  const source = fs.readFileSync(path.join(__dirname, "factor_conditional_evidence_card.js"), "utf8");
  for (const forbidden of [".innerHTML", ".querySelector(", ".getElementById(", "addEventListener(", "setTimeout(", "fetch(", "localStorage", "sessionStorage"]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
  const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  assert.equal(appSource.includes("factor_conditional_evidence_card"), false);
  assert.equal(appSource.includes("HakimiFactorConditionalEvidenceCard"), false);

  console.log(JSON.stringify({
    status: "PASS",
    observed_states: 4,
    verified_unknown_states: 3,
    detached: true,
    mounted: false,
    model_hash: model.presentation_model_hash,
  }));
}

run();
