"use strict";

const SUMMARY_SCHEMA =
  "strategy-correlation-global-independence-protocol-migration-public-summary-v1";
const STATIC_FINGERPRINT =
  "20260821-global-independence-protocol-v8-migration-seal-1";
const REGISTRY_SUMMARY_SCHEMA =
  "strategy-correlation-global-independence-protocol-migration-public-summary-v2";
const REGISTRY_STATIC_FINGERPRINT =
  "20260821-global-independence-registry-candidate-migration-seal-1";

function isStrictResearchOnly(permission) {
  return Boolean(
    permission &&
      permission.status === "RESEARCH_ONLY" &&
      permission.descriptive_only === true &&
      permission.profitability_claim_allowed === false &&
      permission.paper_authorized === false &&
      permission.live_order_allowed === false &&
      permission.formal_registry_activation_allowed === false &&
      permission.current_admission_allowed === false &&
      permission.current_writer_activation_allowed === false,
  );
}

function isValidObservedSummary(summary) {
  return Boolean(
    summary &&
      summary.schema_version === SUMMARY_SCHEMA &&
      summary.static_fingerprint === STATIC_FINGERPRINT &&
      summary.source &&
      summary.source.status === "OBSERVED" &&
      summary.source.protocol_target === "PROTOCOL_V8" &&
      summary.source.report_target === "REPORT19" &&
      summary.source.protocol_registration_status === "PREREGISTERED" &&
      summary.source.report19_consumer_status === "AVAILABLE" &&
      summary.source.global_independence_policy_status === "SEALED" &&
      summary.gap &&
      summary.gap.status === "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED" &&
      summary.gap.formal_registry_status === "NOT_SUPPLIED" &&
      summary.gap.schema19_writer_status === "NOT_IMPLEMENTED" &&
      summary.gap.current_activation_status === "NOT_ACTIVATED" &&
      summary.maturity &&
      summary.maturity.status === "PROTOCOL_PREREGISTERED" &&
      summary.maturity.exact_graph_policy === "SEALED" &&
      summary.maturity.formal_registry === "PENDING" &&
      summary.maturity.writer === "NOT_IMPLEMENTED" &&
      summary.maturity.current === "NOT_ACTIVATED" &&
      Number.isInteger(summary.maturity.writer_prerequisite_count) &&
      summary.maturity.writer_prerequisite_count === 7 &&
      isStrictResearchOnly(summary.permission),
  );
}

function isStrictRegistryRedaction(redaction) {
  return Boolean(
    redaction &&
      redaction.artifact_hashes_exposed === false &&
      redaction.policy_hashes_exposed === false &&
      redaction.source_registration_exposed === false &&
      redaction.registry_candidate_identity_exposed === false &&
      redaction.registry_candidate_hash_exposed === false &&
      redaction.registry_source_exposed === false &&
      redaction.registry_source_hash_exposed === false &&
      redaction.selection_cutoff_exposed === false &&
      redaction.cluster_identities_exposed === false &&
      redaction.symbol_identities_exposed === false,
  );
}

function registryState(summary) {
  const candidate = summary?.gap?.registry_candidate_status;
  const states = {
    NOT_SUPPLIED: {
      gap: "REGISTRY_CANDIDATE_NOT_SUPPLIED",
      maturity: "PROTOCOL_PREREGISTERED",
    },
    BLOCK: {
      gap: "REGISTRY_CANDIDATE_BINDING_BLOCK",
      maturity: "CANDIDATE_EVIDENCE_BLOCKED",
    },
    CANDIDATE_BOUND: {
      gap: "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
      maturity: "REGISTRY_CANDIDATE_BOUND",
    },
  };
  return states[candidate] || null;
}

function isValidRegistrySummary(summary) {
  const state = registryState(summary);
  return Boolean(
    state &&
      summary.schema_version === REGISTRY_SUMMARY_SCHEMA &&
      summary.static_fingerprint === REGISTRY_STATIC_FINGERPRINT &&
      summary.source?.status === "OBSERVED" &&
      summary.source.protocol_target === "PROTOCOL_V8" &&
      summary.source.report_target === "REPORT19" &&
      summary.source.protocol_registration_status === "PREREGISTERED" &&
      summary.source.report19_consumer_status === "AVAILABLE" &&
      summary.source.global_independence_policy_status === "SEALED" &&
      summary.source.registry_candidate_contract_status === "AVAILABLE" &&
      summary.gap.status === state.gap &&
      summary.gap.formal_registry_status === "NOT_SUPPLIED" &&
      summary.gap.schema19_writer_status === "NOT_IMPLEMENTED" &&
      summary.gap.current_activation_status === "NOT_ACTIVATED" &&
      summary.maturity?.status === state.maturity &&
      summary.maturity.registry_candidate === summary.gap.registry_candidate_status &&
      summary.maturity.exact_graph_policy === "SEALED" &&
      summary.maturity.formal_registry === "PENDING" &&
      summary.maturity.writer === "NOT_IMPLEMENTED" &&
      summary.maturity.current === "NOT_ACTIVATED" &&
      summary.maturity.writer_prerequisite_count === 7 &&
      Number.isInteger(summary.maturity.writer_prerequisite_count) &&
      isStrictResearchOnly(summary.permission) &&
      isStrictRegistryRedaction(summary.redaction),
  );
}

