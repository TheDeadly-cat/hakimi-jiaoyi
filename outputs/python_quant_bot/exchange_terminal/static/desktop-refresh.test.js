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

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}

function harness() {
  const elements = new Map([
    ["desktopRefresh", {textContent:"刷新", disabled:false}],
    ["chartStatus", {textContent:"原图表"}],
  ]);
  const calls = [], snapshots = [], coordinatorRequests = [], applied = [];
  let refreshId = 0;
  const ctx = vm.createContext({
    state:{symbol:"HK.00836", bar:"1Dutc", stockSession:"regular"},
    window:{HAKIMI_RUNTIME_MODE:{}, HakimiChartController:{
      inFlightKey:({requestSymbol,requestBar,requestSession}) => `${requestSymbol}|${requestBar}|${requestSession}`,
      retryStatusText:() => "行情刷新暂未完成",
    }},
    runtime:{symbolVersion:4, desktopRefreshRunning:false, chartRefreshApplied:new Map(),
      chartRefreshCoordinator:{request:async(request) => {
        coordinatorRequests.push(request);
        return {refreshId:++refreshId, value:await request.task()};
      }}},
    $:(id) => elements.get(id),
    isStockMarket:(symbol) => !symbol.includes("-"),
    marketSnapshotLimit:(symbol,bar) => bar === "1Dutc" ? 300 : 400,
    chartCacheKey:(symbol,bar,session) => `${symbol}|${bar}|${session}`,
    marketSnapshotPath:(params) => { snapshots.push(params); return "/fixture-snapshot"; },
    api:async() => ({candles:{source:"futu"}}),
    isAbortError:() => false,
    applyMarketSnapshotToChart:(data,request) => applied.push({data,request}),
  });
  for (const name of ["refreshMarketTickers", "loadFutuStatus", "pollLiveTicker", "refreshPaper",
    "loadTerminalLocalMarkets", "loadTerminalLocalMarket", "loadTerminalLocalAccount"]) {
    ctx[name] = async(...args) => { calls.push({name,args}); };
  }
  for (const name of ["chartRefreshTargetIsCurrent", "applyCoordinatedMarketSnapshot",
    "refreshSnapshotCandlesInBackground", "refreshDesktopMarket"]) {
    vm.runInContext(extract(name),ctx);
  }
  return {ctx,elements,calls,snapshots,coordinatorRequests,applied};
}

test("desktop refresh forces the current symbol/bar/session through the shared coordinator and keeps existing refreshes",async()=>{
  const h=harness();
  h.ctx.state.symbol="AAPL"; h.ctx.state.bar="5m"; h.ctx.state.stockSession="post";
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.coordinatorRequests.length,1);
  assert.equal(h.coordinatorRequests[0].manual,true);
  assert.deepEqual(JSON.parse(JSON.stringify(h.snapshots)),[{
    symbol:"AAPL",bar:"5m",limit:400,session:"post",fast:false,force:true,emit:false,consumer:"manual_chart_refresh",
  }]);
  assert.equal(h.applied.length,1);
  assert.equal(h.applied[0].request.cacheKey,"AAPL|5m|post");
  assert.deepEqual(h.calls,[
    {name:"refreshMarketTickers",args:[]},{name:"loadFutuStatus",args:[true]},
    {name:"pollLiveTicker",args:[]},{name:"refreshPaper",args:[true]},
  ]);
  assert.equal(h.elements.get("desktopRefresh").disabled,false);
  assert.equal(h.elements.get("desktopRefresh").textContent,"刷新");
  assert.match(source,/\$\("desktopRefresh"\)\?\.addEventListener\("click", async \(\) => \{\s*await refreshDesktopMarket\(\);\s*\}\)/);
});

test("crypto refresh uses all-session identity instead of the previous stock session",async()=>{
  const h=harness(); h.ctx.state.symbol="BTC-USDT";
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.snapshots[0].session,"all");
  assert.equal(h.applied[0].request.cacheKey,"BTC-USDT|1Dutc|all");
});

test("frozen replay refresh keeps archived data and never requests live or local replacement data",async()=>{
  const h=harness(); h.ctx.state.frozenQuantReplay={symbol:"HK.00836"};
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.snapshots.length,0); assert.equal(h.calls.length,0); assert.equal(h.applied.length,0);
  assert.match(h.elements.get("chartStatus").textContent,/冻结复盘保留封存行情/);
  assert.equal(h.elements.get("desktopRefresh").disabled,false);
});

test("local-only refresh reads only local lists, current market and account",async()=>{
  const h=harness(); h.ctx.window.HAKIMI_RUNTIME_MODE.localOnly=true;
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.snapshots.length,0); assert.equal(h.coordinatorRequests.length,0);
  assert.deepEqual(h.calls,[{name:"loadTerminalLocalMarkets",args:[]},
    {name:"loadTerminalLocalMarket",args:["HK.00836",4]}, {name:"loadTerminalLocalAccount",args:[]}]);
});

