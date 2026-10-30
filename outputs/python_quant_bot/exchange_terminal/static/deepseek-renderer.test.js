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
  const context = vm.createContext({
    state: { symbol: "AAPL", bar: "5m", stockSession: "regular" },
    window: { HAKIMI_RUNTIME_MODE: {} },
    $: (id) => {
      if (!elements.has(id)) elements.set(id, { textContent: "", innerHTML: "", dataset: {} });
      return elements.get(id);
    },
    strategyAiFormInput: () => ({ strategy_id: "dual_ma", strategy_params: { fast: 10, slow: 30 }, risk_config: {} }),
    marketAiPayload: () => ({ symbol: "AAPL", bar: "5m", chart_context: { session: "regular" }, candles: [] }),
    renderStrategyAnalysis: () => {},
    aiReportHtml: (report) => `report: ${report.summary || ""}`,
    apiPost: async (route, payload) => {
      requests.push({ route, payload });
      return context.response;
    },
  });
  for (const name of ["escapeHtml", "marketResearchDirectionLabel", "renderDeepSeekStatus",
    "renderDeepSeekRows", "renderDeepSeekAnalysis", "aiChartContextKey", "aiRequestContext", "loadDeepSeekAnalysis"]) {
    vm.runInContext(extract(name), context);
  }
  return { context, elements, requests };
}

function success(json) {
  return {
    ok: true, provider_status: { configured: true, model: "fixture-model" },
    analysis: { deepseek: json },
    deepseek: { ok: true, content: JSON.stringify(json), json, request_attempts: 1,
      completion_status: "complete", finish_reason: "stop" },
    local: { signal: { calculated: true, availability: "CALCULATED" } },
    completion_counts: { complete: 80 },
  };
}

test("real renderer retains ordinary list output and never mutates the receipt", () => {
  const h = harness();
  const response = success({ summary: "已完成说明", risk_notes: ["风险甲", "风险乙", "风险丙"], reasons: ["依据甲", "依据乙"] });
  const before = JSON.stringify(response);
  h.context.renderDeepSeekAnalysis(response);
  assert.equal(h.elements.get("deepseekHeadline").textContent, "已完成说明");
  assert.equal(h.elements.get("deepseekSummary").textContent, "风险甲 / 风险乙");
  assert.match(h.elements.get("deepseekRows").innerHTML, /依据甲 \/ 依据乙/);
  assert.equal(JSON.stringify(response), before);
});

test("string risk and reason fields render as one complete item", () => {
  const h = harness();
  h.context.renderDeepSeekAnalysis(success({ summary: "说明", risk_notes: "整段风险说明", reasons: "整段证据说明" }));
  assert.equal(h.elements.get("deepseekSummary").textContent, "整段风险说明");
  assert.match(h.elements.get("deepseekRows").innerHTML, /整段证据说明/);
  h.context.renderDeepSeekAnalysis(success({ summary: "说明", risk_notes: null, warnings: ["风险", null], reasons: null }));
  assert.equal(h.elements.get("deepseekSummary").textContent, "风险");
});

test("rows accept text and objects, skip null and invalid entries, and escape text", () => {
  const h = harness();
  h.context.renderDeepSeekRows([null, false, 5, [], "<script>text</script>", { symbol: "NVDA", reason: "有效行" }]);
  const html = h.elements.get("deepseekRows").innerHTML;
  assert.match(html, /&lt;script&gt;text&lt;\/script&gt;/);
  assert.match(html, /NVDA/);
  assert.match(html, /有效行/);
  assert.equal((html.match(/class="deepseek-row"/g) || []).length, 2);
  h.context.renderDeepSeekRows("单项说明");
  assert.match(h.elements.get("deepseekRows").innerHTML, /单项说明/);
  h.context.state.symbol = "<symbol>";
  h.context.renderDeepSeekRows(null);
  assert.match(h.elements.get("deepseekRows").innerHTML, /&lt;symbol&gt;/);
});

test("null analysis and nullable opportunity entries do not break the renderer", () => {
  const h = harness();
  for (const response of [null, {}, { ok: true, analysis: null }, success({ summary: "说明", opportunities: [null] })]) {
    assert.doesNotThrow(() => h.context.renderDeepSeekAnalysis(response));
  }
  assert.equal(h.elements.get("deepseekHeadline").textContent, "说明");
  assert.match(h.elements.get("deepseekRows").innerHTML, /等待 DeepSeek 研究回执/);
});

test("actual strategy request and renderer publish a successful irregular JSON receipt once", async () => {
  const h = harness();
  h.context.response = success({ summary: "模型已返回", risk_notes: "风险文字", reasons: "依据文字" });
  await h.context.loadDeepSeekAnalysis();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].route, "/api/ai/deepseek/analyze");
  assert.match(h.elements.get("strategyAiState").textContent, /已完成/);
  assert.equal(h.elements.get("strategyAiState").dataset.requestAttempts, "1");
  assert.equal(h.elements.get("strategyAiState").dataset.signalStatus, "CALCULATED");
  assert.match(h.elements.get("strategyAiReport").innerHTML, /模型已返回/);
  assert.equal(h.context.state.strategyAiRunning, false);
  assert.equal(h.elements.get("analyzeStrategy").disabled, false);
});

test("actual failed request remains an error with no renderer retry", async () => {
  const h = harness();
  h.context.apiPost = async (route) => {
    h.requests.push({ route });
    const error = new Error("safe error");
    error.responseData = { ok: false, deepseek: { ok: false, error: "接口暂不可用", request_attempts: 1 } };
    throw error;
  };
  await h.context.loadDeepSeekAnalysis();
  assert.equal(h.requests.length, 1);
  assert.equal(h.elements.get("strategyAiReport").textContent, "接口暂不可用");
  assert.equal(h.elements.get("strategyAiState").dataset.requestAttempts, "1");
  assert.equal(h.context.state.strategyAiRunning, false);
});
