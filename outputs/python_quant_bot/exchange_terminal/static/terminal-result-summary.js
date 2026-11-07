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
  const amount = (value, signed = false, fee = false) => {
    if (!finite(value)) return MISSING;
    const places = fee ? 4 : 2, rounded = Number(value.toFixed(places));
    const clean = Object.is(rounded, -0) ? 0 : rounded;
    return (signed && clean > 0 ? "+" : "") + clean.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:places});
  };
  const percentPoints = (value, signed = false) => finite(value) ? `${amount(value, signed)}%` : MISSING;
  const interval = (start, end) => present(start) || present(end) ? `${start || MISSING} 至 ${end || MISSING}` : undefined;
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

  function financialSummary({envelope, saved, native, core, kind, result, config, summary, accounting, capital, currency, holding, closedCount, status}) {
    // This projection is produced only from a verified saved core report. Its
    // last equity-curve point contains the saved closing mark, not a new quote.
    const coreDetail = core && saved === envelope && summary.schema_version === "hakimi-offline-result-view-v1";
    const curve = coreDetail && Array.isArray(envelope.equity_curve) ? envelope.equity_curve : [];
    const last = object(curve[curve.length - 1]);
    const equity = native ? result.final_equity : first(result.final_equity, coreDetail ? last.equity : undefined);
    const cash = native ? result.final_cash : first(result.final_cash, accounting.final_cash, summary.final_cash, coreDetail ? last.cash : undefined);
    const fees = first(result.total_fees, summary.total_fees);
    const returnPct = native ? result.total_return_pct : first(result.total_return, summary.total_return);
    const drawdownPct = native ? result.max_drawdown_pct : first(result.max_drawdown, summary.max_drawdown);
    const unrealized = native ? object(result.open_position).unrealized_pnl : first(result.unrealized_pnl, accounting.unrealized_pnl, summary.unrealized_pnl);
    const realized = native ? result.realized_pnl : first(result.realized_pnl, accounting.realized_pnl, summary.realized_pnl);
    const execution = first(config.execution_model, result.execution_model, summary.execution_model);
    const semantics = first(result.metric_semantics_version, summary.metric_semantics_version);
    const modelConsistent = [config.execution_model, result.execution_model, summary.execution_model].every(value => !present(value) || value === execution);
    const nativeFixed = modelConsistent && native && saved.schema_version === "hakimi-terminal-run-v1" && execution === "signal-close-next-open-ohlc-conservative-v3";
    const coreFixed = modelConsistent && core && execution === "signal-close-next-open-ohlc-v6" && semantics === "research-accounting-score-start-v2";
    const usable = kind !== "UNKNOWN" && envelope.verification_status !== "METADATA_ONLY" && saved.verification_status !== "METADATA_ONLY"
      && [envelope.status, saved.status].every(value => !present(value) || value === "COMPLETED") && result.ok !== false;
    const cashFlowKeys = ["cash_flows", "external_cash_flows", "net_cash_flow", "net_contributions", "deposits", "withdrawals"];
    const cashFlowRecorded = [envelope, saved, config, result, summary, accounting].some(value => cashFlowKeys.some(key => Object.hasOwn(value, key)));
    const fixedPrincipal = usable && (nativeFixed || coreFixed) && !cashFlowRecorded;
    const netDerived = fixedPrincipal && finite(equity) && finite(capital) && capital > 0;
    const net = netDerived ? equity - capital : coreDetail && !cashFlowRecorded && usable ? summary.net_pnl : undefined;
    const recordedPosition = coreDetail ? last.position_value : undefined;
    const positionDerived = !present(recordedPosition) && usable && (nativeFixed || coreFixed) && finite(equity) && finite(cash);
    const positionValue = present(recordedPosition) ? recordedPosition : positionDerived ? equity - cash : undefined;
    const win = closedCount > 0 ? native ? result.win_rate_pct : first(result.win_rate, summary.win_rate) : undefined;
    const unit = currency || "币种未记录";
    const money = (value, signed = false, fee = false) => finite(value) ? `${amount(value, signed, fee)} ${unit}` : MISSING;
    const returnPoints = (native || core) && finite(returnPct) ? returnPct * (native ? 1 : 100) : undefined;
    const drawdownPoints = (native || core) && finite(drawdownPct) && drawdownPct >= 0 ? drawdownPct * (native ? 1 : 100) : undefined;
    const holdingNote = !usable ? "原记录的持仓状态尚未核验，不能据此认定已清仓。" : finite(holding) && holding > 0 ? "期末仍有持仓，尚未全部卖出；现金只是总资产的一部分。"
      : holding === 0 ? "期末持仓数量为 0。" : "期末持仓状态未记录，不能据此认定已清仓。";
    const feeNote = usable && (nativeFixed || coreFixed)
      ? "手续费已在保存的现金与总资产中计入，不再从净变化重复扣除；滑点已体现在成交价格中。未发生的卖出费用不预扣。"
      : "费用是否计入权益的口径未记录，未额外扣减费用。";
    const dataKind = first(object(saved.input_summary).evidence_kind, object(object(saved.input_summary).meta).evidence_kind,
      object(object(saved.input_summary).meta).data_kind, object(saved.dataset).evidence_kind, summary.data_kind);
    return {
      usable, complete:usable && (status === "COMPLETED" || coreDetail), fixedPrincipal, cashFlowRecorded,
      netDerived, positionDerived, execution_model:execution ?? null, metric_semantics_version:semantics ?? null,
      values:{initial_cash:finite(capital)?capital:null, final_equity:finite(equity)?equity:null, net_pnl:finite(net)?net:null,
        total_return_pct:finite(returnPoints)?returnPoints:null, max_drawdown_pct:finite(drawdownPoints)?drawdownPoints:null,
        final_cash:finite(cash)?cash:null, position_value:finite(positionValue)?positionValue:null,
        realized_pnl:finite(realized)?realized:null, unrealized_pnl:finite(unrealized)?unrealized:null,
        total_fees:finite(fees)?fees:null},
      title:!usable ? "原记录数值，结果尚未核验" : status === "COMPLETED" || coreDetail ? "本段历史研究已完成" : "已保存的历史研究数值",
      scope:!usable ? "当前记录不能作为已完成研究结论；保留原状态，不自动重跑。" : "以下是这段历史的保存结果，不是未来收益预测；没有因此发送真实订单。",
      dataLabel:dataKind === "SYNTHETIC_TEST" ? "虚构教学资料" : dataKind === "IMPORTED_UNVERIFIED" ? "导入资料，来源未获独立认证" : "资料性质未记录",
      primary:[{key:"initial_cash",label:"初始本金",value:money(capital)},
        {key:"final_equity",label:"期末总资产",value:money(equity)},
        {key:"net_pnl",label:"净变化",value:money(net,true)},
        {key:"total_return",label:"区间收益率",value:percentPoints(returnPoints,true)},
        {key:"max_drawdown",label:"最大回撤",value:percentPoints(drawdownPoints)}],
      breakdown:[{key:"final_cash",label:"期末现金",value:money(cash)},
        {key:"position_value",label:"持仓市值",value:money(positionValue)},
        {key:"holding",label:"期末持仓数量",value:finite(holding)?`${number(holding)} 单位`:MISSING},
        {key:"realized_pnl",label:"已实现盈亏",value:money(realized,true)},
        {key:"unrealized_pnl",label:"持仓未实现盈亏",value:money(unrealized,true)},
        {key:"total_fees",label:"已发生手续费",value:money(fees,false,true)}],
      netNote:netDerived ? "净变化＝期末总资产－初始本金；本记录采用无追加或提取资金的固定本金研究模型。"
        : cashFlowRecorded ? "记录含资金流字段，未套用固定本金差额；净变化需要对应的现金流口径。"
        : finite(net) ? "净变化使用原保存摘要中的净损益。" : "缺少期末总资产、本金或已确认的资金口径，净变化未计算；不会用现金变化代替。",
      holdingNote, feeNote,
      closedNote:!usable ? "当前结果尚未核验，不据此解释已完成持仓回合或胜率。" : closedCount === 0 ? "本次没有已完成持仓回合，胜率不适用。" : count(closedCount) ? `已完成 ${closedCount} 个持仓回合；胜率 ${finite(win) ? percentPoints(win * (native ? 1 : 100)) : MISSING}。` : "已完成持仓回合数未记录，胜率未展示。",
      direction:usable && finite(net) ? Number(net.toFixed(2)) > 0 ? "up" : Number(net.toFixed(2)) < 0 ? "down" : "flat" : "unknown"
    };
  }

  function buildResultSummary(input) {
    const envelope = object(input), nested = object(envelope.report);
    const saved = present(nested.schema_version) ? nested : envelope;
    const native = saved.schema_version === "hakimi-terminal-run-v1"
      || (typeof saved.engine_id === "string" && saved.engine_id.startsWith("terminal."));
    const core = !native && (["us-equity-research-report-v1", "us-equity-research-report-v2", "us-equity-content-task-report-v1"].includes(saved.schema_version)
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
    const capitalContext = object(config.capital_context);
    const boundCapital = capitalContext.schema_version === "hakimi-terminal-research-capital-v1"
      && present(config.input_id) && capitalContext.input_id === config.input_id && capitalContext.initial_cash === config.initial_cash
      && ["RECORDED_FROM_FROZEN_INPUT", "UNRECORDED"].includes(capitalContext.currency_status);
    const nativeCurrency = boundCapital ? text(capitalContext.currency) : first(text(meta.currency), text(object(meta.security).currency));
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
    const finance = financialSummary({envelope, saved, native, core, kind, result, config, summary, accounting, capital, currency, holding, closedCount, status});
    for (const [key, label] of [["final_equity","期末总资产"],["net_pnl","净变化"],["position_value","持仓市值"],
      ["realized_pnl","已实现盈亏"],["unrealized_pnl","持仓未实现盈亏"]]) {
      add(key,label,number(finance.values[key]));
      rows[rows.length-1].derived = key === "net_pnl" ? finance.netDerived : key === "position_value" && finance.positionDerived;
    }
    add("total_return", "区间收益率", finite(finance.values.total_return_pct) ? percentPoints(finance.values.total_return_pct,true) : undefined);
    add("max_drawdown", "最大回撤", finite(finance.values.max_drawdown_pct) ? percentPoints(finance.values.max_drawdown_pct) : undefined);

    const warnings = [];
    for (const view of saved === envelope ? [envelope] : [envelope, saved]) {
      if (Array.isArray(view.presentation_warnings)) {
        for (const warning of view.presentation_warnings) {
          if (typeof warning === "string" && warning.trim() && !warnings.includes(warning)) warnings.push(warning);
        }
      }
    }
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
      rows, finance, zeroFillExplanation, warnings, new_economic_runs: 0};
  }

  function renderResultSummary(run, esc = escapeHtml) {
    const model = buildResultSummary(run);
    const render = value => esc(String(value));
    const finance = model.finance, rows = Object.fromEntries(model.rows.map(row=>[row.key,row]));
    const shown = key => rows[key]?.value || MISSING;
    const financialKeys = new Set([...finance.primary, ...finance.breakdown].map(row=>row.key));
    const primary = finance.primary.map(row => `<div data-result-field="${render(row.key)}" style="min-width:0"><span>${render(row.label)}</span><p class="numeric ${row.key === "net_pnl" ? render(finance.direction) : ""}" style="font-size:22px;font-weight:650;overflow-wrap:anywhere;margin:4px 0">${render(row.value)}</p></div>`).join("");
    return `<section class="tq-result-summary section-gap" aria-label="已保存研究摘要">`
      + `<section data-result-profit-card aria-label="本段历史资金结果" style="border:1px solid var(--line);border-radius:8px;padding:16px;background:var(--surface)"><h3>${render(finance.title)}</h3>`
      + `<p>${render(finance.dataLabel)} · ${render(shown("symbol"))} · ${render(shown("strategy"))}</p><p class="section-note">${render(finance.scope)}</p>`
      + `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin:16px 0">${primary}</div>`
      + `<p>${render(finance.holdingNote)}</p><dl style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0">${finance.breakdown.map(row=>`<div data-result-field="${render(row.key)}" style="min-width:0"><dt>${render(row.label)}</dt><dd class="numeric" style="margin:2px 0;overflow-wrap:anywhere">${render(row.value)}</dd></div>`).join("")}</dl>`
      + `<p class="section-note" data-result-fee-note>${render(finance.feeNote)}</p><p class="section-note">评分区间：${render(shown("score_interval"))} · 预热 ${render(shown("warmup"))} · 评分 ${render(shown("scored"))}</p>`
      + `<details><summary style="min-height:44px;padding:10px 0;cursor:pointer">查看盈亏计算与回撤说明</summary><p>${render(finance.netNote)}</p><p>最大回撤是本段历史总资产从阶段高点到后续低点的最大下降比例。</p><p>${render(finance.closedNote)}</p></details></section>`
      + (model.zeroFillExplanation ? `<p class="section-note" data-result-zero-fill>${render(model.zeroFillExplanation)}</p>` : "")
      + model.warnings.map(warning => `<p class="section-note">${render(warning)}</p>`).join("")
      + `<details class="section-gap"><summary style="min-height:44px;padding:10px 0;cursor:pointer">查看保存的身份、数据与成本</summary><div class="form-grid">${model.rows.filter(row=>!financialKeys.has(row.key)).map(row => `<div class="field" data-result-field="${render(row.key)}"><span>${render(row.label)}</span><p style="overflow-wrap:anywhere">${render(row.value)}</p></div>`).join("")}</div></details>`
      + "</section>";
  }

  const api = {buildResultSummary, renderResultSummary};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.HakimiTerminalResultSummary = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
