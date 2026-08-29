(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HakimiPortfolioRiskDownsideTailCardV6 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical
) {
  "use strict";

  if (
    !strictCanonical ||
    typeof strictCanonical.verifySealedDocument !== "function" ||
    typeof strictCanonical.isPlainRecord !== "function"
  ) {
    throw new Error("HakimiStrictCanonicalJsonV1 is required");
  }

  var CARD_SCHEMA_VERSION = "portfolio-risk-downside-tail-card-v6";
  var CARD_STATIC_FINGERPRINT =
    "20260823-portfolio-risk-downside-tail-card-v6-unmounted-lock-1";
  var PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v6";
  var PROJECTION_STATIC_FINGERPRINT =
    "20260823-envelope-first-http-candidate-v6-frontend-projection-lock-1";
  var PROJECTION_IMPLEMENTATION_SHA256 =
    "ec136f1cc713f443581f835116610c0210d0fe2faeb638ee815d93709e1566d6";
  var CANDIDATE_V6_IMPLEMENTATION_SHA256 =
    "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096";
  var STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
  var STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  var HTTP_CANDIDATE_BLOCKERS = Object.freeze([
    "HTTP_CANDIDATE_V6_UNREGISTERED",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
  ]);
  var UNKNOWN_LOCAL_BLOCKERS = Object.freeze([
    "adapter_v5_context_exact",
    "adapter_v5_exact_public_verification",
    "downside_tail_context_exact",
    "downside_tail_registration_exact",
    "downside_tail_evaluation_exact",
    "downside_tail_hashes_cross_bound",
    "downside_tail_source_observed",
    "trade_symbol_set_to_tail_identity_set_bound",
    "risk_direction_strictly_derived",
  ]);

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) {
      return value;
    }
    Object.keys(value).forEach(function (key) {
      deepFreeze(value[key]);
    });
    return Object.freeze(value);
  }

  function exactKeys(value, expected) {
    if (!strictCanonical.isPlainRecord(value)) {
      return false;
    }
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return (
      actual.length === wanted.length &&
      actual.every(function (key, index) {
        return key === wanted[index];
      })
    );
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactBooleanMap(actual, expected) {
    return (
      exactKeys(actual, Object.keys(expected)) &&
      Object.keys(expected).every(function (key) {
        return actual[key] === expected[key];
      })
    );
  }

  function projectionAuthority() {
    return {
      research_only: true,
      presentation_only: true,
      frontend_projection_only: true,
      presentation_consumer_activation_allowed: false,
      presentation_mount_allowed: false,
      formal_registry_activation_allowed: false,
      current_admission_allowed: false,
      current_pointer_written: false,
      runtime_gate_activation_allowed: false,
      writer_allowed: false,
      paper_authorized: false,
      live_order_allowed: false,
    };
  }

  function verifyPortfolioRiskProjectionSealV6(projection) {
    return (
      strictCanonical.isPlainRecord(projection) &&
      projection.schema_version === PROJECTION_SCHEMA_VERSION &&
      projection.static_fingerprint === PROJECTION_STATIC_FINGERPRINT &&
      strictCanonical.verifySealedDocument(projection, "projection_hash") ===
        true
    );
  }

  function exactStringArray(actual, expected) {
    return (
      Array.isArray(actual) &&
      actual.length === expected.length &&
      actual.every(function (value, index) {
        return value === expected[index];
      })
    );
  }

  function validUniqueSubset(actual, allowed) {
    if (!Array.isArray(actual)) {
      return false;
    }
    var seen = Object.create(null);
    return actual.every(function (value) {
      if (
        typeof value !== "string" ||
        allowed.indexOf(value) === -1 ||
        seen[value]
      ) {
        return false;
      }
      seen[value] = true;
      return true;
    });
  }

  function exactStage(stage, axis, state, detail) {
    return (
      exactKeys(stage, ["axis", "state", "detail"]) &&
      stage.axis === axis &&
      stage.state === state &&
      stage.detail === detail
    );
  }

  function validStages(stages, source, localDecision) {
    if (!Array.isArray(stages) || stages.length !== STAGE_ORDER.length) {
      return false;
    }
    var known = source.state === "OBSERVED";
    var sourceDetailValid = known
      ? stages[0].detail ===
        "EXACT_ADAPTER_V6_AND_DOWNSIDE_TAIL_SOURCE_BOUND"
      : ["EXACT_ADAPTER_V6_WITH_UNKNOWN_JOINT_SOURCE", "UNKNOWN"].indexOf(
          stages[0].detail
        ) !== -1;
    var gapState = known
      ? localDecision.status === "PASS"
        ? "PRESENT"
        : "BLOCKED"
      : "UNKNOWN";
    var gapDetail = known
      ? localDecision.status === "PASS"
        ? "HTTP_REGISTRATION_CONSUMER_AND_CURRENT_GAPS"
        : "LOCAL_RESEARCH_GATE_BLOCKED"
      : "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN";
    return (
      exactStage(stages[0], "SOURCE", source.state, stages[0].detail) &&
      sourceDetailValid &&
      exactStage(stages[1], "GAP", gapState, gapDetail) &&
      exactStage(
        stages[2],
        "MATURITY",
        "CANDIDATE_ONLY",
        "UNMOUNTED_HTTP_CANDIDATE_V6"
      ) &&
      exactStage(
        stages[3],
        "PERMISSION",
        "UNAUTHORIZED",
        "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY"
      )
    );
  }

  function validTailDecision(localDecision) {
    return (
      (localDecision.downside_tail_gate_decision === "PASS" &&
        localDecision.downside_tail_gate_reason ===
          "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP") ||
      (localDecision.downside_tail_gate_decision === "BLOCK" &&
        localDecision.downside_tail_gate_reason ===
          "DOWNSIDE_TAIL_COUPLING_DETECTED")
    );
  }

  function validDecisionContract(source, localDecision, gaps) {
    if (source.state === "UNKNOWN") {
      return (
        localDecision.status === "UNKNOWN" &&
        localDecision.decision === "UNKNOWN" &&
        localDecision.adapter_v5_status === "UNKNOWN" &&
        localDecision.downside_tail_source_state === "UNKNOWN" &&
        localDecision.downside_tail_gate_decision === "UNKNOWN" &&
        localDecision.downside_tail_gate_reason === "UNKNOWN" &&
        localDecision.risk_increasing === null &&
        validUniqueSubset(gaps.local_blockers, UNKNOWN_LOCAL_BLOCKERS) &&
        exactStringArray(gaps.http_candidate_blockers, HTTP_CANDIDATE_BLOCKERS) &&
        exactStringArray(
          gaps.candidate_blockers,
          HTTP_CANDIDATE_BLOCKERS.concat([
            "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN",
          ])
        )
      );
    }
    if (
      source.state !== "OBSERVED" ||
      localDecision.downside_tail_source_state !== "OBSERVED" ||
      typeof localDecision.risk_increasing !== "boolean" ||
      !validTailDecision(localDecision) ||
      !exactStringArray(
        gaps.http_candidate_blockers,
        HTTP_CANDIDATE_BLOCKERS
      )
    ) {
      return false;
    }
    if (localDecision.status === "PASS") {
      return (
        localDecision.decision ===
          "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE" &&
        localDecision.adapter_v5_status === "PASS" &&
        localDecision.downside_tail_gate_decision === "PASS" &&
        exactStringArray(gaps.local_blockers, []) &&
        exactStringArray(gaps.candidate_blockers, HTTP_CANDIDATE_BLOCKERS)
      );
    }
    if (localDecision.status !== "BLOCK") {
      return false;
    }
    var expectedLocalBlocker = null;
    if (
      localDecision.decision === "BLOCK_DOWNSIDE_TAIL_COUPLING" &&
      localDecision.adapter_v5_status === "PASS" &&
      localDecision.downside_tail_gate_decision === "BLOCK"
    ) {
      expectedLocalBlocker = "downside_tail_coupling_detected";
    } else if (
      localDecision.decision === "BLOCK_ADAPTER_V5_COMPONENT" &&
      localDecision.adapter_v5_status === "BLOCK"
    ) {
      expectedLocalBlocker = "adapter_v5_component_block";
    } else if (
      localDecision.decision === "BLOCK_ADAPTER_V5_STATUS_UNKNOWN" &&
      localDecision.adapter_v5_status === "UNKNOWN"
    ) {
      expectedLocalBlocker = "adapter_v5_status_unknown";
    }
    return (
      expectedLocalBlocker !== null &&
      exactStringArray(gaps.local_blockers, [expectedLocalBlocker]) &&
      exactStringArray(
        gaps.candidate_blockers,
        HTTP_CANDIDATE_BLOCKERS.concat(["LOCAL_RESEARCH_GATE_BLOCKED"])
      )
    );
  }

  function validProjection(projection) {
    if (
      !verifyPortfolioRiskProjectionSealV6(projection) ||
      !exactKeys(projection, [
        "schema_version",
        "static_fingerprint",
        "status",
        "decision",
        "axis_order",
        "source",
        "local_decision",
        "gaps",
        "stages",
        "facts",
        "authority",
        "projection_hash",
      ])
    ) {
      return false;
    }

    var source = projection.source;
    var localDecision = projection.local_decision;
    var gaps = projection.gaps;
    var facts = projection.facts;
    if (
      !exactKeys(source, [
        "state",
        "candidate_v6_schema_version",
        "candidate_v6_static_fingerprint",
        "candidate_v6_response_hash",
        "candidate_v6_implementation_sha256",
        "candidate_state",
        "presentation_envelope_v1_hash",
        "adapter_v6_hash",
        "strict_canonical_implementation_sha256",
      ]) ||
      !exactKeys(localDecision, [
        "status",
        "decision",
        "adapter_v5_status",
        "downside_tail_source_state",
        "downside_tail_gate_decision",
        "downside_tail_gate_reason",
        "risk_increasing",
      ]) ||
      !exactKeys(gaps, [
        "local_blocker_count",
        "local_blockers",
        "http_candidate_blocker_count",
        "http_candidate_blockers",
        "candidate_blockers",
      ]) ||
      !exactKeys(facts, [
        "candidate_v6_exactly_verified",
        "presentation_envelope_v1_bound",
        "adapter_v6_exactly_verified",
        "joint_local_research_source_known",
        "trade_symbol_set_tail_identity_set_cross_bound",
        "downside_tail_block_override_visible",
        "risk_reduction_joint_exemption_implemented",
        "projection_only",
        "source_document_embedded",
        "verification_context_embedded",
        "positions_embedded",
        "aligned_observations_embedded",
        "pair_results_embedded",
        "runtime_consumer_bound",
        "ui_mounted",
        "profitability_proven",
      ])
    ) {
      return false;
    }

    return (
      projection.status === "BLOCK" &&
      projection.decision ===
        "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED" &&
      Array.isArray(projection.axis_order) &&
      projection.axis_order.length === STAGE_ORDER.length &&
      projection.axis_order.every(function (axis, index) {
        return axis === STAGE_ORDER[index];
      }) &&
      source.candidate_v6_schema_version ===
        "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v6" &&
      source.candidate_v6_static_fingerprint ===
        "20260823-adapter-v6-envelope-first-http-unregistered-candidate-1" &&
      source.candidate_v6_implementation_sha256 ===
        CANDIDATE_V6_IMPLEMENTATION_SHA256 &&
      source.candidate_state === "KNOWN_BLOCKED" &&
      source.strict_canonical_implementation_sha256 ===
        STRICT_CANONICAL_IMPLEMENTATION_SHA256 &&
      isHash(source.candidate_v6_response_hash) &&
      isHash(source.presentation_envelope_v1_hash) &&
      (facts.adapter_v6_exactly_verified === true
        ? isHash(source.adapter_v6_hash)
        : source.adapter_v6_hash === null) &&
      validDecisionContract(source, localDecision, gaps) &&
      Number.isInteger(gaps.local_blocker_count) &&
      gaps.local_blocker_count >= 0 &&
      Array.isArray(gaps.local_blockers) &&
      gaps.local_blocker_count === gaps.local_blockers.length &&
      Number.isInteger(gaps.http_candidate_blocker_count) &&
      gaps.http_candidate_blocker_count >= 0 &&
      Array.isArray(gaps.http_candidate_blockers) &&
      gaps.http_candidate_blocker_count ===
        gaps.http_candidate_blockers.length &&
      Array.isArray(gaps.candidate_blockers) &&
      gaps.http_candidate_blockers.indexOf(
        "HTTP_CANDIDATE_V6_UNREGISTERED"
      ) !== -1 &&
      validStages(projection.stages, source, localDecision) &&
      facts.candidate_v6_exactly_verified === true &&
      facts.presentation_envelope_v1_bound === true &&
      typeof facts.adapter_v6_exactly_verified === "boolean" &&
      typeof facts.joint_local_research_source_known === "boolean" &&
      facts.joint_local_research_source_known ===
        (source.state === "OBSERVED") &&
      facts.trade_symbol_set_tail_identity_set_cross_bound ===
        (source.state === "OBSERVED") &&
      (source.state !== "OBSERVED" ||
        facts.adapter_v6_exactly_verified === true) &&
      facts.downside_tail_block_override_visible === true &&
      facts.risk_reduction_joint_exemption_implemented === false &&
      facts.projection_only === true &&
      facts.source_document_embedded === false &&
      facts.verification_context_embedded === false &&
      facts.positions_embedded === false &&
      facts.aligned_observations_embedded === false &&
      facts.pair_results_embedded === false &&
      facts.runtime_consumer_bound === false &&
      facts.ui_mounted === false &&
      facts.profitability_proven === false &&
      exactBooleanMap(projection.authority, projectionAuthority())
    );
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) : "unknown";
  }

  function dedupe(values) {
    var seen = Object.create(null);
    return values.filter(function (value) {
      if (typeof value !== "string" || seen[value]) {
        return false;
      }
      seen[value] = true;
      return true;
    });
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      source_state: "UNKNOWN",
      tone: "unknown",
      kicker: "CORRELATION CLUSTER / DOWNSIDE TAIL",
      title: "Related-risk evidence is unavailable",
      summary:
        "The projection contract is unknown. No portfolio or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN",
      projection_hash_short: "unknown",
      metrics: [],
      tail_risk: {
        source_state: "UNKNOWN",
        decision: "UNKNOWN",
        reason: "UNKNOWN",
        risk_direction: "UNKNOWN",
        exemption: "NOT IMPLEMENTED",
      },
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail:
            axis === "PERMISSION"
              ? "NO_PERMISSION_CAN_BE_INFERRED"
              : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note:
        "Research display only. Route, runtime, paper, and live authority remain unavailable.",
    });
  }

  function buildPortfolioRiskDownsideTailViewModelV6(projection) {
    if (!validProjection(projection)) {
      return unknownViewModel();
    }

    var local = projection.local_decision;
    var sourceKnown =
      projection.facts.joint_local_research_source_known === true;
    var tailBlocked =
      sourceKnown && local.downside_tail_gate_decision === "BLOCK";
    var localBlocked = sourceKnown && local.status === "BLOCK";
    var tone = !sourceKnown
      ? "unknown"
      : tailBlocked
        ? "critical"
        : localBlocked
          ? "gap"
          : "bounded";
    var title = !sourceKnown
      ? "Joint source remains unknown"
      : tailBlocked
        ? "Downside tails move together"
        : localBlocked
          ? "The joint risk gate remains blocked"
          : "Correlation and tail checks are locally clear";
    var summary = !sourceKnown
      ? "The candidate is exact, but its joint research source is unknown. The fail-closed boundary remains active."
      : tailBlocked
        ? "Correlated names share adverse tail events and remain one constrained risk unit."
        : localBlocked
          ? "At least one local research gate is blocked. Correlated exposure remains constrained."
          : "Linear, multi-window, and downside-tail checks are locally consistent. Governance and permission gaps remain.";
    var statusLabel = !sourceKnown
      ? "SOURCE UNKNOWN"
      : tailBlocked
        ? "TAIL COUPLING BLOCK"
        : localBlocked
          ? "LOCAL GATE BLOCK"
          : "LOCAL CHECKS CLEAR";
    var riskDirection =
      local.risk_increasing === true
        ? "INCREASING"
        : local.risk_increasing === false
          ? "REDUCING"
          : "UNKNOWN";
    var blockers = dedupe(
      projection.gaps.local_blockers
        .concat(projection.gaps.http_candidate_blockers)
        .concat(projection.gaps.candidate_blockers)
    );

    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_BLOCKED",
      source_state: projection.source.state,
      tone: tone,
      kicker: "CORRELATION CLUSTER / DOWNSIDE TAIL",
      title: title,
      summary: summary,
      status_label: statusLabel,
      projection_hash_short: shortHash(projection.projection_hash),
      metrics: [
        {
          label: "Local gate",
          value: local.status,
          detail: "Research decision only",
        },
        {
          label: "Tail coupling",
          value: local.downside_tail_gate_decision,
          detail: local.downside_tail_gate_reason,
        },
        {
          label: "Risk direction",
          value: riskDirection,
          detail: "No joint reduction exemption is implemented",
        },
        {
          label: "Open gaps",
          value: String(blockers.length),
          detail: "Local and governance blockers",
        },
        {
          label: "Source",
          value: shortHash(projection.source.candidate_v6_response_hash),
          detail: "Candidate-v6 response hash",
        },
      ],
      tail_risk: {
        source_state: local.downside_tail_source_state,
        decision: local.downside_tail_gate_decision,
        reason: local.downside_tail_gate_reason,
        risk_direction: riskDirection,
        exemption: "NOT IMPLEMENTED",
      },
      stages: projection.stages.map(function (stage) {
        return {
          axis: stage.axis,
          state: stage.state,
          detail: stage.detail,
        };
      }),
      blockers: blockers,
      permission_note:
        "Research display only. Route, runtime, paper, and live authority remain unavailable.",
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderPortfolioRiskDownsideTailCardV6(projection) {
    var view = buildPortfolioRiskDownsideTailViewModelV6(projection);
    var metrics = view.metrics
      .map(function (metric) {
        return (
          '<li class="hakimi-risk-tail-card-v6__metric">' +
          '<span class="hakimi-risk-tail-card-v6__metric-label">' +
          escapeHtml(metric.label) +
          "</span>" +
          '<strong class="hakimi-risk-tail-card-v6__metric-value">' +
          escapeHtml(metric.value) +
          "</strong>" +
          '<small class="hakimi-risk-tail-card-v6__metric-detail">' +
          escapeHtml(metric.detail) +
          "</small></li>"
        );
      })
      .join("");
    var stages = view.stages
      .map(function (stage, index) {
        return (
          '<li class="hakimi-risk-tail-card-v6__stage">' +
          '<span class="hakimi-risk-tail-card-v6__stage-index">0' +
          String(index + 1) +
          "</span>" +
          '<span class="hakimi-risk-tail-card-v6__stage-axis">' +
          escapeHtml(stage.axis) +
          "</span>" +
          '<strong class="hakimi-risk-tail-card-v6__stage-state">' +
          escapeHtml(stage.state) +
          "</strong>" +
          '<small class="hakimi-risk-tail-card-v6__stage-detail">' +
          escapeHtml(stage.detail) +
          "</small></li>"
        );
      })
      .join("");
    var blockers = view.blockers
      .map(function (blocker) {
        return (
          '<li class="hakimi-risk-tail-card-v6__blocker">' +
          escapeHtml(blocker) +
          "</li>"
        );
      })
      .join("");

    return (
      '<article class="hakimi-risk-tail-card-v6" data-tone="' +
      escapeHtml(view.tone) +
      '" aria-label="Portfolio correlation and downside-tail evidence">' +
      '<header class="hakimi-risk-tail-card-v6__header">' +
      '<div><p class="hakimi-risk-tail-card-v6__kicker">' +
      escapeHtml(view.kicker) +
      '</p><h2 class="hakimi-risk-tail-card-v6__title">' +
      escapeHtml(view.title) +
      "</h2></div>" +
      '<span class="hakimi-risk-tail-card-v6__status">' +
      escapeHtml(view.status_label) +
      "</span></header>" +
      '<p class="hakimi-risk-tail-card-v6__summary">' +
      escapeHtml(view.summary) +
      "</p>" +
      '<ul class="hakimi-risk-tail-card-v6__metrics">' +
      metrics +
      "</ul>" +
      '<ol class="hakimi-risk-tail-card-v6__stages">' +
      stages +
      "</ol>" +
      (blockers
        ? '<section class="hakimi-risk-tail-card-v6__gaps"><h3>Open gaps</h3><ul>' +
          blockers +
          "</ul></section>"
        : "") +
      '<footer class="hakimi-risk-tail-card-v6__footer"><span>projection ' +
      escapeHtml(view.projection_hash_short) +
      "</span><span>" +
      escapeHtml(view.permission_note) +
      "</span></footer></article>"
    );
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT: CARD_STATIC_FINGERPRINT,
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA_VERSION,
    PROJECTION_STATIC_FINGERPRINT: PROJECTION_STATIC_FINGERPRINT,
    PROJECTION_IMPLEMENTATION_SHA256: PROJECTION_IMPLEMENTATION_SHA256,
    STAGE_ORDER: STAGE_ORDER,
    verifyPortfolioRiskProjectionSealV6:
      verifyPortfolioRiskProjectionSealV6,
    buildPortfolioRiskDownsideTailViewModelV6:
      buildPortfolioRiskDownsideTailViewModelV6,
    renderPortfolioRiskDownsideTailCardV6:
      renderPortfolioRiskDownsideTailCardV6,
  });
});
