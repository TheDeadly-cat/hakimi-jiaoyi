"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const presenter = require("./evidence_cluster_exposure_readonly_projection_v1.js");

const STATIC_BLOCKERS = [
  "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
  "READONLY_PROJECTION_NOT_REGISTERED",
  "PAPER_LIVE_UNAUTHORIZED",
];

function projection(status = presenter.STATUS_WITHIN_LIMIT) {
  const policyBlockers =
    status === presenter.STATUS_LIMIT_BREACH
      ? ["CLUSTER_GROSS_LIMIT_EXCEEDED"]
      : status === presenter.STATUS_UNKNOWN
        ? ["POLICY_LIMIT_ORDER_INVALID"]
        : [];
  const summary =
    status === presenter.STATUS_UNKNOWN
      ? {
          proposal_count: null,
          independent_cluster_count: null,
          total_gross_bps: null,
          maximum_cluster_gross_bps: null,
        }
      : status === presenter.STATUS_LIMIT_BREACH
        ? {
            proposal_count: 2,
            independent_cluster_count: 1,
            total_gross_bps: 3100,
            maximum_cluster_gross_bps: 3100,
          }
        : {
            proposal_count: 2,
            independent_cluster_count: 2,
            total_gross_bps: 2100,
            maximum_cluster_gross_bps: 1100,
          };
  const paths = {
    [presenter.STATUS_UNKNOWN]: {
      gap: "SOURCE_OR_POLICY_CONTRACT_UNKNOWN",
      maturity: "UNVERIFIED",
    },
    [presenter.STATUS_LIMIT_BREACH]: {
      gap: "PREREGISTERED_CLUSTER_EXPOSURE_LIMIT_BREACH",
      maturity: "STRUCTURAL_POLICY_BREACH",
    },
    [presenter.STATUS_WITHIN_LIMIT]: {
      gap: "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
      maturity: "PREREGISTERED_STRUCTURE_ONLY",
    },
  };
  return {
    schema_version:
      "strategy-correlation-history-covered-budget-universe-cluster-exposure-readonly-projection-v1",
    static_fingerprint:
      "20260824-cluster-exposure-readonly-projection-v1-verified-batch-hash-only-unmounted-permission-lock-1",
    consumer_status: "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CANDIDATE",
    registered: false,
    status,
    source: {
      adapter_contract_version:
        "strategy-correlation-history-covered-budget-universe-cluster-exposure-source-receipt-adapter-v1",
      cluster_exposure_result_hash: "a".repeat(64),
      policy_fingerprint_sha256:
        status === presenter.STATUS_UNKNOWN ? null : "b".repeat(64),
      source_batch_fingerprint_sha256: "c".repeat(64),
    },
    decision_path: {
      source: "ADR0370_EXACT_VERIFIED_BATCH_RECEIPT",
      gap: paths[status].gap,
      maturity: paths[status].maturity,
      permission: "NOT_AUTHORIZED",
    },
    summary,
    policy_blocker_codes: policyBlockers,
    blockers: [...policyBlockers, ...STATIC_BLOCKERS],
    facts: {
      cluster_ids_redacted: true,
      fresh_projected_evidence_completed: false,
      profitability_claim_allowed: false,
      raw_symbols_redacted: true,
      structural_exposure_metrics_only: true,
      synthetic_only: true,
      within_limit_is_not_admission: true,
    },
    authority: {
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
    },
    readonly_projection_hash: "d".repeat(64),
  };
}

function envelope(status) {
  const value = projection(status);
  return {
    schema_version: presenter.ENVELOPE_SCHEMA_VERSION,
    verification_status: presenter.VERIFICATION_STATUS,
    expected_readonly_projection_hash: value.readonly_projection_hash,
    projection: value,
  };
}

test("public constants retain the neutral governance order", () => {
  assert.deepEqual(presenter.STAGE_ORDER, [
    "SOURCE",
    "GAP",
    "MATURITY",
    "PERMISSION",
  ]);
  assert.equal(Object.isFrozen(presenter.STAGE_ORDER), true);
  assert.equal(Object.isFrozen(presenter), true);
});

test("within-limit projection renders as observation, never admission", () => {
  const model = presenter.deriveClusterExposureViewModelV1(envelope());
  const markup = presenter.renderClusterExposureReadonlyProjectionV1(envelope());

  assert.equal(model.verificationAccepted, true);
  assert.equal(model.tone, "observed");
  assert.equal(model.statusLabel, "结构内观察");
  assert.deepEqual(
    model.metrics.map((item) => item.value),
    ["2", "2", "21.00%", "11.00%"],
  );
  assert.match(markup, /不构成准入、仓位、信号、订单或收益结论/);
  assert.doesNotMatch(markup, /\bREADY\b/i);
});

