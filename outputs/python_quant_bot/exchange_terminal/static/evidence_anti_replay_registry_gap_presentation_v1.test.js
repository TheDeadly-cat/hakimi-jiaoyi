"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const keyPossessionV1 = require("./evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js");
const projectionV1 = require("./evidence_anti_replay_registry_gap_projection_v1.js");
const cardV1 = require("./evidence_anti_replay_registry_gap_card_v1.js");
const fixtureV1 = require("./evidence_anti_replay_registry_gap_consumer_fixture_v1.js");

function hash(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex");
}

function verificationFixture(label = "presentation") {
  const verification = canonical.sealDocument(
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
      checks: [
        "registry_identity_preregistration_v1_exact",
        "registry_key_possession_policy_v1_exact",
        "registry_key_possession_challenge_v1_exact",
        "registry_detached_attestation_v1_exact",
        "ed25519_public_key_hash_matches_preregistration",
        "ed25519_detached_signature_verified",
        "registry_organization_identity_not_self_claimed",
        "external_adapter_conformance_not_self_claimed",
      ].map((name) => ({ blocking: true, name, ok: true })),
      decision:
        "PREREGISTERED_REGISTRY_ED25519_KEY_POSSESSION_VERIFIED_EXTERNAL_IDENTITY_AND_CONFORMANCE_UNVERIFIED",
      facts: {
        adapter_conformance_verified: false,
        durable_atomic_compare_and_consume_verified: false,
        external_endpoint_verified: false,
        external_linearizability_verified: false,
        local_node_contract_execution_observed: true,
        local_registry_key_possession_contract_complete: true,
        network_accessed: false,
        post_registration_receipt_issued: false,
        private_key_material_received: false,
        preregistered_public_key_hash_matched: true,
        public_key_material_embedded: false,
        public_key_material_received: true,
        raw_nonce_embedded: false,
        raw_nonce_received: true,
        registry_key_possession_verified: true,
        registry_organization_identity_verified: false,
        runtime_assets_accessed: false,
        signature_material_embedded: false,
        signature_material_received: true,
        signed_target_consumption_receipt_verified: false,
        target_consumption_receipt_issued: false,
        trusted_registry_time_verified: false,
      },
      local_registry_key_possession_status: "PASS",
      schema_version: keyPossessionV1.VERIFICATION_SCHEMA_VERSION,
      source: {
        attestation_hash: hash(`${label}:attestation`),
        challenge_hash: hash(`${label}:challenge`),
        key_algorithm: "Ed25519",
        policy_hash: hash(`${label}:policy`),
        preregistration_hash: hash(`${label}:preregistration`),
        public_key_spki_sha256: hash(`${label}:public-key`),
        registry_id: `synthetic.${label}.registry`,
        signed_payload: "STRICT_CANONICAL_REGISTRY_KEY_POSSESSION_CHALLENGE",
      },
      static_fingerprint: keyPossessionV1.VERIFICATION_STATIC_FINGERPRINT,
      status: "BLOCKED",
    },
    "verification_hash"
  );
  const exact = {
    adapter_conformance_verified: false,
    blockers: [],
    current_admission_allowed: false,
    external_linearizability_verified: false,
    live_order_allowed: false,
    local_registry_key_possession_status: "PASS",
    paper_authorized: false,
    post_registration_receipt_issued: false,
    presentation_mount_allowed: false,
    registry_key_possession_verified: true,
    registry_organization_identity_verified: false,
    runtime_gate_activation_allowed: false,
    schema_version: keyPossessionV1.EXACT_VERIFICATION_SCHEMA_VERSION,
    status: "PASS",
    target_consumption_receipt_issued: false,
    trusted_registry_time_verified: false,
    verification_document_exactly_rebuilt: true,
    verification_status: "BLOCKED",
    writer_allowed: false,
  };
  return { exact, verification };
}

function projection(label) {
  const source = verificationFixture(label);
  return projectionV1.buildAntiReplayRegistryGapProjectionV1(
    source.verification,
    source.exact
  );
}

