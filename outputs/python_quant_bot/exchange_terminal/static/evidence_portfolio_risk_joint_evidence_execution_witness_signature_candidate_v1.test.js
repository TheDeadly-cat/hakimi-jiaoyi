"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const witness = require(
  "./evidence_portfolio_risk_joint_evidence_execution_witness_signature_candidate_v1.js"
);

const keys = crypto.generateKeyPairSync("ed25519");
const publicKeyPem = keys.publicKey.export({
  format: "pem",
  type: "spki"
}).toString();
const witnessId = "synthetic-witness-alpha";
const policyNonce = "policy_nonce_0123456789abcdef0123456789";
const challengeNonce = "challenge_nonce_0123456789abcdef012345";

function lockedAuthority() {
  return {
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
  };
}

function documents() {
  const receipt = strictCanonical.sealDocument(
    {
      schema_version: witness.RECEIPT_SCHEMA_VERSION,
      static_fingerprint: witness.RECEIPT_STATIC_FINGERPRINT,
      status: "PASS",
      authority: lockedAuthority()
    },
    "receipt_hash"
  );
  const evidence = strictCanonical.sealDocument(
    {
      schema_version: witness.EVIDENCE_SCHEMA_VERSION,
      static_fingerprint: witness.EVIDENCE_STATIC_FINGERPRINT,
      status: "PASS",
      source: { receipt_v3_hash: receipt.receipt_hash },
      authority: lockedAuthority()
    },
    "evidence_hash"
  );
  const registration = strictCanonical.sealDocument(
    {
      schema_version: witness.REGISTRATION_SCHEMA_VERSION,
      static_fingerprint: witness.REGISTRATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
      consumer: {
        evidence_schema_version: witness.EVIDENCE_SCHEMA_VERSION,
        evidence_implementation_sha256:
          "0c42538f37bfc165d15ca34fe4136f87df9fdffb411ed1a64d8f2be26c2fdb85"
      },
      facts: {
        evidence_v3_contract_pinned: true,
        registration_activated: false
      },
      authority: lockedAuthority()
    },
    "registration_hash"
  );
  return { receipt, evidence, registration };
}

function policy(pem) {
  return witness.buildPreregisteredExecutionWitnessPolicyV1(
    witnessId,
    pem || publicKeyPem,
    policyNonce
  );
}

function challenge(inputPolicy, inputDocuments) {
  const docs = inputDocuments || documents();
  return witness.buildExecutionWitnessDocumentBundleChallengeV1(
    docs.receipt,
    docs.evidence,
    docs.registration,
    inputPolicy || policy(),
    challengeNonce
  );
}

function attestation(inputPolicy, inputChallenge, keyPair, pem) {
  const chosenPolicy = inputPolicy || policy();
  const chosenChallenge = inputChallenge || challenge(chosenPolicy);
  const chosenKeys = keyPair || keys;
  const signature = crypto.sign(
    null,
    Buffer.from(
      strictCanonical.strictCanonicalStringify(chosenChallenge),
      "utf8"
    ),
    chosenKeys.privateKey
  ).toString("base64");
  return {
    schema_version: witness.ATTESTATION_SCHEMA_VERSION,
    static_fingerprint: witness.ATTESTATION_STATIC_FINGERPRINT,
    witness_id: witnessId,
    policy_hash: chosenPolicy.policy_hash,
    challenge_hash: chosenChallenge.challenge_hash,
    public_key_spki_pem: pem || publicKeyPem,
    signature_base64: signature
  };
}

function verifyAttestation(
  signed,
  inputPolicy,
  inputChallenge,
  inputDocuments
) {
  const docs = inputDocuments || documents();
  return witness.verifyPreregisteredExecutionWitnessSignatureCandidateV1(
    signed,
    inputPolicy,
    inputChallenge,
    docs.receipt,
    docs.evidence,
    docs.registration
  );
}

function verifyVerificationDocument(
  document,
  signed,
  inputPolicy,
  inputChallenge,
  inputDocuments
) {
  const docs = inputDocuments || documents();
  return witness.verifyExecutionWitnessSignatureVerificationDocumentV1(
    document,
    signed,
    inputPolicy,
    inputChallenge,
    docs.receipt,
    docs.evidence,
    docs.registration
  );
}

test("exports are frozen and expose no signing function", () => {
  assert.equal(Object.isFrozen(witness), true);
  const forbiddenExports = new Set([
    "sign",
    "createprivatekey",
    "generatekeypair",
    "generatekeypairsync"
  ]);
  assert.equal(
    Object.keys(witness).some(
      (name) => forbiddenExports.has(name.toLowerCase())
    ),
    false
  );
  assert.equal(witness.POLICY_SCHEMA_VERSION.endsWith("policy-v1"), true);
});

