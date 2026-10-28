"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");

function functionSource(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0);
  const next = /\n(?:async )?function \w+\(/g;
  next.lastIndex = start + name.length + 10;
  return source.slice(start, next.exec(source)?.index ?? source.length);
}

function status(payload) {
  const context = vm.createContext({ state: { futu: payload } });
  vm.runInContext(functionSource("futuStatusPresentation") + "\n" + functionSource("futuOpenDOnline"), context);
  return { ...context.futuStatusPresentation(), quoteUsable: context.futuOpenDOnline() };
}

test("an open TCP port alone does not claim usable quotes or a successful login", () => {
  for (const payload of [
    { opend_online: true, message: "OpenD online" },
    { opend_online: true, transport_status: "REACHABLE", login_status: "UNKNOWN", quote_status: "UNKNOWN" },
  ]) {
    const result = status(payload);
    assert.equal(result.quoteUsable, false);
    assert.equal(result.tone, "flat");
    assert.equal(result.label, "端口已连接");
  }
});

test("permission and login errors do not mislabel a reachable OpenD as offline", () => {
  const base = { opend_online: true, transport_status: "REACHABLE", quote_status: "ERROR" };
  assert.equal(status({ ...base, quote_error_type: "PERMISSION_DENIED" }).label, "无报价权限");
  assert.equal(status({ ...base, quote_error_type: "LOGIN_REQUIRED" }).label, "待登录");
  assert.equal(status({ ...base, login_status: "NOT_LOGGED_IN" }).quoteUsable, false);
  assert.equal(status({ ...base, quote_error_type: "TIMEOUT" }).label, "报价超时");
});

test("successful quotes are described as returned, without asserting real-time entitlement", () => {
  const result = status({ transport_status: "REACHABLE", quote_status: "READY", login_status: "UNKNOWN" });
  assert.equal(result.quoteUsable, true);
  assert.equal(result.label, "报价已返回");
  assert.doesNotMatch(result.label, /实时|登录/);
});

test("disconnected and local-only modes override stale quote success", () => {
  assert.equal(status({ transport_status: "UNREACHABLE", quote_status: "READY" }).quoteUsable, false);
  const local = status({ transport_status: "BLOCKED_LOCAL_MODE", quote_status: "READY" });
  assert.equal(local.label, "本地模式");
  assert.equal(local.quoteUsable, false);
  assert.equal(status({}).quoteUsable, false);
});
