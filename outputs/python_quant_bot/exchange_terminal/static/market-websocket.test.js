"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const market = require("./market-websocket");

function harness(extra = {}) {
  const sockets = [], timers = new Map(), statuses = [], data = [];
  let counter = 0;
  class FakeSocket {
    constructor(url) { this.url = url; this.sent = []; this.closed = false; sockets.push(this); }
    send(value) { this.sent.push(value); }
    close() { this.closed = true; this.onclose?.(); }
    open() { this.onopen?.(); }
    message(value) { this.onmessage?.({ data: typeof value === "string" ? value : JSON.stringify(value) }); }
  }
  const options = { WebSocketCtor: FakeSocket, setTimer(fn, ms) { timers.set(++counter, { fn, ms }); return counter; },
    clearTimer(id) { timers.delete(id); }, onStatus: (value) => statuses.push(value),
    onData: (value) => data.push(value), ...extra };
  return { sockets, timers, statuses, data, options, fire(ms) {
    const found = [...timers].find(([, item]) => item.ms === ms);
    assert.ok(found, `timer ${ms}`); timers.delete(found[0]); found[1].fn();
  } };
}
const pub = { channel: "tickers", instId: "BTC-USDT" };
const candle = { channel: "candle1m", instId: "BTC-USDT" };
const ack = (arg) => ({ event: "subscribe", arg });
const event = (arg) => ({ arg, data: [{ last: "123" }] });

