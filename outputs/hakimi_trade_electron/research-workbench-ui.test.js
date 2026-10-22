"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const html=fs.readFileSync(path.resolve(__dirname,"../../src/hakimi_research/resources/workbench.html"),"utf8");
const source=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];let id=0;
const box={module:{exports:{}},crypto:{randomUUID:()=>"operation-"+(++id)},btoa:s=>Buffer.from(s,"binary").toString("base64"),console};
vm.runInNewContext(source,box);const ui=box.module.exports,copy=value=>JSON.parse(JSON.stringify(value));
const data=()=>({engine:{name:"hakimi_research",version:"test",permissions:{live_trading_allowed:false}},workspace:"temporary",inputs:[],tasks:[],runs:[],accounts:[],watches:[],operations:[],strategies:{"price.dual_ma@1":{title:"双均线",parameters:["fast_window","slow_window","position_pct","stop_loss_pct","take_profit_pct"],defaults:{fast_window:20,slow_window:60,position_pct:.25,stop_loss_pct:.03,take_profit_pct:.06},required_context_sessions:61,continuous_supported:true,event_rule:null}}});
const input=()=>({ref:"data/snapshots/a.json",kind:"PRICE_SNAPSHOT",status:"READY",security:{symbol:"AAPL",security_id:"US:AAPL"},coverage_start:"2024-01-01",coverage_end:"2024-12-31",sessions:252,source:{name:"fixture"}});
const taskRow=()=>({ref:"tasks/task-a",family_id:"family-a",title:"观察任务",state:"ENABLED",strategy:"price.dual_ma@1",inputs:{snapshot:input()},configuration:{requested:{},effective:{},exit_rule:"均线与保护退出"}});
const run=()=>({ref:"runs/run-a",view:{symbol:"AAPL",strategy:{title:"双均线"},score_start:"2024-04-01",score_end:"2024-12-31"},summary:{total_return:.03,max_drawdown:.02,total_fees:4,fill_count:1},signals:[{time:"2024-04-01",action:"BUY",reason:"cross"}],fills:[{time:"2024-04-02",side:"BUY",price:100,quantity:2,fee:.16}],equity_curve:[{time:"2024-04-01",equity:10000},{time:"2024-12-31",equity:10300}]});
const account=()=>({ref:"continuous/account-a",title:"连续观察",continuous:{status:"READY",task_paused:{"family:family-a":false},session_results:[]},state:{paused:false,positions:{}},cash:"10000",available_cash:"10000",equity:"10000",history:[],limits:{}});
const storage=()=>{const map=new Map();return {getItem:key=>map.get(key),setItem:(key,value)=>map.set(key,value),removeItem:key=>map.delete(key)};};

test("formal HTML defines an isolated same-origin token client and never starts a monitor on load",()=>{
  assert.match(html,/content="__SESSION_TOKEN__"/);assert.match(source,/"X-Hakimi-Token":token/);
  assert.doesNotMatch(source,/setInterval|\/api\/(?:orders|paper|broker)|hakimi_terminal_research/);
  assert.match(html,/重启后不会自动恢复观察/);assert.match(html,/暂停新增后/);
});
test("visible percentages become canonical ratios exactly once and rules keep their explicit input binding",()=>{
  const entry=data().strategies["price.dual_ma@1"],values={title:"MA",strategy:"price.dual_ma@1",snapshot:"data/a.json",event_context:null,params:{fast_window:"20",slow_window:"60",position_pct:"25",stop_loss_pct:"3",take_profit_pct:"6"},score_start:"2024-04-01",score_end:"2024-12-31",initial_cash:"10000",fee_rate:"0.08",slippage_pct:"0.05"};
  const result=ui.taskPayload(values,entry);assert.equal(result.params.position_pct,.25);assert.equal(result.params.stop_loss_pct,.03);assert.equal(result.fee_rate,.0008);assert.equal(result.slippage_pct,.0005);assert.equal(values.params.position_pct,"25");
  assert.throws(()=>ui.taskPayload(values,{...entry,event_rule:"schedule"}),/需要明确选择/);
  assert.throws(()=>ui.taskPayload({...values,params:{...values.params,fast_window:"2.5"}},entry),/参数/);
});
test("old refresh cannot replace a newer selection and unverified saves remain locked across refresh",async()=>{
  const waits=[],saved=storage(),controller=ui.createController({storage:saved,uuid:()=>"operation-exact",request:(route)=>route==="/api/state"?new Promise(resolve=>waits.push(resolve)):Promise.reject(Error("connection lost"))});
  const first=controller.refresh(),second=controller.refresh();waits[1]({...data(),workspace:"new"});await second;waits[0]({...data(),workspace:"old"});await first;assert.equal(controller.state.data.workspace,"new");
  const action=controller.action("run_task",{task:"tasks/a"});await new Promise(setImmediate);waits.at(-1)({...data(),operations:[{operation_id:"operation-exact",status:"UNKNOWN_REQUIRES_REVIEW"}]});await assert.rejects(action,/尚未核实/);assert.equal(controller.state.pending,"operation-exact");
  await assert.rejects(controller.action("run_task",{task:"tasks/a"}),/上一项/);
  const reopened=ui.createController({storage:saved,request:async()=>({...data(),operations:[{operation_id:"different",status:"COMMITTED"}]})});await reopened.refresh();assert.equal(reopened.state.pending,"operation-exact");
  const reconciled=ui.createController({storage:saved,request:async()=>({...data(),operations:[{operation_id:"operation-exact",status:"COMMITTED"}]})});await reconciled.refresh();assert.equal(reconciled.state.pending,"");
});
test("one successful explicit operation yields one write and a durable known rejection can be cleared",async()=>{
  const calls=[];let receipt=null;
  const controller=ui.createController({uuid:()=>"operation-owned",request:async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return {...data(),operations:receipt?[receipt]:[]};receipt={operation_id:payload.operation_id,status:"STOPPED",ok:false};throw Error("invalid window");}});
  await assert.rejects(controller.action("create_task",{operation_id:"forged",action:"forged"}),/invalid window/);
  assert.equal(calls[0].payload.operation_id,"operation-owned");assert.equal(calls[0].payload.action,"create_task");assert.equal(controller.state.pending,"");assert.equal(calls.filter(v=>v.route==="/api/action").length,1);
});
test("saved metrics, unavailable comparison and untrusted sources remain distinct",()=>{
  assert.match(ui.runHtml(run()),/3%/);assert.match(ui.runHtml(run()),/最大回撤/);assert.match(ui.runHtml(run()),/cross/);
  const malicious=run();malicious.signals[0].reason='<img src=x onerror="bad">';assert.ok(!ui.runHtml(malicious).includes('<img src=x'));
  const result=ui.comparisonHtml({status:"NOT_COMPARABLE",mismatches:[{row:2,fields:["dataset"]}],rows:[],differences_from_first:[]});assert.match(result,/不计算跨结果收益差/);assert.match(result,/独立本金/);
});

