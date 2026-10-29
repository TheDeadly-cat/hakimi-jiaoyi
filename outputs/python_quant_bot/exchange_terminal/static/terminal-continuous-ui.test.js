'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const ui=require('./terminal-continuous-ui');
const copy=v=>JSON.parse(JSON.stringify(v)),context='a'.repeat(64),source={kind:'terminal_run',id:'b'.repeat(64),label:'QA · 双均线 · 版本 1',status:'COMPLETED'};
const form={display_name:'中文模拟一号',initial_cash:'10000',unit_quantity:'1',fee_percent:'0.1',slippage_bps:'5'};
const envelope=v=>({...v,schema_version:ui.SCHEMA,workspace_context:context});
const hash=v=>crypto.createHash('sha256').update(ui.canonical(v)).digest('hex');
function memory(){const map=new Map();return {map,getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)};}
function fixture(options={}){
  const storage=options.storage||memory(),writes=[],reads=[],receipts=new Map(),snapshots=new Map();let count=0,head=0;
  function snapshot(id,settings){return {account_id:id,head:(++head).toString(16).padStart(64,'0'),phase:'SEED_REQUIRED',state:{cash:settings.initial_cash,quantity:0,pending_signal:null},last_session:null,next_session:{date:'2026-02-17'},seed_selection:{recommended_count:80,recommended_session:'2026-06-05',next_session:'2026-06-08'},display_summary:{...settings,symbol:'QA',strategy_id:'dual_ma',task_version:'r0001-test',reference:copy(source)},implementation_compatible:true};}
  async function api(resource){reads.push(resource);const [name,raw]=resource.split('/'),p=raw?JSON.parse(decodeURIComponent(raw)):{};
    if(options.read) {const override=await options.read(name,p);if(override!==undefined)return override;}
    if(name==='terminal_replay_accounts')return envelope({items:[...snapshots.values()].map(v=>({account_id:v.account_id,head:v.head,phase:v.phase,last_session:v.last_session,display_summary:v.display_summary})),has_more:false,next_after:''});
    if(name==='terminal_replay_preview')return envelope({status:'REPLAY_MODEL_CONFIRMATION_REQUIRED',admission_id:'c'.repeat(64),reference:p.reference,settings:p.settings,model:{id:ui.MODEL,native_execution_equivalent:false,intrabar_stop_loss:false,intrabar_take_profit:false},first_session:'2026-02-17',last_session:'2026-06-12',seed_selection:{recommended_count:80,recommended_session:'2026-06-05',next_session:'2026-06-08'}});
    if(name==='terminal_replay_status'){if(!snapshots.has(p.account_id))throw Error('account_not_found');return envelope(copy(snapshots.get(p.account_id)));}
    if(name==='terminal_replay_receipt'||name==='terminal_replay_creation_receipt'){if(!receipts.has(p.request_id))throw Error('request_not_found');return copy(receipts.get(p.request_id));}
    if(name==='terminal_replay_history')return envelope({head:p.expected_head,items:[{sequence:1,kind:'CREATED'}],has_more:false,next_after:1});
    throw Error('unexpected read '+name);
  }
  async function commit(action,p){const id=action==='create'?p.settings.account_id:p.account_id;
    if(action==='create')snapshots.set(id,snapshot(id,p.settings));const s=snapshots.get(id);if(!s)throw Error('account_not_found');
    const status={create:'CREATED',seed:'SEED_SIGNAL_ONLY',step:'ONE_BAR_APPLIED',pause:'PAUSED',reconcile:'RECONCILED_PAUSED',resume:'EXPLICITLY_RESUMED_NO_STEP',adopt:'INPUT_VERSION_ADOPTED_NO_STEP'}[action];
    if(action==='seed'){s.phase='READY_FOR_EXPLICIT_STEP';s.last_session={date:'2026-06-05'};s.next_session={date:'2026-06-08'};s.state.pending_signal={value:{action:'HOLD'}};}
    if(action==='step'){s.last_session=s.next_session;s.next_session={date:'2026-06-09'};}
    if(action==='pause'||action==='reconcile')s.phase='PAUSED';if(action==='resume')s.phase='READY_FOR_EXPLICIT_STEP';
    s.head=(++head).toString(16).padStart(64,'0');const value=envelope({account_id:id,request_id:p.request_id,request_action:action,request_hash:hash(p),head:s.head,...(action==='create'?{status}:{outcome:{status}})});receipts.set(p.request_id,value);return copy(value);
  }
  async function perform(name,p,opts){const action=name.replace('terminal_replay_','');writes.push({action,p:copy(p),direct:false});if(options.perform)return options.perform(action,p,opts,commit);const value=await commit(action,p);await opts.onSuccess(value);return value;}
  async function pauseReplay(p){writes.push({action:'pause',p:copy(p),direct:true});return options.pause?options.pause(p,commit):commit('pause',p);}
  const make=()=>ui.createController({api,perform,pauseReplay,storage,uuid:()=>String(++count).padStart(12,'0'),hashPayload:async v=>hash(v)});
  return {make,controller:make(),storage,writes,reads,receipts,snapshots,commit,api};
}
async function prepare(f){const c=f.controller;await c.refresh();c.setSources([source]);c.selectSource(source);c.setForm(form);await c.preview();c.confirmModel(true);return c;}
async function created(f){const c=await prepare(f);await c.create();return c;}

