"use strict";

const strictCanonical = require("./strict_canonical_json_v1.js");
const consumer = require(
  "./evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js"
);

const SCHEMA_VERSION =
  "portfolio-risk-joint-evidence-descriptor-load-order-static-review-v1";
const STATIC_FINGERPRINT =
  "20260823-descriptor-css-load-order-static-review-v1-lock-1";
const VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1";
const EXPECTED_ASSET_MANIFEST = Object.freeze({
  strict_canonical_json_v1_js:
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39",
  joint_evidence_card_v5_js:
    "8282b85316a2d238202d2a553af775f98be9f829ad86a49ab0463654bb9c358d",
  joint_evidence_card_v5_css:
    "90ea35644b6d7fdc33f0bb1b1025ab37d6a876d10be00ec81e9b7a257552ed1a",
  joint_evidence_consumer_v5_js:
    "401a16ab303eec51e4a5d65f51e6ca4250f3bb1c281b8b07adb193ec89de8849",
  consumer_execution_receipt_v3_js:
    "9a90650656f63cd8026fcee224ed4e3d690ced6a7d8bd2970772c653e55c2acb",
  execution_witness_signature_candidate_v1_js:
    "8d085ae6528d16f50888b167b7ed3c913a5eed12977f80290c02bc07c55e7156"
});
const EXPECTED_JAVASCRIPT_LOAD_ORDER = Object.freeze([
  "strict_canonical_json_v1.js",
  "evidence_portfolio_risk_joint_evidence_card_v5.js",
  "evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js",
  "evidence_portfolio_risk_joint_evidence_consumer_execution_receipt_v3.js",
  "evidence_portfolio_risk_joint_evidence_execution_witness_signature_candidate_v1.js"
]);
const EXPECTED_STYLESHEET_LOAD_ORDER = Object.freeze([
  "evidence_portfolio_risk_joint_evidence_card_v5.css"
]);
const AUTHORITY = Object.freeze({
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
});
const DESCRIPTOR_AUTHORITY = Object.freeze({
  descriptive_only: true,
  writer_allowed: false,
  runtime_gate_activation_allowed: false,
  presentation_consumer_activation_allowed: false,
  presentation_mount_allowed: false,
  current_admission_allowed: false,
  paper_authorized: false,
  live_order_allowed: false
});

