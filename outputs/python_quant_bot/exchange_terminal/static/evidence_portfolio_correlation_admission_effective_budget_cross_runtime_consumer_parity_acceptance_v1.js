(function (root, factory) {
  const api = factory(
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1,
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.js")
      : root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1
  );
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1 =
      api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical,
  inspectionConsumer
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
    !inspectionConsumer ||
    typeof inspectionConsumer.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1 !==
      "function" ||
    typeof inspectionConsumer.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1 !==
      "function" ||
    typeof inspectionConsumer.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1 !==
      "function"
  ) {
    throw new TypeError("inspection consumer dependency is required");
  }

  const REGISTRATION_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-registration-v1";
  const REGISTRATION_STATIC_FINGERPRINT =
    "20260824-portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-registration-v1-unbound-lock-1";
  const REGISTRATION_ID =
    "portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-v1";
  const SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-acceptance-receipt-v1";
  const STATIC_FINGERPRINT =
    "20260824-portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-acceptance-v1-unbound-lock-1";
  const BROWSER_GLOBAL =
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1";
  const CONSUMER_PREREGISTRATION_HASH =
    "4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987";
  const PYTHON_CONSUMER_CONTRACT_HASH =
    "fd402270f5c03c5225201f9df8768859b398cc1912658a0880f367ff7afc882a";
  const JAVASCRIPT_CONSUMER_CONTRACT_HASH =
    "1966892253b987f98ae8e8814692ec6f94387d2f9191ca7416447802382bbb8f";
  const INPUT_FIXTURE_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-cross-runtime-consumer-fixture-v1";
  const INPUT_FIXTURE_CANONICAL_HASH =
    "3cc4e1a759ef01fe4b8e5441250e307ee0fad9d0b6023608987c50e97da9ea0b";
  const STATUS_MAPPING_HASH =
    "f0332296b3370e75810d172cbc261b13327e25f8b77f0d7f9c83d80df7bd3014";
  const STATE_ORDER = Object.freeze(["KNOWN", "UNKNOWN", "BLOCKED"]);
  const FUNCTION_EXPORTS = Object.freeze([
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_STATIC_FINGERPRINT",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "BROWSER_GLOBAL",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1",
  ]);

  const PYTHON_CONSUMER = Object.freeze({
    consumer_id:
      "portfolio-correlation-admission-effective-budget-hash-envelope-source-v1",
    runtime: "PYTHON",
    role: "HASH_ONLY_IN_MEMORY_ENVELOPE_SOURCE",
    schema_version:
      "portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-result-v1",
    static_fingerprint:
      "20260824-portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-v1-isolated-lock-1",
    implementation_path:
      "exchange_terminal/services/portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.py",
    implementation_sha256:
      "ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca",
    test_path:
      "tests/test_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.py",
    test_sha256:
      "3ff87343beccd2f22d95be20e989886fbde6539a29d81a4730d56ab552addc92",
    adr_path:
      "docs/adr/0311-portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-v1.md",
    adr_sha256:
      "06f2385cd3a302c5311f6685afb917e81f184ccaec79fca228a19dad86a23558",
    host_binding: null,
  });
  const JAVASCRIPT_CONSUMER = Object.freeze({
    consumer_id:
      "portfolio-correlation-admission-effective-budget-inspection-bridge-v1",
    runtime: "JAVASCRIPT",
    role: "VERIFY_EXTRACT_AND_BUILD_UNMOUNTED_INSPECTION_BRIDGE",
    schema_version:
      "portfolio-correlation-admission-effective-budget-inspection-consumer-result-v1",
    static_fingerprint:
      "20260824-portfolio-correlation-admission-effective-budget-inspection-consumer-v1-isolated-lock-1",
    browser_global:
      "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
    implementation_path:
      "exchange_terminal/static/evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.js",
    implementation_sha256:
      "7ea19bbcf27a40657623f2f1a5b503e3b834939d4e08519a4455d95b3255b5e6",
    test_path:
      "exchange_terminal/static/evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.test.js",
    test_sha256:
      "2fa4f1b2f9abc044e483ca66f3fd3decce10287d18646353b9b7e72b28df680f",
    fixture_path:
      "tests/fixtures/portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.json",
    fixture_sha256:
      "b25be196152f370101bc43cf61e065308761d3070c4edb4656ffd00ad287dbe7",
    fixture_canonical_hash: INPUT_FIXTURE_CANONICAL_HASH,
    adr_path:
      "docs/adr/0312-portfolio-correlation-admission-effective-budget-inspection-consumer-v1.md",
    adr_sha256:
      "e4ab75bf5ac2579843668ec97bfa9cf22ea01e8b63e36f1fb577ce5f6763a718",
    host_script: null,
    host_stylesheet: null,
    mount_slot: null,
  });

  const PARITY_MATRIX = Object.freeze([
    Object.freeze({
      state: "KNOWN",
      python_status: "KNOWN",
      javascript_status: "KNOWN",
      python_result_hash:
        "4271f49558382127bb0e1e737ca080686c305907e60e0b5514aded14a98e7b96",
      python_envelope_hash:
        "2bafa66dbb13a0bfe4e927edd91129003177fed0b2f4bc2e788d793b597803c3",
      javascript_result_hash:
        "5e88bb5f5ce875ef2a8b22315487e26a7069a3a16da936461c5f2602b7a23390",
      extraction_receipt_hash:
        "b2991d361f45421a59ceb6980692ecb892bfc60bc41c2691c7f2ac980d6804b3",
      presentation_hash:
        "55e67227c3ad29378d06b5bb8f29db5b3b20981a988f69cadf074298b49c4e5d",
      markup_hash:
        "b7f8be93a4cc11bfdd97436f748ab5c673f086b4c4ae980f55e5effbff84a734",
      bridge_status_label: "LOCAL ALIGNMENT",
      source_hash_policy: "EXACT_64_HEX",
    }),
    Object.freeze({
      state: "UNKNOWN",
      python_status: "UNKNOWN",
      javascript_status: "UNKNOWN",
      python_result_hash:
        "6c67f3e287102d467c5a22f3ff57a2130a40654c7ee994cc560bba4673b04273",
      python_envelope_hash:
        "a5136b988cf6baed8f1009b786828c855c493935e5ff9af570e110834972993c",
      javascript_result_hash:
        "4c438a0de624b03c54d4dbb78a10c9ec3b93ca7deadcbea875d28c00e4d87e15",
      extraction_receipt_hash:
        "14aacd9131f3d8c9131ba4e116d0eb52be26a0e110624b5b89df5e1be8c1e778",
      presentation_hash:
        "9efdb0d85e5176a92ae4acb35686573b7cb769553d031015ed403817c349c2c5",
      markup_hash:
        "57441de8a2b73e502c68ac51bcd923cf65699f7b66a970ba2512321aab74cdac",
      bridge_status_label: "SOURCE UNKNOWN",
      source_hash_policy: "ALL_NULL",
    }),
    Object.freeze({
      state: "BLOCKED",
      python_status: "BLOCKED",
      javascript_status: "BLOCKED",
      python_result_hash:
        "a762ed471125031bf15ed39290b8a6e778454dfa68f07500a473d60f0b8fe9f3",
      python_envelope_hash: null,
      javascript_result_hash:
        "cb4d03284f25cd05a58563d63ef2a6cf51ce9ebe541ba6fb9d5f795f21e9fabc",
      extraction_receipt_hash: null,
      presentation_hash: null,
      markup_hash: null,
      bridge_status_label: null,
      source_hash_policy: "ALL_NULL",
    }),
  ]);

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

  function hasExactKeys(value, expectedKeys) {
    if (!strictCanonical.isPlainRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = Array.from(expectedKeys).sort();
    return (
      actual.length === expected.length &&
      actual.every((key, index) => key === expected[index])
    );
  }

  function expectedRegistration() {
    const consumers = [
      structuredClone(PYTHON_CONSUMER),
      structuredClone(JAVASCRIPT_CONSUMER),
    ];
    const matrix = structuredClone(PARITY_MATRIX);
    const core = {
      schema_version: REGISTRATION_SCHEMA_VERSION,
      static_fingerprint: REGISTRATION_STATIC_FINGERPRINT,
      registration_id: REGISTRATION_ID,
      status: "BLOCKED",
      registration_state:
        "THREE_STATE_CROSS_RUNTIME_CONSUMER_PARITY_REGISTERED_UNBOUND",
      consumer_preregistration: {
        registration_hash: CONSUMER_PREREGISTRATION_HASH,
        python_consumer_contract_hash: PYTHON_CONSUMER_CONTRACT_HASH,
        javascript_consumer_contract_hash: JAVASCRIPT_CONSUMER_CONTRACT_HASH,
        host_binding_required: false,
      },
      consumer_contracts: consumers,
      consumer_pair_hash: strictCanonical.strictCanonicalHash(consumers),
      parity_policy: {
        state_order: Array.from(STATE_ORDER),
        python_to_javascript_mapping: {
          KNOWN: "KNOWN",
          UNKNOWN: "UNKNOWN",
          BLOCKED: "BLOCKED",
        },
        status_mapping_hash: STATUS_MAPPING_HASH,
        known_source_hash_policy: "EXACT_64_HEX",
        unknown_source_hash_policy: "ALL_NULL",
        blocked_source_hash_policy: "ALL_NULL",
        known_unknown_markup_must_differ: true,
        known_bridge_status_label: "LOCAL ALIGNMENT",
        unknown_bridge_status_label: "SOURCE UNKNOWN",
        ready_word_allowed: false,
        raw_source_evidence_embedded: false,
      },
      parity_matrix: matrix,
      parity_matrix_hash: strictCanonical.strictCanonicalHash(matrix),
      acceptance_contract: {
        schema_version: SCHEMA_VERSION,
        static_fingerprint: STATIC_FINGERPRINT,
        browser_global: BROWSER_GLOBAL,
        registration_input_mode: "SEALED_IN_MEMORY_ARGUMENT_ONLY",
        fixture_input_mode: "SEALED_SYNTHETIC_THREE_STATE_ARGUMENT_ONLY",
        output_mode: "HASH_ONLY_ACCEPTANCE_RECEIPT",
        raw_state_documents_embedded: false,
        host_binding: null,
      },
      host_plan: {
        python_provider: null,
        javascript_module: null,
        host_script: null,
        host_stylesheet: null,
        route: null,
        endpoint: null,
        mount_slot: null,
        browser_review_receipt: null,
      },
      activation_order: [
        "VERIFY_EXACT_ADR0310_CONSUMER_PREREGISTRATION",
        "VERIFY_ADR0313_PARITY_REGISTRATION",
        "VERIFY_SYNTHETIC_THREE_STATE_FIXTURE",
        "BUILD_ISOLATED_JAVASCRIPT_RESULTS",
        "VERIFY_THREE_STATE_PARITY_ACCEPTANCE_RECEIPT",
        "DECLARE_HOST_BINDINGS_IN_SEPARATE_VERSION",
        "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_MOUNT",
        "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
      ],
      facts: {
        consumer_preregistration_hash_pinned: true,
        python_consumer_source_pinned: true,
        javascript_consumer_source_pinned: true,
        synthetic_fixture_pinned: true,
        three_state_parity_registered: true,
        acceptance_executed: false,
        host_bindings_declared: false,
        browser_executed: false,
        dom_mounted: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      blockers: [
        "PARITY_ACCEPTANCE_RECEIPT_NOT_YET_BOUND",
        "PYTHON_PROVIDER_UNBOUND",
        "JAVASCRIPT_HOST_MODULE_UNBOUND",
        "HOST_SCRIPT_STYLESHEET_ROUTE_ENDPOINT_AND_MOUNT_UNBOUND",
        "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
        "CURRENT_ACTIVATION_NOT_AUTHORIZED",
        "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
      ],
      authority: {
        acceptance_execution_allowed: false,
        python_provider_binding_allowed: false,
        javascript_module_binding_allowed: false,
        app_import_allowed: false,
        route_registration_allowed: false,
        endpoint_registration_allowed: false,
        html_script_binding_allowed: false,
        stylesheet_link_binding_allowed: false,
        browser_execution_allowed: false,
        dom_mount_allowed: false,
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
        writer_allowed: false,
      },
      decision:
        "THREE_STATE_PYTHON_JAVASCRIPT_CONSUMER_PARITY_REGISTERED_ACCEPTANCE_HOST_BROWSER_DOM_CURRENT_PAPER_AND_LIVE_UNBOUND",
    };
    return {
      ...core,
      parity_registration_hash:
        strictCanonical.strictCanonicalHash(core),
    };
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
    registration
  ) {
    try {
      if (
        !strictCanonical.isPlainRecord(registration) ||
        !strictCanonical.verifySealedDocument(
          registration,
          "parity_registration_hash"
        )
      ) {
        return false;
      }
      return (
        strictCanonical.strictCanonicalStringify(registration) ===
        strictCanonical.strictCanonicalStringify(expectedRegistration())
      );
    } catch (error) {
      return false;
    }
  }

  function verifyInputFixture(fixture) {
    try {
      return (
        hasExactKeys(fixture, [
          "blocked_result",
          "fixture_schema_version",
          "known_result",
          "synthetic_only",
          "unknown_result",
        ]) &&
        fixture.fixture_schema_version === INPUT_FIXTURE_SCHEMA_VERSION &&
        fixture.synthetic_only === true &&
        strictCanonical.strictCanonicalHash(fixture) ===
          INPUT_FIXTURE_CANONICAL_HASH
      );
    } catch (error) {
      return false;
    }
  }

  function authorityLocks() {
    return {
      host_binding_allowed: false,
      app_import_allowed: false,
      route_registration_allowed: false,
      endpoint_registration_allowed: false,
      html_script_binding_allowed: false,
      stylesheet_link_binding_allowed: false,
      browser_execution_allowed: false,
      dom_mount_allowed: false,
      current_admission_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
      writer_allowed: false,
    };
  }

  function transportLocks() {
    return {
      mode: "IN_MEMORY_ARGUMENT_AND_RETURN_ONLY",
      provider: null,
      route: null,
      endpoint: null,
      host_script: null,
      host_stylesheet: null,
      mount_slot: null,
      network_used: false,
      storage_used: false,
    };
  }

  function sealReceipt(core) {
    return deepFreeze({
      ...core,
      acceptance_receipt_hash:
        strictCanonical.strictCanonicalHash(core),
    });
  }

  function blockedReceipt(registrationExact, fixtureExact, registration) {
    const core = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: "BLOCKED",
      reason_code: "PARITY_INPUT_REJECTED_NO_ACCEPTANCE",
      parity_registration_hash:
        registrationExact && registration
          ? registration.parity_registration_hash
          : null,
      parity_matrix_hash:
        registrationExact && registration
          ? registration.parity_matrix_hash
          : null,
      status_mapping_hash: STATUS_MAPPING_HASH,
      state_receipts: [],
      facts: {
        registration_verified: registrationExact,
        fixture_verified: fixtureExact,
        python_results_verified: false,
        javascript_results_verified: false,
        three_state_parity_exact: false,
        known_unknown_markup_distinct: false,
        raw_state_documents_embedded: false,
        host_bindings_declared: false,
        browser_executed: false,
        dom_mounted: false,
        profitability_proven: false,
      },
      blockers: [
        "PARITY_INPUT_NOT_EXACT",
        "HOST_BINDINGS_UNBOUND",
        "BROWSER_AND_DOM_UNAUTHORIZED",
        "CURRENT_ACTIVATION_NOT_AUTHORIZED",
        "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
      ],
      transport: transportLocks(),
      authority: authorityLocks(),
    };
    return sealReceipt(core);
  }

  function buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
    registration,
    fixture
  ) {
    const registrationExact =
      verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
        registration
      );
    const fixtureExact = verifyInputFixture(fixture);
    if (!registrationExact || !fixtureExact) {
      return blockedReceipt(
        registrationExact,
        fixtureExact,
        registrationExact ? registration : null
      );
    }

    try {
      const stateReceipts = [];
      const javascriptResults = [];
      for (let index = 0; index < STATE_ORDER.length; index += 1) {
        const state = STATE_ORDER[index];
        const key = state.toLowerCase() + "_result";
        const pythonResult = fixture[key];
        const expected = registration.parity_matrix[index];
        if (
          !inspectionConsumer.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
            pythonResult
          )
        ) {
          return blockedReceipt(true, true, registration);
        }
        const javascriptResult =
          inspectionConsumer.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
            pythonResult
          );
        if (
          !inspectionConsumer.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
            javascriptResult,
            pythonResult
          )
        ) {
          return blockedReceipt(true, true, registration);
        }
        javascriptResults.push(javascriptResult);
        const actual = {
          state,
          python_result_hash: pythonResult.consumer_result_hash,
          python_envelope_hash: pythonResult.envelope_hash,
          javascript_result_hash:
            javascriptResult.javascript_consumer_result_hash,
          extraction_receipt_hash: javascriptResult.extraction_receipt
            ? javascriptResult.extraction_receipt.receipt_hash
            : null,
          presentation_hash: javascriptResult.presentation_hash,
          markup_hash:
            javascriptResult.markup === null
              ? null
              : strictCanonical.strictCanonicalHash(javascriptResult.markup),
          bridge_status_label: javascriptResult.bridge_view_model
            ? javascriptResult.bridge_view_model.status_label
            : null,
          source_hash_policy: Object.values(
            pythonResult.source_hashes
          ).every((value) => typeof value === "string")
            ? "EXACT_64_HEX"
            : Object.values(pythonResult.source_hashes).every(
                (value) => value === null
              )
            ? "ALL_NULL"
            : "MIXED",
          matched: true,
        };
        const expectedProjection = {
          state: expected.state,
          python_result_hash: expected.python_result_hash,
          python_envelope_hash: expected.python_envelope_hash,
          javascript_result_hash: expected.javascript_result_hash,
          extraction_receipt_hash: expected.extraction_receipt_hash,
          presentation_hash: expected.presentation_hash,
          markup_hash: expected.markup_hash,
          bridge_status_label: expected.bridge_status_label,
          source_hash_policy: expected.source_hash_policy,
          matched: true,
        };
        if (
          strictCanonical.strictCanonicalStringify(actual) !==
          strictCanonical.strictCanonicalStringify(expectedProjection)
        ) {
          return blockedReceipt(true, true, registration);
        }
        stateReceipts.push(actual);
      }

      const knownMarkup = javascriptResults[0].markup;
      const unknownMarkup = javascriptResults[1].markup;
      if (
        typeof knownMarkup !== "string" ||
        typeof unknownMarkup !== "string" ||
        knownMarkup === unknownMarkup
      ) {
        return blockedReceipt(true, true, registration);
      }

      const core = {
        schema_version: SCHEMA_VERSION,
        static_fingerprint: STATIC_FINGERPRINT,
        status: "EXACT",
        reason_code:
          "THREE_STATE_CROSS_RUNTIME_CONSUMER_PARITY_EXACT_HOST_UNBOUND",
        parity_registration_hash: registration.parity_registration_hash,
        parity_matrix_hash: registration.parity_matrix_hash,
        status_mapping_hash: STATUS_MAPPING_HASH,
        state_receipts: stateReceipts,
        facts: {
          registration_verified: true,
          fixture_verified: true,
          python_results_verified: true,
          javascript_results_verified: true,
          three_state_parity_exact: true,
          known_unknown_markup_distinct: true,
          raw_state_documents_embedded: false,
          host_bindings_declared: false,
          browser_executed: false,
          dom_mounted: false,
          profitability_proven: false,
        },
        blockers: [
          "HOST_BINDINGS_UNBOUND",
          "BROWSER_AND_DOM_UNAUTHORIZED",
          "CURRENT_ACTIVATION_NOT_AUTHORIZED",
          "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
        ],
        transport: transportLocks(),
        authority: authorityLocks(),
      };
      return sealReceipt(core);
    } catch (error) {
      return blockedReceipt(true, true, registration);
    }
  }

  function verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
    document,
    registration,
    fixture
  ) {
    try {
      if (
        !strictCanonical.isPlainRecord(document) ||
        !strictCanonical.verifySealedDocument(
          document,
          "acceptance_receipt_hash"
        ) ||
        document.schema_version !== SCHEMA_VERSION ||
        document.static_fingerprint !== STATIC_FINGERPRINT ||
        !strictCanonical.isPlainRecord(document.authority) ||
        !Object.values(document.authority).every((value) => value === false)
      ) {
        return false;
      }
      const expected =
        buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
          registration,
          fixture
        );
      return (
        strictCanonical.strictCanonicalStringify(document) ===
        strictCanonical.strictCanonicalStringify(expected)
      );
    } catch (error) {
      return false;
    }
  }

  return deepFreeze({
    REGISTRATION_SCHEMA_VERSION,
    REGISTRATION_STATIC_FINGERPRINT,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    BROWSER_GLOBAL,
    CONSUMER_PREREGISTRATION_HASH,
    PYTHON_CONSUMER_CONTRACT_HASH,
    JAVASCRIPT_CONSUMER_CONTRACT_HASH,
    INPUT_FIXTURE_SCHEMA_VERSION,
    INPUT_FIXTURE_CANONICAL_HASH,
    STATUS_MAPPING_HASH,
    STATE_ORDER,
    FUNCTION_EXPORTS,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1,
    buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1,
    verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1,
  });
});
