"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),{createHash}=require("node:crypto");
const ui=require("./terminal-broker-candidate-ui");
const permissions={external_connection_allowed:false,submit_allowed:false,query_allowed:false,cancel_allowed:false,unlock_allowed:false,adapter_installed:false,automatic_resume:false,automatic_retry:false};
const copy=v=>JSON.parse(JSON.stringify(v)),hash=v=>createHash("sha256").update(JSON.stringify(v)).digest("hex");
const source={kind:"terminal_run",id:"a".repeat(64),label:"TEST · 已完成版本1"},SIM="OFFICIAL_SIMULATION",LIVE="LIVE_CANDIDATE";
function research(reference=source){return {reference:{kind:reference.kind,id:reference.id},binding:{schema_version:"hakimi-offline-research-binding-v1",status:"COMPLETED",report_hash:reference.id,report_id:reference.id,task_version:1,security_id:"QA:TEST"},display:{security_id:"QA:TEST",symbol:"TEST",currency:"USD",asset_class:"US_EQUITY"},permissions:copy(permissions)};}
const form=()=>({account_id:"900000000000001",market:"US",asset_code:"US.TEST",max_quantity:"2",max_notional:"50.00",side:"BUY",quantity:"1",limit_price:"20.00",expires_at:new Date(Date.now()+3600000).toISOString()});
function fixture(overrides={}){
  let seq=0;const reads=[],writes=[],stops=[],records=new Map(),configs=new Map();
  const status={schema_version:"hakimi-broker-candidate-v2",connection_state:"NOT_CONNECTED",read_only:true,permissions:copy(permissions),sdk:{metadata_status:"NOT_PROVIDED",runtime_compatibility:"NOT_VERIFIED"},
    modes:[SIM,LIVE].map(mode=>({mode,connected:false,state:"NOT_CONFIGURED",permissions:copy(permissions),configurations:[],control:{new_intents_blocked:false,latest_control_receipt_id:null,latest_stop_receipt_id:null,resume_allowed:false}}))};
  const row=mode=>status.modes.find(v=>v.mode===mode);
  function receipt(action,p,result){const value={schema_version:action==="stop"||action==="resume"?"hakimi-broker-candidate-control-v1":"hakimi-broker-candidate-v2",id:hash(p),mode:p.mode,action,request_id:p.request_id,created_at:new Date().toISOString(),result:copy(result)};records.set(p.mode+":"+p.request_id,value);return value;}
  const api=async resource=>{reads.push(resource);if(resource==="terminal_broker_status")return copy(status);
    const [name,encoded]=resource.split("/"),p=name==="terminal_broker_receipts"?encoded:JSON.parse(decodeURIComponent(encoded));
    if(name==="terminal_broker_research")return research(p.reference);
    if(name==="terminal_broker_receipt"){const value=records.get(p.mode+":"+p.request_id);return {status:value?"FOUND":"NOT_RECORDED",mode:p.mode,request_id:p.request_id,receipt:copy(value||null),retry_allowed:false,permissions:copy(permissions)};}
    if(name==="terminal_broker_receipts")return {mode:p,items:[...records.values()].filter(v=>v.mode===p),permissions:copy(permissions)};
    if(name==="terminal_broker_check"){
      const cfg=configs.get(p.config_id);assert.equal(cfg.mode,p.mode);const c=cfg.config,missing=Object.keys(form()).filter(key=>!(key in c)).map(field=>({field,label:field})),blockers=[];
      if(row(p.mode).control.new_intents_blocked)blockers.push("CANDIDATE_STOPPED");if(c.asset_code&&c.asset_code!=="US.TEST")blockers.push("RESEARCH_ASSET_CODE_MISMATCH");
      return {mode:p.mode,config_id:p.config_id,status:blockers.length?"BLOCKED":missing.length?"MISSING":"OFFLINE_PREVIEW_ONLY",missing,blockers,security_binding:{status:missing.length?"MISSING":"MATCHED_SAVED_DECLARATION"},order_notional_excluding_fees:c.quantity&&c.limit_price?String(c.quantity*Number(c.limit_price)):null,fee_verified:false,account_verified:false,asset_rules_verified:false,connected:false,permissions:copy(permissions)};
    }throw Error("Unexpected read "+resource);
  };
  const perform=async(action,p,options)=>{writes.push({action,payload:copy(p)});let result,short;
    if(action==="terminal_broker_save_candidate"){const id=hash({mode:p.mode,config:p.config,reference:p.research_reference});configs.set(id,copy(p));result={status:"SAVED_OFFLINE_CANDIDATE",mode:p.mode,config_id:id,permissions:copy(permissions)};short="save";}
    else if(action==="terminal_broker_prepare_intent"){result={status:"UNSENT_OFFLINE_PREVIEW",mode:p.mode,intent:{status:"UNSENT_OFFLINE_PREVIEW",mode:p.mode,id:hash(p),request_id:p.request_id,config_id:p.config_id,terms:configs.get(p.config_id).config,permissions:copy(permissions)},permissions:copy(permissions)};short="prepare_intent";}
    else if(action==="terminal_broker_resume"){assert.equal(p.expected_stop_receipt_id,row(p.mode).control.latest_stop_receipt_id);result={status:"OFFLINE_PREPARATION_RESUMED",mode:p.mode,new_intents_blocked:false,broker_orders_cancelled:false,resumed_stop_receipt_id:p.expected_stop_receipt_id,permissions:copy(permissions)};short="resume";}
    else throw Error("Unexpected action "+action);
    const saved=receipt(short,p,result);if(short==="resume"){row(p.mode).control={...row(p.mode).control,new_intents_blocked:false,resume_allowed:false,latest_control_receipt_id:saved.id};result={...result,control_receipt_id:saved.id};}
    options.onSuccess(result);return result;
  };
  const stopCandidate=async p=>{stops.push(copy(p));const result={status:"STOPPED",mode:p.mode,new_intents_blocked:true,broker_orders_cancelled:false,permissions:copy(permissions)},saved=receipt("stop",p,result);row(p.mode).control={new_intents_blocked:true,resume_allowed:true,latest_stop_receipt_id:saved.id,latest_control_receipt_id:saved.id};return {...result,stop_receipt_id:saved.id,control_receipt_id:saved.id};};
  const controller=ui.createController({api,perform,stopCandidate,uuid:()=>"request-"+(++seq),...overrides});controller.setSources([source]);
  return {controller,api,perform,stopCandidate,reads,writes,stops,records,configs,status,row};
}
async function selected(f){f.controller.setMode(SIM);await f.controller.openResearch(source);await f.controller.refresh();return f;}

