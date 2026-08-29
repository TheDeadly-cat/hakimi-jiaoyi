"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  buildCalendarSessionPresentationModelV1,
  constants,
  createCalendarSessionEvidenceCardV1,
} = require("./calendar_session_evidence_card_v1.js");
const { strictCanonicalHash } = require("./strict_canonical_json_v1.js");

const HASH_FIELDS = [
  "source_session_verification_hash",
  "source_calendar_registration_hash",
  "source_batch_verification_hash",
  "source_schedule_hash",
  "source_observation_batch_hash",
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function stops(state) {
  const states = state === "LOCAL_SESSION_BOUND"
    ? ["BOUND", "BOUND", "PROVIDER_TIME_BOUND", "LOCKED"]
    : state === "EVIDENCE_BLOCK"
      ? ["BLOCKED", "BLOCKED", "UNKNOWN", "LOCKED"]
      : ["UNKNOWN", "UNKNOWN", "UNKNOWN", "LOCKED"];
  return [
    ["CAL", "CANONICAL CALENDAR"],
    ["LBL", "COMMON SESSION LABELS"],
    ["CLS", "SESSION CLOSE"],
    ["ADM", "OBSERVATION ADMISSION"],
  ].map(([code, label], index) => ({ code, label, state: states[index], result_exposed: false }));
}

function baseEnvelope() {
  const hashes = Object.fromEntries(HASH_FIELDS.map((field, index) => [
    field, (index + 1).toString(16).repeat(64),
  ]));
  return {
    schema_version: constants.SOURCE_SCHEMA,
    static_fingerprint: constants.SOURCE_FINGERPRINT,
    presentation_status: constants.SOURCE_STATUS,
    display_state: "LOCAL_SESSION_BOUND",
    display_reason: "LOCAL_CALENDAR_SESSION_BINDING_VERIFIED",
    source_state: "OBSERVED",
    ...hashes,
    source_axis: {
      label: "SOURCE",
      state: "VERIFIED",
      session_verification_state: "CALENDAR_SESSIONS_VERIFIED_BATCH_NOT_ADMITTED",
      verification_hash: hashes.source_session_verification_hash,
      calendar_registration_hash: hashes.source_calendar_registration_hash,
      batch_verification_hash: hashes.source_batch_verification_hash,
    },
    gap_axis: {
      label: "GAP",
      state: "OPEN",
      gap_code: "PROVIDER_IDENTITY_TIME_AND_REPLAY_UNRESOLVED",
      external_timing_unresolved: true,
      provider_identity_unresolved: true,
      replay_registry_unresolved: true,
    },
    maturity_axis: {
      label: "MATURITY",
      state: "LOCAL_SESSION_SEQUENCE_BOUND",
      metric: "COMMON_COMPLETED_SESSION_LABELS",
      row_count: 80,
      completed_common_session_count: 80,
      distinct_calendar_count: 1,
      session_check_count: 80,
      batch_admitted: false,
    },
    permission_axis: {
      label: "PERMISSION",
      state: "LOCKED",
      current_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      profitability_claim_allowed: false,
    },
    timetable: {
      status: "LOCAL_SESSION_BOUND",
      stops: stops("LOCAL_SESSION_BOUND"),
      aggregate_only: true,
      private_session_details_exposed: false,
    },
    blocker_count: 5,
    facts: {
      aggregate_only: true,
      canonical_calendar_ids_bound: true,
      common_session_intersection_verified: true,
      external_calendar_registration_time_verified: false,
      external_provider_identity_verified: false,
      four_axis_separation_preserved: true,
      observation_admission_allowed: false,
      private_session_details_exposed: false,
      provider_time_close_bound: true,
      replay_registry_checked: false,
      source_verifier_replayed: true,
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
    display_reason: "CALENDAR_SESSION_EVIDENCE_BLOCK_VERIFIED",
    source_axis: {
      ...baseline.source_axis,
      state: "VERIFIED_BLOCK",
      session_verification_state: "UNKNOWN",
    },
    maturity_axis: {
      ...baseline.maturity_axis,
      state: "EVIDENCE_BLOCK",
      row_count: null,
      completed_common_session_count: null,
      distinct_calendar_count: null,
      session_check_count: null,
    },
    timetable: { ...baseline.timetable, status: "EVIDENCE_BLOCK", stops: stops("EVIDENCE_BLOCK") },
    blocker_count: 1,
    facts: {
      ...baseline.facts,
      canonical_calendar_ids_bound: false,
      common_session_intersection_verified: false,
      provider_time_close_bound: false,
    },
  });
}

function unknownEnvelope() {
  const baseline = baseEnvelope();
  const nullHashes = Object.fromEntries(HASH_FIELDS.map((field) => [field, null]));
  return seal({
    display_state: "UNKNOWN",
    display_reason: "SOURCE_NOT_EVALUATED",
    source_state: "UNKNOWN",
    ...nullHashes,
    source_axis: {
      label: "SOURCE", state: "UNKNOWN", session_verification_state: "UNKNOWN",
      verification_hash: null, calendar_registration_hash: null, batch_verification_hash: null,
    },
    maturity_axis: {
      ...baseline.maturity_axis, state: "UNKNOWN", row_count: null,
      completed_common_session_count: null, distinct_calendar_count: null, session_check_count: null,
    },
    timetable: { ...baseline.timetable, status: "UNKNOWN", stops: stops("UNKNOWN") },
    blocker_count: 1,
    facts: {
      ...baseline.facts, canonical_calendar_ids_bound: false,
      common_session_intersection_verified: false, provider_time_close_bound: false,
      source_verifier_replayed: false,
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
  appendChild(node) { this.children.push(node); return node; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  set innerHTML(_value) { throw new Error("innerHTML is forbidden"); }
}

const fakeDocument = Object.freeze({ createElement(tagName) { return new FakeNode(tagName); } });
function collectText(node) { return [node.textContent, ...node.children.flatMap(collectText)].join(" "); }
function collectStrings(value, output = []) {
  if (typeof value === "string") output.push(value);
  else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, output));
  else if (value && typeof value === "object") Object.values(value).forEach((item) => collectStrings(item, output));
  return output;
}

let count = 0;
function test(name, body) { body(); count += 1; process.stdout.write(`ok ${count} - ${name}\n`); }

test("exports exact source and card versions", () => {
  assert.equal(constants.SOURCE_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-long-horizon-calendar-session-presentation-envelope-v1");
  assert.equal(constants.SOURCE_FINGERPRINT, "20260922-cross-lag-factor-calibration-long-horizon-calendar-session-presentation-envelope-1");
  assert.equal(constants.CARD_SCHEMA, "calendar-session-timetable-ledger-card-v1");
  assert.equal(constants.CARD_FINGERPRINT, "20260922-calendar-session-timetable-ledger-card-1");
});

test("maps a local session envelope to four neutral axes", () => {
  const model = buildCalendarSessionPresentationModelV1(seal());
  assert.equal(model.integrity.verified, true);
  assert.deepEqual(model.axes.map(({ label, state }) => [label, state]), [
    ["SOURCE", "VERIFIED LOCAL"], ["GAP", "OPEN"],
    ["MATURITY", "LOCAL SESSION SEQUENCE"], ["PERMISSION", "LOCKED"],
  ]);
});

test("preserves the ordered timetable stops", () => {
  const model = buildCalendarSessionPresentationModelV1(seal());
  assert.deepEqual(model.timetable.stops.map(({ code, state }) => [code, state]), [
    ["CAL", "BOUND"], ["LBL", "BOUND"], ["CLS", "PROVIDER_TIME_BOUND"], ["ADM", "LOCKED"],
  ]);
});

test("maps aggregate labels calendars and checks", () => {
  assert.deepEqual(buildCalendarSessionPresentationModelV1(seal()).metrics, {
    labels: "80/80", calendars: "1", checks: "80",
  });
});

test("maps a verified evidence block without aggregate promotion", () => {
  const model = buildCalendarSessionPresentationModelV1(blockEnvelope());
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "EVIDENCE_BLOCK");
  assert.deepEqual(model.metrics, { labels: "UNKNOWN", calendars: "UNKNOWN", checks: "UNKNOWN" });
  assert.equal(model.axes[3].state, "LOCKED");
});

test("keeps a valid unknown envelope distinct", () => {
  const model = buildCalendarSessionPresentationModelV1(unknownEnvelope());
  assert.equal(model.integrity.verified, true);
  assert.equal(model.display_state, "UNKNOWN");
  assert.equal(model.axes[1].state, "OPEN");
});

test("rejects an unsealed payload mutation", () => {
  const envelope = seal();
  envelope.maturity_axis.session_check_count = 160;
  assert.equal(buildCalendarSessionPresentationModelV1(envelope).integrity.reason, "HASH_MISMATCH");
});

test("rejects an expected hash mismatch", () => {
  assert.equal(buildCalendarSessionPresentationModelV1(seal(), {
    expectedPresentationHash: "f".repeat(64),
  }).integrity.reason, "EXPECTED_HASH_MISMATCH");
});

test("rejects resealed schema fingerprint and mount drift", () => {
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ schema_version: "legacy" })).integrity.reason, "UNSUPPORTED_SCHEMA");
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ static_fingerprint: "other" })).integrity.reason, "UNSUPPORTED_FINGERPRINT");
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ presentation_status: "MOUNTED" })).integrity.reason, "MOUNT_STATUS_INVALID");
});