function unknownPresentation() {
  return {
    variant: "protocol-only",
    state: "UNKNOWN",
    stateLabel: "UNVERIFIED SOURCE",
    eyebrow: "CORRELATION GOVERNANCE / PROTOCOL V8",
    title: "Global independence migration",
    subtitle: "The public migration contract could not be established.",
    prerequisiteCount: null,
    flow: [
      { key: "SOURCE", value: "Unknown", detail: "Protocol source unverified", tone: "unknown" },
      { key: "GAP", value: "Unknown", detail: "Migration gap unavailable", tone: "unknown" },
      { key: "MATURITY", value: "Unknown", detail: "Evidence maturity unavailable", tone: "unknown" },
      { key: "PERMISSION", value: "Research only", detail: "No execution authority", tone: "locked" },
    ],
    seals: [
      { code: "P8", label: "Protocol-v8", status: "UNKNOWN", tone: "unknown" },
      { code: "R19", label: "Report19 consumer", status: "UNKNOWN", tone: "unknown" },
      { code: "G2", label: "Global gate-v2", status: "UNKNOWN", tone: "unknown" },
      { code: "REG", label: "Formal registry", status: "MISSING", tone: "gap" },
      { code: "W19", label: "Schema19 writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Research-only surface. No paper or live execution authority.",
  };
}

function registryPresentation(summary) {
  const candidate = summary.gap.registry_candidate_status;
  const presentations = {
    NOT_SUPPLIED: {
      state: "REGISTRY_CANDIDATE_NOT_SUPPLIED",
      stateLabel: "PREREGISTERED / CANDIDATE MISSING",
      subtitle: "Protocol policy is sealed; registry candidate evidence has not been supplied.",
      gapValue: "Registry candidate",
      gapDetail: "Candidate evidence not supplied",
      maturityValue: "Preregistered",
      maturityDetail: "Formal assets remain absent",
      candidateStatus: "MISSING",
      candidateTone: "gap",
    },
    BLOCK: {
      state: "CANDIDATE_EVIDENCE_BLOCKED",
      stateLabel: "CANDIDATE EVIDENCE BLOCKED",
      subtitle: "Candidate inputs were supplied but did not satisfy the external binding contract.",
      gapValue: "Candidate binding",
      gapDetail: "Evidence contract blocked",
      maturityValue: "Blocked",
      maturityDetail: "No maturity upgrade applied",
      candidateStatus: "BLOCKED",
      candidateTone: "gap",
    },
    CANDIDATE_BOUND: {
      state: "REGISTRY_CANDIDATE_BOUND",
      stateLabel: "CANDIDATE BOUND / NOT FORMAL",
      subtitle: "Candidate evidence is externally bound; formal registry and writer remain absent.",
      gapValue: "Formal registry + writer",
      gapDetail: "Candidate is not a formal asset",
      maturityValue: "Candidate bound",
      maturityDetail: "Seven writer prerequisites remain",
      candidateStatus: "BOUND",
      candidateTone: "candidate",
    },
  };
  const view = presentations[candidate];
  return {
    variant: "registry-candidate",
    state: view.state,
    stateLabel: view.stateLabel,
    eyebrow: "CORRELATION GOVERNANCE / REGISTRY CANDIDATE",
    title: "Global independence migration",
    subtitle: view.subtitle,
    prerequisiteCount: 7,
    flow: [
      { key: "SOURCE", value: "Protocol-v8", detail: "Registration-v6 observed", tone: "sealed" },
      { key: "GAP", value: view.gapValue, detail: view.gapDetail, tone: "gap" },
      { key: "MATURITY", value: view.maturityValue, detail: view.maturityDetail, tone: candidate === "CANDIDATE_BOUND" ? "guarded" : "gap" },
      { key: "PERMISSION", value: "Research only", detail: "Current remains inactive", tone: "locked" },
    ],
    seals: [
      { code: "P8", label: "Protocol-v8", status: "SEALED", tone: "sealed" },
      { code: "R19", label: "Report19 consumer", status: "AVAILABLE", tone: "sealed" },
      { code: "G2", label: "Global gate-v2", status: "REQUIRED", tone: "guarded" },
      { code: "CND", label: "Registry candidate", status: view.candidateStatus, tone: view.candidateTone },
      { code: "REG", label: "Formal registry", status: "MISSING", tone: "gap" },
      { code: "W19", label: "Schema19 writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Candidate evidence is not formal activation. No paper or live execution authority.",
  };
}

function presentGlobalIndependenceProtocolMigration(summary) {
  if (isValidRegistrySummary(summary)) return registryPresentation(summary);
  if (!isValidObservedSummary(summary)) return unknownPresentation();
  return {
    variant: "protocol-only",
    state: "PREREGISTERED_ONLY",
    stateLabel: "PREREGISTERED / NOT ACTIVATED",
    eyebrow: "CORRELATION GOVERNANCE / PROTOCOL V8",
    title: "Global independence migration",
    subtitle:
      "Cross-dimension vote compression is sealed; formal activation assets remain absent.",
    prerequisiteCount: summary.maturity.writer_prerequisite_count,
    flow: [
      { key: "SOURCE", value: "Protocol-v8", detail: "Registration-v6 observed", tone: "sealed" },
      { key: "GAP", value: "Registry + writer", detail: "Formal assets not supplied", tone: "gap" },
      { key: "MATURITY", value: "Preregistered", detail: "Exact graph policy sealed", tone: "guarded" },
      { key: "PERMISSION", value: "Research only", detail: "Current remains inactive", tone: "locked" },
    ],
    seals: [
      { code: "P8", label: "Protocol-v8", status: "SEALED", tone: "sealed" },
      { code: "R19", label: "Report19 consumer", status: "AVAILABLE", tone: "sealed" },
      { code: "G2", label: "Global gate-v2", status: "REQUIRED", tone: "guarded" },
      { code: "REG", label: "Formal registry", status: "MISSING", tone: "gap" },
      { code: "W19", label: "Schema19 writer", status: "MISSING", tone: "gap" },
      { code: "CUR", label: "Current", status: "LOCKED", tone: "locked" },
    ],
    footnote: "Research-only surface. No paper or live execution authority.",
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderGlobalIndependenceProtocolMigration(summary, target) {
  const model = presentGlobalIndependenceProtocolMigration(summary);
  if (!target || typeof target !== "object" || !("innerHTML" in target)) {
    return model;
  }
  const flow = model.flow
    .map(
      (item, index) => `
        <article class="gipm-flow__step" data-tone="${escapeHtml(item.tone)}">
          <span class="gipm-flow__index">0${index + 1}</span>
          <span class="gipm-flow__key">${escapeHtml(item.key)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </article>`,
    )
    .join("");
  const seals = model.seals
    .map(
      (seal, index) => `
        <li class="gipm-seal" data-tone="${escapeHtml(seal.tone)}">
          <span class="gipm-seal__track" aria-hidden="true"></span>
          <span class="gipm-seal__node">${escapeHtml(seal.code)}</span>
          <span class="gipm-seal__copy">
            <strong>${escapeHtml(seal.label)}</strong>
            <small>${escapeHtml(seal.status)}</small>
          </span>
          <span class="gipm-seal__order">${index + 1}/${model.seals.length}</span>
        </li>`,
    )
    .join("");
  const count = model.prerequisiteCount === null ? "--" : model.prerequisiteCount;
  target.innerHTML = `
    <section class="gipm" data-state="${escapeHtml(model.state)}" data-variant="${escapeHtml(model.variant)}" aria-label="Global independence protocol migration">
      <header class="gipm-head">
        <div>
          <p class="gipm-eyebrow">${escapeHtml(model.eyebrow)}</p>
          <h2>${escapeHtml(model.title)}</h2>
          <p class="gipm-subtitle">${escapeHtml(model.subtitle)}</p>
        </div>
        <div class="gipm-stamp" role="status">
          <span>STATE</span>
          <strong>${escapeHtml(model.stateLabel)}</strong>
        </div>
      </header>
      <div class="gipm-flow">${flow}</div>
      <div class="gipm-circuit">
        <div class="gipm-circuit__label">
          <span>ACTIVATION SEAL CIRCUIT</span>
          <strong>${escapeHtml(count)} prerequisites</strong>
        </div>
        <ol class="gipm-seals">${seals}</ol>
      </div>
      <footer class="gipm-foot">
        <span class="gipm-lock" aria-hidden="true"></span>
        <span>${escapeHtml(model.footnote)}</span>
      </footer>
    </section>`;
  return model;
}

module.exports = {
  presentGlobalIndependenceProtocolMigration,
  renderGlobalIndependenceProtocolMigration,
};
