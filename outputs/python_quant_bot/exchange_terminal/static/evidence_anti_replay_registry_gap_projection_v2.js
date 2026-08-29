"use strict";

const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const projectionV1 = require("./evidence_anti_replay_registry_gap_projection_v1.js");
const aggregationV1 = require(
  "./evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js"
);

const PROJECTION_SCHEMA_VERSION = "anti-replay-registry-gap-projection-v2";
const PROJECTION_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-identity-gap-projection-v2-unmounted-lock-1";
const PROJECTION_V1_IMPLEMENTATION_SHA256 =
  "021a4618caf5968057b13dd744918bf059d2a756eb47fe4cc1a55b538de1ca7d";
const AGGREGATION_IMPLEMENTATION_SHA256 =
  "5a1df11be56fcb641d1d04dc0397a94bd22a8c08ea632cd0cf4eb5d9c9754a0f";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
const HASH_PATTERN = /^[0-9a-f]{64}$/;
const AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "evidence_bundle_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "presentation_mount_allowed",
  "registry_identity_admission_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed",
]);
const REMAINING_BLOCKERS = Object.freeze([
  "PYTHON_PROCESS_AUTHENTICATION_UNVERIFIED",
  "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
  "SIGNER_ROLE_IDENTITY_UNVERIFIED",
  "EXTERNAL_SOURCE_TRUST_UNPROVEN",
  "REVOCATION_CONTENT_UNVERIFIED",
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
  "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
  "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
  "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
  "TRUSTED_REGISTRY_TIME_UNVERIFIED",
  "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
  "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
]);
const GAP_ITEMS = Object.freeze(
  projectionV1.GAP_ITEMS.map((item) =>
    Object.freeze({
      id: item.id,
      label: item.label,
      state: item.id === "ORGANIZATION_IDENTITY" ? "OPEN" : item.state,
    })
  )
);
const IDENTITY_EVIDENCE_LEDGER = Object.freeze([
  Object.freeze({
    id: "LOCAL_REGISTRY_KEY_POSSESSION",
    label: "Registry key possession",
    state: "OBSERVED-LOCAL",
  }),
  Object.freeze({
    id: "SIX_ARTIFACT_CRYPTOGRAPHIC_BINDING",
    label: "Six artifact hash and signature bindings",
    state: "OBSERVED-LOCAL",
  }),
  Object.freeze({
    id: "PYTHON_PROCESS_AUTHENTICATION",
    label: "Python verification process authentication",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "EVIDENCE_PAYLOAD_SEMANTICS",
    label: "Evidence payload semantics",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "SIGNER_ROLE_IDENTITY",
    label: "Signer role identity",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "EXTERNAL_SOURCE_TRUST",
    label: "External source trust",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "REVOCATION_CONTENT",
    label: "Revocation content",
    state: "UNVERIFIED",
  }),
  Object.freeze({
    id: "REGISTRY_ORGANIZATION_IDENTITY",
    label: "Registry organization identity",
    state: "UNVERIFIED",
  }),
]);
const AGGREGATION_AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "evidence_bundle_admission_allowed",
  "live_order_allowed",
  "paper_authorized",
  "presentation_mount_allowed",
  "registry_identity_admission_allowed",
  "runtime_gate_activation_allowed",
  "signed_artifact_aggregation_activation_allowed",
  "writer_allowed",
]);
const AGGREGATION_BLOCKERS = Object.freeze([
  "PYTHON_PROCESS_AUTHENTICATION_UNVERIFIED",
  "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
  "SIGNER_ROLE_IDENTITY_UNVERIFIED",
  "EXTERNAL_SOURCE_TRUST_UNPROVEN",
  "REVOCATION_CONTENT_UNVERIFIED",
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
]);
const AGGREGATION_CHECK_NAMES = Object.freeze([
  "python_bundle_verification_envelope_v1_exact",
  "one_signed_artifact_per_evidence_kind_exact",
  "normalized_reference_set_hash_matches_python_envelope",
  "all_reference_subjects_match_python_envelope",
  "all_references_fresh_at_python_envelope_reference_time",
  "all_signer_roles_distinct",
  "all_signer_public_keys_distinct",
  "all_artifact_hashes_distinct",
  "all_six_signed_artifact_exact_verifiers_pass",
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

function lockedAuthority() {
  return Object.fromEntries(AUTHORITY_KEYS.map((key) => [key, false]));
}

function isLockedAuthority(value, keys) {
  return (
    hasExactKeys(value, keys) &&
    keys.every((key) => value[key] === false)
  );
}

function isExactProjectionV1Evidence(value) {
  return (
    hasExactKeys(value, [
      "blockers",
      "current_admission_allowed",
      "live_order_allowed",
      "paper_authorized",
      "presentation_mount_allowed",
      "projection_document_exactly_rebuilt",
      "projection_status",
      "runtime_gate_activation_allowed",
      "schema_version",
      "status",
      "writer_allowed",
    ]) &&
    value.schema_version ===
      "anti-replay-registry-gap-projection-exact-rebuild-v1" &&
    value.status === "PASS" &&
    value.projection_document_exactly_rebuilt === true &&
    value.projection_status === "BLOCKED" &&
    sameArray(value.blockers, []) &&
    [
      "current_admission_allowed",
      "live_order_allowed",
      "paper_authorized",
      "presentation_mount_allowed",
      "runtime_gate_activation_allowed",
      "writer_allowed",
    ].every((field) => value[field] === false)
  );
}

function expectedAggregationFacts() {
  return {
    all_artifact_hashes_distinct: true,
    all_evidence_kinds_present: true,
    all_references_fresh: true,
    all_signer_public_keys_distinct: true,
    all_signer_roles_distinct: true,
    evidence_payloads_embedded: false,
    evidence_payloads_observed: true,
    evidence_payloads_semantics_verified: false,
    evidence_reference_set_bound: true,
    evidence_signatures_verified: true,
    external_source_trust_verified: false,
    network_accessed: false,
    private_key_material_received: false,
    public_key_material_embedded: false,
    public_key_material_received: true,
    python_envelope_seal_verified: true,
    python_process_authenticated: false,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_assets_accessed: false,
    signature_material_embedded: false,
    signature_material_received: true,
    signer_role_identity_verified: false,
    subject_identity_bound: true,
  };
}

function isExactAggregationArtifactRows(value) {
  return (
    Array.isArray(value) &&
    value.length === aggregationV1.EVIDENCE_KINDS.length &&
    value.every(
      (row, index) =>
        hasExactKeys(row, [
          "artifact_sha256",
          "evidence_kind",
          "evidence_reference_sha256",
          "evidence_schema_version",
          "evidence_signature_verified",
          "local_signed_artifact_status",
          "signature_sha256",
          "signer_public_key_spki_sha256",
          "signer_role",
          "verification_hash",
          "verification_status",
        ]) &&
        row.evidence_kind === aggregationV1.EVIDENCE_KINDS[index] &&
        [
          row.artifact_sha256,
          row.evidence_reference_sha256,
          row.signature_sha256,
          row.signer_public_key_spki_sha256,
          row.verification_hash,
        ].every(isHash) &&
        typeof row.evidence_schema_version === "string" &&
        typeof row.signer_role === "string" &&
        row.evidence_signature_verified === true &&
        row.local_signed_artifact_status === "PASS" &&
        row.verification_status === "BLOCKED"
    )
  );
}

function isExactAggregationDocument(value) {
  const facts = expectedAggregationFacts();
  return (
    hasExactKeys(value, [
      "aggregation_hash",
      "artifacts",
      "authority",
      "blockers",
      "checks",
      "decision",
      "facts",
      "local_signed_artifact_bundle_status",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
    ]) &&
    verifySealedDocument(value, "aggregation_hash") &&
    value.schema_version === aggregationV1.AGGREGATION_SCHEMA_VERSION &&
    value.static_fingerprint === aggregationV1.AGGREGATION_STATIC_FINGERPRINT &&
    value.status === "BLOCKED" &&
    value.local_signed_artifact_bundle_status === aggregationV1.LOCAL_PASS_STATUS &&
    value.decision ===
      "SIX_SIGNED_ARTIFACTS_CRYPTOGRAPHICALLY_BOUND_PROCESS_SEMANTICS_SOURCE_ROLE_AND_IDENTITY_UNVERIFIED" &&
    sameArray(value.blockers, AGGREGATION_BLOCKERS) &&
    isLockedAuthority(value.authority, AGGREGATION_AUTHORITY_KEYS) &&
    hasExactKeys(value.facts, Object.keys(facts)) &&
    Object.keys(facts).every((key) => value.facts[key] === facts[key]) &&
    Array.isArray(value.checks) &&
    value.checks.length === AGGREGATION_CHECK_NAMES.length &&
    value.checks.every(
      (check, index) =>
        hasExactKeys(check, ["blocking", "name", "ok"]) &&
        check.blocking === true &&
        check.name === AGGREGATION_CHECK_NAMES[index] &&
        check.ok === true
    ) &&
    isExactAggregationArtifactRows(value.artifacts) &&
    hasExactKeys(value.source, [
      "evidence_reference_count",
      "evidence_reference_set_sha256",
      "public_key_spki_sha256",
      "python_envelope_hash",
      "python_envelope_implementation_sha256",
      "reference_time_ms",
      "registry_id",
      "signed_artifact_candidate_implementation_sha256",
      "trust_domain",
    ]) &&
    value.source.evidence_reference_count === aggregationV1.EVIDENCE_KINDS.length &&
    [
      value.source.evidence_reference_set_sha256,
      value.source.public_key_spki_sha256,
      value.source.python_envelope_hash,
    ].every(isHash) &&
    value.source.python_envelope_implementation_sha256 ===
      aggregationV1.PYTHON_ENVELOPE_IMPLEMENTATION_SHA256 &&
    value.source.signed_artifact_candidate_implementation_sha256 ===
      aggregationV1.SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256
  );
}

function isExactAggregationEvidence(value) {
  const falseFields = [
    "current_admission_allowed",
    "evidence_bundle_admission_allowed",
    "evidence_payloads_semantics_verified",
    "external_source_trust_verified",
    "live_order_allowed",
    "paper_authorized",
    "presentation_mount_allowed",
    "python_process_authenticated",
    "registry_identity_admission_allowed",
    "registry_organization_identity_verified",
    "revocation_content_verified",
    "runtime_gate_activation_allowed",
    "signed_artifact_aggregation_activation_allowed",
    "signer_role_identity_verified",
    "writer_allowed",
  ];
  return (
    hasExactKeys(value, [
      "aggregation_document_exactly_rebuilt",
      "aggregation_status",
      "blockers",
      ...falseFields,
      "evidence_signatures_verified",
      "local_signed_artifact_bundle_status",
      "schema_version",
      "status",
    ]) &&
    value.schema_version === aggregationV1.EXACT_VERIFICATION_SCHEMA_VERSION &&
    value.status === "PASS" &&
    value.aggregation_document_exactly_rebuilt === true &&
    value.aggregation_status === "BLOCKED" &&
    value.local_signed_artifact_bundle_status === aggregationV1.LOCAL_PASS_STATUS &&
    value.evidence_signatures_verified === true &&
    sameArray(value.blockers, []) &&
    falseFields.every((field) => value[field] === false)
  );
}

function buildAntiReplayRegistryGapProjectionV2(
  predecessorProjection,
  predecessorExactEvidence,
  aggregationDocument,
  aggregationExactEvidence
) {
  if (
    !projectionV1.verifyAntiReplayRegistryGapProjectionV1(predecessorProjection) ||
    !isExactProjectionV1Evidence(predecessorExactEvidence) ||
    !isExactAggregationDocument(aggregationDocument) ||
    !isExactAggregationEvidence(aggregationExactEvidence)
  ) {
    throw new TypeError(
      "registry gap predecessor or signed-artifact aggregation is not exact"
    );
  }
  const registryIdBound =
    predecessorProjection.source.registry_id ===
    aggregationDocument.source.registry_id;
  const publicKeyBound =
    predecessorProjection.source.public_key_spki_sha256 ===
    aggregationDocument.source.public_key_spki_sha256;
  if (!registryIdBound || !publicKeyBound) {
    throw new TypeError(
      "registry gap predecessor and aggregation subject do not match"
    );
  }
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...REMAINING_BLOCKERS],
      decision:
        "LOCAL_KEY_POSSESSION_AND_SIX_ARTIFACT_SIGNATURE_BINDINGS_OBSERVED_IDENTITY_SOURCE_AND_PERMISSION_GAPS_REMAIN",
      facts: {
        evidence_payload_semantics_verified: false,
        evidence_signature_count: aggregationDocument.artifacts.length,
        external_source_trust_verified: false,
        gap_count: GAP_ITEMS.length,
        identity_evidence_ledger_count: IDENTITY_EVIDENCE_LEDGER.length,
        local_evidence_observation_count: 2,
        local_registry_key_possession_verified: true,
        projection_descriptive_only: true,
        python_process_authenticated: false,
        registry_organization_identity_verified: false,
        revocation_content_verified: false,
        signer_role_identity_verified: false,
        six_artifact_cryptographic_binding_verified: true,
        unverified_identity_evidence_count: 6,
      },
      identity_evidence: {
        ledger: IDENTITY_EVIDENCE_LEDGER.map((item) => ({ ...item })),
        local_observation_count: 2,
        state: "INCOMPLETE",
        unverified_count: 6,
      },
      schema_version: PROJECTION_SCHEMA_VERSION,
      source: {
        aggregation_hash: aggregationDocument.aggregation_hash,
        evidence_reference_set_sha256:
          aggregationDocument.source.evidence_reference_set_sha256,
        predecessor_projection_hash: predecessorProjection.projection_hash,
        public_key_spki_sha256:
          aggregationDocument.source.public_key_spki_sha256,
        registry_id: aggregationDocument.source.registry_id,
        signed_artifact_bundle_contract:
          aggregationV1.AGGREGATION_SCHEMA_VERSION,
      },
      stage_order: [...STAGE_ORDER],
      stages: {
        gap: {
          items: GAP_ITEMS.map((item) => ({ ...item })),
          state: "OPEN",
        },
        maturity: {
          evidence_payload_semantics: "UNVERIFIED",
          external_source_trust: "UNVERIFIED",
          local_key_possession: "OBSERVED-LOCAL",
          six_artifact_cryptographic_binding: "OBSERVED-LOCAL",
          state: "LOCAL-CRYPTOGRAPHIC-ONLY",
        },
        permission: {
          current: "LOCKED",
          evidence_bundle: "LOCKED",
          identity: "LOCKED",
          live: "LOCKED",
          mount: "LOCKED",
          paper: "LOCKED",
          runtime: "LOCKED",
          state: "LOCKED",
          writer: "LOCKED",
        },
        source: {
          local_key_possession: "OBSERVED-LOCAL",
          signed_artifact_bundle:
            aggregationV1.AGGREGATION_SCHEMA_VERSION,
          six_artifact_cryptographic_binding: "OBSERVED-LOCAL",
          state: "HASH-BOUND",
        },
      },
      static_fingerprint: PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "projection_hash"
  );
}

