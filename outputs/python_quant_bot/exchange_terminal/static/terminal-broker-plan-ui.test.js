"use strict";
// Explicit synthetic mock-backend contracts. No package, account, SDK or order
// is inspected or executed; this file exercises the real UI state machine.
const test=require('node:test'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const ui=require('./terminal-broker-plan-ui');
const copy=v=>JSON.parse(JSON.stringify(v)),hash=v=>createHash('sha256').update(ui.canonical(v)).digest('hex');
const seal=value=>({...copy(value),id:hash(value)}),SIM='OFFICIAL_SIMULATION',REAL='LIVE_CANDIDATE',NOW=Date.parse('2026-10-30T08:00:00Z');
const permissions=Object.fromEntries(ui.permissionKeys.map(key=>[key,false]));
const candidatePermissions={external_connection_allowed:false,submit_allowed:false,query_allowed:false,cancel_allowed:false,unlock_allowed:false,adapter_installed:false,automatic_resume:false,automatic_retry:false};
const workspace='a'.repeat(64),ACTION='terminal_broker_prepare_plan';
function candidate(mode=SIM){const terms={account_id:'900000000000001',market:'US',asset_class:'EQUITY',asset_code:'US.FICTION',currency:'USD',max_quantity:2,max_notional:'100',side:'BUY',quantity:1,limit_price:'20',time_in_force:'DAY',expires_at:new Date(NOW+3600000).toISOString()};
  const config_id='c'.repeat(64),intent=seal({schema_version:'hakimi-broker-candidate-v2',kind:'intents',mode,config_id,request_id:'synthetic-intent-0001',research_sha256:'b'.repeat(64),terms,security_binding:{status:'MATCHED_SAVED_DECLARATION'},status:'UNSENT_OFFLINE_PREVIEW',permissions:copy(candidatePermissions)});
  return {mode,config_id,intent,candidate_terms:copy(terms),expected_control_revision:0,blocked:false};}
const form=()=>({...ui.defaults,valid_until:new Date(NOW+900000).toISOString(),max_total_fees:'2.00'});
function fixture(options={}){
  const reads=[],writes=[],records=new Map(),plans=new Map();let seq=0,capStatus='PACKAGED_IDENTITY_MATCHED';
  const base=(mode,data)=>({schema_version:'hakimi-broker-plan-service-v1',workspace_context:workspace,mode,...copy(data),permissions:copy(permissions),automatic_retry:false});
  function capabilities(mode){return base(mode,{status:capStatus,read_only:true,runtime:{schema_version:'hakimi-broker-package-load-v1',status:capStatus,mode,package:capStatus==='NOT_PACKAGED'?null:{bundle_id:'d'.repeat(64)},sdk:null,adapter:null,missing_capabilities:capStatus==='NOT_PACKAGED'?['PACKAGE_NOT_ANCHORED']:['SDK_NOT_PACKAGED','APPLICATION_ADAPTER_NOT_PACKAGED'],runtime_compatibility:'NOT_VERIFIED',identity_match_only:true,permissions:copy(permissions)}});}
  function record(payload,{preparing=false,refused=false}={}){
    const request_hash=hash({action:ACTION,payload}),claim=seal({schema_version:'hakimi-broker-plan-claim-v1',action:ACTION,mode:payload.mode,workspace_context:workspace,request_id:payload.request_id,request_hash,payload:copy(payload),created_at:new Date(NOW).toISOString(),permissions:copy(permissions)});
    const plan=refused?null:seal({schema_version:'hakimi-broker-execution-plan-v1',status:'BLOCKED_CAPABILITY',mode:payload.mode,created_at:new Date(NOW).toISOString(),candidate_config:{id:payload.config_id},candidate_intent:{id:payload.intent_id},order:candidate(payload.mode).intent.terms,bounds:copy(payload.bounds),research_eligibility:{offline_only:true,external_research_eligible:false,admission_cannot_override_synthetic:true},capability_gaps:['APPLICATION_ADAPTER_NOT_PACKAGED'],missing_evidence:[],permissions:copy(permissions)});
    const result={mode:payload.mode,request_id:payload.request_id,config_id:payload.config_id,intent_id:payload.intent_id,status:refused?'PLAN_NOT_CREATED':'PLAN_SAVED',plan_id:plan?.id||null,plan_status:plan?.status||null,reason:refused?'NOT_PACKAGED':null,permissions:copy(permissions)};
    const receipt=preparing?null:seal({schema_version:'hakimi-broker-plan-receipt-v1',action:ACTION,mode:payload.mode,workspace_context:workspace,request_id:payload.request_id,request_hash,payload:copy(payload),claim_id:claim.id,created_at:new Date(NOW).toISOString(),result,permissions:copy(permissions)});
    const row={claim,receipt,plan:preparing?null:plan};records.set(payload.mode+':'+payload.request_id,row);if(!preparing&&plan)plans.set(plan.id,plan);return row;
  }
  function outcome(row,mutation=false){return base(row.claim.mode,{status:row.receipt?(mutation?row.receipt.result.status:'FOUND'):'PREPARING_UNCONFIRMED',request_id:row.claim.request_id,result:row.receipt?.result||null,claim:row.claim,receipt:row.receipt,retry_allowed:false,read_only:!mutation});}
  const api=async resource=>{reads.push(resource);if(options.read){const found=await options.read(resource);if(found!==undefined)return found;}
    const [name,encoded]=resource.split('/'),p=JSON.parse(decodeURIComponent(encoded));
    if(name==='terminal_broker_plan_capabilities')return capabilities(p.mode);
    if(name==='terminal_broker_plans'){const rows=[...records.values()].filter(row=>row.claim.mode===p.mode);return base(p.mode,{read_only:true,retry_allowed:false,items:rows.filter(row=>row.plan).map(({claim,plan})=>({plan_id:plan.id,config_id:claim.payload.config_id,intent_id:claim.payload.intent_id,status:plan.status,created_at:claim.created_at,account_id:plan.order.account_id,symbol:'FICTION',strategy_id:'dual_ma',task_version:1,research_eligibility:plan.research_eligibility})),requests:rows.map(({claim,receipt,plan})=>({request_id:claim.request_id,request_hash:claim.request_hash,state:receipt?(plan?'COMPLETED':'REFUSED'):'PREPARING',status:receipt?.result.status||'PREPARING_UNCONFIRMED',plan_id:plan?.id||null,config_id:claim.payload.config_id,intent_id:claim.payload.intent_id,created_at:claim.created_at,reason:receipt?.result.reason||null}))});}
    if(name==='terminal_broker_plan_receipt'){const row=records.get(p.mode+':'+p.request_id);return row?outcome(row):base(p.mode,{status:'NOT_RECORDED',request_id:p.request_id,result:null,claim:null,receipt:null,retry_allowed:false,read_only:true});}
    if(name==='terminal_broker_plan'){const plan=plans.get(p.plan_id)||null;return base(p.mode,{status:plan?'FOUND':'NOT_RECORDED',plan,read_only:true,retry_allowed:false});}
    throw Error('Unexpected mock read '+resource);
  };
  const perform=async(action,payload,callbacks)=>{writes.push({action,payload:copy(payload)});assert.equal(action,ACTION);const row=record(payload,{preparing:options.preparing,refused:options.refused});
    if(options.drop)return null;let value=outcome(row,true);if(options.alter)value=options.alter(copy(value));await callbacks.onSuccess(value);if(options.afterSuccess)throw Error('shell refresh failed after acknowledgement');return value;};
  const c=ui.createController({api,perform,uuid:()=>`fixture-${++seq}`,now:()=>NOW,changed:options.changed||(()=>{})});c.setContext(candidate());
  return {c,api,perform,reads,writes,records,plans,base,record,outcome,capabilities,setCap:value=>{capStatus=value;}};
}
async function ready(f){await f.c.readCapabilities();f.c.setForm(form());f.c.setConfirmation(true);return f;}

test('installation state and context changes do not read, select a mode or write a plan automatically',()=>{
  const f=fixture();assert.equal(f.reads.length,0);assert.equal(f.writes.length,0);assert.equal(f.c.state.confirmed,false);assert.equal(f.c.state.form.valid_until,'');assert.equal(f.c.state.form.max_total_fees,'');
  f.c.setContext(candidate(REAL));assert.equal(f.reads.length,0);assert.equal(f.writes.length,0);
});
test('bounds require explicit deadline and fee ceiling and carry all visible finite defaults',()=>{
  const b=ui.boundsFromForm(form(),candidate().intent.terms.expires_at,NOW);assert.equal(b.max_total_fees,'2.00');assert.equal(b.max_output_bytes,131072);assert.equal(b.endpoint.host,'127.0.0.1');assert.equal(b.endpoint.port,11111);assert.equal(b.calls.unlock,0);assert.equal(b.calls.submit,1);
  assert.equal(ui.boundsFromForm({...form(),max_total_fees:'0'},candidate().intent.terms.expires_at,NOW).max_total_fees,'0');
  for(const value of [{...form(),max_total_fees:''},{...form(),max_total_fees:'-1'},{...form(),valid_until:''},{...form(),valid_until:new Date(NOW+184999).toISOString()},{...form(),valid_until:new Date(NOW+3600001).toISOString()},{...form(),port:'70000'},{...form(),observe:'6'},{...form(),call_timeout_seconds:'31'}])assert.throws(()=>ui.boundsFromForm(value,candidate().intent.terms.expires_at,NOW));
});
test('local deadline display crosses the UTC date boundary without changing original ISO or submitted bounds',()=>{
  const {execFileSync}=require('node:child_process');
  // An isolated child fixes the local zone without changing this test runner's
  // clock or environment; the original ISO and economic comparison stay intact.
  const script=`const assert=require('node:assert/strict'),ui=require(process.argv[1]);
    const candidate='2026-10-29T23:49:00.000Z',rawPlan='2026-10-29T23:04:00.000Z';
    assert.equal(ui.localTime(candidate),'2026-10-30 07:49:00');
    assert.equal(ui.localTime(rawPlan),'2026-10-30 07:04:00');
    const form={...ui.defaults,valid_until:'2026-10-30T07:04:00',max_total_fees:'2.00'},before=JSON.stringify(form);
    const bounds=ui.boundsFromForm(form,candidate,Date.parse('2026-10-29T22:59:00.000Z'));
    assert.equal(bounds.valid_until,rawPlan);assert.equal(candidate,'2026-10-29T23:49:00.000Z');assert.equal(JSON.stringify(form),before);
    assert.equal(ui.localTime(undefined),'未记录');assert.equal(ui.localTime('not-a-time'),'时间无法识别');
    assert.throws(()=>ui.boundsFromForm({...form,valid_until:'2026-10-30T07:50:00'},candidate,Date.parse('2026-10-29T22:59:00.000Z')));
  `;
  execFileSync(process.execPath,['-e',script,require.resolve('./terminal-broker-plan-ui')],{env:{...process.env,TZ:'Asia/Shanghai'},encoding:'utf8'});
});

test('saved fact survives auxiliary list failure and missing adapter remains a gap plan',async()=>{
  const f=await ready(fixture({read:resource=>{if(resource.startsWith('terminal_broker_plans/'))throw Error('list unavailable');}}));await f.c.save();
  assert.equal(f.writes.length,1);assert.equal(f.c.state.fact.status,'PLAN_SAVED');assert.equal(f.c.state.pending,null);assert.match(f.c.state.readError,/保存事实仍保留/);assert.equal(f.c.state.fact.plan_status,'BLOCKED_CAPABILITY');
  assert.deepEqual(Object.keys(f.writes[0].payload).sort(),['mode','request_id','config_id','intent_id','expected_control_revision','bounds'].sort());
});
test('durable acknowledgement survives the host throwing after onSuccess',async()=>{
  const f=await ready(fixture({afterSuccess:true}));await f.c.save();assert.equal(f.c.state.fact.status,'PLAN_SAVED');assert.equal(f.c.state.pending,null);assert.equal(f.writes.length,1);
});
test('render failure after a durable acknowledgement cannot turn a saved plan into not submitted',async()=>{
  const f=await ready(fixture({changed:state=>{if(state.fact)throw Error('deliberate rendering failure');}}));await f.c.save();
  assert.equal(f.c.state.fact.status,'PLAN_SAVED');assert.equal(f.c.state.pending,null);assert.equal(f.c.state.error,'');assert.match(f.c.state.readError,/已确认的保存事实/);assert.equal(f.writes.length,1);
});
test('rereading capabilities immediately invalidates old confirmation and cannot use old PACKAGED after failure',async()=>{
  let blocked=false,rejectRead;const f=await ready(fixture({read:r=>blocked&&r.startsWith('terminal_broker_plan_capabilities/')?new Promise((_resolve,reject)=>{rejectRead=reject;}):undefined}));
  await f.c.save();const fact=copy(f.c.state.fact),items=copy(f.c.state.items);f.c.setConfirmation(true);blocked=true;
  const reading=f.c.readCapabilities();assert.equal(f.c.state.capabilities,null);assert.equal(f.c.state.confirmed,false);assert.equal(f.c.state.capLoading,true);await assert.rejects(()=>f.c.save(),/读取当前程序包条件/);
  rejectRead(Error('fresh identity unavailable'));await reading;f.c.setConfirmation(true);await assert.rejects(()=>f.c.save(),/读取当前程序包条件/);assert.equal(f.c.state.capabilities,null);assert.deepEqual(f.c.state.fact,fact);assert.deepEqual(f.c.state.items,items);assert.equal(f.writes.length,1);
});
test('NOT_PACKAGED cannot create a new plan and a refused backend result is not promoted',async()=>{
  const f=fixture();f.setCap('NOT_PACKAGED');await ready(f);await assert.rejects(()=>f.c.save(),/未绑定程序包/);assert.equal(f.writes.length,0);
  const refused=await ready(fixture({refused:true}));await refused.c.save();assert.equal(refused.c.state.fact.status,'PLAN_NOT_CREATED');assert.equal(refused.c.state.fact.plan_id,null);assert.equal(refused.c.state.pending,null);
});
test('lost response is recovered with original request and workspace after switching modes, without another POST',async()=>{
  const f=await ready(fixture({drop:true}));await f.c.save();const pending=copy(f.c.state.pending);assert.ok(pending);
  f.c.setContext(candidate(REAL));await f.c.readCapabilities();f.c.setConfirmation(true);await assert.rejects(()=>f.c.save(),/原计划请求/);await f.c.queryPending();
  assert.equal(f.writes.length,1);assert.equal(f.c.state.fact.mode,SIM);assert.equal(f.c.state.fact.request_id,pending.request_id);assert.equal(f.c.state.pending,null);
  const last=JSON.parse(decodeURIComponent(f.reads.at(-1).split('/')[1]));assert.deepEqual(last,{mode:SIM,request_id:pending.request_id});
});
test('PREPARING and NOT_RECORDED keep the original request locked without retry',async()=>{
  const f=await ready(fixture({preparing:true}));await f.c.save();const original=copy(f.c.state.pending);await f.c.queryPending();assert.ok(f.c.state.pending);assert.equal(f.writes.length,1);
  f.records.clear();await f.c.queryPending();assert.equal(f.c.state.pending.request_id,original.request_id);await assert.rejects(()=>f.c.save(),/原计划请求/);
  f.record(original.payload);await f.c.queryPending();assert.equal(f.c.state.fact.status,'PLAN_SAVED');assert.equal(f.writes.length,1);
});
test('cross-mode, cross-workspace and any missing/extra/open permission reject the claimed result',async()=>{
  const changes=[v=>{v.mode=REAL;return v;},v=>{v.workspace_context='f'.repeat(64);return v;},v=>{v.permissions.submit_allowed=true;return v;},v=>{delete v.permissions.query_allowed;return v;},v=>{v.permissions.adapter_installed=false;return v;},v=>{v.receipt.result.permissions.cancel_allowed=true;return v;}];
  for(const alter of changes){const f=await ready(fixture({alter}));await f.c.save();assert.equal(f.c.state.fact,null);assert.ok(f.c.state.pending);assert.equal(f.writes.length,1);}
});
test('resealed payload or request hash cannot replace the original six-field scope',async()=>{
  for(const mutate of [p=>{p.expected_control_revision=2;},p=>{p.bounds.max_total_fees='999';},p=>{p.runtime={verified:true};}]){
    const f=await ready(fixture({alter:value=>{mutate(value.claim.payload);value.claim=seal({...value.claim,id:undefined});return value;}}));await f.c.save();assert.equal(f.c.state.fact,null);assert.ok(f.c.state.pending);
  }
});
test('form, mode, source/intent and stop revision changes cancel explicit confirmation',async()=>{
  const f=await ready(fixture());assert.equal(f.c.state.confirmed,true);f.c.setForm({...form(),max_total_fees:'3'});assert.equal(f.c.state.confirmed,false);
  for(const change of [{...candidate(),expected_control_revision:2},{...candidate(),blocked:true},{...candidate(),intent:{...candidate().intent,id:'e'.repeat(64)}},candidate(REAL)]){f.c.setConfirmation(true);f.c.setContext(change);assert.equal(f.c.state.confirmed,false);assert.equal(f.c.state.capabilities,null);}
  assert.equal(f.writes.length,0);
});
test('late capabilities cannot authorize a new context or workspace',async()=>{
  let finish;const f=fixture({read:r=>r.startsWith('terminal_broker_plan_capabilities/')?new Promise(resolve=>{finish=resolve;}):undefined});const pending=f.c.readCapabilities();f.c.setContext(candidate(REAL));finish(f.capabilities(SIM));await pending;assert.equal(f.c.state.capabilities,null);assert.equal(f.c.state.workspaceContext,null);assert.equal(f.c.state.capLoading,false);
});
test('explicit history recovery queries the recorded payload, never the current candidate form',async()=>{
  const backend=await ready(fixture());await backend.c.save();const original=backend.writes[0].payload;backend.record(original,{preparing:true});
  const c=ui.createController({api:backend.api,perform:async()=>assert.fail('History cannot POST'),now:()=>NOW});c.setContext({mode:SIM,intent:null,blocked:true});await c.readPlans();assert.equal(c.state.pending,null);
  await c.recoverRequest(original.request_id);assert.equal(c.state.pending.request_id,original.request_id);assert.deepEqual(c.state.pending.payload,original);backend.record(original);await c.queryPending();assert.equal(c.state.fact.plan_id,backend.records.get(SIM+':'+original.request_id).plan.id);
});
test('old plan reads do not need capabilities and keep original budgets and identities unchanged',async()=>{
  const f=await ready(fixture());await f.c.save();const id=f.c.state.items[0].plan_id,before=JSON.stringify(f.plans.get(id)),readCount=f.reads.length;await f.c.readPlan(id);
  assert.equal(f.c.state.detail.plan_id,id);assert.equal(JSON.stringify(f.c.state.detail.plan),before);assert.equal(JSON.stringify(f.plans.get(id)),before);assert.equal(f.reads.length,readCount+1);assert.ok(f.reads.at(-1).startsWith('terminal_broker_plan/'));assert.equal(f.writes.length,1);
});
test('late detail response cannot populate another selected mode',async()=>{
  const backend=await ready(fixture());await backend.c.save();let finish;
  const c=ui.createController({api:resource=>resource.startsWith('terminal_broker_plan/')?new Promise(resolve=>{finish=resolve;}):backend.api(resource),perform:()=>assert.fail('No POST'),now:()=>NOW});c.setContext(candidate());await c.readPlans();const id=c.state.items[0].plan_id,pending=c.readPlan(id);c.setContext(candidate(REAL));finish(await backend.api('terminal_broker_plan/'+encodeURIComponent(JSON.stringify({mode:SIM,plan_id:id}))));await pending;assert.equal(c.state.detail,null);assert.equal(c.state.detailLoading,false);
});

test('plan form DOM has visible budgets, no installation reads, durable save and independent parent stop at 1280/480',async t=>{
  const fs=require('node:fs'),path=require('node:path'),{chromium}=require('playwright');
  const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_BROWSER_EXECUTABLE||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-background-networking','--no-first-run']});t.after(()=>browser.close());
  for(const width of [1280,480]){
    const f=fixture(),page=await browser.newPage({viewport:{width,height:960}}),errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
    const documentHtml='<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px/1.5 system-ui;margin:20px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label{display:block}input{width:100%;box-sizing:border-box}input[type=checkbox]{width:auto}.section-gap{margin-top:20px}button{font:inherit}.panel{padding:16px;border:1px solid #d8e0eb}</style><button id="outside-stop">停止准备新意图</button><main id="host"></main>';
    await page.route('**/*',route=>{if(route.request().url()==='http://127.0.0.1:55324/')return route.fulfill({contentType:'text/html',body:documentHtml});if(route.request().url().endsWith('/favicon.ico'))return route.fulfill({status:204});requests.push(route.request().url());return route.abort();});
    await page.goto('http://127.0.0.1:55324/');
    await page.exposeFunction('readMock',f.api);await page.exposeFunction('writeMock',async(action,payload)=>f.perform(action,payload,{onSuccess:()=>{}}));
    await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,'terminal-broker-plan-ui.js'),'utf8')});
    await page.evaluate(value=>{window.planUI=installTerminalBrokerPlanUI({host:document.querySelector('#host'),api:readMock,perform:writeMock});planUI.setContext(value);},candidate());assert.equal(f.reads.length,0);assert.equal(f.writes.length,0);
    await page.locator('[data-tbp-action=conditions]').click();await page.waitForFunction(()=>planUI.controller.state.capabilities);assert.equal(await page.locator('#tbp-valid_until').inputValue(),'');assert.equal(await page.locator('#tbp-max_total_fees').inputValue(),'');
    // Browser runs at the real local clock; move only the synthetic candidate
    // expiry and explicit form date, never production or saved business data.
    await page.evaluate(value=>{const until=Date.now()+3600000;value.intent.terms.expires_at=new Date(until).toISOString();value.candidate_terms.expires_at=value.intent.terms.expires_at;planUI.setContext(value);},candidate());await page.locator('[data-tbp-action=conditions]').click();await page.waitForFunction(()=>planUI.controller.state.capabilities);
    const localDate=await page.evaluate(()=>{const date=new Date(Date.now()+900000);date.setMinutes(date.getMinutes()-date.getTimezoneOffset());return date.toISOString().slice(0,16);});
    await page.fill('#tbp-valid_until',localDate);await page.fill('#tbp-max_total_fees','2.00');await page.check('#tbp-confirm');assert.equal(await page.locator('#tbp-form').evaluate(form=>form.checkValidity()),true);await page.locator('#tbp-save').click();await page.waitForFunction(()=>planUI.controller.state.fact||planUI.controller.state.error);assert.equal(await page.evaluate(()=>planUI.controller.state.fact?.status),'PLAN_SAVED',await page.evaluate(()=>planUI.controller.state.error));
    assert.match(await page.locator('#tbp-fact').innerText(),/已保存.*未连接/);assert.match(await page.locator('#tbp-expiry').innerText(),/原候选失效时间（本地时间）/);assert.match(await page.locator('#tbp-original-expiry').textContent(),/原始 ISO.*Z/);assert.equal(await page.locator('#outside-stop').isDisabled(),false);assert.equal(f.writes.length,1);
    await page.locator('[data-tbp-action=detail]').click();await page.waitForFunction(()=>planUI.controller.state.detail?.status==='FOUND');assert.match(await page.locator('#tbp-detail').innerText(),/合成研究固定只限离线/);assert.match(await page.locator('#tbp-detail').innerText(),/计划失效时间（本地时间）/);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    if(process.env.BROKER_PLAN_EVIDENCE_DIR){await page.locator('#tbp-fact').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.BROKER_PLAN_EVIDENCE_DIR,'plan-saved-'+width+'.png'),fullPage:true});}
    assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);await page.close();
  }
});
