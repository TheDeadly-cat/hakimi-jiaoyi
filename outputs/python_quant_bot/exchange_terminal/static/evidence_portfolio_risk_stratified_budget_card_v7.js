(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskStratifiedBudgetCardV7 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  "use strict";

  if (!strictCanonical || typeof strictCanonical.verifySealedDocument !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var RESPONSE_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-http-candidate-response-v7";
  var RESPONSE_STATIC_FINGERPRINT =
    "20260823-stratified-budget-http-candidate-v7-unmounted-lock-1";
  var PAYLOAD_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-http-payload-v7";
  var CARD_SCHEMA_VERSION = "portfolio-risk-stratified-budget-card-v7";
  var CARD_STATIC_FINGERPRINT =
    "20260823-portfolio-risk-stratified-budget-card-v7-unmounted-lock-1";
  var PRESENTATION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-v7";
  var PRESENTATION_STATIC_FINGERPRINT =
    "20260823-stratified-portfolio-risk-presentation-v7-lock-1";
  var PRESENTATION_IMPLEMENTATION_SHA256 =
    "27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38";
  var STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var HTTP_CANDIDATE_BLOCKERS = Object.freeze([
    "HTTP_CANDIDATE_V7_UNREGISTERED",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
  ]);

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.keys(value).forEach(function (key) { deepFreeze(value[key]); });
    return Object.freeze(value);
  }

  function exactKeys(value, expected) {
    if (!strictCanonical.isPlainRecord(value)) return false;
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every(function (key, index) {
      return key === wanted[index];
    });
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function numericTextOrNull(value) {
    return value === null || (
      typeof value === "string" && /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$/.test(value)
    );
  }

  function exactStringArray(value) {
    return Array.isArray(value) && value.every(function (item) {
      return typeof item === "string";
    });
  }

  function authorityLocked(value) {
    return exactKeys(value, [
      "consumer_activation_allowed",
      "current_admission_allowed",
      "descriptive_only",
      "live_order_allowed",
      "paper_authorized",
      "presentation_mount_allowed",
      "route_registration_allowed",
      "runtime_gate_activation_allowed",
      "writer_allowed",
    ]) && value.descriptive_only === true && [
      "consumer_activation_allowed",
      "current_admission_allowed",
      "live_order_allowed",
      "paper_authorized",
      "presentation_mount_allowed",
      "route_registration_allowed",
      "runtime_gate_activation_allowed",
      "writer_allowed",
    ].every(function (key) { return value[key] === false; });
  }

  function validDimension(value) {
    return exactKeys(value, [
      "active_stratum_count",
      "dimension_id",
      "diversification_status",
      "dominant_stratum_id",
      "dominant_stratum_share_of_active_gross_pct",
      "gross_limit_status",
      "maximum_stratum_gross_pct",
      "over_limit_stratum_count",
      "status",
      "weighted_effective_strata_count",
    ]) && Number.isInteger(value.active_stratum_count) && value.active_stratum_count >= 0
      && Number.isInteger(value.over_limit_stratum_count) && value.over_limit_stratum_count >= 0
      && typeof value.dimension_id === "string" && value.dimension_id.length > 0
      && typeof value.dominant_stratum_id === "string" && value.dominant_stratum_id.length > 0
      && ["PASS", "BLOCK", "NOT_APPLICABLE"].indexOf(value.diversification_status) !== -1
      && ["PASS", "BLOCK"].indexOf(value.gross_limit_status) !== -1
      && ["PASS", "BLOCK"].indexOf(value.status) !== -1
      && numericTextOrNull(value.dominant_stratum_share_of_active_gross_pct)
      && numericTextOrNull(value.maximum_stratum_gross_pct)
      && numericTextOrNull(value.weighted_effective_strata_count);
  }

  function validStages(stages) {
    return Array.isArray(stages) && stages.length === STAGE_ORDER.length
      && stages.every(function (stage, index) {
        return exactKeys(stage, ["axis", "detail", "state"])
          && stage.axis === STAGE_ORDER[index]
          && typeof stage.detail === "string"
          && typeof stage.state === "string";
      })
      && stages[2].state === "CANDIDATE_ONLY"
      && stages[2].detail === "UNMOUNTED_HTTP_CANDIDATE_V7"
      && stages[3].state === "UNAUTHORIZED"
      && stages[3].detail === "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY";
  }

  function validPayload(payload) {
    if (!strictCanonical.verifySealedDocument(payload, "payload_hash") || !exactKeys(payload, [
      "authority", "decision", "facts", "gaps", "local_decision", "payload_hash",
      "risk_summary", "schema_version", "source", "stages", "status",
    ])) return false;

    var local = payload.local_decision;
    var risk = payload.risk_summary;
    var gaps = payload.gaps;
    var facts = payload.facts;
    return payload.schema_version === PAYLOAD_SCHEMA_VERSION
      && payload.status === "BLOCK"
      && payload.decision === "EXACT_PRESENTATION_V7_PROJECTED_AUTHORITY_UNCHANGED"
      && exactKeys(payload.source, ["presentation_v7_hash", "state"])
      && payload.source.state === "EXACT_V6_AND_BUDGET_V3"
      && isHash(payload.source.presentation_v7_hash)
      && exactKeys(local, [
        "joint_decision", "joint_status", "portfolio_risk_v6_decision",
        "portfolio_risk_v6_status", "stratified_budget_decision", "stratified_budget_status",
      ])
      && ["PASS", "BLOCK"].indexOf(local.joint_status) !== -1
      && ["PASS", "BLOCK"].indexOf(local.portfolio_risk_v6_status) !== -1
      && ["PASS", "BLOCK"].indexOf(local.stratified_budget_status) !== -1
      && exactKeys(risk, [
        "active_dimension_count", "conservative_weighted_effective_strata_count",
        "dimension_results", "maximum_active_stratum_gross_pct", "total_active_gross_pct",
        "v2_weighted_effective_cluster_count", "weighted_diversification_gate_applied",
      ])
      && Number.isInteger(risk.active_dimension_count) && risk.active_dimension_count >= 0
      && numericTextOrNull(risk.conservative_weighted_effective_strata_count)
      && numericTextOrNull(risk.maximum_active_stratum_gross_pct)
      && numericTextOrNull(risk.total_active_gross_pct)
      && numericTextOrNull(risk.v2_weighted_effective_cluster_count)
      && typeof risk.weighted_diversification_gate_applied === "boolean"
      && Array.isArray(risk.dimension_results)
      && risk.dimension_results.every(validDimension)
      && exactKeys(gaps, [
        "http_candidate_blocker_count", "http_candidate_blockers",
        "local_blocker_count", "stratified_budget_blocker_count",
      ])
      && Number.isInteger(gaps.http_candidate_blocker_count)
      && gaps.http_candidate_blocker_count === gaps.http_candidate_blockers.length
      && exactStringArray(gaps.http_candidate_blockers)
      && HTTP_CANDIDATE_BLOCKERS.every(function (blocker) {
        return gaps.http_candidate_blockers.indexOf(blocker) !== -1;
      })
      && Number.isInteger(gaps.local_blocker_count) && gaps.local_blocker_count >= 0
      && Number.isInteger(gaps.stratified_budget_blocker_count)
      && gaps.stratified_budget_blocker_count >= 0
      && exactKeys(facts, [
        "budget_v3_exactly_verified", "dimension_summaries_projected", "matrices_embedded",
        "positions_embedded", "profitability_proven", "runtime_consumer_bound",
        "source_document_embedded", "ui_mounted", "v6_envelope_exactly_verified",
        "verification_context_embedded",
      ])
      && facts.budget_v3_exactly_verified === true
      && facts.v6_envelope_exactly_verified === true
      && facts.dimension_summaries_projected === (risk.dimension_results.length > 0)
      && facts.matrices_embedded === false
      && facts.positions_embedded === false
      && facts.profitability_proven === false
      && facts.runtime_consumer_bound === false
      && facts.source_document_embedded === false
      && facts.ui_mounted === false
      && facts.verification_context_embedded === false
      && validStages(payload.stages)
      && authorityLocked(payload.authority);
  }

  function verifyStratifiedBudgetCandidateResponseV7(response) {
    if (!strictCanonical.verifySealedDocument(response, "response_hash") || !exactKeys(response, [
      "authority", "blockers", "facts", "interface_status", "lineage", "payload",
      "response_hash", "schema_version", "state", "static_fingerprint",
    ])) return false;

    var facts = response.facts;
    var lineage = response.lineage;
    if (response.schema_version !== RESPONSE_SCHEMA_VERSION
      || response.static_fingerprint !== RESPONSE_STATIC_FINGERPRINT
      || response.interface_status !== "UNREGISTERED_CANDIDATE"
      || ["KNOWN_BLOCKED", "UNKNOWN"].indexOf(response.state) === -1
      || !exactStringArray(response.blockers)
      || !HTTP_CANDIDATE_BLOCKERS.every(function (blocker) {
        return response.blockers.indexOf(blocker) !== -1;
      })
      || !authorityLocked(response.authority)
      || !exactKeys(facts, [
        "context_contract_valid", "presentation_v7_exactly_verified", "profitability_proven",
        "request_contract_valid", "result_available", "route_registered",
        "runtime_mutations_performed", "source_contract_known", "transport_registered", "ui_mounted",
      ])
      || facts.profitability_proven !== false
      || facts.route_registered !== false
      || facts.runtime_mutations_performed !== false
      || facts.transport_registered !== false
      || facts.ui_mounted !== false
      || !exactKeys(lineage, [
        "presentation_v7_hash", "presentation_v7_implementation_sha256",
        "presentation_v7_schema_version", "presentation_v7_static_fingerprint",
        "strict_canonical_implementation_sha256",
      ])
      || lineage.presentation_v7_schema_version !== PRESENTATION_SCHEMA_VERSION
      || lineage.presentation_v7_static_fingerprint !== PRESENTATION_STATIC_FINGERPRINT
      || lineage.presentation_v7_implementation_sha256 !== PRESENTATION_IMPLEMENTATION_SHA256
      || lineage.strict_canonical_implementation_sha256 !== STRICT_CANONICAL_IMPLEMENTATION_SHA256) {
      return false;
    }

    if (response.state === "UNKNOWN") {
      return response.payload === null
        && lineage.presentation_v7_hash === null
        && facts.presentation_v7_exactly_verified === false
        && facts.result_available === false
        && facts.source_contract_known === false;
    }
    return facts.request_contract_valid === true
      && facts.context_contract_valid === true
      && facts.presentation_v7_exactly_verified === true
      && facts.result_available === true
      && facts.source_contract_known === true
      && isHash(lineage.presentation_v7_hash)
      && validPayload(response.payload)
      && response.payload.source.presentation_v7_hash === lineage.presentation_v7_hash;
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) : "unknown";
  }

  function displayNumber(value, suffix) {
    return value === null ? "--" : String(value) + (suffix || "");
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "CORRELATION CLUSTER / ACTIVE STRATA",
      title: "Stratified risk evidence is unavailable",
      summary: "The candidate contract is unknown. No portfolio or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN",
      response_hash_short: "unknown",
      metrics: [],
      dimensions: [],
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail: axis === "PERMISSION" ? "NO_PERMISSION_CAN_BE_INFERRED" : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note: "Research display only. Route, runtime, paper, and live authority remain unavailable.",
    });
  }

  function buildPortfolioRiskStratifiedBudgetViewModelV7(response) {
    if (!verifyStratifiedBudgetCandidateResponseV7(response)
      || response.state !== "KNOWN_BLOCKED") return unknownViewModel();

    var payload = response.payload;
    var local = payload.local_decision;
    var risk = payload.risk_summary;
    var blocked = local.joint_status === "BLOCK";
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_BLOCKED",
      tone: blocked ? "blocked" : "bounded",
      kicker: "CORRELATION CLUSTER / ACTIVE STRATA",
      title: blocked
        ? "Active-strata budget holds the local gate"
        : "Active-strata budget is locally clear",
      summary: blocked
        ? "At least one preregistered stratum remains concentrated. Correlated assets stay grouped for the local research decision."
        : "The preregistered strata checks are locally clear, while governance and activation gaps remain open.",
      status_label: blocked ? "LOCAL BLOCK" : "LOCAL CLEAR",
      response_hash_short: shortHash(response.response_hash),
      metrics: [
        { label: "Active dimensions", value: String(risk.active_dimension_count), detail: "Preregistered only" },
        { label: "Effective strata", value: displayNumber(risk.conservative_weighted_effective_strata_count), detail: "Conservative minimum" },
        { label: "Max stratum gross", value: displayNumber(risk.maximum_active_stratum_gross_pct, "%"), detail: "Across active dimensions" },
        { label: "Effective clusters", value: displayNumber(risk.v2_weighted_effective_cluster_count), detail: "Gross weighted v2" },
      ],
      dimensions: risk.dimension_results.map(function (row) {
        return {
          dimension_id: row.dimension_id,
          status: row.status,
          active_stratum_count: row.active_stratum_count,
          effective_strata: displayNumber(row.weighted_effective_strata_count),
          maximum_gross: displayNumber(row.maximum_stratum_gross_pct, "%"),
          dominant_stratum_id: row.dominant_stratum_id,
        };
      }),
      stages: payload.stages.map(function (stage) {
        return { axis: stage.axis, state: stage.state, detail: stage.detail };
      }),
      blockers: response.blockers.slice(),
      permission_note: "Research display only. No route, current, paper, live, or execution permission.",
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderPortfolioRiskStratifiedBudgetCardV7(response) {
    var view = buildPortfolioRiskStratifiedBudgetViewModelV7(response);
    var metrics = view.metrics.map(function (metric) {
      return '<li class="hakimi-strata-card-v7__metric"><span>'
        + escapeHtml(metric.label) + "</span><strong>" + escapeHtml(metric.value)
        + "</strong><small>" + escapeHtml(metric.detail) + "</small></li>";
    }).join("");
    var dimensions = view.dimensions.map(function (row) {
      return '<li class="hakimi-strata-card-v7__dimension"><header><strong>'
        + escapeHtml(row.dimension_id) + '</strong><span data-state="'
        + escapeHtml(row.status.toLowerCase()) + '">' + escapeHtml(row.status)
        + "</span></header><dl><div><dt>Active strata</dt><dd>"
        + escapeHtml(row.active_stratum_count) + "</dd></div><div><dt>Effective</dt><dd>"
        + escapeHtml(row.effective_strata) + "</dd></div><div><dt>Max gross</dt><dd>"
        + escapeHtml(row.maximum_gross) + "</dd></div></dl><small>Dominant: "
        + escapeHtml(row.dominant_stratum_id) + "</small></li>";
    }).join("");
    var stages = view.stages.map(function (stage, index) {
      return '<li class="hakimi-strata-card-v7__stage"><span>0' + String(index + 1)
        + "</span><strong>" + escapeHtml(stage.axis) + "</strong><b>"
        + escapeHtml(stage.state) + "</b><small>" + escapeHtml(stage.detail)
        + "</small></li>";
    }).join("");

    return '<article class="hakimi-strata-card-v7" data-tone="' + escapeHtml(view.tone)
      + '" aria-label="Preregistered strata portfolio-risk evidence"><header class="hakimi-strata-card-v7__header"><div><p>'
      + escapeHtml(view.kicker) + "</p><h2>" + escapeHtml(view.title)
      + '</h2></div><span class="hakimi-strata-card-v7__status">'
      + escapeHtml(view.status_label) + '</span></header><p class="hakimi-strata-card-v7__summary">'
      + escapeHtml(view.summary) + '</p><ul class="hakimi-strata-card-v7__metrics">'
      + metrics + '</ul><ul class="hakimi-strata-card-v7__dimensions">' + dimensions
      + '</ul><ol class="hakimi-strata-card-v7__stages">' + stages
      + '</ol><footer class="hakimi-strata-card-v7__footer"><span>candidate '
      + escapeHtml(view.response_hash_short) + "</span><span>" + escapeHtml(view.permission_note)
      + "</span></footer></article>";
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT: CARD_STATIC_FINGERPRINT,
    RESPONSE_SCHEMA_VERSION: RESPONSE_SCHEMA_VERSION,
    RESPONSE_STATIC_FINGERPRINT: RESPONSE_STATIC_FINGERPRINT,
    PAYLOAD_SCHEMA_VERSION: PAYLOAD_SCHEMA_VERSION,
    STAGE_ORDER: STAGE_ORDER,
    verifyStratifiedBudgetCandidateResponseV7: verifyStratifiedBudgetCandidateResponseV7,
    buildPortfolioRiskStratifiedBudgetViewModelV7: buildPortfolioRiskStratifiedBudgetViewModelV7,
    renderPortfolioRiskStratifiedBudgetCardV7: renderPortfolioRiskStratifiedBudgetCardV7,
  });
});
