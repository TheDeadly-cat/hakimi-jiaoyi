"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { spawnSync } = require("node:child_process");

const strict = require("./strict_canonical_json_v1.js");
const subject = require(
  "./evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js"
);

function fixtures() {
  const script = [
    "import json",
    "from tests.test_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1 import PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests",
    "case = PortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1Tests()",
    "case.setUp()",
    "print(json.dumps({'pass': case.envelope, 'block': case.blocked_envelope, 'unknown': case.unknown_envelope}, separators=(',', ':')))",
  ].join("\n");
  const result = spawnSync("python", ["-c", script], {
    cwd: path.resolve(__dirname, "../.."),
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

const documents = fixtures();

test("exact pass envelope verifies and extracts a frozen payload", () => {
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      documents.pass
    ),
    true
  );
  const payload =
    subject.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
      documents.pass
    );
  assert.equal(payload.binding_status, "PASS");
  assert.equal(Object.isFrozen(payload), true);
  assert.equal(Object.isFrozen(payload.source), true);
  assert.equal(Object.isFrozen(payload.tiers), true);
});

test("exact budget block remains known and preserves its first tier", () => {
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      documents.block
    ),
    true
  );
  const payload =
    subject.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
      documents.block
    );
  assert.equal(payload.binding_status, "BLOCK");
  assert.equal(
    payload.first_blocking_tier,
    "EFFECTIVE_BUDGET_V3_DECISION"
  );
  assert.equal(payload.checks.effective_budget_v3_exact, true);
});

test("canonical unknown verifies but exposes no payload", () => {
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      documents.unknown
    ),
    true
  );
  assert.equal(
    subject.extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1(
      documents.unknown
    ),
    null
  );
});

test("unsealed envelope mutation is rejected", () => {
  const mutated = structuredClone(documents.pass);
  mutated.delivery_state = "FORGED";
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      mutated
    ),
    false
  );
});

test("resealed payload permission promotion is semantically rejected", () => {
  const forged = structuredClone(documents.pass);
  forged.presentation_payload.permissions.paper_authorized = true;
  forged.presentation_payload = strict.sealDocument(
    forged.presentation_payload,
    "presentation_payload_hash"
  );
  forged.provenance.presentation_payload_hash =
    forged.presentation_payload.presentation_payload_hash;
  const resealed = strict.sealDocument(forged, "delivery_envelope_hash");
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      resealed
    ),
    false
  );
});

test("resealed decision inconsistency is rejected", () => {
  const forged = structuredClone(documents.block);
  forged.presentation_payload.binding_status = "PASS";
  forged.presentation_payload = strict.sealDocument(
    forged.presentation_payload,
    "presentation_payload_hash"
  );
  forged.provenance.presentation_payload_hash =
    forged.presentation_payload.presentation_payload_hash;
  const resealed = strict.sealDocument(forged, "delivery_envelope_hash");
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      resealed
    ),
    false
  );
});

test("doubly resealed READY blocker is rejected", () => {
  const forged = structuredClone(documents.block);
  forged.presentation_payload.blockers = ["READY"];
  forged.presentation_payload = strict.sealDocument(
    forged.presentation_payload,
    "presentation_payload_hash"
  );
  forged.provenance.presentation_payload_hash =
    forged.presentation_payload.presentation_payload_hash;
  const resealed = strict.sealDocument(forged, "delivery_envelope_hash");
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      resealed
    ),
    false
  );
});

test("payload is hash-only and omits raw identities and positions", () => {
  const encoded = JSON.stringify(documents.pass.presentation_payload);
  for (const forbidden of [
    '"positions":',
    '"symbol":',
    '"notional":',
    "synthetic-strategy",
    "synthetic-variant",
    "cluster_exposures",
    "READY",
  ]) {
    assert.equal(encoded.includes(forbidden), false);
  }
  assert.equal(
    Object.keys(documents.pass.presentation_payload.source).length,
    12
  );
});

test("receipts distinguish extracted, unknown, and invalid envelopes", () => {
  const passReceipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      documents.pass
    );
  const unknownReceipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      documents.unknown
    );
  const invalidReceipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      {}
    );
  assert.equal(passReceipt.status, "PASS");
  assert.equal(unknownReceipt.reason_code, "ENVELOPE_UNKNOWN");
  assert.equal(invalidReceipt.reason_code, "ENVELOPE_INVALID");
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      passReceipt,
      documents.pass
    ),
    true
  );
});

test("public API, tier order, and receipts remain frozen", () => {
  assert.equal(Object.isFrozen(subject), true);
  assert.equal(Object.isFrozen(subject.TIER_ORDER), true);
  assert.deepEqual(subject.TIER_ORDER, [
    "INPUT_SNAPSHOT",
    "ADMISSION_V2_EXACT",
    "EFFECTIVE_BUDGET_V3_EXACT",
    "CROSS_SOURCE_BINDING",
    "ADMISSION_V2_DECISION",
    "EFFECTIVE_BUDGET_V3_DECISION",
    "PERMISSION",
  ]);
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      documents.pass
    );
  assert.equal(Object.isFrozen(receipt), true);
});

test("production adapter has no DOM, network, storage, or Node runtime API", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js"
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
