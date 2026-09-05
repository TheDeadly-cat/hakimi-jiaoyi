const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const evidence = require("./evidence_presentation.js");

function projectRealSchema14Snapshots() {
  const projectRoot = path.resolve(__dirname, "..", "..");
  const python = process.env.HAKIMI_TEST_PYTHON || "python";
  const source = `
import json
from tests.test_strategy_research_pointer import StrategyResearchPointerTests
from exchange_terminal.services import strategy_research_pointer as pointer_module

def project(report):
    pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)
    return pointer_module._evidence_projection(
        report,
        pointer,
        StrategyResearchPointerTests._verification(),
        requested_strategy_id="dual_ma",
        implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
        observed_at_ms=None,
    )

bound_report = StrategyResearchPointerTests._schema14_report()
receipt_only_report = StrategyResearchPointerTests._schema14_report(receipt_only=True)
drift_report = StrategyResearchPointerTests._schema14_report()
drift_report["preregistered_failure_admission"]["search_lineage_binding"]["current_trial_count"] += 1
print(json.dumps({
    "bound": project(bound_report),
    "receipt_only": project(receipt_only_report),
    "drift": project(drift_report),
}, ensure_ascii=False))
`;
  return JSON.parse(execFileSync(python, ["-c", source], {
    cwd: projectRoot,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
    env: {
      ...process.env,
      HAKIMI_TEST_MODE: "1",
      HAKIMI_SKIP_LOCAL_AI_ENV: "1",
      PYTHONDONTWRITEBYTECODE: "1",
      // Match Node's UTF-8 decoder even on Windows runners using cp1252.
      PYTHONIOENCODING: "utf-8",
    },
  }));
}

function projectRealSingleLookContracts() {
  const projectRoot = path.resolve(__dirname, "..", "..");
  const python = process.env.HAKIMI_TEST_PYTHON || "python";
  const source = `
import json
from unittest.mock import patch

from tests.test_portfolio_backtest_pack import (
    forward_projection_v2,
    sealed_v6_pack,
)
from tests.test_portfolio_forward_statistical_maturity import (
    synthetic_single_look_stage,
    v3_maturity_bundle,
)
from exchange_terminal.services.portfolio_backtest_pack_pointer import (
    PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
    project_verified_portfolio_backtest_return_quality_snapshot,
)
from exchange_terminal.services.portfolio_forward_projection import (
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION,
    build_portfolio_forward_status_projection,
)

def snapshot(outcomes, required, weak_edge=False):
    pack = sealed_v6_pack(
        forward_projection_v2(
            outcomes=outcomes,
            required=required,
            weak_edge=weak_edge,
        )
    )
    projected = project_verified_portfolio_backtest_return_quality_snapshot(
        {"generated_at": 100},
        pack,
        schema_version=PORTFOLIO_BACKTEST_RETURN_QUALITY_SNAPSHOT_V4_SCHEMA_VERSION,
    )
    # The backend test helper uses a readable candidate label. The public
    # browser contract deliberately requires a lowercase SHA-256 identity.
    projected["candidate_hash"] = "a" * 64
    return projected

def dashboard(stage_status, equities):
    candidate, observer, performance = v3_maturity_bundle(
        stage_status=stage_status,
        strategy_equities=equities,
    )
    with patch(
        "exchange_terminal.services.portfolio_forward_statistical_maturity."
        "audit_paired_equity_curve_stage",
        side_effect=synthetic_single_look_stage(status=stage_status),
    ):
        projected = build_portfolio_forward_status_projection(
            {
                "status": "BLOCK",
                "blockers": ["fixture_operational_evidence_not_supplied"],
                "candidate_hash": candidate["candidate_hash"],
                "scheduler": {},
                "experiment_registry": {},
            },
            observed_now_ms=300,
            live_trading_hard_block=True,
            active_candidate=candidate,
            observer_status=observer,
            performance_status=performance,
            dashboard_schema_version=(
                PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION
            ),
        )["incremental_observation"]
    projected["candidate_hash"] = "a" * 64
    projected["statistical_maturity"]["candidate_hash"] = "a" * 64
    return projected

print(json.dumps({
    "snapshot_not_due": snapshot(4, 8),
    "snapshot_pass": snapshot(8, 8),
    "snapshot_tail": snapshot(12, 8),
    "snapshot_block": snapshot(8, 8, weak_edge=True),
    "dashboard_not_due": dashboard("PASS", [100.0, 101.0]),
    "dashboard_pass": dashboard(
        "PASS",
        [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
    ),
    "dashboard_block": dashboard(
        "BLOCK",
        [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0],
    ),
}, ensure_ascii=False))
`;
  return JSON.parse(execFileSync(python, ["-c", source], {
    cwd: projectRoot,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
    env: {
      ...process.env,
      HAKIMI_TEST_MODE: "1",
      HAKIMI_SKIP_LOCAL_AI_ENV: "1",
      PYTHONDONTWRITEBYTECODE: "1",
      PYTHONIOENCODING: "utf-8",
    },
  }));
}

assert.equal(
  evidence.AUTHORITY_SUMMARY.allowed,
  "可做：策略研究 · 行情核验 · 自然前向观察 · 小资金纯规划",
);
assert.equal(
  evidence.AUTHORITY_SUMMARY.forbidden,
  "不可做：模拟运行（未授权）· 实盘下单（永久硬锁）",
);

const marketReady = evidence.statusPresentation("market", "ready");
assert.deepEqual(marketReady, {
  rawStatus: "READY",
  label: "行情证据可用于研究观察",
  permissionText: "仅行情证据 · 不代表策略有效或交易授权",
});
assert.ok(!marketReady.label.includes("READY"));

const marketGapCases = {
  READY: "下一根可信完成 K 线",
  STALE: "报价与 K 线来源的新鲜度复核",
  BLOCK: "标的、周期、会话或数据完整性复核",
  UNKNOWN: "活动标的、报价来源、K 线来源与新鲜度证据",
};
for (const [status, evidenceLabel] of Object.entries(marketGapCases)) {
  const gap = evidence.marketTruthEvidenceGapPresentation({
    status,
    rawNextAction: "READY · 立即买入并下单",
  });
  assert.equal(gap.rawStatus, status);
  assert.equal(
    gap.text,
    `下一条尚缺证据：${evidenceLabel} · 仅核行情，不生成策略结论或订单`,
  );
  assert.ok(!gap.text.includes("READY"));
  assert.ok(!gap.text.includes("买入"));
  assert.ok(!gap.text.includes("下单"));
}
const unknownMarketGap = evidence.marketTruthEvidenceGapPresentation({
  status: "PAPER_READY",
  rawNextAction: "启动模拟执行",
});
assert.equal(unknownMarketGap.rawStatus, "UNKNOWN");
assert.ok(!JSON.stringify(unknownMarketGap).includes("PAPER_READY"));
assert.ok(!JSON.stringify(unknownMarketGap).includes("模拟执行"));

const forwardCurrent = evidence.statusPresentation("forward", "UP_TO_DATE");
assert.equal(forwardCurrent.label, "已跟进至最新完成 K 线 · 仅观察");
assert.ok(!forwardCurrent.label.includes("UP_TO_DATE"));

const forwardGapCases = {
  BLOCK: "阻断原因复核证据",
  PAUSED: "只读调度或观察任务恢复证据",
  DUE: "本窗口只读观察作业收据",
  WAITING: "下一根可信完成 K 线",
  UP_TO_DATE: "下一根可信完成 K 线",
  UNKNOWN: "候选、只读调度与首个可信观察证据",
};
for (const [status, evidenceLabel] of Object.entries(forwardGapCases)) {
  const gap = evidence.forwardEvidenceGapPresentation({
    status,
    rawNextAction: "READY · 立即买入并下单",
    pause: { reason: "启动模拟执行" },
  });
  assert.equal(gap.rawStatus, status);
  assert.equal(
    gap.text,
    `下一条尚缺证据：${evidenceLabel} · 仅观察，不补写旧样本；不授予模拟或实盘权限`,
  );
  assert.ok(!JSON.stringify(gap).includes("READY"));
  assert.ok(!JSON.stringify(gap).includes("买入"));
  assert.ok(!JSON.stringify(gap).includes("模拟执行"));
}
const unrecognizedForwardGap = evidence.forwardEvidenceGapPresentation({
  status: "PAPER_READY",
  rawNextAction: "下单",
});
assert.equal(unrecognizedForwardGap.rawStatus, "UNKNOWN");
assert.equal(
  unrecognizedForwardGap.text,
  "下一条尚缺证据：候选、只读调度与首个可信观察证据 · 仅观察，不补写旧样本；不授予模拟或实盘权限",
);
assert.ok(!JSON.stringify(unrecognizedForwardGap).includes("PAPER_READY"));
assert.ok(!JSON.stringify(unrecognizedForwardGap).includes("下单"));

const planningOnly = evidence.statusPresentation("plan", "PLANNING_ONLY");
assert.equal(planningOnly.label, "仅规划 · 不生成订单");
assert.ok(!planningOnly.label.includes("PLANNING_ONLY"));

const missingFeeEvidence = evidence.smallCapitalEvidenceGapPresentation({
  status: "NEEDS_EVIDENCE",
  checkId: "fee_evidence",
  rawNextAction: "READY · 立即买入并下单",
});
assert.deepEqual(missingFeeEvidence, {
  rawStatus: "NEEDS_EVIDENCE",
  gapKind: "MISSING",
  text: "下一条尚缺证据：费率与成本证据 · 仅研究，不生成订单",
});
assert.ok(!JSON.stringify(missingFeeEvidence).includes("READY"));
assert.ok(!JSON.stringify(missingFeeEvidence).includes("买入"));
assert.ok(!JSON.stringify(missingFeeEvidence).includes("fee_evidence"));

const unknownPlanningEvidence = evidence.smallCapitalEvidenceGapPresentation({
  status: "NEEDS_EVIDENCE",
  checkId: "internal_executor_state",
});
assert.equal(
  unknownPlanningEvidence.text,
  "下一条尚缺证据：关键只读证据未核验 · 仅研究，不生成订单",
);
assert.ok(!JSON.stringify(unknownPlanningEvidence).includes("internal_executor_state"));

const blockedPlanningEvidence = evidence.smallCapitalEvidenceGapPresentation({
  status: "BLOCK",
  checkId: "order_book_depth",
});
assert.equal(
  blockedPlanningEvidence.text,
  "下一条尚缺证据：公开盘口深度证据（当前阻断）· 仅研究，不生成订单",
);
assert.equal(
  evidence.smallCapitalEvidenceGapPresentation({ status: "PLANNING_ONLY" }).text,
  "下一条尚缺证据：无 · 仍仅规划，不生成订单",
);

const emptyStrategy = evidence.strategyEvidencePresentation();
assert.deepEqual(emptyStrategy, {
  hasEvidence: false,
  conclusionText: "尚无研究结论",
  directionText: "方向未形成",
  estimateText: "模型估计未校准",
  noTradeText: "失效与禁做条件尚未核验",
  permissionText: "研究解释 · 非订单 · 不授予模拟或实盘权限",
});
assert.ok(!JSON.stringify(emptyStrategy).includes("Long"));
assert.ok(!JSON.stringify(emptyStrategy).includes("No hard no-trade"));

const explicitResearch = evidence.strategyEvidencePresentation({
  hasAnalysis: true,
  action: "WATCH",
  direction: "LONG",
  probability: 0.63,
  probabilityKnown: true,
});
assert.equal(explicitResearch.conclusionText, "研究结论：继续观察");
assert.equal(explicitResearch.directionText, "研究方向：偏多 · 非订单");
assert.equal(explicitResearch.estimateText, "模型估计 63% · 未校准");
assert.equal(explicitResearch.noTradeText, "失效与禁做条件尚未核验");

const explicitBlock = evidence.strategyEvidencePresentation({
  hasSignal: true,
  action: "BLOCK",
  noTrade: ["数据修订证据异常", "成本压力未通过"],
});
assert.equal(explicitBlock.conclusionText, "研究结论：阻断");
assert.equal(explicitBlock.directionText, "方向未形成");
assert.equal(explicitBlock.noTradeText, "数据修订证据异常 / 成本压力未通过");

const explicitHold = evidence.strategyEvidencePresentation({ hasSignal: true, action: "HOLD" });
assert.equal(explicitHold.conclusionText, "研究结论：继续观察");

const quarantinedFailureText = "来源文本含执行/授权语义，已隔离，需人工复核";
assert.equal(
  evidence.strategySourceTextPresentation("成本压力与数据修订尚未通过"),
  "成本压力与数据修订尚未通过",
);
for (const unsafeFailureText of [
  "READY",
  "ＲＥＡＤＹ",
  "BUY",
  "B\u200BUY",
  "SELL",
  "已授权",
  "已 授 权",
  "paper_authorized",
  "可下单",
  "允许执行",
  '<img src=x onerror="alert(1)">',
  "&#x3c;script&#x3e;alert(1)",
]) {
  assert.equal(evidence.strategySourceTextPresentation(unsafeFailureText), quarantinedFailureText);
  const quarantined = evidence.strategyEvidencePresentation({
    hasWarEvidence: true,
    action: "WAIT",
    noTrade: [unsafeFailureText],
  });
  assert.equal(quarantined.noTradeText, quarantinedFailureText);
  assert.ok(!quarantined.noTradeText.includes(unsafeFailureText));
  assert.ok(!/(?:READY|BUY|SELL|已授权|可下单)/i.test(quarantined.noTradeText));
}
const nonArrayNoTrade = evidence.strategyEvidencePresentation({
  hasWarEvidence: true,
  noTrade: { 0: "READY", length: 1 },
});
assert.equal(nonArrayNoTrade.noTradeText, "失效与禁做条件尚未核验");

const emptyStrategyLabEvidence = evidence.strategyLabEvidencePresentation();
assert.equal(emptyStrategyLabEvidence.valid, false);
assert.equal(emptyStrategyLabEvidence.connectionStatus, "UNKNOWN");
assert.equal(emptyStrategyLabEvidence.parameterText, "参数平台稳定性：未核验");
assert.equal(emptyStrategyLabEvidence.rawAdmissionStatus, "UNKNOWN");
assert.equal(emptyStrategyLabEvidence.admissionText, "事前研究门禁：未核验");
assert.equal(emptyStrategyLabEvidence.rawMechanismStatus, "UNKNOWN");
assert.equal(emptyStrategyLabEvidence.rawFutureConditionStatus, "UNKNOWN");
assert.deepEqual(emptyStrategyLabEvidence.mechanismConditionRows, []);
assert.deepEqual(emptyStrategyLabEvidence.futureConditionRows, []);
assert.equal(Object.isFrozen(emptyStrategyLabEvidence.mechanismConditionRows), true);
assert.ok(emptyStrategyLabEvidence.futureConditionText.includes("未评估、非通过"));
assert.equal(emptyStrategyLabEvidence.rawPostSelectionStatus, "UNKNOWN");
assert.equal(emptyStrategyLabEvidence.rawFrozenTestStatus, "UNKNOWN");
assert.equal(emptyStrategyLabEvidence.rawHoldoutStatus, "UNKNOWN");
assert.ok(emptyStrategyLabEvidence.holdoutText.includes("非自然前向"));
assert.ok(emptyStrategyLabEvidence.detailText.includes("不证明盈利"));

const strategyLabBoundaryContract = {
  schema_version: "strategy-lab-evidence-boundary-v1",
  mode: "DEVELOPMENT_HEURISTIC_PLANNING_ONLY",
  parameter_stability_status: "NOT_CONNECTED",
  cost_sensitivity_status: "NOT_CONNECTED",
  chronological_slice_status: "NOT_CONNECTED",
  research_report_source: "FROZEN_RESEARCH_REPORT_NOT_CONNECTED",
  interpretation: "DESCRIPTIVE_PLANNING_ONLY",
  research_only: true,
  descriptive_only: true,
  development_heuristic_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  paper_authorized: false,
  live_order_allowed: false,
};
const strategyLabBoundary = evidence.strategyLabEvidencePresentation({
  evidence_contract: strategyLabBoundaryContract,
});
assert.equal(strategyLabBoundary.valid, true);
assert.equal(strategyLabBoundary.connectionStatus, "BOUNDARY_ONLY");
assert.equal(strategyLabBoundary.parameterText, "参数平台稳定性：未连接");
assert.equal(strategyLabBoundary.costText, "成本压力：未连接");
assert.equal(strategyLabBoundary.temporalText, "固定参数时间切片：未连接");
assert.equal(strategyLabBoundary.rawAdmissionStatus, "NOT_CONNECTED");
assert.deepEqual(strategyLabBoundary.mechanismConditionRows, []);
assert.deepEqual(strategyLabBoundary.futureConditionRows, []);
assert.equal(strategyLabBoundary.rawPostSelectionStatus, "NOT_CONNECTED");
assert.equal(strategyLabBoundary.rawFrozenTestStatus, "NOT_CONNECTED");
assert.equal(strategyLabBoundary.rawHoldoutStatus, "NOT_CONNECTED");
assert.ok(!strategyLabBoundary.modeText.includes("PASS"));
assert.equal(
  evidence.strategyLabEvidencePresentation({
    evidence_contract: {
      ...strategyLabBoundaryContract,
      paper_authorized: true,
    },
  }).valid,
  false,
);

const frozenStrategyLabPayload = {
  ok: true,
  status: "AVAILABLE",
  source_verification_status: "PASS",
  pointer_schema_version: "strategy-research-report-pointer-v1",
  pointer_hash: "1".repeat(64),
  report_schema_version: 7,
  created_at: "2026-08-12T02:03:04+00:00",
  created_at_ms: 1786500184000,
  batch_spec_hash: "2".repeat(64),
  dataset_manifest_hash: "3".repeat(64),
  batch_run_hash: "4".repeat(64),
  governance_status: "DEVELOPMENT_SELECTION_ONLY",
  formal_single_use: false,
  selection_test_policy: "DEVELOPMENT_ONLY",
  research_generation: "FROZEN_TEST",
  requested_strategy_id: "dual_ma",
  selected_strategy_id: "dual_ma",
  strategy_match_status: "MATCHED",
  available_strategy_ids: ["dual_ma"],
  scope: {
    strategy_count: 1,
    parameter_variant_count: 3,
    selection_symbol_count: 2,
    selection_cell_count: 6,
    frozen_test_candidate_count: 0,
    test_cell_count: 0,
    forward_candidate_count: 0,
  },
  evidence_contract: {
    schema_version: "strategy-lab-frozen-evidence-v3",
    connection_status: "VERIFIED_FROZEN_SOURCE",
    mode: "FROZEN_RESEARCH_EVIDENCE",
    research_report_source: "CURRENT_VERIFIED_STRATEGY_RESEARCH_REPORT",
    interpretation: "DESCRIPTIVE_RESEARCH_EVIDENCE_ONLY",
    strategy_match_status: "MATCHED",
    parameter_stability_status: "PASS",
    hypothesis_preregistration_status: "BOUND",
    cost_sensitivity_status: "PASS",
    chronological_slice_status: "PASS",
    research_only: true,
    descriptive_only: true,
    development_heuristic_only: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    implementation_currentness_checked: true,
    implementation_currentness_status: "MATCH",
    implementation_currentness_match: true,
    implementation_currentness_basis: "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT",
    full_implementation_manifest_checked: true,
    full_implementation_manifest_status: "MATCH",
    full_implementation_manifest_match: true,
    full_implementation_manifest_basis: "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME",
    currentness_facts_schema_version: "strategy-research-currentness-facts-v1",
    currentness_facts_status: "FACTS_AVAILABLE",
    currentness_threshold_applied: false,
    dataset_currentness_checked: false,
    report_age_policy_checked: false,
    paper_authorized: false,
    live_order_allowed: false,
  },
  parameter_stability: {
    schema_version: "strategy-parameter-plateau-v2",
    status: "PASS",
    topology_basis: "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
    numeric_parameter_distance_checked: false,
    frozen_variant_count: 3,
    eligible_variant_count: 2,
    near_best_eligible_variant_count: 2,
    adjacent_near_best_variant_count: 1,
    plateau_width: 2,
    best_adjusted_score: 4.25,
    peak_only: false,
    blockers: [],
    descriptive_only: true,
    parameter_selection_allowed: false,
  },
  hypothesis_preregistration: {
    schema_version: "strategy-hypothesis-preregistration-summary-v1",
    status: "BOUND",
    contract_checked: true,
    hypothesis_id: "frozen-causal-persistence-v1",
    hypothesis_hash: "5".repeat(64),
    research_generation: "FROZEN_TEST",
    strategy_ids: ["dual_ma"],
    selected_strategy_match: true,
    mechanism_family: "causal moving-average persistence confirmation",
    hypothesis_statement: "Completed-bar persistence should retain positive benchmark excess after configured costs.",
    novelty_statement: "This mechanism does not reuse or retune either falsified strategy entry family.",
    mechanism_specific_failure_conditions: [
      "Retire this hypothesis if fresh excess is not positive after stressed costs.",
    ],
    parameter_topology_basis: "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
    numeric_parameter_distance_claimed: false,
    cost_stress_required: true,
    stressed_return_must_remain_positive: true,
    chronological_evaluation_mode: "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
    parameters_refit_per_fold: false,
    walk_forward_optimization_claim_allowed: false,
    fresh_single_use_holdout_required: true,
    minimum_natural_forward_outcomes: 60,
    minimum_executed_rebalances: 8,
    statistical_contract_recheck_required_at_maturity: true,
    historical_backtest_can_substitute_natural_forward: false,
    reuses_falsified_strategy_id: false,
    retunes_falsified_mechanism: false,
    material_mechanism_change_requires_new_strategy_id: true,
    blockers: [],
    descriptive_only: true,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    automatic_paper_activation_allowed: false,
    research_only: true,
    paper_authorized: false,
    live_order_allowed: false,
  },
  cost_sensitivity: {
    status: "PASS",
    evaluated_cell_count: 2,
    pass_cell_count: 2,
    worst_stressed_return_pct: 1.25,
    worst_stressed_drawdown_pct: 7.5,
    break_even_preserved: true,
    blockers: [],
    descriptive_only: true,
    profitability_proven: false,
  },
  chronological_slices: {
    status: "PASS",
    evaluation_mode: "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
    evaluated_cell_count: 2,
    pass_cell_count: 2,
    usable_fold_count: 6,
    positive_fold_count: 5,
    worst_drawdown_pct: 6,
    parameters_refit_per_fold: false,
    walk_forward_optimization_claim_allowed: false,
    blockers: [],
    descriptive_only: true,
  },
  implementation_currentness: {
    schema_version: "strategy-signal-implementation-currentness-v1",
    status: "MATCH",
    basis: "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT",
    checked: true,
    matches_current: true,
    frozen_variant_count: 3,
    matched_variant_count: 3,
    mismatched_variant_count: 0,
    blockers: [],
    full_implementation_manifest_checked: false,
    research_only: true,
    paper_authorized: false,
    live_order_allowed: false,
  },
  full_implementation_currentness: {
    schema_version: "strategy-full-implementation-currentness-v1",
    status: "MATCH",
    basis: "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME",
    checked: true,
    matches_current: true,
    expected_source_count: 12,
    verified_source_count: 12,
    exact_files_checked: true,
    runtime_checked: true,
    blockers: [],
    research_only: true,
    paper_authorized: false,
    live_order_allowed: false,
  },
  currentness_facts: {
    schema_version: "strategy-research-currentness-facts-v1",
    status: "FACTS_AVAILABLE",
    basis: "VERIFIED_REPORT_TIMESTAMPS_WITH_CALLER_OBSERVATION",
    observed_at_ms: 1786507384000,
    report_created_at: "2026-08-12T02:03:04+00:00",
    report_created_at_ms: 1786500184000,
    report_time_basis: "ISO8601_EXPLICIT_OFFSET",
    report_age_ms: 7200000,
    dataset_as_of: "2026-08-10",
    dataset_as_of_source: "REPORT_SUMMARY_AND_SELECTION_ALIGNMENT",
    calendar_days_since_dataset_as_of: 2,
    dataset_age_basis: "UTC_CALENDAR_DAYS_NOT_TRADING_SESSIONS",
    facts_complete: true,
    report_age_threshold_ms: null,
    dataset_age_threshold_calendar_days: null,
    report_age_policy_status: "NOT_DEFINED",
    dataset_freshness_policy_status: "NOT_DEFINED",
    threshold_applied: false,
    freshness_conclusion_allowed: false,
    stale_claim_allowed: false,
    dataset_currentness_checked: false,
    report_age_policy_checked: false,
    blockers: [],
    evidence_gaps: [],
    read_only: true,
    research_only: true,
    descriptive_only: true,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  },
  failure_conditions: {
    schema_version: "strategy-research-failure-conditions-v1",
    status: "GAPS",
    observed: [],
    evidence_gaps: [
      "dataset_currentness_not_checked",
      "report_age_policy_not_checked",
      "natural_forward_performance_not_proven_by_strategy_report",
    ],
    conditions: [
      { condition_id: "parameter_plateau_not_preserved", evidence_status: "PASS", triggered: false, blockers: [] },
      { condition_id: "cost_stress_break_even_not_preserved", evidence_status: "PASS", triggered: false, blockers: [] },
      { condition_id: "fixed_parameter_time_slice_robustness_not_preserved", evidence_status: "PASS", triggered: false, blockers: [] },
      { condition_id: "strategy_signal_implementation_changed", evidence_status: "MATCH", triggered: false, blockers: [] },
      { condition_id: "research_implementation_closure_changed", evidence_status: "MATCH", triggered: false, blockers: [] },
    ],
    descriptive_only: true,
    profitability_proven: false,
    parameter_selection_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  },
  read_only: true,
  research_only: true,
  descriptive_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  implementation_currentness_checked: true,
  implementation_currentness_status: "MATCH",
  implementation_currentness_match: true,
  implementation_currentness_basis: "FROZEN_STRATEGY_SIGNAL_IMPLEMENTATION_FINGERPRINT",
  full_implementation_manifest_checked: true,
  full_implementation_manifest_status: "MATCH",
  full_implementation_manifest_match: true,
  full_implementation_manifest_basis: "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME",
  currentness_facts_status: "FACTS_AVAILABLE",
  dataset_currentness_checked: false,
  report_age_policy_checked: false,
  automatic_paper_activation_allowed: false,
  paper_authorized: false,
  live_order_allowed: false,
};
const frozenStrategyLab = evidence.strategyLabEvidencePresentation(frozenStrategyLabPayload);
assert.equal(frozenStrategyLab.valid, true);
assert.deepEqual(frozenStrategyLab.mechanismConditionRows, []);
assert.deepEqual(frozenStrategyLab.futureConditionRows, []);
assert.equal(frozenStrategyLab.connectionStatus, "VERIFIED_FROZEN");
assert.ok(frozenStrategyLab.modeText.includes("非盲测"));
assert.ok(frozenStrategyLab.modeText.includes("完整实现闭包一致"));
assert.ok(frozenStrategyLab.sourceText.includes("语义复算"));
assert.ok(frozenStrategyLab.implementationText.includes("源码文件 + 运行时"));
assert.ok(frozenStrategyLab.currentnessText.includes("报告年龄 2 小时"));
assert.ok(frozenStrategyLab.currentnessText.includes("数据截止 2026-08-10"));
assert.ok(frozenStrategyLab.currentnessText.includes("未定义新鲜/过期阈值"));
assert.ok(frozenStrategyLab.hypothesisText.includes("事前绑定"));
assert.ok(frozenStrategyLab.hypothesisFailureText.includes("60/8 自然前向"));
assert.ok(frozenStrategyLab.parameterText.includes("非数值距离"));
assert.ok(frozenStrategyLab.costText.includes("非盈利证明"));
assert.ok(frozenStrategyLab.temporalText.includes("非 WFO"));
assert.ok(frozenStrategyLab.failureText.includes("数据新鲜度未核验"));
assert.ok(frozenStrategyLab.detailText.includes("完整源码文件与运行时闭包"));
assert.ok(frozenStrategyLab.detailText.includes("新鲜/过期阈值仍未定义"));
assert.ok(![
  frozenStrategyLab.modeText,
  frozenStrategyLab.sourceText,
  frozenStrategyLab.implementationText,
  frozenStrategyLab.currentnessText,
  frozenStrategyLab.hypothesisText,
  frozenStrategyLab.hypothesisFailureText,
  frozenStrategyLab.parameterText,
  frozenStrategyLab.costText,
  frozenStrategyLab.temporalText,
].join(" ").includes("PASS"));
assert.equal(frozenStrategyLab.rawAdmissionStatus, "NOT_AVAILABLE");
assert.ok(frozenStrategyLab.admissionText.includes("历史报告未包含"));

for (const reportSchemaVersion of [7, 8, 9, 10]) {
  const versionedPayload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
  versionedPayload.report_schema_version = reportSchemaVersion;
  const versionedPresentation = evidence.strategyLabEvidencePresentation(versionedPayload);
  assert.equal(
    versionedPresentation.valid,
    true,
    `hypothesis-bound report schema ${reportSchemaVersion} should remain consumable`,
  );
  assert.equal(versionedPresentation.rawHypothesisStatus, "BOUND");
  assert.equal(versionedPresentation.rawSearchLineageStatus, "NOT_AVAILABLE");
  assert.equal(
    versionedPresentation.lineageText,
    "历史报告未封存检索谱系 · 不补写选择时核验结论",
  );
  assert.ok(versionedPresentation.hypothesisText.includes("事前绑定"));
}

function postSelectionStage(stage, stageStatus = "PASS") {
  if (stageStatus === "NOT_RUN") {
    return {
      stage,
      status: "NOT_RUN",
      candidate_count: 0,
      result_count: 0,
      cell_count: 0,
      replay_verified_cell_count: 0,
      replay_pass_cell_count: 0,
      aggregate_pass_candidate_count: 0,
      minimum_configured_return_pct: null,
      minimum_excess_return_pct: null,
      minimum_severe_cost_return_pct: null,
      worst_drawdown_pct: null,
      total_trades: null,
      fixed_slice_pass_cell_count: 0,
      prefix_invariance_pass_cell_count: 0,
      lookahead_pass_cell_count: 0,
      blockers: [],
    };
  }
  const blocked = stageStatus === "BLOCK";
  const holdout = stage === "HOLDOUT_CONFIRMATION";
  return {
    stage,
    status: stageStatus,
    candidate_count: 1,
    result_count: 1,
    cell_count: 2,
    replay_verified_cell_count: 2,
    replay_pass_cell_count: blocked ? 1 : 2,
    aggregate_pass_candidate_count: blocked ? 0 : 1,
    minimum_configured_return_pct: blocked ? -1.25 : 1.2,
    minimum_excess_return_pct: blocked ? -2.1 : 0.4,
    minimum_severe_cost_return_pct: blocked ? -2.8 : 0.1,
    worst_drawdown_pct: blocked ? 14.5 : 8.5,
    total_trades: 12,
    fixed_slice_pass_cell_count: holdout ? (blocked ? 1 : 2) : 0,
    prefix_invariance_pass_cell_count: holdout ? (blocked ? 1 : 2) : 0,
    lookahead_pass_cell_count: holdout ? (blocked ? 1 : 2) : 0,
    blockers: blocked ? ["post_selection_replay_outcome_not_preserved"] : [],
  };
}

