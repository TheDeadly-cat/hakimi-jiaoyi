"use strict";

const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const keyPossessionV1 = require("./evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js");

const PROJECTION_SCHEMA_VERSION = "anti-replay-registry-gap-projection-v1";
const PROJECTION_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-gap-projection-v1-unmounted-lock-1";
const KEY_POSSESSION_IMPLEMENTATION_SHA256 =
  "aab58710d8cc2bf81f66e2daf8f562e1310ab591542a328b00c23ebdc102bdaf";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
const HASH_PATTERN = /^[0-9a-f]{64}$/;
const AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "post_registration_receipt_issuance_allowed",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
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
const GAP_ITEMS = Object.freeze([
  Object.freeze({
    id: "ORGANIZATION_IDENTITY",
    label: "Registry organization identity",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "ADAPTER_CONFORMANCE",
    label: "External adapter conformance",
    state: "UNEXECUTED",
  }),
  Object.freeze({
    id: "EXTERNAL_LINEARIZABILITY",
    label: "Shared linearizability",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "DURABLE_ATOMIC_CONSUMPTION",
    label: "Durable atomic consumption",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "TRUSTED_REGISTRY_TIME",
    label: "Trusted registry time",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "SIGNED_CONSUMPTION_RECEIPT",
    label: "Signed consumption receipt-v1",
    state: "MISSING",
  }),
  Object.freeze({
    id: "POST_REGISTRATION_RECEIPT",
    label: "Post-registration receipt-v5",
    state: "MISSING",
  }),
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

function expectedVerificationFacts() {
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
    preregistered_public_key_hash_matched: true,
    public_key_material_embedded: false,
    public_key_material_received: true,
    raw_nonce_embedded: false,
    raw_nonce_received: true,
    registry_key_possession_verified: true,
    registry_organization_identity_verified: false,
    runtime_assets_accessed: false,
    signature_material_embedded: false,
    signature_material_received: true,
    signed_target_consumption_receipt_verified: false,
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
  };
}

function isExactKeyPossessionVerification(value) {
  const facts = expectedVerificationFacts();
  const checkNames = [
    "registry_identity_preregistration_v1_exact",
    "registry_key_possession_policy_v1_exact",
    "registry_key_possession_challenge_v1_exact",
    "registry_detached_attestation_v1_exact",
    "ed25519_public_key_hash_matches_preregistration",
    "ed25519_detached_signature_verified",
    "registry_organization_identity_not_self_claimed",
    "external_adapter_conformance_not_self_claimed",
  ];
  return (
    hasExactKeys(value, [
      "authority",
      "blockers",
      "checks",
      "decision",
      "facts",
      "local_registry_key_possession_status",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
      "verification_hash",
    ]) &&
    verifySealedDocument(value, "verification_hash") &&
    value.schema_version === keyPossessionV1.VERIFICATION_SCHEMA_VERSION &&
    value.static_fingerprint === keyPossessionV1.VERIFICATION_STATIC_FINGERPRINT &&
    value.status === "BLOCKED" &&
    value.local_registry_key_possession_status === "PASS" &&
    value.decision ===
      "PREREGISTERED_REGISTRY_ED25519_KEY_POSSESSION_VERIFIED_EXTERNAL_IDENTITY_AND_CONFORMANCE_UNVERIFIED" &&
    sameArray(value.blockers, REMAINING_BLOCKERS) &&
    isLockedAuthority(value.authority) &&
    hasExactKeys(value.facts, Object.keys(facts)) &&
    Object.keys(facts).every((key) => value.facts[key] === facts[key]) &&
    Array.isArray(value.checks) &&
    value.checks.length === checkNames.length &&
    value.checks.every(
      (check, index) =>
        hasExactKeys(check, ["blocking", "name", "ok"]) &&
        check.name === checkNames[index] &&
        check.blocking === true &&
        check.ok === true
    ) &&
    hasExactKeys(value.source, [
      "attestation_hash",
      "challenge_hash",
      "key_algorithm",
      "policy_hash",
      "preregistration_hash",
      "public_key_spki_sha256",
      "registry_id",
      "signed_payload",
    ]) &&
    [
      value.source.attestation_hash,
      value.source.challenge_hash,
      value.source.policy_hash,
      value.source.preregistration_hash,
      value.source.public_key_spki_sha256,
    ].every(isHash) &&
    value.source.key_algorithm === "Ed25519" &&
    value.source.signed_payload ===
      "STRICT_CANONICAL_REGISTRY_KEY_POSSESSION_CHALLENGE" &&
    typeof value.source.registry_id === "string" &&
    value.source.registry_id.length > 0
  );
}

function isExactKeyPossessionEvidence(value, verification) {
  const falseFields = [
    "adapter_conformance_verified",
    "current_admission_allowed",
    "external_linearizability_verified",
    "live_order_allowed",
    "paper_authorized",
    "post_registration_receipt_issued",
    "presentation_mount_allowed",
    "registry_organization_identity_verified",
    "runtime_gate_activation_allowed",
    "target_consumption_receipt_issued",
    "trusted_registry_time_verified",
    "writer_allowed",
  ];
  return (
    hasExactKeys(value, [
      ...falseFields,
      "blockers",
      "local_registry_key_possession_status",
      "registry_key_possession_verified",
      "schema_version",
      "status",
      "verification_document_exactly_rebuilt",
      "verification_status",
    ]) &&
    value.schema_version === keyPossessionV1.EXACT_VERIFICATION_SCHEMA_VERSION &&
    value.status === "PASS" &&
    value.local_registry_key_possession_status === "PASS" &&
    value.registry_key_possession_verified === true &&
    value.verification_document_exactly_rebuilt === true &&
    value.verification_status === verification.status &&
    Array.isArray(value.blockers) &&
    value.blockers.length === 0 &&
    falseFields.every((field) => value[field] === false)
  );
}

function buildAntiReplayRegistryGapProjectionV1(verification, exactEvidence) {
  if (
    !isExactKeyPossessionVerification(verification) ||
    !isExactKeyPossessionEvidence(exactEvidence, verification)
  ) {
    throw new TypeError("registry key-possession evidence is not exact and locally valid");
  }
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...REMAINING_BLOCKERS],
      decision:
        "LOCAL_REGISTRY_KEY_POSSESSION_OBSERVED_EXTERNAL_EVIDENCE_GAPS_REMAIN",
      facts: {
        adapter_conformance_verified: false,
        external_linearizability_verified: false,
        gap_count: GAP_ITEMS.length,
        local_registry_key_possession_verified: true,
        post_registration_receipt_issued: false,
        projection_descriptive_only: true,
        registry_organization_identity_verified: false,
        target_consumption_receipt_issued: false,
        trusted_registry_time_verified: false,
      },
      schema_version: PROJECTION_SCHEMA_VERSION,
      source: {
        attestation_hash: verification.source.attestation_hash,
        challenge_hash: verification.source.challenge_hash,
        key_algorithm: verification.source.key_algorithm,
        policy_hash: verification.source.policy_hash,
        preregistration_hash: verification.source.preregistration_hash,
        public_key_spki_sha256: verification.source.public_key_spki_sha256,
        registry_id: verification.source.registry_id,
        verification_hash: verification.verification_hash,
      },
      stage_order: [...STAGE_ORDER],
      stages: {
        gap: {
          items: GAP_ITEMS.map((item) => ({ ...item })),
          state: "OPEN",
        },
        maturity: {
          adapter_conformance: "UNEXECUTED",
          external_registry_behavior: "UNVERIFIED",
          local_key_possession: "PASS",
          state: "LOCAL_ONLY",
        },
        permission: {
          current: "LOCKED",
          live: "LOCKED",
          mount: "LOCKED",
          paper: "LOCKED",
          receipt_issuance: "LOCKED",
          runtime: "LOCKED",
          state: "LOCKED",
          writer: "LOCKED",
        },
        source: {
          contract: keyPossessionV1.VERIFICATION_SCHEMA_VERSION,
          local_key_possession: "PASS",
          state: "HASH_BOUND",
        },
      },
      static_fingerprint: PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "projection_hash"
  );
}

