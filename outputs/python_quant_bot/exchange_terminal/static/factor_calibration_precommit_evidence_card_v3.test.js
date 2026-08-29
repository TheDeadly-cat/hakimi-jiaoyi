"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  buildFactorCalibrationPrecommitPresentationModelV3,
  constants,
  contractTestHooks,
  createFactorCalibrationPrecommitEvidenceCardV3,
} = require("./factor_calibration_precommit_evidence_card_v3.js");
const { strictCanonicalHash } = require("./strict_canonical_json_v1.js");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function baseEnvelope() {
  return {
    schema_version: constants.SOURCE_SCHEMA,
    static_fingerprint: constants.SOURCE_FINGERPRINT,
    presentation_status: constants.SOURCE_STATUS,
    display_state: "LOCAL_BINDING",
    display_reason: "THREE_LAG_LOCAL_BINDING_VERIFIED",
    blocker_count: 0,
    source_consumer_hash: "1".repeat(64),
    source_gate_hash: "2".repeat(64),
    source_precommit_gate_v5_hash: "3".repeat(64),
    source_report_consumer_v5_hash: "4".repeat(64),
    source_residual_order_gate_v3_hash: "5".repeat(64),
    source_residual_order_gate_v2_hash: "6".repeat(64),
    source_residual_order_gate_v1_hash: "7".repeat(64),
    source_beta_stability_gate_hash: "8".repeat(64),
    source_replay_hash: "9".repeat(64),
    source_registration_hash: "a".repeat(64),
    source_calibration_observations_hash: "b".repeat(64),
    source_state: "OBSERVED",
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
      state: "LOCAL_THREE_LAG_BOUND",
      evaluated_lags: [1, 2, 3],
      maximum_evaluated_lag: 3,
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
      teeth: [1, 2, 3].map((lag) => ({
        lag,
        coverage: "PREREGISTERED",
        result_exposed: false,
      })),
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
    facts: {
      aggregate_only: true,
      consumer_verified: true,
      four_axis_separation_preserved: true,
      private_ledger_exposed: false,
      residual_order_independence_proven: false,
    },
  };
}

function seal(overrides = {}) {
  const value = { ...baseEnvelope(), ...overrides };
  return { ...value, presentation_hash: strictCanonicalHash(value) };
}

function unknownEnvelope() {
  return seal({
    display_state: "UNKNOWN",
    display_reason: "SOURCE_UNKNOWN",
    blocker_count: 1,
    source_state: "MISSING",
    source_axis: {
      label: "SOURCE",
      state: "UNKNOWN",
      consumer_verification_state: "UNKNOWN",
      consumer_hash: "1".repeat(64),
      gate_hash: "2".repeat(64),
    },
    maturity_axis: {
      label: "MATURITY",
      state: "UNKNOWN",
      evaluated_lags: [1, 2, 3],
      maximum_evaluated_lag: 3,
      observed_maximum: null,
      ceiling: "0.8",
      threshold_relation: "UNKNOWN",
      unstable_identity_count: 0,
    },
    phase_comb: {
      status: "UNKNOWN",
      teeth: baseEnvelope().phase_comb.teeth,
      observed_maximum: null,
      ceiling: "0.8",
      private_ledger_exposed: false,
    },
    facts: {
      aggregate_only: true,
      consumer_verified: false,
      four_axis_separation_preserved: true,
      private_ledger_exposed: false,
      residual_order_independence_proven: false,
    },
  });
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

function collectStrings(value, output = []) {
  if (typeof value === "string") {
    output.push(value);
  } else if (Array.isArray(value)) {
    value.forEach((item) => collectStrings(item, output));
  } else if (value && typeof value === "object") {
    Object.values(value).forEach((item) => collectStrings(item, output));
  }
  return output;
}

let count = 0;
function test(name, body) {
  body();
  count += 1;
  process.stdout.write(`ok ${count} - ${name}\n`);
}

test("exports exact source and card versions", () => {
  assert.equal(constants.SOURCE_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v3");
  assert.equal(constants.SOURCE_FINGERPRINT, "20260909-cross-lag-factor-calibration-precommit-presentation-envelope-3");
  assert.equal(constants.CARD_SCHEMA, "factor-calibration-precommit-phase-comb-card-v3");
  assert.equal(constants.CARD_FINGERPRINT, "20260910-factor-calibration-precommit-phase-comb-card-3");
});

test("maps a verified local envelope to four neutral axes", () => {
  const envelope = seal();
  const model = buildFactorCalibrationPrecommitPresentationModelV3(envelope, {
    expectedPresentationHash: envelope.presentation_hash,
  });
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "LOCAL_BINDING");
  assert.deepEqual(model.axes.map(({ label, state }) => [label, state]), [
    ["SOURCE", "VERIFIED LOCAL"],
    ["GAP", "OPEN"],
    ["MATURITY", "LOCAL THREE-LAG BOUND"],
    ["PERMISSION", "LOCKED"],
  ]);
});

test("shows exactly three preregistered coverage teeth", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV3(seal());
  assert.deepEqual(model.phase_comb.teeth, [1, 2, 3].map((lag) => ({
    lag,
    coverage: "PREREGISTERED",
    result_exposed: false,
  })));
  assert.equal(model.phase_comb.private_ledger_exposed, false);
  assert.equal(model.phase_comb.observed_maximum, "0.4");
  assert.equal(model.phase_comb.ceiling, "0.8");
});

