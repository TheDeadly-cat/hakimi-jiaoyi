"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  buildFactorCalibrationPrecommitPresentationModelV2,
  constants,
  contractTestHooks,
  createFactorCalibrationPrecommitEvidenceCardV2,
} = require("./factor_calibration_precommit_evidence_card_v2.js");
const { strictCanonicalHash } = require("./strict_canonical_json_v1.js");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function seal(overrides = {}) {
  const value = {
    schema_version: constants.SOURCE_SCHEMA,
    static_fingerprint: constants.SOURCE_FINGERPRINT,
    presentation_status: constants.SOURCE_STATUS,
    display_state: "LOCAL_BINDING",
    display_reason: "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED",
    blocker_count: 0,
    source_consumer_hash: "1".repeat(64),
    source_gate_hash: "2".repeat(64),
    source_axis: {
      label: "SOURCE",
      state: "VERIFIED",
      consumer_verification_state: "VERIFIED_LOCAL_BINDING",
      consumer_hash: "1".repeat(64),
      gate_hash: "2".repeat(64),
    },
    gap_axis: {
      label: "GAP",
      state: "OPEN",
      gap_code: "ARBITRARY_LAG_AND_EXTERNAL_TIMING_UNRESOLVED",
      arbitrary_lag_independence_unresolved: true,
      external_timing_unresolved: true,
    },
    maturity_axis: {
      label: "MATURITY",
      state: "LOCAL_MULTI_LAG_BOUND",
      evaluated_lags: [1, 2],
      maximum_evaluated_lag: 2,
      observed_maximum: "0.4",
      ceiling: "0.8",
      threshold_relation: "AT_OR_BELOW_CEILING",
      unstable_identity_count: 0,
    },
    permission_axis: {
      label: "PERMISSION",
      state: "LOCKED",
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      profitability_claim_allowed: false,
    },
    phase_comb: {
      status: "LOCAL_BINDING",
      teeth: [
        { lag: 1, coverage: "PREREGISTERED", result_exposed: false },
        { lag: 2, coverage: "PREREGISTERED", result_exposed: false },
      ],
      observed_maximum: "0.4",
      ceiling: "0.8",
      private_ledger_exposed: false,
    },
    authority: {
      descriptive_only: true,
      presentation_mount_allowed: false,
      candidate_activation_allowed: false,
      current_admission_allowed: false,
      current_pointer_written: false,
      paper_authorized: false,
      live_order_allowed: false,
      profitability_claim_allowed: false,
    },
    facts: { aggregate_only: true },
    ...overrides,
  };
  return { ...value, presentation_hash: strictCanonicalHash(value) };
}

class FakeNode {
  constructor(tagName) {
    this.tagName = tagName;
    this.className = "";
    this.children = [];
    this.attributes = {};
    this.textContent = "";
  }

  appendChild(node) {
    this.children.push(node);
    return node;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  set innerHTML(_value) {
    throw new Error("innerHTML is forbidden by the detached rendering contract");
  }
}

const fakeDocument = Object.freeze({
  createElement(tagName) {
    return new FakeNode(tagName);
  },
});

function collectText(node) {
  return [node.textContent, ...node.children.flatMap(collectText)].join(" ");
}

let count = 0;
function test(name, body) {
  body();
  count += 1;
  process.stdout.write(`ok ${count} - ${name}\n`);
}

test("exports exact source and card versions", () => {
  assert.equal(constants.SOURCE_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v2");
  assert.equal(constants.SOURCE_FINGERPRINT, "20260904-cross-lag-factor-calibration-precommit-presentation-envelope-2");
  assert.equal(constants.CARD_SCHEMA, "factor-calibration-precommit-phase-comb-card-v2");
  assert.equal(constants.CARD_FINGERPRINT, "20260905-factor-calibration-precommit-phase-comb-card-2");
});

test("maps a verified local envelope to four neutral axes", () => {
  const envelope = seal();
  const model = buildFactorCalibrationPrecommitPresentationModelV2(envelope, {
    expectedPresentationHash: envelope.presentation_hash,
  });
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "LOCAL_BINDING");
  assert.deepEqual(model.axes.map(({ label, state }) => [label, state]), [
    ["SOURCE", "VERIFIED LOCAL"],
    ["GAP", "OPEN"],
    ["MATURITY", "LOCAL MULTI-LAG BOUND"],
    ["PERMISSION", "LOCKED"],
  ]);
});

test("shows preregistered coverage without per-lag results", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV2(seal());
  assert.deepEqual(model.phase_comb.teeth, [
    { lag: 1, coverage: "PREREGISTERED", result_exposed: false },
    { lag: 2, coverage: "PREREGISTERED", result_exposed: false },
  ]);
  assert.equal(model.phase_comb.private_ledger_exposed, false);
  assert.equal(model.phase_comb.observed_maximum, "0.4");
  assert.equal(model.phase_comb.ceiling, "0.8");
});

