"use strict";

const projectionV1 = require("./evidence_anti_replay_registry_gap_projection_v1.js");

const CARD_SCHEMA_VERSION = "anti-replay-registry-gap-card-v1";
const CARD_STATIC_FINGERPRINT =
  "20260823-anti-replay-registry-gap-card-v1-unmounted-lock-1";
const STAGE_ORDER = Object.freeze(["SOURCE", "GAP", "MATURITY", "PERMISSION"]);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function shortHash(value) {
  return `${String(value).slice(0, 12)}...${String(value).slice(-6)}`;
}

function buildAntiReplayRegistryGapViewModelV1(projection) {
  if (!projectionV1.verifyAntiReplayRegistryGapProjectionV1(projection)) {
    throw new TypeError("anti-replay registry gap projection-v1 is invalid");
  }
  return {
    eyebrow: "ANTI-REPLAY / REGISTRY",
    footnote:
      "Local cryptographic possession only. External registry behavior is not established.",
    gaps: projection.stages.gap.items.map((item, index) => ({
      index: String(index + 1).padStart(2, "0"),
      label: item.label,
      state: item.state,
    })),
    identity: {
      key_hash: shortHash(projection.source.public_key_spki_sha256),
      registry_id: projection.source.registry_id,
      verification_hash: shortHash(projection.source.verification_hash),
    },
    lede:
      "The preregistered key answered a local challenge. Identity, shared atomicity, trusted time, and receipts remain open gaps.",
    permission_locks: [
      "CURRENT",
      "RUNTIME",
      "MOUNT",
      "RECEIPT",
      "PAPER",
      "LIVE",
      "WRITER",
    ],
    schema_version: CARD_SCHEMA_VERSION,
    stages: [
      {
        detail: "Sealed verification and key hash",
        label: "SOURCE",
        state: "HASH-BOUND",
      },
      {
        detail: `${projection.facts.gap_count} external prerequisites`,
        label: "GAP",
        state: "OPEN",
      },
      {
        detail: "Key possession in one local contract",
        label: "MATURITY",
        state: "LOCAL-ONLY",
      },
      {
        detail: "No route, mount, receipt, or trading path",
        label: "PERMISSION",
        state: "LOCKED",
      },
    ],
    static_fingerprint: CARD_STATIC_FINGERPRINT,
    status: "BLOCKED",
    status_label: "EVIDENCE GAP",
    title: "Registry evidence gap",
  };
}

function renderAntiReplayRegistryGapCardV1(projection) {
  const view = buildAntiReplayRegistryGapViewModelV1(projection);
  const stages = view.stages
    .map(
      (stage, index) => `
        <li class="ar-gap-card__stage" data-stage="${escapeHtml(stage.label)}">
          <span class="ar-gap-card__stage-index">0${index + 1}</span>
          <span class="ar-gap-card__stage-label">${escapeHtml(stage.label)}</span>
          <strong class="ar-gap-card__stage-state">${escapeHtml(stage.state)}</strong>
          <span class="ar-gap-card__stage-detail">${escapeHtml(stage.detail)}</span>
        </li>`
    )
    .join("");
  const gaps = view.gaps
    .map(
      (gap) => `
        <li class="ar-gap-card__gap-row">
          <span class="ar-gap-card__gap-index">${escapeHtml(gap.index)}</span>
          <span class="ar-gap-card__gap-label">${escapeHtml(gap.label)}</span>
          <span class="ar-gap-card__gap-state">${escapeHtml(gap.state)}</span>
        </li>`
    )
    .join("");
  const locks = view.permission_locks
    .map((lock) => `<span class="ar-gap-card__lock">${escapeHtml(lock)} / LOCKED</span>`)
    .join("");
  return `<article class="ar-gap-card" data-schema-version="${escapeHtml(
    view.schema_version
  )}" data-status="blocked">
    <header class="ar-gap-card__header">
      <div>
        <p class="ar-gap-card__eyebrow">${escapeHtml(view.eyebrow)}</p>
        <h2 class="ar-gap-card__title">${escapeHtml(view.title)}</h2>
      </div>
      <span class="ar-gap-card__status">${escapeHtml(view.status_label)}</span>
    </header>
    <p class="ar-gap-card__lede">${escapeHtml(view.lede)}</p>
    <dl class="ar-gap-card__identity">
      <div><dt>REGISTRY</dt><dd>${escapeHtml(view.identity.registry_id)}</dd></div>
      <div><dt>KEY HASH</dt><dd>${escapeHtml(view.identity.key_hash)}</dd></div>
      <div><dt>VERIFY HASH</dt><dd>${escapeHtml(view.identity.verification_hash)}</dd></div>
    </dl>
    <ol class="ar-gap-card__stage-rail">${stages}
    </ol>
    <section class="ar-gap-card__gap-panel" aria-label="Open evidence gaps">
      <div class="ar-gap-card__section-heading">
        <span>OPEN GAP REGISTER</span><strong>${view.gaps.length.toString().padStart(2, "0")}</strong>
      </div>
      <ol class="ar-gap-card__gap-list">${gaps}
      </ol>
    </section>
    <div class="ar-gap-card__locks" aria-label="Locked permissions">${locks}</div>
    <footer class="ar-gap-card__footer">${escapeHtml(view.footnote)}</footer>
  </article>`;
}

module.exports = {
  CARD_SCHEMA_VERSION,
  CARD_STATIC_FINGERPRINT,
  STAGE_ORDER,
  buildAntiReplayRegistryGapViewModelV1,
  renderAntiReplayRegistryGapCardV1,
};