function documentFixture(){
  const ids=new Map(),all=new Set(),listeners={};let document;
  const camel=name=>name.replace(/-([a-z])/g,(_c,l)=>l.toUpperCase()),dash=name=>name.replace(/[A-Z]/g,c=>"-"+c.toLowerCase());
  const decode=value=>String(value).replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
  const escape=value=>String(value).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const voids=new Set(["INPUT","META","LINK","BR","HR","IMG"]);
  function descendants(node){return node.children.flatMap(child=>[child,...descendants(child)]);}
  function matches(node,selector){
    const parts=selector.trim().split(/\s+/),last=parts.pop();if(parts.length&&!node.closest(parts.join(" ")))return false;
    if(last.startsWith("."))return String(node.className||"").split(/\s+/).includes(last.slice(1));
    const attr=/^\[([\w-]+)(?:="([^"]*)")?\](:checked)?$/.exec(last);
    if(attr)return Object.hasOwn(node.attributes,attr[1])&&(attr[2]===undefined||node.attributes[attr[1]]===attr[2])&&(!attr[3]||node.checked);
    return node.tagName.toLowerCase()===last;
  }
  function detach(node){for(const child of [...node.children])detach(child);all.delete(node);if(node.id&&ids.get(node.id)===node)ids.delete(node.id);if(document?.activeElement===node)document.activeElement=null;}
  class Element{
    constructor(tag,attrs=""){this.tagName=tag.toUpperCase();this.childNodes=[];this._hidden=false;this.hiddenHistory=[];this._value="";this.disabled=false;this.checked=false;this.open=false;this.files=[];this.attributes={};this.scrollTop=0;this.scrollLeft=0;this.dataset=new Proxy({}, {set:(object,key,value)=>{object[key]=String(value);this.attributes["data-"+dash(key)]=String(value);return true;},deleteProperty:(object,key)=>{delete object[key];delete this.attributes["data-"+dash(key)];return true;}});all.add(this);for(const [,key,value] of attrs.matchAll(/([\w-]+)(?:="([^"]*)")?/g))this.setAttribute(key,decode(value??""));}
    get children(){return this.childNodes.filter(child=>child instanceof Element);}get firstElementChild(){return this.children[0]||null;}
    get className(){return this.attributes.class||"";}set className(value){this.attributes.class=value;}
    get hidden(){return this._hidden;}set hidden(value){this._hidden=Boolean(value);this.hiddenHistory.push(this._hidden);}
    get value(){return this._value;}set value(value){this._value=String(value);}
    get options(){return descendants(this).filter(child=>child.tagName==="OPTION");}
    get textContent(){return this.childNodes.map(child=>child instanceof Element?child.textContent:child.text).join("");}
    set textContent(value){for(const child of this.children)detach(child);this.childNodes=[{text:String(value)}];}
    set innerHTML(value){
      for(const child of this.children)detach(child);this.childNodes=[];const stack=[this];
      for(const token of String(value).match(/<[^>]*>|[^<]+/g)||[]){
        if(token.startsWith("<!"))continue;
        const closing=/^<\/([\w-]+)/.exec(token);if(closing){for(let i=stack.length-1;i>0;i--)if(stack[i].tagName.toLowerCase()===closing[1]){stack.length=i;break;}continue;}
        const opening=/^<([a-z][\w-]*)\b([^>]*)>/i.exec(token);
        if(opening){const child=new Element(opening[1],opening[2]);stack.at(-1).appendChild(child);if(!voids.has(child.tagName)&&!token.endsWith("/>"))stack.push(child);}
        else stack.at(-1).childNodes.push({text:decode(token)});
      }
      if(this.tagName==="SELECT")this.value=this.options[0]?.value||"";
    }
    get innerHTML(){return this.childNodes.map(child=>child instanceof Element?child.outerHTML:escape(child.text)).join("");}
    get outerHTML(){const attrs=Object.entries(this.attributes).map(([key,value])=>` ${key}="${escape(value)}"`).join("");return `<${this.tagName.toLowerCase()}${attrs}>`+(voids.has(this.tagName)?"":this.innerHTML+`</${this.tagName.toLowerCase()}>`);}
    appendChild(child){if(child.parent){child.parent.childNodes=child.parent.childNodes.filter(item=>item!==child);}child.parent=this;this.childNodes.push(child);return child;}
    remove(){if(this.parent)this.parent.childNodes=this.parent.childNodes.filter(item=>item!==this);detach(this);this.parent=null;}
    setAttribute(key,value){this.attributes[key]=String(value);if(key==="id"){this.id=String(value);ids.set(this.id,this);}else if(key.startsWith("data-"))this.dataset[camel(key.slice(5))]=value;else if(key==="value")this.value=value;else if(key==="checked")this.checked=true;else if(key==="disabled")this.disabled=true;else if(key==="hidden")this.hidden=true;else if(key==="open")this.open=true;}
    removeAttribute(key){delete this.attributes[key];if(key.startsWith("data-"))delete this.dataset[camel(key.slice(5))];if(key==="disabled")this.disabled=false;if(key==="hidden")this.hidden=false;}
    focus(){document.activeElement=this;}reportValidity(){return true;}
    closest(selector){for(let node=this;node;node=node.parent)if(matches(node,selector))return node;return null;}
    querySelectorAll(selector){return descendants(this).filter(node=>matches(node,selector));}querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  }
  document={getElementById:id=>ids.get(id),querySelectorAll:selector=>[...all].filter(node=>matches(node,selector)),createElement:tag=>new Element(tag),addEventListener:(kind,handler)=>{listeners[kind]=handler;},scrollingElement:{scrollTop:0,scrollLeft:0},hidden:false};
  const root=new Element("body");root.innerHTML=html.split("<script>")[0];
  return {document,get:id=>ids.get(id),all,listeners,button:(action,ref)=>[...all].find(v=>v.dataset.action===action&&(!ref||v.dataset.ref===ref)),submit:id=>listeners.submit({target:ids.get(id),preventDefault(){}}),click:button=>listeners.click({target:button})};
}
const flush=()=>new Promise(setImmediate);
test("mounted workflow imports, saves, runs, reopens and creates paused-by-default local observation without external requests",async()=>{
  const dom=documentFixture(),current=data(),calls=[];let detail=account();
  const request=async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);if(route.startsWith("/api/run?"))return run();if(route.startsWith("/api/account?"))return copy(detail);assert.equal(route,"/api/action");let result={};switch(payload.action){case"import_input":current.inputs=[input()];result=input();break;case"create_task":current.tasks=[taskRow()];result=taskRow();break;case"run_task":current.runs=[{...run().view,ref:run().ref,total_return:.03,fill_count:1,total_fees:4}];result=run();break;case"create_account":current.accounts=[copy(detail)];result=detail;break;case"pause_account":detail.state.paused=payload.paused;detail.continuous.status="PAUSED_NEW_ENTRIES";current.accounts=[copy(detail)];result={account:detail};break;case"configure_watch":current.watches=[{ref:"watches/a",account:detail.ref,monitoring:false,status:"STOPPED"}];result=current.watches[0];break;default:throw Error(payload.action);}current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:copy(result)};};
  const app=ui.mount(dom.document,request,storage());await flush();
  dom.get("snapshot-file").files=[{name:"snapshot.json",size:2,arrayBuffer:async()=>new Uint8Array([123,125]).buffer}];await dom.submit("snapshot-form");assert.match(dom.get("input-list").innerHTML,/AAPL/);
  await dom.click(dom.button("new-task"));dom.get("task-title").value="观察任务";dom.get("task-snapshot").value=input().ref;dom.get("score-start").value="2024-04-01";dom.get("score-end").value="2024-12-31";
  await dom.submit("task-form");assert.equal(calls.find(v=>v.payload?.action==="create_task").payload.params.position_pct,.25);assert.match(dom.get("task-list").innerHTML,/观察任务/);
  await dom.click(dom.button("run-task",taskRow().ref));assert.match(dom.get("run-detail").innerHTML,/3%/);await app.controller.refresh();await app.openRun(run().ref);assert.equal(calls.filter(v=>v.payload?.action==="run_task").length,1);
  dom.document.querySelectorAll("[data-account-task]")[0].checked=true;dom.get("account-title").value="连续观察";await dom.submit("account-form");assert.match(dom.get("account-summary").innerHTML,/下次提供完整有效数据/);
  await dom.click(dom.button("pause-account"));assert.equal(detail.state.paused,true);assert.match(dom.get("account-summary").innerHTML,/暂停新增/);
  dom.document.querySelectorAll("[data-advance-input]")[0].checked=true;await dom.submit("watch-form");assert.match(dom.get("watch-list").innerHTML,/观察已停止/);assert.equal(calls.filter(v=>v.payload?.action==="start_watch").length,0);
  assert.ok(calls.every(v=>v.route.startsWith("/api/")));assert.equal(app.controller.state.pending,"");
});

