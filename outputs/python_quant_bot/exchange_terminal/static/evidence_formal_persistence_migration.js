(function attachFormalPersistenceMigration(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HakimiFormalPersistenceMigration = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createApi() {
  "use strict";

  const SCHEMA_VERSION =
    "strategy-correlation-cluster-stability-formal-persistence-public-summary-v1";
  const STATIC_BUILD_FINGERPRINT =
    "20260821-formal-persistence-preregistration-lockboard-1";
  const STATES = new Set([
    "NOT_SUPPLIED",
    "READ_CONTRACT_COMPLETE_BLOCKED",
    "READ_CONTRACT_BLOCKED",
    "UNKNOWN",
  ]);

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function lockedPermissions(permission) {
    const fields = [
      "provider_implemented",
      "formal_persistence_verified",
      "formal_persistence_activation_allowed",
      "formal_registry_bound",
      "formal_registry_activation_allowed",
      "writer_implemented",
      "current_writer_activation_allowed",
      "current_admission_allowed",
      "paper_authorized",
      "live_order_allowed",
    ];
    return isRecord(permission) && fields.every((field) => permission[field] === false);
  }

  function stateShapeMatches(summary) {
    const state = summary.projection_state;
    if (state === "READ_CONTRACT_COMPLETE_BLOCKED") {
      return summary.source.status === "PREREGISTRATION_VERIFIED" &&
        summary.source.read_contract === "COMPLETE" &&
        summary.maturity.status === "READ_CONTRACT_ONLY" &&
        summary.maturity.read_contract_complete === true;
    }
    if (state === "READ_CONTRACT_BLOCKED") {
      return summary.source.status === "PREREGISTRATION_VERIFIED" &&
        summary.source.read_contract === "BLOCKED" &&
        summary.maturity.status === "BLOCKED" &&
        summary.maturity.read_contract_complete === false;
    }
    if (state === "NOT_SUPPLIED") {
      return summary.source.status === "NOT_SUPPLIED" &&
        summary.source.read_contract === "NOT_SUPPLIED" &&
        summary.maturity.status === "NO_EVIDENCE" &&
        summary.maturity.read_contract_complete === false;
    }
    return summary.source.status === "UNKNOWN" &&
      summary.source.read_contract === "UNKNOWN" &&
      summary.maturity.status === "UNKNOWN" &&
      summary.maturity.read_contract_complete === false;
  }

  function validSummary(summary) {
    if (!isRecord(summary) || !STATES.has(summary.projection_state)) return false;
    if (summary.schema_version !== SCHEMA_VERSION ||
        summary.static_build_fingerprint !== STATIC_BUILD_FINGERPRINT ||
        !isRecord(summary.source) || !isRecord(summary.gap) ||
        !isRecord(summary.maturity) || !lockedPermissions(summary.permission)) return false;
    if (summary.source.protocol !== "formal-persistence-v1" ||
        summary.gap.status !== "OPEN" ||
        summary.gap.provider !== "MISSING" ||
        summary.gap.durable_write_receipt !== "MISSING" ||
        summary.gap.durable_reopen_receipt !== "MISSING" ||
        summary.gap.session_separation !== "MISSING" ||
        summary.gap.formal_persistence_asset !== "MISSING" ||
        summary.gap.report_writer !== "MISSING" ||
        summary.gap.current_pointer !== "LOCKED" ||
        summary.gap.next_required_boundary !== "AUTHORIZED_ISOLATED_PROVIDER_EVIDENCE" ||
        summary.maturity.activation_prerequisite_count !== 14 ||
        summary.maturity.persistence_decision !== "BLOCK" ||
        summary.permission.status !== "RESEARCH_ONLY") return false;
    return stateShapeMatches(summary);
  }

  function normalize(summary) {
    if (!validSummary(summary)) return { state: "UNKNOWN", read: "UNKNOWN" };
    return { state: summary.projection_state, read: summary.source.read_contract };
  }

  const COPY = {
    READ_CONTRACT_COMPLETE_BLOCKED: {
      tone: "held",
      seal: "PERSISTENCE BLOCKED",
      title: "Read complete. Durability remains unproven.",
      lead: "The isolated read contract replayed, but no provider, durable write, independent reopen, or formal persistence asset exists.",
    },
    READ_CONTRACT_BLOCKED: {
      tone: "blocked",
      seal: "READ CONTRACT BLOCK",
      title: "Read evidence stopped before persistence.",
      lead: "The preregistration exists, but the isolated read contract did not establish one exact candidate record.",
    },
    NOT_SUPPLIED: {
      tone: "absent",
      seal: "NO PERSISTENCE SPEC",
      title: "No persistence evidence has been supplied.",
      lead: "Provider, durable reopen, formal asset, writer, and current boundaries remain closed.",
    },
    UNKNOWN: {
      tone: "unknown",
      seal: "UNKNOWN INPUT",
      title: "Persistence evidence cannot be established.",
      lead: "The public contract is partial, invalid, or unverifiable. The lockboard falls back to its closed state.",
    },
  };

  function valuesFor(state) {
    if (state === "READ_CONTRACT_COMPLETE_BLOCKED")
      return ["VERIFIED", "COMPLETE", "MISSING", "MISSING", "MISSING", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    if (state === "READ_CONTRACT_BLOCKED")
      return ["VERIFIED", "BLOCKED", "MISSING", "MISSING", "MISSING", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    if (state === "NOT_SUPPLIED")
      return ["NOT SUPPLIED", "NOT SUPPLIED", "MISSING", "MISSING", "MISSING", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    return ["UNKNOWN", "UNKNOWN", "MISSING", "MISSING", "MISSING", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
  }

  function toneFor(value) {
    if (value === "VERIFIED" || value === "COMPLETE") return "held";
    if (value === "BLOCKED") return "blocked";
    if (value === "MISSING" || value === "LOCKED" || value === "RESEARCH ONLY") return "locked";
    if (value === "NOT SUPPLIED") return "absent";
    return "unknown";
  }

  function buildFormalPersistenceMigrationView(summary) {
    const normalized = normalize(summary);
    const copy = COPY[normalized.state];
    const keys = ["SPEC", "READ", "PROVIDER", "WRITE", "REOPEN", "FORMAL ASSET", "WRITER", "CURRENT", "PERMISSION"];
    const details = [
      "Fourteen prerequisites frozen",
      "Candidate read contract",
      "No authorized implementation",
      "No durable write receipt",
      "No independent session receipt",
      "No persistence verifier",
      "Report-20 writer absent",
      "Pointer unchanged",
      "No paper or live orders",
    ];
    const values = valuesFor(normalized.state);
    return {
      schema_version: "formal-persistence-migration-view-v1",
      state: normalized.state,
      tone: copy.tone,
      eyebrow: "DURABILITY AIRLOCK / PROTOCOL V1",
      seal: copy.seal,
      title: copy.title,
      lead: copy.lead,
      route: "SOURCE → GAP → MATURITY → PERMISSION",
      stages: keys.map((key, index) => ({ key, value: values[index], detail: details[index], tone: toneFor(values[index]), index })),
      session_gap: {
        label: "SESSION GAP",
        note: "WRITE and REOPEN must be independently sealed.",
      },
      next_boundary: "Authorized isolated provider evidence",
      permission_note: "Research evidence only. Persistence activation remains blocked.",
    };
  }

  function element(doc, tag, className, text) {
    const node = doc.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function mountFormalPersistenceMigration(target, summary) {
    const model = buildFormalPersistenceMigrationView(summary);
    let mountTarget = target;
    if (typeof target === "string" && typeof document !== "undefined") mountTarget = document.querySelector(target);
    if (!mountTarget || typeof mountTarget.replaceChildren !== "function") return model;
    const doc = mountTarget.ownerDocument || document;
    const panel = element(doc, "section", "fpm-lockboard");
    panel.dataset.tone = model.tone;
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-label", "Formal persistence migration status");

    const header = element(doc, "header", "fpm-lockboard__header");
    const heading = element(doc, "div", "fpm-lockboard__heading");
    heading.append(
      element(doc, "p", "fpm-lockboard__eyebrow", model.eyebrow),
      element(doc, "h2", "fpm-lockboard__title", model.title),
      element(doc, "p", "fpm-lockboard__lead", model.lead),
    );
    header.append(heading, element(doc, "div", "fpm-lockboard__seal", model.seal));

    const route = element(doc, "p", "fpm-lockboard__route", model.route);
    const track = element(doc, "div", "fpm-lockboard__track");
    model.stages.forEach((stage) => {
      const cell = element(doc, "article", "fpm-lockboard__cell");
      cell.dataset.tone = stage.tone;
      cell.dataset.key = stage.key;
      cell.style.setProperty("--fpm-index", String(stage.index));
      cell.append(
        element(doc, "span", "fpm-lockboard__index", String(stage.index + 1).padStart(2, "0")),
        element(doc, "p", "fpm-lockboard__label", stage.key),
        element(doc, "p", "fpm-lockboard__value", stage.value),
        element(doc, "p", "fpm-lockboard__detail", stage.detail),
      );
      track.append(cell);
    });
    const gap = element(doc, "div", "fpm-lockboard__session-gap");
    gap.append(
      element(doc, "strong", "fpm-lockboard__gap-label", model.session_gap.label),
      element(doc, "span", "fpm-lockboard__gap-note", model.session_gap.note),
    );
    const footer = element(doc, "footer", "fpm-lockboard__footer");
    footer.append(
      element(doc, "p", "fpm-lockboard__next", `NEXT BOUNDARY / ${model.next_boundary}`),
      element(doc, "p", "fpm-lockboard__permission", model.permission_note),
    );
    panel.append(header, route, track, gap, footer);
    mountTarget.replaceChildren(panel);
    return model;
  }

  return Object.freeze({
    SCHEMA_VERSION,
    STATIC_BUILD_FINGERPRINT,
    buildFormalPersistenceMigrationView,
    mountFormalPersistenceMigration,
  });
});
