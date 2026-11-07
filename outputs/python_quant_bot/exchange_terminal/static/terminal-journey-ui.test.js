'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const ui=require('./terminal-journey-ui');
const copy=v=>JSON.parse(JSON.stringify(v)),ref={kind:'terminal_run',id:'a'.repeat(64)};
const selected=()=>({task:null,research:copy(ref),view:'continuous',replay:{account_id:'replay-a'},manual:{account_id:'manual-a',plan_id:'b'.repeat(64)},broker:{mode:'OFFICIAL_SIMULATION',config_id:'c'.repeat(64),intent_id:'d'.repeat(64),plan_id:'e'.repeat(64)}});
function envelope(selection=selected(),revision=1){return {schema_version:ui.SCHEMA,workspace_context:'f'.repeat(64),revision,selection:copy(selection),read_only:true,status:selection?'SAVED':'EMPTY',resolution:{},new_economic_runs:0,external_calls:0,permissions:{order_allowed:false,live_allowed:false,paper_allowed:false}};}
function fixture(options={}){let snapshot=envelope(),counter=0;const reads=[],writes=[],restores=[];
  const callbacks=Object.fromEntries(['execution','continuous','broker','plan'].map(name=>[name,{state:{research:{binding:{task_id:'original'}}},restoreSelection:async s=>{restores.push({name,s:copy(s)});if(options.fail===name)throw Error(name+' unavailable');}}]));
  const c=ui.createController({api:async path=>{reads.push(path);return copy(snapshot);},saveSelection:async p=>{writes.push(copy(p));if(options.lost)throw Error('lost reply');snapshot=envelope(p.selection,p.expected_revision+1);return {...copy(snapshot),read_only:false,request_id:p.request_id,saved:true};},uuid:()=>String(++counter),...callbacks,onRestore:async view=>restores.push({view}),...options});
  return {c,reads,writes,restores,setSnapshot:v=>{snapshot=v;}};
}
test('reopen restores every exact reference by reads with no save and no controller confirmation',async()=>{
  const f=fixture();await f.c.load();assert.deepEqual(f.reads,['terminal_journey']);assert.equal(f.writes.length,0);assert.deepEqual(f.restores.map(v=>v.name||v.view),['execution','continuous','broker','plan','continuous']);
  assert.deepEqual(f.c.state.selection,selected());assert.equal(f.c.state.restoring,false);
});
test('one unavailable stage does not hide the other saved identities',async()=>{
  const f=fixture({fail:'continuous'});await f.c.load();assert.equal(f.c.state.diagnostics.length,1);assert.equal(f.c.state.diagnostics[0].stage,'replay');assert.ok(f.restores.some(v=>v.name==='broker'));assert.deepEqual(f.c.state.selection,selected());assert.equal(f.writes.length,0);
});
test('explicit source change clears unrelated downstream refs and core cannot use native replay',async()=>{
  const f=fixture();await f.c.load({restore:false});const core={kind:'core_run',id:'1'.repeat(24)};await f.c.select({research:core,view:'execution'});
  assert.equal(f.writes.length,1);assert.equal(f.writes[0].workspace_context,'f'.repeat(64));assert.equal(f.writes[0].selection.manual,null);assert.equal(f.writes[0].selection.replay,null);assert.equal(f.writes[0].selection.broker,null);
  await assert.rejects(f.c.continueAt('continuous'),/不支持|仅支持/);assert.equal(f.writes.length,1);assert.equal(f.restores.length,0);
});
test('unchanged explicit continue reads originals but does not rewrite preference',async()=>{const f=fixture();await f.c.load({restore:false});await f.c.continueAt('continuous');assert.equal(f.writes.length,0);assert.equal(f.restores.at(-1).view,'continuous');});
test('lost preference response retains the original request and business refs without retry',async()=>{
  const f=fixture({lost:true});await f.c.load({restore:false});await assert.rejects(f.c.select({view:'execution'}),/lost/);const pending=copy(f.c.state.pending);
  await assert.rejects(f.c.select({view:'broker'}),/原保存请求/);assert.equal(f.writes.length,1);assert.deepEqual(f.c.state.pending,pending);assert.deepEqual(f.c.state.selection,selected());
  f.setSnapshot(envelope(pending.selection,2));await f.c.reconcileSelection();assert.equal(f.c.state.pending,null);assert.equal(f.writes.length,1);
});
test('stale revision does not overwrite another window and no automatic second post follows',async()=>{
  const f=fixture({saveSelection:async p=>({...envelope({...selected(),view:'broker'},2),request_id:p.request_id,status:'REVISION_CONFLICT',saved:false})});await f.c.load({restore:false});await assert.rejects(f.c.select({view:'execution'}),/另一窗口/);assert.equal(f.c.state.selection.view,'broker');assert.equal(f.c.state.pending,null);
});
test('late initial GET cannot overwrite a newer read or call old page navigation',async()=>{
  let release,n=0;const restores=[];const c=ui.createController({api:async()=>++n===1?await new Promise(r=>{release=r;}):envelope({...selected(),view:'results'},2),onRestore:v=>restores.push(v)});
  const first=c.load();await c.load();release(envelope());await first;assert.equal(c.state.selection.view,'results');assert.deepEqual(restores,['results']);
});
test('strict references reject arbitrary settings, paths and implicit version fields',()=>{
  assert.ok(ui.validSelection(selected()));for(const bad of [{...selected(),secret:'token'},{...selected(),manual:{account_id:'../other',plan_id:null}},{...selected(),task:{kind:'core_task',id:'family'}}])assert.equal(ui.validSelection(bad),false);
});
test('continue panel stays usable at wide/narrow sizes and never saves during render or restore',async()=>{
  const {chromium}=require('playwright'),path=require('node:path'),browser=await chromium.launch({headless:true});
  try{for(const width of [1280,390]){const page=await browser.newPage({viewport:{width,height:800}});await page.setContent('<main></main>');await page.addScriptTag({path:path.join(__dirname,'terminal-journey-ui.js')});
    await page.evaluate(({snapshot})=>{window.saved=[];window.restored=[];window.panel=installTerminalJourneyUI({host:document.querySelector('main'),api:async()=>snapshot,saveSelection:async p=>{saved.push(p);throw Error('unexpected save');},execution:{restoreSelection:async()=>{}},continuous:{restoreSelection:async()=>{}},broker:{state:{research:{binding:{}}},restoreSelection:async()=>{}},plan:{restoreSelection:async()=>{}},onRestore:v=>restored.push(v)});return panel.controller.load();},{snapshot:envelope()});
    await page.getByRole('button',{name:'继续查看原记录'}).focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>restored.length===2);assert.deepEqual(await page.evaluate(()=>saved),[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    if(process.env.HAKIMI_U07_DOM_EVIDENCE_DIR){require('node:fs').mkdirSync(process.env.HAKIMI_U07_DOM_EVIDENCE_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.HAKIMI_U07_DOM_EVIDENCE_DIR,`journey-${width}.png`),fullPage:true});}await page.close();}
  }finally{await browser.close();}
});
