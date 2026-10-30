(function (root) {
  "use strict";
  const MISSING = "未记录";
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value) ? value : {};
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const count = value => finite(value) && Number.isInteger(value) && value >= 0;
  const present = value => value !== undefined && value !== null && value !== "";
  const first = (...values) => values.find(present);
  const text = value => typeof value === "string" && value.trim() ? value : undefined;
  const number = value => finite(value) ? String(value) : undefined;
  const percentage = value => finite(value) ? `${Number((value * 100).toPrecision(15))}%` : undefined;
  const interval = (start, end) => present(start) || present(end) ? `${start || MISSING} 至 ${end || MISSING}` : undefined;
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

  function buildResultSummary(input) {
    const envelope = object(input), nested = object(envelope.report);
    const saved = present(nested.schema_version) ? nested : envelope;
    const native = saved.schema_version === "hakimi-terminal-run-v1"
      || (typeof saved.engine_id === "string" && saved.engine_id.startsWith("terminal."));
    const core = !native && (saved.schema_version === "us-equity-research-report-v1"
      || present(object(envelope.manifest).task) || present(object(envelope.summary).strategy));
    const kind = native ? "NATIVE_ORIGINAL" : core ? "CANONICAL_CORE" : "UNKNOWN";
    const result = object(saved.result), config = object(saved.configuration);
    const summary = object(envelope.summary), manifest = object(envelope.manifest);
    const identities = object(envelope.identities), inputSummary = object(saved.input_summary);
    const dataset = object(saved.dataset), evaluation = object(result.evaluation_window);
    const statistics = object(result.statistical_status), accounting = object(result.accounting);
    const spec = core ? object(saved.spec) : {};
    const coreRequested = object(object(envelope.configuration).requested);
    const meta = object(inputSummary.meta);
    const nativeCurrency = first(text(meta.currency), text(object(meta.security).currency));
    const security = object(dataset.security), sessions = Array.isArray(dataset.sessions) ? dataset.sessions : null;
    const candleRows = Array.isArray(envelope.candles) ? envelope.candles : null;
    const sourceRuntime = first(object(manifest.runtime).source_identity, object(saved.provenance).source_identity);
    const status = envelope.status === "UNKNOWN" || saved.status === "UNKNOWN"
      ? "UNKNOWN" : first(text(envelope.status), text(saved.status));
    const rows = [];
    const add = (key, label, value) => rows.push({key, label, value: present(value) ? String(value) : MISSING, recorded: present(value)});
    const recordedCount = (...values) => values.find(count);
    const nativeVersion = first(saved.version, config.version);
    const summaryStrategy = object(summary.strategy), savedStrategy = object(result.strategy);
    const strategyId = native ? first(saved.strategy_id, config.strategy_id, savedStrategy.id)
      : first(object(manifest.task).strategy, summaryStrategy.key, object(spec.strategy).name, object(coreRequested.strategy).name);
    const strategyName = native ? first(saved.strategy_name, savedStrategy.name) : summaryStrategy.title;
    const strategy = present(strategyName) && strategyName !== strategyId
      ? `${strategyName} · ${strategyId || MISSING}` : strategyId;
    const dataStart = native ? first(inputSummary.date_start, object(result.dataset_manifest).first)
      : first(sessions?.[0]?.date, candleRows?.[0]?.time);
    const dataEnd = native ? first(inputSummary.date_end, object(result.dataset_manifest).last)
      : first(sessions?.[sessions.length - 1]?.date, candleRows?.[candleRows.length - 1]?.time);
    const scoring = object(saved.scoring_protocol);
    const scoreStart = native ? evaluation.start : first(spec.score_start_session, coreRequested.score_start_session, summary.score_start, scoring.score_start);
    const scoreEnd = native ? evaluation.end : first(spec.score_end_session, coreRequested.score_end_session, summary.score_end, scoring.score_end);
    const warmup = native ? first(evaluation.context_rows, config.warmup_rows)
      : first(scoring.available_context_sessions, object(result.scoring).warmup_rows);
    const scored = native ? evaluation.evaluated_rows
      : first(scoring.scored_sessions, object(result.scoring).scored_bar_count);
    const currency = native ? nativeCurrency : first(text(security.currency), text(summary.currency));
    const capital = native ? first(config.initial_cash, result.initial_cash)
      : first(spec.initial_cash, coreRequested.initial_cash);
    const fee = native ? first(object(config.costs).fee_rate, result.fee_rate)
      : first(spec.fee_rate, coreRequested.fee_rate);
    const slippage = native ? first(object(config.costs).slippage_bps, result.slippage_bps)
      : first(spec.slippage_pct, coreRequested.slippage_pct);
    const fillCount = native ? recordedCount(result.order_event_count)
      : recordedCount(result.fill_count, accounting.fill_count, summary.fill_count);
    const closedCount = native ? recordedCount(result.trade_count)
      : recordedCount(result.round_trip_count, accounting.round_trip_count, summary.round_trip_count);
    const holding = native ? object(result.open_position).quantity
      : first(result.open_position_qty, accounting.open_position_qty, summary.open_position_qty);
    const signalCount = recordedCount(result.signal_count, accounting.signal_count, summary.signal_count);
    const decisionCount = recordedCount(result.decision_count, accounting.decision_count, summary.decision_count);
    const runId = first(envelope.run_id, manifest.run_id, identities.run_id, native ? saved.id : undefined);
    const reportHash = first(envelope.report_hash, saved.report_hash, identities.report_hash, native ? saved.id : undefined);
    const taskId = first(saved.task_id, manifest.task_id, identities.task_id, summary.task_id);
    add("symbol", "股票 / 标的", native ? first(inputSummary.symbol, saved.symbol, result.symbol) : first(security.symbol, summary.symbol));
    add("strategy", "保存的规则", strategy);
    add("engine", "保存的引擎身份", first(saved.engine_id, envelope.engine_id, config.engine_id));
    add("execution_model", "成交模型", first(config.execution_model, result.execution_model));
    add("task_version", "任务版本", native ? number(nativeVersion) : number(summary.task_version_number));
    add("rule_version", "规则版本", core ? first(summaryStrategy.version, object(result.reproducibility).strategy_version) : saved.strategy_version);
    add("data_interval", "封存数据区间", interval(dataStart, dataEnd));
    add("input_id", "封存行情标识", native ? first(config.input_id, inputSummary.input_id, inputSummary.id) : dataset.snapshot_id);
    add("score_interval", "评分区间", interval(scoreStart, scoreEnd));
    add("warmup", "预热 / 上下文", count(warmup) ? `${warmup} 根` : undefined);
    add("scored", "参与评分", count(scored) ? `${scored} 根` : undefined);
    add("initial_cash", "初始本金", number(capital));
    add("currency", "币种", currency);
    add("fee_rate", "手续费率", percentage(fee));
    add("slippage", "滑点", native ? (finite(slippage) ? `${number(slippage)} 基点` : undefined) : percentage(slippage));
    add("fills", "成交事件数", number(fillCount));
    add("closed", "已完成持仓回合", number(closedCount));
    add("holding", "期末持仓数量", number(holding));
    add("final_cash", "期末现金", number(first(result.final_cash, accounting.final_cash, summary.final_cash)));
    add("total_fees", "已发生手续费", number(first(result.total_fees, summary.total_fees)));
    add("run_id", "保存的运行标识", runId);
    add("task_id", "保存的任务标识", taskId);
    add("report_hash", "结果校验值", reportHash);
    add("source_identity", "保存的计算来源", object(sourceRuntime).content_sha256);

    const warnings = [];
    if (kind === "UNKNOWN") warnings.push("尚未识别此保存格式；缺少的信息显示为未记录。");
    if (status === "UNKNOWN") warnings.push("此运行状态仍为 UNKNOWN，尚无完整结果；保留原记录，不自动重跑。");
    if (envelope.verification_status === "METADATA_ONLY") warnings.push("此记录尚未通过读取校验，以下仅为原文件信息，不提供验收结论。");
    if (statistics.status === "INSUFFICIENT_EVIDENCE") warnings.push("原报告标记为 INSUFFICIENT_EVIDENCE：样本不足以支持策略有效性判断。");
    if (statistics.annualized_return === "SHORT_SAMPLE" || statistics.sharpe_ratio === "SHORT_SAMPLE") {
      warnings.push("原报告记录评分样本较短，相关统计只供描述。");
    }
    let zeroFillExplanation = null;
    const zero = fillCount === 0 && (!status || status === "COMPLETED") && envelope.verification_status !== "METADATA_ONLY";
    if (zero) {
      const pieces = ["本次保存结果记录为零成交。"];
      const signals = Array.isArray(result.signals) ? result.signals : Array.isArray(envelope.signals) ? envelope.signals : null;
      if (signalCount === 0 && decisionCount > 0) {
        pieces.push(`记录了 ${decisionCount} 次决策，交易信号数为 0。`);
        if (core && signals?.length === decisionCount && signals.every(row => row?.action === "HOLD" && row?.reason === "no MA crossover")) {
          pieces.push("各次已保存决策的原因均为未发生均线交叉。");
        }
      } else if (core && signals?.length === decisionCount && decisionCount > 0 && signals.every(row => row?.action === "HOLD")) {
        pieces.push(`已保存的 ${decisionCount} 次决策全部为 HOLD（继续观察）。`);
      } else if (native && ["BUY", "ADD"].includes(result.pending_signal_at_end)) {
        pieces.push("末尾记录了待执行买入信号，封存区间内没有下一根开盘供该信号成交；这只说明末尾状态，不能确定整个区间的零成交原因。");
      } else {
        pieces.push("现有记录没有足够的信号与决策依据，无法确定零成交原因。");
      }
      pieces.push("零成交只描述这次样本，不能据此认定策略有效或无效。");
      zeroFillExplanation = pieces.join("");
    }
    return {kind, status: status || "UNRECORDED", identity: {run_id: runId ?? null, task_id: taskId ?? null, report_hash: reportHash ?? null},
      rows, zeroFillExplanation, warnings, new_economic_runs: 0};
  }

  function renderResultSummary(run, esc = escapeHtml) {
    const model = buildResultSummary(run);
    const render = value => esc(String(value));
    return `<section class="tq-result-summary section-gap" aria-label="已保存研究摘要"><h3>这次保存的研究</h3>`
      + `<div class="form-grid">${model.rows.map(row => `<div class="field" data-result-field="${render(row.key)}"><span>${render(row.label)}</span><p style="overflow-wrap:anywhere">${render(row.value)}</p></div>`).join("")}</div>`
      + (model.zeroFillExplanation ? `<p class="section-note" data-result-zero-fill>${render(model.zeroFillExplanation)}</p>` : "")
      + model.warnings.map(warning => `<p class="section-note">${render(warning)}</p>`).join("")
      + "</section>";
  }

  const api = {buildResultSummary, renderResultSummary};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.HakimiTerminalResultSummary = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
