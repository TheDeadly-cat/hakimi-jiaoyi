"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const candidateV1 = require("./evidence_anti_replay_registry_organization_identity_signed_artifact_candidate_v1.js");

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function fileHash(...parts) {
  return hash(fs.readFileSync(path.join(__dirname, ...parts)));
}

function publicKeyHash(publicKey) {
  return hash(publicKey.export({ type: "spki", format: "der" }));
}

function metadata(publicKey, label = "signed-artifact") {
  return {
    evidence_kind: "ORGANIZATION_REGISTRY_ATTESTATION",
    evidence_schema_version: "registry-organization-authority-attestation-v1",
    expires_at_ms: 20_000_000,
    issued_at_ms: 10_000_000,
    signature_algorithm: "ed25519",
    signer_public_key_spki_sha256: publicKeyHash(publicKey),
    signer_role: "organization_registry_authority",
    subject_public_key_spki_sha256: hash(
      Buffer.from("synthetic-subject-key:" + label, "utf8")
    ),
    subject_registry_id: "synthetic." + label + ".registry",
  };
}

function fixture(label = "signed-artifact") {
  const pair = crypto.generateKeyPairSync("ed25519");
  const referenceMetadata = metadata(pair.publicKey, label);
  const body = {
    record_sha256: hash(Buffer.from("synthetic-record:" + label, "utf8")),
    record_type: "synthetic_organization_registry_record",
    synthetic: true,
  };
  const payload =
    candidateV1.buildRegistryOrganizationIdentitySignedEvidencePayloadV1(
      referenceMetadata,
      body
    );
  const reference = {
    ...referenceMetadata,
    artifact_sha256: canonical.strictCanonicalHash(payload),
    schema_version: candidateV1.EVIDENCE_REFERENCE_SCHEMA_VERSION,
  };
  const signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    pair.privateKey
  );
  return { body, pair, payload, reference, referenceMetadata, signature };
}

function verify(value, overrides = {}) {
  return candidateV1.verifyRegistryOrganizationIdentitySignedArtifactCandidateV1(
    overrides.reference || value.reference,
    overrides.payload || value.payload,
    overrides.publicKey || value.pair.publicKey,
    overrides.signature || value.signature
  );
}

test("exports exact schemas and pinned dependencies", () => {
  assert.equal(
    fileHash("strict_canonical_json_v1.js"),
    candidateV1.STRICT_CANONICAL_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash("..", "interfaces", "registry_organization_identity.py"),
    candidateV1.PYTHON_EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256
  );
  assert.equal(
    candidateV1.VERIFICATION_SCHEMA_VERSION,
    "registry-organization-identity-signed-artifact-verification-candidate-v1"
  );
});

test("valid detached signature proves only local artifact binding", () => {
  const value = fixture("valid-local");
  const result = verify(value);
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.local_signed_artifact_status, "PASS");
  assert.equal(result.facts.evidence_payload_observed, true);
  assert.equal(result.facts.evidence_signature_verified, true);
  assert.equal(result.facts.evidence_payload_semantics_verified, false);
  assert.equal(result.facts.external_source_trust_verified, false);
  assert.equal(result.facts.signer_role_identity_verified, false);
  assert.equal(result.facts.registry_organization_identity_verified, false);
  assert.equal(Object.values(result.authority).some(Boolean), false);
});

test("artifact substitution blocks even when the substituted body is resigned", () => {
  const value = fixture("artifact-substitution");
  const payload = structuredClone(value.payload);
  payload.evidence_body.record_sha256 = hash(Buffer.from("substituted-record"));
  const signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    value.pair.privateKey
  );
  const result = verify(value, { payload, signature });
  assert.equal(result.local_signed_artifact_status, "BLOCK");
  assert.equal(result.facts.artifact_hash_matched, false);
  assert.ok(
    result.blockers.includes(
      "LOCAL_SIGNED_ARTIFACT_CHECK_FAILED:strict_canonical_artifact_hash_matches_reference"
    )
  );
});

test("subject substitution blocks despite a matching artifact hash and signature", () => {
  const value = fixture("subject-substitution");
  const payload = structuredClone(value.payload);
  payload.subject.registry_id = "synthetic.substituted.registry";
  const reference = {
    ...value.reference,
    artifact_sha256: canonical.strictCanonicalHash(payload),
  };
  const signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    value.pair.privateKey
  );
  const result = verify(value, { payload, reference, signature });
  assert.equal(result.local_signed_artifact_status, "BLOCK");
  assert.equal(result.facts.artifact_hash_matched, true);
  assert.equal(result.facts.evidence_payload_schema_bound, false);
});

