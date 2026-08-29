"use strict";

const SUMMARY_SCHEMA =
  "strategy-correlation-cluster-temporal-stability-migration-public-summary-v1";
const STATIC_FINGERPRINT =
  "20260821-temporal-report21-protocol-v10-lockboard-1";
const CANDIDATE_SUMMARY_SCHEMA =
  "strategy-correlation-cluster-temporal-stability-candidate-binding-public-summary-v1";
const CANDIDATE_STATIC_FINGERPRINT =
  "20260821-temporal-report21-candidate-binding-lock-1";

const OBSERVED_CONTRACT_FIELDS = {
  root: ["schema_version", "static_fingerprint", "source", "gap", "maturity", "permission", "redaction"],
  source: ["status", "protocol_target", "report_target", "protocol_registration_status", "report21_consumer_status", "temporal_policy_status", "report21_contract_status", "registration_report_pairing_status"],
  gap: ["status", "temporal_decision", "formal_binding_status", "formal_registry_status", "schema21_writer_status", "current_activation_status"],
  maturity: ["status", "temporal_policy", "report21_consumer", "report21_contract", "consumer_decision", "formal_binding", "writer", "current", "writer_prerequisite_count"],
  permission: ["status", "descriptive_only", "profitability_claim_allowed", "paper_authorized", "live_order_allowed", "formal_registry_activation_allowed", "report_writer_activation_allowed", "current_admission_allowed", "current_writer_activation_allowed"],
  redaction: ["registration_hashes_exposed", "extension_hashes_exposed", "policy_hashes_exposed", "source_registration_exposed", "report_extensions_exposed", "external_bindings_exposed", "strategy_identities_exposed", "cluster_identities_exposed", "symbol_identities_exposed", "correlation_values_exposed", "interval_values_exposed", "return_values_exposed", "completed_price_datasets_exposed", "profitability_metrics_exposed"],
};

const CANDIDATE_CONTRACT_FIELDS = {
  root: ["schema_version", "static_fingerprint", "source", "gap", "maturity", "permission", "redaction"],
  source: ["status", "binding_assessment_status", "candidate_binding_status", "report21_decision"],
  gap: ["status", "formal_registration_report_binding", "formal_registry_status", "writer_status", "current_activation_status"],
  maturity: ["status", "candidate_binding", "report21_decision", "formal_binding", "writer", "current"],
  permission: ["status", "descriptive_only", "profitability_claim_allowed", "candidate_binding_activation_allowed", "formal_registration_report_binding_allowed", "formal_registry_activation_allowed", "paper_authorized", "live_order_allowed", "current_admission_allowed", "current_writer_activation_allowed"],
  redaction: ["assessment_hash_exposed", "protocol_registration_hash_exposed", "report21_extension_hash_exposed", "report_identity_set_hash_exposed", "binding_id_exposed", "facts_exposed", "blockers_exposed", "external_assets_exposed", "external_bindings_exposed", "strategy_identities_exposed", "correlation_values_exposed", "interval_values_exposed", "return_values_exposed", "profitability_metrics_exposed"],
};

function hasExactKeys(value, fields) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length === fields.length &&
    fields.every((field) => Object.prototype.hasOwnProperty.call(value, field))
  );
}

function hasExactContractShape(summary, contract) {
  return Boolean(
    hasExactKeys(summary, contract.root) &&
      ["source", "gap", "maturity", "permission", "redaction"].every(
        (section) => hasExactKeys(summary[section], contract[section]),
      ),
  );
}

function isStrictResearchOnly(permission) {
  return Boolean(
    permission &&
      permission.status === "RESEARCH_ONLY" &&
      permission.descriptive_only === true &&
      permission.profitability_claim_allowed === false &&
      permission.paper_authorized === false &&
      permission.live_order_allowed === false &&
      permission.formal_registry_activation_allowed === false &&
      permission.report_writer_activation_allowed === false &&
      permission.current_admission_allowed === false &&
      permission.current_writer_activation_allowed === false,
  );
}

