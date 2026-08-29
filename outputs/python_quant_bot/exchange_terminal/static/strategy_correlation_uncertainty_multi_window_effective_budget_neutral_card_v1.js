(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var presentation =
    typeof module === "object" && module.exports
      ? require("./strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js")
      : root.HakimiStrategyCorrelationUncertaintyMultiWindowEffectiveBudgetNeutralPresentationV1;
  var api = factory(strictCanonical, presentation);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) {
    root.HakimiStrategyCorrelationUncertaintyMultiWindowEffectiveBudgetNeutralCardV1 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical,
  presentation
) {
  "use strict";

  if (!strictCanonical
    || typeof strictCanonical.verifySealedDocument !== "function"
    || typeof strictCanonical.isPlainRecord !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }
  if (!presentation
    || typeof presentation.SCHEMA_VERSION !== "string"
    || typeof presentation.STATIC_FINGERPRINT !== "string") {
    throw new Error("Neutral presentation v1 is required");
  }

  var CARD_SCHEMA_VERSION =
    "strategy-correlation-uncertainty-multi-window-effective-budget-neutral-card-v1";
  var CARD_STATIC_FINGERPRINT =
    "20260824-strategy-correlation-uncertainty-multi-window-effective-budget-neutral-card-v1-unmounted-semantic-lock-1";
  var PRESENTATION_SOURCE_SHA256 =
    "70cdc9a565e2b57be7c7c8c4da474df6a308aead2880419e3da344838ac0b65a";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var PRESENTATION_STATES = Object.freeze([
    "CROSS_CLUSTER_DEPENDENCE_VETO",
    "RISK_REDUCTION_ONLY",
    "RESEARCH_BUDGET_CONTRACT_OBSERVED",
    "RESEARCH_BUDGET_BLOCK_OBSERVED",
    "DOWNSTREAM_BUDGET_CHAIN_BLOCK",
  ]);
  var REASON_CODES = Object.freeze([
    "LOCAL_RESEARCH_EVIDENCE_PRESENTED_PERMISSION_LOCKED",
    "SOURCE_DOCUMENT_SET_NOT_BOUNDED_PLAIN_JSON",
    "PINNED_SOURCE_CONTRACT_MARKERS_NOT_EXACT",
    "SOURCE_HASH_FIELDS_NOT_EXACT",
    "GATE_TO_BUDGET_CROSS_BINDING_NOT_EXACT",
    "SOURCE_AUTHORITY_LOCK_NOT_EXACT",
    "SOURCE_SEMANTICS_NOT_COHERENT",
    "SOURCE_DOCUMENT_SET_INSPECTION_FAILED",
  ]);
  var BLOCKERS = Object.freeze([
    "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN",
    "MARKET_VALIDITY_UNPROVEN",
    "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
    "DOM_MOUNT_UNAUTHORIZED",
    "CURRENT_ADMISSION_LOCKED",
    "PAPER_UNAUTHORIZED",
    "LIVE_UNAUTHORIZED",
    "WRITER_UNAUTHORIZED",
  ]);
  var TOP_LEVEL_KEYS = Object.freeze([
    "schema_version",
    "static_fingerprint",
    "status",
    "contract_state",
    "presentation_state",
    "reason_code",
    "tone",
    "stage_order",
    "stages",
    "source",
    "metrics",
    "facts",
    "blockers",
    "authority",
    "presentation_hash",
  ]);
  var SOURCE_KEYS = Object.freeze([
    "uncertainty_gate_contract_hash",
    "uncertainty_gate_source_sha256",
    "budget_binding_contract_hash",
    "budget_binding_source_sha256",
    "embedded_uncertainty_gate_hash",
    "embedded_budget_binding_evaluation_hash",
    "uncertainty_gate_document_sha256",
    "budget_binding_document_sha256",
    "document_set_sha256",
  ]);
  var METRIC_KEYS = Object.freeze([
    "window_count",
    "dependence_edge_count",
    "cross_cluster_dependence_edge_count",
    "conservative_component_count",
    "preregistered_cluster_count",
    "active_cluster_count",
    "symbol_ticket_count",
    "conservative_weighted_strata_count",
  ]);
  var FACT_KEYS = Object.freeze([
    "bounded_plain_json_documents_verified",
    "pinned_contract_markers_verified",
    "gate_to_budget_cross_binding_verified",
    "source_authority_lock_verified",
    "local_document_hashes_computed",
    "raw_source_documents_embedded",
    "raw_window_audits_embedded",
    "raw_price_or_return_series_embedded",
    "dynamic_reclustering_performed",
    "external_independent_review_complete",
    "dom_mounted",
    "current_activated",
    "runtime_mutations_performed",
  ]);
  var AUTHORITY_KEYS = Object.freeze([
    "current_admission_allowed",
    "dom_mount_allowed",
    "effective_budget_activation_allowed",
    "http_registration_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_asset_loading_allowed",
    "writer_allowed",
  ]);

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) {
      return value;
    }
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

  function exactHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function hashOrNull(value) {
    return value === null || exactHash(value);
  }

  function nonNegativeOrNull(value) {
    return value === null
      || (typeof value === "number" && Number.isFinite(value) && value >= 0);
  }

  function exactStringArray(value, expected) {
    return Array.isArray(value)
      && value.length === expected.length
      && value.every(function (item, index) { return item === expected[index]; });
  }

  function authorityExact(value) {
    return exactKeys(value, AUTHORITY_KEYS)
      && AUTHORITY_KEYS.every(function (key) { return value[key] === false; });
  }

  function sourceExact(value, known) {
    if (!exactKeys(value, SOURCE_KEYS)
      || !SOURCE_KEYS.every(function (key) { return hashOrNull(value[key]); })) {
      return false;
    }
    if (!known) return true;
    return value.uncertainty_gate_contract_hash
        === presentation.UNCERTAINTY_GATE_CONTRACT_HASH
      && value.uncertainty_gate_source_sha256
        === presentation.UNCERTAINTY_GATE_SOURCE_SHA256
      && value.budget_binding_contract_hash
        === presentation.BUDGET_BINDING_CONTRACT_HASH
      && value.budget_binding_source_sha256
        === presentation.BUDGET_BINDING_SOURCE_SHA256
      && SOURCE_KEYS.every(function (key) { return exactHash(value[key]); });
  }

  function metricsExact(value, known) {
    if (!known) return value === null;
    return exactKeys(value, METRIC_KEYS)
      && METRIC_KEYS.every(function (key) {
        return nonNegativeOrNull(value[key]);
      });
  }

  function factsExact(value, known) {
    if (!exactKeys(value, FACT_KEYS)
      || !FACT_KEYS.every(function (key) {
        return typeof value[key] === "boolean";
      })) {
      return false;
    }
    var permanentFalse = [
      "raw_source_documents_embedded",
      "raw_window_audits_embedded",
      "raw_price_or_return_series_embedded",
      "dynamic_reclustering_performed",
      "external_independent_review_complete",
      "dom_mounted",
      "current_activated",
      "runtime_mutations_performed",
    ];
    if (!permanentFalse.every(function (key) { return value[key] === false; })) {
      return false;
    }
    return !known || [
      "bounded_plain_json_documents_verified",
      "pinned_contract_markers_verified",
      "gate_to_budget_cross_binding_verified",
      "source_authority_lock_verified",
      "local_document_hashes_computed",
    ].every(function (key) { return value[key] === true; });
  }

  function stagesExact(value, known) {
    if (!Array.isArray(value) || value.length !== STAGE_ORDER.length) return false;
    var expectedStates = known
      ? ["HASH_BOUND_LOCAL", "OPEN", "SYNTHETIC_UNMOUNTED", "UNAUTHORIZED"]
      : null;
    return value.every(function (stage, index) {
      if (!exactKeys(stage, ["axis", "state", "reason_code"])
        || stage.axis !== STAGE_ORDER[index]
        || typeof stage.reason_code !== "string") {
        return false;
      }
      if (known) return stage.state === expectedStates[index];
      if (stage.axis === "SOURCE") {
        return ["HASH_BOUND_LOCAL", "UNKNOWN"].includes(stage.state);
      }
      if (stage.axis === "GAP") return stage.state === "OPEN";
      if (stage.axis === "MATURITY") return stage.state === "UNKNOWN";
      return stage.state === "UNAUTHORIZED";
    });
  }

  function verifyNeutralPresentationV1(candidate) {
    if (!strictCanonical.verifySealedDocument(candidate, "presentation_hash")
      || !exactKeys(candidate, TOP_LEVEL_KEYS)
      || candidate.schema_version !== presentation.SCHEMA_VERSION
      || candidate.static_fingerprint !== presentation.STATIC_FINGERPRINT
      || candidate.tone !== "NEUTRAL"
      || !exactStringArray(candidate.stage_order, STAGE_ORDER)
      || !exactStringArray(candidate.blockers, BLOCKERS)
      || !authorityExact(candidate.authority)
      || !REASON_CODES.includes(candidate.reason_code)) {
      return false;
    }
    var known = candidate.status === "BLOCKED";
    if (!known && candidate.status !== "UNKNOWN") return false;
    if (known) {
      if (candidate.contract_state !== "LOCAL_RESEARCH_EVIDENCE"
        || !PRESENTATION_STATES.includes(candidate.presentation_state)
        || candidate.reason_code
          !== "LOCAL_RESEARCH_EVIDENCE_PRESENTED_PERMISSION_LOCKED") {
        return false;
      }
    } else if (candidate.contract_state !== "UNKNOWN"
      || candidate.presentation_state !== "UNKNOWN") {
      return false;
    }
    return sourceExact(candidate.source, known)
      && metricsExact(candidate.metrics, known)
      && factsExact(candidate.facts, known)
      && stagesExact(candidate.stages, known);
  }

  function shortHash(value) {
    return exactHash(value) ? value.slice(0, 10) : "unknown";
  }

  function formatMetric(value) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      return "not available";
    }
    return String(Number(value.toFixed(6)));
  }

  function stateCopy(state) {
    var copies = {
      CROSS_CLUSTER_DEPENDENCE_VETO: {
        status: "LOCAL VETO",
        title: "Cross-cluster dependence stops budget review",
        summary: "At least one conservative dependence component crosses the preregistered partition. A new preregistration is required before risk-increasing budget review.",
      },
      RISK_REDUCTION_ONLY: {
        status: "REDUCTION ONLY",
        title: "Only the exact risk-reduction path is retained",
        summary: "The local contract preserves a reduction-only path. It does not grant admission, execution, or writer authority.",
      },
      RESEARCH_BUDGET_CONTRACT_OBSERVED: {
        status: "RESEARCH CONTRACT",
        title: "A research-budget contract is locally observed",
        summary: "The local gate and budget binding are hash-bound. Market validity, external review, and every operational permission remain open gaps.",
      },
      RESEARCH_BUDGET_BLOCK_OBSERVED: {
        status: "LOCAL BLOCK",
        title: "The research budget remains blocked",
        summary: "The budget block is preserved as evidence rather than converted into permission or an execution path.",
      },
      DOWNSTREAM_BUDGET_CHAIN_BLOCK: {
        status: "CHAIN BLOCK",
        title: "The downstream budget chain stops locally",
        summary: "The dependence gate is known, but a downstream budget prerequisite blocks further research-budget evaluation.",
      },
    };
    return copies[state] || {
      status: "SOURCE UNKNOWN",
      title: "Correlation-budget evidence is unavailable",
      summary: "The sealed presentation contract is unknown. No source, maturity, or budget conclusion can be inferred.",
    };
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "neutral",
      card_id: "hakimi-uncertainty-budget-card-v1-unknown",
      kicker: "DEPENDENCE / BUDGET / AUTHORITY",
      status_label: "SOURCE UNKNOWN",
      title: "Correlation-budget evidence is unavailable",
      summary: "The sealed presentation contract is unknown. No source, maturity, or budget conclusion can be inferred.",
      source_receipt: "unknown",
      metrics: [],
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "GAP"
            ? "OPEN"
            : axis === "PERMISSION"
              ? "UNAUTHORIZED"
              : "UNKNOWN",
          detail: axis === "PERMISSION"
            ? "CURRENT_PAPER_LIVE_AND_WRITER_LOCKED"
            : "UNKNOWN",
        };
      }),
      gaps: [
        "Source contract is unavailable.",
        "Market validity and external review are unproven.",
        "DOM mount and operational authority remain unavailable.",
      ],
      permission_note: "Research display only. Current, paper, live, writer, route, and mount authority remain unavailable.",
    });
  }

  function buildNeutralBudgetCardViewModelV1(candidate) {
    if (!verifyNeutralPresentationV1(candidate) || candidate.status === "UNKNOWN") {
      return unknownViewModel();
    }
    var copy = stateCopy(candidate.presentation_state);
    var receipt = shortHash(candidate.source.document_set_sha256);
    return deepFreeze({
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN_RESEARCH_ONLY",
      tone: "neutral",
      card_id: "hakimi-uncertainty-budget-card-v1-" + receipt,
      kicker: "DEPENDENCE / BUDGET / AUTHORITY",
      status_label: copy.status,
      title: copy.title,
      summary: copy.summary,
      source_receipt: receipt,
      metrics: [
        { label: "Preregistered windows", value: formatMetric(candidate.metrics.window_count) },
        { label: "Dependence edges", value: formatMetric(candidate.metrics.dependence_edge_count) },
        { label: "Cross-cluster edges", value: formatMetric(candidate.metrics.cross_cluster_dependence_edge_count) },
        { label: "Conservative components", value: formatMetric(candidate.metrics.conservative_component_count) },
        { label: "Budget symbol tickets", value: formatMetric(candidate.metrics.symbol_ticket_count) },
        { label: "Weighted strata count", value: formatMetric(candidate.metrics.conservative_weighted_strata_count) },
      ],
      stages: candidate.stages.map(function (stage) {
        return {
          axis: stage.axis,
          state: stage.state,
          detail: stage.reason_code,
        };
      }),
      gaps: [
        "Window-label issuer binding is unproven.",
        "Market validity and external review remain open.",
        "DOM mount and operational authority remain unavailable.",
      ],
      permission_note: "Research display only. Current, paper, live, writer, route, and mount authority remain unavailable.",
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

  function dataState(value) {
    return String(value || "unknown").toLowerCase().replace(/_/g, "-");
  }

  function renderNeutralBudgetCardV1(candidate) {
    var view = buildNeutralBudgetCardViewModelV1(candidate);
    var id = escapeHtml(view.card_id);
    var metrics = view.metrics.map(function (metric) {
      return '<div class="hakimi-uncertainty-budget-card-v1__metric"><dt>'
        + escapeHtml(metric.label) + "</dt><dd>" + escapeHtml(metric.value)
        + "</dd></div>";
    }).join("");
    var stages = view.stages.map(function (stage, index) {
      return '<li class="hakimi-uncertainty-budget-card-v1__stage" data-state="'
        + escapeHtml(dataState(stage.state)) + '"><span aria-hidden="true">'
        + String(index + 1).padStart(2, "0") + "</span><div><strong>"
        + escapeHtml(stage.axis) + "</strong><span>" + escapeHtml(stage.state)
        + "</span><small>" + escapeHtml(stage.detail) + "</small></div></li>";
    }).join("");
    var gaps = view.gaps.map(function (gap) {
      return "<li>" + escapeHtml(gap) + "</li>";
    }).join("");
    var metricsSection = view.metrics.length
      ? '<section class="hakimi-uncertainty-budget-card-v1__metrics" aria-labelledby="'
        + id + '__metrics-title"><h3 id="' + id
        + '__metrics-title">Evidence counts</h3><dl>' + metrics + "</dl></section>"
      : '<p class="hakimi-uncertainty-budget-card-v1__metrics-empty">No bounded metrics are available.</p>';

    return '<article class="hakimi-uncertainty-budget-card-v1" data-tone="neutral" aria-labelledby="'
      + id + '__title" aria-describedby="' + id + '__summary"><header class="hakimi-uncertainty-budget-card-v1__header"><div><p>'
      + escapeHtml(view.kicker) + '<\/p><h2 id="' + id + '__title">'
      + escapeHtml(view.title) + '</h2></div><p class="hakimi-uncertainty-budget-card-v1__status" aria-label="Local evidence state">'
      + escapeHtml(view.status_label) + '</p></header><p id="' + id
      + '__summary" class="hakimi-uncertainty-budget-card-v1__summary">'
      + escapeHtml(view.summary) + "</p>" + metricsSection
      + '<section class="hakimi-uncertainty-budget-card-v1__path" aria-labelledby="'
      + id + '__path-title"><h3 id="' + id
      + '__path-title">Evidence path</h3><ol>' + stages
      + '</ol></section><section class="hakimi-uncertainty-budget-card-v1__gaps" aria-labelledby="'
      + id + '__gaps-title"><h3 id="' + id
      + '__gaps-title">Open gaps</h3><ul>' + gaps
      + '</ul></section><footer class="hakimi-uncertainty-budget-card-v1__footer"><span>source '
      + escapeHtml(view.source_receipt) + "</span><p>"
      + escapeHtml(view.permission_note) + "</p></footer></article>";
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION: CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT: CARD_STATIC_FINGERPRINT,
    PRESENTATION_SOURCE_SHA256: PRESENTATION_SOURCE_SHA256,
    STAGE_ORDER: STAGE_ORDER,
    buildNeutralBudgetCardViewModelV1: buildNeutralBudgetCardViewModelV1,
    renderNeutralBudgetCardV1: renderNeutralBudgetCardV1,
    verifyNeutralPresentationV1: verifyNeutralPresentationV1,
  });
});