test("rejects sealed extra private fields", () => {
  const model = buildCalendarSessionPresentationModelV1(seal({ session_dates: ["2026-01-01"] }));
  assert.equal(model.integrity.reason, "TOP_LEVEL_CONTRACT_INVALID");
  assert.doesNotMatch(JSON.stringify(model), /session_dates/);
});

test("rejects authority escalation", () => {
  const authority = clone(baseEnvelope().authority);
  authority.paper_authorized = true;
  const model = buildCalendarSessionPresentationModelV1(seal({ authority }));
  assert.equal(model.integrity.reason, "AUTHORITY_INVALID");
  assert.equal(model.authority.live_order_allowed, false);
});

test("rejects permission escalation", () => {
  const permission_axis = { ...baseEnvelope().permission_axis, current_admission_allowed: true };
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ permission_axis })).integrity.reason, "PERMISSION_LOCK_INVALID");
});

test("rejects gap closure", () => {
  const gap_axis = { ...baseEnvelope().gap_axis, replay_registry_unresolved: false };
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ gap_axis })).integrity.reason, "GAP_LOCK_INVALID");
});

test("rejects source hash cross-binding drift", () => {
  const source_axis = { ...baseEnvelope().source_axis, verification_hash: "0".repeat(64) };
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ source_axis })).integrity.reason, "SOURCE_HASH_CROSS_BIND_INVALID");
});

