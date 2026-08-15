"use strict";

const assert = require("node:assert/strict");

global.window = global;
require("./chart_controller.js");

const { createRefreshCoordinator, inFlightKey } = global.HakimiChartController;

async function run() {
  let now = 1_000;
  let calls = 0;
  let release;
  const coordinator = createRefreshCoordinator({
    now: () => now,
    successCooldownMs: 60_000,
    failureBaseCooldownMs: 5_000,
    failureMaxCooldownMs: 60_000,
  });
  const aaplKey = inFlightKey({ requestSymbol: " aapl ", requestBar: "1d", requestSession: "REGULAR", limit: 520 });
  assert.equal(aaplKey, "AAPL|1d|regular");
  assert.equal(
    aaplKey,
    inFlightKey({ requestSymbol: "AAPL", requestBar: "1d", requestSession: "regular", limit: 300 }),
    "limit is a response-size preference and must not split the same market identity",
  );
  assert.notEqual(aaplKey, inFlightKey({ requestSymbol: "NVDA", requestBar: "1d", requestSession: "regular" }));
  assert.notEqual(aaplKey, inFlightKey({ requestSymbol: "AAPL", requestBar: "1m", requestSession: "regular" }));
  assert.notEqual(aaplKey, inFlightKey({ requestSymbol: "AAPL", requestBar: "1d", requestSession: "post" }));

  const first = coordinator.request({
    key: aaplKey,
    task: () => {
      calls += 1;
      return new Promise((resolve) => { release = resolve; });
    },
  });
  const joined = coordinator.request({
    key: aaplKey,
    manual: true,
    task: async () => {
      calls += 1;
      return "duplicate";
    },
  });
  assert.equal(first, joined, "same-key callers must receive the exact shared promise");
  assert.equal(coordinator.inFlightPromise(aaplKey), first);
  await Promise.resolve();
  assert.equal(calls, 1, "same-key automatic and manual refreshes must share one in-flight request");
  assert.equal(coordinator.inFlightCount(), 1);
  release("aapl-snapshot");
  const [fetchedResult, joinedResult] = await Promise.all([first, joined]);
  assert.equal(fetchedResult.status, "FETCHED");
  assert.equal(joinedResult.status, "FETCHED");
  assert.equal(joinedResult.joined, true);
  assert.equal(joinedResult.value, "aapl-snapshot");
  assert.equal(coordinator.inFlightCount(), 0);

  const cooldownResult = await coordinator.request({
    key: aaplKey,
    task: async () => {
      calls += 1;
      return "too-soon";
    },
  });
  assert.equal(cooldownResult.status, "COOLDOWN");
  assert.equal(calls, 1, "automatic refresh must honor the successful outcome cooldown");

  const manualResult = await coordinator.request({
    key: aaplKey,
    manual: true,
    task: async () => {
      calls += 1;
      return "manual-refresh";
    },
  });
  assert.equal(manualResult.status, "FETCHED");
  assert.equal(manualResult.value, "manual-refresh");
  assert.equal(calls, 2, "manual refresh may bypass cooldown when no request is in flight");

  const nvdaResult = await coordinator.request({
    key: "NVDA|1d|regular",
    task: async () => {
      calls += 1;
      return "nvda-snapshot";
    },
  });
  assert.equal(nvdaResult.status, "FETCHED");
  assert.equal(calls, 3, "different request keys must remain independent");

  let failedCalls = 0;
  const failing = createRefreshCoordinator({
    now: () => now,
    failureBaseCooldownMs: 5_000,
    failureMaxCooldownMs: 20_000,
  });
  await assert.rejects(failing.request({
    key: "AAPL|1m|regular",
    task: async () => {
      failedCalls += 1;
      throw new Error("upstream unavailable");
    },
  }), /upstream unavailable/);
  assert.equal(failing.outcome("AAPL|1m|regular").failureCount, 1);
  now += 4_999;
  const backedOff = await failing.request({
    key: "AAPL|1m|regular",
    task: async () => {
      failedCalls += 1;
      return "too-soon";
    },
  });
  assert.equal(backedOff.status, "COOLDOWN");
  assert.equal(failedCalls, 1, "automatic failure retry must wait for backoff");
}

run()
  .then(() => console.log("chart_controller.test.js: PASS"))
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
