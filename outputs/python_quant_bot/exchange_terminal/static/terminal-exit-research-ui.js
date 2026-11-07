/* Frozen, paired exit research. Importing this file never reads DOM or runs research. */
(function(root) {
  "use strict";
  const RULES={fixed_pct:"固定止损",atr_trailing:"ATR 跟踪",confirmed_structure:"已确认结构"};
  const SEGMENTS={TRAIN:"训练段",VALIDATION:"验证段",TEST:"留出测试段"};
  const STATES={EXITED:"已退出",CENSORED:"观察截断",UNAVAILABLE:"规则不可用",UNKNOWN:"待核对"};
  const REASONS={ATR_NOT_AVAILABLE_BEFORE_ENTRY:"入场前 ATR 数据不足",NO_CONFIRMED_SUPPORT_BEFORE_ENTRY:"入场前无已确认支撑",CONFIRMED_SUPPORT_NOT_BELOW_ENTRY:"已确认支撑不低于入场价",SEGMENT_END:"到达分段边界",MAX_HOLD_BARS:"到达最大观察持有期",GAP_OPEN:"开盘跳空触发",INTRABAR_STOP:"盘中触及阈值"};
  const hash=(v)=>typeof v==="string"&&/^[0-9a-f]{64}$/.test(v);
  const esc=(v)=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const num=(v)=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("zh-CN",{maximumFractionDigits:4}):"—";
  const clone=(v)=>JSON.parse(JSON.stringify(v));
  const day=(v)=>typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+"T00:00:00Z"))&&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
  function sourceBlocker(run,catalog=[]) {
    if(run?.status!=="COMPLETED"||!hash(run.run_id||run.id))return "请选择已完整保存的原生回测结果。";
    const entry=catalog.find(v=>v.id===(run.strategy_id||run.configuration?.strategy_id));
    if(entry?.capability?.new_research_allowed!==true||entry?.capability?.backtest_supported!==true)return "此策略当前只保留历史记录，不允许新建出场研究。";
    if((run.result?.trades||[]).some(v=>v.side==="ADD"))return "该原结果含加仓事件，暂不能固定为独立 BUY 入场样本。";
    return "";
  }
  function defaultSpec(rows) {
    const dates=[...new Set((rows||[]).map(v=>v.date).filter(day))];
    if(dates.length<3)throw new Error("冻结行情至少需要 3 个交易日才能划分三段。");
    const a=Math.max(1,Math.min(dates.length-2,Math.floor(dates.length*.6))),b=Math.max(a+1,Math.min(dates.length-1,Math.floor(dates.length*.8)));
    return {split:{TRAIN:{start_date:dates[0],end_date:dates[a-1]},VALIDATION:{start_date:dates[a],end_date:dates[b-1]},TEST:{start_date:dates[b],end_date:dates.at(-1)}},fixed_stop_pct:5,atr_window:14,atr_mult:2,structure_left_window:3,structure_right_window:3,emergency_stop_pct:15,max_hold_bars:60,costs:{fee_rate:.001,slippage_bps:5}};
  }
  function registerPayload(source,spec,requestId) {
    if(!source||!hash(source.run_id||source.id))throw new Error("请先选定冻结结果。");
    const rows=source.chart?.rows||[],dates=rows.map(v=>v.date),first=dates[0]||source.input_summary?.date_start,last=dates.at(-1)||source.input_summary?.date_end;
    let end="";
    for(const segment of Object.keys(SEGMENTS)) {
      const range=spec.split?.[segment];
      if(!day(range?.start_date)||!day(range?.end_date)||range.start_date>range.end_date||range.start_date<=end)throw new Error("三段日期必须有效、先后有序且互不重叠。");
      if((first&&range.start_date<first)||(last&&range.end_date>last))throw new Error("分段日期必须位于冻结行情覆盖范围内。");
      if(dates.length&&!dates.some(v=>v>=range.start_date&&v<=range.end_date))throw new Error("每段至少需要一根已冻结的 K 线。");
      end=range.end_date;
    }
    if(dates.length&&(source.result?.trades||[]).filter(v=>v.side==="BUY").some(v=>!Object.values(spec.split).some(r=>v.date>=r.start_date&&v.date<=r.end_date)))throw new Error("每条原 BUY 入场必须归入其中一段，不能遗漏样本。");
    for(const key of ["fixed_stop_pct","emergency_stop_pct"])if(!Number.isFinite(spec[key])||spec[key]<=0||spec[key]>100)throw new Error("止损百分比必须大于 0 且不超过 100。");
    for(const key of ["atr_window","structure_left_window","structure_right_window","max_hold_bars"])if(!Number.isSafeInteger(spec[key])||spec[key]<1)throw new Error("ATR 窗口、结构窗口和最大持有期必须是正整数。");
    if(!Number.isFinite(spec.atr_mult)||spec.atr_mult<=0)throw new Error("ATR 倍数必须大于 0。");
    if(!Number.isFinite(spec.costs?.fee_rate)||spec.costs.fee_rate<0||spec.costs.fee_rate>1||!Number.isFinite(spec.costs?.slippage_bps)||spec.costs.slippage_bps<0||spec.costs.slippage_bps>10000)throw new Error("请核对手续费和滑点范围。");
    return {client_request_id:requestId,original_run_id:source.run_id||source.id,spec:clone(spec)};
  }
  function createController({api,perform,uuid,changed=()=>{}}) {
    const state={experiments:[],runs:[],warnings:[],source:null,experiment:null,run:null,busy:false,loading:false,error:"",unknown:null,draftRequest:null};
    let selection=0,refreshSequence=0; const emit=()=>changed(state);
    async function openExperiment(id) {
      const seq=++selection;state.run=null;state.experiment=null;state.error="";emit();
      try{const value=await api("terminal_exit_experiments/"+encodeURIComponent(id));if(seq!==selection)return;
        if((value.experiment_id||value.id)!==id)throw new Error("实验身份不匹配。");state.experiment=value;emit();return value;
      }catch(e){if(seq===selection){state.experiment={id,experiment_id:id,status:"UNKNOWN",reason:e.message};state.error="实验读取失败，未重建或运行。";emit();}}
    }
    async function openRun(id) {
      const seq=++selection;state.run=null;state.error="";emit();
      try{const value=await api("terminal_exit_runs/"+encodeURIComponent(id));if(seq!==selection)return;
        if((value.exit_run_id||value.id)!==id)throw new Error("结果身份不匹配。");state.run=value;if(state.experiment&&(state.experiment.experiment_id||state.experiment.id)!==value.experiment_id)state.experiment=null;emit();return value;
      }catch(e){if(seq===selection){state.run={id,exit_run_id:id,status:"UNKNOWN",reason:e.message};state.error="结果读取失败，未补算。";emit();}}
    }
    async function refresh() {
      const seq=++refreshSequence;state.loading=true;state.error="";emit();
      try{const [experiments,runs]=await Promise.all([api("terminal_exit_experiments"),api("terminal_exit_runs")]);if(seq!==refreshSequence)return;
        state.experiments=experiments.items||[];state.runs=runs.items||[];state.warnings=[...(experiments.warnings||[]),...(runs.warnings||[])];
        if(state.unknown){const pending=state.unknown,items=pending.action==="terminal_register_exit_experiment"?state.experiments:state.runs;
          const item=items.find(v=>v.client_request_id===pending.requestId&&v.integrity_status==="PASS"&&v.status===(pending.action==="terminal_register_exit_experiment"?"REGISTERED":"COMPLETED"));
          if(item){const detail=pending.action==="terminal_register_exit_experiment"?await openExperiment(item.experiment_id||item.id):await openRun(item.exit_run_id||item.id);
            if(detail?.client_request_id===pending.requestId&&detail.status===item.status&&detail.integrity_status==="PASS"){state.unknown=null;if(item.status==="REGISTERED")state.source=null;}}
        }else if(state.run)await openRun(state.run.exit_run_id||state.run.id);
        else if(state.experiment)await openExperiment(state.experiment.experiment_id||state.experiment.id);
      }catch(e){if(seq===refreshSequence)state.error=e.message||"研究列表读取失败。";}
      finally{if(seq===refreshSequence){state.loading=false;emit();}}
    }
    function begin(source) {if(state.busy||state.unknown)throw new Error("上次提交仍待核对，请先刷新记录并查看日志。");state.source=clone(source);state.draftRequest=uuid();state.error="";emit();}
    async function mutate(action,payload) {
      if(state.busy||state.unknown)throw new Error("提交仍待核对，不能重复运行或登记。");state.busy=true;state.error="";emit();
      try{let accepted=null;const result=await perform(action,payload,{onSuccess:v=>{accepted=v;}}),value=accepted||result;
        const expected=action==="terminal_register_exit_experiment"?"REGISTERED":"COMPLETED";
        const identity=action==="terminal_register_exit_experiment"?(value?.experiment_id||value?.id):(value?.exit_run_id||value?.id);
        if(!hash(identity)||value.status!==expected||value.integrity_status!=="PASS"||value.client_request_id!==payload.client_request_id)throw new Error(value?.reason||"提交结果未确认。");
        if(expected==="REGISTERED"){state.experiment=value;state.source=null;state.run=null;}else state.run=value;
        await refresh();return value;
      }catch(e){state.unknown={action,requestId:payload.client_request_id};state.error=(e.message||"操作结果未确认。")+" 请刷新核对保存记录，不自动重试。";return null;}
      finally{state.busy=false;emit();}
    }
    async function runExperiment() {
      const id=state.experiment?.experiment_id||state.experiment?.id;
      if(state.experiment?.status!=="REGISTERED"||state.experiment?.integrity_status!=="PASS"||!hash(id))throw new Error("请先登记一份已核验的实验配置。");
      const prior=state.runs.find(v=>v.experiment_id===id);if(prior)return openRun(prior.exit_run_id||prior.id);
      if(state.experiment.requires_revision||state.experiment.run_compatibility==="REQUIRES_NEW_REGISTRATION")throw new Error("计算服务已更新，请从原结果重新登记实验。");
      return mutate("terminal_run_exit_experiment",{client_request_id:uuid(),experiment_id:id});
    }
    return {state,begin,refresh,openExperiment,openRun,runExperiment,register:spec=>mutate("terminal_register_exit_experiment",registerPayload(state.source,spec,state.draftRequest))};
  }
  function specHtml(spec) {return `<dl class="kv"><dt>三段时间</dt><dd>${Object.entries(SEGMENTS).map(([key,label])=>`${label}：${esc(spec?.split?.[key]?.start_date||"—")} 至 ${esc(spec?.split?.[key]?.end_date||"—")}`).join("<br>")}</dd><dt>固定 / ATR</dt><dd>${num(spec?.fixed_stop_pct)}% / ${num(spec?.atr_window)} 根 × ${num(spec?.atr_mult)}</dd><dt>结构确认窗口</dt><dd>左 ${num(spec?.structure_left_window)} 根 · 右 ${num(spec?.structure_right_window)} 根</dd><dt>统一保护与观察期</dt><dd>${num(spec?.emergency_stop_pct)}% · 最多 ${num(spec?.max_hold_bars)} 根</dd><dt>出场成本</dt><dd>手续费 ${num(typeof spec?.costs?.fee_rate==="number"?spec.costs.fee_rate*100:null)}% · 滑点 ${num(spec?.costs?.slippage_bps)} bps</dd></dl>`;}
  function experimentHtml(value,runs=[]) {
    if(!value)return '<p class="muted">选择已登记实验，查看冻结配置。</p>';
    if(value.status!=="REGISTERED"||value.integrity_status!=="PASS")return `<div class="notice warning">实验待核对，不能运行。${esc(value.reason||"")}</div>`;
    const prior=runs.find(v=>v.experiment_id===(value.experiment_id||value.id));
    return `<h3 id="te-experiment-title" tabindex="-1">已登记 · ${esc(value.symbol||"冻结样本")}</h3><p>同一组 ${num(value.cohort_count)} 条 BUY 入场 · 登记时间 ${esc(value.recorded_at||"未记录")}</p>${specHtml(value.spec)}<p class="section-note">入场时间、价格、数量与费用沿用原结果；三条规则共用出场成本和紧急保护。达到边界仍未退出的样本只记为截断。</p><div class="actions section-gap">${prior?`<button class="btn" type="button" data-te-action="open-run" data-te-id="${esc(prior.exit_run_id||prior.id)}">查看已保存运行记录</button>`:(value.requires_revision||value.run_compatibility==="REQUIRES_NEW_REGISTRATION")?`<div class="notice warning">计算服务已更新，请从原结果重新登记实验。</div><button class="btn" type="button" data-te-action="revise" data-te-id="${esc(value.original_run_id)}">从原结果重新登记</button>`:'<button class="btn primary" id="te-run-submit" type="button" data-te-action="run">按已登记配置运行一次</button>'}</div><details class="section-gap"><summary>冻结身份、配置与来源</summary><pre class="code-detail">${esc(JSON.stringify(value,null,2))}</pre></details>`;
  }
  function outcomeHtml(value) {
    if(!value)return '<strong>待核对</strong>';
    const settled=value.status==="EXITED";
    return `<strong>${esc(STATES[value.status]||"待核对")}</strong><p>${esc(REASONS[value.reason]||value.reason||"原因未记录")}</p>${settled?`<p>${esc(value.exit?.date||"—")} · ${num(value.exit?.price)}</p><p>净收益 ${num(value.net_return_pct)}% · 费用 ${num(value.fees?.total)}</p>`:'<p>净收益 —（未结算）</p>'}<p>观察 ${num(value.duration_bars)} 根 · MAE ${num(value.mae_pct)}% / MFE ${num(value.mfe_pct)}%</p>${value.censor?`<p>截止 ${esc(value.censor.date)}</p>`:""}`;
  }
  function resultHtml(value,context={}) {
    if(!value)return '<p class="muted">运行后在此查看三种规则的配对结果。</p>';
    if(value.status!=="COMPLETED"||value.integrity_status!=="PASS"||!value.result)return `<div class="notice warning"><strong>结果待核对 · 不可复盘</strong><p>${esc(value.reason||value.error||"没有完整且可核验的结果。")}</p><p>不自动运行或补齐结果。</p></div>`;
    const result=value.result,samples=result.samples||[],summaries=result.summaries||value.summaries||{},segments=result.segment_stats||value.segment_stats||{},marks=result.structure_marks||value.structure_marks||[];
    return `<h3 id="te-result-title" tabindex="-1">同入场出场对照 · ${esc(context.symbol||value.symbol||"冻结样本")} · 已保存</h3><p class="section-note">原结果 ${esc(String(value.original_run_id||context.original_run_id||"未记录").slice(0,16))} · 冻结输入 ${esc(String(context.input_id||"见实验记录").slice(0,16))} · ${esc(context.bar||"周期见实验记录")}</p><div class="notice">独立入场样本，不是账户权益回测。各样本可能重叠；不合计为资金曲线，也不据此认定最佳策略。</div><div class="actions section-gap"><button class="btn" type="button" data-te-action="replay">在原图查看结构与出场路径</button></div><div id="te-replay-status" class="section-note section-gap" role="status">图中使用原冻结行情和保存的路径；不重新生成入场。</div><h4 class="section-gap">分段统计</h4><p class="section-note">平均净收益仅统计已退出样本；截断与不可用样本单列。配对差值仅用两规则均退出的同一入场，截断与不可用被排除，不能据此宣布整体最优。原入场受原策略及原出场影响，存在选择偏差；本次登记是当前历史研究，不是真正的事前预测。</p><div class="te-table"><table><thead><tr><th>分段</th><th>规则</th><th>样本</th><th>已退出</th><th>截断</th><th>不可用</th><th>净收益（已退出）</th><th>时长与费用（已退出）</th></tr></thead><tbody>${Object.entries(SEGMENTS).flatMap(([segment,label])=>Object.entries(RULES).map(([rule,name])=>{const s=summaries[rule]?.[segment];return `<tr><td>${label}</td><td>${name}</td><td>${num(s?.sample_count)}</td><td>${num(s?.exited_count)}</td><td>${num(s?.censored_count)}</td><td>${num(s?.unavailable_count)}</td><td>${s?.sample_count===0?"样本不足":s?.exited_count===0?"无已退出样本":"均值 "+num(s?.mean_net_return_pct_exited_only)+"%"}<p>中位数 ${num(s?.median_net_return_pct_exited_only)}%</p><p>最差 ${num(s?.worst_net_return_pct_exited_only)}%</p></td><td>平均 ${num(s?.mean_duration_bars_exited_only)} 根<p>平均费用 ${num(s?.mean_total_fee_exited_only)}</p><p>平均 MAE / MFE ${num(s?.mean_mae_pct_exited_only)}% / ${num(s?.mean_mfe_pct_exited_only)}%</p></td></tr>`;})).join("")}</tbody></table></div><div class="te-table section-gap"><table><thead><tr><th>分段</th><th>配对（后者减前者）</th><th>双方已退出 / 排除样本</th><th>平均收益差（百分点）</th></tr></thead><tbody>${Object.entries(SEGMENTS).flatMap(([segment,label])=>Object.entries(segments[segment]?.paired||{}).map(([key,pair])=>`<tr><td>${label}</td><td>${key.split("_vs_").map(k=>RULES[k]||esc(k)).join(" → ")}</td><td>${num(pair.paired_exited_count)} / ${num(pair.excluded_censored_or_unavailable_count)}</td><td>${num(pair.right_minus_left_mean_net_return_pct_points)}</td></tr>`)).join("")}</tbody></table></div><h4 class="section-gap">逐笔同入场对照</h4><div class="te-table"><table><thead><tr><th>入场样本</th>${Object.values(RULES).map(v=>`<th>${v}</th>`).join("")}</tr></thead><tbody>${samples.map(sample=>`<tr><td><strong>${esc(sample.entry?.date)}</strong><p>${esc(SEGMENTS[sample.segment]||sample.segment)} · ${esc(sample.sample_id||sample.entry?.sample_id)}</p><p>价格 ${num(sample.entry?.price)} · 数量 ${num(sample.entry?.quantity)}</p><p>原入场费用 ${num(sample.entry?.fee)}</p><details><summary>逐根决策依据</summary><pre class="code-detail">${esc(JSON.stringify(sample,null,2))}</pre></details></td>${Object.keys(RULES).map(rule=>`<td>${outcomeHtml(sample.outcomes?.[rule])}</td>`).join("")}</tr>`).join("")||'<tr><td colspan="4">样本不足，没有可展示的入场。</td></tr>'}</tbody></table></div><details class="section-gap"><summary>结构发生与确认时间（${marks.length} 项）</summary><p class="section-note">右侧窗口完成后才确认转折；发生日不代表当日已知。</p><div class="te-table"><table><thead><tr><th>类型</th><th>发生日</th><th>确认日</th><th>价格</th></tr></thead><tbody>${marks.map(m=>`<tr><td>${esc(m.classification||m.kind)}</td><td>${esc(m.pivot_date||m.date)}</td><td>${esc(m.confirmed_at_date)}</td><td>${num(m.price)}</td></tr>`).join("")||'<tr><td colspan="4">没有可用的已确认结构。</td></tr>'}</tbody></table></div></details><details class="section-gap"><summary>结果身份与冻结参数</summary>${specHtml(result.spec||value.spec)}<pre class="code-detail">${esc(JSON.stringify({exit_run_id:value.exit_run_id||value.id,experiment_id:value.experiment_id,original_run_id:value.original_run_id,report_hash:value.report_hash,source_hashes:value.source_hashes,schema_version:result.schema_version},null,2))}</pre></details>`;
  }
  function install({host,api,perform,notify=()=>{},sendReplay,validReplay}) {
    if(!host||host.querySelector("#terminalExitResearchWorkspace"))return null;
    const document=host.ownerDocument,section=document.createElement("section");section.id="terminalExitResearchWorkspace";section.className="panel section-gap te";
    const fields=[["fixed_stop_pct","固定止损（%）",.01,100,.01],["atr_window","ATR 窗口（根）",1,"",1],["atr_mult","ATR 倍数",.01,"",.01],["structure_left_window","结构左窗口（根）",1,"",1],["structure_right_window","结构右确认窗口（根）",1,"",1],["emergency_stop_pct","统一紧急止损（%）",.01,100,.01],["max_hold_bars","最大观察持有期（根）",1,"",1],["fee_pct","统一出场手续费（%）",0,100,.001],["slippage_bps","统一出场滑点（bps）",0,10000,.1]];
    section.innerHTML=`<div class="panel-head"><div><h2>结构与出场研究</h2><p class="section-note">固定原 BUY 入场，比较三种出场规则。独立入场样本，不是账户权益回测。</p></div><button class="btn small" type="button" data-te-action="refresh">刷新研究记录</button></div><div class="panel-body"><div id="te-message" class="notice" role="status" hidden></div><div id="te-error" class="notice error" role="alert" tabindex="-1" hidden></div><div class="te-source"><div class="field"><label for="te-source">原生已完成结果</label><select id="te-source"></select></div><button class="btn" type="button" data-te-action="new">新建出场对照</button></div><div class="te-source section-gap"><div class="field"><label for="te-input">独立查看冻结行情结构</label><select id="te-input"></select></div><button class="btn" type="button" data-te-action="structure">在原图查看已确认结构</button></div><p class="hint">结构查看使用左右各 3 根窗口，不需要入场样本。不会新增策略运行或成交。</p><form id="te-form" class="form-section" hidden><h3 id="te-form-title" tabindex="-1">登记出场研究配置</h3><div id="te-source-summary" class="notice"></div><h4>时间切分</h4><p class="hint">初始按交易日约 60% / 20% / 20% 划分，可修改。每条原 BUY 入场须在其中一段；三段不能重叠。所有段都在登记后冻结。</p><div class="form-grid">${Object.entries(SEGMENTS).map(([key,label])=>`<div class="field"><label for="te-${key}-start">${label}起日</label><input type="date" id="te-${key}-start" required></div><div class="field"><label for="te-${key}-end">${label}止日</label><input type="date" id="te-${key}-end" required></div>`).join("")}</div><h4>统一规则与成本</h4><p class="hint">表单中的数值为可编辑的研究起点，不表示推荐参数。入场成本沿用原成交；下列成本只用于三个方案的出场。</p><div class="form-grid">${fields.map(([key,label,min,max,step])=>`<div class="field"><label for="te-${key}">${label}</label><input type="number" id="te-${key}" min="${min}" ${max!==""?`max="${max}"`:""} step="${step}" required></div>`).join("")}</div><p class="section-note">ATR 跟踪使用收盘高水位与上一根完成 K 线的简单 ATR。结构在右窗口完成后才可用；无已确认支撑或 ATR 不足时标记不可用。到达分段边界或最大持有期只记截断，不假设强制成交。</p><button id="te-register-submit" class="btn primary" type="submit">登记配置（不运行）</button></form><div class="te-record-grid section-gap"><div><h3>已登记实验</h3><div id="te-experiments"></div><h3 class="section-gap">已保存研究结果</h3><div id="te-runs"></div></div><div><div id="te-experiment"></div><div id="te-result" class="section-gap"></div></div></div></div>`;
    const anchor=host.querySelector("#terminalJudgmentWorkspace")||host.querySelector("#tq-runs")?.closest(".panel");if(anchor)anchor.after(section);else host.append(section);
    const style=document.createElement("style");style.textContent=`.te{min-width:0}.te [hidden]{display:none!important}.te .panel-head p{margin:6px 0 0}.te .btn{min-height:44px}.te-source{display:flex;align-items:end;gap:12px;margin-top:12px}.te-source .field{flex:1;min-width:0}.te select{width:100%}.te-record-grid{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,3fr);gap:22px}.te-record{display:block;width:100%;text-align:left;padding:12px;margin:8px 0;border:1px solid var(--line);border-radius:7px;color:var(--ink);background:var(--surface);overflow-wrap:anywhere;min-height:44px}.te-record[aria-current=true]{border-color:var(--blue)}.te-record p,.te-table p{font-size:12px;line-height:1.6;margin:5px 0}.te-table{overflow:auto;max-height:440px}.te-table table{min-width:680px;width:100%;border-collapse:collapse}.te-table th,.te-table td{vertical-align:top;text-align:left;padding:10px;border-bottom:1px solid var(--line)}.te .code-detail{max-width:100%;max-height:300px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}.te .kv dd{overflow-wrap:anywhere}.te summary{cursor:pointer}.te button:focus-visible,.te input:focus-visible,.te select:focus-visible,.te summary:focus-visible{outline:2px solid var(--blue);outline-offset:3px}@media(max-width:1000px){.te-record-grid{grid-template-columns:1fr}}@media(max-width:700px){.te-source{flex-direction:column;align-items:stretch}}`;document.head.append(style);
    const $=id=>section.querySelector("#"+id);let sources=[],inputs=[],catalog=[],renderedSource=null,renderedExperiment,renderedRun,priorRuns=null,sourceSequence=0;
    const controller=createController({api,perform,uuid:()=>root.crypto.randomUUID(),changed:render});
    function message(value,error=false){const element=$(error?"te-error":"te-message");element.textContent=value;element.hidden=!value;if(error)element.focus();notify(value,error);}
    function render(state){$("te-error").hidden=!state.error;$("te-error").textContent=state.error;
      $("te-experiments").innerHTML=state.experiments.map(v=>`<button class="te-record" type="button" data-te-action="open-experiment" data-te-id="${esc(v.experiment_id||v.id)}" aria-current="${(state.experiment?.experiment_id||state.experiment?.id)===(v.experiment_id||v.id)}"><strong>${esc(v.symbol||"冻结样本")} · ${v.status==="REGISTERED"?"已登记":"待核对"}</strong><p>${num(v.cohort_count)} 条入场 · ${esc(v.recorded_at||"")}</p></button>`).join("")||'<p class="muted">还没有登记实验。</p>';
      $("te-runs").innerHTML=state.runs.map(v=>`<button class="te-record" type="button" data-te-action="open-run" data-te-id="${esc(v.exit_run_id||v.id)}" aria-current="${(state.run?.exit_run_id||state.run?.id)===(v.exit_run_id||v.id)}"><strong>${esc(v.symbol||state.experiments.find(e=>(e.experiment_id||e.id)===v.experiment_id)?.symbol||"出场研究")} · ${v.status==="COMPLETED"?"已保存":"待核对"}</strong><p>${esc(v.started_at||"")}</p></button>`).join("")||'<p class="muted">登记后需明确运行，才会生成结果。</p>';
      if(state.warnings.length)$("te-runs").innerHTML+=`<p class="notice warning">${esc(state.warnings.join("；"))}</p>`;
      if(renderedExperiment!==state.experiment||priorRuns!==state.runs){$("te-experiment").innerHTML=experimentHtml(state.experiment,state.runs);renderedExperiment=state.experiment;priorRuns=state.runs;}
      if(renderedRun!==state.run){$("te-result").innerHTML=resultHtml(state.run,state.experiments.find(e=>(e.experiment_id||e.id)===state.run?.experiment_id)||{});renderedRun=state.run;}
      if(renderedSource!==state.source){renderedSource=state.source;$("te-form").hidden=!state.source;if(state.source){const spec=defaultSpec(state.source.chart?.rows);$("te-form").reset();for(const key of Object.keys(SEGMENTS)){for(const edge of ["start","end"]){const field=$("te-"+key+"-"+edge);field.value=spec.split[key][edge+"_date"];field.min=state.source.chart.rows[0].date;field.max=state.source.chart.rows.at(-1).date;}}
        for(const [key]of fields)$("te-"+key).value=key==="fee_pct"?spec.costs.fee_rate*100:key==="slippage_bps"?spec.costs.slippage_bps:spec[key];
        $("te-source-summary").textContent=`${state.source.title||state.source.strategy_id} · ${state.source.input_summary?.symbol||state.source.chart?.symbol||""} · ${state.source.chart?.meta?.provider||state.source.input_summary?.source_id||"来源待核对"} · ${state.source.chart?.meta?.price_basis||"价格口径未记录"} · 原结果 ${state.source.run_id||state.source.id}`;}}
      for(const id of ["te-register-submit","te-run-submit"])if($(id))$(id).disabled=state.busy||Boolean(state.unknown);
      if(state.unknown)message("待核对的提交编号："+state.unknown.requestId+"。请保留编号并查看操作日志。");
    }
    async function openSource(id){const seq=++sourceSequence,selected=sources.find(v=>(v.run_id||v.id)===id);if(!selected)throw new Error("请刷新后选择一份原生结果。");const value=await api("terminal_runs/"+encodeURIComponent(id));if(seq!==sourceSequence)return;
      if((value.run_id||value.id)!==id)throw new Error("原结果身份不一致。");const blocker=sourceBlocker(value,catalog);if(blocker)throw new Error(blocker);if(!(value.result?.trades||[]).some(v=>v.side==="BUY"))throw new Error("原结果没有 BUY 样本，可使用独立结构查看。");defaultSpec(value.chart?.rows);controller.begin(value);$("te-source").value=id;section.scrollIntoView({block:"start"});$("te-form-title").focus();message("请核对日期、统一成本与规则。登记不会自动运行。");}
    async function replayStructure(id){if(!hash(id))throw new Error("请先选择冻结行情。");const value=await api("terminal_structure_replay/"+encodeURIComponent(id));if(value.available!==true||value.source!=="STRUCTURE_FROZEN"||value.input_id!==id||!validReplay(value))throw new Error("结构不可查看："+(value.reason||"冻结来源校验未通过。"));sendReplay(value);message("已在原图查看当前公式从冻结输入衍生的结构；标记仅在确认日后显示。");}
    async function replayRun(){const selected=controller.state.run,id=selected?.exit_run_id||selected?.id;if(selected?.status!=="COMPLETED"||selected?.integrity_status!=="PASS")throw new Error("研究结果未完成，不可复盘。");const value=await api("terminal_exit_replay/"+encodeURIComponent(id));if(id!==(controller.state.run?.exit_run_id||controller.state.run?.id))return;
      if(value.available!==true||value.source!=="EXIT_RESEARCH_FROZEN"||value.exit_run_id!==id||!validReplay(value)){if($("te-replay-status"))$("te-replay-status").textContent="不可复盘："+(value.reason||"冻结结果校验未通过。");return;}sendReplay(value);$("te-replay-status").textContent="已打开冻结结构与独立样本路径；请在原图选择样本查看三种阈值。";}
    section.addEventListener("click",async event=>{const target=event.target.closest("[data-te-action]");if(!target||target.disabled)return;try{const action=target.dataset.teAction;if(action==="refresh"){await controller.refresh();message("已读取保存记录，未重新运行。");}if(action==="new")await openSource($("te-source").value);if(action==="revise")await openSource(target.dataset.teId);if(action==="structure")await replayStructure($("te-input").value);if(action==="open-experiment"){await controller.openExperiment(target.dataset.teId);$("te-experiment-title")?.focus();}if(action==="open-run"){await controller.openRun(target.dataset.teId);$("te-result-title")?.focus();}if(action==="run"){const value=await controller.runExperiment();if(value)message("已读取本次出场研究结果。");}if(action==="replay")await replayRun();}catch(e){message(e.message||"操作未完成。",true);}});
    section.addEventListener("submit",async event=>{if(event.target.id!=="te-form")return;event.preventDefault();if(!event.target.reportValidity())return;try{const spec={split:{},costs:{fee_rate:Number($("te-fee_pct").value)/100,slippage_bps:Number($("te-slippage_bps").value)}};for(const key of Object.keys(SEGMENTS))spec.split[key]={start_date:$("te-"+key+"-start").value,end_date:$("te-"+key+"-end").value};for(const [key]of fields)if(!["fee_pct","slippage_bps"].includes(key))spec[key]=Number($("te-"+key).value);const value=await controller.register(spec);if(value){message("实验配置已封存。核对后可明确运行一次。");$("te-experiment-title")?.focus();}else $("te-error").focus();}catch(e){message(e.message||"请核对表单。",true);}});
    render(controller.state);return {refresh:controller.refresh,openSource,replayStructure,setSources(records={}){sources=records.runs||[];inputs=records.inputs||[];catalog=records.catalog||[];const selected=$("te-source").value,selectedInput=$("te-input").value;
      $("te-source").innerHTML='<option value="">请选择已完成原生结果</option>'+sources.map(v=>{const blocker=sourceBlocker(v,catalog);return `<option value="${esc(v.run_id||v.id)}" ${blocker?"disabled":""}>${esc(v.title||v.strategy_id||"未完成结果")} · ${esc(v.input_summary?.symbol||"")}${blocker?" · 不可新建研究":""}</option>`;}).join("");if(sources.some(v=>(v.run_id||v.id)===selected))$("te-source").value=selected;
      $("te-input").innerHTML='<option value="">请选择冻结行情</option>'+inputs.map(v=>`<option value="${esc(v.input_id||v.id)}">${esc(v.symbol)} · ${esc(v.date_start)} 至 ${esc(v.date_end)}</option>`).join("");if(inputs.some(v=>(v.input_id||v.id)===selectedInput))$("te-input").value=selectedInput;}};
  }
  root.installTerminalExitResearchUI=install;
  if(typeof module==="object"&&module.exports)module.exports={RULES,SEGMENTS,sourceBlocker,defaultSpec,registerPayload,createController,specHtml,experimentHtml,outcomeHtml,resultHtml,install};
})(typeof window!=="undefined"?window:globalThis);