function postSelectionSummary(reportSchemaVersion, frozenStatus = "PASS", holdoutStatus = "PASS") {
  const frozen = postSelectionStage("FROZEN_TEST_ONCE", frozenStatus);
  const holdout = postSelectionStage("HOLDOUT_CONFIRMATION", holdoutStatus);
  const status = [frozenStatus, holdoutStatus].includes("BLOCK")
    ? "BLOCK"
    : frozenStatus === "NOT_RUN" && holdoutStatus === "NOT_RUN"
      ? "NOT_RUN"
      : frozenStatus === "PASS" && holdoutStatus === "PASS"
        ? "PASS"
        : "BLOCK";
  return {
    schema_version: "strategy-post-selection-replay-summary-v1",
    status,
    report_schema_version: reportSchemaVersion,
    frozen_test: frozen,
    holdout_confirmation: holdout,
    historical_backtest_only: true,
    natural_forward_performance_proven: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    automatic_paper_activation_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function bindPostSelectionFailureV2(payload) {
  const summary = payload.post_selection_replay_summary;
  payload.failure_conditions.schema_version = "strategy-research-failure-conditions-v2";
  const replayConditionIds = [
    "frozen_test_replay_not_preserved",
    "holdout_confirmation_replay_not_preserved",
  ];
  payload.failure_conditions.conditions = payload.failure_conditions.conditions.filter(
    (condition) => !replayConditionIds.includes(condition.condition_id),
  );
  payload.failure_conditions.observed = payload.failure_conditions.observed.filter(
    (item) => !replayConditionIds.includes(item),
  );
  payload.failure_conditions.evidence_gaps = payload.failure_conditions.evidence_gaps.filter(
    (item) => !replayConditionIds.some((conditionId) => item === `${conditionId}_not_checked`),
  );
  for (const [conditionId, stage] of [
    ["frozen_test_replay_not_preserved", summary.frozen_test],
    ["holdout_confirmation_replay_not_preserved", summary.holdout_confirmation],
  ]) {
    const triggered = stage.status === "PASS" ? false : stage.status === "BLOCK" ? true : null;
    payload.failure_conditions.conditions.push({
      condition_id: conditionId,
      evidence_status: stage.status,
      triggered,
      blockers: [...stage.blockers],
    });
    if (triggered === true) payload.failure_conditions.observed.push(conditionId);
    if (triggered === null) payload.failure_conditions.evidence_gaps.push(`${conditionId}_not_checked`);
  }
  payload.failure_conditions.observed = [...new Set(payload.failure_conditions.observed)];
  payload.failure_conditions.evidence_gaps = [...new Set(payload.failure_conditions.evidence_gaps)];
  payload.failure_conditions.status = payload.failure_conditions.observed.length ? "TRIGGERED" : "GAPS";
}

function makePostSelectionPayload(reportSchemaVersion, frozenStatus = "PASS", holdoutStatus = "PASS") {
  const payload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
  payload.report_schema_version = reportSchemaVersion;
  payload.formal_single_use = true;
  payload.selection_test_policy = "BLIND_ONCE";
  payload.scope.frozen_test_candidate_count = frozenStatus === "NOT_RUN" ? 0 : 1;
  payload.scope.test_cell_count = frozenStatus === "NOT_RUN" ? 0 : 2;
  payload.scope.forward_candidate_count = holdoutStatus === "PASS" ? 1 : 0;
  payload.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v5";
  payload.post_selection_replay_summary = postSelectionSummary(
    reportSchemaVersion,
    frozenStatus,
    holdoutStatus,
  );
  payload.post_selection_replay_status = payload.post_selection_replay_summary.status;
  payload.evidence_contract.post_selection_replay_status = payload.post_selection_replay_summary.status;
  bindPostSelectionFailureV2(payload);
  return payload;
}

const schema11PassPayload = makePostSelectionPayload(11);
const schema11Pass = evidence.strategyLabEvidencePresentation(schema11PassPayload);
assert.equal(schema11Pass.valid, true);
assert.equal(schema11Pass.rawPostSelectionStatus, "PASS");
assert.equal(schema11Pass.rawFrozenTestStatus, "PASS");
assert.equal(schema11Pass.rawHoldoutStatus, "PASS");
assert.ok(schema11Pass.frozenTestText.includes("冻结 TEST"));
assert.ok(schema11Pass.frozenTestText.includes("最低收益 +1.20%"));
assert.ok(schema11Pass.frozenTestText.includes("非盈利证明"));
assert.ok(schema11Pass.holdoutText.includes("单次历史留出"));
assert.ok(schema11Pass.holdoutText.includes("非自然前向"));
assert.ok(!schema11Pass.postSelectionText.includes("READY"));
assert.deepEqual(schema11Pass.mechanismConditionRows, []);
assert.deepEqual(schema11Pass.futureConditionRows, []);

const schema11TwoCandidatePayload = JSON.parse(JSON.stringify(schema11PassPayload));
schema11TwoCandidatePayload.scope.frozen_test_candidate_count = 2;
schema11TwoCandidatePayload.scope.test_cell_count = 4;
schema11TwoCandidatePayload.scope.forward_candidate_count = 2;
for (const stage of [
  schema11TwoCandidatePayload.post_selection_replay_summary.frozen_test,
  schema11TwoCandidatePayload.post_selection_replay_summary.holdout_confirmation,
]) {
  stage.candidate_count = 2;
  stage.result_count = 2;
  stage.cell_count = 4;
  stage.replay_verified_cell_count = 4;
  stage.replay_pass_cell_count = 4;
  stage.aggregate_pass_candidate_count = 2;
  if (stage.stage === "HOLDOUT_CONFIRMATION") {
    stage.fixed_slice_pass_cell_count = 4;
    stage.prefix_invariance_pass_cell_count = 4;
    stage.lookahead_pass_cell_count = 4;
  }
}
bindPostSelectionFailureV2(schema11TwoCandidatePayload);
const schema11TwoCandidate = evidence.strategyLabEvidencePresentation(schema11TwoCandidatePayload);
assert.equal(schema11TwoCandidate.valid, true);
assert.ok(schema11TwoCandidate.frozenTestText.includes("2 候选"));

const schema12PassPayload = makePostSelectionPayload(12);
schema12PassPayload.preregistered_failure_admission_status = "PASS";
schema12PassPayload.evidence_contract.preregistered_failure_admission_status = "PASS";
schema12PassPayload.preregistered_failure_admission = {
  schema_version: "strategy-preregistered-failure-admission-v1",
  status: "PASS",
  admission_scope: "HYPOTHESIS_BATCH",
  hypothesis_id: "frozen-causal-persistence-v1",
  selected_strategy_status: "PASS",
  selected_strategy_candidate_count: 1,
  selected_strategy_admitted_count: 1,
  admitted_candidate_count: 1,
  checks: [
    { condition_id: "parameter_plateau_absent", status: "PASS", triggered: false, blockers: [] },
    { condition_id: "cost_break_even_lost", status: "PASS", triggered: false, blockers: [] },
    { condition_id: "fixed_parameter_time_slice_instability", status: "PASS", triggered: false, blockers: [] },
  ],
  blockers: [],
  descriptive_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  automatic_paper_activation_allowed: false,
  research_only: true,
  paper_authorized: false,
  live_order_allowed: false,
};
const schema12Pass = evidence.strategyLabEvidencePresentation(schema12PassPayload);
assert.equal(schema12Pass.valid, true);
assert.deepEqual(schema12Pass.mechanismConditionRows, []);
assert.deepEqual(schema12Pass.futureConditionRows, []);
assert.equal(schema12Pass.rawHypothesisStatus, "BOUND");
assert.equal(schema12Pass.rawAdmissionStatus, "PASS");
assert.ok(schema12Pass.admissionText.includes("冻结资格仅供后续历史重放"));
assert.ok(schema12Pass.admissionText.includes("非授权"));
assert.ok(!JSON.stringify(schema12Pass).includes("variant"));

const schema12BlockPayload = JSON.parse(JSON.stringify(schema12PassPayload));
schema12BlockPayload.scope.frozen_test_candidate_count = 0;
schema12BlockPayload.scope.test_cell_count = 0;
schema12BlockPayload.scope.forward_candidate_count = 0;
schema12BlockPayload.preregistered_failure_admission_status = "BLOCK";
schema12BlockPayload.evidence_contract.preregistered_failure_admission_status = "BLOCK";
schema12BlockPayload.preregistered_failure_admission.status = "BLOCK";
schema12BlockPayload.preregistered_failure_admission.selected_strategy_admitted_count = 0;
schema12BlockPayload.preregistered_failure_admission.admitted_candidate_count = 0;
schema12BlockPayload.preregistered_failure_admission.blockers = [
  "other_strategy:parameter_plateau_absent",
];
schema12BlockPayload.post_selection_replay_summary = postSelectionSummary(
  12,
  "NOT_RUN",
  "NOT_RUN",
);
schema12BlockPayload.post_selection_replay_status = "NOT_RUN";
schema12BlockPayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
bindPostSelectionFailureV2(schema12BlockPayload);
const schema12Block = evidence.strategyLabEvidencePresentation(schema12BlockPayload);
assert.equal(schema12Block.valid, true);
assert.equal(schema12Block.rawAdmissionStatus, "BLOCK");
assert.equal(schema12Block.admissionText, "事前 BLOCK_RESEARCH 条件已触发 · 本批未冻结候选");
assert.equal(schema12Block.rawPostSelectionStatus, "NOT_RUN");
assert.ok(schema12Block.frozenTestText.includes("未运行"));
assert.ok(schema12Block.frozenTestText.includes("未形成历史收益数字"));
assert.ok(!schema12Block.frozenTestText.includes("0.00%"));

const schema12NoCandidatePayload = JSON.parse(JSON.stringify(schema12PassPayload));
schema12NoCandidatePayload.scope.strategy_count = 2;
schema12NoCandidatePayload.scope.forward_candidate_count = 0;
schema12NoCandidatePayload.preregistered_failure_admission.selected_strategy_candidate_count = 0;
schema12NoCandidatePayload.preregistered_failure_admission.selected_strategy_admitted_count = 0;
schema12NoCandidatePayload.preregistered_failure_admission.checks[1].status = "NOT_APPLICABLE";
schema12NoCandidatePayload.preregistered_failure_admission.checks[2].status = "NOT_APPLICABLE";
schema12NoCandidatePayload.post_selection_replay_summary = postSelectionSummary(
  12,
  "NOT_RUN",
  "NOT_RUN",
);
schema12NoCandidatePayload.post_selection_replay_status = "NOT_RUN";
schema12NoCandidatePayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
bindPostSelectionFailureV2(schema12NoCandidatePayload);
const schema12NoCandidate = evidence.strategyLabEvidencePresentation(schema12NoCandidatePayload);
assert.equal(schema12NoCandidate.valid, true);
assert.equal(schema12NoCandidate.rawAdmissionStatus, "PASS");
assert.ok(schema12NoCandidate.admissionText.includes("当前策略未进入本批冻结候选"));
assert.ok(schema12NoCandidate.admissionText.includes("非选参授权"));

const schema13MechanismCondition = {
  condition_id: "validation_edge_lost",
  evidence_stage: "DEVELOPMENT_SELECTION",
  metric: "median_validation_excess_return_pct",
  operator: "LTE",
  threshold: 0,
  required_action: "BLOCK_RESEARCH",
};

function bindFailureV3(payload) {
  const failure = payload.failure_conditions;
  failure.schema_version = "strategy-research-failure-conditions-v3";
  failure.preregistered_failure_admission_status = payload.preregistered_failure_admission.status;
  if (payload.strategy_match_status === "NOT_IN_REPORT") return;
  const admission = payload.preregistered_failure_admission;
  const appended = [[
    "preregistered_failure_admission_blocked",
    admission.status,
    admission.status === "PASS" ? false : true,
    [...admission.blockers],
  ]];
  for (const check of admission.checks.filter((item) => item.condition_kind === "MECHANISM_SPECIFIC")) {
    appended.push([
      `mechanism_failure:${check.condition_id}`,
      check.status,
      check.status === "PASS" && check.triggered === false
        ? false
        : check.status === "BLOCK" && check.triggered === true
          ? true
          : null,
      [...check.blockers],
    ]);
  }
  for (const check of admission.future_standard_checks) {
    appended.push([
      `future_standard_failure:${check.condition_id}`,
      check.status,
      null,
      [...check.blockers],
    ]);
  }
  for (const [conditionId, evidenceStatus, triggered, blockers] of appended) {
    failure.conditions.push({
      condition_id: conditionId,
      evidence_status: evidenceStatus,
      triggered,
      blockers,
    });
    if (triggered === true) failure.observed.push(conditionId);
    if (triggered === null) failure.evidence_gaps.push(`${conditionId}_not_checked`);
  }
  failure.observed = [...new Set(failure.observed)];
  failure.evidence_gaps = [...new Set(failure.evidence_gaps)];
  failure.status = failure.observed.length ? "TRIGGERED" : "GAPS";
}

function makeSchema13Payload() {
  const payload = JSON.parse(JSON.stringify(schema12PassPayload));
  payload.report_schema_version = 13;
  payload.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v6";
  payload.evidence_contract.hypothesis_preregistration_schema_version =
    "strategy-hypothesis-preregistration-v2";
  payload.evidence_contract.preregistered_failure_admission_schema_version =
    "strategy-preregistered-failure-admission-v2";
  payload.evidence_contract.failure_conditions_schema_version =
    "strategy-research-failure-conditions-v3";
  payload.hypothesis_preregistration.schema_version =
    "strategy-hypothesis-preregistration-summary-v2";
  payload.hypothesis_preregistration.source_schema_version =
    "strategy-hypothesis-preregistration-v2";
  payload.hypothesis_preregistration.hypothesis_id = "frozen-causal-persistence-v2";
  payload.hypothesis_preregistration.mechanism_specific_failure_conditions = [
    { ...schema13MechanismCondition },
  ];
  delete payload.hypothesis_preregistration.hypothesis_statement;
  delete payload.hypothesis_preregistration.novelty_statement;
  payload.post_selection_replay_summary.report_schema_version = 13;
  payload.preregistered_failure_admission = {
    descriptive_only: true,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    automatic_paper_activation_allowed: false,
    research_only: true,
    paper_authorized: false,
    live_order_allowed: false,
    schema_version: "strategy-preregistered-failure-admission-v2",
    status: "PASS",
    admission_scope: "HYPOTHESIS_BATCH",
    hypothesis_id: "frozen-causal-persistence-v2",
    selected_strategy_status: "PASS",
    selected_strategy_candidate_count: 1,
    selected_strategy_admitted_count: 1,
    admitted_candidate_count: 1,
    mechanism_condition_ids: ["validation_edge_lost"],
    checks: [
      ...[
        "parameter_plateau_absent",
        "cost_break_even_lost",
        "fixed_parameter_time_slice_instability",
      ].map((conditionId) => ({
        condition_id: conditionId,
        condition_kind: "STANDARD",
        evidence_stage: "DEVELOPMENT_SELECTION",
        required_action: "BLOCK_RESEARCH",
        status: "PASS",
        triggered: false,
        blockers: [],
      })),
      {
        ...schema13MechanismCondition,
        condition_kind: "MECHANISM_SPECIFIC",
        status: "PASS",
        triggered: false,
        blockers: [],
        metric_value: 0.4,
      },
    ],
    future_standard_checks: [
      {
        condition_id: "fresh_single_use_holdout_failure",
        condition_kind: "STANDARD",
        evidence_stage: "PREREGISTERED_BLIND_SINGLE_USE",
        required_action: "RETIRE_OR_NEW_REGISTRATION",
        status: "NOT_DUE",
        triggered: false,
        blockers: [],
      },
      {
        condition_id: "natural_forward_statistical_failure",
        condition_kind: "STANDARD",
        evidence_stage: "NATURAL_FORWARD_MATURITY",
        required_action: "RETIRE_HYPOTHESIS",
        status: "NOT_DUE",
        triggered: false,
        blockers: [],
      },
    ],
    blockers: [],
  };
  payload.preregistered_failure_admission_status = "PASS";
  payload.evidence_contract.preregistered_failure_admission_status = "PASS";
  bindFailureV3(payload);
  return payload;
}

function bindFailureV4(payload) {
  const failure = payload.failure_conditions;
  failure.schema_version = "strategy-research-failure-conditions-v4";
  failure.search_lineage_status = payload.search_lineage.status;
  if (payload.strategy_match_status === "NOT_IN_REPORT") return;
  const lineageStatus = payload.search_lineage.status;
  const triggered = lineageStatus === "BOUND" ? false : lineageStatus === "BLOCK" ? true : null;
  const conditionId = "search_lineage_live_at_selection_not_verified";
  failure.conditions.push({
    condition_id: conditionId,
    evidence_status: lineageStatus,
    triggered,
    blockers: [...payload.search_lineage.blockers],
  });
  if (triggered === true) failure.observed.push(conditionId);
  if (triggered === null) failure.evidence_gaps.push(`${conditionId}_not_checked`);
  failure.observed = [...new Set(failure.observed)];
  failure.evidence_gaps = [...new Set(failure.evidence_gaps)];
  failure.status = failure.observed.length ? "TRIGGERED" : "GAPS";
}

function makeSchema14Payload() {
  const payload = makeSchema13Payload();
  payload.report_schema_version = 14;
  payload.scope.frozen_test_candidate_count = 0;
  payload.scope.test_cell_count = 0;
  payload.scope.forward_candidate_count = 0;
  payload.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v7";
  payload.evidence_contract.hypothesis_preregistration_schema_version =
    "strategy-hypothesis-preregistration-v3";
  payload.evidence_contract.preregistered_failure_admission_schema_version =
    "strategy-preregistered-failure-admission-v3";
  payload.evidence_contract.failure_conditions_schema_version =
    "strategy-research-failure-conditions-v4";
  payload.evidence_contract.search_lineage_schema_version =
    "strategy-research-search-lineage-public-v1";
  payload.evidence_contract.search_lineage_status = "BOUND";
  payload.hypothesis_preregistration.schema_version =
    "strategy-hypothesis-preregistration-summary-v3";
  payload.hypothesis_preregistration.source_schema_version =
    "strategy-hypothesis-preregistration-v3";
  payload.hypothesis_preregistration.search_family_bound = true;
  payload.post_selection_replay_summary = postSelectionSummary(14, "NOT_RUN", "NOT_RUN");
  payload.post_selection_replay_status = "NOT_RUN";
  payload.evidence_contract.post_selection_replay_status = "NOT_RUN";
  payload.preregistered_failure_admission.schema_version =
    "strategy-preregistered-failure-admission-v3";
  payload.preregistered_failure_admission.status = "BLOCK";
  payload.preregistered_failure_admission.selected_strategy_status = "BLOCK";
  payload.preregistered_failure_admission.selected_strategy_candidate_count = 1;
  payload.preregistered_failure_admission.selected_strategy_admitted_count = 0;
  payload.preregistered_failure_admission.admitted_candidate_count = 0;
  payload.preregistered_failure_admission.checks = [{
    ...schema13MechanismCondition,
    condition_kind: "MECHANISM_SPECIFIC",
    status: "BLOCK",
    triggered: true,
    blockers: ["mechanism_condition_triggered"],
    metric_value: -0.25,
  }];
  payload.preregistered_failure_admission.blockers = [
    "preregistered_failure_admission_blocked",
  ];
  payload.preregistered_failure_admission.search_lineage_status = "BOUND";
  payload.preregistered_failure_admission_status = "BLOCK";
  payload.evidence_contract.preregistered_failure_admission_status = "BLOCK";
  payload.search_lineage_status = "BOUND";
  payload.search_lineage = {
    schema_version: "strategy-research-search-lineage-public-v1",
    descriptive_only: true,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    automatic_paper_activation_allowed: false,
    research_only: true,
    paper_authorized: false,
    live_order_allowed: false,
    status: "BOUND",
    family_bound: true,
    trial_count_scope: "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
    prior_trial_count: 5,
    current_trial_count: 3,
    cumulative_trial_count: 8,
    selection_binding_scope: "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT",
    offline_verification_scope:
      "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY",
    admission_status: "BLOCK",
    blockers: [],
  };
  payload.failure_conditions = JSON.parse(
    JSON.stringify(frozenStrategyLabPayload.failure_conditions),
  );
  bindPostSelectionFailureV2(payload);
  bindFailureV3(payload);
  bindFailureV4(payload);
  return payload;
}

const schema13PassPayload = makeSchema13Payload();
const schema13Pass = evidence.strategyLabEvidencePresentation(schema13PassPayload);
assert.equal(schema13Pass.valid, true);
assert.equal(schema13Pass.rawAdmissionStatus, "PASS");
assert.equal(schema13Pass.rawMechanismStatus, "PASS");
assert.equal(schema13Pass.rawFutureConditionStatus, "NOT_DUE");
assert.ok(schema13Pass.mechanismConditionText.includes("适用开发期条件未触发"));
assert.ok(schema13Pass.futureConditionText.includes("未评估、非通过"));
assert.ok(!schema13Pass.futureConditionText.includes("PASS"));
assert.ok(schema13Pass.hypothesisFailureText.includes("结构化机制失效条件 1 项"));
assert.deepEqual(schema13Pass.mechanismConditionRows, [{
  conditionId: "validation_edge_lost",
  predicateText: "验证超额中位数 ≤ 0.00%",
  observationText: "观测 +0.40%",
  outcomeText: "未触发",
  boundaryText: "仅进入历史研究 · 不授权",
  rawStatus: "PASS",
}]);
assert.deepEqual(schema13Pass.futureConditionRows, [
  {
    conditionId: "fresh_single_use_holdout_failure",
    stageText: "单次新鲜留出",
    outcomeText: "未到期 · 未评估、非通过",
    boundaryText: "到期触发时：退役或新登记",
    rawStatus: "NOT_DUE",
  },
  {
    conditionId: "natural_forward_statistical_failure",
    stageText: "自然前向成熟度",
    outcomeText: "未到期 · 未评估、非通过",
    boundaryText: "到期触发时：退役假设",
    rawStatus: "NOT_DUE",
  },
]);
assert.equal(Object.isFrozen(schema13Pass.mechanismConditionRows), true);
assert.equal(Object.isFrozen(schema13Pass.mechanismConditionRows[0]), true);
assert.equal(Object.isFrozen(schema13Pass.futureConditionRows), true);
assert.equal(Object.isFrozen(schema13Pass.futureConditionRows[0]), true);
assert.ok(schema13Pass.futureConditionRows.every((row) => !row.outcomeText.includes("PASS")));

const schema14PassPayload = makeSchema14Payload();
const schema14Pass = evidence.strategyLabEvidencePresentation(schema14PassPayload);
assert.equal(schema14Pass.valid, true);
assert.equal(schema14Pass.rawSearchLineageStatus, "BOUND");
assert.ok(schema14Pass.lineageText.includes("选择时核验；当前仅离线报告/回执自洽"));
assert.ok(schema14Pass.lineageText.includes("既往 5 + 本批 3 = 累计 8 次"));
assert.ok(!/(?:family|hash|path|candidate|实时数据库)/i.test(schema14Pass.lineageText));

const realSchema14Snapshots = projectRealSchema14Snapshots();
const realSchema14Admission = realSchema14Snapshots.bound.preregistered_failure_admission;
assert.equal(realSchema14Snapshots.bound.evidence_contract.schema_version, "strategy-lab-frozen-evidence-v7");
assert.equal(realSchema14Admission.schema_version, "strategy-preregistered-failure-admission-v3");
assert.deepEqual(realSchema14Admission.mechanism_condition_ids, ["validation_edge_lost"]);
assert.equal(realSchema14Admission.checks.length, 1);
assert.equal(realSchema14Admission.checks[0].condition_kind, "MECHANISM_SPECIFIC");
assert.ok(realSchema14Admission.checks.every((check) => check.condition_kind !== "STANDARD"));
assert.equal(realSchema14Admission.future_standard_checks.length, 2);
assert.ok(
  realSchema14Admission.future_standard_checks.every(
    (check) => check.condition_kind === "STANDARD" && check.status === "NOT_DUE",
  ),
);
const realSchema14Bound = evidence.strategyLabEvidencePresentation(realSchema14Snapshots.bound);
assert.equal(realSchema14Bound.valid, true);
assert.equal(realSchema14Bound.rawSearchLineageStatus, "BOUND");
const realSchema14FullImplementation = realSchema14Snapshots.bound.full_implementation_currentness;
assert.deepEqual(realSchema14FullImplementation, {
  schema_version: "strategy-full-implementation-currentness-v1",
  status: "NOT_AVAILABLE",
  basis: "FROZEN_IMPLEMENTATION_MANIFEST_EXACT_FILES_AND_RUNTIME",
  checked: false,
  matches_current: null,
  expected_source_count: 0,
  verified_source_count: 0,
  exact_files_checked: false,
  runtime_checked: false,
  blockers: ["research_report_does_not_embed_full_implementation_manifest"],
  research_only: true,
  paper_authorized: false,
  live_order_allowed: false,
});
const realSchema14ClosureCondition = realSchema14Snapshots.bound.failure_conditions.conditions.find(
  (condition) => condition.condition_id === "research_implementation_closure_changed",
);
assert.deepEqual(realSchema14ClosureCondition, {
  condition_id: "research_implementation_closure_changed",
  evidence_status: "NOT_AVAILABLE",
  triggered: null,
  blockers: ["research_report_does_not_embed_full_implementation_manifest"],
});
assert.ok(
  realSchema14Snapshots.bound.failure_conditions.evidence_gaps.includes(
    "research_implementation_closure_changed_not_checked",
  ),
);
for (const [name, mutate] of [
  ["missing full implementation blocker", (snapshot) => {
    snapshot.full_implementation_currentness.blockers = [];
    snapshot.failure_conditions.conditions.find(
      (condition) => condition.condition_id === "research_implementation_closure_changed",
    ).blockers = [];
  }],
  ["wrong full implementation blocker", (snapshot) => {
    const forgedBlockers = ["private_manifest_claim_not_in_public_contract"];
    snapshot.full_implementation_currentness.blockers = [...forgedBlockers];
    snapshot.failure_conditions.conditions.find(
      (condition) => condition.condition_id === "research_implementation_closure_changed",
    ).blockers = [...forgedBlockers];
  }],
  ["nonzero full implementation counts", (snapshot) => {
    snapshot.full_implementation_currentness.expected_source_count = 1;
    snapshot.full_implementation_currentness.verified_source_count = 1;
  }],
  ["exact files falsely checked", (snapshot) => {
    snapshot.full_implementation_currentness.exact_files_checked = true;
  }],
  ["runtime falsely checked", (snapshot) => {
    snapshot.full_implementation_currentness.runtime_checked = true;
  }],
  ["missing full implementation evidence gap", (snapshot) => {
    snapshot.failure_conditions.evidence_gaps = snapshot.failure_conditions.evidence_gaps.filter(
      (gap) => gap !== "research_implementation_closure_changed_not_checked",
    );
  }],
]) {
  const forged = JSON.parse(JSON.stringify(realSchema14Snapshots.bound));
  mutate(forged);
  const presentation = evidence.strategyLabEvidencePresentation(forged);
  assert.equal(presentation.valid, false, `real schema14 ${name} must fail closed`);
  assert.equal(presentation.connectionStatus, "UNKNOWN");
}
for (const [name, snapshot] of [
  ["receipt-only", realSchema14Snapshots.receipt_only],
  ["private-lineage-drift", realSchema14Snapshots.drift],
]) {
  const presentation = evidence.strategyLabEvidencePresentation(snapshot);
  assert.equal(presentation.valid, false, `real schema14 ${name} must fail closed`);
  assert.equal(presentation.connectionStatus, "UNKNOWN");
  assert.equal(presentation.rawSearchLineageStatus, "UNKNOWN");
}

const unsafePublicCount = Number.MAX_SAFE_INTEGER + 1;
const assertUnsafePublicCountFailsClosed = (payload, label) => {
  const presentation = evidence.strategyLabEvidencePresentation(payload);
  assert.equal(presentation.valid, false, `${label} must reject an unsafe public count`);
  assert.equal(presentation.connectionStatus, "UNKNOWN");
  assert.equal(presentation.rawPostSelectionStatus, "UNKNOWN");
  assert.ok(
    !JSON.stringify(presentation).includes(String(unsafePublicCount)),
    `${label} must not expose the rejected count`,
  );
};

const schema14UnsafeTotalTrades = makeSchema14Payload();
schema14UnsafeTotalTrades.post_selection_replay_summary.frozen_test.total_trades =
  unsafePublicCount;
assertUnsafePublicCountFailsClosed(schema14UnsafeTotalTrades, "schema14 replay total_trades");

const schema14UnsafeReplayCounts = makeSchema14Payload();
for (const field of [
  "cell_count",
  "replay_verified_cell_count",
  "replay_pass_cell_count",
  "fixed_slice_pass_cell_count",
  "prefix_invariance_pass_cell_count",
  "lookahead_pass_cell_count",
]) {
  schema14UnsafeReplayCounts.post_selection_replay_summary.holdout_confirmation[field] =
    unsafePublicCount;
}
assertUnsafePublicCountFailsClosed(schema14UnsafeReplayCounts, "schema14 replay stage counts");

const schema14UnsafeImplementationCounts = makeSchema14Payload();
schema14UnsafeImplementationCounts.implementation_currentness.frozen_variant_count =
  unsafePublicCount;
schema14UnsafeImplementationCounts.implementation_currentness.matched_variant_count =
  unsafePublicCount;
assertUnsafePublicCountFailsClosed(
  schema14UnsafeImplementationCounts,
  "schema14 signal implementation counts",
);

const schema14UnsafeFullImplementationCounts = makeSchema14Payload();
schema14UnsafeFullImplementationCounts.full_implementation_currentness.expected_source_count =
  unsafePublicCount;
schema14UnsafeFullImplementationCounts.full_implementation_currentness.verified_source_count =
  unsafePublicCount;
assertUnsafePublicCountFailsClosed(
  schema14UnsafeFullImplementationCounts,
  "schema14 full implementation counts",
);

const legacyV5UnsafeCount = JSON.parse(JSON.stringify(schema11PassPayload));
legacyV5UnsafeCount.post_selection_replay_summary.frozen_test.total_trades = unsafePublicCount;
assertUnsafePublicCountFailsClosed(legacyV5UnsafeCount, "legacy v5 replay total_trades");

const legacyV6UnsafeCount = makeSchema13Payload();
legacyV6UnsafeCount.full_implementation_currentness.expected_source_count = unsafePublicCount;
legacyV6UnsafeCount.full_implementation_currentness.verified_source_count = unsafePublicCount;
assertUnsafePublicCountFailsClosed(legacyV6UnsafeCount, "legacy v6 implementation counts");

const legacyV6NotAvailable = makeSchema13Payload();
Object.assign(legacyV6NotAvailable.full_implementation_currentness, {
  status: "NOT_AVAILABLE",
  checked: false,
  matches_current: null,
  expected_source_count: 0,
  verified_source_count: 0,
  exact_files_checked: false,
  runtime_checked: false,
  blockers: ["research_report_does_not_embed_full_implementation_manifest"],
});
legacyV6NotAvailable.full_implementation_manifest_checked = false;
legacyV6NotAvailable.full_implementation_manifest_status = "NOT_AVAILABLE";
legacyV6NotAvailable.full_implementation_manifest_match = null;
legacyV6NotAvailable.evidence_contract.full_implementation_manifest_checked = false;
legacyV6NotAvailable.evidence_contract.full_implementation_manifest_status = "NOT_AVAILABLE";
legacyV6NotAvailable.evidence_contract.full_implementation_manifest_match = null;
const legacyV6ClosureCondition = legacyV6NotAvailable.failure_conditions.conditions.find(
  (condition) => condition.condition_id === "research_implementation_closure_changed",
);
legacyV6ClosureCondition.evidence_status = "NOT_AVAILABLE";
legacyV6ClosureCondition.triggered = null;
legacyV6ClosureCondition.blockers = [
  "research_report_does_not_embed_full_implementation_manifest",
];
legacyV6NotAvailable.failure_conditions.evidence_gaps.push(
  "research_implementation_closure_changed_not_checked",
);
assert.equal(
  evidence.strategyLabEvidencePresentation(legacyV6NotAvailable).valid,
  false,
  "legacy schema13/v6 must keep rejecting NOT_AVAILABLE full implementation evidence",
);

for (const historical of [frozenStrategyLab, schema11Pass, schema12Pass, schema13Pass]) {
  assert.equal(historical.rawSearchLineageStatus, "NOT_AVAILABLE");
  assert.equal(historical.lineageText, "历史报告未封存检索谱系 · 不补写选择时核验结论");
}

for (const [name, mutate] of [
  ["zero-current", (payload) => { payload.search_lineage.current_trial_count = 0; }],
  ["unsafe-prior", (payload) => {
    payload.search_lineage.prior_trial_count = Number.MAX_SAFE_INTEGER + 1;
    payload.search_lineage.cumulative_trial_count = Number.MAX_SAFE_INTEGER + 4;
  }],
  ["cumulative-mismatch", (payload) => { payload.search_lineage.cumulative_trial_count = 9; }],
  ["receipt-only", (payload) => {
    payload.search_lineage.selection_binding_scope = "SELF_CONSISTENT_RECEIPT_ONLY";
  }],
  ["family-unbound", (payload) => { payload.search_lineage.family_bound = false; }],
  ["root-status-mismatch", (payload) => { payload.search_lineage_status = "BLOCK"; }],
  ["contract-status-mismatch", (payload) => {
    payload.evidence_contract.search_lineage_status = "BLOCK";
  }],
  ["admission-status-mismatch", (payload) => {
    payload.preregistered_failure_admission.search_lineage_status = "BLOCK";
  }],
  ["failure-status-mismatch", (payload) => {
    payload.failure_conditions.search_lineage_status = "BLOCK";
  }],
]) {
  const forged = makeSchema14Payload();
  mutate(forged);
  const result = evidence.strategyLabEvidencePresentation(forged);
  assert.equal(result.valid, false, `schema14 ${name} must fail closed`);
  assert.equal(result.rawSearchLineageStatus, "UNKNOWN");
}

for (const privateField of ["search_family_id", "lineage_hash", "registry_path", "candidate_id"]) {
  const forged = makeSchema14Payload();
  forged.search_lineage[privateField] = "must-not-reach-ui";
  assert.equal(
    evidence.strategyLabEvidencePresentation(forged).valid,
    false,
    `schema14 private lineage field ${privateField} must fail exactKeys`,
  );
}

for (const authorityAlias of ["canTrade", "paperReady", "可下单", "实盘-授权"]) {
  const forged = makeSchema14Payload();
  forged.search_lineage.nested_authority = { [authorityAlias]: true };
  assert.equal(
    evidence.strategyLabEvidencePresentation(forged).valid,
    false,
    `schema14 lineage authority alias ${authorityAlias} must fail closed`,
  );
}

const schema14ExtraContractField = makeSchema14Payload();
schema14ExtraContractField.evidence_contract.private_lineage_hash = "9".repeat(64);
assert.equal(evidence.strategyLabEvidencePresentation(schema14ExtraContractField).valid, false);
const schema14HypothesisV2Downgrade = makeSchema14Payload();
schema14HypothesisV2Downgrade.hypothesis_preregistration.schema_version =
  "strategy-hypothesis-preregistration-summary-v2";
assert.equal(evidence.strategyLabEvidencePresentation(schema14HypothesisV2Downgrade).valid, false);
const schema14AdmissionV2Downgrade = makeSchema14Payload();
schema14AdmissionV2Downgrade.preregistered_failure_admission.schema_version =
  "strategy-preregistered-failure-admission-v2";
assert.equal(evidence.strategyLabEvidencePresentation(schema14AdmissionV2Downgrade).valid, false);
const schema14FailureV3Downgrade = makeSchema14Payload();
schema14FailureV3Downgrade.failure_conditions.schema_version =
  "strategy-research-failure-conditions-v3";
assert.equal(evidence.strategyLabEvidencePresentation(schema14FailureV3Downgrade).valid, false);
const schema14PostSelectionWrongReport = makeSchema14Payload();
schema14PostSelectionWrongReport.post_selection_replay_summary.report_schema_version = 13;
assert.equal(evidence.strategyLabEvidencePresentation(schema14PostSelectionWrongReport).valid, false);
const retiredEvidenceV4 = makeSchema14Payload();
retiredEvidenceV4.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v4";
assert.equal(evidence.strategyLabEvidencePresentation(retiredEvidenceV4).valid, false);
const unknownReport15 = makeSchema14Payload();
unknownReport15.report_schema_version = 15;
unknownReport15.post_selection_replay_summary.report_schema_version = 15;
assert.equal(evidence.strategyLabEvidencePresentation(unknownReport15).valid, false);

const schema13CountMetricPayload = makeSchema13Payload();
Object.assign(
  schema13CountMetricPayload.hypothesis_preregistration.mechanism_specific_failure_conditions[0],
  { metric: "validation_trade_count", operator: "LT", threshold: 12 },
);
Object.assign(
  schema13CountMetricPayload.preregistered_failure_admission.checks.at(-1),
  { metric: "validation_trade_count", operator: "LT", threshold: 12, metric_value: 18 },
);
const schema13CountMetric = evidence.strategyLabEvidencePresentation(schema13CountMetricPayload);
assert.equal(schema13CountMetric.valid, true);
assert.equal(schema13CountMetric.mechanismConditionRows[0].predicateText, "验证交易数 < 12 笔");
assert.equal(schema13CountMetric.mechanismConditionRows[0].observationText, "观测 18 笔");

const schema13ScoreMetricPayload = makeSchema13Payload();
Object.assign(
  schema13ScoreMetricPayload.hypothesis_preregistration.mechanism_specific_failure_conditions[0],
  { metric: "validation_adjusted_score", threshold: 0.125 },
);
Object.assign(
  schema13ScoreMetricPayload.preregistered_failure_admission.checks.at(-1),
  { metric: "validation_adjusted_score", threshold: 0.125, metric_value: 0.4 },
);
const schema13ScoreMetric = evidence.strategyLabEvidencePresentation(schema13ScoreMetricPayload);
assert.equal(schema13ScoreMetric.valid, true);
assert.equal(schema13ScoreMetric.mechanismConditionRows[0].predicateText, "验证调整分 ≤ 0.1250");
assert.equal(schema13ScoreMetric.mechanismConditionRows[0].observationText, "观测 +0.4000");

const schema13TriggeredPayload = JSON.parse(JSON.stringify(schema13PassPayload));
schema13TriggeredPayload.scope.frozen_test_candidate_count = 0;
schema13TriggeredPayload.scope.test_cell_count = 0;
schema13TriggeredPayload.scope.forward_candidate_count = 0;
schema13TriggeredPayload.preregistered_failure_admission_status = "BLOCK";
schema13TriggeredPayload.evidence_contract.preregistered_failure_admission_status = "BLOCK";
schema13TriggeredPayload.preregistered_failure_admission.status = "BLOCK";
schema13TriggeredPayload.preregistered_failure_admission.selected_strategy_status = "BLOCK";
schema13TriggeredPayload.preregistered_failure_admission.selected_strategy_admitted_count = 0;
schema13TriggeredPayload.preregistered_failure_admission.admitted_candidate_count = 0;
schema13TriggeredPayload.preregistered_failure_admission.blockers = [
  "preregistered_failure_admission_blocked",
];
const schema13TriggeredCheck = schema13TriggeredPayload.preregistered_failure_admission.checks.at(-1);
schema13TriggeredCheck.status = "BLOCK";
schema13TriggeredCheck.triggered = true;
schema13TriggeredCheck.metric_value = -0.25;
schema13TriggeredCheck.blockers = ["mechanism_condition_triggered"];
schema13TriggeredPayload.post_selection_replay_summary = postSelectionSummary(
  13,
  "NOT_RUN",
  "NOT_RUN",
);
schema13TriggeredPayload.post_selection_replay_status = "NOT_RUN";
schema13TriggeredPayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
schema13TriggeredPayload.failure_conditions = JSON.parse(
  JSON.stringify(schema12BlockPayload.failure_conditions),
);
schema13TriggeredPayload.failure_conditions.conditions =
  schema13TriggeredPayload.failure_conditions.conditions.filter(
    (condition) => !condition.condition_id.endsWith("_replay_not_preserved"),
  );
schema13TriggeredPayload.failure_conditions.observed = [];
schema13TriggeredPayload.failure_conditions.evidence_gaps = [
  "dataset_currentness_not_checked",
  "report_age_policy_not_checked",
  "natural_forward_performance_not_proven_by_strategy_report",
  "frozen_test_replay_not_preserved_not_checked",
  "holdout_confirmation_replay_not_preserved_not_checked",
];
bindPostSelectionFailureV2(schema13TriggeredPayload);
bindFailureV3(schema13TriggeredPayload);
const schema13Triggered = evidence.strategyLabEvidencePresentation(schema13TriggeredPayload);
assert.equal(schema13Triggered.valid, true);
assert.equal(schema13Triggered.rawMechanismStatus, "BLOCK");
assert.ok(schema13Triggered.mechanismConditionText.includes("已触发 1 项"));
assert.equal(schema13Triggered.mechanismConditionRows[0].observationText, "观测 -0.25%");
assert.equal(schema13Triggered.mechanismConditionRows[0].outcomeText, "已触发 · 阻断后续研究");
assert.equal(schema13Triggered.mechanismConditionRows[0].boundaryText, "不得进入冻结后历史复算");

const schema13ForgedPredicate = JSON.parse(JSON.stringify(schema13PassPayload));
schema13ForgedPredicate.preregistered_failure_admission.checks.at(-1).metric_value = -0.25;
assert.equal(evidence.strategyLabEvidencePresentation(schema13ForgedPredicate).valid, false);
const schema13ForgedFuturePass = JSON.parse(JSON.stringify(schema13PassPayload));
schema13ForgedFuturePass.preregistered_failure_admission.future_standard_checks[0].status = "PASS";
assert.equal(evidence.strategyLabEvidencePresentation(schema13ForgedFuturePass).valid, false);
const schema13ExtraConditionField = JSON.parse(JSON.stringify(schema13PassPayload));
schema13ExtraConditionField.hypothesis_preregistration
  .mechanism_specific_failure_conditions[0].private_note = "must-not-enter-public-contract";
assert.equal(evidence.strategyLabEvidencePresentation(schema13ExtraConditionField).valid, false);
const schema13AdmissionBindingMismatch = JSON.parse(JSON.stringify(schema13PassPayload));
schema13AdmissionBindingMismatch.preregistered_failure_admission.checks.at(-1).threshold = -1;
assert.equal(evidence.strategyLabEvidencePresentation(schema13AdmissionBindingMismatch).valid, false);
const schema13ExtraAdmissionField = JSON.parse(JSON.stringify(schema13PassPayload));
schema13ExtraAdmissionField.preregistered_failure_admission.private_candidate_id = "must-not-leak";
assert.equal(evidence.strategyLabEvidencePresentation(schema13ExtraAdmissionField).valid, false);
const schema13WrongFutureAction = JSON.parse(JSON.stringify(schema13PassPayload));
schema13WrongFutureAction.preregistered_failure_admission
  .future_standard_checks[1].required_action = "BLOCK_RESEARCH";
assert.equal(evidence.strategyLabEvidencePresentation(schema13WrongFutureAction).valid, false);
const schema13ForgedNotDueFailurePass = JSON.parse(JSON.stringify(schema13PassPayload));
schema13ForgedNotDueFailurePass.failure_conditions.conditions.find(
  (condition) => condition.condition_id
    === "future_standard_failure:fresh_single_use_holdout_failure",
).triggered = false;
assert.equal(evidence.strategyLabEvidencePresentation(schema13ForgedNotDueFailurePass).valid, false);

const schema13NoCandidatePayload = JSON.parse(JSON.stringify(schema13PassPayload));
schema13NoCandidatePayload.scope.strategy_count = 2;
schema13NoCandidatePayload.hypothesis_preregistration.strategy_ids.push("other_strategy");
schema13NoCandidatePayload.preregistered_failure_admission.selected_strategy_candidate_count = 0;
schema13NoCandidatePayload.preregistered_failure_admission.selected_strategy_admitted_count = 0;
schema13NoCandidatePayload.preregistered_failure_admission.checks[1].status = "NOT_APPLICABLE";
schema13NoCandidatePayload.preregistered_failure_admission.checks[2].status = "NOT_APPLICABLE";
const schema13NoCandidateMechanism = schema13NoCandidatePayload
  .preregistered_failure_admission.checks.at(-1);
schema13NoCandidateMechanism.status = "NOT_APPLICABLE";
schema13NoCandidateMechanism.triggered = false;
schema13NoCandidateMechanism.metric_value = null;
schema13NoCandidateMechanism.blockers = [];
schema13NoCandidatePayload.post_selection_replay_summary = postSelectionSummary(
  13,
  "NOT_RUN",
  "NOT_RUN",
);
schema13NoCandidatePayload.post_selection_replay_status = "NOT_RUN";
schema13NoCandidatePayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
schema13NoCandidatePayload.failure_conditions = JSON.parse(
  JSON.stringify(schema13PassPayload.failure_conditions),
);
schema13NoCandidatePayload.failure_conditions.conditions =
  schema13NoCandidatePayload.failure_conditions.conditions.filter(
    (condition) => ![
      "frozen_test_replay_not_preserved",
      "holdout_confirmation_replay_not_preserved",
      "preregistered_failure_admission_blocked",
      "mechanism_failure:validation_edge_lost",
      "future_standard_failure:fresh_single_use_holdout_failure",
      "future_standard_failure:natural_forward_statistical_failure",
    ].includes(condition.condition_id),
  );
schema13NoCandidatePayload.failure_conditions.observed = [];
schema13NoCandidatePayload.failure_conditions.evidence_gaps = [
  "dataset_currentness_not_checked",
  "report_age_policy_not_checked",
  "natural_forward_performance_not_proven_by_strategy_report",
];
bindPostSelectionFailureV2(schema13NoCandidatePayload);
bindFailureV3(schema13NoCandidatePayload);
const schema13NoCandidate = evidence.strategyLabEvidencePresentation(schema13NoCandidatePayload);
assert.equal(schema13NoCandidate.valid, true);
assert.equal(schema13NoCandidate.rawMechanismStatus, "NOT_APPLICABLE");
assert.ok(schema13NoCandidate.mechanismConditionText.includes("未形成通过结论"));
assert.equal(schema13NoCandidate.mechanismConditionRows[0].observationText, "观测 --");
assert.equal(schema13NoCandidate.mechanismConditionRows[0].outcomeText, "不适用 · 未形成通过结论");
assert.equal(schema13NoCandidate.mechanismConditionRows[0].boundaryText, "当前无候选 · 不选参、不授权");

const v5Schema13Downgrade = JSON.parse(JSON.stringify(schema13PassPayload));
v5Schema13Downgrade.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v5";
assert.equal(evidence.strategyLabEvidencePresentation(v5Schema13Downgrade).valid, false);
const v6Schema12Backport = JSON.parse(JSON.stringify(schema13PassPayload));
v6Schema12Backport.report_schema_version = 12;
v6Schema12Backport.post_selection_replay_summary.report_schema_version = 12;
assert.equal(evidence.strategyLabEvidencePresentation(v6Schema12Backport).valid, false);
const unsupportedSchema14 = JSON.parse(JSON.stringify(schema13PassPayload));
unsupportedSchema14.report_schema_version = 14;
unsupportedSchema14.post_selection_replay_summary.report_schema_version = 14;
assert.equal(evidence.strategyLabEvidencePresentation(unsupportedSchema14).valid, false);

const schema13NotInReportPayload = JSON.parse(JSON.stringify(schema13PassPayload));
schema13NotInReportPayload.requested_strategy_id = "missing_strategy";
schema13NotInReportPayload.selected_strategy_id = null;
schema13NotInReportPayload.strategy_match_status = "NOT_IN_REPORT";
schema13NotInReportPayload.evidence_contract.strategy_match_status = "NOT_IN_REPORT";
schema13NotInReportPayload.evidence_contract.hypothesis_preregistration_status = "BLOCK";
schema13NotInReportPayload.hypothesis_preregistration.status = "BLOCK";
schema13NotInReportPayload.hypothesis_preregistration.selected_strategy_match = false;
schema13NotInReportPayload.hypothesis_preregistration.blockers = [
  "selected_strategy_not_bound_to_hypothesis",
];
schema13NotInReportPayload.evidence_contract.parameter_stability_status = "UNKNOWN";
schema13NotInReportPayload.evidence_contract.cost_sensitivity_status = "UNKNOWN";
schema13NotInReportPayload.evidence_contract.chronological_slice_status = "UNKNOWN";
schema13NotInReportPayload.evidence_contract.implementation_currentness_checked = false;
schema13NotInReportPayload.evidence_contract.implementation_currentness_status = "NOT_IN_REPORT";
schema13NotInReportPayload.evidence_contract.implementation_currentness_match = null;
schema13NotInReportPayload.parameter_stability.status = "UNKNOWN";
schema13NotInReportPayload.cost_sensitivity.status = "UNKNOWN";
schema13NotInReportPayload.chronological_slices.status = "UNKNOWN";
schema13NotInReportPayload.implementation_currentness.status = "NOT_IN_REPORT";
schema13NotInReportPayload.implementation_currentness.checked = false;
schema13NotInReportPayload.implementation_currentness.matches_current = null;
schema13NotInReportPayload.implementation_currentness.frozen_variant_count = 0;
schema13NotInReportPayload.implementation_currentness.matched_variant_count = 0;
schema13NotInReportPayload.implementation_currentness.mismatched_variant_count = 0;
schema13NotInReportPayload.implementation_currentness.blockers = [
  "strategy_not_in_frozen_research_report",
];
schema13NotInReportPayload.implementation_currentness_checked = false;
schema13NotInReportPayload.implementation_currentness_status = "NOT_IN_REPORT";
schema13NotInReportPayload.implementation_currentness_match = null;
schema13NotInReportPayload.preregistered_failure_admission_status = "NOT_IN_REPORT";
schema13NotInReportPayload.evidence_contract.preregistered_failure_admission_status = "NOT_IN_REPORT";
schema13NotInReportPayload.preregistered_failure_admission = {
  ...schema13NotInReportPayload.preregistered_failure_admission,
  status: "NOT_IN_REPORT",
  hypothesis_id: null,
  selected_strategy_status: "NOT_IN_REPORT",
  selected_strategy_candidate_count: 0,
  selected_strategy_admitted_count: 0,
  admitted_candidate_count: 0,
  mechanism_condition_ids: [],
  checks: [],
  future_standard_checks: [],
  blockers: ["strategy_not_in_frozen_research_report"],
};
schema13NotInReportPayload.post_selection_replay_summary = postSelectionSummary(
  13,
  "NOT_RUN",
  "NOT_RUN",
);
schema13NotInReportPayload.post_selection_replay_status = "NOT_RUN";
schema13NotInReportPayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
schema13NotInReportPayload.failure_conditions = {
  schema_version: "strategy-research-failure-conditions-v3",
  status: "NOT_IN_REPORT",
  observed: ["strategy_not_in_frozen_research_report"],
  evidence_gaps: [
    "strategy_specific_parameter_cost_and_time_evidence_missing",
    "dataset_currentness_not_checked",
    "report_age_policy_not_checked",
    "natural_forward_performance_not_proven_by_strategy_report",
  ],
  conditions: [],
  descriptive_only: true,
  profitability_proven: false,
  parameter_selection_allowed: false,
  paper_authorized: false,
  live_order_allowed: false,
  preregistered_failure_admission_status: "NOT_IN_REPORT",
};
const schema13NotInReport = evidence.strategyLabEvidencePresentation(schema13NotInReportPayload);
assert.equal(schema13NotInReport.valid, true);
assert.equal(schema13NotInReport.rawAdmissionStatus, "NOT_IN_REPORT");
assert.equal(schema13NotInReport.rawMechanismStatus, "NOT_IN_REPORT");
assert.equal(schema13NotInReport.rawFutureConditionStatus, "NOT_IN_REPORT");
assert.ok(schema13NotInReport.admissionText.includes("不借用"));
assert.ok(schema13NotInReport.mechanismConditionText.includes("不借用"));
assert.ok(schema13NotInReport.futureConditionText.includes("不借用"));
assert.deepEqual(schema13NotInReport.mechanismConditionRows, []);
assert.deepEqual(schema13NotInReport.futureConditionRows, []);

const schema14NotInReportPayload = JSON.parse(JSON.stringify(schema13NotInReportPayload));
schema14NotInReportPayload.report_schema_version = 14;
schema14NotInReportPayload.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v7";
schema14NotInReportPayload.evidence_contract.hypothesis_preregistration_schema_version =
  "strategy-hypothesis-preregistration-v3";
schema14NotInReportPayload.evidence_contract.preregistered_failure_admission_schema_version =
  "strategy-preregistered-failure-admission-v3";
schema14NotInReportPayload.evidence_contract.failure_conditions_schema_version =
  "strategy-research-failure-conditions-v4";
schema14NotInReportPayload.evidence_contract.search_lineage_schema_version =
  "strategy-research-search-lineage-public-v1";
schema14NotInReportPayload.evidence_contract.search_lineage_status = "NOT_IN_REPORT";
schema14NotInReportPayload.hypothesis_preregistration.schema_version =
  "strategy-hypothesis-preregistration-summary-v3";
schema14NotInReportPayload.hypothesis_preregistration.source_schema_version =
  "strategy-hypothesis-preregistration-v3";
schema14NotInReportPayload.hypothesis_preregistration.search_family_bound = false;
schema14NotInReportPayload.post_selection_replay_summary.report_schema_version = 14;
schema14NotInReportPayload.preregistered_failure_admission.schema_version =
  "strategy-preregistered-failure-admission-v3";
schema14NotInReportPayload.preregistered_failure_admission.search_lineage_status =
  "NOT_IN_REPORT";
schema14NotInReportPayload.search_lineage_status = "NOT_IN_REPORT";
schema14NotInReportPayload.search_lineage = {
  schema_version: "strategy-research-search-lineage-public-v1",
  descriptive_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  automatic_paper_activation_allowed: false,
  research_only: true,
  paper_authorized: false,
  live_order_allowed: false,
  status: "NOT_IN_REPORT",
  family_bound: false,
  trial_count_scope: null,
  prior_trial_count: null,
  current_trial_count: null,
  cumulative_trial_count: null,
  selection_binding_scope: null,
  offline_verification_scope:
    "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY",
  admission_status: "NOT_IN_REPORT",
  blockers: ["strategy_not_in_frozen_research_report"],
};
schema14NotInReportPayload.failure_conditions.schema_version =
  "strategy-research-failure-conditions-v4";
schema14NotInReportPayload.failure_conditions.search_lineage_status = "NOT_IN_REPORT";
const schema14NotInReport = evidence.strategyLabEvidencePresentation(schema14NotInReportPayload);
assert.equal(schema14NotInReport.valid, true);
assert.equal(schema14NotInReport.rawSearchLineageStatus, "NOT_IN_REPORT");
assert.equal(schema14NotInReport.lineageText, "当前策略不在报告 · 检索谱系不借用，计数未提供");
assert.ok(!schema14NotInReport.lineageText.includes("既往"));
assert.ok(!schema14NotInReport.lineageText.includes("累计"));

for (const countField of ["prior_trial_count", "current_trial_count", "cumulative_trial_count"]) {
  const forged = JSON.parse(JSON.stringify(schema14NotInReportPayload));
  forged.search_lineage[countField] = 1;
  assert.equal(
    evidence.strategyLabEvidencePresentation(forged).valid,
    false,
    `schema14 NOT_IN_REPORT must not borrow ${countField}`,
  );
}

const schema13ForgedNotInReportReplay = JSON.parse(JSON.stringify(schema13NotInReportPayload));
schema13ForgedNotInReportReplay.scope.frozen_test_candidate_count = 1;
schema13ForgedNotInReportReplay.scope.test_cell_count = 2;
schema13ForgedNotInReportReplay.scope.forward_candidate_count = 1;
schema13ForgedNotInReportReplay.post_selection_replay_summary = postSelectionSummary(13);
schema13ForgedNotInReportReplay.post_selection_replay_status = "PASS";
schema13ForgedNotInReportReplay.evidence_contract.post_selection_replay_status = "PASS";
assert.equal(evidence.strategyLabEvidencePresentation(schema13ForgedNotInReportReplay).valid, false);
const schema13ForgedNotInReportAdmission = JSON.parse(JSON.stringify(schema13NotInReportPayload));
schema13ForgedNotInReportAdmission.preregistered_failure_admission_status = "PASS";
schema13ForgedNotInReportAdmission.evidence_contract.preregistered_failure_admission_status = "PASS";
schema13ForgedNotInReportAdmission.preregistered_failure_admission = JSON.parse(
  JSON.stringify(schema13PassPayload.preregistered_failure_admission),
);
assert.equal(evidence.strategyLabEvidencePresentation(schema13ForgedNotInReportAdmission).valid, false);

const strategyLabExecutionAuthorityFields = [
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
  "paper_authorized",
  "live_trading_allowed",
  "live_trading_enabled",
  "mission_authorized",
  "order_allowed",
  "paper_activation_allowed",
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
];
for (const key of strategyLabExecutionAuthorityFields) {
  const escalated = JSON.parse(JSON.stringify(schema12PassPayload));
  escalated[key] = true;
  assert.equal(
    evidence.strategyLabEvidencePresentation(escalated).valid,
    false,
    `canonical authority field ${key} must fail closed`,
  );
}

for (const key of [
  "Ａｒｍｅｄ",
  "canTrade",
  "Paper_Authorized",
  "parameterSelectionAuthority",
  "directionSignalAllowed",
  "direction-signal-allowed",
  "performanceClaimProven",
  "performance-claim-proven",
  "roleAssignmentAllowed",
  "role-assignment-allowed",
]) {
  const escalated = JSON.parse(JSON.stringify(schema12PassPayload));
  escalated[key] = true;
  assert.equal(
    evidence.strategyLabEvidencePresentation(escalated).valid,
    false,
    `canonical authority alias ${key} must fail closed`,
  );
}

const schema12MissingAdmission = JSON.parse(JSON.stringify(schema12PassPayload));
delete schema12MissingAdmission.preregistered_failure_admission;
assert.equal(evidence.strategyLabEvidencePresentation(schema12MissingAdmission).valid, false);

const schema12CountMismatch = JSON.parse(JSON.stringify(schema12PassPayload));
schema12CountMismatch.preregistered_failure_admission.admitted_candidate_count = 2;
assert.equal(evidence.strategyLabEvidencePresentation(schema12CountMismatch).valid, false);

const schema12RootStatusMismatch = JSON.parse(JSON.stringify(schema12PassPayload));
schema12RootStatusMismatch.preregistered_failure_admission_status = "BLOCK";
assert.equal(evidence.strategyLabEvidencePresentation(schema12RootStatusMismatch).valid, false);

const schema12HypothesisMismatch = JSON.parse(JSON.stringify(schema12PassPayload));
schema12HypothesisMismatch.preregistered_failure_admission.hypothesis_id = "different-hypothesis-v1";
assert.equal(evidence.strategyLabEvidencePresentation(schema12HypothesisMismatch).valid, false);

const schema12AdmissionSchemaMismatch = JSON.parse(JSON.stringify(schema12PassPayload));
schema12AdmissionSchemaMismatch.preregistered_failure_admission.schema_version = "strategy-preregistered-failure-admission-v2";
assert.equal(evidence.strategyLabEvidencePresentation(schema12AdmissionSchemaMismatch).valid, false);

const schema12CheckMismatch = JSON.parse(JSON.stringify(schema12PassPayload));
schema12CheckMismatch.preregistered_failure_admission.checks[0].triggered = true;
assert.equal(evidence.strategyLabEvidencePresentation(schema12CheckMismatch).valid, false);

const v3WithAdmissionClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
v3WithAdmissionClaim.preregistered_failure_admission_status = "PASS";
assert.equal(evidence.strategyLabEvidencePresentation(v3WithAdmissionClaim).valid, false);

const unsupportedFutureHypothesisSchema = JSON.parse(JSON.stringify(schema12PassPayload));
unsupportedFutureHypothesisSchema.report_schema_version = 13;
assert.equal(
  evidence.strategyLabEvidencePresentation(unsupportedFutureHypothesisSchema).valid,
  false,
  "an unreviewed future report schema must fail closed",
);

const retiredV4Schema12 = JSON.parse(JSON.stringify(schema12PassPayload));
retiredV4Schema12.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v4";
assert.equal(
  evidence.strategyLabEvidencePresentation(retiredV4Schema12).valid,
  false,
  "the current consumer must not permit a schema-12 v4 downgrade without mandatory replay evidence",
);
const v3Schema11Downgrade = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
v3Schema11Downgrade.report_schema_version = 11;
assert.equal(evidence.strategyLabEvidencePresentation(v3Schema11Downgrade).valid, false);

const missingPostSelection = JSON.parse(JSON.stringify(schema11PassPayload));
delete missingPostSelection.post_selection_replay_summary;
assert.equal(evidence.strategyLabEvidencePresentation(missingPostSelection).valid, false);
const rootPostSelectionMismatch = JSON.parse(JSON.stringify(schema11PassPayload));
rootPostSelectionMismatch.post_selection_replay_status = "BLOCK";
assert.equal(evidence.strategyLabEvidencePresentation(rootPostSelectionMismatch).valid, false);
const contractPostSelectionMismatch = JSON.parse(JSON.stringify(schema11PassPayload));
contractPostSelectionMismatch.evidence_contract.post_selection_replay_status = "BLOCK";
assert.equal(evidence.strategyLabEvidencePresentation(contractPostSelectionMismatch).valid, false);
const summaryPostSelectionMismatch = JSON.parse(JSON.stringify(schema11PassPayload));
summaryPostSelectionMismatch.post_selection_replay_summary.status = "BLOCK";
summaryPostSelectionMismatch.post_selection_replay_status = "BLOCK";
summaryPostSelectionMismatch.evidence_contract.post_selection_replay_status = "BLOCK";
assert.equal(evidence.strategyLabEvidencePresentation(summaryPostSelectionMismatch).valid, false);
const reportVersionPostSelectionMismatch = JSON.parse(JSON.stringify(schema11PassPayload));
reportVersionPostSelectionMismatch.post_selection_replay_summary.report_schema_version = 12;
assert.equal(evidence.strategyLabEvidencePresentation(reportVersionPostSelectionMismatch).valid, false);
const schema11WithAdmission = JSON.parse(JSON.stringify(schema11PassPayload));
schema11WithAdmission.preregistered_failure_admission_status = "PASS";
assert.equal(evidence.strategyLabEvidencePresentation(schema11WithAdmission).valid, false);
const extraSummaryField = JSON.parse(JSON.stringify(schema11PassPayload));
extraSummaryField.post_selection_replay_summary.forward_ready = true;
assert.equal(evidence.strategyLabEvidencePresentation(extraSummaryField).valid, false);
const extraStageField = JSON.parse(JSON.stringify(schema11PassPayload));
extraStageField.post_selection_replay_summary.frozen_test.variant_id = "must-not-enter-public-summary";
assert.equal(evidence.strategyLabEvidencePresentation(extraStageField).valid, false);
const swappedStageRole = JSON.parse(JSON.stringify(schema11PassPayload));
swappedStageRole.post_selection_replay_summary.frozen_test.stage = "HOLDOUT_CONFIRMATION";
assert.equal(evidence.strategyLabEvidencePresentation(swappedStageRole).valid, false);

for (const [authorityKey, target] of [
  ["canTrade", "summary"],
  ["Paper_Authorized", "stage"],
  ["parameterSelectionAuthority", "summary"],
]) {
  const forged = JSON.parse(JSON.stringify(schema11PassPayload));
  if (target === "stage") forged.post_selection_replay_summary.frozen_test[authorityKey] = true;
  else forged.post_selection_replay_summary[authorityKey] = true;
  assert.equal(
    evidence.strategyLabEvidencePresentation(forged).valid,
    false,
    `post-selection authority alias ${authorityKey} must fail closed`,
  );
}

const schema11NotRunPayload = makePostSelectionPayload(11, "NOT_RUN", "NOT_RUN");
const schema11NotRun = evidence.strategyLabEvidencePresentation(schema11NotRunPayload);
assert.equal(schema11NotRun.valid, true);
assert.equal(schema11NotRun.rawPostSelectionStatus, "NOT_RUN");
assert.ok(schema11NotRun.frozenTestText.includes("未运行"));
assert.ok(!schema11NotRun.frozenTestText.includes("0.00%"));
const notRunWithCount = JSON.parse(JSON.stringify(schema11NotRunPayload));
notRunWithCount.post_selection_replay_summary.frozen_test.candidate_count = 1;
assert.equal(evidence.strategyLabEvidencePresentation(notRunWithCount).valid, false);
const notRunWithMetric = JSON.parse(JSON.stringify(schema11NotRunPayload));
notRunWithMetric.post_selection_replay_summary.frozen_test.minimum_configured_return_pct = 0;
assert.equal(evidence.strategyLabEvidencePresentation(notRunWithMetric).valid, false);

const schema11ReplayBlockPayload = makePostSelectionPayload(11, "BLOCK", "NOT_RUN");
const schema11ReplayBlock = evidence.strategyLabEvidencePresentation(schema11ReplayBlockPayload);
assert.equal(schema11ReplayBlock.valid, true);
assert.equal(schema11ReplayBlock.rawPostSelectionStatus, "BLOCK");
assert.ok(schema11ReplayBlock.frozenTestText.includes("存在阻断"));
assert.ok(schema11ReplayBlock.frozenTestText.includes("最低收益 -1.25%"));

const integrityBlockedReplay = JSON.parse(JSON.stringify(schema11ReplayBlockPayload));
const integrityStage = integrityBlockedReplay.post_selection_replay_summary.frozen_test;
integrityStage.replay_verified_cell_count = 1;
integrityStage.minimum_configured_return_pct = null;
integrityStage.minimum_excess_return_pct = null;
integrityStage.minimum_severe_cost_return_pct = null;
integrityStage.worst_drawdown_pct = null;
integrityStage.total_trades = null;
integrityStage.blockers = ["post_selection_replay_integrity_not_preserved"];
bindPostSelectionFailureV2(integrityBlockedReplay);
const integrityBlockedPresentation = evidence.strategyLabEvidencePresentation(integrityBlockedReplay);
assert.equal(integrityBlockedPresentation.valid, true);
assert.ok(integrityBlockedPresentation.frozenTestText.includes("交易样本未形成"));
assert.ok(!integrityBlockedPresentation.frozenTestText.includes("null"));
const integrityBlockWithMetric = JSON.parse(JSON.stringify(integrityBlockedReplay));
integrityBlockWithMetric.post_selection_replay_summary.frozen_test.minimum_configured_return_pct = -1;
assert.equal(evidence.strategyLabEvidencePresentation(integrityBlockWithMetric).valid, false);
const integrityBlockWithAuditCount = JSON.parse(JSON.stringify(integrityBlockedReplay));
integrityBlockWithAuditCount.post_selection_replay_summary.frozen_test.fixed_slice_pass_cell_count = 1;
assert.equal(evidence.strategyLabEvidencePresentation(integrityBlockWithAuditCount).valid, false);

const aggregateSemanticsBlockedReplay = makePostSelectionPayload(11, "PASS", "BLOCK");
const aggregateSemanticsStage = aggregateSemanticsBlockedReplay
  .post_selection_replay_summary.holdout_confirmation;
aggregateSemanticsStage.blockers = ["post_selection_aggregate_semantics_not_preserved"];
aggregateSemanticsStage.minimum_configured_return_pct = null;
aggregateSemanticsStage.minimum_excess_return_pct = null;
aggregateSemanticsStage.minimum_severe_cost_return_pct = null;
aggregateSemanticsStage.worst_drawdown_pct = null;
aggregateSemanticsStage.total_trades = null;
aggregateSemanticsStage.fixed_slice_pass_cell_count = 0;
aggregateSemanticsStage.prefix_invariance_pass_cell_count = 0;
aggregateSemanticsStage.lookahead_pass_cell_count = 0;
bindPostSelectionFailureV2(aggregateSemanticsBlockedReplay);
assert.equal(evidence.strategyLabEvidencePresentation(aggregateSemanticsBlockedReplay).valid, true);
const aggregateSemanticsWithMetrics = JSON.parse(JSON.stringify(aggregateSemanticsBlockedReplay));
Object.assign(aggregateSemanticsWithMetrics.post_selection_replay_summary.holdout_confirmation, {
  minimum_configured_return_pct: -1.25,
  minimum_excess_return_pct: -2.1,
  minimum_severe_cost_return_pct: -2.8,
  worst_drawdown_pct: 14.5,
  total_trades: 12,
});
assert.equal(evidence.strategyLabEvidencePresentation(aggregateSemanticsWithMetrics).valid, false);
const aggregateSemanticsWithAuditCount = JSON.parse(JSON.stringify(aggregateSemanticsBlockedReplay));
aggregateSemanticsWithAuditCount
  .post_selection_replay_summary.holdout_confirmation.lookahead_pass_cell_count = 1;
assert.equal(evidence.strategyLabEvidencePresentation(aggregateSemanticsWithAuditCount).valid, false);

const greenCountsDisguisedAsBlock = JSON.parse(JSON.stringify(schema11PassPayload));
greenCountsDisguisedAsBlock.post_selection_replay_summary.status = "BLOCK";
greenCountsDisguisedAsBlock.post_selection_replay_summary.frozen_test.status = "BLOCK";
greenCountsDisguisedAsBlock.post_selection_replay_summary.frozen_test.blockers = [
  "post_selection_replay_outcome_not_preserved",
];
greenCountsDisguisedAsBlock.post_selection_replay_status = "BLOCK";
greenCountsDisguisedAsBlock.evidence_contract.post_selection_replay_status = "BLOCK";
bindPostSelectionFailureV2(greenCountsDisguisedAsBlock);
assert.equal(evidence.strategyLabEvidencePresentation(greenCountsDisguisedAsBlock).valid, false);

for (const mutate of [
  (payload) => { payload.post_selection_replay_summary.frozen_test.candidate_count = true; },
  (payload) => { payload.post_selection_replay_summary.frozen_test.total_trades = "12"; },
  (payload) => { payload.post_selection_replay_summary.frozen_test.minimum_excess_return_pct = Number.NaN; },
  (payload) => { payload.post_selection_replay_summary.frozen_test.worst_drawdown_pct = Number.POSITIVE_INFINITY; },
  (payload) => { payload.post_selection_replay_summary.frozen_test.fixed_slice_pass_cell_count = 1; },
  (payload) => { payload.post_selection_replay_summary.holdout_confirmation.lookahead_pass_cell_count = 3; },
]) {
  const forged = JSON.parse(JSON.stringify(schema11PassPayload));
  mutate(forged);
  assert.equal(evidence.strategyLabEvidencePresentation(forged).valid, false);
}
const duplicateReplayBlocker = JSON.parse(JSON.stringify(schema11ReplayBlockPayload));
duplicateReplayBlocker.post_selection_replay_summary.frozen_test.blockers.push(
  "post_selection_replay_outcome_not_preserved",
);
assert.equal(evidence.strategyLabEvidencePresentation(duplicateReplayBlocker).valid, false);
const unknownReplayBlocker = JSON.parse(JSON.stringify(schema11ReplayBlockPayload));
unknownReplayBlocker.post_selection_replay_summary.frozen_test.blockers = ["READY_TO_TRADE"];
bindPostSelectionFailureV2(unknownReplayBlocker);
assert.equal(evidence.strategyLabEvidencePresentation(unknownReplayBlocker).valid, false);

const passThenHoldoutBlock = makePostSelectionPayload(11, "PASS", "BLOCK");
assert.equal(evidence.strategyLabEvidencePresentation(passThenHoldoutBlock).valid, true);
const strictTestBlockThenHoldoutPass = makePostSelectionPayload(11, "BLOCK", "PASS");
strictTestBlockThenHoldoutPass.post_selection_replay_summary.frozen_test.aggregate_pass_candidate_count = 1;
bindPostSelectionFailureV2(strictTestBlockThenHoldoutPass);
assert.equal(evidence.strategyLabEvidencePresentation(strictTestBlockThenHoldoutPass).valid, true);
const invalidPassThenNotRun = makePostSelectionPayload(11, "PASS", "NOT_RUN");
assert.equal(evidence.strategyLabEvidencePresentation(invalidPassThenNotRun).valid, false);
const invalidNotRunThenPass = makePostSelectionPayload(11, "NOT_RUN", "PASS");
assert.equal(evidence.strategyLabEvidencePresentation(invalidNotRunThenPass).valid, false);
const forgedHoldoutCandidateCausality = JSON.parse(JSON.stringify(schema11PassPayload));
forgedHoldoutCandidateCausality.post_selection_replay_summary.holdout_confirmation.candidate_count = 0;
assert.equal(evidence.strategyLabEvidencePresentation(forgedHoldoutCandidateCausality).valid, false);

const failureV2MissingReplayCondition = JSON.parse(JSON.stringify(schema11PassPayload));
failureV2MissingReplayCondition.failure_conditions.conditions.pop();
assert.equal(evidence.strategyLabEvidencePresentation(failureV2MissingReplayCondition).valid, false);
const failureV2DuplicateReplayCondition = JSON.parse(JSON.stringify(schema11PassPayload));
failureV2DuplicateReplayCondition.failure_conditions.conditions.push(
  JSON.parse(JSON.stringify(failureV2DuplicateReplayCondition.failure_conditions.conditions.at(-1))),
);
assert.equal(evidence.strategyLabEvidencePresentation(failureV2DuplicateReplayCondition).valid, false);
const failureV2ForgedTrigger = JSON.parse(JSON.stringify(schema11PassPayload));
failureV2ForgedTrigger.failure_conditions.conditions.at(-1).triggered = true;
assert.equal(evidence.strategyLabEvidencePresentation(failureV2ForgedTrigger).valid, false);
const failureV2WrongBlockers = JSON.parse(JSON.stringify(schema11ReplayBlockPayload));
failureV2WrongBlockers.failure_conditions.conditions.find(
  (condition) => condition.condition_id === "frozen_test_replay_not_preserved",
).blockers = [];
assert.equal(evidence.strategyLabEvidencePresentation(failureV2WrongBlockers).valid, false);
const failureV2DuplicateObserved = JSON.parse(JSON.stringify(schema11ReplayBlockPayload));
failureV2DuplicateObserved.failure_conditions.observed.push(
  "frozen_test_replay_not_preserved",
);
assert.equal(evidence.strategyLabEvidencePresentation(failureV2DuplicateObserved).valid, false);

const triggeredFailureConditions = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
triggeredFailureConditions.cost_sensitivity.status = "BLOCK";
triggeredFailureConditions.cost_sensitivity.worst_stressed_return_pct = -0.5;
triggeredFailureConditions.cost_sensitivity.break_even_preserved = false;
triggeredFailureConditions.evidence_contract.cost_sensitivity_status = "BLOCK";
triggeredFailureConditions.failure_conditions.status = "TRIGGERED";
triggeredFailureConditions.failure_conditions.observed = ["cost_stress_break_even_not_preserved"];
triggeredFailureConditions.failure_conditions.evidence_gaps = [
  "dataset_currentness_not_checked",
  "report_age_policy_not_checked",
  "natural_forward_performance_not_proven_by_strategy_report",
];
triggeredFailureConditions.failure_conditions.conditions[1].evidence_status = "BLOCK";
triggeredFailureConditions.failure_conditions.conditions[1].triggered = true;
const triggeredFailurePresentation = evidence.strategyLabEvidencePresentation(triggeredFailureConditions);
assert.equal(triggeredFailurePresentation.valid, true);
assert.ok(triggeredFailurePresentation.failureText.includes("压力成本后未守住盈亏线"));

const falseClearFailureClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
falseClearFailureClaim.failure_conditions.status = "CLEAR_ON_CHECKED_DIMENSIONS";
assert.equal(evidence.strategyLabEvidencePresentation(falseClearFailureClaim).valid, false);

const authorityEscalatedStrategyLab = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
authorityEscalatedStrategyLab.parameter_stability.nested = { can_execute: true };
assert.equal(evidence.strategyLabEvidencePresentation(authorityEscalatedStrategyLab).valid, false);

const numericTopologyClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
numericTopologyClaim.parameter_stability.numeric_parameter_distance_checked = true;
assert.equal(evidence.strategyLabEvidencePresentation(numericTopologyClaim).valid, false);

const weakenedHypothesisCostContract = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
weakenedHypothesisCostContract.hypothesis_preregistration.stressed_return_must_remain_positive = false;
assert.equal(evidence.strategyLabEvidencePresentation(weakenedHypothesisCostContract).valid, false);

const malformedHypothesisHash = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
malformedHypothesisHash.hypothesis_preregistration.hypothesis_hash = "not-a-sealed-hash";
assert.equal(evidence.strategyLabEvidencePresentation(malformedHypothesisHash).valid, false);

const hypothesisAuthorityEscalation = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
hypothesisAuthorityEscalation.hypothesis_preregistration.nested = { paper_ready: true };
assert.equal(evidence.strategyLabEvidencePresentation(hypothesisAuthorityEscalation).valid, false);

const falseCostClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
falseCostClaim.cost_sensitivity.break_even_preserved = false;
assert.equal(evidence.strategyLabEvidencePresentation(falseCostClaim).valid, false);

const falseCurrentnessClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
falseCurrentnessClaim.implementation_currentness_match = false;
assert.equal(evidence.strategyLabEvidencePresentation(falseCurrentnessClaim).valid, false);

const missingCurrentnessCount = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
missingCurrentnessCount.implementation_currentness.matched_variant_count = null;
assert.equal(evidence.strategyLabEvidencePresentation(missingCurrentnessCount).valid, false);

const falseFullCurrentnessClaim = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
falseFullCurrentnessClaim.full_implementation_manifest_match = false;
assert.equal(evidence.strategyLabEvidencePresentation(falseFullCurrentnessClaim).valid, false);

const forgedReportAge = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
forgedReportAge.currentness_facts.report_age_ms = 0;
assert.equal(evidence.strategyLabEvidencePresentation(forgedReportAge).valid, false);

const forgedFreshnessThreshold = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
forgedFreshnessThreshold.currentness_facts.report_age_threshold_ms = 86_400_000;
forgedFreshnessThreshold.currentness_facts.threshold_applied = true;
assert.equal(evidence.strategyLabEvidencePresentation(forgedFreshnessThreshold).valid, false);

const malformedDatasetDate = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
malformedDatasetDate.currentness_facts.dataset_as_of = "2026-99-99";
assert.doesNotThrow(() => evidence.strategyLabEvidencePresentation(malformedDatasetDate));
assert.equal(evidence.strategyLabEvidencePresentation(malformedDatasetDate).valid, false);

const mismatchedStrategyLabPayload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
mismatchedStrategyLabPayload.implementation_currentness.status = "MISMATCH";
mismatchedStrategyLabPayload.implementation_currentness.matches_current = false;
mismatchedStrategyLabPayload.implementation_currentness.matched_variant_count = 0;
mismatchedStrategyLabPayload.implementation_currentness.mismatched_variant_count = 3;
mismatchedStrategyLabPayload.implementation_currentness.blockers = [
  "strategy_signal_implementation_fingerprint_changed",
];
mismatchedStrategyLabPayload.implementation_currentness_status = "MISMATCH";
mismatchedStrategyLabPayload.implementation_currentness_match = false;
mismatchedStrategyLabPayload.evidence_contract.implementation_currentness_status = "MISMATCH";
mismatchedStrategyLabPayload.evidence_contract.implementation_currentness_match = false;
mismatchedStrategyLabPayload.failure_conditions.status = "TRIGGERED";
mismatchedStrategyLabPayload.failure_conditions.observed = [
  "strategy_signal_implementation_changed",
];
mismatchedStrategyLabPayload.failure_conditions.conditions[3].evidence_status = "MISMATCH";
mismatchedStrategyLabPayload.failure_conditions.conditions[3].triggered = true;
mismatchedStrategyLabPayload.failure_conditions.conditions[3].blockers = [
  "strategy_signal_implementation_fingerprint_changed",
];
const mismatchedStrategyLab = evidence.strategyLabEvidencePresentation(mismatchedStrategyLabPayload);
assert.equal(mismatchedStrategyLab.valid, true);
assert.equal(mismatchedStrategyLab.connectionStatus, "VERIFIED_IMPLEMENTATION_MISMATCH");
assert.ok(mismatchedStrategyLab.implementationText.includes("已变化"));
assert.ok(mismatchedStrategyLab.parameterText.startsWith("历史冻结"));
assert.ok(mismatchedStrategyLab.detailText.includes("不得外推"));

const fullMismatchPayload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
fullMismatchPayload.full_implementation_currentness.status = "MISMATCH";
fullMismatchPayload.full_implementation_currentness.matches_current = false;
fullMismatchPayload.full_implementation_currentness.blockers = [
  "research_full_implementation_or_runtime_changed",
];
fullMismatchPayload.full_implementation_manifest_status = "MISMATCH";
fullMismatchPayload.full_implementation_manifest_match = false;
fullMismatchPayload.evidence_contract.full_implementation_manifest_status = "MISMATCH";
fullMismatchPayload.evidence_contract.full_implementation_manifest_match = false;
fullMismatchPayload.failure_conditions.status = "TRIGGERED";
fullMismatchPayload.failure_conditions.observed = [
  "research_implementation_closure_changed",
];
fullMismatchPayload.failure_conditions.conditions[4].evidence_status = "MISMATCH";
fullMismatchPayload.failure_conditions.conditions[4].triggered = true;
fullMismatchPayload.failure_conditions.conditions[4].blockers = [
  "research_full_implementation_or_runtime_changed",
];
const fullMismatch = evidence.strategyLabEvidencePresentation(fullMismatchPayload);
assert.equal(fullMismatch.valid, true);
assert.equal(fullMismatch.connectionStatus, "VERIFIED_IMPLEMENTATION_MISMATCH");
assert.ok(fullMismatch.implementationText.includes("闭包或运行时已变化"));
assert.ok(fullMismatch.parameterText.startsWith("历史冻结"));

const legacySignalOnlyPayload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
legacySignalOnlyPayload.report_schema_version = 5;
legacySignalOnlyPayload.evidence_contract.hypothesis_preregistration_status = "LEGACY_NOT_BOUND";
legacySignalOnlyPayload.hypothesis_preregistration = {
  schema_version: "strategy-hypothesis-preregistration-summary-v1",
  status: "LEGACY_NOT_BOUND",
  contract_checked: false,
  hypothesis_id: null,
  hypothesis_hash: null,
  research_generation: "FROZEN_TEST",
  strategy_ids: [],
  selected_strategy_match: null,
  mechanism_family: null,
  hypothesis_statement: null,
  novelty_statement: null,
  mechanism_specific_failure_conditions: [],
  parameter_topology_basis: null,
  numeric_parameter_distance_claimed: null,
  cost_stress_required: null,
  stressed_return_must_remain_positive: null,
  chronological_evaluation_mode: null,
  parameters_refit_per_fold: null,
  walk_forward_optimization_claim_allowed: false,
  fresh_single_use_holdout_required: null,
  minimum_natural_forward_outcomes: null,
  minimum_executed_rebalances: null,
  statistical_contract_recheck_required_at_maturity: null,
  historical_backtest_can_substitute_natural_forward: null,
  reuses_falsified_strategy_id: null,
  retunes_falsified_mechanism: null,
  material_mechanism_change_requires_new_strategy_id: null,
  blockers: ["historical_report_predates_hypothesis_preregistration"],
  descriptive_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  automatic_paper_activation_allowed: false,
  research_only: true,
  paper_authorized: false,
  live_order_allowed: false,
};
legacySignalOnlyPayload.full_implementation_currentness.status = "NOT_AVAILABLE";
legacySignalOnlyPayload.full_implementation_currentness.checked = false;
legacySignalOnlyPayload.full_implementation_currentness.matches_current = null;
legacySignalOnlyPayload.full_implementation_currentness.expected_source_count = 0;
legacySignalOnlyPayload.full_implementation_currentness.verified_source_count = 0;
legacySignalOnlyPayload.full_implementation_currentness.exact_files_checked = false;
legacySignalOnlyPayload.full_implementation_currentness.runtime_checked = false;
legacySignalOnlyPayload.full_implementation_currentness.blockers = [
  "research_report_does_not_embed_full_implementation_manifest",
];
legacySignalOnlyPayload.full_implementation_manifest_checked = false;
legacySignalOnlyPayload.full_implementation_manifest_status = "NOT_AVAILABLE";
legacySignalOnlyPayload.full_implementation_manifest_match = null;
legacySignalOnlyPayload.evidence_contract.full_implementation_manifest_checked = false;
legacySignalOnlyPayload.evidence_contract.full_implementation_manifest_status = "NOT_AVAILABLE";
legacySignalOnlyPayload.evidence_contract.full_implementation_manifest_match = null;
legacySignalOnlyPayload.failure_conditions.evidence_gaps.push(
  "research_implementation_closure_changed_not_checked",
);
legacySignalOnlyPayload.failure_conditions.conditions[4].evidence_status = "NOT_AVAILABLE";
legacySignalOnlyPayload.failure_conditions.conditions[4].triggered = null;
legacySignalOnlyPayload.failure_conditions.conditions[4].blockers = [
  "research_report_does_not_embed_full_implementation_manifest",
];
const legacySignalOnly = evidence.strategyLabEvidencePresentation(legacySignalOnlyPayload);
assert.equal(legacySignalOnly.valid, true);
assert.equal(legacySignalOnly.connectionStatus, "VERIFIED_SIGNAL_ONLY");
assert.ok(legacySignalOnly.implementationText.includes("未封存完整实现闭包"));
assert.ok(legacySignalOnly.hypothesisText.includes("历史报告未封存"));
assert.ok(legacySignalOnly.hypothesisFailureText.includes("不能补写为事前证据"));
assert.ok(legacySignalOnly.parameterText.startsWith("历史冻结"));
for (const reportSchemaVersion of [3, 4, 5]) {
  const legacyPayload = JSON.parse(JSON.stringify(legacySignalOnlyPayload));
  legacyPayload.report_schema_version = reportSchemaVersion;
  const presentation = evidence.strategyLabEvidencePresentation(legacyPayload);
  assert.equal(
    presentation.valid,
    true,
    `v3/report${reportSchemaVersion} must remain explicitly supported`,
  );
  assert.equal(presentation.rawSearchLineageStatus, "NOT_AVAILABLE");
  assert.equal(
    presentation.lineageText,
    "历史报告未封存检索谱系 · 不补写选择时核验结论",
  );
}

const legacySchema6Payload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
legacySchema6Payload.report_schema_version = 6;
legacySchema6Payload.evidence_contract.hypothesis_preregistration_status = "LEGACY_NOT_BOUND";
legacySchema6Payload.hypothesis_preregistration = JSON.parse(
  JSON.stringify(legacySignalOnlyPayload.hypothesis_preregistration),
);
const legacySchema6 = evidence.strategyLabEvidencePresentation(legacySchema6Payload);
assert.equal(legacySchema6.valid, true);
assert.equal(legacySchema6.connectionStatus, "VERIFIED_FROZEN");
assert.equal(legacySchema6.rawHypothesisStatus, "LEGACY_NOT_BOUND");
assert.equal(legacySchema6.rawSearchLineageStatus, "NOT_AVAILABLE");
assert.ok(legacySchema6.hypothesisText.includes("历史报告未封存"));

const unmatchedStrategyLabPayload = JSON.parse(JSON.stringify(frozenStrategyLabPayload));
unmatchedStrategyLabPayload.requested_strategy_id = "bollinger";
unmatchedStrategyLabPayload.selected_strategy_id = null;
unmatchedStrategyLabPayload.strategy_match_status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.evidence_contract.strategy_match_status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.evidence_contract.hypothesis_preregistration_status = "BLOCK";
unmatchedStrategyLabPayload.hypothesis_preregistration.status = "BLOCK";
unmatchedStrategyLabPayload.hypothesis_preregistration.selected_strategy_match = false;
unmatchedStrategyLabPayload.hypothesis_preregistration.blockers = [
  "selected_strategy_not_bound_to_hypothesis",
];
unmatchedStrategyLabPayload.evidence_contract.parameter_stability_status = "UNKNOWN";
unmatchedStrategyLabPayload.evidence_contract.cost_sensitivity_status = "UNKNOWN";
unmatchedStrategyLabPayload.evidence_contract.chronological_slice_status = "UNKNOWN";
unmatchedStrategyLabPayload.evidence_contract.implementation_currentness_checked = false;
unmatchedStrategyLabPayload.evidence_contract.implementation_currentness_status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.evidence_contract.implementation_currentness_match = null;
unmatchedStrategyLabPayload.parameter_stability.status = "UNKNOWN";
unmatchedStrategyLabPayload.cost_sensitivity.status = "UNKNOWN";
unmatchedStrategyLabPayload.chronological_slices.status = "UNKNOWN";
unmatchedStrategyLabPayload.implementation_currentness.status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.implementation_currentness.checked = false;
unmatchedStrategyLabPayload.implementation_currentness.matches_current = null;
unmatchedStrategyLabPayload.implementation_currentness.frozen_variant_count = 0;
unmatchedStrategyLabPayload.implementation_currentness.matched_variant_count = 0;
unmatchedStrategyLabPayload.implementation_currentness.mismatched_variant_count = 0;
unmatchedStrategyLabPayload.implementation_currentness.blockers = [
  "strategy_not_in_frozen_research_report",
];
unmatchedStrategyLabPayload.implementation_currentness_checked = false;
unmatchedStrategyLabPayload.implementation_currentness_status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.implementation_currentness_match = null;
unmatchedStrategyLabPayload.failure_conditions.status = "NOT_IN_REPORT";
unmatchedStrategyLabPayload.failure_conditions.observed = [
  "strategy_not_in_frozen_research_report",
];
unmatchedStrategyLabPayload.failure_conditions.evidence_gaps = [
  "strategy_specific_parameter_cost_and_time_evidence_missing",
  "dataset_currentness_not_checked",
  "report_age_policy_not_checked",
  "natural_forward_performance_not_proven_by_strategy_report",
];
unmatchedStrategyLabPayload.failure_conditions.conditions = [];
const unmatchedStrategyLab = evidence.strategyLabEvidencePresentation(unmatchedStrategyLabPayload);
assert.equal(unmatchedStrategyLab.valid, true);
assert.equal(unmatchedStrategyLab.connectionStatus, "VERIFIED_NO_MATCH");
assert.ok(unmatchedStrategyLab.modeText.includes("当前策略未纳入"));
assert.ok(unmatchedStrategyLab.implementationText.includes("无冻结记录"));
assert.ok(unmatchedStrategyLab.failureText.includes("无冻结失效条件"));

const schema11UnmatchedPayload = JSON.parse(JSON.stringify(unmatchedStrategyLabPayload));
schema11UnmatchedPayload.report_schema_version = 11;
schema11UnmatchedPayload.formal_single_use = true;
schema11UnmatchedPayload.selection_test_policy = "BLIND_ONCE";
schema11UnmatchedPayload.evidence_contract.schema_version = "strategy-lab-frozen-evidence-v5";
schema11UnmatchedPayload.post_selection_replay_summary = postSelectionSummary(
  11,
  "NOT_RUN",
  "NOT_RUN",
);
schema11UnmatchedPayload.post_selection_replay_status = "NOT_RUN";
schema11UnmatchedPayload.evidence_contract.post_selection_replay_status = "NOT_RUN";
schema11UnmatchedPayload.failure_conditions.schema_version = "strategy-research-failure-conditions-v2";
const schema11Unmatched = evidence.strategyLabEvidencePresentation(schema11UnmatchedPayload);
assert.equal(schema11Unmatched.valid, true);
assert.equal(schema11Unmatched.rawPostSelectionStatus, "NOT_RUN");
assert.ok(schema11Unmatched.postSelectionText.includes("当前策略未进入"));
assert.ok(schema11Unmatched.holdoutText.includes("非自然前向"));

const schema12UnmatchedPayload = JSON.parse(JSON.stringify(schema11UnmatchedPayload));
schema12UnmatchedPayload.report_schema_version = 12;
schema12UnmatchedPayload.post_selection_replay_summary.report_schema_version = 12;
schema12UnmatchedPayload.preregistered_failure_admission_status = "NOT_IN_REPORT";
schema12UnmatchedPayload.evidence_contract.preregistered_failure_admission_status = "NOT_IN_REPORT";
schema12UnmatchedPayload.preregistered_failure_admission = {
  schema_version: "strategy-preregistered-failure-admission-v1",
  status: "NOT_IN_REPORT",
  admission_scope: "HYPOTHESIS_BATCH",
  hypothesis_id: null,
  selected_strategy_status: "NOT_IN_REPORT",
  selected_strategy_candidate_count: 0,
  selected_strategy_admitted_count: 0,
  admitted_candidate_count: 0,
  checks: [],
  blockers: ["strategy_not_in_frozen_research_report"],
  descriptive_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  automatic_paper_activation_allowed: false,
  research_only: true,
  paper_authorized: false,
  live_order_allowed: false,
};
const schema12Unmatched = evidence.strategyLabEvidencePresentation(schema12UnmatchedPayload);
assert.equal(schema12Unmatched.valid, true);
assert.equal(schema12Unmatched.rawAdmissionStatus, "NOT_IN_REPORT");
assert.equal(
  schema12Unmatched.admissionText,
  "当前策略不在报告 · 不借用本批事前门禁结论",
);
assert.ok(!schema12Unmatched.admissionText.includes("PASS"));
assert.ok(!schema12Unmatched.admissionText.includes("未触发"));

const schema12BorrowedGlobalPassAttack = JSON.parse(JSON.stringify(schema12UnmatchedPayload));
schema12BorrowedGlobalPassAttack.scope.strategy_count = 2;
schema12BorrowedGlobalPassAttack.scope.frozen_test_candidate_count = 1;
schema12BorrowedGlobalPassAttack.preregistered_failure_admission_status = "PASS";
schema12BorrowedGlobalPassAttack.evidence_contract.preregistered_failure_admission_status = "PASS";
schema12BorrowedGlobalPassAttack.preregistered_failure_admission.status = "PASS";
schema12BorrowedGlobalPassAttack.preregistered_failure_admission.hypothesis_id =
  "frozen-causal-persistence-v1";
schema12BorrowedGlobalPassAttack.preregistered_failure_admission.admitted_candidate_count = 1;
schema12BorrowedGlobalPassAttack.preregistered_failure_admission.blockers = [];
assert.equal(
  evidence.strategyLabEvidencePresentation(schema12BorrowedGlobalPassAttack).valid,
  false,
  "schema12 NOT_IN_REPORT must not borrow another strategy's global PASS admission",
);
const schema12UnmatchedExtraAdmissionField = JSON.parse(JSON.stringify(schema12UnmatchedPayload));
schema12UnmatchedExtraAdmissionField.preregistered_failure_admission.other_strategy_status = "PASS";
assert.equal(evidence.strategyLabEvidencePresentation(schema12UnmatchedExtraAdmissionField).valid, false);

const unmatchedForgedPassPayload = JSON.parse(JSON.stringify(schema11UnmatchedPayload));
unmatchedForgedPassPayload.scope.frozen_test_candidate_count = 2;
unmatchedForgedPassPayload.scope.test_cell_count = 4;
unmatchedForgedPassPayload.scope.forward_candidate_count = 2;
unmatchedForgedPassPayload.post_selection_replay_summary = postSelectionSummary(
  11,
  "PASS",
  "PASS",
);
unmatchedForgedPassPayload.post_selection_replay_status = "PASS";
unmatchedForgedPassPayload.evidence_contract.post_selection_replay_status = "PASS";
assert.equal(
  evidence.strategyLabEvidencePresentation(unmatchedForgedPassPayload).valid,
  false,
  "a strategy not present in the report cannot borrow another strategy's PASS replay or returns",
);

const neutralStrategyStatus = evidence.researchEvidenceStatusPresentation("PAPER_READY");
assert.equal(neutralStrategyStatus.label, "研究证据已核对 · 非授权");
assert.equal(neutralStrategyStatus.stateKind, "verified");
assert.ok(!neutralStrategyStatus.label.includes("READY"));
assert.equal(evidence.researchEvidenceStatusPresentation("RESEARCH_VERIFIED").stateKind, "verified");
assert.equal(evidence.researchEvidenceStatusPresentation("RESEARCH_REVIEW").stateKind, "active");
assert.equal(evidence.researchEvidenceStatusPresentation("RESEARCH_BLOCKED").stateKind, "blocked");
assert.equal(evidence.researchEvidenceStatusPresentation("RESEARCH_OBSERVE").label, "研究观察 · 待核验");

const emptyBacktest = evidence.backtestEvidencePresentation();
assert.equal(emptyBacktest.returnText, "累计收益未提供");
assert.equal(emptyBacktest.benchmarkText, "基准收益未提供");
assert.equal(emptyBacktest.sampleText, "样本量未提供");
assert.equal(emptyBacktest.tradesText, "闭合交易数未提供");
assert.equal(emptyBacktest.boundaryText, "开发回测 · 非盈利证明 · 模拟未授权 · 实盘永久硬锁");

const unbenchmarkedBacktest = evidence.backtestEvidencePresentation({
  current: {
    ok: true,
    total_return_pct: 12.34,
    annualized_pct: 8,
    max_drawdown_pct: 6.5,
    win_rate_pct: 55,
    sharpe: 1.1,
  },
  reproducibility: { data_points: 1800 },
  temporalStatus: "PASS",
});
assert.equal(unbenchmarkedBacktest.returnText, "+12.34%");
assert.equal(unbenchmarkedBacktest.benchmarkText, "基准收益未提供");
assert.equal(unbenchmarkedBacktest.excessText, "超额收益不可计算");
assert.equal(unbenchmarkedBacktest.tradesText, "闭合交易数未提供");
assert.equal(unbenchmarkedBacktest.sampleText, "1800 根 K 线");
assert.equal(unbenchmarkedBacktest.returnBasisText, "成本是否计入未核验 · 不得视为净收益");
assert.equal(unbenchmarkedBacktest.temporalText, "样本外证据已记录 · 非授权");
assert.ok(!unbenchmarkedBacktest.temporalText.includes("PASS"));

const costExcludedBacktest = evidence.backtestEvidencePresentation({
  current: { ok: true, total_return_pct: 12.34, trade_count: 24 },
  benchmarkReturnPct: 5,
  reproducibility: { fee_rate: "0.001", slippage_bps: "3" },
  costsIncluded: false,
});
assert.equal(costExcludedBacktest.benchmarkText, "+5.00%");
assert.equal(costExcludedBacktest.excessText, "超额 +7.34%");
assert.equal(costExcludedBacktest.costsText, "费率 0.001 · 滑点 3 bps");
assert.equal(costExcludedBacktest.returnBasisText, "返回合同声明未计入成本 · 非净收益");
assert.equal(costExcludedBacktest.tradesText, "24 笔闭合交易");

function riskControlSurfaceFixture() {
  const grid = {
    position_pct: [12, 20, 35, 50, 70],
    take_profit_pct: [1.2, 1.8, 2.6, 3.8, 5.5],
    stop_loss_pct: [0.7, 1.1, 1.6, 2.4],
  };
  const cells = [];
  grid.position_pct.forEach((position) => {
    grid.take_profit_pct.forEach((take) => {
      grid.stop_loss_pct.forEach((stop) => {
        const center = position === 35 && take === 2.6 && stop === 1.1;
        const adjacent = (
          ([20, 50].includes(position) && take === 2.6 && stop === 1.1)
          || (position === 35 && [1.8, 3.8].includes(take) && stop === 1.1)
          || (position === 35 && take === 2.6 && [0.7, 1.6].includes(stop))
        );
        cells.push({
          cell_id: `position_pct=${position}|take_profit_pct=${take}|stop_loss_pct=${stop}`,
          position_pct: position,
          take_profit_pct: take,
          stop_loss_pct: stop,
          score: center ? 10 : adjacent ? 9 : 0,
          total_return_pct: 2,
          max_drawdown_pct: 5,
          trade_count: 4,
          run_ok: true,
          quality_usable: true,
        });
      });
    });
  });
  const highest = cells.find((cell) => cell.score === 10);
  const connected = cells.filter((cell) => cell.score >= 9).map((cell) => cell.cell_id);
  return {
    schema_version: "backtest-risk-control-surface-v1",
    status: "LOCAL_PLATEAU",
    scope: "SAME_DATASET_DEVELOPMENT_GRID",
    topology_basis: "ONE_FROZEN_GRID_STEP_PER_AXIS",
    grid_axis_order: ["position_pct", "take_profit_pct", "stop_loss_pct"],
    grid_axes: grid,
    expected_cell_count: 100,
    received_candidate_count: 100,
    mapped_cell_count: 100,
    missing_cell_count: 0,
    invalid_metric_count: 0,
    scored_cell_count: 100,
    usable_cell_count: 100,
    highest_score_cell: { ...highest },
    score_tolerance: 2.5,
    score_tolerance_basis: "MAX_25_PERCENT_OF_BEST_ABSOLUTE_OR_1_POINT",
    near_best_scored_cell_count: 7,
    near_best_usable_cell_count: 7,
    direct_adjacent_near_best_usable_count: 6,
    axis_support: { position_pct: 2, take_profit_pct: 2, stop_loss_pct: 2 },
    supported_axis_count: 3,
    connected_near_best_cell_count: 7,
    connected_near_best_cell_ids: connected,
    cells,
    blockers: [],
    risk_control_parameters_only: true,
    signal_parameter_stability_checked: false,
    numeric_parameter_distance_checked: false,
    same_dataset_grid: true,
    selection_bias_corrected: false,
    out_of_sample_parameter_validation: false,
    frozen_research_evidence: false,
    research_only: true,
    descriptive_only: true,
    parameter_selection_allowed: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    automatic_paper_activation_allowed: false,
    execution_allowed: false,
    order_submission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

const robustnessEvidence = evidence.backtestRobustnessPresentation({
  risk_control_surface: riskControlSurfaceFixture(),
  temporal_validation: {
    status: "PASS",
    temporal_status: "PASS",
    temporal_blockers: [],
    data_split: {
      segments: {
        validation: { count: 120 },
        test: { count: 120 },
      },
    },
    temporal_segments: {
      validation: { total_return_pct: 4.25 },
      test: { total_return_pct: 1.75 },
    },
    walk_forward: {
      status: "PASS",
      evaluation_mode: "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
      parameters_refit_per_fold: false,
      walk_forward_optimization_claim_allowed: false,
      fold_count: 3,
      usable_folds: 3,
      positive_folds: 2,
      total_trades: 8,
      blockers: [],
    },
    cost_sensitivity: {
      status: "PASS",
      worst_return_pct: 1.1,
      break_even_preserved: true,
      blockers: [],
      scenarios: [{ total_return_pct: 1.1 }],
    },
  },
  lookahead_check: { status: "PASS", blockers: [] },
  selection_evidence: { status: "PASS" },
});
assert.equal(robustnessEvidence.valid, true);
assert.equal(robustnessEvidence.modeText, "固定参数时间切片 · 非真正 walk-forward optimization");
assert.ok(robustnessEvidence.temporalText.includes("验证 120 行"));
assert.ok(robustnessEvidence.temporalText.includes("测试 120 行"));
assert.ok(robustnessEvidence.foldsText.includes("正收益 2"));
assert.ok(robustnessEvidence.costText.includes("+1.10%"));
assert.ok(robustnessEvidence.costText.includes("压力仍保持正值"));
assert.ok(robustnessEvidence.parameterText.includes("仅仓位/止盈/止损"));
assert.ok(robustnessEvidence.parameterText.includes("策略信号参数平台仍需冻结报告"));
assert.ok(robustnessEvidence.surfaceStatusText.includes("跨至少两条"));
assert.ok(robustnessEvidence.surfaceCoverageText.includes("100/100"));
assert.ok(robustnessEvidence.surfaceNeighborhoodText.includes("直接支撑轴 3/3"));
assert.equal(robustnessEvidence.rawSurfaceStatus, "LOCAL_PLATEAU");
assert.ok(!robustnessEvidence.temporalText.includes("PASS"));
assert.equal(robustnessEvidence.rawCostStatus, "PASS");

const blockedRobustness = evidence.backtestRobustnessPresentation({
  temporal_validation: {
    status: "BLOCK",
    temporal_status: "BLOCK",
    temporal_blockers: ["test segment return is not positive"],
    walk_forward: {
      status: "BLOCK",
      blockers: ["fold evidence incomplete"],
    },
    cost_sensitivity: {
      status: "BLOCK",
      worst_return_pct: -0.3,
      break_even_preserved: false,
      blockers: ["stressed return is not positive"],
    },
  },
  lookahead_check: { status: "BLOCK", blockers: ["future data risk"] },
});
assert.equal(blockedRobustness.valid, true);
assert.ok(blockedRobustness.costText.includes("-0.30%"));
assert.ok(blockedRobustness.costText.includes("压力未保持正值"));
assert.ok(blockedRobustness.failureText.includes("stressed return is not positive"));
assert.ok(blockedRobustness.failureText.includes("future data risk"));

const incompleteRobustness = evidence.backtestRobustnessPresentation({
  temporal_validation: { status: "BLOCK", cost_sensitivity: { status: "BLOCK" } },
});
assert.equal(incompleteRobustness.valid, true);
assert.ok(incompleteRobustness.temporalText.includes("未提供"));
assert.ok(incompleteRobustness.costText.includes("未提供"));
assert.ok(!incompleteRobustness.temporalText.includes("0 行"));
const missingStressRobustness = evidence.backtestRobustnessPresentation({
  temporal_validation: {
    cost_sensitivity: {
      status: "BLOCK",
      worst_return_pct: null,
      break_even_preserved: null,
      blockers: ["可用压力场景收益或回撤缺失/非有限"],
    },
  },
});
assert.ok(missingStressRobustness.costText.includes("正值条件未核验"));
assert.ok(!missingStressRobustness.costText.includes("压力未保持正值"));

const invalidSurfacePayload = { risk_control_surface: riskControlSurfaceFixture() };
invalidSurfacePayload.risk_control_surface.parameter_selection_allowed = true;
assert.equal(evidence.backtestRobustnessPresentation(invalidSurfacePayload).valid, false);

const forgedSurfaceSummary = { risk_control_surface: riskControlSurfaceFixture() };
forgedSurfaceSummary.risk_control_surface.connected_near_best_cell_count = 99;
assert.equal(evidence.backtestRobustnessPresentation(forgedSurfaceSummary).valid, false);

const forgedSurfaceCell = { risk_control_surface: riskControlSurfaceFixture() };
forgedSurfaceCell.risk_control_surface.cells[0].score = 99;
assert.equal(evidence.backtestRobustnessPresentation(forgedSurfaceCell).valid, false);

const frozenScope = {
  research_only: true,
  profitability_proven: false,
  performance_claim_allowed: false,
  parameter_selection_allowed: false,
  automatic_paper_activation_allowed: false,
  paper_authorized: false,
  live_order_allowed: false,
};
const verifiedFrozenQualityPayload = {
  schema_version: "portfolio-backtest-return-quality-snapshot-v3",
  ok: true,
  status: "AVAILABLE",
  source_verification_status: "PASS",
  generated_at: 1720000000000,
  candidate_hash: "a".repeat(64),
  pack_hash: "b".repeat(64),
  evidence_hash: "c".repeat(64),
  pack_schema_version: "portfolio-internal-backtest-pack-v4",
  pack_status: "INTERNAL_BACKTEST_EVIDENCE_READY",
  promotion_status: "BLOCK",
  ...frozenScope,
  return_quality: {
    schema_version: "backtest-return-quality-v2",
    status: "BLOCK",
    interpretation: "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY",
    summary: {
      strategy_return_pct: 3,
      benchmark_return_pct: 2,
      benchmark_excess_return_pct: 1,
      cost_after_return_pct: 2.5,
      worst_stress_return_pct: -0.5,
      max_drawdown_pct: 7,
      sample_size: 120,
      evidence_stage: "DEVELOPMENT_HISTORICAL",
    },
    stages: {
      validation: {
        stage: "DEVELOPMENT_VALIDATION",
        evidence_status: "PASS",
        benchmark_excess_status: "PASS",
        benchmark_excess_basis: "strategy_and_benchmark_runs",
        strategy_return_pct: 3,
        benchmark_return_pct: 2,
        benchmark_excess_return_pct: 1,
        reported_benchmark_excess_return_pct: 1,
        strategy_max_drawdown_pct: 7,
        benchmark_max_drawdown_pct: 8,
        drawdown_improvement_pct: 1,
        sample: {
          evaluated_rows: 120,
          order_event_count: 10,
          decision_event_count: 20,
          paired_return_observation_count: 120,
        },
        statistical_claim: {
          status: "PASS",
          observed_strategy_compound_return_pct: 3,
          observed_benchmark_compound_return_pct: 2,
          observed_compound_excess_return_pct: 1,
          blockers: [],
        },
      },
      test: {
        stage: "DEVELOPMENT_TEST",
        evidence_status: "BLOCK",
        benchmark_excess_status: "PASS",
        benchmark_excess_basis: "strategy_and_benchmark_runs",
        strategy_return_pct: 3,
        benchmark_return_pct: 2,
        benchmark_excess_return_pct: 1,
        reported_benchmark_excess_return_pct: 1,
        strategy_max_drawdown_pct: 7,
        benchmark_max_drawdown_pct: 8,
        drawdown_improvement_pct: 1,
        sample: {
          evaluated_rows: 120,
          order_event_count: 10,
          decision_event_count: 20,
          paired_return_observation_count: 120,
        },
        statistical_claim: {
          status: "BLOCK",
          observed_strategy_compound_return_pct: 3,
          observed_benchmark_compound_return_pct: 2,
          observed_compound_excess_return_pct: 1,
          blockers: ["historical_statistical_claim_block"],
        },
      },
    },
    failure_conditions: {
      observed: ["historical_statistical_claim_block"],
      evidence_gaps: ["natural_forward_observation_required"],
    },
    cost_after: {
      baseline_model: {
        fee_rate: 0.0005,
        slippage_bps: 2,
        test_return_after_configured_costs_pct: 2.5,
        configured_costs_declared_in_test_run: true,
      },
    },
    ...frozenScope,
  },
  forward_promotion: {
    schema_version: "portfolio-backtest-forward-promotion-summary-v1",
    status: "RESEARCH_REVIEW_BLOCKED",
    source_integrity_status: "PASS",
    maturity: {
      status: "DUE",
      forward_outcomes: 60,
      required_forward_outcomes: 60,
      remaining_forward_outcomes: 0,
      executed_rebalances: 8,
      required_executed_rebalances: 8,
      remaining_executed_rebalances: 0,
      both_thresholds_required: true,
    },
    audit: {
      status: "BLOCK",
      conclusion: "FORWARD_STATISTICAL_CONTRACT_FAILED",
      verification_status: "PASS",
      semantic_recomputed: true,
      audit_hash: "d".repeat(64),
      series_hash: "e".repeat(64),
    },
    readiness_status: "RESEARCH_REVIEW_BLOCKED",
    readiness_promotion_status: "BLOCK",
    historical_contract_claim_status: "BLOCK",
    blockers: ["natural_forward_statistical_evidence_not_passed"],
    promotion_blockers: ["natural_forward_statistical_evidence_not_passed"],
    validation_scope: {
      pack_validates_upstream_semantic_receipt: true,
      settlement_database_reloaded_by_pack: false,
      settlement_chain_independently_replayed_by_pack: false,
      full_forward_rows_hash_bound: true,
    },
    manual_review_required: true,
    ...frozenScope,
  },
};
const verifiedFrozenQuality = evidence.internalBacktestReturnQualityPresentation(verifiedFrozenQualityPayload);
assert.equal(verifiedFrozenQuality.verified, true);
assert.equal(verifiedFrozenQuality.connectionStatus, "VERIFIED");
assert.equal(
  verifiedFrozenQuality.statusText,
  "来源与合同已核验 · 仅作历史描述 · 非盈利证明",
);
assert.equal(verifiedFrozenQuality.returnsText, "策略 3.00% · 基准 2.00% · 重算超额 1.00%");
assert.equal(verifiedFrozenQuality.costText, "成本口径已绑定 · 成本后 2.50%");
assert.equal(verifiedFrozenQuality.riskText, "压力最差 -0.50% · 最大回撤 7.00%");
assert.equal(verifiedFrozenQuality.validationStageText, "验证段：阶段已核对 · 样本 120 · 基准超额已核对 · 统计口径已核对");
assert.equal(verifiedFrozenQuality.testStageText, "测试段：阶段有阻断 · 样本 120 · 基准超额已核对 · 统计口径有阻断");
assert.equal(verifiedFrozenQuality.validationStageRawStatus, "PASS");
assert.equal(verifiedFrozenQuality.testStageRawClaimStatus, "BLOCK");
assert.equal(
  verifiedFrozenQuality.forwardStatusText,
  "自然前向形成有效负结果 · 研究晋级阻断",
);
assert.equal(
  verifiedFrozenQuality.forwardMaturityText,
  "收益期 60/60 · 实际调仓 8/8 · 双门槛同时要求",
);
assert.equal(
  verifiedFrozenQuality.maturityCueText,
  "自然前向形成有效负结果 · 研究晋级阻断 · 收益期 60/60 · 实际调仓 8/8 · 双门槛同时要求",
);
assert.ok(verifiedFrozenQuality.forwardBoundaryText.includes("未重载数据库"));
assert.ok(verifiedFrozenQuality.forwardBoundaryText.includes("未独立重放结算链"));
assert.equal(verifiedFrozenQuality.rawForwardStatus, "RESEARCH_REVIEW_BLOCKED");
assert.ok(verifiedFrozenQuality.forwardSourceText.includes("dddddddd"));
assert.equal(verifiedFrozenQuality.evidenceGapKind, "OBSERVED_BLOCK");
assert.equal(verifiedFrozenQuality.evidenceGapCount, 2);
assert.equal(
  verifiedFrozenQuality.evidenceGapText,
  "已形成有效负结果，停止晋级 · 已观察失效 1 项 · 待补研究证据 1 项",
);
assert.ok(!verifiedFrozenQuality.statusText.includes("研究阻断"));
assert.ok(verifiedFrozenQuality.evidenceGapText.includes("有效负结果"));
assert.equal(verifiedFrozenQuality.failureText, verifiedFrozenQuality.evidenceGapText);
assert.equal(verifiedFrozenQuality.sourceText, "冻结来源已核验 · 包 bbbbbbbbbbbb…");
assert.equal(verifiedFrozenQuality.rawPackSchema, "portfolio-internal-backtest-pack-v4");
assert.equal(verifiedFrozenQuality.rawQualitySchema, "backtest-return-quality-v2");
assert.equal(verifiedFrozenQuality.sourceMode, "SOURCE_EVIDENCE_V2");
assert.equal(verifiedFrozenQuality.generatedAt, 1720000000000);
assert.ok(!verifiedFrozenQuality.statusText.includes("READY"));

const verifiedCompactBundleQualityPayload = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
verifiedCompactBundleQualityPayload.pack_schema_version = "portfolio-internal-backtest-pack-v5";
verifiedCompactBundleQualityPayload.return_quality.schema_version = "backtest-return-quality-v3";
const verifiedCompactBundleQuality = evidence.internalBacktestReturnQualityPresentation(
  verifiedCompactBundleQualityPayload,
);
assert.equal(verifiedCompactBundleQuality.verified, true);
assert.equal(verifiedCompactBundleQuality.connectionStatus, "VERIFIED");
assert.equal(
  verifiedCompactBundleQuality.statusText,
  "紧凑 bundle 来源与合同已复算核验 · 仅作历史描述 · 非盈利证明",
);
assert.equal(
  verifiedCompactBundleQuality.sourceText,
  "紧凑 bundle 来源已复算 · 包 bbbbbbbbbbbb…",
);
assert.equal(verifiedCompactBundleQuality.rawForwardStatus, "RESEARCH_REVIEW_BLOCKED");
assert.equal(verifiedCompactBundleQuality.rawPackSchema, "portfolio-internal-backtest-pack-v5");
assert.equal(verifiedCompactBundleQuality.rawQualitySchema, "backtest-return-quality-v3");
assert.equal(verifiedCompactBundleQuality.sourceMode, "COMPACT_BUNDLE_RECOMPUTED");
assert.ok(!verifiedCompactBundleQuality.sourceText.includes("source_identity"));
assert.ok(!verifiedCompactBundleQuality.sourceText.includes("identity_hash"));
assert.ok(!verifiedCompactBundleQuality.sourceText.includes("外部真实性"));

const redactedFailureQualityPayload = JSON.parse(JSON.stringify(verifiedCompactBundleQualityPayload));
redactedFailureQualityPayload.return_quality.failure_conditions = {
  source_integrity: ["C:\\private\\reports\\candidate-secret.json"],
  observed: [`candidate_hash=${"f".repeat(64)}`],
  evidence_gaps: ["hidden_identity=portfolio-candidate-42"],
  promotion_gaps: ["收益 999.99%"],
};
const redactedFailureQuality = evidence.internalBacktestReturnQualityPresentation(
  redactedFailureQualityPayload,
);
assert.equal(redactedFailureQuality.verified, true);
assert.equal(redactedFailureQuality.evidenceGapKind, "SOURCE_BLOCK");
assert.equal(redactedFailureQuality.evidenceGapCount, 4);
assert.equal(
  redactedFailureQuality.evidenceGapText,
  "来源完整性 1 项 · 已观察失效 1 项 · 待补研究证据 1 项 · 晋级复核缺口 1 项；停止使用当前数字，先修复固定来源",
);
[
  "C:\\private",
  "candidate-secret",
  "candidate_hash",
  "hidden_identity",
  "portfolio-candidate-42",
  "999.99%",
  "f".repeat(64),
].forEach((secret) => {
  assert.ok(!redactedFailureQuality.evidenceGapText.includes(secret));
  assert.ok(!redactedFailureQuality.failureText.includes(secret));
});

const authorityTamperedQuality = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  return_quality: { ...verifiedFrozenQualityPayload.return_quality, paper_authorized: true },
});
assert.equal(authorityTamperedQuality.verified, false);
assert.equal(authorityTamperedQuality.statusText, "来源与合同未核验 · 当前数字不可用");
assert.equal(authorityTamperedQuality.evidenceGapKind, "SAFETY_BOUNDARY");
const nestedAuthorityTamperedQuality = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  nested: { execution_allowed: true },
});
assert.equal(nestedAuthorityTamperedQuality.verified, false);

