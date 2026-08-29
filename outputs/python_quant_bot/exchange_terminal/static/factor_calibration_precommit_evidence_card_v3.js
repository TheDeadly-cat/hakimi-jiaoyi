"use strict";

const {
  isPlainRecord,
  strictCanonicalHash,
} = require("./strict_canonical_json_v1.js");

const SOURCE_SCHEMA =
  "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v3";
const SOURCE_FINGERPRINT =
  "20260909-cross-lag-factor-calibration-precommit-presentation-envelope-3";
const SOURCE_STATUS = "UNMOUNTED_CANDIDATE";
const CARD_SCHEMA = "factor-calibration-precommit-phase-comb-card-v3";
const CARD_FINGERPRINT = "20260910-factor-calibration-precommit-phase-comb-card-3";

const DISPLAY_STATES = new Set([
  "LOCAL_BINDING",
  "EVIDENCE_BLOCK",
  "UNKNOWN",
]);

const STATE_LABELS = Object.freeze({
  LOCAL_BINDING: "LOCAL BINDING",
  EVIDENCE_BLOCK: "EVIDENCE BLOCK",
  UNKNOWN: "UNKNOWN",
});

const SOURCE_HASH_FIELDS = Object.freeze([
  "source_consumer_hash",
  "source_gate_hash",
  "source_precommit_gate_v5_hash",
  "source_report_consumer_v5_hash",
  "source_residual_order_gate_v3_hash",
  "source_residual_order_gate_v2_hash",
  "source_residual_order_gate_v1_hash",
  "source_beta_stability_gate_hash",
  "source_replay_hash",
  "source_registration_hash",
  "source_calibration_observations_hash",
]);

const TOP_LEVEL_KEYS = Object.freeze([
  "schema_version",
  "static_fingerprint",
  "presentation_status",
  "display_state",
  "display_reason",
  "blocker_count",
  ...SOURCE_HASH_FIELDS,
  "source_state",
  "source_axis",
  "gap_axis",
  "maturity_axis",
  "permission_axis",
  "phase_comb",
  "authority",
  "facts",
  "presentation_hash",
]);

const REQUIRED_DENIALS = Object.freeze([
  "presentation_mount_allowed",
  "candidate_activation_allowed",
  "current_admission_allowed",
  "current_pointer_written",
  "paper_authorized",
  "live_order_allowed",
  "profitability_claim_allowed",
]);

function hasOwn(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function hasExactKeys(value, expectedKeys) {
  if (!isPlainRecord(value)) {
    return false;
  }
  const actualKeys = Object.keys(value);
  return actualKeys.length === expectedKeys.length &&
    expectedKeys.every((key) => hasOwn(value, key));
}

function normalizedHash(value) {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/i.test(value)) {
    return null;
  }
  return value.toLowerCase();
}

function boundedScore(value) {
  if (typeof value !== "string" && typeof value !== "number") {
    return null;
  }
  const text = String(value);
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(text)) {
    return null;
  }
  const numeric = Number(text);
  if (!Number.isFinite(numeric) || numeric < 0 || numeric > 1) {
    return null;
  }
  return Object.freeze({ numeric, text });
}

function nonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function validTeeth(teeth) {
  if (!Array.isArray(teeth) || teeth.length !== 3) {
    return false;
  }
  return teeth.every((tooth, index) =>
    hasExactKeys(tooth, ["lag", "coverage", "result_exposed"]) &&
    tooth.lag === index + 1 &&
    tooth.coverage === "PREREGISTERED" &&
    tooth.result_exposed === false
  );
}

function invalid(reason) {
  return Object.freeze({ ok: false, reason });
}