test("public-key substitution blocks signer-key binding", () => {
  const value = fixture("key-substitution");
  const other = crypto.generateKeyPairSync("ed25519");
  const result = verify(value, { publicKey: other.publicKey });
  assert.equal(result.local_signed_artifact_status, "BLOCK");
  assert.equal(result.facts.signer_public_key_hash_matched, false);
});

test("signature substitution blocks local verification", () => {
  const value = fixture("signature-substitution");
  const signature = Buffer.from(value.signature);
  signature[0] ^= 0xff;
  const result = verify(value, { signature });
  assert.equal(result.local_signed_artifact_status, "BLOCK");
  assert.equal(result.facts.evidence_signature_verified, false);
});

test("reference schema aliases are rejected", () => {
  const value = fixture("schema-alias");
  const reference = {
    ...value.reference,
    schema_version: candidateV1.EVIDENCE_REFERENCE_SCHEMA_VERSION + ".0",
  };
  assert.throws(() => verify(value, { reference }), /not exact/);
});

test("private-key and credential fields are rejected before payload creation", () => {
  const value = fixture("forbidden-body");
  assert.throws(
    () =>
      candidateV1.buildRegistryOrganizationIdentitySignedEvidencePayloadV1(
        value.referenceMetadata,
        { nested: { private_key: "synthetic-forbidden" } }
      ),
    /invalid or unsafe/
  );
});

test("public exact verifier PASS preserves blocked identity and authority", () => {
  const value = fixture("exact-pass");
  const document = verify(value);
  const exact =
    candidateV1.verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
      value.reference,
      value.payload,
      value.pair.publicKey,
      value.signature,
      document
    );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.verification_status, "BLOCKED");
  assert.equal(exact.evidence_signature_verified, true);
  assert.equal(exact.evidence_payload_semantics_verified, false);
  assert.equal(exact.external_source_trust_verified, false);
  assert.equal(exact.registry_organization_identity_verified, false);
  assert.equal(exact.current_admission_allowed, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
  assert.equal(exact.writer_allowed, false);
});

test("exact local signature failure remains BLOCK and BLOCKED", () => {
  const value = fixture("exact-local-block");
  const signature = Buffer.from(value.signature);
  signature[1] ^= 0xff;
  const document = verify(value, { signature });
  const exact =
    candidateV1.verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
      value.reference,
      value.payload,
      value.pair.publicKey,
      signature,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.verification_document_exactly_rebuilt, true);
  assert.equal(exact.verification_status, "BLOCKED");
  assert.equal(exact.local_signed_artifact_status, "BLOCK");
});

test("tampered promotion becomes BLOCK and UNKNOWN", () => {
  const value = fixture("tampered-promotion");
  const document = verify(value);
  document.facts.registry_organization_identity_verified = true;
  const exact =
    candidateV1.verifyRegistryOrganizationIdentitySignedArtifactVerificationDocumentV1(
      value.reference,
      value.payload,
      value.pair.publicKey,
      value.signature,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.verification_document_exactly_rebuilt, false);
  assert.equal(exact.verification_status, "UNKNOWN");
});

test("verification embeds no body, public-key, signature, or private-key material", () => {
  const value = fixture("material-boundary");
  value.payload.evidence_body.marker = "synthetic-sensitive-body-marker";
  value.reference.artifact_sha256 = canonical.strictCanonicalHash(value.payload);
  value.signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(value.payload), "utf8"),
    value.pair.privateKey
  );
  const document = verify(value);
  const serialized = JSON.stringify(document);
  const publicDer = value.pair.publicKey.export({ type: "spki", format: "der" });
  const privateDer = value.pair.privateKey.export({
    type: "pkcs8",
    format: "der",
  });
  assert.equal(serialized.includes("synthetic-sensitive-body-marker"), false);
  assert.equal(serialized.includes(publicDer.toString("base64")), false);
  assert.equal(serialized.includes(value.signature.toString("base64")), false);
  assert.equal(serialized.includes(privateDer.toString("base64")), false);
  assert.equal(serialized.includes(privateDer.toString("hex")), false);
  assert.equal(document.facts.evidence_payload_embedded, false);
  assert.equal(document.facts.public_key_material_embedded, false);
  assert.equal(document.facts.signature_material_embedded, false);
  assert.equal(document.facts.private_key_material_received, false);
});
