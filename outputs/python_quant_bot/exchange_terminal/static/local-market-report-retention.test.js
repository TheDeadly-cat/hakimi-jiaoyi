"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
function extract(name) {
  const offset=source.indexOf(`function ${name}(`),start=source.slice(offset-6,offset)==="async "?offset-6:offset;
  assert.ok(offset>=0);const next=/\n(?:async )?function \w+\(/g;next.lastIndex=offset+name.length+10;
  return source.slice(start,next.exec(source)?.index??source.length);
}
test("same selected cache digest preserves explicit reports while changed or unknown context invalidates them", async () => {
  const market={symbol:"HK.00836",source_id:"cache-futu",digest:"a".repeat(64),meta:{session:"regular"},
    quality:{status:"REVIEW"},rows:[{date:"2026-10-23",close:18.9}],available_sources:[]};
  for(const scenario of ["unchanged","new_data","new_source","new_session","unknown_digest","new_bar"]){
    const response=JSON.parse(JSON.stringify(market));
    if(scenario==="new_data")response.digest="b".repeat(64);
    if(scenario==="new_source")response.source_id="cache-other";
    if(scenario==="new_session")response.meta.session="all";
    if(scenario==="unknown_digest")delete response.digest;
    const local={report:"saved local"},ai={report:"saved AI"};let invalidations=0;
    const elements=new Map();
    const state={symbol:market.symbol,bar:scenario==="new_bar"?"5m":"1Dutc",stockSession:"regular",
      chartDataSymbol:market.symbol,chartView:{},terminalLocalMarket:market,currentStrategyLocal:local,strategyAi:ai};
    const ctx=vm.createContext({state,runtime:{symbolVersion:1},api:async()=>({market:response}),
      $:id=>{if(!elements.has(id))elements.set(id,{});return elements.get(id);},escapeHtml:x=>x,
      HakimiTerminalQuantProtocol:{chartRows:rows=>rows},priceText:String,
      resetAiResearchContext(){invalidations++;state.currentStrategyLocal=null;state.strategyAi=null;},
      ...Object.fromEntries(["syncTimeframeTabs","syncStockSessionTabs","syncActiveSymbolHeader","renderChartQuality",
        "loadDrawings","drawChart","renderBook","renderTrades","renderChartStrategyOverlay","renderSideInsights","renderLiveSourceBar"].map(name=>[name,()=>{}]))});
    vm.runInContext(extract("loadTerminalLocalMarket"),ctx);
    await ctx.loadTerminalLocalMarket(market.symbol);
    assert.equal(invalidations,scenario==="unchanged"?0:1,scenario);
    if(scenario==="unchanged"){assert.equal(state.currentStrategyLocal,local);assert.equal(state.strategyAi,ai);}
  }
});
test("successful explicit local analysis has current wording and never pretends to be an AI report", async () => {
  for(const existingAi of [false,true]){
    const elements=new Map();
    const form={strategy_id:"dual_ma",strategy_params:{fast_window:20,slow_window:60}};
    const formKey=JSON.stringify(form),context={context_key:"same-chart"};
    const state={strategyAi:existingAi?{request_context:context,strategy_form_key:formKey}:null};
    const ctx=vm.createContext({state,$:id=>{if(!elements.has(id))elements.set(id,{textContent:"existing AI",dataset:{}});return elements.get(id);},
      strategyAiFormInput:()=>form,marketAiPayload:()=>({symbol:"HK.00836",bar:"1Dutc"}),aiRequestContext:()=>context,
      aiChartContextKey:()=>context.context_key,renderStrategyAnalysis(){},apiPost:async()=>({local:{signal:{calculated:true}},completion_counts:{complete:300}})});
    vm.runInContext(extract("analyzeLocalStrategy"),ctx);await ctx.analyzeLocalStrategy();
    if(existingAi)assert.equal(elements.has("strategyAiState"),false);
    else{assert.match(elements.get("strategyAiState").textContent,/本地规则已完成.*300.*未调用AI/);assert.match(elements.get("strategyAiReport").textContent,/DeepSeek 尚未运行/);}
  }
});
