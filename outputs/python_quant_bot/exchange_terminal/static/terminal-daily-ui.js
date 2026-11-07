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
  const historyAction="terminal_import_history_input",historySchema="terminal-history-input-copy-v1";
  const hex=(value,length)=>typeof value==="string"&&new RegExp(`^[a-f0-9]{${length}}$`).test(value);
  const historyOperation=value=>typeof value==="string"&&/^history-copy-[A-Za-z0-9_-]{8,64}$/.test(value);
  const ordered=value=>value&&typeof value==="object"?(Array.isArray(value)?value.map(ordered):Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])]))):value;
  const canonicalJSON=value=>JSON.stringify(ordered(value)).replace(/[\u007f-\uffff]/g,char=>"\\u"+char.charCodeAt(0).toString(16).padStart(4,"0"));
  const same=value=>canonicalJSON(value);
  async function requestDigest(value){return Array.from(new Uint8Array(await root.crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonicalJSON(value)))),n=>n.toString(16).padStart(2,"0")).join("");}
  const historyInput=value=>value&&hex(value.id,32)&&value.input_id===value.id&&value.resource==="inputs"
    &&value.kind==="PRICE_SNAPSHOT"&&value.available===true&&value.verification_status==="VERIFIED_RECORD"
    &&hex(value.file_sha256,64)&&hex(value.snapshot_id,64)&&value.security&&typeof value.security==="object"
    &&Number.isSafeInteger(value.byte_count)&&value.byte_count>0&&value.byte_count<=8*1024*1024;
  function createHistoryInputController({api,perform,acceptInput,uuid=()=>root.crypto.randomUUID(),changed=()=>{}}){
    const state={workspaces:[],workspaceId:"",inputs:[],selected:null,requests:[],receipt:null,pending:null,confirmed:false,busy:false,reading:false,recoveryChecked:false,error:"",message:""};
    let sequence=0;const delivered=new Set(),emit=()=>changed(state),require=(value,message)=>{if(!value)throw Error(message);};
    const idle=()=>require(!state.busy&&!state.pending,"请先查询原复制请求，不要重复提交。");
    async function checkedReceipt(value,expected){
      require(value?.schema_version===historySchema&&value.action===historyAction&&historyOperation(value.operation_id)
        &&["NOT_RECORDED","PENDING","STOPPED","COMPLETED"].includes(value.status)&&value.source_truth_verified===false
        &&value.current_source_rechecked===false&&value.receipt_scope==="SAVED_OPERATION_FACT_NOT_CURRENT_SOURCE_VALIDATION"
        &&value.permissions?.research_only===true&&["paper_allowed","live_allowed","order_allowed"].every(k=>value.permissions[k]===false),"原复制回执的身份或权限无法核对。");
      if(expected)require(value.operation_id===expected.payload.operation_id,"返回了另一份复制请求。");
      if(value.status==="NOT_RECORDED")return value;
      const payload=value.request;require(payload&&payload.operation_id===value.operation_id&&hex(payload.workspace_id,32)&&hex(payload.input_id,32)
        &&hex(payload.expected_file_sha256,64)&&hex(payload.expected_snapshot_id,64)&&payload.acknowledge_source_limits===true,"原复制请求不完整。");
      const digest=await requestDigest({action:historyAction,payload});require(value.request_hash===digest&&(!expected||digest===expected.request_hash),"原复制请求内容与当前回执不一致。");
      require(value.source?.workspace_id===payload.workspace_id&&value.source.input_id===payload.input_id
        &&value.source.file_sha256===payload.expected_file_sha256&&value.source.snapshot_id===payload.expected_snapshot_id
        &&same(value.source.security)===same(payload.confirmed_security),"复制回执的来源身份不一致。");
      if(value.status==="COMPLETED"){
        require(typeof value.saved_input_id==="string"&&/^canon-[a-f0-9]{32}$/.test(value.saved_input_id),"已保存副本的身份未记录。");
        require(["VERIFIED_CURRENT_TARGET","UNAVAILABLE"].includes(value.saved_input_verification),"当前副本的核验状态未记录。");
        if(value.saved_input_verification==="VERIFIED_CURRENT_TARGET"){
          const input=value.saved_input;require(canonical(input)&&input.id===value.saved_input_id&&input.record_resource===PREFIX+"inputs"
            &&input.kind==="PRICE_SNAPSHOT"&&input.status==="READY"&&input.file_sha256===payload.expected_file_sha256
            &&input.input_id===payload.expected_snapshot_id&&same(input.security)===same(payload.confirmed_security)
            &&input.permissions?.research_only===true&&["paper_allowed","live_allowed","order_allowed"].every(k=>input.permissions[k]===false),"当前副本未通过独立身份核对。");
        }else require(value.saved_input===null,"未核验的副本不能被选用。");
      }
      return value;
    }
    async function accept(value,expected,explicit=false){
      value=await checkedReceipt(value,expected);state.receipt=copy(value);
      if(value.status==="NOT_RECORDED"||value.status==="PENDING"){
        if(value.status==="PENDING")state.pending={payload:copy(value.request),request_hash:value.request_hash};
        state.message=value.status==="PENDING"?"原复制结果仍待核对；这里只查询，不会重试复制。":"尚未找到完整原回执；保留请求编号，继续只读核对。";emit();return false;
      }
      state.pending=null;state.confirmed=false;
      if(value.status==="STOPPED"){state.error="原复制请求已停止："+(value.error||"详情未记录");state.message="此次复制没有完成确认。";emit();return true;}
      state.error="";state.message=value.message||"已复制保存，未创建任务或运行研究。";emit();
      if(value.saved_input_verification==="VERIFIED_CURRENT_TARGET"&&(explicit||!delivered.has(value.operation_id))){
        try{await acceptInput(copy(value.saved_input));delivered.add(value.operation_id);}catch(error){state.error="保存事实已确认，选用副本时读取未完成。请查询原回执。";emit();}
      }
      return true;
    }
    async function readRequests(){
      state.recoveryChecked=false;
      const value=await api("terminal_history_input_requests");require(value?.schema_version===historySchema&&value.read_only===true&&Array.isArray(value.items)&&Array.isArray(value.warnings),"复制记录列表无法核对。");
      const items=[];for(const item of value.items)items.push(await checkedReceipt(item));state.requests=copy(items);
      state.recoveryChecked=value.warnings.length===0;
      const unresolved=items.find(item=>item.status==="PENDING");
      if(unresolved&&!state.pending){state.pending={payload:copy(unresolved.request),request_hash:unresolved.request_hash};state.receipt=copy(unresolved);state.confirmed=false;state.message="发现尚未确认的原复制请求；请先查询它，不要重新复制。";}
      if(value.warnings.length)state.error="部分复制回执尚未读出；已保留原记录。";emit();return items;
    }
    async function discover(){if(state.busy||state.reading)return;state.reading=true;state.error="";emit();
      try{const value=await api("terminal_workspace_history");require(Array.isArray(value?.items)&&Array.isArray(value.warnings)&&value.read_only===true,"已有工作区列表无法核对。");
        require(value.items.every(item=>hex(item.id,32)),"已有工作区的身份不完整。");state.workspaces=copy(value.items);
        state.message=state.workspaces.length?"选择旧工作区，再核对其中的已保存行情。这里只读取，不获取新行情。":"未找到已知旧工作区。可以返回首页使用虚构示例。";
        if(value.warnings.length)state.error="部分旧工作区无法读取；已列出可核对的位置。";
        await readRequests();
      }catch(error){state.error=error?.info?.message||error.message;}finally{state.reading=false;emit();}}
    async function selectWorkspace(identity){idle();require(state.workspaces.some(item=>item.id===identity),"请选择已知旧工作区。");const current=++sequence;
      state.workspaceId=identity;state.selected=null;state.inputs=[];state.confirmed=false;state.reading=true;state.error="";emit();
      try{const value=await api(`terminal_workspace_history/${identity}/inputs`);require(value?.workspace_id===identity&&value.resource==="inputs"&&Array.isArray(value.items)&&value.read_only===true,"旧行情列表身份不一致。");
        if(current!==sequence)return;state.inputs=copy(value.items);state.message=value.items.length?"选择要复制的行情，核对证券与日期后单独确认。":"这个工作区没有可读取的已保存行情；可选择其他工作区或使用教学示例。";
        if(value.warnings?.length)state.error="部分原行情未能读取；不会绕过校验。";
      }catch(error){if(current===sequence)state.error=error?.info?.message||error.message;}finally{if(current===sequence){state.reading=false;emit();}}}
    function selectInput(identity){idle();const item=state.inputs.find(value=>value.id===identity);require(historyInput(item),"这份资料未通过校验或超过8 MiB，暂不可复制。");state.selected=copy(item);state.confirmed=false;state.error="";emit();}
    function confirm(value){state.confirmed=value===true&&state.recoveryChecked&&historyInput(state.selected)&&!state.pending&&!state.busy;emit();}
    async function copySelected(){idle();require(!state.reading&&state.recoveryChecked&&state.confirmed&&historyInput(state.selected),"请先核对原复制记录、证券、日期和来源限制，并明确确认。");
      const input=copy(state.selected),payload={operation_id:"history-copy-"+uuid(),workspace_id:state.workspaceId,input_id:input.id,expected_file_sha256:input.file_sha256,
        expected_snapshot_id:input.snapshot_id,confirmed_security:copy(input.security),acknowledge_source_limits:true};
      state.busy=true;state.error="";state.confirmed=false;state.message="正在复制这份已保存资料；原件不变。";emit();let completion=null,submitted=false;
      try{const operation={payload,request_hash:await requestDigest({action:historyAction,payload})};state.pending=operation;
        const receive=value=>{if(!completion){completion=accept(value,operation);completion.catch(()=>{});}return completion;};submitted=true;
        const result=await perform(historyAction,copy(payload),{onSuccess:receive});if(result&&!completion)receive(result);if(completion)await completion;
      }catch(error){if(completion){try{await completion;}catch(_){}}
        if(state.receipt?.operation_id===payload.operation_id&&state.receipt.status==="COMPLETED")state.error="原回执已确认保存，随后显示未完成；可查询原记录。";
        else state.error=submitted?"提交结果尚未确认，请查询原复制编号，不重复提交。":"复制尚未提交："+(error?.message||"");}
      finally{state.busy=false;if(!submitted)state.pending=null;if(state.pending)state.message="原复制结果待核对；只查询这个请求。";emit();}}
    async function query(identity=state.pending?.payload.operation_id){if(state.busy||state.reading||!historyOperation(identity))return;
      if(state.pending&&identity!==state.pending.payload.operation_id){state.error="请先查询当前待核对的复制编号。";emit();return;}
      state.reading=true;state.error="";emit();try{const value=await api("terminal_history_input_requests/"+identity);await accept(value,state.pending?.payload.operation_id===identity?state.pending:null,true);}
      catch(error){state.error="原复制回执暂未读出："+(error?.info?.message||error.message);}finally{state.reading=false;emit();}}
    return {state,discover,selectWorkspace,selectInput,confirm,copySelected,query,readRequests};
  }
  const pairs = rows => '<dl class="daily-facts">' + rows.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(shown(value))}</dd></div>`).join("") + "</dl>";
  const securityRows = value => {
    const security = value.security || {};
    return [["股票", security.symbol || value.symbol], ["公司名称", value.company_name], ["证券身份", security.security_id], ["交易所", security.exchange], ["币种", security.currency], ["证券类型", security.instrument_type]];
  };
  function facts(value, kind) {
    const source = value.source || {};
    const priceReviewPending = kind === "intake" && value.can_save === false && value.session_count === 0 && value.stop_detail?.category === "CORPORATE_ACTION";
    const missing = value.missing_sessions ?? value.stop_detail?.details?.missing_sessions
      ?? (typeof value.reason === "string" && value.reason.startsWith("SOURCE_MISSING_COMPLETED_SESSIONS:") ? value.reason.slice("SOURCE_MISSING_COMPLETED_SESSIONS:".length) : undefined);
    const rows = [...securityRows(value), ["行情区间", present(value.coverage_start) && present(value.coverage_end) ? `${value.coverage_start} 至 ${value.coverage_end}` : undefined],
      ["已记录交易日数", priceReviewPending ? "尚未核对价格完整性；不表示没有行情" : value.sessions ?? value.session_count], ["价格口径", value.price_basis === "RAW_UNADJUSTED" ? "原始未复权" : value.price_basis],
      ["来源", source.name], ["来源地址", source.reference || value.source_url], ["获取时间", source.retrieved_at || value.retrieved_at],
      ["缺失数据记录", missing],
      ["完整性检查", value.calendar_coverage || (kind === "intake" && value.can_save === true ? "本次检查允许进入保存确认；未单独记录缺失日清单" : undefined)],
      ["公司行为准入", value.corporate_actions || (kind === "intake" && value.can_save === true ? "本次通过无公司行为窗口检查" : undefined)],
      ["区间外公司行为", value.outside_window_actions], ["未完成日线排除记录", value.excluded_forming_sessions],
      ["来源认证记录", value.source_authentication ?? (value.source_truth_verified === false ? "未获独立认证" : undefined)]];
    return (value.stop_detail?.summary ? `<p>${esc(value.stop_detail.summary)}</p>` : "") + (value.stop_detail?.action ? `<p>下一步：${esc(value.stop_detail.action)}</p>` : "") + pairs(rows) + (kind === "intake" ? '<p class="section-note">当前导入只允许完整日线和无公司行为窗口；价格口径以保存后的记录为准。检查通过不等于来源认证。</p>' : "")
      + `<details><summary>查看检查依据与保存身份</summary>${pairs([["原始状态",value.status],["原因",value.reason || value.reasons],["检查详情",value.stop_detail],["限制",value.limitations],["检查身份",value.check_hash],["行情身份",value.input_id],["原始来源校验值",source.raw_sha256 || value.raw_sha256],["本地保存身份",value.id]])}</details>`;
  }
  let instance = 0;
  function installTerminalDailyUI({host, api, perform, notify = () => {}, onInputImported, onUseTeaching, allowPublicDataRequest = false}) {
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
      <style>.terminal-daily-ui button,.terminal-daily-ui select,.terminal-daily-ui summary{min-height:44px}.terminal-daily-ui [data-role="history-host"] select{max-width:100%;width:100%}.terminal-daily-ui [data-role="history-host"] p{overflow-wrap:anywhere}</style>
      <div class="panel-head"><h2>股票日线资料</h2><button class="btn" type="button" data-do="refresh">重新读取已保存资料</button></div>
      <div class="panel-body"><p class="section-note" data-role="mode"></p><p class="section-note">可以选用本机已经保存的行情，或明确检查新的公开日线；没有合格资料时，可先使用虚构教学示例。</p>
      <section class="daily-section" aria-label="选用本机已保存行情"><h3>选用本机已保存行情</h3><p class="section-note">无需准备 SDK 文件。先查找旧工作区，核对证券和历史日期，再单独确认复制。原资料保留；不获取新行情，不运行研究。支持已通过原合同校验的行情快照，最多 8 MiB。</p>
      <div class="actions"><button class="btn" type="button" data-do="history-discover">查找本机已保存资料</button><button class="btn" type="button" data-do="history-requests">找回复制记录</button><button class="btn" type="button" data-do="history-teaching">返回首页使用教学示例</button></div><div data-role="history-host"></div></section>
      <h3 class="daily-section">检查新的公开日线</h3><p class="section-note">1 检查行情 → 2 确认证券并保存 → 3 按需检查更新。保存资料后再选择研究，不会自动运行。</p>
      <p class="section-note" data-role="access"></p><button class="btn" type="button" data-do="revoke">停止获取公开行情</button>
      <p class="daily-status" role="status" aria-live="polite" aria-atomic="true" data-role="status"></p><p role="alert" data-role="error" hidden></p>
      <form data-role="form"><div class="form-grid"><label class="field" for="${uid}-symbol">股票代码<input id="${uid}-symbol" name="symbol" placeholder="例如 NDAQ" maxlength="12" autocomplete="off" spellcheck="false" required></label>
      <div class="field"><label for="${uid}-sessions">历史交易日</label><select id="${uid}-sessions" name="history_sessions"><option value="20">20 个交易日</option><option value="60">60 个交易日</option><option value="120" selected>120 个交易日</option></select></div></div>
      <p class="section-note">默认 120 个交易日，为原策略通常至少 82 日的准备与执行窗口留出余量；具体可评分区间仍需核对。</p><button class="btn primary" type="submit" data-do="check-stock">检查股票行情</button></form>
      <div class="daily-section"><h3>检查记录</h3><div data-role="intakes" class="daily-list"></div><div data-role="intake"></div>
      <label data-role="confirm-wrap" hidden><input type="checkbox" data-do="confirm">我已核对以上证券身份、交易所和币种，确认为要研究的证券</label><button type="button" class="btn primary" data-do="save" hidden>确认证券并保存行情</button>
      <details data-role="supplement-advanced" hidden><summary>高级：使用已取得的来源原件补证</summary><p class="section-note">此路径供已经通过获准采集流程取得证券资料和公司行为查询请求、响应的人使用；截图、随手填写的 JSON 或其他股票资料不能代替原件。没有这些材料，可先选用本机已保存行情，或返回首页使用虚构示例。公司行为和来源未知仍保持未知。</p><div data-role="supplement-host"></div></details></div>
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
    const historyController=createHistoryInputController({api,perform,changed:()=>render(),acceptInput:input=>{
      state.inputs=[input,...state.inputs.filter(item=>item.id!==input.id)];state.input=input;
      say("已复制并选中这份已保存行情。它仍是原历史区间和原来源等级；没有运行研究。");render();
    }});
    function renderHistory(){
      const h=historyController.state,container=role("history-host"),active=document.activeElement;
      const focus=container.contains(active)?active.dataset.historyRole:null;
      const locked=state.busy||!!state.pending||state.importing||h.busy||!!h.pending;
      const busy=locked||h.reading,selected=h.selected;
      const receiptLabels={COMPLETED:"已复制保存",PENDING:"待核对",STOPPED:"已停止",NOT_RECORDED:"未找到记录"};
      container.innerHTML=`<p aria-live="polite">${esc(h.message===h.receipt?.message?"":h.message)}</p><p data-history-role="error" aria-live="assertive" ${h.error?"":"hidden"}>${esc(h.error)}</p>
        ${h.workspaces.length?`<label for="${uid}-history-workspace">旧工作区<select id="${uid}-history-workspace" data-history-role="workspace" ${busy?"disabled":""}><option value="">请选择旧工作区</option>${h.workspaces.map(item=>`<option value="${esc(item.id)}" ${item.id===h.workspaceId?"selected":""}>${esc(item.label||"已知旧工作区")}</option>`).join("")}</select></label>`:""}
        ${h.workspaceId?`<label for="${uid}-history-input">原工作区中的已保存行情<select id="${uid}-history-input" data-history-role="input" ${busy?"disabled":""}><option value="">请选择要复制的行情</option>${h.inputs.map(item=>`<option value="${esc(item.id)}" ${item.id===selected?.id?"selected":""} ${historyInput(item)?"":"disabled"}>${esc(item.security?.symbol||item.label||"未核验资料")} · ${esc(item.coverage_start||"日期未记录")} 至 ${esc(item.coverage_end||"日期未记录")} · ${esc(item.sessions??"?")} 日${historyInput(item)?"":" · 暂不可复制"}</option>`).join("")}</select></label>`:""}
        ${selected?`<div data-history-role="source"><h4>${esc(selected.security.symbol)} · 原历史资料</h4>${pairs([["股票",selected.security.symbol],["交易所",selected.security.exchange],["币种",selected.security.currency],["保存区间",selected.coverage_start+" 至 "+selected.coverage_end],["完整交易日",selected.sessions],["来源",selected.source?.name]])}<p class="section-note">${selected.evidence_kind==="SYNTHETIC_TEST"?"这份原资料是虚构教学数据。":"这份资料保留原导入来源声明，未获得独立真实性认证。"}只使用已保存日期，不补成今天的行情。</p>${selected.sessions<82?`<p class="section-note">这份资料只有 ${esc(selected.sessions)} 个交易日。原九策略通常至少需要 82 个，长周期需要更多；本步只保存和查看，不能据此开始原九策略研究。</p>`:""}<details><summary>查看原资料身份和适用限制</summary>${facts(selected,"input")}</details>
          ${!h.recoveryChecked?'<p class="section-note">原复制记录尚未完整核对；请先点击“找回复制记录”，避免重复保存。</p>':""}<label><input type="checkbox" data-history-role="confirm" ${h.confirmed?"checked":""} ${busy||!h.recoveryChecked?"disabled":""}>我已核对证券、日期和来源限制，确认复制到当前工作区；保留原件，不获取新行情或运行研究</label><button type="button" class="btn primary" data-do="history-copy" ${!h.confirmed||busy||!h.recoveryChecked?"disabled":""}>确认复制并选用</button></div>`:""}
        ${h.pending?`<p>原复制编号：${esc(h.pending.payload.operation_id)}</p><button type="button" class="btn" data-do="history-query" ${h.busy||h.reading?"disabled":""}>查询这次复制结果</button>`:""}
        ${h.receipt?`<p data-history-role="receipt">${esc(receiptLabels[h.receipt.status]||"待核对")}：${esc(h.receipt.message||h.message)}${h.receipt.status==="COMPLETED"?" 原回执说明当时保存结果，不表示旧来源现在仍相同。":""}</p>`:""}
        ${h.requests.length?`<h4>已记录的复制请求</h4><div class="daily-list">${h.requests.map(item=>`<button type="button" class="btn" data-history-query="${esc(item.operation_id)}" ${h.busy||h.reading||(h.pending&&h.pending.payload.operation_id!==item.operation_id)?"disabled":""}>${esc(item.source?.security?.symbol||"原资料")} · ${esc(receiptLabels[item.status]||"待核对")} · 查看并核对副本</button>`).join("")}</div>`:""}`;
      if(focus){const current=container.querySelector(`[data-history-role="${focus}"]`);if(current&&!current.disabled)current.focus({preventScroll:true});}
      for(const name of ["history-discover","history-requests"])action(name).disabled=h.busy||h.reading;
    }
    const supplementUI = typeof root.installTerminalStockSupplementUI === "function" ? root.installTerminalStockSupplementUI({host:role("supplement-host"),api,perform,notify,
      onInputSaved:input => {
        if (!canonical(input) || input.record_resource !== PREFIX + "inputs" || input.kind !== "PRICE_SNAPSHOT" || input.status !== "READY") throw Error("补证新输入的保存身份不完整。");
        state.inputs = [input,...state.inputs.filter(item => item.id !== input.id)]; state.input = input;
        say("补证新输入已保存并选中。可另行复用到原策略研究；原失败记录保持不变，尚未运行策略。"); render();
      }}) : null;
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
      const locked = state.busy || !!state.pending || state.importing || historyController.state.busy || !!historyController.state.pending;
      view.setAttribute("aria-busy", String(state.busy || state.importing || historyController.state.busy));
      role("mode").textContent = allowPublicDataRequest === true ? "每次点击检查，只向 Yahoo Finance 获取一次公开日线；不在后台获取、不自动重试。" : "当前离线：联网检查未启用，仍可读取已保存资料和已有检查记录。";
      role("access").textContent = (state.access?gateStates[state.access.state]+"。会话实际外部请求："+(Number.isSafeInteger(state.access.actual_attempts)?state.access.actual_attempts:"未记录")+" 次。":"许可状态尚未读取。")+(state.requestAttempts!==null?" 最近一次检查实际外部请求："+state.requestAttempts+" 次。":"");
      action("revoke").disabled=state.revoking;action("revoke").hidden=allowPublicDataRequest!==true;
      role("status").textContent = state.message;
      role("error").textContent = [state.error,state.accessError, ...state.warnings].filter(Boolean).join("\n"); role("error").hidden = !role("error").textContent;
      action("check-stock").disabled = locked || state.revoking || allowPublicDataRequest !== true;
      get('[name="symbol"]').disabled = state.busy; get('[name="history_sessions"]').disabled = state.busy;
      renderList("intakes",state.intake); renderList("inputs",state.input); renderList("updates",state.update);
      role("intake").innerHTML = state.intake ? `<h4>${esc(statusText(state.intake))}</h4>` + facts(state.intake,"intake") : "";
      supplementUI?.setContext(state.intake?.reason === "SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN" ? state.intake : null);
      role("supplement-advanced").hidden=state.intake?.reason!=="SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN";
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
      renderHistory();
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
      if (state.busy || state.pending || state.importing || state.revoking || historyController.state.busy || historyController.state.pending) return;
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
      if(event.target.dataset.historyRole){
        const name=event.target.dataset.historyRole;
        try{if(name==="workspace"&&event.target.value)void historyController.selectWorkspace(event.target.value).catch(error=>{historyController.state.error=error.message;render();});
          if(name==="input"&&event.target.value)historyController.selectInput(event.target.value);
          if(name==="confirm")historyController.confirm(event.target.checked);
        }catch(error){historyController.state.error=error.message;render();}
        return;
      }
      if (event.target === action("confirm")) { state.confirmed = event.target.checked; render(); }
      if (event.target === action("revisions")) { state.revisions = event.target.checked; render(); }
    });
    view.addEventListener("click",async event => {
      const button = event.target.closest("button");
      if (!button || !view.contains(button) || button.disabled) return;
      if(button.dataset.historyQuery){await historyController.query(button.dataset.historyQuery);return;}
      if(button.dataset.do?.startsWith("history-")){
        try{const kind=button.dataset.do;
          if(kind==="history-discover")await historyController.discover();
          if(kind==="history-requests")await historyController.readRequests();
          if(kind==="history-copy")await historyController.copySelected();
          if(kind==="history-query")await historyController.query();
          if(kind==="history-teaching"){if(typeof onUseTeaching==="function")await onUseTeaching();else {say("请返回研究首页，点击“用示例体验一次”；这里没有准备或运行任何示例。");render();}}
        }catch(error){historyController.state.error=error?.info?.message||error.message;render();}
        return;
      }
      if (button.dataset.open) {
        if (state.busy || state.importing || historyController.state.busy) return;
        const kind = button.dataset.open, value = state[kind]?.find(item => item.id === button.dataset.id);
        if (value) { state[{inputs:"input",intakes:"intake",updates:"update"}[kind]] = value; state.confirmed = false; state.revisions = false; render(); }
        return;
      }
      const name = button.dataset.do;
      if (name === "refresh") return refresh();
      if (name === "revoke") return revokeUnused();
      if (state.busy || state.pending || state.importing || historyController.state.busy || historyController.state.pending) return;
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
    return {refresh,revokeUnused,historyController,hide:async()=>{view.hidden=true;return revokeUnused();},reveal:async () => { view.hidden = false; await refresh(); return view; }};
  }
  root.installTerminalDailyUI = installTerminalDailyUI;
  if (typeof module === "object" && module.exports) module.exports = {installTerminalDailyUI,createHistoryInputController};
})(typeof globalThis !== "undefined" ? globalThis : this);
