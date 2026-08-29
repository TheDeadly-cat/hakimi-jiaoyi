"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const card = require("./evidence_portfolio_risk_shadow_readiness_card_v1.js");

function makeProjection() {
  return {
    schema_version:
      "strategy-correlation-cluster-portfolio-risk-shadow-readiness-public-projection-v1",
    static_fingerprint:
      "20260822-shadow-readiness-evidence-stair-projection-lock-1",
    status: "OBSERVED",
    projection_hash: "a".repeat(64),
    pipeline: [
      { stage: "SOURCE", state: "LOCAL_EVIDENCE_VERIFIED" },
      {
        stage: "GAP",
        state: "EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN",
      },
      { stage: "MATURITY", state: "UNMOUNTED_CANDIDATE" },
      { stage: "PERMISSION", state: "UNAUTHORIZED" },
    ],
    source: {
      readiness_envelope_supplied: true,
      readiness_envelope_exactly_verified: true,
      readiness_schema_version:
        "strategy-correlation-cluster-portfolio-risk-shadow-input-readiness-envelope-v3",
      readiness_envelope_hash: "b".repeat(64),
      preregistration_supplied: true,
      preregistration_exactly_verified: true,
      preregistration_schema_version:
        "strategy-correlation-cluster-portfolio-risk-shadow-consumer-preregistration-v4",
      preregistration_hash: "c".repeat(64),
      contract_pin_aligned: true,
      readiness_evidence_bound_to_preregistration: false,
    },
    summary: {
      required_input_count: 14,
      verified_input_count: 14,
      signed_clock_source_count: 2,
      closed_local_blocker_count: 3,
      readiness_blocker_count: 18,
      preregistration_blocker_count: 19,
      preregistration_status: "BLOCKED",
      contract_pin_aligned: true,
      readiness_evidence_bound_to_preregistration: false,
      consumer_executed: false,
      external_time_authority_authenticated: false,
      current_time_established: false,
    },
    facts: {
      source_documents_embedded: false,
      verification_contexts_embedded: false,
      public_keys_embedded: false,
      signatures_embedded: false,
      raw_receipts_embedded: false,
      runtime_assets_accessed: false,
      runtime_consumer_mounted: false,
      risk_service_invoked: false,
      natural_forward_chain_changed: false,
      profitability_proof: false,
    },
    authority: {
      descriptive_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      formal_registry_activation_allowed: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      risk_service_invocation_allowed: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false,
    },
  };
}

test("valid projection keeps evidence verification separate from binding", () => {
  const view = card.buildShadowReadinessViewModel(makeProjection());
  assert.equal(view.validContract, true);
  assert.deepEqual(view.metrics, {
    requiredInputs: 14,
    verifiedInputs: 14,
    signedClockSources: 2,
    closedLocalBlockers: 3,
    readinessBlockers: 18,
    preregistrationBlockers: 19,
  });
  assert.equal(view.contractPinAligned, true);
  assert.equal(view.evidenceBound, false);
  assert.equal(view.consumerExecuted, false);
});

