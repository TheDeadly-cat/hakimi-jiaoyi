(function attachFactorConditionalEvidenceCard(root, factory) {
  const api = factory();
  if (typeof module === "object" && module && module.exports) {
    module.exports = api;
  } else if (root && typeof root === "object") {
    root.HakimiFactorConditionalEvidenceCard = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const ENVELOPE_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v1";
  const ENVELOPE_FINGERPRINT = "20260822-cross-lag-factor-conditional-presentation-envelope-1";
  const RECEIPT_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1";
  const RECEIPT_FINGERPRINT = "20260822-cross-lag-factor-conditional-report-consumer-1";
  const MODEL_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-presentation-model-v1";
  const PRESENTATION_FINGERPRINT = "20260822-cross-lag-factor-conditional-f2-unmounted-presentation-1";
  const PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE";
  const F0_V2_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v2";
  const F0_V2_FINGERPRINT = "20260822-cross-lag-factor-conditional-diagnostic-2";
  const F0_V1_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1";
  const F0_V1_FINGERPRINT = "20260822-cross-lag-factor-conditional-diagnostic-1";
  const C0_SCHEMA = "strategy-correlation-cross-lag-gate-candidate-v1";
  const C0_FINGERPRINT = "20260821-cross-lag-dependence-gate-1";

  const ENVELOPE_KEYS = [
    "authority", "blockers", "envelope_hash", "envelope_reason",
    "presentation_status", "report", "schema_version", "source_diagnostic_hash",
    "source_receipt_hash", "source_schema_version", "source_state",
    "source_static_fingerprint", "source_v1_diagnostic_hash", "static_fingerprint",
    "verification_state",
  ];
  const ENVELOPE_AUTHORITY_KEYS = [
    "candidate_activation_allowed", "common_factor_causality_proven",
    "current_admission_allowed", "current_pointer_written", "descriptive_only",
    "factor_calibration_attested", "global_two_view_multiplicity_registered",
    "live_order_allowed", "paper_authorized", "presentation_mounted",
    "profitability_claim_allowed", "raw_independence_proven",
    "residual_independence_proven", "source_semantics_replayed_in_browser",
  ];
  const RECEIPT_KEYS = [
    "authority", "blockers", "diagnostic_reason", "diagnostic_state", "facts",
    "gap_state", "maturity_state", "permission_state", "raw_evaluation",
    "report_state", "residual_evaluation", "schema_version",
    "source_diagnostic_hash", "source_factor_observations_hash",
    "source_identity_order_hash", "source_raw_evaluation_hash",
    "source_registration_hash", "source_report_contract",
    "source_residual_evaluation_hash", "source_residual_input_hash",
    "source_schema_version", "source_state", "source_static_fingerprint",
    "source_v1_diagnostic_hash", "static_fingerprint", "verification_hash",
  ];
  const RECEIPT_AUTHORITY_KEYS = [
    "candidate_activation_allowed", "common_factor_causality_proven",
    "current_admission_allowed", "current_pointer_written", "descriptive_only",
    "factor_calibration_attested", "formal_factor_registration_bound",
    "global_two_view_multiplicity_registered", "live_order_allowed",
    "paper_authorized", "profitability_claim_allowed", "raw_independence_proven",
    "report_consumer_activated", "report_mounted", "residual_independence_proven",
  ];
  const FACT_KEYS = [
    "calibration_receipt_attested", "global_two_view_multiplicity_registered",
    "raw_block_relaxed", "raw_c0_verified", "residual_c0_verified",
    "source_diagnostic_verified",
  ];
  const EVALUATION_KEYS = [
    "cross_stratum_pair_count", "dependent_test_count", "evaluation_hash",
    "gate_decision", "gate_reason", "lag_test_count",
    "max_adjusted_absolute_lower", "observation_count", "schema_version",
    "static_fingerprint",
  ];
  const MODEL_AUTHORITY = Object.freeze({
    candidate_activation_allowed: false,
    common_factor_causality_proven: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    descriptive_only: true,
    factor_calibration_attested: false,
    global_two_view_multiplicity_registered: false,
    live_order_allowed: false,
    paper_authorized: false,
    presentation_mounted: false,
    profitability_claim_allowed: false,
    raw_independence_proven: false,
    residual_independence_proven: false,
    source_semantics_replayed_in_browser: false,
  });
  const COPY = Object.freeze({
    eyebrow: "FACTOR-CONDITIONAL EVIDENCE",
    title: "Cross-lag mechanism ledger",
    permission: "Research display only",
    footer: "No independence, causality, profitability, paper, or live authority.",
  });

  function isPlainObject(value) {
    return value !== null
      && typeof value === "object"
      && Object.getPrototypeOf(value) === Object.prototype;
  }

  function isNativeArray(value) {
    return Array.isArray(value) && Object.getPrototypeOf(value) === Array.prototype;
  }

  function isAscii(value) {
    if (typeof value !== "string") return false;
    for (let index = 0; index < value.length; index += 1) {
      if (value.charCodeAt(index) > 0x7f) return false;
    }
    return true;
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactKeys(value, keys) {
    if (!isPlainObject(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = keys.slice().sort();
    return actual.length === expected.length
      && actual.every((key, index) => key === expected[index]);
  }

  function canonicalJson(value, active) {
    const seen = active || new Set();
    if (value === null) return "null";
    if (value === true) return "true";
    if (value === false) return "false";
    if (typeof value === "string") {
      if (!isAscii(value)) throw new TypeError("strict_canonical_json_non_ascii");
      return JSON.stringify(value);
    }
    if (typeof value === "number") {
      if (!Number.isSafeInteger(value) || Object.is(value, -0)) {
        throw new TypeError("strict_canonical_json_invalid_number");
      }
      return String(value);
    }
    if (isNativeArray(value)) {
      if (seen.has(value)) throw new TypeError("strict_canonical_json_cycle");
      seen.add(value);
      const result = `[${value.map((item) => canonicalJson(item, seen)).join(",")}]`;
      seen.delete(value);
      return result;
    }
    if (isPlainObject(value)) {
      if (seen.has(value)) throw new TypeError("strict_canonical_json_cycle");
      seen.add(value);
      const parts = Object.keys(value).sort().map((key) => {
        if (!isAscii(key)) throw new TypeError("strict_canonical_json_non_ascii_key");
        return `${JSON.stringify(key)}:${canonicalJson(value[key], seen)}`;
      });
      seen.delete(value);
      return `{${parts.join(",")}}`;
    }
    throw new TypeError("strict_canonical_json_invalid_type");
  }

  function rotateRight(value, bits) {
    return (value >>> bits) | (value << (32 - bits));
  }

  function sha256Ascii(value) {
    if (!isAscii(value)) throw new TypeError("sha256_ascii_required");
    const constants = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b,
      0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
      0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7,
      0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
      0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152,
      0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
      0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
      0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
      0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
      0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
      0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
      0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];
    const state = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    const bytes = [];
    for (let index = 0; index < value.length; index += 1) {
      bytes.push(value.charCodeAt(index));
    }
    const bitLength = bytes.length * 8;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) bytes.push(0);
    const high = Math.floor(bitLength / 0x100000000);
    const low = bitLength >>> 0;
    for (let shift = 24; shift >= 0; shift -= 8) bytes.push((high >>> shift) & 0xff);
    for (let shift = 24; shift >= 0; shift -= 8) bytes.push((low >>> shift) & 0xff);

    for (let offset = 0; offset < bytes.length; offset += 64) {
      const words = new Uint32Array(64);
      for (let index = 0; index < 16; index += 1) {
        const start = offset + index * 4;
        words[index] = (
          (bytes[start] << 24) | (bytes[start + 1] << 16)
          | (bytes[start + 2] << 8) | bytes[start + 3]
        ) >>> 0;
      }
      for (let index = 16; index < 64; index += 1) {
        const s0 = rotateRight(words[index - 15], 7)
          ^ rotateRight(words[index - 15], 18) ^ (words[index - 15] >>> 3);
        const s1 = rotateRight(words[index - 2], 17)
          ^ rotateRight(words[index - 2], 19) ^ (words[index - 2] >>> 10);
        words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let index = 0; index < 64; index += 1) {
        const upper = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choose = (e & f) ^ ((~e) & g);
        const first = (h + upper + choose + constants[index] + words[index]) >>> 0;
        const lower = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const second = (lower + majority) >>> 0;
        h = g; g = f; f = e; e = (d + first) >>> 0;
        d = c; c = b; b = a; a = (first + second) >>> 0;
      }
      state[0] = (state[0] + a) >>> 0;
      state[1] = (state[1] + b) >>> 0;
      state[2] = (state[2] + c) >>> 0;
      state[3] = (state[3] + d) >>> 0;
      state[4] = (state[4] + e) >>> 0;
      state[5] = (state[5] + f) >>> 0;
      state[6] = (state[6] + g) >>> 0;
      state[7] = (state[7] + h) >>> 0;
    }
    return state.map((item) => item.toString(16).padStart(8, "0")).join("");
  }

  function verifySealed(document, hashField) {
    if (!isPlainObject(document) || !isHash(document[hashField])) return false;
    const payload = {};
    Object.keys(document).forEach((key) => {
      if (key !== hashField) payload[key] = document[key];
    });
    try {
      return sha256Ascii(canonicalJson(payload)) === document[hashField];
    } catch (_error) {
      return false;
    }
  }

  function seal(payload, hashField) {
    const document = {};
    Object.keys(payload).forEach((key) => { document[key] = payload[key]; });
    document[hashField] = sha256Ascii(canonicalJson(payload));
    return document;
  }

  function lockedAuthority(value, keys) {
    if (!exactKeys(value, keys) || value.descriptive_only !== true) return false;
    return keys.every((key) => key === "descriptive_only" || value[key] === false);
  }

  function asciiStringArray(value, unique) {
    if (!isNativeArray(value) || !value.every((item) => isAscii(item) && item.length > 0)) {
      return false;
    }
    return !unique || new Set(value).size === value.length;
  }

  function validEvaluation(value) {
    if (!exactKeys(value, EVALUATION_KEYS)) return false;
    if (value.schema_version !== C0_SCHEMA || value.static_fingerprint !== C0_FINGERPRINT) return false;
    if (!isHash(value.evaluation_hash)) return false;
    if (!isAscii(value.gate_reason) || !["PASS", "BLOCK"].includes(value.gate_decision)) return false;
    const counts = [
      value.cross_stratum_pair_count, value.dependent_test_count,
      value.lag_test_count, value.observation_count,
    ];
    if (!counts.every((item) => Number.isSafeInteger(item) && item >= 0)) return false;
    if (value.cross_stratum_pair_count < 1 || value.lag_test_count < 1 || value.observation_count < 64) return false;
    return typeof value.max_adjusted_absolute_lower === "string"
      && /^(0|[0-9]+(?:\.[0-9]+)?)$/.test(value.max_adjusted_absolute_lower);
  }

  const OBSERVED_STATES = Object.freeze({
    OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE: {
      diagnostic: "COMMON_FACTOR_MEDIATED_CANDIDATE",
      gap: "COMMON_FACTOR_MEDIATION_CANDIDATE",
      raw: "BLOCK", residual: "PASS",
      summary: "Raw cross-lag dependence remains binding; the residual view is descriptive only.",
    },
    OBSERVED_RESIDUAL_CROSS_LAG_DEPENDENCE: {
      diagnostic: "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
      gap: "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
      raw: "BLOCK", residual: "BLOCK",
      summary: "Cross-lag dependence remains visible in both raw and residual views.",
    },
    OBSERVED_NO_CONDITIONAL_DEPENDENCE: {
      diagnostic: "NO_CONDITIONAL_DEPENDENCE_DETECTED",
      gap: "NO_CONDITIONAL_DEPENDENCE_OBSERVED",
      raw: "PASS", residual: "PASS",
      summary: "Neither candidate view detected preregistered cross-lag dependence; independence is not proven.",
    },
    OBSERVED_SUPPRESSION_OR_MODEL_INSTABILITY: {
      diagnostic: "SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY",
      gap: "FACTOR_MODEL_INSTABILITY_OBSERVED",
      raw: "PASS", residual: "BLOCK",
      summary: "The residual view exposes dependence absent from the raw view; factor-model instability remains open.",
    },
  });

  function validFacts(value, sourceState) {
    if (!exactKeys(value, FACT_KEYS)) return false;
    if (!FACT_KEYS.every((key) => typeof value[key] === "boolean")) return false;
    if (value.calibration_receipt_attested || value.global_two_view_multiplicity_registered || value.raw_block_relaxed) return false;
    if (sourceState === "OBSERVED") {
      return value.source_diagnostic_verified && value.raw_c0_verified && value.residual_c0_verified;
    }
    if (sourceState === "UNSUPPORTED") {
      return value.source_diagnostic_verified && !value.raw_c0_verified && !value.residual_c0_verified;
    }
    return !value.source_diagnostic_verified && !value.raw_c0_verified && !value.residual_c0_verified;
  }

  function validReceipt(value) {
    if (!exactKeys(value, RECEIPT_KEYS) || !verifySealed(value, "verification_hash")) return false;
    if (value.schema_version !== RECEIPT_SCHEMA || value.static_fingerprint !== RECEIPT_FINGERPRINT) return false;
    if (!lockedAuthority(value.authority, RECEIPT_AUTHORITY_KEYS)) return false;
    if (!asciiStringArray(value.blockers, true) || value.permission_state !== "LOCKED") return false;
    if (!isAscii(value.diagnostic_reason) || !isAscii(value.diagnostic_state)
      || !isAscii(value.gap_state) || !isAscii(value.maturity_state)
      || !isAscii(value.report_state)) return false;
    if (!validFacts(value.facts, value.source_state)) return false;

    if (value.source_state === "OBSERVED") {
      const contract = OBSERVED_STATES[value.report_state];
      if (!contract || value.diagnostic_state !== contract.diagnostic || value.gap_state !== contract.gap) return false;
      if (value.maturity_state !== "CANDIDATE_RESIDUALIZED_NOT_FORMAL") return false;
      if (!validEvaluation(value.raw_evaluation) || !validEvaluation(value.residual_evaluation)) return false;
      if (value.raw_evaluation.gate_decision !== contract.raw
        || value.residual_evaluation.gate_decision !== contract.residual) return false;
      if (contract.raw === "PASS" && value.raw_evaluation.dependent_test_count !== 0) return false;
      if (contract.raw === "BLOCK" && value.raw_evaluation.dependent_test_count < 1) return false;
      if (contract.residual === "PASS" && value.residual_evaluation.dependent_test_count !== 0) return false;
      if (contract.residual === "BLOCK" && value.residual_evaluation.dependent_test_count < 1) return false;
      const hashes = [
        value.source_diagnostic_hash, value.source_factor_observations_hash,
        value.source_identity_order_hash, value.source_raw_evaluation_hash,
        value.source_registration_hash, value.source_residual_evaluation_hash,
        value.source_residual_input_hash, value.source_v1_diagnostic_hash,
      ];
      if (!hashes.every(isHash)) return false;
      if (value.source_raw_evaluation_hash !== value.raw_evaluation.evaluation_hash
        || value.source_residual_evaluation_hash !== value.residual_evaluation.evaluation_hash) return false;
      if (value.source_schema_version !== F0_V2_SCHEMA
        || value.source_static_fingerprint !== F0_V2_FINGERPRINT) return false;
      if (!exactKeys(value.source_report_contract, ["activation_state", "schema_version"])) return false;
      if (value.source_report_contract.activation_state !== "UNMOUNTED"
        || value.source_report_contract.schema_version !== RECEIPT_SCHEMA) return false;
      if (value.blockers.filter((item) => item === "FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED").length !== 1) return false;
      return !value.blockers.includes("F1_REPORT_CONSUMER_NOT_IMPLEMENTED");
    }

    if (!["MISSING", "UNSUPPORTED", "INVALID"].includes(value.source_state)) return false;
    if (value.report_state !== "UNKNOWN" || value.diagnostic_state !== "UNKNOWN"
      || value.maturity_state !== "UNKNOWN" || value.raw_evaluation !== null
      || value.residual_evaluation !== null || value.source_report_contract !== null) return false;
    const expectedBlocker = {
      MISSING: "F0_V2_DIAGNOSTIC_MISSING",
      UNSUPPORTED: "F0_V1_PRECONSUMER_CONTRACT",
      INVALID: "F0_V2_DIAGNOSTIC_INVALID",
    }[value.source_state];
    if (value.blockers.length !== 1 || value.blockers[0] !== expectedBlocker
      || value.gap_state !== expectedBlocker || value.diagnostic_reason !== expectedBlocker) return false;
    const nullableFields = [
      "source_factor_observations_hash", "source_identity_order_hash",
      "source_raw_evaluation_hash", "source_registration_hash",
      "source_residual_evaluation_hash", "source_residual_input_hash",
    ];
    if (!nullableFields.every((key) => value[key] === null)) return false;
    if (value.source_state === "UNSUPPORTED") {
      return isHash(value.source_diagnostic_hash)
        && value.source_v1_diagnostic_hash === value.source_diagnostic_hash
        && value.source_schema_version === F0_V1_SCHEMA
        && value.source_static_fingerprint === F0_V1_FINGERPRINT;
    }
    return value.source_diagnostic_hash === null && value.source_v1_diagnostic_hash === null
      && value.source_schema_version === null && value.source_static_fingerprint === null;
  }

  function validEnvelope(value) {
    if (!exactKeys(value, ENVELOPE_KEYS) || !verifySealed(value, "envelope_hash")) return false;
    if (value.schema_version !== ENVELOPE_SCHEMA || value.static_fingerprint !== ENVELOPE_FINGERPRINT
      || value.presentation_status !== PRESENTATION_STATUS) return false;
    if (!lockedAuthority(value.authority, ENVELOPE_AUTHORITY_KEYS)
      || !asciiStringArray(value.blockers, true) || !isAscii(value.envelope_reason)) return false;
    if (value.verification_state === "NOT_SUPPLIED") {
      return value.source_state === "NOT_SUPPLIED" && value.envelope_reason === "F1_RECEIPT_NOT_SUPPLIED"
        && value.blockers.length === 1 && value.blockers[0] === "F1_RECEIPT_NOT_SUPPLIED"
        && value.report === null && value.source_diagnostic_hash === null
        && value.source_receipt_hash === null && value.source_schema_version === null
        && value.source_static_fingerprint === null && value.source_v1_diagnostic_hash === null;
    }
    if (value.verification_state === "INVALID") {
      return value.source_state === "INVALID" && value.envelope_reason === "F1_RECEIPT_INVALID"
        && value.blockers.length === 1 && value.blockers[0] === "F1_RECEIPT_INVALID"
        && value.report === null && value.source_diagnostic_hash === null
        && value.source_receipt_hash === null && value.source_schema_version === null
        && value.source_static_fingerprint === null && value.source_v1_diagnostic_hash === null;
    }
    if (value.verification_state !== "VERIFIED" || value.envelope_reason !== "F1_RECEIPT_VERIFIED"
      || value.blockers.length !== 0 || !validReceipt(value.report)) return false;
    return value.source_state === value.report.source_state
      && value.source_schema_version === RECEIPT_SCHEMA
      && value.source_static_fingerprint === RECEIPT_FINGERPRINT
      && value.source_receipt_hash === value.report.verification_hash
      && value.source_diagnostic_hash === value.report.source_diagnostic_hash
      && value.source_v1_diagnostic_hash === value.report.source_v1_diagnostic_hash;
  }

  function modelPayload(source, gap, maturity, blockers, publicState, comparison, provenance, summary) {
    return {
      authority: { ...MODEL_AUTHORITY },
      axes: [
        { axis: "SOURCE", state: source },
        { axis: "GAP", state: gap },
        { axis: "MATURITY", state: maturity },
        { axis: "PERMISSION", state: "LOCKED" },
      ],
      blockers: blockers.slice(),
      comparison,
      copy: { ...COPY, summary },
      presentation_status: PRESENTATION_STATUS,
      provenance,
      public_state: publicState,
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
    };
  }

  function sealedModel(payload) {
    return seal(payload, "presentation_model_hash");
  }

  function notSuppliedModel() {
    return sealedModel(modelPayload(
      "NOT_SUPPLIED", "ENVELOPE_NOT_SUPPLIED", "NOT_EVALUATED",
      ["F1_PRESENTATION_ENVELOPE_NOT_SUPPLIED"], "NOT_SUPPLIED", null, null,
      "No verified factor-conditional presentation envelope was supplied.",
    ));
  }

  function invalidModel() {
    return sealedModel(modelPayload(
      "UNKNOWN", "ENVELOPE_INVALID", "UNKNOWN",
      ["F1_PRESENTATION_ENVELOPE_INVALID"], "UNKNOWN", null, null,
      "The supplied presentation envelope did not satisfy the exact display contract.",
    ));
  }

  function evaluationView(label, value) {
    return {
      cross_stratum_pair_count: value.cross_stratum_pair_count,
      decision: value.gate_decision,
      dependent_test_count: value.dependent_test_count,
      label,
      lag_test_count: value.lag_test_count,
      max_adjusted_absolute_lower: value.max_adjusted_absolute_lower,
      observation_count: value.observation_count,
      reason: value.gate_reason,
    };
  }

  function verifiedModel(envelope) {
    const report = envelope.report;
    const provenance = {
      diagnostic_hash: report.source_diagnostic_hash,
      envelope_hash: envelope.envelope_hash,
      receipt_hash: report.verification_hash,
      receipt_schema_version: report.schema_version,
      receipt_static_fingerprint: report.static_fingerprint,
      v1_diagnostic_hash: report.source_v1_diagnostic_hash,
    };
    if (report.source_state !== "OBSERVED") {
      const summaries = {
        MISSING: "The exact F1 receipt records that no F0-v2 diagnostic was supplied.",
        UNSUPPORTED: "The exact F1 receipt records a valid F0-v1 source that is not auto-migrated.",
        INVALID: "The exact F1 receipt records an invalid or context-mismatched F0-v2 source.",
      };
      return sealedModel(modelPayload(
        report.source_state, report.gap_state, report.maturity_state,
        report.blockers, report.report_state, null, provenance,
        summaries[report.source_state],
      ));
    }
    const contract = OBSERVED_STATES[report.report_state];
    return sealedModel(modelPayload(
      report.source_state, report.gap_state, report.maturity_state,
      report.blockers, report.report_state,
      {
        raw: evaluationView("RAW VIEW", report.raw_evaluation),
        residual: evaluationView("RESIDUAL VIEW", report.residual_evaluation),
      },
      provenance, contract.summary,
    ));
  }

  function buildFactorConditionalPresentationModel(envelope) {
    try {
      if (envelope === null || envelope === undefined) return notSuppliedModel();
      if (!validEnvelope(envelope)) return invalidModel();
      if (envelope.verification_state === "NOT_SUPPLIED") return notSuppliedModel();
      if (envelope.verification_state === "INVALID") return invalidModel();
      return verifiedModel(envelope);
    } catch (_error) {
      return invalidModel();
    }
  }

  function addText(documentRef, parent, tagName, className, text) {
    const element = documentRef.createElement(tagName);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function formatHash(value) {
    return isHash(value) ? `${value.slice(0, 12)}...${value.slice(-8)}` : "NOT AVAILABLE";
  }

  function createFactorConditionalEvidenceCard(documentRef, envelope) {
    if (!documentRef || typeof documentRef.createElement !== "function"
      || typeof documentRef.createTextNode !== "function") {
      throw new TypeError("explicit_dom_document_required");
    }
    const model = buildFactorConditionalPresentationModel(envelope);
    const rootElement = documentRef.createElement("article");
    rootElement.className = "factor-conditional-evidence-card";
    rootElement.setAttribute("data-public-state", model.public_state);
    rootElement.setAttribute("data-presentation-status", model.presentation_status);

    const header = documentRef.createElement("header");
    header.className = "factor-conditional-evidence-card__header";
    addText(documentRef, header, "p", "factor-conditional-evidence-card__eyebrow", model.copy.eyebrow);
    addText(documentRef, header, "h2", "factor-conditional-evidence-card__title", model.copy.title);
    addText(documentRef, header, "p", "factor-conditional-evidence-card__summary", model.copy.summary);
    rootElement.appendChild(header);

    const axes = documentRef.createElement("ol");
    axes.className = "factor-conditional-evidence-card__axes";
    model.axes.forEach((axis) => {
      const item = documentRef.createElement("li");
      item.className = "factor-conditional-evidence-card__axis";
      item.setAttribute("data-axis", axis.axis);
      item.setAttribute("data-state", axis.state);
      addText(documentRef, item, "span", "factor-conditional-evidence-card__axis-label", axis.axis);
      addText(documentRef, item, "strong", "factor-conditional-evidence-card__axis-state", axis.state);
      axes.appendChild(item);
    });
    rootElement.appendChild(axes);

    if (model.comparison) {
      const comparison = documentRef.createElement("section");
      comparison.className = "factor-conditional-evidence-card__comparison";
      [model.comparison.raw, model.comparison.residual].forEach((view) => {
        const panel = documentRef.createElement("section");
        panel.className = "factor-conditional-evidence-card__view";
        panel.setAttribute("data-decision", view.decision);
        addText(documentRef, panel, "p", "factor-conditional-evidence-card__view-label", view.label);
        addText(documentRef, panel, "h3", "factor-conditional-evidence-card__decision", view.decision);
        addText(documentRef, panel, "p", "factor-conditional-evidence-card__reason", view.reason);
        const metrics = documentRef.createElement("dl");
        metrics.className = "factor-conditional-evidence-card__metrics";
        [
          ["OBSERVATIONS", view.observation_count],
          ["PAIR COUNT", view.cross_stratum_pair_count],
          ["LAG TESTS", view.lag_test_count],
          ["DEPENDENT", view.dependent_test_count],
          ["ADJ LOWER", view.max_adjusted_absolute_lower],
        ].forEach(([label, value]) => {
          addText(documentRef, metrics, "dt", "factor-conditional-evidence-card__metric-label", label);
          addText(documentRef, metrics, "dd", "factor-conditional-evidence-card__metric-value", String(value));
        });
        panel.appendChild(metrics);
        comparison.appendChild(panel);
      });
      rootElement.appendChild(comparison);
    }

    const blockers = documentRef.createElement("section");
    blockers.className = "factor-conditional-evidence-card__blockers";
    addText(documentRef, blockers, "h3", "factor-conditional-evidence-card__section-title", "OPEN GAPS");
    const blockerList = documentRef.createElement("ul");
    blockerList.className = "factor-conditional-evidence-card__blocker-list";
    model.blockers.forEach((blocker) => {
      addText(documentRef, blockerList, "li", "factor-conditional-evidence-card__blocker", blocker);
    });
    blockers.appendChild(blockerList);
    rootElement.appendChild(blockers);

    if (model.provenance) {
      const provenance = documentRef.createElement("section");
      provenance.className = "factor-conditional-evidence-card__provenance";
      addText(documentRef, provenance, "h3", "factor-conditional-evidence-card__section-title", "PROVENANCE");
      [
        ["ENVELOPE", model.provenance.envelope_hash],
        ["F1 RECEIPT", model.provenance.receipt_hash],
        ["F0-V2", model.provenance.diagnostic_hash],
        ["F0-V1", model.provenance.v1_diagnostic_hash],
      ].forEach(([label, hash]) => {
        const row = documentRef.createElement("p");
        row.className = "factor-conditional-evidence-card__hash-row";
        addText(documentRef, row, "span", "factor-conditional-evidence-card__hash-label", label);
        addText(documentRef, row, "code", "factor-conditional-evidence-card__hash", formatHash(hash));
        provenance.appendChild(row);
      });
      rootElement.appendChild(provenance);
    }

    const footer = documentRef.createElement("footer");
    footer.className = "factor-conditional-evidence-card__footer";
    addText(documentRef, footer, "strong", "factor-conditional-evidence-card__permission", model.copy.permission);
    addText(documentRef, footer, "p", "factor-conditional-evidence-card__disclaimer", model.copy.footer);
    rootElement.appendChild(footer);
    return rootElement;
  }

  return Object.freeze({
    buildFactorConditionalPresentationModel,
    constants: Object.freeze({
      ENVELOPE_FINGERPRINT,
      ENVELOPE_SCHEMA,
      MODEL_SCHEMA,
      PRESENTATION_FINGERPRINT,
      PRESENTATION_STATUS,
      RECEIPT_FINGERPRINT,
      RECEIPT_SCHEMA,
    }),
    contractTestHooks: Object.freeze({ canonicalJson, sha256Ascii }),
    createFactorConditionalEvidenceCard,
  });
});
