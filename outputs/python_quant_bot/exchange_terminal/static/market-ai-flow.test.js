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

test("HTTP and application error reasons reach the UI instead of generic 423 or api error", async () => {
  const context = vm.createContext({});
  vm.runInContext(extract("readApiResponse"), context);
  await assert.rejects(context.readApiResponse({
    ok: false, status: 423, statusText: "Locked",
    json: async () => ({ ok: false, read_only: true, error: "runtime is read-only" }),
  }), /只读或本地模式/);
  await assert.rejects(context.readApiResponse({
    ok: false, status: 429, statusText: "Too Many Requests",
    json: async () => ({ ok: false, error: "提供方限流，请稍后手动重试。" }),
  }), /提供方限流/);
  await assert.rejects(context.readApiResponse({
    ok: true, status: 200, json: async () => ({ ok: false, error: "当前行情样本不足" }),
  }), /行情样本不足/);
  assert.equal((await context.readApiResponse({
    ok: true, status: 200, json: async () => ({ ok: true, value: 4 }),
  })).value, 4);
});

function harness(rows, mode = {}) {
  const elements = new Map();
  const requests = [];
  const context = vm.createContext({
    state: {}, window: { HAKIMI_RUNTIME_MODE: mode },
    $: (id) => {
      if (!elements.has(id)) elements.set(id, { textContent: "", innerHTML: "", className: "", dataset: {} });
      return elements.get(id);
    },
    renderMarketAiLocal() {},
    aiReportHtml: () => "safe rendered report",
    loadRuntimeKeyStatus: async () => ({ rows }),
    marketAiPayload: () => ({ symbol: "BTC-USDT", candles: [] }),
    apiPost: async (route, payload) => {
      requests.push({ route, payload });
      return { status: { analysis: "partial", gpt: { model: "gpt-4o-mini" } },
        gpt: { ok: true }, deepseek: { ok: false, skipped: true, error: "未配置" }, analysis: {} };
    },
  });
  vm.runInContext(extract("aiChartContextKey") + "\n" + extract("aiRequestContext") + "\n" + extract("renderMarketAiAnalysis") + "\n" + extract("runMarketAiAnalysis"), context);
  return { context, elements, requests };
}

test("the original analysis button supports OpenAI alone and labels missing second review", async () => {
  const h = harness([{ id: "openai", configured: true }, { id: "deepseek", configured: false }]);
  await h.context.runMarketAiAnalysis();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].route, "/api/ai/market/dual-analysis");
  assert.match(h.elements.get("marketAiState").textContent, /单个AI分析已完成/);
  assert.match(h.elements.get("marketAiState").textContent, /尚无第二方复核/);
  assert.doesNotMatch(h.elements.get("marketAiState").textContent, /双方AI研究回执已更新/);
});

test("local-only mode and missing supported keys make no analysis request", async () => {
  for (const mode of [{ localOnly: true }, { localOnly: true, readOnly: true }]) {
    const h = harness([{ id: "openai", configured: true }], mode);
    await h.context.runMarketAiAnalysis();
    assert.equal(h.requests.length, 0);
    assert.match(h.elements.get("marketAiState").textContent, /请求未发送/);
  }
  const h = harness([{ id: "doubao", configured: true }]);
  await h.context.runMarketAiAnalysis();
  assert.equal(h.requests.length, 0);
  assert.match(h.elements.get("marketAiState").textContent, /OpenAI 或 DeepSeek/);
});

test("read-only storage allows an explicit model analysis without a persistence request", async () => {
  const h = harness([{ id: "deepseek", configured: true }], { readOnly: true, localOnly: false });
  assert.equal(h.requests.length, 0);
  await h.context.runMarketAiAnalysis();
  assert.deepEqual(h.requests.map(request => request.route), ["/api/ai/market/dual-analysis"]);
});

