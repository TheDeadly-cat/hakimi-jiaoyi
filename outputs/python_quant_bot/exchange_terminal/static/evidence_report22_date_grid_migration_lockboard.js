"use strict";

const SUMMARY_SCHEMA =
  "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1";
const CONTRACT_FINGERPRINT =
  "20260822-report22-date-grid-migration-projection-lock-1";

const CONTRACT_FIELDS = {
  root: [
    "schema_version",
    "contract_fingerprint",
    "axis_order",
    "source",
    "gap",
    "maturity",
    "permission",
    "redaction",
  ],
  source: [
    "state",
    "assessment_contract",
    "assessment_mode",
    "report22_contract",
    "report22_decision",
  ],
  gap: [
    "state",
    "execution",
    "runtime_mutations",
    "migration_execution",
    "fresh_migration",
    "formal_registry",
    "writer",
    "current",
  ],
  maturity: [
    "state",
    "report22_evaluation",
    "formal_registry",
    "current",
  ],
  permission: [
    "state",
    "descriptive_only",
    "profitability_claim_allowed",
    "migration_execution_allowed",
    "writer_allowed",
    "current_admission_allowed",
    "paper_authorized",
    "live_order_allowed",
  ],
  redaction: [
    "assessment_hash_exposed",
    "candidate_registration_hash_exposed",
    "report22_extension_hash_exposed",
    "expected_hashes_exposed",
    "identity_bindings_exposed",
    "raw_dates_exposed",
    "raw_prices_exposed",
    "returns_exposed",
    "correlations_exposed",
    "plan_details_exposed",
    "blocker_details_exposed",
    "profitability_metrics_exposed",
    "external_assets_embedded",
  ],
};

const STATE_CONTRACTS = {
  NOT_SUPPLIED: {
    source: {
      assessment_contract: "NOT_SUPPLIED",
      assessment_mode: "NOT_SUPPLIED",
      report22_contract: "NOT_SUPPLIED",
      report22_decision: "NOT_SUPPLIED",
    },
    gap: "ASSESSMENT_NOT_SUPPLIED",
    maturity: "NOT_SUPPLIED",
    report22Evaluation: "NOT_SUPPLIED",
  },
  UNKNOWN: {
    source: {
      assessment_contract: "UNKNOWN",
      assessment_mode: "UNKNOWN",
      report22_contract: "UNKNOWN",
      report22_decision: "UNKNOWN",
    },
    gap: "ASSESSMENT_UNKNOWN",
    maturity: "UNKNOWN",
    report22Evaluation: "UNKNOWN",
  },
  PLAN_LISTED: {
    source: {
      assessment_contract: "VERIFIED",
      assessment_mode: "LIST",
      report22_contract: "NOT_EVALUATED",
      report22_decision: "NOT_EVALUATED",
    },
    gap: "PLAN_ONLY",
    maturity: "PLAN_LISTED_NOT_EXECUTED",
    report22Evaluation: "NOT_EVALUATED",
  },
};

function hasExactKeys(value, fields) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length === fields.length &&
    fields.every((field) => Object.prototype.hasOwnProperty.call(value, field))
  );
}

function hasExactShape(summary) {
  return Boolean(
    hasExactKeys(summary, CONTRACT_FIELDS.root) &&
      ["source", "gap", "maturity", "permission", "redaction"].every(
        (section) => hasExactKeys(summary[section], CONTRACT_FIELDS[section]),
      ),
  );
}

function hasExactAxisOrder(value) {
  const expected = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  return Boolean(
    Array.isArray(value) &&
      value.length === expected.length &&
      expected.every((item, index) => value[index] === item),
  );
}

function hasExactValues(value, expected) {
  return Object.entries(expected).every(([key, expectedValue]) =>
    value[key] === expectedValue,
  );
}

function isStrictGap(gap) {
  return Boolean(
    gap.execution === "NOT_EXECUTED" &&
      gap.runtime_mutations === "NONE" &&
      gap.migration_execution === "NOT_ALLOWED" &&
      gap.fresh_migration === "NOT_ALLOWED" &&
      gap.formal_registry === "NOT_BOUND" &&
      gap.writer === "NOT_AVAILABLE" &&
      gap.current === "NOT_ADMITTED",
  );
}

