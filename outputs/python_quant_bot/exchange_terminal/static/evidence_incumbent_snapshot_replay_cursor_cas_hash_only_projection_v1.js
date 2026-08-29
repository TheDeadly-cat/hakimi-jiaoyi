(function attachReplayCursorCasPresenterV1(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
    return;
  }
  if (root && typeof root === "object") {
    Object.defineProperty(root, "HakimiReplayCursorCasPresenterV1", {
      configurable: false,
      enumerable: false,
      value: api,
      writable: false,
    });
  }
})(typeof globalThis === "object" ? globalThis : this, function buildApi() {
  "use strict";

  const HANDOFF_SCHEMA_VERSION =
    "incumbent-snapshot-replay-cursor-cas-hash-only-projection-verification-handoff-v1";
  const VERIFICATION_STATUS =
    "EXACTLY_VERIFIED_INCUMBENT_SNAPSHOT_REPLAY_CURSOR_CAS_HASH_ONLY_PROJECTION_V1";
  const PROJECTION_SCHEMA_VERSION =
    "strategy-correlation-incumbent-snapshot-replay-cursor-cas-transition-hash-only-projection-v1";
  const STATIC_FINGERPRINT =
    "20260824-incumbent-snapshot-replay-cursor-cas-hash-only-unmounted-permission-lock-1";
  const CONSUMER_STATUS =
    "UNMOUNTED_READONLY_REPLAY_CURSOR_CAS_CANDIDATE";
  const CAS_CONTRACT_VERSION =
    "incumbent-snapshot-replay-cursor-cas-transition-v1";

  const OUTCOME_ALREADY_CONSUMED = "ALREADY_CONSUMED";
  const OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER =
    "SNAPSHOT_SEQUENCE_NOT_ABOVE_OBSERVED_HIGH_WATER";
  const OUTCOME_COMPARE_AND_SWAP_CONFLICT = "COMPARE_AND_SWAP_CONFLICT";
  const OUTCOME_ADVANCED_IN_RETURNED_CURSOR =
    "ADVANCED_IN_RETURNED_CURSOR";
  const GATE_STATUS_BLOCK = "BLOCK";
  const GATE_STATUS_UNKNOWN = "UNKNOWN";

  const STAGE_ORDER = Object.freeze([
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  const STATIC_BOUNDARIES = Object.freeze([
    "ATOMIC_STORAGE_COMMIT_NOT_VERIFIED",
    "DURABLE_COMMIT_NOT_VERIFIED",
    "LINEARIZABLE_READ_NOT_VERIFIED",
    "PAPER_LIVE_UNAUTHORIZED",
  ]);
  const HASH_PATTERN = /^[0-9a-f]{64}$/;

  const OUTCOME_PATHS = Object.freeze({
    [OUTCOME_ALREADY_CONSUMED]: Object.freeze({
      gap: "ATTESTATION_ALREADY_CONSUMED",
      maturity: "REPLAY_BLOCKED",
      tone: "blocked",
      label: "回放阻断",
      headline: "该快照证明已被观察游标消费",
    }),
    [OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER]: Object.freeze({
      gap: "SNAPSHOT_SEQUENCE_NOT_MONOTONIC",
      maturity: "SEQUENCE_BLOCKED",
      tone: "blocked",
      label: "序列阻断",
      headline: "候选序列未越过观察游标高水位",
    }),
    [OUTCOME_COMPARE_AND_SWAP_CONFLICT]: Object.freeze({
      gap: "EXPECTED_CURSOR_CHANGED",
      maturity: "CONCURRENT_STATE_UNRESOLVED",
      tone: "conflict",
      label: "并发竞争未闭合",
      headline: "观察游标已偏离转换意图的预期基线",
    }),
    [OUTCOME_ADVANCED_IN_RETURNED_CURSOR]: Object.freeze({
      gap: "ATOMIC_STORAGE_COMMIT_NOT_VERIFIED",
      maturity: "SYNTHETIC_RETURNED_CURSOR_ONLY",
      tone: "observed",
      label: "合成游标观察",
      headline: "游标推进仅存在于未提交的合成返回值",
    }),
  });

  const AUTHORITY = Object.freeze({
    permission_state: "RESEARCH_ONLY",
    permission: false,
    paper_authorized: false,
    live_authorized: false,
    input_cursor_mutation_performed: false,
    atomic_storage_commit_verified: false,
    durable_commit_verified: false,
    linearizable_read_verified: false,
    provider_identity_verified: false,
    current_chain_activated: false,
  });
  const REDACTION = Object.freeze({
    raw_stream_id_redacted: true,
    raw_request_nonce_redacted: true,
    raw_cursor_documents_redacted: true,
    raw_consumed_attestation_hashes_redacted: true,
    raw_high_water_attestation_hash_redacted: true,
    raw_intent_document_redacted: true,
    raw_receipt_document_redacted: true,
    raw_incumbent_snapshot_redacted: true,
    raw_proposals_and_holdings_redacted: true,
    raw_signatures_and_keys_redacted: true,
  });
  const BOUNDARY_LABELS = Object.freeze({
    ATOMIC_STORAGE_COMMIT_NOT_VERIFIED: "原子存储提交尚未核验",
    DURABLE_COMMIT_NOT_VERIFIED: "持久化提交尚未核验",
    LINEARIZABLE_READ_NOT_VERIFIED: "线性一致读取尚未核验",
    PAPER_LIVE_UNAUTHORIZED: "模拟未授权，实盘永久硬锁",
  });

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function exactKeys(value, keys) {
    if (!isRecord(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = keys.slice().sort();
    return actual.length === expected.length &&
      actual.every((key, index) => key === expected[index]);
  }

  function exactRecord(value, expected) {
    const keys = Object.keys(expected);
    return exactKeys(value, keys) &&
      keys.every((key) => value[key] === expected[key]);
  }

  function isHash(value) {
    return typeof value === "string" && HASH_PATTERN.test(value);
  }

  function isSequence(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }

  function validSourceLineage(source) {
    const keys = [
      "cas_contract_version",
      "intent_hash",
      "freshness_result_fingerprint_sha256",
      "candidate_attestation_hash",
      "projection_preregistration_hash",
      "stream_id_sha256",
      "base_cursor_hash",
      "observed_cursor_hash",
      "returned_cursor_hash",
      "transition_receipt_hash",
    ];
    return exactKeys(source, keys) &&
      source.cas_contract_version === CAS_CONTRACT_VERSION &&
      keys.slice(1).every((key) => isHash(source[key]));
  }

  function validObservation(observation) {
    if (!exactKeys(observation, [
      "outcome",
      "gate_status",
      "candidate_sequence",
      "observed_high_water_sequence",
      "returned_high_water_sequence",
      "returned_cursor_changed",
    ])) return false;
    const path = OUTCOME_PATHS[observation.outcome];
    if (!path || !isSequence(observation.candidate_sequence) ||
      !isSequence(observation.observed_high_water_sequence) ||
      !isSequence(observation.returned_high_water_sequence) ||
      typeof observation.returned_cursor_changed !== "boolean") return false;

    const candidate = observation.candidate_sequence;
    const observed = observation.observed_high_water_sequence;
    const returned = observation.returned_high_water_sequence;
    if (observation.outcome === OUTCOME_ADVANCED_IN_RETURNED_CURSOR) {
      return observation.gate_status === GATE_STATUS_UNKNOWN &&
        candidate > observed && returned === candidate &&
        observation.returned_cursor_changed === true;
    }
    if (observation.outcome === OUTCOME_COMPARE_AND_SWAP_CONFLICT) {
      return observation.gate_status === GATE_STATUS_UNKNOWN &&
        candidate > observed && returned === observed &&
        observation.returned_cursor_changed === false;
    }
    return observation.gate_status === GATE_STATUS_BLOCK &&
      candidate <= observed && returned === observed &&
      observation.returned_cursor_changed === false;
  }

  function validProjection(envelope) {
    if (!exactKeys(envelope, [
      "schema_version",
      "verification_status",
      "expected_readonly_projection_hash",
      "projection",
    ]) || envelope.schema_version !== HANDOFF_SCHEMA_VERSION ||
      envelope.verification_status !== VERIFICATION_STATUS ||
      !isHash(envelope.expected_readonly_projection_hash)) return false;

    const projection = envelope.projection;
    return exactKeys(projection, [
      "projection_schema_version",
      "static_fingerprint",
      "consumer_status",
      "source_lineage",
      "observation",
      "authority",
      "redaction",
      "readonly_projection_hash",
    ]) &&
      projection.projection_schema_version === PROJECTION_SCHEMA_VERSION &&
      projection.static_fingerprint === STATIC_FINGERPRINT &&
      projection.consumer_status === CONSUMER_STATUS &&
      isHash(projection.readonly_projection_hash) &&
      projection.readonly_projection_hash ===
        envelope.expected_readonly_projection_hash &&
      validSourceLineage(projection.source_lineage) &&
      validObservation(projection.observation) &&
      exactRecord(projection.authority, AUTHORITY) &&
      exactRecord(projection.redaction, REDACTION);
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.values(value).forEach(deepFreeze);
    }
    return value;
  }

  function shortHash(value) {
    return isHash(value) ? `${value.slice(0, 8)}...${value.slice(-8)}` : "--";
  }

  function signedDelta(candidate, observed) {
    if (!isSequence(candidate) || !isSequence(observed)) return "--";
    const delta = candidate - observed;
    return delta > 0 ? `+${delta}` : String(delta);
  }

  function unknownModel() {
    return deepFreeze({
      verificationAccepted: false,
      rawOutcome: "UNKNOWN",
      rawGateStatus: GATE_STATUS_UNKNOWN,
      tone: "unknown",
      statusLabel: "未核验",
      headline: "回放游标 CAS 验证交接未闭合",
      eyebrow: "静态 CAS 证据 · 非实时状态",
      stages: [
        { key: "SOURCE", value: "ADR0382 exact handoff：未确认" },
        { key: "GAP", value: "输入、哈希或权限锁合同不完整" },
        { key: "MATURITY", value: "UNVERIFIED" },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      sequences: [
        { label: "候选序列", value: "--" },
        { label: "观察高水位", value: "--" },
        { label: "返回高水位", value: "--" },
        { label: "序列差", value: "--" },
      ],
      lineage: [
        { label: "INTENT", value: "--" },
        { label: "OBSERVED CURSOR", value: "--" },
        { label: "RECEIPT", value: "--" },
      ],
      boundaries: [
        {
          code: "PRESENTATION_INPUT_NOT_EXACTLY_VERIFIED",
          label: "展示输入未完成精确验证交接",
        },
        ...STATIC_BOUNDARIES.map((code) => ({
          code,
          label: BOUNDARY_LABELS[code],
        })),
      ],
      projectionHash: "--",
      caution: "不构成提交、持仓、准入、信号、订单或收益结论",
    });
  }

  function deriveReplayCursorCasViewModelV1(envelope) {
    if (!validProjection(envelope)) return unknownModel();
    const projection = envelope.projection;
    const observation = projection.observation;
    const source = projection.source_lineage;
    const path = OUTCOME_PATHS[observation.outcome];
    return deepFreeze({
      verificationAccepted: true,
      rawOutcome: observation.outcome,
      rawGateStatus: observation.gate_status,
      tone: path.tone,
      statusLabel: path.label,
      headline: path.headline,
      eyebrow: "静态 CAS 证据 · 非实时状态",
      stages: [
        {
          key: "SOURCE",
          value: `ADR0381 投影 ${shortHash(projection.readonly_projection_hash)}`,
        },
        { key: "GAP", value: path.gap },
        { key: "MATURITY", value: path.maturity },
        { key: "PERMISSION", value: "模拟未授权 · 实盘永久硬锁" },
      ],
      sequences: [
        { label: "候选序列", value: String(observation.candidate_sequence) },
        {
          label: "观察高水位",
          value: String(observation.observed_high_water_sequence),
        },
        {
          label: "返回高水位",
          value: String(observation.returned_high_water_sequence),
        },
        {
          label: "序列差",
          value: signedDelta(
            observation.candidate_sequence,
            observation.observed_high_water_sequence,
          ),
        },
      ],
      lineage: [
        { label: "INTENT", value: shortHash(source.intent_hash) },
        {
          label: "OBSERVED CURSOR",
          value: shortHash(source.observed_cursor_hash),
        },
        { label: "RECEIPT", value: shortHash(source.transition_receipt_hash) },
      ],
      boundaries: STATIC_BOUNDARIES.map((code) => ({
        code,
        label: BOUNDARY_LABELS[code],
      })),
      projectionHash: shortHash(projection.readonly_projection_hash),
      caution: "不构成提交、持仓、准入、信号、订单或收益结论",
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

  function renderReplayCursorCasHashOnlyProjectionV1(envelope) {
    const model = deriveReplayCursorCasViewModelV1(envelope);
    const headingId = `replayCursorCasHeading-${
      model.projectionHash === "--" ? "unknown" : model.projectionHash.slice(0, 8)
    }`;
    return [
      `<article class="cursor-cas-plate-v1 is-${escapeHtml(model.tone)}" data-evidence-role="replay-cursor-cas-readonly" data-gate-status="${escapeHtml(model.rawGateStatus)}" aria-labelledby="${headingId}">`,
      '<header class="cursor-cas-plate-v1__header">',
      `<div><span>${escapeHtml(model.eyebrow)}</span><h3 id="${headingId}">${escapeHtml(model.headline)}</h3></div>`,
      `<strong>${escapeHtml(model.statusLabel)}</strong>`,
      "</header>",
      '<div class="cursor-cas-plate-v1__body">',
      '<div class="cursor-cas-plate-v1__switchboard" aria-hidden="true">',
      '<span class="cursor-cas-plate-v1__rail"></span>',
      `<div class="cursor-node is-base"><small>OBSERVED</small><b>${escapeHtml(model.sequences[1].value)}</b></div>`,
      `<div class="cursor-node is-candidate"><small>CANDIDATE</small><b>${escapeHtml(model.sequences[0].value)}</b></div>`,
      `<div class="cursor-node is-returned"><small>RETURNED</small><b>${escapeHtml(model.sequences[2].value)}</b></div>`,
      `<div class="cursor-cas-plate-v1__delta"><small>DELTA</small><strong>${escapeHtml(model.sequences[3].value)}</strong></div>`,
      "</div>",
      '<dl class="cursor-cas-plate-v1__sequences">',
      ...model.sequences.map((item) => `<div><dt>${escapeHtml(item.label)}</dt><dd>${escapeHtml(item.value)}</dd></div>`),
      "</dl></div>",
      '<ol class="cursor-cas-plate-v1__flow">',
      ...model.stages.map((stage) => `<li data-stage="${stage.key.toLowerCase()}"><span>${stage.key}</span><strong>${escapeHtml(stage.value)}</strong></li>`),
      "</ol>",
      '<div class="cursor-cas-plate-v1__ledger">',
      '<section><h4>HASH LINEAGE</h4><ul>',
      ...model.lineage.map((item) => `<li><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></li>`),
      "</ul></section>",
      '<details open><summary>提交缺口与权限边界</summary><ul>',
      ...model.boundaries.map((item) => `<li><span>${escapeHtml(item.code)}</span><strong>${escapeHtml(item.label)}</strong></li>`),
      "</ul></details></div>",
      `<footer><span>PROJECTION ${escapeHtml(model.projectionHash)}</span><strong>${escapeHtml(model.caution)}</strong></footer>`,
      "</article>",
    ].join("");
  }

  return deepFreeze({
    HANDOFF_SCHEMA_VERSION,
    VERIFICATION_STATUS,
    PROJECTION_SCHEMA_VERSION,
    OUTCOME_ALREADY_CONSUMED,
    OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER,
    OUTCOME_COMPARE_AND_SWAP_CONFLICT,
    OUTCOME_ADVANCED_IN_RETURNED_CURSOR,
    GATE_STATUS_BLOCK,
    GATE_STATUS_UNKNOWN,
    STAGE_ORDER,
    deriveReplayCursorCasViewModelV1,
    renderReplayCursorCasHashOnlyProjectionV1,
  });
});