function verifyAntiReplayRegistryGapProjectionV1(value) {
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "decision",
      "facts",
      "projection_hash",
      "schema_version",
      "source",
      "stage_order",
      "stages",
      "static_fingerprint",
      "status",
    ]) ||
    !verifySealedDocument(value, "projection_hash") ||
    value.schema_version !== PROJECTION_SCHEMA_VERSION ||
    value.static_fingerprint !== PROJECTION_STATIC_FINGERPRINT ||
    value.status !== "BLOCKED" ||
    !sameArray(value.stage_order, STAGE_ORDER) ||
    !sameArray(value.blockers, REMAINING_BLOCKERS) ||
    !isLockedAuthority(value.authority) ||
    !hasExactKeys(value.stages, ["gap", "maturity", "permission", "source"])
  ) {
    return false;
  }
  return (
    value.stages.source.state === "HASH_BOUND" &&
    value.stages.source.local_key_possession === "PASS" &&
    value.stages.gap.state === "OPEN" &&
    Array.isArray(value.stages.gap.items) &&
    value.stages.gap.items.length === GAP_ITEMS.length &&
    value.stages.maturity.state === "LOCAL_ONLY" &&
    value.stages.permission.state === "LOCKED" &&
    Object.entries(value.stages.permission).every(
      ([key, state]) => key === "state" || state === "LOCKED"
    ) &&
    isHash(value.source.verification_hash) &&
    isHash(value.source.public_key_spki_sha256)
  );
}

function verifyAntiReplayRegistryGapProjectionExactV1(
  verification,
  exactEvidence,
  projection
) {
  try {
    const expected = buildAntiReplayRegistryGapProjectionV1(
      verification,
      exactEvidence
    );
    const exact =
      verifyAntiReplayRegistryGapProjectionV1(projection) &&
      strictCanonicalHash(projection) === strictCanonicalHash(expected);
    return {
      blockers: exact ? [] : ["ANTI_REPLAY_REGISTRY_GAP_PROJECTION_EXACT_REBUILD"],
      current_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      projection_document_exactly_rebuilt: exact,
      projection_status: exact ? "BLOCKED" : "UNKNOWN",
      runtime_gate_activation_allowed: false,
      schema_version: "anti-replay-registry-gap-projection-exact-rebuild-v1",
      status: exact ? "PASS" : "BLOCK",
      writer_allowed: false,
    };
  } catch (_error) {
    return {
      blockers: ["ANTI_REPLAY_REGISTRY_GAP_PROJECTION_INPUT_INVALID"],
      current_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      projection_document_exactly_rebuilt: false,
      projection_status: "UNKNOWN",
      runtime_gate_activation_allowed: false,
      schema_version: "anti-replay-registry-gap-projection-exact-rebuild-v1",
      status: "BLOCK",
      writer_allowed: false,
    };
  }
}

module.exports = {
  GAP_ITEMS,
  KEY_POSSESSION_IMPLEMENTATION_SHA256,
  PROJECTION_SCHEMA_VERSION,
  PROJECTION_STATIC_FINGERPRINT,
  STAGE_ORDER,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  buildAntiReplayRegistryGapProjectionV1,
  verifyAntiReplayRegistryGapProjectionExactV1,
  verifyAntiReplayRegistryGapProjectionV1,
};
