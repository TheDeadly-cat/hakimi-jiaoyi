(function (root, factory) {
  const strictJson = typeof module === "object" && module.exports
    ? require("./strict_canonical_json_v1.js")
    : root && root.HakimiStrictCanonicalJsonV1;
  const api = factory(strictJson);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskWeightedDiversificationCardV4 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (strictJson) {
  "use strict";

  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v4";
  const PROJECTION_STATIC_FINGERPRINT =
    "20260823-weighted-diversification-public-projection-v4-lock-1";
  const CARD_SCHEMA_VERSION = "portfolio-risk-weighted-diversification-card-v4";
  const CARD_STATIC_FINGERPRINT =
    "20260823-weighted-diversification-card-v4-sealed-projection-lock-2";
  const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);
  const FLOAT_PATHS = Object.freeze(new Set([
    "weighted_diversification.dominant_cluster_share_of_active_gross_pct",
    "weighted_diversification.minimum_weighted_effective_cluster_count",
    "weighted_diversification.weighted_effective_cluster_count"
  ]));

  const TOP_KEYS = [
    "authority", "decision", "facts", "local_decision", "projection_hash",
    "schema_version", "source", "stages", "static_fingerprint", "status",
    "weighted_diversification"
  ];
  const SOURCE_KEYS = [
    "adapter_v3_hash", "adapter_v4_exactly_verified", "adapter_v4_hash",
    "adapter_v4_implementation_sha256", "adapter_v4_schema_version",
    "v1_budget_hash", "weighted_budget_v2_hash"
  ];
  const LOCAL_KEYS = ["blockers", "decision", "risk_increasing", "status", "warnings"];
  const WEIGHTED_KEYS = [
    "assessment", "dominant_cluster_share_of_active_gross_pct", "gate_applied",
    "minimum_weighted_effective_cluster_count", "unweighted_effective_cluster_count",
    "weighted_effective_cluster_count"
  ];
  const FACT_KEYS = [
    "cluster_exposure_rows_embedded", "component_documents_embedded",
    "correlation_matrices_embedded", "positions_embedded", "profitability_proven",
    "projection_only", "runtime_consumer_bound", "source_document_embedded", "ui_mounted"
  ];
  const AUTHORITY_KEYS = [
    "current_admission_allowed", "current_pointer_written",
    "formal_registry_activation_allowed", "live_order_allowed", "migration_allowed",
    "paper_authorized", "presentation_only", "research_only",
    "runtime_gate_activation_allowed", "shadow_consumer_activation_allowed", "writer_allowed"
  ];
  const STAGE_KEYS = ["detail", "key", "state"];
  const DECISION_GAPS = Object.freeze({
    WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY:
      ["NONE_OBSERVED", "NO_LOCAL_WEIGHTED_POLICY_GAP_OBSERVED"],
    RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED:
      ["NONE_OBSERVED", "VERIFIED_RISK_REDUCTION_WEIGHTED_EXEMPTION"],
    BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION:
      ["DECLARED", "WEIGHTED_CLUSTER_DIVERSIFICATION"],
    BLOCKED_ADAPTER_V3_COMPONENT: ["DECLARED", "ADAPTER_V3_COMPONENT"],
    BLOCKED_WEIGHTED_BUDGET_COMPONENT: ["DECLARED", "WEIGHTED_BUDGET_COMPONENT"],
    BLOCKED_WEIGHTED_ADAPTER_COMPONENT_VERIFICATION:
      ["DECLARED", "ADAPTER_V4_COMPONENT_OR_LINEAGE"]
  });

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
      && Object.getPrototypeOf(value) === Object.prototype;
  }

  function hasExactKeys(value, keys) {
    if (!isPlainObject(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = keys.slice().sort();
    return actual.length === expected.length
      && actual.every((key, index) => key === expected[index]);
  }

  function isHash(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function pythonCanonicalNumber(value, path) {
    if (!Number.isFinite(value) || Object.is(value, -0)) {
      throw new TypeError("projection number is not canonical");
    }
    if (FLOAT_PATHS.has(path.join("."))) {
      const rendered = String(value);
      if (/[eE]/.test(rendered)) {
        throw new TypeError("projection float exponent is unsupported");
      }
      return Number.isInteger(value) ? `${rendered}.0` : rendered;
    }
    if (!Number.isSafeInteger(value)) {
      throw new TypeError("projection integer is not canonical");
    }
    return String(value);
  }

  function pythonCanonicalProjectionStringify(value) {
    function encode(current, path) {
      if (current === null) return "null";
      if (typeof current === "boolean") return current ? "true" : "false";
      if (typeof current === "string") return JSON.stringify(current);
      if (typeof current === "number") return pythonCanonicalNumber(current, path);
      if (Array.isArray(current)) {
        for (let index = 0; index < current.length; index += 1) {
          if (!Object.hasOwn(current, index)) {
            throw new TypeError("sparse projection array is not canonical");
          }
        }
        return `[${current.map((item, index) => (
          encode(item, path.concat(String(index)))
        )).join(",")}]`;
      }
      if (isPlainObject(current)) {
        if (Object.getOwnPropertySymbols(current).length !== 0) {
          throw new TypeError("projection symbol key is not canonical");
        }
        return `{${Object.keys(current).sort().map((key) => (
          `${JSON.stringify(key)}:${encode(current[key], path.concat(key))}`
        )).join(",")}}`;
      }
      throw new TypeError("projection value is not canonical JSON");
    }
    return encode(value, []);
  }

  function verifyPortfolioRiskProjectionSealV4(value) {
    if (!isPlainObject(value)
      || !isHash(value.projection_hash)
      || !strictJson
      || typeof strictJson.sha256Hex !== "function") return false;
    try {
      const payload = {};
      Object.keys(value).forEach((key) => {
        if (key !== "projection_hash") payload[key] = value[key];
      });
      return strictJson.sha256Hex(
        pythonCanonicalProjectionStringify(payload)
      ) === value.projection_hash;
    } catch (_error) {
      return false;
    }
  }

  function isFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function isStringArray(value) {
    return Array.isArray(value) && value.every((item) => typeof item === "string");
  }

  function authorityLocked(value) {
    return hasExactKeys(value, AUTHORITY_KEYS)
      && value.research_only === true
      && value.presentation_only === true
      && AUTHORITY_KEYS.filter((key) => !["research_only", "presentation_only"].includes(key))
        .every((key) => value[key] === false);
  }

  function factsAreMinimal(value) {
    return hasExactKeys(value, FACT_KEYS)
      && value.projection_only === true
      && FACT_KEYS.filter((key) => key !== "projection_only")
        .every((key) => value[key] === false);
  }

  function weightedIsConsistent(value, local) {
    if (!hasExactKeys(value, WEIGHTED_KEYS)
      || value.minimum_weighted_effective_cluster_count !== 1.5) return false;
    if (local.risk_increasing === false) {
      return value.assessment === "NOT_APPLICABLE"
        && value.unweighted_effective_cluster_count === null
        && value.weighted_effective_cluster_count === null
        && value.dominant_cluster_share_of_active_gross_pct === null
        && value.gate_applied === false;
    }
    if (!Number.isInteger(value.unweighted_effective_cluster_count)
      || value.unweighted_effective_cluster_count <= 0
      || !isFiniteNumber(value.weighted_effective_cluster_count)
      || value.weighted_effective_cluster_count <= 0
      || !isFiniteNumber(value.dominant_cluster_share_of_active_gross_pct)
      || value.dominant_cluster_share_of_active_gross_pct < 0
      || value.dominant_cluster_share_of_active_gross_pct > 100
      || typeof value.gate_applied !== "boolean") return false;
    const expected = local.decision === "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION"
      ? "CONCENTRATED" : local.status === "PASS" ? "SUFFICIENT" : "UPSTREAM_BLOCKED";
    return value.assessment === expected;
  }

  function stagesAreConsistent(stages, local) {
    if (!Array.isArray(stages) || stages.length !== STAGE_ORDER.length) return false;
    if (!stages.every((stage) => hasExactKeys(stage, STAGE_KEYS))) return false;
    if (!stages.every((stage, index) => stage.key === STAGE_ORDER[index])) return false;
    const gap = DECISION_GAPS[local.decision];
    if (!gap || stages[0].state !== "VERIFIED"
      || stages[0].detail !== "ADAPTER_V4_EXACT_REBUILD"
      || stages[1].state !== gap[0] || stages[1].detail !== gap[1]
      || stages[2].detail !== local.decision
      || stages[2].state !== (local.status === "PASS" ? "LOCAL_POLICY_SATISFIED" : "LOCAL_POLICY_BLOCKED")
      || stages[3].state !== "UNAUTHORIZED"
      || stages[3].detail !== "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY") return false;
    return true;
  }

  function validProjection(value) {
    if (!hasExactKeys(value, TOP_KEYS)
      || value.schema_version !== PROJECTION_SCHEMA_VERSION
      || value.static_fingerprint !== PROJECTION_STATIC_FINGERPRINT
      || value.status !== "PASS"
      || value.decision !== "EXACT_WEIGHTED_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED"
      || !isHash(value.projection_hash)) return false;
    if (!hasExactKeys(value.source, SOURCE_KEYS)
      || value.source.adapter_v4_exactly_verified !== true
      || !isHash(value.source.adapter_v4_hash)
      || !isHash(value.source.adapter_v4_implementation_sha256)
      || !isHash(value.source.adapter_v3_hash)
      || !isHash(value.source.weighted_budget_v2_hash)
      || !isHash(value.source.v1_budget_hash)) return false;
    if (!hasExactKeys(value.local_decision, LOCAL_KEYS)) return false;
    const local = value.local_decision;
    if (!["PASS", "BLOCK"].includes(local.status)
      || !Object.hasOwn(DECISION_GAPS, local.decision)
      || typeof local.risk_increasing !== "boolean"
      || !isStringArray(local.blockers)
      || !isStringArray(local.warnings)) return false;
    return weightedIsConsistent(value.weighted_diversification, local)
      && stagesAreConsistent(value.stages, local)
      && factsAreMinimal(value.facts)
      && authorityLocked(value.authority)
      && verifyPortfolioRiskProjectionSealV4(value);
  }

  function unknownModel() {
    return {
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      tone: "unknown",
      kicker: "PORTFOLIO RISK / WEIGHT-AWARE SHADOW",
      title: "Diversification is a weight, not a label",
      summary: "Projection contract is unknown. No permission can be inferred.",
      metrics: [
        { label: "Cluster labels", value: "--", note: "unweighted" },
        { label: "Effective clusters", value: "--", note: "gross weighted" },
        { label: "Dominant share", value: "--", note: "active gross" },
        { label: "Policy floor", value: "1.50", note: "effective count" }
      ],
      effective_ratio_pct: 0,
      stages: [
        { key: "SOURCE", label: "Source", state: "UNKNOWN", detail: "UNKNOWN", tone: "source" },
        { key: "GAP", label: "Gap", state: "UNKNOWN", detail: "UNKNOWN", tone: "gap" },
        { key: "MATURITY", label: "Maturity", state: "UNKNOWN", detail: "UNKNOWN", tone: "maturity" },
        { key: "PERMISSION", label: "Permission", state: "UNAUTHORIZED", detail: "NO_PERMISSION_CAN_BE_INFERRED", tone: "locked" }
      ],
      blockers: [],
      projection_hash_short: "unknown",
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable."
    };
  }

  function formatCount(value) {
    return value === null ? "N/A" : Number(value).toFixed(2);
  }

  function buildPortfolioRiskWeightedDiversificationViewModelV4(projection) {
    if (!validProjection(projection)) return unknownModel();
    const local = projection.local_decision;
    const weighted = projection.weighted_diversification;
    let summary = "An upstream local research gate remains blocked.";
    if (weighted.assessment === "CONCENTRATED") {
      summary = `${weighted.unweighted_effective_cluster_count} cluster labels compress to ${weighted.weighted_effective_cluster_count.toFixed(2)} effective clusters under gross weighting.`;
    } else if (weighted.assessment === "SUFFICIENT") {
      summary = "Verified gross weights satisfy the local effective-cluster policy.";
    } else if (weighted.assessment === "NOT_APPLICABLE") {
      summary = "The weight-aware gate is not applied on the verified risk-reduction path.";
    }
    const labels = { SOURCE: "Source", GAP: "Gap", MATURITY: "Maturity", PERMISSION: "Permission" };
    const ratio = weighted.weighted_effective_cluster_count === null
      ? 0 : Math.min(100, weighted.weighted_effective_cluster_count / weighted.minimum_weighted_effective_cluster_count * 100);
    return {
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN",
      tone: weighted.assessment.toLowerCase().replace("_", "-"),
      kicker: "PORTFOLIO RISK / WEIGHT-AWARE SHADOW",
      title: "Diversification is a weight, not a label",
      summary,
      metrics: [
        { label: "Cluster labels", value: weighted.unweighted_effective_cluster_count === null ? "N/A" : String(weighted.unweighted_effective_cluster_count), note: "unweighted" },
        { label: "Effective clusters", value: formatCount(weighted.weighted_effective_cluster_count), note: "gross weighted" },
        { label: "Dominant share", value: weighted.dominant_cluster_share_of_active_gross_pct === null ? "N/A" : `${weighted.dominant_cluster_share_of_active_gross_pct.toFixed(2)}%`, note: "active gross" },
        { label: "Policy floor", value: weighted.minimum_weighted_effective_cluster_count.toFixed(2), note: weighted.gate_applied ? "gate applied" : "gate not applied" }
      ],
      effective_ratio_pct: Number(ratio.toFixed(2)),
      stages: projection.stages.map((stage) => ({
        key: stage.key,
        label: labels[stage.key],
        state: stage.state,
        detail: stage.detail,
        tone: stage.key === "PERMISSION" ? "locked"
          : stage.key === "GAP" ? (stage.state === "DECLARED" ? "gap" : "clear")
            : stage.key.toLowerCase()
      })),
      blockers: local.blockers.slice(),
      projection_hash_short: projection.projection_hash.slice(0, 12),
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable."
    };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
    })[character]);
  }

  function renderPortfolioRiskWeightedDiversificationCardV4(projection) {
    const model = buildPortfolioRiskWeightedDiversificationViewModelV4(projection);
    const metrics = model.metrics.map((metric) => `
      <article class="prwd-v4__metric">
        <p>${escapeHtml(metric.label)}</p><strong>${escapeHtml(metric.value)}</strong><span>${escapeHtml(metric.note)}</span>
      </article>`).join("");
    const stages = model.stages.map((stage, index) => `
      <article class="prwd-v4__stage prwd-v4__stage--${escapeHtml(stage.tone)}" style="--stage-index:${index}" data-stage="${escapeHtml(stage.key)}">
        <span>0${index + 1}</span><p>${escapeHtml(stage.label)}</p><strong>${escapeHtml(stage.state)}</strong><code>${escapeHtml(stage.detail)}</code>
      </article>`).join("");
    const blockers = model.blockers.length
      ? `<div class="prwd-v4__blockers" aria-label="Local blockers">${model.blockers.map((blocker) => `<code>${escapeHtml(blocker)}</code>`).join("")}</div>`
      : "";
    return `<section class="prwd-v4 prwd-v4--${escapeHtml(model.tone)}" data-contract-state="${escapeHtml(model.contract_state)}" aria-label="Weighted portfolio diversification evidence">
      <header class="prwd-v4__header"><div><p class="prwd-v4__kicker">${escapeHtml(model.kicker)}</p><h2>${escapeHtml(model.title)}</h2></div><span class="prwd-v4__hash">PROJECTION ${escapeHtml(model.projection_hash_short)}</span></header>
      <div class="prwd-v4__lead"><p>${escapeHtml(model.summary)}</p><div class="prwd-v4__dial" style="--effective-ratio:${escapeHtml(model.effective_ratio_pct)}%"><span>WEIGHTED<br>GEOMETRY</span></div></div>
      <div class="prwd-v4__metrics">${metrics}</div>${blockers}
      <div class="prwd-v4__rail" aria-label="Source gap maturity permission sequence">${stages}</div>
      <footer class="prwd-v4__footer"><span>UNMOUNTED SHADOW VIEW</span><p>${escapeHtml(model.permission_note)}</p></footer>
    </section>`;
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT,
    PROJECTION_SCHEMA_VERSION,
    PROJECTION_STATIC_FINGERPRINT,
    STAGE_ORDER,
    buildPortfolioRiskWeightedDiversificationViewModelV4,
    renderPortfolioRiskWeightedDiversificationCardV4,
    verifyPortfolioRiskProjectionSealV4
  });
});
