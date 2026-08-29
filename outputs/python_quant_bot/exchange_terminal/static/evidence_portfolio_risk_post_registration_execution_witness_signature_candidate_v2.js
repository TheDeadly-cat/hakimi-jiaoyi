"use strict";

const crypto = require("node:crypto");
const canonical = require("./strict_canonical_json_v1.js");

const POLICY_SCHEMA_VERSION =
  "portfolio-risk-post-registration-execution-witness-policy-v2";
const POLICY_STATIC_FINGERPRINT =
  "20260823-post-registration-ed25519-witness-policy-v2-lock-1";
const CHALLENGE_SCHEMA_VERSION =
  "portfolio-risk-post-registration-document-bundle-challenge-v2";
const CHALLENGE_STATIC_FINGERPRINT =
  "20260823-post-registration-document-bundle-challenge-v2-lock-1";
const ATTESTATION_SCHEMA_VERSION =
  "portfolio-risk-post-registration-detached-attestation-v2";
const ATTESTATION_STATIC_FINGERPRINT =
  "20260823-post-registration-ed25519-detached-attestation-v2-lock-1";
const VERIFICATION_SCHEMA_VERSION =
  "portfolio-risk-post-registration-witness-verification-candidate-v2";
const VERIFICATION_STATIC_FINGERPRINT =
  "20260823-post-registration-ed25519-possession-verification-v2-lock-1";
const EXACT_VERIFICATION_SCHEMA_VERSION =
  `${VERIFICATION_SCHEMA_VERSION}-exact-rebuild-v1`;

const PREREGISTRATION_SCHEMA_VERSION =
  "portfolio-risk-downside-tail-post-registration-execution-issuance-preregistration-v1";
const PREREGISTRATION_STATIC_FINGERPRINT =
  "20260823-registration-v7-receipt-v5-single-use-preregistration-lock-1";
const ENVELOPE_SCHEMA_VERSION =
  "portfolio-risk-downside-tail-post-registration-execution-issuance-preregistration-verification-envelope-v1";
const ENVELOPE_STATIC_FINGERPRINT =
  "20260823-receipt-v5-issuance-preregistration-python-envelope-lock-1";
const PREREGISTRATION_IMPLEMENTATION_SHA256 =
  "76a1c05a55395c3258869336b0d00b8e1613670befea35f6152be6947016e6ce";
const ENVELOPE_IMPLEMENTATION_SHA256 =
  "3f2a6b5fadec8b2ac299937505b35b7b7f00b213c4c49241acb26adb192028e7";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const REGISTRATION_V7_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v7";
const REGISTRATION_V7_STATIC_FINGERPRINT =
  "20260823-downside-tail-evidence-v4-registration-v7-lock-1";
const REGISTRATION_V7_IMPLEMENTATION_SHA256 =
  "23f1cf3fe1e8be3b3740d0b4d592a78f32f518b399e680d3cd79044a138956e2";
const EVIDENCE_V4_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-execution-evidence-v4";
const EVIDENCE_V4_IMPLEMENTATION_SHA256 =
  "c1e9bb3f122dd94cb6fd45a9eb1f1c40ecefc539a2af9d12be5f680c5a3819b5";
const TARGET_RECEIPT_SCHEMA_VERSION =
  "portfolio-risk-downside-tail-consumer-post-registration-execution-receipt-v5";
const TARGET_RECEIPT_STATIC_FINGERPRINT =
  "20260823-downside-tail-consumer-v6-post-registration-receipt-v5-lock-1";
const TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1";
const ANTI_REPLAY_SCOPE_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-scope-v1";
const ANTI_REPLAY_NAMESPACE =
  "portfolio-risk-downside-tail-post-registration-execution-receipt-v5";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
const SEMANTIC_STATES = new Set(["CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"]);

const UNDERLYING_AUTHORITY = Object.freeze({
  descriptive_only: true,
  current_admission_allowed: false,
  current_pointer_written: false,
  formal_registration_activation_allowed: false,
  live_order_allowed: false,
  migration_allowed: false,
  paper_authorized: false,
  presentation_consumer_activation_allowed: false,
  presentation_mount_allowed: false,
  post_registration_receipt_issuance_allowed: false,
  runtime_gate_activation_allowed: false,
  shadow_consumer_activation_allowed: false,
  writer_allowed: false,
});
const ENVELOPE_AUTHORITY = Object.freeze({
  ...UNDERLYING_AUTHORITY,
  witness_candidate_activation_allowed: false,
});
const WITNESS_AUTHORITY = Object.freeze({
  ...ENVELOPE_AUTHORITY,
  signature_authority_allowed: false,
});

