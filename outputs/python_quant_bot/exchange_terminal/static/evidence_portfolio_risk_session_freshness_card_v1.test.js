"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const card = require("./evidence_portfolio_risk_session_freshness_card_v1.js");

function makeProjection() {
  return {
    schema_version:
      "strategy-correlation-cluster-portfolio-risk-session-freshness-public-projection-v1",
    static_fingerprint: "20260822-session-lag-ledger-projection-lock-1",
    status: "OBSERVED",
    projection_hash: "a".repeat(64),
    pipeline: [
      { stage: "SOURCE", state: "VERIFIED" },
      {
        stage: "GAP",
        state:
          "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
      },
      { stage: "MATURITY", state: "UNMOUNTED_CANDIDATE" },
      { stage: "PERMISSION", state: "UNAUTHORIZED" },
    ],
    source: {
      evaluation_supplied: true,
      evaluation_exactly_verified: true,
      complete_source_hash_lineage: true,
      evaluation_schema_version:
        "strategy-correlation-cluster-portfolio-risk-session-freshness-evaluation-v1",
      evaluation_hash: "b".repeat(64),
    },
    summary: {
      evaluation_decision:
        "SESSION_LAG_WITHIN_PREREGISTERED_POLICY_EXTERNAL_TIME_AUTHORITY_UNPROVEN",
      evaluation_status: "PASS",
      cutoff_session_label: "2026-12-19",
      reference_time_utc: "2026-12-20T00:00:00Z",
      max_completed_session_lag: 0,
      preregistered_max_completed_session_lag: 1,
      calendar_count: 1,
      clock_quality: "EXTERNAL_QUORUM",
      external_clock_source_count: 2,
      local_policy_condition_satisfied: true,
      external_clock_authority_authenticated: false,
      freshness_externally_proven: false,
      blocker_count: 0,
    },
    facts: {
      source_documents_embedded: false,
      clock_sources_embedded: false,
      calendar_ids_embedded: false,
      per_calendar_lag_embedded: false,
      raw_correlations_embedded: false,
      profitability_proof: false,
      runtime_assets_accessed: false,
      runtime_consumer_mounted: false,
      natural_forward_chain_changed: false,
      external_time_authority_authenticated: false,
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
      shadow_consumer_activation_allowed: false,
      writer_allowed: false,
    },
  };
}

