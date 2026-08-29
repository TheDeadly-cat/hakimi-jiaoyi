"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const {
  presentStrataProtocolMigration,
  renderStrataProtocolMigration,
} = require("./evidence_strata_protocol_migration.js");

const payload = {
  schema_version:
    "strategy-correlation-strata-protocol-migration-public-summary-v1",
  static_fingerprint: "20260821-strata-protocol-v7-migration-seal-1",
  source: {
    status: "OBSERVED",
    protocol_target: "PROTOCOL_V7",
    report_target: "REPORT18",
    report18_consumer_status: "AVAILABLE",
    registry_candidate_contract_status: "AVAILABLE",
  },
  gap: {
    status: "FORMAL_PERSISTENCE_AND_WRITER_PENDING",
    registry_evidence_status: "OBSERVED",
    registry_binding_status: "BOUND",
  },
  maturity: {
    status: "REGISTRY_BOUND_CANDIDATE",
    formal_registry: "PENDING",
    writer: "NOT_IMPLEMENTED",
    current: "NOT_ACTIVATED",
    writer_prerequisite_count: 9,
  },
  permission: {
    status: "RESEARCH_ONLY",
    paper_authorized: false,
    live_order_allowed: false,
  },
};

const view = presentStrataProtocolMigration(payload);
assert.strictEqual(view.source.status, "OBSERVED");
assert.strictEqual(
  view.gap.status,
  "FORMAL_PERSISTENCE_AND_WRITER_PENDING"
);
assert.strictEqual(view.maturity.status, "REGISTRY_BOUND_CANDIDATE");
assert.strictEqual(view.permission.status, "RESEARCH_ONLY");
assert.strictEqual(view.prerequisiteCount, 9);
assert.deepStrictEqual(
  view.seals.map((seal) => seal.status),
  ["SEALED", "SEALED", "SEALED", "OPEN", "OPEN"]
);

const attributes = {};
const root = {
  innerHTML: "",
  setAttribute(name, value) {
    attributes[name] = value;
  },
};
renderStrataProtocolMigration(root, payload);
assert.strictEqual(attributes["data-hksp-mounted"], "true");
for (const label of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
  assert.ok(root.innerHTML.includes(label), label + " is missing");
}
for (const seal of [
  "Protocol-v7",
  "Report18 consumer",
  "Registry candidate",
  "Formal persistence",
  "Writer",
]) {
  assert.ok(root.innerHTML.includes(seal), seal + " is missing");
}
assert.ok(root.innerHTML.includes("The protocol is sealed. Authority is not."));
assert.ok(!/\bREADY\b|profit|return|trade/i.test(root.innerHTML));
assert.ok(!/AAA|cluster-|registry_asset_hash|classification_source/i.test(root.innerHTML));

const hostile = {
  schema_version:
    "strategy-correlation-strata-protocol-migration-public-summary-v1",
  static_fingerprint: "20260821-strata-protocol-v7-migration-seal-1",
  source: {
    status: "<img src=x onerror=alert(1)>",
    protocol_target: "<script>alert(1)</script>",
  },
  gap: {
    status: "<svg onload=alert(1)>",
  },
  maturity: {
    status: "READY",
    writer_prerequisite_count: "<iframe>",
  },
};
renderStrataProtocolMigration(root, hostile);
assert.ok(!/script|onerror|onload|svg|iframe/i.test(root.innerHTML));
assert.ok(root.innerHTML.includes("Protocol source unknown"));
assert.ok(root.innerHTML.includes("Migration evidence unavailable"));

const css = fs.readFileSync(
  path.join(__dirname, "evidence_strata_protocol_migration.css"),
  "utf8"
);
assert.ok(css.includes("@media (max-width: 760px)"));
assert.ok(css.includes("@media (prefers-reduced-motion: reduce)"));
assert.ok(css.includes("--hksp-oxide: #c65d36"));
assert.ok(css.includes("--hksp-tide: #287a78"));
assert.ok(!/purple|violet|magenta/i.test(css));

console.log("PASS evidence strata protocol migration seal rack");
