"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const card = require("./evidence_portfolio_risk_weighted_diversification_card_v4.js");
const strictJson = require("./strict_canonical_json_v1.js");

const FLOAT_PATHS = new Set([
  "weighted_diversification.dominant_cluster_share_of_active_gross_pct",
  "weighted_diversification.minimum_weighted_effective_cluster_count",
  "weighted_diversification.weighted_effective_cluster_count"
]);

function pythonCanonicalProjectionStringify(value) {
  function encode(current, pathParts) {
    if (current === null) return "null";
    if (typeof current === "boolean") return current ? "true" : "false";
    if (typeof current === "string") return JSON.stringify(current);
    if (typeof current === "number") {
      assert.equal(Number.isFinite(current), true);
      assert.equal(Object.is(current, -0), false);
      if (FLOAT_PATHS.has(pathParts.join("."))) {
        const rendered = String(current);
        assert.doesNotMatch(rendered, /[eE]/);
        return Number.isInteger(current) ? `${rendered}.0` : rendered;
      }
      assert.equal(Number.isSafeInteger(current), true);
      return String(current);
    }
    if (Array.isArray(current)) {
      return `[${current.map((item, index) => (
        encode(item, pathParts.concat(String(index)))
      )).join(",")}]`;
    }
    assert.equal(strictJson.isPlainRecord(current), true);
    return `{${Object.keys(current).sort().map((key) => (
      `${JSON.stringify(key)}:${encode(current[key], pathParts.concat(key))}`
    )).join(",")}}`;
  }
  return encode(value, []);
}

function resealProjection(document) {
  const payload = {};
  Object.keys(document).forEach((key) => {
    if (key !== "projection_hash") payload[key] = document[key];
  });
  document.projection_hash = strictJson.sha256Hex(
    pythonCanonicalProjectionStringify(payload)
  );
  return document;
}

