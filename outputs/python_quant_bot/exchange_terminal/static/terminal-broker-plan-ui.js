/* Offline acceptance plans only. No SDK, connection, automatic read or retry. */
(function(root){
  "use strict";
  const SCHEMA="hakimi-broker-plan-service-v1",ACTION="terminal_broker_prepare_plan";
  const modes={OFFICIAL_SIMULATION:"官方模拟候选",LIVE_CANDIDATE:"实盘候选"};
  const permissionKeys=["external_connection_allowed","query_allowed","submit_allowed","cancel_allowed","unlock_allowed","automatic_retry","automatic_resume","automatic_mode_fallback","user_authorization_granted"];
  const candidatePermissions=["external_connection_allowed","submit_allowed","query_allowed","cancel_allowed","unlock_allowed","adapter_installed","automatic_resume","automatic_retry"];
  const calls={connect:1,runtime_read:1,account_read:1,position_read:1,security_read:1,quote_read:1,fee_read:1,submit:1,observe:5,cancel:1,unlock:0};
  const payloadKeys=["mode","request_id","config_id","intent_id","expected_control_revision","bounds"];
  const boundKeys=["valid_until","calls","wall_timeout_seconds","call_timeout_seconds","cleanup_timeout_seconds","max_output_bytes","max_observation_records","max_evidence_age_seconds","max_total_fees","endpoint"];
  const defaults={valid_until:"",max_total_fees:"",port:"11111",wall_timeout_seconds:"180",call_timeout_seconds:"15",cleanup_timeout_seconds:"5",max_output_bytes:"131072",max_observation_records:"50",max_evidence_age_seconds:"30",observe:"5",cancel:"1"};
  const plain=v=>!!v&&typeof v==="object"&&!Array.isArray(v),copy=v=>JSON.parse(JSON.stringify(v));
  const hash=v=>typeof v==="string"&&/^[a-f0-9]{64}$/.test(v),requestId=v=>typeof v==="string"&&/^[A-Za-z0-9][A-Za-z0-9_-]{7,119}$/.test(v);
  const exact=(v,keys)=>plain(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
  const closed=(v,keys=permissionKeys)=>exact(v,keys)&&keys.every(k=>v[k]===false);
  const ordered=v=>Array.isArray(v)?v.map(ordered):plain(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])])):v;
  const canonical=v=>JSON.stringify(ordered(v)).replace(/[\u007f-\uffff]/g,c=>"\\u"+c.charCodeAt(0).toString(16).padStart(4,"0"));
  const equal=(a,b)=>canonical(a)===canonical(b);
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const path=(resource,identity)=>resource+"/"+encodeURIComponent(JSON.stringify(identity));
  const errorText=e=>String(e?.info?.message||e?.message||e||"本地读取未完成");
  const require=(value,message)=>{if(!value)throw Error(message);};
  const reasonLabels={NOT_PACKAGED:"当前启动没有绑定已校验的程序包，未创建计划。",PACKAGE_CHANGED:"程序包身份或相关文件已变化，未创建计划。",BOOTSTRAP_ANCHOR_INVALID:"本次程序包初始化身份无效，未创建计划。",candidate_plan_control_changed_or_stopped:"停止或恢复状态已改变，请重新读取并核对。",candidate_incomplete_expired_or_stopped:"候选资料不完整、已过期或已停止，请先核对原候选。"};
  const planStatusLabels={BLOCKED_CAPABILITY:"缺少接入组件",OFFLINE_ONLY_SYNTHETIC_RESEARCH:"合成资料仅限离线",OFFLINE_PLAN_REQUIRES_EVIDENCE:"尚待独立条件核验"};
  async function digest(value){const bytes=new TextEncoder().encode(canonical(value));return [...new Uint8Array(await root.crypto.subtle.digest("SHA-256",bytes))].map(v=>v.toString(16).padStart(2,"0")).join("");}
  async function sealed(value){if(!plain(value)||!hash(value.id))return false;const body={...value};delete body.id;return value.id===await digest(body);}
  function localTime(value){
    if(typeof value!=="string"||!value.trim())return "未记录";
    const date=new Date(value);if(!Number.isFinite(date.getTime()))return "时间无法识别";
    const two=value=>String(value).padStart(2,"0");
    return `${date.getFullYear()}-${two(date.getMonth()+1)}-${two(date.getDate())} ${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`;
  }
  function integer(value,label,min,max){const text=String(value??"");require(/^\d+$/.test(text)&&Number.isSafeInteger(Number(text))&&Number(text)>=min&&Number(text)<=max,`${label}须为 ${min} 至 ${max} 的整数。`);return Number(text);}
  function boundsFromForm(form,expiresAt,now=Date.now()){
    const money=String(form.max_total_fees??"").trim();require(/^(?:0|[1-9]\d{0,11})(?:\.\d{1,8})?$/.test(money)&&Number(money)<=1e12,"请明确填写费用金额上限，可填 0，最多 8 位小数；这不是实际费用或费率。");
    const wall=integer(form.wall_timeout_seconds,"总时限（秒）",1,180),cleanup=integer(form.cleanup_timeout_seconds,"清理时限（秒）",1,5);
    const until=new Date(form.valid_until).getTime(),expiry=new Date(expiresAt).getTime();
    require(Number.isFinite(until)&&Number.isFinite(expiry)&&until-now>=Math.max(185,wall+cleanup)*1000&&until<=expiry,"请明确填写至少 3 分 5 秒后的计划失效时间，且不晚于原候选失效时间。");
    return {valid_until:new Date(until).toISOString(),calls:{...calls,observe:integer(form.observe,"观察调用次数",1,5),cancel:integer(form.cancel,"撤单调用次数",0,1)},
      wall_timeout_seconds:wall,call_timeout_seconds:integer(form.call_timeout_seconds,"单次调用时限（秒）",1,Math.min(30,wall)),cleanup_timeout_seconds:cleanup,
      max_output_bytes:integer(form.max_output_bytes,"输出与原始证据上限（字节）",1,131072),max_observation_records:integer(form.max_observation_records,"最多观察记录数",1,100),
      max_evidence_age_seconds:integer(form.max_evidence_age_seconds,"证据最长有效时间（秒）",1,60),max_total_fees:money,endpoint:{host:"127.0.0.1",port:integer(form.port,"本机端口",1,65535)}};
  }
  function validPayload(p){return exact(p,payloadKeys)&&!!modes[p.mode]&&requestId(p.request_id)&&hash(p.config_id)&&hash(p.intent_id)&&Number.isInteger(p.expected_control_revision)&&p.expected_control_revision>=0&&p.expected_control_revision<=1000
    &&exact(p.bounds,boundKeys)&&exact(p.bounds.calls,Object.keys(calls))&&Object.entries(p.bounds.calls).every(([k,v])=>Number.isInteger(v)&&v>=(k==='cancel'||k==='unlock'?0:1)&&v<=calls[k])
    &&exact(p.bounds.endpoint,['host','port'])&&p.bounds.endpoint.host==='127.0.0.1'&&Number.isInteger(p.bounds.endpoint.port)&&p.bounds.endpoint.port>=1&&p.bounds.endpoint.port<=65535
    &&['wall_timeout_seconds','call_timeout_seconds','cleanup_timeout_seconds','max_output_bytes','max_observation_records','max_evidence_age_seconds'].every(k=>Number.isInteger(p.bounds[k]))
    &&typeof p.bounds.valid_until==='string'&&Number.isFinite(Date.parse(p.bounds.valid_until))&&typeof p.bounds.max_total_fees==='string';}
  function eligibleContext(value){const intent=value?.intent;return !!modes[value?.mode]&&hash(value.config_id)&&plain(intent)&&intent.schema_version==='hakimi-broker-candidate-v2'&&intent.kind==='intents'
    &&intent.mode===value.mode&&intent.config_id===value.config_id&&hash(intent.id)&&requestId(intent.request_id)&&intent.status==='UNSENT_OFFLINE_PREVIEW'&&closed(intent.permissions,candidatePermissions)
    &&plain(intent.terms)&&equal(intent.terms,value.candidate_terms)&&Number.isInteger(value.expected_control_revision)&&value.expected_control_revision>=0&&value.expected_control_revision<=1000;}
  function envelope(value,mode,workspace){require(value?.schema_version===SCHEMA&&value.mode===mode&&hash(value.workspace_context)&&closed(value.permissions)&&(!workspace||workspace===value.workspace_context),"计划回复的模式、工作区或关闭权限与原请求不一致。");return value.workspace_context;}
  function createController({api,perform,uuid=()=>root.crypto.randomUUID(),now=()=>Date.now(),changed=()=>{}}){
    const state={context:null,workspaceContext:null,form:copy(defaults),confirmed:false,confirmationStamp:null,capabilities:null,items:[],requests:[],listScope:null,detail:null,
      pending:null,busy:false,capLoading:false,listLoading:false,detailLoading:false,querying:false,fact:null,error:"",readError:""};
    let contextSequence=0,capSequence=0,listSequence=0,detailSequence=0;
    const emit=()=>{try{changed(state);}catch(_){state.readError="页面展示未完成；已确认的保存事实和原请求仍保留，请只读查询原记录。";}},mode=()=>{require(modes[state.context?.mode],"请先明确选择候选模式。");return state.context.mode;};
    const stamp=()=>canonical({context:state.context,form:state.form,workspace:state.workspaceContext,capabilities:state.capabilities});
    const unconfirm=()=>{state.confirmed=false;state.confirmationStamp=null;};
    function setContext(value){const next=plain(value)?copy(value):null;if(!equal(next,state.context)){contextSequence++;capSequence++;listSequence++;detailSequence++;state.context=next;state.capabilities=null;state.capLoading=false;state.listLoading=false;state.detailLoading=false;state.items=[];state.requests=[];state.listScope=null;state.detail=null;unconfirm();}emit();}
    function setForm(value){state.form={...copy(defaults),...copy(value)};unconfirm();emit();}
    function setConfirmation(value){state.confirmed=value===true;state.confirmationStamp=state.confirmed?stamp():null;emit();}
    async function readCapabilities(){const wanted=mode(),sequence=++capSequence,context=contextSequence;state.capabilities=null;unconfirm();state.capLoading=true;state.readError="";emit();
      try{const value=await api(path('terminal_broker_plan_capabilities',{mode:wanted}));if(sequence!==capSequence||context!==contextSequence)return;
        const workspace=envelope(value,wanted,state.workspaceContext),runtime=value.runtime;
        require(value.read_only===true&&['NOT_PACKAGED','PACKAGED_IDENTITY_MATCHED'].includes(value.status)&&runtime?.status===value.status&&runtime.mode===wanted&&runtime.runtime_compatibility==='NOT_VERIFIED'&&runtime.identity_match_only===true&&closed(runtime.permissions)&&Array.isArray(runtime.missing_capabilities)&&Object.hasOwn(runtime,'sdk')&&Object.hasOwn(runtime,'adapter'),"程序包条件回复不完整，不能据此保存计划。");
        require(value.status==='NOT_PACKAGED'?runtime.package===null:hash(runtime.package?.bundle_id),"程序包条件身份缺失。");
        state.workspaceContext=workspace;state.capabilities=copy(value);unconfirm();emit();return value;
      }catch(error){if(sequence===capSequence){state.readError="计划条件读取未完成："+errorText(error);emit();}}finally{if(sequence===capSequence){state.capLoading=false;emit();}}
    }
    async function readPlans(){const wanted=mode(),sequence=++listSequence,context=contextSequence;state.listLoading=true;state.readError="";emit();
      try{const value=await api(path('terminal_broker_plans',{mode:wanted}));if(sequence!==listSequence||context!==contextSequence)return;
        const workspace=envelope(value,wanted,state.workspaceContext);
        require(value.read_only===true&&value.retry_allowed===false&&Array.isArray(value.items)&&value.items.length<=1000&&Array.isArray(value.requests)&&value.requests.length<=1000
          &&value.items.every(v=>hash(v.plan_id)&&hash(v.config_id)&&hash(v.intent_id))&&value.requests.every(v=>requestId(v.request_id)&&hash(v.request_hash)&&hash(v.config_id)&&hash(v.intent_id)&&['PREPARING','REFUSED','COMPLETED'].includes(v.state))
          &&new Set(value.items.map(v=>v.plan_id)).size===value.items.length&&new Set(value.requests.map(v=>v.request_id)).size===value.requests.length,"计划列表的原身份或数量不一致。");
        state.workspaceContext=workspace;state.items=copy(value.items);state.requests=copy(value.requests);state.listScope={mode:wanted,workspace_context:workspace};emit();return value;
      }catch(error){if(sequence===listSequence){state.readError="已有计划读取未完成，保存事实仍保留："+errorText(error);emit();}}finally{if(sequence===listSequence){state.listLoading=false;emit();}}
    }
    async function readPlan(id){const scope=state.listScope&&copy(state.listScope),sequence=++detailSequence,context=contextSequence;
      require(scope&&state.items.some(v=>v.plan_id===id),"请从已读取列表明确选择原计划。");state.detailLoading=true;state.readError="";emit();
      try{const value=await api(path('terminal_broker_plan',{mode:scope.mode,plan_id:id}));if(sequence!==detailSequence||context!==contextSequence)return;
        envelope(value,scope.mode,scope.workspace_context);require(value.read_only===true&&value.retry_allowed===false&&['FOUND','NOT_RECORDED'].includes(value.status),"原计划读取状态不完整。");
        if(value.status==='FOUND')require(value.plan?.schema_version==='hakimi-broker-execution-plan-v1'&&value.plan.id===id&&value.plan.mode===scope.mode&&closed(value.plan.permissions),"原计划身份与选择不一致。");
        else require(value.plan===null,"未找到状态不能带入另一份计划。");state.detail={...scope,plan_id:id,status:value.status,plan:copy(value.plan)};emit();return value;
      }catch(error){if(sequence===detailSequence){state.readError="原计划详情读取未完成："+errorText(error);emit();}}finally{if(sequence===detailSequence){state.detailLoading=false;emit();}}
    }
    async function validateOutcome(value,operation,mutation=false){
      const wanted=operation.mode,workspace=envelope(value,wanted,operation.workspace_context);
      require(value.request_id===operation.request_id&&value.retry_allowed===false&&value.read_only===!mutation,"回执未绑定原请求或只读状态。");
      if(value.status==='NOT_RECORDED'){require(!mutation&&value.claim===null&&value.receipt===null,"未找到状态不一致。");return {pending:true};}
      const claim=value.claim;
      require(claim?.schema_version==='hakimi-broker-plan-claim-v1'&&claim.action===ACTION&&claim.mode===wanted&&claim.workspace_context===workspace&&claim.request_id===operation.request_id
        &&claim.request_hash===operation.request_hash&&closed(claim.permissions)&&validPayload(claim.payload)&&claim.payload.mode===wanted&&claim.payload.request_id===operation.request_id
        &&claim.payload.config_id===operation.config_id&&claim.payload.intent_id===operation.intent_id&&(!operation.payload||equal(claim.payload,operation.payload))
        &&claim.request_hash===await digest({action:ACTION,payload:claim.payload})&&await sealed(claim),"原请求认领的范围、预算或身份不一致。");
      if(value.status==='PREPARING_UNCONFIRMED'){require(value.receipt===null&&value.result===null,"未确认状态不能带入完成回执。");return {pending:true,payload:copy(claim.payload)};}
      const receipt=value.receipt,result=receipt?.result;
      require((mutation?['PLAN_SAVED','PLAN_NOT_CREATED'].includes(value.status):value.status==='FOUND')&&receipt?.schema_version==='hakimi-broker-plan-receipt-v1'&&receipt.action===ACTION
        &&receipt.mode===wanted&&receipt.workspace_context===workspace&&receipt.request_id===operation.request_id&&receipt.request_hash===operation.request_hash&&receipt.claim_id===claim.id
        &&equal(receipt.payload,claim.payload)&&closed(receipt.permissions)&&await sealed(receipt)&&plain(result)&&result.mode===wanted&&result.request_id===operation.request_id
        &&result.config_id===operation.config_id&&result.intent_id===operation.intent_id&&closed(result.permissions)&&equal(value.result,result)
        &&['PLAN_SAVED','PLAN_NOT_CREATED'].includes(result.status)&&(mutation?value.status===result.status:true)
        &&(result.status==='PLAN_SAVED'?hash(result.plan_id):result.plan_id===null),"保存回执不属于原请求的计划、范围或关闭权限。");
      return {pending:false,result:copy(result)};
    }
    function accept(checked,operation){if(checked.pending){if(checked.payload)operation.payload=checked.payload;state.error="原请求仍待核对；只查询这个编号，不重复提交。";emit();return false;}
      state.fact={...checked.result,workspace_context:operation.workspace_context};state.pending=null;state.error="";unconfirm();emit();return true;}
    async function save(){require(!state.busy&&!state.pending,"请先查询原计划请求，不能重复提交。");const context=state.context;
      require(eligibleContext(context)&&context.blocked===false,"候选资料或停止状态仍需核对，不能保存新计划。");
      require(!state.capLoading&&state.capabilities?.status==='PACKAGED_IDENTITY_MATCHED'&&state.capabilities.mode===context.mode&&hash(state.workspaceContext),"请明确读取当前程序包条件；未绑定程序包时不能创建计划。");
      require(state.confirmed&&state.confirmationStamp===stamp(),"请重新核对并明确确认只保存离线范围与预算。");
      const payload={mode:context.mode,request_id:'broker-plan-'+uuid(),config_id:context.config_id,intent_id:context.intent.id,expected_control_revision:context.expected_control_revision,bounds:boundsFromForm(state.form,context.intent.terms.expires_at,now())};
      const wanted=stamp(),workspace=state.workspaceContext;state.busy=true;state.error="";state.readError="";emit();let operation,completion=null,acknowledged=false;
      const receive=value=>{if(!completion){completion=validateOutcome(value,operation,true).then(checked=>{acknowledged=accept(checked,operation);return checked;});completion.catch(()=>{});}return completion;};
      try{const requestHash=await digest({action:ACTION,payload});require(wanted===stamp(),"确认后资料已改变，本次没有提交，请重新核对。");
        operation={mode:payload.mode,workspace_context:workspace,request_id:payload.request_id,request_hash:requestHash,config_id:payload.config_id,intent_id:payload.intent_id,payload:copy(payload)};
        state.pending=operation;unconfirm();emit();const value=await perform(ACTION,copy(payload),{onSuccess:receive});if(!completion&&value)receive(value);if(completion)await completion;
        if(!acknowledged&&state.pending)state.error="计划结果尚未确认。保留原编号，只查询回执，不重复提交。";
      }catch(error){if(completion){try{await completion;}catch(_){}}
        if(acknowledged)state.readError="计划已有保存回执，后续读取未完成："+errorText(error);else state.error=(state.pending?"原请求结果待核对：":"本次未提交：")+errorText(error);
      }finally{state.busy=false;emit();}
      if(acknowledged&&state.context?.mode===operation.mode)await readPlans();return acknowledged?state.fact:null;
    }
    async function queryPending(){const operation=state.pending;if(!operation||state.querying)return;state.querying=true;state.readError="";emit();
      try{const value=await api(path('terminal_broker_plan_receipt',{mode:operation.mode,request_id:operation.request_id}));if(state.pending!==operation)return;
        const checked=await validateOutcome(value,operation);if(state.pending!==operation)return;accept(checked,operation);
      }catch(error){if(state.pending===operation)state.readError="原请求回执读取未完成，仍保留原编号："+errorText(error);}
      finally{state.querying=false;emit();}
    }
    async function recoverRequest(id){require(!state.busy&&!state.pending,"先查询当前未确认的原请求。");const row=state.requests.find(v=>v.request_id===id),scope=state.listScope;
      require(row&&scope,"请从已读取的原请求列表选择编号。");state.pending={...copy(scope),request_id:row.request_id,request_hash:row.request_hash,config_id:row.config_id,intent_id:row.intent_id,payload:null};unconfirm();emit();return queryPending();}
    return {state,setContext,setForm,setConfirmation,readCapabilities,readPlans,readPlan,save,queryPending,recoverRequest};
  }

  function installTerminalBrokerPlanUI({host,api,perform,notify=()=>{}}){
    const document=host.ownerDocument,section=document.createElement('section');section.className='panel section-gap tbp';section.id='terminalBrokerPlanWorkspace';
    const field=(key,label,type='number',extra='')=>`<div class="field"><label for="tbp-${key}">${label}</label><input id="tbp-${key}" data-tbp-field="${key}" type="${type}" ${extra}></div>`;
    section.innerHTML=`<div class="panel-head"><h3>3 · 保存离线验收计划</h3></div><div class="panel-body"><p>只保存这份未发送意图的范围、缺口与预算；不连接券商、不授权、不执行订单。</p><p id="tbp-context" class="section-note"></p>
      <div id="tbp-fact" class="notice section-gap" role="status" hidden></div><div id="tbp-pending" class="notice warning section-gap" role="status" hidden></div><div id="tbp-error" class="notice warning section-gap" role="status" hidden></div><div id="tbp-read-error" class="notice warning section-gap" role="status" hidden></div>
      <div class="actions section-gap"><button type="button" class="btn" data-tbp-action="conditions">读取本次保存条件</button><button type="button" class="btn" data-tbp-action="list">读取已有计划与原请求</button></div><div id="tbp-capabilities" class="section-gap"></div>
      <form id="tbp-form" class="section-gap" hidden><div class="form-grid">${field('valid_until','计划失效时间（本地时间，至少 3 分 5 秒后）','datetime-local','required step=1')}${field('max_total_fees','费用金额上限（美元，不是实际费用或费率）','text','required inputmode=decimal placeholder="请明确填写，可填 0"')}</div><p id="tbp-expiry" class="section-note"></p>
      <details class="section-gap"><summary>核对完整调用、时间与输出预算</summary><p>以下只是未来验收的上限，实际执行适配尚未完成。本次保存不会执行任何调用。连接主机固定为 127.0.0.1。</p><p id="tbp-original-expiry" class="section-note"></p><div class="form-grid">
      ${field('port','本机端口','number','required min=1 max=65535 step=1')}${field('wall_timeout_seconds','总时限（秒）','number','required min=1 max=180 step=1')}${field('call_timeout_seconds','单次调用时限（秒）','number','required min=1 max=30 step=1')}${field('cleanup_timeout_seconds','清理时限（秒）','number','required min=1 max=5 step=1')}${field('max_output_bytes','全部输出与原始证据上限（字节；131072 = 128 KiB）','number','required min=1 max=131072 step=1')}${field('max_observation_records','最多观察记录数','number','required min=1 max=100 step=1')}${field('max_evidence_age_seconds','证据最长有效时间（秒）','number','required min=1 max=60 step=1')}${field('observe','观察调用次数上限','number','required min=1 max=5 step=1')}${field('cancel','撤单调用次数上限','number','required min=0 max=1 step=1')}</div>
      <p>固定次数：连接、运行信息、账户、持仓、证券规则、报价、费用和提交各 1 次；解锁 0 次。上述预算不授予调用权限。</p></details>
      <label class="tbp-confirm section-gap"><input id="tbp-confirm" type="checkbox">我确认只保存本地离线范围与预算，不连接、不授权、不下单。</label><button class="btn primary section-gap" id="tbp-save" type="submit">保存离线验收计划</button></form>
      <div id="tbp-list" class="section-gap"></div><div id="tbp-detail" class="section-gap"></div></div>`;
    const style=document.createElement('style');style.textContent='.tbp [hidden]{display:none!important}.tbp .notice,.tbp p,.tbp dd{overflow-wrap:anywhere}.tbp dd{margin-left:0}.tbp .tbp-confirm{display:flex;align-items:flex-start;gap:10px}.tbp .tbp-confirm input{flex:none;margin-top:4px}.tbp button,.tbp select,.tbp input:not([type=checkbox]),.tbp summary{min-height:44px}.tbp summary{cursor:pointer;align-content:center}.tbp .actions{display:flex;flex-wrap:wrap;gap:8px}.tbp .tbp-record{padding:12px 0;border-bottom:1px solid var(--line,#d8e0eb)}@media(max-width:760px){.tbp .form-grid{grid-template-columns:1fr}.tbp button{white-space:normal}}';host.append(section);document.head.append(style);
    const $=id=>section.querySelector('#tbp-'+id),button=(label,action,id='')=>`<button type="button" class="btn small" data-tbp-action="${action}" data-tbp-id="${esc(id)}">${label}</button>`;
    const controller=createController({api,perform,changed:render}),state=controller.state;
    function render(){const context=state.context,valid=eligibleContext(context);section.hidden=!modes[context?.mode]&&!state.pending&&!state.fact;
      $('context').textContent=valid?`${modes[context.mode]} · ${context.intent.terms.asset_code} · ${context.intent.terms.side==='BUY'?'买入':'卖出'} ${context.intent.terms.quantity} 股 · 绑定已保存的未发送意图。${context.blocked?'当前候选或停止状态仍需核对。':''}`:'先保存一份匹配当前资料的未发送意图，再填写新计划；原计划仍可明确读取。';
      const fact=state.fact;$('fact').hidden=!fact;$('fact').innerHTML=fact?`<strong>${fact.status==='PLAN_SAVED'?'离线验收计划已保存；仍未连接、未授权。':'本次没有创建计划，原请求回执已保留。'}</strong><p>${esc(modes[fact.mode])} · ${esc(reasonLabels[fact.reason]||(fact.reason?'保存条件未满足，请核对原回执原因。':''))}</p><details><summary>查看原请求与保存身份</summary><p>请求 ${esc(fact.request_id)}</p><p>计划 ${esc(fact.plan_id??'未创建')}</p><p>工作区 ${esc(fact.workspace_context)}</p>${fact.reason?`<p>原原因 ${esc(fact.reason)}</p>`:''}</details>`:'';
      const pending=state.pending;$('pending').hidden=!pending;$('pending').innerHTML=pending?`<strong>${state.busy?'正在保存离线计划，请勿重复提交。':'原计划请求尚待核对，不重复提交。'}</strong><p>${esc(modes[pending.mode])} · 原请求 ${esc(pending.request_id)}</p>${button(state.querying?'正在查询原回执…':'查询这个原请求','query')}<details><summary>查看原范围</summary><p>工作区 ${esc(pending.workspace_context)}</p><p>候选 ${esc(pending.config_id)}<br>未发送意图 ${esc(pending.intent_id)}</p></details>`:'';
      for(const [id,value] of [['error',state.error],['read-error',state.readError]]){$(id).hidden=!value;$(id).textContent=value;}
      const caps=state.capabilities,runtime=caps?.runtime;$('capabilities').innerHTML=state.capLoading?'<p role="status">正在只读核对程序包身份与保存条件…</p>':caps?`<p class="notice ${caps.status==='NOT_PACKAGED'?'warning':''}">${caps.status==='NOT_PACKAGED'?'当前启动没有可信程序包绑定，不能创建新计划；已有计划仍可只读查看。':'程序包相关文件身份已核对；运行兼容性、账户和外部权限仍未验证。'}</p>${caps.status==='NOT_PACKAGED'?'':`${runtime.sdk?`<p>SDK 元数据：${esc(runtime.sdk.name)} ${esc(runtime.sdk.version)}；不是运行兼容性证明。</p>`:'<p>SDK：未取得已打包身份。</p>'}${runtime.adapter?'<p>适配器已有包内文件声明，尚未运行验证。</p>':'<p>接入适配器：当前包尚未提供。可以保存明确记录此缺口的离线计划。</p>'}`}`:'<p class="section-note">请明确读取本次条件；不会自动连接或查询账户。</p>';
      $('form').hidden=!valid;for(const [key,value] of Object.entries(state.form)){const node=$(key);if(node&&node.value!==String(value))node.value=value;}
      $('expiry').textContent=valid?'不得晚于原候选失效时间（本地时间）：'+localTime(context.intent.terms.expires_at)+'。费用上限只限制金额，不声明费用已知或为零。':'';
      $('original-expiry').textContent=valid?'原候选失效时间（原始 ISO）：'+context.intent.terms.expires_at:'';$('confirm').checked=state.confirmed;
      const locked=state.busy||!!pending;$('save').disabled=locked||state.capLoading||!valid||context?.blocked!==false||caps?.status!=='PACKAGED_IDENTITY_MATCHED'||!state.confirmed;
      for(const node of section.querySelectorAll('#tbp-form input'))node.disabled=locked;
      section.querySelector('[data-tbp-action="conditions"]').disabled=!modes[context?.mode]||state.capLoading;section.querySelector('[data-tbp-action="list"]').disabled=!modes[context?.mode]||state.listLoading;
      const query=section.querySelector('[data-tbp-action="query"]');if(query)query.disabled=state.busy||state.querying;
      $('list').innerHTML=state.listLoading?'<p role="status">正在读取本模式的原计划与请求…</p>':state.listScope?`<h4>${esc(modes[state.listScope.mode])} · 原保存记录</h4>${state.items.length?state.items.map(row=>`<div class="tbp-record"><strong>${esc(row.symbol)} · ${esc(row.strategy_id)} · 版本 ${esc(row.task_version)}</strong><p>${row.research_eligibility?.offline_only?'合成资料，只能离线；': ''}保存的是范围与缺口，不是交易许可。</p>${button('查看这份原计划','detail',row.plan_id)}</div>`).join(''):'<p>尚无保存计划。</p>'}<details class="section-gap"><summary>查看所有原请求，包括未确认和未创建记录</summary>${state.requests.map(row=>`<div class="tbp-record"><p>${esc(row.request_id)} · ${row.state==='PREPARING'?'结果待核对':row.state==='REFUSED'?'未创建计划':'已有保存回执'}</p>${button('查询这个原请求','recover',row.request_id)}</div>`).join('')||'<p>尚无原请求。</p>'}</details>`:'';
      const detail=state.detail,plan=detail?.plan;$('detail').innerHTML=state.detailLoading?'<p role="status">正在只读打开原计划…</p>':detail?plan?`<section aria-label="原保存的离线计划"><h4>原计划 · 只读</h4><p>${esc(modes[detail.mode])} · ${esc(plan.order?.asset_code??'未记录')} · ${esc(plan.order?.side??'未记录')} ${esc(plan.order?.quantity??'未记录')} 股</p><p>保存状态：${esc(planStatusLabels[plan.status]||"未识别状态")}。没有连接、授权或执行。</p><p>${plan.research_eligibility?.offline_only?'这份合成研究固定只限离线，不能通过补齐一般缺证升级。':'研究外部使用资格仍须独立核验。'}</p><dl><dt>计划失效时间（本地时间）</dt><dd>${esc(localTime(plan.bounds?.valid_until))}</dd><dt>费用金额上限</dt><dd>${esc(plan.bounds?.max_total_fees??'未记录')} ${esc(plan.order?.currency??'未记录')}；实际费用未核验</dd><dt>保存计划编号</dt><dd>${esc(detail.plan_id)}</dd></dl><details><summary>查看原预算、缺口和身份</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">${esc(JSON.stringify({status:plan.status,bounds:plan.bounds,capability_gaps:plan.capability_gaps,missing_evidence:plan.missing_evidence,config_id:plan.candidate_config?.id,intent_id:plan.candidate_intent?.id,runtime:plan.runtime},null,2))}</pre></details></section>`:`<p class="notice warning">当前没有读取到原计划 ${esc(detail.plan_id)}；不新建、不重提。</p>`:'';
      section.querySelectorAll('[data-tbp-action="recover"]').forEach(node=>node.disabled=locked);
    }
    const fail=error=>{state.error=errorText(error);render();notify(state.error);};
    section.addEventListener('input',event=>{if(event.target.dataset.tbpField)controller.setForm(Object.fromEntries(Object.keys(defaults).map(key=>[key,$(key).value])));});
    section.addEventListener('change',event=>{if(event.target.id==='tbp-confirm')controller.setConfirmation(event.target.checked);});
    section.addEventListener('submit',event=>{if(event.target.id!=='tbp-form')return;event.preventDefault();if(event.target.reportValidity())controller.save().catch(fail);});
    section.addEventListener('click',event=>{const node=event.target.closest('[data-tbp-action]');if(!node||node.disabled)return;const actions={conditions:()=>controller.readCapabilities(),list:()=>controller.readPlans(),detail:()=>controller.readPlan(node.dataset.tbpId),query:()=>controller.queryPending(),recover:()=>controller.recoverRequest(node.dataset.tbpId)};Promise.resolve().then(actions[node.dataset.tbpAction]).catch(fail);});
    render();return {controller,element:section,setContext:controller.setContext};
  }
  root.installTerminalBrokerPlanUI=installTerminalBrokerPlanUI;
  if(typeof module==='object'&&module.exports)module.exports={createController,install:installTerminalBrokerPlanUI,boundsFromForm,localTime,canonical,permissionKeys,defaults};
})(typeof globalThis!=='undefined'?globalThis:window);
