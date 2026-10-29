"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const protocol = require("./terminal-quant-ui");
const app = fs.readFileSync(path.join(__dirname,"app.js"),"utf8");
const ui = fs.readFileSync(path.join(__dirname,"terminal-quant-ui.js"),"utf8");
function appFunction(name) {
  const offset = app.indexOf("function " + name + "(");
  assert.ok(offset >= 0,name);
  const start = app.slice(offset-6,offset) === "async " ? offset-6 : offset;
  const next = /\n(?:async )?function \w+\(/g; next.lastIndex=offset+10;
  const match=next.exec(app);
  return app.slice(start,match?.index ?? app.length).trim();
}
function configuration(overrides={}) {
  return {engine_id:protocol.ENGINE,strategy_id:"dual_ma",strategy_params:{fast:20,slow:60},
    risk:{position_pct:25,take_profit_pct:6,stop_loss_pct:8,leverage:1},...overrides};
}
const row = (ts=1000,date="2026-01-02") => ({ts_ms:ts,date,open:100,high:105,low:99,close:102,volume:10});

test("bridge requires exact origin, exact frame source, known schema and kind",() => {
  const source={}; const origin="http://127.0.0.1:8765";
  const message={source,origin,data:{schema:protocol.SCHEMA,kind:"terminal-context",payload:{}}};
  assert.equal(protocol.validMessage(message,source,origin,["terminal-context"]),true);
  for(const bad of [{...message,origin:"http://127.0.0.1:11111"},{...message,source:{}},
    {...message,data:{...message.data,schema:"other"}},{...message,data:{...message.data,kind:"run_order"}},
    {...message,data:{...message.data,token:"must not travel"}}])
    assert.equal(protocol.validMessage(bad,source,origin,["terminal-context"]),false);
});

test("native engine and percent units remain distinct from the equity research core",() => {
  assert.equal(protocol.validConfiguration(configuration()),true);
  assert.equal(protocol.ENGINE,"terminal.causal-long-only-signals-v7");
  assert.equal(protocol.validConfiguration(configuration({engine_id:"terminal.causal-long-only-signals-v6"})),true);
  assert.equal(protocol.validConfiguration(configuration({engine_id:"terminal.causal-long-only-signals-v999"})),false);
  assert.equal(protocol.validConfiguration(configuration({engine_id:"research.accepted-equity"})),false);
  assert.equal(protocol.validConfiguration(configuration({strategy_params:{fast:NaN}})),false);
  assert.equal(protocol.validConfiguration(configuration({risk:{position_pct:25,take_profit_pct:6,stop_loss_pct:8,leverage:2}})),false);
  assert.equal(configuration().risk.position_pct,25);
});

test("replay rows preserve original session dates and reject fabricated/malformed chronology",() => {
  const source=[row(1000,"2026-01-02"),row(2000,"2026-01-05")];
  assert.deepEqual(protocol.chartRows(source).map((item)=>item.date),["2026-01-02","2026-01-05"]);
  assert.throws(()=>protocol.chartRows([{...row(),ts_ms:undefined}]),/时间或价格/);
  assert.throws(()=>protocol.chartRows([row(),row()]),/时间或价格/);
  assert.throws(()=>protocol.chartRows([{...row(),high:90}]),/时间或价格/);
  const replay={symbol:"AAPL",run_id:"run",input_id:"input",report_hash:"hash",meta:{asset_class:"EQUITY",price_basis:"RAW"},rows:source,trades:[]};
  assert.equal(protocol.validReplay(replay),true);
  assert.equal(protocol.validReplay({...replay,meta:{}}),false);
});

test("source identity follows target symbol and never leaks an unrelated chart source",() => {
  assert.equal(protocol.contextSourceId("AAPL",{symbol:"AAPL",source_id:"futu-regular"}),"futu-regular");
  assert.equal(protocol.contextSourceId("AAPL",{symbol:"AAPL",source_id:"futu-all"}),"futu-all");
  assert.equal(protocol.contextSourceId("BTC-USDT",{symbol:"AAPL",source_id:"futu-all"}),"");
  assert.equal(protocol.contextSourceId("AAPL",{symbol:"AAPL",source_id:"futu-all"},true),"");
});

test("explicit completion evidence survives local chart conversion and analysis payload without filling unknown flags", () => {
  const original = [{...row(1000), complete:true, provisional:false, source:"futu"},
    {...row(2000), complete:false, provisional:true}, row(3000), {...row(4000), complete:"true"}];
  const candles = protocol.chartRows(original);
  assert.equal(candles[0].date,original[0].date); assert.equal(candles[0].source,"futu");
  const context = vm.createContext({state:{symbol:"AAPL",bar:"1Dutc",chartDataSymbol:"AAPL",candles,
    drawings:[],stockSession:"regular",chartQuality:{source:"terminal-cache:existing"}},
    frontendMarketAiLocal:()=>({}), visibleCandles:()=>({candles}), latestFibLevels:()=>[], $:()=>null});
  vm.runInContext(appFunction("marketAiPayload"), context);
  const payload = context.marketAiPayload();
  assert.equal(payload.candles[0].date, original[0].date);
  assert.equal(payload.candles[0].source, "futu");
  assert.equal(Object.hasOwn(payload.candles[2], "source"), false);
  assert.equal(payload.candles[0].complete,true); assert.equal(payload.candles[0].provisional,false);
  assert.equal(payload.candles[1].complete,false); assert.equal(payload.candles[1].provisional,true);
  for (const index of [2,3]) {
    assert.equal(Object.hasOwn(payload.candles[index],"complete"),false);
    assert.equal(Object.hasOwn(payload.candles[index],"provisional"),false);
  }
  assert.equal(payload.chart_context.snapshot_source,"terminal-cache:existing");
  assert.equal(original[3].complete,"true");
});

test("analysis payload does not invent date or provider provenance for unknown chart rows", () => {
  const candles=[{ts:1000,open:100,high:105,low:99,close:102,volume:10,date:null,source:undefined,complete:true}];
  const context=vm.createContext({state:{symbol:"AAPL",bar:"5m",chartDataSymbol:"AAPL",candles,
    drawings:[],stockSession:"regular",chartQuality:{source:"unverified-client"}},
    frontendMarketAiLocal:()=>({}),visibleCandles:()=>({candles}),latestFibLevels:()=>[],$:()=>null});
  vm.runInContext(appFunction("marketAiPayload"),context);
  const payload=context.marketAiPayload();
  assert.equal(Object.hasOwn(payload.candles[0],"date"),false);
  assert.equal(Object.hasOwn(payload.candles[0],"source"),false);
  assert.equal(payload.candles[0].complete,true);
});

test("current context reads the edited parameter form and radar target safely",() => {
  const elements={strategySelect:{value:"dual_ma"},positionInput:{value:"25"},takeProfitInput:{value:"6"},stopLossInput:{value:"8"},leverageInput:{value:"1"},
    directionMode:{value:"LONG_ONLY"},riskSource:{value:"MANUAL"},riskValueMode:{value:"PCT"},trailingTakeEnabled:{checked:false},trailingStopEnabled:{checked:false},strategyOrderType:{value:"CURRENT"},marginMode:{value:"CROSS"}};
  const state={symbol:"AAPL",bar:"1Dutc",stockSession:"all",strategies:[{id:"dual_ma",name:"双均线",params:{fast:20,slow:60}}],
    terminalLocalMarket:{symbol:"AAPL",source_id:"futu-regular",meta:{session:"regular"}},selectedAnomaly:{symbol:"BTC-USDT"}};
  const context=vm.createContext({state,$:(id)=>elements[id],HakimiTerminalQuantProtocol:protocol,currentAiResearchEvidence:()=>null,
    document:{querySelectorAll:()=>[{dataset:{strategyParam:"fast"},value:"7"},{dataset:{strategyParam:"slow"},value:"19"}]}});
  vm.runInContext(appFunction("currentTerminalResearchContext"),context);
  const direct=vm.runInContext('currentTerminalResearchContext("strategy")',context);
  assert.equal(direct.source_id,"futu-regular"); assert.equal(direct.session,"regular"); assert.equal(direct.strategy_params.fast,7); assert.equal(direct.strategy_params.slow,19);
  const radar=vm.runInContext('currentTerminalResearchContext("radar")',context);
  assert.equal(radar.symbol,"BTC-USDT");assert.equal(radar.source_id,"");assert.equal(radar.bar,"待核对");
});

function dispatchContext(extra={}) {
  const start=ui.indexOf("async function dispatch(action, id, target)");
  const end=ui.indexOf('    host.addEventListener("click"',start);
  const context=vm.createContext(extra);
  vm.runInContext(ui.slice(start,end),context);
  return context;
}

function uiFunction(name) {
  const offset=ui.indexOf("function " + name + "(");assert.ok(offset>=0,name);
  const start=ui.slice(offset-6,offset)==="async "?offset-6:offset;
  const next=/\n    (?:async )?function \w+\(/g;next.lastIndex=offset+10;
  const match=next.exec(ui);return ui.slice(start,match?.index??ui.length).trim();
}

test("market read failures show structured session guidance or native errors as plain text without retry",async () => {
  const cases = [
    [{info:{code:"PermissionError",message:"量化模块操作未完成",detail:"session_token_required:请重新打开量化模块"}},"后台已重启，请刷新整个交易台后继续。已保存任务和结果仍保留。"],
    [{info:{message:"本地来源不可用",detail:"请核对已保存的日线"}},"本地来源不可用；请核对已保存的日线"],
    [new Error("连接暂不可用"),"连接暂不可用"],
    [{info:{message:"<img src=x onerror=alert(1)>"}},"<img src=x onerror=alert(1)>"],
    [null,"本地行情读取未完成，请查看设置与日志中的操作记录。"],
  ];
  for (const [failure,expected] of cases) {
    const panel={textContent:"",innerHTML:"unchanged fixture"},tasks=[{id:"saved-task"}],runs=[{id:"saved-result"}];
    const state={marketRequest:0,market:{symbol:"HK.00836"},tasks,runs};
    let calls=0;
    const context=vm.createContext({state,$:()=>panel,value:id=>id==="tq-symbol"?"HK.00836":"",notify(){},
      api:async()=>{calls++;throw failure;}});
    vm.runInContext(uiFunction("operationErrorText")+"\n"+uiFunction("readMarket"),context);
    await context.readMarket();
    assert.equal(panel.textContent,expected);
    assert.equal(panel.innerHTML,"unchanged fixture");
    assert.equal(calls,1);
    assert.equal(state.market,null);
    assert.equal(state.tasks,tasks); assert.equal(state.runs,runs);
  }
});

test("dashboard and daily page retain their headers while task and result links retain anchors",() => {
  const scrolled=[];const host={hidden:false};const windowScroll=[];
  const executionHost={hidden:true},dailyHost={hidden:true,scrollIntoView:()=>scrolled.push("daily")},brokerHost={hidden:true};
  let dailyHides=0,brokerHides=0,brokerReads=0;
  const panels=Object.fromEntries(["tasks","results"].map(name=>[name,{style:{},scrollIntoView:()=>scrolled.push(name)}]));
  const context=vm.createContext({state:{visible:true,loaded:true},coreMain:{hidden:true},host,executionHost,dailyHost,brokerHost,
    brokerUI:{reveal:async()=>{brokerReads++;},hide:()=>{brokerHides++;}},
    dailyUI:{reveal:async()=>{},hide:()=>dailyHides++},executionUI:{refresh:async()=>{},reveal:()=>scrolled.push("execution")},location:{hash:"#dashboard"},
    history:{pushState(){},replaceState(){}},$:id=>id==="terminalQuantWorkspace"?host:{closest:()=>panels[id==="tq-tasks"?"tasks":"results"]},
    window:{scrollTo:options=>windowScroll.push(JSON.parse(JSON.stringify(options)))},navRoot:{closest:()=>({getBoundingClientRect:()=>({height:48.2})})},
    syncUnifiedNavigation(){},requestAnimationFrame:callback=>callback()});
  vm.runInContext(uiFunction("show"),context);
  vm.runInContext('show("dashboard");show("tasks");show("results")',context);
  assert.deepEqual(windowScroll,[{top:0,left:0,behavior:"auto"}]);assert.deepEqual(scrolled,["tasks","results"]);
  assert.equal(panels.tasks.style.scrollMarginTop,"57px");assert.equal(panels.results.style.scrollMarginTop,"57px");
  vm.runInContext('show("daily")',context);
  assert.equal(host.hidden,true);assert.equal(dailyHost.hidden,false);assert.equal(executionHost.hidden,true);
  vm.runInContext('show("execution")',context);
  assert.equal(dailyHides,1);assert.equal(dailyHost.hidden,true);assert.equal(executionHost.hidden,false);
  assert.deepEqual(windowScroll,Array.from({length:3},()=>({top:0,left:0,behavior:"auto"})));
  assert.deepEqual(scrolled,["tasks","results","execution"]);
  vm.runInContext('show("broker")',context);
  assert.equal(brokerReads,1);assert.equal(brokerHost.hidden,false);assert.equal(executionHost.hidden,true);assert.equal(host.hidden,true);
  vm.runInContext('show("execution")',context);
  assert.equal(brokerHides,1);assert.equal(brokerHost.hidden,true);assert.equal(executionHost.hidden,false);
});

test("old task and unverified records never masquerade as completed result summaries",async () => {
  for(const detail of [
    {resource:"tasks",verification_status:"VERIFIED_RECORD",strategy_id:"macd",version:1,state:"ENABLED",task:{strategy_params:{fast:13}}},
    {resource:"runs",verification_status:"METADATA_ONLY",status:"COMPLETED"},
    {resource:"runs",verification_status:"VERIFIED_RECORD",status:"UNKNOWN",report:{status:"UNKNOWN"}},
    {resource:"runs",verification_status:"VERIFIED_RECORD",status:"COMPLETED",report:{run_id:"actual-saved-run"}}
  ]) {
    const panel={innerHTML:"previous detail",textContent:""},calls=[];
    let resultRenders=0;
    const context=vm.createContext({state:{oldDetail:{}},$:()=>panel,esc:String,warning:()=>"",validReplay:()=>false,
      api:async route=>{calls.push(route);return {id:"opaque-read-only-id",label:"saved",...detail};},
      HakimiTerminalResultSummary:{renderResultSummary:()=>{resultRenders++;return "VERIFIED_RESULT_SUMMARY";}}});
    vm.runInContext(uiFunction("readOldDetail"),context);
    await context.readOldDetail("workspace/"+detail.resource+"/record");
    const completed=detail.resource==="runs"&&detail.status==="COMPLETED"&&detail.verification_status==="VERIFIED_RECORD";
    assert.equal(resultRenders,completed?1:0);
    assert.equal(calls.length,1);assert.equal(typeof calls[0],"string");
    if(detail.resource==="tasks") {
      assert.match(panel.innerHTML,/已保存任务设置/);assert.match(panel.innerHTML,/旧结果/);
      assert.doesNotMatch(panel.innerHTML,/结果校验值|保存的运行标识|VERIFIED_RESULT_SUMMARY/);
    }
  }
});

test("switching old workspaces invalidates a pending old-record response",async () => {
  let finishDetail;
  const panel={innerHTML:"",textContent:""},state={oldWorkspaces:[{id:"new-workspace"}]};
  const context=vm.createContext({state,$:()=>panel,esc:String,warning:()=>"",value:()=>"new-workspace",notify(){},
    api:route=>route.endsWith("/old-record")?new Promise(resolve=>{finishDetail=resolve;}):Promise.resolve({items:[],physical_root:"new"})});
  vm.runInContext(uiFunction("readOldWorkspace")+"\n"+uiFunction("readOldDetail"),context);
  const pending=context.readOldDetail("old-workspace/tasks/old-record");
  await context.readOldWorkspace();finishDetail({resource:"tasks",label:"stale task"});await pending;
  assert.equal(state.oldDetail,null);assert.doesNotMatch(panel.innerHTML,/stale task/);
});

test("frozen replay and exit refresh the original desktop summary for the actual chart symbol",async () => {
  const elements=new Map();const cleared=[];const get=id=>{if(!elements.has(id))elements.set(id,{dataset:{},hidden:false,textContent:"",value:"",classList:{remove(){}}});return elements.get(id);};
  const originalViewport={visible:96,offset:17},reloads=[];
  const runtime={symbolVersion:0,chartUserZoomed:true};
  const state={symbol:"AAPL",bar:"1Dutc",stockSession:"regular",desktop:{},chartView:{...originalViewport},candles:[],chartMode:"candles",replay:{active:true,timer:101}};
  const markets=[{symbol:"AAPL",type:"stock"}];
  const replay={symbol:"BTC-USDT",run_id:"run",input_id:"input",report_hash:"hash",meta:{asset_class:"CRYPTO",price_basis:"RAW",session:"utc"},rows:[row()],trades:[]};
  const noop=()=>{};
  const context=vm.createContext({state,markets,replay,HakimiTerminalQuantProtocol:protocol,$:get,runtime,clearInterval:id=>cleared.push(id),window:{HAKIMI_RUNTIME_MODE:{localOnly:true}},
    document:{querySelectorAll:()=>[],querySelector:()=>null},clearSymbolTasks:noop,abortMarketRequests:noop,setInterfaceView:noop,syncWorkspaceNav:noop,
    syncTimeframeTabs:noop,syncStockSessionTabs:noop,renderMarkets:noop,syncActiveSymbolHeader:noop,priceText:String,renderChartQuality:noop,
    renderChartStrategyOverlay:noop,requestAnimationFrame:noop,drawChart:noop,renderInterfaceView:noop,currentMarket:()=>markets.find(item=>item.symbol===state.symbol),
    marketTypeLabel:market=>market.type==="crypto"?"数字资产":"股票",setLamp:noop,futuOpenDOnline:()=>false,renderStrategyCommandStrip:noop,
    loadTerminalLocalMarket:()=>new Promise(resolve=>reloads.push(resolve)),showTerminalLocalError:noop,resetAiResearchContext:noop,renderBook:noop,renderTrades:noop,
    renderFrozenReplaySummary:noop,renderSideInsights:noop,renderLiveSourceBar:noop});
  vm.runInContext(appFunction("frozenReplayPresentation")+"\n"+appFunction("futuStatusPresentation")+"\n"+appFunction("renderDesktopStatus")+"\n"+appFunction("applyFrozenQuantReplay")+"\n"+appFunction("exitFrozenQuantReplay"),context);
  vm.runInContext("applyFrozenQuantReplay(replay)",context);
  assert.equal(state.symbol,"BTC-USDT");assert.equal(get("desktopSession").textContent,"数字资产 / BTC-USDT");
  assert.equal(state.replay.active,false);assert.equal(state.replay.timer,null);assert.deepEqual(cleared,[101]);
  assert.deepEqual(JSON.parse(JSON.stringify(state.beforeFrozenQuantReplay.chartView)),originalViewport);
  assert.notEqual(state.beforeFrozenQuantReplay.chartView,state.chartView);
  assert.equal(state.beforeFrozenQuantReplay.chartUserZoomed,true);
  assert.equal(state.chartView.visible,1);assert.equal(state.chartView.offset,0);
  state.chartView.visible=44;state.chartView.offset=5;runtime.chartUserZoomed=false;
  state.replay={active:true,timer:202};
  vm.runInContext("exitFrozenQuantReplay()",context);
  assert.equal(state.symbol,"AAPL");assert.equal(get("desktopSession").textContent,"股票 / AAPL");
  assert.deepEqual(cleared,[101,202]);assert.equal(state.replay.active,false);assert.equal(state.replay.timer,null);
  assert.deepEqual(JSON.parse(JSON.stringify(state.chartView)),originalViewport);assert.equal(runtime.chartUserZoomed,true);
  // Loading fresh local candles may reset the chart before its promise settles.
  state.chartView={visible:220,offset:0};runtime.chartUserZoomed=false;
  reloads[0]();await Promise.resolve();
  assert.deepEqual(JSON.parse(JSON.stringify(state.chartView)),originalViewport);assert.equal(runtime.chartUserZoomed,true);
  // Even a newer selection of the same symbol must win over a late restore.
  vm.runInContext("applyFrozenQuantReplay(replay);exitFrozenQuantReplay()",context);
  runtime.symbolVersion+=1;state.chartView={visible:72,offset:3};runtime.chartUserZoomed=false;
  reloads[1]();await Promise.resolve();
  assert.deepEqual(state.chartView,{visible:72,offset:3});assert.equal(runtime.chartUserZoomed,false);
});

test("native parameter editor renders only declared signal keys and leaves risk in its own controls",() => {
  const entry={id:"dual_ma",name:"双均线",params:{fast:20,slow:60,position_pct:0.25,stop_loss_pct:0.08},
    parameter_fields:[{key:"fast",label:"快均线"},{key:"slow",label:"慢均线"}],capability:{backtest_supported:true,new_research_allowed:true}};
  const elements={"tq-strategy-note":{},"tq-save-task":{},"tq-params":{},"tq-position":{value:25},"tq-stop":{value:8}};
  const context=vm.createContext({state:{catalog:[entry]},value:()=>"dual_ma",$:id=>elements[id],esc:String,researchBlocker:protocol.researchBlocker,
    parameterUnits:protocol.parameterUnits,updatePreflight(){}});
  vm.runInContext(uiFunction("renderParams"),context);vm.runInContext("renderParams()",context);
  const keys=[...elements["tq-params"].innerHTML.matchAll(/data-tq-param="([^"]+)"/g)].map(match=>match[1]);
  assert.deepEqual(keys,["fast","slow"]);assert.equal(elements["tq-position"].value,25);assert.equal(elements["tq-stop"].value,8);
});

test("comparison signal fields exclude native canonical risk defaults while preserving core fields and frozen detail",() => {
  const catalog=[{id:"dual_ma",parameter_fields:[{key:"fast"},{key:"slow"}]}];
  const native={engine_id:protocol.ENGINE,configuration:{strategy_id:"dual_ma",strategy_params:{fast:10,slow:25,position_pct:0.25,stop_loss_pct:0.03},risk:{position_pct:10,stop_loss_pct:8}}};
  const before=JSON.stringify(native);
  assert.deepEqual(protocol.comparisonSignalParams(native,catalog),{fast:10,slow:25});
  assert.equal(JSON.stringify(native),before);assert.equal(native.configuration.risk.position_pct,10);
  const core={engine_id:"accepted.stock.engine",configuration:{strategy_params:{fast_window:10,position_pct:0.4}}};
  assert.equal(protocol.comparisonSignalParams(core,catalog),core.configuration.strategy_params);
});

test("unified task and result rows retain both engines and their distinct detail routes",() => {
  const native=Object.freeze({id:"same",family_id:"family",title:"MACD任务",strategy_id:"macd",version:2,state:"ENABLED",risk:{},status:"COMPLETED"});
  const imported=Object.freeze({id:"same",title:"股票双均线",strategy:"price.dual_ma@1",state:"PAUSED",revisions:[{},{}]});
  const state={tasks:[native],coreTasks:[imported],runs:[native],coreRuns:[{id:"core-run",task_display_name:"股票结果",strategy:{title:"股票双均线"},data_kind:"SYNTHETIC_TEST"}],
    catalog:[{id:"macd",capability:{backtest_supported:true,new_research_allowed:true}}],coreStrategies:[],comparison:new Set()};
  const elements={"tq-tasks":{},"tq-runs":{},"tq-core-comparison":{value:""}};
  const context=vm.createContext({state,$:id=>elements[id],value:id=>elements[id].value,esc:String,fmt:String,identity:row=>row.id,
    researchBlocker:protocol.researchBlocker,button:(label,action,id)=>`[${action}:${id}:${label}]`});
  vm.runInContext(uiFunction("renderTasks")+"\n"+uiFunction("renderRuns"),context);
  vm.runInContext("renderTasks();renderRuns()",context);
  assert.match(elements["tq-tasks"].innerHTML,/MACD任务/);assert.match(elements["tq-tasks"].innerHTML,/股票双均线/);
  assert.match(elements["tq-tasks"].innerHTML,/core-task:same/);assert.match(elements["tq-tasks"].innerHTML,/edit:family/);
  assert.match(elements["tq-runs"].innerHTML,/core-result:core-run/);assert.match(elements["tq-runs"].innerHTML,/result:same/);
  assert.match(elements["tq-runs"].innerHTML,/虚构教学数据/);assert.equal(state.tasks[0],native);assert.equal(state.coreTasks[0],imported);
});

test("core detail callback receives only a verified core record id and never a native object",async () => {
  const calls=[];let hidden=0;
  const context=dispatchContext({state:{tasks:[{id:"native-id"}],coreTasks:[{id:"core-task-id"}],coreRuns:[{id:"core-run-id"}]},
    hide:()=>hidden++,openCoreTask:async id=>calls.push(["task",id]),openCoreRun:async id=>calls.push(["run",id])});
  await assert.rejects(vm.runInContext('dispatch("core-task","native-id",{})',context),/未找到/);
  assert.equal(hidden,0);assert.equal(calls.length,0);
  await vm.runInContext('dispatch("core-task","core-task-id",{})',context);
  await vm.runInContext('dispatch("core-result","core-run-id",{})',context);
  assert.equal(hidden,2);assert.deepEqual(calls,[["task","core-task-id"],["run","core-run-id"]]);
});

test("same-symbol context source change overrides stale inner source selection",async () => {
  const input={value:"AAPL"}; let selected;
  const context=dispatchContext({state:{context:{symbol:"AAPL",source_id:"new-futu-all"},market:{symbol:"AAPL",source_id:"old-regular"}},
    $:()=>input,readMarket:async(source)=>{selected=source;}});
  await vm.runInContext('dispatch("context-market","",null)',context);
  assert.equal(selected,"new-futu-all");assert.equal(input.value,"AAPL");
});

test("unknown terminal run is not announced as complete or opened as a verified result",async () => {
  let shown=0;const notices=[];
  const context=dispatchContext({state:{tasks:[{id:"task",strategy_id:"dual_ma"}],catalog:[{id:"dual_ma",capability:{backtest_supported:true,new_research_allowed:true}}]},
    identity:(row)=>row.id,researchBlocker:protocol.researchBlocker,act:async(_action,_payload,options)=>{
      const run={id:"operation",status:"UNKNOWN",message:"结果待核对"};options.onCommitted(run);return options.onSuccess(run);
    },$:()=>({hidden:false}),text:value=>typeof value==="string"&&value.length>0,
    api:async()=>({status:"DATA_READY"}),preflightHtml:()=>"数据足够",
    refreshRecords:async()=>{},showRun:async()=>shown++,notify:(message,error)=>notices.push({message,error})});
  vm.runInContext(uiFunction("recordRunOutcome")+"\n"+uiFunction("readRunOutcome"),context);
  await vm.runInContext('dispatch("run","task",{})',context);
  assert.equal(shown,0);assert.deepEqual(notices,[{message:"结果待核对",error:true}]);
});

test("historical-only strategy remains viewable but cannot start new research",async () => {
  const entry={id:"trend_pullback",capability:{backtest_supported:true,new_research_allowed:false,paper_blocker:"仅保留旧记录"}};
  assert.equal(protocol.researchBlocker(entry),"仅保留旧记录");
  assert.ok(protocol.researchBlocker(undefined));
  let called=0; const notices=[];
  const context=dispatchContext({state:{tasks:[{id:"task",strategy_id:entry.id}],catalog:[entry]},
    identity:(row)=>row.id,researchBlocker:protocol.researchBlocker,act:async()=>called++,notify:(message)=>notices.push(message)});
  await vm.runInContext('dispatch("run","task",{})',context);
  assert.equal(called,0);assert.deepEqual(notices,["仅保留旧记录"]);
});

test("imported price reuse requires an available input and explicit confirmation, then selects only the returned input",async () => {
  const state={coreInputs:[{id:"accepted-price",available:true},{id:"synthetic-price",available:false,blockers:["synthetic"]}]};
  let selected="synthetic-price", confirmed=true,refreshes=0;const calls=[],notices=[],selections=[];
  const context=dispatchContext({state,identity:row=>row.id,value:()=>selected,$:()=>({checked:confirmed}),notify:(message,error)=>notices.push({message,error}),
    act:async(action,payload,options)=>{calls.push({action,payload:JSON.parse(JSON.stringify(payload))});await options.onSuccess({input_id:"terminal-input"});},
    refreshAll:async()=>refreshes++,renderInputs:id=>selections.push(id)});
  await vm.runInContext('dispatch("import-core-input","",{})',context);
  assert.equal(calls.length,0);assert.equal(notices.at(-1).error,true);
  selected="accepted-price";confirmed=false;
  await vm.runInContext('dispatch("import-core-input","",{})',context);assert.equal(calls.length,0);
  confirmed=true;await vm.runInContext('dispatch("import-core-input","",{})',context);
  assert.deepEqual(calls,[{action:"terminal_import_core_input",payload:{input_id:"accepted-price"}}]);
  assert.equal(refreshes,1);assert.deepEqual(selections,["terminal-input"]);assert.match(notices.at(-1).message,/未运行回测/);
});

test("local and frozen daily sources cannot pretend to switch intraday sessions",() => {
  const state={symbol:"AAPL",bar:"1Dutc",stockSession:"regular"};const status={textContent:""};let synced=0;
  const context=vm.createContext({state,isStockMarket:()=>true,window:{HAKIMI_RUNTIME_MODE:{localOnly:true}},$:()=>status,
    syncStockSessionTabs:()=>synced++});
  vm.runInContext(appFunction("selectStockSession"),context);
  vm.runInContext('selectStockSession("pre")',context);
  assert.equal(state.bar,"1Dutc");assert.equal(state.stockSession,"regular");assert.equal(synced,1);assert.match(status.textContent,/来源选择/);
  context.window.HAKIMI_RUNTIME_MODE.localOnly=false; state.frozenQuantReplay={};
  vm.runInContext('selectStockSession("post")',context);
  assert.equal(state.bar,"1Dutc");assert.equal(state.stockSession,"regular");assert.match(status.textContent,/退出复盘/);
});

test("parameter copy uses the normalized original catalog and refuses incompatible risk without mutation",() => {
  const keys=["strategySelect","positionInput","takeProfitInput","stopLossInput","leverageInput","riskSource","riskValueMode","directionMode","trailingTakeEnabled","trailingStopEnabled","strategyOrderType","marginMode","strategyAnalysis"];
  const elements=Object.fromEntries(keys.map(key=>[key,{value:"old",checked:true,textContent:""}]));
  const params={fast:8,slow:30,atr_window:14,min_atr_pct:0,max_atr_pct:10,max_extension_pct:5};
  const inputs=Object.keys(params).map(key=>({dataset:{strategyParam:key},value:"old"}));
  const state={strategies:[{id:"volume_trend",params}]};
  const config=configuration({strategy_id:"volume_trend",strategy_params:params});
  const context=vm.createContext({state,config,HakimiTerminalQuantProtocol:protocol,$:id=>elements[id],document:{querySelectorAll:()=>inputs},
    renderStrategyCards(){},syncRiskPlaceholders(){},renderStrategyCommandStrip(){},HakimiQuantModule:{select(){}},setInterfaceView(){},focusModule(){}});
  vm.runInContext(appFunction("copyFrozenTerminalParameters"),context);
  for (const risk of [{position_pct:0.5},{take_profit_pct:81},{stop_loss_pct:81}]) {
    context.config={...config,risk:{...config.risk,...risk}};
    assert.throws(()=>vm.runInContext('copyFrozenTerminalParameters(config)',context),/超出范围/);
    assert.equal(elements.strategySelect.value,"old");assert.ok(inputs.every(input=>input.value==="old"));
  }
  context.config=config;vm.runInContext('copyFrozenTerminalParameters(config)',context);
  assert.equal(elements.strategySelect.value,"volume_trend");
  for(const input of inputs) assert.equal(input.value,String(params[input.dataset.strategyParam]));
  assert.equal(elements.positionInput.value,25);assert.match(elements.strategyAnalysis.textContent,/费用仍保留/);
});

test("delayed previous market response cannot overwrite a frozen replay",async () => {
  const frozen=[{...row(),ts:1000}];const state={frozenQuantReplay:{run_id:"sealed"},candles:frozen};
  const context=vm.createContext({state});
  vm.runInContext(appFunction("applyChartRows"),context);
  let resolve;const pending=new Promise(done=>resolve=done);
  const oldRequest=pending.then(()=>vm.runInContext('applyChartRows({symbol:"AAPL",bar:"1Dutc",rows:[]})',context));
  resolve();assert.equal(await oldRequest,false);assert.equal(state.candles,frozen);assert.equal(state.frozenQuantReplay.run_id,"sealed");
});

test("choosing a different symbol exits replay and restores the local data path",() => {
  const loads=[],cleared=[];const elements={terminalReplayNotice:{hidden:false},toggleReplay:{classList:{remove(){}}}};
  const state={symbol:"AAPL",bar:"1Dutc",frozenQuantReplay:{run_id:"sealed"},beforeFrozenQuantReplay:{symbol:"BTC-USDT",bar:"1Dutc",candles:[]},chartView:{},candles:[],replay:{active:true,timer:303}};
  const context=vm.createContext({state,runtime:{symbolVersion:0,stockQuoteSeq:0},clearInterval:id=>cleared.push(id),window:{HAKIMI_RUNTIME_MODE:{localOnly:true}},
    $:(id)=>elements[id],resetAiResearchContext(){},clearSymbolTasks(){},abortMarketRequests(){},renderMarkets(){},syncTimeframeTabs(){},syncStockSessionTabs(){},
    loadTerminalLocalMarket:(symbol,version)=>{loads.push({symbol,version});return Promise.resolve();},showTerminalLocalError(){}});
  vm.runInContext(appFunction("exitFrozenQuantReplay")+"\n"+appFunction("selectSymbol"),context);
  vm.runInContext('selectSymbol("NVDA")',context);
  assert.equal(state.frozenQuantReplay,null);assert.equal(state.symbol,"NVDA");assert.equal(state.bar,"1Dutc");
  assert.equal(elements.terminalReplayNotice.hidden,true);assert.equal(loads.length,1);assert.equal(loads[0].symbol,"NVDA");
  assert.deepEqual(cleared,[303]);assert.equal(state.replay.active,false);assert.equal(state.replay.timer,null);
});

test("switching BTC to local AAPL renders saved candles and empty stock book/log without a live quote",async () => {
  const elements=new Map(),errors=[],requests=[];let draws=0;
  const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:"",textContent:"",hidden:true,value:"",className:""});return elements.get(id);};
  const state={symbol:"BTC-USDT",bar:"1Dutc",chartView:{},candles:[{...row(),ts:1000}],stockPriceLog:[],
    stockQuoteContext:{symbol:"BTC-USDT",last:60000,source:"old-btc"},terminalLocalSources:{},lastPrice:60000,
    strategies:[{id:"dual_ma",name:"双均线",params:{fast:20,slow:60}}]};
  for(const [id,value] of Object.entries({strategySelect:"dual_ma",positionInput:"20",takeProfitInput:"0",stopLossInput:"8",leverageInput:"1",
    directionMode:"LONG_ONLY",riskSource:"MANUAL",riskValueMode:"PCT",strategyOrderType:"CURRENT",marginMode:"CROSS"})) get(id).value=value;
  const market={ok:true,symbol:"AAPL",source_id:"futu-regular",rows:[row(1000),row(2000,"2026-01-05")],
    meta:{session:"regular",price_basis:"RAW",asset_class:"EQUITY"},quality:{status:"REVIEW",blockers:[]},
    available_sources:[{source_id:"futu-regular",provider:"Futu",session:"regular",completed_count:44},
      {source_id:"yahoo-adjusted",provider:"YahooAdjusted",session:"regular",completed_count:501},
      {source_id:"futu-all",provider:"Futu",session:"all",completed_count:902}]};
  const noop=()=>{};
  const context=vm.createContext({state,runtime:{symbolVersion:0,stockQuoteSeq:0},window:{HAKIMI_RUNTIME_MODE:{localOnly:true}},HakimiTerminalQuantProtocol:protocol,
    $:get,resetAiResearchContext:noop,currentAiResearchEvidence:()=>null,document:{querySelectorAll:()=>[]},api:async url=>{requests.push(url);return market;},
    currentMarket:()=>({symbol:"AAPL",type:"stock",price:"--",source:"local_history"}),isStockMarket:()=>state.symbol==="AAPL",
    clearSymbolTasks:noop,abortMarketRequests:noop,renderMarkets:noop,syncTimeframeTabs:noop,syncStockSessionTabs:noop,syncActiveSymbolHeader:noop,
    renderChartQuality:noop,loadDrawings:noop,drawChart:()=>draws++,renderChartStrategyOverlay:noop,renderStockMicroSignal:noop,
    priceText:String,escapeHtml:String,number:String,compact:String,cssMove:()=>"flat",showTerminalLocalError:error=>errors.push(error.message),renderSideInsights:noop,renderLiveSourceBar:noop});
  const actual=["numericMarketValue","stockQuoteContextSource","stockQuoteContextForMarket","activeStockPriceLogRows","renderStockOrderBook","renderBook","renderStockPriceLog","renderTrades","loadTerminalLocalMarket","selectSymbol","currentTerminalResearchContext"];
  vm.runInContext(actual.map(appFunction).join("\n"),context);vm.runInContext('selectSymbol("AAPL")',context);
  await new Promise(setImmediate);
  assert.deepEqual(errors,[]);assert.deepEqual(requests,["/api/local/terminal-market?symbol=AAPL"]);
  assert.equal(state.symbol,"AAPL");assert.equal(state.stockQuoteContext,null);assert.equal(state.lastPrice,0);
  assert.equal(state.candles.length,2);assert.equal(state.stockSession,"regular");assert.equal(draws,1);
  assert.match(get("chartStatus").textContent,/AAPL 本地日线/);assert.match(get("trades").innerHTML,/等待股票报价/);
  assert.match(get("bids").innerHTML,/--/);assert.match(get("terminalLocalSource").innerHTML,/yahoo-adjusted/);
  assert.equal(state.chartQuality.realtime,false);assert.equal(get("priceChange").textContent,"历史收盘 · 非实时");
  const research=vm.runInContext('currentTerminalResearchContext("chart")',context);
  assert.equal(research.symbol,"AAPL");assert.equal(research.source_id,"futu-regular");assert.equal(research.session,"regular");
  assert.equal(research.strategy_params.fast,20);assert.equal(research.strategy_params.slow,60);
  assert.equal(research.risk.position_pct,20);assert.equal(research.risk.stop_loss_pct,8);assert.equal(research.blockers.length,0);
});