test("shared cluster breach stays blocked and exposes one effective cluster", () => {
  const input = envelope(presenter.STATUS_LIMIT_BREACH);
  const model = presenter.deriveClusterExposureViewModelV1(input);
  const markup = presenter.renderClusterExposureReadonlyProjectionV1(input);

  assert.equal(model.verificationAccepted, true);
  assert.equal(model.tone, "blocked");
  assert.equal(model.statusLabel, "预登记上限阻断");
  assert.deepEqual(
    model.metrics.map((item) => item.value),
    ["2", "1", "31.00%", "31.00%"],
  );
  assert.match(markup, /相关簇合计暴露超过预登记上限/);
  assert.match(markup, /模拟未授权 · 实盘永久硬锁/);
});

test("valid unknown projection hides every metric", () => {
  const model = presenter.deriveClusterExposureViewModelV1(
    envelope(presenter.STATUS_UNKNOWN),
  );

  assert.equal(model.verificationAccepted, true);
  assert.equal(model.rawStatus, presenter.STATUS_UNKNOWN);
  assert.deepEqual(
    model.metrics.map((item) => item.value),
    ["--", "--", "--", "--"],
  );
  assert.equal(model.projectionHash, "dddddddd...dddddddd");
});

test("hash mismatch fails closed without reflecting attacker content", () => {
  const input = envelope();
  input.expected_readonly_projection_hash = "e".repeat(64);
  input.projection.decision_path.gap = "<img src=x onerror=alert(1)>";
  const model = presenter.deriveClusterExposureViewModelV1(input);
  const markup = presenter.renderClusterExposureReadonlyProjectionV1(input);

  assert.equal(model.verificationAccepted, false);
  assert.equal(model.rawStatus, presenter.STATUS_UNKNOWN);
  assert.doesNotMatch(markup, /onerror|<img/i);
  assert.match(markup, /展示输入未完成精确验证交接/);
});

test("authority promotion and blocker injection fail closed", () => {
  const promoted = envelope();
  promoted.projection.authority.paper_authorized = true;
  const injected = envelope(presenter.STATUS_LIMIT_BREACH);
  injected.projection.policy_blocker_codes = ["<SCRIPT>"];
  injected.projection.blockers = ["<SCRIPT>", ...STATIC_BLOCKERS];

  assert.equal(
    presenter.deriveClusterExposureViewModelV1(promoted).verificationAccepted,
    false,
  );
  assert.equal(
    presenter.deriveClusterExposureViewModelV1(injected).verificationAccepted,
    false,
  );
});

test("rendered governance stages remain ordered", () => {
  const markup = presenter.renderClusterExposureReadonlyProjectionV1(envelope());
  const positions = presenter.STAGE_ORDER.map((stage) => markup.indexOf(`>${stage}<`));

  assert.equal(positions.every((position) => position >= 0), true);
  assert.deepEqual(positions, [...positions].sort((left, right) => left - right));
  assert.match(markup, /data-evidence-role="cluster-exposure-readonly"/);
});

test("view model and nested values are immutable", () => {
  const model = presenter.deriveClusterExposureViewModelV1(envelope());

  assert.equal(Object.isFrozen(model), true);
  assert.equal(Object.isFrozen(model.metrics), true);
  assert.equal(Object.isFrozen(model.metrics[0]), true);
  assert.throws(() => {
    model.metrics[0].value = "forged";
  }, TypeError);
});

test("production presenter has no DOM, network, storage, or runtime loader API", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "evidence_cluster_exposure_readonly_projection_v1.js"),
    "utf8",
  );
  for (const forbidden of [
    "document.",
    "window.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "registerRoute",
    "currentPointer",
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});

test("isolated stylesheet carries the contour signature and accessibility guards", () => {
  const css = fs.readFileSync(
    path.join(__dirname, "evidence_cluster_exposure_readonly_projection_v1.css"),
    "utf8",
  );

  assert.match(css, /--cep-ink:\s*#13282d/);
  assert.match(css, /--cep-tide:\s*#0d6670/);
  assert.match(css, /--cep-rust:\s*#b34e34/);
  assert.match(css, /conic-gradient/);
  assert.match(css, /summary:focus-visible/);
  assert.match(css, /max-width:\s*720px/);
  assert.match(css, /max-width:\s*430px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test("presenter and stylesheet remain deliberately unmounted", () => {
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

  assert.equal(
    index.includes("evidence_cluster_exposure_readonly_projection_v1.js"),
    false,
  );
  assert.equal(
    index.includes("evidence_cluster_exposure_readonly_projection_v1.css"),
    false,
  );
});
