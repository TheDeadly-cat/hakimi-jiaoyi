"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const test = require("node:test");
const canonical = require("./strict_canonical_json_v1.js");
const witnessV2 = require("./evidence_portfolio_risk_post_registration_execution_witness_signature_candidate_v2.js");

const UNDERLYING_AUTHORITY = {
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
};
const ENVELOPE_AUTHORITY = {
  ...UNDERLYING_AUTHORITY,
  witness_candidate_activation_allowed: false,
};

function hash(label) {
  return crypto.createHash("sha256").update(label).digest("hex");
}

function checks(names) {
  return names.map((name) => ({ name, ok: true, blocking: true }));
}

function fixture(state = "CLEAR") {
  const rawNonce = `synthetic-witness-v2-raw-nonce-${state}-0123456789abcdef`;
  const commitment = hash(rawNonce);
  const issuanceId = `node-witness-v2-${state.toLowerCase()}-0001`;
  const source = {
    registration_v7_hash: hash(`registration-${state}`),
    execution_evidence_v4_hash: hash(`evidence-${state}`),
    pre_registration_receipt_v4_hash: hash(`receipt-${state}`),
    projection_v6_hash: hash(`projection-${state}`),
    execution_preregistration_v1_hash: hash(`execution-prereg-${state}`),
    execution_semantic_state: state,
  };
  const scopeBase = {
    schema_version: "portfolio-risk-post-registration-anti-replay-scope-v1",
    namespace:
      "portfolio-risk-downside-tail-post-registration-execution-receipt-v5",
    registration_hash: source.registration_v7_hash,
    execution_evidence_hash: source.execution_evidence_v4_hash,
    pre_registration_receipt_hash: source.pre_registration_receipt_v4_hash,
    issuance_id: issuanceId,
    nonce_commitment_sha256: commitment,
    issuance_sequence: 1,
  };
  const scopeHash = canonical.strictCanonicalHash(scopeBase);
  const preregistration = canonical.sealDocument(
    {
      schema_version:
        "portfolio-risk-downside-tail-post-registration-execution-issuance-preregistration-v1",
      static_fingerprint:
        "20260823-registration-v7-receipt-v5-single-use-preregistration-lock-1",
      status: "BLOCKED",
      decision:
        "POST_REGISTRATION_RECEIPT_V5_ISSUANCE_PREREGISTERED_ANTI_REPLAY_REGISTRY_WITNESS_AND_RECEIPT_UNBOUND",
      source: {
        registration_v7_schema_version:
          "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v7",
        registration_v7_static_fingerprint:
          "20260823-downside-tail-evidence-v4-registration-v7-lock-1",
        registration_v7_hash: source.registration_v7_hash,
        registration_v7_implementation_sha256:
          "23f1cf3fe1e8be3b3740d0b4d592a78f32f518b399e680d3cd79044a138956e2",
        execution_evidence_v4_schema_version:
          "strategy-correlation-cluster-portfolio-risk-presentation-consumer-execution-evidence-v4",
        execution_evidence_v4_hash: source.execution_evidence_v4_hash,
        execution_evidence_v4_implementation_sha256:
          "c1e9bb3f122dd94cb6fd45a9eb1f1c40ecefc539a2af9d12be5f680c5a3819b5",
        pre_registration_receipt_v4_hash: source.pre_registration_receipt_v4_hash,
        projection_v6_hash: source.projection_v6_hash,
        execution_preregistration_v1_hash: source.execution_preregistration_v1_hash,
        strict_canonical_python_sha256:
          "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412",
        execution_semantic_state: state,
        registration_document_embedded: false,
        execution_evidence_document_embedded: false,
        receipt_document_embedded: false,
        projection_document_embedded: false,
        execution_preregistration_document_embedded: false,
      },
      issuance: {
        issuance_id: issuanceId,
        issuance_sequence: 1,
        target_receipt_schema_version:
          "portfolio-risk-downside-tail-consumer-post-registration-execution-receipt-v5",
        target_receipt_static_fingerprint:
          "20260823-downside-tail-consumer-v6-post-registration-receipt-v5-lock-1",
        target_witness_policy_schema_version:
          "portfolio-risk-post-registration-execution-witness-policy-v2",
        target_challenge_schema_version:
          "portfolio-risk-post-registration-document-bundle-challenge-v2",
        target_attestation_schema_version:
          "portfolio-risk-post-registration-detached-attestation-v2",
        target_witness_verification_schema_version:
          "portfolio-risk-post-registration-witness-verification-candidate-v2",
        target_anti_replay_consumption_schema_version:
          "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1",
        registration_hash: source.registration_v7_hash,
        execution_evidence_hash: source.execution_evidence_v4_hash,
        pre_registration_receipt_hash: source.pre_registration_receipt_v4_hash,
        post_registration_receipt_hash: null,
      },
      anti_replay: {
        scope_schema_version:
          "portfolio-risk-post-registration-anti-replay-scope-v1",
        namespace:
          "portfolio-risk-downside-tail-post-registration-execution-receipt-v5",
        scope_hash: scopeHash,
        nonce_commitment_sha256: commitment,
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
      checks: checks([
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
      ]),
      closed_local_blockers: [
        "REGISTRATION_V7_EXACT_BLOCKED_CANDIDATE_BOUND",
        "PRE_REGISTRATION_EXECUTION_CHAIN_HASHES_BOUND",
        "POST_REGISTRATION_RECEIPT_V5_TARGET_SCHEMA_FROZEN",
        "ANTI_REPLAY_NAMESPACE_AND_SINGLE_USE_POLICY_FROZEN",
        "NONCE_COMMITMENT_BOUND_WITHOUT_NONCE_DISCLOSURE",
      ],
      blockers: [
        "WITNESS_POLICY_V2_IMPLEMENTATION_MISSING",
        "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
        "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
        "NONCE_ENTROPY_AND_TRUSTED_TIME_UNVERIFIED",
        "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
        "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNVERIFIED",
        "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
        "BROWSER_ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNAUTHORIZED",
      ],
      activation_order: [
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
      ],
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
    },
    "preregistration_hash",
  );
  const envelope = canonical.sealDocument(
    {
      schema_version:
        "portfolio-risk-downside-tail-post-registration-execution-issuance-preregistration-verification-envelope-v1",
      static_fingerprint:
        "20260823-receipt-v5-issuance-preregistration-python-envelope-lock-1",
      status: "PASS",
      decision:
        "BLOCKED_ISSUANCE_PREREGISTRATION_V1_EXACTLY_VERIFIED_FOR_CROSS_RUNTIME_WITNESS_CONSUMER",
      source: {
        issuance_preregistration_schema_version: preregistration.schema_version,
        issuance_preregistration_static_fingerprint:
          preregistration.static_fingerprint,
        issuance_preregistration_hash: preregistration.preregistration_hash,
        issuance_preregistration_implementation_sha256:
          "76a1c05a55395c3258869336b0d00b8e1613670befea35f6152be6947016e6ce",
        registration_v7_hash: source.registration_v7_hash,
        execution_evidence_v4_hash: source.execution_evidence_v4_hash,
        pre_registration_receipt_v4_hash: source.pre_registration_receipt_v4_hash,
        projection_v6_hash: source.projection_v6_hash,
        execution_preregistration_v1_hash: source.execution_preregistration_v1_hash,
        execution_semantic_state: state,
        issuance_id: issuanceId,
        nonce_commitment_sha256: commitment,
        anti_replay_scope_hash: scopeHash,
        verification_environment: "PYTHON_CONTRACT_PROCESS",
      },
      target_contracts: {
        receipt_schema_version: preregistration.issuance.target_receipt_schema_version,
        receipt_static_fingerprint:
          preregistration.issuance.target_receipt_static_fingerprint,
        witness_policy_schema_version:
          preregistration.issuance.target_witness_policy_schema_version,
        challenge_schema_version:
          preregistration.issuance.target_challenge_schema_version,
        attestation_schema_version:
          preregistration.issuance.target_attestation_schema_version,
        witness_verification_schema_version:
          preregistration.issuance.target_witness_verification_schema_version,
        anti_replay_consumption_schema_version:
          preregistration.issuance.target_anti_replay_consumption_schema_version,
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
        stage_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
      },
      checks: checks([
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
      ]),
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
    },
    "envelope_hash",
  );
  return { preregistration, envelope, rawNonce };
}

function signedBundle(state = "CLEAR", mode = "valid") {
  const documents = fixture(state);
  const pair = crypto.generateKeyPairSync("ed25519");
  const publicDer = pair.publicKey.export({ type: "spki", format: "der" });
  const publicHash = crypto.createHash("sha256").update(publicDer).digest("hex");
  const policy = witnessV2.buildPostRegistrationExecutionWitnessPolicyV2(
    documents.preregistration,
    documents.envelope,
    {
      witness_id: "synthetic-node-witness-v2",
      public_key_spki_sha256: publicHash,
      policy_nonce: hash("synthetic-node-policy-nonce-v2"),
    },
  );
  const rawNonce = mode === "nonce-mismatch" ? `${documents.rawNonce}-wrong` : documents.rawNonce;
  const challenge = witnessV2.buildPostRegistrationDocumentBundleChallengeV2(
    documents.preregistration,
    documents.envelope,
    policy,
    rawNonce,
  );
  const signingKey = mode === "signature-substitution"
    ? crypto.generateKeyPairSync("ed25519").privateKey
    : pair.privateKey;
  const signature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(challenge), "utf8"),
    signingKey,
  );
  const attestation = canonical.sealDocument(
    {
      schema_version: witnessV2.ATTESTATION_SCHEMA_VERSION,
      static_fingerprint: witnessV2.ATTESTATION_STATIC_FINGERPRINT,
      policy_hash: policy.policy_hash,
      challenge_hash: challenge.challenge_hash,
      witness_id: policy.witness.witness_id,
      key_algorithm: "Ed25519",
      public_key_spki_sha256: publicHash,
      signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
      signature_base64: signature.toString("base64"),
    },
    "attestation_hash",
  );
  const consumption = mode === "unexpected-consumption" ? { unsupported: true } : null;
  const verification = witnessV2.verifyPostRegistrationWitnessSignatureCandidateV2(
    documents.preregistration,
    documents.envelope,
    policy,
    challenge,
    attestation,
    pair.publicKey,
    rawNonce,
    consumption,
  );
  return { ...documents, policy, challenge, attestation, verification, publicKey: pair.publicKey, consumption };
}

