(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.HakimiPortfolioRiskSessionFreshnessCardV1 = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-session-freshness-public-projection-v1";
  const STATIC_FINGERPRINT =
    "20260822-session-lag-ledger-projection-lock-1";
  const STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  const GAP_STATES = new Set([
    "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
    "SESSION_LAG_POLICY_GAP_PRESENT",
    "UNVERIFIED_FRESHNESS_EVIDENCE_GAP",
    "UNKNOWN",
    "NOT_SUPPLIED",
  ]);
  const AUTHORITY_KEYS = [
    "current_admission_allowed",
    "current_pointer_written",
    "descriptive_only",
    "formal_registry_activation_allowed",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "shadow_consumer_activation_allowed",
    "writer_allowed",
  ];

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function isNullableString(value) {
    return value === null || typeof value === "string";
  }

  function isNullableInteger(value) {
    return value === null || (Number.isInteger(value) && value >= 0);
  }

  function isNullableBoolean(value) {
    return value === null || typeof value === "boolean";
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function hasExactKeys(value, expected) {
    if (!isObject(value)) return false;
    const actual = Object.keys(value).sort();
    const wanted = expected.slice().sort();
    return actual.length === wanted.length && actual.every((key, i) => key === wanted[i]);
  }

  function authorityIsLocked(authority) {
    if (!hasExactKeys(authority, AUTHORITY_KEYS)) return false;
    return AUTHORITY_KEYS.every(function (key) {
      return key === "descriptive_only"
        ? authority[key] === true
        : authority[key] === false;
    });
  }

  function pipelineIsValid(pipeline, status) {
    if (!Array.isArray(pipeline) || pipeline.length !== STAGE_ORDER.length) {
      return false;
    }
    if (
      !pipeline.every(function (item, index) {
        return (
          isObject(item) &&
          hasExactKeys(item, ["stage", "state"]) &&
          item.stage === STAGE_ORDER[index] &&
          typeof item.state === "string"
        );
      })
    ) {
      return false;
    }
    if (
      pipeline[2].state !== "UNMOUNTED_CANDIDATE" ||
      pipeline[3].state !== "UNAUTHORIZED" ||
      !GAP_STATES.has(pipeline[1].state)
    ) {
      return false;
    }
    if (status === "OBSERVED") {
      return pipeline[0].state === "VERIFIED" && !["UNKNOWN", "NOT_SUPPLIED"].includes(pipeline[1].state);
    }
    if (status === "UNKNOWN") {
      return pipeline[0].state === "UNKNOWN" && pipeline[1].state === "UNKNOWN";
    }
    if (status === "NOT_SUPPLIED") {
      return pipeline[0].state === "NOT_SUPPLIED" && pipeline[1].state === "NOT_SUPPLIED";
    }
    return false;
  }

  function summaryIsValid(summary, status) {
    const keys = [
      "evaluation_decision",
      "evaluation_status",
      "cutoff_session_label",
      "reference_time_utc",
      "max_completed_session_lag",
      "preregistered_max_completed_session_lag",
      "calendar_count",
      "clock_quality",
      "external_clock_source_count",
      "local_policy_condition_satisfied",
      "external_clock_authority_authenticated",
      "freshness_externally_proven",
      "blocker_count",
    ];
    if (!hasExactKeys(summary, keys) || typeof summary.evaluation_decision !== "string") {
      return false;
    }
    if (
      !isNullableString(summary.evaluation_status) ||
      !isNullableString(summary.cutoff_session_label) ||
      !isNullableString(summary.reference_time_utc) ||
      !isNullableInteger(summary.max_completed_session_lag) ||
      !isNullableInteger(summary.preregistered_max_completed_session_lag) ||
      !isNullableInteger(summary.calendar_count) ||
      !isNullableString(summary.clock_quality) ||
      !isNullableInteger(summary.external_clock_source_count) ||
      !isNullableBoolean(summary.local_policy_condition_satisfied) ||
      !isNullableBoolean(summary.external_clock_authority_authenticated) ||
      !isNullableBoolean(summary.freshness_externally_proven) ||
      !isNullableInteger(summary.blocker_count)
    ) {
      return false;
    }
    if (status !== "OBSERVED") {
      return (
        summary.evaluation_status === null &&
        summary.max_completed_session_lag === null &&
        summary.external_clock_authority_authenticated === null
      );
    }
    return (
      ["PASS", "BLOCK"].includes(summary.evaluation_status) &&
      Number.isInteger(summary.max_completed_session_lag) &&
      Number.isInteger(summary.preregistered_max_completed_session_lag) &&
      Number.isInteger(summary.calendar_count) &&
      Number.isInteger(summary.external_clock_source_count) &&
      typeof summary.local_policy_condition_satisfied === "boolean" &&
      summary.external_clock_authority_authenticated === false &&
      summary.freshness_externally_proven === false
    );
  }

  function factsAreLocked(facts) {
    const expected = [
      "source_documents_embedded",
      "clock_sources_embedded",
      "calendar_ids_embedded",
      "per_calendar_lag_embedded",
      "raw_correlations_embedded",
      "profitability_proof",
      "runtime_assets_accessed",
      "runtime_consumer_mounted",
      "natural_forward_chain_changed",
      "external_time_authority_authenticated",
    ];
    return hasExactKeys(facts, expected) && expected.every(function (key) {
      return facts[key] === false;
    });
  }

  function projectionIsValid(projection) {
    return Boolean(
      isObject(projection) &&
        projection.schema_version === PROJECTION_SCHEMA_VERSION &&
        projection.static_fingerprint === STATIC_FINGERPRINT &&
        ["OBSERVED", "UNKNOWN", "NOT_SUPPLIED"].includes(projection.status) &&
        isSha256(projection.projection_hash) &&
        pipelineIsValid(projection.pipeline, projection.status) &&
        summaryIsValid(projection.summary, projection.status) &&
        factsAreLocked(projection.facts) &&
        authorityIsLocked(projection.authority),
    );
  }

  function unknownView() {
    return {
      validContract: false,
      sourceState: "UNKNOWN",
      gapState: "UNKNOWN",
      maturityState: "UNMOUNTED_CANDIDATE",
      permissionState: "UNAUTHORIZED",
      decisionLabel: "会话滞后证据未知",
      metrics: {
        completedSessionLag: null,
        registeredLimit: null,
        calendarCount: null,
        clockSourceCount: null,
      },
      cutoffLabel: "未提供",
      referenceLabel: "未提供",
      clockQuality: "UNKNOWN",
      blockerCount: null,
      localConditionSatisfied: false,
      externalAuthorityLabel: "未认证",
      permissionLabel: "PAPER / LIVE 未授权",
      stages: [
        { stage: "SOURCE", state: "UNKNOWN" },
        { stage: "GAP", state: "UNKNOWN" },
        { stage: "MATURITY", state: "UNMOUNTED_CANDIDATE" },
        { stage: "PERMISSION", state: "UNAUTHORIZED" },
      ],
    };
  }

  function decisionLabel(gapState) {
    if (gapState === "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP") {
      return "本地会话滞后在阈值内，外部时钟权威未认证";
    }
    if (gapState === "SESSION_LAG_POLICY_GAP_PRESENT") {
      return "完成会话滞后超过预登记阈值";
    }
    if (gapState === "UNVERIFIED_FRESHNESS_EVIDENCE_GAP") {
      return "会话滞后尚未形成可验证结论";
    }
    if (gapState === "NOT_SUPPLIED") return "会话滞后证据未提供";
    return "会话滞后证据未知";
  }

  function buildSessionFreshnessViewModel(projection) {
    if (!projectionIsValid(projection)) return unknownView();
    const summary = projection.summary;
    return {
      validContract: true,
      sourceState: projection.pipeline[0].state,
      gapState: projection.pipeline[1].state,
      maturityState: projection.pipeline[2].state,
      permissionState: projection.pipeline[3].state,
      decisionLabel: decisionLabel(projection.pipeline[1].state),
      metrics: {
        completedSessionLag: summary.max_completed_session_lag,
        registeredLimit: summary.preregistered_max_completed_session_lag,
        calendarCount: summary.calendar_count,
        clockSourceCount: summary.external_clock_source_count,
      },
      cutoffLabel: summary.cutoff_session_label || "未提供",
      referenceLabel: summary.reference_time_utc || "未提供",
      clockQuality: summary.clock_quality || "UNKNOWN",
      blockerCount: summary.blocker_count,
      localConditionSatisfied: summary.local_policy_condition_satisfied === true,
      externalAuthorityLabel: "未认证",
      permissionLabel: "PAPER / LIVE 未授权",
      stages: projection.pipeline.map(function (item) {
        return { stage: item.stage, state: item.state };
      }),
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function metric(value) {
    return Number.isInteger(value) ? String(value) : "?";
  }

  function stageTone(stage) {
    if (stage.stage === "PERMISSION") return "permission";
    if (stage.stage === "MATURITY") return "maturity";
    if (stage.state === "UNKNOWN" || stage.state === "NOT_SUPPLIED") return "unknown";
    if (stage.stage === "GAP") return "gap";
    return "source";
  }

  function renderStage(stage, index) {
    const labels = {
      SOURCE: "来源",
      GAP: "缺口",
      MATURITY: "成熟度",
      PERMISSION: "权限",
    };
    return [
      '<li class="hkm-session-lag__stage" data-tone="',
      escapeHtml(stageTone(stage)),
      '"><span aria-hidden="true">',
      String(index + 1).padStart(2, "0"),
      "</span><div><b>",
      escapeHtml(labels[stage.stage] || stage.stage),
      "</b><small>",
      escapeHtml(stage.state),
      "</small></div></li>",
    ].join("");
  }

  function renderTicks(view) {
    const limit = Number.isInteger(view.metrics.registeredLimit)
      ? view.metrics.registeredLimit
      : 1;
    const lag = Number.isInteger(view.metrics.completedSessionLag)
      ? view.metrics.completedSessionLag
      : -1;
    const upper = Math.max(3, Math.min(8, limit + 2, lag + 1));
    const ticks = [];
    for (let index = 0; index <= upper; index += 1) {
      const states = ["hkm-session-lag__tick"];
      if (index <= lag) states.push("is-observed");
      if (index === limit) states.push("is-limit");
      ticks.push(
        '<span class="' + states.join(" ") + '" data-index="' + index +
          '"><i></i><b>' + index + "</b></span>",
      );
    }
    return ticks.join("");
  }

  function renderSessionFreshnessCard(projection, options) {
    const view = buildSessionFreshnessViewModel(projection);
    const copy = isObject(options) ? options : {};
    const title = typeof copy.title === "string" ? copy.title : "会话滞后尺";
    const eyebrow = typeof copy.eyebrow === "string"
      ? copy.eyebrow
      : "CORRELATION CLUSTER · SESSION LAG LEDGER";
    return [
      '<article class="hkm-session-lag" data-gap-state="',
      escapeHtml(view.gapState),
      '" aria-label="相关簇会话滞后候选卡">',
      '<div class="hkm-session-lag__perforation" aria-hidden="true"></div>',
      '<header class="hkm-session-lag__header"><div><p>',
      escapeHtml(eyebrow),
      "</p><h2>",
      escapeHtml(title),
      '</h2></div><span class="hkm-session-lag__badge">未挂载候选</span></header>',
      '<ol class="hkm-session-lag__rail">',
      view.stages.map(renderStage).join(""),
      "</ol>",
      '<div class="hkm-session-lag__layout">',
      '<section class="hkm-session-lag__tape" aria-label="完成会话滞后刻度">',
      '<div class="hkm-session-lag__dates"><span><small>CUTOFF</small><b>',
      escapeHtml(view.cutoffLabel),
      '</b></span><span><small>REFERENCE</small><b>',
      escapeHtml(view.referenceLabel),
      "</b></span></div>",
      '<div class="hkm-session-lag__ticks">',
      renderTicks(view),
      "</div>",
      '<div class="hkm-session-lag__ratio"><span><b>',
      escapeHtml(metric(view.metrics.completedSessionLag)),
      "</b><small>完成会话滞后</small></span><em>/</em><span><b>",
      escapeHtml(metric(view.metrics.registeredLimit)),
      "</b><small>预登记上限</small></span></div>",
      "</section>",
      '<section class="hkm-session-lag__ledger">',
      '<p class="hkm-session-lag__decision">',
      escapeHtml(view.decisionLabel),
      "</p>",
      '<dl><div><dt>时钟证据</dt><dd>',
      escapeHtml(view.clockQuality),
      '</dd></div><div><dt>时钟源数量</dt><dd>',
      escapeHtml(metric(view.metrics.clockSourceCount)),
      '</dd></div><div><dt>日历数量</dt><dd>',
      escapeHtml(metric(view.metrics.calendarCount)),
      '</dd></div><div class="is-gap"><dt>外部时钟权威</dt><dd>',
      escapeHtml(view.externalAuthorityLabel),
      "</dd></div></dl>",
      '<aside><b>边界</b><span>本地阈值条件不等于真实市场 freshness，也不产生交易权限。</span></aside>',
      "</section>",
      "</div>",
      '<footer class="hkm-session-lag__footer"><span>BLOCKERS ',
      escapeHtml(metric(view.blockerCount)),
      "</span><b>",
      escapeHtml(view.permissionLabel),
      "</b></footer>",
      "</article>",
    ].join("");
  }

  function mountSessionFreshnessCard(target, projection, options) {
    if (!target || typeof target !== "object" || !("innerHTML" in target)) {
      throw new TypeError("A mount target with innerHTML is required.");
    }
    target.innerHTML = renderSessionFreshnessCard(projection, options);
    return target;
  }

  return {
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    buildSessionFreshnessViewModel: buildSessionFreshnessViewModel,
    renderSessionFreshnessCard: renderSessionFreshnessCard,
    mountSessionFreshnessCard: mountSessionFreshnessCard,
  };
});
