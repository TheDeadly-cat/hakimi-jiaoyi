"use strict";

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_joint_evidence_card_v5.js");
const consumer = require(
  "./evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js"
);

const SCHEMA_VERSION =
  "portfolio-risk-joint-evidence-consumer-execution-receipt-v3";
const STATIC_FINGERPRINT =
  "20260823-joint-evidence-consumer-v5-node-execution-receipt-v3-lock-1";
const VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1";
const PROJECTION_IMPLEMENTATION_SHA256 =
  "eadaec98c0b2882b28a6523779a02171afd39e7f5ed0caf0d581bfd81ee983c1";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const CARD_IMPLEMENTATION_SHA256 =
  "8282b85316a2d238202d2a553af775f98be9f829ad86a49ab0463654bb9c358d";
const CARD_STYLESHEET_SHA256 =
  "90ea35644b6d7fdc33f0bb1b1025ab37d6a876d10be00ec81e9b7a257552ed1a";
const CONSUMER_IMPLEMENTATION_SHA256 =
  "401a16ab303eec51e4a5d65f51e6ca4250f3bb1c281b8b07adb193ec89de8849";
const REGISTRATION_IMPLEMENTATION_SHA256 =
  "b7b0b8faf64d34796b6ae97e6594ea08a0fcd930272fa4841e4a7bd0ebecd897";
const REGISTRATION_SCHEMA_VERSION =
  "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v4";
const REGISTRATION_STATIC_FINGERPRINT =
  "20260823-joint-evidence-frontend-registration-v4-lock-1";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
const REGISTRATION_BINDING_KEYS = Object.freeze([
  "implementation_sha256",
  "registration_hash",
  "schema_version",
  "static_fingerprint"
]);
const DESCRIPTOR_AUTHORITY_KEYS = Object.freeze([
  "current_admission_allowed",
  "descriptive_only",
  "live_order_allowed",
  "paper_authorized",
  "presentation_consumer_activation_allowed",
  "presentation_mount_allowed",
  "runtime_gate_activation_allowed",
  "writer_allowed"
]);

