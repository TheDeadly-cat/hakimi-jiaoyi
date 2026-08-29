"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const card = require("./evidence_portfolio_risk_temporal_lattice_card_v2.js");

function makeProjection() {
  return {
    schema_version:
      "strategy-correlation-cluster-portfolio-risk-public-projection-v2",
    static_fingerprint:
      "20260822-portfolio-risk-temporal-lattice-projection-lock-1",
    status: "OBSERVED",
    projection_hash: "a".repeat(64),
    pipeline: [
      { stage: "SOURCE", state: "VERIFIED" },
      {
        stage: "GAP",
        state: "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY",
      },
      { stage: "MATURITY", state: "UNMOUNTED_CANDIDATE" },
      { stage: "PERMISSION", state: "UNAUTHORIZED" },
    ],
    source: {
      adapter_supplied: true,
      adapter_exactly_verified: true,
      adapter_schema_version:
        "strategy-correlation-cluster-portfolio-risk-adapter-v2",
      adapter_hash: "b".repeat(64),
      verification_schema_version:
        "strategy-correlation-cluster-portfolio-risk-adapter-v2-verification-v1",
    },
    summary: {
      adapter_decision:
        "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY",
      adapter_status: "PASS",
      risk_increasing: true,
      base_adapter_passed: true,
      temporal_stability_required: true,
      temporal_stability_passed: true,
      legacy_gross_exposure_pct: 41,
      legacy_net_exposure_pct: 41,
      legacy_proposal_centered_cluster_pct: 23,
      all_cluster_max_gross_exposure_pct: 23,
      symbol_ticket_count: 3,
      effective_independent_bet_count: 2,
      correlated_duplicate_ticket_count: 1,
      effective_bet_blocker_count: 0,
      legacy_reject_reason_count: 0,
      temporal_stability_status: "PASS",
      window_result_count: 3,
      unstable_window_count: 0,
      insufficient_sample_window_count: 0,
      blocked_window_count: 0,
      within_cluster_pair_count: 1,
      pair_window_hypothesis_count: 3,
      first_blocking_tier: "NONE",
      stability_blocker_count: 0,
      adapter_blocker_count: 0,
      adapter_warning_count: 0,
    },
    facts: {
      source_documents_embedded: false,
      component_results_embedded: false,
      raw_correlations_embedded: false,
      return_series_embedded: false,
      window_rows_embedded: false,
      profitability_proof: false,
      runtime_assets_accessed: false,
      runtime_consumer_mounted: false,
      natural_forward_chain_changed: false,
    },
    authority: {
      current_admission_allowed: false,
      current_pointer_written: false,
      descriptive_only: true,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      risk_service_invocation_allowed: false,
      runtime_gate_activation_allowed: false,
      writer_allowed: false,
    },
  };
}

test("stable projection maps tickets, effective bets, and temporal counts", () => {
  const view =
    card.buildPortfolioRiskTemporalLatticeViewModel(makeProjection());
  assert.equal(view.validContract, true);
  assert.equal(view.sourceState, "VERIFIED");
  assert.equal(
    view.gapState,
    "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY",
  );
  assert.equal(view.permissionState, "UNAUTHORIZED");
  assert.deepEqual(view.metrics, {
    symbolTickets: 3,
    effectiveBets: 2,
    correlatedDuplicates: 1,
  });
  assert.equal(view.stability.status, "PASS");
  assert.equal(view.stability.windowResults, 3);
});

test("temporal block remains a research gap without authority", () => {
  const projection = makeProjection();
  projection.pipeline[1].state = "TEMPORAL_STABILITY_GAP_PRESENT";
  projection.summary.adapter_decision =
    "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY";
  projection.summary.adapter_status = "BLOCK";
  projection.summary.temporal_stability_passed = false;
  projection.summary.temporal_stability_status = "BLOCK";
  projection.summary.unstable_window_count = 1;
  projection.summary.blocked_window_count = 1;
  projection.summary.first_blocking_tier = "PAIR_WINDOW";
  projection.summary.stability_blocker_count = 1;
  projection.summary.adapter_blocker_count = 1;
  const view = card.buildPortfolioRiskTemporalLatticeViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.gapState, "TEMPORAL_STABILITY_GAP_PRESENT");
  assert.equal(view.stability.status, "BLOCK");
  assert.equal(view.permissionState, "UNAUTHORIZED");
  assert.match(view.decisionLabel, /稳定性缺口/);
});

test("base portfolio-risk block has a distinct gap", () => {
  const projection = makeProjection();
  projection.pipeline[1].state = "PORTFOLIO_RISK_LIMIT_GAP_PRESENT";
  projection.summary.adapter_decision = "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET";
  projection.summary.adapter_status = "BLOCK";
  projection.summary.base_adapter_passed = false;
  projection.summary.adapter_blocker_count = 1;
  const view = card.buildPortfolioRiskTemporalLatticeViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.gapState, "PORTFOLIO_RISK_LIMIT_GAP_PRESENT");
  assert.match(view.decisionLabel, /组合风险预算/);
});

