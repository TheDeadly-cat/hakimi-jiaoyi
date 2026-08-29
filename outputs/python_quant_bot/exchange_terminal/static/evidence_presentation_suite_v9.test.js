"use strict";

const path = require("node:path");
const { spawnSync } = require("node:child_process");

const suites = [
  "evidence_presentation_suite_v8.test.js",
  "evidence_cluster_stability_registry_migration.test.js",
];

for (const suite of suites) {
  const result = spawnSync(process.execPath, [path.join(__dirname, suite)], {
    encoding: "utf8",
  });
  if (result.stdout) {
    process.stdout.write(result.stdout);
  }
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }
  if (result.status !== 0) {
    process.exit(result.status === null ? 1 : result.status);
  }
}

process.stdout.write("evidence presentation suite v9: 2/2 suites PASS\n");
