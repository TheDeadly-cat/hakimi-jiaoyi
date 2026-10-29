"use strict";
const assert=require("node:assert/strict"),path=require("node:path"),vm=require("node:vm"),test=require("node:test");
const {execFileSync}=require("node:child_process");
const {createCoreCompletionAdapter}=require("./terminal-core-completion");
// Exercise the actual server-rendered functions, including the source guards and
// adapter placement, rather than hand-reimplementing perform/refresh in tests.
const rendered=execFileSync(process.env.PYTHON||"python",["-c",
  "import sys;sys.path.insert(0,'outputs/python_quant_bot');from exchange_terminal.services import quant_workspace as q;sys.stdout.buffer.write(q.render_quant_html((q._VENDOR/'hakimi_terminal_research/resources/desktop.html').read_bytes(),'synthetic-token','synthetic-nonce'))"],
  {cwd:path.resolve(__dirname,"../../../.."),encoding:"utf8",maxBuffer:3*1024*1024});
const source=name=>{const match=rendered.match(new RegExp("^(?:async )?function "+name+"\\(.*$","m"));assert.ok(match,name);return match[0];};
function fixture({refreshFailure=false,detailFailure=false,jobStatus="succeeded",unknownResult=false}={}) {
  const elements=[];const element=()=>{const value={id:"",hidden:true,innerHTML:"",textContent:"",dataset:{},listeners:{},disabled:false,isConnected:true,setAttribute(){},removeAttribute(){},before(){},append(){},addEventListener(name,callback){this.listeners[name]=callback;}};elements.push(value);return value;};
  for(const id of ["main","refresh","version","dialog"])element().id=id;
  const document={createElement:element,getElementById:id=>elements.find(value=>value.id===id)||null};
  const S={runs:[],tasks:[],inputs:[],jobs:[],runCache:new Map(),runLoading:new Set(),selectedRun:null,dialogSerial:0};
  const result=unknownResult?{id:"unknown",status:"UNKNOWN"}:{id:"saved-result",summary:{id:"saved-result",symbol:"SYNTHETIC"},fills:[]};
  const calls=[],errors=[],events=[];let failDetail=detailFailure;
  const context=vm.createContext({S,document,Map,Set,Promise,Date,encodeURIComponent,
    $:selector=>document.getElementById(selector.replace(/^#/,"")),ACTIONS:{},refreshing:false,
    crypto:{randomUUID:()=>"operation-1"},announce:message=>events.push(message),closeDialog(){},syncMappingState(){},updateJobs(){},render(){},
    unresolved:[],saveUnresolved(){},showError:error=>errors.push(error),
    api:async(resource,method="GET")=>{
      calls.push({resource,method});
      if(method==="POST")return {job_id:"operation-1",status:jobStatus,result,message:"结果待核对"};
      if(resource==="status") {events.push("refresh-start");if(refreshFailure)throw Error("状态目录读取失败");return {runs:[],inputs:[],tasks:[]};}
      if(resource.startsWith("runs/")){if(failDetail)throw Error("详情读取失败 <script>");const id=decodeURIComponent(resource.slice(5));return {id,summary:{id,symbol:"SYNTHETIC"},fills:[]};}
      return {items:[]};
    }
  });
  vm.runInContext(["perform","refresh","loadRun","applyOverview"].map(source).join("\n"),context);
  context.coreCompletion=createCoreCompletionAdapter({api:context.api,state:S,document,esc:value=>String(value).replaceAll("<","&lt;"),
    render:()=>context.render(),refresh:options=>context.refresh(options),showError:context.showError,
    runTask:(task,button)=>context.perform("run_task",{task_id:task.id,expected_task_id:task.task_id},{button})});
  return {context,S,result,events,calls,errors,document,failDetail:value=>{failDetail=value;},
    run:callback=>context.perform("run_task",{task_id:"task"},{onSuccess:callback})};
}

test("saving exposes an explicit run action and its click reaches perform without pre-disabling it",async()=>{
  const f=fixture();
  const task={id:"task-handle",task_id:"frozen-version-hash",state:"ENABLED",title:"样例",revisions:["revision-hash"],selected_revision:"revision-hash"};
  f.context.coreCompletion.confirm("create_task",task);
  assert.equal(f.calls.filter(call=>call.method==="POST").length,0);
  assert.match(f.document.getElementById("core-read-saved-task").innerHTML,/运行这次回测/);
  const button={dataset:{coreRunTask:"1"},disabled:false,isConnected:true,setAttribute(){},removeAttribute(){}};
  f.document.getElementById("core-completion-feedback").listeners.click({target:{closest:()=>button}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.calls.filter(call=>call.resource==="actions/run_task"&&call.method==="POST").length,1);
  assert.equal(f.errors.length,0);
});

test("rendered core completion is visible before callback and auxiliary refresh",async()=>{
  const f=fixture();const result=await f.run(()=>{
    assert.equal(f.document.getElementById("core-read-completed").hidden,false);
    assert.equal(f.S.runCache.get("saved-result"),f.result);f.events.push("callback");
  });
  assert.equal(result,f.result);assert.equal(f.S.runs[0].id,"saved-result");
  assert.ok(f.events.indexOf("callback")<f.events.indexOf("refresh-start"));assert.equal(f.errors.length,0);
});

test("rendered success callback exceptions never become an operation failure",async()=>{
  const f=fixture({refreshFailure:true});assert.equal(await f.run(()=>{throw Error("页面刷新故障");}),f.result);
  assert.equal(f.errors.length,0);assert.equal(f.document.getElementById("core-read-completed").hidden,false);
  assert.equal(f.document.getElementById("core-read-detail").hidden,false);
  assert.equal(f.calls.filter(call=>call.method==="POST").length,1);
});

test("successful later render clears a previous presentation error",async()=>{
  const f=fixture();await f.run(()=>{throw Error("页面刷新故障");});
  assert.equal(f.document.getElementById("core-read-detail").hidden,true);
  assert.equal(f.document.getElementById("core-read-completed").hidden,false);
});

test("rendered task-form hook preselects only a known rule without saving or running",async()=>{
  const hook=rendered.match(/openCoreTaskForm:(async strategyKey=>\{.*?\}),openCoreImport:/)[1];
  const calls=[],field={value:"first"},S={strategies:[{key:"first"},{key:"second"}],taskDraft:null};
  const context=vm.createContext({S,$:()=>field,nav:view=>calls.push(["nav",view]),
    openTaskForm:async()=>{calls.push(["open"]);S.taskDraft={task:null,strategy:"first"};},
    renderStrategyFields:changed=>calls.push(["fields",changed])});
  const open=vm.runInContext("("+hook+")",context);await open("second");
  assert.equal(field.value,"second");assert.equal(S.taskDraft.strategy,"second");
  assert.deepEqual(calls,[["nav","tasks"],["open"],["fields",true]]);
  calls.length=0;await assert.rejects(()=>open("unknown"),/所选研究规则尚未就绪/);assert.equal(calls.length,0);
  await open();assert.deepEqual(calls,[["nav","tasks"],["open"]]);assert.equal(S.taskDraft.strategy,"first");
});

test("rendered refresh failures preserve completion without frozen showError",async()=>{
  const f=fixture({refreshFailure:true});assert.equal(await f.run(()=>{}),f.result);
  assert.equal(f.errors.length,0);assert.equal(f.document.getElementById("core-read-refresh").hidden,false);
  assert.equal(f.document.getElementById("core-read-completed").hidden,false);assert.equal(f.S.runs[0].id,"saved-result");
});

test("saved-result detail read fails separately and retries only that result",async()=>{
  const f=fixture({detailFailure:true});await f.context.loadRun("existing/result");
  assert.equal(f.errors.length,0);assert.match(f.context.coreCompletion.resultPlaceholder("existing/result"),/结果详情读取未完成/);
  assert.doesNotMatch(f.context.coreCompletion.resultPlaceholder("existing/result"),/<script>|spinner/);
  await f.context.loadRun("existing/result",true);assert.equal(f.calls.length,1,"quiet refresh must not auto-retry failed detail");
  f.failDetail(false);await f.context.loadRun("existing/result");
  assert.deepEqual(f.calls,[{resource:"runs/existing%2Fresult",method:"GET"},{resource:"runs/existing%2Fresult",method:"GET"}]);
  assert.equal(f.S.runCache.get("existing/result").id,"existing/result");assert.equal(f.document.getElementById("core-read-detail").hidden,true);
  assert.equal(f.document.getElementById("core-read-completed"),null);
});

test("unknown job and unknown result never invoke the legacy successful-run callback",async()=>{
  for(const options of [{jobStatus:"unknown"},{unknownResult:true}]) {
    const f=fixture(options);let callback=0;await f.run(()=>callback++);
    assert.equal(callback,0);assert.equal(f.S.runCache.size,0);assert.equal(f.document.getElementById("core-read-completed").hidden,true);
    assert.equal(f.calls.filter(call=>call.method==="POST").length,1);
  }
});

test("error after an acknowledged job returns the saved receipt and never resubmits",async()=>{
  const f=fixture();f.context.announce=message=>{if(message.includes("已完成"))throw Error("announcement failed");};
  assert.equal(await f.run(()=>{}),f.result);assert.equal(f.errors.length,0);
  assert.equal(f.document.getElementById("core-read-completed").hidden,false);
  assert.equal(f.calls.filter(call=>call.method==="POST").length,1);
});
