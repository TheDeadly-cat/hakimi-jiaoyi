"use strict";
const assert=require("node:assert/strict"),test=require("node:test");
const ui=require("./terminal-execution-ui");
const permissions={local_simulation_allowed:true,paper_order_allowed:false,live_order_allowed:false,order_allowed:false,broker_connection_allowed:false,model_calls_allowed:false};
const source={kind:"terminal_run",id:"saved-source",label:"TEST 保存研究"};
const copy=v=>JSON.parse(JSON.stringify(v));
function research(ref=source){return {reference:{kind:ref.kind,id:ref.id},binding:{status:"COMPLETED",engine_id:"native-v7",strategy_id:"dual_ma",strategy_params:{fast:5,slow:20},task_id:"task",task_version:1,input_id:"input",report_id:ref.id,report_hash:"a".repeat(64),security_id:"TEST:id"},display:{security_id:"TEST:id",symbol:"TEST",currency:"USD",asset_class:"US_EQUITY"},permissions:copy(permissions)};}
function account(id="account-a") {return {account_id:id,account_context:"context-"+id,label:id,status:"READY_FOR_SYNTHETIC_EXECUTION",paused:false,reconciliation_required:false,deficiencies:[],plan_links:[],permissions:copy(permissions),ledger:{account_id:id,revision:1,cash:"1000",reserved_cash:"0",available_cash:"1000",config:{securities:{"TEST:id":{symbol:"TEST",tick_size:"0.01"}},rules:{fee_buffer:"1",cash_floor:"100",max_order_notional:"500"}},plans:[],orders:[],positions:[]}};}
function fixture(overrides={}) {
  let view=account(),counter=0;const writes=[],reads=[],receipts=new Map();
  const api=async resource=>{reads.push(resource);
    if(resource==="terminal_execution_accounts")return {items:[{account_id:view.account_id,label:view.label}]};
    if(resource.startsWith("terminal_execution_research/"))return research(JSON.parse(decodeURIComponent(resource.split("/").slice(1).join("/"))).reference);
    if(resource.startsWith("terminal_execution_account/"))return copy(view);
    if(resource.startsWith("terminal_execution_receipt/")){const q=JSON.parse(decodeURIComponent(resource.split("/").slice(1).join("/")));return receipts.has(q.request_id)?{status:"COMMITTED",receipt:copy(receipts.get(q.request_id)),permissions:copy(permissions)}:{status:"NOT_RECORDED"};}
    return {status:"CONTEXT_ONLY_NOT_RETURN_COMPARISON"};
  };
  const perform=async(action,payload,options)=>{writes.push({action,payload:copy(payload)});let value;
    if(action==="terminal_execution_create_account"){view=account(payload.account_id);view.creation_request_id=payload.client_request_id;value={status:"ACCOUNT_CREATED",account_id:view.account_id,account:copy(view),permissions:copy(permissions)};}
    else {
      const status=action.endsWith("create_plan")?"PLAN_SAVED":action.endsWith("reconcile")?"RECONCILED":action.endsWith("submit")?payload.outcome:"APPLIED";
      const outcome={status,...(status==="PLAN_SAVED"?{plan_id:"plan-one"}:{})};
      if(status==="PLAN_SAVED")view.ledger.plans=[{plan_id:"plan-one",stage:"SIMULATION",owner_id:"owner-a",research_binding:research().binding}];
      if(status==="TIMEOUT_UNCONFIRMED"){view.reconciliation_required=true;view.deficiencies=[{kind:"UNCONFIRMED_ORDERS"}];}
      const receipt={schema_version:"hakimi-offline-execution-receipt-v1",request_id:payload.client_request_id,account_id:payload.account_id,permissions:copy(permissions),outcome};receipts.set(payload.client_request_id,receipt);
      value={receipt,account:copy(view),permissions:copy(permissions)};
    }
    await options.onSuccess(value);return value;
  };
  const controller=ui.createController({api,perform,uuid:()=>"request-"+(++counter),...overrides});
  controller.setSources([source]);
  return {controller,api,perform,writes,reads,receipts,setView:value=>{view=value;},getView:()=>view};
}
async function selected(f){await f.controller.openResearch(source);await f.controller.openAccount("account-a");}

test("source/account reads never select orders or start a computation",async()=>{
  const f=fixture();await f.controller.refresh();assert.equal(f.controller.state.account,null);
  await selected(f);assert.equal(f.writes.length,0);assert.equal(f.controller.state.planId,"");assert.equal(f.controller.state.orderId,"");
});

test("complete receipt survives auxiliary read failure and a shell exception after callback",async()=>{
  const f=fixture();await selected(f);
  f.controller=ui.createController({api:async()=>{throw Error("aux read failed");},uuid:()=>"request-test",perform:async(action,payload,options)=>{
    const value={receipt:{schema_version:"hakimi-offline-execution-receipt-v1",request_id:payload.client_request_id,account_id:payload.account_id,permissions,outcome:{status:"PLAN_SAVED",plan_id:"saved-plan"}}};
    options.onSuccess(value);throw Error("shell post-refresh failed");}});
  f.controller.state.account=account();f.controller.state.accountId="account-a";
  const result=await f.controller.execute("terminal_execution_create_plan",{client_request_id:"request-test",account_id:"account-a"});
  assert.equal(result.receipt.outcome.status,"PLAN_SAVED");assert.equal(f.controller.state.pending,null);
  assert.match(f.controller.state.fact.message,/计划已保存/);assert.match(f.controller.state.readError,/后续读取未完成/);
});

