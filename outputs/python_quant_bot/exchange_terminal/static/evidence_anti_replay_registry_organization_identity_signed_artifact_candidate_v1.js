"use strict";

const crypto = require("node:crypto");
const {
  isPlainRecord,
  sealDocument,
  strictCanonicalHash,
  strictCanonicalStringify,
  verifySealedDocument,
} = require("./strict_canonical_json_v1.js");

const EVIDENCE_REFERENCE_SCHEMA_VERSION =
  "registry-organization-identity-evidence-reference-v1";
const VERIFICATION_SCHEMA_VERSION =
  "registry-organization-identity-signed-artifact-verification-candidate-v1";
const VERIFICATION_STATIC_FINGERPRINT =
  "20260823-registry-organization-identity-signed-artifact-candidate-v1-lock-1";
const EXACT_VERIFICATION_SCHEMA_VERSION =
  "registry-organization-identity-signed-artifact-exact-rebuild-v1";
const SIGNED_PAYLOAD_CONTEXT =
  "STRICT_CANONICAL_REGISTRY_ORGANIZATION_IDENTITY_EVIDENCE_ARTIFACT_V1";

const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256 =
  "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f";

const HASH_PATTERN = /^[0-9a-f]{64}$/;
const IDENTIFIER_PATTERN = /^[a-z0-9][a-z0-9._:-]{2,127}$/;
const MAX_EVIDENCE_BODY_BYTES = 65_536;
const EXPECTED_EVIDENCE = Object.freeze({
  ORGANIZATION_REGISTRY_ATTESTATION: Object.freeze({
    schema: "registry-organization-authority-attestation-v1",
    signerRole: "organization_registry_authority",
  }),
  DOMAIN_CONTROL_ATTESTATION: Object.freeze({
    schema: "registry-domain-control-attestation-v1",
    signerRole: "domain_control_auditor",
  }),
  KEY_GOVERNANCE_EVALUATION: Object.freeze({
    schema: "provider-identity-witness-conformance-key-governance-evaluation-v1",
    signerRole: "key_governance_auditor",
  }),
  AUDITOR_PROVENANCE_EVALUATION: Object.freeze({
    schema: "provider-identity-auditor-provenance-suite-reproducibility-evaluation-v1",
    signerRole: "provenance_registry_authority",
  }),
  ARTIFACT_TRANSPARENCY_EVALUATION: Object.freeze({
    schema: "provider-identity-artifact-transparency-availability-evaluation-v1",
    signerRole: "transparency_log_authority",
  }),
  REVOCATION_STATUS_RECEIPT: Object.freeze({
    schema: "registry-revocation-status-receipt-v1",
    signerRole: "revocation_authority",
  }),
});
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
  "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
  "SIGNER_ROLE_IDENTITY_UNVERIFIED",
  "EXTERNAL_SOURCE_TRUST_UNPROVEN",
  "REVOCATION_CONTENT_UNVERIFIED",
  "SIX_REFERENCE_SIGNATURE_AGGREGATION_NOT_IMPLEMENTED",
  "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
]);
const FORBIDDEN_BODY_KEYS = new Set([
  "credential",
  "credentials",
  "detached_signature",
  "private_key",
  "private_key_material",
  "raw_signature",
  "secret",
  "signature_material",
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

function isIdentifier(value) {
  return typeof value === "string" && IDENTIFIER_PATTERN.test(value);
}

function isTimestamp(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function lockedAuthority() {
  return Object.fromEntries(AUTHORITY_KEYS.map((key) => [key, false]));
}

function isExactEvidenceReferenceV1(value) {
  if (
    !hasExactKeys(value, [
      "artifact_sha256",
      "evidence_kind",
      "evidence_schema_version",
      "expires_at_ms",
      "issued_at_ms",
      "schema_version",
      "signature_algorithm",
      "signer_public_key_spki_sha256",
      "signer_role",
      "subject_public_key_spki_sha256",
      "subject_registry_id",
    ])
  ) {
    return false;
  }
  const expected = EXPECTED_EVIDENCE[value.evidence_kind];
  return Boolean(
    expected &&
      value.evidence_schema_version === expected.schema &&
      value.signer_role === expected.signerRole &&
      value.signature_algorithm === "ed25519" &&
      value.schema_version === EVIDENCE_REFERENCE_SCHEMA_VERSION &&
      isHash(value.artifact_sha256) &&
      isHash(value.signer_public_key_spki_sha256) &&
      isHash(value.subject_public_key_spki_sha256) &&
      isIdentifier(value.subject_registry_id) &&
      isTimestamp(value.issued_at_ms) &&
      isTimestamp(value.expires_at_ms) &&
      value.expires_at_ms > value.issued_at_ms
  );
}

function isExactReferenceMetadataV1(value) {
  if (
    !hasExactKeys(value, [
      "evidence_kind",
      "evidence_schema_version",
      "expires_at_ms",
      "issued_at_ms",
      "signature_algorithm",
      "signer_public_key_spki_sha256",
      "signer_role",
      "subject_public_key_spki_sha256",
      "subject_registry_id",
    ])
  ) {
    return false;
  }
  return isExactEvidenceReferenceV1({
    ...value,
    artifact_sha256: "0".repeat(64),
    schema_version: EVIDENCE_REFERENCE_SCHEMA_VERSION,
  });
}

function containsForbiddenBodyKey(value) {
  if (Array.isArray(value)) {
    return value.some(containsForbiddenBodyKey);
  }
  if (!isPlainRecord(value)) {
    return false;
  }
  return Object.entries(value).some(
    ([key, child]) =>
      FORBIDDEN_BODY_KEYS.has(key.toLowerCase()) ||
      containsForbiddenBodyKey(child)
  );
}

function isBoundedEvidenceBody(value) {
  if (
    !isPlainRecord(value) ||
    Object.keys(value).length === 0 ||
    containsForbiddenBodyKey(value)
  ) {
    return false;
  }
  try {
    return (
      Buffer.byteLength(strictCanonicalStringify(value), "utf8") <=
      MAX_EVIDENCE_BODY_BYTES
    );
  } catch (_error) {
    return false;
  }
}

function buildRegistryOrganizationIdentitySignedEvidencePayloadV1(
  referenceMetadata,
  evidenceBody
) {
  if (!isExactReferenceMetadataV1(referenceMetadata)) {
    throw new TypeError("organization-identity evidence metadata is not exact");
  }
  if (!isBoundedEvidenceBody(evidenceBody)) {
    throw new TypeError("organization-identity evidence body is invalid or unsafe");
  }
  return {
    evidence_body: evidenceBody,
    evidence_kind: referenceMetadata.evidence_kind,
    expires_at_ms: referenceMetadata.expires_at_ms,
    issued_at_ms: referenceMetadata.issued_at_ms,
    schema_version: referenceMetadata.evidence_schema_version,
    signature_algorithm: referenceMetadata.signature_algorithm,
    signed_payload_context: SIGNED_PAYLOAD_CONTEXT,
    signer: {
      public_key_spki_sha256:
        referenceMetadata.signer_public_key_spki_sha256,
      role: referenceMetadata.signer_role,
    },
    subject: {
      public_key_spki_sha256:
        referenceMetadata.subject_public_key_spki_sha256,
      registry_id: referenceMetadata.subject_registry_id,
    },
  };
}

function isExactSignedEvidencePayloadV1(value) {
  if (
    !hasExactKeys(value, [
      "evidence_body",
      "evidence_kind",
      "expires_at_ms",
      "issued_at_ms",
      "schema_version",
      "signature_algorithm",
      "signed_payload_context",
      "signer",
      "subject",
    ]) ||
    !hasExactKeys(value.signer, ["public_key_spki_sha256", "role"]) ||
    !hasExactKeys(value.subject, ["public_key_spki_sha256", "registry_id"]) ||
    !isBoundedEvidenceBody(value.evidence_body)
  ) {
    return false;
  }
  const expected = EXPECTED_EVIDENCE[value.evidence_kind];
  return Boolean(
    expected &&
      value.schema_version === expected.schema &&
      value.signer.role === expected.signerRole &&
      value.signature_algorithm === "ed25519" &&
      value.signed_payload_context === SIGNED_PAYLOAD_CONTEXT &&
      isHash(value.signer.public_key_spki_sha256) &&
      isHash(value.subject.public_key_spki_sha256) &&
      isIdentifier(value.subject.registry_id) &&
      isTimestamp(value.issued_at_ms) &&
      isTimestamp(value.expires_at_ms) &&
      value.expires_at_ms > value.issued_at_ms
  );
}

function payloadBindsReference(payload, reference) {
  return (
    payload.evidence_kind === reference.evidence_kind &&
    payload.schema_version === reference.evidence_schema_version &&
    payload.signature_algorithm === reference.signature_algorithm &&
    payload.signer.role === reference.signer_role &&
    payload.signer.public_key_spki_sha256 ===
      reference.signer_public_key_spki_sha256 &&
    payload.subject.registry_id === reference.subject_registry_id &&
    payload.subject.public_key_spki_sha256 ===
      reference.subject_public_key_spki_sha256 &&
    payload.issued_at_ms === reference.issued_at_ms &&
    payload.expires_at_ms === reference.expires_at_ms
  );
}

function hashBuffer(value) {
  if (!Buffer.isBuffer(value)) {
    throw new TypeError("sha256 binary input must be a Buffer");
  }
  return crypto.createHash("sha256").update(value).digest("hex");
}

function publicKeyInfo(value) {
  if (
    !(value instanceof crypto.KeyObject) ||
    value.type !== "public" ||
    value.asymmetricKeyType !== "ed25519"
  ) {
    return null;
  }
  const spki = value.export({ type: "spki", format: "der" });
  return { key: value, spkiSha256: hashBuffer(spki) };
}

function signatureBuffer(value) {
  const signature = Buffer.isBuffer(value)
    ? value
    : value instanceof Uint8Array
      ? Buffer.from(value)
      : null;
  return signature && signature.length === 64 ? signature : null;
}

function verificationFacts(localPass, values) {
  return {
    artifact_hash_matched: values.artifactHashMatched,
    evidence_payload_embedded: false,
    evidence_payload_observed: true,
    evidence_payload_schema_bound: values.payloadBinding,
    evidence_payload_semantics_verified: false,
    evidence_signature_verified: localPass,
    external_source_trust_verified: false,
    network_accessed: false,
    private_key_material_received: false,
    public_key_material_embedded: false,
    public_key_material_received: true,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_assets_accessed: false,
    signature_material_embedded: false,
    signature_material_received: true,
    signer_public_key_hash_matched: values.keyHashMatched,
    signer_role_identity_verified: false,
  };
}

function verifyRegistryOrganizationIdentitySignedArtifactCandidateV1(
  reference,
  payload,
  publicKey,
  detachedSignature
) {
  if (!isExactEvidenceReferenceV1(reference)) {
    throw new TypeError("organization-identity evidence reference-v1 is not exact");
  }
  if (!isPlainRecord(payload) || !isBoundedEvidenceBody(payload.evidence_body)) {
    throw new TypeError("organization-identity evidence payload is invalid");
  }
  const keyInfo = publicKeyInfo(publicKey);
  const signature = signatureBuffer(detachedSignature);
  if (!keyInfo || !signature) {
    throw new TypeError("public Ed25519 key or detached signature is invalid");
  }
  const canonicalPayload = strictCanonicalStringify(payload);
  const artifactHash = strictCanonicalHash(payload);
  const payloadShapeExact = isExactSignedEvidencePayloadV1(payload);
  const payloadBinding =
    payloadShapeExact && payloadBindsReference(payload, reference);
  const artifactHashMatched = artifactHash === reference.artifact_sha256;
  const keyHashMatched =
    keyInfo.spkiSha256 === reference.signer_public_key_spki_sha256;
  const signatureVerified = crypto.verify(
    null,
    Buffer.from(canonicalPayload, "utf8"),
    keyInfo.key,
    signature
  );
  const checks = [
    { blocking: true, name: "evidence_reference_v1_exact", ok: true },
    {
      blocking: true,
      name: "signed_evidence_payload_shape_exact",
      ok: payloadShapeExact,
    },
    {
      blocking: true,
      name: "signed_evidence_payload_binds_reference",
      ok: payloadBinding,
    },
    {
      blocking: true,
      name: "strict_canonical_artifact_hash_matches_reference",
      ok: artifactHashMatched,
    },
    {
      blocking: true,
      name: "ed25519_signer_public_key_hash_matches_reference",
      ok: keyHashMatched,
    },
    {
      blocking: true,
      name: "ed25519_detached_signature_verified",
      ok: signatureVerified,
    },
  ];
  const localPass = checks.every((check) => check.ok);
  const localBlockers = checks
    .filter((check) => !check.ok)
    .map(
      (check) =>
        "LOCAL_SIGNED_ARTIFACT_CHECK_FAILED:" + check.name
    );
  const values = { artifactHashMatched, keyHashMatched, payloadBinding };
  return sealDocument(
    {
      authority: lockedAuthority(),
      blockers: [...localBlockers, ...REMAINING_BLOCKERS],
      checks,
      decision: localPass
        ? "SIGNED_ARTIFACT_CRYPTOGRAPHICALLY_BOUND_SOURCE_ROLE_AND_ORGANIZATION_IDENTITY_UNVERIFIED"
        : "SIGNED_ARTIFACT_LOCAL_CRYPTOGRAPHIC_BINDING_BLOCKED_ORGANIZATION_IDENTITY_UNVERIFIED",
      facts: verificationFacts(localPass, values),
      local_signed_artifact_status: localPass ? "PASS" : "BLOCK",
      schema_version: VERIFICATION_SCHEMA_VERSION,
      source: {
        artifact_sha256: artifactHash,
        evidence_body_sha256: strictCanonicalHash(payload.evidence_body),
        evidence_kind: reference.evidence_kind,
        evidence_reference_sha256: strictCanonicalHash(reference),
        evidence_reference_schema_version:
          EVIDENCE_REFERENCE_SCHEMA_VERSION,
        evidence_schema_version: reference.evidence_schema_version,
        expires_at_ms: reference.expires_at_ms,
        issued_at_ms: reference.issued_at_ms,
        key_algorithm: "Ed25519",
        python_evidence_reference_implementation_sha256:
          PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256,
        signature_sha256: hashBuffer(signature),
        signed_payload_context: SIGNED_PAYLOAD_CONTEXT,
        signer_public_key_spki_sha256: keyInfo.spkiSha256,
        signer_role: reference.signer_role,
        subject_public_key_spki_sha256:
          reference.subject_public_key_spki_sha256,
        subject_registry_id: reference.subject_registry_id,
      },
      static_fingerprint: VERIFICATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "verification_hash"
  );
}

function blockedExactVerification(blocker) {
  return {
    blockers: [blocker],
    current_admission_allowed: false,
    evidence_bundle_admission_allowed: false,
    evidence_payload_observed: false,
    evidence_payload_semantics_verified: false,
    evidence_signature_verified: false,
    external_source_trust_verified: false,
    live_order_allowed: false,
    local_signed_artifact_status: "UNKNOWN",
    paper_authorized: false,
    presentation_mount_allowed: false,
    registry_identity_admission_allowed: false,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
    signer_role_identity_verified: false,
    status: "BLOCK",
    verification_document_exactly_rebuilt: false,
    verification_status: "UNKNOWN",
    writer_allowed: false,
  };
}

function verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
  reference,
  payload,
  publicKey,
  detachedSignature,
  document
) {
  try {
    const expected =
      verifyRegistryOrganizationIdentitySignedArtifactCandidateV1(
        reference,
        payload,
        publicKey,
        detachedSignature
      );
    const exact =
      verifySealedDocument(document, "verification_hash") &&
      strictCanonicalHash(document) === strictCanonicalHash(expected);
    if (!exact) {
      return blockedExactVerification(
        "SIGNED_ARTIFACT_VERIFICATION_DOCUMENT_EXACT_REBUILD"
      );
    }
    const localPass = expected.local_signed_artifact_status === "PASS";
    return {
      blockers: localPass ? [] : ["LOCAL_SIGNED_ARTIFACT_NOT_PASS"],
      current_admission_allowed: false,
      evidence_bundle_admission_allowed: false,
      evidence_payload_observed: true,
      evidence_payload_semantics_verified: false,
      evidence_signature_verified: localPass,
      external_source_trust_verified: false,
      live_order_allowed: false,
      local_signed_artifact_status: expected.local_signed_artifact_status,
      paper_authorized: false,
      presentation_mount_allowed: false,
      registry_identity_admission_allowed: false,
      registry_organization_identity_verified: false,
      revocation_content_verified: false,
      runtime_gate_activation_allowed: false,
      schema_version: EXACT_VERIFICATION_SCHEMA_VERSION,
      signer_role_identity_verified: false,
      status: localPass ? "PASS" : "BLOCK",
      verification_document_exactly_rebuilt: true,
      verification_status: "BLOCKED",
      writer_allowed: false,
    };
  } catch (_error) {
    return blockedExactVerification(
      "SIGNED_ARTIFACT_VERIFICATION_INPUT_INVALID"
    );
  }
}

module.exports = {
  EVIDENCE_REFERENCE_SCHEMA_VERSION,
  EXACT_VERIFICATION_SCHEMA_VERSION,
  MAX_EVIDENCE_BODY_BYTES,
  PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256,
  SIGNED_PAYLOAD_CONTEXT,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  VERIFICATION_SCHEMA_VERSION,
  VERIFICATION_STATIC_FINGERPRINT,
  buildRegistryOrganizationIdentitySignedEvidencePayloadV1,
  isExactEvidenceReferenceV1,
  verifyRegistryOrganizationIdentitySignedArtifactCandidateV1,
  verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1,
};