test("443 public and business subscriptions stay separate and readiness waits for both acknowledgments", () => {
  const h = harness();
  const session = market.createSession({ ...h.options, publicArgs: [pub], businessArgs: [candle] }); session.start();
  assert.deepEqual(h.sockets.map((s) => s.url), [market.URLS.public, market.URLS.business]);
  assert.ok(h.sockets.every((s) => !s.url.includes(":8443")));
  h.sockets.forEach((s) => s.open());
  assert.deepEqual(JSON.parse(h.sockets[0].sent[0]).args, [pub]);
  assert.deepEqual(JSON.parse(h.sockets[1].sent[0]).args, [candle]);
  assert.equal(h.statuses.at(-1).ready, false);
  h.sockets[0].message(ack(pub)); assert.equal(h.statuses.at(-1).ready, false);
  h.sockets[1].message(ack(candle)); assert.equal(h.statuses.at(-1).ready, true);
  session.close();
});
test("provider subscription errors remain visible even if other channels acknowledge", () => {
  const h = harness(); const session = market.createSession({ ...h.options, publicArgs: [pub], businessArgs: [candle] }); session.start();
  h.sockets.forEach((s) => s.open());
  h.sockets[1].message({ event: "error", code: "60018", msg: "channel rejected" });
  h.sockets[0].message(ack(pub)); h.sockets[1].message(ack(candle));
  assert.equal(h.statuses.at(-1).ready, false); assert.equal(h.statuses.at(-1).error, true);
  assert.equal(h.statuses.at(-1).groups.business.reason, "subscription_error:60018");
  session.close();
});
test("obsolete socket callbacks and timers cannot write after symbol identity changes", () => {
  let current = true;
  const h = harness({ isCurrent: () => current });
  const session = market.createSession({ ...h.options, publicArgs: [pub] }); session.start();
  const old = h.sockets[0]; old.open(); const callback = old.onmessage;
  old.close(); current = false; h.fire(3000);
  callback({ data: JSON.stringify(event(pub)) });
  assert.equal(h.data.length, 0); assert.equal(h.sockets.length, 1); assert.equal(h.timers.size, 0);
});
test("reconnection resubscribes and ignores late data from the closed transport", () => {
  const h = harness(); const session = market.createSession({ ...h.options, publicArgs: [pub] }); session.start();
  const old = h.sockets[0]; old.open(); const callback = old.onmessage;
  old.close(); h.fire(3000); const next = h.sockets[1]; next.open(); next.message(ack(pub));
  callback({ data: JSON.stringify(event(pub)) }); assert.equal(h.data.length, 0);
  next.message(event({ ...pub, instId: "ETH-USDT" })); assert.equal(h.data.length, 0);
  next.message(event(pub)); assert.equal(h.data.length, 1);
  assert.deepEqual(JSON.parse(next.sent[0]).args, [pub]); session.close();
});
test("heartbeat handles plain pong and reconnects only after a missing response", () => {
  const h = harness(); const session = market.createSession({ ...h.options, publicArgs: [pub] }); session.start();
  const socket = h.sockets[0]; socket.open(); h.fire(20000);
  assert.equal(socket.sent.at(-1), "ping"); socket.message("pong");
  assert.equal([...h.timers.values()].some((item) => item.ms === 10000), false);
  h.fire(20000); h.fire(10000); assert.equal(socket.closed, true);
  h.fire(3000); assert.equal(h.sockets.length, 2); session.close(); assert.equal(h.timers.size, 0);
});
test("only public read channels are accepted and malformed frames do not crash", () => {
  assert.throws(() => market.createSession({ publicArgs: [{ channel: "orders", instId: "BTC-USDT" }] }), /subscription_invalid/);
  const h = harness(); const session = market.createSession({ ...h.options, publicArgs: [pub] }); session.start();
  h.sockets[0].open(); h.sockets[0].message("not-json");
  assert.equal(h.statuses.at(-1).groups.public.reason, "invalid_message");
  h.sockets[0].message(event({ channel: "candle1m", instId: "BTC-USDT" }));
  assert.equal(h.data.length, 0); session.close();
});
function appFunctions() {
  const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  return source.slice(source.indexOf("function connectSocket()"), source.indexOf("async function fallbackPoll()"));
}
test("actual app rapid symbol switch and frozen replay reject both streams and cancel reconnects", () => {
  const h = harness(); const calls = [];
  const context = { state: { symbol: "BTC-USDT", bar: "1m", socket: null, marketSocket: null }, runtime: { symbolVersion: 1 },
    window: { HAKIMI_RUNTIME_MODE: { localOnly: false }, HakimiMarketWebSocket: {
      createSession: (options) => market.createSession({ ...h.options, ...options }) } },
    markets: [{ source: "okx", instId: "BTC-USDT" }], clearTimeout() {}, isStockMarket: () => false,
    okxInstId: (symbol) => symbol, setConnection: (...args) => calls.push(["status", ...args]),
    updateTicker: (...args) => calls.push(["ticker", ...args]), updateBook: () => calls.push(["book"]),
    addTrades: () => calls.push(["trade"]), updateCandle: () => calls.push(["candle"]),
    updateMarketFromTicker: () => calls.push(["market"]), scheduleMarketRender() {}, $: () => ({ textContent: "" }) };
  vm.createContext(context); vm.runInContext(appFunctions(), context);
  context.connectSocket(); const old = h.sockets.slice(); old.forEach((s) => s.open());
  const stale = old.map((s) => s.onmessage);
  context.state.symbol = "ETH-USDT"; context.runtime.symbolVersion++; context.connectSocket();
  stale.forEach((fn) => fn({ data: JSON.stringify(event(candle)) }));
  assert.equal(calls.filter((row) => row[0] === "candle").length, 0);
  const next = h.sockets.slice(2); next.forEach((s) => s.open());
  next[1].message(event({ ...candle, instId: "ETH-USDT" }));
  assert.equal(calls.filter((row) => row[0] === "candle").length, 1);
  context.connectMarketSocket(); const list = h.sockets.at(-1); list.open();
  context.state.frozenQuantReplay = { run_id: "frozen" };
  next[1].message(event({ ...candle, instId: "ETH-USDT" })); list.message(event(pub));
  assert.equal(calls.filter((row) => row[0] === "candle").length, 1);
  assert.equal(calls.filter((row) => row[0] === "market").length, 0);
  assert.equal(h.timers.size, 0);
  const count = h.sockets.length; context.connectSocket(); context.connectMarketSocket();
  assert.equal(h.sockets.length, count);
});
test("actual app local mode creates no sockets and helper is included once before app", () => {
  const h = harness(); const context = { state: {}, window: { HAKIMI_RUNTIME_MODE: { localOnly: true },
    HakimiMarketWebSocket: { createSession: () => { throw Error("must not connect"); } } }, clearTimeout() {} };
  vm.createContext(context); vm.runInContext(appFunctions(), context); context.connectSocket(); context.connectMarketSocket();
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.equal((html.match(/src="\.\/market-websocket\.js/g) || []).length, 1);
  assert.ok(html.indexOf('./market-websocket.js') < html.indexOf('./app.js'));
  assert.equal(h.sockets.length, 0);
});
