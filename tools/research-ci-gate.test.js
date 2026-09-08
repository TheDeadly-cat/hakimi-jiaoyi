"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const { REQUIRED_JOBS, evaluateRequiredJobs } = require("./research-ci-gate");
const allSucceeded = () => Object.fromEntries(
  REQUIRED_JOBS.map((job) => [job, { result: "success", outputs: {} }]),
);

assert.equal(evaluateRequiredJobs(allSucceeded()).success, true);
for (const job of REQUIRED_JOBS) {
  for (const status of ["failure", "cancelled", "skipped", "pending", "", null, true]) {
    const needs = allSucceeded();
    needs[job].result = status;
    assert.equal(evaluateRequiredJobs(needs).success, false, `${job}: ${status}`);
  }
  const missing = allSucceeded();
  delete missing[job];
  assert.equal(evaluateRequiredJobs(missing).success, false, `missing ${job}`);
}
for (const malformed of [null, [], {}, true, "success"]) {
  assert.equal(evaluateRequiredJobs(malformed).success, false);
}
assert.equal(evaluateRequiredJobs({ ...allSucceeded(), extra: { result: "success" } }).success, false);

// Exercise the actual executable/environment boundary used by Actions.
for (const [payload, expectedStatus] of [
  [JSON.stringify(allSucceeded()), 0],
  [JSON.stringify({ ...allSucceeded(), "mvp-contracts": { result: "skipped" } }), 1],
  ["not-json", 1],
  ["", 1],
]) {
  const result = spawnSync(process.execPath, [path.join(__dirname, "research-ci-gate.js")], {
    env: { ...process.env, RESEARCH_CI_NEEDS: payload },
    encoding: "utf8",
  });
  assert.equal(result.status, expectedStatus, result.stderr);
}
console.log("research CI aggregate gate tests passed");