for (const [alias, value] of [
  ["canTrade", true],
  ["Paper_Authorized", true],
  ["live-order-allowed", true],
  ["可下单", true],
  ["已授权", true],
  ["实盘-授权", true],
]) {
  const aliasAuthorityTamperedQuality = evidence.internalBacktestReturnQualityPresentation({
    ...verifiedCompactBundleQualityPayload,
    untrusted_extension: { [alias]: value },
  });
  assert.equal(aliasAuthorityTamperedQuality.verified, false, `${alias} must fail closed`);
  assert.equal(aliasAuthorityTamperedQuality.connectionStatus, "UNKNOWN");
  assert.equal(aliasAuthorityTamperedQuality.returnsText, "策略 -- · 基准 -- · 重算超额 --");
  assert.equal(aliasAuthorityTamperedQuality.evidenceGapKind, "SAFETY_BOUNDARY");
  assert.ok(!aliasAuthorityTamperedQuality.evidenceGapText.includes(alias));
}

for (const [field, mutate] of [
  ["stage", (payload, marker) => { payload.return_quality.stages.validation.stage = marker; }],
  ["benchmark basis", (payload, marker) => {
    payload.return_quality.stages.validation.benchmark_excess_basis = marker;
  }],
  ["stage status", (payload, marker) => {
    payload.return_quality.stages.validation.evidence_status = marker;
  }],
  ["benchmark status", (payload, marker) => {
    payload.return_quality.stages.validation.benchmark_excess_status = marker;
  }],
  ["claim status", (payload, marker) => {
    payload.return_quality.stages.validation.statistical_claim.status = marker;
  }],
  ["summary stage", (payload, marker) => {
    payload.return_quality.summary.evidence_stage = marker;
  }],
]) {
  const marker = `C:\\private\\raw=${"d".repeat(64)} 999.99%`;
  const tampered = JSON.parse(JSON.stringify(verifiedCompactBundleQualityPayload));
  mutate(tampered, marker);
  const presentation = evidence.internalBacktestReturnQualityPresentation(tampered);
  assert.equal(presentation.verified, false, `${field} must fail closed`);
  assert.equal(presentation.evidenceGapKind, "STAGE_EVIDENCE");
  [
    presentation.validationStageText,
    presentation.validationStageDetailText,
    presentation.sampleText,
    presentation.evidenceGapText,
    presentation.validationStageRawStatus,
    presentation.validationStageRawBenchmarkStatus,
    presentation.validationStageRawClaimStatus,
  ].forEach((value) => assert.ok(!String(value).includes(marker)));
}

