"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const subject = require(
  "./strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js"
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

function gateFixture(status = "PASS") {
  const blocked = status === "BLOCK";
  return {
    schema_version: subject.UNCERTAINTY_GATE_SCHEMA_VERSION,
    static_fingerprint: subject.UNCERTAINTY_GATE_STATIC_FINGERPRINT,
    gate_contract_hash: subject.UNCERTAINTY_GATE_CONTRACT_HASH,
    gate_hash: "a".repeat(64),
    status,
    reason_code: blocked
      ? "CROSS_CLUSTER_DEPENDENCE_NOT_CONSERVATIVELY_GROUPED"
      : "ALL_DEPENDENCE_EDGES_WITHIN_PREREGISTERED_CLUSTERS",
    window_count: 2,
    dependence_edge_count: blocked ? 2 : 1,
    cross_cluster_dependence_edge_count: blocked ? 1 : 0,
    derived_conservative_component_count: blocked ? 2 : 3,
    preregistered_cluster_count: 3,
    private_window_receipt: "window-secret-must-not-be-rendered",
    authority: authority(),
  };
}

function trustedBudget(status = "PASS", decision = "PASS_STRATIFIED_RESEARCH_BUDGET") {
  return {
    budget_v3_hash: "d".repeat(64),
    status,
    decision,
    private_budget_source: "budget-secret-must-not-be-rendered",
    portfolio: {
      active_cluster_count: 2,
      symbol_ticket_count: 2,
      conservative_weighted_effective_strata_count: 2,
    },
  };
}

function bindingFixture(gate, mode = "research") {
  const common = {
    schema_version: subject.BUDGET_BINDING_SCHEMA_VERSION,
    static_fingerprint: subject.BUDGET_BINDING_STATIC_FINGERPRINT,
    binding_contract_hash: subject.BUDGET_BINDING_CONTRACT_HASH,
    evaluation_hash: "b".repeat(64),
    uncertainty_gate_hash: gate.gate_hash,
    uncertainty_gate_status: gate.status,
    uncertainty_dependence_edge_count: gate.dependence_edge_count,
    uncertainty_cross_cluster_edge_count:
      gate.cross_cluster_dependence_edge_count,
    uncertainty_component_count: gate.derived_conservative_component_count,
    authority: authority(),
  };
  if (mode === "veto") {
    return {
      ...common,
      status: "BLOCK",
      reason_code: "CROSS_CLUSTER_DEPENDENCE_REQUIRES_REPREREGISTRATION",
      effective_budget_status: null,
      effective_budget_decision: null,
      trusted_effective_budget_document: null,
      facts: {
        risk_increasing: true,
        budget_verification_attempted: false,
        budget_evaluation_exactly_verified: false,
      },
    };
  }
  if (mode === "reduction") {
    return {
      ...common,
      status: "PASS",
      reason_code: "EXACT_RISK_REDUCTION_PRESERVED_UNDER_UNCERTAINTY_BLOCK",
      effective_budget_status: "PASS",
      effective_budget_decision: "RISK_REDUCTION_PATH",
      trusted_effective_budget_document: trustedBudget(
        "PASS",
        "RISK_REDUCTION_PATH"
      ),
      facts: {
        risk_increasing: false,
        budget_verification_attempted: true,
        budget_evaluation_exactly_verified: true,
      },
    };
  }
  if (mode === "budget-block") {
    return {
      ...common,
      status: "PASS",
      reason_code: "UNCERTAINTY_CLUSTER_BOUND_EFFECTIVE_BUDGET_VERIFIED",
      effective_budget_status: "BLOCK",
      effective_budget_decision: "BLOCK",
      trusted_effective_budget_document: trustedBudget("BLOCK", "BLOCK"),
      facts: {
        risk_increasing: true,
        budget_verification_attempted: true,
        budget_evaluation_exactly_verified: true,
      },
    };
  }
  return {
    ...common,
    status: "PASS",
    reason_code: "UNCERTAINTY_CLUSTER_BOUND_EFFECTIVE_BUDGET_VERIFIED",
    effective_budget_status: "PASS",
    effective_budget_decision: "PASS_STRATIFIED_RESEARCH_BUDGET",
    trusted_effective_budget_document: trustedBudget(),
    facts: {
      risk_increasing: true,
      budget_verification_attempted: true,
      budget_evaluation_exactly_verified: true,
    },
  };
}

function fixture(mode = "research") {
  const gate = gateFixture(mode === "veto" || mode === "reduction" ? "BLOCK" : "PASS");
  return {
    uncertainty_cluster_gate: gate,
    uncertainty_budget_binding: bindingFixture(gate, mode),
  };
}

function build(input = fixture()) {
  return subject.buildUncertaintyEffectiveBudgetNeutralPresentationV1(input);
}

test("research budget becomes neutral local evidence with permission blocked", () => {
  const presentation = build();
  assert.equal(presentation.status, "BLOCKED");
  assert.equal(presentation.contract_state, "LOCAL_RESEARCH_EVIDENCE");
  assert.equal(
    presentation.presentation_state,
    "RESEARCH_BUDGET_CONTRACT_OBSERVED"
  );
  assert.equal(presentation.tone, "NEUTRAL");
  assert.deepEqual(
    presentation.stage_order,
    ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
  );
});

test("cross-cluster veto remains explicit and budget metrics stay absent", () => {
  const presentation = build(fixture("veto"));
  assert.equal(presentation.presentation_state, "CROSS_CLUSTER_DEPENDENCE_VETO");
  assert.equal(presentation.metrics.cross_cluster_dependence_edge_count, 1);
  assert.equal(presentation.metrics.active_cluster_count, null);
  assert.equal(presentation.metrics.symbol_ticket_count, null);
});

