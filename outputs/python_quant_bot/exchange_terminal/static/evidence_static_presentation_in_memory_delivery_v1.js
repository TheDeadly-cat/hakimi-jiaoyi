(function (root, factory) {
  "use strict";

  var strictCanonical =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1;
  var rail =
    typeof module === "object" && module.exports
      ? require("./evidence_portfolio_correlation_admission_rail_v1.js")
      : root.HakimiPortfolioCorrelationAdmissionRailV1;
  var api = factory(strictCanonical, rail);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiStaticPresentationInMemoryDeliveryV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictCanonical, rail) {
  "use strict";

  if (!strictCanonical || typeof strictCanonical.verifySealedDocument !== "function"
    || typeof strictCanonical.sha256Hex !== "function") {
    throw new Error("Strict canonical JSON v1 is required");
  }
  if (!rail || typeof rail.verifyPortfolioCorrelationAdmissionV1 !== "function") {
    throw new Error("Portfolio correlation admission rail v1 is required");
  }

  var SCHEMA_VERSION = "static-presentation-in-memory-delivery-envelope-v1";
  var STATIC_FINGERPRINT =
    "20260823-static-presentation-in-memory-delivery-v1-host-unbound-lock-1";
  var RECEIPT_SCHEMA_VERSION = "static-presentation-in-memory-delivery-receipt-v1";
  var RECEIPT_STATIC_FINGERPRINT =
    "20260823-static-presentation-in-memory-delivery-receipt-v1-no-dom-lock-1";
  var REGISTRATION_ID = "portfolio-correlation-admission-rail-v1";
  var REGISTRATION_HASH =
    "e5512d1d84ce9a2d3e3a23955b9d089c8c454d3cad93ac49f2c78bbf288459a1";
  var SOURCE_SCHEMA_VERSION = "portfolio-correlation-admission-v1";

  function exactKeys(value, expected) {
    if (!strictCanonical.isPlainRecord(value)) return false;
    var actual = Object.keys(value).sort();
    var wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every(function (key, index) {
      return key === wanted[index];
    });
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function authorityLocked(value) {
    return exactKeys(value, [
      "browser_execution_allowed", "current_admission_allowed", "dom_mount_allowed",
      "endpoint_registration_allowed", "live_order_allowed", "paper_authorized",
      "runtime_delivery_allowed", "writer_allowed",
    ]) && Object.keys(value).every(function (key) { return value[key] === false; });
  }

  function validConsumer(value) {
    return exactKeys(value, [
      "browser_global", "render_function", "schema_version", "static_fingerprint",
      "verify_function", "view_model_function",
    ])
      && value.schema_version === rail.RAIL_SCHEMA_VERSION
      && value.static_fingerprint === rail.RAIL_STATIC_FINGERPRINT
      && value.browser_global === "HakimiPortfolioCorrelationAdmissionRailV1"
      && value.verify_function === "verifyPortfolioCorrelationAdmissionV1"
      && value.view_model_function === "buildPortfolioCorrelationAdmissionRailViewModelV1"
      && value.render_function === "renderPortfolioCorrelationAdmissionRailV1";
  }

  function validTransport(value) {
    return exactKeys(value, ["content_type", "endpoint", "host_slot", "mode", "route"])
      && value.mode === "IN_MEMORY_ARGUMENT_ONLY"
      && value.content_type === "application/json"
      && value.endpoint === null
      && value.route === null
      && value.host_slot === null;
  }

  function validFacts(value, known) {
    if (!exactKeys(value, [
      "admission_candidate_embedded", "browser_executed", "delivery_attempted",
      "dom_mounted", "javascript_adapter_executed", "markup_derived",
      "markup_embedded", "profitability_proven", "raw_correlation_evidence_embedded",
      "raw_source_report_embedded", "registration_exactly_verified",
      "runtime_mutations_performed", "source_candidate_exactly_verified",
      "view_model_derived",
    ])) return false;
    return value.registration_exactly_verified === known
      && value.source_candidate_exactly_verified === known
      && value.admission_candidate_embedded === known
      && [
        "browser_executed", "delivery_attempted", "dom_mounted",
        "javascript_adapter_executed", "markup_derived", "markup_embedded",
        "profitability_proven", "raw_correlation_evidence_embedded",
        "raw_source_report_embedded", "runtime_mutations_performed", "view_model_derived",
      ].every(function (key) { return value[key] === false; });
  }

  function verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope) {
    if (!strictCanonical.verifySealedDocument(envelope, "envelope_hash")
      || !exactKeys(envelope, [
        "authority", "consumer_contract", "delivery_state", "envelope_hash", "facts",
        "payload", "reason_code", "registration_hash", "registration_id",
        "schema_version", "source_hash", "source_schema_version", "source_status",
        "static_fingerprint", "status", "transport",
      ])
      || envelope.schema_version !== SCHEMA_VERSION
      || envelope.static_fingerprint !== STATIC_FINGERPRINT
      || envelope.registration_id !== REGISTRATION_ID
      || envelope.source_schema_version !== SOURCE_SCHEMA_VERSION
      || !validConsumer(envelope.consumer_contract)
      || !validTransport(envelope.transport)
      || !authorityLocked(envelope.authority)) return false;

    if (envelope.status === "UNKNOWN") {
      return envelope.delivery_state === "UNKNOWN"
        && typeof envelope.reason_code === "string"
        && envelope.reason_code.length > 0
        && envelope.registration_hash === null
        && envelope.source_status === "UNKNOWN"
        && envelope.source_hash === null
        && envelope.payload === null
        && validFacts(envelope.facts, false);
    }
    return envelope.status === "BLOCKED"
      && envelope.delivery_state === "EXACT_CANDIDATE_ENVELOPED_IN_MEMORY_HOST_UNBOUND"
      && envelope.registration_hash === REGISTRATION_HASH
      && ["PASS", "BLOCK"].indexOf(envelope.source_status) !== -1
      && isHash(envelope.source_hash)
      && rail.verifyPortfolioCorrelationAdmissionV1(envelope.payload)
      && envelope.payload.schema_version === SOURCE_SCHEMA_VERSION
      && envelope.payload.status === envelope.source_status
      && envelope.payload.correlation_admission_hash === envelope.source_hash
      && validFacts(envelope.facts, true);
  }

  function extractAdmissionCandidateFromEnvelopeV1(envelope) {
    return verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope)
      && envelope.status === "BLOCKED"
      ? envelope.payload
      : null;
  }

  function receiptAuthority() {
    return {
      browser_execution_allowed: false,
      current_admission_allowed: false,
      dom_mount_allowed: false,
      live_order_allowed: false,
      paper_authorized: false,
      writer_allowed: false,
    };
  }

  function buildStaticPresentationInMemoryDeliveryReceiptV1(envelope) {
    var envelopeExact = verifyStaticPresentationInMemoryDeliveryEnvelopeV1(envelope);
    var candidate = extractAdmissionCandidateFromEnvelopeV1(envelope);
    var known = candidate !== null;
    var view = known
      ? rail.buildPortfolioCorrelationAdmissionRailViewModelV1(candidate)
      : null;
    var markup = known
      ? rail.renderPortfolioCorrelationAdmissionRailV1(candidate)
      : null;
    return strictCanonical.sealDocument({
      authority: receiptAuthority(),
      envelope_hash: envelopeExact ? envelope.envelope_hash : null,
      facts: {
        admission_candidate_exactly_verified: known,
        browser_executed: false,
        dom_mounted: false,
        envelope_exactly_verified: envelopeExact,
        markup_derived: known,
        markup_embedded: false,
        profitability_proven: false,
        runtime_mutations_performed: false,
        view_model_derived: known,
      },
      markup_length: known ? markup.length : null,
      markup_sha256: known ? strictCanonical.sha256Hex(markup) : null,
      receipt_state: known
        ? "CANDIDATE_VERIFIED_MARKUP_HASH_DERIVED_NO_DOM"
        : "UNKNOWN",
      registration_hash: known ? REGISTRATION_HASH : null,
      schema_version: RECEIPT_SCHEMA_VERSION,
      source_hash: known ? candidate.correlation_admission_hash : null,
      source_status: known ? candidate.status : "UNKNOWN",
      static_fingerprint: RECEIPT_STATIC_FINGERPRINT,
      status: known ? "BLOCKED" : "UNKNOWN",
      view: known ? {
        contract_state: view.contract_state,
        gap_state: view.stages[1].state,
        permission_state: view.stages[3].state,
        rail_schema_version: view.schema_version,
        rail_static_fingerprint: view.static_fingerprint,
        status_label: view.status_label,
      } : null,
    }, "receipt_hash");
  }

  function verifyStaticPresentationInMemoryDeliveryReceiptV1(receipt, envelope) {
    if (!strictCanonical.verifySealedDocument(receipt, "receipt_hash")) return false;
    return strictCanonical.strictCanonicalStringify(receipt)
      === strictCanonical.strictCanonicalStringify(
        buildStaticPresentationInMemoryDeliveryReceiptV1(envelope)
      );
  }

  return Object.freeze({
    RECEIPT_SCHEMA_VERSION: RECEIPT_SCHEMA_VERSION,
    RECEIPT_STATIC_FINGERPRINT: RECEIPT_STATIC_FINGERPRINT,
    REGISTRATION_HASH: REGISTRATION_HASH,
    SCHEMA_VERSION: SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    buildStaticPresentationInMemoryDeliveryReceiptV1:
      buildStaticPresentationInMemoryDeliveryReceiptV1,
    extractAdmissionCandidateFromEnvelopeV1:
      extractAdmissionCandidateFromEnvelopeV1,
    verifyStaticPresentationInMemoryDeliveryEnvelopeV1:
      verifyStaticPresentationInMemoryDeliveryEnvelopeV1,
    verifyStaticPresentationInMemoryDeliveryReceiptV1:
      verifyStaticPresentationInMemoryDeliveryReceiptV1,
  });
});
