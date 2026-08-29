(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiPortfolioRiskShadowReadinessCardV1 = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-cluster-portfolio-risk-shadow-readiness-public-projection-v1";
  var STATIC_FINGERPRINT =
    "20260822-shadow-readiness-evidence-stair-projection-lock-1";
  var STAGE_ORDER = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  var ALLOWED_STATES = {
    SOURCE: ["LOCAL_EVIDENCE_VERIFIED", "UNKNOWN", "NOT_SUPPLIED"],
    GAP: [
      "EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN",
      "UNKNOWN",
      "NOT_SUPPLIED",
    ],
    MATURITY: ["UNMOUNTED_CANDIDATE"],
    PERMISSION: ["UNAUTHORIZED"],
  };
  var STAGE_LABELS = {
    SOURCE: "来源",
    GAP: "缺口",
    MATURITY: "成熟度",
    PERMISSION: "权限",
  };
  var STATE_LABELS = {
    LOCAL_EVIDENCE_VERIFIED: "本地证据已验证",
    EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN: "外部信任与运行时绑定未证明",
    UNKNOWN: "未知",
    NOT_SUPPLIED: "未提供",
    UNMOUNTED_CANDIDATE: "未挂载候选",
    UNAUTHORIZED: "未授权",
  };

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function isOptionalInteger(value) {
    return value === null || (Number.isInteger(value) && value >= 0);
  }

  function isOptionalString(value) {
    return value === null || typeof value === "string";
  }

  function hasLockedAuthority(authority) {
    if (!isObject(authority) || authority.descriptive_only !== true) {
      return false;
    }
    return [
      "current_admission_allowed",
      "current_pointer_written",
      "formal_registry_activation_allowed",
      "live_order_allowed",
      "migration_allowed",
      "paper_authorized",
      "risk_service_invocation_allowed",
      "runtime_gate_activation_allowed",
      "shadow_consumer_activation_allowed",
      "writer_allowed",
    ].every(function (key) {
      return authority[key] === false;
    });
  }

  function hasValidPipeline(projection) {
    return (
      Array.isArray(projection.pipeline) &&
      projection.pipeline.length === 4 &&
      projection.pipeline.every(function (item, index) {
        var stage = STAGE_ORDER[index];
        return (
          isObject(item) &&
          item.stage === stage &&
          ALLOWED_STATES[stage].indexOf(item.state) !== -1
        );
      })
    );
  }

  function hasConsistentState(projection) {
    var source = projection.pipeline[0].state;
    var gap = projection.pipeline[1].state;
    if (projection.status === "OBSERVED") {
      return (
        source === "LOCAL_EVIDENCE_VERIFIED" &&
        gap === "EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN"
      );
    }
    if (projection.status === "UNKNOWN") {
      return source === "UNKNOWN" && gap === "UNKNOWN";
    }
    if (projection.status === "NOT_SUPPLIED") {
      return source === "NOT_SUPPLIED" && gap === "NOT_SUPPLIED";
    }
    return false;
  }

  function hasValidSource(source) {
    if (!isObject(source)) {
      return false;
    }
    return (
      typeof source.readiness_envelope_supplied === "boolean" &&
      typeof source.readiness_envelope_exactly_verified === "boolean" &&
      isOptionalString(source.readiness_schema_version) &&
      (source.readiness_envelope_hash === null ||
        /^[0-9a-f]{64}$/.test(source.readiness_envelope_hash)) &&
      typeof source.preregistration_supplied === "boolean" &&
      typeof source.preregistration_exactly_verified === "boolean" &&
      isOptionalString(source.preregistration_schema_version) &&
      (source.preregistration_hash === null ||
        /^[0-9a-f]{64}$/.test(source.preregistration_hash)) &&
      typeof source.contract_pin_aligned === "boolean" &&
      source.readiness_evidence_bound_to_preregistration === false
    );
  }

  function hasValidSummary(summary, status) {
    if (!isObject(summary)) {
      return false;
    }
    var scalarShape =
      isOptionalInteger(summary.required_input_count) &&
      isOptionalInteger(summary.verified_input_count) &&
      isOptionalInteger(summary.signed_clock_source_count) &&
      isOptionalInteger(summary.closed_local_blocker_count) &&
      isOptionalInteger(summary.readiness_blocker_count) &&
      isOptionalInteger(summary.preregistration_blocker_count) &&
      (summary.preregistration_status === null ||
        summary.preregistration_status === "BLOCKED") &&
      typeof summary.contract_pin_aligned === "boolean" &&
      summary.readiness_evidence_bound_to_preregistration === false &&
      summary.consumer_executed === false &&
      summary.external_time_authority_authenticated === false &&
      summary.current_time_established === false;
    if (!scalarShape) {
      return false;
    }
    if (status !== "OBSERVED") {
      return true;
    }
    return (
      summary.required_input_count === 14 &&
      summary.verified_input_count === 14 &&
      summary.signed_clock_source_count >= 2 &&
      summary.closed_local_blocker_count === 3 &&
      summary.preregistration_status === "BLOCKED" &&
      summary.contract_pin_aligned === true
    );
  }

  function isValidProjection(projection) {
    return Boolean(
      isObject(projection) &&
        projection.schema_version === PROJECTION_SCHEMA_VERSION &&
        projection.static_fingerprint === STATIC_FINGERPRINT &&
        /^[0-9a-f]{64}$/.test(projection.projection_hash || "") &&
        ["OBSERVED", "UNKNOWN", "NOT_SUPPLIED"].indexOf(projection.status) !== -1 &&
        hasValidPipeline(projection) &&
        hasConsistentState(projection) &&
        hasValidSource(projection.source) &&
        hasValidSummary(projection.summary, projection.status) &&
        hasLockedAuthority(projection.authority)
    );
  }

  function tone(state) {
    if (state === "LOCAL_EVIDENCE_VERIFIED") return "source";
    if (state === "EXTERNAL_TRUST_AND_RUNTIME_BINDING_UNPROVEN") return "gap";
    if (state === "UNMOUNTED_CANDIDATE") return "maturity";
    if (state === "UNAUTHORIZED") return "permission";
    return "unknown";
  }

  function fallbackViewModel() {
    return {
      validContract: false,
      status: "UNKNOWN",
      badgeLabel: "合同未知",
      decisionLabel: "无法验证 shadow readiness 公开投影",
      stages: STAGE_ORDER.map(function (stage) {
        var state =
          stage === "MATURITY"
            ? "UNMOUNTED_CANDIDATE"
            : stage === "PERMISSION"
              ? "UNAUTHORIZED"
              : "UNKNOWN";
        return {
          stage: stage,
          stageLabel: STAGE_LABELS[stage],
          state: state,
          stateLabel: STATE_LABELS[state],
          tone: tone(state),
        };
      }),
      metrics: {
        requiredInputs: null,
        verifiedInputs: null,
        signedClockSources: null,
        closedLocalBlockers: null,
        readinessBlockers: null,
        preregistrationBlockers: null,
      },
      contractPinAligned: false,
      evidenceBound: false,
      consumerExecuted: false,
      permissionLabel: "PAPER / LIVE 未授权",
    };
  }

  function buildShadowReadinessViewModel(projection) {
    if (!isValidProjection(projection)) {
      return fallbackViewModel();
    }
    var summary = projection.summary;
    var stages = projection.pipeline.map(function (item) {
      return {
        stage: item.stage,
        stageLabel: STAGE_LABELS[item.stage],
        state: item.state,
        stateLabel: STATE_LABELS[item.state],
        tone: tone(item.state),
      };
    });
    var decision = "尚未提供 shadow readiness 公开投影";
    if (projection.status === "OBSERVED") {
      decision =
        "14 项本地输入与签名时钟 quorum 已验证；外部信任与运行时绑定仍未证明。";
    } else if (projection.status === "UNKNOWN") {
      decision = "shadow readiness 来源无法完成公开重验";
    }
    return {
      validContract: true,
      status: projection.status,
      badgeLabel:
        projection.status === "OBSERVED"
          ? "本地观测"
          : projection.status === "NOT_SUPPLIED"
            ? "未提供"
            : "未知",
      decisionLabel: decision,
      stages: stages,
      metrics: {
        requiredInputs: summary.required_input_count,
        verifiedInputs: summary.verified_input_count,
        signedClockSources: summary.signed_clock_source_count,
        closedLocalBlockers: summary.closed_local_blocker_count,
        readinessBlockers: summary.readiness_blocker_count,
        preregistrationBlockers: summary.preregistration_blocker_count,
      },
      contractPinAligned: summary.contract_pin_aligned,
      evidenceBound: summary.readiness_evidence_bound_to_preregistration,
      consumerExecuted: summary.consumer_executed,
      permissionLabel: "PAPER / LIVE 未授权",
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
    return value === null ? "N/A" : String(value);
  }

  function renderStage(stage, index) {
    return [
      '<li class="hkm-readiness-stair__stage" data-tone="',
      escapeHtml(stage.tone),
      '"><span>0',
      String(index + 1),
      "</span><div><b>",
      escapeHtml(stage.stageLabel),
      "</b><small>",
      escapeHtml(stage.stateLabel),
      "</small></div></li>",
    ].join("");
  }

  function renderSteps(view) {
    var count = view.metrics.requiredInputs === null ? 14 : view.metrics.requiredInputs;
    return Array.from({ length: count }, function (_, index) {
      var verified =
        view.metrics.verifiedInputs !== null && index < view.metrics.verifiedInputs;
      return [
        '<i data-state="',
        verified ? "verified" : "unknown",
        '" style="--step-index:',
        String(index),
        '"><span>',
        String(index + 1).padStart(2, "0"),
        "</span></i>",
      ].join("");
    }).join("");
  }

  function renderShadowReadinessCard(projection, options) {
    var view = buildShadowReadinessViewModel(projection);
    var config = isObject(options) ? options : {};
    var eyebrow =
      typeof config.eyebrow === "string"
        ? config.eyebrow
        : "SHADOW READINESS / LOCAL EVIDENCE ONLY";
    var title = typeof config.title === "string" ? config.title : "证据阶梯";
    return [
      '<article class="hkm-readiness-stair" data-contract-valid="',
      view.validContract ? "true" : "false",
      '"><div class="hkm-readiness-stair__trace" aria-hidden="true"></div>',
      '<header class="hkm-readiness-stair__header"><div><p>',
      escapeHtml(eyebrow),
      "</p><h2>",
      escapeHtml(title),
      '</h2></div><span class="hkm-readiness-stair__badge">',
      escapeHtml(view.badgeLabel),
      "</span></header>",
      '<ol class="hkm-readiness-stair__rail" aria-label="来源到权限路径">',
      view.stages.map(renderStage).join(""),
      "</ol>",
      '<div class="hkm-readiness-stair__layout"><section class="hkm-readiness-stair__steps">',
      '<div class="hkm-readiness-stair__steps-head"><span>LOCAL INPUT LEDGER</span><b>',
      escapeHtml(metric(view.metrics.verifiedInputs)),
      " / ",
      escapeHtml(metric(view.metrics.requiredInputs)),
      "</b></div><div class=\"hkm-readiness-stair__stack\">",
      renderSteps(view),
      "</div><p>",
      escapeHtml(view.decisionLabel),
      "</p></section>",
      '<section class="hkm-readiness-stair__ledger"><div class="hkm-readiness-stair__seal">',
      '<span><b>',
      escapeHtml(metric(view.metrics.signedClockSources)),
      "</b><small>签名时钟源</small></span><span><b>",
      escapeHtml(metric(view.metrics.closedLocalBlockers)),
      "</b><small>既有本地闭合项</small></span></div>",
      '<dl><div><dt>合同 pin 对齐</dt><dd>',
      view.contractPinAligned ? "是" : "未知",
      "</dd></div><div class=\"is-gap\"><dt>readiness evidence 绑定</dt><dd>",
      view.evidenceBound ? "是" : "未绑定",
      "</dd></div><div class=\"is-gap\"><dt>外部时钟权威</dt><dd>未认证</dd></div>",
      '<div class="is-gap"><dt>运行时 consumer</dt><dd>',
      view.consumerExecuted ? "已执行" : "未执行",
      "</dd></div></dl>",
      '<div class="hkm-readiness-stair__blockers"><span>READINESS BLOCKERS <b>',
      escapeHtml(metric(view.metrics.readinessBlockers)),
      "</b></span><span>PREREG BLOCKERS <b>",
      escapeHtml(metric(view.metrics.preregistrationBlockers)),
      "</b></span></div></section></div>",
      '<footer class="hkm-readiness-stair__footer"><span>CONTRACT PIN != EVIDENCE BINDING</span><b>',
      escapeHtml(view.permissionLabel),
      "</b></footer></article>",
    ].join("");
  }

  function mountShadowReadinessCard(target, projection, options) {
    if (!target || typeof target !== "object" || !("innerHTML" in target)) {
      throw new TypeError("A mount target with innerHTML is required.");
    }
    target.innerHTML = renderShadowReadinessCard(projection, options);
    return target;
  }

  return {
    PROJECTION_SCHEMA_VERSION: PROJECTION_SCHEMA_VERSION,
    STATIC_FINGERPRINT: STATIC_FINGERPRINT,
    buildShadowReadinessViewModel: buildShadowReadinessViewModel,
    renderShadowReadinessCard: renderShadowReadinessCard,
    mountShadowReadinessCard: mountShadowReadinessCard,
  };
});
