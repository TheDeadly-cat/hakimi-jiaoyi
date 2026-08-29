"use strict";

const SUMMARY_SCHEMA = "strategy-correlation-cluster-stability-public-summary-v1";
const STATIC_FINGERPRINT = "20260821-within-cluster-stability-calibration-rail-1";
const PROTOCOL_SUMMARY_SCHEMA =
  "strategy-correlation-cluster-stability-protocol-migration-public-summary-v1";
const PROTOCOL_STATIC_FINGERPRINT =
  "20260821-cluster-stability-protocol-v9-migration-rail-1";

function isStrictResearchOnly(permission) {
  return Boolean(
    permission &&
      permission.status === "RESEARCH_ONLY" &&
      permission.descriptive_only === true &&
      permission.profitability_claim_allowed === false &&
      permission.paper_authorized === false &&
      permission.live_order_allowed === false &&
      permission.current_admission_allowed === false &&
      permission.current_writer_activation_allowed === false,
  );
}

function isStrictRedaction(redaction) {
  const fields = [
    "artifact_hashes_exposed",
    "strategy_identity_exposed",
    "variant_identity_exposed",
    "lane_identity_exposed",
    "cluster_identities_exposed",
    "symbol_identities_exposed",
    "correlation_values_exposed",
    "interval_values_exposed",
    "return_values_exposed",
    "rankings_exposed",
    "profitability_metrics_exposed",
  ];
  return Boolean(
    redaction && fields.every((field) => redaction[field] === false),
  );
}

function isStrictProtocolRedaction(redaction) {
  const fields = [
    "registration_hashes_exposed",
    "policy_hashes_exposed",
    "source_registration_exposed",
    "registry_identity_exposed",
    "strategy_identities_exposed",
    "cluster_identities_exposed",
    "symbol_identities_exposed",
    "correlation_values_exposed",
    "interval_values_exposed",
    "return_values_exposed",
  ];
  return Boolean(
    redaction && fields.every((field) => redaction[field] === false),
  );
}

function isValidProtocolSummary(summary) {
  return Boolean(
    summary &&
      summary.schema_version === PROTOCOL_SUMMARY_SCHEMA &&
      summary.static_fingerprint === PROTOCOL_STATIC_FINGERPRINT &&
      summary.source?.status === "OBSERVED" &&
      summary.source.protocol_target === "PROTOCOL_V9" &&
      summary.source.report_target === "REPORT20" &&
      summary.source.protocol_registration_status === "PREREGISTERED" &&
      summary.source.report20_consumer_status === "AVAILABLE" &&
      summary.source.stability_policy_status === "SEALED" &&
      summary.gap?.status === "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED" &&
      summary.gap.formal_registry_status === "NOT_SUPPLIED" &&
      summary.gap.schema20_writer_status === "NOT_IMPLEMENTED" &&
      summary.gap.current_activation_status === "NOT_ACTIVATED" &&
      summary.maturity?.status === "PROTOCOL_PREREGISTERED" &&
      summary.maturity.stability_policy === "SEALED" &&
      summary.maturity.report20_consumer === "AVAILABLE" &&
      summary.maturity.formal_registry === "PENDING" &&
      summary.maturity.writer === "NOT_IMPLEMENTED" &&
      summary.maturity.current === "NOT_ACTIVATED" &&
      Number.isInteger(summary.maturity.writer_prerequisite_count) &&
      summary.maturity.writer_prerequisite_count === 12 &&
      isStrictResearchOnly(summary.permission) &&
      summary.permission.formal_registry_activation_allowed === false &&
      isStrictProtocolRedaction(summary.redaction),
  );
}

function expectedState(summary) {
  const decision = summary?.gap?.stability_decision;
  if (decision === "PASS") {
    return {
      gap: "REPORT_INTEGRATION_NOT_IMPLEMENTED",
      maturity: "CONSUMER_GATE_PASS",
    };
  }
  if (decision === "BLOCK") {
    return {
      gap: "STABILITY_EVIDENCE_BLOCKED",
      maturity: "CONSUMER_GATE_BLOCK",
    };
  }
  return null;
}