function verifyAntiReplayRegistryGapProjectionV2(value) {
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "decision",
      "facts",
      "identity_evidence",
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
    !isLockedAuthority(value.authority, AUTHORITY_KEYS) ||
    !hasExactKeys(value.stages, ["gap", "maturity", "permission", "source"]) ||
    !hasExactKeys(value.identity_evidence, [
      "ledger",
      "local_observation_count",
      "state",
      "unverified_count",
    ])
  ) {
    return false;
  }
  return (
    value.stages.source.state === "HASH-BOUND" &&
    value.stages.source.local_key_possession === "OBSERVED-LOCAL" &&
    value.stages.source.six_artifact_cryptographic_binding ===
      "OBSERVED-LOCAL" &&
    value.stages.gap.state === "OPEN" &&
    strictCanonicalHash(value.stages.gap.items) ===
      strictCanonicalHash(GAP_ITEMS) &&
    value.stages.maturity.state === "LOCAL-CRYPTOGRAPHIC-ONLY" &&
    value.stages.permission.state === "LOCKED" &&
    Object.entries(value.stages.permission).every(
      ([key, state]) => key === "state" || state === "LOCKED"
    ) &&
    value.identity_evidence.state === "INCOMPLETE" &&
    value.identity_evidence.local_observation_count === 2 &&
    value.identity_evidence.unverified_count === 6 &&
    strictCanonicalHash(value.identity_evidence.ledger) ===
      strictCanonicalHash(IDENTITY_EVIDENCE_LEDGER) &&
    isHash(value.source.aggregation_hash) &&
    isHash(value.source.predecessor_projection_hash) &&
    isHash(value.source.evidence_reference_set_sha256) &&
    isHash(value.source.public_key_spki_sha256) &&
    value.facts.evidence_signature_count === 6 &&
    value.facts.six_artifact_cryptographic_binding_verified === true &&
    value.facts.registry_organization_identity_verified === false
  );
}

