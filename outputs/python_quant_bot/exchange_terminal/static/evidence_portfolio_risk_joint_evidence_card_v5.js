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
    root.HakimiPortfolioRiskJointEvidenceCardV5 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  "use strict";

  if (
    !strictCanonical ||
    typeof strictCanonical.verifySealedDocument !== "function" ||
    typeof strictCanonical.isPlainRecord !== "function"
  ) {
    throw new Error("HakimiStrictCanonicalJsonV1 is required");
  }

  var CARD_SCHEMA_VERSION = "portfolio-risk-joint-evidence-card-v5";
  var CARD_STATIC_FINGERPRINT =
    "20260823-portfolio-risk-joint-evidence-card-v5-projection-lock-1";
  var PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v5";
  var PROJECTION_STATIC_FINGERPRINT =
    "20260823-http-candidate-v5-frontend-projection-lock-1";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

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

  function projectionAuthority() {
    return {
      research_only: true,
      presentation_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false,
    };
  }

  function exactBooleanMap(actual, expected) {
    return (
      exactKeys(actual, Object.keys(expected)) &&
      Object.keys(expected).every(function (key) {
        return actual[key] === expected[key];
      })
    );
  }

  function verifyPortfolioRiskProjectionSealV5(projection) {
    return (
      strictCanonical.isPlainRecord(projection) &&
      projection.schema_version === PROJECTION_SCHEMA_VERSION &&
      projection.static_fingerprint === PROJECTION_STATIC_FINGERPRINT &&
      strictCanonical.verifySealedDocument(projection, "projection_hash") === true
    );
  }

  function validStages(stages) {
    return (
      Array.isArray(stages) &&
      stages.length === STAGE_ORDER.length &&
      stages.every(function (stage, index) {
        return (
          exactKeys(stage, ["key", "state", "detail"]) &&
          stage.key === STAGE_ORDER[index] &&
          typeof stage.state === "string" &&
          typeof stage.detail === "string"
        );
      }) &&
      stages[3].state === "UNAUTHORIZED"
    );
  }

  function validProjection(projection) {
    if (
      !verifyPortfolioRiskProjectionSealV5(projection) ||
      !exactKeys(projection, [
        "schema_version",
        "static_fingerprint",
        "status",
        "decision",
        "source",
        "local_decision",
        "joint_risk",
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
    var jointRisk = projection.joint_risk;
    var gaps = projection.gaps;
    var facts = projection.facts;
    var jointPassed = localDecision && localDecision.joint_risk_gate_passed === true;

    return (
      projection.status === "BLOCK" &&
      projection.decision ===
        "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED" &&
      exactKeys(source, [
        "candidate_v5_schema_version",
        "candidate_v5_static_fingerprint",
        "candidate_v5_response_hash",
        "candidate_v5_exactly_verified",
        "candidate_v5_implementation_sha256",
        "candidate_state",
        "source_preregistration_hash",
        "portfolio_risk_adapter_v5_hash",
      ]) &&
      source.candidate_v5_exactly_verified === true &&
      source.candidate_state === "KNOWN_BLOCKED" &&
      isHash(source.candidate_v5_response_hash) &&
      isHash(source.source_preregistration_hash) &&
      isHash(source.portfolio_risk_adapter_v5_hash) &&
      exactKeys(localDecision, [
        "status",
        "decision",
        "joint_risk_gate_passed",
        "blockers",
      ]) &&
      ["PASS", "BLOCK", "UNKNOWN"].indexOf(localDecision.status) !== -1 &&
      typeof localDecision.decision === "string" &&
      Array.isArray(localDecision.blockers) &&
      exactKeys(jointRisk, [
        "assessment",
        "multi_window_stability_gate_verified",
        "anchor_window_budget_and_context_bound",
        "trade_identity_cross_bound",
        "anchor_window_id",
        "trade_identity_hash",
      ]) &&
      jointRisk.assessment ===
        (jointPassed
          ? "LOCAL_JOINT_RESEARCH_GATE_PASSED"
          : "LOCAL_JOINT_RESEARCH_GATE_BLOCKED") &&
      typeof jointRisk.anchor_window_id === "string" &&
      isHash(jointRisk.trade_identity_hash) &&
      exactKeys(gaps, [
        "remaining_blocker_count",
        "remaining_blockers",
        "candidate_blockers",
      ]) &&
      Number.isInteger(gaps.remaining_blocker_count) &&
      gaps.remaining_blocker_count >= 0 &&
      Array.isArray(gaps.remaining_blockers) &&
      Array.isArray(gaps.candidate_blockers) &&
      validStages(projection.stages) &&
      exactKeys(facts, [
        "projection_only",
        "candidate_v5_exactly_verified",
        "http_candidate_to_projection_bound",
        "source_document_embedded",
        "verification_context_embedded",
        "positions_embedded",
        "correlation_matrices_embedded",
        "profitability_proven",
        "runtime_consumer_bound",
        "ui_mounted",
      ]) &&
      facts.projection_only === true &&
      facts.candidate_v5_exactly_verified === true &&
      facts.http_candidate_to_projection_bound === true &&
      facts.source_document_embedded === false &&
      facts.verification_context_embedded === false &&
      facts.positions_embedded === false &&
      facts.correlation_matrices_embedded === false &&
      facts.profitability_proven === false &&
      facts.runtime_consumer_bound === false &&
      facts.ui_mounted === false &&
      exactBooleanMap(projection.authority, projectionAuthority())
    );
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) : "unknown";
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "PORTFOLIO RISK / JOINT EVIDENCE",
      title: "Joint-risk evidence is unavailable",
      summary: "Projection contract is unknown. No permission can be inferred.",
      status_label: "SOURCE UNKNOWN",
      projection_hash_short: "unknown",
      metrics: [],
      joint_risk: {
        assessment: "UNKNOWN",
        anchor_window_id: "unknown",
        trade_identity_hash_short: "unknown",
      },
      stages: STAGE_ORDER.map(function (key) {
        return {
          key: key,
          state: key === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail:
            key === "PERMISSION"
              ? "NO_PERMISSION_CAN_BE_INFERRED"
              : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note:
        "Research display only. Runtime, paper, and live authority remain unavailable.",
    });
  }

  function buildPortfolioRiskJointEvidenceViewModelV5(projection) {
    if (!validProjection(projection)) {
      return unknownViewModel();
    }

    var jointPassed = projection.local_decision.joint_risk_gate_passed === true;
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_BLOCKED",
      tone: jointPassed ? "bounded" : "gap",
      kicker: "CORRELATION CLUSTER / MULTI-WINDOW",
      title: jointPassed
        ? "One correlated budget, checked across windows"
        : "The joint correlation gate remains blocked",
      summary: jointPassed
        ? "The local joint research gate is internally consistent. External, transport, and permission gaps remain."
        : "The local joint research gate is blocked. Correlated names remain one constrained risk unit.",
      status_label: jointPassed ? "LOCAL GATE PASS" : "LOCAL GATE BLOCK",
      projection_hash_short: shortHash(projection.projection_hash),
      metrics: [
        {
          label: "Joint gate",
          value: jointPassed ? "PASS" : "BLOCK",
          detail: "Local research decision only",
        },
        {
          label: "Anchor window",
          value: projection.joint_risk.anchor_window_id,
          detail: "Cross-bound budget and context",
        },
        {
          label: "Remaining blockers",
          value: String(projection.gaps.remaining_blocker_count),
          detail: "External and activation gaps",
        },
        {
          label: "Source",
          value: shortHash(projection.source.candidate_v5_response_hash),
          detail: "Candidate-v5 response hash",
        },
      ],
      joint_risk: {
        assessment: projection.joint_risk.assessment,
        anchor_window_id: projection.joint_risk.anchor_window_id,
        trade_identity_hash_short: shortHash(
          projection.joint_risk.trade_identity_hash
        ),
      },
      stages: projection.stages.map(function (stage) {
        return {
          key: stage.key,
          state: stage.state,
          detail: stage.detail,
        };
      }),
      blockers: projection.gaps.remaining_blockers.slice(),
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

  function renderPortfolioRiskJointEvidenceCardV5(projection) {
    var view = buildPortfolioRiskJointEvidenceViewModelV5(projection);
    var metrics = view.metrics
      .map(function (metric) {
        return (
          '<li class="hakimi-joint-risk-card-v5__metric">' +
          '<span class="hakimi-joint-risk-card-v5__metric-label">' +
          escapeHtml(metric.label) +
          "</span>" +
          '<strong class="hakimi-joint-risk-card-v5__metric-value">' +
          escapeHtml(metric.value) +
          "</strong>" +
          '<small class="hakimi-joint-risk-card-v5__metric-detail">' +
          escapeHtml(metric.detail) +
          "</small></li>"
        );
      })
      .join("");
    var stages = view.stages
      .map(function (stage, index) {
        return (
          '<li class="hakimi-joint-risk-card-v5__stage">' +
          '<span class="hakimi-joint-risk-card-v5__stage-index">0' +
          String(index + 1) +
          "</span>" +
          '<span class="hakimi-joint-risk-card-v5__stage-key">' +
          escapeHtml(stage.key) +
          "</span>" +
          '<strong class="hakimi-joint-risk-card-v5__stage-state">' +
          escapeHtml(stage.state) +
          "</strong>" +
          '<small class="hakimi-joint-risk-card-v5__stage-detail">' +
          escapeHtml(stage.detail) +
          "</small></li>"
        );
      })
      .join("");
    var blockers = view.blockers
      .map(function (blocker) {
        return (
          '<li class="hakimi-joint-risk-card-v5__blocker">' +
          escapeHtml(blocker) +
          "</li>"
        );
      })
      .join("");

    return (
      '<article class="hakimi-joint-risk-card-v5" data-tone="' +
      escapeHtml(view.tone) +
      '" aria-label="Portfolio risk joint evidence">' +
      '<header class="hakimi-joint-risk-card-v5__header">' +
      '<div><p class="hakimi-joint-risk-card-v5__kicker">' +
      escapeHtml(view.kicker) +
      '</p><h2 class="hakimi-joint-risk-card-v5__title">' +
      escapeHtml(view.title) +
      "</h2></div>" +
      '<span class="hakimi-joint-risk-card-v5__status">' +
      escapeHtml(view.status_label) +
      "</span></header>" +
      '<p class="hakimi-joint-risk-card-v5__summary">' +
      escapeHtml(view.summary) +
      "</p>" +
      '<ul class="hakimi-joint-risk-card-v5__metrics">' +
      metrics +
      "</ul>" +
      '<ol class="hakimi-joint-risk-card-v5__stages">' +
      stages +
      "</ol>" +
      (blockers
        ? '<section class="hakimi-joint-risk-card-v5__gaps"><h3>Open gaps</h3><ul>' +
          blockers +
          "</ul></section>"
        : "") +
      '<footer class="hakimi-joint-risk-card-v5__footer"><span>projection ' +
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
    STAGE_ORDER: STAGE_ORDER,
    verifyPortfolioRiskProjectionSealV5: verifyPortfolioRiskProjectionSealV5,
    buildPortfolioRiskJointEvidenceViewModelV5:
      buildPortfolioRiskJointEvidenceViewModelV5,
    renderPortfolioRiskJointEvidenceCardV5:
      renderPortfolioRiskJointEvidenceCardV5,
  });
});