test("research preview requires a fresh human decision and binds the exact approved record only when selected",async()=>{
  const dom=documentFixture(),current=data(),calls=[];
  current.inputs=[input()];current.research_imports=[];
  current.strategies["event.earnings_schedule@1"]={title:"财报排期",parameters:["target_position_pct"],defaults:{target_position_pct:.25},required_context_sessions:1,continuous_supported:true,event_rule:"schedule"};
  const preview={ref:"research-imports/preview-a",status:"REJECTED",security_id:"US:AAPL",reasons:["human_confirmation_required"],event_versions:[{event_id:"event-a",version:1,source_url:"https://source.example/announcement",version_public_at:"2024-03-01T12:00:00Z",available_at:"2024-03-01T12:00:00Z",scheduled_date:"2024-04-15",time_precision:"DATE_ONLY",schedule_status:"SCHEDULED"}]};
  const approved={...preview,ref:"research-imports/review-accepted",status:"READY_FOR_EXPLICIT_INPUT_CHECK",reasons:[],confirmation_declaration:{actor:"人工核对者",decision:"ACCEPT_FOR_INPUT_CHECK"}};
  const context={ref:"data/contexts/schedule.json",kind:"SCHEDULE_CONTEXT",status:"READY",security_id:"US:AAPL",versions:preview.event_versions};
  const eventTask={...taskRow(),strategy:"event.earnings_schedule@1"};
  const request=async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);assert.equal(route,"/api/action");let result={};switch(payload.action){
    case"preview_research":current.research_imports.push(preview);result=preview;break;
    case"review_research":if(payload.decision==="REJECT"){result={...preview,ref:"research-imports/review-rejected",confirmation_declaration:{actor:payload.actor,decision:"REJECT"}};}else{result=approved;current.inputs.push(context);}current.research_imports.push(result);break;
    case"create_task":current.tasks=[eventTask];result=eventTask;break;
    case"bind_research":result={...eventTask,viewed_revision:"2-bound"};current.runs=[{...run().view,ref:run().ref}];break;
    case"export_research_result":result={ref:"exports/return-a",external_database_modified:false};break;
    default:throw Error(payload.action);
  }current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:copy(result)};};
  const app=ui.mount(dom.document,request,storage());await flush();
  const file=(name,text)=>({name,size:Buffer.byteLength(text),arrayBuffer:async()=>Uint8Array.from(Buffer.from(text)).buffer});
  dom.get("research-result-file").files=[file("result.json","{}")];dom.get("research-context-file").files=[file("context.json","{}")];dom.get("research-source-file").files=[file("source.html","<h1>Original</h1>")];dom.get("research-security").value="US:AAPL";
  await dom.submit("research-preview-form");assert.equal(calls.filter(v=>v.payload?.action==="review_research").length,0);assert.equal(calls.find(v=>v.payload?.action==="preview_research").payload.source_base64,Buffer.from("<h1>Original</h1>").toString("base64"));
  assert.equal(dom.get("research-decision").value,"");assert.equal(dom.get("research-actor").value,"");assert.equal(dom.get("research-reason").value,"");assert.equal(dom.get("research-use").hidden,true);assert.match(dom.get("research-preview").innerHTML,/2024-03-01T12:00:00Z/);
  await dom.submit("research-review-form");assert.equal(calls.filter(v=>v.payload?.action==="review_research").length,0);
  dom.get("research-decision").value="REJECT";dom.get("research-actor").value="人工核对者";dom.get("research-reason").value="先保留异议";await dom.submit("research-review-form");assert.equal(dom.get("research-use").hidden,true);
  await dom.click(dom.button("research-detail",preview.ref));assert.equal(dom.get("research-actor").value,"");dom.get("research-decision").value="ACCEPT_FOR_INPUT_CHECK";dom.get("research-actor").value="人工核对者";dom.get("research-reason").value="已逐项核对原始来源和可用时间";await dom.submit("research-review-form");assert.equal(dom.get("research-use").hidden,false);assert.equal(dom.get("task-research").value,"");
  dom.get("task-strategy").value="event.earnings_schedule@1";dom.listeners.change({target:dom.get("task-strategy")});dom.get("task-title").value="排期观察";dom.get("task-snapshot").value=input().ref;dom.get("task-event").value=context.ref;dom.get("task-research").value=approved.ref;dom.get("score-start").value="2024-04-01";dom.get("score-end").value="2024-12-31";await dom.submit("task-form");
  const saved=calls.find(v=>v.payload?.action==="create_task").payload;assert.equal(saved.research,approved.ref);assert.equal(saved.event_context,context.ref);assert.equal(saved.params.target_position_pct,.25);
  dom.get("research-bind-task").value=eventTask.ref;await dom.click(dom.button("bind-research"));assert.equal(calls.find(v=>v.payload?.action==="bind_research").payload.research,approved.ref);
  dom.get("research-export-run").value=run().ref;await dom.click(dom.button("export-research"));assert.equal(calls.find(v=>v.payload?.action==="export_research_result").payload.research,approved.ref);assert.match(dom.get("research-export-result").innerHTML,/未写入研究侧数据库/);assert.match(dom.get("research-export-result").textContent,/尚未被研究侧接收/);assert.match(dom.get("research-export-result").textContent,/旧回执未提供反馈文件名/);
  await app.controller.refresh();assert.equal(calls.filter(v=>v.payload?.action==="create_task").length,1);assert.equal(calls.filter(v=>v.payload?.action==="export_research_result").length,1);
});

test("local feedback export shows the exact import file and next manual step without claiming delivery",async()=>{
  const dom=documentFixture(),approved={ref:"research-imports/accepted-ndaq",status:"READY_FOR_EXPLICIT_INPUT_CHECK",security_id:"US:NDAQ",event_versions:[],confirmation_declaration:{actor:"使用者",decision:"ACCEPT_FOR_INPUT_CHECK"}},current={...data(),research_imports:[approved],runs:[{...run().view,ref:run().ref}]},calls=[];
  const digest="a".repeat(64),filename=`research-feedback-${digest}.md`,result={status:"FROZEN_RESEARCH_RETURN_READY",delivery_status:"LOCAL_EXPORT_ONLY_NOT_RECEIVED",directory:"C:\\research workspace\\exports\\return-a",ref:"exports/return-a",feedback_filename:filename,feedback_sha256:digest,feedback_ref:`exports/return-a/${filename}`,external_database_modified:false,research_input_outcome:{status:"FILTER_RECORDED",note:"原始影响说明 <保留>"}};
  ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);assert.equal(route,"/api/action");assert.equal(payload.action,"export_research_result");current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result};},storage());await flush();
  await dom.click(dom.button("research-detail",approved.ref));dom.get("research-export-run").value=run().ref;await dom.click(dom.button("export-research"));
  const output=dom.get("research-export-result"),text=output.textContent;assert.ok(text.includes(filename));assert.ok(text.includes(result.feedback_ref));assert.ok(text.includes(result.directory));assert.match(text,/在交易分析的房间资料中选择导入文件/);assert.match(text,/尚未被研究侧接收/);assert.match(text,/未写入研究侧数据库/);assert.match(text,/查看本地导出回执/);assert.match(text,/研究输入的实际影响/);assert.ok(text.includes(result.status));assert.ok(text.includes(digest));assert.ok(output.innerHTML.includes("&lt;保留&gt;"));
  assert.equal(calls.filter(row=>row.payload).length,1);assert.equal(calls.find(row=>row.payload).payload.research,approved.ref);assert.ok(calls.every(row=>row.route.startsWith("/api/")));
});

