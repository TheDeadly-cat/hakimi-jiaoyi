(function initSourceBaselineProviderConformanceCard(root, factory) {
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
    root.HakimiSourceBaselineProviderConformanceCardV1 = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi(canonical) {
  "use strict";

  if (
    !canonical ||
    typeof canonical.isPlainRecord !== "function" ||
    typeof canonical.sealDocument !== "function" ||
    typeof canonical.strictCanonicalStringify !== "function" ||
    typeof canonical.verifySealedDocument !== "function"
  ) {
    throw new TypeError("strict canonical JSON v1 is required");
  }

  const CARD_SCHEMA_VERSION =
    "source-baseline-provider-conformance-neutral-card-v1";
  const CARD_STATIC_FINGERPRINT =
    "20260823-source-baseline-provider-conformance-neutral-card-v1-unmounted-lock-1";
  const PAYLOAD_SCHEMA_VERSION =
    "source-baseline-provider-conformance-presentation-consumer-payload-candidate-v1";
  const PAYLOAD_STATIC_FINGERPRINT =
    "20260823-source-baseline-presentation-consumer-preregistration-v1-lock-2";
  const CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256 =
    "7ff64216e70dcedd43b86210cfac68b632c1eb7bc10a390bec9d4ffb619ac572";
  const CONSUMER_PREREGISTRATION_HASH =
    "42b4c9830844c455b05c4952a7010655534048f73cf78f9f7ab574bebbddca5d";
  const STRICT_CANONICAL_JS_SHA256 =
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39";
  const STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);

  const EXPECTED_AXES = Object.freeze([
    Object.freeze({
      detail: "V1_IDENTITY_AND_SOURCE_TRUST_EXACT_V2_BINDING_BLOCKED",
      stage: "SOURCE",
      state: "BOUND",
    }),
    Object.freeze({
      detail:
        "EXTERNAL_IDENTITY_TRUST_CONFORMANCE_ATOMICITY_DURABILITY_UNVERIFIED",
      stage: "GAP",
      state: "OPEN",
    }),
    Object.freeze({
      detail: "14_REQUIRED_CASES_0_EXECUTED_0_PASSED",
      stage: "MATURITY",
      state: "PREREGISTERED_NOT_RUN",
    }),
    Object.freeze({
      detail: "PROVIDER_HTTP_UI_CURRENT_PAPER_LIVE_DISABLED",
      stage: "PERMISSION",
      state: "BLOCKED",
    }),
  ]);
  const EXPECTED_BLOCKERS = Object.freeze([
    "EXTERNAL_REGISTRY_IDENTITY_UNVERIFIED",
    "EXTERNAL_SOURCE_TRUST_UNVERIFIED",
    "PROVIDER_CONFORMANCE_CASES_NOT_RUN",
    "ATOMIC_COMPARE_AND_CONSUME_UNVERIFIED",
    "LINEARIZABILITY_UNVERIFIED",
    "DURABLE_COMMIT_UNVERIFIED",
    "AUTHENTICATED_CONSUMPTION_RECEIPT_NOT_ISSUED",
  ]);
  const EXPECTED_SUMMARY = Object.freeze({
    executed_case_count: 0,
    open_gap_count: 7,
    passed_case_count: 0,
    required_case_count: 14,
    source_document_count: 6,
  });
  const EXPECTED_PERMISSION = Object.freeze({
    current_admission_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    provider_call_allowed: false,
    route_registration_allowed: false,
    state: "BLOCKED",
    ui_consumer_mount_allowed: false,
    writer_allowed: false,
  });
  const EXPECTED_FACTS = Object.freeze({
    asset_manifest_complete: false,
    bounded_payload_built: true,
    browser_executed: false,
    consumer_implementation_present: false,
    current_activated: false,
    preregistration_exactly_verified: true,
    profitability_proven: false,
    raw_identity_material_embedded: false,
    raw_source_documents_embedded: false,
    route_registered: false,
    runtime_mutations_performed: false,
    source_envelope_exactly_verified: true,
    source_lineage_details_embedded: false,
    ui_mounted: false,
  });
  const EXPECTED_AUTHORITY = Object.freeze({
    asset_write_allowed: false,
    browser_execution_allowed: false,
    current_admission_allowed: false,
    descriptive_only: true,
    live_order_allowed: false,
    paper_authorized: false,
    route_registration_allowed: false,
    ui_consumer_mount_allowed: false,
  });

  function sameKeys(value, expectedKeys) {
    if (!canonical.isPlainRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = [...expectedKeys].sort();
    return (
      actual.length === expected.length &&
      actual.every((key, index) => key === expected[index])
    );
  }

  function strictEqual(left, right) {
    try {
      return (
        canonical.strictCanonicalStringify(left) ===
        canonical.strictCanonicalStringify(right)
      );
    } catch (_error) {
      return false;
    }
  }

  function snapshotStrictJson(value) {
    try {
      return JSON.parse(canonical.strictCanonicalStringify(value));
    } catch (_error) {
      return null;
    }
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function verifiedPayloadSnapshot(document) {
    const snapshot = snapshotStrictJson(document);
    if (!snapshot) return null;
    if (!canonical.verifySealedDocument(snapshot, "payload_candidate_hash")) {
      return null;
    }
    if (
      !sameKeys(snapshot, [
        "schema_version",
        "static_fingerprint",
        "status",
        "consumer_status",
        "reason_code",
        "source_envelope_hash",
        "consumer_preregistration_hash",
        "payload",
        "facts",
        "authority",
        "payload_candidate_hash",
      ]) ||
      snapshot.schema_version !== PAYLOAD_SCHEMA_VERSION ||
      snapshot.static_fingerprint !== PAYLOAD_STATIC_FINGERPRINT ||
      snapshot.status !== "BLOCKED" ||
      snapshot.consumer_status !== "PAYLOAD_BUILT_CONSUMER_UNREGISTERED" ||
      snapshot.reason_code !==
        "BOUNDED_PAYLOAD_BUILT_ASSETS_ROUTE_BROWSER_AND_MOUNT_ABSENT" ||
      snapshot.consumer_preregistration_hash !==
        CONSUMER_PREREGISTRATION_HASH ||
      !isSha256(snapshot.source_envelope_hash) ||
      !isSha256(snapshot.payload_candidate_hash) ||
      !strictEqual(snapshot.facts, EXPECTED_FACTS) ||
      !strictEqual(snapshot.authority, EXPECTED_AUTHORITY)
    ) {
      return null;
    }

    const payload = snapshot.payload;
    if (
      !sameKeys(payload, [
        "display_tone",
        "display_state",
        "ordered_stage_contract",
        "axes",
        "summary",
        "blockers",
        "permission",
      ]) ||
      payload.display_tone !== "NEUTRAL" ||
      payload.display_state !==
        "SOURCE_BOUND_CONFORMANCE_NOT_RUN_PERMISSION_BLOCKED" ||
      !strictEqual(payload.ordered_stage_contract, STAGE_ORDER) ||
      !strictEqual(payload.axes, EXPECTED_AXES) ||
      !strictEqual(payload.summary, EXPECTED_SUMMARY) ||
      !strictEqual(payload.blockers, EXPECTED_BLOCKERS) ||
      !strictEqual(payload.permission, EXPECTED_PERMISSION)
    ) {
      return null;
    }
    return snapshot;
  }

  function verifySourceBaselineProviderConformancePayloadCandidateV1(document) {
    return verifiedPayloadSnapshot(document) !== null;
  }

  function shortHash(value) {
    return value.slice(0, 12) + "..." + value.slice(-6);
  }

  function buildSourceBaselineProviderConformanceViewModelV1(document) {
    const snapshot = verifiedPayloadSnapshot(document);
    if (!snapshot) {
      throw new TypeError(
        "source-baseline provider-conformance payload candidate is invalid"
      );
    }
    const payload = snapshot.payload;
    const viewModel = {
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      status: "BLOCKED",
      mount_state: "UNMOUNTED_CANDIDATE",
      tone: "NEUTRAL",
      eyebrow: "SOURCE BASELINE / PROVIDER CONFORMANCE",
      title: "External anti-replay conformance gap",
      status_label: "NOT RUN / BLOCKED",
      lede:
        "Identity and source declarations are hash-bound locally. External atomicity, durability, linearizability, and authenticated consumption remain unverified.",
      display_state: payload.display_state,
      provenance: {
        source_envelope_hash: shortHash(snapshot.source_envelope_hash),
        consumer_preregistration_hash: shortHash(
          snapshot.consumer_preregistration_hash
        ),
        payload_candidate_hash: shortHash(snapshot.payload_candidate_hash),
      },
      metrics: [
        {
          label: "SOURCE DOCUMENTS",
          state: "BOUND",
          value: String(payload.summary.source_document_count).padStart(2, "0"),
        },
        {
          label: "REQUIRED CASES",
          state: "PREREGISTERED",
          value: String(payload.summary.required_case_count).padStart(2, "0"),
        },
        {
          label: "EXECUTED",
          state: "NOT RUN",
          value: String(payload.summary.executed_case_count).padStart(2, "0"),
        },
        {
          label: "PASSED",
          state: "NOT RUN",
          value: String(payload.summary.passed_case_count).padStart(2, "0"),
        },
        {
          label: "OPEN GAPS",
          state: "OPEN",
          value: String(payload.summary.open_gap_count).padStart(2, "0"),
        },
      ],
      stages: payload.axes.map((axis, index) => ({
        index: String(index + 1).padStart(2, "0"),
        label: axis.stage,
        state: axis.state,
        detail: axis.detail,
      })),
      blockers: payload.blockers.map((blocker, index) => ({
        index: String(index + 1).padStart(2, "0"),
        label: blocker,
        state: "OPEN",
      })),
      permission_locks: [
        "PROVIDER CALL",
        "WRITER",
        "ROUTE",
        "UI MOUNT",
        "CURRENT",
        "PAPER",
        "LIVE",
      ],
      footnote:
        "This unmounted candidate is descriptive only. It does not call a provider, register a route, mount UI, activate current evidence, or authorize paper or live activity.",
    };
    return canonical.sealDocument(viewModel, "view_model_hash");
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderSourceBaselineProviderConformanceCardV1(document) {
    const view = buildSourceBaselineProviderConformanceViewModelV1(document);
    const metrics = view.metrics
      .map(
        (metric) =>
          '<li class="sb-conformance-card__metric">' +
          '<span class="sb-conformance-card__metric-label">' +
          escapeHtml(metric.label) +
          "</span>" +
          '<strong class="sb-conformance-card__metric-value">' +
          escapeHtml(metric.value) +
          "</strong>" +
          '<span class="sb-conformance-card__metric-state">' +
          escapeHtml(metric.state) +
          "</span></li>"
      )
      .join("");
    const stages = view.stages
      .map(
        (stage) =>
          '<li class="sb-conformance-card__stage" data-stage="' +
          escapeHtml(stage.label) +
          '"><span class="sb-conformance-card__stage-index">' +
          escapeHtml(stage.index) +
          "</span>" +
          '<span class="sb-conformance-card__stage-label">' +
          escapeHtml(stage.label) +
          "</span>" +
          '<strong class="sb-conformance-card__stage-state">' +
          escapeHtml(stage.state) +
          "</strong>" +
          '<span class="sb-conformance-card__stage-detail">' +
          escapeHtml(stage.detail) +
          "</span></li>"
      )
      .join("");
    const blockers = view.blockers
      .map(
        (blocker) =>
          '<li class="sb-conformance-card__blocker">' +
          '<span class="sb-conformance-card__blocker-index">' +
          escapeHtml(blocker.index) +
          "</span>" +
          '<span class="sb-conformance-card__blocker-label">' +
          escapeHtml(blocker.label) +
          "</span>" +
          '<strong class="sb-conformance-card__blocker-state">' +
          escapeHtml(blocker.state) +
          "</strong></li>"
      )
      .join("");
    const locks = view.permission_locks
      .map(
        (lock) =>
          '<span class="sb-conformance-card__lock">' +
          escapeHtml(lock) +
          " / LOCKED</span>"
      )
      .join("");
    return (
      '<article class="sb-conformance-card" data-schema-version="' +
      escapeHtml(view.schema_version) +
      '" data-status="blocked" data-mount-state="unmounted-candidate">' +
      '<header class="sb-conformance-card__header"><div>' +
      '<p class="sb-conformance-card__eyebrow">' +
      escapeHtml(view.eyebrow) +
      "</p>" +
      '<h2 class="sb-conformance-card__title">' +
      escapeHtml(view.title) +
      "</h2></div>" +
      '<span class="sb-conformance-card__status">' +
      escapeHtml(view.status_label) +
      "</span></header>" +
      '<p class="sb-conformance-card__lede">' +
      escapeHtml(view.lede) +
      "</p>" +
      '<ul class="sb-conformance-card__metrics" aria-label="Bounded conformance counts">' +
      metrics +
      "</ul>" +
      '<ol class="sb-conformance-card__stage-rail" aria-label="Source to permission stages">' +
      stages +
      "</ol>" +
      '<section class="sb-conformance-card__gap-panel" aria-label="Open provider conformance gaps">' +
      '<div class="sb-conformance-card__section-heading"><span>OPEN GAP REGISTER</span><strong>' +
      String(view.blockers.length).padStart(2, "0") +
      "</strong></div>" +
      '<ol class="sb-conformance-card__blockers">' +
      blockers +
      "</ol></section>" +
      '<div class="sb-conformance-card__locks" aria-label="Locked permissions">' +
      locks +
      "</div>" +
      '<footer class="sb-conformance-card__footer">' +
      escapeHtml(view.footnote) +
      "</footer></article>"
    );
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT,
    CONSUMER_PREREGISTRATION_HASH,
    CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256,
    PAYLOAD_SCHEMA_VERSION,
    PAYLOAD_STATIC_FINGERPRINT,
    STAGE_ORDER,
    STRICT_CANONICAL_JS_SHA256,
    buildSourceBaselineProviderConformanceViewModelV1,
    renderSourceBaselineProviderConformanceCardV1,
    verifySourceBaselineProviderConformancePayloadCandidateV1,
  });
});
