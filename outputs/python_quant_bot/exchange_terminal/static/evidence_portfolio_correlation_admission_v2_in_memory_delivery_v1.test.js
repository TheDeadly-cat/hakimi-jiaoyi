"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const strictCanonical = require("./strict_canonical_json_v1.js");
const adapter = require("./evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js");

const PROJECT_ROOT = path.resolve(__dirname, "../..");
const PYTHON_FIXTURE_SCRIPT = String.raw`
import json
from tests.test_portfolio_correlation_admission_v2_in_memory_delivery_v1 import PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests
case = PortfolioCorrelationAdmissionV2InMemoryDeliveryV1Tests(methodName="runTest")
case.setUp()
_, _, block = case._block_fixture()
print(json.dumps({"exact": case.envelope, "block": block}, separators=(",", ":")))
`;
const bundle = JSON.parse(childProcess.execFileSync(
  process.env.PYTHON || "python",
  ["-c", PYTHON_FIXTURE_SCRIPT],
  { cwd: PROJECT_ROOT, encoding: "utf8", maxBuffer: 2 * 1024 * 1024 }
));

test("exact Python pass envelope verifies and extracts a frozen detached payload", () => {
  assert.equal(
    adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(bundle.exact),
    true
  );
  const payload = adapter.extractPortfolioCorrelationAdmissionV2PresentationPayloadV1(bundle.exact);
  assert.equal(payload.status, "PASS");
  assert.equal(payload.common_universe_status, "PASS");
  assert.equal(Object.isFrozen(payload), true);
  assert.notEqual(payload, bundle.exact.presentation_payload);
});

test("exact Python common-universe block remains visible and unpromoted", () => {
  assert.equal(
    adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(bundle.block),
    true
  );
  const payload = adapter.extractPortfolioCorrelationAdmissionV2PresentationPayloadV1(bundle.block);
  assert.equal(payload.status, "BLOCK");
  assert.equal(payload.first_blocking_tier, "COMMON_UNIVERSE");
  assert.equal(payload.v1_admission_status, "NOT_EVALUATED");
  assert.equal(payload.permissions.current_admission_allowed, false);
});

test("candidate or envelope hash substitution fails closed", () => {
  const candidateTamper = structuredClone(bundle.exact);
  candidateTamper.presentation_payload.candidate_hash = "f".repeat(64);
  const envelopeTamper = structuredClone(bundle.exact);
  envelopeTamper.delivery_envelope_hash = "0".repeat(64);
  assert.equal(adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(candidateTamper), false);
  assert.equal(adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(envelopeTamper), false);
  assert.equal(adapter.extractPortfolioCorrelationAdmissionV2PresentationPayloadV1(candidateTamper), null);
});

test("resealed downstream PASS after common-universe block is rejected", () => {
  const altered = structuredClone(bundle.block);
  delete altered.presentation_payload.presentation_payload_hash;
  altered.presentation_payload.checks.v1_admission_exact = true;
  altered.presentation_payload.checks.v1_admission_pass = true;
  altered.presentation_payload.v1_admission_status = "PASS";
  altered.presentation_payload = strictCanonical.sealDocument(
    altered.presentation_payload,
    "presentation_payload_hash"
  );
  delete altered.delivery_envelope_hash;
  const resealed = strictCanonical.sealDocument(altered, "delivery_envelope_hash");
  assert.equal(adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(resealed), false);
});

test("resealed permission promotion is rejected", () => {
  const altered = structuredClone(bundle.exact);
  delete altered.presentation_payload.presentation_payload_hash;
  altered.presentation_payload.permissions.paper_authorized = true;
  altered.presentation_payload = strictCanonical.sealDocument(
    altered.presentation_payload,
    "presentation_payload_hash"
  );
  delete altered.delivery_envelope_hash;
  const resealed = strictCanonical.sealDocument(altered, "delivery_envelope_hash");
  assert.equal(adapter.verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1(resealed), false);
});

test("exact extraction receipt records extraction but no presentation execution", () => {
  const receipt = adapter.buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1(bundle.exact);
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.facts.payload_extracted_in_memory, true);
  assert.equal(receipt.facts.presentation_consumer_executed, false);
  assert.equal(receipt.facts.render_called, false);
  assert.equal(receipt.facts.dom_accessed, false);
  assert.equal(receipt.authority.paper_authorized, false);
  assert.equal(
    adapter.verifyPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1(receipt, bundle.exact),
    true
  );
});

test("invalid envelope creates unknown receipt without partial hashes", () => {
  const receipt = adapter.buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1({});
  assert.equal(receipt.status, "UNKNOWN");
  assert.equal(receipt.delivery_envelope_hash, null);
  assert.equal(receipt.presentation_payload_hash, null);
  assert.equal(receipt.candidate_hash, null);
});

test("resealed receipt promotion fails exact verification", () => {
  const receipt = adapter.buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1(bundle.exact);
  delete receipt.payload_extraction_receipt_hash;
  receipt.facts.presentation_consumer_executed = true;
  const resealed = strictCanonical.sealDocument(receipt, "payload_extraction_receipt_hash");
  assert.equal(
    adapter.verifyPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1(resealed, bundle.exact),
    false
  );
});

test("public API stays frozen and carries no render function", () => {
  assert.equal(Object.isFrozen(adapter), true);
  assert.equal("render" in adapter, false);
  assert.equal("mount" in adapter, false);
});

test("production adapter has no DOM, network, storage, or promotional API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js"),
    "utf8"
  );
  assert.equal(source.includes("globalThis.document"), false);
  assert.equal(source.includes("fetch("), false);
  assert.equal(source.includes("XMLHttpRequest"), false);
  assert.equal(source.includes("localStorage"), false);
  assert.equal(source.includes("sessionStorage"), false);
  assert.equal(/\bREADY\b/i.test(source), false);
});
