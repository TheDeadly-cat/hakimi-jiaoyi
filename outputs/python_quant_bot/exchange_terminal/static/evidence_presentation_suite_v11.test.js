"use strict";

const path = require("node:path");
const { spawnSync } = require("node:child_process");

for (const suite of [
  "evidence_presentation_suite_v10.test.js",
  "evidence_temporal_stability_report21_lockboard.test.js",
]) {
  const result = spawnSync(process.execPath, [path.join(__dirname, suite)], { encoding: "utf8" });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) process.exit(result.status === null ? 1 : result.status);
}

process.stdout.write("evidence presentation suite v11: 2/2 suites PASS\n");