const inconsistentExcessQuality = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  return_quality: {
    ...verifiedFrozenQualityPayload.return_quality,
    summary: { ...verifiedFrozenQualityPayload.return_quality.summary, benchmark_excess_return_pct: 99 },
  },
});
assert.equal(inconsistentExcessQuality.verified, false);
assert.equal(inconsistentExcessQuality.evidenceGapKind, "VALUE_CONSISTENCY");
const incompleteStageQuality = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  return_quality: {
    ...verifiedFrozenQualityPayload.return_quality,
    stages: {
      ...verifiedFrozenQualityPayload.return_quality.stages,
      test: {
        ...verifiedFrozenQualityPayload.return_quality.stages.test,
        sample: { ...verifiedFrozenQualityPayload.return_quality.stages.test.sample, evaluated_rows: "120" },
      },
    },
  },
});
assert.equal(incompleteStageQuality.verified, false);
assert.equal(incompleteStageQuality.evidenceGapKind, "STAGE_EVIDENCE");
const availableUnknownStageQuality = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  return_quality: {
    ...verifiedFrozenQualityPayload.return_quality,
    status: "AVAILABLE",
    stages: {
      ...verifiedFrozenQualityPayload.return_quality.stages,
      test: {
        ...verifiedFrozenQualityPayload.return_quality.stages.test,
        evidence_status: "UNKNOWN",
        benchmark_excess_status: "UNKNOWN",
        sample: {
          evaluated_rows: null,
          order_event_count: null,
          decision_event_count: null,
          paired_return_observation_count: null,
        },
        statistical_claim: {
          ...verifiedFrozenQualityPayload.return_quality.stages.test.statistical_claim,
          status: "UNKNOWN",
        },
      },
    },
  },
});
assert.equal(availableUnknownStageQuality.verified, false);
assert.equal(availableUnknownStageQuality.evidenceGapKind, "STAGE_EVIDENCE");

const collectingForwardQuality = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
collectingForwardQuality.forward_promotion.status = "COLLECTING";
collectingForwardQuality.forward_promotion.maturity.status = "NOT_DUE";
collectingForwardQuality.forward_promotion.maturity.forward_outcomes = 31;
collectingForwardQuality.forward_promotion.maturity.remaining_forward_outcomes = 29;
collectingForwardQuality.forward_promotion.maturity.executed_rebalances = 4;
collectingForwardQuality.forward_promotion.maturity.remaining_executed_rebalances = 4;
collectingForwardQuality.forward_promotion.audit.status = "NOT_DUE";
collectingForwardQuality.forward_promotion.audit.conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE";
collectingForwardQuality.forward_promotion.readiness_status = "COLLECTING";
collectingForwardQuality.forward_promotion.promotion_blockers = [
  "natural_forward_statistical_evidence_not_mature",
];
const collectingForwardPresentation = evidence.internalBacktestReturnQualityPresentation(
  collectingForwardQuality,
);
assert.equal(collectingForwardPresentation.verified, true);
assert.ok(collectingForwardPresentation.forwardStatusText.includes("仍在收集"));
assert.ok(collectingForwardPresentation.forwardMaturityText.includes("31/60"));
assert.ok(collectingForwardPresentation.maturityCueText.includes("仍在收集"));
assert.ok(collectingForwardPresentation.maturityCueText.includes("31/60"));

const readyForwardQuality = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
readyForwardQuality.promotion_status = "REVIEW_REQUIRED";
readyForwardQuality.forward_promotion.status = "RESEARCH_REVIEW_READY";
readyForwardQuality.forward_promotion.audit.status = "PASS";
readyForwardQuality.forward_promotion.audit.conclusion = "FORWARD_STATISTICAL_CONTRACT_PASS";
readyForwardQuality.forward_promotion.readiness_status = "RESEARCH_REVIEW_READY";
readyForwardQuality.forward_promotion.readiness_promotion_status = "REVIEW_REQUIRED";
readyForwardQuality.forward_promotion.blockers = [];
readyForwardQuality.forward_promotion.promotion_blockers = [];
const readyForwardPresentation = evidence.internalBacktestReturnQualityPresentation(
  readyForwardQuality,
);
assert.equal(readyForwardPresentation.verified, true);
assert.ok(readyForwardPresentation.forwardStatusText.includes("等待人工研究复核"));
assert.ok(!readyForwardPresentation.forwardStatusText.includes("READY"));

const forwardReadyButPackBlocked = JSON.parse(JSON.stringify(readyForwardQuality));
forwardReadyButPackBlocked.pack_status = "INTERNAL_BACKTEST_BLOCKED";
forwardReadyButPackBlocked.promotion_status = "BLOCK";
forwardReadyButPackBlocked.forward_promotion.promotion_blockers = [
  "internal_backtest_evidence_ready",
];
const forwardReadyButPackBlockedPresentation = evidence.internalBacktestReturnQualityPresentation(
  forwardReadyButPackBlocked,
);
assert.equal(forwardReadyButPackBlockedPresentation.verified, true);
assert.equal(
  forwardReadyButPackBlockedPresentation.forwardStatusText,
  "自然前向统计已到期 · 其他包内证据阻断",
);

const forgedForwardMaturity = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
forgedForwardMaturity.forward_promotion.maturity.remaining_forward_outcomes = 9;
const forgedForwardMaturityPresentation = evidence.internalBacktestReturnQualityPresentation(
  forgedForwardMaturity,
);
assert.equal(forgedForwardMaturityPresentation.verified, false);
assert.equal(forgedForwardMaturityPresentation.evidenceGapKind, "FORWARD_EVIDENCE");

