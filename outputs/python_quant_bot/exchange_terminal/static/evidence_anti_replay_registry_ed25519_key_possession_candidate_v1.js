"use strict";

const crypto = require("node:crypto");
const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  strictCanonicalStringify,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");

const PREREGISTRATION_SCHEMA_VERSION =
  "anti-replay-registry-identity-preregistration-v1";
const PREREGISTRATION_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-identity-preregistration-v1-lock-1";
const POLICY_SCHEMA_VERSION =
  "anti-replay-registry-ed25519-key-possession-policy-v1";
const POLICY_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-ed25519-key-possession-policy-v1-lock-1";
const CHALLENGE_SCHEMA_VERSION =
  "anti-replay-registry-ed25519-key-possession-challenge-v1";
const CHALLENGE_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-ed25519-key-possession-challenge-v1-lock-1";
const ATTESTATION_SCHEMA_VERSION =
  "anti-replay-registry-ed25519-detached-attestation-v1";
const ATTESTATION_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-ed25519-detached-attestation-v1-lock-1";
const VERIFICATION_SCHEMA_VERSION =
  "anti-replay-registry-ed25519-key-possession-verification-candidate-v1";
const VERIFICATION_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-ed25519-key-possession-verification-v1-lock-1";
const EXACT_VERIFICATION_SCHEMA_VERSION =
  "anti-replay-registry-ed25519-key-possession-exact-rebuild-v1";

const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const PYTHON_PREREGISTRATION_IMPLEMENTATION_SHA256 =
  "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f";
const PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
const REFERENCE_MODEL_IMPLEMENTATION_SHA256 =
  "c56055d08b8ba6cc7f35437bbea7e042618b02e0d5ffed66e702f18103f8d587";

const ANTI_REPLAY_NAMESPACE =
  "portfolio-risk-downside-tail-post-registration-execution-receipt-v5";
const ADAPTER_PROTOCOL_VERSION = "anti-replay-compare-and-consume-port-v1";
const COMMAND_SCHEMA_VERSION = "anti-replay-compare-and-consume-command-v1";
const RESULT_SCHEMA_VERSION = "anti-replay-compare-and-consume-result-v1";
const CONSUMPTION_REQUEST_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-consumption-request-v1";
const TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION =
  "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1";
const TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION =
  "portfolio-risk-downside-tail-consumer-post-registration-execution-receipt-v5";
const SIGNED_PAYLOAD =
  "STRICT_CANONICAL_REGISTRY_KEY_POSSESSION_CHALLENGE";

const HASH_PATTERN = /^[0-9a-f]{64}$/;
const IDENTIFIER_PATTERN = /^[a-z0-9][a-z0-9._:-]{2,127}$/;
const AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "post_registration_receipt_issuance_allowed",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
]);
const PREREGISTRATION_BLOCKERS = Object.freeze([
  "REGISTRY_KEY_POSSESSION_UNVERIFIED",
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
  "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
  "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
  "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
  "TRUSTED_REGISTRY_TIME_UNVERIFIED",
  "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
]);
const REMAINING_BLOCKERS = Object.freeze([
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
  "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
  "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
  "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
  "TRUSTED_REGISTRY_TIME_UNVERIFIED",
  "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
]);
const REQUIRED_CAPABILITIES = Object.freeze([
  "ATOMIC_COMPARE_AND_CONSUME",
  "EXACT_DUPLICATE_REJECTION",
  "SAME_SCOPE_CONFLICT_REJECTION",
  "DURABLE_RESTART_RECOVERY",
  "ROLLBACK_RESISTANCE",
  "TIMEOUT_AFTER_COMMIT_IDEMPOTENCY",
  "SIGNED_RECEIPT_V1",
  "PREREGISTERED_ED25519_REGISTRY_KEY",
  "TRUSTED_MONOTONIC_REGISTRY_TIME",
  "INDEPENDENT_CONFORMANCE_OBSERVER",
]);

function hasExactKeys(value, keys) {
  return (
    isPlainRecord(value) &&
    Object.keys(value).sort().join("\n") === [...keys].sort().join("\n")
  );
}

function sameArray(value, expected) {
  return (
    Array.isArray(value) &&
    value.length === expected.length &&
    value.every((item, index) => item === expected[index])
  );
}

