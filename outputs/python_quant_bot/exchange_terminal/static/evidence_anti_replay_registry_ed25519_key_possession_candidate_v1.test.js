"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const candidateV1 = require("./evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js");

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function fileHash(...parts) {
  return hash(fs.readFileSync(path.join(__dirname, ...parts)));
}

function publicKeyHash(publicKey) {
  return hash(publicKey.export({ type: "spki", format: "der" }));
}

function preregistration(publicKey, label = "registry") {
  return canonical.sealDocument(
    {
      authority: {
        current_admission_allowed: false,
        live_order_allowed: false,
        paper_authorized: false,
        post_registration_receipt_issuance_allowed: false,
        presentation_mount_allowed: false,
        runtime_gate_activation_allowed: false,
        writer_allowed: false,
      },
      blockers: [
        "REGISTRY_KEY_POSSESSION_UNVERIFIED",
        "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
        "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
        "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
        "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
        "TRUSTED_REGISTRY_TIME_UNVERIFIED",
        "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
        "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
      ],
      checks: [
        "registry_identity_fields_preregistered",
        "registry_ed25519_public_key_hash_preregistered",
        "adapter_protocol_and_target_schemas_exact",
        "external_identity_and_conformance_not_self_claimed",
      ].map((name) => ({ blocking: true, name, ok: true })),
      decision:
        "REGISTRY_IDENTITY_PREREGISTERED_KEY_POSSESSION_IDENTITY_AND_EXTERNAL_CONFORMANCE_UNVERIFIED",
      facts: {
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
      },
      identity: {
        key_algorithm: "Ed25519",
        operator_identity_claim: `synthetic-${label}-operator-claim`,
        public_key_spki_sha256: publicKeyHash(publicKey),
        registry_id: `synthetic.${label}.registry`,
        trust_domain: `synthetic.${label}.test`,
      },
      requirements: [
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
      ],
      schema_version: candidateV1.PREREGISTRATION_SCHEMA_VERSION,
      source: {
        adapter_protocol_version: "anti-replay-compare-and-consume-port-v1",
        anti_replay_namespace:
          "portfolio-risk-downside-tail-post-registration-execution-receipt-v5",
        command_schema_version: "anti-replay-compare-and-consume-command-v1",
        consumption_request_schema_version:
          "portfolio-risk-post-registration-anti-replay-consumption-request-v1",
        reference_model_implementation_sha256:
          "c56055d08b8ba6cc7f35437bbea7e042618b02e0d5ffed66e702f18103f8d587",
        result_schema_version: "anti-replay-compare-and-consume-result-v1",
        strict_canonical_implementation_sha256:
          candidateV1.PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        target_consumption_receipt_schema_version:
          "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1",
        target_post_registration_receipt_schema_version:
          "portfolio-risk-downside-tail-consumer-post-registration-execution-receipt-v5",
      },
      static_fingerprint: candidateV1.PREREGISTRATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "preregistration_hash"
  );
}

function fixture(label = "registry") {
  const pair = crypto.generateKeyPairSync("ed25519");
  const document = preregistration(pair.publicKey, label);
  const policy = candidateV1.buildAntiReplayRegistryKeyPossessionPolicyV1(document);
  const rawNonce = crypto.randomBytes(32);
  const challenge = candidateV1.buildAntiReplayRegistryKeyPossessionChallengeV1(
    policy,
    rawNonce
  );
  const signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(challenge), "utf8"),
    pair.privateKey
  );
  return { challenge, pair, policy, preregistration: document, rawNonce, signature };
}

function verify(value, overrides = {}) {
  return candidateV1.verifyAntiReplayRegistryKeyPossessionCandidateV1(
    overrides.preregistration || value.preregistration,
    overrides.policy || value.policy,
    overrides.challenge || value.challenge,
    overrides.rawNonce || value.rawNonce,
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
    fileHash("..", "application", "anti_replay_registry_identity_preregistration_v1.py"),
    candidateV1.PYTHON_PREREGISTRATION_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash("..", "services", "strict_canonical_json_hash.py"),
    candidateV1.PYTHON_STRICT_CANONICAL_IMPLEMENTATION_SHA256
  );
  assert.equal(
    candidateV1.VERIFICATION_SCHEMA_VERSION,
    "anti-replay-registry-ed25519-key-possession-verification-candidate-v1"
  );
});

test("exact preregistration creates a blocked local-only policy", () => {
  const value = fixture("policy");
  assert.equal(value.policy.status, "BLOCKED");
  assert.equal(value.policy.facts.registry_key_possession_verified, false);
  assert.equal(value.policy.facts.registry_organization_identity_verified, false);
  assert.equal(value.policy.authority.writer_allowed, false);
});

test("challenge binds nonce commitment without embedding raw nonce", () => {
  const value = fixture("challenge");
  assert.equal(value.challenge.source.nonce_commitment_sha256, hash(value.rawNonce));
  assert.equal(value.challenge.facts.raw_nonce_embedded, false);
  assert.equal(JSON.stringify(value.challenge).includes(value.rawNonce.toString("hex")), false);
});

