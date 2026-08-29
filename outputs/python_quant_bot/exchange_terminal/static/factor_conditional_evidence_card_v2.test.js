"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const api = require("./factor_conditional_evidence_card_v2.js");

const tests = [];
function test(name, fn) {
  tests.push({ name, fn });
}

function lockedOuterAuthority(registered = true) {
  return {
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    global_two_view_multiplicity_registered: registered,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mounted: false,
    profitability_claim_allowed: false,
    report_consumer_v2_activated: false,
    source_semantics_replayed_in_browser: false,
  };
}

function lockedReportAuthority() {
  return {
    candidate_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    global_independence_proven: false,
    live_order_allowed: false,
    paper_authorized: false,
    profitability_claim_allowed: false,
    raw_independence_proven: false,
    report_consumer_v2_activated: false,
    residual_independence_proven: false,
  };
}

function reportFixture(decision = "PASS") {
  const blocked = decision === "BLOCK";
  return {
    authority: lockedReportAuthority(),
    blockers: [
      "REGISTRATION_TIMING_UNATTESTED",
      "FACTOR_CALIBRATION_RECEIPT_UNATTESTED",
      "TWO_VIEW_MULTIPLICITY_GATE_NOT_ACTIVATED",
      "FACTOR_CONDITIONAL_REPORT_V2_NOT_ACTIVATED",
    ],
    correction_method: "BONFERRONI_TWO_SIDED_FWER_RAW_RESIDUAL_V1",
    dependence_threshold: "0.75",
    family_alpha: "0.05",
    facts: {
      factor_calibration_attested: false,
      formula_parity_verified: true,
      global_two_view_multiplicity_registered: true,
      registration_timing_attested: false,
      report_consumer_v2_activated: false,
      source_block_preserved: blocked,
      source_cross_links_verified: true,
      source_f1_receipt_verified: true,
      source_f3_gate_verified: true,
    },
    gap_state: blocked
      ? "GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED"
      : "NO_GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED",
    global_dependent_test_count: blocked ? 1 : 0,
    global_recalibrated_decision: decision,
    global_test_count: 8,
    lags: [-2, -1, 1, 2],
    maturity_state: "CANDIDATE_GLOBAL_FAMILY_NOT_TIME_ATTESTED",
    per_view_test_count: 4,
    permission_state: "RESEARCH_ONLY_NO_EXECUTION_AUTHORITY",
    report_state: blocked
      ? "GLOBAL_TWO_VIEW_FAMILY_BLOCKED"
      : "GLOBAL_TWO_VIEW_FAMILY_OBSERVED_NOT_ACTIVATED",
    schema_version: api.constants.REPORT_SCHEMA,
    source_f0_diagnostic_hash: "4".repeat(64),
    source_f1_gap_state: "NO_CONDITIONAL_DEPENDENCE_OBSERVED",
    source_f1_maturity_state: "CANDIDATE_RESIDUALIZED_NOT_FORMAL",
    source_f1_report_state: "OBSERVED_FACTOR_CONDITIONAL_CANDIDATE",
    source_f1_verification_hash: "2".repeat(64),
    source_family_registration_hash: "5".repeat(64),
    source_raw_evaluation_hash: "6".repeat(64),
    source_residual_evaluation_hash: "7".repeat(64),
    source_residual_input_hash: "8".repeat(64),
    source_state: "OBSERVED",
    source_two_view_gate_evaluation_hash: "3".repeat(64),
    static_fingerprint: api.constants.REPORT_FINGERPRINT,
    verification_hash: "1".repeat(64),
    view_count: 2,
    view_summaries: [
      {
        global_dependent_test_count: 0,
        max_global_adjusted_absolute_lower: "0",
        source_dependent_test_count: blocked ? 2 : 0,
        source_evaluation_hash: "6".repeat(64),
        source_gate_decision: blocked ? "BLOCK" : "PASS",
        view: "RAW",
      },
      {
        global_dependent_test_count: blocked ? 1 : 0,
        max_global_adjusted_absolute_lower: blocked ? "0.81" : "0",
        source_dependent_test_count: blocked ? 1 : 0,
        source_evaluation_hash: "7".repeat(64),
        source_gate_decision: blocked ? "BLOCK" : "PASS",
        view: "RESIDUAL",
      },
    ],
    views: ["RAW", "RESIDUAL"],
  };
}

function envelopeFixture(decision = "PASS") {
  const report = reportFixture(decision);
  return api.contractTestHooks.sealEnvelope({
    authority: lockedOuterAuthority(true),
    envelope_reason: "F4_REPORT_VERIFIED",
    presentation_status: api.constants.PRESENTATION_STATUS,
    report,
    schema_version: api.constants.ENVELOPE_SCHEMA,
    source_f1_verification_hash: report.source_f1_verification_hash,
    source_report_hash: report.verification_hash,
    source_schema_version: report.schema_version,
    source_state: report.source_state,
    source_static_fingerprint: report.static_fingerprint,
    source_two_view_gate_evaluation_hash:
      report.source_two_view_gate_evaluation_hash,
    static_fingerprint: api.constants.ENVELOPE_FINGERPRINT,
    verification_state: "VERIFIED",
  });
}