test("a pre-write account read cannot overwrite acknowledged reserved cash after shell failure",async()=>{
  let finish;const newer=account();newer.ledger.cash="900";newer.ledger.reserved_cash="100";
  const c=ui.createController({api:async()=>new Promise(resolve=>finish=resolve),perform:async(_action,payload,options)=>{
    options.onSuccess({receipt:{schema_version:"hakimi-offline-execution-receipt-v1",request_id:payload.client_request_id,account_id:"account-a",permissions,outcome:{status:"ACCEPTED"}},account:newer});
    throw Error("shell refresh failed");
  }});
  c.state.account=account();c.state.accountId="account-a";
  const oldRead=c.openAccount("account-a");
  await c.execute("terminal_execution_submit",{client_request_id:"saved-request",account_id:"account-a"});
  finish(account());await oldRead;
  assert.equal(c.state.account.ledger.cash,"900");assert.equal(c.state.account.ledger.reserved_cash,"100");assert.equal(c.state.pending,null);
});

test("unknown request is read back by its original id and never automatically resubmitted",async()=>{
  const backend=fixture();let attempts=0;
  const c=ui.createController({api:backend.api,perform:async()=>{attempts++;return null;},uuid:()=>"unique-request"});
  c.state.account=account();c.state.accountId="account-a";
  const payload={client_request_id:"original-request",account_id:"account-a"};
  await c.execute("terminal_execution_submit",payload);assert.ok(c.state.pending);
  await assert.rejects(()=>c.execute("terminal_execution_submit",payload),/上一项操作/);
  await c.checkPending();assert.ok(c.state.pending);assert.equal(attempts,1);
  backend.receipts.set("original-request",{schema_version:"hakimi-offline-execution-receipt-v1",request_id:"original-request",account_id:"account-a",permissions,outcome:{status:"TIMEOUT_UNCONFIRMED"}});
  await c.checkPending();assert.equal(c.state.pending,null);assert.match(c.state.fact.message,/待核对订单/);assert.equal(attempts,1);
});

test("late source and account reads cannot replace a newer user selection",async()=>{
  let firstAccount,firstResearch;
  const c=ui.createController({uuid:()=>"x",perform:async()=>null,api:async path=>{
    if(path==="terminal_execution_account/account-a")return new Promise(resolve=>firstAccount=resolve);
    if(path.startsWith("terminal_execution_account/"))return account("account-b");
    const ref=JSON.parse(decodeURIComponent(path.split("/")[1])).reference;
    return ref.id==="first"?new Promise(resolve=>firstResearch=resolve):research(ref);
  }});
  const older=c.openAccount("account-a");await c.openAccount("account-b");firstAccount(account());await older;assert.equal(c.state.account.account_id,"account-b");
  const sourceOne=c.openResearch({kind:"terminal_run",id:"first"});await c.openResearch({kind:"terminal_run",id:"second"});firstResearch(research({kind:"terminal_run",id:"first"}));await sourceOne;assert.equal(c.state.source.binding.report_id,"second");
});

test("missing trusted security metadata and same-label different identity block new plans",async()=>{
  const f=fixture();await selected(f);
  f.controller.state.source.display={symbol:"TEST"};
  await assert.rejects(()=>f.controller.createPlan(),/证券身份/);
  f.controller.state.source=research();f.controller.state.source.display.security_id="OTHER:TEST";
  await assert.rejects(()=>f.controller.createPlan(),/精确一致/);assert.equal(f.writes.length,0);
});

test("an order cannot choose another security than its saved plan",async()=>{
  const f=fixture();await selected(f);const view=f.controller.state.account;
  view.ledger.config.securities["OTHER:id"]={symbol:"OTHER"};view.ledger.plans=[{plan_id:"plan-one",stage:"SIMULATION",research_binding:research().binding}];f.controller.selectPlan("plan-one");
  await assert.rejects(()=>f.controller.submitOrder({confirm:true,side:"BUY",outcome:"ACCEPTED",security:"OTHER:id"}),/保存计划绑定/);
  assert.equal(f.writes.length,0);
});

test("reconciliation prefill contains identities only, never local economic observations",()=>{
  const view=account();view.ledger.cash="777";view.ledger.orders=[{order_id:"order-one",state:"PARTIAL",filled:3,notional:"30",fee:"1",terms:{owner_id:"owner-a",security_id:"TEST:id",quantity:10}}];view.ledger.positions=[{owner_id:"owner-a",security_id:"TEST:id",quantity:7}];
  const draft=ui.reconciliationIdentities(view);
  assert.deepEqual(draft.orders,[{order_id:"order-one"}]);assert.deepEqual(draft.positions,[{owner_id:"owner-a",security_id:"TEST:id"}]);
  for(const field of ["cash","state","filled","quantity","notional","fee"])assert.equal(Object.hasOwn(draft,field),false);
});

