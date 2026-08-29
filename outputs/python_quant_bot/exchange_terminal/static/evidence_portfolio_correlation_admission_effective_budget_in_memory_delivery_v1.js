(function (root, factory) {
  "use strict";

  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./strict_canonical_json_v1.js"));
    return;
  }
  root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1 =
    factory(root.HakimiStrictCanonicalJsonV1);
})(typeof globalThis === "object" ? globalThis : this, function (strict) {
  "use strict";

  if (
    !strict ||
    typeof strict.isPlainRecord !== "function" ||
    typeof strict.sealDocument !== "function" ||
    typeof strict.strictCanonicalStringify !== "function" ||
    typeof strict.verifySealedDocument !== "function"
  ) {
    throw new Error("strict canonical JSON v1 dependency is required");
  }

  var ENVELOPE_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-in-memory-delivery-envelope-v1";
  var PAYLOAD_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-presentation-payload-v1";
  var RECEIPT_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-payload-extraction-receipt-v1";
  var BINDING_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-binding-v1";
  var BINDING_STATIC_FINGERPRINT =
    "20260823-portfolio-correlation-admission-effective-budget-binding-v1-lock-1";
  var STATIC_FINGERPRINT =
    "20260823-portfolio-correlation-admission-effective-budget-in-memory-delivery-v1-lock-1";
  var JAVASCRIPT_GLOBAL =
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1";

  var TIER_ORDER = Object.freeze([
    "INPUT_SNAPSHOT",
    "ADMISSION_V2_EXACT",
    "EFFECTIVE_BUDGET_V3_EXACT",
    "CROSS_SOURCE_BINDING",
    "ADMISSION_V2_DECISION",
    "EFFECTIVE_BUDGET_V3_DECISION",
    "PERMISSION",
  ]);
  var FUNCTION_EXPORTS = Object.freeze([
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1",
    "extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
  ]);
  var SOURCE_FIELDS = Object.freeze([
    "binding_hash",
    "report_universe_contract_hash",
    "correlation_preregistration_hash",
    "correlation_matrix_hash",
    "complete_link_audit_hash",
    "complete_link_gate_hash",
    "strata_registration_hash",
    "strata_gate_hash",
    "admission_v2_hash",
    "effective_budget_v3_hash",
    "strategy_identity_hash",
    "proposal_scope_hash",
  ]);
  var CHECK_FIELDS = Object.freeze([
    "input_snapshot_exact",
    "admission_v2_exact",
    "effective_budget_v3_exact",
    "report_universe_hash_bound",
    "correlation_preregistration_hash_bound",
    "shared_correlation_matrix_snapshot",
    "complete_link_audit_hash_bound",
    "complete_link_gate_hash_bound",
    "strata_hash_chain_bound",
    "strategy_identity_bound",
    "cross_source_hashes_exact",
    "admission_v2_decision_pass",
    "effective_budget_v3_decision_pass",
    "evidence_has_no_execution_authority",
  ]);

  function exactKeys(value, expected) {
    if (!strict.isPlainRecord(value)) {
      return false;
    }
    var actual = Object.keys(value).sort();
    var cleanExpected = expected.slice().sort();
    return (
      actual.length === cleanExpected.length &&
      actual.every(function (key, index) {
        return key === cleanExpected[index];
      })
    );
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactFalseRecord(value, keys) {
    return (
      exactKeys(value, keys) &&
      keys.every(function (key) {
        return value[key] === false;
      })
    );
  }

  function safeGovernanceToken(value) {
    return (
      typeof value === "string" &&
      value.length > 0 &&
      value.length <= 160 &&
      value.toUpperCase().indexOf("READY") === -1 &&
      /^[A-Z0-9_:,-]+$/.test(value)
    );
  }

  function safeBlockerToken(value) {
    return (
      typeof value === "string" &&
      value.length > 0 &&
      value.length <= 240 &&
      value.toUpperCase().indexOf("READY") === -1 &&
      /^[A-Za-z0-9_:,-]+$/.test(value)
    );
  }

  function deepClone(value) {
    if (Array.isArray(value)) {
      return value.map(deepClone);
    }
    if (strict.isPlainRecord(value)) {
      var result = {};
      Object.keys(value).forEach(function (key) {
        result[key] = deepClone(value[key]);
      });
      return result;
    }
    return value;
  }

  function deepFreeze(value) {
    if (Array.isArray(value)) {
      value.forEach(deepFreeze);
      return Object.freeze(value);
    }
    if (strict.isPlainRecord(value)) {
      Object.keys(value).forEach(function (key) {
        deepFreeze(value[key]);
      });
      return Object.freeze(value);
    }
    return value;
  }

  function verifySource(source) {
    return (
      exactKeys(source, SOURCE_FIELDS) &&
      SOURCE_FIELDS.every(function (field) {
        return isHash(source[field]);
      })
    );
  }

  function verifyChecks(checks, bindingStatus) {
    if (
      !exactKeys(checks, CHECK_FIELDS) ||
      !CHECK_FIELDS.every(function (field) {
        return typeof checks[field] === "boolean";
      })
    ) {
      return false;
    }
    var structuralFields = CHECK_FIELDS.filter(function (field) {
      return (
        field !== "admission_v2_decision_pass" &&
        field !== "effective_budget_v3_decision_pass"
      );
    });
    if (
      !structuralFields.every(function (field) {
        return checks[field] === true;
      })
    ) {
      return false;
    }
    return (
      (bindingStatus === "PASS" &&
        checks.admission_v2_decision_pass === true &&
        checks.effective_budget_v3_decision_pass === true) ||
      (bindingStatus === "BLOCK" &&
        (!checks.admission_v2_decision_pass ||
          !checks.effective_budget_v3_decision_pass))
    );
  }

  function verifyTiers(tiers, payload) {
    if (!Array.isArray(tiers) || tiers.length !== TIER_ORDER.length) {
      return false;
    }
    for (var index = 0; index < tiers.length; index += 1) {
      var row = tiers[index];
      if (
        !exactKeys(row, ["tier", "state", "detail"]) ||
        row.tier !== TIER_ORDER[index] ||
        !safeGovernanceToken(row.state) ||
        !safeGovernanceToken(row.detail)
      ) {
        return false;
      }
    }
    if (
      tiers[4].state !== payload.admission_v2_status ||
      tiers[5].state !== payload.effective_budget_v3_status ||
      tiers[6].state !== "PASS" ||
      tiers[6].detail !== "LOCKED"
    ) {
      return false;
    }
    var firstNonPass = null;
    for (var tierIndex = 0; tierIndex < tiers.length - 1; tierIndex += 1) {
      if (tiers[tierIndex].state !== "PASS") {
        firstNonPass = tiers[tierIndex].tier;
        break;
      }
    }
    return firstNonPass === payload.first_blocking_tier;
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
    payload
  ) {
    try {
      if (
        !exactKeys(payload, [
          "schema_version",
          "static_fingerprint",
          "status",
          "binding_status",
          "first_blocking_tier",
          "admission_v2_status",
          "effective_budget_v3_status",
          "source",
          "checks",
          "tiers",
          "blockers",
          "facts",
          "permissions",
          "presentation_payload_hash",
        ]) ||
        !strict.verifySealedDocument(payload, "presentation_payload_hash") ||
        payload.schema_version !== PAYLOAD_SCHEMA_VERSION ||
        payload.static_fingerprint !== STATIC_FINGERPRINT ||
        payload.status !== "KNOWN" ||
        !["PASS", "BLOCK"].includes(payload.binding_status) ||
        !["PASS", "BLOCK"].includes(payload.admission_v2_status) ||
        !["PASS", "BLOCK"].includes(payload.effective_budget_v3_status) ||
        !verifySource(payload.source) ||
        !verifyChecks(payload.checks, payload.binding_status) ||
        !verifyTiers(payload.tiers, payload) ||
        !Array.isArray(payload.blockers) ||
        !payload.blockers.every(safeBlockerToken)
      ) {
        return false;
      }
      if (
        payload.binding_status === "PASS" &&
        (payload.first_blocking_tier !== null ||
          payload.blockers.length !== 0 ||
          payload.admission_v2_status !== "PASS" ||
          payload.effective_budget_v3_status !== "PASS")
      ) {
        return false;
      }
      if (
        payload.binding_status === "BLOCK" &&
        (TIER_ORDER.indexOf(payload.first_blocking_tier) < 0 ||
          payload.blockers.length === 0)
      ) {
        return false;
      }
      if (
        !exactKeys(payload.facts, [
          "binding_exactly_verified",
          "hash_only_projection",
          "source_documents_embedded",
          "positions_embedded",
          "strategy_identity_embedded",
          "raw_symbol_lists_embedded",
          "profitability_proven",
        ]) ||
        payload.facts.binding_exactly_verified !== true ||
        payload.facts.hash_only_projection !== true ||
        payload.facts.source_documents_embedded !== false ||
        payload.facts.positions_embedded !== false ||
        payload.facts.strategy_identity_embedded !== false ||
        payload.facts.raw_symbol_lists_embedded !== false ||
        payload.facts.profitability_proven !== false ||
        !exactFalseRecord(payload.permissions, [
          "current_admission_allowed",
          "paper_authorized",
          "live_order_allowed",
          "render_allowed",
          "dom_access_allowed",
          "browser_execution_allowed",
        ])
      ) {
        return false;
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  function verifyTransport(transport) {
    return (
      exactKeys(transport, [
        "mode",
        "network_used",
        "storage_used",
        "persisted",
        "endpoint",
        "route",
      ]) &&
      transport.mode === "IN_MEMORY_JSON_DOCUMENT" &&
      transport.network_used === false &&
      transport.storage_used === false &&
      transport.persisted === false &&
      transport.endpoint === null &&
      transport.route === null
    );
  }

  function verifyConsumerContract(contract) {
    return (
      exactKeys(contract, [
        "javascript_global",
        "module_format",
        "function_exports",
        "payload_schema_version",
        "envelope_schema_version",
        "receipt_schema_version",
        "tier_order",
        "host_script",
        "host_stylesheet",
        "host_slot",
        "payload_source_provider",
      ]) &&
      contract.javascript_global === JAVASCRIPT_GLOBAL &&
      contract.module_format === "UMD_COMMONJS" &&
      strict.strictCanonicalStringify(contract.function_exports) ===
        strict.strictCanonicalStringify(FUNCTION_EXPORTS) &&
      contract.payload_schema_version === PAYLOAD_SCHEMA_VERSION &&
      contract.envelope_schema_version === ENVELOPE_SCHEMA_VERSION &&
      contract.receipt_schema_version === RECEIPT_SCHEMA_VERSION &&
      strict.strictCanonicalStringify(contract.tier_order) ===
        strict.strictCanonicalStringify(TIER_ORDER) &&
      contract.host_script === null &&
      contract.host_stylesheet === null &&
      contract.host_slot === null &&
      contract.payload_source_provider === null
    );
  }

  function verifyAuthority(authority) {
    return (
      exactKeys(authority, [
        "descriptive_only",
        "runtime_delivery_allowed",
        "browser_execution_allowed",
        "dom_access_allowed",
        "render_allowed",
        "ui_mount_allowed",
        "route_registration_allowed",
        "endpoint_registration_allowed",
        "writer_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
      ]) &&
      authority.descriptive_only === true &&
      Object.keys(authority).every(function (key) {
        return key === "descriptive_only" || authority[key] === false;
      })
    );
  }

  function verifyFacts(facts, known) {
    return (
      exactKeys(facts, [
        "binding_exactly_verified",
        "payload_projected",
        "runtime_mutations_performed",
        "source_documents_embedded",
        "browser_executed",
        "dom_accessed",
        "profitability_proven",
      ]) &&
      facts.binding_exactly_verified === known &&
      facts.payload_projected === known &&
      facts.runtime_mutations_performed === false &&
      facts.source_documents_embedded === false &&
      facts.browser_executed === false &&
      facts.dom_accessed === false &&
      facts.profitability_proven === false
    );
  }

  function verifyProvenance(provenance, payload, known) {
    if (
      !exactKeys(provenance, [
        "binding_schema_version",
        "binding_static_fingerprint",
        "binding_hash",
        "admission_v2_hash",
        "effective_budget_v3_hash",
        "presentation_payload_hash",
      ]) ||
      provenance.binding_schema_version !== BINDING_SCHEMA_VERSION ||
      provenance.binding_static_fingerprint !== BINDING_STATIC_FINGERPRINT
    ) {
      return false;
    }
    if (!known) {
      return [
        "binding_hash",
        "admission_v2_hash",
        "effective_budget_v3_hash",
        "presentation_payload_hash",
      ].every(function (field) {
        return provenance[field] === null;
      });
    }
    return (
      isHash(provenance.binding_hash) &&
      isHash(provenance.admission_v2_hash) &&
      isHash(provenance.effective_budget_v3_hash) &&
      isHash(provenance.presentation_payload_hash) &&
      provenance.binding_hash === payload.source.binding_hash &&
      provenance.admission_v2_hash === payload.source.admission_v2_hash &&
      provenance.effective_budget_v3_hash ===
        payload.source.effective_budget_v3_hash &&
      provenance.presentation_payload_hash ===
        payload.presentation_payload_hash
    );
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
    envelope
  ) {
    try {
      if (
        !exactKeys(envelope, [
          "schema_version",
          "static_fingerprint",
          "status",
          "delivery_state",
          "reason_code",
          "transport",
          "consumer_contract",
          "provenance",
          "presentation_payload",
          "facts",
          "authority",
          "delivery_envelope_hash",
        ]) ||
        !strict.verifySealedDocument(envelope, "delivery_envelope_hash") ||
        envelope.schema_version !== ENVELOPE_SCHEMA_VERSION ||
        envelope.static_fingerprint !== STATIC_FINGERPRINT ||
        !verifyTransport(envelope.transport) ||
        !verifyConsumerContract(envelope.consumer_contract) ||
        !verifyAuthority(envelope.authority)
      ) {
        return false;
      }
      if (envelope.status === "UNKNOWN") {
        return (
          envelope.delivery_state === "UNKNOWN" &&
          ["BINDING_UNKNOWN", "BINDING_SOURCE_UNKNOWN", "DELIVERY_BUILD_FAILED"].includes(
            envelope.reason_code
          ) &&
          envelope.presentation_payload === null &&
          verifyProvenance(envelope.provenance, null, false) &&
          verifyFacts(envelope.facts, false)
        );
      }
      if (
        envelope.status !== "KNOWN" ||
        envelope.delivery_state !== "EXACT_IN_MEMORY" ||
        envelope.reason_code !== "EXACT_BINDING_PROJECTED" ||
        !verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
          envelope.presentation_payload
        ) ||
        !verifyProvenance(
          envelope.provenance,
          envelope.presentation_payload,
          true
        ) ||
        !verifyFacts(envelope.facts, true)
      ) {
        return false;
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  function extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
    envelope
  ) {
    if (
      !verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
        envelope
      ) ||
      envelope.status !== "KNOWN"
    ) {
      return null;
    }
    return deepFreeze(deepClone(envelope.presentation_payload));
  }

  function receiptAuthority() {
    return {
      descriptive_only: true,
      render_allowed: false,
      dom_access_allowed: false,
      browser_execution_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    };
  }

  function buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
    envelope
  ) {
    var exact =
      verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
        envelope
      );
    var payload = exact && envelope.status === "KNOWN"
      ? envelope.presentation_payload
      : null;
    var receipt = {
      schema_version: RECEIPT_SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: payload ? "PASS" : "BLOCK",
      reason_code: payload
        ? "EXACT_PAYLOAD_EXTRACTED"
        : exact
          ? "ENVELOPE_UNKNOWN"
          : "ENVELOPE_INVALID",
      source: {
        delivery_envelope_hash: exact
          ? envelope.delivery_envelope_hash
          : null,
        presentation_payload_hash: payload
          ? payload.presentation_payload_hash
          : null,
      },
      facts: {
        envelope_exact: exact,
        payload_extracted: Boolean(payload),
        payload_mutated: false,
        rendered: false,
        dom_accessed: false,
      },
      authority: receiptAuthority(),
    };
    return deepFreeze(strict.sealDocument(receipt, "receipt_hash"));
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
    receipt,
    envelope
  ) {
    try {
      var expected =
        buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
          envelope
        );
      return (
        strict.verifySealedDocument(receipt, "receipt_hash") &&
        strict.strictCanonicalStringify(receipt) ===
          strict.strictCanonicalStringify(expected)
      );
    } catch (_error) {
      return false;
    }
  }

  return Object.freeze({
    ENVELOPE_SCHEMA_VERSION: ENVELOPE_SCHEMA_VERSION,
    PAYLOAD_SCHEMA_VERSION: PAYLOAD_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION: RECEIPT_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    TIER_ORDER: TIER_ORDER,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1:
      verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1:
      verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1,
    extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1:
      extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1,
    buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1:
      buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1:
      verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1,
  });
});