test("AI and current-market requests require explicitly leaving frozen replay",() => {
  const state={frozenQuantReplay:{run_id:"sealed"}};
  const context=vm.createContext({state,URL,location:{origin:"http://127.0.0.1:8765"}});
  vm.runInContext(appFunction("assertTerminalReplayRequest"),context);
  for(const route of ["/api/ai/market/dual-analysis","/api/market/chart-candles","/api/strategy/backtest/preview"])
    assert.throws(()=>vm.runInContext(`assertTerminalReplayRequest(${JSON.stringify(route)})`,context),/退出/);
  assert.doesNotThrow(()=>vm.runInContext('assertTerminalReplayRequest("/api/local/terminal-account")',context));
  state.frozenQuantReplay=null;
  assert.doesNotThrow(()=>vm.runInContext('assertTerminalReplayRequest("/api/market/chart-candles")',context));
});

test("all frozen sources isolate real cached quotes and update every selected-symbol summary at the historical cutoff",async()=>{
  for(const source of ["JUDGMENT_FROZEN_INPUT","BACKTEST","STRUCTURE_FROZEN","EXIT_RESEARCH_FROZEN"]){
    const elements=new Map(),metaElement={textContent:"股票 / 离线种子"},captions=new Map();
    const get=id=>{if(!elements.has(id))elements.set(id,{dataset:{},hidden:false,textContent:"old AAPL 338.92",innerHTML:"old AAPL 343.06",className:"",value:"",title:"",classList:{remove(){}},parentElement:{querySelector:()=>{if(!captions.has(id))captions.set(id,{textContent:"常规高"});return captions.get(id);}}});return elements.get(id);};
    const markets=[{symbol:"AAPL",type:"stock",source:"offline-seed",price:"338.92",high24h:343.06,low24h:330,vol24h:18000000,bidPx:338,askPx:339},
      {symbol:"HK.00836",type:"stock",source:"offline-seed",price:"22",high24h:22.264,low24h:21.736,vol24h:18000000,bidPx:21.9,askPx:22.1}];
    const state={symbol:"AAPL",bar:"1Dutc",chartMode:"candles",chartView:{visible:96,offset:17},candles:[],replay:{active:true,timer:7,index:2},sideInsight:"volatility",lastPrice:338.92,
      stockQuoteContext:{symbol:"AAPL",last:338.92,source:"futu"},stockPriceLog:[{symbol:"AAPL",price:338.92}],orderBook:{asks:[{price:343.06}],bids:[{price:338.92}]},trades:[{price:338.92}],
      futuDeep:{symbol:"HK.00836",order_book:{bids:[{price:24,volume:9}]}},research:{news:[{title:"future news"}]},stockAsyncResearch:{symbol:"HK.00836",status:"ready",detail:"current cache 2026-10-20 news"},chartQuality:{sourceText:"current cache 2026-10-20"},desktop:{},paper:{symbol:"AAPL",equity:1000,take_profit_price:343.06,stop_loss_price:338.92,ai_analysis:{}}};
    const frozenRows=[{...row(1,"2026-09-17"),open:18,high:18.8,low:17,close:18.2,volume:10000},{...row(2,"2026-09-18"),open:19,high:19.5,low:18.4,close:19.2233,volume:12000},{...row(3,"2026-09-21"),open:29,high:30,low:28,close:29,volume:50000}];
    const hash="a".repeat(64),replay={source,symbol:"HK.00836",input_id:hash,meta:{asset_class:"EQUITY",price_basis:"RAW",session:"regular",provider:"frozen-provider"},rows:frozenRows,trades:[]};
    if(source==="JUDGMENT_FROZEN_INPUT")Object.assign(replay,{judgment_id:hash,record_hash:hash});
    else if(source==="STRUCTURE_FROZEN")Object.assign(replay,{record_hash:hash,structure_marks:[]});
    else if(source==="EXIT_RESEARCH_FROZEN")Object.assign(replay,{record_hash:hash,exit_run_id:hash,structure_marks:[],exit_paths:[]});
    else Object.assign(replay,{run_id:hash,report_hash:hash,trades:[{date:"2026-09-17",side:"BUY"},{date:"2026-09-21",side:"SELL"}]});
    const noop=()=>{};let callbacks,loads=0,resolveMarkets,marketRequests=0;const runtime={symbolVersion:0,chartUserZoomed:true};let context;
    context=vm.createContext({state,markets,replay,runtime,HakimiTerminalQuantProtocol:protocol,$:get,clearInterval:noop,
      document:{querySelectorAll:()=>[],querySelector:s=>s===".symbol-meta"?metaElement:null},window:{HAKIMI_RUNTIME_MODE:{localOnly:true},HakimiResearchChart:{configure:(value,options)=>{if(value)callbacks=options;}}},
      priceText:String,number:String,compact:String,escapeHtml:String,cssMove:()=>"flat",previewPriceForSymbol:()=>999,api:()=>{marketRequests++;return new Promise(resolve=>{resolveMarkets=resolve;});},
      clearSymbolTasks:noop,abortMarketRequests:noop,resetAiResearchContext:noop,setInterfaceView:noop,syncWorkspaceNav:noop,syncTimeframeTabs:noop,syncStockSessionTabs:noop,renderMarkets:noop,
      renderChartQuality:noop,renderChartStrategyOverlay:noop,renderMarketWorkflowStrip:noop,requestAnimationFrame:noop,
      renderInterfaceView:noop,setLamp:noop,renderStrategyCommandStrip:noop,renderStrategyAnalysis:noop,strategyAnalysisForDisplay:v=>v,renderOrders:noop,renderSignals:noop,renderConditions:noop,renderStrategyDetail:noop,renderOrderHistory:noop,drawEquityChart:noop,renderBotReadiness:noop,
      drawChart:()=>vm.runInContext("renderFrozenReplaySummary()",context),loadTerminalLocalMarket:()=>{loads++;return Promise.resolve();},showTerminalLocalError:noop,
      futuOpenDOnline:()=>false,futuStatusPresentation:()=>({tone:"flat",label:"未连接"})});
    const functions=["frozenReplayPresentation","renderFrozenReplaySummary","currentMarket","isStockMarket","marketTypeLabel","numericMarketValue","stockSourceLabel","marketVolumeForDisplay","activeSymbolMetaText","syncQuoteFieldLabels","bidAskText","syncActiveSymbolHeader",
      "sideInsightRow","renderSideInsights","setLiveSourceItem","renderLiveSourceBar","renderBook","renderTrades","renderBookStrategyHint","stockQuoteContextForMarket","acceptStockQuoteContext","activeStockPriceLogRows","syncActiveMarketQuote",
      "updateTicker","updateMarketFromTicker","updateBook","addTrades","addStockPriceLog","mergeFutuTickerRowsIntoStockLog","updateCandle","setConnection","loadMarkets","loadTerminalLocalMarkets","renderPaper","renderDesktopStatus","applyFrozenQuantReplay","exitFrozenQuantReplay"];
    vm.runInContext(functions.map(appFunction).join("\n"),context);
    const oldMarketsRequest=vm.runInContext("loadMarkets()",context);
    vm.runInContext("applyFrozenQuantReplay(replay)",context);
    assert.equal(get("lastPrice").textContent,"29");callbacks.cutoff(2);
    assert.equal(get("lastPrice").textContent,"19.2233",source);assert.equal(get("high24h").textContent,"19.5");assert.equal(get("low24h").textContent,"18.4");assert.equal(get("vol24h").textContent,"12000");assert.equal(get("bidAsk").textContent,"--");
    assert.equal(captions.get("high24h").textContent,"截止日高");assert.match(metaElement.textContent,/frozen-provider.*2026-09-18.*非实时/);assert.ok(!metaElement.textContent.includes("离线种子"));
    assert.match(get("sideInsightState").textContent,/HK.00836/);assert.match(get("sideInsightRows").innerHTML,/19.2233/);assert.match(get("sideInsightRows").innerHTML,/未封存/);
    assert.match(get("liveCandleDetail").textContent,/2026-09-18.*2 根.*frozen-provider/);assert.match(get("liveNewsDetail").textContent,/不引用当前补全/);
    assert.equal(get("tradeCount").textContent,source==="BACKTEST"?"1 条回测记录":"0 条回测记录");assert.match(get("microSignal").textContent,/不可用/);
    // Fake elements keep innerHTML/textContent separately; use only the channel each renderer writes.
    const rendered=get("sideInsightRows").innerHTML+get("liveCandleDetail").textContent+get("liveNewsDetail").textContent+get("tradeTapeSummary").textContent+get("bookStrategyHint").textContent;
    assert.ok(!/338\.92|343\.06|22\.264|21\.736|18000000|2026-10-20|future news/.test(rendered),source);
    vm.runInContext('updateTicker({symbol:"HK.00836",last:999});updateMarketFromTicker({symbol:"HK.00836",last:999});updateBook({asks:[[999,1]]});addTrades([{px:999}]);addStockPriceLog({symbol:"HK.00836",last:999});mergeFutuTickerRowsIntoStockLog({symbol:"HK.00836",ticker:[{price:999}]});updateCandle([])',context);
    assert.equal(vm.runInContext('acceptStockQuoteContext({symbol:"HK.00836",last:999})',context),false);assert.equal(vm.runInContext("syncActiveMarketQuote()",context),false);
    assert.equal(vm.runInContext("stockQuoteContextForMarket().last",context),19.2233);assert.equal(state.candles.length,3);assert.equal(state.stockPriceLog.length,0);assert.equal(markets[1].price,"22");assert.equal(get("lastPrice").textContent,"19.2233");
    // Resolve a market-list request started before freezing, then run delayed
    // paper/status/quote projection callbacks after the historical prefix draw.
    resolveMarkets({items:[{symbol:"HK.00836",available:true}]});await oldMarketsRequest;
    await Promise.resolve();vm.runInContext('renderPaper();syncActiveMarketQuote();syncActiveSymbolHeader();renderSideInsights();renderLiveSourceBar();setConnection("实时 2026-10-20","up")',context);
    await vm.runInContext("loadMarkets()",context);
    assert.equal(marketRequests,1);assert.equal(context.markets,markets);assert.equal(get("lastPrice").textContent,"19.2233");assert.equal(get("vol24h").textContent,"12000");
    assert.match(get("priceChange").textContent,/2026-09-18/);assert.match(get("sideInsightRows").innerHTML,/19.2233/);assert.match(get("connectionState").textContent,/冻结复盘.*2026-09-18/);
    state.sideInsight="news";vm.runInContext("renderSideInsights();renderLiveSourceBar();syncActiveSymbolHeader()",context);assert.ok(!get("sideInsightRows").innerHTML.includes("future news"));
    state.sideInsight="volatility";vm.runInContext("exitFrozenQuantReplay()",context);await Promise.resolve();
    assert.equal(state.symbol,"AAPL");assert.equal(state.frozenQuantReplay,null);assert.equal(loads,1);assert.equal(get("lastPrice").textContent,"338.92");assert.match(get("sideInsightState").textContent,/AAPL/);assert.match(metaElement.textContent,/离线种子/);
  }
  assert.match(appFunction("drawChart"),/if \(state\.frozenQuantReplay\) renderFrozenReplaySummary\(\)/);
});

