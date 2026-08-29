"use strict";

const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");
const signedArtifactV1 = require(
  "./evidence_anti_replay_registry_organization_identity_signed_artifact_candidate_v1.js"
);

const PYTHON_ENVELOPE_SCHEMA_VERSION =
  "anti-replay-registry-organization-identity-evidence-bundle-python-verification-envelope-v1";
const PYTHON_ENVELOPE_STATIC_FINGERPRINT =
  "20260823-registry-organization-identity-bundle-python-envelope-v1-lock-1";
const AGGREGATION_SCHEMA_VERSION =
  "registry-organization-identity-signed-artifact-bundle-aggregation-candidate-v1";
const AGGREGATION_STATIC_FINGERPRINT =
  "20260823-registry-organization-identity-signed-artifact-bundle-aggregation-v1-lock-1";
const EXACT_VERIFICATION_SCHEMA_VERSION =
  "registry-organization-identity-signed-artifact-bundle-aggregation-exact-rebuild-v1";
const LOCAL_PASS_STATUS = "CRYPTOGRAPHIC_BINDING_PASS";

const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256 =
  "3f31febbc017d57cee6dd666751f83f2796fd60257aab0d211156e70b47cfecc";
const PYTHON_ENVELOPE_IMPLEMENTATION_SHA256 =
  "c51984b8e15d7847a46d9d452ab099ca954bd11cadccad1d510fdc2539f9c05d";
const PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
const PYTHON_IDENTITY_IMPLEMENTATION_SHA256 =
  "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f";
const PYTHON_INTAKE_IMPLEMENTATION_SHA256 =
  "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56";
const PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256 =
  "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f";
const PYTHON_BUNDLE_EVALUATION_IMPLEMENTATION_SHA256 =
  "fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055";

const BUNDLE_EVALUATION_SCHEMA_VERSION =
  "anti-replay-registry-organization-identity-evidence-bundle-evaluation-v1";
const BUNDLE_EVALUATION_STATIC_FINGERPRINT =
  "20260823-registry-organization-identity-evidence-bundle-evaluation-v1-lock-1";