test("a durable schedule rejection explains the time boundary and preserves the draft, while an unverified rejection remains unknown",async()=>{
  for(const confirmed of [true,false]){
    const dom=documentFixture(),snapshot={...input(),security:{symbol:"NDAQ",security_id:"US:NDAQ"},coverage_start:"2026-09-15",coverage_end:"2026-10-21",sessions:26},context={ref:"data/contexts/ndaq.json",kind:"SCHEDULE_CONTEXT",status:"READY",security_id:"US:NDAQ",versions:[]},current={...data(),inputs:[snapshot,context]},calls=[];
    current.strategies["event.earnings_schedule@1"]={title:"财报排期",parameters:["target_position_pct"],defaults:{target_position_pct:.25},required_context_sessions:1,event_rule:"schedule"};
    const code="event_schedule_filter_NOT_RUN_no_historical_usable_schedule";
    const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);if(payload.action==="task_context")return {ok:true,result:{required_context_sessions:1,suggested_score_start:"2026-09-16",coverage_end:"2026-10-21",sessions:26}};calls.push(payload);assert.equal(payload.action,"create_task");if(confirmed)current.operations.push({operation_id:payload.operation_id,ok:false,status:"STOPPED",error:code,automatic_retry:false});return {ok:false,error:code,automatic_retry:false};},storage());await flush();
    await dom.click(dom.button("new-task"));dom.get("task-strategy").value="event.earnings_schedule@1";dom.listeners.change({target:dom.get("task-strategy")});dom.get("task-title").value="NDAQ 排期演示";dom.get("task-snapshot").value=snapshot.ref;dom.get("task-event").value=context.ref;dom.get("score-start").value="2026-10-21";dom.get("score-end").value="2026-10-21";dom.listeners.input({target:dom.get("score-start")});dom.listeners.input({target:dom.get("score-end")});await dom.submit("task-form");
    assert.equal(calls.length,1);assert.equal(current.tasks.length,0);assert.equal(dom.get("task-editor").hidden,false);assert.equal(dom.get("task-title").value,"NDAQ 排期演示");assert.equal(dom.get("task-event").value,context.ref);assert.equal(dom.get("score-start").value,"2026-10-21");assert.equal(dom.get("score-end").value,"2026-10-21");assert.doesNotMatch(dom.get("status").textContent,/正在保存/);
    if(confirmed){assert.equal(app.controller.state.pending,"");assert.match(dom.get("status").textContent,/本次未保存/);assert.equal(dom.get("error").textContent,"当前行情窗口内还没有可用的排期版本，任务未创建。请在新增完整日线并核对后重试；不可提前使用公告。");assert.ok(dom.get("engine-detail").textContent.includes(code));}
    else{assert.ok(app.controller.state.pending);assert.match(dom.get("status").textContent,/尚未核实/);assert.doesNotMatch(dom.get("status").textContent,/未保存/);assert.doesNotMatch(dom.get("error").textContent,/任务未创建/);current.operations.push({operation_id:calls[0].operation_id,ok:false,status:"STOPPED",error:code,automatic_retry:false});await app.controller.refresh();assert.equal(app.controller.state.pending,"");assert.match(dom.get("status").textContent,/本次未保存/);assert.match(dom.get("error").textContent,/任务未创建/);assert.equal(calls.length,1);}
  }
});

test("late or mismatched saved-result reads never replace the explicitly selected result",async()=>{
  const dom=documentFixture(),waiting=[];const app=ui.mount(dom.document,route=>route==="/api/state"?Promise.resolve(data()):new Promise(resolve=>waiting.push(resolve)),storage());await flush();
  const first=app.openRun("runs/old"),second=app.openRun("runs/new");waiting[1]({...run(),ref:"runs/new",view:{...run().view,symbol:"NEW"}});await second;waiting[0]({...run(),ref:"runs/old",view:{...run().view,symbol:"OLD"}});await first;assert.match(dom.get("run-detail").innerHTML,/NEW/);assert.doesNotMatch(dom.get("run-detail").innerHTML,/OLD/);
  const mismatch=app.openRun("runs/exact");waiting[2]({...run(),ref:"runs/other"});await mismatch;assert.match(dom.get("run-detail").innerHTML,/读取失败/);assert.match(dom.get("error").textContent,/身份不一致/);
});

test("changed runtime stays readable but blocks new operations before a pending request is created",async()=>{
  const dom=documentFixture(),calls=[],current={...data(),runtime_guard:{restart_required:true}};
  const app=ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});return copy(current);},storage());await flush();
  assert.equal(dom.get("restart").hidden,false);assert.ok(dom.document.querySelectorAll("[data-write]").every(button=>button.disabled));
  await assert.rejects(app.controller.action("create_account",{}),/程序文件已更新/);assert.equal(app.controller.state.pending,"");assert.equal(calls.filter(v=>v.route==="/api/action").length,0);
  await app.controller.refresh();assert.equal(calls.length,2);
});

test("stopping local observation remains available after a runtime change and requires a positive receipt",async()=>{
  const dom=documentFixture(),current={...data(),runtime_guard:{restart_required:true},accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT"}]};let accepted=false;const calls=[];
  const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return account();calls.push(payload);if(!accepted)return {ok:false,error:"stop not confirmed"};current.watches[0].monitoring=false;return {ok:true,result:current.watches[0]};},storage());await flush();await app.openAccount(account().ref);
  const stop=dom.button("stop-watch");assert.equal(stop.disabled,false);await dom.click(stop);assert.match(dom.get("error").textContent,/stop not confirmed/);assert.doesNotMatch(dom.get("status").textContent,/已停止观察/);
  accepted=true;await dom.click(stop);assert.match(dom.get("status").textContent,/已停止观察/);assert.equal(calls.length,2);assert.ok(calls.every(row=>row.action==="stop_watch"));assert.equal(dom.button("start-watch").disabled,true);
});

test("loss recovery requires a later completed session and sends the explicitly reviewed receipt head",async()=>{
  const same={...account(),receipt_head:"receipt-current",state:{paused:true,loss_halted:true,positions:{}},continuous:{status:"LOSS_HALTED",loss_halt_session:"2024-04-02",last_session:"2024-04-02"}};
  assert.match(ui.lossResetHtml(same),/data-unavailable="true"/);assert.equal(ui.lossResetHtml(account()),"");
  const detail={...same,continuous:{...same.continuous,last_session:"2024-04-03"}},dom=documentFixture(),current={...data(),accounts:[detail]},calls=[];
  const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return copy(detail);calls.push(payload);assert.equal(payload.action,"reset_loss");detail.state.loss_halted=false;detail.continuous.status="PAUSED_NEW_ENTRIES";return {ok:true,result:{account:detail}};},storage());await flush();await app.openAccount(detail.ref);
  assert.equal(calls.length,0);await dom.click(dom.button("reset-loss"));assert.equal(calls.length,1);assert.equal(calls[0].expected_head,"receipt-current");assert.equal(calls[0].account,detail.ref);assert.equal(detail.state.paused,true);assert.equal(dom.button("reset-loss"),undefined);
});

