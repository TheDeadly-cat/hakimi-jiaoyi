"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const strictCanonical = require("./strict_canonical_json_v1.js");
const rail = require("./evidence_portfolio_correlation_admission_rail_v1.js");
const delivery = require("./evidence_static_presentation_in_memory_delivery_v1.js");

const HASH = "a".repeat(64);

function candidate(blocked = false) {
  const checks = {
    input_snapshot_exact: true,
    input_identity_exact: true,
    report_strict_canonical: true,
    base_admission_exact: true,
    correlation_preregistration_exact: true,
    correlation_matrix_exact: true,
    selection_cells_strict_canonical: true,
    complete_link_gate_exact: true,
    complete_link_gate_pass: blocked ? false : true,
    strata_preregistration_exact: blocked ? null : true,
    strata_gate_exact: blocked ? null : true,
    strata_gate_pass: blocked ? null : true,
    evidence_has_no_execution_authority: true,
  };
  return strictCanonical.sealDocument({
    admission_state: blocked
      ? "CORRELATION_EVIDENCE_BLOCKED"
      : "CORRELATION_AND_PREREGISTERED_STRATA_VERIFIED_RESEARCH_ONLY",
    automatic_internal_backtest_activation_allowed: false,
    base_admission_status: "INTERNAL_BACKTEST_READY",
    blockers: blocked ? ["complete_link_gate_blocked"] : [],
    checks,
    complete_link_status: blocked ? "BLOCK" : "PASS",
    consumer_only: true,
    current_admission_allowed: false,
    current_writer_activation_allowed: false,
    evidence_hashes: {
      source_report_hash: HASH,
      base_admission_hash: HASH,
      correlation_preregistration_hash: HASH,
      correlation_matrix_hash: HASH,
      selection_cells_hash: HASH,
      complete_link_gate_hash: HASH,
      strata_preregistration_hash: blocked ? "" : HASH,
      strata_gate_hash: blocked ? "" : HASH,
    },
    first_blocking_tier: blocked ? "COMPLETE_LINK" : null,
    independent_vote_policy:
      "AT_MOST_ONE_VOTE_PER_PREREGISTERED_CLUSTER_WITH_STRATA_GATE",
    lane: "RAW_EXCESS",
    manual_review_required: true,
    paper_admission_status: "BLOCKED",
    permissions: { paper_authorized: false, live_order_allowed: false },
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

function authority() {
  return {
    browser_execution_allowed: false,
    current_admission_allowed: false,
    dom_mount_allowed: false,
    endpoint_registration_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    runtime_delivery_allowed: false,
    writer_allowed: false,
  };
}

function facts(known) {
  return {
    admission_candidate_embedded: known,
    browser_executed: false,
    delivery_attempted: false,
    dom_mounted: false,
    javascript_adapter_executed: false,
    markup_derived: false,
    markup_embedded: false,
    profitability_proven: false,
    raw_correlation_evidence_embedded: false,
    raw_source_report_embedded: false,
    registration_exactly_verified: known,
    runtime_mutations_performed: false,
    source_candidate_exactly_verified: known,
    view_model_derived: false,
  };
}

function consumerContract() {
  return {
    schema_version: rail.RAIL_SCHEMA_VERSION,
    static_fingerprint: rail.RAIL_STATIC_FINGERPRINT,
    browser_global: "HakimiPortfolioCorrelationAdmissionRailV1",
    verify_function: "verifyPortfolioCorrelationAdmissionV1",
    view_model_function: "buildPortfolioCorrelationAdmissionRailViewModelV1",
    render_function: "renderPortfolioCorrelationAdmissionRailV1",
  };
}

function transport() {
  return {
    mode: "IN_MEMORY_ARGUMENT_ONLY",
    content_type: "application/json",
    endpoint: null,
    route: null,
    host_slot: null,
  };
}

function envelope(blocked = false) {
  const source = candidate(blocked);
  return strictCanonical.sealDocument({
    authority: authority(),
    consumer_contract: consumerContract(),
    delivery_state: "EXACT_CANDIDATE_ENVELOPED_IN_MEMORY_HOST_UNBOUND",
    facts: facts(true),
    payload: source,
    reason_code:
      "EXACT_REGISTRATION_AND_ADMISSION_CANDIDATE_ENVELOPED_IN_MEMORY_HOST_UNBOUND",
    registration_hash: delivery.REGISTRATION_HASH,
    registration_id: "portfolio-correlation-admission-rail-v1",
    schema_version: delivery.SCHEMA_VERSION,
    source_hash: source.correlation_admission_hash,
    source_schema_version: rail.ADMISSION_SCHEMA_VERSION,
    source_status: source.status,
    static_fingerprint: delivery.STATIC_FINGERPRINT,
    status: "BLOCKED",
    transport: transport(),
  }, "envelope_hash");
}

function unknownEnvelope() {
  return strictCanonical.sealDocument({
    authority: authority(),
    consumer_contract: consumerContract(),
    delivery_state: "UNKNOWN",
    facts: facts(false),
    payload: null,
    reason_code: "ADMISSION_CANDIDATE_NOT_EXACT",
    registration_hash: null,
    registration_id: "portfolio-correlation-admission-rail-v1",
    schema_version: delivery.SCHEMA_VERSION,
    source_hash: null,
    source_schema_version: rail.ADMISSION_SCHEMA_VERSION,
    source_status: "UNKNOWN",
    static_fingerprint: delivery.STATIC_FINGERPRINT,
    status: "UNKNOWN",
    transport: transport(),
  }, "envelope_hash");
}

test("exact local pass produces a no-DOM markup-hash receipt", () => {
  const source = envelope();
  const receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(source);
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(source), true);
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryReceiptV1(receipt, source), true);
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.view.status_label, "LOCAL CLEAR");
  assert.match(receipt.markup_sha256, /^[0-9a-f]{64}$/);
  assert.equal(receipt.facts.markup_embedded, false);
  assert.equal(receipt.facts.dom_mounted, false);
});

