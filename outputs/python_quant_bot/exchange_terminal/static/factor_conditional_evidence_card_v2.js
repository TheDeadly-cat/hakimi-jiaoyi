(function attachFactorConditionalEvidenceCardV2(root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiFactorConditionalEvidenceCardV2 = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const constants = Object.freeze({
    ENVELOPE_FINGERPRINT:
      "20260822-cross-lag-factor-conditional-presentation-envelope-2",
    ENVELOPE_SCHEMA:
      "strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v2",
    MODEL_SCHEMA:
      "strategy-correlation-cross-lag-factor-conditional-presentation-model-v2",
    PRESENTATION_FINGERPRINT:
      "20260822-cross-lag-factor-conditional-f5-unmounted-presentation-1",
    PRESENTATION_STATUS: "UNMOUNTED_CANDIDATE",
    REPORT_FINGERPRINT:
      "20260822-cross-lag-factor-conditional-report-consumer-2",
    REPORT_SCHEMA:
      "strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v2",
  });

  const AXIS_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  const FORBIDDEN_DETAIL_KEYS = new Set([
    "global_adjusted_absolute_lower",
    "left_identity",
    "private_recalculated_test_ledger_hash",
    "right_identity",
    "source_correlation",
  ]);
  const OUTER_AUTHORITY_KEYS = Object.freeze([
    "candidate_activation_allowed",
    "current_admission_allowed",
    "current_pointer_written",
    "descriptive_only",
    "global_two_view_multiplicity_registered",
    "live_order_allowed",
    "paper_authorized",
    "presentation_mounted",
    "profitability_claim_allowed",
    "report_consumer_v2_activated",
    "source_semantics_replayed_in_browser",
  ]);
  const REPORT_AUTHORITY_KEYS = Object.freeze([
    "candidate_activation_allowed",
    "current_admission_allowed",
    "current_pointer_written",
    "descriptive_only",
    "global_independence_proven",
    "live_order_allowed",
    "paper_authorized",
    "profitability_claim_allowed",
    "raw_independence_proven",
    "report_consumer_v2_activated",
    "residual_independence_proven",
  ]);

  function isPlainObject(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
      return false;
    }
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function exactKeys(value, expected) {
    if (!isPlainObject(value)) {
      return false;
    }
    const actual = Object.keys(value).sort();
    const wanted = Array.from(expected).sort();
    return (
      actual.length === wanted.length &&
      actual.every(function sameKey(key, index) {
        return key === wanted[index];
      })
    );
  }

  function strictCanonicalStringify(value) {
    if (value === null) {
      return "null";
    }
    if (typeof value === "boolean") {
      return value ? "true" : "false";
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new TypeError("nonfinite_number");
      }
      return JSON.stringify(value);
    }
    if (typeof value === "string") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return (
        "[" +
        value.map(function canonicalItem(item) {
          return strictCanonicalStringify(item);
        }).join(",") +
        "]"
      );
    }
    if (!isPlainObject(value)) {
      throw new TypeError("noncanonical_value");
    }
    return (
      "{" +
      Object.keys(value)
        .sort()
        .map(function canonicalEntry(key) {
          return JSON.stringify(key) + ":" + strictCanonicalStringify(value[key]);
        })
        .join(",") +
      "}"
    );
  }

  function utf8Bytes(text) {
    const bytes = [];
    for (const symbol of text) {
      const code = symbol.codePointAt(0);
      if (code <= 0x7f) {
        bytes.push(code);
      } else if (code <= 0x7ff) {
        bytes.push(0xc0 | (code >>> 6), 0x80 | (code & 0x3f));
      } else if (code <= 0xffff) {
        bytes.push(
          0xe0 | (code >>> 12),
          0x80 | ((code >>> 6) & 0x3f),
          0x80 | (code & 0x3f)
        );
      } else {
        bytes.push(
          0xf0 | (code >>> 18),
          0x80 | ((code >>> 12) & 0x3f),
          0x80 | ((code >>> 6) & 0x3f),
          0x80 | (code & 0x3f)
        );
      }
    }
    return bytes;
  }

  function rotateRight(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  }

  function sha256Hex(text) {
    const constantsK = [
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
    const hash = [
      0x6a09e667,
      0xbb67ae85,
      0x3c6ef372,
      0xa54ff53a,
      0x510e527f,
      0x9b05688c,
      0x1f83d9ab,
      0x5be0cd19,
    ];
    const bytes = utf8Bytes(text);
    const bitLength = bytes.length * 8;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) {
      bytes.push(0);
    }
    const high = Math.floor(bitLength / 0x100000000);
    const low = bitLength >>> 0;
    for (let shift = 24; shift >= 0; shift -= 8) {
      bytes.push((high >>> shift) & 0xff);
    }
    for (let shift = 24; shift >= 0; shift -= 8) {
      bytes.push((low >>> shift) & 0xff);
    }

    for (let offset = 0; offset < bytes.length; offset += 64) {
      const words = new Array(64);
      for (let index = 0; index < 16; index += 1) {
        const cursor = offset + index * 4;
        words[index] =
          ((bytes[cursor] << 24) |
            (bytes[cursor + 1] << 16) |
            (bytes[cursor + 2] << 8) |
            bytes[cursor + 3]) >>>
          0;
      }
      for (let index = 16; index < 64; index += 1) {
        const first = words[index - 15];
        const second = words[index - 2];
        const sigma0 =
          rotateRight(first, 7) ^ rotateRight(first, 18) ^ (first >>> 3);
        const sigma1 =
          rotateRight(second, 17) ^ rotateRight(second, 19) ^ (second >>> 10);
        words[index] =
          (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0;
      }

      let a = hash[0];
      let b = hash[1];
      let c = hash[2];
      let d = hash[3];
      let e = hash[4];
      let f = hash[5];
      let g = hash[6];
      let h = hash[7];
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choice = (e & f) ^ (~e & g);
        const temporary1 =
          (h + sum1 + choice + constantsK[index] + words[index]) >>> 0;
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
      hash[0] = (hash[0] + a) >>> 0;
      hash[1] = (hash[1] + b) >>> 0;
      hash[2] = (hash[2] + c) >>> 0;
      hash[3] = (hash[3] + d) >>> 0;
      hash[4] = (hash[4] + e) >>> 0;
      hash[5] = (hash[5] + f) >>> 0;
      hash[6] = (hash[6] + g) >>> 0;
      hash[7] = (hash[7] + h) >>> 0;
    }
    return hash
      .map(function hexWord(value) {
        return value.toString(16).padStart(8, "0");
      })
      .join("");
  }

  function cloneCanonical(value) {
    return JSON.parse(strictCanonicalStringify(value));
  }

  function sealEnvelopeForTest(envelope) {
    const copy = cloneCanonical(envelope);
    delete copy.envelope_hash;
    copy.envelope_hash = sha256Hex(strictCanonicalStringify(copy));
    return copy;
  }

  function verifyEnvelopeIntegrity(envelope) {
    if (!isPlainObject(envelope) || !isSha256(envelope.envelope_hash)) {
      return false;
    }
    try {
      const copy = cloneCanonical(envelope);
      const expected = copy.envelope_hash;
      delete copy.envelope_hash;
      return sha256Hex(strictCanonicalStringify(copy)) === expected;
    } catch (_error) {
      return false;
    }
  }

  function collectKeys(value, target) {
    const result = target || new Set();
    if (Array.isArray(value)) {
      value.forEach(function visit(item) {
        collectKeys(item, result);
      });
    } else if (isPlainObject(value)) {
      Object.keys(value).forEach(function visit(key) {
        result.add(key);
        collectKeys(value[key], result);
      });
    }
    return result;
  }

  function authorityLocked(authority, keys, allowGlobalFamily) {
    if (!exactKeys(authority, keys) || authority.descriptive_only !== true) {
      return false;
    }
    return keys.every(function locked(key) {
      if (key === "descriptive_only") {
        return authority[key] === true;
      }
      if (allowGlobalFamily && key === "global_two_view_multiplicity_registered") {
        return typeof authority[key] === "boolean";
      }
      return authority[key] === false;
    });
  }

  function shortHash(value) {
    if (!isSha256(value)) {
      return "not supplied";
    }
    return value.slice(0, 10) + "..." + value.slice(-6);
  }

  function unavailableAxes(reason) {
    return AXIS_ORDER.map(function axis(label) {
      return {
        detail: reason,
        id: label.toLowerCase(),
        label: label,
        tone: "unknown",
        value: "UNKNOWN",
      };
    });
  }

  function closedModel(reason, envelope) {
    const verificationState =
      isPlainObject(envelope) && typeof envelope.verification_state === "string"
        ? envelope.verification_state
        : "INVALID";
    return {
      axes: unavailableAxes(reason),
      blockers: [reason],
      detached: true,
      eyebrow: "TWO-VIEW FAMILY / DETACHED",
      integrityState: "INVALID_OR_UNAVAILABLE",
      metrics: [],
      modelSchema: constants.MODEL_SCHEMA,
      mounted: false,
      presentationFingerprint: constants.PRESENTATION_FINGERPRINT,
      presentationStatus: constants.PRESENTATION_STATUS,
      provenance: [],
      reportState: "UNKNOWN",
      sourceState: "UNKNOWN",
      statusTone: "unknown",
      subtitle: "Verified evidence is not available for this detached surface.",
      title: "Conditional evidence / global family",
      verificationState: verificationState,
      viewRows: [],
    };
  }

  function buildFactorConditionalPresentationModelV2(envelope) {
    if (!verifyEnvelopeIntegrity(envelope)) {
      return closedModel("ENVELOPE_INTEGRITY_INVALID", envelope);
    }
    if (
      envelope.schema_version !== constants.ENVELOPE_SCHEMA ||
      envelope.static_fingerprint !== constants.ENVELOPE_FINGERPRINT ||
      envelope.presentation_status !== constants.PRESENTATION_STATUS
    ) {
      return closedModel("ENVELOPE_CONTRACT_UNSUPPORTED", envelope);
    }
    if (!authorityLocked(envelope.authority, OUTER_AUTHORITY_KEYS, true)) {
      return closedModel("ENVELOPE_AUTHORITY_INVALID", envelope);
    }
    if (envelope.verification_state !== "VERIFIED") {
      return closedModel(envelope.envelope_reason || "REPORT_UNAVAILABLE", envelope);
    }
    const report = envelope.report;
    if (
      !isPlainObject(report) ||
      report.schema_version !== constants.REPORT_SCHEMA ||
      report.static_fingerprint !== constants.REPORT_FINGERPRINT ||
      !isSha256(report.verification_hash) ||
      report.verification_hash !== envelope.source_report_hash ||
      report.source_f1_verification_hash !== envelope.source_f1_verification_hash ||
      report.source_two_view_gate_evaluation_hash !==
        envelope.source_two_view_gate_evaluation_hash
    ) {
      return closedModel("REPORT_CONTRACT_INVALID", envelope);
    }
    if (!authorityLocked(report.authority, REPORT_AUTHORITY_KEYS, false)) {
      return closedModel("REPORT_AUTHORITY_INVALID", envelope);
    }
    const forbidden = collectKeys(report);
    for (const key of FORBIDDEN_DETAIL_KEYS) {
      if (forbidden.has(key)) {
        return closedModel("FORBIDDEN_DETAIL_FIELD", envelope);
      }
    }
    if (!Array.isArray(report.blockers) || report.blockers.some(function invalid(item) {
      return typeof item !== "string";
    })) {
      return closedModel("REPORT_BLOCKERS_INVALID", envelope);
    }
    if (report.source_state === "UNKNOWN") {
      const model = closedModel("VERIFIED_UNKNOWN_CLOSURE", envelope);
      model.integrityState = "VERIFIED_ENVELOPE";
      model.verificationState = "VERIFIED";
      model.provenance = [
        {
          fullHash: report.verification_hash,
          label: "F4 report",
          value: shortHash(report.verification_hash),
        },
      ];
      return model;
    }
    if (
      report.source_state !== "OBSERVED" ||
      !["PASS", "BLOCK"].includes(report.global_recalibrated_decision) ||
      !Array.isArray(report.view_summaries) ||
      report.view_summaries.length !== 2 ||
      !Array.isArray(report.views) ||
      report.views.join("|") !== "RAW|RESIDUAL"
    ) {
      return closedModel("REPORT_AGGREGATE_INVALID", envelope);
    }

    const blocked = report.global_recalibrated_decision === "BLOCK";
    const viewRows = report.view_summaries.map(function viewSummary(summary, index) {
      if (!isPlainObject(summary) || summary.view !== report.views[index]) {
        throw new TypeError("view_summary_invalid");
      }
      return {
        globalDependent: summary.global_dependent_test_count,
        maxGlobalLower: summary.max_global_adjusted_absolute_lower,
        sourceDecision: summary.source_gate_decision,
        sourceDependent: summary.source_dependent_test_count,
        view: summary.view,
      };
    });
    const axes = [
      {
        detail: "F1 receipt and F3 gate replayed with shared source hashes.",
        id: "source",
        label: "SOURCE",
        tone: "verified",
        value: "F1 + F3 VERIFIED",
      },
      {
        detail: blocked
          ? "The preregistered global family retains a dependence block."
          : "No global-family dependence was detected in this candidate view.",
        id: "gap",
        label: "GAP",
        tone: blocked ? "blocked" : "observed",
        value: report.gap_state,
      },
      {
        detail: "Candidate evidence; registration timing remains unattested.",
        id: "maturity",
        label: "MATURITY",
        tone: "candidate",
        value: report.maturity_state,
      },
      {
        detail: "Research-only surface with no execution authority.",
        id: "permission",
        label: "PERMISSION",
        tone: "locked",
        value: report.permission_state,
      },
    ];
    return {
      axes: axes,
      blockers: report.blockers.slice(),
      detached: true,
      eyebrow: "TWO-VIEW FAMILY / DETACHED",
      integrityState: "VERIFIED_ENVELOPE",
      metrics: [
        { label: "Views", value: String(report.view_count) },
        {
          label: "Family tests",
          value:
            String(report.per_view_test_count) +
            " + " +
            String(report.per_view_test_count) +
            " = " +
            String(report.global_test_count),
        },
        { label: "Family alpha", value: String(report.family_alpha) },
        {
          label: "Global dependent",
          value: String(report.global_dependent_test_count),
        },
      ],
      modelSchema: constants.MODEL_SCHEMA,
      mounted: false,
      presentationFingerprint: constants.PRESENTATION_FINGERPRINT,
      presentationStatus: constants.PRESENTATION_STATUS,
      provenance: [
        {
          fullHash: report.verification_hash,
          label: "F4 report",
          value: shortHash(report.verification_hash),
        },
        {
          fullHash: report.source_f1_verification_hash,
          label: "F1 receipt",
          value: shortHash(report.source_f1_verification_hash),
        },
        {
          fullHash: report.source_two_view_gate_evaluation_hash,
          label: "F3 gate",
          value: shortHash(report.source_two_view_gate_evaluation_hash),
        },
        {
          fullHash: report.source_family_registration_hash,
          label: "Family registration",
          value: shortHash(report.source_family_registration_hash),
        },
      ],
      reportState: report.report_state,
      sourceState: report.source_state,
      statusTone: blocked ? "blocked" : "observed",
      subtitle: "One preregistered family across raw and residual views.",
      title: "Conditional evidence / global family",
      verificationState: envelope.verification_state,
      viewRows: viewRows,
    };
  }

  function element(documentRef, tagName, className, text) {
    const node = documentRef.createElement(tagName);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = String(text);
    }
    return node;
  }

  function createFactorConditionalEvidenceCardV2(envelope, options) {
    const settings = options || {};
    const documentRef = settings.document ||
      (typeof document === "object" ? document : null);
    if (!documentRef || typeof documentRef.createElement !== "function") {
      throw new TypeError("document_required");
    }
    const model = buildFactorConditionalPresentationModelV2(envelope);
    const card = element(documentRef, "article", "f5-evidence-card");
    card.setAttribute("aria-label", model.title);
    card.setAttribute("data-f5-state", model.statusTone);
    card.setAttribute("data-presentation-status", model.presentationStatus);

    const header = element(documentRef, "header", "f5-evidence-card__header");
    const headingGroup = element(
      documentRef,
      "div",
      "f5-evidence-card__heading-group"
    );
    headingGroup.append(
      element(documentRef, "p", "f5-evidence-card__eyebrow", model.eyebrow),
      element(documentRef, "h2", "f5-evidence-card__title", model.title),
      element(documentRef, "p", "f5-evidence-card__subtitle", model.subtitle)
    );
    const status = element(
      documentRef,
      "span",
      "f5-evidence-card__status",
      model.statusTone.toUpperCase()
    );
    header.append(headingGroup, status);
    card.append(header);

    const rail = element(documentRef, "ol", "f5-evidence-card__axis-rail");
    model.axes.forEach(function renderAxis(axis, index) {
      const item = element(documentRef, "li", "f5-evidence-card__axis");
      item.setAttribute("data-axis-tone", axis.tone);
      item.style.setProperty("--f5-axis-index", String(index));
      item.append(
        element(documentRef, "span", "f5-evidence-card__axis-label", axis.label),
        element(documentRef, "strong", "f5-evidence-card__axis-value", axis.value),
        element(documentRef, "span", "f5-evidence-card__axis-detail", axis.detail)
      );
      rail.append(item);
    });
    card.append(rail);

    const body = element(documentRef, "div", "f5-evidence-card__body");
    const evidence = element(documentRef, "section", "f5-evidence-card__evidence");
    evidence.append(
      element(documentRef, "h3", "f5-evidence-card__section-title", "Family evidence")
    );
    const metrics = element(documentRef, "dl", "f5-evidence-card__metrics");
    model.metrics.forEach(function renderMetric(metric) {
      const item = element(documentRef, "div", "f5-evidence-card__metric");
      item.append(
        element(documentRef, "dt", "f5-evidence-card__metric-label", metric.label),
        element(documentRef, "dd", "f5-evidence-card__metric-value", metric.value)
      );
      metrics.append(item);
    });
    evidence.append(metrics);

    const views = element(documentRef, "div", "f5-evidence-card__views");
    model.viewRows.forEach(function renderView(view) {
      const row = element(documentRef, "div", "f5-evidence-card__view-row");
      row.setAttribute(
        "data-view-state",
        view.globalDependent > 0 ? "blocked" : "observed"
      );
      row.append(
        element(documentRef, "strong", "f5-evidence-card__view-name", view.view),
        element(
          documentRef,
          "span",
          "f5-evidence-card__view-decision",
          "Source " + String(view.sourceDecision)
        ),
        element(
          documentRef,
          "span",
          "f5-evidence-card__view-count",
          "Global dependent " + String(view.globalDependent)
        ),
        element(
          documentRef,
          "span",
          "f5-evidence-card__view-bound",
          "Max lower " + String(view.maxGlobalLower)
        )
      );
      views.append(row);
    });
    evidence.append(views);

    const blockers = element(documentRef, "section", "f5-evidence-card__blockers");
    blockers.append(
      element(documentRef, "h3", "f5-evidence-card__section-title", "Open blockers")
    );
    const blockerList = element(documentRef, "ul", "f5-evidence-card__blocker-list");
    model.blockers.forEach(function renderBlocker(blocker) {
      blockerList.append(
        element(documentRef, "li", "f5-evidence-card__blocker", blocker)
      );
    });
    blockers.append(blockerList);
    body.append(evidence, blockers);
    card.append(body);

    const footer = element(documentRef, "footer", "f5-evidence-card__footer");
    const provenance = element(
      documentRef,
      "div",
      "f5-evidence-card__provenance"
    );
    model.provenance.forEach(function renderProvenance(item) {
      const token = element(documentRef, "span", "f5-evidence-card__hash");
      token.setAttribute("title", item.fullHash);
      token.append(
        element(documentRef, "span", "f5-evidence-card__hash-label", item.label),
        element(documentRef, "code", "f5-evidence-card__hash-value", item.value)
      );
      provenance.append(token);
    });
    footer.append(
      provenance,
      element(
        documentRef,
        "p",
        "f5-evidence-card__disclaimer",
        "Descriptive research evidence. No execution authority."
      )
    );
    card.append(footer);
    return card;
  }

  return Object.freeze({
    buildFactorConditionalPresentationModelV2:
      buildFactorConditionalPresentationModelV2,
    constants: constants,
    contractTestHooks: Object.freeze({
      collectKeys: collectKeys,
      sealEnvelope: sealEnvelopeForTest,
      sha256Hex: sha256Hex,
      strictCanonicalStringify: strictCanonicalStringify,
      verifyEnvelopeIntegrity: verifyEnvelopeIntegrity,
    }),
    createFactorConditionalEvidenceCardV2:
      createFactorConditionalEvidenceCardV2,
  });
});
