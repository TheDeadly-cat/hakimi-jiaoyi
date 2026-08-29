(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiWitnessStoragePersistenceAdmissionViewModelV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical
) {
  "use strict";

  if (!strictCanonical
    || typeof strictCanonical.sealDocument !== "function"
    || typeof strictCanonical.verifySealedDocument !== "function"
    || typeof strictCanonical.strictCanonicalStringify !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var SOURCE_SCHEMA_VERSION =
    "witness-ownership-snapshot-storage-persistence-admission-presentation-v1";
  var SOURCE_STATIC_FINGERPRINT =
    "20260824-witness-ownership-snapshot-storage-persistence-admission-presentation-v1-unmounted-lock-1";
  var SCHEMA_VERSION = "witness-storage-persistence-admission-view-model-v1";
  var STATIC_FINGERPRINT =
    "20260824-witness-storage-persistence-admission-view-model-v1-unmounted-lock-1";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var PENDING_CONDITIONS = [
    "EXPLICIT_ISOLATED_TEST_AUTHORIZATION_NOT_SUPPLIED",
    "REAL_IDENTITY_SOURCE_TRUTH_UNVERIFIED",
    "EXTERNAL_OBSERVER_IDENTITY_UNVERIFIED",
    "REAL_ADAPTER_EXECUTION_UNVERIFIED",
    "ISOLATED_DOMAIN_CONFINEMENT_UNVERIFIED",
    "EXTERNAL_PERSISTENCE_UNVERIFIED",
  ];
  var UNKNOWN_REASONS = [
    "EXPECTED_PERSISTENCE_ADMISSION_DECISION_HASH_NOT_EXACT",
    "EXPECTED_LINEAGE_BINDING_HASH_NOT_EXACT",
    "SOURCE_PERSISTENCE_ADMISSION_DECISION_NOT_EXACT",
    "SOURCE_DECISION_SEMANTICS_NOT_SAFE",
  ];
  var TOP_LEVEL_KEYS = [
    "schema_version", "static_fingerprint", "presentation_status",
    "display_tone", "display_state", "stage_order", "stages", "source",
    "summary", "facts", "blockers", "authority", "presentation_hash",
  ];
  var SOURCE_KEYS = [
    "persistence_admission_decision_hash", "lineage_binding_hash",
    "lineage_bundle_hash", "lineage_implementation_sha256",
  ];
  var FACT_KEYS = [
    "source_decision_exactly_verified", "bounded_projection",
    "structural_lineage_verified", "isolated_backend_test_candidate",
    "explicit_isolated_test_authorization_supplied",
    "real_identity_source_truth_verified", "external_observer_identity_verified",
    "real_adapter_execution_verified", "isolated_domain_confinement_verified",
    "external_persistence_independently_verified",
    "isolated_backend_test_authorized", "backend_mount_authorized",
    "snapshot_publication_authorized", "current_chain_activated",
    "raw_decision_document_embedded", "raw_lineage_document_embedded",
    "raw_component_hash_map_embedded", "raw_key_material_embedded",
    "raw_signature_material_embedded",
  ];
  var AUTHORITY_KEYS = [
    "descriptive_only", "asset_write_allowed", "browser_execution_allowed",
    "route_registration_allowed", "ui_consumer_mount_allowed",
    "isolated_backend_test_allowed", "backend_mount_allowed",
    "current_admission_allowed", "runtime_gate_activation_allowed",
    "writer_allowed", "paper_authorized", "live_order_allowed",
  ];
  var MAX_DEPTH = 16;
  var MAX_NODES = 4096;
  var MAX_OBJECT_KEYS = 64;
  var MAX_ARRAY_LENGTH = 64;
  var MAX_STRING_LENGTH = 4096;

  function exactHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every(function (key, index) {
      return key === wanted[index];
    });
  }

  function validatePlainJson(value) {
    var budget = { nodes: 0 };
    var seen = new WeakSet();
    function visit(current, depth) {
      budget.nodes += 1;
      if (budget.nodes > MAX_NODES || depth > MAX_DEPTH) return false;
      if (current === null || typeof current === "boolean") return true;
      if (typeof current === "string") return current.length <= MAX_STRING_LENGTH;
      if (typeof current === "number") {
        return Number.isSafeInteger(current) && !Object.is(current, -0);
      }
      if (typeof current !== "object" || seen.has(current)) return false;
      seen.add(current);
      if (Object.getOwnPropertySymbols(current).length !== 0) return false;
      if (Array.isArray(current)) {
        if (Object.getPrototypeOf(current) !== Array.prototype
          || current.length > MAX_ARRAY_LENGTH
          || Object.getOwnPropertyNames(current).length !== current.length + 1) {
          return false;
        }
        for (var index = 0; index < current.length; index += 1) {
          var arrayDescriptor = Object.getOwnPropertyDescriptor(current, String(index));
          if (!arrayDescriptor || !arrayDescriptor.enumerable
            || typeof arrayDescriptor.get === "function"
            || typeof arrayDescriptor.set === "function"
            || !visit(arrayDescriptor.value, depth + 1)) return false;
        }
        return true;
      }
      var prototype = Object.getPrototypeOf(current);
      if (prototype !== Object.prototype && prototype !== null) return false;
      var names = Object.getOwnPropertyNames(current);
      if (names.length > MAX_OBJECT_KEYS) return false;
      for (var nameIndex = 0; nameIndex < names.length; nameIndex += 1) {
        var name = names[nameIndex];
        if (name.length > 128 || name === "__proto__"
          || name === "prototype" || name === "constructor") return false;
        var descriptor = Object.getOwnPropertyDescriptor(current, name);
        if (!descriptor || !descriptor.enumerable
          || typeof descriptor.get === "function"
          || typeof descriptor.set === "function"
          || !visit(descriptor.value, depth + 1)) return false;
      }
      return true;
    }
    try {
      return visit(value, 0);
    } catch (_error) {
      return false;
    }
  }

  function canonicalEqual(first, second) {
    try {
      return strictCanonical.strictCanonicalStringify(first)
        === strictCanonical.strictCanonicalStringify(second);
    } catch (_error) {
      return false;
    }
  }

  function authorityExact(authority) {
    return exactKeys(authority, AUTHORITY_KEYS)
      && authority.descriptive_only === true
      && AUTHORITY_KEYS.filter(function (key) {
        return key !== "descriptive_only";
      }).every(function (key) {
        return authority[key] === false;
      });
  }

  function factsExact(facts, mode) {
    if (!exactKeys(facts, FACT_KEYS) || facts.bounded_projection !== true) return false;
    var expectedTrue = mode === "candidate"
      ? [
        "source_decision_exactly_verified", "bounded_projection",
        "structural_lineage_verified", "isolated_backend_test_candidate",
      ]
      : mode === "incomplete"
        ? ["source_decision_exactly_verified", "bounded_projection"]
        : ["bounded_projection"];
    return FACT_KEYS.every(function (key) {
      return facts[key] === expectedTrue.includes(key);
    });
  }

  function expectedStages(mode, reason) {
    if (mode === "unknown") {
      return [
        { axis: "SOURCE", state: "UNKNOWN", reason_code: reason },
        { axis: "GAP", state: "OPEN", reason_code: reason },
        { axis: "MATURITY", state: "UNKNOWN", reason_code: reason },
        {
          axis: "PERMISSION",
          state: "BLOCKED",
          reason_code: "CURRENT_AND_EXECUTION_PERMISSIONS_BLOCKED",
        },
      ];
    }
    var candidate = mode === "candidate";
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

  function sourceExact(source, mode) {
    if (!exactKeys(source, SOURCE_KEYS)) return false;
    return SOURCE_KEYS.every(function (key) {
      return mode === "unknown" ? source[key] === null : exactHash(source[key]);
    });
  }

  function inspectProjection(projection, expectedPresentationHash) {
    var rejected = {
      accepted: false,
      known: false,
      mode: "unknown",
      reason_code: "SOURCE_PRESENTATION_PROJECTION_NOT_EXACT",
    };
    try {
      if (!exactHash(expectedPresentationHash)
        || !validatePlainJson(projection)
        || !exactKeys(projection, TOP_LEVEL_KEYS)
        || projection.schema_version !== SOURCE_SCHEMA_VERSION
        || projection.static_fingerprint !== SOURCE_STATIC_FINGERPRINT
        || projection.display_tone !== "NEUTRAL"
        || !canonicalEqual(projection.stage_order, STAGE_ORDER)
        || !strictCanonical.verifySealedDocument(projection, "presentation_hash")
        || projection.presentation_hash !== expectedPresentationHash
        || !authorityExact(projection.authority)
        || !exactKeys(projection.summary, ["blocker_count", "component_count"])
        || !Array.isArray(projection.blockers)) return rejected;

      var mode = "unknown";
      var reason = null;
      if (projection.presentation_status === "UNMOUNTED_RESEARCH_EVIDENCE"
        && projection.display_state
          === "STRUCTURAL_LINEAGE_PRESENT_PERMISSION_BLOCKED") {
        mode = "candidate";
      } else if (projection.presentation_status === "UNMOUNTED_RESEARCH_EVIDENCE"
        && projection.display_state === "LINEAGE_INCOMPLETE_PERMISSION_BLOCKED") {
        mode = "incomplete";
      } else if (projection.presentation_status === "UNMOUNTED_UNKNOWN"
        && projection.display_state === "UNKNOWN"
        && projection.blockers.length === 1
        && UNKNOWN_REASONS.includes(projection.blockers[0])) {
        reason = projection.blockers[0];
      } else {
        return rejected;
      }
      var expectedBlockers = mode === "candidate"
        ? PENDING_CONDITIONS
        : mode === "incomplete"
          ? ["LINEAGE_BINDING_NOT_COMPLETE"]
          : [reason];
      var summaryExact = mode === "unknown"
        ? projection.summary.blocker_count === null
          && projection.summary.component_count === null
        : projection.summary.blocker_count === expectedBlockers.length
          && Number.isSafeInteger(projection.summary.component_count)
          && projection.summary.component_count >= 1;
      if (!summaryExact
        || !canonicalEqual(projection.blockers, expectedBlockers)
        || !factsExact(projection.facts, mode)
        || !sourceExact(projection.source, mode)
        || !canonicalEqual(projection.stages, expectedStages(mode, reason))) {
        return rejected;
      }
      return {
        accepted: true,
        known: mode !== "unknown",
        mode: mode,
        reason_code: mode === "unknown"
          ? reason
          : "LOCAL_STRUCTURAL_EVIDENCE_PRESENTED_PERMISSION_LOCKED",
      };
    } catch (_error) {
      return rejected;
    }
  }

  function outputAuthority() {
    return {
      current_admission_allowed: false,
      dom_mount_allowed: false,
      isolated_backend_test_allowed: false,
      backend_mount_allowed: false,
      runtime_asset_loading_allowed: false,
      writer_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    };
  }

  function nullSource() {
    return {
      presentation_hash: null,
      persistence_admission_decision_hash: null,
      lineage_binding_hash: null,
      lineage_bundle_hash: null,
      lineage_implementation_sha256: null,
    };
  }

  function buildWitnessStoragePersistenceAdmissionViewModelV1(
    sourceProjection,
    expectedSourcePresentationHash
  ) {
    var inspection = inspectProjection(
      sourceProjection,
      expectedSourcePresentationHash
    );
    var accepted = inspection.accepted;
    var known = inspection.known;
    var source = nullSource();
    var stages = expectedStages("unknown", inspection.reason_code);
    var blockers = [inspection.reason_code];
    var blockerCount = 1;
    var componentCount = null;
    var structural = false;
    var candidate = false;
    var presentationState = "UNKNOWN";
    if (accepted) {
      source = {
        presentation_hash: sourceProjection.presentation_hash,
        persistence_admission_decision_hash:
          sourceProjection.source.persistence_admission_decision_hash,
        lineage_binding_hash: sourceProjection.source.lineage_binding_hash,
        lineage_bundle_hash: sourceProjection.source.lineage_bundle_hash,
        lineage_implementation_sha256:
          sourceProjection.source.lineage_implementation_sha256,
      };
      stages = sourceProjection.stages.map(function (stage) {
        return { axis: stage.axis, state: stage.state, reason_code: stage.reason_code };
      });
      blockers = sourceProjection.blockers.slice();
      blockerCount = sourceProjection.summary.blocker_count;
      componentCount = sourceProjection.summary.component_count;
      structural = sourceProjection.facts.structural_lineage_verified;
      candidate = sourceProjection.facts.isolated_backend_test_candidate;
      presentationState = sourceProjection.display_state;
    }
    var body = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: known ? "BLOCKED" : "UNKNOWN",
      contract_state: known ? "LOCAL_RESEARCH_EVIDENCE" : "UNKNOWN",
      presentation_state: presentationState,
      reason_code: inspection.reason_code,
      tone: "NEUTRAL",
      stage_order: STAGE_ORDER.slice(),
      sections: stages,
      source: source,
      gap: { blocker_count: blockerCount, blocker_codes: blockers },
      maturity: {
        state: stages[2].state,
        structural_lineage_verified: structural,
        isolated_backend_test_candidate: candidate,
      },
      permission: {
        state: "BLOCKED",
        decision: "DO_NOT_MOUNT",
        current_admission_allowed: false,
        isolated_backend_test_allowed: false,
        backend_mount_allowed: false,
        writer_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
      },
      summary: { blocker_count: blockerCount, component_count: componentCount },
      facts: {
        source_projection_contract_verified: accepted,
        source_projection_known: known,
        bounded_view_model: true,
        raw_source_projection_embedded: false,
        raw_decision_document_embedded: false,
        raw_lineage_document_embedded: false,
        dom_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
      },
      authority: outputAuthority(),
    };
    return strictCanonical.sealDocument(body, "view_model_hash");
  }

  function verifyWitnessStoragePersistenceAdmissionViewModelV1(
    viewModel,
    sourceProjection,
    expectedSourcePresentationHash
  ) {
    if (!strictCanonical.verifySealedDocument(viewModel, "view_model_hash")) {
      return false;
    }
    return canonicalEqual(
      viewModel,
      buildWitnessStoragePersistenceAdmissionViewModelV1(
        sourceProjection,
        expectedSourcePresentationHash
      )
    );
  }

  return Object.freeze({
    INPUT_LIMITS: Object.freeze({
      max_array_length: MAX_ARRAY_LENGTH,
      max_depth: MAX_DEPTH,
      max_nodes: MAX_NODES,
      max_object_keys: MAX_OBJECT_KEYS,
      max_string_length: MAX_STRING_LENGTH,
    }),
    PENDING_CONDITIONS: Object.freeze(PENDING_CONDITIONS.slice()),
    SCHEMA_VERSION: SCHEMA_VERSION,
    SOURCE_SCHEMA_VERSION: SOURCE_SCHEMA_VERSION,
    SOURCE_STATIC_FINGERPRINT: SOURCE_STATIC_FINGERPRINT,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STAGE_ORDER: Object.freeze(STAGE_ORDER.slice()),
    buildWitnessStoragePersistenceAdmissionViewModelV1:
      buildWitnessStoragePersistenceAdmissionViewModelV1,
    verifyWitnessStoragePersistenceAdmissionViewModelV1:
      verifyWitnessStoragePersistenceAdmissionViewModelV1,
  });
});
