(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HakimiStrataProtocolMigration = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SCHEMA =
    "strategy-correlation-strata-protocol-migration-public-summary-v1";
  const FINGERPRINT = "20260821-strata-protocol-v7-migration-seal-1";
  const GAP_LABELS = Object.freeze({
    UNKNOWN: "Migration evidence unavailable",
    REAL_REGISTRY_ASSET_NOT_SUPPLIED: "Real registry asset not supplied",
    REGISTRY_BINDING_BLOCK_OBSERVED: "Registry binding block observed",
    FORMAL_PERSISTENCE_AND_WRITER_PENDING:
      "Formal persistence and writer remain pending",
  });

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function presentStrataProtocolMigration(payload) {
    const validRoot =
      isRecord(payload) &&
      payload.schema_version === SCHEMA &&
      payload.static_fingerprint === FINGERPRINT;
    const source = validRoot && isRecord(payload.source) ? payload.source : {};
    const gap = validRoot && isRecord(payload.gap) ? payload.gap : {};
    const maturity =
      validRoot && isRecord(payload.maturity) ? payload.maturity : {};
    const sourceObserved =
      source.status === "OBSERVED" &&
      source.protocol_target === "PROTOCOL_V7" &&
      source.report_target === "REPORT18";
    const gapStatus = Object.prototype.hasOwnProperty.call(
      GAP_LABELS,
      gap.status
    )
      ? gap.status
      : "UNKNOWN";
    const maturityStatus = [
      "PROTOCOL_PREREGISTERED",
      "REGISTRY_BOUND_CANDIDATE",
    ].includes(maturity.status)
      ? maturity.status
      : "UNKNOWN";
    const prerequisiteCount =
      Number.isInteger(maturity.writer_prerequisite_count) &&
      maturity.writer_prerequisite_count >= 0
        ? maturity.writer_prerequisite_count
        : null;

    const sealed = sourceObserved ? "SEALED" : "UNKNOWN";
    const reportSeal =
      sourceObserved && source.report18_consumer_status === "AVAILABLE"
        ? "SEALED"
        : "UNKNOWN";
    const registrySeal =
      sourceObserved &&
      source.registry_candidate_contract_status === "AVAILABLE"
        ? "SEALED"
        : "UNKNOWN";
    return {
      source: {
        status: sourceObserved ? "OBSERVED" : "UNKNOWN",
        label: sourceObserved
          ? "Protocol preregistration observed"
          : "Protocol source unknown",
      },
      gap: {
        status: gapStatus,
        label: GAP_LABELS[gapStatus],
      },
      maturity: {
        status: maturityStatus,
        label:
          maturityStatus === "REGISTRY_BOUND_CANDIDATE"
            ? "Registry-bound candidate"
            : maturityStatus === "PROTOCOL_PREREGISTERED"
              ? "Protocol preregistered"
              : "Maturity unknown",
      },
      permission: {
        status: "RESEARCH_ONLY",
        label: "Research-only",
      },
      prerequisiteCount,
      seals: [
        { label: "Protocol-v7", status: sealed },
        { label: "Report18 consumer", status: reportSeal },
        { label: "Registry candidate", status: registrySeal },
        { label: "Formal persistence", status: "OPEN" },
        { label: "Writer", status: "OPEN" },
      ],
    };
  }

  function renderStrataProtocolMigration(rootElement, payload) {
    if (!rootElement || typeof rootElement !== "object") {
      throw new TypeError("rootElement is required");
    }
    const view = presentStrataProtocolMigration(payload);
    const prerequisiteText =
      view.prerequisiteCount === null
        ? "Unknown prerequisite count"
        : String(view.prerequisiteCount) + " frozen prerequisites";
    const seals = view.seals
      .map(
        (seal, index) =>
          '<li class="hksp-seal is-' +
          seal.status.toLowerCase() +
          '" style="--hksp-order:' +
          String(index) +
          '">' +
          '<span class="hksp-seal-notch" aria-hidden="true"></span>' +
          "<strong>" +
          seal.label +
          "</strong>" +
          "<small>" +
          seal.status +
          "</small>" +
          "</li>"
      )
      .join("");

    rootElement.innerHTML =
      '<section class="hksp-panel" tabindex="0" aria-labelledby="hksp-title">' +
      '<header class="hksp-header">' +
      '<p class="hksp-eyebrow">Strata migration / activation seal rack</p>' +
      '<h2 id="hksp-title">The protocol is sealed. Authority is not.</h2>' +
      '<p>Consumer contracts can be present while persistence, writer, and current activation remain absent.</p>' +
      "</header>" +
      '<ol class="hksp-seal-rack" aria-label="Migration seals">' +
      seals +
      "</ol>" +
      '<div class="hksp-sequence" aria-label="Evidence sequence">' +
      '<div><span>SOURCE</span><strong>' +
      view.source.label +
      "</strong></div>" +
      '<div><span>GAP</span><strong>' +
      view.gap.label +
      "</strong></div>" +
      '<div><span>MATURITY</span><strong>' +
      view.maturity.label +
      "</strong></div>" +
      '<div><span>PERMISSION</span><strong>' +
      view.permission.label +
      "</strong></div>" +
      "</div>" +
      '<footer class="hksp-footer">' +
      "<span>" +
      prerequisiteText +
      "</span>" +
      "<span>Formal registry pending / writer absent / current disabled</span>" +
      "</footer>" +
      "</section>";
    if (typeof rootElement.setAttribute === "function") {
      rootElement.setAttribute("data-hksp-mounted", "true");
    }
    return view;
  }

  return Object.freeze({
    presentStrataProtocolMigration,
    renderStrataProtocolMigration,
  });
});
