"use strict";

const {
  isPlainRecord,
  strictCanonicalHash,
} = require("./strict_canonical_json_v1.js");

const SOURCE_SCHEMA =
  "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v2";
const SOURCE_FINGERPRINT =
  "20260904-cross-lag-factor-calibration-precommit-presentation-envelope-2";
const SOURCE_STATUS = "UNMOUNTED_CANDIDATE";
const CARD_SCHEMA = "factor-calibration-precommit-phase-comb-card-v2";
const CARD_FINGERPRINT = "20260905-factor-calibration-precommit-phase-comb-card-2";

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

const REQUIRED_DENIALS = Object.freeze([
  "presentation_mount_allowed",
  "candidate_activation_allowed",
  "current_admission_allowed",
  "current_pointer_written",
  "paper_authorized",
  "live_order_allowed",
  "profitability_claim_allowed",
]);

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

function axisHasLabel(axis, label) {
  return isPlainRecord(axis) && axis.label === label;
}

function hasLockedAuthority(authority) {
  if (!isPlainRecord(authority) || authority.descriptive_only !== true) {
    return false;
  }
  return REQUIRED_DENIALS.every((key) => authority[key] === false);
}

function validTeeth(teeth) {
  if (!Array.isArray(teeth) || teeth.length !== 2) {
    return false;
  }
  return teeth.every((tooth, index) =>
    isPlainRecord(tooth) &&
    tooth.lag === index + 1 &&
    tooth.coverage === "PREREGISTERED" &&
    tooth.result_exposed === false
  );
}

function verifyEnvelope(envelope, expectedPresentationHash) {
  if (!isPlainRecord(envelope)) {
    return Object.freeze({ ok: false, reason: "MISSING_OR_INVALID_ENVELOPE" });
  }
  if (envelope.schema_version !== SOURCE_SCHEMA) {
    return Object.freeze({ ok: false, reason: "UNSUPPORTED_SCHEMA" });
  }
  if (envelope.static_fingerprint !== SOURCE_FINGERPRINT) {
    return Object.freeze({ ok: false, reason: "UNSUPPORTED_FINGERPRINT" });
  }
  if (envelope.presentation_status !== SOURCE_STATUS) {
    return Object.freeze({ ok: false, reason: "MOUNT_STATUS_INVALID" });
  }

  const actualHash = normalizedHash(envelope.presentation_hash);
  const expectedHash = expectedPresentationHash == null
    ? null
    : normalizedHash(expectedPresentationHash);
  if (!actualHash || (expectedPresentationHash != null && !expectedHash)) {
    return Object.freeze({ ok: false, reason: "HASH_INVALID" });
  }
  if (expectedHash && expectedHash !== actualHash) {
    return Object.freeze({ ok: false, reason: "EXPECTED_HASH_MISMATCH" });
  }

  const unsigned = {};
  for (const key of Object.keys(envelope)) {
    if (key !== "presentation_hash") {
      unsigned[key] = envelope[key];
    }
  }
  if (normalizedHash(strictCanonicalHash(unsigned)) !== actualHash) {
    return Object.freeze({ ok: false, reason: "HASH_MISMATCH" });
  }

  if (!DISPLAY_STATES.has(envelope.display_state)) {
    return Object.freeze({ ok: false, reason: "DISPLAY_STATE_INVALID" });
  }
  if (
    !axisHasLabel(envelope.source_axis, "SOURCE") ||
    !axisHasLabel(envelope.gap_axis, "GAP") ||
    !axisHasLabel(envelope.maturity_axis, "MATURITY") ||
    !axisHasLabel(envelope.permission_axis, "PERMISSION")
  ) {
    return Object.freeze({ ok: false, reason: "AXIS_CONTRACT_INVALID" });
  }
  if (envelope.gap_axis.state !== "OPEN" || envelope.permission_axis.state !== "LOCKED") {
    return Object.freeze({ ok: false, reason: "AXIS_LOCK_INVALID" });
  }
  if (!hasLockedAuthority(envelope.authority)) {
    return Object.freeze({ ok: false, reason: "AUTHORITY_INVALID" });
  }

  const phaseComb = envelope.phase_comb;
  if (
    !isPlainRecord(phaseComb) ||
    phaseComb.status !== envelope.display_state ||
    phaseComb.private_ledger_exposed !== false ||
    !validTeeth(phaseComb.teeth)
  ) {
    return Object.freeze({ ok: false, reason: "PHASE_COMB_INVALID" });
  }
  const ceiling = boundedScore(phaseComb.ceiling);
  const observed = phaseComb.observed_maximum == null
    ? null
    : boundedScore(phaseComb.observed_maximum);
  if (!ceiling || (phaseComb.observed_maximum != null && !observed)) {
    return Object.freeze({ ok: false, reason: "AGGREGATE_INVALID" });
  }

  return Object.freeze({
    ok: true,
    reason: "VERIFIED",
    hash: actualHash,
    ceiling,
    observed,
  });
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
      teeth: Object.freeze([
        Object.freeze({ lag: 1, coverage: "PREREGISTERED", result_exposed: false }),
        Object.freeze({ lag: 2, coverage: "PREREGISTERED", result_exposed: false }),
      ]),
      observed_maximum: "UNKNOWN",
      ceiling: "UNKNOWN",
      private_ledger_exposed: false,
    }),
    provenance: Object.freeze({ presentation_hash: null, source_consumer_hash: null }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT",
      title: "Residual order / phase comb",
      subtitle: "LAG 1 + LAG 2 / AGGREGATE ONLY",
      note: "No verified envelope is available. The gap remains open and permission remains locked.",
    }),
  });
}

