"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const math = require("./indicator_math.js");

test("panning and playback preserve the same timestamp values", () => {
  const rows = Array.from({length: 240}, (_, i) => ({close: 40 + i / 20 + Math.sin(i / 4)}));
  const full = math.chartWindow(rows);
  for (const [start, end] of [[0, 40], [55, 140], [140, 240], [80, 81]]) {
    const viewport = math.chartWindow(rows.slice(0, end), start, end);
    for (const key of ["ma20", "ma60", "bollinger"]) {
      assert.deepEqual(viewport[key], full[key].slice(start, end));
    }
  }
  assert.notEqual(math.chartWindow(rows, 100, 160).ma60[0], null, "left edge retains pre-window history");
  assert.equal(math.chartWindow(rows.slice(0, 50)).ma60[49], null);
});

test("known values, no fill, and flat RSI", () => {
  assert.deepEqual(math.sma([1, 2, 3], 3), [null, null, 2]);
  assert.equal(math.rsi([3, 3, 3, 3], 3)[3], 50);
  assert.equal(math.rsi([1, 2, 3, 4], 3)[3], 100);
  assert.equal(math.rsi([4, 3, 2, 1], 3)[3], 0);
  assert.deepEqual(math.ema([1, 2, null, 4], 3), [1, 1.5, null, 4]);
  assert.deepEqual(math.sma([1, "2", 3], 3), [null, null, null]);
  assert.throws(() => math.sma([1], 0));
  assert.deepEqual(math.sma([1e308, 1e308], 2), [null, null]);
  assert.deepEqual(math.bollinger([1e308, -1e308], 2), [null, null]);
});

test("the real chart breaks the path at missing observations", () => {
  const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
  const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const start = source.indexOf("function drawLineOverlay(");
  const end = source.indexOf("\nfunction ", start + 1);
  const calls = [];
  const ctx = {beginPath(){},moveTo(x,y){calls.push(["move",x,y]);},
    lineTo(x,y){calls.push(["line",x,y]);},stroke(){calls.push(["stroke"]);}};
  const context = vm.createContext({ctx});
  vm.runInContext(source.slice(start, end) + "\ndrawLineOverlay(ctx,[1,null,3,null],x=>x,y=>y,'red');", context);
  assert.deepEqual(calls, [["move",0,1],["move",2,3],["stroke"]]);
});
