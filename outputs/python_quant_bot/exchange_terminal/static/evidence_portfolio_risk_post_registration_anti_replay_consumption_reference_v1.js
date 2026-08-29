"use strict";

const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const witnessV2 = require("./evidence_portfolio_risk_post_registration_execution_witness_signature_candidate_v2.js");

const REQUEST_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-consumption-request-v1";
const REQUEST_STATIC_FINGERPRINT =
  "20260823-post-registration-anti-replay-consumption-request-v1-lock-1";
const REFERENCE_STATE_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-reference-state-v1";
const REFERENCE_STATE_STATIC_FINGERPRINT =
  "20260823-post-registration-anti-replay-reference-state-v1-lock-1";
const OBSERVATION_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-transition-observation-v1";
const OBSERVATION_STATIC_FINGERPRINT =
  "20260823-post-registration-anti-replay-transition-observation-v1-lock-1";
const EXACT_VERIFICATION_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-transition-exact-rebuild-v1";

const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const WITNESS_V2_IMPLEMENTATION_SHA256 =
  "7e4a52b0559d500d137dfb5c409988c8958e698429a78dafbc3f5f06ad6e2fdc";

const HASH_PATTERN = /^[0-9a-f]{64}$/;
const OUTCOMES = Object.freeze({
  FIRST_SEEN: "REFERENCE_FIRST_SEEN",
  DUPLICATE: "REFERENCE_DUPLICATE_REJECTED",
  CONFLICT: "REFERENCE_CONFLICT_REJECTED",
});

const WITNESS_AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "current_pointer_written",
  "descriptive_only",
  "formal_registration_activation_allowed",
  "live_order_allowed",
  "migration_allowed",
  "paper_authorized",
  "post_registration_receipt_issuance_allowed",
  "presentation_consumer_activation_allowed",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "shadow_consumer_activation_allowed",
  "signature_authority_allowed",
  "witness_candidate_activation_allowed",
  "writer_allowed",
]);
const WITNESS_FACTS = Object.freeze({
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
});
const WITNESS_SOURCE_KEYS = Object.freeze([
  "anti_replay_scope_hash",
  "attestation_hash",
  "challenge_hash",
  "execution_evidence_v4_hash",
  "issuance_preregistration_hash",
  "key_algorithm",
  "policy_hash",
  "public_key_material_embedded",
  "public_key_spki_sha256",
  "raw_nonce_embedded",
  "registration_v7_hash",
  "signature_material_embedded",
  "signed_payload",
  "verification_envelope_hash",
  "witness_id",
]);
const WITNESS_CHECK_NAMES = Object.freeze([
  "issuance_preregistration_v1_exact",
  "python_verification_envelope_v1_exact",
  "witness_policy_v2_exact",
  "document_bundle_challenge_v2_exact",
  "detached_attestation_v2_exact",
  "ed25519_public_key_hash_matches_policy",
  "ed25519_detached_signature_verified",
  "anti_replay_consumption_not_claimed_before_implementation",
]);
const WITNESS_BLOCKERS = Object.freeze([
  "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
  "ANTI_REPLAY_CONSUMPTION_RECEIPT_V1_MISSING",
  "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
  "TRUSTED_SIGNATURE_TIME_UNVERIFIED",
  "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
  "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNVERIFIED",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
  "BROWSER_ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNAUTHORIZED",
]);
const AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "post_registration_receipt_issuance_allowed",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
]);
const REFERENCE_BLOCKERS = Object.freeze([
  "REFERENCE_MODEL_IS_NOT_AN_EXTERNAL_REGISTRY",
  "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
  "REGISTRY_IDENTITY_UNVERIFIED",
  "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
  "TRUSTED_CONSUMPTION_TIME_UNVERIFIED",
  "TARGET_CONSUMPTION_RECEIPT_V1_NOT_ISSUED",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
]);

function hasExactKeys(value, keys) {
  return (
    isPlainRecord(value) &&
    Object.keys(value).sort().join("\n") === [...keys].sort().join("\n")
  );
}

function isHash(value) {
  return typeof value === "string" && HASH_PATTERN.test(value);
}

function sameArray(value, expected) {
  return (
    Array.isArray(value) &&
    value.length === expected.length &&
    value.every((item, index) => item === expected[index])
  );
}

function lockedAuthority() {
  return Object.fromEntries(AUTHORITY_KEYS.map((key) => [key, false]));
}