test("rejects maturity count arithmetic drift", () => {
  const maturity_axis = { ...baseEnvelope().maturity_axis, session_check_count: 79 };
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ maturity_axis })).integrity.reason, "MATURITY_COUNT_INVALID");
});

test("rejects reordered and promoted timetable stops", () => {
  const baseline = baseEnvelope().timetable;
  for (const candidate of [
    [baseline.stops[1], baseline.stops[0], ...baseline.stops.slice(2)],
    baseline.stops.map((stop, index) => index === 3 ? { ...stop, state: "BOUND" } : stop),
  ]) {
    assert.equal(buildCalendarSessionPresentationModelV1(seal({
      timetable: { ...baseline, stops: candidate },
    })).integrity.reason, "TIMETABLE_INVALID");
  }
});

test("rejects external fact promotion", () => {
  const facts = { ...baseEnvelope().facts, replay_registry_checked: true };
  assert.equal(buildCalendarSessionPresentationModelV1(seal({ facts })).integrity.reason, "FACTS_INVALID");
});

test("renders timetable metrics and axes through textContent", () => {
  const card = createCalendarSessionEvidenceCardV1({ document: fakeDocument, envelope: seal() });
  const text = collectText(card);
  assert.match(text, /Session timetable ledger/);
  for (const label of ["CANONICAL CALENDAR", "COMMON SESSION LABELS", "SESSION CLOSE", "OBSERVATION ADMISSION"]) assert.match(text, new RegExp(label));
  assert.match(text, /80\/80/);
  assert.equal(card.attributes["data-state"], "LOCAL_SESSION_BOUND");
  const hostile = createCalendarSessionEvidenceCardV1({ document: fakeDocument, envelope: seal({ display_reason: "<img onerror=alert(1)>" }) });
  assert.doesNotMatch(collectText(hostile), /<img|onerror/);
});

test("requires an explicit detached document", () => {
  assert.throws(() => createCalendarSessionEvidenceCardV1({ envelope: seal() }), /explicit detached document/);
});

test("keeps all public copy neutral", () => {
  const local = collectStrings(buildCalendarSessionPresentationModelV1(seal())).join(" ");
  const unknown = collectStrings(buildCalendarSessionPresentationModelV1(null)).join(" ");
  assert.doesNotMatch(`${local} ${unknown}`, /\bready\b|\bprofit(?:able|ability)?\b|盈利|收益证明/i);
  for (const label of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) assert.match(local, new RegExp(label));
});

test("is deterministic", () => {
  const envelope = seal();
  assert.deepEqual(buildCalendarSessionPresentationModelV1(envelope), buildCalendarSessionPresentationModelV1(clone(envelope)));
});

test("ships scoped timetable responsive and reduced-motion styles", () => {
  const css = fs.readFileSync(path.join(__dirname, "calendar_session_evidence_card_v1.css"), "utf8");
  for (const selector of [".csrl1-card", ".csrl1-route", ".csrl1-route-line", ".csrl1-stop", ".csrl1-ticket", ".csrl1-axes"]) assert.match(css, new RegExp(selector.replace(".", "\\.")));
  assert.match(css, /@media \(max-width: 900px\)/);
  assert.match(css, /@media \(max-width: 540px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(css, /\.ready|\.profit|#00ff00|purple/i);
});

test("contains no implicit activation or unsafe HTML hook", () => {
  const source = fs.readFileSync(path.join(__dirname, "calendar_session_evidence_card_v1.js"), "utf8");
  assert.doesNotMatch(source, /require\(["']\.\/app|DOMContentLoaded|document\.querySelector|window\./);
  assert.doesNotMatch(source, /\.innerHTML\s*=/);
});

assert.equal(count, 23);
process.stdout.write("calendar session timetable ledger card v1: 23/23 PASS\n");