function isValidObservedSummary(summary) {
  const state = expectedState(summary);
  return Boolean(
    state &&
      summary.schema_version === SUMMARY_SCHEMA &&
      summary.static_fingerprint === STATIC_FINGERPRINT &&
      summary.source?.status === "OBSERVED" &&
      summary.source.uncertainty_evidence_status === "VERIFIED" &&
      summary.source.complete_link_gate_status === "VERIFIED" &&
      summary.source.stability_policy_status === "SEALED" &&
      summary.source.stability_gate_contract_status === "VERIFIED" &&
      summary.gap.status === state.gap &&
      summary.gap.report_integration_status === "NOT_IMPLEMENTED" &&
      summary.gap.current_activation_status === "NOT_ACTIVATED" &&
      summary.maturity?.status === state.maturity &&
      summary.maturity.family_scope === "WITHIN_CLUSTER_PAIRS_ONLY" &&
      summary.maturity.correction_method === "BONFERRONI_TWO_SIDED_FWER_V1" &&
      summary.maturity.interval_rule === "SEALED" &&
      summary.maturity.report_integration === "NOT_IMPLEMENTED" &&
      summary.maturity.writer === "NOT_IMPLEMENTED" &&
      summary.maturity.current === "NOT_ACTIVATED" &&
      isStrictResearchOnly(summary.permission) &&
      isStrictRedaction(summary.redaction),
  );
}

