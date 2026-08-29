"use strict";

const {
  isPlainRecord,
  strictCanonicalHash,
} = require("./strict_canonical_json_v1.js");

const SOURCE_SCHEMA =
  "strategy-correlation-cross-lag-factor-calibration-long-horizon-calendar-session-presentation-envelope-v1";
const SOURCE_FINGERPRINT =
  "20260922-cross-lag-factor-calibration-long-horizon-calendar-session-presentation-envelope-1";
const SOURCE_STATUS = "UNMOUNTED_CANDIDATE";
const CARD_SCHEMA = "calendar-session-timetable-ledger-card-v1";
const CARD_FINGERPRINT = "20260922-calendar-session-timetable-ledger-card-1";

const DISPLAY_STATES = new Set(["LOCAL_SESSION_BOUND", "EVIDENCE_BLOCK", "UNKNOWN"]);
const STATE_LABELS = Object.freeze({
  LOCAL_SESSION_BOUND: "LOCAL SESSION BOUND",
  EVIDENCE_BLOCK: "EVIDENCE BLOCK",
  UNKNOWN: "UNKNOWN",
});
const SOURCE_HASH_FIELDS = Object.freeze([
  "source_session_verification_hash",
  "source_calendar_registration_hash",
  "source_batch_verification_hash",
  "source_schedule_hash",
  "source_observation_batch_hash",
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
  "timetable",
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
const STOP_DEFINITIONS = Object.freeze([
  Object.freeze({ code: "CAL", label: "CANONICAL CALENDAR" }),
  Object.freeze({ code: "LBL", label: "COMMON SESSION LABELS" }),
  Object.freeze({ code: "CLS", label: "SESSION CLOSE" }),
  Object.freeze({ code: "ADM", label: "OBSERVATION ADMISSION" }),
]);

function hasOwn(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function hasExactKeys(value, expected) {
  if (!isPlainRecord(value)) return false;
  const keys = Object.keys(value);
  return keys.length === expected.length && expected.every((key) => hasOwn(value, key));
}

function normalizedHash(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/i.test(value)
    ? value.toLowerCase()
    : null;
}

function nonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function invalid(reason) {
  return Object.freeze({ ok: false, reason });
}

function expectedStopStates(displayState) {
  if (displayState === "LOCAL_SESSION_BOUND") {
    return ["BOUND", "BOUND", "PROVIDER_TIME_BOUND", "LOCKED"];
  }
  if (displayState === "EVIDENCE_BLOCK") {
    return ["BLOCKED", "BLOCKED", "UNKNOWN", "LOCKED"];
  }
  return ["UNKNOWN", "UNKNOWN", "UNKNOWN", "LOCKED"];
}

function validStops(stops, displayState) {
  if (!Array.isArray(stops) || stops.length !== STOP_DEFINITIONS.length) return false;
  const states = expectedStopStates(displayState);
  return stops.every((stop, index) => hasExactKeys(stop, [
    "code", "label", "state", "result_exposed",
  ]) && stop.code === STOP_DEFINITIONS[index].code &&
    stop.label === STOP_DEFINITIONS[index].label &&
    stop.state === states[index] &&
    stop.result_exposed === false);
}

function verifyEnvelope(envelope, expectedPresentationHash) {
  if (!isPlainRecord(envelope)) return invalid("MISSING_OR_INVALID_ENVELOPE");
  if (envelope.schema_version !== SOURCE_SCHEMA) return invalid("UNSUPPORTED_SCHEMA");
  if (envelope.static_fingerprint !== SOURCE_FINGERPRINT) return invalid("UNSUPPORTED_FINGERPRINT");
  if (envelope.presentation_status !== SOURCE_STATUS) return invalid("MOUNT_STATUS_INVALID");
  if (!hasExactKeys(envelope, TOP_LEVEL_KEYS)) return invalid("TOP_LEVEL_CONTRACT_INVALID");

  const actualHash = normalizedHash(envelope.presentation_hash);
  const expectedHash = expectedPresentationHash == null
    ? null
    : normalizedHash(expectedPresentationHash);
  if (!actualHash || (expectedPresentationHash != null && !expectedHash)) return invalid("HASH_INVALID");
  if (expectedHash && expectedHash !== actualHash) return invalid("EXPECTED_HASH_MISMATCH");
  const unsigned = {};
  for (const key of Object.keys(envelope)) {
    if (key !== "presentation_hash") unsigned[key] = envelope[key];
  }
  try {
    if (normalizedHash(strictCanonicalHash(unsigned)) !== actualHash) return invalid("HASH_MISMATCH");
  } catch (_error) {
    return invalid("HASH_PAYLOAD_INVALID");
  }

  if (!DISPLAY_STATES.has(envelope.display_state)) return invalid("DISPLAY_STATE_INVALID");
  if (typeof envelope.display_reason !== "string" || envelope.display_reason.length === 0 ||
      typeof envelope.source_state !== "string" || envelope.source_state.length === 0 ||
      !nonNegativeInteger(envelope.blocker_count)) return invalid("SUMMARY_CONTRACT_INVALID");

  const sourceAxis = envelope.source_axis;
  const gapAxis = envelope.gap_axis;
  const maturityAxis = envelope.maturity_axis;
  const permissionAxis = envelope.permission_axis;
  const timetable = envelope.timetable;
  const facts = envelope.facts;
  const authority = envelope.authority;
  if (!hasExactKeys(sourceAxis, [
    "label", "state", "session_verification_state", "verification_hash",
    "calendar_registration_hash", "batch_verification_hash",
  ])) return invalid("SOURCE_AXIS_INVALID");
  if (!hasExactKeys(gapAxis, [
    "label", "state", "gap_code", "external_timing_unresolved",
    "provider_identity_unresolved", "replay_registry_unresolved",
  ])) return invalid("GAP_AXIS_INVALID");
  if (!hasExactKeys(maturityAxis, [
    "label", "state", "metric", "row_count", "completed_common_session_count",
    "distinct_calendar_count", "session_check_count", "batch_admitted",
  ])) return invalid("MATURITY_AXIS_INVALID");
  if (!hasExactKeys(permissionAxis, [
    "label", "state", "current_admission_allowed", "live_order_allowed",
    "paper_authorized", "profitability_claim_allowed",
  ])) return invalid("PERMISSION_AXIS_INVALID");
  if (!hasExactKeys(timetable, [
    "status", "stops", "aggregate_only", "private_session_details_exposed",
  ])) return invalid("TIMETABLE_INVALID");
  if (!hasExactKeys(authority, ["descriptive_only", ...REQUIRED_DENIALS])) return invalid("AUTHORITY_INVALID");
  if (!hasExactKeys(facts, [
    "aggregate_only", "canonical_calendar_ids_bound",
    "common_session_intersection_verified", "external_calendar_registration_time_verified",
    "external_provider_identity_verified", "four_axis_separation_preserved",
    "observation_admission_allowed", "private_session_details_exposed",
    "provider_time_close_bound", "replay_registry_checked", "source_verifier_replayed",
  ])) return invalid("FACTS_INVALID");

  const observed = envelope.display_state !== "UNKNOWN";
  const locallyBound = envelope.display_state === "LOCAL_SESSION_BOUND";
  const expectedSourceAxisState = locallyBound ? "VERIFIED" : observed ? "VERIFIED_BLOCK" : "UNKNOWN";
  const expectedSessionState = locallyBound
    ? "CALENDAR_SESSIONS_VERIFIED_BATCH_NOT_ADMITTED"
    : "UNKNOWN";
  if (sourceAxis.label !== "SOURCE" || sourceAxis.state !== expectedSourceAxisState ||
      sourceAxis.session_verification_state !== expectedSessionState) return invalid("SOURCE_STATE_INCONSISTENT");

  const sourceHashes = {};
  for (const field of SOURCE_HASH_FIELDS) {
    const value = envelope[field];
    const hash = value == null ? null : normalizedHash(value);
    if ((value != null && !hash) || (observed && !hash) || (!observed && value != null)) {
      return invalid("SOURCE_HASH_INVALID");
    }
    sourceHashes[field] = hash;
  }
  const axisBindings = {
    source_session_verification_hash: sourceAxis.verification_hash,
    source_calendar_registration_hash: sourceAxis.calendar_registration_hash,
    source_batch_verification_hash: sourceAxis.batch_verification_hash,
  };
  for (const [field, value] of Object.entries(axisBindings)) {
    const hash = value == null ? null : normalizedHash(value);
    if (hash !== sourceHashes[field]) return invalid("SOURCE_HASH_CROSS_BIND_INVALID");
  }

  if (gapAxis.label !== "GAP" || gapAxis.state !== "OPEN" ||
      gapAxis.gap_code !== "PROVIDER_IDENTITY_TIME_AND_REPLAY_UNRESOLVED" ||
      gapAxis.external_timing_unresolved !== true ||
      gapAxis.provider_identity_unresolved !== true ||
      gapAxis.replay_registry_unresolved !== true) return invalid("GAP_LOCK_INVALID");
  if (permissionAxis.label !== "PERMISSION" || permissionAxis.state !== "LOCKED" ||
      permissionAxis.current_admission_allowed !== false ||
      permissionAxis.live_order_allowed !== false ||
      permissionAxis.paper_authorized !== false ||
      permissionAxis.profitability_claim_allowed !== false) return invalid("PERMISSION_LOCK_INVALID");
  if (authority.descriptive_only !== true ||
      !REQUIRED_DENIALS.every((key) => authority[key] === false)) return invalid("AUTHORITY_INVALID");

  const expectedMaturityState = locallyBound
    ? "LOCAL_SESSION_SEQUENCE_BOUND"
    : observed ? "EVIDENCE_BLOCK" : "UNKNOWN";
  if (maturityAxis.label !== "MATURITY" || maturityAxis.state !== expectedMaturityState ||
      maturityAxis.metric !== "COMMON_COMPLETED_SESSION_LABELS" ||
      maturityAxis.batch_admitted !== false) return invalid("MATURITY_CONTRACT_INVALID");
  if (locallyBound) {
    const { row_count: rows, completed_common_session_count: completed,
      distinct_calendar_count: calendars, session_check_count: checks } = maturityAxis;
    if (!nonNegativeInteger(rows) || rows === 0 || completed !== rows ||
        !nonNegativeInteger(calendars) || calendars === 0 ||
        !nonNegativeInteger(checks) || checks !== rows * calendars ||
        !Number.isSafeInteger(rows * calendars)) return invalid("MATURITY_COUNT_INVALID");
  } else if ([
    maturityAxis.row_count, maturityAxis.completed_common_session_count,
    maturityAxis.distinct_calendar_count, maturityAxis.session_check_count,
  ].some((value) => value !== null)) return invalid("NONLOCAL_AGGREGATE_INVALID");

  if (timetable.status !== envelope.display_state || timetable.aggregate_only !== true ||
      timetable.private_session_details_exposed !== false ||
      !validStops(timetable.stops, envelope.display_state)) return invalid("TIMETABLE_INVALID");
  if (facts.aggregate_only !== true || facts.four_axis_separation_preserved !== true ||
      facts.source_verifier_replayed !== observed ||
      facts.canonical_calendar_ids_bound !== locallyBound ||
      facts.common_session_intersection_verified !== locallyBound ||
      facts.provider_time_close_bound !== locallyBound ||
      facts.external_calendar_registration_time_verified !== false ||
      facts.external_provider_identity_verified !== false ||
      facts.replay_registry_checked !== false ||
      facts.observation_admission_allowed !== false ||
      facts.private_session_details_exposed !== false) return invalid("FACTS_INVALID");

  return Object.freeze({ ok: true, reason: "VERIFIED", hash: actualHash, sourceHashes });
}

function unknownStops() {
  const states = expectedStopStates("UNKNOWN");
  return Object.freeze(STOP_DEFINITIONS.map((definition, index) => Object.freeze({
    ...definition,
    state: states[index],
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
    timetable: Object.freeze({ stops: unknownStops(), private_session_details_exposed: false }),
    metrics: Object.freeze({ labels: "UNKNOWN", calendars: "UNKNOWN", checks: "UNKNOWN" }),
    provenance: Object.freeze({ presentation_hash: null, session_verification_hash: null }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 05",
      title: "Session timetable ledger",
      subtitle: "CANONICAL CALENDAR / COMMON SESSION / PROVIDER-TIME CLOSE",
      note: "No verified envelope is available. Provider identity, external time, replay, and admission remain unresolved.",
    }),
  });
}

function buildCalendarSessionPresentationModelV1(
  envelope,
  { expectedPresentationHash = null } = {},
) {
  const verification = verifyEnvelope(envelope, expectedPresentationHash);
  if (!verification.ok) return unknownModel(verification.reason);
  const local = envelope.display_state === "LOCAL_SESSION_BOUND";
  const block = envelope.display_state === "EVIDENCE_BLOCK";
  const maturity = envelope.maturity_axis;
  const note = local
    ? "Calendar IDs, common labels, and session closes are locally bound. Provider identity, external time, replay, and observation admission remain unresolved."
    : block
      ? "The sealed source records a calendar/session evidence block. No aggregate is promoted and permission remains locked."
      : "The sealed source is explicitly unknown. No calendar/session aggregate is promoted and permission remains locked.";
  return Object.freeze({
    schema_version: CARD_SCHEMA,
    static_fingerprint: CARD_FINGERPRINT,
    presentation_status: SOURCE_STATUS,
    display_state: envelope.display_state,
    display_label: STATE_LABELS[envelope.display_state],
    integrity: Object.freeze({ verified: true, reason: verification.reason }),
    axes: Object.freeze([
      Object.freeze({ label: "SOURCE", state: local ? "VERIFIED LOCAL" : block ? "VERIFIED BLOCK" : "UNKNOWN" }),
      Object.freeze({ label: "GAP", state: "OPEN" }),
      Object.freeze({ label: "MATURITY", state: local ? "LOCAL SESSION SEQUENCE" : block ? "EVIDENCE BLOCK" : "UNKNOWN" }),
      Object.freeze({ label: "PERMISSION", state: "LOCKED" }),
    ]),
    timetable: Object.freeze({
      stops: Object.freeze(envelope.timetable.stops.map((stop) => Object.freeze({ ...stop }))),
      private_session_details_exposed: false,
    }),
    metrics: Object.freeze({
      labels: local ? `${maturity.completed_common_session_count}/${maturity.row_count}` : "UNKNOWN",
      calendars: local ? String(maturity.distinct_calendar_count) : "UNKNOWN",
      checks: local ? String(maturity.session_check_count) : "UNKNOWN",
    }),
    provenance: Object.freeze({
      presentation_hash: verification.hash,
      session_verification_hash: verification.sourceHashes.source_session_verification_hash,
    }),
    authority: Object.freeze({
      presentation_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    }),
    copy: Object.freeze({
      eyebrow: "DETACHED RESEARCH INSTRUMENT / 05",
      title: "Session timetable ledger",
      subtitle: "CANONICAL CALENDAR / COMMON SESSION / PROVIDER-TIME CLOSE",
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

function createCalendarSessionEvidenceCardV1({
  document: documentRef,
  envelope,
  expectedPresentationHash = null,
}) {
  if (!documentRef || typeof documentRef.createElement !== "function") {
    throw new TypeError("An explicit detached document is required");
  }
  const model = buildCalendarSessionPresentationModelV1(envelope, {
    expectedPresentationHash,
  });
  const card = documentRef.createElement("section");
  card.className = "csrl1-card";
  card.setAttribute("data-contract", CARD_SCHEMA);
  card.setAttribute("data-state", model.display_state);
  card.setAttribute("aria-label", "Calendar session timetable evidence");

  const header = documentRef.createElement("header");
  header.className = "csrl1-header";
  const heading = documentRef.createElement("div");
  heading.className = "csrl1-heading";
  addText(documentRef, heading, "p", "csrl1-eyebrow", model.copy.eyebrow);
  addText(documentRef, heading, "h2", "csrl1-title", model.copy.title);
  addText(documentRef, heading, "p", "csrl1-subtitle", model.copy.subtitle);
  header.appendChild(heading);
  const stamp = documentRef.createElement("div");
  stamp.className = "csrl1-stamp";
  addText(documentRef, stamp, "span", "csrl1-stamp-index", "CAL / SESSION / 01");
  addText(documentRef, stamp, "strong", "csrl1-state", model.display_label);
  header.appendChild(stamp);
  card.appendChild(header);

  const route = documentRef.createElement("div");
  route.className = "csrl1-route";
  const routeLine = documentRef.createElement("div");
  routeLine.className = "csrl1-route-line";
  route.appendChild(routeLine);
  model.timetable.stops.forEach((stop, index) => {
    const node = documentRef.createElement("section");
    node.className = `csrl1-stop csrl1-stop-${stop.code.toLowerCase()}`;
    node.setAttribute("data-stop-state", stop.state);
    addText(documentRef, node, "span", "csrl1-stop-index", String(index + 1).padStart(2, "0"));
    addText(documentRef, node, "span", "csrl1-stop-code", stop.code);
    addText(documentRef, node, "strong", "csrl1-stop-label", stop.label);
    addText(documentRef, node, "span", "csrl1-stop-state", stop.state);
    route.appendChild(node);
  });
  card.appendChild(route);

  const metrics = documentRef.createElement("div");
  metrics.className = "csrl1-metrics";
  [
    ["LABELS", model.metrics.labels],
    ["CALENDARS", model.metrics.calendars],
    ["CHECKS", model.metrics.checks],
  ].forEach(([label, value]) => {
    const ticket = documentRef.createElement("div");
    ticket.className = "csrl1-ticket";
    addText(documentRef, ticket, "span", "csrl1-ticket-label", label);
    addText(documentRef, ticket, "strong", "csrl1-ticket-value", value);
    metrics.appendChild(ticket);
  });
  card.appendChild(metrics);

  const axes = documentRef.createElement("div");
  axes.className = "csrl1-axes";
  model.axes.forEach((axis, index) => {
    const axisNode = documentRef.createElement("div");
    axisNode.className = "csrl1-axis";
    addText(documentRef, axisNode, "span", "csrl1-axis-index", String(index + 1).padStart(2, "0"));
    addText(documentRef, axisNode, "span", "csrl1-axis-label", axis.label);
    addText(documentRef, axisNode, "strong", "csrl1-axis-state", axis.state);
    axes.appendChild(axisNode);
  });
  card.appendChild(axes);

  const footer = documentRef.createElement("footer");
  footer.className = "csrl1-footer";
  addText(documentRef, footer, "p", "csrl1-note", model.copy.note);
  const hash = model.provenance.presentation_hash;
  addText(documentRef, footer, "p", "csrl1-provenance", hash ? `ENVELOPE ${hash.slice(0, 12)}` : "ENVELOPE UNVERIFIED");
  card.appendChild(footer);
  return card;
}

module.exports = {
  buildCalendarSessionPresentationModelV1,
  constants: Object.freeze({
    CARD_FINGERPRINT,
    CARD_SCHEMA,
    SOURCE_FINGERPRINT,
    SOURCE_SCHEMA,
    SOURCE_STATUS,
  }),
  contractTestHooks: Object.freeze({ hasExactKeys, verifyEnvelope }),
  createCalendarSessionEvidenceCardV1,
};
