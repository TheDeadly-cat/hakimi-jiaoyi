"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const strictCanonical = require("./strict_canonical_json_v1.js");
const rail = require("./evidence_portfolio_correlation_admission_rail_v1.js");

const HASH = "a".repeat(64);
const CHECK_KEYS = [
  "input_snapshot_exact",
  "input_identity_exact",
  "report_strict_canonical",
  "base_admission_exact",
  "correlation_preregistration_exact",
  "correlation_matrix_exact",
  "selection_cells_strict_canonical",
  "complete_link_gate_exact",
  "complete_link_gate_pass",
  "strata_preregistration_exact",
  "strata_gate_exact",
  "strata_gate_pass",
  "evidence_has_no_execution_authority",
];

function checks(mode) {
  const result = Object.fromEntries(CHECK_KEYS.map((key) => [key, true]));
  if (mode === "complete-link-block") {
    result.complete_link_gate_pass = false;
    result.strata_preregistration_exact = null;
    result.strata_gate_exact = null;
    result.strata_gate_pass = null;
  }
  return result;
}

function evidenceHashes(mode) {
  return {
    source_report_hash: HASH,
    base_admission_hash: HASH,
    correlation_preregistration_hash: HASH,
    correlation_matrix_hash: HASH,
    selection_cells_hash: HASH,
    complete_link_gate_hash: HASH,
    strata_preregistration_hash: mode === "complete-link-block" ? "" : HASH,
    strata_gate_hash: mode === "complete-link-block" ? "" : HASH,
  };
}

function candidate(mode = "pass") {
  const blocked = mode === "complete-link-block";
  return strictCanonical.sealDocument({
    admission_state: blocked
      ? "CORRELATION_EVIDENCE_BLOCKED"
      : "CORRELATION_AND_PREREGISTERED_STRATA_VERIFIED_RESEARCH_ONLY",
    automatic_internal_backtest_activation_allowed: false,
    base_admission_status: "INTERNAL_BACKTEST_READY",
    blockers: blocked ? ["complete_link_gate_blocked"] : [],
    checks: checks(mode),
    complete_link_status: blocked ? "BLOCK" : "PASS",
    consumer_only: true,
    current_admission_allowed: false,
    current_writer_activation_allowed: false,
    evidence_hashes: evidenceHashes(mode),
    first_blocking_tier: blocked ? "COMPLETE_LINK" : null,
    independent_vote_policy:
      "AT_MOST_ONE_VOTE_PER_PREREGISTERED_CLUSTER_WITH_STRATA_GATE",
    lane: "RAW_EXCESS",
    manual_review_required: true,
    paper_admission_status: "BLOCKED",
    permissions: {
      paper_authorized: false,
      live_order_allowed: false,
    },
    raw_correlation_evidence_embedded: false,
    raw_report_embedded: false,
    research_only: true,
    schema_version: rail.ADMISSION_SCHEMA_VERSION,
    status: blocked ? "BLOCK" : "PASS",
    strata_gate_status: blocked ? "NOT_EVALUATED" : "PASS",
    strata_preregistration_status: blocked ? "NOT_EVALUATED" : "PASS",
    strategy_id: "strategy-1",
    variant_id: "variant-1",
  }, "correlation_admission_hash");
}

test("local pass renders bounded language without permission wording", () => {
  const source = candidate();
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV1(source);
  const markup = rail.renderPortfolioCorrelationAdmissionRailV1(source);

  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(source), true);
  assert.equal(view.contract_state, "KNOWN");
  assert.equal(view.status_label, "LOCAL CLEAR");
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(view.metrics[0].value, "PASS");
  assert.doesNotMatch(markup, /\bREADY\b/);
  assert.match(markup, /NO_CURRENT_PAPER_LIVE_OR_EXECUTION_AUTHORITY/);
});

