"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const witnessV2 = require("./evidence_portfolio_risk_post_registration_execution_witness_signature_candidate_v2.js");
const referenceV1 = require("./evidence_portfolio_risk_post_registration_anti_replay_consumption_reference_v1.js");

function hash(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex");
}

function fileHash(name) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(path.join(__dirname, name)))
    .digest("hex");
}

function lockedWitnessAuthority() {
  return {
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    formal_registration_activation_allowed: false,
    live_order_allowed: false,
    migration_allowed: false,
    paper_authorized: false,
    post_registration_receipt_issuance_allowed: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    shadow_consumer_activation_allowed: false,
    signature_authority_allowed: false,
    witness_candidate_activation_allowed: false,
    writer_allowed: false,
  };
}

function witnessFacts() {
  return {
    anti_replay_consumption_receipt_present: false,
    anti_replay_consumption_receipt_supported: false,
    anti_replay_registry_bound: false,
    atomic_nonce_consumption_verified: false,
    browser_visual_review_performed: false,
    cryptographic_key_possession_verified: true,
    cryptographic_signature_verified: true,
    duplicate_rejection_verified: false,
    independent_execution_process_witnessed: false,
    local_node_contract_execution_observed: true,
    local_signature_contract_complete: true,
    network_accessed: false,
    post_registration_receipt_issued: false,
    preregistered_public_key_hash_matched: true,
    private_key_material_received: false,
    profitability_proven: false,
    public_key_material_embedded: false,
    public_key_material_received_by_verifier: true,
    raw_nonce_embedded: false,
    raw_nonce_received: true,
    runtime_assets_accessed: false,
    runtime_consumer_bound: false,
    signature_material_embedded: false,
    signature_material_received: true,
    trusted_timestamp_verified: false,
    witness_organization_identity_verified: false,
  };
}

