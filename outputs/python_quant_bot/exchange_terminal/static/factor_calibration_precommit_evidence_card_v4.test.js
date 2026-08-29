"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  buildFactorCalibrationPrecommitPresentationModelV4,
  constants,
  createFactorCalibrationPrecommitEvidenceCardV4,
} = require("./factor_calibration_precommit_evidence_card_v4.js");
const { strictCanonicalHash } = require("./strict_canonical_json_v1.js");

const SOURCE_HASH_FIELDS = [
  "source_consumer_hash",
  "source_precommit_gate_v7_hash",
  "source_report_consumer_v6_hash",
  "source_precommit_gate_v6_hash",
  "source_omnibus_gate_v1_hash",
  "source_report_consumer_v5_hash",
  "source_precommit_gate_v5_hash",
  "source_residual_order_gate_v3_hash",
  "source_precommit_gate_v4_hash",
  "source_residual_order_gate_v2_hash",
  "source_residual_order_gate_v1_hash",
  "source_beta_stability_gate_hash",
  "source_replay_hash",
  "source_registration_hash",
  "source_calibration_observations_hash",
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function baseEnvelope() {
  const hashes = Object.fromEntries(
    SOURCE_HASH_FIELDS.map((field, index) => [
      field,
      (index + 1).toString(16).repeat(64),
    ]),
  );
  return {
    schema_version: constants.SOURCE_SCHEMA,
    static_fingerprint: constants.SOURCE_FINGERPRINT,
    presentation_status: constants.SOURCE_STATUS,
    display_state: "LOCAL_BINDING",
    display_reason: "FINITE_HORIZON_LOCAL_BINDING_VERIFIED",
    source_state: "OBSERVED",
    ...hashes,
    source_axis: {
      label: "SOURCE",
      state: "VERIFIED",
      consumer_verification_state: "VERIFIED_LOCAL_BINDING",
      consumer_hash: hashes.source_consumer_hash,
      precommit_gate_v7_hash: hashes.source_precommit_gate_v7_hash,
      omnibus_gate_v1_hash: hashes.source_omnibus_gate_v1_hash,
    },
    gap_axis: {
      label: "GAP",
      state: "OPEN",
      gap_code: "LAGS_ABOVE_SIX_AND_EXTERNAL_TIMING_UNRESOLVED",
      arbitrary_lag_independence_unresolved: true,
      external_timing_unresolved: true,
      lags_above_six_unresolved: true,
    },
    maturity_axis: {
      label: "MATURITY",
      state: "LOCAL_FINITE_HORIZON_BOUND",
      evaluated_lags: [1, 2, 3, 4, 5, 6],
      omnibus_band_lags: [4, 5, 6],
      maximum_evaluated_lag: 6,
      metric: "LAG_BAND_QUADRATIC_ENERGY",
      observed_maximum: "0.4",
      ceiling: "0.64",
      threshold_relation: "AT_OR_BELOW_CEILING",
      fold_count: 4,
      unstable_identity_count: 0,
    },
    permission_axis: {
      label: "PERMISSION",
      state: "LOCKED",
      current_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      profitability_claim_allowed: false,
    },
    phase_comb: {
      status: "LOCAL_BINDING",
      teeth: [1, 2, 3, 4, 5, 6].map((lag) => ({
        lag,
        coverage: lag <= 3
          ? "BASELINE_PREREGISTERED"
          : "OMNIBUS_PREREGISTERED",
        result_exposed: false,
      })),
      omnibus_band_lags: [4, 5, 6],
      observed_maximum: "0.4",
      ceiling: "0.64",
      private_ledger_exposed: false,
    },
    blocker_count: 1,
    facts: {
      aggregate_only: true,
      consumer_verified: true,
      finite_horizon_omnibus_guard_bound: true,
      four_axis_separation_preserved: true,
      lags_above_six_unresolved: true,
      omnibus_quadratic_energy_threshold_passed: true,
      private_ledger_exposed: false,
      residual_order_independence_proven: false,
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
  };
}

function seal(overrides = {}) {
  const value = { ...baseEnvelope(), ...overrides };
  return { ...value, presentation_hash: strictCanonicalHash(value) };
}

function blockEnvelope() {
  const baseline = baseEnvelope();
  return seal({
    display_state: "EVIDENCE_BLOCK",
    display_reason: "FINITE_HORIZON_EVIDENCE_BLOCK_VERIFIED",
    source_axis: {
      ...baseline.source_axis,
      consumer_verification_state: "VERIFIED_BLOCK",
    },
    maturity_axis: {
      ...baseline.maturity_axis,
      state: "EVIDENCE_BLOCK",
      observed_maximum: "1.2",
      threshold_relation: "SOURCE_BLOCK_VERIFIED",
      unstable_identity_count: 4,
    },
    phase_comb: {
      ...baseline.phase_comb,
      status: "EVIDENCE_BLOCK",
      observed_maximum: "1.2",
    },
    blocker_count: 3,
    facts: {
      ...baseline.facts,
      finite_horizon_omnibus_guard_bound: false,
      omnibus_quadratic_energy_threshold_passed: false,
    },
  });
}

function unknownEnvelope() {
  const baseline = baseEnvelope();
  const nullHashes = Object.fromEntries(SOURCE_HASH_FIELDS.map((field) => [field, null]));
  return seal({
    display_state: "UNKNOWN",
    display_reason: "SOURCE_NOT_EVALUATED",
    source_state: "UNKNOWN",
    ...nullHashes,
    source_axis: {
      label: "SOURCE",
      state: "UNKNOWN",
      consumer_verification_state: "UNKNOWN",
      consumer_hash: null,
      precommit_gate_v7_hash: null,
      omnibus_gate_v1_hash: null,
    },
    maturity_axis: {
      ...baseline.maturity_axis,
      state: "UNKNOWN",
      observed_maximum: null,
      threshold_relation: "UNKNOWN",
      fold_count: null,
      unstable_identity_count: null,
    },
    phase_comb: {
      ...baseline.phase_comb,
      status: "UNKNOWN",
      observed_maximum: null,
    },
    facts: {
      ...baseline.facts,
      consumer_verified: false,
      finite_horizon_omnibus_guard_bound: false,
      omnibus_quadratic_energy_threshold_passed: false,
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
  assert.equal(constants.SOURCE_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v4");
  assert.equal(constants.SOURCE_FINGERPRINT, "20260914-cross-lag-factor-calibration-precommit-presentation-envelope-4");
  assert.equal(constants.CARD_SCHEMA, "factor-calibration-precommit-finite-horizon-card-v4");
  assert.equal(constants.CARD_FINGERPRINT, "20260915-factor-calibration-precommit-finite-horizon-card-4");
});

test("maps a verified local envelope to four neutral axes", () => {
  const envelope = seal();
  const model = buildFactorCalibrationPrecommitPresentationModelV4(envelope, {
    expectedPresentationHash: envelope.presentation_hash,
  });
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "LOCAL_BINDING");
  assert.deepEqual(model.axes.map(({ label, state }) => [label, state]), [
    ["SOURCE", "VERIFIED LOCAL"],
    ["GAP", "OPEN"],
    ["MATURITY", "LOCAL FINITE-HORIZON BOUND"],
    ["PERMISSION", "LOCKED"],
  ]);
});

test("shows six teeth split into baseline and omnibus bands", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV4(seal());
  assert.deepEqual(model.phase_comb.teeth, [1, 2, 3, 4, 5, 6].map((lag) => ({
    lag,
    coverage: lag <= 3 ? "BASELINE_PREREGISTERED" : "OMNIBUS_PREREGISTERED",
    result_exposed: false,
  })));
  assert.deepEqual(model.phase_comb.omnibus_band_lags, [4, 5, 6]);
  assert.equal(model.phase_comb.private_ledger_exposed, false);
});

test("maps verified omnibus block monotonically", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV4(blockEnvelope());
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "EVIDENCE_BLOCK");
  assert.equal(model.phase_comb.observed_maximum, "1.2");
  assert.equal(model.axes[2].state, "EVIDENCE BLOCK");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("keeps a valid unknown envelope distinct", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV4(unknownEnvelope());
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "UNKNOWN");
  assert.equal(model.phase_comb.observed_maximum, "UNKNOWN");
  assert.equal(model.phase_comb.ceiling, "0.64");
  assert.equal(model.axes[1].state, "OPEN");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("rejects an unsealed payload mutation", () => {
  const envelope = seal();
  envelope.phase_comb.observed_maximum = "0.1";
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(envelope).integrity.reason,
    "HASH_MISMATCH",
  );
});

test("rejects an expected hash mismatch", () => {
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal(), {
      expectedPresentationHash: "f".repeat(64),
    }).integrity.reason,
    "EXPECTED_HASH_MISMATCH",
  );
});