function isHash(value) {
  return typeof value === "string" && HASH_PATTERN.test(value);
}

function sha256BufferHex(value) {
  if (!Buffer.isBuffer(value)) {
    throw new TypeError("sha256 binary input must be a Buffer");
  }
  return crypto.createHash("sha256").update(value).digest("hex");
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

function expectedPreregistrationFacts() {
  return {
    adapter_conformance_verified: false,
    durable_atomic_compare_and_consume_verified: false,
    external_endpoint_verified: false,
    external_linearizability_verified: false,
    local_preregistration_complete: true,
    network_accessed: false,
    post_registration_receipt_issued: false,
    registry_key_possession_verified: false,
    registry_organization_identity_verified: false,
    registry_public_key_hash_preregistered: true,
    runtime_assets_accessed: false,
    signed_target_consumption_receipt_verified: false,
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
  };
}

function isExactPreregistration(value) {
  const facts = expectedPreregistrationFacts();
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "checks",
      "decision",
      "facts",
      "identity",
      "preregistration_hash",
      "requirements",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
    ]) ||
    !verifySealedDocument(value, "preregistration_hash") ||
    value.schema_version !== PREREGISTRATION_SCHEMA_VERSION ||
    value.static_fingerprint !== PREREGISTRATION_STATIC_FINGERPRINT ||
    value.status !== "BLOCKED" ||
    value.decision !==
      "REGISTRY_IDENTITY_PREREGISTERED_KEY_POSSESSION_IDENTITY_AND_EXTERNAL_CONFORMANCE_UNVERIFIED" ||
    !isLockedAuthority(value.authority) ||
    !sameArray(value.blockers, PREREGISTRATION_BLOCKERS) ||
    !sameArray(value.requirements, REQUIRED_CAPABILITIES) ||
    !hasExactKeys(value.facts, Object.keys(facts)) ||
    !Object.keys(facts).every((key) => value.facts[key] === facts[key]) ||
    !hasExactKeys(value.identity, [
      "key_algorithm",
      "operator_identity_claim",
      "public_key_spki_sha256",
      "registry_id",
      "trust_domain",
    ]) ||
    !hasExactKeys(value.source, [
      "adapter_protocol_version",
      "anti_replay_namespace",
      "command_schema_version",
      "consumption_request_schema_version",
      "reference_model_implementation_sha256",
      "result_schema_version",
      "strict_canonical_implementation_sha256",
      "target_consumption_receipt_schema_version",
      "target_post_registration_receipt_schema_version",
    ])
  ) {
    return false;
  }
  const expectedChecks = [
    "registry_identity_fields_preregistered",
    "registry_ed25519_public_key_hash_preregistered",
    "adapter_protocol_and_target_schemas_exact",
    "external_identity_and_conformance_not_self_claimed",
  ];
  return (
    Array.isArray(value.checks) &&
    value.checks.length === expectedChecks.length &&
    value.checks.every(
      (check, index) =>
        hasExactKeys(check, ["blocking", "name", "ok"]) &&
        check.name === expectedChecks[index] &&
        check.blocking === true &&
        check.ok === true
    ) &&
    value.identity.key_algorithm === "Ed25519" &&
    isHash(value.identity.public_key_spki_sha256) &&
    typeof value.identity.operator_identity_claim === "string" &&
    value.identity.operator_identity_claim.length > 0 &&
    value.identity.operator_identity_claim.length <= 256 &&
    IDENTIFIER_PATTERN.test(value.identity.registry_id) &&
    IDENTIFIER_PATTERN.test(value.identity.trust_domain) &&
    value.source.adapter_protocol_version === ADAPTER_PROTOCOL_VERSION &&
    value.source.anti_replay_namespace === ANTI_REPLAY_NAMESPACE &&
    value.source.command_schema_version === COMMAND_SCHEMA_VERSION &&
    value.source.consumption_request_schema_version ===
      CONSUMPTION_REQUEST_SCHEMA_VERSION &&
    value.source.reference_model_implementation_sha256 ===
      REFERENCE_MODEL_IMPLEMENTATION_SHA256 &&
    value.source.result_schema_version === RESULT_SCHEMA_VERSION &&
    value.source.strict_canonical_implementation_sha256 ===
      PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256 &&
    value.source.target_consumption_receipt_schema_version ===
      TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION &&
    value.source.target_post_registration_receipt_schema_version ===
      TARGET_POST_REGISTRATION_RECEIPT_SCHEMA_VERSION
  );
}

