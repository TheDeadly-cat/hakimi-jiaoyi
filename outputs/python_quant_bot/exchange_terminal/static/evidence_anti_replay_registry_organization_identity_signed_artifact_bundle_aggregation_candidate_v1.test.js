"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const signedArtifactV1 = require(
  "./evidence_anti_replay_registry_organization_identity_signed_artifact_candidate_v1.js"
);
const aggregationV1 = require(
  "./evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js"
);

const CONFIGS = Object.freeze([
  [
    "ORGANIZATION_REGISTRY_ATTESTATION",
    "registry-organization-authority-attestation-v1",
    "organization_registry_authority",
  ],
  [
    "DOMAIN_CONTROL_ATTESTATION",
    "registry-domain-control-attestation-v1",
    "domain_control_auditor",
  ],
  [
    "KEY_GOVERNANCE_EVALUATION",
    "provider-identity-witness-conformance-key-governance-evaluation-v1",
    "key_governance_auditor",
  ],
  [
    "AUDITOR_PROVENANCE_EVALUATION",
    "provider-identity-auditor-provenance-suite-reproducibility-evaluation-v1",
    "provenance_registry_authority",
  ],
  [
    "ARTIFACT_TRANSPARENCY_EVALUATION",
    "provider-identity-artifact-transparency-availability-evaluation-v1",
    "transparency_log_authority",
  ],
  [
    "REVOCATION_STATUS_RECEIPT",
    "registry-revocation-status-receipt-v1",
    "revocation_authority",
  ],
]);

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function fileHash(...parts) {
  return hash(fs.readFileSync(path.join(__dirname, ...parts)));
}

function publicKeyHash(publicKey) {
  return hash(publicKey.export({ type: "spki", format: "der" }));
}

function envelopeAuthority() {
  return {
    current_admission_allowed: false,
    evidence_bundle_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    registry_identity_admission_allowed: false,
    runtime_gate_activation_allowed: false,
    signed_artifact_aggregation_activation_allowed: false,
    writer_allowed: false,
  };
}

