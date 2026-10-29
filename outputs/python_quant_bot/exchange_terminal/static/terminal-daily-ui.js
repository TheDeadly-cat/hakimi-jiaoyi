/* Explicit daily-source review. Local reads never request provider data. */
(function (root) {
  "use strict";
  const PREFIX = "terminal_daily_";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const copy = value => JSON.parse(JSON.stringify(value));
  const present = value => value !== undefined && value !== null && value !== "";
  const terms = {COMMON_STOCK:"普通股",XNAS:"纳斯达克（XNAS）",XNYS:"纽约证券交易所（XNYS）",
    SOURCE_BACKED_IMPORTER_DECLARATION_NOT_EXTERNAL_TRUTH:"依据导入来源声明核对交易日历，未经独立真实性认证",
    ACTION_FREE_FIXED_WINDOW_ONLY:"仅允许不含公司行为的固定区间",NOT_CRYPTOGRAPHICALLY_AUTHENTICATED:"未获密码学来源认证",
    IMPORTED_UNVERIFIED:"导入资料，未获独立认证"};
  const shown = value => !present(value) ? "未记录" : Array.isArray(value) && !value.length ? "记录为空" : typeof value === "object" ? JSON.stringify(value) : Object.hasOwn(terms,value) ? terms[value] : String(value);
  const canonical = value => value && /^canon-[a-f0-9]{32}$/.test(value.id || "") && value.record_namespace === "canonical-daily-v1";
  const labels = {REVIEW_REQUIRED:"待确认证券", READY:"有新日线", REVISION_REVIEW_REQUIRED:"历史数据有修订", UNCHANGED:"没有变化", BLOCKED:"检查未通过", WAITING_SOURCE_UPDATE:"等待来源更新", CALENDAR_UNAVAILABLE:"交易日历不可用", UNKNOWN:"结果尚未确认"};
  const statusText = value => value?.saved_input_id ? "已保存行情" : Object.hasOwn(labels,value?.status) ? labels[value.status] : shown(value?.status);
  const pairs = rows => '<dl class="daily-facts">' + rows.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(shown(value))}</dd></div>`).join("") + "</dl>";
  const securityRows = value => {
    const security = value.security || {};
    return [["股票", security.symbol || value.symbol], ["公司名称", value.company_name], ["证券身份", security.security_id], ["交易所", security.exchange], ["币种", security.currency], ["证券类型", security.instrument_type]];
  };
  function facts(value, kind) {
    const source = value.source || {};
    const missing = value.missing_sessions ?? value.stop_detail?.details?.missing_sessions
      ?? (typeof value.reason === "string" && value.reason.startsWith("SOURCE_MISSING_COMPLETED_SESSIONS:") ? value.reason.slice("SOURCE_MISSING_COMPLETED_SESSIONS:".length) : undefined);
    const rows = [...securityRows(value), ["行情区间", present(value.coverage_start) && present(value.coverage_end) ? `${value.coverage_start} 至 ${value.coverage_end}` : undefined],
      ["已记录交易日数", value.sessions ?? value.session_count], ["价格口径", value.price_basis === "RAW_UNADJUSTED" ? "原始未复权" : value.price_basis],
      ["来源", source.name], ["来源地址", source.reference || value.source_url], ["获取时间", source.retrieved_at || value.retrieved_at],
      ["缺失数据记录", missing],
      ["完整性检查", value.calendar_coverage || (kind === "intake" && value.can_save === true ? "本次检查允许进入保存确认；未单独记录缺失日清单" : undefined)],
      ["公司行为准入", value.corporate_actions || (kind === "intake" && value.can_save === true ? "本次通过无公司行为窗口检查" : undefined)],
      ["区间外公司行为", value.outside_window_actions], ["未完成日线排除记录", value.excluded_forming_sessions],
      ["来源认证记录", value.source_authentication ?? (value.source_truth_verified === false ? "未获独立认证" : undefined)]];
    return (value.stop_detail?.summary ? `<p>${esc(value.stop_detail.summary)}</p>` : "") + pairs(rows) + (kind === "intake" ? '<p class="section-note">当前导入只允许完整日线和无公司行为窗口；价格口径以保存后的记录为准。检查通过不等于来源认证。</p>' : "")
      + `<details><summary>查看检查依据与保存身份</summary>${pairs([["原始状态",value.status],["原因",value.reason || value.reasons],["检查详情",value.stop_detail],["限制",value.limitations],["检查身份",value.check_hash],["行情身份",value.input_id],["原始来源校验值",source.raw_sha256 || value.raw_sha256],["本地保存身份",value.id]])}</details>`;
  }
  let instance = 0;
  function installTerminalDailyUI({host, api, perform, notify = () => {}, onInputImported, allowPublicDataRequest = false}) {
    if (!host || typeof api !== "function" || typeof perform !== "function") throw new Error("daily_ui_dependencies_required");
    const document = host.ownerDocument;
    const view = document.createElement("section");
    const uid = "terminal-daily-" + (++instance);
    const state = {inputs:[], intakes:[], updates:[], input:null, intake:null, update:null, confirmed:false, revisions:false,
      busy:false, importing:false, pending:null, message:"", error:"", warnings:[], imported:new Set(),access:null,accessError:"",requestAttempts:null,revoking:false};
    let readSequence = 0, accessSequence = 0, permissionEpoch = 0;
    view.className = "panel terminal-daily-ui";
    view.setAttribute("aria-label", "股票日线资料");
    view.innerHTML = `<style>.terminal-daily-ui .daily-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:12px;margin:16px 0}.terminal-daily-ui .daily-facts div{min-width:0}.terminal-daily-ui dt{font-size:.85em;color:var(--muted,#a1a9b8)}.terminal-daily-ui dd{margin:4px 0;overflow-wrap:anywhere}.terminal-daily-ui .daily-list{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.terminal-daily-ui .daily-section{margin-top:24px}.terminal-daily-ui label{display:block;margin:10px 0}.terminal-daily-ui button{min-height:36px;white-space:normal}.terminal-daily-ui button:focus-visible,.terminal-daily-ui input:focus-visible,.terminal-daily-ui select:focus-visible{outline:2px solid var(--blue,#74a8ff);outline-offset:3px}.terminal-daily-ui [hidden]{display:none!important}.terminal-daily-ui .daily-status{min-height:1.6em;overflow-wrap:anywhere}.terminal-daily-ui pre{white-space:pre-wrap;overflow-wrap:anywhere}.terminal-daily-ui .daily-revisions{overflow-x:auto}.terminal-daily-ui table{width:100%;border-collapse:collapse}.terminal-daily-ui th,.terminal-daily-ui td{text-align:left;padding:8px;overflow-wrap:anywhere}</style>
      <div class="panel-head"><h2>股票日线资料</h2><button class="btn" type="button" data-do="refresh">重新读取已保存资料</button></div>
      <div class="panel-body"><p class="section-note" data-role="mode"></p><p class="section-note">1 检查行情 → 2 确认证券并保存 → 3 按需检查更新。保存资料后，可另行选择原策略研究；不会自动运行。</p>
      <p class="section-note" data-role="access"></p><button class="btn" type="button" data-do="revoke">停止获取公开行情</button>
      <p class="daily-status" role="status" aria-live="polite" aria-atomic="true" data-role="status"></p><p role="alert" data-role="error" hidden></p>
      <form data-role="form"><div class="form-grid"><label class="field" for="${uid}-symbol">股票代码<input id="${uid}-symbol" name="symbol" placeholder="例如 NDAQ" maxlength="12" autocomplete="off" spellcheck="false" required></label>
      <div class="field"><label for="${uid}-sessions">历史交易日</label><select id="${uid}-sessions" name="history_sessions"><option value="20">20 个交易日</option><option value="60">60 个交易日</option><option value="120" selected>120 个交易日</option></select></div></div>
      <p class="section-note">默认 120 个交易日，为原策略通常至少 82 日的准备与执行窗口留出余量；具体可评分区间仍需核对。</p><button class="btn primary" type="submit" data-do="check-stock">检查股票行情</button></form>
      <div class="daily-section"><h3>检查记录</h3><div data-role="intakes" class="daily-list"></div><div data-role="intake"></div>
      <label data-role="confirm-wrap" hidden><input type="checkbox" data-do="confirm">我已核对以上证券身份、交易所和币种，确认为要研究的证券</label><button type="button" class="btn primary" data-do="save" hidden>确认证券并保存行情</button></div>
      <div class="daily-section"><h3>已保存行情</h3><div data-role="inputs" class="daily-list"></div><div data-role="input"></div><div class="actions">
      <button type="button" class="btn" data-do="check-update" hidden>检查这份行情的更新</button><button type="button" class="btn" data-do="import" hidden>复用到原策略研究</button></div><p class="section-note" data-role="import-note" hidden></p></div>
      <div class="daily-section"><h3>更新检查记录</h3><div data-role="updates" class="daily-list"></div><div data-role="update"></div>
      <label data-role="revision-wrap" hidden><input type="checkbox" data-do="revisions">我已核对历史修订，确认另存新版本；保留原行情和原结果</label><button type="button" class="btn primary" data-do="freeze" hidden>保存新的行情版本</button></div></div>`;
    host.appendChild(view);
    const get = selector => view.querySelector(selector);
    const role = name => get(`[data-role="${name}"]`);
    const action = name => get(`[data-do="${name}"]`);
    const say = (message) => {
      state.message = message;
      // A page switch may have just displayed the next step or a saved fact.
      // Keep this component's late cleanup/result locally without replacing it.
      if (view.hidden) return;
      try { notify(message); } catch (_) { /* notification failure cannot revoke a saved result */ }
    };
    const gateStates={DISABLED:"当前没有可用的获取许可",AVAILABLE_ONCE:"已准备一次获取许可",PREPARING:"本次检查正在准备",REQUESTING:"公开行情请求已在途",REVOKED_PREPARING:"后续获取已阻断，原检查仍待返回",REVOKED_IN_FLIGHT:"后续获取已阻断，在途请求无法撤销",UNAVAILABLE:"本次会话的公开行情入口不可用"};
    function gateValue(value) {
      const result=value?.ok===true?value.data:value;
      if(result?.schema_version!=="hakimi-public-daily-access-v1"||!Object.hasOwn(gateStates,result.state))throw Error("公开行情许可状态尚未确认。");
      return result;
    }
    async function readAccess() {
      const sequence=++accessSequence;
      try { const value=gateValue(await api("public-daily-access"));if(sequence===accessSequence){state.access=value;state.accessError="";} }
      catch (_) {if(sequence===accessSequence)state.accessError="许可状态读取未完成；未新增获取许可。";}
    }
    async function revokeUnused() {
      permissionEpoch++;const sequence=++accessSequence;state.revoking=true;render();
      try {
        const value=gateValue(await api("public-daily-access/revoke","POST",{}));
        if(sequence===accessSequence){state.access=value;state.accessError="";}
        say(value.requests_in_flight>0||value.state==="REVOKED_IN_FLIGHT"?"已阻断后续获取。在途请求无法撤销，原检查仍将保留返回记录。":"已撤销未使用的许可并阻断后续获取；不会删除已完成记录，也不会取消已经发出的请求。");
        return value;
      } catch (_) {state.accessError="停止获取的结果尚未确认；不能声称在途请求已取消。请重新读取状态。";return null;}
      finally {state.revoking=false;render();}
    }
    const id = () => {
      const crypto = document.defaultView?.crypto;
      if (typeof crypto?.randomUUID === "function") return crypto.randomUUID();
      if (!crypto?.getRandomValues) throw new Error("无法生成本次操作身份，未提交。");
      return Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2,"0")).join("");
    };
    function renderList(name, selected) {
      role(name).innerHTML = state[name].length ? state[name].map(item => `<button type="button" class="btn" data-open="${name}" data-id="${esc(item.id)}" aria-pressed="${item.id === selected?.id}">${esc(item.security?.symbol || item.symbol || "证券未记录")} · ${esc(item.coverage_end || item.latest_completed_session || item.checked_at || "日期未记录")} · ${esc(name === "inputs" ? "已保存" : statusText(item))}</button>`).join("") : '<p class="section-note">暂无已读取的记录。</p>';
    }
    function render() {
      const locked = state.busy || !!state.pending || state.importing;
      view.setAttribute("aria-busy", String(state.busy || state.importing));
      role("mode").textContent = allowPublicDataRequest === true ? "每次点击检查，只向 Yahoo Finance 获取一次公开日线；不在后台获取、不自动重试。" : "当前离线：联网检查未启用，仍可读取已保存资料和已有检查记录。";
      role("access").textContent = (state.access?gateStates[state.access.state]+"。会话实际外部请求："+(Number.isSafeInteger(state.access.actual_attempts)?state.access.actual_attempts:"未记录")+" 次。":"许可状态尚未读取。")+(state.requestAttempts!==null?" 最近一次检查实际外部请求："+state.requestAttempts+" 次。":"");
      action("revoke").disabled=state.revoking;action("revoke").hidden=allowPublicDataRequest!==true;
      role("status").textContent = state.message;
      role("error").textContent = [state.error,state.accessError, ...state.warnings].filter(Boolean).join("\n"); role("error").hidden = !role("error").textContent;
      action("check-stock").disabled = locked || state.revoking || allowPublicDataRequest !== true;
      get('[name="symbol"]').disabled = state.busy; get('[name="history_sessions"]').disabled = state.busy;
      renderList("intakes",state.intake); renderList("inputs",state.input); renderList("updates",state.update);
      role("intake").innerHTML = state.intake ? `<h4>${esc(statusText(state.intake))}</h4>` + facts(state.intake,"intake") : "";
      const canSave = state.intake?.can_save === true && state.intake.status === "REVIEW_REQUIRED" && !state.intake.saved_input_id;
      role("confirm-wrap").hidden = !canSave; action("confirm").checked = state.confirmed; action("confirm").disabled = locked;
      action("save").hidden = !canSave; action("save").disabled = locked || !state.confirmed;
      role("input").innerHTML = state.input ? facts(state.input,"input") : "";
      const usableInput = state.input?.status === "READY" && state.input?.kind === "PRICE_SNAPSHOT";
      action("check-update").hidden = !state.input; action("check-update").disabled = locked || state.revoking || allowPublicDataRequest !== true || !usableInput;
      action("import").hidden = !state.input; action("import").disabled = locked || typeof onInputImported !== "function" || !usableInput || state.imported.has(state.input?.id);
      role("import-note").hidden = !state.input; role("import-note").textContent = typeof onInputImported === "function" ? "复用后仍需在原策略研究中确认任务设置并明确运行。" : "已保存资料可继续查看；复用到原策略的入口尚未启用。";
      const update = state.update;
      role("update").innerHTML = !update ? "" : `<h4>${esc(statusText(update))}</h4>` + (update.stop_detail?.summary ? `<p>${esc(update.stop_detail.summary)}</p>` : "") + pairs([["股票",update.symbol],["本次检查时间",update.checked_at],["原行情区间",present(update.baseline_start) && present(update.baseline_end) ? `${update.baseline_start} 至 ${update.baseline_end}` : undefined],["原行情身份",update.baseline_snapshot_id],["最新完整交易日",update.latest_completed_session],["新增日线日期",update.new_dates],["来源地址",update.source_url],["获取时间",update.retrieved_at],["原始状态",update.status],["原因",update.reason],["检查详情",update.stop_detail],["已保存行情身份",update.saved_input_id]])
        + (Array.isArray(update.revisions) && update.revisions.length ? `<div class="daily-revisions"><table><caption>历史修订明细</caption><thead><tr><th>日期</th><th>字段</th><th>原值</th><th>新值</th></tr></thead><tbody>${update.revisions.map(row => `<tr><td>${esc(shown(row.date))}</td><td>${esc(shown(row.field))}</td><td>${esc(shown(row.old_value))}</td><td>${esc(shown(row.new_value))}</td></tr>`).join("")}</tbody></table></div>` : "")
        + (update.status === "UNCHANGED" ? '<p class="section-note">没有新增或修订的完整日线，不创建新行情、任务版本或回测结果。</p>' : update.status === "UNKNOWN" ? '<p class="section-note">检查结果尚未确认。只读取记录核对，不自动重试。</p>' : "");
      const revision = update?.status === "REVISION_REVIEW_REQUIRED" || !!update?.revisions?.length;
      const canFreeze = update?.can_freeze === true && ["READY","REVISION_REVIEW_REQUIRED"].includes(update.status) && !update.saved_input_id;
      role("revision-wrap").hidden = !canFreeze || !revision; action("revisions").checked = state.revisions; action("revisions").disabled = locked;
      action("freeze").hidden = !canFreeze; action("freeze").disabled = locked || (revision && !state.revisions);
    }
    function accept(name, value) {
      const request=value?.public_daily_request;
      if(Number.isSafeInteger(request?.actual_attempts)&&request.actual_attempts>=0)state.requestAttempts=request.actual_attempts;
      if(["check_stock","check_update"].includes(name)&&value?.status==="PUBLIC_DAILY_REQUEST_REFUSED"&&request?.actual_attempts===0&&request.request_in_flight===false&&request.operation_in_flight===false){
        state.pending=null;state.error="本次请求已被拒绝，检查未发起。实际外部请求 0 次。"+(value.error?.message||"");say("本次检查未发起；可核对原因后再次明确点击。");render();return true;
      }
      if (!canonical(value)) return false;
      const kind = name === "check_stock" ? "intakes" : name === "check_update" ? "updates" : "inputs";
      if (value.record_resource !== PREFIX + kind || (kind === "inputs" && value.kind !== "PRICE_SNAPSHOT") || !present(value.status)) return false;
      state[kind] = [value, ...state[kind].filter(item => item.id !== value.id)];
      if (kind === "intakes") { state.intake = value; state.confirmed = false; }
      else if (kind === "updates") { state.update = value; state.revisions = false; }
      else {
        state.input = value;
        if (name === "save_stock" && state.intake) state.intake = {...state.intake,saved_input_id:value.id};
        if (name === "freeze_update" && state.update) state.update = {...state.update,saved_input_id:value.id};
      }
      if (value.status === "UNKNOWN") { state.error = "检查结果尚未确认，请读取记录和操作日志核对；不重复提交。";state.message="本次检查结果待核对。"; render(); return true; }
      state.pending = null;
      say(kind === "inputs" ? "行情已保存。原行情和原结果保留，尚未运行策略。" : "检查记录已保存，请核对以下信息。");
      render(); return true;
    }
    async function refresh() {
      const sequence = ++readSequence;
      const kinds = ["inputs","intakes","updates"];
      const [results] = await Promise.all([Promise.allSettled(kinds.map(kind => api(PREFIX + kind))),readAccess()]);
      if (sequence !== readSequence) return;
      state.warnings = [];
      results.forEach((result,index) => {
        const kind = kinds[index];
        if (result.status !== "fulfilled" || !Array.isArray(result.value?.items)) { state.warnings.push("部分已保存资料读取失败，已保留当前显示；可重新读取。" ); return; }
        const items = result.value.items;
        if (items.some(item => !canonical(item) || item.record_resource !== PREFIX + kind)) { state.warnings.push("资料身份不匹配，已保留当前显示。"); return; }
        state[kind] = items;
        state.warnings.push(...(result.value.warnings || []).map(item => "资料读取提示：" + item));
        const key = {inputs:"input",intakes:"intake",updates:"update"}[kind];
        const found = items.find(item => item.id === state[key]?.id);
        if (found) { if (found.check_hash !== state[key]?.check_hash) { state.confirmed = false; state.revisions = false; } state[key] = found; }
      });
      if (state.pending) {
        const pending = state.pending;
        const kind = pending.name === "check_stock" ? "intakes" : "updates";
        if (["check_stock","check_update"].includes(pending.name)) {
          const check = state[kind].find(item => item.intake_id === "check-" + pending.operation_id || item.ref === (kind === "intakes" ? "stock-intakes/" : "updates/") + "check-" + pending.operation_id);
          if (check && check.status !== "UNKNOWN") { state.error = ""; accept(pending.name,check); }
        } else if (["save_stock","freeze_update"].includes(pending.name)) {
          const checks = pending.name === "save_stock" ? state.intakes : state.updates;
          const check = checks.find(item => item.id === pending.check_id && item.check_hash === pending.check_hash);
          const input = check && state.inputs.find(item => item.id === check.saved_input_id);
          if (input) { state.error = ""; accept(pending.name,input); }
        }
      }
      render();
    }
    async function mutate(name, payload) {
      if (state.busy || state.pending || state.importing || state.revoking) return;
      const networkCheck=["check_stock","check_update"].includes(name),epoch=permissionEpoch;
      if (networkCheck && allowPublicDataRequest !== true) return;
      payload = {...payload,operation_id:id()};
      if(networkCheck)state.requestAttempts=null;
      state.pending = {name,operation_id:payload.operation_id,check_id:payload.intake_id || payload.update_id,check_hash:payload.expected_check_hash};
      state.busy = true; state.error = ""; state.message = "正在处理本次明确操作，请等待记录。"; render();
      let accepted = false,submitted=false;
      try {
        if(networkCheck){
          const sequence=++accessSequence;
          const value=gateValue(await api("public-daily-access/allow-once","POST",{action:PREFIX+name,payload:copy(payload)}));
          if(sequence===accessSequence){state.access=value;state.accessError="";}
          if(epoch!==permissionEpoch||view.hidden){await revokeUnused();state.pending=null;state.message="已停止本次检查，尚未提交行情任务。";return;}
          if(!Array.isArray(value.allowed_actions)||!value.allowed_actions.includes(PREFIX+name)||!(value.unconsumed_authorizations>0))throw Error("未取得本次操作的单次许可。");
        }
        submitted=true;
        const result = await perform(PREFIX + name,payload,{onSuccess:value => { accepted = accept(name,value); }});
        if (!accepted) accepted = accept(name,result);
      } catch (error) {
        if (accepted) state.warnings = ["操作记录已返回；随后页面刷新未完成。可重新读取已保存资料。"];
        else if(!submitted){state.pending=null;state.error="单次获取许可未完成，尚未发起行情检查。"+(error?.info?.message||error?.message||"");state.message="行情检查尚未发起。";}
      } finally {
        state.busy = false;
        if (!accepted&&submitted) { state.error = "提交结果尚未确认。请重新读取已保存资料并核对操作日志，不要重复提交。"; state.message = "本次操作待核对。"; }
        render();
      }
      if(networkCheck&&!accepted){await readAccess();render();}
      if (accepted) await refresh();
    }
    get('[data-role="form"]').addEventListener("submit",event => {
      event.preventDefault();
      const symbol = get('[name="symbol"]').value.trim().toUpperCase();
      const history_sessions = Number(get('[name="history_sessions"]').value);
      if (!/^[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?$/.test(symbol) || ![20,60,120].includes(history_sessions)) { state.error = "请填写有效股票代码，并选择 20、60 或 120 个交易日。"; render(); return; }
      void mutate("check_stock",{symbol,history_sessions});
    });
    for (const field of view.querySelectorAll("form input,form select")) field.addEventListener("input",() => { state.confirmed = false; action("confirm").checked = false; action("save").disabled = true; });
    view.addEventListener("change",event => {
      if (event.target === action("confirm")) { state.confirmed = event.target.checked; render(); }
      if (event.target === action("revisions")) { state.revisions = event.target.checked; render(); }
    });
    view.addEventListener("click",async event => {
      const button = event.target.closest("button");
      if (!button || !view.contains(button) || button.disabled) return;
      if (button.dataset.open) {
        if (state.busy || state.importing) return;
        const kind = button.dataset.open, value = state[kind]?.find(item => item.id === button.dataset.id);
        if (value) { state[{inputs:"input",intakes:"intake",updates:"update"}[kind]] = value; state.confirmed = false; state.revisions = false; render(); }
        return;
      }
      const name = button.dataset.do;
      if (name === "refresh") return refresh();
      if (name === "revoke") return revokeUnused();
      if (state.busy || state.pending || state.importing) return;
      if (name === "save" && state.confirmed && state.intake?.can_save === true && !state.intake.saved_input_id) return mutate("save_stock",{intake_id:state.intake.id,expected_check_hash:state.intake.check_hash,confirmed_security:copy(state.intake.security)});
      if (name === "check-update" && state.input?.status === "READY" && state.input?.kind === "PRICE_SNAPSHOT") return mutate("check_update",{input_id:state.input.id});
      if (name === "freeze" && state.update?.can_freeze === true && ["READY","REVISION_REVIEW_REQUIRED"].includes(state.update.status) && !state.update.saved_input_id
        && (!(state.update.status === "REVISION_REVIEW_REQUIRED" || state.update.revisions?.length) || state.revisions)) return mutate("freeze_update",{update_id:state.update.id,expected_check_hash:state.update.check_hash,acknowledge_revisions:state.revisions});
      if (name === "import" && typeof onInputImported === "function" && state.input?.status === "READY" && state.input?.kind === "PRICE_SNAPSHOT" && !state.imported.has(state.input.id)) {
        const selected = copy(state.input); state.importing = true; state.error = ""; render();
        try {
          // The host owns import/admission and truthful completion feedback.
          // Returning false/null/undefined is not evidence of a completed import.
          const result = await onInputImported(selected);
          if (result?.status === "IMPORTED" && typeof result.input_id === "string" && result.input_id.length > 0 && !result.input_id.startsWith("canon-")) { state.imported.add(selected.id); say("已复用到原策略研究，尚未运行策略。"); }
          else { state.pending = {name:"import",check_id:selected.id}; state.error = "复用结果尚未确认，请到原策略研究核对；不要重复提交。"; }
        } catch (_) { state.pending = {name:"import",check_id:selected.id}; state.error = "复用结果尚未确认，请到原策略研究核对；不要重复提交。"; }
        finally { state.importing = false; render(); }
      }
    });
    render();
    return {refresh,revokeUnused,hide:async()=>{view.hidden=true;return revokeUnused();},reveal:async () => { view.hidden = false; await refresh(); return view; }};
  }
  root.installTerminalDailyUI = installTerminalDailyUI;
  if (typeof module === "object" && module.exports) module.exports = {installTerminalDailyUI};
})(typeof globalThis !== "undefined" ? globalThis : this);