function policyFacts() {
  return {
    adapter_conformance_verified: false,
    external_linearizability_verified: false,
    key_possession_challenge_complete: false,
    local_policy_complete: true,
    network_accessed: false,
    post_registration_receipt_issued: false,
    registry_key_possession_verified: false,
    registry_organization_identity_verified: false,
    registry_public_key_hash_preregistered: true,
    runtime_assets_accessed: false,
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
  };
}

function buildAntiReplayRegistryKeyPossessionPolicyV1(preregistration) {
  if (!isExactPreregistration(preregistration)) {
    throw new TypeError("registry identity preregistration-v1 is not exact");
  }
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: ["REGISTRY_KEY_POSSESSION_CHALLENGE_UNVERIFIED", ...REMAINING_BLOCKERS],
      decision:
        "REGISTRY_KEY_HASH_BOUND_LOCAL_CHALLENGE_AND_EXTERNAL_IDENTITY_UNVERIFIED",
      facts: policyFacts(),
      schema_version: POLICY_SCHEMA_VERSION,
      source: {
        adapter_protocol_version: ADAPTER_PROTOCOL_VERSION,
        anti_replay_namespace: ANTI_REPLAY_NAMESPACE,
        operator_identity_claim_hash: strictCanonicalHash(
          preregistration.identity.operator_identity_claim
        ),
        preregistration_hash: preregistration.preregistration_hash,
        public_key_spki_sha256:
          preregistration.identity.public_key_spki_sha256,
        registry_id: preregistration.identity.registry_id,
        target_consumption_receipt_schema_version:
          TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION,
        trust_domain: preregistration.identity.trust_domain,
      },
      static_fingerprint: POLICY_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "policy_hash"
  );
}

function isPolicyDocument(value) {
  return (
    hasExactKeys(value, [
      "authority",
      "blockers",
      "decision",
      "facts",
      "policy_hash",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
    ]) &&
    verifySealedDocument(value, "policy_hash") &&
    value.schema_version === POLICY_SCHEMA_VERSION &&
    value.static_fingerprint === POLICY_STATIC_FINGERPRINT &&
    value.status === "BLOCKED" &&
    isLockedAuthority(value.authority) &&
    hasExactKeys(value.facts, Object.keys(policyFacts())) &&
    Object.keys(policyFacts()).every(
      (key) => value.facts[key] === policyFacts()[key]
    ) &&
    hasExactKeys(value.source, [
      "adapter_protocol_version",
      "anti_replay_namespace",
      "operator_identity_claim_hash",
      "preregistration_hash",
      "public_key_spki_sha256",
      "registry_id",
      "target_consumption_receipt_schema_version",
      "trust_domain",
    ]) &&
    [
      value.source.operator_identity_claim_hash,
      value.source.preregistration_hash,
      value.source.public_key_spki_sha256,
    ].every(isHash)
  );
}

function rawNonceBuffer(value) {
  if (!Buffer.isBuffer(value) || value.length !== 32) {
    throw new TypeError("registry key-possession raw nonce must be 32 bytes");
  }
  return value;
}

function buildAntiReplayRegistryKeyPossessionChallengeV1(policy, rawNonce) {
  if (!isPolicyDocument(policy)) {
    throw new TypeError("registry key-possession policy-v1 is not exact");
  }
  rawNonce = rawNonceBuffer(rawNonce);
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: ["REGISTRY_KEY_POSSESSION_SIGNATURE_UNVERIFIED", ...REMAINING_BLOCKERS],
      decision:
        "DETACHED_REGISTRY_KEY_POSSESSION_SIGNATURE_REQUIRED_EXTERNAL_IDENTITY_UNVERIFIED",
      facts: {
        network_accessed: false,
        public_key_material_embedded: false,
        raw_nonce_embedded: false,
        raw_nonce_received: true,
        registry_key_possession_verified: false,
        runtime_assets_accessed: false,
        signature_material_embedded: false,
        signature_material_received: false,
      },
      schema_version: CHALLENGE_SCHEMA_VERSION,
      source: {
        nonce_commitment_sha256: sha256BufferHex(rawNonce),
        policy_hash: policy.policy_hash,
        preregistration_hash: policy.source.preregistration_hash,
        registry_id: policy.source.registry_id,
        signed_payload: SIGNED_PAYLOAD,
      },
      static_fingerprint: CHALLENGE_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "challenge_hash"
  );
}

