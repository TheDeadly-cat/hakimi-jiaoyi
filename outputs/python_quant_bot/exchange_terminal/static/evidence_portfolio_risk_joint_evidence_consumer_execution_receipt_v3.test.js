"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_joint_evidence_card_v5.js");
const consumer = require(
  "./evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js"
);
const receipts = require(
  "./evidence_portfolio_risk_joint_evidence_consumer_execution_receipt_v3.js"
);

function registrationBinding(hash) {
  return {
    schema_version: receipts.REGISTRATION_SCHEMA_VERSION,
    static_fingerprint: receipts.REGISTRATION_STATIC_FINGERPRINT,
    implementation_sha256: receipts.REGISTRATION_IMPLEMENTATION_SHA256,
    registration_hash: hash || "6".repeat(64)
  };
}

function projection(localStatus) {
  const status = localStatus || "PASS";
  const passed = status === "PASS";
  return strictCanonical.sealDocument(
    {
      schema_version: card.PROJECTION_SCHEMA_VERSION,
      static_fingerprint: card.PROJECTION_STATIC_FINGERPRINT,
      status: "BLOCK",
      decision:
        "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
      source: {
        candidate_v5_schema_version: "candidate-v5",
        candidate_v5_static_fingerprint: "candidate-v5-lock",
        candidate_v5_response_hash: "1".repeat(64),
        candidate_v5_exactly_verified: true,
        candidate_v5_implementation_sha256: "2".repeat(64),
        candidate_state: "KNOWN_BLOCKED",
        source_preregistration_hash: "3".repeat(64),
        portfolio_risk_adapter_v5_hash: "4".repeat(64)
      },
      local_decision: {
        status,
        decision: "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE",
        joint_risk_gate_passed: passed,
        blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"]
      },
      joint_risk: {
        assessment: passed
          ? "LOCAL_JOINT_RESEARCH_GATE_PASSED"
          : "LOCAL_JOINT_RESEARCH_GATE_BLOCKED",
        multi_window_stability_gate_verified: passed,
        anchor_window_budget_and_context_bound: true,
        trade_identity_cross_bound: true,
        anchor_window_id: "medium",
        trade_identity_hash: "5".repeat(64)
      },
      gaps: {
        remaining_blocker_count: 1,
        remaining_blockers: ["route_unregistered"],
        candidate_blockers: ["PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED"]
      },
      stages: [
        { key: "SOURCE", state: "VERIFIED", detail: "V5_EXACT_REBUILD" },
        { key: "GAP", state: "PRESENT", detail: "EXTERNAL_GAPS" },
        { key: "MATURITY", state: "LOCAL_EVIDENCE_BOUND", detail: "LOCAL_ONLY" },
        { key: "PERMISSION", state: "UNAUTHORIZED", detail: "NO_AUTHORITY" }
      ],
      facts: {
        projection_only: true,
        candidate_v5_exactly_verified: true,
        http_candidate_to_projection_bound: true,
        source_document_embedded: false,
        verification_context_embedded: false,
        positions_embedded: false,
        correlation_matrices_embedded: false,
        profitability_proven: false,
        runtime_consumer_bound: false,
        ui_mounted: false
      },
      authority: {
        research_only: true,
        presentation_only: true,
        current_admission_allowed: false,
        current_pointer_written: false,
        formal_registry_activation_allowed: false,
        live_order_allowed: false,
        migration_allowed: false,
        paper_authorized: false,
        runtime_gate_activation_allowed: false,
        shadow_consumer_activation_allowed: false,
        writer_allowed: false
      }
    },
    "projection_hash"
  );
}

function execute(localStatus, binding) {
  const source = projection(localStatus);
  const registration = binding || registrationBinding();
  return {
    source,
    registration,
    receipt:
      receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
        source,
        registration
      )
  };
}

test("exports are frozen and all six implementation pins are exact", () => {
  assert.equal(Object.isFrozen(receipts), true);
  assert.equal(Object.isFrozen(receipts.STAGE_ORDER), true);
  assert.equal(
    receipts.SCHEMA_VERSION,
    "portfolio-risk-joint-evidence-consumer-execution-receipt-v3"
  );
  for (const value of [
    receipts.PROJECTION_IMPLEMENTATION_SHA256,
    receipts.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    receipts.CARD_IMPLEMENTATION_SHA256,
    receipts.CARD_STYLESHEET_SHA256,
    receipts.CONSUMER_IMPLEMENTATION_SHA256,
    receipts.REGISTRATION_IMPLEMENTATION_SHA256
  ]) assert.match(value, /^[0-9a-f]{64}$/);
});

test("valid local pass projection produces a local execution pass receipt", () => {
  const { receipt } = execute("PASS");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.local_joint_gate_status, "PASS");
  assert.equal(receipt.verification.local_joint_gate_passed, true);
  assert.equal(receipt.verification.local_joint_gate_state_preserved, true);
  assert.equal(receipt.authority.presentation_mount_allowed, false);
});

test("valid local block projection remains block while execution receipt passes", () => {
  const { receipt } = execute("BLOCK");
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.local_joint_gate_status, "BLOCK");
  assert.equal(receipt.verification.local_joint_gate_passed, false);
  assert.equal(receipt.verification.view_status_label, "LOCAL GATE BLOCK");
  assert.equal(receipt.authority.paper_authorized, false);
});