function deepFreeze(value) {
  if (value !== null && typeof value === "object") {
    for (const nested of Object.values(value)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

function canonicalEqual(left, right) {
  try {
    return strictCanonical.strictCanonicalStringify(left)
      === strictCanonical.strictCanonicalStringify(right);
  } catch (_error) {
    return false;
  }
}

function authorityLocked(value) {
  return strictCanonical.isPlainRecord(value)
    && canonicalEqual(value, AUTHORITY);
}

function stylesheetReview(stylesheetText) {
  const source = typeof stylesheetText === "string" ? stylesheetText : "";
  const globalSelector = /(^|\})\s*(html|body)\s*\{/im;
  const promotion = new RegExp("\\b" + "R" + "EADY" + "\\b", "i");
  return {
    sourceSupplied: typeof stylesheetText === "string",
    hashExact: Boolean(
      source
      && strictCanonical.sha256Hex(source)
        === EXPECTED_ASSET_MANIFEST.joint_evidence_card_v5_css
    ),
    rootScoped: source.includes(".hakimi-joint-risk-card-v5"),
    responsive: source.includes("@media (max-width: 760px)"),
    reducedMotion: source.includes("prefers-reduced-motion"),
    globalScopeAbsent: !globalSelector.test(source),
    purpleBiasAbsent: !/purple/i.test(source),
    promotionClaimAbsent: !promotion.test(source)
  };
}

function markupStaticSafe(markup) {
  return typeof markup === "string"
    && markup.includes("hakimi-joint-risk-card-v5")
    && !/<\s*(script|iframe|object|embed|style)\b/i.test(markup)
    && !/\son[a-z]+\s*=/i.test(markup)
    && !/javascript\s*:/i.test(markup);
}

function descriptorUnmounted(value) {
  return strictCanonical.isPlainRecord(value)
    && strictCanonical.isPlainRecord(value.mount)
    && strictCanonical.isPlainRecord(value.facts)
    && value.status === "BLOCK"
    && value.mount.mode === "UNMOUNTED"
    && value.mount.mount_api_exposed === false
    && value.mount.browser_executed === false
    && value.facts.dom_accessed === false
    && value.facts.browser_visual_review_performed === false
    && value.facts.ui_mounted === false
    && canonicalEqual(value.authority, DESCRIPTOR_AUTHORITY);
}

function stageOrderExact(value) {
  return strictCanonical.isPlainRecord(value)
    && strictCanonical.isPlainRecord(value.presentation)
    && strictCanonical.isPlainRecord(value.presentation.view_model)
    && Array.isArray(value.presentation.view_model.stages)
    && canonicalEqual(
      value.presentation.view_model.stages.map((stage) => stage.key),
      ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
    )
    && value.presentation.view_model.stages[3].state === "UNAUTHORIZED";
}

function buildPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
  projection,
  observedDescriptor,
  stylesheetText,
  assetManifest,
  observedJavascriptLoadOrder,
  observedStylesheetLoadOrder
) {
  let descriptorExact = false;
  let expectedDescriptor = null;
  try {
    expectedDescriptor =
      consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
        projection
      );
    descriptorExact =
      consumer.verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
        observedDescriptor,
        projection
      )
      && canonicalEqual(observedDescriptor, expectedDescriptor);
  } catch (_error) {
    descriptorExact = false;
    expectedDescriptor = null;
  }
  const stylesheet = stylesheetReview(stylesheetText);
  const projectionAccepted = Boolean(
    descriptorExact
    && strictCanonical.isPlainRecord(observedDescriptor.facts)
    && observedDescriptor.facts.projection_v5_accepted === true
  );
  const manifestExact = canonicalEqual(
    assetManifest,
    EXPECTED_ASSET_MANIFEST
  );
  const javascriptOrderExact = canonicalEqual(
    observedJavascriptLoadOrder,
    EXPECTED_JAVASCRIPT_LOAD_ORDER
  );
  const stylesheetOrderExact = canonicalEqual(
    observedStylesheetLoadOrder,
    EXPECTED_STYLESHEET_LOAD_ORDER
  );
  const unmounted = Boolean(
    projectionAccepted && descriptorUnmounted(observedDescriptor)
  );
  const stagesExact = Boolean(
    descriptorExact && stageOrderExact(observedDescriptor)
  );
  const markupSafe = Boolean(
    descriptorExact
    && strictCanonical.isPlainRecord(observedDescriptor.presentation)
    && markupStaticSafe(observedDescriptor.presentation.markup)
  );
  const stylesheetAssetExact = Boolean(
    descriptorExact
    && observedDescriptor.presentation.stylesheet_asset
      === consumer.STYLESHEET_ASSET
  );
  const checks = [
    {
      name: "consumer_v5_descriptor_exact_rebuild",
      ok: descriptorExact,
      blocking: true
    },
    {
      name: "projection_v5_accepted_by_consumer",
      ok: projectionAccepted,
      blocking: true
    },
    {
      name: "descriptor_remains_unmounted_and_authority_locked",
      ok: unmounted,
      blocking: true
    },
    {
      name: "neutral_stage_order_exact",
      ok: stagesExact,
      blocking: true
    },
    {
      name: "descriptor_markup_static_safe",
      ok: markupSafe,
      blocking: true
    },
    {
      name: "descriptor_stylesheet_asset_exact",
      ok: stylesheetAssetExact,
      blocking: true
    },
    {
      name: "six_asset_manifest_exact",
      ok: manifestExact,
      blocking: true
    },
    {
      name: "javascript_dependency_load_order_exact",
      ok: javascriptOrderExact,
      blocking: true
    },
    {
      name: "stylesheet_load_order_exact",
      ok: stylesheetOrderExact,
      blocking: true
    },
    {
      name: "stylesheet_content_sha256_exact",
      ok: stylesheet.hashExact,
      blocking: true
    },
    {
      name: "stylesheet_root_scope_present",
      ok: stylesheet.rootScoped,
      blocking: true
    },
    {
      name: "stylesheet_responsive_contract_present",
      ok: stylesheet.responsive,
      blocking: true
    },
    {
      name: "stylesheet_reduced_motion_contract_present",
      ok: stylesheet.reducedMotion,
      blocking: true
    },
    {
      name: "stylesheet_global_scope_absent",
      ok: stylesheet.globalScopeAbsent,
      blocking: true
    },
    {
      name: "stylesheet_neutral_claim_surface",
      ok: stylesheet.purpleBiasAbsent && stylesheet.promotionClaimAbsent,
      blocking: true
    }
  ];
  const blockers = checks
    .filter((check) => check.ok !== true)
    .map((check) => check.name);
  const passed = blockers.length === 0;
  const review = {
    schema_version: SCHEMA_VERSION,
    static_fingerprint: STATIC_FINGERPRINT,
    status: passed ? "PASS" : "BLOCK",
    decision: passed
      ? "STATIC_DESCRIPTOR_CSS_LOAD_ORDER_REVIEWED_UNMOUNTED_BROWSER_UNVERIFIED"
      : "STATIC_DESCRIPTOR_LOAD_ORDER_REVIEW_BLOCKED",
    source: {
      projection_schema_version: descriptorExact
        && projectionAccepted
        ? projection.schema_version
        : "UNKNOWN",
      projection_hash: descriptorExact && projectionAccepted
        ? projection.projection_hash
        : null,
      descriptor_schema_version: descriptorExact
        ? observedDescriptor.schema_version
        : "UNKNOWN",
      descriptor_hash: descriptorExact
        ? observedDescriptor.descriptor_hash
        : null,
      stylesheet_asset: stylesheetAssetExact
        ? consumer.STYLESHEET_ASSET
        : "UNKNOWN",
      stylesheet_sha256: stylesheet.hashExact
        ? EXPECTED_ASSET_MANIFEST.joint_evidence_card_v5_css
        : null,
      expected_asset_manifest_sha256: strictCanonical.strictCanonicalHash(
        EXPECTED_ASSET_MANIFEST
      ),
      asset_manifest_embedded: false,
      descriptor_embedded: false,
      stylesheet_source_embedded: false
    },
    verification: {
      descriptor_exactly_rebuilt: descriptorExact,
      projection_v5_accepted: projectionAccepted,
      descriptor_status: expectedDescriptor
        ? expectedDescriptor.status
        : "UNKNOWN",
      javascript_load_order: javascriptOrderExact
        ? EXPECTED_JAVASCRIPT_LOAD_ORDER.slice()
        : [],
      stylesheet_load_order: stylesheetOrderExact
        ? EXPECTED_STYLESHEET_LOAD_ORDER.slice()
        : [],
      stylesheet_content_sha256_verified: stylesheet.hashExact,
      stage_order: ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
    },
    checks,
    blockers,
    facts: {
      static_descriptor_review_performed:
        projectionAccepted && descriptorExact && markupSafe,
      static_dependency_load_order_reviewed: javascriptOrderExact,
      static_stylesheet_source_reviewed: stylesheet.hashExact,
      implementation_manifest_exact: manifestExact,
      implementation_hashes_runtime_verified: false,
      source_files_read_by_production_module: false,
      javascript_assets_executed_by_review: false,
      stylesheet_executed: false,
      dom_contract_reviewed: false,
      dom_accessed: false,
      browser_visual_review_performed: false,
      server_route_registered: false,
      runtime_consumer_bound: false,
      ui_mounted: false,
      profitability_proven: false
    },
    authority: { ...AUTHORITY }
  };
  return deepFreeze(strictCanonical.sealDocument(review, "review_hash"));
}

function verifyPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
  document,
  projection,
  observedDescriptor,
  stylesheetText,
  assetManifest,
  observedJavascriptLoadOrder,
  observedStylesheetLoadOrder
) {
  const expected = buildPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
    projection,
    observedDescriptor,
    stylesheetText,
    assetManifest,
    observedJavascriptLoadOrder,
    observedStylesheetLoadOrder
  );
  let sealed = false;
  try {
    sealed = strictCanonical.verifySealedDocument(document, "review_hash");
  } catch (_error) {
    sealed = false;
  }
  const exact = sealed && canonicalEqual(document, expected);
  return deepFreeze({
    schema_version: VERIFICATION_SCHEMA_VERSION,
    status: exact ? "PASS" : "BLOCK",
    review_seal_verified: sealed,
    review_exactly_rebuilt: exact,
    review_status: exact ? expected.status : "UNKNOWN",
    review_hash: exact ? expected.review_hash : null,
    blockers: exact ? [] : ["descriptor_load_order_review_exact_rebuild"],
    browser_visual_review_verified: false,
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mount_allowed: false,
    writer_allowed: false
  });
}

module.exports = Object.freeze({
  EXPECTED_ASSET_MANIFEST,
  EXPECTED_JAVASCRIPT_LOAD_ORDER,
  EXPECTED_STYLESHEET_LOAD_ORDER,
  SCHEMA_VERSION,
  STATIC_FINGERPRINT,
  VERIFICATION_SCHEMA_VERSION,
  buildPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1,
  verifyPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1
});
