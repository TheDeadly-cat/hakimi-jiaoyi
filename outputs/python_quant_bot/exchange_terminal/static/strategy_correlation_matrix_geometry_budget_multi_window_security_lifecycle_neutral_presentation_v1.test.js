"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const subject = require(
  "./strategy_correlation_matrix_geometry_budget_multi_window_security_lifecycle_neutral_presentation_v1.js"
);

function fixture() {
  return {
    security_gate_evaluation: {
      schema_version: "security-receipt-semantic-gate-candidate-v1",
      gate_contract_hash: subject.SECURITY_GATE_CONTRACT_HASH,
      preregistration_hash: subject.SECURITY_GATE_PREREGISTRATION_HASH,
      status: "UNKNOWN",
      authorization_state: "UNAUTHORIZED",
      reason_code: "SECURITY_SEMANTICS_UNAVAILABLE",
      private_receipt: "gate-secret-must-not-be-rendered",
      authority: {
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
        writer_allowed: false,
      },
    },
    lifecycle_owner_creation: {
      schema_version: "request-lifecycle-owner-creation-candidate-v1",
      lifecycle_owner_contract_hash: subject.LIFECYCLE_OWNER_CONTRACT_HASH,
      static_fingerprint: subject.LIFECYCLE_OWNER_STATIC_FINGERPRINT,
      state: "SYNTHETIC_UNREGISTERED",
      private_receipt: "creation-secret-must-not-be-rendered",
    },
    lifecycle_claim_result: {
      schema_version: "request-lifecycle-owner-claim-result-v1",
      status: "REJECTED",
      reason_code: subject.CLAIM_REJECTION_REASON,
      private_receipt: "claim-secret-must-not-be-rendered",
      authority: {
        provider_invocation_allowed: false,
        request_handler_invocation_allowed: false,
      },
    },
  };
}

function build(input = fixture()) {
  return subject.buildSecurityLifecycleNeutralPresentationV1(input);
}

