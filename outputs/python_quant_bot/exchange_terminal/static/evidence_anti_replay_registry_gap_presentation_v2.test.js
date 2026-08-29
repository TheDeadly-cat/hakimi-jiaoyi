"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const projectionV1 = require("./evidence_anti_replay_registry_gap_projection_v1.js");
const aggregationV1 = require(
  "./evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js"
);
const projectionV2 = require("./evidence_anti_replay_registry_gap_projection_v2.js");
const cardV2 = require("./evidence_anti_replay_registry_gap_card_v2.js");
const fixtureV2 = require("./evidence_anti_replay_registry_gap_consumer_fixture_v2.js");

function hash(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex");
}

function fileHash(...parts) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(path.join(__dirname, ...parts)))
    .digest("hex");
}

function predecessor(registryId, publicKeyHash, label) {
  const projection = canonical.sealDocument(
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
        "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
        "EXTERNAL_ADAPTER_CONFORMANCE_UNVERIFIED",
        "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
        "DURABLE_ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
        "TRUSTED_REGISTRY_TIME_UNVERIFIED",
        "SIGNED_TARGET_CONSUMPTION_RECEIPT_V1_MISSING",
        "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
      ],
      decision:
        "LOCAL_REGISTRY_KEY_POSSESSION_OBSERVED_EXTERNAL_EVIDENCE_GAPS_REMAIN",
      facts: {
        adapter_conformance_verified: false,
        external_linearizability_verified: false,
        gap_count: 7,
        local_registry_key_possession_verified: true,
        post_registration_receipt_issued: false,
        projection_descriptive_only: true,
        registry_organization_identity_verified: false,
        target_consumption_receipt_issued: false,
        trusted_registry_time_verified: false,
      },
      schema_version: projectionV1.PROJECTION_SCHEMA_VERSION,
      source: {
        attestation_hash: hash(label + ":attestation"),
        challenge_hash: hash(label + ":challenge"),
        key_algorithm: "Ed25519",
        policy_hash: hash(label + ":policy"),
        preregistration_hash: hash(label + ":preregistration"),
        public_key_spki_sha256: publicKeyHash,
        registry_id: registryId,
        verification_hash: hash(label + ":verification"),
      },
      stage_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
      stages: {
        gap: {
          items: projectionV1.GAP_ITEMS.map((item) => ({ ...item })),
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
          contract:
            "anti-replay-registry-ed25519-key-possession-verification-candidate-v1",
          local_key_possession: "PASS",
          state: "HASH_BOUND",
        },
      },
      static_fingerprint: projectionV1.PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "projection_hash"
  );
  const exact = {
    blockers: [],
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    projection_document_exactly_rebuilt: true,
    projection_status: "BLOCKED",
    runtime_gate_activation_allowed: false,
    schema_version: "anti-replay-registry-gap-projection-exact-rebuild-v1",
    status: "PASS",
    writer_allowed: false,
  };
  return { exact, projection };
}

