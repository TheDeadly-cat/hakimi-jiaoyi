/* Account-wide stop control. No SDK, dispatch, automatic resume or retry. */
(function(root){
  "use strict";
  const schema="hakimi-broker-account-control-v1",resumeAction="terminal_broker_account_resume";
  const modes={OFFICIAL_SIMULATION:"官方模拟候选",LIVE_CANDIDATE:"实盘候选"};
  const permissionKeys=["external_connection_allowed","query_allowed","submit_allowed","cancel_allowed","unlock_allowed","automatic_retry","automatic_resume","automatic_mode_fallback","user_authorization_granted"];
  const plain=v=>Boolean(v&&typeof v==="object"&&!Array.isArray(v)),copy=v=>JSON.parse(JSON.stringify(v));
  const hash=v=>typeof v==="string"&&/^[a-f0-9]{64}$/.test(v),closed=v=>plain(v)&&permissionKeys.every(key=>v[key]===false);
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const require=(value,message)=>{if(!value)throw Error(message);};
  const ordered=v=>v&&typeof v==="object"?(Array.isArray(v)?v.map(ordered):Object.fromEntries(Object.keys(v).sort().map(key=>[key,ordered(v[key])]))):v;
  const canonical=v=>JSON.stringify(ordered(v)).replace(/[\u007f-\uffff]/g,c=>"\\u"+c.charCodeAt(0).toString(16).padStart(4,"0"));
  const equal=(a,b)=>canonical(a)===canonical(b),errorText=e=>String(e?.message||e||"读取未完成");
  async function digest(value){const bytes=await root.crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical(value)));return Array.from(new Uint8Array(bytes),v=>v.toString(16).padStart(2,"0")).join("");}
  const validContext=c=>plain(c)&&Boolean(modes[c.mode])&&hash(c.config_id);
  const sameContext=(a,b)=>Boolean(a&&b&&a.mode===b.mode&&a.config_id===b.config_id);
  const path=(resource,identity)=>resource+"/"+encodeURIComponent(JSON.stringify(identity));
  const pin=v=>v?.service_available?{root_id:v.root_id,record_domain:v.record_domain,account_scope_id:v.account_scope_id,account:copy(v.account)}:null;
  async function envelope(value,context,expected,readOnly){
    require(plain(value)&&value.schema_version===schema&&value.config_id===context.config_id&&closed(value.permissions),"账户控制身份或关闭权限未通过核对。");
    if(readOnly)require(value.read_only===true,"读取结果未声明只读。");
    if(value.service_available===false){require(readOnly&&value.reason==="HOST_BINDING_UNAVAILABLE","账户控制服务不可用。");return value;}
    const account=value.account,control=value.control;
    require(value.service_available===true&&plain(account)&&equal(Object.keys(account).sort(),["account_id","mode","provider"])&&account.provider==="FUTU"&&account.mode===context.mode
      &&typeof account.account_id==="string"&&/^[1-9][0-9]{0,19}$/.test(account.account_id)&&BigInt(account.account_id)<2n**64n
      &&hash(value.root_id)&&["EXTERNAL_RECORD","SYNTHETIC_TEST"].includes(value.record_domain)&&value.account_scope_id===await digest(account),"返回账户与已保存候选的范围不一致。");
    if(expected)require(equal(pin(value),expected),"账户控制的原账户或保存范围已变化。");
    require(plain(control)&&Number.isSafeInteger(control.revision)&&control.revision>=0&&control.revision<=1000&&control.dispatch_authorized===false&&control.automatic_resume===false
      &&typeof control.stopped==="boolean"&&(control.revision===0?control.head_id===null&&control.last_action===null&&!control.stopped:hash(control.head_id)&&["stop","resume"].includes(control.last_action)&&control.stopped===(control.last_action==="stop"))
      &&value.broker_orders_cancelled===false&&typeof value.replayed==="boolean", "当前账户停止状态或权限不完整。");
    return value;
  }
  async function validateReceipt(value,operation){
    const receipt=value.receipt,p=operation.payload;
    if(receipt===null)return false;
    require(plain(receipt)&&receipt.schema_version===schema&&hash(receipt.id)&&receipt.request_id===p.request_id&&receipt.action===operation.action
      &&receipt.root_id===value.root_id&&receipt.record_domain===value.record_domain&&receipt.account_scope_id===value.account_scope_id&&closed(receipt.permissions)
      &&Number.isSafeInteger(receipt.revision)&&receipt.revision>0&&receipt.revision<=value.control.revision
      &&(receipt.revision===1?receipt.previous_id===null:hash(receipt.previous_id))&&typeof receipt.at==="string"&&Number.isFinite(Date.parse(receipt.at)),"回执不属于原账户控制请求。");
    const body={request_id:p.request_id,reason:p.reason,...(operation.action==="resume"?{expected_stop_receipt_id:p.expected_stop_receipt_id}:{})};
    require(equal(receipt.payload,body)&&receipt.request_hash===await digest({action:operation.action,payload:body})
      &&receipt.id===await digest(Object.fromEntries(Object.entries(receipt).filter(([key])=>key!=="id")))
      &&(receipt.revision!==value.control.revision||receipt.id===value.control.head_id&&receipt.action===value.control.last_action),"原请求内容或回执身份未通过核对。");
    return true;
  }
  function createController({api,perform,stopAccount,uuid=()=>root.crypto.randomUUID(),changed=()=>{}}){
    const state={context:null,view:null,stale:true,loading:false,confirmed:false,confirmationHead:null,stopPending:null,resumePending:null,stopping:false,resuming:false,queryingStop:false,queryingResume:false,facts:{},error:"",readError:""};
    let readSequence=0;
    const emit=()=>{try{changed(state);}catch(_){state.readError="页面展示未完成；原请求与已确认回执仍保留。";}};
    const unconfirm=()=>{state.confirmed=false;state.confirmationHead=null;};
    const current=()=>{require(validContext(state.context),"请先检查并暂存当前账户的候选资料；修改后须重新暂存。");return copy(state.context);};
    function setContext(value){const next=validContext(value)?{mode:value.mode,config_id:value.config_id}:null;if(sameContext(next,state.context)||!next&&!state.context)return;
      readSequence++;state.context=next;state.view=null;state.stale=true;state.loading=false;state.error="";state.readError="";unconfirm();emit();}
    function setConfirmation(value){state.confirmed=value===true&&!state.stale&&state.view?.service_available===true&&state.view.control.stopped;state.confirmationHead=state.confirmed?state.view.control.head_id:null;emit();}
    function updateCurrent(value,context){
      if(!sameContext(context,state.context))return;
      const old=state.view;
      if(old?.service_available&&value.service_available){require(equal(pin(old),pin(value)),"当前账户控制范围已变化，请重新核对。");
        if(value.control.revision<old.control.revision)return;
        require(value.control.revision!==old.control.revision||equal(value.control,old.control),"同一版本的账户控制状态不一致。");}
      if(!old||old.control?.head_id!==value.control?.head_id||value.service_available!==true)unconfirm();
      state.view=copy(value);state.stale=false;
    }
    async function refresh(){const context=current(),sequence=++readSequence,expected=pin(state.view);state.loading=true;state.stale=true;state.readError="";unconfirm();emit();
      try{const value=await api(path("terminal_broker_account_control",context));await envelope(value,context,expected,true);
        if(sequence!==readSequence||!sameContext(context,state.context))return;updateCurrent(value,context);return value;
      }catch(error){if(sequence===readSequence)state.readError="账户状态读取未完成："+errorText(error);}
      finally{if(sequence===readSequence){state.loading=false;emit();}}
    }
    async function accept(value,operation,readOnly=false){
      await envelope(value,operation.context,operation.scope,readOnly);
      require(value.service_available===true,"当前宿主未绑定共享账户控制；原请求仍待核对。");
      const recorded=await validateReceipt(value,operation);
      updateCurrent(value,operation.context);
      if(!recorded){state.error="当前未见原请求回执，不代表未处理；保留原编号，只能继续查询。";emit();return false;}
      state.facts[operation.action]={context:copy(operation.context),account:copy(value.account),request_id:operation.payload.request_id,receipt:copy(value.receipt),replayed:value.replayed};
      if(state[operation.action+"Pending"]===operation)state[operation.action+"Pending"]=null;
      state.error="";emit();return true;
    }
    async function execute(action,reason){const context=current(),isStop=action==="stop",lane=action+"Pending";
      require(!state[lane]&&!(isStop?state.stopping:state.resuming),"请先查询这个原请求回执，不能重复提交。");
      if(isStop)require(typeof stopAccount==="function","账户独立停止入口尚未配置，不能假定已经停止。");
      else require(!state.stopPending&&!state.stopping&&!state.stale&&state.view?.service_available===true&&state.view.control.stopped&&state.confirmed&&state.confirmationHead===state.view.control.head_id,"请读取并核对最新停止回执，明确确认只解除该账户的执行停止标记。");
      require(!(state.view?.service_available===false),"当前宿主未绑定共享账户控制，不能提交。");
      require(typeof reason==="string"&&reason.trim().length>=1&&reason.trim().length<=200,"请填写 1 至 200 字的原因。");
      const payload={...context,request_id:"broker-account-"+uuid(),reason:reason.trim(),...(isStop?{}:{expected_stop_receipt_id:state.confirmationHead})};
      const operation={action,context,payload,scope:pin(state.view)};state[lane]=operation;state[isStop?"stopping":"resuming"]=true;state.error="";state.readError="";unconfirm();emit();
      let completion=null,acknowledged=false;
      const receive=value=>{if(!completion){completion=accept(value,operation).then(ok=>{acknowledged=ok;return ok;});completion.catch(()=>{});}return completion;};
      try{const value=isStop?await stopAccount(copy(payload)):await perform(resumeAction,copy(payload),{onSuccess:receive});if(value&&!completion)receive(value);if(completion)await completion;
        if(!acknowledged)state.error="账户控制结果尚未确认；保留原请求，只查询回执，不自动重发。";
      }catch(error){if(completion){try{await completion;}catch(_){}}
        if(acknowledged)state.readError="原请求已有保存回执，后续读取未完成："+errorText(error);else state.error="原请求结果待核对："+errorText(error)+"。请查询原回执，不重复提交。";
      }finally{state[isStop?"stopping":"resuming"]=false;emit();}
      return acknowledged?state.facts[action]:null;
    }
    async function queryPending(action="stop"){require(["stop","resume"].includes(action),"原请求类别不正确。");const operation=state[action+"Pending"],key=action==="stop"?"queryingStop":"queryingResume";if(!operation||state[key])return;state[key]=true;state.readError="";emit();
      try{const value=await api(path("terminal_broker_account_receipt",{...operation.context,request_id:operation.payload.request_id}));if(state[action+"Pending"]!==operation)return;return await accept(value,operation,true);
      }catch(error){state.readError="原账户回执读取未完成，仍保留原编号："+errorText(error);}
      finally{state[key]=false;emit();}
    }
    return {state,setContext,setConfirmation,refresh,stop:reason=>execute("stop",reason),resume:reason=>execute("resume",reason),queryPending};
  }

  function installTerminalBrokerAccountControlUI({host,api,perform,stopAccount,notify=()=>{}}){
    const document=host.ownerDocument,section=document.createElement("section");section.className="panel section-gap tbac";section.id="terminalBrokerAccountControlWorkspace";
    section.innerHTML=`<div class="panel-head"><h3>该账户的执行停止</h3></div><div class="panel-body"><p>同一模式、同一账户的其他工作区会读取同一停止标记；不代表撤单或清仓。离线资料、未发送意图和验收计划仍可准备，另受本模式准备停止限制。券商执行尚未启用。</p><p id="tbac-context" class="section-note"></p><p id="tbac-state" role="status"></p>
      <div class="actions section-gap"><button type="button" class="btn" data-tbac-action="refresh">读取该账户当前状态</button><button type="button" class="btn" data-tbac-action="stop">停止该账户的执行</button></div>
      <div class="field section-gap"><label for="tbac-stop-reason">停止备注（可选）</label><input id="tbac-stop-reason" maxlength="200"></div>
      <div id="tbac-facts" class="section-gap" role="status" hidden></div><div id="tbac-pending" class="notice warning section-gap" role="status" hidden></div><div id="tbac-error" class="notice warning section-gap" role="status" hidden></div><div id="tbac-read-error" class="notice warning section-gap" role="status" hidden></div>
      <details class="section-gap"><summary>解除该账户的执行停止标记</summary><p>只解除这一账户的执行停止标记；不授予外部权限，不发送旧请求。本模式的准备停止仍须单独解除。</p><p id="tbac-resume-context"></p><div class="field"><label for="tbac-resume-reason">本次恢复原因（必填）</label><input id="tbac-resume-reason" maxlength="200"></div>
      <label class="tbac-confirm"><input id="tbac-confirm" type="checkbox">我已核对最新停止回执，只解除该账户的执行停止标记。</label><button type="button" class="btn" data-tbac-action="resume">确认解除执行停止</button></details></div>`;
    const style=document.createElement("style");style.textContent=".tbac [hidden]{display:none!important}.tbac{min-width:0}.tbac p,.tbac .notice{overflow-wrap:anywhere}.tbac button,.tbac summary,.tbac input:not([type=checkbox]){min-height:44px}.tbac summary{cursor:pointer;align-content:center}.tbac .actions{display:flex;flex-wrap:wrap;gap:8px}.tbac .tbac-confirm{display:flex;align-items:center;gap:10px;min-height:44px;margin:16px 0}.tbac .tbac-confirm input{flex:none}.tbac details .field{margin-top:12px}.tbac button{white-space:normal}@media(max-width:760px){.tbac .actions{align-items:stretch;flex-direction:column}}";host.appendChild(section);document.head.appendChild(style);
    const $=id=>section.querySelector("#tbac-"+id),button=action=>section.querySelector('[data-tbac-action="'+action+'"]');
    const controller=createController({api,perform,stopAccount,changed:render}),state=controller.state;let formContext="",lastHead=null;
    function render(){const context=state.context,view=state.view,available=view?.service_available===true,control=available?view.control:null;
      const nextContext=context?JSON.stringify(context):"";if(nextContext!==formContext){$("stop-reason").value="";$("resume-reason").value="";formContext=nextContext;}
      if(lastHead!==control?.head_id){$("resume-reason").value="";lastHead=control?.head_id;}
      $("context").textContent=available?`${modes[view.account.mode]} · 富途账户 ${view.account.account_id}${view.record_domain==="SYNTHETIC_TEST"?" · 隔离测试资料":""}`:context?`${modes[context.mode]} · 绑定当前已保存候选；尚未读取账户身份。`:"请先检查并暂存当前账户的候选资料；修改账户或资料后须重新暂存。";
      $("state").textContent=state.loading?"正在只读查询账户状态…":view?.service_available===false?"当前启动未提供共享账户控制，尚不能确认或更改账户停止状态。":state.stale?"当前账户状态尚未确认；不代表已停止。":control.stopped?"该账户的停止状态已保存；同一模式、同一账户的其他工作区会读取同一标记。未撤单或清仓。券商执行尚未启用。":"当前该账户没有停止标记；这不授予连接或交易权限。券商执行尚未启用。";
      button("refresh").disabled=!context||state.loading;
      button("stop").disabled=!context||state.stopping||!!state.stopPending||typeof stopAccount!=="function"||view?.service_available===false;
      button("stop").textContent=state.stopping?"正在提交账户停止…":"停止该账户的执行";
      const resumable=available&&!state.stale&&control.stopped&&!state.stopPending&&!state.resumePending&&!state.stopping&&!state.resuming;
      $("confirm").disabled=!resumable;$("confirm").checked=state.confirmed;button("resume").disabled=!resumable||!state.confirmed;
      $("resume-context").textContent=resumable?"最新停止回执："+control.head_id:"请先读取并核对当前账户最新停止回执；待核对请求须先查询。";
      const facts=Object.values(state.facts);$("facts").hidden=!facts.length;$("facts").innerHTML=facts.map(fact=>`<div class="notice section-gap"><strong>原${fact.receipt.action==="stop"?"停止":"恢复"}请求已有保存回执；当前状态以账户状态栏为准。</strong><p>${esc(modes[fact.account.mode])} · 原账户 ${esc(fact.account.account_id)}${sameContext(fact.context,context)?"":" · 来自先前候选"}</p><details><summary>查看原请求与回执</summary><p>请求：${esc(fact.request_id)}</p><p>回执：${esc(fact.receipt.id)}</p><p>记录时间：${esc(fact.receipt.at)}</p></details></div>`).join("");
      const pending=["stop","resume"].filter(action=>state[action+"Pending"]);$("pending").hidden=!pending.length;$("pending").innerHTML=pending.map(action=>{const op=state[action+"Pending"];return `<p>原账户${action==="stop"?"停止":"恢复"}结果待核对；不重复提交。</p><p>${esc(modes[op.context.mode])}${op.scope?" · 原账户 "+esc(op.scope.account.account_id):" · 原已保存候选"}</p><button type="button" class="btn" data-tbac-action="query-${action}">查询原${action==="stop"?"停止":"恢复"}回执</button><details><summary>查看原范围与请求编号</summary><p>候选：${esc(op.context.config_id)}</p><p>请求：${esc(op.payload.request_id)}</p></details>`;}).join("");
      for(const action of pending)button("query-"+action).disabled=state[action==="stop"?"queryingStop":"queryingResume"];
      for(const [id,value] of [["error",state.error],["read-error",state.readError]]){$(id).hidden=!value;$(id).textContent=value;}
    }
    const fail=error=>{state.error=errorText(error);render();notify(state.error);};
    section.addEventListener("change",event=>{if(event.target.id==="tbac-confirm")controller.setConfirmation(event.target.checked);});
    section.addEventListener("click",event=>{const node=event.target.closest("[data-tbac-action]");if(!node||node.disabled)return;const actions={refresh:()=>controller.refresh(),stop:()=>controller.stop($("stop-reason").value.trim()||"用户明确停止该账户的执行"),resume:()=>controller.resume($("resume-reason").value),"query-stop":()=>controller.queryPending("stop"),"query-resume":()=>controller.queryPending("resume")};Promise.resolve().then(actions[node.dataset.tbacAction]).catch(fail);});
    render();return {controller,element:section,setContext:controller.setContext};
  }
  root.installTerminalBrokerAccountControlUI=installTerminalBrokerAccountControlUI;
  if(typeof module==="object"&&module.exports)module.exports={createController,install:installTerminalBrokerAccountControlUI,canonical,permissionKeys};
})(typeof globalThis!=="undefined"?globalThis:window);
