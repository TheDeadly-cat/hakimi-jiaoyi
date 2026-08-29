"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_downside_tail_card_v6.js");
const consumer = require("./evidence_portfolio_risk_downside_tail_consumer_fixture_v6.js");
const receipts = require("./evidence_portfolio_risk_downside_tail_consumer_execution_receipt_v4.js");

const HTTP_BLOCKERS = [
  "HTTP_CANDIDATE_V6_UNREGISTERED",
  "PRESENTATION_CONSUMER_NOT_REGISTERED",
  "CURRENT_ADMISSION_LOCKED",
];

function authority() {
  return {
    research_only: true,
    presentation_only: true,
    frontend_projection_only: true,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    formal_registry_activation_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function projection(mode = "clear") {
  const known = mode !== "unknown";
  const tailBlock = mode === "tail-block";
  const localStatus = known ? (tailBlock ? "BLOCK" : "PASS") : "UNKNOWN";
  const localBlockers = tailBlock
    ? ["downside_tail_coupling_detected"]
    : known
      ? []
      : ["downside_tail_source_observed"];
  return strictCanonical.sealDocument(
    {
      schema_version: card.PROJECTION_SCHEMA_VERSION,
      static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCK",
      decision: "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED",
      axis_order: card.STAGE_ORDER.slice(),
      source: {
        state: known ? "OBSERVED" : "UNKNOWN",
        candidate_v6_schema_version:
          "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v6",
        candidate_v6_static_fingerprint:
          "20260823-adapter-v6-envelope-first-http-unregistered-candidate-1",
        candidate_v6_response_hash: "1".repeat(64),
        candidate_v6_implementation_sha256:
          "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096",
        candidate_state: "KNOWN_BLOCKED",
        presentation_envelope_v1_hash: "2".repeat(64),
        adapter_v6_hash: "3".repeat(64),
        strict_canonical_implementation_sha256:
          "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412",
      },
      local_decision: {
        status: localStatus,
        decision: known
          ? tailBlock
            ? "BLOCK_DOWNSIDE_TAIL_COUPLING"
            : "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE"
          : "UNKNOWN",
        adapter_v5_status: known ? "PASS" : "UNKNOWN",
        downside_tail_source_state: known ? "OBSERVED" : "UNKNOWN",
        downside_tail_gate_decision: known
          ? tailBlock
            ? "BLOCK"
            : "PASS"
          : "UNKNOWN",
        downside_tail_gate_reason: known
          ? tailBlock
            ? "DOWNSIDE_TAIL_COUPLING_DETECTED"
            : "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
          : "UNKNOWN",
        risk_increasing: known ? true : null,
      },
      gaps: {
        local_blocker_count: localBlockers.length,
        local_blockers: localBlockers,
        http_candidate_blocker_count: HTTP_BLOCKERS.length,
        http_candidate_blockers: HTTP_BLOCKERS.slice(),
        candidate_blockers: HTTP_BLOCKERS.concat(
          known
            ? tailBlock
              ? ["LOCAL_RESEARCH_GATE_BLOCKED"]
              : []
            : ["JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN"]
        ),
      },
      stages: [
        {
          axis: "SOURCE",
          state: known ? "OBSERVED" : "UNKNOWN",
          detail: known
            ? "EXACT_ADAPTER_V6_AND_DOWNSIDE_TAIL_SOURCE_BOUND"
            : "EXACT_ADAPTER_V6_WITH_UNKNOWN_JOINT_SOURCE",
        },
        {
          axis: "GAP",
          state: known ? (tailBlock ? "BLOCKED" : "PRESENT") : "UNKNOWN",
          detail: known
            ? tailBlock
              ? "LOCAL_RESEARCH_GATE_BLOCKED"
              : "HTTP_REGISTRATION_CONSUMER_AND_CURRENT_GAPS"
            : "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN",
        },
        {
          axis: "MATURITY",
          state: "CANDIDATE_ONLY",
          detail: "UNMOUNTED_HTTP_CANDIDATE_V6",
        },
        {
          axis: "PERMISSION",
          state: "UNAUTHORIZED",
          detail: "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
        },
      ],
      facts: {
        candidate_v6_exactly_verified: true,
        presentation_envelope_v1_bound: true,
        adapter_v6_exactly_verified: true,
        joint_local_research_source_known: known,
        trade_symbol_set_tail_identity_set_cross_bound: known,
        downside_tail_block_override_visible: true,
        risk_reduction_joint_exemption_implemented: false,
        projection_only: true,
        source_document_embedded: false,
        verification_context_embedded: false,
        positions_embedded: false,
        aligned_observations_embedded: false,
        pair_results_embedded: false,
        runtime_consumer_bound: false,
        ui_mounted: false,
        profitability_proven: false,
      },
      authority: authority(),
    },
    "projection_hash"
  );
}

function preregistration(id = "receipt-v4-synthetic") {
  return receipts.buildPortfolioRiskDownsideTailExecutionPreregistrationV1(id);
}

function execute(mode = "clear", prereg = preregistration()) {
  const source = projection(mode);
  const receipt =
    receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      source,
      prereg
    );
  return { source, prereg, receipt };
}

test("exports are frozen and all five implementation pins are exact", () => {
  assert.equal(Object.isFrozen(receipts), true);
  assert.equal(Object.isFrozen(receipts.STAGE_ORDER), true);
  assert.equal(
    receipts.SCHEMA_VERSION,
    "portfolio-risk-downside-tail-consumer-execution-receipt-v4"
  );
  for (const value of [
    receipts.PROJECTION_IMPLEMENTATION_SHA256,
    receipts.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    receipts.CARD_IMPLEMENTATION_SHA256,
    receipts.CARD_STYLESHEET_SHA256,
    receipts.CONSUMER_IMPLEMENTATION_SHA256,
  ]) {
    assert.match(value, /^[0-9a-f]{64}$/);
  }
});

test("execution preregistration is exact sealed and authority locked", () => {
  const value = preregistration();
  assert.equal(
    receipts.verifyPortfolioRiskDownsideTailExecutionPreregistrationV1(value),
    true
  );
  assert.equal(
    strictCanonical.verifySealedDocument(value, "preregistration_hash"),
    true
  );
  assert.equal(value.authority.formal_registration_allowed, false);
  assert.equal(value.authority.paper_authorized, false);
});

test("dynamic preregistration ids produce distinct sealed bindings", () => {
  const first = preregistration("receipt-v4-a");
  const second = preregistration("receipt-v4-b");
  assert.notEqual(first.preregistration_hash, second.preregistration_hash);
  assert.equal(
    receipts.verifyPortfolioRiskDownsideTailExecutionPreregistrationV1(first),
    true
  );
  assert.equal(
    receipts.verifyPortfolioRiskDownsideTailExecutionPreregistrationV1(second),
    true
  );
});

test("local clear projection produces a pass execution receipt", () => {
  const { receipt } = execute("clear");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.local_status, "PASS");
  assert.equal(receipt.verification.view_tone, "bounded");
  assert.equal(receipt.verification.source_tail_and_local_state_preserved, true);
  assert.equal(receipt.verification.formal_registration_bound, false);
});