function witnessFixture(label, scopeLabel = label) {
  const verification = canonical.sealDocument(
    {
      authority: lockedWitnessAuthority(),
      blockers: [
        "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
        "ANTI_REPLAY_CONSUMPTION_RECEIPT_V1_MISSING",
        "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
        "TRUSTED_SIGNATURE_TIME_UNVERIFIED",
        "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
        "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNVERIFIED",
        "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
        "BROWSER_ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNAUTHORIZED",
      ],
      checks: [
        "issuance_preregistration_v1_exact",
        "python_verification_envelope_v1_exact",
        "witness_policy_v2_exact",
        "document_bundle_challenge_v2_exact",
        "detached_attestation_v2_exact",
        "ed25519_public_key_hash_matches_policy",
        "ed25519_detached_signature_verified",
        "anti_replay_consumption_not_claimed_before_implementation",
      ].map((name) => ({ blocking: true, name, ok: true })),
      decision:
        "PREREGISTERED_ED25519_KEY_POSSESSION_VERIFIED_ANTI_REPLAY_IDENTITY_AND_RECEIPT_UNBOUND",
      facts: witnessFacts(),
      local_signature_status: "PASS",
      schema_version: witnessV2.VERIFICATION_SCHEMA_VERSION,
      source: {
        anti_replay_scope_hash: hash(`${scopeLabel}:scope`),
        attestation_hash: hash(`${label}:attestation`),
        challenge_hash: hash(`${label}:challenge`),
        execution_evidence_v4_hash: hash(`${label}:evidence`),
        issuance_preregistration_hash: hash(`${label}:preregistration`),
        key_algorithm: "Ed25519",
        policy_hash: hash(`${label}:policy`),
        public_key_material_embedded: false,
        public_key_spki_sha256: hash(`${label}:public-key`),
        raw_nonce_embedded: false,
        registration_v7_hash: hash(`${label}:registration`),
        signature_material_embedded: false,
        signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
        verification_envelope_hash: hash(`${label}:envelope`),
        witness_id: `synthetic-${label}`,
      },
      static_fingerprint: witnessV2.VERIFICATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "verification_hash"
  );
  const exact = {
    anti_replay_registry_bound: false,
    atomic_nonce_consumption_verified: false,
    blockers: [],
    current_admission_allowed: false,
    independent_execution_process_witnessed: false,
    live_order_allowed: false,
    local_signature_status: "PASS",
    paper_authorized: false,
    post_registration_receipt_issued: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    schema_version: witnessV2.EXACT_VERIFICATION_SCHEMA_VERSION,
    status: "PASS",
    verification_document_exactly_rebuilt: true,
    verification_hash: verification.verification_hash,
    verification_status: "BLOCKED",
    witness_organization_identity_verified: false,
    writer_allowed: false,
  };
  return { exact, verification };
}

function request(label, scopeLabel = label) {
  const fixture = witnessFixture(label, scopeLabel);
  return referenceV1.buildAntiReplayConsumptionRequestV1(
    fixture.verification,
    fixture.exact
  );
}

function reseal(document, hashField, mutate) {
  const body = structuredClone(document);
  delete body[hashField];
  mutate(body);
  return canonical.sealDocument(body, hashField);
}

test("exports exact schemas and pinned source dependencies", () => {
  assert.equal(
    referenceV1.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
    witnessV2.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION
  );
  assert.equal(
    referenceV1.TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION,
    witnessV2.TARGET_RECEIPT_SCHEMA_VERSION
  );
  assert.equal(
    fileHash("strict_canonical_json_v1.js"),
    referenceV1.STRICT_CANONICAL_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash(
      "evidence_portfolio_risk_post_registration_execution_witness_signature_candidate_v2.js"
    ),
    referenceV1.WITNESS_V2_IMPLEMENTATION_SHA256
  );
});

test("request binds exact witness output without raw nonce or signature material", () => {
  const value = request("clear");
  assert.equal(referenceV1.verifyAntiReplayConsumptionRequestV1(value), true);
  assert.equal(value.status, "BLOCKED");
  assert.equal(value.facts.raw_nonce_embedded, false);
  assert.equal(value.facts.external_registry_bound, false);
  assert.equal(value.facts.external_linearizability_verified, false);
  assert.equal(JSON.stringify(value).includes("signature_material"), false);
  assert.equal(JSON.stringify(value).includes("raw_nonce\""), false);
});

test("first-seen transition changes only the sealed reference state", () => {
  const prior = referenceV1.createAntiReplayReferenceStateV1();
  const result = referenceV1.applyAntiReplayConsumptionReferenceV1(
    prior,
    request("first")
  );
  assert.equal(result.observation.outcome, referenceV1.OUTCOMES.FIRST_SEEN);
  assert.equal(result.observation.status, "BLOCKED");
  assert.equal(result.next_state.revision, 1);
  assert.equal(result.next_state.entries.length, 1);
  assert.equal(result.observation.facts.atomic_nonce_consumption_verified, false);
});

test("exact replay is rejected as duplicate without changing state", () => {
  const value = request("duplicate");
  const first = referenceV1.applyAntiReplayConsumptionReferenceV1(
    referenceV1.createAntiReplayReferenceStateV1(),
    value
  );
  const duplicate = referenceV1.applyAntiReplayConsumptionReferenceV1(
    first.next_state,
    value
  );
  assert.equal(duplicate.observation.outcome, referenceV1.OUTCOMES.DUPLICATE);
  assert.equal(duplicate.observation.facts.duplicate_rejected, true);
  assert.equal(duplicate.next_state.state_hash, first.next_state.state_hash);
  assert.equal(duplicate.next_state.revision, 1);
});

test("same scope with a different request is rejected as conflict", () => {
  const firstRequest = request("first-request", "shared");
  const conflictingRequest = request("second-request", "shared");
  const first = referenceV1.applyAntiReplayConsumptionReferenceV1(
    referenceV1.createAntiReplayReferenceStateV1(),
    firstRequest
  );
  const conflict = referenceV1.applyAntiReplayConsumptionReferenceV1(
    first.next_state,
    conflictingRequest
  );
  assert.equal(conflict.observation.outcome, referenceV1.OUTCOMES.CONFLICT);
  assert.equal(conflict.observation.facts.conflict_rejected, true);
  assert.equal(conflict.next_state.state_hash, first.next_state.state_hash);
});

test("different scopes are accepted and stored in canonical key order", () => {
  const first = referenceV1.applyAntiReplayConsumptionReferenceV1(
    referenceV1.createAntiReplayReferenceStateV1(),
    request("scope-b")
  );
  const second = referenceV1.applyAntiReplayConsumptionReferenceV1(
    first.next_state,
    request("scope-a")
  );
  assert.equal(second.next_state.revision, 2);
  assert.deepEqual(
    second.next_state.entries.map((entry) => entry.consumption_key),
    [...second.next_state.entries]
      .map((entry) => entry.consumption_key)
      .sort()
  );
});

test("the reference reducer is deterministic for identical inputs", () => {
  const prior = referenceV1.createAntiReplayReferenceStateV1();
  const value = request("deterministic");
  const left = referenceV1.applyAntiReplayConsumptionReferenceV1(prior, value);
  const right = referenceV1.applyAntiReplayConsumptionReferenceV1(prior, value);
  assert.deepEqual(left, right);
});

test("schema aliases and resealed request drift are rejected", () => {
  const value = request("alias");
  const alias = reseal(value, "request_hash", (body) => {
    body.schema_version = `${referenceV1.REQUEST_SCHEMA_VERSION}.0`;
  });
  const drift = reseal(value, "request_hash", (body) => {
    body.facts.external_registry_bound = true;
  });
  assert.equal(referenceV1.verifyAntiReplayConsumptionRequestV1(alias), false);
  assert.equal(referenceV1.verifyAntiReplayConsumptionRequestV1(drift), false);
});

test("non-PASS exact witness evidence cannot create a request", () => {
  const fixture = witnessFixture("invalid-exact");
  fixture.exact.status = "BLOCK";
  assert.throws(
    () =>
      referenceV1.buildAntiReplayConsumptionRequestV1(
        fixture.verification,
        fixture.exact
      ),
    /not exact and locally valid/
  );
});

test("state rollback and entry tampering are rejected", () => {
  const first = referenceV1.applyAntiReplayConsumptionReferenceV1(
    referenceV1.createAntiReplayReferenceStateV1(),
    request("state-tamper")
  );
  const rollback = reseal(first.next_state, "state_hash", (body) => {
    body.revision = 0;
  });
  const entryDrift = structuredClone(first.next_state);
  entryDrift.entries[0].first_request_hash = hash("forged");
  assert.equal(referenceV1.verifyAntiReplayReferenceStateV1(rollback), false);
  assert.equal(referenceV1.verifyAntiReplayReferenceStateV1(entryDrift), false);
});

test("public exact verifier PASS means only exact reference reconstruction", () => {
  const prior = referenceV1.createAntiReplayReferenceStateV1();
  const value = request("exact");
  const transition = referenceV1.applyAntiReplayConsumptionReferenceV1(
    prior,
    value
  );
  const exact = referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
    prior,
    value,
    transition.next_state,
    transition.observation
  );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.reference_transition_status, "PASS");
  assert.equal(exact.atomic_nonce_consumption_verified, false);
  assert.equal(exact.external_linearizability_verified, false);
  assert.equal(exact.registry_identity_verified, false);
  assert.equal(exact.target_consumption_receipt_issued, false);
  assert.equal(exact.current_admission_allowed, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
  assert.equal(exact.writer_allowed, false);
});