function unknownPresentation() {
  return {
    variant: "unknown",
    state: "UNKNOWN",
    stateLabel: "UNVERIFIED SOURCE",
    eyebrow: "CORRELATION GOVERNANCE / INTERVAL STABILITY",
    title: "Within-cluster stability",
    subtitle: "The public stability contract could not be established.",
    flow: [
      { key: "SOURCE", value: "Unknown", detail: "Evidence source unverified", tone: "unknown" },
      { key: "GAP", value: "Unknown", detail: "Stability gap unavailable", tone: "unknown" },
      { key: "MATURITY", value: "Unknown", detail: "Consumer maturity unavailable", tone: "unknown" },
      { key: "PERMISSION", value: "Research only", detail: "No execution authority", tone: "locked" },
    ],
    rail: [
      { code: "U2", label: "Uncertainty-v2", status: "UNKNOWN", tone: "unknown" },
      { code: "CL", label: "Complete-link-v2", status: "UNKNOWN", tone: "unknown" },
      { code: "CI", label: "Adjusted interval", status: "UNKNOWN", tone: "unknown" },
      { code: "CG", label: "Consumer gate", status: "UNKNOWN", tone: "unknown" },
      { code: "RPT", label: "Report integration", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Research-only surface. No paper or live execution authority.",
  };
}

function observedPresentation(summary) {
  const blocked = summary.gap.stability_decision === "BLOCK";
  return {
    variant: "gate-evidence",
    state: blocked ? "EVIDENCE_BLOCKED" : "CONSUMER_GATE_PASS",
    stateLabel: blocked ? "CONTRACT VALID / EVIDENCE BLOCKED" : "INTERVAL BOUND HELD / CONSUMER ONLY",
    eyebrow: "CORRELATION GOVERNANCE / INTERVAL STABILITY",
    title: "Within-cluster stability",
    subtitle: blocked
      ? "The source contract is verified, but internal stability evidence does not satisfy the sealed rule."
      : "The sealed interval rule is satisfied; report integration and current activation remain absent.",
    flow: [
      { key: "SOURCE", value: "Verified", detail: "Uncertainty + topology observed", tone: "sealed" },
      {
        key: "GAP",
        value: blocked ? "Stability evidence" : "Report integration",
        detail: blocked ? "Consumer decision remains BLOCK" : "No report writer is available",
        tone: "gap",
      },
      {
        key: "MATURITY",
        value: blocked ? "Blocked evidence" : "Consumer gate",
        detail: blocked ? "No maturity upgrade applied" : "Not integrated into current",
        tone: blocked ? "gap" : "guarded",
      },
      { key: "PERMISSION", value: "Research only", detail: "Current remains inactive", tone: "locked" },
    ],
    rail: [
      { code: "U2", label: "Uncertainty-v2", status: "VERIFIED", tone: "sealed" },
      { code: "CL", label: "Complete-link-v2", status: "VERIFIED", tone: "sealed" },
      { code: "CI", label: "Adjusted interval", status: blocked ? "BLOCKED" : "HELD", tone: blocked ? "gap" : "guarded" },
      { code: "CG", label: "Consumer gate", status: blocked ? "BLOCK" : "PASS", tone: blocked ? "gap" : "guarded" },
      { code: "RPT", label: "Report integration", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Consumer evidence is not activation. No paper or live execution authority.",
  };
}

function protocolPresentation() {
  return {
    variant: "protocol-v9",
    state: "PROTOCOL_PREREGISTERED",
    stateLabel: "PROTOCOL-V9 SEALED / NOT ACTIVATED",
    eyebrow: "CORRELATION GOVERNANCE / PROTOCOL V9",
    title: "Within-cluster stability migration",
    subtitle: "Report20 and its stability policy are preregistered; formal registry, writer, and current remain absent.",
    flow: [
      { key: "SOURCE", value: "Protocol-v9", detail: "Registration-v7 observed", tone: "sealed" },
      { key: "GAP", value: "Registry + writer", detail: "Formal assets not supplied", tone: "gap" },
      { key: "MATURITY", value: "Preregistered", detail: "Twelve writer prerequisites remain", tone: "guarded" },
      { key: "PERMISSION", value: "Research only", detail: "Current remains inactive", tone: "locked" },
    ],
    rail: [
      { code: "P9", label: "Protocol-v9", status: "SEALED", tone: "sealed" },
      { code: "R20", label: "Report20 consumer", status: "AVAILABLE", tone: "sealed" },
      { code: "SP", label: "Stability policy", status: "SEALED", tone: "guarded" },
      { code: "REG", label: "Formal registry", status: "MISSING", tone: "gap" },
      { code: "W20", label: "Report20 writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Preregistration is not activation. No paper or live execution authority.",
  };
}

function presentClusterStabilityMigration(summary) {
  if (isValidProtocolSummary(summary)) return protocolPresentation();
  if (isValidObservedSummary(summary)) return observedPresentation(summary);
  return unknownPresentation();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderClusterStabilityMigration(summary, target) {
  const model = presentClusterStabilityMigration(summary);
  if (!target || typeof target !== "object" || !("innerHTML" in target)) {
    return model;
  }
  const flow = model.flow
    .map(
      (item, index) => `
        <article class="csmp-flow__step" data-tone="${escapeHtml(item.tone)}">
          <span class="csmp-flow__index">0${index + 1}</span>
          <span class="csmp-flow__key">${escapeHtml(item.key)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </article>`,
    )
    .join("");
  const rail = model.rail
    .map(
      (item, index) => `
        <li class="csmp-rail__stop" data-tone="${escapeHtml(item.tone)}">
          <span class="csmp-rail__line" aria-hidden="true"></span>
          <span class="csmp-rail__node">${escapeHtml(item.code)}</span>
          <span class="csmp-rail__copy">
            <strong>${escapeHtml(item.label)}</strong>
            <small>${escapeHtml(item.status)}</small>
          </span>
          <span class="csmp-rail__order">${index + 1}/${model.rail.length}</span>
        </li>`,
    )
    .join("");
  target.innerHTML = `
    <section class="csmp" data-state="${escapeHtml(model.state)}" data-variant="${escapeHtml(model.variant)}" aria-label="Within-cluster stability migration">
      <header class="csmp-head">
        <div>
          <p class="csmp-eyebrow">${escapeHtml(model.eyebrow)}</p>
          <h2>${escapeHtml(model.title)}</h2>
          <p class="csmp-subtitle">${escapeHtml(model.subtitle)}</p>
        </div>
        <div class="csmp-stamp" role="status">
          <span>EVIDENCE STATE</span>
          <strong>${escapeHtml(model.stateLabel)}</strong>
        </div>
      </header>
      <div class="csmp-flow">${flow}</div>
      <div class="csmp-calibration">
        <div class="csmp-calibration__label">
          <span>STABILITY CALIBRATION RAIL</span>
          <strong>Point estimate → interval evidence → permission lock</strong>
        </div>
        <ol class="csmp-rail">${rail}</ol>
      </div>
      <footer class="csmp-foot">
        <span class="csmp-lock" aria-hidden="true"></span>
        <span>${escapeHtml(model.footnote)}</span>
      </footer>
    </section>`;
  return model;
}

module.exports = {
  presentClusterStabilityMigration,
  renderClusterStabilityMigration,
};