function isStrictRedaction(redaction) {
  const fields = [
    "registration_hashes_exposed",
    "extension_hashes_exposed",
    "policy_hashes_exposed",
    "source_registration_exposed",
    "report_extensions_exposed",
    "external_bindings_exposed",
    "strategy_identities_exposed",
    "cluster_identities_exposed",
    "symbol_identities_exposed",
    "correlation_values_exposed",
    "interval_values_exposed",
    "return_values_exposed",
    "completed_price_datasets_exposed",
    "profitability_metrics_exposed",
  ];
  return Boolean(
    redaction && fields.every((field) => redaction[field] === false),
  );
}

function classifyCandidateSummary(summary) {
  if (summary === undefined || summary === null) {
    return { kind: "ABSENT", decision: "NOT_SUPPLIED" };
  }
  const redactionFields = [
    "assessment_hash_exposed",
    "protocol_registration_hash_exposed",
    "report21_extension_hash_exposed",
    "report_identity_set_hash_exposed",
    "binding_id_exposed",
    "facts_exposed",
    "blockers_exposed",
    "external_assets_exposed",
    "external_bindings_exposed",
    "strategy_identities_exposed",
    "correlation_values_exposed",
    "interval_values_exposed",
    "return_values_exposed",
    "profitability_metrics_exposed",
  ];
  const permission = summary?.permission;
  const redaction = summary?.redaction;
  if (
    !hasExactContractShape(summary, CANDIDATE_CONTRACT_FIELDS) ||
    summary.schema_version !== CANDIDATE_SUMMARY_SCHEMA ||
    summary.static_fingerprint !== CANDIDATE_STATIC_FINGERPRINT ||
    !permission ||
    permission.status !== "RESEARCH_ONLY" ||
    permission.descriptive_only !== true ||
    permission.profitability_claim_allowed !== false ||
    permission.candidate_binding_activation_allowed !== false ||
    permission.formal_registration_report_binding_allowed !== false ||
    permission.formal_registry_activation_allowed !== false ||
    permission.paper_authorized !== false ||
    permission.live_order_allowed !== false ||
    permission.current_admission_allowed !== false ||
    permission.current_writer_activation_allowed !== false ||
    !redaction ||
    !redactionFields.every((field) => redaction[field] === false) ||
    summary.gap?.formal_registration_report_binding !== "NOT_ESTABLISHED" ||
    summary.gap.formal_registry_status !== "NOT_SUPPLIED" ||
    summary.gap.writer_status !== "NOT_IMPLEMENTED" ||
    summary.gap.current_activation_status !== "NOT_ACTIVATED" ||
    summary.maturity?.formal_binding !== "NOT_ESTABLISHED" ||
    summary.maturity.writer !== "NOT_IMPLEMENTED" ||
    summary.maturity.current !== "NOT_ACTIVATED"
  ) {
    return { kind: "UNKNOWN", decision: "UNKNOWN" };
  }
  const decision = summary.source?.report21_decision;
  if (
    summary.source.status === "NOT_SUPPLIED" &&
    summary.source.binding_assessment_status === "NOT_SUPPLIED" &&
    summary.source.candidate_binding_status === "NOT_SUPPLIED" &&
    decision === "NOT_SUPPLIED" &&
    summary.gap.status === "CANDIDATE_BINDING_NOT_SUPPLIED" &&
    summary.maturity.status === "NOT_SUPPLIED" &&
    summary.maturity.candidate_binding === "NOT_SUPPLIED" &&
    summary.maturity.report21_decision === "NOT_SUPPLIED"
  ) {
    return { kind: "NOT_SUPPLIED", decision };
  }
  if (
    summary.source.status === "UNKNOWN" &&
    summary.source.binding_assessment_status === "UNKNOWN" &&
    summary.source.candidate_binding_status === "UNKNOWN" &&
    decision === "UNKNOWN" &&
    summary.gap.status === "CANDIDATE_BINDING_UNKNOWN" &&
    summary.maturity.status === "UNKNOWN" &&
    summary.maturity.candidate_binding === "UNKNOWN" &&
    summary.maturity.report21_decision === "UNKNOWN"
  ) {
    return { kind: "UNKNOWN", decision };
  }
  if (
    summary.source.status === "OBSERVED" &&
    summary.source.binding_assessment_status === "VERIFIED" &&
    ["PASS", "BLOCK"].includes(decision) &&
    summary.maturity.report21_decision === decision
  ) {
    if (
      summary.source.candidate_binding_status === "CANDIDATE_BOUND" &&
      summary.gap.status === "FORMAL_BINDING_NOT_ESTABLISHED" &&
      summary.maturity.status === "CANDIDATE_BOUND_NOT_FORMAL" &&
      summary.maturity.candidate_binding === "CANDIDATE_BOUND"
    ) {
      return { kind: "CANDIDATE_BOUND", decision };
    }
    if (
      summary.source.candidate_binding_status === "BLOCK" &&
      summary.gap.status === "CANDIDATE_BINDING_BLOCKED" &&
      summary.maturity.status === "CANDIDATE_BLOCKED" &&
      summary.maturity.candidate_binding === "BLOCK"
    ) {
      return { kind: "CANDIDATE_BLOCKED", decision };
    }
  }
  return { kind: "UNKNOWN", decision: "UNKNOWN" };
}

