"use strict";

const assert = require("node:assert/strict");
const {
  chooseStockDisplayQuote,
  evaluateStockQuoteOverlay,
  shouldAcceptStockQuoteContext,
} = require("./stock_quote_guard.js");

function evaluate(overrides = {}) {
  return evaluateStockQuoteOverlay({
    price: 306,
    candleClose: 309,
    source: "futu",
    quoteQuality: { status: "READY", quarantined: false },
    changeBasis: "previous_close",
    previousClose: 304,
    changePct: (306 / 304 - 1) * 100,
    ...overrides,
  });
}

assert.equal(evaluate().allowed, true, "near READY Futu quote should be accepted");

assert.deepEqual(
  evaluate({ price: 195, source: "offline_seed", quoteQuality: { status: "STALE" } }).reason,
  "untrusted_source",
  "offline seed must never mutate a stock candle",
);

assert.equal(
  evaluate({ price: 195, previousClose: 194, changePct: (195 / 194 - 1) * 100 }).allowed,
  false,
  "a fake READY quote whose previous close disagrees with the chart must be rejected",
);

assert.equal(
  evaluate({ price: 115, candleClose: 100, previousClose: 100, changePct: 15 }).reason,
  "verified_large_move",
  "a large move with internally consistent evidence should be accepted",
);

assert.equal(
  evaluate({ price: 160, candleClose: 100, previousClose: 100, changePct: 60 }).reason,
  "hard_scale_mismatch",
  "a quote beyond the hard scale boundary must be rejected",
);

assert.equal(
  evaluate({ quoteQuality: { status: "READY", quarantined: true } }).reason,
  "quarantined_quote",
  "quarantined quotes must be rejected",
);

assert.equal(evaluate({ price: Number.NaN }).reason, "invalid_price");
assert.equal(evaluate({ source: "" }).reason, "untrusted_source");

const quarantinedDisplay = chooseStockDisplayQuote({
  price: 195,
  candleClose: 309,
  previousCandleClose: 304,
  source: "offline_seed",
  quoteQuality: { status: "STALE" },
  chartTrusted: true,
});
assert.equal(quarantinedDisplay.useChart, true);
assert.equal(quarantinedDisplay.displayPrice, 309);
assert.equal(Number(quarantinedDisplay.displayChangePct.toFixed(4)), Number(((309 / 304 - 1) * 100).toFixed(4)));

const initialPreviewDisplay = chooseStockDisplayQuote({
  price: 195,
  candleClose: 309,
  source: "offline_seed",
  quoteQuality: { status: "STALE" },
  chartTrusted: false,
});
assert.equal(initialPreviewDisplay.useChart, false);
assert.equal(initialPreviewDisplay.displayPrice, 195);

const verifiedDisplay = chooseStockDisplayQuote({
  price: 306,
  candleClose: 309,
  source: "futu",
  quoteQuality: { status: "READY" },
  chartTrusted: true,
});
assert.equal(verifiedDisplay.useChart, false);
assert.equal(verifiedDisplay.displayPrice, 306);

const acceptedHigherQuality = shouldAcceptStockQuoteContext({
  current: { symbol: "AAPL", source: "offline-seed", last: 195, ts: 1_000 },
  incoming: { symbol: "AAPL", source: "yahoo", last: 306, ts: 2_000 },
  nowMs: 3_000,
});
assert.equal(acceptedHigherQuality.allowed, true, "a better source may replace a seed quote");

const rejectedFallback = shouldAcceptStockQuoteContext({
  current: { symbol: "AAPL", source: "yahoo", last: 306, ts: 2_000 },
  incoming: { symbol: "AAPL", source: "offline-seed", last: 195, ts: 3_000 },
  nowMs: 4_000,
});
assert.equal(rejectedFallback.allowed, false);
assert.equal(rejectedFallback.reason, "lower_quality_source", "a fresh fallback must not overwrite a live quote");

const rejectedOlderSameSource = shouldAcceptStockQuoteContext({
  current: { symbol: "AAPL", source: "yahoo", last: 306, ts: 5_000 },
  incoming: { symbol: "AAPL", source: "yahoo", last: 305, ts: 4_000 },
  nowMs: 6_000,
});
assert.equal(rejectedOlderSameSource.allowed, false);
assert.equal(rejectedOlderSameSource.reason, "older_quote_timestamp");

console.log("stock_quote_guard.test.js: PASS");
