"use strict";

const path = require("path");
const { spawnSync } = require("child_process");

const suites = [
  "evidence_presentation_suite_v2.test.js",
  "evidence_strata_independence.test.js",
];

for (const suite of suites) {
  const result = spawnSync(process.execPath, [path.join(__dirname, suite)], {
    encoding: "utf8",
  });
  if (result.stdout) {
    process.stdout.write(result.stdout);
  }
  if (result.status !== 0) {
    if (result.stderr) {
      process.stderr.write(result.stderr);
    }
    process.exit(result.status || 1);
  }
}

console.log("PASS evidence presentation suite v3");