test("only a stopped review-required watch can explicitly discard an exact uncommitted request with a reason",async()=>{
  const watch={ref:"watches/review",account:account().ref,status:"PENDING_REVIEW_REQUIRED",pending_operation_id:"pending-exact",monitoring:false};
  assert.match(ui.watchRecoveryHtml(watch),/放弃理由/);assert.equal(ui.watchRecoveryHtml({...watch,monitoring:true}),"");assert.doesNotMatch(ui.watchRecoveryHtml({...watch,status:"SUBMISSION_UNKNOWN"}),/discard-watch/);
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[watch]},calls=[];
  const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return account();calls.push(payload);watch.pending_operation_id=null;watch.status="STOPPED";return {ok:true,result:watch};},storage());await flush();await app.openAccount(account().ref);
  const button=dom.button("discard-watch"),reason={value:""};button.closest=selector=>selector==="button"?button:{querySelector:()=>reason};
  await dom.click(button);assert.equal(calls.length,0);reason.value="已核对未提交请求与旧控制状态，保留原始记录";await dom.click(button);assert.equal(calls.length,1);assert.equal(calls[0].action,"discard_watch_pending");assert.equal(calls[0].expected_operation_id,"pending-exact");assert.equal(calls[0].reason,reason.value);assert.equal(calls.some(row=>row.action==="start_watch"),false);
});

test("reopening an unknown watch offers explicit recovery of its original request without starting observation",async()=>{
  for(const outcome of ["CURRENT","INPUT_REJECTED","PENDING_REVIEW_REQUIRED","SUBMISSION_UNKNOWN"]){
    const watch={ref:"watches/interrupted",account:account().ref,status:"SUBMISSION_UNKNOWN",pending_operation_id:"watch-original",monitoring:false};
    const dom=documentFixture(),current={...data(),accounts:[account()],watches:[watch]},calls=[];
    const app=ui.mount(dom.document,async(route,payload)=>{
      if(route==="/api/state")return copy(current);
      if(route.startsWith("/api/account?"))return account();
      calls.push(payload);assert.equal(payload.action,"recover_watch_pending");
      assert.equal(payload.watch,watch.ref);assert.equal(payload.expected_operation_id,"watch-original");
      watch.status=outcome;if(["CURRENT","INPUT_REJECTED"].includes(outcome))watch.pending_operation_id=null;
      current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});
      return {ok:true,result:copy(watch)};
    },storage());
    await flush();await app.openAccount(account().ref);await app.controller.refresh();
    assert.equal(calls.length,0);assert.equal(dom.button("start-watch").disabled,true);
    const recover=dom.button("recover-watch");assert.ok(recover,"a reopened pending watch needs a visible recovery entry");assert.equal(recover.disabled,false);
    await dom.click(recover);assert.equal(calls.length,1);assert.equal(watch.monitoring,false);
    assert.equal(calls.some(row=>row.action==="start_watch"),false);
    if(["CURRENT","INPUT_REJECTED"].includes(outcome)){
      assert.equal(dom.button("recover-watch"),undefined);assert.equal(dom.button("start-watch").disabled,false);
      assert.match(dom.get("status").textContent,/原回执|原提交/);
    }else{
      assert.equal(dom.button("start-watch").disabled,true);assert.ok(dom.button("recover-watch"));
      assert.equal(Boolean(dom.button("discard-watch")),outcome==="PENDING_REVIEW_REQUIRED");
      assert.match(dom.get("status").textContent,outcome==="SUBMISSION_UNKNOWN"?/仍未确认/:/人工复核/);
    }
  }
});

test("pending recovery keeps normal controls and generic unknown-operation locks",async()=>{
  for(const status of ["STOPPED","SUBMISSION_UNKNOWN","PENDING_REVIEW_REQUIRED"]){
    const watch={ref:"watches/interrupted",account:account().ref,status,pending_operation_id:"watch-original",monitoring:false};
    assert.match(ui.watchRecoveryHtml(watch),/核对原提交并恢复/);
    assert.equal(ui.watchRecoveryHtml({...watch,pending_operation_id:null}),"");
    assert.equal(ui.watchRecoveryHtml({...watch,monitoring:true}),"");
    const dom=documentFixture(),current={...data(),accounts:[account()],watches:[watch],operations:[{operation_id:"other-unknown",status:"UNKNOWN_REQUIRES_REVIEW"}]};
    const app=ui.mount(dom.document,async route=>route==="/api/state"?copy(current):account(),storage());await flush();await app.openAccount(account().ref);
    assert.equal(dom.button("recover-watch").disabled,true);
    assert.equal(dom.button("start-watch").disabled,true);
  }
});

test("an unreadable durable pending record blocks a new watch without inventing a recoverable identity",async()=>{
  const watch={ref:"watches/corrupt",account:account().ref,status:"SUBMISSION_UNKNOWN",pending_present:true,pending_operation_id:null,monitoring:false};
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[watch]};
  const app=ui.mount(dom.document,async route=>route==="/api/state"?copy(current):account(),storage());await flush();await app.openAccount(account().ref);
  assert.equal(dom.button("start-watch").disabled,true);assert.equal(dom.button("recover-watch"),undefined);assert.equal(dom.button("discard-watch"),undefined);
  assert.match(dom.get("watch-list").textContent,/原提交记录暂时无法核实/);
});

test("edited rule parameters use canonical context, discard late defaults and preserve manually entered dates",async()=>{
  const dom=documentFixture(),current=data(),reads=[];current.inputs=[{...input(),security:{symbol:"NDAQ",security_id:"US:NDAQ"},sessions:26,coverage_end:"2024-02-05"}];current.strategies["price.dual_ma@1"].required_context_sessions=62;
  ui.mount(dom.document,(route,payload)=>{if(route==="/api/state")return Promise.resolve(copy(current));assert.equal(route,"/api/action");assert.equal(payload.action,"task_context");assert.equal(payload.operation_id,undefined);return new Promise(resolve=>reads.push({payload,resolve}));},storage());await flush();
  dom.get("task-snapshot").value=input().ref;const old=dom.listeners.change({target:dom.get("task-snapshot")});assert.match(dom.get("input-note").textContent,/正在按当前参数/);assert.doesNotMatch(dom.get("input-note").textContent,/62 根预热/);
  dom.get("param-fast_window").value="5";dom.get("param-slow_window").value="10";const edited=dom.listeners.input({target:dom.get("param-slow_window")});assert.equal(reads[1].payload.params.fast_window,5);assert.equal(reads[1].payload.params.slow_window,10);assert.equal(reads[1].payload.params.position_pct,.25);assert.equal(reads[1].payload.snapshot,input().ref);
  const context={required_context_sessions:12,suggested_score_start:"2024-01-17",coverage_end:"2024-02-05",sessions:26};reads[1].resolve({ok:true,result:context});await edited;assert.match(dom.get("input-note").textContent,/12 根预热/);assert.equal(dom.get("score-start").value,"2024-01-17");assert.equal(dom.get("score-end").value,"2024-02-05");
  reads[0].resolve({ok:true,result:{...context,required_context_sessions:62,suggested_score_start:null}});await old;assert.match(dom.get("input-note").textContent,/12 根预热/);assert.equal(dom.get("score-start").value,"2024-01-17");
  dom.get("score-start").value="2024-01-19";dom.listeners.input({target:dom.get("score-start")});dom.get("score-end").value="";dom.listeners.change({target:dom.get("score-end")});dom.get("param-slow_window").value="11";const revised=dom.listeners.input({target:dom.get("param-slow_window")});reads[2].resolve({ok:true,result:{...context,required_context_sessions:13,suggested_score_start:"2024-01-18"}});await revised;assert.match(dom.get("input-note").textContent,/13 根预热/);assert.equal(dom.get("score-start").value,"2024-01-19");assert.equal(dom.get("score-end").value,"");
  const pending=dom.listeners.change({target:dom.get("task-snapshot")});dom.get("task-snapshot").value="";await dom.listeners.change({target:dom.get("task-snapshot")});reads[3].resolve({ok:true,result:context});await pending;assert.match(dom.get("input-note").textContent,/先选择/);assert.doesNotMatch(dom.get("input-note").textContent,/12 根预热/);
});

