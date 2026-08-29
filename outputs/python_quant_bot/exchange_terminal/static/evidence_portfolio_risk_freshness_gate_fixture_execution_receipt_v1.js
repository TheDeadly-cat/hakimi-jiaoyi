"use strict";

const crypto = require("node:crypto");
const fixture = require("./evidence_portfolio_risk_freshness_gate_consumer_fixture_v3.js");

const SCHEMA_VERSION =
  "portfolio-risk-freshness-fixture-execution-receipt-v1";
const STATIC_FINGERPRINT =
  "20260822-portfolio-risk-freshness-fixture-execution-receipt-lock-1";
const VERIFICATION_SCHEMA_VERSION = `${SCHEMA_VERSION}-verification-v1`;
const PROJECTION_IMPLEMENTATION_SHA256 =
  "a983593e70f7dfd707c4933e41422335ccb7825f84c1c689339518e47186f1bf";
const CARD_IMPLEMENTATION_SHA256 =
  "0999f934aafe7bcb193e99bfe36362dbc2a91f2015c7d131ce7fb3b252e36f29";
const FIXTURE_IMPLEMENTATION_SHA256 =
  "6e9c1da54ed9ee6e8d5ba70d1473d920c67b0c0534bb9110cafb604518430b0d";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

function canonicalJson(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string")
    return JSON.stringify(value);
  if (typeof value === "number" && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (isPlainObject(value)) {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  throw new TypeError("unsupported canonical JSON value");
}

function sha256Canonical(value) {
  return crypto.createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}

function authorityLocked(value) {
  if (!isPlainObject(value) || value.descriptive_only !== true) return false;
  return Object.keys(value).filter((key) => key !== "descriptive_only")
    .every((key) => value[key] === false);
}

function buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(
  projection,
  observedDescriptor
) {
  let expectedDescriptor = null;
  let descriptorExact = false;
  try {
    expectedDescriptor =
      fixture.buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection);
    descriptorExact = isPlainObject(observedDescriptor)
      && canonicalJson(observedDescriptor) === canonicalJson(expectedDescriptor);
  } catch (_error) {
    expectedDescriptor = null;
  }

  const expectedKnown = Boolean(
    expectedDescriptor
    && expectedDescriptor.status === "PASS"
    && expectedDescriptor.presentation.contract_state === "KNOWN"
    && expectedDescriptor.source.projection_hash === projection?.projection_hash
  );
  const unmounted = Boolean(
    descriptorExact
    && observedDescriptor.mount.requested === false
    && observedDescriptor.mount.performed === false
    && observedDescriptor.mount.dom_accessed === false
    && observedDescriptor.mount.browser_review_performed === false
    && observedDescriptor.facts.ui_mounted === false
  );
  const locked = Boolean(
    descriptorExact && authorityLocked(observedDescriptor.authority)
  );
  const checks = [
    { name: "known_projection_consumed", ok: expectedKnown, blocking: true },
    { name: "fixture_descriptor_exact_rebuild", ok: descriptorExact, blocking: true },
    { name: "fixture_execution_remained_unmounted", ok: unmounted, blocking: true },
    { name: "fixture_authority_not_promoted", ok: locked, blocking: true }
  ];
  const blockers = checks.filter((check) => check.ok !== true).map((check) => check.name);
  const passed = blockers.length === 0;
  const descriptorHash = isPlainObject(observedDescriptor)
    ? sha256Canonical(observedDescriptor)
    : null;

  const receipt = {
    schema_version: SCHEMA_VERSION,
    static_fingerprint: STATIC_FINGERPRINT,
    status: passed ? "PASS" : "BLOCK",
    decision: passed
      ? "LOCAL_NODE_FIXTURE_DESCRIPTOR_EXACTLY_REBUILT_UNMOUNTED"
      : "LOCAL_NODE_FIXTURE_EXECUTION_RECEIPT_BLOCKED",
    source: {
      projection_schema_version: passed
        ? projection.schema_version
        : "UNKNOWN",
      projection_hash: passed ? projection.projection_hash : null,
      projection_implementation_sha256: PROJECTION_IMPLEMENTATION_SHA256,
      card_implementation_sha256: CARD_IMPLEMENTATION_SHA256,
      fixture_schema_version: fixture.SCHEMA_VERSION,
      fixture_static_fingerprint: fixture.STATIC_FINGERPRINT,
      fixture_implementation_sha256: FIXTURE_IMPLEMENTATION_SHA256,
      execution_environment: "NODE_CONTRACT_PROCESS"
    },
    verification: {
      descriptor_exactly_rebuilt: descriptorExact,
      descriptor_status: expectedDescriptor ? expectedDescriptor.status : "UNKNOWN",
      descriptor_contract_state: expectedDescriptor
        ? expectedDescriptor.presentation.contract_state
        : "UNKNOWN",
      descriptor_sha256: descriptorHash,
      stage_order: STAGE_ORDER.slice()
    },
    checks,
    blockers,
    facts: {
      local_process_execution_observed: true,
      node_process_identity_authenticated: false,
      receipt_signature_verified: false,
      external_execution_authority_verified: false,
      projection_document_embedded: false,
      fixture_descriptor_embedded: false,
      markup_embedded: false,
      dom_accessed: false,
      browser_visual_review_performed: false,
      network_accessed: false,
      runtime_consumer_bound: false,
      profitability_proven: false
    },
    authority: {
      descriptive_only: true,
      current_admission_allowed: false,
      current_pointer_written: false,
      live_order_allowed: false,
      migration_allowed: false,
      paper_authorized: false,
      presentation_consumer_activation_allowed: false,
      presentation_mount_allowed: false,
      runtime_gate_activation_allowed: false,
      shadow_consumer_activation_allowed: false,
      writer_allowed: false
    }
  };
  receipt.receipt_hash = sha256Canonical(receipt);
  return receipt;
}

function verifyPortfolioRiskFreshnessFixtureExecutionReceiptV1(
  receipt,
  projection,
  observedDescriptor
) {
  const expected = buildPortfolioRiskFreshnessFixtureExecutionReceiptV1(
    projection,
    observedDescriptor
  );
  const exact = isPlainObject(receipt)
    && canonicalJson(receipt) === canonicalJson(expected);
  return {
    schema_version: VERIFICATION_SCHEMA_VERSION,
    status: exact ? "PASS" : "BLOCK",
    receipt_exactly_verified: exact,
    receipt_status: exact ? expected.status : "UNKNOWN",
    blockers: exact ? [] : ["fixture_execution_receipt_exact_rebuild"],
    browser_visual_review_verified: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false
  };
}

module.exports = Object.freeze({
  CARD_IMPLEMENTATION_SHA256,
  FIXTURE_IMPLEMENTATION_SHA256,
  PROJECTION_IMPLEMENTATION_SHA256,
  SCHEMA_VERSION,
  STATIC_FINGERPRINT,
  STAGE_ORDER,
  VERIFICATION_SCHEMA_VERSION,
  buildPortfolioRiskFreshnessFixtureExecutionReceiptV1,
  verifyPortfolioRiskFreshnessFixtureExecutionReceiptV1
});