function isStrictMaturity(maturity) {
  return Boolean(
    maturity.formal_registry === "NOT_BOUND" &&
      maturity.current === "NOT_ADMITTED",
  );
}

function isStrictPermission(permission) {
  return Boolean(
    permission.state === "RESEARCH_ONLY" &&
      permission.descriptive_only === true &&
      permission.profitability_claim_allowed === false &&
      permission.migration_execution_allowed === false &&
      permission.writer_allowed === false &&
      permission.current_admission_allowed === false &&
      permission.paper_authorized === false &&
      permission.live_order_allowed === false,
  );
}

function isStrictRedaction(redaction) {
  return CONTRACT_FIELDS.redaction.every((field) => redaction[field] === false);
}

function classifySummary(summary) {
  if (
    !hasExactShape(summary) ||
    summary.schema_version !== SUMMARY_SCHEMA ||
    summary.contract_fingerprint !== CONTRACT_FINGERPRINT ||
    !hasExactAxisOrder(summary.axis_order) ||
    !isStrictGap(summary.gap) ||
    !isStrictMaturity(summary.maturity) ||
    !isStrictPermission(summary.permission) ||
    !isStrictRedaction(summary.redaction)
  ) {
    return null;
  }

  const state = summary.source.state;
  if (Object.prototype.hasOwnProperty.call(STATE_CONTRACTS, state)) {
    const contract = STATE_CONTRACTS[state];
    if (
      hasExactValues(summary.source, { state, ...contract.source }) &&
      summary.gap.state === contract.gap &&
      summary.maturity.state === contract.maturity &&
      summary.maturity.report22_evaluation === contract.report22Evaluation
    ) {
      return { state, decision: summary.source.report22_decision };
    }
    return null;
  }

  if (
    state === "DRY_RUN_VERIFIED" &&
    summary.source.assessment_contract === "VERIFIED" &&
    summary.source.assessment_mode === "DRY_RUN" &&
    summary.source.report22_contract === "VERIFIED" &&
    ["PASS", "BLOCK"].includes(summary.source.report22_decision) &&
    summary.gap.state === "DRY_RUN_ONLY" &&
    summary.maturity.state === "DRY_RUN_VERIFIED_NOT_EXECUTED" &&
    summary.maturity.report22_evaluation === "VERIFIED"
  ) {
    return { state, decision: summary.source.report22_decision };
  }
  return null;
}

