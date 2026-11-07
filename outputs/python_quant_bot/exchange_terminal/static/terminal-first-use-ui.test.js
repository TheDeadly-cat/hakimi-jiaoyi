"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {createController,validTeaching,records}=require("./terminal-first-use-ui.js");
const copy=v=>JSON.parse(JSON.stringify(v));
const receipt=()=>({schema_version:"terminal-teaching-input-v1",status:"READY",input_id:"a".repeat(24),snapshot_id:"b".repeat(64),
  input:{id:"a".repeat(24),input_id:"b".repeat(64),evidence_kind:"SYNTHETIC_TEST",security:{currency:"USD"}},
  evidence_kind:"SYNTHETIC_TEST",currency:"USD",sessions:22,strategy_key:"price.dual_ma@1",
  params:{fast_window:2,slow_window:4,position_pct:.25,stop_loss_pct:.03,take_profit_pct:.06},source_truth_verified:false,new_tasks:0,new_economic_runs:0,
  permissions:{research_only:true,paper_allowed:false,live_allowed:false,order_allowed:false}});
const store=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),values};};
function fixture(options={}){const data={loaded:true,coreOverview:{workspace:"C:/fictional/workspace-one"},tasks:[],runs:[],coreTasks:[],coreRuns:[]},storage=store(),calls=[];
  const controller=createController({getState:()=>data,storage,api:async()=>({items:[]}),onTeaching:async hooks=>{calls.push("prepare");hooks.onRequest("fixture-request-001");hooks.onCommitted(receipt());return receipt();},
    onChooseTeaching:async value=>calls.push(["choose",value.input_id]),onOwnData:async()=>calls.push("own"),onContinue:async value=>calls.push(["continue",value.kind,value.id]),...options});
  controller.refresh();return {controller,data,storage,calls};}

test("fresh first use reads without importing and explicit preparation saves a reference before a mutation",async()=>{
  const f=fixture();assert.equal(f.controller.model().action,"prepare");assert.deepEqual(f.calls,[]);
  await f.controller.primary();assert.deepEqual(f.calls,["prepare"]);assert.equal(f.controller.model().action,"choose");
  assert.equal(f.controller.state.prepared.new_tasks,0);assert.equal(f.controller.state.prepared.new_economic_runs,0);
  const saved=JSON.parse([...f.storage.values.values()][0]);assert.equal(saved.job_id,"fixture-request-001");assert.equal(saved.phase,"PREPARED");
  assert.equal(saved.workspace,f.data.coreOverview.workspace);assert.equal(saved.input_id,"a".repeat(24));assert.equal(Object.hasOwn(saved,"params"),false);
  await f.controller.primary();assert.deepEqual(f.calls,["prepare",["choose","a".repeat(24)]]);
});

test("saving and reopening the same teaching task never retain an earlier preparation notice",async()=>{
  const f=fixture();await f.controller.prepare();await f.controller.chooseTeaching();
  f.data.coreTasks=[{id:"saved-task",title:"教学100",version:1}];f.controller.state.error="局部读取未完成";
  f.controller.markContinuation({kind:"core-task",id:"saved-task"});
  assert.equal(f.controller.model().primary,"继续上次策略");assert.doesNotMatch(f.controller.state.notice,/正在选择|尚未创建/);
  assert.equal(f.controller.state.error,"局部读取未完成");
  const next=createController({getState:()=>f.data,storage:f.storage,api:async path=>path.startsWith('jobs/')
    ?{job_id:"fixture-request-001",action:"terminal_prepare_teaching_input",status:"succeeded",result:receipt()}:{...receipt().input,status:"READY"}});
  await next.recover();assert.equal(next.model().action,"continue");assert.doesNotMatch(next.state.notice,/正在选择|尚未创建/);
});

test("late teaching form completion cannot overwrite a saved task or another workspace's notice",async()=>{
  for(const change of ['saved','workspace']){
    let finish;const f=fixture({onChooseTeaching:()=>new Promise(resolve=>finish=resolve)});await f.controller.prepare();
    const pending=f.controller.chooseTeaching();
    if(change==='saved'){f.data.coreTasks=[{id:'saved-task'}];f.controller.markContinuation({kind:'core-task',id:'saved-task'});}
    else{f.data.coreOverview.workspace='C:/fictional/other';f.controller.refresh();}
    const notice=f.controller.state.notice;finish();await pending;assert.equal(f.controller.state.notice,notice);assert.doesNotMatch(notice,/正在选择/);
  }
});