function envelopeFacts() {
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

function envelopeChecks() {
  return [
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
  ].map((name) => ({ blocking: true, name, ok: true }));
}

function pythonEnvelope(references, subject) {
  return canonical.sealDocument(
    {
      authority: envelopeAuthority(),
      blockers: [],
      checks: envelopeChecks(),
      decision:
        "BLOCKED_BUNDLE_EVALUATION_V1_EXACTLY_VERIFIED_FOR_CROSS_RUNTIME_SIGNED_ARTIFACT_CONSUMER",
      facts: envelopeFacts(),
      schema_version: aggregationV1.PYTHON_ENVELOPE_SCHEMA_VERSION,
      source: {
        bundle_evaluation_hash: hash(Buffer.from("synthetic-evaluation")),
        bundle_evaluation_implementation_sha256:
          "fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055",
        bundle_evaluation_schema_version:
          "anti-replay-registry-organization-identity-evidence-bundle-evaluation-v1",
        bundle_evaluation_static_fingerprint:
          "20260823-registry-organization-identity-evidence-bundle-evaluation-v1-lock-1",
        evidence_reference_count: 6,
        evidence_reference_implementation_sha256:
          "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f",
        evidence_reference_set_sha256: canonical.strictCanonicalHash({
          references,
        }),
        identity_preregistration_hash: hash(
          Buffer.from("synthetic-identity-preregistration")
        ),
        identity_preregistration_implementation_sha256:
          "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f",
        intake_preregistration_hash: hash(
          Buffer.from("synthetic-intake-preregistration")
        ),
        intake_preregistration_implementation_sha256:
          "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56",
        operator_identity_claim_hash: canonical.strictCanonicalHash(
          "synthetic-operator-claim"
        ),
        public_key_spki_sha256: subject.publicKeyHash,
        reference_time_ms: subject.referenceTime,
        registry_id: subject.registryId,
        strict_canonical_implementation_sha256:
          "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412",
        trust_domain: subject.trustDomain,
        verification_environment: "PYTHON_CONTRACT_PROCESS",
      },
      static_fingerprint:
        aggregationV1.PYTHON_ENVELOPE_STATIC_FINGERPRINT,
      status: "PASS",
      target_contracts: {
        signed_artifact_aggregation_schema_version:
          aggregationV1.AGGREGATION_SCHEMA_VERSION,
        signed_artifact_candidate_implementation_sha256:
          aggregationV1.SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256,
        signed_artifact_exact_verification_schema_version:
          signedArtifactV1.EXACT_VERIFICATION_SCHEMA_VERSION,
        signed_artifact_verification_schema_version:
          signedArtifactV1.VERIFICATION_SCHEMA_VERSION,
      },
      verification: {
        bundle_evaluation_document_exactly_rebuilt: true,
        bundle_evaluation_status: "BLOCKED",
        bundle_local_status: "STRUCTURE_BINDING_AND_FRESHNESS_PASS",
        bundle_public_verifier_status: "PASS",
        evidence_reference_count: 6,
        identity_preregistration_status: "BLOCKED",
        intake_preregistration_status: "BLOCKED",
        reference_set_exact: true,
        reference_time_exact: true,
      },
    },
    "envelope_hash"
  );
}

function fixture(label = "aggregate") {
  const subject = {
    publicKeyHash: hash(Buffer.from("synthetic-subject:" + label)),
    referenceTime: 10_000_000,
    registryId: "synthetic." + label + ".registry",
    trustDomain: "synthetic." + label + ".test",
  };
  const items = CONFIGS.map(([kind, schema, role]) => {
    const pair = crypto.generateKeyPairSync("ed25519");
    const metadata = {
      evidence_kind: kind,
      evidence_schema_version: schema,
      expires_at_ms: subject.referenceTime + 1_000,
      issued_at_ms: subject.referenceTime - 1_000,
      signature_algorithm: "ed25519",
      signer_public_key_spki_sha256: publicKeyHash(pair.publicKey),
      signer_role: role,
      subject_public_key_spki_sha256: subject.publicKeyHash,
      subject_registry_id: subject.registryId,
    };
    const payload =
      signedArtifactV1.buildRegistryOrganizationIdentitySignedEvidencePayloadV1(
        metadata,
        {
          marker: "synthetic-body:" + label + ":" + kind,
          record_sha256: hash(Buffer.from(label + ":" + kind)),
          synthetic: true,
        }
      );
    const reference = {
      ...metadata,
      artifact_sha256: canonical.strictCanonicalHash(payload),
      schema_version: signedArtifactV1.EVIDENCE_REFERENCE_SCHEMA_VERSION,
    };
    const detachedSignature = crypto.sign(
      null,
      Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
      pair.privateKey
    );
    return { detachedSignature, pair, payload, publicKey: pair.publicKey, reference };
  });
  const envelope = pythonEnvelope(
    items.map((item) => item.reference),
    subject
  );
  return { envelope, items, subject };
}

function productionItems(items) {
  return items.map(({ detachedSignature, payload, publicKey, reference }) => ({
    detachedSignature,
    payload,
    publicKey,
    reference,
  }));
}

function aggregate(value, overrides = {}) {
  return aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
    overrides.envelope || value.envelope,
    productionItems(overrides.items || value.items)
  );
}

test("exports exact schemas and pinned dependencies", () => {
  assert.equal(
    fileHash("strict_canonical_json_v1.js"),
    aggregationV1.STRICT_CANONICAL_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash(
      "evidence_anti_replay_registry_organization_identity_signed_artifact_candidate_v1.js"
    ),
    aggregationV1.SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash(
      "..",
      "application",
      "anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1.py"
    ),
    aggregationV1.PYTHON_ENVELOPE_IMPLEMENTATION_SHA256
  );
});