test("valid detached signature proves local preregistered key possession only", () => {
  const value = fixture("valid");
  const result = verify(value);
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.local_registry_key_possession_status, "PASS");
  assert.equal(result.facts.registry_key_possession_verified, true);
  assert.equal(result.facts.registry_organization_identity_verified, false);
  assert.equal(result.facts.adapter_conformance_verified, false);
  assert.equal(result.facts.external_linearizability_verified, false);
});

test("public KeyObject input preserves the preregistered SPKI hash", () => {
  const value = fixture("key-object");
  const result = verify(value);
  assert.equal(
    result.source.public_key_spki_sha256,
    value.preregistration.identity.public_key_spki_sha256
  );
});

test("public-key substitution blocks local possession", () => {
  const value = fixture("key-substitution");
  const other = crypto.generateKeyPairSync("ed25519");
  const result = verify(value, { publicKey: other.publicKey });
  assert.equal(result.local_registry_key_possession_status, "BLOCK");
  assert.equal(result.facts.preregistered_public_key_hash_matched, false);
  assert.ok(
    result.blockers.includes(
      "LOCAL_REGISTRY_KEY_POSSESSION_CHECK_FAILED:ed25519_public_key_hash_matches_preregistration"
    )
  );
});

test("signature substitution blocks local possession", () => {
  const value = fixture("signature-substitution");
  const signature = Buffer.from(value.signature);
  signature[0] ^= 0xff;
  const result = verify(value, { signature });
  assert.equal(result.local_registry_key_possession_status, "BLOCK");
  assert.ok(
    result.blockers.includes(
      "LOCAL_REGISTRY_KEY_POSSESSION_CHECK_FAILED:ed25519_detached_signature_verified"
    )
  );
});

test("nonce mismatch blocks challenge exactness", () => {
  const value = fixture("nonce-mismatch");
  const result = verify(value, { rawNonce: crypto.randomBytes(32) });
  assert.equal(result.local_registry_key_possession_status, "BLOCK");
  assert.ok(
    result.blockers.includes(
      "LOCAL_REGISTRY_KEY_POSSESSION_CHECK_FAILED:registry_key_possession_challenge_v1_exact"
    )
  );
});

test("resealed preregistration schema alias is rejected", () => {
  const value = fixture("schema-alias");
  const body = structuredClone(value.preregistration);
  delete body.preregistration_hash;
  body.schema_version = `${candidateV1.PREREGISTRATION_SCHEMA_VERSION}.0`;
  const alias = canonical.sealDocument(body, "preregistration_hash");
  assert.throws(
    () => candidateV1.buildAntiReplayRegistryKeyPossessionPolicyV1(alias),
    /not exact/
  );
});

test("public exact verifier PASS preserves blocked document and authority", () => {
  const value = fixture("exact-pass");
  const document = verify(value);
  const exact =
    candidateV1.verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1(
      value.preregistration,
      value.policy,
      value.challenge,
      value.rawNonce,
      value.pair.publicKey,
      value.signature,
      document
    );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.verification_status, "BLOCKED");
  assert.equal(exact.registry_key_possession_verified, true);
  assert.equal(exact.registry_organization_identity_verified, false);
  assert.equal(exact.current_admission_allowed, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
  assert.equal(exact.writer_allowed, false);
});

test("exact local failure stays BLOCK rather than becoming verifier PASS", () => {
  const value = fixture("exact-local-block");
  const signature = Buffer.from(value.signature);
  signature[1] ^= 0xff;
  const document = verify(value, { signature });
  const exact =
    candidateV1.verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1(
      value.preregistration,
      value.policy,
      value.challenge,
      value.rawNonce,
      value.pair.publicKey,
      signature,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.verification_document_exactly_rebuilt, true);
  assert.equal(exact.verification_status, "BLOCKED");
  assert.equal(exact.local_registry_key_possession_status, "BLOCK");
});

test("tampered verification document fails exact reconstruction", () => {
  const value = fixture("verification-tamper");
  const document = verify(value);
  document.facts.registry_organization_identity_verified = true;
  const exact =
    candidateV1.verifyAntiReplayRegistryKeyPossessionVerificationDocumentV1(
      value.preregistration,
      value.policy,
      value.challenge,
      value.rawNonce,
      value.pair.publicKey,
      value.signature,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.verification_document_exactly_rebuilt, false);
  assert.equal(exact.verification_status, "UNKNOWN");
});

test("verification and attestation contain no raw or cryptographic material", () => {
  const value = fixture("material-boundary");
  const attestation = candidateV1.buildAntiReplayRegistryDetachedAttestationV1(
    value.preregistration,
    value.policy,
    value.challenge,
    value.pair.publicKey,
    value.signature
  );
  const document = verify(value);
  const serialized = JSON.stringify({ attestation, document });
  assert.equal(serialized.includes(value.signature.toString("base64")), false);
  assert.equal(serialized.includes(value.rawNonce.toString("base64")), false);
  assert.equal(serialized.includes("privateKey"), false);
  assert.equal(document.facts.private_key_material_received, false);
});
