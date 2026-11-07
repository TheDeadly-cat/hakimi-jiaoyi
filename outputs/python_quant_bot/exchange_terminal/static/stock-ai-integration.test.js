"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
function extract(name) {
  const offset = source.indexOf(`function ${name}(`);
  assert.ok(offset >= 0, name);
  const start = source.slice(offset - 6, offset) === "async " ? offset - 6 : offset;
  const next = /\n(?:async )?function \w+\(/g;
  next.lastIndex = offset + name.length + 10;
  return source.slice(start, next.exec(source)?.index ?? source.length);
}
function harness() {
  const elements = new Map();
  const requests = [];
  let form = {strategy_id:"dual_ma", strategy_params:{fast:10,slow:30},risk_config:{}};
  const ctx = vm.createContext({
    state:{symbol:"AAPL",bar:"5m",stockSession:"regular"},
    window:{HAKIMI_RUNTIME_MODE:{}},
    $:(id) => {
      if (!elements.has(id)) elements.set(id,{textContent:"",innerHTML:"",dataset:{}});
      return elements.get(id);
    },
    strategyAiFormInput:() => form,
    marketAiPayload:() => ({symbol:ctx.state.symbol,bar:ctx.state.bar,candles:[{complete:true},{complete:false}],
      chart_context:{session:"regular",snapshot_source:"futu"},max_output_tokens:768}),
    renderMarketAiLocal(){}, renderDeepSeekAnalysis(){}, renderStrategyAnalysis(){}, aiReportHtml:()=>"fixture analysis",
    loadRuntimeKeyStatus:async()=>({rows:[{id:"deepseek",configured:true}]}),
    renderMarketAiAnalysis:(data)=>{ctx.state.marketAi=data;},
    apiPost:async(route,payload)=> {
      requests.push({route,payload});
      return success();
    },
  });
  for (const name of ["aiChartContextKey","aiRequestContext","resetAiResearchContext",
    "currentAiResearchEvidence","runMarketAiAnalysis","loadDeepSeekAnalysis"]) {
    vm.runInContext(extract(name),ctx);
  }
  return {ctx,elements,requests,changeForm:()=>{form={...form,strategy_params:{fast:12,slow:30}};}};
}
function success() {
  return {ok:true,local:{symbol:"AAPL",bar:"5m"},input_identity:{
    rows_sha256:"a".repeat(64),row_count:100,first_ts:1,last_ts:2,source:"futu",
    price_basis:"SUPPLIED_LAST_CANDLE_CLOSE",snapshot_id:null},
    deepseek:{ok:true,model:"deepseek-v4-pro",content:'{"summary":"fixture only"}',
      json:{summary:"fixture only"},request_attempts:1,completion_status:"complete",finish_reason:"stop"}};
}

test("strategy analysis separates local-only networking from read-only storage", async () => {
  const local = harness();
  local.ctx.window.HAKIMI_RUNTIME_MODE = { localOnly: true, readOnly: true };
  await local.ctx.loadDeepSeekAnalysis();
  assert.equal(local.requests.length, 0);
  assert.match(local.elements.get("strategyAiState").textContent, /本地模式.*未发送/);
  const readonly = harness();
  readonly.ctx.window.HAKIMI_RUNTIME_MODE = { localOnly: false, readOnly: true };
  assert.equal(readonly.requests.length, 0);
  await readonly.ctx.loadDeepSeekAnalysis();
  assert.deepEqual(readonly.requests.map(request => request.route), ["/api/ai/deepseek/analyze"]);
});

test("market response arriving after symbol switch is discarded, including switch-back",async()=>{
  const h=harness();
  let finish;
  h.ctx.apiPost=(route,payload)=>{h.requests.push({route,payload});return new Promise(resolve=>{finish=resolve;});};
  const pending=h.ctx.runMarketAiAnalysis();
  await new Promise(setImmediate);
  h.ctx.state.symbol="NVDA";h.ctx.resetAiResearchContext();
  h.ctx.state.symbol="AAPL";h.ctx.resetAiResearchContext();
  finish(success());await pending;
  assert.equal(h.ctx.state.marketAi,null);
  assert.equal(h.requests.length,1);
  assert.equal(h.elements.get("runMarketAiAnalysis").disabled,false);
});

test("timeframe/session switches invalidate reports and keep single-flight until request completes",async()=>{
  const h=harness();
  let finish;
  h.ctx.apiPost=()=>new Promise(resolve=>{finish=resolve;});
  const pending=h.ctx.loadDeepSeekAnalysis();
  h.ctx.state.bar="1Dutc";h.ctx.state.stockSession="all";h.ctx.resetAiResearchContext();
  assert.equal(h.ctx.state.strategyAiRunning,true);
  finish(success());await pending;
  assert.equal(h.ctx.state.strategyAi,null);
  assert.equal(h.ctx.state.strategyAiRunning,false);
  assert.equal(h.elements.get("deepseekAnalyze").disabled,false);
});

test("explicit strategy analysis sends current form and candle completion once",async()=>{
  const h=harness();
  await h.ctx.loadDeepSeekAnalysis();
  assert.equal(h.requests.length,1);
  assert.equal(h.requests[0].route,"/api/ai/deepseek/analyze");
  assert.equal(h.requests[0].payload.strategy_params.fast,10);
  assert.equal(h.requests[0].payload.chart_context.session,"regular");
  assert.equal(h.requests[0].payload.candles[1].complete,false);
  assert.match(h.elements.get("strategyAiState").textContent,/已完成/);
  assert.equal(h.elements.get("strategyAiState").dataset.requestAttempts,"1");
});

test("strategy parameter changes cannot publish an old request or hand off old AI evidence",async()=>{
  const h=harness();
  let finish;
  h.ctx.apiPost=()=>new Promise(resolve=>{finish=resolve;});
  const pending=h.ctx.loadDeepSeekAnalysis();h.changeForm();finish(success());await pending;
  assert.equal(h.ctx.state.strategyAi,undefined);
  assert.match(h.elements.get("strategyAiState").textContent,/参数已改变/);
  assert.equal(h.ctx.currentAiResearchEvidence(),null);
});

test("provider failures render safe error and local result without pretending success",async()=>{
  const h=harness();
  h.ctx.apiPost=async()=>{
    const err=new Error("provider failed");
    err.responseData={ok:false,local:{symbol:"AAPL"},deepseek:{
      ok:false,error:"DeepSeek API 余额不足",request_attempts:1,completion_status:"failed"}};
    throw err;
  };
  await h.ctx.loadDeepSeekAnalysis();
  assert.match(h.elements.get("strategyAiReport").textContent,/余额不足/);
  assert.equal(h.ctx.currentAiResearchEvidence(),null);
  assert.equal(h.elements.get("analyzeStrategy").disabled,false);
});

test("only completed matching AI evidence follows a research task, without changing parameters",async()=>{
  const h=harness();
  h.ctx.state.bar="1Dutc";
  await h.ctx.loadDeepSeekAnalysis();
  const evidence=h.ctx.currentAiResearchEvidence();
  assert.equal(evidence.symbol,"AAPL");
  assert.equal(evidence.session,"regular");
  assert.equal(evidence.input_identity.rows_sha256,"a".repeat(64));
  assert.equal(evidence.providers.length,1);
  assert.equal(evidence.providers[0].content,'{"summary":"fixture only"}');
  assert.equal("strategy_params" in evidence,false);
  h.ctx.state.stockSession="pre";
  assert.equal(h.ctx.currentAiResearchEvidence(),null);
});

test("intraday AI does not block creation of a daily task or pretend it is daily evidence",async()=>{
  const h=harness();
  await h.ctx.loadDeepSeekAnalysis();
  assert.equal(h.ctx.currentAiResearchEvidence(),null);
});

test("paper refresh preserves same-context manual strategy analysis without changing research direction",async()=>{
  const h=harness();
  vm.runInContext(extract("strategyAnalysisForDisplay"),h.ctx);
  await h.ctx.loadDeepSeekAnalysis();
  assert.equal(h.ctx.strategyAnalysisForDisplay({}).symbol,"AAPL");
  h.changeForm();
  assert.equal(h.ctx.strategyAnalysisForDisplay({reason:"paper-only"}).reason,"paper-only");
  assert.match(extract("renderPaper"), /renderStrategyAnalysis\(strategyAnalysisForDisplay\(analysis\)\)/);
  const prefix=extract("renderPaper").split("if (paper.armed)")[0];
  assert.doesNotMatch(prefix,/\$\("directionMode"\)\.value\s*=/);
});

test("Hong Kong daily chart labels keep trading dates while crypto stays UTC and frozen rows stay unchanged",()=>{
  const h=harness();
  vm.runInContext(extract("formatCandleTime"),h.ctx);
  const ts=Date.parse("2026-10-19T16:00:00Z");
  h.ctx.state.symbol="HK.00836";h.ctx.state.bar="1Dutc";
  assert.equal(h.ctx.formatCandleTime(ts),"2026-10-20");
  assert.equal(h.ctx.formatCandleTime(Date.parse("2026-10-20T00:00:00Z")),"2026-10-20");
  h.ctx.state.symbol="BTC-USDT";
  assert.equal(h.ctx.formatCandleTime(ts),"2026-10-19");
  h.ctx.state.symbol="HK.00836";h.ctx.state.frozenQuantReplay={run_id:"fixture"};
  h.ctx.state.candles=[{ts,date:"2026-10-20"}];
  const before=JSON.stringify(h.ctx.state.candles);
  assert.equal(h.ctx.formatCandleTime(ts),"2026-10-20");
  assert.equal(JSON.stringify(h.ctx.state.candles),before);
});

test("frozen replay clears previous-symbol live order book instead of showing it under the replay symbol",()=>{
  const h=harness();
  h.ctx.state.frozenQuantReplay={symbol:"HK.00836"};
  for(const id of ["asks","bids","midPrice","bookSpread"])h.ctx.$(id).textContent="previous AAPL quote";
  for(const id of ["asks","bids"])h.ctx.$(id).innerHTML="previous AAPL order book";
  h.ctx.$("bookStrategyHint").textContent="previous AAPL strategy";
  h.ctx.$("bookStrategyHint").dataset.rawPaperArmed="true";
  vm.runInContext(extract("renderBookStrategyHint"),h.ctx);
  vm.runInContext(extract("renderBook"),h.ctx);
  h.ctx.renderBook();
  assert.equal(h.elements.get("midPrice").textContent,"--");
  assert.equal(h.elements.get("asks").innerHTML,"");
  assert.equal(h.elements.get("bids").innerHTML,"");
  assert.match(h.elements.get("bookSpread").textContent,/冻结复盘/);
  assert.match(h.elements.get("bookStrategyHint").textContent,/冻结研究复盘/);
  assert.equal(h.elements.get("bookStrategyHint").dataset.rawPaperArmed,undefined);
});
