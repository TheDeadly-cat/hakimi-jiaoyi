/* Same-window OFFLINE broker candidates. No client, SDK, or automatic action. */
(function(root){
  "use strict";
  const schema="hakimi-broker-candidate-v2",modes={OFFICIAL_SIMULATION:"官方模拟候选（未连接）",LIVE_CANDIDATE:"实盘候选（未连接）"};
  const permissionKeys=["external_connection_allowed","submit_allowed","query_allowed","cancel_allowed","unlock_allowed","adapter_installed","automatic_resume","automatic_retry"];
  const plain=v=>Boolean(v&&typeof v==="object"&&!Array.isArray(v)),copy=v=>JSON.parse(JSON.stringify(v));
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safe=v=>plain(v)&&permissionKeys.every(key=>v[key]===false),hash=v=>typeof v==="string"&&/^[a-f0-9]{64}$/.test(v);
  const ref=v=>plain(v)&&typeof v.id==="string"&&({terminal_run:/^[a-f0-9]{64}$/,core_run:/^[a-f0-9]{24}$/}[v.kind]?.test(v.id)===true);
  const same=(a,b)=>a?.kind===b?.kind&&a?.id===b?.id;
  const path=(resource,value)=>resource+"/"+encodeURIComponent(JSON.stringify(value));
  const message=e=>String(e?.message||e||"资料读取未完成");
  const actions={terminal_broker_save_candidate:"save",terminal_broker_prepare_intent:"prepare_intent",terminal_broker_stop:"stop",terminal_broker_resume:"resume"};
  const blockerLabels={CANDIDATE_STOPPED:"候选已停止，请先核对停止记录",CANDIDATE_EXPIRED:"候选已过期，请明确填写新的失效时间",MARKET_CURRENCY_MISMATCH:"市场与币种不一致",MARKET_ASSET_MISMATCH:"证券代码与市场不一致",QUANTITY_EXCEEDS_CANDIDATE_LIMIT:"本次数量超过单笔数量上限",NOTIONAL_EXCEEDS_CANDIDATE_LIMIT:"本次金额超过单笔金额上限",RESEARCH_CURRENCY_MISMATCH:"币种与保存研究不一致",RESEARCH_MARKET_MISMATCH:"市场与保存研究不一致",RESEARCH_ASSET_CODE_MISMATCH:"证券代码与保存研究不一致",RESEARCH_SECURITY_IDENTITY_MISMATCH:"保存研究的证券身份不一致",SAVED_RESEARCH_MARKET_MAPPING_UNSUPPORTED:"这份保存研究的市场暂不支持候选映射"};
  const names={account_id:"候选账户编号",market:"市场",asset_code:"证券代码",max_quantity:"单笔数量上限",max_notional:"单笔金额上限",side:"方向",quantity:"本次数量",limit_price:"限价",expires_at:"失效时间"};
  function configFromForm(form,now=Date.now()){
    const config={asset_class:"EQUITY",time_in_force:"DAY"};
    for(const key of Object.keys(names)){
      const value=String(form[key]??"").trim();if(!value)continue;
      if(key==="account_id"&&(!/^[1-9][0-9]{0,19}$/.test(value)||BigInt(value)>=2n**64n))throw Error("请填写有效的候选账户编号；不会据此查询或验证账户。");
      if(key==="market"&&!['US','HK'].includes(value))throw Error("请选择市场。");
      if(key==="asset_code"&&!/^(?:US\.[A-Z][A-Z0-9.-]{0,19}|HK\.[0-9]{5})$/.test(value))throw Error("请明确填写完整证券代码，例如 US.AAPL。");
      if(key==="side"&&!['BUY','SELL'].includes(value))throw Error("请明确选择买入或卖出。");
      if(["quantity","max_quantity"].includes(key)){const n=Number(value);if(!/^[1-9]\d*$/.test(value)||!Number.isSafeInteger(n)||n>1000000)throw Error(names[key]+"须为 1 至 1000000 的整数。");config[key]=n;continue;}
      if(["limit_price","max_notional"].includes(key)&&(!/^(?:0|[1-9]\d{0,11})(?:\.\d{1,8})?$/.test(value)||Number(value)<=0||Number(value)>1e12))throw Error(names[key]+"须为有效的正金额。");
      if(key==="expires_at"){const date=new Date(value);if(!Number.isFinite(date.getTime())||date.getTime()<=now||date.getTime()>now+86400000)throw Error("请明确填写未来 24 小时内的候选失效时间。");config[key]=date.toISOString();continue;}
      config[key]=value;
    }
    if(config.market)config.currency=config.market==="US"?"USD":"HKD";
    return config;
  }
  function createController({api,perform,stopCandidate,readResearch,uuid=()=>root.crypto.randomUUID(),changed=()=>{}}){
    const state={mode:"",sources:[],reference:null,research:null,status:null,statusStale:true,form:{},formEpoch:0,configId:null,savedStamp:null,check:null,
      busy:false,stopping:false,pending:null,controlPending:null,fact:null,controlFact:null,preparedConfigId:null,lastPreparedIntent:null,error:"",readError:"",receipts:[]};
    let sourceSeq=0,statusSeq=0,checkSeq=0,historySeq=0;
    const emit=()=>{try{changed(state);}catch(_){state.readError="页面展示未完成；已保存事实和原请求仍保留。";}};
    const request=()=>"broker-candidate-"+uuid();
    const idle=()=>{if(state.busy||state.pending||state.controlPending)throw Error("请先核对原请求，不能再次提交或切换候选。");};
    const selected=()=>{if(!modes[state.mode])throw Error("请明确选择候选模式。");return state.mode;};
    const modeView=()=>state.status?.modes.find(row=>row.mode===state.mode);
    const stamp=()=>JSON.stringify({mode:state.mode,reference:state.reference,form:state.form});
    function invalidate(){checkSeq++;state.check=null;}
    function setSources(items){state.sources=(items||[]).filter(v=>ref(v)&&(!v.status||v.status==="COMPLETED")).map(v=>({kind:v.kind,id:v.id,label:String(v.label||"已保存研究结果")}));emit();}
    function setMode(mode){idle();if(mode!==""&&!modes[mode])throw Error("请选择候选模式。");if(mode!==state.mode){state.mode=mode;state.form={};state.formEpoch++;state.configId=null;state.savedStamp=null;state.fact=null;state.controlFact=null;state.receipts=[];invalidate();}emit();}
    function setForm(form){idle();state.form=copy(form);invalidate();emit();}
    async function openResearch(reference){
      idle();const seq=++sourceSeq;state.reference=reference&&ref(reference)?{kind:reference.kind,id:reference.id}:null;state.research=null;state.configId=null;state.savedStamp=null;invalidate();emit();
      if(!state.reference)return;
      const wanted=copy(state.reference);
      try{const value=await (readResearch?readResearch(wanted):api(path("terminal_broker_research",{reference:wanted})));
        if(seq!==sourceSeq||!same(wanted,state.reference))return;
        if(!same(value?.reference,wanted)||value?.binding?.status!=="COMPLETED"||!hash(value?.binding?.report_hash)||!safe(value.permissions)||(wanted.kind==='terminal_run'&&(value.binding.report_id!==wanted.id||value.binding.report_hash!==wanted.id)))throw Error("保存研究的身份或候选权限未通过核对。");
        state.research=value;state.readError="";emit();return value;
      }catch(error){if(seq===sourceSeq){state.readError="保存研究读取未完成："+message(error);emit();}}
    }
    async function refresh(){
      const seq=++statusSeq;state.statusStale=true;emit();
      try{const value=await api("terminal_broker_status");if(seq!==statusSeq)return;
        if(value?.schema_version!==schema||value.connection_state!=="NOT_CONNECTED"||!safe(value.permissions)||!Array.isArray(value.modes)||value.modes.length!==2||new Set(value.modes.map(v=>v.mode)).size!==2||value.modes.some(v=>!modes[v.mode]||v.connected!==false||!safe(v.permissions)||!plain(v.control)))throw Error("候选状态或关闭权限未通过核对。");
        state.status=value;state.statusStale=false;emit();return value;
      }catch(error){if(seq===statusSeq){state.readError="状态读取未完成："+message(error);emit();}}
    }
    function accept(value,operation,receipt){
      const p=operation.payload,action=operation.action;
      if(!plain(value)||value.mode!==p.mode||!safe(value.permissions))throw Error("返回的候选模式或权限不一致。");
      if(action==="terminal_broker_save_candidate"){
        if(value.status!=="SAVED_OFFLINE_CANDIDATE"||!hash(value.config_id))throw Error("未取得完整的候选保存结果。");
        state.configId=value.config_id;state.savedStamp=operation.stamp;state.fact={message:"候选资料已保存；尚未保存或发送订单意图。",requestId:p.request_id,id:value.config_id,mode:p.mode};
      }else if(action==="terminal_broker_prepare_intent"){
        if(value.status!=="UNSENT_OFFLINE_PREVIEW"||value.intent?.status!=="UNSENT_OFFLINE_PREVIEW"||value.intent.mode!==p.mode||value.intent.request_id!==p.request_id||value.intent.config_id!==p.config_id||!hash(value.intent.id)||!safe(value.intent.permissions))throw Error("未取得与原请求一致的未发送意图。");
        state.fact={message:"未发送意图已保存；没有连接券商或提交订单。",requestId:p.request_id,id:value.intent.id,mode:p.mode};
        state.preparedConfigId=p.config_id;
        state.lastPreparedIntent=copy(value.intent);
      }else{
        const stopping=action==="terminal_broker_stop",id=receipt?.id||value.control_receipt_id;
        if(value.status!==(stopping?"STOPPED":"OFFLINE_PREPARATION_RESUMED")||!hash(id)||value.new_intents_blocked!==stopping||value.broker_orders_cancelled!==false||(!stopping&&value.resumed_stop_receipt_id!==p.expected_stop_receipt_id))throw Error("未取得与原控制请求一致的回执。");
        const row=state.status?.modes.find(v=>v.mode===p.mode);
        if(row)row.control={...row.control,new_intents_blocked:stopping,latest_control_receipt_id:id,latest_stop_receipt_id:stopping?(receipt?.id||value.stop_receipt_id):p.expected_stop_receipt_id,resume_allowed:stopping};
        state.controlFact={message:stopping?"已停止准备新意图；未撤销任何券商挂单。":"已恢复离线准备；没有恢复任何外部权限，请重新检查资料。",requestId:p.request_id,id,mode:p.mode};invalidate();
      }
      statusSeq++;state.statusStale=true;
      if(operation.lane==="control")state.controlPending=null;else state.pending=null;
      state.error="";emit();return value;
    }
    async function execute(action,payload,{direct=false,operationStamp=stamp()}={}){
      if(direct){if(state.stopping||state.controlPending)throw Error("请先查询原停止请求。");if(typeof stopCandidate!=="function")throw Error("独立停止入口尚未配置，不能假定已经停止。");}
      else idle();
      const operation={action,payload:copy(payload),stamp:operationStamp,lane:direct?"control":"normal"};
      if(direct){state.controlPending=operation;state.stopping=true;}else{state.pending=operation;state.busy=true;}
      state.error="";state.readError="";let acknowledged=null;emit();
      const receive=value=>{if(acknowledged)return acknowledged;acknowledged=accept(value,operation);return acknowledged;};
      try{const value=direct?await stopCandidate(copy(payload)):await perform(action,copy(payload),{onSuccess:receive});if(value&&!acknowledged)receive(value);
        if(!acknowledged)state.error="结果尚未确认。保留原请求，只能查询回执，不能自动重试。";
      }catch(error){if(acknowledged)state.readError="保存结果已确认，后续读取未完成："+message(error);else state.error="结果尚未确认："+message(error)+"。请查询原请求回执。";}
      finally{if(direct)state.stopping=false;else state.busy=false;emit();}
      if(acknowledged)await refresh();return acknowledged;
    }
    async function loadCheck(){
      const mode=selected(),id=state.configId,wanted=stamp(),seq=++checkSeq;
      if(!hash(id)||state.savedStamp!==wanted)throw Error("资料已变化，请先检查并暂存当前候选。");
      try{const value=await api(path("terminal_broker_check",{mode,config_id:id}));
        if(seq!==checkSeq||state.mode!==mode||state.configId!==id||stamp()!==wanted)return;
        if(value?.mode!==mode||value.config_id!==id||!safe(value.permissions)||value.connected!==false||value.account_verified!==false||value.asset_rules_verified!==false||value.fee_verified!==false||!Array.isArray(value.missing)||!Array.isArray(value.blockers)||!['MISSING','BLOCKED','OFFLINE_PREVIEW_ONLY'].includes(value.status)||(value.status==='OFFLINE_PREVIEW_ONLY'&&(value.missing.length||value.blockers.length||value.security_binding?.status!=="MATCHED_SAVED_DECLARATION")))throw Error("检查结果与当前候选不一致。");
        state.check={...value,stamp:wanted};emit();return value;
      }catch(error){if(seq===checkSeq){state.readError="候选已保存，但检查资料读取未完成："+message(error);emit();}}
    }
    async function check(form){
      idle();selected();if(!state.research||!same(state.research.reference,state.reference))throw Error("请先选择并读取一份已完成的保存研究。");
      state.form=copy(form);invalidate();const wanted=stamp();
      if(state.savedStamp!==wanted||!state.configId){const result=await execute("terminal_broker_save_candidate",{mode:state.mode,request_id:request(),config:configFromForm(form),research_reference:copy(state.reference)},{operationStamp:wanted});if(!result)return;}
      return loadCheck();
    }
    async function prepareIntent(confirmed){
      idle();const mode=selected(),control=modeView()?.control;
      if(confirmed!==true)throw Error("请确认只保存本地未发送意图。");
      if(state.preparedConfigId&&state.preparedConfigId===state.configId)throw Error("这份候选已保存未发送意图，请查看原保存记录；修改资料后再明确检查新候选。");
      if(state.statusStale||control?.new_intents_blocked!==false||state.check?.status!=="OFFLINE_PREVIEW_ONLY"||state.check.stamp!==stamp()||state.check.config_id!==state.configId)throw Error("资料或停止状态已变化，请重新读取并检查。");
      return execute("terminal_broker_prepare_intent",{mode,request_id:request(),config_id:state.configId});
    }
    async function stop(reason){const mode=selected();if(!String(reason||"").trim()||String(reason).trim().length>200)throw Error("请填写 1 至 200 字的停止原因。");return execute("terminal_broker_stop",{mode,request_id:request(),reason:String(reason).trim()},{direct:true});}
    async function resume(reason,confirmed,expectedStopReceiptId){
      idle();const mode=selected(),control=modeView()?.control;
      if(confirmed!==true||!String(reason||"").trim()||String(reason).trim().length>200)throw Error("请填写 1 至 200 字的恢复原因，并确认仅恢复离线准备。");
      if(state.statusStale||control?.resume_allowed!==true||!hash(expectedStopReceiptId)||control.latest_stop_receipt_id!==expectedStopReceiptId)throw Error("请重新读取并核对最近的停止记录。");
      return execute("terminal_broker_resume",{mode,request_id:request(),expected_stop_receipt_id:expectedStopReceiptId,reason:String(reason).trim()});
    }
    async function queryPending(lane="normal"){
      const operation=lane==="control"?state.controlPending:state.pending;if(!operation)return;
      const p=operation.payload;
      try{const value=await api(path("terminal_broker_receipt",{mode:p.mode,request_id:p.request_id}));
        if((lane==="control"?state.controlPending:state.pending)!==operation)return;
        if(value?.mode!==p.mode||value.request_id!==p.request_id||!safe(value.permissions)||value.retry_allowed!==false)throw Error("原请求回执身份不一致。");
        if(value.status==="NOT_RECORDED"){state.error="当前未见原请求回执，不代表未处理；仍保留原编号，只能继续查询。";emit();return;}
        const receipt=value.receipt;
        if(value.status!=="FOUND"||receipt?.mode!==p.mode||receipt.request_id!==p.request_id||receipt.action!==actions[operation.action]||!hash(receipt.id))throw Error("查询到的回执不属于原请求。");
        accept(receipt.result,operation,receipt);await refresh();
      }catch(error){state.readError="原回执读取未完成："+message(error);emit();}
    }
    async function readReceipts(){const mode=selected(),seq=++historySeq;try{const value=await api("terminal_broker_receipts/"+mode);if(seq!==historySeq||mode!==state.mode)return;if(value?.mode!==mode||!safe(value.permissions)||!Array.isArray(value.items)||value.items.some(row=>row.mode!==mode||row.result?.mode!==mode||!safe(row.result?.permissions)))throw Error("保存记录模式或权限不一致。");state.receipts=value.items;emit();}catch(error){state.readError="保存记录读取未完成："+message(error);emit();}}
    return {state,setSources,setMode,setForm,openResearch,refresh,check,loadCheck,prepareIntent,stop,resume,queryPending,readReceipts};
  }
  // Installation alone performs no reads; reveal() is explicitly read-only.
  function installTerminalBrokerCandidateUI({host,api,perform,stopCandidate,readResearch,notify=()=>{},onBack}){
    const document=host.ownerDocument,view=document.createElement("section");view.id="terminalBrokerCandidateWorkspace";view.className="tbc section-gap";view.hidden=true;
    const field=(key,label,type="text",extra="")=>`<div class="field"><label for="tbc-${key}">${label}</label><input id="tbc-${key}" name="${key}" type="${type}" ${extra}></div>`;
    view.innerHTML=`<div class="page-heading"><div><h2>检查券商候选资料</h2><p>官方模拟候选与实盘候选均未连接；它们与本地合成演练相互独立。</p></div><div class="actions">${typeof onBack==="function"?'<button class="btn" data-tbc-action="back" type="button">返回本地演练</button>':""}<button class="btn" data-tbc-action="refresh" type="button">重新读取</button><button class="btn" data-tbc-action="stop" type="button">停止准备新意图</button></div></div>
      <div id="tbc-fact" class="notice section-gap" role="status" hidden></div><div id="tbc-control-fact" class="notice section-gap" role="status" hidden></div><div id="tbc-error" class="notice warning section-gap" role="status" hidden></div><div id="tbc-read-error" class="notice warning section-gap" role="status" hidden></div>
      <section class="panel"><div class="panel-head"><h3>1 · 选择保存研究与候选模式</h3></div><div class="panel-body"><div class="form-grid"><div class="field"><label for="tbc-source">已完成的保存研究</label><select id="tbc-source"><option value="">请选择</option></select></div><div class="field"><label for="tbc-mode">候选模式</label><select id="tbc-mode"><option value="">请明确选择</option>${Object.entries(modes).map(([value,label])=>`<option value="${value}">${label}</option>`).join("")}</select></div></div><div id="tbc-research" class="section-gap">选择后只读取保存身份，不重新回测。</div><p id="tbc-state" class="section-note">未连接券商，所有外部权限关闭。</p></div></section>
      <section class="panel section-gap"><div class="panel-head"><h3>2 · 填写候选账户、证券与限额</h3></div><div class="panel-body"><form id="tbc-form"><p>仅股票、当日有效限价候选。账户与证券由你明确填写，不会查询余额、持仓或交易权限。</p><div class="form-grid">
      ${field("account_id","候选账户编号","text","inputmode=numeric autocomplete=off")}
      <div class="field"><label for="tbc-market">市场与币种</label><select id="tbc-market" name="market"><option value="">请选择</option><option value="US">美股 · 美元（US / USD）</option><option value="HK">港股 · 港元（HK / HKD）</option></select></div>
      ${field("asset_code","完整证券代码","text","placeholder='例如 US.AAPL' autocomplete=off")}${field("max_quantity","单笔数量上限（整股）","number","min=1 step=1")}${field("max_notional","单笔金额上限（所选币种）","number","min=0.00000001 step=any")}
      <div class="field"><label for="tbc-side">本次方向 · 由你决定</label><select id="tbc-side" name="side"><option value="">请明确选择</option><option value="BUY">买入候选</option><option value="SELL">卖出候选</option></select></div>
      ${field("quantity","本次数量（整股）","number","min=1 step=1")}${field("limit_price","本次限价（所选币种）","number","min=0.00000001 step=any")}${field("expires_at","候选失效时间（本地时间，24 小时内）","datetime-local")}</div><p class="section-note">点击检查会暂存这份本地候选资料；不会连接券商，也不会保存或发送订单意图。缺项将逐一列出。</p><button id="tbc-check" class="btn primary" type="submit">检查并暂存候选资料</button></form><div id="tbc-check-result" class="section-gap"></div>
      <form id="tbc-intent-form" class="section-gap" hidden><label class="tbc-confirm"><input id="tbc-confirm-intent" type="checkbox">我确认只保存本地未发送意图；账户、费用、持仓与外部权限均未经券商验证。</label><button id="tbc-prepare" class="btn primary" type="submit">确认保存未发送意图</button></form></div></section>
      <div id="tbc-plan-host"></div><section class="panel section-gap"><div class="panel-head"><h3>停止与恢复本模式的意图准备</h3></div><div class="panel-body"><p>停止直接生效于后续离线准备，不等待普通任务队列，也不表示撤销券商挂单。</p><div class="field"><label for="tbc-stop-reason">停止备注（可选）</label><input id="tbc-stop-reason" maxlength="200"></div><button class="btn" data-tbc-action="stop" type="button">停止准备新意图</button>
      <details class="section-gap"><summary>手动恢复离线准备</summary><p id="tbc-resume-context">先读取并核对最近一次停止记录。</p><div class="field"><label for="tbc-resume-reason">本次恢复原因</label><input id="tbc-resume-reason" maxlength="200"></div><label class="tbc-confirm"><input id="tbc-confirm-resume" type="checkbox">只恢复离线准备；不连接、不解锁、不下单，过期资料仍需重新填写。</label><button class="btn" data-tbc-action="resume" type="button">确认恢复离线准备</button></details></div></section>
      <details class="section-gap"><summary>保存记录与完整身份</summary><button class="btn" data-tbc-action="receipts" type="button">读取本模式保存记录</button><div id="tbc-history"></div><div id="tbc-diagnostics"></div></details>`;
    const style=document.createElement("style");style.textContent=".tbc [hidden]{display:none!important}.tbc{min-width:0}.tbc .notice,.tbc dd,.tbc li{overflow-wrap:anywhere}.tbc summary,.tbc button,.tbc select,.tbc input:not([type=checkbox]){min-height:44px}.tbc summary{cursor:pointer;align-content:center}.tbc dd{margin-left:0}.tbc .tbc-confirm{display:flex;align-items:flex-start;gap:10px;margin:16px 0}.tbc .tbc-confirm input{flex:none;margin-top:4px}.tbc [data-tbc-action=stop]{border-color:#a44831;color:#8d3420}.tbc details .field{margin-top:12px}@media(max-width:760px){.tbc .form-grid{grid-template-columns:1fr}.tbc .page-heading{align-items:flex-start;flex-direction:column}.tbc button{white-space:normal}}";
    host.appendChild(view);document.head.appendChild(style);
    const $=id=>view.querySelector("#tbc-"+id),form=()=>Object.fromEntries(Object.keys(names).map(key=>[key,$(key).value]));
    let formEpoch=-1,lastCheck=null,lastStop=null;
    const controller=createController({api,perform,stopCandidate,readResearch,changed:render}),state=controller.state;
    const planUI=typeof root.installTerminalBrokerPlanUI==='function'?root.installTerminalBrokerPlanUI({host:$("plan-host"),api,perform,notify}):null;
    const displayFact=(node,fact)=>{node.hidden=!fact;node.innerHTML=fact?`<strong>${esc(fact.message)}</strong><details><summary>查看原模式与完整编号</summary><p>${esc(modes[fact.mode])}</p><p>请求：${esc(fact.requestId)}</p><p>记录：${esc(fact.id)}</p></details>`:"";};
    const pendingIdentity=operation=>operation?`<details><summary>查看待核对请求的原编号</summary><p>${esc(modes[operation.payload.mode])}</p><p>${esc(operation.payload.request_id)}</p></details>`:"";
    function render(){
      const index=state.sources.findIndex(row=>same(row,state.reference));$("source").innerHTML='<option value="">请选择</option>'+state.sources.map((row,i)=>`<option value="${i}">${esc(row.label)}</option>`).join("");$("source").value=index<0?"":String(index);$("mode").value=state.mode;
      if(formEpoch!==state.formEpoch){for(const key of Object.keys(names))$(key).value=state.form[key]??"";$("stop-reason").value="";$("resume-reason").value="";formEpoch=state.formEpoch;}
      const locked=state.busy||!!state.pending||!!state.controlPending;
      for(const node of view.querySelectorAll('#tbc-form input,#tbc-form select,#tbc-source,#tbc-mode'))node.disabled=locked;
      $("check").disabled=locked||!state.mode||!state.research;
      const row=state.status?.modes.find(v=>v.mode===state.mode),control=row?.control;
      let candidateTerms=null;try{candidateTerms=configFromForm(state.form);}catch(_){}
      const currentStamp=JSON.stringify({mode:state.mode,reference:state.reference,form:state.form});
      const matchingIntent=state.savedStamp===currentStamp&&state.lastPreparedIntent?.mode===state.mode&&state.lastPreparedIntent.config_id===state.configId?state.lastPreparedIntent:null;
      planUI?.setContext({mode:state.mode,config_id:state.configId,intent:matchingIntent,candidate_terms:candidateTerms,expected_control_revision:control?.revision??null,
        blocked:locked||state.statusStale||control?.new_intents_blocked!==false});
      if(lastStop!==control?.latest_stop_receipt_id){$("confirm-resume").checked=false;lastStop=control?.latest_stop_receipt_id||null;}
      const research=state.research,d=research?.display||{};
      $("research").innerHTML=research?`<p>保存研究中的证券：${esc(d.symbol||"未记录")} · 币种：${esc({USD:"美元",HKD:"港元"}[d.currency]||d.currency||"未记录")} · 资产类别：${esc({US_EQUITY:"美国股票",EQUITY:"股票"}[d.asset_class]||d.asset_class||"未记录")}</p><p class="section-note">证券身份缺失或候选填写不一致时，不会进入意图保存。</p><details><summary>查看保存研究的完整身份</summary><dl><dt>证券身份</dt><dd>${esc(d.security_id||"未记录")}</dd><dt>研究版本身份</dt><dd>${esc(research.binding.task_version??"未记录")}</dd><dt>报告</dt><dd>${esc(research.binding.report_id)}</dd></dl></details>`:"选择后只读取保存身份，不重新回测。";
      $("state").textContent=(state.mode?modes[state.mode]+" · ":"")+(state.statusStale?"状态待读取；不能据旧状态保存意图。":control?.new_intents_blocked?"本模式当前已停止离线准备；未连接券商。":control?.new_intents_blocked===false?"本模式当前未停止离线准备；未连接券商，所有外部权限关闭。":"未连接券商，所有外部权限关闭。");
      const controlFact=state.controlFact&&state.statusStale?{...state.controlFact,message:"控制请求已有保存回执；当前停止或恢复状态待读取。"}:state.controlFact&&control?.latest_control_receipt_id!==state.controlFact.id?{...state.controlFact,message:"原控制请求已有保存回执；后续控制记录已改变当前状态，请以当前模式状态为准。"}:state.controlFact;
      displayFact($("fact"),state.fact);displayFact($("control-fact"),controlFact);
      $("error").hidden=!state.error&&!state.pending&&!state.controlPending;$("error").innerHTML=esc(state.error)+(state.pending?'<p>保留原请求，不重提。</p><button class="btn" data-tbc-action="query" type="button">查询原请求回执</button>'+pendingIdentity(state.pending):"")+(state.controlPending?'<p>停止结果待核对，不表示已取消任何在途操作。</p><button class="btn" data-tbc-action="query-stop" type="button">查询原停止回执</button>'+pendingIdentity(state.controlPending):"");
      $("read-error").hidden=!state.readError;$("read-error").textContent=state.readError;
      const check=state.check;$("check-result").innerHTML=check?`<h4>${check.status==="OFFLINE_PREVIEW_ONLY"?"本地资料检查完成，仍未连接":check.status==="MISSING"?"请补齐以下资料":"以下问题需先处理"}</h4><ul>${check.missing.map(item=>`<li>未填写或未记录：${esc(item.label)}</li>`).join("")}${check.blockers.map(code=>`<li>${esc(blockerLabels[code]||"候选条件未满足，见完整检查依据")}</li>`).join("")}</ul><p>候选金额（不含费用）：${esc(check.order_notional_excluding_fees??"未记录")} ${esc(state.form.market==="US"?"美元":state.form.market==="HK"?"港元":"")}</p><p>${esc(check.message||"账户、持仓、费用和交易规则未经券商核对。")}</p><details><summary>查看检查的完整依据</summary><p>候选：${esc(check.config_id)}</p><p>证券声明：${esc(check.security_binding?.status||"未记录")}</p><p>${esc(check.blockers.join(" · "))}</p></details>`:"";
      $("intent-form").hidden=check?.status!=="OFFLINE_PREVIEW_ONLY"||state.preparedConfigId===state.configId;$("prepare").disabled=locked||state.statusStale||control?.new_intents_blocked!==false;
      if(lastCheck!==check){$("confirm-intent").checked=false;lastCheck=check;}
      view.querySelectorAll('[data-tbc-action="stop"]').forEach(button=>{button.disabled=!state.mode||state.stopping||!!state.controlPending||typeof stopCandidate!=="function";});
      view.querySelector('[data-tbc-action="resume"]').disabled=locked||state.statusStale||control?.resume_allowed!==true;
      $("resume-context").textContent=control?.resume_allowed?"最近停止记录已读取；恢复只针对这一份停止记录。":"当前没有可确认恢复的停止记录。";
      view.querySelector('[data-tbc-action="receipts"]').disabled=!state.mode;
      $("history").innerHTML=state.receipts.length?`<p>最近 ${Math.min(state.receipts.length,20)} 条，共 ${state.receipts.length} 条本模式记录。</p>`+state.receipts.slice(-20).reverse().map(r=>`<details><summary>${esc({save:"候选资料已保存",prepare_intent:"未发送意图已保存",stop:"停止准备记录",resume:"恢复离线准备记录"}[r.action]||"保存记录")} · ${esc(r.created_at||"时间未记录")}</summary><p>请求：${esc(r.request_id)}</p><p>原记录：${esc(r.id)}</p><p>外部权限仍关闭。</p></details>`).join(""):"";
      $("diagnostics").innerHTML=state.status?`<p>组件元数据：${esc(state.status.sdk?.metadata_status||"未提供")}；运行兼容性：${esc(state.status.sdk?.runtime_compatibility||"未核验")}。没有安装或启用连接适配器。</p>`:"";
    }
    const fail=error=>{state.readError=message(error);render();if(!view.hidden)notify(state.readError);};
    view.addEventListener("change",event=>{const id=event.target.id;if(id==="tbc-mode"){try{controller.setMode(event.target.value);}catch(error){fail(error);}return;}if(id==="tbc-source"){controller.openResearch(event.target.value===""?null:state.sources[Number(event.target.value)]||null).catch(fail);return;}});
    view.addEventListener("input",event=>{if(event.target.closest('#tbc-form')){try{controller.setForm(form());}catch(error){fail(error);}}});
    view.addEventListener("submit",event=>{event.preventDefault();if(event.target.id==="tbc-form")controller.check(form()).catch(fail);if(event.target.id==="tbc-intent-form")controller.prepareIntent($("confirm-intent").checked).catch(fail);});
    view.addEventListener("click",event=>{const action=event.target.closest('[data-tbc-action]')?.dataset.tbcAction;if(!action)return;const operations={back:()=>onBack?.(),refresh:()=>controller.refresh(),stop:()=>controller.stop($("stop-reason").value.trim()||"用户明确点击停止准备新意图"),resume:()=>controller.resume($("resume-reason").value,$("confirm-resume").checked,lastStop),query:()=>controller.queryPending(),"query-stop":()=>controller.queryPending("control"),receipts:()=>controller.readReceipts()};Promise.resolve().then(operations[action]).catch(fail);});
    render();return {controller,element:view,planUI,setSources:controller.setSources,refresh:controller.refresh,reveal:()=>{view.hidden=false;return controller.refresh();},hide:()=>{view.hidden=true;}};
  }
  root.installTerminalBrokerCandidateUI=installTerminalBrokerCandidateUI;
  if(typeof module==="object"&&module.exports)module.exports={createController,install:installTerminalBrokerCandidateUI,configFromForm};
})(typeof globalThis!=="undefined"?globalThis:window);
