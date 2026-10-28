"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");

// Exercise the shipped functions in an offline VM, without booting the terminal,
// starting paper trading, touching account data, or contacting an AI provider.
function extract(name) {
  const offset = source.indexOf(`function ${name}(`);
  assert.ok(offset >= 0, `Missing actual app function: ${name}`);
  const start = source.slice(offset - 6, offset) === "async " ? offset - 6 : offset;
  const next = /\n(?:async )?function \w+\(/g;
  next.lastIndex = offset + name.length + 10;
  return source.slice(start, next.exec(source)?.index ?? source.length);
}

function harness() {
  const elements = new Map();
  const requests = [];
  const el = (id) => {
    if (!elements.has(id)) elements.set(id, { textContent: "", innerHTML: "", disabled: false });
    return elements.get(id);
  };
  const context = vm.createContext({
    state: { orderFilter: "ALL" }, $: el,
    api: async (route) => { requests.push(route); return { ledger: [] }; },
    apiMutation: async (route) => {
      requests.push(route);
      return { ok: true, export: { path: "C:\\旧数据\\订单.csv", rows: 2, truncated: false } };
    },
  });
  const functions = ["number", "timeText", "escapeHtml", "renderOrders", "renderOrderHistory", "loadLedger", "exportRecords", "exportOrders", "exportLedger"];
  vm.runInContext(functions.map(extract).join("\n"), context);
  return { context, el, requests };
}

function plainText(html) {
  return html.replace(/<[^>]+>/g, "")
    .replaceAll("&lt;", "<").replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"').replaceAll("&#39;", "'").replaceAll("&amp;", "&");
}

test("order and history records preserve Chinese, signs and text-like tags without injecting elements", () => {
  const h = harness();
  const rows = [
    { time: 1000, side: "BUY", price: 12.5, quantity: 2, order_type: "LIMIT", reason: "旧单买入" },
    { time: 2000, side: '<img src=x onerror="bad()">', price: -12.5, quantity: -0.25,
      order_type: "<b>条件单</b>", reason: '中文 & <script>旧备注</script> "原文"', fee: -0.5,
      slippage_pct: 1.25, funding_estimate: -1, funding_charged: 2, reduce_only: true },
  ];
  const original = JSON.stringify(rows);
  h.context.renderOrders(rows);
  h.context.renderOrderHistory(rows);
  for (const id of ["orderRows", "historyOrderRows"]) {
    const html = h.el(id).innerHTML;
    assert.doesNotMatch(html, /<(?:img|script|b)(?:\s|>)/i);
    const text = plainText(html);
    assert.ok(text.includes(rows[1].side));
    assert.ok(text.includes(rows[1].reason));
    assert.ok(text.includes(rows[1].order_type));
    assert.match(text, /-12\.50/);
    assert.match(text, /-0\.250000/);
    assert.match(text, /fee -0\.5000/);
    assert.match(text, /12\.50/);
    assert.ok(text.indexOf(rows[1].reason) < text.indexOf("旧单买入"), "newest first");
  }
  assert.equal(JSON.stringify(rows), original, "rendering cannot modify old records");
  assert.match(h.el("orderRows").innerHTML, /funding est\. -1\.0000/);
  assert.match(h.el("orderRows").innerHTML, /funding charged 2\.0000/);
});

test("existing side filter remains effective and empty views clearly explain missing records", () => {
  const h = harness();
  const rows = [{ time: 1000, side: "BUY", price: 10, quantity: 1, reason: "买入记录" },
    { time: 2000, side: "SELL", price: 11, quantity: -1, reason: "卖出记录" }];
  h.context.state.orderFilter = "BUY";
  h.context.renderOrders(rows);
  assert.equal(h.el("orderSummary").textContent, "1 orders");
  assert.match(h.el("orderRows").innerHTML, /买入记录/);
  assert.doesNotMatch(h.el("orderRows").innerHTML, /卖出记录/);
  h.context.state.orderFilter = "COVER";
  h.context.renderOrders(rows);
  assert.match(h.el("orderRows").innerHTML, /当前筛选下没有模拟订单/);
  h.context.renderOrders([]);
  h.context.renderOrderHistory([]);
  assert.match(h.el("orderRows").innerHTML, /暂无模拟订单记录/);
  assert.match(h.el("historyOrderRows").innerHTML, /暂无模拟订单记录/);
});

test("event type and JSON remain text; empty or failed reads cannot erase previous entries", async () => {
  const h = harness();
  const row = { time: 1000, type: "<img src=x>中文", change: -2, reason: '<script>旧记录</script> & "保留"' };
  const original = JSON.stringify(row);
  h.context.api = async () => ({ ledger: [row] });
  await h.context.loadLedger();
  const html = h.el("ledgerRows").innerHTML;
  assert.doesNotMatch(html, /<(?:img|script)(?:\s|>)/i);
  assert.ok(plainText(html).includes(original));
  assert.equal(JSON.stringify(row), original);
  h.context.api = async () => { throw new Error("后台连接断开"); };
  await h.context.loadLedger();
  assert.equal(h.el("ledgerRows").innerHTML, html);
  assert.match(h.el("ledgerSummary").textContent, /读取失败：后台连接断开/);
  h.context.api = async () => ({ ledger: [] });
  await h.context.loadLedger();
  assert.match(h.el("ledgerRows").innerHTML, /暂无终端事件记录/);
});

test("both export buttons share one flight and recover their original enabled state", async () => {
  const h = harness();
  let finish;
  h.context.apiMutation = (route) => {
    h.requests.push(route);
    return new Promise((resolve) => { finish = resolve; });
  };
  const first = h.context.exportOrders();
  assert.equal(h.el("exportOrders").disabled, true);
  assert.equal(h.el("exportLedger").disabled, true);
  assert.equal(await h.context.exportOrders(), false);
  assert.equal(await h.context.exportLedger(), false);
  assert.deepEqual(h.requests, ["/api/export/orders"]);
  finish({ export: { path: "C:\\中文\\历史.csv", rows: 0, truncated: false } });
  assert.equal(await first, true);
  assert.equal(h.el("exportOrders").disabled, false);
  assert.equal(h.el("exportLedger").disabled, false);
  assert.equal(h.context.state.recordsExportPending, false);
  assert.match(h.el("exportState").textContent, /订单已导出 0 行（完整历史）/);
  assert.equal(h.el("exportPath").textContent, "C:\\中文\\历史.csv");
  assert.deepEqual(h.requests, ["/api/export/orders", "/api/ledger?limit=80"]);
});

test("export failures are visible, retain the last successful file path and allow a manual retry", async () => {
  const h = harness();
  await h.context.exportOrders();
  const oldPath = h.el("exportPath").textContent;
  h.context.apiMutation = async () => { throw new Error("磁盘空间不足 <旧提示>"); };
  h.el("exportLedger").disabled = true;
  assert.equal(await h.context.exportOrders(), false);
  assert.equal(h.el("exportPath").textContent, oldPath);
  assert.equal(h.el("exportState").textContent, "导出失败：磁盘空间不足 <旧提示>");
  assert.equal(h.el("exportOrders").disabled, false);
  assert.equal(h.el("exportLedger").disabled, true, "pre-existing disable is preserved");
  assert.equal(h.context.state.recordsExportPending, false);
  h.context.apiMutation = async () => ({ export: { path: "C:\\新事件.csv", rows: 12 } });
  assert.equal(await h.context.exportLedger(), true);
  assert.equal(h.el("exportPath").textContent, "C:\\新事件.csv");
  assert.equal(h.el("exportState").textContent, "事件已导出 12 行");
});

test("partial and alternate export receipts display row counts without claiming complete history", async () => {
  const h = harness();
  h.context.apiMutation = async () => ({ rows: 5000, export: { path: "C:\\partial.csv", truncated: true, total_rows: 6001 } });
  assert.equal(await h.context.exportLedger(), true);
  assert.match(h.el("exportState").textContent, /5000 \/ 6001 行（部分记录/);
  assert.doesNotMatch(h.el("exportState").textContent, /完整历史/);
  h.context.apiMutation = async () => ({ path: "C:\\flat.csv", rows: 7 });
  assert.equal(await h.context.exportOrders(), true);
  assert.equal(h.el("exportState").textContent, "订单已导出 7 行");
  h.context.apiMutation = async () => ({ export: { path: "C:\\count.csv", row_count: 9, truncated: true } });
  assert.equal(await h.context.exportLedger(), true);
  assert.match(h.el("exportState").textContent, /9 行（部分记录/);
});

test("incomplete export receipts fail clearly instead of replacing the successful path with undefined", async () => {
  const h = harness();
  await h.context.exportOrders();
  const oldPath = h.el("exportPath").textContent;
  for (const receipt of [{}, { rows: -1, path: "new.csv" }, { rows: 1.2, path: "new.csv" }, { rows: 0, path: "" }, { rows: null, path: "new.csv" }]) {
    h.context.apiMutation = async () => ({ export: receipt });
    assert.equal(await h.context.exportLedger(), false);
    assert.equal(h.el("exportPath").textContent, oldPath);
    assert.match(h.el("exportState").textContent, /导出失败：服务未返回完整/);
    assert.equal(h.context.state.recordsExportPending, false);
    assert.equal(h.el("exportOrders").disabled, false);
    assert.equal(h.el("exportLedger").disabled, false);
  }
});