test("reconciliation requires explicit cash/order/position entries and sends those values unchanged",async()=>{
  const f=fixture(),view=account();view.ledger.cash="777";view.ledger.orders=[{order_id:"order-one",terms:{owner_id:"owner-a",security_id:"TEST:id"}}];view.ledger.positions=[{owner_id:"owner-a",security_id:"TEST:id",quantity:7}];f.setView(view);
  await selected(f);f.controller.beginReconciliation();
  const form={cash:"90",at:new Date().toISOString(),confirm:true,orders:[{state:"PARTIAL",quantity:"3",notional:"30",fee:"0.3"}],positions:[{quantity:"2"}]};
  await assert.rejects(()=>f.controller.reconcile({...form,cash:""}),/现金/);assert.equal(f.writes.length,0);
  await f.controller.reconcile(form);
  const sent=f.writes[0].payload.complete_snapshot;assert.equal(sent.cash,"90");assert.equal(sent.orders[0].cumulative_quantity,3);assert.equal(sent.positions[0].quantity,2);
  assert.notEqual(sent.cash,view.ledger.cash);assert.notEqual(sent.positions[0].quantity,view.ledger.positions[0].quantity);
});

test("stale reconciliation revision and failed account reads block mutation without new requests",async()=>{
  const f=fixture();await selected(f);f.controller.beginReconciliation();
  const next=account();next.ledger.revision=2;f.setView(next);await f.controller.openAccount("account-a");
  await assert.rejects(()=>f.controller.reconcile({}),/记录已变化/);assert.equal(f.writes.length,0);
  const bad=ui.createController({api:async()=>{throw Error("read unavailable");},perform:async()=>{throw Error("must not write");}});
  await bad.openAccount("account-a");await assert.rejects(()=>bad.control("stop","reason"),/重新读取/);
});

test("late context comparison cannot overwrite a newly selected plan",async()=>{
  let finish;const f=fixture();await selected(f);
  const c=ui.createController({api:async()=>new Promise(resolve=>finish=resolve),perform:f.perform});
  c.state.account=account();c.state.accountId="account-a";c.state.planId="first";c.state.sourceReference=source;
  const pending=c.compare();c.state.planId="second";finish({status:"old-result"});await pending;assert.equal(c.state.comparison,null);
});

const orderForm=()=>({security:"TEST:id",side:"BUY",quantity:"4",limit:"10",quote:"9.9",at:new Date().toISOString(),outcome:"ACCEPTED"});
async function planned(f){await selected(f);await f.controller.createPlan();return f;}

test("preview requires explicit direction and writes nothing until separate confirmation",async()=>{
  const f=await planned(fixture()),before=f.writes.length,form=orderForm();
  assert.throws(()=>f.controller.previewOrder({...form,side:""}),/方向/);
  const preview=f.controller.previewOrder(form);
  assert.equal(f.writes.length,before);assert.equal(preview.terms.quantity,4);assert.equal(preview.estimate.notional,40);assert.equal(preview.estimate.reservation,41);
  assert.equal(preview.estimate.available,1000);assert.equal(preview.accountLabel,"account-a");
  await assert.rejects(()=>f.controller.confirmOrder(false),/明确确认/);assert.equal(f.writes.length,before);
  await f.controller.confirmOrder(true);assert.equal(f.writes.length,before+1);
  assert.equal(f.writes.at(-1).action,"terminal_execution_submit");assert.equal(f.writes.at(-1).payload.signal_at,Date.parse(form.at));
  await assert.rejects(()=>f.controller.confirmOrder(true),/预览已失效/);assert.equal(f.writes.length,before+1);
});

test("changed source, account revision and edited order each invalidate the original preview",async()=>{
  const f=await planned(fixture()),before=f.writes.length;
  f.controller.previewOrder(orderForm());f.controller.state.account.ledger.revision++;
  await assert.rejects(()=>f.controller.confirmOrder(true),/预览已失效/);
  f.controller.previewOrder(orderForm());f.controller.invalidatePreview();
  await assert.rejects(()=>f.controller.confirmOrder(true),/预览已失效/);
  f.controller.previewOrder(orderForm());await f.controller.openResearch({...source,id:"different-saved-result"});
  assert.equal(f.controller.state.orderPreview,null);
  assert.throws(()=>f.controller.previewOrder(orderForm()),/所选保存结果不同/);
  assert.equal(f.writes.length,before);
});

test("clearing a selection cancels pending reads and cannot retain an actionable preview",async()=>{
  let finish;const f=await planned(fixture());f.controller.previewOrder(orderForm());
  await f.controller.openAccount("");assert.equal(f.controller.state.account,null);assert.equal(f.controller.state.orderPreview,null);
  const c=ui.createController({api:()=>new Promise(resolve=>finish=resolve),perform:async()=>assert.fail("no write")});
  const pending=c.openResearch(source);await c.openResearch(null);finish(research());await pending;
  assert.equal(c.state.source,null);assert.equal(c.state.sourceReference,null);
});

test("confirmed preview with unknown receipt retains its request and never submits again",async()=>{
  const f=await planned(fixture()),attempts=[];
  const c=ui.createController({api:f.api,uuid:()=>"preview-original-request",perform:async(action,payload)=>{attempts.push({action,payload});return null;}});
  Object.assign(c.state,{account:copy(f.controller.state.account),accountId:"account-a",planId:"plan-one",source:research(),sourceReference:source});
  c.previewOrder(orderForm());await c.confirmOrder(true);assert.equal(attempts.length,1);assert.ok(c.state.pending);
  await c.checkPending();assert.equal(attempts.length,1);assert.equal(c.state.pending.payload.client_request_id,attempts[0].payload.client_request_id);
  assert.throws(()=>c.previewOrder(orderForm()),/原操作/);assert.equal(c.state.orderPreview,null);
});