test("authority escalation fails closed to unknown", () => {
  const projection = makeProjection();
  projection.authority.paper_authorized = true;
  const view = card.buildShadowReadinessViewModel(projection);
  assert.equal(view.validContract, false);
  assert.equal(view.stages[0].state, "UNKNOWN");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("evidence binding inflation fails closed", () => {
  const projection = makeProjection();
  projection.summary.readiness_evidence_bound_to_preregistration = true;
  assert.equal(card.buildShadowReadinessViewModel(projection).validContract, false);
});

test("stage reorder and scalar aliases fail closed", () => {
  const reordered = makeProjection();
  reordered.pipeline.reverse();
  assert.equal(card.buildShadowReadinessViewModel(reordered).validContract, false);
  const aliased = makeProjection();
  aliased.summary.required_input_count = "14";
  assert.equal(card.buildShadowReadinessViewModel(aliased).validContract, false);
});

test("not-supplied projection remains neutral", () => {
  const projection = makeProjection();
  projection.status = "NOT_SUPPLIED";
  projection.pipeline[0].state = "NOT_SUPPLIED";
  projection.pipeline[1].state = "NOT_SUPPLIED";
  for (const key of Object.keys(projection.summary)) {
    if (typeof projection.summary[key] === "number" ||
        typeof projection.summary[key] === "string") {
      projection.summary[key] = null;
    } else {
      projection.summary[key] = false;
    }
  }
  projection.source.readiness_envelope_supplied = false;
  projection.source.readiness_envelope_exactly_verified = false;
  projection.source.readiness_schema_version = null;
  projection.source.readiness_envelope_hash = null;
  projection.source.preregistration_supplied = false;
  projection.source.preregistration_exactly_verified = false;
  projection.source.preregistration_schema_version = null;
  projection.source.preregistration_hash = null;
  projection.source.contract_pin_aligned = false;
  const view = card.buildShadowReadinessViewModel(projection);
  assert.equal(view.validContract, true);
  assert.equal(view.status, "NOT_SUPPLIED");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
});

test("render preserves neutral four-stage order and visible gaps", () => {
  const html = card.renderShadowReadinessCard(makeProjection());
  const source = html.indexOf("<b>来源</b>");
  const gap = html.indexOf("<b>缺口</b>");
  const maturity = html.indexOf("<b>成熟度</b>");
  const permission = html.indexOf("<b>权限</b>");
  assert.ok(source < gap && gap < maturity && maturity < permission);
  assert.match(html, /14 \/ 14/);
  assert.match(html, /readiness evidence 绑定/);
  assert.match(html, /未绑定/);
  assert.match(html, /外部时钟权威/);
  assert.match(html, /PAPER \/ LIVE 未授权/);
  assert.doesNotMatch(html, /READY|收益保证|盈利保证/);
});

test("render creates fourteen evidence steps", () => {
  const html = card.renderShadowReadinessCard(makeProjection());
  assert.equal((html.match(/data-state="verified"/g) || []).length, 14);
});

test("custom copy is escaped", () => {
  const html = card.renderShadowReadinessCard(makeProjection(), {
    title: '<img src=x onerror="boom">',
    eyebrow: "<script>boom</script>",
  });
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img/);
});

test("mount writes only to supplied target", () => {
  const target = { innerHTML: "" };
  assert.equal(card.mountShadowReadinessCard(target, makeProjection()), target);
  assert.match(target.innerHTML, /hkm-readiness-stair/);
  assert.throws(
    () => card.mountShadowReadinessCard(null, makeProjection()),
    /mount target/,
  );
});

test("view-model build does not mutate projection", () => {
  const projection = makeProjection();
  const before = JSON.stringify(projection);
  card.buildShadowReadinessViewModel(projection);
  assert.equal(JSON.stringify(projection), before);
});

test("browser global exports the same narrow API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_shadow_readiness_card_v1.js"),
    "utf8",
  );
  const sandbox = {};
  vm.runInNewContext(source, sandbox);
  const api = sandbox.HakimiPortfolioRiskShadowReadinessCardV1;
  assert.equal(typeof api.buildShadowReadinessViewModel, "function");
  assert.equal(typeof api.renderShadowReadinessCard, "function");
  assert.equal(typeof api.mountShadowReadinessCard, "function");
  assert.equal(api.PROJECTION_SCHEMA_VERSION, card.PROJECTION_SCHEMA_VERSION);
});

test("stylesheet carries stair signature and accessibility contracts", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_risk_shadow_readiness_card_v1.css"),
    "utf8",
  );
  assert.match(css, /hkm-readiness-stair__stack/);
  assert.match(css, /border-radius: 8px 34px 8px 34px/);
  assert.match(css, /@media \(max-width: 820px\)/);
  assert.match(css, /@media \(max-width: 500px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /forced-colors: active/);
  assert.match(css, /hkm-readiness-rise/);
  assert.doesNotMatch(css, /purple|#800080/i);
});

test("public API and fingerprint stay version locked", () => {
  assert.equal(
    card.PROJECTION_SCHEMA_VERSION,
    "strategy-correlation-cluster-portfolio-risk-shadow-readiness-public-projection-v1",
  );
  assert.equal(
    card.STATIC_FINGERPRINT,
    "20260822-shadow-readiness-evidence-stair-projection-lock-1",
  );
  assert.deepEqual(
    Object.keys(card).sort(),
    [
      "PROJECTION_SCHEMA_VERSION",
      "STATIC_FINGERPRINT",
      "buildShadowReadinessViewModel",
      "mountShadowReadinessCard",
      "renderShadowReadinessCard",
    ].sort(),
  );
});