function unknownEnvelope() {
  const report = reportFixture();
  report.authority = lockedReportAuthority();
  report.blockers = ["EXPECTED_HASH_INVALID"];
  report.facts = {
    factor_calibration_attested: false,
    formula_parity_verified: false,
    global_two_view_multiplicity_registered: false,
    registration_timing_attested: false,
    report_consumer_v2_activated: false,
    source_block_preserved: false,
    source_cross_links_verified: false,
    source_f1_receipt_verified: false,
    source_f3_gate_verified: false,
  };
  report.gap_state = "UNKNOWN";
  report.global_dependent_test_count = null;
  report.global_recalibrated_decision = "UNKNOWN";
  report.global_test_count = null;
  report.lags = [];
  report.maturity_state = "UNKNOWN";
  report.per_view_test_count = null;
  report.report_state = "UNKNOWN";
  report.source_state = "UNKNOWN";
  report.view_count = null;
  report.view_summaries = [];
  report.views = [];
  return api.contractTestHooks.sealEnvelope({
    authority: lockedOuterAuthority(false),
    envelope_reason: "F4_REPORT_VERIFIED",
    presentation_status: api.constants.PRESENTATION_STATUS,
    report,
    schema_version: api.constants.ENVELOPE_SCHEMA,
    source_f1_verification_hash: report.source_f1_verification_hash,
    source_report_hash: report.verification_hash,
    source_schema_version: report.schema_version,
    source_state: report.source_state,
    source_static_fingerprint: report.static_fingerprint,
    source_two_view_gate_evaluation_hash:
      report.source_two_view_gate_evaluation_hash,
    static_fingerprint: api.constants.ENVELOPE_FINGERPRINT,
    verification_state: "VERIFIED",
  });
}

class FakeElement {
  constructor(tagName, tracker) {
    this.tagName = tagName;
    this.tracker = tracker;
    this.children = [];
    this.attributes = {};
    this.className = "";
    this.style = {
      values: {},
      setProperty: (key, value) => {
        this.style.values[key] = value;
      },
    };
    this.textContent = "";
  }

  append(...children) {
    this.children.push(...children);
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  set innerHTML(_value) {
    this.tracker.innerHtmlWrites += 1;
    throw new Error("innerHTML forbidden");
  }
}

class FakeDocument {
  constructor() {
    this.tracker = { innerHtmlWrites: 0 };
  }

