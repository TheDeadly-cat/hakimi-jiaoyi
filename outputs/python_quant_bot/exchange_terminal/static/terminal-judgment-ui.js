/* Local judgment journal. This module defines its API before any DOM access. */
(function (root) {
  "use strict";
  const DIRECTIONS = {LONG:"看多", SHORT:"看空", WAIT:"等待"};
  const EVENTS = {OBSERVATION:"追加观察", TRIGGERED:"记录触发", INVALIDATED:"记录失效", USER_ACTION:"用户报告动作"};
  const BINDINGS = {terminal_input:"冻结行情", terminal_task:"策略任务版本", terminal_run:"已保存回测结果", core_run:"股票研究结果"};
  const hash = (value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  const plain = (value) => Boolean(value && typeof value === "object" && !Array.isArray(value));
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const copy = (value) => JSON.parse(JSON.stringify(value));
  const text = (value) => typeof value === "string" ? value.trim() : "";
  const date = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value)) && !Number.isNaN(Date.parse(value + "T00:00:00Z"))
    && new Date(value + "T00:00:00Z").toISOString().slice(0,10) === value;
  const summary = (input = {}) => {
    const meta = input.meta || {};
    return [input.source_id || meta.provider || meta.source || "来源待核对", meta.session || "时段未记录",
      meta.price_basis || "价格口径未记录"].join(" · ");
  };
  const judgmentId = (value) => value?.judgment_id || value?.id || "";
  function checkedText(value, label, max, required = true) {
    const result = text(value);
    if ((required && !result) || result.length > max || result.includes("\0")) throw new Error(`${label}${required ? "不能为空，且" : ""}最多 ${max} 字。`);
    return result;
  }
  function createPayload(context, fields, requestId) {
    if (!plain(context) || !hash(context.input_id) || !plain(context.binding) || !Object.hasOwn(BINDINGS,context.binding.kind)
      || !text(context.binding.id)) throw new Error("请先选择一份已核验的冻结行情、任务或结果。");
    if (!Object.hasOwn(DIRECTIONS, fields.direction)) throw new Error("请选择判断方向。");
    if (!date(fields.as_of)) throw new Error("请填写有效的判断数据日期。");
    if ((context.input?.date_start && fields.as_of < context.input.date_start)
      || (context.input?.date_end && fields.as_of > context.input.date_end)) throw new Error("数据截止日必须位于这份冻结行情的覆盖范围内。");
    const counters = Array.isArray(fields.counter_evidence) ? fields.counter_evidence : String(fields.counter_evidence || "").split(/\r?\n/).map(text).filter(Boolean);
    if (counters.length > 8) throw new Error("反证最多 8 条，每行填写一条。");
    return {client_request_id:requestId, input_id:context.input_id,
      binding:{kind:context.binding.kind,id:context.binding.id}, direction:fields.direction, as_of:fields.as_of,
      thesis:checkedText(fields.thesis,"观点",2000),
      trigger_condition:checkedText(fields.trigger_condition,"触发条件",1000),
      invalidation_condition:checkedText(fields.invalidation_condition,"失效条件",1000),
      counter_evidence:counters.map((item) => checkedText(item,"反证",500))};
  }
  function eventPayload(detail, fields, requestId) {
    if (detail?.status !== "RECORDED" || detail?.integrity_status !== "PASS" || !hash(judgmentId(detail))) throw new Error("判断记录尚未通过校验，暂不能追加。");
    if (!Object.hasOwn(EVENTS, fields.event_type)) throw new Error("请选择追加记录类型。");
    const lastDate = detail.events?.at(-1)?.as_of || detail.as_of;
    if (!date(fields.as_of) || fields.as_of < lastDate) throw new Error("事件日期不能早于原判断或最近一条观察日期。");
    return {client_request_id:requestId,judgment_id:judgmentId(detail),expected_head:detail.head ?? null,
      event_type:fields.event_type,as_of:fields.as_of,note:checkedText(fields.note,"记录内容",2000)};
  }
  function createController({api, perform, uuid, changed = () => {}}) {
    const state = {items:[],warnings:[],selectedId:"",detail:null,context:null,error:"",loading:false,
      busy:false,unknown:false,unknownRequest:null,unknownAction:null,draftRequest:null,eventRequest:null};
    let listSequence = 0, detailSequence = 0;
    const emit = () => changed(state);
    async function open(id) {
      const sequence = ++detailSequence;
      state.selectedId = id; state.detail = null; state.error = ""; emit();
      try {
        const value = await api("terminal_judgments/" + encodeURIComponent(id));
        if (sequence !== detailSequence) return;
        if (judgmentId(value) !== id) throw new Error("返回记录与所选判断身份不一致。");
        state.detail = value; state.eventRequest = uuid();
        if (state.unknown && value.status === "RECORDED" && value.integrity_status === "PASS" && (value.client_request_id === state.unknownRequest
          || (value.events || []).some((event) => event.client_request_id === state.unknownRequest))) {
          if (state.unknownAction === "terminal_save_judgment") state.context = null;
          state.unknown = false; state.unknownRequest = null; state.unknownAction = null; state.error = "";
        }
        emit(); return value;
      } catch (error) {
        if (sequence !== detailSequence) return;
        state.detail = {id,judgment_id:id,status:"UNKNOWN",integrity_status:"UNKNOWN",events:[],reason:error.message || "记录读取失败"};
        state.error = "读取失败；已保留选择，未补算或重建记录。"; emit();
      }
    }
    async function refresh() {
      const sequence = ++listSequence; state.loading = true; state.error = ""; emit();
      try {
        const value = await api("terminal_judgments");
        if (sequence !== listSequence) return;
        state.items = Array.isArray(value.items) ? value.items : [];
        state.warnings = value.warnings || [];
        const recovered = state.unknownAction === "terminal_save_judgment"
          ? state.items.find((item) => item.client_request_id === state.unknownRequest && item.status === "RECORDED" && item.integrity_status === "PASS") : null;
        if (recovered) await open(judgmentId(recovered));
        else if (state.selectedId) await open(state.selectedId);
      } catch (error) {
        if (sequence === listSequence) state.error = error.message || "判断列表读取失败。";
      } finally {
        if (sequence === listSequence) { state.loading = false; emit(); }
      }
    }
    function begin(context) {
      if (state.busy) throw new Error("本次保存尚未完成，请等待结果。");
      state.context = copy(context); state.draftRequest = uuid(); state.error = "";
      // An uncertain write stays visible until the user starts a new, explicit draft.
      state.unknown = false; state.unknownRequest = null; state.unknownAction = null; emit();
    }
    async function mutate(action, payload, button) {
      if (state.busy || state.unknown) throw new Error("上次提交仍待核对，请先查看记录和操作日志。");
      state.busy = true; state.error = ""; emit();
      try {
        let accepted = null;
        // This controller owns button state. Passing its already-disabled button
        // to the shared job helper would make that helper skip the request.
        const result = await perform(action,payload,{onSuccess:(value) => { accepted = value; }});
        const value = accepted || result;
        if (!plain(value) || !hash(judgmentId(value)) || value.status !== "RECORDED" || value.integrity_status !== "PASS") {
          state.unknown = true; state.unknownRequest = payload.client_request_id; state.unknownAction = action;
          state.error = "提交结果尚未确认。请刷新判断列表并查看设置与日志；不要重复提交。";
          return null;
        }
        state.selectedId = judgmentId(value); state.detail = value; state.eventRequest = uuid();
        if (action === "terminal_save_judgment") state.context = null;
        await refresh(); return value;
      } catch (error) {
        state.unknown = true; state.unknownRequest = payload.client_request_id; state.unknownAction = action;
        state.error = (error.message || "保存结果未确认。") + " 请刷新记录并核对操作日志，不自动重试。";
        return null;
      } finally { state.busy = false; emit(); }
    }
    return {state,open,refresh,begin,
      save:(fields,button) => mutate("terminal_save_judgment",createPayload(state.context,fields,state.draftRequest),button),
      append:(fields,button) => mutate("terminal_append_judgment_event",eventPayload(state.detail,fields,state.eventRequest),button)};
  }
  function sourcesFrom({inputs = [],tasks = [],runs = []} = {}) {
    const rows = [];
    for (const input of inputs) rows.push({key:"terminal_input:" + (input.input_id || input.id),kind:"terminal_input",id:input.input_id || input.id,
      input_id:input.input_id || input.id,input,label:`${input.symbol || "行情"} · 冻结行情 · ${input.date_end || "日期待核对"}`});
    for (const task of tasks) rows.push({key:"terminal_task:" + (task.task_id || task.id),kind:"terminal_task",id:task.task_id || task.id,
      input_id:task.input_id,input:task.input_summary,label:`${task.title || task.name || task.strategy_id} · 任务版本 ${task.version}`});
    for (const run of runs.filter((row) => row.status === "COMPLETED")) rows.push({key:"terminal_run:" + (run.run_id || run.id),kind:"terminal_run",id:run.run_id || run.id,
      input_id:run.configuration?.input_id || run.input_summary?.input_id || run.input_summary?.id,input:run.input_summary,
      label:`${run.title || run.strategy_id} · 回测结果版本 ${run.version}`});
    return rows.filter((row) => hash(row.input_id) && text(row.id));
  }
  function renderTimeline(events) {
    if (!Array.isArray(events) || !events.length) return '<p class="muted">尚未追加观察。原判断已封存，可继续记录后续发生的事情。</p>';
    return '<ol class="tj-timeline">' + events.map((event) => `<li><div class="tj-event-heading"><strong>${escape(EVENTS[event.event_type] || "记录")}</strong><span>${escape(event.as_of || "日期未记录")}</span></div>
      ${event.event_type === "USER_ACTION" ? '<p class="tj-label">用户报告 · 未核验成交，不代表系统订单</p>' : '<p class="tj-label">用户补记 · 不会自动改变策略或成交</p>'}
      <p class="tj-prose">${escape(event.note)}</p><small class="muted">写入时间 ${escape(event.created_at || event.recorded_at || "未记录")}</small></li>`).join("") + "</ol>";
  }
  function indicatorHtml(snapshot) {
    if (!plain(snapshot)) return '<p class="muted">此记录没有可核验的指标快照，不用当前值补齐。</p>';
    const values = snapshot.values || {};
    const number = (value) => typeof value === "number" && Number.isFinite(value)
      ? value.toLocaleString("zh-CN",{maximumFractionDigits:6}) : "不足／缺失";
    const rows = [["SMA",values.sma],["EMA",values.ema],["布林上轨",values.bollinger?.upper],
      ["布林中轨",values.bollinger?.mid],["布林下轨",values.bollinger?.lower],["MACD",values.macd?.line],
      ["信号线",values.macd?.signal],["MACD 柱",values.macd?.hist],["RSI",values.rsi],["动量",values.momentum],["ATR",values.atr]];
    return `<p class="section-note">保存时独立计算的参考值 · 截止 ${escape(snapshot.bar_date || "未记录")} · ${escape(snapshot.contract?.version || "公式版本未记录")}。不冒充旧回测的原始指标。</p>
      <dl class="tj-indicators">${rows.map(([label,value]) => `<div><dt>${label}</dt><dd>${number(value)}</dd></div>`).join("")}</dl>
      <details><summary>参数、公式版本与计算来源</summary><pre class="code-detail">${escape(JSON.stringify({params:snapshot.params,contract:snapshot.contract,source_sha256:snapshot.source_sha256,input_id:snapshot.input_id},null,2))}</pre></details>`;
  }
  function aiTimingHtml(evidence, asOf) {
    const generated = evidence?.generated_at;
    let timestamp = typeof generated === "number" && Number.isSafeInteger(generated) ? generated : NaN;
    if (typeof generated === "string" && date(generated.slice(0,10))
      && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(generated)) timestamp = Date.parse(generated);
    if (!Number.isFinite(timestamp) || timestamp < 0 || timestamp > 8640000000000000 || !date(asOf)) {
      return '<p class="notice warning">AI 参考生成日期未知，无法确认它在声明截止日之前已经存在；仅用于事后对照。</p>';
    }
    const generatedDay = new Date(timestamp).toISOString().slice(0,10);
    return `<p class="${generatedDay > asOf ? "notice warning" : "section-note"}">AI 参考生成日期（UTC）：${escape(generatedDay)}。${generatedDay > asOf
      ? "该 AI 参考生成于声明截止日之后，仅用于事后对照。"
      : "生成日期按 UTC 日历日期与声明截止日比较；不代表这条用户判断在当时已经写入。"}</p>`;
  }
  function detailHtml(detail) {
    if (!detail) return '<p class="muted">选择一条判断，查看当时依据和后续观察。</p>';
    if (detail.status !== "RECORDED" || detail.integrity_status !== "PASS") return `<div class="notice warning"><strong>记录待核对 · 不可复盘</strong><p>${escape(detail.reason || "缺少完整来源或记录校验未通过。")}</p><p>原记录保持原样，不使用当前行情补齐。</p></div>`;
    const input = detail.input_summary || {}, config = detail.task_configuration || {};
    const evidence = config.ai_evidence;
    const run = detail.run_summary, lastEventDate = detail.events?.at(-1)?.as_of || detail.as_of;
    return `<div class="tj-detail-heading"><h3 tabindex="-1" id="tj-detail-title">${escape(DIRECTIONS[detail.direction] || detail.direction)} · ${escape(detail.symbol)} · ${escape(detail.as_of)}</h3>
      <span class="tj-label">用户判断 · 已记录</span></div>
      <p class="tj-prose"><strong>观点：</strong>${escape(detail.thesis)}</p>
      <dl class="kv"><dt>触发条件</dt><dd class="tj-prose">${escape(detail.trigger_condition)}</dd><dt>失效条件</dt><dd class="tj-prose">${escape(detail.invalidation_condition)}</dd>
      <dt>反证</dt><dd>${detail.counter_evidence?.length ? detail.counter_evidence.map(escape).join("<br>") : "未填写；不代表没有反证"}</dd>
      <dt>来源与口径</dt><dd>${escape(summary(input))}</dd><dt>声明的数据截止日</dt><dd>${escape(detail.as_of)} · 实际最后完整 K 线 ${escape(detail.indicator_snapshot?.bar_date || "未记录")}</dd>
      <dt>本判断使用的数据</dt><dd>${escape(detail.prefix_summary?.date_start || input.date_start || "起点未记录")} 至 ${escape(detail.prefix_summary?.date_end || detail.indicator_snapshot?.bar_date || "终点未记录")} · ${escape(detail.prefix_summary?.row_count ?? detail.prefix_row_count ?? "数量未记录")} 根</dd>
      <dt>冻结原输入覆盖</dt><dd>${escape(input.date_start || "起点未记录")} 至 ${escape(input.date_end || "终点未记录")} · ${escape(input.row_count ?? "数量未记录")} 根 · ${escape(detail.bar || "周期未记录")}</dd>
      <dt>绑定记录</dt><dd>${escape(BINDINGS[detail.binding?.kind] || "绑定类型未记录")}${detail.binding?.version != null ? " · 版本 " + escape(detail.binding.version) : ""} · ${escape(detail.binding?.engine_id || "不涉及策略引擎")}</dd>
      <dt>系统记录时间</dt><dd>${escape(detail.created_at || detail.recorded_at || "未记录")}<p class="hint">这是本次写入时间；历史截止日不表示判断在当时已经写入。</p></dd></dl>
      <div class="actions section-gap"><button class="btn small" type="button" data-tj-action="replay">在原图查看当时行情</button><button class="btn small" type="button" data-tj-action="reload-detail">刷新这条记录</button></div>
      <div id="tj-replay-status" class="section-note section-gap" role="status">复盘前重新核验原冻结输入；来源缺失或校验失败时不可复盘。</div>
      <details class="section-gap"><summary>当时指标与参数版本</summary>${indicatorHtml(detail.indicator_snapshot)}
      <pre class="code-detail">${escape(JSON.stringify({binding:detail.binding,task_configuration:config,input_id:detail.input_id},null,2))}</pre></details>
      ${evidence ? `<details class="section-gap"><summary>AI 参考 · 原任务保存的内容</summary><p class="section-note">AI 内容保留原来源，与上方用户判断分别记录。</p>${aiTimingHtml(evidence,detail.as_of)}<pre class="code-detail">${escape(JSON.stringify(evidence,null,2))}</pre></details>` : '<p class="section-note section-gap">AI 参考：此绑定记录未保存 AI 内容。</p>'}
      ${run ? `<details class="section-gap"><summary>已记录回测结果</summary><p class="section-note">这里只引用原回测记录。下方用户报告动作不会生成或修改成交。</p><pre class="code-detail">${escape(JSON.stringify(run,null,2))}</pre></details>` : '<p class="section-note">已记录成交：此判断未绑定回测结果。</p>'}
      <h4 class="section-gap">后续观察时间线</h4>${renderTimeline(detail.events)}
      <form id="tj-event-form" class="form-section"><h4>追加记录</h4><div class="form-grid">
      <div class="field"><label for="tj-event-type">记录类型</label><select id="tj-event-type">${Object.entries(EVENTS).map(([key,label]) => `<option value="${key}">${label}</option>`).join("")}</select></div>
      <div class="field"><label for="tj-event-date">事件日期</label><input id="tj-event-date" type="date" min="${escape(lastEventDate)}" value="${escape(lastEventDate)}" required></div>
      <div class="field span-2"><label for="tj-event-note">观察或动作说明</label><textarea id="tj-event-note" rows="3" maxlength="2000" required aria-describedby="tj-action-help"></textarea><span id="tj-action-help" class="hint">记录你观察到的事实；“用户报告动作”仅为个人补记，未核验成交。</span></div></div>
      <button class="btn primary" type="submit" id="tj-event-submit">保存追加记录</button></form>`;
  }
  function install({host,api,perform,notify = () => {},sendReplay,validReplay}) {
    if (!host || host.querySelector("#terminalJudgmentWorkspace")) return null;
    const document = host.ownerDocument;
    const section = document.createElement("section"); section.id = "terminalJudgmentWorkspace"; section.className = "panel section-gap tj";
    section.setAttribute("aria-label","判断与复盘记录");
    section.innerHTML = `<div class="panel-head"><div><h2>判断与复盘记录</h2><p class="section-note">留下当时观点、触发与失效条件，沿时间线核对后续变化。</p></div><button class="btn small" type="button" data-tj-action="refresh">刷新判断</button></div>
      <div class="panel-body"><div id="tj-message" class="notice" role="status" aria-live="polite" hidden></div><div id="tj-error" class="notice error" role="alert" tabindex="-1" hidden></div>
      <div class="tj-source-row"><div class="field"><label for="tj-source">从哪份冻结记录开始</label><select id="tj-source"><option value="">先冻结行情或选择已保存任务／结果</option></select></div><button class="btn" type="button" data-tj-action="new">新建用户判断</button></div>
      <form id="tj-create-form" class="form-section" hidden><h3 tabindex="-1" id="tj-create-title">记录当时判断</h3><div id="tj-bound-source" class="notice"></div><div class="form-grid section-gap">
      <div class="field"><label for="tj-direction">方向</label><select id="tj-direction">${Object.entries(DIRECTIONS).map(([key,label]) => `<option value="${key}">${label}</option>`).join("")}</select></div>
      <div class="field"><label for="tj-as-of">数据截止日</label><input id="tj-as-of" type="date" required aria-describedby="tj-date-help"><span class="hint" id="tj-date-help">可选冻结覆盖内的历史日期；指标与复盘仅用截至该日的数据。系统同时保存本次写入时间。</span></div>
      <div class="field span-2"><label for="tj-thesis">我的观点</label><textarea id="tj-thesis" rows="3" maxlength="2000" required></textarea></div>
      <div class="field"><label for="tj-trigger">什么情况算触发</label><textarea id="tj-trigger" rows="3" maxlength="1000" required></textarea></div>
      <div class="field"><label for="tj-invalidation">什么情况说明判断失效</label><textarea id="tj-invalidation" rows="3" maxlength="1000" required></textarea></div>
      <div class="field span-2"><label for="tj-counter">反证与不确定之处（可选，每行一条，最多 8 条，每条 500 字）</label><textarea id="tj-counter" rows="3" maxlength="4007"></textarea></div></div>
      <div class="actions"><button id="tj-create-submit" class="btn primary" type="submit">保存用户判断</button><button class="btn" type="button" data-tj-action="cancel">收起草稿</button></div></form>
      <div class="tj-record-grid section-gap"><div><h3>已保存判断</h3><div id="tj-list" aria-live="polite">正在读取判断记录…</div></div><div id="tj-detail"></div></div></div>`;
    const anchor = host.querySelector("#tq-runs")?.closest(".panel");
    if (anchor) anchor.after(section); else host.append(section);
    const style = document.createElement("style");
    style.textContent = `.tj{min-width:0}.tj [hidden]{display:none!important}.tj .panel-head p{margin:6px 0 0}.tj-source-row{display:flex;align-items:end;gap:12px;margin-top:14px}.tj-source-row .field{flex:1;min-width:0}.tj select,.tj textarea{width:100%;min-width:0}.tj textarea{resize:vertical;min-height:84px;line-height:1.6}.tj .btn{min-height:44px}.tj-record-grid{display:grid;grid-template-columns:minmax(220px,1fr) minmax(0,2fr);gap:24px}.tj-record{display:block;width:100%;padding:14px;text-align:left;margin:0 0 8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);color:var(--ink);overflow-wrap:anywhere}.tj-record[aria-current=true]{border-color:var(--blue);box-shadow:inset 3px 0 var(--blue)}.tj-record p{margin:6px 0;font-size:13px;line-height:1.5}.tj-label{font-size:12px;color:var(--muted)}.tj-prose{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}.tj .kv dd{overflow-wrap:anywhere}.tj-timeline{list-style:none;margin:10px 0;padding:0 0 0 16px;border-left:2px solid var(--line)}.tj-timeline li{padding:8px 0 18px}.tj-event-heading{display:flex;justify-content:space-between;gap:12px}.tj-indicators{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:12px}.tj-indicators dt{font-size:12px;color:var(--muted)}.tj-indicators dd{margin:4px 0;overflow-wrap:anywhere}.tj details{line-height:1.6}.tj summary{cursor:pointer}.tj .code-detail{max-height:320px;overflow:auto}.tj input:focus-visible,.tj select:focus-visible,.tj textarea:focus-visible,.tj button:focus-visible,.tj summary:focus-visible{outline:2px solid var(--blue);outline-offset:3px}@media(max-width:900px){.tj-record-grid{grid-template-columns:1fr}.tj-source-row{align-items:stretch;flex-direction:column}}`;
    document.head.append(style);
    const $ = (id) => section.querySelector("#" + id);
    let sources = [], renderedDetail, renderedContext = null, sourceSequence = 0;
    const controller = createController({api,perform,uuid:() => root.crypto.randomUUID(),changed:render});
    function message(value,error = false) {
      const target = $(error ? "tj-error" : "tj-message"); target.hidden = !value; target.textContent = value;
      if (error && value) target.focus();
      notify(value,error);
    }
    function render(state) {
      $("tj-error").hidden = !state.error; $("tj-error").textContent = state.error;
      $("tj-list").innerHTML = state.loading && !state.items.length ? '<p class="muted">正在读取判断记录…</p>' :
        state.items.length ? state.items.map((item) => {
          const input = sources.find((source) => source.input_id === item.input_id)?.input || item.input_summary || {};
          return `<button class="tj-record" type="button" data-tj-action="open" data-tj-id="${escape(judgmentId(item))}" aria-current="${judgmentId(item) === state.selectedId}">
            <strong>${escape(item.symbol || "标的未记录")} · ${escape(DIRECTIONS[item.direction] || "方向待核对")} · ${escape(item.as_of || "日期未记录")}</strong><p>${escape(item.thesis || item.reason || "记录待核对")}</p>
            <p>${escape(summary(input))}</p><small>${item.integrity_status === "PASS" ? `已记录 · ${escape(item.event_count ?? 0)} 条后续观察` : "校验待核对 · 不可复盘"} · ${escape(BINDINGS[item.binding?.kind] || "来源未记录")}</small><p class="tj-label">系统记录 ${escape(item.created_at || item.recorded_at || "时间未记录")}</p></button>`;
        }).join("") : '<p class="muted">还没有判断记录。可从上方选择冻结行情，或使用任务、结果旁的“记录判断”。</p>';
      if (state.warnings.length) $("tj-list").innerHTML += `<p class="notice warning">${escape(state.warnings.join("；"))}</p>`;
      if (renderedDetail !== state.detail) { $("tj-detail").innerHTML = detailHtml(state.detail); renderedDetail = state.detail; }
      if (renderedContext !== state.context) {
        renderedContext = state.context;
        $("tj-create-form").hidden = !state.context;
        if (state.context) {
          $("tj-create-form").reset(); $("tj-direction").value = "WAIT";
          $("tj-as-of").value = state.context.input?.date_end || "";
          $("tj-as-of").min = state.context.input?.date_start || ""; $("tj-as-of").max = state.context.input?.date_end || "";
          $("tj-bound-source").textContent = `${state.context.label || BINDINGS[state.context.binding.kind]} · ${summary(state.context.input)} · 数据 ${state.context.input?.date_start || "—"} 至 ${state.context.input?.date_end || "—"}。保存后原判断不会被追加观察覆盖。`;
        }
      }
      for (const id of ["tj-create-submit","tj-event-submit"]) if ($(id)) $(id).disabled = state.busy || state.unknown;
      if (state.unknownRequest) { $("tj-message").hidden = false; $("tj-message").textContent = "待核对的提交编号：" + state.unknownRequest + "。请保留此编号并查看操作记录。"; }
    }
    async function openSource(kind,id) {
      const selected = sources.find((row) => row.kind === kind && row.id === id);
      if (!selected) throw new Error("冻结来源已变化，请刷新任务与结果后重新选择。");
      const sequence = ++sourceSequence;
      const record = kind === "terminal_input" ? null : await api((kind === "terminal_task" ? "terminal_tasks/" : "terminal_runs/") + encodeURIComponent(id));
      if (record && kind === "terminal_run" && record.status !== "COMPLETED") throw new Error("该结果未完整保存，不能绑定判断。");
      const inputId = record?.configuration?.input_id || record?.input_id || selected.input_id;
      const input = await api("terminal_inputs/" + encodeURIComponent(inputId));
      if (sequence !== sourceSequence) return;
      controller.begin({input_id:inputId,input,binding:{kind,id},label:selected.label});
      $("tj-source").value = selected.key; section.scrollIntoView({block:"start"}); $("tj-create-title").focus();
      message("已选定冻结来源，请填写你的观点与可核对条件。");
    }
    async function replay() {
      const id = controller.state.selectedId, detail = controller.state.detail;
      if (!id || detail?.status !== "RECORDED" || detail?.integrity_status !== "PASS") throw new Error("记录未通过校验，不可复盘。");
      let result;
      try { result = await api("terminal_judgment_replay/" + encodeURIComponent(id)); }
      catch (error) { if (id === controller.state.selectedId) $("tj-replay-status").textContent = "不可复盘：" + (error.message || "冻结来源暂不可读取。"); return; }
      if (id !== controller.state.selectedId) return;
      if (result.available !== true || result.judgment_id !== id || !validReplay(result)) {
        $("tj-replay-status").textContent = "不可复盘：" + (result.reason || "冻结来源或身份校验未通过；未使用当前行情替代。");
        return;
      }
      sendReplay(result); $("tj-replay-status").textContent = result.source === "JUDGMENT_FROZEN_INPUT"
        ? "已打开当时冻结行情；此判断没有回测成交。" : "已打开当时冻结行情与原回测成交；用户报告动作不进入成交图。";
    }
    section.addEventListener("click",async (event) => {
      const target = event.target.closest("[data-tj-action]"); if (!target || target.disabled) return;
      try {
        const action = target.dataset.tjAction;
        if (action === "refresh") { await controller.refresh(); message("已重新读取保存的判断记录。"); }
        if (action === "open") { await controller.open(target.dataset.tjId); $("tj-detail-title")?.focus(); }
        if (action === "reload-detail") await controller.open(controller.state.selectedId);
        if (action === "new") {
          const selected = sources.find((row) => row.key === $("tj-source").value);
          if (!selected) throw new Error("请选择一份冻结来源。"); await openSource(selected.kind,selected.id);
        }
        if (action === "cancel") { $("tj-create-form").hidden = true; message("草稿已收起；原判断记录保留。"); }
        if (action === "replay") await replay();
      } catch (error) { message(error.message || "操作未完成。",true); }
    });
    section.addEventListener("submit",async (event) => {
      if (!["tj-create-form","tj-event-form"].includes(event.target.id)) return;
      event.preventDefault(); if (!event.target.reportValidity()) return;
      try {
        const result = event.target.id === "tj-create-form"
          ? await controller.save({direction:$("tj-direction").value,as_of:$("tj-as-of").value,thesis:$("tj-thesis").value,
            trigger_condition:$("tj-trigger").value,invalidation_condition:$("tj-invalidation").value,counter_evidence:$("tj-counter").value},event.submitter)
          : await controller.append({event_type:$("tj-event-type").value,as_of:$("tj-event-date").value,note:$("tj-event-note").value},event.submitter);
        if (result) { message("记录已保存，可刷新重开并查看原冻结依据。"); $("tj-detail-title")?.focus(); }
        else $("tj-error").focus();
      } catch (error) { message(error.message || "请核对表单。",true); }
    });
    render(controller.state);
    return {refresh:controller.refresh,openSource,
      setSources(records) {
        sources = sourcesFrom(records); const selected = $("tj-source").value;
        $("tj-source").innerHTML = '<option value="">请选择冻结行情、任务或结果</option>' + sources.map((row) => `<option value="${escape(row.key)}">${escape(row.label)}</option>`).join("");
        if (sources.some((row) => row.key === selected)) $("tj-source").value = selected;
        render(controller.state);
      }};
  }
  root.installTerminalJudgmentUI = install;
  if (typeof module === "object" && module.exports) module.exports = {createPayload,eventPayload,createController,sourcesFrom,renderTimeline,indicatorHtml,detailHtml,install};
})(typeof window !== "undefined" ? window : globalThis);
