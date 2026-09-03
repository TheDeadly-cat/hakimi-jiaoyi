"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const publicViewStart = appSource.indexOf("function platformMarketTruthView(");
const rendererStart = appSource.indexOf("function renderPlatformMarketTruth(", publicViewStart);
assert.ok(publicViewStart >= 0, "public market truth projection consumer must exist");
assert.ok(rendererStart > publicViewStart, "market truth renderer must follow the public consumer");

const publicViewSource = appSource.slice(publicViewStart, rendererStart);
assert.match(publicViewSource, /truth\.research_projection/);
assert.match(
  appSource,
  /const MARKET_DATA_RESEARCH_PROJECTION_SCHEMA = "market-data-research-projection-v1";/,
);
assert.match(
  publicViewSource,
  /projection\.schema_version === MARKET_DATA_RESEARCH_PROJECTION_SCHEMA/,
);
assert.match(publicViewSource, /SOURCE[\s\S]*GAP[\s\S]*MATURITY[\s\S]*PERMISSION/);
assert.match(publicViewSource, /permissionKeys\.every/);
assert.match(publicViewSource, /Object\.keys\(permission\)\.length/);
assert.match(publicViewSource, /legacy\.status === "BLOCK"/);
assert.doesNotMatch(publicViewSource, /readyContractComplete/);
assert.doesNotMatch(publicViewSource, /PLATFORM_MARKET_STATUSES/);
assert.doesNotMatch(publicViewSource, /REALTIME_READY/);
assert.doesNotMatch(publicViewSource, /["']READY["']/);

const nextFunctionStart = appSource.indexOf("\nfunction ", rendererStart + 1);
const rendererSource = appSource.slice(
  rendererStart,
  nextFunctionStart > rendererStart ? nextFunctionStart : appSource.length,
);
assert.match(rendererSource, /行情研究成熟度/);
assert.doesNotMatch(rendererSource, /原始行情证据状态|原始状态|原始行情状态/);

assert.match(appSource, /marketTruth\?\.status === "READY"/);
assert.match(appSource, /marketTruth\?\.mode === "REALTIME_READY"/);

console.log("ADR0553_RENDERER_CONTRACT=PASS");
console.log("NETWORK_CALLS=0");
console.log("RUNTIME_MUTATIONS=false");
