"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const suites = [
  "evidence_presentation_suite_v13.test.js",
  "evidence_report22_date_grid_migration_lockboard.test.js",
];

for (const suite of suites) {
  const result = spawnSync(process.execPath, [path.join(__dirname, suite)], {
    encoding: "utf8",
    stdio: "pipe",
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) process.exit(result.status || 1);
}

console.log("evidence presentation suite v14: 2/2 suites PASS");