test("exports exact projection contract and pinned source dependencies", () => {
  assert.equal(
    projectionV1.KEY_POSSESSION_IMPLEMENTATION_SHA256,
    crypto
      .createHash("sha256")
      .update(
        fs.readFileSync(
          path.join(
            __dirname,
            "evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js"
          )
        )
      )
      .digest("hex")
  );
  assert.deepEqual(projectionV1.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
});

test("projection preserves neutral stage order and blocked status", () => {
  const value = projection("stage-order");
  assert.equal(projectionV1.verifyAntiReplayRegistryGapProjectionV1(value), true);
  assert.equal(value.status, "BLOCKED");
  assert.deepEqual(value.stage_order, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(value.stages.source.state, "HASH_BOUND");
  assert.equal(value.stages.gap.state, "OPEN");
  assert.equal(value.stages.maturity.state, "LOCAL_ONLY");
  assert.equal(value.stages.permission.state, "LOCKED");
});

test("projection exposes exactly seven external gaps", () => {
  const value = projection("gaps");
  assert.equal(value.facts.gap_count, 7);
  assert.equal(value.stages.gap.items.length, 7);
  assert.equal(new Set(value.stages.gap.items.map((item) => item.id)).size, 7);
  assert.ok(value.stages.gap.items.every((item) => item.state !== "PASS"));
});

test("all projection authority and permission remain locked", () => {
  const value = projection("permission");
  assert.ok(Object.values(value.authority).every((flag) => flag === false));
  assert.ok(
    Object.entries(value.stages.permission).every(
      ([key, state]) => key === "state" || state === "LOCKED"
    )
  );
});

test("projection tamper and schema alias fail closed", () => {
  const source = verificationFixture("projection-tamper");
  const value = projectionV1.buildAntiReplayRegistryGapProjectionV1(
    source.verification,
    source.exact
  );
  const tampered = structuredClone(value);
  tampered.stages.permission.live = "OPEN";
  assert.equal(projectionV1.verifyAntiReplayRegistryGapProjectionV1(tampered), false);
  const body = structuredClone(value);
  delete body.projection_hash;
  body.schema_version = `${projectionV1.PROJECTION_SCHEMA_VERSION}.0`;
  const alias = canonical.sealDocument(body, "projection_hash");
  assert.equal(projectionV1.verifyAntiReplayRegistryGapProjectionV1(alias), false);
});

test("view model stays descriptive and local-only", () => {
  const view = cardV1.buildAntiReplayRegistryGapViewModelV1(projection("view"));
  assert.equal(view.status, "BLOCKED");
  assert.equal(view.stages[2].state, "LOCAL-ONLY");
  assert.equal(view.stages[3].state, "LOCKED");
  assert.equal(view.gaps.length, 7);
});

test("rendered card preserves source-to-permission order", () => {
  const html = cardV1.renderAntiReplayRegistryGapCardV1(projection("render-order"));
  const positions = ["SOURCE", "GAP", "MATURITY", "PERMISSION"].map((stage) =>
    html.indexOf(`data-stage="${stage}"`)
  );
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual(positions, [...positions].sort((left, right) => left - right));
});

test("rendered card has no promotional or permission language", () => {
  const html = cardV1.renderAntiReplayRegistryGapCardV1(projection("neutral-copy"));
  assert.equal(/\bREADY\b/i.test(html), false);
  assert.equal(/profit|return|alpha|win rate/i.test(html), false);
  assert.equal(/data-status="ready"/i.test(html), false);
  assert.ok(html.includes("EVIDENCE GAP"));
  assert.ok(html.includes("LOCAL-ONLY"));
});

test("rendered card contains hashes but no nonce or signature material", () => {
  const html = cardV1.renderAntiReplayRegistryGapCardV1(projection("materials"));
  assert.ok(html.includes("KEY HASH"));
  assert.ok(html.includes("VERIFY HASH"));
  assert.equal(/raw nonce|detached signature|private key/i.test(html), false);
});

test("consumer fixture remains sealed and unmounted", () => {
  const value = projection("fixture");
  const fixture = fixtureV1.buildAntiReplayRegistryGapPresentationConsumerFixtureV1(value);
  assert.equal(fixture.status, "UNMOUNTED");
  assert.equal(fixture.facts.mounted, false);
  assert.equal(fixture.facts.route_bound, false);
  assert.equal(fixture.facts.app_imported, false);
  assert.equal(fixture.facts.browser_visual_review_performed, false);
  assert.ok(Object.values(fixture.authority).every((flag) => flag === false));
});

test("consumer exact verifier PASS does not imply mount", () => {
  const value = projection("fixture-exact");
  const fixture = fixtureV1.buildAntiReplayRegistryGapPresentationConsumerFixtureV1(value);
  const exact = fixtureV1.verifyAntiReplayRegistryGapPresentationConsumerFixtureV1(
    value,
    fixture
  );
  assert.equal(exact.status, "PASS");
  assert.equal(exact.fixture_status, "UNMOUNTED");
  assert.equal(exact.mounted, false);
  assert.equal(exact.presentation_mount_allowed, false);
  assert.equal(exact.paper_authorized, false);
  assert.equal(exact.live_order_allowed, false);
});

test("consumer fixture tamper fails exact reconstruction", () => {
  const value = projection("fixture-tamper");
  const fixture = fixtureV1.buildAntiReplayRegistryGapPresentationConsumerFixtureV1(value);
  fixture.facts.mounted = true;
  const exact = fixtureV1.verifyAntiReplayRegistryGapPresentationConsumerFixtureV1(
    value,
    fixture
  );
  assert.equal(exact.status, "BLOCK");
  assert.equal(exact.fixture_status, "UNKNOWN");
  assert.equal(exact.presentation_mount_allowed, false);
});

test("stylesheet is scoped, responsive, and motion-aware", () => {
  const css = fs.readFileSync(
    path.join(__dirname, fixtureV1.STYLESHEET_ASSET),
    "utf8"
  );
  assert.ok(css.includes(".ar-gap-card"));
  assert.ok(css.includes("@media (max-width: 720px)"));
  assert.ok(css.includes("@media (prefers-reduced-motion: reduce)"));
  assert.equal(/(^|\n)\s*(body|html|:root)\b/.test(css), false);
  assert.equal(
    crypto
      .createHash("sha256")
      .update(fs.readFileSync(path.join(__dirname, "styles.css")))
      .digest("hex"),
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
  );
});