test("explicit fit-all restores the whole 575 or 1250 bar frozen interval after Home while live viewport limits and restoration stay unchanged",()=>{
  for(const count of [575,1250]){
    const data=Array.from({length:count},(_,i)=>row(Date.UTC(2020,0,i+1),new Date(Date.UTC(2020,0,i+1)).toISOString().slice(0,10)));
    const originalRows=Array.from({length:1250},(_,i)=>row(i+1));
    const originalView={visible:96,offset:17};
    const state={symbol:"AAPL",bar:"1Dutc",stockSession:"regular",candles:originalRows,chartView:{...originalView},replay:{active:false,timer:null}};
    const runtime={symbolVersion:0,chartUserZoomed:true},elements=new Map(),noop=()=>{};let callbacks,currentView,context;
    const get=id=>{if(!elements.has(id))elements.set(id,{dataset:{},classList:{remove(){}},hidden:false,textContent:""});return elements.get(id);};
    const replay={source:"STRUCTURE_FROZEN",symbol:"HK.00836",input_id:"a".repeat(64),record_hash:"b".repeat(64),meta:{asset_class:"EQUITY",price_basis:"RAW"},rows:data,structure_marks:[],trades:[]};
    context=vm.createContext({state,runtime,replay,markets:[{symbol:"AAPL",type:"stock"}],HakimiTerminalQuantProtocol:protocol,$:get,clearInterval:noop,
      window:{HakimiResearchChart:{configure:(value,options)=>{if(value)callbacks=options;}}},document:{querySelector:()=>null},
      drawChart:()=>{currentView=vm.runInContext("visibleCandles()",context);},requestAnimationFrame:noop,priceText:String,
      clearSymbolTasks:noop,abortMarketRequests:noop,resetAiResearchContext:noop,renderBook:noop,renderTrades:noop,setInterfaceView:noop,syncWorkspaceNav:noop,
      syncTimeframeTabs:noop,syncStockSessionTabs:noop,renderMarkets:noop,syncActiveSymbolHeader:noop,renderDesktopStatus:noop,renderChartQuality:noop,renderChartStrategyOverlay:noop,renderFrozenReplaySummary:noop});
    vm.runInContext(["clampNumber","visibleCandles","applyFrozenQuantReplay","exitFrozenQuantReplay"].map(appFunction).join("\n"),context);
    vm.runInContext("applyFrozenQuantReplay(replay)",context);
    state.chartView.visible=150;callbacks.cutoff(count-5);
    assert.equal(state.chartView.visible,150,"ordinary slider does not expand the viewport");
    callbacks.cutoff(1);assert.equal(currentView.candles.length,1);assert.equal(state.chartView.visible,40);
    callbacks.cutoff(count,{fitAll:true});
    assert.equal(state.replay.index,count);assert.equal(state.chartView.visible,count);assert.equal(state.chartView.offset,0);
    assert.equal(currentView.start,0);assert.equal(currentView.end,count);assert.equal(currentView.candles.length,count);
    vm.runInContext("exitFrozenQuantReplay(false)",context);
    assert.equal(state.symbol,"AAPL");assert.equal(state.candles,originalRows);assert.deepEqual(JSON.parse(JSON.stringify(state.chartView)),originalView);assert.equal(runtime.chartUserZoomed,true);
    state.chartView.visible=1250;vm.runInContext("visibleCandles()",context);assert.equal(state.chartView.visible,800,"normal market retains its original cap");
  }
});