test("maps verified block monotonically without unlocking permission", () => {
  const baseline = baseEnvelope();
  const envelope = seal({
    display_state: "EVIDENCE_BLOCK",
    display_reason: "THREE_LAG_GATE_BLOCK",
    blocker_count: 2,
    source_axis: {
      ...baseline.source_axis,
      consumer_verification_state: "VERIFIED_BLOCK",
    },
    maturity_axis: {
      ...baseline.maturity_axis,
      state: "EVIDENCE_BLOCK",
      observed_maximum: "0.81",
      threshold_relation: "SOURCE_BLOCK_VERIFIED",
      unstable_identity_count: 1,
    },
    phase_comb: {
      ...baseline.phase_comb,
      status: "EVIDENCE_BLOCK",
      observed_maximum: "0.81",
    },
  });
  const model = buildFactorCalibrationPrecommitPresentationModelV3(envelope);
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "EVIDENCE_BLOCK");
  assert.equal(model.axes[2].state, "EVIDENCE BLOCK");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("keeps a valid unknown source distinct", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV3(unknownEnvelope());
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "UNKNOWN");
  assert.equal(model.phase_comb.observed_maximum, "UNKNOWN");
  assert.equal(model.axes[1].state, "OPEN");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("rejects an unsealed payload mutation", () => {
  const envelope = seal();
  envelope.phase_comb.observed_maximum = "0.1";
  const model = buildFactorCalibrationPrecommitPresentationModelV3(envelope);
  assert.equal(model.integrity.verified, false);
  assert.equal(model.integrity.reason, "HASH_MISMATCH");
});

test("rejects an expected hash mismatch", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV3(seal(), {
    expectedPresentationHash: "f".repeat(64),
  });
  assert.equal(model.integrity.reason, "EXPECTED_HASH_MISMATCH");
});

test("rejects resealed schema fingerprint and mount drift", () => {
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ schema_version: "legacy-v2" })).integrity.reason,
    "UNSUPPORTED_SCHEMA",
  );
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ static_fingerprint: "other" })).integrity.reason,
    "UNSUPPORTED_FINGERPRINT",
  );
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ presentation_status: "MOUNTED" })).integrity.reason,
    "MOUNT_STATUS_INVALID",
  );
});

