"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const ui = fs.readFileSync(path.join(__dirname,"terminal-quant-ui.js"),"utf8");
const shell = fs.readFileSync(path.join(__dirname,"../../vendor/research/hakimi_terminal_research/resources/desktop.html"),"utf8");
const performSource = shell.split(/\r?\n/).find(line=>line.startsWith("async function perform("));
function uiFunction(name) {
  const offset=ui.indexOf("function "+name+"(");assert.ok(offset>=0,name);
  const start=ui.slice(offset-6,offset)==="async "?offset-6:offset;
  const next=/\n    (?:async )?function \w+\(/g;next.lastIndex=offset+10;
  return ui.slice(start,next.exec(ui)?.index??ui.length).trim();
}
const escape = value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll('"',"&quot;");
function fixture({outcome,detailFailure,refreshFailure,shellRefreshFailure,jobStatus="succeeded"}={}) {
  const run=outcome??{id:"saved-run",run_id:"saved-run",task_id:"task",status:"COMPLETED",title:"研究",version:1,strategy_id:"dual_ma",result:{trades:[]}};
  const elements=new Map();
  const element=id=>{if(!elements.has(id))elements.set(id,{hidden:true,innerHTML:"",textContent:"",disabled:false,isConnected:true,dataset:{},setAttribute(){},removeAttribute(){}});return elements.get(id);};
  const events=[],posts=[],reads=[],errors=[];
  let failDetail=detailFailure;
  const state={runReadRequest:0,completedRun:null,selectedRun:null,catalog:[],runs:[]};
  const context=vm.createContext({state,encodeURIComponent,Set,Date,Promise,
    HakimiTerminalResultSummary:require("./terminal-result-summary"),
    $:element,text:value=>typeof value==="string"&&value.length>0,esc:escape,fmt:value=>String(value??"—"),
    button:(label,action,id)=>`<button data-tq-action="${action}" data-tq-id="${escape(id)}">${label}</button>`,
    warning:message=>`<div class="notice warning">${escape(message)}</div>`,researchBlocker:()=>"",aiEvidenceHtml:()=>"",
    identity:row=>row.run_id||row.id,renderRuns:()=>{},
    notify:(message,error=false)=>{events.push({type:"notice",message,error});element("tq-message").textContent=message;},
    refreshAll:async()=>{events.push({type:"aux-refresh"});if(refreshFailure)throw Error("辅助目录暂不可用");},
    api:async(resource,method="GET",body)=>{
      if(method==="POST") {posts.push({resource,body});events.push({type:"committed"});return {job_id:"job",status:jobStatus,result:run,message:"结果待核对"};}
      reads.push(resource);events.push({type:"detail-read"});
      if(failDetail)throw Error("详情暂不可用 <script>");return {...run,id:decodeURIComponent(resource.slice("terminal_runs/".length)),run_id:decodeURIComponent(resource.slice("terminal_runs/".length))};
    },
    coreMain:{querySelector:()=>({textContent:"操作未完成"})},
    S:{jobs:[],pending:new Map(),dialogSerial:1},crypto:{randomUUID:()=>"request-1"},ACTIONS:{},
    announce:()=>{},updateJobs:()=>{},render:()=>{},closeDialog:()=>{},syncMappingState:()=>{},
    refresh:async()=>{events.push({type:"shell-refresh"});if(shellRefreshFailure)throw Error("壳层后置刷新失败");},
    showError:error=>errors.push(error),unresolved:[],saveUnresolved:()=>{}
  });
  vm.runInContext(performSource+"\n"+["act","showRefreshFailure","refreshRecords","recordRunOutcome","readRunOutcome","operationErrorText","showRun","renderRun"].map(uiFunction).join("\n"),context);
  return {context,state,events,posts,reads,errors,element,run,setDetailFailure:value=>{failDetail=value;},
    runTask:()=>vm.runInContext('act("terminal_run_task",{task_id:"task"},{button:$("run-button"),onCommitted:recordRunOutcome,onSuccess:readRunOutcome})',context)};
}

test("completed backend fact is visible before both shell refresh and result reads",async()=>{
  const f=fixture();const result=await f.runTask();
  assert.equal(result,f.run);assert.equal(f.posts.length,1);assert.equal(f.state.completedRun.id,"saved-run");
  assert.match(f.element("tq-completion").innerHTML,/回测已完成，结果已保存/);
  const confirmed=f.events.findIndex(e=>e.type==="notice"&&e.message.includes("回测已完成"));
  assert.ok(confirmed>=0);assert.ok(confirmed<f.events.findIndex(e=>e.type==="shell-refresh"));
  assert.ok(confirmed<f.events.findIndex(e=>e.type==="detail-read"));
  assert.equal(f.state.selectedRun.id,"saved-run");assert.equal(f.errors.length,0);
});

test("auxiliary refresh failure retains completion and opens the saved result",async()=>{
  const f=fixture({refreshFailure:true});const result=await f.runTask();
  assert.equal(result.id,"saved-run");assert.equal(f.state.selectedRun.id,"saved-run");
  assert.equal(f.state.runs[0].id,"saved-run");
  assert.equal(f.element("tq-completion").hidden,false);
  assert.match(f.element("tq-refresh-message").innerHTML,/辅助记录读取未完成/);
  assert.equal(f.events.some(e=>e.type==="notice"&&e.error),false);assert.equal(f.errors.length,0);assert.equal(f.posts.length,1);
});

test("detail failure has a fixed-result read retry that never computes again",async()=>{
  const f=fixture({detailFailure:true});await f.runTask();
  assert.equal(f.state.selectedRun,null);assert.equal(f.state.completedRun.id,"saved-run");
  assert.match(f.element("tq-run-detail").innerHTML,/回测已完成且结果已保存/);
  assert.match(f.element("tq-run-detail").innerHTML,/data-tq-action="result" data-tq-id="saved-run"/);
  assert.doesNotMatch(f.element("tq-run-detail").innerHTML,/<script>|data-tq-action="run"/);
  f.setDetailFailure(false);await f.context.showRun("saved-run");
  assert.equal(f.state.selectedRun.id,"saved-run");assert.deepEqual(f.reads,["terminal_runs/saved-run","terminal_runs/saved-run"]);
  assert.equal(f.posts.length,1);assert.equal(f.errors.length,0);
});

test("frozen shell returning null after its own refresh cannot erase an acknowledged result",async()=>{
  const f=fixture({shellRefreshFailure:true});const result=await f.runTask();
  assert.equal(result.id,"saved-run");assert.equal(f.state.completedRun.id,"saved-run");
  assert.equal(f.element("tq-completion").hidden,false);assert.equal(f.state.selectedRun.id,"saved-run");
  assert.equal(f.posts.length,1);assert.equal(f.events.some(e=>e.type==="notice"&&e.error),false);
});

test("unknown operation or unknown research receipt is never promoted to completion",async()=>{
  for(const options of [{jobStatus:"unknown"},{outcome:{id:"unknown-run",status:"UNKNOWN",message:"结果待核对"}}]) {
    const f=fixture(options);await f.runTask();
    assert.equal(f.state.completedRun,null);assert.equal(f.element("tq-completion").hidden,true);
    assert.equal(f.reads.length,0);assert.equal(f.posts.length,1);
    assert.equal(f.events.some(e=>e.type==="notice"&&e.message.includes("回测已完成")),false);
  }
});

test("opening a saved result is read-only and does not claim a fresh completion",async()=>{
  const f=fixture();await f.context.showRun("older-saved-run");
  assert.deepEqual(f.reads,["terminal_runs/older-saved-run"]);assert.equal(f.posts.length,0);
  assert.equal(f.state.selectedRun.id,"older-saved-run");assert.equal(f.state.completedRun,null);
  assert.equal(f.element("tq-completion").hidden,true);
});

test("late detail response cannot replace a newer user-selected saved result",async()=>{
  const f=fixture();const pending=new Map();f.context.api=resource=>new Promise(resolve=>pending.set(resource,resolve));
  const first=f.context.showRun("first"),second=f.context.showRun("second");
  pending.get("terminal_runs/second")({...f.run,id:"second",run_id:"second"});await second;
  pending.get("terminal_runs/first")({...f.run,id:"first",run_id:"first"});await first;
  assert.equal(f.state.selectedRun.id,"second");assert.equal(f.posts.length,0);
});

test("a rendering exception after success stays a UI issue and returns the saved receipt",async()=>{
  const f=fixture();f.context.renderRun=()=>{throw Error("详情展示失败");};
  const result=await f.runTask();assert.equal(result.id,"saved-run");
  assert.equal(f.state.completedRun.id,"saved-run");assert.equal(f.state.selectedRun,null);
  assert.match(f.element("tq-run-detail").innerHTML,/重新读取这份结果/);assert.equal(f.posts.length,1);
});