test("valid projection keeps local condition separate from authority", () => {
  const view = card.buildSessionFreshnessViewModel(makeProjection());
  assert.equal(view.validContract, true);
  assert.equal(view.sourceState, "VERIFIED");
  assert.equal(
    view.gapState,
    "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
  );
  assert.deepEqual(view.metrics, {
    completedSessionLag: 0,
    registeredLimit: 1,
    calendarCount: 1,
    clockSourceCount: 2,
  });
  assert.equal(view.externalAuthorityLabel, "未认证");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("stale evaluation remains a visible policy gap", () => {
  const projection = makeProjection();
  projection.pipeline[1].state = "SESSION_LAG_POLICY_GAP_PRESENT";
  projection.summary.evaluation_status = "BLOCK";
  projection.summary.max_completed_session_lag = 2;
  projection.summary.local_policy_condition_satisfied = false;
  projection.summary.blocker_count = 1;
  const view = card.buildSessionFreshnessViewModel(projection);
  assert.equal(view.validContract, true);
  assert.match(view.decisionLabel, /超过预登记阈值/);
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("authority escalation fails closed to unknown", () => {
  const projection = makeProjection();
  projection.authority.paper_authorized = true;
  const view = card.buildSessionFreshnessViewModel(projection);
  assert.equal(view.validContract, false);
  assert.equal(view.sourceState, "UNKNOWN");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("stage reorder and scalar aliases fail closed", () => {
  const reordered = makeProjection();
  reordered.pipeline.reverse();
  assert.equal(card.buildSessionFreshnessViewModel(reordered).validContract, false);
  const aliased = makeProjection();
  aliased.summary.max_completed_session_lag = "0";
  assert.equal(card.buildSessionFreshnessViewModel(aliased).validContract, false);
});

test("valid not-supplied projection stays neutral", () => {
  const projection = makeProjection();
  projection.status = "NOT_SUPPLIED";
  projection.pipeline[0].state = "NOT_SUPPLIED";
  projection.pipeline[1].state = "NOT_SUPPLIED";
  for (const key of Object.keys(projection.summary)) {
    projection.summary[key] = null;
  }
  projection.summary.evaluation_decision = "NOT_SUPPLIED";
  const view = card.buildSessionFreshnessViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.sourceState, "NOT_SUPPLIED");
  assert.equal(view.permissionState, "UNAUTHORIZED");
});

test("render uses session ruler and neutral permission language", () => {
  const html = card.renderSessionFreshnessCard(makeProjection());
  const source = html.indexOf("<b>来源</b>");
  const gap = html.indexOf("<b>缺口</b>");
  const maturity = html.indexOf("<b>成熟度</b>");
  const permission = html.indexOf("<b>权限</b>");
  assert.ok(source < gap && gap < maturity && maturity < permission);
  assert.match(html, /完成会话滞后/);
  assert.match(html, /外部时钟权威/);
  assert.match(html, /PAPER \/ LIVE 未授权/);
  assert.doesNotMatch(html, /READY|收益保证|盈利保证/);
});

test("custom copy is escaped", () => {
  const html = card.renderSessionFreshnessCard(makeProjection(), {
    title: '<img src=x onerror="boom">',
    eyebrow: "<script>boom</script>",
  });
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img/);
});

test("mount writes only to supplied target", () => {
  const target = { innerHTML: "" };
  assert.equal(card.mountSessionFreshnessCard(target, makeProjection()), target);
  assert.match(target.innerHTML, /hkm-session-lag/);
  assert.throws(
    () => card.mountSessionFreshnessCard(null, makeProjection()),
    /mount target/,
  );
});

test("view-model build does not mutate projection", () => {
  const projection = makeProjection();
  const before = JSON.stringify(projection);
  card.buildSessionFreshnessViewModel(projection);
  assert.equal(JSON.stringify(projection), before);
});

test("browser global exports the same narrow API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_session_freshness_card_v1.js"),
    "utf8",
  );
  const sandbox = {};
  vm.runInNewContext(source, sandbox);
  const api = sandbox.HakimiPortfolioRiskSessionFreshnessCardV1;
  assert.equal(typeof api.buildSessionFreshnessViewModel, "function");
  assert.equal(typeof api.renderSessionFreshnessCard, "function");
  assert.equal(typeof api.mountSessionFreshnessCard, "function");
  assert.equal(api.PROJECTION_SCHEMA_VERSION, card.PROJECTION_SCHEMA_VERSION);
});

test("stylesheet carries signature ruler and accessibility contracts", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_session_freshness_card_v1.css"),
    "utf8",
  );
  assert.match(css, /hkm-session-lag__ticks/);
  assert.match(css, /clip-path: polygon/);
  assert.match(css, /@media \(max-width: 780px\)/);
  assert.match(css, /@media \(max-width: 480px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(css, /hkm-session-unfurl/);
  assert.doesNotMatch(css, /purple|#800080/i);
});

test("public API and fingerprint stay version locked", () => {
  assert.equal(
    card.PROJECTION_SCHEMA_VERSION,
    "strategy-correlation-cluster-portfolio-risk-session-freshness-public-projection-v1",
  );
  assert.equal(
    card.STATIC_FINGERPRINT,
    "20260822-session-lag-ledger-projection-lock-1",
  );
  assert.deepEqual(
    Object.keys(card).sort(),
    [
      "PROJECTION_SCHEMA_VERSION",
      "STATIC_FINGERPRINT",
      "buildSessionFreshnessViewModel",
      "mountSessionFreshnessCard",
      "renderSessionFreshnessCard",
    ].sort(),
  );
});