test("high-correlation block remains visible and unauthorized", () => {
  const source = envelope(true);
  const receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(source);
  assert.equal(receipt.source_status, "BLOCK");
  assert.equal(receipt.view.status_label, "LOCAL BLOCK");
  assert.equal(receipt.view.gap_state, "OPEN");
  assert.equal(receipt.view.permission_state, "UNAUTHORIZED");
});

test("exact unknown envelope yields an unknown receipt without partial hashes", () => {
  const source = unknownEnvelope();
  const receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(source);
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(source), true);
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.markup_sha256, null);
  assert.equal(receipt.view, null);
  assert.equal(receipt.facts.envelope_exactly_verified, true);
});

test("substituted envelope hash fails closed", () => {
  const altered = structuredClone(envelope());
  altered.envelope_hash = "0".repeat(64);
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(altered), false);
  assert.equal(delivery.extractAdmissionCandidateFromEnvelopeV1(altered), null);
});

test("resealed registration hash swap is rejected", () => {
  const altered = structuredClone(envelope());
  delete altered.envelope_hash;
  altered.registration_hash = "f".repeat(64);
  const resealed = strictCanonical.sealDocument(altered, "envelope_hash");
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(resealed), false);
});

test("resealed payload substitution without source hash update is rejected", () => {
  const altered = structuredClone(envelope());
  delete altered.envelope_hash;
  altered.payload = candidate(true);
  const resealed = strictCanonical.sealDocument(altered, "envelope_hash");
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(resealed), false);
});

test("resealed authority promotion is rejected", () => {
  const altered = structuredClone(envelope());
  delete altered.envelope_hash;
  altered.authority.browser_execution_allowed = true;
  const resealed = strictCanonical.sealDocument(altered, "envelope_hash");
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(resealed), false);
});

test("resealed receipt promotion fails exact rebuild", () => {
  const source = envelope();
  const altered = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(source);
  delete altered.receipt_hash;
  altered.authority.paper_authorized = true;
  const resealed = strictCanonical.sealDocument(altered, "receipt_hash");
  assert.equal(delivery.verifyStaticPresentationInMemoryDeliveryReceiptV1(resealed, source), false);
});

test("receipt never embeds markup or implies browser execution", () => {
  const receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(envelope());
  assert.equal(Object.hasOwn(receipt, "markup"), false);
  assert.equal(receipt.facts.browser_executed, false);
  assert.equal(receipt.facts.runtime_mutations_performed, false);
  assert.equal(receipt.authority.current_admission_allowed, false);
  assert.equal(receipt.authority.paper_authorized, false);
  assert.equal(receipt.authority.live_order_allowed, false);
});
