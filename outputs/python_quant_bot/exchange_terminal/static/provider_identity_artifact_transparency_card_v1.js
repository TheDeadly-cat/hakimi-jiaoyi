(function (root, factory) {
  const strictJson = typeof module === "object" && module.exports
    ? require("./strict_canonical_json_v1.js")
    : root.HakimiStrictCanonicalJsonV1;
  const api = factory(strictJson);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HakimiProviderIdentityArtifactTransparencyCardV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictJson) {
  "use strict";

  const constants = Object.freeze({
    AXIS_ORDER: Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]),
    ENVELOPE_SCHEMA: "provider-identity-artifact-transparency-presentation-envelope-v1",
    ENVELOPE_FINGERPRINT: "20260822-provider-identity-artifact-transparency-presentation-envelope-1",
    DISPLAY_STATE: "LOCAL_ARTIFACTS_AND_SIGNED_RETRIEVAL_CLAIMS_BOUND_EXTERNAL_AVAILABILITY_GAP",
    SOURCE_SCHEMA: "provider-identity-artifact-transparency-availability-evaluation-v1",
    SOURCE_FINGERPRINT: "20260822-provider-identity-artifact-transparency-availability-contract-1"
  });

  const TOP_KEYS = Object.freeze(["authority", "axes", "axis_order", "blockers", "display_state", "facts", "lineage", "presentation_hash", "presentation_status", "schema_version", "source_evaluation_fingerprint", "source_evaluation_schema", "static_fingerprint", "summary"]);
  const AXIS_KEYS = Object.freeze(["axis", "detail", "headline", "signal", "state"]);
  const SUMMARY_KEYS = Object.freeze(["artifact_count", "checkpoint_tree_size", "observer_count", "signed_retrieval_claim_count", "total_payload_bytes", "verified_inclusion_count"]);
  const LINEAGE_KEYS = Object.freeze(["artifact_catalog_root_hash", "observer_a_receipt_hash", "observer_b_receipt_hash", "observer_result_transcript_root_hash", "registration_receipt_hash", "source_evaluation_receipt_hash", "transparency_checkpoint_hash", "transparency_checkpoint_root_hash"]);
  const FACT_KEYS = Object.freeze(["append_only_consistency_verified", "catalog_scope_verified", "dual_observer_claims_verified", "dual_observer_result_agreement_verified", "external_log_trust_verified", "external_persistence_verified", "external_time_truth_verified", "inclusion_set_verified", "local_artifact_content_verified", "observer_independence_verified", "profitability_verified", "public_availability_verified", "result_available", "signed_checkpoint_verified", "source_evaluation_verified"]);
  const AUTHORITY_KEYS = Object.freeze(["artifact_promotion_allowed", "current_admission_allowed", "current_pointer_written", "descriptive_only", "live_order_allowed", "paper_authorized", "parameter_selection_allowed", "public_availability_promotion_allowed"]);
  const POSITIVE_FACTS = Object.freeze(["append_only_consistency_verified", "catalog_scope_verified", "dual_observer_claims_verified", "dual_observer_result_agreement_verified", "inclusion_set_verified", "local_artifact_content_verified", "result_available", "signed_checkpoint_verified", "source_evaluation_verified"]);
  const EXTERNAL_FACTS = Object.freeze(["external_log_trust_verified", "external_persistence_verified", "external_time_truth_verified", "observer_independence_verified", "profitability_verified", "public_availability_verified"]);
  const HASH_RE = /^[0-9a-f]{64}$/;

  function exactKeys(value, expected) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value).sort();
    return keys.length === expected.length && keys.every((key, index) => key === expected[index]);
  }

  function requireExact(value, expected, label) {
    if (!exactKeys(value, expected)) throw new TypeError(label + " fields are not exact");
  }

  function isHash(value) {
    return typeof value === "string" && HASH_RE.test(value);
  }

  function isInteger(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function validateAuthority(authority) {
    requireExact(authority, AUTHORITY_KEYS, "authority");
    for (const key of AUTHORITY_KEYS) {
      const expected = key === "descriptive_only";
      if (authority[key] !== expected) throw new TypeError("authority must remain descriptive and locked");
    }
  }

  function validateFacts(facts, positive) {
    requireExact(facts, FACT_KEYS, "facts");
    for (const key of FACT_KEYS) if (typeof facts[key] !== "boolean") throw new TypeError("fact values must be boolean");
    if (positive) {
      for (const key of POSITIVE_FACTS) if (facts[key] !== true) throw new TypeError("positive local facts are incomplete");
    } else if (FACT_KEYS.some((key) => facts[key] !== false)) {
      throw new TypeError("unknown facts must remain false");
    }
    for (const key of EXTERNAL_FACTS) if (facts[key] !== false) throw new TypeError("external facts must remain unverified");
  }

  function validateAxes(axes, positive) {
    if (!Array.isArray(axes) || axes.length !== constants.AXIS_ORDER.length) throw new TypeError("axes must be complete");
    return axes.map((axis, index) => {
      requireExact(axis, AXIS_KEYS, "axis");
      if (axis.axis !== constants.AXIS_ORDER[index]) throw new TypeError("axis order mismatch");
      for (const key of AXIS_KEYS) if (typeof axis[key] !== "string" || !axis[key]) throw new TypeError("axis values must be nonempty strings");
      if (!positive && (axis.state !== "UNKNOWN" || axis.signal !== "UNKNOWN")) throw new TypeError("unknown axes must fail closed");
      return Object.freeze(Object.assign({}, axis, { ordinal: index + 1 }));
    });
  }

  function validateEnvelope(envelope, expectedPresentationHash) {
    requireExact(envelope, TOP_KEYS, "envelope");
    if (!isHash(expectedPresentationHash)) throw new TypeError("expected presentation hash is required");
    if (envelope.schema_version !== constants.ENVELOPE_SCHEMA || envelope.static_fingerprint !== constants.ENVELOPE_FINGERPRINT) throw new TypeError("envelope contract mismatch");
    if (envelope.presentation_status !== "UNMOUNTED_CANDIDATE" || !isHash(envelope.presentation_hash)) throw new TypeError("presentation seal metadata invalid");
    if (envelope.presentation_hash !== expectedPresentationHash) throw new TypeError("expected presentation hash mismatch");
    if (!strictJson || typeof strictJson.verifySealedDocument !== "function") throw new TypeError("strict canonical verifier is required");
    if (!strictJson.verifySealedDocument(envelope, "presentation_hash")) throw new TypeError("presentation hash mismatch");
    if (!Array.isArray(envelope.axis_order) || envelope.axis_order.join("|") !== constants.AXIS_ORDER.join("|")) throw new TypeError("axis_order mismatch");
    const positive = envelope.display_state === constants.DISPLAY_STATE;
    if (!positive && envelope.display_state !== "UNKNOWN") throw new TypeError("display_state invalid");
    if (positive) {
      if (envelope.source_evaluation_schema !== constants.SOURCE_SCHEMA || envelope.source_evaluation_fingerprint !== constants.SOURCE_FINGERPRINT) throw new TypeError("source contract mismatch");
    } else if (envelope.source_evaluation_schema !== null || envelope.source_evaluation_fingerprint !== null) {
      throw new TypeError("unknown source metadata must be null");
    }
    requireExact(envelope.summary, SUMMARY_KEYS, "summary");
    requireExact(envelope.lineage, LINEAGE_KEYS, "lineage");
    validateFacts(envelope.facts, positive);
    validateAuthority(envelope.authority);
    if (!Array.isArray(envelope.blockers) || envelope.blockers.length === 0 || envelope.blockers.some((item) => typeof item !== "string" || !item)) throw new TypeError("blockers invalid");
    const axes = validateAxes(envelope.axes, positive);
    if (positive) {
      for (const key of SUMMARY_KEYS) if (!isInteger(envelope.summary[key])) throw new TypeError("positive summary integers invalid");
      if (envelope.summary.artifact_count < 1 || envelope.summary.observer_count !== 2) throw new TypeError("artifact and observer scope invalid");
      if (envelope.summary.checkpoint_tree_size < envelope.summary.artifact_count) throw new TypeError("checkpoint scope invalid");
      if (envelope.summary.verified_inclusion_count !== envelope.summary.artifact_count) throw new TypeError("inclusion count drift");
      if (envelope.summary.signed_retrieval_claim_count !== envelope.summary.artifact_count * envelope.summary.observer_count) throw new TypeError("retrieval claim count drift");
      for (const key of LINEAGE_KEYS) if (!isHash(envelope.lineage[key])) throw new TypeError("positive lineage hash invalid");
      if (envelope.lineage.observer_a_receipt_hash === envelope.lineage.observer_b_receipt_hash) throw new TypeError("observer receipts must remain distinct");
    } else {
      if (SUMMARY_KEYS.some((key) => envelope.summary[key] !== null) || LINEAGE_KEYS.some((key) => envelope.lineage[key] !== null)) throw new TypeError("unknown evidence fields must be null");
    }
    return { positive: positive, axes: axes };
  }

  function shortHash(value) {
    return isHash(value) ? value.slice(0, 10) + "..." + value.slice(-6) : "UNKNOWN";
  }

  function buildProviderIdentityArtifactTransparencyModelV1(envelope, expectedPresentationHash) {
    const validated = validateEnvelope(envelope, expectedPresentationHash);
    const summary = envelope.summary;
    const lineage = envelope.lineage;
    return Object.freeze({
      displayState: envelope.display_state,
      statusLabel: validated.positive ? "LOCAL EVIDENCE / EXTERNAL GAP" : "EVIDENCE UNKNOWN",
      axes: validated.axes,
      artifactCount: validated.positive ? summary.artifact_count : null,
      payloadBytes: validated.positive ? summary.total_payload_bytes : null,
      checkpointTreeSize: validated.positive ? summary.checkpoint_tree_size : null,
      inclusionCount: validated.positive ? summary.verified_inclusion_count : null,
      observerCount: validated.positive ? summary.observer_count : null,
      retrievalClaimCount: validated.positive ? summary.signed_retrieval_claim_count : null,
      catalog: validated.positive ? shortHash(lineage.artifact_catalog_root_hash) : "UNKNOWN",
      checkpoint: validated.positive ? shortHash(lineage.transparency_checkpoint_root_hash) : "UNKNOWN",
      observerA: validated.positive ? shortHash(lineage.observer_a_receipt_hash) : "UNKNOWN",
      observerB: validated.positive ? shortHash(lineage.observer_b_receipt_hash) : "UNKNOWN",
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

  function createProviderIdentityArtifactTransparencyCardV1(envelope, documentRef, expectedPresentationHash) {
    const doc = documentRef || (typeof document !== "undefined" ? document : null);
    if (!doc || typeof doc.createElement !== "function") throw new TypeError("document.createElement is required");
    const model = buildProviderIdentityArtifactTransparencyModelV1(envelope, expectedPresentationHash);
    const root = createElement(doc, "article", "pia-transparency-card");
    root.dataset.state = model.displayState;

    const header = createElement(doc, "header", "pia-transparency-card__header");
    const heading = createElement(doc, "div", "pia-transparency-card__heading");
    heading.appendChild(createElement(doc, "p", "pia-transparency-card__kicker", "ARTIFACT TRANSPARENCY / DETACHED OBSERVATORY"));
    heading.appendChild(createElement(doc, "h2", "pia-transparency-card__title", "Availability Evidence Plate"));
    heading.appendChild(createElement(doc, "p", "pia-transparency-card__subtitle", "Local payload integrity and signed retrieval claims, separated from public availability."));
    header.appendChild(heading);
    header.appendChild(createElement(doc, "div", "pia-transparency-card__stamp", model.statusLabel));
    root.appendChild(header);

    const observatory = createElement(doc, "section", "pia-transparency-card__observatory");
    const artifactField = createElement(doc, "div", "pia-transparency-card__artifacts");
    artifactField.appendChild(createElement(doc, "span", "pia-transparency-card__micro", "CATALOG SCOPE"));
    const bars = createElement(doc, "div", "pia-transparency-card__bars");
    const artifactCount = Math.max(0, Math.min(model.artifactCount || 0, 12));
    for (let index = 0; index < artifactCount; index += 1) {
      const bar = createElement(doc, "span", "pia-transparency-card__bar", String(index + 1));
      bar.dataset.index = String(index + 1);
      bars.appendChild(bar);
    }
    artifactField.appendChild(bars);
    observatory.appendChild(artifactField);
    const checkpoint = createElement(doc, "div", "pia-transparency-card__checkpoint");
    checkpoint.appendChild(createElement(doc, "span", "pia-transparency-card__micro", "SIGNED CHECKPOINT"));
    checkpoint.appendChild(createElement(doc, "strong", "pia-transparency-card__checkpoint-size", model.checkpointTreeSize === null ? "UNKNOWN" : "TREE " + model.checkpointTreeSize));
    checkpoint.appendChild(createElement(doc, "span", "pia-transparency-card__hash", model.checkpoint));
    observatory.appendChild(checkpoint);
    const observers = createElement(doc, "div", "pia-transparency-card__observers");
    for (const pair of [["A", model.observerA], ["B", model.observerB]]) {
      const observer = createElement(doc, "div", "pia-transparency-card__observer");
      observer.appendChild(createElement(doc, "span", "pia-transparency-card__observer-mark", pair[0]));
      observer.appendChild(createElement(doc, "span", "pia-transparency-card__hash", pair[1]));
      observers.appendChild(observer);
    }
    observatory.appendChild(observers);
    root.appendChild(observatory);

    const metrics = createElement(doc, "section", "pia-transparency-card__metrics");
    for (const pair of [
      ["ARTIFACTS", model.artifactCount],
      ["LOCAL BYTES", model.payloadBytes],
      ["INCLUSIONS", model.inclusionCount],
      ["OBSERVERS", model.observerCount],
      ["SIGNED CLAIMS", model.retrievalClaimCount],
      ["CATALOG", model.catalog]
    ]) {
      const metric = createElement(doc, "div", "pia-transparency-card__metric");
      metric.appendChild(createElement(doc, "span", "pia-transparency-card__micro", pair[0]));
      metric.appendChild(createElement(doc, "strong", "pia-transparency-card__metric-value", pair[1] === null ? "UNKNOWN" : pair[1]));
      metrics.appendChild(metric);
    }
    root.appendChild(metrics);

    const axes = createElement(doc, "section", "pia-transparency-card__axes");
    for (const axis of model.axes) {
      const panel = createElement(doc, "article", "pia-transparency-card__axis pia-transparency-card__axis--" + axis.axis.toLowerCase());
      panel.appendChild(createElement(doc, "span", "pia-transparency-card__axis-index", String(axis.ordinal).padStart(2, "0")));
      panel.appendChild(createElement(doc, "span", "pia-transparency-card__micro", axis.axis));
      panel.appendChild(createElement(doc, "strong", "pia-transparency-card__axis-state", axis.state));
      panel.appendChild(createElement(doc, "h3", "pia-transparency-card__axis-title", axis.headline));
      panel.appendChild(createElement(doc, "p", "pia-transparency-card__axis-detail", axis.detail));
      axes.appendChild(panel);
    }
    root.appendChild(axes);

    const footer = createElement(doc, "footer", "pia-transparency-card__footer");
    footer.appendChild(createElement(doc, "p", "pia-transparency-card__gap", "PUBLIC LOG / NETWORK RETRIEVAL / PERSISTENCE: UNPROVEN"));
    footer.appendChild(createElement(doc, "strong", "pia-transparency-card__permission", model.permissionLabel));
    root.appendChild(footer);
    return root;
  }

  return Object.freeze({
    buildProviderIdentityArtifactTransparencyModelV1: buildProviderIdentityArtifactTransparencyModelV1,
    createProviderIdentityArtifactTransparencyCardV1: createProviderIdentityArtifactTransparencyCardV1,
    constants: constants,
    contractTestHooks: Object.freeze({ exactKeys: exactKeys, validateAuthority: validateAuthority, validateAxes: validateAxes, validateEnvelope: validateEnvelope })
  });
});
