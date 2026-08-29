(function attachDownsideTailLockboard(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HakimiDownsideTailLockboard = api;
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const SUMMARY_SCHEMA = "strategy-correlation-downside-tail-public-summary-v1";
  const STATIC_FINGERPRINT = "20260821-downside-tail-public-lockboard-1";

  const permissionKeys = [
    "descriptive_only", "independence_proven", "count_as_independent_allowed",
    "candidate_binding_activation_allowed", "formal_report_binding_allowed",
    "formal_registry_activation_allowed", "profitability_claim_allowed",
    "current_admission_allowed", "current_writer_activation_allowed",
    "paper_authorized", "live_order_allowed",
  ];
  const redactionKeys = [
    "protocol_hash_exposed", "registration_hash_exposed", "evaluation_hash_exposed",
    "consumer_verification_hash_exposed", "assessment_hash_exposed",
    "identity_set_hash_exposed", "stratum_assignment_hash_exposed",
    "observation_ids_exposed", "returns_exposed", "pair_identities_exposed",
    "strata_exposed", "overlap_values_exposed", "p_values_exposed",
    "profitability_metrics_exposed",
  ];

  function exactKeys(value, keys) {
    return value && typeof value === "object" && !Array.isArray(value) &&
      Object.keys(value).sort().join("|") === [...keys].sort().join("|");
  }

  function permissionIsClosed(permission) {
    if (!exactKeys(permission, permissionKeys)) return false;
    if (permission.descriptive_only !== true) return false;
    return permissionKeys.every((key) => key === "descriptive_only" || permission[key] === false);
  }

  function redactionIsClosed(redaction) {
    return exactKeys(redaction, redactionKeys) && redactionKeys.every((key) => redaction[key] === false);
  }

  function countsAreNull(source) {
    return ["observation_count", "tail_event_count", "cross_stratum_pair_count", "coupled_pair_count"]
      .every((key) => source[key] === null);
  }

  function observedCountsAreValid(source, decision) {
    const values = [source.observation_count, source.tail_event_count, source.cross_stratum_pair_count, source.coupled_pair_count];
    if (!values.every((value) => Number.isInteger(value) && value >= 0)) return false;
    if (source.observation_count < 60 || source.tail_event_count < 12 || source.cross_stratum_pair_count < 1) return false;
    if (source.coupled_pair_count > source.cross_stratum_pair_count) return false;
    if (decision === "PASS" && source.coupled_pair_count !== 0) return false;
    if (decision === "BLOCK" && source.coupled_pair_count < 1) return false;
    return true;
  }

  function classifySummary(summary) {
    if (!exactKeys(summary, ["schema_version", "static_fingerprint", "source", "gap", "maturity", "permission", "redaction"])) return "UNKNOWN";
    if (summary.schema_version !== SUMMARY_SCHEMA || summary.static_fingerprint !== STATIC_FINGERPRINT) return "UNKNOWN";
    if (!exactKeys(summary.source, ["state", "evidence_contract", "observation_count", "tail_event_count", "cross_stratum_pair_count", "coupled_pair_count"])) return "UNKNOWN";
    if (!exactKeys(summary.gap, ["gate_decision", "gate_reason", "binding_status", "protocol_status"])) return "UNKNOWN";
    if (!exactKeys(summary.maturity, ["state", "formal_registration_status", "current_status"])) return "UNKNOWN";
    if (!permissionIsClosed(summary.permission) || !redactionIsClosed(summary.redaction)) return "UNKNOWN";
    if (summary.source.evidence_contract !== "PREREGISTERED_DOWNSIDE_TAIL_CANDIDATE_V1") return "UNKNOWN";
    if (summary.maturity.formal_registration_status !== "NOT_ESTABLISHED" || summary.maturity.current_status !== "LOCKED") return "UNKNOWN";

    if (summary.source.state === "NOT_SUPPLIED" && countsAreNull(summary.source) &&
      summary.gap.gate_decision === "NOT_SUPPLIED" && summary.gap.gate_reason === "NOT_SUPPLIED" &&
      summary.gap.binding_status === "NOT_SUPPLIED" && summary.gap.protocol_status === "NOT_SUPPLIED" &&
      summary.maturity.state === "NOT_SUPPLIED") return "NOT_SUPPLIED";

    if (summary.source.state === "UNKNOWN" && countsAreNull(summary.source) &&
      summary.gap.gate_decision === "UNKNOWN" && summary.gap.gate_reason === "SOURCE_CONTRACT_UNKNOWN" &&
      summary.gap.binding_status === "UNKNOWN" && summary.gap.protocol_status === "UNKNOWN" &&
      summary.maturity.state === "UNKNOWN") return "UNKNOWN";

    if (summary.source.state === "UNKNOWN" && countsAreNull(summary.source) &&
      summary.gap.gate_decision === "BLOCK" && summary.gap.gate_reason === "SOURCE_EVALUATION_UNKNOWN" &&
      summary.gap.binding_status === "CANDIDATE_BLOCKED" && summary.gap.protocol_status === "VERIFIED_CANDIDATE" &&
      summary.maturity.state === "CANDIDATE_BLOCKED_NOT_FORMAL") return "CANDIDATE_BLOCKED";

    if (summary.source.state === "OBSERVED" && summary.gap.binding_status === "CANDIDATE_BOUND" &&
      summary.gap.protocol_status === "VERIFIED_CANDIDATE" && summary.maturity.state === "CANDIDATE_BOUND_NOT_FORMAL" &&
      ["PASS", "BLOCK"].includes(summary.gap.gate_decision) && observedCountsAreValid(summary.source, summary.gap.gate_decision)) {
      const expectedReason = summary.gap.gate_decision === "PASS"
        ? "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
        : "DOWNSIDE_TAIL_COUPLING_DETECTED";
      if (summary.gap.gate_reason !== expectedReason) return "UNKNOWN";
      return summary.gap.gate_decision === "PASS" ? "OBSERVED_PASS" : "OBSERVED_BLOCK";
    }
    return "UNKNOWN";
  }

  function copyFor(kind) {
    const copies = {
      NOT_SUPPLIED: ["No candidate evidence supplied", "The downside-tail source has not been supplied.", "not-supplied"],
      UNKNOWN: ["Contract cannot be verified", "The supplied source or binding contract fails closed.", "unknown"],
      CANDIDATE_BLOCKED: ["Candidate source remains blocked", "A sealed source exists but is not evaluable as observed evidence.", "blocked"],
      OBSERVED_PASS: ["Candidate tail gate is clear", "No significant high downside-tail overlap was detected by this candidate gate.", "clear"],
      OBSERVED_BLOCK: ["Downside-tail coupling detected", "Cross-stratum downside-tail coupling remains visible and blocks this gate.", "blocked"],
    };
    return copies[kind] || copies.UNKNOWN;
  }

  function presentDownsideTailLockboard(summary) {
    const kind = classifySummary(summary);
    const [headline, detail, tone] = copyFor(kind);
    const observed = kind === "OBSERVED_PASS" || kind === "OBSERVED_BLOCK";
    const sourceValue = observed ? "OBSERVED" : kind === "NOT_SUPPLIED" ? "NOT SUPPLIED" : "UNKNOWN";
    const gateValue = kind === "OBSERVED_PASS" ? "PASS" : (kind === "OBSERVED_BLOCK" || kind === "CANDIDATE_BLOCKED") ? "BLOCK" : kind === "NOT_SUPPLIED" ? "NOT SUPPLIED" : "UNKNOWN";
    const maturityValue = observed ? "CANDIDATE / NOT FORMAL" : kind === "CANDIDATE_BLOCKED" ? "CANDIDATE BLOCKED" : kind === "NOT_SUPPLIED" ? "NOT SUPPLIED" : "UNKNOWN";
    return {
      kind, tone, eyebrow: "DOWNSIDE TAIL / CANDIDATE SEAL", title: headline, detail,
      nodes: [
        { code: "SRC", label: "SOURCE", value: sourceValue, tone: observed ? "ink" : tone },
        { code: "GAP", label: "GAP", value: gateValue, tone },
        { code: "MAT", label: "MATURITY", value: maturityValue, tone: observed ? "candidate" : tone },
        { code: "PERM", label: "PERMISSION", value: "ALL PATHS LOCKED", tone: "locked" },
      ],
      metrics: observed ? [
        ["OBS", String(summary.source.observation_count)],
        ["TAIL", String(summary.source.tail_event_count)],
        ["X-STRATA", String(summary.source.cross_stratum_pair_count)],
        ["COUPLED", String(summary.source.coupled_pair_count)],
      ] : [["OBS", "--"], ["TAIL", "--"], ["X-STRATA", "--"], ["COUPLED", "--"]],
      seals: ["FORMAL / NOT ESTABLISHED", "CURRENT / LOCKED", "PAPER / LOCKED", "LIVE / HARD LOCK"],
    };
  }

  function element(documentRef, tag, className, text) {
    const node = documentRef.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderDownsideTailLockboard(summary, target) {
    const model = presentDownsideTailLockboard(summary);
    if (!target || typeof target.replaceChildren !== "function" || !target.ownerDocument || typeof target.ownerDocument.createElement !== "function") return model;
    const doc = target.ownerDocument;
    const card = element(doc, "article", `dt-lockboard dt-lockboard--${model.tone}`);
    const header = element(doc, "header", "dt-lockboard__header");
    header.append(element(doc, "p", "dt-lockboard__eyebrow", model.eyebrow));
    header.append(element(doc, "h2", "dt-lockboard__title", model.title));
    header.append(element(doc, "p", "dt-lockboard__detail", model.detail));
    card.append(header);
    const circuit = element(doc, "div", "dt-lockboard__circuit");
    model.nodes.forEach((item, index) => {
      const node = element(doc, "section", `dt-lockboard__node dt-lockboard__node--${item.tone}`);
      node.style.setProperty("--dt-index", String(index));
      node.append(element(doc, "span", "dt-lockboard__code", item.code));
      node.append(element(doc, "span", "dt-lockboard__label", item.label));
      node.append(element(doc, "strong", "dt-lockboard__value", item.value));
      circuit.append(node);
    });
    card.append(circuit);
    const metrics = element(doc, "dl", "dt-lockboard__metrics");
    model.metrics.forEach(([label, value]) => {
      const item = element(doc, "div", "dt-lockboard__metric");
      item.append(element(doc, "dt", "dt-lockboard__metric-label", label));
      item.append(element(doc, "dd", "dt-lockboard__metric-value", value));
      metrics.append(item);
    });
    card.append(metrics);
    const footer = element(doc, "footer", "dt-lockboard__seals");
    model.seals.forEach((seal) => footer.append(element(doc, "span", "dt-lockboard__seal", seal)));
    card.append(footer);
    target.replaceChildren(card);
    return model;
  }

  return { SUMMARY_SCHEMA, STATIC_FINGERPRINT, presentDownsideTailLockboard, renderDownsideTailLockboard };
});
