"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
function extract(name) {
  const offset = source.indexOf(`function ${name}(`);
  assert.ok(offset >= 0);
  const start = source.slice(offset - 6, offset) === "async " ? offset - 6 : offset;
  const next = /\n(?:async )?function \w+\(/g; next.lastIndex = offset + name.length + 10;
  return source.slice(start, next.exec(source)?.index ?? source.length);
}
test("archived development assistant explains its boundary without requests or erasing draft text", async () => {
  const elements = new Map();
  const context = vm.createContext({
    $: id => {
      if (!elements.has(id)) elements.set(id, { value: "previous unsent draft", textContent: "", setAttribute(name, value) { this[name] = value; } });
      return elements.get(id);
    },
    api() { assert.fail("archived management must not request drafts"); },
    apiMutation() { assert.fail("archived management must not mutate or call models"); },
  });
  for (const name of ["showArchivedCodeWorker", "renderCodeWorkerDrafts", "loadCodeWorkerDrafts", "runCodeWorker", "archiveCodeWorkerDraft"]) vm.runInContext(extract(name), context);
  for (const name of ["loadCodeWorkerDrafts", "runCodeWorker", "archiveCodeWorkerDraft"]) {
    assert.equal((await context[name]("old-draft-id")).status, "ARCHIVED");
  }
  assert.match(elements.get("codeWorkerRows").textContent, /旧草稿文件按原身份保留/);
  assert.match(elements.get("codeWorkerRows").textContent, /行情与策略 AI 分析仍使用各自入口/);
  for (const id of ["codeWorkerTask", "codeWorkerMode", "runCodeWorker"]) {
    assert.equal(elements.get(id).disabled, true);
    assert.equal(elements.get(id)["aria-disabled"], "true");
    assert.equal(elements.get(id).value, "previous unsent draft");
  }
});

test("local-only opportunity and platform review buttons do not issue model requests", async () => {
  const elements = new Map();
  const context = vm.createContext({
    window: { HAKIMI_RUNTIME_MODE: { localOnly: true } },
    $: id => { if (!elements.has(id)) elements.set(id, { textContent: "previous report" }); return elements.get(id); },
    api() { assert.fail("local-only mode must not invoke provider-backed GET endpoints"); },
    renderDeepSeekAnalysis() { assert.fail("there was no AI response to render"); },
  });
  for (const name of ["loadDeepSeekOpportunities", "loadDeepSeekPlatformReview"]) vm.runInContext(extract(name), context);
  await context.loadDeepSeekOpportunities();
  assert.match(elements.get("deepseekState").textContent, /本地模式.*未发送/);
  elements.get("deepseekState").textContent = "previous report";
  await context.loadDeepSeekOpportunities(true);
  assert.equal(elements.get("deepseekState").textContent, "previous report");
  await context.loadDeepSeekPlatformReview();
  assert.match(elements.get("deepseekState").textContent, /本地模式.*未发送/);
});