function aggregation(registryId, publicKeyHash, label) {
  const kinds = aggregationV1.EVIDENCE_KINDS;
  const artifacts = kinds.map((kind) => ({
    artifact_sha256: hash(label + ":" + kind + ":artifact"),
    evidence_kind: kind,
    evidence_reference_sha256: hash(label + ":" + kind + ":reference"),
    evidence_schema_version: "synthetic-" + kind.toLowerCase() + "-v1",
    evidence_signature_verified: true,
    local_signed_artifact_status: "PASS",
    signature_sha256: hash(label + ":" + kind + ":signature"),
    signer_public_key_spki_sha256: hash(label + ":" + kind + ":key"),
    signer_role: "synthetic_" + kind.toLowerCase() + "_role",
    verification_hash: hash(label + ":" + kind + ":verification"),
    verification_status: "BLOCKED",
  }));
  const document = canonical.sealDocument(
    {
      artifacts,
      authority: {
        current_admission_allowed: false,
        evidence_bundle_admission_allowed: false,
        live_order_allowed: false,
        paper_authorized: false,
        presentation_mount_allowed: false,
        registry_identity_admission_allowed: false,
        runtime_gate_activation_allowed: false,
        signed_artifact_aggregation_activation_allowed: false,
        writer_allowed: false,
      },
      blockers: [
        "PYTHON_PROCESS_AUTHENTICATION_UNVERIFIED",
        "EVIDENCE_PAYLOAD_SEMANTICS_UNVERIFIED",
        "SIGNER_ROLE_IDENTITY_UNVERIFIED",
        "EXTERNAL_SOURCE_TRUST_UNPROVEN",
        "REVOCATION_CONTENT_UNVERIFIED",
        "REGISTRY_ORGANIZATION_IDENTITY_UNVERIFIED",
      ],
      checks: [
        "python_bundle_verification_envelope_v1_exact",
        "one_signed_artifact_per_evidence_kind_exact",
        "normalized_reference_set_hash_matches_python_envelope",
        "all_reference_subjects_match_python_envelope",
        "all_references_fresh_at_python_envelope_reference_time",
        "all_signer_roles_distinct",
        "all_signer_public_keys_distinct",
        "all_artifact_hashes_distinct",
        "all_six_signed_artifact_exact_verifiers_pass",
      ].map((name) => ({ blocking: true, name, ok: true })),
      decision:
        "SIX_SIGNED_ARTIFACTS_CRYPTOGRAPHICALLY_BOUND_PROCESS_SEMANTICS_SOURCE_ROLE_AND_IDENTITY_UNVERIFIED",
      facts: {
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
      },
      local_signed_artifact_bundle_status:
        aggregationV1.LOCAL_PASS_STATUS,
      schema_version: aggregationV1.AGGREGATION_SCHEMA_VERSION,
      source: {
        evidence_reference_count: 6,
        evidence_reference_set_sha256: hash(label + ":reference-set"),
        public_key_spki_sha256: publicKeyHash,
        python_envelope_hash: hash(label + ":envelope"),
        python_envelope_implementation_sha256:
          aggregationV1.PYTHON_ENVELOPE_IMPLEMENTATION_SHA256,
        reference_time_ms: 10_000_000,
        registry_id: registryId,
        signed_artifact_candidate_implementation_sha256:
          aggregationV1.SIGNED_ARTIFACT_CANDIDATE_IMPLEMENTATION_SHA256,
        trust_domain: "synthetic." + label + ".test",
      },
      static_fingerprint: aggregationV1.AGGREGATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "aggregation_hash"
  );
  const exact = {
    aggregation_document_exactly_rebuilt: true,
    aggregation_status: "BLOCKED",
    blockers: [],
    current_admission_allowed: false,
    evidence_bundle_admission_allowed: false,
    evidence_payloads_semantics_verified: false,
    evidence_signatures_verified: true,
    external_source_trust_verified: false,
    live_order_allowed: false,
    local_signed_artifact_bundle_status:
      aggregationV1.LOCAL_PASS_STATUS,
    paper_authorized: false,
    presentation_mount_allowed: false,
    python_process_authenticated: false,
    registry_identity_admission_allowed: false,
    registry_organization_identity_verified: false,
    revocation_content_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: aggregationV1.EXACT_VERIFICATION_SCHEMA_VERSION,
    signed_artifact_aggregation_activation_allowed: false,
    signer_role_identity_verified: false,
    status: "PASS",
    writer_allowed: false,
  };
  return { document, exact };
}

function fixture(label = "presentation-v2") {
  const registryId = "synthetic." + label + ".registry";
  const publicKeyHash = hash(label + ":registry-key");
  const predecessorValue = predecessor(registryId, publicKeyHash, label);
  const aggregateValue = aggregation(registryId, publicKeyHash, label);
  const projection = projectionV2.buildAntiReplayRegistryGapProjectionV2(
    predecessorValue.projection,
    predecessorValue.exact,
    aggregateValue.document,
    aggregateValue.exact
  );
  return { aggregateValue, predecessorValue, projection };
}

test("v2 pins frozen v1, aggregation, stylesheet, and shared CSS", () => {
  assert.equal(
    fileHash("evidence_anti_replay_registry_gap_projection_v1.js"),
    projectionV2.PROJECTION_V1_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash(
      "evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js"
    ),
    projectionV2.AGGREGATION_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash(fixtureV2.STYLESHEET_ASSET),
    fixtureV2.STYLESHEET_IMPLEMENTATION_SHA256
  );
  assert.equal(
    fileHash("styles.css"),
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
  );
});

test("v2 preserves neutral stage order and blocked status", () => {
  const value = fixture("stage-order").projection;
  assert.equal(projectionV2.verifyAntiReplayRegistryGapProjectionV2(value), true);
  assert.equal(value.status, "BLOCKED");
  assert.deepEqual(value.stage_order, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(value.stages.source.state, "HASH-BOUND");
  assert.equal(value.stages.gap.state, "OPEN");
  assert.equal(value.stages.maturity.state, "LOCAL-CRYPTOGRAPHIC-ONLY");
  assert.equal(value.stages.permission.state, "LOCKED");
});

test("identity ledger separates two local observations from six gaps", () => {
  const value = fixture("ledger").projection;
  assert.equal(value.identity_evidence.state, "INCOMPLETE");
  assert.equal(value.identity_evidence.local_observation_count, 2);
  assert.equal(value.identity_evidence.unverified_count, 6);
  assert.equal(
    value.identity_evidence.ledger.filter(
      (row) => row.state === "OBSERVED-LOCAL"
    ).length,
    2
  );
  assert.equal(
    value.identity_evidence.ledger.filter(
      (row) => row.state === "UNVERIFIED"
    ).length,
    6
  );
  assert.equal(
    value.stages.gap.items.find(
      (row) => row.id === "ORGANIZATION_IDENTITY"
    ).state,
    "OPEN"
  );
});

test("view model remains descriptive and permission-locked", () => {
  const view = cardV2.buildAntiReplayRegistryGapViewModelV2(
    fixture("view").projection
  );
  assert.equal(view.status, "BLOCKED");
  assert.equal(view.identity_ledger.length, 8);
  assert.equal(view.gaps.length, 7);
  assert.equal(view.stages[2].state, "LOCAL-CRYPTOGRAPHIC");
  assert.equal(view.stages[3].state, "LOCKED");
  assert.ok(view.permission_locks.includes("IDENTITY"));
  assert.ok(view.permission_locks.includes("LIVE"));
});

test("rendered card preserves source-to-permission order and both ledgers", () => {
  const html = cardV2.renderAntiReplayRegistryGapCardV2(
    fixture("render-order").projection
  );
  const positions = ["SOURCE", "GAP", "MATURITY", "PERMISSION"].map(
    (stage) => html.indexOf('data-stage="' + stage + '"')
  );
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
  assert.ok(html.includes("IDENTITY EVIDENCE LEDGER"));
  assert.ok(html.includes("OPEN SYSTEM GAP REGISTER"));
});

test("rendered copy has no promotional or permission implication", () => {
  const html = cardV2.renderAntiReplayRegistryGapCardV2(
    fixture("neutral-copy").projection
  );
  assert.equal(/\bREADY\b/i.test(html), false);
  assert.equal(/profit|return|alpha|win rate/i.test(html), false);
  assert.equal(/data-status="ready"/i.test(html), false);
  assert.ok(html.includes("EVIDENCE GAP"));
  assert.ok(html.includes("UNVERIFIED"));
  assert.ok(html.includes("LOCKED"));
});

test("projection exact verifier separates exact presentation from authority", () => {
  const value = fixture("projection-exact");
  const exact = projectionV2.verifyAntiReplayRegistryGapProjectionExactV2(
    value.predecessorValue.projection,
    value.predecessorValue.exact,
    value.aggregateValue.document,
    value.aggregateValue.exact,
    value.projection
  );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.projection_status, "BLOCKED");
  assert.equal(exact.registry_identity_admission_allowed, false);
  assert.equal(exact.evidence_bundle_admission_allowed, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
});

test("registry id or key-hash mismatch is rejected", () => {
  const value = fixture("binding-mismatch");
  const document = structuredClone(value.aggregateValue.document);
  delete document.aggregation_hash;
  document.source.registry_id = "synthetic.substituted.registry";
  const substituted = canonical.sealDocument(document, "aggregation_hash");
  assert.throws(
    () =>
      projectionV2.buildAntiReplayRegistryGapProjectionV2(
        value.predecessorValue.projection,
        value.predecessorValue.exact,
        substituted,
        value.aggregateValue.exact
      ),
    /do not match/
  );
});

test("aggregate identity promotion evidence is rejected", () => {
  const value = fixture("aggregate-promotion");
  const promoted = { ...value.aggregateValue.exact };
  promoted.registry_organization_identity_verified = true;
  assert.throws(
    () =>
      projectionV2.buildAntiReplayRegistryGapProjectionV2(
        value.predecessorValue.projection,
        value.predecessorValue.exact,
        value.aggregateValue.document,
        promoted
      ),
    /not exact/
  );
});

test("consumer fixture remains sealed, unmounted, and stylesheet-reusing", () => {
  const projection = fixture("fixture").projection;
  const consumer =
    fixtureV2.buildAntiReplayRegistryGapPresentationConsumerFixtureV2(
      projection
    );
  const exact =
    fixtureV2.verifyAntiReplayRegistryGapPresentationConsumerFixtureV2(
      projection,
      consumer
    );
  assert.equal(consumer.status, "UNMOUNTED");
  assert.equal(consumer.facts.mounted, false);
  assert.equal(consumer.facts.route_bound, false);
  assert.equal(consumer.facts.app_imported, false);
  assert.equal(consumer.facts.browser_visual_review_performed, false);
  assert.equal(consumer.facts.stylesheet_reused_without_modification, true);
  assert.equal(exact.status, "PASS");
  assert.equal(exact.fixture_status, "UNMOUNTED");
  assert.equal(exact.presentation_mount_allowed, false);
});

test("projection and fixture tampering fail exact reconstruction", () => {
  const value = fixture("tamper");
  const projection = structuredClone(value.projection);
  projection.stages.permission.live = "OPEN";
  const projectionExact =
    projectionV2.verifyAntiReplayRegistryGapProjectionExactV2(
      value.predecessorValue.projection,
      value.predecessorValue.exact,
      value.aggregateValue.document,
      value.aggregateValue.exact,
      projection
    );
  assert.equal(projectionExact.status, "BLOCK");
  assert.equal(projectionExact.projection_status, "UNKNOWN");
  const consumer =
    fixtureV2.buildAntiReplayRegistryGapPresentationConsumerFixtureV2(
      value.projection
    );
  consumer.facts.mounted = true;
  const fixtureExact =
    fixtureV2.verifyAntiReplayRegistryGapPresentationConsumerFixtureV2(
      value.projection,
      consumer
    );
  assert.equal(fixtureExact.status, "BLOCK");
  assert.equal(fixtureExact.fixture_status, "UNKNOWN");
  assert.equal(fixtureExact.mounted, false);
});