test("receipt records a resealed wrong-schema adversarial rejection", () => {
  const { receipt } = execute("PASS");
  assert.equal(receipt.verification.projection_seal_verified, true);
  assert.equal(receipt.verification.projection_schema_alias_rejected, true);
  assert.equal(
    receipt.checks.find(
      (check) => check.name === "projection_schema_alias_rejected"
    ).ok,
    true
  );
});

test("wrong projection schema blocks the receipt even with a valid canonical seal", () => {
  const value = JSON.parse(JSON.stringify(projection("PASS")));
  delete value.projection_hash;
  value.schema_version = "strategy-correlation-cluster-portfolio-risk-projection-v4";
  const resealed = strictCanonical.sealDocument(value, "projection_hash");
  assert.equal(strictCanonical.verifySealedDocument(resealed, "projection_hash"), true);
  const receipt =
    receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      resealed,
      registrationBinding()
    );
  assert.equal(receipt.status, "BLOCK");
  assert.ok(receipt.blockers.includes("projection_v5_seal_verified"));
});

test("registration binding is exact and rejects missing or extra fields", () => {
  const missing = registrationBinding();
  delete missing.registration_hash;
  const extra = registrationBinding();
  extra.activation = true;
  for (const invalid of [missing, extra]) {
    const receipt =
      receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
        projection("PASS"),
        invalid
      );
    assert.equal(receipt.status, "BLOCK");
    assert.equal(receipt.source.registration_hash, null);
    assert.ok(receipt.blockers.includes("registration_v4_binding_exact"));
  }
});

test("dynamic registration hash is bound rather than hard coded", () => {
  const first = execute("PASS", registrationBinding("6".repeat(64))).receipt;
  const second = execute("PASS", registrationBinding("7".repeat(64))).receipt;
  assert.equal(first.status, "PASS");
  assert.equal(second.status, "PASS");
  assert.equal(first.source.registration_hash, "6".repeat(64));
  assert.equal(second.source.registration_hash, "7".repeat(64));
  assert.notEqual(first.receipt_hash, second.receipt_hash);
});

test("receipt binds the exact consumer descriptor hash without embedding it", () => {
  const source = projection("PASS");
  const descriptor =
    consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(source);
  const receipt =
    receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      source,
      registrationBinding()
    );
  assert.equal(receipt.status, "PASS");
  assert.equal(receipt.verification.descriptor_sha256, descriptor.descriptor_hash);
  assert.equal(receipt.facts.consumer_descriptor_embedded, false);
});

test("receipt has a strict canonical seal and is deeply frozen", () => {
  const { receipt } = execute("PASS");
  assert.equal(strictCanonical.verifySealedDocument(receipt, "receipt_hash"), true);
  assert.equal(Object.isFrozen(receipt), true);
  assert.equal(Object.isFrozen(receipt.source), true);
  assert.equal(Object.isFrozen(receipt.checks), true);
  assert.equal(Object.isFrozen(receipt.checks[0]), true);
});

test("public exact verifier accepts exact receipt and rejects resealed tamper", () => {
  const { source, registration, receipt } = execute("PASS");
  assert.equal(
    receipts.verifyPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      receipt,
      source,
      registration
    ).status,
    "PASS"
  );
  const tampered = JSON.parse(JSON.stringify(receipt));
  delete tampered.receipt_hash;
  tampered.authority.paper_authorized = true;
  const resealed = strictCanonical.sealDocument(tampered, "receipt_hash");
  const verification =
    receipts.verifyPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      resealed,
      source,
      registration
    );
  assert.equal(verification.status, "BLOCK");
  assert.equal(verification.receipt_exactly_rebuilt, false);
});

test("receipt is deterministic and does not mutate either input", () => {
  const source = projection("PASS");
  const registration = registrationBinding();
  const before = JSON.stringify({ source, registration });
  const first =
    receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      source,
      registration
    );
  const second =
    receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      source,
      registration
    );
  assert.deepEqual(first, second);
  assert.equal(JSON.stringify({ source, registration }), before);
});

test("facts distinguish local execution from identity browser CSS and authority", () => {
  const { receipt } = execute("PASS");
  assert.equal(receipt.facts.local_process_execution_observed, true);
  assert.equal(receipt.facts.node_process_identity_authenticated, false);
  assert.equal(receipt.facts.receipt_signature_verified, false);
  assert.equal(receipt.facts.external_execution_authority_verified, false);
  assert.equal(receipt.facts.stylesheet_declared, true);
  assert.equal(receipt.facts.stylesheet_executed, false);
  assert.equal(receipt.facts.dom_accessed, false);
  assert.equal(receipt.facts.browser_visual_review_performed, false);
  for (const [key, value] of Object.entries(receipt.authority)) {
    if (key !== "descriptive_only") assert.equal(value, false);
  }
});

test("receipt embeds no source descriptor markup or promotion claim", () => {
  const { receipt } = execute("PASS");
  const serialized = JSON.stringify(receipt);
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  assert.doesNotMatch(serialized, promotion);
  assert.doesNotMatch(serialized, /hakimi-joint-risk-card-v5/);
  assert.equal(receipt.facts.projection_document_embedded, false);
  assert.equal(receipt.facts.source_evidence_embedded, false);
  assert.equal(receipt.facts.markup_embedded, false);
  assert.equal(receipt.facts.profitability_proven, false);
});

test("production receipt uses no filesystem DOM browser or network primitive", () => {
  const source = fs.readFileSync(
    path.resolve(
      __dirname,
      "evidence_portfolio_risk_joint_evidence_consumer_execution_receipt_v3.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "node:fs",
    "document.",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket"
  ]) assert.equal(source.includes(forbidden), false);
});
