(function initEvidencePresentation(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiEvidencePresentation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function buildEvidencePresentation() {
  "use strict";

  const AUTHORITY_SUMMARY = Object.freeze({
    allowed: "可做：策略研究 · 行情核验 · 自然前向观察 · 小资金纯规划",
    forbidden: "不可做：模拟运行（未授权）· 实盘下单（永久硬锁）",
  });

  const HYPOTHESIS_V1_REPORT_SCHEMA_VERSIONS = Object.freeze([7, 8, 9, 10, 11, 12]);
  const STRATEGY_LAB_FROZEN_V3_REPORT_SCHEMA_VERSIONS = Object.freeze([
    3, 4, 5, 6, 7, 8, 9, 10,
  ]);
  const STRATEGY_LAB_POST_SELECTION_REPORT_SCHEMA_VERSIONS = Object.freeze([11, 12, 13, 14]);
  const INTERNAL_BACKTEST_QUALITY_COUPLINGS = Object.freeze({
    "portfolio-internal-backtest-pack-v2": Object.freeze({
      qualitySchema: "backtest-return-quality-v1",
      availability: "LEGACY_UNKNOWN",
      forwardSchema: null,
      snapshotSchema: "portfolio-backtest-return-quality-snapshot-v3",
    }),
    "portfolio-internal-backtest-pack-v3": Object.freeze({
      qualitySchema: "backtest-return-quality-v1",
      availability: "LEGACY_UNKNOWN",
      forwardSchema: "portfolio-backtest-forward-promotion-summary-v1",
      snapshotSchema: "portfolio-backtest-return-quality-snapshot-v3",
    }),
    "portfolio-internal-backtest-pack-v4": Object.freeze({
      qualitySchema: "backtest-return-quality-v2",
      availability: "AVAILABLE",
      forwardSchema: "portfolio-backtest-forward-promotion-summary-v1",
      snapshotSchema: "portfolio-backtest-return-quality-snapshot-v3",
      sourceMode: "SOURCE_EVIDENCE_V2",
    }),
    "portfolio-internal-backtest-pack-v5": Object.freeze({
      qualitySchema: "backtest-return-quality-v3",
      availability: "AVAILABLE",
      forwardSchema: "portfolio-backtest-forward-promotion-summary-v1",
      snapshotSchema: "portfolio-backtest-return-quality-snapshot-v3",
      sourceMode: "COMPACT_BUNDLE_RECOMPUTED",
    }),
    "portfolio-internal-backtest-pack-v6": Object.freeze({
      qualitySchema: "backtest-return-quality-v3",
      availability: "AVAILABLE",
      forwardSchema: "portfolio-backtest-forward-promotion-summary-v2",
      snapshotSchema: "portfolio-backtest-return-quality-snapshot-v4",
      sourceMode: "COMPACT_BUNDLE_RECOMPUTED",
    }),
  });

  const INTERNAL_BACKTEST_EVIDENCE_CUE_TEXT = Object.freeze({
    SAFETY_BOUNDARY: "先修复只读边界：研究范围与权限关闭声明必须完整，当前证据不作解释",
    SOURCE: "先补冻结来源：固定快照、冻结时间与内容指纹需同时可核验",
    VERSION_BINDING: "先补版本绑定：冻结包、收益质量与自然前向必须采用受支持的精确组合",
    STAGE_EVIDENCE: "先补阶段证据：验证段与测试段都需样本、基准和统计口径",
    VALUE_CONSISTENCY: "先修复复算口径：策略、基准与派生值的关系尚未闭合",
    FORWARD_EVIDENCE: "先补自然前向证据：成熟度、审计收据与整体状态必须闭合",
    SOURCE_BLOCK: "来源完整性已阻断：停止使用当前数字，先修复固定来源",
    OBSERVED_BLOCK: "已形成有效负结果，停止晋级；保留结果，不用补录覆盖",
    EVIDENCE_GAP: "先补研究证据：至少一类必需证据尚未形成",
    PROMOTION_GAP: "先补晋级复核证据：当前只保留研究阻断",
    PARTIAL_EVIDENCE: "先补描述字段：收益质量摘要尚不完整",
    RESEARCH_BLOCK: "研究阻断已记录：原因类别未公开，停止晋级",
    HUMAN_REVIEW: "证据结构已闭合：下一步仅限人工研究复核",
    NO_STRUCTURAL_GAP: "当前无结构缺口：继续人工研究复核，仍非盈利证明",
    UNKNOWN: "先核固定快照：尚不能确定缺口类别",
  });

  const STATUS_PRESENTATIONS = Object.freeze({
    market: Object.freeze({
      READY: "行情证据可用于研究观察",
      STALE: "行情证据已过期 · 暂停形成新结论",
      UNKNOWN: "行情证据不足 · 等待可信快照",
      BLOCK: "行情证据阻断 · 停止数据消费",
    }),
    forward: Object.freeze({
      UP_TO_DATE: "已跟进至最新完成 K 线 · 仅观察",
      WAITING: "等待新完成 K 线 · 仅观察",
      DUE: "发现待处理完成 K 线 · 仅观察",
      PAUSED: "自然前向观察已暂停",
      UNKNOWN: "自然前向证据不足",
      BLOCK: "自然前向证据阻断",
    }),
    plan: Object.freeze({
      PLANNING_ONLY: "仅规划 · 不生成订单",
      NEEDS_EVIDENCE: "仅规划 · 仍缺关键证据",
      UNKNOWN: "纯规划证据不足",
      BLOCK: "纯规划证据阻断",
    }),
  });

  const PERMISSION_PRESENTATIONS = Object.freeze({
    market: "仅行情证据 · 不代表策略有效或交易授权",
    forward: "只读观察 · 模拟未授权 · 实盘永久硬锁",
    plan: "只读规划 · 不充值 · 不下单 · 模拟未授权 · 实盘永久硬锁",
    strategy: "研究解释 · 非订单 · 不授予模拟或实盘权限",
  });

  const SMALL_CAPITAL_EVIDENCE_LABELS = Object.freeze({
    permission_boundary: "权限边界",
    market_evidence: "行情证据",
    forward_evidence: "自然前向证据",
    fee_evidence: "费率与成本证据",
    instrument_rules: "现货规则证据",
    order_book_depth: "公开盘口深度证据",
    security_isolation: "安全隔离证据",
    circuit_breaker_reconciliation: "停止观察条件对账",
  });

  const FORWARD_EVIDENCE_GAPS = Object.freeze({
    BLOCK: "阻断原因复核证据",
    PAUSED: "只读调度或观察任务恢复证据",
    DUE: "本窗口只读观察作业收据",
    WAITING: "下一根可信完成 K 线",
    UP_TO_DATE: "下一根可信完成 K 线",
    UNKNOWN: "候选、只读调度与首个可信观察证据",
  });

  const MARKET_TRUTH_EVIDENCE_GAPS = Object.freeze({
    READY: "下一根可信完成 K 线",
    STALE: "报价与 K 线来源的新鲜度复核",
    BLOCK: "标的、周期、会话或数据完整性复核",
    UNKNOWN: "活动标的、报价来源、K 线来源与新鲜度证据",
  });

  const STRATEGY_FAILURE_TEXT_QUARANTINED = "来源文本含执行/授权语义，已隔离，需人工复核";
  const STRATEGY_FAILURE_ACTION_PATTERN = /(?:^|[^A-Z0-9])(?:READY|BUY|SELL|ADD|LONG|SHORT|COVER|EXIT|EXECUTE|EXECUTION|ORDER|TRADE|ARMED|AUTHORIZE|AUTHORIZED|AUTHORISE|AUTHORISED|AUTHORIZATION|AUTHORISATION|PERMISSION|PERMITTED|ALLOW|ALLOWED|ENABLE|ENABLED)(?:$|[^A-Z0-9])/i;
  const STRATEGY_FAILURE_AUTHORITY_PATTERN = /(?:授权|可下单|可交易|下单|执行|订单|买入|卖出|开仓|平仓|做多|做空|允许|许可|启用)/;
  const STRATEGY_FAILURE_MARKUP_PATTERN = /[<>]|&(?:lt|gt|#0*60|#x0*3c);/i;

  function normalizeStatus(value, fallback = "UNKNOWN") {
    const normalized = String(value || "").trim().toUpperCase();
    return normalized || fallback;
  }

  function internalBacktestEvidenceCue(kind, options = {}) {
    const safeKind = Object.prototype.hasOwnProperty.call(
      INTERNAL_BACKTEST_EVIDENCE_CUE_TEXT,
      kind,
    ) ? kind : "UNKNOWN";
    const count = Number.isSafeInteger(options.count) && options.count >= 0
      ? options.count
      : null;
    const text = typeof options.text === "string" && options.text.trim()
      ? options.text.trim()
      : INTERNAL_BACKTEST_EVIDENCE_CUE_TEXT[safeKind];
    return Object.freeze({
      evidenceGapKind: safeKind,
      evidenceGapText: text,
      evidenceGapCount: count,
      // Compatibility alias for the existing renderer contract. The value is
      // category-only and never contains a source blocker string.
      failureText: text,
    });
  }

  function verifiedInternalBacktestEvidenceCue(qualityState, promotionStatus, failureConditions) {
    const conditions = failureConditions
      && typeof failureConditions === "object"
      && !Array.isArray(failureConditions)
      ? failureConditions
      : {};
    const counts = Object.freeze({
      source: Array.isArray(conditions.source_integrity) ? conditions.source_integrity.length : 0,
      observed: Array.isArray(conditions.observed) ? conditions.observed.length : 0,
      evidence: Array.isArray(conditions.evidence_gaps) ? conditions.evidence_gaps.length : 0,
      promotion: Array.isArray(conditions.promotion_gaps) ? conditions.promotion_gaps.length : 0,
    });
    const total = counts.source + counts.observed + counts.evidence + counts.promotion;
    const categoryParts = [
      counts.source ? `来源完整性 ${counts.source} 项` : "",
      counts.observed ? `已观察失效 ${counts.observed} 项` : "",
      counts.evidence ? `待补研究证据 ${counts.evidence} 项` : "",
      counts.promotion ? `晋级复核缺口 ${counts.promotion} 项` : "",
    ].filter(Boolean);
    const categoryText = categoryParts.join(" · ");
    if (counts.source) {
      return internalBacktestEvidenceCue("SOURCE_BLOCK", {
        count: total,
        text: `${categoryText}；停止使用当前数字，先修复固定来源`,
      });
    }
    if (counts.observed) {
      return internalBacktestEvidenceCue("OBSERVED_BLOCK", {
        count: total,
        text: `已形成有效负结果，停止晋级 · ${categoryText}`,
      });
    }
    if (counts.evidence) {
      return internalBacktestEvidenceCue("EVIDENCE_GAP", {
        count: total,
        text: `先补研究证据 · ${categoryText}`,
      });
    }
    if (counts.promotion) {
      return internalBacktestEvidenceCue("PROMOTION_GAP", {
        count: total,
        text: `先补晋级复核证据 · ${categoryText}`,
      });
    }
    if (qualityState === "PARTIAL") {
      return internalBacktestEvidenceCue("PARTIAL_EVIDENCE");
    }
    if (qualityState === "BLOCK") {
      return internalBacktestEvidenceCue("RESEARCH_BLOCK");
    }
    if (promotionStatus === "REVIEW_REQUIRED") {
      return internalBacktestEvidenceCue("HUMAN_REVIEW");
    }
    return internalBacktestEvidenceCue("NO_STRUCTURAL_GAP");
  }

  function statusPresentation(kind, rawStatus) {
    const safeKind = Object.prototype.hasOwnProperty.call(STATUS_PRESENTATIONS, kind) ? kind : "market";
    const raw = normalizeStatus(rawStatus);
    const labels = STATUS_PRESENTATIONS[safeKind];
    return Object.freeze({
      rawStatus: raw,
      label: labels[raw] || labels.UNKNOWN,
      permissionText: PERMISSION_PRESENTATIONS[safeKind],
    });
  }

  function forwardEvidenceGapPresentation(input = {}) {
    const normalized = normalizeStatus(input.status);
    const rawStatus = Object.prototype.hasOwnProperty.call(FORWARD_EVIDENCE_GAPS, normalized)
      ? normalized
      : "UNKNOWN";
    return Object.freeze({
      rawStatus,
      gapKind: rawStatus === "BLOCK" ? "BLOCK" : rawStatus === "UNKNOWN" ? "UNKNOWN" : "MISSING",
      text: `下一条尚缺证据：${FORWARD_EVIDENCE_GAPS[rawStatus]} · 仅观察，不补写旧样本；不授予模拟或实盘权限`,
    });
  }

  function marketTruthEvidenceGapPresentation(input = {}) {
    const normalized = normalizeStatus(input.status);
    const rawStatus = Object.prototype.hasOwnProperty.call(MARKET_TRUTH_EVIDENCE_GAPS, normalized)
      ? normalized
      : "UNKNOWN";
    return Object.freeze({
      rawStatus,
      gapKind: rawStatus === "BLOCK" ? "BLOCK" : rawStatus === "UNKNOWN" ? "UNKNOWN" : "MISSING",
      text: `下一条尚缺证据：${MARKET_TRUTH_EVIDENCE_GAPS[rawStatus]} · 仅核行情，不生成策略结论或订单`,
    });
  }

  function smallCapitalEvidenceGapPresentation(input = {}) {
    const rawStatus = normalizeStatus(input.status);
    const checkId = String(input.checkId || "").trim();
    const evidenceLabel = Object.prototype.hasOwnProperty.call(
      SMALL_CAPITAL_EVIDENCE_LABELS,
      checkId,
    )
      ? SMALL_CAPITAL_EVIDENCE_LABELS[checkId]
      : "";

    if (rawStatus === "PLANNING_ONLY") {
      return Object.freeze({
        rawStatus,
        gapKind: "NONE",
        text: "下一条尚缺证据：无 · 仍仅规划，不生成订单",
      });
    }
    if (rawStatus === "NEEDS_EVIDENCE") {
      return Object.freeze({
        rawStatus,
        gapKind: "MISSING",
        text: evidenceLabel
          ? `下一条尚缺证据：${evidenceLabel} · 仅研究，不生成订单`
          : "下一条尚缺证据：关键只读证据未核验 · 仅研究，不生成订单",
      });
    }
    if (rawStatus === "BLOCK") {
      return Object.freeze({
        rawStatus,
        gapKind: "BLOCK",
        text: evidenceLabel
          ? `下一条尚缺证据：${evidenceLabel}（当前阻断）· 仅研究，不生成订单`
          : "下一条尚缺证据：只读规划证据合同完整性（当前阻断）· 仅研究，不生成订单",
      });
    }
    return Object.freeze({
      rawStatus,
      gapKind: "UNKNOWN",
      text: "下一条尚缺证据：尚未核验 · 仅研究，不生成订单",
    });
  }

  function strategySourceTextPresentation(value) {
    if (typeof value !== "string") return "";
    const text = value.trim();
    if (!text) return "";
    const detectionText = text.normalize("NFKC").replace(/[\u200B-\u200D\u2060\uFEFF]/g, "");
    const compactDetectionText = detectionText.replace(/[\s_.:/\\-]+/g, "");
    if (
      STRATEGY_FAILURE_ACTION_PATTERN.test(detectionText)
      || STRATEGY_FAILURE_AUTHORITY_PATTERN.test(compactDetectionText)
      || STRATEGY_FAILURE_MARKUP_PATTERN.test(detectionText)
    ) {
      return STRATEGY_FAILURE_TEXT_QUARANTINED;
    }
    return text;
  }

  function strategyEvidencePresentation(input = {}) {
    const hasEvidence = input.hasSignal === true
      || input.hasAnalysis === true
      || input.hasWarEvidence === true;
    const action = normalizeStatus(input.action, "WAIT");
    const direction = normalizeStatus(input.direction, "");
    const noTrade = Array.isArray(input.noTrade)
      ? [...new Set(input.noTrade.map(strategySourceTextPresentation).filter(Boolean))].slice(0, 3)
      : [];
    const probability = Number(input.probability);
    const probabilityKnown = input.probabilityKnown === true
      && Number.isFinite(probability)
      && probability >= 0
      && probability <= 1;

    if (!hasEvidence) {
      return Object.freeze({
        hasEvidence: false,
        conclusionText: "尚无研究结论",
        directionText: "方向未形成",
        estimateText: "模型估计未校准",
        noTradeText: "失效与禁做条件尚未核验",
        permissionText: PERMISSION_PRESENTATIONS.strategy,
      });
    }

    let conclusionText = "研究结论：待核验";
    if (["BUY", "ADD", "LONG"].includes(action)) conclusionText = "研究假设：偏多 · 非订单";
    else if (["SELL", "SHORT"].includes(action)) conclusionText = "研究假设：偏空 · 非订单";
    else if (["HALT", "BLOCK"].includes(action)) conclusionText = "研究结论：阻断";
    else if (["EXIT", "COVER"].includes(action)) conclusionText = "研究结论：退出观察 · 非订单";
    else if (["WAIT", "WATCH", "HOLD"].includes(action)) conclusionText = "研究结论：继续观察";

    const directionText = direction === "LONG"
      ? "研究方向：偏多 · 非订单"
      : direction === "SHORT"
        ? "研究方向：偏空 · 非订单"
        : "方向未形成";
    const estimateText = probabilityKnown
      ? `模型估计 ${Math.round(probability * 100)}% · 未校准`
      : "模型估计未校准";

    return Object.freeze({
      hasEvidence: true,
      conclusionText,
      directionText,
      estimateText,
      noTradeText: noTrade.length ? noTrade.join(" / ") : "失效与禁做条件尚未核验",
      permissionText: PERMISSION_PRESENTATIONS.strategy,
    });
  }

  function optionalFiniteNumber(value) {
    if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function firstFiniteNumber(...values) {
    for (const value of values) {
      const parsed = optionalFiniteNumber(value);
      if (parsed !== null) return parsed;
    }
    return null;
  }

  function fixedNumberText(value, digits = 2) {
    return Number(value).toFixed(digits);
  }

  function percentageText(value, digits = 2, signed = false) {
    if (value === null) return null;
    const prefix = signed && value > 0 ? "+" : "";
    return `${prefix}${fixedNumberText(value, digits)}%`;
  }

  const RISK_SURFACE_AXES = Object.freeze(["position_pct", "take_profit_pct", "stop_loss_pct"]);
  const RISK_SURFACE_GRID = Object.freeze({
    position_pct: Object.freeze([12, 20, 35, 50, 70]),
    take_profit_pct: Object.freeze([1.2, 1.8, 2.6, 3.8, 5.5]),
    stop_loss_pct: Object.freeze([0.7, 1.1, 1.6, 2.4]),
  });
  const RISK_SURFACE_FIELDS = Object.freeze([
    "schema_version", "status", "scope", "topology_basis", "grid_axis_order", "grid_axes",
    "expected_cell_count", "received_candidate_count", "mapped_cell_count", "missing_cell_count",
    "invalid_metric_count", "scored_cell_count", "usable_cell_count", "highest_score_cell",
    "score_tolerance", "score_tolerance_basis", "near_best_scored_cell_count",
    "near_best_usable_cell_count", "direct_adjacent_near_best_usable_count", "axis_support",
    "supported_axis_count", "connected_near_best_cell_count", "connected_near_best_cell_ids",
    "cells", "blockers", "risk_control_parameters_only", "signal_parameter_stability_checked",
    "numeric_parameter_distance_checked", "same_dataset_grid", "selection_bias_corrected",
    "out_of_sample_parameter_validation", "frozen_research_evidence", "research_only",
    "descriptive_only", "parameter_selection_allowed", "profitability_proven",
    "performance_claim_allowed", "automatic_paper_activation_allowed", "execution_allowed",
    "order_submission_allowed", "paper_authorized", "live_order_allowed",
  ]);
  const RISK_SURFACE_CELL_FIELDS = Object.freeze([
    "cell_id", "position_pct", "take_profit_pct", "stop_loss_pct", "score",
    "total_return_pct", "max_drawdown_pct", "trade_count", "run_ok", "quality_usable",
  ]);

  function exactKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value).sort();
    const target = [...expected].sort();
    return keys.length === target.length && keys.every((key, index) => key === target[index]);
  }

  function nativeFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  function nativeNonnegativeInteger(value) {
    return Number.isInteger(value) && value >= 0 ? value : null;
  }

  function riskSurfaceGridKey(cell) {
    if (!exactKeys(cell, RISK_SURFACE_CELL_FIELDS)) return null;
    const indexes = RISK_SURFACE_AXES.map((axis) => {
      if (nativeFiniteNumber(cell[axis]) === null) return -1;
      return RISK_SURFACE_GRID[axis].findIndex((value) => value === cell[axis]);
    });
    return indexes.some((index) => index < 0) ? null : indexes;
  }

  function riskSurfaceCellId(key) {
    return RISK_SURFACE_AXES
      .map((axis, index) => `${axis}=${RISK_SURFACE_GRID[axis][key[index]]}`)
      .join("|");
  }

  function riskSurfaceNeighbors(key) {
    const neighbors = [];
    RISK_SURFACE_AXES.forEach((axis, axisIndex) => {
      [-1, 1].forEach((step) => {
        const candidate = [...key];
        candidate[axisIndex] += step;
        if (candidate[axisIndex] >= 0 && candidate[axisIndex] < RISK_SURFACE_GRID[axis].length) {
          neighbors.push({ key: candidate, axis });
        }
      });
    });
    return neighbors;
  }

  function sameRiskSurfaceCell(left, right) {
    if (!exactKeys(left, RISK_SURFACE_CELL_FIELDS) || !exactKeys(right, RISK_SURFACE_CELL_FIELDS)) return false;
    return RISK_SURFACE_CELL_FIELDS.every((field) => left[field] === right[field]);
  }

  function validateBacktestRiskControlSurface(surface) {
    if (!surface || typeof surface !== "object" || Array.isArray(surface) || Object.keys(surface).length === 0) {
      return Object.freeze({ present: false, valid: true, rawStatus: "UNKNOWN" });
    }
    const status = normalizeStatus(surface.status);
    const allowedStatuses = new Set([
      "LOCAL_PLATEAU", "PEAK_ONLY", "HIGHEST_SCORE_CELL_UNUSABLE",
      "NON_POSITIVE_SURFACE", "INCOMPLETE_GRID", "NOT_AVAILABLE", "BLOCK",
    ]);
    const arrayExactly = (actual, expected) => Array.isArray(actual)
      && actual.length === expected.length
      && actual.every((value, index) => value === expected[index]);
    const stringList = (value) => Array.isArray(value)
      && value.every((item) => typeof item === "string" && item.length > 0)
      && new Set(value).size === value.length;
    const authorityClosed = surface.risk_control_parameters_only === true
      && surface.signal_parameter_stability_checked === false
      && surface.numeric_parameter_distance_checked === false
      && surface.same_dataset_grid === true
      && surface.selection_bias_corrected === false
      && surface.out_of_sample_parameter_validation === false
      && surface.frozen_research_evidence === false
      && surface.research_only === true
      && surface.descriptive_only === true
      && surface.parameter_selection_allowed === false
      && surface.profitability_proven === false
      && surface.performance_claim_allowed === false
      && surface.automatic_paper_activation_allowed === false
      && surface.execution_allowed === false
      && surface.order_submission_allowed === false
      && surface.paper_authorized === false
      && surface.live_order_allowed === false;
    const gridValid = exactKeys(surface.grid_axes, RISK_SURFACE_AXES)
      && arrayExactly(surface.grid_axis_order, RISK_SURFACE_AXES)
      && RISK_SURFACE_AXES.every((axis) => arrayExactly(surface.grid_axes[axis], RISK_SURFACE_GRID[axis]));
    const axisSupport = surface.axis_support;
    const axisSupportValid = exactKeys(axisSupport, RISK_SURFACE_AXES)
      && RISK_SURFACE_AXES.every((axis) => nativeNonnegativeInteger(axisSupport[axis]) !== null);
    const cells = Array.isArray(surface.cells) ? surface.cells : [];
    const mapped = new Map();
    let cellsValid = Array.isArray(surface.cells);
    let recomputedInvalidMetricCount = 0;
    let recomputedScoredCellCount = 0;
    let recomputedUsableCellCount = 0;
    cells.forEach((cell) => {
      const key = riskSurfaceGridKey(cell);
      if (!key) {
        cellsValid = false;
        return;
      }
      const keyText = key.join(",");
      const score = cell.score === null ? null : nativeFiniteNumber(cell.score);
      const totalReturn = cell.total_return_pct === null ? null : nativeFiniteNumber(cell.total_return_pct);
      const drawdown = cell.max_drawdown_pct === null ? null : nativeFiniteNumber(cell.max_drawdown_pct);
      const tradeCount = cell.trade_count === null ? null : nativeNonnegativeInteger(cell.trade_count);
      const metricInvalid = score === null || totalReturn === null || drawdown === null || drawdown < 0 || tradeCount === null;
      const expectedUsable = cell.run_ok === true
        && !metricInvalid
        && tradeCount > 0;
      if (
        mapped.has(keyText)
        || cell.cell_id !== riskSurfaceCellId(key)
        || typeof cell.run_ok !== "boolean"
        || typeof cell.quality_usable !== "boolean"
        || cell.quality_usable !== expectedUsable
      ) cellsValid = false;
      if (metricInvalid) recomputedInvalidMetricCount += 1;
      if (score !== null) recomputedScoredCellCount += 1;
      if (expectedUsable) recomputedUsableCellCount += 1;
      mapped.set(keyText, { cell, key, score });
    });

    const expectedKeys = [];
    RISK_SURFACE_GRID.position_pct.forEach((_position, positionIndex) => {
      RISK_SURFACE_GRID.take_profit_pct.forEach((_take, takeIndex) => {
        RISK_SURFACE_GRID.stop_loss_pct.forEach((_stop, stopIndex) => {
          expectedKeys.push([positionIndex, takeIndex, stopIndex]);
        });
      });
    });
    const receivedCount = nativeNonnegativeInteger(surface.received_candidate_count);
    const mappedCount = nativeNonnegativeInteger(surface.mapped_cell_count);
    const missingCount = nativeNonnegativeInteger(surface.missing_cell_count);
    const invalidMetricCount = nativeNonnegativeInteger(surface.invalid_metric_count);
    const scoredCellCount = nativeNonnegativeInteger(surface.scored_cell_count);
    const usableCellCount = nativeNonnegativeInteger(surface.usable_cell_count);
    const nearBestScoredCount = nativeNonnegativeInteger(surface.near_best_scored_cell_count);
    const nearBestUsableCount = nativeNonnegativeInteger(surface.near_best_usable_cell_count);
    const directAdjacentCount = nativeNonnegativeInteger(surface.direct_adjacent_near_best_usable_count);
    const supportedAxisCount = nativeNonnegativeInteger(surface.supported_axis_count);
    const connectedCount = nativeNonnegativeInteger(surface.connected_near_best_cell_count);
    const countsValid = surface.expected_cell_count === expectedKeys.length
      && receivedCount !== null
      && mappedCount === mapped.size
      && missingCount === expectedKeys.length - mapped.size
      && invalidMetricCount === recomputedInvalidMetricCount
      && scoredCellCount === recomputedScoredCellCount
      && usableCellCount === recomputedUsableCellCount
      && receivedCount >= mapped.size
      && nearBestScoredCount !== null
      && nearBestUsableCount !== null
      && directAdjacentCount !== null
      && supportedAxisCount !== null
      && connectedCount !== null;

    const scored = expectedKeys
      .map((key, index) => ({ entry: mapped.get(key.join(",")), index }))
      .filter(({ entry }) => entry && entry.score !== null);
    scored.sort((left, right) => right.entry.score - left.entry.score || left.index - right.index);
    const highest = scored.length ? scored[0].entry : null;
    const expectedTolerance = highest ? Math.max(Math.abs(highest.score) * 0.25, 1) : null;
    const declaredTolerance = surface.score_tolerance === null ? null : nativeFiniteNumber(surface.score_tolerance);
    let nearBestScored = new Set();
    let nearBestUsable = new Set();
    const recomputedAxisSupport = { position_pct: 0, take_profit_pct: 0, stop_loss_pct: 0 };
    const connected = new Set();
    if (highest) {
      nearBestScored = new Set(scored
        .filter(({ entry }) => highest.score - entry.score <= expectedTolerance)
        .map(({ entry }) => entry.key.join(",")));
      nearBestUsable = new Set([...nearBestScored]
        .filter((keyText) => mapped.get(keyText).cell.quality_usable === true));
      riskSurfaceNeighbors(highest.key).forEach(({ key, axis }) => {
        if (nearBestUsable.has(key.join(","))) recomputedAxisSupport[axis] += 1;
      });
      const highestKeyText = highest.key.join(",");
      if (nearBestUsable.has(highestKeyText)) {
        const queue = [highest.key];
        connected.add(highestKeyText);
        while (queue.length) {
          const current = queue.shift();
          riskSurfaceNeighbors(current).forEach(({ key }) => {
            const keyText = key.join(",");
            if (nearBestUsable.has(keyText) && !connected.has(keyText)) {
              connected.add(keyText);
              queue.push(key);
            }
          });
        }
      }
    }
    const expectedConnectedIds = expectedKeys
      .filter((key) => connected.has(key.join(",")))
      .map((key) => riskSurfaceCellId(key));
    const recomputedSupportedAxisCount = RISK_SURFACE_AXES
      .filter((axis) => recomputedAxisSupport[axis] > 0).length;
    const topologyValid = nearBestScoredCount === nearBestScored.size
      && nearBestUsableCount === nearBestUsable.size
      && directAdjacentCount === Object.values(recomputedAxisSupport).reduce((sum, value) => sum + value, 0)
      && supportedAxisCount === recomputedSupportedAxisCount
      && connectedCount === connected.size
      && RISK_SURFACE_AXES.every((axis) => axisSupport?.[axis] === recomputedAxisSupport[axis])
      && arrayExactly(surface.connected_near_best_cell_ids, expectedConnectedIds)
      && (expectedTolerance === null
        ? declaredTolerance === null
        : declaredTolerance !== null && Math.abs(declaredTolerance - expectedTolerance) <= 1e-9)
      && (highest === null
        ? surface.highest_score_cell === null
        : sameRiskSurfaceCell(surface.highest_score_cell, highest.cell));

    const blockers = surface.blockers;
    const structuralBlockers = new Set([
      "risk_control_surface_candidates_not_a_list",
      "risk_control_surface_candidate_not_an_object",
      "risk_control_surface_candidate_outside_frozen_grid",
      "risk_control_surface_duplicate_grid_cell",
      "risk_control_surface_cell_metrics_invalid",
    ]);
    const allowedBlockers = new Set([
      ...structuralBlockers,
      "risk_control_surface_grid_coverage_incomplete",
      "risk_control_surface_not_available",
      "risk_control_surface_no_finite_scores",
      "risk_control_surface_best_score_not_positive",
      "risk_control_surface_highest_score_cell_metrics_unusable",
      "risk_control_surface_peak_without_multiaxis_neighborhood",
    ]);
    const blockersValid = stringList(blockers) && blockers.every((blocker) => allowedBlockers.has(blocker));
    const hasStructuralBlocker = blockersValid && blockers.some((blocker) => structuralBlockers.has(blocker));
    let expectedStatus = "BLOCK";
    if (
      receivedCount === 0
      && mappedCount === 0
      && blockersValid
      && arrayExactly(blockers, ["risk_control_surface_not_available"])
    ) expectedStatus = "NOT_AVAILABLE";
    else if (hasStructuralBlocker) expectedStatus = "BLOCK";
    else if (missingCount > 0) expectedStatus = "INCOMPLETE_GRID";
    else if (!highest) expectedStatus = "BLOCK";
    else if (highest.score <= 0) expectedStatus = "NON_POSITIVE_SURFACE";
    else if (highest.cell.quality_usable !== true) expectedStatus = "HIGHEST_SCORE_CELL_UNUSABLE";
    else if (connected.size >= 3 && recomputedSupportedAxisCount >= 2) expectedStatus = "LOCAL_PLATEAU";
    else expectedStatus = "PEAK_ONLY";
    const requiredBlockerByStatus = {
      NOT_AVAILABLE: "risk_control_surface_not_available",
      INCOMPLETE_GRID: "risk_control_surface_grid_coverage_incomplete",
      NON_POSITIVE_SURFACE: "risk_control_surface_best_score_not_positive",
      HIGHEST_SCORE_CELL_UNUSABLE: "risk_control_surface_highest_score_cell_metrics_unusable",
      PEAK_ONLY: "risk_control_surface_peak_without_multiaxis_neighborhood",
    };
    const statusBlockerValid = expectedStatus === "LOCAL_PLATEAU"
      ? blockersValid && blockers.length === 0
      : expectedStatus === "BLOCK"
        ? blockersValid && blockers.length > 0
        : blockersValid && blockers.includes(requiredBlockerByStatus[expectedStatus]);
    const valid = exactKeys(surface, RISK_SURFACE_FIELDS)
      && surface.schema_version === "backtest-risk-control-surface-v1"
      && allowedStatuses.has(status)
      && status === expectedStatus
      && surface.scope === "SAME_DATASET_DEVELOPMENT_GRID"
      && surface.topology_basis === "ONE_FROZEN_GRID_STEP_PER_AXIS"
      && surface.score_tolerance_basis === "MAX_25_PERCENT_OF_BEST_ABSOLUTE_OR_1_POINT"
      && authorityClosed
      && gridValid
      && axisSupportValid
      && cellsValid
      && countsValid
      && topologyValid
      && statusBlockerValid;
    return Object.freeze({ present: true, valid, rawStatus: valid ? status : "UNKNOWN" });
  }

  function backtestEvidencePresentation(input = {}) {
    const current = input.current || {};
    const reproducibility = input.reproducibility || {};
    const hasResult = current.ok === true;
    const totalReturn = hasResult ? optionalFiniteNumber(current.total_return_pct) : null;
    const benchmarkReturn = hasResult
      ? firstFiniteNumber(current.benchmark_return_pct, input.benchmarkReturnPct)
      : null;
    const annualized = hasResult ? optionalFiniteNumber(current.annualized_pct) : null;
    const drawdown = hasResult ? optionalFiniteNumber(current.max_drawdown_pct) : null;
    const winRate = hasResult ? optionalFiniteNumber(current.win_rate_pct) : null;
    const sharpe = hasResult ? optionalFiniteNumber(current.sharpe) : null;
    const trades = hasResult ? optionalFiniteNumber(current.trade_count) : null;
    const dataPoints = firstFiniteNumber(reproducibility.data_points, input.dataPoints, current.data_points);
    const feeRate = optionalFiniteNumber(reproducibility.fee_rate);
    const slippageBps = optionalFiniteNumber(reproducibility.slippage_bps);
    const explicitCostFlags = [
      input.costsIncluded,
      current.costs_included,
      reproducibility.costs_included,
    ].filter((value) => typeof value === "boolean");
    const costsIncluded = explicitCostFlags.includes(false)
      ? false
      : explicitCostFlags.includes(true)
        ? true
        : null;
    const temporalRaw = normalizeStatus(input.temporalStatus, "UNKNOWN");
    const temporalState = pipelineStateKind(temporalRaw);
    const temporalLabels = {
      verified: "样本外证据已记录 · 非授权",
      active: "样本外证据核对中 · 非授权",
      review: "样本外证据待人工复核",
      blocked: "样本外证据存在阻断",
      waiting: "样本外证据未核验",
    };

    const returnText = percentageText(totalReturn, 2, true) || "累计收益未提供";
    const benchmarkText = percentageText(benchmarkReturn, 2, true) || "基准收益未提供";
    const excessValue = totalReturn !== null && benchmarkReturn !== null
      ? totalReturn - benchmarkReturn
      : null;
    const excessText = percentageText(excessValue, 2, true);
    const feeText = feeRate === null ? "费率未提供" : `费率 ${String(reproducibility.fee_rate).trim()}`;
    const slippageText = slippageBps === null
      ? "滑点未提供"
      : `滑点 ${String(reproducibility.slippage_bps).trim()} bps`;
    const returnBasisText = !hasResult
      ? "尚无可解释的开发回测结果"
      : costsIncluded === true
        ? "返回合同声明已计入成本 · 仍非盈利证明"
        : costsIncluded === false
          ? "返回合同声明未计入成本 · 非净收益"
          : "成本是否计入未核验 · 不得视为净收益";

    return Object.freeze({
      hasResult,
      returnText,
      benchmarkText,
      excessText: excessText ? `超额 ${excessText}` : "超额收益不可计算",
      costsText: `${feeText} · ${slippageText}`,
      returnBasisText,
      drawdownText: percentageText(drawdown, 2, false) || "最大回撤未提供",
      sampleText: Number.isInteger(dataPoints) && dataPoints >= 0 ? `${dataPoints} 根 K 线` : "样本量未提供",
      tradesText: Number.isInteger(trades) && trades >= 0 ? `${trades} 笔闭合交易` : "闭合交易数未提供",
      annualizedText: percentageText(annualized, 2, true) || "年化收益未提供",
      winRateText: percentageText(winRate, 1, false) || "胜率未提供",
      sharpeText: sharpe === null ? "夏普未提供" : fixedNumberText(sharpe, 2),
      rawTemporalStatus: temporalRaw,
      temporalText: temporalLabels[temporalState],
      boundaryText: "开发回测 · 非盈利证明 · 模拟未授权 · 实盘永久硬锁",
    });
  }

  function backtestRobustnessPresentation(payload = {}) {
    const empty = Object.freeze({
      valid: false,
      modeText: "时间稳健性证据未核验",
      temporalText: "验证/测试时间切片未提供",
      foldsText: "固定参数折叠未提供",
      costText: "成本压力未提供",
      parameterText: "风险控制参数表面未提供 · 策略信号参数平台未连接",
      surfaceStatusText: "风险控制参数表面未核验",
      surfaceCoverageText: "同数据开发网格覆盖未核验",
      surfaceNeighborhoodText: "局部邻域未核验",
      causalText: "因果/前视检查未提供",
      failureText: "稳健性失败条件/证据缺口未核验",
      rawTemporalStatus: "UNKNOWN",
      rawFoldStatus: "UNKNOWN",
      rawCostStatus: "UNKNOWN",
      rawSurfaceStatus: "UNKNOWN",
      rawCausalStatus: "UNKNOWN",
      permissionText: PERMISSION_PRESENTATIONS.strategy,
    });
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return empty;
    const temporal = payload.temporal_validation;
    const temporalObject = temporal && typeof temporal === "object" && !Array.isArray(temporal)
      ? temporal
      : {};
    const walk = temporalObject.walk_forward;
    const walkObject = walk && typeof walk === "object" && !Array.isArray(walk) ? walk : {};
    const cost = temporalObject.cost_sensitivity;
    const costObject = cost && typeof cost === "object" && !Array.isArray(cost) ? cost : {};
    const lookahead = payload.lookahead_check;
    const lookaheadObject = lookahead && typeof lookahead === "object" && !Array.isArray(lookahead)
      ? lookahead
      : {};
    const surface = payload.risk_control_surface;
    const surfaceObject = surface && typeof surface === "object" && !Array.isArray(surface)
      ? surface
      : {};
    const hasEvidence = Object.keys(temporalObject).length > 0
      || Object.keys(walkObject).length > 0
      || Object.keys(costObject).length > 0
      || Object.keys(surfaceObject).length > 0
      || Object.keys(lookaheadObject).length > 0;
    if (!hasEvidence) return empty;

    const status = (value) => normalizeStatus(value);
    const statusLabel = (value) => researchEvidenceStatusPresentation(status(value)).label;
    const finite = (value) => optionalFiniteNumber(value);
    const integer = (value) => Number.isInteger(value) && value >= 0 ? value : null;
    const percent = (value) => {
      const parsed = finite(value);
      return parsed === null ? "未提供" : `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}%`;
    };
    const temporalStatus = status(temporalObject.temporal_status || temporalObject.status);
    const foldStatus = status(walkObject.status);
    const costStatus = status(costObject.status);
    const causalStatus = status(lookaheadObject.status);
    const surfaceValidation = validateBacktestRiskControlSurface(surfaceObject);
    const surfaceStatus = surfaceValidation.rawStatus;
    const fixedParameterSlices = walkObject.evaluation_mode === "FIXED_PARAMETER_CHRONOLOGICAL_SLICES"
      && walkObject.parameters_refit_per_fold === false
      && walkObject.walk_forward_optimization_claim_allowed === false;
    const splitSegments = temporalObject.data_split?.segments;
    const validationCount = integer(splitSegments?.validation?.count);
    const testCount = integer(splitSegments?.test?.count);
    const validationReport = temporalObject.temporal_segments?.validation;
    const testReport = temporalObject.temporal_segments?.test;
    const validationReturn = finite(validationReport?.total_return_pct);
    const testReturn = finite(testReport?.total_return_pct);
    const foldCount = integer(walkObject.fold_count);
    const usableFolds = integer(walkObject.usable_folds);
    const positiveFolds = integer(walkObject.positive_folds);
    const totalTrades = integer(walkObject.total_trades);
    const expectedCells = integer(surfaceObject.expected_cell_count);
    const mappedCells = integer(surfaceObject.mapped_cell_count);
    const missingCells = integer(surfaceObject.missing_cell_count);
    const usableCells = integer(surfaceObject.usable_cell_count);
    const nearBestCells = integer(surfaceObject.near_best_usable_cell_count);
    const connectedCells = integer(surfaceObject.connected_near_best_cell_count);
    const supportedAxes = integer(surfaceObject.supported_axis_count);
    const surfaceContractValid = surfaceValidation.valid;
    const worstCostReturn = finite(costObject.worst_return_pct) ?? Math.min(
      ...(Array.isArray(costObject.scenarios)
        ? costObject.scenarios.map((item) => finite(item?.total_return_pct)).filter((value) => value !== null)
        : []),
    );
    const breakEven = costObject.break_even_preserved === true
      ? "压力仍保持正值"
      : costObject.break_even_preserved === false
        ? "压力未保持正值"
        : "正值条件未核验";
    const blockers = [
      ...(Array.isArray(temporalObject.temporal_blockers) ? temporalObject.temporal_blockers : []),
      ...(Array.isArray(walkObject.blockers) ? walkObject.blockers : []),
      ...(Array.isArray(costObject.blockers) ? costObject.blockers : []),
      ...(Array.isArray(surfaceObject.blockers) ? surfaceObject.blockers : []),
      ...(Array.isArray(lookaheadObject.blockers) ? lookaheadObject.blockers : []),
    ]
      .filter((item) => typeof item === "string" && item.trim())
      .map((item) => item.trim().slice(0, 120))
      .filter((item, index, list) => list.indexOf(item) === index)
      .slice(0, 4);
    const surfaceLabels = {
      LOCAL_PLATEAU: "局部近优区域跨至少两条风险控制轴连通",
      PEAK_ONLY: "最高分附近缺少跨轴局部支撑 · 峰值敏感",
      HIGHEST_SCORE_CELL_UNUSABLE: "最高分单元缺少可用成交/风险指标",
      NON_POSITIVE_SURFACE: "网格最高分不为正",
      INCOMPLETE_GRID: "同数据开发网格覆盖不完整",
      NOT_AVAILABLE: "风险控制参数表面未提供",
      BLOCK: "风险控制参数表面合同阻断",
    };
    const surfaceMode = Object.keys(surfaceObject).length === 0
      ? "风险控制参数表面未提供"
      : surfaceContractValid
        ? (surfaceLabels[surfaceStatus] || "风险控制参数表面状态未核验")
        : "风险控制参数表面合同未核验";
    const surfaceCoverageText = surfaceContractValid && expectedCells !== null
      ? `同数据开发网格 ${mappedCells}/${expectedCells} · 可用 ${usableCells} · 缺失 ${missingCells}`
      : "同数据开发网格覆盖未核验";
    const surfaceNeighborhoodText = surfaceContractValid && connectedCells !== null
      ? `近优可用 ${nearBestCells} · 连通 ${connectedCells} · 直接支撑轴 ${supportedAxes}/3 · 非数值距离`
      : "局部邻域未核验";
    return Object.freeze({
      valid: surfaceContractValid,
      modeText: fixedParameterSlices
        ? "固定参数时间切片 · 非真正 walk-forward optimization"
        : "时间稳健性模式待核验",
      temporalText: `${statusLabel(temporalStatus)} · 验证 ${validationCount === null ? "未提供" : validationCount} 行${validationReturn === null ? "" : ` / ${percent(validationReturn)}`} · 测试 ${testCount === null ? "未提供" : testCount} 行${testReturn === null ? "" : ` / ${percent(testReturn)}`}`,
      foldsText: `固定参数折叠 ${foldCount === null ? "未提供" : foldCount} · 可用 ${usableFolds === null ? "未提供" : usableFolds} · 正收益 ${positiveFolds === null ? "未提供" : positiveFolds} · 闭合交易 ${totalTrades === null ? "未提供" : totalTrades}`,
      costText: `${statusLabel(costStatus)} · 压力最差 ${percent(worstCostReturn)} · ${breakEven}`,
      parameterText: `${surfaceMode} · 仅仓位/止盈/止损；策略信号参数平台仍需冻结报告`,
      surfaceStatusText: surfaceMode,
      surfaceCoverageText,
      surfaceNeighborhoodText,
      causalText: statusLabel(causalStatus),
      failureText: blockers.length
        ? `阻断/缺口：${blockers.join(" / ")}`
        : "未记录额外阻断 · 仍非盈利证明，不授予模拟或实盘权限",
      rawTemporalStatus: temporalStatus,
      rawFoldStatus: foldStatus,
      rawCostStatus: costStatus,
      rawSurfaceStatus: surfaceStatus,
      rawCausalStatus: causalStatus,
      permissionText: PERMISSION_PRESENTATIONS.strategy,
    });
  }

  const PIPELINE_VERIFIED_STATUSES = new Set([
    "PASS",
    "READY",
    "COMPLETE",
    "COMPLETED",
    "DONE",
    "SUCCESS",
    "SUCCEEDED",
    "PAPER_READY",
    "PAPER_RUNNING",
    "PAPER_MANUAL_READY",
    "PAPER_STRATEGY_READY",
    "RESTART_READY",
    "RESEARCH_VERIFIED",
  ]);
  const PIPELINE_ACTIVE_STATUSES = new Set(["RUNNING", "ACTIVE", "IN_PROGRESS", "RESEARCH_REVIEW"]);
  const PIPELINE_REVIEW_STATUSES = new Set(["WARN", "WARNING", "REVIEW", "NEEDS_REVIEW"]);
  const PIPELINE_BLOCKED_STATUSES = new Set([
    "BLOCK",
    "BLOCKED",
    "ERROR",
    "FAILED",
    "REJECTED",
    "UNSAFE",
    "LEGACY_BLOCKED",
    "VALIDATION_BLOCKED",
    "RESEARCH_BLOCKED",
  ]);

  function pipelineStateKind(rawStatus) {
    const raw = normalizeStatus(rawStatus);
    if (PIPELINE_VERIFIED_STATUSES.has(raw)) return "verified";
    if (PIPELINE_ACTIVE_STATUSES.has(raw)) return "active";
    if (PIPELINE_REVIEW_STATUSES.has(raw)) return "review";
    if (PIPELINE_BLOCKED_STATUSES.has(raw)) return "blocked";
    return "waiting";
  }

  function pipelineSummaryPresentation(rawStatus, hasRun = false) {
    const raw = normalizeStatus(rawStatus, hasRun ? "UNKNOWN" : "NOT_STARTED");
    const stateKind = hasRun ? pipelineStateKind(raw) : "waiting";
    const labels = {
      verified: "研究证据链已核对 · 不授予模拟或实盘权限",
      active: "研究证据核对进行中 · 不授予模拟或实盘权限",
      review: "研究证据链待人工复核 · 不授予模拟或实盘权限",
      blocked: "研究证据链存在阻断 · 不授予模拟或实盘权限",
      waiting: hasRun
        ? "研究证据链尚未形成 · 不授予模拟或实盘权限"
        : "尚无已登记研究证据 · 不授予模拟或实盘权限",
    };
    return Object.freeze({
      rawStatus: raw,
      stateKind,
      label: labels[stateKind],
    });
  }

  function pipelineStagePresentation(stageKey, rawStatus, context = {}) {
    const key = String(stageKey || "").trim().toLowerCase();
    const raw = normalizeStatus(rawStatus, key === "live_trading" ? "BLOCKED" : "WAIT");
    const stateKind = pipelineStateKind(raw);
    const paperAuthorized = context.paperAuthorized === true;
    const liveHardLocked = context.liveHardLocked === true;

    if (key === "paper_authorization") {
      return Object.freeze({
        rawStatus: raw,
        stateKind: paperAuthorized && stateKind === "verified" ? "verified" : "waiting",
        label: paperAuthorized && stateKind === "verified"
          ? "模拟权限证据已核对 · 非实盘"
          : "模拟未授权",
        detailText: "模拟权限与研究证据分离",
      });
    }

    if (key === "paper_run") {
      let label = "模拟未授权 · 未运行";
      if (paperAuthorized && stateKind === "verified") label = "模拟运行证据已记录 · 非实盘";
      else if (paperAuthorized && stateKind === "active") label = "模拟运行证据记录中 · 非实盘";
      else if (paperAuthorized && stateKind === "blocked") label = "模拟运行证据存在阻断 · 非实盘";
      else if (paperAuthorized && stateKind === "review") label = "模拟运行证据待人工复核 · 非实盘";
      else if (paperAuthorized) label = "模拟已授权 · 尚未运行 · 非实盘";
      return Object.freeze({
        rawStatus: raw,
        stateKind: paperAuthorized ? stateKind : "waiting",
        label,
        detailText: paperAuthorized ? "仅模拟证据 · 不授予实盘权限" : "模拟权限与研究证据分离",
      });
    }

    if (key === "live_trading") {
      return Object.freeze({
        rawStatus: raw,
        stateKind: "locked",
        label: liveHardLocked ? "实盘永久硬锁" : "实盘保护未确认 · 禁止执行",
        detailText: "AI、回测与研究证据不得解锁实盘",
      });
    }

    const labels = {
      verified: "研究证据已核对 · 非授权",
      active: "研究证据核对中 · 非授权",
      review: "研究证据待人工复核",
      blocked: "研究证据存在阻断",
      waiting: "等待研究证据",
    };
    return Object.freeze({
      rawStatus: raw,
      stateKind,
      label: labels[stateKind],
      detailText: "研究证据不授予模拟或实盘权限",
    });
  }

  function researchEvidenceStatusPresentation(rawStatus) {
    const raw = normalizeStatus(rawStatus, "WAIT");
    const stateKind = pipelineStateKind(raw);
    const labels = {
      verified: "研究证据已核对 · 非授权",
      active: "研究证据核对中 · 非授权",
      review: "研究证据待人工复核",
      blocked: "研究证据存在阻断",
      waiting: "等待研究证据",
    };
    return Object.freeze({
      rawStatus: raw,
      stateKind,
      label: raw === "RESEARCH_OBSERVE" ? "研究观察 · 待核验" : labels[stateKind],
      detailText: "仅研究证据 · 不授予模拟或实盘权限",
    });
  }

  function strategyLabEvidencePresentation(payload = {}) {
    if (
      payload
      && typeof payload === "object"
      && !Array.isArray(payload)
      && Object.prototype.hasOwnProperty.call(payload, "correlation_cluster_summary")
    ) {
      payload = { ...payload };
      delete payload.correlation_cluster_summary;
    }
    const emptyConditionRows = Object.freeze([]);
    const empty = Object.freeze({
      valid: false,
      connectionStatus: "UNKNOWN",
      modeText: "即时启发式规划 · 未形成冻结研究证据",
      sourceText: "冻结来源未核验",
      implementationText: "策略信号实现：未核验",
      currentnessText: "数据新鲜度与报告年龄门槛：未核验",
      hypothesisText: "事前研究假设：未核验",
      lineageText: "检索谱系：未核验",
      hypothesisFailureText: "事前失效条件：未核验",
      admissionText: "事前研究门禁：未核验",
      mechanismConditionText: "开发期机制条件：未核验",
      futureConditionText: "未来标准条件：未核验 · 未评估、非通过",
      mechanismConditionRows: emptyConditionRows,
      futureConditionRows: emptyConditionRows,
      postSelectionText: "冻结后历史复算：未核验 · 非自然前向",
      frozenTestText: "冻结 TEST 历史复算：未核验 · 非盈利证明",
      holdoutText: "单次历史留出：未核验 · 非自然前向 · 非盈利证明",
      parameterText: "参数平台稳定性：未核验",
      costText: "成本压力：未核验",
      temporalText: "固定参数时间切片：未核验",
      coverageText: "研究覆盖未核验",
      failureText: "失效条件与证据缺口：未核验",
      detailText: "开发期分只作描述，不选参、不证明盈利；模拟未授权，实盘永久硬锁",
      rawParameterStatus: "UNKNOWN",
      rawCostStatus: "UNKNOWN",
      rawTemporalStatus: "UNKNOWN",
      rawImplementationStatus: "UNKNOWN",
      rawFullImplementationStatus: "UNKNOWN",
      rawHypothesisStatus: "UNKNOWN",
      rawSearchLineageStatus: "UNKNOWN",
      rawAdmissionStatus: "UNKNOWN",
      rawMechanismStatus: "UNKNOWN",
      rawFutureConditionStatus: "UNKNOWN",
      rawPostSelectionStatus: "UNKNOWN",
      rawFrozenTestStatus: "UNKNOWN",
      rawHoldoutStatus: "UNKNOWN",
      permissionText: PERMISSION_PRESENTATIONS.plan,
    });
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return empty;
    const contract = payload.evidence_contract;
    if (!contract || typeof contract !== "object" || Array.isArray(contract)) return empty;
    const authorityKey = (value) => String(value || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "");
    const localizedAuthorityKey = (value) => String(value || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[\s_\-./\\:：]/g, "");
    const localizedAuthorityField = (value) => (
      /(?:授权|可下单|可交易|允许下单|允许交易|交易许可|执行许可|执行允许|模拟许可|实盘许可|自动下单)/
        .test(localizedAuthorityKey(value))
    );
    const authorityFields = new Set([
      "armed",
      "automatic_paper_activation_allowed",
      "automated_paper_order_allowed",
      "binding_authorized",
      "can_execute",
      "can_trade",
      "direction_signal_allowed",
      "execution_allowed",
      "live_order_allowed",
      "live_ready",
      "live_trading_allowed",
      "live_trading_enabled",
      "mission_authorized",
      "order_allowed",
      "paper_activation_allowed",
      "paper_authorized",
      "paper_armed",
      "paper_order_allowed",
      "paper_ready",
      "parameter_selection_allowed",
      "parameter_selection_authority",
      "performance_claim_allowed",
      "performance_claim_proven",
      "profitability_proven",
      "role_assignment_allowed",
      "runtime_mutations_allowed",
      "selection_allowed",
      "trade_allowed",
    ].map(authorityKey));
    const authoritySafe = (value) => {
      if (Array.isArray(value)) return value.every(authoritySafe);
      if (!value || typeof value !== "object") return true;
      return Object.entries(value).every(([key, nested]) => (
        (
          (!authorityFields.has(authorityKey(key)) && !localizedAuthorityField(key))
          || nested === false
        ) && authoritySafe(nested)
      ));
    };
    const status = (value) => normalizeStatus(value);
    const parameterStatus = status(contract.parameter_stability_status);
    const costStatus = status(contract.cost_sensitivity_status);
    const temporalStatus = status(contract.chronological_slice_status);
    const boundaryOnly = [parameterStatus, costStatus, temporalStatus]
      .every((value) => value === "NOT_CONNECTED");
    const boundaryValid = contract.schema_version === "strategy-lab-evidence-boundary-v1"
      && contract.mode === "DEVELOPMENT_HEURISTIC_PLANNING_ONLY"
      && contract.research_report_source === "FROZEN_RESEARCH_REPORT_NOT_CONNECTED"
      && contract.interpretation === "DESCRIPTIVE_PLANNING_ONLY"
      && contract.research_only === true
      && contract.descriptive_only === true
      && contract.development_heuristic_only === true
      && contract.profitability_proven === false
      && contract.performance_claim_allowed === false
      && contract.parameter_selection_allowed === false
      && contract.paper_authorized === false
      && contract.live_order_allowed === false
      && boundaryOnly
      && authoritySafe(payload);
    if (boundaryValid) {
      return Object.freeze({
        valid: true,
        connectionStatus: "BOUNDARY_ONLY",
        modeText: "即时启发式规划 · 未接入冻结研究报告",
        sourceText: "固定研究报告尚未连接",
        implementationText: "策略信号实现：未连接",
        currentnessText: "数据新鲜度与报告年龄门槛：未连接",
        hypothesisText: "事前研究假设：未连接",
        lineageText: "检索谱系：未连接",
        hypothesisFailureText: "事前失效条件：未连接",
        admissionText: "事前研究门禁：未连接",
        mechanismConditionText: "开发期机制条件：未连接",
        futureConditionText: "未来标准条件：未连接 · 未评估、非通过",
        mechanismConditionRows: emptyConditionRows,
        futureConditionRows: emptyConditionRows,
        postSelectionText: "冻结后历史复算：未连接 · 非自然前向",
        frozenTestText: "冻结 TEST 历史复算：未连接 · 非盈利证明",
        holdoutText: "单次历史留出：未连接 · 非自然前向 · 非盈利证明",
        parameterText: "参数平台稳定性：未连接",
        costText: "成本压力：未连接",
        temporalText: "固定参数时间切片：未连接",
        coverageText: "研究覆盖：未连接",
        failureText: "失效条件与证据缺口：未连接",
        detailText: "开发期分不用于选参；需独立研究 runner 证据，模拟未授权，实盘永久硬锁",
        rawParameterStatus: parameterStatus,
        rawCostStatus: costStatus,
        rawTemporalStatus: temporalStatus,
        rawImplementationStatus: "NOT_CONNECTED",
        rawFullImplementationStatus: "NOT_CONNECTED",
        rawHypothesisStatus: "NOT_CONNECTED",
        rawSearchLineageStatus: "NOT_CONNECTED",
        rawAdmissionStatus: "NOT_CONNECTED",
        rawMechanismStatus: "NOT_CONNECTED",
        rawFutureConditionStatus: "NOT_CONNECTED",
        rawPostSelectionStatus: "NOT_CONNECTED",
        rawFrozenTestStatus: "NOT_CONNECTED",
        rawHoldoutStatus: "NOT_CONNECTED",
        permissionText: PERMISSION_PRESENTATIONS.plan,
      });
    }

    const isObject = (value) => value
      && typeof value === "object"
      && !Array.isArray(value);
    const finiteOrNull = (value) => value === null
      || (typeof value === "number" && Number.isFinite(value));
    const nonnegativeIntegerOrNull = (value) => value === null
      || (Number.isSafeInteger(value) && value >= 0);
    const stringList = (value) => Array.isArray(value)
      && value.every((item) => typeof item === "string");
    const hash256 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
    const hasOwn = (value, key) => isObject(value)
      && Object.prototype.hasOwnProperty.call(value, key);
    const exactKeys = (value, fields) => isObject(value)
      && Object.keys(value).length === fields.length
      && fields.every((field) => hasOwn(value, field));
    const safeScope = (value) => isObject(value)
      && value.research_only === true
      && value.descriptive_only === true
      && value.profitability_proven === false
      && value.performance_claim_allowed === false
      && value.parameter_selection_allowed === false
      && value.paper_authorized === false
      && value.live_order_allowed === false;
    const scope = payload.scope;
    const plateau = payload.parameter_stability;
    const hypothesis = payload.hypothesis_preregistration;
    const searchLineage = payload.search_lineage;
    const admission = payload.preregistered_failure_admission;
    const postSelection = payload.post_selection_replay_summary;
    const cost = payload.cost_sensitivity;
    const chronological = payload.chronological_slices;
    const implementation = payload.implementation_currentness;
    const fullImplementation = payload.full_implementation_currentness;
    const currentness = payload.currentness_facts;
    const failureConditions = payload.failure_conditions;
    const matchStatus = status(payload.strategy_match_status);
    const contractMatchStatus = status(contract.strategy_match_status);
    const matched = matchStatus === "MATCHED";
    const noMatch = matchStatus === "NOT_IN_REPORT";
    const hypothesisStatus = status(hypothesis?.status);
    const searchLineageStatus = status(searchLineage?.status);
    const policy = status(payload.selection_test_policy);
    const formalBoundaryValid = payload.formal_single_use === true
      ? policy === "BLIND_ONCE"
      : payload.formal_single_use === false && policy === "DEVELOPMENT_ONLY";
    const hypothesisV1CommonValid = isObject(hypothesis)
      && hypothesis.schema_version === "strategy-hypothesis-preregistration-summary-v1"
      && safeScope(hypothesis)
      && hypothesis.automatic_paper_activation_allowed === false
      && hypothesis.walk_forward_optimization_claim_allowed === false
      && stringList(hypothesis.strategy_ids)
      && new Set(hypothesis.strategy_ids).size === hypothesis.strategy_ids.length
      && stringList(hypothesis.mechanism_specific_failure_conditions)
      && stringList(hypothesis.blockers);
    const mechanismConditionFields = [
      "condition_id",
      "evidence_stage",
      "metric",
      "operator",
      "threshold",
      "required_action",
    ];
    const mechanismMetrics = new Set([
      "validation_adjusted_score",
      "median_validation_return_pct",
      "median_validation_excess_return_pct",
      "validation_worst_drawdown_pct",
      "validation_trade_count",
      "minimum_stressed_return_pct",
      "minimum_positive_fold_count",
    ]);
    const mechanismOperators = new Set(["LT", "LTE", "GT", "GTE"]);
    const validMechanismCondition = (condition) => exactKeys(condition, mechanismConditionFields)
      && typeof condition.condition_id === "string"
      && /^[a-z][a-z0-9_]{2,63}$/.test(condition.condition_id)
      && condition.evidence_stage === "DEVELOPMENT_SELECTION"
      && mechanismMetrics.has(condition.metric)
      && mechanismOperators.has(condition.operator)
      && typeof condition.threshold === "number"
      && Number.isFinite(condition.threshold)
      && condition.required_action === "BLOCK_RESEARCH";
    const hypothesisV2Fields = [
      "schema_version",
      "descriptive_only",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "research_only",
      "paper_authorized",
      "live_order_allowed",
      "status",
      "contract_checked",
      "hypothesis_id",
      "hypothesis_hash",
      "research_generation",
      "strategy_ids",
      "selected_strategy_match",
      "mechanism_family",
      "mechanism_specific_failure_conditions",
      "parameter_topology_basis",
      "numeric_parameter_distance_claimed",
      "cost_stress_required",
      "stressed_return_must_remain_positive",
      "chronological_evaluation_mode",
      "parameters_refit_per_fold",
      "walk_forward_optimization_claim_allowed",
      "fresh_single_use_holdout_required",
      "minimum_natural_forward_outcomes",
      "minimum_executed_rebalances",
      "statistical_contract_recheck_required_at_maturity",
      "historical_backtest_can_substitute_natural_forward",
      "reuses_falsified_strategy_id",
      "retunes_falsified_mechanism",
      "material_mechanism_change_requires_new_strategy_id",
      "blockers",
      "source_schema_version",
    ];
    const hypothesisV2Conditions = Array.isArray(hypothesis?.mechanism_specific_failure_conditions)
      ? hypothesis.mechanism_specific_failure_conditions
      : [];
    const hypothesisV2ConditionIds = hypothesisV2Conditions.map((condition) => condition?.condition_id);
    const hypothesisV2CommonValid = exactKeys(hypothesis, hypothesisV2Fields)
      && hypothesis.schema_version === "strategy-hypothesis-preregistration-summary-v2"
      && hypothesis.source_schema_version === "strategy-hypothesis-preregistration-v2"
      && safeScope(hypothesis)
      && hypothesis.automatic_paper_activation_allowed === false
      && hypothesis.walk_forward_optimization_claim_allowed === false
      && stringList(hypothesis.strategy_ids)
      && new Set(hypothesis.strategy_ids).size === hypothesis.strategy_ids.length
      && hypothesisV2Conditions.length >= 1
      && hypothesisV2Conditions.length <= 8
      && hypothesisV2Conditions.every(validMechanismCondition)
      && new Set(hypothesisV2ConditionIds).size === hypothesisV2ConditionIds.length
      && stringList(hypothesis.blockers)
      && new Set(hypothesis.blockers).size === hypothesis.blockers.length;
    const hypothesisV3Fields = [...hypothesisV2Fields, "search_family_bound"];
    const hypothesisV3CommonValid = exactKeys(hypothesis, hypothesisV3Fields)
      && hypothesis.schema_version === "strategy-hypothesis-preregistration-summary-v3"
      && hypothesis.source_schema_version === "strategy-hypothesis-preregistration-v3"
      && safeScope(hypothesis)
      && hypothesis.automatic_paper_activation_allowed === false
      && hypothesis.walk_forward_optimization_claim_allowed === false
      && stringList(hypothesis.strategy_ids)
      && new Set(hypothesis.strategy_ids).size === hypothesis.strategy_ids.length
      && hypothesisV2Conditions.length >= 1
      && hypothesisV2Conditions.length <= 8
      && hypothesisV2Conditions.every(validMechanismCondition)
      && new Set(hypothesisV2ConditionIds).size === hypothesisV2ConditionIds.length
      && stringList(hypothesis.blockers)
      && new Set(hypothesis.blockers).size === hypothesis.blockers.length;
    const legacyHypothesisValid = Number.isInteger(payload.report_schema_version)
      && payload.report_schema_version >= 3
      && payload.report_schema_version < 7
      && hypothesisV1CommonValid
      && hypothesisStatus === "LEGACY_NOT_BOUND"
      && hypothesis.contract_checked === false
      && hypothesis.hypothesis_id === null
      && hypothesis.hypothesis_hash === null
      && typeof hypothesis.research_generation === "string"
      && hypothesis.strategy_ids.length === 0
      && hypothesis.selected_strategy_match === null
      && hypothesis.mechanism_family === null
      && hypothesis.hypothesis_statement === null
      && hypothesis.novelty_statement === null
      && hypothesis.mechanism_specific_failure_conditions.length === 0
      && hypothesis.parameter_topology_basis === null
      && hypothesis.numeric_parameter_distance_claimed === null
      && hypothesis.cost_stress_required === null
      && hypothesis.stressed_return_must_remain_positive === null
      && hypothesis.chronological_evaluation_mode === null
      && hypothesis.parameters_refit_per_fold === null
      && hypothesis.fresh_single_use_holdout_required === null
      && hypothesis.minimum_natural_forward_outcomes === null
      && hypothesis.minimum_executed_rebalances === null
      && hypothesis.statistical_contract_recheck_required_at_maturity === null
      && hypothesis.historical_backtest_can_substitute_natural_forward === null
      && hypothesis.reuses_falsified_strategy_id === null
      && hypothesis.retunes_falsified_mechanism === null
      && hypothesis.material_mechanism_change_requires_new_strategy_id === null
      && hypothesis.blockers.includes("historical_report_predates_hypothesis_preregistration");
    const boundHypothesisV1Valid = HYPOTHESIS_V1_REPORT_SCHEMA_VERSIONS.includes(
      payload.report_schema_version,
    )
      && hypothesisV1CommonValid
      && hypothesis.contract_checked === true
      && ["BOUND", "BLOCK"].includes(hypothesisStatus)
      && hypothesisStatus === (matched ? "BOUND" : "BLOCK")
      && typeof hypothesis.hypothesis_id === "string"
      && hypothesis.hypothesis_id.length >= 3
      && hash256(hypothesis.hypothesis_hash)
      && hypothesis.research_generation === payload.research_generation
      && hypothesis.strategy_ids.length > 0
      && hypothesis.selected_strategy_match === matched
      && (!matched || hypothesis.strategy_ids.includes(payload.selected_strategy_id))
      && typeof hypothesis.mechanism_family === "string"
      && hypothesis.mechanism_family.length >= 3
      && typeof hypothesis.hypothesis_statement === "string"
      && hypothesis.hypothesis_statement.length >= 24
      && typeof hypothesis.novelty_statement === "string"
      && hypothesis.novelty_statement.length >= 24
      && hypothesis.mechanism_specific_failure_conditions.length > 0
      && hypothesis.parameter_topology_basis === "FROZEN_VARIANT_SEQUENCE_ADJACENCY"
      && hypothesis.numeric_parameter_distance_claimed === false
      && hypothesis.cost_stress_required === true
      && hypothesis.stressed_return_must_remain_positive === true
      && hypothesis.chronological_evaluation_mode === "FIXED_PARAMETER_CHRONOLOGICAL_SLICES"
      && hypothesis.parameters_refit_per_fold === false
      && hypothesis.fresh_single_use_holdout_required === true
      && hypothesis.minimum_natural_forward_outcomes === 60
      && hypothesis.minimum_executed_rebalances === 8
      && hypothesis.statistical_contract_recheck_required_at_maturity === true
      && hypothesis.historical_backtest_can_substitute_natural_forward === false
      && hypothesis.reuses_falsified_strategy_id === false
      && hypothesis.retunes_falsified_mechanism === false
      && hypothesis.material_mechanism_change_requires_new_strategy_id === true
      && (matched
        ? hypothesis.blockers.length === 0
        : hypothesis.blockers.includes("selected_strategy_not_bound_to_hypothesis"));
    const boundHypothesisV2Valid = payload.report_schema_version === 13
      && hypothesisV2CommonValid
      && hypothesis.contract_checked === true
      && ["BOUND", "BLOCK"].includes(hypothesisStatus)
      && hypothesisStatus === (matched ? "BOUND" : "BLOCK")
      && typeof hypothesis.hypothesis_id === "string"
      && hypothesis.hypothesis_id.length >= 3
      && hash256(hypothesis.hypothesis_hash)
      && hypothesis.research_generation === payload.research_generation
      && hypothesis.strategy_ids.length > 0
      && hypothesis.selected_strategy_match === matched
      && (!matched || hypothesis.strategy_ids.includes(payload.selected_strategy_id))
      && typeof hypothesis.mechanism_family === "string"
      && hypothesis.mechanism_family.length >= 3
      && hypothesis.parameter_topology_basis === "FROZEN_VARIANT_SEQUENCE_ADJACENCY"
      && hypothesis.numeric_parameter_distance_claimed === false
      && hypothesis.cost_stress_required === true
      && hypothesis.stressed_return_must_remain_positive === true
      && hypothesis.chronological_evaluation_mode === "FIXED_PARAMETER_CHRONOLOGICAL_SLICES"
      && hypothesis.parameters_refit_per_fold === false
      && hypothesis.fresh_single_use_holdout_required === true
      && hypothesis.minimum_natural_forward_outcomes === 60
      && hypothesis.minimum_executed_rebalances === 8
      && hypothesis.statistical_contract_recheck_required_at_maturity === true
      && hypothesis.historical_backtest_can_substitute_natural_forward === false
      && hypothesis.reuses_falsified_strategy_id === false
      && hypothesis.retunes_falsified_mechanism === false
      && hypothesis.material_mechanism_change_requires_new_strategy_id === true
      && (matched
        ? hypothesis.blockers.length === 0
        : hypothesis.blockers.length === 1
          && hypothesis.blockers[0] === "selected_strategy_not_bound_to_hypothesis");
    const boundHypothesisV3Valid = payload.report_schema_version === 14
      && hypothesisV3CommonValid
      && hypothesis.contract_checked === true
      && ["BOUND", "BLOCK"].includes(hypothesisStatus)
      && hypothesisStatus === (matched ? "BOUND" : "BLOCK")
      && typeof hypothesis.hypothesis_id === "string"
      && hypothesis.hypothesis_id.length >= 3
      && hash256(hypothesis.hypothesis_hash)
      && hypothesis.research_generation === payload.research_generation
      && hypothesis.strategy_ids.length > 0
      && hypothesis.selected_strategy_match === matched
      && hypothesis.search_family_bound === matched
      && (!matched || hypothesis.strategy_ids.includes(payload.selected_strategy_id))
      && typeof hypothesis.mechanism_family === "string"
      && hypothesis.mechanism_family.length >= 3
      && hypothesis.parameter_topology_basis === "FROZEN_VARIANT_SEQUENCE_ADJACENCY"
      && hypothesis.numeric_parameter_distance_claimed === false
      && hypothesis.cost_stress_required === true
      && hypothesis.stressed_return_must_remain_positive === true
      && hypothesis.chronological_evaluation_mode === "FIXED_PARAMETER_CHRONOLOGICAL_SLICES"
      && hypothesis.parameters_refit_per_fold === false
      && hypothesis.fresh_single_use_holdout_required === true
      && hypothesis.minimum_natural_forward_outcomes === 60
      && hypothesis.minimum_executed_rebalances === 8
      && hypothesis.statistical_contract_recheck_required_at_maturity === true
      && hypothesis.historical_backtest_can_substitute_natural_forward === false
      && hypothesis.reuses_falsified_strategy_id === false
      && hypothesis.retunes_falsified_mechanism === false
      && hypothesis.material_mechanism_change_requires_new_strategy_id === true
      && (matched
        ? hypothesis.blockers.length === 0
        : hypothesis.blockers.length === 1
          && hypothesis.blockers[0] === "selected_strategy_not_bound_to_hypothesis");
    const hypothesisValid = legacyHypothesisValid
      || boundHypothesisV1Valid
      || boundHypothesisV2Valid
      || boundHypothesisV3Valid;
    const scopeFields = [
      "strategy_count",
      "parameter_variant_count",
      "selection_symbol_count",
      "selection_cell_count",
      "frozen_test_candidate_count",
      "test_cell_count",
      "forward_candidate_count",
    ];
    const scopeValid = isObject(scope)
      && scopeFields.every((field) => nonnegativeIntegerOrNull(scope[field]));
    const admissionStatus = status(admission?.status);
    const selectedAdmissionStatus = status(admission?.selected_strategy_status);
    const searchLineageFields = [
      "schema_version",
      "descriptive_only",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "research_only",
      "paper_authorized",
      "live_order_allowed",
      "status",
      "family_bound",
      "trial_count_scope",
      "prior_trial_count",
      "current_trial_count",
      "cumulative_trial_count",
      "selection_binding_scope",
      "offline_verification_scope",
      "admission_status",
      "blockers",
    ];
    const searchLineageCommonValid = exactKeys(searchLineage, searchLineageFields)
      && searchLineage.schema_version === "strategy-research-search-lineage-public-v1"
      && searchLineage.status === searchLineageStatus
      && safeScope(searchLineage)
      && searchLineage.automatic_paper_activation_allowed === false
      && stringList(searchLineage.blockers)
      && new Set(searchLineage.blockers).size === searchLineage.blockers.length
      && searchLineage.offline_verification_scope
        === "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY";
    const boundSearchLineageValid = matched
      && searchLineageCommonValid
      && payload.search_lineage_status === "BOUND"
      && searchLineageStatus === "BOUND"
      && searchLineage.family_bound === true
      && searchLineage.trial_count_scope === "GLOBAL_REGISTERED_STRATEGY_RESEARCH"
      && Number.isSafeInteger(searchLineage.prior_trial_count)
      && searchLineage.prior_trial_count >= 0
      && Number.isSafeInteger(searchLineage.current_trial_count)
      && searchLineage.current_trial_count > 0
      && Number.isSafeInteger(searchLineage.cumulative_trial_count)
      && searchLineage.cumulative_trial_count
        === searchLineage.prior_trial_count + searchLineage.current_trial_count
      && searchLineage.selection_binding_scope
        === "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT"
      && searchLineage.admission_status === admissionStatus
      && ["PASS", "BLOCK"].includes(searchLineage.admission_status)
      && searchLineage.blockers.length === 0;
    const notInReportSearchLineageValid = noMatch
      && searchLineageCommonValid
      && payload.search_lineage_status === "NOT_IN_REPORT"
      && searchLineageStatus === "NOT_IN_REPORT"
      && searchLineage.family_bound === false
      && searchLineage.trial_count_scope === null
      && searchLineage.prior_trial_count === null
      && searchLineage.current_trial_count === null
      && searchLineage.cumulative_trial_count === null
      && searchLineage.selection_binding_scope === null
      && searchLineage.admission_status === "NOT_IN_REPORT"
      && searchLineage.blockers.length === 1
      && searchLineage.blockers[0] === "strategy_not_in_frozen_research_report";
    const searchLineageValid = boundSearchLineageValid || notInReportSearchLineageValid;
    const admissionConditionIds = [
      "parameter_plateau_absent",
      "cost_break_even_lost",
      "fixed_parameter_time_slice_instability",
    ];
    const admissionCandidateCount = admission?.selected_strategy_candidate_count;
    const selectedAdmittedCount = admission?.selected_strategy_admitted_count;
    const admittedCandidateCount = admission?.admitted_candidate_count;
    const admissionV1Fields = [
      "schema_version",
      "status",
      "admission_scope",
      "hypothesis_id",
      "selected_strategy_status",
      "selected_strategy_candidate_count",
      "selected_strategy_admitted_count",
      "admitted_candidate_count",
      "checks",
      "blockers",
      "descriptive_only",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "research_only",
      "paper_authorized",
      "live_order_allowed",
    ];
    const admissionV1CheckFields = ["condition_id", "status", "triggered", "blockers"];
    const admissionChecks = Array.isArray(admission?.checks) ? admission.checks : [];
    const admissionCheckById = new Map(
      admissionChecks.map((check) => [check?.condition_id, check]),
    );
    const admissionChecksValid = isObject(admission)
      && Array.isArray(admission.checks)
      && (
        noMatch
          ? admissionChecks.length === 0
          : admissionChecks.length === admissionConditionIds.length
            && admissionCheckById.size === admissionConditionIds.length
            && admissionConditionIds.every((conditionId) => {
              const check = admissionCheckById.get(conditionId);
              const checkStatus = check?.status;
              return exactKeys(check, admissionV1CheckFields)
                && check.condition_id === conditionId
                && ["PASS", "BLOCK", "NOT_APPLICABLE"].includes(checkStatus)
                && typeof check.triggered === "boolean"
                && check.triggered === (checkStatus === "BLOCK")
                && stringList(check.blockers)
                && new Set(check.blockers).size === check.blockers.length
                && (checkStatus === "BLOCK" ? check.blockers.length > 0 : check.blockers.length === 0)
                && (conditionId !== "parameter_plateau_absent" || checkStatus !== "NOT_APPLICABLE");
            })
      );
    const candidateCheckApplicabilityValid = noMatch
      ? true
      : admissionCheckById.size === admissionConditionIds.length
        && (admissionCandidateCount === 0
          ? admissionCheckById.get("cost_break_even_lost")?.status === "NOT_APPLICABLE"
            && admissionCheckById.get("fixed_parameter_time_slice_instability")?.status === "NOT_APPLICABLE"
          : admissionCheckById.get("cost_break_even_lost")?.status !== "NOT_APPLICABLE"
            && admissionCheckById.get("fixed_parameter_time_slice_instability")?.status !== "NOT_APPLICABLE");
    const admissionCountsValid = Number.isSafeInteger(admissionCandidateCount)
      && admissionCandidateCount >= 0
      && Number.isSafeInteger(selectedAdmittedCount)
      && selectedAdmittedCount >= 0
      && selectedAdmittedCount <= admissionCandidateCount
      && Number.isSafeInteger(admittedCandidateCount)
      && admittedCandidateCount >= 0
      && selectedAdmittedCount <= admittedCandidateCount
      && (noMatch
        ? admissionCandidateCount === 0
          && selectedAdmittedCount === 0
          && admittedCandidateCount === 0
        : admissionCandidateCount <= 1
          && scope?.frozen_test_candidate_count === admittedCandidateCount
          && (scope?.strategy_count === null || admittedCandidateCount <= scope.strategy_count)
          && (scope?.parameter_variant_count === null || admittedCandidateCount <= scope.parameter_variant_count));
    const admissionStatusValid = ["PASS", "BLOCK", "NOT_IN_REPORT"].includes(admissionStatus)
      && admission?.status === admissionStatus
      && admission?.selected_strategy_status === selectedAdmissionStatus
      && (
        noMatch
          ? admissionStatus === "NOT_IN_REPORT"
            && selectedAdmissionStatus === "NOT_IN_REPORT"
            && admissionCandidateCount === 0
            && selectedAdmittedCount === 0
            && admittedCandidateCount === 0
            && admission.blockers.length === 1
            && admission.blockers[0] === "strategy_not_in_frozen_research_report"
          : ["PASS", "BLOCK"].includes(admissionStatus)
            && ["PASS", "BLOCK"].includes(selectedAdmissionStatus)
      )
      && (selectedAdmissionStatus !== "PASS"
        || admissionChecks.every((check) => check.status !== "BLOCK"))
      && (
        noMatch
          ? admissionChecks.length === 0
          : admissionStatus === "PASS"
          ? admittedCandidateCount > 0
            && (
              selectedAdmissionStatus === "PASS"
              && selectedAdmittedCount === admissionCandidateCount
              && admissionChecks.every((check) => check.status !== "BLOCK")
            )
            && admission?.blockers?.length === 0
          : admittedCandidateCount === 0
            && selectedAdmittedCount === 0
            && admission?.blockers?.length > 0
      );
    const admissionV1Valid = exactKeys(admission, admissionV1Fields)
      && admission.schema_version === "strategy-preregistered-failure-admission-v1"
      && admission.admission_scope === "HYPOTHESIS_BATCH"
      && (noMatch
        ? admission.hypothesis_id === null
        : typeof admission.hypothesis_id === "string"
          && admission.hypothesis_id.length >= 3
          && admission.hypothesis_id === hypothesis?.hypothesis_id)
      && admissionCountsValid
      && admissionChecksValid
      && candidateCheckApplicabilityValid
      && stringList(admission.blockers)
      && new Set(admission.blockers).size === admission.blockers.length
      && admissionStatusValid
      && safeScope(admission)
      && admission.automatic_paper_activation_allowed === false;
    const admissionV2Fields = [
      "descriptive_only",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "research_only",
      "paper_authorized",
      "live_order_allowed",
      "schema_version",
      "status",
      "admission_scope",
      "hypothesis_id",
      "selected_strategy_status",
      "selected_strategy_candidate_count",
      "selected_strategy_admitted_count",
      "admitted_candidate_count",
      "mechanism_condition_ids",
      "checks",
      "future_standard_checks",
      "blockers",
    ];
    const admissionV3Fields = [...admissionV2Fields, "search_lineage_status"];
    const standardAdmissionCheckFields = [
      "condition_id",
      "condition_kind",
      "evidence_stage",
      "required_action",
      "status",
      "triggered",
      "blockers",
    ];
    const mechanismAdmissionCheckFields = [
      ...standardAdmissionCheckFields.slice(0, 4),
      "status",
      "triggered",
      "blockers",
      "metric",
      "operator",
      "threshold",
      "metric_value",
    ];
    const admissionMechanismIds = Array.isArray(admission?.mechanism_condition_ids)
      ? admission.mechanism_condition_ids
      : [];
    const futureAdmissionChecks = Array.isArray(admission?.future_standard_checks)
      ? admission.future_standard_checks
      : [];
    const evaluateMechanismPredicate = (metricValue, operator, threshold) => ({
      LT: metricValue < threshold,
      LTE: metricValue <= threshold,
      GT: metricValue > threshold,
      GTE: metricValue >= threshold,
    })[operator];
    const validStandardAdmissionCheck = (check, conditionId) => {
      if (!exactKeys(check, standardAdmissionCheckFields)) return false;
      const checkStatus = check.status;
      return check.condition_id === conditionId
        && check.condition_kind === "STANDARD"
        && check.evidence_stage === "DEVELOPMENT_SELECTION"
        && check.required_action === "BLOCK_RESEARCH"
        && ["PASS", "BLOCK", "NOT_APPLICABLE"].includes(checkStatus)
        && typeof check.triggered === "boolean"
        && check.triggered === (checkStatus === "BLOCK")
        && (checkStatus === "BLOCK"
          ? Array.isArray(check.blockers)
            && check.blockers.length === 1
            && check.blockers[0] === "standard_condition_blocked"
          : Array.isArray(check.blockers) && check.blockers.length === 0)
        && (conditionId !== "parameter_plateau_absent" || checkStatus !== "NOT_APPLICABLE")
        && (admissionCandidateCount === 0
          ? conditionId === "parameter_plateau_absent" || checkStatus === "NOT_APPLICABLE"
          : checkStatus !== "NOT_APPLICABLE");
    };
    const validMechanismAdmissionCheck = (check, hypothesisCondition) => {
      if (
        !exactKeys(check, mechanismAdmissionCheckFields)
        || !validMechanismCondition(hypothesisCondition)
        || !mechanismConditionFields.every((field) => check[field] === hypothesisCondition[field])
        || check.condition_kind !== "MECHANISM_SPECIFIC"
      ) return false;
      if (admissionCandidateCount === 0) {
        return check.status === "NOT_APPLICABLE"
          && check.triggered === false
          && check.metric_value === null
          && Array.isArray(check.blockers)
          && check.blockers.length === 0;
      }
      if (admissionCandidateCount !== 1) {
        return check.status === "BLOCK"
          && check.triggered === null
          && check.metric_value === null
          && Array.isArray(check.blockers)
          && check.blockers.length === 1
          && check.blockers[0] === "mechanism_condition_unresolved";
      }
      if (typeof check.metric_value !== "number" || !Number.isFinite(check.metric_value)) return false;
      const triggered = evaluateMechanismPredicate(
        check.metric_value,
        check.operator,
        check.threshold,
      );
      return typeof triggered === "boolean"
        && check.triggered === triggered
        && check.status === (triggered ? "BLOCK" : "PASS")
        && (triggered
          ? Array.isArray(check.blockers)
            && check.blockers.length === 1
            && check.blockers[0] === "mechanism_condition_triggered"
          : Array.isArray(check.blockers) && check.blockers.length === 0);
    };
    const expectedFutureAdmissionChecks = [
      [
        "fresh_single_use_holdout_failure",
        "PREREGISTERED_BLIND_SINGLE_USE",
        "RETIRE_OR_NEW_REGISTRATION",
      ],
      [
        "natural_forward_statistical_failure",
        "NATURAL_FORWARD_MATURITY",
        "RETIRE_HYPOTHESIS",
      ],
    ];
    const futureAdmissionChecksValid = noMatch
      ? futureAdmissionChecks.length === 0
      : futureAdmissionChecks.length === 2
        && expectedFutureAdmissionChecks.every(([conditionId, evidenceStage, requiredAction], index) => {
        const check = futureAdmissionChecks[index];
        return exactKeys(check, standardAdmissionCheckFields)
          && check.condition_id === conditionId
          && check.condition_kind === "STANDARD"
          && check.evidence_stage === evidenceStage
          && check.required_action === requiredAction
          && check.status === "NOT_DUE"
          && check.triggered === false
          && Array.isArray(check.blockers)
          && check.blockers.length === 0;
        });
    const v2StandardChecks = admissionChecks.slice(0, admissionConditionIds.length);
    const v2MechanismChecks = admissionChecks.slice(admissionConditionIds.length);
    const admissionV2ChecksValid = noMatch
      ? admissionChecks.length === 0
      : admissionChecks.length === admissionConditionIds.length + hypothesisV2Conditions.length
        && admissionConditionIds.every(
          (conditionId, index) => validStandardAdmissionCheck(v2StandardChecks[index], conditionId),
        )
        && hypothesisV2Conditions.every(
          (condition, index) => validMechanismAdmissionCheck(v2MechanismChecks[index], condition),
        );
    const v3MechanismChecks = admissionChecks;
    const admissionV3ChecksValid = noMatch
      ? v3MechanismChecks.length === 0
      : v3MechanismChecks.length === hypothesisV2Conditions.length
        && hypothesisV2Conditions.every(
          (condition, index) => validMechanismAdmissionCheck(v3MechanismChecks[index], condition),
        );
    const admissionV2CountsValid = Number.isSafeInteger(admissionCandidateCount)
      && admissionCandidateCount >= 0
      && Number.isSafeInteger(selectedAdmittedCount)
      && selectedAdmittedCount >= 0
      && selectedAdmittedCount <= admissionCandidateCount
      && Number.isSafeInteger(admittedCandidateCount)
      && admittedCandidateCount >= 0
      && selectedAdmittedCount <= admittedCandidateCount
      && (noMatch
        ? admissionCandidateCount === 0
          && selectedAdmittedCount === 0
          && admittedCandidateCount === 0
        : scope?.frozen_test_candidate_count === admittedCandidateCount
          && (scope?.strategy_count === null || admittedCandidateCount <= scope.strategy_count)
          && admittedCandidateCount <= hypothesis.strategy_ids.length
          && (scope?.parameter_variant_count === null || admittedCandidateCount <= scope.parameter_variant_count)
          && (scope?.parameter_variant_count === null || admissionCandidateCount <= scope.parameter_variant_count));
    const admissionV2RootStatusValid = ["PASS", "BLOCK", "NOT_IN_REPORT"].includes(admissionStatus)
      && admission.status === admissionStatus
      && admission.selected_strategy_status === selectedAdmissionStatus
      && (noMatch
        ? admissionStatus === "NOT_IN_REPORT"
          && selectedAdmissionStatus === "NOT_IN_REPORT"
          && admissionCandidateCount === 0
          && selectedAdmittedCount === 0
          && admittedCandidateCount === 0
          && admission.blockers.length === 1
          && admission.blockers[0] === "strategy_not_in_frozen_research_report"
        : ["PASS", "BLOCK"].includes(admissionStatus)
          && ["PASS", "BLOCK"].includes(selectedAdmissionStatus))
      && (selectedAdmissionStatus !== "PASS"
        || admissionChecks.every((check) => check.status !== "BLOCK"))
      && (noMatch || (admissionStatus === "PASS"
        ? admittedCandidateCount > 0
          && (
            selectedAdmissionStatus === "PASS"
            && selectedAdmittedCount === admissionCandidateCount
            && admissionChecks.every((check) => check.status !== "BLOCK")
          )
          && admission.blockers.length === 0
        : admittedCandidateCount === 0
          && selectedAdmittedCount === 0
          && admission.blockers.length === 1
          && admission.blockers[0] === "preregistered_failure_admission_blocked"));
    const structuredAdmissionCommonValid = isObject(admission)
      && admission.admission_scope === "HYPOTHESIS_BATCH"
      && (noMatch
        ? admission.hypothesis_id === null
        : typeof admission.hypothesis_id === "string"
          && admission.hypothesis_id.length >= 3
          && admission.hypothesis_id === hypothesis?.hypothesis_id)
      && admissionV2CountsValid
      && stringList(admissionMechanismIds)
      && (noMatch
        ? admissionMechanismIds.length === 0
        : admissionMechanismIds.length >= 1 && admissionMechanismIds.length <= 8)
      && new Set(admissionMechanismIds).size === admissionMechanismIds.length
      && (noMatch || (
        admissionMechanismIds.length === hypothesisV2ConditionIds.length
        && admissionMechanismIds.every((id, index) => id === hypothesisV2ConditionIds[index])
      ))
      && futureAdmissionChecksValid
      && stringList(admission.blockers)
      && new Set(admission.blockers).size === admission.blockers.length
      && admissionV2RootStatusValid
      && safeScope(admission)
      && admission.automatic_paper_activation_allowed === false;
    const admissionV2Valid = exactKeys(admission, admissionV2Fields)
      && admission.schema_version === "strategy-preregistered-failure-admission-v2"
      && admissionV2ChecksValid
      && structuredAdmissionCommonValid;
    const admissionV3Valid = exactKeys(admission, admissionV3Fields)
      && admission.schema_version === "strategy-preregistered-failure-admission-v3"
      && admission.search_lineage_status === searchLineageStatus
      && searchLineageValid
      && admissionV3ChecksValid
      && structuredAdmissionCommonValid;
    const stageFields = [
      "stage",
      "status",
      "candidate_count",
      "result_count",
      "cell_count",
      "replay_verified_cell_count",
      "replay_pass_cell_count",
      "aggregate_pass_candidate_count",
      "minimum_configured_return_pct",
      "minimum_excess_return_pct",
      "minimum_severe_cost_return_pct",
      "worst_drawdown_pct",
      "total_trades",
      "fixed_slice_pass_cell_count",
      "prefix_invariance_pass_cell_count",
      "lookahead_pass_cell_count",
      "blockers",
    ];
    const stageCountFields = [
      "candidate_count",
      "result_count",
      "cell_count",
      "replay_verified_cell_count",
      "replay_pass_cell_count",
      "aggregate_pass_candidate_count",
      "fixed_slice_pass_cell_count",
      "prefix_invariance_pass_cell_count",
      "lookahead_pass_cell_count",
    ];
    const stageMetricFields = [
      "minimum_configured_return_pct",
      "minimum_excess_return_pct",
      "minimum_severe_cost_return_pct",
      "worst_drawdown_pct",
    ];
    const replayStageBlockers = new Set([
      "post_selection_candidate_contract_invalid",
      "post_selection_result_contract_invalid",
      "post_selection_symbol_scope_invalid",
      "post_selection_cell_coverage_not_preserved",
      "post_selection_replay_integrity_not_preserved",
      "post_selection_aggregate_semantics_not_preserved",
      "post_selection_replay_outcome_not_preserved",
    ]);
    const replayStageIntegrityBlockers = new Set([
      "post_selection_candidate_contract_invalid",
      "post_selection_result_contract_invalid",
      "post_selection_symbol_scope_invalid",
      "post_selection_cell_coverage_not_preserved",
      "post_selection_replay_integrity_not_preserved",
      "post_selection_aggregate_semantics_not_preserved",
    ]);
    const exactStringList = (value, allowed = null) => stringList(value)
      && new Set(value).size === value.length
      && (!allowed || value.every((item) => allowed.has(item)));
    const validateReplayStage = (value, expectedStage) => {
      if (!exactKeys(value, stageFields)) return false;
      const replayStatus = status(value.status);
      const countsValid = stageCountFields.every(
        (field) => Number.isSafeInteger(value[field]) && value[field] >= 0,
      );
      const blockersValid = exactStringList(value.blockers, replayStageBlockers);
      const metricsNull = stageMetricFields.every((field) => value[field] === null)
        && value.total_trades === null;
      const metricsPresent = stageMetricFields.every(
        (field) => typeof value[field] === "number" && Number.isFinite(value[field]),
      ) && Number.isSafeInteger(value.total_trades) && value.total_trades >= 0;
      if (!countsValid || !blockersValid || (!metricsNull && !metricsPresent)) return false;
      if (
        value.stage !== expectedStage
        || !["PASS", "BLOCK", "NOT_RUN"].includes(replayStatus)
        || value.status !== replayStatus
        || value.result_count > value.candidate_count
        || value.aggregate_pass_candidate_count > value.candidate_count
        || value.replay_verified_cell_count > value.cell_count
        || value.replay_pass_cell_count > value.replay_verified_cell_count
        || value.fixed_slice_pass_cell_count > value.cell_count
        || value.prefix_invariance_pass_cell_count > value.cell_count
        || value.lookahead_pass_cell_count > value.cell_count
      ) return false;
      const testStage = expectedStage === "FROZEN_TEST_ONCE";
      const auditCounts = [
        value.fixed_slice_pass_cell_count,
        value.prefix_invariance_pass_cell_count,
        value.lookahead_pass_cell_count,
      ];
      const hasIntegrityBlocker = value.blockers.some(
        (blocker) => replayStageIntegrityBlockers.has(blocker),
      );
      const pureOutcomeBlock = value.blockers.length === 1
        && value.blockers[0] === "post_selection_replay_outcome_not_preserved";
      if (testStage && [
        ...auditCounts,
      ].some((count) => count !== 0)) return false;
      if (
        (metricsPresent && value.replay_verified_cell_count !== value.cell_count)
        || (metricsNull && auditCounts.some((count) => count !== 0))
        || (value.replay_verified_cell_count < value.cell_count && !metricsNull)
        || (hasIntegrityBlocker && (!metricsNull || auditCounts.some((count) => count !== 0)))
        || (replayStatus === "BLOCK" && metricsPresent && !pureOutcomeBlock)
      ) return false;
      const emptyCounts = stageCountFields.every((field) => value[field] === 0);
      if (replayStatus === "NOT_RUN") {
        return emptyCounts && metricsNull && value.blockers.length === 0;
      }
      if (value.candidate_count < 1) return false;
      const replayPreservedShape = value.result_count === value.candidate_count
        && value.cell_count > 0
        && value.replay_verified_cell_count === value.cell_count
        && value.replay_pass_cell_count === value.cell_count
        && value.aggregate_pass_candidate_count === value.candidate_count
        && metricsPresent
        && (testStage || (
          value.fixed_slice_pass_cell_count === value.cell_count
          && value.prefix_invariance_pass_cell_count === value.cell_count
          && value.lookahead_pass_cell_count === value.cell_count
        ));
      return replayStatus === "PASS"
        ? replayPreservedShape && value.blockers.length === 0
        : value.blockers.length > 0 && !replayPreservedShape;
    };
    const postSelectionStatus = status(postSelection?.status);
    const frozenTestStatus = status(postSelection?.frozen_test?.status);
    const holdoutStatus = status(postSelection?.holdout_confirmation?.status);
    const expectedPostSelectionStatus = [frozenTestStatus, holdoutStatus].includes("BLOCK")
      ? "BLOCK"
      : frozenTestStatus === "NOT_RUN" && holdoutStatus === "NOT_RUN"
        ? "NOT_RUN"
        : frozenTestStatus === "PASS" && holdoutStatus === "PASS"
          ? "PASS"
          : "BLOCK";
    const postSelectionProgressionValid = frozenTestStatus === "NOT_RUN"
      ? holdoutStatus === "NOT_RUN"
      : frozenTestStatus === "PASS"
        ? holdoutStatus !== "NOT_RUN"
        : frozenTestStatus === "BLOCK";
    const postSelectionFields = [
      "schema_version",
      "status",
      "report_schema_version",
      "frozen_test",
      "holdout_confirmation",
      "historical_backtest_only",
      "natural_forward_performance_proven",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "paper_authorized",
      "live_order_allowed",
    ];
    const postSelectionValid = exactKeys(postSelection, postSelectionFields)
      && postSelection.schema_version === "strategy-post-selection-replay-summary-v1"
      && STRATEGY_LAB_POST_SELECTION_REPORT_SCHEMA_VERSIONS.includes(
        postSelection.report_schema_version,
      )
      && postSelection.report_schema_version === payload.report_schema_version
      && ["PASS", "BLOCK", "NOT_RUN"].includes(postSelectionStatus)
      && postSelection.status === postSelectionStatus
      && postSelectionStatus === expectedPostSelectionStatus
      && postSelectionProgressionValid
      && validateReplayStage(postSelection.frozen_test, "FROZEN_TEST_ONCE")
      && validateReplayStage(postSelection.holdout_confirmation, "HOLDOUT_CONFIRMATION")
      && postSelection.holdout_confirmation.candidate_count
        === postSelection.frozen_test.aggregate_pass_candidate_count
      && postSelection.historical_backtest_only === true
      && postSelection.natural_forward_performance_proven === false
      && postSelection.profitability_proven === false
      && postSelection.performance_claim_allowed === false
      && postSelection.parameter_selection_allowed === false
      && postSelection.automatic_paper_activation_allowed === false
      && postSelection.paper_authorized === false
      && postSelection.live_order_allowed === false
      && postSelection.frozen_test.candidate_count <= (scope?.frozen_test_candidate_count ?? -1)
      && postSelection.frozen_test.cell_count <= (scope?.test_cell_count ?? -1)
      && postSelection.holdout_confirmation.aggregate_pass_candidate_count
        <= (scope?.forward_candidate_count ?? -1)
      && (!noMatch || (
        postSelectionStatus === "NOT_RUN"
        && frozenTestStatus === "NOT_RUN"
        && holdoutStatus === "NOT_RUN"
      ));
    const legacySearchLineageAbsent = !hasOwn(payload, "search_lineage_status")
      && !hasOwn(payload, "search_lineage")
      && !hasOwn(contract, "search_lineage_schema_version")
      && !hasOwn(contract, "search_lineage_status");
    const v3ContractValid = contract.schema_version === "strategy-lab-frozen-evidence-v3"
      && STRATEGY_LAB_FROZEN_V3_REPORT_SCHEMA_VERSIONS.includes(payload.report_schema_version)
      && legacySearchLineageAbsent
      && !hasOwn(payload, "preregistered_failure_admission_status")
      && !hasOwn(contract, "preregistered_failure_admission_status")
      && !hasOwn(payload, "preregistered_failure_admission")
      && !hasOwn(payload, "post_selection_replay_status")
      && !hasOwn(contract, "post_selection_replay_status")
      && !hasOwn(payload, "post_selection_replay_summary")
      && !hasOwn(contract, "hypothesis_preregistration_schema_version")
      && !hasOwn(contract, "preregistered_failure_admission_schema_version")
      && !hasOwn(contract, "failure_conditions_schema_version");
    const v5Schema11ContractValid = contract.schema_version === "strategy-lab-frozen-evidence-v5"
      && payload.report_schema_version === 11
      && legacySearchLineageAbsent
      && payload.post_selection_replay_status === postSelectionStatus
      && contract.post_selection_replay_status === postSelectionStatus
      && postSelectionValid
      && !hasOwn(payload, "preregistered_failure_admission_status")
      && !hasOwn(contract, "preregistered_failure_admission_status")
      && !hasOwn(payload, "preregistered_failure_admission")
      && !hasOwn(contract, "hypothesis_preregistration_schema_version")
      && !hasOwn(contract, "preregistered_failure_admission_schema_version")
      && !hasOwn(contract, "failure_conditions_schema_version");
    const v5Schema12ContractValid = contract.schema_version === "strategy-lab-frozen-evidence-v5"
      && payload.report_schema_version === 12
      && legacySearchLineageAbsent
      && payload.post_selection_replay_status === postSelectionStatus
      && contract.post_selection_replay_status === postSelectionStatus
      && postSelectionValid
      && payload.preregistered_failure_admission_status === admissionStatus
      && contract.preregistered_failure_admission_status === admissionStatus
      && admissionV1Valid
      && !hasOwn(contract, "hypothesis_preregistration_schema_version")
      && !hasOwn(contract, "preregistered_failure_admission_schema_version")
      && !hasOwn(contract, "failure_conditions_schema_version")
      && (selectedAdmittedCount > 0
        ? frozenTestStatus !== "NOT_RUN"
        : frozenTestStatus === "NOT_RUN")
      && (admissionStatus !== "BLOCK" || (
        postSelectionStatus === "NOT_RUN"
        && frozenTestStatus === "NOT_RUN"
        && holdoutStatus === "NOT_RUN"
      ));
    const v5ContractValid = v5Schema11ContractValid || v5Schema12ContractValid;
    const v6ContractValid = contract.schema_version === "strategy-lab-frozen-evidence-v6"
      && payload.report_schema_version === 13
      && legacySearchLineageAbsent
      && contract.hypothesis_preregistration_schema_version
        === "strategy-hypothesis-preregistration-v2"
      && contract.preregistered_failure_admission_schema_version
        === "strategy-preregistered-failure-admission-v2"
      && contract.failure_conditions_schema_version
        === "strategy-research-failure-conditions-v3"
      && payload.post_selection_replay_status === postSelectionStatus
      && contract.post_selection_replay_status === postSelectionStatus
      && postSelectionValid
      && payload.preregistered_failure_admission_status === admissionStatus
      && contract.preregistered_failure_admission_status === admissionStatus
      && admissionV2Valid
      && (selectedAdmittedCount > 0
        ? frozenTestStatus !== "NOT_RUN"
        : frozenTestStatus === "NOT_RUN")
      && (admissionStatus !== "BLOCK" || (
        postSelectionStatus === "NOT_RUN"
        && frozenTestStatus === "NOT_RUN"
        && holdoutStatus === "NOT_RUN"
      ));
    const v7EvidenceContractFields = [
      "schema_version",
      "connection_status",
      "mode",
      "research_report_source",
      "interpretation",
      "strategy_match_status",
      "parameter_stability_status",
      "hypothesis_preregistration_status",
      "cost_sensitivity_status",
      "chronological_slice_status",
      "research_only",
      "descriptive_only",
      "development_heuristic_only",
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "implementation_currentness_checked",
      "implementation_currentness_status",
      "implementation_currentness_match",
      "implementation_currentness_basis",
      "full_implementation_manifest_checked",
      "full_implementation_manifest_status",
      "full_implementation_manifest_match",
      "full_implementation_manifest_basis",
      "currentness_facts_schema_version",
      "currentness_facts_status",
      "currentness_threshold_applied",
      "dataset_currentness_checked",
      "report_age_policy_checked",
      "paper_authorized",
      "live_order_allowed",
      "hypothesis_preregistration_schema_version",
      "preregistered_failure_admission_schema_version",
      "failure_conditions_schema_version",
      "search_lineage_schema_version",
      "search_lineage_status",
      "preregistered_failure_admission_status",
      "post_selection_replay_status",
    ];
    const v7ContractValid = exactKeys(contract, v7EvidenceContractFields)
      && contract.schema_version === "strategy-lab-frozen-evidence-v7"
      && payload.report_schema_version === 14
      && contract.hypothesis_preregistration_schema_version
        === "strategy-hypothesis-preregistration-v3"
      && contract.preregistered_failure_admission_schema_version
        === "strategy-preregistered-failure-admission-v3"
      && contract.failure_conditions_schema_version
        === "strategy-research-failure-conditions-v4"
      && contract.search_lineage_schema_version
        === "strategy-research-search-lineage-public-v1"
      && payload.search_lineage_status === searchLineageStatus
      && contract.search_lineage_status === searchLineageStatus
      && searchLineageValid
      && payload.post_selection_replay_status === postSelectionStatus
      && contract.post_selection_replay_status === postSelectionStatus
      && postSelectionValid
      && payload.preregistered_failure_admission_status === admissionStatus
      && contract.preregistered_failure_admission_status === admissionStatus
      && admissionV3Valid
      && (selectedAdmittedCount > 0
        ? frozenTestStatus !== "NOT_RUN"
        : frozenTestStatus === "NOT_RUN")
      && (admissionStatus !== "BLOCK" || (
        postSelectionStatus === "NOT_RUN"
        && frozenTestStatus === "NOT_RUN"
        && holdoutStatus === "NOT_RUN"
      ));
    const postSelectionContractValid = v5ContractValid || v6ContractValid || v7ContractValid;
    const admissionContractValid = v5Schema12ContractValid || v6ContractValid || v7ContractValid;
    const structuredMechanismContractValid = v6ContractValid || v7ContractValid;
    const activeMechanismChecks = v7ContractValid ? v3MechanismChecks : v2MechanismChecks;
    const plateauFields = [
      "frozen_variant_count",
      "eligible_variant_count",
      "near_best_eligible_variant_count",
      "adjacent_near_best_variant_count",
      "plateau_width",
    ];
    const plateauValid = isObject(plateau)
      && typeof plateau.status === "string"
      && plateauFields.every((field) => nonnegativeIntegerOrNull(plateau[field]))
      && finiteOrNull(plateau.best_adjusted_score)
      && [null, true, false].includes(plateau.peak_only)
      && stringList(plateau.blockers)
      && plateau.descriptive_only === true
      && plateau.parameter_selection_allowed === false;
    const costFields = [
      "evaluated_cell_count",
      "pass_cell_count",
    ];
    const costValid = isObject(cost)
      && typeof cost.status === "string"
      && costFields.every((field) => nonnegativeIntegerOrNull(cost[field]))
      && finiteOrNull(cost.worst_stressed_return_pct)
      && finiteOrNull(cost.worst_stressed_drawdown_pct)
      && [null, true, false].includes(cost.break_even_preserved)
      && stringList(cost.blockers)
      && cost.descriptive_only === true
      && cost.profitability_proven === false;
    const chronologicalFields = [
      "evaluated_cell_count",
      "pass_cell_count",
      "usable_fold_count",
      "positive_fold_count",
    ];
    const chronologicalValid = isObject(chronological)
      && typeof chronological.status === "string"
      && typeof chronological.evaluation_mode === "string"
      && chronologicalFields.every((field) => nonnegativeIntegerOrNull(chronological[field]))
      && finiteOrNull(chronological.worst_drawdown_pct)
      && [null, false].includes(chronological.parameters_refit_per_fold)
      && chronological.walk_forward_optimization_claim_allowed === false
      && stringList(chronological.blockers)
      && chronological.descriptive_only === true;
    const implementationStatus = status(implementation?.status);
    const implementationValid = isObject(implementation)
      && implementation.schema_version === "strategy-signal-implementation-currentness-v1"
      && implementation.basis === "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT"
      && ["MATCH", "MISMATCH", "BLOCK", "UNKNOWN", "NOT_IN_REPORT"].includes(implementationStatus)
      && typeof implementation.checked === "boolean"
      && [null, true, false].includes(implementation.matches_current)
      && [
        "frozen_variant_count",
        "matched_variant_count",
        "mismatched_variant_count",
      ].every((field) => Number.isSafeInteger(implementation[field]) && implementation[field] >= 0)
      && implementation.matched_variant_count + implementation.mismatched_variant_count
        <= implementation.frozen_variant_count
      && stringList(implementation.blockers)
      && implementation.full_implementation_manifest_checked === false
      && implementation.research_only === true
      && implementation.paper_authorized === false
      && implementation.live_order_allowed === false
      && (
        implementationStatus !== "MATCH"
        || (
          implementation.checked === true
          && implementation.matches_current === true
          && implementation.frozen_variant_count > 0
          && implementation.matched_variant_count === implementation.frozen_variant_count
          && implementation.mismatched_variant_count === 0
        )
      )
      && (
        implementationStatus !== "MISMATCH"
        || (
          implementation.checked === true
          && implementation.matches_current === false
          && implementation.mismatched_variant_count > 0
          && implementation.matched_variant_count + implementation.mismatched_variant_count
            === implementation.frozen_variant_count
        )
      )
      && (
        !["BLOCK", "UNKNOWN", "NOT_IN_REPORT"].includes(implementationStatus)
        || (implementation.checked === false && implementation.matches_current === null)
      );
    const fullImplementationStatus = status(fullImplementation?.status);
    const fullImplementationValid = isObject(fullImplementation)
      && fullImplementation.schema_version === "strategy-full-implementation-currentness-v1"
      && fullImplementation.basis === "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME"
      && ["MATCH", "MISMATCH", "BLOCK", "NOT_AVAILABLE"].includes(fullImplementationStatus)
      && typeof fullImplementation.checked === "boolean"
      && [null, true, false].includes(fullImplementation.matches_current)
      && ["expected_source_count", "verified_source_count"].every(
        (field) => Number.isSafeInteger(fullImplementation[field]) && fullImplementation[field] >= 0,
      )
      && fullImplementation.verified_source_count <= fullImplementation.expected_source_count
      && typeof fullImplementation.exact_files_checked === "boolean"
      && typeof fullImplementation.runtime_checked === "boolean"
      && stringList(fullImplementation.blockers)
      && fullImplementation.research_only === true
      && fullImplementation.paper_authorized === false
      && fullImplementation.live_order_allowed === false
      && (
        fullImplementationStatus !== "MATCH"
        || (
          fullImplementation.checked === true
          && fullImplementation.matches_current === true
          && fullImplementation.expected_source_count > 0
          && fullImplementation.verified_source_count === fullImplementation.expected_source_count
          && fullImplementation.exact_files_checked === true
          && fullImplementation.runtime_checked === true
          && fullImplementation.blockers.length === 0
        )
      )
      && (
        fullImplementationStatus !== "MISMATCH"
        || (
          fullImplementation.checked === true
          && fullImplementation.matches_current === false
          && fullImplementation.expected_source_count > 0
          && fullImplementation.verified_source_count === fullImplementation.expected_source_count
          && fullImplementation.exact_files_checked === true
          && fullImplementation.runtime_checked === true
          && fullImplementation.blockers.length > 0
        )
      )
      && (
        fullImplementationStatus !== "BLOCK"
        || (
          fullImplementation.checked === false
          && fullImplementation.matches_current === null
          && fullImplementation.exact_files_checked === false
          && fullImplementation.runtime_checked === false
          && fullImplementation.blockers.length > 0
        )
      )
      && (
        fullImplementationStatus !== "NOT_AVAILABLE"
        || (
          fullImplementation.checked === false
          && fullImplementation.matches_current === null
          && fullImplementation.expected_source_count === 0
          && fullImplementation.verified_source_count === 0
          && fullImplementation.exact_files_checked === false
          && fullImplementation.runtime_checked === false
          && fullImplementation.blockers.length > 0
          && (
            !v7ContractValid
            || (
              fullImplementation.blockers.length === 1
              && fullImplementation.blockers[0]
                === "research_report_does_not_embed_full_implementation_manifest"
            )
          )
        )
      );
    const currentnessStatus = status(currentness?.status);
    const currentnessObservedAt = Number.isSafeInteger(currentness?.observed_at_ms)
      && currentness.observed_at_ms >= 0
      ? currentness.observed_at_ms
      : null;
    const currentnessCreatedAt = Number.isSafeInteger(currentness?.report_created_at_ms)
      && currentness.report_created_at_ms >= 0
      ? currentness.report_created_at_ms
      : null;
    const reportTimeInput = currentness?.report_time_basis === "UTC_ASSUMED_FOR_NAIVE_ISO8601"
      ? `${currentness?.report_created_at || ""}Z`
      : currentness?.report_created_at;
    const parsedReportCreatedAt = typeof reportTimeInput === "string"
      ? Date.parse(reportTimeInput)
      : Number.NaN;
    const expectedReportAge = currentnessObservedAt !== null
      && currentnessCreatedAt !== null
      && currentnessCreatedAt <= currentnessObservedAt
      ? currentnessObservedAt - currentnessCreatedAt
      : null;
    const parsedDatasetUtcMidnight = typeof currentness?.dataset_as_of === "string"
      && /^\d{4}-\d{2}-\d{2}$/.test(currentness.dataset_as_of)
      ? Date.parse(`${currentness.dataset_as_of}T00:00:00Z`)
      : Number.NaN;
    const datasetAsOfValid = currentness?.dataset_as_of === null || (
      Number.isFinite(parsedDatasetUtcMidnight)
      && new Date(parsedDatasetUtcMidnight).toISOString().slice(0, 10)
        === currentness.dataset_as_of
    );
    const observedDate = currentnessObservedAt === null ? null : new Date(currentnessObservedAt);
    const observedUtcMidnight = observedDate && Number.isFinite(observedDate.getTime())
      ? Date.UTC(
        observedDate.getUTCFullYear(),
        observedDate.getUTCMonth(),
        observedDate.getUTCDate(),
      )
      : null;
    const datasetUtcMidnight = typeof currentness?.dataset_as_of === "string"
      && datasetAsOfValid
      ? parsedDatasetUtcMidnight
      : null;
    const expectedDatasetCalendarDays = observedUtcMidnight !== null
      && Number.isFinite(datasetUtcMidnight)
      && datasetUtcMidnight <= observedUtcMidnight
      ? (observedUtcMidnight - datasetUtcMidnight) / 86_400_000
      : null;
    const currentnessBlockersValid = stringList(currentness?.blockers)
      && new Set(currentness.blockers).size === currentness.blockers.length;
    const currentnessGapsValid = stringList(currentness?.evidence_gaps)
      && new Set(currentness.evidence_gaps).size === currentness.evidence_gaps.length;
    const expectedCurrentnessStatus = currentnessBlockersValid && currentness.blockers.length > 0
      ? "BLOCK"
      : currentnessGapsValid && currentness.evidence_gaps.length > 0
        ? "PARTIAL"
        : "FACTS_AVAILABLE";
    const currentnessValid = isObject(currentness)
      && currentness.schema_version === "strategy-research-currentness-facts-v1"
      && currentness.basis === "VERIFIED_REPORT_TIMESTAMPS_WITH_CALLER_OBSERVATION"
      && ["FACTS_AVAILABLE", "PARTIAL", "BLOCK"].includes(currentnessStatus)
      && currentnessStatus === expectedCurrentnessStatus
      && currentness.report_created_at === payload.created_at
      && currentnessCreatedAt === payload.created_at_ms
      && Number.isFinite(parsedReportCreatedAt)
      && parsedReportCreatedAt === currentnessCreatedAt
      && ["ISO8601_EXPLICIT_OFFSET", "UTC_ASSUMED_FOR_NAIVE_ISO8601"].includes(
        currentness.report_time_basis,
      )
      && (currentness.observed_at_ms === null || currentnessObservedAt !== null)
      && currentness.report_age_ms === expectedReportAge
      && datasetAsOfValid
      && [
        "REPORT_SUMMARY_AND_SELECTION_ALIGNMENT",
        "REPORT_SUMMARY",
        "SELECTION_ALIGNMENT",
        "NOT_AVAILABLE",
      ].includes(currentness.dataset_as_of_source)
      && (
        currentness.dataset_as_of === null
          ? currentness.dataset_as_of_source === "NOT_AVAILABLE"
          : currentness.dataset_as_of_source !== "NOT_AVAILABLE"
      )
      && currentness.calendar_days_since_dataset_as_of === expectedDatasetCalendarDays
      && currentness.dataset_age_basis === "UTC_CALENDAR_DAYS_NOT_TRADING_SESSIONS"
      && currentness.facts_complete === (currentnessStatus === "FACTS_AVAILABLE")
      && currentness.report_age_threshold_ms === null
      && currentness.dataset_age_threshold_calendar_days === null
      && currentness.report_age_policy_status === "NOT_DEFINED"
      && currentness.dataset_freshness_policy_status === "NOT_DEFINED"
      && currentness.threshold_applied === false
      && currentness.freshness_conclusion_allowed === false
      && currentness.stale_claim_allowed === false
      && currentness.dataset_currentness_checked === false
      && currentness.report_age_policy_checked === false
      && currentnessBlockersValid
      && currentnessGapsValid
      && currentness.read_only === true
      && currentness.research_only === true
      && currentness.descriptive_only === true
      && currentness.profitability_proven === false
      && currentness.performance_claim_allowed === false
      && currentness.parameter_selection_allowed === false
      && currentness.paper_authorized === false
      && currentness.live_order_allowed === false;
    const baseConditionIds = [
      "parameter_plateau_not_preserved",
      "cost_stress_break_even_not_preserved",
      "fixed_parameter_time_slice_robustness_not_preserved",
      "strategy_signal_implementation_changed",
      "research_implementation_closure_changed",
    ];
    const replayConditionIds = [
      "frozen_test_replay_not_preserved",
      "holdout_confirmation_replay_not_preserved",
    ];
    const admissionFailureConditionId = "preregistered_failure_admission_blocked";
    const searchLineageFailureConditionId = "search_lineage_live_at_selection_not_verified";
    const mechanismFailureConditionIds = hypothesisV2ConditionIds.map(
      (conditionId) => `mechanism_failure:${conditionId}`,
    );
    const futureFailureConditionIds = expectedFutureAdmissionChecks.map(
      ([conditionId]) => `future_standard_failure:${conditionId}`,
    );
    const conditionIds = v7ContractValid
      ? [
        ...baseConditionIds,
        ...replayConditionIds,
        admissionFailureConditionId,
        ...mechanismFailureConditionIds,
        ...futureFailureConditionIds,
        searchLineageFailureConditionId,
      ]
      : v6ContractValid
        ? [
          ...baseConditionIds,
          ...replayConditionIds,
          admissionFailureConditionId,
          ...mechanismFailureConditionIds,
          ...futureFailureConditionIds,
        ]
        : v5ContractValid
          ? [...baseConditionIds, ...replayConditionIds]
          : baseConditionIds;
    const failureStatus = status(failureConditions?.status);
    const expectedFailureSchema = v7ContractValid
      ? "strategy-research-failure-conditions-v4"
      : v6ContractValid
        ? "strategy-research-failure-conditions-v3"
        : v5ContractValid
          ? "strategy-research-failure-conditions-v2"
          : "strategy-research-failure-conditions-v1";
    const failureV3Fields = [
      "schema_version",
      "status",
      "observed",
      "evidence_gaps",
      "conditions",
      "descriptive_only",
      "profitability_proven",
      "parameter_selection_allowed",
      "paper_authorized",
      "live_order_allowed",
      "preregistered_failure_admission_status",
    ];
    const failureV4Fields = [...failureV3Fields, "search_lineage_status"];
    const failureConditionsValid = isObject(failureConditions)
      && failureConditions.schema_version === expectedFailureSchema
      && (v7ContractValid
        ? exactKeys(failureConditions, failureV4Fields)
          && failureConditions.preregistered_failure_admission_status === admissionStatus
          && failureConditions.search_lineage_status === searchLineageStatus
        : v6ContractValid
          ? exactKeys(failureConditions, failureV3Fields)
            && failureConditions.preregistered_failure_admission_status === admissionStatus
          : !hasOwn(failureConditions, "preregistered_failure_admission_status")
            && !hasOwn(failureConditions, "search_lineage_status"))
      && ["TRIGGERED", "GAPS", "NOT_IN_REPORT"].includes(failureStatus)
      && exactStringList(failureConditions.observed)
      && exactStringList(failureConditions.evidence_gaps)
      && Array.isArray(failureConditions.conditions)
      && failureConditions.conditions.length === (noMatch ? 0 : conditionIds.length)
      && failureConditions.conditions.every((condition) => isObject(condition)
        && (!postSelectionContractValid || exactKeys(condition, [
          "condition_id",
          "evidence_status",
          "triggered",
          "blockers",
        ]))
        && conditionIds.includes(condition.condition_id)
        && typeof condition.evidence_status === "string"
        && [null, true, false].includes(condition.triggered)
        && exactStringList(condition.blockers))
      && failureConditions.descriptive_only === true
      && failureConditions.profitability_proven === false
      && failureConditions.parameter_selection_allowed === false
      && failureConditions.paper_authorized === false
      && failureConditions.live_order_allowed === false
      && (
        failureStatus !== "TRIGGERED"
        || failureConditions.observed.length > 0
      )
      && (
        failureStatus !== "GAPS"
        || (failureConditions.observed.length === 0 && failureConditions.evidence_gaps.length > 0)
      )
      && (
        failureStatus !== "NOT_IN_REPORT"
        || (noMatch && failureConditions.conditions.length === 0)
      );
    const sameStringSet = (left, right) => stringList(left)
      && stringList(right)
      && new Set(left).size === left.length
      && new Set(right).size === right.length
      && left.length === right.length
      && left.every((item) => right.includes(item));
    const conditionById = new Map(
      Array.isArray(failureConditions?.conditions)
        ? failureConditions.conditions.map((condition) => [condition?.condition_id, condition])
        : [],
    );
    const parameterTriggered = parameterStatus === "PASS"
      ? false
      : ["REVIEW", "NOT_ENOUGH_VARIANTS", "BLOCK"].includes(parameterStatus) ? true : null;
    const costTriggered = costStatus === "PASS"
      && cost?.break_even_preserved === true
      && typeof cost?.worst_stressed_return_pct === "number"
      && cost.worst_stressed_return_pct > 0
      ? false
      : ["REVIEW", "BLOCK"].includes(costStatus)
        || cost?.break_even_preserved === false
        || (typeof cost?.worst_stressed_return_pct === "number" && cost.worst_stressed_return_pct <= 0)
        ? true
        : null;
    const temporalTriggered = temporalStatus === "PASS"
      && chronological?.usable_fold_count > 0
      && chronological?.positive_fold_count > 0
      ? false
      : ["REVIEW", "BLOCK"].includes(temporalStatus) ? true : null;
    const signalTriggered = implementationStatus === "MATCH"
      ? false
      : implementationStatus === "MISMATCH" ? true : null;
    const fullTriggered = fullImplementationStatus === "MATCH"
      ? false
      : fullImplementationStatus === "MISMATCH" ? true : null;
    const expectedConditionBindings = [
      ["parameter_plateau_not_preserved", parameterStatus, parameterTriggered, plateau?.blockers],
      ["cost_stress_break_even_not_preserved", costStatus, costTriggered, cost?.blockers],
      ["fixed_parameter_time_slice_robustness_not_preserved", temporalStatus, temporalTriggered, chronological?.blockers],
      ["strategy_signal_implementation_changed", implementationStatus, signalTriggered, implementation?.blockers],
      ["research_implementation_closure_changed", fullImplementationStatus, fullTriggered, fullImplementation?.blockers],
      ...(postSelectionContractValid ? [
        [
          "frozen_test_replay_not_preserved",
          frozenTestStatus,
          frozenTestStatus === "PASS" ? false : frozenTestStatus === "BLOCK" ? true : null,
          postSelection?.frozen_test?.blockers,
        ],
        [
          "holdout_confirmation_replay_not_preserved",
          holdoutStatus,
          holdoutStatus === "PASS" ? false : holdoutStatus === "BLOCK" ? true : null,
          postSelection?.holdout_confirmation?.blockers,
        ],
      ] : []),
      ...(structuredMechanismContractValid ? [
        [
          admissionFailureConditionId,
          admissionStatus,
          admissionStatus === "PASS" ? false : admissionStatus === "BLOCK" ? true : null,
          admission?.blockers,
        ],
        ...activeMechanismChecks.map((check) => [
          `mechanism_failure:${check.condition_id}`,
          check.status,
          check.status === "PASS" && check.triggered === false
            ? false
            : check.status === "BLOCK" && check.triggered === true
              ? true
              : null,
          check.blockers,
        ]),
        ...futureAdmissionChecks.map((check) => [
          `future_standard_failure:${check.condition_id}`,
          check.status,
          null,
          check.blockers,
        ]),
      ] : []),
      ...(v7ContractValid ? [[
        searchLineageFailureConditionId,
        searchLineageStatus,
        searchLineageStatus === "BOUND" ? false : searchLineageStatus === "BLOCK" ? true : null,
        searchLineage?.blockers,
      ]] : []),
    ];
    const failureBindingValid = noMatch
      ? failureStatus === "NOT_IN_REPORT"
        && sameStringSet(failureConditions?.observed, ["strategy_not_in_frozen_research_report"])
        && sameStringSet(failureConditions?.evidence_gaps, [
          "strategy_specific_parameter_cost_and_time_evidence_missing",
          "dataset_currentness_not_checked",
          "report_age_policy_not_checked",
          "natural_forward_performance_not_proven_by_strategy_report",
        ])
        && failureConditions?.conditions?.length === 0
      : (() => {
        if (conditionById.size !== expectedConditionBindings.length) return false;
        const bindingsMatch = expectedConditionBindings.every(([id, evidenceStatus, triggered, blockers]) => {
          const condition = conditionById.get(id);
          return isObject(condition)
            && (postSelectionContractValid
              ? condition.evidence_status === evidenceStatus
              : status(condition.evidence_status) === evidenceStatus)
            && condition.triggered === triggered
            && sameStringSet(condition.blockers, blockers);
        });
        const expectedObserved = expectedConditionBindings
          .filter(([, , triggered]) => triggered === true)
          .map(([id]) => id);
        const expectedGaps = [
          "dataset_currentness_not_checked",
          "report_age_policy_not_checked",
          "natural_forward_performance_not_proven_by_strategy_report",
          ...expectedConditionBindings
            .filter(([, , triggered]) => triggered === null)
            .map(([id]) => `${id}_not_checked`),
        ];
        const expectedStatus = expectedObserved.length ? "TRIGGERED" : "GAPS";
        return bindingsMatch
          && failureStatus === expectedStatus
          && sameStringSet(failureConditions?.observed, expectedObserved)
          && sameStringSet(failureConditions?.evidence_gaps, expectedGaps);
      })();
    const aggregateCountsValid = plateauValid
      && plateau.eligible_variant_count <= plateau.frozen_variant_count
      && plateau.near_best_eligible_variant_count <= plateau.eligible_variant_count
      && plateau.adjacent_near_best_variant_count <= plateau.near_best_eligible_variant_count
      && plateau.plateau_width <= plateau.near_best_eligible_variant_count
      && costValid
      && cost.pass_cell_count <= cost.evaluated_cell_count
      && chronologicalValid
      && chronological.pass_cell_count <= chronological.evaluated_cell_count
      && chronological.positive_fold_count <= chronological.usable_fold_count;
    const statusClaimsValid = ["PASS", "REVIEW", "NOT_ENOUGH_VARIANTS", "BLOCK", "UNKNOWN"]
      .includes(parameterStatus)
      && ["PASS", "REVIEW", "BLOCK", "UNKNOWN"].includes(costStatus)
      && ["PASS", "REVIEW", "BLOCK", "UNKNOWN"].includes(temporalStatus)
      && (parameterStatus !== "PASS" || (
        plateau.plateau_width >= 2
        && plateau.adjacent_near_best_variant_count >= 1
        && plateau.peak_only === false
        && typeof plateau.best_adjusted_score === "number"
        && plateau.best_adjusted_score > 0
      ))
      && (costStatus !== "PASS" || (
        cost.break_even_preserved === true
        && typeof cost.worst_stressed_return_pct === "number"
        && cost.worst_stressed_return_pct > 0
      ))
      && (temporalStatus !== "PASS" || (
        chronological.usable_fold_count > 0
        && chronological.positive_fold_count > 0
      ));
    const matchedEvidenceValid = !matched || (
      typeof payload.selected_strategy_id === "string"
      && payload.selected_strategy_id.length > 0
      && plateau.schema_version === "strategy-parameter-plateau-v2"
      && plateau.topology_basis === "FROZEN_VARIANT_SEQUENCE_ADJACENCY"
      && plateau.numeric_parameter_distance_checked === false
      && plateau.frozen_variant_count >= 3
      && cost.evaluated_cell_count > 0
      && chronological.evaluated_cell_count > 0
      && chronological.evaluation_mode === "FIXED_PARAMETER_CHRONOLOGICAL_SLICES"
      && chronological.parameters_refit_per_fold === false
      && ["MATCH", "MISMATCH", "BLOCK", "UNKNOWN"].includes(implementationStatus)
    );
    const noMatchValid = !noMatch || (
      payload.selected_strategy_id === null
      && parameterStatus === "UNKNOWN"
      && costStatus === "UNKNOWN"
      && temporalStatus === "UNKNOWN"
      && implementationStatus === "NOT_IN_REPORT"
    );
    const frozenValid = payload.ok === true
      && status(payload.status) === "AVAILABLE"
      && status(payload.source_verification_status) === "PASS"
      && (v3ContractValid || v5ContractValid || v6ContractValid || v7ContractValid)
      && contract.connection_status === "VERIFIED_FROZEN_SOURCE"
      && contract.mode === "FROZEN_RESEARCH_EVIDENCE"
      && contract.research_report_source === "CURRENT_VERIFIED_STRATEGY_RESEARCH_REPORT"
      && contract.interpretation === "DESCRIPTIVE_RESEARCH_EVIDENCE_ONLY"
      && contract.research_only === true
      && contract.descriptive_only === true
      && contract.development_heuristic_only === false
      && contract.profitability_proven === false
      && contract.performance_claim_allowed === false
      && contract.parameter_selection_allowed === false
      && status(contract.hypothesis_preregistration_status) === hypothesisStatus
      && contract.implementation_currentness_checked === implementation?.checked
      && status(contract.implementation_currentness_status) === implementationStatus
      && contract.implementation_currentness_match === implementation?.matches_current
      && contract.implementation_currentness_basis === implementation?.basis
      && contract.full_implementation_manifest_checked === fullImplementation?.checked
      && status(contract.full_implementation_manifest_status) === fullImplementationStatus
      && contract.full_implementation_manifest_match === fullImplementation?.matches_current
      && contract.full_implementation_manifest_basis === fullImplementation?.basis
      && contract.currentness_facts_schema_version === currentness?.schema_version
      && status(contract.currentness_facts_status) === currentnessStatus
      && contract.currentness_threshold_applied === false
      && contract.dataset_currentness_checked === false
      && contract.report_age_policy_checked === false
      && contract.paper_authorized === false
      && contract.live_order_allowed === false
      && ["MATCHED", "NOT_IN_REPORT"].includes(matchStatus)
      && contractMatchStatus === matchStatus
      && status(plateau.status) === parameterStatus
      && status(cost.status) === costStatus
      && status(chronological.status) === temporalStatus
      && Number.isInteger(payload.report_schema_version)
      && payload.report_schema_version >= 3
      && (
        (v7ContractValid && fullImplementationStatus === "NOT_AVAILABLE")
        || (payload.report_schema_version >= 6 && fullImplementationStatus !== "NOT_AVAILABLE")
        || (payload.report_schema_version < 6 && fullImplementationStatus === "NOT_AVAILABLE")
      )
      && Number.isSafeInteger(payload.created_at_ms)
      && payload.created_at_ms > 0
      && hash256(payload.pointer_hash)
      && hash256(payload.batch_spec_hash)
      && hash256(payload.dataset_manifest_hash)
      && hash256(payload.batch_run_hash)
      && payload.implementation_currentness_checked === implementation?.checked
      && status(payload.implementation_currentness_status) === implementationStatus
      && payload.implementation_currentness_match === implementation?.matches_current
      && payload.implementation_currentness_basis === implementation?.basis
      && payload.full_implementation_manifest_checked === fullImplementation?.checked
      && status(payload.full_implementation_manifest_status) === fullImplementationStatus
      && payload.full_implementation_manifest_match === fullImplementation?.matches_current
      && payload.full_implementation_manifest_basis === fullImplementation?.basis
      && status(payload.currentness_facts_status) === currentnessStatus
      && payload.dataset_currentness_checked === false
      && payload.report_age_policy_checked === false
      && formalBoundaryValid
      && safeScope(payload)
      && authoritySafe(payload)
      && scopeValid
      && hypothesisValid
      && plateauValid
      && costValid
      && chronologicalValid
      && implementationValid
      && fullImplementationValid
      && currentnessValid
      && failureConditionsValid
      && failureBindingValid
      && aggregateCountsValid
      && statusClaimsValid
      && matchedEvidenceValid
      && noMatchValid;
    if (!frozenValid) return empty;

    const metricPresentation = Object.freeze({
      validation_adjusted_score: Object.freeze({ label: "验证调整分", kind: "score" }),
      median_validation_return_pct: Object.freeze({ label: "验证收益中位数", kind: "percent" }),
      median_validation_excess_return_pct: Object.freeze({ label: "验证超额中位数", kind: "percent" }),
      validation_worst_drawdown_pct: Object.freeze({ label: "验证最差回撤", kind: "percent" }),
      validation_trade_count: Object.freeze({ label: "验证交易数", kind: "trade_count" }),
      minimum_stressed_return_pct: Object.freeze({ label: "压力后最低收益", kind: "percent" }),
      minimum_positive_fold_count: Object.freeze({ label: "正收益切片下限", kind: "fold_count" }),
    });
    const operatorPresentation = Object.freeze({
      LT: "<",
      LTE: "≤",
      GT: ">",
      GTE: "≥",
    });
    const normalizedFiniteNumber = (value) => (Object.is(value, -0) ? 0 : value);
    const signedFixed = (value, digits) => {
      const normalized = normalizedFiniteNumber(value);
      return `${normalized > 0 ? "+" : ""}${normalized.toFixed(digits)}`;
    };
    const conditionValueText = (value, metric, { observed = false } = {}) => {
      const presentation = metricPresentation[metric];
      if (!presentation || typeof value !== "number" || !Number.isFinite(value)) return "--";
      if (presentation.kind === "percent") {
        return `${observed ? signedFixed(value, 2) : normalizedFiniteNumber(value).toFixed(2)}%`;
      }
      if (presentation.kind === "score") {
        return observed ? signedFixed(value, 4) : normalizedFiniteNumber(value).toFixed(4);
      }
      const countText = Number.isInteger(value)
        ? String(normalizedFiniteNumber(value))
        : normalizedFiniteNumber(value).toFixed(2);
      return presentation.kind === "trade_count" ? `${countText} 笔` : `${countText} 个`;
    };
    const freezeRows = (rows) => Object.freeze(rows.map((row) => Object.freeze(row)));
    const mechanismConditionRows = structuredMechanismContractValid && matchStatus === "MATCHED"
      ? freezeRows(activeMechanismChecks.map((check) => {
        const metric = metricPresentation[check.metric];
        const predicateText = `${metric.label} ${operatorPresentation[check.operator]} ${conditionValueText(check.threshold, check.metric)}`;
        const observationText = check.metric_value === null
          ? "观测 --"
          : `观测 ${conditionValueText(check.metric_value, check.metric, { observed: true })}`;
        if (check.status === "NOT_APPLICABLE") {
          return {
            conditionId: check.condition_id,
            predicateText,
            observationText,
            outcomeText: "不适用 · 未形成通过结论",
            boundaryText: "当前无候选 · 不选参、不授权",
            rawStatus: check.status,
          };
        }
        if (check.triggered === null) {
          return {
            conditionId: check.condition_id,
            predicateText,
            observationText,
            outcomeText: "未解析 · 阻断后续研究",
            boundaryText: "未形成准入结论",
            rawStatus: check.status,
          };
        }
        if (check.triggered === true) {
          return {
            conditionId: check.condition_id,
            predicateText,
            observationText,
            outcomeText: "已触发 · 阻断后续研究",
            boundaryText: "不得进入冻结后历史复算",
            rawStatus: check.status,
          };
        }
        return {
          conditionId: check.condition_id,
          predicateText,
          observationText,
          outcomeText: "未触发",
          boundaryText: "仅进入历史研究 · 不授权",
          rawStatus: check.status,
        };
      }))
      : emptyConditionRows;
    const futureConditionLabels = Object.freeze({
      fresh_single_use_holdout_failure: "单次新鲜留出",
      natural_forward_statistical_failure: "自然前向成熟度",
    });
    const futureBoundaryLabels = Object.freeze({
      fresh_single_use_holdout_failure: "到期触发时：退役或新登记",
      natural_forward_statistical_failure: "到期触发时：退役假设",
    });
    const futureConditionRows = structuredMechanismContractValid && matchStatus === "MATCHED"
      ? freezeRows(futureAdmissionChecks.map((check) => ({
        conditionId: check.condition_id,
        stageText: futureConditionLabels[check.condition_id],
        outcomeText: "未到期 · 未评估、非通过",
        boundaryText: futureBoundaryLabels[check.condition_id],
        rawStatus: check.status,
      })))
      : emptyConditionRows;

    const dateText = typeof payload.created_at === "string" && /^\d{4}-\d{2}-\d{2}/.test(payload.created_at)
      ? payload.created_at.slice(0, 10)
      : "时间已核验";
    const sourceText = `固定指针 + 语义复算 · ${dateText} · ${payload.batch_run_hash.slice(0, 8)}`;
    const ageText = typeof currentness.report_age_ms === "number"
      ? (() => {
        const wholeDays = Math.floor(currentness.report_age_ms / 86_400_000);
        const wholeHours = Math.floor((currentness.report_age_ms % 86_400_000) / 3_600_000);
        return wholeDays > 0 ? `${wholeDays} 天 ${wholeHours} 小时` : `${wholeHours} 小时`;
      })()
      : "未形成";
    const datasetAgeText = typeof currentness.calendar_days_since_dataset_as_of === "number"
      ? `${currentness.calendar_days_since_dataset_as_of} 个 UTC 日历日`
      : "未形成";
    const currentnessText = currentnessStatus === "BLOCK"
      ? "时间事实合同阻断 · 不作新鲜或过期判断"
      : `报告年龄 ${ageText} · 数据截止 ${currentness.dataset_as_of || "未提供"} · 相距 ${datasetAgeText} · 未定义新鲜/过期阈值`;
    const coverageParts = [
      scope.selection_symbol_count === null ? "标的 --" : `${scope.selection_symbol_count} 标的`,
      scope.parameter_variant_count === null ? "变体 --" : `${scope.parameter_variant_count} 变体`,
      scope.selection_cell_count === null ? "选择单元 --" : `${scope.selection_cell_count} 选择单元`,
      scope.forward_candidate_count === null ? "前向候选 --" : `${scope.forward_candidate_count} 前向候选`,
    ];
    const hypothesisText = hypothesisStatus === "BOUND"
      ? `${hypothesis.hypothesis_id} · ${hypothesis.mechanism_family} · 事前绑定`
      : hypothesisStatus === "LEGACY_NOT_BOUND"
        ? "历史报告未封存机器可验事前假设合同"
        : noMatch
          ? "事前假设绑定于报告内其他策略 · 当前策略未纳入"
          : "事前假设合同阻断 · 不外推研究结论";
    const rawSearchLineageStatus = v7ContractValid
      ? searchLineageStatus
      : "NOT_AVAILABLE";
    const lineageText = v7ContractValid
      ? matched
        ? `选择时核验；当前仅离线报告/回执自洽 · 既往 ${searchLineage.prior_trial_count} + 本批 ${searchLineage.current_trial_count} = 累计 ${searchLineage.cumulative_trial_count} 次`
        : "当前策略不在报告 · 检索谱系不借用，计数未提供"
      : "历史报告未封存检索谱系 · 不补写选择时核验结论";
    const hypothesisFailureText = hypothesisStatus === "BOUND"
      ? structuredMechanismContractValid
        ? `结构化机制失效条件 ${hypothesisV2Conditions.length} 项 · 开发期可重算 · 新鲜留出与自然前向仍待到期`
        : `机制失效条件 ${hypothesis.mechanism_specific_failure_conditions.length} 项 · 新鲜留出 + 60/8 自然前向 · 到期统计复核`
      : hypothesisStatus === "LEGACY_NOT_BOUND"
        ? "事前失效条件未封存 · 历史结果不能补写为事前证据"
        : noMatch
          ? "事前失效条件不适用于当前策略 · 需新 ID 与新登记"
          : "事前失效合同未通过语义核验";
    const pct = (value) => typeof value === "number" && Number.isFinite(value)
      ? `${value.toFixed(2)}%`
      : "--";
    const signedPct = (value) => typeof value === "number" && Number.isFinite(value)
      ? `${value > 0 ? "+" : ""}${value.toFixed(2)}%`
      : "--";
    const replayStageText = (stage, label, { holdout = false } = {}) => {
      const stageStatus = status(stage?.status);
      const boundary = holdout ? " · 非自然前向" : " · 历史重放";
      if (!postSelectionContractValid) {
        return `${label}${boundary}：历史报告未包含阶段摘要 · 非盈利证明`;
      }
      if (stageStatus === "NOT_RUN") {
        return `${label}${boundary} · 未运行 · 未形成历史收益数字 · 非盈利证明`;
      }
      const outcome = stageStatus === "PASS" ? "复算记录完整" : "存在阻断";
      const metricsAvailable = stageMetricFields.every(
        (field) => typeof stage?.[field] === "number" && Number.isFinite(stage[field]),
      ) && Number.isSafeInteger(stage?.total_trades);
      if (!metricsAvailable) {
        return `${label}${boundary} · ${outcome} · 收益、成本、回撤与交易样本未形成 · 非盈利证明`;
      }
      return `${label}${boundary} · ${outcome} · ${stage.candidate_count} 候选 · ${stage.replay_verified_cell_count}/${stage.cell_count} 单元已核对 · 最低收益 ${signedPct(stage.minimum_configured_return_pct)} · 最低超额 ${signedPct(stage.minimum_excess_return_pct)} · 压力后最低 ${signedPct(stage.minimum_severe_cost_return_pct)} · 最差回撤 ${pct(stage.worst_drawdown_pct)} · ${stage.total_trades} 笔 · 非盈利证明`;
    };
    const postSelectionText = !postSelectionContractValid
      ? "历史报告未包含冻结后 TEST / 留出摘要 · 不补写收益结论"
      : postSelectionStatus === "PASS"
        ? "冻结 TEST 与单次历史留出复算记录完整 · 历史回测 · 非自然前向"
        : postSelectionStatus === "BLOCK"
          ? "冻结后历史复算存在阻断 · 不外推收益结论"
          : "冻结后保护阶段未运行 · 未形成历史收益数字";
    const frozenTestText = replayStageText(postSelection?.frozen_test, "冻结 TEST");
    const holdoutText = replayStageText(
      postSelection?.holdout_confirmation,
      "单次历史留出",
      { holdout: true },
    );
    const triggeredMechanismCheckCount = activeMechanismChecks.filter(
      (check) => check.status === "BLOCK" && check.triggered === true,
    ).length;
    const unresolvedMechanismCheckCount = activeMechanismChecks.filter(
      (check) => check.status === "BLOCK" && check.triggered === null,
    ).length;
    const rawMechanismStatus = !structuredMechanismContractValid
      ? "NOT_AVAILABLE"
      : noMatch
        ? "NOT_IN_REPORT"
        : admissionCandidateCount === 0
          ? "NOT_APPLICABLE"
          : triggeredMechanismCheckCount > 0 || unresolvedMechanismCheckCount > 0
            ? "BLOCK"
            : "PASS";
    const rawFutureConditionStatus = !structuredMechanismContractValid
      ? "NOT_AVAILABLE"
      : noMatch
        ? "NOT_IN_REPORT"
        : "NOT_DUE";
    const mechanismConditionText = !structuredMechanismContractValid
      ? "历史报告未包含结构化机制条件 · 不补写开发期结论"
      : noMatch
        ? "当前策略不在报告 · 不借用其他策略的机制条件结论"
        : admissionCandidateCount === 0
          ? `结构化机制条件 ${hypothesisV2Conditions.length} 项 · 当前无候选，标记不适用 · 未形成通过结论`
          : triggeredMechanismCheckCount > 0
            ? `结构化机制条件 ${hypothesisV2Conditions.length} 项 · 已触发 ${triggeredMechanismCheckCount} 项 · 阻断后续研究`
            : unresolvedMechanismCheckCount > 0
              ? `结构化机制条件 ${hypothesisV2Conditions.length} 项 · ${unresolvedMechanismCheckCount} 项未解析 · 阻断后续研究`
              : `结构化机制条件 ${hypothesisV2Conditions.length} 项 · 适用开发期条件未触发 · 仅历史研究门`;
    const futureConditionText = !structuredMechanismContractValid
      ? "历史报告未包含未来标准条件 · 不补写到期结论"
      : noMatch
        ? "当前策略不在报告 · 不借用本批未来条件状态"
        : "单次新鲜留出与自然前向成熟度均未到期 · 未评估、非通过";
    if (noMatch) {
      return Object.freeze({
        valid: true,
        connectionStatus: "VERIFIED_NO_MATCH",
        modeText: "冻结来源已核验 · 当前策略未纳入报告",
        sourceText,
        implementationText: fullImplementationStatus === "MATCH"
          ? "报告完整实现闭包与当前一致 · 当前策略无冻结记录"
          : fullImplementationStatus === "MISMATCH"
            ? "报告完整实现闭包已变化 · 当前策略亦无冻结记录"
            : "当前策略无冻结记录 · 完整实现闭包未核验",
        currentnessText,
        hypothesisText,
        lineageText,
        hypothesisFailureText,
        admissionText: admissionContractValid
          ? "当前策略不在报告 · 不借用本批事前门禁结论"
          : admissionStatus === "BLOCK"
          ? "事前 BLOCK_RESEARCH 条件已触发 · 本批未冻结候选"
          : admissionStatus === "PASS"
            ? "事前失效门未触发 · 当前策略未进入本批冻结候选 · 非选参授权"
            : "历史报告未包含事前研究门禁 · 不补写准入结论",
        mechanismConditionText,
        futureConditionText,
        mechanismConditionRows: emptyConditionRows,
        futureConditionRows: emptyConditionRows,
        postSelectionText: postSelectionContractValid
          ? "当前策略未进入冻结后历史复算 · 未形成收益数字 · 非自然前向"
          : postSelectionText,
        frozenTestText,
        holdoutText,
        parameterText: "参数平台稳定性：当前策略无冻结记录",
        costText: "成本压力：当前策略无冻结记录",
        temporalText: "固定参数时间切片：当前策略无冻结记录",
        coverageText: coverageParts.join(" · "),
        failureText: "当前策略无冻结失效条件 · 年龄仅列事实，阈值/自然前向仍未核验",
        detailText: "来源有效不等于当前策略有效；当前策略没有可核对的冻结实现身份，模拟未授权，实盘永久硬锁",
        rawParameterStatus: parameterStatus,
        rawCostStatus: costStatus,
        rawTemporalStatus: temporalStatus,
        rawImplementationStatus: implementationStatus,
        rawFullImplementationStatus: fullImplementationStatus,
        rawHypothesisStatus: hypothesisStatus,
        rawSearchLineageStatus,
        rawAdmissionStatus: admissionContractValid ? admissionStatus : "NOT_AVAILABLE",
        rawMechanismStatus,
        rawFutureConditionStatus,
        rawPostSelectionStatus: postSelectionContractValid ? postSelectionStatus : "NOT_AVAILABLE",
        rawFrozenTestStatus: postSelectionContractValid ? frozenTestStatus : "NOT_AVAILABLE",
        rawHoldoutStatus: postSelectionContractValid ? holdoutStatus : "NOT_AVAILABLE",
        permissionText: PERMISSION_PRESENTATIONS.plan,
      });
    }

    const currentImplementationMatched = implementationStatus === "MATCH"
      && fullImplementationStatus === "MATCH";
    const historicalPrefix = currentImplementationMatched ? "" : "历史冻结 · ";
    const parameterText = historicalPrefix + ({
      PASS: `冻结序列存在相邻近优点 · 平台宽度 ${plateau.plateau_width ?? "--"} · 非数值距离`,
      REVIEW: "冻结序列邻接平台不足 · 待人工复核",
      NOT_ENOUGH_VARIANTS: "冻结变体不足 · 无法判断平台",
      BLOCK: "参数平台证据合同阻断",
    }[parameterStatus] || "参数平台稳定性：未核验");
    const costText = historicalPrefix + ({
      PASS: `压力成本后仍保持盈亏线 · 最差 ${pct(cost.worst_stressed_return_pct)} · 非盈利证明`,
      REVIEW: "成本压力证据待人工复核",
      BLOCK: `压力成本条件未保持 · 最差 ${pct(cost.worst_stressed_return_pct)}`,
    }[costStatus] || "成本压力：未核验");
    const temporalText = historicalPrefix + ({
      PASS: `固定参数时间切片已记录 · ${chronological.positive_fold_count ?? "--"}/${chronological.usable_fold_count ?? "--"} 正收益 · 非 WFO`,
      REVIEW: "固定参数时间切片待人工复核 · 非 WFO",
      BLOCK: "固定参数时间切片存在阻断 · 非 WFO",
    }[temporalStatus] || "固定参数时间切片：未核验 · 非 WFO");
    const implementationText = fullImplementationStatus === "MATCH"
      ? (implementationStatus === "MATCH"
        ? `完整研究实现闭包与当前一致 · ${fullImplementation.expected_source_count} 个源码文件 + 运行时`
        : implementationStatus === "MISMATCH"
          ? "完整研究实现闭包一致，但策略信号指纹已变化 · 需核对非源码输入"
          : "完整研究实现闭包一致 · 策略信号身份核对失败")
      : fullImplementationStatus === "MISMATCH"
        ? "完整研究实现闭包或运行时已变化 · 冻结结果不可视为当前实现结果"
        : fullImplementationStatus === "BLOCK"
          ? "完整研究实现闭包核对失败 · 当前实现身份未核验"
          : implementationStatus === "MATCH"
            ? "策略信号指纹一致 · 历史报告未封存完整实现闭包"
            : implementationStatus === "MISMATCH"
              ? "策略信号指纹已变化 · 历史报告无完整闭包复核"
              : "策略实现当前性：未核验";
    const implementationMismatch = implementationStatus === "MISMATCH"
      || fullImplementationStatus === "MISMATCH";
    const connectionStatus = currentImplementationMatched
      ? "VERIFIED_FROZEN"
      : implementationMismatch
        ? "VERIFIED_IMPLEMENTATION_MISMATCH"
        : implementationStatus === "MATCH" && fullImplementationStatus === "NOT_AVAILABLE"
          ? "VERIFIED_SIGNAL_ONLY"
          : "VERIFIED_IMPLEMENTATION_UNCHECKED";
    const modeText = currentImplementationMatched
      ? (payload.formal_single_use
        ? "冻结单次研究证据 · 完整实现闭包一致 · 仍需人工复核"
        : "冻结开发研究证据 · 完整实现闭包一致 · 非盲测")
      : implementationMismatch
        ? "历史冻结研究证据 · 当前策略信号实现已变化"
        : implementationStatus === "MATCH" && fullImplementationStatus === "NOT_AVAILABLE"
          ? "历史冻结研究证据 · 仅信号指纹一致 · 非盲测"
          : "历史冻结研究证据 · 当前实现身份未核验";
    const failureLabels = {
      parameter_plateau_not_preserved: "参数平台未保持",
      cost_stress_break_even_not_preserved: "压力成本后未守住盈亏线",
      fixed_parameter_time_slice_robustness_not_preserved: "固定参数时间切片未保持",
      strategy_signal_implementation_changed: "策略信号实现已变化",
      research_implementation_closure_changed: "研究实现闭包已变化",
      frozen_test_replay_not_preserved: "冻结 TEST 历史复算未保持",
      holdout_confirmation_replay_not_preserved: "单次历史留出复算未保持",
      frozen_test_replay_not_preserved_not_checked: "冻结 TEST 历史复算未运行",
      holdout_confirmation_replay_not_preserved_not_checked: "单次历史留出复算未运行",
      dataset_currentness_not_checked: "数据新鲜度未核验",
      report_age_policy_not_checked: "报告年龄门槛未核验",
      natural_forward_performance_not_proven_by_strategy_report: "自然前向表现不由本报告证明",
      research_implementation_closure_changed_not_checked: "完整实现闭包未核验",
      strategy_signal_implementation_changed_not_checked: "策略信号实现未核验",
      search_lineage_live_at_selection_not_verified: "选择时检索谱系未核验",
    };
    const prioritizedFailureItems = (items) => [
      ...replayConditionIds.flatMap((id) => [id, `${id}_not_checked`]),
      ...items,
    ].filter((item, index, all) => items.includes(item) && all.indexOf(item) === index);
    const failureText = failureStatus === "TRIGGERED"
      ? `已触发：${prioritizedFailureItems(failureConditions.observed).slice(0, 3).map((item) => failureLabels[item] || item).join(" · ")}`
      : failureStatus === "GAPS"
        ? `未闭合：${prioritizedFailureItems(failureConditions.evidence_gaps).slice(0, 3).map((item) => failureLabels[item] || item).join(" · ")}`
        : "已核维度未触发失效 · 仍有未闭合证据";
    const admissionText = structuredMechanismContractValid
      ? admissionStatus === "BLOCK"
        ? "适用开发期标准或机制条件存在阻断 · 本批未冻结候选"
        : selectedAdmittedCount > 0
          ? "适用开发期标准与机制条件未触发 · 冻结资格仅供历史重放 · 非授权"
          : "当前策略无候选，机制条件不适用 · 未形成机制通过结论 · 非选参授权"
      : admissionStatus === "BLOCK"
        ? "事前 BLOCK_RESEARCH 条件已触发 · 本批未冻结候选"
        : admissionStatus === "PASS" && selectedAdmittedCount > 0
          ? "事前失效门未触发 · 冻结资格仅供后续历史重放 · 非授权"
          : admissionStatus === "PASS"
            ? "事前失效门未触发 · 当前策略未进入本批冻结候选 · 非选参授权"
            : "历史报告未包含事前研究门禁 · 不补写准入结论";
    return Object.freeze({
      valid: true,
      connectionStatus,
      modeText,
      sourceText,
      implementationText,
      currentnessText,
      hypothesisText,
      lineageText,
      hypothesisFailureText,
      admissionText,
      mechanismConditionText,
      futureConditionText,
      mechanismConditionRows,
      futureConditionRows,
      postSelectionText,
      frozenTestText,
      holdoutText,
      parameterText,
      costText,
      temporalText,
      coverageText: coverageParts.join(" · "),
      failureText,
      detailText: currentImplementationMatched
        ? "冻结报告内部语义已复算，完整源码文件与运行时闭包和当前一致；年龄与数据截止只列事实，新鲜/过期阈值仍未定义，不自动选参、不证明盈利，模拟未授权，实盘永久硬锁"
        : "冻结报告来源及历史语义仍可核对，但不得外推为当前实现结果；不自动选参、不证明盈利，模拟未授权，实盘永久硬锁",
      rawParameterStatus: parameterStatus,
      rawCostStatus: costStatus,
      rawTemporalStatus: temporalStatus,
      rawImplementationStatus: implementationStatus,
      rawFullImplementationStatus: fullImplementationStatus,
      rawHypothesisStatus: hypothesisStatus,
      rawSearchLineageStatus,
      rawAdmissionStatus: admissionContractValid ? admissionStatus : "NOT_AVAILABLE",
      rawMechanismStatus,
      rawFutureConditionStatus,
      rawPostSelectionStatus: postSelectionContractValid ? postSelectionStatus : "NOT_AVAILABLE",
      rawFrozenTestStatus: postSelectionContractValid ? frozenTestStatus : "NOT_AVAILABLE",
      rawHoldoutStatus: postSelectionContractValid ? holdoutStatus : "NOT_AVAILABLE",
      permissionText: PERMISSION_PRESENTATIONS.plan,
    });
  }

  const INTERNAL_BACKTEST_SNAPSHOT_V4_KEYS = Object.freeze([
    "schema_version", "ok", "status", "source_verification_status", "blockers",
    "generated_at", "pack_schema_version", "candidate_hash", "pack_hash", "evidence_hash",
    "pack_status", "promotion_status", "return_quality", "forward_promotion", "read_only",
    "profitability_proven", "performance_claim_allowed", "parameter_selection_allowed",
    "automatic_paper_activation_allowed", "research_only", "paper_authorized", "live_order_allowed",
  ]);
  const FORWARD_PROMOTION_V2_KEYS = Object.freeze([
    "schema_version", "status", "source_integrity_status", "decision", "maturity",
    "frozen_prefix", "audit", "tail_observation", "readiness_status",
    "readiness_promotion_status", "historical_contract_claim_status", "blockers",
    "promotion_blockers", "validation_scope", "manual_review_required",
    "profitability_proven", "performance_claim_allowed", "parameter_selection_allowed",
    "automatic_paper_activation_allowed", "research_only", "paper_authorized", "live_order_allowed",
  ]);
  const FORWARD_PROMOTION_V2_DECISION_KEYS = Object.freeze([
    "policy", "status", "decision_status", "research_action", "decision_hash",
    "later_settlements_used",
  ]);
  const FORWARD_PROMOTION_V2_MATURITY_KEYS = Object.freeze([
    "status", "forward_outcomes", "required_forward_outcomes", "remaining_forward_outcomes",
    "executed_rebalances", "required_executed_rebalances", "remaining_executed_rebalances",
    "both_thresholds_required", "first_due_settlement_index", "first_due_settlement_date",
    "first_due_settlement_hash",
  ]);
  const FORWARD_PROMOTION_V2_PREFIX_KEYS = Object.freeze([
    "status", "settlement_count", "outcome_period_count", "rebalance_execution_count",
    "decision_series_hash",
  ]);
  const FORWARD_PROMOTION_V2_AUDIT_KEYS = Object.freeze([
    "status", "conclusion", "verification_status", "semantic_recomputed", "audit_hash",
    "full_series_hash", "stage", "risk_acceptance",
  ]);
  const FORWARD_PROMOTION_V2_STAGE_KEYS = Object.freeze(["status", "stage_hash"]);
  const FORWARD_PROMOTION_V2_RISK_KEYS = Object.freeze([
    "status", "risk_hash", "required_max_drawdown_below_pct", "prefix_max_drawdown_pct",
  ]);
  const FORWARD_PROMOTION_V2_TAIL_KEYS = Object.freeze([
    "full_settlement_count", "frozen_prefix_settlement_count", "later_settlement_count",
    "full_series_hash", "frozen_decision_hash", "later_settlements_descriptive_only",
  ]);
  const FORWARD_PROMOTION_V2_SCOPE_KEYS = Object.freeze([
    "pack_validates_upstream_single_look_semantic_receipt", "settlement_database_reloaded_by_pack",
    "settlement_chain_independently_replayed_by_pack", "full_forward_rows_hash_bound",
    "first_joint_maturity_prefix_hash_bound", "decision_stage_and_risk_hashes_bound",
    "later_settlements_descriptive_only",
  ]);

  function internalBacktestReturnQualityPresentation(payload = {}) {
    const empty = Object.freeze({
      verified: false,
      connectionStatus: "UNKNOWN",
      qualityState: "UNKNOWN",
      statusText: "来源与合同未核验 · 当前数字不可用",
      detailText: "固定来源缺失或合同校验失败 · 模拟未授权 · 实盘永久硬锁",
      returnsText: "策略 -- · 基准 -- · 重算超额 --",
      costText: "成本绑定未核验 · 成本后 --",
      riskText: "压力最差 -- · 最大回撤 --",
      sampleText: "样本 -- · 时间证据未核验",
      validationStageText: "验证段来源未核验",
      validationStageDetailText: "验证段依据、样本和统计主张未核验",
      testStageText: "测试段来源未核验",
      testStageDetailText: "测试段依据、样本和统计主张未核验",
      validationStageRawStatus: "UNKNOWN",
      validationStageRawBenchmarkStatus: "UNKNOWN",
      validationStageRawClaimStatus: "UNKNOWN",
      testStageRawStatus: "UNKNOWN",
      testStageRawBenchmarkStatus: "UNKNOWN",
      testStageRawClaimStatus: "UNKNOWN",
      forwardStatusText: "自然前向晋级证据未核验",
      forwardMaturityText: "收益期 --/-- · 实际调仓 --/--",
      maturityCueText: "自然前向成熟度未核验 · 收益期 --/-- · 实际调仓 --/--",
      forwardBoundaryText: "自然前向来源、语义重算与人工复核边界未核验",
      forwardSourceText: "自然前向审计指纹未核验",
      rawForwardStatus: "UNKNOWN",
      rawForwardIntegrityStatus: "UNKNOWN",
      rawForwardMaturityStatus: "UNKNOWN",
      rawForwardAuditStatus: "UNKNOWN",
      ...internalBacktestEvidenceCue("SOURCE"),
      sourceText: "冻结来源未核验",
      generatedAt: null,
      packHash: null,
      evidenceHash: null,
      rawPackSchema: "UNKNOWN",
      rawQualitySchema: "UNKNOWN",
      sourceMode: "UNKNOWN",
      rawPackStatus: "UNKNOWN",
      rawPromotionStatus: "UNKNOWN",
    });
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return empty;
    const quality = payload.return_quality;
    const forward = payload.forward_promotion;
    const summary = quality?.summary;
    const costAfter = quality?.cost_after;
    const baseline = costAfter?.baseline_model;
    const authorityKey = (value) => String(value || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "");
    const localizedAuthorityKey = (value) => String(value || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[\s_\-./\\:：]/g, "");
    const localizedAuthorityField = (value) => (
      /(?:授权|可下单|可交易|允许下单|允许交易|交易许可|执行许可|执行允许|模拟许可|实盘许可|自动下单)/
        .test(localizedAuthorityKey(value))
    );
    const falseFields = [
      "profitability_proven",
      "performance_claim_allowed",
      "parameter_selection_allowed",
      "automatic_paper_activation_allowed",
      "paper_authorized",
      "live_order_allowed",
    ];
    const authorityFields = new Set([
      ...falseFields,
      "armed",
      "automated_paper_order_allowed",
      "binding_authorized",
      "can_execute",
      "can_trade",
      "direction_signal_allowed",
      "execution_allowed",
      "live_ready",
      "live_trading_allowed",
      "live_trading_enabled",
      "mission_authorized",
      "order_allowed",
      "paper_activation_allowed",
      "paper_armed",
      "paper_order_allowed",
      "paper_ready",
      "performance_claim_proven",
      "role_assignment_allowed",
      "runtime_mutations_allowed",
      "selection_allowed",
      "trade_allowed",
    ].map(authorityKey));
    const authoritySafe = (value) => {
      if (Array.isArray(value)) return value.every(authoritySafe);
      if (!value || typeof value !== "object") return true;
      return Object.entries(value).every(([key, nested]) => (
        (
          (!authorityFields.has(authorityKey(key)) && !localizedAuthorityField(key))
          || nested === false
        ) && authoritySafe(nested)
      ));
    };
    const safeScope = (value) => value
      && typeof value === "object"
      && value.research_only === true
      && falseFields.every((field) => value[field] === false);
    const finiteOrNull = (value) => value === null
      || (typeof value === "number" && Number.isFinite(value));
    const nonnegativeIntegerOrNull = (value) => value === null
      || (Number.isInteger(value) && value >= 0);
    const stageNames = Object.freeze({
      VALIDATION: new Set(["VALIDATION", "DEVELOPMENT_VALIDATION"]),
      TEST: new Set(["TEST", "DEVELOPMENT_TEST"]),
    });
    const stageStatuses = new Set(["AVAILABLE", "PASS", "PARTIAL", "BLOCK", "UNKNOWN"]);
    const statisticalClaimStatuses = new Set(["PASS", "BLOCK", "PARTIAL", "NOT_DUE", "UNKNOWN"]);
    const benchmarkBasisText = Object.freeze({
      RECOMPUTED_FROM_STRATEGY_AND_BENCHMARK_RETURNS: "策略与基准收益已重算",
      STRATEGY_AND_BENCHMARK_RUNS: "策略与基准收益已重算",
      REPORTED_ONLY_NOT_USED: "仅保留上报超额，未用于复算",
      NOT_PROVIDED: "基准超额依据未提供",
      SOURCE_INTEGRITY_BLOCKED: "来源完整性阻断",
    });
    const summaryEvidenceStageText = Object.freeze({
      DEVELOPMENT_HISTORICAL: "开发期历史证据",
      HISTORICAL_RESEARCH: "历史研究证据",
      UNKNOWN: "时间证据未核验",
    });
    const stageContract = (stage, expectedStage) => {
      if (!stage || typeof stage !== "object" || Array.isArray(stage)) return false;
      const sample = stage.sample;
      const claim = stage.statistical_claim;
      const normalizedStage = normalizeStatus(stage.stage);
      const evidenceStatus = normalizeStatus(stage.evidence_status);
      const benchmarkStatus = normalizeStatus(stage.benchmark_excess_status);
      const benchmarkBasis = normalizeStatus(stage.benchmark_excess_basis);
      const claimStatus = normalizeStatus(claim?.status);
      const metricFields = [
        "strategy_return_pct",
        "benchmark_return_pct",
        "benchmark_excess_return_pct",
        "reported_benchmark_excess_return_pct",
        "strategy_max_drawdown_pct",
        "benchmark_max_drawdown_pct",
        "drawdown_improvement_pct",
      ];
      return stageNames[expectedStage]?.has(normalizedStage) === true
        && stageStatuses.has(evidenceStatus)
        && stageStatuses.has(benchmarkStatus)
        && Object.prototype.hasOwnProperty.call(benchmarkBasisText, benchmarkBasis)
        && sample
        && typeof sample === "object"
        && !Array.isArray(sample)
        && [
          "evaluated_rows",
          "order_event_count",
          "decision_event_count",
          "paired_return_observation_count",
        ].every((field) => nonnegativeIntegerOrNull(sample[field]))
        && claim
        && typeof claim === "object"
        && !Array.isArray(claim)
        && statisticalClaimStatuses.has(claimStatus)
        && [
          "observed_strategy_compound_return_pct",
          "observed_benchmark_compound_return_pct",
          "observed_compound_excess_return_pct",
        ].every((field) => finiteOrNull(claim[field]))
        && Array.isArray(claim.blockers)
        && claim.blockers.every((item) => typeof item === "string")
        && metricFields.every((field) => finiteOrNull(stage[field]));
    };
    const stages = quality?.stages;
    const stageContractValid = stages
      && typeof stages === "object"
      && !Array.isArray(stages)
      && stageContract(stages.validation, "VALIDATION")
      && stageContract(stages.test, "TEST");
    const stageSummary = (stage, label, expectedStage) => {
      const value = stageContract(stage, expectedStage) ? stage : {};
      const rawStatus = normalizeStatus(value.evidence_status);
      const rawBenchmarkStatus = normalizeStatus(value.benchmark_excess_status);
      const rawClaimStatus = normalizeStatus(value.statistical_claim?.status);
      const statusText = {
        AVAILABLE: "阶段证据齐全",
        PASS: "阶段已核对",
        BLOCK: "阶段有阻断",
        PARTIAL: "阶段不完整",
        UNKNOWN: "阶段未核验",
      }[rawStatus] || "阶段未核验";
      const benchmarkText = {
        AVAILABLE: "基准超额已重算",
        PASS: "基准超额已核对",
        BLOCK: "基准超额有阻断",
        PARTIAL: "基准超额不完整",
        UNKNOWN: "基准超额未核验",
      }[rawBenchmarkStatus] || "基准超额未核验";
      const claimText = {
        PASS: "统计口径已核对",
        BLOCK: "统计口径有阻断",
        PARTIAL: "统计口径不完整",
        NOT_DUE: "统计口径尚未到期",
        UNKNOWN: "统计口径未核验",
      }[rawClaimStatus] || "统计口径未核验";
      const sampleValue = value.sample?.paired_return_observation_count
        ?? value.sample?.evaluated_rows;
      const sampleText = nonnegativeIntegerOrNull(sampleValue) && sampleValue !== null
        ? String(sampleValue)
        : "--";
      const basis = benchmarkBasisText[normalizeStatus(value.benchmark_excess_basis)]
        || "基准超额依据未核验";
      return {
        text: `${label}：${statusText} · 样本 ${sampleText} · ${benchmarkText} · ${claimText}`,
        detailText: `${label}证据 · ${basis}`,
        rawStatus,
        rawBenchmarkStatus,
        rawClaimStatus,
        samplePresent: sampleText !== "--",
      };
    };
    const validationStage = stageSummary(stages?.validation, "验证段", "VALIDATION");
    const testStage = stageSummary(stages?.test, "测试段", "TEST");
    const summaryFields = [
      "strategy_return_pct",
      "benchmark_return_pct",
      "benchmark_excess_return_pct",
      "cost_after_return_pct",
      "worst_stress_return_pct",
      "max_drawdown_pct",
      "sample_size",
    ];
    const baselineFields = ["fee_rate", "slippage_bps", "test_return_after_configured_costs_pct"];
    const numericContract = summary
      && typeof summary === "object"
      && summaryFields.every((field) => finiteOrNull(summary[field]))
      && baseline
      && typeof baseline === "object"
      && baselineFields.every((field) => finiteOrNull(baseline[field]))
      && [null, true, false].includes(baseline.configured_costs_declared_in_test_run);
    const strategyReturn = summary?.strategy_return_pct;
    const benchmarkReturn = summary?.benchmark_return_pct;
    const excessReturn = summary?.benchmark_excess_return_pct;
    const pairedReturnsPresent = typeof strategyReturn === "number" && typeof benchmarkReturn === "number";
    const recomputedExcessConsistent = pairedReturnsPresent
      ? typeof excessReturn === "number"
        && Math.abs((strategyReturn - benchmarkReturn) - excessReturn) <= 0.00011
      : excessReturn === null;
    const sampleContract = summary?.sample_size === null
      || (Number.isInteger(summary?.sample_size) && summary.sample_size >= 0);
    const hash256 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
    const provenanceContract = Number.isSafeInteger(payload.generated_at)
      && payload.generated_at > 0
      && hash256(payload.candidate_hash)
      && hash256(payload.pack_hash)
      && hash256(payload.evidence_hash);
    const packSchema = String(payload.pack_schema_version || "");
    const packQualityCoupling = Object.prototype.hasOwnProperty.call(
      INTERNAL_BACKTEST_QUALITY_COUPLINGS,
      packSchema,
    )
      ? INTERNAL_BACKTEST_QUALITY_COUPLINGS[packSchema]
      : null;
    const packStatus = normalizeStatus(payload.pack_status);
    const promotionStatus = normalizeStatus(payload.promotion_status);
    const forwardStatus = normalizeStatus(forward?.status);
    const forwardIntegrityStatus = normalizeStatus(forward?.source_integrity_status);
    const forwardMaturityStatus = normalizeStatus(forward?.maturity?.status);
    const forwardAuditStatus = normalizeStatus(forward?.audit?.status);
    const forwardPromotionBlockers = Array.isArray(forward?.promotion_blockers)
      ? forward.promotion_blockers
      : [];
    const stringList = (value) => Array.isArray(value)
      && value.every((item) => typeof item === "string")
      && new Set(value).size === value.length;
    const forwardCountFields = [
      "forward_outcomes",
      "required_forward_outcomes",
      "remaining_forward_outcomes",
      "executed_rebalances",
      "required_executed_rebalances",
      "remaining_executed_rebalances",
    ];
    const forwardCountsContract = forward?.maturity
      && typeof forward.maturity === "object"
      && !Array.isArray(forward.maturity)
      && forwardCountFields.every((field) => nonnegativeIntegerOrNull(forward.maturity[field]));
    const forwardCountsComplete = forwardCountsContract
      && forwardCountFields.every((field) => Number.isSafeInteger(forward.maturity[field]));
    const forwardRequiredThresholdsValid = forwardCountsComplete
      && forward.maturity.required_forward_outcomes > 0
      && forward.maturity.required_executed_rebalances > 0;
    const forwardCausalCountsValid = forwardCountsComplete
      && forward.maturity.executed_rebalances <= forward.maturity.forward_outcomes;
    const expectedForwardDue = forwardRequiredThresholdsValid && forwardCausalCountsValid
      ? forward.maturity.forward_outcomes >= forward.maturity.required_forward_outcomes
        && forward.maturity.executed_rebalances >= forward.maturity.required_executed_rebalances
      : null;
    const forwardRemainingCountsMatch = forwardCountsComplete
      && forward.maturity.remaining_forward_outcomes === Math.max(
        forward.maturity.required_forward_outcomes - forward.maturity.forward_outcomes,
        0,
      )
      && forward.maturity.remaining_executed_rebalances === Math.max(
        forward.maturity.required_executed_rebalances - forward.maturity.executed_rebalances,
        0,
      );
    const isSingleLookV2 = packQualityCoupling?.forwardSchema
      === "portfolio-backtest-forward-promotion-summary-v2";
    const safeNonnegativeInteger = (value) => Number.isSafeInteger(value) && value >= 0;
    const validIsoDay = (value) => {
      if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
      const stamp = Date.parse(`${value}T00:00:00Z`);
      return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0, 10) === value;
    };
    const decisionV2 = forward?.decision;
    const prefixV2 = forward?.frozen_prefix;
    const auditV2 = forward?.audit;
    const stageV2 = auditV2?.stage;
    const riskV2 = auditV2?.risk_acceptance;
    const tailV2 = forward?.tail_observation;
    const scopeV2 = forward?.validation_scope;
    const firstDueIndexV2 = forward?.maturity?.first_due_settlement_index;
    const firstDueDateV2 = forward?.maturity?.first_due_settlement_date;
    const firstDueHashV2 = forward?.maturity?.first_due_settlement_hash;
    const prefixCountFieldsV2 = [
      "settlement_count", "outcome_period_count", "rebalance_execution_count",
    ];
    const tailCountFieldsV2 = [
      "full_settlement_count", "frozen_prefix_settlement_count", "later_settlement_count",
    ];
    const snapshotV4ShapeContract = payload.schema_version
      !== "portfolio-backtest-return-quality-snapshot-v4"
      || (
        exactObjectKeys(payload, INTERNAL_BACKTEST_SNAPSHOT_V4_KEYS)
        && stringList(payload.blockers)
        && payload.blockers.length === 0
        && payload.read_only === true
      );
    const forwardV2ExactShape = isSingleLookV2
      && forward?.schema_version === "portfolio-backtest-forward-promotion-summary-v2"
      && exactObjectKeys(forward, FORWARD_PROMOTION_V2_KEYS)
      && exactObjectKeys(decisionV2, FORWARD_PROMOTION_V2_DECISION_KEYS)
      && exactObjectKeys(forward?.maturity, FORWARD_PROMOTION_V2_MATURITY_KEYS)
      && exactObjectKeys(prefixV2, FORWARD_PROMOTION_V2_PREFIX_KEYS)
      && exactObjectKeys(auditV2, FORWARD_PROMOTION_V2_AUDIT_KEYS)
      && exactObjectKeys(stageV2, FORWARD_PROMOTION_V2_STAGE_KEYS)
      && exactObjectKeys(riskV2, FORWARD_PROMOTION_V2_RISK_KEYS)
      && exactObjectKeys(tailV2, FORWARD_PROMOTION_V2_TAIL_KEYS)
      && exactObjectKeys(scopeV2, FORWARD_PROMOTION_V2_SCOPE_KEYS);
    const forwardV2CountsSafe = forwardV2ExactShape
      && forwardCountFields.every((field) => safeNonnegativeInteger(forward.maturity[field]))
      && prefixCountFieldsV2.every((field) => safeNonnegativeInteger(prefixV2[field]))
      && tailCountFieldsV2.every((field) => safeNonnegativeInteger(tailV2[field]));
    const forwardV2TailContract = forwardV2CountsSafe
      && tailV2.full_settlement_count === forward.maturity.forward_outcomes + 1
      && tailV2.frozen_prefix_settlement_count === prefixV2.settlement_count
      && tailV2.later_settlement_count
        === tailV2.full_settlement_count - tailV2.frozen_prefix_settlement_count
      && tailV2.full_settlement_count >= tailV2.frozen_prefix_settlement_count
      && hash256(tailV2.full_series_hash)
      && tailV2.full_series_hash === auditV2.full_series_hash
      && hash256(tailV2.frozen_decision_hash)
      && tailV2.frozen_decision_hash === decisionV2.decision_hash
      && tailV2.later_settlements_descriptive_only === true;
    const forwardV2ScopeContract = forwardV2ExactShape
      && scopeV2.pack_validates_upstream_single_look_semantic_receipt === true
      && scopeV2.settlement_database_reloaded_by_pack === false
      && scopeV2.settlement_chain_independently_replayed_by_pack === false
      && scopeV2.full_forward_rows_hash_bound === true
      && scopeV2.first_joint_maturity_prefix_hash_bound === true
      && scopeV2.decision_stage_and_risk_hashes_bound === true
      && scopeV2.later_settlements_descriptive_only === true;
    const forwardV2CommonContract = forwardV2ExactShape
      && snapshotV4ShapeContract
      && ["PASS", "BLOCK"].includes(forwardIntegrityStatus)
      && [
        "COLLECTING", "RESEARCH_REVIEW_READY", "RESEARCH_REVIEW_BLOCKED", "BLOCK",
      ].includes(forwardStatus)
      && forwardCountsComplete
      && forwardRequiredThresholdsValid
      && forwardCausalCountsValid
      && forwardRemainingCountsMatch
      && forward.maturity.both_thresholds_required === true
      && forwardV2CountsSafe
      && forwardV2TailContract
      && forwardV2ScopeContract
      && decisionV2.policy === "FIRST_JOINT_MATURITY_SINGLE_LOOK"
      && hash256(decisionV2.decision_hash)
      && decisionV2.later_settlements_used === false
      && auditV2.verification_status === "PASS"
      && auditV2.semantic_recomputed === true
      && typeof auditV2.conclusion === "string"
      && hash256(auditV2.audit_hash)
      && hash256(auditV2.full_series_hash)
      && hash256(riskV2.risk_hash)
      && ["PASS", "BLOCK"].includes(
        normalizeStatus(forward.historical_contract_claim_status),
      )
      && typeof riskV2.required_max_drawdown_below_pct === "number"
      && Number.isFinite(riskV2.required_max_drawdown_below_pct)
      && riskV2.required_max_drawdown_below_pct > 0
      && stringList(forward.blockers)
      && stringList(forward.promotion_blockers)
      && forward.manual_review_required === true
      && safeScope(forward)
      && authoritySafe(forward);
    const forwardV2NotDueContract = forwardV2CommonContract
      && forwardMaturityStatus === "NOT_DUE"
      && decisionV2.status === "NOT_DUE"
      && decisionV2.decision_status === "NOT_DUE"
      && decisionV2.research_action === "COLLECT_MORE"
      && prefixV2.status === "NOT_DUE"
      && prefixCountFieldsV2.every((field) => prefixV2[field] === 0)
      && prefixV2.decision_series_hash === ""
      && firstDueIndexV2 === null
      && firstDueDateV2 === null
      && firstDueHashV2 === null
      && stageV2.status === "NOT_DUE"
      && stageV2.stage_hash === null
      && riskV2.status === "NOT_DUE"
      && riskV2.prefix_max_drawdown_pct === null;
    const forwardV2DuePrefixContract = forwardV2CommonContract
      && forwardMaturityStatus === "DUE"
      && decisionV2.status === "FROZEN"
      && prefixV2.status === "DUE"
      && safeNonnegativeInteger(firstDueIndexV2)
      && validIsoDay(firstDueDateV2)
      && hash256(firstDueHashV2)
      && prefixV2.settlement_count === firstDueIndexV2 + 1
      && prefixV2.outcome_period_count === Math.max(prefixV2.settlement_count - 1, 0)
      && prefixV2.rebalance_execution_count <= prefixV2.outcome_period_count
      && prefixV2.outcome_period_count >= forward.maturity.required_forward_outcomes
      && prefixV2.rebalance_execution_count >= forward.maturity.required_executed_rebalances
      && prefixV2.outcome_period_count <= forward.maturity.forward_outcomes
      && prefixV2.rebalance_execution_count <= forward.maturity.executed_rebalances
      && hash256(prefixV2.decision_series_hash)
      && ["PASS", "BLOCK"].includes(stageV2.status)
      && hash256(stageV2.stage_hash)
      && ["PASS", "BLOCK"].includes(riskV2.status)
      && typeof riskV2.prefix_max_drawdown_pct === "number"
      && Number.isFinite(riskV2.prefix_max_drawdown_pct)
      && riskV2.prefix_max_drawdown_pct >= 0
      && (
        (riskV2.status === "PASS"
          && riskV2.prefix_max_drawdown_pct < riskV2.required_max_drawdown_below_pct)
        || (riskV2.status === "BLOCK"
          && riskV2.prefix_max_drawdown_pct >= riskV2.required_max_drawdown_below_pct)
      );
    const forwardStateContract = forwardIntegrityStatus === "PASS" && forwardCountsComplete
      ? (
        forwardRequiredThresholdsValid
        && forwardCausalCountsValid
        && forwardMaturityStatus === (expectedForwardDue ? "DUE" : "NOT_DUE")
        && forwardRemainingCountsMatch
        && (
          (
            forwardStatus === "COLLECTING"
            && expectedForwardDue === false
            && forwardAuditStatus === "NOT_DUE"
            && normalizeStatus(forward.readiness_status) === "COLLECTING"
            && normalizeStatus(forward.readiness_promotion_status) === "BLOCK"
            && promotionStatus === "BLOCK"
            && forwardPromotionBlockers.includes("natural_forward_statistical_evidence_not_mature")
          )
          || (
            forwardStatus === "RESEARCH_REVIEW_READY"
            && expectedForwardDue === true
            && forwardAuditStatus === "PASS"
            && normalizeStatus(forward.readiness_status) === "RESEARCH_REVIEW_READY"
            && normalizeStatus(forward.readiness_promotion_status) === "REVIEW_REQUIRED"
            && (
              (
                packStatus === "INTERNAL_BACKTEST_EVIDENCE_READY"
                && promotionStatus === "REVIEW_REQUIRED"
                && forwardPromotionBlockers.length === 0
              )
              || (
                packStatus === "INTERNAL_BACKTEST_BLOCKED"
                && promotionStatus === "BLOCK"
                && forwardPromotionBlockers.includes("internal_backtest_evidence_ready")
              )
            )
          )
          || (
            forwardStatus === "RESEARCH_REVIEW_BLOCKED"
            && expectedForwardDue === true
            && forwardAuditStatus === "BLOCK"
            && normalizeStatus(forward.readiness_status) === "RESEARCH_REVIEW_BLOCKED"
            && normalizeStatus(forward.readiness_promotion_status) === "BLOCK"
            && promotionStatus === "BLOCK"
            && forwardPromotionBlockers.includes("natural_forward_statistical_evidence_not_passed")
          )
        )
      )
      : (
        forwardIntegrityStatus === "BLOCK"
        && forwardStatus === "BLOCK"
        && promotionStatus === "BLOCK"
        && packStatus === "INTERNAL_BACKTEST_BLOCKED"
      );
    const forwardV2PassDecision = forwardV2DuePrefixContract
      && stageV2.status === "PASS"
      && riskV2.status === "PASS"
      && decisionV2.decision_status === "PASS"
      && decisionV2.research_action === "REVIEW_REQUIRED"
      && forwardStatus === "RESEARCH_REVIEW_READY"
      && forwardAuditStatus === "PASS"
      && normalizeStatus(forward.readiness_status) === "RESEARCH_REVIEW_READY"
      && normalizeStatus(forward.readiness_promotion_status) === "REVIEW_REQUIRED"
      && (
        (
          packStatus === "INTERNAL_BACKTEST_EVIDENCE_READY"
          && promotionStatus === "REVIEW_REQUIRED"
          && forwardPromotionBlockers.length === 0
        )
        || (
          packStatus === "INTERNAL_BACKTEST_BLOCKED"
          && promotionStatus === "BLOCK"
          && forwardPromotionBlockers.includes("internal_backtest_evidence_ready")
        )
      );
    const forwardV2BlockedDecision = forwardV2DuePrefixContract
      && (stageV2.status === "BLOCK" || riskV2.status === "BLOCK")
      && decisionV2.decision_status === "BLOCK"
      && decisionV2.research_action === "STOP_RESEARCH"
      && forwardStatus === "RESEARCH_REVIEW_BLOCKED"
      && forwardAuditStatus === "BLOCK"
      && normalizeStatus(forward.readiness_status) === "RESEARCH_REVIEW_BLOCKED"
      && normalizeStatus(forward.readiness_promotion_status) === "BLOCK"
      && promotionStatus === "BLOCK"
      && forwardPromotionBlockers.includes("natural_forward_single_look_decision_blocked");
    const forwardV2CollectingDecision = forwardV2NotDueContract
      && decisionV2.decision_status === "NOT_DUE"
      && forwardStatus === "COLLECTING"
      && forwardAuditStatus === "NOT_DUE"
      && normalizeStatus(forward.readiness_status) === "COLLECTING"
      && normalizeStatus(forward.readiness_promotion_status) === "BLOCK"
      && promotionStatus === "BLOCK"
      && forwardPromotionBlockers.includes("natural_forward_single_look_not_mature");
    const forwardV2StateContract = forwardIntegrityStatus === "PASS"
      && (forwardV2CollectingDecision || forwardV2PassDecision || forwardV2BlockedDecision);
    const forwardBoundContract = isSingleLookV2
      ? forwardV2StateContract
      : packQualityCoupling?.forwardSchema
      && forward
      && typeof forward === "object"
      && !Array.isArray(forward)
      && forward.schema_version === packQualityCoupling.forwardSchema
      && ["PASS", "BLOCK"].includes(forwardIntegrityStatus)
      && [
        "COLLECTING",
        "RESEARCH_REVIEW_READY",
        "RESEARCH_REVIEW_BLOCKED",
        "BLOCK",
      ].includes(forwardStatus)
      && forwardCountsContract
      && ["DUE", "NOT_DUE", "UNKNOWN"].includes(forwardMaturityStatus)
      && forward.maturity.both_thresholds_required === true
      && forward.audit
      && typeof forward.audit === "object"
      && !Array.isArray(forward.audit)
      && ["PASS", "BLOCK", "NOT_DUE", "UNKNOWN"].includes(forwardAuditStatus)
      && typeof forward.audit.conclusion === "string"
      && typeof forward.audit.verification_status === "string"
      && typeof forward.audit.semantic_recomputed === "boolean"
      && (forward.audit.audit_hash === null || hash256(forward.audit.audit_hash))
      && (forward.audit.series_hash === null || hash256(forward.audit.series_hash))
      && ["PASS", "BLOCK", "UNKNOWN"].includes(
        normalizeStatus(forward.historical_contract_claim_status),
      )
      && stringList(forward.blockers)
      && stringList(forward.promotion_blockers)
      && forward.validation_scope
      && typeof forward.validation_scope === "object"
      && forward.validation_scope.pack_validates_upstream_semantic_receipt === true
      && forward.validation_scope.settlement_database_reloaded_by_pack === false
      && forward.validation_scope.settlement_chain_independently_replayed_by_pack === false
      && forward.validation_scope.full_forward_rows_hash_bound === true
      && forward.manual_review_required === true
      && safeScope(forward)
      && authoritySafe(forward)
      && (
        forwardIntegrityStatus !== "PASS"
        || (
          forward.audit.verification_status === "PASS"
          && forward.audit.semantic_recomputed === true
          && hash256(forward.audit.audit_hash)
          && hash256(forward.audit.series_hash)
          && ["PASS", "BLOCK"].includes(
            normalizeStatus(forward.historical_contract_claim_status),
          )
        )
      )
      && forwardStateContract;
    const qualitySchema = String(quality?.schema_version || "");
    const versionCoupling = packQualityCoupling?.availability === "AVAILABLE"
      && qualitySchema === packQualityCoupling.qualitySchema
      && forwardBoundContract;
    const qualityState = normalizeStatus(quality?.status);
    const summaryEvidenceStage = normalizeStatus(summary?.evidence_stage);
    const summaryEvidenceStageValid = Object.prototype.hasOwnProperty.call(
      summaryEvidenceStageText,
      summaryEvidenceStage,
    );
    const stageCoverageValid = qualityState !== "AVAILABLE"
      || [validationStage, testStage].every((stage) => (
        ["AVAILABLE", "PASS", "PARTIAL", "BLOCK"].includes(stage.rawStatus)
        && ["AVAILABLE", "PASS", "PARTIAL", "BLOCK"].includes(stage.rawBenchmarkStatus)
        && ["PASS", "PARTIAL", "BLOCK"].includes(stage.rawClaimStatus)
        && stage.samplePresent
      ));
    const objectRecord = (value) => value
      && typeof value === "object"
      && !Array.isArray(value);
    const explicitScopeViolation = (value) => objectRecord(value) && (
      (Object.prototype.hasOwnProperty.call(value, "research_only")
        && value.research_only !== true)
      || falseFields.some((field) => (
        Object.prototype.hasOwnProperty.call(value, field) && value[field] !== false
      ))
    );
    const explicitSafetyViolation = !authoritySafe(payload)
      || [payload, quality, forward].some(explicitScopeViolation);
    const sourceConnectionValid = payload.ok === true
      && normalizeStatus(payload.status) === "AVAILABLE"
      && normalizeStatus(payload.source_verification_status) === "PASS"
      && objectRecord(quality)
      && provenanceContract;
    const expectedSnapshotSchema = packQualityCoupling?.snapshotSchema || "";
    const packQualityVersionValid = payload.schema_version === expectedSnapshotSchema
      && snapshotV4ShapeContract
      && packQualityCoupling?.availability === "AVAILABLE"
      && qualitySchema === packQualityCoupling.qualitySchema;
    const packStateContract = [
      "INTERNAL_BACKTEST_EVIDENCE_READY",
      "INTERNAL_BACKTEST_BLOCKED",
    ].includes(packStatus)
      && ["BLOCK", "REVIEW_REQUIRED"].includes(promotionStatus);
    const qualityContract = quality?.interpretation
        === "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY"
      && ["AVAILABLE", "PARTIAL", "BLOCK"].includes(qualityState)
      && summaryEvidenceStageValid;
    const trusted = payload.ok === true
      && payload.schema_version === expectedSnapshotSchema
      && snapshotV4ShapeContract
      && normalizeStatus(payload.status) === "AVAILABLE"
      && normalizeStatus(payload.source_verification_status) === "PASS"
      && quality?.interpretation === "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY"
      && safeScope(payload)
      && safeScope(quality)
      && authoritySafe(payload)
      && numericContract
      && sampleContract
      && stageContractValid
      && stageCoverageValid
      && summaryEvidenceStageValid
      && recomputedExcessConsistent
      && provenanceContract
      && ["INTERNAL_BACKTEST_EVIDENCE_READY", "INTERNAL_BACKTEST_BLOCKED"].includes(packStatus)
      && ["BLOCK", "REVIEW_REQUIRED"].includes(promotionStatus)
      && versionCoupling
      && ["AVAILABLE", "PARTIAL", "BLOCK"].includes(qualityState);
    if (!trusted) {
      let evidenceCue = internalBacktestEvidenceCue("UNKNOWN");
      if (explicitSafetyViolation) {
        evidenceCue = internalBacktestEvidenceCue("SAFETY_BOUNDARY");
      } else if (!sourceConnectionValid) {
        evidenceCue = internalBacktestEvidenceCue("SOURCE");
      } else if (!packQualityVersionValid) {
        evidenceCue = internalBacktestEvidenceCue("VERSION_BINDING");
      } else if (!safeScope(payload) || !safeScope(quality)) {
        evidenceCue = internalBacktestEvidenceCue("SAFETY_BOUNDARY");
      } else if (!stageContractValid || !stageCoverageValid || !qualityContract) {
        evidenceCue = internalBacktestEvidenceCue("STAGE_EVIDENCE");
      } else if (!numericContract || !sampleContract || !recomputedExcessConsistent) {
        evidenceCue = internalBacktestEvidenceCue("VALUE_CONSISTENCY");
      } else if (!objectRecord(forward)) {
        evidenceCue = internalBacktestEvidenceCue("FORWARD_EVIDENCE");
      } else if (forward.schema_version !== packQualityCoupling.forwardSchema) {
        evidenceCue = internalBacktestEvidenceCue("VERSION_BINDING");
      } else if (!safeScope(forward) || !authoritySafe(forward)) {
        evidenceCue = internalBacktestEvidenceCue("SAFETY_BOUNDARY");
      } else if (!forwardBoundContract || !packStateContract) {
        evidenceCue = internalBacktestEvidenceCue("FORWARD_EVIDENCE");
      }
      return Object.freeze({ ...empty, ...evidenceCue });
    }

    const pct = (value) => typeof value === "number" && Number.isFinite(value)
      ? `${value.toFixed(2)}%`
      : "--";
    const packText = packStatus === "INTERNAL_BACKTEST_EVIDENCE_READY"
      ? "包内证据结构完整"
      : packStatus === "INTERNAL_BACKTEST_BLOCKED"
      ? "包内研究阻断"
      : "包内状态未核验";
    const promotionText = promotionStatus === "REVIEW_REQUIRED"
      ? "需人工研究复核"
      : promotionStatus === "BLOCK"
      ? "研究晋级阻断"
      : "晋级状态未核验";
    const compactBundleSource = packQualityCoupling.sourceMode === "COMPACT_BUNDLE_RECOMPUTED";
    const sourceTrustText = compactBundleSource
      ? "紧凑 bundle 来源与合同已复算核验"
      : "来源与合同已核验";
    // Source trust and research outcome are deliberately separate. A verified
    // negative result is still trustworthy evidence, never a positive signal.
    const statusText = `${sourceTrustText} · 仅作历史描述 · 非盈利证明`;
    const costBinding = baseline.configured_costs_declared_in_test_run === true
      ? "成本口径已绑定"
      : baseline.configured_costs_declared_in_test_run === false
      ? "成本口径不匹配"
      : "成本绑定未核验";
    const sample = Number.isInteger(summary.sample_size) && summary.sample_size >= 0
      ? String(summary.sample_size)
      : "--";
    const stage = summaryEvidenceStageText[summaryEvidenceStage]
      || "时间证据未核验";
    const failureConditions = quality.failure_conditions && typeof quality.failure_conditions === "object"
      ? quality.failure_conditions
      : {};
    const evidenceCue = verifiedInternalBacktestEvidenceCue(
      qualityState,
      promotionStatus,
      failureConditions,
    );
    const legacyForward = packSchema === "portfolio-internal-backtest-pack-v2";
    const forwardStatusText = isSingleLookV2
      ? ({
        COLLECTING: "首次联合门槛尚未到期 · 继续自然收集，不作通过结论",
        RESEARCH_REVIEW_READY: packStatus === "INTERNAL_BACKTEST_BLOCKED"
          ? "首次到期决策已冻结 · 其他包内证据仍阻断"
          : "首次到期决策已冻结 · 仅进入人工研究复核",
        RESEARCH_REVIEW_BLOCKED: "首次到期决策已冻结为停止晋级 · 后续仅保留描述",
        BLOCK: "首次到期决策来源不可核验 · 不使用判定",
      }[forwardStatus] || "首次到期决策未核验")
      : legacyForward
      ? "旧版冻结包未封存版本化自然前向摘要"
      : forwardIntegrityStatus === "BLOCK"
        ? "自然前向来源完整性阻断"
        : ({
          COLLECTING: "自然前向仍在收集 · 未到统计双门槛",
          RESEARCH_REVIEW_READY: packStatus === "INTERNAL_BACKTEST_BLOCKED"
            ? "自然前向统计已到期 · 其他包内证据阻断"
            : "自然前向统计已到期 · 等待人工研究复核",
          RESEARCH_REVIEW_BLOCKED: "自然前向形成有效负结果 · 研究晋级阻断",
        }[forwardStatus] || "自然前向晋级证据未核验");
    const forwardMaturityText = isSingleLookV2
      ? forwardCountsComplete
        ? `收益期 ${forward.maturity.forward_outcomes}/${forward.maturity.required_forward_outcomes}`
          + ` · 实际调仓 ${forward.maturity.executed_rebalances}/${forward.maturity.required_executed_rebalances}`
          + (forwardMaturityStatus === "DUE"
            ? ` · 首次前缀 ${prefixV2.settlement_count} 个结算 · 后续 ${tailV2.later_settlement_count} 个仅描述`
            : " · 首次到期决策尚未形成")
        : "收益期与实际调仓计数未核验"
      : legacyForward
      ? "收益期与实际调仓门槛未由旧版包封存"
      : forwardCountsComplete
        ? `收益期 ${forward.maturity.forward_outcomes}/${forward.maturity.required_forward_outcomes} · 实际调仓 ${forward.maturity.executed_rebalances}/${forward.maturity.required_executed_rebalances} · 双门槛同时要求`
        : "收益期与实际调仓计数未核验";
    const forwardBoundaryText = isSingleLookV2
      ? "Pack 仅核验上游单次决策收据、首次前缀与风险绑定 · 未重载结算数据库、未独立重放结算链 · 后续样本仅描述"
      : legacyForward
      ? "旧版包不追认自然前向结论 · 需 v3/v4 版本化证据链"
      : "Pack 仅校验上游语义重算收据与完整序列 Hash · 未重载数据库、未独立重放结算链 · 始终人工复核";
    const forwardSourceText = isSingleLookV2
      ? `决策 ${decisionV2.decision_hash.slice(0, 8)} · 风险 ${riskV2.risk_hash.slice(0, 8)} · 全序列 ${tailV2.full_series_hash.slice(0, 8)}`
      : legacyForward
      ? "自然前向审计指纹：旧版未封存"
      : forward?.audit?.audit_hash && forward?.audit?.series_hash
        ? `前向审计 ${forward.audit.audit_hash.slice(0, 8)} · 序列 ${forward.audit.series_hash.slice(0, 8)}`
        : "自然前向审计指纹未形成";
    return Object.freeze({
      verified: true,
      connectionStatus: "VERIFIED",
      qualityState,
      statusText,
      detailText: `${packText} · ${promotionText} · 模拟未授权 · 实盘永久硬锁`,
      returnsText: `策略 ${pct(strategyReturn)} · 基准 ${pct(benchmarkReturn)} · 重算超额 ${pct(excessReturn)}`,
      costText: `${costBinding} · 成本后 ${pct(summary.cost_after_return_pct)}`,
      riskText: `压力最差 ${pct(summary.worst_stress_return_pct)} · 最大回撤 ${pct(summary.max_drawdown_pct)}`,
      sampleText: `样本 ${sample} · ${stage}`,
      validationStageText: validationStage.text,
      validationStageDetailText: validationStage.detailText,
      testStageText: testStage.text,
      testStageDetailText: testStage.detailText,
      validationStageRawStatus: validationStage.rawStatus,
      validationStageRawBenchmarkStatus: validationStage.rawBenchmarkStatus,
      validationStageRawClaimStatus: validationStage.rawClaimStatus,
      testStageRawStatus: testStage.rawStatus,
      testStageRawBenchmarkStatus: testStage.rawBenchmarkStatus,
      testStageRawClaimStatus: testStage.rawClaimStatus,
      forwardStatusText,
      forwardMaturityText,
      maturityCueText: `${forwardStatusText} · ${forwardMaturityText}`,
      forwardBoundaryText,
      forwardSourceText,
      rawForwardStatus: legacyForward ? "LEGACY_NOT_BOUND" : forwardStatus,
      rawForwardIntegrityStatus: legacyForward ? "LEGACY_NOT_BOUND" : forwardIntegrityStatus,
      rawForwardMaturityStatus: legacyForward ? "LEGACY_NOT_BOUND" : forwardMaturityStatus,
      rawForwardAuditStatus: legacyForward ? "LEGACY_NOT_BOUND" : forwardAuditStatus,
      ...evidenceCue,
      sourceText: compactBundleSource
        ? `紧凑 bundle 来源已复算 · 包 ${payload.pack_hash.slice(0, 12)}…`
        : `冻结来源已核验 · 包 ${payload.pack_hash.slice(0, 12)}…`,
      generatedAt: payload.generated_at,
      packHash: payload.pack_hash,
      evidenceHash: payload.evidence_hash,
      rawPackSchema: packSchema,
      rawQualitySchema: qualitySchema,
      sourceMode: packQualityCoupling.sourceMode,
      rawPackStatus: packStatus,
      rawPromotionStatus: promotionStatus,
    });
  }

  const FORWARD_STATISTICAL_MATURITY_STATUSES = new Set([
    "NOT_DUE",
    "REVIEW_REQUIRED",
    "STOP_RESEARCH",
    "BLOCK",
  ]);
  const FORWARD_STATISTICAL_MATURITY_COPY = Object.freeze({
    NOT_DUE: "统计样本尚未到期 · 不作通过结论",
    REVIEW_REQUIRED: "统计证据已到期 · 等待人工研究复核",
    STOP_RESEARCH: "自然前向形成有效负结果 · 停止研究晋级",
    BLOCK: "统计来源或绑定不可核验 · 不使用成熟度结论",
    NOT_AVAILABLE: "旧版运行看板未携带统计成熟度 · 不作通过结论",
  });
  const FORWARD_SOURCE_BINDING_STATUSES = new Set([
    "FULL",
    "PREFIX",
    "CONTRADICTION",
    "NOT_AVAILABLE",
  ]);
  const FORWARD_SOURCE_BINDING_COPY = Object.freeze({
    FULL: "本地归档覆盖当前序列 · 仅证明本地跨工件一致",
    PREFIX: "本地归档仅覆盖历史前缀 · 当前尾段未覆盖",
    CONTRADICTION: "本地归档与当前序列矛盾 · 不使用成熟度结论",
    NOT_AVAILABLE: "未取得本地归档覆盖 · 不作来源覆盖结论",
  });
  const FORWARD_SOURCE_BINDING_SCOPE_TEXT = (
    "仅本地归档跨工件绑定 · 不证明外部真实性或盈利"
  );
  const FORWARD_SOURCE_BINDING_KEYS = Object.freeze([
    "schema_version",
    "status",
    "trust_scope",
    "current_observation_count",
    "anchored_observation_count",
    "current_settlement_count",
    "anchored_settlement_count",
    "external_authenticity_proven",
    "profitability_proven",
    "research_only",
    "observation_only",
    "simulation_only",
    "paper_authorized",
    "live_order_allowed",
  ]);
  const FORWARD_STATISTICAL_PROGRESS_KEYS = Object.freeze([
    "forward_outcomes",
    "required_forward_outcomes",
    "remaining_forward_outcomes",
    "settlements",
    "captured_observations",
    "executed_rebalances",
    "required_executed_rebalances",
    "remaining_executed_rebalances",
  ]);
  const FORWARD_STATISTICAL_MATURITY_V3_KEYS = Object.freeze([
    "schema_version", "status", "candidate_hash", "progress", "source_binding",
    "decision_policy", "decision_status", "research_action", "decision_hash", "stage_hash",
    "risk_acceptance_hash", "first_due_settlement_hash", "verification_scope", "research_only",
    "observation_only", "simulation_only", "profitability_proven", "paper_authorized",
    "live_order_allowed",
  ]);
  const FORWARD_DASHBOARD_V7_KEYS = Object.freeze([
    "schema_version", "status", "as_of_ms", "candidate_hash", "service", "observer", "data",
    "latest_completed_bar", "pending", "skipped", "next_check", "pause", "schedule",
    "latest_observation", "latest_observation_change", "recent_observer_jobs", "progress",
    "experiment_status", "blockers", "next_action", "permissions", "read_only",
    "observation_only", "simulation_only", "paper_authorized", "live_order_allowed",
    "live_trading_hard_block", "statistical_maturity",
  ]);
  const FORWARD_DASHBOARD_PERMISSION_KEYS = Object.freeze([
    "read_only", "observation_only", "simulation_only", "paper_authorized",
    "live_order_allowed", "live_trading_hard_block",
  ]);

  function canonicalAuthorityKey(value) {
    const normalized = String(value ?? "").normalize("NFKC").toLocaleLowerCase("und");
    return Array.from(normalized)
      .filter((character) => /[\p{L}\p{N}]/u.test(character))
      .join("");
  }

  const EXECUTION_AUTHORITY_FIELD_KEYS = new Set([
    "armed",
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "direction_signal_allowed",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "live_trading_allowed",
    "live_trading_enabled",
    "mission_authorized",
    "order_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_authorized",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "parameter_selection_authority",
    "performance_claim_allowed",
    "performance_claim_proven",
    "profitability_proven",
    "role_assignment_allowed",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
    "可下单",
    "已授权",
    "实盘授权",
  ].map(canonicalAuthorityKey));

  function executionAuthoritySafe(value) {
    if (Array.isArray(value)) return value.every(executionAuthoritySafe);
    if (!value || typeof value !== "object") return true;
    return Object.entries(value).every(([key, nested]) => (
      (!EXECUTION_AUTHORITY_FIELD_KEYS.has(canonicalAuthorityKey(key)) || nested === false)
      && executionAuthoritySafe(nested)
    ));
  }

  function exactObjectKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    return keys.length === expected.length && expected.every((key) => Object.hasOwn(value, key));
  }

  function unavailableForwardSourceBinding({ invalid = false } = {}) {
    const status = invalid ? "CONTRADICTION" : "NOT_AVAILABLE";
    return {
      valid: !invalid,
      available: false,
      status,
      statusText: FORWARD_SOURCE_BINDING_COPY[status],
      detailText: `${FORWARD_SOURCE_BINDING_SCOPE_TEXT} · 覆盖计数不可核验`,
      currentObservationCount: null,
      anchoredObservationCount: null,
      currentSettlementCount: null,
      anchoredSettlementCount: null,
    };
  }

  function forwardSourceBindingContract(sourceBinding) {
    if (!exactObjectKeys(sourceBinding, FORWARD_SOURCE_BINDING_KEYS)) {
      return unavailableForwardSourceBinding({ invalid: true });
    }
    const status = sourceBinding.status;
    const countKeys = [
      "current_observation_count",
      "anchored_observation_count",
      "current_settlement_count",
      "anchored_settlement_count",
    ];
    if (
      sourceBinding.schema_version !== "portfolio-forward-source-binding-v1"
      || !FORWARD_SOURCE_BINDING_STATUSES.has(status)
      || sourceBinding.trust_scope !== "LOCAL_ARCHIVE_CROSS_ARTIFACT_BINDING_ONLY"
      || !countKeys.every(
        (key) => Number.isSafeInteger(sourceBinding[key])
          && sourceBinding[key] >= 0
          && sourceBinding[key] <= 1024,
      )
      || sourceBinding.external_authenticity_proven !== false
      || sourceBinding.profitability_proven !== false
      || sourceBinding.research_only !== true
      || sourceBinding.observation_only !== true
      || sourceBinding.simulation_only !== true
      || sourceBinding.paper_authorized !== false
      || sourceBinding.live_order_allowed !== false
      || !executionAuthoritySafe(sourceBinding)
    ) return unavailableForwardSourceBinding({ invalid: true });

    const currentObservationCount = sourceBinding.current_observation_count;
    const anchoredObservationCount = sourceBinding.anchored_observation_count;
    const currentSettlementCount = sourceBinding.current_settlement_count;
    const anchoredSettlementCount = sourceBinding.anchored_settlement_count;
    const fullCountsValid = status !== "FULL" || (
      currentObservationCount > 0
      && currentObservationCount === anchoredObservationCount
      && currentSettlementCount === anchoredSettlementCount
      && currentObservationCount === currentSettlementCount
    );
    const prefixCountsValid = status !== "PREFIX" || (
      anchoredObservationCount > 0
      && anchoredObservationCount === anchoredSettlementCount
      && currentObservationCount === currentSettlementCount
      && currentObservationCount > anchoredObservationCount
    );
    if (!fullCountsValid || !prefixCountsValid) {
      return unavailableForwardSourceBinding({ invalid: true });
    }
    return {
      valid: true,
      available: ["FULL", "PREFIX"].includes(status),
      status,
      statusText: FORWARD_SOURCE_BINDING_COPY[status],
      detailText: `${FORWARD_SOURCE_BINDING_SCOPE_TEXT}`
        + ` · 当前/归档观察 ${currentObservationCount}/${anchoredObservationCount}`
        + ` · 当前/归档结算 ${currentSettlementCount}/${anchoredSettlementCount}`,
      currentObservationCount,
      anchoredObservationCount,
      currentSettlementCount,
      anchoredSettlementCount,
    };
  }

  function forwardStatisticalMaturityContract(maturity, candidateHash, dashboardSchema = "") {
    const baseTopLevelKeys = [
      "schema_version",
      "status",
      "candidate_hash",
      "progress",
      "verification_scope",
      "research_only",
      "observation_only",
      "simulation_only",
      "profitability_proven",
      "paper_authorized",
      "live_order_allowed",
    ];
    const v1 = maturity?.schema_version === "portfolio-forward-statistical-maturity-v1";
    const v2 = maturity?.schema_version === "portfolio-forward-statistical-maturity-v2";
    const v3 = maturity?.schema_version === "portfolio-forward-statistical-maturity-v3";
    const topLevelKeys = v3
      ? FORWARD_STATISTICAL_MATURITY_V3_KEYS
      : v2 ? [...baseTopLevelKeys, "source_binding"] : baseTopLevelKeys;
    if (!exactObjectKeys(maturity, topLevelKeys)) return { valid: false };
    const expectedVerificationScope = v3
      ? "PERSISTED_READINESS_V3_AND_FIRST_JOINT_MATURITY_DECISION_REBUILT_FROM_EMBEDDED_FULL_SERIES_NO_SETTLEMENT_REPLAY"
      : "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY";
    if (
      (!v1 && !v2 && !v3)
      || (dashboardSchema === "portfolio-forward-dashboard-v5" && !v1)
      || (dashboardSchema === "portfolio-forward-dashboard-v6" && !v2)
      || (dashboardSchema === "portfolio-forward-dashboard-v7" && !v3)
      || !FORWARD_STATISTICAL_MATURITY_STATUSES.has(maturity.status)
      || !/^[a-f0-9]{64}$/.test(String(candidateHash || ""))
      || maturity.candidate_hash !== candidateHash
      || maturity.verification_scope !== expectedVerificationScope
      || maturity.research_only !== true
      || maturity.observation_only !== true
      || maturity.simulation_only !== true
      || maturity.profitability_proven !== false
      || maturity.paper_authorized !== false
      || maturity.live_order_allowed !== false
      || !executionAuthoritySafe(maturity)
      || !exactObjectKeys(maturity.progress, FORWARD_STATISTICAL_PROGRESS_KEYS)
    ) return { valid: false };

    const sourceBinding = v2 || v3
      ? forwardSourceBindingContract(maturity.source_binding)
      : unavailableForwardSourceBinding();
    if (
      !sourceBinding.valid
      || (sourceBinding.status === "CONTRADICTION" && maturity.status !== "BLOCK")
    ) return { valid: false };

    const progress = maturity.progress;
    if (!FORWARD_STATISTICAL_PROGRESS_KEYS.every(
      (key) => Number.isSafeInteger(progress[key]) && progress[key] >= 0,
    )) return { valid: false };
    const emptySeriesProgress = progress.forward_outcomes === 0
      && progress.settlements === 0
      && progress.captured_observations === 0;
    if (
      (!emptySeriesProgress && (
        progress.settlements !== progress.forward_outcomes + 1
        || progress.captured_observations !== progress.settlements
      ))
      || progress.executed_rebalances > progress.forward_outcomes
    ) return { valid: false };
    if (maturity.status === "BLOCK") {
      if (!FORWARD_STATISTICAL_PROGRESS_KEYS.every((key) => progress[key] === 0)) {
        return { valid: false };
      }
    } else if (
      progress.required_forward_outcomes <= 0
      || progress.required_executed_rebalances <= 0
      || progress.remaining_forward_outcomes
        !== Math.max(progress.required_forward_outcomes - progress.forward_outcomes, 0)
      || progress.remaining_executed_rebalances
        !== Math.max(progress.required_executed_rebalances - progress.executed_rebalances, 0)
      || (
        maturity.status === "NOT_DUE"
        && progress.remaining_forward_outcomes === 0
        && progress.remaining_executed_rebalances === 0
      )
      || (
        ["REVIEW_REQUIRED", "STOP_RESEARCH"].includes(maturity.status)
        && (
          progress.remaining_forward_outcomes !== 0
          || progress.remaining_executed_rebalances !== 0
        )
      )
    ) return { valid: false };
    if (v3) {
      const hash256 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
      const emptyDecisionHashes = [
        maturity.decision_hash,
        maturity.stage_hash,
        maturity.risk_acceptance_hash,
        maturity.first_due_settlement_hash,
      ].every((value) => value === "");
      const dueDecisionHashes = [
        maturity.decision_hash,
        maturity.stage_hash,
        maturity.risk_acceptance_hash,
        maturity.first_due_settlement_hash,
      ].every(hash256);
      const decisionContract = maturity.decision_policy === "FIRST_JOINT_MATURITY_SINGLE_LOOK"
        && (
          (
            maturity.status === "BLOCK"
            && maturity.decision_status === "BLOCK"
            && maturity.research_action === "BLOCK"
            && emptyDecisionHashes
          )
          || (
            maturity.status === "NOT_DUE"
            && maturity.decision_status === "NOT_DUE"
            && maturity.research_action === "COLLECT_MORE"
            && hash256(maturity.decision_hash)
            && maturity.stage_hash === ""
            && hash256(maturity.risk_acceptance_hash)
            && maturity.first_due_settlement_hash === ""
          )
          || (
            maturity.status === "REVIEW_REQUIRED"
            && maturity.decision_status === "PASS"
            && maturity.research_action === "REVIEW_REQUIRED"
            && dueDecisionHashes
          )
          || (
            maturity.status === "STOP_RESEARCH"
            && maturity.decision_status === "BLOCK"
            && maturity.research_action === "STOP_RESEARCH"
            && dueDecisionHashes
          )
        );
      if (!decisionContract) return { valid: false };
    }
    return {
      valid: true,
      status: maturity.status,
      progress,
      sourceBinding,
    };
  }

  function forwardStatisticalMaturityPresentation(dashboard = {}) {
    const supportedDashboard = Boolean(
      dashboard
      && typeof dashboard === "object"
      && !Array.isArray(dashboard)
      && [
        "portfolio-forward-dashboard-v4",
        "portfolio-forward-dashboard-v5",
        "portfolio-forward-dashboard-v6",
        "portfolio-forward-dashboard-v7",
      ]
        .includes(dashboard.schema_version),
    );
    const dashboardV7Shape = dashboard?.schema_version !== "portfolio-forward-dashboard-v7"
      || (
        exactObjectKeys(dashboard, FORWARD_DASHBOARD_V7_KEYS)
        && exactObjectKeys(dashboard.permissions, FORWARD_DASHBOARD_PERMISSION_KEYS)
        && Number.isSafeInteger(dashboard.as_of_ms)
        && dashboard.as_of_ms > 0
        && Array.isArray(dashboard.blockers)
        && dashboard.blockers.every((item) => typeof item === "string")
        && new Set(dashboard.blockers).size === dashboard.blockers.length
        && dashboard.read_only === true
        && dashboard.observation_only === true
        && dashboard.simulation_only === true
        && dashboard.paper_authorized === false
        && dashboard.live_order_allowed === false
        && dashboard.live_trading_hard_block === true
        && dashboard.permissions.read_only === true
        && dashboard.permissions.observation_only === true
        && dashboard.permissions.simulation_only === true
        && dashboard.permissions.paper_authorized === false
        && dashboard.permissions.live_order_allowed === false
        && dashboard.permissions.live_trading_hard_block === true
      );
    const dashboardAuthoritySafe = supportedDashboard
      && dashboardV7Shape
      && executionAuthoritySafe(dashboard);
    const isLegacy = Boolean(
      supportedDashboard
      && dashboard.schema_version === "portfolio-forward-dashboard-v4"
      && !Object.hasOwn(dashboard, "statistical_maturity"),
    );
    if (isLegacy && dashboardAuthoritySafe) {
      return Object.freeze({
        valid: false,
        available: false,
        legacy: true,
        dashboardAuthoritySafe,
        rawStatus: "NOT_AVAILABLE",
        statusText: FORWARD_STATISTICAL_MATURITY_COPY.NOT_AVAILABLE,
        progressText: "结果 --/-- · 调仓 --/-- · 结算 -- · 观察 --",
        sourceBindingAvailable: false,
        sourceBindingRawStatus: "NOT_AVAILABLE",
        sourceBindingText: FORWARD_SOURCE_BINDING_COPY.NOT_AVAILABLE,
        sourceBindingDetailText: `${FORWARD_SOURCE_BINDING_SCOPE_TEXT} · 覆盖计数不可核验`,
      });
    }
    const currentDashboard = [
      "portfolio-forward-dashboard-v5",
      "portfolio-forward-dashboard-v6",
      "portfolio-forward-dashboard-v7",
    ].includes(dashboard?.schema_version);
    const contract = currentDashboard
      && dashboardAuthoritySafe
      ? forwardStatisticalMaturityContract(
        dashboard.statistical_maturity,
        dashboard.candidate_hash,
        dashboard.schema_version,
      )
      : { valid: false };
    if (!contract.valid) {
      return Object.freeze({
        valid: false,
        available: false,
        legacy: isLegacy,
        dashboardAuthoritySafe,
        rawStatus: "BLOCK",
        statusText: FORWARD_STATISTICAL_MATURITY_COPY.BLOCK,
        progressText: "结果 0/0 · 调仓 0/0 · 结算 0 · 观察 0",
        sourceBindingAvailable: false,
        sourceBindingRawStatus: "CONTRADICTION",
        sourceBindingText: FORWARD_SOURCE_BINDING_COPY.CONTRADICTION,
        sourceBindingDetailText: `${FORWARD_SOURCE_BINDING_SCOPE_TEXT} · 覆盖计数不可核验`,
      });
    }
    const progress = contract.progress;
    const singleLookV3 = dashboard.schema_version === "portfolio-forward-dashboard-v7";
    const singleLookStatusText = {
      NOT_DUE: "首次联合门槛尚未到期 · 不作通过结论",
      REVIEW_REQUIRED: "首次到期决策已冻结 · 仅进入人工研究复核",
      STOP_RESEARCH: "首次到期决策已冻结为停止晋级 · 后续仅保留描述",
      BLOCK: "首次到期决策来源或绑定不可核验 · 不使用判定",
    };
    const singleLookProgressText = `结果 ${progress.forward_outcomes}/${progress.required_forward_outcomes}`
      + ` · 调仓 ${progress.executed_rebalances}/${progress.required_executed_rebalances}`
      + ` · 结算 ${progress.settlements} · 观察 ${progress.captured_observations}`
      + (contract.status === "NOT_DUE"
        ? " · 首次到期决策尚未形成"
        : " · 首次到期决策已冻结，后续累计仅描述");
    return Object.freeze({
      valid: true,
      available: true,
      legacy: false,
      dashboardAuthoritySafe,
      rawStatus: contract.status,
      statusText: singleLookV3
        ? singleLookStatusText[contract.status]
        : FORWARD_STATISTICAL_MATURITY_COPY[contract.status],
      progressText: `结果 ${progress.forward_outcomes}/${progress.required_forward_outcomes}`
        + ` · 调仓 ${progress.executed_rebalances}/${progress.required_executed_rebalances}`
        + ` · 结算 ${progress.settlements} · 观察 ${progress.captured_observations}`,
      ...(singleLookV3 ? { progressText: singleLookProgressText } : {}),
      sourceBindingAvailable: contract.sourceBinding.available,
      sourceBindingRawStatus: contract.sourceBinding.status,
      sourceBindingText: contract.sourceBinding.statusText,
      sourceBindingDetailText: contract.sourceBinding.detailText,
    });
  }

  function evidenceAttributionPresentation(input = {}) {
    const hash256 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
    const identityLabel = (value) => {
      const text = typeof value === "string" ? value.trim() : "";
      return /^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(text) ? text : null;
    };
    const shortHash = (value) => `${value.slice(0, 12)}…`;
    const frozenSnapshot = input.frozenSnapshot;
    const frozenPresentation = internalBacktestReturnQualityPresentation(frozenSnapshot);
    const frozenCandidateHash = frozenPresentation.verified
      && hash256(frozenSnapshot?.candidate_hash)
      ? frozenSnapshot.candidate_hash
      : null;

    const forwardDashboard = input.forwardDashboard;
    const forwardPermissions = forwardDashboard?.permissions;
    const isLegacyForwardDashboard = Boolean(
      forwardDashboard?.schema_version === "portfolio-forward-dashboard-v4"
      && !Object.hasOwn(forwardDashboard, "statistical_maturity"),
    );
    const isCurrentForwardDashboard = Boolean(
      [
        "portfolio-forward-dashboard-v5",
        "portfolio-forward-dashboard-v6",
        "portfolio-forward-dashboard-v7",
      ].includes(forwardDashboard?.schema_version)
      && forwardStatisticalMaturityPresentation(forwardDashboard).valid,
    );
    const forwardContractValid = forwardDashboard
      && typeof forwardDashboard === "object"
      && !Array.isArray(forwardDashboard)
      && (isLegacyForwardDashboard || isCurrentForwardDashboard)
      && hash256(forwardDashboard.candidate_hash)
      && forwardPermissions
      && typeof forwardPermissions === "object"
      && !Array.isArray(forwardPermissions)
      && forwardPermissions.read_only === true
      && forwardPermissions.observation_only === true
      && forwardPermissions.simulation_only === true
      && forwardPermissions.paper_authorized === false
      && forwardPermissions.live_order_allowed === false
      && forwardPermissions.live_trading_hard_block === true
      && executionAuthoritySafe(forwardDashboard);
    const forwardCandidateHash = forwardContractValid
      ? forwardDashboard.candidate_hash
      : null;

    const relationStatus = frozenCandidateHash && forwardCandidateHash
      ? frozenCandidateHash === forwardCandidateHash ? "SAME" : "MISMATCH"
      : "UNKNOWN";
    const relationText = relationStatus === "SAME"
      ? "同一组合候选 · 仅确认归属，不代表盈利"
      : relationStatus === "MISMATCH"
        ? "候选不同 · 禁止合并解读"
        : "候选归属未核验 · 禁止合并解读";

    const strategySnapshot = input.strategySnapshot;
    const strategyPresentation = strategyLabEvidencePresentation(strategySnapshot);
    const currentStrategyId = identityLabel(input.currentStrategyId);
    const requestedStrategyId = strategyPresentation.valid
      ? identityLabel(strategySnapshot?.requested_strategy_id)
      : null;
    const selectedStrategyId = strategyPresentation.valid
      ? identityLabel(strategySnapshot?.selected_strategy_id)
      : null;
    const hypothesis = strategySnapshot?.hypothesis_preregistration;
    const hypothesisId = strategyPresentation.valid
      ? identityLabel(hypothesis?.hypothesis_id)
      : null;
    const hypothesisHash = strategyPresentation.valid && hash256(hypothesis?.hypothesis_hash)
      ? hypothesis.hypothesis_hash
      : null;
    const strategyContextMatches = Boolean(
      currentStrategyId
      && requestedStrategyId
      && currentStrategyId === requestedStrategyId,
    );
    const hypothesisBoundToCurrentStrategy = Boolean(
      strategyContextMatches
      && selectedStrategyId === currentStrategyId
      && hypothesis?.status === "BOUND"
      && hypothesis?.selected_strategy_match === true
      && hypothesisId
      && hypothesisHash,
    );
    let strategyContextText = currentStrategyId
      ? `当前策略 ${currentStrategyId}`
      : "当前策略未核验";
    if (hypothesisBoundToCurrentStrategy) {
      strategyContextText += ` · 事前假设 ${hypothesisId}`;
    } else if (strategyPresentation.valid && strategyContextMatches) {
      strategyContextText += strategySnapshot?.strategy_match_status === "NOT_IN_REPORT"
        ? " · 冻结假设未覆盖当前策略"
        : " · 事前假设归属未核验";
    } else if (strategyPresentation.valid && currentStrategyId && requestedStrategyId) {
      strategyContextText += " · 冻结策略证据上下文不一致";
    } else {
      strategyContextText += " · 事前假设归属未核验";
    }

    return Object.freeze({
      relationStatus,
      frozenCandidateText: frozenCandidateHash
        ? `冻结组合 ${shortHash(frozenCandidateHash)}`
        : "冻结组合归属未核验",
      forwardCandidateText: forwardCandidateHash
        ? `当前自然前向 ${shortHash(forwardCandidateHash)}`
        : "当前自然前向归属未核验",
      relationText,
      strategyAttributionText: `${strategyContextText} · 与组合候选未建立白名单绑定`,
      rawFrozenCandidateHash: frozenCandidateHash,
      rawForwardCandidateHash: forwardCandidateHash,
      rawHypothesisHash: hypothesisBoundToCurrentStrategy ? hypothesisHash : null,
    });
  }

  function strategyCorrelationClusterSummaryPresentation(input = {}) {
    const unknown = () => Object.freeze({
      valid: false,
      rawStatus: "UNKNOWN",
      rawSourceStatus: "UNKNOWN",
      rawLane: "UNKNOWN",
      statusText: "未核验",
      sourceText: "本地冻结完成日收盘复算：未核验",
      gapText: "输入完整性、事前截止日与正式协议绑定尚未闭合",
      maturityText: "独立簇票：-- / --",
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "固定 60 个完成日收益、绝对 Pearson 阈值 0.75；当前不形成准入结论",
    });
    const expectedKeys = [
      "absolute_pearson_threshold",
      "cluster_count",
      "cluster_vote_rule",
      "cross_cluster_conflict_count",
      "current_admission_allowed",
      "current_report_schema_bound",
      "current_writer_activation_allowed",
      "external_authenticity_proven",
      "first_gap_category",
      "formal_registry_bound",
      "full_manifest_reverified",
      "gate_status",
      "interpretation",
      "lane",
      "live_order_allowed",
      "lookback_observations",
      "minimum_pair_overlap",
      "next_evidence_required",
      "pair_count",
      "paper_authorized",
      "parameter_selection_allowed",
      "passing_cluster_count",
      "performance_claim_allowed",
      "preregistered_cutoff_bound",
      "profitability_proven",
      "replay_scope",
      "required_cluster_votes",
      "required_price_rows",
      "schema_version",
      "source_status",
      "status",
    ];
    if (!input || typeof input !== "object" || Array.isArray(input)) return unknown();
    const inputKeys = Object.keys(input);
    if (
      inputKeys.length !== expectedKeys.length
      || !expectedKeys.every((key) => Object.prototype.hasOwnProperty.call(input, key))
    ) return unknown();

    const authorityKeys = [
      "current_admission_allowed",
      "current_report_schema_bound",
      "current_writer_activation_allowed",
      "external_authenticity_proven",
      "formal_registry_bound",
      "full_manifest_reverified",
      "live_order_allowed",
      "paper_authorized",
      "parameter_selection_allowed",
      "performance_claim_allowed",
      "preregistered_cutoff_bound",
      "profitability_proven",
    ];
    const fixedContractValid = input.schema_version === "strategy-correlation-cluster-public-summary-v1"
      && input.lookback_observations === 60
      && input.required_price_rows === 61
      && input.minimum_pair_overlap === 40
      && input.absolute_pearson_threshold === 0.75
      && input.cluster_vote_rule === "ALL_MEMBERS_PASS_ONE_VOTE_PER_CLUSTER"
      && input.replay_scope === "LOCAL_FROZEN_COMPLETED_DAILY_CLOSE_REPLAY_NOT_EXTERNAL_AUTHENTICITY"
      && input.interpretation === "DESCRIPTIVE_CORRELATION_INDEPENDENCE_ONLY"
      && input.next_evidence_required === "FORMAL_PROTOCOL_BINDING_AND_NEW_REPORT_SCHEMA"
      && authorityKeys.every((key) => input[key] === false);
    const statusValid = ["UNKNOWN", "DESCRIPTIVE_PASS", "DESCRIPTIVE_BLOCK"].includes(input.status);
    const gapCategoryValid = input.first_gap_category === null
      || (typeof input.first_gap_category === "string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(input.first_gap_category));
    if (!fixedContractValid || !statusValid || !gapCategoryValid) return unknown();

    const countKeys = [
      "cluster_count",
      "passing_cluster_count",
      "required_cluster_votes",
      "cross_cluster_conflict_count",
      "pair_count",
    ];
    if (input.status === "UNKNOWN") {
      const unknownValid = input.source_status === "UNKNOWN"
        && input.gate_status === "UNKNOWN"
        && input.lane === "UNKNOWN"
        && input.first_gap_category === "INPUT_INTEGRITY"
        && countKeys.every((key) => input[key] === null);
      if (!unknownValid) return unknown();
      return Object.freeze({ ...unknown(), valid: true });
    }

    const countsValid = countKeys.every((key) => Number.isInteger(input[key]) && input[key] >= 0)
      && input.cluster_count >= 2
      && input.required_cluster_votes === Math.ceil(input.cluster_count * 0.6)
      && input.passing_cluster_count <= input.cluster_count
      && input.required_cluster_votes <= input.cluster_count;
    const replayValid = input.source_status === "VERIFIED_LOCAL_REPLAY"
      && ["RAW_EXCESS", "RISK_ADJUSTED"].includes(input.lane)
      && countsValid;
    const passValid = input.status === "DESCRIPTIVE_PASS"
      && input.gate_status === "PASS"
      && input.passing_cluster_count >= input.required_cluster_votes
      && input.cross_cluster_conflict_count === 0;
    const blockValid = input.status === "DESCRIPTIVE_BLOCK"
      && input.gate_status === "BLOCK"
      && (
        input.passing_cluster_count < input.required_cluster_votes
        || input.cross_cluster_conflict_count > 0
      );
    if (!replayValid || (!passValid && !blockValid)) return unknown();

    const descriptivePass = input.status === "DESCRIPTIVE_PASS";
    return Object.freeze({
      valid: true,
      rawStatus: input.status,
      rawSourceStatus: input.source_status,
      rawLane: input.lane,
      statusText: descriptivePass ? "描述性未阻断" : "描述性阻断",
      sourceText: "本地冻结完成日收盘已直接复算 · 不证明外部真实性",
      gapText: descriptivePass
        ? "正式截止日、注册表与新报告 schema 尚未绑定"
        : "本地复算先有相关簇阻断；正式协议绑定仍未闭合",
      maturityText: `独立簇票 ${input.passing_cluster_count} / ${input.required_cluster_votes} · 共 ${input.cluster_count} 簇`,
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: `固定 ${input.lookback_observations} 个完成日收益 · |Pearson| >= ${input.absolute_pearson_threshold.toFixed(2)} 视为高相关`,
    });
  }

  const SUMMARY_FIELDS = [
    "absolute_pearson_threshold",
    "ambiguous_cross_cluster_count",
    "confidence_level",
    "confirmed_high_cross_cluster_count",
    "cross_cluster_pair_count",
    "current_admission_allowed",
    "current_writer_activation_allowed",
    "effective_sample_method",
    "evidence_scope",
    "external_authenticity_proven",
    "gap_category",
    "insufficient_effective_sample_pair_count",
    "live_order_allowed",
    "lookback_observations",
    "maturity",
    "minimum_effective_observations",
    "minimum_pair_overlap",
    "pair_count",
    "paper_authorized",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "permission",
    "profitability_proven",
    "required_price_rows",
    "required_source_schema_version",
    "requires_new_report_schema",
    "schema_version",
    "status",
    "uncertainty_policy",
  ].sort();

  const FIXED_VALUES = {
    schema_version: "strategy-correlation-uncertainty-public-summary-v1",
    required_source_schema_version: "strategy-correlation-uncertainty-audit-v2",
    evidence_scope: "REDACTED_LOCAL_CORRELATION_UNCERTAINTY",
    uncertainty_policy: "FISHER_Z_95_WITH_LAG1_EFFECTIVE_N_DESCRIPTIVE_V1",
    effective_sample_method: "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1",
    lookback_observations: 60,
    required_price_rows: 61,
    minimum_pair_overlap: 40,
    minimum_effective_observations: 12,
    confidence_level: 0.95,
    absolute_pearson_threshold: 0.75,
    maturity: "DESCRIPTIVE_ONLY",
    permission: "RESEARCH_ONLY",
    external_authenticity_proven: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    requires_new_report_schema: true,
    current_writer_activation_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };

  const COUNT_FIELDS = [
    "pair_count",
    "cross_cluster_pair_count",
    "confirmed_high_cross_cluster_count",
    "ambiguous_cross_cluster_count",
    "insufficient_effective_sample_pair_count",
  ];

  function exactFields(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value).sort();
    return keys.length === SUMMARY_FIELDS.length
      && keys.every((key, index) => key === SUMMARY_FIELDS[index]);
  }

  function fixedValuesMatch(value) {
    return Object.entries(FIXED_VALUES).every(
      ([key, expected]) => value[key] === expected
    );
  }

  function unknownPresentation(valid) {
    return {
      valid,
      contractConnected: valid,
      rawStatus: "UNKNOWN",
      rawGapCategory: "SOURCE_INVALID",
      statusText: valid ? "来源未连接" : "未核验",
      sourceText: "相关性不确定性审计：未核验",
      gapText: "有效样本、区间分类与事前协议绑定尚未闭合",
      maturityText: "跨簇 pair：-- / -- · 有效样本门槛：12",
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "公共投影只接受聚合计数；symbol、相关系数、区间与 Hash 不进入页面",
    };
  }

  function gapCategoryFor(value) {
    const categories = [];
    if (value.confirmed_high_cross_cluster_count > 0) {
      categories.push("CROSS_CLUSTER_CONFIRMED_HIGH");
    }
    if (value.ambiguous_cross_cluster_count > 0) {
      categories.push("CROSS_CLUSTER_AMBIGUOUS");
    }
    if (value.insufficient_effective_sample_pair_count > 0) {
      categories.push("EFFECTIVE_SAMPLE_INSUFFICIENT");
    }
    if (categories.length > 1) return "MULTIPLE_CROSS_CLUSTER_UNCERTAINTY_GAPS";
    if (categories.length === 1) return categories[0];
    return value.status === "OBSERVED_UNCERTAINTY_BLOCK"
      ? "SOURCE_EVIDENCE_BLOCK"
      : "NONE_OBSERVED";
  }

  function gapText(category) {
    const labels = {
      NONE_OBSERVED: "当前聚合未观察到跨簇区间阻断 · 仍非外部真实性",
      CROSS_CLUSTER_CONFIRMED_HIGH: "跨簇高相关区间已确认 · 需要重新预登记",
      CROSS_CLUSTER_AMBIGUOUS: "相关区间跨越阈值 · 不确定性不能按低相关处理",
      EFFECTIVE_SAMPLE_INSUFFICIENT: "有效样本不足 · 不能形成低相关描述",
      MULTIPLE_CROSS_CLUSTER_UNCERTAINTY_GAPS: "存在多类跨簇不确定性缺口",
      SOURCE_EVIDENCE_BLOCK: "来源审计阻断 · 需要补齐冻结证据",
    };
    return labels[category] || "不确定性分类未核验";
  }

  function strategyCorrelationUncertaintySummaryPresentation(value) {
    if (!exactFields(value) || !fixedValuesMatch(value)) {
      return unknownPresentation(false);
    }
    if (value.status === "UNKNOWN") {
      const unknownShape = value.gap_category === "SOURCE_INVALID"
        && COUNT_FIELDS.every((field) => value[field] === null);
      return unknownPresentation(unknownShape);
    }
    if (![
      "OBSERVED_NO_UNCERTAINTY_BLOCK",
      "OBSERVED_UNCERTAINTY_BLOCK",
    ].includes(value.status)) {
      return unknownPresentation(false);
    }
    if (!COUNT_FIELDS.every(
      (field) => Number.isInteger(value[field]) && value[field] >= 0
    )) {
      return unknownPresentation(false);
    }
    if (value.cross_cluster_pair_count > value.pair_count) {
      return unknownPresentation(false);
    }
    const blockingCount = value.confirmed_high_cross_cluster_count
      + value.ambiguous_cross_cluster_count
      + value.insufficient_effective_sample_pair_count;
    if (blockingCount > value.cross_cluster_pair_count) {
      return unknownPresentation(false);
    }
    if (
      value.status === "OBSERVED_NO_UNCERTAINTY_BLOCK"
      && blockingCount !== 0
    ) {
      return unknownPresentation(false);
    }
    const expectedGap = gapCategoryFor(value);
    if (value.gap_category !== expectedGap) {
      return unknownPresentation(false);
    }
    const observedBlock = value.status === "OBSERVED_UNCERTAINTY_BLOCK";
    return {
      valid: true,
      contractConnected: true,
      rawStatus: value.status,
      rawGapCategory: value.gap_category,
      statusText: observedBlock
        ? "存在不确定性证据缺口"
        : "未观察到不确定性阻断",
      sourceText: "冻结价格复算 · 95% Fisher-z · lag-1 有效样本",
      gapText: gapText(value.gap_category),
      maturityText: "跨簇 pair "
        + value.cross_cluster_pair_count + " / " + value.pair_count
        + " · 高相关 " + value.confirmed_high_cross_cluster_count
        + " · 模糊 " + value.ambiguous_cross_cluster_count
        + " · 样本不足 " + value.insufficient_effective_sample_pair_count,
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "60 个完成日收益 · 61 根收盘 · 最小重叠 40"
        + " · 有效样本门槛 12 · |r| 阈值 0.75",
    };
  }

  const MULTIPLICITY_SUMMARY_FIELDS = [
    "current_admission_allowed",
    "current_report_schema_bound",
    "current_writer_activation_allowed",
    "decision_status",
    "evidence_scope",
    "expected_family_size",
    "external_authenticity_proven",
    "familywise_alpha",
    "familywise_confidence_level",
    "familywise_method",
    "formal_registry_bound",
    "gap_category",
    "live_order_allowed",
    "maturity",
    "observed_family_size",
    "paper_authorized",
    "parameter_selection_allowed",
    "per_pair_alpha",
    "performance_claim_allowed",
    "permission",
    "profitability_proven",
    "required_matrix_report_schema_version",
    "required_report_schema_version",
    "required_source_schema_version",
    "requires_current_consumer_activation",
    "schema_version",
    "status",
  ].sort();

  const MULTIPLICITY_FIXED_VALUES = {
    schema_version: "strategy-correlation-multiplicity-public-summary-v1",
    required_source_schema_version:
      "strategy-correlation-multiplicity-report-evidence-v1",
    required_report_schema_version: 16,
    required_matrix_report_schema_version: 8,
    evidence_scope: "REDACTED_LOCAL_CORRELATION_MULTIPLICITY",
    familywise_method: "BONFERRONI_TWO_SIDED_95_FWER_CROSS_CLUSTER_V1",
    familywise_confidence_level: 0.95,
    familywise_alpha: 0.05,
    maturity: "DESCRIPTIVE_ONLY",
    permission: "RESEARCH_ONLY",
    external_authenticity_proven: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    formal_registry_bound: false,
    current_report_schema_bound: false,
    requires_current_consumer_activation: true,
    current_writer_activation_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };

  function multiplicityUnknownPresentation(valid) {
    return {
      valid,
      contractConnected: valid,
      rawStatus: "UNKNOWN",
      rawGapCategory: "SOURCE_INVALID",
      statusText: valid ? "来源未连接" : "未核验",
      sourceText: "Schema16 family evidence：未核验",
      gapText: "事前 family size、Bonferroni 调整与来源重放尚未闭合",
      maturityText: "跨簇 family：-- / -- · 单 pair α：--",
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "只公开 family 聚合；symbol、pair、protocol 与 Hash 不进入页面",
    };
  }

  function multiplicityGapText(category) {
    const labels = {
      NONE_OBSERVED: "Bonferroni family 未观察到聚合阻断 · 仍非外部真实性",
      CORRELATION_GATE_BLOCK: "相关簇基础门禁阻断 · family 结论不可推进",
      UNCERTAINTY_BLOCK: "单 pair 区间仍有不确定性 · family 校正继续阻断",
      FAMILY_WISE_MULTIPLICITY_BLOCK:
        "family-wise 校正后仍有跨簇缺口 · 需要重登记或补证据",
      SOURCE_DECISION_BLOCK: "来源 decision 不一致 · family 结论未核验",
    };
    return labels[category] || "family-wise gap 未核验";
  }

  function strategyCorrelationMultiplicitySummaryPresentation(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return multiplicityUnknownPresentation(false);
    }
    const keys = Object.keys(value).sort();
    if (
      keys.length !== MULTIPLICITY_SUMMARY_FIELDS.length
      || !keys.every(
        (key, index) => key === MULTIPLICITY_SUMMARY_FIELDS[index]
      )
      || !Object.entries(MULTIPLICITY_FIXED_VALUES).every(
        ([key, expected]) => value[key] === expected
      )
    ) {
      return multiplicityUnknownPresentation(false);
    }
    if (value.status === "UNKNOWN") {
      const unknownShape = value.decision_status === null
        && value.expected_family_size === null
        && value.observed_family_size === null
        && value.per_pair_alpha === null
        && value.gap_category === "SOURCE_INVALID";
      return multiplicityUnknownPresentation(unknownShape);
    }
    if (![
      "OBSERVED_NO_FAMILY_WISE_BLOCK",
      "OBSERVED_FAMILY_WISE_BLOCK",
    ].includes(value.status)) {
      return multiplicityUnknownPresentation(false);
    }
    if (
      !Number.isInteger(value.expected_family_size)
      || value.expected_family_size <= 0
      || value.observed_family_size !== value.expected_family_size
      || typeof value.per_pair_alpha !== "number"
      || !Number.isFinite(value.per_pair_alpha)
      || Math.abs(
        value.per_pair_alpha
          - MULTIPLICITY_FIXED_VALUES.familywise_alpha
            / value.expected_family_size
      ) > 1e-15
    ) {
      return multiplicityUnknownPresentation(false);
    }
    const decisionPass = value.decision_status === "PASS";
    const decisionBlock = value.decision_status === "BLOCK";
    if (
      (!decisionPass && !decisionBlock)
      || (decisionPass
        && (
          value.status !== "OBSERVED_NO_FAMILY_WISE_BLOCK"
          || value.gap_category !== "NONE_OBSERVED"
        ))
      || (decisionBlock
        && (
          value.status !== "OBSERVED_FAMILY_WISE_BLOCK"
          || ![
            "CORRELATION_GATE_BLOCK",
            "UNCERTAINTY_BLOCK",
            "FAMILY_WISE_MULTIPLICITY_BLOCK",
            "SOURCE_DECISION_BLOCK",
          ].includes(value.gap_category)
        ))
    ) {
      return multiplicityUnknownPresentation(false);
    }
    return {
      valid: true,
      contractConnected: true,
      rawStatus: value.status,
      rawGapCategory: value.gap_category,
      statusText: decisionBlock
        ? "family-wise 证据存在缺口"
        : "family-wise 未观察到阻断",
      sourceText: "Schema16 冻结选择重放 · 事前 family 登记",
      gapText: multiplicityGapText(value.gap_category),
      maturityText: "跨簇 family "
        + value.observed_family_size + " / " + value.expected_family_size
        + " · 单 pair α " + value.per_pair_alpha.toFixed(6),
      permissionText: "仅研究描述 · 不选参 · 模拟未授权 · 实盘永久硬锁",
      detailText: "95% family-wise · Bonferroni · schema8 consumer dormant",
    };
  }

  return Object.freeze({
    AUTHORITY_SUMMARY,
    PERMISSION_PRESENTATIONS,
    backtestEvidencePresentation,
    backtestRobustnessPresentation,
    evidenceAttributionPresentation,
    forwardStatisticalMaturityPresentation,
    forwardEvidenceGapPresentation,
    internalBacktestReturnQualityPresentation,
    marketTruthEvidenceGapPresentation,
    pipelineStagePresentation,
    pipelineSummaryPresentation,
    researchEvidenceStatusPresentation,
    smallCapitalEvidenceGapPresentation,
    statusPresentation,
    strategyCorrelationClusterSummaryPresentation,
    strategyCorrelationMultiplicitySummaryPresentation,
    strategyCorrelationUncertaintySummaryPresentation,
    strategyLabEvidencePresentation,
    strategyEvidencePresentation,
    strategySourceTextPresentation,
  });
});
