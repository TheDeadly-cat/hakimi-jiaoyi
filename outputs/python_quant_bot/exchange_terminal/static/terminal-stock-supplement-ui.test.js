"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),{createHash}=require("node:crypto"),fs=require("node:fs"),path=require("node:path");
const ui=require("./terminal-stock-supplement-ui"),copy=v=>JSON.parse(JSON.stringify(v)),hash=v=>createHash("sha256").update(ui.canonical(v)).digest("hex");
const cid=letter=>"canon-"+letter.repeat(32),sid=letter=>"supplement-"+letter.repeat(64),schema="terminal-stock-supplement-view-v2";
const permissions={research_only:true,order_allowed:false,live_allowed:false,paper_allowed:false};
const security={security_id:"retained:QA:ORIGINAL",symbol:"NDAQ",exchange:"XNAS",currency:"USD",instrument_type:"COMMON_STOCK"};
const original=(letter="a")=>({id:cid(letter),check_hash:letter.repeat(64),status:"BLOCKED",reason:"SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN",can_save:false,security:copy(security),coverage_start:"2026-07-01",coverage_end:"2026-10-28"});
const base=context=>({schema_version:schema,original_intake_id:context.id,original_check_hash:context.check_hash,security:copy(context.security),window:{start:context.coverage_start,end:context.coverage_end},permissions:copy(permissions),source_truth_verified:false});
const requirements=context=>({...base(context),supported_formats:[{id:"futu-retained-sdk-v1",title:"本机富途原件",required_artifacts:ui.keys.map(key=>({key,title:key,filename:key+".json"}))}],limits:{file_bytes:1048576,total_bytes:4194304},read_only:true});
const input=context=>({id:cid("f"),record_namespace:"canonical-daily-v1",record_resource:"terminal_daily_inputs",kind:"PRICE_SNAPSHOT",status:"READY",security:copy(context.security),coverage_start:context.coverage_start,coverage_end:context.coverage_end,permissions:copy(permissions)});
const view=(context=original(),status="REVIEW_REQUIRED")=>({...base(context),id:sid("c"),status,can_save:status==="REVIEW_REQUIRED",check_hash:"d".repeat(64),reason:status==="REVIEW_REQUIRED"?"SOURCE_LIMITS_CONFIRMATION_REQUIRED":"FUTU_SECURITY_MISMATCH",diagnostic:{summary:status==="REVIEW_REQUIRED"?"已核对保留原件，仍需确认来源限制。":"证券身份与原检查不一致。",action:"核对原件，不改写原检查。",details:{source_completeness:"UNKNOWN",source_as_of:"UNKNOWN"}},times:{original_price_retrieved_at:"2026-10-29T02:00:00Z",supplement_checked_at:"2026-10-30T02:00:00Z"},saved_input_id:null});
function fixture(options={}){
  const reads=[],writes=[],requests=new Map(),rows=new Map(),inputs=[];let sequence=0;const contexts=new Map([[cid("a"),original()],[cid("b"),original("b")]]);
  const api=async resource=>{reads.push(resource);if(options.read){const result=await options.read(resource);if(result!==undefined)return result;}
    const [name,id]=resource.split("/");
    if(name==="terminal_daily_supplement_context")return requirements(contexts.get(id));
    if(name==="terminal_daily_supplements")return id?copy(rows.get(id)):{items:[...rows.values()].map(copy)};
    if(name==="terminal_daily_supplement_requests")return copy(requests.get(id)||{operation_id:id,status:"NOT_RECORDED",action:null,request_hash:null,result:null});
    throw Error("Unexpected read "+resource);
  };
  const perform=async(action,payload,callbacks)=>{writes.push({action,payload:copy(payload)});let result;
    if(action==="terminal_daily_check_supplement")result=view(contexts.get(payload.intake_id),options.blocked?"BLOCKED":"REVIEW_REQUIRED");
    else if(action==="terminal_daily_save_supplement"){const old=rows.get(payload.supplement_id),context=contexts.get(old.original_intake_id);result={...copy(old),saved_input_id:cid("f"),saved_input:input(context)};}
    else throw Error("Unexpected write "+action);
    rows.set(result.id,copy(result));requests.set(payload.operation_id,{operation_id:payload.operation_id,status:"COMPLETED",action,request_hash:hash({action,payload}),result:copy(result)});
    if(options.perform)return options.perform(action,payload,callbacks,result);
    await callbacks.onSuccess(result);return result;
  };
  const c=ui.createController({api,perform,uuid:()=>"supplement-operation-"+(++sequence),onInputSaved:async value=>{inputs.push(copy(value));if(options.onInputSaved)return options.onInputSaved(value);},changed:options.changed||(()=>{})});c.setContext(original());
  return {c,api,perform,reads,writes,requests,rows,inputs,contexts};
}
async function loaded(f=fixture()){await f.c.readContext();for(const key of ui.keys)f.c.setArtifact(key,{name:key+".json",bytes:new TextEncoder().encode('{"已保存原件":"'+key+'"}\r\n')});return f;}
async function checked(f=fixture()){await loaded(f);await f.c.check();return f;}