test("context failures and invalid parameters remove prior requirements instead of reusing catalog defaults",async()=>{
  const dom=documentFixture(),current={...data(),inputs:[input()]},calls=[];let fail=false;
  ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);calls.push(payload);if(fail)throw Error("context unavailable");return {ok:true,result:{required_context_sessions:62,suggested_score_start:"2024-04-01",coverage_end:"2024-12-31",sessions:252}};},storage());await flush();
  dom.get("task-snapshot").value=input().ref;await dom.listeners.change({target:dom.get("task-snapshot")});assert.match(dom.get("input-note").textContent,/62 根预热/);
  fail=true;dom.get("param-fast_window").value="5";await dom.listeners.input({target:dom.get("param-fast_window")});assert.match(dom.get("input-note").textContent,/尚未核实/);assert.doesNotMatch(dom.get("input-note").textContent,/62 根预热/);
  dom.get("param-fast_window").value="";await dom.listeners.input({target:dom.get("param-fast_window")});assert.equal(calls.length,2);assert.match(dom.get("input-note").textContent,/请核对规则参数/);
});

test("watch conditions explain stopping and unavailable protection in ordinary language",()=>{
  for(const [status,label] of Object.entries({WAITING_STABLE_INPUT:"等待输入稳定",INPUT_MISSING:"缺少本地输入",INPUT_STALE:"数据已过期",INPUT_NOT_YET_AVAILABLE:"等待数据可用",INPUT_ERROR:"本地输入读取或校验失败",INPUT_REJECTED:"本次输入未通过检查",SUBMISSION_UNKNOWN:"需要核对提交结果",PENDING_REVIEW_REQUIRED:"未提交请求需要人工复核"})){
    const result=ui.watchStatusHtml({status,reason:"Raw internal diagnostic"});assert.ok(result.includes(label),status);assert.match(result,/持仓保护/);assert.doesNotMatch(result,/Raw internal diagnostic|待核对/);assert.ok(!result.includes(status));
  }
  assert.match(ui.watchStatusHtml({status:"NEW_UNKNOWN_STATUS"}),/不能确认/);
});

test("the real polling callback preserves focused controls, open records and the user's latest scroll without hiding cards",async()=>{
  const timers=new Map();let timerId=0;box.setTimeout=callback=>{timers.set(++timerId,callback);return timerId;};box.clearTimeout=id=>timers.delete(id);
  try{
    const dom=documentFixture(),current={...data(),inputs:[input()],tasks:[taskRow()],accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT",last_poll_at:"2024-04-01T12:00:00Z"},{ref:"watches/review",account:account().ref,monitoring:false,status:"PENDING_REVIEW_REQUIRED",pending_operation_id:"pending-kept"}]},calls=[],waiting=[];let background=false,detail=account();
    const request=async(route,payload)=>{calls.push({route,payload});if(background&&!payload)return new Promise(resolve=>waiting.push({route,resolve}));if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return copy(detail);assert.equal(payload.action,"stop_watch");current.watches[0].monitoring=false;return {ok:true,result:copy(current.watches[0])};};
    const app=ui.mount(dom.document,request,storage());await flush();app.switchView("continuous");await app.openAccount(account().ref);
    const stop=dom.button("stop-watch"),card=stop.closest("[data-watch-ref]"),select=card.querySelector("select"),record=card.querySelector("details"),pre=record.querySelector("pre"),reason=dom.document.querySelectorAll("[data-discard-reason]")[0],accountRecord=dom.document.querySelectorAll('[data-account-record="history"]')[0],history=accountRecord.querySelector("pre"),checkbox=dom.document.querySelectorAll("[data-advance-input]")[0],date=dom.get("advance-through");
    select.value=input().ref;record.open=true;pre.scrollTop=37;accountRecord.open=true;history.scrollTop=29;checkbox.checked=true;date.value="2024-04-02";stop.focus();dom.document.scrollingElement.scrollTop=740;
    for(const id of ["advance-card","account-detail-card","watch-card"])dom.get(id).hiddenHistory=[];
    const callback=timers.values().next().value;timers.clear();background=true;const poll=callback();await flush();assert.equal(waiting[0].route,"/api/state");
    for(const id of ["advance-card","account-detail-card","watch-card"])assert.equal(dom.get(id).hidden,false);
    reason.value="保留尚未提交的复核草稿";reason.selectionStart=2;reason.selectionEnd=5;reason.focus();dom.document.scrollingElement.scrollTop=918;
    current.watches[0].last_poll_at="2024-04-01T12:00:05Z";waiting[0].resolve(copy(current));await flush();assert.match(waiting[1].route,/^\/api\/account/);assert.equal(dom.document.activeElement,reason);
    detail={...detail,receipt_head:"new-head",equity:"10002",history:[{operation_id:"one-new-record"}],continuous:{...detail.continuous,last_session:"2024-04-02"}};waiting[1].resolve(copy(detail));await poll;
    assert.equal(dom.button("stop-watch"),stop);assert.equal(card.querySelector("select"),select);assert.equal(select.value,input().ref);assert.equal(card.querySelector("details"),record);assert.equal(record.open,true);assert.equal(record.querySelector("pre"),pre);assert.equal(pre.scrollTop,37);assert.equal(accountRecord.querySelector("pre"),history);assert.equal(history.scrollTop,29);assert.equal(accountRecord.open,true);assert.match(history.textContent,/one-new-record/);
    assert.equal(dom.document.activeElement,reason);assert.equal(reason.value,"保留尚未提交的复核草稿");assert.equal(reason.selectionStart,2);assert.equal(reason.selectionEnd,5);assert.equal(dom.document.querySelectorAll("[data-advance-input]")[0],checkbox);assert.equal(checkbox.checked,true);assert.equal(dom.get("advance-through"),date);assert.equal(date.value,"2024-04-02");assert.equal(dom.document.scrollingElement.scrollTop,918);assert.ok(["advance-card","account-detail-card","watch-card"].every(id=>dom.get(id).hiddenHistory.every(value=>value===false)));
    assert.match(card.querySelector('[data-watch-field="poll"]').textContent,/12:00:05/);assert.equal(calls.filter(row=>row.payload).length,0);
    background=false;await dom.click(stop);assert.equal(calls.filter(row=>row.payload?.action==="stop_watch").length,1);assert.equal(timers.size,0);
  }finally{delete box.setTimeout;delete box.clearTimeout;}
});

test("stopping observation invalidates an in-flight poll so an older monitoring state cannot come back",async()=>{
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT"}]},waiting=[];let hold=false;const calls=[];
  const app=ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state"&&hold){hold=false;return new Promise(resolve=>waiting.push(resolve));}if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return account();assert.equal(payload.action,"stop_watch");current.watches[0].monitoring=false;return {ok:true,result:copy(current.watches[0])};},storage());await flush();app.switchView("continuous");await app.openAccount(account().ref);
  hold=true;const stale=copy(current),poll=app.pollContinuous();await flush();await dom.click(dom.button("stop-watch"));assert.equal(app.controller.state.data.watches[0].monitoring,false);waiting[0](stale);await poll;
  assert.equal(app.controller.state.data.watches[0].monitoring,false);assert.equal(dom.button("stop-watch"),undefined);assert.ok(dom.button("start-watch"));assert.equal(calls.filter(row=>row.payload).length,1);
});

test("a stop awaiting its receipt cannot become an enabled start button after another status read",async()=>{
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT"}]};let finishStop;
  const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return account();assert.equal(payload.action,"stop_watch");return new Promise(resolve=>{finishStop=resolve;});},storage());await flush();app.switchView("continuous");await app.openAccount(account().ref);
  const control=dom.button("stop-watch"),stopping=dom.click(control);await flush();current.watches[0].monitoring=false;await app.controller.refresh({background:true});assert.equal(dom.button("start-watch"),control);assert.equal(control.disabled,true);
  finishStop({ok:true,result:current.watches[0]});await stopping;assert.equal(control.disabled,false);
});

