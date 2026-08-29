(function (root, factory) {
  "use strict";
  var strictCanonical = typeof module === "object" && module.exports
    ? require("./strict_canonical_json_v1.js") : root.HakimiStrictCanonicalJsonV1;
  var card = typeof module === "object" && module.exports
    ? require("./evidence_portfolio_risk_stratified_budget_card_v7.js")
    : root.HakimiPortfolioRiskStratifiedBudgetCardV7;
  var api = factory(strictCanonical, card);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskStratifiedBudgetConsumerFixtureV7 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical, card) {
  "use strict";
  if (!strictCanonical || !card) throw new Error("Strict canonical and card-v7 are required");

  var SCHEMA_VERSION = "portfolio-risk-stratified-budget-consumer-fixture-v7";
  var STATIC_FINGERPRINT = "20260823-stratified-budget-consumer-v7-unmounted-lock-1";
  var STYLESHEET_ASSET = "evidence_portfolio_risk_stratified_budget_card_v7.css";

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.keys(value).forEach(function (key) { deepFreeze(value[key]); });
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

  function buildPortfolioRiskStratifiedBudgetConsumerFixtureV7(response) {
    var contractVerified = card.verifyStratifiedBudgetCandidateResponseV7(response) === true;
    var view = card.buildPortfolioRiskStratifiedBudgetViewModelV7(response);
    var known = contractVerified && view.contract_state === "KNOWN_BLOCKED";
    var descriptor = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: "BLOCK",
      decision: known
        ? "KNOWN_BLOCKED_CANDIDATE_V7_RENDER_DESCRIPTOR_ONLY"
        : "UNKNOWN_CANDIDATE_V7_RENDER_DESCRIPTOR_FAIL_CLOSED",
      source: {
        response_schema_version: contractVerified ? response.schema_version : "UNKNOWN",
        response_static_fingerprint: contractVerified ? response.static_fingerprint : "UNKNOWN",
        response_hash: known ? response.response_hash : null,
        candidate_contract_verified: contractVerified,
        source_known: known,
        candidate_embedded: false,
      },
      presentation: {
        card_schema_version: card.CARD_SCHEMA_VERSION,
        card_static_fingerprint: card.CARD_STATIC_FINGERPRINT,
        stage_order: card.STAGE_ORDER.slice(),
        tone: view.tone,
        view_model: view,
        markup: card.renderPortfolioRiskStratifiedBudgetCardV7(response),
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
        response_v7_accepted: known,
        active_strata_budget_visible: known && view.dimensions.length > 0,
        local_block_visible: known && view.status_label === "LOCAL BLOCK",
        local_clear_is_not_permission: known && view.status_label === "LOCAL CLEAR",
        static_markup_generated: true,
        stylesheet_declared: true,
        source_candidate_embedded: false,
        runtime_assets_accessed: false,
        runtime_mutations_performed: false,
        dom_accessed: false,
        browser_visual_review_performed: false,
        profitability_proven: false,
        ui_mounted: false,
      },
      authority: authority(),
    };
    return deepFreeze(strictCanonical.sealDocument(descriptor, "descriptor_hash"));
  }

  function verifyPortfolioRiskStratifiedBudgetConsumerFixtureV7(descriptor, response) {
    if (!strictCanonical.verifySealedDocument(descriptor, "descriptor_hash")) return false;
    var expected = buildPortfolioRiskStratifiedBudgetConsumerFixtureV7(response);
    return strictCanonical.strictCanonicalStringify(descriptor)
      === strictCanonical.strictCanonicalStringify(expected);
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STYLESHEET_ASSET: STYLESHEET_ASSET,
    EXPECTED_CARD_SCHEMA_VERSION: card.CARD_SCHEMA_VERSION,
    EXPECTED_CARD_STATIC_FINGERPRINT: card.CARD_STATIC_FINGERPRINT,
    EXPECTED_RESPONSE_SCHEMA_VERSION: card.RESPONSE_SCHEMA_VERSION,
    EXPECTED_RESPONSE_STATIC_FINGERPRINT: card.RESPONSE_STATIC_FINGERPRINT,
    STAGE_ORDER: card.STAGE_ORDER,
    buildPortfolioRiskStratifiedBudgetConsumerFixtureV7:
      buildPortfolioRiskStratifiedBudgetConsumerFixtureV7,
    verifyPortfolioRiskStratifiedBudgetConsumerFixtureV7:
      verifyPortfolioRiskStratifiedBudgetConsumerFixtureV7,
  });
});
