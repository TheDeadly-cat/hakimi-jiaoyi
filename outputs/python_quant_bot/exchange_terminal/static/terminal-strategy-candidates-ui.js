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
      </details><button type="button" class="btn" data-candidate-choose="${esc(row.diagnostic_id)}" ${ready ? "" : "disabled"}>选择此策略并核对设置</button>
      <p class="section-note">选择只带入规则和参数；保存、回测及订单确认分别进行。</p></article>`;
  }
  function install({host,api,onChoose,onAcquireData,getDraft,notify=()=>{}}) {
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
      <p class="candidate-message" data-candidate="message" role="status" aria-live="polite"></p><p data-candidate="error" role="alert" hidden></p><div data-candidate="results"></div></div>`;
    host.append(view);
    const el=key=>view.querySelector(`[data-candidate="${key}"]`),state={inputs:[],rows:[],busy:false},clone=value=>JSON.parse(JSON.stringify(value));
    let sequence=0;
    function clear(message="") {sequence++;state.rows=[];el("results").replaceChildren();el("message").textContent=message;}
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
      const row=state.rows.find(item=>item.diagnostic_id===button.dataset.candidateChoose);
      if(!row || row.status!=="READY" || row.decision_matches_factors!==true)return;
      try{await onChoose(clone(row));el("message").textContent=`已选择 ${row.name||row.strategy_id}，请在任务表单核对参数和风险，再明确保存。没有自动回测或下单。`;notify(el("message").textContent);}
      catch(error){el("error").textContent=error.message;el("error").hidden=false;}
    });
    controls();
    return {setSources,selectInput,read,element:view,reveal:()=>view.scrollIntoView({block:"start"})};
  }
  root.installTerminalStrategyCandidatesUI=install;
  if(typeof module==="object"&&module.exports)module.exports={install,renderDiagnostic,factorRows,factorValue,valid};
})(typeof globalThis!=="undefined"?globalThis:this);
