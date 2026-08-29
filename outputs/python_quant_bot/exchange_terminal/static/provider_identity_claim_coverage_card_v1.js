(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HakimiProviderIdentityClaimCoverageCardV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const constants = Object.freeze({
    AXIS_ORDER: Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]),
    ENVELOPE_SCHEMA: "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-uniqueness-freshness-presentation-envelope-v1",
    ENVELOPE_FINGERPRINT: "20261004-cross-lag-factor-calibration-long-horizon-provider-identity-uniqueness-freshness-presentation-envelope-1",
    DISPLAY_STATE: "SIGNED_CLAIMS_BOUND_BOUNDED_PREFIX_EXTERNAL_TRUST_GAP",
    SIGNED_CLAIM_SCHEMA: "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-evaluation-v1",
    SIGNED_CLAIM_FINGERPRINT: "20261002-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-verifier-1",
    COVERAGE_SCHEMA: "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-longitudinal-coverage-evaluation-v1",
    COVERAGE_FINGERPRINT: "20261003-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-longitudinal-coverage-1"
  });

  const TOP_KEYS = Object.freeze(["authority", "axes", "axis_order", "blockers", "display_state", "facts", "lineage", "presentation_hash", "presentation_status", "schema_version", "source_coverage_fingerprint", "source_coverage_schema", "source_signed_claim_fingerprint", "source_signed_claim_schema", "static_fingerprint", "summary"]);
  const AXIS_KEYS = Object.freeze(["axis", "detail", "headline", "signal", "state"]);
  const SUMMARY_KEYS = Object.freeze(["assertion_leaf_index", "assertion_receipt_hash", "checkpoint_tree_size", "coverage_end_tree_size", "coverage_evaluation_count", "coverage_start_tree_size", "maximum_reference_time_gap_ms", "occurrence_provider_id", "reference_time_ms_claim", "replay_registry_id", "scan_completed_at_ms_claim", "time_authority_id"]);
  const LINEAGE_KEYS = Object.freeze(["coverage_evaluation_receipt_hash", "coverage_registration_receipt_hash", "first_checkpoint_hash", "first_source_evaluation_receipt_hash", "last_checkpoint_hash", "last_source_evaluation_receipt_hash", "signed_claim_evaluation_receipt_hash", "source_evidence_registration_receipt_hash"]);
  const FACT_KEYS = Object.freeze(["assertion_uniqueness_verified", "bounded_prefix_verified", "complete_history_verified", "complete_scan_claim_verified", "external_occurrence_provider_trust_attested", "external_time_authority_trust_attested", "freshness_verified", "longitudinal_coverage_evaluation_verified", "replay_absence_verified", "result_available", "signed_claim_evaluation_verified", "time_window_claim_verified"]);
  const AUTHORITY_KEYS = Object.freeze(["current_admission_allowed", "current_pointer_written", "descriptive_only", "freshness_truth_promotion_allowed", "live_order_allowed", "paper_authorized", "replay_absence_promotion_allowed", "uniqueness_truth_promotion_allowed"]);
  const HASH_RE = /^[0-9a-f]{64}$/;

  function exactKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value).sort();
    return keys.length === expected.length && keys.every((key, index) => key === expected[index]);
  }

  function requireExact(value, expected, label) {
    if (!exactKeys(value, expected)) throw new TypeError(label + " fields are not exact");
  }

  function isInteger(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function isHash(value) {
    return typeof value === "string" && HASH_RE.test(value);
  }

  function validateAuthority(authority) {
    requireExact(authority, AUTHORITY_KEYS, "authority");
    for (const key of AUTHORITY_KEYS) {
      const expected = key === "descriptive_only";
      if (authority[key] !== expected) throw new TypeError("authority must remain descriptive and locked");
    }
    return true;
  }

  function validateFacts(facts, positive) {
    requireExact(facts, FACT_KEYS, "facts");
    for (const key of FACT_KEYS) if (typeof facts[key] !== "boolean") throw new TypeError("fact values must be boolean");
    if (positive) {
      for (const key of ["result_available", "signed_claim_evaluation_verified", "longitudinal_coverage_evaluation_verified", "complete_scan_claim_verified", "time_window_claim_verified", "bounded_prefix_verified"]) {
        if (facts[key] !== true) throw new TypeError("positive presentation facts are incomplete");
      }
    } else if (FACT_KEYS.some((key) => facts[key] !== false)) {
      throw new TypeError("unknown presentation facts must remain false");
    }
    for (const key of ["external_occurrence_provider_trust_attested", "external_time_authority_trust_attested", "assertion_uniqueness_verified", "freshness_verified", "replay_absence_verified", "complete_history_verified"]) {
      if (facts[key] !== false) throw new TypeError("truth-bearing facts must remain false");
    }
    return true;
  }

  function validateAxes(axes, positive) {
    if (!Array.isArray(axes) || axes.length !== constants.AXIS_ORDER.length) throw new TypeError("axes must be complete");
    return axes.map((axis, index) => {
      requireExact(axis, AXIS_KEYS, "axis");
      if (axis.axis !== constants.AXIS_ORDER[index]) throw new TypeError("axis order mismatch");
      for (const key of AXIS_KEYS) if (typeof axis[key] !== "string") throw new TypeError("axis values must be strings");
      if (!positive && (axis.state !== "UNKNOWN" || axis.signal !== "UNKNOWN")) throw new TypeError("unknown axes must fail closed");
      return Object.freeze(Object.assign({}, axis, { ordinal: index + 1 }));
    });
  }

  function validateEnvelope(envelope) {
    requireExact(envelope, TOP_KEYS, "envelope");
    if (envelope.schema_version !== constants.ENVELOPE_SCHEMA || envelope.static_fingerprint !== constants.ENVELOPE_FINGERPRINT) throw new TypeError("envelope contract mismatch");
    if (envelope.presentation_status !== "UNMOUNTED_CANDIDATE" || !isHash(envelope.presentation_hash)) throw new TypeError("presentation seal metadata invalid");
    if (!Array.isArray(envelope.axis_order) || envelope.axis_order.join("|") !== constants.AXIS_ORDER.join("|")) throw new TypeError("axis_order mismatch");
    const positive = envelope.display_state === constants.DISPLAY_STATE;
    if (!positive && envelope.display_state !== "UNKNOWN") throw new TypeError("display_state invalid");
    if (positive) {
      if (envelope.source_signed_claim_schema !== constants.SIGNED_CLAIM_SCHEMA || envelope.source_signed_claim_fingerprint !== constants.SIGNED_CLAIM_FINGERPRINT) throw new TypeError("signed claim source mismatch");
      if (envelope.source_coverage_schema !== constants.COVERAGE_SCHEMA || envelope.source_coverage_fingerprint !== constants.COVERAGE_FINGERPRINT) throw new TypeError("coverage source mismatch");
    } else if ([envelope.source_signed_claim_schema, envelope.source_signed_claim_fingerprint, envelope.source_coverage_schema, envelope.source_coverage_fingerprint].some((value) => value !== null)) {
      throw new TypeError("unknown source metadata must be null");
    }
    requireExact(envelope.summary, SUMMARY_KEYS, "summary");
    requireExact(envelope.lineage, LINEAGE_KEYS, "lineage");
    validateFacts(envelope.facts, positive);
    validateAuthority(envelope.authority);
    if (!Array.isArray(envelope.blockers) || envelope.blockers.length === 0 || envelope.blockers.some((item) => typeof item !== "string" || !item)) throw new TypeError("blockers invalid");
    const axes = validateAxes(envelope.axes, positive);
    if (positive) {
      for (const key of ["assertion_leaf_index", "checkpoint_tree_size", "coverage_end_tree_size", "coverage_evaluation_count", "coverage_start_tree_size", "maximum_reference_time_gap_ms", "reference_time_ms_claim", "scan_completed_at_ms_claim"]) if (!isInteger(envelope.summary[key])) throw new TypeError("positive summary integers invalid");
      if (!isHash(envelope.summary.assertion_receipt_hash)) throw new TypeError("positive summary hash invalid");
      for (const key of ["replay_registry_id", "occurrence_provider_id", "time_authority_id"]) if (typeof envelope.summary[key] !== "string" || !envelope.summary[key]) throw new TypeError("positive summary identity invalid");
      for (const key of LINEAGE_KEYS) if (!isHash(envelope.lineage[key])) throw new TypeError("positive lineage hash invalid");
    } else {
      if (SUMMARY_KEYS.some((key) => envelope.summary[key] !== null) || LINEAGE_KEYS.some((key) => envelope.lineage[key] !== null)) throw new TypeError("unknown evidence fields must be null");
    }
    return { positive: positive, axes: axes };
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 12) + "..." + value.slice(-6) : "UNKNOWN";
  }

  function buildProviderIdentityClaimCoverageModelV1(envelope) {
    const validated = validateEnvelope(envelope);
    const summary = envelope.summary;
    return Object.freeze({
      displayState: envelope.display_state,
      statusLabel: validated.positive ? "SIGNED CLAIMS / TRUST OPEN" : "EVIDENCE UNKNOWN",
      axes: validated.axes,
      registry: validated.positive ? summary.replay_registry_id : "UNKNOWN",
      assertion: validated.positive ? shortHash(summary.assertion_receipt_hash) : "UNKNOWN",
      leafIndex: validated.positive ? summary.assertion_leaf_index : null,
      checkpointTreeSize: validated.positive ? summary.checkpoint_tree_size : null,
      coverageRange: validated.positive ? summary.coverage_start_tree_size + " to " + summary.coverage_end_tree_size : "UNKNOWN",
      evaluationCount: validated.positive ? summary.coverage_evaluation_count : null,
      maximumReferenceGapMs: validated.positive ? summary.maximum_reference_time_gap_ms : null,
      occurrenceProvider: validated.positive ? summary.occurrence_provider_id : "UNKNOWN",
      timeAuthority: validated.positive ? summary.time_authority_id : "UNKNOWN",
      blockers: Object.freeze(envelope.blockers.slice()),
      permissionLabel: "DESCRIPTIVE RESEARCH ONLY"
    });
  }

  function createElement(documentRef, tag, className, text) {
    const node = documentRef.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function createProviderIdentityClaimCoverageCardV1(envelope, documentRef) {
    const doc = documentRef || (typeof document !== "undefined" ? document : null);
    if (!doc || typeof doc.createElement !== "function") throw new TypeError("document.createElement is required");
    const model = buildProviderIdentityClaimCoverageModelV1(envelope);
    const root = createElement(doc, "article", "pif-coverage-card");
    root.dataset.state = model.displayState;
    const header = createElement(doc, "header", "pif-coverage-card__header");
    const heading = createElement(doc, "div", "pif-coverage-card__heading");
    heading.appendChild(createElement(doc, "p", "pif-coverage-card__kicker", "PROVIDER IDENTITY / DETACHED DOSSIER"));
    heading.appendChild(createElement(doc, "h2", "pif-coverage-card__title", "Claim Coverage Ledger"));
    heading.appendChild(createElement(doc, "p", "pif-coverage-card__subtitle", "Signed occurrence claims mapped against a bounded checkpoint prefix."));
    header.appendChild(heading);
    header.appendChild(createElement(doc, "div", "pif-coverage-card__stamp", model.statusLabel));
    root.appendChild(header);
    const rail = createElement(doc, "section", "pif-coverage-card__rail");
    const railCopy = createElement(doc, "div", "pif-coverage-card__rail-copy");
    railCopy.appendChild(createElement(doc, "span", "pif-coverage-card__micro", "OBSERVED PREFIX"));
    railCopy.appendChild(createElement(doc, "strong", "pif-coverage-card__range", model.coverageRange));
    railCopy.appendChild(createElement(doc, "span", "pif-coverage-card__rail-note", model.evaluationCount === null ? "No verified window" : model.evaluationCount + " consecutive signed claims"));
    rail.appendChild(railCopy);
    const track = createElement(doc, "div", "pif-coverage-card__track");
    const count = Math.max(0, Math.min(model.evaluationCount || 0, 12));
    for (let index = 0; index < count; index += 1) {
      const mark = createElement(doc, "span", "pif-coverage-card__mark", String(index + 1));
      mark.dataset.index = String(index + 1);
      track.appendChild(mark);
    }
    rail.appendChild(track);
    root.appendChild(rail);
    const identity = createElement(doc, "section", "pif-coverage-card__identity");
    for (const pair of [["REGISTRY", model.registry], ["ASSERTION", model.assertion], ["LEAF", model.leafIndex === null ? "UNKNOWN" : model.leafIndex], ["MAX GAP", model.maximumReferenceGapMs === null ? "UNKNOWN" : model.maximumReferenceGapMs + " ms"]]) {
      const cell = createElement(doc, "div", "pif-coverage-card__identity-cell");
      cell.appendChild(createElement(doc, "span", "pif-coverage-card__micro", pair[0]));
      cell.appendChild(createElement(doc, "strong", "pif-coverage-card__identity-value", pair[1]));
      identity.appendChild(cell);
    }
    root.appendChild(identity);
    const axes = createElement(doc, "section", "pif-coverage-card__axes");
    for (const axis of model.axes) {
      const panel = createElement(doc, "article", "pif-coverage-card__axis pif-coverage-card__axis--" + axis.axis.toLowerCase());
      panel.appendChild(createElement(doc, "span", "pif-coverage-card__axis-index", String(axis.ordinal).padStart(2, "0")));
      panel.appendChild(createElement(doc, "span", "pif-coverage-card__micro", axis.axis));
      panel.appendChild(createElement(doc, "strong", "pif-coverage-card__axis-state", axis.state));
      panel.appendChild(createElement(doc, "h3", "pif-coverage-card__axis-title", axis.headline));
      panel.appendChild(createElement(doc, "p", "pif-coverage-card__axis-detail", axis.detail));
      axes.appendChild(panel);
    }
    root.appendChild(axes);
    const footer = createElement(doc, "footer", "pif-coverage-card__footer");
    footer.appendChild(createElement(doc, "p", "pif-coverage-card__witnesses", "OCCURRENCE: " + model.occurrenceProvider + " / TIME: " + model.timeAuthority));
    footer.appendChild(createElement(doc, "strong", "pif-coverage-card__permission", model.permissionLabel));
    root.appendChild(footer);
    return root;
  }

  return Object.freeze({
    buildProviderIdentityClaimCoverageModelV1: buildProviderIdentityClaimCoverageModelV1,
    createProviderIdentityClaimCoverageCardV1: createProviderIdentityClaimCoverageCardV1,
    constants: constants,
    contractTestHooks: Object.freeze({ exactKeys: exactKeys, validateAuthority: validateAuthority, validateAxes: validateAxes, validateEnvelope: validateEnvelope })
  });
});
