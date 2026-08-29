"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const strictCanonical = require("./strict_canonical_json_v1.js");
const delivery = require("./evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js");
const bridge = require("./evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js");
const subject = require("./evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.js");

const ROOT = path.resolve(__dirname, "..", "..");
const FIXTURE_PATH = path.join(
  ROOT,
  "tests",
  "fixtures",
  "portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.json"
);
const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));

function clone(value) {
  return structuredClone(value);
}

function resealPythonResult(value) {
  delete value.consumer_result_hash;
  value.consumer_result_hash = strictCanonical.strictCanonicalHash(value);
  return value;
}

function resealJavascriptResult(value) {
  delete value.javascript_consumer_result_hash;
  value.javascript_consumer_result_hash =
    strictCanonical.strictCanonicalHash(value);
  return value;
}

test("exact known Python result builds a deterministic frozen inspection result", () => {
  const first =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  const second =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  assert.deepEqual(first, second);
  assert.equal(first.status, "KNOWN");
  assert.equal(
    first.reason_code,
    "EXACT_PYTHON_CONSUMER_RESULT_VERIFIED_AND_BRIDGE_BUILT"
  );
  assert.equal(Object.isFrozen(first), true);
  assert.equal(Object.isFrozen(first.bridge_view_model), true);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      first,
      fixture.known_result
    ),
    true
  );
});

test("known Python result outer seal and semantic chain verify exactly", () => {
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      fixture.known_result
    ),
    true
  );
  assert.equal(
    delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1(
      fixture.known_result.envelope
    ),
    true
  );
  assert.equal(
    fixture.known_result.envelope_hash,
    fixture.known_result.envelope.delivery_envelope_hash
  );
});

test("known result preserves exact cross-runtime source receipts", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  assert.deepEqual(result.source_receipt, {
    python_consumer_result_hash:
      fixture.known_result.consumer_result_hash,
    envelope_hash: fixture.known_result.envelope_hash,
    binding_hash: fixture.known_result.source_hashes.binding_hash,
    admission_v2_hash:
      fixture.known_result.source_hashes.admission_v2_hash,
    effective_budget_v3_hash:
      fixture.known_result.source_hashes.effective_budget_v3_hash,
    presentation_payload_hash:
      fixture.known_result.source_hashes.presentation_payload_hash,
  });
});

test("known extraction receipt verifies against the embedded envelope", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  assert.equal(
    delivery.verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1(
      result.extraction_receipt,
      fixture.known_result.envelope
    ),
    true
  );
  assert.equal(result.facts.extraction_receipt_verified, true);
});

test("known bridge remains neutral, unmounted, and structurally complete", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  assert.equal(
    result.bridge_view_model.schema_version,
    bridge.BRIDGE_SCHEMA_VERSION
  );
  assert.deepEqual(
    result.bridge_view_model.stages.map((stage) => stage.axis),
    bridge.STAGE_ORDER
  );
  assert.equal(typeof result.markup, "string");
  assert.equal(result.markup.length > 0, true);
  assert.equal(result.markup.includes("LOCAL ALIGNMENT"), true);
  assert.equal(result.markup.includes("SOURCE UNKNOWN"), false);
  assert.equal(/\bREADY\b/i.test(result.markup), false);
  assert.equal(result.facts.dom_mounted, false);
  assert.equal(result.facts.browser_executed, false);
});

test("unknown Python result builds a verified neutral unknown bridge", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.unknown_result
    );
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      fixture.unknown_result
    ),
    true
  );
  assert.equal(result.status, "UNKNOWN");
  assert.equal(
    result.reason_code,
    "EXACT_PYTHON_UNKNOWN_RESULT_VERIFIED_AND_NEUTRAL_BRIDGE_BUILT"
  );
  assert.equal(result.bridge_view_model.status_label, "SOURCE UNKNOWN");
  assert.equal(result.markup.includes("SOURCE UNKNOWN"), true);
  const known =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  assert.notEqual(result.markup, known.markup);
  assert.equal(result.extraction_receipt.status, "BLOCK");
  assert.equal(result.extraction_receipt.reason_code, "ENVELOPE_UNKNOWN");
  assert.equal(result.extraction_receipt.facts.payload_extracted, false);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.unknown_result
    ),
    true
  );
});