for (const [coupling, sourcePayload] of [
  ["pack-v4", verifiedFrozenQualityPayload],
  ["pack-v5", verifiedCompactBundleQualityPayload],
]) {
  for (const [caseName, mutate] of [
    ["zero-required-thresholds", (maturity) => {
      maturity.forward_outcomes = 0;
      maturity.required_forward_outcomes = 0;
      maturity.remaining_forward_outcomes = 0;
      maturity.executed_rebalances = 0;
      maturity.required_executed_rebalances = 0;
      maturity.remaining_executed_rebalances = 0;
    }],
    ["unsafe-integer", (maturity) => {
      maturity.forward_outcomes = Number.MAX_SAFE_INTEGER + 1;
    }],
    ["rebalance-count-exceeds-outcomes", (maturity) => {
      maturity.forward_outcomes = 7;
      maturity.required_forward_outcomes = 7;
      maturity.remaining_forward_outcomes = 0;
      maturity.executed_rebalances = 8;
      maturity.required_executed_rebalances = 8;
      maturity.remaining_executed_rebalances = 0;
    }],
  ]) {
    const invalidCounts = JSON.parse(JSON.stringify(sourcePayload));
    mutate(invalidCounts.forward_promotion.maturity);

    const presentation = evidence.internalBacktestReturnQualityPresentation(invalidCounts);

    assert.equal(presentation.verified, false, `${coupling}/${caseName} must fail closed`);
    assert.equal(presentation.evidenceGapKind, "FORWARD_EVIDENCE");
    assert.equal(presentation.rawForwardMaturityStatus, "UNKNOWN");
    assert.equal(
      presentation.maturityCueText,
      "自然前向成熟度未核验 · 收益期 --/-- · 实际调仓 --/--",
    );
    assert.equal(presentation.returnsText, "策略 -- · 基准 -- · 重算超额 --");
  }
}

const unsafeForwardScope = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
unsafeForwardScope.forward_promotion.validation_scope.settlement_database_reloaded_by_pack = true;
assert.equal(evidence.internalBacktestReturnQualityPresentation(unsafeForwardScope).verified, false);

const legacyV2FrozenQuality = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
legacyV2FrozenQuality.pack_schema_version = "portfolio-internal-backtest-pack-v2";
legacyV2FrozenQuality.pack_status = "INTERNAL_BACKTEST_BLOCKED";
legacyV2FrozenQuality.return_quality.schema_version = "backtest-return-quality-v1";
legacyV2FrozenQuality.forward_promotion = null;
const legacyV2FrozenPresentation = evidence.internalBacktestReturnQualityPresentation(
  legacyV2FrozenQuality,
);
assert.equal(legacyV2FrozenPresentation.verified, false);
assert.equal(legacyV2FrozenPresentation.connectionStatus, "UNKNOWN");
assert.equal(legacyV2FrozenPresentation.qualityState, "UNKNOWN");
assert.equal(legacyV2FrozenPresentation.rawForwardStatus, "UNKNOWN");
assert.equal(legacyV2FrozenPresentation.evidenceGapKind, "VERSION_BINDING");

const legacyV3FrozenQuality = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
legacyV3FrozenQuality.pack_schema_version = "portfolio-internal-backtest-pack-v3";
legacyV3FrozenQuality.return_quality.schema_version = "backtest-return-quality-v1";
const legacyV3FrozenPresentation = evidence.internalBacktestReturnQualityPresentation(
  legacyV3FrozenQuality,
);
assert.equal(legacyV3FrozenPresentation.verified, false);
assert.equal(legacyV3FrozenPresentation.connectionStatus, "UNKNOWN");
assert.equal(legacyV3FrozenPresentation.qualityState, "UNKNOWN");
assert.equal(legacyV3FrozenPresentation.rawForwardStatus, "UNKNOWN");
assert.equal(legacyV3FrozenPresentation.evidenceGapKind, "VERSION_BINDING");

const missingForwardQuality = JSON.parse(JSON.stringify(verifiedCompactBundleQualityPayload));
missingForwardQuality.forward_promotion = null;
const missingForwardPresentation = evidence.internalBacktestReturnQualityPresentation(
  missingForwardQuality,
);
assert.equal(missingForwardPresentation.verified, false);
assert.equal(missingForwardPresentation.evidenceGapKind, "FORWARD_EVIDENCE");

const futureForwardSchemaQuality = JSON.parse(JSON.stringify(verifiedCompactBundleQualityPayload));
futureForwardSchemaQuality.forward_promotion.schema_version = "portfolio-backtest-forward-promotion-summary-v2";
const futureForwardSchemaPresentation = evidence.internalBacktestReturnQualityPresentation(
  futureForwardSchemaQuality,
);
assert.equal(futureForwardSchemaPresentation.verified, false);
assert.equal(futureForwardSchemaPresentation.evidenceGapKind, "VERSION_BINDING");

const invalidPackQualityCouplings = [
  {
    ...verifiedFrozenQualityPayload,
    return_quality: {
      ...verifiedFrozenQualityPayload.return_quality,
      schema_version: "backtest-return-quality-v1",
    },
  },
  {
    ...legacyV3FrozenQuality,
    return_quality: {
      ...legacyV3FrozenQuality.return_quality,
      schema_version: "backtest-return-quality-v2",
    },
  },
  {
    ...legacyV2FrozenQuality,
    return_quality: {
      ...legacyV2FrozenQuality.return_quality,
      schema_version: "backtest-return-quality-v2",
    },
  },
  { ...legacyV2FrozenQuality, forward_promotion: verifiedFrozenQualityPayload.forward_promotion },
  {
    ...verifiedCompactBundleQualityPayload,
    return_quality: {
      ...verifiedCompactBundleQualityPayload.return_quality,
      schema_version: "backtest-return-quality-v2",
    },
  },
  {
    ...verifiedFrozenQualityPayload,
    return_quality: {
      ...verifiedFrozenQualityPayload.return_quality,
      schema_version: "backtest-return-quality-v3",
    },
  },
  {
    ...verifiedCompactBundleQualityPayload,
    pack_schema_version: "portfolio-internal-backtest-pack-v6",
  },
  {
    ...verifiedCompactBundleQualityPayload,
    return_quality: {
      ...verifiedCompactBundleQualityPayload.return_quality,
      schema_version: "backtest-return-quality-v4",
    },
  },
  {
    ...verifiedCompactBundleQualityPayload,
    schema_version: "portfolio-backtest-return-quality-snapshot-v4",
  },
  {
    ...verifiedCompactBundleQualityPayload,
    source_verification_status: "BLOCK",
  },
  {
    ...verifiedCompactBundleQualityPayload,
    forward_promotion: {
      ...verifiedCompactBundleQualityPayload.forward_promotion,
      schema_version: "portfolio-backtest-forward-promotion-summary-v2",
    },
  },
  { ...verifiedCompactBundleQualityPayload, forward_promotion: null },
];
invalidPackQualityCouplings.forEach((payload) => {
  assert.equal(evidence.internalBacktestReturnQualityPresentation(payload).verified, false);
});

const realSingleLookContracts = projectRealSingleLookContracts();
const singleLookSnapshotPresentations = Object.fromEntries(
  ["snapshot_not_due", "snapshot_pass", "snapshot_tail", "snapshot_block"].map((key) => [
    key,
    evidence.internalBacktestReturnQualityPresentation(realSingleLookContracts[key]),
  ]),
);
Object.entries(singleLookSnapshotPresentations).forEach(([key, presentation]) => {
  assert.equal(presentation.verified, true, `${key} real v4 projection must verify`);
  assert.equal(presentation.connectionStatus, "VERIFIED");
  assert.equal(presentation.rawPackSchema, "portfolio-internal-backtest-pack-v6");
  assert.equal(presentation.rawQualitySchema, "backtest-return-quality-v3");
});
assert.equal(singleLookSnapshotPresentations.snapshot_not_due.rawForwardStatus, "COLLECTING");
assert.equal(singleLookSnapshotPresentations.snapshot_not_due.rawForwardMaturityStatus, "NOT_DUE");
assert.equal(singleLookSnapshotPresentations.snapshot_pass.rawForwardStatus, "RESEARCH_REVIEW_READY");
assert.equal(singleLookSnapshotPresentations.snapshot_pass.rawForwardMaturityStatus, "DUE");
assert.equal(singleLookSnapshotPresentations.snapshot_tail.rawForwardStatus, "RESEARCH_REVIEW_READY");
assert.equal(singleLookSnapshotPresentations.snapshot_block.rawForwardStatus, "RESEARCH_REVIEW_BLOCKED");
assert.equal(singleLookSnapshotPresentations.snapshot_block.rawForwardAuditStatus, "BLOCK");
assert.ok(singleLookSnapshotPresentations.snapshot_pass.forwardStatusText.includes("首次到期决策已冻结"));
assert.ok(singleLookSnapshotPresentations.snapshot_tail.forwardMaturityText.includes("后续 4 个仅描述"));
assert.ok(singleLookSnapshotPresentations.snapshot_block.forwardStatusText.includes("停止晋级"));
assert.ok(singleLookSnapshotPresentations.snapshot_tail.forwardBoundaryText.includes("后续样本仅描述"));
assert.equal(
  realSingleLookContracts.snapshot_pass.forward_promotion.decision.decision_hash,
  realSingleLookContracts.snapshot_tail.forward_promotion.decision.decision_hash,
);
assert.equal(
  realSingleLookContracts.snapshot_tail.forward_promotion.tail_observation.frozen_decision_hash,
  realSingleLookContracts.snapshot_tail.forward_promotion.decision.decision_hash,
);

const mutateSingleLookSnapshot = (mutate) => {
  const payload = JSON.parse(JSON.stringify(realSingleLookContracts.snapshot_tail));
  mutate(payload);
  return evidence.internalBacktestReturnQualityPresentation(payload);
};
[
  ["snapshot-extra-key", (payload) => { payload.extra = true; }],
  ["summary-extra-key", (payload) => { payload.forward_promotion.extra = true; }],
  ["decision-extra-key", (payload) => { payload.forward_promotion.decision.extra = true; }],
  ["maturity-extra-key", (payload) => { payload.forward_promotion.maturity.extra = true; }],
  ["prefix-extra-key", (payload) => { payload.forward_promotion.frozen_prefix.extra = true; }],
  ["audit-extra-key", (payload) => { payload.forward_promotion.audit.extra = true; }],
  ["stage-extra-key", (payload) => { payload.forward_promotion.audit.stage.extra = true; }],
  ["risk-extra-key", (payload) => { payload.forward_promotion.audit.risk_acceptance.extra = true; }],
  ["tail-extra-key", (payload) => { payload.forward_promotion.tail_observation.extra = true; }],
  ["scope-extra-key", (payload) => { payload.forward_promotion.validation_scope.extra = true; }],
  ["unsafe-current-count", (payload) => {
    payload.forward_promotion.maturity.forward_outcomes = Number.MAX_SAFE_INTEGER + 1;
  }],
  ["unsafe-prefix-count", (payload) => {
    payload.forward_promotion.frozen_prefix.settlement_count = Number.MAX_SAFE_INTEGER + 1;
  }],
  ["unsafe-tail-count", (payload) => {
    payload.forward_promotion.tail_observation.full_settlement_count = Number.MAX_SAFE_INTEGER + 1;
  }],
  ["missing-risk", (payload) => { payload.forward_promotion.audit.risk_acceptance = null; }],
  ["nonfinite-risk", (payload) => {
    payload.forward_promotion.audit.risk_acceptance.prefix_max_drawdown_pct = Infinity;
  }],
  ["mixed-risk-state", (payload) => {
    payload.forward_promotion.audit.risk_acceptance.status = "BLOCK";
  }],
  ["first-due-index-drift", (payload) => {
    payload.forward_promotion.maturity.first_due_settlement_index += 1;
  }],
  ["first-due-date-invalid", (payload) => {
    payload.forward_promotion.maturity.first_due_settlement_date = "2026-99-99";
  }],
  ["tail-decision-drift", (payload) => {
    payload.forward_promotion.tail_observation.frozen_decision_hash = "f".repeat(64);
  }],
  ["tail-series-drift", (payload) => {
    payload.forward_promotion.tail_observation.full_series_hash = "e".repeat(64);
  }],
  ["tail-used-for-decision", (payload) => {
    payload.forward_promotion.decision.later_settlements_used = true;
  }],
  ["nested-authority", (payload) => {
    payload.forward_promotion.audit.stage.can_trade = true;
  }],
].forEach(([caseName, mutate]) => {
  const presentation = mutateSingleLookSnapshot(mutate);
  assert.equal(presentation.verified, false, `${caseName} must fail closed`);
  assert.equal(presentation.rawForwardStatus, "UNKNOWN");
});

const mixedSingleLookSnapshot = JSON.parse(JSON.stringify(realSingleLookContracts.snapshot_tail));
mixedSingleLookSnapshot.forward_promotion.schema_version = "portfolio-backtest-forward-promotion-summary-v1";
assert.equal(evidence.internalBacktestReturnQualityPresentation(mixedSingleLookSnapshot).verified, false);
assert.equal(
  evidence.internalBacktestReturnQualityPresentation(verifiedCompactBundleQualityPayload).verified,
  true,
  "current snapshot-v3/pack-v5 behavior must remain unchanged",
);

const realDashboardPresentations = Object.fromEntries(
  ["dashboard_not_due", "dashboard_pass", "dashboard_block"].map((key) => [
    key,
    evidence.forwardStatisticalMaturityPresentation(realSingleLookContracts[key]),
  ]),
);
assert.equal(realDashboardPresentations.dashboard_not_due.valid, true);
assert.equal(realDashboardPresentations.dashboard_not_due.rawStatus, "NOT_DUE");
assert.ok(realDashboardPresentations.dashboard_not_due.progressText.includes("尚未形成"));
assert.equal(realDashboardPresentations.dashboard_pass.valid, true);
assert.equal(realDashboardPresentations.dashboard_pass.rawStatus, "REVIEW_REQUIRED");
assert.ok(realDashboardPresentations.dashboard_pass.statusText.includes("已冻结"));
assert.equal(realDashboardPresentations.dashboard_block.valid, true);
assert.equal(realDashboardPresentations.dashboard_block.rawStatus, "STOP_RESEARCH");
assert.ok(realDashboardPresentations.dashboard_block.progressText.includes("后续累计仅描述"));

const mutateSingleLookDashboard = (mutate) => {
  const dashboard = JSON.parse(JSON.stringify(realSingleLookContracts.dashboard_pass));
  mutate(dashboard);
  return evidence.forwardStatisticalMaturityPresentation(dashboard);
};
[
  ["dashboard-extra-key", (dashboard) => { dashboard.extra = true; }],
  ["dashboard-permission-extra-key", (dashboard) => { dashboard.permissions.extra = true; }],
  ["maturity-v3-extra-key", (dashboard) => { dashboard.statistical_maturity.extra = true; }],
  ["maturity-v3-unsafe", (dashboard) => {
    dashboard.statistical_maturity.progress.forward_outcomes = Number.MAX_SAFE_INTEGER + 1;
  }],
  ["maturity-v3-risk-missing", (dashboard) => {
    dashboard.statistical_maturity.risk_acceptance_hash = "";
  }],
  ["maturity-v3-mixed-action", (dashboard) => {
    dashboard.statistical_maturity.research_action = "STOP_RESEARCH";
  }],
  ["maturity-v3-nested-authority", (dashboard) => {
    dashboard.service.can_trade = true;
  }],
  ["maturity-v3-mixed-version", (dashboard) => {
    dashboard.statistical_maturity.schema_version = "portfolio-forward-statistical-maturity-v2";
  }],
].forEach(([caseName, mutate]) => {
  const presentation = mutateSingleLookDashboard(mutate);
  assert.equal(presentation.valid, false, `${caseName} must fail closed`);
  assert.equal(presentation.rawStatus, "BLOCK");
});
const dashboardTail = JSON.parse(JSON.stringify(realSingleLookContracts.dashboard_pass));
const tailProgress = dashboardTail.statistical_maturity.progress;
tailProgress.forward_outcomes += 2;
tailProgress.settlements += 2;
tailProgress.captured_observations += 2;
tailProgress.remaining_forward_outcomes = 0;
const dashboardTailPresentation = evidence.forwardStatisticalMaturityPresentation(dashboardTail);
assert.equal(dashboardTailPresentation.valid, true);
assert.equal(dashboardTailPresentation.rawStatus, "REVIEW_REQUIRED");
assert.ok(dashboardTailPresentation.progressText.includes("后续累计仅描述"));

const nonNumericCompactBundleQuality = JSON.parse(
  JSON.stringify(verifiedCompactBundleQualityPayload),
);
nonNumericCompactBundleQuality.return_quality.summary.strategy_return_pct = "3";
const nonNumericCompactBundlePresentation = evidence.internalBacktestReturnQualityPresentation(
  nonNumericCompactBundleQuality,
);
assert.equal(nonNumericCompactBundlePresentation.verified, false);
assert.equal(nonNumericCompactBundlePresentation.evidenceGapKind, "VALUE_CONSISTENCY");
const nestedAuthorityFrozenQuality = JSON.parse(JSON.stringify(verifiedFrozenQualityPayload));
nestedAuthorityFrozenQuality.return_quality.nested_authority = {
  can_trade: true,
  direction_signal_allowed: true,
};
const nestedAuthorityFrozenPresentation = evidence.internalBacktestReturnQualityPresentation(
  nestedAuthorityFrozenQuality,
);
assert.equal(nestedAuthorityFrozenPresentation.verified, false);
assert.equal(nestedAuthorityFrozenPresentation.evidenceGapKind, "SAFETY_BOUNDARY");
const unavailableFrozenPresentation = evidence.internalBacktestReturnQualityPresentation({ ok: false });
assert.equal(unavailableFrozenPresentation.verified, false);
assert.equal(unavailableFrozenPresentation.evidenceGapKind, "SOURCE");
const invalidFreezeTimePresentation = evidence.internalBacktestReturnQualityPresentation({
  ...verifiedFrozenQualityPayload,
  generated_at: 0,
});
assert.equal(invalidFreezeTimePresentation.verified, false);
assert.equal(invalidFreezeTimePresentation.evidenceGapKind, "SOURCE");

const currentForwardMaturityProgress = {
  forward_outcomes: 3,
  required_forward_outcomes: 12,
  remaining_forward_outcomes: 9,
  settlements: 4,
  captured_observations: 4,
  executed_rebalances: 2,
  required_executed_rebalances: 6,
  remaining_executed_rebalances: 4,
};
const matureForwardMaturityProgress = {
  forward_outcomes: 12,
  required_forward_outcomes: 12,
  remaining_forward_outcomes: 0,
  settlements: 13,
  captured_observations: 13,
  executed_rebalances: 6,
  required_executed_rebalances: 6,
  remaining_executed_rebalances: 0,
};
const currentForwardMaturity = (
  status,
  progress = ["REVIEW_REQUIRED", "STOP_RESEARCH"].includes(status)
    ? matureForwardMaturityProgress
    : currentForwardMaturityProgress,
) => ({
  schema_version: "portfolio-forward-statistical-maturity-v1",
  status,
  candidate_hash: "a".repeat(64),
  progress: { ...progress },
  verification_scope: "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY",
  research_only: true,
  observation_only: true,
  simulation_only: true,
  profitability_proven: false,
  paper_authorized: false,
  live_order_allowed: false,
});
const currentForwardMaturityDashboard = (status, progress) => ({
  schema_version: "portfolio-forward-dashboard-v5",
  candidate_hash: "a".repeat(64),
  statistical_maturity: currentForwardMaturity(status, progress),
});
const currentForwardSourceBinding = (
  status = "NOT_AVAILABLE",
  {
    currentCount = 4,
    anchoredCount = status === "FULL" ? currentCount : status === "PREFIX" ? currentCount - 1 : 0,
  } = {},
) => ({
  schema_version: "portfolio-forward-source-binding-v1",
  status,
  trust_scope: "LOCAL_ARCHIVE_CROSS_ARTIFACT_BINDING_ONLY",
  current_observation_count: currentCount,
  anchored_observation_count: anchoredCount,
  current_settlement_count: currentCount,
  anchored_settlement_count: anchoredCount,
  external_authenticity_proven: false,
  profitability_proven: false,
  research_only: true,
  observation_only: true,
  simulation_only: true,
  paper_authorized: false,
  live_order_allowed: false,
});
const currentForwardMaturityV2 = (
  status,
  progress = ["REVIEW_REQUIRED", "STOP_RESEARCH"].includes(status)
    ? matureForwardMaturityProgress
    : status === "BLOCK"
      ? Object.fromEntries(Object.keys(currentForwardMaturityProgress).map((key) => [key, 0]))
      : currentForwardMaturityProgress,
  sourceBinding = currentForwardSourceBinding("NOT_AVAILABLE", {
    currentCount: progress.settlements,
  }),
) => ({
  ...currentForwardMaturity(status, progress),
  schema_version: "portfolio-forward-statistical-maturity-v2",
  source_binding: sourceBinding,
});
const currentForwardMaturityDashboardV6 = (status, progress, sourceBinding) => ({
  schema_version: "portfolio-forward-dashboard-v6",
  candidate_hash: "a".repeat(64),
  statistical_maturity: currentForwardMaturityV2(status, progress, sourceBinding),
});
const forwardMaturityCopy = {
  NOT_DUE: "统计样本尚未到期 · 不作通过结论",
  REVIEW_REQUIRED: "统计证据已到期 · 等待人工研究复核",
  STOP_RESEARCH: "自然前向形成有效负结果 · 停止研究晋级",
  BLOCK: "统计来源或绑定不可核验 · 不使用成熟度结论",
};
for (const status of ["NOT_DUE", "REVIEW_REQUIRED", "STOP_RESEARCH"]) {
  const maturity = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboard(status),
  );
  assert.equal(maturity.valid, true);
  assert.equal(maturity.available, true);
  assert.equal(maturity.legacy, false);
  assert.equal(maturity.dashboardAuthoritySafe, true);
  assert.equal(maturity.rawStatus, status);
  assert.equal(maturity.statusText, forwardMaturityCopy[status]);
  assert.equal(
    maturity.progressText,
    status === "NOT_DUE"
      ? "结果 3/12 · 调仓 2/6 · 结算 4 · 观察 4"
      : "结果 12/12 · 调仓 6/6 · 结算 13 · 观察 13",
  );
  assert.ok(!maturity.progressText.includes("%"));
}
const sourceBindingCopy = {
  FULL: "本地归档覆盖当前序列 · 仅证明本地跨工件一致",
  PREFIX: "本地归档仅覆盖历史前缀 · 当前尾段未覆盖",
  CONTRADICTION: "本地归档与当前序列矛盾 · 不使用成熟度结论",
  NOT_AVAILABLE: "未取得本地归档覆盖 · 不作来源覆盖结论",
};
for (const [sourceStatus, currentCount, anchoredCount] of [
  ["FULL", 4, 4],
  ["PREFIX", 4, 3],
  ["NOT_AVAILABLE", 4, 0],
]) {
  const sourceBinding = currentForwardSourceBinding(sourceStatus, {
    currentCount,
    anchoredCount,
  });
  const maturity = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboardV6("NOT_DUE", currentForwardMaturityProgress, sourceBinding),
  );
  assert.equal(maturity.valid, true);
  assert.equal(maturity.available, true);
  assert.equal(maturity.dashboardAuthoritySafe, true);
  assert.equal(maturity.sourceBindingRawStatus, sourceStatus);
  assert.equal(maturity.sourceBindingAvailable, ["FULL", "PREFIX"].includes(sourceStatus));
  assert.equal(maturity.sourceBindingText, sourceBindingCopy[sourceStatus]);
  assert.equal(
    maturity.sourceBindingDetailText,
    "仅本地归档跨工件绑定 · 不证明外部真实性或盈利"
      + ` · 当前/归档观察 ${currentCount}/${anchoredCount}`
      + ` · 当前/归档结算 ${currentCount}/${anchoredCount}`,
  );
  assert.ok(!maturity.sourceBindingText.includes("FULL"));
  assert.ok(!maturity.sourceBindingDetailText.includes("hash"));
  assert.ok(!maturity.sourceBindingDetailText.includes("path"));
  assert.ok(!maturity.sourceBindingDetailText.includes("reason"));
}
const sourceContradictionMaturity = evidence.forwardStatisticalMaturityPresentation(
  currentForwardMaturityDashboardV6(
    "BLOCK",
    Object.fromEntries(Object.keys(currentForwardMaturityProgress).map((key) => [key, 0])),
    currentForwardSourceBinding("CONTRADICTION", { currentCount: 0, anchoredCount: 0 }),
  ),
);
assert.equal(sourceContradictionMaturity.valid, true);
assert.equal(sourceContradictionMaturity.rawStatus, "BLOCK");
assert.equal(sourceContradictionMaturity.sourceBindingRawStatus, "CONTRADICTION");
assert.equal(sourceContradictionMaturity.sourceBindingText, sourceBindingCopy.CONTRADICTION);
const v5SourceDowngrade = evidence.forwardStatisticalMaturityPresentation(
  currentForwardMaturityDashboard("NOT_DUE"),
);
assert.equal(v5SourceDowngrade.valid, true);
assert.equal(v5SourceDowngrade.sourceBindingRawStatus, "NOT_AVAILABLE");
assert.equal(v5SourceDowngrade.sourceBindingText, sourceBindingCopy.NOT_AVAILABLE);
for (const falseMatureStatus of ["REVIEW_REQUIRED", "STOP_RESEARCH"]) {
  const falseMature = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboard(falseMatureStatus, currentForwardMaturityProgress),
  );
  assert.equal(falseMature.valid, false);
  assert.equal(falseMature.rawStatus, "BLOCK");
}
const falseNotDue = evidence.forwardStatisticalMaturityPresentation(
  currentForwardMaturityDashboard("NOT_DUE", matureForwardMaturityProgress),
);
assert.equal(falseNotDue.valid, false);
assert.equal(falseNotDue.rawStatus, "BLOCK");
const emptyCollectingForwardProgress = {
  forward_outcomes: 0,
  required_forward_outcomes: 12,
  remaining_forward_outcomes: 12,
  settlements: 0,
  captured_observations: 0,
  executed_rebalances: 0,
  required_executed_rebalances: 6,
  remaining_executed_rebalances: 6,
};
const emptyCollectingForwardMaturity = evidence.forwardStatisticalMaturityPresentation(
  currentForwardMaturityDashboard("NOT_DUE", emptyCollectingForwardProgress),
);
assert.equal(emptyCollectingForwardMaturity.valid, true);
assert.equal(emptyCollectingForwardMaturity.rawStatus, "NOT_DUE");
const baselineOnlyForwardProgress = {
  ...emptyCollectingForwardProgress,
  settlements: 1,
  captured_observations: 1,
};
assert.equal(
  evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboard("NOT_DUE", baselineOnlyForwardProgress),
  ).valid,
  true,
);
for (const [status, impossibleProgress] of [
  [
    "REVIEW_REQUIRED",
    { ...matureForwardMaturityProgress, settlements: 0, captured_observations: 0 },
  ],
  [
    "NOT_DUE",
    {
      ...currentForwardMaturityProgress,
      executed_rebalances: 4,
      remaining_executed_rebalances: 2,
    },
  ],
  [
    "NOT_DUE",
    { ...currentForwardMaturityProgress, captured_observations: 5 },
  ],
]) {
  const causalFailure = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboard(status, impossibleProgress),
  );
  assert.equal(causalFailure.dashboardAuthoritySafe, true);
  assert.equal(causalFailure.valid, false);
  assert.equal(causalFailure.rawStatus, "BLOCK");
}
const zeroForwardMaturityProgress = Object.fromEntries(
  Object.keys(currentForwardMaturityProgress).map((key) => [key, 0]),
);
const blockedForwardMaturity = evidence.forwardStatisticalMaturityPresentation(
  currentForwardMaturityDashboard("BLOCK", zeroForwardMaturityProgress),
);
assert.equal(blockedForwardMaturity.valid, true);
assert.equal(blockedForwardMaturity.dashboardAuthoritySafe, true);
assert.equal(blockedForwardMaturity.rawStatus, "BLOCK");
assert.equal(blockedForwardMaturity.statusText, forwardMaturityCopy.BLOCK);
assert.equal(blockedForwardMaturity.progressText, "结果 0/0 · 调仓 0/0 · 结算 0 · 观察 0");
const legacyForwardMaturity = evidence.forwardStatisticalMaturityPresentation({
  schema_version: "portfolio-forward-dashboard-v4",
  candidate_hash: "a".repeat(64),
});
assert.equal(legacyForwardMaturity.valid, false);
assert.equal(legacyForwardMaturity.available, false);
assert.equal(legacyForwardMaturity.legacy, true);
assert.equal(legacyForwardMaturity.dashboardAuthoritySafe, true);
assert.equal(legacyForwardMaturity.rawStatus, "NOT_AVAILABLE");
assert.equal(
  legacyForwardMaturity.statusText,
  "旧版运行看板未携带统计成熟度 · 不作通过结论",
);
assert.equal(legacyForwardMaturity.progressText, "结果 --/-- · 调仓 --/-- · 结算 -- · 观察 --");

const invalidForwardMaturityDashboards = [
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    candidate_hash: "A".repeat(64),
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      candidate_hash: "b".repeat(64),
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      verification_scope: "SETTLEMENTS_REPLAYED",
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      verification_scope: "PERSISTED_FORWARD_READINESS_REBUILT_WITHOUT_SETTLEMENT_REPLAY",
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      verification_scope: "PERSISTED_READINESS_DETERMINISTIC_REBUILD_NO_SETTLEMENT_OR_STATISTICAL_REPLAY",
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      verification_scope: "PERSISTED_READINESS_DETERMINISTIC_REBUILD_NO_SETTLEMENT_OR_STATISTICAL_REPLAY_V2",
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      verification_scope: "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY_V2",
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      progress: { ...currentForwardMaturityProgress, forward_outcomes: "3" },
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      progress: { ...currentForwardMaturityProgress, settlements: true },
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      progress: { ...currentForwardMaturityProgress, remaining_forward_outcomes: 8 },
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      progress: { ...currentForwardMaturityProgress, required_executed_rebalances: 0 },
    },
  },
  {
    ...currentForwardMaturityDashboard("BLOCK", zeroForwardMaturityProgress),
    statistical_maturity: currentForwardMaturity("BLOCK", {
      ...zeroForwardMaturityProgress,
      captured_observations: 1,
    }),
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      paper_authorized: 0,
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: {
      ...currentForwardMaturity("NOT_DUE"),
      nested: { "ＣＡＮ－ＴＲＡＤＥ": true },
    },
  },
  {
    ...currentForwardMaturityDashboard("NOT_DUE"),
    nested_authority: [{ "实盘-授权": true }],
  },
];
invalidForwardMaturityDashboards.forEach((dashboard) => {
  const maturity = evidence.forwardStatisticalMaturityPresentation(dashboard);
  assert.equal(maturity.valid, false);
  assert.equal(maturity.available, false);
  assert.equal(maturity.rawStatus, "BLOCK");
  assert.equal(maturity.statusText, forwardMaturityCopy.BLOCK);
  assert.equal(maturity.progressText, "结果 0/0 · 调仓 0/0 · 结算 0 · 观察 0");
});
const oldScopeForwardMaturity = evidence.forwardStatisticalMaturityPresentation({
  ...currentForwardMaturityDashboard("NOT_DUE"),
  statistical_maturity: {
    ...currentForwardMaturity("NOT_DUE"),
    verification_scope: "PERSISTED_READINESS_DETERMINISTIC_REBUILD_NO_SETTLEMENT_OR_STATISTICAL_REPLAY",
  },
});
assert.equal(oldScopeForwardMaturity.dashboardAuthoritySafe, true);
assert.equal(oldScopeForwardMaturity.rawStatus, "BLOCK");
const futureScopeForwardMaturity = evidence.forwardStatisticalMaturityPresentation({
  ...currentForwardMaturityDashboard("NOT_DUE"),
  statistical_maturity: {
    ...currentForwardMaturity("NOT_DUE"),
    verification_scope: "PERSISTED_READINESS_AND_EMBEDDED_SERIES_STATISTICS_REBUILT_NO_SETTLEMENT_REPLAY_V2",
  },
});
assert.equal(futureScopeForwardMaturity.dashboardAuthoritySafe, true);
assert.equal(futureScopeForwardMaturity.rawStatus, "BLOCK");
const unsafeAuthorityForwardMaturity = evidence.forwardStatisticalMaturityPresentation({
  ...currentForwardMaturityDashboard("NOT_DUE"),
  nested_authority: [{ Paper_Authorized: true }, { "可-下单": true }],
});
assert.equal(unsafeAuthorityForwardMaturity.dashboardAuthoritySafe, false);
assert.equal(unsafeAuthorityForwardMaturity.rawStatus, "BLOCK");
const unsafeLegacyForwardMaturity = evidence.forwardStatisticalMaturityPresentation({
  schema_version: "portfolio-forward-dashboard-v4",
  candidate_hash: "a".repeat(64),
  nested_authority: { canTrade: true },
});
assert.equal(unsafeLegacyForwardMaturity.dashboardAuthoritySafe, false);
assert.equal(unsafeLegacyForwardMaturity.rawStatus, "BLOCK");
for (const [field, unsafeValue] of [
  ["research_only", false],
  ["observation_only", false],
  ["simulation_only", false],
  ["profitability_proven", true],
  ["paper_authorized", true],
  ["live_order_allowed", true],
]) {
  const dashboard = currentForwardMaturityDashboard("NOT_DUE");
  dashboard.statistical_maturity[field] = unsafeValue;
  const maturity = evidence.forwardStatisticalMaturityPresentation(dashboard);
  assert.equal(maturity.valid, false);
  assert.equal(maturity.rawStatus, "BLOCK");
}
const unsafeSourceBindingMutations = [
  (binding) => { delete binding.trust_scope; },
  (binding) => { binding.extra = false; },
  (binding) => { binding.current_observation_count = true; },
  (binding) => { binding.current_observation_count = 1.5; },
  (binding) => { binding.current_observation_count = -1; },
  (binding) => { binding.current_observation_count = Number.MAX_SAFE_INTEGER + 1; },
  (binding) => { binding.trust_scope = "EXTERNAL_ARCHIVE_AUTHENTICITY"; },
  (binding) => { binding.external_authenticity_proven = true; },
  (binding) => { binding.profitability_proven = true; },
  (binding) => { binding.research_only = false; },
  (binding) => { binding.paper_authorized = "false"; },
  (binding) => { binding.nested_authority = { LiveOrderAllowed: true }; },
];
unsafeSourceBindingMutations.forEach((mutate) => {
  const dashboard = currentForwardMaturityDashboardV6("NOT_DUE");
  mutate(dashboard.statistical_maturity.source_binding);
  const maturity = evidence.forwardStatisticalMaturityPresentation(dashboard);
  assert.equal(maturity.valid, false);
  assert.equal(maturity.available, false);
  assert.equal(maturity.sourceBindingRawStatus, "CONTRADICTION");
  assert.equal(maturity.sourceBindingText, sourceBindingCopy.CONTRADICTION);
});
for (const sourceBinding of [
  currentForwardSourceBinding("FULL", { currentCount: 1025, anchoredCount: 1025 }),
  currentForwardSourceBinding("PREFIX", { currentCount: 1025, anchoredCount: 1024 }),
  currentForwardSourceBinding("FULL", {
    currentCount: Number.MAX_SAFE_INTEGER,
    anchoredCount: Number.MAX_SAFE_INTEGER,
  }),
]) {
  const maturity = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboardV6("NOT_DUE", currentForwardMaturityProgress, sourceBinding),
  );
  assert.equal(maturity.valid, false);
  assert.equal(maturity.available, false);
  assert.equal(maturity.sourceBindingRawStatus, "CONTRADICTION");
}
for (const sourceBinding of [
  currentForwardSourceBinding("FULL", { currentCount: 4, anchoredCount: 3 }),
  currentForwardSourceBinding("PREFIX", { currentCount: 4, anchoredCount: 4 }),
]) {
  const maturity = evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboardV6("NOT_DUE", currentForwardMaturityProgress, sourceBinding),
  );
  assert.equal(maturity.valid, false);
  assert.equal(maturity.sourceBindingRawStatus, "CONTRADICTION");
}
assert.equal(
  evidence.forwardStatisticalMaturityPresentation(
    currentForwardMaturityDashboardV6(
      "NOT_DUE",
      currentForwardMaturityProgress,
      currentForwardSourceBinding("CONTRADICTION", { currentCount: 4, anchoredCount: 4 }),
    ),
  ).valid,
  false,
);
assert.equal(
  evidence.forwardStatisticalMaturityPresentation({
    ...currentForwardMaturityDashboardV6("NOT_DUE"),
    statistical_maturity: currentForwardMaturity("NOT_DUE"),
  }).valid,
  false,
);
assert.equal(
  evidence.forwardStatisticalMaturityPresentation({
    ...currentForwardMaturityDashboard("NOT_DUE"),
    statistical_maturity: currentForwardMaturityV2("NOT_DUE"),
  }).valid,
  false,
);
for (const malformedMaturity of [
  { ...currentForwardMaturity("NOT_DUE"), status: "PASS" },
  { ...currentForwardMaturity("NOT_DUE"), extra: false },
  {
    ...currentForwardMaturity("NOT_DUE"),
    progress: { ...currentForwardMaturityProgress, extra: 0 },
  },
]) {
  const maturity = evidence.forwardStatisticalMaturityPresentation({
    schema_version: "portfolio-forward-dashboard-v5",
    candidate_hash: "a".repeat(64),
    statistical_maturity: malformedMaturity,
  });
  assert.equal(maturity.valid, false);
  assert.equal(maturity.rawStatus, "BLOCK");
}

const currentForwardIdentity = {
  schema_version: "portfolio-forward-dashboard-v4",
  candidate_hash: "a".repeat(64),
  permissions: {
    read_only: true,
    observation_only: true,
    simulation_only: true,
    paper_authorized: false,
    live_order_allowed: false,
    live_trading_hard_block: true,
  },
};
const currentForwardV5Identity = {
  ...currentForwardIdentity,
  schema_version: "portfolio-forward-dashboard-v5",
  statistical_maturity: currentForwardMaturity("NOT_DUE"),
};
const currentForwardV6Identity = {
  ...currentForwardIdentity,
  schema_version: "portfolio-forward-dashboard-v6",
  statistical_maturity: currentForwardMaturityV2("NOT_DUE"),
};
const schema11AttributionStrategySnapshot = JSON.parse(JSON.stringify(schema11PassPayload));
const sameCandidateAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: currentForwardIdentity,
  strategySnapshot: schema11AttributionStrategySnapshot,
  currentStrategyId: "dual_ma",
});
assert.equal(sameCandidateAttribution.relationStatus, "SAME");
assert.equal(sameCandidateAttribution.frozenCandidateText, "冻结组合 aaaaaaaaaaaa…");
assert.equal(sameCandidateAttribution.forwardCandidateText, "当前自然前向 aaaaaaaaaaaa…");
assert.equal(sameCandidateAttribution.relationText, "同一组合候选 · 仅确认归属，不代表盈利");
assert.ok(sameCandidateAttribution.strategyAttributionText.includes("当前策略 dual_ma"));
assert.ok(sameCandidateAttribution.strategyAttributionText.includes("事前假设 frozen-causal-persistence-v1"));
assert.ok(sameCandidateAttribution.strategyAttributionText.endsWith("与组合候选未建立白名单绑定"));
assert.equal(sameCandidateAttribution.rawFrozenCandidateHash, "a".repeat(64));
assert.equal(sameCandidateAttribution.rawForwardCandidateHash, "a".repeat(64));
assert.equal(sameCandidateAttribution.rawHypothesisHash, "5".repeat(64));
const sameCandidateV5Attribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: currentForwardV5Identity,
});
assert.equal(sameCandidateV5Attribution.relationStatus, "SAME");
assert.equal(sameCandidateV5Attribution.rawForwardCandidateHash, "a".repeat(64));
const sameCandidateV6Attribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: currentForwardV6Identity,
});
assert.equal(sameCandidateV6Attribution.relationStatus, "SAME");
assert.equal(sameCandidateV6Attribution.rawForwardCandidateHash, "a".repeat(64));
const visibleAttributionText = [
  sameCandidateAttribution.frozenCandidateText,
  sameCandidateAttribution.forwardCandidateText,
  sameCandidateAttribution.relationText,
  sameCandidateAttribution.strategyAttributionText,
].join(" ");
assert.ok(!visibleAttributionText.includes("a".repeat(64)));
assert.ok(!visibleAttributionText.includes("5".repeat(64)));
assert.ok(!visibleAttributionText.includes("PASS"));
assert.ok(!visibleAttributionText.includes("READY"));

const mismatchedCandidateAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: { ...currentForwardIdentity, candidate_hash: "f".repeat(64) },
});
assert.equal(mismatchedCandidateAttribution.relationStatus, "MISMATCH");
assert.equal(mismatchedCandidateAttribution.relationText, "候选不同 · 禁止合并解读");
assert.equal(mismatchedCandidateAttribution.rawFrozenCandidateHash, "a".repeat(64));
assert.equal(mismatchedCandidateAttribution.rawForwardCandidateHash, "f".repeat(64));
assert.equal(mismatchedCandidateAttribution.rawHypothesisHash, null);

const malformedForwardAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: { ...currentForwardIdentity, candidate_hash: "A".repeat(64) },
});
assert.equal(malformedForwardAttribution.relationStatus, "UNKNOWN");
assert.equal(malformedForwardAttribution.rawForwardCandidateHash, null);
const unsafeForwardAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: {
    ...currentForwardIdentity,
    permissions: { ...currentForwardIdentity.permissions, paper_authorized: true },
  },
});
assert.equal(unsafeForwardAttribution.relationStatus, "UNKNOWN");
assert.equal(unsafeForwardAttribution.rawForwardCandidateHash, null);
const newlyNamedUnsafeForwardAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: {
    ...currentForwardIdentity,
    nested_authority: { can_execute: true, mission_authorized: true },
  },
});
assert.equal(newlyNamedUnsafeForwardAttribution.relationStatus, "UNKNOWN");
assert.equal(newlyNamedUnsafeForwardAttribution.rawForwardCandidateHash, null);
for (const nestedAuthority of [
  { parameterSelectionAuthority: true },
  { "ＣＡＮ－ＴＲＡＤＥ": true },
  { "可-下单": true },
  { 已授权: "false" },
  { 实盘授权: 0 },
]) {
  const canonicalAliasUnsafeForwardAttribution = evidence.evidenceAttributionPresentation({
    frozenSnapshot: verifiedFrozenQualityPayload,
    forwardDashboard: {
      ...currentForwardV5Identity,
      nested_authority: [nestedAuthority],
    },
  });
  assert.equal(canonicalAliasUnsafeForwardAttribution.relationStatus, "UNKNOWN");
  assert.equal(canonicalAliasUnsafeForwardAttribution.rawForwardCandidateHash, null);
}
const canonicalAliasSafeForwardAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: {
    ...currentForwardV5Identity,
    nested_authority: [
      { parameterSelectionAuthority: false },
      { "ＣＡＮ－ＴＲＡＤＥ": false },
      { "可-下单": false, 已授权: false, 实盘授权: false },
    ],
  },
});
assert.equal(canonicalAliasSafeForwardAttribution.relationStatus, "SAME");
assert.equal(canonicalAliasSafeForwardAttribution.rawForwardCandidateHash, "a".repeat(64));
const v4WithMaturityFieldAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: {
    ...currentForwardIdentity,
    statistical_maturity: currentForwardMaturity("NOT_DUE"),
  },
});
assert.equal(v4WithMaturityFieldAttribution.relationStatus, "UNKNOWN");
assert.equal(v4WithMaturityFieldAttribution.rawForwardCandidateHash, null);
const malformedV5MaturityAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: {
    ...currentForwardV5Identity,
    statistical_maturity: {
      ...currentForwardV5Identity.statistical_maturity,
      progress: { ...currentForwardMaturityProgress, remaining_forward_outcomes: 0 },
    },
  },
});
assert.equal(malformedV5MaturityAttribution.relationStatus, "UNKNOWN");
assert.equal(malformedV5MaturityAttribution.rawForwardCandidateHash, null);

const malformedFrozenAttribution = evidence.evidenceAttributionPresentation({
  frozenSnapshot: { ...verifiedFrozenQualityPayload, candidate_hash: "a".repeat(63) },
  forwardDashboard: currentForwardIdentity,
});
assert.equal(malformedFrozenAttribution.relationStatus, "UNKNOWN");
assert.equal(malformedFrozenAttribution.rawFrozenCandidateHash, null);
const forgedStrategyBinding = evidence.evidenceAttributionPresentation({
  frozenSnapshot: verifiedFrozenQualityPayload,
  forwardDashboard: currentForwardIdentity,
  strategySnapshot: {
    ...frozenStrategyLabPayload,
    portfolio_candidate_hash: "a".repeat(64),
  },
  currentStrategyId: "dual_ma",
});
assert.ok(forgedStrategyBinding.strategyAttributionText.includes("与组合候选未建立白名单绑定"));
assert.ok(!forgedStrategyBinding.strategyAttributionText.includes("与组合候选已建立白名单绑定"));
assert.equal(evidence.evidenceAttributionPresentation().relationStatus, "UNKNOWN");

const verifiedPipeline = evidence.pipelineSummaryPresentation("PASS", true);
assert.equal(verifiedPipeline.label, "研究证据链已核对 · 不授予模拟或实盘权限");
assert.ok(!verifiedPipeline.label.includes("PASS"));

const emptyPipeline = evidence.pipelineSummaryPresentation("NOT_STARTED", false);
assert.equal(emptyPipeline.label, "尚无已登记研究证据 · 不授予模拟或实盘权限");

const researchStage = evidence.pipelineStagePresentation("backtest", "READY");
assert.equal(researchStage.label, "研究证据已核对 · 非授权");
assert.ok(!researchStage.label.includes("READY"));

const unauthorizedPaper = evidence.pipelineStagePresentation("paper_authorization", "PASS", {
  paperAuthorized: false,
});
assert.equal(unauthorizedPaper.label, "模拟未授权");

const authorizedPaper = evidence.pipelineStagePresentation("paper_authorization", "PASS", {
  paperAuthorized: true,
});
assert.equal(authorizedPaper.label, "模拟权限证据已核对 · 非实盘");

const unauthorizedPaperRun = evidence.pipelineStagePresentation("paper_run", "PASS", {
  paperAuthorized: false,
});
assert.equal(unauthorizedPaperRun.label, "模拟未授权 · 未运行");

const liveStage = evidence.pipelineStagePresentation("live_trading", "PASS", {
  liveHardLocked: true,
});
assert.equal(liveStage.label, "实盘永久硬锁");
assert.ok(!liveStage.label.includes("PASS"));

assert.equal(globalThis.HakimiEvidencePresentation, evidence);

const evidencePresentationSource = fs.readFileSync(
  path.join(__dirname, "evidence_presentation.js"),
  "utf8",
);
const singleLookContractStart = evidencePresentationSource.indexOf(
  "const INTERNAL_BACKTEST_SNAPSHOT_V4_KEYS",
);
const singleLookContractEnd = evidencePresentationSource.indexOf(
  "function evidenceAttributionPresentation",
  singleLookContractStart,
);
assert.ok(singleLookContractStart >= 0 && singleLookContractEnd > singleLookContractStart);
const singleLookContractSource = evidencePresentationSource.slice(
  singleLookContractStart,
  singleLookContractEnd,
);
assert.ok(singleLookContractSource.includes("portfolio-backtest-return-quality-snapshot-v4"));
assert.ok(singleLookContractSource.includes("portfolio-forward-dashboard-v7"));
assert.ok(singleLookContractSource.includes("FIRST_JOINT_MATURITY_SINGLE_LOOK"));
assert.ok(!singleLookContractSource.includes("fetch("));
assert.ok(!singleLookContractSource.includes("aria-live"));
assert.ok(!singleLookContractSource.includes("classList"));

const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const forwardMaturityFallbackStart = appSource.indexOf(
  "function evidenceForwardStatisticalMaturityPresentation(",
);
const forwardMaturityFallbackEnd = appSource.indexOf(
  "function evidenceMarketTruthGapPresentation(",
  forwardMaturityFallbackStart,
);
assert.ok(
  forwardMaturityFallbackStart >= 0
    && forwardMaturityFallbackEnd > forwardMaturityFallbackStart,
);
const forwardMaturityFallbackSource = appSource.slice(
  forwardMaturityFallbackStart,
  forwardMaturityFallbackEnd,
);
assert.ok(forwardMaturityFallbackSource.includes("dashboardAuthoritySafe: false"));
const desktopStatusStart = appSource.indexOf("function renderDesktopStatus()");
const desktopStatusEnd = appSource.indexOf("function futuOpenDOnline", desktopStatusStart);
assert.ok(desktopStatusStart >= 0 && desktopStatusEnd > desktopStatusStart, "desktop status renderer should exist");
const desktopStatusSource = appSource.slice(desktopStatusStart, desktopStatusEnd);
assert.ok(desktopStatusSource.includes('setLamp("paperStatusLamp", "flat")'));
assert.ok(desktopStatusSource.includes('"模拟未授权"'));
assert.ok(desktopStatusSource.includes('paperStatusText.dataset.rawArmed = String(armed)'));
assert.ok(desktopStatusSource.includes('不代表模拟授权'));
assert.ok(!desktopStatusSource.includes('armed ? "up" : "flat"'));
assert.ok(!desktopStatusSource.includes(' : "模拟运行"'));
assert.ok(appSource.includes('const stateText = "研究观察";'));
assert.ok(appSource.includes('target.dataset.rawPaperArmed = String(Boolean(paper.armed))'));
assert.ok(appSource.includes('模拟条件待权限核验'));
assert.ok(!appSource.includes('策略模拟可执行'));
assert.ok(!appSource.includes('手动模拟入口可用'));
const reviewStart = appSource.indexOf("async function reviewPlatformEvidence()");
const reviewEnd = appSource.indexOf("async function apiPostStream", reviewStart);
assert.ok(reviewStart >= 0 && reviewEnd > reviewStart, "evidence review workflow should exist");
const reviewSource = appSource.slice(reviewStart, reviewEnd);
assert.ok(reviewSource.includes("loadPlatformControlCenter()"));
assert.ok(!reviewSource.includes("loadBacktest("));
assert.ok(!reviewSource.includes("loadStrategyDoctor("));
assert.ok(!appSource.includes("runPlatformValidation"));
assert.ok(!appSource.includes('data.direction === "SHORT" ? "Short" : "Long"'));
assert.ok(!appSource.includes('paper.direction_mode === "SHORT_ONLY" ? "Short only" : "Long only"'));
assert.ok(appSource.includes(': "模拟未授权"'));
assert.ok(appSource.includes("evidencePipelineStagePresentation(key, row.status"));
assert.ok(!appSource.includes('class="platform-stage ${platformTone(row.status)}"'));
assert.ok(appSource.includes('role="listitem"'));
assert.ok(appSource.includes('data-raw-status="${escapeHtml(presentation.rawStatus)}"'));
const platformCenterStart = appSource.indexOf("function renderPlatformControlCenter(");
const platformReplayStart = appSource.indexOf("function renderPlatformReplay(", platformCenterStart);
assert.ok(platformCenterStart >= 0 && platformReplayStart > platformCenterStart, "platform control renderer should exist");
const platformCenterSource = appSource.slice(platformCenterStart, platformReplayStart);
assert.ok(platformCenterSource.includes('label: "模拟未授权"'));
assert.ok(platformCenterSource.includes("claimedPaperAuthorized"));
assert.ok(!platformCenterSource.includes("模拟已授权 · 未运行"));
assert.ok(!platformCenterSource.includes("模拟运行中 · 非实盘"));
assert.ok(platformCenterSource.includes("researchStatusShort"));
const marketTruthViewStart = appSource.indexOf("function platformMarketTruthView(");
const marketTruthViewEnd = appSource.indexOf("function renderPlatformMarketTruth(", marketTruthViewStart);
assert.ok(marketTruthViewStart >= 0 && marketTruthViewEnd > marketTruthViewStart, "market truth view should exist");
const marketTruthViewSource = appSource.slice(marketTruthViewStart, marketTruthViewEnd);
assert.ok(marketTruthViewSource.includes("truth.research_projection"));
assert.ok(marketTruthViewSource.includes("permissionKeys.every"));
assert.ok(marketTruthViewSource.includes('legacy.status === "BLOCK"'));
assert.ok(marketTruthViewSource.includes("evidenceGapText: gapLabel"));
assert.ok(!marketTruthViewSource.includes("evidenceMarketTruthGapPresentation"));
assert.ok(!marketTruthViewSource.includes("truth.next_action"));
assert.ok(!marketTruthViewSource.includes("nextAction:"));
const marketTruthRenderEnd = appSource.indexOf("function platformForwardObservationView(", marketTruthViewEnd);
const marketTruthRenderSource = appSource.slice(marketTruthViewEnd, marketTruthRenderEnd);
assert.ok(marketTruthRenderSource.includes('$("platformTruthEvidenceGap").textContent = view.evidenceGapText'));
assert.ok(marketTruthRenderSource.includes("行情研究成熟度"));
assert.ok(!marketTruthRenderSource.includes("原始行情证据状态"));
assert.ok(!marketTruthRenderSource.includes("platformTruthNextAction"));
const forwardViewStart = appSource.indexOf("function platformForwardObservationView(");
const forwardViewEnd = appSource.indexOf("function renderPlatformForwardObservation(", forwardViewStart);
assert.ok(forwardViewStart >= 0 && forwardViewEnd > forwardViewStart, "forward observation view should exist");
  const forwardViewSource = appSource.slice(forwardViewStart, forwardViewEnd);
  assert.ok(forwardViewSource.includes("researchStatusShort"));
  assert.ok(forwardViewSource.includes("evidenceForwardGapPresentation({ status })"));
  assert.ok(forwardViewSource.includes('raw.schema_version === "portfolio-forward-dashboard-v4"'));
  assert.ok(forwardViewSource.includes('raw.schema_version === "portfolio-forward-dashboard-v5"'));
  assert.ok(forwardViewSource.includes('raw.schema_version === "portfolio-forward-dashboard-v6"'));
  assert.ok(forwardViewSource.includes('raw.schema_version === "portfolio-forward-dashboard-v7"'));
  assert.ok(forwardViewSource.includes("evidenceForwardStatisticalMaturityPresentation(raw)"));
  assert.ok(forwardViewSource.includes("&& statisticalMaturity.dashboardAuthoritySafe === true"));
  assert.ok(forwardViewSource.includes("maturityRawStatus: statisticalMaturity.rawStatus"));
  assert.ok(forwardViewSource.includes("maturityText: statisticalMaturity.statusText"));
  assert.ok(forwardViewSource.includes("maturityProgressText: statisticalMaturity.progressText"));
  assert.ok(forwardViewSource.includes("sourceBindingRawStatus: statisticalMaturity.sourceBindingRawStatus"));
  assert.ok(forwardViewSource.includes("sourceBindingText: statisticalMaturity.sourceBindingText"));
  assert.ok(forwardViewSource.includes("sourceBindingDetailText: statisticalMaturity.sourceBindingDetailText"));
  const forwardOperationalStatusStart = forwardViewSource.indexOf("let status =");
  const forwardOperationalStatusEnd = forwardViewSource.indexOf("const evidenceGap =", forwardOperationalStatusStart);
  assert.ok(forwardOperationalStatusStart >= 0 && forwardOperationalStatusEnd > forwardOperationalStatusStart);
  assert.ok(!forwardViewSource.slice(
    forwardOperationalStatusStart,
    forwardOperationalStatusEnd,
  ).includes("statisticalMaturity"));
  const isolatedForwardObservationView = new Function(
    "evidenceForwardStatisticalMaturityPresentation",
    "evidenceForwardGapPresentation",
    "evidenceStatusPresentation",
    "timeText",
    "platformTruthTimeText",
    "researchStatusShort",
    `"use strict";
      const PLATFORM_FORWARD_STATUSES = new Set([
        "UP_TO_DATE", "WAITING", "DUE", "PAUSED", "BLOCK", "UNKNOWN",
      ]);
      ${forwardViewSource}
      return platformForwardObservationView;`,
  )(
    evidence.forwardStatisticalMaturityPresentation,
    ({ status }) => ({ text: `gap ${status}` }),
    (_kind, status) => ({ label: `operational ${status}`, permissionText: "read only" }),
    () => "time",
    () => "time",
    (status, fallback) => status || fallback,
  );
  const forwardViewPermissions = {
    read_only: true,
    observation_only: true,
    simulation_only: true,
    paper_authorized: false,
    live_order_allowed: false,
    live_trading_hard_block: true,
  };
  const realV7ForwardView = isolatedForwardObservationView({
    incremental_observation: realSingleLookContracts.dashboard_pass,
  });
  assert.equal(realV7ForwardView.status, "BLOCK");
  assert.equal(realV7ForwardView.maturityRawStatus, "REVIEW_REQUIRED");
  assert.ok(realV7ForwardView.maturityText.includes("首次到期决策已冻结"));
  assert.ok(realV7ForwardView.maturityProgressText.includes("后续累计仅描述"));
  const unsafeAuthorityForwardView = isolatedForwardObservationView({
    incremental_observation: {
      ...currentForwardMaturityDashboard("NOT_DUE"),
      status: "UP_TO_DATE",
      permissions: forwardViewPermissions,
      nested_authority: [{ canTrade: true }, { "可-下单": true }],
    },
  });
  assert.equal(unsafeAuthorityForwardView.status, "BLOCK");
  assert.equal(unsafeAuthorityForwardView.maturityRawStatus, "BLOCK");
  const sourceBoundForwardView = isolatedForwardObservationView({
    incremental_observation: {
      ...currentForwardMaturityDashboardV6(
        "NOT_DUE",
        currentForwardMaturityProgress,
        currentForwardSourceBinding("PREFIX", { currentCount: 4, anchoredCount: 3 }),
      ),
      status: "UP_TO_DATE",
      permissions: forwardViewPermissions,
    },
  });
  assert.equal(sourceBoundForwardView.status, "UP_TO_DATE");
  assert.equal(sourceBoundForwardView.maturityRawStatus, "NOT_DUE");
  assert.equal(sourceBoundForwardView.sourceBindingRawStatus, "PREFIX");
  assert.equal(sourceBoundForwardView.sourceBindingText, sourceBindingCopy.PREFIX);
  const malformedScopeForwardView = isolatedForwardObservationView({
    incremental_observation: {
      ...currentForwardMaturityDashboard("NOT_DUE"),
      status: "UP_TO_DATE",
      permissions: forwardViewPermissions,
      statistical_maturity: {
        ...currentForwardMaturity("NOT_DUE"),
        verification_scope: "PERSISTED_FORWARD_READINESS_REBUILT_WITHOUT_SETTLEMENT_REPLAY",
      },
    },
  });
  assert.equal(malformedScopeForwardView.status, "UP_TO_DATE");
  assert.equal(malformedScopeForwardView.maturityRawStatus, "BLOCK");
  assert.ok(forwardViewSource.includes("evidenceGapText: evidenceGap.text"));
  assert.ok(forwardViewSource.includes("latestObservationText,"));
  assert.ok(!forwardViewSource.includes("raw.next_action"));
  assert.ok(!forwardViewSource.includes("pause.reason"));
  assert.ok(!forwardViewSource.includes("· 下一步 ${nextAction}"));
  assert.ok(!forwardViewSource.includes("风险复核 ${previousRiskStatus}→${currentRiskStatus}"));
  assert.ok(!forwardViewSource.includes("调度 ${service.status ||"));
  const forwardRenderEnd = appSource.indexOf("function platformSmallCapitalPlanView(", forwardViewEnd);
  const forwardRenderSource = appSource.slice(forwardViewEnd, forwardRenderEnd);
  assert.ok(forwardRenderSource.includes('$("platformForwardEvidenceGap").textContent = view.evidenceGapText'));
  assert.ok(forwardRenderSource.includes('$("platformForwardObservationReceipt").textContent = view.latestObservationText'));
  assert.ok(forwardRenderSource.includes("root.dataset.forwardOperationalStatus = view.status"));
  assert.ok(forwardRenderSource.includes("root.dataset.forwardMaturityStatus = view.maturityRawStatus"));
  assert.ok(forwardRenderSource.includes("root.dataset.forwardSourceStatus = view.sourceBindingRawStatus"));
  assert.ok(forwardRenderSource.includes("evidenceLedger.dataset.operationalStatus = view.status"));
  assert.ok(forwardRenderSource.includes("evidenceLedger.dataset.maturityStatus = view.maturityRawStatus"));
  assert.ok(forwardRenderSource.includes("evidenceLedger.dataset.sourceBindingStatus = view.sourceBindingRawStatus"));
  assert.ok(forwardRenderSource.includes('$("platformForwardLocalSourceBinding")'));
  assert.ok(forwardRenderSource.includes('$("internalBacktestMaturitySourceBinding")'));
  assert.ok(forwardRenderSource.includes('$("platformForwardOperationalTruth").textContent = view.operationalTruthText'));
  assert.ok(forwardRenderSource.includes('$("platformForwardStatisticalMaturity").textContent = view.maturityText'));
  assert.ok(forwardRenderSource.includes('$("platformForwardStatisticalProgress").textContent = view.maturityProgressText'));
  assert.ok(!forwardRenderSource.includes("platformForwardPauseReason"));
  const smallPlanStart = appSource.indexOf("function platformSmallCapitalPlanView(");
const smallPlanEnd = appSource.indexOf("function renderPlatformSmallCapitalPlan(", smallPlanStart);
assert.ok(smallPlanStart >= 0 && smallPlanEnd > smallPlanStart, "small capital view should exist");
const smallPlanSource = appSource.slice(smallPlanStart, smallPlanEnd);
assert.ok(smallPlanSource.includes("researchStatusShort(instrumentRules.status"));
assert.ok(!smallPlanSource.includes("规则 ${instrumentRules.status ||"));
assert.ok(smallPlanSource.includes("evidenceSmallCapitalGapPresentation"));
assert.ok(smallPlanSource.includes("requiredChecks.find"));
assert.ok(!smallPlanSource.includes("raw?.next_action"));
assert.ok(!smallPlanSource.includes("nextAction:"));
const replayStart = appSource.indexOf("function renderPlatformReplay(");
const replayEnd = appSource.indexOf("async function replayLatestPlatformOrder(", replayStart);
assert.ok(replayStart >= 0 && replayEnd > replayStart, "platform replay renderer should exist");
const replaySource = appSource.slice(replayStart, replayEnd);
assert.ok(replaySource.includes("platform-replay-summary flat evidence-neutral"));
assert.ok(replaySource.includes("evidenceResearchCellPresentation"));
assert.ok(!replaySource.includes("platformTone(data.status)"));
const backtestMetricStart = appSource.indexOf("function renderBacktestMetrics(");
const backtestMetricEnd = appSource.indexOf("function backtestPercentText(", backtestMetricStart);
assert.ok(backtestMetricStart >= 0 && backtestMetricEnd > backtestMetricStart);
const backtestMetricSource = appSource.slice(backtestMetricStart, backtestMetricEnd);
assert.ok(backtestMetricSource.includes("evidenceBacktestPresentation(current, data)"));
assert.ok(!backtestMetricSource.includes("cssMove("));
assert.ok(!backtestMetricSource.includes("trade_count || 0"));
assert.ok(!appSource.includes("进入模拟候选"));
assert.ok(appSource.includes('$("btTemporal").textContent = evidence.temporalText'));
assert.ok(appSource.includes('$("btTemporal").dataset.rawStatus = evidence.rawTemporalStatus'));
assert.ok(appSource.includes("function renderBacktestRobustness("));
assert.ok(appSource.includes("evidenceBacktestRobustnessPresentation(data)"));
assert.ok(appSource.includes('$("btRobustnessCosts").textContent = evidence.costText'));
assert.ok(appSource.includes('target.dataset.rawCostStatus = evidence.rawCostStatus'));
assert.ok(!appSource.includes("cssMove(row.return_pct)"));
assert.ok(!appSource.includes("cssMove(row.total_return_pct)"));
assert.ok(appSource.includes("function evidenceResearchStatusBadge("));
assert.ok(appSource.includes("function evidenceResearchStatusClass("));
const leaderboardSliceStart = appSource.indexOf("async function loadLeaderboard()");
const leaderboardSliceEnd = appSource.indexOf("function renderStrategyLabEvidence", leaderboardSliceStart);
assert.ok(leaderboardSliceStart >= 0 && leaderboardSliceEnd > leaderboardSliceStart, "leaderboard renderer should exist");
const leaderboardSlice = appSource.slice(leaderboardSliceStart, leaderboardSliceEnd);
assert.ok(leaderboardSlice.includes("leader-row evidence-neutral"));
assert.ok(leaderboardSlice.includes("data-raw-score"));
assert.ok(!leaderboardSlice.includes("cssMove(row.score)"));
const backtestRowsSliceStart = appSource.indexOf('$("backtestRows").innerHTML');
const backtestRowsSliceEnd = appSource.indexOf("document.querySelectorAll(\".backtest-row\")", backtestRowsSliceStart);
assert.ok(backtestRowsSliceStart >= 0 && backtestRowsSliceEnd > backtestRowsSliceStart, "backtest rows renderer should exist");
const backtestRowsSlice = appSource.slice(backtestRowsSliceStart, backtestRowsSliceEnd);
assert.ok(backtestRowsSlice.includes("backtest-row evidence-neutral"));
assert.ok(backtestRowsSlice.includes("data-raw-score"));
assert.ok(!backtestRowsSlice.includes("cssMove(row.score)"));
assert.ok(appSource.includes("研究参数已复制到表单 · 未运行 · 未授权"));
const backtestQualityStart = appSource.indexOf("function renderBacktestQuality(");
const backtestQualityEnd = appSource.indexOf("async function loadBacktest(", backtestQualityStart);
assert.ok(backtestQualityStart >= 0 && backtestQualityEnd > backtestQualityStart);
const backtestQualitySource = appSource.slice(backtestQualityStart, backtestQualityEnd);
assert.ok(backtestQualitySource.includes("evidenceResearchStatusBadge(acceptance.status"));
assert.ok(backtestQualitySource.includes("evidenceResearchStatusBadge(row.status"));
assert.ok(backtestQualitySource.includes("evidenceResearchStatusBadge(manifest.status"));
const configRendererStart = appSource.indexOf("function configStatusClass(");
const configRendererEnd = appSource.indexOf("async function loadFullConfig(", configRendererStart);
assert.ok(configRendererStart >= 0 && configRendererEnd > configRendererStart, "configuration research renderer should exist");
const configRendererSource = appSource.slice(configRendererStart, configRendererEnd);
assert.ok(configRendererSource.includes('class="config-card flat"'));
assert.ok(configRendererSource.includes("data-raw-status"));
assert.ok(configRendererSource.includes("raw_status"));
assert.ok(configRendererSource.includes("配置已写入"));
assert.ok(configRendererSource.includes("实盘永久硬锁"));
assert.ok(!configRendererSource.includes('data.status || "READY"'));
assert.ok(!configRendererSource.includes("configStatusClass(data.status)"));
assert.ok(!configRendererSource.includes('"双AI就绪"'));
assert.ok(!configRendererSource.includes('"缓存+实时"'));
assert.ok(backtestQualitySource.includes("evidenceResearchStatusBadge(artifact.integrity_status"));
assert.ok(!backtestQualitySource.includes("renderStatusClass("));

const indexSource = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const marketDisclosureStart = indexSource.indexOf('id="marketRailDisclosure"');
const marketDisclosureEnd = indexSource.indexOf("</details>", marketDisclosureStart);
assert.ok(marketDisclosureStart >= 0 && marketDisclosureEnd > marketDisclosureStart);
const marketDisclosureSource = indexSource.slice(marketDisclosureStart, marketDisclosureEnd);
assert.ok(marketDisclosureSource.includes('class="market-rail-disclosure" open'));
assert.ok(marketDisclosureSource.includes(
  '<summary id="marketRailDisclosureSummary" aria-controls="marketRailDisclosureContent">',
));
assert.ok(marketDisclosureSource.includes('id="marketRailDisclosureCurrent">AAPL · 股票</strong>'));
assert.ok(marketDisclosureSource.includes('class="market-rail-disclosure-closed-copy">展开</span>'));
assert.ok(marketDisclosureSource.includes('class="market-rail-disclosure-open-copy">收起</span>'));
assert.ok(!marketDisclosureSource.includes("aria-live"));
assert.ok(marketDisclosureSource.indexOf('id="marketSearch"') < marketDisclosureSource.indexOf('id="marketCategoryTabs"'));
assert.ok(marketDisclosureSource.includes('id="marketCategoryTabs" role="group" aria-label="市场分类"'));
assert.ok(marketDisclosureSource.indexOf('id="marketCategoryTabs"') < marketDisclosureSource.indexOf('id="marketList"'));
assert.ok(indexSource.indexOf('id="workspaceRail"') < marketDisclosureStart);
const marketDisclosureAppStart = appSource.indexOf("function compactMarketRailMatches(");
const marketDisclosureAppEnd = appSource.indexOf("function stockSourceLabel(", marketDisclosureAppStart);
assert.ok(marketDisclosureAppStart >= 0 && marketDisclosureAppEnd > marketDisclosureAppStart);
const marketDisclosureAppSource = appSource.slice(marketDisclosureAppStart, marketDisclosureAppEnd);
assert.ok(marketDisclosureAppSource.includes('window.matchMedia?.("(max-width: 480px)")'));
assert.ok(marketDisclosureAppSource.includes('current.textContent = `${state.symbol} · ${marketTypeLabel(currentMarket(state.symbol))}`'));
assert.ok(marketDisclosureAppSource.includes("disclosure.open = !compact"));
assert.ok(marketDisclosureAppSource.includes("disclosure.open = false"));
assert.ok(marketDisclosureAppSource.includes("disclosure.contains(document.activeElement)"));
assert.ok(marketDisclosureAppSource.includes('disclosure.querySelector("summary")?.focus({ preventScroll: true })'));
assert.ok(!marketDisclosureAppSource.includes("fetch("));
assert.ok(!marketDisclosureAppSource.includes("api("));
const closeMarketDisclosureStart = appSource.indexOf("function closeCompactMarketRailDisclosure(");
const closeMarketDisclosureEnd = appSource.indexOf("function stockSourceLabel(", closeMarketDisclosureStart);
assert.ok(closeMarketDisclosureStart >= 0 && closeMarketDisclosureEnd > closeMarketDisclosureStart);
const isolatedCloseCompactMarketRailDisclosure = new Function(
  "$",
  "compactMarketRailMatches",
  "document",
  `"use strict";
    ${appSource.slice(closeMarketDisclosureStart, closeMarketDisclosureEnd)}
    return closeCompactMarketRailDisclosure;`,
);
const focusedMarketRow = {};
const outsideControl = {};
const focusOptions = [];
const disclosureSummary = {
  focus(options) {
    focusOptions.push(options);
  },
};
const disclosureFixture = {
  open: true,
  contains(node) {
    return node === focusedMarketRow;
  },
  querySelector(selector) {
    assert.equal(selector, "summary");
    return disclosureSummary;
  },
};
isolatedCloseCompactMarketRailDisclosure(
  () => disclosureFixture,
  () => true,
  { activeElement: focusedMarketRow },
)();
assert.equal(disclosureFixture.open, false);
assert.deepEqual(focusOptions, [{ preventScroll: true }]);
disclosureFixture.open = true;
isolatedCloseCompactMarketRailDisclosure(
  () => disclosureFixture,
  () => true,
  { activeElement: outsideControl },
)();
assert.equal(disclosureFixture.open, false);
assert.equal(focusOptions.length, 1, "programmatic selection outside the disclosure must not steal focus");
disclosureFixture.open = true;
isolatedCloseCompactMarketRailDisclosure(
  () => disclosureFixture,
  () => false,
  { activeElement: focusedMarketRow },
)();
assert.equal(disclosureFixture.open, true, "wide layouts must remain expanded");
assert.equal(focusOptions.length, 1);
const renderMarketsStart = appSource.indexOf("function renderMarkets(");
const renderMarketsEnd = appSource.indexOf("function scheduleMarketRender(", renderMarketsStart);
assert.ok(renderMarketsStart >= 0 && renderMarketsEnd > renderMarketsStart);
assert.ok(appSource.slice(renderMarketsStart, renderMarketsEnd).includes("renderMarketRailDisclosureSummary();"));
assert.ok(appSource.includes('addEventListener?.("change", syncMarketRailDisclosure)'));
assert.ok(indexSource.includes("多标的研究扫描"));
assert.ok(indexSource.includes("研究扫描列表"));
assert.ok(indexSource.includes("模型线索"));
const scannerRenderStart = appSource.indexOf("function renderMarketScanner(");
const scannerRenderEnd = appSource.indexOf("async function loadMarketScanner(", scannerRenderStart);
assert.ok(scannerRenderStart >= 0 && scannerRenderEnd > scannerRenderStart);
const scannerRenderSource = appSource.slice(scannerRenderStart, scannerRenderEnd);
assert.ok(scannerRenderSource.includes("研究观察，未套用策略"));
assert.ok(scannerRenderSource.includes('role="listitem"'));
assert.ok(scannerRenderSource.includes('class="flat"'));
assert.ok(!scannerRenderSource.includes("cssMove("));
assert.ok(!scannerRenderSource.includes("loadStrategyLab()"));
assert.ok(!appSource.includes("套用推荐策略"));
assert.ok(indexSource.includes("开发期策略比较"));
assert.ok(indexSource.includes("仅描述，不选参"));
assert.ok(indexSource.includes(">核对当前证据</button>"));
assert.ok(indexSource.includes("只核对已有证据，不触发回测或参数搜索"));
assert.ok(indexSource.includes("研究证据与权限阶段"));
assert.ok(!indexSource.includes("研究到模拟运行"));
assert.ok(indexSource.includes('role="list" aria-label="研究证据与权限阶段列表"'));

const planStart = indexSource.indexOf('id="platformSmallCapitalPlanCenter"');
const planEnd = indexSource.indexOf('<section class="platform-pipeline-band"', planStart);
assert.ok(planStart >= 0 && planEnd > planStart, "small-capital planning view should exist");
const planSource = indexSource.slice(planStart, planEnd);
assert.ok(planSource.includes('aria-labelledby="platformSmallCapitalPlanTitle"'));
assert.ok(planSource.includes('aria-describedby="platformSmallCapitalEvidenceGap platformSmallCapitalPlanPermissions"'));
assert.ok(!planSource.slice(0, planSource.indexOf(">") + 1).includes("aria-live"));
assert.ok(planSource.includes('id="platformSmallCapitalPlanStatus" role="status"'));
assert.ok(planSource.includes('id="platformSmallCapitalEvidenceGap"'));
assert.ok(!planSource.includes("platformSmallCapitalNextAction"));
const planGapStart = planSource.indexOf('id="platformSmallCapitalEvidenceGap"');
const planGapEnd = planSource.indexOf(">", planGapStart);
const planGapTag = planSource.slice(planGapStart, planGapEnd);
assert.ok(!planGapTag.includes('role="status"'));
assert.ok(!planGapTag.includes("aria-live"));
assert.equal((planSource.match(/aria-live=/g) || []).length, 1);
assert.ok(planSource.includes('<div class="platform-small-capital-quantity" role="listitem">'));
assert.ok(planSource.includes('<details id="platformSmallCapitalQuantityDetails">'));
assert.ok(planSource.indexOf("下一条尚缺证据 · 仅研究") < planSource.indexOf("规划封套 · 非账户余额"));
assert.ok(planSource.includes("模拟未授权 · 实盘永久硬锁"));
assert.ok(!planSource.includes("费用 NOT_CHECKED"));
assert.ok(!planSource.includes("<span>下一步</span>"));
assert.ok(appSource.includes('<div><span>研究观察</span><strong>${escapeHtml(nextState)}'));
const marketTruthStart = indexSource.indexOf('id="platformMarketTruthCenter"');
const marketTruthEnd = indexSource.indexOf('id="platformForwardObservationCenter"', marketTruthStart);
assert.ok(marketTruthStart >= 0 && marketTruthEnd > marketTruthStart);
const marketTruthSource = indexSource.slice(marketTruthStart, marketTruthEnd);
assert.ok(!marketTruthSource.slice(0, marketTruthSource.indexOf(">") + 1).includes("aria-live"));
assert.ok(marketTruthSource.includes('id="platformTruthStatus" role="status" aria-live="polite"'));
assert.ok(marketTruthSource.includes('aria-labelledby="platformMarketTruthTitle"'));
assert.ok(marketTruthSource.includes('aria-describedby="platformTruthEvidenceGap platformTruthPermissions"'));
assert.equal((marketTruthSource.match(/aria-live=/g) || []).length, 1);
assert.ok(marketTruthSource.includes('id="platformMarketTruthTitle" role="heading" aria-level="2"'));
assert.ok(marketTruthSource.includes('<div class="platform-truth-gap">'));
assert.ok(marketTruthSource.indexOf('id="platformTruthEvidenceGap"') < marketTruthSource.indexOf('id="platformTruthSymbol"'));
const marketGapTagStart = marketTruthSource.indexOf('id="platformTruthEvidenceGap"');
const marketGapTag = marketTruthSource.slice(
  marketGapTagStart,
  marketTruthSource.indexOf(">", marketGapTagStart),
);
assert.ok(!marketGapTag.includes('role="status"'));
assert.ok(!marketGapTag.includes("aria-live"));
assert.ok(!marketTruthSource.includes("platformTruthNextAction"));
assert.ok(!marketTruthSource.includes("<span>下一步</span>"));
const forwardCenterStart = indexSource.indexOf('id="platformForwardObservationCenter"');
const forwardCenterEnd = indexSource.indexOf('id="platformSmallCapitalPlanCenter"', forwardCenterStart);
assert.ok(forwardCenterStart >= 0 && forwardCenterEnd > forwardCenterStart);
  const forwardCenterSource = indexSource.slice(forwardCenterStart, forwardCenterEnd);
  assert.ok(!forwardCenterSource.slice(0, forwardCenterSource.indexOf(">") + 1).includes("aria-live"));
  assert.ok(forwardCenterSource.includes('aria-labelledby="platformForwardObservationTitle"'));
  assert.ok(forwardCenterSource.includes(
    'aria-describedby="platformForwardLocalSourceBinding platformForwardEvidenceGap platformForwardStatisticalMaturity platformForwardPermissions"',
  ));
  assert.ok(forwardCenterSource.includes('data-forward-operational-status="UNKNOWN"'));
  assert.ok(forwardCenterSource.includes('data-forward-maturity-status="BLOCK"'));
  assert.ok(forwardCenterSource.includes('data-forward-source-status="NOT_AVAILABLE"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardObservationStatus" role="status" aria-live="polite"'));
  assert.equal((forwardCenterSource.match(/aria-live=/g) || []).length, 1);
  assert.ok(forwardCenterSource.includes('id="platformForwardObservationTitle" role="heading" aria-level="2"'));
  assert.ok(forwardCenterSource.includes('<div class="platform-forward-gap" role="listitem">'));
  assert.ok(forwardCenterSource.includes('<div class="platform-forward-source" role="listitem">'));
  assert.ok(forwardCenterSource.includes('<div class="platform-forward-observation-detail" role="listitem">'));
  assert.ok(forwardCenterSource.includes('<details id="platformForwardObservationDetails">'));
  assert.ok(forwardCenterSource.includes('class="platform-forward-receipt-closed-copy"'));
  assert.ok(forwardCenterSource.includes('class="platform-forward-receipt-open-copy"'));
  assert.ok(forwardCenterSource.includes("最近已验证观察 · 展开只读收据"));
  assert.ok(forwardCenterSource.includes("最近已验证观察 · 收起只读收据"));
  assert.ok(forwardCenterSource.includes('id="platformForwardObservationReceipt"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardEvidenceLedger"'));
  assert.ok(forwardCenterSource.includes('aria-label="自然前向运行、统计成熟度与权限边界"'));
  assert.ok(forwardCenterSource.includes('<dt>运行状态</dt>'));
  assert.ok(forwardCenterSource.includes('<dt>首次联合到期决策</dt>'));
  assert.ok(forwardCenterSource.includes('<dt>研究与权限边界</dt>'));
  assert.ok(forwardCenterSource.includes('id="platformForwardLocalSourceBinding" data-raw-status="NOT_AVAILABLE"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardLocalSourceDetail"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardOperationalTruth"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardStatisticalMaturity"'));
  assert.ok(forwardCenterSource.includes('id="platformForwardStatisticalProgress"'));
  assert.ok(forwardCenterSource.includes("统计来源、首次到期决策或绑定不可核验 · 不使用判定"));
  assert.ok(forwardCenterSource.includes("首次到期决策未核验"));
  [
    "platformForwardEvidenceLedger",
    "platformForwardLocalSourceBinding",
    "platformForwardLocalSourceDetail",
    "platformForwardOperationalTruth",
    "platformForwardStatisticalMaturity",
    "platformForwardStatisticalProgress",
    "platformForwardPermissions",
  ].forEach((id) => {
    assert.equal((indexSource.match(new RegExp(`id="${id}"`, "g")) || []).length, 1);
  });
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardLocalSourceBinding"')
      < forwardCenterSource.indexOf('id="platformForwardEvidenceGap"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardEvidenceGap"')
      < forwardCenterSource.indexOf('id="platformForwardEvidenceLedger"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardStatisticalMaturity"')
      < forwardCenterSource.indexOf('id="platformForwardPermissions"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardPermissions"')
      < forwardCenterSource.indexOf('id="platformForwardOperationalTruth"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardOperationalTruth"')
      < forwardCenterSource.indexOf('id="platformForwardLatestBar"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardEvidenceLedger"')
      < forwardCenterSource.indexOf('id="platformForwardLatestBar"'),
  );
  assert.ok(
    forwardCenterSource.indexOf('id="platformForwardObservationReceipt"')
      > forwardCenterSource.indexOf('id="platformForwardNextCheck"'),
  );
  const forwardGapTagStart = forwardCenterSource.indexOf('id="platformForwardEvidenceGap"');
  const forwardGapTag = forwardCenterSource.slice(
    forwardGapTagStart,
    forwardCenterSource.indexOf(">", forwardGapTagStart),
  );
  assert.ok(!forwardGapTag.includes('role="status"'));
  assert.ok(!forwardGapTag.includes("aria-live"));
  const forwardReceiptTagStart = forwardCenterSource.indexOf('id="platformForwardObservationReceipt"');
  const forwardReceiptTag = forwardCenterSource.slice(
    forwardReceiptTagStart,
    forwardCenterSource.indexOf(">", forwardReceiptTagStart),
  );
  assert.ok(!forwardReceiptTag.includes('role="status"'));
  assert.ok(!forwardReceiptTag.includes("aria-live"));
  const forwardEvidenceLedgerStart = forwardCenterSource.indexOf('id="platformForwardEvidenceLedger"');
  const forwardEvidenceLedgerEnd = forwardCenterSource.indexOf("</dl>", forwardEvidenceLedgerStart);
  const forwardEvidenceLedgerSource = forwardCenterSource.slice(
    forwardEvidenceLedgerStart,
    forwardEvidenceLedgerEnd,
  );
  assert.ok(!forwardEvidenceLedgerSource.includes("role="));
  assert.ok(!forwardEvidenceLedgerSource.includes("aria-live"));
  assert.ok(!forwardEvidenceLedgerSource.includes("button"));
  assert.ok(!forwardEvidenceLedgerSource.includes("note"));
  assert.ok(!forwardCenterSource.includes("platformForwardPauseReason"));