const PREREGISTRATION_CHECK_NAMES = Object.freeze([
  "registration_v7_exact_blocked_candidate",
  "execution_evidence_v4_hash_edge_exact",
  "pre_registration_receipt_v4_hash_edge_exact",
  "projection_v6_hash_edge_exact",
  "execution_preregistration_v1_hash_edge_exact",
  "pre_registration_receipt_absence_preserved",
  "issuance_id_format_exact",
  "nonce_commitment_shape_exact",
  "anti_replay_scope_derivation_exact",
  "future_receipt_witness_and_consumption_schemas_frozen",
]);
const PREREGISTRATION_CLOSED = Object.freeze([
  "REGISTRATION_V7_EXACT_BLOCKED_CANDIDATE_BOUND",
  "PRE_REGISTRATION_EXECUTION_CHAIN_HASHES_BOUND",
  "POST_REGISTRATION_RECEIPT_V5_TARGET_SCHEMA_FROZEN",
  "ANTI_REPLAY_NAMESPACE_AND_SINGLE_USE_POLICY_FROZEN",
  "NONCE_COMMITMENT_BOUND_WITHOUT_NONCE_DISCLOSURE",
]);
const PREREGISTRATION_BLOCKERS = Object.freeze([
  "WITNESS_POLICY_V2_IMPLEMENTATION_MISSING",
  "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
  "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
  "NONCE_ENTROPY_AND_TRUSTED_TIME_UNVERIFIED",
  "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
  "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNVERIFIED",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
  "BROWSER_ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNAUTHORIZED",
]);
const PREREGISTRATION_ACTIVATION_ORDER = Object.freeze([
  "REGISTRATION_V7_STATIC_BLOCKED_CANDIDATE",
  "POST_REGISTRATION_ISSUANCE_PREREGISTRATION_V1",
  "WITNESS_POLICY_AND_CHALLENGE_V2",
  "EXTERNAL_LINEARIZABLE_ANTI_REPLAY_REGISTRY",
  "ATOMIC_NONCE_CONSUMPTION_RECEIPT_V1",
  "INDEPENDENT_WITNESS_ATTESTATION_V2",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5",
  "PYTHON_POST_REGISTRATION_RECEIPT_EVIDENCE",
  "EXPLICIT_BROWSER_VISUAL_REVIEW",
  "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
]);
const ENVELOPE_CHECK_NAMES = Object.freeze([
  "issuance_preregistration_v1_strict_canonical_seal_exact",
  "issuance_preregistration_v1_identity_blocked_exact",
  "issuance_preregistration_v1_public_verifier_pass",
  "execution_semantic_state_exact",
  "registration_v7_hash_edge_exact",
  "execution_evidence_v4_hash_edge_exact",
  "pre_registration_receipt_v4_hash_edge_exact",
  "projection_v6_hash_edge_exact",
  "execution_preregistration_v1_hash_edge_exact",
  "issuance_id_commitment_and_scope_hash_bound",
  "future_target_schemas_exact",
  "anti_replay_registry_remains_explicitly_unbound",
  "issuance_preregistration_authority_locked",
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

function isRecord(value) {
  return canonical.isPlainRecord(value);
}

function isHash(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isNonceCommitment(value) {
  return (
    isHash(value) &&
    value !== "0".repeat(64) &&
    value !== "f".repeat(64) &&
    new Set(value).size >= 8
  );
}

function isIssuanceId(value) {
  return (
    typeof value === "string" &&
    /^[a-z0-9][a-z0-9._:-]{7,127}$/.test(value)
  );
}

function isWitnessId(value) {
  return isIssuanceId(value);
}

function isPrintableToken(value, minimum = 32, maximum = 256) {
  return (
    typeof value === "string" &&
    value.length >= minimum &&
    value.length <= maximum &&
    /^[\x21-\x7e]+$/.test(value) &&
    new Set(value).size >= 8
  );
}

function exactJson(left, right) {
  try {
    return canonical.strictCanonicalStringify(left) === canonical.strictCanonicalStringify(right);
  } catch (_error) {
    return false;
  }
}

function sealedExact(document, hashField) {
  return Boolean(
    isRecord(document) &&
      isHash(document[hashField]) &&
      canonical.verifySealedDocument(document, hashField),
  );
}

function checks(names, ok = true) {
  return names.map((name) => ({ name, ok, blocking: true }));
}

function sha256Utf8(value) {
  return crypto.createHash("sha256").update(Buffer.from(value, "utf8")).digest("hex");
}

function expectedPreregistration(document) {
  if (!isRecord(document) || !isRecord(document.source) || !isRecord(document.issuance) || !isRecord(document.anti_replay)) {
    return null;
  }
  const source = document.source;
  const issuance = document.issuance;
  const antiReplay = document.anti_replay;
  const hashes = [
    source.registration_v7_hash,
    source.execution_evidence_v4_hash,
    source.pre_registration_receipt_v4_hash,
    source.projection_v6_hash,
    source.execution_preregistration_v1_hash,
  ];
  if (
    !hashes.every(isHash) ||
    !SEMANTIC_STATES.has(source.execution_semantic_state) ||
    !isIssuanceId(issuance.issuance_id) ||
    !isNonceCommitment(antiReplay.nonce_commitment_sha256)
  ) {
    return null;
  }
  const scopeDocument = {
    schema_version: ANTI_REPLAY_SCOPE_SCHEMA_VERSION,
    namespace: ANTI_REPLAY_NAMESPACE,
    registration_hash: source.registration_v7_hash,
    execution_evidence_hash: source.execution_evidence_v4_hash,
    pre_registration_receipt_hash: source.pre_registration_receipt_v4_hash,
    issuance_id: issuance.issuance_id,
    nonce_commitment_sha256: antiReplay.nonce_commitment_sha256,
    issuance_sequence: 1,
  };
  const expectedScopeHash = canonical.strictCanonicalHash(scopeDocument);
  const expected = {
    schema_version: PREREGISTRATION_SCHEMA_VERSION,
    static_fingerprint: PREREGISTRATION_STATIC_FINGERPRINT,
    status: "BLOCKED",
    decision:
      "POST_REGISTRATION_RECEIPT_V5_ISSUANCE_PREREGISTERED_ANTI_REPLAY_REGISTRY_WITNESS_AND_RECEIPT_UNBOUND",
    source: {
      registration_v7_schema_version: REGISTRATION_V7_SCHEMA_VERSION,
      registration_v7_static_fingerprint: REGISTRATION_V7_STATIC_FINGERPRINT,
      registration_v7_hash: source.registration_v7_hash,
      registration_v7_implementation_sha256: REGISTRATION_V7_IMPLEMENTATION_SHA256,
      execution_evidence_v4_schema_version: EVIDENCE_V4_SCHEMA_VERSION,
      execution_evidence_v4_hash: source.execution_evidence_v4_hash,
      execution_evidence_v4_implementation_sha256: EVIDENCE_V4_IMPLEMENTATION_SHA256,
      pre_registration_receipt_v4_hash: source.pre_registration_receipt_v4_hash,
      projection_v6_hash: source.projection_v6_hash,
      execution_preregistration_v1_hash: source.execution_preregistration_v1_hash,
      strict_canonical_python_sha256:
        "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412",
      execution_semantic_state: source.execution_semantic_state,
      registration_document_embedded: false,
      execution_evidence_document_embedded: false,
      receipt_document_embedded: false,
      projection_document_embedded: false,
      execution_preregistration_document_embedded: false,
    },
    issuance: {
      issuance_id: issuance.issuance_id,
      issuance_sequence: 1,
      target_receipt_schema_version: TARGET_RECEIPT_SCHEMA_VERSION,
      target_receipt_static_fingerprint: TARGET_RECEIPT_STATIC_FINGERPRINT,
      target_witness_policy_schema_version: POLICY_SCHEMA_VERSION,
      target_challenge_schema_version: CHALLENGE_SCHEMA_VERSION,
      target_attestation_schema_version: ATTESTATION_SCHEMA_VERSION,
      target_witness_verification_schema_version: VERIFICATION_SCHEMA_VERSION,
      target_anti_replay_consumption_schema_version:
        TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
      registration_hash: source.registration_v7_hash,
      execution_evidence_hash: source.execution_evidence_v4_hash,
      pre_registration_receipt_hash: source.pre_registration_receipt_v4_hash,
      post_registration_receipt_hash: null,
    },
    anti_replay: {
      scope_schema_version: ANTI_REPLAY_SCOPE_SCHEMA_VERSION,
      namespace: ANTI_REPLAY_NAMESPACE,
      scope_hash: expectedScopeHash,
      nonce_commitment_sha256: antiReplay.nonce_commitment_sha256,
      replay_key_fields: [
        "namespace",
        "registration_hash",
        "issuance_id",
        "nonce_commitment_sha256",
      ],
      registry_consistency_required: "LINEARIZABLE",
      required_registry_operation: "ATOMIC_PUT_IF_ABSENT_THEN_CONSUME_ONCE",
      challenge_use_limit: 1,
      receipt_issue_limit: 1,
      nonce_material_embedded: false,
      external_registry_snapshot_hash: null,
      nonce_consumption_receipt_hash: null,
      registry_bound: false,
      atomic_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_time_source_bound: false,
    },
    checks: checks(PREREGISTRATION_CHECK_NAMES),
    closed_local_blockers: [...PREREGISTRATION_CLOSED],
    blockers: [...PREREGISTRATION_BLOCKERS],
    activation_order: [...PREREGISTRATION_ACTIVATION_ORDER],
    facts: {
      issuance_preregistration_built: true,
      local_preregistration_complete: true,
      registration_v7_bound: true,
      pre_registration_receipt_preserved: true,
      post_registration_receipt_issued: false,
      witness_policy_v2_implemented: false,
      raw_nonce_received: false,
      nonce_entropy_verified: false,
      nonce_material_embedded: false,
      external_anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_timestamp_verified: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      browser_visual_review_performed: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      runtime_consumer_bound: false,
      ui_mounted: false,
      profitability_proven: false,
    },
    authority: { ...UNDERLYING_AUTHORITY },
  };
  return canonical.sealDocument(expected, "preregistration_hash");
}

function preregistrationExact(document) {
  const expected = expectedPreregistration(document);
  return Boolean(
    expected &&
      sealedExact(document, "preregistration_hash") &&
      exactJson(document, expected),
  );
}

function expectedEnvelope(preregistration) {
  if (!preregistrationExact(preregistration)) {
    return null;
  }
  const source = preregistration.source;
  const issuance = preregistration.issuance;
  const antiReplay = preregistration.anti_replay;
  const expected = {
    schema_version: ENVELOPE_SCHEMA_VERSION,
    static_fingerprint: ENVELOPE_STATIC_FINGERPRINT,
    status: "PASS",
    decision:
      "BLOCKED_ISSUANCE_PREREGISTRATION_V1_EXACTLY_VERIFIED_FOR_CROSS_RUNTIME_WITNESS_CONSUMER",
    source: {
      issuance_preregistration_schema_version: PREREGISTRATION_SCHEMA_VERSION,
      issuance_preregistration_static_fingerprint:
        PREREGISTRATION_STATIC_FINGERPRINT,
      issuance_preregistration_hash: preregistration.preregistration_hash,
      issuance_preregistration_implementation_sha256:
        PREREGISTRATION_IMPLEMENTATION_SHA256,
      registration_v7_hash: source.registration_v7_hash,
      execution_evidence_v4_hash: source.execution_evidence_v4_hash,
      pre_registration_receipt_v4_hash: source.pre_registration_receipt_v4_hash,
      projection_v6_hash: source.projection_v6_hash,
      execution_preregistration_v1_hash: source.execution_preregistration_v1_hash,
      execution_semantic_state: source.execution_semantic_state,
      issuance_id: issuance.issuance_id,
      nonce_commitment_sha256: antiReplay.nonce_commitment_sha256,
      anti_replay_scope_hash: antiReplay.scope_hash,
      verification_environment: "PYTHON_CONTRACT_PROCESS",
    },
    target_contracts: {
      receipt_schema_version: TARGET_RECEIPT_SCHEMA_VERSION,
      receipt_static_fingerprint: TARGET_RECEIPT_STATIC_FINGERPRINT,
      witness_policy_schema_version: POLICY_SCHEMA_VERSION,
      challenge_schema_version: CHALLENGE_SCHEMA_VERSION,
      attestation_schema_version: ATTESTATION_SCHEMA_VERSION,
      witness_verification_schema_version: VERIFICATION_SCHEMA_VERSION,
      anti_replay_consumption_schema_version:
        TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
    },
    verification: {
      underlying_public_verifier_status: "PASS",
      underlying_preregistration_status: "BLOCKED",
      underlying_local_preregistration_complete: true,
      preregistration_seal_exact: true,
      hash_edges_exact: true,
      issuance_scope_exact: true,
      target_schemas_exact: true,
      anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      post_registration_receipt_issued: false,
      stage_order: [...STAGE_ORDER],
    },
    checks: checks(ENVELOPE_CHECK_NAMES),
    blockers: [],
    facts: {
      local_python_verification_execution_observed: true,
      underlying_preregistration_remains_blocked: true,
      cross_runtime_summary_envelope_built: true,
      node_process_executed: false,
      signature_verified: false,
      raw_nonce_received: false,
      nonce_material_embedded: false,
      anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_timestamp_verified: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      preregistration_document_embedded: false,
      registration_document_embedded: false,
      execution_evidence_document_embedded: false,
      receipt_document_embedded: false,
      projection_document_embedded: false,
      execution_preregistration_document_embedded: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      browser_visual_review_performed: false,
      runtime_consumer_bound: false,
      ui_mounted: false,
      profitability_proven: false,
    },
    authority: { ...ENVELOPE_AUTHORITY },
  };
  return canonical.sealDocument(expected, "envelope_hash");
}

function envelopeExact(envelope, preregistration) {
  const expected = expectedEnvelope(preregistration);
  return Boolean(
    expected &&
      sealedExact(envelope, "envelope_hash") &&
      exactJson(envelope, expected),
  );
}

function bridgeExact(preregistration, envelope) {
  return preregistrationExact(preregistration) && envelopeExact(envelope, preregistration);
}

function buildPostRegistrationExecutionWitnessPolicyV2(
  preregistration,
  envelope,
  witness,
) {
  const bridge = bridgeExact(preregistration, envelope);
  const witnessIdExact = isRecord(witness) && isWitnessId(witness.witness_id);
  const publicKeyHashExact =
    isRecord(witness) && isHash(witness.public_key_spki_sha256);
  const policyNonceExact =
    isRecord(witness) && isPrintableToken(witness.policy_nonce, 32, 128);
  const localPolicyComplete = Boolean(
    bridge && witnessIdExact && publicKeyHashExact && policyNonceExact,
  );
  const localChecks = [
    { name: "issuance_preregistration_v1_exact", ok: preregistrationExact(preregistration), blocking: true },
    { name: "python_verification_envelope_v1_exact", ok: envelopeExact(envelope, preregistration), blocking: true },
    { name: "witness_id_format_exact", ok: witnessIdExact, blocking: true },
    { name: "ed25519_public_key_spki_hash_shape_exact", ok: publicKeyHashExact, blocking: true },
    { name: "policy_nonce_format_exact", ok: policyNonceExact, blocking: true },
    { name: "anti_replay_registry_not_claimed", ok: bridge, blocking: true },
  ];
  const localBlockers = localChecks.filter((check) => check.ok !== true).map((check) => `LOCAL_POLICY_CHECK_FAILED:${check.name}`);
  const source = bridge ? envelope.source : {};
  const document = {
    schema_version: POLICY_SCHEMA_VERSION,
    static_fingerprint: POLICY_STATIC_FINGERPRINT,
    status: "BLOCKED",
    decision: localPolicyComplete
      ? "ED25519_KEY_HASH_PREREGISTERED_FOR_POST_REGISTRATION_CHALLENGE_ANTI_REPLAY_AND_IDENTITY_UNBOUND"
      : "POST_REGISTRATION_WITNESS_POLICY_V2_LOCAL_BINDING_BLOCKED",
    source: {
      issuance_preregistration_hash: bridge ? preregistration.preregistration_hash : null,
      issuance_preregistration_implementation_sha256:
        PREREGISTRATION_IMPLEMENTATION_SHA256,
      verification_envelope_hash: bridge ? envelope.envelope_hash : null,
      verification_envelope_implementation_sha256:
        ENVELOPE_IMPLEMENTATION_SHA256,
      registration_v7_hash: bridge ? source.registration_v7_hash : null,
      execution_evidence_v4_hash: bridge ? source.execution_evidence_v4_hash : null,
      pre_registration_receipt_v4_hash: bridge
        ? source.pre_registration_receipt_v4_hash
        : null,
      anti_replay_scope_hash: bridge ? source.anti_replay_scope_hash : null,
      execution_semantic_state: bridge
        ? source.execution_semantic_state
        : "UNVERIFIED",
      strict_canonical_implementation_sha256:
        STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    },
    scope: {
      issuance_id: bridge ? source.issuance_id : "UNKNOWN",
      nonce_commitment_sha256: bridge
        ? source.nonce_commitment_sha256
        : null,
      anti_replay_namespace: ANTI_REPLAY_NAMESPACE,
      target_receipt_schema_version: TARGET_RECEIPT_SCHEMA_VERSION,
      challenge_schema_version: CHALLENGE_SCHEMA_VERSION,
      attestation_schema_version: ATTESTATION_SCHEMA_VERSION,
      verification_schema_version: VERIFICATION_SCHEMA_VERSION,
      anti_replay_consumption_schema_version:
        TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
      detached_signature_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
    },
    witness: {
      witness_id: witnessIdExact ? witness.witness_id : "UNKNOWN",
      key_algorithm: "Ed25519",
      public_key_spki_sha256: publicKeyHashExact
        ? witness.public_key_spki_sha256
        : null,
      policy_nonce: policyNonceExact ? witness.policy_nonce : "UNKNOWN",
    },
    checks: localChecks,
    blockers: [...localBlockers, ...WITNESS_BLOCKERS],
    facts: {
      policy_candidate_built: true,
      local_policy_complete: localPolicyComplete,
      public_key_hash_preregistered_locally: publicKeyHashExact,
      public_key_material_received: false,
      public_key_material_embedded: false,
      private_key_material_received: false,
      raw_nonce_received: false,
      cryptographic_key_possession_verified: false,
      signature_verified: false,
      anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_timestamp_verified: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      post_registration_receipt_issued: false,
      browser_visual_review_performed: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      runtime_consumer_bound: false,
      profitability_proven: false,
    },
    authority: { ...WITNESS_AUTHORITY },
  };
  return canonical.sealDocument(document, "policy_hash");
}

function policyExact(policy, preregistration, envelope) {
  if (!isRecord(policy) || !isRecord(policy.witness)) {
    return false;
  }
  const expected = buildPostRegistrationExecutionWitnessPolicyV2(
    preregistration,
    envelope,
    {
      witness_id: policy.witness.witness_id,
      public_key_spki_sha256: policy.witness.public_key_spki_sha256,
      policy_nonce: policy.witness.policy_nonce,
    },
  );
  return Boolean(
    policy.facts &&
      policy.facts.local_policy_complete === true &&
      sealedExact(policy, "policy_hash") &&
      exactJson(policy, expected),
  );
}

function buildPostRegistrationDocumentBundleChallengeV2(
  preregistration,
  envelope,
  policy,
  rawNonce,
) {
  const bridge = bridgeExact(preregistration, envelope);
  const policyIsExact = policyExact(policy, preregistration, envelope);
  const rawNonceValid = isPrintableToken(rawNonce, 32, 256);
  const nonceHash = rawNonceValid ? sha256Utf8(rawNonce) : null;
  const nonceMatches = Boolean(
    bridge &&
      rawNonceValid &&
      nonceHash === preregistration.anti_replay.nonce_commitment_sha256,
  );
  const localChallengeComplete = Boolean(
    bridge && policyIsExact && nonceMatches,
  );
  const challengeIdentity = localChallengeComplete
    ? canonical.strictCanonicalHash({
        schema_version:
          "portfolio-risk-post-registration-document-bundle-challenge-identity-v1",
        issuance_preregistration_hash: preregistration.preregistration_hash,
        verification_envelope_hash: envelope.envelope_hash,
        policy_hash: policy.policy_hash,
        anti_replay_scope_hash: envelope.source.anti_replay_scope_hash,
        nonce_commitment_sha256: nonceHash,
        witness_id: policy.witness.witness_id,
      })
    : null;
  const localChecks = [
    { name: "issuance_preregistration_v1_exact", ok: preregistrationExact(preregistration), blocking: true },
    { name: "python_verification_envelope_v1_exact", ok: envelopeExact(envelope, preregistration), blocking: true },
    { name: "witness_policy_v2_exact", ok: policyIsExact, blocking: true },
    { name: "raw_nonce_format_exact", ok: rawNonceValid, blocking: true },
    { name: "raw_nonce_matches_preregistered_commitment", ok: nonceMatches, blocking: true },
    { name: "anti_replay_scope_hash_bound", ok: bridge, blocking: true },
  ];
  const localBlockers = localChecks.filter((check) => check.ok !== true).map((check) => `LOCAL_CHALLENGE_CHECK_FAILED:${check.name}`);
  const document = {
    schema_version: CHALLENGE_SCHEMA_VERSION,
    static_fingerprint: CHALLENGE_STATIC_FINGERPRINT,
    status: "BLOCKED",
    decision: localChallengeComplete
      ? "POST_REGISTRATION_DOCUMENT_BUNDLE_CHALLENGE_BUILT_NONCE_UNCONSUMED_AUTHORITY_UNCHANGED"
      : "POST_REGISTRATION_DOCUMENT_BUNDLE_CHALLENGE_LOCAL_BINDING_BLOCKED",
    source: {
      issuance_preregistration_hash: bridge ? preregistration.preregistration_hash : null,
      verification_envelope_hash: bridge ? envelope.envelope_hash : null,
      policy_hash: policyIsExact ? policy.policy_hash : null,
      registration_v7_hash: bridge ? envelope.source.registration_v7_hash : null,
      execution_evidence_v4_hash: bridge
        ? envelope.source.execution_evidence_v4_hash
        : null,
      pre_registration_receipt_v4_hash: bridge
        ? envelope.source.pre_registration_receipt_v4_hash
        : null,
      anti_replay_scope_hash: bridge
        ? envelope.source.anti_replay_scope_hash
        : null,
      nonce_commitment_sha256: nonceMatches ? nonceHash : null,
      strict_canonical_implementation_sha256:
        STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    },
    challenge: {
      challenge_identity_hash: challengeIdentity,
      signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
      witness_id: policyIsExact ? policy.witness.witness_id : "UNKNOWN",
      public_key_spki_sha256: policyIsExact
        ? policy.witness.public_key_spki_sha256
        : null,
      nonce_preimage_verified: nonceMatches,
      raw_nonce_embedded: false,
    },
    checks: localChecks,
    blockers: [...localBlockers, ...WITNESS_BLOCKERS],
    facts: {
      challenge_candidate_built: true,
      local_challenge_complete: localChallengeComplete,
      raw_nonce_received: rawNonceValid,
      raw_nonce_preimage_verified: nonceMatches,
      raw_nonce_embedded: false,
      signature_present: false,
      signature_verified: false,
      anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_timestamp_verified: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      post_registration_receipt_issued: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      profitability_proven: false,
    },
    authority: { ...WITNESS_AUTHORITY },
  };
  return canonical.sealDocument(document, "challenge_hash");
}

function challengeExact(challenge, preregistration, envelope, policy, rawNonce) {
  const expected = buildPostRegistrationDocumentBundleChallengeV2(
    preregistration,
    envelope,
    policy,
    rawNonce,
  );
  return Boolean(
    isRecord(challenge) &&
      challenge.facts &&
      challenge.facts.local_challenge_complete === true &&
      sealedExact(challenge, "challenge_hash") &&
      exactJson(challenge, expected),
  );
}

function publicKeyInfo(publicKeyMaterial) {
  try {
    const key =
      publicKeyMaterial instanceof crypto.KeyObject
        ? publicKeyMaterial
        : crypto.createPublicKey(publicKeyMaterial);
    if (key.type !== "public" || key.asymmetricKeyType !== "ed25519") {
      return null;
    }
    const der = key.export({ type: "spki", format: "der" });
    return {
      key,
      sha256: crypto.createHash("sha256").update(der).digest("hex"),
    };
  } catch (_error) {
    return null;
  }
}

function signatureBuffer(signatureBase64) {
  if (typeof signatureBase64 !== "string") {
    return null;
  }
  try {
    const value = Buffer.from(signatureBase64, "base64");
    return value.length === 64 && value.toString("base64") === signatureBase64
      ? value
      : null;
  } catch (_error) {
    return null;
  }
}

function attestationExact(attestation, policy, challenge) {
  if (!isRecord(attestation) || !isRecord(policy) || !isRecord(challenge)) {
    return false;
  }
  const signature = signatureBuffer(attestation.signature_base64);
  if (!signature) {
    return false;
  }
  const expected = canonical.sealDocument(
    {
      schema_version: ATTESTATION_SCHEMA_VERSION,
      static_fingerprint: ATTESTATION_STATIC_FINGERPRINT,
      policy_hash: policy.policy_hash,
      challenge_hash: challenge.challenge_hash,
      witness_id: policy.witness.witness_id,
      key_algorithm: "Ed25519",
      public_key_spki_sha256: policy.witness.public_key_spki_sha256,
      signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
      signature_base64: attestation.signature_base64,
    },
    "attestation_hash",
  );
  return sealedExact(attestation, "attestation_hash") && exactJson(attestation, expected);
}

function verifyPostRegistrationWitnessSignatureCandidateV2(
  preregistration,
  envelope,
  policy,
  challenge,
  attestation,
  publicKeyMaterial,
  rawNonce,
  antiReplayConsumptionReceipt = null,
) {
  const preregistrationIsExact = preregistrationExact(preregistration);
  const envelopeIsExact = envelopeExact(envelope, preregistration);
  const policyIsExact = policyExact(policy, preregistration, envelope);
  const challengeIsExact = challengeExact(
    challenge,
    preregistration,
    envelope,
    policy,
    rawNonce,
  );
  const attestationIsExact = attestationExact(attestation, policy, challenge);
  const keyInfo = publicKeyInfo(publicKeyMaterial);
  const publicKeyHashMatches = Boolean(
    keyInfo &&
      policyIsExact &&
      keyInfo.sha256 === policy.witness.public_key_spki_sha256,
  );
  let signatureVerified = false;
  const signature = isRecord(attestation)
    ? signatureBuffer(attestation.signature_base64)
    : null;
  if (
    keyInfo &&
    signature &&
    publicKeyHashMatches &&
    challengeIsExact &&
    attestationIsExact
  ) {
    try {
      signatureVerified = crypto.verify(
        null,
        Buffer.from(canonical.strictCanonicalStringify(challenge), "utf8"),
        keyInfo.key,
        signature,
      );
    } catch (_error) {
      signatureVerified = false;
    }
  }
  const consumptionNotClaimed = antiReplayConsumptionReceipt === null;
  const localChecks = [
    { name: "issuance_preregistration_v1_exact", ok: preregistrationIsExact, blocking: true },
    { name: "python_verification_envelope_v1_exact", ok: envelopeIsExact, blocking: true },
    { name: "witness_policy_v2_exact", ok: policyIsExact, blocking: true },
    { name: "document_bundle_challenge_v2_exact", ok: challengeIsExact, blocking: true },
    { name: "detached_attestation_v2_exact", ok: attestationIsExact, blocking: true },
    { name: "ed25519_public_key_hash_matches_policy", ok: publicKeyHashMatches, blocking: true },
    { name: "ed25519_detached_signature_verified", ok: signatureVerified, blocking: true },
    { name: "anti_replay_consumption_not_claimed_before_implementation", ok: consumptionNotClaimed, blocking: true },
  ];
  const localBlockers = localChecks.filter((check) => check.ok !== true).map((check) => `LOCAL_SIGNATURE_CHECK_FAILED:${check.name}`);
  const localSignatureComplete = localBlockers.length === 0;
  const document = {
    schema_version: VERIFICATION_SCHEMA_VERSION,
    static_fingerprint: VERIFICATION_STATIC_FINGERPRINT,
    status: "BLOCKED",
    local_signature_status: localSignatureComplete ? "PASS" : "BLOCK",
    decision: localSignatureComplete
      ? "PREREGISTERED_ED25519_KEY_POSSESSION_VERIFIED_ANTI_REPLAY_IDENTITY_AND_RECEIPT_UNBOUND"
      : "POST_REGISTRATION_ED25519_KEY_POSSESSION_LOCAL_VERIFICATION_BLOCKED",
    source: {
      issuance_preregistration_hash: preregistrationIsExact
        ? preregistration.preregistration_hash
        : null,
      verification_envelope_hash: envelopeIsExact ? envelope.envelope_hash : null,
      policy_hash: policyIsExact ? policy.policy_hash : null,
      challenge_hash: challengeIsExact ? challenge.challenge_hash : null,
      attestation_hash: attestationIsExact ? attestation.attestation_hash : null,
      registration_v7_hash: envelopeIsExact
        ? envelope.source.registration_v7_hash
        : null,
      execution_evidence_v4_hash: envelopeIsExact
        ? envelope.source.execution_evidence_v4_hash
        : null,
      anti_replay_scope_hash: envelopeIsExact
        ? envelope.source.anti_replay_scope_hash
        : null,
      witness_id: policyIsExact ? policy.witness.witness_id : "UNKNOWN",
      key_algorithm: "Ed25519",
      public_key_spki_sha256: publicKeyHashMatches ? keyInfo.sha256 : null,
      public_key_material_embedded: false,
      signature_material_embedded: false,
      raw_nonce_embedded: false,
      signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
    },
    checks: localChecks,
    blockers: [...localBlockers, ...WITNESS_BLOCKERS],
    facts: {
      local_node_contract_execution_observed: true,
      local_signature_contract_complete: localSignatureComplete,
      cryptographic_key_possession_verified: signatureVerified,
      cryptographic_signature_verified: signatureVerified,
      preregistered_public_key_hash_matched: publicKeyHashMatches,
      public_key_material_received_by_verifier: Boolean(keyInfo),
      public_key_material_embedded: false,
      private_key_material_received: false,
      signature_material_received: Boolean(signature),
      signature_material_embedded: false,
      raw_nonce_received: isPrintableToken(rawNonce, 32, 256),
      raw_nonce_embedded: false,
      anti_replay_consumption_receipt_supported: false,
      anti_replay_consumption_receipt_present: !consumptionNotClaimed,
      anti_replay_registry_bound: false,
      atomic_nonce_consumption_verified: false,
      duplicate_rejection_verified: false,
      trusted_timestamp_verified: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      post_registration_receipt_issued: false,
      browser_visual_review_performed: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      runtime_consumer_bound: false,
      profitability_proven: false,
    },
    authority: { ...WITNESS_AUTHORITY },
  };
  return canonical.sealDocument(document, "verification_hash");
}

function verifyPostRegistrationWitnessVerificationDocumentV2(
  document,
  preregistration,
  envelope,
  policy,
  challenge,
  attestation,
  publicKeyMaterial,
  rawNonce,
  antiReplayConsumptionReceipt = null,
) {
  const expected = verifyPostRegistrationWitnessSignatureCandidateV2(
    preregistration,
    envelope,
    policy,
    challenge,
    attestation,
    publicKeyMaterial,
    rawNonce,
    antiReplayConsumptionReceipt,
  );
  const exact = Boolean(
    isRecord(document) &&
      sealedExact(document, "verification_hash") &&
      exactJson(document, expected) &&
      expected.local_signature_status === "PASS",
  );
  return {
    schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
    status: exact ? "PASS" : "BLOCK",
    verification_document_exactly_rebuilt: exact,
    verification_status: exact ? expected.status : "UNKNOWN",
    local_signature_status: exact
      ? expected.local_signature_status
      : "UNVERIFIED",
    verification_hash: exact ? expected.verification_hash : null,
    blockers: exact ? [] : ["witness_v2_verification_document_exact_rebuild"],
    anti_replay_registry_bound: false,
    atomic_nonce_consumption_verified: false,
    witness_organization_identity_verified: false,
    independent_execution_process_witnessed: false,
    post_registration_receipt_issued: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
  };
}

module.exports = Object.freeze({
  POLICY_SCHEMA_VERSION,
  POLICY_STATIC_FINGERPRINT,
  CHALLENGE_SCHEMA_VERSION,
  CHALLENGE_STATIC_FINGERPRINT,
  ATTESTATION_SCHEMA_VERSION,
  ATTESTATION_STATIC_FINGERPRINT,
  VERIFICATION_SCHEMA_VERSION,
  VERIFICATION_STATIC_FINGERPRINT,
  EXACT_VERIFICATION_SCHEMA_VERSION,
  PREREGISTRATION_SCHEMA_VERSION,
  PREREGISTRATION_STATIC_FINGERPRINT,
  ENVELOPE_SCHEMA_VERSION,
  ENVELOPE_STATIC_FINGERPRINT,
  PREREGISTRATION_IMPLEMENTATION_SHA256,
  ENVELOPE_IMPLEMENTATION_SHA256,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  TARGET_RECEIPT_SCHEMA_VERSION,
  TARGET_RECEIPT_STATIC_FINGERPRINT,
  TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION,
  ANTI_REPLAY_NAMESPACE,
  STAGE_ORDER,
  buildPostRegistrationExecutionWitnessPolicyV2,
  buildPostRegistrationDocumentBundleChallengeV2,
  verifyPostRegistrationWitnessSignatureCandidateV2,
  verifyPostRegistrationWitnessVerificationDocumentV2,
});
