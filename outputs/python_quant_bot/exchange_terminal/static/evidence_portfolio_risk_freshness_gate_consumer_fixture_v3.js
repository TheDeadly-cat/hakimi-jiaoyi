(function (root, factory) {
  let card = null;
  if (typeof module === "object" && module.exports) {
    card = require("./evidence_portfolio_risk_freshness_gate_card_v3.js");
    module.exports = factory(card);
  } else if (root) {
    card = root.HakimiPortfolioRiskFreshnessGateCardV3;
    root.HakimiPortfolioRiskFreshnessGateConsumerFixtureV3 = factory(card);
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (card) {
  "use strict";

  const SCHEMA_VERSION =
    "portfolio-risk-freshness-presentation-consumer-fixture-v3";
  const STATIC_FINGERPRINT =
    "20260822-portfolio-risk-freshness-consumer-fixture-lock-1";
  const EXPECTED_CARD_SCHEMA_VERSION = "portfolio-risk-freshness-gate-card-v3";
  const EXPECTED_CARD_STATIC_FINGERPRINT =
    "20260822-portfolio-risk-freshness-gate-card-lock-1";
  const EXPECTED_PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v3";
  const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.getOwnPropertyNames(value).forEach((key) => deepFreeze(value[key]));
    return Object.freeze(value);
  }

  function cardContractAvailable() {
    return card
      && card.CARD_SCHEMA_VERSION === EXPECTED_CARD_SCHEMA_VERSION
      && card.CARD_STATIC_FINGERPRINT === EXPECTED_CARD_STATIC_FINGERPRINT
      && card.PROJECTION_SCHEMA_VERSION === EXPECTED_PROJECTION_SCHEMA_VERSION
      && typeof card.buildPortfolioRiskFreshnessGateViewModelV3 === "function"
      && typeof card.renderPortfolioRiskFreshnessGateCardV3 === "function";
  }

  function fallbackModel() {
    return {
      schema_version: EXPECTED_CARD_SCHEMA_VERSION,
      static_fingerprint: EXPECTED_CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      kicker: "PORTFOLIO RISK / LOCAL RESEARCH",
      title: "Session freshness gate",
      summary: "Projection contract is unknown. No permission can be inferred.",
      stages: [
        { key: "SOURCE", label: "Source", state: "UNKNOWN", detail: "UNKNOWN", tone: "source" },
        { key: "GAP", label: "Gap", state: "UNKNOWN", detail: "UNKNOWN", tone: "gap" },
        { key: "MATURITY", label: "Maturity", state: "UNKNOWN", detail: "UNKNOWN", tone: "maturity" },
        { key: "PERMISSION", label: "Permission", state: "UNAUTHORIZED", detail: "NO_PERMISSION_CAN_BE_INFERRED", tone: "locked" }
      ],
      projection_hash_short: "unknown",
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable."
    };
  }

  function fallbackMarkup() {
    return '<section class="prfg-v3" data-contract-state="UNKNOWN" aria-label="Portfolio risk session freshness evidence"><p>UNKNOWN</p><strong>UNAUTHORIZED</strong></section>';
  }

  function buildPortfolioRiskFreshnessPresentationConsumerFixtureV3(projection) {
    let model = fallbackModel();
    let markup = fallbackMarkup();
    let rendererInvoked = false;
    if (cardContractAvailable()) {
      try {
        model = card.buildPortfolioRiskFreshnessGateViewModelV3(projection);
        markup = card.renderPortfolioRiskFreshnessGateCardV3(projection);
        rendererInvoked = true;
      } catch (_error) {
        model = fallbackModel();
        markup = fallbackMarkup();
      }
    }

    const stageOrder = Array.isArray(model.stages)
      ? model.stages.map((stage) => stage.key)
      : [];
    const known = model.contract_state === "KNOWN"
      && stageOrder.length === STAGE_ORDER.length
      && stageOrder.every((stage, index) => stage === STAGE_ORDER[index])
      && model.stages[3].state === "UNAUTHORIZED"
      && projection
      && projection.schema_version === EXPECTED_PROJECTION_SCHEMA_VERSION
      && isHash(projection.projection_hash);

    const descriptor = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: known ? "PASS" : "BLOCK",
      decision: known
        ? "KNOWN_PROJECTION_RENDER_DESCRIPTOR_BUILT_UNMOUNTED"
        : "UNKNOWN_PROJECTION_RENDER_DESCRIPTOR_BUILT_FAIL_CLOSED",
      source: {
        projection_schema_version: known
          ? projection.schema_version
          : "UNKNOWN",
        projection_hash: known ? projection.projection_hash : null,
        card_schema_version: EXPECTED_CARD_SCHEMA_VERSION,
        card_static_fingerprint: EXPECTED_CARD_STATIC_FINGERPRINT,
        card_contract_available: cardContractAvailable()
      },
      presentation: {
        contract_state: known ? "KNOWN" : "UNKNOWN",
        stage_order: STAGE_ORDER.slice(),
        view_model: model,
        markup,
        markup_embedded: true
      },
      mount: {
        requested: false,
        performed: false,
        target_kind: "NONE",
        selector: null,
        dom_accessed: false,
        browser_review_performed: false
      },
      facts: {
        renderer_invoked: rendererInvoked,
        projection_document_embedded: false,
        source_evidence_embedded: false,
        positions_embedded: false,
        completed_price_rows_embedded: false,
        return_series_embedded: false,
        correlation_matrices_embedded: false,
        profitability_proven: false,
        runtime_assets_accessed: false,
        runtime_consumer_bound: false,
        server_route_registered: false,
        ui_mounted: false
      },
      authority: {
        descriptive_only: true,
        current_admission_allowed: false,
        current_pointer_written: false,
        live_order_allowed: false,
        migration_allowed: false,
        paper_authorized: false,
        presentation_consumer_activation_allowed: false,
        runtime_gate_activation_allowed: false,
        shadow_consumer_activation_allowed: false,
        writer_allowed: false
      }
    };
    return deepFreeze(descriptor);
  }

  return Object.freeze({
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    EXPECTED_CARD_SCHEMA_VERSION,
    EXPECTED_CARD_STATIC_FINGERPRINT,
    EXPECTED_PROJECTION_SCHEMA_VERSION,
    STAGE_ORDER,
    buildPortfolioRiskFreshnessPresentationConsumerFixtureV3
  });
});