assert.ok(appSource.includes("5%名义缓冲参考，非余额冻结或手续费"));
assert.ok(!appSource.includes("5%临时冻结规划参考"));
assert.ok(appSource.includes("只读规划阻断 · 模拟未授权 · 实盘永久硬锁"));
assert.ok(indexSource.includes("开发回测收益证据"));
assert.ok(indexSource.includes("开发回测 · 非盈利证明 · 模拟未授权 · 实盘永久硬锁"));
assert.ok(indexSource.includes("仅研究配置观察 · 模拟未授权 · 实盘永久硬锁"));
assert.ok(indexSource.includes("写入研究优先配置"));
assert.ok(indexSource.includes('id="btBenchmark">基准收益未提供'));
assert.ok(indexSource.includes('id="btCosts">费率未提供 · 滑点未提供'));
assert.ok(indexSource.includes('id="btSample">样本量未提供'));
assert.ok(indexSource.includes('id="btTemporal" data-raw-status="UNKNOWN"'));
assert.ok(indexSource.includes('id="backtestRobustnessLedger"'));
assert.ok(indexSource.includes('id="btRiskSurfaceDetails"'));
assert.ok(indexSource.includes("同一历史数据 · 仓位 / 止盈 / 止损 · 非策略信号参数"));
assert.ok(appSource.includes("btRiskSurfaceNeighborhood"));
assert.ok(indexSource.includes('id="btRobustnessMode"'));
assert.ok(indexSource.includes('id="btRobustnessCosts"'));
assert.ok(indexSource.includes('id="btRobustnessFailures"'));
assert.ok(indexSource.includes("开发期参数比较"));
assert.ok(indexSource.includes("开发期最高收益候选"));
assert.ok(indexSource.includes("选择偏差未校正"));
assert.ok(!indexSource.includes("高收益备选"));
assert.ok(!indexSource.includes("等待寻优"));
assert.ok(indexSource.includes('id="internalBacktestPackBoundary"'));
assert.ok(indexSource.includes('class="internal-backtest-pack-boundary"'));
assert.ok(indexSource.includes('aria-labelledby="internalBacktestQualityTitle"'));
assert.ok(indexSource.includes('id="internalBacktestQualityTitle" role="heading" aria-level="3"'));
assert.ok(indexSource.includes('id="internalBacktestAttributionSpine"'));
const platformCenterMarkup = indexSource.slice(
  indexSource.indexOf('id="platformControlCenter"'),
  indexSource.indexOf('id="internalBacktestAttributionSpine"'),
);
assert.ok(platformCenterMarkup.includes('id="platformEvidenceAttributionSpine"'));
assert.ok(platformCenterMarkup.includes('aria-describedby="platformCandidateAttributionRelation"'));
assert.ok(platformCenterMarkup.includes('aria-labelledby="platformEvidenceAttributionTitle"'));
assert.ok(platformCenterMarkup.includes('id="platformCandidateAttributionRelation" role="status"'));
assert.ok(platformCenterMarkup.includes('id="platformStrategyAttribution"'));
assert.ok(!platformCenterMarkup.includes('class="platform-evidence-attribution-spine up"'));
assert.ok(!platformCenterMarkup.includes('class="platform-evidence-attribution-spine down"'));
const platformAttributionStart = platformCenterMarkup.indexOf('id="platformEvidenceAttributionSpine"');
const platformAttributionEnd = platformCenterMarkup.indexOf("</section>", platformAttributionStart);
assert.ok(platformAttributionStart >= 0 && platformAttributionEnd > platformAttributionStart);
const platformAttributionMarkup = platformCenterMarkup.slice(platformAttributionStart, platformAttributionEnd);
const platformAttributionDetailsId = platformAttributionMarkup.indexOf('id="platformEvidenceAttributionDetails"');
const platformAttributionDetailsTagStart = platformAttributionMarkup.lastIndexOf(
  "<details",
  platformAttributionDetailsId,
);
const platformAttributionDetailsTagEnd = platformAttributionMarkup.indexOf(
  ">",
  platformAttributionDetailsId,
);
assert.ok(platformAttributionDetailsId >= 0);
assert.ok(platformAttributionDetailsTagStart >= 0 && platformAttributionDetailsTagEnd > platformAttributionDetailsTagStart);
const platformAttributionDetailsTag = platformAttributionMarkup.slice(
  platformAttributionDetailsTagStart,
  platformAttributionDetailsTagEnd + 1,
);
assert.ok(!/\sopen(?:\s|=|>)/.test(platformAttributionDetailsTag));
const platformAttributionDetailsEnd = platformAttributionMarkup.indexOf(
  "</details>",
  platformAttributionDetailsId,
);
assert.ok(platformAttributionDetailsEnd > platformAttributionDetailsId);
const platformAttributionDetailsMarkup = platformAttributionMarkup.slice(
  platformAttributionDetailsTagStart,
  platformAttributionDetailsEnd,
);
assert.ok(platformAttributionDetailsMarkup.includes("完整归属标识 · 展开核对"));
assert.ok(platformAttributionDetailsMarkup.includes('<dl aria-label="经证据合同核验的完整归属标识">'));
assert.ok(platformAttributionDetailsMarkup.includes('id="platformFrozenCandidateHash">未核验'));
assert.ok(platformAttributionDetailsMarkup.includes('id="platformForwardCandidateHash">未核验'));
assert.ok(platformAttributionDetailsMarkup.includes('id="platformHypothesisHash">未核验'));
assert.ok(!platformAttributionDetailsMarkup.includes("aria-live"));
assert.ok(!platformAttributionDetailsMarkup.includes('role="status"'));
assert.ok(!platformAttributionDetailsMarkup.includes("<button"));
assert.ok(
  platformAttributionMarkup.indexOf('id="platformStrategyAttribution"')
    < platformAttributionMarkup.indexOf('id="platformEvidenceAttributionDetails"'),
);
[
  "platformEvidenceAttributionDetails",
  "platformFrozenCandidateHash",
  "platformForwardCandidateHash",
  "platformHypothesisHash",
].forEach((id) => {
  assert.equal((indexSource.match(new RegExp(`id="${id}"`, "g")) || []).length, 1);
});
assert.ok(indexSource.includes('aria-label="冻结组合、自然前向与策略假设归属"'));
assert.ok(indexSource.includes('id="internalBacktestFrozenCandidate"'));
assert.ok(indexSource.includes('id="internalBacktestCurrentForwardCandidate"'));
assert.ok(indexSource.includes('id="internalBacktestCandidateRelation" role="status"'));
assert.ok(indexSource.includes('id="internalBacktestStrategyAttribution"'));
assert.ok(indexSource.includes("与组合候选未建立白名单绑定"));
[
  "internalBacktestPackBoundary",
  "internalBacktestEvidenceCue",
  "internalBacktestAttributionSpine",
  "internalBacktestFrozenCandidate",
  "internalBacktestCurrentForwardCandidate",
  "internalBacktestCandidateRelation",
  "internalBacktestStrategyAttribution",
  "internalBacktestMaturityCue",
  "internalBacktestMaturityText",
  "internalBacktestMaturitySourceBinding",
  "internalBacktestMaturitySourceBindingDetail",
].forEach((id) => {
  assert.equal((indexSource.match(new RegExp(`id="${id}"`, "g")) || []).length, 1);
});
const frozenSectionIdStart = indexSource.indexOf('id="internalBacktestPackBoundary"');
const frozenSectionStart = indexSource.lastIndexOf("<section", frozenSectionIdStart);
const frozenSectionEnd = indexSource.indexOf("</section>", frozenSectionIdStart);
const backtestActionsStart = indexSource.indexOf('<div class="backtest-actions">', frozenSectionIdStart);
const developmentBacktestHeadStart = indexSource.indexOf('<div class="backtest-evidence-head">', backtestActionsStart);
const developmentBacktestLedgerStart = indexSource.indexOf('id="backtestEvidenceLedger"', developmentBacktestHeadStart);
const evidenceCueStart = indexSource.indexOf('id="internalBacktestEvidenceCue"', frozenSectionStart);
const attributionSpineStart = indexSource.indexOf('id="internalBacktestAttributionSpine"', frozenSectionStart);
assert.ok(frozenSectionStart >= 0 && frozenSectionEnd > frozenSectionStart);
assert.ok(evidenceCueStart > frozenSectionStart && evidenceCueStart < attributionSpineStart);
const evidenceGateStart = indexSource.lastIndexOf("<dl", evidenceCueStart);
const evidenceGateEnd = indexSource.indexOf("</dl>", evidenceCueStart) + "</dl>".length;
const evidenceGateSource = indexSource.slice(evidenceGateStart, evidenceGateEnd);
assert.ok(evidenceGateStart > frozenSectionStart && evidenceGateEnd < attributionSpineStart);
assert.equal((evidenceGateSource.match(/<dt\b/g) || []).length, 4);
assert.equal((evidenceGateSource.match(/<dd\b/g) || []).length, 4);
assert.equal((evidenceGateSource.match(/role="status"/g) || []).length, 0);
assert.ok(evidenceGateSource.includes('aria-label="冻结收益证据解读闸门"'));
assert.ok(evidenceGateSource.includes('data-read-order="source-gap-maturity-permission-returns"'));
const gateVerdictStart = evidenceGateSource.indexOf('data-gate-step="01 SOURCE">证据判定</dt>');
const gateGapStart = evidenceGateSource.indexOf('data-gate-step="02 GAP">下一条可信证据</dt>');
const gateMaturityStart = evidenceGateSource.indexOf('data-gate-step="03 MATURITY">首次联合到期决策</dt>');
const gateBoundaryStart = evidenceGateSource.indexOf('data-gate-step="04 PERMISSION">研究与权限边界</dt>');
assert.ok(gateVerdictStart >= 0 && gateVerdictStart < gateGapStart);
assert.ok(gateGapStart < gateMaturityStart);
assert.ok(gateMaturityStart < gateBoundaryStart);
assert.ok(evidenceGateSource.includes(
  '<dd id="internalBacktestQualityStatus">来源与合同未核验 · 当前数字不可用</dd>',
));
assert.ok(evidenceGateSource.includes('id="internalBacktestQualityFailures"'));
assert.ok(evidenceGateSource.includes(
  'id="internalBacktestMaturityCue" class="internal-backtest-maturity-layer" data-raw-status="UNKNOWN"',
));
assert.ok(evidenceGateSource.includes('id="internalBacktestMaturityText"'));
assert.ok(evidenceGateSource.includes(
  'id="internalBacktestMaturitySourceBinding" data-raw-status="NOT_AVAILABLE"',
));
assert.ok(evidenceGateSource.includes('id="internalBacktestMaturitySourceBindingDetail"'));
assert.ok(evidenceGateSource.includes("本地归档覆盖：未取得本地归档覆盖 · 不作来源覆盖结论"));
assert.ok(evidenceGateSource.includes("仅本地归档跨工件绑定 · 不证明外部真实性或盈利"));
assert.ok(evidenceGateSource.includes("收益期 --/-- · 实际调仓 --/--"));
assert.ok(evidenceGateSource.includes('id="internalBacktestQualityBoundary"'));
assert.ok(evidenceGateSource.includes("模拟未授权 · 实盘永久硬锁"));
assert.ok(!evidenceGateSource.includes("aria-live"));
assert.ok(!evidenceGateSource.includes("READY"));
const maturityCueStart = indexSource.indexOf('id="internalBacktestMaturityCue"', evidenceGateStart);
const maturitySourceBindingStart = indexSource.indexOf(
  'id="internalBacktestMaturitySourceBinding"',
  evidenceGateStart,
);
const frozenReturnGridStart = indexSource.indexOf("internal-backtest-quality-grid", evidenceGateEnd);
assert.ok(maturityCueStart > evidenceGateStart && maturityCueStart < frozenReturnGridStart);
assert.ok(maturitySourceBindingStart > maturityCueStart && maturitySourceBindingStart < gateBoundaryStart + evidenceGateStart);
assert.ok(indexSource.includes('aria-label="证据解读闸门之后的冻结历史收益描述"'));
assert.ok(frozenSectionEnd < backtestActionsStart);
assert.ok(backtestActionsStart < developmentBacktestHeadStart);
assert.ok(developmentBacktestHeadStart < developmentBacktestLedgerStart);
assert.ok(!indexSource.slice(frozenSectionStart, frozenSectionEnd).includes('role="note"'));
assert.ok(!indexSource.slice(frozenSectionStart, frozenSectionEnd).includes("aria-live"));
const mobileStyleSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
const gateStyleStart = mobileStyleSource.indexOf(".internal-backtest-evidence-cue {");
const gateStyleEnd = mobileStyleSource.indexOf(
  ".internal-backtest-attribution-spine {",
  gateStyleStart,
);
assert.ok(gateStyleStart >= 0 && gateStyleEnd > gateStyleStart);
const gateStyleSource = mobileStyleSource.slice(gateStyleStart, gateStyleEnd);
assert.ok(gateStyleSource.includes("content: attr(data-gate-step)"));
assert.ok(gateStyleSource.includes("font-variant-numeric: tabular-nums"));
assert.ok(!gateStyleSource.includes("background:"));
assert.ok(!gateStyleSource.includes("[data-evidence-gap-kind"));
assert.ok(!gateStyleSource.includes("var(--up)"));
assert.ok(!gateStyleSource.includes("var(--down)"));
assert.ok(!gateStyleSource.includes("var(--danger)"));
const mobileStart = mobileStyleSource.lastIndexOf("@media (max-width: 480px)");
assert.ok(mobileStart >= 0, "narrow-screen information architecture should exist");
const compactStart = mobileStyleSource.lastIndexOf("@media (max-width: 720px)", mobileStart);
assert.ok(compactStart >= 0 && compactStart < mobileStart, "720px evidence layout should exist");
const compactSource = mobileStyleSource.slice(compactStart, mobileStart);
assert.ok(compactSource.includes(".internal-backtest-evidence-cue"));
assert.ok(compactSource.includes("grid-template-columns: minmax(0, 1fr)"));
assert.ok(compactSource.includes(".internal-backtest-evidence-cue dt:not(:first-child)"));
const mobileSource = mobileStyleSource.slice(mobileStart);
assert.ok(mobileSource.includes(".internal-backtest-evidence-cue"));
assert.ok(mobileSource.includes("body.view-research .app-shell"));
assert.ok(mobileSource.includes("grid-template-columns: minmax(0, 1fr)"));
assert.ok(mobileSource.includes("position: relative"));
assert.ok(mobileSource.includes("grid-template-columns: repeat(2, minmax(0, 1fr))"));
assert.ok(mobileSource.includes("body.view-research .terminal"));
assert.ok(mobileSource.includes("body.view-research .ticker-header"));
assert.ok(mobileSource.includes("body.view-research .chart-panel"));
assert.ok(mobileSource.includes("body.view-research .chart-footer"));
assert.ok(mobileStyleSource.includes(".market-rail-disclosure-content {"));
assert.ok(mobileSource.includes(".market-rail-disclosure > summary"));
assert.ok(mobileSource.includes("grid-template-columns: auto minmax(0, 1fr) auto"));
assert.ok(mobileSource.includes(".market-rail-disclosure > summary:focus-visible"));
assert.ok(mobileSource.includes(".market-rail-disclosure:not([open]) > .market-rail-disclosure-content"));
assert.ok(mobileSource.includes(".market-rail-disclosure[open] .market-rail-disclosure-open-copy"));
assert.ok(mobileStyleSource.includes(
  ".platform-forward-observation-detail details[open] .platform-forward-receipt-open-copy",
));
assert.ok(mobileStyleSource.includes(".platform-forward-observation-detail summary:focus-visible"));
assert.ok(indexSource.includes(
  'data-supported-schema-couplings="portfolio-internal-backtest-pack-v4=>backtest-return-quality-v2;portfolio-internal-backtest-pack-v5=>backtest-return-quality-v3;portfolio-internal-backtest-pack-v6=>backtest-return-quality-v3=>portfolio-backtest-forward-promotion-summary-v2"',
));
assert.ok(!indexSource.includes("data-expected-schema="));
assert.ok(indexSource.includes('data-snapshot-schema="portfolio-backtest-return-quality-snapshot-v3"'));
assert.ok(indexSource.includes('data-noncurrent-snapshot-schema="portfolio-backtest-return-quality-snapshot-v4"'));
assert.ok(indexSource.includes('data-connection-status="CHECKING"'));
assert.ok(indexSource.includes('<dd id="internalBacktestQualityStatus">'));
assert.ok(evidenceGateSource.includes('id="internalBacktestEvidenceCue"'));
assert.ok(evidenceGateSource.includes('class="internal-backtest-evidence-cue"'));
assert.ok(evidenceGateSource.includes('data-evidence-gap-kind="SOURCE"'));
assert.ok(indexSource.includes("首次联合到期决策</dt>"));
assert.ok(indexSource.includes('aria-describedby="internalBacktestQualityStatus internalBacktestQualityFailures internalBacktestMaturityCue internalBacktestQualityBoundary internalBacktestQualitySource"'));
assert.ok(indexSource.includes('id="internalBacktestQualityFailures"'));
assert.ok(indexSource.includes('id="internalBacktestQualitySource"'));
assert.ok(indexSource.includes('id="internalBacktestQualityStages"'));
assert.ok(indexSource.includes('id="internalBacktestQualityValidation"'));
assert.ok(indexSource.includes('id="internalBacktestQualityTest"'));
assert.ok(indexSource.includes('id="internalBacktestForwardEvidence"'));
assert.ok(indexSource.includes('id="internalBacktestForwardStatus"'));
assert.ok(indexSource.includes('id="internalBacktestForwardMaturity"'));
assert.ok(indexSource.includes('id="internalBacktestForwardBoundary"'));
assert.ok(indexSource.includes("展开首次到期决策、后续描述与人工复核边界"));
assert.ok(indexSource.includes("首次到期决策未核验 · 后续样本仅可描述"));
assert.ok(indexSource.includes("styles.css?v=20260822-evidence-calibration-rail-2"));
assert.ok(indexSource.includes("evidence_presentation.js?v=20260821-correlation-multiplicity-ledger-1"));
assert.ok(indexSource.includes("app.js?v=20260821-correlation-multiplicity-ledger-1"));
assert.equal((indexSource.match(/20260821-correlation-multiplicity-ledger-1/g) || []).length, 2);
assert.ok(!indexSource.includes("20260814-forward-local-source-binding-1"));
assert.ok(!indexSource.includes("20260814-schema14-search-lineage-1"));
assert.ok(!indexSource.includes("20260814-evidence-reading-gate-1"));
assert.ok(!indexSource.includes("20260814-forward-statistical-maturity-1"));
assert.ok(!indexSource.includes("20260814-return-evidence-triad-1"));
assert.ok(!indexSource.includes("20260814-return-evidence-cue-2"));
assert.ok(!indexSource.includes("20260814-return-evidence-cue-1"));
assert.ok(!indexSource.includes("20260814-pack-v5-quality-v3-1"));
assert.ok(!indexSource.includes("20260814-schema13-predicate-ledger-1"));
assert.ok(!indexSource.includes("20260814-schema13-mechanism-gate-1"));
assert.ok(!indexSource.includes("20260814-strategy-audit-path-1"));
assert.ok(indexSource.includes("独立只读证据 · 不覆盖交互开发回测"));
assert.ok(appSource.includes('fetch("/api/portfolio/backtest-return-quality"'));
assert.equal((appSource.match(/\/api\/portfolio\/backtest-return-quality/g) || []).length, 1);
assert.ok(appSource.includes("internalBacktestReturnQualityLoaded"));
assert.ok(appSource.includes("renderInternalBacktestReturnQuality"));
assert.ok(appSource.includes("internalBacktestReturnQualityPresentation"));
assert.ok(appSource.includes("boundary.dataset.packSchema = evidence.rawPackSchema"));
assert.ok(appSource.includes("boundary.dataset.qualitySchema = evidence.rawQualitySchema"));
assert.ok(appSource.includes("boundary.dataset.sourceMode = evidence.sourceMode"));
assert.ok(appSource.includes("evidenceCue.dataset.evidenceGapKind = evidence.evidenceGapKind"));
assert.ok(appSource.includes("evidenceGap.textContent = evidence.evidenceGapText || evidence.failureText"));
assert.ok(appSource.includes('$("internalBacktestMaturityText").textContent = evidence.maturityCueText'));
assert.ok(!appSource.includes('maturityCue.textContent = evidence.maturityCueText'));
assert.ok(appSource.includes('maturityCue.dataset.rawStatus = evidence.rawForwardMaturityStatus'));
const returnQualityRendererStart = appSource.indexOf("function renderInternalBacktestReturnQuality(");
const returnQualityRendererEnd = appSource.indexOf(
  "async function loadInternalBacktestReturnQuality()",
  returnQualityRendererStart,
);
assert.ok(
  returnQualityRendererStart >= 0 && returnQualityRendererEnd > returnQualityRendererStart,
);
const returnQualityRendererSource = appSource.slice(
  returnQualityRendererStart,
  returnQualityRendererEnd,
);
assert.ok(returnQualityRendererSource.includes("textContent"));
assert.ok(!returnQualityRendererSource.includes("innerHTML"));
assert.ok(!returnQualityRendererSource.includes("fetch("));
assert.ok(!returnQualityRendererSource.includes("apiMutation("));
assert.ok(!returnQualityRendererSource.includes("className"));
const returnQualityFallbackStart = appSource.indexOf(
  "function evidenceInternalBacktestReturnQualityPresentation(payload = {})",
);
const returnQualityFallbackEnd = appSource.indexOf(
  "function evidenceAttributionSpinePresentation(input = {})",
  returnQualityFallbackStart,
);
assert.ok(returnQualityFallbackStart >= 0 && returnQualityFallbackEnd > returnQualityFallbackStart);
const returnQualityFallbackSource = appSource.slice(
  returnQualityFallbackStart,
  returnQualityFallbackEnd,
);
[
  "forwardStatusText",
  "forwardMaturityText",
  "maturityCueText",
  "forwardBoundaryText",
  "forwardSourceText",
  "rawForwardStatus",
  "rawForwardIntegrityStatus",
  "rawForwardMaturityStatus",
  "rawForwardAuditStatus",
  "evidenceGapKind",
  "evidenceGapText",
  "evidenceGapCount",
  "rawPackSchema",
  "rawQualitySchema",
  "sourceMode",
].forEach((field) => assert.ok(returnQualityFallbackSource.includes(`${field}:`)));
assert.ok(appSource.includes("evidenceAttributionPresentation"));
assert.ok(appSource.includes("function renderEvidenceAttributionSpine()"));
const attributionRendererStart = appSource.indexOf("function renderEvidenceAttributionSpine()");
const attributionRendererEnd = appSource.indexOf("function renderInternalBacktestReturnQuality(", attributionRendererStart);
assert.ok(attributionRendererStart >= 0 && attributionRendererEnd > attributionRendererStart);
const attributionRendererSource = appSource.slice(attributionRendererStart, attributionRendererEnd);
assert.ok(attributionRendererSource.includes("dataset.relationStatus"));
assert.ok(
  attributionRendererSource.includes(
    "state.platformControl?.forward_validation?.incremental_observation || {}",
  ),
  "attribution spine must pass the verified forward dashboard, not its outer control-center wrapper",
);
assert.ok(!attributionRendererSource.includes("forwardDashboard: state.platformControl?.forward_validation || {}"));
assert.ok(attributionRendererSource.includes("rawFrozenCandidateHash"));
assert.ok(attributionRendererSource.includes("rawForwardCandidateHash"));
assert.ok(attributionRendererSource.includes("rawHypothesisHash"));
assert.ok(attributionRendererSource.includes("verifiedHashText"));
assert.ok(attributionRendererSource.includes('/^[a-f0-9]{64}$/.test(value)'));
assert.ok(attributionRendererSource.includes('["platformFrozenCandidateHash", evidence.rawFrozenCandidateHash]'));
assert.ok(attributionRendererSource.includes('["platformForwardCandidateHash", evidence.rawForwardCandidateHash]'));
assert.ok(attributionRendererSource.includes('["platformHypothesisHash", evidence.rawHypothesisHash]'));
assert.ok(attributionRendererSource.includes("node.textContent = verifiedHashText(value)"));
assert.ok(attributionRendererSource.includes("internalBacktestCandidateRelation"));
assert.ok(attributionRendererSource.includes('spine: "platformEvidenceAttributionSpine"'));
assert.ok(attributionRendererSource.includes('relation: "platformCandidateAttributionRelation"'));
assert.ok(attributionRendererSource.includes("["));
assert.ok(attributionRendererSource.includes("].forEach((target) =>"));
assert.ok(!attributionRendererSource.includes("textContent = evidence.raw"));
assert.ok(!attributionRendererSource.includes("className"));
assert.ok(!attributionRendererSource.includes("innerHTML"));
assert.ok(!attributionRendererSource.includes("fetch("));
assert.ok(!attributionRendererSource.includes("setInterval("));
assert.ok(!attributionRendererSource.includes("loadBacktest("));
assert.ok(!attributionRendererSource.includes("navigator.clipboard"));
assert.ok((appSource.match(/renderEvidenceAttributionSpine\(\);/g) || []).length >= 4);
assert.ok(appSource.includes("internalBacktestQualityValidation"));
assert.ok(appSource.includes("internalBacktestQualityTest"));
assert.ok(appSource.includes("internalBacktestForwardStatus"));
assert.ok(appSource.includes("internalBacktestForwardMaturity"));
assert.ok(appSource.includes("rawForwardIntegrityStatus"));
assert.ok(appSource.includes("${prefix}Detail"));
assert.ok(appSource.includes("renderStage("));
assert.ok(indexSource.includes("策略实验室稳健性证据边界"));
assert.ok(indexSource.includes("冻结来源未核验"));
assert.ok(indexSource.includes("实现身份"));
assert.ok(indexSource.includes("时效边界"));
assert.ok(indexSource.includes("当前失效证据"));
assert.ok(indexSource.includes("研究假设"));
assert.ok(indexSource.includes("事前失效条件"));
assert.ok(indexSource.includes("事前研究门禁"));
assert.ok(indexSource.includes('data-band-code="source">源'));
assert.ok(indexSource.includes('data-band-code="robustness">稳'));
assert.ok(indexSource.includes('data-band-code="invalidation">止'));
assert.ok(indexSource.includes("研究覆盖未核验"));
const strategyEvidenceStaticStart = indexSource.indexOf('id="strategyLabEvidence"');
const strategyEvidenceStaticEnd = indexSource.indexOf('<div class="lab-head">', strategyEvidenceStaticStart);
assert.ok(strategyEvidenceStaticStart >= 0 && strategyEvidenceStaticEnd > strategyEvidenceStaticStart);
const strategyEvidenceStaticSource = indexSource.slice(
  strategyEvidenceStaticStart,
  strategyEvidenceStaticEnd,
);
assert.ok(strategyEvidenceStaticSource.includes('class="strategy-condition-ledger"'));
assert.ok(strategyEvidenceStaticSource.includes('id="strategyMechanismLedgerHeading"'));
assert.ok(strategyEvidenceStaticSource.includes('id="strategyFutureLedgerHeading"'));
assert.ok(strategyEvidenceStaticSource.includes('<dl class="strategy-condition-list">'));
assert.ok(strategyEvidenceStaticSource.includes("<dt><code>未核验</code></dt>"));
assert.ok(strategyEvidenceStaticSource.includes("<dd>"));
assert.ok(!strategyEvidenceStaticSource.includes("tabindex="));
assert.ok(!strategyEvidenceStaticSource.includes('role="status"'));
assert.ok(!strategyEvidenceStaticSource.includes("aria-live"));
assert.ok(!strategyEvidenceStaticSource.includes("<button"));
const conditionLedgerRendererStart = appSource.indexOf("function renderStrategyConditionLedger(");
const conditionLedgerRendererEnd = appSource.indexOf(
  "function renderStrategyLabEvidence(",
  conditionLedgerRendererStart,
);
assert.ok(conditionLedgerRendererStart >= 0 && conditionLedgerRendererEnd > conditionLedgerRendererStart);
const conditionLedgerRendererSource = appSource.slice(
  conditionLedgerRendererStart,
  conditionLedgerRendererEnd,
);
[
  'escapeHtml(row?.rawStatus || "UNKNOWN")',
  'escapeHtml(row?.conditionId || "--")',
  'escapeHtml(row?.[detailKey] || "--")',
  'escapeHtml(row?.[observationKey] || "--")',
  'escapeHtml(row?.outcomeText || "未核验")',
  'escapeHtml(row?.boundaryText || "边界未核验")',
  "escapeHtml(kind)",
  "escapeHtml(headingId)",
  "escapeHtml(headingText)",
].forEach((escapedField) => assert.ok(conditionLedgerRendererSource.includes(escapedField)));
assert.ok(conditionLedgerRendererSource.includes('<dl class="strategy-condition-list">'));
assert.ok(conditionLedgerRendererSource.includes("<dt><code>"));
assert.ok(conditionLedgerRendererSource.includes("<dd>"));
assert.ok(!conditionLedgerRendererSource.includes("tabindex"));
assert.ok(!conditionLedgerRendererSource.includes('role="status"'));
assert.ok(!conditionLedgerRendererSource.includes("aria-live"));
assert.ok(!conditionLedgerRendererSource.includes("<button"));
assert.ok(!conditionLedgerRendererSource.includes("fetch("));
assert.ok(!conditionLedgerRendererSource.includes("setInterval("));
const strategyEvidenceRendererStart = conditionLedgerRendererEnd;
const strategyEvidenceRendererEnd = appSource.indexOf(
  "async function loadStrategyResearchEvidence(",
  strategyEvidenceRendererStart,
);
const strategyEvidenceRendererSource = appSource.slice(
  strategyEvidenceRendererStart,
  strategyEvidenceRendererEnd,
);
assert.ok(strategyEvidenceRendererSource.includes("evidence.mechanismConditionRows"));
assert.ok(strategyEvidenceRendererSource.includes("evidence.futureConditionRows"));
assert.ok(!strategyEvidenceRendererSource.includes("tabindex="));
assert.ok(!strategyEvidenceRendererSource.includes('role="status"'));
assert.ok(!strategyEvidenceRendererSource.includes("aria-live"));
assert.ok(appSource.includes("/api/strategy/research-evidence?strategy="));
assert.ok(appSource.includes("async function loadStrategyResearchEvidence(strategy,"));
assert.ok(appSource.includes("state.strategyResearchEvidence = frozenEvidence"));
assert.ok(appSource.includes("strategyResearchEvidenceCache"));
assert.ok(appSource.includes("loadStrategyResearchEvidence(strategy, { force: refreshEvidence })"));
assert.ok(appSource.includes("loadStrategyLab({ refreshEvidence: true })"));
const labLoadStart = appSource.indexOf("async function loadStrategyLab(");
const labLoadEnd = appSource.indexOf("function warRoomQuery(", labLoadStart);
assert.ok(labLoadStart >= 0 && labLoadEnd > labLoadStart);
const labLoadSource = appSource.slice(labLoadStart, labLoadEnd);
assert.ok(labLoadSource.includes("Promise.all(["));
assert.ok(labLoadSource.includes("renderStrategyLabEvidence(frozenEvidence || {})"));
assert.ok(!labLoadSource.includes("api(`/api/strategy/research-evidence"));
const bootStart = appSource.indexOf("async function boot()");
const bootEnd = appSource.indexOf("\nboot();", bootStart);
assert.ok(bootStart >= 0 && bootEnd > bootStart);
assert.ok(appSource.slice(bootStart, bootEnd).includes("deferBootLoad(1300, loadInternalBacktestReturnQuality)"));
assert.ok(appSource.includes("platformTruthTimeText(evidence.generatedAt)"));
assert.ok(appSource.includes("evidenceResearchStatusPresentation"));
assert.ok(appSource.includes("实盘永久硬锁"));
assert.ok(appSource.includes("恢复证据已核对"));
assert.ok(appSource.includes("账本恢复证据已核对"));
assert.ok(appSource.includes("strategyCardPresentation.label"));
assert.ok(appSource.includes("风控证据待核验 · 不授予执行"));
assert.ok(!appSource.includes("策略模拟可执行\"}"));
assert.ok(!appSource.includes('futuTradeState").textContent = data.live_trading_hard_block ? "BLOCKED" : "READY"'));
const releasePipelineStart = appSource.indexOf("function renderReleasePipeline(");
const releasePipelineEnd = appSource.indexOf("async function loadStrategyDoctor(", releasePipelineStart);
assert.ok(releasePipelineStart >= 0 && releasePipelineEnd > releasePipelineStart);
const releasePipelineSource = appSource.slice(releasePipelineStart, releasePipelineEnd);
assert.ok(releasePipelineSource.includes("evidenceResearchStatusPresentation"));
assert.ok(releasePipelineSource.includes("evidencePipelineStagePresentation"));
assert.ok(!releasePipelineSource.includes('>${escapeHtml(row.status || "--")}</span>'));
assert.ok(releasePipelineSource.includes("data-raw-status"));
assert.ok(appSource.includes("Score · 研究诊断"));
assert.ok(appSource.includes("strategyDoctorLifecycle"));
assert.ok(appSource.includes("data.signal?.raw_action || data.signal?.action"));
assert.ok(appSource.includes("研究预检已核对 · 模拟仍未授权"));
assert.ok(appSource.includes('target.className = "bot-readiness-panel flat evidence-neutral"'));
assert.ok(appSource.includes('data-raw-status="${escapeHtml(item.status)}"'));
assert.ok(!appSource.includes("Ready for paper automation"));
assert.ok(!appSource.includes("Paper run allowed, warnings exist"));
assert.ok(!appSource.includes("Exact run is paper-authorized"));