function isLockedAuthority(value) {
  return (
    hasExactKeys(value, AUTHORITY_KEYS) &&
    AUTHORITY_KEYS.every((key) => value[key] === false)
  );
}

function hasExpectedWitnessAuthority(value) {
  return (
    hasExactKeys(value, WITNESS_AUTHORITY_KEYS) &&
    WITNESS_AUTHORITY_KEYS.every((key) =>
      key === "descriptive_only" ? value[key] === true : value[key] === false
    )
  );
}

function hasExpectedWitnessFacts(value) {
  const keys = Object.keys(WITNESS_FACTS);
  return (
    hasExactKeys(value, keys) &&
    keys.every((key) => value[key] === WITNESS_FACTS[key])
  );
}

function hasExpectedWitnessSource(value) {
  if (!hasExactKeys(value, WITNESS_SOURCE_KEYS)) {
    return false;
  }
  const hashKeys = [
    "anti_replay_scope_hash",
    "attestation_hash",
    "challenge_hash",
    "execution_evidence_v4_hash",
    "issuance_preregistration_hash",
    "policy_hash",
    "public_key_spki_sha256",
    "registration_v7_hash",
    "verification_envelope_hash",
  ];
  return (
    hashKeys.every((key) => isHash(value[key])) &&
    value.key_algorithm === "Ed25519" &&
    value.signed_payload === "STRICT_CANONICAL_CHALLENGE_DOCUMENT" &&
    value.public_key_material_embedded === false &&
    value.raw_nonce_embedded === false &&
    value.signature_material_embedded === false &&
    typeof value.witness_id === "string" &&
    value.witness_id.length > 0
  );
}

function isExactWitnessVerificationDocument(value) {
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "checks",
      "decision",
      "facts",
      "local_signature_status",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
      "verification_hash",
    ]) ||
    !verifySealedDocument(value, "verification_hash") ||
    value.schema_version !== witnessV2.VERIFICATION_SCHEMA_VERSION ||
    value.static_fingerprint !== witnessV2.VERIFICATION_STATIC_FINGERPRINT ||
    value.status !== "BLOCKED" ||
    value.local_signature_status !== "PASS" ||
    value.decision !==
      "PREREGISTERED_ED25519_KEY_POSSESSION_VERIFIED_ANTI_REPLAY_IDENTITY_AND_RECEIPT_UNBOUND" ||
    !sameArray(value.blockers, WITNESS_BLOCKERS) ||
    !hasExpectedWitnessAuthority(value.authority) ||
    !hasExpectedWitnessFacts(value.facts) ||
    !hasExpectedWitnessSource(value.source) ||
    !Array.isArray(value.checks) ||
    value.checks.length !== WITNESS_CHECK_NAMES.length
  ) {
    return false;
  }
  return value.checks.every(
    (check, index) =>
      hasExactKeys(check, ["blocking", "name", "ok"]) &&
      check.name === WITNESS_CHECK_NAMES[index] &&
      check.ok === true &&
      check.blocking === true
  );
}

function isExactWitnessRebuildEvidence(value, verification) {
  const falseFields = [
    "anti_replay_registry_bound",
    "atomic_nonce_consumption_verified",
    "current_admission_allowed",
    "independent_execution_process_witnessed",
    "live_order_allowed",
    "paper_authorized",
    "post_registration_receipt_issued",
    "presentation_mount_allowed",
    "runtime_gate_activation_allowed",
    "witness_organization_identity_verified",
    "writer_allowed",
  ];
  return (
    hasExactKeys(value, [
      ...falseFields,
      "blockers",
      "local_signature_status",
      "schema_version",
      "status",
      "verification_document_exactly_rebuilt",
      "verification_hash",
      "verification_status",
    ]) &&
    value.schema_version === witnessV2.EXACT_VERIFICATION_SCHEMA_VERSION &&
    value.status === "PASS" &&
    value.verification_document_exactly_rebuilt === true &&
    value.verification_hash === verification.verification_hash &&
    value.verification_status === "BLOCKED" &&
    value.local_signature_status === "PASS" &&
    Array.isArray(value.blockers) &&
    value.blockers.length === 0 &&
    falseFields.every((field) => value[field] === false)
  );
}