test("installation and context changes are inert; explicit views only read without changing original",async()=>{
  const f=fixture(),before=copy(original());assert.deepEqual(f.reads,[]);f.c.setContext(original("b"));assert.deepEqual(f.reads,[]);await f.c.readContext();await f.c.readList();assert.equal(f.writes.length,0);assert.deepEqual(f.contexts.get(cid("a")),before);f.c.setContext({...original(),reason:"OTHER"});assert.equal(f.c.state.context,null);
});
test("four original JSON bytes are submitted exactly once with original identity and no provider permission request",async()=>{
  const f=await loaded();await f.c.check();assert.equal(f.writes.length,1);const p=f.writes[0].payload;assert.deepEqual(Object.keys(p).sort(),["operation_id","intake_id","expected_check_hash","source_format","artifacts"].sort());assert.deepEqual(Object.keys(p.artifacts).sort(),[...ui.keys].sort());
  for(const key of ui.keys)assert.equal(Buffer.from(p.artifacts[key],"base64").toString(),'{"已保存原件":"'+key+'"}\r\n');assert.equal(p.intake_id,cid("a"));assert.equal(p.source_format,"futu-retained-sdk-v1");assert.equal(f.c.state.selected.status,"REVIEW_REQUIRED");assert.equal(f.inputs.length,0);assert.equal(f.reads.some(r=>/allow-once|futu|market/.test(r)),false);
});
test("missing originals, invalid extensions, empty and oversize files cannot submit",async()=>{
  const f=fixture();await assert.rejects(()=>f.c.check(),/要求/);await f.c.readContext();await assert.rejects(()=>f.c.check(),/四份/);
  for(const file of [{name:"a.txt",bytes:new Uint8Array([1])},{name:"a.json",bytes:new Uint8Array()},{name:"a.json",bytes:new Uint8Array(1048577)}])assert.throws(()=>f.c.setArtifact(ui.keys[0],file));
  f.c.state.requirements.limits.total_bytes=3;f.c.setArtifact(ui.keys[0],{name:"a.json",bytes:new Uint8Array([1,2])});assert.throws(()=>f.c.setArtifact(ui.keys[1],{name:"b.json",bytes:new Uint8Array([3,4])}),/合计/);assert.equal(f.writes.length,0);
});
test("unsupported reader capability is unavailable rather than a fake accepted format",async()=>{
  const f=fixture({read:r=>r.startsWith("terminal_daily_supplement_context")?{...requirements(original()),supported_formats:[]}:undefined});await f.c.readContext();assert.equal(f.c.state.requirements.supported_formats.length,0);await assert.rejects(()=>f.c.check(),/要求/);assert.equal(f.writes.length,0);
});
test("blocked source retains specific diagnostic and cannot create an input",async()=>{
  const f=await checked(fixture({blocked:true}));assert.equal(f.c.state.selected.status,"BLOCKED");assert.match(f.c.state.selected.diagnostic.summary,/证券身份/);f.c.setConfirmation(true);assert.equal(f.c.state.confirmed,false);await assert.rejects(()=>f.c.save(),/限制/);assert.equal(f.inputs.length,0);assert.equal(f.writes.length,1);
});
test("save separately requires acknowledgment and exact reviewed security/hash; it only selects a saved canonical input",async()=>{
  const f=await checked();await assert.rejects(()=>f.c.save(),/明确承认/);f.c.setConfirmation(true);await f.c.save();assert.equal(f.writes.length,2);const p=f.writes[1].payload;assert.deepEqual(Object.keys(p).sort(),["operation_id","supplement_id","expected_check_hash","confirmed_security","acknowledge_source_limits"].sort());assert.deepEqual(p.confirmed_security,security);assert.equal(p.acknowledge_source_limits,true);assert.equal(p.expected_check_hash,"d".repeat(64));assert.equal(f.inputs.length,1);assert.equal(f.inputs[0].id,cid("f"));assert.equal(f.contexts.get(cid("a")).status,"BLOCKED");await assert.rejects(()=>f.c.save(),/限制/);assert.equal(f.writes.length,2);
});
test("changing any file or rereading requirements revokes save confirmation",async()=>{
  const f=await checked();f.c.setConfirmation(true);await f.c.readContext();assert.equal(f.c.state.confirmed,false);f.c.setConfirmation(true);f.c.clearArtifact(ui.keys[0]);assert.equal(f.c.state.selected,null);assert.equal(f.c.state.confirmed,false);await assert.rejects(()=>f.c.save(),/限制/);
});

