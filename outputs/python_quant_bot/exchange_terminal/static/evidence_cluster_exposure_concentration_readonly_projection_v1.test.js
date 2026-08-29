"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const presenter = require("./evidence_cluster_exposure_concentration_readonly_projection_v1.js");
const STATIC_BLOCKERS = ["FRESH_PROJECTED_EVIDENCE_INCOMPLETE", "READONLY_PROJECTION_NOT_REGISTERED", "PAPER_LIVE_UNAUTHORIZED"];

function projection(status = presenter.STATUS_WITHIN_LIMIT) {
  const policyBlockers = status === presenter.STATUS_CONCENTRATION_BLOCK
    ? ["LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED", "CLUSTER_HHI_LIMIT_EXCEEDED"]
    : status === presenter.STATUS_UPSTREAM_BLOCK
      ? ["UPSTREAM_EXPOSURE_LIMIT_BREACH"]
      : status === presenter.STATUS_UNKNOWN ? ["MAX_CLUSTER_HHI_INVALID"] : [];
  const summary = status === presenter.STATUS_UNKNOWN || status === presenter.STATUS_UPSTREAM_BLOCK
    ? { proposal_count: null, independent_cluster_count: null, total_gross_bps: null, largest_cluster_share_bps_ceiling: null, hhi_ppm_ceiling: null, effective_cluster_count_milli_floor: null }
    : status === presenter.STATUS_CONCENTRATION_BLOCK
      ? { proposal_count: 2, independent_cluster_count: 2, total_gross_bps: 4000, largest_cluster_share_bps_ceiling: 7500, hhi_ppm_ceiling: 625000, effective_cluster_count_milli_floor: 1600 }
      : { proposal_count: 2, independent_cluster_count: 2, total_gross_bps: 4000, largest_cluster_share_bps_ceiling: 5000, hhi_ppm_ceiling: 500000, effective_cluster_count_milli_floor: 2000 };
  const paths = {
    [presenter.STATUS_UNKNOWN]: ["SOURCE_OR_CONCENTRATION_POLICY_UNKNOWN", "UNVERIFIED"],
    [presenter.STATUS_UPSTREAM_BLOCK]: ["UPSTREAM_ABSOLUTE_EXPOSURE_LIMIT_BREACH", "STRUCTURAL_UPSTREAM_BLOCK"],
    [presenter.STATUS_CONCENTRATION_BLOCK]: ["PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT_BREACH", "STRUCTURAL_CONCENTRATION_POLICY_BREACH"],
    [presenter.STATUS_WITHIN_LIMIT]: ["FRESH_PROJECTED_EVIDENCE_INCOMPLETE", "PREREGISTERED_CONCENTRATION_STRUCTURE_ONLY"],
  };
  return {
    schema_version: presenter.PROJECTION_SCHEMA_VERSION,
    static_fingerprint: "20260824-cluster-exposure-concentration-readonly-projection-v1-verified-batch-hash-only-unmounted-permission-lock-1",
    consumer_status: "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CONCENTRATION_CANDIDATE",
    registered: false,
    status,
    source: {
      concentration_gate_contract_version: "strategy-correlation-history-covered-budget-universe-cluster-exposure-concentration-gate-v1",
      concentration_result_hash: "a".repeat(64),
      concentration_policy_fingerprint_sha256: status === presenter.STATUS_UNKNOWN ? null : "b".repeat(64),
      source_exposure_result_hash: "c".repeat(64),
    },
    decision_path: { source: "ADR0374_EXACT_VERIFIED_BATCH_CONCENTRATION", gap: paths[status][0], maturity: paths[status][1], permission: "NOT_AUTHORIZED" },
    summary,
    policy_blocker_codes: policyBlockers,
    blockers: [...policyBlockers, ...STATIC_BLOCKERS],
    facts: { concentration_metrics_structural_only: true, diversification_quality_claim_allowed: false, fresh_projected_evidence_completed: false, profitability_claim_allowed: false, raw_cluster_ids_redacted: true, raw_symbols_redacted: true, synthetic_only: true, within_limit_is_not_admission: true },
    authority: { consumer_registration_allowed: false, current_admission_allowed: false, current_pointer_written: false, diversification_claim_allowed: false, http_registration_allowed: false, live_order_allowed: false, paper_authorized: false, profitability_claim_allowed: false, readonly_projection_activation_allowed: false, runtime_activation_allowed: false, writer_allowed: false, research_evidence_only: true },
    readonly_projection_hash: "d".repeat(64),
  };
}

function envelope(status) {
  const value = projection(status);
  return { schema_version: presenter.ENVELOPE_SCHEMA_VERSION, verification_status: presenter.VERIFICATION_STATUS, expected_readonly_projection_hash: value.readonly_projection_hash, projection: value };
}