test("complete-link block leaves both strata tiers not evaluated", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV1(
    candidate("complete-link-block")
  );
  const completeLink = view.tiers.find((tier) => tier.tier === "COMPLETE_LINK");
  const strataRegistration = view.tiers.find(
    (tier) => tier.tier === "STRATA_PREREGISTRATION"
  );
  const strataGate = view.tiers.find((tier) => tier.tier === "STRATA_GATE");

  assert.equal(view.status_label, "LOCAL BLOCK");
  assert.equal(completeLink.state, "BLOCK");
  assert.equal(strataRegistration.state, "NOT_EVALUATED");
  assert.equal(strataGate.state, "NOT_EVALUATED");
  assert.equal(view.stages[1].detail, "COMPLETE_LINK");
});

test("substituted hash fails closed to unknown", () => {
  const altered = structuredClone(candidate());
  altered.correlation_admission_hash = "0".repeat(64);
  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(altered), false);
  assert.equal(
    rail.buildPortfolioCorrelationAdmissionRailViewModelV1(altered).contract_state,
    "UNKNOWN"
  );
});

test("extra field is rejected even after resealing", () => {
  const altered = structuredClone(candidate());
  delete altered.correlation_admission_hash;
  altered.hidden_claim = true;
  const resealed = strictCanonical.sealDocument(
    altered,
    "correlation_admission_hash"
  );
  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(resealed), false);
});

test("resealed permission promotion cannot change the rail", () => {
  const altered = structuredClone(candidate());
  delete altered.correlation_admission_hash;
  altered.permissions.paper_authorized = true;
  const resealed = strictCanonical.sealDocument(
    altered,
    "correlation_admission_hash"
  );
  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(resealed), false);
  assert.equal(
    rail.buildPortfolioCorrelationAdmissionRailViewModelV1(resealed).contract_state,
    "UNKNOWN"
  );
});

test("downstream pass after complete-link block is impossible", () => {
  const altered = structuredClone(candidate("complete-link-block"));
  delete altered.correlation_admission_hash;
  altered.checks.strata_preregistration_exact = true;
  altered.checks.strata_gate_exact = true;
  altered.checks.strata_gate_pass = true;
  altered.strata_preregistration_status = "PASS";
  altered.strata_gate_status = "PASS";
  altered.evidence_hashes.strata_preregistration_hash = HASH;
  altered.evidence_hashes.strata_gate_hash = HASH;
  const resealed = strictCanonical.sealDocument(
    altered,
    "correlation_admission_hash"
  );
  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(resealed), false);
});

test("renderer escapes adversarial identity and blocker labels", () => {
  const altered = structuredClone(candidate("complete-link-block"));
  delete altered.correlation_admission_hash;
  altered.strategy_id = '<img src=x onerror="boom">';
  altered.blockers = ['<script>alert("x")</script>'];
  const resealed = strictCanonical.sealDocument(
    altered,
    "correlation_admission_hash"
  );
  const markup = rail.renderPortfolioCorrelationAdmissionRailV1(resealed);

  assert.equal(rail.verifyPortfolioCorrelationAdmissionV1(resealed), true);
  assert.doesNotMatch(markup, /<(?:img|script|svg|iframe)\b/i);
  assert.doesNotMatch(markup, /<[^>]+\son(?:error|load)\s*=/i);
  assert.match(markup, /&lt;img/);
  assert.match(markup, /&lt;script/);
});

test("unknown view hides metrics and preserves permission lock", () => {
  const view = rail.buildPortfolioCorrelationAdmissionRailViewModelV1({});
  assert.equal(view.contract_state, "UNKNOWN");
  assert.deepEqual(view.metrics, []);
  assert.equal(view.stages[3].state, "UNAUTHORIZED");
  assert.equal(Object.isFrozen(view), true);
});

test("public API and ordered axes stay frozen", () => {
  assert.equal(Object.isFrozen(rail), true);
  assert.equal(Object.isFrozen(rail.STAGE_ORDER), true);
  assert.equal(Object.isFrozen(rail.TIER_ORDER), true);
  assert.deepEqual(rail.STAGE_ORDER, ["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  assert.equal(rail.TIER_ORDER.length, 8);
});
