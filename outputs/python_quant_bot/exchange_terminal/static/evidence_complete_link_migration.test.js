"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  presentCompleteLinkMigration,
  renderCompleteLinkMigration,
} = require("./evidence_complete_link_migration.js");

const observed = {
  schema_version: "strategy-correlation-complete-link-migration-public-summary-v1",
  status: "OBSERVED",
  source: "PROTOCOL_REGISTRATION_V4",
};
const view = presentCompleteLinkMigration(observed);
assert.equal(view.schemaVersion, "complete-link-migration-ledger-view-v1");
assert.equal(view.badge, "CONSUMER ONLY");
assert.deepEqual(
  view.segments.map((segment) => segment.id),
  ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
);
assert.equal(view.canTrade, false);
assert.equal(view.profitabilityClaimed, false);

const html = renderCompleteLinkMigration(observed);
assert.match(html, /Complete-link migration evidence ledger/);
assert.ok(html.indexOf("Source") < html.indexOf("Gap"));
assert.ok(html.indexOf("Gap") < html.indexOf("Maturity"));
assert.ok(html.indexOf("Maturity") < html.indexOf("Permission"));
assert.doesNotMatch(html, /READY|profit|trade/i);
assert.doesNotMatch(html, /registration_hash|strategy_id|variant_id|RAW_EXCESS/);

const unknown = presentCompleteLinkMigration({});
assert.equal(unknown.badge, "SOURCE UNKNOWN");
assert.equal(unknown.segments[0].state, "unknown");
assert.equal(unknown.canTrade, false);

const css = fs.readFileSync(path.join(__dirname, "evidence_complete_link_migration.css"), "utf8");
assert.match(css, /grid-template-columns: repeat\(4/);
assert.match(css, /prefers-reduced-motion/);
assert.match(css, /max-width: 430px/);
assert.doesNotMatch(css, /purple|#(?:8b5cf6|7c3aed|a855f7)/i);

console.log("complete-link migration presentation contract passed");