test("valid blocked Python result never invokes JavaScript presentation", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.blocked_result
    );
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      fixture.blocked_result
    ),
    true
  );
  assert.equal(result.status, "BLOCKED");
  assert.equal(
    result.reason_code,
    "PYTHON_CONSUMER_RESULT_BLOCKED_NO_JAVASCRIPT_ADAPTER_INVOCATION"
  );
  assert.equal(result.extraction_receipt, null);
  assert.equal(result.bridge_view_model, null);
  assert.equal(result.markup, null);
  assert.equal(result.facts.javascript_adapter_invoked, false);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.blocked_result
    ),
    true
  );
});

test("resealed Python authority promotion blocks before JavaScript adapter use", () => {
  const drifted = clone(fixture.known_result);
  drifted.authority.paper_authorized = true;
  resealPythonResult(drifted);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      drifted
    ),
    false
  );
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      drifted
    );
  assert.equal(result.status, "BLOCKED");
  assert.equal(
    result.reason_code,
    "PYTHON_CONSUMER_RESULT_INVALID_NO_JAVASCRIPT_ADAPTER_INVOCATION"
  );
  assert.equal(result.facts.javascript_adapter_invoked, false);
  assert.equal(result.bridge_view_model, null);
});

test("doubly resealed embedded-envelope permission promotion is rejected", () => {
  const drifted = clone(fixture.known_result);
  drifted.envelope.authority.paper_authorized = true;
  delete drifted.envelope.delivery_envelope_hash;
  drifted.envelope.delivery_envelope_hash =
    strictCanonical.strictCanonicalHash(drifted.envelope);
  drifted.envelope_hash = drifted.envelope.delivery_envelope_hash;
  resealPythonResult(drifted);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      drifted
    ),
    false
  );
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      drifted
    );
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.facts.javascript_adapter_invoked, false);
});

test("resealed Python source-hash drift is rejected before extraction", () => {
  const drifted = clone(fixture.known_result);
  drifted.source_hashes.binding_hash = "0".repeat(64);
  resealPythonResult(drifted);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      drifted
    ),
    false
  );
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      drifted
    );
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.extraction_receipt, null);
});

test("resealed JavaScript markup mutation is rejected", () => {
  const result = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    )
  );
  result.markup += "<div>drift</div>";
  resealJavascriptResult(result);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.known_result
    ),
    false
  );
});

test("resealed JavaScript authority promotion is rejected", () => {
  const result = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    )
  );
  result.authority.dom_mount_allowed = true;
  resealJavascriptResult(result);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.known_result
    ),
    false
  );
});

test("resealed required-contract drift is rejected", () => {
  const result = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    )
  );
  result.required_contracts.javascript_consumer_contract_hash = "1".repeat(64);
  resealJavascriptResult(result);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.known_result
    ),
    false
  );
});

test("resealed extra field is rejected by exact rebuild", () => {
  const result = clone(
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    )
  );
  result.extension = { enabled: false };
  resealJavascriptResult(result);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      result,
      fixture.known_result
    ),
    false
  );
});

test("cyclic and non-native Python results fail closed", () => {
  const cyclic = {};
  cyclic.cycle = cyclic;
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      cyclic
    ),
    false
  );
  const blocked =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      cyclic
    );
  assert.equal(blocked.status, "BLOCKED");
  assert.equal(blocked.facts.javascript_adapter_invoked, false);
  assert.equal(
    subject.verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1(
      new Date()
    ),
    false
  );
});

