"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const protocol = require("./terminal-quant-ui");
const ui = fs.readFileSync(path.join(__dirname,"terminal-quant-ui.js"),"utf8");
const app = fs.readFileSync(path.join(__dirname,"app.js"),"utf8");
function fn(source,name,indent="") {
  const start=source.indexOf(`function ${name}(`);
  assert.ok(start>=0,name);
  const begin=source.slice(start-6,start)==="async "?start-6:start;
  const end=source.indexOf("\n"+indent+"}",start);
  assert.ok(end>=start,name+" end");
  return source.slice(begin,end+indent.length+2).trim();
}
const percent={key:"threshold",display_scale:100,display_unit:"%",label:"动量阈值",step:"any"};
test("percentage unit round trips preserve stored ratios, count and multipliers",()=>{
  for(const value of [.015,.006,.004,.01,.08,.12,1e-12,1.234567891234567])
    assert.equal(protocol.parameterUnits(percent,protocol.parameterUnits(percent,value),false),value);
  assert.equal(protocol.parameterUnits(percent,.015),1.5);
  assert.equal(protocol.parameterUnits({display_scale:1},100),100);
  assert.equal(protocol.parameterUnits({display_scale:1},1.1),1.1);
  for(const value of [undefined,null,""]) assert.equal(protocol.parameterUnits(percent,value),null);
  assert.throws(()=>protocol.parameterUnits(percent,"unknown"),/有限/);
});
test("AI form and research bridge read the same raw parameters after a percentage edit",()=>{
  const entry={id:"momentum",name:"动量",params:{window:20,threshold:.015,position_pct:.25},parameter_fields:[percent,{key:"window",display_scale:1}]};
  const fields=[{dataset:{strategyParam:"threshold"},value:"2.5"},{dataset:{strategyParam:"window"},value:"40"}];
  const values={strategySelect:"momentum",positionInput:25,takeProfitInput:0,stopLossInput:8,leverageInput:1,directionMode:"LONG_ONLY",riskSource:"MANUAL",riskValueMode:"PCT",strategyOrderType:"CURRENT",marginMode:"CROSS"};
  const ctx=vm.createContext({state:{symbol:"AAPL",bar:"1D",strategies:[entry]},HakimiTerminalQuantProtocol:protocol,
    document:{querySelectorAll:()=>fields},$:id=>({value:values[id],checked:false}),riskQueryParams:()=>"",URLSearchParams,currentAiResearchEvidence:()=>null});
  vm.runInContext(fn(app,"strategyAiFormInput")+"\n"+fn(app,"currentTerminalResearchContext"),ctx);
  const ai=ctx.strategyAiFormInput(),research=ctx.currentTerminalResearchContext();
  assert.deepEqual(ai.strategy_params,research.strategy_params);
  assert.equal(ai.strategy_params.threshold,.025);assert.equal(ai.strategy_params.window,40);
  assert.equal(ai.strategy_params.position_pct,.25);
});
test("native new and revised forms render percentages but do not fill missing history parameters",()=>{
  const entry={id:"momentum",params:{threshold:.015,window:20},parameter_fields:[percent,{key:"window",label:"周期"}],capability:{backtest_supported:true,new_research_allowed:true}};
  const elements={"tq-strategy-note":{},"tq-save-task":{},"tq-params":{}};
  const ctx=vm.createContext({state:{catalog:[entry]},$:id=>elements[id],value:()=>"momentum",parameterUnits:protocol.parameterUnits,researchBlocker:protocol.researchBlocker,esc:String,updatePreflight(){}});
  vm.runInContext(fn(ui,"renderParams","    "),ctx);ctx.renderParams();
  assert.match(elements["tq-params"].innerHTML,/value="1.5"/);
  ctx.renderParams({window:30});assert.match(elements["tq-params"].innerHTML,/原记录未记录/);
  assert.doesNotMatch(elements["tq-params"].innerHTML,/value="1.5"/);
});
test("data shortage blocks submission and failed preflight does not compute",async()=>{
  const notices=[];let operations=0;const entry={id:"dual_ma",capability:{backtest_supported:true,new_research_allowed:true}};
  const elements={"tq-preflight":{},"tq-completion":{}};
  const ctx=vm.createContext({state:{tasks:[{id:"task",strategy_id:"dual_ma"}],catalog:[entry]},
    identity:row=>row.id,researchBlocker:protocol.researchBlocker,$:id=>elements[id],preflightHtml:check=>String(check.required_rows),
    api:async route=>{assert.deepEqual(JSON.parse(decodeURIComponent(route.split("/")[1])),{task_id:"task"});return {status:"BLOCKED",complete_rows:81,required_rows:82};},
    act:async()=>operations++,notify:(message)=>notices.push(message)});
  vm.runInContext(fn(ui,"dispatch","    "),ctx);await ctx.dispatch("run","task",{});
  assert.equal(operations,0);assert.match(notices[0],/81.*82/);
  ctx.api=async()=>{throw new Error("read failure");};await assert.rejects(ctx.dispatch("run","task",{}),/read failure/);assert.equal(operations,0);
});
test("late preflight response cannot overwrite changed parameters",async()=>{
  const panel={};let resolveFirst;let count=0;
  const ctx=vm.createContext({state:{preflightRequest:0},$:()=>panel,value:id=>id==="tq-input"?"input":"dual_ma",
    currentSignalParams:()=>({slow_window:++count}),preflightHtml:check=>String(check.required_rows),operationErrorText:e=>e.message,
    api:()=>count===1?new Promise(resolve=>{resolveFirst=resolve;}):Promise.resolve({required_rows:107})});
  vm.runInContext(fn(ui,"updatePreflight","    "),ctx);
  const first=ctx.updatePreflight();await ctx.updatePreflight();resolveFirst({required_rows:82});await first;
  assert.equal(panel.innerHTML,"107");
});
test("opening another rule form preserves the native draft rule and its parameters",async()=>{
  const selected={value:"core:price.dual_ma@1"};let opened;
  const state={lastNativeStrategy:"momentum",coreStrategies:[{key:"price.dual_ma@1"}],catalog:[{id:"dual_ma"},{id:"momentum"}]};
  const ctx=vm.createContext({state,$:()=>selected,hide(){},show(){},notify(){},operationErrorText:e=>e.message,
    openCoreTaskForm:async key=>{opened=key;},researchBlocker:()=>""});
  vm.runInContext(fn(ui,"openCoreRule","    "),ctx);await ctx.openCoreRule("price.dual_ma@1");
  assert.equal(selected.value,"momentum");assert.equal(opened,"price.dual_ma@1");
  await assert.rejects(ctx.openCoreRule("unknown"),/未找到/);assert.equal(selected.value,"momentum");
});
