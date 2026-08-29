"use strict";

const crypto = require("node:crypto");
const strictCanonical = require("./strict_canonical_json_v1.js");

const POLICY_SCHEMA_VERSION =
  "portfolio-risk-execution-witness-preregistration-policy-v1";
const POLICY_STATIC_FINGERPRINT =
  "20260823-ed25519-witness-policy-v1-candidate-lock-1";
const CHALLENGE_SCHEMA_VERSION =
  "portfolio-risk-execution-witness-document-bundle-challenge-v1";
const CHALLENGE_STATIC_FINGERPRINT =
  "20260823-receipt-evidence-registration-bundle-challenge-v1-lock-1";
const ATTESTATION_SCHEMA_VERSION =
  "portfolio-risk-execution-witness-detached-attestation-v1";
const ATTESTATION_STATIC_FINGERPRINT =
  "20260823-ed25519-detached-attestation-v1-lock-1";
const VERIFICATION_SCHEMA_VERSION =
  "portfolio-risk-execution-witness-signature-verification-candidate-v1";
const VERIFICATION_STATIC_FINGERPRINT =
  "20260823-preregistered-ed25519-possession-verification-v1-lock-1";
const RECEIPT_SCHEMA_VERSION =
  "portfolio-risk-joint-evidence-consumer-execution-receipt-v3";
const RECEIPT_STATIC_FINGERPRINT =
  "20260823-joint-evidence-consumer-v5-node-execution-receipt-v3-lock-1";
const EVIDENCE_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-execution-evidence-v3";
const EVIDENCE_STATIC_FINGERPRINT =
  "20260823-consumer-v5-receipt-v3-python-evidence-lock-1";
const REGISTRATION_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v5";
const REGISTRATION_STATIC_FINGERPRINT =
  "20260823-consumer-v5-receipt-evidence-registration-v5-lock-1";
const EVIDENCE_IMPLEMENTATION_SHA256 =
  "0c42538f37bfc165d15ca34fe4136f87df9fdffb411ed1a64d8f2be26c2fdb85";
const REGISTRATION_IMPLEMENTATION_SHA256 =
  "5205b4dfb3a33e5903c9f8c0015383352f2cd1fd84eb38563f2f6364f08d08d3";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const ATTESTATION_KEYS = Object.freeze([
  "challenge_hash",
  "policy_hash",
  "public_key_spki_pem",
  "schema_version",
  "signature_base64",
  "static_fingerprint",
  "witness_id"
]);
const AUTHORITY = Object.freeze({
  descriptive_only: true,
  current_admission_allowed: false,
  current_pointer_written: false,
  live_order_allowed: false,
  migration_allowed: false,
  paper_authorized: false,
  presentation_consumer_activation_allowed: false,
  presentation_mount_allowed: false,
  runtime_gate_activation_allowed: false,
  shadow_consumer_activation_allowed: false,
  writer_allowed: false
});

