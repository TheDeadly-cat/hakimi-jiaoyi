(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiPortfolioRiskGeometryCardV1 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-public-projection-v1";
  var STATIC_FINGERPRINT =
    "20260822-portfolio-risk-geometry-projection-lock-1";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var ALLOWED_STAGE_STATES = {
    SOURCE: ["VERIFIED", "UNKNOWN", "NOT_SUPPLIED"],
    GAP: [
      "WITHIN_DECLARED_RESEARCH_LIMITS",
      "RESEARCH_LIMIT_GAP_PRESENT",
      "RISK_REDUCTION_PATH",
      "UNKNOWN",
      "NOT_SUPPLIED",
    ],
    MATURITY: ["UNMOUNTED_CANDIDATE"],
    PERMISSION: ["UNAUTHORIZED"],
  };
  var STATE_LABELS = {
    VERIFIED: "来源已验证",
    UNKNOWN: "未知",
    NOT_SUPPLIED: "未提供",
    WITHIN_DECLARED_RESEARCH_LIMITS: "声明的研究限额内",
    RESEARCH_LIMIT_GAP_PRESENT: "存在研究限额缺口",
    RISK_REDUCTION_PATH: "风险降低路径",
    UNMOUNTED_CANDIDATE: "未挂载候选",
    UNAUTHORIZED: "未授权",
  };
  var STAGE_LABELS = {
    SOURCE: "来源",
    GAP: "缺口",
    MATURITY: "成熟度",
    PERMISSION: "权限",
  };

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function isOptionalNumber(value) {
    return value === null || (typeof value === "number" && Number.isFinite(value));
  }

  function isOptionalInteger(value) {
    return value === null || (Number.isInteger(value) && value >= 0);
  }

  function isOptionalBoolean(value) {
    return value === null || typeof value === "boolean";
  }

  function hasLockedAuthority(authority) {
    if (!isPlainObject(authority) || authority.descriptive_only !== true) {
      return false;
    }
    var falseKeys = [
      "current_admission_allowed",
      "current_pointer_written",
      "formal_registry_activation_allowed",
      "live_order_allowed",
      "migration_allowed",
      "paper_authorized",
      "runtime_gate_activation_allowed",
      "writer_allowed",
    ];
    return falseKeys.every(function (key) {
      return authority[key] === false;
    });
  }

  function hasValidPipeline(projection) {
    if (!Array.isArray(projection.pipeline) || projection.pipeline.length !== 4) {
      return false;
    }
    return projection.pipeline.every(function (item, index) {
      var stage = STAGE_ORDER[index];
      return (
        isPlainObject(item) &&
        item.stage === stage &&
        ALLOWED_STAGE_STATES[stage].indexOf(item.state) !== -1
      );
    });
  }

  function hasConsistentProjectionState(projection) {
    var sourceState = projection.pipeline[0].state;
    var gapState = projection.pipeline[1].state;
    if (projection.status === "OBSERVED") {
      return (
        sourceState === "VERIFIED" &&
        [
          "WITHIN_DECLARED_RESEARCH_LIMITS",
          "RESEARCH_LIMIT_GAP_PRESENT",
          "RISK_REDUCTION_PATH",
        ].indexOf(gapState) !== -1
      );
    }
    if (projection.status === "UNKNOWN") {
      return sourceState === "UNKNOWN" && gapState === "UNKNOWN";
    }
    if (projection.status === "NOT_SUPPLIED") {
      return sourceState === "NOT_SUPPLIED" && gapState === "NOT_SUPPLIED";
    }
    return false;
  }

  function hasValidSummary(summary) {
    if (!isPlainObject(summary)) {
      return false;
    }
    var decisions = [
      "WITHIN_RESEARCH_RISK_BUDGET",
      "BLOCKED_RESEARCH_RISK_BUDGET",
      "UNKNOWN",
      "NOT_SUPPLIED",
    ];
    var statuses = ["PASS", "BLOCK", null];
    return (
      decisions.indexOf(summary.adapter_decision) !== -1 &&
      statuses.indexOf(summary.adapter_status) !== -1 &&
      isOptionalBoolean(summary.risk_increasing) &&
      isOptionalBoolean(summary.legacy_gate_passed) &&
      isOptionalBoolean(summary.effective_bet_gate_passed) &&
      isOptionalBoolean(summary.cluster_limit_aligned) &&
      isOptionalNumber(summary.legacy_gross_exposure_pct) &&
      isOptionalNumber(summary.legacy_net_exposure_pct) &&
      isOptionalNumber(summary.legacy_proposal_centered_cluster_pct) &&
      isOptionalNumber(summary.all_cluster_max_gross_exposure_pct) &&
      isOptionalInteger(summary.symbol_ticket_count) &&
      isOptionalInteger(summary.effective_independent_bet_count) &&
      isOptionalInteger(summary.correlated_duplicate_ticket_count) &&
      isOptionalInteger(summary.blocker_count)
    );
  }

  function isValidProjection(projection) {
    return Boolean(
      isPlainObject(projection) &&
        projection.schema_version === PROJECTION_SCHEMA_VERSION &&
        projection.static_fingerprint === STATIC_FINGERPRINT &&
        /^(?:[0-9a-f]{64})$/.test(projection.projection_hash || "") &&
        ["OBSERVED", "UNKNOWN", "NOT_SUPPLIED"].indexOf(projection.status) !== -1 &&
        hasValidPipeline(projection) &&
        hasConsistentProjectionState(projection) &&
        hasValidSummary(projection.summary) &&
        hasLockedAuthority(projection.authority)
    );
  }

  function stageTone(state) {
    if (state === "VERIFIED") {
      return "source";
    }
    if (
      state === "WITHIN_DECLARED_RESEARCH_LIMITS" ||
      state === "RISK_REDUCTION_PATH"
    ) {
      return "observed";
    }
    if (state === "RESEARCH_LIMIT_GAP_PRESENT") {
      return "gap";
    }
    if (state === "UNAUTHORIZED") {
      return "permission";
    }
    if (state === "UNMOUNTED_CANDIDATE") {
      return "maturity";
    }
    return "unknown";
  }

  function gateState(value) {
    if (value === true) {
      return { code: "OBSERVED_PASS", label: "观测通过" };
    }
    if (value === false) {
      return { code: "BLOCKED", label: "阻断" };
    }
    return { code: "UNKNOWN", label: "未知" };
  }

  function fallbackViewModel() {
    return {
      validContract: false,
      projectionStatus: "UNKNOWN",
      sourceState: "UNKNOWN",
      gapState: "UNKNOWN",
      maturityState: "UNMOUNTED_CANDIDATE",
      permissionState: "UNAUTHORIZED",
      badgeLabel: "合同未知",
      decisionLabel: "无法验证研究风险投影",
      stages: STAGE_ORDER.map(function (stage) {
        var state =
          stage === "MATURITY"
            ? "UNMOUNTED_CANDIDATE"
            : stage === "PERMISSION"
              ? "UNAUTHORIZED"
              : "UNKNOWN";
        return {
          stage: stage,
          stageLabel: STAGE_LABELS[stage],
          state: state,
          stateLabel: STATE_LABELS[state],
          tone: stageTone(state),
        };
      }),
      metrics: {
        symbolTickets: null,
        effectiveBets: null,
        correlatedDuplicates: null,
      },
      exposures: {
        legacyGrossPct: null,
        legacyNetPct: null,
        proposalClusterPct: null,
        allClusterMaxPct: null,
      },
      gates: {
        legacy: gateState(null),
        allCluster: gateState(null),
        limitAlignment: gateState(null),
      },
      blockerCount: null,
      permissionLabel: "PAPER / LIVE 未授权",
    };
  }

  function buildPortfolioRiskGeometryViewModel(projection) {
    if (!isValidProjection(projection)) {
      return fallbackViewModel();
    }
    var summary = projection.summary;
    var stages = projection.pipeline.map(function (item) {
      return {
        stage: item.stage,
        stageLabel: STAGE_LABELS[item.stage],
        state: item.state,
        stateLabel: STATE_LABELS[item.state],
        tone: stageTone(item.state),
      };
    });
    var decisionLabel = "无法验证研究风险投影";
    if (stages[1].state === "RISK_REDUCTION_PATH") {
      decisionLabel = "风险降低路径，不依赖新增簇证据";
    } else if (summary.adapter_decision === "WITHIN_RESEARCH_RISK_BUDGET") {
      decisionLabel = "双门禁均在声明的研究限额内";
    } else if (summary.adapter_decision === "BLOCKED_RESEARCH_RISK_BUDGET") {
      decisionLabel = "至少一个研究门禁阻断";
    } else if (summary.adapter_decision === "NOT_SUPPLIED") {
      decisionLabel = "尚未提供双门禁研究证据";
    }
    return {
      validContract: true,
      projectionStatus: projection.status,
      sourceState: stages[0].state,
      gapState: stages[1].state,
      maturityState: stages[2].state,
      permissionState: stages[3].state,
      badgeLabel:
        projection.status === "OBSERVED"
          ? "研究观测"
          : projection.status === "NOT_SUPPLIED"
            ? "未提供"
            : "未知",
      decisionLabel: decisionLabel,
      stages: stages,
      metrics: {
        symbolTickets: summary.symbol_ticket_count,
        effectiveBets: summary.effective_independent_bet_count,
        correlatedDuplicates: summary.correlated_duplicate_ticket_count,
      },
      exposures: {
        legacyGrossPct: summary.legacy_gross_exposure_pct,
        legacyNetPct: summary.legacy_net_exposure_pct,
        proposalClusterPct: summary.legacy_proposal_centered_cluster_pct,
        allClusterMaxPct: summary.all_cluster_max_gross_exposure_pct,
      },
      gates: {
        legacy: gateState(summary.legacy_gate_passed),
        allCluster: gateState(summary.effective_bet_gate_passed),
        limitAlignment: gateState(summary.cluster_limit_aligned),
      },
      blockerCount: summary.blocker_count,
      permissionLabel: "PAPER / LIVE 未授权",
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatMetric(value) {
    return value === null ? "N/A" : String(value);
  }

  function formatPercent(value) {
    return value === null ? "N/A" : Number(value).toFixed(1) + "%";
  }

  function barWidth(value) {
    if (value === null) {
      return 0;
    }
    return Math.max(0, Math.min(100, Number(value)));
  }

  function renderStage(stage, index) {
    return [
      '<li class="hkm-risk-geometry__stage" data-tone="',
      escapeHtml(stage.tone),
      '">',
      '<span class="hkm-risk-geometry__stage-index">0',
      String(index + 1),
      "</span>",
      '<span class="hkm-risk-geometry__stage-copy">',
      "<b>",
      escapeHtml(stage.stageLabel),
      "</b>",
      "<small>",
      escapeHtml(stage.stateLabel),
      "</small>",
      "</span>",
      "</li>",
    ].join("");
  }

  function renderGate(label, gate) {
    return [
      '<div class="hkm-risk-geometry__gate" data-state="',
      escapeHtml(gate.code),
      '">',
      "<span>",
      escapeHtml(label),
      "</span>",
      "<b>",
      escapeHtml(gate.label),
      "</b>",
      "</div>",
    ].join("");
  }

  function renderExposure(label, value) {
    return [
      '<div class="hkm-risk-geometry__exposure">',
      '<div class="hkm-risk-geometry__exposure-label"><span>',
      escapeHtml(label),
      "</span><b>",
      escapeHtml(formatPercent(value)),
      "</b></div>",
      '<div class="hkm-risk-geometry__bar" aria-hidden="true"><i style="--hkm-risk-value:',
      String(barWidth(value)),
      '%"></i></div>',
      "</div>",
    ].join("");
  }

  function renderPortfolioRiskGeometryCard(projection, options) {
    var view = buildPortfolioRiskGeometryViewModel(projection);
    var config = isPlainObject(options) ? options : {};
    var eyebrow =
      typeof config.eyebrow === "string"
        ? config.eyebrow
        : "PORTFOLIO GEOMETRY / RESEARCH ONLY";
    var title =
      typeof config.title === "string" ? config.title : "相关簇风险几何";
    return [
      '<article class="hkm-risk-geometry" data-contract-valid="',
      view.validContract ? "true" : "false",
      '" data-gap-state="',
      escapeHtml(view.gapState),
      '">',
      '<div class="hkm-risk-geometry__grain" aria-hidden="true"></div>',
      '<header class="hkm-risk-geometry__header">',
      "<div><p>",
      escapeHtml(eyebrow),
      "</p><h2>",
      escapeHtml(title),
      "</h2></div>",
      '<span class="hkm-risk-geometry__badge">',
      escapeHtml(view.badgeLabel),
      "</span>",
      "</header>",
      '<ol class="hkm-risk-geometry__rail" aria-label="证据到权限路径">',
      view.stages.map(renderStage).join(""),
      "</ol>",
      '<section class="hkm-risk-geometry__body">',
      '<div class="hkm-risk-geometry__orbit-panel">',
      '<div class="hkm-risk-geometry__orbit" aria-hidden="true">',
      "<i></i><i></i><i></i><span></span>",
      "</div>",
      '<p class="hkm-risk-geometry__decision">',
      escapeHtml(view.decisionLabel),
      "</p>",
      '<div class="hkm-risk-geometry__equation" aria-label="标的票数与有效独立押注">',
      "<span><b>",
      escapeHtml(formatMetric(view.metrics.symbolTickets)),
      "</b><small>标的票数</small></span>",
      '<em aria-hidden="true">&rarr;</em>',
      "<span><b>",
      escapeHtml(formatMetric(view.metrics.effectiveBets)),
      "</b><small>有效独立押注</small></span>",
      "<span><b>",
      escapeHtml(formatMetric(view.metrics.correlatedDuplicates)),
      "</b><small>相关重复票</small></span>",
      "</div>",
      "</div>",
      '<div class="hkm-risk-geometry__detail">',
      '<div class="hkm-risk-geometry__gates">',
      renderGate("Legacy 组合门禁", view.gates.legacy),
      renderGate("全簇有效押注门禁", view.gates.allCluster),
      renderGate("相关簇限额同步", view.gates.limitAlignment),
      "</div>",
      '<div class="hkm-risk-geometry__exposures">',
      renderExposure("Legacy gross", view.exposures.legacyGrossPct),
      renderExposure("Legacy net", view.exposures.legacyNetPct),
      renderExposure("提案中心相关簇", view.exposures.proposalClusterPct),
      renderExposure("全部簇最大 gross", view.exposures.allClusterMaxPct),
      "</div>",
      "</div>",
      "</section>",
      '<footer class="hkm-risk-geometry__footer">',
      "<span>BLOCKERS ",
      escapeHtml(formatMetric(view.blockerCount)),
      "</span><b>",
      escapeHtml(view.permissionLabel),
      "</b>",
      "</footer>",
      "</article>",
    ].join("");
  }

  function mountPortfolioRiskGeometryCard(target, projection, options) {
    if (!target || typeof target !== "object" || !("innerHTML" in target)) {
      throw new TypeError("A mount target with innerHTML is required.");
    }
    target.innerHTML = renderPortfolioRiskGeometryCard(projection, options);
    return target;
  }

  return {
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    buildPortfolioRiskGeometryViewModel:
      buildPortfolioRiskGeometryViewModel,
    renderPortfolioRiskGeometryCard: renderPortfolioRiskGeometryCard,
    mountPortfolioRiskGeometryCard: mountPortfolioRiskGeometryCard,
  };
});