test('canonical hash agrees with Python ASCII compact sorted-key fixture including Unicode',async()=>{
  const value={z:'暂停：核对😀',a:{name:'中文模拟',n:3}};
  assert.equal(ui.canonical(value),' {"a":{"n":3,"name":"\\u4e2d\\u6587\\u6a21\\u62df"},"z":"\\u6682\\u505c\\uff1a\\u6838\\u5bf9\\ud83d\\ude00"}'.trim());
  assert.equal(await ui.digest(value),hash(value));assert.throws(()=>ui.canonical({a:NaN}));assert.throws(()=>ui.canonical({a:0.5}));
});
test('user percent input converts by exact decimal shifts without rounding at the service boundary',()=>{
  for(const [input,ratio] of [['0.1','0.001'],['0.015','0.00015'],['5','0.05'],['0','0'],['0.000001','0.00000001']]){const got=ui.settings({...form,fee_percent:input},'replay-fixture');assert.equal(got.fee_rate,ratio);assert.equal(ui.percent(ratio),input+'%');}
  for(const bad of ['','0.0000001','5.000001','-1','1e-3','0.1%'])assert.throws(()=>ui.settings({...form,fee_percent:bad},'replay-fixture'),/费率/);
});
test('controller installation and source/input population have no read, mutation or storage effects',()=>{
  let access=0;const f=fixture({storage:()=>{access++;throw Error('unavailable');}});const c=f.controller;
  c.setSources([source,{kind:'core_run',id:'b'.repeat(24)},{...source,id:'c'.repeat(64),status:'FAILED'}]);
  c.setInputs([{id:'c'.repeat(64),available:true},{id:'d'.repeat(64),available:false},{id:'unknown'}]);
  assert.equal(c.state.sources.length,1);assert.equal(c.state.inputs.length,1);assert.equal(f.reads.length,0);assert.equal(f.writes.length,0);assert.equal(access,0);
});
test('every edited create parameter invalidates preview and model confirmation; nothing is created by preview',async()=>{
  const f=fixture(),c=await prepare(f);assert.equal(f.writes.length,0);assert.equal(c.state.preview.settings.display_name,form.display_name);
  c.setForm({...form,unit_quantity:'2'});assert.equal(c.state.preview,null);assert.equal(c.state.confirmed,false);await assert.rejects(c.create(),/确认/);
  await c.preview();c.confirmModel(true);c.selectSource(null);assert.equal(c.state.preview,null);assert.equal(c.state.confirmed,false);
});
test('successful create is persisted before sending; exact acknowledgement clears pending without an auxiliary receipt dependency',async()=>{
  let f;f=fixture({perform:async(action,p,opts,commit)=>{assert.equal(f.storage.map.size,1);const old=[...f.storage.map.values()][0];assert.equal(JSON.parse(old).request_id,p.request_id);opts.onSuccess(await commit(action,p));}});
  const c=await created(f);assert.equal(f.writes.length,1);assert.equal(f.writes[0].action,'create');assert.equal(f.storage.map.size,0);assert.equal(c.state.snapshot.phase,'SEED_REQUIRED');assert.match(c.state.fact.text,/已保存/);assert.equal(c.state.snapshot.head,f.snapshots.get(c.state.accountId).head);assert.equal(f.reads.filter(v=>v.startsWith('terminal_replay_creation_receipt')).length,0);
});
test('storage failure or unverified storage write prevents any submission',async()=>{
  const s=memory(),f=fixture({storage:s}),c=await prepare(f);s.setItem=()=>{throw Error('quota');};await c.create();assert.equal(f.writes.length,0);assert.match(c.state.storageError,/尚未发送/);
  const s2=memory(),f2=fixture({storage:s2}),c2=await prepare(f2);s2.setItem=()=>{};await c2.create();assert.equal(f2.writes.length,0);
});
test('lost create response survives a new controller and reveal reads; only querying the same receipt clears it',async()=>{
  const f=fixture({perform:async(action,p,_opts,commit)=>{await commit(action,p);throw Error('lost response');}}),c=await prepare(f);await c.create();
  const original=copy(c.state.pending.normal);assert.equal(f.storage.map.size,1);assert.match(c.state.error,/待核对/);
  const resumed=f.make();assert.equal(resumed.state.pending.normal,null);await resumed.refresh();assert.equal(f.writes.length,1);assert.equal(resumed.state.pending.normal.request_id,original.request_id);assert.equal(resumed.state.accountId,'');
  await resumed.queryPending('normal');assert.equal(f.writes.length,1);assert.equal(f.storage.map.size,0);assert.equal(resumed.state.snapshot.account_id,original.account_id);assert.equal(resumed.state.snapshot.head,f.snapshots.get(original.account_id).head);
});
test('not found and PENDING are not retry permission and cannot erase original request',async()=>{
  const f=fixture({perform:async()=>{throw Error('offline');}}),c=await prepare(f);await c.create();const original=copy(c.state.pending.normal);
  await c.queryPending('normal');assert.equal(c.state.pending.normal.request_id,original.request_id);await assert.rejects(c.create(),/核对/);
  f.receipts.set(original.request_id,envelope({account_id:original.account_id,request_id:original.request_id,request_action:original.action,request_hash:original.request_hash,status:'PENDING'}));await c.queryPending('normal');assert.equal(f.storage.map.size,1);assert.equal(f.writes.length,1);
});
test('wrong workspace/account/action/hash/request identities never clear a pending request',async()=>{
  for(const [key,bad] of [['workspace_context','d'.repeat(64)],['account_id','other-account'],['request_action','step'],['request_hash','d'.repeat(64)],['request_id','other-request'],['schema_version','wrong']]){
    const f=fixture({perform:async(a,p,_o,commit)=>{await commit(a,p);throw Error('lost');}}),c=await prepare(f);await c.create();const p=c.state.pending.normal;f.receipts.get(p.request_id)[key]=bad;await c.queryPending('normal');assert.ok(c.state.pending.normal,key);assert.equal(f.storage.map.size,1,key);
  }
});
test('malformed durable record is preserved and blocks new submissions',async()=>{
  const storage=memory();storage.map.set('hakimi-terminal-replay-pending-v1:'+context+':normal','{broken');const f=fixture({storage});await f.controller.refresh();assert.match(f.controller.state.storageError,/无法安全读取/);assert.equal(storage.map.size,1);await assert.rejects(f.controller.create(),/核对/);assert.equal(f.writes.length,0);
});
test('seed and step use server dates/count and advance only on explicit separate actions',async()=>{
  const f=fixture(),c=await created(f);await c.act('seed');assert.equal(f.writes[1].p.seed_count,80);assert.equal(c.state.snapshot.last_session.date,'2026-06-05');assert.equal(c.state.snapshot.next_session.date,'2026-06-08');assert.equal(f.writes.length,2);
  await c.refresh();await c.openAccount(c.state.accountId);assert.equal(f.writes.length,2);await c.act('step');assert.equal(f.writes.length,3);assert.equal(c.state.snapshot.last_session.date,'2026-06-08');assert.equal(c.state.snapshot.next_session.date,'2026-06-09');
});
test('pause has its own direct lane and original in-flight step identity; it never uses Jobs',async()=>{
  let release;const f=fixture(),c=await created(f);await c.act('seed');
  // Replace the perform dependency in a new controller; restore current account by GET.
  const c2=ui.createController({api:f.api,storage:f.storage,uuid:()=>crypto.randomUUID(),hashPayload:async v=>hash(v),perform:async(name,p)=>{f.writes.push({action:name,p});await new Promise(r=>release=r);throw Error('lost');},pauseReplay:async p=>{assert.equal(f.storage.map.size,2);f.writes.push({action:'direct-pause',p});return f.commit('pause',p);}});
  await c2.refresh();await c2.openAccount(c.state.accountId);const before=c2.state.snapshot.head,promise=c2.act('step');await new Promise(r=>setImmediate(r));const request=c2.state.pending.normal.request_id;
  await c2.act('pause',{reason:'人工核对'});const p=f.writes.at(-1).p;assert.equal(p.expected_head,before);assert.equal(p.in_flight_request_id,request);assert.equal(c2.state.pending.control,null);assert.equal(f.storage.map.size,1);release();await promise;assert.equal(c2.state.pending.normal.request_id,request);
});
test('recovery review and resume are separate and neither automatically steps',async()=>{
  const f=fixture(),c=await created(f),id=c.state.accountId;f.snapshots.get(id).phase='RECOVERY_REQUIRED';await c.openAccount(id);await assert.rejects(c.act('reconcile'),/核对/);c.review(true);await c.act('reconcile');assert.equal(c.state.snapshot.phase,'PAUSED');assert.equal(c.state.reviewedHead,null);await assert.rejects(c.act('resume'),/核对/);c.review(true);await c.act('resume');assert.equal(f.writes.filter(v=>v.action==='step').length,0);
});
test('adopt requires an explicitly selected available saved input and confirmation, and no step',async()=>{
  const f=fixture(),c=await created(f);f.snapshots.get(c.state.accountId).phase='WAITING_DATA';await c.openAccount(c.state.accountId);c.setInputs([{id:'d'.repeat(64),available:true}]);await assert.rejects(c.act('adopt'),/选择/);c.selectInput('d'.repeat(64));c.confirmInput(true);await c.act('adopt');assert.equal(f.writes.at(-1).p.input_id,'d'.repeat(64));assert.equal(f.writes.filter(v=>v.action==='step').length,0);
});
test('saved success is never changed to operation failure by shell or state read errors',async()=>{
  const f=fixture({perform:async(a,p,o,commit)=>{o.onSuccess(await commit(a,p));throw Error('shell refresh failure');},read:async name=>{if(name==='terminal_replay_status')throw Error('read unavailable');}}),c=await prepare(f);await c.create();assert.match(c.state.fact.text,/已保存/);assert.equal(c.state.error,'');assert.equal(c.state.pending.normal,null);assert.equal(f.writes.length,1);assert.match(c.state.readError,/shell refresh failure.*read unavailable/);
});
test('exact typed before-write refusal clears with no retry; a generic refusal still stays unknown',async()=>{
  const f=fixture({perform:async(a,p,o)=>{o.onSuccess(envelope({account_id:p.settings.account_id,request_id:p.request_id,request_action:a,request_hash:hash(p),status:'REFUSED_NOT_APPLIED',automatic_retry:false,reason:'记录版本已经变化'}));}}),c=await prepare(f);await c.create();assert.equal(c.state.pending.normal,null);assert.match(c.state.fact.text,/未应用.*版本已经变化/);assert.equal(f.writes.length,1);assert.equal(f.reads.filter(v=>v.startsWith('terminal_replay_creation_receipt')).length,0);
  const bad=fixture({perform:async(a,p,o)=>o.onSuccess(envelope({account_id:p.settings.account_id,request_id:p.request_id,request_action:a,request_hash:hash(p),status:'REFUSED_NOT_APPLIED'}))}),b=await prepare(bad);await b.create();assert.ok(b.state.pending.normal);
});
test('parallel submit attempts cannot overtake async digest or overwrite a durable request',async()=>{
  const f=fixture(),c=await prepare(f);const a=c.create();await assert.rejects(c.create(),/核对/);await a;assert.equal(f.writes.length,1);
});
test('double receipt query cannot clear the same persisted record twice or create a false storage failure',async()=>{
  let release;const f=fixture({perform:async(a,p,_o,commit)=>{await commit(a,p);throw Error('lost');},read:async name=>{if(name==='terminal_replay_creation_receipt')await new Promise(r=>release=r);}}),c=await prepare(f);await c.create();const a=c.queryPending('normal');await new Promise(r=>setImmediate(r));await c.queryPending('normal');release();await a;assert.equal(c.state.pending.normal,null);assert.equal(c.state.storageError,'');assert.equal(f.reads.filter(v=>v.startsWith('terminal_replay_creation_receipt')).length,1);
});
test('a stale source preview response cannot restore confirmation after edits',async()=>{
  let release;const f=fixture({read:async name=>{if(name==='terminal_replay_preview')await new Promise(r=>release=r);}}),c=f.controller;await c.refresh();c.setSources([source]);c.selectSource(source);c.setForm(form);const pending=c.preview();await new Promise(r=>setImmediate(r));c.setForm({...form,display_name:'已修改的名称'});release();await pending;assert.equal(c.state.preview,null);assert.equal(c.state.confirmed,false);assert.equal(f.writes.length,0);
});
test('workspace change during digest blocks sending before persistence',async()=>{
  const f=fixture();let release;const c=ui.createController({api:f.api,perform:()=>{throw Error('must never send');},storage:f.storage,uuid:()=>crypto.randomUUID(),hashPayload:async p=>{await new Promise(r=>release=r);return hash(p);}});f.controller=c;await prepare(f);const pending=c.create();await new Promise(r=>setImmediate(r));c.state.contextConflict=true;release();await pending;assert.equal(f.storage.map.size,0);assert.equal(f.writes.length,0);assert.match(c.state.error,/尚未发送/);
});
test('account labels present the original human name and version without inventing a version',()=>{
  assert.match(ui.accountLabel({display_summary:{display_name:'我的模拟',symbol:'QA',strategy_id:'dual_ma',task_version:'r0003-abcdef'},last_session:{date:'2026-10-01'}}),/我的模拟.*版本 3.*2026-10-01/);assert.doesNotMatch(ui.accountLabel({display_summary:{display_name:'无版本',task_version:null}}),/版本 \d/);
});

