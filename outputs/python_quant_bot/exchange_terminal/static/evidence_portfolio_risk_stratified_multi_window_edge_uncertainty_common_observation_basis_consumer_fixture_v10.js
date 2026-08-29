(function (root, factory) {
  "use strict";
  var strictCanonical = typeof module === "object" && module.exports
    ? require("./strict_canonical_json_v1.js") : root.HakimiStrictCanonicalJsonV1;
  var card = typeof module === "object" && module.exports
    ? require("./evidence_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_card_v10.js")
    : root.HakimiPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCommonObservationBasisCardV10;
  var api = factory(strictCanonical, card);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) {
    root.HakimiPortfolioRiskStratifiedMultiWindowEdgeUncertaintyCommonObservationBasisConsumerFixtureV10 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical, card) {
  "use strict";
  if (!strictCanonical || !card) throw new Error("Strict canonical and card-v10 are required");

  var SCHEMA_VERSION =
    "portfolio-risk-stratified-multi-window-edge-uncertainty-common-observation-basis-consumer-fixture-v10";
  var STATIC_FINGERPRINT =
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-" +
    "basis-consumer-v10-unmounted-lock-1";
  var STYLESHEET_ASSET =
    "evidence_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_card_v10.css";

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

  function buildConsumerFixtureV10(response) {
    var contractVerified = card.verifyCandidateResponseV10(response) === true;
    var view = card.buildViewModelV10(response);
    var known = contractVerified && view.contract_state === "KNOWN_BLOCKED";
    var descriptor = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: "BLOCK",
      decision: known
        ? "KNOWN_BLOCKED_CANDIDATE_V10_RENDER_DESCRIPTOR_ONLY"
        : "UNKNOWN_CANDIDATE_V10_RENDER_DESCRIPTOR_FAIL_CLOSED",
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
        markup: card.renderCardV10(response),
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
        response_v10_accepted: known,
        common_observation_summary_visible: known && view.common !== null,
        common_observation_basis_block_visible:
          known && view.common !== null && view.common.blocked,
        edge_uncertainty_summary_visible: known && view.edge !== null,
        local_clear_is_not_permission:
          known && view.status_label === "LOCAL CLEAR / OUTER BLOCK",
        provenance_declaration_only:
          known && view.common !== null && view.common.provenance_declaration_only,
        raw_samples_recomputed: false,
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

  function verifyConsumerFixtureV10(descriptor, response) {
    if (!strictCanonical.verifySealedDocument(descriptor, "descriptor_hash")) return false;
    var expected = buildConsumerFixtureV10(response);
    return strictCanonical.strictCanonicalStringify(descriptor)
      === strictCanonical.strictCanonicalStringify(expected);
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STYLESHEET_ASSET: STYLESHEET_ASSET,
    EXPECTED_CARD_SCHEMA_VERSION: card.CARD_SCHEMA_VERSION,
    EXPECTED_CARD_STATIC_FINGERPRINT: card.CARD_STATIC_FINGERPRINT,
    EXPECTED_HTTP_CANDIDATE_IMPLEMENTATION_SHA256:
      card.HTTP_CANDIDATE_IMPLEMENTATION_SHA256,
    EXPECTED_RESPONSE_SCHEMA_VERSION: card.RESPONSE_SCHEMA_VERSION,
    EXPECTED_RESPONSE_STATIC_FINGERPRINT: card.RESPONSE_STATIC_FINGERPRINT,
    STAGE_ORDER: card.STAGE_ORDER,
    buildConsumerFixtureV10: buildConsumerFixtureV10,
    verifyConsumerFixtureV10: verifyConsumerFixtureV10,
  });
});
