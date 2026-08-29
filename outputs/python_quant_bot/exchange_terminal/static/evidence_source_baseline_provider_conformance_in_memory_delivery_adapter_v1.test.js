"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const canonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_source_baseline_provider_conformance_card_v1.js");
const adapter = require(
  "./evidence_source_baseline_provider_conformance_in_memory_delivery_adapter_v1.js"
);

function payloadFixture() {
  return canonical.sealDocument(
    {
      schema_version: card.PAYLOAD_SCHEMA_VERSION,
      static_fingerprint: card.PAYLOAD_STATIC_FINGERPRINT,
      status: "BLOCKED",
      consumer_status: "PAYLOAD_BUILT_CONSUMER_UNREGISTERED",
      reason_code:
        "BOUNDED_PAYLOAD_BUILT_ASSETS_ROUTE_BROWSER_AND_MOUNT_ABSENT",
      source_envelope_hash: "1".repeat(64),
      consumer_preregistration_hash: card.CONSUMER_PREREGISTRATION_HASH,
      payload: {
        display_tone: "NEUTRAL",
        display_state: "SOURCE_BOUND_CONFORMANCE_NOT_RUN_PERMISSION_BLOCKED",
        ordered_stage_contract: ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        axes: [
          { detail: "V1_IDENTITY_AND_SOURCE_TRUST_EXACT_V2_BINDING_BLOCKED", stage: "SOURCE", state: "BOUND" },
          { detail: "EXTERNAL_IDENTITY_TRUST_CONFORMANCE_ATOMICITY_DURABILITY_UNVERIFIED", stage: "GAP", state: "OPEN" },
          { detail: "14_REQUIRED_CASES_0_EXECUTED_0_PASSED", stage: "MATURITY", state: "PREREGISTERED_NOT_RUN" },
          { detail: "PROVIDER_HTTP_UI_CURRENT_PAPER_LIVE_DISABLED", stage: "PERMISSION", state: "BLOCKED" },
        ],
        summary: { source_document_count: 6, required_case_count: 14, executed_case_count: 0, passed_case_count: 0, open_gap_count: 7 },
        blockers: [
          "EXTERNAL_REGISTRY_IDENTITY_UNVERIFIED",
          "EXTERNAL_SOURCE_TRUST_UNVERIFIED",
          "PROVIDER_CONFORMANCE_CASES_NOT_RUN",
          "ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
          "LINEARIZABILITY_UNVERIFIED",
          "DURABLE_COMMIT_UNVERIFIED",
          "AUTHENTICATED_CONSUMPTION_RECEIPT_NOT_ISSUED",
        ],
        permission: { state: "BLOCKED", provider_call_allowed: false, writer_allowed: false, route_registration_allowed: false, ui_consumer_mount_allowed: false, current_admission_allowed: false, paper_authorized: false, live_order_allowed: false },
      },
      facts: { source_envelope_exactly_verified: true, preregistration_exactly_verified: true, bounded_payload_built: true, source_lineage_details_embedded: false, raw_source_documents_embedded: false, raw_identity_material_embedded: false, consumer_implementation_present: false, asset_manifest_complete: false, browser_executed: false, route_registered: false, ui_mounted: false, current_activated: false, runtime_mutations_performed: false, profitability_proven: false },
      authority: { descriptive_only: true, asset_write_allowed: false, browser_execution_allowed: false, route_registration_allowed: false, ui_consumer_mount_allowed: false, current_admission_allowed: false, paper_authorized: false, live_order_allowed: false },
    },
    "payload_candidate_hash"
  );
}