test("tail block is preserved while execution receipt passes", () => {
  const { receipt } = execute("tail-block");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.local_status, "BLOCK");
  assert.equal(receipt.verification.downside_tail_gate_decision, "BLOCK");
  assert.equal(receipt.verification.view_tone, "critical");
  assert.equal(receipt.authority.paper_authorized, false);
});

test("exact unknown source is preserved by a pass execution receipt", () => {
  const { receipt } = execute("unknown");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.view_source_state, "UNKNOWN");
  assert.equal(receipt.verification.local_status, "UNKNOWN");
  assert.equal(receipt.verification.view_tone, "unknown");
  assert.equal(receipt.verification.source_tail_and_local_state_preserved, true);
});

test("receipt records projection-v5 schema alias rejection", () => {
  const { receipt } = execute("clear");
  assert.equal(receipt.verification.projection_schema_alias_rejected, true);
  assert.equal(
    receipt.checks.find(
      (check) => check.name === "projection_v5_schema_alias_rejected"
    ).ok,
    true
  );
});

test("wrong projection schema blocks even with a valid seal", () => {
  const value = JSON.parse(JSON.stringify(projection("clear")));
  delete value.projection_hash;
  value.schema_version =
    "strategy-correlation-cluster-portfolio-risk-projection-v5";
  const resealed = strictCanonical.sealDocument(value, "projection_hash");
  const receipt =
    receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      resealed,
      preregistration()
    );
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("projection_v6_seal_verified"));
});

