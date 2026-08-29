(function completeLinkMigrationModule(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HakimiCompleteLinkMigration = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function factory() {
  "use strict";

  const SUMMARY_SCHEMA = "strategy-correlation-complete-link-migration-public-summary-v1";
  const VIEW_SCHEMA = "complete-link-migration-ledger-view-v1";

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function presentCompleteLinkMigration(summary) {
    const observed = Boolean(
      summary &&
        summary.schema_version === SUMMARY_SCHEMA &&
        summary.status === "OBSERVED" &&
        summary.source === "PROTOCOL_REGISTRATION_V4"
    );
    return {
      schemaVersion: VIEW_SCHEMA,
      tone: observed ? "caution" : "muted",
      eyebrow: "STRUCTURE MIGRATION",
      title: "Complete-link evidence lane",
      badge: observed ? "CONSUMER ONLY" : "SOURCE UNKNOWN",
      segments: [
        {
          id: "SOURCE",
          label: "Source",
          value: observed ? "Protocol registration v4" : "Unverified",
          state: observed ? "observed" : "unknown",
        },
        {
          id: "GAP",
          label: "Gap",
          value: observed
            ? "Formal registry + schema17 writer pending"
            : "Verified source unavailable",
          state: "blocked",
        },
        {
          id: "MATURITY",
          label: "Maturity",
          value: observed ? "Consumer only" : "Unknown",
          state: observed ? "descriptive" : "unknown",
        },
        {
          id: "PERMISSION",
          label: "Permission",
          value: "Research only",
          state: "locked",
        },
      ],
      canTrade: false,
      profitabilityClaimed: false,
    };
  }

  function renderCompleteLinkMigration(summary) {
    const view = presentCompleteLinkMigration(summary);
    const segments = view.segments
      .map(
        (segment) =>
          `<li class="complete-link-ledger__segment" data-state="${escapeHtml(
            segment.state
          )}"><span>${escapeHtml(segment.label)}</span><strong>${escapeHtml(
            segment.value
          )}</strong></li>`
      )
      .join("");
    return `<section class="complete-link-ledger" data-tone="${escapeHtml(
      view.tone
    )}" aria-label="Complete-link migration evidence ledger"><header><div><p>${escapeHtml(
      view.eyebrow
    )}</p><h3>${escapeHtml(view.title)}</h3></div><span>${escapeHtml(
      view.badge
    )}</span></header><ol>${segments}</ol></section>`;
  }

  return { presentCompleteLinkMigration, renderCompleteLinkMigration };
});