function envelopeFixture() {
  const payload = payloadFixture();
  return canonical.sealDocument(
    {
      schema_version: adapter.SCHEMA_VERSION,
      static_fingerprint: adapter.STATIC_FINGERPRINT,
      status: "BLOCKED",
      delivery_state: "IN_MEMORY_DOCUMENT_BUILT_ENDPOINT_UNBOUND",
      reason_code:
        "EXACT_BOUNDED_PAYLOAD_EMBEDDED_IN_MEMORY_WIRE_ENDPOINT_ROUTE_CONSUMER_RENDER_BROWSER_AND_MOUNT_ABSENT",
      transport: { mode: "IN_MEMORY_JSON_DOCUMENT", media_type: "application/json", encoding: "UTF-8", cache_policy: "NO_STORE", endpoint: null, route: null, wire_bytes_built: false, network_transport_used: false, persistent_storage_used: false },
      consumer_contract: { payload_schema_version: card.PAYLOAD_SCHEMA_VERSION, payload_static_fingerprint: card.PAYLOAD_STATIC_FINGERPRINT, javascript_adapter_global: "HakimiSourceBaselineProviderConformanceInMemoryDeliveryAdapterV1", javascript_verify_function: "verifyInMemoryPayloadDeliveryEnvelopeV1", javascript_extract_function: "extractPayloadCandidateFromInMemoryEnvelopeV1", javascript_receipt_function: "buildInMemoryPayloadConsumptionReceiptCandidateV1" },
      provenance: { load_descriptor_schema_version: "source-baseline-provider-conformance-application-load-descriptor-preregistration-v1", load_descriptor_binding_schema_version: "source-baseline-provider-conformance-application-load-descriptor-binding-candidate-v1", load_descriptor_static_fingerprint: "20260823-source-baseline-provider-conformance-load-descriptor-v1-lock-1", load_descriptor_implementation_sha256: adapter.LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256, load_descriptor_binding_hash: "2".repeat(64), load_descriptor_hash: adapter.LOAD_DESCRIPTOR_HASH, style_binding_hash: "3".repeat(64), payload_candidate_hash: payload.payload_candidate_hash, source_envelope_hash: payload.source_envelope_hash },
      payload_candidate: payload,
      facts: { descriptor_binding_exactly_verified: true, payload_hash_matches_descriptor_binding: true, bounded_payload_embedded: true, raw_source_documents_embedded: false, raw_identity_material_embedded: false, wire_bytes_built: false, delivery_attempted: false, network_accessed: false, endpoint_present: false, route_registered: false, persistent_storage_used: false, consumer_executed: false, card_render_called: false, dom_accessed: false, browser_executed: false, ui_mounted: false, current_activated: false, runtime_mutations_performed: false, profitability_proven: false },
      authority: { descriptive_only: true, wire_transport_allowed: false, endpoint_registration_allowed: false, route_registration_allowed: false, persistent_storage_allowed: false, consumer_execution_allowed: false, card_render_allowed: false, dom_access_allowed: false, browser_execution_allowed: false, ui_consumer_mount_allowed: false, current_admission_allowed: false, paper_authorized: false, live_order_allowed: false },
    },
    "delivery_envelope_hash"
  );
}

function reseal(mutator) {
  const value = structuredClone(envelopeFixture());
  delete value.delivery_envelope_hash;
  mutator(value);
  return canonical.sealDocument(value, "delivery_envelope_hash");
}

test("accepts exact blocked in-memory envelope", () => {
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(envelopeFixture()), true);
});

test("extracts an exact card payload without mutation", () => {
  const envelope = envelopeFixture();
  const payload = adapter.extractPayloadCandidateFromInMemoryEnvelopeV1(envelope);
  assert.equal(card.verifySourceBaselineProviderConformancePayloadCandidateV1(payload), true);
  assert.deepEqual(payload, envelope.payload_candidate);
  assert.notEqual(payload, envelope.payload_candidate);
});

test("builds sealed blocked extraction receipt without render", () => {
  const envelope = envelopeFixture();
  const receipt = adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope);
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.consumption_state, "PAYLOAD_EXTRACTED_IN_MEMORY_DOM_RENDER_NOT_EXECUTED");
  assert.equal(receipt.facts.card_render_called, false);
  assert.equal(canonical.verifySealedDocument(receipt, "consumption_receipt_hash"), true);
  assert.equal(adapter.verifyInMemoryPayloadConsumptionReceiptCandidateV1(envelope, receipt), true);
});