test("repeated clicks remain single-flight until both candles and existing refreshes settle",async()=>{
  const h=harness(), candle=deferred(), ancillary=deferred();
  h.ctx.api=()=>candle.promise; h.ctx.loadFutuStatus=()=>ancillary.promise;
  const first=h.ctx.refreshDesktopMarket();
  assert.equal(h.elements.get("desktopRefresh").disabled,true);
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.snapshots.length,1);
  candle.resolve({candles:{source:"futu"}});
  await new Promise(setImmediate);
  assert.equal(h.elements.get("desktopRefresh").disabled,true);
  ancillary.resolve(); await first;
  assert.equal(h.ctx.runtime.desktopRefreshRunning,false);
  assert.equal(h.elements.get("desktopRefresh").disabled,false);
});

test("a failed candle request reports failure, restores the button and allows one explicit retry",async()=>{
  const h=harness(); h.ctx.api=async()=>{throw new Error("Futu 暂不可用");};
  await h.ctx.refreshDesktopMarket();
  assert.match(h.elements.get("chartStatus").textContent,/刷新未完成：Futu 暂不可用/);
  assert.equal(h.elements.get("desktopRefresh").disabled,false);
  assert.equal(h.elements.get("desktopRefresh").textContent,"刷新");
  assert.equal(h.applied.length,0);
  h.ctx.api=async()=>({candles:{source:"futu"}});
  await h.ctx.refreshDesktopMarket();
  assert.equal(h.snapshots.length,2); assert.equal(h.applied.length,1);
});

test("late refresh cannot replace frozen replay, local mode, another symbol or another session",async()=>{
  for (const change of [ctx=>{ctx.state.frozenQuantReplay={symbol:"HK.00836"};},
    ctx=>{ctx.window.HAKIMI_RUNTIME_MODE.localOnly=true;},ctx=>{ctx.state.symbol="AAPL";},
    ctx=>{ctx.state.bar="5m";},ctx=>{ctx.state.stockSession="all";}]) {
    const h=harness(), pending=deferred(); h.ctx.api=()=>pending.promise;
    const first=h.ctx.refreshDesktopMarket(); change(h.ctx);
    pending.resolve({candles:{source:"futu"}}); await first;
    assert.equal(h.applied.length,0);
  }
});

test("late failure does not overwrite a new chart or frozen replay status",async()=>{
  const h=harness(), pending=deferred(); h.ctx.api=()=>pending.promise;
  const first=h.ctx.refreshDesktopMarket();
  h.ctx.state.frozenQuantReplay={symbol:"HK.00836"};
  h.elements.get("chartStatus").textContent="冻结记录";
  pending.reject(new Error("old request failed")); await first;
  assert.equal(h.elements.get("chartStatus").textContent,"冻结记录");
  assert.equal(h.elements.get("desktopRefresh").disabled,false);
});

test("opening data records after a chart or research start loads the local history and ledger without replacing the active market",async()=>{
  for (const initialView of ["trade","research"]) {
    const h=harness(), reads=[], history=[];
    h.ctx.state.interfaceView=initialView;
    h.ctx.state.candles=[{ts:1,close:22}];
    const originalMarket=JSON.stringify({symbol:h.ctx.state.symbol,bar:h.ctx.state.bar,candles:h.ctx.state.candles});
    h.ctx.INTERFACE_VIEWS={system:{},trade:{},research:{}};
    h.ctx.localStorage={setItem(){}};
    h.ctx.renderInterfaceView=()=>{};
    h.ctx.renderHistory=(rows)=>history.push(rows);
    h.elements.set("ledgerSummary",{textContent:"读取中"});
    h.elements.set("ledgerRows",{innerHTML:""});
    for (const name of ["loadFullConfig","loadV2Platform","loadDataReliability","loadDataCache","loadApiConfig"]) {
      h.ctx[name]=async()=>{};
    }
    h.ctx.api=async(route)=>{
      reads.push(route);
      if (route==="/api/local/btc-daily?limit=5000") return {rows:[{date:"2026-10-23",close:65000}]};
      if (route==="/api/ledger?limit=80") return {ledger:[]};
      throw new Error("unexpected read: "+route);
    };
    for (const name of ["loadHistoryTable","loadLedger","setInterfaceView"]) vm.runInContext(extract(name),h.ctx);
    h.ctx.setInterfaceView("system");
    await new Promise(setImmediate);
    assert.deepEqual(reads,["/api/local/btc-daily?limit=5000","/api/ledger?limit=80"]);
    assert.equal(history[0][0].date,"2026-10-23");
    assert.equal(h.elements.get("ledgerSummary").textContent,"0 rows");
    assert.equal(JSON.stringify({symbol:h.ctx.state.symbol,bar:h.ctx.state.bar,candles:h.ctx.state.candles}),originalMarket);
    assert.equal(h.snapshots.length,0);
  }
  assert.match(fs.readFileSync(path.join(__dirname,"index.html"),"utf8"),/<strong>BTC 本地日线价格库<\/strong>/);
});
