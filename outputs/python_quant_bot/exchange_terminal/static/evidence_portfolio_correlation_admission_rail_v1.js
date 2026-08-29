(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var api = factory(strictCanonical);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioCorrelationAdmissionRailV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical) {
  "use strict";

  if (!strictCanonical || typeof strictCanonical.verifySealedDocument !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }

  var ADMISSION_SCHEMA_VERSION = "portfolio-correlation-admission-v1";
  var RAIL_SCHEMA_VERSION = "portfolio-correlation-admission-rail-v1";
  var RAIL_STATIC_FINGERPRINT =
    "20260823-portfolio-correlation-admission-rail-v1-unmounted-lock-1";
  var STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  var TIER_ORDER = Object.freeze([
    "INPUT_IDENTITY",
    "BASE_ADMISSION",
    "CORRELATION_PREREGISTRATION",
    "CORRELATION_MATRIX",
    "COMPLETE_LINK",
    "STRATA_PREREGISTRATION",
    "STRATA_GATE",
    "PERMISSION",
  ]);
  var CHECK_KEYS = Object.freeze([
    "input_snapshot_exact",
    "input_identity_exact",
    "report_strict_canonical",
    "base_admission_exact",
    "correlation_preregistration_exact",
    "correlation_matrix_exact",
    "selection_cells_strict_canonical",
    "complete_link_gate_exact",
    "complete_link_gate_pass",
    "strata_preregistration_exact",
    "strata_gate_exact",
    "strata_gate_pass",
    "evidence_has_no_execution_authority",
  ]);
  var FLOW_CHECKS = Object.freeze([
    { key: "input_identity_exact", tier: "INPUT_IDENTITY" },
    { key: "report_strict_canonical", tier: "BASE_ADMISSION" },
    { key: "base_admission_exact", tier: "BASE_ADMISSION" },
    { key: "correlation_preregistration_exact", tier: "CORRELATION_PREREGISTRATION" },
    { key: "correlation_matrix_exact", tier: "CORRELATION_MATRIX" },
    { key: "selection_cells_strict_canonical", tier: "CORRELATION_MATRIX" },
    { key: "complete_link_gate_exact", tier: "COMPLETE_LINK" },
    { key: "complete_link_gate_pass", tier: "COMPLETE_LINK" },
    { key: "strata_preregistration_exact", tier: "STRATA_PREREGISTRATION" },
    { key: "strata_gate_exact", tier: "STRATA_GATE" },
    { key: "strata_gate_pass", tier: "STRATA_GATE" },
  ]);
  var EVIDENCE_HASH_CHECKS = Object.freeze({
    source_report_hash: "report_strict_canonical",
    base_admission_hash: "base_admission_exact",
    correlation_preregistration_hash: "correlation_preregistration_exact",
    correlation_matrix_hash: "correlation_matrix_exact",
    selection_cells_hash: "selection_cells_strict_canonical",
    complete_link_gate_hash: "complete_link_gate_exact",
    strata_preregistration_hash: "strata_preregistration_exact",
    strata_gate_hash: "strata_gate_exact",
  });
  var TIER_CHECKS = Object.freeze({
    INPUT_IDENTITY: ["input_identity_exact"],
    BASE_ADMISSION: ["report_strict_canonical", "base_admission_exact"],
    CORRELATION_PREREGISTRATION: ["correlation_preregistration_exact"],
    CORRELATION_MATRIX: ["correlation_matrix_exact", "selection_cells_strict_canonical"],
    COMPLETE_LINK: ["complete_link_gate_exact", "complete_link_gate_pass"],
    STRATA_PREREGISTRATION: ["strata_preregistration_exact"],
    STRATA_GATE: ["strata_gate_exact", "strata_gate_pass"],
    PERMISSION: ["evidence_has_no_execution_authority"],
  });

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

  function isTriState(value) {
    return value === true || value === false || value === null;
  }

  function exactStringArray(value) {
    return Array.isArray(value) && value.every(function (item) {
      return typeof item === "string";
    });
  }

  function fixedBoundary(candidate) {
    return candidate.independent_vote_policy
        === "AT_MOST_ONE_VOTE_PER_PREREGISTERED_CLUSTER_WITH_STRATA_GATE"
      && candidate.raw_report_embedded === false
      && candidate.raw_correlation_evidence_embedded === false
      && candidate.consumer_only === true
      && candidate.manual_review_required === true
      && candidate.current_writer_activation_allowed === false
      && candidate.current_admission_allowed === false
      && candidate.automatic_internal_backtest_activation_allowed === false
      && candidate.paper_admission_status === "BLOCKED"
      && candidate.research_only === true
      && exactKeys(candidate.permissions, ["live_order_allowed", "paper_authorized"])
      && candidate.permissions.paper_authorized === false
      && candidate.permissions.live_order_allowed === false;
  }

  function validSnapshotFailure(candidate) {
    var allChecksFalse = CHECK_KEYS.every(function (key) {
      return candidate.checks[key] === false;
    });
    var allHashesEmpty = Object.keys(EVIDENCE_HASH_CHECKS).every(function (key) {
      return candidate.evidence_hashes[key] === "";
    });
    return candidate.status === "BLOCK"
      && candidate.admission_state === "CORRELATION_EVIDENCE_BLOCKED"
      && candidate.first_blocking_tier === "INPUT_SNAPSHOT"
      && candidate.base_admission_status === "NOT_EVALUATED"
      && candidate.complete_link_status === "NOT_EVALUATED"
      && candidate.strata_preregistration_status === "NOT_EVALUATED"
      && candidate.strata_gate_status === "NOT_EVALUATED"
      && candidate.blockers.length === 1
      && candidate.blockers[0] === "evidence_snapshot_failed"
      && allChecksFalse
      && allHashesEmpty;
  }

  function validFlow(candidate) {
    var checks = candidate.checks;
    var firstFalseIndex = -1;
    for (var index = 0; index < FLOW_CHECKS.length; index += 1) {
      if (checks[FLOW_CHECKS[index].key] === false) {
        firstFalseIndex = index;
        break;
      }
    }

    if (firstFalseIndex !== -1) {
      for (var later = firstFalseIndex + 1; later < FLOW_CHECKS.length; later += 1) {
        if (checks[FLOW_CHECKS[later].key] !== null) return false;
      }
    } else if (FLOW_CHECKS.some(function (item) { return checks[item.key] !== true; })) {
      return false;
    }

    var authorityBlocked = checks.evidence_has_no_execution_authority === false;
    var expectedFirstTier = firstFalseIndex === -1
      ? (authorityBlocked ? "PERMISSION" : null)
      : FLOW_CHECKS[firstFalseIndex].tier;
    var passed = expectedFirstTier === null;
    if (candidate.first_blocking_tier !== expectedFirstTier
      || candidate.status !== (passed ? "PASS" : "BLOCK")
      || candidate.admission_state !== (
        passed
          ? "CORRELATION_AND_PREREGISTERED_STRATA_VERIFIED_RESEARCH_ONLY"
          : "CORRELATION_EVIDENCE_BLOCKED"
      )) return false;
    if (passed ? candidate.blockers.length !== 0 : candidate.blockers.length === 0) return false;

    var expectedComplete = checks.complete_link_gate_exact === null
      ? "NOT_EVALUATED"
      : (checks.complete_link_gate_exact === false
        ? "INVALID"
        : (checks.complete_link_gate_pass ? "PASS" : "BLOCK"));
    var expectedStrataPreregistration = checks.strata_preregistration_exact === null
      ? "NOT_EVALUATED"
      : (checks.strata_preregistration_exact ? "PASS" : "INVALID");
    var expectedStrataGate = checks.strata_gate_exact === null
      ? "NOT_EVALUATED"
      : (checks.strata_gate_exact === false
        ? "INVALID"
        : (checks.strata_gate_pass ? "PASS" : "BLOCK"));
    if (candidate.complete_link_status !== expectedComplete
      || candidate.strata_preregistration_status !== expectedStrataPreregistration
      || candidate.strata_gate_status !== expectedStrataGate) return false;
    if (checks.base_admission_exact === true
      && candidate.base_admission_status !== "INTERNAL_BACKTEST_READY") return false;
    if (checks.base_admission_exact === false
      && ["INTERNAL_BACKTEST_BLOCKED", ""].indexOf(candidate.base_admission_status) === -1) {
      return false;
    }
    return true;
  }

  function validEvidenceHashes(candidate) {
    return Object.keys(EVIDENCE_HASH_CHECKS).every(function (hashKey) {
      var check = candidate.checks[EVIDENCE_HASH_CHECKS[hashKey]];
      return check === true
        ? isHash(candidate.evidence_hashes[hashKey])
        : candidate.evidence_hashes[hashKey] === "";
    });
  }

  function verifyPortfolioCorrelationAdmissionV1(candidate) {
    if (!strictCanonical.verifySealedDocument(candidate, "correlation_admission_hash")
      || !exactKeys(candidate, [
        "admission_state", "automatic_internal_backtest_activation_allowed",
        "base_admission_status", "blockers", "checks", "complete_link_status",
        "consumer_only", "correlation_admission_hash", "current_admission_allowed",
        "current_writer_activation_allowed", "evidence_hashes", "first_blocking_tier",
        "independent_vote_policy", "lane", "manual_review_required",
        "paper_admission_status", "permissions", "raw_correlation_evidence_embedded",
        "raw_report_embedded", "research_only", "schema_version", "status",
        "strata_gate_status", "strata_preregistration_status", "strategy_id", "variant_id",
      ])) return false;
    if (candidate.schema_version !== ADMISSION_SCHEMA_VERSION
      || ["PASS", "BLOCK"].indexOf(candidate.status) === -1
      || typeof candidate.strategy_id !== "string"
      || typeof candidate.variant_id !== "string"
      || ["RAW_EXCESS", "RISK_ADJUSTED", ""].indexOf(candidate.lane) === -1
      || !exactStringArray(candidate.blockers)
      || !exactKeys(candidate.checks, CHECK_KEYS)
      || !CHECK_KEYS.every(function (key) { return isTriState(candidate.checks[key]); })
      || !exactKeys(candidate.evidence_hashes, Object.keys(EVIDENCE_HASH_CHECKS))
      || !fixedBoundary(candidate)) return false;

    if (candidate.checks.input_snapshot_exact === false) {
      return validSnapshotFailure(candidate);
    }
    return candidate.checks.input_snapshot_exact === true
      && candidate.strategy_id.length > 0
      && candidate.strategy_id === candidate.strategy_id.trim()
      && candidate.variant_id.length > 0
      && candidate.variant_id === candidate.variant_id.trim()
      && candidate.lane !== ""
      && validFlow(candidate)
      && validEvidenceHashes(candidate);
  }

  function tierState(checks, tier) {
    var values = TIER_CHECKS[tier].map(function (key) { return checks[key]; });
    if (values.some(function (value) { return value === false; })) return "BLOCK";
    if (values.every(function (value) { return value === true; })) return "PASS";
    return "NOT_EVALUATED";
  }

  function friendlyTier(tier) {
    return String(tier || "UNKNOWN").toLowerCase().replace(/_/g, " ");
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) : "unknown";
  }

  function displayBaseStatus(value) {
    if (value === "INTERNAL_BACKTEST_READY") return "PASS";
    if (value === "INTERNAL_BACKTEST_BLOCKED") return "BLOCK";
    return value || "UNKNOWN";
  }

  function unknownViewModel() {
    return deepFreeze({
      schema_version: RAIL_SCHEMA_VERSION,
      static_fingerprint: RAIL_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "PORTFOLIO ADMISSION / CORRELATION HIERARCHY",
      title: "Admission hierarchy is unavailable",
      summary: "The candidate contract is unknown. No local evidence or permission conclusion can be inferred.",
      status_label: "SOURCE UNKNOWN",
      identity: "unknown / unknown",
      lane: "UNKNOWN",
      candidate_hash_short: "unknown",
      metrics: [],
      tiers: TIER_ORDER.map(function (tier) {
        return { tier: tier, state: "NOT_EVALUATED", detail: "UNKNOWN" };
      }),
      stages: STAGE_ORDER.map(function (axis) {
        return {
          axis: axis,
          state: axis === "PERMISSION" ? "UNAUTHORIZED" : "UNKNOWN",
          detail: axis === "PERMISSION"
            ? "NO_PERMISSION_CAN_BE_INFERRED"
            : "UNKNOWN",
        };
      }),
      blockers: [],
      permission_note: "Research display only. Current, paper, live, and execution authority remain unavailable.",
    });
  }

  function buildPortfolioCorrelationAdmissionRailViewModelV1(candidate) {
    if (!verifyPortfolioCorrelationAdmissionV1(candidate)) return unknownViewModel();
    var blocked = candidate.status === "BLOCK";
    var tiers = TIER_ORDER.map(function (tier) {
      var state = tierState(candidate.checks, tier);
      var detail = tier === "BASE_ADMISSION"
        ? displayBaseStatus(candidate.base_admission_status)
        : (tier === "COMPLETE_LINK"
          ? candidate.complete_link_status
          : (tier === "STRATA_PREREGISTRATION"
            ? candidate.strata_preregistration_status
            : (tier === "STRATA_GATE" ? candidate.strata_gate_status : state)));
      return { tier: tier, state: state, detail: detail };
    });
    return deepFreeze({
      schema_version: RAIL_SCHEMA_VERSION,
      static_fingerprint: RAIL_STATIC_FINGERPRINT,
      contract_state: "KNOWN",
      tone: blocked ? "blocked" : "bounded",
      kicker: "PORTFOLIO ADMISSION / CORRELATION HIERARCHY",
      title: blocked
        ? "Evidence stops at " + friendlyTier(candidate.first_blocking_tier)
        : "Correlation hierarchy is locally clear",
      summary: blocked
        ? "The first failed tier stops all dependent checks. Later tiers remain unevaluated rather than inferred."
        : "Cluster and preregistered-strata checks are locally clear. Activation and trading authority remain closed.",
      status_label: blocked ? "LOCAL BLOCK" : "LOCAL CLEAR",
      identity: candidate.strategy_id + " / " + candidate.variant_id,
      lane: candidate.lane,
      candidate_hash_short: shortHash(candidate.correlation_admission_hash),
      metrics: [
        { label: "Base admission", value: displayBaseStatus(candidate.base_admission_status) },
        { label: "Complete-link", value: candidate.complete_link_status },
        { label: "Strata prereg", value: candidate.strata_preregistration_status },
        { label: "Strata gate", value: candidate.strata_gate_status },
      ],
      tiers: tiers,
      stages: [
        { axis: "SOURCE", state: "KNOWN", detail: "EXACT_HASH_SEALED_ADMISSION_V1" },
        {
          axis: "GAP",
          state: blocked ? "OPEN" : "LOCAL_CLEAR",
          detail: blocked ? candidate.first_blocking_tier : "NO_LOCAL_BLOCKER",
        },
        { axis: "MATURITY", state: "CANDIDATE_ONLY", detail: "UNMOUNTED_ADMISSION_RAIL_V1" },
        { axis: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_CURRENT_PAPER_LIVE_OR_EXECUTION_AUTHORITY" },
      ],
      blockers: candidate.blockers.slice(),
      permission_note: "Research display only. No current, paper, live, execution, route, or mount permission.",
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

  function renderPortfolioCorrelationAdmissionRailV1(candidate) {
    var view = buildPortfolioCorrelationAdmissionRailViewModelV1(candidate);
    var metrics = view.metrics.map(function (metric) {
      return '<li class="hakimi-admission-rail-v1__metric"><span>'
        + escapeHtml(metric.label) + "</span><strong>" + escapeHtml(metric.value)
        + "</strong></li>";
    }).join("");
    var tiers = view.tiers.map(function (tier, index) {
      return '<li class="hakimi-admission-rail-v1__tier" data-state="'
        + escapeHtml(tier.state.toLowerCase()) + '"><span>'
        + String(index + 1).padStart(2, "0") + "</span><strong>"
        + escapeHtml(tier.tier) + "</strong><b>" + escapeHtml(tier.state)
        + "</b><small>" + escapeHtml(tier.detail) + "</small></li>";
    }).join("");
    var stages = view.stages.map(function (stage, index) {
      return '<li class="hakimi-admission-rail-v1__stage" data-state="'
        + escapeHtml(stage.state.toLowerCase()) + '"><span>0' + String(index + 1)
        + "</span><strong>" + escapeHtml(stage.axis) + "</strong><b>"
        + escapeHtml(stage.state) + "</b><small>" + escapeHtml(stage.detail)
        + "</small></li>";
    }).join("");
    var blockers = view.blockers.length
      ? '<ul class="hakimi-admission-rail-v1__blockers">' + view.blockers.map(function (blocker) {
        return "<li>" + escapeHtml(blocker) + "</li>";
      }).join("") + "</ul>"
      : '<p class="hakimi-admission-rail-v1__no-blocker">No local blocker in this candidate. Governance gaps remain.</p>';

    return '<article class="hakimi-admission-rail-v1" data-tone="'
      + escapeHtml(view.tone)
      + '" aria-label="Portfolio correlation admission hierarchy"><header class="hakimi-admission-rail-v1__header"><div><p>'
      + escapeHtml(view.kicker) + "</p><h2>" + escapeHtml(view.title)
      + '</h2></div><span class="hakimi-admission-rail-v1__status">'
      + escapeHtml(view.status_label) + '</span></header><div class="hakimi-admission-rail-v1__context"><span>'
      + escapeHtml(view.identity) + "</span><span>" + escapeHtml(view.lane)
      + '</span></div><p class="hakimi-admission-rail-v1__summary">'
      + escapeHtml(view.summary) + '</p><ul class="hakimi-admission-rail-v1__metrics">'
      + metrics + '</ul><ol class="hakimi-admission-rail-v1__tiers">' + tiers
      + '</ol><ol class="hakimi-admission-rail-v1__stages">' + stages
      + '</ol><section class="hakimi-admission-rail-v1__gap" aria-label="Admission blockers"><h3>Gap ledger</h3>'
      + blockers + '</section><footer class="hakimi-admission-rail-v1__footer"><span>candidate '
      + escapeHtml(view.candidate_hash_short) + "</span><span>" + escapeHtml(view.permission_note)
      + "</span></footer></article>";
  }

  return Object.freeze({
    ADMISSION_SCHEMA_VERSION: ADMISSION_SCHEMA_VERSION,
    RAIL_SCHEMA_VERSION: RAIL_SCHEMA_VERSION,
    RAIL_STATIC_FINGERPRINT: RAIL_STATIC_FINGERPRINT,
    STAGE_ORDER: STAGE_ORDER,
    TIER_ORDER: TIER_ORDER,
    verifyPortfolioCorrelationAdmissionV1: verifyPortfolioCorrelationAdmissionV1,
    buildPortfolioCorrelationAdmissionRailViewModelV1:
      buildPortfolioCorrelationAdmissionRailViewModelV1,
    renderPortfolioCorrelationAdmissionRailV1:
      renderPortfolioCorrelationAdmissionRailV1,
  });
});
