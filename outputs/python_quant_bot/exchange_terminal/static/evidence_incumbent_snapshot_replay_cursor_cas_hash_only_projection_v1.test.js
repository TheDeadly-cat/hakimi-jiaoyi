"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const presenter = require("./evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.js");

const authority = Object.freeze({
  permission_state: "RESEARCH_ONLY",
  permission: false,
  paper_authorized: false,
  live_authorized: false,
  input_cursor_mutation_performed: false,
  atomic_storage_commit_verified: false,
  durable_commit_verified: false,
  linearizable_read_verified: false,
  provider_identity_verified: false,
  current_chain_activated: false,
});
const redaction = Object.freeze({
  raw_stream_id_redacted: true,
  raw_request_nonce_redacted: true,
  raw_cursor_documents_redacted: true,
  raw_consumed_attestation_hashes_redacted: true,
  raw_high_water_attestation_hash_redacted: true,
  raw_intent_document_redacted: true,
  raw_receipt_document_redacted: true,
  raw_incumbent_snapshot_redacted: true,
  raw_proposals_and_holdings_redacted: true,
  raw_signatures_and_keys_redacted: true,
});

function observation(outcome) {
  if (outcome === presenter.OUTCOME_ADVANCED_IN_RETURNED_CURSOR) {
    return { outcome, gate_status: "UNKNOWN", candidate_sequence: 10, observed_high_water_sequence: 9, returned_high_water_sequence: 10, returned_cursor_changed: true };
  }
  if (outcome === presenter.OUTCOME_COMPARE_AND_SWAP_CONFLICT) {
    return { outcome, gate_status: "UNKNOWN", candidate_sequence: 10, observed_high_water_sequence: 9, returned_high_water_sequence: 9, returned_cursor_changed: false };
  }
  if (outcome === presenter.OUTCOME_ALREADY_CONSUMED) {
    return { outcome, gate_status: "BLOCK", candidate_sequence: 10, observed_high_water_sequence: 10, returned_high_water_sequence: 10, returned_cursor_changed: false };
  }
  return { outcome, gate_status: "BLOCK", candidate_sequence: 9, observed_high_water_sequence: 10, returned_high_water_sequence: 10, returned_cursor_changed: false };
}

function envelope(outcome = presenter.OUTCOME_ADVANCED_IN_RETURNED_CURSOR) {
  const projectionHash = "f".repeat(64);
  return {
    schema_version: presenter.HANDOFF_SCHEMA_VERSION,
    verification_status: presenter.VERIFICATION_STATUS,
    expected_readonly_projection_hash: projectionHash,
    projection: {
      projection_schema_version: presenter.PROJECTION_SCHEMA_VERSION,
      static_fingerprint: "20260824-incumbent-snapshot-replay-cursor-cas-hash-only-unmounted-permission-lock-1",
      consumer_status: "UNMOUNTED_READONLY_REPLAY_CURSOR_CAS_CANDIDATE",
      source_lineage: {
        cas_contract_version: "incumbent-snapshot-replay-cursor-cas-transition-v1",
        intent_hash: "a".repeat(64),
        freshness_result_fingerprint_sha256: "b".repeat(64),
        candidate_attestation_hash: "c".repeat(64),
        projection_preregistration_hash: "d".repeat(64),
        stream_id_sha256: "e".repeat(64),
        base_cursor_hash: "1".repeat(64),
        observed_cursor_hash: "2".repeat(64),
        returned_cursor_hash: "3".repeat(64),
        transition_receipt_hash: "4".repeat(64),
      },
      observation: observation(outcome),
      authority: { ...authority },
      redaction: { ...redaction },
      readonly_projection_hash: projectionHash,
    },
  };
}

