(function attachClusterExposureReadonlyProjectionV1(root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
    return;
  }
  if (root && typeof root === "object") {
    Object.defineProperty(root, "HakimiClusterExposureReadonlyProjectionV1", {
      configurable: false,
      enumerable: false,
      value: api,
      writable: false,
    });
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const ENVELOPE_SCHEMA_VERSION =
    "cluster-exposure-readonly-projection-verification-handoff-v1";
  const VERIFICATION_STATUS = "EXACTLY_VERIFIED_READONLY_PROJECTION_V1";
  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-history-covered-budget-universe-cluster-exposure-readonly-projection-v1";
  const PROJECTION_STATIC_FINGERPRINT =
    "20260824-cluster-exposure-readonly-projection-v1-verified-batch-hash-only-unmounted-permission-lock-1";
  const PROJECTION_CONSUMER_STATUS =
    "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CANDIDATE";
  const ADAPTER_CONTRACT_VERSION =
    "strategy-correlation-history-covered-budget-universe-cluster-exposure-source-receipt-adapter-v1";

  const STATUS_UNKNOWN = "UNKNOWN";
  const STATUS_LIMIT_BREACH =
    "BLOCKED_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT";
  const STATUS_WITHIN_LIMIT =
    "OBSERVED_WITHIN_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT";
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
  const LIMIT_BLOCKER_ORDER = Object.freeze([
    "PROPOSAL_COUNT_LIMIT_EXCEEDED",
    "SINGLE_PROPOSAL_GROSS_LIMIT_EXCEEDED",
    "CLUSTER_GROSS_LIMIT_EXCEEDED",
    "PORTFOLIO_GROSS_LIMIT_EXCEEDED",
  ]);
  const HASH_PATTERN = /^[0-9a-f]{64}$/;
  const BLOCKER_PATTERN = /^[A-Z0-9_]{1,96}$/;

  const AUTHORITY_LOCK = Object.freeze({
    consumer_registration_allowed: false,
    current_admission_allowed: false,
    current_pointer_written: false,
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
    cluster_ids_redacted: true,
    fresh_projected_evidence_completed: false,
    profitability_claim_allowed: false,
    raw_symbols_redacted: true,
    structural_exposure_metrics_only: true,
    synthetic_only: true,
    within_limit_is_not_admission: true,
  });

  const STATUS_PATHS = Object.freeze({
    [STATUS_UNKNOWN]: Object.freeze({
      gap: "SOURCE_OR_POLICY_CONTRACT_UNKNOWN",
      maturity: "UNVERIFIED",
      tone: "unknown",
      label: "未核验",
      headline: "相关簇暴露合同仍有缺口",
    }),
    [STATUS_LIMIT_BREACH]: Object.freeze({
      gap: "PREREGISTERED_CLUSTER_EXPOSURE_LIMIT_BREACH",
      maturity: "STRUCTURAL_POLICY_BREACH",
      tone: "blocked",
      label: "预登记上限阻断",
      headline: "同簇暴露已触发结构门禁",
    }),
    [STATUS_WITHIN_LIMIT]: Object.freeze({
      gap: "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
      maturity: "PREREGISTERED_STRUCTURE_ONLY",
      tone: "observed",
      label: "结构内观察",
      headline: "当前仅观察到预登记结构内暴露",
    }),
  });

  const BLOCKER_LABELS = Object.freeze({
    PROPOSAL_COUNT_LIMIT_EXCEEDED: "提案数量超过预登记上限",
    SINGLE_PROPOSAL_GROSS_LIMIT_EXCEEDED: "单提案暴露超过预登记上限",
    CLUSTER_GROSS_LIMIT_EXCEEDED: "相关簇合计暴露超过预登记上限",
    PORTFOLIO_GROSS_LIMIT_EXCEEDED: "组合总暴露超过预登记上限",
    POLICY_LIMIT_ORDER_INVALID: "暴露政策层级关系无效",
    FRESH_PROJECTED_EVIDENCE_INCOMPLETE: "新投影证据尚未完成",
    READONLY_PROJECTION_NOT_REGISTERED: "只读投影消费者尚未注册",
    PAPER_LIVE_UNAUTHORIZED: "模拟未授权，实盘永久硬锁",
  });

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function hasExactKeys(value, expectedKeys) {
    if (!isRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = expectedKeys.slice().sort();
    return (
      actual.length === expected.length &&
      actual.every((key, index) => key === expected[index])
    );
  }

  function sameArray(left, right) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => value === right[index])
    );
  }

  function isHash(value) {
    return typeof value === "string" && HASH_PATTERN.test(value);
  }

  function isPlainInteger(value) {
    return Number.isInteger(value) && Number.isSafeInteger(value);
  }

  function exactRecord(value, expected) {
    const keys = Object.keys(expected);
    return (
      hasExactKeys(value, keys) &&
      keys.every((key) => value[key] === expected[key])
    );
  }

  function validPolicyBlockers(status, values) {
    if (
      !Array.isArray(values) ||
      new Set(values).size !== values.length ||
      values.some(
        (value) => typeof value !== "string" || !BLOCKER_PATTERN.test(value),
      )
    ) {
      return false;
    }
    if (status === STATUS_WITHIN_LIMIT) return values.length === 0;
    if (status === STATUS_LIMIT_BREACH) {
      return (
        values.length > 0 &&
        values.every((value) => LIMIT_BLOCKER_ORDER.includes(value)) &&
        sameArray(
          values,
          LIMIT_BLOCKER_ORDER.filter((value) => values.includes(value)),
        )
      );
    }
    return values.length > 0;
  }

  function validSummary(status, summary) {
    if (
      !hasExactKeys(summary, [
        "proposal_count",
        "independent_cluster_count",
        "total_gross_bps",
        "maximum_cluster_gross_bps",
      ])
    ) {
      return false;
    }
    if (status === STATUS_UNKNOWN) {
      return Object.values(summary).every((value) => value === null);
    }
    const proposalCount = summary.proposal_count;
    const clusterCount = summary.independent_cluster_count;
    const totalGross = summary.total_gross_bps;
    const maximumClusterGross = summary.maximum_cluster_gross_bps;
    return (
      isPlainInteger(proposalCount) &&
      proposalCount >= 1 &&
      proposalCount <= 256 &&
      isPlainInteger(clusterCount) &&
      clusterCount >= 1 &&
      clusterCount <= proposalCount &&
      isPlainInteger(totalGross) &&
      totalGross >= 1 &&
      isPlainInteger(maximumClusterGross) &&
      maximumClusterGross >= 1 &&
      maximumClusterGross <= totalGross
    );
  }

  function validSource(status, source) {
    if (
      !hasExactKeys(source, [
        "adapter_contract_version",
        "cluster_exposure_result_hash",
        "policy_fingerprint_sha256",
        "source_batch_fingerprint_sha256",
      ]) ||
      source.adapter_contract_version !== ADAPTER_CONTRACT_VERSION ||
      !isHash(source.cluster_exposure_result_hash) ||
      !isHash(source.source_batch_fingerprint_sha256)
    ) {
      return false;
    }
    if (status === STATUS_UNKNOWN) {
      return (
        source.policy_fingerprint_sha256 === null ||
        isHash(source.policy_fingerprint_sha256)
      );
    }
    return isHash(source.policy_fingerprint_sha256);
  }

  function validDecisionPath(status, decisionPath) {
    const statusPath = STATUS_PATHS[status];
    return (
      statusPath &&
      hasExactKeys(decisionPath, ["source", "gap", "maturity", "permission"]) &&
      decisionPath.source === "ADR0370_EXACT_VERIFIED_BATCH_RECEIPT" &&
      decisionPath.gap === statusPath.gap &&
      decisionPath.maturity === statusPath.maturity &&
      decisionPath.permission === "NOT_AUTHORIZED"
    );
  }

  function validProjection(envelope) {
    if (
      !hasExactKeys(envelope, [
        "schema_version",
        "verification_status",
        "expected_readonly_projection_hash",
        "projection",
      ]) ||
      envelope.schema_version !== ENVELOPE_SCHEMA_VERSION ||
      envelope.verification_status !== VERIFICATION_STATUS ||
      !isHash(envelope.expected_readonly_projection_hash)
    ) {
      return false;
    }
    const projection = envelope.projection;
    if (
      !hasExactKeys(projection, [
        "schema_version",
        "static_fingerprint",
        "consumer_status",
        "registered",
        "status",
        "source",
        "decision_path",
        "summary",
        "policy_blocker_codes",
        "blockers",
        "facts",
        "authority",
        "readonly_projection_hash",
      ]) ||
      projection.schema_version !== PROJECTION_SCHEMA_VERSION ||
      projection.static_fingerprint !== PROJECTION_STATIC_FINGERPRINT ||
      projection.consumer_status !== PROJECTION_CONSUMER_STATUS ||
      projection.registered !== false ||
      !Object.prototype.hasOwnProperty.call(STATUS_PATHS, projection.status) ||
      !isHash(projection.readonly_projection_hash) ||
      projection.readonly_projection_hash !==
        envelope.expected_readonly_projection_hash ||
      !exactRecord(projection.authority, AUTHORITY_LOCK) ||
      !exactRecord(projection.facts, FACTS) ||
      !validSource(projection.status, projection.source) ||
      !validDecisionPath(projection.status, projection.decision_path) ||
      !validSummary(projection.status, projection.summary) ||
      !validPolicyBlockers(
        projection.status,
        projection.policy_blocker_codes,
      ) ||
      !sameArray(projection.blockers, [
        ...projection.policy_blocker_codes,
        ...STATIC_BLOCKERS,
      ])
    ) {
      return false;
    }
    return true;
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.values(value).forEach(deepFreeze);
    }
    return value;
  }

  function formatBps(value) {
    if (!isPlainInteger(value)) return "--";
    return `${(value / 100).toFixed(2)}%`;
  }

  function shortHash(value) {
    return isHash(value) ? `${value.slice(0, 8)}...${value.slice(-8)}` : "--";
  }

  function blockerLabel(code) {
    return BLOCKER_LABELS[code] || `合同阻断：${code}`;
  }

  function unknownModel() {
    return deepFreeze({
      componentVersion: "cluster-exposure-static-presenter-v1",
      verificationAccepted: false,
      rawStatus: STATUS_UNKNOWN,
      tone: "unknown",
      statusLabel: "未核验",
      headline: "相关簇暴露验证交接未闭合",
      eyebrow: "静态只读投影 · 非实时结果",
      stages: [
        { key: "SOURCE", value: "ADR0371 exact verification：未确认" },
        { key: "GAP", value: "输入、哈希或权限锁合同不完整" },
        { key: "MATURITY", value: "UNVERIFIED" },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      metrics: [
        { label: "提案", value: "--" },
        { label: "独立簇", value: "--" },
        { label: "总暴露", value: "--" },
        { label: "最大簇", value: "--" },
      ],
      policyBlockers: [
        {
          code: "PRESENTATION_INPUT_NOT_EXACTLY_VERIFIED",
          label: "展示输入未完成精确验证交接",
        },
      ],
      boundaryBlockers: STATIC_BLOCKERS.map((code) => ({
        code,
        label: blockerLabel(code),
      })),
      projectionHash: "--",
      sourceHash: "--",
      caution: "不构成准入、仓位、信号、订单或收益结论",
    });
  }

  function deriveClusterExposureViewModelV1(envelope) {
    if (!validProjection(envelope)) return unknownModel();
    const projection = envelope.projection;
    const statusPath = STATUS_PATHS[projection.status];
    const summary = projection.summary;
    return deepFreeze({
      componentVersion: "cluster-exposure-static-presenter-v1",
      verificationAccepted: true,
      rawStatus: projection.status,
      tone: statusPath.tone,
      statusLabel: statusPath.label,
      headline: statusPath.headline,
      eyebrow: "静态只读投影 · 非实时结果",
      stages: [
        {
          key: "SOURCE",
          value: `ADR0371 投影 ${shortHash(projection.readonly_projection_hash)}`,
        },
        { key: "GAP", value: projection.decision_path.gap },
        { key: "MATURITY", value: projection.decision_path.maturity },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      metrics: [
        {
          label: "提案",
          value:
            summary.proposal_count === null ? "--" : String(summary.proposal_count),
        },
        {
          label: "独立簇",
          value:
            summary.independent_cluster_count === null
              ? "--"
              : String(summary.independent_cluster_count),
        },
        { label: "总暴露", value: formatBps(summary.total_gross_bps) },
        {
          label: "最大簇",
          value: formatBps(summary.maximum_cluster_gross_bps),
        },
      ],
      policyBlockers: projection.policy_blocker_codes.map((code) => ({
        code,
        label: blockerLabel(code),
      })),
      boundaryBlockers: STATIC_BLOCKERS.map((code) => ({
        code,
        label: blockerLabel(code),
      })),
      projectionHash: shortHash(projection.readonly_projection_hash),
      sourceHash: shortHash(projection.source.cluster_exposure_result_hash),
      caution: "不构成准入、仓位、信号、订单或收益结论",
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderBlockers(items) {
    return items
      .map(
        (item) =>
          `<li><span>${escapeHtml(item.code)}</span><strong>${escapeHtml(item.label)}</strong></li>`,
      )
      .join("");
  }

  function renderClusterExposureReadonlyProjectionV1(envelope) {
    const model = deriveClusterExposureViewModelV1(envelope);
    const headingId = `clusterExposureHeading-${
      model.projectionHash === "--" ? "unknown" : model.projectionHash.slice(0, 8)
    }`;
    const policyItems =
      model.policyBlockers.length > 0
        ? model.policyBlockers
        : [
            {
              code: "NO_STRUCTURAL_LIMIT_BREACH_OBSERVED",
              label: "未观察到预登记结构上限阻断，但成熟度仍未闭合",
            },
          ];
    return [
      `<article class="cluster-exposure-plate-v1 is-${escapeHtml(model.tone)}" data-evidence-role="cluster-exposure-readonly" data-raw-status="${escapeHtml(model.rawStatus)}" aria-labelledby="${headingId}">`,
      '<header class="cluster-exposure-plate-v1__header">',
      `<div><span>${escapeHtml(model.eyebrow)}</span><h3 id="${headingId}">${escapeHtml(model.headline)}</h3></div>`,
      `<strong>${escapeHtml(model.statusLabel)}</strong>`,
      "</header>",
      '<div class="cluster-exposure-plate-v1__body">',
      '<div class="cluster-exposure-plate-v1__map" aria-hidden="true">',
      '<span class="cluster-exposure-plate-v1__orbit"></span>',
      '<i class="cluster-exposure-plate-v1__node node-a">P1</i>',
      '<i class="cluster-exposure-plate-v1__node node-b">P2</i>',
      '<b class="cluster-exposure-plate-v1__cluster">CLUSTER<br>EXPOSURE</b>',
      '<em class="cluster-exposure-plate-v1__cap">PREREGISTERED CAP</em>',
      "</div>",
      '<dl class="cluster-exposure-plate-v1__metrics">',
      ...model.metrics.map(
        (metric) =>
          `<div><dt>${escapeHtml(metric.label)}</dt><dd>${escapeHtml(metric.value)}</dd></div>`,
      ),
      "</dl>",
      "</div>",
      '<ol class="cluster-exposure-plate-v1__flow">',
      ...model.stages.map(
        (stage) =>
          `<li data-stage="${stage.key.toLowerCase()}"><span>${stage.key}</span><strong>${escapeHtml(stage.value)}</strong></li>`,
      ),
      "</ol>",
      '<details class="cluster-exposure-plate-v1__ledger" open>',
      "<summary>阻断与证据边界</summary>",
      `<ul>${renderBlockers([...policyItems, ...model.boundaryBlockers])}</ul>`,
      "</details>",
      '<footer class="cluster-exposure-plate-v1__footer">',
      `<span>PROJECTION ${escapeHtml(model.projectionHash)}</span>`,
      `<span>SOURCE ${escapeHtml(model.sourceHash)}</span>`,
      `<strong>${escapeHtml(model.caution)}</strong>`,
      "</footer>",
      "</article>",
    ].join("");
  }

  return deepFreeze({
    ENVELOPE_SCHEMA_VERSION,
    PROJECTION_SCHEMA_VERSION,
    STATUS_LIMIT_BREACH,
    STATUS_UNKNOWN,
    STATUS_WITHIN_LIMIT,
    STAGE_ORDER,
    VERIFICATION_STATUS,
    deriveClusterExposureViewModelV1,
    renderClusterExposureReadonlyProjectionV1,
  });
});