test("rejects resealed schema fingerprint and mount drift", () => {
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ schema_version: "legacy" })).integrity.reason, "UNSUPPORTED_SCHEMA");
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ static_fingerprint: "other" })).integrity.reason, "UNSUPPORTED_FINGERPRINT");
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ presentation_status: "MOUNTED" })).integrity.reason, "MOUNT_STATUS_INVALID");
});

test("rejects extra sealed private fields", () => {
  const model = buildFactorCalibrationPrecommitPresentationModelV4(seal({
    private_ledger: [{ lag: 6, score: "2.4" }],
  }));
  assert.equal(model.integrity.reason, "TOP_LEVEL_CONTRACT_INVALID");
  assert.doesNotMatch(
    JSON.stringify(model),
    /"private_ledger"\s*:|"score"\s*:/,
  );
});

test("rejects resealed authority escalation", () => {
  const authority = clone(baseEnvelope().authority);
  authority.paper_authorized = true;
  const model = buildFactorCalibrationPrecommitPresentationModelV4(seal({ authority }));
  assert.equal(model.integrity.reason, "AUTHORITY_INVALID");
  assert.equal(model.authority.paper_authorized, false);
  assert.equal(model.authority.live_order_allowed, false);
});

test("rejects resealed permission escalation", () => {
  const permissionAxis = clone(baseEnvelope().permission_axis);
  permissionAxis.current_admission_allowed = true;
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ permission_axis: permissionAxis })).integrity.reason,
    "PERMISSION_LOCK_INVALID",
  );
});