test("governance order and API are frozen", () => {
  assert.deepEqual(presenter.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(Object.isFrozen(presenter), true);
});

test("synthetic advance is an UNKNOWN observation, never a commit", () => {
  const input = envelope();
  const model = presenter.deriveReplayCursorCasViewModelV1(input);
  const markup = presenter.renderReplayCursorCasHashOnlyProjectionV1(input);
  assert.equal(model.verificationAccepted, true);
  assert.equal(model.rawGateStatus, "UNKNOWN");
  assert.equal(model.statusLabel, "合成游标观察");
  assert.deepEqual(model.sequences.map((item) => item.value), ["10", "9", "10", "+1"]);
  assert.match(markup, /原子存储提交尚未核验/);
  assert.doesNotMatch(markup, /\bREADY\b/i);
});

test("CAS conflict remains visibly unresolved", () => {
  const model = presenter.deriveReplayCursorCasViewModelV1(envelope(presenter.OUTCOME_COMPARE_AND_SWAP_CONFLICT));
  assert.equal(model.verificationAccepted, true);
  assert.equal(model.statusLabel, "并发竞争未闭合");
  assert.equal(model.tone, "conflict");
  assert.deepEqual(model.sequences.map((item) => item.value), ["10", "9", "9", "+1"]);
});

test("duplicate and nonmonotonic outcomes remain blocked", () => {
  const cases = [
    [presenter.OUTCOME_ALREADY_CONSUMED, "回放阻断"],
    [presenter.OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER, "序列阻断"],
  ];
  for (const [outcome, label] of cases) {
    const model = presenter.deriveReplayCursorCasViewModelV1(envelope(outcome));
    assert.equal(model.rawGateStatus, "BLOCK");
    assert.equal(model.statusLabel, label);
    assert.equal(model.tone, "blocked");
  }
});

test("hash mismatch fails closed without reflecting attacker input", () => {
  const input = envelope();
  input.expected_readonly_projection_hash = "0".repeat(64);
  input.projection.consumer_status = "<img src=x onerror=alert(1)>";
  const markup = presenter.renderReplayCursorCasHashOnlyProjectionV1(input);
  assert.doesNotMatch(markup, /onerror|<img/i);
  assert.match(markup, /展示输入未完成精确验证交接/);
});

test("authority promotion and raw alias injection fail closed", () => {
  const promoted = envelope();
  promoted.projection.authority.atomic_storage_commit_verified = true;
  const injected = envelope();
  injected.projection.raw_cursor = { consumed: ["secret"] };
  assert.equal(presenter.deriveReplayCursorCasViewModelV1(promoted).verificationAccepted, false);
  assert.equal(presenter.deriveReplayCursorCasViewModelV1(injected).verificationAccepted, false);
});

test("impossible outcome and sequence combinations fail closed", () => {
  const invalid = envelope(presenter.OUTCOME_ADVANCED_IN_RETURNED_CURSOR);
  invalid.projection.observation.returned_cursor_changed = false;
  const unsafe = envelope();
  unsafe.projection.observation.candidate_sequence = Number.MAX_SAFE_INTEGER + 1;
  assert.equal(presenter.deriveReplayCursorCasViewModelV1(invalid).verificationAccepted, false);
  assert.equal(presenter.deriveReplayCursorCasViewModelV1(unsafe).verificationAccepted, false);
});

test("rendered stages retain SOURCE GAP MATURITY PERMISSION order", () => {
  const markup = presenter.renderReplayCursorCasHashOnlyProjectionV1(envelope());
  const positions = presenter.STAGE_ORDER.map((stage) => markup.indexOf(`>${stage}<`));
  assert.equal(positions.every((position) => position >= 0), true);
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
});

test("view model is deeply immutable", () => {
  const model = presenter.deriveReplayCursorCasViewModelV1(envelope());
  assert.equal(Object.isFrozen(model), true);
  assert.equal(Object.isFrozen(model.sequences[0]), true);
  assert.throws(() => { model.sequences[0].value = "forged"; }, TypeError);
});

test("production presenter has no DOM network storage or runtime APIs", () => {
  const source = fs.readFileSync(path.join(__dirname, "evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.js"), "utf8");
  for (const forbidden of ["document.", "window.", "fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage", "indexedDB", "registerRoute", "currentPointer"]) assert.equal(source.includes(forbidden), false, forbidden);
});

test("isolated CSS encodes switchboard responsive and motion guards", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.css"), "utf8");
  assert.match(css, /--rcp-ink:\s*#16242a/);
  assert.match(css, /cursor-cas-plate-v1__switchboard/);
  assert.match(css, /cursor-cas-plate-v1__rail/);
  assert.match(css, /summary:focus-visible/);
  assert.match(css, /max-width:\s*780px/);
  assert.match(css, /max-width:\s*480px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test("presenter remains deliberately absent from current index", () => {
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.equal(index.includes("evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.js"), false);
  assert.equal(index.includes("evidence_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1.css"), false);
});