function isChallengeDocument(value) {
  return (
    hasExactKeys(value, [
      "authority",
      "blockers",
      "challenge_hash",
      "decision",
      "facts",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
    ]) &&
    verifySealedDocument(value, "challenge_hash") &&
    value.schema_version === CHALLENGE_SCHEMA_VERSION &&
    value.static_fingerprint === CHALLENGE_STATIC_FINGERPRINT &&
    value.status === "BLOCKED" &&
    isLockedAuthority(value.authority) &&
    hasExactKeys(value.source, [
      "nonce_commitment_sha256",
      "policy_hash",
      "preregistration_hash",
      "registry_id",
      "signed_payload",
    ]) &&
    [
      value.source.nonce_commitment_sha256,
      value.source.policy_hash,
      value.source.preregistration_hash,
    ].every(isHash) &&
    value.source.signed_payload === SIGNED_PAYLOAD
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
    const spki = key.export({ type: "spki", format: "der" });
    return { key, spkiSha256: sha256BufferHex(spki) };
  } catch (_error) {
    return null;
  }
}

function signatureBuffer(value) {
  const signature = Buffer.isBuffer(value)
    ? value
    : value instanceof Uint8Array
      ? Buffer.from(value)
      : null;
  return signature && signature.length === 64 ? signature : null;
}

function buildAntiReplayRegistryDetachedAttestationV1(
  preregistration,
  policy,
  challenge,
  publicKeyMaterial,
  detachedSignature
) {
  if (
    !isExactPreregistration(preregistration) ||
    !isPolicyDocument(policy) ||
    !isChallengeDocument(challenge)
  ) {
    throw new TypeError("registry key-possession attestation source is invalid");
  }
  const keyInfo = publicKeyInfo(publicKeyMaterial);
  const signature = signatureBuffer(detachedSignature);
  if (!keyInfo || !signature) {
    throw new TypeError("registry key-possession public key or signature is invalid");
  }
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...REMAINING_BLOCKERS],
      facts: {
        private_key_material_received: false,
        public_key_material_embedded: false,
        public_key_material_received: true,
        raw_nonce_embedded: false,
        signature_material_embedded: false,
        signature_material_received: true,
      },
      schema_version: ATTESTATION_SCHEMA_VERSION,
      source: {
        challenge_hash: challenge.challenge_hash,
        policy_hash: policy.policy_hash,
        preregistration_hash: preregistration.preregistration_hash,
        public_key_spki_sha256: keyInfo.spkiSha256,
        registry_id: preregistration.identity.registry_id,
        signature_sha256: sha256BufferHex(signature),
        signed_payload: SIGNED_PAYLOAD,
      },
      static_fingerprint: ATTESTATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "attestation_hash"
  );
}

function isAttestationDocument(value) {
  return (
    hasExactKeys(value, [
      "attestation_hash",
      "authority",
      "blockers",
      "facts",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
    ]) &&
    verifySealedDocument(value, "attestation_hash") &&
    value.schema_version === ATTESTATION_SCHEMA_VERSION &&
    value.static_fingerprint === ATTESTATION_STATIC_FINGERPRINT &&
    value.status === "BLOCKED" &&
    isLockedAuthority(value.authority) &&
    hasExactKeys(value.source, [
      "challenge_hash",
      "policy_hash",
      "preregistration_hash",
      "public_key_spki_sha256",
      "registry_id",
      "signature_sha256",
      "signed_payload",
    ]) &&
    [
      value.source.challenge_hash,
      value.source.policy_hash,
      value.source.preregistration_hash,
      value.source.public_key_spki_sha256,
      value.source.signature_sha256,
    ].every(isHash) &&
    value.source.signed_payload === SIGNED_PAYLOAD
  );
}

