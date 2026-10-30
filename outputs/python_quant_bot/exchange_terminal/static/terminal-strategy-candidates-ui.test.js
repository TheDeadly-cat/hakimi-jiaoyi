"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {renderDiagnostic,factorValue}=require("./terminal-strategy-candidates-ui");
const candidate=require("./terminal-strategy-candidates-ui"),copy=v=>JSON.parse(JSON.stringify(v));
const row=changes=>({schema_version:"hakimi-terminal-strategy-diagnostic-v1",diagnostic_id:"a".repeat(64),input_id:"b".repeat(64),
  strategy_id:"momentum",name:"动量",strategy_params:{threshold:.015},status:"READY",group:"ENTRY_MATCH",decision_matches_factors:true,
  signal:{action:"BUY"},position_context:{has_position:false},symbol:"QA",cutoff_session:"2024-07-31",complete_rows:130,warmup_rows:80,required_rows:82,
  factors:[{key:"momentum",label:"动量",value:.02,operator:">",threshold:.015,passed:true,applies_to_position:true,unit:"ratio"}],...changes});
test("ratio values and both inclusive boundaries use the same percent units",()=>{
  assert.equal(factorValue(.015,"ratio"),"1.5%");assert.equal(factorValue(0,"ratio"),"0%");
  assert.equal(factorValue([.005,.04],"ratio"),"0.5% 至 4%");
  const html=renderDiagnostic(row({factors:[{label:"ATR 比例",value:.02,operator:"between_inclusive",threshold:[.005,.04],passed:true,unit:"ratio"}]}));
  assert.match(html,/2%/);assert.match(html,/0.5% 至 4%（含边界）/);assert.doesNotMatch(html,/between_inclusive<\/td>/);
});
test("a BUY on insufficient data cannot offer strategy selection",()=>{
  const html=renderDiagnostic(row({status:"DATA_INSUFFICIENT",group:"INSUFFICIENT",missing_rows:2,complete_rows:80}));
  assert.match(html,/还缺 2 根/);assert.match(html,/至少需要 82 根/);
  assert.match(html,/data-candidate-choose="[a-f0-9]+" disabled/);
  assert.doesNotMatch(html,/截至所选日，满足开仓条件/);
});
test("missing factor is not zero and observed EXIT is not described as a new buy",()=>{
  const html=renderDiagnostic(row({signal:{action:"EXIT"},group:"EXIT_MATCH",position_context:{has_position:true},
    factors:[{label:"未记录值",value:null,operator:"<",threshold:1,passed:null,unit:"price"}]}));
  assert.match(html,/满足退出条件/);assert.match(html,/未记录值<\/th><td>未记录/);assert.match(html,/资料不足/);
});
test("provider and strategy text is escaped in visible reasons and raw details",()=>{
  const html=renderDiagnostic(row({name:'<img src=x onerror=alert(1)>',factors:[{label:'<script>alert(1)</script>',value:2,threshold:1,operator:'>',passed:true}]}));
  assert.doesNotMatch(html,/<img|<script>/);assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);
});
function savedFixture(){const diagnostic=row({engine_id:"terminal.fixture-v1",source_digest:"c".repeat(64),fingerprint:"d".repeat(64),engine_source_identity:Object.fromEntries(["backtest_engine.py","strategy_signals.py","market_calendar.py","indicator_math.py"].map(k=>[k,"e".repeat(64)])),indicator_contract:{version:"QA"},strategy_params:{window:20,threshold:.015,position_pct:.25,stop_loss_pct:.03}});
 const report={schema_version:"hakimi-terminal-run-v1",status:"COMPLETED",id:"f".repeat(64),run_id:"f".repeat(64),report_hash:"f".repeat(64),task_id:"1".repeat(64),version:1,title:"QA 已完成研究",started_at:"2026-10-30T01:00:00Z",engine_id:diagnostic.engine_id,strategy_id:diagnostic.strategy_id,
   configuration:{engine_id:diagnostic.engine_id,input_id:diagnostic.input_id,strategy_params:copy(diagnostic.strategy_params),fingerprint:diagnostic.fingerprint,engine_source_identity:copy(diagnostic.engine_source_identity),indicator_contract:copy(diagnostic.indicator_contract),initial_cash:10000,risk:{position_pct:25,stop_loss_pct:8,take_profit_pct:0},costs:{fee_rate:.0005,slippage_bps:2}},
   input_summary:{id:diagnostic.input_id,input_id:diagnostic.input_id,source_digest:diagnostic.source_digest,digest:diagnostic.source_digest,symbol:diagnostic.symbol,date_start:"2024-01-01",date_end:diagnostic.cutoff_session,meta:{currency:"USD"}}};return {diagnostic,report};}
