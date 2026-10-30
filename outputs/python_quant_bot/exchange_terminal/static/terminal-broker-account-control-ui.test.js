"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),{createHash}=require("node:crypto"),fs=require("node:fs");
const ui=require("./terminal-broker-account-control-ui");
const SIM="OFFICIAL_SIMULATION",LIVE="LIVE_CANDIDATE",A="a".repeat(64),B="b".repeat(64),ROOT="f".repeat(64),schema="hakimi-broker-account-control-v1";
const copy=v=>JSON.parse(JSON.stringify(v)),hash=v=>createHash("sha256").update(ui.canonical(v)).digest("hex");
const permissions=Object.fromEntries(ui.permissionKeys.map(key=>[key,false])),context=(mode=SIM,config_id=A)=>({mode,config_id});
function fixture(options={}){
  let sequence=0;const reads=[],writes=[],stops=[],records=new Map();
  const account=p=>({provider:"FUTU",mode:p.mode,account_id:p.config_id===B?"900000000000002":"900000000000001"});
  const rows=p=>records.get(hash(account(p)))||[];
  function view(p,{read=false,replayed=false}={}){const list=rows(p),head=list.at(-1);return {schema_version:schema,service_available:true,config_id:p.config_id,account:account(p),account_scope_id:hash(account(p)),root_id:ROOT,record_domain:"SYNTHETIC_TEST",
    control:{revision:list.length,head_id:head?.id||null,stopped:head?.action==="stop",last_action:head?.action||null,dispatch_authorized:false,automatic_resume:false},receipt:list.find(row=>row.request_id===p.request_id)||null,replayed,broker_orders_cancelled:false,permissions:copy(permissions),...(read?{read_only:true}:{})};}
  function record(action,p){const list=rows(p);if(list.some(row=>row.request_id===p.request_id))return view(p,{replayed:true});
    if(action==="resume")assert.equal(p.expected_stop_receipt_id,list.at(-1)?.id);
    const payload={request_id:p.request_id,reason:p.reason,...(action==="resume"?{expected_stop_receipt_id:p.expected_stop_receipt_id}:{})};
    const row={schema_version:schema,root_id:ROOT,record_domain:"SYNTHETIC_TEST",account_scope_id:hash(account(p)),revision:list.length+1,previous_id:list.at(-1)?.id||null,request_id:p.request_id,request_hash:hash({action,payload}),action,payload,at:"2026-10-30T01:00:00+00:00",permissions:copy(permissions)};
    row.id=hash(row);records.set(hash(account(p)),[...list,row]);return view(p);}
  const api=async resource=>{reads.push(resource);const [name,encoded]=resource.split("/"),p=JSON.parse(decodeURIComponent(encoded));assert.ok(["terminal_broker_account_control","terminal_broker_account_receipt"].includes(name));
    assert.deepEqual(Object.keys(p).sort(),(name.endsWith("receipt")?["mode","config_id","request_id"]:["mode","config_id"]).sort());
    return options.read?options.read(name,p,view):view(p,{read:true});};
  const stopAccount=async p=>{stops.push(copy(p));const result=record("stop",p);return options.stop?options.stop(p,result):result;};
  const perform=async(action,p,callbacks)=>{writes.push({action,payload:copy(p)});assert.equal(action,"terminal_broker_account_resume");const result=record("resume",p);if(options.perform)return options.perform(p,result,callbacks);await callbacks.onSuccess(result);return result;};
  const c=ui.createController({api,perform,stopAccount,uuid:()=>"fixture-"+(++sequence),changed:options.changed||(()=>{})});c.setContext(context());
  return {c,api,perform,stopAccount,reads,writes,stops,records,view,record};
}
async function stopped(f=fixture()){await f.c.stop("明确停止隔离账户");return f;}