test("explicit saved-input selection can be repeated while duplicate completion callbacks remain inert",async()=>{
  const f=await checked(fixture({perform:async(_action,_payload,callbacks,result)=>{await callbacks.onSuccess(result);await callbacks.onSuccess(result);return result;}}));
  f.c.setConfirmation(true);await f.c.save();assert.equal(f.inputs.length,1);assert.equal(f.writes.length,2);
  f.c.setContext(original("b"));await f.c.selectSaved();await f.c.selectSaved();
  assert.equal(f.inputs.length,3);assert.ok(f.inputs.every(value=>value.id===cid("f")));
  assert.equal(f.writes.length,2,"selecting an existing input cannot resave, import, create a task, or run research");
});
test("lost check response keeps immutable original operation; queries never resubmit",async()=>{
  const f=await loaded(fixture({perform:()=>null}));await f.c.check();const p=copy(f.c.state.pending);await assert.rejects(()=>f.c.check(),/原请求/);f.requests.clear();await f.c.queryPending();assert.match(f.c.state.error,/不代表未处理/);assert.equal(f.c.state.pending.payload.operation_id,p.payload.operation_id);
  f.requests.set(p.payload.operation_id,{operation_id:p.payload.operation_id,status:"PENDING",action:p.action,request_hash:p.request_hash,result:null});await f.c.queryPending();assert.ok(f.c.state.pending);
  f.requests.set(p.payload.operation_id,{operation_id:p.payload.operation_id,status:"COMPLETED",action:p.action,request_hash:p.request_hash,result:view()});await f.c.queryPending();assert.equal(f.c.state.pending,null);assert.equal(f.writes.length,1);
});
test("switched original and late save preserve old saved fact without changing new selection or auto importing",async()=>{
  let release;const f=await checked(fixture({perform:async(action,_p,callbacks,result)=>{if(action.endsWith("save_supplement"))return new Promise(resolve=>release=()=>resolve(result));await callbacks.onSuccess(result);return result;}}));f.c.setConfirmation(true);const saving=f.c.save();while(!release)await new Promise(resolve=>setImmediate(resolve));f.c.setContext(original("b"));release();await saving;
  assert.equal(f.c.state.context.id,cid("b"));assert.equal(f.c.state.selected,null);assert.equal(f.c.state.fact.context.id,cid("a"));assert.equal(f.inputs.length,0);await f.c.selectSaved();assert.equal(f.inputs.length,1);assert.equal(f.writes.length,2);
});
test("query after context switch retains original operation scope and rejects foreign completed receipts",async()=>{
  const f=await loaded(fixture({perform:()=>null}));await f.c.check();const op=copy(f.c.state.pending),receipt=f.requests.get(op.payload.operation_id);f.c.setContext(original("b"));receipt.request_hash="0".repeat(64);await f.c.queryPending();assert.ok(f.c.state.pending);receipt.request_hash=op.request_hash;receipt.result=view(original("b"));await f.c.queryPending();assert.ok(f.c.state.pending);receipt.result=view();await f.c.queryPending();assert.equal(f.c.state.pending,null);assert.equal(f.c.state.selected,null);assert.equal(f.c.state.fact.context.id,cid("a"));assert.ok(f.reads.at(-1).endsWith(op.payload.operation_id));assert.equal(f.writes.length,1);
});
test("stale context/details reads never overwrite another original",async()=>{
  let release;const f=fixture({read:r=>r.startsWith("terminal_daily_supplement_context")?new Promise(resolve=>release=()=>resolve(requirements(original()))):undefined});const reading=f.c.readContext();f.c.setContext(original("b"));release();await reading;assert.equal(f.c.state.requirements,null);
  const g=fixture({read:r=>r.startsWith("terminal_daily_supplements/")?new Promise(resolve=>release=()=>resolve(view())):undefined});const detail=g.c.openRecord(sid("c"));g.c.setContext(original("b"));release();await detail;assert.equal(g.c.state.selected,null);
});
test("unsafe permissions, wrong security, window or saved input cannot be accepted",async()=>{
  for(const alter of [v=>v.permissions.live_allowed=true,v=>v.security.symbol="OTHER",v=>v.window.end="2026-10-29",v=>v.source_truth_verified=true]){const f=await loaded(fixture({perform:(_a,_p,_c,result)=>{alter(result);return result;}}));await f.c.check();assert.ok(f.c.state.pending);assert.equal(f.c.state.fact,null);}
  const f=await checked(fixture({perform:async(action,_p,callbacks,result)=>{if(action.endsWith("save_supplement"))result.saved_input.security.symbol="OTHER";await callbacks.onSuccess(result);return result;}}));f.c.setConfirmation(true);await f.c.save();assert.ok(f.c.state.pending);assert.equal(f.inputs.length,0);
});
test("durable save fact survives after-callback failure and parent selection failure",async()=>{
  const f=await checked(fixture({perform:async(action,_p,callbacks,result)=>{await callbacks.onSuccess(result);if(action.endsWith("save_supplement"))throw Error("aux refresh failed");return result;}}));f.c.setConfirmation(true);await f.c.save();assert.equal(f.c.state.pending,null);assert.equal(f.c.state.fact.view.saved_input_id,cid("f"));assert.match(f.c.state.readError,/保存事实已确认/);assert.equal(f.inputs.length,1);
  const g=await checked(fixture({onInputSaved:()=>{throw Error("parent view failed");}}));g.c.setConfirmation(true);await g.c.save();assert.equal(g.c.state.pending,null);assert.equal(g.c.state.fact.view.saved_input_id,cid("f"));assert.match(g.c.state.readError,/新输入已保存/);
});
test("list failure retains saved fact; opening saved detail does not select input or run anything",async()=>{
  let fail=false;const f=await checked(fixture({read:r=>{if(fail&&r==="terminal_daily_supplements")throw Error("offline read");}}));f.c.setConfirmation(true);await f.c.save();const fact=copy(f.c.state.fact);fail=true;await f.c.readList();assert.deepEqual(f.c.state.fact,fact);assert.match(f.c.state.readError,/仍保留/);await f.c.openRecord(sid("c"));assert.equal(f.inputs.length,1);assert.equal(f.writes.length,2);
});
test("receipt hash matches backend ASCII canonical serialization",()=>{
  assert.equal(ui.canonical({reason:"补证🙂",a:true}),'{"a":true,"reason":"\\u8865\\u8bc1\\ud83d\\ude42"}');
});
test("missing or malformed original context cannot produce an upload scope",()=>{
  const f=fixture();for(const value of [null,{...original(),security:null},{...original(),coverage_end:null},{...original(),status:"REVIEW_REQUIRED"}]){f.c.setContext(value);assert.equal(f.c.state.context,null);}assert.equal(f.writes.length,0);
});