function fixture({ status = "PASS", decision, weighted = 2, dominant = 50, labels = 2 } = {}) {
  const localDecision = decision
    || "WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY";
  const riskIncreasing = localDecision
    !== "RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED";
  const localStatus = status;
  const gaps = {
    WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY:
      ["NONE_OBSERVED", "NO_LOCAL_WEIGHTED_POLICY_GAP_OBSERVED"],
    RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED:
      ["NONE_OBSERVED", "VERIFIED_RISK_REDUCTION_WEIGHTED_EXEMPTION"],
    BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION:
      ["DECLARED", "WEIGHTED_CLUSTER_DIVERSIFICATION"],
    BLOCKED_ADAPTER_V3_COMPONENT: ["DECLARED", "ADAPTER_V3_COMPONENT"]
  };
  const gap = gaps[localDecision];
  const assessment = !riskIncreasing ? "NOT_APPLICABLE"
    : localDecision === "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION" ? "CONCENTRATED"
      : localStatus === "PASS" ? "SUFFICIENT" : "UPSTREAM_BLOCKED";
  const document = {
    schema_version: card.PROJECTION_SCHEMA_VERSION,
    static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
    status: "PASS",
    decision: "EXACT_WEIGHTED_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED",
    source: {
      adapter_v4_schema_version: "strategy-correlation-cluster-portfolio-risk-adapter-v4",
      adapter_v4_hash: "a".repeat(64),
      adapter_v4_exactly_verified: true,
      adapter_v4_implementation_sha256: "b".repeat(64),
      adapter_v3_hash: "c".repeat(64),
      weighted_budget_v2_hash: "d".repeat(64),
      v1_budget_hash: "e".repeat(64)
    },
    local_decision: {
      status: localStatus,
      decision: localDecision,
      risk_increasing: riskIncreasing,
      blockers: localStatus === "BLOCK" ? ["WEIGHTED_EFFECTIVE_CLUSTER_GATE_BLOCKED"] : [],
      warnings: []
    },
    weighted_diversification: {
      assessment,
      unweighted_effective_cluster_count: riskIncreasing ? labels : null,
      weighted_effective_cluster_count: riskIncreasing ? weighted : null,
      dominant_cluster_share_of_active_gross_pct: riskIncreasing ? dominant : null,
      minimum_weighted_effective_cluster_count: 1.5,
      gate_applied: riskIncreasing ? true : false
    },
    stages: [
      { key: "SOURCE", state: "VERIFIED", detail: "ADAPTER_V4_EXACT_REBUILD" },
      { key: "GAP", state: gap[0], detail: gap[1] },
      { key: "MATURITY", state: localStatus === "PASS" ? "LOCAL_POLICY_SATISFIED" : "LOCAL_POLICY_BLOCKED", detail: localDecision },
      { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY" }
    ],
    facts: {
      projection_only: true,
      source_document_embedded: false,
      component_documents_embedded: false,
      positions_embedded: false,
      cluster_exposure_rows_embedded: false,
      correlation_matrices_embedded: false,
      profitability_proven: false,
      runtime_consumer_bound: false,
      ui_mounted: false
    },
    authority: {
      research_only: true,
      presentation_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false
    },
    projection_hash: ""
  };
  return resealProjection(document);
}

test("exports and stage order are version locked", () => {
  assert.equal(card.CARD_SCHEMA_VERSION, "portfolio-risk-weighted-diversification-card-v4");
  assert.deepEqual(card.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(card.verifyPortfolioRiskProjectionSealV4(fixture()), true);
});

test("concentrated projection produces a known weight-aware model", () => {
  const model = card.buildPortfolioRiskWeightedDiversificationViewModelV4(fixture({
    status: "BLOCK",
    decision: "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION",
    weighted: 1.090722,
    dominant: 95.6522
  }));
  assert.equal(model.contract_state, "KNOWN");
  assert.equal(model.tone, "concentrated");
  assert.equal(model.metrics[0].value, "2");
  assert.equal(model.metrics[1].value, "1.09");
  assert.equal(model.metrics[2].value, "95.65%");
  assert.match(model.summary, /compress to 1\.09 effective clusters/);
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

test("balanced projection remains neutral and sufficient", () => {
  const model = card.buildPortfolioRiskWeightedDiversificationViewModelV4(fixture());
  assert.equal(model.contract_state, "KNOWN");
  assert.equal(model.tone, "sufficient");
  assert.match(model.summary, /local effective-cluster policy/);
});

test("risk reduction is explicit and weight gate is not applicable", () => {
  const model = card.buildPortfolioRiskWeightedDiversificationViewModelV4(fixture({
    decision: "RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED"
  }));
  assert.equal(model.tone, "not-applicable");
  assert.equal(model.metrics[1].value, "N/A");
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

for (const [name, mutate] of [
  ["schema drift", (value) => { value.schema_version = "legacy"; }],
  ["extra field", (value) => { value.extra = true; }],
  ["stage reorder", (value) => { value.stages.reverse(); }],
  ["authority promotion", (value) => { value.authority.paper_authorized = true; }],
  ["boolean alias", (value) => { value.local_decision.risk_increasing = 1; }],
  ["metric alias", (value) => { value.weighted_diversification.weighted_effective_cluster_count = "2"; }],
  ["assessment drift", (value) => { value.weighted_diversification.assessment = "SUFFICIENT"; }],
  ["permission promotion", (value) => { value.stages[3].state = "AUTHORIZED"; }]
]) {
  test(`${name} fails closed after adversarial reseal`, () => {
    const value = fixture({
      status: "BLOCK",
      decision: "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION",
      weighted: 1.090722,
      dominant: 95.6522
    });
    mutate(value);
    resealProjection(value);
    const model = card.buildPortfolioRiskWeightedDiversificationViewModelV4(value);
    assert.equal(model.contract_state, "UNKNOWN");
    assert.equal(model.stages[3].state, "UNAUTHORIZED");
  });
}

test("invalid projection hash shape fails closed", () => {
  const value = fixture();
  value.projection_hash = "short";
  assert.equal(card.verifyPortfolioRiskProjectionSealV4(value), false);
  assert.equal(
    card.buildPortfolioRiskWeightedDiversificationViewModelV4(value).contract_state,
    "UNKNOWN"
  );
});

test("valid-shape projection hash substitution fails closed", () => {
  const value = fixture({
    status: "BLOCK",
    decision: "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION",
    weighted: 1.090722,
    dominant: 95.6522
  });
  const original = value.projection_hash;
  value.projection_hash = "f".repeat(64);
  assert.notEqual(value.projection_hash, original);
  assert.equal(card.verifyPortfolioRiskProjectionSealV4(value), false);
  assert.equal(
    card.buildPortfolioRiskWeightedDiversificationViewModelV4(value).contract_state,
    "UNKNOWN"
  );
});

test("renderer escapes blocker text and exposes no mount API", () => {
  const value = fixture({ status: "BLOCK", decision: "BLOCKED_ADAPTER_V3_COMPONENT" });
  value.local_decision.blockers = ["<script>alert(1)</script>"];
  resealProjection(value);
  const html = card.renderPortfolioRiskWeightedDiversificationCardV4(value);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.equal(Object.hasOwn(card, "mount"), false);
});

test("rendered card remains unauthorized without promotion wording", () => {
  const html = card.renderPortfolioRiskWeightedDiversificationCardV4(fixture());
  assert.doesNotMatch(html, /\bREADY\b/i);
  assert.match(html, /UNAUTHORIZED/);
  assert.match(html, /UNMOUNTED SHADOW VIEW/);
});

test("malformed input renders unknown and unauthorized", () => {
  const html = card.renderPortfolioRiskWeightedDiversificationCardV4(null);
  assert.match(html, /data-contract-state="UNKNOWN"/);
  assert.match(html, /UNAUTHORIZED/);
});

test("css includes responsive reduced-motion and forced-color contracts", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_portfolio_risk_weighted_diversification_card_v4.css"), "utf8");
  assert.match(css, /@media \(max-width: 520px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(css, /\.prwd-v4__metrics/);
});