test("prepared input survives task-form failures and another explicit attempt never imports again",async()=>{
  let tries=0;const f=fixture({onChooseTeaching:async()=>{if(++tries===1)throw Error("form unavailable");}});
  await f.controller.prepare();await f.controller.chooseTeaching();assert.match(f.controller.state.error,/资料已保存/);
  assert.equal(f.controller.model().action,"choose");await f.controller.chooseTeaching();assert.equal(tries,2);assert.deepEqual(f.calls,["prepare"]);
});

test("unknown submission is not repeated after refresh and is recovered only by the original job ID",async()=>{
  const storage=store(),data={loaded:true,coreOverview:{workspace:"C:/fictional/workspace"}},calls=[];
  const first=createController({getState:()=>data,storage,api:async()=>({items:[]}),onTeaching:async h=>{h.onRequest("original-request");calls.push("POST");return null;}});
  first.refresh();await first.prepare();assert.equal(first.state.pending,true);
  await assert.rejects(first.prepare(),/原准备/);assert.deepEqual(calls,["POST"]);
  const second=createController({getState:()=>data,storage,api:async path=>{calls.push(path);return {job_id:"original-request",action:"terminal_prepare_teaching_input",status:"unknown"};},onTeaching:()=>{throw Error("No retry");}});
  await second.recover();assert.equal(second.state.pending,true);assert.equal(second.model().action,"recover");
  assert.deepEqual(calls,["POST","jobs/original-request"]);
});

test("reload reads the original succeeded job and exact input before allowing settings",async()=>{
  const f=fixture();await f.controller.prepare();const requests=[];
  const second=createController({getState:()=>f.data,storage:f.storage,api:async path=>{requests.push(path);
    return path.startsWith("jobs/")?{job_id:"fixture-request-001",action:"terminal_prepare_teaching_input",status:"succeeded",result:receipt()}:{...receipt().input,status:"READY"};}});
  await second.recover();assert.equal(second.model().action,"choose");assert.equal(second.state.pending,false);
  assert.deepEqual(requests,["jobs/fixture-request-001","inputs/"+"a".repeat(24)]);
});

test("missing, mismatched and unreadable original records remain locked instead of making a new input",async()=>{
  for(const api of [async()=>{throw Error("job not found");},async()=>({job_id:"wrong",action:"terminal_prepare_teaching_input",status:"succeeded",result:receipt()}),
    async path=>path.startsWith("jobs/")?{job_id:"fixture-request-001",action:"terminal_prepare_teaching_input",status:"succeeded",result:receipt()}:{...receipt().input,status:"BLOCKED"}]){
    const f=fixture();await f.controller.prepare();const c=createController({getState:()=>f.data,storage:f.storage,api});await c.recover();
    assert.equal(c.state.pending,true);assert.equal(c.state.prepared,null);await assert.rejects(c.prepare(),/原准备/);
  }
});

test("workspace changes neither read the old job from the new backend nor apply late old completion",async()=>{
  const f=fixture();await f.controller.prepare();const oldKey=[...f.storage.values.keys()][0];
  f.data.coreOverview.workspace="C:/fictional/workspace-two";f.controller.refresh();
  assert.equal(f.controller.state.reference,null);assert.equal(f.controller.state.prepared,null);assert.equal(f.controller.model().action,"prepare");
  assert.ok(f.storage.values.has(oldKey));
  assert.throws(()=>f.controller.acceptTeaching(receipt()),/工作区已变化/);
});

test("lack of durable reference storage prevents submission before POST",async()=>{
  let mutations=0;const f=fixture({storage:{getItem:()=>null,setItem:()=>{throw Error("quota");}},onTeaching:async h=>{h.onRequest("no-write-request");mutations++;}});
  await f.controller.prepare();assert.equal(mutations,0);assert.equal(f.controller.state.pending,false);assert.match(f.controller.state.error,/quota/);
});

