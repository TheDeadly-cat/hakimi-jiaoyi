(function (root, factory) {
  "use strict";

  var delivery = typeof module === "object" && module.exports
    ? require("./evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js")
    : root.HakimiPortfolioCorrelationAdmissionV2InMemoryDeliveryV1;
  var api = factory(delivery);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioCorrelationAdmissionRailV2 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (delivery) {
  "use strict";

  if (!delivery
    || typeof delivery.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1 !== "function"
    || typeof delivery.extractPortfolioCorrelationAdmissionV2PresentationPayloadV1 !== "function") {
    throw new Error("Portfolio correlation admission v2 delivery adapter is required");
  }

  var RAIL_SCHEMA_VERSION = "portfolio-correlation-admission-rail-v2";
  var RAIL_STATIC_FINGERPRINT =
    "20260823-portfolio-correlation-admission-rail-v2-unmounted-lock-1";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var TIER_ORDER = Object.freeze([
    "INPUT_SNAPSHOT",
    "INPUT_IDENTITY",
    "REPORT_UNIVERSE",
    "CORRELATION_PREREGISTRATION",
    "COMMON_UNIVERSE",
    "V1_ADMISSION",
    "PERMISSION",
  ]);
  var TIER_CHECKS = Object.freeze({
    INPUT_SNAPSHOT: ["input_snapshot_exact"],
    INPUT_IDENTITY: ["input_identity_exact"],
    REPORT_UNIVERSE: ["report_universe_contract_exact"],
    CORRELATION_PREREGISTRATION: ["correlation_preregistration_exact"],
    COMMON_UNIVERSE: ["common_universe_exact"],
    V1_ADMISSION: ["v1_admission_exact", "v1_admission_pass"],
    PERMISSION: ["evidence_has_no_execution_authority"],
  });

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.keys(value).forEach(function (key) { deepFreeze(value[key]); });
    return Object.freeze(value);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function shortHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value)
      ? value.slice(0, 10)
      : "unknown";
  }

  function tierState(checks, tier) {
    var values = TIER_CHECKS[tier].map(function (key) { return checks[key]; });
    if (values.some(function (value) { return value === false; })) return "BLOCK";
    if (values.every(function (value) { return value === true; })) return "PASS";
    return "NOT_EVALUATED";
  }

  function friendlyTier(value) {
    return String(value || "unknown").toLowerCase().replace(/_/g, " ");
  }

  function tierDetail(payload, tier, state) {
    if (tier === "COMMON_UNIVERSE") return payload.common_universe_status;
    if (tier === "V1_ADMISSION") {
      return payload.v1_admission_status === "BLOCK" && payload.v1_first_blocking_tier
        ? "BLOCK / " + payload.v1_first_blocking_tier
        : payload.v1_admission_status;
    }
    if (tier === "PERMISSION") return "LOCKED";
    return state;
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: RAIL_SCHEMA_VERSION,
      static_fingerprint: RAIL_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "UNIVERSE BINDING / RESEARCH ADMISSION V2",
      title: "Universe binding is unavailable",
      summary: "The in-memory delivery contract is unknown. No source, gap, maturity, or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN",
      candidate_hash_short: "unknown",
      source_hash_short: "unknown",
      payload_hash_short: "unknown",
      metrics: [],
      handshake: {
        report: { label: "REPORT UNIVERSE", state: "NOT_EVALUATED", detail: "UNKNOWN" },
        common: { label: "COMMON UNIVERSE", state: "NOT_EVALUATED", detail: "UNKNOWN" },
        correlation: { label: "CORRELATION PREREGISTRATION", state: "NOT_EVALUATED", detail: "UNKNOWN" },
      },
      tiers: TIER_ORDER.map(function (tier) {
        return { tier: tier, state: "NOT_EVALUATED", detail: "UNKNOWN" };
      }),
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail: axis === "PERMISSION" ? "NO_PERMISSION_CAN_BE_INFERRED" : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note: "Research display only. Current, paper, live, render, and execution authority remain unavailable.",
    });
  }

  function buildPortfolioCorrelationAdmissionRailViewModelV2(envelope) {
    if (!delivery.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(envelope)) {
      return unknownViewModel();
    }
    var payload = delivery.extractPortfolioCorrelationAdmissionV2PresentationPayloadV1(envelope);
    if (!payload) return unknownViewModel();

    var blocked = payload.status === "BLOCK";
    var commonState = tierState(payload.checks, "COMMON_UNIVERSE");
    var v1State = tierState(payload.checks, "V1_ADMISSION");
    var title;
    var summary;
    if (!blocked) {
      title = "One universe, then one admission path";
      summary = "The report and correlation preregistration describe the same tradable set. The v1 chain is locally clear; execution remains closed.";
    } else if (payload.first_blocking_tier === "COMMON_UNIVERSE") {
      title = "The evidence sets do not meet";
      summary = "The report universe and correlation preregistration differ. The v1 admission path remains unevaluated rather than inferred.";
    } else if (payload.first_blocking_tier === "V1_ADMISSION") {
      title = "The universe meets; admission still stops";
      summary = "The common universe is exact, but the unchanged v1 chain blocks at "
        + friendlyTier(payload.v1_first_blocking_tier) + ".";
    } else {
      title = "Evidence stops before universe binding";
      summary = "An upstream contract blocks the path. Dependent tiers remain unevaluated and permission remains closed.";
    }

    var tiers = TIER_ORDER.map(function (tier) {
      var state = tierState(payload.checks, tier);
      return { tier: tier, state: state, detail: tierDetail(payload, tier, state) };
    });
    var gapDetail = blocked ? payload.first_blocking_tier : "NO_LOCAL_BLOCKER";
    return deepFreeze({
      schema_version: RAIL_SCHEMA_VERSION,
      static_fingerprint: RAIL_STATIC_FINGERPRINT,
      contract_state: "KNOWN",
      tone: blocked ? "blocked" : "bounded",
      kicker: "UNIVERSE BINDING / RESEARCH ADMISSION V2",
      title: title,
      summary: summary,
      status_label: blocked ? "LOCAL BLOCK" : "LOCAL CLEAR",
      candidate_hash_short: shortHash(payload.candidate_hash),
      source_hash_short: shortHash(payload.source_report_hash),
      payload_hash_short: shortHash(payload.presentation_payload_hash),
      metrics: [
        { label: "Common universe", value: payload.common_universe_status },
        { label: "V1 admission", value: payload.v1_admission_status },
        { label: "Candidate", value: shortHash(payload.candidate_hash) },
        { label: "Source", value: shortHash(payload.source_report_hash) },
      ],
      handshake: {
        report: {
          label: "REPORT UNIVERSE",
          state: tierState(payload.checks, "REPORT_UNIVERSE"),
          detail: tierDetail(payload, "REPORT_UNIVERSE", tierState(payload.checks, "REPORT_UNIVERSE")),
        },
        common: {
          label: "COMMON UNIVERSE",
          state: commonState,
          detail: payload.common_universe_status,
        },
        correlation: {
          label: "CORRELATION PREREGISTRATION",
          state: tierState(payload.checks, "CORRELATION_PREREGISTRATION"),
          detail: tierDetail(payload, "CORRELATION_PREREGISTRATION", tierState(payload.checks, "CORRELATION_PREREGISTRATION")),
        },
      },
      tiers: tiers,
      stages: [
        { axis: "SOURCE", state: "KNOWN", detail: "EXACT_IN_MEMORY_PAYLOAD_V1" },
        { axis: "GAP", state: blocked ? "OPEN" : "LOCAL_CLEAR", detail: gapDetail },
        { axis: "MATURITY", state: "CANDIDATE_ONLY", detail: "UNMOUNTED_RAIL_V2" },
        { axis: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_CURRENT_PAPER_LIVE_RENDER_OR_EXECUTION_AUTHORITY" },
      ],
      blockers: payload.blockers.slice(),
      permission_note: "Research display only. No current, paper, live, render, route, mount, or execution permission.",
    });
  }

  function renderPortfolioCorrelationAdmissionRailV2(envelope) {
    var view = buildPortfolioCorrelationAdmissionRailViewModelV2(envelope);
    var handshake = [view.handshake.report, view.handshake.common, view.handshake.correlation]
      .map(function (item, index) {
        var role = index === 1 ? "gate" : "track";
        return '<div class="hakimi-correlation-v2-rail__handshake-' + role
          + '" data-state="' + escapeHtml(item.state.toLowerCase()) + '"><span>'
          + escapeHtml(item.label) + '</span><strong>' + escapeHtml(item.state)
          + '</strong><small>' + escapeHtml(item.detail) + '</small></div>';
      }).join("");
    var metrics = view.metrics.map(function (metric) {
      return '<li><span>' + escapeHtml(metric.label) + '</span><strong>'
        + escapeHtml(metric.value) + '</strong></li>';
    }).join("");
    var tiers = view.tiers.map(function (tier, index) {
      return '<li data-state="' + escapeHtml(tier.state.toLowerCase())
        + '"><span>' + String(index + 1).padStart(2, "0") + '</span><strong>'
        + escapeHtml(tier.tier) + '</strong><b>' + escapeHtml(tier.state)
        + '</b><small>' + escapeHtml(tier.detail) + '</small></li>';
    }).join("");
    var stages = view.stages.map(function (stage) {
      return '<li data-state="' + escapeHtml(stage.state.toLowerCase()) + '"><strong>'
        + escapeHtml(stage.axis) + '</strong><b>' + escapeHtml(stage.state)
        + '</b><small>' + escapeHtml(stage.detail) + '</small></li>';
    }).join("");
    var blockers = view.blockers.length
      ? '<ul class="hakimi-correlation-v2-rail__blockers">' + view.blockers.map(function (blocker) {
        return '<li>' + escapeHtml(blocker) + '</li>';
      }).join("") + '</ul>'
      : '<p class="hakimi-correlation-v2-rail__no-blocker">No local blocker in this candidate. Governance limits remain.</p>';

    return '<article class="hakimi-correlation-v2-rail" data-tone="'
      + escapeHtml(view.tone) + '" aria-label="Portfolio correlation common-universe admission rail"><header class="hakimi-correlation-v2-rail__header"><div><p>'
      + escapeHtml(view.kicker) + '</p><h2>' + escapeHtml(view.title)
      + '</h2></div><span class="hakimi-correlation-v2-rail__status">'
      + escapeHtml(view.status_label) + '</span></header><p class="hakimi-correlation-v2-rail__summary">'
      + escapeHtml(view.summary) + '</p><section class="hakimi-correlation-v2-rail__handshake" aria-label="Common universe handshake">'
      + handshake + '</section><ul class="hakimi-correlation-v2-rail__metrics">'
      + metrics + '</ul><ol class="hakimi-correlation-v2-rail__tiers" aria-label="Admission tiers">'
      + tiers + '</ol><ol class="hakimi-correlation-v2-rail__stages" aria-label="Evidence governance stages">'
      + stages + '</ol><section class="hakimi-correlation-v2-rail__gap" aria-label="Admission blockers"><h3>Gap ledger</h3>'
      + blockers + '</section><footer class="hakimi-correlation-v2-rail__footer"><span>payload '
      + escapeHtml(view.payload_hash_short) + '</span><span>'
      + escapeHtml(view.permission_note) + '</span></footer></article>';
  }

  return Object.freeze({
    RAIL_SCHEMA_VERSION: RAIL_SCHEMA_VERSION,
    RAIL_STATIC_FINGERPRINT: RAIL_STATIC_FINGERPRINT,
    STAGE_ORDER: STAGE_ORDER,
    TIER_ORDER: TIER_ORDER,
    buildPortfolioCorrelationAdmissionRailViewModelV2:
      buildPortfolioCorrelationAdmissionRailViewModelV2,
    renderPortfolioCorrelationAdmissionRailV2:
      renderPortfolioCorrelationAdmissionRailV2,
  });
});