test("valid public key builds sealed candidate policy without key material", () => {
  const value = policy();
  assert.equal(value.status, "CANDIDATE");
  assert.equal(
    strictCanonical.verifySealedDocument(value, "policy_hash"),
    true
  );
  assert.match(value.witness.public_key_spki_sha256, /^[0-9a-f]{64}$/);
  assert.equal(value.facts.public_key_material_embedded, false);
  assert.equal(value.facts.private_key_material_received, false);
  assert.equal(JSON.stringify(value).includes("BEGIN PUBLIC KEY"), false);
});

test("invalid or non-Ed25519 public key blocks policy", () => {
  const invalid = policy("not-a-public-key");
  assert.equal(invalid.status, "BLOCK");
  assert.ok(invalid.blockers.includes("POLICY_INPUT_INVALID"));
  const rsa = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const rsaPem = rsa.publicKey.export({ format: "pem", type: "spki" }).toString();
  assert.equal(policy(rsaPem).status, "BLOCK");
});

test("valid documents build a sealed hash-only challenge", () => {
  const value = challenge();
  assert.equal(value.status, "PASS");
  assert.equal(
    strictCanonical.verifySealedDocument(value, "challenge_hash"),
    true
  );
  assert.match(value.source.receipt_v3_hash, /^[0-9a-f]{64}$/);
  assert.match(value.source.evidence_v3_hash, /^[0-9a-f]{64}$/);
  assert.match(value.source.registration_v5_hash, /^[0-9a-f]{64}$/);
  assert.equal(value.facts.receipt_document_embedded, false);
  assert.equal(value.facts.evidence_document_embedded, false);
});

test("resealed wrong receipt schema blocks challenge", () => {
  const docs = documents();
  const altered = JSON.parse(JSON.stringify(docs.receipt));
  delete altered.receipt_hash;
  altered.schema_version =
    "portfolio-risk-weighted-diversification-fixture-execution-receipt-v2";
  docs.receipt = strictCanonical.sealDocument(altered, "receipt_hash");
  const value = challenge(policy(), docs);
  assert.equal(value.status, "BLOCK");
  assert.ok(
    value.blockers.includes("receipt_v3_exact_and_authority_locked")
  );
});

test("evidence receipt hash substitution blocks challenge", () => {
  const docs = documents();
  const altered = JSON.parse(JSON.stringify(docs.evidence));
  delete altered.evidence_hash;
  altered.source.receipt_v3_hash = "f".repeat(64);
  docs.evidence = strictCanonical.sealDocument(altered, "evidence_hash");
  const value = challenge(policy(), docs);
  assert.equal(value.status, "BLOCK");
  assert.ok(
    value.blockers.includes("receipt_v3_to_evidence_v3_hash_bound")
  );
});

test("registration without evidence-v3 pin blocks challenge", () => {
  const docs = documents();
  const altered = JSON.parse(JSON.stringify(docs.registration));
  delete altered.registration_hash;
  altered.facts.evidence_v3_contract_pinned = false;
  docs.registration = strictCanonical.sealDocument(
    altered,
    "registration_hash"
  );
  const value = challenge(policy(), docs);
  assert.equal(value.status, "BLOCK");
  assert.ok(
    value.blockers.includes(
      "evidence_v3_contract_pinned_by_registration_v5"
    )
  );
});

test("valid detached attestation verifies key possession only", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const verification = verifyAttestation(
    attestation(selectedPolicy, selectedChallenge),
    selectedPolicy,
    selectedChallenge
  );
  assert.equal(verification.status, "PASS");
  assert.equal(verification.facts.cryptographic_signature_verified, true);
  assert.equal(
    verification.facts.cryptographic_key_possession_verified,
    true
  );
  assert.equal(
    verification.facts.witness_organization_identity_verified,
    false
  );
  assert.equal(
    verification.facts.independent_execution_process_witnessed,
    false
  );
  assert.equal(verification.authority.paper_authorized, false);
});

test("valid signature from a substituted public key blocks policy match", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const other = crypto.generateKeyPairSync("ed25519");
  const otherPem = other.publicKey.export({
    format: "pem",
    type: "spki"
  }).toString();
  const altered = attestation(
    selectedPolicy,
    selectedChallenge,
    other,
    otherPem
  );
  const verification = verifyAttestation(
    altered,
    selectedPolicy,
    selectedChallenge
  );
  assert.equal(verification.status, "BLOCK");
  assert.ok(
    verification.blockers.includes(
      "ed25519_public_key_hash_matches_policy"
    )
  );
});

test("signature tamper blocks verification", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const altered = attestation(selectedPolicy, selectedChallenge);
  const bytes = Buffer.from(altered.signature_base64, "base64");
  bytes[0] ^= 1;
  altered.signature_base64 = bytes.toString("base64");
  const verification = verifyAttestation(
    altered,
    selectedPolicy,
    selectedChallenge
  );
  assert.equal(verification.status, "BLOCK");
  assert.ok(
    verification.blockers.includes("ed25519_detached_signature_verified")
  );
});