test("rejects resealed authority escalation", () => {
  const authority = clone(baseEnvelope().authority);
  authority.paper_authorized = true;
  const model = buildFactorCalibrationPrecommitPresentationModelV3(seal({ authority }));
  assert.equal(model.integrity.reason, "AUTHORITY_INVALID");
  assert.equal(model.authority.paper_authorized, false);
  assert.equal(model.authority.live_order_allowed, false);
});

test("rejects resealed permission escalation", () => {
  const permissionAxis = clone(baseEnvelope().permission_axis);
  permissionAxis.current_admission_allowed = true;
  const model = buildFactorCalibrationPrecommitPresentationModelV3(
    seal({ permission_axis: permissionAxis }),
  );
  assert.equal(model.integrity.reason, "PERMISSION_LOCK_INVALID");
});

test("rejects per-lag result exposure", () => {
  const phaseComb = clone(baseEnvelope().phase_comb);
  phaseComb.teeth[2].result_exposed = true;
  const model = buildFactorCalibrationPrecommitPresentationModelV3(
    seal({ phase_comb: phaseComb }),
  );
  assert.equal(model.integrity.reason, "PHASE_COMB_INVALID");
});

test("rejects missing duplicate and reordered lag teeth", () => {
  for (const teeth of [
    baseEnvelope().phase_comb.teeth.slice(0, 2),
    [
      baseEnvelope().phase_comb.teeth[0],
      baseEnvelope().phase_comb.teeth[0],
      baseEnvelope().phase_comb.teeth[2],
    ],
    [...baseEnvelope().phase_comb.teeth].reverse(),
  ]) {
    const phaseComb = { ...baseEnvelope().phase_comb, teeth };
    assert.equal(
      buildFactorCalibrationPrecommitPresentationModelV3(seal({ phase_comb: phaseComb })).integrity.reason,
      "PHASE_COMB_INVALID",
    );
  }
});

test("rejects maturity lag coverage drift", () => {
  const maturityAxis = {
    ...baseEnvelope().maturity_axis,
    evaluated_lags: [1, 2, 4],
  };
  const model = buildFactorCalibrationPrecommitPresentationModelV3(
    seal({ maturity_axis: maturityAxis }),
  );
  assert.equal(model.integrity.reason, "MATURITY_CONTRACT_INVALID");
});

test("rejects phase and maturity aggregate mismatch", () => {
  const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: "0.3" };
  const model = buildFactorCalibrationPrecommitPresentationModelV3(
    seal({ phase_comb: phaseComb }),
  );
  assert.equal(model.integrity.reason, "PHASE_COMB_INVALID");
});

test("rejects gap closure and axis relabeling", () => {
  const gapAxis = { ...baseEnvelope().gap_axis, state: "CLOSED" };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ gap_axis: gapAxis })).integrity.reason,
    "GAP_LOCK_INVALID",
  );
  const sourceAxis = { ...baseEnvelope().source_axis, label: "SIGNAL" };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ source_axis: sourceAxis })).integrity.reason,
    "SOURCE_STATE_INCONSISTENT",
  );
});

test("rejects source state and hash cross-bind drift", () => {
  const sourceAxis = {
    ...baseEnvelope().source_axis,
    consumer_verification_state: "VERIFIED_BLOCK",
  };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ source_axis: sourceAxis })).integrity.reason,
    "SOURCE_STATE_INCONSISTENT",
  );
  const hashAxis = { ...baseEnvelope().source_axis, consumer_hash: "f".repeat(64) };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ source_axis: hashAxis })).integrity.reason,
    "SOURCE_HASH_CROSS_BIND_INVALID",
  );
});

test("rejects extra sealed private fields and does not project them", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV3(seal({
    private_ledger: [{ lag: 3, score: "0.9" }],
  }));
  assert.equal(model.integrity.reason, "TOP_LEVEL_CONTRACT_INVALID");
  assert.equal(model.phase_comb.private_ledger_exposed, false);
  assert.doesNotMatch(
    JSON.stringify(model),
    /"private_ledger"\s*:|"score"\s*:/,
  );
});

