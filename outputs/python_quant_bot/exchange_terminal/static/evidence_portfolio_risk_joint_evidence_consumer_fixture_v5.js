(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var card =
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_risk_joint_evidence_card_v5.js")
      : root.HakimiPortfolioRiskJointEvidenceCardV5;
  var api = factory(strictCanonical, card);

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HakimiPortfolioRiskJointEvidenceConsumerFixtureV5 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical,
  card
) {
  "use strict";

  if (
    !strictCanonical ||
    typeof strictCanonical.sealDocument !== "function" ||
    !card ||
    typeof card.buildPortfolioRiskJointEvidenceViewModelV5 !== "function"
  ) {
    throw new Error("Strict canonical and joint evidence card-v5 are required");
  }

  var SCHEMA_VERSION =
    "portfolio-risk-joint-evidence-presentation-consumer-fixture-v5";
  var STATIC_FINGERPRINT =
    "20260823-portfolio-risk-joint-evidence-consumer-v5-unmounted-lock-1";
  var STYLESHEET_ASSET =
    "evidence_portfolio_risk_joint_evidence_card_v5.css";

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) {
      return value;
    }
    Object.keys(value).forEach(function (key) {
      deepFreeze(value[key]);
    });
    return Object.freeze(value);
  }

  function authority() {
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

  function buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
    projection
  ) {
    var sealVerified = card.verifyPortfolioRiskProjectionSealV5(projection) === true;
    var view = card.buildPortfolioRiskJointEvidenceViewModelV5(projection);
    var sourceAccepted = sealVerified && view.contract_state === "KNOWN_BLOCKED";
    var descriptor = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: "BLOCK",
      decision: sourceAccepted
        ? "KNOWN_BLOCKED_PROJECTION_V5_RENDER_DESCRIPTOR_ONLY"
        : "UNKNOWN_PROJECTION_V5_RENDER_DESCRIPTOR_FAIL_CLOSED",
      source: {
        projection_schema_version: sourceAccepted
          ? projection.schema_version
          : "UNKNOWN",
        projection_static_fingerprint: sourceAccepted
          ? projection.static_fingerprint
          : "UNKNOWN",
        projection_hash: sourceAccepted ? projection.projection_hash : null,
        projection_seal_and_schema_verified: sourceAccepted,
        projection_embedded: false,
      },
      presentation: {
        card_schema_version: card.CARD_SCHEMA_VERSION,
        card_static_fingerprint: card.CARD_STATIC_FINGERPRINT,
        stage_order: card.STAGE_ORDER.slice(),
        view_model: view,
        markup: card.renderPortfolioRiskJointEvidenceCardV5(projection),
        stylesheet_asset: STYLESHEET_ASSET,
        descriptor_only: true,
      },
      mount: {
        mode: "UNMOUNTED",
        dom_target: null,
        selector: null,
        mount_api_exposed: false,
        browser_executed: false,
      },
      facts: {
        projection_v5_accepted: sourceAccepted,
        view_model_built: sourceAccepted,
        static_markup_generated: true,
        stylesheet_declared: true,
        source_projection_embedded: false,
        runtime_assets_accessed: false,
        runtime_mutations_performed: false,
        dom_accessed: false,
        browser_visual_review_performed: false,
        profitability_proven: false,
        ui_mounted: false,
      },
      authority: authority(),
    };
    return deepFreeze(
      strictCanonical.sealDocument(descriptor, "descriptor_hash")
    );
  }

  function verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(
    descriptor,
    projection
  ) {
    if (
      !strictCanonical.verifySealedDocument(descriptor, "descriptor_hash")
    ) {
      return false;
    }
    var expected =
      buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(projection);
    return (
      strictCanonical.strictCanonicalStringify(descriptor) ===
      strictCanonical.strictCanonicalStringify(expected)
    );
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    EXPECTED_PROJECTION_SCHEMA_VERSION: card.PROJECTION_SCHEMA_VERSION,
    EXPECTED_PROJECTION_STATIC_FINGERPRINT:
      card.PROJECTION_STATIC_FINGERPRINT,
    EXPECTED_CARD_SCHEMA_VERSION: card.CARD_SCHEMA_VERSION,
    EXPECTED_CARD_STATIC_FINGERPRINT: card.CARD_STATIC_FINGERPRINT,
    STAGE_ORDER: card.STAGE_ORDER,
    STYLESHEET_ASSET: STYLESHEET_ASSET,
    buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5:
      buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5,
    verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5:
      verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5,
  });
});