function requestFacts() {
  return {
    external_linearizability_verified: false,
    external_registry_bound: false,
    local_signature_verified: true,
    network_accessed: false,
    post_registration_receipt_issued: false,
    raw_nonce_embedded: false,
    registry_identity_verified: false,
    runtime_assets_accessed: false,
    target_consumption_receipt_issued: false,
    trusted_consumption_time_verified: false,
    witness_verification_exactly_rebuilt: true,
  };
}

function buildAntiReplayConsumptionRequestV1(verification, exactEvidence) {
  if (
    !isExactWitnessVerificationDocument(verification) ||
    !isExactWitnessRebuildEvidence(exactEvidence, verification)
  ) {
    throw new TypeError("witness-v2 verification is not exact and locally valid");
  }
  const source = {
    anti_replay_namespace: witnessV2.ANTI_REPLAY_NAMESPACE,
    anti_replay_scope_hash: verification.source.anti_replay_scope_hash,
    attestation_hash: verification.source.attestation_hash,
    challenge_hash: verification.source.challenge_hash,
    consumption_key: strictCanonicalHash({
      anti_replay_namespace: witnessV2.ANTI_REPLAY_NAMESPACE,
      anti_replay_scope_hash: verification.source.anti_replay_scope_hash,
    }),
    issuance_preregistration_hash:
      verification.source.issuance_preregistration_hash,
    policy_hash: verification.source.policy_hash,
    public_key_spki_sha256: verification.source.public_key_spki_sha256,
    witness_id: verification.source.witness_id,
    witness_verification_hash: verification.verification_hash,
  };
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...REFERENCE_BLOCKERS],
      decision:
        "REFERENCE_CONSUMPTION_REQUEST_ONLY_EXTERNAL_REGISTRY_AND_RECEIPT_UNBOUND",
      facts: requestFacts(),
      schema_version: REQUEST_SCHEMA_VERSION,
      source,
      static_fingerprint: REQUEST_STATIC_FINGERPRINT,
      status: "BLOCKED",
      target: {
        consumption_receipt_schema_version:
          witnessV2.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
        post_registration_receipt_schema_version:
          witnessV2.TARGET_RECEIPT_SCHEMA_VERSION,
      },
    },
    "request_hash"
  );
}

function verifyAntiReplayConsumptionRequestV1(value) {
  const sourceKeys = [
    "anti_replay_namespace",
    "anti_replay_scope_hash",
    "attestation_hash",
    "challenge_hash",
    "consumption_key",
    "issuance_preregistration_hash",
    "policy_hash",
    "public_key_spki_sha256",
    "witness_id",
    "witness_verification_hash",
  ];
  const factKeys = Object.keys(requestFacts());
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "decision",
      "facts",
      "request_hash",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
      "target",
    ]) ||
    !verifySealedDocument(value, "request_hash") ||
    value.schema_version !== REQUEST_SCHEMA_VERSION ||
    value.static_fingerprint !== REQUEST_STATIC_FINGERPRINT ||
    value.status !== "BLOCKED" ||
    value.decision !==
      "REFERENCE_CONSUMPTION_REQUEST_ONLY_EXTERNAL_REGISTRY_AND_RECEIPT_UNBOUND" ||
    !sameArray(value.blockers, REFERENCE_BLOCKERS) ||
    !isLockedAuthority(value.authority) ||
    !hasExactKeys(value.facts, factKeys) ||
    !factKeys.every((key) => value.facts[key] === requestFacts()[key]) ||
    !hasExactKeys(value.source, sourceKeys) ||
    !hasExactKeys(value.target, [
      "consumption_receipt_schema_version",
      "post_registration_receipt_schema_version",
    ])
  ) {
    return false;
  }
  const sourceHashKeys = [
    "anti_replay_scope_hash",
    "attestation_hash",
    "challenge_hash",
    "consumption_key",
    "issuance_preregistration_hash",
    "policy_hash",
    "public_key_spki_sha256",
    "witness_verification_hash",
  ];
  return (
    sourceHashKeys.every((key) => isHash(value.source[key])) &&
    value.source.anti_replay_namespace === witnessV2.ANTI_REPLAY_NAMESPACE &&
    typeof value.source.witness_id === "string" &&
    value.source.witness_id.length > 0 &&
    value.source.consumption_key ===
      strictCanonicalHash({
        anti_replay_namespace: value.source.anti_replay_namespace,
        anti_replay_scope_hash: value.source.anti_replay_scope_hash,
      }) &&
    value.target.consumption_receipt_schema_version ===
      witnessV2.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION &&
    value.target.post_registration_receipt_schema_version ===
      witnessV2.TARGET_RECEIPT_SCHEMA_VERSION
  );
}

