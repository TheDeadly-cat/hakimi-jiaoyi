(function initFactorCalibrationPrecommitEvidenceCard(root, factory) {
  let strictJson = null;
  if (typeof module === "object" && module && module.exports) {
    strictJson = require("./strict_canonical_json_v1.js");
    module.exports = factory(strictJson);
  } else if (root && typeof root === "object") {
    strictJson = root.HakimiStrictCanonicalJsonV1;
    root.HakimiFactorCalibrationPrecommitEvidenceCard = factory(strictJson);
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi(strictJson) {
  "use strict";

  const ENVELOPE_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v1";
  const ENVELOPE_FINGERPRINT = "20260827-cross-lag-factor-calibration-precommit-presentation-envelope-1";
  const GATE_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v2";
  const GATE_FINGERPRINT = "20260826-cross-lag-factor-calibration-precommit-gate-2";
  const MODEL_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-model-v1";
  const PRESENTATION_FINGERPRINT = "20260827-cross-lag-factor-calibration-h2-unmounted-presentation-1";
  const PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE";

  const ENVELOPE_KEYS = Object.freeze([
    "authority", "envelope_hash", "envelope_reason", "gate",
    "presentation_status", "schema_version", "source_calibration_observations_hash",
    "source_gate_hash", "source_precommit_gate_v1_hash", "source_registration_hash",
    "source_replay_hash", "source_schema_version", "source_stability_gate_hash",
    "source_state", "source_static_fingerprint", "static_fingerprint",
    "verification_state",
  ].sort());
  const GATE_KEYS = Object.freeze([
    "authority", "blockers", "evaluation_not_before_date",
    "external_time_anchor_reference_hash", "facts", "fold_count",
    "future_evaluation_id", "gate_decision", "gate_hash", "gate_reason",
    "maximum_allowed_normalized_beta_drift",
    "maximum_observed_normalized_beta_drift", "precommit_declared_at_utc",
    "protocol_id", "schema_version", "sign_reversal_count",
    "source_calibration_observations_hash", "source_declaration_hash",
    "source_precommit_gate_v1_decision", "source_precommit_gate_v1_hash",
    "source_registration_hash", "source_replay_hash", "source_report_hash",
    "source_stability_gate_decision", "source_stability_gate_hash",
    "source_state", "static_fingerprint", "unidentified_fold_count",
    "unstable_identity_count",
  ].sort());
  const GATE_AUTHORITY_KEYS = Object.freeze([
    "beta_temporal_stability_proven", "candidate_activation_allowed",
    "current_admission_allowed", "current_pointer_written", "descriptive_only",
    "external_precommit_timing_attested",
    "formal_residualization_registration_v2_issued", "future_evaluation_allowed",
    "live_order_allowed", "paper_authorized", "profitability_claim_allowed",
  ].sort());
  const ENVELOPE_AUTHORITY_KEYS = Object.freeze([
    "beta_temporal_stability_proven", "candidate_activation_allowed",
    "current_admission_allowed", "current_pointer_written", "descriptive_only",
    "external_precommit_timing_attested",
    "formal_residualization_registration_v2_issued", "future_evaluation_allowed",
    "live_order_allowed", "paper_authorized", "presentation_mounted",
    "profitability_claim_allowed", "source_semantics_replayed_in_browser",
  ].sort());
  const FACT_KEYS = Object.freeze([
    "beta_stability_threshold_passed", "beta_temporal_stability_proven",
    "cross_gate_source_hashes_bound", "external_time_anchor_verified",
    "formal_residualization_registration_v2_issued", "future_evaluation_activated",
    "local_precommit_binding_complete", "precommit_gate_v1_verified",
    "source_gate_block_relaxed", "stability_gate_verified",
  ].sort());
  const PRIVATE_KEYS = new Set([
    "beta_by_identity", "factor_id", "factor_return", "factor_source_hash",
    "identity_order", "returns", "returns_by_identity", "rows",
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

  function strictUtc(value) {
    return typeof value === "string"
      && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value);
  }

  function strictDecimal(value) {
    return typeof value === "string"
      && /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[Ee][+-]?\d+)?$/.test(value)
      && Number.isFinite(Number(value));
  }

  function strictToken(value) {
    return typeof value === "string" && /^[A-Z0-9][A-Z0-9._:-]{0,127}$/.test(value);
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

  function validBlockers(blockers) {
    return Array.isArray(blockers)
      && blockers.length > 0
      && blockers.every((value) => typeof value === "string" && /^[A-Z0-9_]+$/.test(value))
      && new Set(blockers).size === blockers.length;
  }

  function validFacts(facts, observed) {
    if (!exactKeys(facts, FACT_KEYS)) return false;
    if (!FACT_KEYS.every((key) => typeof facts[key] === "boolean")) return false;
    const denied = [
      "beta_temporal_stability_proven", "external_time_anchor_verified",
      "formal_residualization_registration_v2_issued", "future_evaluation_activated",
      "source_gate_block_relaxed",
    ];
    if (!denied.every((key) => facts[key] === false)) return false;
    if (!observed) return FACT_KEYS.every((key) => facts[key] === false);
    return facts.cross_gate_source_hashes_bound === true
      && facts.local_precommit_binding_complete === true
      && facts.precommit_gate_v1_verified === true
      && facts.stability_gate_verified === true;
  }

  function verifyGate(gate) {
    try {
      if (!strictJson || !exactKeys(gate, GATE_KEYS)) return false;
      if (!strictJson.verifySealedDocument(gate, "gate_hash")) return false;
      if (gate.schema_version !== GATE_SCHEMA || gate.static_fingerprint !== GATE_FINGERPRINT) return false;
      if (!lockedAuthority(gate.authority, GATE_AUTHORITY_KEYS)) return false;
      if (!validBlockers(gate.blockers) || containsPrivateKeys(gate)) return false;

      const observed = gate.source_state === "OBSERVED";
      if (!validFacts(gate.facts, observed)) return false;
      if (!observed) {
        if (!["MISSING", "UNSUPPORTED", "INVALID"].includes(gate.source_state)) return false;
        if (gate.gate_decision !== "UNKNOWN" || !strictToken(gate.gate_reason)) return false;
        const nullable = [
          "evaluation_not_before_date", "external_time_anchor_reference_hash",
          "fold_count", "future_evaluation_id", "maximum_allowed_normalized_beta_drift",
          "maximum_observed_normalized_beta_drift", "precommit_declared_at_utc",
          "protocol_id", "sign_reversal_count", "source_calibration_observations_hash",
          "source_declaration_hash", "source_precommit_gate_v1_decision",
          "source_precommit_gate_v1_hash", "source_registration_hash",
          "source_replay_hash", "source_report_hash", "source_stability_gate_decision",
          "source_stability_gate_hash", "unidentified_fold_count", "unstable_identity_count",
        ];
        return nullable.every((key) => gate[key] === null);
      }

      const hashes = [
        gate.external_time_anchor_reference_hash, gate.source_calibration_observations_hash,
        gate.source_declaration_hash, gate.source_precommit_gate_v1_hash,
        gate.source_registration_hash, gate.source_replay_hash, gate.source_report_hash,
        gate.source_stability_gate_hash,
      ];
      if (!hashes.every(strictHash)) return false;
      if (!strictDate(gate.evaluation_not_before_date)
        || !strictUtc(gate.precommit_declared_at_utc)
        || !strictToken(gate.future_evaluation_id)
        || !strictToken(gate.protocol_id)) return false;
      if (gate.fold_count !== 4) return false;
      if (![gate.unstable_identity_count, gate.sign_reversal_count,
        gate.unidentified_fold_count].every((value) => Number.isInteger(value) && value >= 0)) return false;
      if (!strictDecimal(gate.maximum_allowed_normalized_beta_drift)
        || !strictDecimal(gate.maximum_observed_normalized_beta_drift)) return false;
      if (!["BOUND_LOCAL_ONLY", "BLOCK"].includes(gate.source_precommit_gate_v1_decision)) return false;
      if (!["STABLE_CANDIDATE", "BLOCK"].includes(gate.source_stability_gate_decision)) return false;

      if (gate.gate_decision === "BOUND_LOCAL_ONLY_STABILITY_GUARDED") {
        return gate.gate_reason === "LOCAL_PRECOMMIT_AND_BETA_STABILITY_GUARD_BOUND"
          && gate.source_precommit_gate_v1_decision === "BOUND_LOCAL_ONLY"
          && gate.source_stability_gate_decision === "STABLE_CANDIDATE"
          && gate.facts.beta_stability_threshold_passed === true
          && gate.unstable_identity_count === 0
          && gate.sign_reversal_count === 0
          && gate.unidentified_fold_count === 0
          && Number(gate.maximum_observed_normalized_beta_drift)
            <= Number(gate.maximum_allowed_normalized_beta_drift);
      }
      if (gate.gate_decision !== "BLOCK") return false;
      if (gate.gate_reason === "SOURCE_PRECOMMIT_GATE_BLOCKED") {
        return gate.source_precommit_gate_v1_decision === "BLOCK";
      }
      if (gate.gate_reason === "BETA_STABILITY_GATE_BLOCKED") {
        return gate.source_stability_gate_decision === "BLOCK";
      }
      return false;
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

      if (envelope.gate === null) {
        return envelope.verification_state === "UNKNOWN"
          && ["NOT_SUPPLIED", "UNSUPPORTED", "INVALID"].includes(envelope.source_state)
          && envelope.source_schema_version === null
          && envelope.source_static_fingerprint === null
          && envelope.source_gate_hash === null
          && envelope.source_precommit_gate_v1_hash === null
          && envelope.source_stability_gate_hash === null
          && envelope.source_replay_hash === null
          && envelope.source_registration_hash === null
          && envelope.source_calibration_observations_hash === null;
      }

      if (!verifyGate(envelope.gate)) return false;
      return envelope.verification_state === "VERIFIED"
        && envelope.envelope_reason === "H1_PRECOMMIT_GATE_VERIFIED"
        && envelope.source_state === envelope.gate.source_state
        && envelope.source_schema_version === envelope.gate.schema_version
        && envelope.source_static_fingerprint === envelope.gate.static_fingerprint
        && envelope.source_gate_hash === envelope.gate.gate_hash
        && envelope.source_precommit_gate_v1_hash === envelope.gate.source_precommit_gate_v1_hash
        && envelope.source_stability_gate_hash === envelope.gate.source_stability_gate_hash
        && envelope.source_replay_hash === envelope.gate.source_replay_hash
        && envelope.source_registration_hash === envelope.gate.source_registration_hash
        && envelope.source_calibration_observations_hash
          === envelope.gate.source_calibration_observations_hash;
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
      beta_temporal_stability_proven: false,
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
      source: { label: "SOURCE", state: "UNKNOWN", detail: "No verified H1 gate is available." },
      gap: { label: "GAP", state: reason, detail: "Precommit and beta-stability composition remains unresolved." },
      maturity: { label: "MATURITY", state: "UNKNOWN", detail: "Candidate maturity cannot be projected." },
      permission: { label: "PERMISSION", state: "LOCKED", detail: "Research display only. No current, paper, or live authority." },
      stability: null,
      precommit: null,
      blockers: [reason],
      provenance: { envelope_hash: envelopeHash || null, gate_hash: null, stability_gate_hash: null, precommit_gate_hash: null },
      authority: lockedModelAuthority(),
    });
  }

  function buildFactorCalibrationPrecommitPresentationModel(envelope) {
    if (!verifyEnvelope(envelope)) return unknownModel("PRESENTATION_ENVELOPE_INVALID", null);
    if (envelope.gate === null) return unknownModel(envelope.envelope_reason, envelope.envelope_hash);

    const gate = envelope.gate;
    const observed = gate.source_state === "OBSERVED";
    if (!observed) {
      const model = unknownModel(gate.gate_reason, envelope.envelope_hash);
      return deepFreeze({
        ...model,
        verification_state: "VERIFIED",
        source: { label: "SOURCE", state: gate.source_state, detail: "Verified H1 gate carries an unresolved source state." },
        blockers: [...gate.blockers],
        provenance: { envelope_hash: envelope.envelope_hash, gate_hash: gate.gate_hash, stability_gate_hash: null, precommit_gate_hash: null },
      });
    }

    const guarded = gate.gate_decision === "BOUND_LOCAL_ONLY_STABILITY_GUARDED";
    return deepFreeze({
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
      presentation_status: PRESENTATION_STATUS,
      verification_state: "VERIFIED",
      evidence_state: gate.gate_decision,
      source: { label: "SOURCE", state: "OBSERVED", detail: "Official H1 composition gate verified by the Python envelope." },
      gap: {
        label: "GAP",
        state: guarded ? "EXTERNAL_TIME_AND_FORMALITY_OPEN" : gate.gate_reason,
        detail: guarded
          ? "Local hashes and the candidate fold guard agree; external timing and formal issuance remain open."
          : "A verified source gate blocks this candidate composition.",
      },
      maturity: {
        label: "MATURITY",
        state: guarded ? "STABILITY_GUARDED_CANDIDATE" : "BLOCKED_CANDIDATE",
        detail: guarded
          ? "No H0 violation was found under the fixed candidate thresholds; stability is not proven."
          : "The candidate remains blocked by a verified source decision.",
      },
      permission: { label: "PERMISSION", state: "LOCKED", detail: "Research display only. No current, paper, or live authority." },
      stability: {
        fold_count: gate.fold_count,
        maximum_allowed_normalized_beta_drift: gate.maximum_allowed_normalized_beta_drift,
        maximum_observed_normalized_beta_drift: gate.maximum_observed_normalized_beta_drift,
        unstable_identity_count: gate.unstable_identity_count,
        sign_reversal_count: gate.sign_reversal_count,
        unidentified_fold_count: gate.unidentified_fold_count,
        source_decision: gate.source_stability_gate_decision,
      },
      precommit: {
        future_evaluation_id: gate.future_evaluation_id,
        protocol_id: gate.protocol_id,
        declared_at_utc: gate.precommit_declared_at_utc,
        evaluation_not_before_date: gate.evaluation_not_before_date,
        source_decision: gate.source_precommit_gate_v1_decision,
      },
      blockers: [...gate.blockers],
      provenance: {
        envelope_hash: envelope.envelope_hash,
        gate_hash: envelope.source_gate_hash,
        stability_gate_hash: envelope.source_stability_gate_hash,
        precommit_gate_hash: envelope.source_precommit_gate_v1_hash,
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
    const item = element(documentRef, "article", "factor-precommit-axis");
    item.setAttribute("data-axis-state", axis.state);
    append(
      item,
      element(documentRef, "span", "factor-precommit-axis__label", axis.label),
      element(documentRef, "strong", "factor-precommit-axis__state", axis.state),
      element(documentRef, "p", "factor-precommit-axis__detail", axis.detail),
    );
    return item;
  }

  function metricNode(documentRef, label, value) {
    const metric = element(documentRef, "div", "factor-precommit-card__metric");
    append(
      metric,
      element(documentRef, "dt", "factor-precommit-card__metric-label", label),
      element(documentRef, "dd", "factor-precommit-card__metric-value", value),
    );
    return metric;
  }

  function shortHash(value) {
    return typeof value === "string" ? `${value.slice(0, 10)}...${value.slice(-8)}` : "UNKNOWN";
  }

  function createFactorCalibrationPrecommitEvidenceCard(envelope, options) {
    const model = buildFactorCalibrationPrecommitPresentationModel(envelope);
    const documentRef = options && options.documentRef;
    if (!documentRef || typeof documentRef.createElement !== "function") {
      throw new TypeError("a documentRef with createElement is required");
    }

    const root = element(documentRef, "section", "factor-precommit-card");
    root.setAttribute("aria-label", "Factor calibration precommit and stability evidence");
    root.setAttribute("data-evidence-state", model.evidence_state);

    const header = element(documentRef, "header", "factor-precommit-card__header");
    const heading = element(documentRef, "div", "factor-precommit-card__heading");
    append(
      heading,
      element(documentRef, "p", "factor-precommit-card__eyebrow", "PRECOMMIT x STABILITY / CANDIDATE"),
      element(documentRef, "h2", "factor-precommit-card__title", "Does the local precommit survive a beta-regime check?"),
      element(documentRef, "p", "factor-precommit-card__dek", "A versioned composition view. Fold diagnostics, external timing, formal issuance, and execution authority remain separate claims."),
    );
    const stamp = model.evidence_state === "BOUND_LOCAL_ONLY_STABILITY_GUARDED"
      ? "LOCAL / GUARDED CANDIDATE"
      : model.evidence_state;
    append(header, heading, element(documentRef, "strong", "factor-precommit-card__stamp", stamp));

    const axes = element(documentRef, "div", "factor-precommit-card__axes");
    [model.source, model.gap, model.maturity, model.permission]
      .forEach((axis) => axes.appendChild(axisNode(documentRef, axis)));

    const body = element(documentRef, "div", "factor-precommit-card__body");
    const instrument = element(documentRef, "section", "factor-precommit-card__instrument");
    instrument.appendChild(element(documentRef, "h3", "factor-precommit-card__section-title", "Contiguous-fold guard"));
    if (model.stability) {
      const foldRail = element(documentRef, "div", "factor-precommit-card__fold-rail");
      for (let index = 1; index <= model.stability.fold_count; index += 1) {
        const fold = element(documentRef, "span", "factor-precommit-card__fold");
        append(
          fold,
          element(documentRef, "b", "factor-precommit-card__fold-index", `FOLD ${index}`),
          element(documentRef, "small", "factor-precommit-card__fold-detail", "PRIVATE LEDGER"),
        );
        foldRail.appendChild(fold);
      }
      instrument.appendChild(foldRail);
      const metrics = element(documentRef, "dl", "factor-precommit-card__metrics");
      [
        ["Observed drift", model.stability.maximum_observed_normalized_beta_drift],
        ["Allowed drift", model.stability.maximum_allowed_normalized_beta_drift],
        ["Unstable identities", model.stability.unstable_identity_count],
        ["Sign reversals", model.stability.sign_reversal_count],
        ["Unidentified folds", model.stability.unidentified_fold_count],
      ].forEach(([label, value]) => metrics.appendChild(metricNode(documentRef, label, value)));
      instrument.appendChild(metrics);
    } else {
      instrument.appendChild(element(documentRef, "p", "factor-precommit-card__empty", "No verified aggregate fold summary supplied."));
    }

    const side = element(documentRef, "div", "factor-precommit-card__side");
    const precommit = element(documentRef, "section", "factor-precommit-card__precommit");
    precommit.appendChild(element(documentRef, "h3", "factor-precommit-card__section-title", "Future evaluation binding"));
    if (model.precommit) {
      const rows = [
        ["Evaluation", model.precommit.future_evaluation_id],
        ["Protocol", model.precommit.protocol_id],
        ["Declared", model.precommit.declared_at_utc],
        ["Not before", model.precommit.evaluation_not_before_date],
      ];
      rows.forEach(([label, value]) => {
        const row = element(documentRef, "p", "factor-precommit-card__precommit-row");
        append(
          row,
          element(documentRef, "b", "factor-precommit-card__precommit-label", label),
          element(documentRef, "span", "factor-precommit-card__precommit-value", value),
        );
        precommit.appendChild(row);
      });
    } else {
      precommit.appendChild(element(documentRef, "p", "factor-precommit-card__empty", "No verified precommit summary supplied."));
    }

    const blockers = element(documentRef, "section", "factor-precommit-card__blockers");
    blockers.appendChild(element(documentRef, "h3", "factor-precommit-card__section-title", "Open blockers"));
    const blockerList = element(documentRef, "ul", "factor-precommit-card__blocker-list");
    model.blockers.forEach((blocker) => blockerList.appendChild(
      element(documentRef, "li", "factor-precommit-card__blocker", blocker),
    ));
    blockers.appendChild(blockerList);
    append(side, precommit, blockers);
    append(body, instrument, side);

    const provenance = element(documentRef, "footer", "factor-precommit-card__provenance");
    [
      ["Envelope", model.provenance.envelope_hash],
      ["H1 gate", model.provenance.gate_hash],
      ["H0 gate", model.provenance.stability_gate_hash],
      ["G3 gate", model.provenance.precommit_gate_hash],
    ].forEach(([label, value]) => {
      const chip = element(documentRef, "span", "factor-precommit-card__hash");
      append(
        chip,
        element(documentRef, "b", "factor-precommit-card__hash-label", label),
        element(documentRef, "code", "factor-precommit-card__hash-value", shortHash(value)),
      );
      provenance.appendChild(chip);
    });

    append(root, header, axes, body, provenance);
    return root;
  }

  return Object.freeze({
    buildFactorCalibrationPrecommitPresentationModel,
    constants: Object.freeze({
      ENVELOPE_FINGERPRINT,
      ENVELOPE_SCHEMA,
      GATE_FINGERPRINT,
      GATE_SCHEMA,
      MODEL_SCHEMA,
      PRESENTATION_FINGERPRINT,
      PRESENTATION_STATUS,
    }),
    contractTestHooks: Object.freeze({ collectKeys, verifyEnvelope, verifyGate }),
    createFactorCalibrationPrecommitEvidenceCard,
  });
});