test("policy substitution blocks attestation binding", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const signed = attestation(selectedPolicy, selectedChallenge);
  const otherPolicy = witness.buildPreregisteredExecutionWitnessPolicyV1(
    "synthetic-witness-beta",
    publicKeyPem,
    "other_policy_nonce_0123456789abcdef012345"
  );
  const verification = verifyAttestation(
    signed,
    otherPolicy,
    selectedChallenge
  );
  assert.equal(verification.status, "BLOCK");
  assert.ok(
    verification.blockers.includes("document_bundle_challenge_exact")
  );
});

test("resealed challenge substitution invalidates detached signature", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const signed = attestation(selectedPolicy, selectedChallenge);
  const altered = JSON.parse(JSON.stringify(selectedChallenge));
  delete altered.challenge_hash;
  altered.challenge_nonce = "altered_nonce_0123456789abcdef0123456789";
  const resealed = strictCanonical.sealDocument(altered, "challenge_hash");
  signed.challenge_hash = resealed.challenge_hash;
  const verification = verifyAttestation(
    signed,
    selectedPolicy,
    resealed
  );
  assert.equal(verification.status, "BLOCK");
  assert.ok(
    verification.blockers.includes("ed25519_detached_signature_verified")
  );
});

test("exact verification document verifier rejects authority tamper", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const signed = attestation(selectedPolicy, selectedChallenge);
  const verification = verifyAttestation(
    signed,
    selectedPolicy,
    selectedChallenge
  );
  assert.equal(
    verifyVerificationDocument(
      verification,
      signed,
      selectedPolicy,
      selectedChallenge
    ).status,
    "PASS"
  );
  const altered = JSON.parse(JSON.stringify(verification));
  delete altered.verification_hash;
  altered.authority.live_order_allowed = true;
  const resealed = strictCanonical.sealDocument(
    altered,
    "verification_hash"
  );
  assert.equal(
    verifyVerificationDocument(
      resealed,
      signed,
      selectedPolicy,
      selectedChallenge
    ).status,
    "BLOCK"
  );
});

test("outputs are deeply frozen and contain no promotion claim", () => {
  const selectedPolicy = policy();
  const selectedChallenge = challenge(selectedPolicy);
  const verification = verifyAttestation(
    attestation(selectedPolicy, selectedChallenge),
    selectedPolicy,
    selectedChallenge
  );
  assert.equal(Object.isFrozen(selectedPolicy), true);
  assert.equal(Object.isFrozen(selectedChallenge), true);
  assert.equal(Object.isFrozen(verification), true);
  assert.equal(Object.isFrozen(verification.facts), true);
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(JSON.stringify(verification), promotion);
  assert.equal(verification.facts.profitability_proven, false);
});

test("forged pass challenge with valid signature fails source rebuild", () => {
  const docs = documents();
  const alteredEvidence = JSON.parse(JSON.stringify(docs.evidence));
  delete alteredEvidence.evidence_hash;
  alteredEvidence.source.receipt_v3_hash = "f".repeat(64);
  docs.evidence = strictCanonical.sealDocument(
    alteredEvidence,
    "evidence_hash"
  );
  const selectedPolicy = policy();
  const blocked = challenge(selectedPolicy, docs);
  assert.equal(blocked.status, "BLOCK");
  const forged = JSON.parse(JSON.stringify(blocked));
  delete forged.challenge_hash;
  forged.status = "PASS";
  forged.decision =
    "STRICT_CANONICAL_DOCUMENT_BUNDLE_CHALLENGE_BUILT_AUTHORITY_UNCHANGED";
  forged.checks = forged.checks.map((check) => ({ ...check, ok: true }));
  forged.blockers = [];
  forged.facts.document_bundle_hashes_bound = true;
  const resealed = strictCanonical.sealDocument(forged, "challenge_hash");
  const signed = attestation(selectedPolicy, resealed);
  const verification = verifyAttestation(
    signed,
    selectedPolicy,
    resealed,
    docs
  );
  assert.equal(verification.status, "BLOCK");
  assert.ok(
    verification.blockers.includes("document_bundle_challenge_exact")
  );
  assert.equal(
    verification.facts.document_bundle_challenge_exactly_rebuilt,
    false
  );
});

test("production verifier has no private-key filesystem network or DOM path", () => {
  const source = fs.readFileSync(
    path.resolve(
      __dirname,
      "evidence_portfolio_risk_joint_evidence_execution_witness_signature_candidate_v1.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "node:fs",
    "generateKeyPair",
    "createPrivateKey",
    "crypto.sign",
    "document.",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket"
  ]) assert.equal(source.includes(forbidden), false);
});