test("saved matcher requires full immutable data/rule/parameter/cutoff identities including compatibility fields",()=>{
 const {diagnostic:d,report:r}=savedFixture();assert.equal(candidate.matchesSavedResult(r,d),true);const reordered=copy(r);reordered.configuration.strategy_params=Object.fromEntries(Object.entries(reordered.configuration.strategy_params).reverse());assert.equal(candidate.matchesSavedResult(reordered,d),true);
 for(const corrupt of [v=>v.status="UNKNOWN",v=>v.schema_version="core",v=>v.run_id="2".repeat(64),v=>v.report_hash="2".repeat(64),v=>v.task_id="missing",v=>v.version=null,v=>v.engine_id="core",v=>v.configuration.engine_id="core",v=>v.strategy_id="same-name-other",v=>v.configuration.input_id="2".repeat(64),v=>v.input_summary.id="2".repeat(64),v=>v.input_summary.input_id="2".repeat(64),v=>v.input_summary.source_digest="2".repeat(64),v=>delete v.input_summary.digest,v=>v.input_summary.date_end="2024-08-01",v=>v.configuration.strategy_params.threshold="0.015",v=>delete v.configuration.strategy_params.position_pct,v=>v.configuration.strategy_params.stop_loss_pct=.08,v=>v.configuration.fingerprint="2".repeat(64),v=>delete v.configuration.engine_source_identity['backtest_engine.py'],v=>v.configuration.indicator_contract.version="OTHER"]){const value=copy(r);corrupt(value);assert.equal(candidate.matchesSavedResult(value,d),false);}
 const risk=copy(r);risk.configuration.risk.stop_loss_pct=10;assert.equal(candidate.matchesSavedResult(risk,d),true,"separate execution risk is displayed, not invented as a candidate criterion");
});
test("unique completed match reads original detail before opening and never calls new draft",async()=>{
 const {diagnostic,report}=savedFixture(),reads=[],opened=[],drafts=[];const c=candidate.createSavedResultController({api:async p=>{reads.push(p);return p==='terminal_runs'?{items:[report,{...report,status:'UNKNOWN'}],warnings:[],new_economic_runs:0}:report;},onOpenSaved:(...a)=>opened.push(a),onChoose:d=>drafts.push(d)});
 await c.select(diagnostic);assert.deepEqual(reads,['terminal_runs','terminal_runs/'+report.id]);assert.equal(opened.length,1);assert.equal(opened[0][0].id,report.id);assert.equal(c.state.status,'OPENED');assert.equal(drafts.length,0);
});
test("multiple matches and incomplete unique indexes require explicit choice and show actual risk/costs",async()=>{
 for(const incomplete of [false,true]){const {diagnostic,report}=savedFixture(),other=copy(report);other.id=other.run_id=other.report_hash='2'.repeat(64);other.task_id='3'.repeat(64);other.version=2;other.configuration.risk.stop_loss_pct=10;other.configuration.costs.fee_rate=.001;
 const opened=[],reads=[],items=incomplete?[report]:[report,other],c=candidate.createSavedResultController({api:async p=>{reads.push(p);return p==='terminal_runs'?{items,warnings:incomplete?['one unread record']:[],new_economic_runs:0}:items.find(v=>p.endsWith(v.id));},onOpenSaved:(...a)=>opened.push(a),onChoose:()=>assert.fail('no draft')});await c.select(diagnostic);assert.equal(opened.length,0);assert.equal(c.state.status,'CHOICES');assert.deepEqual(reads,['terminal_runs']);await c.open(items.at(-1).id);assert.equal(opened.length,1);assert.equal(opened[0][2].incompleteIndex,incomplete);
 const html=candidate.savedResultTerms(other);assert.match(html,/执行止损 10%/);assert.match(html,/手续费 0.1%/);assert.doesNotMatch(html,/3%/);}
});
test("zero matches offers an explicit draft; errors never silently become no-history or a draft",async()=>{
 const {diagnostic,report}=savedFixture(),drafts=[];const c=candidate.createSavedResultController({api:async()=>({items:[{...report,status:'UNKNOWN'}],warnings:['unread'],new_economic_runs:0}),onChoose:d=>drafts.push(d)});await c.select(diagnostic);assert.equal(c.state.status,'EMPTY');assert.equal(drafts.length,0);await c.newDraft();assert.equal(drafts.length,1);
 const broken=candidate.createSavedResultController({api:async()=>{throw Error('list offline');},onChoose:()=>assert.fail('must not create')});await broken.select(diagnostic);assert.equal(broken.state.status,'INDEX_ERROR');await broken.newDraft();assert.match(broken.state.error,/list offline/);
});
test("detail failure retries only the original report with the original match and frozen index terms",async()=>{
 const {diagnostic,report}=savedFixture(),reads=[],opened=[];let fail=true;const c=candidate.createSavedResultController({api:async p=>{reads.push(p);if(p==='terminal_runs')return {items:[report],warnings:[],new_economic_runs:0};if(fail)throw Error('detail offline');return report;},onOpenSaved:r=>opened.push(r),onChoose:()=>assert.fail('must not create')});await c.select(diagnostic);assert.equal(c.state.status,'DETAIL_ERROR');fail=false;await c.open(c.state.runId);assert.equal(opened.length,1);assert.deepEqual(reads,['terminal_runs','terminal_runs/'+report.id,'terminal_runs/'+report.id]);
 const drift=copy(report);drift.configuration.risk.stop_loss_pct=9;const refused=candidate.createSavedResultController({api:async p=>p==='terminal_runs'?{items:[report],warnings:[],new_economic_runs:0}:drift,onOpenSaved:()=>assert.fail('index risk changed'),onChoose:()=>{}});await refused.select(diagnostic);assert.equal(refused.state.status,'DETAIL_ERROR');
});
test("changed input/parameters/candidate scope discards both late list and late detail responses",async()=>{
 for(const stage of ['index','detail'])for(const fail of [false,true]){const {diagnostic,report}=savedFixture();let release,reject,scope='first';const c=candidate.createSavedResultController({getScope:()=>scope,api:p=>{if(stage==='detail'&&p==='terminal_runs')return Promise.resolve({items:[report],warnings:[],new_economic_runs:0});return new Promise((a,b)=>{release=a;reject=b;});},onOpenSaved:()=>assert.fail('late result'),onChoose:()=>assert.fail('late draft')});const pending=c.select(diagnostic);await new Promise(r=>setImmediate(r));scope='changed';if(fail)reject(Error('old error'));else release(stage==='index'?{items:[report],warnings:[],new_economic_runs:0}:report);await pending;assert.equal(c.state.status,'IDLE');assert.equal(c.state.matches.length,0);assert.equal(c.state.error,'');}
});
test("different candidate replaces an in-flight lookup and duplicate report identity conflicts are refused",async()=>{
 const a=savedFixture(),b=savedFixture();b.diagnostic.diagnostic_id='4'.repeat(64);b.diagnostic.strategy_params.threshold=.02;b.report.configuration.strategy_params.threshold=.02;const opens=[];let first;let n=0;
 const c=candidate.createSavedResultController({api:p=>p==='terminal_runs'?(++n===1?new Promise(r=>first=r):Promise.resolve({items:[b.report],warnings:[],new_economic_runs:0})):Promise.resolve(b.report),onOpenSaved:r=>opens.push(r),onChoose:()=>{}});const pending=c.select(a.diagnostic);await c.select(b.diagnostic);first({items:[a.report],warnings:[],new_economic_runs:0});await pending;assert.equal(opens.length,1);assert.equal(opens[0].configuration.strategy_params.threshold,.02);
 const drift=copy(a.report);drift.configuration.risk.stop_loss_pct=10;const duplicate=candidate.createSavedResultController({api:async()=>({items:[a.report,drift],warnings:[],new_economic_runs:0}),onOpenSaved:()=>assert.fail('ambiguous id'),onChoose:()=>{}});await duplicate.select(a.diagnostic);assert.equal(duplicate.state.status,'INDEX_ERROR');
});