function verifyEnvelope(envelope, expectedPresentationHash) {
  if (!isPlainRecord(envelope)) {
    return invalid("MISSING_OR_INVALID_ENVELOPE");
  }
  if (envelope.schema_version !== SOURCE_SCHEMA) {
    return invalid("UNSUPPORTED_SCHEMA");
  }
  if (envelope.static_fingerprint !== SOURCE_FINGERPRINT) {
    return invalid("UNSUPPORTED_FINGERPRINT");
  }
  if (envelope.presentation_status !== SOURCE_STATUS) {
    return invalid("MOUNT_STATUS_INVALID");
  }
  if (!hasExactKeys(envelope, TOP_LEVEL_KEYS)) {
    return invalid("TOP_LEVEL_CONTRACT_INVALID");
  }

  const actualHash = normalizedHash(envelope.presentation_hash);
  const expectedHash = expectedPresentationHash == null
    ? null
    : normalizedHash(expectedPresentationHash);
  if (!actualHash || (expectedPresentationHash != null && !expectedHash)) {
    return invalid("HASH_INVALID");
  }
  if (expectedHash && expectedHash !== actualHash) {
    return invalid("EXPECTED_HASH_MISMATCH");
  }

  const unsigned = {};
  for (const key of Object.keys(envelope)) {
    if (key !== "presentation_hash") {
      unsigned[key] = envelope[key];
    }
  }
  let computedHash;
  try {
    computedHash = normalizedHash(strictCanonicalHash(unsigned));
  } catch (_error) {
    return invalid("HASH_PAYLOAD_INVALID");
  }
  if (computedHash !== actualHash) {
    return invalid("HASH_MISMATCH");
  }

  if (!DISPLAY_STATES.has(envelope.display_state)) {
    return invalid("DISPLAY_STATE_INVALID");
  }
  if (
    typeof envelope.display_reason !== "string" ||
    envelope.display_reason.length === 0 ||
    typeof envelope.source_state !== "string" ||
    envelope.source_state.length === 0 ||
    !nonNegativeInteger(envelope.blocker_count)
  ) {
    return invalid("SUMMARY_CONTRACT_INVALID");
  }

  const sourceAxis = envelope.source_axis;
  const gapAxis = envelope.gap_axis;
  const maturityAxis = envelope.maturity_axis;
  const permissionAxis = envelope.permission_axis;
  const phaseComb = envelope.phase_comb;
  const authority = envelope.authority;
  const facts = envelope.facts;

  if (!hasExactKeys(sourceAxis, [
    "label",
    "state",
    "consumer_verification_state",
    "consumer_hash",
    "gate_hash",
  ])) {
    return invalid("SOURCE_AXIS_INVALID");
  }
  if (!hasExactKeys(gapAxis, [
    "label",
    "state",
    "gap_code",
    "arbitrary_lag_independence_unresolved",
    "external_timing_unresolved",
  ])) {
    return invalid("GAP_AXIS_INVALID");
  }
  if (!hasExactKeys(maturityAxis, [
    "label",
    "state",
    "evaluated_lags",
    "maximum_evaluated_lag",
    "observed_maximum",
    "ceiling",
    "threshold_relation",
    "unstable_identity_count",
  ])) {
    return invalid("MATURITY_AXIS_INVALID");
  }
  if (!hasExactKeys(permissionAxis, [
    "label",
    "state",
    "current_admission_allowed",
    "paper_authorized",
    "live_order_allowed",
    "profitability_claim_allowed",
  ])) {
    return invalid("PERMISSION_AXIS_INVALID");
  }
  if (!hasExactKeys(phaseComb, [
    "status",
    "teeth",
    "observed_maximum",
    "ceiling",
    "private_ledger_exposed",
  ])) {
    return invalid("PHASE_COMB_INVALID");
  }
  if (!hasExactKeys(authority, ["descriptive_only", ...REQUIRED_DENIALS])) {
    return invalid("AUTHORITY_INVALID");
  }
  if (!hasExactKeys(facts, [
    "aggregate_only",
    "consumer_verified",
    "four_axis_separation_preserved",
    "private_ledger_exposed",
    "residual_order_independence_proven",
  ])) {
    return invalid("FACTS_INVALID");
  }

  const expectedSourceState = envelope.display_state === "UNKNOWN"
    ? "UNKNOWN"
    : "VERIFIED";
  const expectedConsumerState = envelope.display_state === "LOCAL_BINDING"
    ? "VERIFIED_LOCAL_BINDING"
    : envelope.display_state === "EVIDENCE_BLOCK" ? "VERIFIED_BLOCK" : "UNKNOWN";
  if (
    sourceAxis.label !== "SOURCE" ||
    sourceAxis.state !== expectedSourceState ||
    sourceAxis.consumer_verification_state !== expectedConsumerState
  ) {
    return invalid("SOURCE_STATE_INCONSISTENT");
  }

  const normalizedSources = {};
  for (const field of SOURCE_HASH_FIELDS) {
    const value = envelope[field];
    const hash = value == null ? null : normalizedHash(value);
    if ((value != null && !hash) || (envelope.display_state !== "UNKNOWN" && !hash)) {
      return invalid("SOURCE_HASH_INVALID");
    }
    normalizedSources[field] = hash;
  }
  const axisConsumerHash = sourceAxis.consumer_hash == null
    ? null
    : normalizedHash(sourceAxis.consumer_hash);
  const axisGateHash = sourceAxis.gate_hash == null
    ? null
    : normalizedHash(sourceAxis.gate_hash);
  if (
    (sourceAxis.consumer_hash != null && !axisConsumerHash) ||
    (sourceAxis.gate_hash != null && !axisGateHash) ||
    axisConsumerHash !== normalizedSources.source_consumer_hash ||
    axisGateHash !== normalizedSources.source_gate_hash
  ) {
    return invalid("SOURCE_HASH_CROSS_BIND_INVALID");
  }

  if (
    gapAxis.label !== "GAP" ||
    gapAxis.state !== "OPEN" ||
    gapAxis.gap_code !== "ARBITRARY_LAG_AND_EXTERNAL_TIMING_UNRESOLVED" ||
    gapAxis.arbitrary_lag_independence_unresolved !== true ||
    gapAxis.external_timing_unresolved !== true
  ) {
    return invalid("GAP_LOCK_INVALID");
  }
  if (
    permissionAxis.label !== "PERMISSION" ||
    permissionAxis.state !== "LOCKED" ||
    permissionAxis.current_admission_allowed !== false ||
    permissionAxis.paper_authorized !== false ||
    permissionAxis.live_order_allowed !== false ||
    permissionAxis.profitability_claim_allowed !== false
  ) {
    return invalid("PERMISSION_LOCK_INVALID");
  }
  if (
    authority.descriptive_only !== true ||
    !REQUIRED_DENIALS.every((key) => authority[key] === false)
  ) {
    return invalid("AUTHORITY_INVALID");
  }

  const expectedMaturityState = envelope.display_state === "LOCAL_BINDING"
    ? "LOCAL_THREE_LAG_BOUND"
    : envelope.display_state === "EVIDENCE_BLOCK" ? "EVIDENCE_BLOCK" : "UNKNOWN";
  if (
    maturityAxis.label !== "MATURITY" ||
    maturityAxis.state !== expectedMaturityState ||
    !Array.isArray(maturityAxis.evaluated_lags) ||
    maturityAxis.evaluated_lags.length !== 3 ||
    maturityAxis.evaluated_lags.some((lag, index) => lag !== index + 1) ||
    maturityAxis.maximum_evaluated_lag !== 3 ||
    maturityAxis.ceiling !== "0.8" ||
    !nonNegativeInteger(maturityAxis.unstable_identity_count)
  ) {
    return invalid("MATURITY_CONTRACT_INVALID");
  }
  if (
    phaseComb.status !== envelope.display_state ||
    phaseComb.private_ledger_exposed !== false ||
    phaseComb.ceiling !== maturityAxis.ceiling ||
    phaseComb.observed_maximum !== maturityAxis.observed_maximum ||
    !validTeeth(phaseComb.teeth)
  ) {
    return invalid("PHASE_COMB_INVALID");
  }

  const ceiling = boundedScore(phaseComb.ceiling);
  const observed = phaseComb.observed_maximum == null
    ? null
    : boundedScore(phaseComb.observed_maximum);
  if (!ceiling || ceiling.numeric !== 0.8) {
    return invalid("CEILING_INVALID");
  }
  if (envelope.display_state === "UNKNOWN") {
    if (observed || maturityAxis.threshold_relation !== "UNKNOWN") {
      return invalid("UNKNOWN_AGGREGATE_INVALID");
    }
  } else if (!observed) {
    return invalid("OBSERVED_AGGREGATE_INVALID");
  }
  if (
    maturityAxis.threshold_relation === "AT_OR_BELOW_CEILING" &&
    (!observed || observed.numeric > ceiling.numeric)
  ) {
    return invalid("THRESHOLD_RELATION_INVALID");
  }
  if (
    maturityAxis.threshold_relation === "ABOVE_CEILING" &&
    (!observed || observed.numeric <= ceiling.numeric)
  ) {
    return invalid("THRESHOLD_RELATION_INVALID");
  }
  if (
    envelope.display_state === "LOCAL_BINDING" &&
    maturityAxis.threshold_relation !== "AT_OR_BELOW_CEILING"
  ) {
    return invalid("LOCAL_BINDING_RELATION_INVALID");
  }
  if (
    envelope.display_state === "EVIDENCE_BLOCK" &&
    maturityAxis.threshold_relation !== "SOURCE_BLOCK_VERIFIED"
  ) {
    return invalid("BLOCK_RELATION_INVALID");
  }

  const expectedConsumerVerified = envelope.display_state !== "UNKNOWN";
  if (
    facts.aggregate_only !== true ||
    facts.consumer_verified !== expectedConsumerVerified ||
    facts.four_axis_separation_preserved !== true ||
    facts.private_ledger_exposed !== false ||
    facts.residual_order_independence_proven !== false
  ) {
    return invalid("FACTS_INVALID");
  }

  return Object.freeze({
    ok: true,
    reason: "VERIFIED",
    hash: actualHash,
    ceiling,
    observed,
    sources: Object.freeze(normalizedSources),
  });
}

