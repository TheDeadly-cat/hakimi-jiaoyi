(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) {
    root.HakimiStrategyCorrelationMatrixGeometryBudgetMultiWindowSecurityLifecycleNeutralPresentationV1 = api;
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
    "strategy-correlation-matrix-geometry-budget-multi-window-security-lifecycle-neutral-presentation-v1";
  var STATIC_FINGERPRINT =
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-security-lifecycle-neutral-presentation-v1-unmounted-lock-1";
  var SECURITY_GATE_CONTRACT_HASH =
    "f1da8347793aee5d57462ab2c46a38cce3dcd6889c78bb975a65a0b0c0a3e645";
  var SECURITY_GATE_PREREGISTRATION_HASH =
    "580e8b14d316c47b80c660bc7ad2236351e5daaa80f1246ee45fd4501c6be372";
  var LIFECYCLE_OWNER_CONTRACT_HASH =
    "73833a5ada7b94b52bbf7ec86130f033dab0ca582288b946a4d7a67498efd202";
  var LIFECYCLE_OWNER_STATIC_FINGERPRINT =
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-request-lifecycle-owner-candidate-v1-synthetic-unregistered-atomic-lock-1";
  var SECURITY_GAP_REASON = "SECURITY_SEMANTICS_UNAVAILABLE";
  var CLAIM_REJECTION_REASON =
    "CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var INPUT_KEYS = [
    "lifecycle_claim_result",
    "lifecycle_owner_creation",
    "security_gate_evaluation",
  ];
  var MAX_DEPTH = 16;
  var MAX_NODES = 4096;
  var MAX_OBJECT_KEYS = 128;
  var MAX_ARRAY_LENGTH = 128;
  var MAX_STRING_LENGTH = 4096;
  var PROMOTION_MARKERS = Object.freeze([
    "AUTHORIZED",
    "ALLOWED",
    "CLAIM_ACCEPTED",
    "ADMISSION_GRANTED",
    "WRITER_ENABLED",
    "PAPER_ENABLED",
    "LIVE_ENABLED",
  ]);

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
        var arrayNames = Object.getOwnPropertyNames(current);
        if (arrayNames.length !== current.length + 1) return false;
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

  function scanDocument(value) {
    var strings = new Set();
    var authorityPromotion = false;

    function visit(current, parentKey) {
      if (typeof current === "string") {
        strings.add(current);
        return;
      }
      if (typeof current === "boolean") {
        if (current === true
          && /(?:^|_)(?:allowed|authorized|permission_granted|authority_granted)$/i
            .test(parentKey || "")) {
          authorityPromotion = true;
        }
        return;
      }
      if (current === null || typeof current !== "object") return;
      Object.keys(current).forEach(function (key) {
        visit(current[key], key);
      });
    }

    visit(value, "");
    return { strings: strings, authority_promotion: authorityPromotion };
  }

  function hasPromotionMarker(scan) {
    if (scan.authority_promotion) return true;
    return PROMOTION_MARKERS.some(function (marker) {
      return scan.strings.has(marker);
    });
  }

  function canonicalHash(value) {
    return strictCanonical.sha256Hex(
      strictCanonical.strictCanonicalStringify(value)
    );
  }

  function emptyInspection(reasonCode) {
    return {
      known: false,
      reason_code: reasonCode,
      plain_json_documents_verified: false,
      pinned_source_contracts_verified: false,
      rejection_semantics_verified: false,
      authority_promotion_absent: false,
      security_gate_document_sha256: null,
      lifecycle_owner_creation_sha256: null,
      lifecycle_claim_result_sha256: null,
      document_set_sha256: null,
    };
  }

  function inspectInput(input) {
    try {
      if (!validatePlainJson(input)
        || !exactKeys(input, INPUT_KEYS)
        || !plainRecord(input.security_gate_evaluation)
        || !plainRecord(input.lifecycle_owner_creation)
        || !plainRecord(input.lifecycle_claim_result)) {
        return emptyInspection("SOURCE_DOCUMENT_SET_NOT_PLAIN_JSON");
      }

      var gateHash = canonicalHash(input.security_gate_evaluation);
      var creationHash = canonicalHash(input.lifecycle_owner_creation);
      var claimHash = canonicalHash(input.lifecycle_claim_result);
      var setHash = canonicalHash({
        lifecycle_claim_result_sha256: claimHash,
        lifecycle_owner_creation_sha256: creationHash,
        security_gate_document_sha256: gateHash,
      });
      var gateScan = scanDocument(input.security_gate_evaluation);
      var creationScan = scanDocument(input.lifecycle_owner_creation);
      var claimScan = scanDocument(input.lifecycle_claim_result);
      var contractsExact =
        gateScan.strings.has(SECURITY_GATE_CONTRACT_HASH)
        && gateScan.strings.has(SECURITY_GATE_PREREGISTRATION_HASH)
        && creationScan.strings.has(LIFECYCLE_OWNER_CONTRACT_HASH)
        && creationScan.strings.has(LIFECYCLE_OWNER_STATIC_FINGERPRINT);
      var rejectionExact = gateScan.strings.has("UNKNOWN")
        && gateScan.strings.has("UNAUTHORIZED")
        && gateScan.strings.has(SECURITY_GAP_REASON)
        && claimScan.strings.has(CLAIM_REJECTION_REASON);
      var promotionAbsent = !hasPromotionMarker(gateScan)
        && !hasPromotionMarker(creationScan)
        && !hasPromotionMarker(claimScan);
      var known = contractsExact && rejectionExact && promotionAbsent;
      var reasonCode = "LOCAL_SECURITY_REJECTION_PRESENTED_AUTHORITY_UNAVAILABLE";
      if (!contractsExact) {
        reasonCode = "PINNED_SOURCE_CONTRACT_MARKERS_NOT_EXACT";
      } else if (!rejectionExact) {
        reasonCode = "SECURITY_REJECTION_MARKERS_NOT_EXACT";
      } else if (!promotionAbsent) {
        reasonCode = "SOURCE_DOCUMENT_SET_CONTAINS_AUTHORITY_PROMOTION";
      }
      return {
        known: known,
        reason_code: reasonCode,
        plain_json_documents_verified: true,
        pinned_source_contracts_verified: contractsExact,
        rejection_semantics_verified: rejectionExact,
        authority_promotion_absent: promotionAbsent,
        security_gate_document_sha256: gateHash,
        lifecycle_owner_creation_sha256: creationHash,
        lifecycle_claim_result_sha256: claimHash,
        document_set_sha256: setHash,
      };
    } catch (_error) {
      return emptyInspection("SOURCE_DOCUMENT_SET_INSPECTION_FAILED");
    }
  }

  function authority() {
    return {
      current_admission_allowed: false,
      dom_mount_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      provider_invocation_allowed: false,
      request_handler_invocation_allowed: false,
      runtime_asset_loading_allowed: false,
      writer_allowed: false,
    };
  }

  function blockers() {
    return [
      "HOST_AUTHORIZATION_PROVIDER_UNAVAILABLE",
      "CSRF_PROVIDER_UNAVAILABLE",
      "ORIGIN_PROVIDER_UNAVAILABLE",
      "EXTERNAL_VERIFIER_UNAVAILABLE",
      "ISSUER_TRUST_UNAVAILABLE",
      "CURRENT_ADMISSION_LOCKED",
      "PAPER_UNAUTHORIZED",
      "LIVE_UNAUTHORIZED",
      "WRITER_UNAUTHORIZED",
    ];
  }

  function stages(inspection) {
    return [
      {
        axis: "SOURCE",
        state: inspection.plain_json_documents_verified
          ? "HASH_BOUND"
          : "UNKNOWN",
        reason_code: inspection.plain_json_documents_verified
          ? "LOCAL_JSON_DOCUMENT_HASHES_ONLY"
          : "SOURCE_DOCUMENTS_UNAVAILABLE",
      },
      {
        axis: "GAP",
        state: "OPEN",
        reason_code:
          "HOST_SECURITY_PROVIDERS_VERIFIERS_AND_ISSUER_TRUST_UNAVAILABLE",
      },
      {
        axis: "MATURITY",
        state: inspection.known ? "SYNTHETIC_UNREGISTERED" : "UNKNOWN",
        reason_code: inspection.known
          ? "IN_PROCESS_ATOMIC_REJECTION_ONLY"
          : "MATURITY_SOURCE_NOT_EXACT",
      },
      {
        axis: "PERMISSION",
        state: "UNAUTHORIZED",
        reason_code: "CURRENT_PAPER_LIVE_AND_WRITER_LOCKED",
      },
    ];
  }

  function buildSecurityLifecycleNeutralPresentationV1(input) {
    var inspection = inspectInput(input);
    var value = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: inspection.known ? "BLOCKED" : "UNKNOWN",
      presentation_state: inspection.known
        ? "LOCAL_SECURITY_REJECTION_ONLY"
        : "UNKNOWN",
      reason_code: inspection.reason_code,
      tone: "NEUTRAL",
      stage_order: STAGE_ORDER.slice(),
      stages: stages(inspection),
      source: {
        security_gate_contract_hash:
          inspection.pinned_source_contracts_verified
            ? SECURITY_GATE_CONTRACT_HASH
            : null,
        security_gate_preregistration_hash:
          inspection.pinned_source_contracts_verified
            ? SECURITY_GATE_PREREGISTRATION_HASH
            : null,
        lifecycle_owner_contract_hash:
          inspection.pinned_source_contracts_verified
            ? LIFECYCLE_OWNER_CONTRACT_HASH
            : null,
        security_gate_document_sha256:
          inspection.security_gate_document_sha256,
        lifecycle_owner_creation_sha256:
          inspection.lifecycle_owner_creation_sha256,
        lifecycle_claim_result_sha256:
          inspection.lifecycle_claim_result_sha256,
        document_set_sha256: inspection.document_set_sha256,
      },
      facts: {
        plain_json_documents_verified:
          inspection.plain_json_documents_verified,
        pinned_source_contracts_verified:
          inspection.pinned_source_contracts_verified,
        rejection_semantics_verified:
          inspection.rejection_semantics_verified,
        authority_promotion_absent: inspection.authority_promotion_absent,
        canonical_document_hashes_computed:
          inspection.document_set_sha256 !== null,
        synthetic_evidence_only: inspection.known,
        unregistered_candidate_only: inspection.known,
        in_process_atomic_rejection_only: inspection.known,
        external_independent_review_complete: false,
        raw_source_documents_embedded: false,
        raw_security_receipts_embedded: false,
        provider_invoked: false,
        request_handler_invoked: false,
        dom_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
      },
      blockers: blockers(),
      authority: authority(),
    };
    return strictCanonical.sealDocument(value, "presentation_hash");
  }

  function canonicalEqual(first, second) {
    try {
      return strictCanonical.strictCanonicalStringify(first)
        === strictCanonical.strictCanonicalStringify(second);
    } catch (_error) {
      return false;
    }
  }

  function verifySecurityLifecycleNeutralPresentationV1(presentation, input) {
    if (!strictCanonical.verifySealedDocument(
      presentation,
      "presentation_hash"
    )) {
      return false;
    }
    return canonicalEqual(
      presentation,
      buildSecurityLifecycleNeutralPresentationV1(input)
    );
  }

  return Object.freeze({
    CLAIM_REJECTION_REASON: CLAIM_REJECTION_REASON,
    INPUT_LIMITS: Object.freeze({
      max_array_length: MAX_ARRAY_LENGTH,
      max_depth: MAX_DEPTH,
      max_nodes: MAX_NODES,
      max_object_keys: MAX_OBJECT_KEYS,
      max_string_length: MAX_STRING_LENGTH,
    }),
    LIFECYCLE_OWNER_CONTRACT_HASH: LIFECYCLE_OWNER_CONTRACT_HASH,
    LIFECYCLE_OWNER_STATIC_FINGERPRINT:
      LIFECYCLE_OWNER_STATIC_FINGERPRINT,
    SCHEMA_VERSION: SCHEMA_VERSION,
    SECURITY_GATE_CONTRACT_HASH: SECURITY_GATE_CONTRACT_HASH,
    SECURITY_GATE_PREREGISTRATION_HASH:
      SECURITY_GATE_PREREGISTRATION_HASH,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STAGE_ORDER: Object.freeze(STAGE_ORDER.slice()),
    buildSecurityLifecycleNeutralPresentationV1:
      buildSecurityLifecycleNeutralPresentationV1,
    verifySecurityLifecycleNeutralPresentationV1:
      verifySecurityLifecycleNeutralPresentationV1,
  });
});