function classifyObservedSummary(summary) {
  if (
    !hasExactContractShape(summary, OBSERVED_CONTRACT_FIELDS) ||
    summary.schema_version !== SUMMARY_SCHEMA ||
    summary.static_fingerprint !== STATIC_FINGERPRINT ||
    summary.source?.status !== "OBSERVED" ||
    summary.source.protocol_target !== "PROTOCOL_V10" ||
    summary.source.report_target !== "REPORT21" ||
    summary.source.protocol_registration_status !== "PREREGISTERED" ||
    summary.source.report21_consumer_status !== "AVAILABLE" ||
    summary.source.temporal_policy_status !== "SEALED" ||
    summary.gap?.formal_registry_status !== "NOT_SUPPLIED" ||
    summary.gap.schema21_writer_status !== "NOT_IMPLEMENTED" ||
    summary.gap.current_activation_status !== "NOT_ACTIVATED" ||
    summary.maturity?.temporal_policy !== "SEALED" ||
    summary.maturity.report21_consumer !== "AVAILABLE" ||
    summary.maturity.writer !== "NOT_IMPLEMENTED" ||
    summary.maturity.current !== "NOT_ACTIVATED" ||
    !Number.isInteger(summary.maturity.writer_prerequisite_count) ||
    summary.maturity.writer_prerequisite_count !== 13 ||
    !isStrictResearchOnly(summary.permission) ||
    !isStrictRedaction(summary.redaction)
  ) {
    return null;
  }

  const contract = summary.source.report21_contract_status;
  const pairing = summary.source.registration_report_pairing_status;
  if (
    contract === "NOT_SUPPLIED" &&
    pairing === "NOT_SUPPLIED" &&
    summary.gap.status === "REPORT21_CONTRACT_NOT_SUPPLIED" &&
    summary.gap.temporal_decision === "NOT_SUPPLIED" &&
    summary.gap.formal_binding_status === "NOT_SUPPLIED" &&
    summary.maturity.status === "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED" &&
    summary.maturity.report21_contract === "NOT_SUPPLIED" &&
    summary.maturity.consumer_decision === "NOT_SUPPLIED" &&
    summary.maturity.formal_binding === "NOT_SUPPLIED"
  ) {
    return "NOT_SUPPLIED";
  }
  if (
    contract === "UNKNOWN" &&
    pairing === "UNKNOWN" &&
    summary.gap.status === "REPORT21_CONTRACT_UNKNOWN" &&
    summary.gap.temporal_decision === "UNKNOWN" &&
    summary.gap.formal_binding_status === "UNKNOWN" &&
    summary.maturity.status === "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN" &&
    summary.maturity.report21_contract === "UNKNOWN" &&
    summary.maturity.consumer_decision === "UNKNOWN" &&
    summary.maturity.formal_binding === "UNKNOWN"
  ) {
    return "REPORT_UNKNOWN";
  }
  if (
    contract === "VERIFIED" &&
    pairing === "NOT_FORMALLY_BOUND" &&
    summary.gap.formal_binding_status === "NOT_FORMALLY_BOUND" &&
    summary.maturity.report21_contract === "VERIFIED" &&
    summary.maturity.formal_binding === "NOT_FORMALLY_BOUND"
  ) {
    if (
      summary.gap.status === "FORMAL_BINDING_AND_WRITER_NOT_SUPPLIED" &&
      summary.gap.temporal_decision === "PASS" &&
      summary.maturity.status === "REPORT21_CONSUMER_PASS_UNBOUND" &&
      summary.maturity.consumer_decision === "PASS"
    ) {
      return "CONSUMER_PASS_UNBOUND";
    }
    if (
      summary.gap.status === "TEMPORAL_EVIDENCE_BLOCKED_AND_UNBOUND" &&
      summary.gap.temporal_decision === "BLOCK" &&
      summary.maturity.status === "REPORT21_CONSUMER_BLOCK_UNBOUND" &&
      summary.maturity.consumer_decision === "BLOCK"
    ) {
      return "CONSUMER_BLOCK_UNBOUND";
    }
  }
  return null;
}

