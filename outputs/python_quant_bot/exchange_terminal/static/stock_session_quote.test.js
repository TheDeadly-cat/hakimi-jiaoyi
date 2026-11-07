"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const guard = require("./stock_quote_guard.js");
const app = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");

function extract(name) {
  const start = app.indexOf(`function ${name}(`);
  assert.ok(start >= 0, name);
  const next = /\n(?:async )?function \w+\(/g;
  next.lastIndex = start + 10;
  return app.slice(start, next.exec(app)?.index ?? app.length).trim();
}

function quote(session = "pre", price = 338.58, fallback = false) {
  const row = { price, change_pct: -1.271, volume: 240, turnover: 81259 };
  return {
    symbol: "AAPL", instId: "US.AAPL", last: 342.94, change24h_pct: 2,
    prevClose: 336.22, open24h: 337, high24h: 344, low24h: 336,
    vol24h: 9000000, volCcy24h: 3000000000, source: "futu", ts: Date.now(),
    quote_quality: { status: "READY", quarantined: false },
    change_basis: "previous_close",
    market_session: {
      phase: session, active_session: fallback ? "regular" : session,
      active_session_label: fallback ? "盘中" : { pre: "盘前", post: "盘后", overnight: "夜盘", regular: "盘中" }[session],
      active_price: fallback ? 342.94 : price,
      active_change_pct: fallback ? 2 : -1.271,
      active_price_is_fallback: fallback,
      status: fallback ? "SESSION_PRICE_UNAVAILABLE" : "LIVE_SESSION",
      status_label: fallback ? "盘前价格不可用 · 常规时段参考价" : "盘前进行中",
      sessions: { [session]: row, regular: { price: 342.94, change_pct: 2, volume: 9000000, turnover: 3000000000 } },
    },
  };
}

function harness(selected = "all") {
  const elements = {};
  const labels = {};
  const seen = {};
  const noop = () => {};
  const state = {
    symbol: "AAPL", bar: "1m", chartDataSymbol: "AAPL", stockSession: selected,
    candles: [
      { ts: Date.now() - 60000, open: 341, high: 343, low: 340, close: 341 },
      { ts: Date.now(), open: 342, high: 343, low: 341, close: 342.94 },
    ],
    chartQuality: { source: "futu", preview: false }, frozenQuantReplay: null,
  };
  const scope = {
    state, markets: [{ symbol: "AAPL", type: "stock", source: "futu" }],
    window: { HakimiStockQuoteGuard: guard, HAKIMI_RUNTIME_MODE: {} },
    document: { querySelector: () => elements.meta ||= {} },
    $: id => elements[id] ||= { textContent: "", parentElement: { querySelector: () => labels[id] ||= {} } },
    isStockMarket: () => true, isPreviewChartSource: () => false,
    currentMarket: () => scope.markets[0], okxInstId: value => value,
    number: (value, digits) => Number(value).toFixed(digits),
    numericMarketValue: value => Number(value || 0), cssMove: () => "", compact: String,
    bidAskText: () => "", timeText: String, setConnection: text => { seen.connection = text; },
    addStockPriceLog: data => { seen.logged = data; },
    maybeRefreshActiveStockCandles: noop, scheduleMarketRender: noop,
    renderDesktopStatus: noop, renderSideInsights: noop, renderLiveSourceBar: noop,
    renderMarketWorkflowStrip: noop, previewPriceForSymbol: () => 0,
    marketTypeLabel: () => "股票", stockSourceLabel: () => "Futu",
    barToMs: () => 60000, drawChart: noop, Date,
  };
  vm.createContext(scope);
  const names = [
    "stockSessionQuoteForDisplay", "syncQuoteFieldLabels", "acceptStockQuoteContext",
    "activeSymbolMetaText", "syncActiveSymbolHeader", "marketVolumeForDisplay",
    "activeStockChartQuoteGuard", "freshAcceptedStockQuote", "updateMarketFromTicker",
    "canonicalTickerSymbol", "stockSessionAllowsPriceOverlay", "stockQuoteOverlayDecision",
    "syncLiveCandle", "syncActiveMarketQuote", "updateTicker",
  ];
  vm.runInContext(names.map(extract).join("\n"), scope);
  return { scope, state, elements, labels, seen };
}

test("active extended session price drives headline, market row, context, log and matching chart", () => {
  for (const session of ["pre", "post", "overnight"]) {
    const { scope, state, elements, labels, seen } = harness("all");
    const input = quote(session); const before = JSON.stringify(input);
    scope.updateTicker(input, "FUTU");
    assert.equal(JSON.stringify(input), before, "provider regular fields must remain untouched");
    assert.equal(elements.lastPrice.textContent, "338.58");
    assert.equal(state.lastPrice, 338.58);
    assert.equal(scope.markets[0].price, "338.58");
    assert.equal(scope.markets[0].quoteChangeBasis, "provider_session");
    assert.equal(scope.markets[0].quotePreviousClose, null);
    assert.equal(scope.markets[0].baseVolume24h, 240);
    assert.equal(state.stockQuoteContext.last, 338.58);
    assert.equal(state.stockQuoteContext.regular_quote.last, 342.94);
    assert.equal(scope.markets[0].regularQuote.last, 342.94);
    assert.equal(seen.logged.last, 338.58);
    assert.equal(state.candles.at(-1).close, 338.58);
    assert.match(labels.high24h.textContent, /常规高.*参考/);
    assert.equal(elements.vol24h.textContent, "240");
  }
});

test("regular chart selection rejects premarket overlay while current quote remains premarket", () => {
  const { scope, state } = harness("regular");
  const before = JSON.stringify(state.candles);
  scope.updateTicker(quote(), "FUTU");
  assert.equal(state.lastPrice, 338.58);
  assert.equal(JSON.stringify(state.candles), before);
});

test("missing extended price is explicit regular reference and never overlays current chart", () => {
  const { scope, state, seen } = harness("all");
  const before = JSON.stringify(state.candles);
  scope.updateTicker(quote("pre", 0, true), "FUTU");
  assert.equal(state.lastPrice, 342.94);
  assert.equal(state.stockQuoteContext.session_price_is_reference, true);
  assert.match(seen.connection, /价格不可用.*参考价/);
  assert.equal(JSON.stringify(state.candles), before);
});

test("batch ticker path uses identical session price and repeated projection preserves regular origin", () => {
  const { scope, state } = harness("all");
  scope.updateMarketFromTicker(quote());
  assert.equal(scope.markets[0].price, "338.58");
  assert.equal(state.lastPrice, 338.58);
  assert.equal(state.marketSession.active_session, "pre");
  assert.equal(state.candles.at(-1).close, 338.58);
  const first = scope.stockSessionQuoteForDisplay(quote());
  const second = scope.stockSessionQuoteForDisplay(first);
  assert.equal(second.last, 338.58);
  assert.equal(second.regular_quote.last, 342.94);
});

test("session selection never weakens price-quality guard or borrows regular change evidence", () => {
  const { scope, state } = harness("all");
  const input = quote("pre", 260);
  const before = JSON.stringify(state.candles);
  scope.updateTicker(input, "FUTU");
  assert.equal(JSON.stringify(state.candles), before);
  const projected = scope.stockSessionQuoteForDisplay(input);
  assert.equal(projected.prevClose, 0);
  assert.equal(projected.change_basis, "provider_session");
  assert.equal(guard.evaluateStockQuoteOverlay({
    price: projected.last, candleClose: 342.94, source: "futu",
    quoteQuality: projected.quote_quality, previousClose: projected.prevClose,
    changeBasis: projected.change_basis, changePct: projected.change24h_pct,
  }).allowed, false);
});

test("rejected fallback cannot replace a fresh accepted Futu quote or its session", () => {
  for (const method of ["updateTicker", "updateMarketFromTicker"]) {
    for (const missingMetadata of [false, true]) {
    const { scope, state, elements, seen } = harness("regular");
    state.candles.at(-1).close = 343.20;
    scope.updateTicker(quote("pre", 338.32), "FUTU");
    const context = JSON.stringify(state.stockQuoteContext);
    const market = JSON.stringify(scope.markets[0]);
    const connection = seen.connection;
    scope[method]({
      symbol: "AAPL", last: 343.20, source: missingMetadata ? "futu" : "stock_sqlite_cache", ts: Date.now(),
      quote_quality: missingMetadata ? null : { status: "DEGRADED" },
      market_session: missingMetadata ? null : { active_session: "regular", active_price: 343.20, status: "STALE" },
    });
    assert.equal(state.lastPrice, 338.32);
    assert.equal(elements.lastPrice.textContent, "338.32");
    assert.equal(JSON.stringify(state.stockQuoteContext), context);
    assert.equal(JSON.stringify(scope.markets[0]), market);
    assert.equal(state.marketSession.active_session, "pre");
    assert.equal(seen.connection, connection);
    assert.equal(state.candles.at(-1).close, 343.20);
    }
  }
});

test("fresh accepted source priority also applies before batch market mutation", () => {
  const { scope, state } = harness("regular");
  scope.updateTicker(quote("pre", 338.32), "FUTU");
  const market = JSON.stringify(scope.markets[0]);
  scope.updateMarketFromTicker({
    symbol: "AAPL", last: 342.94, source: "yahoo", ts: Date.now(),
    quote_quality: { status: "READY" }, change24h_pct: 0,
  });
  assert.equal(state.lastPrice, 338.32);
  assert.equal(JSON.stringify(scope.markets[0]), market);
});

test("stale future unknown invalid or untrusted current context cannot block the chart fallback", () => {
  const invalid = [
    { ts: 0 }, { ts: Date.now() - 120001 }, { ts: Date.now() + 60000 },
    { last: NaN }, { symbol: "TSLA" },
    { quote_quality: {} }, { quote_quality: { status: "DEGRADED" } },
    { quote_quality: { status: "READY", quarantined: true } },
    { source: "offline_seed" }, { session_price_is_reference: true },
    { last: 1000 },
  ];
  for (const override of invalid) {
    const { scope, state, elements } = harness("regular");
    state.candles.at(-1).close = 343.20;
    scope.updateTicker(quote("pre", 338.32), "FUTU");
    state.stockQuoteContext = { ...state.stockQuoteContext, ...override };
    scope.updateMarketFromTicker({ symbol: "AAPL", source: "futu", last: 342.94, ts: Date.now(), quote_quality: null });
    assert.equal(state.lastPrice, 343.20);
    assert.equal(elements.lastPrice.textContent, "343.20");
  }
});
