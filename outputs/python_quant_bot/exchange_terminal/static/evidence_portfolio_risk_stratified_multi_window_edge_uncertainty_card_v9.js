(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCardV9 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  "use strict";

  if (!strictCanonical || typeof strictCanonical.verifySealedDocument !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var RESPONSE_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "edge-uncertainty-presentation-http-candidate-response-v9";
  var RESPONSE_STATIC_FINGERPRINT =
    "20260823-stratified-multi-window-edge-uncertainty-presentation-http-" +
    "candidate-v9-unmounted-lock-1";
  var PAYLOAD_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "edge-uncertainty-presentation-http-payload-v9";
  var CARD_SCHEMA_VERSION =
    "portfolio-risk-stratified-multi-window-edge-uncertainty-card-v9";
  var CARD_STATIC_FINGERPRINT =
    "20260823-portfolio-risk-stratified-multi-window-edge-uncertainty-card-v9-" +
    "unmounted-lock-1";
  var PRESENTATION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-" +
    "edge-uncertainty-presentation-v9";
  var PRESENTATION_STATIC_FINGERPRINT =
    "20260823-stratified-multi-window-edge-uncertainty-presentation-v9-" +
    "unmounted-lock-1";
  var PRESENTATION_IMPLEMENTATION_SHA256 =
    "5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132";
  var HTTP_CANDIDATE_IMPLEMENTATION_SHA256 =
    "329aa276701063ba6625a7cedac495c82bd9b264dfd273043067ce1f6065d394";
  var STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var HTTP_CANDIDATE_BLOCKERS = Object.freeze([
    "HTTP_CANDIDATE_V9_UNREGISTERED",
    "PRESENTATION_V9_CONSUMER_NOT_REGISTERED",
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

  function integerInRange(value, minimum, maximum) {
    return Number.isSafeInteger(value) && value >= minimum && value <= maximum;
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
      "adapter_v8_decision",
      "adapter_v8_status",
      "edge_gate_v1_decision",
      "edge_gate_v1_status",
      "joint_decision",
      "joint_status",
      "presentation_v8_joint_decision",
      "presentation_v8_joint_status",
      "stability_gate_v2_decision",
      "stability_gate_v2_status",
    ])) return false;
    return [
      "adapter_v7_status",
      "adapter_v8_status",
      "edge_gate_v1_status",
      "joint_status",
      "presentation_v8_joint_status",
      "stability_gate_v2_status",
    ].every(function (key) {
      return ["PASS", "BLOCK"].indexOf(value[key]) !== -1;
    }) && [
      "adapter_v7_decision",
      "adapter_v8_decision",
      "edge_gate_v1_decision",
      "joint_decision",
      "presentation_v8_joint_decision",
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

  function validEdgeSummary(value) {
    if (!exactKeys(value, [
      "blocked_pair_count",
      "cluster_partition_hash",
      "confidence_z_micros",
      "correlation_floor_micros",
      "insufficient_sample_pair_count",
      "maximum_confidence_upper_correlation_micros",
      "observed_breach_pair_count",
      "uncertainty_overlap_pair_count",
      "verified_pair_count",
    ])) return false;
    var counts = [
      value.blocked_pair_count,
      value.insufficient_sample_pair_count,
      value.observed_breach_pair_count,
      value.uncertainty_overlap_pair_count,
      value.verified_pair_count,
    ];
    return counts.every(function (count) {
      return Number.isInteger(count) && count >= 0;
    })
      && value.blocked_pair_count <= value.verified_pair_count
      && isHash(value.cluster_partition_hash)
      && integerInRange(value.correlation_floor_micros, -1000000, 1000000)
      && Number.isSafeInteger(value.confidence_z_micros)
      && value.confidence_z_micros > 0
      && integerInRange(
        value.maximum_confidence_upper_correlation_micros,
        -1000000,
        1000000
      );
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
      && stages[2].detail === "UNMOUNTED_HTTP_CANDIDATE_V9"
      && stages[3].state === "UNAUTHORIZED"
      && stages[3].detail === "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY";
  }

  function validPayload(payload) {
    if (!strictCanonical.verifySealedDocument(payload, "payload_hash") || !exactKeys(payload, [
      "authority",
      "decision",
      "edge_uncertainty_summary",
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
      && payload.decision === "EXACT_PRESENTATION_V9_PROJECTED_AUTHORITY_UNCHANGED"
      && authorityLocked(payload.authority)
      && exactKeys(facts, [
        "adapter_v8_exactly_verified",
        "edge_uncertainty_summary_projected",
        "matrices_embedded",
        "multi_window_summary_projected",
        "positions_embedded",
        "presentation_v8_exactly_verified",
        "profitability_proven",
        "runtime_consumer_bound",
        "source_documents_embedded",
        "ui_mounted",
        "verification_contexts_embedded",
      ])
      && facts.adapter_v8_exactly_verified === true
      && facts.edge_uncertainty_summary_projected === true
      && facts.multi_window_summary_projected === true
      && facts.presentation_v8_exactly_verified === true
      && facts.matrices_embedded === false
      && facts.positions_embedded === false
      && facts.profitability_proven === false
      && facts.runtime_consumer_bound === false
      && facts.source_documents_embedded === false
      && facts.ui_mounted === false
      && facts.verification_contexts_embedded === false
      && exactKeys(gaps, [
        "adapter_v8_blocker_count",
        "edge_uncertainty_blocker_count",
        "http_candidate_blocker_count",
        "http_candidate_blockers",
        "local_blocker_count",
        "presentation_blocker_count",
        "presentation_blockers",
      ])
      && [
        "adapter_v8_blocker_count",
        "edge_uncertainty_blocker_count",
        "http_candidate_blocker_count",
        "local_blocker_count",
        "presentation_blocker_count",
      ].every(function (key) {
        return Number.isInteger(gaps[key]) && gaps[key] >= 0;
      })
      && gaps.http_candidate_blocker_count === gaps.http_candidate_blockers.length
      && exactStringArray(gaps.http_candidate_blockers)
      && HTTP_CANDIDATE_BLOCKERS.every(function (blocker) {
        return gaps.http_candidate_blockers.indexOf(blocker) !== -1;
      })
      && exactStringArray(gaps.presentation_blockers)
      && gaps.presentation_blocker_count === gaps.presentation_blockers.length
      && validLocalDecision(payload.local_decision)
      && validMultiWindowSummary(payload.multi_window_summary)
      && validRiskSummary(payload.risk_summary)
      && validEdgeSummary(payload.edge_uncertainty_summary)
      && exactKeys(source, [
        "adapter_v7_hash",
        "adapter_v8_hash",
        "cluster_partition_hash",
        "edge_gate_v1_hash",
        "presentation_v8_hash",
        "presentation_v9_hash",
        "stability_gate_v2_hash",
        "state",
        "trade_identity_hash",
      ])
      && source.state === "EXACT_PRESENTATION_V8_AND_ADAPTER_V8"
      && [
        "adapter_v7_hash",
        "adapter_v8_hash",
        "cluster_partition_hash",
        "edge_gate_v1_hash",
        "presentation_v8_hash",
        "presentation_v9_hash",
        "stability_gate_v2_hash",
        "trade_identity_hash",
      ].every(function (key) { return isHash(source[key]); })
      && payload.edge_uncertainty_summary.cluster_partition_hash
        === source.cluster_partition_hash
      && validStages(payload.stages);
  }

  function verifyStratifiedMultiWindowEdgeUncertaintyCandidateResponseV9(response) {
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
        "presentation_v9_exactly_verified",
        "profitability_proven",
        "request_contract_valid",
        "result_available",
        "route_registered",
        "runtime_mutations_performed",
        "source_contract_known",
        "transport_registered",
        "ui_mounted",
      ])
      || !Object.keys(facts).every(function (key) { return typeof facts[key] === "boolean"; })
      || facts.profitability_proven !== false
      || facts.route_registered !== false
      || facts.runtime_mutations_performed !== false
      || facts.transport_registered !== false
      || facts.ui_mounted !== false
      || !exactKeys(lineage, [
        "presentation_v9_hash",
        "presentation_v9_implementation_sha256",
        "presentation_v9_schema_version",
        "presentation_v9_static_fingerprint",
        "strict_canonical_implementation_sha256",
      ])
      || lineage.presentation_v9_schema_version !== PRESENTATION_SCHEMA_VERSION
      || lineage.presentation_v9_static_fingerprint !== PRESENTATION_STATIC_FINGERPRINT
      || lineage.presentation_v9_implementation_sha256 !== PRESENTATION_IMPLEMENTATION_SHA256
      || lineage.strict_canonical_implementation_sha256
        !== STRICT_CANONICAL_IMPLEMENTATION_SHA256) {
      return false;
    }

    if (response.state === "UNKNOWN") {
      return response.payload === null
        && lineage.presentation_v9_hash === null
        && facts.presentation_v9_exactly_verified === false
        && facts.result_available === false
        && facts.source_contract_known === false;
    }
    return facts.request_contract_valid === true
      && facts.context_contract_valid === true
      && facts.presentation_v9_exactly_verified === true
      && facts.result_available === true
      && facts.source_contract_known === true
      && isHash(lineage.presentation_v9_hash)
      && validPayload(response.payload)
      && response.payload.source.presentation_v9_hash === lineage.presentation_v9_hash;
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) : "unknown";
  }

  function displayNumber(value, suffix) {
    return value === null ? "--" : String(value) + (suffix || "");
  }

  function microsText(value) {
    if (!Number.isSafeInteger(value)) return "--";
    return (value / 1000000).toFixed(3);
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "CORRELATION CLUSTERS / EDGE UNCERTAINTY",
      title: "Cross-cluster evidence is unavailable",
      summary: "The candidate contract is unknown. No cluster, maturity, or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN / OUTER BLOCK",
      response_hash_short: "unknown",
      edge: null,
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

  function buildPortfolioRiskStratifiedMultiWindowEdgeUncertaintyViewModelV9(response) {
    if (!verifyStratifiedMultiWindowEdgeUncertaintyCandidateResponseV9(response)
      || response.state !== "KNOWN_BLOCKED") return unknownViewModel();

    var payload = response.payload;
    var local = payload.local_decision;
    var multi = payload.multi_window_summary;
    var risk = payload.risk_summary;
    var edge = payload.edge_uncertainty_summary;
    var blocked = local.joint_status === "BLOCK" || edge.blocked_pair_count > 0;
    var edgeBlocked = edge.blocked_pair_count > 0;
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_BLOCKED",
      tone: blocked ? "blocked" : "bounded",
      kicker: "CORRELATION CLUSTERS / EDGE UNCERTAINTY",
      title: edgeBlocked
        ? "Cross-cluster uncertainty holds the local gate"
        : "Cluster separation survives the registered check",
      summary: blocked
        ? "At least one preregistered research component remains blocked. Correlated assets are not counted as independent evidence."
        : "Registered windows and cross-cluster confidence bounds are locally clear, while consumer, current, and execution gaps remain open.",
      status_label: blocked ? "LOCAL BLOCK / OUTER BLOCK" : "LOCAL CLEAR / OUTER BLOCK",
      response_hash_short: shortHash(response.response_hash),
      edge: {
        blocked_count: edge.blocked_pair_count,
        verified_count: edge.verified_pair_count,
        observed_breach_count: edge.observed_breach_pair_count,
        uncertainty_overlap_count: edge.uncertainty_overlap_pair_count,
        insufficient_sample_count: edge.insufficient_sample_pair_count,
        floor: microsText(edge.correlation_floor_micros),
        maximum_upper: microsText(edge.maximum_confidence_upper_correlation_micros),
        confidence_z: microsText(edge.confidence_z_micros),
        partition_hash_short: shortHash(edge.cluster_partition_hash),
        blocked: edgeBlocked,
      },
      window: {
        anchor_id: multi.anchor_window_id,
        coverage: String(multi.verified_window_count) + "/" + String(multi.registered_window_count),
        any_blocked: multi.any_registered_window_blocked === true,
      },
      metrics: [
        {
          label: "Edge coverage",
          value: String(edge.verified_pair_count),
          detail: "Preregistered cross-cluster pairs",
        },
        {
          label: "Maximum confidence upper",
          value: microsText(edge.maximum_confidence_upper_correlation_micros),
          detail: "One-sided correlation bound",
        },
        {
          label: "Preregistered floor",
          value: microsText(edge.correlation_floor_micros),
          detail: "Positive-correlation gate",
        },
        {
          label: "Window coverage",
          value: String(multi.verified_window_count) + "/" + String(multi.registered_window_count),
          detail: "Verified / preregistered",
        },
      ],
      signals: [
        {
          label: "Edge gate",
          state: edgeBlocked ? "BLOCK PRESENT" : "NO EDGE BLOCK",
          clear: !edgeBlocked,
        },
        {
          label: "Observed breaches",
          state: String(edge.observed_breach_pair_count),
          clear: edge.observed_breach_pair_count === 0,
        },
        {
          label: "Uncertainty overlaps",
          state: String(edge.uncertainty_overlap_pair_count),
          clear: edge.uncertainty_overlap_pair_count === 0,
        },
        {
          label: "Insufficient samples",
          state: String(edge.insufficient_sample_pair_count),
          clear: edge.insufficient_sample_pair_count === 0,
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
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCardV9(response) {
    var view = buildPortfolioRiskStratifiedMultiWindowEdgeUncertaintyViewModelV9(response);
    var edgeMarkup = view.edge === null
      ? '<section class="hakimi-edge-card-v9__bridge" data-state="unknown"><div class="hakimi-edge-card-v9__rail"><span>A</span><i></i><span>B</span></div><div><small>EDGE CONTRACT</small><strong>unknown</strong><p>No pair aggregate is displayed.</p></div></section>'
      : '<section class="hakimi-edge-card-v9__bridge" data-state="'
        + (view.edge.blocked ? "blocked" : "bounded")
        + '"><div class="hakimi-edge-card-v9__rail"><span>A</span><i></i><span>B</span></div><div><small>MAXIMUM CONFIDENCE UPPER / FLOOR</small><strong>'
        + escapeHtml(view.edge.maximum_upper) + ' / ' + escapeHtml(view.edge.floor)
        + '</strong><p>partition ' + escapeHtml(view.edge.partition_hash_short)
        + ' · z ' + escapeHtml(view.edge.confidence_z) + '</p></div></section>';
    var metrics = view.metrics.map(function (metric) {
      return '<li class="hakimi-edge-card-v9__metric"><span>'
        + escapeHtml(metric.label) + '</span><strong>' + escapeHtml(metric.value)
        + '</strong><small>' + escapeHtml(metric.detail) + '</small></li>';
    }).join("");
    var signals = view.signals.map(function (signal) {
      return '<li class="hakimi-edge-card-v9__signal" data-state="'
        + (signal.clear ? "bounded" : "blocked") + '"><span>'
        + escapeHtml(signal.label) + '</span><strong>' + escapeHtml(signal.state)
        + '</strong></li>';
    }).join("");
    var dimensions = view.dimensions.map(function (row) {
      return '<li class="hakimi-edge-card-v9__dimension"><header><strong>'
        + escapeHtml(row.dimension_id) + '</strong><span data-state="'
        + escapeHtml(row.status.toLowerCase()) + '">' + escapeHtml(row.status)
        + '</span></header><dl><div><dt>Active strata</dt><dd>'
        + escapeHtml(row.active_stratum_count) + '</dd></div><div><dt>Effective</dt><dd>'
        + escapeHtml(row.effective_strata) + '</dd></div><div><dt>Max gross</dt><dd>'
        + escapeHtml(row.maximum_gross) + '</dd></div></dl><small>Dominant: '
        + escapeHtml(row.dominant_stratum_id) + '</small></li>';
    }).join("");
    var stages = view.stages.map(function (stage, index) {
      return '<li class="hakimi-edge-card-v9__stage"><span>0' + String(index + 1)
        + '</span><strong>' + escapeHtml(stage.axis) + '</strong><b>'
        + escapeHtml(stage.state) + '</b><small>' + escapeHtml(stage.detail)
        + '</small></li>';
    }).join("");

    return '<article class="hakimi-edge-card-v9" data-tone="' + escapeHtml(view.tone)
      + '" aria-label="Preregistered cross-cluster edge uncertainty evidence">'
      + '<header class="hakimi-edge-card-v9__header"><div><p>'
      + escapeHtml(view.kicker) + '</p><h2>' + escapeHtml(view.title)
      + '</h2></div><span class="hakimi-edge-card-v9__status" role="status">'
      + escapeHtml(view.status_label) + '</span></header>'
      + '<p class="hakimi-edge-card-v9__summary">' + escapeHtml(view.summary) + '</p>'
      + edgeMarkup
      + '<ul class="hakimi-edge-card-v9__metrics">' + metrics + '</ul>'
      + '<ul class="hakimi-edge-card-v9__signals" aria-label="Edge uncertainty signals">'
      + signals + '</ul>'
      + '<ul class="hakimi-edge-card-v9__dimensions">' + dimensions + '</ul>'
      + '<ol class="hakimi-edge-card-v9__stages" aria-label="Evidence stages">'
      + stages + '</ol>'
      + '<footer class="hakimi-edge-card-v9__footer"><span>candidate '
      + escapeHtml(view.response_hash_short) + '</span><span>'
      + escapeHtml(view.permission_note) + '</span></footer></article>';
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT: CARD_STATIC_FINGERPRINT,
    HTTP_CANDIDATE_IMPLEMENTATION_SHA256: HTTP_CANDIDATE_IMPLEMENTATION_SHA256,
    PAYLOAD_SCHEMA_VERSION: PAYLOAD_SCHEMA_VERSION,
    RESPONSE_SCHEMA_VERSION: RESPONSE_SCHEMA_VERSION,
    RESPONSE_STATIC_FINGERPRINT: RESPONSE_STATIC_FINGERPRINT,
    STAGE_ORDER: STAGE_ORDER,
    verifyStratifiedMultiWindowEdgeUncertaintyCandidateResponseV9:
      verifyStratifiedMultiWindowEdgeUncertaintyCandidateResponseV9,
    buildPortfolioRiskStratifiedMultiWindowEdgeUncertaintyViewModelV9:
      buildPortfolioRiskStratifiedMultiWindowEdgeUncertaintyViewModelV9,
    renderPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCardV9:
      renderPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCardV9,
  });
});
