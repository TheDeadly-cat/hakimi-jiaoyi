(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskStratifiedMultiWindowCardV8 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  "use strict";

  if (!strictCanonical || typeof strictCanonical.verifySealedDocument !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var RESPONSE_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "presentation-http-candidate-response-v8";
  var RESPONSE_STATIC_FINGERPRINT =
    "20260823-stratified-multi-window-presentation-http-candidate-v8-" +
    "unmounted-lock-1";
  var PAYLOAD_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "presentation-http-payload-v8";
  var CARD_SCHEMA_VERSION = "portfolio-risk-stratified-multi-window-card-v8";
  var CARD_STATIC_FINGERPRINT =
    "20260823-portfolio-risk-stratified-multi-window-card-v8-unmounted-lock-1";
  var PRESENTATION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "presentation-v8";
  var PRESENTATION_STATIC_FINGERPRINT =
    "20260823-stratified-multi-window-presentation-v8-unmounted-lock-1";
  var PRESENTATION_IMPLEMENTATION_SHA256 =
    "f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b";
  var HTTP_CANDIDATE_IMPLEMENTATION_SHA256 =
    "70e2cabb54d0a9bf51973756fbe40173b142745d3a3f9d0f6f816ca759eb2770";
  var STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var HTTP_CANDIDATE_BLOCKERS = Object.freeze([
    "HTTP_CANDIDATE_V8_UNREGISTERED",
    "PRESENTATION_V8_CONSUMER_NOT_REGISTERED",
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

  function numericText(value) {
    return typeof value === "string"
      && /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$/.test(value);
  }

  function exactStringArray(value) {
    return Array.isArray(value) && value.every(function (item) {
      return typeof item === "string" && item.length > 0;
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
    ])
      && Number.isInteger(value.active_stratum_count)
      && value.active_stratum_count >= 0
      && Number.isInteger(value.over_limit_stratum_count)
      && value.over_limit_stratum_count >= 0
      && typeof value.dimension_id === "string"
      && value.dimension_id.length > 0
      && typeof value.dominant_stratum_id === "string"
      && value.dominant_stratum_id.length > 0
      && ["PASS", "BLOCK", "NOT_APPLICABLE"].indexOf(value.diversification_status) !== -1
      && ["PASS", "BLOCK"].indexOf(value.gross_limit_status) !== -1
      && ["PASS", "BLOCK"].indexOf(value.status) !== -1
      && numericText(value.dominant_stratum_share_of_active_gross_pct)
      && numericText(value.maximum_stratum_gross_pct)
      && numericText(value.weighted_effective_strata_count);
  }

  function validLocalDecision(value) {
    if (!exactKeys(value, [
      "adapter_v7_decision",
      "adapter_v7_status",
      "anchor_budget_v3_decision",
      "anchor_budget_v3_status",
      "joint_decision",
      "joint_status",
      "presentation_v7_joint_decision",
      "presentation_v7_joint_status",
      "stability_gate_v2_decision",
      "stability_gate_v2_status",
    ])) return false;
    return [
      "adapter_v7_status",
      "anchor_budget_v3_status",
      "joint_status",
      "presentation_v7_joint_status",
      "stability_gate_v2_status",
    ].every(function (key) {
      return ["PASS", "BLOCK"].indexOf(value[key]) !== -1;
    }) && [
      "adapter_v7_decision",
      "anchor_budget_v3_decision",
      "joint_decision",
      "presentation_v7_joint_decision",
      "stability_gate_v2_decision",
    ].every(function (key) {
      return typeof value[key] === "string" && value[key].length > 0;
    });
  }

  function validMultiWindowSummary(value) {
    return exactKeys(value, [
      "anchor_window_id",
      "any_registered_window_blocked",
      "cluster_partition_stable",
      "minimum_conservative_weighted_effective_strata_count",
      "registered_window_count",
      "strata_topology_stable",
      "verified_window_count",
      "worst_window_maximum_active_stratum_gross_pct",
    ])
      && typeof value.anchor_window_id === "string"
      && value.anchor_window_id.length > 0
      && typeof value.any_registered_window_blocked === "boolean"
      && typeof value.cluster_partition_stable === "boolean"
      && typeof value.strata_topology_stable === "boolean"
      && Number.isInteger(value.registered_window_count)
      && value.registered_window_count > 0
      && Number.isInteger(value.verified_window_count)
      && value.verified_window_count === value.registered_window_count
      && numericText(value.minimum_conservative_weighted_effective_strata_count)
      && numericText(value.worst_window_maximum_active_stratum_gross_pct);
  }

  function validRiskSummary(value) {
    if (!exactKeys(value, [
      "active_dimension_count",
      "conservative_weighted_effective_strata_count",
      "dimension_results",
      "maximum_active_stratum_gross_pct",
      "total_active_gross_pct",
      "v2_weighted_effective_cluster_count",
      "weighted_diversification_gate_applied",
    ])) return false;
    return Number.isInteger(value.active_dimension_count)
      && value.active_dimension_count >= 0
      && Array.isArray(value.dimension_results)
      && value.active_dimension_count === value.dimension_results.length
      && value.dimension_results.every(validDimension)
      && numericText(value.conservative_weighted_effective_strata_count)
      && numericText(value.maximum_active_stratum_gross_pct)
      && numericText(value.total_active_gross_pct)
      && numericText(value.v2_weighted_effective_cluster_count)
      && typeof value.weighted_diversification_gate_applied === "boolean";
  }

  function validStages(stages) {
    return Array.isArray(stages)
      && stages.length === STAGE_ORDER.length
      && stages.every(function (stage, index) {
        return exactKeys(stage, ["axis", "detail", "state"])
          && stage.axis === STAGE_ORDER[index]
          && typeof stage.detail === "string"
          && stage.detail.length > 0
          && typeof stage.state === "string"
          && stage.state.length > 0;
      })
      && stages[2].state === "CANDIDATE_ONLY"
      && stages[2].detail === "UNMOUNTED_HTTP_CANDIDATE_V8"
      && stages[3].state === "UNAUTHORIZED"
      && stages[3].detail === "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY";
  }

  function validPayload(payload) {
    if (!strictCanonical.verifySealedDocument(payload, "payload_hash") || !exactKeys(payload, [
      "authority",
      "decision",
      "facts",
      "gaps",
      "local_decision",
      "multi_window_summary",
      "payload_hash",
      "risk_summary",
      "schema_version",
      "source",
      "stages",
      "status",
    ])) return false;

    var facts = payload.facts;
    var gaps = payload.gaps;
    var source = payload.source;
    return payload.schema_version === PAYLOAD_SCHEMA_VERSION
      && payload.status === "BLOCK"
      && payload.decision === "EXACT_PRESENTATION_V8_PROJECTED_AUTHORITY_UNCHANGED"
      && authorityLocked(payload.authority)
      && exactKeys(facts, [
        "adapter_v7_exactly_verified",
        "matrices_embedded",
        "multi_window_summary_projected",
        "positions_embedded",
        "presentation_v7_exactly_verified",
        "profitability_proven",
        "runtime_consumer_bound",
        "source_documents_embedded",
        "ui_mounted",
        "verification_contexts_embedded",
      ])
      && facts.adapter_v7_exactly_verified === true
      && facts.multi_window_summary_projected === true
      && facts.presentation_v7_exactly_verified === true
      && facts.matrices_embedded === false
      && facts.positions_embedded === false
      && facts.profitability_proven === false
      && facts.runtime_consumer_bound === false
      && facts.source_documents_embedded === false
      && facts.ui_mounted === false
      && facts.verification_contexts_embedded === false
      && exactKeys(gaps, [
        "http_candidate_blocker_count",
        "http_candidate_blockers",
        "local_blocker_count",
        "multi_window_blocker_count",
        "presentation_blocker_count",
        "presentation_blockers",
      ])
      && Number.isInteger(gaps.http_candidate_blocker_count)
      && gaps.http_candidate_blocker_count === gaps.http_candidate_blockers.length
      && exactStringArray(gaps.http_candidate_blockers)
      && HTTP_CANDIDATE_BLOCKERS.every(function (blocker) {
        return gaps.http_candidate_blockers.indexOf(blocker) !== -1;
      })
      && Number.isInteger(gaps.local_blocker_count)
      && gaps.local_blocker_count >= 0
      && Number.isInteger(gaps.multi_window_blocker_count)
      && gaps.multi_window_blocker_count >= 0
      && Number.isInteger(gaps.presentation_blocker_count)
      && gaps.presentation_blocker_count >= 0
      && exactStringArray(gaps.presentation_blockers)
      && gaps.presentation_blocker_count === gaps.presentation_blockers.length
      && validLocalDecision(payload.local_decision)
      && validMultiWindowSummary(payload.multi_window_summary)
      && validRiskSummary(payload.risk_summary)
      && exactKeys(source, [
        "adapter_v7_hash",
        "presentation_v7_hash",
        "presentation_v8_hash",
        "stability_gate_v2_hash",
        "state",
        "trade_identity_hash",
      ])
      && source.state === "EXACT_PRESENTATION_V7_AND_ADAPTER_V7"
      && [
        "adapter_v7_hash",
        "presentation_v7_hash",
        "presentation_v8_hash",
        "stability_gate_v2_hash",
        "trade_identity_hash",
      ].every(function (key) { return isHash(source[key]); })
      && validStages(payload.stages);
  }

  function verifyStratifiedMultiWindowCandidateResponseV8(response) {
    if (!strictCanonical.verifySealedDocument(response, "response_hash") || !exactKeys(response, [
      "authority",
      "blockers",
      "facts",
      "interface_status",
      "lineage",
      "payload",
      "response_hash",
      "schema_version",
      "state",
      "static_fingerprint",
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
        "context_contract_valid",
        "presentation_v8_exactly_verified",
        "profitability_proven",
        "request_contract_valid",
        "result_available",
        "route_registered",
        "runtime_mutations_performed",
        "source_contract_known",
        "transport_registered",
        "ui_mounted",
      ])
      || facts.profitability_proven !== false
      || facts.route_registered !== false
      || facts.runtime_mutations_performed !== false
      || facts.transport_registered !== false
      || facts.ui_mounted !== false
      || !exactKeys(lineage, [
        "presentation_v8_hash",
        "presentation_v8_implementation_sha256",
        "presentation_v8_schema_version",
        "presentation_v8_static_fingerprint",
        "strict_canonical_implementation_sha256",
      ])
      || lineage.presentation_v8_schema_version !== PRESENTATION_SCHEMA_VERSION
      || lineage.presentation_v8_static_fingerprint !== PRESENTATION_STATIC_FINGERPRINT
      || lineage.presentation_v8_implementation_sha256 !== PRESENTATION_IMPLEMENTATION_SHA256
      || lineage.strict_canonical_implementation_sha256
        !== STRICT_CANONICAL_IMPLEMENTATION_SHA256) {
      return false;
    }

    if (response.state === "UNKNOWN") {
      return response.payload === null
        && lineage.presentation_v8_hash === null
        && facts.presentation_v8_exactly_verified === false
        && facts.result_available === false
        && facts.source_contract_known === false;
    }
    return facts.request_contract_valid === true
      && facts.context_contract_valid === true
      && facts.presentation_v8_exactly_verified === true
      && facts.result_available === true
      && facts.source_contract_known === true
      && isHash(lineage.presentation_v8_hash)
      && validPayload(response.payload)
      && response.payload.source.presentation_v8_hash === lineage.presentation_v8_hash;
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
      kicker: "CORRELATION CLUSTERS / PREREGISTERED WINDOWS",
      title: "Multi-window evidence is unavailable",
      summary: "The candidate contract is unknown. No stability, maturity, or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN / OUTER BLOCK",
      response_hash_short: "unknown",
      window: null,
      metrics: [],
      signals: [],
      dimensions: [],
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail: axis === "PERMISSION" ? "NO_PERMISSION_CAN_BE_INFERRED" : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note: "Research display only. Route, current, paper, live, and execution authority remain unavailable.",
    });
  }

  function buildPortfolioRiskStratifiedMultiWindowViewModelV8(response) {
    if (!verifyStratifiedMultiWindowCandidateResponseV8(response)
      || response.state !== "KNOWN_BLOCKED") return unknownViewModel();

    var payload = response.payload;
    var local = payload.local_decision;
    var multi = payload.multi_window_summary;
    var risk = payload.risk_summary;
    var blocked = local.joint_status === "BLOCK";
    var windowBlocked = multi.any_registered_window_blocked === true;
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_BLOCKED",
      tone: blocked ? "blocked" : "bounded",
      kicker: "CORRELATION CLUSTERS / PREREGISTERED WINDOWS",
      title: blocked
        ? "Cross-window structure holds the local gate"
        : "Cross-window structure is locally consistent",
      summary: blocked
        ? "At least one preregistered research component remains blocked. Correlated assets stay grouped across the registered windows."
        : "Registered-window structure and the anchor-local checks are clear, while consumer, current, and execution gaps remain open.",
      status_label: blocked ? "LOCAL BLOCK / OUTER BLOCK" : "LOCAL CLEAR / OUTER BLOCK",
      response_hash_short: shortHash(response.response_hash),
      window: {
        anchor_id: multi.anchor_window_id,
        coverage: String(multi.verified_window_count) + "/" + String(multi.registered_window_count),
        registered_count: multi.registered_window_count,
        verified_count: multi.verified_window_count,
        any_blocked: windowBlocked,
      },
      metrics: [
        {
          label: "Window coverage",
          value: String(multi.verified_window_count) + "/" + String(multi.registered_window_count),
          detail: "Verified / preregistered",
        },
        {
          label: "Effective strata floor",
          value: displayNumber(multi.minimum_conservative_weighted_effective_strata_count),
          detail: "Worst registered window",
        },
        {
          label: "Worst max stratum gross",
          value: displayNumber(multi.worst_window_maximum_active_stratum_gross_pct, "%"),
          detail: "Across registered windows",
        },
        {
          label: "Anchor max stratum gross",
          value: displayNumber(risk.maximum_active_stratum_gross_pct, "%"),
          detail: "Anchor-local projection",
        },
      ],
      signals: [
        {
          label: "Cluster partition",
          state: multi.cluster_partition_stable ? "STABLE" : "UNSTABLE",
          clear: multi.cluster_partition_stable,
        },
        {
          label: "Strata topology",
          state: multi.strata_topology_stable ? "STABLE" : "UNSTABLE",
          clear: multi.strata_topology_stable,
        },
        {
          label: "Registered windows",
          state: windowBlocked ? "BLOCK PRESENT" : "NO WINDOW BLOCK",
          clear: !windowBlocked,
        },
        {
          label: "Local joint gate",
          state: local.joint_status,
          clear: local.joint_status === "PASS",
        },
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

  function renderPortfolioRiskStratifiedMultiWindowCardV8(response) {
    var view = buildPortfolioRiskStratifiedMultiWindowViewModelV8(response);
    var windowMarkup = view.window === null
      ? '<section class="hakimi-multiwindow-card-v8__window" data-state="unknown"><span>ANCHOR</span><strong>unknown</strong><small>0 verified windows</small></section>'
      : '<section class="hakimi-multiwindow-card-v8__window" data-state="'
        + (view.window.any_blocked ? "blocked" : "bounded")
        + '"><span>ANCHOR WINDOW</span><strong>' + escapeHtml(view.window.anchor_id)
        + '</strong><small>' + escapeHtml(view.window.coverage)
        + " windows exactly verified</small></section>";
    var metrics = view.metrics.map(function (metric) {
      return '<li class="hakimi-multiwindow-card-v8__metric"><span>'
        + escapeHtml(metric.label) + "</span><strong>" + escapeHtml(metric.value)
        + "</strong><small>" + escapeHtml(metric.detail) + "</small></li>";
    }).join("");
    var signals = view.signals.map(function (signal) {
      return '<li class="hakimi-multiwindow-card-v8__signal" data-state="'
        + (signal.clear ? "bounded" : "blocked") + '"><span>'
        + escapeHtml(signal.label) + "</span><strong>" + escapeHtml(signal.state)
        + "</strong></li>";
    }).join("");
    var dimensions = view.dimensions.map(function (row) {
      return '<li class="hakimi-multiwindow-card-v8__dimension"><header><strong>'
        + escapeHtml(row.dimension_id) + '</strong><span data-state="'
        + escapeHtml(row.status.toLowerCase()) + '">' + escapeHtml(row.status)
        + "</span></header><dl><div><dt>Active strata</dt><dd>"
        + escapeHtml(row.active_stratum_count) + "</dd></div><div><dt>Effective</dt><dd>"
        + escapeHtml(row.effective_strata) + "</dd></div><div><dt>Max gross</dt><dd>"
        + escapeHtml(row.maximum_gross) + "</dd></div></dl><small>Dominant: "
        + escapeHtml(row.dominant_stratum_id) + "</small></li>";
    }).join("");
    var stages = view.stages.map(function (stage, index) {
      return '<li class="hakimi-multiwindow-card-v8__stage"><span>0' + String(index + 1)
        + "</span><strong>" + escapeHtml(stage.axis) + "</strong><b>"
        + escapeHtml(stage.state) + "</b><small>" + escapeHtml(stage.detail)
        + "</small></li>";
    }).join("");

    return '<article class="hakimi-multiwindow-card-v8" data-tone="'
      + escapeHtml(view.tone)
      + '" aria-label="Preregistered multi-window correlation-cluster evidence">'
      + '<header class="hakimi-multiwindow-card-v8__header"><div><p>'
      + escapeHtml(view.kicker) + "</p><h2>" + escapeHtml(view.title)
      + '</h2></div><span class="hakimi-multiwindow-card-v8__status" role="status">'
      + escapeHtml(view.status_label) + "</span></header>"
      + '<p class="hakimi-multiwindow-card-v8__summary">' + escapeHtml(view.summary)
      + "</p>" + windowMarkup
      + '<ul class="hakimi-multiwindow-card-v8__metrics">' + metrics + "</ul>"
      + '<ul class="hakimi-multiwindow-card-v8__signals" aria-label="Stability signals">'
      + signals + "</ul>"
      + '<ul class="hakimi-multiwindow-card-v8__dimensions">' + dimensions + "</ul>"
      + '<ol class="hakimi-multiwindow-card-v8__stages" aria-label="Evidence stages">'
      + stages + "</ol>"
      + '<footer class="hakimi-multiwindow-card-v8__footer"><span>candidate '
      + escapeHtml(view.response_hash_short) + "</span><span>" + escapeHtml(view.permission_note)
      + "</span></footer></article>";
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT: CARD_STATIC_FINGERPRINT,
    HTTP_CANDIDATE_IMPLEMENTATION_SHA256: HTTP_CANDIDATE_IMPLEMENTATION_SHA256,
    PAYLOAD_SCHEMA_VERSION: PAYLOAD_SCHEMA_VERSION,
    RESPONSE_SCHEMA_VERSION: RESPONSE_SCHEMA_VERSION,
    RESPONSE_STATIC_FINGERPRINT: RESPONSE_STATIC_FINGERPRINT,
    STAGE_ORDER: STAGE_ORDER,
    verifyStratifiedMultiWindowCandidateResponseV8:
      verifyStratifiedMultiWindowCandidateResponseV8,
    buildPortfolioRiskStratifiedMultiWindowViewModelV8:
      buildPortfolioRiskStratifiedMultiWindowViewModelV8,
    renderPortfolioRiskStratifiedMultiWindowCardV8:
      renderPortfolioRiskStratifiedMultiWindowCardV8,
  });
});