test("saved-record continuation keeps exact engine namespaces and does not run a task",async()=>{
  const f=fixture();f.data.tasks=[{id:"same",title:"原策略",version:2,updated_at:"2026-11-07T00:00:00Z"}];
  f.data.coreRuns=[{id:"same",task_display_name:"股票研究",started_at:"2026-11-07T01:00:00Z",data_kind:"SYNTHETIC_TEST"}];
  f.controller.refresh();assert.equal(f.controller.model().action,"continue");assert.equal(f.controller.model().item.kind,"core-run");
  await f.controller.primary();assert.deepEqual(f.calls,[["continue","core-run","same"]]);
  f.controller.select("terminal-task:same");await f.controller.primary();assert.deepEqual(f.calls[1],["continue","terminal-task","same"]);
  assert.equal(JSON.parse([...f.storage.values.values()][0]).continuation.kind,"terminal-task");
});

test("own-data navigation never quietly replaces the selected fictional input",async()=>{
  const f=fixture();await f.controller.prepare();await f.controller.ownData();
  assert.equal(f.controller.state.prepared.evidence_kind,"SYNTHETIC_TEST");assert.equal(f.controller.model().action,"choose");
  assert.deepEqual(f.calls,["prepare","own"]);
});

test("reading and presentation errors cannot erase a durable successful preparation",async()=>{
  const f=fixture({changed:()=>{throw Error("renderer failed");}});await f.controller.prepare();
  assert.equal(f.controller.state.prepared.input_id,"a".repeat(24));assert.equal(f.controller.state.pending,false);
  assert.equal(f.controller.model().action,"choose");assert.match(f.controller.state.error,/页面更新/);
});

test("teaching receipts require exact public parameters and never accept external permissions",()=>{
  assert.equal(validTeaching(receipt()),true);
  for(const mutate of [v=>v.params.fast_window=20,v=>v.new_tasks=2,v=>v.new_economic_runs=1,v=>v.permissions.order_allowed=true,v=>v.evidence_kind="IMPORTED_UNVERIFIED"]){const v=receipt();mutate(v);assert.equal(validTeaching(v),false);}
  assert.deepEqual(records({coreRuns:[{id:"\0bad"}],tasks:[]}),[]);
});

test("readonly mode retains viewing controls but does not offer a preparation mutation",()=>{
  const f=fixture();f.data.coreOverview.session={read_only:true};assert.equal(f.controller.model().disabled,true);
  f.data.coreRuns=[{id:"saved",label:"已保存结果"}];assert.equal(f.controller.model().action,"continue");assert.equal(f.controller.model().disabled,false);
});

test("a late preparation callback cannot complete another workspace's current job",async()=>{
  const data={loaded:true,coreOverview:{workspace:"workspace-one"}},storage=store();let firstHooks,resolveFirst,calls=0;
  const c=createController({getState:()=>data,storage,api:async()=>({items:[]}),onTeaching:async hooks=>{if(++calls===1){firstHooks=hooks;hooks.onRequest("first-workspace-job");return new Promise(resolve=>resolveFirst=resolve);}
    hooks.onRequest("second-workspace-job");const v=receipt();v.input_id="c".repeat(24);v.input.id=v.input_id;hooks.onCommitted(v);return v;}});
  c.refresh();const first=c.prepare();await Promise.resolve();data.coreOverview.workspace="workspace-two";c.refresh();await c.prepare();
  firstHooks.onCommitted(receipt());resolveFirst(receipt());await first;
  assert.equal(c.state.reference.job_id,"second-workspace-job");assert.equal(c.state.prepared.input_id,"c".repeat(24));
  assert.equal(c.state.pending,false);
});

test("a new origin without a local marker checks current-workspace jobs before another POST",async()=>{
  const pending={job_id:"existing-workspace-job",action:"terminal_prepare_teaching_input",status:"unknown"};
  const f=fixture({api:async()=>({items:[pending]})});await f.controller.prepare();
  assert.deepEqual(f.calls,[]);assert.equal(f.controller.state.pending,true);assert.equal(f.controller.state.reference.job_id,pending.job_id);
});

test("multiple pending preparations require selecting the exact original ID",async()=>{
  const rows=["first-old-job","second-old-job"].map(job_id=>({job_id,action:"terminal_prepare_teaching_input",status:"unknown"}));
  const f=fixture({api:async()=>({items:rows})});await f.controller.prepare();
  assert.equal(f.controller.state.reference,null);assert.equal(f.controller.model().disabled,true);assert.deepEqual(f.calls,[]);
  f.controller.selectPending("second-old-job");assert.equal(f.controller.state.reference.job_id,"second-old-job");
  assert.equal(f.controller.model().disabled,false);assert.throws(()=>f.controller.selectPending("invented-job"),/原操作/);
});
