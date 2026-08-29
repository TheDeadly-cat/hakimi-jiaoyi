"use strict";

const crypto = require("node:crypto");
const fixture = require(
  "./evidence_portfolio_risk_weighted_diversification_consumer_fixture_v4.js"
);

const SCHEMA_VERSION =
  "portfolio-risk-weighted-diversification-fixture-execution-receipt-v2";
const STATIC_FINGERPRINT =
  "20260823-weighted-diversification-fixture-execution-receipt-v2-lock-1";
const VERIFICATION_SCHEMA_VERSION = `${SCHEMA_VERSION}-verification-v1`;
const PROJECTION_IMPLEMENTATION_SHA256 =
  "a41f0a263a9fae6ec67e737ed24fa2d8b9a00a13cc9e868132611b26d9334f94";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const CARD_IMPLEMENTATION_SHA256 =
  "ff7e5868a0d8121f5d2076555a5fff994d1f3d2c2375be6dbf665c080cfa9163";
const FIXTURE_IMPLEMENTATION_SHA256 =
  "fc48c5c20f3d95cc62e4ab639e1edb3c2cc90f6212e9bbf04623e4fa886dc872";
const REGISTRATION_IMPLEMENTATION_SHA256 =
  "c190e3aa49777b1c73a7cf0a12e534ef829003227818cc6412b68b388980f4cc";
const REGISTRATION_CANDIDATE_HASH =
  "628ccc78ede53224901a0a3df307252597d4d25bfadf557d8f248a79f45cf55a";
const REGISTRATION_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v2";
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

function descriptorIsSummaryOnly(value) {
  return isPlainObject(value)
    && isPlainObject(value.facts)
    && value.facts.projection_document_embedded === false
    && value.facts.source_evidence_embedded === false
    && value.facts.positions_embedded === false
    && value.facts.completed_price_rows_embedded === false
    && value.facts.return_series_embedded === false
    && value.facts.correlation_matrices_embedded === false
    && value.facts.profitability_proven === false
    && value.facts.runtime_assets_accessed === false
    && value.facts.runtime_consumer_bound === false
    && value.facts.ui_mounted === false;
}

function buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
  projection,
  observedDescriptor
) {
  let expectedDescriptor = null;
  let descriptorExact = false;
  try {
    expectedDescriptor =
      fixture.buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
        projection
      );
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
    && expectedDescriptor.source.card_contract_available === true
    && expectedDescriptor.source.implementation_hashes_runtime_verified === false
  );
  const summaryOnly = Boolean(
    descriptorExact && descriptorIsSummaryOnly(observedDescriptor)
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
    { name: "sealed_projection_consumed", ok: expectedKnown, blocking: true },
    { name: "fixture_descriptor_exact_rebuild", ok: descriptorExact, blocking: true },
    { name: "fixture_descriptor_summary_only", ok: summaryOnly, blocking: true },
    { name: "fixture_execution_remained_unmounted", ok: unmounted, blocking: true },
    { name: "fixture_authority_not_promoted", ok: locked, blocking: true },
    {
      name: "implementation_identity_not_self_certified",
      ok: Boolean(
        descriptorExact
        && observedDescriptor.source.implementation_hashes_runtime_verified === false
      ),
      blocking: true
    }
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
      ? "LOCAL_NODE_SEALED_FIXTURE_V4_DESCRIPTOR_EXACTLY_REBUILT_UNMOUNTED"
      : "LOCAL_NODE_FIXTURE_V4_EXECUTION_RECEIPT_BLOCKED",
    source: {
      projection_schema_version: passed
        ? projection.schema_version
        : "UNKNOWN",
      projection_hash: passed ? projection.projection_hash : null,
      projection_implementation_sha256: PROJECTION_IMPLEMENTATION_SHA256,
      strict_canonical_implementation_sha256:
        STRICT_CANONICAL_IMPLEMENTATION_SHA256,
      card_implementation_sha256: CARD_IMPLEMENTATION_SHA256,
      fixture_schema_version: fixture.SCHEMA_VERSION,
      fixture_static_fingerprint: fixture.STATIC_FINGERPRINT,
      fixture_implementation_sha256: FIXTURE_IMPLEMENTATION_SHA256,
      registration_schema_version: REGISTRATION_SCHEMA_VERSION,
      registration_implementation_sha256: REGISTRATION_IMPLEMENTATION_SHA256,
      registration_candidate_hash: REGISTRATION_CANDIDATE_HASH,
      execution_environment: "NODE_CONTRACT_PROCESS"
    },
    verification: {
      projection_seal_verified: expectedKnown,
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
      stylesheet_executed: false,
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

function verifyPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
  receipt,
  projection,
  observedDescriptor
) {
  const expected = buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2(
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
    blockers: exact ? [] : ["fixture_v4_execution_receipt_exact_rebuild"],
    browser_visual_review_verified: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false
  };
}

module.exports = Object.freeze({
  CARD_IMPLEMENTATION_SHA256,
  FIXTURE_IMPLEMENTATION_SHA256,
  PROJECTION_IMPLEMENTATION_SHA256,
  REGISTRATION_CANDIDATE_HASH,
  REGISTRATION_IMPLEMENTATION_SHA256,
  REGISTRATION_SCHEMA_VERSION,
  SCHEMA_VERSION,
  STATIC_FINGERPRINT,
  STAGE_ORDER,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  VERIFICATION_SCHEMA_VERSION,
  buildPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2,
  verifyPortfolioRiskWeightedDiversificationFixtureExecutionReceiptV2
});
