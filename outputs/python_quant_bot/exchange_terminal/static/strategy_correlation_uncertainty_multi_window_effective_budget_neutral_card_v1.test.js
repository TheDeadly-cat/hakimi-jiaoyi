"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const presenter = require(
  "./strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js"
);
const subject = require(
  "./strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.js"
);

function authority() {
  return {
    research_evidence_only: true,
    current_admission_allowed: false,
    effective_budget_activation_allowed: false,
    http_registration_allowed: false,
    runtime_activation_allowed: false,
    writer_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function source(mode = "research") {
  const gateBlocked = mode === "veto" || mode === "reduction";
  const gate = {
    schema_version: presenter.UNCERTAINTY_GATE_SCHEMA_VERSION,
    static_fingerprint: presenter.UNCERTAINTY_GATE_STATIC_FINGERPRINT,
    gate_contract_hash: presenter.UNCERTAINTY_GATE_CONTRACT_HASH,
    gate_hash: "a".repeat(64),
    status: gateBlocked ? "BLOCK" : "PASS",
    window_count: 2,
    dependence_edge_count: gateBlocked ? 1 : 0,
    cross_cluster_dependence_edge_count: gateBlocked ? 1 : 0,
    derived_conservative_component_count: gateBlocked ? 2 : 3,
    preregistered_cluster_count: 3,
    authority: authority(),
  };
  const decision = mode === "reduction"
    ? "RISK_REDUCTION_PATH"
    : mode === "budget-block"
      ? "BLOCK"
      : "PASS_STRATIFIED_RESEARCH_BUDGET";
  const budgetStatus = mode === "budget-block" ? "BLOCK" : "PASS";
  const trusted = mode === "veto" ? null : {
    budget_v3_hash: "d".repeat(64),
    status: budgetStatus,
    decision,
    portfolio: {
      active_cluster_count: 2,
      symbol_ticket_count: 2,
      conservative_weighted_effective_strata_count: 2,
    },
  };
  const binding = {
    schema_version: presenter.BUDGET_BINDING_SCHEMA_VERSION,
    static_fingerprint: presenter.BUDGET_BINDING_STATIC_FINGERPRINT,
    binding_contract_hash: presenter.BUDGET_BINDING_CONTRACT_HASH,
    evaluation_hash: "b".repeat(64),
    uncertainty_gate_hash: gate.gate_hash,
    uncertainty_gate_status: gate.status,
    uncertainty_dependence_edge_count: gate.dependence_edge_count,
    uncertainty_cross_cluster_edge_count:
      gate.cross_cluster_dependence_edge_count,
    uncertainty_component_count: gate.derived_conservative_component_count,
    status: mode === "veto" ? "BLOCK" : "PASS",
    reason_code: mode === "veto"
      ? "CROSS_CLUSTER_DEPENDENCE_REQUIRES_REPREREGISTRATION"
      : "LOCAL_RESEARCH_EVIDENCE",
    effective_budget_status: trusted ? trusted.status : null,
    effective_budget_decision: trusted ? trusted.decision : null,
    trusted_effective_budget_document: trusted,
    facts: {
      risk_increasing: mode !== "reduction",
      budget_verification_attempted: mode !== "veto",
      budget_evaluation_exactly_verified: mode !== "veto",
    },
    authority: authority(),
  };
  return { uncertainty_cluster_gate: gate, uncertainty_budget_binding: binding };
}

function projection(mode = "research") {
  return presenter.buildUncertaintyEffectiveBudgetNeutralPresentationV1(
    source(mode)
  );
}

test("known projection builds a deeply frozen neutral card view", () => {
  const view = subject.buildNeutralBudgetCardViewModelV1(projection());
  assert.equal(subject.verifyNeutralPresentationV1(projection()), true);
  assert.equal(view.contract_state, "KNOWN_RESEARCH_ONLY");
  assert.equal(view.status_label, "RESEARCH CONTRACT");
  assert.equal(view.tone, "neutral");
  assert.equal(Object.isFrozen(view), true);
  assert.equal(Object.isFrozen(view.metrics), true);
  assert.deepEqual(
    view.stages.map((stage) => stage.axis),
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
});

test("semantic markup has labelled structure and text states", () => {
  const markup = subject.renderNeutralBudgetCardV1(projection());
  assert.match(markup, /^<article\b/);
  assert.match(markup, /aria-labelledby="[^"]+__title"/);
  assert.match(markup, /aria-describedby="[^"]+__summary"/);
  assert.match(markup, /<h2\b[^>]*>A research-budget contract is locally observed<\/h2>/);
  assert.match(markup, /<dl>/);
  assert.match(markup, /<ol>/);
  assert.match(markup, />SOURCE</);
  assert.match(markup, />UNAUTHORIZED</);
  assert.match(markup, /Research display only/);
});

test("cross-cluster veto has explicit non-color text", () => {
  const view = subject.buildNeutralBudgetCardViewModelV1(projection("veto"));
  const markup = subject.renderNeutralBudgetCardV1(projection("veto"));
  assert.equal(view.status_label, "LOCAL VETO");
  assert.match(markup, /Cross-cluster dependence stops budget review/);
  assert.match(markup, /new preregistration is required/i);
});

test("risk reduction and budget block remain distinct", () => {
  const reduction = subject.buildNeutralBudgetCardViewModelV1(
    projection("reduction")
  );
  const blocked = subject.buildNeutralBudgetCardViewModelV1(
    projection("budget-block")
  );
  assert.equal(reduction.status_label, "REDUCTION ONLY");
  assert.equal(blocked.status_label, "LOCAL BLOCK");
  assert.notEqual(reduction.title, blocked.title);
});

test("unknown sealed projection renders no metrics and keeps permission text", () => {
  const unknown = presenter.buildUncertaintyEffectiveBudgetNeutralPresentationV1({});
  const view = subject.buildNeutralBudgetCardViewModelV1(unknown);
  const markup = subject.renderNeutralBudgetCardV1(unknown);
  assert.equal(subject.verifyNeutralPresentationV1(unknown), true);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.deepEqual(view.metrics, []);
  assert.match(markup, /No bounded metrics are available/);
  assert.match(markup, />UNAUTHORIZED</);
});

test("resealed authority promotion degrades to the fixed unknown card", () => {
  const altered = JSON.parse(JSON.stringify(projection()));
  altered.authority.dom_mount_allowed = true;
  delete altered.presentation_hash;
  const resealed = strictCanonical.sealDocument(altered, "presentation_hash");
  const view = subject.buildNeutralBudgetCardViewModelV1(resealed);
  assert.equal(subject.verifyNeutralPresentationV1(resealed), false);
  assert.equal(view.contract_state, "UNKNOWN");
  assert.equal(view.status_label, "SOURCE UNKNOWN");
});

test("resealed metric injection is rejected and never reaches markup", () => {
  const altered = JSON.parse(JSON.stringify(projection()));
  altered.metrics.window_count = '<img src=x onerror="boom">';
  delete altered.presentation_hash;
  const resealed = strictCanonical.sealDocument(altered, "presentation_hash");
  const markup = subject.renderNeutralBudgetCardV1(resealed);
  assert.equal(subject.verifyNeutralPresentationV1(resealed), false);
  assert.doesNotMatch(markup, /<(?:img|script|svg|iframe)\b/i);
  assert.doesNotMatch(markup, /onerror/i);
});

test("known markup exposes bounded counts but no source payload", () => {
  const markup = subject.renderNeutralBudgetCardV1(projection());
  assert.match(markup, /Preregistered windows/);
  assert.match(markup, /Budget symbol tickets/);
  assert.doesNotMatch(markup, /trusted_effective_budget_document/);
  assert.doesNotMatch(markup, /window_audits/);
  assert.doesNotMatch(markup, /price_rows/);
});

test("markup is deterministic non-interactive and contains no inline style", () => {
  const first = subject.renderNeutralBudgetCardV1(projection());
  const second = subject.renderNeutralBudgetCardV1(projection());
  assert.equal(first, second);
  assert.doesNotMatch(first, /\sstyle=/i);
  assert.doesNotMatch(first, /<(?:button|a|input|select|textarea)\b/i);
  assert.doesNotMatch(first, /<[^>]+\son(?:click|error|load)\s*=/i);
});

test("card ids are deterministic and differ across sealed evidence states", () => {
  const normal = subject.buildNeutralBudgetCardViewModelV1(projection());
  const veto = subject.buildNeutralBudgetCardViewModelV1(projection("veto"));
  assert.match(normal.card_id, /^hakimi-uncertainty-budget-card-v1-[0-9a-f]{10}$/);
  assert.notEqual(normal.card_id, veto.card_id);
});

test("rendered card contains no promotional or directional wording", () => {
  const markup = subject.renderNeutralBudgetCardV1(projection());
  const forbidden = new RegExp(
    "\\b(?:" + ["REA", "DY|PRO", "FIT|RET", "URN|B", "UY|S", "ELL"].join("") + ")\\b",
    "i"
  );
  assert.equal(forbidden.test(markup), false);
});

test("presenter source pin matches the reviewed dependency", () => {
  const sourcePath = path.join(
    __dirname,
    "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js"
  );
  const hash = require("node:crypto")
    .createHash("sha256")
    .update(fs.readFileSync(sourcePath))
    .digest("hex");
  assert.equal(hash, subject.PRESENTATION_SOURCE_SHA256);
});

test("production renderer is unmounted and has no DOM or network operation", () => {
  const sourceText = fs.readFileSync(
    path.join(
      __dirname,
      "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_card_v1.js"
    ),
    "utf8"
  );
  assert.equal(sourceText.includes("document."), false);
  assert.equal(sourceText.includes("innerHTML"), false);
  assert.equal(sourceText.includes("fetch("), false);
  assert.equal(sourceText.includes("XMLHttpRequest"), false);
  assert.equal(sourceText.includes("WebSocket"), false);
  assert.equal(sourceText.includes("eval("), false);
});

test("public API and axis order remain frozen", () => {
  assert.equal(Object.isFrozen(subject), true);
  assert.equal(Object.isFrozen(subject.STAGE_ORDER), true);
  assert.deepEqual(
    subject.STAGE_ORDER,
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
});
