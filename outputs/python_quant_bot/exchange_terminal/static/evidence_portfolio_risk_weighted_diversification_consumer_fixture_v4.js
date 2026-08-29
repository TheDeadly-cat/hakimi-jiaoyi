(function (root, factory) {
  let card = null;
  if (typeof module === "object" && module.exports) {
    card = require("./evidence_portfolio_risk_weighted_diversification_card_v4.js");
    module.exports = factory(card);
  } else if (root) {
    card = root.HakimiPortfolioRiskWeightedDiversificationCardV4;
    root.HakimiPortfolioRiskWeightedDiversificationConsumerFixtureV4 = factory(card);
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (card) {
  "use strict";

  const SCHEMA_VERSION =
    "portfolio-risk-weighted-diversification-presentation-consumer-fixture-v4";
  const STATIC_FINGERPRINT =
    "20260823-weighted-diversification-consumer-fixture-v4-sealed-projection-lock-2";
  const EXPECTED_CARD_SCHEMA_VERSION =
    "portfolio-risk-weighted-diversification-card-v4";
  const EXPECTED_CARD_STATIC_FINGERPRINT =
    "20260823-weighted-diversification-card-v4-sealed-projection-lock-2";
  const EXPECTED_PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v4";
  const EXPECTED_PROJECTION_STATIC_FINGERPRINT =
    "20260823-weighted-diversification-public-projection-v4-lock-1";
  const STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION"
  ]);
  const CARD_API_KEYS = Object.freeze([
    "CARD_SCHEMA_VERSION",
    "CARD_STATIC_FINGERPRINT",
    "PROJECTION_SCHEMA_VERSION",
    "PROJECTION_STATIC_FINGERPRINT",
    "STAGE_ORDER",
    "buildPortfolioRiskWeightedDiversificationViewModelV4",
    "renderPortfolioRiskWeightedDiversificationCardV4",
    "verifyPortfolioRiskProjectionSealV4"
  ].sort());
  const MODEL_KEYS = Object.freeze([
    "blockers",
    "contract_state",
    "effective_ratio_pct",
    "kicker",
    "metrics",
    "permission_note",
    "projection_hash_short",
    "schema_version",
    "stages",
    "static_fingerprint",
    "summary",
    "title",
    "tone"
  ].sort());
  const PROJECTION_AUTHORITY_KEYS = Object.freeze([
    "current_admission_allowed",
    "current_pointer_written",
    "formal_registry_activation_allowed",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "presentation_only",
    "research_only",
    "runtime_gate_activation_allowed",
    "shadow_consumer_activation_allowed",
    "writer_allowed"
  ].sort());

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function exactKeys(value, expected) {
    if (!isObject(value)) return false;
    const actual = Object.keys(value).sort();
    return actual.length === expected.length
      && actual.every((key, index) => key === expected[index]);
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.getOwnPropertyNames(value).forEach((key) => deepFreeze(value[key]));
    return Object.freeze(value);
  }

  function cardContractAvailable() {
    return exactKeys(card, CARD_API_KEYS)
      && card.CARD_SCHEMA_VERSION === EXPECTED_CARD_SCHEMA_VERSION
      && card.CARD_STATIC_FINGERPRINT === EXPECTED_CARD_STATIC_FINGERPRINT
      && card.PROJECTION_SCHEMA_VERSION === EXPECTED_PROJECTION_SCHEMA_VERSION
      && card.PROJECTION_STATIC_FINGERPRINT
        === EXPECTED_PROJECTION_STATIC_FINGERPRINT
      && Array.isArray(card.STAGE_ORDER)
      && card.STAGE_ORDER.length === STAGE_ORDER.length
      && card.STAGE_ORDER.every((key, index) => key === STAGE_ORDER[index])
      && typeof card.buildPortfolioRiskWeightedDiversificationViewModelV4
        === "function"
      && typeof card.renderPortfolioRiskWeightedDiversificationCardV4
        === "function"
      && typeof card.verifyPortfolioRiskProjectionSealV4 === "function";
  }

  function projectionAuthorityLocked(projection) {
    const authority = isObject(projection) ? projection.authority : null;
    if (!exactKeys(authority, PROJECTION_AUTHORITY_KEYS)) return false;
    return authority.research_only === true
      && authority.presentation_only === true
      && PROJECTION_AUTHORITY_KEYS.every((key) => (
        key === "research_only" || key === "presentation_only"
          ? authority[key] === true
          : authority[key] === false
      ));
  }

  function modelPresentable(model) {
    if (!exactKeys(model, MODEL_KEYS)) return false;
    if (
      model.schema_version !== EXPECTED_CARD_SCHEMA_VERSION
      || model.static_fingerprint !== EXPECTED_CARD_STATIC_FINGERPRINT
      || model.contract_state !== "KNOWN"
      || typeof model.kicker !== "string"
      || typeof model.title !== "string"
      || typeof model.summary !== "string"
      || typeof model.permission_note !== "string"
      || typeof model.projection_hash_short !== "string"
      || typeof model.tone !== "string"
      || !Array.isArray(model.blockers)
      || !model.blockers.every((item) => typeof item === "string")
      || !Array.isArray(model.metrics)
      || model.metrics.length !== 4
      || !model.metrics.every((metric) => (
        exactKeys(metric, ["label", "note", "value"])
        && typeof metric.label === "string"
        && typeof metric.note === "string"
        && typeof metric.value === "string"
      ))
      || !Array.isArray(model.stages)
      || model.stages.length !== STAGE_ORDER.length
    ) {
      return false;
    }
    const stageOrderExact = model.stages.every((stage, index) => (
      isObject(stage)
      && stage.key === STAGE_ORDER[index]
      && typeof stage.state === "string"
      && typeof stage.detail === "string"
    ));
    return stageOrderExact
      && model.stages[3].state === "UNAUTHORIZED"
      && (
        model.effective_ratio_pct === null
        || (
          typeof model.effective_ratio_pct === "number"
          && Number.isFinite(model.effective_ratio_pct)
        )
      );
  }

  function markupPresentable(markup) {
    return typeof markup === "string"
      && markup.includes("prwd-v4")
      && markup.includes("UNAUTHORIZED")
      && !/<(?:script|iframe|object|embed)\b/i.test(markup)
      && !/\son[a-z]+\s*=/i.test(markup);
  }

  function projectionPresentable(projection) {
    return isObject(projection)
      && projection.schema_version === EXPECTED_PROJECTION_SCHEMA_VERSION
      && projection.static_fingerprint === EXPECTED_PROJECTION_STATIC_FINGERPRINT
      && projection.status === "PASS"
      && projection.decision
        === "EXACT_WEIGHTED_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED"
      && isHash(projection.projection_hash)
      && card.verifyPortfolioRiskProjectionSealV4(projection) === true
      && projectionAuthorityLocked(projection);
  }

  function fallbackModel() {
    return {
      schema_version: EXPECTED_CARD_SCHEMA_VERSION,
      static_fingerprint: EXPECTED_CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      kicker: "PORTFOLIO RISK / LOCAL RESEARCH",
      title: "Weighted diversification",
      summary: "Projection contract is unknown. No permission can be inferred.",
      stages: [
        { key: "SOURCE", label: "Source", state: "UNKNOWN", detail: "UNKNOWN", tone: "source" },
        { key: "GAP", label: "Gap", state: "UNKNOWN", detail: "UNKNOWN", tone: "gap" },
        { key: "MATURITY", label: "Maturity", state: "UNKNOWN", detail: "UNKNOWN", tone: "maturity" },
        { key: "PERMISSION", label: "Permission", state: "UNAUTHORIZED", detail: "NO_PERMISSION_CAN_BE_INFERRED", tone: "locked" }
      ],
      metrics: [
        { label: "Label count", value: "N/A", note: "Unverified" },
        { label: "Weighted effective count", value: "N/A", note: "Unverified" },
        { label: "Dominant share", value: "N/A", note: "Unverified" },
        { label: "Minimum", value: "N/A", note: "Unverified" }
      ],
      blockers: ["UNKNOWN_PROJECTION_CONTRACT"],
      effective_ratio_pct: null,
      projection_hash_short: "unknown",
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable.",
      tone: "unknown"
    };
  }

  function fallbackMarkup() {
    return '<section class="prwd-v4" data-contract-state="UNKNOWN" aria-label="Weighted diversification evidence"><p>UNKNOWN</p><strong>UNAUTHORIZED</strong></section>';
  }

  function buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4(
    projection
  ) {
    const contractAvailable = cardContractAvailable();
    let model = fallbackModel();
    let markup = fallbackMarkup();
    let rendererInvoked = false;
    let known = false;

    if (contractAvailable) {
      try {
        const candidateModel =
          card.buildPortfolioRiskWeightedDiversificationViewModelV4(projection);
        const candidateMarkup =
          card.renderPortfolioRiskWeightedDiversificationCardV4(projection);
        rendererInvoked = true;
        known = projectionPresentable(projection)
          && modelPresentable(candidateModel)
          && markupPresentable(candidateMarkup);
        if (known) {
          model = candidateModel;
          markup = candidateMarkup;
        }
      } catch (_error) {
        known = false;
      }
    }

    const descriptor = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: known ? "PASS" : "BLOCK",
      decision: known
        ? "KNOWN_WEIGHTED_PROJECTION_RENDER_DESCRIPTOR_BUILT_UNMOUNTED"
        : "UNKNOWN_WEIGHTED_PROJECTION_RENDER_DESCRIPTOR_FAIL_CLOSED",
      source: {
        projection_schema_version: known
          ? projection.schema_version
          : "UNKNOWN",
        projection_static_fingerprint: EXPECTED_PROJECTION_STATIC_FINGERPRINT,
        projection_hash: known ? projection.projection_hash : null,
        card_schema_version: EXPECTED_CARD_SCHEMA_VERSION,
        card_static_fingerprint: EXPECTED_CARD_STATIC_FINGERPRINT,
        card_contract_available: contractAvailable,
        implementation_hashes_runtime_verified: false
      },
      presentation: {
        contract_state: known ? "KNOWN" : "UNKNOWN",
        stage_order: STAGE_ORDER.slice(),
        metric_count: known ? model.metrics.length : 0,
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
        weighted_summary_presented: known,
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
    EXPECTED_PROJECTION_STATIC_FINGERPRINT,
    STAGE_ORDER,
    buildPortfolioRiskWeightedDiversificationPresentationConsumerFixtureV4
  });
});