test("result is hash-only with permanent permission locks", () => {
  const result =
    subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
      fixture.known_result
    );
  const serialized = JSON.stringify(result).toLowerCase();
  for (const forbidden of [
    "\"positions\"",
    "\"proposed_symbol\"",
    "\"prices\"",
    "\"returns\"",
    "\"bars\"",
    "\"account_id\"",
    "\"paper_authorized\":true",
    "\"live_order_allowed\":true",
  ]) {
    assert.equal(serialized.includes(forbidden), false, forbidden);
  }
  assert.equal(
    Object.values(result.authority).every((value) => value === false),
    true
  );
});

test("fixture is exact, synthetic, and byte-pinned", () => {
  const bytes = fs.readFileSync(FIXTURE_PATH);
  assert.equal(
    crypto.createHash("sha256").update(bytes).digest("hex"),
    "b25be196152f370101bc43cf61e065308761d3070c4edb4656ffd00ad287dbe7"
  );
  assert.equal(fixture.synthetic_only, true);
  assert.equal(
    fixture.known_result.consumer_result_hash,
    "4271f49558382127bb0e1e737ca080686c305907e60e0b5514aded14a98e7b96"
  );
  assert.equal(
    fixture.unknown_result.consumer_result_hash,
    "6c67f3e287102d467c5a22f3ff57a2130a40654c7ee994cc560bba4673b04273"
  );
  assert.equal(
    fixture.blocked_result.consumer_result_hash,
    "a762ed471125031bf15ed39290b8a6e778454dfa68f07500a473d60f0b8fe9f3"
  );
});

test("all predecessor implementation pins match current source", () => {
  const expected = new Map([
    [
      "exchange_terminal/services/portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.py",
      subject.PYTHON_CONSUMER_IMPLEMENTATION_SHA256,
    ],
    [
      "tests/test_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1.py",
      subject.PYTHON_CONSUMER_TEST_SHA256,
    ],
    [
      "docs/adr/0311-portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-v1.md",
      subject.PYTHON_CONSUMER_ADR_SHA256,
    ],
    [
      "exchange_terminal/static/strict_canonical_json_v1.js",
      subject.STRICT_CANONICAL_JAVASCRIPT_SHA256,
    ],
    [
      "exchange_terminal/static/evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js",
      subject.DELIVERY_JAVASCRIPT_SHA256,
    ],
    [
      "exchange_terminal/static/evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js",
      subject.BRIDGE_JAVASCRIPT_SHA256,
    ],
  ]);
  for (const [relativePath, expectedHash] of expected) {
    const actual = crypto
      .createHash("sha256")
      .update(fs.readFileSync(path.join(ROOT, relativePath)))
      .digest("hex");
    assert.equal(actual, expectedHash, relativePath);
  }
});

test("public API and cross-runtime status mapping remain frozen", () => {
  assert.deepEqual(Object.keys(subject).sort(), [
    "ADAPTER_REGISTRATION_HASH",
    "BRIDGE_JAVASCRIPT_SHA256",
    "BROWSER_GLOBAL",
    "CONSUMER_ID",
    "CONSUMER_PREREGISTRATION_HASH",
    "DELIVERY_JAVASCRIPT_SHA256",
    "FUNCTION_EXPORTS",
    "JAVASCRIPT_CONSUMER_CONTRACT_HASH",
    "PYTHON_CONSUMER_ADR_SHA256",
    "PYTHON_CONSUMER_CONTRACT_HASH",
    "PYTHON_CONSUMER_IMPLEMENTATION_SHA256",
    "PYTHON_CONSUMER_TEST_SHA256",
    "PYTHON_RESULT_SCHEMA_VERSION",
    "PYTHON_RESULT_STATIC_FINGERPRINT",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_JAVASCRIPT_SHA256",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPythonConsumerResultV1",
  ]);
  assert.deepEqual(
    [
      fixture.known_result,
      fixture.unknown_result,
      fixture.blocked_result,
    ].map(
      (value) =>
        subject.buildPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1(
          value
        ).status
    ),
    ["KNOWN", "UNKNOWN", "BLOCKED"]
  );
});

test("production consumer has no DOM, network, storage, or host-loader API", () => {
  const source = fs.readFileSync(
    path.join(
      __dirname,
      "evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.js"
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
