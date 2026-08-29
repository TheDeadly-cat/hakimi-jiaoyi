"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { spawnSync } = require("node:child_process");

const subject = require(
  "./evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js"
);

function fixtures() {
  const script = [
    "import json",
    "from tests.test_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 import PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests",
    "from exchange_terminal.services import portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 as delivery",
    "case = PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests()",
    "case.setUp()",
    "base = case.fixture",
    "evidence = base.admission_case._replace_universe(base.evidence, ['A', 'B'], selection_basis='BRIDGE_TOPOLOGY_BLOCK')",
    "blocked_admission = base.admission_case._build(evidence)",
    "blocked_binding = base._build_binding(admission=blocked_admission, evidence=evidence)",
    "topology = delivery.build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(blocked_binding, blocked_admission, base.budget, evidence['report_document'], evidence['correlation_preregistration_document'], evidence['correlation_matrix_document'], evidence['selection_cells_document'], base.budget_case.audit, evidence['complete_link_gate_document'], evidence['strata_preregistration_document'], evidence['strata_gate_document'], strategy_id=evidence['strategy_id'], variant_id=evidence['variant_id'], lane=evidence['lane'], **base.inputs)",
    "print(json.dumps({'pass': case.envelope, 'exposure': case.blocked_envelope, 'topology': topology, 'unknown': case.unknown_envelope}, separators=(',', ':')))",
  ].join("\n");
  const result = spawnSync("python", ["-c", script], {
    cwd: path.resolve(__dirname, "../.."),
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

const documents = fixtures();

test("exact pass builds a bounded two-pier bridge view", () => {
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      documents.pass
    );
  assert.equal(model.contract_state, "KNOWN");
  assert.equal(model.tone, "bounded");
  assert.equal(model.status_label, "LOCAL ALIGNMENT");
  assert.equal(model.piers.admission.state, "PASS");
  assert.equal(model.piers.budget.state, "PASS");
  assert.equal(model.piers.binding.state, "PASS");
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

test("effective budget block remains the visible exposure pier stop", () => {
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      documents.exposure
    );
  assert.equal(model.tone, "exposure");
  assert.equal(model.status_label, "EXPOSURE BLOCK");
  assert.equal(model.piers.admission.state, "PASS");
  assert.equal(model.piers.budget.state, "BLOCK");
  assert.equal(model.piers.binding.state, "PASS");
  assert.equal(model.stages[1].detail, "EFFECTIVE_BUDGET_V3_DECISION");
});

test("admission block remains the visible topology pier stop", () => {
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      documents.topology
    );
  assert.equal(model.tone, "topology");
  assert.equal(model.status_label, "TOPOLOGY BLOCK");
  assert.equal(model.piers.admission.state, "BLOCK");
  assert.equal(model.piers.budget.state, "PASS");
  assert.equal(model.stages[1].detail, "ADMISSION_V2_DECISION");
});

test("unknown delivery exposes no metrics and no inferred conclusion", () => {
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      documents.unknown
    );
  assert.equal(model.contract_state, "UNKNOWN");
  assert.equal(model.status_label, "SOURCE UNKNOWN");
  assert.deepEqual(model.metrics, []);
  assert.equal(model.piers.binding.state, "NOT_EVALUATED");
  assert.equal(model.stages[3].state, "UNAUTHORIZED");
});

test("renderer carries the bridge signature and neutral governance order", () => {
  const markup =
    subject.renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1(
      documents.pass
    );
  assert.equal(markup.includes("ADMISSION TOPOLOGY"), true);
  assert.equal(markup.includes("SHARED SOURCE BINDING"), true);
  assert.equal(markup.includes("EFFECTIVE BUDGET"), true);
  const stagesStart = markup.indexOf("__stages");
  const stagesEnd = markup.indexOf("</ol>", stagesStart);
  const stages = markup.slice(stagesStart, stagesEnd);
  let cursor = -1;
  for (const axis of subject.STAGE_ORDER) {
    const next = stages.indexOf(axis, cursor + 1);
    assert.ok(next > cursor);
    cursor = next;
  }
});

test("markup contains hashes only and no raw identities or permission claim", () => {
  const markup =
    subject.renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1(
      documents.pass
    );
  for (const forbidden of [
    "synthetic-strategy",
    "synthetic-variant",
    ">A<",
    ">B<",
    ">C<",
    "READY",
    "paper_authorized",
    "live_order_allowed",
  ]) {
    assert.equal(markup.includes(forbidden), false);
  }
});

test("invalid envelope fails closed before markup construction", () => {
  const forged = structuredClone(documents.pass);
  forged.delivery_state = "<svg/onload=alert(1)>";
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      forged
    );
  const markup =
    subject.renderPortfolioCorrelationAdmissionEffectiveBudgetBridgeV1(
      forged
    );
  assert.equal(model.contract_state, "UNKNOWN");
  assert.equal(markup.includes("<svg"), false);
  assert.equal(markup.includes("onload"), false);
});

test("public API, constants, and returned models remain frozen", () => {
  const model =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetBridgeViewModelV1(
      documents.pass
    );
  assert.equal(Object.isFrozen(subject), true);
  assert.equal(Object.isFrozen(subject.STAGE_ORDER), true);
  assert.equal(Object.isFrozen(subject.TIER_ORDER), true);
  assert.equal(Object.isFrozen(model), true);
  assert.equal(Object.isFrozen(model.piers), true);
  assert.equal(Object.isFrozen(model.tiers), true);
});

test("isolated CSS encodes the structural bridge, responsive layout, and motion guard", () => {
  const css = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_correlation_admission_effective_budget_bridge_v1.css"
    ),
    "utf8"
  );
  assert.equal(css.includes(".hakimi-admission-budget-bridge-v1__structure"), true);
  assert.equal(css.includes(".hakimi-admission-budget-bridge-v1__pier"), true);
  assert.equal(css.includes(".hakimi-admission-budget-bridge-v1__truss"), true);
  assert.equal(css.includes(".hakimi-admission-budget-bridge-v1__lock"), true);
  assert.equal(css.includes("@media (max-width: 860px)"), true);
  assert.equal(css.includes("@media (max-width: 560px)"), true);
  assert.equal(css.includes("@media (prefers-reduced-motion: reduce)"), true);
  assert.equal(css.includes("@import"), false);
  assert.equal(css.includes("url("), false);
  assert.equal(css.includes(":root"), false);
});

test("production bridge has no DOM, network, storage, or runtime loader API", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "globalThis.document",
    "innerHTML",
    "fetch(",
    "XMLHttpRequest",
    "localStorage",
    "sessionStorage",
    'require("node:',
  ]) {
    assert.equal(source.includes(forbidden), false);
  }
});