test("data-quality pause and two actual model receipts have distinct presentation", () => {
  const h = harness([]);
  h.context.renderMarketAiAnalysis({ local: { analysis_paused: true }, analysis: {} });
  assert.match(h.elements.get("marketAiState").textContent, /数据待核/);
  h.context.renderMarketAiAnalysis({ gpt: { ok: true }, deepseek: { ok: true }, analysis: {} });
  assert.match(h.elements.get("marketAiState").textContent, /双方AI研究回执/);
});

test("background analysis cannot replace the active chart's period or session identity", () => {
  const context = vm.createContext({
    state: { symbol: "AAPL", bar: "1Dutc", stockSession: "all",
      marketSnapshotContext: { snapshot_id: "selected", symbol: "AAPL", bar: "1Dutc", session: "all" } },
    isStockMarket: () => true, $: () => null,
  });
  vm.runInContext(extract("applySharedSnapshotContext"), context);
  context.applySharedSnapshotContext({ snapshot_id: "background-hourly", symbol: "AAPL", bar: "1H", session: "all" });
  assert.equal(context.state.marketSnapshotContext.snapshot_id, "selected");
  context.applySharedSnapshotContext({ snapshot_id: "background-regular", symbol: "AAPL", bar: "1Dutc", session: "regular" });
  assert.equal(context.state.marketSnapshotContext.snapshot_id, "selected");
  context.applySharedSnapshotContext({ snapshot_id: "same-chart", symbol: "AAPL", bar: "1d", session: "all" });
  assert.equal(context.state.marketSnapshotContext.snapshot_id, "same-chart");
});


test("provider failure receipt survives the API wrapper and reaches the original analysis cards once", async () => {
  const h = harness([{ id: "openai", configured: true }]);
  vm.runInContext(extract("readApiResponse"), h.context);
  const failure = { ok: false, error: "没有取得可用模型分析", status: { analysis: "failure" },
    gpt: { ok: false, error: "OpenAI API 额度不足，请核对额度。", request_attempts: 1 },
    deepseek: { ok: false, skipped: true, error: "未配置 · 已跳过", request_attempts: 0 },
    input_identity: { rows_sha256: "fixture", row_count: 300 }, analysis: {} };
  let requests = 0;
  h.context.apiPost = async () => {
    requests += 1;
    return h.context.readApiResponse({ ok: true, status: 200, json: async () => failure });
  };
  await h.context.runMarketAiAnalysis();
  assert.equal(requests, 1);
  assert.equal(h.elements.get("marketAiState").textContent, "尚未取得AI分析结果");
  assert.match(h.elements.get("marketAiGptBadge").textContent, /额度不足/);
  assert.match(h.elements.get("marketAiDeepSeekBadge").textContent, /已跳过/);
  assert.equal(h.elements.get("marketAiState").dataset.requestAttempts, "1");
  assert.equal(h.elements.get("marketAiState").dataset.inputRows, "300");
});


test("projection-only safety metadata cannot hide provider text or failure", () => {
  const context = vm.createContext({ escapeHtml: (text) => String(text).replaceAll("<", "&lt;") });
  vm.runInContext(extract("aiReportHtml"), context);
  const projectedEmpty = { analysis_only: true, planning_only: true, safe_action: "仅研究", order_allowed: false };
  assert.match(context.aiReportHtml(projectedEmpty, { ok: true, content: "实际模型文字" }), /实际模型文字/);
  assert.match(context.aiReportHtml(projectedEmpty, { ok: false, error: "提供方额度不足" }), /提供方额度不足/);
  assert.doesNotMatch(context.aiReportHtml(projectedEmpty, { ok: false, error: "失败" }), /等待结论/);
  assert.match(context.aiReportHtml({}, { ok: true, content: "<script>" }), /&lt;script>/);
});