test("accepts the inclusive ceiling without semantic promotion", () => {
  const maturityAxis = { ...baseEnvelope().maturity_axis, observed_maximum: "0.8" };
  const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: "0.8" };
  const model = buildFactorCalibrationPrecommitPresentationModelV3(
    seal({ maturity_axis: maturityAxis, phase_comb: phaseComb }),
  );
  assert.equal(model.integrity.verified, true);
  assert.equal(model.phase_comb.observed_maximum, "0.8");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("rejects invalid score grammar and threshold relation drift", () => {
  for (const score of ["NaN", "Infinity", "1e-1", "-0.1", "1.1"] ) {
    const maturityAxis = { ...baseEnvelope().maturity_axis, observed_maximum: score };
    const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: score };
    assert.equal(
      buildFactorCalibrationPrecommitPresentationModelV3(
        seal({ maturity_axis: maturityAxis, phase_comb: phaseComb }),
      ).integrity.verified,
      false,
    );
  }
  const maturityAxis = {
    ...baseEnvelope().maturity_axis,
    threshold_relation: "ABOVE_CEILING",
  };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV3(seal({ maturity_axis: maturityAxis })).integrity.reason,
    "THRESHOLD_RELATION_INVALID",
  );
});

test("renders three teeth through textContent in a detached document", () => {
  const card = createFactorCalibrationPrecommitEvidenceCardV3({
    document: fakeDocument,
    envelope: seal({ display_reason: "<img src=x onerror=alert(1)>" }),
  });
  const text = collectText(card);
  assert.match(text, /Three-lag residual phase comb/);
  assert.match(text, /LAG 1/);
  assert.match(text, /LAG 2/);
  assert.match(text, /LAG 3/);
  assert.doesNotMatch(text, /<img|onerror/);
  assert.equal(card.attributes["data-state"], "LOCAL_BINDING");
});

test("requires an explicit detached document", () => {
  assert.throws(
    () => createFactorCalibrationPrecommitEvidenceCardV3({ envelope: seal() }),
    /explicit detached document/,
  );
});

test("keeps all public string copy neutral", () => {
  const local = collectStrings(buildFactorCalibrationPrecommitPresentationModelV3(seal())).join(" ");
  const unknown = collectStrings(buildFactorCalibrationPrecommitPresentationModelV3(null)).join(" ");
  assert.doesNotMatch(`${local} ${unknown}`, /\bready\b|\bprofit(?:able|ability)?\b|盈利|收益证明/i);
  assert.match(local, /SOURCE/);
  assert.match(local, /GAP/);
  assert.match(local, /MATURITY/);
  assert.match(local, /PERMISSION/);
});

test("is deterministic for the same sealed envelope", () => {
  const envelope = seal();
  assert.deepEqual(
    buildFactorCalibrationPrecommitPresentationModelV3(envelope),
    buildFactorCalibrationPrecommitPresentationModelV3(clone(envelope)),
  );
});

test("ships scoped responsive reduced-motion instrument styles", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v3.css"),
    "utf8",
  );
  assert.match(css, /\.fcpc3-card/);
  assert.match(css, /\.fcpc3-tooth-lag-3/);
  assert.match(css, /@media \(max-width: 780px\)/);
  assert.match(css, /@media \(max-width: 460px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(css, /\.ready|\.profit|#00ff00|#[a-f0-9]*(?:80|ff)[a-f0-9]*ff/i);
});

test("contains no implicit page activation hook", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v3.js"),
    "utf8",
  );
  assert.doesNotMatch(source, /require\(["']\.\/app|DOMContentLoaded|document\.querySelector|window\./);
});

assert.equal(count, 25);
process.stdout.write("factor calibration precommit phase-comb card v3: 25/25 PASS\n");