const strategyRoomStart = appSource.indexOf("function renderWarRoomBrief(");
const strategyRoomEnd = appSource.indexOf("function renderStatusClass(", strategyRoomStart);
assert.ok(strategyRoomStart >= 0 && strategyRoomEnd > strategyRoomStart, "strategy research room should exist");
const strategyRoomSource = appSource.slice(strategyRoomStart, strategyRoomEnd);
assert.ok(strategyRoomSource.includes("evidenceResearchCellPresentation"));
assert.ok(strategyRoomSource.includes("evidenceResearchValue"));
assert.ok(strategyRoomSource.includes("evidenceStrategyActionPresentation"));
assert.ok(strategyRoomSource.includes("row.raw_action || row.action"));
assert.ok(appSource.includes('row.raw_action || row.action || "WAIT"'));
assert.ok(appSource.includes('class="strategy-compare-row evidence-neutral"'));
assert.ok(appSource.includes('role="button" tabindex="0" aria-label="开发期策略比较'));
assert.ok(appSource.includes('strategyCompareSummary").textContent = "开发期研究比较中"'));
assert.ok(appSource.includes('event.key === "Enter" || event.key === " "'));
assert.ok(strategyRoomSource.includes('class="flat"'));
assert.ok(strategyRoomSource.includes("data-raw-status"));
assert.ok(strategyRoomSource.includes("data-raw-action"));
assert.ok(!strategyRoomSource.includes("renderStatusClass(row.status)"));
assert.ok(!strategyRoomSource.includes("renderStatusClass(row.level)"));
assert.ok(!strategyRoomSource.includes('>${escapeHtml(row.action)}</span>'));
assert.ok(!strategyRoomSource.includes('class="${row.action ==='));
assert.ok(strategyRoomSource.includes("模型估计 ${number(row.probability_pct, 0)}% · 未校准"));
assert.ok(indexSource.includes("研究机器人观察台"));
assert.ok(indexSource.includes("研究角色调度"));
assert.ok(indexSource.includes("研究动作 / 说明"));
const botCenterStart = appSource.indexOf("async function loadBotCenter()");
const botCenterEnd = appSource.indexOf("function renderStrategyRobotProfiles", botCenterStart);
assert.ok(botCenterStart >= 0 && botCenterEnd > botCenterStart, "bot center research renderer should exist");
const botCenterSource = appSource.slice(botCenterStart, botCenterEnd);
assert.ok(botCenterSource.includes("data-raw-status"));
assert.ok(botCenterSource.includes('class="flat"'));
assert.ok(botCenterSource.includes("研究草案待核验"));
assert.ok(!botCenterSource.includes('renderStatusClass(row.status)'));
const schedulerStart = appSource.indexOf("async function loadBotScheduler()");
const schedulerEnd = appSource.indexOf("async function assignBotOwner", schedulerStart);
assert.ok(schedulerStart >= 0 && schedulerEnd > schedulerStart, "bot scheduler research renderer should exist");
const schedulerSource = appSource.slice(schedulerStart, schedulerEnd);
assert.ok(schedulerSource.includes("研究主观察"));
assert.ok(schedulerSource.includes('class="flat"'));
assert.ok(!schedulerSource.includes('row.role === "OWNER"'));
assert.ok(!schedulerSource.includes("readinessClass(row.score)"));
assert.ok(appSource.includes("mode=research"));
const signalStart = appSource.indexOf("function renderSignals(");
const signalEnd = appSource.indexOf("function drawEquityChart(", signalStart);
assert.ok(signalStart >= 0 && signalEnd > signalStart, "signal evidence renderer should exist");
const signalSource = appSource.slice(signalStart, signalEnd);
assert.ok(signalSource.includes("evidenceStrategyActionPresentation"));
assert.ok(signalSource.includes('class="signal-item evidence-neutral"'));
assert.ok(signalSource.includes("data-raw-action"));
assert.ok(!signalSource.includes("strategyActionTone(signal.action)"));
assert.ok(!signalSource.includes('>${escapeHtml(signal.action || "--")}</span>'));
assert.ok(appSource.includes("本地模拟状态已记录 · 模拟仍未授权"));
assert.ok(appSource.includes("模拟参数仅供规划"));
assert.ok(!appSource.includes("${strategyName} ${leverage}x running"));
assert.ok(indexSource.includes("研究参数（只读）"));
assert.ok(indexSource.includes("风控证据"));
assert.ok(indexSource.includes("研究规划 TP · 非订单"));
assert.ok(indexSource.includes("研究规划 SL · 非订单"));
assert.ok(appSource.includes('$("strategyState").textContent = paper.armed ? "本地模拟状态已记录 · 模拟未授权"'));
assert.ok(appSource.includes('$("riskState").className = "flat"'));
assert.ok(appSource.includes("marketResearchDirectionLabel"));
assert.ok(appSource.includes("marketPlanningValue"));
assert.ok(appSource.includes("偏多估计 · 未校准"));
assert.ok(appSource.includes("偏空估计 · 未校准"));
assert.ok(appSource.includes("支撑观察 · 非方向"));
assert.ok(appSource.includes('$("marketAiDeepSeekBadge").className = "flat"'));
assert.ok(appSource.includes('$("marketAiGptBadge").className = "flat"'));
assert.ok(appSource.includes("function renderDeepSeekAnalysis"));
assert.ok(appSource.includes("marketResearchDirectionLabel(result.direction"));
assert.ok(appSource.includes("planning_entry_hint"));
const deepSeekRenderStart = appSource.indexOf("function renderDeepSeekAnalysis(");
const deepSeekRenderEnd = appSource.indexOf("async function loadDeepSeekStatus(", deepSeekRenderStart);
assert.ok(deepSeekRenderStart >= 0 && deepSeekRenderEnd > deepSeekRenderStart, "DeepSeek research renderer should exist");
const deepSeekRenderSource = appSource.slice(deepSeekRenderStart, deepSeekRenderEnd);
assert.ok(deepSeekRenderSource.includes('className = "flat"'));
assert.ok(!deepSeekRenderSource.includes('result.direction === "LONG" ? "up"'));
assert.ok(!deepSeekRenderSource.includes('result.direction === "SHORT" ? "down"'));
assert.ok(appSource.includes('$("tradingAgentsState").textContent ='));
assert.ok(appSource.includes("decisionLabel"));
assert.ok(appSource.includes("planning_long_take_profit"));
const tradingAgentsRoomStart = appSource.indexOf("function renderTradingAgentsRoom(");
const tradingAgentsRoomEnd = appSource.indexOf("async function runTradingAgentsRoom(", tradingAgentsRoomStart);
assert.ok(tradingAgentsRoomStart >= 0 && tradingAgentsRoomEnd > tradingAgentsRoomStart, "TradingAgents research renderer should exist");
const tradingAgentsRoomSource = appSource.slice(tradingAgentsRoomStart, tradingAgentsRoomEnd);
assert.ok(tradingAgentsRoomSource.includes("marketResearchDirectionLabel"));
assert.ok(tradingAgentsRoomSource.includes('class="flat"'));
assert.ok(!tradingAgentsRoomSource.includes('class="up"'));
assert.ok(!tradingAgentsRoomSource.includes('class="down"'));

const anomalyResearchStart = appSource.indexOf("function anomalyDirectionLabel(");
const anomalyResearchEnd = appSource.indexOf("async function loadAnomalyRadar(", anomalyResearchStart);
assert.ok(anomalyResearchStart >= 0 && anomalyResearchEnd > anomalyResearchStart, "anomaly research renderer should exist");
const anomalyResearchSource = appSource.slice(anomalyResearchStart, anomalyResearchEnd);
assert.ok(anomalyResearchSource.includes("研究观察"));
assert.ok(anomalyResearchSource.includes("研究优先队列"));
assert.ok(anomalyResearchSource.includes('class="flat"'));
assert.ok(!anomalyResearchSource.includes("cssMove(change)"));
const trendCockpitStart = appSource.indexOf("function renderTrendCockpit(");
const trendCockpitEnd = appSource.indexOf("async function loadTrendCockpit(", trendCockpitStart);
assert.ok(trendCockpitStart >= 0 && trendCockpitEnd > trendCockpitStart, "trend cockpit renderer should exist");
const trendCockpitSource = appSource.slice(trendCockpitStart, trendCockpitEnd);
assert.ok(trendCockpitSource.includes("trend-cockpit-card flat"));
assert.ok(!trendCockpitSource.includes("trend-cockpit-card ${card.tone"));
assert.ok(appSource.includes("研究观察 / ${trend.safe_action"));

const styleSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
const conditionLedgerStyleStart = styleSource.indexOf(".strategy-condition-ledger {");
const conditionLedgerStyleEnd = styleSource.indexOf(
  ".strategy-evidence-band small",
  conditionLedgerStyleStart,
);
assert.ok(conditionLedgerStyleStart >= 0 && conditionLedgerStyleEnd > conditionLedgerStyleStart);
const conditionLedgerStyleSource = styleSource.slice(
  conditionLedgerStyleStart,
  conditionLedgerStyleEnd,
);
assert.ok(conditionLedgerStyleSource.includes(".strategy-condition-row"));
assert.ok(conditionLedgerStyleSource.includes("font-variant-numeric: tabular-nums"));
assert.ok(conditionLedgerStyleSource.includes("overflow-wrap: anywhere"));
assert.ok(!conditionLedgerStyleSource.includes("border-radius"));
assert.ok(!conditionLedgerStyleSource.includes("box-shadow"));
assert.ok(!conditionLedgerStyleSource.includes("animation"));
assert.ok(!conditionLedgerStyleSource.includes("[data-raw-status"));
assert.ok(styleSource.includes(
  "grid-template-columns: minmax(0, 1fr) minmax(0, 0.95fr) minmax(270px, 1.1fr);",
));
assert.ok(!styleSource.includes(".strategy-lab-evidence[data-connection-status"));
assert.ok(!styleSource.includes(".strategy-evidence-band:focus-visible"));
const conditionLedger720Start = styleSource.indexOf(
  "@media (max-width: 720px)",
  conditionLedgerStyleEnd,
);
const conditionLedger480Start = styleSource.indexOf(
  "@media (max-width: 480px)",
  conditionLedger720Start,
);
assert.ok(conditionLedger720Start >= 0 && conditionLedger480Start > conditionLedger720Start);
const conditionLedger720Source = styleSource.slice(conditionLedger720Start, conditionLedger480Start);
assert.ok(conditionLedger720Source.includes(".strategy-condition-row"));
assert.ok(conditionLedger720Source.includes(
  "grid-template-columns: minmax(150px, 0.68fr) minmax(0, 1.32fr);",
));
const conditionLedger480End = styleSource.indexOf(".param-panel", conditionLedger480Start);
assert.ok(conditionLedger480End > conditionLedger480Start);
const conditionLedger480Source = styleSource.slice(conditionLedger480Start, conditionLedger480End);
assert.ok(conditionLedger480Source.includes(".strategy-condition-row"));
assert.ok(conditionLedger480Source.includes("grid-template-columns: minmax(0, 1fr);"));
const marketTruthStyleStart = styleSource.indexOf(".platform-data-truth-strip {");
const marketTruthStyleEnd = styleSource.indexOf("#platformTruthStatus", marketTruthStyleStart);
assert.ok(marketTruthStyleStart >= 0 && marketTruthStyleEnd > marketTruthStyleStart);
const marketTruthStyleSource = styleSource.slice(marketTruthStyleStart, marketTruthStyleEnd);
assert.ok(marketTruthStyleSource.includes("grid-template-columns: repeat(5, minmax(120px, 1fr));"));
assert.ok(marketTruthStyleSource.includes(".platform-truth-gap"));
assert.ok(marketTruthStyleSource.includes("grid-column: 1 / -1;"));
const forwardStyleStart = styleSource.indexOf(".platform-forward-observation-strip {");
const forwardStyleEnd = styleSource.indexOf(".platform-data-truth-strip {", forwardStyleStart);
assert.ok(forwardStyleStart >= 0 && forwardStyleEnd > forwardStyleStart);
const forwardStyleSource = styleSource.slice(forwardStyleStart, forwardStyleEnd);
assert.ok(forwardStyleSource.includes("grid-template-columns: repeat(6, minmax(108px, 1fr));"));
assert.ok(forwardStyleSource.includes(".platform-forward-source,"));
assert.ok(forwardStyleSource.includes(".platform-forward-gap,"));
assert.ok(forwardStyleSource.includes(".platform-forward-observation-detail"));
assert.ok(forwardStyleSource.includes("grid-column: 1 / -1;"));
assert.ok(forwardStyleSource.includes("#platformForwardObservationReceipt"));
assert.ok(forwardStyleSource.includes(".platform-forward-evidence-ledger"));
assert.ok(forwardStyleSource.includes("grid-template-columns: repeat(3, minmax(0, 1fr));"));
assert.ok(forwardStyleSource.includes("box-shadow: inset 2px 0 #667487;"));
assert.ok(forwardStyleSource.includes("border-block: 1px solid var(--line);"));
assert.ok(forwardStyleSource.includes(".platform-forward-evidence-ledger > div + div"));
assert.ok(!forwardStyleSource.includes("background:"));
assert.ok(!forwardStyleSource.includes("border-radius:"));
assert.ok(!styleSource.includes("[data-forward-source-status"));
assert.ok(!styleSource.includes("[data-source-binding-status"));
const forwardMobileStart = styleSource.indexOf("@media (max-width: 720px)", forwardStyleEnd);
const forwardMobileEnd = styleSource.indexOf("body.view-trade", forwardMobileStart);
assert.ok(forwardMobileStart >= 0 && forwardMobileEnd > forwardMobileStart);
const forwardMobileSource = styleSource.slice(forwardMobileStart, forwardMobileEnd);
assert.ok(forwardMobileSource.includes(".platform-forward-observation-strip > div {"));
assert.ok(forwardMobileSource.includes(".platform-forward-source {"));
assert.ok(forwardMobileSource.includes("border-right: 0;"));
assert.ok(forwardMobileSource.includes("border-bottom: 1px solid var(--line);"));
assert.ok(forwardMobileSource.includes(".platform-forward-evidence-ledger {"));
assert.ok(forwardMobileSource.includes("grid-template-columns: minmax(0, 1fr);"));
assert.ok(forwardMobileSource.includes(".platform-forward-evidence-ledger > div + div"));
assert.ok(forwardMobileSource.includes("border-left: 0;"));
assert.ok(forwardMobileSource.includes(".platform-forward-observation-strip > div:last-child"));
assert.ok(forwardMobileSource.includes(".platform-data-truth-strip > div {"));
assert.ok(forwardMobileSource.includes(".platform-data-truth-strip > div:last-child"));
assert.ok(forwardMobileSource.includes(".platform-attribution-identity dl {"));
assert.ok(forwardMobileSource.includes("grid-template-columns: 1fr;"));
assert.ok(forwardMobileSource.includes(".platform-attribution-identity dl > div {"));
assert.ok(forwardMobileSource.includes(".platform-attribution-identity dl > div:last-child"));
assert.ok(styleSource.includes(".backtest-risk-surface-spine"));
assert.ok(styleSource.includes(".platform-stage.evidence-stage"));
assert.ok(styleSource.includes("grid-template-columns: minmax(90px, 0.55fr) minmax(0, 1.45fr);"));
assert.ok(styleSource.includes(".platform-small-capital-quantity"));
assert.ok(styleSource.includes(".platform-small-capital-gap,"));
assert.ok(!styleSource.includes(".platform-small-capital-next"));
assert.ok(styleSource.includes(".backtest-metrics.backtest-evidence-ledger"));
assert.ok(styleSource.includes(".backtest-evidence-head"));
assert.ok(styleSource.includes(".internal-backtest-pack-boundary"));
assert.ok(styleSource.includes("grid-template-columns: minmax(124px, 0.55fr) minmax(210px, 1fr) minmax(280px, 1.65fr);"));
assert.ok(styleSource.includes(".internal-backtest-evidence-cue"));
const returnEvidenceCueStyleStart = styleSource.indexOf(".internal-backtest-evidence-cue {");
const returnEvidenceCueStyleEnd = styleSource.indexOf(
  ".internal-backtest-attribution-spine",
  returnEvidenceCueStyleStart,
);
assert.ok(returnEvidenceCueStyleStart >= 0 && returnEvidenceCueStyleEnd > returnEvidenceCueStyleStart);
const returnEvidenceCueStyleSource = styleSource.slice(
  returnEvidenceCueStyleStart,
  returnEvidenceCueStyleEnd,
);
assert.ok(returnEvidenceCueStyleSource.includes("border-block: 1px solid #1b211f;"));
assert.ok(returnEvidenceCueStyleSource.includes("grid-template-columns: minmax(124px, 0.55fr) minmax(0, 2.65fr);"));
assert.ok(!returnEvidenceCueStyleSource.includes("background:"));
assert.ok(!returnEvidenceCueStyleSource.includes("border-radius:"));
assert.ok(!styleSource.includes('.internal-backtest-evidence-cue[data-evidence-gap-kind'));
assert.ok(styleSource.includes(".internal-backtest-attribution-spine"));
assert.ok(styleSource.includes(".platform-evidence-attribution-spine"));
assert.ok(styleSource.includes(".platform-evidence-attribution-spine > div"));
assert.ok(styleSource.includes("grid-template-columns: repeat(3, minmax(0, 1fr));"));
const attributionIdentityStyleStart = styleSource.indexOf(
  ".platform-evidence-attribution-spine > div > .platform-attribution-identity",
);
const attributionIdentityStyleEnd = styleSource.indexOf("#platformValidate", attributionIdentityStyleStart);
assert.ok(attributionIdentityStyleStart >= 0 && attributionIdentityStyleEnd > attributionIdentityStyleStart);
const attributionIdentityStyleSource = styleSource.slice(
  attributionIdentityStyleStart,
  attributionIdentityStyleEnd,
);
assert.ok(attributionIdentityStyleSource.includes("grid-column: 1 / -1;"));
assert.ok(attributionIdentityStyleSource.includes("min-height: 44px;"));
assert.ok(attributionIdentityStyleSource.includes("summary:focus-visible"));
assert.ok(attributionIdentityStyleSource.includes("overflow-wrap: anywhere;"));
assert.ok(attributionIdentityStyleSource.includes("user-select: all;"));
assert.ok(!attributionIdentityStyleSource.includes("data-relation-status"));
assert.ok(!styleSource.includes('.internal-backtest-attribution-spine[data-relation-status'));
assert.ok(!styleSource.includes('.platform-evidence-attribution-spine[data-relation-status'));
assert.ok(styleSource.includes(".internal-backtest-quality-grid"));
assert.ok(styleSource.includes("grid-template-columns: repeat(4, minmax(0, 1fr));"));
assert.ok(styleSource.includes(".bot-readiness-panel.evidence-neutral .readiness-score strong"));
assert.ok(styleSource.includes(".bot-readiness-panel.evidence-neutral .readiness-checks .flat"));
assert.ok(styleSource.includes(".strategy-desk .strategy-war-card.evidence-neutral"));
assert.ok(styleSource.includes(".strategy-desk .execution-row.evidence-neutral.flat"));
assert.ok(styleSource.includes(".signal-item.evidence-neutral"));
assert.ok(styleSource.includes(".strategy-lab-row.evidence-neutral"));
assert.ok(styleSource.includes(".strategy-lab-evidence"));
assert.ok(styleSource.includes(".strategy-evidence-band.invalidation"));
assert.ok(styleSource.includes(".strategy-evidence-band header [data-band-code]"));
assert.ok(styleSource.includes("grid-template-columns: minmax(0, 1fr) minmax(0, 0.95fr) minmax(270px, 1.1fr);"));
assert.ok(!styleSource.includes('[data-connection-status="BOUNDARY_ONLY"]'));
assert.ok(styleSource.includes("grid-template-columns: minmax(74px, 0.85fr)"));
assert.ok(styleSource.includes(".strategy-compare-row.evidence-neutral"));
assert.ok(styleSource.includes(".bot-blueprint-row.evidence-neutral"));
assert.ok(styleSource.includes(".scheduler-row.evidence-neutral"));
assert.ok(styleSource.includes(".scheduler-conflict.flat"));
assert.ok(styleSource.includes("grid-template-columns: minmax(88px, 0.9fr)"));
assert.ok(styleSource.includes("@media (max-width: 720px)"));
const finalNarrowStart = styleSource.lastIndexOf("@media (max-width: 720px)");
assert.ok(finalNarrowStart >= 0);
const finalNarrowSource = styleSource.slice(finalNarrowStart);
assert.ok(finalNarrowSource.includes(".internal-backtest-attribution-spine"));
assert.ok(finalNarrowSource.includes(".internal-backtest-evidence-cue"));
assert.ok(finalNarrowSource.includes(".platform-evidence-attribution-spine"));
assert.ok(finalNarrowSource.includes("grid-template-columns: minmax(0, 1fr);"));

assert.ok(indexSource.includes("策略研究台"));
assert.ok(indexSource.includes("策略研究室"));
assert.ok(indexSource.includes("失效与权限边界"));
assert.ok(indexSource.includes("研究结论"));
assert.ok(indexSource.includes("模型估计"));
assert.ok(indexSource.includes("观察区间"));
assert.ok(!indexSource.includes(">交易锚点</div>"));
assert.ok(!indexSource.includes(">入场阶梯</div>"));
assert.ok(indexSource.includes('id="strategyLabSummary"'));
assert.ok(indexSource.includes('id="strategyRegime"'));
assert.ok(indexSource.includes('id="strategyLabEvidence"'));
assert.ok(indexSource.includes("策略信号参数平台未连接"));
assert.ok(indexSource.includes("固定参数时间切片"));
assert.ok(appSource.includes("function renderStrategyLabEvidence("));
assert.ok(appSource.includes("evidenceStrategyLabPresentation(data)"));
const strategyLabEvidenceStart = appSource.indexOf("function renderStrategyLabEvidence(");
const strategyLabEvidenceEnd = appSource.indexOf("async function loadStrategyLab(", strategyLabEvidenceStart);
assert.ok(strategyLabEvidenceStart >= 0 && strategyLabEvidenceEnd > strategyLabEvidenceStart);
const strategyLabEvidenceSource = appSource.slice(strategyLabEvidenceStart, strategyLabEvidenceEnd);
const strategyLabStaticStart = indexSource.indexOf('id="strategyLabEvidence"');
const strategyLabStaticEnd = indexSource.indexOf('id="strategyLabRows"', strategyLabStaticStart);
const strategyLabStaticSource = indexSource.slice(strategyLabStaticStart, strategyLabStaticEnd);
assert.equal((strategyLabStaticSource.match(/aria-live=/g) || []).length, 0);
assert.equal((strategyLabEvidenceSource.match(/aria-live=/g) || []).length, 0);
assert.ok(strategyLabEvidenceSource.includes("data-raw-status"));
assert.ok(strategyLabEvidenceSource.includes("connectionStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawImplementationStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawHypothesisStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawSearchLineageStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawAdmissionStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawMechanismStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawFutureConditionStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawPostSelectionStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawFrozenTestStatus"));
assert.ok(strategyLabEvidenceSource.includes("rawHoldoutStatus"));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="implementation"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="currentness"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="hypothesis"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="search-lineage"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="hypothesis-failure"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="admission"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="mechanism-condition"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="future-condition"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="post-selection"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="frozen-test"'));
assert.ok(strategyLabEvidenceSource.includes('data-evidence-role="holdout-confirmation"'));
assert.ok(strategyLabEvidenceSource.includes('role="group"'));
for (const [headingId, headingText] of [
  ["strategyEvidenceSourceHeading", "来源与当前性"],
  ["strategyEvidenceRobustnessHeading", "完整性与稳健性"],
  ["strategyEvidenceInvalidationHeading", "失效与权限边界"],
]) {
  for (const source of [strategyLabStaticSource, strategyLabEvidenceSource]) {
    assert.ok(source.includes(`aria-labelledby="${headingId}"`));
    assert.ok(source.includes(`<h3 id="${headingId}">${headingText}</h3>`));
  }
}
assert.ok(!strategyLabStaticSource.includes("tabindex="));
assert.ok(!strategyLabEvidenceSource.includes("tabindex="));
assert.ok(strategyLabEvidenceSource.includes("冻结后历史复算 · 非自然前向"));
assert.ok(strategyLabEvidenceSource.includes("单次历史留出 · 非自然前向"));
assert.ok(strategyLabStaticSource.includes('role="group"'));
assert.ok(strategyLabStaticSource.includes("冻结 TEST · 历史重放"));
assert.ok(strategyLabStaticSource.includes("单次历史留出 · 非自然前向"));
assert.ok(strategyLabStaticSource.includes("非盈利证明"));
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="coverage"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="post-selection"'),
);
for (const source of [strategyLabStaticSource, strategyLabEvidenceSource]) {
  assert.ok(
    source.indexOf('data-evidence-role="hypothesis"')
      < source.indexOf('data-evidence-role="search-lineage"'),
  );
  assert.ok(
    source.indexOf('data-evidence-role="search-lineage"')
      < source.indexOf('data-band-code="robustness"'),
  );
}
const lineageRendererStart = strategyLabEvidenceSource.indexOf(
  'class="strategy-search-lineage-row"',
);
const lineageRendererEnd = strategyLabEvidenceSource.indexOf("</section>", lineageRendererStart);
assert.ok(lineageRendererStart >= 0 && lineageRendererEnd > lineageRendererStart);
const lineageRendererSource = strategyLabEvidenceSource.slice(
  lineageRendererStart,
  lineageRendererEnd,
);
assert.ok(lineageRendererSource.includes("escapeHtml(evidence.rawSearchLineageStatus)"));
assert.ok(lineageRendererSource.includes("escapeHtml(evidence.lineageText)"));
assert.ok(!/(?:READY|family_id|lineage_hash|registry_path|candidate_id)/i.test(lineageRendererSource));
assert.ok(!lineageRendererSource.includes("fetch("));
assert.ok(!lineageRendererSource.includes("setInterval("));
assert.equal((appSource.match(/\/api\/strategy\/research-evidence\?strategy=/g) || []).length, 1);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="post-selection"')
    < strategyLabEvidenceSource.indexOf('data-raw-status="${escapeHtml(evidence.rawParameterStatus)}"'),
);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="frozen-test"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="holdout-confirmation"'),
);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="admission"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="failure"'),
);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="admission"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="mechanism-condition"'),
);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="mechanism-condition"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="future-condition"'),
);
assert.ok(
  strategyLabEvidenceSource.indexOf('data-evidence-role="future-condition"')
    < strategyLabEvidenceSource.indexOf('data-evidence-role="failure"'),
);
assert.ok(strategyLabEvidenceSource.includes('aria-label="开发期机制门与未来未到期条件"'));
assert.ok(strategyLabStaticSource.includes('aria-label="开发期机制门与未来未到期条件"'));
assert.ok(strategyLabStaticSource.includes("未来标准条件 · 非通过"));
assert.ok(
  indexSource.indexOf("事前研究门禁") < indexSource.indexOf("当前失效证据"),
);
assert.ok(styleSource.includes(".strategy-post-selection-group"));
assert.ok(styleSource.includes(".strategy-preregistered-gate-group"));
const preregisteredGateStyleStart = styleSource.indexOf(".strategy-preregistered-gate-group");
const preregisteredGateStyleEnd = styleSource.indexOf(
  ".strategy-evidence-band small",
  preregisteredGateStyleStart,
);
assert.ok(preregisteredGateStyleStart >= 0 && preregisteredGateStyleEnd > preregisteredGateStyleStart);
const preregisteredGateStyleSource = styleSource.slice(
  preregisteredGateStyleStart,
  preregisteredGateStyleEnd,
);
assert.ok(!preregisteredGateStyleSource.includes("var(--green)"));
assert.ok(!preregisteredGateStyleSource.includes("var(--red)"));
assert.ok(!preregisteredGateStyleSource.includes("gradient"));
assert.ok(!preregisteredGateStyleSource.includes("animation"));
assert.ok(!styleSource.includes(".strategy-evidence-band:focus-visible"));
assert.ok(styleSource.includes("border-left: 2px solid rgba(128, 146, 142, 0.34);"));
const strategyLabTabletStart = styleSource.indexOf(
  "@media (max-width: 720px)",
  styleSource.indexOf(".strategy-lab-evidence"),
);
const strategyLabPhoneStart = styleSource.indexOf("@media (max-width: 480px)", strategyLabTabletStart);
assert.ok(strategyLabTabletStart >= 0 && strategyLabPhoneStart > strategyLabTabletStart);
const strategyLabTabletSource = styleSource.slice(strategyLabTabletStart, strategyLabPhoneStart);
assert.ok(strategyLabTabletSource.includes(".strategy-lab-evidence {"));
assert.ok(strategyLabTabletSource.includes("grid-template-columns: minmax(0, 1fr);"));
assert.ok(strategyLabTabletSource.includes(".strategy-evidence-band + .strategy-evidence-band"));
assert.ok(strategyLabTabletSource.includes("grid-column: auto;"));
assert.ok(strategyLabTabletSource.includes(".strategy-search-lineage-row"));
const strategyLabPhoneEnd = styleSource.indexOf(".param-panel", strategyLabPhoneStart);
assert.ok(strategyLabPhoneEnd > strategyLabPhoneStart);
const strategyLabPhoneSource = styleSource.slice(strategyLabPhoneStart, strategyLabPhoneEnd);
assert.ok(strategyLabPhoneSource.includes(".strategy-evidence-band,"));
assert.ok(strategyLabPhoneSource.includes("grid-template-columns: minmax(0, 1fr);"));
assert.ok(strategyLabPhoneSource.includes(".strategy-evidence-band > .strategy-search-lineage-row"));
const lineageStyleStart = styleSource.indexOf(
  ".strategy-evidence-band > .strategy-search-lineage-row",
);
const lineageStyleEnd = styleSource.indexOf(".strategy-post-selection-group", lineageStyleStart);
assert.ok(lineageStyleStart >= 0 && lineageStyleEnd > lineageStyleStart);
const lineageStyleSource = styleSource.slice(lineageStyleStart, lineageStyleEnd);
assert.ok(lineageStyleSource.includes("font-variant-numeric: tabular-nums;"));
assert.ok(!/(?:var\(--green\)|var\(--red\)|gradient|animation|transition|data-raw-status)/.test(
  lineageStyleSource,
));
const postSelectionStyleStart = styleSource.indexOf(".strategy-post-selection-group");
const postSelectionStyleEnd = styleSource.indexOf(".strategy-evidence-band small", postSelectionStyleStart);
const postSelectionStyleSource = styleSource.slice(postSelectionStyleStart, postSelectionStyleEnd);
assert.ok(postSelectionStyleSource.includes("border-left"));
assert.ok(!postSelectionStyleSource.includes("var(--green)"));
assert.ok(!postSelectionStyleSource.includes("var(--red)"));
assert.ok(!postSelectionStyleSource.includes("animation"));
assert.ok(appSource.includes("row.planning_candidate?.position_pct"));
assert.ok(appSource.includes('data-lab-planning-only="1"'));
assert.ok(appSource.includes("strategyAnalysis"));
assert.ok(appSource.includes('role="button" tabindex="0"'));
assert.ok(appSource.includes('event.key === "Enter" || event.key === " "'));
assert.ok(!appSource.includes('row.score >= 60 ? "up"'));
const strategyExplainPanelStart = indexSource.indexOf('id="strategyExplainPanel"');
const strategyExplainPanelEnd = indexSource.indexOf("</section>", strategyExplainPanelStart);
assert.ok(strategyExplainPanelStart >= 0 && strategyExplainPanelEnd > strategyExplainPanelStart);
const strategyExplainPanelSource = indexSource.slice(strategyExplainPanelStart, strategyExplainPanelEnd);
assert.ok(strategyExplainPanelSource.includes('role="note"'));
assert.ok(strategyExplainPanelSource.includes('aria-label="策略解释、失效条件与权限边界"'));
assert.equal((strategyExplainPanelSource.match(/aria-live=/g) || []).length, 1);
assert.ok(strategyExplainPanelSource.includes('data-evidence-role="failure" role="status" aria-live="polite" aria-atomic="true"'));
assert.ok(strategyExplainPanelSource.includes("失效与禁做条件尚未核验"));
assert.ok(strategyExplainPanelSource.includes("研究解释 · 非订单 · 不授予模拟或实盘权限"));
assert.ok(strategyExplainPanelSource.indexOf('class="explain-no-trade"') < strategyExplainPanelSource.indexOf('class="explain-permission"'));
assert.ok(strategyExplainPanelSource.indexOf('class="explain-permission"') < strategyExplainPanelSource.indexOf('class="explain-main"'));
assert.ok(strategyExplainPanelSource.indexOf('class="explain-main"') < strategyExplainPanelSource.indexOf('class="explain-why"'));
assert.ok(strategyExplainPanelSource.indexOf('class="explain-why"') < strategyExplainPanelSource.indexOf('class="explain-evidence"'));
assert.ok(!/>\s*(?:BUY|READY|已授权|可下单)\s*</.test(strategyExplainPanelSource));
const strategyExplainRendererStart = appSource.indexOf("function renderStrategyExplainPanel()");
const strategyExplainRendererEnd = appSource.indexOf("function signalEvidenceText(", strategyExplainRendererStart);
assert.ok(strategyExplainRendererStart >= 0 && strategyExplainRendererEnd > strategyExplainRendererStart);
const strategyExplainRendererSource = appSource.slice(strategyExplainRendererStart, strategyExplainRendererEnd);
assert.equal((strategyExplainRendererSource.match(/aria-live=/g) || []).length, 1);
assert.ok(strategyExplainRendererSource.includes('data-evidence-role="failure" role="status" aria-live="polite" aria-atomic="true"'));
assert.ok(strategyExplainRendererSource.includes("escapeHtml(explanation.noTradeText)"));
assert.ok(strategyExplainRendererSource.indexOf('class="explain-no-trade"') < strategyExplainRendererSource.indexOf('class="explain-permission"'));
assert.ok(strategyExplainRendererSource.indexOf('class="explain-permission"') < strategyExplainRendererSource.indexOf('class="explain-main"'));
assert.ok(strategyExplainRendererSource.indexOf('class="explain-main"') < strategyExplainRendererSource.indexOf('class="explain-why"'));
assert.ok(strategyExplainRendererSource.indexOf('class="explain-why"') < strategyExplainRendererSource.indexOf('class="explain-evidence"'));
assert.ok(!/>\s*(?:BUY|READY|已授权|可下单)\s*</.test(strategyExplainRendererSource));
const currentStrategyExplanationStart = appSource.indexOf("function currentStrategyExplanation()");
const currentStrategyExplanationEnd = appSource.indexOf("function renderStrategyExplainPanel()", currentStrategyExplanationStart);
assert.ok(currentStrategyExplanationStart >= 0 && currentStrategyExplanationEnd > currentStrategyExplanationStart);
const currentStrategyExplanationSource = appSource.slice(currentStrategyExplanationStart, currentStrategyExplanationEnd);
assert.ok(currentStrategyExplanationSource.includes("Array.isArray(war.no_trade)"));
assert.ok(currentStrategyExplanationSource.includes(".map(evidenceStrategySourceText).filter(Boolean)"));
assert.ok(currentStrategyExplanationSource.includes("evidenceStrategySourceText(latestSignal?.reason)"));
assert.ok(currentStrategyExplanationSource.includes("evidenceStrategySourceText(top.reason)"));
assert.ok(currentStrategyExplanationSource.includes("evidenceStrategySourceText(analysis.reason)"));
assert.ok(!currentStrategyExplanationSource.includes("latestSignal?.reason || top.reason"));
assert.ok(!currentStrategyExplanationSource.includes("(war.no_trade || []).slice"));
assert.ok(styleSource.includes(".strategy-explain-panel .explain-no-trade strong"));
const strategyExplainMobileStart = styleSource.indexOf("@media (max-width: 720px)", styleSource.indexOf(".strategy-explain-panel"));
assert.ok(strategyExplainMobileStart >= 0);
const strategyExplainMobileSource = styleSource.slice(strategyExplainMobileStart);
assert.ok(strategyExplainMobileSource.includes(".strategy-explain-panel,"));
assert.ok(strategyExplainMobileSource.includes("grid-template-columns: minmax(0, 1fr);"));
const strategyAnalysisStart = appSource.indexOf("function renderStrategyAnalysis(");
const strategyAnalysisEnd = appSource.indexOf("function riskQueryParams(", strategyAnalysisStart);
assert.ok(strategyAnalysisStart >= 0 && strategyAnalysisEnd > strategyAnalysisStart, "strategy analysis research renderer should exist");
const strategyAnalysisSource = appSource.slice(strategyAnalysisStart, strategyAnalysisEnd);
assert.ok(strategyAnalysisSource.includes("strategyPlanningValue"));
assert.ok(strategyAnalysisSource.includes("strategyPlanningDirectionText"));
assert.ok(strategyAnalysisSource.includes("研究规划 TP"));
assert.ok(strategyAnalysisSource.includes('class="flat"'));
assert.ok(strategyAnalysisSource.includes("evidence-neutral"));
assert.ok(!strategyAnalysisSource.includes('class="up"'));
assert.ok(!strategyAnalysisSource.includes('class="down"'));

const correlationUnknownPayload = {
  absolute_pearson_threshold: 0.75,
  cluster_count: null,
  cluster_vote_rule: "ALL_MEMBERS_PASS_ONE_VOTE_PER_CLUSTER",
  cross_cluster_conflict_count: null,
  current_admission_allowed: false,
  current_report_schema_bound: false,
  current_writer_activation_allowed: false,
  external_authenticity_proven: false,
  first_gap_category: "INPUT_INTEGRITY",
  formal_registry_bound: false,
  full_manifest_reverified: false,
  gate_status: "UNKNOWN",
  interpretation: "DESCRIPTIVE_CORRELATION_INDEPENDENCE_ONLY",
  lane: "UNKNOWN",
  live_order_allowed: false,
  lookback_observations: 60,
  minimum_pair_overlap: 40,
  next_evidence_required: "FORMAL_PROTOCOL_BINDING_AND_NEW_REPORT_SCHEMA",
  pair_count: null,
  paper_authorized: false,
  parameter_selection_allowed: false,
  passing_cluster_count: null,
  performance_claim_allowed: false,
  preregistered_cutoff_bound: false,
  profitability_proven: false,
  replay_scope: "LOCAL_FROZEN_COMPLETED_DAILY_CLOSE_REPLAY_NOT_EXTERNAL_AUTHENTICITY",
  required_cluster_votes: null,
  required_price_rows: 61,
  schema_version: "strategy-correlation-cluster-public-summary-v1",
  source_status: "UNKNOWN",
  status: "UNKNOWN",
};
const correlationUnknown = evidence.strategyCorrelationClusterSummaryPresentation(correlationUnknownPayload);
assert.equal(correlationUnknown.valid, true);
assert.equal(correlationUnknown.rawStatus, "UNKNOWN");
assert.ok(correlationUnknown.permissionText.includes("实盘永久硬锁"));
const correlationPassPayload = {
  ...correlationUnknownPayload,
  cluster_count: 3,
  cross_cluster_conflict_count: 0,
  first_gap_category: null,
  gate_status: "PASS",
  lane: "RAW_EXCESS",
  pair_count: 6,
  passing_cluster_count: 2,
  required_cluster_votes: 2,
  source_status: "VERIFIED_LOCAL_REPLAY",
  status: "DESCRIPTIVE_PASS",
};
const correlationPass = evidence.strategyCorrelationClusterSummaryPresentation(correlationPassPayload);
assert.equal(correlationPass.valid, true);
assert.equal(correlationPass.rawStatus, "DESCRIPTIVE_PASS");
assert.ok(correlationPass.maturityText.includes("2 / 2"));
assert.equal(evidence.strategyCorrelationClusterSummaryPresentation({
  ...correlationPassPayload,
  paper_authorized: true,
}).rawStatus, "UNKNOWN");
assert.equal(evidence.strategyCorrelationClusterSummaryPresentation({
  ...correlationPassPayload,
  symbol: "SHOULD_NOT_BE_PUBLIC",
}).rawStatus, "UNKNOWN");
const boundaryWithCorrelation = evidence.strategyLabEvidencePresentation({
  evidence_contract: strategyLabBoundaryContract,
  correlation_cluster_summary: correlationUnknownPayload,
});
assert.equal(boundaryWithCorrelation.valid, true);
const strategyLabRenderStart = appSource.indexOf("function renderStrategyLabEvidence(");
const strategyLabRenderEnd = appSource.indexOf("async function loadStrategyResearchEvidence(", strategyLabRenderStart);
const strategyLabRenderSource = appSource.slice(strategyLabRenderStart, strategyLabRenderEnd);
assert.ok(strategyLabRenderSource.includes('class="strategy-correlation-ledger"'));
assert.ok(strategyLabRenderSource.includes("SOURCE"));
assert.ok(strategyLabRenderSource.includes("GAP"));
assert.ok(strategyLabRenderSource.includes("MATURITY"));
assert.ok(strategyLabRenderSource.includes("PERMISSION"));
assert.ok(styleSource.includes(".strategy-correlation-flow"));
console.log("evidence_presentation.test.js: PASS");
