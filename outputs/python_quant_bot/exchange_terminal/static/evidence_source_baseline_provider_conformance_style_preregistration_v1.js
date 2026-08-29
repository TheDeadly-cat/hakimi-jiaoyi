(function initSourceBaselineProviderConformanceStylePreregistration(root, factory) {
  "use strict";

  const hasCommonJs =
    typeof module === "object" && module && module.exports;
  const canonical = hasCommonJs
    ? require("./strict_canonical_json_v1.js")
    : root && root.HakimiStrictCanonicalJsonV1;
  const api = factory(canonical);
  if (hasCommonJs) {
    module.exports = api;
  } else if (root && typeof root === "object") {
    root.HakimiSourceBaselineProviderConformanceStylePreregistrationV1 = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi(canonical) {
  "use strict";

  if (
    !canonical ||
    typeof canonical.sealDocument !== "function" ||
    typeof canonical.strictCanonicalStringify !== "function"
  ) {
    throw new TypeError("strict canonical JSON v1 is required");
  }

  const SCHEMA_VERSION =
    "source-baseline-provider-conformance-style-preregistration-v1";
  const STATIC_FINGERPRINT =
    "20260823-source-baseline-provider-conformance-style-preregistration-v1-lock-1";
  const STATUS = "BLOCKED";
  const CONSUMER_REGISTRATION_IMPLEMENTATION_SHA256 =
    "948aaa77ea86658732226d2ed4d4c585a625ba409b946ef1f79fac58f0a883fe";
  const CONSUMER_REGISTRATION_HASH =
    "217e4b759b993f3f513b989b79c380f7e192c799872e3f6959116171cc83d036";
  const CARD_IMPLEMENTATION_SHA256 =
    "88a1ac27eaefd554e82129a5b2883d14af365965559d1d0e84db8dc32b1d9a5a";
  const STRICT_CANONICAL_JS_SHA256 =
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
  const PROTECTED_STYLESHEET_SHA256 =
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a";

  const STYLE_TOKENS = Object.freeze({
    colors: Object.freeze({
      surface: "#e8eef0",
      ink: "#142226",
      trace: "#245f63",
      gap: "#8a521f",
      lock: "#7a3028",
      line: "#779097",
    }),
    typography: Object.freeze({
      display:
        '"Bahnschrift SemiCondensed", "DIN Condensed", sans-serif',
      body: '"Aptos", "Trebuchet MS", sans-serif',
      utility: '"Cascadia Mono", "IBM Plex Mono", monospace',
    }),
    geometry: Object.freeze({
      corner_radius_px: 2,
      rule_width_px: 1,
      stage_count: 4,
      metric_count: 5,
      gap_count: 7,
    }),
  });

  function buildSourceBaselineProviderConformanceStylePreregistrationV1() {
    const document = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: STATUS,
      candidate_state: "ISOLATED_STYLESHEET_UNMOUNTED",
      decision:
        "COLD_AUDIT_FILM_TOKENS_AND_SELECTORS_PREREGISTERED_STYLESHEET_HASH_APP_ROUTE_BROWSER_AND_MOUNT_ABSENT",
      brief: {
        subject: "EXTERNAL_ANTI_REPLAY_PROVIDER_CONFORMANCE_GAP",
        audience: "RESEARCH_TERMINAL_OPERATOR",
        single_job:
          "SEPARATE_BOUND_SOURCE_OPEN_GAPS_NOT_RUN_MATURITY_AND_LOCKED_PERMISSION_AT_A_GLANCE",
        visual_direction: "COLD_AUDIT_FILM",
        signature_element: "FOUR_STAGE_CALIBRATION_SPINE",
      },
      source_contract: {
        consumer_registration_hash: CONSUMER_REGISTRATION_HASH,
        consumer_registration_implementation_sha256:
          CONSUMER_REGISTRATION_IMPLEMENTATION_SHA256,
        card_implementation_sha256: CARD_IMPLEMENTATION_SHA256,
        strict_canonical_javascript_sha256: STRICT_CANONICAL_JS_SHA256,
      },
      tokens: STYLE_TOKENS,
      selector_contract: {
        namespace: ".sb-conformance-card",
        required_classes: [
          "sb-conformance-card",
          "sb-conformance-card__header",
          "sb-conformance-card__status",
          "sb-conformance-card__metrics",
          "sb-conformance-card__stage-rail",
          "sb-conformance-card__stage",
          "sb-conformance-card__gap-panel",
          "sb-conformance-card__blockers",
          "sb-conformance-card__locks",
          "sb-conformance-card__footer",
        ],
        required_stage_selectors: [
          "SOURCE",
          "GAP",
          "MATURITY",
          "PERMISSION",
        ],
        global_selectors_allowed: false,
      },
      responsive_contract: {
        compact_breakpoint_max_width_px: 780,
        narrow_breakpoint_max_width_px: 520,
        desktop_stage_layout: "FOUR_COLUMN_SPINE",
        compact_stage_layout: "VERTICAL_SPINE",
      },
      motion_contract: {
        animation_name: "sb-conformance-calibration-in",
        mounted_state_only: true,
        reduced_motion_override_required: true,
        ambient_animation_allowed: false,
      },
      asset_plan: {
        stylesheet_path:
          "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.css",
        stylesheet_sha256: null,
        protected_stylesheet_path: "exchange_terminal/static/styles.css",
        protected_stylesheet_observed_sha256: PROTECTED_STYLESHEET_SHA256,
        protected_stylesheet_imported: false,
        app_importer: null,
        html_template: null,
      },
      facts: {
        style_contract_preregistered: true,
        isolated_stylesheet_candidate_declared: true,
        stylesheet_hash_registered: false,
        protected_stylesheet_modified: false,
        app_imported: false,
        route_registered: false,
        browser_executed: false,
        visually_reviewed: false,
        ui_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      authority: {
        descriptive_only: true,
        protected_stylesheet_write_allowed: false,
        stylesheet_binding_allowed: false,
        app_import_allowed: false,
        route_registration_allowed: false,
        browser_execution_allowed: false,
        ui_consumer_mount_allowed: false,
        current_admission_allowed: false,
        paper_authorized: false,
        live_order_allowed: false,
      },
    };
    return canonical.sealDocument(document, "style_preregistration_hash");
  }

  function verifySourceBaselineProviderConformanceStylePreregistrationV1(
    document
  ) {
    try {
      const snapshot = JSON.parse(canonical.strictCanonicalStringify(document));
      return (
        canonical.strictCanonicalStringify(snapshot) ===
        canonical.strictCanonicalStringify(
          buildSourceBaselineProviderConformanceStylePreregistrationV1()
        )
      );
    } catch (_error) {
      return false;
    }
  }

  return Object.freeze({
    CARD_IMPLEMENTATION_SHA256,
    CONSUMER_REGISTRATION_HASH,
    CONSUMER_REGISTRATION_IMPLEMENTATION_SHA256,
    PROTECTED_STYLESHEET_SHA256,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    STATUS,
    STRICT_CANONICAL_JS_SHA256,
    STYLE_TOKENS,
    buildSourceBaselineProviderConformanceStylePreregistrationV1,
    verifySourceBaselineProviderConformanceStylePreregistrationV1,
  });
});