test("exports exact v2 schemas and implementation pins", () => {
  assert.equal(witnessV2.POLICY_SCHEMA_VERSION, "portfolio-risk-post-registration-execution-witness-policy-v2");
  assert.equal(witnessV2.ENVELOPE_IMPLEMENTATION_SHA256, "3f2a6b5fadec8b2ac299937505b35b7b7f00b213c4c49241acb26adb192028e7");
});

test("exact policy remains blocked with local policy complete", () => {
  const result = signedBundle();
  assert.equal(result.policy.status, "BLOCKED");
  assert.equal(result.policy.facts.local_policy_complete, true);
  assert.equal(result.policy.facts.private_key_material_received, false);
});

test("challenge verifies nonce commitment without embedding raw nonce", () => {
  const result = signedBundle();
  assert.equal(result.challenge.status, "BLOCKED");
  assert.equal(result.challenge.facts.raw_nonce_preimage_verified, true);
  assert.equal(result.challenge.challenge.raw_nonce_embedded, false);
  assert.equal(JSON.stringify(result.challenge).includes(result.rawNonce), false);
});

test("valid signature proves local key possession only", () => {
  const result = signedBundle();
  assert.equal(result.verification.status, "BLOCKED");
  assert.equal(result.verification.local_signature_status, "PASS");
  assert.equal(result.verification.facts.cryptographic_signature_verified, true);
  assert.equal(result.verification.facts.anti_replay_registry_bound, false);
  assert.equal(result.verification.facts.post_registration_receipt_issued, false);
});