function frozenTeeth() {
  return Object.freeze([1, 2, 3].map((lag) => Object.freeze({
    lag,
    coverage: "PREREGISTERED",
    result_exposed: false,
  })));
}

function unknownModel(reason) {
  return Object.freeze({
    schema_version: CARD_SCHEMA,
    static_fingerprint: CARD_FINGERPRINT,
    presentation_status: SOURCE_STATUS,
    display_state: "UNKNOWN",
    display_label: STATE_LABELS.UNKNOWN,
    integrity: Object.freeze({ verified: false, reason }),
    axes: Object.freeze([
      Object.freeze({ label: "SOURCE", state: "UNKNOWN" }),
      Object.freeze({ label: "GAP", state: "OPEN" }),
      Object.freeze({ label: "MATURITY", state: "UNKNOWN" }),
      Object.freeze({ label: "PERMISSION", state: "LOCKED" }),
    ]),
    phase_comb: Object.freeze({
      teeth: frozenTeeth(),
      observed_maximum: "UNKNOWN",
      ceiling: "UNKNOWN",
      private_ledger_exposed: false,
    }),
    provenance: Object.freeze({
      presentation_hash: null,
      source_consumer_hash: null,
      source_gate_hash: null,
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 03",
      title: "Three-lag residual phase comb",
      subtitle: "PREREGISTERED COVERAGE / AGGREGATE ONLY",
      note: "No verified envelope is available. The evidence gap remains open and permission remains locked.",
    }),
  });
}