test("mount/context selection is inert; explicit status reads never create records or choose an account",async()=>{
  const f=fixture();assert.equal(f.reads.length,0);assert.equal(f.stops.length,0);await f.c.refresh();assert.equal(f.records.size,0);assert.equal(f.c.state.view.control.revision,0);assert.equal(f.c.state.view.control.stopped,false);
  f.c.setContext(context(LIVE,B));assert.equal(f.reads.length,1);assert.equal(f.c.state.view,null);assert.equal(f.writes.length,0);
});
test("direct stop uses exact identity and bypasses all parent busy/research/plan flags and perform",async()=>{
  const f=fixture();f.c.setContext({...context(),busy:true,blocked:true,research_locked:true,plan_locked:true});await f.c.stop("现在停止");
  assert.equal(f.stops.length,1);assert.equal(f.writes.length,0);assert.equal(f.reads.length,0);assert.deepEqual(Object.keys(f.stops[0]).sort(),["mode","config_id","request_id","reason"].sort());
  assert.equal(f.c.state.stopPending,null);assert.equal(f.c.state.view.control.stopped,true);assert.equal(f.c.state.view.control.dispatch_authorized,false);
});
test("draft scope invalidation prevents stopping previously saved account while preserving unresolved original",async()=>{
  const f=fixture({stop:()=>null});await f.c.stop("停止");const original=copy(f.c.state.stopPending);f.c.setContext({mode:SIM,config_id:null});
  await assert.rejects(()=>f.c.stop("再停"),/暂存/);assert.deepEqual(f.c.state.stopPending,original);await f.c.queryPending();assert.equal(f.stops.length,1);assert.equal(f.c.state.view,null);assert.equal(f.c.state.facts.stop.context.config_id,A);
});
test("lost stop recovers original account/mode/config/request after switching without another POST",async()=>{
  const f=fixture({stop:()=>null});await f.c.stop("隔离停止");const p=copy(f.c.state.stopPending.payload);f.c.setContext(context(LIVE,B));await f.c.refresh();await f.c.queryPending();
  assert.equal(f.stops.length,1);assert.deepEqual(JSON.parse(decodeURIComponent(f.reads.at(-1).split("/")[1])),{mode:SIM,config_id:A,request_id:p.request_id});
  assert.equal(f.c.state.view.account.mode,LIVE);assert.equal(f.c.state.view.account.account_id,"900000000000002");assert.equal(f.c.state.view.control.stopped,false);assert.equal(f.c.state.facts.stop.account.mode,SIM);
});
test("NOT_RECORDED stays unresolved and repeated queries never resubmit",async()=>{
  const f=fixture({stop:()=>null});await f.c.stop("停止");const p=copy(f.c.state.stopPending);f.records.clear();await f.c.queryPending();await f.c.queryPending();
  assert.equal(f.c.state.stopPending.payload.request_id,p.payload.request_id);assert.match(f.c.state.error,/不代表未处理/);await assert.rejects(()=>f.c.stop("重试"),/原请求/);assert.equal(f.stops.length,1);
});
test("replayed old STOP receipt displays current resumed state and cannot re-stop it",async()=>{
  const f=fixture({stop:()=>null});await f.c.stop("停止");const p=f.stops[0];
  const first=f.view(p).receipt;f.record("resume",{...context(),request_id:"other-resume",reason:"另一工作区明确恢复",expected_stop_receipt_id:first.id});await f.c.queryPending();
  assert.equal(f.c.state.view.control.stopped,false);assert.equal(f.c.state.view.control.last_action,"resume");assert.equal(f.c.state.facts.stop.receipt.action,"stop");assert.equal(f.c.state.stopPending,null);assert.equal(f.stops.length,1);
});
test("late stop response cannot impersonate the newly selected scope",async()=>{
  let release;const f=fixture({stop:(_p,result)=>new Promise(resolve=>release=()=>resolve(result))});const writing=f.c.stop("停止旧账户");await Promise.resolve();f.c.setContext(context(LIVE,B));await f.c.refresh();release();await writing;
  assert.equal(f.c.state.view.account.mode,LIVE);assert.equal(f.c.state.view.control.stopped,false);assert.equal(f.c.state.facts.stop.context.config_id,A);
});
test("late read and older mutation responses cannot overwrite a newer current revision",async()=>{
  let release;const f=fixture({stop:(_p,result)=>new Promise(resolve=>release=()=>resolve(result))});const writing=f.c.stop("停止");await Promise.resolve();
  const first=f.view(f.stops[0]).receipt;f.record("resume",{...context(),request_id:"elsewhere",reason:"明确恢复",expected_stop_receipt_id:first.id});await f.c.refresh();release();await writing;
  assert.equal(f.c.state.view.control.revision,2);assert.equal(f.c.state.view.control.stopped,false);assert.equal(f.c.state.stopPending,null);
  let finishRead;const g=fixture({read:(_n,p,view)=>new Promise(resolve=>finishRead=()=>resolve(view(p,{read:true})))});const reading=g.c.refresh();g.c.setContext(context(LIVE,B));finishRead();await reading;assert.equal(g.c.state.view,null);
});
test("resume requires explicit latest receipt, checkbox and reason; changes revoke confirmation",async()=>{
  const f=await stopped();await assert.rejects(()=>f.c.resume("恢复"),/明确确认/);f.c.setConfirmation(true);await assert.rejects(()=>f.c.resume(" "),/原因/);
  await f.c.refresh();assert.equal(f.c.state.confirmed,false);f.c.setConfirmation(true);const id=f.c.state.view.control.head_id;await f.c.resume("恢复隔离准备");
  assert.equal(f.writes.length,1);assert.deepEqual(Object.keys(f.writes[0].payload).sort(),["mode","config_id","request_id","reason","expected_stop_receipt_id"].sort());assert.equal(f.writes[0].payload.expected_stop_receipt_id,id);
  assert.equal(f.c.state.view.control.stopped,false);assert.ok(Object.values(f.c.state.view.permissions).every(value=>value===false));assert.equal(f.c.state.view.broker_orders_cancelled,false);
});
test("account STOP remains independent of a pending resume job and stale resumed view cannot replace STOP",async()=>{
  let release;const f=await stopped(fixture({perform:(_p,result,callbacks)=>new Promise(resolve=>release=async()=>{await callbacks.onSuccess(result);resolve(result);})}));f.c.setConfirmation(true);const resuming=f.c.resume("恢复准备");await Promise.resolve();await f.c.stop("再次明确停止");release();await resuming;
  assert.equal(f.stops.length,2);assert.equal(f.writes.length,1);assert.equal(f.c.state.view.control.revision,3);assert.equal(f.c.state.view.control.stopped,true);
});
test("host unavailable remains honest and cannot submit account changes",async()=>{
  const f=fixture({read:(_n,p)=>({schema_version:schema,service_available:false,reason:"HOST_BINDING_UNAVAILABLE",config_id:p.config_id,permissions:copy(permissions),read_only:true})});await f.c.refresh();
  assert.equal(f.c.state.view.service_available,false);await assert.rejects(()=>f.c.stop("停止"),/未绑定/);assert.equal(f.stops.length,0);assert.equal(f.records.size,0);
});
test("malformed permission, account scope, receipt payload and root changes remain unresolved",async()=>{
  const cases=[v=>v.permissions.submit_allowed=true,v=>v.control.dispatch_authorized=true,v=>v.account.account_id="123",v=>v.receipt.payload.reason="另一原因",v=>v.receipt.request_id="other",v=>v.config_id=B,v=>v.broker_orders_cancelled=true];
  for(const alter of cases){const f=fixture({stop:(_p,result)=>{const value=copy(result);alter(value);return value;}});await f.c.stop("停止");assert.ok(f.c.state.stopPending);assert.equal(f.c.state.facts.stop,undefined);assert.equal(f.c.state.view,null);}
  const f=fixture({stop:(_p,result)=>({...result,root_id:"e".repeat(64)})});await f.c.refresh();await f.c.stop("停止");assert.ok(f.c.state.stopPending);assert.equal(f.c.state.view.root_id,ROOT);
});
test("acknowledged receipt survives host post-success failure and presentation failure",async()=>{
  const f=await stopped(fixture({perform:async(_p,result,callbacks)=>{await callbacks.onSuccess(result);throw Error("post-success list failed");}}));f.c.setConfirmation(true);await f.c.resume("恢复");
  assert.equal(f.c.state.resumePending,null);assert.equal(f.c.state.view.control.stopped,false);assert.match(f.c.state.readError,/已有保存回执/);
  const g=fixture({changed:s=>{if(s.facts.stop)throw Error("render failed");}});await g.c.stop("停止");assert.equal(g.c.state.stopPending,null);assert.ok(g.c.state.facts.stop);assert.match(g.c.state.readError,/仍保留/);
});
test("read failure revokes resume confirmation; mode/config boundaries remain separate",async()=>{
  let fail=false;const f=await stopped(fixture({read:(_n,p,view)=>{if(fail)throw Error("offline");return view(p,{read:true});}}));f.c.setConfirmation(true);fail=true;await f.c.refresh();
  assert.equal(f.c.state.confirmed,false);assert.equal(f.c.state.stale,true);await assert.rejects(()=>f.c.resume("恢复"),/最新停止回执/);f.c.setContext(context(LIVE));assert.equal(f.c.state.view,null);await f.c.stop("明确停止另一个模式");assert.equal(f.c.state.view.account.mode,LIVE);assert.equal(f.c.state.view.control.revision,1);
});
test("same-window integration passes only unchanged saved scope and retains original mode stop",()=>{
  const source=fs.readFileSync(require.resolve("./terminal-broker-candidate-ui"),"utf8"),account=fs.readFileSync(require.resolve("./terminal-broker-account-control-ui"),"utf8");
  assert.match(source,/installTerminalBrokerCandidateUI\(\{host,api,perform,stopCandidate,stopAccount/);assert.match(source,/config_id:state\.savedStamp===currentStamp\?state\.configId:null/);
  assert.match(source,/停止与恢复本模式的意图准备/);assert.match(source,/controller\.stop\(\$\("stop-reason"\)/);assert.match(account,/同一模式、同一账户的其他工作区会读取同一停止标记；不代表撤单或清仓/);assert.match(account,/min-height:44px/);
  assert.doesNotMatch(account,/fetch\(|WebSocket|localStorage|setInterval|window\.open/);
});
test("canonical receipt hashing matches the backend ASCII encoding for Chinese reasons and surrogate pairs",()=>{
  assert.equal(ui.canonical({reason:"暂停\u007f🙂",request_id:"x"}),'{"reason":"\\u6682\\u505c\\u007f\\ud83d\\ude42","request_id":"x"}');
});
