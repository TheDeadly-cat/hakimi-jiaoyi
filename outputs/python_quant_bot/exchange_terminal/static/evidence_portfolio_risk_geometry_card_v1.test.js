"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const card = require("./evidence_portfolio_risk_geometry_card_v1.js");

function makeProjection() {
  return {
    schema_version:
      "strategy-correlation-cluster-portfolio-risk-public-projection-v1",
    static_fingerprint:
      "20260822-portfolio-risk-geometry-projection-lock-1",
    status: "OBSERVED",
    projection_hash: "a".repeat(64),
    pipeline: [
      { stage: "SOURCE", state: "VERIFIED" },
      { stage: "GAP", state: "WITHIN_DECLARED_RESEARCH_LIMITS" },
      { stage: "MATURITY", state: "UNMOUNTED_CANDIDATE" },
      { stage: "PERMISSION", state: "UNAUTHORIZED" },
    ],
    summary: {
      adapter_decision: "WITHIN_RESEARCH_RISK_BUDGET",
      adapter_status: "PASS",
      risk_increasing: true,
      legacy_gate_passed: true,
      effective_bet_gate_passed: true,
      cluster_limit_aligned: true,
      legacy_gross_exposure_pct: 41,
      legacy_net_exposure_pct: 41,
      legacy_proposal_centered_cluster_pct: 5,
      all_cluster_max_gross_exposure_pct: 36,
      symbol_ticket_count: 3,
      effective_independent_bet_count: 2,
      correlated_duplicate_ticket_count: 1,
      blocker_count: 0,
    },
    authority: {
      current_admission_allowed: false,
      current_pointer_written: false,
      descriptive_only: true,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      runtime_gate_activation_allowed: false,
      writer_allowed: false,
    },
  };
}

test("valid projection maps tickets to effective independent bets", () => {
  const view = card.buildPortfolioRiskGeometryViewModel(makeProjection());
  assert.equal(view.validContract, true);
  assert.equal(view.sourceState, "VERIFIED");
  assert.equal(view.gapState, "WITHIN_DECLARED_RESEARCH_LIMITS");
  assert.equal(view.permissionState, "UNAUTHORIZED");
  assert.deepEqual(view.metrics, {
    symbolTickets: 3,
    effectiveBets: 2,
    correlatedDuplicates: 1,
  });
});

test("verified block remains a research gap and never changes permission", () => {
  const projection = makeProjection();
  projection.pipeline[1].state = "RESEARCH_LIMIT_GAP_PRESENT";
  projection.summary.adapter_decision = "BLOCKED_RESEARCH_RISK_BUDGET";
  projection.summary.adapter_status = "BLOCK";
  projection.summary.effective_bet_gate_passed = false;
  projection.summary.blocker_count = 1;
  const view = card.buildPortfolioRiskGeometryViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.gapState, "RESEARCH_LIMIT_GAP_PRESENT");
  assert.equal(view.permissionState, "UNAUTHORIZED");
  assert.match(view.decisionLabel, /阻断/);
});

test("authority escalation fails closed to unknown", () => {
  const projection = makeProjection();
  projection.authority.paper_authorized = true;
  const view = card.buildPortfolioRiskGeometryViewModel(projection);
  assert.equal(view.validContract, false);
  assert.equal(view.sourceState, "UNKNOWN");
  assert.equal(view.gapState, "UNKNOWN");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("stage reordering and scalar aliases fail closed", () => {
  const reordered = makeProjection();
  reordered.pipeline.reverse();
  assert.equal(
    card.buildPortfolioRiskGeometryViewModel(reordered).validContract,
    false,
  );
  const aliased = makeProjection();
  aliased.summary.symbol_ticket_count = "3";
  assert.equal(
    card.buildPortfolioRiskGeometryViewModel(aliased).validContract,
    false,
  );
});

test("rendered card preserves neutral stage order and permission language", () => {
  const html = card.renderPortfolioRiskGeometryCard(makeProjection());
  const source = html.indexOf("<b>来源</b>");
  const gap = html.indexOf("<b>缺口</b>");
  const maturity = html.indexOf("<b>成熟度</b>");
  const permission = html.indexOf("<b>权限</b>");
  assert.ok(source < gap && gap < maturity && maturity < permission);
  assert.match(html, /PAPER \/ LIVE 未授权/);
  assert.doesNotMatch(html, /READY/);
  assert.doesNotMatch(html, /盈利|收益保证/);
});

test("custom copy is escaped", () => {
  const html = card.renderPortfolioRiskGeometryCard(makeProjection(), {
    title: '<img src=x onerror="boom">',
    eyebrow: "<script>boom</script>",
  });
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img/);
});

test("mount writes only to the supplied target", () => {
  const target = { innerHTML: "" };
  const returned = card.mountPortfolioRiskGeometryCard(
    target,
    makeProjection(),
  );
  assert.equal(returned, target);
  assert.match(target.innerHTML, /hkm-risk-geometry/);
  assert.throws(
    () => card.mountPortfolioRiskGeometryCard(null, makeProjection()),
    /mount target/,
  );
});

test("view-model construction does not mutate the projection", () => {
  const projection = makeProjection();
  const before = JSON.stringify(projection);
  card.buildPortfolioRiskGeometryViewModel(projection);
  assert.equal(JSON.stringify(projection), before);
});

test("browser-global build exports the same narrow API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_geometry_card_v1.js"),
    "utf8",
  );
  const sandbox = {};
  vm.runInNewContext(source, sandbox);
  const api = sandbox.HakimiPortfolioRiskGeometryCardV1;
  assert.equal(typeof api.buildPortfolioRiskGeometryViewModel, "function");
  assert.equal(typeof api.renderPortfolioRiskGeometryCard, "function");
  assert.equal(typeof api.mountPortfolioRiskGeometryCard, "function");
  assert.equal(api.PROJECTION_SCHEMA_VERSION, card.PROJECTION_SCHEMA_VERSION);
});

test("stylesheet carries responsive, motion, and forced-color contracts", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_geometry_card_v1.css"),
    "utf8",
  );
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(max-width: 460px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(css, /hkm-risk-arrive/);
  assert.match(css, /--hkm-risk-ocean/);
  assert.doesNotMatch(css, /#[a-f0-9]{6}.*purple/i);
});

test("public API and fingerprint stay version locked", () => {
  assert.equal(
    card.PROJECTION_SCHEMA_VERSION,
    "strategy-correlation-cluster-portfolio-risk-public-projection-v1",
  );
  assert.equal(
    card.STATIC_FINGERPRINT,
    "20260822-portfolio-risk-geometry-projection-lock-1",
  );
  assert.deepEqual(
    Object.keys(card).sort(),
    [
      "PROJECTION_SCHEMA_VERSION",
      "STATIC_FINGERPRINT",
      "buildPortfolioRiskGeometryViewModel",
      "mountPortfolioRiskGeometryCard",
      "renderPortfolioRiskGeometryCard",
    ].sort(),
  );
});
