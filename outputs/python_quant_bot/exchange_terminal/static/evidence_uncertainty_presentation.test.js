const assert = require("assert");
const fs = require("fs");
const path = require("path");

global.window = global;
require("./evidence_presentation.js");

const present =
  global.HakimiEvidencePresentation
    .strategyCorrelationUncertaintySummaryPresentation;

function summary(overrides = {}) {
  return {
    schema_version: "strategy-correlation-uncertainty-public-summary-v1",
    status: "OBSERVED_NO_UNCERTAINTY_BLOCK",
    required_source_schema_version: "strategy-correlation-uncertainty-audit-v2",
    evidence_scope: "REDACTED_LOCAL_CORRELATION_UNCERTAINTY",
    uncertainty_policy: "FISHER_Z_95_WITH_LAG1_EFFECTIVE_N_DESCRIPTIVE_V1",
    effective_sample_method: "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1",
    lookback_observations: 60,
    required_price_rows: 61,
    minimum_pair_overlap: 40,
    minimum_effective_observations: 12,
    confidence_level: 0.95,
    absolute_pearson_threshold: 0.75,
    pair_count: 10,
    cross_cluster_pair_count: 7,
    confirmed_high_cross_cluster_count: 0,
    ambiguous_cross_cluster_count: 0,
    insufficient_effective_sample_pair_count: 0,
    gap_category: "NONE_OBSERVED",
    maturity: "DESCRIPTIVE_ONLY",
    permission: "RESEARCH_ONLY",
    external_authenticity_proven: false,
    profitability_proven: false,
    performance_claim_allowed: false,
    parameter_selection_allowed: false,
    requires_new_report_schema: true,
    current_writer_activation_allowed: false,
    current_admission_allowed: false,
    paper_authorized: false,
    live_order_allowed: false,
    ...overrides,
  };
}

const clear = present(summary());
assert.strictEqual(clear.valid, true);
assert.strictEqual(clear.rawStatus, "OBSERVED_NO_UNCERTAINTY_BLOCK");
assert.match(clear.statusText, /未观察到/);
assert.match(clear.sourceText, /95% Fisher-z/);
assert.match(clear.maturityText, /7 \/ 10/);
assert.match(clear.permissionText, /模拟未授权/);
assert.doesNotMatch(JSON.stringify(clear), /READY|盈利已证明|可交易/);

const blocked = present(summary({
  status: "OBSERVED_UNCERTAINTY_BLOCK",
  ambiguous_cross_cluster_count: 1,
  gap_category: "CROSS_CLUSTER_AMBIGUOUS",
}));
assert.strictEqual(blocked.valid, true);
assert.match(blocked.statusText, /证据缺口/);
assert.match(blocked.gapText, /跨越阈值/);

const unknown = present(summary({
  status: "UNKNOWN",
  pair_count: null,
  cross_cluster_pair_count: null,
  confirmed_high_cross_cluster_count: null,
  ambiguous_cross_cluster_count: null,
  insufficient_effective_sample_pair_count: null,
  gap_category: "SOURCE_INVALID",
}));
assert.strictEqual(unknown.valid, true);
assert.strictEqual(unknown.contractConnected, true);
assert.match(unknown.statusText, /来源未连接/);

const tamperCases = [
  summary({ paper_authorized: true }),
  summary({ pair_count: "10" }),
  summary({ cross_cluster_pair_count: 11 }),
  summary({ ambiguous_cross_cluster_count: 1 }),
  { ...summary(), left_symbol: "AAPL" },
];
for (const value of tamperCases) {
  const observed = present(value);
  assert.strictEqual(observed.valid, false);
  assert.strictEqual(observed.rawStatus, "UNKNOWN");
}

const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const styleSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
assert.match(appSource, /data-evidence-role="correlation-uncertainty"/);
assert.match(appSource, /strategyUncertaintyLedgerHeading/);
assert.match(appSource, /SOURCE/);
assert.match(appSource, /GAP/);
assert.match(appSource, /MATURITY/);
assert.match(appSource, /PERMISSION/);
assert.match(styleSource, /\.strategy-uncertainty-ledger/);
assert.match(styleSource, /95% CI/);

console.log("strategy correlation uncertainty presentation contract: PASS");
