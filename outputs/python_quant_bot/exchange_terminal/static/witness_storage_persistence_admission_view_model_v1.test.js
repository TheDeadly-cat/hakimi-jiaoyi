"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const subject = require("./witness_storage_persistence_admission_view_model_v1.js");

function authority() {
  return {
    descriptive_only: true,
    asset_write_allowed: false,
    browser_execution_allowed: false,
    route_registration_allowed: false,
    ui_consumer_mount_allowed: false,
    isolated_backend_test_allowed: false,
    backend_mount_allowed: false,
    current_admission_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function facts(mode) {
  const candidate = mode === "candidate";
  const exact = mode !== "unknown";
  return {
    source_decision_exactly_verified: exact,
    bounded_projection: true,
    structural_lineage_verified: candidate,
    isolated_backend_test_candidate: candidate,
    explicit_isolated_test_authorization_supplied: false,
    real_identity_source_truth_verified: false,
    external_observer_identity_verified: false,
    real_adapter_execution_verified: false,
    isolated_domain_confinement_verified: false,
    external_persistence_independently_verified: false,
    isolated_backend_test_authorized: false,
    backend_mount_authorized: false,
    snapshot_publication_authorized: false,
    current_chain_activated: false,
    raw_decision_document_embedded: false,
    raw_lineage_document_embedded: false,
    raw_component_hash_map_embedded: false,
    raw_key_material_embedded: false,
    raw_signature_material_embedded: false,
  };
}

function knownStages(mode) {
  const candidate = mode === "candidate";
  return [
    {
      axis: "SOURCE",
      state: "HASH_BOUND_LOCAL",
      reason_code: "EXACT_LOCAL_HASH_CHAIN_ONLY_EXTERNAL_TRUTH_UNVERIFIED",
    },
    {
      axis: "GAP",
      state: "OPEN",
      reason_code: candidate
        ? "SIX_EXTERNAL_AND_AUTHORIZATION_GAPS_OPEN"
        : "LINEAGE_BINDING_NOT_COMPLETE",
    },
    {
      axis: "MATURITY",
      state: candidate ? "STRUCTURAL_TEST_CANDIDATE" : "LINEAGE_INCOMPLETE",
      reason_code: candidate
        ? "STRUCTURAL_CANDIDATE_IS_NOT_TEST_AUTHORIZATION"
        : "STRUCTURAL_LINEAGE_REQUIREMENTS_NOT_COMPLETE",
    },
    {
      axis: "PERMISSION",
      state: "BLOCKED",
      reason_code: "DO_NOT_MOUNT_CURRENT_PAPER_LIVE_AND_WRITER_LOCKED",
    },
  ];
}

function projectionFixture(mode = "candidate") {
  const candidate = mode === "candidate";
  const blockers = candidate
    ? subject.PENDING_CONDITIONS.slice()
    : ["LINEAGE_BINDING_NOT_COMPLETE"];
  return strictCanonical.sealDocument({
    schema_version: subject.SOURCE_SCHEMA_VERSION,
    static_fingerprint: subject.SOURCE_STATIC_FINGERPRINT,
    presentation_status: "UNMOUNTED_RESEARCH_EVIDENCE",
    display_tone: "NEUTRAL",
    display_state: candidate
      ? "STRUCTURAL_LINEAGE_PRESENT_PERMISSION_BLOCKED"
      : "LINEAGE_INCOMPLETE_PERMISSION_BLOCKED",
    stage_order: subject.STAGE_ORDER.slice(),
    stages: knownStages(mode),
    source: {
      persistence_admission_decision_hash: "a".repeat(64),
      lineage_binding_hash: "b".repeat(64),
      lineage_bundle_hash: "c".repeat(64),
      lineage_implementation_sha256: "d".repeat(64),
    },
    summary: { blocker_count: blockers.length, component_count: 14 },
    facts: facts(mode),
    blockers,
    authority: authority(),
  }, "presentation_hash");
}

function unknownProjectionFixture() {
  const reason = "SOURCE_PERSISTENCE_ADMISSION_DECISION_NOT_EXACT";
  return strictCanonical.sealDocument({
    schema_version: subject.SOURCE_SCHEMA_VERSION,
    static_fingerprint: subject.SOURCE_STATIC_FINGERPRINT,
    presentation_status: "UNMOUNTED_UNKNOWN",
    display_tone: "NEUTRAL",
    display_state: "UNKNOWN",
    stage_order: subject.STAGE_ORDER.slice(),
    stages: [
      { axis: "SOURCE", state: "UNKNOWN", reason_code: reason },
      { axis: "GAP", state: "OPEN", reason_code: reason },
      { axis: "MATURITY", state: "UNKNOWN", reason_code: reason },
      {
        axis: "PERMISSION",
        state: "BLOCKED",
        reason_code: "CURRENT_AND_EXECUTION_PERMISSIONS_BLOCKED",
      },
    ],
    source: {
      persistence_admission_decision_hash: null,
      lineage_binding_hash: null,
      lineage_bundle_hash: null,
      lineage_implementation_sha256: null,
    },
    summary: { blocker_count: null, component_count: null },
    facts: facts("unknown"),
    blockers: [reason],
    authority: authority(),
  }, "presentation_hash");
}

function build(projection = projectionFixture(), expectedHash = null) {
  return subject.buildWitnessStoragePersistenceAdmissionViewModelV1(
    projection,
    expectedHash || projection.presentation_hash
  );
}

test("exact projection maps to neutral source gap maturity permission", () => {
  const view = build();
  assert.equal(view.status, "BLOCKED");
  assert.equal(view.contract_state, "LOCAL_RESEARCH_EVIDENCE");
  assert.equal(view.tone, "NEUTRAL");
  assert.deepEqual(view.stage_order, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(view.sections[3].state, "BLOCKED");
});

test("structural candidate remains unmounted and unauthorized", () => {
  const view = build();
  assert.equal(view.maturity.state, "STRUCTURAL_TEST_CANDIDATE");
  assert.equal(view.maturity.isolated_backend_test_candidate, true);
  assert.equal(view.permission.isolated_backend_test_allowed, false);
  assert.equal(view.permission.backend_mount_allowed, false);
  assert.equal(view.permission.current_admission_allowed, false);
});

test("out of band expected presentation hash is mandatory", () => {
  const projection = projectionFixture();
  const view = build(projection, "f".repeat(64));
  assert.equal(view.status, "UNKNOWN");
  assert.equal(view.facts.source_projection_contract_verified, false);
  assert.equal(view.permission.state, "BLOCKED");
});

test("resealed hash substitution fails against the original commitment", () => {
  const projection = projectionFixture();
  const expected = projection.presentation_hash;
  projection.source.lineage_binding_hash = "e".repeat(64);
  delete projection.presentation_hash;
  const resealed = strictCanonical.sealDocument(projection, "presentation_hash");
  assert.equal(build(resealed, expected).status, "UNKNOWN");
});

test("resealed authority promotion fails even with its new hash", () => {
  const projection = projectionFixture();
  projection.authority.backend_mount_allowed = true;
  delete projection.presentation_hash;
  const resealed = strictCanonical.sealDocument(projection, "presentation_hash");
  assert.equal(build(resealed, resealed.presentation_hash).status, "UNKNOWN");
});

test("extra source fields are rejected and never echoed", () => {
  const projection = projectionFixture();
  projection.private_storage_locator = "must-not-echo";
  delete projection.presentation_hash;
  const resealed = strictCanonical.sealDocument(projection, "presentation_hash");
  const serialized = JSON.stringify(build(resealed, resealed.presentation_hash));
  assert.equal(serialized.includes("must-not-echo"), false);
});

test("exact unknown projection remains unknown with permission blocked", () => {
  const projection = unknownProjectionFixture();
  const view = build(projection);
  assert.equal(view.status, "UNKNOWN");
  assert.equal(view.facts.source_projection_contract_verified, true);
  assert.equal(view.facts.source_projection_known, false);
  assert.equal(view.permission.state, "BLOCKED");
});

test("cycles accessors custom prototypes and oversized strings fail closed", () => {
  const cyclic = projectionFixture();
  cyclic.loop = cyclic;
  assert.equal(build(cyclic).status, "UNKNOWN");

  let getterInvoked = false;
  const accessor = {};
  Object.defineProperty(accessor, "schema_version", {
    enumerable: true,
    get() {
      getterInvoked = true;
      return subject.SOURCE_SCHEMA_VERSION;
    },
  });
  assert.equal(build(accessor, "a".repeat(64)).status, "UNKNOWN");
  assert.equal(getterInvoked, false);

  const customPrototype = Object.create({ inherited: true });
  customPrototype.presentation_hash = "a".repeat(64);
  assert.equal(build(customPrototype).status, "UNKNOWN");

  const oversized = projectionFixture();
  oversized.display_state = "x".repeat(subject.INPUT_LIMITS.max_string_length + 1);
  assert.equal(build(oversized).status, "UNKNOWN");
});

test("view model contains hashes and bounded counts but no source documents", () => {
  const view = build();
  assert.match(view.source.presentation_hash, /^[0-9a-f]{64}$/);
  assert.match(view.source.lineage_binding_hash, /^[0-9a-f]{64}$/);
  assert.equal(view.summary.blocker_count, 6);
  assert.equal(view.summary.component_count, 14);
  assert.equal(view.facts.raw_source_projection_embedded, false);
  assert.equal(view.facts.raw_decision_document_embedded, false);
  assert.equal(view.facts.raw_lineage_document_embedded, false);
});

test("all operational authority remains false", () => {
  const view = build();
  assert.equal(Object.values(view.authority).every((value) => value === false), true);
  assert.equal(view.facts.dom_mounted, false);
  assert.equal(view.facts.current_activated, false);
  assert.equal(view.facts.runtime_mutations_performed, false);
});

test("view model is deterministic and exact verifier rejects promotion", () => {
  const projection = projectionFixture();
  const first = build(projection);
  assert.deepEqual(first, build(projection));
  assert.equal(
    subject.verifyWitnessStoragePersistenceAdmissionViewModelV1(
      first,
      projection,
      projection.presentation_hash
    ),
    true
  );
  const promoted = JSON.parse(JSON.stringify(first));
  promoted.permission.backend_mount_allowed = true;
  delete promoted.view_model_hash;
  const resealed = strictCanonical.sealDocument(promoted, "view_model_hash");
  assert.equal(
    subject.verifyWitnessStoragePersistenceAdmissionViewModelV1(
      resealed,
      projection,
      projection.presentation_hash
    ),
    false
  );
});

test("serialized view model contains no promotional or directional wording", () => {
  const forbidden = new RegExp(
    "\\b(?:" + ["REA", "DY|PRO", "FIT|RET", "URN|B", "UY|S", "ELL"].join("") + ")\\b",
    "i"
  );
  assert.equal(forbidden.test(JSON.stringify(build())), false);
});

test("production module is unmounted and has no DOM or network operation", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "witness_storage_persistence_admission_view_model_v1.js"),
    "utf8"
  );
  assert.equal(source.includes("document."), false);
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("WebSocket"), false);
  assert.equal(source.includes("eval("), false);
});