test("rejects per-lag result exposure", () => {
  const phaseComb = clone(baseEnvelope().phase_comb);
  phaseComb.teeth[5].result_exposed = true;
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ phase_comb: phaseComb })).integrity.reason,
    "PHASE_COMB_INVALID",
  );
});

test("rejects missing duplicate and reordered teeth", () => {
  const teeth = baseEnvelope().phase_comb.teeth;
  for (const candidate of [
    teeth.slice(0, 5),
    [teeth[0], teeth[1], teeth[2], teeth[3], teeth[4], teeth[4]],
    [teeth[1], teeth[0], ...teeth.slice(2)],
  ]) {
    const phaseComb = { ...baseEnvelope().phase_comb, teeth: candidate };
    assert.equal(
      buildFactorCalibrationPrecommitPresentationModelV4(seal({ phase_comb: phaseComb })).integrity.reason,
      "PHASE_COMB_INVALID",
    );
  }
});

test("rejects baseline and omnibus coverage drift", () => {
  const phaseComb = clone(baseEnvelope().phase_comb);
  phaseComb.teeth[3].coverage = "BASELINE_PREREGISTERED";
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ phase_comb: phaseComb })).integrity.reason,
    "PHASE_COMB_INVALID",
  );
});

test("rejects maturity lag coverage drift", () => {
  const maturityAxis = { ...baseEnvelope().maturity_axis, evaluated_lags: [1, 2, 3, 4, 5, 7] };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ maturity_axis: maturityAxis })).integrity.reason,
    "MATURITY_CONTRACT_INVALID",
  );
});

test("rejects omnibus band and metric drift", () => {
  for (const maturityAxis of [
    { ...baseEnvelope().maturity_axis, omnibus_band_lags: [3, 4, 5] },
    { ...baseEnvelope().maturity_axis, metric: "MAX_ABSOLUTE_LAG" },
  ]) {
    assert.equal(
      buildFactorCalibrationPrecommitPresentationModelV4(seal({ maturity_axis: maturityAxis })).integrity.reason,
      "MATURITY_CONTRACT_INVALID",
    );
  }
});

test("rejects phase and maturity aggregate mismatch", () => {
  const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: "0.3" };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ phase_comb: phaseComb })).integrity.reason,
    "PHASE_COMB_INVALID",
  );
});

test("rejects gap closure and axis relabeling", () => {
  const gapAxis = { ...baseEnvelope().gap_axis, state: "CLOSED" };
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ gap_axis: gapAxis })).integrity.reason, "GAP_LOCK_INVALID");
  const sourceAxis = { ...baseEnvelope().source_axis, label: "SIGNAL" };
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ source_axis: sourceAxis })).integrity.reason, "SOURCE_STATE_INCONSISTENT");
});

test("rejects source state and three-way hash drift", () => {
  const stateAxis = { ...baseEnvelope().source_axis, consumer_verification_state: "VERIFIED_BLOCK" };
  assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ source_axis: stateAxis })).integrity.reason, "SOURCE_STATE_INCONSISTENT");
  for (const key of ["consumer_hash", "precommit_gate_v7_hash", "omnibus_gate_v1_hash"]) {
    const sourceAxis = { ...baseEnvelope().source_axis, [key]: "0".repeat(64) };
    assert.equal(buildFactorCalibrationPrecommitPresentationModelV4(seal({ source_axis: sourceAxis })).integrity.reason, "SOURCE_HASH_CROSS_BIND_INVALID");
  }
});

test("accepts the inclusive Q ceiling without promotion", () => {
  const maturityAxis = { ...baseEnvelope().maturity_axis, observed_maximum: "0.64" };
  const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: "0.64" };
  const model = buildFactorCalibrationPrecommitPresentationModelV4(seal({ maturity_axis: maturityAxis, phase_comb: phaseComb }));
  assert.equal(model.integrity.verified, true);
  assert.equal(model.phase_comb.observed_maximum, "0.64");
  assert.equal(model.axes[3].state, "LOCKED");
});

