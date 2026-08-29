(function attachClusterStabilityRegistryMigration(root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HakimiClusterStabilityRegistryMigration = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function createApi() {
  "use strict";

  const SCHEMA_VERSION =
    "strategy-correlation-cluster-stability-registry-public-summary-v1";
  const STATIC_BUILD_FINGERPRINT =
    "20260821-cluster-stability-registry-candidate-migration-docket-1";
  const STATES = new Set([
    "NOT_SUPPLIED",
    "CANDIDATE_BOUND",
    "CANDIDATE_EVIDENCE_BLOCKED",
    "UNKNOWN",
  ]);

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function isNativeFalse(value) {
    return value === false;
  }

  function stateShapeMatches(summary) {
    const state = summary.projection_state;
    const source = summary.source.status;
    const maturity = summary.maturity.status;
    const bound = summary.maturity.candidate_evidence_bound;
    if (state === "CANDIDATE_BOUND") {
      return source === "VERIFIED_CANDIDATE" && maturity === "CANDIDATE_BOUND" && bound === true;
    }
    if (state === "CANDIDATE_EVIDENCE_BLOCKED") {
      return source === "VERIFIED_BLOCK" && maturity === "BLOCKED" && bound === false;
    }
    if (state === "NOT_SUPPLIED") {
      return source === "NOT_SUPPLIED" && maturity === "NO_EVIDENCE" && bound === false;
    }
    return source === "UNKNOWN" && maturity === "UNKNOWN" && bound === false;
  }

  function isValidSummary(summary) {
    if (!isRecord(summary) || !STATES.has(summary.projection_state)) {
      return false;
    }
    if (
      summary.schema_version !== SCHEMA_VERSION ||
      summary.static_build_fingerprint !== STATIC_BUILD_FINGERPRINT ||
      !isRecord(summary.source) ||
      !isRecord(summary.gap) ||
      !isRecord(summary.maturity) ||
      !isRecord(summary.permission)
    ) {
      return false;
    }
    if (
      summary.source.protocol !== "protocol-v9" ||
      summary.source.report !== "report-20" ||
      summary.source.contract !== "cluster-stability-registry-candidate-v1" ||
      summary.gap.status !== "OPEN" ||
      summary.gap.formal_registry !== "MISSING" ||
      summary.gap.report_writer !== "MISSING" ||
      summary.gap.current_pointer !== "LOCKED" ||
      summary.gap.next_required_boundary !== "FORMAL_REGISTRY_FINGERPRINT" ||
      summary.maturity.candidate_only !== true ||
      summary.permission.status !== "RESEARCH_ONLY"
    ) {
      return false;
    }
    const locked = [
      "formal_registry_bound",
      "formal_registry_activation_allowed",
      "writer_implemented",
      "current_writer_activation_allowed",
      "current_admission_allowed",
      "paper_authorized",
      "live_order_allowed",
    ];
    if (!locked.every((field) => isNativeFalse(summary.permission[field]))) {
      return false;
    }
    return stateShapeMatches(summary);
  }

  function lockedUnknownSummary() {
    return {
      projection_state: "UNKNOWN",
      source_status: "UNKNOWN",
      maturity_status: "UNKNOWN",
      candidate_evidence_bound: false,
    };
  }

  function normalizeSummary(summary) {
    if (!isValidSummary(summary)) {
      return lockedUnknownSummary();
    }
    return {
      projection_state: summary.projection_state,
      source_status: summary.source.status,
      maturity_status: summary.maturity.status,
      candidate_evidence_bound: summary.maturity.candidate_evidence_bound,
    };
  }

  const COPY = {
    CANDIDATE_BOUND: {
      tone: "candidate",
      stamp: "CANDIDATE ONLY",
      title: "Candidate sealed. Formal boundary remains open.",
      lead: "The frozen candidate and its binding replayed. This proves provenance only; it does not activate a registry or writer.",
    },
    CANDIDATE_EVIDENCE_BLOCKED: {
      tone: "blocked",
      stamp: "EVIDENCE BLOCK",
      title: "Candidate evidence stopped at binding.",
      lead: "The blocking assessment replayed as issued. Formal registration, report writing, and current admission stay unavailable.",
    },
    NOT_SUPPLIED: {
      tone: "absent",
      stamp: "NO CANDIDATE",
      title: "No registry candidate has been supplied.",
      lead: "The protocol target exists, but there is no public candidate evidence to evaluate. Every downstream boundary remains closed.",
    },
    UNKNOWN: {
      tone: "unknown",
      stamp: "UNKNOWN INPUT",
      title: "Registry evidence cannot be established.",
      lead: "The public contract is partial, invalid, or unverified. The display falls back to the locked state.",
    },
  };

  function stageValues(state) {
    if (state === "CANDIDATE_BOUND") {
      return ["VERIFIED", "FROZEN", "BOUND", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    }
    if (state === "CANDIDATE_EVIDENCE_BLOCKED") {
      return ["VERIFIED BLOCK", "FROZEN", "BLOCK", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    }
    if (state === "NOT_SUPPLIED") {
      return ["NOT SUPPLIED", "NOT SUPPLIED", "NOT SUPPLIED", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
    }
    return ["UNKNOWN", "UNKNOWN", "UNKNOWN", "MISSING", "MISSING", "LOCKED", "RESEARCH ONLY"];
  }

  function stageTone(value) {
    if (value === "VERIFIED" || value === "FROZEN" || value === "BOUND") {
      return "candidate";
    }
    if (value === "VERIFIED BLOCK" || value === "BLOCK") {
      return "blocked";
    }
    if (value === "MISSING" || value === "LOCKED" || value === "RESEARCH ONLY") {
      return "locked";
    }
    if (value === "NOT SUPPLIED") {
      return "absent";
    }
    return "unknown";
  }

  function buildClusterStabilityRegistryMigrationView(summary) {
    const normalized = normalizeSummary(summary);
    const state = normalized.projection_state;
    const copy = COPY[state];
    const values = stageValues(state);
    const labels = ["SOURCE", "CANDIDATE", "BINDING", "FORMAL", "WRITER", "CURRENT", "PERMISSION"];
    const details = [
      "Public contract replay",
      "Frozen input only",
      "Expected hashes checked",
      "No persisted authority",
      "Report-20 writer absent",
      "Pointer unchanged",
      "No paper or live orders",
    ];
    return {
      schema_version: "cluster-stability-registry-migration-view-v1",
      state,
      tone: copy.tone,
      eyebrow: "REGISTRY DOCKET / PROTOCOL V9",
      stamp: copy.stamp,
      title: copy.title,
      lead: copy.lead,
      route: "SOURCE → GAP → MATURITY → PERMISSION",
      stages: labels.map((label, index) => ({
        label,
        value: values[index],
        detail: details[index],
        tone: stageTone(values[index]),
        index,
      })),
      next_boundary: {
        label: "Next required boundary",
        value: "Formal registry fingerprint",
        note: "Candidate evidence cannot satisfy this boundary.",
      },
      permission_note: "Research evidence only. No activation path is implied.",
    };
  }

  function createElement(doc, tag, className, text) {
    const node = doc.createElement(tag);
    node.className = className;
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function mountClusterStabilityRegistryMigration(target, summary) {
    const model = buildClusterStabilityRegistryMigrationView(summary);
    let mountTarget = target;
    if (typeof target === "string" && typeof document !== "undefined") {
      mountTarget = document.querySelector(target);
    }
    if (!mountTarget || typeof mountTarget.replaceChildren !== "function") {
      return model;
    }
    const doc = mountTarget.ownerDocument || document;
    const panel = createElement(doc, "section", "csr-docket");
    panel.dataset.tone = model.tone;
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-label", "Cluster stability registry migration status");

    const header = createElement(doc, "header", "csr-docket__header");
    const headingGroup = createElement(doc, "div", "csr-docket__heading");
    headingGroup.append(
      createElement(doc, "p", "csr-docket__eyebrow", model.eyebrow),
      createElement(doc, "h2", "csr-docket__title", model.title),
      createElement(doc, "p", "csr-docket__lead", model.lead),
    );
    const stamp = createElement(doc, "div", "csr-docket__stamp", model.stamp);
    stamp.setAttribute("aria-label", model.stamp);
    header.append(headingGroup, stamp);

    const route = createElement(doc, "p", "csr-docket__route", model.route);
    const track = createElement(doc, "div", "csr-docket__track");
    track.setAttribute("aria-label", "Activation boundary track");
    model.stages.forEach((stage) => {
      const cell = createElement(doc, "article", "csr-docket__cell");
      cell.dataset.tone = stage.tone;
      cell.style.setProperty("--csr-index", String(stage.index));
      cell.append(
        createElement(doc, "span", "csr-docket__marker", String(stage.index + 1).padStart(2, "0")),
        createElement(doc, "p", "csr-docket__label", stage.label),
        createElement(doc, "p", "csr-docket__value", stage.value),
        createElement(doc, "p", "csr-docket__detail", stage.detail),
      );
      track.append(cell);
    });

    const footer = createElement(doc, "footer", "csr-docket__footer");
    const boundary = createElement(doc, "div", "csr-docket__boundary");
    boundary.append(
      createElement(doc, "span", "csr-docket__boundary-label", model.next_boundary.label),
      createElement(doc, "strong", "csr-docket__boundary-value", model.next_boundary.value),
      createElement(doc, "span", "csr-docket__boundary-note", model.next_boundary.note),
    );
    footer.append(
      boundary,
      createElement(doc, "p", "csr-docket__permission", model.permission_note),
    );
    panel.append(header, route, track, footer);
    mountTarget.replaceChildren(panel);
    return model;
  }

  return Object.freeze({
    SCHEMA_VERSION,
    STATIC_BUILD_FINGERPRINT,
    buildClusterStabilityRegistryMigrationView,
    mountClusterStabilityRegistryMigration,
  });
});
