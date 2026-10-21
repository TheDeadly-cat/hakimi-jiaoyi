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
  const next = /\n(?:async )?function \w+\(/g;
  next.lastIndex = offset + name.length + 10;
  return source.slice(offset, next.exec(source)?.index ?? source.length);
}

function harness() {
  const context = vm.createContext({
    state: {
      symbol: "AAPL", chartDataSymbol: "AAPL", bar: "5m", stockSession: "regular",
      candles: [], drawings: [], chartMeta: {}, chartQuality: { source: "futu" },
    },
    barToMs: () => 300000,
    frontendMarketAiLocal: () => ({}),
    visibleCandles: () => ({ candles: [] }),
    latestFibLevels: () => [],
    $: () => null,
  });
  for (const name of ["candleFromOkx", "candleFromCsv", "candleFromApi", "normalizeChartRows", "marketAiPayload"]) {
    vm.runInContext(extract(name), context);
  }
  return context;
}

const base = { ts: 1792504200000, ts_ms: 1792504200000, open: 100, high: 102, low: 99, close: 101, volume: 500 };

test("API and CSV preserve explicit completion and provisional evidence through chart normalization", () => {
  const h = harness();
  for (const convert of [h.candleFromApi, h.candleFromCsv]) {
    for (const [complete, provisional] of [[true, false], [false, true], [1, 0], [0, 1], ["1", "0"], ["0", "1"]]) {
      const input = { ...base, complete, provisional };
      const before = JSON.stringify(input);
      const converted = convert(input);
      const row = h.normalizeChartRows([converted])[0];
      assert.equal(row.complete, complete === true || complete === 1 || complete === "1");
      assert.equal(row.provisional, provisional === true || provisional === 1 || provisional === "1");
      assert.equal(row.ts, base.ts);
      assert.equal(row.close, base.close);
      assert.equal(JSON.stringify(input), before);
    }
  }
});

test("missing or unrecognized fields remain absent; one flag never invents its inverse", () => {
  const h = harness();
  for (const convert of [h.candleFromApi, h.candleFromCsv, (row) => h.normalizeChartRows([row])[0]]) {
    for (const value of [undefined, null, "", "false", "true", "unknown", 2, -1, NaN, {}, []]) {
      const row = convert({ ...base, complete: value, provisional: value });
      assert.equal(Object.hasOwn(row, "complete"), false);
      assert.equal(Object.hasOwn(row, "provisional"), false);
    }
    const onlyProvisional = convert({ ...base, provisional: false });
    assert.equal(onlyProvisional.provisional, false);
    assert.equal(Object.hasOwn(onlyProvisional, "complete"), false);
    const onlyComplete = convert({ ...base, complete: false });
    assert.equal(onlyComplete.complete, false);
    assert.equal(Object.hasOwn(onlyComplete, "provisional"), false);
  }
});

test("OKX confirmation accepts only explicit zero or one, including documented numeric strings", () => {
  const h = harness();
  const candle = [base.ts, 100, 102, 99, 101, 500, 500, 500];
  for (const confirm of [0, 1, "0", "1"]) {
    const row = h.normalizeChartRows([h.candleFromOkx([...candle, confirm])])[0];
    assert.equal(row.complete, confirm === 1 || confirm === "1");
    assert.equal(Object.hasOwn(row, "provisional"), false);
  }
  for (const confirm of [undefined, null, "", true, false, "true", "false", 2, -1, NaN]) {
    const row = h.candleFromOkx([...candle, confirm]);
    assert.equal(Object.hasOwn(row, "complete"), false);
    assert.equal(Object.hasOwn(row, "provisional"), false);
  }
});

test("chart normalization keeps explicit conflicting flags for downstream validation without resolving them", () => {
  const h = harness();
  const row = h.normalizeChartRows([{ ...base, complete: true, provisional: true }])[0];
  assert.equal(row.complete, true);
  assert.equal(row.provisional, true);
});