test("risk reduction is distinct and still unauthorized", () => {
  const projection = makeProjection();
  projection.pipeline[1].state = "RISK_REDUCTION_PATH";
  projection.summary.adapter_decision =
    "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED";
  projection.summary.risk_increasing = false;
  projection.summary.temporal_stability_required = false;
  projection.summary.temporal_stability_passed = false;
  projection.summary.temporal_stability_status = "BLOCK";
  projection.summary.adapter_warning_count = 1;
  const view = card.buildPortfolioRiskTemporalLatticeViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.gapState, "RISK_REDUCTION_PATH");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("authority escalation fails closed to unknown", () => {
  const projection = makeProjection();
  projection.authority.paper_authorized = true;
  const view = card.buildPortfolioRiskTemporalLatticeViewModel(projection);
  assert.equal(view.validContract, false);
  assert.equal(view.sourceState, "UNKNOWN");
  assert.equal(view.gapState, "UNKNOWN");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("stage reordering and scalar aliases fail closed", () => {
  const reordered = makeProjection();
  reordered.pipeline.reverse();
  assert.equal(
    card.buildPortfolioRiskTemporalLatticeViewModel(reordered).validContract,
    false,
  );
  const aliased = makeProjection();
  aliased.summary.window_result_count = "3";
  assert.equal(
    card.buildPortfolioRiskTemporalLatticeViewModel(aliased).validContract,
    false,
  );
});

test("decision and gate inconsistency fails closed", () => {
  const projection = makeProjection();
  projection.summary.temporal_stability_passed = false;
  assert.equal(
    card.buildPortfolioRiskTemporalLatticeViewModel(projection).validContract,
    false,
  );
});

test("rendered card preserves neutral stage order and permission language", () => {
  const html = card.renderPortfolioRiskTemporalLatticeCard(makeProjection());
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
  const html = card.renderPortfolioRiskTemporalLatticeCard(makeProjection(), {
    title: '<img src=x onerror="boom">',
    eyebrow: "<script>boom</script>",
  });
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img/);
});

test("mount writes only to the supplied target", () => {
  const target = { innerHTML: "" };
  const returned = card.mountPortfolioRiskTemporalLatticeCard(
    target,
    makeProjection(),
  );
  assert.equal(returned, target);
  assert.match(target.innerHTML, /hkm-risk-lattice/);
  assert.throws(
    () =>
      card.mountPortfolioRiskTemporalLatticeCard(null, makeProjection()),
    /mount target/,
  );
});

test("view-model construction does not mutate the projection", () => {
  const projection = makeProjection();
  const before = JSON.stringify(projection);
  card.buildPortfolioRiskTemporalLatticeViewModel(projection);
  assert.equal(JSON.stringify(projection), before);
});

test("browser-global build exports the same narrow API", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_risk_temporal_lattice_card_v2.js",
    ),
    "utf8",
  );
  const sandbox = {};
  vm.runInNewContext(source, sandbox);
  const api = sandbox.HakimiPortfolioRiskTemporalLatticeCardV2;
  assert.equal(
    typeof api.buildPortfolioRiskTemporalLatticeViewModel,
    "function",
  );
  assert.equal(typeof api.renderPortfolioRiskTemporalLatticeCard, "function");
  assert.equal(typeof api.mountPortfolioRiskTemporalLatticeCard, "function");
  assert.equal(api.PROJECTION_SCHEMA_VERSION, card.PROJECTION_SCHEMA_VERSION);
});

test("stylesheet carries responsive, motion, and forced-color contracts", () => {
  const css = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_risk_temporal_lattice_card_v2.css",
    ),
    "utf8",
  );
  assert.match(css, /@media \(max-width: 820px\)/);
  assert.match(css, /@media \(max-width: 560px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(css, /hkm-lattice-arrive/);
  assert.match(css, /hkm-lattice-stage/);
  assert.match(css, /--hkm-lattice-tide/);
  assert.doesNotMatch(css, /purple/i);
});

test("public API and fingerprint stay version locked", () => {
  assert.equal(
    card.PROJECTION_SCHEMA_VERSION,
    "strategy-correlation-cluster-portfolio-risk-public-projection-v2",
  );
  assert.equal(
    card.STATIC_FINGERPRINT,
    "20260822-portfolio-risk-temporal-lattice-projection-lock-1",
  );
  assert.deepEqual(
    Object.keys(card).sort(),
    [
      "PROJECTION_SCHEMA_VERSION",
      "STATIC_FINGERPRINT",
      "buildPortfolioRiskTemporalLatticeViewModel",
      "mountPortfolioRiskTemporalLatticeCard",
      "renderPortfolioRiskTemporalLatticeCard",
    ].sort(),
  );
});