function explanationFixture() {
  return {schema_version:"hakimi-execution-explanation-v1",status:"BOUND_REPORT_CONTEXT_ONLY",summary:"只说明记录条件，不计算收益差贡献。",
    scope:{account_id:"account-a",plan_id:"plan-one",ledger_revision:1,reference_report_hash:"a".repeat(64)},permissions:copy(permissions),
    attribution:{numeric_performance_comparison_allowed:false,contributions:null},
    groups:[["DATA","数据"],["RULES","规则"],["TIMING","时点"],["MATCHING","撮合"],["COSTS","费用"],["UNKNOWN","未知"]].map(([id,label])=>({id,label,counts:{MATCH:0,DIFFERENT:0,UNKNOWN:1},default_open:true,
      items:[{id:id.toLowerCase(),label:label+"说明",status:"UNKNOWN",explanation:"未记录仍保持未知。",research:{value:null,evidence_ref:[{source:"SAVED_PROJECTION",report_hash:"a".repeat(64),pointer:"/conditions/example"}]},simulation:{value:null,evidence_ref:[{source:"UNRECORDED",reason:"NOT_RECORDED"}]}}]})),
    account_scope:{label:"整个合成账户，跨策略共享；不是本计划收益",cash:"1000",reserved_cash:"0",available_cash:"1000",owner_positions:[]}};
}

test("six-group explanation uses read-only resource with account context and preserves preview",async()=>{
  const f=await planned(fixture()),calls=[];f.controller.previewOrder(orderForm());
  const c=ui.createController({api:async path=>{calls.push(path);return explanationFixture();},perform:async()=>assert.fail("comparison cannot mutate")});
  Object.assign(c.state,copy(f.controller.state));const preview=copy(c.state.orderPreview);
  await c.compare();
  assert.equal(calls.length,1);assert.ok(calls[0].startsWith("terminal_execution_explanation/"));
  assert.deepEqual(JSON.parse(decodeURIComponent(calls[0].split("/")[1])),{account_id:"account-a",account_context:"context-account-a",plan_id:"plan-one",reference:{kind:"terminal_run",id:"saved-source"}});
  assert.equal(c.state.comparison.schema_version,"hakimi-execution-explanation-v1");assert.deepEqual(c.state.orderPreview,preview);
});

test("explanation reads reject wrong identity, revision, schema and external permissions",async()=>{
  for(const corrupt of [v=>v.scope.account_id="other",v=>v.scope.plan_id="other",v=>v.scope.ledger_revision=2,v=>v.scope.reference_report_hash="wrong",v=>v.permissions.live_order_allowed=true,v=>v.attribution.contributions=[],v=>v.schema_version="old"]){
    const value=explanationFixture();corrupt(value);
    const f=await planned(fixture()),c=ui.createController({api:async()=>value,perform:async()=>assert.fail("read only")});Object.assign(c.state,copy(f.controller.state));
    await c.compare();assert.equal(c.state.comparison,null);assert.match(c.state.readError,/差异资料/);
  }
});

test("late explanation success or error cannot override changed account context or ledger",async()=>{
  for(const change of [s=>s.account.account_context="new-context",s=>s.account.ledger.revision++,s=>s.sourceReference={kind:"core_run",id:"new-source"}]){
    for(const rejectRead of [false,true]){
      let finish,fail;const f=await planned(fixture()),c=ui.createController({api:()=>new Promise((resolve,reject)=>{finish=resolve;fail=reject;}),perform:async()=>assert.fail("read only")});Object.assign(c.state,copy(f.controller.state));
      const pending=c.compare();change(c.state);c.state.readError="new current notice";
      if(rejectRead)fail(Error("old error"));else finish(explanationFixture());await pending;
      assert.equal(c.state.comparison,null);assert.equal(c.state.readError,"new current notice");
    }
  }
});

test("explanation HTML keeps six groups, units, read-only evidence and escapes report text",()=>{
  const value=explanationFixture();value.status="ONLY_CONTEXT_NO_ATTRIBUTION";value.summary="当前报告不是此计划绑定的原报告。";
  value.groups[0].items[0].research.value='<img src=x onerror="bad()">';
  value.groups[4].items[0].research={value:20,unit:"basis_points",evidence_ref:[]};
  const html=ui.renderExecutionExplanation(value);
  assert.equal((html.match(/data-tex-explanation-group=/g)||[]).length,6);
  assert.equal((html.match(/data-tex-evidence/g)||[]).length,6);
  assert.match(html,/基点（1 = 0.01%）/);assert.match(html,/查看只读依据/);assert.match(html,/未记录 \/ 未知/);
  assert.match(html,/跨策略共享/);assert.match(html,/当前报告不是/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);
  assert.doesNotMatch(html,/<button|<input|<form/);
});

test("human version labels preserve recorded identity and never invent missing revisions",()=>{
  for(const value of [1,"1","r0001-ad0123"]){assert.equal(ui.displayVersion(value),"版本 1");}
  assert.equal(ui.savedResultTitle("TEST · 版本1 · 保存结果","r0001-ad0123"),"TEST · 版本1 · 保存结果");
  assert.equal(ui.savedResultTitle("TEST 保存结果","r0002-ad0123"),"TEST 保存结果 · 版本 2");
  for(const value of [undefined,null,"",0,"immutable-task-hash","rX-guess","r000000000000000000000000000000001234567890123456789"]){assert.equal(ui.displayVersion(value),"版本未记录");}
});