test("maps verified block monotonically without unlocking permission", () => {
  const envelope = seal({
    display_state: "EVIDENCE_BLOCK",
    phase_comb: {
      status: "EVIDENCE_BLOCK",
      teeth: [
        { lag: 1, coverage: "PREREGISTERED", result_exposed: false },
        { lag: 2, coverage: "PREREGISTERED", result_exposed: false },
      ],
      observed_maximum: "0.81",
      ceiling: "0.8",
      private_ledger_exposed: false,
    },
  });
  const model = buildFactorCalibrationPrecommitPresentationModelV2(envelope);
  assert.equal(model.display_state, "EVIDENCE_BLOCK");
  assert.equal(model.axes[2].state, "EVIDENCE BLOCK");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("keeps a valid unknown source distinct", () => {
  const envelope = seal({
    display_state: "UNKNOWN",
    phase_comb: {
      status: "UNKNOWN",
      teeth: [
        { lag: 1, coverage: "PREREGISTERED", result_exposed: false },
        { lag: 2, coverage: "PREREGISTERED", result_exposed: false },
      ],
      observed_maximum: null,
      ceiling: "0.8",
      private_ledger_exposed: false,
    },
  });
  const model = buildFactorCalibrationPrecommitPresentationModelV2(envelope);
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "UNKNOWN");
  assert.equal(model.phase_comb.observed_maximum, "UNKNOWN");
});

test("rejects an unsealed payload mutation", () => {
  const envelope = seal();
  envelope.phase_comb.observed_maximum = "0.1";
  const model = buildFactorCalibrationPrecommitPresentationModelV2(envelope);
  assert.equal(model.integrity.verified, false);
  assert.equal(model.integrity.reason, "HASH_MISMATCH");
});

test("rejects an expected hash mismatch", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV2(seal(), {
    expectedPresentationHash: "f".repeat(64),
  });
  assert.equal(model.integrity.reason, "EXPECTED_HASH_MISMATCH");
});

test("rejects resealed schema and fingerprint drift", () => {
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV2(seal({ schema_version: "legacy-v1" })).integrity.reason,
    "UNSUPPORTED_SCHEMA",
  );
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV2(seal({ static_fingerprint: "other" })).integrity.reason,
    "UNSUPPORTED_FINGERPRINT",
  );
});

test("rejects resealed authority escalation", () => {
  const authority = clone(seal().authority);
  authority.paper_authorized = true;
  const model = buildFactorCalibrationPrecommitPresentationModelV2(seal({ authority }));
  assert.equal(model.integrity.reason, "AUTHORITY_INVALID");
  assert.equal(model.authority.paper_authorized, false);
  assert.equal(model.authority.live_order_allowed, false);
});

test("rejects resealed per-lag result exposure", () => {
  const phaseComb = clone(seal().phase_comb);
  phaseComb.teeth[1].result_exposed = true;
  phaseComb.teeth[1].observed = "0.9";
  const model = buildFactorCalibrationPrecommitPresentationModelV2(seal({ phase_comb: phaseComb }));
  assert.equal(model.integrity.reason, "PHASE_COMB_INVALID");
});

test("does not carry private ledgers or source facts into the view model", () => {
  const envelope = seal({
    facts: { identities: ["private-a"], returns: ["0.2"], aggregate_only: false },
    private_ledger: [{ lag: 1, score: "0.4" }],
  });
  const serialized = JSON.stringify(buildFactorCalibrationPrecommitPresentationModelV2(envelope));
  assert.doesNotMatch(serialized, /private-a|"returns":|"private_ledger":|"score":/);
});

test("accepts the inclusive ceiling without semantic promotion", () => {
  const phaseComb = clone(seal().phase_comb);
  phaseComb.observed_maximum = "0.8";
  const model = buildFactorCalibrationPrecommitPresentationModelV2(seal({ phase_comb: phaseComb }));
  assert.equal(model.phase_comb.observed_maximum, "0.8");
  assert.equal(model.display_state, "LOCAL_BINDING");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("renders through textContent in an explicit detached document", () => {
  const envelope = seal({ display_reason: "<img src=x onerror=alert(1)>" });
  const card = createFactorCalibrationPrecommitEvidenceCardV2({
    document: fakeDocument,
    envelope,
  });
  const text = collectText(card);
  assert.match(text, /Residual order \/ phase comb/);
  assert.match(text, /LAG 1/);
  assert.match(text, /LAG 2/);
  assert.doesNotMatch(text, /<img|onerror/);
  assert.equal(card.attributes["data-state"], "LOCAL_BINDING");
});

test("requires an explicit detached document", () => {
  assert.throws(
    () => createFactorCalibrationPrecommitEvidenceCardV2({ envelope: seal() }),
    /explicit detached document/,
  );
});

test("keeps public copy neutral", () => {
  const local = JSON.stringify(buildFactorCalibrationPrecommitPresentationModelV2(seal()));
  const unknown = JSON.stringify(buildFactorCalibrationPrecommitPresentationModelV2(null));
  assert.doesNotMatch(`${local} ${unknown}`, /\bready\b|profit|profitable|盈利|收益证明/i);
  assert.match(local, /SOURCE/);
  assert.match(local, /GAP/);
  assert.match(local, /MATURITY/);
  assert.match(local, /PERMISSION/);
});

test("is deterministic for the same sealed envelope", () => {
  const envelope = seal();
  assert.deepEqual(
    buildFactorCalibrationPrecommitPresentationModelV2(envelope),
    buildFactorCalibrationPrecommitPresentationModelV2(clone(envelope)),
  );
});

test("ships scoped responsive and reduced-motion styles", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v2.css"),
    "utf8",
  );
  assert.match(css, /\.fcpc2-card/);
  assert.match(css, /\.fcpc2-comb/);
  assert.match(css, /@media \(max-width: 720px\)/);
  assert.match(css, /@media \(max-width: 430px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(css, /\.ready|\.profit|#00ff00/i);
});

test("contains no implicit page activation hook", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v2.js"),
    "utf8",
  );
  assert.doesNotMatch(source, /require\(["']\.\/app|DOMContentLoaded|document\.querySelector|window\./);
});

assert.equal(count, 18);
process.stdout.write("factor calibration precommit phase-comb card v2: 18/18 PASS\n");
