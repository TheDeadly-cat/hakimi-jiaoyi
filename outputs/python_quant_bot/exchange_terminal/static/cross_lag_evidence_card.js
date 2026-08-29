(function attachCrossLagEvidenceCard(root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module && module.exports) {
    module.exports = api;
    return;
  }
  if (root && typeof root === "object" && !Object.prototype.hasOwnProperty.call(root, "HakimiCrossLagEvidenceCard")) {
    Object.defineProperty(root, "HakimiCrossLagEvidenceCard", {
      configurable: false,
      enumerable: false,
      writable: false,
      value: api,
    });
  }
})(typeof globalThis === "object" ? globalThis : this, function createCrossLagEvidenceCardApi() {
  "use strict";

  const ENVELOPE_SCHEMA = "strategy-correlation-cross-lag-presentation-envelope-v1";
  const MODEL_SCHEMA = "strategy-correlation-cross-lag-presentation-model-v1";
  const PRESENTATION_FINGERPRINT = "20260821-cross-lag-c4-unmounted-presentation-1";
  const C3_SCHEMA = "strategy-correlation-cross-lag-public-summary-v1";
  const C3_VERIFICATION_SCHEMA = "strategy-correlation-cross-lag-public-summary-v1-verification-v1";
  const C3_FINGERPRINT = "20260821-cross-lag-public-summary-1";
  const C2_SCHEMA = "strategy-correlation-cross-lag-protocol-binding-candidate-v1";
  const C2_FINGERPRINT = "20260821-cross-lag-protocol-binding-1";
  const PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE";

  const PUBLIC_STATES = Object.freeze([
    "NOT_SUPPLIED",
    "UNKNOWN",
    "OBSERVED_PASS",
    "OBSERVED_BLOCK",
  ]);
  const AXIS_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  const HASH_PATTERN = /^[0-9a-f]{64}$/i;
  const DECIMAL_PATTERN = /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/;

  const SUMMARY_KEYS = Object.freeze([
    "analytic_policy_hash",
    "authority",
    "blockers",
    "c2_assessment_hash",
    "c2_assessment_schema",
    "c2_assessment_static_fingerprint",
    "consumer_receipt_hash",
    "cross_stratum_pair_count",
    "dependent_test_count",
    "direction_contract_hash",
    "evaluation_hash",
    "facts",
    "gap_axis",
    "gate_decision",
    "gate_reason",
    "lag_test_count",
    "maturity_axis",
    "max_adjusted_absolute_lower",
    "permission_axis",
    "preregistration_adapter_binding_hash",
    "protocol_registration_hash",
    "public_state",
    "public_summary_hash",
    "schema_version",
    "source_axis",
    "static_fingerprint",
    "stratum_assignment_hash",
    "verification_schema_version",
  ]);
  const AUTHORITY_KEYS = Object.freeze([
    "candidate_binding_activation_allowed",
    "count_as_independent_allowed",
    "current_admission_allowed",
    "current_pointer_written",
    "current_writer_activation_allowed",
    "descriptive_only",
    "formal_preregistration_bound",
    "formal_registry_activation_allowed",
    "formal_registry_written",
    "independence_proven",
    "live_order_allowed",
    "paper_authorized",
    "profitability_claim_allowed",
    "sequence_order_attested",
    "strata_timing_attested",
  ]);
  const FACT_KEYS = Object.freeze([
    "aggregate_projection_only",
    "c2_assessment_verified",
    "formal_preregistration_bound",
    "sequence_order_attested",
  ]);
  const HASH_FIELDS = Object.freeze([
    "analytic_policy_hash",
    "c2_assessment_hash",
    "consumer_receipt_hash",
    "direction_contract_hash",
    "evaluation_hash",
    "preregistration_adapter_binding_hash",
    "protocol_registration_hash",
    "stratum_assignment_hash",
  ]);
  const MODEL_KEYS = Object.freeze([
    "authority",
    "axes",
    "blockers",
    "metrics",
    "presentation_model_hash",
    "presentation_status",
    "provenance",
    "public_state",
    "schema_version",
    "static_fingerprint",
  ]);

  const STATE_CONTRACTS = Object.freeze({
    NOT_SUPPLIED: Object.freeze({
      axes: Object.freeze(["NOT_SUPPLIED", "SOURCE_NOT_SUPPLIED", "NOT_EVALUATED", "LOCKED"]),
      decision: "UNKNOWN",
      reason: "UNKNOWN",
      blockers: Object.freeze(["CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED"]),
      observed: false,
    }),
    UNKNOWN: Object.freeze({
      axes: Object.freeze(["UNKNOWN", "SOURCE_INVALID", "UNKNOWN", "LOCKED"]),
      decision: "UNKNOWN",
      reason: "UNKNOWN",
      blockers: Object.freeze(["CROSS_LAG_PROTOCOL_EVIDENCE_INVALID"]),
      observed: false,
    }),
    OBSERVED_PASS: Object.freeze({
      axes: Object.freeze(["VERIFIED_C2", "SEQUENCE_ORDER_UNATTESTED", "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL", "LOCKED"]),
      decision: "PASS",
      reason: "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_DETECTED",
      blockers: Object.freeze([
        "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
        "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED",
      ]),
      observed: true,
    }),
    OBSERVED_BLOCK: Object.freeze({
      axes: Object.freeze(["VERIFIED_C2", "CROSS_LAG_DEPENDENCE_OBSERVED", "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL", "LOCKED"]),
      decision: "BLOCK",
      reason: "CROSS_LAG_DEPENDENCE_DETECTED",
      blockers: Object.freeze([
        "CROSS_LAG_DEPENDENCE_DETECTED",
        "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
        "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED",
      ]),
      observed: true,
    }),
  });

  const OBSERVATION_COPY = Object.freeze({
    NOT_SUPPLIED: "No cross-lag evidence summary was supplied.",
    UNKNOWN: "Cross-lag evidence could not be verified for presentation.",
    OBSERVED_PASS: "No preregistered cross-lag dependence was detected in this candidate observation.",
    OBSERVED_BLOCK: "Cross-lag dependence was observed; correlated tickets must not be counted independently.",
  });
  const STATE_LABELS = Object.freeze({
    NOT_SUPPLIED: "Not supplied",
    UNKNOWN: "Unverified",
    OBSERVED_PASS: "Candidate non-detection",
    OBSERVED_BLOCK: "Dependence block",
  });
  const AXIS_DETAILS = Object.freeze({
    NOT_SUPPLIED: "No C3 summary was supplied.",
    SOURCE_NOT_SUPPLIED: "The evidence source is absent.",
    NOT_EVALUATED: "No maturity assessment is available.",
    UNKNOWN: "The supplied evidence could not be verified.",
    SOURCE_INVALID: "The supplied source failed the C3 contract.",
    VERIFIED_C2: "The C3 summary records a verified C2 replay.",
    SEQUENCE_ORDER_UNATTESTED: "Sequence order has not been attested.",
    CROSS_LAG_DEPENDENCE_OBSERVED: "Cross-lag dependence was observed.",
    CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL: "Candidate protocol binding is not formal registration.",
    LOCKED: "Research display only; execution remains locked.",
  });
  const BLOCKER_COPY = Object.freeze({
    CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED: "C3 protocol evidence was not supplied.",
    CROSS_LAG_PROTOCOL_EVIDENCE_INVALID: "C3 protocol evidence is invalid for presentation.",
    CROSS_LAG_DEPENDENCE_DETECTED: "Dependence was detected across preregistered lag tests.",
    CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED: "Sequence order has not been attested.",
    CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED: "Presentation remains an unmounted candidate.",
  });

  const SHA256_CONSTANTS = Object.freeze([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function isAsciiString(value) {
    if (typeof value !== "string") return false;
    for (let index = 0; index < value.length; index += 1) {
      if (value.charCodeAt(index) > 0x7f) return false;
    }
    return true;
  }

  function hasOnlyDataProperties(value) {
    const descriptors = Object.getOwnPropertyDescriptors(value);
    return Object.keys(descriptors).every((key) => {
      const descriptor = descriptors[key];
      return typeof descriptor.get !== "function" && typeof descriptor.set !== "function";
    });
  }

  function isDataRecord(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
    const prototype = Object.getPrototypeOf(value);
    return (prototype === Object.prototype || prototype === null) && hasOnlyDataProperties(value);
  }

  function isDataArray(value) {
    if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype || !hasOnlyDataProperties(value)) return false;
    if (Object.keys(value).length !== value.length) return false;
    for (let index = 0; index < value.length; index += 1) {
      if (!Object.prototype.hasOwnProperty.call(value, index)) return false;
    }
    return true;
  }

  function hasExactKeys(value, expectedKeys) {
    if (!isDataRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = Array.from(expectedKeys).sort();
    return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
  }

  function arraysEqual(left, right) {
    return isDataArray(left) && left.length === right.length && left.every((value, index) => value === right[index]);
  }

  function canonicalJson(value) {
    if (value === null) return "null";
    if (value === true) return "true";
    if (value === false) return "false";
    if (typeof value === "number") {
      if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw new TypeError("non-canonical number");
      return String(value);
    }
    if (typeof value === "string") {
      if (!isAsciiString(value)) throw new TypeError("non-ASCII string");
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      if (!isDataArray(value)) throw new TypeError("non-canonical array");
      return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
    }
    if (!isDataRecord(value)) throw new TypeError("non-canonical object");
    const keys = Object.keys(value).sort();
    for (const key of keys) {
      if (!isAsciiString(key)) throw new TypeError("non-ASCII key");
    }
    return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }

  function rotateRight(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  }

  function sha256Ascii(input) {
    if (!isAsciiString(input)) throw new TypeError("SHA-256 input must be ASCII");
    const bytes = [];
    for (let index = 0; index < input.length; index += 1) bytes.push(input.charCodeAt(index));
    const bitLength = bytes.length * 8;
    const highLength = Math.floor(bitLength / 0x100000000);
    const lowLength = bitLength >>> 0;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) bytes.push(0);
    bytes.push(
      (highLength >>> 24) & 0xff,
      (highLength >>> 16) & 0xff,
      (highLength >>> 8) & 0xff,
      highLength & 0xff,
      (lowLength >>> 24) & 0xff,
      (lowLength >>> 16) & 0xff,
      (lowLength >>> 8) & 0xff,
      lowLength & 0xff,
    );

    const state = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ]);
    const words = new Uint32Array(64);
    for (let offset = 0; offset < bytes.length; offset += 64) {
      for (let index = 0; index < 16; index += 1) {
        const start = offset + index * 4;
        words[index] = (
          (bytes[start] << 24)
          | (bytes[start + 1] << 16)
          | (bytes[start + 2] << 8)
          | bytes[start + 3]
        ) >>> 0;
      }
      for (let index = 16; index < 64; index += 1) {
        const s0 = rotateRight(words[index - 15], 7) ^ rotateRight(words[index - 15], 18) ^ (words[index - 15] >>> 3);
        const s1 = rotateRight(words[index - 2], 17) ^ rotateRight(words[index - 2], 19) ^ (words[index - 2] >>> 10);
        words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
      }

      let a = state[0];
      let b = state[1];
      let c = state[2];
      let d = state[3];
      let e = state[4];
      let f = state[5];
      let g = state[6];
      let h = state[7];
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choose = (e & f) ^ (~e & g);
        const temporary1 = (h + sum1 + choose + SHA256_CONSTANTS[index] + words[index]) >>> 0;
        const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const temporary2 = (sum0 + majority) >>> 0;
        h = g;
        g = f;
        f = e;
        e = (d + temporary1) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (temporary1 + temporary2) >>> 0;
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
    return Array.from(state, (value) => value.toString(16).padStart(8, "0")).join("");
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.values(value).forEach((item) => deepFreeze(item));
      Object.freeze(value);
    }
    return value;
  }

  function fixedAuthority() {
    const authority = {};
    AUTHORITY_KEYS.forEach((key) => {
      authority[key] = key === "descriptive_only";
    });
    return authority;
  }

  function validateAuthority(authority) {
    if (!hasExactKeys(authority, AUTHORITY_KEYS)) return false;
    return AUTHORITY_KEYS.every((key) => authority[key] === (key === "descriptive_only"));
  }

  function validateFacts(facts, observed) {
    if (!hasExactKeys(facts, FACT_KEYS)) return false;
    return facts.aggregate_projection_only === true
      && facts.c2_assessment_verified === observed
      && facts.formal_preregistration_bound === false
      && facts.sequence_order_attested === false;
  }

  function isCount(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function isBoundString(value) {
    if (typeof value !== "string" || !DECIMAL_PATTERN.test(value)) return false;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1;
  }

  function summaryPayload(summary) {
    const payload = {};
    SUMMARY_KEYS.forEach((key) => {
      if (key !== "public_summary_hash") payload[key] = summary[key];
    });
    return payload;
  }

  function validateSummary(summary, verification) {
    if (!hasExactKeys(summary, SUMMARY_KEYS)) return false;
    if (!hasExactKeys(verification, [
      "schema_version",
      "valid",
      "supplied_public_summary_hash",
      "rebuilt_public_summary_hash",
    ])) return false;
    if (summary.schema_version !== C3_SCHEMA
      || summary.verification_schema_version !== C3_VERIFICATION_SCHEMA
      || summary.static_fingerprint !== C3_FINGERPRINT
      || summary.c2_assessment_schema !== C2_SCHEMA
      || summary.c2_assessment_static_fingerprint !== C2_FINGERPRINT) return false;
    if (verification.schema_version !== C3_VERIFICATION_SCHEMA || verification.valid !== true) return false;
    if (!HASH_PATTERN.test(summary.public_summary_hash)
      || !HASH_PATTERN.test(verification.supplied_public_summary_hash)
      || !HASH_PATTERN.test(verification.rebuilt_public_summary_hash)) return false;
    const publicHash = summary.public_summary_hash.toLowerCase();
    if (verification.supplied_public_summary_hash.toLowerCase() !== publicHash
      || verification.rebuilt_public_summary_hash.toLowerCase() !== publicHash) return false;
    if (sha256Ascii(canonicalJson(summaryPayload(summary))) !== publicHash) return false;
    if (!validateAuthority(summary.authority)) return false;

    const contract = STATE_CONTRACTS[summary.public_state];
    if (!contract || !validateFacts(summary.facts, contract.observed)) return false;
    if (summary.source_axis !== contract.axes[0]
      || summary.gap_axis !== contract.axes[1]
      || summary.maturity_axis !== contract.axes[2]
      || summary.permission_axis !== contract.axes[3]
      || summary.gate_decision !== contract.decision
      || summary.gate_reason !== contract.reason
      || !arraysEqual(summary.blockers, contract.blockers)) return false;
    if (!isCount(summary.cross_stratum_pair_count)
      || !isCount(summary.lag_test_count)
      || !isCount(summary.dependent_test_count)
      || !isBoundString(summary.max_adjusted_absolute_lower)) return false;

    if (contract.observed) {
      if (summary.cross_stratum_pair_count < 1
        || summary.lag_test_count !== summary.cross_stratum_pair_count * 4
        || summary.dependent_test_count > summary.lag_test_count) return false;
      if (summary.public_state === "OBSERVED_PASS" && summary.dependent_test_count !== 0) return false;
      if (summary.public_state === "OBSERVED_BLOCK" && summary.dependent_test_count < 1) return false;
      if (!HASH_FIELDS.every((key) => HASH_PATTERN.test(summary[key]))) return false;
    } else {
      if (summary.cross_stratum_pair_count !== 0
        || summary.lag_test_count !== 0
        || summary.dependent_test_count !== 0
        || summary.max_adjusted_absolute_lower !== "0") return false;
      if (!HASH_FIELDS.every((key) => summary[key] === "")) return false;
    }
    return true;
  }

  function sealModel(baseModel) {
    const presentationModelHash = sha256Ascii(canonicalJson(baseModel));
    return deepFreeze({ ...baseModel, presentation_model_hash: presentationModelHash });
  }

  function modelFromSummary(summary) {
    const contract = STATE_CONTRACTS[summary.public_state];
    const observed = contract.observed;
    const axes = AXIS_ORDER.map((axis, index) => ({ axis, state: contract.axes[index] }));
    const metrics = observed ? {
      cross_stratum_pair_count: summary.cross_stratum_pair_count,
      dependent_test_count: summary.dependent_test_count,
      lag_test_count: summary.lag_test_count,
      max_adjusted_absolute_lower: summary.max_adjusted_absolute_lower,
    } : null;
    const provenance = observed ? {
      c2_assessment_hash: summary.c2_assessment_hash.toLowerCase(),
      consumer_receipt_hash: summary.consumer_receipt_hash.toLowerCase(),
      evaluation_hash: summary.evaluation_hash.toLowerCase(),
      public_summary_hash: summary.public_summary_hash.toLowerCase(),
    } : null;
    return sealModel({
      authority: fixedAuthority(),
      axes,
      blockers: Array.from(contract.blockers),
      metrics,
      presentation_status: PRESENTATION_STATUS,
      provenance,
      public_state: summary.public_state,
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
    });
  }

  function fixedModel(publicState) {
    const state = publicState === "NOT_SUPPLIED" ? "NOT_SUPPLIED" : "UNKNOWN";
    const contract = STATE_CONTRACTS[state];
    return sealModel({
      authority: fixedAuthority(),
      axes: AXIS_ORDER.map((axis, index) => ({ axis, state: contract.axes[index] })),
      blockers: Array.from(contract.blockers),
      metrics: null,
      presentation_status: PRESENTATION_STATUS,
      provenance: null,
      public_state: state,
      schema_version: MODEL_SCHEMA,
      static_fingerprint: PRESENTATION_FINGERPRINT,
    });
  }

  function buildCrossLagPresentationModel(envelope) {
    if (envelope === undefined || envelope === null) return fixedModel("NOT_SUPPLIED");
    try {
      if (!hasExactKeys(envelope, ["schema_version", "summary", "verification"])) return fixedModel("UNKNOWN");
      if (envelope.schema_version !== ENVELOPE_SCHEMA) return fixedModel("UNKNOWN");
      if (!validateSummary(envelope.summary, envelope.verification)) return fixedModel("UNKNOWN");
      return modelFromSummary(envelope.summary);
    } catch (_error) {
      return fixedModel("UNKNOWN");
    }
  }

  function validateModel(model) {
    try {
      if (!hasExactKeys(model, MODEL_KEYS)
        || model.schema_version !== MODEL_SCHEMA
        || model.static_fingerprint !== PRESENTATION_FINGERPRINT
        || model.presentation_status !== PRESENTATION_STATUS
        || !HASH_PATTERN.test(model.presentation_model_hash)
        || !validateAuthority(model.authority)) return false;
      const payload = {};
      MODEL_KEYS.forEach((key) => {
        if (key !== "presentation_model_hash") payload[key] = model[key];
      });
      if (sha256Ascii(canonicalJson(payload)) !== model.presentation_model_hash.toLowerCase()) return false;
      const contract = STATE_CONTRACTS[model.public_state];
      if (!contract || !isDataArray(model.axes) || model.axes.length !== AXIS_ORDER.length) return false;
      for (let index = 0; index < AXIS_ORDER.length; index += 1) {
        const axis = model.axes[index];
        if (!hasExactKeys(axis, ["axis", "state"])
          || axis.axis !== AXIS_ORDER[index]
          || axis.state !== contract.axes[index]) return false;
      }
      if (!arraysEqual(model.blockers, contract.blockers)) return false;
      if (!contract.observed) return model.metrics === null && model.provenance === null;
      if (!hasExactKeys(model.metrics, [
        "cross_stratum_pair_count",
        "dependent_test_count",
        "lag_test_count",
        "max_adjusted_absolute_lower",
      ]) || !hasExactKeys(model.provenance, [
        "c2_assessment_hash",
        "consumer_receipt_hash",
        "evaluation_hash",
        "public_summary_hash",
      ])) return false;
      if (!isCount(model.metrics.cross_stratum_pair_count)
        || !isCount(model.metrics.dependent_test_count)
        || !isCount(model.metrics.lag_test_count)
        || !isBoundString(model.metrics.max_adjusted_absolute_lower)
        || model.metrics.cross_stratum_pair_count < 1
        || model.metrics.lag_test_count !== model.metrics.cross_stratum_pair_count * 4
        || model.metrics.dependent_test_count > model.metrics.lag_test_count) return false;
      if (model.public_state === "OBSERVED_PASS" && model.metrics.dependent_test_count !== 0) return false;
      if (model.public_state === "OBSERVED_BLOCK" && model.metrics.dependent_test_count < 1) return false;
      return Object.values(model.provenance).every((value) => HASH_PATTERN.test(value));
    } catch (_error) {
      return false;
    }
  }

  function requireDocument(documentRef) {
    if (!documentRef
      || typeof documentRef.createElement !== "function"
      || typeof documentRef.createTextNode !== "function") {
      throw new TypeError("documentRef must provide createElement and createTextNode");
    }
  }

  function element(documentRef, tagName, classNames) {
    const node = documentRef.createElement(tagName);
    classNames.forEach((className) => node.classList.add(className));
    return node;
  }

  function textElement(documentRef, tagName, classNames, text) {
    const node = element(documentRef, tagName, classNames);
    node.appendChild(documentRef.createTextNode(text));
    return node;
  }

  function createCrossLagEvidenceCard(documentRef, suppliedModel) {
    requireDocument(documentRef);
    const model = validateModel(suppliedModel) ? suppliedModel : fixedModel("UNKNOWN");
    const stateClass = model.public_state.toLowerCase().replaceAll("_", "-");
    const rootNode = element(documentRef, "section", [
      "cross-lag-evidence-card",
      `cross-lag-evidence-card--${stateClass}`,
    ]);
    rootNode.setAttribute("aria-label", "Cross-lag dependence research evidence");
    rootNode.setAttribute("data-public-state", model.public_state);

    const rail = element(documentRef, "div", ["cross-lag-evidence-card__rail"]);
    rail.setAttribute("aria-hidden", "true");
    rootNode.appendChild(rail);

    const header = element(documentRef, "header", ["cross-lag-evidence-card__header"]);
    const titleGroup = element(documentRef, "div", ["cross-lag-evidence-card__title-group"]);
    titleGroup.appendChild(textElement(documentRef, "p", ["cross-lag-evidence-card__eyebrow"], "Research evidence / Candidate"));
    titleGroup.appendChild(textElement(documentRef, "h3", ["cross-lag-evidence-card__title"], "Cross-lag dependence"));
    header.appendChild(titleGroup);
    header.appendChild(textElement(documentRef, "span", ["cross-lag-evidence-card__state"], STATE_LABELS[model.public_state]));
    rootNode.appendChild(header);
    rootNode.appendChild(textElement(documentRef, "p", ["cross-lag-evidence-card__observation"], OBSERVATION_COPY[model.public_state]));

    const axes = element(documentRef, "dl", ["cross-lag-evidence-card__axes"]);
    model.axes.forEach((axis) => {
      const group = element(documentRef, "div", ["cross-lag-evidence-card__axis"]);
      group.setAttribute("data-axis", axis.axis.toLowerCase());
      group.appendChild(textElement(documentRef, "dt", ["cross-lag-evidence-card__axis-name"], axis.axis));
      group.appendChild(textElement(documentRef, "dd", ["cross-lag-evidence-card__axis-state"], axis.state));
      group.appendChild(textElement(documentRef, "dd", ["cross-lag-evidence-card__axis-detail"], AXIS_DETAILS[axis.state]));
      axes.appendChild(group);
    });
    rootNode.appendChild(axes);

    if (model.metrics) {
      const metrics = element(documentRef, "div", ["cross-lag-evidence-card__metrics"]);
      metrics.setAttribute("aria-label", "Aggregate diagnostics");
      const metricRows = [
        ["Cross-stratum pairs", String(model.metrics.cross_stratum_pair_count)],
        ["Preregistered lag tests", String(model.metrics.lag_test_count)],
        ["Dependent tests", String(model.metrics.dependent_test_count)],
        ["Max adjusted absolute lower", model.metrics.max_adjusted_absolute_lower],
      ];
      metricRows.forEach(([label, value]) => {
        const metric = element(documentRef, "div", ["cross-lag-evidence-card__metric"]);
        metric.appendChild(textElement(documentRef, "span", ["cross-lag-evidence-card__metric-label"], label));
        metric.appendChild(textElement(documentRef, "strong", ["cross-lag-evidence-card__metric-value"], value));
        metrics.appendChild(metric);
      });
      rootNode.appendChild(metrics);
    }

    const blockerSection = element(documentRef, "div", ["cross-lag-evidence-card__blockers"]);
    blockerSection.appendChild(textElement(documentRef, "p", ["cross-lag-evidence-card__section-label"], "Open blockers"));
    const blockerList = element(documentRef, "ul", ["cross-lag-evidence-card__blocker-list"]);
    model.blockers.forEach((blocker) => {
      blockerList.appendChild(textElement(documentRef, "li", ["cross-lag-evidence-card__blocker"], BLOCKER_COPY[blocker]));
    });
    blockerSection.appendChild(blockerList);
    rootNode.appendChild(blockerSection);

    if (model.provenance) {
      const provenance = element(documentRef, "div", ["cross-lag-evidence-card__provenance"]);
      provenance.appendChild(textElement(documentRef, "p", ["cross-lag-evidence-card__section-label"], "Provenance identifiers"));
      const rows = [
        ["Public summary", model.provenance.public_summary_hash],
        ["C2 assessment", model.provenance.c2_assessment_hash],
        ["Evaluation", model.provenance.evaluation_hash],
        ["Consumer receipt", model.provenance.consumer_receipt_hash],
      ];
      rows.forEach(([label, value]) => {
        const row = element(documentRef, "div", ["cross-lag-evidence-card__provenance-row"]);
        row.appendChild(textElement(documentRef, "span", ["cross-lag-evidence-card__provenance-label"], label));
        row.appendChild(textElement(documentRef, "code", ["cross-lag-evidence-card__hash"], value));
        provenance.appendChild(row);
      });
      rootNode.appendChild(provenance);
    }

    const footer = element(documentRef, "footer", ["cross-lag-evidence-card__permission"]);
    footer.appendChild(textElement(documentRef, "span", ["cross-lag-evidence-card__permission-mark"], "LOCKED"));
    footer.appendChild(documentRef.createTextNode("Locked: research display only"));
    rootNode.appendChild(footer);
    return rootNode;
  }

  return Object.freeze({
    buildCrossLagPresentationModel,
    constants: Object.freeze({
      C3_FINGERPRINT,
      C3_SCHEMA,
      C3_VERIFICATION_SCHEMA,
      ENVELOPE_SCHEMA,
      MODEL_SCHEMA,
      PRESENTATION_FINGERPRINT,
      PRESENTATION_STATUS,
    }),
    contractTestHooks: Object.freeze({ canonicalJson, sha256Ascii }),
    createCrossLagEvidenceCard,
  });
});