test('real DOM: explicit creation and next-day flow, percent display, lost response and read-only remount at 1280/480',async t=>{
  const fs=require('node:fs'),path=require('node:path'),{chromium}=require('playwright');
  const executablePath=[process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,chromium.executablePath(),'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(v=>v&&fs.existsSync(v));
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),args:['--disable-background-networking','--no-first-run']});t.after(()=>browser.close());
  for(const width of [1280,480]){
    const f=fixture(),context=await browser.newContext({viewport:{width,height:960}}),page=await context.newPage(),errors=[],unexpected=[];t.after(()=>context.close());page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await context.route('**/*',r=>{if(r.request().url()==='http://127.0.0.1:55317/')return r.fulfill({contentType:'text/html',body:'<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px/1.6 system-ui;margin:24px;background:#111a29;color:#e5edf8}input,select,button{font:inherit}button{padding:8px 16px}input,select{padding:8px}.panel{max-width:1100px;margin:auto}.notice{padding:14px;border:1px solid #62789a;margin:16px 0}.field{min-width:0}</style><main id="host"></main>'});unexpected.push(r.request().url());return r.abort();});
    await page.exposeFunction('readReplay',f.api);await page.exposeFunction('writeReplay',async(action,p)=>{f.writes.push({action,p:copy(p)});return f.commit(action,p);});await page.goto('http://127.0.0.1:55317/');
    await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,'terminal-continuous-ui.js'),'utf8')});
    await page.evaluate(source=>{window.install=()=>{document.querySelector('#host').replaceChildren();window.panel=installTerminalContinuousUI({host:document.querySelector('#host'),api:window.readReplay,perform:async(action,p,o)=>{const value=await window.writeReplay(action.replace('terminal_replay_',''),p);if(window.loseNext){window.loseNext=false;throw Error('synthetic lost response');}o.onSuccess(value);},pauseReplay:p=>window.writeReplay('pause',p)});panel.setSources([source]);};install();},source);
    assert.equal(f.reads.length,0);assert.equal(f.writes.length,0);await page.evaluate(()=>panel.reveal());await page.locator('[data-field=source]').selectOption(source.id);
    for(const [k,v] of Object.entries(form))await page.locator('[data-form='+k+']').fill(v);
    await page.locator('[data-action=preview]').click();await page.waitForSelector('[data-field=model-confirm]');assert.match(await page.locator('[data-role=preview]').innerText(),/费率 0.1%/);assert.equal(f.writes.length,0);
    await page.locator('[data-field=model-confirm]').check();if(width===480)await page.evaluate(()=>window.loseNext=true);await page.locator('[data-action=create]').click();await page.waitForFunction(()=>!panel.controller.state.busy.normal);
    if(width===480){assert.equal(await page.locator('[data-query=normal]').count(),1);const before=f.writes.length;await page.evaluate(async()=>{install();await panel.reveal();});assert.equal(f.writes.length,before);assert.equal(await page.locator('[data-query=normal]').count(),1);await page.locator('[data-query=normal]').click();}
    await page.waitForFunction(()=>panel.controller.state.snapshot?.phase==='SEED_REQUIRED');assert.equal(f.writes.length,1);assert.equal(f.writes[0].p.settings.fee_rate,'0.001');assert.match(await page.locator('[data-action=seed]').innerText(),/2026-06-05/);await page.locator('[data-action=seed]').click();await page.waitForFunction(()=>panel.controller.state.snapshot?.phase==='READY_FOR_EXPLICIT_STEP');
    assert.match(await page.locator('[data-action=step]').innerText(),/2026-06-08/);if(width===480)await page.evaluate(()=>window.loseNext=true);await page.locator('[data-action=step]').click();await page.waitForFunction(()=>!panel.controller.state.busy.normal);
    if(width===480){const before=f.writes.length;await page.evaluate(async()=>{install();await panel.reveal();});assert.equal(f.writes.length,before);await page.locator('[data-query=normal]').click();await page.waitForFunction(()=>!panel.controller.state.pending.normal);await page.locator('[data-field=account]').selectOption(f.writes[0].p.settings.account_id);}
    await page.waitForFunction(()=>panel.controller.state.snapshot?.last_session?.date==='2026-06-08');assert.equal(f.writes.length,3);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    if(process.env.CONTINUOUS_UI_EVIDENCE_DIR)await page.screenshot({path:path.join(process.env.CONTINUOUS_UI_EVIDENCE_DIR,'continuous-'+width+'.png'),fullPage:true});assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);await context.close();
  }
});
