(function (root, factory) {
  "use strict";

  if (typeof module === "object" && module.exports) {
    module.exports = factory(
      require(
        "./evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js"
      )
    );
    return;
  }
  root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1 = factory(
    root.HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1
  );
})(typeof globalThis === "object" ? globalThis : this, function (delivery) {
  "use strict";

  if (
    !delivery ||
    typeof delivery.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1 !==
      "function"
  ) {
    throw new Error(
      "admission-budget in-memory delivery v1 dependency is required"
    );
  }

  var BRIDGE_SCHEMA_VERSION =
    "portfolio-correlation-admission-effective-budget-bridge-v1";
  var BRIDGE_STATIC_FINGERPRINT =
    "20260823-portfolio-correlation-admission-effective-budget-bridge-v1-unmounted-lock-1";
  var STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  var TIER_ORDER = Object.freeze([
    "INPUT_SNAPSHOT",
    "ADMISSION_V2_EXACT",
    "EFFECTIVE_BUDGET_V3_EXACT",
    "CROSS_SOURCE_BINDING",
    "ADMISSION_V2_DECISION",
    "EFFECTIVE_BUDGET_V3_DECISION",
    "PERMISSION",
  ]);

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function deepFreeze(value) {
    if (Array.isArray(value)) {
      value.forEach(deepFreeze);
      return Object.freeze(value);
    }
    if (value && typeof value === "object") {
      Object.keys(value).forEach(function (key) {
        deepFreeze(value[key]);
      });
      return Object.freeze(value);
    }
    return value;
  }

  function shortHash(value) {
    return typeof value === "string" && value.length === 64
      ? value.slice(0, 10)
      : "unknown";
  }

  function unknownTiers() {
    return TIER_ORDER.map(function (tier) {
      return {
        tier: tier,
        state: "NOT_EVALUATED",
        detail: "UNKNOWN",
      };
    });
  }

  function unknownStages() {
    return STAGE_ORDER.map(function (axis) {
      return {
        axis: axis,
        state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
        detail:
          axis === "PERMISSION"
            ? "NO_PERMISSION_CAN_BE_INFERRED"
            : "UNKNOWN",
      };
    });
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: BRIDGE_SCHEMA_VERSION,
      static_fingerprint: BRIDGE_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "STRUCTURAL REVIEW / RESEARCH BINDING",
      title: "The bridge evidence is unavailable",
      summary:
        "No exact admission-budget delivery envelope is available. Topology, exposure, maturity, and permission remain unknown.",
      status_label: "SOURCE UNKNOWN",
      metrics: [],
      piers: {
        admission: {
          label: "ADMISSION TOPOLOGY",
          state: "NOT_EVALUATED",
          detail: "UNKNOWN",
        },
        binding: {
          label: "SHARED SOURCE BINDING",
          state: "NOT_EVALUATED",
          detail: "UNKNOWN",
        },
        budget: {
          label: "EFFECTIVE BUDGET",
          state: "NOT_EVALUATED",
          detail: "UNKNOWN",
        },
      },
      tiers: unknownTiers(),
      stages: unknownStages(),
      blocker_count: 0,
      permission_note:
        "Research display only. Current, paper, live, render, and execution authority remain unavailable.",
    });
  }

  function toneFor(payload) {
    if (payload.binding_status === "PASS") {
      return "bounded";
    }
    if (payload.first_blocking_tier === "ADMISSION_V2_DECISION") {
      return "topology";
    }
    if (
      payload.first_blocking_tier ===
      "EFFECTIVE_BUDGET_V3_DECISION"
    ) {
      return "exposure";
    }
    return "source";
  }

  function titleFor(tone) {
    if (tone === "bounded") {
      return "Topology and exposure support one local bridge";
    }
    if (tone === "topology") {
      return "The topology pier does not carry";
    }
    if (tone === "exposure") {
      return "The exposure pier exceeds its local budget";
    }
    return "The shared source span is blocked";
  }

  function summaryFor(tone) {
    if (tone === "bounded") {
      return "Admission topology and effective-bet budget both pass on one exact source chain. The bridge remains an unmounted research candidate.";
    }
    if (tone === "topology") {
      return "The admission decision blocks before portfolio exposure can be interpreted as permission.";
    }
    if (tone === "exposure") {
      return "The correlation topology is locally acceptable, but the effective-bet budget blocks the proposed exposure.";
    }
    return "An exact predecessor or cross-source tier blocks the combined research conclusion.";
  }

  function statusLabelFor(tone) {
    if (tone === "bounded") {
      return "LOCAL ALIGNMENT";
    }
    if (tone === "topology") {
      return "TOPOLOGY BLOCK";
    }
    if (tone === "exposure") {
      return "EXPOSURE BLOCK";
    }
    return "SOURCE BLOCK";
  }

  function buildStages(payload) {
    var clear = payload.binding_status === "PASS";
    return [
      {
        axis: "SOURCE",
        state: "KNOWN",
        detail: "EXACT_IN_MEMORY_PAYLOAD_V1",
      },
      {
        axis: "GAP",
        state: clear ? "LOCAL_CLEAR" : "OPEN",
        detail: clear
          ? "NO_LOCAL_BLOCKER"
          : payload.first_blocking_tier,
      },
      {
        axis: "MATURITY",
        state: "CANDIDATE_ONLY",
        detail: "UNMOUNTED_BRIDGE_V1",
      },
      {
        axis: "PERMISSION",
        state: "UNAUTHORIZED",
        detail: "NO_CURRENT_PAPER_LIVE_RENDER_OR_EXECUTION_AUTHORITY",
      },
    ];
  }

  function buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
    envelope
  ) {
    var payload =
      delivery.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
        envelope
      );
    if (!payload) {
      return unknownViewModel();
    }

    var tone = toneFor(payload);
    return deepFreeze({
      schema_version: BRIDGE_SCHEMA_VERSION,
      static_fingerprint: BRIDGE_STATIC_FINGERPRINT,
      contract_state: "KNOWN",
      tone: tone,
      kicker: "STRUCTURAL REVIEW / RESEARCH BINDING",
      title: titleFor(tone),
      summary: summaryFor(tone),
      status_label: statusLabelFor(tone),
      metrics: [
        {
          label: "Admission topology",
          value: payload.admission_v2_status,
        },
        {
          label: "Effective budget",
          value: payload.effective_budget_v3_status,
        },
        {
          label: "Binding",
          value: shortHash(payload.source.binding_hash),
        },
        {
          label: "Proposal scope",
          value: shortHash(payload.source.proposal_scope_hash),
        },
      ],
      piers: {
        admission: {
          label: "ADMISSION TOPOLOGY",
          state: payload.admission_v2_status,
          detail: payload.checks.admission_v2_exact
            ? "EXACT"
            : "NOT_EVALUATED",
        },
        binding: {
          label: "SHARED SOURCE BINDING",
          state: payload.checks.cross_source_hashes_exact
            ? "PASS"
            : "BLOCK",
          detail:
            payload.binding_status === "PASS"
              ? "ONE_SHARED_HASH_CHAIN"
              : payload.first_blocking_tier,
        },
        budget: {
          label: "EFFECTIVE BUDGET",
          state: payload.effective_budget_v3_status,
          detail: payload.checks.effective_budget_v3_exact
            ? "EXACT"
            : "NOT_EVALUATED",
        },
      },
      tiers: payload.tiers.map(function (row) {
        return {
          tier: row.tier,
          state: row.state,
          detail: row.detail,
        };
      }),
      stages: buildStages(payload),
      blocker_count: payload.blockers.length,
      permission_note:
        "Research display only. No current, paper, live, render, route, mount, or execution permission.",
    });
  }

  function metricMarkup(metric) {
    return (
      '<li class="hakimi-admission-budget-bridge-v1__metric">' +
      '<span class="hakimi-admission-budget-bridge-v1__metric-label">' +
      escapeHtml(metric.label) +
      "</span>" +
      '<strong class="hakimi-admission-budget-bridge-v1__metric-value">' +
      escapeHtml(metric.value) +
      "</strong>" +
      "</li>"
    );
  }

  function pierMarkup(pier, position) {
    return (
      '<article class="hakimi-admission-budget-bridge-v1__pier" data-state="' +
      escapeHtml(pier.state) +
      '">' +
      '<span class="hakimi-admission-budget-bridge-v1__pier-index">' +
      escapeHtml(position) +
      "</span>" +
      '<p class="hakimi-admission-budget-bridge-v1__pier-label">' +
      escapeHtml(pier.label) +
      "</p>" +
      '<strong class="hakimi-admission-budget-bridge-v1__pier-state">' +
      escapeHtml(pier.state) +
      "</strong>" +
      '<span class="hakimi-admission-budget-bridge-v1__pier-detail">' +
      escapeHtml(pier.detail) +
      "</span>" +
      "</article>"
    );
  }

  function tierMarkup(row, index) {
    return (
      '<li class="hakimi-admission-budget-bridge-v1__tier" data-state="' +
      escapeHtml(row.state) +
      '">' +
      '<span class="hakimi-admission-budget-bridge-v1__tier-index">' +
      escapeHtml(String(index + 1).padStart(2, "0")) +
      "</span>" +
      '<span class="hakimi-admission-budget-bridge-v1__tier-name">' +
      escapeHtml(row.tier) +
      "</span>" +
      '<strong class="hakimi-admission-budget-bridge-v1__tier-state">' +
      escapeHtml(row.state) +
      "</strong>" +
      "</li>"
    );
  }

  function stageMarkup(stage) {
    return (
      '<li class="hakimi-admission-budget-bridge-v1__stage" data-state="' +
      escapeHtml(stage.state) +
      '">' +
      '<span class="hakimi-admission-budget-bridge-v1__stage-axis">' +
      escapeHtml(stage.axis) +
      "</span>" +
      '<strong class="hakimi-admission-budget-bridge-v1__stage-state">' +
      escapeHtml(stage.state) +
      "</strong>" +
      '<small class="hakimi-admission-budget-bridge-v1__stage-detail">' +
      escapeHtml(stage.detail) +
      "</small>" +
      "</li>"
    );
  }

  function renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1(
    envelope
  ) {
    var model =
      buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
        envelope
      );
    var metrics = model.metrics.map(metricMarkup).join("");
    var tiers = model.tiers.map(tierMarkup).join("");
    var stages = model.stages.map(stageMarkup).join("");

    return (
      '<section class="hakimi-admission-budget-bridge-v1" data-tone="' +
      escapeHtml(model.tone) +
      '" aria-label="Admission and effective budget research bridge">' +
      '<div class="hakimi-admission-budget-bridge-v1__survey-line" aria-hidden="true"></div>' +
      '<header class="hakimi-admission-budget-bridge-v1__header">' +
      '<div class="hakimi-admission-budget-bridge-v1__heading">' +
      '<p class="hakimi-admission-budget-bridge-v1__kicker">' +
      escapeHtml(model.kicker) +
      "</p>" +
      '<h2 class="hakimi-admission-budget-bridge-v1__title">' +
      escapeHtml(model.title) +
      "</h2>" +
      '<p class="hakimi-admission-budget-bridge-v1__summary">' +
      escapeHtml(model.summary) +
      "</p>" +
      "</div>" +
      '<div class="hakimi-admission-budget-bridge-v1__status" aria-label="Local binding status">' +
      '<span class="hakimi-admission-budget-bridge-v1__status-mark" aria-hidden="true"></span>' +
      '<strong class="hakimi-admission-budget-bridge-v1__status-label">' +
      escapeHtml(model.status_label) +
      "</strong>" +
      '<small class="hakimi-admission-budget-bridge-v1__status-count">' +
      escapeHtml(String(model.blocker_count)) +
      " LOCAL BLOCKERS</small>" +
      "</div>" +
      "</header>" +
      '<ul class="hakimi-admission-budget-bridge-v1__metrics" aria-label="Hash-only bridge metrics">' +
      metrics +
      "</ul>" +
      '<div class="hakimi-admission-budget-bridge-v1__structure">' +
      pierMarkup(model.piers.admission, "01") +
      '<div class="hakimi-admission-budget-bridge-v1__span">' +
      '<div class="hakimi-admission-budget-bridge-v1__truss" aria-hidden="true">' +
      '<span></span><span></span><span></span><span></span><span></span>' +
      "</div>" +
      '<div class="hakimi-admission-budget-bridge-v1__lock" data-state="' +
      escapeHtml(model.piers.binding.state) +
      '">' +
      '<span class="hakimi-admission-budget-bridge-v1__lock-label">' +
      escapeHtml(model.piers.binding.label) +
      "</span>" +
      '<strong class="hakimi-admission-budget-bridge-v1__lock-state">' +
      escapeHtml(model.piers.binding.state) +
      "</strong>" +
      '<small class="hakimi-admission-budget-bridge-v1__lock-detail">' +
      escapeHtml(model.piers.binding.detail) +
      "</small>" +
      "</div>" +
      "</div>" +
      pierMarkup(model.piers.budget, "02") +
      "</div>" +
      '<ol class="hakimi-admission-budget-bridge-v1__tiers" aria-label="Ordered binding tiers">' +
      tiers +
      "</ol>" +
      '<ol class="hakimi-admission-budget-bridge-v1__stages" aria-label="Evidence governance stages">' +
      stages +
      "</ol>" +
      '<footer class="hakimi-admission-budget-bridge-v1__permission">' +
      '<span class="hakimi-admission-budget-bridge-v1__permission-key">PERMISSION LOCK</span>' +
      '<p class="hakimi-admission-budget-bridge-v1__permission-note">' +
      escapeHtml(model.permission_note) +
      "</p>" +
      "</footer>" +
      "</section>"
    );
  }

  return Object.freeze({
    BRIDGE_SCHEMA_VERSION: BRIDGE_SCHEMA_VERSION,
    BRIDGE_STATIC_FINGERPRINT: BRIDGE_STATIC_FINGERPRINT,
    STAGE_ORDER: STAGE_ORDER,
    TIER_ORDER: TIER_ORDER,
    buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1:
      buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1,
    renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1:
      renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1,
  });
});