test("human version formatting cannot weaken exact preview version binding",async()=>{
  const f=await planned(fixture()),original="r0001-ad0123";
  f.controller.state.source.binding.task_version=original;
  f.controller.state.account.ledger.plans[0].research_binding.task_version=original;
  f.controller.previewOrder(orderForm());
  assert.match(f.controller.state.orderPreview.stamp,/r0001-ad0123/);
  assert.equal(ui.displayVersion(original),"版本 1");
  f.controller.state.source.binding.task_version="r0001-different";
  await assert.rejects(()=>f.controller.confirmOrder(true),/预览已失效/);
  assert.equal(f.writes.filter(row=>row.action==="terminal_execution_submit").length,0);
});

// Explicitly fictional protocol fixtures; no research, market or ledger runs.
function factorFixture(options={}) {
  const ref={kind:"terminal_run",id:"b".repeat(64),label:"QA · 已保存动量研究 · 版本 1"};
  const engine="terminal.fixture-signals-v1",params={window:20,threshold:0.015},sources=Object.fromEntries(["backtest_engine.py","strategy_signals.py","market_calendar.py","indicator_math.py"].map(k=>[k,"c".repeat(64)]));
  const binding={status:"COMPLETED",engine_id:engine,strategy_id:"momentum",strategy_params:copy(params),task_id:"d".repeat(64),task_version:1,input_id:"e".repeat(64),report_id:ref.id,report_hash:ref.id,security_id:"TEST:id",risk:{position_pct:25},costs:{fee_rate:0.001,slippage_bps:5}};
  const researchValue={reference:{kind:ref.kind,id:ref.id},binding,display:{symbol:"TEST",security_id:"TEST:id",currency:"USD",asset_class:"US_EQUITY"},permissions:copy(permissions)};
  const report={schema_version:"hakimi-terminal-run-v1",status:"COMPLETED",id:ref.id,run_id:ref.id,report_hash:ref.id,task_id:binding.task_id,version:1,engine_id:engine,strategy_id:"momentum",
    configuration:{engine_id:engine,strategy_params:copy(params),risk:copy(binding.risk),costs:copy(binding.costs),input_id:binding.input_id,fingerprint:"f".repeat(64),engine_source_identity:sources,indicator_contract:{version:"FICTIONAL_UNIT_CONTRACT"}},
    input_summary:{id:binding.input_id,input_id:binding.input_id,source_digest:"a".repeat(64),digest:"a".repeat(64),symbol:"TEST",date_start:"2026-01-05",date_end:"2026-06-05",meta:{security_id:"TEST:id"}}};
  const closed={research_only:true,paper_allowed:false,live_allowed:false,order_allowed:false};
  const diagnostic=holding=>({schema_version:"hakimi-terminal-strategy-diagnostic-v1",diagnostic_id:"1".repeat(64),input_id:binding.input_id,source_digest:report.input_summary.source_digest,symbol:"TEST",cutoff_session:"2026-06-05",
    engine_id:engine,signal_engine_version:"fixture-signals-v1",strategy_id:"momentum",strategy_params:copy(params),fingerprint:report.configuration.fingerprint,engine_source_identity:copy(sources),indicator_contract:copy(report.configuration.indicator_contract),
    position_context:{has_position:holding},freshness:{context:"SAVED_HISTORICAL_INPUT",live_quote_verified:false,cutoff_session:"2026-06-05"},status:"READY",decision_matches_factors:true,signal:{action:holding?"EXIT":"BUY"},
    factors:[{key:"momentum",label:"20 日动量",value:holding?-0.03:0.03,operator:holding?"<":">",threshold:holding?-0.015:0.015,unit:"ratio",cutoff_session:"2026-06-05",passed:true,applies_to_position:true}],new_economic_runs:0,permissions:copy(closed)});
  const response=holding=>({schema_version:"hakimi-terminal-strategy-candidates-v1",read_only:true,input_id:binding.input_id,cutoff_session:"2026-06-05",new_economic_runs:0,permissions:copy(closed),groups:[{key:holding?"EXIT_MATCH":"ENTRY_MATCH",items:[diagnostic(holding)]}]});
  const view=account();view.ledger.plans=[{plan_id:"plan-one",stage:"SIMULATION",owner_id:"owner-one",research_binding:copy(binding)}];view.plan_links=[{plan_id:"plan-one",reference:researchValue.reference}];
  const reads=[],writes=[];
  const api=async resource=>{reads.push(resource);if(options.read){const value=await options.read(resource);if(value!==undefined)return value;}
    if(resource==="terminal_execution_accounts")return {items:[{account_id:view.account_id,label:"QA 合成账户"}]};
    if(resource.startsWith("terminal_execution_research/"))return copy(researchValue);
    if(resource.startsWith("terminal_runs/"))return copy(report);
    if(resource.startsWith("terminal_execution_account/"))return copy(view);
    if(resource.startsWith("terminal_strategy_candidates/")){const p=JSON.parse(decodeURIComponent(resource.split('/')[1]));return response(p.position_context.has_position);}
    throw Error('unexpected read '+resource);
  };
  const c=ui.createController({api,perform:async(...args)=>{writes.push(args);throw Error('factor fixture forbids mutations');}});c.setSources([ref]);
  return {c,api,ref,researchValue,report,view,diagnostic,response,reads,writes};
}
async function factorPlanned(f){await f.c.openResearch(f.ref);await f.c.openAccount(f.view.account_id);f.c.selectPlan("plan-one");return f;}