test("six exact signatures aggregate into a blocked local-only pass", () => {
  const value = fixture("valid");
  const result = aggregate(value);
  assert.equal(result.status, "BLOCKED");
  assert.equal(
    result.local_signed_artifact_bundle_status,
    aggregationV1.LOCAL_PASS_STATUS
  );
  assert.equal(result.facts.evidence_signatures_verified, true);
  assert.equal(result.facts.python_process_authenticated, false);
  assert.equal(result.facts.evidence_payloads_semantics_verified, false);
  assert.equal(result.facts.external_source_trust_verified, false);
  assert.equal(result.facts.registry_organization_identity_verified, false);
  assert.equal(Object.values(result.authority).some(Boolean), false);
});

test("aggregation emits one hash-only receipt per evidence kind", () => {
  const value = fixture("receipts");
  const result = aggregate(value);
  assert.deepEqual(
    result.artifacts.map((row) => row.evidence_kind),
    aggregationV1.EVIDENCE_KINDS
  );
  assert.equal(new Set(result.artifacts.map((row) => row.verification_hash)).size, 6);
  assert.equal(result.artifacts.every((row) => row.evidence_signature_verified), true);
});

test("one substituted signature blocks the aggregate", () => {
  const value = fixture("signature-substitution");
  const items = [...value.items];
  const signature = Buffer.from(items[0].detachedSignature);
  signature[0] ^= 0xff;
  items[0] = { ...items[0], detachedSignature: signature };
  const result = aggregate(value, { items });
  assert.equal(result.local_signed_artifact_bundle_status, "BLOCK");
  assert.equal(result.facts.evidence_signatures_verified, false);
  assert.equal(result.artifacts[0].local_signed_artifact_status, "BLOCK");
});

test("resigned body substitution still fails the frozen reference", () => {
  const value = fixture("body-substitution");
  const items = [...value.items];
  const item = items[0];
  const payload = structuredClone(item.payload);
  payload.evidence_body.record_sha256 = hash(Buffer.from("substituted-body"));
  const detachedSignature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    item.pair.privateKey
  );
  items[0] = { ...item, detachedSignature, payload };
  const result = aggregate(value, { items });
  assert.equal(result.local_signed_artifact_bundle_status, "BLOCK");
  assert.equal(result.artifacts[0].local_signed_artifact_status, "BLOCK");
});

test("public-key substitution blocks the aggregate", () => {
  const value = fixture("key-substitution");
  const items = [...value.items];
  const other = crypto.generateKeyPairSync("ed25519");
  items[0] = { ...items[0], publicKey: other.publicKey };
  const result = aggregate(value, { items });
  assert.equal(result.local_signed_artifact_bundle_status, "BLOCK");
  assert.equal(result.artifacts[0].local_signed_artifact_status, "BLOCK");
});

test("missing and duplicate evidence kinds are rejected before aggregation", () => {
  const value = fixture("kind-cardinality");
  assert.throws(
    () => aggregate(value, { items: value.items.slice(0, -1) }),
    /exactly six/
  );
  const duplicate = value.items.slice(0, -1).concat(value.items[0]);
  assert.throws(
    () => aggregate(value, { items: duplicate }),
    /one signed-artifact/
  );
});

test("reference-set substitution blocks even when the changed item verifies", () => {
  const value = fixture("reference-set-substitution");
  const items = [...value.items];
  const item = items[0];
  const payload = structuredClone(item.payload);
  payload.subject.registry_id = "synthetic.substituted.registry";
  const reference = {
    ...item.reference,
    artifact_sha256: canonical.strictCanonicalHash(payload),
    subject_registry_id: payload.subject.registry_id,
  };
  const detachedSignature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    item.pair.privateKey
  );
  items[0] = { ...item, detachedSignature, payload, reference };
  const result = aggregate(value, { items });
  assert.equal(result.artifacts[0].local_signed_artifact_status, "PASS");
  assert.equal(result.facts.evidence_reference_set_bound, false);
  assert.equal(result.facts.subject_identity_bound, false);
  assert.equal(result.local_signed_artifact_bundle_status, "BLOCK");
});