function invalidPresentation() {
  return {
    variant: "unverified-contract",
    state: "UNKNOWN",
    decision: "UNKNOWN",
    eyebrow: "CORRELATION GOVERNANCE / REPORT22 DATE GRID",
    title: "Migration evidence ledger",
    stateLabel: "PUBLIC CONTRACT UNVERIFIED / PERMISSION LOCKED",
    subtitle:
      "The supplied public projection does not match the report22 migration summary contract.",
    flow: [
      { key: "SOURCE", value: "Unknown", detail: "Public contract unverified", tone: "unknown" },
      { key: "GAP", value: "Unknown", detail: "Migration evidence unavailable", tone: "unknown" },
      { key: "MATURITY", value: "Unknown", detail: "No maturity inference", tone: "unknown" },
      { key: "PERMISSION", value: "Research only", detail: "Execution remains locked", tone: "locked" },
    ],
    ledger: [
      { label: "Assessment contract", value: "UNKNOWN", tone: "unknown" },
      { label: "Assessment mode", value: "UNKNOWN", tone: "unknown" },
      { label: "Report22 decision", value: "UNKNOWN", tone: "unknown" },
      { label: "Runtime mutation", value: "NOT ALLOWED", tone: "locked" },
    ],
    rail: [
      { code: "SRC", label: "Public source", status: "UNKNOWN", tone: "unknown" },
      { code: "ASM", label: "Assessment", status: "UNKNOWN", tone: "unknown" },
      { code: "R22", label: "Report22", status: "UNKNOWN", tone: "unknown" },
      { code: "EXE", label: "Execution", status: "LOCKED", tone: "locked" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Unverified public source. No migration, paper or live execution authority.",
  };
}

function verifiedPresentation(classification) {
  const details = {
    NOT_SUPPLIED: {
      stateLabel: "ASSESSMENT NOT SUPPLIED / ZERO EXECUTION",
      subtitle:
        "No migration assessment was supplied; the report22 candidate remains outside presentation maturity.",
      sourceValue: "Assessment absent",
      sourceDetail: "Public state is NOT_SUPPLIED",
      sourceTone: "gap",
      gapValue: "Source evidence",
      gapDetail: "Assessment not supplied",
      maturityValue: "Not supplied",
      maturityDetail: "No report22 evaluation",
      assessmentStatus: "MISSING",
      modeStatus: "NOT SUPPLIED",
      reportStatus: "MISSING",
      reportTone: "gap",
    },
    UNKNOWN: {
      stateLabel: "ASSESSMENT UNKNOWN / ZERO EXECUTION",
      subtitle:
        "A migration assessment was supplied but could not establish a supported LIST or DRY_RUN state.",
      sourceValue: "Assessment unknown",
      sourceDetail: "Independent reconstruction unavailable",
      sourceTone: "unknown",
      gapValue: "Contract evidence",
      gapDetail: "Assessment remains unknown",
      maturityValue: "Unknown",
      maturityDetail: "No maturity upgrade",
      assessmentStatus: "UNKNOWN",
      modeStatus: "UNKNOWN",
      reportStatus: "UNKNOWN",
      reportTone: "unknown",
    },
    PLAN_LISTED: {
      stateLabel: "PLAN LISTED / REPORT22 NOT EVALUATED / ZERO EXECUTION",
      subtitle:
        "LIST verifies the migration plan boundary only; report22 was not evaluated and no step executed.",
      sourceValue: "LIST verified",
      sourceDetail: "Assessment contract reconstructed",
      sourceTone: "observed",
      gapValue: "Report22 evaluation",
      gapDetail: "Not evaluated in LIST mode",
      maturityValue: "Plan only",
      maturityDetail: "Listed, not executed",
      assessmentStatus: "VERIFIED",
      modeStatus: "LIST",
      reportStatus: "NOT EVALUATED",
      reportTone: "gap",
    },
    DRY_RUN_VERIFIED: {
      stateLabel:
        classification.decision === "PASS"
          ? "DRY RUN VERIFIED / REPORT22 PASS / ZERO EXECUTION"
          : "DRY RUN VERIFIED / REPORT22 BLOCK / ZERO EXECUTION",
      subtitle:
        classification.decision === "PASS"
          ? "The dry-run contract and report22 PASS decision verify, while migration execution remains absent."
          : "The dry-run contract verifies and preserves a report22 BLOCK decision without activation.",
      sourceValue: "DRY RUN verified",
      sourceDetail: "Assessment contract reconstructed",
      sourceTone: "observed",
      gapValue: "Migration execution",
      gapDetail: "Not executed; runtime unchanged",
      maturityValue: "Dry-run only",
      maturityDetail: `Report22 decision ${classification.decision}`,
      assessmentStatus: "VERIFIED",
      modeStatus: "DRY RUN",
      reportStatus: classification.decision,
      reportTone: classification.decision === "PASS" ? "observed" : "gap",
    },
  }[classification.state];

  return {
    variant: "report22-date-grid",
    state: classification.state,
    decision: classification.decision,
    eyebrow: "CORRELATION GOVERNANCE / REPORT22 DATE GRID",
    title: "Migration evidence ledger",
    stateLabel: details.stateLabel,
    subtitle: details.subtitle,
    flow: [
      { key: "SOURCE", value: details.sourceValue, detail: details.sourceDetail, tone: details.sourceTone },
      { key: "GAP", value: details.gapValue, detail: details.gapDetail, tone: "gap" },
      { key: "MATURITY", value: details.maturityValue, detail: details.maturityDetail, tone: details.reportTone },
      { key: "PERMISSION", value: "Research only", detail: "Writer, current, paper and live locked", tone: "locked" },
    ],
    ledger: [
      { label: "Assessment contract", value: details.assessmentStatus, tone: details.sourceTone },
      { label: "Assessment mode", value: details.modeStatus, tone: details.sourceTone },
      { label: "Report22 decision", value: details.reportStatus, tone: details.reportTone },
      { label: "Runtime mutation", value: "NONE", tone: "locked" },
    ],
    rail: [
      { code: "SRC", label: "Public source", status: details.sourceTone === "observed" ? "VERIFIED" : details.assessmentStatus, tone: details.sourceTone },
      { code: "ASM", label: "Assessment", status: details.modeStatus, tone: details.sourceTone },
      { code: "R22", label: "Report22", status: details.reportStatus, tone: details.reportTone },
      { code: "EXE", label: "Execution", status: "ZERO", tone: "locked" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote:
      "LIST and DRY_RUN are descriptive evidence only. No migration, paper or live execution authority.",
  };
}

function presentReport22DateGridMigrationLockboard(summary) {
  const classification = classifySummary(summary);
  return classification
    ? verifiedPresentation(classification)
    : invalidPresentation();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderReport22DateGridMigrationLockboard(summary, target) {
  const model = presentReport22DateGridMigrationLockboard(summary);
  if (!target || typeof target !== "object" || !("innerHTML" in target)) {
    return model;
  }
  const flow = model.flow
    .map(
      (item, index) => `
        <div class="tdg22-flow__step" data-tone="${escapeHtml(item.tone)}">
          <span class="tdg22-flow__index">0${index + 1}</span>
          <span class="tdg22-flow__key">${escapeHtml(item.key)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </div>`,
    )
    .join("");
  const ledger = model.ledger
    .map(
      (item) => `
        <div class="tdg22-ledger__row" data-tone="${escapeHtml(item.tone)}">
          <dt>${escapeHtml(item.label)}</dt>
          <dd>${escapeHtml(item.value)}</dd>
        </div>`,
    )
    .join("");
  const rail = model.rail
    .map(
      (item, index) => `
        <li class="tdg22-rail__stop" data-tone="${escapeHtml(item.tone)}">
          <span class="tdg22-rail__node">${escapeHtml(item.code)}</span>
          <span class="tdg22-rail__copy">
            <strong>${escapeHtml(item.label)}</strong>
            <small>${escapeHtml(item.status)}</small>
          </span>
          <span class="tdg22-rail__order">${String(index + 1).padStart(2, "0")}</span>
        </li>`,
    )
    .join("");
  target.innerHTML = `
    <article class="tdg22" data-state="${escapeHtml(model.state)}" data-decision="${escapeHtml(model.decision)}" data-variant="${escapeHtml(model.variant)}" aria-label="Report22 date-grid migration evidence ledger">
      <header class="tdg22-head">
        <div>
          <p class="tdg22-eyebrow">${escapeHtml(model.eyebrow)}</p>
          <h2>${escapeHtml(model.title)}</h2>
          <p class="tdg22-subtitle">${escapeHtml(model.subtitle)}</p>
        </div>
        <div class="tdg22-stamp"><span>PUBLIC STATE</span><strong>${escapeHtml(model.stateLabel)}</strong></div>
      </header>
      <section class="tdg22-flow" aria-label="Source gap maturity permission">${flow}</section>
      <section class="tdg22-body">
        <div class="tdg22-aperture" aria-hidden="true">
          <span class="tdg22-aperture__orbit"></span>
          <span class="tdg22-aperture__core">22</span>
          <small>DATE GRID</small>
        </div>
        <div class="tdg22-ledger-wrap">
          <div class="tdg22-section-label"><span>REDACTED VERIFICATION LEDGER</span><strong>No private evidence exposed</strong></div>
          <dl class="tdg22-ledger">${ledger}</dl>
        </div>
      </section>
      <section class="tdg22-rail-wrap">
        <div class="tdg22-section-label"><span>CONSUMER-FIRST LOCK RAIL</span><strong>Stops before execution and current</strong></div>
        <ol class="tdg22-rail">${rail}</ol>
      </section>
      <footer class="tdg22-foot"><span class="tdg22-lock" aria-hidden="true"></span>${escapeHtml(model.footnote)}</footer>
    </article>`;
  return model;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    SUMMARY_SCHEMA,
    CONTRACT_FINGERPRINT,
    presentReport22DateGridMigrationLockboard,
    renderReport22DateGridMigrationLockboard,
  };
}

if (typeof window !== "undefined") {
  window.HakimiReport22DateGridMigrationLockboard = {
    presentReport22DateGridMigrationLockboard,
    renderReport22DateGridMigrationLockboard,
  };
}