function buildFactorCalibrationPrecommitPresentationModelV2(
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
    ? "LOCAL MULTI-LAG BOUND"
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
      source_consumer_hash: normalizedHash(envelope.source_consumer_hash),
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT",
      title: "Residual order / phase comb",
      subtitle: "LAG 1 + LAG 2 / AGGREGATE ONLY",
      note: "Two preregistered lags are shown as coverage. Per-lag results stay private; arbitrary-lag independence and external timing remain unresolved.",
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

function createFactorCalibrationPrecommitEvidenceCardV2({
  document: documentRef,
  envelope,
  expectedPresentationHash = null,
}) {
  if (!documentRef || typeof documentRef.createElement !== "function") {
    throw new TypeError("An explicit detached document is required");
  }
  const model = buildFactorCalibrationPrecommitPresentationModelV2(envelope, {
    expectedPresentationHash,
  });

  const card = documentRef.createElement("section");
  card.className = "fcpc2-card";
  card.setAttribute("data-contract", CARD_SCHEMA);
  card.setAttribute("data-state", model.display_state);

  const header = documentRef.createElement("header");
  header.className = "fcpc2-header";
  const heading = documentRef.createElement("div");
  heading.className = "fcpc2-heading";
  addText(documentRef, heading, "p", "fcpc2-eyebrow", model.copy.eyebrow);
  addText(documentRef, heading, "h2", "fcpc2-title", model.copy.title);
  addText(documentRef, heading, "p", "fcpc2-subtitle", model.copy.subtitle);
  header.appendChild(heading);
  addText(documentRef, header, "span", "fcpc2-state", model.display_label);
  card.appendChild(header);

  const comb = documentRef.createElement("div");
  comb.className = "fcpc2-comb";
  model.phase_comb.teeth.forEach((tooth) => {
    const toothNode = documentRef.createElement("div");
    toothNode.className = `fcpc2-tooth fcpc2-tooth-lag-${tooth.lag}`;
    addText(documentRef, toothNode, "span", "fcpc2-lag", `LAG ${tooth.lag}`);
    addText(documentRef, toothNode, "span", "fcpc2-coverage", tooth.coverage);
    comb.appendChild(toothNode);
  });
  const aggregate = documentRef.createElement("div");
  aggregate.className = "fcpc2-aggregate";
  addText(documentRef, aggregate, "span", "fcpc2-aggregate-label", "AGGREGATE MAX");
  addText(
    documentRef,
    aggregate,
    "strong",
    "fcpc2-aggregate-value",
    model.phase_comb.observed_maximum,
  );
  addText(
    documentRef,
    aggregate,
    "span",
    "fcpc2-ceiling",
    `CEILING ${model.phase_comb.ceiling}`,
  );
  comb.appendChild(aggregate);
  card.appendChild(comb);

  const axes = documentRef.createElement("div");
  axes.className = "fcpc2-axes";
  model.axes.forEach((axis) => {
    const axisNode = documentRef.createElement("div");
    axisNode.className = "fcpc2-axis";
    addText(documentRef, axisNode, "span", "fcpc2-axis-label", axis.label);
    addText(documentRef, axisNode, "strong", "fcpc2-axis-state", axis.state);
    axes.appendChild(axisNode);
  });
  card.appendChild(axes);

  addText(documentRef, card, "p", "fcpc2-note", model.copy.note);
  const hash = model.provenance.presentation_hash;
  addText(
    documentRef,
    card,
    "p",
    "fcpc2-provenance",
    hash ? `ENVELOPE ${hash.slice(0, 12)}` : "ENVELOPE UNVERIFIED",
  );
  return card;
}

module.exports = {
  buildFactorCalibrationPrecommitPresentationModelV2,
  constants: Object.freeze({
    CARD_FINGERPRINT,
    CARD_SCHEMA,
    SOURCE_FINGERPRINT,
    SOURCE_SCHEMA,
    SOURCE_STATUS,
  }),
  contractTestHooks: Object.freeze({ boundedScore, verifyEnvelope }),
  createFactorCalibrationPrecommitEvidenceCardV2,
};