test("rapid repeated analysis clicks share one in-flight request and release the button after failure", async () => {
  const h = harness([{ id: "openai", configured: true }]);
  let release;
  let requests = 0;
  h.context.apiPost = async () => {
    requests += 1;
    return new Promise(resolve => { release = resolve; });
  };
  const first = h.context.runMarketAiAnalysis();
  const repeated = h.context.runMarketAiAnalysis();
  await new Promise(setImmediate);
  assert.equal(requests, 1);
  assert.equal(h.context.state.marketAiRunning, true);
  assert.equal(h.elements.get("runMarketAiAnalysis").disabled, true);
  release({ ok: false, status: { analysis: "unavailable" },
    gpt: { ok: false, error_code: "credit_balance_exhausted", error: "API 预付余额已用完", request_attempts: 1 }, analysis: {} });
  await Promise.all([first, repeated]);
  assert.equal(requests, 1);
  assert.equal(h.context.state.marketAiRunning, false);
  assert.equal(h.elements.get("runMarketAiAnalysis").disabled, false);
  assert.match(h.elements.get("marketAiGptBadge").textContent, /余额已用完/);
});

test("missing key preflight releases the analysis button without a provider request", async () => {
  const h = harness([]);
  await h.context.runMarketAiAnalysis();
  assert.equal(h.requests.length, 0);
  assert.equal(h.context.state.marketAiRunning, false);
  assert.equal(h.elements.get("runMarketAiAnalysis").disabled, false);
});


test("DeepSeek-only configuration displays disabled GPT without treating it as a missing key", () => {
  const h = harness([]);
  h.context.escapeHtml = (value) => String(value);
  vm.runInContext(extract("renderMarketAiProviderStrip"), h.context);
  h.context.renderMarketAiProviderStrip([
    { id: "openai", configured: false, enabled: false, source: "disabled" },
    { id: "deepseek", configured: true, enabled: true, source: "env" },
  ]);
  assert.match(h.elements.get("marketAiProviderStrip").innerHTML, /未启用/);
  assert.match(h.elements.get("marketAiReadiness").textContent, /1 个 AI 已启用/);
  assert.doesNotMatch(h.elements.get("marketAiReadiness").textContent, /GPT/);
});

test("the original analysis button works with DeepSeek alone and reports one completed provider", async () => {
  const h = harness([
    { id: "openai", configured: false, enabled: false, source: "disabled" },
    { id: "deepseek", configured: true },
  ]);
  h.context.apiPost = async (route, payload) => {
    h.requests.push({ route, payload });
    return { status: { analysis: "complete", deepseek: { model: "deepseek-v4-pro" } },
      gpt: { ok: false, skipped: true, request_attempts: 0 },
      deepseek: { ok: true, request_attempts: 1, content: "completed analysis" }, analysis: {} };
  };
  await h.context.runMarketAiAnalysis();
  assert.equal(h.requests.length, 1);
  assert.equal(h.elements.get("marketAiState").dataset.requestAttempts, "1");
  assert.match(h.elements.get("marketAiState").textContent, /单个AI分析已完成/);
  assert.equal(h.elements.get("runMarketAiAnalysis").disabled, false);
});

test("ordinary strategy analysis cannot silently trigger paid DeepSeek analysis", async () => {
  let paidRequests = 0;
  let localRequests = 0;
  const context = vm.createContext({
    state: { lastPrice: 10, candles: [], symbol: "BTC-USDT" },
    $: () => ({ value: "dual_ma", textContent: "" }),
    riskQueryParams: () => "", renderStrategyAnalysis() {},
    apiPost: async (route) => { assert.equal(route, "/api/strategy/analyze"); localRequests += 1; return { local: { summary: "local" } }; },
    strategyAiFormInput: () => ({strategy_id:"dual_ma",strategy_params:{},risk_config:{}}),
    marketAiPayload: () => ({symbol:"BTC-USDT",bar:"1Dutc",chart_context:{session:"all"}}),
    loadDeepSeekAnalysis: async () => { paidRequests += 1; },
  });
  vm.runInContext(extract("aiChartContextKey") + "\n" + extract("aiRequestContext") + "\n" + extract("analyzeLocalStrategy"), context);
  assert.equal((await context.analyzeLocalStrategy()).summary, "local");
  assert.equal(localRequests, 1);
  assert.equal(paidRequests, 0);
  assert.doesNotMatch(source, /loadDeepSeekOpportunities\(true\)/);
  assert.match(source, /addEventListener\("click", \(\) => loadDeepSeekOpportunities\(false\)\)/);
});