test("preregistration missing extra and authority promotion block", () => {
  const missing = JSON.parse(JSON.stringify(preregistration()));
  delete missing.preregistration_hash;
  const extra = JSON.parse(JSON.stringify(preregistration()));
  delete extra.preregistration_hash;
  extra.activation = true;
  const promoted = JSON.parse(JSON.stringify(preregistration()));
  delete promoted.preregistration_hash;
  promoted.authority.paper_authorized = true;
  const invalids = [
    missing,
    strictCanonical.sealDocument(extra, "preregistration_hash"),
    strictCanonical.sealDocument(promoted, "preregistration_hash"),
  ];
  for (const invalid of invalids) {
    const receipt =
      receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
        projection("clear"),
        invalid
      );
    assert.equal(receipt.status, "BLOCK");
    assert.equal(receipt.source.execution_preregistration_hash, null);
    assert.ok(
      receipt.blockers.includes("execution_preregistration_v1_exact")
    );
  }
});

test("receipt binds descriptor hash without embedding descriptor", () => {
  const source = projection("tail-block");
  const descriptor =
    consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
      source
    );
  const receipt =
    receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      source,
      preregistration()
    );
  assert.equal(receipt.verification.descriptor_hash, descriptor.descriptor_hash);
  assert.equal(receipt.facts.consumer_descriptor_embedded, false);
  assert.equal(receipt.facts.markup_embedded, false);
});

test("receipt is strict sealed deeply frozen and deterministic", () => {
  const source = projection("clear");
  const prereg = preregistration();
  const first =
    receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      source,
      prereg
    );
  const second =
    receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      source,
      prereg
    );
  assert.deepEqual(first, second);
  assert.equal(strictCanonical.verifySealedDocument(first, "receipt_hash"), true);
  assert.equal(Object.isFrozen(first), true);
  assert.equal(Object.isFrozen(first.checks[0]), true);
});

test("public verifier accepts exact receipt and rejects resealed tamper", () => {
  const { source, prereg, receipt } = execute("clear");
  const exact =
    receipts.verifyPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      receipt,
      source,
      prereg
    );
  assert.equal(exact.status, "PASS");
  assert.equal(
    strictCanonical.verifySealedDocument(exact, "verification_hash"),
    true
  );
  const altered = JSON.parse(JSON.stringify(receipt));
  delete altered.receipt_hash;
  altered.authority.current_admission_allowed = true;
  const resealed = strictCanonical.sealDocument(altered, "receipt_hash");
  assert.equal(
    receipts.verifyPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      resealed,
      source,
      prereg
    ).status,
    "BLOCK"
  );
});

test("facts distinguish execution from identity registration browser and authority", () => {
  const { receipt } = execute("clear");
  assert.equal(receipt.facts.local_process_execution_observed, true);
  assert.equal(receipt.facts.node_process_identity_authenticated, false);
  assert.equal(receipt.facts.receipt_signature_verified, false);
  assert.equal(receipt.facts.external_execution_authority_verified, false);
  assert.equal(receipt.facts.execution_preregistration_bound, true);
  assert.equal(receipt.facts.formal_registration_bound, false);
  assert.equal(receipt.facts.stylesheet_executed, false);
  assert.equal(receipt.facts.dom_accessed, false);
  assert.equal(receipt.facts.browser_visual_review_performed, false);
  for (const [key, value] of Object.entries(receipt.authority)) {
    if (key !== "descriptive_only") assert.equal(value, false);
  }
});

test("receipt embeds no projection descriptor markup or promotion claim", () => {
  const serialized = JSON.stringify(execute("clear").receipt);
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(serialized, promotion);
  assert.doesNotMatch(serialized, /hakimi-risk-tail-card-v6/);
});

test("production receipt uses no filesystem DOM browser or network primitive", () => {
  const source = fs.readFileSync(
    path.resolve(
      __dirname,
      "evidence_portfolio_risk_downside_tail_consumer_execution_receipt_v4.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "node:fs",
    "document.",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
  ]) {
    assert.equal(source.includes(forbidden), false);
  }
});