function deepFreeze(value) {
  if (value !== null && typeof value === "object") {
    for (const nested of Object.values(value)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

function isHash(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function hasExactKeys(value, keys) {
  return strictCanonical.isPlainRecord(value)
    && JSON.stringify(Object.keys(value).sort()) === JSON.stringify(keys);
}

function canonicalEqual(left, right) {
  try {
    return strictCanonical.strictCanonicalStringify(left)
      === strictCanonical.strictCanonicalStringify(right);
  } catch (_error) {
    return false;
  }
}

function registrationBindingExact(value) {
  return hasExactKeys(value, REGISTRATION_BINDING_KEYS)
    && value.schema_version === REGISTRATION_SCHEMA_VERSION
    && value.static_fingerprint === REGISTRATION_STATIC_FINGERPRINT
    && value.implementation_sha256 === REGISTRATION_IMPLEMENTATION_SHA256
    && isHash(value.registration_hash);
}

function projectionAuthorityLocked(value) {
  if (!strictCanonical.isPlainRecord(value)) return false;
  if (value.research_only !== true || value.presentation_only !== true) return false;
  const permissionEntries = Object.entries(value).filter(
    ([key]) => key !== "research_only" && key !== "presentation_only"
  );
  return permissionEntries.length >= 8
    && permissionEntries.every(([, permission]) => permission === false);
}

function descriptorAuthorityLocked(value) {
  if (
    !hasExactKeys(value, DESCRIPTOR_AUTHORITY_KEYS)
    || value.descriptive_only !== true
  ) {
    return false;
  }
  const permissionEntries = Object.entries(value).filter(
    ([key]) => key !== "descriptive_only"
  );
  return permissionEntries.every(([, permission]) => permission === false);
}

function stageOrderExact(view) {
  return strictCanonical.isPlainRecord(view)
    && Array.isArray(view.stages)
    && JSON.stringify(view.stages.map((stage) => stage.key))
      === JSON.stringify(STAGE_ORDER)
    && view.stages[3].state === "UNAUTHORIZED";
}

function resealedWrongSchemaRejected(projection, projectionSealVerified) {
  if (!projectionSealVerified) return false;
  try {
    const alias = JSON.parse(JSON.stringify(projection));
    delete alias.projection_hash;
    alias.schema_version = "strategy-correlation-cluster-portfolio-risk-projection-v4";
    const resealed = strictCanonical.sealDocument(alias, "projection_hash");
    return strictCanonical.verifySealedDocument(resealed, "projection_hash")
      && card.verifyPortfolioRiskProjectionSealV5(resealed) === false;
  } catch (_error) {
    return false;
  }
}

function localGateState(projection, projectionSealVerified, view) {
  const localDecision = projectionSealVerified
    && strictCanonical.isPlainRecord(projection.local_decision)
      ? projection.local_decision
      : null;
  const status = localDecision
    && (localDecision.status === "PASS" || localDecision.status === "BLOCK")
      ? localDecision.status
      : "UNKNOWN";
  const passed = status === "PASS" ? true : status === "BLOCK" ? false : null;
  const expectedLabel = status === "PASS"
    ? "LOCAL GATE PASS"
    : status === "BLOCK"
      ? "LOCAL GATE BLOCK"
      : null;
  return {
    status,
    passed,
    preserved: Boolean(
      localDecision
      && expectedLabel
      && localDecision.joint_risk_gate_passed === passed
      && strictCanonical.isPlainRecord(view)
      && view.status_label === expectedLabel
    )
  };
}

function descriptorUnmounted(value) {
  return strictCanonical.isPlainRecord(value)
    && strictCanonical.isPlainRecord(value.mount)
    && strictCanonical.isPlainRecord(value.facts)
    && value.mount.mode === "UNMOUNTED"
    && value.mount.mount_api_exposed === false
    && value.mount.browser_executed === false
    && value.facts.dom_accessed === false
    && value.facts.browser_visual_review_performed === false
    && value.facts.ui_mounted === false;
}

function buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
  projection,
  registrationBinding
) {
  const nodeProcessObserved = Boolean(
    typeof process === "object"
    && process
    && process.versions
    && typeof process.versions.node === "string"
    && process.versions.node.length > 0
  );
  const registrationExact = registrationBindingExact(registrationBinding);
  let projectionSealVerified = false;
  let view = null;
  let descriptor = null;
  let descriptorExact = false;

  try {
    projectionSealVerified = card.verifyPortfolioRiskProjectionSealV5(projection);
    view = card.buildPortfolioRiskJointEvidenceViewModelV5(projection);
    descriptor =
      consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
        projection
      );
    descriptorExact =
      consumer.verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
        descriptor,
        projection
      );
  } catch (_error) {
    projectionSealVerified = false;
    view = null;
    descriptor = null;
    descriptorExact = false;
  }

  const schemaAliasRejected = resealedWrongSchemaRejected(
    projection,
    projectionSealVerified
  );
  const localGate = localGateState(projection, projectionSealVerified, view);
  const viewKnown = Boolean(
    projectionSealVerified
    && strictCanonical.isPlainRecord(view)
    && view.contract_state === "KNOWN_BLOCKED"
    && stageOrderExact(view)
  );
  const unmounted = Boolean(descriptorExact && descriptorUnmounted(descriptor));
  const authorityLocked = Boolean(
    projectionSealVerified
    && projectionAuthorityLocked(projection.authority)
    && descriptorExact
    && descriptorAuthorityLocked(descriptor.authority)
  );
  const stylesheetDeclared = Boolean(
    descriptorExact
    && strictCanonical.isPlainRecord(descriptor.presentation)
    && descriptor.presentation.stylesheet_asset === consumer.STYLESHEET_ASSET
  );
  const descriptorHash = descriptorExact && isHash(descriptor.descriptor_hash)
    ? descriptor.descriptor_hash
    : null;

  const checks = [
    {
      name: "node_contract_process_observed",
      ok: nodeProcessObserved,
      blocking: true
    },
    {
      name: "registration_v4_binding_exact",
      ok: registrationExact,
      blocking: true
    },
    {
      name: "projection_v5_seal_verified",
      ok: projectionSealVerified,
      blocking: true
    },
    {
      name: "projection_schema_alias_rejected",
      ok: schemaAliasRejected,
      blocking: true
    },
    {
      name: "card_v5_view_model_built",
      ok: viewKnown,
      blocking: true
    },
    {
      name: "consumer_v5_descriptor_exact_rebuild",
      ok: descriptorExact && descriptorHash !== null,
      blocking: true
    },
    {
      name: "local_joint_gate_state_preserved",
      ok: localGate.preserved,
      blocking: true
    },
    {
      name: "consumer_v5_remained_unmounted",
      ok: unmounted,
      blocking: true
    },
    {
      name: "projection_and_descriptor_authority_locked",
      ok: authorityLocked,
      blocking: true
    },
    {
      name: "stylesheet_declared_but_not_executed",
      ok: stylesheetDeclared,
      blocking: true
    }
  ];
  const blockers = checks
    .filter((check) => check.ok !== true)
    .map((check) => check.name);
  const passed = blockers.length === 0;

  const receipt = {
    schema_version: SCHEMA_VERSION,
    static_fingerprint: STATIC_FINGERPRINT,
    status: passed ? "PASS" : "BLOCK",
    decision: passed
      ? "LOCAL_NODE_CONSUMER_V5_EXECUTED_EXACTLY_UNMOUNTED_AUTHORITY_UNCHANGED"
      : "LOCAL_NODE_CONSUMER_V5_EXECUTION_RECEIPT_BLOCKED",
    source: {
      projection_schema_version: projectionSealVerified
        ? projection.schema_version
        : "UNKNOWN",
      projection_static_fingerprint: projectionSealVerified
        ? projection.static_fingerprint
        : "UNKNOWN",
      projection_hash: projectionSealVerified ? projection.projection_hash : null,
      projection_implementation_sha256: PROJECTION_IMPLEMENTATION_SHA256,
      strict_canonical_implementation_sha256:
        STRICT_CANONICAL_IMPLEMENTATION_SHA256,
      card_schema_version: card.CARD_SCHEMA_VERSION,
      card_static_fingerprint: card.CARD_STATIC_FINGERPRINT,
      card_implementation_sha256: CARD_IMPLEMENTATION_SHA256,
      card_stylesheet_asset: consumer.STYLESHEET_ASSET,
      card_stylesheet_sha256: CARD_STYLESHEET_SHA256,
      consumer_schema_version: consumer.SCHEMA_VERSION,
      consumer_static_fingerprint: consumer.STATIC_FINGERPRINT,
      consumer_implementation_sha256: CONSUMER_IMPLEMENTATION_SHA256,
      registration_schema_version: REGISTRATION_SCHEMA_VERSION,
      registration_static_fingerprint: REGISTRATION_STATIC_FINGERPRINT,
      registration_implementation_sha256: REGISTRATION_IMPLEMENTATION_SHA256,
      registration_hash: registrationExact
        ? registrationBinding.registration_hash
        : null,
      execution_environment: "NODE_CONTRACT_PROCESS"
    },
    verification: {
      node_process_observed: nodeProcessObserved,
      registration_binding_exact: registrationExact,
      projection_seal_verified: projectionSealVerified,
      projection_schema_alias_rejected: schemaAliasRejected,
      view_contract_state: viewKnown ? view.contract_state : "UNKNOWN",
      view_status_label: viewKnown ? view.status_label : "UNKNOWN",
      local_joint_gate_status: localGate.status,
      local_joint_gate_passed: localGate.passed,
      local_joint_gate_state_preserved: localGate.preserved,
      descriptor_exactly_rebuilt: descriptorExact,
      descriptor_status: descriptorExact ? descriptor.status : "UNKNOWN",
      descriptor_decision: descriptorExact ? descriptor.decision : "UNKNOWN",
      descriptor_sha256: descriptorHash,
      stage_order: STAGE_ORDER.slice()
    },
    checks,
    blockers,
    facts: {
      local_process_execution_observed: nodeProcessObserved,
      node_process_identity_authenticated: false,
      receipt_signature_verified: false,
      external_execution_authority_verified: false,
      projection_document_embedded: false,
      consumer_descriptor_embedded: false,
      source_evidence_embedded: false,
      markup_embedded: false,
      stylesheet_declared: stylesheetDeclared,
      stylesheet_executed: false,
      dom_accessed: false,
      browser_visual_review_performed: false,
      network_accessed: false,
      runtime_assets_accessed: false,
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
  return deepFreeze(strictCanonical.sealDocument(receipt, "receipt_hash"));
}

function verifyPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
  receipt,
  projection,
  registrationBinding
) {
  let expected = null;
  let sealed = false;
  try {
    expected = buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
      projection,
      registrationBinding
    );
    sealed = strictCanonical.verifySealedDocument(receipt, "receipt_hash");
  } catch (_error) {
    expected = null;
    sealed = false;
  }
  const exact = Boolean(
    expected
    && sealed
    && strictCanonical.isPlainRecord(receipt)
    && canonicalEqual(receipt, expected)
  );
  return deepFreeze({
    schema_version: VERIFICATION_SCHEMA_VERSION,
    status: exact ? "PASS" : "BLOCK",
    receipt_seal_verified: sealed,
    receipt_exactly_rebuilt: exact,
    receipt_status: exact ? expected.status : "UNKNOWN",
    receipt_hash: exact ? expected.receipt_hash : null,
    blockers: exact
      ? []
      : ["consumer_v5_execution_receipt_exact_rebuild"],
    browser_visual_review_verified: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false
  });
}

module.exports = Object.freeze({
  CARD_IMPLEMENTATION_SHA256,
  CARD_STYLESHEET_SHA256,
  CONSUMER_IMPLEMENTATION_SHA256,
  PROJECTION_IMPLEMENTATION_SHA256,
  REGISTRATION_IMPLEMENTATION_SHA256,
  REGISTRATION_SCHEMA_VERSION,
  REGISTRATION_STATIC_FINGERPRINT,
  SCHEMA_VERSION,
  STATIC_FINGERPRINT,
  STAGE_ORDER,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  VERIFICATION_SCHEMA_VERSION,
  buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3,
  verifyPortfolioRiskJointEvidenceConsumerExecutionReceiptV3
});