function verificationFacts(localPass) {
  return {
    adapter_conformance_verified: false,
    durable_atomic_compare_and_consume_verified: false,
    external_endpoint_verified: false,
    external_linearizability_verified: false,
    local_node_contract_execution_observed: true,
    local_registry_key_possession_contract_complete: true,
    network_accessed: false,
    post_registration_receipt_issued: false,
    private_key_material_received: false,
    preregistered_public_key_hash_matched: localPass,
    public_key_material_embedded: false,
    public_key_material_received: true,
    raw_nonce_embedded: false,
    raw_nonce_received: true,
    registry_key_possession_verified: localPass,
    registry_organization_identity_verified: false,
    runtime_assets_accessed: false,
    signature_material_embedded: false,
    signature_material_received: true,
    signed_target_consumption_receipt_verified: false,
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
  };
}

function verifyAntiReplayRegistryKeyPossessionCandidateV1(
  preregistration,
  policy,
  challenge,
  rawNonce,
  publicKeyMaterial,
  detachedSignature
) {
  if (!isExactPreregistration(preregistration)) {
    throw new TypeError("registry identity preregistration-v1 is not exact");
  }
  rawNonce = rawNonceBuffer(rawNonce);
  const expectedPolicy = buildAntiReplayRegistryKeyPossessionPolicyV1(
    preregistration
  );
  const policyExact =
    isPolicyDocument(policy) &&
    strictCanonicalHash(policy) === strictCanonicalHash(expectedPolicy);
  const expectedChallenge = buildAntiReplayRegistryKeyPossessionChallengeV1(
    expectedPolicy,
    rawNonce
  );
  const challengeExact =
    isChallengeDocument(challenge) &&
    strictCanonicalHash(challenge) === strictCanonicalHash(expectedChallenge);
  const keyInfo = publicKeyInfo(publicKeyMaterial);
  const signature = signatureBuffer(detachedSignature);
  if (!keyInfo || !signature || !isPolicyDocument(policy) || !isChallengeDocument(challenge)) {
    throw new TypeError("registry key-possession verification material is invalid");
  }
  const attestation = buildAntiReplayRegistryDetachedAttestationV1(
    preregistration,
    policy,
    challenge,
    keyInfo.key,
    signature
  );
  const keyHashMatches =
    keyInfo.spkiSha256 === preregistration.identity.public_key_spki_sha256;
  const signatureVerified = crypto.verify(
    null,
    Buffer.from(strictCanonicalStringify(challenge), "utf8"),
    keyInfo.key,
    signature
  );
  const checks = [
    { blocking: true, name: "registry_identity_preregistration_v1_exact", ok: true },
    { blocking: true, name: "registry_key_possession_policy_v1_exact", ok: policyExact },
    { blocking: true, name: "registry_key_possession_challenge_v1_exact", ok: challengeExact },
    { blocking: true, name: "registry_detached_attestation_v1_exact", ok: isAttestationDocument(attestation) },
    { blocking: true, name: "ed25519_public_key_hash_matches_preregistration", ok: keyHashMatches },
    { blocking: true, name: "ed25519_detached_signature_verified", ok: signatureVerified },
    { blocking: true, name: "registry_organization_identity_not_self_claimed", ok: true },
    { blocking: true, name: "external_adapter_conformance_not_self_claimed", ok: true },
  ];
  const localPass = checks.slice(0, 6).every((check) => check.ok);
  const localBlockers = checks
    .slice(0, 6)
    .filter((check) => !check.ok)
    .map((check) => `LOCAL_REGISTRY_KEY_POSSESSION_CHECK_FAILED:${check.name}`);
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...localBlockers, ...REMAINING_BLOCKERS],
      checks,
      decision: localPass
        ? "PREREGISTERED_REGISTRY_ED25519_KEY_POSSESSION_VERIFIED_EXTERNAL_IDENTITY_AND_CONFORMANCE_UNVERIFIED"
        : "REGISTRY_ED25519_KEY_POSSESSION_BLOCKED_EXTERNAL_IDENTITY_AND_CONFORMANCE_UNVERIFIED",
      facts: verificationFacts(localPass),
      local_registry_key_possession_status: localPass ? "PASS" : "BLOCK",
      schema_version: VERIFICATION_SCHEMA_VERSION,
      source: {
        attestation_hash: attestation.attestation_hash,
        challenge_hash: challenge.challenge_hash,
        key_algorithm: "Ed25519",
        policy_hash: policy.policy_hash,
        preregistration_hash: preregistration.preregistration_hash,
        public_key_spki_sha256: keyInfo.spkiSha256,
        registry_id: preregistration.identity.registry_id,
        signed_payload: SIGNED_PAYLOAD,
      },
      static_fingerprint: VERIFICATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "verification_hash"
  );
}

