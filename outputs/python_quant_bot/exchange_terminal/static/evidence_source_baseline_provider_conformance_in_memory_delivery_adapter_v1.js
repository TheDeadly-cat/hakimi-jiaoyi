(function initInMemoryDeliveryAdapter(root, factory) {
  "use strict";

  const hasCommonJs =
    typeof module === "object" && module && module.exports;
  const canonical = hasCommonJs
    ? require("./strict_canonical_json_v1.js")
    : root && root.HakimiStrictCanonicalJsonV1;
  const card = hasCommonJs
    ? require("./evidence_source_baseline_provider_conformance_card_v1.js")
    : root && root.HakimiSourceBaselineProviderConformanceCardV1;
  const api = factory(canonical, card);
  if (hasCommonJs) {
    module.exports = api;
  } else if (root && typeof root === "object") {
    root.HakimiSourceBaselineProviderConformanceInMemoryDeliveryAdapterV1 = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi(canonical, card) {
  "use strict";

  if (
    !canonical ||
    typeof canonical.isPlainRecord !== "function" ||
    typeof canonical.sealDocument !== "function" ||
    typeof canonical.strictCanonicalStringify !== "function" ||
    typeof canonical.verifySealedDocument !== "function" ||
    !card ||
    typeof card.verifySourceBaselineProviderConformancePayloadCandidateV1 !==
      "function"
  ) {
    throw new TypeError("strict canonical JSON and neutral card v1 are required");
  }

  const SCHEMA_VERSION =
    "source-baseline-provider-conformance-in-memory-payload-delivery-envelope-v1";
  const RECEIPT_SCHEMA_VERSION =
    "source-baseline-provider-conformance-in-memory-payload-consumption-receipt-candidate-v1";
  const STATIC_FINGERPRINT =
    "20260823-source-baseline-provider-conformance-in-memory-delivery-v1-lock-1";
  const LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256 =
    "9bcd1f37f8c0ef85ddcfffed65dd1104b7317567e69972ad1469cf55886e7ae5";
  const LOAD_DESCRIPTOR_HASH =
    "a842fe43de8b8c2b7bdd2c2978dfb4d09f03ca49aa8555d2ab3edcbe7cdbd7b2";

  const EXPECTED_TRANSPORT = Object.freeze({
    mode: "IN_MEMORY_JSON_DOCUMENT",
    media_type: "application/json",
    encoding: "UTF-8",
    cache_policy: "NO_STORE",
    endpoint: null,
    route: null,
    wire_bytes_built: false,
    network_transport_used: false,
    persistent_storage_used: false,
  });
  const EXPECTED_FACTS = Object.freeze({
    descriptor_binding_exactly_verified: true,
    payload_hash_matches_descriptor_binding: true,
    bounded_payload_embedded: true,
    raw_source_documents_embedded: false,
    raw_identity_material_embedded: false,
    wire_bytes_built: false,
    delivery_attempted: false,
    network_accessed: false,
    endpoint_present: false,
    route_registered: false,
    persistent_storage_used: false,
    consumer_executed: false,
    card_render_called: false,
    dom_accessed: false,
    browser_executed: false,
    ui_mounted: false,
    current_activated: false,
    runtime_mutations_performed: false,
    profitability_proven: false,
  });
  const EXPECTED_AUTHORITY = Object.freeze({
    descriptive_only: true,
    wire_transport_allowed: false,
    endpoint_registration_allowed: false,
    route_registration_allowed: false,
    persistent_storage_allowed: false,
    consumer_execution_allowed: false,
    card_render_allowed: false,
    dom_access_allowed: false,
    browser_execution_allowed: false,
    ui_consumer_mount_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  });

  function snapshotStrictJson(value) {
    try {
      return JSON.parse(canonical.strictCanonicalStringify(value));
    } catch (_error) {
      return null;
    }
  }

  function strictEqual(left, right) {
    try {
      return (
        canonical.strictCanonicalStringify(left) ===
        canonical.strictCanonicalStringify(right)
      );
    } catch (_error) {
      return false;
    }
  }

  function sameKeys(value, keys) {
    if (!canonical.isPlainRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = [...keys].sort();
    return (
      actual.length === expected.length &&
      actual.every((key, index) => key === expected[index])
    );
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function verifiedEnvelopeSnapshot(document) {
    const snapshot = snapshotStrictJson(document);
    if (!snapshot) return null;
    if (!canonical.verifySealedDocument(snapshot, "delivery_envelope_hash")) {
      return null;
    }
    if (
      !sameKeys(snapshot, [
        "schema_version",
        "static_fingerprint",
        "status",
        "delivery_state",
        "reason_code",
        "transport",
        "consumer_contract",
        "provenance",
        "payload_candidate",
        "facts",
        "authority",
        "delivery_envelope_hash",
      ]) ||
      snapshot.schema_version !== SCHEMA_VERSION ||
      snapshot.static_fingerprint !== STATIC_FINGERPRINT ||
      snapshot.status !== "BLOCKED" ||
      snapshot.delivery_state !==
        "IN_MEMORY_DOCUMENT_BUILT_ENDPOINT_UNBOUND" ||
      snapshot.reason_code !==
        "EXACT_BOUNDED_PAYLOAD_EMBEDDED_IN_MEMORY_WIRE_ENDPOINT_ROUTE_CONSUMER_RENDER_BROWSER_AND_MOUNT_ABSENT" ||
      !strictEqual(snapshot.transport, EXPECTED_TRANSPORT) ||
      !strictEqual(snapshot.facts, EXPECTED_FACTS) ||
      !strictEqual(snapshot.authority, EXPECTED_AUTHORITY)
    ) {
      return null;
    }
    if (
      !sameKeys(snapshot.consumer_contract, [
        "payload_schema_version",
        "payload_static_fingerprint",
        "javascript_adapter_global",
        "javascript_verify_function",
        "javascript_extract_function",
        "javascript_receipt_function",
      ]) ||
      snapshot.consumer_contract.payload_schema_version !==
        card.PAYLOAD_SCHEMA_VERSION ||
      snapshot.consumer_contract.payload_static_fingerprint !==
        card.PAYLOAD_STATIC_FINGERPRINT
    ) {
      return null;
    }
    if (
      !sameKeys(snapshot.provenance, [
        "load_descriptor_schema_version",
        "load_descriptor_binding_schema_version",
        "load_descriptor_static_fingerprint",
        "load_descriptor_implementation_sha256",
        "load_descriptor_binding_hash",
        "load_descriptor_hash",
        "style_binding_hash",
        "payload_candidate_hash",
        "source_envelope_hash",
      ]) ||
      snapshot.provenance.load_descriptor_implementation_sha256 !==
        LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256 ||
      snapshot.provenance.load_descriptor_hash !== LOAD_DESCRIPTOR_HASH ||
      !isSha256(snapshot.provenance.load_descriptor_binding_hash) ||
      !isSha256(snapshot.provenance.style_binding_hash) ||
      !isSha256(snapshot.provenance.payload_candidate_hash) ||
      !isSha256(snapshot.provenance.source_envelope_hash) ||
      !card.verifySourceBaselineProviderConformancePayloadCandidateV1(
        snapshot.payload_candidate
      ) ||
      snapshot.payload_candidate.payload_candidate_hash !==
        snapshot.provenance.payload_candidate_hash ||
      snapshot.payload_candidate.source_envelope_hash !==
        snapshot.provenance.source_envelope_hash
    ) {
      return null;
    }
    return snapshot;
  }

  function verifyInMemoryPayloadDeliveryEnvelopeV1(document) {
    return verifiedEnvelopeSnapshot(document) !== null;
  }

  function extractPayloadCandidateFromInMemoryEnvelopeV1(document) {
    const snapshot = verifiedEnvelopeSnapshot(document);
    if (!snapshot) {
      throw new TypeError("in-memory payload delivery envelope is invalid");
    }
    return snapshot.payload_candidate;
  }

  function buildInMemoryPayloadConsumptionReceiptCandidateV1(document) {
    const snapshot = verifiedEnvelopeSnapshot(document);
    if (!snapshot) {
      throw new TypeError("in-memory payload delivery envelope is invalid");
    }
    const receipt = {
      schema_version: RECEIPT_SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: "BLOCKED",
      consumption_state: "PAYLOAD_EXTRACTED_IN_MEMORY_DOM_RENDER_NOT_EXECUTED",
      delivery_envelope_hash: snapshot.delivery_envelope_hash,
      payload_candidate_hash: snapshot.provenance.payload_candidate_hash,
      facts: {
        envelope_exactly_verified: true,
        payload_extracted_in_memory: true,
        card_payload_exactly_verified: true,
        card_render_called: false,
        dom_accessed: false,
        browser_executed: false,
        ui_mounted: false,
        network_accessed: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      authority: {
        descriptive_only: true,
        card_render_allowed: false,
        dom_access_allowed: false,
        browser_execution_allowed: false,
        ui_consumer_mount_allowed: false,
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
      },
    };
    return canonical.sealDocument(receipt, "consumption_receipt_hash");
  }

  function verifyInMemoryPayloadConsumptionReceiptCandidateV1(
    envelope,
    receipt
  ) {
    const snapshot = snapshotStrictJson(receipt);
    if (!snapshot) return false;
    try {
      return strictEqual(
        snapshot,
        buildInMemoryPayloadConsumptionReceiptCandidateV1(envelope)
      );
    } catch (_error) {
      return false;
    }
  }

  return Object.freeze({
    LOAD_DESCRIPTOR_HASH,
    LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256,
    RECEIPT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    buildInMemoryPayloadConsumptionReceiptCandidateV1,
    extractPayloadCandidateFromInMemoryEnvelopeV1,
    verifyInMemoryPayloadConsumptionReceiptCandidateV1,
    verifyInMemoryPayloadDeliveryEnvelopeV1,
  });
});
