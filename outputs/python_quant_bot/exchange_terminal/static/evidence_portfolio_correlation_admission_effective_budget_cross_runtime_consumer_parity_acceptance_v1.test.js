"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const subject = require("./evidence_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_acceptance_v1.js");

const ROOT = path.resolve(__dirname, "..", "..");
const registration = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "tests/fixtures/portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_registration_v1.json"
    ),
    "utf8"
  )
);
const fixture = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "tests/fixtures/portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.json"
    ),
    "utf8"
  )
);

function clone(value) {
  return structuredClone(value);
}

function resealRegistration(value) {
  delete value.parity_registration_hash;
  value.parity_registration_hash = strictCanonical.strictCanonicalHash(value);
  return value;
}

function resealPython(value) {
  delete value.consumer_result_hash;
  value.consumer_result_hash = strictCanonical.strictCanonicalHash(value);
  return value;
}

function resealReceipt(value) {
  delete value.acceptance_receipt_hash;
  value.acceptance_receipt_hash = strictCanonical.strictCanonicalHash(value);
  return value;
}

test("Python registration verifies exactly in JavaScript", () => {
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
      registration
    ),
    true
  );
  assert.equal(registration.status, "BLOCKED");
  assert.equal(
    registration.registration_state,
    "THREE_STATE_CROSS_RUNTIME_CONSUMER_PARITY_REGISTERED_UNBOUND"
  );
});

test("exact acceptance receipt is deterministic, frozen, and verifies", () => {
  const first =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  const second =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  assert.deepEqual(first, second);
  assert.equal(first.status, "EXACT");
  assert.equal(Object.isFrozen(first), true);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      first,
      registration,
      fixture
    ),
    true
  );
});

test("state receipts preserve exact KNOWN UNKNOWN BLOCKED order", () => {
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  assert.deepEqual(
    receipt.state_receipts.map((row) => row.state),
    ["KNOWN", "UNKNOWN", "BLOCKED"]
  );
  assert.equal(receipt.state_receipts.every((row) => row.matched), true);
});

test("state receipt hashes match the registered parity matrix", () => {
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  for (let index = 0; index < receipt.state_receipts.length; index += 1) {
    const actual = receipt.state_receipts[index];
    const expected = registration.parity_matrix[index];
    for (const key of [
      "python_result_hash",
      "python_envelope_hash",
      "javascript_result_hash",
      "extraction_receipt_hash",
      "presentation_hash",
      "markup_hash",
      "bridge_status_label",
      "source_hash_policy",
    ]) {
      assert.equal(actual[key], expected[key], actual.state + ":" + key);
    }
  }
});

test("known and unknown presentation semantics remain distinct", () => {
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  assert.equal(receipt.state_receipts[0].bridge_status_label, "LOCAL ALIGNMENT");
  assert.equal(receipt.state_receipts[1].bridge_status_label, "SOURCE UNKNOWN");
  assert.notEqual(
    receipt.state_receipts[0].markup_hash,
    receipt.state_receipts[1].markup_hash
  );
  assert.equal(receipt.facts.known_unknown_markup_distinct, true);
});

test("blocked state carries no envelope or presentation hashes", () => {
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  const blocked = receipt.state_receipts[2];
  assert.equal(blocked.python_envelope_hash, null);
  assert.equal(blocked.extraction_receipt_hash, null);
  assert.equal(blocked.presentation_hash, null);
  assert.equal(blocked.markup_hash, null);
  assert.equal(blocked.bridge_status_label, null);
});

test("receipt embeds hashes only and keeps all authority false", () => {
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  const serialized = JSON.stringify(receipt).toLowerCase();
  for (const forbidden of [
    "\"positions\"",
    "\"proposed_symbol\"",
    "\"prices\"",
    "\"returns\"",
    "\"bars\"",
    "\"account_id\"",
    "\"markup\"",
    "\"paper_authorized\":true",
    "\"live_order_allowed\":true",
  ]) {
    assert.equal(serialized.includes(forbidden), false, forbidden);
  }
  assert.equal(
    Object.values(receipt.authority).every((value) => value === false),
    true
  );
});

