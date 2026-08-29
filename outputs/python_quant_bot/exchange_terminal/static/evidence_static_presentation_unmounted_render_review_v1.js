(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var delivery =
    typeof module === "object" && module.exports
      ? require("./evidence_static_presentation_in_memory_delivery_v1.js")
      : root.HakimiStaticPresentationInMemoryDeliveryV1;
  var rail =
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_correlation_admission_rail_v1.js")
      : root.HakimiPortfolioCorrelationAdmissionRailV1;
  var api = factory(strictCanonical, delivery, rail);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiStaticPresentationUnmountedRenderReviewV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (
  strictCanonical,
  delivery,
  rail
) {
  "use strict";

  if (!strictCanonical
    || typeof strictCanonical.sealDocument !== "function"
    || typeof strictCanonical.verifySealedDocument !== "function"
    || typeof strictCanonical.strictCanonicalStringify !== "function"
    || typeof strictCanonical.sha256Hex !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }
  if (!delivery
    || typeof delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1
      !== "function"
    || typeof delivery.extractAdmissionCandidateFromEnvelopeV1 !== "function"
    || typeof delivery.buildStaticPresentationInMemoryDeliveryReceiptV1
      !== "function"
    || typeof delivery.verifyStaticPresentationInMemoryDeliveryReceiptV1
      !== "function") {
    throw new Error("Static presentation in-memory delivery v1 is required");
  }
  if (!rail
    || typeof rail.buildPortfolioCorrelationAdmissionRailViewModelV1
      !== "function"
    || typeof rail.renderPortfolioCorrelationAdmissionRailV1 !== "function") {
    throw new Error("Portfolio correlation admission rail v1 is required");
  }

  var SCHEMA_VERSION = "static-presentation-unmounted-render-review-receipt-v1";
  var STATIC_FINGERPRINT =
    "20260823-static-presentation-unmounted-render-review-v1-no-dom-lock-1";
  var HOST_CANDIDATE_SCHEMA_VERSION =
    "portfolio-correlation-admission-rail-host-render-candidate-v1";
  var PATCH_PREREGISTRATION_HASH =
    "90a9a0e4ba600007a7c1d11239bafbbeb52367ffdd45680395ddf96c0ff5df36";
  var PATCH_PLAN_HASH =
    "26a9d7637648b59cd5fb1900b20d2ba292920db0385493012ce0bc2ec72e932b";
  var HOST_APP_FRAGMENT_SHA256 =
    "356b49b8b9a701b12bc06d36eee28f99ebb40642f5f5e133d66819a7f58be24f";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var NO_DOM_ENVIRONMENT = typeof document === "undefined";

  function exactKeys(value, expected) {
    if (!value || Object.prototype.toString.call(value) !== "[object Object]") {
      return false;
    }
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every(function (key, index) {
      return key === wanted[index];
    });
  }

  function reviewContextExact(context) {
    return exactKeys(context, [
      "host_app_fragment_sha256",
      "patch_plan_hash",
      "patch_preregistration_hash",
    ])
      && context.patch_preregistration_hash === PATCH_PREREGISTRATION_HASH
      && context.patch_plan_hash === PATCH_PLAN_HASH
      && context.host_app_fragment_sha256 === HOST_APP_FRAGMENT_SHA256;
  }

  function authority() {
    return {
      browser_execution_allowed: false,
      current_admission_allowed: false,
      dom_mount_allowed: false,
      external_independent_review_completion_allowed: false,
      host_patch_application_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      runtime_asset_loading_allowed: false,
      writer_allowed: false,
    };
  }

  function blockers() {
    return [
      "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
      "HOST_PATCH_APPLICATION_NOT_AUTHORIZED_BY_REVIEW",
      "BROWSER_VISUAL_REVIEW_NOT_PERFORMED",
      "DOM_MOUNT_UNAUTHORIZED",
      "CURRENT_ADMISSION_LOCKED",
    ];
  }

  function unknownHostCandidate(reasonCode) {
    return {
      schema_version: HOST_CANDIDATE_SCHEMA_VERSION,
      status: "UNKNOWN",
      render_state: "UNKNOWN",
      reason_code: reasonCode,
      envelope_hash: null,
      source_hash: null,
      delivery_receipt_hash: null,
      markup: null,
    };
  }

  function expectedHostCandidate(envelope) {
    if (!delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope)) {
      return unknownHostCandidate("DELIVERY_ENVELOPE_NOT_EXACT");
    }
    var candidate = delivery.extractAdmissionCandidateFromEnvelopeV1(envelope);
    if (!candidate) return unknownHostCandidate("ADMISSION_CANDIDATE_UNKNOWN");
    var receipt = delivery.buildStaticPresentationInMemoryDeliveryReceiptV1(envelope);
    if (!delivery.verifyStaticPresentationInMemoryDeliveryReceiptV1(
      receipt,
      envelope
    )) {
      return unknownHostCandidate("DELIVERY_RECEIPT_NOT_EXACT");
    }
    return {
      schema_version: HOST_CANDIDATE_SCHEMA_VERSION,
      status: "BLOCKED",
      render_state: "EXACT_UNMOUNTED_MARKUP_CANDIDATE",
      reason_code: "EXACT_LOCAL_PRESENTATION_DERIVED_DOM_MOUNT_UNAUTHORIZED",
      envelope_hash: envelope.envelope_hash,
      source_hash: candidate.correlation_admission_hash,
      delivery_receipt_hash: receipt.receipt_hash,
      markup: rail.renderPortfolioCorrelationAdmissionRailV1(candidate),
    };
  }

  function canonicalEqual(first, second) {
    try {
      return strictCanonical.strictCanonicalStringify(first)
        === strictCanonical.strictCanonicalStringify(second);
    } catch (_error) {
      return false;
    }
  }

  function callHostApi(hostApi, envelope) {
    if (!hostApi
      || typeof hostApi.buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1
        !== "function") {
      return {
        invoked: false,
        candidate: null,
        reason_code: "HOST_RENDER_API_UNAVAILABLE",
      };
    }
    try {
      return {
        invoked: true,
        candidate:
          hostApi.buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1(
            envelope
          ),
        reason_code: null,
      };
    } catch (_error) {
      return {
        invoked: true,
        candidate: null,
        reason_code: "HOST_RENDER_API_EXCEPTION",
      };
    }
  }

  function buildReviewDocument(options) {
    var known = options.known;
    var documentValue = {
      schema_version: SCHEMA_VERSION,
      static_fingerprint: STATIC_FINGERPRINT,
      status: known ? "BLOCKED" : "UNKNOWN",
      review_state: known
        ? "EXACT_UNMOUNTED_RENDER_CANDIDATE_REVIEWED_NO_DOM"
        : "UNKNOWN",
      reason_code: options.reason_code,
      patch_preregistration_hash: options.context_exact
        ? PATCH_PREREGISTRATION_HASH
        : null,
      patch_plan_hash: options.context_exact ? PATCH_PLAN_HASH : null,
      host_app_fragment_sha256: options.context_exact
        ? HOST_APP_FRAGMENT_SHA256
        : null,
      envelope_hash: options.envelope_exact
        ? options.envelope.envelope_hash
        : null,
      source_hash: known ? options.source.correlation_admission_hash : null,
      source_status: known ? options.source.status : "UNKNOWN",
      delivery_receipt_hash: known
        ? options.host_candidate.delivery_receipt_hash
        : null,
      markup_sha256: known
        ? strictCanonical.sha256Hex(options.host_candidate.markup)
        : null,
      markup_length: known ? options.host_candidate.markup.length : null,
      presentation_summary: known ? options.presentation_summary : null,
      facts: {
        review_context_exactly_verified: options.context_exact,
        no_dom_environment_verified: NO_DOM_ENVIRONMENT,
        delivery_envelope_exactly_verified: options.envelope_exact,
        host_render_api_invoked_in_memory: options.host_invoked,
        host_render_candidate_exactly_verified: options.host_exact,
        source_candidate_exactly_verified: known,
        unmounted_markup_exactly_verified: known,
        neutral_stage_order_verified: known,
        promotional_ready_absent: known,
        local_unmounted_behavior_reviewed: known,
        external_independent_review_complete: false,
        raw_envelope_embedded: false,
        raw_source_candidate_embedded: false,
        raw_markup_embedded: false,
        host_patch_applied: false,
        browser_visual_review_performed: false,
        dom_mounted: false,
        current_activated: false,
        runtime_mutations_performed: false,
        profitability_proven: false,
      },
      blockers: blockers(),
      authority: authority(),
    };
    return strictCanonical.sealDocument(documentValue, "review_receipt_hash");
  }

  function buildStaticPresentationUnmountedRenderReviewReceiptV1(
    hostApi,
    envelope,
    reviewContext
  ) {
    var contextExact = reviewContextExact(reviewContext);
    if (!contextExact) {
      return buildReviewDocument({
        known: false,
        reason_code: "REVIEW_CONTEXT_NOT_EXACT",
        context_exact: false,
        envelope_exact: false,
        envelope: null,
        host_invoked: false,
        host_exact: false,
      });
    }
    if (!NO_DOM_ENVIRONMENT) {
      return buildReviewDocument({
        known: false,
        reason_code: "NO_DOM_REVIEW_ENVIRONMENT_REQUIRED",
        context_exact: true,
        envelope_exact: false,
        envelope: null,
        host_invoked: false,
        host_exact: false,
      });
    }

    var envelopeExact =
      delivery.verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope);
    var expected = expectedHostCandidate(envelope);
    var observed = callHostApi(hostApi, envelope);
    var hostExact = observed.candidate !== null
      && canonicalEqual(observed.candidate, expected);
    if (!hostExact) {
      return buildReviewDocument({
        known: false,
        reason_code: observed.reason_code || "HOST_RENDER_CANDIDATE_NOT_EXACT",
        context_exact: true,
        envelope_exact: envelopeExact,
        envelope: envelope,
        host_invoked: observed.invoked,
        host_exact: false,
      });
    }
    if (expected.status !== "BLOCKED") {
      return buildReviewDocument({
        known: false,
        reason_code: expected.reason_code,
        context_exact: true,
        envelope_exact: envelopeExact,
        envelope: envelope,
        host_invoked: observed.invoked,
        host_exact: true,
      });
    }

    var source = delivery.extractAdmissionCandidateFromEnvelopeV1(envelope);
    var view = rail.buildPortfolioCorrelationAdmissionRailViewModelV1(source);
    var stageOrder = view.stages.map(function (stage) { return stage.axis; });
    var presentationExact = stageOrder.length === STAGE_ORDER.length
      && stageOrder.every(function (stage, index) {
        return stage === STAGE_ORDER[index];
      })
      && typeof view.status_label === "string"
      && !/\bREADY\b/i.test(view.status_label)
      && !/\bREADY\b/i.test(expected.markup);
    if (!presentationExact) {
      return buildReviewDocument({
        known: false,
        reason_code: "PRESENTATION_SUMMARY_NOT_EXACT",
        context_exact: true,
        envelope_exact: true,
        envelope: envelope,
        host_invoked: true,
        host_exact: true,
      });
    }
    return buildReviewDocument({
      known: true,
      reason_code: (
        "EXACT_LOCAL_UNMOUNTED_RENDER_CANDIDATE_REVIEWED_"
        + "EXTERNAL_INDEPENDENCE_UNPROVEN"
      ),
      context_exact: true,
      envelope_exact: true,
      envelope: envelope,
      host_invoked: true,
      host_exact: true,
      host_candidate: expected,
      source: source,
      presentation_summary: {
        rail_schema_version: view.schema_version,
        rail_static_fingerprint: view.static_fingerprint,
        contract_state: view.contract_state,
        status_label: view.status_label,
        stage_order: stageOrder,
        stage_states: view.stages.map(function (stage) {
          return { stage: stage.axis, state: stage.state };
        }),
      },
    });
  }

  function verifyStaticPresentationUnmountedRenderReviewReceiptV1(
    receipt,
    hostApi,
    envelope,
    reviewContext
  ) {
    if (!strictCanonical.verifySealedDocument(receipt, "review_receipt_hash")) {
      return false;
    }
    return canonicalEqual(
      receipt,
      buildStaticPresentationUnmountedRenderReviewReceiptV1(
        hostApi,
        envelope,
        reviewContext
      )
    );
  }

  return Object.freeze({
    HOST_APP_FRAGMENT_SHA256: HOST_APP_FRAGMENT_SHA256,
    PATCH_PLAN_HASH: PATCH_PLAN_HASH,
    PATCH_PREREGISTRATION_HASH: PATCH_PREREGISTRATION_HASH,
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    STAGE_ORDER: Object.freeze(STAGE_ORDER.slice()),
    buildStaticPresentationUnmountedRenderReviewReceiptV1:
      buildStaticPresentationUnmountedRenderReviewReceiptV1,
    verifyStaticPresentationUnmountedRenderReviewReceiptV1:
      verifyStaticPresentationUnmountedRenderReviewReceiptV1,
  });
});