  createElement(tagName) {
    return new FakeElement(tagName, this.tracker);
  }
}

function flattenText(node) {
  return [node.textContent]
    .concat(node.children.flatMap(flattenText))
    .filter(Boolean)
    .join(" ");
}

test("exports exact v2 identities", () => {
  assert.equal(
    api.constants.ENVELOPE_SCHEMA,
    "strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v2"
  );
  assert.equal(
    api.constants.MODEL_SCHEMA,
    "strategy-correlation-cross-lag-factor-conditional-presentation-model-v2"
  );
  assert.deepEqual(Object.keys(api).sort(), [
    "buildFactorConditionalPresentationModelV2",
    "constants",
    "contractTestHooks",
    "createFactorConditionalEvidenceCardV2",
  ]);
});

test("verified pass model keeps four ordered axes and family metrics", () => {
  const model = api.buildFactorConditionalPresentationModelV2(envelopeFixture());
  assert.equal(model.integrityState, "VERIFIED_ENVELOPE");
  assert.deepEqual(model.axes.map((axis) => axis.label), [
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  assert.equal(model.metrics.find((item) => item.label === "Family tests").value, "4 + 4 = 8");
  assert.equal(model.viewRows.length, 2);
  assert.equal(model.statusTone, "observed");
});

test("blocked model remains blocked", () => {
  const model = api.buildFactorConditionalPresentationModelV2(
    envelopeFixture("BLOCK")
  );
  assert.equal(model.statusTone, "blocked");
  assert.equal(model.axes[1].tone, "blocked");
  assert.equal(model.viewRows[1].globalDependent, 1);
});

test("verified unknown closure stays unknown", () => {
  const model = api.buildFactorConditionalPresentationModelV2(unknownEnvelope());
  assert.equal(model.integrityState, "VERIFIED_ENVELOPE");
  assert.equal(model.sourceState, "UNKNOWN");
  assert.equal(model.statusTone, "unknown");
  assert.deepEqual(model.axes.map((axis) => axis.value), [
    "UNKNOWN",
    "UNKNOWN",
    "UNKNOWN",
    "UNKNOWN",
  ]);
});

test("valid closed envelope is unavailable rather than observed", () => {
  const envelope = api.contractTestHooks.sealEnvelope({
    authority: lockedOuterAuthority(false),
    envelope_reason: "F4_REPORT_NOT_SUPPLIED",
    presentation_status: api.constants.PRESENTATION_STATUS,
    report: null,
    schema_version: api.constants.ENVELOPE_SCHEMA,
    source_f1_verification_hash: null,
    source_report_hash: null,
    source_schema_version: null,
    source_state: "UNKNOWN",
    source_static_fingerprint: null,
    source_two_view_gate_evaluation_hash: null,
    static_fingerprint: api.constants.ENVELOPE_FINGERPRINT,
    verification_state: "NOT_SUPPLIED",
  });
  const model = api.buildFactorConditionalPresentationModelV2(envelope);
  assert.equal(model.statusTone, "unknown");
  assert.deepEqual(model.blockers, ["F4_REPORT_NOT_SUPPLIED"]);
});

test("tamper without reseal invalidates integrity", () => {
  const envelope = envelopeFixture();
  envelope.report.global_test_count = 1;
  const model = api.buildFactorConditionalPresentationModelV2(envelope);
  assert.equal(model.integrityState, "INVALID_OR_UNAVAILABLE");
  assert.deepEqual(model.blockers, ["ENVELOPE_INTEGRITY_INVALID"]);
});

test("resealed outer authority unlock is rejected", () => {
  const envelope = envelopeFixture();
  envelope.authority.paper_authorized = true;
  const resealed = api.contractTestHooks.sealEnvelope(envelope);
  const model = api.buildFactorConditionalPresentationModelV2(resealed);
  assert.deepEqual(model.blockers, ["ENVELOPE_AUTHORITY_INVALID"]);
});

test("resealed report authority alias is rejected", () => {
  const envelope = envelopeFixture();
  envelope.report.authority.execution_allowed = false;
  const resealed = api.contractTestHooks.sealEnvelope(envelope);
  const model = api.buildFactorConditionalPresentationModelV2(resealed);
  assert.deepEqual(model.blockers, ["REPORT_AUTHORITY_INVALID"]);
});

test("identity and private-ledger fields are rejected after reseal", () => {
  for (const key of ["left_identity", "private_recalculated_test_ledger_hash"]) {
    const envelope = envelopeFixture();
    envelope.report.injected = { [key]: "hidden" };
    const resealed = api.contractTestHooks.sealEnvelope(envelope);
    const model = api.buildFactorConditionalPresentationModelV2(resealed);
    assert.deepEqual(model.blockers, ["FORBIDDEN_DETAIL_FIELD"], key);
  }
});

test("model construction is deterministic", () => {
  const envelope = envelopeFixture();
  assert.deepEqual(
    api.buildFactorConditionalPresentationModelV2(envelope),
    api.buildFactorConditionalPresentationModelV2(envelope)
  );
});

test("module import is detached and DOM-free", () => {
  assert.equal(typeof global.document, "undefined");
  assert.equal(api.buildFactorConditionalPresentationModelV2(envelopeFixture()).mounted, false);
});

test("DOM factory renders with textContent and no innerHTML", () => {
  const documentRef = new FakeDocument();
  const card = api.createFactorConditionalEvidenceCardV2(envelopeFixture(), {
    document: documentRef,
  });
  assert.equal(card.tagName, "article");
  assert.equal(card.attributes["data-presentation-status"], "UNMOUNTED_CANDIDATE");
  assert.equal(documentRef.tracker.innerHtmlWrites, 0);
  assert.match(flattenText(card), /Conditional evidence \/ global family/);
});

test("hostile blocker is rendered as literal text", () => {
  const envelope = envelopeFixture();
  const hostile = "<img src=x onerror=alert(1)>";
  envelope.report.blockers.push(hostile);
  const resealed = api.contractTestHooks.sealEnvelope(envelope);
  const documentRef = new FakeDocument();
  const card = api.createFactorConditionalEvidenceCardV2(resealed, {
    document: documentRef,
  });
  assert.match(flattenText(card), /<img src=x onerror=alert\(1\)>/);
  assert.equal(documentRef.tracker.innerHtmlWrites, 0);
});

test("canonical hash has known SHA-256 parity", () => {
  assert.equal(
    api.contractTestHooks.sha256Hex("abc"),
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
  );
  assert.equal(api.contractTestHooks.verifyEnvelopeIntegrity(envelopeFixture()), true);
});

test("CSS remains scoped responsive and motion-safe", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "factor_conditional_evidence_card_v2.css"),
    "utf8"
  );
  assert.match(css, /^\.f5-evidence-card/m);
  assert.match(css, /@media \(max-width: 52rem\)/);
  assert.match(css, /@media \(max-width: 34rem\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.doesNotMatch(css, /(^|\n)\s*:root\s*\{/);
});

test("visible copy contains no recommendation or execution implication", () => {
  const model = api.buildFactorConditionalPresentationModelV2(envelopeFixture());
  const visible = JSON.stringify({
    axes: model.axes,
    blockers: model.blockers,
    subtitle: model.subtitle,
    title: model.title,
  });
  assert.doesNotMatch(visible, /\bready\b|guarantee|buy signal|sell signal|execute now/i);
});

for (const entry of tests) {
  entry.fn();
}
console.log(`factor_conditional_evidence_card_v2 PASS tests=${tests.length}`);
