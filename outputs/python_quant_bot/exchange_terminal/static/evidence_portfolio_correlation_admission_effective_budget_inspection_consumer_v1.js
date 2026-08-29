(function (root, factory) {
  const api = factory(
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1,
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js")
      : root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1,
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js")
      : root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1
  );
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1 =
      api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical,
  delivery,
  bridge
) {
  "use strict";

  if (
    !strictCanonical ||
    typeof strictCanonical.isPlainRecord !== "function" ||
    typeof strictCanonical.strictCanonicalHash !== "function" ||
    typeof strictCanonical.strictCanonicalStringify !== "function" ||
    typeof strictCanonical.verifySealedDocument !== "function"
  ) {
    throw new TypeError("strict canonical dependency is required");
  }
  if (
    !delivery ||
    typeof delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1 !==
      "function" ||
    typeof delivery.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1 !==
      "function" ||
    typeof delivery.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1 !==
      "function" ||
    typeof delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1 !==
      "function"
  ) {
    throw new TypeError("delivery adapter dependency is required");
  }
  if (
    !bridge ||
    typeof bridge.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1 !==
      "function" ||
    typeof bridge.renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1 !==
      "function"
  ) {
    throw new TypeError("inspection bridge dependency is required");
  }

  const SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-inspection-consumer-result-v1";
  const STATIC_FINGERPRINT =
    "20260824-portfolio-correlation-admission-effective-budget-inspection-consumer-v1-isolated-lock-1";
  const CONSUMER_ID =
    "portfolio-correlation-admission-effective-budget-inspection-bridge-v1";
  const BROWSER_GLOBAL =
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1";

  const PYTHON_RESULT_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-result-v1";
  const PYTHON_RESULT_STATIC_FINGERPRINT =
    "20260824-portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-v1-isolated-lock-1";
  const PYTHON_CONSUMER_ID =
    "portfolio-correlation-admission-effective-budget-hash-envelope-source-v1";
  const ADAPTER_REGISTRATION_HASH =
    "4c6eb60d842611d2babaf072527fe93d2a68f67bc6a7c2658b80fd1b9f07f4cb";
  const CONSUMER_PREREGISTRATION_HASH =
    "4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987";
  const PYTHON_CONSUMER_CONTRACT_HASH =
    "fd402270f5c03c5225201f9df8768859b398cc1912658a0880f367ff7afc882a";
  const JAVASCRIPT_CONSUMER_CONTRACT_HASH =
    "1966892253b987f98ae8e8814692ec6f94387d2f9191ca7416447802382bbb8f";

  const PYTHON_CONSUMER_IMPLEMENTATION_SHA256 =
    "ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca";
  const PYTHON_CONSUMER_TEST_SHA256 =
    "3ff87343beccd2f22d95be20e989886fbde6539a29d81a4730d56ab552addc92";
  const PYTHON_CONSUMER_ADR_SHA256 =
    "06f2385cd3a302c5311f6685afb917e81f184ccaec79fca228a19dad86a23558";
  const STRICT_CANONICAL_JAVASCRIPT_SHA256 =
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
  const DELIVERY_JAVASCRIPT_SHA256 =
    "867f7a7016472101a3606f2af22ae7b63509cc2afb3d2dbfe8f7058da8e08be0";
  const BRIDGE_JAVASCRIPT_SHA256 =
    "67f16fa7946aee1c552b85bbb9758c84149a5cf657b7af5f78dad5ed0f7149d7";

  const PYTHON_RESULT_KEYS = Object.freeze([
    "authority",
    "blockers",
    "consumer_id",
    "consumer_result_hash",
    "envelope",
    "envelope_hash",
    "facts",
    "gate",
    "reason_code",
    "required_contracts",
    "schema_version",
    "source_hashes",
    "static_fingerprint",
    "status",
    "transport",
  ]);
  const PYTHON_GATE_KEYS = Object.freeze([
    "adapter_registration_exact",
    "consumer_preregistration_exact",
    "python_consumer_contract_exact",
    "python_consumer_unbound",
  ]);
  const PYTHON_SOURCE_HASH_KEYS = Object.freeze([
    "admission_v2_hash",
    "binding_hash",
    "effective_budget_v3_hash",
    "presentation_payload_hash",
  ]);
  const PYTHON_AUTHORITY_KEYS = Object.freeze([
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "endpoint_registration_allowed",
    "host_import_allowed",
    "live_order_allowed",
    "network_allowed",
    "paper_authorized",
    "payload_provider_binding_allowed",
    "route_registration_allowed",
    "runtime_delivery_allowed",
    "storage_allowed",
    "writer_allowed",
  ]);
  const RESULT_AUTHORITY_KEYS = Object.freeze([
    "app_import_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "endpoint_registration_allowed",
    "html_script_binding_allowed",
    "live_order_allowed",
    "network_allowed",
    "paper_authorized",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "storage_allowed",
    "stylesheet_link_binding_allowed",
    "writer_allowed",
  ]);
  const FUNCTION_EXPORTS = Object.freeze([
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "CONSUMER_ID",
    "BROWSER_GLOBAL",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
  ]);

  function hasExactKeys(value, expectedKeys) {
    if (!strictCanonical.isPlainRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = Array.from(expectedKeys).sort();
    return (
      actual.length === expected.length &&
      actual.every((key, index) => key === expected[index])
    );
  }

  function valuesAreFalse(value, expectedKeys) {
    return (
      hasExactKeys(value, expectedKeys) &&
      expectedKeys.every((key) => value[key] === false)
    );
  }

  function valuesAreNull(value, expectedKeys) {
    return (
      hasExactKeys(value, expectedKeys) &&
      expectedKeys.every((key) => value[key] === null)
    );
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function deepFreeze(value, active) {
    if (
      value === null ||
      (typeof value !== "object" && typeof value !== "function")
    ) {
      return value;
    }
    const seen = active || new Set();
    if (seen.has(value)) return value;
    seen.add(value);
    for (const key of Object.keys(value)) deepFreeze(value[key], seen);
    seen.delete(value);
    return Object.freeze(value);
  }

  function requiredContracts() {
    return {
      adapter_registration_hash: ADAPTER_REGISTRATION_HASH,
      consumer_preregistration_hash: CONSUMER_PREREGISTRATION_HASH,
      python_consumer_contract_hash: PYTHON_CONSUMER_CONTRACT_HASH,
      javascript_consumer_contract_hash: JAVASCRIPT_CONSUMER_CONTRACT_HASH,
      python_result_schema_version: PYTHON_RESULT_SCHEMA_VERSION,
      python_result_static_fingerprint: PYTHON_RESULT_STATIC_FINGERPRINT,
      delivery_schema_version: delivery.ENVELOPE_SCHEMA_VERSION,
      delivery_static_fingerprint: delivery.STATIC_FINGERPRINT,
      bridge_schema_version: bridge.BRIDGE_SCHEMA_VERSION,
      bridge_static_fingerprint: bridge.BRIDGE_STATIC_FINGERPRINT,
      strict_canonical_javascript_sha256:
        STRICT_CANONICAL_JAVASCRIPT_SHA256,
      delivery_javascript_sha256: DELIVERY_JAVASCRIPT_SHA256,
      bridge_javascript_sha256: BRIDGE_JAVASCRIPT_SHA256,
      python_consumer_implementation_sha256:
        PYTHON_CONSUMER_IMPLEMENTATION_SHA256,
    };
  }

  function verifyRequiredPythonContracts(required) {
    return (
      hasExactKeys(required, [
        "adapter_registration_hash",
        "consumer_preregistration_hash",
        "delivery_payload_schema_version",
        "delivery_schema_version",
        "delivery_static_fingerprint",
        "python_consumer_contract_hash",
      ]) &&
      required.adapter_registration_hash === ADAPTER_REGISTRATION_HASH &&
      required.consumer_preregistration_hash ===
        CONSUMER_PREREGISTRATION_HASH &&
      required.python_consumer_contract_hash ===
        PYTHON_CONSUMER_CONTRACT_HASH &&
      required.delivery_schema_version === delivery.ENVELOPE_SCHEMA_VERSION &&
      required.delivery_static_fingerprint === delivery.STATIC_FINGERPRINT &&
      required.delivery_payload_schema_version ===
        delivery.PAYLOAD_SCHEMA_VERSION
    );
  }

  function verifyPythonTransport(transport) {
    return (
      hasExactKeys(transport, [
        "endpoint",
        "mode",
        "network_used",
        "payload_source_provider",
        "route",
        "storage_used",
      ]) &&
      transport.mode === "IN_MEMORY_RETURN_ONLY" &&
      transport.payload_source_provider === null &&
      transport.route === null &&
      transport.endpoint === null &&
      transport.storage_used === false &&
      transport.network_used === false
    );
  }

  function verifyPythonFacts(facts, gateExact, envelopeExpected) {
    return (
      hasExactKeys(facts, [
        "adapter_failed",
        "adapter_invoked",
        "browser_executed",
        "consumer_gate_exact",
        "dom_mounted",
        "envelope_verified",
        "input_documents_embedded",
        "profitability_proven",
        "runtime_mutations_performed",
      ]) &&
      facts.consumer_gate_exact === gateExact &&
      facts.envelope_verified === envelopeExpected &&
      facts.input_documents_embedded === false &&
      facts.browser_executed === false &&
      facts.dom_mounted === false &&
      facts.runtime_mutations_performed === false &&
      facts.profitability_proven === false
    );
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
    result
  ) {
    try {
      if (!hasExactKeys(result, PYTHON_RESULT_KEYS)) return false;
      if (
        !strictCanonical.verifySealedDocument(
          result,
          "consumer_result_hash"
        )
      ) {
        return false;
      }
      if (
        result.schema_version !== PYTHON_RESULT_SCHEMA_VERSION ||
        result.static_fingerprint !== PYTHON_RESULT_STATIC_FINGERPRINT ||
        result.consumer_id !== PYTHON_CONSUMER_ID ||
        !verifyRequiredPythonContracts(result.required_contracts) ||
        !hasExactKeys(result.gate, PYTHON_GATE_KEYS) ||
        !PYTHON_GATE_KEYS.every(
          (key) => typeof result.gate[key] === "boolean"
        ) ||
        !hasExactKeys(result.source_hashes, PYTHON_SOURCE_HASH_KEYS) ||
        !valuesAreFalse(result.authority, PYTHON_AUTHORITY_KEYS) ||
        !verifyPythonTransport(result.transport) ||
        !Array.isArray(result.blockers) ||
        !result.blockers.every((item) => typeof item === "string")
      ) {
        return false;
      }

      const gateExact = PYTHON_GATE_KEYS.every((key) => result.gate[key]);
      if (result.status === "BLOCKED") {
        if (
          result.envelope !== null ||
          result.envelope_hash !== null ||
          !valuesAreNull(result.source_hashes, PYTHON_SOURCE_HASH_KEYS) ||
          !verifyPythonFacts(result.facts, gateExact, false)
        ) {
          return false;
        }
        if (gateExact) {
          return (
            result.reason_code === "ADAPTER_ENVELOPE_VERIFICATION_FAILED" &&
            result.facts.adapter_invoked === true
          );
        }
        return (
          result.reason_code ===
            "CONSUMER_GATE_REJECTED_NO_ADAPTER_INVOCATION" &&
          result.facts.adapter_invoked === false &&
          result.facts.adapter_failed === false
        );
      }

      if (
        (result.status !== "KNOWN" && result.status !== "UNKNOWN") ||
        !gateExact ||
        !verifyPythonFacts(result.facts, true, true) ||
        result.facts.adapter_invoked !== true ||
        result.facts.adapter_failed !== false ||
        !strictCanonical.isPlainRecord(result.envelope) ||
        !delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
          result.envelope
        ) ||
        result.envelope_hash !== result.envelope.delivery_envelope_hash ||
        result.status !== result.envelope.status
      ) {
        return false;
      }

      const provenance = result.envelope.provenance;
      if (
        !strictCanonical.isPlainRecord(provenance) ||
        result.source_hashes.binding_hash !== provenance.binding_hash ||
        result.source_hashes.admission_v2_hash !== provenance.admission_v2_hash ||
        result.source_hashes.effective_budget_v3_hash !==
          provenance.effective_budget_v3_hash ||
        result.source_hashes.presentation_payload_hash !==
          provenance.presentation_payload_hash ||
        !PYTHON_SOURCE_HASH_KEYS.every((key) =>
          result.status === "KNOWN"
            ? isHash(result.source_hashes[key])
            : result.source_hashes[key] === null
        )
      ) {
        return false;
      }

      const payload =
        delivery.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
          result.envelope
        );
      if (result.status === "KNOWN") {
        return (
          result.reason_code ===
            "EXACT_CONSUMER_GATE_KNOWN_ENVELOPE_RETURNED" &&
          strictCanonical.isPlainRecord(payload)
        );
      }
      return (
        result.reason_code ===
          "EXACT_CONSUMER_GATE_UNKNOWN_ENVELOPE_RETURNED" &&
        payload === null
      );
    } catch (error) {
      return false;
    }
  }

  function commonBlockers() {
    return [
      "JAVASCRIPT_CONSUMER_HOST_UNBOUND",
      "HTML_STYLESHEET_AND_MOUNT_SLOT_UNBOUND",
      "BROWSER_EXECUTION_AND_DOM_MOUNT_UNAUTHORIZED",
      "CURRENT_ACTIVATION_NOT_AUTHORIZED",
      "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
    ];
  }

  function uniqueStrings(values) {
    return Array.from(new Set(values.filter((value) => typeof value === "string")));
  }

  function authorityLocks() {
    const locks = {};
    for (const key of RESULT_AUTHORITY_KEYS) locks[key] = false;
    return locks;
  }

  function sealResult(core) {
    return deepFreeze({
      ...core,
      javascript_consumer_result_hash:
        strictCanonical.strictCanonicalHash(core),
    });
  }

  function blockedResult(reasonCode, pythonResultVerified, pythonResult) {
    const validBlocked =
      pythonResultVerified &&
      strictCanonical.isPlainRecord(pythonResult) &&
      pythonResult.status === "BLOCKED";
    const core = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      consumer_id: CONSUMER_ID,
      status: "BLOCKED",
      reason_code: reasonCode,
      required_contracts: requiredContracts(),
      source_receipt: {
        python_consumer_result_hash: pythonResultVerified
          ? pythonResult.consumer_result_hash
          : null,
        envelope_hash: null,
        binding_hash: null,
        admission_v2_hash: null,
        effective_budget_v3_hash: null,
        presentation_payload_hash: null,
      },
      extraction_receipt: null,
      bridge_view_model: null,
      markup: null,
      presentation_hash: null,
      transport: {
        mode: "IN_MEMORY_ARGUMENT_AND_RETURN_ONLY",
        host_script: null,
        host_stylesheet: null,
        mount_slot: null,
        route: null,
        endpoint: null,
        network_used: false,
        storage_used: false,
      },
      facts: {
        python_consumer_result_verified: pythonResultVerified,
        python_result_blocked: validBlocked,
        javascript_adapter_invoked: false,
        extraction_receipt_verified: false,
        bridge_model_built: false,
        markup_built: false,
        browser_executed: false,
        dom_mounted: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      blockers: uniqueStrings(
        [
          validBlocked
            ? "PYTHON_CONSUMER_RESULT_BLOCKED"
            : "PYTHON_CONSUMER_RESULT_INVALID",
        ].concat(commonBlockers())
      ),
      authority: authorityLocks(),
    };
    return sealResult(core);
  }

  function buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
    pythonResult
  ) {
    const pythonResultVerified =
      verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
        pythonResult
      );
    if (!pythonResultVerified) {
      return blockedResult(
        "PYTHON_CONSUMER_RESULT_INVALID_NO_JAVASCRIPT_ADAPTER_INVOCATION",
        false,
        null
      );
    }
    if (pythonResult.status === "BLOCKED") {
      return blockedResult(
        "PYTHON_CONSUMER_RESULT_BLOCKED_NO_JAVASCRIPT_ADAPTER_INVOCATION",
        true,
        pythonResult
      );
    }

    try {
      const envelope = pythonResult.envelope;
      const extractionReceipt =
        delivery.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
          envelope
        );
      if (
        !delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
          extractionReceipt,
          envelope
        )
      ) {
        return blockedResult(
          "JAVASCRIPT_EXTRACTION_RECEIPT_INVALID",
          true,
          pythonResult
        );
      }
      const bridgeViewModel =
        bridge.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
          envelope
        );
      const markup =
        bridge.renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1(
          envelope
        );
      if (
        !strictCanonical.isPlainRecord(bridgeViewModel) ||
        bridgeViewModel.schema_version !== bridge.BRIDGE_SCHEMA_VERSION ||
        bridgeViewModel.static_fingerprint !== bridge.BRIDGE_STATIC_FINGERPRINT ||
        typeof markup !== "string" ||
        markup.length === 0 ||
        /\bREADY\b/i.test(markup)
      ) {
        return blockedResult(
          "JAVASCRIPT_BRIDGE_OUTPUT_INVALID",
          true,
          pythonResult
        );
      }

      const presentation = {
        bridge_view_model: bridgeViewModel,
        markup,
      };
      const core = {
        schema_version: SCHEMA_VERSION,
        static_fingerprint: STATIC_FINGERPRINT,
        consumer_id: CONSUMER_ID,
        status: pythonResult.status,
        reason_code:
          pythonResult.status === "KNOWN"
            ? "EXACT_PYTHON_CONSUMER_RESULT_VERIFIED_AND_BRIDGE_BUILT"
            : "EXACT_PYTHON_UNKNOWN_RESULT_VERIFIED_AND_NEUTRAL_BRIDGE_BUILT",
        required_contracts: requiredContracts(),
        source_receipt: {
          python_consumer_result_hash: pythonResult.consumer_result_hash,
          envelope_hash: pythonResult.envelope_hash,
          binding_hash: pythonResult.source_hashes.binding_hash,
          admission_v2_hash: pythonResult.source_hashes.admission_v2_hash,
          effective_budget_v3_hash:
            pythonResult.source_hashes.effective_budget_v3_hash,
          presentation_payload_hash:
            pythonResult.source_hashes.presentation_payload_hash,
        },
        extraction_receipt: extractionReceipt,
        bridge_view_model: bridgeViewModel,
        markup,
        presentation_hash: strictCanonical.strictCanonicalHash(presentation),
        transport: {
          mode: "IN_MEMORY_ARGUMENT_AND_RETURN_ONLY",
          host_script: null,
          host_stylesheet: null,
          mount_slot: null,
          route: null,
          endpoint: null,
          network_used: false,
          storage_used: false,
        },
        facts: {
          python_consumer_result_verified: true,
          python_result_blocked: false,
          javascript_adapter_invoked: true,
          extraction_receipt_verified: true,
          bridge_model_built: true,
          markup_built: true,
          browser_executed: false,
          dom_mounted: false,
          runtime_mutations_performed: false,
          profitability_proven: false,
        },
        blockers: uniqueStrings(
          pythonResult.blockers.concat(commonBlockers())
        ),
        authority: authorityLocks(),
      };
      return sealResult(core);
    } catch (error) {
      return blockedResult(
        "JAVASCRIPT_CONSUMER_PROCESSING_FAILED",
        true,
        pythonResult
      );
    }
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
    document,
    pythonResult
  ) {
    try {
      if (
        !strictCanonical.isPlainRecord(document) ||
        !strictCanonical.verifySealedDocument(
          document,
          "javascript_consumer_result_hash"
        ) ||
        document.schema_version !== SCHEMA_VERSION ||
        document.static_fingerprint !== STATIC_FINGERPRINT ||
        document.consumer_id !== CONSUMER_ID ||
        !valuesAreFalse(document.authority, RESULT_AUTHORITY_KEYS)
      ) {
        return false;
      }
      const expected =
        buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
          pythonResult
        );
      return (
        strictCanonical.strictCanonicalStringify(document) ===
          strictCanonical.strictCanonicalStringify(expected) &&
        strictCanonical.strictCanonicalHash(document) ===
          strictCanonical.strictCanonicalHash(expected)
      );
    } catch (error) {
      return false;
    }
  }

  return deepFreeze({
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    CONSUMER_ID,
    BROWSER_GLOBAL,
    PYTHON_RESULT_SCHEMA_VERSION,
    PYTHON_RESULT_STATIC_FINGERPRINT,
    ADAPTER_REGISTRATION_HASH,
    CONSUMER_PREREGISTRATION_HASH,
    PYTHON_CONSUMER_CONTRACT_HASH,
    JAVASCRIPT_CONSUMER_CONTRACT_HASH,
    PYTHON_CONSUMER_IMPLEMENTATION_SHA256,
    PYTHON_CONSUMER_TEST_SHA256,
    PYTHON_CONSUMER_ADR_SHA256,
    STRICT_CANONICAL_JAVASCRIPT_SHA256,
    DELIVERY_JAVASCRIPT_SHA256,
    BRIDGE_JAVASCRIPT_SHA256,
    FUNCTION_EXPORTS,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1,
    buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1,
  });
});