test("governance order and API are frozen", () => {
  assert.deepEqual(presenter.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(Object.isFrozen(presenter), true);
});

test("balanced concentration is an observation, not diversification proof", () => {
  const model = presenter.deriveClusterConcentrationViewModelV1(envelope());
  const markup = presenter.renderClusterConcentrationReadonlyProjectionV1(envelope());
  assert.equal(model.verificationAccepted, true);
  assert.equal(model.statusLabel, "结构分布观察");
  assert.deepEqual(model.metrics.map((item) => item.value), ["2", "2", "40.00%", "50.00%", "0.500000", "2.000"]);
  assert.match(markup, /不构成分散化、准入、仓位、信号、订单或收益结论/);
  assert.doesNotMatch(markup, /\bREADY\b/i);
});

test("75/25 concentration remains visibly blocked", () => {
  const input = envelope(presenter.STATUS_CONCENTRATION_BLOCK);
  const model = presenter.deriveClusterConcentrationViewModelV1(input);
  assert.equal(model.statusLabel, "集中度门禁阻断");
  assert.deepEqual(model.metrics.map((item) => item.value), ["2", "2", "40.00%", "75.00%", "0.625000", "1.600"]);
  assert.equal(model.policyBlockers.length, 2);
});

test("upstream block and unknown both hide every metric", () => {
  for (const status of [presenter.STATUS_UPSTREAM_BLOCK, presenter.STATUS_UNKNOWN]) {
    const model = presenter.deriveClusterConcentrationViewModelV1(envelope(status));
    assert.equal(model.verificationAccepted, true);
    assert.deepEqual(model.metrics.map((item) => item.value), ["--", "--", "--", "--", "--", "--"]);
  }
});

test("hash mismatch fails closed without reflecting attacker input", () => {
  const input = envelope();
  input.expected_readonly_projection_hash = "e".repeat(64);
  input.projection.decision_path.gap = "<img src=x onerror=alert(1)>";
  const markup = presenter.renderClusterConcentrationReadonlyProjectionV1(input);
  assert.doesNotMatch(markup, /onerror|<img/i);
  assert.match(markup, /展示输入未完成精确验证交接/);
});

test("authority promotion and blocker injection fail closed", () => {
  const promoted = envelope();
  promoted.projection.authority.diversification_claim_allowed = true;
  const injected = envelope(presenter.STATUS_CONCENTRATION_BLOCK);
  injected.projection.policy_blocker_codes = ["<SCRIPT>"];
  injected.projection.blockers = ["<SCRIPT>", ...STATIC_BLOCKERS];
  assert.equal(presenter.deriveClusterConcentrationViewModelV1(promoted).verificationAccepted, false);
  assert.equal(presenter.deriveClusterConcentrationViewModelV1(injected).verificationAccepted, false);
});

test("rendered stages retain SOURCE GAP MATURITY PERMISSION order", () => {
  const markup = presenter.renderClusterConcentrationReadonlyProjectionV1(envelope());
  const positions = presenter.STAGE_ORDER.map((stage) => markup.indexOf(`>${stage}<`));
  assert.equal(positions.every((position) => position >= 0), true);
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
});

test("view model is deeply immutable", () => {
  const model = presenter.deriveClusterConcentrationViewModelV1(envelope());
  assert.equal(Object.isFrozen(model), true);
  assert.equal(Object.isFrozen(model.metrics[0]), true);
  assert.throws(() => { model.metrics[0].value = "forged"; }, TypeError);
});

test("production presenter has no DOM network storage or runtime APIs", () => {
  const source = fs.readFileSync(path.join(__dirname, "evidence_cluster_exposure_concentration_readonly_projection_v1.js"), "utf8");
  for (const forbidden of ["document.", "window.", "fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage", "indexedDB", "registerRoute", "currentPointer"]) assert.equal(source.includes(forbidden), false, forbidden);
});

test("isolated CSS encodes dominance HHI and accessibility guards", () => {
  const css = fs.readFileSync(path.join(__dirname, "evidence_cluster_exposure_concentration_readonly_projection_v1.css"), "utf8");
  assert.match(css, /--ccp-ink:\s*#13282d/);
  assert.match(css, /dominance-track/);
  assert.match(css, /hhi-dial/);
  assert.match(css, /conic-gradient/);
  assert.match(css, /summary:focus-visible/);
  assert.match(css, /max-width:\s*760px/);
  assert.match(css, /max-width:\s*460px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test("presenter remains deliberately absent from current index", () => {
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.equal(index.includes("evidence_cluster_exposure_concentration_readonly_projection_v1.js"), false);
  assert.equal(index.includes("evidence_cluster_exposure_concentration_readonly_projection_v1.css"), false);
});