function createAntiReplayReferenceStateV1() {
  return sealDocument(
    {
      entries: [],
      reference_model_only: true,
      revision: 0,
      schema_version: REFERENCE_STATE_SCHEMA_VERSION,
      static_fingerprint: REFERENCE_STATE_STATIC_FINGERPRINT,
      status: "REFERENCE_ONLY",
    },
    "state_hash"
  );
}

function verifyAntiReplayReferenceStateV1(value) {
  if (
    !hasExactKeys(value, [
      "entries",
      "reference_model_only",
      "revision",
      "schema_version",
      "state_hash",
      "static_fingerprint",
      "status",
    ]) ||
    !verifySealedDocument(value, "state_hash") ||
    value.schema_version !== REFERENCE_STATE_SCHEMA_VERSION ||
    value.static_fingerprint !== REFERENCE_STATE_STATIC_FINGERPRINT ||
    value.reference_model_only !== true ||
    value.status !== "REFERENCE_ONLY" ||
    !Number.isSafeInteger(value.revision) ||
    value.revision < 0 ||
    !Array.isArray(value.entries) ||
    value.revision !== value.entries.length
  ) {
    return false;
  }
  for (let index = 0; index < value.entries.length; index += 1) {
    const entry = value.entries[index];
    if (
      !hasExactKeys(entry, [
        "anti_replay_scope_hash",
        "consumption_key",
        "first_request_hash",
        "witness_verification_hash",
      ]) ||
      !Object.values(entry).every(isHash) ||
      (index > 0 &&
        value.entries[index - 1].consumption_key >= entry.consumption_key)
    ) {
      return false;
    }
  }
  return true;
}

function cloneState(value) {
  return {
    ...value,
    entries: value.entries.map((entry) => ({ ...entry })),
  };
}

function observationFacts(outcome) {
  return {
    atomic_nonce_consumption_verified: false,
    conflict_rejected: outcome === OUTCOMES.CONFLICT,
    duplicate_rejected: outcome === OUTCOMES.DUPLICATE,
    external_linearizability_verified: false,
    external_registry_bound: false,
    network_accessed: false,
    post_registration_receipt_issued: false,
    reference_first_seen: outcome === OUTCOMES.FIRST_SEEN,
    reference_model_only: true,
    reference_transition_exact: true,
    registry_identity_verified: false,
    runtime_assets_accessed: false,
    target_consumption_receipt_issued: false,
    trusted_consumption_time_verified: false,
  };
}

function applyAntiReplayConsumptionReferenceV1(state, request) {
  if (!verifyAntiReplayReferenceStateV1(state)) {
    throw new TypeError("invalid anti-replay reference state-v1");
  }
  if (!verifyAntiReplayConsumptionRequestV1(request)) {
    throw new TypeError("invalid anti-replay consumption request-v1");
  }
  const existing = state.entries.find(
    (entry) => entry.consumption_key === request.source.consumption_key
  );
  let outcome;
  let nextState;
  if (!existing) {
    outcome = OUTCOMES.FIRST_SEEN;
    const entries = [
      ...state.entries.map((entry) => ({ ...entry })),
      {
        anti_replay_scope_hash: request.source.anti_replay_scope_hash,
        consumption_key: request.source.consumption_key,
        first_request_hash: request.request_hash,
        witness_verification_hash: request.source.witness_verification_hash,
      },
    ].sort((left, right) =>
      left.consumption_key < right.consumption_key
        ? -1
        : left.consumption_key > right.consumption_key
          ? 1
          : 0
    );
    nextState = sealDocument(
      {
        entries,
        reference_model_only: true,
        revision: state.revision + 1,
        schema_version: REFERENCE_STATE_SCHEMA_VERSION,
        static_fingerprint: REFERENCE_STATE_STATIC_FINGERPRINT,
        status: "REFERENCE_ONLY",
      },
      "state_hash"
    );
  } else {
    outcome =
      existing.first_request_hash === request.request_hash
        ? OUTCOMES.DUPLICATE
        : OUTCOMES.CONFLICT;
    nextState = cloneState(state);
  }
  const decisionByOutcome = {
    [OUTCOMES.FIRST_SEEN]:
      "REFERENCE_FIRST_SEEN_ONLY_EXTERNAL_ATOMIC_CONSUMPTION_UNVERIFIED",
    [OUTCOMES.DUPLICATE]:
      "REFERENCE_DUPLICATE_REJECTED_EXTERNAL_ATOMIC_CONSUMPTION_UNVERIFIED",
    [OUTCOMES.CONFLICT]:
      "REFERENCE_CONFLICT_REJECTED_EXTERNAL_ATOMIC_CONSUMPTION_UNVERIFIED",
  };
  const observation = sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...REFERENCE_BLOCKERS],
      decision: decisionByOutcome[outcome],
      facts: observationFacts(outcome),
      outcome,
      schema_version: OBSERVATION_SCHEMA_VERSION,
      source: {
        consumption_key: request.source.consumption_key,
        next_state_hash: nextState.state_hash,
        prior_state_hash: state.state_hash,
        request_hash: request.request_hash,
        revision_after: nextState.revision,
        revision_before: state.revision,
      },
      static_fingerprint: OBSERVATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "observation_hash"
  );
  return { next_state: nextState, observation };
}