test("transport remains endpoint, route, wire, network, and storage free", () => {
  const transport = envelopeFixture().transport;
  assert.equal(transport.endpoint, null);
  assert.equal(transport.route, null);
  assert.equal(transport.wire_bytes_built, false);
  assert.equal(transport.network_transport_used, false);
  assert.equal(transport.persistent_storage_used, false);
});

test("rejects invalid seal and extra field", () => {
  const invalid = envelopeFixture();
  invalid.delivery_envelope_hash = "0".repeat(64);
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(invalid), false);
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.synthetic = true; })), false);
});

test("rejects endpoint, route, or network promotion", () => {
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.transport.endpoint = "/api/synthetic"; })), false);
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.transport.route = "/synthetic"; })), false);
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.transport.network_transport_used = true; })), false);
});

test("rejects delivery, render, DOM, browser, or mount promotion", () => {
  for (const field of ["delivery_attempted", "card_render_called", "dom_accessed", "browser_executed", "ui_mounted"]) {
    assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.facts[field] = true; })), false);
  }
});

test("rejects payload tone and permission promotion", () => {
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.payload_candidate.payload.display_tone = "POSITIVE"; })), false);
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.payload_candidate.payload.permission.ui_consumer_mount_allowed = true; })), false);
});

test("rejects nested payload hash mismatch", () => {
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.provenance.payload_candidate_hash = "f".repeat(64); })), false);
});

test("rejects authority promotion", () => {
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(reseal((value) => { value.authority.consumer_execution_allowed = true; })), false);
});

test("receipt promotion fails exact verification", () => {
  const envelope = envelopeFixture();
  const receipt = adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope);
  delete receipt.consumption_receipt_hash;
  receipt.facts.card_render_called = true;
  const promoted = canonical.sealDocument(receipt, "consumption_receipt_hash");
  assert.equal(adapter.verifyInMemoryPayloadConsumptionReceiptCandidateV1(envelope, promoted), false);
});

test("one-time snapshot blocks second-read envelope hash substitution", () => {
  const envelope = envelopeFixture();
  let reads = 0;
  const proxy = new Proxy(envelope, { get(target, property, receiver) { if (property === "delivery_envelope_hash") { reads += 1; if (reads >= 2) return "f".repeat(64); } return Reflect.get(target, property, receiver); } });
  const receipt = adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(proxy);
  assert.equal(reads, 1);
  assert.equal(receipt.delivery_envelope_hash, envelope.delivery_envelope_hash);
});

test("throwing getter and cyclic input fail closed", () => {
  const throwing = envelopeFixture();
  Object.defineProperty(throwing, "status", { enumerable: true, get() { throw new Error("synthetic getter failure"); } });
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(throwing), false);
  const cyclic = {}; cyclic.self = cyclic;
  assert.equal(adapter.verifyInMemoryPayloadDeliveryEnvelopeV1(cyclic), false);
});

test("adapter leaves source envelope unchanged", () => {
  const envelope = envelopeFixture();
  const before = canonical.strictCanonicalStringify(envelope);
  adapter.extractPayloadCandidateFromInMemoryEnvelopeV1(envelope);
  adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope);
  assert.equal(canonical.strictCanonicalStringify(envelope), before);
});

test("adapter output contains no promotional language", () => {
  const receipt = adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelopeFixture());
  const text = JSON.stringify(receipt);
  assert.equal(/\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate/i.test(text), false);
  assert.equal(receipt.facts.profitability_proven, false);
});

test("extraction and receipt are deterministic", () => {
  const envelope = envelopeFixture();
  assert.deepEqual(adapter.extractPayloadCandidateFromInMemoryEnvelopeV1(envelope), adapter.extractPayloadCandidateFromInMemoryEnvelopeV1(envelope));
  assert.deepEqual(adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope), adapter.buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope));
});