test("three semantic states remain distinct and blocked", () => {
  for (const state of ["CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"]) {
    const result = signedBundle(state);
    assert.equal(result.policy.source.execution_semantic_state, state);
    assert.equal(result.verification.status, "BLOCKED");
    assert.equal(result.verification.local_signature_status, "PASS");
  }
});

test("signature substitution blocks local verification", () => {
  const result = signedBundle("CLEAR", "signature-substitution");
  assert.equal(result.verification.local_signature_status, "BLOCK");
  assert.equal(result.verification.facts.cryptographic_signature_verified, false);
});

test("nonce mismatch blocks challenge and signature verification", () => {
  const result = signedBundle("CLEAR", "nonce-mismatch");
  assert.equal(result.challenge.facts.local_challenge_complete, false);
  assert.equal(result.verification.local_signature_status, "BLOCK");
});

test("unsupported consumption receipt is rejected rather than promoted", () => {
  const result = signedBundle("CLEAR", "unexpected-consumption");
  assert.equal(result.verification.local_signature_status, "BLOCK");
  assert.equal(result.verification.facts.anti_replay_consumption_receipt_supported, false);
});

test("public exact verifier accepts blocked valid signature document", () => {
  const result = signedBundle();
  const exact = witnessV2.verifyPostRegistrationWitnessVerificationDocumentV2(
    result.verification,
    result.preregistration,
    result.envelope,
    result.policy,
    result.challenge,
    result.attestation,
    result.publicKey,
    result.rawNonce,
    null,
  );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.verification_status, "BLOCKED");
  assert.equal(exact.local_signature_status, "PASS");
  assert.equal(exact.atomic_nonce_consumption_verified, false);
});

test("resealed envelope authority promotion blocks policy", () => {
  const documents = fixture();
  const promoted = structuredClone(documents.envelope);
  promoted.authority.witness_candidate_activation_allowed = true;
  const resealed = canonical.sealDocument(promoted, "envelope_hash");
  const policy = witnessV2.buildPostRegistrationExecutionWitnessPolicyV2(
    documents.preregistration,
    resealed,
    {
      witness_id: "synthetic-node-witness-v2",
      public_key_spki_sha256: hash("public-key"),
      policy_nonce: hash("policy-nonce"),
    },
  );
  assert.equal(policy.facts.local_policy_complete, false);
});

test("verification contains no signature material, raw nonce, or authority", () => {
  const result = signedBundle();
  const serialized = JSON.stringify(result.verification);
  assert.equal(serialized.includes(result.rawNonce), false);
  assert.equal(result.verification.source.signature_material_embedded, false);
  assert.equal(result.verification.authority.signature_authority_allowed, false);
  assert.equal(result.verification.authority.paper_authorized, false);
  assert.doesNotMatch(serialized, new RegExp("\\b" + "R" + "EADY" + "\\b"));
});