test("requires block threshold facts to match aggregate Q", () => {
  const block = blockEnvelope();
  const { presentation_hash: _presentationHash, ...unsignedBlock } = block;
  const facts = { ...block.facts, omnibus_quadratic_energy_threshold_passed: true };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({
      ...unsignedBlock,
      facts,
    })).integrity.reason,
    "FACTS_INVALID",
  );
});

test("rejects invalid score grammar and threshold relation drift", () => {
  for (const score of ["NaN", "Infinity", "1e-1", "-0.1", "3.1"]) {
    const maturityAxis = { ...baseEnvelope().maturity_axis, observed_maximum: score };
    const phaseComb = { ...baseEnvelope().phase_comb, observed_maximum: score };
    assert.equal(
      buildFactorCalibrationPrecommitPresentationModelV4(seal({ maturity_axis: maturityAxis, phase_comb: phaseComb })).integrity.verified,
      false,
    );
  }
  const maturityAxis = { ...baseEnvelope().maturity_axis, threshold_relation: "SOURCE_BLOCK_VERIFIED" };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ maturity_axis: maturityAxis })).integrity.reason,
    "LOCAL_BINDING_RELATION_INVALID",
  );
});

test("rejects finite-horizon fact promotion", () => {
  const facts = { ...baseEnvelope().facts, residual_order_independence_proven: true };
  assert.equal(
    buildFactorCalibrationPrecommitPresentationModelV4(seal({ facts })).integrity.reason,
    "FACTS_INVALID",
  );
});

test("renders six teeth and Q aperture through textContent", () => {
  const card = createFactorCalibrationPrecommitEvidenceCardV4({
    document: fakeDocument,
    envelope: seal(),
  });
  const text = collectText(card);
  assert.match(text, /Six-lag residual order instrument/);
  for (const lag of [1, 2, 3, 4, 5, 6]) {
    assert.match(text, new RegExp(`LAG ${lag}`));
  }
  assert.match(text, /Q GUARD/);
  assert.match(text, /Q\(04-06\) AGGREGATE/);
  assert.equal(card.attributes["data-state"], "LOCAL_BINDING");

  const hostileCard = createFactorCalibrationPrecommitEvidenceCardV4({
    document: fakeDocument,
    envelope: seal({ display_reason: "<img src=x onerror=alert(1)>" }),
  });
  const hostileText = collectText(hostileCard);
  assert.doesNotMatch(hostileText, /<img|onerror/);
  assert.equal(hostileCard.attributes["data-state"], "UNKNOWN");
});

test("requires an explicit detached document", () => {
  assert.throws(
    () => createFactorCalibrationPrecommitEvidenceCardV4({ envelope: seal() }),
    /explicit detached document/,
  );
});

test("keeps all public string copy neutral", () => {
  const local = collectStrings(buildFactorCalibrationPrecommitPresentationModelV4(seal())).join(" ");
  const unknown = collectStrings(buildFactorCalibrationPrecommitPresentationModelV4(null)).join(" ");
  assert.doesNotMatch(`${local} ${unknown}`, /\bready\b|\bprofit(?:able|ability)?\b|盈利|收益证明/i);
  for (const label of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
    assert.match(local, new RegExp(label));
  }
});

test("is deterministic for the same sealed envelope", () => {
  const envelope = seal();
  assert.deepEqual(
    buildFactorCalibrationPrecommitPresentationModelV4(envelope),
    buildFactorCalibrationPrecommitPresentationModelV4(clone(envelope)),
  );
});

test("ships scoped dual-band responsive reduced-motion styles", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v4.css"),
    "utf8",
  );
  assert.match(css, /\.fcpc4-card/);
  assert.match(css, /\.fcpc4-band-baseline/);
  assert.match(css, /\.fcpc4-band-omnibus/);
  assert.match(css, /\.fcpc4-guard-seam/);
  assert.match(css, /\.fcpc4-aperture/);
  assert.match(css, /\.fcpc4-tooth-lag-6/);
  assert.match(css, /@media \(max-width: 880px\)/);
  assert.match(css, /@media \(max-width: 500px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(css, /\.ready|\.profit|#00ff00/i);
});

test("contains no implicit page activation hook", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "factor_calibration_precommit_evidence_card_v4.js"),
    "utf8",
  );
  assert.doesNotMatch(source, /require\(["']\.\/app|DOMContentLoaded|document\.querySelector|window\./);
});

assert.equal(count, 29);
process.stdout.write("factor calibration precommit finite-horizon card v4: 29/29 PASS\n");
