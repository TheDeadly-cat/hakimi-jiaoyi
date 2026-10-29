/* Same-window synthetic execution UI. Loading this file has no effects. */
(function(root) {
  "use strict";
  const plain=v=>Boolean(v&&typeof v==="object"&&!Array.isArray(v));
  const clone=v=>JSON.parse(JSON.stringify(v));
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const requestPath=(resource,value)=>resource+"/"+encodeURIComponent(JSON.stringify(value));
  const labels={ACCEPTED:"已接受 · 尚未成交",REJECTED:"已拒绝",PARTIAL:"部分成交",FILLED:"全部成交",CANCELLED:"已撤销",TIMEOUT_UNCONFIRMED:"结果待核对"};
  const safePermissions=value=>plain(value)&&["paper_order_allowed","live_order_allowed","order_allowed","broker_connection_allowed","model_calls_allowed"].every(key=>value[key]===false);
  const reference=value=>plain(value)&&["terminal_run","core_run"].includes(value.kind)&&typeof value.id==="string"&&value.id.length>0;
  const sameReference=(a,b)=>a?.kind===b?.kind&&a?.id===b?.id;
  const money=(value,label,positive=false,signed=false)=>{const s=String(value??"").trim(),number=signed&&s.startsWith("-")?s.slice(1):s;if(!/^(?:0|[1-9]\d{0,14})(?:\.\d{1,8})?$/.test(number)||(positive&&Number(s)<=0))throw Error(label+"请填写有效的美元金额。");return s;};
  const integer=(value,label,zero=false)=>{const n=Number(value);if(String(value).trim()===""||!Number.isSafeInteger(n)||n<(zero?0:1)||n>1e9)throw Error(label+"请填写"+(zero?"非负":"正")+"整数。");return n;};
  const timestamp=(value,label)=>{const n=Date.parse(value);if(!value||!Number.isFinite(n))throw Error("请填写"+label+"。");return n;};
  const readableError=error=>error?.info?.message||error?.message||"本地读取未完成，请核对原操作记录。";
  const reasons={SHARED_CASH_UNAVAILABLE:"可用资金不足，已计入其他订单预留和费用。",OWNER_SHARES_UNAVAILABLE:"该归属的可卖股份不足，已扣除未完成卖单预留。",
    ORDER_NOTIONAL_LIMIT:"超过账户保存的每单金额上限。",TOTAL_EXPOSURE_LIMIT:"超过账户保存的总敞口上限。",SECURITY_EXPOSURE_LIMIT:"超过该标的的敞口上限。",
    NEW_RISK_STOPPED:"账户已暂停新增风险。",ACCOUNT_LOSS_LIMIT:"已触发账户累计亏损上限。",EXPLICIT_SYNTHETIC_REJECTION:"这是你明确填写的合成拒绝响应。",
    OBSERVED_ACCOUNT_DEFICIT:"现金或所属持仓低于未完成订单预留，需先解决冲突并完整核对。",
    execution_cumulative_state_invalid:"累计成交数量与原订单或观察状态冲突，未把这份观察记成成交。",
    execution_observation_id_conflict:"同一观察编号出现不同内容，原记录保留，新增风险已停止。",
    synthetic_cash_or_owner_position_mismatch:"观察现金或所属持仓与累计成交无法对应，本批核对没有改写账务。",
    order_absence_does_not_prove_rejection:"完整观察缺少原订单；查无订单不能当作已拒绝。",
    synthetic_account_still_unconfirmed:"账户仍有未知结果或资金、持仓预留冲突。",terminal_order_reported_open:"已结束订单在完整观察中仍显示未结束，需要核对。"};
  const facts={PLAN_SAVED:"演练计划已保存，尚未记录任何订单。",ACCEPTED:"已记录合成接受响应并保留资金或股份；尚未成交。",
    REJECTED:"已记录拒绝，未新增成交。",TIMEOUT_UNCONFIRMED:"已保存待核对订单；预留仍保留，请勿再次提交。",
    DUPLICATE_OPPORTUNITY:"同一机会已有订单，未重复占款。",CAPACITY_REACHED:"这个合成账户已达到记录上限，未新增订单。",
    APPLIED:"合成累计观察已记录。",DUPLICATE:"这份观察已记录，未重复记账。",STALE:"较旧观察已保留，没有倒退当前成交。",
    BLOCKED:"本次核对未通过，原记录和风险停止状态已保留。",RECONCILED:"完整合成观察已核对；暂停状态需要另外明确恢复。",
    NEW_RISK_STOPPED:"已暂停新增风险，原订单和预留仍保留。",NEW_RISK_RESUMED:"已明确恢复本地合成演练。",
    CANCEL_RESPONSE_ACCEPTED:"已记录撤销请求的接受响应；预留仍保留，需另行记录最终状态。",
    CANCEL_RESPONSE_TIMEOUT_UNCONFIRMED:"撤销响应待核对，未释放预留，也不会重复尝试。",
    CANCEL_ALREADY_ATTEMPTED:"撤销已经尝试，未再次发起。",ALREADY_TERMINAL:"订单已经结束，没有新增成交。",QUOTES_RECORDED:"合成报价已保存，没有运行订单。"};
  function validView(value,id) {return value?.account_id===id&&typeof value.account_context==="string"&&plain(value.ledger)&&safePermissions(value.permissions)&&value.ledger.account_id===id
    &&[value.ledger.plans,value.ledger.orders,value.ledger.positions].every(Array.isArray)&&plain(value.ledger.config?.securities);}
  function readyResearch(value) {const d=value?.display,b=value?.binding;return b?.status==="COMPLETED"&&[b.engine_id,b.strategy_id,b.input_id,b.report_id].every(v=>typeof v==="string"&&v.length>0)
    &&/^[0-9a-f]{64}$/.test(b.report_hash||"")&&b.task_version!=null&&d?.security_id===b.security_id&&d?.security_id&&d?.symbol&&d?.currency==="USD"&&d?.asset_class==="US_EQUITY";}
  function accountMatchesResearch(account,research) {
    const display=research?.display,security=account?.ledger?.config?.securities?.[display?.security_id];
    return Boolean(readyResearch(research)&&security?.symbol===display.symbol);
  }
  function planMatchesResearch(plan,research) {
    return Boolean(plan&&readyResearch(research)&&["report_id","report_hash","task_id","task_version","input_id","engine_id","security_id"].every(key=>research.binding[key]===plan.research_binding?.[key]));
  }
  function reconciliationIdentities(account) {
    if(!account?.ledger)throw Error("请先读取合成账户。");
    const slots=new Map();
    for(const row of account.ledger.positions||[])slots.set(row.owner_id+"\0"+row.security_id,{owner_id:row.owner_id,security_id:row.security_id});
    for(const row of account.ledger.orders||[]){const t=row.terms;slots.set(t.owner_id+"\0"+t.security_id,{owner_id:t.owner_id,security_id:t.security_id});}
    return {account_id:account.account_id,account_context:account.account_context,revision:account.ledger.revision,
      orders:(account.ledger.orders||[]).map(row=>({order_id:row.order_id})),positions:[...slots.values()]};
  }
  function createController({api,perform,readResearch,uuid=()=>root.crypto.randomUUID(),changed=()=>{}}) {
    const state={sources:[],accounts:[],source:null,sourceReference:null,account:null,accountId:"",planId:"",orderId:"",
      busy:false,pending:null,fact:null,error:"",readError:"",accountStale:false,comparison:null,reconciliation:null,orderPreview:null};
    let accountSequence=0,sourceSequence=0,listSequence=0;
    const emit=()=>{if(state.orderPreview&&state.orderPreview.stamp!==previewStamp())state.orderPreview=null;try{changed(state);}catch(error){state.readError="页面展示未完成；已保存回执仍保留。";}};
    const req=()=>"execution-"+uuid();
    function setSources(items) {state.sources=(items||[]).filter(reference).map(v=>({kind:v.kind,id:v.id,label:String(v.label||"已保存研究结果")}));emit();}
    async function openResearch(value) {
      if(value==null){sourceSequence++;state.sourceReference=null;state.source=null;state.comparison=null;emit();return;}
      if(!reference(value))throw Error("请选择一份已保存研究结果。");
      const ref={kind:value.kind,id:value.id},seq=++sourceSequence;state.sourceReference=ref;state.source=null;state.comparison=null;state.readError="";emit();
      try{const result=await (readResearch?readResearch(ref):api(requestPath("terminal_execution_research",{reference:ref})));
        if(seq!==sourceSequence)return;
        if(result?.binding?.status!=="COMPLETED"||!sameReference(result.reference,ref)||!safePermissions(result.permissions))throw Error("这份结果的保存身份尚未通过核对。");
        state.source=result;emit();return result;
      }catch(error){if(seq===sourceSequence){state.readError=readableError(error);emit();}}
    }
    async function refreshAccounts() {
      const seq=++listSequence;
      try{const value=await api("terminal_execution_accounts");if(seq!==listSequence)return;state.accounts=value.items||[];emit();}
      catch(error){if(seq===listSequence){state.readError="账户列表读取未完成："+readableError(error);emit();}}
    }
    async function openAccount(id,{retain=true}={}) {
      if(!id){accountSequence++;state.accountId="";state.account=null;state.planId="";state.orderId="";state.reconciliation=null;state.comparison=null;emit();return;}
      const seq=++accountSequence,changedAccount=state.accountId!==id;
      state.accountId=id;state.accountStale=true;state.readError="";
      if(changedAccount||!retain){state.account=null;state.planId="";state.orderId="";state.reconciliation=null;state.comparison=null;}
      emit();
      try{const value=await api("terminal_execution_account/"+encodeURIComponent(id));if(seq!==accountSequence)return;
        if(!validView(value,id))throw Error("返回的账户身份与当前选择不一致。");
        state.account=value;state.accountStale=false;
        if(!value.ledger.plans.some(p=>p.plan_id===state.planId))state.planId="";
        if(!value.ledger.orders.some(o=>o.order_id===state.orderId))state.orderId="";
        emit();return value;
      }catch(error){if(seq===accountSequence){state.readError="账户读取未完成，保留上次状态："+readableError(error);emit();}}
    }
    async function refresh() {await Promise.all([refreshAccounts(),state.accountId?openAccount(state.accountId):Promise.resolve()]);}
    function currentAccount() {
      if(!state.account||state.accountStale)throw Error("请先重新读取并选中一个合成账户。");
      return {account_id:state.account.account_id,account_context:state.account.account_context};
    }
    function accept(value,action,payload) {
      if(action==="terminal_execution_create_account") {
        if(value?.status!=="ACCOUNT_CREATED"||value.account_id!==payload.account_id||!safePermissions(value.permissions))return false;
        state.fact={message:"合成账户已保存，没有运行研究或订单。",requestId:payload.client_request_id,status:"ACCOUNT_CREATED"};
        state.accountId=value.account_id;
      }else {
        const receipt=value?.receipt;
        if(receipt?.schema_version!=="hakimi-offline-execution-receipt-v1"||receipt.request_id!==payload.client_request_id
          ||receipt.account_id!==payload.account_id||!safePermissions(receipt.permissions)||!Object.hasOwn(facts,receipt.outcome?.status))return false;
        state.fact={message:facts[receipt.outcome.status]+(reasons[receipt.outcome.reason]?" "+reasons[receipt.outcome.reason]:""),requestId:receipt.request_id,status:receipt.outcome.status,reason:receipt.outcome.reason||""};
        if(state.accountId===payload.account_id){if(receipt.outcome.plan_id)state.planId=receipt.outcome.plan_id;if(receipt.outcome.order_id)state.orderId=receipt.outcome.order_id;}
      }
      // A read begun before the durable write must not later replace its
      // acknowledged account projection with an older cash/reservation view.
      accountSequence++;
      if(validView(value.account,state.accountId)){state.account=value.account;state.accountStale=false;}
      else state.accountStale=true;
      state.pending=null;state.error="";
      if(value.read_warning||value.display_warning)state.readError="保存已确认，部分页面资料暂未读出；请重新读取。";
      emit();return true;
    }
    async function execute(action,payload) {
      if(state.busy||state.pending)throw Error("上一项操作仍在处理或待核对，请勿重复提交。");
      state.busy=true;state.error="";state.readError="";emit();let captured,confirmed=false;
      try {
        const result=await perform(action,clone(payload),{onSuccess:value=>{captured=value;confirmed=accept(value,action,payload);}});
        if(!confirmed)confirmed=accept(captured||result,action,payload);
        if(!confirmed){state.pending={action,payload:clone(payload)};state.error="尚未确认原操作回执。请核对原操作，不要再次提交。";emit();return null;}
        await refresh();return captured||result;
      }catch(error){
        if(confirmed){state.readError="原保存已确认，后续读取未完成："+readableError(error);}
        else{state.pending={action,payload:clone(payload)};state.error="原操作结果待核对："+readableError(error);}
        emit();return captured||null;
      }finally{state.busy=false;emit();}
    }
    async function checkPending() {
      const pending=state.pending;if(!pending)return;
      state.readError="";
      try {
        if(pending.action==="terminal_execution_create_account") {
          const account=await api("terminal_execution_account/"+encodeURIComponent(pending.payload.account_id));
          if(state.pending!==pending)return;
          if(!validView(account,pending.payload.account_id)||account.creation_request_id!==pending.payload.client_request_id)throw Error("尚未找到与原请求对应的创建回执。");
          accept({status:"ACCOUNT_CREATED",account_id:account.account_id,account,permissions:account.permissions},pending.action,pending.payload);
        }else {
          const result=await api(requestPath("terminal_execution_receipt",{account_id:pending.payload.account_id,request_id:pending.payload.client_request_id}));
          if(state.pending!==pending)return;
          if(result.status!=="COMMITTED"||!accept(result,pending.action,pending.payload))throw Error("原请求尚未确认。未找到回执不等于已拒绝；不会自动重新提交。");
        }
        await refresh();
      }catch(error){state.readError=readableError(error);emit();}
    }
    async function createAccount(form) {
      if(!readyResearch(state.source))throw Error("保存结果缺少可核验的美元股票身份，请先选择资料完整的结果。");
      if(!form.confirm)throw Error("请明确确认这是本地合成资金。");
      const label=String(form.label||"").trim();if(!label||label.length>100)throw Error("请填写不超过100字的账户名称。");
      const seconds=integer(form.quoteAge,"报价有效时长");if(seconds>86400)throw Error("报价有效时长不能超过一天。");
      const d=state.source.display;
      return execute("terminal_execution_create_account",{client_request_id:req(),account_id:"sim-"+uuid(),label,
        evidence_kind:"SYNTHETIC_TEST",initial_cash:money(form.cash,"初始资金",true),securities:{[d.security_id]:{symbol:d.symbol,tick_size:money(form.tick,"价格最小单位",true)}},
        rules:{max_order_notional:money(form.orderLimit,"每单上限",true),max_total_exposure:money(form.totalLimit,"总敞口上限",true),max_security_exposure:money(form.securityLimit,"单标的上限",true),
          cash_floor:money(form.floor,"现金底线"),fee_buffer:money(form.feeBuffer,"费用预留"),max_account_loss:money(form.lossLimit,"账户亏损上限"),quote_max_age_ms:seconds*1000}});
    }
    async function createPlan() {
      const account=currentAccount();if(!accountMatchesResearch(state.account,state.source))throw Error("保存结果与合成账户的证券身份必须精确一致，缺少身份时不能保存新计划。");
      return execute("terminal_execution_create_plan",{client_request_id:req(),...account,reference:clone(state.sourceReference),stage:"SIMULATION"});
    }
    function selectPlan(id) {
      if(!id){state.planId="";state.comparison=null;emit();return;}
      if(!state.account?.ledger.plans.some(p=>p.plan_id===id))throw Error("请选择当前账户的保存计划。");
      state.planId=id;state.comparison=null;emit();
    }
    function selectOrder(id) {if(!state.account?.ledger.orders.some(o=>o.order_id===id))throw Error("请选择当前账户的原订单。");state.orderId=id;emit();}
    function orderTerms(form,requireConfirmation=true) {
      const account=currentAccount(),plan=state.account.ledger.plans.find(p=>p.plan_id===state.planId);
      if(!plan||plan.stage!=="SIMULATION")throw Error("请选择可用于本地合成演练的计划。");
      if(state.account.reconciliation_required||state.account.deficiencies?.length)throw Error("账户仍有待核对事项，先完成明确核对。");
      if(requireConfirmation&&!form.confirm)throw Error("请确认记录的是虚构订单响应。");
      if(!["BUY","SELL"].includes(form.side)||!["ACCEPTED","REJECTED","TIMEOUT_UNCONFIRMED"].includes(form.outcome))throw Error("请选择方向和合成响应。");
      if(state.account.paused&&form.side==="BUY")throw Error("账户已暂停新增风险。");
      if(!state.account.ledger.config.securities[form.security])throw Error("请选择这个账户的演练标的。");
      if(!plan.research_binding?.security_id||plan.research_binding.security_id!==form.security)throw Error("订单标的必须与保存计划绑定的证券身份一致。");
      const at=timestamp(form.at,"演练时点"),now=Date.now();if(at>now)throw Error("演练时点不能晚于当前时间。");
      return {...account,plan_id:state.planId,security_id:form.security,side:form.side,
        quantity:integer(form.quantity,"委托股数"),limit_price:money(form.limit,"限价",true),
        quote:{security_id:form.security,price:money(form.quote,"合成报价",true),as_of:at,observed_at:now,source_id:"USER_DECLARED_SYNTHETIC",evidence_kind:"SYNTHETIC_TEST"},
        signal_at:at,execution_at:at,now_ms:now,outcome:form.outcome};
    }
    async function submitOrder(form) {
      return execute("terminal_execution_submit",{client_request_id:req(),...orderTerms(form)});
    }
    function previewStamp() {
      return JSON.stringify({accountId:state.accountId,context:state.account?.account_context,revision:state.account?.ledger.revision,
        stale:state.accountStale,paused:state.account?.paused,reconcile:state.account?.reconciliation_required,deficiencies:state.account?.deficiencies,
        plan:state.account?.ledger.plans.find(p=>p.plan_id===state.planId),source:state.sourceReference,binding:state.source?.binding,
        available:state.account?.ledger.available_cash,reserved:state.account?.ledger.reserved_cash,config:state.account?.ledger.config});
    }
    function invalidatePreview() {if(state.orderPreview){state.orderPreview=null;emit();}}
    function previewOrder(form) {
      if(state.busy||state.pending)throw Error("原操作仍待处理或核对，不能生成新订单。");
      const terms=orderTerms(form,false),plan=state.account.ledger.plans.find(p=>p.plan_id===state.planId);
      if(!planMatchesResearch(plan,state.source))throw Error("当前计划与所选保存结果不同，请先保存或选择对应计划。");
      const rules=state.account.ledger.config.rules||{},amount=terms.quantity*Number(terms.limit_price),fee=Number(rules.fee_buffer),available=Number(state.account.ledger.available_cash);
      state.orderPreview={stamp:previewStamp(),form:clone({...form,confirm:false}),terms,
        estimate:{notional:amount,reservation:terms.side==="BUY"&&Number.isFinite(fee)?amount+fee:null,
          available,feeBuffer:Number.isFinite(fee)?fee:null},accountLabel:state.account.label};
      state.error="";emit();return clone(state.orderPreview);
    }
    async function confirmOrder(confirmed) {
      const preview=state.orderPreview;
      if(!preview||preview.stamp!==previewStamp()){state.orderPreview=null;emit();throw Error("订单预览已失效，请重新核对资金与订单。");}
      if(confirmed!==true)throw Error("请先核对预览并明确确认合成订单。");
      const form=clone(preview.form);state.orderPreview=null;emit();
      return submitOrder({...form,confirm:true});
    }
    async function recordObservation(form) {
      const account=currentAccount();if(!state.orderId)throw Error("请先选择原订单。");
      if(!form.confirm)throw Error("请确认这些数值来自另行提供的合成观察。");
      if(!["ACCEPTED","REJECTED","PARTIAL","FILLED","CANCELLED"].includes(form.state))throw Error("请选择观察到的订单状态。");
      return execute("terminal_execution_observe",{client_request_id:req(),...account,now_ms:Date.now(),observation:{evidence_id:req(),order_id:state.orderId,
        state:form.state,cumulative_quantity:integer(form.quantity,"累计成交股数",true),cumulative_notional:money(form.notional,"累计成交金额"),cumulative_fee:money(form.fee,"累计费用")}});
    }
    async function recordCancel(outcome) {
      const account=currentAccount();if(!state.orderId||!["ACCEPTED","TIMEOUT_UNCONFIRMED"].includes(outcome))throw Error("请选择原订单和撤销响应。");
      return execute("terminal_execution_cancel",{client_request_id:req(),...account,order_id:state.orderId,now_ms:Date.now(),outcome});
    }
    async function control(kind,reason) {
      if(!["stop","resume"].includes(kind)||!String(reason||"").trim())throw Error("请填写暂停或恢复的原因。");
      return execute("terminal_execution_"+kind,{client_request_id:req(),...currentAccount(),reason:String(reason).trim()});
    }
    function beginReconciliation() {currentAccount();state.reconciliation=reconciliationIdentities(state.account);emit();}
    async function reconcile(form) {
      const account=currentAccount(),draft=state.reconciliation;
      if(!draft||draft.account_id!==account.account_id||draft.account_context!==account.account_context||draft.revision!==state.account.ledger.revision)throw Error("账户记录已变化，请重新打开核对表格，核对新的完整观察。");
      if(!form.confirm)throw Error("请确认这是另行提供的完整合成观察，不是把本地账本复制为证明。");
      if(form.orders?.length!==draft.orders.length||form.positions?.length!==draft.positions.length)throw Error("请逐项填写全部订单和持仓观察。");
      const orders=draft.orders.map((row,index)=>{const input=form.orders[index];if(!["ACCEPTED","REJECTED","PARTIAL","FILLED","CANCELLED"].includes(input.state))throw Error("每笔订单都需要明确的观察状态。");
        return {order_id:row.order_id,evidence_id:req(),state:input.state,cumulative_quantity:integer(input.quantity,"累计成交股数",true),cumulative_notional:money(input.notional,"累计成交金额"),cumulative_fee:money(input.fee,"累计费用")};});
      const positions=draft.positions.map((row,index)=>({...row,quantity:integer(form.positions[index].quantity,"所属持仓股数",true)}));
      return execute("terminal_execution_reconcile",{client_request_id:req(),...account,now_ms:Date.now(),complete_snapshot:{schema_version:"hakimi-offline-reconciliation-v1",evidence_kind:"SYNTHETIC_TEST",
        account_id:account.account_id,account_revision:draft.revision,observed_at:timestamp(form.at,"独立合成观察时间"),orders,cash:money(form.cash,"观察到的账户现金",false,true),positions}});
    }
    async function compare() {
      const account=currentAccount();if(!state.planId||!state.sourceReference)throw Error("请选择保存结果和演练计划。");
      const planId=state.planId,source=clone(state.sourceReference);
      try{const value=await api(requestPath("terminal_execution_compare",{account_id:account.account_id,plan_id:planId,reference:source}));
        if(state.accountId!==account.account_id||state.planId!==planId||!sameReference(source,state.sourceReference))return;
        state.comparison=value;state.readError="";emit();}
      catch(error){state.readError="差异资料读取未完成："+readableError(error);emit();}
    }
    return {state,setSources,openResearch,openAccount,refresh,createAccount,createPlan,selectPlan,selectOrder,submitOrder,
      previewOrder,confirmOrder,invalidatePreview,recordObservation,recordCancel,control,beginReconciliation,reconcile,compare,checkPending,execute};
  }

  function installTerminalExecutionUI({host,api,perform,notify=()=>{},readResearch}) {
    const document=host.ownerDocument,section=document.createElement("section");section.id="terminalExecutionWorkspace";section.className="section-gap tex";section.hidden=true;
    const field=(id,label,type="text",value="",extra="")=>`<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type}" value="${esc(value)}" ${extra}></div>`;
    const action=(label,name,extra="")=>`<button type="button" class="btn small" data-tex-action="${name}" ${extra}>${label}</button>`;
    const states=Object.entries(labels).filter(([key])=>key!=="TIMEOUT_UNCONFIRMED").map(([key,label])=>`<option value="${key}">${label}</option>`).join("");
    section.innerHTML=`<div class="page-heading"><div><p class="tex-mode">本地合成演练 · 美元整股</p><h2>核对策略、资金，再确认订单</h2><p>使用独立合成账户；不会连接券商或发送真实订单。策略推荐不等于买入指令。</p></div><div class="actions">${action("重新读取","refresh")}${action("暂停新增风险","stop")}</div></div>
      <div id="tex-fact" class="notice section-gap" role="status" aria-live="polite" hidden></div><div id="tex-error" class="notice warning section-gap" role="status" hidden></div><div id="tex-read-error" class="notice warning section-gap" role="status" hidden></div>
      <section class="panel"><div class="panel-head"><h3>1 · 选择保存的策略结果</h3></div><div class="panel-body"><div class="field"><label for="tex-source">已保存策略 / 结果</label><select id="tex-source"><option value="">请选择</option></select></div><div id="tex-source-detail" class="section-gap">选择后只读取原结果，不重新回测。</div></div></section>
      <section class="panel section-gap"><div class="panel-head"><h3>2 · 核对账户与风险</h3></div><div class="panel-body"><div class="field"><label for="tex-account">当前合成账户</label><select id="tex-account"><option value="">请选择</option></select></div>
      <div class="actions section-gap">${action("首次使用：新建合成账户","open-account")}</div><p id="tex-next-step" class="section-note"></p>
      <details id="tex-new-account" class="section-gap"><summary>新账户资金与风险设置</summary><form id="tex-account-form"><p class="section-note">标的身份来自选中的保存结果；以下资金和报价规则只用于本地演练。</p><div id="tex-account-symbol" class="section-note"></div><div class="form-grid section-gap">
      ${field("tex-name","账户名称","text","我的合成账户","required maxlength=100")}${field("tex-cash","初始合成资金（美元）","number","10000","required min=0.01 step=any")}
      ${field("tex-order-limit","每单金额上限（美元）","number","1000","required min=0.01 step=any")}${field("tex-total-limit","总敞口上限（美元）","number","10000","required min=0.01 step=any")}
      ${field("tex-security-limit","单标的上限（美元）","number","5000","required min=0.01 step=any")}${field("tex-floor","现金底线（美元）","number","0","required min=0 step=any")}
      ${field("tex-fee-buffer","每单费用预留（美元）","number","1","required min=0 step=any")}${field("tex-loss-limit","累计账户亏损上限（美元）","number","1000","required min=0 step=any")}
      ${field("tex-tick","合成价格最小单位（美元）","number","0.01","required min=0.00000001 step=any")}${field("tex-quote-age","报价最长有效时间（秒）","number","60","required min=1 max=86400 step=1")}</div>
      <label class="check-label"><input id="tex-confirm-account" type="checkbox" required>我确认这是本地合成资金，没有连接真实账户。</label><button id="tex-create-account" class="btn primary section-gap" type="submit">保存合成账户</button></form></details>
      <div id="tex-account-detail" class="section-gap"></div><div class="actions section-gap">${action("确认使用此策略 · 保存计划","create-plan")}</div><p class="section-note">仅绑定保存版本，不下单、不改变原策略。</p><div id="tex-plan-detail"></div>
      <details class="section-gap"><summary>已有计划与结果差异</summary><div class="field section-gap"><label for="tex-plan">切换已有演练计划</label><select id="tex-plan"><option value="">请选择已保存计划</option></select></div>${action("查看与保存结果的差异","compare")}<div id="tex-comparison" class="section-gap"></div></details></div></section>
      <section class="panel section-gap"><div class="panel-head"><h3>3 · 预览并确认合成订单</h3></div><div class="panel-body"><p id="tex-order-symbol" class="section-note">先保存策略计划，再填写订单。</p><form id="tex-order-form"><input id="tex-security" type="hidden"><div class="form-grid">
      <div class="field"><label for="tex-side">订单动作 · 由你决定</label><select id="tex-side" required><option value="">请选择，不默认买入</option><option value="BUY">买入（合成）</option><option value="SELL">卖出所属持仓（合成）</option></select></div>
      ${field("tex-quantity","股数（整股）","number","","required min=1 step=1")}${field("tex-limit","限价（美元）","number","","required min=0.00000001 step=any")}${field("tex-quote","合成参考价（美元）","number","","required min=0.00000001 step=any")}</div>
      <p class="section-note">参考价由你填写。预览时冻结当前本地时间；默认场景为合成接受，仍未成交。</p>
      <details class="section-gap"><summary>高级订单场景：拒绝、超时或指定时点</summary><div class="form-grid section-gap">${field("tex-order-at","另行指定演练时点（可选）","datetime-local","","step=1")}
      <div class="field"><label for="tex-outcome">合成订单响应</label><select id="tex-outcome" required><option value="ACCEPTED">接受，尚未成交</option><option value="REJECTED">明确拒绝</option><option value="TIMEOUT_UNCONFIRMED">超时，结果待核对</option></select></div></div>${action("填入当前演练时间","order-time")}</details>
      <button id="tex-preview-order" class="btn primary section-gap" type="submit">核对订单预览</button></form>
      <form id="tex-confirm-form" class="tex-preview section-gap" hidden><div id="tex-preview-detail"></div><label class="check-label section-gap"><input id="tex-confirm-order" type="checkbox" required>我已核对账户、方向和金额，确认仅记录本地合成订单。</label><button id="tex-submit-order" class="btn primary section-gap" type="submit">确认记录合成订单</button></form></div></section>
      <details id="tex-advanced" class="panel section-gap"><summary class="panel-head">高级：成交观察、撤销与账户核对</summary><div class="panel-body"><p class="section-note">用于手工验证合成响应和恢复流程；这里的观察数值仍需独立填写。</p><div id="tex-orders"></div><div class="field section-gap"><label for="tex-order">选择原订单</label><select id="tex-order"><option value="">请选择</option></select></div>
      <form id="tex-observation-form"><p class="section-note">以下必须是另行提供的合成累计观察；不会从账本中的旧数字自动填充。</p><div class="form-grid"><div class="field"><label for="tex-observed-state">观察到的状态</label><select id="tex-observed-state" required><option value="">请选择</option>${states}</select></div>
      ${field("tex-observed-qty","累计成交股数","number","","required min=0 step=1")}${field("tex-observed-notional","累计成交金额（美元）","number","","required min=0 step=any")}${field("tex-observed-fee","累计费用（美元）","number","","required min=0 step=any")}</div>
      <label class="check-label"><input id="tex-confirm-observation" type="checkbox" required>这些数值来自另行提供的合成观察。</label><button id="tex-save-observation" class="btn section-gap" type="submit">记录累计观察</button></form>
      <div class="form-grid section-gap"><div class="field"><label for="tex-cancel-outcome">撤销请求的合成响应</label><select id="tex-cancel-outcome"><option value="">请选择</option><option value="ACCEPTED">已接受请求，尚未确认撤销</option><option value="TIMEOUT_UNCONFIRMED">响应超时，继续待核对</option></select></div></div>${action("记录撤销响应","cancel")}<p class="section-note">撤销响应不释放预留；只有最终撤销或全部成交观察才能释放。</p>
      <div class="field section-gap"><label for="tex-control-reason">明确恢复的原因</label><input id="tex-control-reason" maxlength="500"></div><div class="actions">${action("明确恢复演练","resume")}${action("填写完整合成对账","begin-reconcile")}</div><div id="tex-reconciliation" class="section-gap" hidden></div></div></details>`;
    host.append(section);
    const style=document.createElement("style");style.textContent=".tex{scroll-margin-top:100px}.tex [hidden]{display:none!important}.tex .notice,.tex td,.tex dd{overflow-wrap:anywhere}.tex .tex-table{overflow:auto;max-height:440px}.tex .tex-table table{min-width:680px}.tex .tex-metrics{display:flex;gap:24px;flex-wrap:wrap}.tex .tex-metrics strong{display:block;font-size:20px}.tex details form{margin-top:14px}.tex .tex-mode{font-weight:700;color:var(--primary,#245ad5)}.tex .tex-preview{border:2px solid var(--primary,#245ad5);padding:18px;border-radius:10px}.tex summary{cursor:pointer;min-height:44px;align-content:center}.tex button,.tex select,.tex input:not([type=checkbox]):not([type=hidden]){min-height:44px}.tex [data-tex-action=stop]{border-color:#a44831;color:#8d3420}.tex .tex-rule-summary{margin:12px 0}.tex .check-label{display:flex;gap:10px;align-items:flex-start}.tex .check-label input{flex:none;margin-top:4px}.tex .page-heading>.actions{flex-wrap:wrap;flex-shrink:0}@media(max-width:760px){.tex .form-grid{grid-template-columns:1fr}.tex .page-heading{align-items:flex-start;flex-direction:column}.tex .tex-metrics{gap:16px}.tex .tex-preview{padding:14px}.tex button{white-space:normal}}";document.head.append(style);
    const $=id=>section.querySelector("#"+id),v=id=>$(id)?.value||"",checked=id=>$(id)?.checked===true;
    const option=(id,label)=>`<option value="${esc(id)}">${esc(label)}</option>`;
    const select=(id,rows,current,empty)=>{const node=$(id);node.innerHTML=option("",empty)+rows.map(([value,label])=>option(value,label)).join("");node.value=current||"";};
    const dollars=value=>typeof value==="string"?"$"+value:"未记录";
    let reconKey="",lastOrder="",lastPreview=null;
    const controller=createController({api,perform,readResearch,changed:render});
    const {state}=controller;
    function sourceLabel(ref){return state.sources.find(item=>sameReference(item,ref))?.label||"已保存研究结果";}
    function ownerLabel(owner){const plan=state.account?.ledger.plans.find(p=>p.owner_id===owner),link=state.account?.plan_links.find(p=>p.plan_id===plan?.plan_id);return link?sourceLabel(link.reference):"归属 "+String(owner).slice(0,10);}
    function render() {
      select("tex-source",state.sources.map((item,index)=>[String(index),item.label]),state.sourceReference?String(state.sources.findIndex(item=>sameReference(item,state.sourceReference))):"","请选择保存结果");
      select("tex-account",state.accounts.map(item=>[item.account_id,item.label]),state.accountId,"请选择合成账户");
      $("tex-fact").hidden=!state.fact;$("tex-fact").innerHTML=state.fact?`<strong>${esc(state.fact.message)}</strong><details><summary>查看原请求编号与原因</summary><p>${esc(state.fact.requestId)}</p>${state.fact.reason?`<p>${esc(state.fact.reason)}</p>`:""}</details>`:"";
      $("tex-error").hidden=!state.error&&!state.pending;$("tex-error").innerHTML=esc(state.error)+(state.pending?`<p>只读取同一份原回执，不会重新提交。</p>${action("核对原操作","check-pending")}`:"");
      $("tex-read-error").hidden=!state.readError;$("tex-read-error").textContent=state.readError;
      const research=state.source,d=research?.display||{};
      $("tex-source-detail").innerHTML=research?`<strong>${esc(sourceLabel(state.sourceReference))}</strong><p>${d.symbol?esc(d.symbol):"证券身份未记录"} · 保存版本 ${esc(research.binding.task_version)}</p><p>${readyResearch(research)?"已读取原保存身份；报价和成交仍需另行合成输入。":"缺少可核验的美元股票身份，暂不能新建账户或计划。"}</p><details><summary>查看保存的规则与身份</summary><dl class="kv"><dt>规则</dt><dd>${esc(research.binding.strategy_id)}</dd><dt>引擎</dt><dd>${esc(research.binding.engine_id)}</dd><dt>原结果</dt><dd>${esc(research.binding.report_id)}</dd></dl></details>`:"选择后只读取原结果，不重新回测。";
      $("tex-account-symbol").textContent=readyResearch(research)?"演练标的："+d.symbol+" · 合成美元资金与整股":"请先选择证券身份完整的保存结果。";
      const account=state.account,ledger=account?.ledger,securities=ledger?.config?.securities||{};
      select("tex-plan",(ledger?.plans||[]).map(plan=>[plan.plan_id,sourceLabel(account.plan_links.find(link=>link.plan_id===plan.plan_id)?.reference)+" · 版本 "+plan.research_binding.task_version]),state.planId,"请选择已保存计划");
      const selectedPlan=ledger?.plans.find(p=>p.plan_id===state.planId);$("tex-security").value=selectedPlan?.research_binding.security_id||"";
      $("tex-order-symbol").textContent=selectedPlan?"订单标的："+(securities[v("tex-security")]?.symbol||"身份未记录")+" · 使用保存版本 "+selectedPlan.research_binding.task_version+"；方向与数量由你决定。":"先在上一步保存或选择策略计划，再填写订单。";
      $("tex-next-step").textContent=!research?"先选择一份已保存结果，核对对应股票。":!account?"还未选择账户。首次使用可创建独立合成账户；不会使用真实资金。":!planMatchesResearch(selectedPlan,research)?"账户已选定。下一步点击“确认使用此策略”，保存绑定计划。":"计划已选定。下一步填写方向、股数和价格，再预览订单。";
      select("tex-order",(ledger?.orders||[]).map(row=>[row.order_id,(securities[row.terms.security_id]?.symbol||row.terms.security_id)+" · "+(row.terms.side==="BUY"?"买入":"卖出")+" "+row.terms.quantity+" 股 · "+(labels[row.state]||"状态待核对")]),state.orderId,"请选择原订单");
      if(lastOrder!==state.orderId){lastOrder=state.orderId;for(const id of ["tex-observed-state","tex-observed-qty","tex-observed-notional","tex-observed-fee","tex-cancel-outcome"])$(id).value="";$("tex-confirm-observation").checked=false;}
      $("tex-account-detail").innerHTML=ledger?`<div class="tex-metrics"><div>合成现金<strong>${esc(dollars(ledger.cash))}</strong></div><div>订单预留<strong>${esc(dollars(ledger.reserved_cash))}</strong></div><div>可用现金<strong>${esc(dollars(ledger.available_cash))}</strong></div></div>
        <p class="tex-rule-summary">保存的风险边界：每单不超过 ${esc(dollars(ledger.config.rules?.max_order_notional))} · 现金底线 ${esc(dollars(ledger.config.rules?.cash_floor))} · 每单费用预留 ${esc(dollars(ledger.config.rules?.fee_buffer))}</p>
        <p>${account.paused?"已暂停新增风险。"+(reasons[ledger.stop_reason]||""):""}${account.reconciliation_required?"需要明确的完整合成对账。":"当前本地状态已核对。"}${state.accountStale?" 当前显示上次读取状态；请先重新读取。":""}</p>${account.deficiencies?.length||account.reconciliation_required||account.paused?'<div class="notice warning">'+(account.paused?"新增风险已暂停。":"账户有待核对订单、资金或所属持仓冲突。")+'原观察和预留仍保留。'+action("打开账户核对与恢复","open-advanced")+'</div>':""}
        <details><summary>查看所属持仓与全部风险设置</summary><p class="section-note">总敞口上限 ${esc(dollars(ledger.config.rules?.max_total_exposure))} · 单标的上限 ${esc(dollars(ledger.config.rules?.max_security_exposure))} · 账户亏损上限 ${esc(dollars(ledger.config.rules?.max_account_loss))}</p>${ledger.positions.length?'<div class="tex-table"><table><thead><tr><th>归属</th><th>演练标的</th><th>整股数量</th></tr></thead><tbody>'+ledger.positions.map(row=>`<tr><td>${esc(ownerLabel(row.owner_id))}</td><td>${esc(securities[row.security_id]?.symbol||row.security_id)}</td><td>${esc(row.quantity)}</td></tr>`).join("")+"</tbody></table></div>":'<p class="section-note">尚无成交持仓。</p>'}</details>`:"请选择或创建明确的合成账户。";
      $("tex-orders").innerHTML=ledger?.orders.length?`<div class="tex-table"><table><thead><tr><th>标的 / 方向</th><th>状态</th><th>累计股数</th><th>累计金额 / 费用</th><th>剩余预留</th></tr></thead><tbody>${ledger.orders.map(row=>`<tr><td>${esc(securities[row.terms.security_id]?.symbol||row.terms.security_id)} / ${row.terms.side==="BUY"?"买入":"卖出"}</td><td>${esc(labels[row.state]||"待核对")}</td><td>${esc(row.filled)}</td><td>${esc(dollars(row.notional))} / ${esc(dollars(row.fee))}</td><td>${esc(row.terms.side==="BUY"?dollars(row.reserved_cash):row.reserved_shares+" 股")}</td></tr>`).join("")}</tbody></table></div>`:'<p class="section-note">尚无订单。保存账户和计划不会自动生成订单。</p>';
      const plan=ledger?.plans.find(p=>p.plan_id===state.planId),link=account?.plan_links.find(item=>item.plan_id===state.planId);
      $("tex-plan-detail").textContent=plan?(planMatchesResearch(plan,research)?"当前计划已绑定所选保存版本。"+(link?.owner_continuity==="VERIFIED_TASK_FAMILY"?"持仓归属沿用已核验的原任务族。":"只绑定这一不可变任务；不宣称跨版本持仓连续。") :"当前计划属于另一份保存结果，请为所选结果保存计划，或切换已有计划。") :"";
      const comparison=state.comparison,tag=value=>({MATCH:"记录一致",DIFFERENT:"记录不同",UNKNOWN:"未记录 / 未知"}[value]||"未知");
      $("tex-comparison").innerHTML=comparison?`<h4>已记录的差异</h4><dl class="kv"><dt>数据</dt><dd>${esc(tag(comparison.data?.input_id?.status))}</dd><dt>规则参数</dt><dd>${esc(tag(comparison.rules?.strategy_params?.status))}</dd><dt>费用设置</dt><dd>${esc(tag(comparison.costs?.status))}</dd><dt>成交模型</dt><dd>${esc(tag(comparison.execution_assumptions?.fill_model?.status))}</dd><dt>数量单位</dt><dd>${esc(tag(comparison.execution_assumptions?.quantity_policy?.status))}</dd></dl><p class="section-note">尚未逐笔对齐经济事件；不据此计算跨模型收益差或推断差异原因。</p>`:"";
      const locked=state.busy||Boolean(state.pending),available=Boolean(account)&&!state.accountStale;
      for(const id of ["tex-source","tex-account","tex-plan","tex-order"])$(id).disabled=locked;
      section.querySelectorAll("button").forEach(button=>{const action=button.dataset.texAction;button.disabled=locked&&!["check-pending","refresh"].includes(action);});
      $("tex-create-account").disabled=locked||!readyResearch(research);
      const orderBlocked=locked||!available||!planMatchesResearch(plan,research)||account.reconciliation_required||account.deficiencies?.length>0||(account.paused&&v("tex-side")==="BUY");
      $("tex-preview-order").disabled=orderBlocked;$("tex-submit-order").disabled=orderBlocked||!state.orderPreview;
      renderPreview();
      $("tex-save-observation").disabled=locked||!available||!state.orderId;
      for(const [name,blocked] of [["create-plan",!available||!accountMatchesResearch(account,research)],["compare",!available||!plan||!state.sourceReference],["cancel",!available||!state.orderId],["stop",!available],["resume",!available||!account.paused||account.reconciliation_required||account.deficiencies?.length>0],["begin-reconcile",!available]])section.querySelector(`[data-tex-action="${name}"]`).disabled=locked||blocked;
      renderReconciliation();
    }
    function renderPreview() {
      const preview=state.orderPreview;$("tex-confirm-form").hidden=!preview;
      if(lastPreview!==preview){$("tex-confirm-order").checked=false;lastPreview=preview;}
      if(!preview){$("tex-preview-detail").innerHTML="";return;}
      const t=preview.terms,e=preview.estimate,ledger=state.account.ledger,plan=ledger.plans.find(p=>p.plan_id===t.plan_id),approx=n=>Number.isFinite(n)?"$"+n.toFixed(2):"未记录";
      const held=ledger.positions.filter(p=>p.owner_id===plan.owner_id&&p.security_id===t.security_id).reduce((sum,p)=>sum+p.quantity,0),reserved=ledger.orders.filter(o=>o.terms.owner_id===plan.owner_id&&o.terms.security_id===t.security_id).reduce((sum,o)=>sum+(o.reserved_shares||0),0);
      const scenario={ACCEPTED:"接受（确认后才记录）",REJECTED:"明确拒绝（确认后才记录）",TIMEOUT_UNCONFIRMED:"超时（确认后进入待核对）"}[t.outcome];
      $("tex-preview-detail").innerHTML=`<h4>请核对这笔合成订单</h4><p><strong>${esc(preview.accountLabel)} · ${esc(ledger.config.securities[t.security_id].symbol)} · ${t.side==="BUY"?"买入":"卖出所属持仓"} ${esc(t.quantity)} 股</strong></p><p>限价 ${esc(dollars(t.limit_price))} · 合成参考价 ${esc(dollars(t.quote.price))} · 拟记录场景：${esc(scenario)}</p><p>绑定策略：${esc(sourceLabel(state.sourceReference))} · 保存版本 ${esc(plan.research_binding.task_version)}</p>
        <div class="tex-metrics"><div>当前可用现金<strong>${esc(dollars(ledger.available_cash))}</strong></div><div>当前订单预留<strong>${esc(dollars(ledger.reserved_cash))}</strong></div><div>委托金额粗估<strong>${esc(approx(e.notional))}</strong></div></div>
        <p>${t.side==="BUY"?"本单资金预留粗估（含费用预留）："+esc(approx(e.reservation)):"当前计划归属持仓："+esc(held)+" 股；已预留："+esc(reserved)+" 股。"}</p>${t.outcome==="REJECTED"?'<p>明确拒绝场景不会新增资金预留；上方金额仅为订单规模。</p>':""}
        <p class="section-note">粗估只作核对，以服务端资金、持仓和风险校验为准；不代表成交。参考时点：${esc(new Date(t.signal_at).toLocaleString())}。修改任何订单字段或重新读取账户后，需重新预览。</p>${e.reservation!==null&&e.reservation>e.available?'<p class="notice warning">粗估预留已高于当前可用现金，请先调整；最终仍由服务端校验。</p>':""}`;
    }
    function renderReconciliation() {
      const target=$("tex-reconciliation"),draft=state.reconciliation;target.hidden=!draft;if(!draft){reconKey="";return;}
      const key=draft.account_id+"/"+draft.revision;
      if(key!==reconKey){reconKey=key;target.innerHTML=`<form id="tex-reconcile-form"><h4>另行填写完整合成观察</h4><p class="section-note">这里只带入身份，不带入账本的现金、状态或累计成交数值。请从另一份明确的合成观察逐项填写；没有持仓也请明确填写 0。</p>
        <p>当前账户：${esc(state.account.label)} · 核对的记录版本：${esc(draft.revision)}</p><div id="tex-reconcile-stale" class="notice warning" hidden>账本或账户选择已变化。请重新打开核对表格，不会自动沿用旧观察。</div>
        <div class="form-grid">${field("tex-reconcile-cash","另行观察到的现金（美元）","number","","required step=any")}${field("tex-reconcile-at","独立合成观察时间","datetime-local","","required step=1")}</div>${action("填入当前观察时间","reconcile-time")}
        <h4 class="section-gap">每笔原订单的合成观察</h4><p class="section-note">表格可横向滚动，金额与费用也需逐项填写。</p><div class="tex-table"><table><thead><tr><th>原订单身份</th><th>观察状态</th><th>累计股数</th><th>累计金额（美元）</th><th>累计费用（美元）</th></tr></thead><tbody>${draft.orders.map((row,i)=>`<tr><td><span title="${esc(row.order_id)}">${esc(row.order_id.slice(0,12))}</span></td><td><select id="tex-reconcile-state-${i}" required aria-label="订单 ${i+1} 观察状态"><option value="">请选择</option>${states}</select></td><td><input id="tex-reconcile-qty-${i}" type="number" min="0" step="1" required aria-label="订单 ${i+1} 累计股数"></td><td><input id="tex-reconcile-notional-${i}" type="number" min="0" step="any" required aria-label="订单 ${i+1} 累计金额"></td><td><input id="tex-reconcile-fee-${i}" type="number" min="0" step="any" required aria-label="订单 ${i+1} 累计费用"></td></tr>`).join("")}</tbody></table></div>
        <h4 class="section-gap">每个归属的持仓观察</h4>${draft.positions.map((row,i)=>field("tex-reconcile-position-"+i,esc(ownerLabel(row.owner_id))+" · "+esc(state.account.ledger.config.securities[row.security_id]?.symbol||row.security_id)+" · 观察股数","number","","required min=0 step=1")).join("")||'<p class="section-note">此账户尚无已登记的订单或持仓身份。</p>'}
        <label class="check-label section-gap"><input id="tex-confirm-reconcile" type="checkbox" required>以上是另行提供的完整合成观察，没有把本地账本复制为证明。</label><button id="tex-reconcile-submit" class="btn primary section-gap" type="submit">核对这份完整观察</button></form>`;}
      const stale=state.accountId!==draft.account_id||state.account?.account_context!==draft.account_context||state.account?.ledger.revision!==draft.revision;
      $("tex-reconcile-stale").hidden=!stale;$("tex-reconcile-submit").disabled=stale||state.busy||Boolean(state.pending);
    }
    const fail=error=>{state.error=readableError(error);render();notify(state.error,true);};
    section.addEventListener("input",event=>{if(event.target.closest("#tex-order-form"))controller.invalidatePreview();});
    section.addEventListener("change",event=>{
      const id=event.target.id;
      if(event.target.closest("#tex-order-form"))controller.invalidatePreview();
      if(id==="tex-source")controller.openResearch(event.target.value===""?null:state.sources[Number(event.target.value)]).catch(fail);
      if(id==="tex-account")controller.openAccount(event.target.value,{retain:false}).catch(fail);
      if(id==="tex-plan")try{controller.selectPlan(event.target.value);}catch(error){fail(error);}
      if(id==="tex-order"&&event.target.value)try{controller.selectOrder(event.target.value);}catch(error){fail(error);}
      if(id==="tex-side")render();
    });
    const fillNow=id=>{const date=new Date();date.setMinutes(date.getMinutes()-date.getTimezoneOffset());$(id).value=date.toISOString().slice(0,19);};
    section.addEventListener("click",event=>{
      const target=event.target.closest("[data-tex-action]");if(!target||target.disabled)return;
      const name=target.dataset.texAction;
      const work=async()=>{if(name==="refresh")return controller.refresh();if(name==="check-pending")return controller.checkPending();if(name==="create-plan")return controller.createPlan();if(name==="compare")return controller.compare();
        if(name==="open-account"){$("tex-new-account").open=true;$("tex-name").focus();return;}
        if(name==="open-advanced"){$("tex-advanced").open=true;$("tex-advanced").scrollIntoView({block:"start"});return;}
        if(name==="cancel")return controller.recordCancel(v("tex-cancel-outcome"));if(name==="stop")return controller.control("stop","用户在订单核对页明确暂停新增风险");if(name==="resume")return controller.control(name,v("tex-control-reason"));if(name==="begin-reconcile")return controller.beginReconciliation();if(name==="order-time"){fillNow("tex-order-at");controller.invalidatePreview();return;}if(name==="reconcile-time")return fillNow("tex-reconcile-at");};
      work().catch(fail);
    });
    section.addEventListener("submit",event=>{event.preventDefault();if(!event.target.reportValidity())return;const id=event.target.id;
      const work=async()=>{
        if(id==="tex-account-form")return controller.createAccount({label:v("tex-name"),cash:v("tex-cash"),orderLimit:v("tex-order-limit"),totalLimit:v("tex-total-limit"),securityLimit:v("tex-security-limit"),floor:v("tex-floor"),feeBuffer:v("tex-fee-buffer"),lossLimit:v("tex-loss-limit"),quoteAge:v("tex-quote-age"),tick:v("tex-tick"),confirm:checked("tex-confirm-account")});
        if(id==="tex-order-form")return controller.previewOrder({security:v("tex-security"),side:v("tex-side"),quantity:v("tex-quantity"),limit:v("tex-limit"),quote:v("tex-quote"),at:v("tex-order-at")||new Date().toISOString(),outcome:v("tex-outcome")});
        if(id==="tex-confirm-form")return controller.confirmOrder(checked("tex-confirm-order"));
        if(id==="tex-observation-form")return controller.recordObservation({state:v("tex-observed-state"),quantity:v("tex-observed-qty"),notional:v("tex-observed-notional"),fee:v("tex-observed-fee"),confirm:checked("tex-confirm-observation")});
        if(id==="tex-reconcile-form")return controller.reconcile({cash:v("tex-reconcile-cash"),at:v("tex-reconcile-at"),confirm:checked("tex-confirm-reconcile"),orders:state.reconciliation.orders.map((_,i)=>({state:v("tex-reconcile-state-"+i),quantity:v("tex-reconcile-qty-"+i),notional:v("tex-reconcile-notional-"+i),fee:v("tex-reconcile-fee-"+i)})),positions:state.reconciliation.positions.map((_,i)=>({quantity:v("tex-reconcile-position-"+i)}))});
      };work().then(result=>{if(result&&!state.pending){
        if(id==="tex-account-form"){$("tex-confirm-account").checked=false;event.target.closest("details").open=false;}
        if(id==="tex-confirm-form")$("tex-confirm-order").checked=false;
        if(id==="tex-observation-form")$("tex-confirm-observation").checked=false;
        if(id==="tex-reconcile-form")$("tex-confirm-reconcile").checked=false;
      }}).catch(fail);
    });
    render();
    return {setSources:controller.setSources,refresh:controller.refresh,reveal:()=>{section.hidden=false;section.scrollIntoView({block:"start"});},hide:()=>{section.hidden=true;},controller,element:section};
  }
  const api={createController,install:installTerminalExecutionUI,reconciliationIdentities,readyResearch,accountMatchesResearch};
  root.installTerminalExecutionUI=installTerminalExecutionUI;
  if(typeof module==="object"&&module.exports)module.exports=api;
})(typeof globalThis!=="undefined"?globalThis:window);