test("exact reduction path is normalized to risk-reduction-only", () => {
  const presentation = build(fixture("reduction"));
  assert.equal(presentation.presentation_state, "RISK_REDUCTION_ONLY");
  assert.equal(presentation.status, "BLOCKED");
  assert.equal(presentation.authority.current_admission_allowed, false);
});

test("verified downstream budget block remains a neutral block observation", () => {
  const presentation = build(fixture("budget-block"));
  assert.equal(
    presentation.presentation_state,
    "RESEARCH_BUDGET_BLOCK_OBSERVED"
  );
  assert.equal(presentation.metrics.active_cluster_count, 2);
});

test("gate hash substitution fails closed", () => {
  const input = fixture();
  input.uncertainty_budget_binding.uncertainty_gate_hash = "f".repeat(64);
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(
    presentation.reason_code,
    "GATE_TO_BUDGET_CROSS_BINDING_NOT_EXACT"
  );
});

test("count substitution fails closed even when the gate hash matches", () => {
  const input = fixture();
  input.uncertainty_budget_binding.uncertainty_component_count += 1;
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(presentation.facts.gate_to_budget_cross_binding_verified, false);
});

test("pinned contract drift fails closed", () => {
  const input = fixture();
  input.uncertainty_cluster_gate.gate_contract_hash = "0".repeat(64);
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(presentation.source.uncertainty_gate_contract_hash, null);
});

test("authority promotion in a nested source document fails closed", () => {
  const input = fixture();
  input.uncertainty_budget_binding.trusted_effective_budget_document.authority = {
    writer_allowed: true,
  };
  const presentation = build(input);
  assert.equal(presentation.status, "UNKNOWN");
  assert.equal(presentation.reason_code, "SOURCE_AUTHORITY_LOCK_NOT_EXACT");
  assert.equal(presentation.authority.writer_allowed, false);
});

test("cycles accessors custom prototypes and oversized strings are rejected", () => {
  const cyclic = fixture();
  cyclic.uncertainty_cluster_gate.loop = cyclic.uncertainty_cluster_gate;
  assert.equal(build(cyclic).status, "UNKNOWN");

  let getterInvoked = false;
  const accessor = fixture();
  Object.defineProperty(accessor, "uncertainty_cluster_gate", {
    enumerable: true,
    get() {
      getterInvoked = true;
      return gateFixture();
    },
  });
  assert.equal(build(accessor).status, "UNKNOWN");
  assert.equal(getterInvoked, false);

  const customPrototype = fixture();
  customPrototype.uncertainty_cluster_gate = Object.create({ inherited: true });
  customPrototype.uncertainty_cluster_gate.marker = "local";
  assert.equal(build(customPrototype).status, "UNKNOWN");

  const oversized = fixture();
  oversized.uncertainty_budget_binding.padding = "x".repeat(
    subject.INPUT_LIMITS.max_string_length + 1
  );
  assert.equal(build(oversized).status, "UNKNOWN");
});

test("projection emits hashes and bounded counts but no source documents", () => {
  const presentation = build();
  const serialized = JSON.stringify(presentation);
  assert.equal(serialized.includes("window-secret-must-not-be-rendered"), false);
  assert.equal(serialized.includes("budget-secret-must-not-be-rendered"), false);
  assert.equal(serialized.includes('"window_receipts":'), false);
  assert.equal(serialized.includes('"pair_assessments":'), false);
  assert.equal(serialized.includes('"trusted_effective_budget_document":'), false);
  assert.match(presentation.source.document_set_sha256, /^[0-9a-f]{64}$/);
  assert.equal(presentation.metrics.window_count, 2);
  assert.equal(presentation.metrics.conservative_weighted_strata_count, 2);
});

test("all operational authority remains false", () => {
  const presentation = build();
  assert.deepEqual(presentation.authority, {
    current_admission_allowed: false,
    dom_mount_allowed: false,
    effective_budget_activation_allowed: false,
    http_registration_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    runtime_asset_loading_allowed: false,
    writer_allowed: false,
  });
  assert.equal(presentation.facts.dom_mounted, false);
  assert.equal(presentation.facts.current_activated, false);
});

test("presentation is deterministic and exact verifier rejects resealed promotion", () => {
  const input = fixture();
  const presentation = build(input);
  assert.deepEqual(presentation, build(input));
  assert.equal(
    subject.verifyUncertaintyEffectiveBudgetNeutralPresentationV1(
      presentation,
      input
    ),
    true
  );
  const promoted = JSON.parse(JSON.stringify(presentation));
  promoted.authority.dom_mount_allowed = true;
  delete promoted.presentation_hash;
  const resealed = strictCanonical.sealDocument(
    promoted,
    "presentation_hash"
  );
  assert.equal(
    subject.verifyUncertaintyEffectiveBudgetNeutralPresentationV1(
      resealed,
      input
    ),
    false
  );
});

test("serialized model contains no promotional or directional wording", () => {
  const serialized = JSON.stringify(build());
  const forbidden = new RegExp(
    "\\b(?:" + ["REA", "DY|PRO", "FIT|RET", "URN|B", "UY|S", "ELL|PASS_STRATIFIED"].join("") + ")\\b",
    "i"
  );
  assert.equal(forbidden.test(serialized), false);
});

test("production module is unmounted and has no DOM or network operation", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js"
    ),
    "utf8"
  );
  assert.equal(source.includes("document."), false);
  assert.equal(source.includes("innerHTML"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("WebSocket"), false);
  assert.equal(source.includes("eval("), false);
});
