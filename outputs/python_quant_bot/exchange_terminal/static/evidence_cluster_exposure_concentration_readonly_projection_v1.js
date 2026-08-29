(function attachClusterConcentrationPresenterV1(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
    return;
  }
  if (root && typeof root === "object") {
    Object.defineProperty(root, "HakimiClusterConcentrationPresenterV1", {
      configurable: false,
      enumerable: false,
      value: api,
      writable: false,
    });
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const ENVELOPE_SCHEMA_VERSION =
    "cluster-exposure-concentration-readonly-projection-verification-handoff-v1";
  const VERIFICATION_STATUS =
    "EXACTLY_VERIFIED_CONCENTRATION_READONLY_PROJECTION_V1";
  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-history-covered-budget-universe-cluster-exposure-concentration-readonly-projection-v1";
  const STATIC_FINGERPRINT =
    "20260824-cluster-exposure-concentration-readonly-projection-v1-verified-batch-hash-only-unmounted-permission-lock-1";
  const CONSUMER_STATUS =
    "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CONCENTRATION_CANDIDATE";
  const GATE_CONTRACT_VERSION =
    "strategy-correlation-history-covered-budget-universe-cluster-exposure-concentration-gate-v1";

  const STATUS_UNKNOWN = "UNKNOWN";
  const STATUS_UPSTREAM_BLOCK = "BLOCKED_UPSTREAM_EXPOSURE_LIMIT";
  const STATUS_CONCENTRATION_BLOCK =
    "BLOCKED_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT";
  const STATUS_WITHIN_LIMIT =
    "OBSERVED_WITHIN_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT";
  const STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  const STATIC_BLOCKERS = Object.freeze([
    "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
    "READONLY_PROJECTION_NOT_REGISTERED",
    "PAPER_LIVE_UNAUTHORIZED",
  ]);
  const CONCENTRATION_BLOCKER_ORDER = Object.freeze([
    "INDEPENDENT_CLUSTER_COUNT_BELOW_MINIMUM",
    "LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED",
    "CLUSTER_HHI_LIMIT_EXCEEDED",
  ]);
  const HASH_PATTERN = /^[0-9a-f]{64}$/;
  const BLOCKER_PATTERN = /^[A-Z0-9_]{1,96}$/;

  const STATUS_PATHS = Object.freeze({
    [STATUS_UNKNOWN]: Object.freeze({
      gap: "SOURCE_OR_CONCENTRATION_POLICY_UNKNOWN",
      maturity: "UNVERIFIED",
      tone: "unknown",
      label: "未核验",
      headline: "相关簇集中度合同仍有缺口",
    }),
    [STATUS_UPSTREAM_BLOCK]: Object.freeze({
      gap: "UPSTREAM_ABSOLUTE_EXPOSURE_LIMIT_BREACH",
      maturity: "STRUCTURAL_UPSTREAM_BLOCK",
      tone: "blocked",
      label: "上游暴露阻断",
      headline: "绝对暴露门禁已先行阻断",
    }),
    [STATUS_CONCENTRATION_BLOCK]: Object.freeze({
      gap: "PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT_BREACH",
      maturity: "STRUCTURAL_CONCENTRATION_POLICY_BREACH",
      tone: "blocked",
      label: "集中度门禁阻断",
      headline: "簇间分布触发预登记集中度门禁",
    }),
    [STATUS_WITHIN_LIMIT]: Object.freeze({
      gap: "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
      maturity: "PREREGISTERED_CONCENTRATION_STRUCTURE_ONLY",
      tone: "observed",
      label: "结构分布观察",
      headline: "当前仅观察到预登记结构内分布",
    }),
  });

  const AUTHORITY = Object.freeze({
    consumer_registration_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
    diversification_claim_allowed: false,
    http_registration_allowed: false,
    live_order_allowed: false,
    paper_authorized: false,
    profitability_claim_allowed: false,
    readonly_projection_activation_allowed: false,
    runtime_activation_allowed: false,
    writer_allowed: false,
    research_evidence_only: true,
  });
  const FACTS = Object.freeze({
    concentration_metrics_structural_only: true,
    diversification_quality_claim_allowed: false,
    fresh_projected_evidence_completed: false,
    profitability_claim_allowed: false,
    raw_cluster_ids_redacted: true,
    raw_symbols_redacted: true,
    synthetic_only: true,
    within_limit_is_not_admission: true,
  });
  const BLOCKER_LABELS = Object.freeze({
    INDEPENDENT_CLUSTER_COUNT_BELOW_MINIMUM: "独立簇数量低于预登记下限",
    LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED: "最大簇占比超过预登记上限",
    CLUSTER_HHI_LIMIT_EXCEEDED: "簇暴露 HHI 超过预登记上限",
    UPSTREAM_EXPOSURE_LIMIT_BREACH: "上游绝对暴露门禁已阻断",
    MAX_CLUSTER_HHI_INVALID: "集中度政策 HHI 上限无效",
    FRESH_PROJECTED_EVIDENCE_INCOMPLETE: "新投影证据尚未完成",
    READONLY_PROJECTION_NOT_REGISTERED: "只读投影消费者尚未注册",
    PAPER_LIVE_UNAUTHORIZED: "模拟未授权，实盘永久硬锁",
  });

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function exactKeys(value, keys) {
    if (!isRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = keys.slice().sort();
    return actual.length === expected.length && actual.every((v, i) => v === expected[i]);
  }

  function exactRecord(value, expected) {
    const keys = Object.keys(expected);
    return exactKeys(value, keys) && keys.every((key) => value[key] === expected[key]);
  }

  function sameArray(left, right) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length && left.every((value, index) => value === right[index]);
  }

  function isHash(value) {
    return typeof value === "string" && HASH_PATTERN.test(value);
  }

  function isInteger(value) {
    return Number.isSafeInteger(value);
  }

  function metricsAreNull(summary) {
    return Object.values(summary).every((value) => value === null);
  }

  function validSummary(status, summary) {
    if (!exactKeys(summary, [
      "proposal_count",
      "independent_cluster_count",
      "total_gross_bps",
      "largest_cluster_share_bps_ceiling",
      "hhi_ppm_ceiling",
      "effective_cluster_count_milli_floor",
    ])) return false;
    if (status === STATUS_UNKNOWN || status === STATUS_UPSTREAM_BLOCK) {
      return metricsAreNull(summary);
    }
    return (
      isInteger(summary.proposal_count) && summary.proposal_count >= 1 &&
      isInteger(summary.independent_cluster_count) && summary.independent_cluster_count >= 1 && summary.independent_cluster_count <= summary.proposal_count &&
      isInteger(summary.total_gross_bps) && summary.total_gross_bps >= 1 &&
      isInteger(summary.largest_cluster_share_bps_ceiling) && summary.largest_cluster_share_bps_ceiling >= 1 && summary.largest_cluster_share_bps_ceiling <= 10000 &&
      isInteger(summary.hhi_ppm_ceiling) && summary.hhi_ppm_ceiling >= 1 && summary.hhi_ppm_ceiling <= 1000000 &&
      isInteger(summary.effective_cluster_count_milli_floor) && summary.effective_cluster_count_milli_floor >= 1000 && summary.effective_cluster_count_milli_floor <= summary.independent_cluster_count * 1000
    );
  }

  function validPolicyBlockers(status, blockers) {
    if (!Array.isArray(blockers) || new Set(blockers).size !== blockers.length || blockers.some((code) => typeof code !== "string" || !BLOCKER_PATTERN.test(code))) return false;
    if (status === STATUS_WITHIN_LIMIT) return blockers.length === 0;
    if (status === STATUS_UPSTREAM_BLOCK) return sameArray(blockers, ["UPSTREAM_EXPOSURE_LIMIT_BREACH"]);
    if (status === STATUS_CONCENTRATION_BLOCK) {
      return blockers.length > 0 && blockers.every((code) => CONCENTRATION_BLOCKER_ORDER.includes(code)) && sameArray(blockers, CONCENTRATION_BLOCKER_ORDER.filter((code) => blockers.includes(code)));
    }
    return blockers.length > 0;
  }

  function validSource(status, source) {
    if (!exactKeys(source, [
      "concentration_gate_contract_version",
      "concentration_result_hash",
      "concentration_policy_fingerprint_sha256",
      "source_exposure_result_hash",
    ])) return false;
    if (source.concentration_gate_contract_version !== GATE_CONTRACT_VERSION || !isHash(source.concentration_result_hash) || !isHash(source.source_exposure_result_hash)) return false;
    return status === STATUS_UNKNOWN
      ? source.concentration_policy_fingerprint_sha256 === null || isHash(source.concentration_policy_fingerprint_sha256)
      : isHash(source.concentration_policy_fingerprint_sha256);
  }

  function validProjection(envelope) {
    if (!exactKeys(envelope, ["schema_version", "verification_status", "expected_readonly_projection_hash", "projection"]) || envelope.schema_version !== ENVELOPE_SCHEMA_VERSION || envelope.verification_status !== VERIFICATION_STATUS || !isHash(envelope.expected_readonly_projection_hash)) return false;
    const projection = envelope.projection;
    if (!exactKeys(projection, ["schema_version", "static_fingerprint", "consumer_status", "registered", "status", "source", "decision_path", "summary", "policy_blocker_codes", "blockers", "facts", "authority", "readonly_projection_hash"])) return false;
    const statusPath = STATUS_PATHS[projection.status];
    return Boolean(statusPath) &&
      projection.schema_version === PROJECTION_SCHEMA_VERSION &&
      projection.static_fingerprint === STATIC_FINGERPRINT &&
      projection.consumer_status === CONSUMER_STATUS &&
      projection.registered === false &&
      isHash(projection.readonly_projection_hash) &&
      projection.readonly_projection_hash === envelope.expected_readonly_projection_hash &&
      exactRecord(projection.authority, AUTHORITY) &&
      exactRecord(projection.facts, FACTS) &&
      validSource(projection.status, projection.source) &&
      exactKeys(projection.decision_path, ["source", "gap", "maturity", "permission"]) &&
      projection.decision_path.source === "ADR0374_EXACT_VERIFIED_BATCH_CONCENTRATION" &&
      projection.decision_path.gap === statusPath.gap &&
      projection.decision_path.maturity === statusPath.maturity &&
      projection.decision_path.permission === "NOT_AUTHORIZED" &&
      validSummary(projection.status, projection.summary) &&
      validPolicyBlockers(projection.status, projection.policy_blocker_codes) &&
      sameArray(projection.blockers, [...projection.policy_blocker_codes, ...STATIC_BLOCKERS]);
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.values(value).forEach(deepFreeze);
    }
    return value;
  }

  function formatPercentBps(value) {
    return isInteger(value) ? `${(value / 100).toFixed(2)}%` : "--";
  }

  function formatHhi(value) {
    return isInteger(value) ? (value / 1000000).toFixed(6) : "--";
  }

  function formatMilli(value) {
    return isInteger(value) ? (value / 1000).toFixed(3) : "--";
  }

  function shortHash(value) {
    return isHash(value) ? `${value.slice(0, 8)}...${value.slice(-8)}` : "--";
  }

  function blockerLabel(code) {
    return BLOCKER_LABELS[code] || `合同阻断：${code}`;
  }

  function unknownModel() {
    return deepFreeze({
      verificationAccepted: false,
      rawStatus: STATUS_UNKNOWN,
      tone: "unknown",
      statusLabel: "未核验",
      headline: "相关簇集中度验证交接未闭合",
      eyebrow: "静态集中度投影 · 非实时结果",
      stages: [
        { key: "SOURCE", value: "ADR0375 exact verification：未确认" },
        { key: "GAP", value: "输入、哈希或权限锁合同不完整" },
        { key: "MATURITY", value: "UNVERIFIED" },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      metrics: [
        { label: "提案", value: "--" },
        { label: "独立簇", value: "--" },
        { label: "总暴露", value: "--" },
        { label: "最大簇占比", value: "--" },
        { label: "HHI", value: "--" },
        { label: "有效簇", value: "--" },
      ],
      policyBlockers: [{ code: "PRESENTATION_INPUT_NOT_EXACTLY_VERIFIED", label: "展示输入未完成精确验证交接" }],
      boundaryBlockers: STATIC_BLOCKERS.map((code) => ({ code, label: blockerLabel(code) })),
      projectionHash: "--",
      caution: "不构成分散化、准入、仓位、信号、订单或收益结论",
    });
  }

  function deriveClusterConcentrationViewModelV1(envelope) {
    if (!validProjection(envelope)) return unknownModel();
    const projection = envelope.projection;
    const path = STATUS_PATHS[projection.status];
    const summary = projection.summary;
    return deepFreeze({
      verificationAccepted: true,
      rawStatus: projection.status,
      tone: path.tone,
      statusLabel: path.label,
      headline: path.headline,
      eyebrow: "静态集中度投影 · 非实时结果",
      stages: [
        { key: "SOURCE", value: `ADR0375 投影 ${shortHash(projection.readonly_projection_hash)}` },
        { key: "GAP", value: projection.decision_path.gap },
        { key: "MATURITY", value: projection.decision_path.maturity },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      metrics: [
        { label: "提案", value: summary.proposal_count === null ? "--" : String(summary.proposal_count) },
        { label: "独立簇", value: summary.independent_cluster_count === null ? "--" : String(summary.independent_cluster_count) },
        { label: "总暴露", value: formatPercentBps(summary.total_gross_bps) },
        { label: "最大簇占比", value: formatPercentBps(summary.largest_cluster_share_bps_ceiling) },
        { label: "HHI", value: formatHhi(summary.hhi_ppm_ceiling) },
        { label: "有效簇", value: formatMilli(summary.effective_cluster_count_milli_floor) },
      ],
      policyBlockers: projection.policy_blocker_codes.map((code) => ({ code, label: blockerLabel(code) })),
      boundaryBlockers: STATIC_BLOCKERS.map((code) => ({ code, label: blockerLabel(code) })),
      projectionHash: shortHash(projection.readonly_projection_hash),
      caution: "不构成分散化、准入、仓位、信号、订单或收益结论",
    });
  }

  function escapeHtml(value) {
    return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  }

  function renderItems(items) {
    return items.map((item) => `<li><span>${escapeHtml(item.code)}</span><strong>${escapeHtml(item.label)}</strong></li>`).join("");
  }

  function renderClusterConcentrationReadonlyProjectionV1(envelope) {
    const model = deriveClusterConcentrationViewModelV1(envelope);
    const headingId = `clusterConcentrationHeading-${model.projectionHash === "--" ? "unknown" : model.projectionHash.slice(0, 8)}`;
    const policyItems = model.policyBlockers.length ? model.policyBlockers : [{ code: "NO_CONCENTRATION_LIMIT_BREACH_OBSERVED", label: "未观察到预登记集中度阻断，但成熟度仍未闭合" }];
    return [
      `<article class="cluster-concentration-plate-v1 is-${escapeHtml(model.tone)}" data-evidence-role="cluster-concentration-readonly" data-raw-status="${escapeHtml(model.rawStatus)}" aria-labelledby="${headingId}">`,
      '<header class="cluster-concentration-plate-v1__header">',
      `<div><span>${escapeHtml(model.eyebrow)}</span><h3 id="${headingId}">${escapeHtml(model.headline)}</h3></div><strong>${escapeHtml(model.statusLabel)}</strong>`,
      "</header>",
      '<div class="cluster-concentration-plate-v1__body">',
      '<div class="cluster-concentration-plate-v1__instrument" aria-hidden="true"><span class="dominance-track"><i></i></span><b>MAX CLUSTER SHARE</b><div class="hhi-dial"><strong>HHI</strong><em>EFFECTIVE<br>CLUSTERS</em></div></div>',
      '<dl class="cluster-concentration-plate-v1__metrics">',
      ...model.metrics.map((item) => `<div><dt>${escapeHtml(item.label)}</dt><dd>${escapeHtml(item.value)}</dd></div>`),
      "</dl></div>",
      '<ol class="cluster-concentration-plate-v1__flow">',
      ...model.stages.map((stage) => `<li data-stage="${stage.key.toLowerCase()}"><span>${stage.key}</span><strong>${escapeHtml(stage.value)}</strong></li>`),
      "</ol>",
      '<details class="cluster-concentration-plate-v1__ledger" open><summary>集中度阻断与证据边界</summary>',
      `<ul>${renderItems([...policyItems, ...model.boundaryBlockers])}</ul></details>`,
      `<footer><span>PROJECTION ${escapeHtml(model.projectionHash)}</span><strong>${escapeHtml(model.caution)}</strong></footer>`,
      "</article>",
    ].join("");
  }

  return deepFreeze({
    ENVELOPE_SCHEMA_VERSION,
    VERIFICATION_STATUS,
    PROJECTION_SCHEMA_VERSION,
    STATUS_UNKNOWN,
    STATUS_UPSTREAM_BLOCK,
    STATUS_CONCENTRATION_BLOCK,
    STATUS_WITHIN_LIMIT,
    STAGE_ORDER,
    deriveClusterConcentrationViewModelV1,
    renderClusterConcentrationReadonlyProjectionV1,
  });
});