test("reads never choose an account, side, candidate mode or create an intent",async()=>{
  const f=fixture();await f.controller.refresh();assert.equal(f.controller.state.mode,"");assert.deepEqual(f.controller.state.form,{});assert.equal(f.writes.length,0);assert.equal(f.stops.length,0);
  f.controller.setSources([source,{...source,status:"UNKNOWN"},{kind:"core_run",id:"bad"}]);assert.equal(f.controller.state.sources.length,1);
  await f.controller.openResearch(source);assert.equal(f.writes.length,0);
});
test("missing candidate fields remain missing and checking saves only local config",async()=>{
  const f=await selected(fixture());await assert.rejects(()=>f.controller.prepareIntent(true),/重新读取并检查/);const checked=await f.controller.check({});assert.equal(checked.status,"MISSING");
  assert.ok(checked.missing.some(v=>v.field==="account_id"));assert.ok(checked.missing.some(v=>v.field==="side"));
  assert.equal(f.writes.length,1);assert.equal(f.writes[0].action,"terminal_broker_save_candidate");assert.deepEqual(f.writes[0].payload.config,{asset_class:"EQUITY",time_in_force:"DAY"});
  await assert.rejects(()=>f.controller.prepareIntent(true),/重新读取并检查/);assert.equal(f.writes.length,1);
});
test("complete check requires separate confirmation; unchanged recheck is GET only",async()=>{
  const f=await selected(fixture()),input=form();await f.controller.check(input);assert.equal(f.writes.length,1);
  await f.controller.check(input);assert.equal(f.writes.length,1);assert.ok(f.reads.some(v=>v.startsWith("terminal_broker_check/")));
  await assert.rejects(()=>f.controller.prepareIntent(false),/确认/);await f.controller.prepareIntent(true);
  assert.equal(f.writes.length,2);assert.equal(f.writes[1].action,"terminal_broker_prepare_intent");assert.match(f.controller.state.fact.message,/未发送意图已保存/);
  await assert.rejects(()=>f.controller.prepareIntent(true),/已保存未发送意图/);assert.equal(f.writes.length,2);
});
test("editing form or switching mode cannot reuse an earlier check or account",async()=>{
  const f=await selected(fixture()),input=form();await f.controller.check(input);f.controller.setForm({...input,quantity:"2"});
  await assert.rejects(()=>f.controller.prepareIntent(true),/重新读取并检查/);
  f.controller.setMode(LIVE);assert.deepEqual(f.controller.state.form,{});assert.equal(f.controller.state.configId,null);assert.equal(f.writes.length,1);
});
test("UNKNOWN keeps original request and NOT_RECORDED cannot permit a second submission",async()=>{
  let calls=0;const f=fixture({perform:async()=>{calls++;return null;}});await selected(f);await f.controller.check(form());
  const original=copy(f.controller.state.pending);await f.controller.queryPending();assert.deepEqual(f.controller.state.pending,original);assert.match(f.controller.state.error,/不代表未处理/);
  await assert.rejects(()=>f.controller.check(form()),/原请求/);assert.throws(()=>f.controller.setMode(LIVE),/原请求/);
  const result={status:"SAVED_OFFLINE_CANDIDATE",mode:SIM,config_id:"b".repeat(64),permissions};
  f.records.set(SIM+":"+original.payload.request_id,{id:"c".repeat(64),mode:SIM,request_id:original.payload.request_id,action:"save",result});
  await f.controller.queryPending();assert.equal(f.controller.state.pending,null);assert.equal(calls,1);assert.match(f.controller.state.fact.message,/候选资料已保存/);
});
test("an acknowledged save survives post-success callback and refresh failure",async()=>{
  const backend=fixture();let after=false;
  const f=fixture({api:async path=>{if(after&&path==="terminal_broker_status")throw Error("refresh unavailable");return backend.api(path);},perform:async(action,p,options)=>{const result=await backend.perform(action,p,options);after=true;throw Error("shell after success");}});
  await selected(f);await f.controller.check(form());assert.equal(f.controller.state.pending,null);assert.match(f.controller.state.fact.message,/已保存/);assert.match(f.controller.state.readError,/未完成/);assert.equal(f.controller.state.statusStale,true);
});
test("stop bypasses a blocked save and never goes through perform",async()=>{
  const backend=fixture();let release,started;const entered=new Promise(resolve=>started=resolve);
  const f=fixture({api:backend.api,stopCandidate:backend.stopCandidate,perform:async(...args)=>{started();await new Promise(resolve=>release=resolve);return backend.perform(...args);}});
  await selected(f);const pending=f.controller.check(form());await entered;
  await f.controller.stop("明确暂停检查");assert.equal(backend.stops.length,1);assert.equal(backend.writes.length,0);assert.equal(f.controller.state.controlPending,null);
  release();await pending;assert.equal(f.controller.state.check.status,"BLOCKED");assert.equal(backend.writes.length,1);assert.match(f.controller.state.controlFact.message,/未撤销/);
});
test("lost stop response recovers receipt.id without requiring a circular result id",async()=>{
  const backend=fixture();const f=fixture({api:backend.api,stopCandidate:async p=>{await backend.stopCandidate(p);return null;}});await selected(f);
  await f.controller.stop("停止待核对");assert.ok(f.controller.state.controlPending);const original=f.controller.state.controlPending.payload.request_id;
  const record=backend.records.get(SIM+":"+original);assert.equal(record.result.stop_receipt_id,undefined);
  await f.controller.queryPending("control");assert.equal(f.controller.state.controlPending,null);assert.equal(f.controller.state.controlFact.id,record.id);assert.equal(backend.stops.length,1);
});
test("resume explicitly binds latest stop plus reason and never restores external permissions",async()=>{
  const f=await selected(fixture());await f.controller.stop("先核对");const first=f.row(SIM).control.latest_stop_receipt_id;
  await assert.rejects(()=>f.controller.resume("已核对",false,first),/确认/);
  await f.stopCandidate({mode:SIM,request_id:"external-second-stop",reason:"更新停止原因"});await f.controller.refresh();
  await assert.rejects(()=>f.controller.resume("已核对",true,first),/最近的停止记录/);
  const latest=f.row(SIM).control.latest_stop_receipt_id;await f.controller.resume("只恢复离线准备",true,latest);
  const request=f.writes.at(-1);assert.equal(request.action,"terminal_broker_resume");assert.equal(request.payload.expected_stop_receipt_id,latest);assert.match(f.controller.state.controlFact.message,/没有恢复任何外部权限/);
  assert.deepEqual(f.controller.state.status.permissions,permissions);
});
test("wrong receipt mode/action/request and unexpected permissions never clear UNKNOWN",async()=>{
  for(const corrupt of [r=>r.mode=LIVE,r=>r.action="prepare_intent",r=>r.request_id="other-request",r=>r.result.permissions.submit_allowed=true]){
    const f=await selected(fixture({perform:async()=>null}));await f.controller.check(form());const op=f.controller.state.pending;
    const record={id:"c".repeat(64),mode:SIM,request_id:op.payload.request_id,action:"save",result:{status:"SAVED_OFFLINE_CANDIDATE",mode:SIM,config_id:"b".repeat(64),permissions:copy(permissions)}};corrupt(record);f.records.set(SIM+":"+op.payload.request_id,record);
    await f.controller.queryPending();assert.ok(f.controller.state.pending);assert.equal(f.controller.state.fact,null);
  }
});
test("stale saved research read cannot overwrite a changed selection or clearing",async()=>{
  let finish;const f=fixture({api:()=>new Promise(resolve=>finish=resolve)});const pending=f.controller.openResearch(source);await f.controller.openResearch(null);finish(research());await pending;assert.equal(f.controller.state.research,null);assert.equal(f.controller.state.reference,null);
});
test("foreign native binding and cross-mode receipt inventory are rejected",async()=>{
  const bad=research();bad.binding.report_hash='f'.repeat(64);
  const f=fixture({api:async resource=>resource.startsWith('terminal_broker_research/')?bad:{mode:SIM,permissions,items:[{mode:LIVE,result:{mode:LIVE,permissions}}]}});
  await f.controller.openResearch(source);assert.equal(f.controller.state.research,null);assert.match(f.controller.state.readError,/身份/);
  f.controller.setMode(SIM);await f.controller.readReceipts();assert.deepEqual(f.controller.state.receipts,[]);assert.match(f.controller.state.readError,/模式或权限/);
});
test("field parsing preserves numeric account IDs and missing fields without made-up values",()=>{
  const value=ui.configFromForm({...form(),account_id:"18446744073709551615"});assert.equal(value.account_id,"18446744073709551615");assert.equal(value.max_quantity,2);assert.equal(value.currency,"USD");
  assert.throws(()=>ui.configFromForm({...form(),account_id:"18446744073709551616"}),/账户编号/);
  assert.throws(()=>ui.configFromForm({...form(),side:"" ,quantity:"1.5"}),/整数/);
  assert.equal(ui.configFromForm({}).side,undefined);assert.equal(ui.configFromForm({}).account_id,undefined);
  assert.throws(()=>ui.configFromForm({...form(),expires_at:new Date(Date.now()-1000).toISOString()}),/未来 24 小时/);
  assert.throws(()=>ui.configFromForm({...form(),expires_at:new Date(Date.now()+90000000).toISOString()}),/未来 24 小时/);
});
