(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiPortfolioRiskFreshnessGateCardV3 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-projection-v3";
  const PROJECTION_STATIC_FINGERPRINT =
    "20260822-portfolio-risk-freshness-public-projection-lock-1";
  const CARD_SCHEMA_VERSION = "portfolio-risk-freshness-gate-card-v3";
  const CARD_STATIC_FINGERPRINT =
    "20260822-portfolio-risk-freshness-gate-card-lock-1";
  const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

  const TOP_KEYS = [
    "authority", "decision", "facts", "local_decision", "projection_hash",
    "schema_version", "source", "stages", "static_fingerprint", "status"
  ];
  const SOURCE_KEYS = [
    "adapter_v3_exactly_verified", "adapter_v3_hash", "adapter_v3_schema_version",
    "freshness_evaluation_hash", "lineage_binding_hash", "lineage_binding_schema_version"
  ];
  const LOCAL_KEYS = [
    "blockers", "decision", "risk_increasing", "session_freshness_required",
    "status", "warnings"
  ];
  const FACT_KEYS = [
    "completed_price_rows_embedded", "correlation_matrices_embedded",
    "positions_embedded", "profitability_proven", "projection_only",
    "return_series_embedded", "runtime_consumer_bound", "source_document_embedded"
  ];
  const AUTHORITY_KEYS = [
    "current_admission_allowed", "current_pointer_written",
    "formal_registry_activation_allowed", "live_order_allowed", "migration_allowed",
    "paper_authorized", "presentation_only", "research_only",
    "runtime_gate_activation_allowed", "shadow_consumer_activation_allowed", "writer_allowed"
  ];
  const STAGE_KEYS = ["detail", "key", "state"];
  const DECISIONS = new Set([
    "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY",
    "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED",
    "BLOCKED_SESSION_FRESHNESS",
    "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET",
    "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY",
    "BLOCKED_ADAPTER_FRESHNESS_LINEAGE",
    "BLOCKED_ADAPTER_V2_COMPONENT"
  ]);

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

  function stagesAreConsistent(stages, local) {
    if (!Array.isArray(stages) || stages.length !== STAGE_ORDER.length) return false;
    if (!stages.every((stage) => hasExactKeys(stage, STAGE_KEYS))) return false;
    if (!stages.every((stage, index) => stage.key === STAGE_ORDER[index])) return false;
    if (stages[0].state !== "VERIFIED" || stages[0].detail !== "ADAPTER_V3_EXACT_REBUILD") return false;
    if (!["NONE_OBSERVED", "DECLARED"].includes(stages[1].state)) return false;
    if (!["LOCAL_POLICY_SATISFIED", "LOCAL_POLICY_BLOCKED"].includes(stages[2].state)) return false;
    if (stages[3].state !== "UNAUTHORIZED"
      || stages[3].detail !== "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY") return false;
    if (local.status === "PASS" && stages[2].state !== "LOCAL_POLICY_SATISFIED") return false;
    if (local.status === "BLOCK" && stages[2].state !== "LOCAL_POLICY_BLOCKED") return false;
    return stages[2].detail === local.decision;
  }

  function validProjection(value) {
    if (!hasExactKeys(value, TOP_KEYS)) return false;
    if (value.schema_version !== PROJECTION_SCHEMA_VERSION
      || value.static_fingerprint !== PROJECTION_STATIC_FINGERPRINT
      || value.status !== "PASS"
      || value.decision !== "EXACT_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED"
      || !isHash(value.projection_hash)) return false;
    if (!hasExactKeys(value.source, SOURCE_KEYS)
      || value.source.adapter_v3_exactly_verified !== true
      || !isHash(value.source.adapter_v3_hash)
      || !isHash(value.source.lineage_binding_hash)
      || !isHash(value.source.freshness_evaluation_hash)) return false;
    if (!hasExactKeys(value.local_decision, LOCAL_KEYS)) return false;
    const local = value.local_decision;
    if (!["PASS", "BLOCK"].includes(local.status)
      || !DECISIONS.has(local.decision)
      || typeof local.risk_increasing !== "boolean"
      || local.session_freshness_required !== local.risk_increasing
      || !isStringArray(local.blockers)
      || !isStringArray(local.warnings)) return false;
    return stagesAreConsistent(value.stages, local)
      && factsAreMinimal(value.facts)
      && authorityLocked(value.authority);
  }

  function unknownModel() {
    return {
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "UNKNOWN",
      kicker: "PORTFOLIO RISK / LOCAL RESEARCH",
      title: "Session freshness gate",
      summary: "Projection contract is unknown. No permission can be inferred.",
      stages: [
        { key: "SOURCE", label: "Source", state: "UNKNOWN", detail: "UNKNOWN", tone: "source" },
        { key: "GAP", label: "Gap", state: "UNKNOWN", detail: "UNKNOWN", tone: "gap" },
        { key: "MATURITY", label: "Maturity", state: "UNKNOWN", detail: "UNKNOWN", tone: "maturity" },
        { key: "PERMISSION", label: "Permission", state: "UNAUTHORIZED", detail: "NO_PERMISSION_CAN_BE_INFERRED", tone: "locked" }
      ],
      projection_hash_short: "unknown",
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable."
    };
  }

  function buildPortfolioRiskFreshnessGateViewModelV3(projection) {
    if (!validProjection(projection)) return unknownModel();
    const local = projection.local_decision;
    let summary = "A declared evidence gap blocks this local research policy.";
    if (local.decision === "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY") {
      summary = "Budget, temporal stability, and session freshness align for this local research decision.";
    } else if (local.decision === "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED") {
      summary = "The risk-reduction exception is explicit; stale freshness remains visible as a warning.";
    }
    const labels = { SOURCE: "Source", GAP: "Gap", MATURITY: "Maturity", PERMISSION: "Permission" };
    return {
      schema_version: CARD_SCHEMA_VERSION,
      static_fingerprint: CARD_STATIC_FINGERPRINT,
      contract_state: "KNOWN",
      kicker: "PORTFOLIO RISK / LOCAL RESEARCH",
      title: "Session freshness gate",
      summary,
      stages: projection.stages.map((stage) => ({
        key: stage.key,
        label: labels[stage.key],
        state: stage.state,
        detail: stage.detail,
        tone: stage.key === "PERMISSION" ? "locked"
          : stage.key === "GAP" ? (stage.state === "DECLARED" ? "gap" : "clear")
            : stage.key.toLowerCase()
      })),
      projection_hash_short: projection.projection_hash.slice(0, 12),
      permission_note: "Research display only. Runtime, paper, and live authority remain unavailable."
    };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
    })[char]);
  }

  function renderPortfolioRiskFreshnessGateCardV3(projection) {
    const model = buildPortfolioRiskFreshnessGateViewModelV3(projection);
    const stages = model.stages.map((stage, index) => `
      <article class="prfg-v3__stage prfg-v3__stage--${escapeHtml(stage.tone)}" style="--stage-index:${index}" data-stage="${escapeHtml(stage.key)}">
        <span class="prfg-v3__index">0${index + 1}</span>
        <p class="prfg-v3__label">${escapeHtml(stage.label)}</p>
        <strong class="prfg-v3__state">${escapeHtml(stage.state)}</strong>
        <code class="prfg-v3__detail">${escapeHtml(stage.detail)}</code>
      </article>`).join("");
    return `<section class="prfg-v3" data-contract-state="${escapeHtml(model.contract_state)}" aria-label="Portfolio risk session freshness evidence">
      <header class="prfg-v3__header">
        <div><p class="prfg-v3__kicker">${escapeHtml(model.kicker)}</p><h2>${escapeHtml(model.title)}</h2></div>
        <span class="prfg-v3__hash">PROJECTION ${escapeHtml(model.projection_hash_short)}</span>
      </header>
      <p class="prfg-v3__summary">${escapeHtml(model.summary)}</p>
      <div class="prfg-v3__rail" aria-label="Source gap maturity permission sequence">${stages}</div>
      <footer class="prfg-v3__footer"><span>LOCAL EVIDENCE VIEW</span><p>${escapeHtml(model.permission_note)}</p></footer>
    </section>`;
  }

  return Object.freeze({
    CARD_SCHEMA_VERSION,
    CARD_STATIC_FINGERPRINT,
    PROJECTION_SCHEMA_VERSION,
    PROJECTION_STATIC_FINGERPRINT,
    STAGE_ORDER,
    buildPortfolioRiskFreshnessGateViewModelV3,
    renderPortfolioRiskFreshnessGateCardV3
  });
});