function verifyAntiReplayRegistryGapProjectionExactV2(
  predecessorProjection,
  predecessorExactEvidence,
  aggregationDocument,
  aggregationExactEvidence,
  projection
) {
  try {
    const expected = buildAntiReplayRegistryGapProjectionV2(
      predecessorProjection,
      predecessorExactEvidence,
      aggregationDocument,
      aggregationExactEvidence
    );
    const exact =
      verifyAntiReplayRegistryGapProjectionV2(projection) &&
      strictCanonicalHash(projection) === strictCanonicalHash(expected);
    return {
      blockers: exact ? [] : ["ANTI_REPLAY_REGISTRY_GAP_PROJECTION_V2_EXACT_REBUILD"],
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      projection_document_exactly_rebuilt: exact,
      projection_status: exact ? "BLOCKED" : "UNKNOWN",
      registry_identity_admission_allowed: false,
      runtime_gate_activation_allowed: false,
      schema_version: "anti-replay-registry-gap-projection-v2-exact-rebuild-v1",
      status: exact ? "PASS" : "BLOCK",
      writer_allowed: false,
    };
  } catch (_error) {
    return {
      blockers: ["ANTI_REPLAY_REGISTRY_GAP_PROJECTION_V2_INPUT_INVALID"],
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      presentation_mount_allowed: false,
      projection_document_exactly_rebuilt: false,
      projection_status: "UNKNOWN",
      registry_identity_admission_allowed: false,
      runtime_gate_activation_allowed: false,
      schema_version: "anti-replay-registry-gap-projection-v2-exact-rebuild-v1",
      status: "BLOCK",
      writer_allowed: false,
    };
  }
}

module.exports = {
  AGGREGATION_IMPLEMENTATION_SHA256,
  GAP_ITEMS,
  IDENTITY_EVIDENCE_LEDGER,
  PROJECTION_SCHEMA_VERSION,
  PROJECTION_STATIC_FINGERPRINT,
  PROJECTION_V1_IMPLEMENTATION_SHA256,
  STAGE_ORDER,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  buildAntiReplayRegistryGapProjectionV2,
  verifyAntiReplayRegistryGapProjectionExactV2,
  verifyAntiReplayRegistryGapProjectionV2,
};