function deepFreeze(value) {
  if (value !== null && typeof value === "object") {
    for (const nested of Object.values(value)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

function isHash(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isWitnessId(value) {
  return typeof value === "string"
    && /^[a-z0-9][a-z0-9._-]{2,63}$/.test(value);
}

function isNonce(value) {
  return typeof value === "string"
    && /^[A-Za-z0-9_-]{32,128}$/.test(value);
}

function canonicalEqual(left, right) {
  try {
    return strictCanonical.strictCanonicalStringify(left)
      === strictCanonical.strictCanonicalStringify(right);
  } catch (_error) {
    return false;
  }
}

function authorityLocked(value) {
  return strictCanonical.isPlainRecord(value)
    && canonicalEqual(value, AUTHORITY);
}

function sealedExact(value, hashField) {
  try {
    return strictCanonical.isPlainRecord(value)
      && isHash(value[hashField])
      && strictCanonical.verifySealedDocument(value, hashField);
  } catch (_error) {
    return false;
  }
}

function publicKeyDetails(publicKeySpkiPem) {
  try {
    if (typeof publicKeySpkiPem !== "string") return null;
    const key = crypto.createPublicKey({
      key: publicKeySpkiPem,
      format: "pem",
      type: "spki"
    });
    if (key.asymmetricKeyType !== "ed25519") return null;
    const der = key.export({ format: "der", type: "spki" });
    return {
      key,
      sha256: crypto.createHash("sha256").update(der).digest("hex")
    };
  } catch (_error) {
    return null;
  }
}

function buildPreregisteredExecutionWitnessPolicyV1(
  witnessId,
  publicKeySpkiPem,
  policyNonce
) {
  const keyDetails = publicKeyDetails(publicKeySpkiPem);
  const inputsValid = Boolean(
    isWitnessId(witnessId)
    && keyDetails
    && isNonce(policyNonce)
  );
  const policy = {
    schema_version: POLICY_SCHEMA_VERSION,
    static_fingerprint: POLICY_STATIC_FINGERPRINT,
    status: inputsValid ? "CANDIDATE" : "BLOCK",
    decision: inputsValid
      ? "ED25519_PUBLIC_KEY_HASH_PREREGISTERED_EXTERNAL_IDENTITY_UNVERIFIED"
      : "EXECUTION_WITNESS_POLICY_INPUT_BLOCKED",
    witness: {
      witness_id: inputsValid ? witnessId : "UNKNOWN",
      key_algorithm: "Ed25519",
      public_key_spki_sha256: inputsValid ? keyDetails.sha256 : null,
      policy_nonce: isNonce(policyNonce) ? policyNonce : "UNKNOWN"
    },
    scope: {
      receipt_schema_version: RECEIPT_SCHEMA_VERSION,
      evidence_schema_version: EVIDENCE_SCHEMA_VERSION,
      registration_schema_version: REGISTRATION_SCHEMA_VERSION,
      detached_signature_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT"
    },
    blockers: [
      "EXTERNAL_POLICY_REGISTRY_UNBOUND",
      "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
      "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNPROVEN"
    ].concat(inputsValid ? [] : ["POLICY_INPUT_INVALID"]),
    facts: {
      policy_candidate_built: true,
      public_key_hash_preregistered_locally: inputsValid,
      public_key_material_embedded: false,
      private_key_material_received: false,
      external_policy_registry_bound: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      anti_replay_registry_bound: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      profitability_proven: false
    },
    authority: { ...AUTHORITY }
  };
  return deepFreeze(strictCanonical.sealDocument(policy, "policy_hash"));
}

function policyExact(policy) {
  return Boolean(
    sealedExact(policy, "policy_hash")
    && policy.schema_version === POLICY_SCHEMA_VERSION
    && policy.static_fingerprint === POLICY_STATIC_FINGERPRINT
    && policy.status === "CANDIDATE"
    && strictCanonical.isPlainRecord(policy.witness)
    && isWitnessId(policy.witness.witness_id)
    && policy.witness.key_algorithm === "Ed25519"
    && isHash(policy.witness.public_key_spki_sha256)
    && isNonce(policy.witness.policy_nonce)
    && authorityLocked(policy.authority)
    && policy.facts.private_key_material_received === false
    && policy.facts.external_policy_registry_bound === false
  );
}

function documentBundleChecks(receipt, evidence, registration) {
  const receiptExact = Boolean(
    sealedExact(receipt, "receipt_hash")
    && receipt.schema_version === RECEIPT_SCHEMA_VERSION
    && receipt.static_fingerprint === RECEIPT_STATIC_FINGERPRINT
    && receipt.status === "PASS"
    && authorityLocked(receipt.authority)
  );
  const evidenceExact = Boolean(
    sealedExact(evidence, "evidence_hash")
    && evidence.schema_version === EVIDENCE_SCHEMA_VERSION
    && evidence.static_fingerprint === EVIDENCE_STATIC_FINGERPRINT
    && evidence.status === "PASS"
    && authorityLocked(evidence.authority)
  );
  const registrationExact = Boolean(
    sealedExact(registration, "registration_hash")
    && registration.schema_version === REGISTRATION_SCHEMA_VERSION
    && registration.static_fingerprint === REGISTRATION_STATIC_FINGERPRINT
    && registration.status === "BLOCKED"
    && authorityLocked(registration.authority)
  );
  const receiptEvidenceBound = Boolean(
    receiptExact
    && evidenceExact
    && strictCanonical.isPlainRecord(evidence.source)
    && evidence.source.receipt_v3_hash === receipt.receipt_hash
  );
  const evidenceRegistrationPinned = Boolean(
    evidenceExact
    && registrationExact
    && strictCanonical.isPlainRecord(registration.consumer)
    && strictCanonical.isPlainRecord(registration.facts)
    && registration.consumer.evidence_schema_version === EVIDENCE_SCHEMA_VERSION
    && registration.consumer.evidence_implementation_sha256
      === EVIDENCE_IMPLEMENTATION_SHA256
    && registration.facts.evidence_v3_contract_pinned === true
    && registration.facts.registration_activated === false
  );
  return {
    receiptExact,
    evidenceExact,
    registrationExact,
    receiptEvidenceBound,
    evidenceRegistrationPinned
  };
}

function buildExecutionWitnessDocumentBundleChallengeV1(
  receipt,
  evidence,
  registration,
  policy,
  challengeNonce
) {
  const policyVerified = policyExact(policy);
  const documents = documentBundleChecks(receipt, evidence, registration);
  const nonceValid = isNonce(challengeNonce);
  const checks = [
    {
      name: "preregistered_witness_policy_exact",
      ok: policyVerified,
      blocking: true
    },
    {
      name: "receipt_v3_exact_and_authority_locked",
      ok: documents.receiptExact,
      blocking: true
    },
    {
      name: "evidence_v3_exact_and_authority_locked",
      ok: documents.evidenceExact,
      blocking: true
    },
    {
      name: "registration_v5_exact_blocked_candidate",
      ok: documents.registrationExact,
      blocking: true
    },
    {
      name: "receipt_v3_to_evidence_v3_hash_bound",
      ok: documents.receiptEvidenceBound,
      blocking: true
    },
    {
      name: "evidence_v3_contract_pinned_by_registration_v5",
      ok: documents.evidenceRegistrationPinned,
      blocking: true
    },
    {
      name: "challenge_nonce_valid",
      ok: nonceValid,
      blocking: true
    }
  ];
  const blockers = checks
    .filter((check) => check.ok !== true)
    .map((check) => check.name);
  const passed = blockers.length === 0;
  const challenge = {
    schema_version: CHALLENGE_SCHEMA_VERSION,
    static_fingerprint: CHALLENGE_STATIC_FINGERPRINT,
    status: passed ? "PASS" : "BLOCK",
    decision: passed
      ? "STRICT_CANONICAL_DOCUMENT_BUNDLE_CHALLENGE_BUILT_AUTHORITY_UNCHANGED"
      : "EXECUTION_WITNESS_DOCUMENT_BUNDLE_CHALLENGE_BLOCKED",
    witness: {
      witness_id: policyVerified ? policy.witness.witness_id : "UNKNOWN",
      public_key_spki_sha256: policyVerified
        ? policy.witness.public_key_spki_sha256
        : null
    },
    source: {
      policy_hash: policyVerified ? policy.policy_hash : null,
      receipt_v3_hash: documents.receiptExact ? receipt.receipt_hash : null,
      evidence_v3_hash: documents.evidenceExact ? evidence.evidence_hash : null,
      evidence_v3_implementation_sha256: EVIDENCE_IMPLEMENTATION_SHA256,
      registration_v5_hash: documents.registrationExact
        ? registration.registration_hash
        : null,
      registration_v5_implementation_sha256:
        REGISTRATION_IMPLEMENTATION_SHA256,
      strict_canonical_implementation_sha256:
        STRICT_CANONICAL_IMPLEMENTATION_SHA256
    },
    challenge_nonce: nonceValid ? challengeNonce : "UNKNOWN",
    checks,
    blockers,
    facts: {
      document_bundle_hashes_bound: passed,
      receipt_document_embedded: false,
      evidence_document_embedded: false,
      registration_document_embedded: false,
      policy_document_embedded: false,
      private_key_material_received: false,
      signature_present: false,
      signature_verified: false,
      witness_identity_externally_verified: false,
      independent_execution_process_witnessed: false,
      anti_replay_registry_checked: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      profitability_proven: false
    },
    authority: { ...AUTHORITY }
  };
  return deepFreeze(strictCanonical.sealDocument(challenge, "challenge_hash"));
}

function challengeExact(challenge, policy) {
  return Boolean(
    sealedExact(challenge, "challenge_hash")
    && challenge.schema_version === CHALLENGE_SCHEMA_VERSION
    && challenge.static_fingerprint === CHALLENGE_STATIC_FINGERPRINT
    && challenge.status === "PASS"
    && strictCanonical.isPlainRecord(challenge.source)
    && strictCanonical.isPlainRecord(challenge.witness)
    && challenge.source.policy_hash === policy.policy_hash
    && challenge.witness.witness_id === policy.witness.witness_id
    && challenge.witness.public_key_spki_sha256
      === policy.witness.public_key_spki_sha256
    && isNonce(challenge.challenge_nonce)
    && authorityLocked(challenge.authority)
  );
}

function attestationShapeExact(attestation) {
  return Boolean(
    strictCanonical.isPlainRecord(attestation)
    && JSON.stringify(Object.keys(attestation).sort())
      === JSON.stringify(ATTESTATION_KEYS)
    && attestation.schema_version === ATTESTATION_SCHEMA_VERSION
    && attestation.static_fingerprint === ATTESTATION_STATIC_FINGERPRINT
    && isWitnessId(attestation.witness_id)
    && isHash(attestation.policy_hash)
    && isHash(attestation.challenge_hash)
    && typeof attestation.public_key_spki_pem === "string"
    && typeof attestation.signature_base64 === "string"
  );
}

function strictSignatureBuffer(signatureBase64) {
  try {
    if (typeof signatureBase64 !== "string") return null;
    const signature = Buffer.from(signatureBase64, "base64");
    return signature.length === 64
      && signature.toString("base64") === signatureBase64
      ? signature
      : null;
  } catch (_error) {
    return null;
  }
}

function verifyPreregisteredExecutionWitnessSignatureCandidateV1(
  attestation,
  policy,
  challenge,
  receipt,
  evidence,
  registration
) {
  const policyVerified = policyExact(policy);
  let expectedChallenge = null;
  try {
    expectedChallenge = buildExecutionWitnessDocumentBundleChallengeV1(
      receipt,
      evidence,
      registration,
      policy,
      strictCanonical.isPlainRecord(challenge)
        ? challenge.challenge_nonce
        : null
    );
  } catch (_error) {
    expectedChallenge = null;
  }
  const challengeVerified = Boolean(
    policyVerified
    && expectedChallenge
    && expectedChallenge.status === "PASS"
    && challengeExact(challenge, policy)
    && canonicalEqual(challenge, expectedChallenge)
  );
  const attestationExact = attestationShapeExact(attestation);
  const keyDetails = attestationExact
    ? publicKeyDetails(attestation.public_key_spki_pem)
    : null;
  const keyHashMatched = Boolean(
    keyDetails
    && policyVerified
    && keyDetails.sha256 === policy.witness.public_key_spki_sha256
  );
  const fieldsBound = Boolean(
    attestationExact
    && policyVerified
    && challengeVerified
    && attestation.witness_id === policy.witness.witness_id
    && attestation.policy_hash === policy.policy_hash
    && attestation.challenge_hash === challenge.challenge_hash
  );
  const signature = attestationExact
    ? strictSignatureBuffer(attestation.signature_base64)
    : null;
  let signatureVerified = false;
  try {
    signatureVerified = Boolean(
      fieldsBound
      && keyHashMatched
      && signature
      && crypto.verify(
        null,
        Buffer.from(
          strictCanonical.strictCanonicalStringify(challenge),
          "utf8"
        ),
        keyDetails.key,
        signature
      )
    );
  } catch (_error) {
    signatureVerified = false;
  }
  const checks = [
    {
      name: "preregistered_witness_policy_exact",
      ok: policyVerified,
      blocking: true
    },
    {
      name: "document_bundle_challenge_exact",
      ok: challengeVerified,
      blocking: true
    },
    {
      name: "detached_attestation_shape_exact",
      ok: attestationExact,
      blocking: true
    },
    {
      name: "attestation_policy_and_challenge_fields_bound",
      ok: fieldsBound,
      blocking: true
    },
    {
      name: "ed25519_public_key_hash_matches_policy",
      ok: keyHashMatched,
      blocking: true
    },
    {
      name: "ed25519_detached_signature_verified",
      ok: signatureVerified,
      blocking: true
    }
  ];
  const blockers = checks
    .filter((check) => check.ok !== true)
    .map((check) => check.name);
  const passed = blockers.length === 0;
  const verification = {
    schema_version: VERIFICATION_SCHEMA_VERSION,
    static_fingerprint: VERIFICATION_STATIC_FINGERPRINT,
    status: passed ? "PASS" : "BLOCK",
    decision: passed
      ? "PREREGISTERED_ED25519_KEY_POSSESSION_VERIFIED_EXTERNAL_IDENTITY_UNVERIFIED"
      : "PREREGISTERED_EXECUTION_WITNESS_SIGNATURE_VERIFICATION_BLOCKED",
    source: {
      witness_id: fieldsBound ? attestation.witness_id : "UNKNOWN",
      policy_hash: policyVerified ? policy.policy_hash : null,
      challenge_hash: challengeVerified ? challenge.challenge_hash : null,
      receipt_v3_hash: challengeVerified ? receipt.receipt_hash : null,
      evidence_v3_hash: challengeVerified ? evidence.evidence_hash : null,
      registration_v5_hash: challengeVerified
        ? registration.registration_hash
        : null,
      public_key_spki_sha256: keyHashMatched ? keyDetails.sha256 : null,
      key_algorithm: "Ed25519",
      signed_payload: "STRICT_CANONICAL_CHALLENGE_DOCUMENT",
      public_key_material_embedded: false,
      signature_material_embedded: false
    },
    checks,
    blockers,
    facts: {
      cryptographic_signature_verified: signatureVerified,
      preregistered_public_key_hash_matched: keyHashMatched,
      cryptographic_key_possession_verified: passed,
      document_bundle_challenge_exactly_rebuilt: challengeVerified,
      public_key_material_presented_to_verifier: Boolean(keyDetails),
      public_key_material_embedded: false,
      private_key_material_received: false,
      policy_externally_registered: false,
      witness_organization_identity_verified: false,
      independent_execution_process_witnessed: false,
      signature_timestamp_verified: false,
      anti_replay_registry_checked: false,
      browser_visual_review_performed: false,
      runtime_assets_accessed: false,
      network_accessed: false,
      profitability_proven: false
    },
    authority: { ...AUTHORITY }
  };
  return deepFreeze(
    strictCanonical.sealDocument(verification, "verification_hash")
  );
}

function verifyExecutionWitnessSignatureVerificationDocumentV1(
  document,
  attestation,
  policy,
  challenge,
  receipt,
  evidence,
  registration
) {
  const expected = verifyPreregisteredExecutionWitnessSignatureCandidateV1(
    attestation,
    policy,
    challenge,
    receipt,
    evidence,
    registration
  );
  const exact = sealedExact(document, "verification_hash")
    && canonicalEqual(document, expected);
  return deepFreeze({
    schema_version: VERIFICATION_SCHEMA_VERSION + "-exact-rebuild-v1",
    status: exact ? "PASS" : "BLOCK",
    verification_document_exactly_rebuilt: exact,
    verification_status: exact ? expected.status : "UNKNOWN",
    verification_hash: exact ? expected.verification_hash : null,
    blockers: exact ? [] : ["witness_signature_verification_exact_rebuild"],
    witness_organization_identity_verified: false,
    independent_execution_process_witnessed: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    writer_allowed: false
  });
}

module.exports = Object.freeze({
  ATTESTATION_SCHEMA_VERSION,
  ATTESTATION_STATIC_FINGERPRINT,
  CHALLENGE_SCHEMA_VERSION,
  CHALLENGE_STATIC_FINGERPRINT,
  EVIDENCE_SCHEMA_VERSION,
  EVIDENCE_STATIC_FINGERPRINT,
  POLICY_SCHEMA_VERSION,
  POLICY_STATIC_FINGERPRINT,
  RECEIPT_SCHEMA_VERSION,
  RECEIPT_STATIC_FINGERPRINT,
  REGISTRATION_SCHEMA_VERSION,
  REGISTRATION_STATIC_FINGERPRINT,
  VERIFICATION_SCHEMA_VERSION,
  VERIFICATION_STATIC_FINGERPRINT,
  buildExecutionWitnessDocumentBundleChallengeV1,
  buildPreregisteredExecutionWitnessPolicyV1,
  verifyExecutionWitnessSignatureVerificationDocumentV1,
  verifyPreregisteredExecutionWitnessSignatureCandidateV1
});
