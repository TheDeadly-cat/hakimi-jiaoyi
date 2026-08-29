(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) {
    root.HakimiStrategyCorrelationUncertaintyMultiWindowEffectiveBudgetNeutralPresentationV1 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical
) {
  "use strict";

  if (!strictCanonical
    || typeof strictCanonical.sealDocument !== "function"
    || typeof strictCanonical.verifySealedDocument !== "function"
    || typeof strictCanonical.strictCanonicalStringify !== "function"
    || typeof strictCanonical.sha256Hex !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var SCHEMA_VERSION =
    "strategy-correlation-uncertainty-multi-window-effective-budget-neutral-presentation-v1";
  var STATIC_FINGERPRINT =
    "20260824-strategy-correlation-uncertainty-multi-window-effective-budget-neutral-presentation-v1-unmounted-lock-1";
  var UNCERTAINTY_GATE_SCHEMA_VERSION =
    "strategy-correlation-uncertainty-multi-window-cluster-gate-v1";
  var UNCERTAINTY_GATE_STATIC_FINGERPRINT =
    "20260824-strategy-correlation-uncertainty-multi-window-cluster-gate-v1-synthetic-unmounted-conservative-union-lock-1";
  var UNCERTAINTY_GATE_CONTRACT_HASH =
    "fba4f4d72763e894d639f11165fc722b2c3aaa2b7440e4bba69faaba1a615310";
  var UNCERTAINTY_GATE_SOURCE_SHA256 =
    "4c64530efa76730404b7441ecdb9dab9ee914c156116296eea21a54c47a5f9e2";
  var BUDGET_BINDING_SCHEMA_VERSION =
    "strategy-correlation-uncertainty-multi-window-effective-bet-budget-binding-evaluation-v1";
  var BUDGET_BINDING_STATIC_FINGERPRINT =
    "20260824-strategy-correlation-uncertainty-multi-window-effective-bet-budget-binding-v1-synthetic-unmounted-veto-lock-1";
  var BUDGET_BINDING_CONTRACT_HASH =
    "1ef0cc02c968dbf8832b95c59b07522950726ea22b1ec1ad149df5cbec1500ae";
  var BUDGET_BINDING_SOURCE_SHA256 =
    "993a28a33e20bc64666ec3229e420a3299257382a25d9ff2d4aaf8da8ffd8918";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var INPUT_KEYS = [
    "uncertainty_budget_binding",
    "uncertainty_cluster_gate",
  ];
  var MAX_DEPTH = 24;
  var MAX_NODES = 65536;
  var MAX_OBJECT_KEYS = 256;
  var MAX_ARRAY_LENGTH = 4096;
  var MAX_STRING_LENGTH = 8192;

  function exactHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return false;
    }
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every(function (key, index) {
      return key === wanted[index];
    });
  }

  function plainRecord(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return false;
    }
    var prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function validatePlainJson(value) {
    var budget = { nodes: 0 };
    var seen = new WeakSet();

    function visit(current, depth) {
      budget.nodes += 1;
      if (budget.nodes > MAX_NODES || depth > MAX_DEPTH) return false;
      if (current === null || typeof current === "boolean") return true;
      if (typeof current === "string") {
        return current.length <= MAX_STRING_LENGTH;
      }
      if (typeof current === "number") return Number.isFinite(current);
      if (typeof current !== "object") return false;
      if (seen.has(current)) return false;
      seen.add(current);
      if (Object.getOwnPropertySymbols(current).length !== 0) return false;

      var isArray = Array.isArray(current);
      var prototype = Object.getPrototypeOf(current);
      if (isArray) {
        if (prototype !== Array.prototype
          || current.length > MAX_ARRAY_LENGTH) {
          return false;
        }
        if (Object.getOwnPropertyNames(current).length !== current.length + 1) {
          return false;
        }
        for (var index = 0; index < current.length; index += 1) {
          var arrayDescriptor = Object.getOwnPropertyDescriptor(
            current,
            String(index)
          );
          if (!arrayDescriptor
            || !arrayDescriptor.enumerable
            || typeof arrayDescriptor.get === "function"
            || typeof arrayDescriptor.set === "function"
            || !visit(arrayDescriptor.value, depth + 1)) {
            return false;
          }
        }
        return true;
      }

      if (prototype !== Object.prototype && prototype !== null) return false;
      var names = Object.getOwnPropertyNames(current);
      if (names.length > MAX_OBJECT_KEYS) return false;
      for (var nameIndex = 0; nameIndex < names.length; nameIndex += 1) {
        var name = names[nameIndex];
        if (name.length > 128
          || name === "__proto__"
          || name === "prototype"
          || name === "constructor") {
          return false;
        }
        var descriptor = Object.getOwnPropertyDescriptor(current, name);
        if (!descriptor
          || !descriptor.enumerable
          || typeof descriptor.get === "function"
          || typeof descriptor.set === "function"
          || !visit(descriptor.value, depth + 1)) {
          return false;
        }
      }
      return true;
    }

    try {
      return visit(value, 0);
    } catch (_error) {
      return false;
    }
  }

  function authorityPromotionPresent(value) {
    var promoted = false;
    function visit(current, parentKey) {
      if (promoted || current === null || typeof current !== "object") return;
      Object.keys(current).forEach(function (key) {
        var child = current[key];
        if (child === true
          && /(?:^|_)(?:allowed|authorized|permission_granted|authority_granted)$/i
            .test(key)) {
          promoted = true;
          return;
        }
        if (typeof child === "string"
          && [
            "AUTHORIZED",
            "CLAIM_ACCEPTED",
            "ADMISSION_GRANTED",
            "WRITER_ENABLED",
            "PAPER_ENABLED",
            "LIVE_ENABLED",
          ].includes(child)) {
          promoted = true;
          return;
        }
        visit(child, key);
      });
    }
    visit(value, "");
    return promoted;
  }

  function canonicalHash(value) {
    return strictCanonical.sha256Hex(
      strictCanonical.strictCanonicalStringify(value)
    );
  }

  function nonNegativeNumber(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0
      ? value
      : null;
  }

  function contractMarkersExact(gate, binding) {
    return gate.schema_version === UNCERTAINTY_GATE_SCHEMA_VERSION
      && gate.static_fingerprint === UNCERTAINTY_GATE_STATIC_FINGERPRINT
      && gate.gate_contract_hash === UNCERTAINTY_GATE_CONTRACT_HASH
      && binding.schema_version === BUDGET_BINDING_SCHEMA_VERSION
      && binding.static_fingerprint === BUDGET_BINDING_STATIC_FINGERPRINT
      && binding.binding_contract_hash === BUDGET_BINDING_CONTRACT_HASH;
  }

  function authorityLocked(gate, binding) {
    if (!plainRecord(gate.authority) || !plainRecord(binding.authority)) {
      return false;
    }
    var fields = [
      "current_admission_allowed",
      "effective_budget_activation_allowed",
      "http_registration_allowed",
      "runtime_activation_allowed",
      "writer_allowed",
      "paper_authorized",
      "live_order_allowed",
    ];
    return fields.every(function (field) {
      return gate.authority[field] === false
        && binding.authority[field] === false;
    }) && !authorityPromotionPresent(gate) && !authorityPromotionPresent(binding);
  }

  function crossBindingExact(gate, binding) {
    return binding.uncertainty_gate_hash === gate.gate_hash
      && binding.uncertainty_gate_status === gate.status
      && binding.uncertainty_dependence_edge_count
        === gate.dependence_edge_count
      && binding.uncertainty_cross_cluster_edge_count
        === gate.cross_cluster_dependence_edge_count
      && binding.uncertainty_component_count
        === gate.derived_conservative_component_count;
  }

  function derivePresentationState(gate, binding) {
    if (!plainRecord(binding.facts)
      || typeof binding.facts.risk_increasing !== "boolean"
      || typeof binding.facts.budget_verification_attempted !== "boolean"
      || typeof binding.facts.budget_evaluation_exactly_verified !== "boolean") {
      return null;
    }
    var riskIncreasing = binding.facts.risk_increasing;
    if (gate.status === "BLOCK" && riskIncreasing) {
      return binding.status === "BLOCK"
        && binding.reason_code
          === "CROSS_CLUSTER_DEPENDENCE_REQUIRES_REPREREGISTRATION"
        && binding.facts.budget_verification_attempted === false
        && binding.trusted_effective_budget_document === null
        ? "CROSS_CLUSTER_DEPENDENCE_VETO"
        : null;
    }
    if (gate.status === "BLOCK" && !riskIncreasing) {
      return binding.status === "PASS"
        && binding.effective_budget_status === "PASS"
        && binding.effective_budget_decision === "RISK_REDUCTION_PATH"
        && binding.facts.budget_evaluation_exactly_verified === true
        ? "RISK_REDUCTION_ONLY"
        : null;
    }
    if (gate.status !== "PASS") return null;
    if (binding.status === "BLOCK"
      && binding.facts.budget_evaluation_exactly_verified === true) {
      return "DOWNSTREAM_BUDGET_CHAIN_BLOCK";
    }
    if (binding.status !== "PASS"
      || binding.facts.budget_evaluation_exactly_verified !== true
      || !plainRecord(binding.trusted_effective_budget_document)) {
      return null;
    }
    if (binding.effective_budget_status === "BLOCK"
      && binding.effective_budget_decision === "BLOCK") {
      return "RESEARCH_BUDGET_BLOCK_OBSERVED";
    }
    if (binding.effective_budget_status === "PASS"
      && binding.effective_budget_decision === "RISK_REDUCTION_PATH") {
      return "RISK_REDUCTION_ONLY";
    }
    if (binding.effective_budget_status === "PASS"
      && binding.effective_budget_decision
        === "PASS_STRATIFIED_RESEARCH_BUDGET") {
      return "RESEARCH_BUDGET_CONTRACT_OBSERVED";
    }
    return null;
  }

  function emptyInspection(reasonCode) {
    return {
      known: false,
      reason_code: reasonCode,
      presentation_state: "UNKNOWN",
      plain_json_documents_verified: false,
      contract_markers_verified: false,
      cross_binding_verified: false,
      authority_locked: false,
      gate_document_sha256: null,
      binding_document_sha256: null,
      document_set_sha256: null,
      gate_hash: null,
      binding_evaluation_hash: null,
      metrics: null,
    };
  }

  function metrics(gate, binding) {
    var budget = plainRecord(binding.trusted_effective_budget_document)
      ? binding.trusted_effective_budget_document
      : null;
    var portfolio = budget && plainRecord(budget.portfolio)
      ? budget.portfolio
      : null;
    return {
      window_count: nonNegativeNumber(gate.window_count),
      dependence_edge_count: nonNegativeNumber(gate.dependence_edge_count),
      cross_cluster_dependence_edge_count: nonNegativeNumber(
        gate.cross_cluster_dependence_edge_count
      ),
      conservative_component_count: nonNegativeNumber(
        gate.derived_conservative_component_count
      ),
      preregistered_cluster_count: nonNegativeNumber(
        gate.preregistered_cluster_count
      ),
      active_cluster_count: portfolio
        ? nonNegativeNumber(portfolio.active_cluster_count)
        : null,
      symbol_ticket_count: portfolio
        ? nonNegativeNumber(portfolio.symbol_ticket_count)
        : null,
      conservative_weighted_strata_count: portfolio
        ? nonNegativeNumber(
            portfolio.conservative_weighted_effective_strata_count
          )
        : null,
    };
  }

  function inspectInput(input) {
    try {
      if (!validatePlainJson(input)
        || !exactKeys(input, INPUT_KEYS)
        || !plainRecord(input.uncertainty_cluster_gate)
        || !plainRecord(input.uncertainty_budget_binding)) {
        return emptyInspection("SOURCE_DOCUMENT_SET_NOT_BOUNDED_PLAIN_JSON");
      }
      var gate = input.uncertainty_cluster_gate;
      var binding = input.uncertainty_budget_binding;
      var gateDocumentHash = canonicalHash(gate);
      var bindingDocumentHash = canonicalHash(binding);
      var documentSetHash = canonicalHash({
        uncertainty_budget_binding_sha256: bindingDocumentHash,
        uncertainty_cluster_gate_sha256: gateDocumentHash,
      });
      var contractsExact = contractMarkersExact(gate, binding);
      var hashesExact = exactHash(gate.gate_hash)
        && exactHash(binding.evaluation_hash)
        && exactHash(binding.uncertainty_gate_hash);
      var crossExact = hashesExact && crossBindingExact(gate, binding);
      var locked = authorityLocked(gate, binding);
      var state = contractsExact && crossExact && locked
        ? derivePresentationState(gate, binding)
        : null;
      var reasonCode = "LOCAL_RESEARCH_EVIDENCE_PRESENTED_PERMISSION_LOCKED";
      if (!contractsExact) {
        reasonCode = "PINNED_SOURCE_CONTRACT_MARKERS_NOT_EXACT";
      } else if (!hashesExact) {
        reasonCode = "SOURCE_HASH_FIELDS_NOT_EXACT";
      } else if (!crossExact) {
        reasonCode = "GATE_TO_BUDGET_CROSS_BINDING_NOT_EXACT";
      } else if (!locked) {
        reasonCode = "SOURCE_AUTHORITY_LOCK_NOT_EXACT";
      } else if (state === null) {
        reasonCode = "SOURCE_SEMANTICS_NOT_COHERENT";
      }
      return {
        known: state !== null,
        reason_code: reasonCode,
        presentation_state: state || "UNKNOWN",
        plain_json_documents_verified: true,
        contract_markers_verified: contractsExact,
        cross_binding_verified: crossExact,
        authority_locked: locked,
        gate_document_sha256: gateDocumentHash,
        binding_document_sha256: bindingDocumentHash,
        document_set_sha256: documentSetHash,
        gate_hash: hashesExact ? gate.gate_hash : null,
        binding_evaluation_hash: hashesExact ? binding.evaluation_hash : null,
        metrics: state !== null ? metrics(gate, binding) : null,
      };
    } catch (_error) {
      return emptyInspection("SOURCE_DOCUMENT_SET_INSPECTION_FAILED");
    }
  }

  function stages(inspection) {
    return [
      {
        axis: "SOURCE",
        state: inspection.plain_json_documents_verified
          ? "HASH_BOUND_LOCAL"
          : "UNKNOWN",
        reason_code: inspection.plain_json_documents_verified
          ? "LOCAL_DOCUMENT_HASHES_ONLY"
          : "SOURCE_DOCUMENTS_UNAVAILABLE",
      },
      {
        axis: "GAP",
        state: "OPEN",
        reason_code: "WINDOW_ISSUER_MARKET_AND_EXTERNAL_VALIDITY_UNPROVEN",
      },
      {
        axis: "MATURITY",
        state: inspection.known ? "SYNTHETIC_UNMOUNTED" : "UNKNOWN",
        reason_code: inspection.known
          ? "LOCAL_VETO_AND_BUDGET_CONTRACT_ONLY"
          : "MATURITY_SOURCE_NOT_EXACT",
      },
      {
        axis: "PERMISSION",
        state: "UNAUTHORIZED",
        reason_code: "CURRENT_PAPER_LIVE_AND_WRITER_LOCKED",
      },
    ];
  }

  function authority() {
    return {
      current_admission_allowed: false,
      dom_mount_allowed: false,
      effective_budget_activation_allowed: false,
      http_registration_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      runtime_asset_loading_allowed: false,
      writer_allowed: false,
    };
  }

  function blockers() {
    return [
      "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN",
      "MARKET_VALIDITY_UNPROVEN",
      "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
      "DOM_MOUNT_UNAUTHORIZED",
      "CURRENT_ADMISSION_LOCKED",
      "PAPER_UNAUTHORIZED",
      "LIVE_UNAUTHORIZED",
      "WRITER_UNAUTHORIZED",
    ];
  }

  function buildUncertaintyEffectiveBudgetNeutralPresentationV1(input) {
    var inspection = inspectInput(input);
    var documentValue = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: inspection.known ? "BLOCKED" : "UNKNOWN",
      contract_state: inspection.known
        ? "LOCAL_RESEARCH_EVIDENCE"
        : "UNKNOWN",
      presentation_state: inspection.presentation_state,
      reason_code: inspection.reason_code,
      tone: "NEUTRAL",
      stage_order: STAGE_ORDER.slice(),
      stages: stages(inspection),
      source: {
        uncertainty_gate_contract_hash: inspection.contract_markers_verified
          ? UNCERTAINTY_GATE_CONTRACT_HASH
          : null,
        uncertainty_gate_source_sha256: inspection.contract_markers_verified
          ? UNCERTAINTY_GATE_SOURCE_SHA256
          : null,
        budget_binding_contract_hash: inspection.contract_markers_verified
          ? BUDGET_BINDING_CONTRACT_HASH
          : null,
        budget_binding_source_sha256: inspection.contract_markers_verified
          ? BUDGET_BINDING_SOURCE_SHA256
          : null,
        embedded_uncertainty_gate_hash: inspection.gate_hash,
        embedded_budget_binding_evaluation_hash:
          inspection.binding_evaluation_hash,
        uncertainty_gate_document_sha256:
          inspection.gate_document_sha256,
        budget_binding_document_sha256:
          inspection.binding_document_sha256,
        document_set_sha256: inspection.document_set_sha256,
      },
      metrics: inspection.metrics,
      facts: {
        bounded_plain_json_documents_verified:
          inspection.plain_json_documents_verified,
        pinned_contract_markers_verified:
          inspection.contract_markers_verified,
        gate_to_budget_cross_binding_verified:
          inspection.cross_binding_verified,
        source_authority_lock_verified: inspection.authority_locked,
        local_document_hashes_computed:
          inspection.document_set_sha256 !== null,
        raw_source_documents_embedded: false,
        raw_window_audits_embedded: false,
        raw_price_or_return_series_embedded: false,
        dynamic_reclustering_performed: false,
        external_independent_review_complete: false,
        dom_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
      },
      blockers: blockers(),
      authority: authority(),
    };
    return strictCanonical.sealDocument(documentValue, "presentation_hash");
  }

  function canonicalEqual(first, second) {
    try {
      return strictCanonical.strictCanonicalStringify(first)
        === strictCanonical.strictCanonicalStringify(second);
    } catch (_error) {
      return false;
    }
  }

  function verifyUncertaintyEffectiveBudgetNeutralPresentationV1(
    presentation,
    input
  ) {
    if (!strictCanonical.verifySealedDocument(
      presentation,
      "presentation_hash"
    )) {
      return false;
    }
    return canonicalEqual(
      presentation,
      buildUncertaintyEffectiveBudgetNeutralPresentationV1(input)
    );
  }

  return Object.freeze({
    BUDGET_BINDING_CONTRACT_HASH: BUDGET_BINDING_CONTRACT_HASH,
    BUDGET_BINDING_SCHEMA_VERSION: BUDGET_BINDING_SCHEMA_VERSION,
    BUDGET_BINDING_SOURCE_SHA256: BUDGET_BINDING_SOURCE_SHA256,
    BUDGET_BINDING_STATIC_FINGERPRINT:
      BUDGET_BINDING_STATIC_FINGERPRINT,
    INPUT_LIMITS: Object.freeze({
      max_array_length: MAX_ARRAY_LENGTH,
      max_depth: MAX_DEPTH,
      max_nodes: MAX_NODES,
      max_object_keys: MAX_OBJECT_KEYS,
      max_string_length: MAX_STRING_LENGTH,
    }),
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STAGE_ORDER: Object.freeze(STAGE_ORDER.slice()),
    UNCERTAINTY_GATE_CONTRACT_HASH: UNCERTAINTY_GATE_CONTRACT_HASH,
    UNCERTAINTY_GATE_SCHEMA_VERSION: UNCERTAINTY_GATE_SCHEMA_VERSION,
    UNCERTAINTY_GATE_SOURCE_SHA256: UNCERTAINTY_GATE_SOURCE_SHA256,
    UNCERTAINTY_GATE_STATIC_FINGERPRINT:
      UNCERTAINTY_GATE_STATIC_FINGERPRINT,
    buildUncertaintyEffectiveBudgetNeutralPresentationV1:
      buildUncertaintyEffectiveBudgetNeutralPresentationV1,
    verifyUncertaintyEffectiveBudgetNeutralPresentationV1:
      verifyUncertaintyEffectiveBudgetNeutralPresentationV1,
  });
});
