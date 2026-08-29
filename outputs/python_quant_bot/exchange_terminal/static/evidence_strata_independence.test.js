"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const {
  presentStrataIndependence,
  renderStrataIndependence,
} = require("./evidence_strata_independence.js");

const payload = {
  schema_version:
    "strategy-correlation-preregistered-strata-public-summary-v1",
  static_fingerprint:
    "20260821-preregistered-strata-independence-ledger-1",
  source: {
    status: "OBSERVED",
    gate_evidence_status: "OBSERVED",
    cluster_count: 7,
    dimension_count: 2,
    stratum_count: 4,
  },
  gap: {
    status: "PARENT_STRATUM_CONCENTRATION_OBSERVED",
    passing_dimension_count: 1,
    blocked_dimension_count: 1,
  },
  maturity: {
    status: "CONSUMER_ONLY",
  },
  policy: {
    maximum_votes_per_stratum: 1,
    minimum_independent_strata: 2,
    required_strata_fraction: 0.6,
  },
  permission: {
    status: "RESEARCH_ONLY",
    paper_authorized: false,
    live_order_allowed: false,
  },
};

const view = presentStrataIndependence(payload);
assert.strictEqual(view.source.status, "OBSERVED");
assert.strictEqual(
  view.gap.status,
  "PARENT_STRATUM_CONCENTRATION_OBSERVED"
);
assert.strictEqual(view.metrics.clusters, 7);
assert.strictEqual(view.metrics.strata, 4);
assert.strictEqual(view.policy.requiredPercent, 60);
assert.strictEqual(view.permission.status, "RESEARCH_ONLY");

const attributes = {};
const root = {
  innerHTML: "",
  setAttribute(name, value) {
    attributes[name] = value;
  },
};
const renderedView = renderStrataIndependence(root, payload);
assert.deepStrictEqual(renderedView, view);
assert.strictEqual(attributes["data-hksi-mounted"], "true");
for (const label of ["SOURCE", "GAP", "MATURITY", "PERMISSION"]) {
  assert.ok(root.innerHTML.includes(label), label + " is missing");
}
assert.ok(root.innerHTML.includes("Independence is counted, not assumed."));
assert.ok(root.innerHTML.includes("Parent-stratum concentration observed"));
assert.ok(root.innerHTML.includes("7"));
assert.ok(root.innerHTML.includes("4"));
assert.ok(!/\bREADY\b|profit|return|trade/i.test(root.innerHTML));
assert.ok(!/AAA|BBB|cluster-aaa|registration_hash/.test(root.innerHTML));

const hostile = {
  schema_version:
    "strategy-correlation-preregistered-strata-public-summary-v1",
  static_fingerprint:
    "20260821-preregistered-strata-independence-ledger-1",
  source: {
    status: "<img src=x onerror=alert(1)>",
    cluster_count: "<script>alert(1)</script>",
  },
  gap: {
    status: "<svg onload=alert(1)>",
  },
  maturity: {
    status: "READY",
  },
  policy: {},
};
renderStrataIndependence(root, hostile);
assert.ok(!/script|onerror|onload|svg/i.test(root.innerHTML));
assert.ok(root.innerHTML.includes("Source unknown"));
assert.ok(root.innerHTML.includes("Evidence unavailable"));

const css = fs.readFileSync(
  path.join(__dirname, "evidence_strata_independence.css"),
  "utf8"
);
assert.ok(css.includes("@media (max-width: 760px)"));
assert.ok(css.includes("@media (prefers-reduced-motion: reduce)"));
assert.ok(css.includes("--hksi-oxide: #c65d36"));
assert.ok(css.includes("--hksi-tide: #287a78"));
assert.ok(!/purple|violet|magenta/i.test(css));

console.log("PASS evidence strata independence ledger");
