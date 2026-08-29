"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./strict_canonical_json_v1.js"));
  } else {
    root.HakimiPortfolioCorrelationAdmissionV2InMemoryDeliveryV1 = factory(
      root.HakimiStrictCanonicalJsonV1
    );
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  if (!strictCanonical) throw new Error("strict canonical dependency is required");

  var ENVELOPE_SCHEMA_VERSION = "portfolio-correlation-admission-v2-in-memory-delivery-envelope-v1";
  var PAYLOAD_SCHEMA_VERSION = "portfolio-correlation-admission-v2-presentation-payload-v1";
  var RECEIPT_SCHEMA_VERSION = "portfolio-correlation-admission-v2-payload-extraction-receipt-v1";
  var STATIC_FINGERPRINT = "20260823-portfolio-correlation-admission-v2-in-memory-delivery-v1-lock-1";
  var CHECK_KEYS = Object.freeze([
    "input_snapshot_exact",
    "input_identity_exact",
    "report_universe_contract_exact",
    "correlation_preregistration_exact",
    "common_universe_exact",
    "v1_admission_exact",
    "v1_admission_pass",
    "evidence_has_no_execution_authority",
  ]);
  var FLOW_CHECKS = Object.freeze([
    { key: "input_identity_exact", tier: "INPUT_IDENTITY", blocker: "strategy_variant_or_lane_identity_invalid" },
    { key: "report_universe_contract_exact", tier: "REPORT_UNIVERSE", blocker: "report_universe_contract_verification_failed" },
    { key: "correlation_preregistration_exact", tier: "CORRELATION_PREREGISTRATION", blocker: "correlation_preregistration_verification_failed" },
    { key: "common_universe_exact", tier: "COMMON_UNIVERSE", blocker: "report_and_correlation_universe_mismatch" },
    { key: "v1_admission_exact", tier: "V1_ADMISSION", blocker: "portfolio_correlation_admission_v1_verification_failed" },
    { key: "v1_admission_pass", tier: "V1_ADMISSION", blocker: "portfolio_correlation_admission_v1_blocked" },
  ]);
  var V1_TIERS = Object.freeze([
    "INPUT_SNAPSHOT", "INPUT_IDENTITY", "BASE_ADMISSION",
    "CORRELATION_PREREGISTRATION", "CORRELATION_MATRIX", "COMPLETE_LINK",
    "STRATA_PREREGISTRATION", "STRATA_GATE", "PERMISSION",
  ]);

  function exactKeys(value, keys) {
    return strictCanonical.isPlainRecord(value)
      && Object.keys(value).sort().join("\u0000") === keys.slice().sort().join("\u0000");
  }

  function exactArray(actual, expected) {
    return Array.isArray(actual)
      && actual.length === expected.length
      && actual.every(function (value, index) { return value === expected[index]; });
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function isHashOrEmpty(value) {
    return value === "" || isHash(value);
  }

  function isTriState(value) {
    return value === true || value === false || value === null;
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.keys(value).forEach(function (key) { deepFreeze(value[key]); });
    }
    return value;
  }

  function detached(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function sameDocument(left, right) {
    try {
      return strictCanonical.strictCanonicalStringify(left)
        === strictCanonical.strictCanonicalStringify(right);
    } catch (_error) {
      return false;
    }
  }

  function validPayloadFlow(payload) {
    var checks = payload.checks;
    var expectedBlockers = [];
    var expectedFirst = null;
    if (checks.input_snapshot_exact === false) {
      if (!FLOW_CHECKS.every(function (item) { return checks[item.key] === null; })
        || checks.evidence_has_no_execution_authority !== null) return false;
      expectedFirst = "INPUT_SNAPSHOT";
      expectedBlockers.push("evidence_snapshot_failed");
    } else if (checks.input_snapshot_exact === true) {
      var firstFalse = -1;
      for (var index = 0; index < FLOW_CHECKS.length; index += 1) {
        if (checks[FLOW_CHECKS[index].key] === false) {
          firstFalse = index;
          break;
        }
      }
      if (firstFalse === -1) {
        if (FLOW_CHECKS.some(function (item) { return checks[item.key] !== true; })) return false;
      } else {
        expectedFirst = FLOW_CHECKS[firstFalse].tier;
        expectedBlockers.push(FLOW_CHECKS[firstFalse].blocker);
        for (var later = firstFalse + 1; later < FLOW_CHECKS.length; later += 1) {
          if (checks[FLOW_CHECKS[later].key] !== null) return false;
        }
      }
      if (checks.evidence_has_no_execution_authority === false) {
        expectedBlockers.push("correlation_evidence_has_execution_authority");
        if (expectedFirst === null) expectedFirst = "PERMISSION";
      } else if (checks.evidence_has_no_execution_authority !== true) {
        return false;
      }
    } else {
      return false;
    }

    var passed = expectedFirst === null;
    if (payload.status !== (passed ? "PASS" : "BLOCK")
      || payload.first_blocking_tier !== expectedFirst
      || !exactArray(payload.blockers, expectedBlockers)) return false;

    var commonCheck = checks.common_universe_exact;
    var expectedCommon = commonCheck === null
      ? "NOT_EVALUATED" : (commonCheck ? "PASS" : "BLOCK");
    if (payload.common_universe_status !== expectedCommon) return false;

    var v1Exact = checks.v1_admission_exact;
    var expectedV1 = v1Exact === null
      ? "NOT_EVALUATED"
      : (v1Exact === false ? "INVALID" : (checks.v1_admission_pass ? "PASS" : "BLOCK"));
    if (payload.v1_admission_status !== expectedV1) return false;
    if (expectedV1 === "BLOCK") {
      if (V1_TIERS.indexOf(payload.v1_first_blocking_tier) === -1) return false;
    } else if (payload.v1_first_blocking_tier !== null) {
      return false;
    }
    if (commonCheck === null && payload.common_universe_binding_hash !== "") return false;
    if (commonCheck !== null && !isHash(payload.common_universe_binding_hash)) return false;
    return isHashOrEmpty(payload.source_report_hash);
  }

  function verifyPresentationPayload(payload) {
    if (!strictCanonical.verifySealedDocument(payload, "presentation_payload_hash")
      || !exactKeys(payload, [
        "blockers", "candidate_hash", "checks", "common_universe_binding_hash",
        "common_universe_status", "facts", "first_blocking_tier", "permissions",
        "presentation_payload_hash", "schema_version", "source_report_hash",
        "static_fingerprint", "status", "v1_admission_status", "v1_first_blocking_tier",
      ])) return false;
    if (payload.schema_version !== PAYLOAD_SCHEMA_VERSION
      || payload.static_fingerprint !== STATIC_FINGERPRINT
      || !isHash(payload.candidate_hash)
      || !exactKeys(payload.checks, CHECK_KEYS)
      || !CHECK_KEYS.every(function (key) { return isTriState(payload.checks[key]); })
      || !Array.isArray(payload.blockers)
      || !payload.blockers.every(function (value) { return typeof value === "string"; })
      || !exactKeys(payload.facts, [
        "consumer_only", "profitability_proven", "raw_source_documents_embedded",
        "raw_symbol_lists_embedded", "raw_v2_candidate_embedded",
      ])
      || payload.facts.consumer_only !== true
      || payload.facts.profitability_proven !== false
      || payload.facts.raw_source_documents_embedded !== false
      || payload.facts.raw_symbol_lists_embedded !== false
      || payload.facts.raw_v2_candidate_embedded !== false
      || !exactKeys(payload.permissions, [
        "current_admission_allowed", "live_order_allowed", "paper_authorized",
      ])
      || payload.permissions.current_admission_allowed !== false
      || payload.permissions.paper_authorized !== false
      || payload.permissions.live_order_allowed !== false) return false;
    return validPayloadFlow(payload);
  }

  function verifyEnvelope(envelope) {
    if (!strictCanonical.verifySealedDocument(envelope, "delivery_envelope_hash")
      || !exactKeys(envelope, [
        "authority", "consumer_contract", "delivery_envelope_hash", "delivery_state",
        "facts", "presentation_payload", "provenance", "reason_code",
        "schema_version", "static_fingerprint", "status", "transport",
      ])) return false;
    if (envelope.schema_version !== ENVELOPE_SCHEMA_VERSION
      || envelope.static_fingerprint !== STATIC_FINGERPRINT
      || envelope.status !== "BLOCKED"
      || envelope.delivery_state !== "EXACT_V2_PRESENTATION_PAYLOAD_ENVELOPED_IN_MEMORY_CONSUMER_UNBOUND"
      || envelope.reason_code !== "EXACT_BOUNDED_V2_PRESENTATION_PAYLOAD_EMBEDDED_IN_MEMORY_WIRE_ENDPOINT_ROUTE_PRESENTATION_RENDER_BROWSER_AND_MOUNT_ABSENT"
      || !verifyPresentationPayload(envelope.presentation_payload)) return false;

    var transport = envelope.transport;
    if (!exactKeys(transport, [
      "cache_policy", "encoding", "endpoint", "media_type", "mode",
      "network_transport_used", "persistent_storage_used", "route", "wire_bytes_built",
    ]) || transport.mode !== "IN_MEMORY_JSON_DOCUMENT"
      || transport.media_type !== "application/json" || transport.encoding !== "UTF-8"
      || transport.cache_policy !== "NO_STORE" || transport.endpoint !== null
      || transport.route !== null || transport.wire_bytes_built !== false
      || transport.network_transport_used !== false
      || transport.persistent_storage_used !== false) return false;

    var contract = envelope.consumer_contract;
    if (!exactKeys(contract, [
      "javascript_adapter_global", "javascript_extract_function",
      "javascript_receipt_function", "javascript_verify_function",
      "payload_schema_version", "presentation_consumer", "render_function",
    ]) || contract.payload_schema_version !== PAYLOAD_SCHEMA_VERSION
      || contract.javascript_adapter_global !== "HakimiPortfolioCorrelationAdmissionV2InMemoryDeliveryV1"
      || contract.javascript_verify_function !== "verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1"
      || contract.javascript_extract_function !== "extractPortfolioCorrelationAdmissionV2PresentationPayloadV1"
      || contract.javascript_receipt_function !== "buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1"
      || contract.presentation_consumer !== null || contract.render_function !== null) return false;

    var provenance = envelope.provenance;
    if (!exactKeys(provenance, [
      "candidate_hash", "candidate_status", "common_universe_binding_hash",
      "consumer_binding_hash", "consumer_preregistration_adr_sha256",
      "consumer_preregistration_hash", "consumer_preregistration_implementation_sha256",
      "consumer_preregistration_test_sha256", "source_report_hash",
    ]) || !isHash(provenance.consumer_preregistration_hash)
      || !isHash(provenance.consumer_preregistration_implementation_sha256)
      || !isHash(provenance.consumer_preregistration_test_sha256)
      || !isHash(provenance.consumer_preregistration_adr_sha256)
      || !isHash(provenance.consumer_binding_hash)
      || provenance.candidate_hash !== envelope.presentation_payload.candidate_hash
      || provenance.candidate_status !== envelope.presentation_payload.status
      || provenance.common_universe_binding_hash !== envelope.presentation_payload.common_universe_binding_hash
      || provenance.source_report_hash !== envelope.presentation_payload.source_report_hash) return false;

    var facts = envelope.facts;
    if (!exactKeys(facts, [
      "bounded_presentation_payload_embedded", "browser_executed",
      "consumer_binding_exactly_verified", "consumer_preregistration_exactly_verified",
      "current_activated", "delivery_attempted", "dom_accessed", "endpoint_present",
      "network_accessed", "payload_extracted", "persistent_storage_used",
      "presentation_consumer_executed", "profitability_proven", "raw_source_documents_embedded",
      "raw_symbol_lists_embedded", "raw_v2_candidate_embedded", "render_called",
      "route_registered", "runtime_mutations_performed", "ui_mounted", "wire_bytes_built",
    ]) || facts.consumer_preregistration_exactly_verified !== true
      || facts.consumer_binding_exactly_verified !== true
      || facts.bounded_presentation_payload_embedded !== true
      || Object.keys(facts).some(function (key) {
        return key !== "consumer_preregistration_exactly_verified"
          && key !== "consumer_binding_exactly_verified"
          && key !== "bounded_presentation_payload_embedded"
          && facts[key] !== false;
      })) return false;

    var authority = envelope.authority;
    if (!exactKeys(authority, [
      "browser_execution_allowed", "current_admission_allowed", "descriptive_only",
      "dom_access_allowed", "endpoint_registration_allowed", "live_order_allowed",
      "paper_authorized", "payload_extraction_runtime_allowed",
      "persistent_storage_allowed", "presentation_consumer_execution_allowed",
      "render_allowed", "route_registration_allowed", "ui_consumer_mount_allowed",
      "wire_transport_allowed",
    ]) || authority.descriptive_only !== true
      || Object.keys(authority).some(function (key) {
        return key !== "descriptive_only" && authority[key] !== false;
      })) return false;
    return true;
  }

  function extractPayload(envelope) {
    if (!verifyEnvelope(envelope)) return null;
    return deepFreeze(detached(envelope.presentation_payload));
  }

  function buildReceipt(envelope) {
    var exact = verifyEnvelope(envelope);
    var document = {
      schema_version: RECEIPT_SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: exact ? "BLOCKED" : "UNKNOWN",
      receipt_state: exact
        ? "EXACT_PRESENTATION_PAYLOAD_EXTRACTED_IN_MEMORY_RENDER_UNCALLED"
        : "UNKNOWN",
      reason_code: exact
        ? "EXACT_PAYLOAD_EXTRACTED_IN_MEMORY_PRESENTATION_RENDER_DOM_BROWSER_AND_MOUNT_ABSENT"
        : "DELIVERY_ENVELOPE_NOT_EXACT",
      delivery_envelope_hash: exact ? envelope.delivery_envelope_hash : null,
      presentation_payload_hash: exact
        ? envelope.presentation_payload.presentation_payload_hash : null,
      candidate_hash: exact ? envelope.presentation_payload.candidate_hash : null,
      facts: {
        delivery_envelope_exactly_verified: exact,
        payload_extracted_in_memory: exact,
        raw_payload_embedded: false,
        presentation_consumer_executed: false,
        render_called: false,
        dom_accessed: false,
        browser_executed: false,
        ui_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      authority: {
        descriptive_only: true,
        presentation_consumer_execution_allowed: false,
        render_allowed: false,
        dom_access_allowed: false,
        browser_execution_allowed: false,
        ui_consumer_mount_allowed: false,
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
      },
    };
    return strictCanonical.sealDocument(document, "payload_extraction_receipt_hash");
  }

  function verifyReceipt(receipt, envelope) {
    return strictCanonical.verifySealedDocument(receipt, "payload_extraction_receipt_hash")
      && sameDocument(receipt, buildReceipt(envelope));
  }

  return Object.freeze({
    ENVELOPE_SCHEMA_VERSION: ENVELOPE_SCHEMA_VERSION,
    PAYLOAD_SCHEMA_VERSION: PAYLOAD_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION: RECEIPT_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    verifyPortfolioCorrelationAdmissionV2PresentationPayloadV1: verifyPresentationPayload,
    verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1: verifyEnvelope,
    extractPortfolioCorrelationAdmissionV2PresentationPayloadV1: extractPayload,
    buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1: buildReceipt,
    verifyPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1: verifyReceipt,
  });
});