function buildFactorCalibrationPrecommitPresentationModelV3(
  envelope,
  { expectedPresentationHash = null } = {},
) {
  const verification = verifyEnvelope(envelope, expectedPresentationHash);
  if (!verification.ok) {
    return unknownModel(verification.reason);
  }

  const displayState = envelope.display_state;
  const sourceState = displayState === "LOCAL_BINDING"
    ? "VERIFIED LOCAL"
    : displayState === "EVIDENCE_BLOCK" ? "VERIFIED BLOCK" : "UNKNOWN";
  const maturityState = displayState === "LOCAL_BINDING"
    ? "LOCAL THREE-LAG BOUND"
    : displayState === "EVIDENCE_BLOCK" ? "EVIDENCE BLOCK" : "UNKNOWN";

  return Object.freeze({
    schema_version: CARD_SCHEMA,
    static_fingerprint: CARD_FINGERPRINT,
    presentation_status: SOURCE_STATUS,
    display_state: displayState,
    display_label: STATE_LABELS[displayState],
    integrity: Object.freeze({ verified: true, reason: verification.reason }),
    axes: Object.freeze([
      Object.freeze({ label: "SOURCE", state: sourceState }),
      Object.freeze({ label: "GAP", state: "OPEN" }),
      Object.freeze({ label: "MATURITY", state: maturityState }),
      Object.freeze({ label: "PERMISSION", state: "LOCKED" }),
    ]),
    phase_comb: Object.freeze({
      teeth: Object.freeze(envelope.phase_comb.teeth.map((tooth) => Object.freeze({
        lag: tooth.lag,
        coverage: tooth.coverage,
        result_exposed: false,
      }))),
      observed_maximum: verification.observed ? verification.observed.text : "UNKNOWN",
      ceiling: verification.ceiling.text,
      private_ledger_exposed: false,
    }),
    provenance: Object.freeze({
      presentation_hash: verification.hash,
      source_consumer_hash: verification.sources.source_consumer_hash,
      source_gate_hash: verification.sources.source_gate_hash,
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 03",
      title: "Three-lag residual phase comb",
      subtitle: "PREREGISTERED COVERAGE / AGGREGATE ONLY",
      note: "Three preregistered lags are coverage markers, not independent results. Arbitrary-lag independence and external timing remain unresolved.",
    }),
  });
}

function addText(documentRef, parent, tagName, className, text) {
  const node = documentRef.createElement(tagName);
  node.className = className;
  node.textContent = String(text);
  parent.appendChild(node);
  return node;
}