test("saved report review requires every report/task/input/engine/parameter/source/fingerprint binding",()=>{
  const f=factorFixture(),valid=ui.savedRuleContext(f.report,f.researchValue,f.ref);assert.equal(valid.cutoff_session,"2026-06-05");assert.deepEqual(valid.strategy_params,{window:20,threshold:0.015});
  const reordered=copy(f.report);reordered.configuration.strategy_params={threshold:0.015,window:20};assert.deepEqual(ui.savedRuleContext(reordered,f.researchValue,f.ref).strategy_params,reordered.configuration.strategy_params);
  for(const corrupt of [r=>r.id="2".repeat(64),r=>r.run_id="2".repeat(64),r=>r.report_hash="2".repeat(64),r=>r.task_id="2".repeat(64),r=>r.version=2,r=>r.status="UNKNOWN",r=>r.engine_id="other",r=>r.configuration.engine_id="other",r=>r.strategy_id="dual_ma",r=>r.configuration.input_id="2".repeat(64),r=>r.input_summary.id="2".repeat(64),r=>r.input_summary.input_id="2".repeat(64),r=>delete r.input_summary.source_digest,r=>r.input_summary.digest="2".repeat(64),r=>r.input_summary.symbol="OTHER",r=>r.input_summary.meta.security_id="OTHER",r=>delete r.configuration.fingerprint,r=>delete r.configuration.engine_source_identity['indicator_math.py'],r=>delete r.configuration.indicator_contract,r=>r.configuration.strategy_params.threshold=0.02,r=>delete r.configuration.strategy_params.window,r=>r.configuration.risk.position_pct=50,r=>r.configuration.costs.fee_rate=0.02,r=>r.input_summary.date_end="2026-02-31"]){const r=copy(f.report);corrupt(r);assert.throws(()=>ui.savedRuleContext(r,f.researchValue,f.ref),/无法取得一致解释/);}
});
test("read-only factors use exact saved raw parameters/cutoff and an explicitly selected position scenario",async()=>{
  const f=await factorPlanned(factorFixture()),c=f.c;assert.equal(c.state.factorPosition,"");await c.readFactors();assert.equal(f.reads.filter(r=>r.startsWith('terminal_strategy_candidates/')).length,0);
  c.setFactorPosition("flat");const preview=c.previewOrder(orderForm());await c.readFactors();assert.deepEqual(c.state.orderPreview,preview);assert.equal(c.state.factorReview.row.signal.action,"BUY");
  const p=JSON.parse(decodeURIComponent(f.reads.at(-1).split('/')[1]));assert.deepEqual(p,{input_id:f.report.configuration.input_id,strategy_id:"momentum",strategy_params:{window:20,threshold:0.015},cutoff_session:"2026-06-05",position_context:{has_position:false}});assert.equal(f.writes.length,0);
  c.setFactorPosition("holding");assert.equal(c.state.factorReview,null);assert.equal(c.state.orderPreview,null);await c.readFactors();assert.equal(c.state.factorReview.row.signal.action,"EXIT");assert.equal(f.writes.length,0);
});
test("matching report IDs cannot hide different plan rule parameters in an order preview",async()=>{
  const f=await factorPlanned(factorFixture());f.c.state.account.ledger.plans[0].research_binding.strategy_params.threshold=0.02;
  assert.throws(()=>f.c.previewOrder(orderForm()),/所选保存结果不同/);assert.equal(f.writes.length,0);
});
test("factor identity, raw parameters, code fingerprint, historical cutoff and scenario cannot be substituted",()=>{
  const f=factorFixture(),context=ui.savedRuleContext(f.report,f.researchValue,f.ref);
  for(const corrupt of [v=>v.input_id="2".repeat(64),v=>v.cutoff_session="2026-06-08",v=>v.read_only=false,v=>v.new_economic_runs=1,v=>v.groups.push(copy(v.groups[0])),v=>v.permissions.order_allowed=true,
    v=>v.groups[0].items[0].engine_id="other",v=>v.groups[0].items[0].input_id="2".repeat(64),v=>v.groups[0].items[0].source_digest="2".repeat(64),v=>v.groups[0].items[0].strategy_id="dual_ma",v=>v.groups[0].items[0].strategy_params.threshold=0.02,v=>delete v.groups[0].items[0].strategy_params.window,v=>v.groups[0].items[0].fingerprint="2".repeat(64),v=>v.groups[0].items[0].engine_source_identity['backtest_engine.py']="2".repeat(64),v=>v.groups[0].items[0].indicator_contract.version="other",v=>v.groups[0].items[0].position_context.has_position=true,v=>v.groups[0].items[0].cutoff_session="2026-06-08",v=>v.groups[0].items[0].factors[0].cutoff_session="2026-06-08",v=>v.groups[0].items[0].freshness.live_quote_verified=true,v=>v.groups[0].items[0].status="DATA_INSUFFICIENT",v=>v.groups[0].items[0].decision_matches_factors=false]){const v=f.response(false);corrupt(v);assert.throws(()=>ui.savedFactorContext(v,context,false),/无法取得一致解释/);}
});
test("factor read errors preserve an already successful order preview and prior completion fact",async()=>{
  const f=await factorPlanned(factorFixture({read:async r=>{if(r.startsWith('terminal_strategy_candidates/'))throw Error('read unavailable');}})),c=f.c;c.setFactorPosition('flat');const preview=c.previewOrder(orderForm());c.state.fact={message:'原保存已确认',status:'ACCEPTED'};
  await c.readFactors();assert.deepEqual(c.state.orderPreview,preview);assert.equal(c.state.factorReview,null);assert.match(c.state.factorError,/read unavailable.*已有订单预览仍保留/);assert.equal(c.state.fact.message,'原保存已确认');assert.equal(c.state.error,'');assert.equal(f.writes.length,0);
});
test("late factor success and failure cannot replace a changed source, account revision, scenario or newer preview",async()=>{
  for(const change of ['source','revision','scenario','preview'])for(const rejectRead of [false,true]){
    let resolve,reject;const f=await factorPlanned(factorFixture({read:r=>r.startsWith('terminal_strategy_candidates/')?new Promise((a,b)=>{resolve=a;reject=b;}):undefined})),c=f.c;c.setFactorPosition('flat');c.previewOrder(orderForm());const pending=c.readFactors();await new Promise(r=>setImmediate(r));
    if(change==='source')await c.openResearch(null);if(change==='revision'){f.view.ledger.revision++;await c.openAccount(f.view.account_id);}if(change==='scenario')c.setFactorPosition('holding');if(change==='preview'){c.invalidatePreview();c.previewOrder({...orderForm(),quantity:'2'});}
    const preview=copy(c.state.orderPreview);c.state.factorError='当前提示';if(rejectRead)reject(Error('old read failure'));else resolve(f.response(false));await pending;assert.equal(c.state.factorReview,null);assert.equal(c.state.factorError,'当前提示');assert.deepEqual(c.state.orderPreview,preview);assert.equal(c.state.factorBusy,false);assert.equal(f.writes.length,0);
  }
});
test("old-engine or incomplete report stays unavailable and never falls back to a same-name strategy",async()=>{
  const f=factorFixture({read:r=>r.startsWith('terminal_runs/')?{}:undefined});await f.c.openResearch(f.ref);assert.equal(f.c.state.sourceRuleContext,null);assert.match(f.c.state.sourceRuleError,/无法取得一致解释/);f.c.setFactorPosition('flat');await f.c.readFactors();assert.equal(f.reads.some(r=>r.startsWith('terminal_strategy_candidates/')),false);
  const core=factorFixture();await core.c.openResearch({kind:'core_run',id:'other-engine'});assert.equal(core.reads.some(r=>r.startsWith('terminal_runs/')),false);assert.equal(core.c.state.sourceRuleContext,null);
});
test("rule review displays historical dates, percent units and explicit explanation provenance without HTML injection",()=>{
  const f=factorFixture(),context=ui.savedRuleContext(f.report,f.researchValue,f.ref),row=ui.savedFactorContext(f.response(true),context,true);row.factors[0].label='<img src=x onerror=bad()>';
  const html=ui.renderRuleReview(context,{row});assert.match(html,/历史数据截至 2026-06-05/);assert.match(html,/1.5%/);assert.match(html,/已有持仓.*历史日满足退出条件/);assert.match(html,/不是原报告已保存的因子/);assert.match(html,/不是当前买入指令/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img|<button|<input/);
});
test("rule review separates legacy 3% stop compatibility from the report's actual 8% execution risk without changing raw parameters",()=>{
  const f=factorFixture(),params={fast_window:20,slow_window:60,position_pct:0.25,stop_loss_pct:0.03,take_profit_pct:0.06,unknown_legacy_field:0.07},risk={position_pct:25,stop_loss_pct:8,take_profit_pct:0,leverage:1};
  f.report.strategy_id=f.researchValue.binding.strategy_id='dual_ma';f.report.configuration.strategy_params=copy(params);f.researchValue.binding.strategy_params=copy(params);f.report.configuration.risk=copy(risk);f.researchValue.binding.risk=copy(risk);
  const before=copy({report:f.report,research:f.researchValue}),context=ui.savedRuleContext(f.report,f.researchValue,f.ref),html=ui.renderRuleReview(context,null);
  const signals=html.match(/<details open data-tex-signal-params>(.*?)<\/details>/s)[1],compatibility=html.match(/<details data-tex-compatibility-params>(.*?)<\/details>/s)[1],saved=html.match(/<p data-tex-saved-risk>(.*?)<\/p>/s)[1],other=html.match(/<details data-tex-other-params>(.*?)<\/details>/s)[1];
  assert.match(signals,/快均线周期.*20.*慢均线周期.*60/);assert.doesNotMatch(signals,/旧仓位|旧止损|旧止盈|unknown_legacy/);assert.match(compatibility,/旧仓位比例.*25%.*旧止损比例.*3%.*旧止盈比例.*6%/);assert.match(compatibility,/不作为本报告的执行风险条件/);assert.match(saved,/仓位 25%.*止损 8%.*止盈 0%/);assert.doesNotMatch(saved,/止损 3%/);assert.match(other,/unknown_legacy_field.*0.07/);assert.doesNotMatch(other,/7%/);
  assert.deepEqual(context.strategy_params,params);assert.deepEqual(context.execution_risk,risk);assert.deepEqual({report:f.report,research:f.researchValue},before);
});

