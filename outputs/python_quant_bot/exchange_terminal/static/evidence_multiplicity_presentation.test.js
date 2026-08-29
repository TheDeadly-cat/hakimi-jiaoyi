const assert = require("assert");
const fs = require("fs");
const path = require("path");

global.window = global;
require("./evidence_presentation.js");

const present =
  global.HakimiEvidencePresentation
    .strategyCorrelationMultiplicitySummaryPresentation;

function summary(overrides = {}) {
  return {
    schema_version: "strategy-correlation-multiplicity-public-summary-v1",
    status: "OBSERVED_NO_FAMILY_WISE_BLOCK",
    decision_status: "PASS",
    required_source_schema_version:
      "strategy-correlation-multiplicity-report-evidence-v1",
    required_report_schema_version: 16,
    required_matrix_report_schema_version: 8,
    evidence_scope: "REDACTED_LOCAL_CORRELATION_MULTIPLICITY",
    familywise_method: "BONFERRONI_TWO_SIDED_95_FWER_CROSS_CLUSTER_V1",
    familywise_confidence_level: 0.95,
    familywise_alpha: 0.05,
    expected_family_size: 7,
    observed_family_size: 7,
    per_pair_alpha: 0.05 / 7,
    gap_category: "NONE_OBSERVED",
    maturity: "DESCRIPTIVE_ONLY",
    permission: "RESEARCH_ONLY",
    external_authenticity_proven: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    formal_registry_bound: false,
    current_report_schema_bound: false,
    requires_current_consumer_activation: true,
    current_writer_activation_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
    ...overrides,
  };
}

const clear = present(summary());
assert.strictEqual(clear.valid, true);
assert.strictEqual(clear.rawStatus, "OBSERVED_NO_FAMILY_WISE_BLOCK");
assert.match(clear.statusText, /未观察到阻断/);
assert.match(clear.sourceText, /Schema16/);
assert.match(clear.maturityText, /7 \/ 7/);
assert.match(clear.maturityText, /0\.007143/);
assert.match(clear.permissionText, /模拟未授权/);
assert.doesNotMatch(JSON.stringify(clear), /READY|盈利已证明|可交易/);

const blocked = present(summary({
  status: "OBSERVED_FAMILY_WISE_BLOCK",
  decision_status: "BLOCK",
  gap_category: "FAMILY_WISE_MULTIPLICITY_BLOCK",
}));
assert.strictEqual(blocked.valid, true);
assert.match(blocked.statusText, /证据存在缺口/);
assert.match(blocked.gapText, /重登记或补证据/);

const unknown = present(summary({
  status: "UNKNOWN",
  decision_status: null,
  expected_family_size: null,
  observed_family_size: null,
  per_pair_alpha: null,
  gap_category: "SOURCE_INVALID",
}));
assert.strictEqual(unknown.valid, true);
assert.strictEqual(unknown.contractConnected, true);
assert.match(unknown.statusText, /来源未连接/);

const tamperCases = [
  summary({ paper_authorized: true }),
  summary({ expected_family_size: "7" }),
  summary({ observed_family_size: 8 }),
  summary({ per_pair_alpha: 0.05 }),
  summary({ decision_status: "BLOCK" }),
  { ...summary(), left_symbol: "AAPL" },
];
for (const value of tamperCases) {
  const observed = present(value);
  assert.strictEqual(observed.valid, false);
  assert.strictEqual(observed.rawStatus, "UNKNOWN");
}

const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const styleSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
assert.match(appSource, /data-evidence-role="correlation-multiplicity"/);
assert.match(appSource, /strategyMultiplicityLedgerHeading/);
assert.match(appSource, /SOURCE/);
assert.match(appSource, /GAP/);
assert.match(appSource, /MATURITY/);
assert.match(appSource, /PERMISSION/);
assert.match(styleSource, /\.strategy-multiplicity-ledger/);
assert.match(styleSource, /FWER 95%/);

console.log("strategy correlation multiplicity presentation contract: PASS");