test("independent freshness check blocks a forged fresh-status envelope", () => {
  const value = fixture("freshness-defense");
  const items = [...value.items];
  const item = items[0];
  const payload = structuredClone(item.payload);
  payload.issued_at_ms = 1;
  payload.expires_at_ms = 2;
  const reference = {
    ...item.reference,
    artifact_sha256: canonical.strictCanonicalHash(payload),
    issued_at_ms: 1,
    expires_at_ms: 2,
  };
  const detachedSignature = crypto.sign(
    null,
    Buffer.from(canonical.strictCanonicalStringify(payload), "utf8"),
    item.pair.privateKey
  );
  items[0] = { ...item, detachedSignature, payload, reference };
  const envelope = pythonEnvelope(
    items.map((row) => row.reference),
    value.subject
  );
  const result = aggregate(value, { envelope, items });
  assert.equal(result.facts.evidence_reference_set_bound, true);
  assert.equal(result.facts.all_references_fresh, false);
  assert.equal(result.local_signed_artifact_bundle_status, "BLOCK");
});

test("resealed Python-envelope promotion is rejected before aggregation", () => {
  const value = fixture("envelope-promotion");
  const body = structuredClone(value.envelope);
  delete body.envelope_hash;
  body.facts.registry_organization_identity_verified = true;
  const envelope = canonical.sealDocument(body, "envelope_hash");
  assert.throws(
    () => aggregate(value, { envelope }),
    /not exact/
  );
});

test("public exact verifier PASS preserves BLOCKED identity and authority", () => {
  const value = fixture("exact-pass");
  const items = productionItems(value.items);
  const document = aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
    value.envelope,
    items
  );
  const exact =
    aggregationV1.verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
      value.envelope,
      items,
      document
    );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.aggregation_status, "BLOCKED");
  assert.equal(exact.evidence_signatures_verified, true);
  assert.equal(exact.python_process_authenticated, false);
  assert.equal(exact.registry_organization_identity_verified, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
  assert.equal(exact.writer_allowed, false);
});

test("exact one-signature failure remains BLOCK and BLOCKED", () => {
  const value = fixture("exact-local-block");
  const items = [...value.items];
  const signature = Buffer.from(items[0].detachedSignature);
  signature[1] ^= 0xff;
  items[0] = { ...items[0], detachedSignature: signature };
  const production = productionItems(items);
  const document =
    aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
      value.envelope,
      production
    );
  const exact =
    aggregationV1.verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
      value.envelope,
      production,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.aggregation_document_exactly_rebuilt, true);
  assert.equal(exact.aggregation_status, "BLOCKED");
  assert.equal(exact.local_signed_artifact_bundle_status, "BLOCK");
});

test("tampered aggregate promotion becomes BLOCK and UNKNOWN", () => {
  const value = fixture("aggregate-promotion");
  const items = productionItems(value.items);
  const document =
    aggregationV1.buildRegistryOrganizationIdentitySignedArtifactBundleAggregationCandidateV1(
      value.envelope,
      items
    );
  document.facts.registry_organization_identity_verified = true;
  const exact =
    aggregationV1.verifyRegistryOrganizationIdentitySignedArtifactBundleAggregationDocumentV1(
      value.envelope,
      items,
      document
    );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.aggregation_document_exactly_rebuilt, false);
  assert.equal(exact.aggregation_status, "UNKNOWN");
});

test("aggregate embeds no payload, public-key, signature, or private-key material", () => {
  const value = fixture("material-boundary");
  const document = aggregate(value);
  const serialized = JSON.stringify(document);
  for (const item of value.items) {
    const publicDer = item.pair.publicKey.export({ type: "spki", format: "der" });
    const privateDer = item.pair.privateKey.export({ type: "pkcs8", format: "der" });
    assert.equal(serialized.includes(item.payload.evidence_body.marker), false);
    assert.equal(serialized.includes(publicDer.toString("base64")), false);
    assert.equal(serialized.includes(item.detachedSignature.toString("base64")), false);
    assert.equal(serialized.includes(privateDer.toString("base64")), false);
    assert.equal(serialized.includes(privateDer.toString("hex")), false);
  }
  assert.equal(document.facts.evidence_payloads_embedded, false);
  assert.equal(document.facts.public_key_material_embedded, false);
  assert.equal(document.facts.signature_material_embedded, false);
  assert.equal(document.facts.private_key_material_received, false);
});