const HASH_PATTERN = /^[0-9a-f]{64}$/;
const IDENTIFIER_PATTERN = /^[a-z0-9][a-z0-9._:-]{2,127}$/;
const EVIDENCE_KINDS = Object.freeze([
  "ORGANIZATION_REGISTRY_ATTESTATION",
  "DOMAIN_CONTROL_ATTESTATION",
  "KEY_GOVERNANCE_EVALUATION",
  "AUDITOR_PROVENANCE_EVALUATION",
  "ARTIFACT_TRANSPARENCY_EVALUATION",
  "REVOCATION_STATUS_RECEIPT",
]);
const AUTHORITY_KEYS = Object.freeze([
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
const ENVELOPE_CHECK_NAMES = Object.freeze([
  "identity_preregistration_v1_exact",
  "organization_identity_intake_v1_exact",
  "bundle_evaluation_v1_strict_canonical_seal_exact",
  "bundle_evaluation_v1_identity_and_local_pass_exact",
  "bundle_evaluation_v1_public_exact_verifier_pass",
  "identity_preregistration_hash_edge_exact",
  "intake_preregistration_hash_edge_exact",
  "six_reference_set_and_order_exact",
  "explicit_reference_time_exact",
  "registry_subject_identity_binding_exact",
  "signature_source_revocation_and_identity_remain_unverified",
  "bundle_evaluation_authority_locked",
]);
const REMAINING_BLOCKERS = Object.freeze([
  "PYTHON_PROCESS_AUTHENTICATION_UNVERIFIED",
  "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
  "SIGNER_ROLE_IDENTITY_UNVERIFIED",
  "EXTERNAL_SOURCE_TRUST_UNPROVEN",
  "REVOCATION_CONTENT_UNVERIFIED",
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
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

function isIdentifier(value) {
  return typeof value === "string" && IDENTIFIER_PATTERN.test(value);
}

function isTimestamp(value) {
  return Number.isSafeInteger(value) && value >= 0;
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

function expectedEnvelopeFacts() {
  return {
    browser_visual_review_performed: false,
    cross_runtime_summary_envelope_built: true,
    evidence_payloads_observed: false,
    evidence_references_embedded: false,
    evidence_signatures_verified: false,
    evaluation_document_embedded: false,
    external_source_trust_verified: false,
    identity_preregistration_document_embedded: false,
    independent_source_observation_verified: false,
    intake_preregistration_document_embedded: false,
    local_python_verification_execution_observed: true,
    local_structure_binding_freshness_verified: true,
    network_accessed: false,
    node_process_executed: false,
    operator_identity_claim_embedded: false,
    profitability_proven: false,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_assets_accessed: false,
    signed_artifact_candidate_executed: false,
    signed_artifact_verification_documents_embedded: false,
    signer_role_identity_verified: false,
    underlying_evaluation_remains_blocked: true,
  };
}

function isExactPythonVerificationEnvelopeV1(value) {
  const facts = expectedEnvelopeFacts();
  if (
    !hasExactKeys(value, [
      "authority",
      "blockers",
      "checks",
      "decision",
      "envelope_hash",
      "facts",
      "schema_version",
      "source",
      "static_fingerprint",
      "status",
      "target_contracts",
      "verification",
    ]) ||
    !verifySealedDocument(value, "envelope_hash") ||
    value.schema_version !== PYTHON_ENVELOPE_SCHEMA_VERSION ||
    value.static_fingerprint !== PYTHON_ENVELOPE_STATIC_FINGERPRINT ||
    value.status !== "PASS" ||
    value.decision !==
      "BLOCKED_BUNDLE_EVALUATION_V1_EXACTLY_VERIFIED_FOR_CROSS_RUNTIME_SIGNED_ARTIFACT_CONSUMER" ||
    !sameArray(value.blockers, []) ||
    !isLockedAuthority(value.authority) ||
    !hasExactKeys(value.facts, Object.keys(facts)) ||
    !Object.keys(facts).every((key) => value.facts[key] === facts[key]) ||
    !Array.isArray(value.checks) ||
    value.checks.length !== ENVELOPE_CHECK_NAMES.length ||
    !value.checks.every(
      (check, index) =>
        hasExactKeys(check, ["blocking", "name", "ok"]) &&
        check.blocking === true &&
        check.name === ENVELOPE_CHECK_NAMES[index] &&
        check.ok === true
    ) ||
    !hasExactKeys(value.source, [
      "bundle_evaluation_hash",
      "bundle_evaluation_implementation_sha256",
      "bundle_evaluation_schema_version",
      "bundle_evaluation_static_fingerprint",
      "evidence_reference_count",
      "evidence_reference_implementation_sha256",
      "evidence_reference_set_sha256",
      "identity_preregistration_hash",
      "identity_preregistration_implementation_sha256",
      "intake_preregistration_hash",
      "intake_preregistration_implementation_sha256",
      "operator_identity_claim_hash",
      "public_key_spki_sha256",
      "reference_time_ms",
      "registry_id",
      "strict_canonical_implementation_sha256",
      "trust_domain",
      "verification_environment",
    ]) ||
    !hasExactKeys(value.target_contracts, [
      "signed_artifact_aggregation_schema_version",
      "signed_artifact_candidate_implementation_sha256",
      "signed_artifact_exact_verification_schema_version",
      "signed_artifact_verification_schema_version",
    ]) ||
    !hasExactKeys(value.verification, [
      "bundle_evaluation_document_exactly_rebuilt",
      "bundle_evaluation_status",
      "bundle_local_status",
      "bundle_public_verifier_status",
      "evidence_reference_count",
      "identity_preregistration_status",
      "intake_preregistration_status",
      "reference_set_exact",
      "reference_time_exact",
    ])
  ) {
    return false;
  }
  const sourceHashes = [
    value.source.bundle_evaluation_hash,
    value.source.evidence_reference_set_sha256,
    value.source.identity_preregistration_hash,
    value.source.intake_preregistration_hash,
    value.source.operator_identity_claim_hash,
    value.source.public_key_spki_sha256,
  ];
  return (
    sourceHashes.every(isHash) &&
    value.source.bundle_evaluation_implementation_sha256 ===
      PYTHON_BUNDLE_EVALUATION_IMPLEMENTATION_SHA256 &&
    value.source.bundle_evaluation_schema_version ===
      BUNDLE_EVALUATION_SCHEMA_VERSION &&
    value.source.bundle_evaluation_static_fingerprint ===
      BUNDLE_EVALUATION_STATIC_FINGERPRINT &&
    value.source.evidence_reference_count === EVIDENCE_KINDS.length &&
    value.source.evidence_reference_implementation_sha256 ===
      PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256 &&
    value.source.identity_preregistration_implementation_sha256 ===
      PYTHON_IDENTITY_IMPLEMENTATION_SHA256 &&
    value.source.intake_preregistration_implementation_sha256 ===
      PYTHON_INTAKE_IMPLEMENTATION_SHA256 &&
    value.source.strict_canonical_implementation_sha256 ===
      PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256 &&
    isTimestamp(value.source.reference_time_ms) &&
    isIdentifier(value.source.registry_id) &&
    isIdentifier(value.source.trust_domain) &&
    value.source.verification_environment === "PYTHON_CONTRACT_PROCESS" &&
    value.target_contracts.signed_artifact_aggregation_schema_version ===
      AGGREGATION_SCHEMA_VERSION &&
    value.target_contracts.signed_artifact_candidate_implementation_sha256 ===
      SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256 &&
    value.target_contracts.signed_artifact_exact_verification_schema_version ===
      signedArtifactV1.EXACT_VERIFICATION_SCHEMA_VERSION &&
    value.target_contracts.signed_artifact_verification_schema_version ===
      signedArtifactV1.VERIFICATION_SCHEMA_VERSION &&
    value.verification.bundle_evaluation_document_exactly_rebuilt === true &&
    value.verification.bundle_evaluation_status === "BLOCKED" &&
    value.verification.bundle_local_status ===
      "STRUCTURE_BINDING_AND_FRESHNESS_PASS" &&
    value.verification.bundle_public_verifier_status === "PASS" &&
    value.verification.evidence_reference_count === EVIDENCE_KINDS.length &&
    value.verification.identity_preregistration_status === "BLOCKED" &&
    value.verification.intake_preregistration_status === "BLOCKED" &&
    value.verification.reference_set_exact === true &&
    value.verification.reference_time_exact === true
  );
}

function normalizeArtifactItems(items) {
  if (!Array.isArray(items) || items.length !== EVIDENCE_KINDS.length) {
    throw new TypeError("exactly six signed-artifact items are required");
  }
  if (
    !items.every(
      (item) =>
        hasExactKeys(item, [
          "detachedSignature",
          "payload",
          "publicKey",
          "reference",
        ]) &&
        signedArtifactV1.isExactEvidenceReferenceV1(item.reference)
    )
  ) {
    throw new TypeError("every signed-artifact item must use an exact reference");
  }
  const byKind = new Map(
    items.map((item) => [item.reference.evidence_kind, item])
  );
  if (
    byKind.size !== EVIDENCE_KINDS.length ||
    !EVIDENCE_KINDS.every((kind) => byKind.has(kind))
  ) {
    throw new TypeError("one signed-artifact item per evidence kind is required");
  }
  return EVIDENCE_KINDS.map((kind) => byKind.get(kind));
}

function artifactReceipt(item) {
  const verification =
    signedArtifactV1.verifyRegistryOrganizationIdentitySignedArtifactCandidateV1(
      item.reference,
      item.payload,
      item.publicKey,
      item.detachedSignature
    );
  const exact =
    signedArtifactV1.verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
      item.reference,
      item.payload,
      item.publicKey,
      item.detachedSignature,
      verification
    );
  const localPass =
    verification.local_signed_artifact_status === "PASS" &&
    exact.status === "PASS" &&
    exact.verification_status === "BLOCKED" &&
    exact.evidence_signature_verified === true &&
    exact.registry_organization_identity_verified === false;
  return {
    artifact_sha256: item.reference.artifact_sha256,
    evidence_kind: item.reference.evidence_kind,
    evidence_reference_sha256: strictCanonicalHash(item.reference),
    evidence_schema_version: item.reference.evidence_schema_version,
    evidence_signature_verified: localPass,
    local_signed_artifact_status: localPass ? "PASS" : "BLOCK",
    signature_sha256: verification.source.signature_sha256,
    signer_public_key_spki_sha256:
      item.reference.signer_public_key_spki_sha256,
    signer_role: item.reference.signer_role,
    verification_hash: verification.verification_hash,
    verification_status: verification.status,
  };
}

function buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
  pythonEnvelope,
  artifactItems
) {
  if (!isExactPythonVerificationEnvelopeV1(pythonEnvelope)) {
    throw new TypeError(
      "organization-identity Python verification envelope-v1 is not exact"
    );
  }
  const items = normalizeArtifactItems(artifactItems);
  const references = items.map((item) => item.reference);
  const referenceSetHash = strictCanonicalHash({ references });
  const referenceSetBound =
    referenceSetHash ===
    pythonEnvelope.source.evidence_reference_set_sha256;
  const subjectBinding = references.every(
    (reference) =>
      reference.subject_registry_id === pythonEnvelope.source.registry_id &&
      reference.subject_public_key_spki_sha256 ===
        pythonEnvelope.source.public_key_spki_sha256
  );
  const freshnessBinding = references.every(
    (reference) =>
      reference.issued_at_ms <= pythonEnvelope.source.reference_time_ms &&
      pythonEnvelope.source.reference_time_ms < reference.expires_at_ms
  );
  const roles = references.map((reference) => reference.signer_role);
  const signerKeys = references.map(
    (reference) => reference.signer_public_key_spki_sha256
  );
  const artifactHashes = references.map(
    (reference) => reference.artifact_sha256
  );
  const rolesDistinct = new Set(roles).size === EVIDENCE_KINDS.length;
  const signerKeysDistinct =
    new Set(signerKeys).size === EVIDENCE_KINDS.length;
  const artifactHashesDistinct =
    new Set(artifactHashes).size === EVIDENCE_KINDS.length;
  const receipts = items.map(artifactReceipt);
  const allArtifactsVerified = receipts.every(
    (receipt) =>
      receipt.local_signed_artifact_status === "PASS" &&
      receipt.evidence_signature_verified === true
  );
  const checks = [
    {
      blocking: true,
      name: "python_bundle_verification_envelope_v1_exact",
      ok: true,
    },
    {
      blocking: true,
      name: "one_signed_artifact_per_evidence_kind_exact",
      ok: true,
    },
    {
      blocking: true,
      name: "normalized_reference_set_hash_matches_python_envelope",
      ok: referenceSetBound,
    },
    {
      blocking: true,
      name: "all_reference_subjects_match_python_envelope",
      ok: subjectBinding,
    },
    {
      blocking: true,
      name: "all_references_fresh_at_python_envelope_reference_time",
      ok: freshnessBinding,
    },
    {
      blocking: true,
      name: "all_signer_roles_distinct",
      ok: rolesDistinct,
    },
    {
      blocking: true,
      name: "all_signer_public_keys_distinct",
      ok: signerKeysDistinct,
    },
    {
      blocking: true,
      name: "all_artifact_hashes_distinct",
      ok: artifactHashesDistinct,
    },
    {
      blocking: true,
      name: "all_six_signed_artifact_exact_verifiers_pass",
      ok: allArtifactsVerified,
    },
  ];
  const localPass = checks.every((check) => check.ok);
  const localBlockers = checks
    .filter((check) => !check.ok)
    .map(
      (check) =>
        "LOCAL_SIGNED_ARTIFACT_BUNDLE_CHECK_FAILED:" + check.name
    );
  return sealDocument(
    {
      artifacts: receipts,
      authority: lockedAuthority(),
      blockers: [...localBlockers, ...REMAINING_BLOCKERS],
      checks,
      decision: localPass
        ? "SIX_SIGNED_ARTIFACTS_CRYPTOGRAPHICALLY_BOUND_PROCESS_SEMANTICS_SOURCE_ROLE_AND_IDENTITY_UNVERIFIED"
        : "SIX_SIGNED_ARTIFACT_AGGREGATION_BLOCKED_ORGANIZATION_IDENTITY_UNVERIFIED",
      facts: {
        all_artifact_hashes_distinct: artifactHashesDistinct,
        all_evidence_kinds_present: true,
        all_references_fresh: freshnessBinding,
        all_signer_public_keys_distinct: signerKeysDistinct,
        all_signer_roles_distinct: rolesDistinct,
        evidence_payloads_embedded: false,
        evidence_payloads_observed: true,
        evidence_payloads_semantics_verified: false,
        evidence_reference_set_bound: referenceSetBound,
        evidence_signatures_verified: allArtifactsVerified,
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
        subject_identity_bound: subjectBinding,
      },
      local_signed_artifact_bundle_status: localPass
        ? LOCAL_PASS_STATUS
        : "BLOCK",
      schema_version: AGGREGATION_SCHEMA_VERSION,
      source: {
        evidence_reference_count: references.length,
        evidence_reference_set_sha256: referenceSetHash,
        public_key_spki_sha256:
          pythonEnvelope.source.public_key_spki_sha256,
        python_envelope_hash: pythonEnvelope.envelope_hash,
        python_envelope_implementation_sha256:
          PYTHON_ENVELOPE_IMPLEMENTATION_SHA256,
        reference_time_ms: pythonEnvelope.source.reference_time_ms,
        registry_id: pythonEnvelope.source.registry_id,
        signed_artifact_candidate_implementation_sha256:
          SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256,
        trust_domain: pythonEnvelope.source.trust_domain,
      },
      static_fingerprint: AGGREGATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "aggregation_hash"
  );
}

function blockedExactVerification(blocker) {
  return {
    aggregation_document_exactly_rebuilt: false,
    aggregation_status: "UNKNOWN",
    blockers: [blocker],
    current_admission_allowed: false,
    evidence_bundle_admission_allowed: false,
    evidence_payloads_semantics_verified: false,
    evidence_signatures_verified: false,
    external_source_trust_verified: false,
    live_order_allowed: false,
    local_signed_artifact_bundle_status: "UNKNOWN",
    paper_authorized: false,
    presentation_mount_allowed: false,
    python_process_authenticated: false,
    registry_identity_admission_allowed: false,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
    signed_artifact_aggregation_activation_allowed: false,
    signer_role_identity_verified: false,
    status: "BLOCK",
    writer_allowed: false,
  };
}

function verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
  pythonEnvelope,
  artifactItems,
  document
) {
  try {
    const expected =
      buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
        pythonEnvelope,
        artifactItems
      );
    const exact =
      verifySealedDocument(document, "aggregation_hash") &&
      strictCanonicalHash(document) === strictCanonicalHash(expected);
    if (!exact) {
      return blockedExactVerification(
        "SIGNED_ARTIFACT_BUNDLE_AGGREGATION_DOCUMENT_EXACT_REBUILD"
      );
    }
    const localPass =
      expected.local_signed_artifact_bundle_status === LOCAL_PASS_STATUS;
    return {
      aggregation_document_exactly_rebuilt: true,
      aggregation_status: "BLOCKED",
      blockers: localPass
        ? []
        : ["LOCAL_SIGNED_ARTIFACT_BUNDLE_NOT_PASS"],
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      evidence_payloads_semantics_verified: false,
      evidence_signatures_verified: localPass,
      external_source_trust_verified: false,
      live_order_allowed: false,
      local_signed_artifact_bundle_status:
        expected.local_signed_artifact_bundle_status,
      paper_authorized: false,
      presentation_mount_allowed: false,
      python_process_authenticated: false,
      registry_identity_admission_allowed: false,
      registry_organization_identity_verified: false,
      revocation_content_verified: false,
      runtime_gate_activation_allowed: false,
      schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
      signed_artifact_aggregation_activation_allowed: false,
      signer_role_identity_verified: false,
      status: localPass ? "PASS" : "BLOCK",
      writer_allowed: false,
    };
  } catch (_error) {
    return blockedExactVerification(
      "SIGNED_ARTIFACT_BUNDLE_AGGREGATION_INPUT_INVALID"
    );
  }
}

module.exports = {
  AGGREGATION_SCHEMA_VERSION,
  AGGREGATION_STATIC_FINGERPRINT,
  EVIDENCE_KINDS,
  EXACT_VERIFICATION_SCHEMA_VERSION,
  LOCAL_PASS_STATUS,
  PYTHON_ENVELOPE_IMPLEMENTATION_SHA256,
  PYTHON_ENVELOPE_SCHEMA_VERSION,
  PYTHON_ENVELOPE_STATIC_FINGERPRINT,
  SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1,
  isExactPythonVerificationEnvelopeV1,
  verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1,
};