function createFactorCalibrationPrecommitEvidenceCardV3({
  document: documentRef,
  envelope,
  expectedPresentationHash = null,
}) {
  if (!documentRef || typeof documentRef.createElement !== "function") {
    throw new TypeError("An explicit detached document is required");
  }
  const model = buildFactorCalibrationPrecommitPresentationModelV3(envelope, {
    expectedPresentationHash,
  });

  const card = documentRef.createElement("section");
  card.className = "fcpc3-card";
  card.setAttribute("data-contract", CARD_SCHEMA);
  card.setAttribute("data-state", model.display_state);
  card.setAttribute("aria-label", "Three-lag residual phase-comb evidence");

  const header = documentRef.createElement("header");
  header.className = "fcpc3-header";
  const heading = documentRef.createElement("div");
  heading.className = "fcpc3-heading";
  addText(documentRef, heading, "p", "fcpc3-eyebrow", model.copy.eyebrow);
  addText(documentRef, heading, "h2", "fcpc3-title", model.copy.title);
  addText(documentRef, heading, "p", "fcpc3-subtitle", model.copy.subtitle);
  header.appendChild(heading);
  const stamp = documentRef.createElement("div");
  stamp.className = "fcpc3-stamp";
  addText(documentRef, stamp, "span", "fcpc3-stamp-index", "LAG / 01-03");
  addText(documentRef, stamp, "strong", "fcpc3-state", model.display_label);
  header.appendChild(stamp);
  card.appendChild(header);

  const railLabel = documentRef.createElement("div");
  railLabel.className = "fcpc3-rail-label";
  addText(documentRef, railLabel, "span", "fcpc3-rail-kicker", "PHASE COMB");
  addText(documentRef, railLabel, "span", "fcpc3-rail-detail", "COVERAGE, NOT PER-LAG RESULT");
  card.appendChild(railLabel);

  const comb = documentRef.createElement("div");
  comb.className = "fcpc3-comb";
  model.phase_comb.teeth.forEach((tooth) => {
    const toothNode = documentRef.createElement("div");
    toothNode.className = `fcpc3-tooth fcpc3-tooth-lag-${tooth.lag}`;
    toothNode.setAttribute("data-lag", tooth.lag);
    addText(documentRef, toothNode, "span", "fcpc3-lag-index", `0${tooth.lag}`);
    addText(documentRef, toothNode, "strong", "fcpc3-lag", `LAG ${tooth.lag}`);
    addText(documentRef, toothNode, "span", "fcpc3-coverage", tooth.coverage);
    comb.appendChild(toothNode);
  });
  const aggregate = documentRef.createElement("div");
  aggregate.className = "fcpc3-aggregate";
  addText(documentRef, aggregate, "span", "fcpc3-aggregate-label", "AGGREGATE MAX");
  addText(
    documentRef,
    aggregate,
    "strong",
    "fcpc3-aggregate-value",
    model.phase_comb.observed_maximum,
  );
  addText(
    documentRef,
    aggregate,
    "span",
    "fcpc3-ceiling",
    `CEILING ${model.phase_comb.ceiling}`,
  );
  comb.appendChild(aggregate);
  card.appendChild(comb);

  const axes = documentRef.createElement("div");
  axes.className = "fcpc3-axes";
  model.axes.forEach((axis, index) => {
    const axisNode = documentRef.createElement("div");
    axisNode.className = "fcpc3-axis";
    addText(documentRef, axisNode, "span", "fcpc3-axis-index", `0${index + 1}`);
    addText(documentRef, axisNode, "span", "fcpc3-axis-label", axis.label);
    addText(documentRef, axisNode, "strong", "fcpc3-axis-state", axis.state);
    axes.appendChild(axisNode);
  });
  card.appendChild(axes);

  const footer = documentRef.createElement("footer");
  footer.className = "fcpc3-footer";
  addText(documentRef, footer, "p", "fcpc3-note", model.copy.note);
  const hash = model.provenance.presentation_hash;
  addText(
    documentRef,
    footer,
    "p",
    "fcpc3-provenance",
    hash ? `ENVELOPE ${hash.slice(0, 12)}` : "ENVELOPE UNVERIFIED",
  );
  card.appendChild(footer);
  return card;
}

module.exports = {
  buildFactorCalibrationPrecommitPresentationModelV3,
  constants: Object.freeze({
    CARD_FINGERPRINT,
    CARD_SCHEMA,
    SOURCE_FINGERPRINT,
    SOURCE_SCHEMA,
    SOURCE_STATUS,
  }),
  contractTestHooks: Object.freeze({
    boundedScore,
    hasExactKeys,
    verifyEnvelope,
  }),
  createFactorCalibrationPrecommitEvidenceCardV3,
};
