"use strict";

const strictCanonical = require("./strict_canonical_json_v1.js");
const card = require("./evidence_portfolio_risk_downside_tail_card_v6.js");
const consumer = require(
  "./evidence_portfolio_risk_downside_tail_consumer_fixture_v6.js"
);

const SCHEMA_VERSION =
  "portfolio-risk-downside-tail-consumer-execution-receipt-v4";
const STATIC_FINGERPRINT =
  "20260823-downside-tail-consumer-v6-node-execution-receipt-v4-lock-1";
const VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1";
const PREREGISTRATION_SCHEMA_VERSION =
  "portfolio-risk-downside-tail-consumer-execution-preregistration-v1";
const PREREGISTRATION_STATIC_FINGERPRINT =
  "20260823-downside-tail-consumer-v6-local-node-preregistration-lock-1";
const EXECUTION_PROFILE = "LOCAL_NODE_CONTRACT_PROCESS_UNMOUNTED";
const PROJECTION_IMPLEMENTATION_SHA256 =
  "ec136f1cc713f443581f835116610c0210d0fe2faeb638ee815d93709e1566d6";
const STRICT_CANONICAL_IMPLEMENTATION_SHA256 =
  "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
const CARD_IMPLEMENTATION_SHA256 =
  "a75e6e033872cd1db418488c5ee57814e642c764887c633f74e8e592b08be22d";
const CARD_STYLESHEET_SHA256 =
  "0f7870b549c0cdb671f92cb59b7776c33ac25ca101f2cf25c4420a7ad8268c83";
const CONSUMER_IMPLEMENTATION_SHA256 =
  "e98af5ea40f9e5cf56787cac0af14071b2acd1d2cdd3febc79db230c8c5f3ce7";