test("factor-review DOM: explicit GET only, preview survives read failure, scenario invalidates at 1280 and 480",async t=>{
  const fs=require('node:fs'),path=require('node:path'),{chromium}=require('playwright');const executablePath=[process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,chromium.executablePath(),'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(v=>v&&fs.existsSync(v));
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),args:['--disable-background-networking','--no-first-run']});t.after(()=>browser.close());
  for(const width of [1280,480]){
    let failFactors=false;const f=factorFixture({read:r=>{if(failFactors&&r.startsWith('terminal_strategy_candidates/'))throw Error('explicit synthetic read failure');}}),context=await browser.newContext({viewport:{width,height:960}}),page=await context.newPage(),errors=[],external=[];t.after(()=>context.close());page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await context.route('**/*',r=>{if(r.request().url()==='http://127.0.0.1:55321/')return r.fulfill({contentType:'text/html',body:'<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px/1.6 system-ui;margin:24px}.panel{border:1px solid #ccd4e0;padding:16px}.section-gap{margin-top:20px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label{display:block}input,select{max-width:100%;box-sizing:border-box;width:100%}input[type=checkbox]{width:auto}.kv{display:grid;grid-template-columns:1fr 1fr}.notice{padding:12px;background:#eef4ff}.actions{display:flex;gap:10px;flex-wrap:wrap}button,input,select{font:inherit}.btn{padding:8px 14px}</style><main id="host"></main>'});external.push(r.request().url());return r.abort();});
    await page.exposeFunction('readFixture',f.api);await page.exposeFunction('writeFixture',()=>{f.writes.push('unexpected');throw Error('No mutation allowed');});await page.goto('http://127.0.0.1:55321/');await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,'terminal-execution-ui.js'),'utf8')});
    await page.evaluate(ref=>{window.ui=installTerminalExecutionUI({host:document.querySelector('#host'),api:readFixture,perform:writeFixture});ui.setSources([ref]);ui.reveal();},f.ref);assert.equal(f.reads.length,0);
    await page.selectOption('#tex-source','0');await page.waitForFunction(()=>ui.controller.state.sourceRuleContext);await page.evaluate(async()=>{await ui.refresh();});await page.selectOption('#tex-account','account-a');await page.waitForFunction(()=>ui.controller.state.account&&!ui.controller.state.accountStale);await page.evaluate(()=>ui.controller.selectPlan('plan-one'));
    assert.equal(await page.locator('#tex-side').inputValue(),'');assert.equal(await page.locator('#tex-factor-position').inputValue(),'');assert.equal(await page.locator('[data-tex-action=read-factors]').isDisabled(),true);await page.selectOption('#tex-factor-position','flat');await page.locator('[data-tex-action=read-factors]').click();await page.waitForFunction(()=>ui.controller.state.factorReview);assert.equal(await page.locator('#tex-side').inputValue(),'');
    await page.selectOption('#tex-side','BUY');await page.fill('#tex-quantity','1');await page.fill('#tex-limit','10');await page.fill('#tex-quote','10');await page.locator('#tex-preview-order').click();await page.waitForFunction(()=>ui.controller.state.orderPreview);assert.match(await page.locator('[data-tex-preview-cutoff]').innerText(),/2026-06-05/);assert.equal(await page.locator('[data-tex-preview-evidence]').getAttribute('open'),null);assert.equal(await page.evaluate(()=>document.querySelector('#tex-preview-detail .tex-metrics').getBoundingClientRect().top<document.querySelector('[data-tex-preview-cutoff]').getBoundingClientRect().top),true);await page.locator('[data-tex-preview-evidence]>summary').click();assert.match(await page.locator('[data-tex-preview-rule]').innerText(),/历史数据截至 2026-06-05/);assert.match(await page.locator('[data-tex-preview-rule]').innerText(),/1.5%/);assert.match(await page.locator('[data-tex-preview-rule]').innerText(),/不是原报告已保存的因子/);
    failFactors=true;await page.locator('[data-tex-action=read-factors]').click();await page.waitForFunction(()=>!ui.controller.state.factorBusy&&ui.controller.state.factorError);assert.equal(await page.locator('#tex-confirm-form').isVisible(),true);assert.equal(await page.locator('#tex-confirm-order').isChecked(),false);assert.equal(f.writes.length,0);
    await page.selectOption('#tex-factor-position','holding');assert.equal(await page.locator('#tex-confirm-form').isVisible(),false);failFactors=false;await page.locator('[data-tex-action=read-factors]').click();await page.waitForFunction(()=>ui.controller.state.factorReview?.row.signal.action==='EXIT');assert.equal(await page.locator('#tex-side').inputValue(),'BUY');await page.locator('#tex-preview-order').click();await page.waitForFunction(()=>ui.controller.state.orderPreview);assert.equal(await page.locator('[data-tex-preview-evidence]').getAttribute('open'),null);await page.locator('[data-tex-preview-evidence]>summary').click();assert.match(await page.locator('[data-tex-preview-rule]').innerText(),/已有持仓.*历史日满足退出条件/);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);if(process.env.EXECUTION_FACTOR_EVIDENCE_DIR)await page.screenshot({path:path.join(process.env.EXECUTION_FACTOR_EVIDENCE_DIR,'order-factor-'+width+'.png'),fullPage:true});assert.equal(f.writes.length,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);await context.close();
  }
});