test("resealed registration source drift blocks acceptance", () => {
  const drifted = clone(registration);
  drifted.consumer_contracts[1].implementation_sha256 = "0".repeat(64);
  drifted.consumer_pair_hash = strictCanonical.strictCanonicalHash(
    drifted.consumer_contracts
  );
  resealRegistration(drifted);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
      drifted
    ),
    false
  );
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      drifted,
      fixture
    );
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.state_receipts.length, 0);
});

test("resealed parity matrix drift blocks acceptance", () => {
  const drifted = clone(registration);
  drifted.parity_matrix[0].markup_hash = "1".repeat(64);
  drifted.parity_matrix_hash = strictCanonical.strictCanonicalHash(
    drifted.parity_matrix
  );
  resealRegistration(drifted);
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      drifted,
      fixture
    );
  assert.equal(receipt.status, "BLOCKED");
});

test("resealed Python authority drift blocks acceptance", () => {
  const driftedFixture = clone(fixture);
  driftedFixture.known_result.authority.paper_authorized = true;
  resealPython(driftedFixture.known_result);
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      driftedFixture
    );
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.facts.javascript_results_verified, false);
});

test("fixture extra field blocks before parity execution", () => {
  const driftedFixture = clone(fixture);
  driftedFixture.extension = { enabled: false };
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      driftedFixture
    );
  assert.equal(receipt.status, "BLOCKED");
  assert.equal(receipt.facts.fixture_verified, false);
});

test("resealed acceptance state drift is rejected", () => {
  const receipt = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    )
  );
  receipt.state_receipts[0].matched = false;
  resealReceipt(receipt);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      receipt,
      registration,
      fixture
    ),
    false
  );
});

test("resealed acceptance authority promotion is rejected", () => {
  const receipt = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    )
  );
  receipt.authority.host_binding_allowed = true;
  resealReceipt(receipt);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      receipt,
      registration,
      fixture
    ),
    false
  );
});

test("resealed extra acceptance field is rejected", () => {
  const receipt = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    )
  );
  receipt.extension = { enabled: false };
  resealReceipt(receipt);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      receipt,
      registration,
      fixture
    ),
    false
  );
});

test("cyclic and non-native inputs fail closed", () => {
  const cyclic = {};
  cyclic.cycle = cyclic;
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
      cyclic
    ),
    false
  );
  assert.equal(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      cyclic,
      fixture
    ).status,
    "BLOCKED"
  );
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1(
      new Date()
    ),
    false
  );
});

test("public API and activation locks remain frozen", () => {
  assert.deepEqual(Object.keys(subject).sort(), [
    "BROWSER_GLOBAL",
    "CONSUMER_PREREGISTRATION_HASH",
    "FUNCTION_EXPORTS",
    "INPUT_FIXTURE_CANONICAL_HASH",
    "INPUT_FIXTURE_SCHEMA_VERSION",
    "JAVASCRIPT_CONSUMER_CONTRACT_HASH",
    "PYTHON_CONSUMER_CONTRACT_HASH",
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_STATIC_FINGERPRINT",
    "SCHEMA_VERSION",
    "STATE_ORDER",
    "STATIC_FINGERPRINT",
    "STATUS_MAPPING_HASH",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityRegistrationV1",
  ]);
  const receipt =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetCrossRuntimeConsumerParityAcceptanceV1(
      registration,
      fixture
    );
  assert.equal(receipt.facts.host_bindings_declared, false);
  assert.equal(receipt.facts.browser_executed, false);
  assert.equal(receipt.facts.dom_mounted, false);
});

test("production acceptance has no DOM network storage or host-loader API", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_acceptance_v1.js"
    ),
    "utf8"
  );
  for (const forbidden of [
    "globalThis.document",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "localStorage",
    "sessionStorage",
    "WebSocket",
    "node:fs",
    "child_process",
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});