test("exact synthetic rejection projects the fixed neutral four-axis model", () => {
  const presentation = build();
  assert.equal(presentation.status, "BLOCKED");
  assert.equal(presentation.presentation_state, "LOCAL_SECURITY_REJECTION_ONLY");
  assert.equal(presentation.tone, "NEUTRAL");
  assert.deepEqual(
    presentation.stage_order,
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
  assert.deepEqual(
    presentation.stages.map((stage) => stage.state),
    ["HASH_BOUND", "OPEN", "SYNTHETIC_UNREGISTERED", "UNAUTHORIZED"]
  );
});

test("projection retains only hashes and never embeds source receipts", () => {
  const presentation = build();
  const serialized = JSON.stringify(presentation);
  assert.equal(serialized.includes("gate-secret-must-not-be-rendered"), false);
  assert.equal(serialized.includes("creation-secret-must-not-be-rendered"), false);
  assert.equal(serialized.includes("claim-secret-must-not-be-rendered"), false);
  assert.match(presentation.source.security_gate_document_sha256, /^[0-9a-f]{64}$/);
  assert.match(presentation.source.lifecycle_owner_creation_sha256, /^[0-9a-f]{64}$/);
  assert.match(presentation.source.lifecycle_claim_result_sha256, /^[0-9a-f]{64}$/);
  assert.match(presentation.source.document_set_sha256, /^[0-9a-f]{64}$/);
  assert.equal(presentation.facts.raw_source_documents_embedded, false);
  assert.equal(presentation.facts.raw_security_receipts_embedded, false);
});

test("permission remains locked on every known projection", () => {
  const presentation = build();
  assert.deepEqual(presentation.authority, {
    current_admission_allowed: false,
    dom_mount_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    provider_invocation_allowed: false,
    request_handler_invocation_allowed: false,
    runtime_asset_loading_allowed: false,
    writer_allowed: false,
  });
  assert.equal(presentation.facts.dom_mounted, false);
  assert.equal(presentation.facts.current_activated, false);
});

test("missing pinned contract marker fails closed without losing local hashes", () => {
  const input = fixture();
  input.security_gate_evaluation.gate_contract_hash = "f".repeat(64);
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(
    presentation.reason_code,
    "PINNED_SOURCE_CONTRACT_MARKERS_NOT_EXACT"
  );
  assert.equal(presentation.source.security_gate_contract_hash, null);
  assert.match(presentation.source.document_set_sha256, /^[0-9a-f]{64}$/);
});

test("missing rejection marker fails closed", () => {
  const input = fixture();
  input.lifecycle_claim_result.reason_code = "CLAIM_RESULT_UNAVAILABLE";
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(
    presentation.reason_code,
    "SECURITY_REJECTION_MARKERS_NOT_EXACT"
  );
  assert.equal(presentation.stages[2].state, "UNKNOWN");
});

test("authority promotion in any source document fails closed", () => {
  const input = fixture();
  input.lifecycle_claim_result.authority.provider_invocation_allowed = true;
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(
    presentation.reason_code,
    "SOURCE_DOCUMENT_SET_CONTAINS_AUTHORITY_PROMOTION"
  );
  assert.equal(presentation.authority.provider_invocation_allowed, false);
});

test("promotional scalar substitution fails closed", () => {
  const input = fixture();
  input.lifecycle_owner_creation.extra_state = "CLAIM_ACCEPTED";
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(
    presentation.reason_code,
    "SOURCE_DOCUMENT_SET_CONTAINS_AUTHORITY_PROMOTION"
  );
});

test("extra top-level document and missing document both fail closed", () => {
  const extra = fixture();
  extra.unregistered_source = {};
  assert.equal(build(extra).status, "UNKNOWN");
  const missing = fixture();
  delete missing.lifecycle_claim_result;
  assert.equal(build(missing).status, "UNKNOWN");
});

test("cycles, accessors, custom prototypes, and oversized strings are rejected", () => {
  const cyclic = fixture();
  cyclic.security_gate_evaluation.loop = cyclic.security_gate_evaluation;
  assert.equal(build(cyclic).status, "UNKNOWN");

  let getterInvoked = false;
  const accessor = fixture();
  Object.defineProperty(accessor, "security_gate_evaluation", {
    enumerable: true,
    get() {
      getterInvoked = true;
      return fixture().security_gate_evaluation;
    },
  });
  assert.equal(build(accessor).status, "UNKNOWN");
  assert.equal(getterInvoked, false);

  const customPrototype = fixture();
  customPrototype.lifecycle_owner_creation = Object.create({ inherited: true });
  customPrototype.lifecycle_owner_creation.marker = "local";
  assert.equal(build(customPrototype).status, "UNKNOWN");

  const oversized = fixture();
  oversized.lifecycle_claim_result.padding = "x".repeat(
    subject.INPUT_LIMITS.max_string_length + 1
  );
  assert.equal(build(oversized).status, "UNKNOWN");
});

test("projection is deterministic and does not mutate input", () => {
  const input = fixture();
  const before = JSON.stringify(input);
  assert.deepEqual(build(input), build(input));
  assert.equal(JSON.stringify(input), before);
});

test("exact verifier rejects a resealed permission promotion", () => {
  const input = fixture();
  const presentation = build(input);
  assert.equal(
    subject.verifySecurityLifecycleNeutralPresentationV1(presentation, input),
    true
  );
  const promoted = JSON.parse(JSON.stringify(presentation));
  promoted.authority.writer_allowed = true;
  delete promoted.presentation_hash;
  const resealed = strictCanonical.sealDocument(
    promoted,
    "presentation_hash"
  );
  assert.equal(
    subject.verifySecurityLifecycleNeutralPresentationV1(resealed, input),
    false
  );
});

test("serialized presentation contains no promotional or execution wording", () => {
  const serialized = JSON.stringify(build());
  const forbidden = new RegExp(
    "\\b(?:" + ["REA", "DY|PRO", "FIT|RET", "URN|B", "UY|S", "ELL"].join("") + ")\\b",
    "i"
  );
  assert.equal(forbidden.test(serialized), false);
});

test("production module is unmounted and has no DOM or network operation", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "strategy_correlation_matrix_geometry_budget_multi_window_security_lifecycle_neutral_presentation_v1.js"
    ),
    "utf8"
  );
  assert.equal(source.includes("document."), false);
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("WebSocket"), false);
  assert.equal(source.includes("eval("), false);
});