test("rendered same-window supplement uploads four files, shows insufficiency, saves explicitly, and reopens read-only at desktop/mobile",async t=>{
  const {chromium}=require("playwright"),executablePath=[process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,chromium.executablePath(),
    "C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(value=>value&&fs.existsSync(value));
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),args:["--disable-background-networking","--no-first-run"]});t.after(()=>browser.close());
  const source=fs.readFileSync(require.resolve("./terminal-stock-supplement-ui"),"utf8");
  for(const width of [1440,390]){const f=fixture({blocked:width===390}),page=await browser.newPage({viewport:{width,height:1000}}),errors=[],external=[];page.on("pageerror",e=>errors.push(e.message));page.on("console",m=>{if(["error","warning"].includes(m.type()))errors.push(m.text());});page.on("websocket",w=>external.push(w.url()));
    await page.route("**/*",route=>{if(route.request().url()==="http://127.0.0.1:55325/")return route.fulfill({contentType:"text/html",body:'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>本机补证 · 隔离测试</title><style>body{font:16px/1.6 system-ui;margin:20px;background:#f3f5f8;color:#152033}main{max-width:1100px;margin:auto;background:white;padding:16px}button,input{font:inherit;box-sizing:border-box;max-width:100%}button{padding:8px 12px}label{display:block}.notice{padding:12px;background:#edf4ff;margin-top:16px}[hidden]{display:none!important}</style><main id="host"></main></html>'});external.push(route.request().url());return route.abort();});
    await page.goto("http://127.0.0.1:55325/");await page.exposeFunction("readFixture",f.api);await page.exposeFunction("performFixture",async(action,payload)=>f.perform(action,payload,{onSuccess:()=>{}}));await page.exposeFunction("inputSavedFixture",input=>f.inputs.push(copy(input)));await page.addScriptTag({content:source});await page.evaluate(context=>{window.ui=installTerminalStockSupplementUI({host:document.querySelector("#host"),api:readFixture,perform:performFixture,onInputSaved:async input=>{await inputSavedFixture(input);window.savedSelectionCount=(window.savedSelectionCount||0)+1;}});ui.setContext(context);},original());
    assert.equal(await page.title(),"本机补证 · 隔离测试");assert.equal(await page.getByRole("heading",{name:"补充本机已有来源原件"}).count(),1);assert.equal(f.reads.length,0);await page.getByRole("button",{name:"读取补证要求",exact:true}).click();await page.waitForFunction(()=>ui.controller.state.requirements);
    for(const key of ui.keys)await page.locator('[data-supplement-file="'+key+'"]').setInputFiles({name:key+".json",mimeType:"application/json",buffer:Buffer.from('{"保留原件":"'+key+'"}\r\n')});await page.getByRole("button",{name:"检查这四份补充原件",exact:true}).click();await page.waitForFunction(()=>ui.controller.state.selected&&!ui.controller.state.busy);
    assert.equal(f.writes.length,1);assert.match(await page.locator('[data-supplement-role="detail"]').innerText(),/来源完整性与截至时点仍未知/);assert.equal(f.inputs.length,0);
    if(width===1440){assert.equal(await page.getByRole("button",{name:"确认限制并另存新输入",exact:true}).isDisabled(),true);await page.locator('[data-supplement-confirm]').check();await page.getByRole("button",{name:"确认限制并另存新输入",exact:true}).click();await page.waitForFunction(()=>ui.controller.state.fact?.view.saved_input_id&&!ui.controller.state.busy);assert.equal(f.inputs.length,1);assert.equal(f.writes.length,2);
      await page.getByRole("button",{name:"选用这份已保存行情",exact:true}).click();await page.waitForFunction(()=>window.savedSelectionCount===2);
      await page.getByRole("button",{name:"读取已有补证记录",exact:true}).click();await page.locator('[data-supplement-open]').click();await page.waitForFunction(()=>ui.controller.state.selected?.saved_input_id);assert.equal(f.inputs.length,2);assert.equal(f.writes.length,2);assert.match(await page.locator('[data-supplement-role="fact"]').innerText(),/新输入已保存/);
    }else{assert.match(await page.locator('[data-supplement-role="detail"]').innerText(),/证券身份与原检查不一致/);assert.equal(await page.getByRole("button",{name:"确认限制并另存新输入",exact:true}).isVisible(),false);}
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);const heights=await page.locator('button').evaluateAll(nodes=>nodes.filter(n=>n.offsetParent).map(n=>n.getBoundingClientRect().height));assert.ok(heights.every(h=>h>=44));
    assert.ok((await page.locator('input[type=file]').evaluateAll(nodes=>nodes.map(n=>parseFloat(getComputedStyle(n,'::file-selector-button').minHeight)))).every(height=>height>=44));assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    if(process.env.STOCK_SUPPLEMENT_EVIDENCE_DIR){await page.locator('[data-supplement-role="detail"]').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.STOCK_SUPPLEMENT_EVIDENCE_DIR,'supplement-'+width+'.png'),fullPage:true});}await page.close();
  }
});