test("tampered next state and observation fail exact reconstruction", () => {
  const prior = referenceV1.createAntiReplayReferenceStateV1();
  const value = request("exact-tamper");
  const transition = referenceV1.applyAntiReplayConsumptionReferenceV1(
    prior,
    value
  );
  const badState = structuredClone(transition.next_state);
  badState.state_hash = hash("bad-state");
  const badObservation = structuredClone(transition.observation);
  badObservation.observation_hash = hash("bad-observation");
  assert.equal(
    referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
      prior,
      value,
      badState,
      transition.observation
    ).status,
    "BLOCK"
  );
  assert.equal(
    referenceV1.verifyAntiReplayConsumptionReferenceTransitionV1(
      prior,
      value,
      transition.next_state,
      badObservation
    ).status,
    "BLOCK"
  );
});

test("branch-local first-seen results never claim shared linearizability", () => {
  const prior = referenceV1.createAntiReplayReferenceStateV1();
  const left = referenceV1.applyAntiReplayConsumptionReferenceV1(
    prior,
    request("branch-left", "branch-shared")
  );
  const right = referenceV1.applyAntiReplayConsumptionReferenceV1(
    prior,
    request("branch-right", "branch-shared")
  );
  assert.equal(left.observation.outcome, referenceV1.OUTCOMES.FIRST_SEEN);
  assert.equal(right.observation.outcome, referenceV1.OUTCOMES.FIRST_SEEN);
  assert.equal(left.observation.facts.external_linearizability_verified, false);
  assert.equal(right.observation.facts.external_linearizability_verified, false);
  assert.equal(left.observation.facts.target_consumption_receipt_issued, false);
  assert.equal(right.observation.facts.target_consumption_receipt_issued, false);
});
