(function initFactorCalibrationEvidenceCard(root, factory) {
  let strictJson = null;
  if (typeof module === "object" && module && module.exports) {
    strictJson = require("./strict_canonical_json_v1.js");
    module.exports = factory(strictJson);
  } else if (root && typeof root === "object") {
    strictJson = root.HakimiStrictCanonicalJsonV1;
    root.HakimiFactorCalibrationEvidenceCard = factory(strictJson);
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi(strictJson) {
  "use strict";

  const ENVELOPE_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-presentation-envelope-v1";
  const ENVELOPE_FINGERPRINT = "20260823-cross-lag-factor-calibration-presentation-envelope-1";
  const REPORT_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-report-consumer-verification-v1";
  const REPORT_FINGERPRINT = "20260823-cross-lag-factor-calibration-report-consumer-1";
  const MODEL_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-presentation-model-v1";
  const PRESENTATION_FINGERPRINT = "20260823-cross-lag-factor-calibration-g2-unmounted-presentation-1";
  const PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE";

  const ENVELOPE_KEYS = Object.freeze([
    "authority", "envelope_hash", "envelope_reason", "presentation_status",
    "report", "schema_version", "source_calibration_observations_hash",
    "source_registration_hash", "source_replay_hash", "source_report_hash",
    "source_schema_version", "source_state", "source_static_fingerprint",
    "static_fingerprint", "verification_state",
  ].sort());
  const REPORT_KEYS = Object.freeze([
    "authority", "blockers", "calibration_summary", "diagnostic_reason",
    "diagnostic_state", "facts", "gap_state", "maturity_state",
    "permission_state", "report_state", "schema_version",
    "source_calibration_observations_hash",
    "source_declared_calibration_receipt_hash",
    "source_registered_beta_ledger_hash", "source_registration_hash",
    "source_replay_hash", "source_replayed_beta_ledger_hash",
    "source_report_contract", "source_schema_version", "source_state",
    "source_static_fingerprint", "static_fingerprint", "verification_hash",
  ].sort());
  const FACT_KEYS = Object.freeze([
    "all_rows_at_or_before_calibration_cutoff",
    "beta_replay_matches_registration", "calibration_input_verified",
    "estimator_replayed", "external_calibration_timing_attested",
    "registration_calibration_receipt_g0_bound", "registration_v1_verified",
    "selection_after_calibration", "source_replay_verified",
  ].sort());
  const SUMMARY_KEYS = Object.freeze([
    "beta_abs_tolerance", "calibration_cutoff_date", "estimator",
    "first_observation_date", "identity_count", "intercept_policy",
    "last_observation_date", "max_abs_beta_error", "observation_count",
    "replay_decision", "selection_cutoff_date",
  ].sort());
  const REPORT_AUTHORITY_KEYS = Object.freeze([
    "calibration_receipt_attested", "candidate_activation_allowed",
    "current_admission_allowed", "current_pointer_written", "descriptive_only",
    "external_calibration_timing_attested", "factor_registration_formal",
    "live_order_allowed", "paper_authorized", "profitability_claim_allowed",
    "report_consumer_activated", "report_mounted",
  ].sort());
  const ENVELOPE_AUTHORITY_KEYS = Object.freeze([
    "candidate_activation_allowed", "current_admission_allowed",
    "current_pointer_written", "descriptive_only",
    "external_calibration_timing_attested", "live_order_allowed",
    "paper_authorized", "presentation_mounted", "profitability_claim_allowed",
    "report_consumer_activated", "source_semantics_replayed_in_browser",
  ].sort());
  const PRIVATE_KEYS = new Set([
    "beta_by_identity", "factor_id", "factor_return", "factor_source_hash",
    "identity_order", "returns_by_identity", "rows",
  ]);

  function exactKeys(value, expected) {
    return strictJson && strictJson.isPlainRecord(value)
      && JSON.stringify(Object.keys(value).sort()) === JSON.stringify(expected);
  }

  function strictHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function strictDate(value) {
    return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
  }

  function lockedAuthority(value, expectedKeys) {
    if (!exactKeys(value, expectedKeys) || value.descriptive_only !== true) return false;
    return expectedKeys.every((key) => key === "descriptive_only" || value[key] === false);
  }

  function collectKeys(value, output) {
    const keys = output || new Set();
    if (Array.isArray(value)) {
      value.forEach((item) => collectKeys(item, keys));
    } else if (strictJson && strictJson.isPlainRecord(value)) {
      Object.keys(value).forEach((key) => {
        keys.add(key);
        collectKeys(value[key], keys);
      });
    }
    return keys;
  }

  function containsPrivateKeys(value) {
    const keys = collectKeys(value);
    return [...PRIVATE_KEYS].some((key) => keys.has(key));
  }

  function validFacts(value, sourceObserved) {
    if (!exactKeys(value, FACT_KEYS)) return false;
    if (!FACT_KEYS.every((key) => typeof value[key] === "boolean")) return false;
    if (value.external_calibration_timing_attested !== false) return false;
    if (value.registration_calibration_receipt_g0_bound !== false) return false;
    return sourceObserved ? value.source_replay_verified === true : value.source_replay_verified === false;
  }

  function validSummary(summary, reportState) {
    if (!exactKeys(summary, SUMMARY_KEYS)) return false;
    if (!Number.isInteger(summary.observation_count) || summary.observation_count < 20) return false;
    if (!Number.isInteger(summary.identity_count) || summary.identity_count < 1) return false;
    if (![summary.first_observation_date, summary.last_observation_date,
      summary.calibration_cutoff_date, summary.selection_cutoff_date].every(strictDate)) return false;
    if (![summary.beta_abs_tolerance, summary.max_abs_beta_error,
      summary.estimator, summary.intercept_policy].every((value) => typeof value === "string" && value.length > 0)) return false;
    if (reportState === "OBSERVED_CALIBRATION_MATCH") return summary.replay_decision === "MATCH";
    if (reportState === "OBSERVED_CALIBRATION_BLOCK") return summary.replay_decision === "BLOCK";
    return false;
  }

  function verifyReport(report) {
    try {
      if (!strictJson || !exactKeys(report, REPORT_KEYS)) return false;
      if (!strictJson.verifySealedDocument(report, "verification_hash")) return false;
      if (report.schema_version !== REPORT_SCHEMA || report.static_fingerprint !== REPORT_FINGERPRINT) return false;
      if (report.permission_state !== "LOCKED") return false;
      if (!lockedAuthority(report.authority, REPORT_AUTHORITY_KEYS)) return false;
      if (!Array.isArray(report.blockers) || report.blockers.length === 0
        || !report.blockers.every((value) => typeof value === "string" && /^[A-Z0-9_]+$/.test(value))) return false;
      if (containsPrivateKeys(report)) return false;

      const observed = report.source_state === "OBSERVED";
      if (!validFacts(report.facts, observed)) return false;
      if (observed) {
        if (report.source_schema_version !== "strategy-correlation-cross-lag-factor-calibration-replay-candidate-v1") return false;
        if (report.source_static_fingerprint !== "20260823-cross-lag-factor-calibration-replay-1") return false;
        const hashes = [report.source_replay_hash, report.source_registration_hash,
          report.source_calibration_observations_hash,
          report.source_declared_calibration_receipt_hash,
          report.source_registered_beta_ledger_hash,
          report.source_replayed_beta_ledger_hash];
        if (!hashes.every(strictHash)) return false;
        if (!exactKeys(report.source_report_contract, ["activation_state", "schema_version"])) return false;
        if (report.source_report_contract.activation_state !== "UNMOUNTED"
          || report.source_report_contract.schema_version !== REPORT_SCHEMA) return false;
        if (!["OBSERVED_CALIBRATION_MATCH", "OBSERVED_CALIBRATION_BLOCK"].includes(report.report_state)) return false;
        if (!validSummary(report.calibration_summary, report.report_state)) return false;
      } else {
        if (!["MISSING", "UNSUPPORTED", "INVALID"].includes(report.source_state)) return false;
        if (report.report_state !== "UNKNOWN" || report.diagnostic_state !== "UNKNOWN"
          || report.maturity_state !== "UNKNOWN" || report.calibration_summary !== null
          || report.source_report_contract !== null) return false;
        const nullable = ["source_schema_version", "source_static_fingerprint",
          "source_replay_hash", "source_registration_hash",
          "source_calibration_observations_hash",
          "source_declared_calibration_receipt_hash",
          "source_registered_beta_ledger_hash", "source_replayed_beta_ledger_hash"];
        if (!nullable.every((key) => report[key] === null)) return false;
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  function verifyEnvelope(envelope) {
    try {
      if (!strictJson || !exactKeys(envelope, ENVELOPE_KEYS)) return false;
      if (!strictJson.verifySealedDocument(envelope, "envelope_hash")) return false;
      if (envelope.schema_version !== ENVELOPE_SCHEMA
        || envelope.static_fingerprint !== ENVELOPE_FINGERPRINT
        || envelope.presentation_status !== PRESENTATION_STATUS) return false;
      if (!lockedAuthority(envelope.authority, ENVELOPE_AUTHORITY_KEYS)) return false;
      if (containsPrivateKeys(envelope)) return false;

      if (envelope.report === null) {
        const closedStates = ["NOT_SUPPLIED", "UNSUPPORTED", "INVALID"];
        return envelope.verification_state === "UNKNOWN"
          && closedStates.includes(envelope.source_state)
          && envelope.source_schema_version === null
          && envelope.source_static_fingerprint === null
          && envelope.source_report_hash === null
          && envelope.source_replay_hash === null
          && envelope.source_registration_hash === null
          && envelope.source_calibration_observations_hash === null;
      }

      if (!verifyReport(envelope.report)) return false;
      return envelope.verification_state === "VERIFIED"
        && envelope.envelope_reason === "G1_REPORT_VERIFIED"
        && envelope.source_state === envelope.report.source_state
        && envelope.source_schema_version === envelope.report.schema_version
        && envelope.source_static_fingerprint === envelope.report.static_fingerprint
        && envelope.source_report_hash === envelope.report.verification_hash
        && envelope.source_replay_hash === envelope.report.source_replay_hash
        && envelope.source_registration_hash === envelope.report.source_registration_hash
        && envelope.source_calibration_observations_hash
          === envelope.report.source_calibration_observations_hash;
    } catch (_error) {
      return false;
    }
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.values(value).forEach(deepFreeze);
    }
    return value;
  }

  function lockedModelAuthority() {
    return {
      current_admission_allowed: false,
      descriptive_only: true,
      live_order_allowed: false,
      paper_authorized: false,
      presentation_mounted: false,
      profitability_claim_allowed: false,
    };
  }

  function unknownModel(reason, envelopeHash) {
    return deepFreeze({
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
      presentation_status: PRESENTATION_STATUS,
      verification_state: "UNKNOWN",
      evidence_state: "UNKNOWN",
      source: { label: "SOURCE", state: "UNKNOWN", detail: "No verified G1 report is available." },
      gap: { label: "GAP", state: reason, detail: "Calibration replay evidence remains unresolved." },
      maturity: { label: "MATURITY", state: "UNKNOWN", detail: "Candidate maturity cannot be projected." },
      permission: { label: "PERMISSION", state: "LOCKED", detail: "Research display only. No current, paper, or live authority." },
      calibration: null,
      blockers: [reason],
      provenance: { envelope_hash: envelopeHash || null, report_hash: null, replay_hash: null },
      authority: lockedModelAuthority(),
    });
  }

  function buildFactorCalibrationPresentationModel(envelope) {
    if (!verifyEnvelope(envelope)) return unknownModel("PRESENTATION_ENVELOPE_INVALID", null);
    if (envelope.report === null) return unknownModel(envelope.envelope_reason, envelope.envelope_hash);

    const report = envelope.report;
    const match = report.report_state === "OBSERVED_CALIBRATION_MATCH";
    const block = report.report_state === "OBSERVED_CALIBRATION_BLOCK";
    const observed = match || block;
    return deepFreeze({
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
      presentation_status: PRESENTATION_STATUS,
      verification_state: "VERIFIED",
      evidence_state: report.report_state,
      source: {
        label: "SOURCE",
        state: report.source_state,
        detail: observed ? "Official G1 replay report verified." : "Verified G1 report carries an unresolved source state.",
      },
      gap: {
        label: "GAP",
        state: report.gap_state,
        detail: match
          ? "Declared betas replay, while timing and registration binding remain open."
          : block
            ? "Declared betas do not replay within the preregistered tolerance."
            : "Calibration replay evidence remains unresolved.",
      },
      maturity: {
        label: "MATURITY",
        state: report.maturity_state,
        detail: observed ? "Candidate mathematical replay; external timing is not attested." : "Candidate maturity is unknown.",
      },
      permission: {
        label: "PERMISSION",
        state: "LOCKED",
        detail: "Research display only. No current, paper, or live authority.",
      },
      calibration: report.calibration_summary ? { ...report.calibration_summary } : null,
      blockers: [...report.blockers],
      provenance: {
        envelope_hash: envelope.envelope_hash,
        report_hash: envelope.source_report_hash,
        replay_hash: envelope.source_replay_hash,
      },
      authority: lockedModelAuthority(),
    });
  }

  function element(documentRef, tag, className, text) {
    const node = documentRef.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function append(parent, ...children) {
    children.forEach((child) => parent.appendChild(child));
    return parent;
  }

  function axisNode(documentRef, axis) {
    const item = element(documentRef, "article", "factor-calibration-axis");
    item.setAttribute("data-axis-state", axis.state);
    append(
      item,
      element(documentRef, "span", "factor-calibration-axis__label", axis.label),
      element(documentRef, "strong", "factor-calibration-axis__state", axis.state),
      element(documentRef, "p", "factor-calibration-axis__detail", axis.detail),
    );
    return item;
  }

  function shortHash(value) {
    return typeof value === "string" ? `${value.slice(0, 10)}...${value.slice(-8)}` : "UNKNOWN";
  }

  function createFactorCalibrationEvidenceCard(envelope, options) {
    const model = buildFactorCalibrationPresentationModel(envelope);
    const documentRef = options && options.documentRef;
    if (!documentRef || typeof documentRef.createElement !== "function") {
      throw new TypeError("a documentRef with createElement is required");
    }

    const root = element(documentRef, "section", "factor-calibration-evidence-card");
    root.setAttribute("aria-label", "Factor calibration replay evidence");
    root.setAttribute("data-evidence-state", model.evidence_state);

    const header = element(documentRef, "header", "factor-calibration-evidence-card__header");
    const heading = element(documentRef, "div", "factor-calibration-evidence-card__heading");
    append(
      heading,
      element(documentRef, "p", "factor-calibration-evidence-card__eyebrow", "CALIBRATION REPLAY / CANDIDATE"),
      element(documentRef, "h2", "factor-calibration-evidence-card__title", "Does the declared beta ledger replay?"),
      element(documentRef, "p", "factor-calibration-evidence-card__dek", "A sealed mathematical replay view. Timing, formal registration, and execution authority remain separate."),
    );
    const stampText = model.calibration ? model.calibration.replay_decision : "UNKNOWN";
    append(header, heading, element(documentRef, "strong", "factor-calibration-evidence-card__stamp", stampText));

    const axes = element(documentRef, "div", "factor-calibration-evidence-card__axes");
    [model.source, model.gap, model.maturity, model.permission]
      .forEach((axis) => axes.appendChild(axisNode(documentRef, axis)));

    const body = element(documentRef, "div", "factor-calibration-evidence-card__body");
    const calibration = element(documentRef, "section", "factor-calibration-evidence-card__calibration");
    calibration.appendChild(element(documentRef, "h3", "factor-calibration-evidence-card__section-title", "Calibration window"));
    if (model.calibration) {
      const windowText = `${model.calibration.observation_count} rows / ${model.calibration.first_observation_date} to ${model.calibration.last_observation_date}`;
      calibration.appendChild(element(documentRef, "p", "factor-calibration-evidence-card__window", windowText));
      const metrics = element(documentRef, "dl", "factor-calibration-evidence-card__metrics");
      [
        ["Decision", model.calibration.replay_decision],
        ["Max beta error", model.calibration.max_abs_beta_error],
        ["Tolerance", model.calibration.beta_abs_tolerance],
      ].forEach(([label, value]) => {
        const metric = element(documentRef, "div", "factor-calibration-evidence-card__metric");
        append(metric, element(documentRef, "dt", "factor-calibration-evidence-card__metric-label", label), element(documentRef, "dd", "factor-calibration-evidence-card__metric-value", value));
        metrics.appendChild(metric);
      });
      calibration.appendChild(metrics);
    } else {
      calibration.appendChild(element(documentRef, "p", "factor-calibration-evidence-card__window", "No verified calibration summary supplied."));
    }

    const blockers = element(documentRef, "section", "factor-calibration-evidence-card__blockers");
    blockers.appendChild(element(documentRef, "h3", "factor-calibration-evidence-card__section-title", "Open blockers"));
    const blockerList = element(documentRef, "ul", "factor-calibration-evidence-card__blocker-list");
    model.blockers.forEach((blocker) => blockerList.appendChild(element(documentRef, "li", "factor-calibration-evidence-card__blocker", blocker)));
    blockers.appendChild(blockerList);
    append(body, calibration, blockers);

    const provenance = element(documentRef, "footer", "factor-calibration-evidence-card__provenance");
    [
      ["Envelope", model.provenance.envelope_hash],
      ["Report", model.provenance.report_hash],
      ["Replay", model.provenance.replay_hash],
    ].forEach(([label, value]) => {
      const chip = element(documentRef, "span", "factor-calibration-evidence-card__hash");
      append(chip, element(documentRef, "b", "factor-calibration-evidence-card__hash-label", label), element(documentRef, "code", "factor-calibration-evidence-card__hash-value", shortHash(value)));
      provenance.appendChild(chip);
    });

    append(root, header, axes, body, provenance);
    return root;
  }

  return Object.freeze({
    buildFactorCalibrationPresentationModel,
    constants: Object.freeze({
      ENVELOPE_FINGERPRINT,
      ENVELOPE_SCHEMA,
      MODEL_SCHEMA,
      PRESENTATION_FINGERPRINT,
      PRESENTATION_STATUS,
      REPORT_FINGERPRINT,
      REPORT_SCHEMA,
    }),
    contractTestHooks: Object.freeze({ collectKeys, verifyEnvelope, verifyReport }),
    createFactorCalibrationEvidenceCard,
  });
});
