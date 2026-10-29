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
