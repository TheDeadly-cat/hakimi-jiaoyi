/* Explain verified saved-input rules without running a backtest or an order. */
(function (root) {
  "use strict";
  const esc = value => String(value ?? "").replace(/[&<>"']/g,c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const plain = value => value && typeof value === "object" && !Array.isArray(value);
  const number = value => typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("zh-CN",{maximumSignificantDigits:10}) : "未记录";
  function factorValue(value,unit) {
    if(Array.isArray(value))return value.map(item=>factorValue(item,unit)).join(" 至 ");
    if(typeof value!=="number"||!Number.isFinite(value))return "未记录";
    if(unit==="ratio")return number(value*100)+"%";
    return number(value)+({percent:"%",volume:" 股",rsi:" 点",oscillator_points:" 点",multiple:" 倍",multiplier:" 倍"}[unit]||"");
  }
  const condition = factor => factor.operator==="between_inclusive"
    ? `处于 ${factorValue(factor.threshold,factor.unit)}（含边界）`
    : `${factor.operator||""} ${factorValue(factor.threshold,factor.unit)}`;
  const valid = row => plain(row) && row.schema_version === "hakimi-terminal-strategy-diagnostic-v1"
    && /^[a-f0-9]{64}$/.test(row.diagnostic_id || "") && /^[a-f0-9]{64}$/.test(row.input_id || "")
    && typeof row.strategy_id === "string" && plain(row.strategy_params) && Array.isArray(row.factors);
  const clone=value=>JSON.parse(JSON.stringify(value)),hash=value=>typeof value==="string"&&/^[a-f0-9]{64}$/.test(value);
  const ordered=value=>Array.isArray(value)?value.map(ordered):plain(value)?Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])])):value;
  const equal=(a,b)=>a!==undefined&&b!==undefined&&JSON.stringify(ordered(a))===JSON.stringify(ordered(b));
  const params=value=>plain(value)&&Object.keys(value).length>0&&Object.values(value).every(v=>typeof v==="boolean"||(typeof v==="number"&&Number.isFinite(v)));
  const sources=value=>plain(value)&&["backtest_engine.py","strategy_signals.py","market_calendar.py","indicator_math.py"].every(k=>hash(value[k]))&&Object.values(value).every(hash);
  const matchable=row=>valid(row)&&row.status==="READY"&&row.decision_matches_factors===true&&hash(row.source_digest)&&hash(row.fingerprint)&&sources(row.engine_source_identity)&&plain(row.indicator_contract)&&params(row.strategy_params)&&typeof row.engine_id==="string"&&typeof row.symbol==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(row.cutoff_session||"");
  function matchesSavedResult(run,diagnostic) {
    const c=run?.configuration,i=run?.input_summary;
    return Boolean(matchable(diagnostic)&&run?.schema_version==="hakimi-terminal-run-v1"&&run.status==="COMPLETED"&&hash(run.id)&&run.run_id===run.id&&run.report_hash===run.id&&hash(run.task_id)&&Number.isSafeInteger(run.version)&&run.version>0
      &&plain(c)&&plain(i)&&run.engine_id===diagnostic.engine_id&&c.engine_id===diagnostic.engine_id&&run.strategy_id===diagnostic.strategy_id
      &&[c.input_id,i.id,i.input_id].every(id=>id===diagnostic.input_id)&&i.source_digest===diagnostic.source_digest&&i.digest===diagnostic.source_digest&&i.symbol===diagnostic.symbol
      &&i.date_end===diagnostic.cutoff_session&&params(c.strategy_params)&&equal(c.strategy_params,diagnostic.strategy_params)&&c.fingerprint===diagnostic.fingerprint
      &&equal(c.engine_source_identity,diagnostic.engine_source_identity)&&equal(c.indicator_contract,diagnostic.indicator_contract));
  }
  function savedResultTerms(run) {
    const c=run.configuration||{},risk=c.risk||{},cost=c.costs||{},currency=run.input_summary?.meta?.currency;
    return `<p class="candidate-saved-terms">原报告本金 ${esc(number(c.initial_cash))}${currency?" "+esc(currency):"（币种未记录）"} · 执行仓位 ${esc(factorValue(risk.position_pct,"percent"))} · 执行止损 ${esc(factorValue(risk.stop_loss_pct,"percent"))} · 执行止盈 ${esc(factorValue(risk.take_profit_pct,"percent"))} · 手续费 ${esc(factorValue(cost.fee_rate,"ratio"))} · 滑点 ${esc(number(cost.slippage_bps))} 基点</p>`;
  }
  function createSavedResultController({api,onOpenSaved,onChoose,getScope=()=>"",changed=()=>{}}) {
    const state={diagnostic:null,status:"IDLE",matches:[],warnings:[],error:"",busy:false,runId:null};let sequence=0,scope=null;
    const emit=()=>changed(state),current=seq=>seq===sequence&&scope===getScope();
    function invalidate(){sequence++;scope=null;Object.assign(state,{diagnostic:null,status:"IDLE",matches:[],warnings:[],error:"",busy:false,runId:null});emit();}
    async function open(id,seq=sequence) {
      const selected=state.matches.find(row=>row.id===id);if(!selected||!current(seq)||state.busy)return;
      state.status="READING";state.busy=true;state.runId=id;state.error="";emit();
      try{const run=await api("terminal_runs/"+encodeURIComponent(id));if(!current(seq))return;
        if(!matchesSavedResult(run,state.diagnostic)||run.id!==id||run.task_id!==selected.task_id||run.version!==selected.version||!equal(run.configuration,selected.configuration)||!equal(run.input_summary,selected.input_summary))throw Error("这份结果与所选行情、规则或原列表身份不一致，未打开其他结果。");
        if(typeof onOpenSaved!=="function")throw Error("原结果入口尚未就绪，请稍后只读重试。");
        await onOpenSaved(clone(run),clone(state.diagnostic),{incompleteIndex:state.warnings.length>0,warnings:clone(state.warnings)});
        if(current(seq)){state.status="OPENED";emit();}
      }catch(error){if(current(seq)){state.status="DETAIL_ERROR";state.error=error?.info?.message||error.message||"原结果暂未读出";emit();}}
      finally{if(seq===sequence){state.busy=false;if(!current(seq))invalidate();else emit();}}
    }
    async function select(row) {
      if(state.busy&&state.diagnostic?.diagnostic_id===row?.diagnostic_id&&current(sequence))return;
      const seq=++sequence;scope=getScope();Object.assign(state,{diagnostic:clone(row),status:"LOOKING",matches:[],warnings:[],error:"",busy:true,runId:null});emit();
      try{if(!matchable(row))throw Error("候选缺少完整输入、参数或源码身份，请重新读取候选后核对。");const result=await api("terminal_runs");if(!current(seq))return;
        if(!Array.isArray(result?.items)||!Array.isArray(result.warnings)||result.new_economic_runs!==0)throw Error("结果索引的读取状态不完整，不能据此判断是否已有研究。");
        const matched=new Map();for(const item of result.items){if(!matchesSavedResult(item,row))continue;if(matched.has(item.id)&&!equal(matched.get(item.id),item))throw Error("同一报告编号出现不同记录，需先核对索引。");matched.set(item.id,item);}
        state.matches=[...matched.values()].sort((a,b)=>String(b.started_at||"").localeCompare(String(a.started_at||""))||a.id.localeCompare(b.id));state.warnings=clone(result.warnings);
        state.status=state.matches.length?"CHOICES":"EMPTY";state.busy=false;emit();
        if(state.matches.length===1&&!state.warnings.length)await open(state.matches[0].id,seq);
      }catch(error){if(current(seq)){state.status="INDEX_ERROR";state.error=error?.info?.message||error.message||"已保存索引暂未读出";emit();}}
      finally{if(seq===sequence&&state.status!=="READING"){state.busy=false;if(!current(seq))invalidate();else emit();}}
    }
    async function newDraft(){if(state.status!=="EMPTY"||state.busy||!current(sequence))return;const selected=clone(state.diagnostic);await onChoose(selected);invalidate();}
    return {state,select,open,newDraft,invalidate};
  }
  function factorRows(row) {
    return row.factors.map(factor => {
      const state = factor.passed === true ? "满足" : factor.passed === false ? "未满足" : "资料不足";
      return `<tr><th scope="row">${esc(factor.label || factor.key)}</th><td>${esc(factorValue(factor.value,factor.unit))}</td><td>${esc(condition(factor))}</td><td>${esc(state)}${factor.applies_to_position === false ? "（另一持仓情景）" : ""}</td></tr>`;
    }).join("");
  }
  function renderDiagnostic(row) {
    if (!valid(row)) throw Error("策略解释的保存行情或规则身份不完整。");
    const ready = row.status === "READY" && row.decision_matches_factors === true;
    const holding = row.position_context?.has_position === true;
    const action = row.signal?.action;
    const result = !ready ? `资料或规则仍需核对${row.missing_rows > 0 ? `，还缺 ${row.missing_rows} 根完整日线` : ""}`
      : action === "BUY" ? "截至所选日，满足开仓条件" : action === "EXIT" ? "截至所选日，满足退出条件" : "截至所选日，暂未触发动作";
    return `<article class="candidate-card" data-candidate-id="${esc(row.diagnostic_id)}">
      <h4>${esc(row.name || row.strategy_id)}</h4><p class="candidate-result">${esc(result)}</p>
      <p class="section-note">${esc(row.symbol)} · 数据截止 ${esc(row.cutoff_session)} · ${holding ? "已有持仓的诊断情景" : "未持仓的诊断情景"}</p>
      ${row.selection_note ? `<p>${esc(row.selection_note)}</p>` : ""}
      <p>${row.factors.filter(factor=>factor.applies_to_position!==false).slice(0,2).map(factor=>`${esc(factor.label||factor.key)} ${esc(factorValue(factor.value,factor.unit))} ${esc(condition(factor))}：${factor.passed===true ? "满足" : factor.passed===false ? "未满足" : "资料不足"}`).join("；")}</p>
      <p>完整日线 ${esc(row.complete_rows)} 根，研究至少需要 ${esc(row.required_rows)} 根（${esc(row.warmup_rows)} 根准备指标，再留 2 根用于信号与下一根成交）。历史收益优劣尚未评估。</p>
      <details><summary>为什么：查看因子值与触发条件</summary>
        <div class="candidate-table"><table><thead><tr><th>因子</th><th>当前值</th><th>判定条件</th><th>规则判断</th></tr></thead><tbody>${factorRows(row)}</tbody></table></div>
        <p class="section-note">判断使用引擎原始精度；表格数值仅为显示格式。所选数据是封存历史行情，不能当作实时下单报价。</p>
        <details><summary>参数与原始诊断依据</summary><pre>${esc(JSON.stringify({parameters:row.strategy_params,signal:row.signal,factors:row.factors,freshness:row.freshness,blockers:row.blockers,input_id:row.input_id,engine_id:row.engine_id,fingerprint:row.fingerprint,diagnostic_id:row.diagnostic_id},null,2))}</pre></details>
      </details><button type="button" class="btn" data-candidate-choose="${esc(row.diagnostic_id)}" ${ready ? "" : "disabled"}>选择并查看已有研究</button>
      <p class="section-note">先只读查找行情与规则相同的完成研究，不重复保存或运行。</p></article>`;
  }
  function install({host,api,onChoose,onOpenSaved,onAcquireData,getDraft,notify=()=>{}}) {
    if (!host || typeof api !== "function" || typeof onChoose !== "function") throw Error("candidate_ui_dependencies_required");
    const doc=host.ownerDocument,view=doc.createElement("section");
    view.className="panel section-gap terminal-candidates";view.setAttribute("aria-label","策略候选与因子解释");
    view.innerHTML=`<style>.terminal-candidates .candidate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:16px}.terminal-candidates .candidate-card{padding:18px;border:1px solid var(--line,#3b475b);border-radius:10px;min-width:0}.terminal-candidates h3,.terminal-candidates h4{margin:0 0 10px}.terminal-candidates .candidate-result{font-weight:600}.terminal-candidates details{margin:12px 0}.terminal-candidates summary{cursor:pointer;min-height:32px}.terminal-candidates .candidate-table{overflow:auto}.terminal-candidates table{width:100%;border-collapse:collapse;font-size:.85em}.terminal-candidates th,.terminal-candidates td{padding:8px;text-align:left;border-bottom:1px solid var(--line,#3b475b)}.terminal-candidates pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:350px;overflow:auto}.terminal-candidates button{min-height:40px}.terminal-candidates .candidate-message{overflow-wrap:anywhere}.terminal-candidates .candidate-group{margin-top:24px}.terminal-candidates [hidden]{display:none!important}.terminal-candidates select{max-width:100%}</style>
      <div class="panel-head"><h2>选策略，先看理由</h2></div><div class="panel-body">
      <p>根据已保存行情查看九个原策略的条件。满足条件的候选集中展示；暂未触发时可以等待，不会强行推荐买入。</p>
      <div class="form-grid"><label class="field">选择已保存行情<select data-candidate="input"><option value="">先选择已保存行情</option></select></label>
      <label class="field">诊断情景<select data-candidate="position"><option value="flat">未持仓，查看开仓条件</option><option value="holding">已有持仓，查看退出条件</option></select></label></div>
      <div class="actions"><button class="btn primary" type="button" data-candidate="read">查看策略候选</button><button class="btn" type="button" data-candidate="draft">解释当前表单参数</button><button class="btn" type="button" data-candidate="acquire">获取或更新股票日线</button></div>
      <p class="section-note">这里核对所选截止日的指标和规则，不运行回测或订单。策略收益表现需要单独查看已保存结果；当前原策略按只做多规则解释。</p>
      <p class="candidate-message" data-candidate="message" role="status" aria-live="polite"></p><p data-candidate="error" role="alert" hidden></p><div data-candidate="saved" aria-live="polite"></div><div data-candidate="results"></div></div>`;
    host.append(view);
    const el=key=>view.querySelector(`[data-candidate="${key}"]`),state={inputs:[],rows:[],busy:false},clone=value=>JSON.parse(JSON.stringify(value));
    let sequence=0;
    const saved=createSavedResultController({api,onChoose,onOpenSaved,getScope:()=>{let draft;try{draft=getDraft?.();}catch(_){draft={invalid:true};}return JSON.stringify(ordered({sequence,input:el("input").value,position:el("position").value,draft}));},changed:renderSaved});
    function renderSaved(s) {
      const target=el("saved");if(s.status==="IDLE"){target.replaceChildren();return;}
      const note='<p class="section-note">这里只匹配封存行情、历史截止日、规则及全部参数。费用、执行风险和本金未纳入候选匹配，须查看各报告实际设置；诊断情景不等于报告中的实际持仓。不按收益排名。</p>';
      const warning=s.warnings.length?`<p class="notice warning">部分记录未读出（${s.warnings.length} 项）；这里只列出目前可核验的匹配结果，不能据此判断全部历史记录。</p>`:"";
      const error=s.error?`<p role="alert">${esc(s.error)}。未保存任务、运行回测或提交订单。</p>`:"";
      const button=(label,action,id="")=>`<button class="btn" type="button" data-candidate-saved="${action}" data-run-id="${esc(id)}" ${s.busy?"disabled":""}>${label}</button>`;
      const rows=s.matches.map(run=>`<article class="candidate-card"><h4>${esc(run.title||run.strategy_id)} · 版本 ${esc(run.version)}</h4><p>保存时间 ${esc(run.started_at||"未记录")} · 历史截至 ${esc(run.input_summary.date_end)}</p>${savedResultTerms(run)}${button("打开这份已保存结果","open",run.id)}<details><summary>查看原报告与任务编号</summary><p>${esc(run.id)}<br>${esc(run.task_id)}</p></details></article>`).join("");
      target.innerHTML=`<section class="notice section-gap"><h3>${esc(s.diagnostic?.name||"所选策略")} · 已保存研究</h3>${note}${warning}${error}${s.status==="LOOKING"?'<p>正在只读查找已保存结果……</p>':s.status==="READING"?'<p>正在重新核对并读取这份原结果……</p>':s.status==="INDEX_ERROR"?'<p>索引未读完整；不能据此说没有做过研究。请重新读取。</p>'+button("重新查找已保存研究","search"):s.status==="DETAIL_ERROR"?button("重新读取这份结果","open",s.runId):s.status==="EMPTY"?'<p>未找到可核验的、行情与规则相同的已完成研究。未完成或待核对的原记录不算完成结果，也不会被重跑。</p>'+button("核对设置并新建任务草稿","new"):s.status==="OPENED"?'<p>已只读打开原报告，没有重复保存或运行。</p>':`<p>找到 ${s.matches.length} 份可核验匹配，按保存时间显示，请明确选择。</p><div class="candidate-grid">${rows}</div>`}</section>`;
    }
    function clear(message="") {sequence++;saved.invalidate();state.rows=[];el("results").replaceChildren();el("message").textContent=message;}
    function invalidateDraft(){clear("表单行情或参数已改变，请重新查看候选或解释当前表单参数。");controls();}
    function controls() {el("read").disabled=state.busy || !el("input").value;el("draft").disabled=state.busy || typeof getDraft!=="function";view.setAttribute("aria-busy",String(state.busy));}
    function setSources({inputs=[]}={}) {
      const selected=el("input").value;state.inputs=inputs.filter(row=>/^[a-f0-9]{64}$/.test(row.input_id || row.id || ""));
      el("input").innerHTML='<option value="">先选择已保存行情</option>'+state.inputs.map(row=>`<option value="${esc(row.input_id||row.id)}">${esc(row.symbol)} · ${esc(row.date_start||"日期未记录")} 至 ${esc(row.date_end||"日期未记录")} · ${esc(row.row_count ?? "?")} 日</option>`).join("");
      if(state.inputs.some(row=>(row.input_id||row.id)===selected))el("input").value=selected;else if(selected)clear("原选择已不在可读行情列表，请重新核对。");controls();
    }
    function selectInput(id) {if(!state.inputs.some(row=>(row.input_id||row.id)===id))return false;el("input").value=id;clear("行情已选入。点击查看策略候选，核对这份行情的条件。");controls();return true;}
    async function read(draft=false) {
      if(state.busy)return;el("error").hidden=true;
      let payload;
      try {
        const current=draft ? getDraft() : {input_id:el("input").value};
        if(!current?.input_id || !state.inputs.some(row=>(row.input_id||row.id)===current.input_id))throw Error("请先选择一份已保存且可读取的行情。");
        payload={input_id:current.input_id,position_context:{has_position:el("position").value==="holding"}};
        if(draft){if(!current.strategy_id || !plain(current.strategy_params))throw Error("请先在下方填写完整的策略参数。");Object.assign(payload,{strategy_id:current.strategy_id,strategy_params:clone(current.strategy_params)});}
      } catch(error) {el("error").textContent=error.message;el("error").hidden=false;return;}
      clear();const request=sequence;state.busy=true;controls();el("message").textContent="正在核对已保存行情与实际规则，不会运行回测。";
      try {
        const result=await api("terminal_strategy_candidates/"+encodeURIComponent(JSON.stringify(payload)));
        if(request!==sequence)return;
        if(result?.schema_version!=="hakimi-terminal-strategy-candidates-v1" || !Array.isArray(result.groups))throw Error("策略候选响应格式无法核对。");
        const rows=result.groups.flatMap(group=>group.items||[]);
        if(!rows.length || rows.some(row=>!valid(row)||row.input_id!==payload.input_id||row.position_context?.has_position!==payload.position_context.has_position
          ||(draft && row.strategy_id!==payload.strategy_id)))throw Error("策略候选与所选行情或诊断情景不一致。");
        state.rows=rows;el("input").value=payload.input_id;
        el("results").innerHTML=result.groups.filter(group=>group.items?.length).map(group=>`<section class="candidate-group"><h3>${esc(group.label)} · ${group.items.length}</h3><div class="candidate-grid">${group.items.map(renderDiagnostic).join("")}</div></section>`).join("");
        const matches=rows.filter(row=>row.group==="ENTRY_MATCH" && row.status==="READY").length;
        el("message").textContent=`已核对 ${rows.length} 个策略${payload.position_context.has_position ? "的退出条件" : `，其中 ${matches} 个满足所选日的开仓规则`}。同组按固定规则目录展示，不按历史收益排名。`;
      } catch(error) {if(request===sequence){el("error").textContent=error?.info?.message||error.message||"策略解释暂未读出，可重新读取。";el("error").hidden=false;el("message").textContent="没有运行回测或提交订单。";}}
      finally {state.busy=false;controls();}
    }
    view.addEventListener("change",event=>{if([el("input"),el("position")].includes(event.target)){clear("选择已改变，请重新查看条件。");controls();}});
    view.addEventListener("click",async event=>{
      const button=event.target.closest("button");if(!button||button.disabled)return;
      if(button===el("read"))return read();if(button===el("draft"))return read(true);
      if(button===el("acquire"))return onAcquireData?.();
      if(button.dataset.candidateSaved){const action=button.dataset.candidateSaved;try{if(action==="open")return await saved.open(button.dataset.runId);if(action==="search")return await saved.select(saved.state.diagnostic);if(action==="new"){await saved.newDraft();el("message").textContent="已带入新任务草稿；请核对参数和风险后明确保存，尚未运行。";notify(el("message").textContent);}}catch(error){el("error").textContent=error.message;el("error").hidden=false;}return;}
      const row=state.rows.find(item=>item.diagnostic_id===button.dataset.candidateChoose);
      if(!row || row.status!=="READY" || row.decision_matches_factors!==true)return;
      try{const pending=saved.select(clone(row));el("saved").scrollIntoView({block:"nearest"});await pending;}
      catch(error){el("error").textContent=error.message;el("error").hidden=false;}
    });
    controls();
    return {setSources,selectInput,read,invalidateDraft,savedController:saved,element:view,reveal:()=>view.scrollIntoView({block:"start"})};
  }
  root.installTerminalStrategyCandidatesUI=install;
  const exports={install,renderDiagnostic,factorRows,factorValue,valid,matchesSavedResult,savedResultTerms,createSavedResultController};root.HakimiTerminalStrategyCandidates=exports;
  if(typeof module==="object"&&module.exports)module.exports=exports;
})(typeof globalThis!=="undefined"?globalThis:this);