function blockedExactVerification(blocker) {
  return {
    atomic_nonce_consumption_verified: false,
    blockers: [blocker],
    current_admission_allowed: false,
    external_linearizability_verified: false,
    live_order_allowed: false,
    next_state_exactly_rebuilt: false,
    observation_exactly_rebuilt: false,
    outcome: "UNKNOWN",
    paper_authorized: false,
    post_registration_receipt_issued: false,
    presentation_mount_allowed: false,
    reference_transition_status: "UNKNOWN",
    registry_identity_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
    status: "BLOCK",
    target_consumption_receipt_issued: false,
    trusted_consumption_time_verified: false,
    writer_allowed: false,
  };
}

function verifyAntiReplayConsumptionReferenceTransitionV1(
  priorState,
  request,
  nextState,
  observation
) {
  try {
    const expected = applyAntiReplayConsumptionReferenceV1(priorState, request);
    const nextStateExact =
      verifyAntiReplayReferenceStateV1(nextState) &&
      strictCanonicalHash(nextState) === strictCanonicalHash(expected.next_state);
    const observationExact =
      verifySealedDocument(observation, "observation_hash") &&
      strictCanonicalHash(observation) ===
        strictCanonicalHash(expected.observation);
    if (!nextStateExact || !observationExact) {
      return blockedExactVerification(
        nextStateExact
          ? "ANTI_REPLAY_REFERENCE_OBSERVATION_EXACT_REBUILD"
          : "ANTI_REPLAY_REFERENCE_NEXT_STATE_EXACT_REBUILD"
      );
    }
    return {
      atomic_nonce_consumption_verified: false,
      blockers: [],
      current_admission_allowed: false,
      external_linearizability_verified: false,
      live_order_allowed: false,
      next_state_exactly_rebuilt: true,
      observation_exactly_rebuilt: true,
      outcome: expected.observation.outcome,
      paper_authorized: false,
      post_registration_receipt_issued: false,
      presentation_mount_allowed: false,
      reference_transition_status: "PASS",
      registry_identity_verified: false,
      runtime_gate_activation_allowed: false,
      schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
      status: "PASS",
      target_consumption_receipt_issued: false,
      trusted_consumption_time_verified: false,
      writer_allowed: false,
    };
  } catch (_error) {
    return blockedExactVerification(
      "ANTI_REPLAY_REFERENCE_TRANSITION_INPUT_INVALID"
    );
  }
}

module.exports = {
  EXACT_VERIFICATION_SCHEMA_VERSION,
  OBSERVATION_SCHEMA_VERSION,
  OBSERVATION_STATIC_FINGERPRINT,
  OUTCOMES,
  REFERENCE_STATE_SCHEMA_VERSION,
  REFERENCE_STATE_STATIC_FINGERPRINT,
  REQUEST_SCHEMA_VERSION,
  REQUEST_STATIC_FINGERPRINT,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION:
    witnessV2.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
  TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION:
    witnessV2.TARGET_RECEIPT_SCHEMA_VERSION,
  WITNESS_V2_IMPLEMENTATION_SHA256,
  applyAntiReplayConsumptionReferenceV1,
  buildAntiReplayConsumptionRequestV1,
  createAntiReplayReferenceStateV1,
  verifyAntiReplayConsumptionReferenceTransitionV1,
  verifyAntiReplayConsumptionRequestV1,
  verifyAntiReplayReferenceStateV1,
};