test("a failed stop that cancels a manual refresh does not leave the refresh control permanently busy",async()=>{
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT"}]};let hold=false,finishRead;
  const app=ui.mount(dom.document,async(route,payload)=>{if(route==="/api/state"&&hold){hold=false;return new Promise(resolve=>{finishRead=resolve;});}if(route==="/api/state")return copy(current);if(route.startsWith("/api/account?"))return account();return {ok:false,error:"stop receipt not confirmed"};},storage());await flush();app.switchView("continuous");await app.openAccount(account().ref);
  hold=true;const refresh=app.controller.refresh();await flush();assert.equal(dom.get("refresh").disabled,true);await dom.click(dom.button("stop-watch"));assert.equal(app.controller.state.loading,false);assert.equal(dom.get("refresh").disabled,false);finishRead(copy(current));await refresh;assert.equal(dom.get("refresh").disabled,false);
});

test("background account failures retain confirmed records and stop controls but block dependent writes until verified",async()=>{
  const dom=documentFixture(),current={...data(),accounts:[account()],watches:[{ref:"watches/live",account:account().ref,monitoring:true,status:"CURRENT"}]};let failed=false;
  const app=ui.mount(dom.document,async route=>{if(route==="/api/state")return copy(current);if(failed)throw Error("read temporarily failed");return account();},storage());await flush();app.switchView("continuous");await app.openAccount(account().ref);const history=dom.document.querySelectorAll('[data-account-record="history"]')[0],stop=dom.button("stop-watch");history.open=true;
  failed=true;await app.pollContinuous();assert.equal(dom.document.querySelectorAll('[data-account-record="history"]')[0],history);assert.equal(history.open,true);assert.equal(dom.get("advance-card").hidden,false);assert.match(dom.get("account-read-state").textContent,/仍显示上次已核实状态/);assert.equal(dom.button("pause-account").disabled,true);assert.equal(dom.button("stop-watch"),stop);assert.equal(stop.disabled,false);
  failed=false;await app.pollContinuous();assert.equal(dom.button("pause-account").disabled,false);assert.match(dom.get("account-read-state").textContent,/当前状态已核实/);
});

test("late account reads from a background poll cannot overwrite a newly selected account",async()=>{
  const dom=documentFixture(),first=account(),second={...account(),ref:"continuous/account-b",title:"另一个组合"},current={...data(),accounts:[first,second],watches:[{ref:"watches/a",account:first.ref,monitoring:true,status:"CURRENT"}]};let hold=false,resolveOld;
  const app=ui.mount(dom.document,async route=>{if(route==="/api/state")return copy(current);if(route.includes(encodeURIComponent(first.ref))&&hold)return new Promise(resolve=>{resolveOld=resolve;});return route.includes(encodeURIComponent(second.ref))?second:first;},storage());await flush();app.switchView("continuous");await app.openAccount(first.ref);hold=true;const poll=app.pollContinuous();await flush();await app.openAccount(second.ref);const button=dom.button("pause-account");resolveOld({...first,title:"旧组合迟到结果"});await poll;
  assert.match(dom.get("account-summary").textContent,/另一个组合/);assert.doesNotMatch(dom.get("account-summary").textContent,/旧组合迟到结果/);assert.equal(dom.button("pause-account"),button);
});

test("stock update checks one selected imported snapshot only after an explicit submit",async()=>{
  const dom=documentFixture(),current={...data(),inputs:[input()],daily_updates:[],data_update_policy:{calendar_years:[2026],source:"Yahoo Finance",max_symbols:1,network:"EXPLICIT_CHECK_ONLY"}},calls=[];
  const update={ref:"daily-updates/check-a",symbol:"AAPL",status:"WAITING_SOURCE_UPDATE",reason:"SOURCE_MISSING_COMPLETED_SESSIONS:2026-10-22",baseline_snapshot_id:"old-a",baseline_start:"2026-09-16",baseline_end:"2026-10-21",checked_at:"2026-10-23T01:00:00Z",latest_completed_session:"2026-10-22",new_dates:[],revisions:[],candidate_snapshot_id:null,can_freeze:false};
  const app=ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);if(route.startsWith("/api/daily-update?"))return copy(update);assert.equal(payload.action,"check_stock_update");current.daily_updates=[update];current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:copy(update)};},storage());await flush();await app.controller.refresh();
  assert.equal(calls.filter(row=>row.payload).length,0);assert.match(dom.get("stock-update-policy").textContent,/每次检查 1 只，可逐只操作/);assert.match(dom.get("input-list").textContent,/AAPL/);
  dom.get("stock-update-snapshot").value=input().ref;await dom.submit("stock-update-form");
  assert.equal(calls.filter(row=>row.payload).length,1);assert.equal(calls.find(row=>row.payload).payload.snapshot,input().ref);assert.match(dom.get("daily-update-list").textContent,/公开来源尚缺最近一个完整交易日/);assert.doesNotMatch(dom.get("daily-update-list").textContent,/SOURCE_MISSING/);assert.match(dom.get("daily-update-detail").querySelector("dl").textContent,/2026-09-16 至 2026-10-21/);assert.match(dom.get("daily-update-detail").querySelector("dl").textContent,/2026-10-23T01:00:00Z/);assert.doesNotMatch(dom.get("daily-update-detail").querySelector("dl").textContent,/old-a/);assert.equal(dom.button("freeze-stock-update"),undefined);assert.equal(calls.some(row=>row.payload?.action==="run_task"),false);
});

