(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiPortfolioRiskTemporalLatticeCardV2 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-public-projection-v2";
  var STATIC_FINGERPRINT =
    "20260822-portfolio-risk-temporal-lattice-projection-lock-1";
  var ADAPTER_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-adapter-v2";
  var ADAPTER_VERIFICATION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-adapter-v2-verification-v1";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var ALLOWED_STAGE_STATES = {
    SOURCE: ["VERIFIED", "UNKNOWN", "NOT_SUPPLIED"],
    GAP: [
      "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY",
      "PORTFOLIO_RISK_LIMIT_GAP_PRESENT",
      "TEMPORAL_STABILITY_GAP_PRESENT",
      "JOINT_RESEARCH_GAP_PRESENT",
      "RISK_REDUCTION_PATH",
      "UNKNOWN",
      "NOT_SUPPLIED",
    ],
    MATURITY: ["UNMOUNTED_CANDIDATE"],
    PERMISSION: ["UNAUTHORIZED"],
  };
  var ALLOWED_DECISIONS = [
    "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY",
    "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET",
    "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY",
    "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED",
    "UNKNOWN",
    "NOT_SUPPLIED",
  ];
  var STATE_LABELS = {
    VERIFIED: "来源已验证",
    UNKNOWN: "未知",
    NOT_SUPPLIED: "未提供",
    WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY:
      "组合限额与时序稳定性已观测",
    PORTFOLIO_RISK_LIMIT_GAP_PRESENT: "组合风险限额存在缺口",
    TEMPORAL_STABILITY_GAP_PRESENT: "时序稳定性存在缺口",
    JOINT_RESEARCH_GAP_PRESENT: "联合研究证据存在缺口",
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

  function isOptionalTier(value) {
    return (
      value === null ||
      (typeof value === "string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(value))
    );
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
      "risk_service_invocation_allowed",
      "runtime_gate_activation_allowed",
      "writer_allowed",
    ];
    return falseKeys.every(function (key) {
      return authority[key] === false;
    });
  }

  function hasLockedFacts(facts) {
    if (!isPlainObject(facts)) {
      return false;
    }
    var falseKeys = [
      "source_documents_embedded",
      "component_results_embedded",
      "raw_correlations_embedded",
      "return_series_embedded",
      "window_rows_embedded",
      "profitability_proof",
      "runtime_assets_accessed",
      "runtime_consumer_mounted",
      "natural_forward_chain_changed",
    ];
    return falseKeys.every(function (key) {
      return facts[key] === false;
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

  function hasValidSource(source, status) {
    if (
      !isPlainObject(source) ||
      typeof source.adapter_supplied !== "boolean" ||
      typeof source.adapter_exactly_verified !== "boolean"
    ) {
      return false;
    }
    if (status === "OBSERVED") {
      return (
        source.adapter_supplied === true &&
        source.adapter_exactly_verified === true &&
        source.adapter_schema_version === ADAPTER_SCHEMA_VERSION &&
        /^(?:[0-9a-f]{64})$/.test(source.adapter_hash || "") &&
        source.verification_schema_version ===
          ADAPTER_VERIFICATION_SCHEMA_VERSION
      );
    }
    if (status === "UNKNOWN") {
      return (
        source.adapter_supplied === true &&
        source.adapter_exactly_verified === false &&
        source.adapter_schema_version === null &&
        source.adapter_hash === null &&
        source.verification_schema_version === null
      );
    }
    if (status === "NOT_SUPPLIED") {
      return (
        source.adapter_supplied === false &&
        source.adapter_exactly_verified === false &&
        source.adapter_schema_version === null &&
        source.adapter_hash === null &&
        source.verification_schema_version === null
      );
    }
    return false;
  }

  function hasValidSummary(summary) {
    if (!isPlainObject(summary)) {
      return false;
    }
    return (
      ALLOWED_DECISIONS.indexOf(summary.adapter_decision) !== -1 &&
      ["PASS", "BLOCK", null].indexOf(summary.adapter_status) !== -1 &&
      isOptionalBoolean(summary.risk_increasing) &&
      isOptionalBoolean(summary.base_adapter_passed) &&
      isOptionalBoolean(summary.temporal_stability_required) &&
      isOptionalBoolean(summary.temporal_stability_passed) &&
      isOptionalNumber(summary.legacy_gross_exposure_pct) &&
      isOptionalNumber(summary.legacy_net_exposure_pct) &&
      isOptionalNumber(summary.legacy_proposal_centered_cluster_pct) &&
      isOptionalNumber(summary.all_cluster_max_gross_exposure_pct) &&
      isOptionalInteger(summary.symbol_ticket_count) &&
      isOptionalInteger(summary.effective_independent_bet_count) &&
      isOptionalInteger(summary.correlated_duplicate_ticket_count) &&
      isOptionalInteger(summary.effective_bet_blocker_count) &&
      isOptionalInteger(summary.legacy_reject_reason_count) &&
      ["PASS", "BLOCK", null].indexOf(summary.temporal_stability_status) !== -1 &&
      isOptionalInteger(summary.window_result_count) &&
      isOptionalInteger(summary.unstable_window_count) &&
      isOptionalInteger(summary.insufficient_sample_window_count) &&
      isOptionalInteger(summary.blocked_window_count) &&
      isOptionalInteger(summary.within_cluster_pair_count) &&
      isOptionalInteger(summary.pair_window_hypothesis_count) &&
      isOptionalTier(summary.first_blocking_tier) &&
      isOptionalInteger(summary.stability_blocker_count) &&
      isOptionalInteger(summary.adapter_blocker_count) &&
      isOptionalInteger(summary.adapter_warning_count)
    );
  }

  function hasConsistentProjectionState(projection) {
    var sourceState = projection.pipeline[0].state;
    var gapState = projection.pipeline[1].state;
    var summary = projection.summary;
    if (projection.status === "UNKNOWN") {
      return (
        sourceState === "UNKNOWN" &&
        gapState === "UNKNOWN" &&
        summary.adapter_decision === "UNKNOWN" &&
        summary.adapter_status === null
      );
    }
    if (projection.status === "NOT_SUPPLIED") {
      return (
        sourceState === "NOT_SUPPLIED" &&
        gapState === "NOT_SUPPLIED" &&
        summary.adapter_decision === "NOT_SUPPLIED" &&
        summary.adapter_status === null
      );
    }
    if (projection.status !== "OBSERVED" || sourceState !== "VERIFIED") {
      return false;
    }
    if (summary.risk_increasing === false) {
      return (
        gapState === "RISK_REDUCTION_PATH" &&
        summary.adapter_status === "PASS" &&
        summary.adapter_decision ===
          "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED"
      );
    }
    if (summary.base_adapter_passed === false) {
      return (
        gapState === "PORTFOLIO_RISK_LIMIT_GAP_PRESENT" &&
        summary.adapter_status === "BLOCK" &&
        summary.adapter_decision === "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET"
      );
    }
    if (
      summary.temporal_stability_required === true &&
      summary.temporal_stability_passed === false
    ) {
      return (
        gapState === "TEMPORAL_STABILITY_GAP_PRESENT" &&
        summary.adapter_status === "BLOCK" &&
        summary.adapter_decision ===
          "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY"
      );
    }
    if (
      summary.risk_increasing === true &&
      summary.base_adapter_passed === true &&
      summary.temporal_stability_required === true &&
      summary.temporal_stability_passed === true
    ) {
      return (
        gapState ===
          "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY" &&
        summary.adapter_status === "PASS" &&
        summary.adapter_decision ===
          "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY"
      );
    }
    return gapState === "JOINT_RESEARCH_GAP_PRESENT";
  }

  function isValidProjection(projection) {
    return Boolean(
      isPlainObject(projection) &&
        projection.schema_version === PROJECTION_SCHEMA_VERSION &&
        projection.static_fingerprint === STATIC_FINGERPRINT &&
        /^(?:[0-9a-f]{64})$/.test(projection.projection_hash || "") &&
        ["OBSERVED", "UNKNOWN", "NOT_SUPPLIED"].indexOf(projection.status) !== -1 &&
        hasValidPipeline(projection) &&
        hasValidSource(projection.source, projection.status) &&
        hasValidSummary(projection.summary) &&
        hasConsistentProjectionState(projection) &&
        hasLockedFacts(projection.facts) &&
        hasLockedAuthority(projection.authority)
    );
  }

  function stageTone(state) {
    if (state === "VERIFIED") {
      return "source";
    }
    if (
      state ===
        "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY" ||
      state === "RISK_REDUCTION_PATH"
    ) {
      return "observed";
    }
    if (
      state === "PORTFOLIO_RISK_LIMIT_GAP_PRESENT" ||
      state === "TEMPORAL_STABILITY_GAP_PRESENT" ||
      state === "JOINT_RESEARCH_GAP_PRESENT"
    ) {
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
      return { code: "BLOCKED", label: "存在缺口" };
    }
    return { code: "UNKNOWN", label: "未知" };
  }

  function requirementState(value) {
    if (value === true) {
      return { code: "REQUIRED", label: "风险增加必需" };
    }
    if (value === false) {
      return { code: "NOT_REQUIRED", label: "风险降低不要求" };
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
      decisionLabel: "无法验证组合风险与时序稳定性投影",
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
        grossPct: null,
        netPct: null,
        proposalClusterPct: null,
        allClusterMaxPct: null,
      },
      gates: {
        baseAdapter: gateState(null),
        temporalStability: gateState(null),
        temporalRequirement: requirementState(null),
      },
      stability: {
        status: null,
        windowResults: null,
        unstableWindows: null,
        insufficientWindows: null,
        blockedWindows: null,
        pairHypotheses: null,
        firstBlockingTier: null,
      },
      blockerCount: null,
      warningCount: null,
      permissionLabel: "PAPER / LIVE 未授权",
    };
  }

  function decisionLabel(summary) {
    if (
      summary.adapter_decision ===
      "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY"
    ) {
      return "组合限额与时序稳定性均完成研究观测";
    }
    if (
      summary.adapter_decision === "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY"
    ) {
      return "相关簇在时序窗口中存在稳定性缺口";
    }
    if (summary.adapter_decision === "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET") {
      return "组合风险预算存在缺口";
    }
    if (
      summary.adapter_decision ===
      "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED"
    ) {
      return "风险降低路径不以时序稳定性授予权限";
    }
    if (summary.adapter_decision === "NOT_SUPPLIED") {
      return "尚未提供联合研究证据";
    }
    return "无法验证组合风险与时序稳定性投影";
  }

  function buildPortfolioRiskTemporalLatticeViewModel(projection) {
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
      decisionLabel: decisionLabel(summary),
      stages: stages,
      metrics: {
        symbolTickets: summary.symbol_ticket_count,
        effectiveBets: summary.effective_independent_bet_count,
        correlatedDuplicates: summary.correlated_duplicate_ticket_count,
      },
      exposures: {
        grossPct: summary.legacy_gross_exposure_pct,
        netPct: summary.legacy_net_exposure_pct,
        proposalClusterPct: summary.legacy_proposal_centered_cluster_pct,
        allClusterMaxPct: summary.all_cluster_max_gross_exposure_pct,
      },
      gates: {
        baseAdapter: gateState(summary.base_adapter_passed),
        temporalStability: gateState(summary.temporal_stability_passed),
        temporalRequirement: requirementState(
          summary.temporal_stability_required,
        ),
      },
      stability: {
        status: summary.temporal_stability_status,
        windowResults: summary.window_result_count,
        unstableWindows: summary.unstable_window_count,
        insufficientWindows: summary.insufficient_sample_window_count,
        blockedWindows: summary.blocked_window_count,
        pairHypotheses: summary.pair_window_hypothesis_count,
        firstBlockingTier: summary.first_blocking_tier,
      },
      blockerCount: summary.adapter_blocker_count,
      warningCount: summary.adapter_warning_count,
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
    return Math.max(0, Math.min(100, Math.abs(Number(value))));
  }

  function renderStage(stage, index) {
    return [
      '<li class="hkm-risk-lattice__stage" data-tone="',
      escapeHtml(stage.tone),
      '"><span class="hkm-risk-lattice__stage-index">0',
      String(index + 1),
      '</span><span class="hkm-risk-lattice__stage-copy"><b>',
      escapeHtml(stage.stageLabel),
      "</b><small>",
      escapeHtml(stage.stateLabel),
      "</small></span></li>",
    ].join("");
  }

  function renderGate(label, gate) {
    return [
      '<div class="hkm-risk-lattice__gate" data-state="',
      escapeHtml(gate.code),
      '"><span>',
      escapeHtml(label),
      "</span><b>",
      escapeHtml(gate.label),
      "</b></div>",
    ].join("");
  }

  function renderExposure(label, value) {
    return [
      '<div class="hkm-risk-lattice__exposure"><div><span>',
      escapeHtml(label),
      "</span><b>",
      escapeHtml(formatPercent(value)),
      '</b></div><i aria-hidden="true"><em style="--hkm-risk-lattice-value:',
      String(barWidth(value)),
      '%"></em></i></div>',
    ].join("");
  }

  function renderCount(label, value, tone) {
    return [
      '<div class="hkm-risk-lattice__count" data-tone="',
      escapeHtml(tone),
      '"><span>',
      escapeHtml(label),
      "</span><b>",
      escapeHtml(formatMetric(value)),
      "</b></div>",
    ].join("");
  }

  function renderPortfolioRiskTemporalLatticeCard(projection, options) {
    var view = buildPortfolioRiskTemporalLatticeViewModel(projection);
    var config = isPlainObject(options) ? options : {};
    var eyebrow =
      typeof config.eyebrow === "string"
        ? config.eyebrow
        : "CORRELATION FIELD NOTE / RESEARCH ONLY";
    var title =
      typeof config.title === "string" ? config.title : "相关簇时序格网";
    return [
      '<article class="hkm-risk-lattice" data-contract-valid="',
      view.validContract ? "true" : "false",
      '" data-gap-state="',
      escapeHtml(view.gapState),
      '"><div class="hkm-risk-lattice__paper" aria-hidden="true"></div>',
      '<header class="hkm-risk-lattice__header"><div><p>',
      escapeHtml(eyebrow),
      "</p><h2>",
      escapeHtml(title),
      '</h2></div><span class="hkm-risk-lattice__badge">',
      escapeHtml(view.badgeLabel),
      "</span></header>",
      '<ol class="hkm-risk-lattice__rail" aria-label="证据到权限路径">',
      view.stages.map(renderStage).join(""),
      "</ol>",
      '<section class="hkm-risk-lattice__body">',
      '<div class="hkm-risk-lattice__geometry"><div class="hkm-risk-lattice__compass" aria-hidden="true"><i></i><i></i><i></i></div><p class="hkm-risk-lattice__decision">',
      escapeHtml(view.decisionLabel),
      '</p><div class="hkm-risk-lattice__metric-chain"><span><b>',
      escapeHtml(formatMetric(view.metrics.symbolTickets)),
      '</b><small>标的票数</small></span><em aria-hidden="true"></em><span><b>',
      escapeHtml(formatMetric(view.metrics.effectiveBets)),
      '</b><small>有效独立票</small></span><em aria-hidden="true"></em><span><b>',
      escapeHtml(formatMetric(view.metrics.correlatedDuplicates)),
      "</b><small>相关重复票</small></span></div>",
      '<div class="hkm-risk-lattice__exposures">',
      renderExposure("组合 gross", view.exposures.grossPct),
      renderExposure("组合 net", view.exposures.netPct),
      renderExposure("提案中心簇", view.exposures.proposalClusterPct),
      renderExposure("全部簇最大 gross", view.exposures.allClusterMaxPct),
      "</div></div>",
      '<div class="hkm-risk-lattice__temporal"><div class="hkm-risk-lattice__temporal-head"><span>时序稳定摘要</span><b>',
      escapeHtml(view.stability.status || "UNKNOWN"),
      '</b></div><div class="hkm-risk-lattice__counts">',
      renderCount("窗口结果", view.stability.windowResults, "neutral"),
      renderCount("不稳定窗口", view.stability.unstableWindows, "gap"),
      renderCount("样本不足", view.stability.insufficientWindows, "caution"),
      renderCount("阻断窗口", view.stability.blockedWindows, "gap"),
      renderCount("配对假设", view.stability.pairHypotheses, "neutral"),
      renderCount(
        "首个阻断层",
        view.stability.firstBlockingTier,
        "caution",
      ),
      '</div><div class="hkm-risk-lattice__gates">',
      renderGate("组合风险预算", view.gates.baseAdapter),
      renderGate("时序稳定性", view.gates.temporalStability),
      renderGate("时序要求", view.gates.temporalRequirement),
      "</div></div></section>",
      '<footer class="hkm-risk-lattice__footer"><span>BLOCKERS ',
      escapeHtml(formatMetric(view.blockerCount)),
      " / WARNINGS ",
      escapeHtml(formatMetric(view.warningCount)),
      "</span><b>",
      escapeHtml(view.permissionLabel),
      "</b></footer></article>",
    ].join("");
  }

  function mountPortfolioRiskTemporalLatticeCard(target, projection, options) {
    if (!target || typeof target !== "object" || !("innerHTML" in target)) {
      throw new TypeError("A mount target with innerHTML is required.");
    }
    target.innerHTML = renderPortfolioRiskTemporalLatticeCard(
      projection,
      options,
    );
    return target;
  }

  return {
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    buildPortfolioRiskTemporalLatticeViewModel:
      buildPortfolioRiskTemporalLatticeViewModel,
    renderPortfolioRiskTemporalLatticeCard:
      renderPortfolioRiskTemporalLatticeCard,
    mountPortfolioRiskTemporalLatticeCard:
      mountPortfolioRiskTemporalLatticeCard,
  };
});