function blockedExactVerification(blocker) {
  return {
    adapter_conformance_verified: false,
    blockers: [blocker],
    current_admission_allowed: false,
    external_linearizability_verified: false,
    live_order_allowed: false,
    local_registry_key_possession_status: "UNVERIFIED",
    paper_authorized: false,
    post_registration_receipt_issued: false,
    presentation_mount_allowed: false,
    registry_key_possession_verified: false,
    registry_organization_identity_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
    status: "BLOCK",
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
    verification_document_exactly_rebuilt: false,
    verification_status: "UNKNOWN",
    writer_allowed: false,
  };
}

function verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1(
  preregistration,
  policy,
  challenge,
  rawNonce,
  publicKeyMaterial,
  detachedSignature,
  document
) {
  try {
    const expected = verifyAntiReplayRegistryKeyPossessionCandidateV1(
      preregistration,
      policy,
      challenge,
      rawNonce,
      publicKeyMaterial,
      detachedSignature
    );
    const exact =
      verifySealedDocument(document, "verification_hash") &&
      strictCanonicalHash(document) === strictCanonicalHash(expected);
    if (!exact) {
      return blockedExactVerification(
        "REGISTRY_KEY_POSSESSION_VERIFICATION_DOCUMENT_EXACT_REBUILD"
      );
    }
    const localPass =
      expected.local_registry_key_possession_status === "PASS";
    return {
      adapter_conformance_verified: false,
      blockers: localPass ? [] : ["LOCAL_REGISTRY_KEY_POSSESSION_NOT_PASS"],
      current_admission_allowed: false,
      external_linearizability_verified: false,
      live_order_allowed: false,
      local_registry_key_possession_status:
        expected.local_registry_key_possession_status,
      paper_authorized: false,
      post_registration_receipt_issued: false,
      presentation_mount_allowed: false,
      registry_key_possession_verified: localPass,
      registry_organization_identity_verified: false,
      runtime_gate_activation_allowed: false,
      schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
      status: localPass ? "PASS" : "BLOCK",
      target_consumption_receipt_issued: false,
      trusted_registry_time_verified: false,
      verification_document_exactly_rebuilt: true,
      verification_status: "BLOCKED",
      writer_allowed: false,
    };
  } catch (_error) {
    return blockedExactVerification(
      "REGISTRY_KEY_POSSESSION_VERIFICATION_INPUT_INVALID"
    );
  }
}

module.exports = {
  ATTESTATION_SCHEMA_VERSION,
  ATTESTATION_STATIC_FINGERPRINT,
  CHALLENGE_SCHEMA_VERSION,
  CHALLENGE_STATIC_FINGERPRINT,
  EXACT_VERIFICATION_SCHEMA_VERSION,
  POLICY_SCHEMA_VERSION,
  POLICY_STATIC_FINGERPRINT,
  PREREGISTRATION_SCHEMA_VERSION,
  PREREGISTRATION_STATIC_FINGERPRINT,
  PYTHON_PREREGISTRATION_IMPLEMENTATION_SHA256,
  PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  VERIFICATION_SCHEMA_VERSION,
  VERIFICATION_STATIC_FINGERPRINT,
  buildAntiReplayRegistryDetachedAttestationV1,
  buildAntiReplayRegistryKeyPossessionChallengeV1,
  buildAntiReplayRegistryKeyPossessionPolicyV1,
  verifyAntiReplayRegistryKeyPossessionCandidateV1,
  verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1,
};
