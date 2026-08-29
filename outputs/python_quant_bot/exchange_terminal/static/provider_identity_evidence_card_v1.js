(function attachProviderIdentityEvidenceCardV1(root, factory) {
  const strictJson =
    typeof module === "object" && module.exports
      ? require("./strict_canonical_json_v1.js")
      : root.HakimiStrictCanonicalJsonV1 ||
        root.StrictCanonicalJsonV1 ||
        root.strictCanonicalJsonV1;
  const api = factory(strictJson);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.ProviderIdentityEvidenceCardV1 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function providerIdentityFactory(strictJson) {
  "use strict";

  if (!strictJson) {
    throw new Error("strict canonical JSON dependency is required");
  }

  const ENVELOPE_SCHEMA =
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-presentation-envelope-v1";
  const ENVELOPE_FINGERPRINT =
    "20260925-cross-lag-factor-calibration-long-horizon-provider-identity-presentation-envelope-1";
  const SOURCE_SCHEMA =
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-verification-candidate-v1";
  const SOURCE_FINGERPRINT =
    "20260924-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-verifier-1";
  const SOURCE_STATE =
    "IDENTITY_ASSERTION_SIGNATURE_AND_MEMBERSHIP_VERIFIED_EXTERNAL_TRUST_UNPROVEN";
  const DISPLAY_STATE = "CRYPTOGRAPHIC_PROOF_BOUND_EXTERNAL_TRUST_GAP";
  const AXIS_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  const AXIS_STATES = [
    "CRYPTOGRAPHIC_PROOF_BOUND",
    "EXTERNAL_TRUST_TIME_REPLAY_UNPROVEN",
    "DETACHED_CANDIDATE",
    "LOCKED",
  ];
  const VERIFIED_BLOCKERS = [
    "IDENTITY_REGISTRY_TRUST_ROOT_NOT_EXTERNALLY_ATTESTED",
    "IDENTITY_ASSERTION_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "IDENTITY_ASSERTION_REPLAY_REGISTRY_NOT_CHECKED",
    "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
    "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
  ];
  const TOP_LEVEL_KEYS = [
    "authority",
    "axes",
    "axis_order",
    "blockers",
    "display_state",
    "facts",
    "lineage",
    "presentation_hash",
    "presentation_status",
    "schema_version",
    "source_schema_version",
    "source_state",
    "source_static_fingerprint",
    "source_verification_state",
    "static_fingerprint",
    "summary",
  ];
  const AUTHORITY_KEYS = [
    "current_admission_allowed",
    "current_pointer_written",
    "descriptive_only",
    "live_order_allowed",
    "paper_authorized",
    "profitability_claim_allowed",
    "provider_identity_admission_allowed",
  ];
  const FACT_KEYS = [
    "cryptographic_identity_assertion_verified",
    "external_identity_registry_authenticity_proven",
    "external_registration_time_verified",
    "provider_identity_verified",
    "replay_registry_checked",
    "result_available",
    "source_assertion_verification_verified",
  ];
  const LINEAGE_KEYS = [
    "assertion_content_sha256",
    "assertion_hash",
    "identity_registry_snapshot_sha256",
    "identity_registry_trust_root_sha256",
    "membership_proof_hash",
    "provider_identity_document_sha256",
    "provider_receipt_trust_root_sha256",
    "source_provider_identity_registration_hash",
    "source_verification_hash",
  ];
  const SUMMARY_KEYS = [
    "asserted_at_utc",
    "assertion_id",
    "identity_registry_id",
    "identity_registry_snapshot_id",
    "membership_leaf_index",
    "membership_proof_count",
    "membership_tree_size",
    "provider_id",
    "provider_subject_id",
    "valid_until_utc",
  ];
  const AXIS_KEYS = ["axis", "detail", "headline", "signal", "state"];
  const SHA256 = /^[0-9a-f]{64}$/;

  function fail(message) {
    throw new TypeError(message);
  }

  function exactKeys(value, expected, label) {
    if (!strictJson.isPlainRecord(value)) fail(`${label} must be a plain record`);
    const actual = Object.keys(value).sort();
    const wanted = expected.slice().sort();
    if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
      fail(`${label} fields are not exact`);
    }
  }

  function exactArray(actual, expected, label) {
    if (!Array.isArray(actual) || actual.length !== expected.length) fail(`${label} is invalid`);
    if (actual.some((value, index) => value !== expected[index])) fail(`${label} order drifted`);
  }

  function allStrings(value, found) {
    if (typeof value === "string") found.push(value);
    else if (Array.isArray(value)) value.forEach((item) => allStrings(item, found));
    else if (strictJson.isPlainRecord(value)) Object.values(value).forEach((item) => allStrings(item, found));
    return found;
  }

  function validateAuthority(authority) {
    exactKeys(authority, AUTHORITY_KEYS, "authority");
    AUTHORITY_KEYS.forEach((key) => {
      if (typeof authority[key] !== "boolean") fail(`authority.${key} must be boolean`);
      const expected = key === "descriptive_only";
      if (authority[key] !== expected) fail(`authority.${key} is not locked`);
    });
  }

  function validateFacts(facts, positive) {
    exactKeys(facts, FACT_KEYS, "facts");
    FACT_KEYS.forEach((key) => {
      if (typeof facts[key] !== "boolean") fail(`facts.${key} must be boolean`);
    });
    const trueKeys = positive
      ? ["cryptographic_identity_assertion_verified", "source_assertion_verification_verified"]
      : [];
    FACT_KEYS.forEach((key) => {
      if (facts[key] !== trueKeys.includes(key)) fail(`facts.${key} drifted`);
    });
  }

  function validateAxes(axes, positive) {
    if (!Array.isArray(axes) || axes.length !== AXIS_ORDER.length) fail("axes length is invalid");
    axes.forEach((axis, index) => {
      exactKeys(axis, AXIS_KEYS, `axes[${index}]`);
      if (axis.axis !== AXIS_ORDER[index]) fail("axis order drifted");
      const expectedState = positive ? AXIS_STATES[index] : "UNKNOWN";
      if (axis.state !== expectedState) fail("axis state drifted");
      ["detail", "headline", "signal"].forEach((key) => {
        if (typeof axis[key] !== "string" || !axis[key]) fail(`axis ${key} is invalid`);
      });
    });
  }

  function validateSummary(summary, positive) {
    exactKeys(summary, SUMMARY_KEYS, "summary");
    const textKeys = [
      "asserted_at_utc",
      "assertion_id",
      "identity_registry_id",
      "identity_registry_snapshot_id",
      "provider_id",
      "provider_subject_id",
      "valid_until_utc",
    ];
    const countKeys = ["membership_leaf_index", "membership_proof_count", "membership_tree_size"];
    textKeys.forEach((key) => {
      const value = summary[key];
      if (positive && (typeof value !== "string" || !value)) fail(`summary.${key} is invalid`);
      if (!positive && value !== null && (typeof value !== "string" || !value)) fail(`summary.${key} is invalid`);
    });
    countKeys.forEach((key) => {
      const value = summary[key];
      if (positive && (!Number.isSafeInteger(value) || value < 0)) fail(`summary.${key} is invalid`);
      if (!positive && value !== null && (!Number.isSafeInteger(value) || value < 0)) fail(`summary.${key} is invalid`);
    });
    const populatedCounts = countKeys.filter((key) => summary[key] !== null).length;
    if (!positive && populatedCounts !== 0 && populatedCounts !== countKeys.length) {
      fail("unknown membership aggregates are partially populated");
    }
    if (!positive && populatedCounts === 0) return;
    const size = summary.membership_tree_size;
    if (size < 1 || (size & (size - 1)) !== 0) fail("membership tree size is invalid");
    if (summary.membership_leaf_index >= size) fail("membership leaf index is invalid");
    if (summary.membership_proof_count !== Math.log2(size)) fail("membership proof count drifted");
  }

  function validateLineage(lineage, positive) {
    exactKeys(lineage, LINEAGE_KEYS, "lineage");
    LINEAGE_KEYS.forEach((key) => {
      const value = lineage[key];
      if (positive && !SHA256.test(value)) fail(`lineage.${key} is invalid`);
      if (!positive && value !== null && !SHA256.test(value)) fail(`lineage.${key} is invalid`);
    });
  }

  function buildProviderIdentityPresentationModelV1(envelope) {
    exactKeys(envelope, TOP_LEVEL_KEYS, "envelope");
    if (!strictJson.verifySealedDocument(envelope, "presentation_hash")) fail("presentation hash is invalid");
    if (envelope.schema_version !== ENVELOPE_SCHEMA) fail("envelope schema is unsupported");
    if (envelope.static_fingerprint !== ENVELOPE_FINGERPRINT) fail("envelope fingerprint drifted");
    if (envelope.presentation_status !== "UNMOUNTED_CANDIDATE") fail("presentation status drifted");
    exactArray(envelope.axis_order, AXIS_ORDER, "axis_order");
    validateAuthority(envelope.authority);

    const positive = envelope.display_state === DISPLAY_STATE;
    if (!positive && envelope.display_state !== "UNKNOWN") fail("display state is unsupported");
    validateSummary(envelope.summary, positive);
    validateLineage(envelope.lineage, positive);
    validateFacts(envelope.facts, positive);
    validateAxes(envelope.axes, positive);
    if (positive) {
      if (envelope.source_schema_version !== SOURCE_SCHEMA) fail("source schema drifted");
      if (envelope.source_static_fingerprint !== SOURCE_FINGERPRINT) fail("source fingerprint drifted");
      if (envelope.source_state !== "VERIFIED") fail("source state drifted");
      if (envelope.source_verification_state !== SOURCE_STATE) fail("source verification state drifted");
      exactArray(envelope.blockers, VERIFIED_BLOCKERS, "blockers");
    } else if (!Array.isArray(envelope.blockers) || envelope.blockers.length !== 1) {
      fail("unknown blocker is invalid");
    }

    const unsafe = /\bREADY\b|\bPROFIT(?:ABILITY)?\b|\bBUY\b|\bSELL\b/i;
    if (allStrings(envelope, []).some((value) => unsafe.test(value))) fail("promotional copy is forbidden");

    const textOrUnknown = (value) => (typeof value === "string" && value ? value : "UNKNOWN");
    const proofKnown = [
      envelope.summary.membership_leaf_index,
      envelope.summary.membership_proof_count,
      envelope.summary.membership_tree_size,
    ].every((value) => Number.isSafeInteger(value));
    return {
      axes: envelope.axes.map((axis, index) => ({ ...axis, ordinal: index + 1 })),
      blockers: envelope.blockers.slice(),
      displayState: envelope.display_state,
      identity: {
        assertion: textOrUnknown(envelope.summary.assertion_id),
        provider: textOrUnknown(envelope.summary.provider_id),
        registry: textOrUnknown(envelope.summary.identity_registry_id),
        snapshot: textOrUnknown(envelope.summary.identity_registry_snapshot_id),
        subject: textOrUnknown(envelope.summary.provider_subject_id),
      },
      proof: {
        index: proofKnown ? envelope.summary.membership_leaf_index : null,
        known: proofKnown,
        nodes: proofKnown ? envelope.summary.membership_proof_count : null,
        treeSize: proofKnown ? envelope.summary.membership_tree_size : null,
      },
      statusLabel: positive ? "TRUST GAP RECORDED" : "EVIDENCE UNKNOWN",
      timeWindow: `${textOrUnknown(envelope.summary.asserted_at_utc)} / ${textOrUnknown(envelope.summary.valid_until_utc)}`,
    };
  }

  function createTextNode(documentRef, tagName, className, text) {
    const node = documentRef.createElement(tagName);
    node.className = className;
    node.textContent = String(text);
    return node;
  }

  function createProviderIdentityEvidenceCardV1(envelope, options) {
    const settings = options || {};
    const documentRef = settings.document || (typeof document !== "undefined" ? document : null);
    if (!documentRef || typeof documentRef.createElement !== "function") fail("document.createElement is required");
    const model = buildProviderIdentityPresentationModelV1(envelope);
    const card = documentRef.createElement("section");
    card.className = "pirl1-card";
    card.setAttribute("aria-label", "Provider identity evidence dossier");

    const header = documentRef.createElement("header");
    header.className = "pirl1-header";
    const heading = documentRef.createElement("div");
    heading.className = "pirl1-heading";
    heading.append(
      createTextNode(documentRef, "p", "pirl1-kicker", "IDENTITY / ASSERTION DOSSIER"),
      createTextNode(documentRef, "h2", "pirl1-title", "Registry proof, external trust pending"),
      createTextNode(
        documentRef,
        "p",
        "pirl1-deck",
        "A cryptographic membership record separated from provider identity authority."
      )
    );
    header.append(
      heading,
      createTextNode(documentRef, "span", "pirl1-status", model.statusLabel)
    );

    const identity = documentRef.createElement("dl");
    identity.className = "pirl1-identity";
    [
      ["PROVIDER", model.identity.provider],
      ["SUBJECT", model.identity.subject],
      ["REGISTRY", model.identity.registry],
      ["SNAPSHOT", model.identity.snapshot],
    ].forEach(([label, value]) => {
      const cell = documentRef.createElement("div");
      cell.className = "pirl1-identity-cell";
      cell.append(
        createTextNode(documentRef, "dt", "pirl1-label", label),
        createTextNode(documentRef, "dd", "pirl1-value", value)
      );
      identity.append(cell);
    });

    const route = documentRef.createElement("ol");
    route.className = "pirl1-route";
    model.axes.forEach((axis) => {
      const stop = documentRef.createElement("li");
      stop.className = `pirl1-stop pirl1-stop-${axis.axis.toLowerCase()}`;
      stop.setAttribute("data-state", axis.state);
      stop.append(
        createTextNode(documentRef, "span", "pirl1-ordinal", String(axis.ordinal).padStart(2, "0")),
        createTextNode(documentRef, "span", "pirl1-axis", axis.axis),
        createTextNode(documentRef, "strong", "pirl1-headline", axis.headline),
        createTextNode(documentRef, "p", "pirl1-detail", axis.detail),
        createTextNode(documentRef, "span", "pirl1-signal", axis.signal)
      );
      route.append(stop);
    });

    const proof = documentRef.createElement("aside");
    proof.className = "pirl1-proof";
    proof.append(
      createTextNode(documentRef, "span", "pirl1-proof-label", "MERKLE POSITION"),
      createTextNode(
        documentRef,
        "strong",
        "pirl1-proof-value",
        model.proof.known ? `${model.proof.index} / ${model.proof.treeSize - 1}` : "UNKNOWN"
      ),
      createTextNode(
        documentRef,
        "span",
        "pirl1-proof-meta",
        model.proof.known ? `${model.proof.nodes} proof nodes` : "proof aggregate unavailable"
      ),
      createTextNode(documentRef, "span", "pirl1-proof-time", model.timeWindow)
    );

    const footer = documentRef.createElement("footer");
    footer.className = "pirl1-footer";
    footer.append(
      createTextNode(documentRef, "span", "pirl1-footer-mark", "EXTERNAL TRUST OPEN"),
      createTextNode(
        documentRef,
        "p",
        "pirl1-footer-copy",
        "No provider identity admission, evaluation result, paper authority, or live authority."
      )
    );
    card.append(header, identity, route, proof, footer);
    return { element: card, model };
  }

  return {
    buildProviderIdentityPresentationModelV1,
    constants: {
      AXIS_ORDER: AXIS_ORDER.slice(),
      DISPLAY_STATE,
      ENVELOPE_FINGERPRINT,
      ENVELOPE_SCHEMA,
      SOURCE_FINGERPRINT,
      SOURCE_SCHEMA,
      SOURCE_STATE,
    },
    contractTestHooks: { exactKeys, validateAxes, validateAuthority },
    createProviderIdentityEvidenceCardV1,
  };
});