test("historical revisions require an explicit acknowledgement before freezing a distinct input",async()=>{
  const dom=documentFixture(),original=input(),frozen={...input(),ref:"data/snapshots/new-a.json",coverage_end:"2026-10-22"},update={ref:"daily-updates/revised-a",symbol:"AAPL",status:"REVISION_REVIEW_REQUIRED",reason:"来源修订一项历史值",baseline_snapshot_id:"old-a",latest_completed_session:"2026-10-22",new_dates:["2026-10-22"],revisions:[{date:"2026-10-21",field:"volume",old_value:100,new_value:110}],candidate_snapshot_id:"candidate-a",can_freeze:true,frozen:false},current={...data(),inputs:[original],daily_updates:[update]},calls=[];
  ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);if(route.startsWith("/api/daily-update?"))return copy(update);assert.equal(payload.action,"freeze_stock_update");current.inputs.push(frozen);update.frozen=true;update.frozen_input_ref=frozen.ref;current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:{ref:frozen.ref,status:"DAILY_UPDATE_FROZEN"}};},storage());await flush();
  await dom.click(dom.button("daily-update-detail",update.ref));assert.match(dom.get("daily-update-detail").textContent,/2026-10-21/);assert.match(dom.get("daily-update-detail").textContent,/110/);assert.match(dom.get("daily-update-detail").textContent,/原文件精度/);assert.equal(dom.button("freeze-stock-update").disabled,true);
  await dom.click(dom.button("freeze-stock-update"));assert.equal(calls.filter(row=>row.payload).length,0);
  const acknowledgement=dom.document.querySelectorAll("[data-ack-update-revisions]")[0];acknowledgement.checked=true;dom.listeners.change({target:acknowledgement});assert.equal(dom.button("freeze-stock-update").disabled,false);await dom.click(dom.button("freeze-stock-update"));
  const write=calls.find(row=>row.payload?.action==="freeze_stock_update").payload;assert.equal(write.update,update.ref);assert.equal(write.acknowledge_revisions,true);assert.equal(current.inputs[0].ref,original.ref);assert.match(dom.get("daily-update-detail").textContent,/已冻结新输入/);assert.equal(calls.some(row=>row.payload?.action==="run_task"),false);
});

test("updating a task binds the selected frozen input to the current task identity without running it",async()=>{
  const dom=documentFixture(),oldTask={...taskRow(),task_id:"task-original"},newInput={...input(),ref:"data/snapshots/new-a.json",coverage_end:"2026-10-22"},current={...data(),inputs:[input(),newInput],tasks:[oldTask],runs:[{...run().view,ref:run().ref}]},calls=[];
  ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);assert.equal(payload.action,"bind_task_input");current.tasks=[{...oldTask,task_id:"task-next",inputs:{snapshot:newInput}}];current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:{...current.tasks[0],input_update_status:"NEW_IMMUTABLE_VERSION"}};},storage());await flush();
  dom.get("bind-task").value=oldTask.ref;dom.get("bind-snapshot").value=newInput.ref;dom.get("bind-score-end").value="2026-10-22";await dom.submit("bind-task-input-form");
  const actions=calls.filter(row=>row.payload).map(row=>row.payload);assert.equal(actions.length,1);assert.equal(actions[0].action,"bind_task_input");assert.equal(actions[0].task,oldTask.ref);assert.equal(actions[0].snapshot,newInput.ref);assert.equal(actions[0].score_end,"2026-10-22");assert.equal(actions[0].expected_task_id,"task-original");assert.equal(current.runs.length,1);assert.match(dom.get("status").textContent,/尚未自动运行/);
});

test("saved run diagnostics and cost validation stay read-only until the explicit validation action",async()=>{
  const dom=documentFixture(),savedRun={...run(),view:{...run().view,run_id:"run-a"},diagnostics:{status:"SAVED_DESCRIPTIVE_DIAGNOSTICS",sample:{scored_sessions:16,return_observations:16,completed_round_trips:0,fill_count:0,available_context_sessions:60,required_context_sessions:61},statistical_status:{status:"INSUFFICIENT_EVIDENCE",annualized_return:"SHORT_SAMPLE"},accounting:{round_trip_count:0},risk_semantics:{status:"DESCRIPTIVE_ONLY"}}},followupInput={...input(),ref:"data/snapshots/followup.json",coverage_start:"2025-01-02",coverage_end:"2025-02-28"},current={...data(),inputs:[input(),followupInput],runs:[{...run().view,ref:run().ref}],validations:[]},calls=[];
  const summary={total_return:.03,max_drawdown:.02,total_fees:4,fill_count:1};const validation={ref:"validations/val-a",status:"COMPLETED_WITH_STOPPED_SCENARIOS",validation_hash:"hash-a",base:{run_id:"run-a",symbol:"AAPL",spec:{fee_rate:.001,slippage_pct:.0005}},cost_scenarios:[{multiplier:1,fee_rate:.001,slippage_pct:.0005,status:"REUSED_SAVED_RESULT",summary},{multiplier:2,fee_rate:.002,slippage_pct:.001,status:"COMPLETED",summary:{...summary,total_return:.02}},{multiplier:3,fee_rate:.003,slippage_pct:.0015,status:"STOPPED",reason:"source identity mismatch",summary:null}],benchmarks:[{benchmark:"cash",title:"现金基准",status:"COMPLETED",summary:{...summary,total_return:0,fill_count:0}},{benchmark:"buy_and_hold",title:"100%买入持有基准",status:"STOPPED",reason:"insufficient data",summary:null}],followup:{status:"NOT_RUN",reason:"NO_EXPLICIT_FOLLOWUP_INTERVAL",summary:null}};
  const app=ui.mount(dom.document,async(route,payload)=>{calls.push({route,payload});if(route==="/api/state")return copy(current);if(route.startsWith("/api/run?"))return copy(savedRun);if(route.startsWith("/api/validation?"))return copy(validation);assert.equal(payload.action,"validate_run");current.validations=[{ref:validation.ref,base:validation.base,status:validation.status,validation_hash:validation.validation_hash}];current.operations.push({operation_id:payload.operation_id,status:"COMMITTED",ok:true});return {ok:true,result:{...validation,action_new_economic_runs:4,reused_saved_validation:false}};},storage());await flush();await dom.click(dom.button("run-detail",run().ref));
  assert.equal(calls.filter(row=>row.payload).length,0);assert.match(dom.get("run-detail").textContent,/已计分交易日/);assert.match(dom.get("run-detail").textContent,/本段没有模拟成交/);assert.match(dom.get("run-detail").textContent,/样本不足/);await dom.click(dom.button("validate-run",run().ref));
  const writes=calls.filter(row=>row.payload);assert.equal(writes.length,1);assert.equal(writes[0].payload.action,"validate_run");assert.equal(writes[0].payload.run,run().ref);assert.equal(writes[0].payload.followup_snapshot,undefined);assert.match(dom.get("validation-detail").textContent,/未运行/);assert.match(dom.get("validation-detail").innerHTML,/现金基准<\/td><td>0.1%<\/td><td>0.05%/);assert.match(dom.get("validation-detail").textContent,/source identity mismatch/);assert.doesNotMatch(dom.get("validation-detail").textContent,/PASS/);assert.match(dom.get("validation-list").textContent,/AAPL/);
  assert.equal(dom.button("validate-run",run().ref),undefined);assert.ok(dom.button("validation-detail",validation.ref));await app.controller.refresh();await dom.click(dom.button("validation-detail",validation.ref));assert.equal(calls.filter(row=>row.payload).length,1);
  dom.get("validation-followup-snapshot").value=followupInput.ref;dom.get("validation-followup-start").value="2025-01-02";dom.get("validation-followup-end").value="2025-02-28";await dom.click(dom.button("validate-run-followup",run().ref));
  const followupWrite=calls.filter(row=>row.payload)[1].payload;assert.equal(followupWrite.action,"validate_run");assert.equal(followupWrite.run,run().ref);assert.equal(followupWrite.followup_snapshot,followupInput.ref);assert.equal(followupWrite.followup_start,"2025-01-02");assert.equal(followupWrite.followup_end,"2025-02-28");
});