const STAGE_ORDER = Object.freeze([
  "SOURCE",
  "GAP",
  "MATURITY",
  "PERMISSION",
]);
const PREREGISTRATION_KEYS = Object.freeze([
  "authority",
  "card_implementation_sha256",
  "card_stylesheet_sha256",
  "consumer_implementation_sha256",
  "execution_profile",
  "preregistration_hash",
  "preregistration_id",
  "projection_implementation_sha256",
  "schema_version",
  "static_fingerprint",
  "strict_canonical_implementation_sha256",
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
  return (
    strictCanonical.isPlainRecord(value) &&
    JSON.stringify(Object.keys(value).sort()) ===
      JSON.stringify(keys.slice().sort())
  );
}

function canonicalEqual(left, right) {
  try {
    return (
      strictCanonical.strictCanonicalStringify(left) ===
      strictCanonical.strictCanonicalStringify(right)
    );
  } catch (_error) {
    return false;
  }
}

function preregistrationAuthority() {
  return {
    descriptive_only: true,
    formal_registration_allowed: false,
    current_admission_allowed: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    writer_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function receiptAuthority() {
  return {
    descriptive_only: true,
    current_admission_allowed: false,
    current_pointer_written: false,
    formal_registration_activation_allowed: false,
    live_order_allowed: false,
    migration_allowed: false,
    paper_authorized: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    runtime_gate_activation_allowed: false,
    shadow_consumer_activation_allowed: false,
    writer_allowed: false,
  };
}

function projectionAuthority() {
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

function descriptorAuthority() {
  return {
    descriptive_only: true,
    writer_allowed: false,
    runtime_gate_activation_allowed: false,
    presentation_consumer_activation_allowed: false,
    presentation_mount_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
  };
}

function validPreregistrationId(value) {
  return (
    typeof value === "string" &&
    /^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$/.test(value)
  );
}

function buildPortfolioRiskDownsideTailExecutionPreregistrationV1(
  preregistrationId
) {
  if (!validPreregistrationId(preregistrationId)) {
    throw new TypeError("preregistration_id is invalid");
  }
  const document = {
    schema_version: PREREGISTRATION_SCHEMA_VERSION,
    static_fingerprint: PREREGISTRATION_STATIC_FINGERPRINT,
    preregistration_id: preregistrationId,
    execution_profile: EXECUTION_PROFILE,
    projection_implementation_sha256: PROJECTION_IMPLEMENTATION_SHA256,
    strict_canonical_implementation_sha256:
      STRICT_CANONICAL_IMPLEMENTATION_SHA256,
    card_implementation_sha256: CARD_IMPLEMENTATION_SHA256,
    card_stylesheet_sha256: CARD_STYLESHEET_SHA256,
    consumer_implementation_sha256: CONSUMER_IMPLEMENTATION_SHA256,
    authority: preregistrationAuthority(),
  };
  return deepFreeze(
    strictCanonical.sealDocument(document, "preregistration_hash")
  );
}

function verifyPortfolioRiskDownsideTailExecutionPreregistrationV1(
  preregistration
) {
  if (
    !hasExactKeys(preregistration, PREREGISTRATION_KEYS) ||
    !isHash(preregistration.preregistration_hash) ||
    !strictCanonical.verifySealedDocument(
      preregistration,
      "preregistration_hash"
    ) ||
    preregistration.schema_version !== PREREGISTRATION_SCHEMA_VERSION ||
    preregistration.static_fingerprint !==
      PREREGISTRATION_STATIC_FINGERPRINT ||
    preregistration.execution_profile !== EXECUTION_PROFILE ||
    preregistration.projection_implementation_sha256 !==
      PROJECTION_IMPLEMENTATION_SHA256 ||
    preregistration.strict_canonical_implementation_sha256 !==
      STRICT_CANONICAL_IMPLEMENTATION_SHA256 ||
    preregistration.card_implementation_sha256 !==
      CARD_IMPLEMENTATION_SHA256 ||
    preregistration.card_stylesheet_sha256 !== CARD_STYLESHEET_SHA256 ||
    preregistration.consumer_implementation_sha256 !==
      CONSUMER_IMPLEMENTATION_SHA256 ||
    !canonicalEqual(preregistration.authority, preregistrationAuthority())
  ) {
    return false;
  }
  try {
    return canonicalEqual(
      preregistration,
      buildPortfolioRiskDownsideTailExecutionPreregistrationV1(
        preregistration.preregistration_id
      )
    );
  } catch (_error) {
    return false;
  }
}

function projectionAuthorityLocked(value) {
  return canonicalEqual(value, projectionAuthority());
}

function descriptorAuthorityLocked(value) {
  return canonicalEqual(value, descriptorAuthority());
}

function stageOrderExact(view) {
  return (
    strictCanonical.isPlainRecord(view) &&
    Array.isArray(view.stages) &&
    JSON.stringify(view.stages.map((stage) => stage.axis)) ===
      JSON.stringify(STAGE_ORDER) &&
    view.stages[3].state === "UNAUTHORIZED"
  );
}

function resealedWrongSchemaRejected(projection, projectionSealVerified) {
  if (!projectionSealVerified) return false;
  try {
    const alias = JSON.parse(JSON.stringify(projection));
    delete alias.projection_hash;
    alias.schema_version =
      "strategy-correlation-cluster-portfolio-risk-projection-v5";
    const resealed = strictCanonical.sealDocument(alias, "projection_hash");
    return (
      strictCanonical.verifySealedDocument(resealed, "projection_hash") &&
      card.verifyPortfolioRiskProjectionSealV6(resealed) === false &&
      card.buildPortfolioRiskDownsideTailViewModelV6(resealed)
        .contract_state === "UNKNOWN"
    );
  } catch (_error) {
    return false;
  }
}

function semanticState(projection, projectionSealVerified, view) {
  if (
    !projectionSealVerified ||
    !strictCanonical.isPlainRecord(projection.local_decision) ||
    !strictCanonical.isPlainRecord(projection.source) ||
    !strictCanonical.isPlainRecord(view)
  ) {
    return {
      source_state: "UNKNOWN",
      local_status: "UNKNOWN",
      tail_decision: "UNKNOWN",
      tone: "unknown",
      preserved: false,
    };
  }
  const sourceState = projection.source.state;
  const localStatus = projection.local_decision.status;
  const tailDecision =
    projection.local_decision.downside_tail_gate_decision;
  let expectedTone = null;
  let expectedLabel = null;
  if (sourceState === "UNKNOWN" && localStatus === "UNKNOWN") {
    expectedTone = "unknown";
    expectedLabel = "SOURCE UNKNOWN";
  } else if (sourceState === "OBSERVED" && tailDecision === "BLOCK") {
    expectedTone = "critical";
    expectedLabel = "TAIL COUPLING BLOCK";
  } else if (sourceState === "OBSERVED" && localStatus === "BLOCK") {
    expectedTone = "gap";
    expectedLabel = "LOCAL GATE BLOCK";
  } else if (sourceState === "OBSERVED" && localStatus === "PASS") {
    expectedTone = "bounded";
    expectedLabel = "LOCAL CHECKS CLEAR";
  }
  return {
    source_state: sourceState,
    local_status: localStatus,
    tail_decision: tailDecision,
    tone: expectedTone || "unknown",
    preserved: Boolean(
      expectedTone &&
        view.contract_state === "KNOWN_BLOCKED" &&
        view.source_state === sourceState &&
        view.tone === expectedTone &&
        view.status_label === expectedLabel &&
        view.tail_risk.decision === tailDecision
    ),
  };
}

function descriptorUnmounted(value) {
  return Boolean(
    strictCanonical.isPlainRecord(value) &&
      strictCanonical.isPlainRecord(value.mount) &&
      strictCanonical.isPlainRecord(value.facts) &&
      value.mount.mode === "UNMOUNTED" &&
      value.mount.mount_api_exposed === false &&
      value.mount.browser_executed === false &&
      value.facts.dom_accessed === false &&
      value.facts.browser_visual_review_performed === false &&
      value.facts.ui_mounted === false
  );
}

function buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
  projection,
  executionPreregistration
) {
  const nodeProcessObserved = Boolean(
    typeof process === "object" &&
      process &&
      process.versions &&
      typeof process.versions.node === "string" &&
      process.versions.node.length > 0
  );
  const preregistrationExact =
    verifyPortfolioRiskDownsideTailExecutionPreregistrationV1(
      executionPreregistration
    );
  let projectionSealVerified = false;
  let view = null;
  let descriptor = null;
  let descriptorExact = false;
  try {
    projectionSealVerified =
      card.verifyPortfolioRiskProjectionSealV6(projection);
    view = card.buildPortfolioRiskDownsideTailViewModelV6(projection);
    descriptor =
      consumer.buildPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
        projection
      );
    descriptorExact =
      consumer.verifyPortfolioRiskDownsideTailPresentationConsumerFixtureV6(
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
  const semantics = semanticState(
    projection,
    projectionSealVerified,
    view
  );
  const viewKnown = Boolean(
    projectionSealVerified &&
      strictCanonical.isPlainRecord(view) &&
      view.contract_state === "KNOWN_BLOCKED" &&
      stageOrderExact(view)
  );
  const unmounted = Boolean(
    descriptorExact && descriptorUnmounted(descriptor)
  );
  const authorityLocked = Boolean(
    projectionSealVerified &&
      projectionAuthorityLocked(projection.authority) &&
      descriptorExact &&
      descriptorAuthorityLocked(descriptor.authority)
  );
  const stylesheetDeclared = Boolean(
    descriptorExact &&
      strictCanonical.isPlainRecord(descriptor.presentation) &&
      descriptor.presentation.stylesheet_asset === consumer.STYLESHEET_ASSET
  );
  const descriptorHash =
    descriptorExact && isHash(descriptor.descriptor_hash)
      ? descriptor.descriptor_hash
      : null;
  const checks = [
    {
      name: "node_contract_process_observed",
      ok: nodeProcessObserved,
      blocking: true,
    },
    {
      name: "execution_preregistration_v1_exact",
      ok: preregistrationExact,
      blocking: true,
    },
    {
      name: "projection_v6_seal_verified",
      ok: projectionSealVerified,
      blocking: true,
    },
    {
      name: "projection_v5_schema_alias_rejected",
      ok: schemaAliasRejected,
      blocking: true,
    },
    {
      name: "card_v6_view_model_built",
      ok: viewKnown,
      blocking: true,
    },
    {
      name: "consumer_v6_descriptor_exact_rebuild",
      ok: descriptorExact && descriptorHash !== null,
      blocking: true,
    },
    {
      name: "source_tail_and_local_state_preserved",
      ok: semantics.preserved,
      blocking: true,
    },
    {
      name: "consumer_v6_remained_unmounted",
      ok: unmounted,
      blocking: true,
    },
    {
      name: "projection_and_descriptor_authority_locked",
      ok: authorityLocked,
      blocking: true,
    },
    {
      name: "stylesheet_declared_but_not_executed",
      ok: stylesheetDeclared,
      blocking: true,
    },
    {
      name: "formal_registration_not_claimed",
      ok: true,
      blocking: true,
    },
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
      ? "LOCAL_NODE_DOWNSIDE_TAIL_CONSUMER_V6_EXECUTED_EXACTLY_UNMOUNTED_AUTHORITY_UNCHANGED"
      : "LOCAL_NODE_DOWNSIDE_TAIL_CONSUMER_V6_EXECUTION_RECEIPT_BLOCKED",
    source: {
      projection_schema_version: projectionSealVerified
        ? projection.schema_version
        : "UNKNOWN",
      projection_static_fingerprint: projectionSealVerified
        ? projection.static_fingerprint
        : "UNKNOWN",
      projection_hash: projectionSealVerified
        ? projection.projection_hash
        : null,
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
      execution_preregistration_schema_version:
        PREREGISTRATION_SCHEMA_VERSION,
      execution_preregistration_static_fingerprint:
        PREREGISTRATION_STATIC_FINGERPRINT,
      execution_preregistration_hash: preregistrationExact
        ? executionPreregistration.preregistration_hash
        : null,
      formal_registration_schema_version: null,
      formal_registration_hash: null,
      execution_environment: "NODE_CONTRACT_PROCESS",
    },
    verification: {
      node_process_observed: nodeProcessObserved,
      execution_preregistration_exact: preregistrationExact,
      projection_seal_verified: projectionSealVerified,
      projection_schema_alias_rejected: schemaAliasRejected,
      view_contract_state: viewKnown ? view.contract_state : "UNKNOWN",
      view_source_state: viewKnown ? view.source_state : "UNKNOWN",
      view_tone: viewKnown ? view.tone : "unknown",
      view_status_label: viewKnown ? view.status_label : "UNKNOWN",
      local_status: semantics.local_status,
      downside_tail_gate_decision: semantics.tail_decision,
      source_tail_and_local_state_preserved: semantics.preserved,
      descriptor_exactly_rebuilt: descriptorExact,
      descriptor_status: descriptorExact ? descriptor.status : "UNKNOWN",
      descriptor_decision: descriptorExact
        ? descriptor.decision
        : "UNKNOWN",
      descriptor_hash: descriptorHash,
      formal_registration_bound: false,
      stage_order: STAGE_ORDER.slice(),
    },
    checks,
    blockers,
    facts: {
      local_process_execution_observed: nodeProcessObserved,
      node_process_identity_authenticated: false,
      receipt_signature_verified: false,
      external_execution_authority_verified: false,
      execution_preregistration_bound: preregistrationExact,
      formal_registration_bound: false,
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
      profitability_proven: false,
    },
    authority: receiptAuthority(),
  };
  return deepFreeze(strictCanonical.sealDocument(receipt, "receipt_hash"));
}

function verifyPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
  receipt,
  projection,
  executionPreregistration
) {
  let expected = null;
  let sealed = false;
  try {
    expected = buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(
      projection,
      executionPreregistration
    );
    sealed = strictCanonical.verifySealedDocument(receipt, "receipt_hash");
  } catch (_error) {
    expected = null;
    sealed = false;
  }
  const exact = Boolean(
    expected &&
      sealed &&
      strictCanonical.isPlainRecord(receipt) &&
      canonicalEqual(receipt, expected)
  );
  return deepFreeze(
    strictCanonical.sealDocument(
      {
        schema_version: VERIFICATION_SCHEMA_VERSION,
        status: exact ? "PASS" : "BLOCK",
        receipt_seal_verified: sealed,
        receipt_exactly_rebuilt: exact,
        receipt_status: exact ? expected.status : "UNKNOWN",
        receipt_hash: exact ? expected.receipt_hash : null,
        blockers: exact
          ? []
          : ["consumer_v6_execution_receipt_exact_rebuild"],
        browser_visual_review_verified: false,
        formal_registration_verified: false,
        current_admission_allowed: false,
        live_order_allowed: false,
        paper_authorized: false,
        presentation_consumer_activation_allowed: false,
        presentation_mount_allowed: false,
        runtime_gate_activation_allowed: false,
        writer_allowed: false,
      },
      "verification_hash"
    )
  );
}

module.exports = Object.freeze({
  CARD_IMPLEMENTATION_SHA256,
  CARD_STYLESHEET_SHA256,
  CONSUMER_IMPLEMENTATION_SHA256,
  EXECUTION_PROFILE,
  PREREGISTRATION_SCHEMA_VERSION,
  PREREGISTRATION_STATIC_FINGERPRINT,
  PROJECTION_IMPLEMENTATION_SHA256,
  SCHEMA_VERSION,
  STATIC_FINGERPRINT,
  STAGE_ORDER,
  STRICT_CANONICAL_IMPLEMENTATION_SHA256,
  VERIFICATION_SCHEMA_VERSION,
  buildPortfolioRiskDownsideTailExecutionPreregistrationV1,
  verifyPortfolioRiskDownsideTailExecutionPreregistrationV1,
  buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4,
  verifyPortfolioRiskDownsideTailConsumerExecutionReceiptV4,
});