function unknownPresentation() {
  return {
    variant: "unknown",
    state: "UNKNOWN",
    stateLabel: "UNVERIFIED SOURCE",
    eyebrow: "CORRELATION GOVERNANCE / TEMPORAL REPORT21",
    title: "Temporal evidence lockboard",
    subtitle: "The public report21 and protocol-v10 contract could not be established.",
    flow: [
      { key: "SOURCE", value: "Unknown", detail: "Protocol source unverified", tone: "unknown" },
      { key: "GAP", value: "Unknown", detail: "Report and binding state unavailable", tone: "unknown" },
      { key: "MATURITY", value: "Unknown", detail: "Consumer maturity unavailable", tone: "unknown" },
      { key: "PERMISSION", value: "Research only", detail: "No execution authority", tone: "locked" },
    ],
    windows: [1, 2, 3].map((index) => ({
      label: `W${index}`,
      span: "20 returns",
      status: "UNVERIFIED",
      tone: "unknown",
    })),
    rail: [
      { code: "P10", label: "Protocol v10", status: "UNKNOWN", tone: "unknown" },
      { code: "R21", label: "Report21 consumer", status: "UNKNOWN", tone: "unknown" },
      { code: "W3", label: "Three-window policy", status: "UNKNOWN", tone: "unknown" },
      { code: "EXT", label: "Report contract", status: "UNKNOWN", tone: "unknown" },
      { code: "BND", label: "Formal binding", status: "UNKNOWN", tone: "unknown" },
      { code: "WRT", label: "Report writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Research-only surface. No paper or live execution authority.",
  };
}

function observedPresentation(kind) {
  const details = {
    NOT_SUPPLIED: {
      state: "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED",
      stateLabel: "PROTOCOL SEALED / REPORT21 NOT SUPPLIED",
      subtitle: "Protocol-v10 is preregistered; no report21 contract was supplied for public verification.",
      gapValue: "Report21 contract",
      gapDetail: "Not supplied",
      maturityValue: "Protocol preregistered",
      maturityDetail: "Consumer contract not observed",
      contractStatus: "MISSING",
      contractTone: "gap",
      bindingStatus: "MISSING",
      bindingTone: "gap",
    },
    REPORT_UNKNOWN: {
      state: "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN",
      stateLabel: "PROTOCOL SEALED / REPORT21 UNVERIFIED",
      subtitle: "Protocol-v10 is preregistered; the supplied report21 contract did not verify.",
      gapValue: "Report21 contract",
      gapDetail: "Supplied but unverified",
      maturityValue: "Protocol only",
      maturityDetail: "No consumer decision is displayed",
      contractStatus: "UNKNOWN",
      contractTone: "unknown",
      bindingStatus: "UNKNOWN",
      bindingTone: "unknown",
    },
    CONSUMER_PASS_UNBOUND: {
      state: "REPORT21_CONSUMER_PASS_UNBOUND",
      stateLabel: "CONTRACT VALID / DECISION PASS / UNBOUND",
      subtitle: "The report21 consumer contract verifies, but no formal registration-to-report binding or writer exists.",
      gapValue: "Formal binding",
      gapDetail: "Not supplied; writer absent",
      maturityValue: "Consumer decision PASS",
      maturityDetail: "Descriptive contract only",
      contractStatus: "PASS",
      contractTone: "sealed",
      bindingStatus: "UNBOUND",
      bindingTone: "gap",
    },
    CONSUMER_BLOCK_UNBOUND: {
      state: "REPORT21_CONSUMER_BLOCK_UNBOUND",
      stateLabel: "CONTRACT VALID / EVIDENCE BLOCKED / UNBOUND",
      subtitle: "The report21 contract verifies and preserves a temporal evidence BLOCK without activation.",
      gapValue: "Temporal evidence",
      gapDetail: "Consumer decision remains BLOCK",
      maturityValue: "Consumer decision BLOCK",
      maturityDetail: "No maturity upgrade applied",
      contractStatus: "BLOCK",
      contractTone: "gap",
      bindingStatus: "UNBOUND",
      bindingTone: "gap",
    },
  }[kind];

  return {
    variant: "report21-protocol-v10",
    state: details.state,
    stateLabel: details.stateLabel,
    eyebrow: "CORRELATION GOVERNANCE / TEMPORAL REPORT21",
    title: "Temporal evidence lockboard",
    subtitle: details.subtitle,
    flow: [
      { key: "SOURCE", value: "Protocol v10 sealed", detail: "Report21 consumer available", tone: "sealed" },
      { key: "GAP", value: details.gapValue, detail: details.gapDetail, tone: "gap" },
      { key: "MATURITY", value: details.maturityValue, detail: details.maturityDetail, tone: kind === "CONSUMER_PASS_UNBOUND" ? "guarded" : "gap" },
      { key: "PERMISSION", value: "Research only", detail: "Writer absent; current locked", tone: "locked" },
    ],
    windows: [1, 2, 3].map((index) => ({
      label: `W${index}`,
      span: "20 returns",
      status: "BOUNDARY SEALED",
      tone: "sealed",
    })),
    rail: [
      { code: "P10", label: "Protocol v10", status: "SEALED", tone: "sealed" },
      { code: "R21", label: "Report21 consumer", status: "AVAILABLE", tone: "sealed" },
      { code: "W3", label: "Three-window policy", status: "SEALED", tone: "sealed" },
      { code: "EXT", label: "Report contract", status: details.contractStatus, tone: details.contractTone },
      { code: "BND", label: "Formal binding", status: details.bindingStatus, tone: details.bindingTone },
      { code: "WRT", label: "Report writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Preregistration and consumer verification are not activation. No paper or live execution authority.",
  };
}

function applyCandidateBinding(model, baseKind, candidateSummary) {
  const candidate = classifyCandidateSummary(candidateSummary);
  if (candidate.kind === "ABSENT" || candidate.kind === "NOT_SUPPLIED") {
    return model;
  }
  const expectedDecision =
    baseKind === "CONSUMER_PASS_UNBOUND"
      ? "PASS"
      : baseKind === "CONSUMER_BLOCK_UNBOUND"
        ? "BLOCK"
        : null;
  let kind = candidate.kind;
  if (kind === "CANDIDATE_BOUND" && candidate.decision !== expectedDecision) {
    kind = "UNKNOWN";
  }
  const next = {
    ...model,
    flow: model.flow.map((item) => ({ ...item })),
    rail: model.rail.map((item) => ({ ...item })),
  };
  const binding = next.rail.find((item) => item.code === "BND");
  const gap = next.flow.find((item) => item.key === "GAP");
  if (kind === "CANDIDATE_BOUND") {
    next.state = `${model.state}_CANDIDATE_BOUND_NOT_FORMAL`;
    next.stateLabel = "CANDIDATE BOUND / NOT FORMAL / CURRENT LOCKED";
    binding.status = "CANDIDATE";
    binding.tone = "candidate";
    gap.value = "Formal binding";
    gap.detail = "Candidate verified; formal binding absent";
    gap.tone = "gap";
    next.footnote = "Candidate binding is not formal registration or activation. No paper or live execution authority.";
  } else if (kind === "CANDIDATE_BLOCKED") {
    next.state = `${model.state}_CANDIDATE_BLOCKED`;
    next.stateLabel = "CANDIDATE BINDING BLOCKED / CURRENT LOCKED";
    binding.status = "BLOCKED";
    binding.tone = "gap";
    gap.value = "Candidate binding";
    gap.detail = "Candidate assessment remains BLOCK";
    gap.tone = "gap";
  } else {
    next.state = `${model.state}_BINDING_UNKNOWN`;
    next.stateLabel = "REPORT STATE HELD / CANDIDATE BINDING UNKNOWN";
    binding.status = "UNKNOWN";
    binding.tone = "unknown";
    gap.value = "Candidate binding";
    gap.detail = "Candidate assessment unverified or mismatched";
    gap.tone = "unknown";
  }
  return next;
}

function presentTemporalReport21Lockboard(summary, candidateSummary) {
  const kind = classifyObservedSummary(summary);
  return kind
    ? applyCandidateBinding(observedPresentation(kind), kind, candidateSummary)
    : unknownPresentation();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTemporalReport21Lockboard(summary, target, candidateSummary) {
  const model = presentTemporalReport21Lockboard(summary, candidateSummary);
  if (!target || typeof target !== "object" || !("innerHTML" in target)) {
    return model;
  }
  const flow = model.flow
    .map(
      (item, index) => `
        <div class="tsr21-flow__step" data-tone="${escapeHtml(item.tone)}">
          <span class="tsr21-flow__index">0${index + 1}</span>
          <span class="tsr21-flow__key">${escapeHtml(item.key)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </div>`,
    )
    .join("");
  const windows = model.windows
    .map(
      (item) => `
        <li class="tsr21-window" data-tone="${escapeHtml(item.tone)}">
          <span class="tsr21-window__label">${escapeHtml(item.label)}</span>
          <span class="tsr21-window__aperture" aria-hidden="true"></span>
          <strong>${escapeHtml(item.span)}</strong>
          <small>${escapeHtml(item.status)}</small>
        </li>`,
    )
    .join("");
  const rail = model.rail
    .map(
      (item, index) => `
        <li class="tsr21-rail__stop" data-tone="${escapeHtml(item.tone)}">
          <span class="tsr21-rail__node">${escapeHtml(item.code)}</span>
          <span class="tsr21-rail__copy">
            <strong>${escapeHtml(item.label)}</strong>
            <small>${escapeHtml(item.status)}</small>
          </span>
          <span class="tsr21-rail__order">${String(index + 1).padStart(2, "0")}</span>
        </li>`,
    )
    .join("");
  target.innerHTML = `
    <article class="tsr21" data-state="${escapeHtml(model.state)}" data-variant="${escapeHtml(model.variant)}" aria-label="Temporal report21 evidence lockboard">
      <header class="tsr21-head">
        <div>
          <p class="tsr21-eyebrow">${escapeHtml(model.eyebrow)}</p>
          <h2>${escapeHtml(model.title)}</h2>
          <p class="tsr21-subtitle">${escapeHtml(model.subtitle)}</p>
        </div>
        <div class="tsr21-stamp"><span>PUBLIC STATE</span><strong>${escapeHtml(model.stateLabel)}</strong></div>
      </header>
      <section class="tsr21-flow" aria-label="Source gap maturity permission">${flow}</section>
      <section class="tsr21-body">
        <div class="tsr21-register">
          <div class="tsr21-section-label"><span>PREREGISTERED WINDOW REGISTER</span><strong>3 x 20 completed returns</strong></div>
          <ol class="tsr21-windows">${windows}</ol>
        </div>
        <div class="tsr21-migration">
          <div class="tsr21-section-label"><span>MIGRATION LOCK RAIL</span><strong>Stops before writer and current</strong></div>
          <ol class="tsr21-rail">${rail}</ol>
        </div>
      </section>
      <footer class="tsr21-foot"><span class="tsr21-lock" aria-hidden="true"></span>${escapeHtml(model.footnote)}</footer>
    </article>`;
  return model;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    SUMMARY_SCHEMA,
    STATIC_FINGERPRINT,
    CANDIDATE_SUMMARY_SCHEMA,
    CANDIDATE_STATIC_FINGERPRINT,
    presentTemporalReport21Lockboard,
    renderTemporalReport21Lockboard,
  };
}

if (typeof window !== "undefined") {
  window.HakimiTemporalReport21Lockboard = {
    presentTemporalReport21Lockboard,
    renderTemporalReport21Lockboard,
  };
}
