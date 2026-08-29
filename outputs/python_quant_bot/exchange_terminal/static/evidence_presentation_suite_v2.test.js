"use strict";

const path = require("node:path");
const { spawnSync } = require("node:child_process");

for (const file of [
  "evidence_presentation_suite.test.js",
  "evidence_complete_link_migration.test.js",
]) {
  const result = spawnSync(process.execPath, [path.join(__dirname, file)], {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

console.log("evidence presentation suite v2 passed");
