"use strict";

const {
  isPlainRecord,
  strictCanonicalHash,
} = require("./strict_canonical_json_v1.js");

const SOURCE_SCHEMA =
  "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v4";
const SOURCE_FINGERPRINT =
  "20260914-cross-lag-factor-calibration-precommit-presentation-envelope-4";
const SOURCE_STATUS = "UNMOUNTED_CANDIDATE";
const CARD_SCHEMA = "factor-calibration-precommit-finite-horizon-card-v4";
const CARD_FINGERPRINT =
  "20260915-factor-calibration-precommit-finite-horizon-card-4";

const EVALUATED_LAGS = Object.freeze([1, 2, 3, 4, 5, 6]);
const OMNIBUS_BAND_LAGS = Object.freeze([4, 5, 6]);
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
]);

const TOP_LEVEL_KEYS = Object.freeze([
  "schema_version",
  "static_fingerprint",
  "presentation_status",
  "display_state",
  "display_reason",
  "source_state",
  ...SOURCE_HASH_FIELDS,
  "source_axis",
  "gap_axis",
  "maturity_axis",
  "permission_axis",
  "phase_comb",
  "blocker_count",
  "facts",
  "authority",
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

function finiteHorizonScore(value) {
  if (typeof value !== "string" && typeof value !== "number") {
    return null;
  }
  const text = String(value);
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(text)) {
    return null;
  }
  const numeric = Number(text);
  if (!Number.isFinite(numeric) || numeric < 0 || numeric > 3) {
    return null;
  }
  return Object.freeze({ numeric, text });
}

function nonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function exactIntegerArray(value, expected) {
  return Array.isArray(value) &&
    value.length === expected.length &&
    value.every((item, index) => item === expected[index]);
}

function expectedCoverage(lag) {
  return lag <= 3
    ? "BASELINE_PREREGISTERED"
    : "OMNIBUS_PREREGISTERED";
}

function validTeeth(teeth) {
  if (!Array.isArray(teeth) || teeth.length !== EVALUATED_LAGS.length) {
    return false;
  }
  return teeth.every((tooth, index) => {
    const lag = EVALUATED_LAGS[index];
    return hasExactKeys(tooth, ["lag", "coverage", "result_exposed"]) &&
      tooth.lag === lag &&
      tooth.coverage === expectedCoverage(lag) &&
      tooth.result_exposed === false;
  });
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
    "precommit_gate_v7_hash",
    "omnibus_gate_v1_hash",
  ])) {
    return invalid("SOURCE_AXIS_INVALID");
  }
  if (!hasExactKeys(gapAxis, [
    "label",
    "state",
    "gap_code",
    "arbitrary_lag_independence_unresolved",
    "external_timing_unresolved",
    "lags_above_six_unresolved",
  ])) {
    return invalid("GAP_AXIS_INVALID");
  }
  if (!hasExactKeys(maturityAxis, [
    "label",
    "state",
    "evaluated_lags",
    "omnibus_band_lags",
    "maximum_evaluated_lag",
    "metric",
    "observed_maximum",
    "ceiling",
    "threshold_relation",
    "fold_count",
    "unstable_identity_count",
  ])) {
    return invalid("MATURITY_AXIS_INVALID");
  }
  if (!hasExactKeys(permissionAxis, [
    "label",
    "state",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "profitability_claim_allowed",
  ])) {
    return invalid("PERMISSION_AXIS_INVALID");
  }
  if (!hasExactKeys(phaseComb, [
    "status",
    "teeth",
    "omnibus_band_lags",
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
    "finite_horizon_omnibus_guard_bound",
    "four_axis_separation_preserved",
    "lags_above_six_unresolved",
    "omnibus_quadratic_energy_threshold_passed",
    "private_ledger_exposed",
    "residual_order_independence_proven",
  ])) {
    return invalid("FACTS_INVALID");
  }

  const observedState = envelope.display_state !== "UNKNOWN";
  const expectedSourceState = observedState ? "VERIFIED" : "UNKNOWN";
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
    if ((value != null && !hash) || (observedState && !hash) || (!observedState && value != null)) {
      return invalid("SOURCE_HASH_INVALID");
    }
    normalizedSources[field] = hash;
  }
  const axisHashes = {
    source_consumer_hash: sourceAxis.consumer_hash,
    source_precommit_gate_v7_hash: sourceAxis.precommit_gate_v7_hash,
    source_omnibus_gate_v1_hash: sourceAxis.omnibus_gate_v1_hash,
  };
  for (const [field, value] of Object.entries(axisHashes)) {
    const hash = value == null ? null : normalizedHash(value);
    if ((value != null && !hash) || hash !== normalizedSources[field]) {
      return invalid("SOURCE_HASH_CROSS_BIND_INVALID");
    }
  }

  if (
    gapAxis.label !== "GAP" ||
    gapAxis.state !== "OPEN" ||
    gapAxis.gap_code !== "LAGS_ABOVE_SIX_AND_EXTERNAL_TIMING_UNRESOLVED" ||
    gapAxis.arbitrary_lag_independence_unresolved !== true ||
    gapAxis.external_timing_unresolved !== true ||
    gapAxis.lags_above_six_unresolved !== true
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
    ? "LOCAL_FINITE_HORIZON_BOUND"
    : envelope.display_state === "EVIDENCE_BLOCK" ? "EVIDENCE_BLOCK" : "UNKNOWN";
  if (
    maturityAxis.label !== "MATURITY" ||
    maturityAxis.state !== expectedMaturityState ||
    !exactIntegerArray(maturityAxis.evaluated_lags, EVALUATED_LAGS) ||
    !exactIntegerArray(maturityAxis.omnibus_band_lags, OMNIBUS_BAND_LAGS) ||
    maturityAxis.maximum_evaluated_lag !== 6 ||
    maturityAxis.metric !== "LAG_BAND_QUADRATIC_ENERGY" ||
    maturityAxis.ceiling !== "0.64"
  ) {
    return invalid("MATURITY_CONTRACT_INVALID");
  }
  if (
    phaseComb.status !== envelope.display_state ||
    phaseComb.private_ledger_exposed !== false ||
    !exactIntegerArray(phaseComb.omnibus_band_lags, OMNIBUS_BAND_LAGS) ||
    phaseComb.ceiling !== maturityAxis.ceiling ||
    phaseComb.observed_maximum !== maturityAxis.observed_maximum ||
    !validTeeth(phaseComb.teeth)
  ) {
    return invalid("PHASE_COMB_INVALID");
  }

  const ceiling = finiteHorizonScore(phaseComb.ceiling);
  const observed = phaseComb.observed_maximum == null
    ? null
    : finiteHorizonScore(phaseComb.observed_maximum);
  if (!ceiling || ceiling.numeric !== 0.64) {
    return invalid("CEILING_INVALID");
  }
  if (!observedState) {
    if (
      observed ||
      maturityAxis.threshold_relation !== "UNKNOWN" ||
      maturityAxis.fold_count !== null ||
      maturityAxis.unstable_identity_count !== null
    ) {
      return invalid("UNKNOWN_AGGREGATE_INVALID");
    }
  } else if (
    !observed ||
    !nonNegativeInteger(maturityAxis.fold_count) ||
    !nonNegativeInteger(maturityAxis.unstable_identity_count)
  ) {
    return invalid("OBSERVED_AGGREGATE_INVALID");
  }
  if (
    envelope.display_state === "LOCAL_BINDING" &&
    (
      maturityAxis.threshold_relation !== "AT_OR_BELOW_CEILING" ||
      !observed ||
      observed.numeric > ceiling.numeric ||
      envelope.display_reason !== "FINITE_HORIZON_LOCAL_BINDING_VERIFIED"
    )
  ) {
    return invalid("LOCAL_BINDING_RELATION_INVALID");
  }
  if (
    envelope.display_state === "EVIDENCE_BLOCK" &&
    (
      maturityAxis.threshold_relation !== "SOURCE_BLOCK_VERIFIED" ||
      envelope.display_reason !== "FINITE_HORIZON_EVIDENCE_BLOCK_VERIFIED"
    )
  ) {
    return invalid("BLOCK_RELATION_INVALID");
  }

  const thresholdPassed = observedState && observed.numeric <= ceiling.numeric;
  if (
    facts.aggregate_only !== true ||
    facts.consumer_verified !== observedState ||
    facts.finite_horizon_omnibus_guard_bound !== (envelope.display_state === "LOCAL_BINDING") ||
    facts.four_axis_separation_preserved !== true ||
    facts.lags_above_six_unresolved !== true ||
    facts.omnibus_quadratic_energy_threshold_passed !== thresholdPassed ||
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
  return Object.freeze(EVALUATED_LAGS.map((lag) => Object.freeze({
    lag,
    coverage: expectedCoverage(lag),
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
      omnibus_band_lags: OMNIBUS_BAND_LAGS,
      observed_maximum: "UNKNOWN",
      ceiling: "UNKNOWN",
      private_ledger_exposed: false,
    }),
    provenance: Object.freeze({
      presentation_hash: null,
      source_consumer_hash: null,
      source_precommit_gate_v7_hash: null,
      source_omnibus_gate_v1_hash: null,
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 04",
      title: "Six-lag residual order instrument",
      subtitle: "BASELINE 01-03 / OMNIBUS 04-06 / AGGREGATE Q ONLY",
      note: "No verified envelope is available. The evidence gap remains open and permission remains locked.",
    }),
  });
}

function buildFactorCalibrationPrecommitPresentationModelV4(
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
    ? "LOCAL FINITE-HORIZON BOUND"
    : displayState === "EVIDENCE_BLOCK" ? "EVIDENCE BLOCK" : "UNKNOWN";
  const note = displayState === "UNKNOWN"
    ? "The sealed source is explicitly unknown. Lags above 6 and external timing remain unresolved; permission stays locked."
    : "Six preregistered lags are coverage markers. Q summarizes lags 4-6; no per-lag result is displayed. Lags above 6 and external timing remain unresolved.";

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
      omnibus_band_lags: OMNIBUS_BAND_LAGS,
      observed_maximum: verification.observed ? verification.observed.text : "UNKNOWN",
      ceiling: verification.ceiling.text,
      private_ledger_exposed: false,
    }),
    provenance: Object.freeze({
      presentation_hash: verification.hash,
      source_consumer_hash: verification.sources.source_consumer_hash,
      source_precommit_gate_v7_hash: verification.sources.source_precommit_gate_v7_hash,
      source_omnibus_gate_v1_hash: verification.sources.source_omnibus_gate_v1_hash,
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 04",
      title: "Six-lag residual order instrument",
      subtitle: "BASELINE 01-03 / OMNIBUS 04-06 / AGGREGATE Q ONLY",
      note,
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

function appendBand(documentRef, parent, label, range, teeth, className) {
  const band = documentRef.createElement("section");
  band.className = `fcpc4-band ${className}`;
  const header = documentRef.createElement("header");
  header.className = "fcpc4-band-header";
  addText(documentRef, header, "strong", "fcpc4-band-label", label);
  addText(documentRef, header, "span", "fcpc4-band-range", range);
  band.appendChild(header);
  const grid = documentRef.createElement("div");
  grid.className = "fcpc4-band-grid";
  teeth.forEach((tooth) => {
    const toothNode = documentRef.createElement("div");
    toothNode.className = `fcpc4-tooth fcpc4-tooth-lag-${tooth.lag}`;
    toothNode.setAttribute("data-lag", tooth.lag);
    addText(documentRef, toothNode, "span", "fcpc4-lag-index", String(tooth.lag).padStart(2, "0"));
    addText(documentRef, toothNode, "strong", "fcpc4-lag", `LAG ${tooth.lag}`);
    addText(documentRef, toothNode, "span", "fcpc4-coverage", tooth.coverage);
    grid.appendChild(toothNode);
  });
  band.appendChild(grid);
  parent.appendChild(band);
}

function createFactorCalibrationPrecommitEvidenceCardV4({
  document: documentRef,
  envelope,
  expectedPresentationHash = null,
}) {
  if (!documentRef || typeof documentRef.createElement !== "function") {
    throw new TypeError("An explicit detached document is required");
  }
  const model = buildFactorCalibrationPrecommitPresentationModelV4(envelope, {
    expectedPresentationHash,
  });

  const card = documentRef.createElement("section");
  card.className = "fcpc4-card";
  card.setAttribute("data-contract", CARD_SCHEMA);
  card.setAttribute("data-state", model.display_state);
  card.setAttribute("aria-label", "Six-lag finite-horizon residual-order evidence");

  const header = documentRef.createElement("header");
  header.className = "fcpc4-header";
  const heading = documentRef.createElement("div");
  heading.className = "fcpc4-heading";
  addText(documentRef, heading, "p", "fcpc4-eyebrow", model.copy.eyebrow);
  addText(documentRef, heading, "h2", "fcpc4-title", model.copy.title);
  addText(documentRef, heading, "p", "fcpc4-subtitle", model.copy.subtitle);
  header.appendChild(heading);
  const stamp = documentRef.createElement("div");
  stamp.className = "fcpc4-stamp";
  addText(documentRef, stamp, "span", "fcpc4-stamp-index", "LAG / 01-06");
  addText(documentRef, stamp, "strong", "fcpc4-state", model.display_label);
  header.appendChild(stamp);
  card.appendChild(header);

  const railLabel = documentRef.createElement("div");
  railLabel.className = "fcpc4-rail-label";
  addText(documentRef, railLabel, "span", "fcpc4-rail-kicker", "FINITE-HORIZON COMB");
  addText(documentRef, railLabel, "span", "fcpc4-rail-detail", "COVERAGE, NOT PER-LAG RESULT");
  card.appendChild(railLabel);

  const horizon = documentRef.createElement("div");
  horizon.className = "fcpc4-horizon";
  appendBand(
    documentRef,
    horizon,
    "BASELINE",
    "01-03",
    model.phase_comb.teeth.slice(0, 3),
    "fcpc4-band-baseline",
  );
  const seam = documentRef.createElement("div");
  seam.className = "fcpc4-guard-seam";
  addText(documentRef, seam, "span", "fcpc4-guard-copy", "Q GUARD");
  horizon.appendChild(seam);
  appendBand(
    documentRef,
    horizon,
    "OMNIBUS",
    "04-06",
    model.phase_comb.teeth.slice(3),
    "fcpc4-band-omnibus",
  );
  card.appendChild(horizon);

  const aperture = documentRef.createElement("div");
  aperture.className = "fcpc4-aperture";
  addText(documentRef, aperture, "span", "fcpc4-aperture-label", "Q(04-06) AGGREGATE");
  addText(
    documentRef,
    aperture,
    "strong",
    "fcpc4-aperture-value",
    model.phase_comb.observed_maximum,
  );
  addText(
    documentRef,
    aperture,
    "span",
    "fcpc4-ceiling",
    `CEILING ${model.phase_comb.ceiling}`,
  );
  card.appendChild(aperture);

  const axes = documentRef.createElement("div");
  axes.className = "fcpc4-axes";
  model.axes.forEach((axis, index) => {
    const axisNode = documentRef.createElement("div");
    axisNode.className = "fcpc4-axis";
    addText(documentRef, axisNode, "span", "fcpc4-axis-index", String(index + 1).padStart(2, "0"));
    addText(documentRef, axisNode, "span", "fcpc4-axis-label", axis.label);
    addText(documentRef, axisNode, "strong", "fcpc4-axis-state", axis.state);
    axes.appendChild(axisNode);
  });
  card.appendChild(axes);

  const footer = documentRef.createElement("footer");
  footer.className = "fcpc4-footer";
  addText(documentRef, footer, "p", "fcpc4-note", model.copy.note);
  const hash = model.provenance.presentation_hash;
  addText(
    documentRef,
    footer,
    "p",
    "fcpc4-provenance",
    hash ? `ENVELOPE ${hash.slice(0, 12)}` : "ENVELOPE UNVERIFIED",
  );
  card.appendChild(footer);
  return card;
}

module.exports = {
  buildFactorCalibrationPrecommitPresentationModelV4,
  constants: Object.freeze({
    CARD_FINGERPRINT,
    CARD_SCHEMA,
    SOURCE_FINGERPRINT,
    SOURCE_SCHEMA,
    SOURCE_STATUS,
  }),
  contractTestHooks: Object.freeze({
    hasExactKeys,
    verifyEnvelope,
  }),
  createFactorCalibrationPrecommitEvidenceCardV4,
};
